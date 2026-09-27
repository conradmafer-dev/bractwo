# Raport weryfikacji 0.8.1 — 23.09.2026

## Wyniki wykonanych testów

**187 testów Python: PASS, 14,172 s w końcowym przebiegu.** Polecenie: `python -m unittest discover -s tests -v`. Zestaw zawiera 82 testy regresji bazowej 0.8 oraz 105 nowych testów PvP. Część prób wykonuje dodatkowe podprzypadki; nie doliczono ich jako osobnych testów. Wynik źródłowy: `qa_0.8.1/server-tests.txt`.

Każdy z 47 wpisów katalogu ma osobną próbę zgodnego z przeznaczeniem działania w scenariuszu graczy. Sprawdzono wszystkie ofensywne zaklęcia także przy nieprawidłowych/chronionych celach. Zakres: blokada i ponowne zablokowanie, poziom, drużyna, osada, piętro i ściany, obszar mieszany, próba ataku bez kosztu na nieprawidłowy cel, kolejka, koncentracja i jej właściciel, ponawianie obrony, negatywne statusy, Tarcza kontra pociski, blokada reakcji, odporności i mieszane składniki obrażeń, pola okresowe i obrażenia za ruch, Znak łowcy, pet, formy i dodatkowe ataki, śmierć/czaszki/kary, wsparcie drużyny i zabezpieczenia przed bezkarnym leczeniem. Osobne testy obejmują wilka przy granicy osady i wejściu do strefy bezpiecznej.

Dwa nowe testy używają **rzeczywistych połączeń dwóch klientów aiohttp WebSocket** do serwera, rejestracji kont, wyboru gracza, rzucania czaru, blokady i wsparcia drużyny. Bazowy zestaw zachowuje również próby HTTP/rankingu/zasobów, migracji zapisów i wyposażenia.

**10 testów Node: PASS.** `node --test tests/test_client_runtime.cjs`. Testy dotychczasowego runtime: indeks przestrzenny, pomiary/interpolacja, wybieranie celu, teren, duże sylwetki, wilk i opis kości. Nie są one osobnym dowodem wszystkich zmian PvP; te sprawdzają Python i test UI. Wynik: `qa_0.8.1/client-runtime-tests.txt`.

**10 sprawdzeń UI w Chromium: PASS, zero błędów JavaScript strony.** Skrypt `tools/browser_pvp_smoke.py`; wyniki `qa_0.8.1/browser-results.json` i `browser-console.txt`. Dwie strony klienta podłączone kontrolowanym mostem do rzeczywistego serwera. Weryfikacje: zablokowany Magiczny pocisk, odblokowanie autoataku już wybranego gracza, trzy pociski z paska rzeczywiście zadają obrażenia graczowi, zdolność Promień mrozu spowalnia go, relock usuwa własny status i blokuje kolejne trafienie, leczenie siebie przy zaznaczonym przeciwniku, wzmocnienie wybranego sojusznika z koncentracją rzucającego, leczenie towarzysza w PvP i oznaczenie wspierającego walką, osiem slotów na mobilnym widoku, brak błędów JS.

`node --check web/game.js`, `node --check web/runtime.js` oraz `python -m py_compile server/*.py tests/*.py tools/browser_pvp_smoke.py`: PASS.

## Obrazy i metoda UI

Zrzuty z działającego canvas i interfejsu: `01_pvp_spell_desktop.png`, `02_pvp_party_support.png`, `03_pvp_mobile.png` w `qa_0.8.1`. Zrzuty desktop i telefon sprawdzono wizualnie. To test responsywnego widoku, nie fizycznego telefonu.

Środowisko Chromium zwracało `ERR_BLOCKED_BY_ADMINISTRATOR` dla natywnej nawigacji HTTP do localhost. Dlatego skrypt ładuje rzeczywiste HTML/CSS/JS przez `set_content`, a obiekt WebSocket zastępuje kontrolowanym mostem Python do serwera aiohttp. Zegar i rzuty są deterministyczne; localStorage to obiekt testowy. Nie jest to pełny test otwierania strony po sieci ani trwałości localStorage po restarcie przeglądarki. Natywny transport serwera ma niezależne testy HTTP i WebSocket opisane wyżej. Nie zapisano haseł testowych do dziennika pakietów w raporcie JSON.

## Nie wykonano

**Godot: zmieniono źródła, ale nie wykonano importu, kompilacji, uruchomienia ani eksportu w silniku.** Brak silnika w tym środowisku. Brak APK/AAB/EXE. Nie potwierdzono statycznego typowania GDScript przez silnik ani działania na fizycznym Androidzie. Nie wykonano internetowego wdrożenia, obciążeniowego testu dużej liczby graczy ani wielogodzinnej oceny balansu PvP. Nie deklarujemy konkretnych FPS ani gotowości produkcyjnej na podstawie tych testów.

Dokumenty `archive_*`, `qa_0.8/` i inne starsze katalogi QA to zapis historii; nie są nowymi pomiarami 0.8.1. Testy `tests/legacy_0_7/` nie wchodzą do liczby 187.
