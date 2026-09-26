# Bractwo 0.8.15 — Odzyskanie mocy podczas walki

Mała aktualizacja pełnej wersji **0.8.14**. Zmieniono wyłącznie Odzyskanie mocy i jego obsługę w interfejsie. Nie ukryto atutów ani przyszłych czarów; nie dodano zwojów. Pozostałe mechaniki opisane poniżej pozostają bez zmian.

## Czarodziej

**Odzyskanie mocy** działa od poziomu 1: natychmiast przywraca początkowo **20 many**, także **w walce PvE/PvP i podczas ruchu**, bez kosztu many ani złota. Jest **akcją dodatkową** (jej wspólne odnowienie wynosi 3 sekundy), a nie głównym atakiem. Nie przerywa ruchu, autoataku, zaznaczenia celu, kolejki głównego czaru ani trwającej koncentracji. Nie wymaga czterech sekund skupienia.

Własne odnowienie zdolności to nadal **180 sekund**, liczone od skutecznego użycia i zapisywane od razu z postacią. Ilość odzyskiwanej many i jej skalowanie są takie jak w 0.8.14. Odnowienie nie resetuje się po ponownym logowaniu ani aktualizacji. Przy pełnej manie przycisk jest nieaktywny: nie zużywasz akcji ani odnowienia. Otrzymujesz najwyżej brakującą manę. Podczas rozpoczętego rytuału najpierw go przerwij; sama zdolność nie przerywa go automatycznie.

Zdolności użyjesz z paska, księgi czarów lub **C → Atuty**; działa też pod F, jeśli jest faktycznie najczęściej używana. Wszystkie te miejsca pokazują tę samą gotowość. Krótki błękitny efekt i komunikat informują o odzyskanej manie. Pasywna regeneracja many, mikstury, rytuały, czary i inne klasy nie zostały zmienione. Natychmiastowa akcja dodatkowa w walce jest adaptacją Bractwa, a nie odtwarzaniem odpoczynku.

**Rytuały** wybierasz w C → Czary / K, przy konkretnym czarze. Odpowiedni przycisk nie zużywa many, ale wymaga nieruchomego rzucania poza walką. Zwykłe użycie z paska pozostaje wersją płatną.

| Czar | Zwykłe rzucenie | Rytuał |
| --- | --- | --- |
| Alarm | 20 many, 3 s | 0 many, 10 s |
| Przywołanie chowańca | 20 many, 30 s oraz 10 złota | 0 many, 40 s oraz 10 złota |
| Rozmowa ze zwierzętami — druid | 20 many, 3 s | 0 many, 10 s |

**Alarm** zaznacza kwadrat wokół miejsca rzucenia i ostrzega właściciela, gdy wejdzie do niego potwór lub gracz spoza drużyny. Nie atakuje, nie ujawnia łupów, nie reaguje na osoby już obecne w chwili utworzenia. Jeden Alarm na postać; kolejny zastępuje poprzedni. Trwa do 4 godzin rzeczywistego czasu Bractwa, zgodnie z przeliczeniem 6-sekundowych rund na 3-sekundowe.

**Chowaniec to sowa, nie drugi bojowy wilk.** Nie zadaje obrażeń. W Atutach i Czarach ma polecenia: Za mną, Pomagaj, Zwiad, Odeślij. Pomoc daje ułatwienie jednemu atakowi właściciela przeciw wskazanemu, legalnemu celowi, jeśli sowa do niego podejdzie. Może zostać zabita. Zwiad opisuje tylko widoczne pobliskie zagrożenia, bez ich łupów. Koszt 10 złota jest składnikiem również przy rytuale; płatność następuje dopiero po ukończeniu.

Nie można robić rytuałów z Leczenia ran, Długonogiego ani zwykłych czarów ofensywnych. Nie dodano przepisywania zwojów ani pełnego systemu przygotowywania czarów.

## Druid

W **C → Atuty** wybierasz jeden kafelek i osobno zatwierdzasz decyzję:

- **Strażnik:** broń żołnierska i średnie pancerze.
- **Mistyk natury:** +1 do trafienia czarami druida i +1 do ST jego czarów. Nie zwiększa obrażeń, leczenia, many ani uderzeń bronią pod Shillelagh.

Pierwszy wybór jest darmowy, poza walką. Zmiana istniejącej ścieżki: u mistrza profesji w osadzie, poza walką i przemianą. Nie zużywa punktów ogólnych atutów. Nie zmienia automatycznie stylu wojownika ani rodzaju uzbrojenia.

