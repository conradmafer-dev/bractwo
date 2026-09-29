# Mobile01 — mobilny HUD na bazie 0.8.17

Kompaktowy status i mapa, stałe sterowanie, przewijany pasek zajętych czarów oraz menu i czat na żądanie. Reguły różdżki i many bez zmian. [Opis zmian, instalacja i testy Mobile01](docs/MOBILE_01.md).

---

# Bractwo 0.8.17 — różdżka nie przeszkadza czarom

Aktualizacja na bazie **0.8.16**. Poprawia wyłącznie współpracę wyboru celu,
zwykłego strzału różdżką i ręcznie rzucanych zaklęć. Zachowuje stopniowy przyrost
many, Odzyskanie mocy w walce, wszystkie klasy, przedmioty i dotychczasowy świat.

## Zaznaczenie to cel dla magii, nie automatyczny strzał

Gdy trzymasz **różdżkę / fokus czarodzieja**, wybranie potwora lub gracza nie
uruchamia Iskry i nie zużywa gotowej akcji. Wybierz przeciwnika i użyj czaru
z paska, księgi, klawiszy 1–0 / − / = / F1–F12 albo skrótu F.

Iskra **1k4** pozostaje pod **Spacją i przyciskiem Atakuj**. Przytrzymanie ataku
nadal ponawia próbę użycia broni, ale nie ma pierwszeństwa przed oczekującym
czarem. Sama różdżka nie wznawia strzelania po zakończeniu zaklęcia.

Zmiana dotyczy rodzaju wyposażenia, a nie zakazu dla całej klasy. **Łuki, miecze,
laski do walki wręcz i ataki przemian nadal korzystają z dotychczasowego autoataku.**
Czarodziej po założeniu zwykłej broni wręcz również zachowuje jej zwykłe zasady.
Wybrany cel nadal jest dostępny dla zaklęć i poleceń towarzysza.

## Jedno wybrane zaklęcie ma pierwszeństwo

Jeżeli trwa odnowienie głównej akcji po poprzednim czarze lub ręcznym strzale,
jedno użycie zaklęcia czeka na jej zakończenie. Pasek, przycisk F i księga pokazują
**„Za … s”**. Nie trzeba trafiać naciśnięciem w konkretną chwilę między atakami.

- Powtórne wskazanie **tego samego** przeciwnika nie kasuje polecenia.
- Spacja ani pakiet ataku przychodzący tuż przed klatką serwera nie zabierają
  głównej akcji przyjętemu już zaklęciu.
- Kolejny czar główny zastępuje poprzedni: nie tworzy się długa lista rzucań.
- Zmiana celu lub odznaczenie anuluje oczekujący czar. Nie przenosi go potajemnie
  na nowego potwora albo gracza.
- Nowy czar wykonany natychmiast na gotowej akcji usuwa stare zaległe polecenie;
  nie pojawia się później dodatkowe, niezamierzone rzucenie.
- Odzyskanie mocy jako akcja dodatkowa i włączenie Tarczy jako reakcji nie kasują
  oczekującej głównej akcji.

**Nie dodano drugiej akcji ani darmowego rzucania po strzale.** Atak bronią i czar
nadal dzielą trzysekundowe odnowienie. Przyjęta komenda nie pobiera many z góry;
rzut ponownie sprawdza zasięg, ściany, piętro, życie celu, manę i ochronę PvP.
Nieudane lub anulowane rzucenie nie uruchamia zastępczej Iskry.

To nie jest automatyczne powtarzanie wybranej sztuczki: jedno naciśnięcie oznacza
jedno zaklęcie. Do kolejnego użycia służy następne naciśnięcie.

## Aktualizacja

1. Zatrzymaj stary serwer i zrób kopię `data/world.sqlite3`
   (na Railway: dotychczasowa baza `/data/world.sqlite3`).
2. Podmień **serwer oraz cały katalog `web` razem**. Zachowaj bazę i wolumen.
3. Lokalnie uruchom `start_windows.bat` / `./start_unix.sh` z folderu tej wersji
   i otwórz `http://127.0.0.1:8080`. Odśwież grę **Ctrl+F5**.
4. Nie otwieraj starego `web/index.html` ani nie pozostawiaj starego procesu
   serwera na porcie 8080.

**Reset postaci nie jest potrzebny.** Nie zmieniono schematu zapisu ani wersji
reguł many (nadal 3). Zwykłe logowanie nie odnawia many i zdolności. Niewykonane
polecenia bojowe nie zapisują się między sesjami, tak jak wcześniej.

Pełny ZIP ma katalog **Bractwo_0.8.17**, w tym projekt Godota
`client/project.godot`. Paczka Railway ma `Dockerfile`, `run.py`, `server` i `web`
bezpośrednio w głównym katalogu. Nie wysyłaj na GitHub bazy gracza ani samego ZIP-a.

## Sprawdzenie i zakres

**803 testy Python, 117 testów JavaScript, 16 sprawdzeń interfejsu Chromium,
17 sprawdzeń lokalnego startu/zapisu/restartu.** Raport i logi:
`docs/TEST_REPORT.md`, `docs/qa_0.8.17/`. Aktualizacja nie dodaje zwojów, nie
przebudowuje Atutów ani nie zmienia kosztów, kości i progresji.

Test przeglądarkowy korzystał z kontrolowanego mostu WebSocket do rzeczywistego
serwera: bezpośredni loopback Chromium jest blokowany przez środowisko testowe.
Oddzielny test procesu używa natywnego TCP/WebSocket. AI potworów w teście UI
była zatrzymana, zegar kontrolowany. To nie jest benchmark ani długi test balansu.

Źródła Godota są poprawione, ale silnik nie był uruchamiany ani kompilowany.
Nie zbudowano Dockera, nie wykonano wdrożenia Railway. Paczki nie zawierają
APK, AAB, EXE ani prywatnej bazy. Protokół: `docs/PROTOCOL_0.8.17.md`.
