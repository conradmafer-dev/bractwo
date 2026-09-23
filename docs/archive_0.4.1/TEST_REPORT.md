# Raport weryfikacji — Bractwo 0.4.1

Data: 2026-09-22. Wersja koncentruje się na płynności bez pogorszenia grafiki, wyborze potworów, reakcji na ostrzał i liczniku FPS.

## Wyniki

| Sprawdzenie | Wynik |
| --- | --- |
| Pełny zestaw serwera | **50/50**, 10,186 s |
| Dodatkowa końcowa kontrola utrzymania aggro ponad 20 sekund | **7/7** testów naprawczych, 0,709 s |
| `node --test tests/test_client_runtime.cjs` | **5/5** |
| `node --check` dla game.js i runtime.js | Poprawna składnia |
| `gdparse client/scripts/*.gd` | Sześć plików, poprawna składnia |
| Python: server.py, progression.py, world_content.py | Poprawna składnia |
| Skrypt startowy Bash | Poprawna składnia |
| Generowanie terenu WWW | **90/90** porównań, identyczne polecenia rysowania |

Zapis wykonania serwera: server-tests-0.4.1.txt. Testy używają lokalnych WebSocketów i tymczasowych baz; fixture'y izolują pozycje, poziomy i potwory. Dodatkowe przypadki sprawdzają wskazany dalszy cel przy bliższym wrogu, blokadę PvP, ściany, piętra, martwe/nieprawidłowe cele, pościg i rzeczywiste obrażenia po ostrzale, podtrzymanie aggro oraz ograniczenie pościgu. Sprawdzono także czary/runy/umiejętności, pełny pierwszy stan, odtwarzanie zmian prywatnego stanu, ponowne logowanie, zgodność ze starszymi klientami i dostępność runtime.js przez HTTP.

Testy JS obejmują granice indeksu przestrzennego i piętra, rzeczywiste próbkowanie czasu klatek, interpolację i teleportację, wybór wroga według pozycji rysowania oraz scalanie prywatnych aktualizacji. Nie zastępują kliknięcia w uruchomionej przeglądarce.

## Pomiary przed i po

Ten sam komputer roboczy, ten sam kontynent i 7729 potworów. Postacie na poziomie 100 stały w deterministycznie wybranych odległych rejonach, poza pasywnym aggro. Po rozgrzaniu zmierzono 240 kroków bez narzutu profilera. Pierwsza wiadomość pozostaje pełna; poniższe rozmiary dotyczą kolejnych wiadomości bez zmian prywatnych list. Jednostki kB są dziesiętne.

| Metryka | 0.4.0 | 0.4.1 |
| --- | ---: | ---: |
| Krok serwera, 1 postać | 0,115 ms | 0,062 ms |
| Krok serwera, 24 postacie | 13,241 ms | 0,821 ms |
| Wiadomość stanu, 1 postać | 21 651 B | 1 987 B |
| Średnia wiadomość stanu, 24 postacie | 36 249 B | 16 585 B |
| 9000 wyszukań widocznej okolicy klienta, bez renderera | 221,14 ms | 27,57 ms |
| Średnia liczba odwiedzonych pozycji statycznych przy wyszukaniu | 2653 | 33 |

Surowe dane: performance-0.4.1.json. Powtarzalny test serwera: `python tools/benchmark_server.py [ścieżka-do-projektu]`. Wyniki zależą od sprzętu i sytuacji; nie są gwarancją FPS ani pomiarem pełnego obciążenia walką, siecią i renderowaniem. Indeks kamery jest w normalnej pracy dodatkowo odświeżany tylko przy zmianie komórki lub widoku.

## Zachowanie grafiki

Porównano sekwencje operacji generowania 90 fragmentów powierzchni i podziemi ze źródłami 0.4.0 — były identyczne. Funkcje rysujące drzewa, budynki, przeszkody, NPC, postacie, smoki, demony, ogień, rzekę, efekty i cząsteczki zachowano. Generator Godot używa tych samych kolorów, kafli i szumów, podzielonych na buforowane fragmenty. Nie obniżono rozdzielczości, skali obrazu, szczegółowości modeli ani liczby efektów. Nowymi elementami UI są odczyt FPS i oznaczenie wybranego celu.

## Niewykonane próby

Podgląd przeglądarkowy pozostawał niedostępny z powodu blokady polityki środowiska. Nie obchodzono jej innym narzędziem. Brak świeżych zrzutów, pomiaru GPU/FPS w prawdziwej przeglądarce i przejścia scenariusza kliknięciami. Porównanie poleceń rysowania jest sprawdzeniem algorytmu, nie wizualnym testem gotowych klatek.

Nie ma zainstalowanego silnika Godot, więc GDScript przeszedł parser, lecz nie import i uruchomienie silnika. Nie wykonano APK/AAB/EXE, testu fizycznego Androida ani wielogodzinnej sesji. Rzeczywisty odczyt FPS na urządzeniu pokaże nowy licznik podczas gry.

Archiwa wcześniejszych raportów nie potwierdzają działania interfejsu 0.4.1.
