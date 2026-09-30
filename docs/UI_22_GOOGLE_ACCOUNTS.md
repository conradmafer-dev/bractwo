# Google i maksymalnie cztery postacie — aktualne zasady UI_25

## Zmiana dla gracza

1. Otwórz stronę gry i wybierz oficjalny przycisk Google.
2. Po potwierdzeniu konta wybierz jedną ze swoich postaci albo stwórz nową.
3. Nowa postać wymaga nazwy i klasy. Nie otrzymuje osobnego hasła.
4. Dawne przypisywanie postaci przez stare hasło zostało usunięte w UI_25.
   Postacie już wcześniej powiązane z Google pozostają dostępne na swoim koncie.

Jedno konto Google ma najwyżej 4 postacie łącznie. Postacie offline i przypisane
stare postacie zajmują miejsca w tym samym limicie. Po wykorzystaniu wszystkich
miejsc nadal można grać istniejącymi postaciami. Serwer odrzuca piąte utworzenie
również po ręcznej zmianie komunikatu w przeglądarce.

Stare logowanie nazwą i hasłem oraz anonimowa rejestracja są wyłączone.
Stare hasło nie służy już do przypisywania postaci.
Postaci już przypisanej nie można przejąć drugim kontem Google, nawet znając
dawne hasło. Nie dodano funkcji usuwania ani przenoszenia postaci między kontami.
Aktywna postać nie może być równocześnie otwarta w dwóch sesjach.

## Włączenie na stronie gry

Ta paczka zawiera implementację. Nie zawiera poświadczeń właściciela,
nie zmienia ustawień Google Cloud ani Railway i nie została wdrożona.

### 1. Google Cloud

W projekcie Google Cloud skonfiguruj aplikację logowania: nazwę Bractwo Krain,
adres kontaktowy oraz odbiorców aplikacji. Utwórz identyfikator klienta OAuth
typu **Web application**. W **Authorized JavaScript origins** wpisz dokładny
publiczny origin gry, np.:

```text
https://bractwo.up.railway.app
```

Jeśli używasz własnej domeny, wpisz ją zamiast przykładu. Origin nie zawiera
ścieżki `/ws`, `/auth` ani końcowego ukośnika. Ta wersja obsługuje jeden origin
na serwerze; stronę należy otwierać pod tym adresem. Przy trybie testowym projektu
Google udostępnij dostęp odpowiednim testerom; dla wszystkich graczy skonfiguruj
aplikację jako publiczną zgodnie z wymaganiami wyświetlanymi w Google Cloud.

Używamy przycisku Google Identity Services z oknem popup i odpowiedzią JavaScript.
Nie potrzeba Client Secret ani własnej trasy OAuth redirect. Nie dodawaj klucza
prywatnego ani danych logowania do kodu, ZIP-a czy zmiennych klienta.

### 2. Railway

Zachowaj istniejący wolumen i `BRACTWO_DB_PATH`. Dodaj dwie zmienne usługi:

```text
GOOGLE_CLIENT_ID=IDENTYFIKATOR_Z_GOOGLE.apps.googleusercontent.com
GOOGLE_AUTH_ORIGIN=https://bractwo.up.railway.app
```

Zastąp wartości rzeczywistym identyfikatorem i adresem gry. Client ID jest
publicznym identyfikatorem aplikacji i trafia do przycisku Google.
Serwer pobiera klucze publiczne Google przez HTTPS, aby sprawdzać podpisy tokenów;
musi mieć dostęp do `www.googleapis.com`, a przeglądarka do `accounts.google.com`.

Wdróż zawartość paczki RAILWAY_GITHUB_READY razem: pliki serwera, klienta i
`requirements.txt`. Pozostaw **jedną replikę**, jeden proces symulacji oraz
dotychczasowy trwały wolumen. Krótkotrwałe potwierdzenia logowania są w pamięci
procesu; po restarcie trzeba ponownie użyć Google.

Brak albo niepoprawny format konfiguracji powoduje zamknięcie logowania.
Gra pokazuje „Logowanie Google nie jest jeszcze skonfigurowane”, zamiast wracać
do dawnych haseł. `/health` nadal sprawdza działanie procesu, a
`/auth/google/config` podaje `enabled` i publiczny `client_id`.
`enabled:true` oznacza poprawny lokalny format konfiguracji; nie dowodzi, że
origin został poprawnie dodany po stronie Google.

### 3. Kontrola po wdrożeniu

- `/health` ma zwracać `ui_revision: UI_25`, `world_revision: 20`.
- Na stronie ma być przycisk Google i informacja o maksymalnie 4 postaciach.
- Zaloguj się rzeczywistym kontem Google, stwórz postać i sprawdź ponowne wejście.
- Dotychczasowy gracz wybiera postać wcześniej powiązaną z jego kontem Google.
  Nie resetuj bazy graczy; nie ma już opcji przypisywania starym hasłem.
