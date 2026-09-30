# UI_22 — kontrola logowania w przeglądarce

Wynik: **17 kontroli zaliczonych, 0 wyjątków JavaScript**. Szczegóły: `browser_auth_results.json`.

Kontrola uruchamia rzeczywistą aplikację HTTP/WebSocket oraz interfejs gry na izolowanej bazie SQLite w pamięci. Skrypt Google Identity Services jest zastępowany wyłącznie przez trasę Playwright, a weryfikator podpisu Google jest przekazywany jako jawna zależność testowa. Produkcyjne sprawdzanie nonce, czasu, origin, ciasteczka, jednorazowego biletu, właściciela postaci i limitu pozostaje aktywne.

Sprawdzono:

- Obowiązkowe Google; stare wejście WebSocket na imię i poprawne hasło jest odrzucane.
- Puste konto, utworzenie postaci, wylogowanie z nowym nonce i wybór zapisanej postaci przy powrocie.
- Utworzenie czterech postaci przez rzeczywiste WebSockety; wyłączone przyciski przy limicie oraz odrzucenie piątej postaci i przypisania starej postaci przez bezpośrednie żądania do serwera.
- Odrzucenie wyboru postaci należącej do innego konta Google.
- Przypisanie starej postaci: błędne hasło, ponowienie z poprawnym hasłem oraz zachowanie nazwy i poziomu 7.
- Wygaśnięcie biletu serwera, ponowne uwierzytelnienie, zmiana konta i zignorowanie spóźnionej odpowiedzi SDK.
- Anulowanie okna Google, pusta odpowiedź, odrzucone poświadczenie, błąd ładowania SDK i skuteczne ponowienia.
- Brak konfiguracji Google: czytelny komunikat i brak alternatywnego wejścia hasłem.
- Brak adresu e-mail, nazwy profilu i identyfikatora Google w publicznym rankingu oraz pakietach gry.
- Układ na 1440 × 900 i dotykowym 430 × 932; brak przewijania poziomego. Wszystkie zapisane zrzuty obejrzano.

Zrzuty `google-*.png` w paczce FULL_SOURCE pokazują rzeczywisty interfejs; sam przycisk Google jest atrapą testową, a nie odwzorowaniem oficjalnego przycisku SDK. Mniejsza paczka Railway zawiera raporty bez zrzutów.

Uruchomienie:

```sh
python tools/browser_ui22_run.py
```

Wymagane są Playwright i Chromium (`CHROMIUM_BIN` wskazuje plik wykonywalny). Kod pomocniczy `tools/browser_ui22_server.py` uruchamia się tylko jawnie na loopback i nie jest importowany przez produkcyjny serwer.

Nie sprawdzono rzeczywistego okna zgody Google, podpisanego przez Google tokenu ani logowania na produkcyjnej domenie: wymaga to skonfigurowanego OAuth Client ID. Symulacja dotyku w Chromium nie zastępuje testu na fizycznym telefonie.
