# Bractwo 0.8.15 — raport sprawdzenia

26.09.2026. Bazą jest przekazana pełna paczka 0.8.14. Jedyną zmianą mechaniki jest Odzyskanie mocy; nie wdrożono ukrywania atutów/czarów ani zwojów. Starsze raporty i katalogi QA są historyczne.

## Wykonane testy

| Sprawdzenie | Wynik | Dowód |
| --- | --- | --- |
| Pełna regresja serwera, unittest | **746/746** | `qa_0.8.15/server_tests.log` |
| Nowe testy Odzyskania mocy (wliczone w 746) | **24/24** | `qa_0.8.15/recovery_tests.log`, `tests/test_arcane_recovery_0815.py` |
| JavaScript / Node | **104/104** | `qa_0.8.15/node_tests.log` |
| Chromium, rzeczywisty interfejs i serwer | **13 sprawdzeń**, bez wyjątków JS | `qa_0.8.15/browser_results.json`, `browser.log` |
| Lokalny HTTP, natywny WebSocket, zapis i restart procesu | **17/17** | `qa_0.8.15/local_process.log` |
| Składnia Python/JavaScript, porównanie katalogu i skalowania | Poprawne | `qa_0.8.15/static_checks.json` |

Środowisko: Python 3.13.5, aiohttp 3.13.3, Node v22.16.0 i lokalny Chromium. Produkcyjny plik requirements nie został zmieniony (nadal przypina aiohttp 3.13.5); testy wykonano na zainstalowanym aiohttp 3.13.3. Ostrzeżenia aiohttp NotAppKeyWarning i czasu zadań asyncio są widoczne w logu, nie oznaczają nieudanych testów.

Pięć wcześniejszych testów Odzyskania mocy z 0.8.14 dostosowano do nowej reguły (zamiast sprawdzać czterosekundowy kanał i blokadę walki). Kontrole wersji HTTP wskazują teraz 0.8.15. Pozostałe testy mechanik zachowano. Statyczne porównanie potwierdza, że w katalogu czarodzieja/druida zmieniła się tylko definicja arcane_recovery, a funkcja obliczająca ilość many ma identyczną strukturę jak w 0.8.14.

## Zakres scenariuszy

Natychmiastowe +20 many na poziomie 1 oraz dotychczasowe skalowanie; brak kosztu złota/many; akcja dodatkowa bez modyfikowania głównej akcji, reakcji i mikstur. Użycie przy aktywnych znacznikach walki PvE/PvP, zachowanie kierunków ruchu, autoataku, zaznaczenia, kolejki czaru, koncentracji i ograniczeń PvP. Pełna mana bez utraty odnowienia, przycięcie do maksimum i prawidłowy komunikat dla ułamkowej brakującej many. Sprawdzono niewłaściwą klasę, śmierć, formę zwierzęcą, rozłączenie, nieprawidłowe cele, zajętą akcję dodatkową, serię 25 jednoczesnych żądań oraz granicę 180 sekund.

Mana i odnowienie zapisują się natychmiast w bazie; odnowienie z poprzedniej wersji jest respektowane. Próba użycia przez kanał lub komendę rytuału nie obchodzi ograniczeń. Rytuał już rozpoczęty pozostaje nietknięty przy odrzuconej próbie Odzyskania mocy. Rytuały nadal wymagają postoju poza walką i ukończenia kanału. Pasywna regeneracja nie została zmieniona.

## Interfejs

Sprawdzono przycisk w Atutach, księdze, pasku oraz klawisz F wynikający z rzeczywistej historii użyć. Aktualizacja przycisków przy wygaśnięciu samego odnowienia akcji dodatkowej, blokada przy pełnej manie i wyświetlanie 180-sekundowego odnowienia. Test z wciśniętym D i kliknięciem zdolności potwierdza rzeczywisty ruch serwera. Potwierdzono zachowanie nieposiadanych atutów i przyszłych czarów zgodnie z najnowszym, zawężonym zakresem.

Chromium ładuje rzeczywiste pliki WWW, lecz komunikacja WebSocket odbywa się przez kontrolowany most Python do rzeczywistego aiohttp. Zegar jest kontrolowany, AI potworów zatrzymane, konta i znaczniki walki testowe. Nie jest to test obciążenia ani długiej walki na hostingu. Rozdzielczości: 1440×900, 390×844 i 844×390. Zrzuty desktop i portrait sprawdzono wizualnie. Oddzielny test procesu używa natywnego TCP/WebSocket, uruchamia run.py, wykonuje Odzyskanie mocy, zatrzymuje proces, uruchamia go ponownie i sprawdza zachowany cooldown.

## Czego nie sprawdzono

Godot: zaktualizowano źródła przycisków i numer wersji, ale nie uruchomiono ani nie skompilowano klienta. Nie zbudowano Docker i nie wdrożono niczego na Railway. Paczki nie zawierają APK/AAB/EXE. Nie testowano wydajności wielu graczy ani długoterminowego balansu.

## Odtworzenie

Z pełnego pakietu (testowe zależności Playwright/Chromium nie należą do produkcyjnych requirements):

```text
python -m unittest discover -s tests -v
node --test tests/*.cjs
python tools/browser_0815_recovery.py
python tests/smoke_railway.py
```

Pliki manifestów obejmują rzeczywiste pliki danego ZIP-a. Integralność i hashe obu paczek oraz zgodność wspólnego kodu są sprawdzane po ich zbudowaniu. Nie dołącza się bazy gracza, kluczy ani plików środowiska.
