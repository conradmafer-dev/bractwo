# Bractwo 0.8.18 UI_21 — magia i żywioły

Przegląd całego katalogu 99 czarów, przemian i zdolności magicznych.
Rozbudowane animacje błyskawic, ognia, lodu, pnączy, leczenia, teleportacji,
barier i trwałych pól. Efekty trafienia są związane z rzeczywistym działaniem
czaru na serwerze. Zachowane obrażenia, koszty, zasięgi i koncentracja.
Paczka zawiera także wszystkie zmiany świata i łupów z UI_20.

[Opis aktualizacji i weryfikacji](docs/UI_21_SPELL_EFFECTS.md) ·
[Pełny audyt katalogu](docs/UI_21_SPELL_AUDIT.md).

## Railway / GitHub

Zawartość **RAILWAY_GITHUB_READY** umieść w głównym katalogu istniejącego
repozytorium. `Dockerfile`, `run.py`, `requirements.txt`, `server/` i `web/`
mają być obok siebie. Zachowaj bazę graczy, wolumen i zmienne środowiska.
Wdróż cały serwer i klienta razem, potem odśwież stronę i zaloguj się ponownie.
Logowanie oraz `/health` pokazują **UI_21**. Reset postaci nie jest potrzebny.
Paczka nie została wdrożona automatycznie.

## Lokalnie i Godot

Uruchom `start_windows.bat` lub `./start_unix.sh`, potem otwórz
`http://127.0.0.1:8080`. Nie uruchamiaj gry przez samo otwarcie HTML.
**FULL_SOURCE** zawiera także `client/project.godot`, testy i narzędzia.
Natywny klient wymaga ponownego importu i eksportu z Godota.
Nie dołączono nowego APK; źródła natywne sprawdzono w kodzie, bez dostępnego
silnika do uruchomienia w tej sesji.

## Weryfikacja

Bieżący raport: `docs/qa_0.8.18/ui21/summary.json`.
Testy przeglądarki korzystają z rzeczywistego HTTP i WebSocket oraz osobnej
bazy w pamięci. Nie korzystają z kont produkcyjnych.

Poprzednie aktualizacje: [UI_20 — kontynent i łupy](docs/UI_20_WORLD.md), [UI_19](docs/UI_19_WORLD.md),
[UI_18 — odrodzenie w ostatnim mieście](docs/UI_18_RESPAWN_CITY.md).
