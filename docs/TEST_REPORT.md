# Weryfikacja Bractwo 0.6.0

Data: 2026-09-23. Sprawdzano źródła serwera, WWW i Godot.

## Wykonane sprawdzenia

- **71/71 testów serwera** (23,780 s): realne lokalne WebSockety i tymczasowe SQLite. Wszystkie 60 wcześniejszych regresji plus 11 nowych scenariuszy; poprzednią liczbę pięter podziemnych zaktualizowano z 22 do 30.
- **7/7 testów logiki JS**: indeks, interpolacja, licznik FPS, wybór dużych potworów, prywatne aktualizacje i podłoże.
- **4965 zgodnych klasyfikacji podłoża Python/JS**, w tym nowe dodatnie piętra. Próba nie uruchamia renderera.
- Poprawna składnia Python, JavaScript, 7 skryptów GDScript i skryptu startowego. `gdparse` nie zastępuje sprawdzenia typów/API przez silnik Godot.
- Wszystkie 11235 punktów pojawiania się potworów i 106 przejść są poza kolizją. Każde z 30 pięter podziemnych ma trasę między komnatami. BFS na 23 tarasach potwierdza dostęp z miejsca wejścia do schodów oraz skrytek/kapliczek; krawędzie nie pozwalają zejść poza taras.
- Sprawdzono osie wszystkich 178 dróg nie rzadziej niż co 20 jednostek z promieniem gracza 18, a także wszystkie pomosty. Dwie nowe łącznice przecinały skały; zmieniono ich przebieg i ponownie sprawdzono cały zbiór.
- Nowe testy potwierdzają wejście na +3, powrót, zapis piętra, blokadę PvP i brak trafień między piętrami; woda zatrzymuje ruch.
- Hybrydy faktycznie zbliżają się podczas zwykłego rzutu, dochodzą do zwarcia i zadają ciosy. Boss wznawia pościg po zapowiedzi; łucznik utrzymuje dystans. Dotychczasowy test paladyna krążącego z premium i pośpiechem również przechodzi.
- Interakcje odrzucają użycie z daleka, z innego piętra, za niski poziom i walkę. Zweryfikowano efekt leczenia, szybkości i osłony PvE (bez osłony PvP), odnowienie po restarcie oraz blokadę skrytki przy pełnym plecaku.
- Trofeum można sprzedać raz, nie można go założyć. Próbki wszystkich klas/gatunków wskazują istniejące, odpowiednie szablony. W 40000 losowaniach cyklopa częstości sprzętu, trofeum, mikstury i przedmiotu rodowego mieszczą się w 0,9 punktu procentowego od deklarowanych stawek.

## Syntetyczne obciążenie serwera

`tools/benchmark_living_world.py`: 300 kroków po rozgrzaniu, postacie przy oddzielnych siedliskach. Duże testowe HP zachowuje obciążenie walką do końca. Pomiar dotyczy CPU serwera na tym komputerze, **nie FPS klienta**.

| Postacie | Średni krok | P95 | Maksimum | Przygotowanie stanów | Średnia wiadomość |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.229 ms | 0.326 ms | 0.601 ms | 0.305 ms | 6213 B |
| 24 | 3.8 ms | 5.051 ms | 11.705 ms | 15.476 ms | 20348 B |

Budżet kroku 20 Hz: 50 ms. Przy 24 postaciach obrażenia otrzymały 23, wszystkie pozostały żywe. Katalog początkowy: 2751882 B JSON. Bufor Godota pozostaje 8 MiB. Woda, skały i pokoje mają indeksy przestrzenne; klienci korzystają z istniejącego cachowania i cullingu.

## Ograniczenia

Nie przeprowadzono wizualnego uruchomienia tej wersji. Przeglądarka była zablokowana przez zasady środowiska; nie używano alternatywnej ścieżki obchodzącej tę blokadę. Silnik Godot i Android nie były dostępne; sprawdzono składnię GDScript, ale nie wykonano importu, eksportu ani testu urządzenia. Nowe powierzchnie HUD oraz rysunki wymagają prób w grze na docelowym urządzeniu. Licznik FPS jest zachowany, lecz brak pomiaru rzeczywistych FPS tego wydania. Historyczne zrzuty w archive_0.3 nie przedstawiają 0.6.0.

Balans walki i rzadkości potwierdzono scenariuszami symulacji, nie wielogodzinnym playtestem. Zapis z miejsca zajętego przez nową wodę/skałę przenosi postać do Przystani przy logowaniu poza blokadą walki, jak w poprzedniej wersji. Przed migracją zachowaj kopię `data`.

Surowe wyniki: server-tests-0.6.0.txt, client-tests-0.6.0.txt, surface-parity-0.6.0.json, performance-0.6.0.json, world-0.6.0.json.
