# UI_31 — dziesięć nowych atutów i pierwszy wybór od poziomu 1

Baza: `BRACTWO_KRAIN_0.8.18_UI_30_LOWISKA_POTWOROW_FULL_SOURCE.zip`.
Zmiany dotyczą serwera Python i klienta przeglądarkowego. Nie resetują świata,
postaci, biegłości, cech ani wcześniejszych wyborów atutów. Teren i łowiska UI_30
pozostają bez zmian. Historyczny klient Godot nie był aktualizowany ani eksportowany.

## Wybory postaci

Od poziomu 1, po wyborze profesji, postać ma **jeden osobny, bezpłatny wybór atutu
pochodzenia**. Katalog początkowy zawiera siedem pozycji: Twardy, Zacięty atak,
Wszechstronny oraz nowe Czujny, Rzemieślnik, Uzdrowiciel i Szczęściarz.

Późniejsze wybory pozostają na poziomach **15, 35, 55, 75 i 90**, a wojownik ma
również dodatkowe wybory na **25 i 65**. W tych progach gracz wybiera **atut ALBO
rozwój cech (+2 lub +1/+1)**. To ta sama pula; dodatkowe atuty nie dają nowych punktów.
Pierwszy atut nie pomniejsza tej puli. Nowe atuty nie są powtarzalne. Dotychczasowa
powtarzalność Wszechstronnego i Rozwoju cech pozostaje bez zmian.

Istniejąca postać, także druid na poziomie 23, może odebrać niewykorzystany pierwszy
wybór. Jeśli pierwszy atut został już wybrany, pozostaje wybrany — aktualizacja nie
przyznaje drugiego i nie zamienia go automatycznie. Każde zatwierdzenie jest trwałe.

## Dziesięć nowych atutów

To adaptacje do walki w czasie rzeczywistym w Bractwie, nie kompletne odwzorowanie
wszystkich korzyści podręcznikowych atutów D&D. Poniżej podano rzeczywiście wdrożone
reguły. Wewnętrzna runda gry trwa 3 sekundy; 5 stóp odpowiada jednemu polu (32 jednostki).

| Atut | Dostępność | Działający efekt |
| --- | --- | --- |
| **Czujny** | Początkowy lub późniejszy | Dodaje premię z biegłości do testów Percepcji i pasywnej Percepcji. Sumuje się z posiadaną biegłością i ekspertyzą. Nie wprowadza inicjatywy do gry. |
| **Rzemieślnik** | Początkowy lub późniejszy | Towary u kupców są o 20% tańsze; wynik zaokrąglany w górę. Cena w oknie kupca odpowiada kwocie pobieranej przez serwer. Nie zmienia cen sprzedaży, usług ani run. Sprawdzono, że obecne asortymenty nie pozwalają zarabiać na kupowaniu i natychmiastowej odsprzedaży. |
| **Uzdrowiciel** | Początkowy lub późniejszy | Mikstura zdrowia leczy dodatkowo o premię z biegłości. Przy krótkim odpoczynku każda 1 na kości zdrowia jest przerzucana raz; drugi wynik obowiązuje. Nie zwiększa leczenia czarami. |
| **Szczęściarz** | Początkowy lub późniejszy | Automatycznie przerzuca nieudany rzut obronny lub koncentracji; zachowuje lepszy wynik. Ma tyle użyć, ile wynosi premia z biegłości. Wszystkie wracają po długim odpoczynku, nie po krótkim ani logowaniu. Nie zużywa użycia przy sukcesie, automatycznej porażce, niemożliwym do osiągnięcia ST ani wyniku zastąpionym Przepowiednią. Nie dotyczy ataków i testów umiejętności. |
| **Odporny** | Późniejszy | +1 do wybranej cechy i biegłość w jej rzutach obronnych. Można wybrać tylko cechę, w której obronie postać nie ma już biegłości. Maksimum cechy: 20. |
| **Mag bitewny** | Późniejszy; czarodziej, druid lub łowca | +1 do Inteligencji, Mądrości albo Charyzmy, do 20. Przewaga przy utrzymywaniu koncentracji po obrażeniach. Zachowuje działanie Smoka Kręgu Gwiazd i Przepowiedni. Nie dodaje ataków okazyjnych czarem. |
| **Szybki** | Późniejszy | +1 Zręczność albo Kondycja, do 20. Bez ciężkiego pancerza: +10 stóp ruchu na rundę. Działa też po wtopieniu pancerza w Dziki kształt. Teren, spowolnienia i unieruchomienie nadal obowiązują. |
| **Przebijacz** | Późniejszy | +1 Siła albo Zręczność, do 20. Raz na rundę przerzuca najniższą kość kłutych obrażeń broni, jeśli wynik jest poniżej średniej kości; drugi wynik obowiązuje. Kłuty krytyk broni dodaje jedną kość tej broni. Nie obejmuje czarów, fokusów ani przemian. |
| **Siekacz** | Późniejszy | +1 Siła albo Zręczność, do 20. Raz na rundę cięte trafienie bronią spowalnia cel o 10 stóp na rundę na 3 sekundy. Krytyk daje celowi utrudnienie ataków na 3 sekundy. Spowolnienia z tego atutu nie sumują się. |
| **Miażdżyciel** | Późniejszy | +1 Siła albo Kondycja, do 20. Raz na rundę obuchowe trafienie bronią odpycha cel o maks. 5 stóp z kontrolą kolizji. Bossowie nie są odpychani. Krytyk daje przewagę ataków przeciw celowi przez 3 sekundy. |

