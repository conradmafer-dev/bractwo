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


@dataclass(frozen=True)
class PublicLanguage:
    tag: str
    open_graph: str
    name: str
    blog_label: str
    language_label: str
    navigation_label: str
    home_label: str
    count_label: str
    author: str
    latest_label: str
    default_image_alt: str


PUBLIC_LANGUAGES = {
    "pl": PublicLanguage(
        "pl-PL", "pl_PL", "Polski", "Blog MMO", "Język", "Główna nawigacja",
        "Bractwo Krain — strona główna", "stworzonych postaci", "Zespół Bractwa Krain",
        "Zobacz najnowsze informacje ze świata MMORPG", IMAGE_ALT,
    ),
    "en": PublicLanguage(
        "en", "en_US", "English", "MMO Blog", "Language", "Main navigation",
        "Bractwo Krain — home", "characters created", "Bractwo Krain Team",
        "Read the latest MMORPG news", "Bractwo Krain gameplay: Solna Przystań and a desert region",
    ),
    "es": PublicLanguage(
        "es", "es_ES", "Español", "Blog MMO", "Idioma", "Navegación principal",
        "Bractwo Krain — inicio (en polaco)", "personajes creados", "Equipo de Bractwo Krain",
        "Consulta las últimas noticias de MMORPG", "Bractwo Krain: Solna Przystań y una región desértica",
    ),
    "pt-BR": PublicLanguage(
        "pt-BR", "pt_BR", "Português do Brasil", "Blog MMO", "Idioma", "Navegação principal",
        "Bractwo Krain — início (em polonês)", "personagens criados", "Equipe de Bractwo Krain",
        "Leia as últimas novidades de MMORPG", "Bractwo Krain: Solna Przystań e uma região desértica",
    ),
}


