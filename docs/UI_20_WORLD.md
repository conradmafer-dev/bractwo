# Bractwo 0.8.18 UI_20 — kontynent, archipelagi i nekropolia

Aktualizacja bazuje na dostarczonej paczce UI_19. Zmiany obejmują serwer,
klienta przeglądarkowego i źródła klienta Godota. Mniejsze mobilne przyciski,
skala świata i wcześniejsza zasada odrodzenia w ostatnio odwiedzonym mieście
pozostają zachowane.

## Naprawione usterki

- Pierścienie pokazują rzeczywiste właściwości i wymaganie zestrojenia,
  również w starych egzemplarzach z zapisanej postaci. Klient Godota otrzymał
  też obsługę zestrojenia w ekwipunku.
- Wskazówki mają ilustrację dłoni i gwiazdy, a Wiodący pocisk — promienistego
  pocisku. Obie ikony są dołączone do obu klientów. Natywna księga czarów
  uwzględnia zaklęcia otrzymane z wybranej ścieżki druida.
- Wiodący pocisk bez zaznaczenia wybiera najbliższego żywego potwora w zasięgu,
  na tym samym piętrze i bez przeszkody na linii strzału. Ręczne zaznaczenie
  oraz zablokowany cel mają pierwszeństwo. Automatycznie nie wybiera graczy.
- Rejs wymaga obecności przy właściwym przewoźniku, żywej postaci, zakończenia
  blokady walki i odpowiedniej liczby złotych monet. Poziom celu jest zaleceniem.
  Interfejs wyjaśnia rzeczywistą przyczynę niedostępności przycisku.
- Godot korzysta teraz z faktycznych portów, cen i połączeń serwera zamiast
  dawnej listy wszystkich miast. Atlas i teren otrzymały obsługę kontynentu,
  oceanu, wysp i brzegowych przystani, której brakowało w tym kliencie w UI_19.
- Ork szaman ma własny czteroklatkowy wizerunek humanoidalnego orka z kosturem.

## Handel i rzadkie łupy

Kupiec w Brzezinie ma sześć podstawowych ofert: dwie mikstury zdrowia,
skórzany kaftan druida, zwykły łuk, zwykłą laskę i drewnianą tarczę.
Pozostałe sklepy także mają krótkie lokalne listy. Serwer odrzuca próbę kupna
przedmiotu spoza oferty danego sprzedawcy. Godot nie wyświetla już całego
katalogu przedmiotów, które mają cenę.

Wszystkie 16 nowych magicznych szablonów otrzymało konkretne źródła wśród
przeciwników. Zachowano również łupy z istniejącego uzbrojenia i jednorazowe
nagrody wcześniejszych zadań. Przedmioty już posiadane przez graczy zostają.

| Przeciwnicy | Przykładowe rzadkie łupy |
| --- | --- |
| Ork szaman | Magiczny kostur +1, pierścień odporności na błyskawice |
| Elfy i krasnoludy | Magiczny łuk, mitrylowa lub adamantynowa kolczuga |
| Strażnicy krypt i ożywione zbroje | Magiczna broń, tarcza lub kolczuga |
| Nieumarli nowej nekropolii | Broń i pancerze krypt, różdżka mumii, szata hierofanta |
| Nowi bossowie | Rzadkie relikty odpowiadające ich podziemiom, w tym magiczne pierścienie |

Szansa magicznego pierścienia nie przekracza 0,3% u zwykłego przeciwnika
i 2% u bossa. Pozostałe nowe łupy bossów mają indywidualne szanse do 6%.
Każda pozycja jest losowana osobno; nie jest to gwarantowana nagroda za zabicie.
Dokładne źródła i prawdopodobieństwa znajdują się w `server/loot_economy.py`.

## Geografia