Efekty Siekacza i Miażdżyciela działają w PvE i PvP z zachowaniem istniejących
zabezpieczeń PvP. Nie uruchamiają się od czarów, naturalnych ataków przemiany ani
trafienia martwego celu. Nowe stany mają polskie nazwy i objaśnienia w interfejsie.

## Interfejs

Przypomnienie **„Wybierz pierwszy atut”** pojawia się przy niewykorzystanym wyborze,
także po zalogowaniu istniejącej postaci. Można je zamknąć do następnego logowania.
Do wyboru prowadzi również **C → Atuty → Pochodzenie** lub przycisk w części ogólnej
atutów. Po późniejszych progach przypomnienie zachowuje oddzielne przyciski
„Rozwiń cechy” i „Wybierz atut”.

Wybór ma osobne okno, po sześć nazw z ikonami na stronie. Kliknięcie nazwy wyświetla
opis i ewentualny wybór zwiększanej cechy. Dopiero **„Zatwierdź wybór”** wysyła
polecenie. „Wróć”, × i Escape zamykają bez wydawania punktu. Zwykła karta pokazuje
atuty posiadane; niewybrane pozycje są w oknie wyboru, nie na długiej liście karty.

Okno odświeża uprawnienia z aktualnego stanu, zachowuje skupienie klawiatury i
blokuje sterowanie grą pod spodem. Serwer niezależnie sprawdza poziom, klasę,
życie, walkę, przemianę, pulę, duplikaty i limit cech. Powtórzenie pakietu nie
wydaje następnego wyboru. Użycia Szczęściarza i znaczniki rundy są zapisywane.

## Testy i ograniczenia

W końcowym, wybranym zestawie regresji przeszło **140 testów Python i 58 podtestów**.
Obejmuje on nowe atuty, wcześniejsze atuty, rozwój postaci, umiejętności, odpoczynek,
środowisko oraz reguły obronne i ofensywne czarodzieja. W ramach tego zestawu jest
22 nowych testów atutów UI_31. Przeszły **343 testy JavaScript**.

Sprawdzono 7 scenariuszy DOM w Chromium na szerokościach 1440, 390 i 320 pikseli.
Użyto produkcyjnych modułów interfejsu, rzeczywistych danych postaci i prawdziwej
obsługi poleceń serwera, połączonych lokalnym mechanizmem testowym. Obejrzano zrzuty
okien. Pełny test nawigacji HTTP w przeglądarce został zablokowany przez zasady
Chromium w środowisku testowym; zasad tych nie zmieniano. Test DOM nie udaje testu
Google OAuth, pełnego świata gry ani połączenia WebSocket.

Historyczny, szerszy zestaw testów nie jest raportowany jako w całości zaliczony.
Wykryto pięć porażek starych testów katalogu mikstur/czarów; odtworzono identyczne
porażki na niezmienionej paczce UI_30. Logi bazowe i log tego przebiegu znajdują się
w katalogu QA. Stare testy JavaScript dotyczące usuniętego formularza wyboru,
dawnego Odzyskania mocy i nazwy pamięci podręcznej dostosowano do obecnego interfejsu
oraz modelu zasobów; nie zmieniano z tego powodu mechaniki Odzyskania mocy.

Raport: `docs/qa_0.8.18/ui31/summary.json`. Zrzuty są w pełnych źródłach.
Nie testowano fizycznego telefonu, nie eksportowano APK i nie wdrażano na Railway.

## Wdrożenie

Do dalszej edycji służy `FULL_SOURCE`. Do wdrożenia użyj zawartości płaskiego archiwum
`RAILWAY_GITHUB_READY` jako plików repozytorium. Zachowaj obecne zmienne środowiskowe,
konfigurację trwałego wolumenu i bazę danych; przed aktualizacją wykonaj kopię bazy.
Archiwa nie zawierają zapisów graczy, kluczy podpisu ani sekretów.

Po wdrożeniu `/health` powinno zwracać `ui_revision: UI_31`, a ekran logowania
pokazywać UI_31. Po uruchomieniu klient powinien wczytać nowe pliki; aktualizacja
zmienia też wersję pamięci podręcznej pomocniczej aplikacji.
