# Bractwo 0.8.8 — raport weryfikacji

Data: 24.09.2026. Baza: pełne źródła 0.8.7 i launcher Railway z 0.8.7. Serwer i WWW obu paczek wynikowych są identyczne bajtowo. Nowa wersja nie zawiera bazy testowych kont ani plików APK/AAB/EXE.

## Testy Python: 502 / 502 PASS

Polecenie: `python -m unittest discover -s tests -v`. Ostatni pełny przebieg: **502 testy w 48,681 s, OK, kod wyjścia 0**. Log: `qa_0.8.8/python-tests.txt`, kod: `python-exit.txt`.

437 testów poprzedniej gry + 18 testów konfiguracji launchera Railway + **47 nowych testów zawartości 0.8.8**. Podprzypadków w pętlach nie doliczano do liczby testów.

Nowe przypadki sprawdzają kompletność tabel wszystkich 57 gatunków, 79 nowych przedmiotów (59 elementów wyposażenia + 20 trofeów), poprawne identyfikatory, zakres i granice procentów, identyczne szanse dla każdej klasy, niezależne losowanie i brak wymyślonego gwarantowanego dropu. Monte Carlo: po 80 000 prób dla mumii, szkieleta łucznika, bandyty i herszta, z ustalonym ziarnem i tolerancją 0,6 punktu procentowego; testuje implementację, nie dowodzi idealnego balansu gry.

Sprawdzono poziomy sprzętu względem źródła, brak legendarnych premii u słabych przeciwników, trofea zwierząt/żywiołaków zamiast ekwipunku, brak pozostałego generowania sprzętu pod klasę gracza. Każdy nowy przedmiot ma źródło. Tabele w podglądzie i rzeczywiste losowanie mają tę samą podstawę danych.

Obliczenia obejmują również rzeczywisty nekrotyczny pocisk akolity przeciw szacie Hierofanty (odporność nie tylko w opisie). Lekkie/średnie/ciężkie pancerze, suma premii, zgodność szat ze Zbroją maga, faktyczne rzuty 2k6 w ataku, jednokrotne dodanie premii +1, cztery kości na krytyku, obuchowy młot, Shillelagh, nieskalująca Iskra 1k4 wszystkich nowych różdżek, odporności (połowa, brak kumulacji, mieszane obrażenia, PvE i PvP, brak odporności wyposażenia podczas przemiany). Ograniczenia poziomu i klasy są egzekwowane na serwerze; trofeów nie można założyć.

Integracja: prawdziwe pokonanie mumii rozdaje jej tabelę i nie nalicza nagrody drugi raz; pełny plecak zwraca ostrzeżenie; zapis/wczytanie nowych i starych przedmiotów i depozytu zachowuje UID/własność. Wszystkie 126 nowych odrodzeń są przechodnie i poza osadą; każdy z dwóch nowych bossów ma jedno miejsce, a wszystkie dziewięć gatunków ma znaczniki łowisk.

Pliki: prawidłowe SVG, PNG o wymiarach 320×80 (cztery klatki), zgodność grafik WWW/Godot. Rzeczywiste trasy HTTP zwracają nowy JavaScript, CSS oraz wszystkie nowe ikony i atlasy. Zdrowie serwera podaje wersję 0.8.8. Przypadki regresji walki/czarów/manowej progresji/hotbarów/PvP/pościgu/zapisów/awansów pozostały w pełnym przebiegu.

## JavaScript: 43 / 43 PASS

`node --test tests/*.cjs`: 43 testy, zero błędów. Nowych jest 7: procenty PL, źródła i rzeczywista szansa niezależna od pól przedmiotu, mikstury, brak tabeli, bezpieczne indeksy animacji i jej pętla. Log: `qa_0.8.8/javascript-tests.txt`.

`node --check` dla każdego skryptu WWW oraz `python -m compileall -q server tests tools` przeszły. Bezpośrednie uruchamianie `python server/server.py --help` także działa (importy modułów zarówno w trybie pakietu, jak i skryptu).

## Interfejs Chromium: 14 / 14 PASS, zero błędów strony

`python tools/browser_088_smoke.py`. Wynik: `qa_0.8.8/browser-results.json`, log i kod wyjścia w tym samym katalogu. Rzeczywisty klient i serwer przez **kontrolowany most WebSocket Python**, z HTML/CSS/JS i plikami graficznymi wczytanymi lokalnie. Ruch potworów i zegar zamrożone wyłącznie w narzędziu QA. Konta i przedmioty sceny są testowe, ale wyposażanie i obliczenia są wykonywane przez kod serwera.

