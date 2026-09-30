"""Google Identity Services verification and short-lived browser-bound game tickets.

Only Google's immutable ``sub`` crosses into game account handling. No Google
credential, email, name, or picture is persisted. Account creation/linking lives
in server.py; this module deliberately cannot select a game account by email.
"""
from __future__ import annotations

import asyncio
from collections import deque
from dataclasses import dataclass
import hashlib
import hmac
import json
import logging
import math
import os
import re
import secrets
import threading
import time
from urllib.parse import urlsplit

from aiohttp import web

AUTH_TTL = 300
MAX_AUTH_BODY = 16384
MAX_CREDENTIAL = 12288
MAX_PENDING = 1024
MAX_VERIFY_WORKERS = 4
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_CLIENT_RE = re.compile(r"^[A-Za-z0-9_-]+\.apps\.googleusercontent\.com$")
_CERT_URL = "https://www.googleapis.com/oauth2/v1/certs"
_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache", "X-Content-Type-Options": "nosniff"}
_LOG = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, code: str, message: str, status: int = 400):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


@dataclass(frozen=True)
class GoogleIdentity:
    sub: str


@dataclass(frozen=True)
class _Challenge:
    nonce: str
    binding: bytes
    expires: float


@dataclass(frozen=True)
class _Ticket:
    identity: GoogleIdentity
    binding: bytes
    expires: float


