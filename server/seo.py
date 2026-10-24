"""Public, server-rendered metadata for the game and its player guides.

PUBLIC_SITE_URL is a deployment setting, never a request Host header. Invalid
origins fall back to the existing public Railway URL rather than generating
broken or attacker-controlled canonical, social or sitemap URLs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from html import escape
from ipaddress import ip_address
import json
import os
from pathlib import Path
import re
from urllib.parse import urlsplit


DEFAULT_ORIGIN = "https://bractwo.up.railway.app"
TITLE = "Bractwo Krain — polskie MMORPG z mechaniką D&D"
DESCRIPTION = ("Bractwo Krain — polskie MMORPG i gra w przeglądarce z mechaniką "
               "Dungeons & Dragons (D&D). Rozwijaj postać, wybieraj atuty i odkrywaj kręgi czarów.")
IMAGE_PATH = "/assets/seo/bractwo-krain-og.png"
IMAGE_ALT = "Zrzut gry Bractwo Krain: Solna Przystań i pustynna kraina"
HEAD_MARKER = "<!-- SEO_HEAD -->"
HEADER_MARKER = "<!-- PUBLIC_HEADER -->"


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
    modified_date: str | None = None
    language: str = "pl"


HOME_PAGE = PublicPage("/", "index.html", TITLE, DESCRIPTION, "Bractwo Krain")
BLOG_PAGE = PublicPage(
    "/blog", "blog/index.html",
    "Blog MMO — najnowsze informacje ze świata MMORPG",
    "Najnowsze informacje o MMORPG: Aion 2, Black Desert, RuneScape i inne gry MMO. "
    "Premiery, aktualizacje i wiadomości po polsku.",
    "Blog MMO — aktualności MMORPG i poradniki",
    modified_date="2026-10-24",
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
        "/blog/vampir-swiat-klasy-mechaniki", "blog/vampir-swiat-klasy-mechaniki.html",
        "VAMPIR: świat, klasy postaci i mechaniki rozgrywki",
        "Poznaj świat Nocturne, pięć klas VAMPIR oraz walkę, rozwój postaci i rywalizację między graczami. Co potwierdzają oficjalne materiały Netmarble?",
        "VAMPIR: świat wampirów, klasy postaci i mechaniki rozgrywki",
        published_date="2026-10-22", category="VAMPIR · Świat i rozgrywka", article_kind="NewsArticle",
        image=PageImage("/assets/blog/vampir-class-choice-1200.webp",
                        "Podróżnik w płaszczu przed gotyckimi arkadami pod czerwonym księżycem", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-3-czy-osrs-od-czego-zaczac", "blog/runescape-3-czy-osrs-od-czego-zaczac.html",
        "RuneScape 3 czy OSRS? Różnice i poradnik na start",
        "RuneScape 3 czy Old School RuneScape? Porównaj walkę, rozwój, darmową grę, abonament i wersje mobilne. Wybierz MMO i zaplanuj pierwsze kroki.",
        "RuneScape 3 czy Old School RuneScape? Różnice i od czego zacząć",
        published_date="2026-10-22", category="RuneScape · Porównanie", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-rs3-osrs-crossroads-1200.webp",
                        "Podróżnik na rozstaju dróg prowadzących do średniowiecznego miasta i magicznej krainy", 1200, 675),
    ),
    PublicPage(
        "/blog/archeage-chronicles-demo-klasy-walka", "blog/archeage-chronicles-demo-klasy-walka.html",
        "ArcheAge Chronicles: klasy, walka, PvP i demo | Bractwo Krain",
        "Warrior, Ranger, Berserker i Mage, PvP oraz Throne of Hinnon. Sprawdź demo ArcheAge Chronicles, system rozwoju i potwierdzony status premiery.",
        "ArcheAge Chronicles: klasy, walka, PvP i poradnik do dema",
        published_date="2026-10-20", category="ArcheAge Chronicles · Klasy i walka", article_kind="NewsArticle",
        image=PageImage("/assets/blog/archeage-chronicles-adventurers-1200.webp",
                        "Czworo poszukiwaczy przygód spogląda na słoneczną dolinę i starożytną kamienną bramę", 1200, 675),
    ),
    PublicPage(
        "/blog/eve-online-fractured-skies-dodatek", "blog/eve-online-fractured-skies-dodatek.html",
        "EVE Online Fractured Skies: premiera, okręty i Conquests",
        "Co zmienia EVE Online: Fractured Skies? Premiera 10 listopada 2026, navy battlecruisers, Synchronizer rigs, nowy HUD i plan Conquests na 2027 rok.",
        "EVE Online: Fractured Skies — premiera, nowe okręty i droga do Conquests",
        published_date="2026-10-20", category="EVE Online", article_kind="NewsArticle",
        image=PageImage("/assets/blog/eve-fractured-skies-fleet-1200.webp",
                        "Cztery autorskie krążowniki bojowe wyłaniające się z błękitnej mgławicy nad planetą — ilustracja redakcyjna do EVE Online: Fractured Skies", 1200, 675),
    ),
    PublicPage(
        "/blog/osrs-fractured-archive-raid-poradnik", "blog/osrs-fractured-archive-raid-poradnik.html",
        "OSRS The Fractured Archive — wymagania i nagrody | Blog MMO",
        "Jak przygotować się do The Fractured Archive w OSRS? Wymagany quest, skalowanie drużyny, wybór bossów, śmierć, Practice Mode i najważniejsze nagrody.",
        "OSRS The Fractured Archive: wymagania, drużyna i nagrody z raidu",
        published_date="2026-10-20", category="Old School RuneScape · Raidy", article_kind="NewsArticle",
        image=PageImage("/assets/blog/osrs-fractured-archive-raid-1200.webp",
                        "Czworo poszukiwaczy przygód zbliża się do świetlistego skarbca w podziemnym archiwum — ilustracja fantasy.", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-pluginy-hub-quest-helper", "blog/runescape-pluginy-hub-quest-helper.html",
        "RS3 Plugin Hub: jak włączyć pluginy i data premiery",
        "Gdzie jest RS3 Plugin Hub i jak włączyć pluginy? Instalacja, Manage, uprawnienia, brak ikony oraz daty bety i premiery 19 października 2026.",
        "RS3 Plugin Hub: jak włączyć pluginy i kiedy była premiera?",
        published_date="2026-10-20", modified_date="2026-10-24", category="RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-plugin-hub-tools-1200.webp",
                        "Pięć mosiężnych i kryształowych narzędzi połączonych nad mapą fantasy ze świetlistymi znacznikami nawigacji", 1200, 675),
    ),
    PublicPage(
        "/blog/vampir-premiera-polska-pobieranie-wymagania", "blog/vampir-premiera-polska-pobieranie-wymagania.html",
        "VAMPIR: premiera w Polsce, pobieranie i wymagania PC",
        "VAMPIR ma ruszyć 28 października o 03:00 w Polsce. Sprawdź wcześniejsze pobieranie, "
        "wymagania PC, linki do sklepów i różnicę w terminie iOS.",
        "VAMPIR: kiedy premiera w Polsce? Start, pobieranie i wymagania",
        published_date="2026-10-18", category="Nowe MMORPG · VAMPIR", article_kind="NewsArticle",
        image=PageImage("/assets/blog/vampir-premiera-polska-pc-android-1200.webp",
                        "Bohaterowie VAMPIR na tle czerwonego księżyca — grafika promocyjna wampirzego MMORPG Netmarble", 1200, 630),
    ),
    PublicPage(
        "/blog/alien-colonies-gra-podobna-do-ogame-android", "blog/alien-colonies-gra-podobna-do-ogame-android.html",
        "Alien Colonies — nowa gra podobna do OGame na Androida",
        "Alien Colonies to nowa gra podobna do OGame: trzy rasy, kolonie, badania i floty. "
        "Pobierz na Androida z Google Play lub graj w przeglądarce.",
        "Alien Colonies — nowa gra podobna do OGame na Androida",
        published_date="2026-10-15", category="Nowe gry MMO · Alien Colonies", article_kind="NewsArticle",
        image=PageImage("/assets/blog/alien-colonies-trzy-rasy-planety-1200.webp",
                        "Zetan, Automaton i Symbiont — trzy rasy Alien Colonies na tle planet i jasnej gwiazdy", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-2027-dragon-slayer-2-arposandra", "blog/runescape-2027-dragon-slayer-2-arposandra.html",
        "RuneScape 2027: Dragon Slayer II, Arposandra i Agility | Bractwo Krain",
        "Plany RuneScape na 2027: Dragon Slayer II, Arposandra, przebudowa Agility i rajd na Karamji. "
        "Sprawdź trzy cykle aktualizacji oraz ogłoszone terminy.",
        "RuneScape 2027: Dragon Slayer II, Arposandra i przebudowa Agility",
        published_date="2026-10-12", modified_date="2026-10-18", category="Newsy MMORPG · RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-2027-roadmap-1200.webp",
                        "Złoty smok, miasto gnomów i wyprawa w dżungli — oficjalna ilustracja planów RuneScape na 2027 rok", 1200, 675),
    ),
    PublicPage(
        "/blog/aion-2-boty-rmt-4996-kont-11-pazdziernika", "blog/aion-2-boty-rmt-4996-kont-11-pazdziernika.html",
        "AION 2: bany za RMT, kupowanie Kinah i odwołanie",
        "Czy kupowanie Kinah grozi banem w AION 2? Globalne zasady RMT: kary 30 i 90 dni, blokady ochronne oraz termin 15 dni na odwołanie.",
        "AION 2: bany za RMT, kupowanie Kinah i odwołanie od blokady",
        published_date="2026-10-11", modified_date="2026-10-24", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        image=PageImage("/assets/blog/aion-2-komunikat-ograniczenia-kont-800.webp",
                        "Logo AION 2 na tle wysokiej zrujnowanej wieży — oficjalna grafika NC", 800, 450),
    ),
    PublicPage(
        "/blog/black-desert-poziom-75-exp-8-pazdziernika", "blog/black-desert-poziom-75-exp-8-pazdziernika.html",
        "Black Desert: poziom 75 i zmiany EXP — 8 października | Bractwo Krain",
        "Aktualizacja Black Desert NA/EU z 8 października 2026: poziom 75, premie PvE od 70, "
        "limity EXP za potwory i Combat Secret Books planowane na 15 października.",
        "Black Desert: poziom 75 i przebudowa EXP w aktualizacji 8 października",
        published_date="2026-10-08", category="Newsy MMORPG · Black Desert", article_kind="NewsArticle",
        image=PageImage("/assets/blog/black-desert-aktualizacja-8-pazdziernika-880.webp",
                        "Postać na koniu na leśnej drodze w jesiennym krajobrazie Black Desert — oficjalny baner aktualizacji.", 880, 355),
    ),
    PublicPage(
        "/blog/aion-2-nowe-serwery-eu-nathara-tassin", "blog/aion-2-nowe-serwery-eu-nathara-tassin.html",
        "AION 2: nowe serwery EU i konserwacja 9 października | Bractwo Krain",
        "Nathara dla Elyos i Tassin dla Asmodian: nowe serwery EU w AION 2. "
        "Godziny w Polsce, konserwacja 9 października o 08:30, zmiany skrzydeł i rekompensata za awarię EU.",
        "AION 2: nowe serwery EU Nathara i Tassin. Konserwacja 9 października",
        published_date="2026-10-08", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        modified_date="2026-10-11",
        image=PageImage("/assets/blog/aion-2-nowe-serwery-eu-oficjalna-800.webp",
                        "Logo AION 2 i napis „New Servers Opening!” przed portalem — oficjalna grafika nowych serwerów EU Nathara i Tassin.", 800, 450),
    ),
    PublicPage(
        "/blog/aion-2-rekord-steam-nagrody", "blog/aion-2-rekord-steam-nagrody.html",
        "AION 2: rekord Steam, darmowy voucher i nagrody | Bractwo Krain",
        "AION 2 po premierze: 397 905 graczy jednocześnie na Steam, darmowy Customization Voucher "
        "i prezenty za 400 tysięcy aktywnych użytkowników. Sprawdź źródła i menu Closet.",
        "AION 2: rekord na Steam i darmowy Customization Voucher po premierze",
        published_date="2026-10-06", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        modified_date="2026-10-11",
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
        modified_date="2026-10-11",
        image=PageImage("/assets/blog/aion-2-start-skrzydla-ilustracja-1200.webp",
                        "Skrzydlata postać nad chmurami przed podniebną cytadelą — ilustracja redakcyjna do artykułu o starcie AION 2.", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-4-zapowiedz", "blog/runescape-4-zapowiedz.html",
        "RuneScape 4 zapowiedziane — nowe MMORPG i Ashenfall | Bractwo Krain",
        "Jagex zapowiedział RuneScape 4 z początkiem przygody w Ashenfall. "
        "Co ogłoszono o nowym MMORPG, czego jeszcze nie wiemy i co oznacza to dla graczy?",
        "RuneScape 4 zapowiedziane. Nowe MMORPG zacznie się w Ashenfall",
        published_date="2026-10-04", modified_date="2026-10-12", category="Newsy MMORPG · RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-4-wyprawa-ilustracja-1200.webp",
                        "Podróżnik patrzy ze skalnego tarasu na wulkaniczną dolinę — ilustracja do zapowiedzi RuneScape 4.", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-pluginy-beta", "blog/runescape-pluginy-beta.html",
        "RuneScape: beta pluginów 6 października i Quest Helper | Bractwo Krain",
        "Beta pluginów RuneScape rusza 6 października 2026. Quest Helper obejmie "
        "62 zadania. Poznaj potwierdzone informacje i ograniczenia testów.",
        "RuneScape: beta pluginów 6 października. Quest Helper z 62 zadaniami",
        published_date="2026-10-04", modified_date="2026-10-20", category="Newsy MMORPG · RuneScape", article_kind="NewsArticle",
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


def _english_blog_pages():
    """Build translated documents from one metadata file and the original assets.

    A missing file is tolerated while a checkout is being prepared. A present
    file must describe every blog document, so partial translations cannot
    silently generate mismatched language links or an incomplete collection.
    """
    metadata_path = Path(__file__).with_name("blog_en.json")
    if not metadata_path.is_file():
        return None, (), {}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read English blog metadata: {metadata_path.name}") from error
    originals = (BLOG_PAGE, *ALL_BLOG_ARTICLES)
    expected = {page.path for page in originals}
    if not isinstance(metadata, dict) or set(metadata) != expected:
        raise ValueError("blog_en.json must contain exactly the Polish blog index and all article paths")
    translated = []
    language_paths = {}
    required = ("path", "title", "description", "name")
    for original in originals:
        entry = metadata[original.path]
        if (not isinstance(entry, dict)
                or any(not isinstance(entry.get(field), str) or not entry[field].strip()
                       for field in required)):
            raise ValueError(f"Invalid English blog metadata for {original.path}: required text is missing")
        path = entry["path"]
        if (not re.fullmatch(r"/en/blog(?:/[a-z0-9]+(?:-[a-z0-9]+)*)?", path)
                or (original is BLOG_PAGE) != (path == "/en/blog")):
            raise ValueError(f"Invalid English blog path for {original.path}: {path}")
        if path in language_paths:
            raise ValueError(f"Duplicate English blog path: {path}")
        image = original.image
        if image:
            image_alt = entry.get("image_alt")
            if not isinstance(image_alt, str) or not image_alt.strip():
                raise ValueError(f"Missing English image_alt for {original.path}")
            image = replace(image, alt=image_alt)
        category = entry.get("category", original.category)
        if category is not None and not isinstance(category, str):
            raise ValueError(f"Invalid English category for {original.path}")
        modified_date = entry.get("modified_date", original.modified_date or original.published_date)
        if modified_date is not None:
            try:
                if not isinstance(modified_date, str) or len(modified_date) != 10:
                    raise ValueError("Expected an ISO calendar date")
                date.fromisoformat(modified_date)
            except ValueError as error:
                raise ValueError(f"Invalid English modified_date for {original.path}") from error
            if any(modified_date < source_date for source_date in
                   (original.published_date, original.modified_date) if source_date):
                raise ValueError(f"English modified_date predates the original document: {original.path}")
        elif original.published_date or original.modified_date:
            raise ValueError(f"Missing English modified_date for {original.path}")
        translated.append(replace(
            original, path=path,
            template="en/blog/index.html" if original is BLOG_PAGE else path.lstrip("/") + ".html",
            title=entry["title"], description=entry["description"], name=entry["name"],
            category=category, image=image, modified_date=modified_date, language="en",
        ))
        language_paths[original.path] = {"pl": original.path, "en": path}
        language_paths[path] = language_paths[original.path]
    return translated[0], tuple(translated[1:]), language_paths


EN_BLOG_PAGE, EN_ALL_BLOG_ARTICLES, BLOG_LANGUAGE_PATHS = _english_blog_pages()
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
        "Klasy postaci w Bractwie Krain – wojownik, łowca, czarodziej i druid",
        "Porównaj cztery klasy postaci w Bractwie Krain. Poznaj styl walki wojownika, "
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
    *((EN_BLOG_PAGE,) if EN_BLOG_PAGE else ()),
    *EN_ALL_BLOG_ARTICLES,
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
    english = page.language == "en"
    language_tag = "en" if english else "pl-PL"
    blog_page = EN_BLOG_PAGE if english else BLOG_PAGE
    blog_articles = EN_ALL_BLOG_ARTICLES if english else ALL_BLOG_ARTICLES
    is_news = page.article_kind == "NewsArticle"
    page_image = page.image or (None if is_news else DEFAULT_IMAGE)
    if english and page.image is None and page_image:
        page_image = replace(page_image, alt="Bractwo Krain gameplay: Solna Przystań and a desert region")
    image_url = config.origin + page_image.path if page_image else None
    image_id = canonical + "#image" if page.image or english else homepage + "#image"
    attributes = [
        ("property", "og:type", "article" if page.published_date else "website"),
        ("property", "og:locale", "en_US" if english else "pl_PL"),
        ("property", "og:site_name", "Bractwo Krain"),
        ("property", "og:title", page.title),
        ("property", "og:description", page.description),
        ("property", "og:url", canonical),
        ("name", "twitter:card", "summary_large_image" if page_image else "summary"),
        ("name", "twitter:title", page.title),
        ("name", "twitter:description", page.description),
    ]
    if page.path in BLOG_LANGUAGE_PATHS:
        attributes.append(("property", "og:locale:alternate", "pl_PL" if english else "en_US"))
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
        if page.modified_date:
            attributes.append(("property", "article:modified_time", page.modified_date))
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
    for language, path in BLOG_LANGUAGE_PATHS.get(page.path, {}).items():
        lines.append(f'<link rel="alternate" hreflang="{language}" href="{escape(config.origin + path, quote=True)}">')
    lines.extend(f'<meta {kind}="{name}" content="{escape(value, quote=True)}">'
                 for kind, name, value in attributes)
    webpage = {
        "@type": "WebPage", "@id": canonical + "#webpage", "url": canonical,
        "name": page.title, "description": page.description, "inLanguage": language_tag,
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
        elif blog_page and page.path == blog_page.path:
            webpage["mainEntity"] = {"@id": canonical + "#collection"}
    structured = {"@context": "https://schema.org", "@graph": [webpage]}
    if page_image and (page.image or page.path == "/" or english):
        structured["@graph"].append({
            "@type": "ImageObject", "@id": image_id, "url": image_url,
            "contentUrl": image_url, "width": page_image.width, "height": page_image.height,
            "encodingFormat": page_image.mime_type, "caption": page_image.alt,
        })
    if page.path == "/":
        structured["@graph"].extend([
            {"@type": "WebSite", "@id": homepage + "#website", "url": homepage,
             "name": "Bractwo Krain", "inLanguage": ["pl-PL", "en"] if EN_BLOG_PAGE else "pl-PL",
             "description": DESCRIPTION},
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
                                "name": blog_page.name, "item": config.origin + blog_page.path})
        breadcrumbs.append({"@type": "ListItem", "position": len(breadcrumbs) + 1,
                            "name": page.name, "item": canonical})
        structured["@graph"].append({
            "@type": "BreadcrumbList", "@id": canonical + "#breadcrumb",
            "itemListElement": breadcrumbs,
        })
    if blog_page and page.path == blog_page.path:
        structured["@graph"].extend([
            {"@type": "CollectionPage", "@id": canonical + "#collection", "url": canonical,
             "name": page.name, "description": page.description, "inLanguage": language_tag,
             "isPartOf": {"@id": homepage + "#website"},
             "mainEntity": {"@id": canonical + "#articles"}},
            {"@type": "ItemList", "@id": canonical + "#articles",
             "itemListElement": [
                 {"@type": "ListItem", "position": position, "name": article.name,
                  "url": config.origin + article.path}
                 for position, article in enumerate(blog_articles, start=1)
             ]},
        ])
    elif page.published_date:
        author = {"@type": "Organization", "name": "Bractwo Krain Team" if english else "Zespół Bractwa Krain", "url": homepage}
        article = {
            "@type": page.article_kind, "@id": canonical + "#article", "url": canonical,
            "headline": page.name, "description": page.description, "inLanguage": language_tag,
            "datePublished": page.published_date, "author": author, "publisher": author,
            "mainEntityOfPage": {"@id": canonical + "#webpage"},
            "isPartOf": {"@id": config.origin + blog_page.path + "#collection"},
        }
        if page_image:
            article["image"] = image_url
        if page.modified_date:
            article["dateModified"] = page.modified_date
        if page.category:
            article["articleSection"] = page.category
        if english and page.path in BLOG_LANGUAGE_PATHS:
            original_url = config.origin + BLOG_LANGUAGE_PATHS[page.path]["pl"]
            article["translationOfWork"] = {
                "@type": page.article_kind, "@id": original_url + "#article",
                "url": original_url, "inLanguage": "pl-PL",
            }
        structured["@graph"].append(article)
    # A JSON script remains safe even if future editable text contains </script>.
    payload = json.dumps(structured, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    lines.append(f'<script type="application/ld+json">{payload}</script>')
    return "\n".join(lines)


def render_index(template, config):
    """Replace only the explicit template marker, leaving the app shell intact."""
    return render_page(template, config, HOME_PAGE)


def public_header(page):
    """One public navigation bar for the landing page, blog and guides."""
    english = page.language == "en"
    blog_path = "/en/blog" if english else "/blog"
    blog_current = ' aria-current="page"' if page.path == blog_path else ""
    brand_label = "Bractwo Krain — home" if english else "Bractwo Krain — strona główna"
    navigation_label = "Main navigation" if english else "Główna nawigacja"
    blog_label = "MMO Blog" if english else "Blog MMO"
    count_label = "characters created" if english else "stworzonych postaci"
    language_switch = ""
    if EN_BLOG_PAGE:
        paths = BLOG_LANGUAGE_PATHS.get(page.path, {"pl": BLOG_PAGE.path, "en": EN_BLOG_PAGE.path})
        language_label = "Language" if english else "Język"
        links = []
        for language, label, accessible_label in (("pl", "PL", "Polski"), ("en", "EN", "English")):
            current = ' aria-current="true"' if page.language == language else ""
            links.append(f'<a href="{escape(paths[language], quote=True)}" lang="{language}" '
                         f'hreflang="{language}" aria-label="{accessible_label}"{current}>{label}</a>')
        language_switch = (f'<span class="public-header__languages" role="group" aria-label="{language_label}">'
                           + "".join(links) + "</span>")
    return f'''<header class="public-header">
  <a class="public-header__brand" href="/" aria-label="{brand_label}"><svg viewBox="0 0 36 44" width="30" height="38" aria-hidden="true"><path d="M18 2 33 9v13c0 9-8 16-15 20C11 38 3 31 3 22V9Z" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M18 8v25m-7-9h14m-11 9h8m-8-18 4-7 4 7" fill="none" stroke="currentColor" stroke-width="1.4"/></svg><span>BRACTWO<small>KRAIN</small></span></a>
  <nav class="public-header__nav" aria-label="{navigation_label}"><a href="{blog_path}"{blog_current}>{blog_label}</a>{language_switch}</nav>
  <p class="public-header__count" data-character-count hidden><strong data-character-count-value></strong><span data-character-count-label>{count_label}</span></p>
</header>'''


def render_page(template, config, page):
    """Use the same document for visitors, previews and search engine crawlers."""
    html = template.replace(HEAD_MARKER, metadata_head(config, page), 1)
    if page.published_date and page.path.startswith(("/blog/", "/en/blog/")):
        blog_path = "/en/blog" if page.language == "en" else "/blog"
        latest_label = ("Read the latest MMORPG news" if page.language == "en"
                        else "Zobacz najnowsze informacje ze świata MMORPG")
        latest_link = f'<p class="blog-latest"><a href="{blog_path}">{latest_label}</a></p>\n'
        html = html.replace("</article>", latest_link + "</article>", 1)
    if HEADER_MARKER in html:
        html = html.replace(HEADER_MARKER, public_header(page), 1)
        assets = ('  <link rel="stylesheet" href="/public-header.css?v=20261018">\n'
                  '  <script src="/public-header.js?v=20261018" defer></script>\n')
        html = html.replace("</head>", assets + "</head>", 1)
    return html


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
        modified = f'<lastmod>{escape(page.modified_date)}</lastmod>' if page.modified_date else ""
        urls.append(f'  <url><loc>{escape(config.origin + page.path)}</loc>{modified}{image}</url>\n')
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
            'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">\n'
            f'{"".join(urls)}</urlset>\n')
