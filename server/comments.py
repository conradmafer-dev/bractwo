"""Public comments with verified Google sessions and character ownership.

Google credentials never enter this module. The Google verify route alone calls
``on_verified`` with the verified subject. Browser session tokens are opaque,
stored only as hashes in bounded memory, and expire after eight hours. Comments
and posting limits share the game's SQLite connection and survive a restart.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from html import escape
import hashlib
import json
import math
import re
import secrets
import time
import unicodedata

from aiohttp import web

try:
    from .google_auth import _configured_origin
    from .profanity import contains_profanity
except ImportError:
    from google_auth import _configured_origin
    from profanity import contains_profanity


SESSION_TTL = 8 * 60 * 60
MAX_SESSIONS = 4096
MAX_ACCOUNT_SESSIONS = 4
MAX_LENGTH = 1000
MAX_BODY_BYTES = 16384
PAGE_SIZE = 20
COOLDOWN_SECONDS = 30
HOURLY_LIMIT = 20
DUPLICATE_WINDOW = 24 * 60 * 60
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{43}$")
_ID_RE = re.compile(r"^[1-9][0-9]{0,18}$")
_HEADERS = {"Cache-Control": "no-store", "Vary": "Cookie",
            "X-Content-Type-Options": "nosniff", "X-Robots-Tag": "noindex, nofollow"}


class CommentError(Exception):
    def __init__(self, code, message, status=400, retry_after=None):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
        self.retry_after = retry_after


@dataclass(frozen=True)
class _Session:
    account_id: int
    expires: float


def _token_hash(value):
    if not isinstance(value, str) or not _TOKEN_RE.fullmatch(value):
        return None
    return hashlib.sha256(value.encode("ascii")).digest()


def _identifier(value):
    if not isinstance(value, str) or not _ID_RE.fullmatch(value):
        return None
    number = int(value)
    return number if number <= 9223372036854775807 else None


def _timestamp(value):
    return datetime.fromtimestamp(value, timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _clean_body(value):
    if not isinstance(value, str):
        raise CommentError("invalid_body", "Komentarz musi być tekstem od 3 do 1000 znaków.")
    # Remove invisible direction/format controls rather than letting them hide
    # words. Newlines and tabs remain plain text; reject other control codes.
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    if any(unicodedata.category(char) in ("Cc", "Cs") and char not in "\n\t" for char in value):
        raise CommentError("invalid_body", "Komentarz zawiera niedozwolone znaki sterujące.")
    value = unicodedata.normalize("NFC", "".join(char for char in value if unicodedata.category(char) != "Cf")).strip()
    if not 3 <= len(value) <= MAX_LENGTH:
        raise CommentError("invalid_body", "Komentarz musi mieć od 3 do 1000 znaków.")
    return value


def _safe_author(value, check=contains_profanity):
    if not isinstance(value, str) or not value.strip() or check(value):
        return "Gracz Bractwa Krain"
    if any(unicodedata.category(char) in ("Cc", "Cf", "Cs") for char in value):
        return "Gracz Bractwa Krain"
    return value


class CommentService:
    """Owned by the event loop, like the game's shared SQLite connection."""

    def __init__(self, db, allowed_origin, *, clock=time.monotonic, wall_clock=time.time,
                 max_sessions=MAX_SESSIONS):
        self.db = db
        self.allowed_origin = _configured_origin(allowed_origin)
        self.secure = self.allowed_origin.startswith("https://")
        self.cookie_name = "__Host-bractwo_comments" if self.secure else "bractwo_comments_local"
        self._clock, self._wall_clock = clock, wall_clock
        self._max_sessions = max(1, int(max_sessions))
        self._sessions = {}
        # Bodies are immutable. Rechecking legacy rows after a deploy is useful,
        # but repeated public reads must not rerun moderation on the game loop.
        self._contains_profanity = lru_cache(maxsize=4096)(contains_profanity)
        self.db.executescript("""
          CREATE TABLE IF NOT EXISTS public_comments(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            google_account_id INTEGER NOT NULL REFERENCES google_accounts(id),
            character_id INTEGER NOT NULL REFERENCES accounts(id),
            author TEXT NOT NULL,
            body TEXT NOT NULL,
            created_at REAL NOT NULL
          );
          CREATE TABLE IF NOT EXISTS comment_post_events(
            google_account_id INTEGER NOT NULL REFERENCES google_accounts(id),
            body_hash TEXT NOT NULL,
            created_at REAL NOT NULL,
            PRIMARY KEY(google_account_id, body_hash)
          );
          CREATE INDEX IF NOT EXISTS comment_post_events_account_time
            ON comment_post_events(google_account_id, created_at);
          CREATE INDEX IF NOT EXISTS comment_post_events_time
            ON comment_post_events(created_at);
        """)

    def _prune_sessions(self):
        now = self._clock()
        self._sessions = {key: session for key, session in self._sessions.items() if session.expires > now}

    def account_for_request(self, request):
        self._prune_sessions()
        session = self._sessions.get(_token_hash(request.cookies.get(self.cookie_name)))
        return session.account_id if session is not None else None

    def require_account(self, request):
        account_id = self.account_for_request(request)
        if account_id is None:
            raise CommentError("unauthenticated", "Zaloguj się przez Google, aby dodać komentarz.", 401)
        return account_id

    def on_verified(self, request, response, identity):
        """Hook called only after Google's subject/nonce/signature validation."""
        self._prune_sessions()
        self._sessions.pop(_token_hash(request.cookies.get(self.cookie_name)), None)
        # google_account_info normally creates this row immediately before the
        # hook. Keeping the insert idempotent also supports a fresh account.
        with self.db:
            self.db.execute("INSERT OR IGNORE INTO google_accounts(subject,created_at) VALUES(?,?)",
                            (identity.sub, self._wall_clock()))
        account_id = self.db.execute("SELECT id FROM google_accounts WHERE subject=?", (identity.sub,)).fetchone()[0]
        owned = [key for key, session in self._sessions.items() if session.account_id == account_id]
        for key in owned[:max(0, len(owned) - MAX_ACCOUNT_SESSIONS + 1)]:
            self._sessions.pop(key, None)
        while len(self._sessions) >= self._max_sessions:
            self._sessions.pop(next(iter(self._sessions)))
        token = secrets.token_urlsafe(32)
        self._sessions[_token_hash(token)] = _Session(account_id, self._clock() + SESSION_TTL)
        response.set_cookie(self.cookie_name, token, max_age=SESSION_TTL, path="/",
                            secure=self.secure, httponly=True, samesite="Strict")

    def check_mutation(self, request, *, json_body=False):
        if (not self.allowed_origin or request.headers.getall("Origin", []) != [self.allowed_origin]
                or request.headers.getall("X-Bractwo-Comments", []) != ["1"]
                or request.headers.get("Sec-Fetch-Site", "").lower() == "cross-site"):
            raise CommentError("invalid_origin", "Otwórz komentarze na właściwej stronie gry.", 403)
        if json_body and request.content_type != "application/json":
            raise CommentError("invalid_request", "Wymagany komunikat JSON.", 415)

    def session_payload(self, request):
        account_id = self.account_for_request(request)
        characters = []
        if account_id is not None:
            characters = [{"id": str(pid), "name": _safe_author(name, self._contains_profanity)} for pid, name in self.db.execute(
                "SELECT a.id,a.name FROM accounts a JOIN google_characters g ON g.character_id=a.id "
                "WHERE g.google_account_id=? ORDER BY a.id", (account_id,))]
        return {"authenticated": account_id is not None, "characters": characters, "max_length": MAX_LENGTH}

    def list_comments(self, *, cursor=None, limit=PAGE_SIZE, account_id=None):
        # Scan a bounded batch to omit content rejected by an updated filter.
        # A cursor still advances when a batch contains only hidden old rows.
        rows = self.db.execute(
            "SELECT id,google_account_id,author,body,created_at FROM public_comments "
            "WHERE id < ? ORDER BY id DESC LIMIT 100",
            (cursor if cursor is not None else 9223372036854775807,)).fetchall()
        items = []
        for comment_id, owner, author, body, created_at in rows:
            if self._contains_profanity(body):
                continue
            items.append({"id": str(comment_id), "author": _safe_author(author, self._contains_profanity), "body": body,
                          "created_at": _timestamp(created_at), "can_delete": owner == account_id})
            if len(items) > limit:
                return {"items": items[:limit], "next_cursor": items[limit - 1]["id"]}
        next_cursor = str(rows[-1][0]) if len(rows) == 100 else None
        return {"items": items, "next_cursor": next_cursor}

    def create_comment(self, account_id, character_id, body):
        character_id = _identifier(character_id)
        if character_id is None:
            raise CommentError("invalid_character", "Wybierz swoją postać w grze.")
        character = self.db.execute(
            "SELECT a.name FROM accounts a JOIN google_characters g ON g.character_id=a.id "
            "WHERE a.id=? AND g.google_account_id=?", (character_id, account_id)).fetchone()
        if character is None:
            raise CommentError("forbidden", "Możesz pisać wyłącznie jako własna postać.", 403)
        body = _clean_body(body)
        now = self._wall_clock()
        body_hash = hashlib.sha256(" ".join(body.casefold().split()).encode("utf-8")).hexdigest()
        # No await occurs in this transaction. Posting and rate events commit
        # together; removing a comment cannot reset cooldown or duplicate checks.
        with self.db:
            self.db.execute("DELETE FROM comment_post_events WHERE created_at <= ?", (now - DUPLICATE_WINDOW,))
            if self.db.execute("SELECT 1 FROM comment_post_events WHERE google_account_id=? AND body_hash=?",
                               (account_id, body_hash)).fetchone():
                raise CommentError("duplicate", "Taki komentarz został już dodany. Napisz coś nowego.", 409)
            events = self.db.execute(
                "SELECT created_at FROM comment_post_events WHERE google_account_id=? AND created_at > ? "
                "ORDER BY created_at", (account_id, now - 3600)).fetchall()
            if events and events[-1][0] + COOLDOWN_SECONDS > now:
                retry = max(1, math.ceil(events[-1][0] + COOLDOWN_SECONDS - now))
                raise CommentError("rate_limited", "Poczekaj chwilę przed dodaniem kolejnego komentarza.", 429, retry)
            if len(events) >= HOURLY_LIMIT:
                retry = max(1, math.ceil(events[0][0] + 3600 - now))
                raise CommentError("rate_limited", "Osiągnięto limit 20 komentarzy na godzinę. Spróbuj później.", 429, retry)
            # Reject rate-limited requests before doing the more expensive text
            # filtering. Successful bodies also warm the cache for public reads.
            if self._contains_profanity(body):
                raise CommentError("profanity", "Usuń wulgaryzmy z komentarza i spróbuj ponownie.")
            author = _safe_author(character[0], self._contains_profanity)
            result = self.db.execute(
                "INSERT INTO public_comments(google_account_id,character_id,author,body,created_at) VALUES(?,?,?,?,?)",
                (account_id, character_id, author, body, now))
            self.db.execute("INSERT INTO comment_post_events(google_account_id,body_hash,created_at) VALUES(?,?,?)",
                            (account_id, body_hash, now))
        return {"id": str(result.lastrowid), "author": author, "body": body,
                "created_at": _timestamp(now), "can_delete": True}

    def delete_comment(self, account_id, comment_id):
        comment_id = _identifier(comment_id)
        row = self.db.execute("SELECT google_account_id FROM public_comments WHERE id=?", (comment_id,)).fetchone()
        if row is None:
            raise CommentError("not_found", "Nie znaleziono komentarza.", 404)
        if row[0] != account_id:
            raise CommentError("forbidden", "Możesz usuwać tylko własne komentarze.", 403)
        with self.db:
            self.db.execute("DELETE FROM public_comments WHERE id=? AND google_account_id=?", (comment_id, account_id))

    def logout(self, request, response):
        self._sessions.pop(_token_hash(request.cookies.get(self.cookie_name)), None)
        response.set_cookie(self.cookie_name, "", max_age=0, expires="Thu, 01 Jan 1970 00:00:00 GMT",
                            path="/", secure=self.secure, httponly=True, samesite="Strict")

    def render_public_list(self):
        """Safe public HTML, identical for every visitor and search crawler."""
        items = self.list_comments()["items"]
        if not items:
            return '<li class="comments-empty">Brak komentarzy. Podziel się pierwszym wrażeniem z gry.</li>'
        return "\n".join(
            f'<li class="comment-item" data-comment-id="{escape(item["id"], quote=True)}"><article>'
            f'<header><strong>{escape(item["author"])}</strong>'
            f'<time datetime="{item["created_at"]}">{item["created_at"][:10]}</time></header>'
            f'<p class="comment-body">{escape(item["body"])}</p></article></li>' for item in items)

    def close(self):
        self._sessions.clear()
        self._contains_profanity.cache_clear()