def _configured_origin(value: str) -> str:
    """Accept an explicit HTTPS origin (HTTP only on exact local loopback)."""
    try:
        parsed = urlsplit(value)
        port = parsed.port  # Reject invalid/overflowing port strings.
    except (ValueError, TypeError):
        return ""
    if (not parsed.hostname or parsed.username is not None or parsed.password is not None
            or parsed.path not in ("", "/") or parsed.query or parsed.fragment
            or any(c.isspace() for c in value) or "\\" in value):
        return ""
    if parsed.scheme != "https" and not (
            parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1", "::1"}):
        return ""
    # Configuration is exact, not inferred from Host/X-Forwarded-* headers.
    host = parsed.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    if port is not None and port != (443 if parsed.scheme == "https" else 80):
        host += f":{port}"
    return f"{parsed.scheme}://{host}"


def _binding_hash(value: str | None) -> bytes | None:
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        return None
    return hashlib.sha256(value.encode("ascii")).digest()


class GoogleTokenVerifier:
    """Official verifier with an HTTP-cache-aware, timeout-bounded transport."""
    def __init__(self, client_id: str, request=None):
        from google.oauth2 import id_token
        self._verify = id_token.verify_oauth2_token
        self.client_id = client_id
        self._lock = threading.Lock()
        self._session = None
        if request is None:
            import requests
            from cachecontrol import CacheControl
            from google.auth.transport.requests import Request
            self._session = CacheControl(requests.Session())
            # One fixed HTTPS endpoint, no environment netrc credentials.
            self._session.trust_env = False
            self._request = Request(session=self._session)
        else:
            self._request = request

    def _cert_request(self, url, method="GET", body=None, headers=None, **kwargs):
        if url != _CERT_URL or method != "GET":
            raise ValueError("Unexpected Google certificate endpoint")
        # Requests Session/CacheControl are shared only under this lock. Google
        # Cache-Control controls rotation; a cache miss has bounded I/O and no retries.
        with self._lock:
            return self._request(url=url, method=method, body=body, headers=headers,
                                 timeout=(2.0, 4.0))

    def __call__(self, credential: str):
        return self._verify(credential, self._cert_request, audience=self.client_id,
                            clock_skew_in_seconds=0)

    def close(self):
        if self._session is not None:
            self._session.close()


class GoogleAuthService:
    """Event-loop-owned challenge/ticket state; verification runs off the loop."""
    def __init__(self, client_id="", allowed_origin="", *, verifier=None, clock=time.monotonic,
                 wall_clock=time.time, max_pending=MAX_PENDING):
        self.client_id = client_id if isinstance(client_id, str) else ""
        self.allowed_origin = _configured_origin(allowed_origin)
        self.cookie_name = "__Host-bractwo_google" if self.allowed_origin.startswith("https://") else "bractwo_google_local"
        self.enabled = bool(_CLIENT_RE.fullmatch(self.client_id) and self.allowed_origin)
        self._clock, self._wall_clock = clock, wall_clock
        self._max_pending = max(1, int(max_pending))
        self._challenges: dict[str, _Challenge] = {}
        self._tickets: dict[str, _Ticket] = {}
        self._attempts: dict[str, deque] = {}
        self._inflight = 0
        self._verifier = verifier
        if self.enabled and self._verifier is None:
            try:
                self._verifier = GoogleTokenVerifier(self.client_id)
            except ImportError:
                self.enabled = False
                _LOG.error("Google login disabled: install google-auth[requests] and CacheControl.")

    @classmethod
    def from_env(cls):
        service = cls(os.environ.get("GOOGLE_CLIENT_ID", "").strip(),
                      os.environ.get("GOOGLE_AUTH_ORIGIN", "").strip())
        if not service.enabled and (os.environ.get("GOOGLE_CLIENT_ID") or os.environ.get("GOOGLE_AUTH_ORIGIN")):
            _LOG.warning("Google login disabled: check GOOGLE_CLIENT_ID and GOOGLE_AUTH_ORIGIN.")
        return service

    def _require_enabled(self):
        if not self.enabled:
            raise AuthError("google_disabled", "Logowanie przez Google nie jest jeszcze włączone.", 503)

    def _prune(self):
        now = self._clock()
        self._challenges = {k: v for k, v in self._challenges.items() if v.expires > now}
        self._tickets = {k: v for k, v in self._tickets.items() if v.expires > now}
        self._attempts = {k: v for k, v in self._attempts.items() if v and v[-1] > now - 60}

    def check_request(self, request):
        self._require_enabled()
        origins = request.headers.getall("Origin", [])
        if origins != [self.allowed_origin] or request.headers.get("X-Bractwo-Auth") != "1":
            raise AuthError("invalid_origin", "Otwórz logowanie na właściwej stronie gry.", 403)
        if request.headers.get("Sec-Fetch-Site") == "cross-site":
            raise AuthError("invalid_origin", "Otwórz logowanie na właściwej stronie gry.", 403)
        if request.content_type != "application/json":
            raise AuthError("invalid_request", "Wymagany komunikat JSON.", 415)
        self._prune()
        binding = _binding_hash(request.cookies.get(self.cookie_name))
        # Enforce both budgets: replacing a browser cookie cannot bypass the IP
        # cap. The peer budget is generous because reverse proxies may share it;
        # arbitrary forwarded-IP headers are never accepted as trustworthy.
        limits = [("p:" + (request.remote or "unknown"), 120)]
        if binding:
            limits.append(("b:" + binding.hex(), 30))
        missing = sum(key not in self._attempts for key, _ in limits)
        if len(self._attempts) + missing > self._max_pending:
            raise AuthError("busy", "Logowanie jest zajęte. Spróbuj za chwilę.", 429)
        now = self._clock()
        for key, limit in limits:
            attempts = self._attempts.setdefault(key, deque())
            while attempts and attempts[0] <= now - 60:
                attempts.popleft()
            if len(attempts) >= limit:
                raise AuthError("rate_limited", "Za dużo prób logowania. Poczekaj minutę.", 429)
        for key, _ in limits:
            self._attempts[key].append(now)

    def start(self, browser_binding: str | None = None):
        self._require_enabled()
        self._prune()
        if _binding_hash(browser_binding) is None:
            browser_binding = secrets.token_urlsafe(32)
        binding = _binding_hash(browser_binding)
        # Reloading the page invalidates the oldest challenge after four tabs,
        # rather than leaving a browser locked out for the full five minutes.
        owned = [key for key, value in self._challenges.items() if value.binding == binding]
        for key in owned[:-3]:
            self._challenges.pop(key, None)
        if len(self._challenges) >= self._max_pending:
            raise AuthError("busy", "Logowanie jest zajęte. Spróbuj za chwilę.", 503)
        challenge, nonce = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        self._challenges[challenge] = _Challenge(nonce, binding, self._clock() + AUTH_TTL)
        return {"challenge": challenge, "nonce": nonce, "expires_in": AUTH_TTL}, browser_binding

    def _validate_claims(self, claims, nonce: str):
        if not isinstance(claims, dict):
            raise ValueError("Invalid claims")
        if claims.get("aud") != self.client_id or claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise ValueError("Invalid issuer/audience")
        now = self._wall_clock()
        for name in ("iat", "exp"):
            value = claims.get(name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                raise ValueError("Invalid token time")
        if claims["iat"] > now or claims["exp"] <= now or claims["iat"] >= claims["exp"]:
            raise ValueError("Invalid token time")
        sub = claims.get("sub")
        if not isinstance(sub, str) or not 1 <= len(sub) <= 255 or not sub.isascii() or any(c.isspace() or not 33 <= ord(c) <= 126 for c in sub):
            raise ValueError("Invalid subject")
        token_nonce = claims.get("nonce")
        if not isinstance(token_nonce, str) or not _TOKEN_RE.fullmatch(token_nonce) or not hmac.compare_digest(token_nonce, nonce):
            raise ValueError("Invalid nonce")
        return GoogleIdentity(sub)

    async def verify(self, challenge, credential, browser_binding=None):
        self._require_enabled()
        self._prune()
        if not isinstance(challenge, str) or not _TOKEN_RE.fullmatch(challenge):
            raise AuthError("invalid_challenge", "Logowanie wygasło. Wybierz Google ponownie.", 401)
        # Burn the challenge on every verification attempt, including malformed
        # credentials and mismatched cookies. It can never authorize a replay.
        pending = self._challenges.pop(challenge, None)
        binding = _binding_hash(browser_binding)
        if pending is None or binding is None or not hmac.compare_digest(pending.binding, binding):
            raise AuthError("invalid_challenge", "Logowanie wygasło. Wybierz Google ponownie.", 401)
        if not isinstance(credential, str) or not 32 <= len(credential) <= MAX_CREDENTIAL or credential.count(".") != 2:
            raise AuthError("invalid_credential", "Nie udało się potwierdzić konta Google. Spróbuj ponownie.", 401)
        if self._inflight >= MAX_VERIFY_WORKERS:
            raise AuthError("busy", "Logowanie jest zajęte. Spróbuj za chwilę.", 429)
        if len(self._tickets) >= self._max_pending:
            raise AuthError("busy", "Logowanie jest zajęte. Spróbuj za chwilę.", 503)
        self._inflight += 1
        worker = asyncio.create_task(asyncio.to_thread(self._verifier, credential))
        try:
            try:
                claims = await asyncio.shield(worker)
            except asyncio.CancelledError:
                # Keep the worker slot occupied until the bounded network call
                # finishes, so disconnected clients cannot spawn extra workers.
                try:
                    await worker
                except Exception:
                    pass
                raise
            identity = self._validate_claims(claims, pending.nonce)
        except asyncio.CancelledError:
            raise
        except Exception:
            # Do not reflect Google token/claims or verification exception text.
            raise AuthError("invalid_credential", "Nie udało się potwierdzić konta Google. Spróbuj ponownie.", 401) from None
        finally:
            self._inflight -= 1
        if pending.expires <= self._clock():
            raise AuthError("invalid_challenge", "Logowanie wygasło. Wybierz Google ponownie.", 401)
        if len(self._tickets) >= self._max_pending:
            raise AuthError("busy", "Logowanie jest zajęte. Spróbuj za chwilę.", 503)
        ticket = secrets.token_urlsafe(32)
        self._tickets[ticket] = _Ticket(identity, binding, self._clock() + AUTH_TTL)
        return {"ticket": ticket, "expires_in": AUTH_TTL}, identity

    def peek_ticket(self, ticket, browser_binding=None):
        self._require_enabled()
        self._prune()
        if not isinstance(ticket, str) or not _TOKEN_RE.fullmatch(ticket):
            raise AuthError("invalid_ticket", "Logowanie wygasło. Wybierz Google ponownie.", 401)
        entry, binding = self._tickets.get(ticket), _binding_hash(browser_binding)
        if entry is None or binding is None or not hmac.compare_digest(entry.binding, binding):
            raise AuthError("invalid_ticket", "Logowanie wygasło. Wybierz Google ponownie.", 401)
        return entry.identity

    def consume_ticket(self, ticket, browser_binding=None):
        identity = self.peek_ticket(ticket, browser_binding)
        self._tickets.pop(ticket)
        return identity

    def close(self):
        self._challenges.clear()
        self._tickets.clear()
        self._attempts.clear()
        close = getattr(self._verifier, "close", None)
        if close:
            close()


async def _read_json(request):
    # Auth HTTP accepts a larger credential than the game's 2048-byte WS limit.
    # Read the stream with an independent hard cap, including chunked requests.
    if request.content_length is not None and request.content_length > MAX_AUTH_BODY:
        raise AuthError("request_too_large", "Zbyt duży komunikat logowania.", 413)
    data = bytearray()
    async for chunk in request.content.iter_chunked(4096):
        data.extend(chunk)
        if len(data) > MAX_AUTH_BODY:
            raise AuthError("request_too_large", "Zbyt duży komunikat logowania.", 413)
    try:
        payload = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise AuthError("invalid_request", "Nieprawidłowy komunikat logowania.") from None
    if not isinstance(payload, dict):
        raise AuthError("invalid_request", "Nieprawidłowy komunikat logowania.")
    return payload


def register_routes(app, service: GoogleAuthService, account_info=None):
    """Register routes; ``account_info(sub)`` returns the verified account roster."""
    async def config(request):
        payload = {"enabled": service.enabled}
        if service.enabled:
            payload["client_id"] = service.client_id
        return web.json_response(payload, headers=_HEADERS)

    async def start(request):
        try:
            service.check_request(request)
            await _read_json(request)
            payload, binding = service.start(request.cookies.get(service.cookie_name))
            response = web.json_response(payload, headers=_HEADERS)
            response.set_cookie(service.cookie_name, binding, max_age=3600, path="/", httponly=True,
                                secure=service.allowed_origin.startswith("https://"), samesite="Strict")
            return response
        except AuthError as exc:
            return web.json_response({"error": exc.code, "message": exc.message}, status=exc.status, headers=_HEADERS)

    async def verify(request):
        try:
            service.check_request(request)
            data = await _read_json(request)
            payload, identity = await service.verify(data.get("challenge"), data.get("credential"),
                                                      request.cookies.get(service.cookie_name))
            payload["account"] = account_info(identity.sub) if account_info else {"characters": [], "max_characters": 4}
            return web.json_response(payload, headers=_HEADERS)
        except AuthError as exc:
            return web.json_response({"error": exc.code, "message": exc.message}, status=exc.status, headers=_HEADERS)

    async def cleanup(_app):
        service.close()

    app.router.add_get("/auth/google/config", config)
    app.router.add_post("/auth/google/start", start)
    app.router.add_post("/auth/google/verify", verify)
    app.on_cleanup.append(cleanup)
