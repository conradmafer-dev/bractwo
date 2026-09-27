# Bractwo 0.8.11 — aktualizacja istniejącej usługi Railway

Ta paczka aktualizuje kod wersji 0.8.10 do **0.8.11: ruch przy zmianie celu i otwartych oknach, poprawiony rozwój i interaktywny atlas**. Zawiera serwer i kompletny klient WWW, nie jest plikiem APK ani bazą kont. Wersja FULL_SOURCE zawiera dodatkowo źródła Godota.

## Z 0.8.10 do 0.8.11

Zachowaj dotychczasowe repozytorium/usługę Bractwa oraz **ten sam trwały dysk**. Przed wdrożeniem zabezpiecz kopię bazy. Nie zakładaj nowego pustego wolumenu zamiast obecnego i nie usuwaj starej bazy.

Rozpakuj ZIP i podmień zawartość repozytorium. Nie wysyłaj samego archiwum, plików bazy ani katalogu obejmującego całą wersję. W głównym katalogu muszą znajdować się `Dockerfile`, `run.py`, `requirements.txt`, `server/` i `web/`. Wgraj razem zaktualizowany `server/server.py` oraz cały katalog `web/`, w tym nowy `web/atlas_map.js`, zmieniony `web/game.js` i `web/windows.css`. Nowy `server/progression_guide.py` dostarcza rzeczywiste progi rozwoju klas. Stary serwer nie udostępnia nowego skryptu atlasu. Zachowano wszystkie zasoby przedmiotów i potworów z 0.8.10.

Po zatwierdzeniu kodu uruchom wdrożenie podłączonej gałęzi. Nie podmieniaj usługi Alien Colonies ani innej gry. Ta wersja nadal wymaga jednej repliki/procesu, który prowadzi wspólny świat i SQLite.

## Ustawienia tej paczki

```text
Volume Mount Path: /data
Root Directory: /
Custom Build Command: puste
Custom Start Command: puste (CMD jest w Dockerfile)
Healthcheck Path: /health
Replicas: 1
Public domain target port: 8080
```

Zmienne są także w `RAILWAY_VARIABLES.txt`:

```dotenv
PORT=8080
BRACTWO_DB_PATH=/data/world.sqlite3
RAILWAY_DEPLOYMENT_DRAINING_SECONDS=30
```

Nie zmieniaj ścieżki, gdy istniejąca instalacja już zapisuje bazę w innym poprawnym katalogu swojego wolumenu. Launcher celowo odmawia startu na Railway bez dołączonego trwałego dysku lub przy próbie zapisu poza nim. Prawdziwe podłączenie wolumenu jest wymagane; ręczne dopisanie zmiennej jego ścieżki nie tworzy dysku.

Launcher `run.py` wykonuje kopię istniejącej bazy przed startem (do pięciu plików w `backups` obok bazy), a przy SIGTERM zapisuje graczy i zamyka połączenia. To zabezpieczenie **na tym samym dysku**, nie zamiennik niezależnej kopii zapasowej. Nie usuwa kont ani ekwipunku.

## Sprawdzenie po wdrożeniu

Wejdź pod dotychczasowy adres gry. `/health` powinno zwrócić `ok: true` i `version: "0.8.11"`. Zaloguj się starym kontem, sprawdź ciągły ruch przy zmianie celu, E otwierające i zamykające Świat oraz zoom i rzekę w Atlasie. Nie potrzebujesz nowego konta. Przy starych grafikach lub skryptach odśwież stronę Ctrl+F5. Serwer i klient WWW muszą pochodzić z tej samej paczki; lokalnego klienta Godot trzeba osobno zaktualizować/przebudować.

## Zakres weryfikacji

Sprawdzono lokalne uruchamianie rzeczywistego procesu `run.py`, natywne połączenia HTTP/WebSocket, dwa konta we wspólnym świecie, zamknięcie SIGTERM, SQLite i ponowne logowanie po restarcie. Testy odbyły się lokalnie, nie na koncie Railway. Obrazu Docker nie budowano. Właściwy raport: `TEST_REPORT.md`; starsze raporty opisują wcześniejsze wersje.

Kopia zapisu i kontrola właściwej usługi/wolumenu pozostają potrzebne przed podmianą działającego serwera.

Ścieżki `/data`, `/health`, numer portu i wymaganie jednego procesu wynikają z konfiguracji tej paczki. Ustawienia platformy odziedziczono po działającej konfiguracji projektu; tej aktualizacji nie wdrożono na koncie Railway.

Nie dodano migracji względem 0.8.10. Przy aktualizacji ze starszych wersji mikstury nadal migrują jednorazowo ze starych liczników do plecaka. Nie otwieraj zmigrowanej bazy starszym serwerem. Cofając wersję, przywróć też kopię bazy sprzed aktualizacji. Odkryte źródła łupów zaczynają zapisywać się od nowych zdobyczy; nie są zgadywane ze starego ekwipunku.
