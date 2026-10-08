# Bractwo Krain 0.8.18 UI_31 — atuty

Dodano **10 nowych atutów**: cztery początkowe i sześć późniejszych. Od poziomu 1
postać wybiera jeden z siedmiu atutów początkowych w osobnym oknie z opisem
i potwierdzeniem. Istniejące postacie zachowują wybory i mogą odebrać niewykorzystany
pierwszy atut. Późniejsza pula cech/atutów pozostaje wspólna. Nie wymaga resetu.
[Zasady, lista atutów, testy i wdrożenie UI_31](docs/UI_31_ATUTY.md).

Początek gry jest łagodniejszy: szczury mają KP 8, a wilki KP 11.
Przy Moście Wędrowców pozostał jeden ognik i dwa pająki, z większą przestrzenią
przy wyjściu z przeprawy. Władca Twierdzy zadaje 2k4+3 obrażeń zwykłym atakiem
(także dystansowym) oraz 3k6+3 atakiem obszarowym. Zmiana nie wymaga resetu postaci.

## Zachowana zawartość wcześniejszych aktualizacji

**[Zagraj w Bractwo Krain](https://bractwo.up.railway.app/)** — polska gra RPG
online w przeglądarce na komputerze i telefonie. Wybierz wojownika, łowcę,
czarodzieja lub druida, odkrywaj świat i wyruszaj na wyprawy w drużynie.
Do gry potrzebujesz konta Google i połączenia z internetem.

Nowe układy przeciwników wiążą potwory z lokalnym terenem: czaty, obozowiska, watahy, legowiska i dziedzińce ruin. Mieszkańcy mają różne pozycje na podejściu, bokach i w głębi łowiska. Aktualizacja przestawia istniejących przeciwników; zachowuje ich liczbę, statystyki i łupy oraz układ początku gry.
[Szczegóły i sprawdzenia UI_30](docs/UI_30_LOWISKA_POTWOROW.md).

Dalsze krainy otrzymały 167 lokalnych formacji: leśne doliny i polany, skalne przesmyki, wydmowe niecki, suche kępy na bagnach oraz osłonięte miejsca w śniegu. Nowa grafika terenu w przeglądarce korzysta z pamięci podręcznej. Układ początku gry pozostaje zachowany.
[Szczegóły i sprawdzenia UI_29](docs/UI_29_UKSZTALTOWANIE_TERENU.md).

Dodano wybór cech za 27 punktów, osobny atut pochodzenia, pełną listę 18
umiejętności, biegłości klasowe i ekspertyzę. Rozwój cech korzysta z tej samej
puli co atuty, na progach przeliczonych z D&D. Umiejętności wykorzystują
18 oznaczonych wydarzeń w świecie oraz akcje badania, szukania i ukrycia PvE.
Naprawiono chodzenie po oceanie; przeprawy odbywają się łodziami.
[Zasady, sterowanie i migracja UI_28](docs/UI_28_CECHY_UMIEJETNOSCI.md).


Publiczna strona przedstawia klasy, świat i rozgrywkę przed logowaniem.
Poradniki rozpoczęcia gry, wyboru klasy i wypraw mają osobne adresy,
metadane i linki w mapie witryny. Strona korzysta z kompresji zasobów
przy budowie obrazu oraz wstrzymuje rysowanie świata przed wejściem do gry.
[Zmiany SEO, weryfikacja i zgłoszenie do Google](docs/SEO_IMPROVEMENTS.md).
Galeria pokazuje sześć kadrów z gry, a sekcja mechanik opisuje adaptację D&D.
Komentarze są publiczne; pisanie i usuwanie własnych wpisów wymaga logowania.
Serwer sprawdza własność postaci, filtruje wulgaryzmy i ogranicza spam.
[Galeria i komentarze — działanie oraz testy](docs/KOMENTARZE_I_GALERIA.md).

Wejście do gry wymaga logowania przez Google. Jedno konto Google może mieć
maksymalnie **4 postacie**, wliczając postacie offline i przypisane stare zapisy.
Limit obowiązuje na serwerze i w bazie danych. Usunięto dodawanie starych
postaci przez hasło; postacie wcześniej powiązane z Google nadal działają.

NPC otwierają własny panel usług po prawej. Bank, depozyt, promocja,
błogosławieństwo i przeprawy mają osobne widoki. Górne menu ma nowe ikony.
Wszystkie **20 przystani** jest bezpiecznych. W **10 miastach** dodano kamienie
przypisania: odrodzenie zmieniasz wyłącznie przez świadome użycie kamienia,
bez automatycznego przypisywania podczas wizyty lub rejsu.
[Zakres UI_25](docs/UI_25_BRACTWO_KRAIN.md).

Promocja profesji jest dostępna od **poziomu 10**, za **2000 złota**.
W **C → Atuty** wojownik wybiera **Mistrza Bitewnego** (3 z 5 manewrów,
kości przewagi) albo **Czempiona** (krytyk bronią 19–20). Łowca wybiera
**Huntera** i jedną technikę: Pogromcę kolosów, Rozbijacza hord albo Zabójcę
olbrzymów. Wybór jest bezpłatny po promocji i stały. Poznane manewry
pojawiają się na pasku umiejętności. Krótki lub długi odpoczynek odnawia
kości; logowanie ich nie odnawia. Wilk łowcy pozostaje dostępny.
[Zdolności, sterowanie i zakres UI_26](docs/UI_26_MARTIAL_PROMOTIONS.md).

Promowany czarodziej wybiera w **C → Atuty** jedną z czterech działających szkół:
**Ewokację, Odpychanie, Wróżbiarstwo albo Iluzję**. Wybór jest trwały;
zdolności rozwijają się na poziomach **10, 25, 45 i 65**. Serwer sprawdza
promocję i poziom, a wykorzystane zasoby zachowuje po ponownym logowaniu.
[Zdolności i zakres UI_24](docs/UI_24_WIZARD_SCHOOLS.md).

Nowy wybór kręgu druida również wymaga promocji; wcześniej wybrane kręgi
zachowują zdolności. Demon, Wędrowiec Otchłani i Władca Otchłani mają własne
animowane grafiki z [UI_23](docs/UI_23_PROMOTION_DEMONS.md).

Paczka zawiera także świat i łupy z UI_20, animacje czarów z UI_21 i konta Google z UI_22.

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
Ekran wejścia oraz `/health` pokazują **UI_30**. Reset postaci nie jest potrzebny.
Paczka nie została wdrożona automatycznie.

## Lokalnie i źródła Godota

Skonfiguruj osobnego klienta Google z originem `http://localhost:8080`, ustaw
`GOOGLE_CLIENT_ID` oraz `GOOGLE_AUTH_ORIGIN=http://localhost:8080`, uruchom
`start_windows.bat` lub `./start_unix.sh` i otwórz ten sam adres.
Nie uruchamiaj gry przez samo otwarcie HTML.

Logowanie UI_22 jest przeznaczone dla przeglądarki i PWA. **FULL_SOURCE**
zachowuje również historyczne źródła Godota. Ich dotychczasowe logowanie hasłem
nie działa z obecnym serwerem; natywny klient nie otrzymał integracji Google.
Nie dołączono nowego APK.

## Weryfikacja

Bieżący raport: `docs/qa_0.8.18/ui27/summary.json`.
Weryfikacja obejmuje publiczny HTML i metadane, canonical, sitemap, robots,
ustawienia adresu i weryfikacji, logowanie oraz wygląd na komputerze i telefonie.
Przeglądarka używa osobnej bazy i testowego dostawcy Google. Nie wykonano
logowania prawdziwym kontem ani publikacji na produkcyjnym serwerze.
Wcześniejsze raporty, w tym `ui26/`, pozostają dołączone.

Poprzednie aktualizacje: [UI_23 — promocja i demony](docs/UI_23_PROMOTION_DEMONS.md), [UI_22 — konta Google](docs/UI_22_GOOGLE_ACCOUNTS.md), [UI_21 — czary](docs/UI_21_SPELL_EFFECTS.md),
[UI_20 — kontynent i łupy](docs/UI_20_WORLD.md), [UI_19](docs/UI_19_WORLD.md).
