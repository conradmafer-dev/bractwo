# Bractwo 0.8.17 — raport sprawdzenia

26.09.2026. Baza: dostarczony pełny ZIP 0.8.16. Ten raport opisuje bieżącą
poprawkę. Starsze raporty, logi i zrzuty w paczce są historyczne.

## Odtworzony błąd w 0.8.16

Na rzeczywistych handlerach serwera, z zegarem testowym, stwierdzono:
1. Sam wybór potwora wykonuje Iskrę i blokuje główną akcję na 3 s.
2. Wskazanie ponownie tego samego potwora usuwa przyjęty Magiczny pocisk z kolejki.
3. Komenda ręcznego ataku tuż przed klatką symulacji zabiera gotową akcję
   oczekującemu zaklęciu; kolejny Spark opóźnia je o następną rundę.

## Wykonane sprawdzenia

| Test | Wynik | Dowód |
| --- | --- | --- |
| Python unittest: kompletna regresja | **803/803** | `qa_0.8.17/server_tests.log` |
| Nowe scenariusze różdżki, wliczone w powyższy wynik | **30/30** | `qa_0.8.17/wand_tests.log` |
| JavaScript / Node | **117/117** | `qa_0.8.17/node_tests.log` |
| Chromium + rzeczywiste handlery serwera | **16 sprawdzeń** | `qa_0.8.17/browser_results.json`, `browser.log` |
| Lokalny proces + TCP/WebSocket + zapis/restart | **17/17** | `qa_0.8.17/local_process.log` |
| Składnia Python i JS, zakres zmian | Poprawne | `qa_0.8.17/static_checks.json` |

Zachowano wszystkie stare testy. Testy, które zakładały automatyczny Spark po
samym zaznaczeniu, inicjują teraz jawny atak; sprawdzają nadal trzysekundową akcję
i pierwszeństwo czaru. Test odblokowania automatycznego PvP wykonuje łowca z
łukiem; dla maga osobny nowy przypadek sprawdza brak niezamówionej Iskry.
Pierwsze synchroniczne uruchomienie pełnej regresji zostało przerwane limitem
czasu narzędzia; komplet uruchomiono ponownie i zakończył się powyższym wynikiem.

Środowisko: Python **3.13.5**, aiohttp **3.13.3**, Node **v22.16.0**, lokalny Chromium.
Produkcyjne `requirements.txt` pozostało niezmienione: **aiohttp==3.13.5**.
Testy nie są deklarowane jako wykonane na innym numerze biblioteki. Ostrzeżenia
asyncio/AppKey w logach nie są pomijanymi niepowodzeniami testów.

## Pokrycie

- Wybór celu różdżką nie zmienia HP, many, akcji ani ruchu. Potem zaklęcie z
  gotowej akcji działa od razu. Różdżka nie wraca samoczynnie do ostrzału.
- Spacja/przycisk wciąż strzelają 1k4. Ręczny atak i czar nie sumują się w jednej
  głównej akcji. Przytrzymanie Spacji nie odbiera terminu oczekującemu czarowi.
- Wskazanie tego samego celu zachowuje komendę i termin. Inny cel / odznaczenie
  ją kasuje. Nowy czar zastępuje poprzedni, także na granicy gotowości serwera.
- Utrata życia celu, piętra, zasięgu, linii widzenia i many jest sprawdzana ponownie.
  Nieudana komenda nie odpala zastępczego Sparka. Ochrona PvP pozostaje.
- Reakcja Tarcza i Odzyskanie mocy nie kasują kolejki ani ruchu. Odnowienie 180 s
  i stopniowa mana pozostają. Stare zapisy nadal działają bez migracji schematu.
- Rycerz, łowca i druid z bronią wręcz nadal autoatakują. Kontrola zależy od broni,
  nie od klasy: także zwykła broń w dłoni maga jest traktowana normalnie.
- Wszystkie obecne fokusy, w tym ulepszone różdżki, są rozpoznane, a forma zwierzęca
  zachowuje swoje ataki. Nowe prywatne pole poprawnie opisuje zachowanie broni.
- GUI: rzeczywiste kliknięcie na liście potworów, 4, F, F1, Spacja, hotbar i księga,
  potwierdzenie kolejki, ruch oraz anulowanie. Rozdzielczości 1440×900, 390×844,
  844×390; bez poziomego przepełnienia strony. Zrzuty obejrzano wizualnie.

## Granice sprawdzenia

Chromium nie może tu otworzyć lokalnego HTTP (`ERR_BLOCKED_BY_ADMINISTRATOR`),
co sprawdzono bezpośrednio przed testem. Kod WWW osadzono w stronie testowej,
a WebSocket obsługuje kontrolowany most Python do rzeczywistego aiohttp. Nie
zastąpiono obrażeń ani stanu postaci atrapami. Zegar jest kontrolowany, AI
potworów zatrzymana, używany jest produkcyjny cykl akcji. Test ma odporny cel
z dodatkowym HP, nie służy do oceny balansu lub skali pasków HP przeciwników.

Osobno wykonano natywny TCP/WebSocket i dwa uruchomienia prawdziwego procesu,
z SIGTERM, kopią i wczytaniem SQLite oraz zachowaniem ustawień i odnowień.
Nie uruchomiono Godota, nie wygenerowano APK/AAB/EXE, nie zbudowano Dockera i nie
wdrożono niczego na koncie Railway. Brak testu fizycznego urządzenia Android
oraz długiej rozgrywki. Źródła Godota mają poprawione opisy i statusy kolejki.

## Odtworzenie

```text
python -m unittest discover -s tests -v
node --test tests/*.cjs
python tools/browser_0817_wand.py
python tests/smoke_railway.py
```

Skrypty odtworzenia testów znajdują się w pełnym ZIP-ie źródeł.
Przeglądarka wymaga testowych zależności Playwright i Chromium. Nie dodano ich
do produkcyjnych requirements. Oba archiwa mają osobne manifesty SHA-256;
sprawdzono integralność ZIP-ów i zgodność wszystkich wymienionych plików.
