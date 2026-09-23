# Raport weryfikacji — Bractwo 0.4.0

Data: 2026-09-22. Dotyczy źródeł w tej paczce. Raporty i obrazy wersji 0.3 znajdują się w `archive_0.3/` i nie stanowią dowodu sprawdzenia aktualnego interfejsu.

## Wykonane sprawdzenia

| Zakres | Wynik |
| --- | --- |
| `python3 -m unittest discover -s tests -v` | **43/43 zaliczone**, końcowe wykonanie: 11,369 s |
| Python: server.py, world_content.py, progression.py | Kompilacja składniowa zaliczona |
| JavaScript: `node --check web/game.js` | Zaliczone |
| GDScript: `gdparse client/scripts/*.gd` | Pięć plików przeszło parser składni |
| Bash: `bash -n start_unix.sh` | Zaliczone |

Surowy log końcowego zestawu serwera: `server-tests-0.4.txt`. Testy używają rzeczywistych lokalnych sesji WebSocket i tymczasowych baz SQLite. Czas jest kontrolowany, a pozycje, poziomy i zasoby ustawiane w fixture'ach w celu sprawdzenia konkretnych reguł. Nie oznacza to rozegrania postacią całej drogi do poziomu 100. W produkcyjnym protokole nie dodano komend ustawiających poziom lub pozycję.

33 zachowane testy obejmują wcześniejsze zasady kont, zapisu, migracji, walki, PvP, drużyn, ekwipunku i zadań. Dziesięć nowych testów obejmuje:

1. Rozmiar kontynentu, odstępy miast oraz wszystkie 7729 punkty odrodzenia i 40 przejść bez kolizji.
2. Przejście po siatce z rzeczywistą kolizją między wejściem a dalszymi komnatami wszystkich 20 pięter podziemi.
3. Autorytet schodów, próg ostatniego piętra, blokadę PvP, powrót i zapis piętra.
4. Poziom, profesję, promocję, manę, odnowienie czarów i wygaśnięcie przyspieszenia.
5. Jednorazową promocję, punkty specjalizacji, błogosławieństwo, bank, depozyt, zapis i odrodzenie w wybranym mieście.
6. Wymagania kapitana, poziomu, ceny i braku walki przy podróży.
7. Koszty run, trening, zakup i brak obrażeń pomiędzy piętrami.
8. Rozwój umiejętności, lokalne migawki i ochronę prywatnych danych.
9. Wymagania nowych mikstur i odblokowywanie zadań.
10. Odrzucanie nieprawidłowych parametrów i zdalnych prób usług.

Przegląd katalogu serwera potwierdził 20 regionów, 5 miast, 10 podziemi po dwa piętra, 1435 łowisk, 39 typów wrogów, 7729 punktów respawnu, 109 odkryć, 30 zadań, 53 szablony sprzętu, 8 mikstur, 10 czarów i 3 runy. Te liczby określają rozmiar danych, nie ilość unikalnej ręcznie przygotowanej zawartości.

## Granice weryfikacji

**Nie uruchomiono graficznie klienta WWW 0.4.** Podgląd został zablokowany przez politykę przeglądarki w środowisku pracy. Nie wykonano alternatywnego obejścia. Brak zrzutów potwierdzających aktualny HUD, atlas lub układ telefonu; analiza kodu i kontrola składni nie zastępują takiego sprawdzenia.

**Nie uruchomiono silnika Godot i nie wykonano APK/AAB/EXE.** Parser GDScript nie potwierdza wszystkich typów, API, zasobów i zachowań silnika. Nie testowano fizycznego Androida, pracy w tle, wydajności renderowania ani sieci mobilnej.

Wcześniejsza syntetyczna próba serwera z 24 rozmieszczonymi postaciami i 7729 potworami dała średnio około 9,1 ms na krok symulacji i 12,5 ms na przygotowanie 24 migawek. To pomiar laboratoryjny w tym środowisku, nie test obciążeniowy publicznego serwera ani wynik FPS klienta.

Do próby z graczem pozostają długie trasy, tempo progresji, ceny podróży i zapasów, walki z nowymi bossami oraz różnorodność dużych regionów. Nie wykonano pełnego wielogodzinnego przejścia wysokich poziomów.