Sprawdzono siatkę plecaka 3×5, kości/bonusy i źródła przedmiotów, rzeczywiste założenie broni i ciężkiej płyty oraz wynik KP 20, blokadę cudzej klasy/trofeum, odświeżenie statystyk po założeniu broni. Canvas narysował wszystkie 11 nowych atlasów przez normalny renderer. Nie podłożono obrazka całej sceny zamiast działania klienta.

Podgląd wybranej mumii pokazuje różdżkę 5%, a podgląd herszta rzeczywiste osobne szanse. Ikony ładują się poprawnie. Escape i dolne Zamknij działają. Widoki 390×844 i 844×390 nie mają poziomego przepełnienia, lista łupów przewija się, a Zamknij pozostaje dostępne. Ekwipunek mobilny zachowuje trzy rzędy.

Zrzuty: `01_inventory_sources_desktop.png`, `02_monsters_desktop.png`, `03_mummy_loot_desktop.png`, `04_boss_loot_mobile.png`, `05_boss_loot_landscape.png`, `06_inventory_mobile.png`. Są to kadry interfejsu z kontrolowanego serwera QA, a nie z produkcyjnej sesji na Railway.

Podczas prac test wykrył zasłanianie przycisku Łup przez opis zadania po zawinięciu paska celu; naprawiono układ i ponowny pełny przebieg przeszedł. Poprawiono także opis pierścienia w podglądzie (KP, nie błędne „Mikstura”).

## Rzeczywisty lokalny proces / HTTP / WebSocket / restart: 15 / 15 PASS

`python tests/smoke_railway.py`. Log: `qa_0.8.8/railway-process-smoke.txt`, kod wyjścia 0. Uruchamia `run.py` w osobnym procesie na lokalnym porcie TCP i tymczasowej bazie; połączenia WebSocket są natywne, bez mostu testu przeglądarkowego.

Dwa konta weszły do wspólnego świata. Serwer wykonał czar, zapisał skróty i historię użyć; SIGTERM zakończył proces poprawnie, SQLite przeszło kontrolę integralności, następny start utworzył kopię, a to samo konto zalogowało się z zapisanymi ustawieniami. Wszystkie statyczne pliki WWW/ikony zwracane są bajtowo poprawnie, zapis i kod serwera nie są publicznie serwowane. To lokalny test launchera, **nie wdrożenie Railway**.

## Środowisko i ograniczenia

Python 3.13.5, aiohttp 3.13.3 z dostępnego środowiska, Node 22.16.0, Chromium. Pliki requirements pozostawiają przypięte w wejściowym projekcie aiohttp 3.13.5. Próba instalacji tej wersji do oddzielnego katalogu testowego nie powiodła się z powodu niedostępnego DNS pip; nie testowano osobnego środowiska z tym przypięciem. Istnienie wydania sprawdzono na oficjalnym PyPI; nie zmieniano globalnych zależności.

Nie uruchamiano Godota, importu zasobów w edytorze, kompilacji GDScript ani eksportu APK/AAB/EXE. Zmieniono źródła renderera, ikon/karty, podglądu łupu i wejścia; podgląd Godota jest tekstowy, nie identyczny z graficznym oknem WWW. To nadal wymaga testu w silniku.

Nie budowano obrazu Docker, nie wdrażano nic na koncie Railway, nie wykonano testu obciążenia wielu graczy ani wielogodzinnego pomiaru ekonomii. Szanse i jakość są pierwszym konkretnym balansem do testowania w rozgrywce, nie gwarancją idealnej ekonomii. Brak automatycznego podnoszenia z ziemi lub magazynu przepełnienia: przy pełnym plecaku zachowany jest wcześniejszy komunikat utraty nadmiaru.

## Paczki

Pełny ZIP: źródła klienta Godot, serwera, WWW, testów i narzędzi, dokumentacja, grafiki. ZIP Railway: ten sam serwer/WWW + launcher i konfiguracja, bez Godota. `SOURCE_MANIFEST.json` zawiera SHA-256 plików danej paczki. Archiwa przechodzą `ZipFile.testzip` i kontrolę manifestów. Nie zawierają baz, kluczy, czcionek, cache Python ani folderów importu Godota.
