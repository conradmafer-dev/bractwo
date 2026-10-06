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
class PageImage:
    """The publicly served image actually illustrating a document."""

    path: str
    alt: str
    width: int
    height: int
    mime_type: str = "image/webp"


DEFAULT_IMAGE = PageImage(IMAGE_PATH, IMAGE_ALT, 1920, 1080, "image/png")


@dataclass(frozen=True)
class PublicPage:
    """A published document; this registry also defines the sitemap and routes."""

    path: str
    template: str
    title: str
    description: str
    name: str
    published_date: str | None = None
    category: str | None = None
    article_kind: str = "BlogPosting"
    image: PageImage | None = None


HOME_PAGE = PublicPage("/", "index.html", TITLE, DESCRIPTION, "Bractwo Krain")
BLOG_PAGE = PublicPage(
    "/blog", "blog/index.html",
    "Blog D&D i newsy MMORPG | Bractwo Krain",
    "Poznaj D&D online po polsku: zasady k20, Klasa Pancerza, magia i atuty. "
    "Czytaj poradniki Bractwa Krain i sprawdzone aktualności ze świata MMORPG.",
    "Blog D&D i aktualności MMORPG",
)
BLOG_ARTICLES = (
    PublicPage(
        "/blog/dnd-online", "blog/dnd-online.html",
        "D&D online po polsku — sesja RPG czy gra w przeglądarce? | Bractwo Krain",
        "Jak grać w D&D online po polsku? Porównaj sesję z Mistrzem Gry, wirtualny "
        "stół i MMORPG w przeglądarce. Poznaj zasady D&D zaadaptowane w Bractwie Krain.",
        "D&D online po polsku — sesja RPG czy gra w przeglądarce?",
        published_date="2026-10-04", category="D&D online",
        image=PageImage(
            "/assets/screenshots/bractwo-krain-mmorpg-otwarty-swiat.png",
            "Czarodziej przy drodze i zabudowaniach w Bractwie Krain, polskim MMORPG z mechaniką D&D.",
            1920, 1080, "image/png",
        ),
    ),
    PublicPage(
        "/blog/walka-k20", "blog/walka-k20.html",
        "K20, Klasa Pancerza i trafienia krytyczne w D&D | Bractwo Krain",
        "Jak działa walka w D&D? Zrozum rzut k20, premię do ataku, Klasę Pancerza "
        "i trafienia krytyczne dzięki obliczeniom i przykładom z Bractwa Krain.",
        "K20, Klasa Pancerza i trafienia krytyczne — jak działa walka?",
        published_date="2026-10-04", category="Zasady D&D",
        image=PageImage(
            "/assets/screenshots/bractwo-krain-zlote-wybrzeze.png",
            "Walka w Bractwie Krain: czarodziej rzuca Błyskawicę w stronę minotaura i skorpiona na Złotym Wybrzeżu.",
            1920, 1080, "image/png",
        ),
    ),
    PublicPage(
        "/blog/magia-kregi-czarow", "blog/magia-kregi-czarow.html",
        "Czarodziej czy druid? Magia D&D w Bractwie Krain",
        "Kręgi czarów, rzuty obronne i koncentracja w D&D. Porównaj czarodzieja "
        "z druidem i poznaj adaptację magii do rozgrywki w Bractwie Krain.",
        "Czarodziej czy druid? Magia D&D w Bractwie Krain",
        published_date="2026-10-04", category="Magia D&D",
        image=PageImage(
            "/assets/screenshots/bractwo-krain-magiczny-pocisk.png",
            "Czarodziej rzuca Magiczny pocisk przy kamiennych ruinach w Bractwie Krain — czar znany z D&D.",
            1920, 1080, "image/png",
        ),
    ),
    PublicPage(
        "/blog/atuty-rozwoj-postaci", "blog/atuty-rozwoj-postaci.html",
        "Atuty w D&D i Bractwie — jak rozwijać bohatera? | Bractwo Krain",
        "Poznaj atuty, cechy i biegłości w D&D oraz ich rolę w rozwoju postaci. "
        "Zobacz, jak wybierać ulepszenia bohatera w Bractwie Krain.",
        "Atuty w D&D i Bractwie — jak rozwijać bohatera?",
        published_date="2026-10-04", category="Rozwój postaci",
        image=PageImage(
            "/assets/screenshots/bractwo-krain-druid-rozdarcie-demonow.png",
            "Druid w Rozdarciu Demonów w Bractwie Krain, z paskiem zaklęć i zdolności postaci u dołu ekranu.",
            1920, 1080, "image/png",
        ),
    ),
)
NEWS_ARTICLES = (
    PublicPage(
        "/blog/aion-2-rekord-steam-nagrody", "blog/aion-2-rekord-steam-nagrody.html",
        "AION 2: rekord Steam, darmowy voucher i nagrody | Bractwo Krain",
        "AION 2 po premierze: 397 905 graczy jednocześnie na Steam, darmowy Customization Voucher "
        "i prezenty za 400 tysięcy aktywnych użytkowników. Sprawdź źródła i menu Closet.",
        "AION 2: rekord na Steam i darmowy Customization Voucher po premierze",
        published_date="2026-10-06", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        image=PageImage("/assets/blog/aion-2-customization-voucher-oficjalna-800.webp",
                        "Zwierzęca postać w białym stroju obok logo AION 2 — oficjalna grafika komunikatu o Customization Voucher.", 800, 450),
    ),
    PublicPage(
        "/blog/aion-2-start-polska", "blog/aion-2-start-polska.html",
        "AION 2: start 5 października — godzina w Polsce | Bractwo Krain",
        "Globalny start AION 2 zaplanowano na 5 października 2026. Sprawdź godzinę w Polsce, "
        "harmonogram przerwy technicznej i zmiany w aktualizacji premierowej.",
        "AION 2: globalny start 5 października. O której ruszą serwery w Polsce?",
        published_date="2026-10-05", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        image=PageImage("/assets/blog/aion-2-start-skrzydla-ilustracja-1200.webp",
                        "Skrzydlata postać nad chmurami przed podniebną cytadelą — ilustracja redakcyjna do artykułu o starcie AION 2.", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-4-zapowiedz", "blog/runescape-4-zapowiedz.html",
        "RuneScape 4 zapowiedziane — nowe MMORPG i Ashenfall | Bractwo Krain",
        "Jagex zapowiedział RuneScape 4 z początkiem przygody w Ashenfall. "
        "Co ogłoszono o nowym MMORPG, czego jeszcze nie wiemy i co oznacza to dla graczy?",
        "RuneScape 4 zapowiedziane. Nowe MMORPG zacznie się w Ashenfall",
        published_date="2026-10-04", category="Newsy MMORPG · RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-4-wyprawa-ilustracja-1200.webp",
                        "Podróżnik patrzy ze skalnego tarasu na wulkaniczną dolinę — ilustracja do zapowiedzi RuneScape 4.", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-pluginy-beta", "blog/runescape-pluginy-beta.html",
        "RuneScape: beta pluginów 6 października i Quest Helper | Bractwo Krain",
        "Beta pluginów RuneScape rusza 6 października 2026. Quest Helper obejmie "
        "62 zadania. Poznaj potwierdzone informacje i ograniczenia testów.",
        "RuneScape: beta pluginów 6 października. Quest Helper z 62 zadaniami",
        published_date="2026-10-04", category="Newsy MMORPG · RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-pluginy-narzedzia-ilustracja-1200.webp",
                        "Kompas, mapa i modułowe narzędzia na drewnianym stole — ilustracja do artykułu o pluginach RuneScape.", 1200, 675),
    ),
    PublicPage(
        "/blog/ddo-court-of-strahd", "blog/ddo-court-of-strahd.html",
        "DDO: The Court of Strahd 14 października i Hardcore | Bractwo Krain",
        "14 października 2026 w Dungeons & Dragons Online startuje The Court of Strahd. "
        "Poznaj latarnie, zasady Hardcore i potwierdzone szczegóły wydarzenia.",
        "DDO: The Court of Strahd rusza 14 października. Latarnie i tryb Hardcore",
        published_date="2026-10-04", category="Newsy MMORPG · Dungeons & Dragons", article_kind="NewsArticle",
        image=PageImage("/assets/blog/ddo-court-of-strahd-latarnia-ilustracja-1200.webp",
                        "Latarnia rozświetla mgłę na drodze do gotyckiego zamku — ilustracja do zapowiedzi The Court of Strahd w DDO.", 1200, 675),
    ),
    PublicPage(
        "/blog/pantheon-crafting-2027", "blog/pantheon-crafting-2027.html",
        "Pantheon: crafting planowany na 2027 — Q&A 2 października | Bractwo Krain",
        "Q&A Pantheon z 2 października 2026: crafting planowany na 2027 rok. "
        "Sprawdzamy zapowiedzi twórców i rozróżniamy plany od gotowych funkcji.",
        "Pantheon: crafting planowany na 2027. Co ujawniono w Q&A z 2 października?",
        published_date="2026-10-04", category="Newsy MMORPG · Pantheon", article_kind="NewsArticle",
        image=PageImage("/assets/blog/pantheon-crafting-kuznia-ilustracja-1200.webp",
                        "Kuźnia fantasy z młotem, sztabkami metalu i niedokończonym mieczem — ilustracja do zapowiedzi craftingu w Pantheon.", 1200, 675),
    ),
)
ALL_BLOG_ARTICLES = (*NEWS_ARTICLES, *BLOG_ARTICLES)
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
    BLOG_PAGE,
    *ALL_BLOG_ARTICLES,
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
    is_news = page.article_kind == "NewsArticle"
    page_image = page.image or (None if is_news else DEFAULT_IMAGE)
    image_url = config.origin + page_image.path if page_image else None
    image_id = canonical + "#image" if page.image else homepage + "#image"
    attributes = [
        ("property", "og:type", "article" if page.published_date else "website"),
        ("property", "og:locale", "pl_PL"),
        ("property", "og:site_name", "Bractwo Krain"),
        ("property", "og:title", page.title),
        ("property", "og:description", page.description),
        ("property", "og:url", canonical),
        ("name", "twitter:card", "summary_large_image" if page_image else "summary"),
        ("name", "twitter:title", page.title),
        ("name", "twitter:description", page.description),
    ]
    if page_image:
        attributes.extend([
            ("property", "og:image", image_url),
            ("property", "og:image:type", page_image.mime_type),
            ("property", "og:image:width", str(page_image.width)),
            ("property", "og:image:height", str(page_image.height)),
            ("property", "og:image:alt", page_image.alt),
            ("name", "twitter:image", image_url),
            ("name", "twitter:image:alt", page_image.alt),
        ])
    if page.published_date:
        attributes.append(("property", "article:published_time", page.published_date))
        if page.category:
            attributes.append(("property", "article:section", page.category))
    if config.google_verification:
        attributes.append(("name", "google-site-verification", config.google_verification))
    lines = [
        f'<title>{escape(page.title)}</title>',
        f'<meta name="description" content="{escape(page.description, quote=True)}">',
        '<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1">',
        f'<link rel="canonical" href="{escape(canonical, quote=True)}">',
        '<link rel="icon" href="/favicon.ico" type="image/vnd.microsoft.icon" sizes="16x16 32x32 48x48 64x64 128x128 256x256">',
    ]
    lines.extend(f'<meta {kind}="{name}" content="{escape(value, quote=True)}">'
                 for kind, name, value in attributes)
    webpage = {
        "@type": "WebPage", "@id": canonical + "#webpage", "url": canonical,
        "name": page.title, "description": page.description, "inLanguage": "pl-PL",
        "isPartOf": {"@id": homepage + "#website"},
    }
    if not is_news:
        webpage["about"] = {"@id": homepage + "#game"}
    if page_image:
        webpage["primaryImageOfPage"] = {"@id": image_id}
    if page.path == "/":
        webpage["mainEntity"] = {"@id": homepage + "#game"}
    else:
        webpage["breadcrumb"] = {"@id": canonical + "#breadcrumb"}
        if page.published_date:
            webpage["mainEntity"] = {"@id": canonical + "#article"}
        elif page.path == BLOG_PAGE.path:
            webpage["mainEntity"] = {"@id": canonical + "#collection"}
    structured = {"@context": "https://schema.org", "@graph": [webpage]}
    if page_image and (page.image or page.path == "/"):
        structured["@graph"].append({
            "@type": "ImageObject", "@id": image_id, "url": image_url,
            "contentUrl": image_url, "width": page_image.width, "height": page_image.height,
            "encodingFormat": page_image.mime_type, "caption": page_image.alt,
        })
    if page.path == "/":
        structured["@graph"].extend([
            {"@type": "WebSite", "@id": homepage + "#website", "url": homepage,
             "name": "Bractwo Krain", "inLanguage": "pl-PL", "description": DESCRIPTION},
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
        breadcrumbs = [
            {"@type": "ListItem", "position": 1, "name": "Bractwo Krain", "item": homepage},
        ]
        if page.published_date:
            breadcrumbs.append({"@type": "ListItem", "position": 2,
                                "name": BLOG_PAGE.name, "item": config.origin + BLOG_PAGE.path})
        breadcrumbs.append({"@type": "ListItem", "position": len(breadcrumbs) + 1,
                            "name": page.name, "item": canonical})
        structured["@graph"].append({
            "@type": "BreadcrumbList", "@id": canonical + "#breadcrumb",
            "itemListElement": breadcrumbs,
        })
    if page.path == BLOG_PAGE.path:
        structured["@graph"].extend([
            {"@type": "CollectionPage", "@id": canonical + "#collection", "url": canonical,
             "name": page.name, "description": page.description, "inLanguage": "pl-PL",
             "isPartOf": {"@id": homepage + "#website"},
             "mainEntity": {"@id": canonical + "#articles"}},
            {"@type": "ItemList", "@id": canonical + "#articles",
             "itemListElement": [
                 {"@type": "ListItem", "position": position, "name": article.name,
                  "url": config.origin + article.path}
                 for position, article in enumerate(ALL_BLOG_ARTICLES, start=1)
             ]},
        ])
    elif page.published_date:
        author = {"@type": "Organization", "name": "Zespół Bractwa Krain", "url": homepage}
        article = {
            "@type": page.article_kind, "@id": canonical + "#article", "url": canonical,
            "headline": page.name, "description": page.description, "inLanguage": "pl-PL",
            "datePublished": page.published_date, "author": author, "publisher": author,
            "mainEntityOfPage": {"@id": canonical + "#webpage"},
            "isPartOf": {"@id": config.origin + BLOG_PAGE.path + "#collection"},
        }
        if page_image:
            article["image"] = image_url
        if page.category:
            article["articleSection"] = page.category
        structured["@graph"].append(article)
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
    urls = []
    for page in PUBLIC_PAGES:
        image = (f'<image:image><image:loc>{escape(config.origin + page.image.path)}</image:loc>'
                 '</image:image>' if page.image else "")
        urls.append(f'  <url><loc>{escape(config.origin + page.path)}</loc>{image}</url>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
            f'{"".join(urls)}</urlset>\n')
