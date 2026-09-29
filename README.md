# Bractwo 0.8.18 UI_19 — kontynent, wyspy i lokalne wyprawy

Nowa geografia i 20 różnych układów dróg, 10 osad z lokalnym handlem oraz
14 portów połączonych 17 dwukierunkowymi trasami. Dodano 18 zadań, 12 rozmówców,
8 kompleksów podziemnych i 3 dwupoziomowe wzgórza. Stare paski zaklęć usunięto,
mikstury zdrowia używają akcji dodatkowej, a potwory odradzają się wolniej.

[Opis świata i wdrożenie z zachowaniem bazy](docs/UI_19_WORLD.md) ·
[Nowe wyprawy](docs/UI_19_WYPRAWY.md) · [Magiczne przedmioty](docs/UI_19_MAGIC_ITEMS.md).
Aktualizacja zachowuje postacie i stare ID zadań oraz odkryć. Paczka READY wymaga
wdrożenia całego serwera i klienta; pozostaw dotychczasową bazę oraz wolumen Railway.

Poprzednia aktualizacja: [UI_18 — odrodzenie w ostatnio odwiedzonym mieście](docs/UI_18_RESPAWN_CITY.md).

## Bractwo 0.8.18 UI_17 — Wiodący pocisk bez fałszywego spadku na awansie

Poprawiono porównanie siły czaru w panelu awansu i w zapowiedzi ulepszenia.
Pojawienie się nowego darmowego użycia nie jest już mylone z osłabieniem czaru.
Przy awansie 19 → 20 najmocniejsza płatna wersja Wiodącego pocisku zyskuje
**+1k6 obrażeń**, a różnica kosztu mocniejszej wersji wynosi **+20 many**.
Darmowy pocisk i wszystkie koszty poszczególnych wersji pozostają bez zmian.

[Opis poprawki, wdrożenie i pełny zakres testów](docs/UI_17_GUIDING_BOLT_GROWTH.md).
16 nowych testów i 8 kontroli w Chromium przeszło. Zestaw starszych testów
ma te same trzy problemy odzyskiwania many co UI_16 — szczegóły w raporcie.
Nie testowano na fizycznym Androidzie ani na koncie produkcyjnym.

## GitHub / Railway

Rozpakowane pliki paczki **RAILWAY_GITHUB_READY** umieść w katalogu głównym repozytorium.
`Dockerfile`, `run.py`, `requirements.txt`, `server/` i `web/` muszą być na tym samym
poziomie. Zachowaj istniejącą bazę graczy, wolumen i ustawienia środowiska. Zatwierdź
zmiany i wyślij je do gałęzi używanej przez Railway. Serwer musi uruchomić nowy kod;
nie wystarczy zmienić samych plików przeglądarki. Reset postaci nie jest potrzebny.
Po wdrożeniu odśwież stronę — logowanie powinno pokazywać **UI_17**.

Paczka nie została wdrożona automatycznie na Railway.

## Lokalnie i pełne źródła

Uruchom `start_windows.bat` lub `./start_unix.sh`, potem otwórz `http://127.0.0.1:8080`.
Nie uruchamiaj gry przez samo otwarcie pliku HTML.

**FULL_SOURCE** zawiera dodatkowo `client/project.godot`, testy, narzędzia i wcześniejszą
dokumentację. Nie przebudowywano natywnego klienta Godota ani starych buildów.

Poprzednie opisy: [UI_16](docs/UI_16_SPELLBOOK.md),
[UI_14](docs/UI_14_DRUID_FULLSCREEN.md), [zasady 0.8.18](docs/RELEASE_0.8.18.md).
