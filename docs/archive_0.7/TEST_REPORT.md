# Weryfikacja Bractwo 0.7.0

Data: 2026-09-23. Weryfikowano serwer, kod WWW i źródła Godot.

## Wyniki

- **87/87 testów serwera** w jednym uruchomieniu (29,983 s). Realne lokalne WebSockety, HTTP i tymczasowe bazy SQLite. W tym 71 wcześniejszych regresji oraz 16 nowych testów rund i kości.
- **8/8 testów logiki JS**: dotychczasowe indeksy, interpolacja, FPS, wybór potworów, podłoże i prywatne aktualizacje oraz format wyniku ataku/obrony.
- Składnia Python i JS poprawna; parser GDScript przyjął wszystkie 7 skryptów. Sprawdzono składnię skryptu startowego Bash. Nie jest to import ani sprawdzenie typów przez silnik Godot.
- Kod generujący mapę, siedliska, góry, rzeki i łupy jest identyczny z 0.6.0. Pliki graficzne nie zostały zmienione. Dodano wyłącznie elementy HUD i napisy wyników walki do istniejących rendererów; jakość i rozdzielczość rysowania pozostają.

Nowe scenariusze obejmują: trafienie przy równości z KP, naturalne 1/20, podwojenie kości bez podwajania dodatku, utrudnienie, obronę i połowę obrażeń, rozkład trafień w 20000 deterministycznych losowaniach, wybór najbliższego potwora bez zaznaczenia, granicę 3 sekund, odrzucanie powtórzonych pakietów, brak odłożonego ataku, ciągły ruch, wspólną akcję we wszystkich czterech profesjach, brak kosztu przy niewłaściwym celu, ignorowanie sfałszowanych rzutów, prowokowanie potwora, PvP po pudle, ciosy/pociski/obszary potworów, unikanie pól, obronne wzmocnienia i migrację wyposażenia/odnowienia.

W starych testach gospodarki i uprawnień kości są kontrolowane, aby pudło nie losowało wyniku testu łupu lub zadań. Dawne dwusekundowe przerwy między atakami dostosowano do nowej rundy. Nowe testy niezależnie sprawdzają pudła, trafienia i krytyki. Nie zmieniono chronionych reguł ekonomii ani PvP.

## Koszt symulacji

`tools/benchmark_living_world.py`: 300 kroków po rozgrzaniu, postacie przy różnych siedliskach. Testowe wysokie HP utrzymuje walkę. To pomiar CPU serwera na tym komputerze, **nie FPS klienta ani opóźnień sieciowych**.

| Postacie | Średni krok | P95 | Maksimum | Przygotowanie stanów | Średnia wiadomość |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.242 ms | 0.359 ms | 0.67 ms | 0.349 ms | 8061 B |
| 24 | 3.841 ms | 5.227 ms | 6.044 ms | 16.234 ms | 22522 B |

Budżet kroku 20 Hz wynosi 50 ms. Przy 24 postaciach wszystkie pozostały żywe, a 21 otrzymało obrażenia. Średni krok jest zbliżony do pomiaru 0.6.0 (3,8 ms); pomiary nie stanowią gwarancji wydajności na innym sprzęcie. Rzuty są wykonywane przy akcjach, a nie dla każdego potwora w każdej klatce. Zostały zachowane indeksy przestrzenne, lokalna symulacja, buforowanie terenu i interpolacja. Bufor początkowej wiadomości Godota pozostaje 8 MiB.

## Ograniczenia

Nie przeprowadzono wizualnego uruchomienia 0.7.0. Przeglądarka była zablokowana przez zasady środowiska; nie używano alternatywnej drogi obchodzącej tę blokadę. Silnik Godot i środowisko Android nie były dostępne. Nie wykonano importu projektu, eksportu APK/EXE ani próby na urządzeniu. Pakiet zawiera źródła. Licznik FPS pozostaje dostępny, ale nie zmierzono FPS tej wersji.

Dłuższa walka wynikająca z rund i pudeł wymaga docelowego playtestu balansu. Mana, stare profesje i dotychczasowe czary pozostają — nie jest to pełna implementacja podręcznika D&D. Aktualizacja obejmuje fundamenty opisane w COMBAT_0.7.md.

Surowe wyniki: `server-tests-0.7.0.txt`, `client-tests-0.7.0.txt`, `performance-0.7.0.json`. Wyniki 0.6 i wcześniejsze zrzuty są historyczne; nie dowodzą wizualnego działania obecnego wydania.