HOME_PAGE = PublicPage("/", "index.html", TITLE, DESCRIPTION, "Bractwo Krain")
BLOG_PAGE = PublicPage(
    "/blog", "blog/index.html",
    "Blog MMO — poradniki i aktualności MMORPG | Bractwo Krain",
    "Nowe wiadomości MMORPG: WoW Forever, Albion Online, AION 2 i VAMPIR. Aktualizacje z oficjalnych źródeł, daty komunikatów i praktyczne poradniki.",
    "Blog MMO — aktualności MMORPG i poradniki",
    modified_date="2026-11-28",
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
        "/blog/gry-mmorpg-na-telefon-android", "blog/gry-mmorpg-na-telefon-android.html",
        "Najlepsze gry MMORPG na telefon z Androidem",
        "Porównaj Albion Online, Broken Ranks, RuneScape i OSRS na Androidzie. Sprawdź, które mają polski interfejs, ile miejsca wymagają i jak wrócić do gry na PC.",
        "Najlepsze gry MMORPG na telefon – w co zagrać na Androidzie?",
        published_date="2026-11-28", modified_date="2026-11-28", category="MMORPG na Androida", article_kind="Article",
        image=PageImage("/assets/blog/mobile-mmorpg-albion.webp",
                        "Poszukiwacz przygód w Albion Online uderza kilofem w świecącą żyłę rudy", 800, 450),
    ),
    PublicPage(
        "/blog/wow-forever-alterac-valley-zmiany-25-listopada", "blog/wow-forever-alterac-valley-zmiany-25-listopada.html",
        "WoW Forever: zmiany Alterac Valley z 25 listopada",
        "Nowe nagrody Alterac Valley w WoW Forever: mniej za generała, więcej za cele mapy oraz silniejsi dowódcy. Co uwzględnić przed kolejnym meczem?",
        "WoW Forever: Alterac Valley po zmianach z 25 listopada",
        published_date="2026-11-26", category="Newsy MMORPG", article_kind="NewsArticle",
        image=PageImage("/assets/blog/wow-forever-official-camp-1920.jpg",
                        "Bohaterowie World of Warcraft przy ognisku w lesie — oficjalna grafika WoW: Forever", 1920, 1080, "image/jpeg"),
    ),
    PublicPage(
        "/blog/wow-forever-balance-druid-zmiany-25-listopada", "blog/wow-forever-balance-druid-zmiany-25-listopada.html",
        "WoW: Forever — Balance Druid i reset talentów 25.11",
        "Zmiany Balance Druida w WoW: Forever już działają. Nowe talenty, Starfire, Dreamstate i dokładny warunek pełnego resetu po aktualizacji 25 listopada.",
        "WoW: Forever — Balance Druid po zmianach z 25 listopada",
        published_date="2026-11-26", category="Newsy MMORPG", article_kind="NewsArticle",
        image=PageImage("/assets/blog/wow-forever-official-camp-1920.jpg",
                        "Bohaterowie World of Warcraft przy ognisku w lesie — oficjalna grafika WoW: Forever", 1920, 1080, "image/jpeg"),
    ),
    PublicPage(
        "/blog/albion-online-dragonfire-patch-5-26-listopada", "blog/albion-online-dragonfire-patch-5-26-listopada.html",
        "Albion Online przyspiesza Dragonfire Patch 5 na 26 listopada",
        "Dragonfire Patch 5 wcześniej: wszystkie serwery Albion Online czeka przerwa 26 listopada o 11:00 CET. Harmonogram i kontekst testowych zmian.",
        "Albion Online przyspiesza Dragonfire Patch 5 na 26 listopada",
        published_date="2026-11-26", category="Newsy MMORPG · Albion Online", article_kind="NewsArticle",
        image=PageImage("/assets/blog/albion-dragonfire-official-792.jpg",
                        "Czerwony smok naprzeciw maga z kosturem — oficjalna grafika Albion Online: Dragonfire", 792, 248, "image/jpeg"),
    ),
    PublicPage(
        "/blog/aion-2-world-market-world-exchange-25-listopada", "blog/aion-2-world-market-world-exchange-25-listopada.html",
        "AION 2 World Market: 25 listopada, podatek i limity",
        "Archiwum zapowiedzi World Market i World Exchange w AION 2: podatek 20%, limity i dostęp. Status po konserwacji 25 listopada oraz pełne patch notes.",
        "AION 2: World Market i World Exchange od 25 listopada",
        published_date="2026-11-22", modified_date="2026-11-26", category="AION 2 · Archiwum zapowiedzi", article_kind="NewsArticle",
        image=PageImage("/assets/blog/aion-2-world-market-nc-800.webp",
                        "Logo AION 2 na tle osady z drewnianymi budynkami i jesiennymi drzewami — grafika NC", 800, 450),
    ),
    PublicPage(
        "/blog/vampir-crest-skirmish-listopad-2026", "blog/vampir-crest-skirmish-listopad-2026.html",
        "VAMPIR: Crest od 70. poziomu i Skirmish EU 28–29 listopada",
        "VAMPIR: archiwum zapowiedzi Crest od 70. poziomu, godziny Skirmish EU 28–29 listopada i pule diamentów. Aktualny status oraz link do pełnych notatek.",
        "VAMPIR: Crest od 70. poziomu i Skirmish EU 28–29 listopada",
        published_date="2026-11-22", modified_date="2026-11-26", category="VAMPIR · Archiwum zapowiedzi", article_kind="NewsArticle",
        image=PageImage("/assets/blog/vampir-premiera-polska-pc-android-1200.webp",
                        "Bohaterowie VAMPIR na tle czerwonego księżyca — grafika promocyjna wampirzego MMORPG Netmarble", 1200, 630),
    ),
    PublicPage(
        "/blog/eve-online-fractured-skies-jak-zaczac", "blog/eve-online-fractured-skies-jak-zaczac.html",
        "EVE Online Fractured Skies — statki AIR, HUD i Vanguard",
        "Fractured Skies w EVE Online zaplanowano na 10 listopada. Zobacz, jak odebrać darmowy statek AIR Academy, włączyć nowy HUD i znaleźć lokacje Vanguard.",
        "EVE Online: Fractured Skies — czy to dobry moment, by zacząć?",
        published_date="2026-11-09", category="EVE Online", article_kind="NewsArticle",
        image=PageImage("/assets/blog/eve-fractured-skies-training-hangar-1200.webp",
                        "Niebieskoszary statek nad pokładem orbitalnego hangaru z widokiem na turkusową planetę", 1200, 675),
    ),
    PublicPage(
        "/blog/wow-forever-jak-zaczac-tryby", "blog/wow-forever-jak-zaczac-tryby.html",
        "WoW Forever — poradnik na start i wybór trybu",
        "Jak zacząć w WoW Forever? Sprawdź dostęp w abonamencie, różnicę między ustawieniami Classic i Enhanced oraz tryby Normal, PvP, Roleplay i Roleplay PvP.",
        "WoW Forever — jak zacząć i który tryb wybrać?",
        published_date="2026-11-09", category="World of Warcraft", article_kind="NewsArticle",
        image=PageImage("/assets/blog/wow-forever-adventurers-camp-1200.webp",
                        "Czworo podróżników przy ognisku z widokiem na kamienną wieżę i unoszące się wyspy", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-3-nowe-pluginy-listopad-2026", "blog/runescape-3-nowe-pluginy-listopad-2026.html",
        "RuneScape 3 — 13 nowych pluginów i jak je włączyć",
        "Pełna lista 13 pluginów RS3 wydanych 5 listopada: Ground Items, Drop Log i kolejne. Instalacja, uprawnienia oraz aktualny status Clue Trainer i mobile.",
        "RuneScape 3 — 13 nowych pluginów. Które warto włączyć?",
        published_date="2026-11-04", modified_date="2026-11-14", category="RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-plugin-hub-tools-1200.webp",
                        "Pięć mosiężnych i kryształowych narzędzi połączonych nad mapą fantasy ze świetlistymi znacznikami nawigacji", 1200, 675),
    ),
    PublicPage(
        "/blog/guild-wars-afterlife-premiera-cena-unformed", "blog/guild-wars-afterlife-premiera-cena-unformed.html",
        "Guild Wars Afterlife: premiera, cena i nowy loch",
        "Guild Wars Afterlife zadebiutuje 13 stycznia 2027. Sprawdź, jak działa Unformed, ile kosztuje DLC i co muszą wiedzieć wracający gracze.",
        "Guild Wars Afterlife: nowy dodatek po niemal 20 latach",
        published_date="2026-11-04", category="Guild Wars", article_kind="NewsArticle",
        image=PageImage("/assets/blog/guild-wars-afterlife-misty-ruins-1200.webp",
                        "Troje podróżników spogląda na porośnięte dżunglą ruiny z turkusowym portalem ponad mgłą", 1200, 675),
    ),
    PublicPage(
        "/blog/vampir-swiat-klasy-mechaniki", "blog/vampir-swiat-klasy-mechaniki.html",
        "best class in vampir — jaką klasę wybrać do PvE i PvP?",
        "Carnage na start, Bloodstained do defensywnego PvE czy Akasha do walki PvP w zwarciu? Porównaj pięć klas VAMPIR i dobierz styl gry do swojego celu.",
        "best class in vampir — jaką klasę wybrać do PvE i PvP?",
        published_date="2026-10-22", modified_date="2026-11-26", category="VAMPIR · Poradnik klas", article_kind="NewsArticle",
        image=PageImage("/assets/blog/vampir-class-choice-1200.webp",
                        "Podróżnik w płaszczu przed gotyckimi arkadami pod czerwonym księżycem", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-3-czy-osrs-od-czego-zaczac", "blog/runescape-3-czy-osrs-od-czego-zaczac.html",
        "RuneScape 3 czy OSRS? Różnice i poradnik na start",
        "RS3 czy OSRS? Sprawdź, w której grze znajdziesz dawną postać. Porównaj walkę, abonament i to samo darmowe zadanie w zamku Lumbridge.",
        "RuneScape 3 czy Old School RuneScape? Różnice i od czego zacząć",
        published_date="2026-10-22", modified_date="2026-11-28", category="RuneScape · Porównanie", article_kind="Article",
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
        published_date="2026-10-20", modified_date="2026-11-26", category="Old School RuneScape · Raidy", article_kind="NewsArticle",
        image=PageImage("/assets/blog/osrs-fractured-archive-raid-1200.webp",
                        "Czworo poszukiwaczy przygód zbliża się do świetlistego skarbca w podziemnym archiwum — ilustracja fantasy.", 1200, 675),
    ),
    PublicPage(
        "/blog/runescape-pluginy-hub-quest-helper", "blog/runescape-pluginy-hub-quest-helper.html",
        "RS3 Plugin Hub: jak zainstalować i włączyć pluginy",
        "Jak otworzyć RS3 Plugin Hub, zainstalować dodatki i włączyć je w Manage. Oficjalne zrzuty, uprawnienia, nowe pluginy oraz informacje o Androidzie i iOS.",
        "RS3 Plugin Hub: jak zainstalować i włączyć pluginy?",
        published_date="2026-10-20", modified_date="2026-11-26", category="RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-plugin-hub-tools-1200.webp",
                        "Pięć mosiężnych i kryształowych narzędzi połączonych nad mapą fantasy ze świetlistymi znacznikami nawigacji", 1200, 675),
    ),
    PublicPage(
        "/blog/vampir-premiera-polska-pobieranie-wymagania", "blog/vampir-premiera-polska-pobieranie-wymagania.html",
        "VAMPIR w Polsce: pobieranie i wymagania PC oraz telefonów",
        "VAMPIR jest dostępne na PC, Androida i iOS. Pobierz grę z oficjalnych źródeł, sprawdź wymagania, języki i potwierdzoną datę globalnego startu.",
        "VAMPIR w Polsce: pobieranie, wymagania PC i telefonów",
        published_date="2026-10-18", modified_date="2026-11-14", category="VAMPIR · Pobieranie i wymagania", article_kind="NewsArticle",
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
        "Globalne zasady AION 2: kupowanie Kinah, kary za RMT, blokady bezpieczeństwa i 15 dni na odwołanie. Historyczna akcja wobec 4996 kont z 11 października.",
        "AION 2: bany za RMT, kupowanie Kinah i odwołanie od blokady",
        published_date="2026-10-11", modified_date="2026-11-14", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
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
        "AION 2: Nathara i Tassin — archiwum października 2026",
        "Archiwum ogłoszeń AION 2 z 8–9 października 2026: serwery Nathara i Tassin, plan konserwacji, skrzydła i zapowiedziane rekompensaty.",
        "AION 2: Nathara, Tassin i konserwacja — archiwum z października 2026",
        published_date="2026-10-08", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        modified_date="2026-10-11",
        image=PageImage("/assets/blog/aion-2-nowe-serwery-eu-oficjalna-800.webp",
                        "Logo AION 2 i napis „New Servers Opening!” przed portalem — oficjalna grafika nowych serwerów EU Nathara i Tassin.", 800, 450),
    ),
    PublicPage(
        "/blog/aion-2-rekord-steam-nagrody", "blog/aion-2-rekord-steam-nagrody.html",
        "AION 2: rekord Steam i nagrody — archiwum premiery",
        "Archiwalna relacja z 6 października 2026 o premierowym wyniku AION 2 na Steam, Customization Voucher i zapowiedzianych prezentach.",
        "AION 2: rekord Steam i nagrody z października 2026",
        published_date="2026-10-06", category="Newsy MMORPG · AION 2", article_kind="NewsArticle",
        modified_date="2026-10-11",
        image=PageImage("/assets/blog/aion-2-customization-voucher-oficjalna-800.webp",
                        "Zwierzęca postać w białym stroju obok logo AION 2 — oficjalna grafika komunikatu o Customization Voucher.", 800, 450),
    ),
    PublicPage(
        "/blog/aion-2-start-polska", "blog/aion-2-start-polska.html",
        "AION 2: premiera 5 października 2026 — archiwum",
        "Archiwalny harmonogram globalnej premiery AION 2 z 5 października 2026: godziny w Polsce, przerwa techniczna i zapowiedziane zmiany.",
        "AION 2: harmonogram globalnej premiery z 5 października 2026",
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
        "RuneScape: beta pluginów w październiku 2026 — archiwum",
        "Archiwalna zapowiedź bety pluginów RS3 z października 2026. Przejdź do aktualnej instrukcji instalacji, włączania i listy nowych dodatków.",
        "RuneScape: zapowiedź bety pluginów z października 2026 — archiwum",
        published_date="2026-10-04", modified_date="2026-11-14", category="RuneScape", article_kind="NewsArticle",
        image=PageImage("/assets/blog/runescape-pluginy-narzedzia-ilustracja-1200.webp",
                        "Kompas, mapa i modułowe narzędzia na drewnianym stole — ilustracja do artykułu o pluginach RuneScape.", 1200, 675),
    ),
    PublicPage(
        "/blog/ddo-court-of-strahd", "blog/ddo-court-of-strahd.html",
        "DDO Court of Strahd: terminy, latarnie i nagrody",
        "The Court of Strahd trwa w DDO. Planowany koniec: 17 lutego 2027. Sprawdź zasady latarni, wymagania Hardcore, nagrody i poprawki po premierze.",
        "DDO Court of Strahd: terminy, latarnie, Hardcore i nagrody",
        published_date="2026-10-04", modified_date="2026-11-14", category="Poradniki MMORPG · Dungeons & Dragons Online", article_kind="NewsArticle",
        image=PageImage("/assets/blog/ddo-court-of-strahd-latarnia-ilustracja-1200.webp",
                        "Latarnia rozświetla mgłę na drodze do gotyckiego zamku — ilustracja wydarzenia The Court of Strahd w DDO.", 1200, 675),
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


def _translated_blog_pages(language, originals, *, complete=False):
    """Build published translations using the original article dates and assets."""
    prefix = f"/{language.lower()}/blog"
    filename = f"blog_{language.lower().replace('-', '_')}.json"
    metadata_path = Path(__file__).with_name(filename)
    if not metadata_path.is_file():
        return {}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ValueError(f"Cannot read blog metadata: {filename}") from error
    if (not isinstance(metadata, dict) or BLOG_PAGE.path not in metadata
            or not metadata.keys() <= originals.keys()
            or (complete and metadata.keys() != originals.keys())):
        raise ValueError(f"Invalid original paths or missing translations in {filename}")
    translated = {}
    used_paths = set()
    required = ("path", "title", "description", "name")
    for original_path, original in originals.items():
        if original_path not in metadata:
            continue
        entry = metadata[original_path]
        if (not isinstance(entry, dict)
                or any(not isinstance(entry.get(field), str) or not entry[field].strip()
                       for field in required)):
            raise ValueError(f"Missing required text for {original_path} in {filename}")
        path = entry["path"]
        if (not re.fullmatch(re.escape(prefix) + r"(?:/[a-z0-9]+(?:-[a-z0-9]+)*)?", path)
                or (original is BLOG_PAGE) != (path == prefix)):
            raise ValueError(f"Invalid blog path for {original_path} in {filename}: {path}")
        if path in used_paths:
            raise ValueError(f"Duplicate blog path: {path}")
        used_paths.add(path)
        image = original.image
        if image:
            image_alt = entry.get("image_alt")
            if not isinstance(image_alt, str) or not image_alt.strip():
                raise ValueError(f"Missing image_alt for {original_path} in {filename}")
            image = replace(image, alt=image_alt)
        category = entry.get("category", original.category)
        if category is not None and not isinstance(category, str):
            raise ValueError(f"Invalid category for {original_path} in {filename}")
        modified_date = entry.get("modified_date", original.modified_date or original.published_date)
        if modified_date is not None:
            try:
                if not isinstance(modified_date, str) or len(modified_date) != 10:
                    raise ValueError("Expected an ISO calendar date")
                date.fromisoformat(modified_date)
            except ValueError as error:
                raise ValueError(f"Invalid modified_date for {original_path} in {filename}") from error
            if any(modified_date < source_date for source_date in
                   (original.published_date, original.modified_date) if source_date):
                raise ValueError(f"modified_date predates the original {original_path} in {filename}")
        elif original.published_date or original.modified_date:
            raise ValueError(f"Missing modified_date for {original_path} in {filename}")
        translated[original_path] = replace(
            original, path=path,
            template=path.lstrip("/") + ("/index.html" if original is BLOG_PAGE else ".html"),
            title=entry["title"], description=entry["description"], name=entry["name"],
            category=category, image=image, modified_date=modified_date, language=language,
        )
    return translated


_POLISH_BLOG_PAGES = {page.path: page for page in (BLOG_PAGE, *ALL_BLOG_ARTICLES)}
_BLOG_PAGES_BY_LANGUAGE = {
    "pl": _POLISH_BLOG_PAGES,
    **{language: _translated_blog_pages(language, _POLISH_BLOG_PAGES, complete=language == "en")
       for language in PUBLIC_LANGUAGES if language != "pl"},
}

BLOG_INDEXES = {
    language: pages[BLOG_PAGE.path] for language, pages in _BLOG_PAGES_BY_LANGUAGE.items() if pages
}
BLOG_ARTICLES_BY_LANGUAGE = {
    language: tuple(page for page in _BLOG_PAGES_BY_LANGUAGE[language].values() if page is not index)
    for language, index in BLOG_INDEXES.items()
}
BLOG_LANGUAGE_PATHS = {}
for _original_path in _POLISH_BLOG_PAGES:
    _variants = {
        language: _BLOG_PAGES_BY_LANGUAGE[language][_original_path].path
        for language in BLOG_INDEXES if _original_path in _BLOG_PAGES_BY_LANGUAGE[language]
    }
    if len(_variants) > 1:
        BLOG_LANGUAGE_PATHS.update(dict.fromkeys(_variants.values(), _variants))


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
    *(page for language in BLOG_INDEXES for page in _BLOG_PAGES_BY_LANGUAGE[language].values()),
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
    language = PUBLIC_LANGUAGES[page.language]
    is_translation = page.language != "pl"
    blog_page = BLOG_INDEXES.get(page.language, BLOG_PAGE)
    blog_articles = BLOG_ARTICLES_BY_LANGUAGE.get(page.language, ())
    alternates = BLOG_LANGUAGE_PATHS.get(page.path, {})
    is_editorial_article = page.article_kind in {"Article", "NewsArticle"}
    page_image = page.image or (None if is_editorial_article else DEFAULT_IMAGE)
    if is_translation and page.image is None and page_image:
        page_image = replace(page_image, alt=language.default_image_alt)
    image_url = config.origin + page_image.path if page_image else None
    image_id = canonical + "#image" if page.image or is_translation else homepage + "#image"
    attributes = [
        ("property", "og:type", "article" if page.published_date else "website"),
        ("property", "og:locale", language.open_graph),
        ("property", "og:site_name", "Bractwo Krain"),
        ("property", "og:title", page.title),
        ("property", "og:description", page.description),
        ("property", "og:url", canonical),
        ("name", "twitter:card", "summary_large_image" if page_image else "summary"),
        ("name", "twitter:title", page.title),
        ("name", "twitter:description", page.description),
    ]
    attributes.extend(("property", "og:locale:alternate", PUBLIC_LANGUAGES[alternate].open_graph)
                      for alternate in alternates if alternate != page.language)
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
    for alternate, path in alternates.items():
        lines.append(f'<link rel="alternate" hreflang="{alternate}" href="{escape(config.origin + path, quote=True)}">')
    lines.extend(f'<meta {kind}="{name}" content="{escape(value, quote=True)}">'
                 for kind, name, value in attributes)
    webpage = {
        "@type": "WebPage", "@id": canonical + "#webpage", "url": canonical,
        "name": page.title, "description": page.description, "inLanguage": language.tag,
        "isPartOf": {"@id": homepage + "#website"},
    }
    if not is_editorial_article:
        webpage["about"] = {"@id": homepage + "#game"}
    if page_image:
        webpage["primaryImageOfPage"] = {"@id": image_id}
    if page.path == "/":
        webpage["mainEntity"] = {"@id": homepage + "#game"}
    else:
        webpage["breadcrumb"] = {"@id": canonical + "#breadcrumb"}
        if page.published_date:
            webpage["mainEntity"] = {"@id": canonical + "#article"}
        elif page.path == blog_page.path:
            webpage["mainEntity"] = {"@id": canonical + "#collection"}
    structured = {"@context": "https://schema.org", "@graph": [webpage]}
    if page_image and (page.image or page.path == "/" or is_translation):
        structured["@graph"].append({
            "@type": "ImageObject", "@id": image_id, "url": image_url,
            "contentUrl": image_url, "width": page_image.width, "height": page_image.height,
            "encodingFormat": page_image.mime_type, "caption": page_image.alt,
        })
    if page.path == "/":
        website_languages = [PUBLIC_LANGUAGES[tag].tag for tag in BLOG_INDEXES]
        structured["@graph"].extend([
            {"@type": "WebSite", "@id": homepage + "#website", "url": homepage,
             "name": "Bractwo Krain", "inLanguage": website_languages if len(website_languages) > 1 else "pl-PL",
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
    if page.path == blog_page.path:
        structured["@graph"].extend([
            {"@type": "CollectionPage", "@id": canonical + "#collection", "url": canonical,
             "name": page.name, "description": page.description, "inLanguage": language.tag,
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
        author = {"@type": "Organization", "name": language.author, "url": homepage}
        article = {
            "@type": page.article_kind, "@id": canonical + "#article", "url": canonical,
            "headline": page.name, "description": page.description, "inLanguage": language.tag,
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
        if is_translation and "pl" in alternates:
            original_url = config.origin + alternates["pl"]
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
    language = PUBLIC_LANGUAGES[page.language]
    blog_path = BLOG_INDEXES.get(page.language, BLOG_PAGE).path
    blog_current = ' aria-current="page"' if page.path == blog_path else ""
    paths = BLOG_LANGUAGE_PATHS.get(page.path, BLOG_LANGUAGE_PATHS.get(BLOG_PAGE.path, {}))
    language_switch = ""
    if paths:
        links = []
        for tag, path in paths.items():
            current = ' aria-current="true"' if page.language == tag else ""
            links.append(f'<a href="{escape(path, quote=True)}" lang="{tag}" '
                         f'hreflang="{tag}" aria-label="{PUBLIC_LANGUAGES[tag].name}"{current}>{tag.upper()}</a>')
        language_switch = (f'<span class="public-header__languages" role="group" aria-label="{language.language_label}">'
                           + "".join(links) + "</span>")
    return f'''<header class="public-header">
  <a class="public-header__brand" href="/" aria-label="{language.home_label}"><svg viewBox="0 0 36 44" width="30" height="38" aria-hidden="true"><path d="M18 2 33 9v13c0 9-8 16-15 20C11 38 3 31 3 22V9Z" fill="none" stroke="currentColor" stroke-width="1.4"/><path d="M18 8v25m-7-9h14m-11 9h8m-8-18 4-7 4 7" fill="none" stroke="currentColor" stroke-width="1.4"/></svg><span>BRACTWO<small>KRAIN</small></span></a>
  <nav class="public-header__nav" aria-label="{language.navigation_label}"><a href="{blog_path}"{blog_current}>{language.blog_label}</a>{language_switch}</nav>
  <p class="public-header__count" data-character-count hidden><strong data-character-count-value></strong><span data-character-count-label>{language.count_label}</span></p>
</header>'''


def render_page(template, config, page):
    """Use the same document for visitors, previews and search engine crawlers."""
    html = template.replace(HEAD_MARKER, metadata_head(config, page), 1)
    blog_path = BLOG_INDEXES.get(page.language, BLOG_PAGE).path
    if page.published_date and page.path.startswith(blog_path + "/"):
        latest_label = PUBLIC_LANGUAGES[page.language].latest_label
        latest_link = f'<p class="blog-latest"><a href="{blog_path}">{latest_label}</a></p>\n'
        html = html.replace("</article>", latest_link + "</article>", 1)
    if HEADER_MARKER in html:
        html = html.replace(HEADER_MARKER, public_header(page), 1)
        assets = ('  <link rel="stylesheet" href="/public-header.css?v=20261018">\n'
                  '  <script src="/public-header.js?v=20261126" defer></script>\n')
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
