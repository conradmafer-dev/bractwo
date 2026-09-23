# Weryfikacja Bractwo 0.5.0

Data: 2026-09-22. Sprawdzano pełne źródła serwera, WWW i Godot. To raport wykonanych sprawdzeń, nie deklaracja testu na urządzeniu.

## Wyniki

- **60/60 testów serwera**: `python3 -m unittest discover -s tests -p 'test_*.py' -v` — 19,325 s. Realne lokalne WebSockety i tymczasowe bazy SQLite.
- **7/7 testów JS**: wybór celu, duże sylwetki, interpolacja, FPS, prywatne aktualizacje, indeks przestrzenny i klasyfikacja podłoża.
- **4779 zgodnych punktów podłoża Python/JS**, na rzeczywistej mapie: ścieżki, granice elips, miasta, piętra i losowe punkty kontynentu. `tools/check_surfaces.py` nie uruchamia przeglądarki ani renderera.
- Poprawna składnia Python (`py_compile`), JavaScript (`node --check`), wszystkich 7 plików GDScript (`gdparse`) i skryptu startowego (`bash -n`).
- Każdy punkt odrodzenia oraz każde wejście/wyjście z podziemi jest poza kolizją. Wszystkie 22 piętra mają przejście między komnatami. Wszystkie osie dróg sprawdzono co najwyżej co 20 jednostek, z promieniem gracza 18; brak kolizji.
- Test ekologii potwierdza 48 występujących typów, 9 nowych, mieszane grupy nieumarłych, smoka pod ziemią, pojedynczego cyklopa oraz brak obozów z ogniskiem u zwierząt. Cele zadań łowieckich odpowiadają rzeczywistym punktom występowania.
- Test walki potwierdza wykrywanie przed zasięgiem łuku, patrolowanie bez kontaktu gracza, dystansowe obrażenia oraz zapowiedzi bossów. Sprawdza unik z pola, ściany, piętra, strefę ochronną i anulowanie obrażeń po zabiciu strzelca.
- Test krążenia paladynem w zasięgu łuku z premium i przyspieszeniem potwierdza otrzymywanie obrażeń; przetestowano też leczenie wycofującego się bossa.
- Symulacja premium: odrzucenie błędnych danych i wymuszonego mnożnika, zapis/ponowne logowanie, 30-dniowe wygaśnięcie, wyłączenie, brak zmiany złota, idempotentne włączenie. To nie jest integracja płatności.

## Wydajność symulacji

`tools/benchmark_living_world.py`: 11130 potworów w świecie; postacie stoją przy oddzielnych siedliskach, przeciwnicy patrolują i walczą. Postacie mają testowe duże HP, aby śmierć nie zmniejszała obciążenia. Po rozgrzaniu zmierzono 300 kroków. To pomiar syntetyczny CPU na tym komputerze, **nie FPS klienta ani pomiar sieci internetowej**. Test nie jest bezpośrednio porównywalny z nieruchomym, niebojowym scenariuszem 0.4.1.

| Postacie | Średni krok | P95 kroku | Najdłuższy krok | Przygotowanie stanów wszystkich graczy | Średni stan |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 0.195 ms | 0.313 ms | 1.317 ms | 0.282 ms | 6150 B |
| 24 | 4.466 ms | 7.055 ms | 9.741 ms | 14.274 ms | 20464 B |

W scenariuszu 24 postaci obrażenia otrzymały 22, a wszystkie 24 pozostały żywe do końca próbki. Budżet kroku przy 20 Hz wynosi 50 ms. Katalog świata ma 2412950 B JSON i jest wysyłany jednokrotnie przy logowaniu. Godot ma zwiększony bufor wejścia 8 MiB. Wiadomości stanu korzystają z zachowanych ograniczeń widoczności i różnic prywatnych pól.

Grafika nie została uproszczona w celu poprawy pomiaru. Zachowano rysunki, efekty, gęstość pikseli i interpolację; nowe drogi/podłoże wykorzystują indeksy komórek i istniejące buforowanie terenu. FPS nadal jest mierzony przez klienta w rogu ekranu.

## Ograniczenia

W tej sesji dostępna droga do testu w przeglądarce była zablokowana przez politykę środowiska. Nie obchodzono tej blokady innym narzędziem. **Nie wykonano wizualnego testu przeglądarkowego wersji 0.5.0, uruchomienia w silniku Godot, eksportu APK/AAB/EXE ani testu na telefonie.** Parser GDScript nie zastępuje sprawdzenia typów i API przez silnik. Nie ma nowych zrzutów ekranu ani pomiaru rzeczywistego FPS. Historyczne obrazy w archive_0.3 nie dokumentują tej wersji.

Test krążenia w jednej arenie i kilkunastosekundowy pomiar obciążenia nie dowodzą pełnego balansu wszystkich klas, bossów, poziomów i długich sesji. Gra pozostaje prototypem do dalszego sprawdzania podczas gry.

## Pliki dowodowe i odtworzenie

- server-tests-0.5.0.txt — pełne wyjście 60 testów.
- client-tests-0.5.0.txt — 7 testów logiki JS.
- performance-0.5.0.json, surface-parity-0.5.0.json, world-0.5.0.json.
- `python3 tools/benchmark_living_world.py`; `python3 tools/check_surfaces.py`.
- Instrukcje uruchomienia serwera/klientów i eksportu: BUILD.md.
