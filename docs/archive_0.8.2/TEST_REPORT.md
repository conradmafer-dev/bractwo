# Raport weryfikacji Bractwa 0.8.2 — 24.09.2026

## Wykonane testy

**224 testy Python: PASS**, końcowy pełny przebieg 21,302 s. `python -m unittest discover -s tests -v`. Wynik: `qa_0.8.2/server-tests.txt`. W tej liczbie są 187 wcześniejsze testy 0.8/0.8.1 oraz 37 nowych metod testowych z `tests/test_pursuit_cantrips.py`. Podprzypadków nie doliczano do liczby testów.

Nowe przypadki: przekraczanie granicy spawnu bez przerwania pościgu; zatrzymanie w aktualnej pozycji; ponowne wykrycie z nowej pozycji; wielokrotne próby nadużycia starej granicy; odciąganie przez kolejne sektory i brak duplikatów indeksu; wymuszone przesunięcie; zasięg bossa przekraczający dwie komórki; śmierć/zmiana piętra/wyjście gracza poza symulację; osady; wygasanie pamięci za ścianą; początkowy patrol; regeneracja dopiero po przerwie; brak resetowania odnowień; zero HP przed rozliczeniem śmierci; śmierć po wyjściu wszystkich graczy; odrodzenie przy oryginalnym spawnie; starsze ID potworów; przejęcie celu przez innego gracza; towarzysz; zachowanie typów melee/ranged/hybrid/boss.

Balans jest testowany przez faktyczne akcje serwera, nie sam opis: Iskra 1k4 na kolejnych poziomach, skalowanie Ognistego pocisku, kości krytyka, wspólna akcja, kolejka przed autoatakiem, brak podwójnych obrażeń, zgodność PvE/PvP, blokada PvP, bonusy i opisy wszystkich różdżek, efekt Promienia mrozu, brak zmian broni innych klas, prowokacja także pudłem. Poprzedni zestaw zachowuje testy całego katalogu PvP, migracji, HTTP, rankingu i rzeczywistych par połączeń WebSocket.

Ruch w nowych izolowanych testach AI odbywa się w płaskiej arenie z wyłączonymi przeszkodami, chyba że przypadek celowo testuje widoczność lub ochronę rzeczywistych stref miejskich. Nie jest to dowód bezbłędnego omijania każdego zakrętu mapy.

**10 testów JavaScript/Node: PASS.** `node --test tests/test_client_runtime.cjs`, wynik w `qa_0.8.2/client-runtime-tests.txt`. Dotychczasowy runtime klienta: indeks, interpolacja, wybór celu, teren, sylwetki, pet i podsumowanie kości. `node --check web/game.js`, `node --check web/runtime.js`, kompilacja składni modułów Python: PASS.

## Chromium: 16 sprawdzeń, 0 błędów JavaScript

Wykonano `python tools/browser_082_smoke.py`. Wyniki i komendy bez haseł: `qa_0.8.2/browser-results.json`; log: `browser-console.txt`. Zachowano dziesięć dotychczasowych sprawdzeń PvP UI, w tym blokady, rzucanie na gracza, leczenie siebie przy wrogim celu, leczenie i wzmacnianie drużyny oraz układ telefonu.

Sześć nowych sprawdzeń: wybór potwora uruchamia faktyczną iskrę 1k4; opis przycisku wskazuje słabszą różdżkę; czar z paska w kolejce zadaje 2k10 zamiast iskry, bez dodatkowego ataku; księga pokazuje różnicę i brak kosztu many; układ mobilny zachowuje osiem slotów; w działającej symulacji przesunięty potwór zostaje w punkcie utraty gracza bez szybkiego leczenia, a stan/indeks nadal go zawiera. Część tych asercji należy do wspólnego sprawdzenia, dlatego raport ma 16 wpisów, nie liczbę pojedynczych asercji.

Zrzuty desktop 1440×900 i widoku mobilnego 390×844, w tym `04_cantrip_book_desktop.png` i `05_cantrip_book_mobile.png`, zostały obejrzane. Nowe informacje mieszczą się w panelu księgi; osiem skrótów pozostaje widocznych na telefonie.

**Metoda:** rzeczywiste HTML/CSS/JS klienta załadowane przez `set_content`, rzeczywisty serwer aiohttp oraz kontrolowany most WebSocket Python–Chromium. Dane kont testowych, zegar, rzuty i wybrane położenia są deterministycznymi fixture'ami. `localStorage` jest testowym obiektem. Nie jest to test natywnego połączenia HTTP/WebSocket z przeglądarki ani trwałości ustawień po ponownym uruchomieniu przeglądarki. Transport HTTP/WebSocket serwera ma oddzielne testy Pythona.

## Pomiar lokalny, nie gwarancja wydajności

`python tools/benchmark_server.py`, wyniki: `qa_0.8.2/performance.json` i `performance-profile.txt`. Świat zawiera 11 235 potworów. Średnia kroku symulacji w tym przebiegu: 0,356 ms przy jednym aktorze gracza, 4,111 ms przy 24. Średni pakiet po rozgrzaniu delty: 9544 / 23276 bajtów. To krótki lokalny mikrobenchmark istniejącego scenariusza, nie 24 fizyczne połączenia, test sieciowy, wielogodzinna rozgrywka ani gwarancja FPS.

## Ograniczenia

**Godot:** zmodyfikowano komunikaty i wersję źródeł, ale nie ma tu zainstalowanego silnika. Nie wykonano importu, weryfikacji typów przez silnik, uruchomienia, kompilacji ani eksportu. Brak APK/AAB/EXE i testu fizycznego Androida. Nie wykonano wdrożenia hostingu, długiej sesji wielu graczy ani końcowego testu ekonomii/balansu klas. Sterowanie potworów nadal używa lokalnego omijania, nie globalnego planowania ścieżek. Nie dodano zapisu ich położeń między restartami.

`archive_*`, `qa_0.8/`, `qa_0.8.1/` i testy `legacy_0_7` są historyczne. Wyniki bieżącej wersji są wyłącznie w `qa_0.8.2`.