**Nowy druid zaczyna w lekkim pancerzu. Strażnik NIE dodaje średniego pancerza do ekwipunku.** Pancerz musisz kupić albo zdobyć. Obie ścieżki mają biegłość w broni prostej, lekkie pancerze i tarcze. Dębowa tarcza i zwykły średni Pancerz ze skór są u kupca; tarcza nie jest darmowym nowym wyposażeniem druida.

**Druidyczny i Rozmowa ze zwierzętami:** w świecie pojawiły się lis, żaba i znak druidów. Podejdź i naciśnij **E**. Zwierzęta przekazują wskazówki po użyciu czaru; znak odczytuje druid. Wskazówka może ustawić punkt na mapie. Nie jest to automatyczna rozmowa z każdym potworem ani uspokajanie atakujących zwierząt.

### Przemiany

| Poziom Bractwa | Forma | Podstawowe ataki / przeznaczenie |
| --- | --- | --- |
| 5 | Wilk | 1k6+2, taktyka watahy i przewracanie celów do średniego rozmiaru |
| 5 | Kot | Drobna postać, szybki ruch; podstawowe obrażenia 1 |
| 15 | Niedźwiedź czarny | Dwa uderzenia po 1k6+2 |
| 35 | Niedźwiedź brunatny | Ugryzienie 1k8+3 i pazury 1k4+3 |

Na poziomie 5 otrzymujesz również **Dzikiego towarzysza**, przywołującego leśną sowę bez many i złota. Wszystkie przemiany i to przywołanie mają **wspólne odnowienie 60 sekund**. Powrót do własnej postaci nie zeruje odnowienia. Podstawowa przemiana od poziomu 5 trwa do 30 minut; czas rośnie wraz z przeliczonym poziomem klasy.

W formie zwierzęcia zachowujesz własne HP, otrzymujesz tymczasowe HP równe przeliczonemu poziomowi klasy (na poziomie gry 5: **+2**), używasz statystyk i ataków formy zamiast broni. Wyczerpanie tych tymczasowych HP nie kończy przemiany. Nie rzucasz czarów, ale możesz utrzymać wcześniejszą koncentrację. Wyposażenie zostaje zapisane i wraca po wyjściu z formy; jego premie nie wzmacniają pazurów ani KP formy. Nie dodano jeszcze wspinania, skradania, przechodzenia kota przez małe otwory ani pełnego katalogu form bestii.

## Atuty i wyszkolenie

**Uprawnienia z klasy lub ścieżki są od razu pokazane jako posiadane** i niczego nie trzeba wybierać ponownie:

| Klasa | Broń | Pancerze i tarcze |
| --- | --- | --- |
| Wojownik / Rycerz | Prosta i żołnierska | Lekkie, średnie, ciężkie; tarcze |
| Łowca | Prosta i żołnierska | Lekkie, średnie; tarcze |
| Czarodziej | Prosta | Brak początkowego wyszkolenia w pancerzach/tarczach |
| Druid | Prosta; Strażnik również żołnierska | Lekkie, tarcze; Strażnik również średnie |

Wyszkolenie otrzymane z klasy to nie zakup całego ogólnego atutu. **Wojownik nie dostaje dodatkowych +1 do cech tylko dlatego, że ma wyszkolenie w pancerzach.**

Przygotowane zostały cztery rzeczywiście wybieralne atuty wyposażenia: **Lekko opancerzony, Średnio opancerzony, Ciężko opancerzony, Szkolenie w broni żołnierskiej**. Wybory od poziomów **15, 35, 55 i 75** (odpowiedniki 4/8/12/16). Zakup przyznaje uprawnienie i pojedyncze +1 do wskazanej dozwolonej cechy, do 20. Nie zmienia istniejących punktów mistrzostwa. Dostępne są wyłącznie brakujące, niekupione atuty ze spełnionymi wymaganiami. Pozostałe niewykorzystane wybory są zachowane; to cztery atuty wyposażenia, nie pełny katalog wszystkich atutów D&D.

Strażnik ze średnimi pancerzami nie widzi ponownego wyboru Średnio opancerzonego. Jeśli późniejszy atut wymaga wyszkolenia pochodzącego ze ścieżki, a zmienisz tę ścieżkę, atut i jego +1 stają się nieaktywne do ponownego spełnienia wymagań. Wybór nie jest usuwany ani zwracany wielokrotnie.

## Wspólny sprzęt i krótkie podglądy

Tylko **broń prosta i żołnierska**. Nie ma broni egzotycznej. Każda zwykła broń ma konkretny rodzaj, np. laska, miecz długi, krótki/długi łuk, młot dwuręczny. Magiczna premia i rzadkość są niezależne od rodzaju. Różdżki pozostają fokusami czarodzieja.

