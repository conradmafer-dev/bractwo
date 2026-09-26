# Bractwo 0.8.13 — raport sprawdzenia

Data: 25.09.2026. Bazą jest pełna paczka **0.8.12**. Aktualizacja dotyczy wojownika (wewnętrzny identyfikator `knight`, nazwa w grze „Rycerz”), jego wyposażenia i interfejsu. Zachowano magię łowcy. Nie przebudowywano terenu ani dotychczasowych tabel łupów.

## Wykonane lokalnie

| Zakres | Wynik | Dowód |
| --- | --- | --- |
| Testy Python całego projektu | **652 / 652**, bez błędów | `qa_0.8.13/python_full.log` |
| W tym nowy moduł testów wojownika | **47 / 47** | `qa_0.8.13/fighter_tests.log`, `tests/test_fighter_0813.py` |
| Testy JavaScript | **81 / 81**, bez błędów | `qa_0.8.13/javascript.log` |
| Sprawdzenia wojownika w Chromium | **19 / 19**, bez wyjątków JavaScript | `qa_0.8.13/results.json`, `browser_run.log` |
| Regresja łowcy w Chromium na nowym kodzie | **13 / 13**, bez wyjątków JavaScript | `qa_0.8.13/ranger_regression/results.json`, `ranger_browser_regression.log` |
| Lokalny launcher, HTTP, WebSocket, zapis i restart procesu | **15 / 15** | `qa_0.8.13/local_process.log` |

Łącznie interfejs przeglądarkowy przeszedł **32 nazwane sprawdzenia w dwóch scenariuszach**; to nie 32 niezależne długie sesje gry. Zrzuty w starszych katalogach `qa_0.8.12` i wcześniejszych są historyczne. Nowe sprawdzenie łowcy znajduje się wyłącznie w `qa_0.8.13/ranger_regression/`.

## Co sprawdzono

Testy wojownika obejmują ręczny wybór i zapis stylu; walidację profesji, śmierci, walki i obecności mistrza; brak opłaty lub zużywania punktu; rzeczywistą KP kolczugi, tarczy i Obrony; działanie Pojedynku i wyłączenie premii przy broni oburęcznej; zmianę chwytu miecza wszechstronnego; kości i krytyki Walki wielką bronią; brak tej premii przy leczeniu; trzy typy mistrzostwa, pudła z Draśnięciem, śmierć celu i przyznanie nagrody, rzuty obronne przed Powaleniem, czas wstawania, pojedynczy osłabiony rzut ataku i odporności w PvP.

Drugi oddech sprawdzono przy zerowej manie, z limitem 60 sekund, skalowaniem i utrzymaniem odnowienia w zapisie. Zryw akcji sprawdzono przed/po poziomie 5, ze wszystkimi atakami danej profesji, bez resetowania głównej lub dodatkowej akcji, z odnowieniem 90 sekund oraz ochroną PvP, zasięgiem, ścianami i piętrami. Nowa zdolność i przyrost Drugiego oddechu pojawiają się w podsumowaniu awansu.

Migracja obejmuje nowe i zapisane postacie, jednorazowe przyznanie kolczugi/tarczy, pełny plecak, zachowanie UID i starego sprzętu, niezmienianie już posiadanego właściwego pancerza oraz wyłączenie sprzecznej konfiguracji tarcza–broń dwuręczna bez kasowania przedmiotu. Ponowne logowanie nie przyznaje zestawu drugi raz.

Dotychczasowe testy zachowano. Zaktualizowano oczekiwany numer wydania, liczbę zdolności i parametry Drugiego oddechu. Stary scenariusz PvP, który zakładał konkretną niską KP, jawnie zakłada kurtkę zamiast nowego zestawu startowego; nowy moduł testuje także rzeczywistą kolczugę i tarczę. Nie usuwano testów po zmianie wyników trafień.

JavaScript sprawdza m.in. ręczne potwierdzenie wyboru, warunki stylów, nowy slot, opisy i podsumowania Draśnięcia, efekty canvas bez niezbilansowanego `save/restore`, zasoby graficzne i ich zgodność pomiędzy klientami. Wcześniejsze testy ruchu, atlasu, pasków, łowcy i przesuwanych okien pozostają w zestawie.

## Interfejs WWW i granice testu

Chromium uruchamia **rzeczywisty kod WWW i rzeczywisty lokalny serwer aiohttp przez kontrolowany most WebSocket w Pythonie**. Pierwszy wybór, zmiana u mistrza, wyposażanie, chwyty, odnowienia, obrażenia, statusy i ruch przechodzą przez rzeczywiste handlery. Dla powtarzalności użyto kontrolowanego zegara i rzutów oraz wstrzymano autonomiczne AI potworów. Nie jest to test publicznej sieci, Railway ani długotrwałej rozgrywki.

Sprawdzono układy **1440×900, 390×844 i 844×390**. Kafelki stylów, potwierdzenie, ekwipunek z czterema slotami i opis tarczy są dostępne; otwarte okna nie blokują ruchu. Przy zerowej manie działa Drugi oddech, Zryw jest dostępny od piątego poziomu, a Osłabienie ma widoczny status i opis. Oddzielny scenariusz regresji łowcy sprawdza Znak, oplątanie, koncentrację, leczenie, skalowanie i uwalnianie drugiego klienta z pnączy w PvP.

Test procesu osobno uruchamia `run.py` przez rzeczywisty lokalny TCP/WebSocket, sprawdza pliki WWW bajt po bajcie (w tym nowe moduły i ikony), blokadę dostępu do plików prywatnych, dwa konta w jednym świecie, zapis, SIGTERM, integralność SQLite, kopię bazy, ponowne logowanie i ranking. Korzysta z tymczasowej bazy, nie z zapisu użytkownika.

## Środowisko i rzeczy nieuruchomione

Python **3.13.5**, aiohttp **3.13.3**, Node **22.16.0**, Chromium **144.0.7559.96**. Zachowano dotychczasowe `requirements.txt` z `aiohttp==3.13.5`; nie utworzono osobnego środowiska z tą przypiętą wersją.

**Godot: źródła zmienione, ale projekt nie był importowany, uruchamiany, kompilowany ani eksportowany w silniku.** Natywny interfejs i efekty nie mają weryfikacji ekranowej. Nie wykonano osobnego sprawdzenia parserem GDScript. Nie ma APK, AAB ani EXE.

**Docker nie został zbudowany. Railway nie zostało wdrożone ani zbadane na koncie użytkownika.** Nie przeprowadzono wielogodzinnych testów balansu, ekonomii, wydajności ani fizycznego urządzenia Android. Odnowienia 60/90 sekund, automatyczne wstawanie i zestaw startowy wymagają oceny w normalnej rozgrywce.

Oba wydania zawierają manifesty SHA-256. Skrypt pakujący sprawdza integralność ZIP, zgodność każdego pliku z manifestem oraz zgodność wspólnych plików serwera i WWW obu paczek. Wynik zostaje zapisany obok paczek w `BUILD_0.8.13_VALIDATION.json`.

## Odtworzenie

```sh
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.cjs
python tools/browser_0813_smoke.py
BRACTWO_QA_OUT=docs/qa_0.8.13/ranger_regression python tools/browser_0812_smoke.py
python tests/smoke_railway.py
```

Składnia zmiennej w czwartym wierszu dotyczy powłoki Unix; na Windows ustaw zmienną środowiskową przed uruchomieniem skryptu. Scenariusze przeglądarkowe wymagają Playwright i dostępnego Chromium (domyślnie `/usr/bin/chromium`). Nie są one wymagane do działania serwera gry.