async def _read_json(request):
    # Read the stream with an independent cap: the game's WS limit is 2 KiB,
    # while a 1000-character JSON comment can exceed it when Unicode-escaped.
    if request.content_length is not None and request.content_length > MAX_BODY_BYTES:
        raise CommentError("request_too_large", "Komentarz jest zbyt duży.", 413)
    data = bytearray()
    async for chunk in request.content.iter_chunked(4096):
        data.extend(chunk)
        if len(data) > MAX_BODY_BYTES:
            raise CommentError("request_too_large", "Komentarz jest zbyt duży.", 413)
    try:
        payload = json.loads(data, parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError, RecursionError):
        raise CommentError("invalid_request", "Nieprawidłowy komunikat JSON.") from None
    if not isinstance(payload, dict):
        raise CommentError("invalid_request", "Nieprawidłowy komunikat JSON.")
    return payload


def register_routes(app, service):
    def result(payload, *, status=200):
        return web.json_response(payload, status=status, headers=_HEADERS)

    def failure(exc):
        payload = {"error": exc.code, "message": exc.message}
        if exc.retry_after is not None:
            payload["retry_after"] = exc.retry_after
        response = result(payload, status=exc.status)
        if exc.retry_after is not None:
            response.headers["Retry-After"] = str(exc.retry_after)
        return response

    async def listing(request):
        cursor = request.query.get("cursor")
        limit = request.query.get("limit", str(PAGE_SIZE))
        if (cursor is not None and _identifier(cursor) is None
                or not re.fullmatch(r"[1-9][0-9]?", limit) or int(limit) > PAGE_SIZE):
            return failure(CommentError("invalid_cursor", "Nieprawidłowa strona komentarzy."))
        return result(service.list_comments(cursor=int(cursor) if cursor else None, limit=int(limit),
                                            account_id=service.account_for_request(request)))

    async def session(request):
        return result(service.session_payload(request))

    async def create(request):
        try:
            service.check_mutation(request, json_body=True)
            account_id = service.require_account(request)
            data = await _read_json(request)
            return result({"item": service.create_comment(account_id, data.get("character_id"), data.get("body"))}, status=201)
        except CommentError as exc:
            return failure(exc)

    async def delete(request):
        try:
            service.check_mutation(request)
            service.delete_comment(service.require_account(request), request.match_info["comment_id"])
            return result({"deleted": True})
        except CommentError as exc:
            return failure(exc)

    async def logout(request):
        try:
            service.check_mutation(request, json_body=True)
            await _read_json(request)
            response = result({"authenticated": False})
            service.logout(request, response)
            return response
        except CommentError as exc:
            return failure(exc)

    async def cleanup(_app):
        service.close()

    app.router.add_get("/api/comments", listing)
    app.router.add_get("/api/comments/session", session)
    app.router.add_post("/api/comments", create)
    app.router.add_post("/api/comments/logout", logout)
    app.router.add_delete("/api/comments/{comment_id}", delete)
    app.on_cleanup.append(cleanup)