Brak biegłości nie blokuje założenia zwykłej broni: nie doliczasz premii biegłości do ataku. Nie odejmujesz jej ponownie od już obliczonego rzutu. Broń używa własnego zasięgu, kości, chwytu i odpowiedniej cechy; sztylet/rapier mogą korzystać ze Zręczności. Biegłość NIE daje mistrzostw wojownika. Shillelagh działa tylko na laskę/maczugę, nie przenosi się na miecz ani łuk. Trzy istniejące mistrzostwa nadal należą do wojownika.

Pancerze są lekkie, średnie i ciężkie; szaty pozostają osobno. Niewyszkolony użytkownik może założyć pancerz, ale nie rzuca w nim czarów i ma utrudnienie w testach Siły/Zręczności. Tarcza bez wyszkolenia nie dodaje KP. Przy ciężkim pancerzu sprawdzana jest także wymagana Siła; za mała spowalnia ruch.

**Jednorącz / Oburącz** działa dla każdej klasy przy odpowiedniej broni. Zmieniasz chwyt poza walką w podglądzie założonej broni. Tarcza jest odkładana do plecaka, nigdy usuwana. Jej premia nie działa równocześnie z chwytem oburącz. Laska 1k6 / 1k8 i miecz długi 1k8 / 1k10 pokazują już własne modyfikatory postaci.

Podgląd po najechaniu/kliknięciu pokazuje nazwę, kategorię/rodzaj i rzeczywiste rzuty. Bez ściany klas, wartości zerowych, długich opisów i powtarzania premii magicznej. Dodatkowe wiersze tylko dla wymagań, braków wyszkolenia, efektów i rzeczywiście odkrytych źródeł. Mistrzostwo ma nazwę/kłódkę; rozwinięcie jest osobno. Przyciski są w dolnym rzędzie, **Sprzedaj** tylko podczas handlu, z ceną na przycisku. Przedmioty założone również mają podgląd. Druid rzeczywiście pokazuje założoną tarczę/broń, a nie stale tę samą laskę.

## Grafika i granice adaptacji

Dodane/odświeżone ikony ścieżek, wyszkoleń, rytuałów, form i wyposażenia. Sowa ma animowane skrzydła, kot i czarny niedźwiedź własny wygląd, Alarm swój kwadrat, skupienie krąg i cząstki. Grafika działa razem z serwerowymi efektami. Czasy rzucania rytuałów, odnowienia zamiast odpoczynków, wspólna mana, pomoc sowy dla właściciela, automatyczne wstawanie po 1,5 s i bonus Mistyka są adaptacjami Bractwa, nie dosłownymi regułami podręcznika.

Chowaniec i Alarm są obiektami bieżącej sesji: znikają po śmierci/wylogowaniu właściciela lub restarcie serwera. Nie zapisujemy ich jako trwałych obiektów świata. Zdolności, ścieżka, atuty, przedmioty i opłacone odnowienia są zapisywane.

## Aktualizacja

1. Zatrzymaj stary serwer i skopiuj `data/world.sqlite3` (na Railway `/data/world.sqlite3`) jako kopię bezpieczeństwa.
2. Podmień serwer i CAŁY `web` razem, żeby stare przyciski nie blokowały używania w walce. Nie zmieniaj ścieżki bazy ani wolumenu.
3. Zachowaj stary wolumen/bazę. Uruchom `start_windows.bat` lub `./start_unix.sh`. Otwórz `http://127.0.0.1:8080`, odśwież Ctrl+F5. Nie otwieraj starego lokalnego `index.html`.

**Bez resetu postaci.** Stare wyposażenie, UID i wybory wojownika pozostają. Istniejący druid w średnim pancerzu zachowuje przejściowe uprawnienie do pierwszego jawnego wyboru ścieżki. Po wybraniu Mistyka działają już zwykłe wymagania wyszkolenia; nie usuwamy ani nie wymieniamy automatycznie jego pancerza. Po wyborze Strażnika nie dopisujemy żadnych przedmiotów. Wcześniejsze podsumowania awansu nie są odtwarzane jako nowe wybory klasowe. Do cofnięcia wersji użyj również kopii bazy sprzed migracji.

Paczka Railway ma pliki bez dodatkowego katalogu; pełna paczka ma folder `Bractwo_0.8.15`. Godot import: `client/project.godot`. Nie ma APK/AAB/EXE. **Godot nie był uruchamiany ani kompilowany; Docker nie był budowany; nie wykonano wdrożenia na Railway.** Raport wykonanych testów: `docs/TEST_REPORT.md`. Zmiana protokołu: `docs/PROTOCOL_0.8.15.md`. Starszy opis pozostałych funkcji: `docs/PROTOCOL_0.8.14.md` (jego akapit o odzyskaniu zastępuje nowy opis).