Krainy mają nieregularne granice i różne wielkości. Poszerzono pustynię,
urozmaicono zatoki i kształty wysp oraz dodano skupiska lasów, kaniony,
przełęcze i rozgałęzione szlaki. Atlas używa tych samych obrysów co serwer
kolizji. Przy brzegach widać pomosty i łódki; atlas pokazuje też połączenia
między przystaniami. Sieć obejmuje 20 portów i 27 dwukierunkowych połączeń.
Powierzchnia dostępnego piaszczystego terenu w obszarze pustyń wzrosła o około 31%
względem UI_19 (kolizje i typ powierzchni, próbki co 400 jednostek świata). Zestawienie końcowej geometrii i jej kontroli znajduje się
w `docs/qa_0.8.18/ui20/`.

## Nekropolia Zgasłego Słońca

Wejście jest na pustyni; znajduje się w Atlasie wśród wejść do podziemi.
Kompleks ma trzy obszerne kondygnacje i 39 głównych komór. Poszczególne
poziomy mają inne układy, boczne sale, powracające połączenia i schody
prowadzące z powrotem na powierzchnię.

1. Aleja Zapomnianych.
2. Sale Balsamistów.
3. Grobowce Dziewięciu Dynastii.

Zamieszkują je szkielety wydmowe, łucznicy z piaskowych krypt,
upiory zasypanej straży i balsamiści bez twarzy. Dodano również rozmówcę,
łańcuch trzech zadań i skrytkę. Zalecana trudność rośnie od poziomu około
35 do 65; wejście nie jest zablokowane poziomem.

| Boss | Miejsce |
| --- | --- |
| Nefret, Strażniczka Skarabeuszy | Sale Balsamistów |
| Akharet, Król Zgasłego Słońca | Grobowce Dziewięciu Dynastii |
| Veyra, Serce Splątanych Korzeni | Jaskinie Szeptającego Korzenia |
| Bezimienny Regent | Katakumby Siedmiu Imion |
| Kormag, Nadzorca Wygasłego Pieca | Sztolnia Czerwonego Oddechu |
| Sędzia Wygaszonych Imion | Archiwum Wygaszonych Pieczęci |

Bossowie używają zapowiadanych ataków obszarowych oraz walki wręcz i dystansowej.
Upiór ma nieumarłą wytrwałość z wyjątkiem krytyków i obrażeń promienistych.
Są to autorscy przeciwnicy Bractwa, bez deklaracji wiernego odwzorowania
oficjalnych statystyk D&D.

## Uruchomienie i aktualizacja

- **RAILWAY_GITHUB_READY**: zawartość ZIP umieść w głównym katalogu
  repozytorium wdrażanego na Railway. Zaktualizuj serwer i folder `web` razem.
  Zachowaj obecną bazę, wolumen i ustawienia środowiska. Strona logowania
  pokazuje **UI_20**, a `/health` zawiera tę samą rewizję.
- **FULL_SOURCE**: pełny projekt, w tym `client/project.godot`, źródła serwera,
  testy, grafiki i narzędzia. Aby sprawdzić natywnego klienta, zaimportuj projekt
  i przebuduj go; dawne APK nie aktualizuje się przez podmianę samych źródeł.
- Po aktualizacji ponownie połącz klienta z serwerem. Zapisana postać stojąca
  na terenie zamienionym w ocean trafia do ostatnio odwiedzonego miasta poza
  blokadą walki. Migracja obejmuje również postacie zapisane w UI_19.

Nie resetowano kont, przedmiotów, zadań ani odkryć. Paczek nie wdrożono
na działający serwer użytkownika.

## Zakres weryfikacji

Raport zbiorczy: `docs/qa_0.8.18/ui20/summary.json`. Testy obejmują działający
serwer, lokalny HTTP i WebSocket, przeglądarkę Chromium w układzie komputera
i telefonu, rzeczywiste kolizje podziemi, łupy, czary oraz płatność za rejs.
Nie testowano na fizycznym telefonie ani na produkcyjnym Railway.

Źródła Godota i odwołania do zasobów sprawdzono w kodzie. W środowisku nie
było silnika Godota, więc nie wykonano importu, uruchomienia ani eksportu APK.
