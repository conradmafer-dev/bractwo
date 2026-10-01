"""Public, server-rendered metadata for the game and its player guides.

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
TITLE = "Bractwo Krain — polskie MMORPG z mechaniką D&D"
DESCRIPTION = ("Bractwo Krain — polskie MMORPG i gra w przeglądarce z mechaniką "
               "Dungeons & Dragons (D&D). Rozwijaj postać, wybieraj atuty i odkrywaj kręgi czarów.")
IMAGE_PATH = "/assets/seo/bractwo-krain-og.png"
IMAGE_ALT = "Zrzut gry Bractwo Krain: Solna Przystań i pustynna kraina"
HEAD_MARKER = "<!-- SEO_HEAD -->"


@dataclass(frozen=True)
class PublicPage:
    """A published document; this registry also defines the sitemap and routes."""

    path: str
    template: str
    title: str
    description: str
    name: str


HOME_PAGE = PublicPage("/", "index.html", TITLE, DESCRIPTION, "Bractwo Krain")
PUBLIC_PAGES = (
    HOME_PAGE,
    PublicPage(
        "/poradniki/jak-zaczac", "poradniki/jak-zaczac.html",
        "Jak zacząć grać w Bractwo Krain? Poradnik dla początkujących",
        "Pierwsze kroki w Bractwie Krain: logowanie przez Google, wybór klasy, "
        "sterowanie i pierwsza wyprawa. Poznaj polską grę RPG online w przeglądarce.",
        "Jak zacząć grać",
    ),
    PublicPage(
        "/poradniki/klasy-postaci", "poradniki/klasy-postaci.html",
        "Klasy postaci w Bractwie Krain – rycerz, łowca, czarodziej i druid",
        "Porównaj cztery klasy postaci w Bractwie Krain. Poznaj styl walki rycerza, "
        "łowcy, czarodzieja i druida oraz wybierz bohatera na pierwszą przygodę.",
        "Klasy postaci",
    ),
    PublicPage(
        "/poradniki/swiat-i-wyprawy", "poradniki/swiat-i-wyprawy.html",
        "Świat i wyprawy w Bractwie Krain – krainy, podziemia i drużyny",
        "Odkrywaj świat Bractwa Krain: osady, wyspy, podziemia i wyprawy po łupy. "
        "Dowiedz się, jak przygotować bohatera i współpracować z innymi graczami.",
        "Świat i wyprawy",
    ),
)


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


def metadata_head(config, page=HOME_PAGE):
    """Generate the crawlable head without user/session data or inline code."""
    canonical = config.origin + page.path
    homepage = config.canonical
    image = config.origin + IMAGE_PATH
    attributes = [
        ("property", "og:type", "website"),
        ("property", "og:locale", "pl_PL"),
        ("property", "og:site_name", "Bractwo Krain"),
        ("property", "og:title", page.title),
        ("property", "og:description", page.description),
        ("property", "og:url", canonical),
        ("property", "og:image", image),
        ("property", "og:image:type", "image/png"),
        ("property", "og:image:width", "1920"),
        ("property", "og:image:height", "1080"),
        ("property", "og:image:alt", IMAGE_ALT),
        ("name", "twitter:card", "summary_large_image"),
        ("name", "twitter:title", page.title),
        ("name", "twitter:description", page.description),
        ("name", "twitter:image", image),
        ("name", "twitter:image:alt", IMAGE_ALT),
    ]
    if config.google_verification:
        attributes.append(("name", "google-site-verification", config.google_verification))
    lines = [
        f'<title>{escape(page.title)}</title>',
        f'<meta name="description" content="{escape(page.description, quote=True)}">',
        '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">',
        f'<link rel="canonical" href="{escape(canonical, quote=True)}">',
    ]
    lines.extend(f'<meta {kind}="{name}" content="{escape(value, quote=True)}">'
                 for kind, name, value in attributes)
    webpage = {
        "@type": "WebPage", "@id": canonical + "#webpage", "url": canonical,
        "name": page.title, "description": page.description, "inLanguage": "pl-PL",
        "isPartOf": {"@id": homepage + "#website"},
        "about": {"@id": homepage + "#game"},
        "primaryImageOfPage": {"@id": homepage + "#image"},
    }
    if page.path == "/":
        webpage["mainEntity"] = {"@id": homepage + "#game"}
    else:
        webpage["breadcrumb"] = {"@id": canonical + "#breadcrumb"}
    structured = {"@context": "https://schema.org", "@graph": [webpage]}
    if page.path == "/":
        structured["@graph"].extend([
            {"@type": "WebSite", "@id": homepage + "#website", "url": homepage,
             "name": "Bractwo Krain", "inLanguage": "pl-PL", "description": DESCRIPTION},
            {"@type": "ImageObject", "@id": homepage + "#image", "url": image,
             "contentUrl": image, "width": 1920, "height": 1080, "caption": IMAGE_ALT},
            {"@type": "VideoGame", "@id": homepage + "#game", "url": homepage,
             "name": "Bractwo Krain", "description": DESCRIPTION,
             "keywords": ["polskie MMORPG", "gra w przeglądarce", "Dungeons & Dragons",
                          "D&D", "SRD 5.2.1", "RPG online"],
             "image": {"@id": homepage + "#image"},
             "inLanguage": "pl-PL", "genre": "RPG", "gamePlatform": "Web browser",
             "playMode": "https://schema.org/MultiPlayer",
             "isPartOf": {"@id": homepage + "#website"}},
        ])
    else:
        structured["@graph"].append({
            "@type": "BreadcrumbList", "@id": canonical + "#breadcrumb",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Bractwo Krain", "item": homepage},
                {"@type": "ListItem", "position": 2, "name": page.name, "item": canonical},
            ],
        })
    # A JSON script remains safe even if future editable text contains </script>.
    payload = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    lines.append(f'<script type="application/ld+json">{payload}</script>')
    return "\n".join(lines)


def render_index(template, config):
    """Replace only the explicit template marker, leaving the app shell intact."""
    return render_page(template, config, HOME_PAGE)


def render_page(template, config, page):
    """Use the same document for visitors, previews and search engine crawlers."""
    return template.replace(HEAD_MARKER, metadata_head(config, page), 1)


def robots_txt(config):
    # Technical endpoints send X-Robots-Tag: noindex. Crawlers must be allowed
    # to fetch that header; Disallow alone can leave their URLs in the index.
    return ("User-agent: *\nAllow: /\n\n"
            f"Sitemap: {config.origin}/sitemap.xml\n")


def sitemap_xml(config):
    urls = "".join(f'  <url><loc>{escape(config.origin + page.path)}</loc></url>\n'
                   for page in PUBLIC_PAGES)
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            f'{urls}</urlset>\n')