- W razie błędu origin sprawdź zgodność adresu w pasku przeglądarki,
  `GOOGLE_AUTH_ORIGIN` oraz **Authorized JavaScript origins** w Google Cloud.

## Zapisy i prywatność

Sześciokolumnowa tabela `accounts` pozostaje tabelą postaci i ich zapisów.
Przy starcie powstają dodatkowo `google_accounts` oraz `google_characters`.
Powiązanie postaci używa stałego identyfikatora Google `sub`, a nie adresu e-mail.
Nie zapisujemy tokenów Google, e-maili, zdjęć ani nazw profilu Google w bazie gry.
Do rankingu i komunikatów świata trafia wybrana nazwa postaci.

Migracja nie przypisuje starych postaci automatycznie. UI_25 nie udostępnia już
samodzielnego przypisywania niepowiązanych zapisów. Istniejąca kopia startowa
w `run.py` obejmuje całą bazę przed migracją, w tym późniejsze powiązania kont.
Nowe postacie nie mają działającego hasła do dawnego logowania.

## Zabezpieczenia i zakres

- Podpis Google, odbiorca `aud`, wystawca `iss`, czas ważności i `nonce` są
  weryfikowane po stronie serwera przy użyciu `google-auth`.
- Wymiana HTTP wymaga zgodnego originu, JSON i własnego nagłówka aplikacji.
  WebSocket również dopuszcza tylko skonfigurowany origin.
- Jednorazowe potwierdzenie wejścia wygasa po 5 minutach i jest związane
  z ciasteczkiem przeglądarki HttpOnly, SameSite=Strict, Secure na HTTPS.
- Limit 4 jest sprawdzany w logice gry oraz przez ograniczenia SQLite.
  Tworzenie postaci i przypisanie właściciela stanowią jedną transakcję.
- Ograniczamy częstotliwość prób HTTP i WebSocket oraz równoległe kosztowne
  sprawdzanie tokenów. Rotacja ciasteczka nie omija limitu
  połączeń HTTP liczonego według adresu bezpośredniego nadawcy.
- Nie ufamy dowolnym nagłówkom `X-Forwarded-For`. Za proxy limity dla adresu
  nadawcy mogą obejmować więcej graczy, zależnie od topologii hostingu.
- Google i limit postaci ograniczają masowe zakładanie postaci. Nie gwarantują
  jednej osoby na konto i nie zastępują ochrony hostingu przed DDoS.

## Testy i odtwarzanie

W `docs/qa_0.8.18/ui25/summary.json` znajdują się bieżące wyniki i ograniczenia.
Raport UI_22 pozostaje historycznym zapisem wcześniejszej wersji.
Pakiet testowy obejmuje prawdziwe sprawdzanie lokalnie podpisanych tokenów przez
bibliotekę Google, ataki na protokół, równoległe tworzenie postaci i odrzucanie wyłączonego przypisywania oraz
pełną drogę przeglądarka → HTTP → WebSocket → baza danych.

Testy przeglądarki zastępują tylko dostawcę Google kontrolowanym testowym
dostawcą; używają oddzielnej bazy w pamięci. Ich serwer jest w `tools/`, nie jest
kopiowany do obrazu Docker ani do paczki Railway i nie stanowi obejścia produkcji.
Prawdziwego popupu Google oraz konfiguracji produkcyjnej domeny nie można
potwierdzić tym testem. Wymagają rzeczywistego klienta OAuth.

Przykładowe uruchomienia ze źródeł:

```text
python -m unittest discover -s tests -p 'test_google_*ui22.py' -v
node --test tests/test_google_auth_ui22.cjs
python tools/browser_ui22_run.py
```

Testy podpisów wymagają biblioteki `cryptography` w środowisku testowym.
Test przeglądarkowy wymaga Node.js, Playwright i Chromium; `CHROMIUM_BIN` pozwala
wskazać lokalny plik wykonywalny. Historyczne scenariusze sprzed UI_22, które
logowały się dawnym pakietem `hello`, wymagają nowej testowej sesji Google.
Nowy serwer celowo odrzuca ich dawne logowanie.

Ta aktualizacja dotyczy gry przeglądarkowej i PWA. Historyczny klient Godot
w pełnych źródłach nadal używa starego logowania i nie może wejść do serwera UI_22.

Dokumentacja Google: [konfiguracja klienta](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid),
[weryfikacja tokenów](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token),
[przycisk i JavaScript](https://developers.google.com/identity/gsi/web/reference/js-reference).
