# Weryfikacja Bractwa 0.8.6 — 24.09.2026

## Serwer: 369 testów PASS

Pełny zakończony przebieg `python -m unittest discover -s tests -v`: **369 testów, 38,306 s, OK**. Log: `qa_0.8.6/server-tests.txt`, kod wyjścia `server-tests.exit` = 0. Wcześniejsze dwa wywołania zbiorcze przerwał limit narzędzia; wynik powyżej pochodzi z osobnego kompletnego przebiegu, a nie sumowania częściowych logów.

35 nowych testów w `tests/test_level_up_086.py` obejmuje rzeczywistą funkcję przyznawania PD, każdy pośredni poziom, konkretne przyrosty HP/many/cech/obron/kości/czarów, brak danych przed/po, brak zerowych wierszy, neutralizację chwilowych buffów i form, niezmienność historycznego wyposażenia, indywidualne i idempotentne potwierdzanie, wadliwe i cudze ID, prywatność, zapis i ponowne wczytanie, zgodność kompaktowych stanów, brak retroaktywnego spamu i duży awans o milion poziomów przechowywany jako zakres. Nie doliczano iteracji pętli jako osobnych testów.

Sprawdzono też przydzielenie istniejącego mistrzostwa poza NPC, walidację gałęzi, promocji i dostępnych punktów, odrzucenie podwójnego wydatku, śmierci i blokady walki; reset nadal wymaga mistrza. Nowe JS/CSS rzeczywiście pobrano przez serwer HTTP aiohttp. Pozostałe testy ponownie obejmują dotychczasową walkę, geometrię czarów, PvP, manę, kręgi, pościg, hotbar, historię F, zapis i migracje.

Środowisko wykonania: Python 3.13, zainstalowane aiohttp 3.13.3. Produkcyjny `server/requirements.txt` zachowuje wcześniejsze przypięcie aiohttp 3.13.5; nie wykonano nowej instalacji tego przypiętego środowiska.

## JavaScript: 28 testów PASS

`node --test tests/test_client_runtime.cjs tests/test_spell_vfx.cjs tests/test_level_up.cjs`: **28 testów, 28 PASS, zero porażek**. Log: `qa_0.8.6/node-tests.txt`. Nowe testy sprawdzają format pojedynczych przyrostów oraz zachowywanie i czyszczenie kolejki w scalanych stanach właściciela. Dotychczasowe testy 24 skrótów i geometrii/animacji pozostają.

`python -m compileall -q server tests tools` oraz `node --check` dla skryptów WWW: PASS. To nie sprawdza GDScript ani API silnika Godot.

## Interfejs WWW: 17 sprawdzeń PASS, 0 błędów JS

`python tools/browser_086_smoke.py`. Wyniki: `qa_0.8.6/browser-results.json`; pełny log: `browser-run.txt`; kod wyjścia `browser-tests.exit` = 0.

Sprawdzono osobne podsumowania dwóch poziomów z jednej nagrody, rzeczywiste przyrosty, nazwy przycisków, kaskadowe przesunięcia, wybór poprzedniego nagłówka, brak wygaśnięcia przez 9,5 s (poza czasem zwykłych powiadomień), zamknięcie środkowego panelu bez utraty pozostałych, zniknięcie samej kaskady po ostatnim zamknięciu, szczegóły awansu na poziom 20 i ikony nowych czarów. Pierwszy przebieg wykrył zasłonięcie nagłówka przez wcześniej podniesiony panel; poprawiono porządek kaskady. Powyższy wynik pochodzi z ponownego udanego przebiegu.

Rozdzielczości: **1440×900, 390×844, 320×700, 844×390**. Sprawdzono brak poziomego przepełnienia strony oraz pozostawanie dolnego przycisku w widocznym obszarze przy przewijanej długiej liście. Sprawdzono także mobilne zamknięcie przedniego panelu, przejście przyciskiem do Statystyk, faktyczny wydatek punktu i wzrost HP, blokadę przydziału podczas walki, ponowne logowanie z przywróceniem tylko oczekujących podsumowań, niewydawanie punktów przy zamykaniu oraz oddzielenie historii między kontami. Zrzuty są obok logów.

**Metoda:** rzeczywisty klient WWW i rzeczywisty serwer, uruchamiane w Chromium przez kontrolowany most WebSocket Python. Lokalny HTML, JS, CSS i SVG wczytywane z dostarczonych plików; localStorage testowy w pamięci. Postać, poziom i PD ustawiane przez fixture, przyrosty przez rzeczywistą funkcję `award`; AI potworów wstrzymane. Nie jest to test natywnej nawigacji HTTP/WS Chromium, fizycznego dotyku, trwałego przeglądarkowego localStorage, hostingu ani wielogodzinnej sesji. Trwałość kolejki testowano w bazie serwera i przez ponowne logowanie.

## Godot / eksport: NIE WYKONANO

Dodano natywny panel kaskadowy, integrację stanu i odpowiednik przydziału mistrzostwa. **Nie uruchomiono ani nie importowano projektu w Godocie, nie wykonano kompilacji GDScript, sprawdzenia typów przez silnik ani eksportu.** Natywna geometria UI i dotyk wymagają osobnej weryfikacji w silniku i na urządzeniu. Paczka nie zawiera APK, AAB ani EXE. Sam brak błędów Python/JS nie oznacza weryfikacji klienta Godot.

## Integralność

`SOURCE_MANIFEST.json` zawiera rozmiary i SHA-256 dostarczonych plików poza samym manifestem. ZIP jest sprawdzany przez `zipfile.testzip()`. Wykluczone są pamięci podręczne, środowiska wirtualne, bazy użytkownika i pliki podpisu. Raport 0.8.5 zachowano w `qa_0.8.5/TEST_REPORT.md`; starsze materiały nie opisują testów wykonanych dla 0.8.6.
