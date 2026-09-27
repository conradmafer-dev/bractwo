# Bractwo 0.8.10 — raport weryfikacji

Baza: `BRACTWO_0.8.9_UKLAD_HUD_FULL_SOURCE.zip`. Wszystkie opisane testy przeprowadzono lokalnie na zmienionych źródłach, bez dostępu do produkcyjnej bazy użytkownika.

## Python — 545 / 545 PASS

Polecenie: `python -m unittest discover -s tests -v`. Pełny końcowy przebieg: **545 testów w 97,659 s, OK**. Log: `qa_0.8.10/python-tests.txt`.

Nowych 36 przypadków w `test_inventory_windows_0810.py` obejmuje migrację/idempotencję i pełny stary plecak; stosy i atomowe sprawdzanie miejsca; zakup/sprzedaż z walidacją ilości; użycie dokładnej przypisanej mikstury; brak zapasów z podrobionego licznika; zachowanie 3 s odnowienia i niezużywanie przy pełnym zasobie; wymagania poziomów i blokadę walki; zapis/odtworzenie osobistych źródeł; brak ujawniania globalnych tabel; ujawnienie tylko udanego łupu; upgrade każdej klasy i odtworzenie UID; stały termin 24 s szukania; powrót poza ekranem bez teleportu; ponowne podjęcie walki, zachowanie odnowień i stan śmierci; nowe statyczne trasy HTTP.

Zaktualizowano dotychczasowe oczekiwania, których zmiana jest zamierzona: wersję `/health`, dawny nieruchomy potwór po utracie celu oraz wypełnienie ekwipunku po migracji mikstur. Regresje mechanik D&D, PvP, czarów, lootu, awansów i konfiguracji uruchamiania pozostały w pełnym przebiegu. Kontrole źródeł Godota nie są testem kompilacji.

## JavaScript — 52 / 52 PASS

Polecenie: `node --test tests/*.cjs`. Log: `qa_0.8.10/javascript-tests.txt`. Nowe przypadki dotyczą danych podglądu przedmiotów, statystyk, mikstur i ograniczania położenia okien. Dotychczasowe testy sterowania, geometrii efektów, skalowania, podsumowań awansu i podglądu łupów również przeszły.

Kontrola składni `node --check` wszystkich plików `web/*.js` oraz `python -m compileall -q server tests tools run.py` również zakończyła się powodzeniem.

## Chromium — 19 / 19 PASS, brak błędów strony

Polecenie: `python tools/browser_0810_smoke.py`. Wynik: `qa_0.8.10/results.json`; log: `browser-log.txt` w tym samym katalogu.

Scenariusz używa rzeczywistego klienta i rzeczywistych handlerów serwera aiohttp. HTML, CSS, JavaScript i grafiki są wczytywane lokalnie; ze względu na ograniczenie dostępu Chromium do localhost komunikację prowadzi **kontrolowany most WebSocket Python**. Zegar i losowania są kontrolowane; ruch potworów jest w tym scenariuszu wstrzymany. AI sprawdzono oddzielnie w testach Python. Nie jest to przeglądarka telefonu fizycznego ani sesja na Railway.

Sprawdzono: domyślny brak kolizji regionu, PvP i zadania; wyrównanie chat/Q/R/czary; trzy prawdziwe podsumowania awansu i zamknięcie tylko jednego; przesuwanie i ponowne otwarcie karty; przesuwanie zadania bez przypadkowego otwarcia; ukrywanie awansów bez utraty historii; reset; tooltip założonej broni; kliknięcie założonego przedmiotu; dolny wiersz akcji; przypisanie większej mikstury many do Q i przywrócenie dokładnie 35; Kupuj/Sprzedaj i faktyczne rozliczenia zapasów/złota; odpoczynek przez właściwą interakcję; przeciąganie i Escape u kupca; osobiste odkrycie rzeczywiście wydanej różdżki mumii; aktywny cel/PvP/statusy; brak poziomego przepełnienia; zapis pozycji i widoczności per postać/orientacja.

Rozdzielczości: **1440×900, 390×844, 844×390, 360×640**. Na każdej z mobilnych sprawdzono HUD oraz okno ekwipunku i kupca. Zrzuty pokazują faktyczny renderer klienta. Testy nie stanowią gwarancji wszystkich możliwych ręcznych położeń — przeciągając można świadomie nałożyć panele na siebie. Przycisk ↺ odzyskuje układ domyślny.

## Lokalny proces / HTTP / WebSocket / restart — 15 / 15 PASS

Polecenie: `python tests/smoke_railway.py`. Log: `qa_0.8.10/local-process-smoke.txt`.

Rzeczywisty osobny proces `run.py`, tymczasowa SQLite i natywne HTTP/WebSocket bez mostu Chromium: dostępność kompletnego WWW bajtowo, brak publicznego serwowania źródeł/bazy, dwa konta, czar i ustawienia skrótów, zapis SIGTERM, integralność SQLite, kopia przed startem i ponowne logowanie. Jest to lokalne sprawdzenie launchera, nie wdrożenie na Railway ani budowa obrazu Docker.

## Środowisko i ograniczenia

Python 3.13.5, aiohttp 3.13.3, Node 22.16.0, Chromium. Przypięte aiohttp 3.13.5 w requirements pozostaje odziedziczone z wejściowego ZIP-a; nie było osobnego przebiegu z tą wersją. Most przeglądarkowy używa lokalnie dostępnego Playwright/Chromium, które nie są zależnościami produkcyjnego serwera.

Źródła Godota zaktualizowano, ale **nie uruchomiono silnika, importu, kompilacji GDScript ani eksportu**. Nie wygenerowano APK/AAB/EXE. Nie budowano Dockera, nie wdrażano na koncie Railway, nie testowano wielogodzinnego balansu ani obciążenia wielu jednoczesnych graczy. W tych obszarach nie deklarujemy wyników.

## Archiwa

Każde archiwum ma własny `SOURCE_MANIFEST.json` z SHA-256 plików. Paczka Railway ma kod w głównym katalogu; pełna ma katalog `Bractwo_0.8.10/`. Serwer i WWW są identyczne w obu. Kontrola integralności ZIP-ów i zgodność z manifestami są wykonywane podczas pakowania. Żaden ZIP nie zawiera bazy użytkowników, cache, kluczy, gotowego eksportu ani plików czcionek. Konta i hasła w scenariuszach QA są wyłącznie lokalnymi danymi testowymi.
