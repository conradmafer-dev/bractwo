# Bractwo 0.8.12 — raport sprawdzenia

Data: 25.09.2026. Bazą jest pełna paczka 0.8.11. Aktualizacja dotyczy łowcy; nie zmieniano mechanik pozostałych profesji, lootu, terenu ani ruchu.

## Wykonane lokalnie

| Zakres | Wynik | Dowód |
| --- | --- | --- |
| Testy Python całego projektu | **604 / 604**, bez błędów | qa_0.8.12/python_full.log |
| W tym nowe testy łowcy | **43 / 43** | tests/test_ranger_0812.py |
| Testy JavaScript | **72 / 72**, bez błędów | qa_0.8.12/node_full.log |
| Scenariusze Chromium | **13 / 13**, zero błędów JavaScript | qa_0.8.12/results.json, browser.log |
| Lokalny launcher, HTTP, WebSocket, zapis i restart procesu | **15 / 15** | qa_0.8.12/local_process.log |

Python obejmuje nowe bramki czarów i pulę many, bezpłatny Znak, wspólne odnowienie i jego zachowanie przy zmianie celu/śmierci/logowaniu, źródła dodatkowych obrażeń, przygotowanie jednego trafienia, pudło i śmiertelny cios, zajętą akcję dodatkową, udaną/nieudaną obronę, przewagę dużego celu, wszystkie dziesięć tyknięć, brak aktualizacji już opłaconych obrażeń po awansie, akcje ucieczki, koncentrację, pomoc drużynową, ochronę PvP, zabicie okresowym efektem i PD, przyrosty po awansie oraz migrację many dokładnie raz. Dotychczasowe testy bram i kosztów łowcy zostały zaktualizowane do nowych wymagań, a nie usunięte.

JavaScript obejmuje dotychczasowy HUD/ekwipunek/atlas/sterowanie oraz siedem nowych sprawdzeń: bramki na profesję, komunikat koncentracji, poprawne i zbilansowane komendy canvas, brak efektu celu na samym rzucającym, jeden czytelny symbol przy wielu znakach, brak pozostałości grafiki po wygaśnięciu i tę samą nową ikonę w obu klientach.

## Interfejs WWW i ograniczenia testu

Chromium używa rzeczywistego kodu WWW oraz rzeczywistego lokalnego serwera aiohttp przez **kontrolowany most WebSocket w Pythonie**. Nie jest to badanie publicznej sieci ani wdrożenia Railway. Logowanie, skróty, autoatak, czary, wydawanie many, koncentracja, opisy i przycisk uwalniania działają przez prawdziwe handlery. Dla powtarzalności test ma kontrolowany zegar i rzuty, zatrzymaną sztuczną inteligencję potworów oraz syntetyczną postać/dużo HP celu. Zachowanie AI sprawdzają testy serwera. Zablokowanie akcji do wybranej chwili jest ustawieniem scenariusza testowego, nie zmianą czasu ataku w grze.

Sprawdzono 1440×900, 390×844 i 844×390. Drugi faktyczny klient WWW otrzymuje pnącza w PvP i korzysta z przycisku „Wyrwij się”, z zużyciem głównej akcji. Testy nie są wielogodzinnym sprawdzeniem balansu, wydajności ani ekonomii. Zrzuty są w qa_0.8.12/.

Lokalny test procesu osobno uruchamia run.py, sprawdza wszystkie pliki WWW bajt po bajcie, niedostępność prywatnych plików przez HTTP, dwuosobowe połączenie, zapis kont, kopię bazy przed restartem, ponowne logowanie i ranking. Używa wyłącznie tymczasowej bazy.

## Środowisko i rzeczy nieuruchomione

Środowisko testowe: Python 3.13.5, aiohttp 3.13.3, Node i Chromium z kontenera. Zachowano dotychczasowy requirements.txt z aiohttp==3.13.5; nie budowano nowego obrazu Docker ani osobnego środowiska z tą przypiętą wersją.

Źródła Godota są zaktualizowane (bramki, pasek, koszt Znaku, gotowość, koncentracja, grafika i przycisk uwalniania), lecz **nie były importowane, uruchamiane, kompilowane ani eksportowane w silniku**. Nie ma APK, AAB ani EXE. Nie wykonywano wdrożenia na koncie Railway. Nie twierdzimy, że sprawdzono publiczny serwer lub urządzenie Android.

Oba wydania zawierają manifest SHA-256. Integralność ZIP i zgodność każdego pliku z manifestem sprawdza skrypt pakujący; podsumowanie jest w pliku BUILD_0.8.12_VALIDATION.json obok ZIP-ów.

## Odtworzenie testów

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.cjs
python tools/browser_0812_smoke.py
python tests/smoke_railway.py
```

Test przeglądarkowy wymaga dodatkowo Playwright i /usr/bin/chromium. Nie są potrzebne do działania produkcyjnego serwera.
