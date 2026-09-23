# Bractwo 0.6.0 — deployment na Railway

Projekt jest przygotowany tak, aby klient WWW i serwer gry działały z jednego serwisu Railway.

## Najprostsze wdrożenie

1. Wrzuć zawartość katalogu `Bractwo_0.6.0` do repozytorium GitHub.
2. W Railway utwórz usługę z repozytorium GitHub (`New` -> GitHub Repo).
3. Railway wykryje `Dockerfile` i uruchomi serwer automatycznie. Nie ustawiaj ręcznie portu.
4. W usłudze wybierz `Networking` -> `Generate Domain`.
5. Otwórz wygenerowany adres HTTPS. Gra powinna pojawić się od razu, a klient połączy się z `/ws` przez WSS.

## Trwały zapis świata i kont

Bez Volume gra działa, ale plik SQLite znajduje się na nietrwałym dysku wdrożenia i może zniknąć przy ponownym deployu.

Aby zachować konta i świat:

1. Dodaj Railway Volume do tej samej usługi.
2. Ustaw mount path na `/data`.
3. Zrób redeploy.

Serwer automatycznie wykrywa `RAILWAY_VOLUME_MOUNT_PATH` i zapisuje bazę jako `world.sqlite3` w zamontowanym Volume. Nie trzeba dodawać żadnej zmiennej ręcznie.

## Healthcheck (zalecane)

W ustawieniach usługi ustaw Healthcheck Path na:

`/health`

Endpoint zwraca JSON z `ok: true`, liczbą graczy i wersją serwera.

## Zmienne obsługiwane przez serwer

- `PORT` — port przydzielony przez Railway; odczytywany automatycznie.
- `GAME_HOST` — host nasłuchiwania; Dockerfile ustawia `0.0.0.0`.
- `RAILWAY_VOLUME_MOUNT_PATH` — po dołączeniu Volume wskazuje trwały katalog bazy.
- `BRACTWO_DB` — opcjonalna ręczna ścieżka do SQLite; ma pierwszeństwo przed Volume.

## Lokalny test obrazu Docker

```bash
docker build -t bractwo .
docker run --rm -p 8080:8080 -e PORT=8080 bractwo
```

Następnie otwórz `http://127.0.0.1:8080`.
