# Bractwo 0.8.18 UI_22 — konta Google

Wejście do gry wymaga logowania przez Google. Jedno konto Google może mieć
maksymalnie **4 postacie**, wliczając postacie offline i przypisane stare zapisy.
Limit obowiązuje na serwerze i w bazie danych. Dotychczasową postać można
przypisać po zalogowaniu przez Google i potwierdzeniu jej starego hasła.
Postęp, wyposażenie i nazwa postaci zostają zachowane.

Paczka zawiera także świat i łupy z UI_20 oraz animacje czarów z UI_21.

## Konfiguracja przed wdrożeniem

W Google Cloud utwórz klienta OAuth typu **Web application** i dodaj adres
strony gry do **Authorized JavaScript origins**. Na Railway ustaw:

```text
GOOGLE_CLIENT_ID=TWÓJ_IDENTYFIKATOR.apps.googleusercontent.com
GOOGLE_AUTH_ORIGIN=https://TWOJA-DOMENA-GRY
```

Origin to dokładnie protokół i domena, bez ścieżki. Oba ustawienia muszą
odpowiadać konfiguracji Google. Ta integracja nie potrzebuje Client Secret.
Bez poprawnej konfiguracji strona pokaże komunikat, a serwer odmówi logowania;
nie ma obejścia przez dawne hasło ani anonimowe tworzenie postaci.

[Pełna instrukcja konfiguracji, migracji i testów](docs/UI_22_GOOGLE_ACCOUNTS.md).

## Railway / GitHub

Zawartość **RAILWAY_GITHUB_READY** umieść w głównym katalogu istniejącego
repozytorium. `Dockerfile`, `run.py`, `requirements.txt`, `server/` i `web/`
mają być obok siebie. Zachowaj bazę graczy, wolumen i istniejące zmienne.
Używaj jednej repliki serwera. Ustaw parametry Google przed wdrożeniem
i wdróż cały serwer razem z klientem. Odśwież stronę po aktualizacji.
Ekran wejścia oraz `/health` pokazują **UI_22**. Reset postaci nie jest potrzebny.
Paczka nie została wdrożona automatycznie.

## Lokalnie i źródła Godota

Skonfiguruj osobnego klienta Google z originem `http://localhost:8080`, ustaw
`GOOGLE_CLIENT_ID` oraz `GOOGLE_AUTH_ORIGIN=http://localhost:8080`, uruchom
`start_windows.bat` lub `./start_unix.sh` i otwórz ten sam adres.
Nie uruchamiaj gry przez samo otwarcie HTML.

Logowanie UI_22 jest przeznaczone dla przeglądarki i PWA. **FULL_SOURCE**
zachowuje również historyczne źródła Godota. Ich dotychczasowe logowanie hasłem
nie działa z serwerem UI_22; natywny klient nie otrzymał integracji Google.
Nie dołączono nowego APK.

## Weryfikacja

Bieżący raport: `docs/qa_0.8.18/ui22/summary.json`.
Testy przeglądarki używają rzeczywistego HTTP, WebSocket i osobnej bazy,
z testowym dostawcą Google. Bibliotekę sprawdzają też testy podpisanych tokenów.
Logowania na produkcyjnej domenie z prawdziwym kontem Google nie wykonano —
wymaga klienta OAuth właściciela gry.

Poprzednie aktualizacje: [UI_21 — czary](docs/UI_21_SPELL_EFFECTS.md),
[UI_20 — kontynent i łupy](docs/UI_20_WORLD.md), [UI_19](docs/UI_19_WORLD.md).
