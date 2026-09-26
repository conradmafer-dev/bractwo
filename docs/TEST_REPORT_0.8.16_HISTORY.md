# Bractwo 0.8.16 — raport sprawdzenia

26.09.2026. Baza: dostarczony pełny ZIP 0.8.15. Aktualizacja wygładza wyłącznie
maksymalną manę i ilość Odzyskania mocy. Starsze raporty/QA są historyczne.

## Wyniki wykonanych testów

| Sprawdzenie | Wynik | Plik dowodowy |
| --- | --- | --- |
| Python / unittest, pełna regresja | **773/773** | `qa_0.8.16/server_tests.log` |
| Nowe testy many (wliczone w 773) | **27/27** | `qa_0.8.16/mana_tests.log` |
| JavaScript / Node | **110/110** | `qa_0.8.16/node_tests.log` |
| Chromium + rzeczywisty kod serwera | **15 sprawdzeń** | `qa_0.8.16/browser_results.json`, `browser.log` |
| Lokalny TCP/WebSocket, proces, zapis/restart | **17/17** | `qa_0.8.16/local_process.log` |
| Składnia Python/JS i kontrola zakresu zmian | Poprawne | `qa_0.8.16/static_checks.json` |

Baza 0.8.15 przeszła przed zmianami 746 testów Python. Zaktualizowano stare
oczekiwania dotyczące skokowej many (m.in. +80 na 10. poziomie, brak przyrostu na
11., 40 many łowcy na poziomach 2/8), wiersza Odzyskania mocy na pośrednim poziomie
oraz numeru wersji i migracji. Nie usunięto żadnego testu. Dołożono 27 testów
Python i 6 Node; nie sumuje się ponownie podzbioru 27 z całą regresją.

Środowisko: Python **3.13.5**, aiohttp **3.13.3**, Node **v22.16.0**, lokalny Chromium.
Produkcyjny `requirements.txt` pozostał niezmieniony: przypina aiohttp 3.13.5.
Nie twierdzimy, że testy wykonano na innym numerze biblioteki. Logi asyncio mogą
zawierać ostrzeżenia o czasie zadań, a aiohttp o AppKey; końcowa regresja jest OK.

## Co sprawdzono

Dokładne uzgodnione liczby na każdym poziomie 1–10, stałe przyrosty 10–20,
niezmienione pule na wszystkich progach aż do końcowego limitu, całkowite liczby,
brak zmniejszania pul i brak rosnącego zasobu po dotychczasowym limicie. Oddzielna
premia Skupienia, niezmieniona mana wojownika oraz niezmienione koszty i kręgi.

Rzeczywiste rzucenie Odzyskania mocy na poziomach pośrednich (w walce), przycięcie
do brakującej many, brak resetu 180 sekund przy awansie. Profile księgi, karta
Atutów, paski, F i następny przyrost odpowiadają obliczeniom serwera.

Kaskada ma osobne wiersze Mana i Odzyskanie mocy. Wielopoziomowa nagroda i kolejne
pojedyncze awanse dają takie same liczby. Nowa mana nie odblokowuje czarów wcześniej.
Stare niezamknięte podsumowania zachowują historyczne przyrosty i identyfikatory;
nie łączą się z nowymi batchami innej wersji. Migracja nie tworzy dawnych awansów.

Migracje wersji many 0/1/2 do 3, w tym stary łowca. Zachowanie procentu pełnej,
pustej i częściowej puli dla wszystkich klas, premii Skupienia, przedmiotów,
HP/XP/złota/wyborów oraz odnowień. Wielokrotne wczytanie aktualnego zapisu nie
odnawia ani ponownie nie skaluje many. Sprawdzono zapis i odczyt SQLite.

## Zakres przeglądarki

Rzeczywisty interfejs WWW i autorytatywny serwer, z testowym zegarem, zatrzymaną AI
potworów i kontrolowanym mostem Python WebSocket. Bezpośrednie lokalne adresy są
blokowane w testowym Chromium (`ERR_BLOCKED_BY_ADMINISTRATOR`), więc pliki klienta
są osadzane w stronie testowej, a most przesyła wiadomości do rzeczywistego aiohttp.
Dane postaci nie są atrapami UI. Oddzielny test procesu korzysta z natywnego TCP i
WebSocket, bez przeglądarkowego mostu.

Rozdzielczości: **1440×900, 390×844, 844×390**. Sprawdzono kaskadę, licznik many,
opis puli, Atuty, księgę, faktyczne kliknięcie Odzyskania mocy i skrót F. Osobno
sprawdzono nowe pule/awanse druida, łowcy i wojownika. Zrzuty desktop i portrait
obejrzano wizualnie. Nie jest to benchmark płynności ani test długiej rozgrywki.

## Czego nie wykonano

Nie uruchomiono ani nie skompilowano Godota. Źródła pobierają pule i przyrosty
z serwera; zaktualizowano dymek many i numer wersji. Nie zbudowano obrazu Docker,
nie wdrożono aktualizacji na Railway, nie przetestowano rzeczywistych urządzeń
Android i nie wygenerowano APK/AAB/EXE. Nie deklarujemy długoterminowego balansu.

## Odtworzenie testów

```text
python -m unittest discover -s tests -v
node --test tests/*.cjs
python tools/browser_0816_mana.py
python tests/smoke_railway.py
```

Test przeglądarkowy wymaga testowych zależności Playwright i Chromium; nie są one
dodane do produkcyjnych requirements. ZIP-y są sprawdzane po utworzeniu, z osobnym
manifestem plików dla pełnych źródeł i płaskiej paczki Railway. Nie zawierają bazy
gracza, kluczy ani plików środowiska.
