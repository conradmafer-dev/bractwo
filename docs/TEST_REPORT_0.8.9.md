# Bractwo 0.8.9 — raport weryfikacji

Data: 24.09.2026. Baza: pełne źródła 0.8.8, wraz z istniejącym launcherem Railway. Zakres zmiany: układ HUD, dostępność przycisków statusów i trasa nowego CSS. Mechaniki, loot, tabele, zasoby graficzne i format zapisów nie były zmieniane.

## Python: 509 / 509 PASS

Polecenie: `python -m unittest discover -s tests -v`.

Końcowy pełny przebieg: **509 testów w 42,835 s, OK, kod wyjścia 0**. Log: `qa_0.8.9/python-tests.txt`; kod wyjścia: `python-exit.txt`.

Zachowano 502 testy regresji. Dodano siedem przypadków w `tests/test_hud_089.py`: unikalność identyfikatorów kontrolek; kolejność chat/mikstury/paski; umieszczenie F bezpośrednio po K i poza przewijaniem; dostępne etykiety własnych/cudzych efektów oraz opisy; kolejność arkuszy i brak wspólnego tła; kontrola położenia/przycisków w źródłach Godota; rzeczywista trasa HTTP nowego CSS z poprawną zawartością, typem MIME i rewalidacją cache. Przypadek Godota jest wyłącznie kontrolą tekstu źródłowego — nie testem kompilacji.

Przy pierwszym pełnym przebiegu znaleziono jedno stare oczekiwanie wersji 0.8.8 w teście `/health`; zostało zaktualizowane do 0.8.9. Podany powyżej wynik pochodzi z ponownego pełnego przebiegu.

## JavaScript: 43 / 43 PASS

Polecenie: `node --test tests/*.cjs`. 43 testy, zero błędów i pominięć. Log: `qa_0.8.9/javascript-tests.txt`.

Kontrola składni `node --check` dla wszystkich skryptów WWW oraz `python -m compileall -q server tests tools` również zakończyła się powodzeniem.

## Chromium: 17 / 17 PASS, zero błędów strony

Polecenie: `python tools/browser_089_smoke.py`. Log: `qa_0.8.9/browser-log.txt`, wynik: `browser-results.json`, kod wyjścia 0.

Narzędzie uruchamia rzeczywisty kod serwera w pamięci oraz klienta WWW w Chromium. HTML/CSS/JS i grafiki są wczytywane lokalnie; komunikacja z serwerem odbywa się przez **kontrolowany most WebSocket Python**. Zegar i ruch potworów są kontrolowane wyłącznie w scenariuszu QA. To nie jest produkcyjna sesja Railway ani test na fizycznym telefonie.

Sprawdzono układ 1440×900, 1280×720, 1024×768, 390×844, 360×640 oraz 844×390. Automatyczne kontrole obejmują kolejność i granice kontrolek, F po prawej stronie K, brak zasłaniania środka przycisków mikstur/K/F, brak kolizji F z przyciskami walki i statusów z górnymi przyciskami, położenie statusów w górnej części ekranu i brak poziomego przepełnienia strony.

Sprawdzono rzeczywiste zużycie mikstur i odnowienie HP/many na serwerze, uruchamianie czaru z F i klawisza F, zmianę ulubionego czaru wraz z historią użyć, otwarcie zakładki Czary przez K, zmianę zestawu 24 slotów oraz wspólne przewijanie obu rzędów na telefonie. Kliknięcie własnego lub cudzego efektu otwiera opis poniżej statusów. Nazwa, czas, rundy i rozróżnienie właściciela są zachowane. Wysłano wiadomość czatu przez prawdziwy handler. Usunięcie efektów ukrywa cały pusty pasek.

Zrzuty w katalogu QA są kadrami rzeczywistego renderera, nie podłożonym obrazem. Obejrzano widoki pulpitu oraz obu orientacji. W trakcie kontroli poprawiono nakładanie statusów na górne menu telefonu, kolizję F z przyciskami walki przy 1024 px oraz położenie wiadomości w niskim widoku poziomym. Po tych zmianach wykonano pełny ponowny przebieg.

## Lokalny proces / HTTP / WebSocket / restart: 15 / 15 PASS

Polecenie: `python tests/smoke_railway.py`; kod wyjścia 0. Log: `qa_0.8.9/railway-process-smoke.txt`.

Uruchomiono `run.py` w osobnym procesie z tymczasową bazą. Natywne HTTP/WebSocket, bez mostu używanego przez Chromium: dwa konta we wspólnym świecie, rzucenie czaru, zapis skrótów i historii, zamknięcie SIGTERM, integralność bazy i odtworzenie po ponownym uruchomieniu. Sprawdzono również serwowanie wszystkich plików WWW bajtowo, w tym nowego `hud_layout.css`, oraz brak publicznego dostępu do bazy i źródeł serwera.

To test lokalny launchera, **nie wdrożenie ani test konta Railway**.

## Środowisko i ograniczenia

Python 3.13.5, aiohttp 3.13.3 z dostępnego środowiska, Node 22.16.0, Chromium. Przypięte w wejściowych plikach requirements aiohttp 3.13.5 pozostawiono bez zmian; nie wykonano osobnego testu z tą wersją.

Nie uruchamiano Godota, importu w edytorze ani kompilacji GDScript. Zmienione źródła natywnego klienta wymagają sprawdzenia w silniku. Nie eksportowano APK/AAB/EXE. Nie budowano obrazu Docker i nie wdrażano nic na koncie Railway. Nie wykonywano nowego testu wydajności wielu graczy ani wielogodzinnej rozgrywki.

## Paczki i integralność

`SOURCE_MANIFEST.json` w każdej paczce zawiera skróty SHA-256 jej plików. Archiwa są sprawdzane funkcją `ZipFile.testzip`, a zawartość porównywana z manifestem. Serwer i WWW obu paczek są identyczne bajtowo.

Paczki nie zawierają baz kont, kluczy, haseł użytkownika, cache Pythona/Godota, czcionek ani gotowych plików APK/AAB/EXE. Hasło występujące w kodzie/logu testu przeglądarkowego dotyczy wyłącznie utworzonego lokalnie konta testowego w nietrwałej bazie.
