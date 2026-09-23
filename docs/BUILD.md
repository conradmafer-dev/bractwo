# Uruchamianie i eksport

## Klient WWW

Nie ma procesu kompilacji ani zależności npm. Pliki w `web/` są serwowane bezpośrednio przez Python. Klient korzysta z Canvas 2D i standardowego WebSocket. Serwer działa na Pythonie 3.11+ z biblioteką `aiohttp` (wersja w requirements.txt).

```bash
python -m pip install -r server/requirements.txt
python server/server.py --host 127.0.0.1 --port 8080 --db data/world.sqlite3
```

## Godot

Wersja docelowa: **4.5.1 Standard**, GDScript, renderer GL Compatibility. Zainstaluj szablony eksportu tej samej wersji w menu edytora: Editor → Manage Export Templates. Klient potrzebuje działającego serwera Python; plik wykonywalny nie uruchamia go samodzielnie.

Z głównego katalogu paczki (dostosuj nazwę polecenia `godot` do swojego systemu):

```bash
godot --headless --path client --import
godot --path client
godot --headless --path client --export-debug "Windows Desktop" ../builds/BractwoPogranicze.exe
godot --headless --path client --export-debug "Android" ../builds/BractwoPogranicze-test.apk
```

Ścieżka eksportu jest liczona względem projektu `client`. Katalog `builds` jest już w paczce. Przed eksportem Androida skonfiguruj JDK 17 i Android SDK zgodnie z dokumentacją wersji silnika. W Editor Settings → Export → Android ustaw Java SDK Path i Android SDK Path. Preset ma włączone uprawnienie INTERNET. Eksport debug używa lokalnego klucza debug Godota; nie dołączono żadnego keystore. To nie jest build do publikacji w Google Play.

Eksportów **nie wykonano w środowisku przygotowania paczki**. Sam udany eksport nie zastępuje testu na urządzeniu: należy sprawdzić dotyk, skalowanie UI, powrót z tła, rozłączenie i ponowne logowanie. `gdparse` sprawdza składnię GDScript, ale nie wykrywa wszystkich problemów typowania i API silnika.

Materiały źródłowe:

- [Oficjalny CLI Godot 4.5](https://docs.godotengine.org/en/4.5/tutorials/editor/command_line_tutorial.html)
- [Eksport na Androida](https://docs.godotengine.org/en/4.5/tutorials/export/exporting_for_android.html)
- [WebSocket w Godot](https://docs.godotengine.org/en/4.5/tutorials/networking/websocket.html)

## Testy wersji 0.6.0

```bash
python -m unittest discover -s tests -v
node --check web/game.js
node --test tests/test_client_runtime.cjs
python tools/check_surfaces.py
python tools/benchmark_living_world.py
```

Testy tworzą tymczasowe bazy i uruchamiają lokalne serwery; nie używają zapisu graczy. `check_surfaces.py` porównuje rzeczywiste klasyfikacje podłoża Python/JS; `benchmark_living_world.py` mierzy obciążenie symulacji przy 1 i 24 postaciach. Nie mierzy FPS. `check_expedition.py` pozostaje historycznym scenariuszem 0.3. Historyczny scenariusz przeglądarkowy 0.3 `tools/browser_smoke.cjs` wymaga Playwright i osobno zainstalowanego Chromium; instrukcja uruchomienia jest na początku pliku. `python tools/run_browser_smoke.py` uruchamia odizolowany serwer i cały scenariusz (wymaga tych samych narzędzi przeglądarkowych). Skrypt przeglądarkowy nie obejmuje księgi, podróży ani podziemi 0.4 i nie był wykonany dla tego wydania. Aktualny raport wykonanych prób znajduje się w TEST_REPORT.md; wcześniejsze obrazy i wyniki przeniesiono do archive_0.3/.

## Internetowy test zamknięty — następny etap

Uruchamiaj pojedynczy proces serwera dla jednego pliku SQLite. Dwa procesy nie synchronizują swoich światów w pamięci. Zapewnij trwały dysk na bazę, regularną kopię po bezpiecznym checkpointcie/zatrzymaniu i reverse proxy z poprawnym certyfikatem TLS. Proxy musi obsługiwać upgrade WebSocket dla `/ws`.

Klient WWW automatycznie używa `wss://`, jeśli strona działa pod HTTPS. W Godot wpisuje się `wss://twoja-domena/ws`. Nie wysyłaj danych logowania przez nieszyfrowane połączenie w publicznym internecie. Ten pakiet niczego samodzielnie nie wdraża i nie zawiera danych dostępu do hostingu.

Limity w kodzie to osłony prototypu. Nie przeprowadzono testów pojemności, pełnego audytu bezpieczeństwa ani testów w długich sesjach mobilnych.

Natywny klient ustawia `WebSocketPeer.inbound_buffer_size` na 8 MiB przed połączeniem: katalog kontynentu przekracza domyślny bufor. [Opis właściwości w Godot 4.5](https://docs.godotengine.org/en/4.5/classes/class_websocketpeer.html#class-websocketpeer-property-inbound-buffer-size).
