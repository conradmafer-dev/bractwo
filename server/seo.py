"""Public, server-rendered metadata for the game entry page.

PUBLIC_SITE_URL is a deployment setting, never a request Host header. Invalid
origins fall back to the existing public Railway URL rather than generating
broken or attacker-controlled canonical, social or sitemap URLs.
"""
from __future__ import annotations

from dataclasses import dataclass
from html import escape
from ipaddress import ip_address
import json
import os
import re
from urllib.parse import urlsplit


DEFAULT_ORIGIN = "https://bractwo.up.railway.app"
TITLE = "Bractwo Krain – polska gra RPG online w przeglądarce"
DESCRIPTION = ("Polska gra RPG online w przeglądarce. Wybierz jedną z czterech klas, "
               "odkrywaj krainy i podziemia, zdobywaj łupy i graj z innymi.")
IMAGE_PATH = "/assets/seo/bractwo-krain-og.png"
IMAGE_ALT = "Zrzut gry Bractwo Krain: Solna Przystań i pustynna kraina"
HEAD_MARKER = "<!-- SEO_HEAD -->"


def public_origin(value):
    """Return a normalized HTTP(S) origin; reject credentials and URL suffixes."""
    if not isinstance(value, str) or not value:
        return DEFAULT_ORIGIN
    value = value.strip()
    if not value or any(char.isspace() or ord(char) < 32 for char in value) or "\\" in value:
        return DEFAULT_ORIGIN
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None
                or parsed.path not in ("", "/") or parsed.query or parsed.fragment
                or "?" in value or "#" in value):
            return DEFAULT_ORIGIN
        host = parsed.hostname
        if "%" in host:
            return DEFAULT_ORIGIN
        port = parsed.port  # also validates malformed ports / IPv6
        if port is not None and not 1 <= port <= 65535:
            return DEFAULT_ORIGIN
        try:
            address = ip_address(host)
            host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            host = host.encode("idna").decode("ascii").lower()
            if (len(host) > 253 or not all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                          for label in host.split("."))):
                return DEFAULT_ORIGIN
        default_port = 443 if parsed.scheme == "https" else 80
        suffix = f":{port}" if port is not None and port != default_port else ""
        return f"{parsed.scheme}://{host}{suffix}"
    except (ValueError, UnicodeError):
        return DEFAULT_ORIGIN


@dataclass(frozen=True)
class SEOConfig:
    origin: str = DEFAULT_ORIGIN
    google_verification: str = ""

    @classmethod
    def from_env(cls, environ=None):
        environ = os.environ if environ is None else environ
        return cls(public_origin(environ.get("PUBLIC_SITE_URL", DEFAULT_ORIGIN)),
                   str(environ.get("GOOGLE_SITE_VERIFICATION", "")).strip())

    @property
    def canonical(self):
        return self.origin + "/"


def metadata_head(config):
    """Generate the crawlable head without user/session data or inline code."""
    canonical = config.canonical
    image = config.origin + IMAGE_PATH
    attributes = [
        ("property", "og:type", "website"),
        ("property", "og:locale", "pl_PL"),
        ("property", "og:site_name", "Bractwo Krain"),
        ("property", "og:title", TITLE),
        ("property", "og:description", DESCRIPTION),
        ("property", "og:url", canonical),
        ("property", "og:image", image),
        ("property", "og:image:type", "image/png"),
        ("property", "og:image:width", "1920"),
        ("property", "og:image:height", "1080"),
        ("property", "og:image:alt", IMAGE_ALT),
        ("name", "twitter:card", "summary_large_image"),
        ("name", "twitter:title", TITLE),
        ("name", "twitter:description", DESCRIPTION),
        ("name", "twitter:image", image),
        ("name", "twitter:image:alt", IMAGE_ALT),
    ]
    if config.google_verification:
        attributes.append(("name", "google-site-verification", config.google_verification))
    lines = [f'<link rel="canonical" href="{escape(canonical, quote=True)}">']
    lines.extend(f'<meta {kind}="{name}" content="{escape(value, quote=True)}">'
                 for kind, name, value in attributes)
    structured = {
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": canonical + "#website", "url": canonical,
             "name": "Bractwo Krain", "inLanguage": "pl-PL", "description": DESCRIPTION},
            {"@type": "VideoGame", "@id": canonical + "#game", "url": canonical,
             "name": "Bractwo Krain", "description": DESCRIPTION, "image": image,
             "inLanguage": "pl-PL", "genre": "RPG", "gamePlatform": "Web browser",
             "playMode": "https://schema.org/MultiPlayer",
             "isPartOf": {"@id": canonical + "#website"}},
        ],
    }
    # A JSON script remains safe even if future editable text contains </script>.
    payload = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    lines.append(f'<script type="application/ld+json">{payload}</script>')
    return "\n".join(lines)


def render_index(template, config):
    """Replace only the explicit template marker, leaving the app shell intact."""
    return template.replace(HEAD_MARKER, metadata_head(config), 1)


def robots_txt(config):
    return ("User-agent: *\nAllow: /\nDisallow: /auth/\nDisallow: /ws\n"
            "Disallow: /health\nDisallow: /ranking\n\n"
            f"Sitemap: {config.origin}/sitemap.xml\n")


def sitemap_xml(config):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'  <url><loc>{escape(config.canonical)}</loc></url>\n'
            '</urlset>\n')
