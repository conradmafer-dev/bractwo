# UI_30 — łowiska potworów

Baza: UI_29 z ulepszonym terenem. Ta aktualizacja rozbudowuje sposób rozmieszczenia istniejących przeciwników na powierzchni.

## Zakres

**159 łowisk, 438 niewielkich podgrup i 1149 przeniesionych przeciwników** w **20 krainach**. Układy wykorzystują 18 tematycznych rodzin. Przestawiono część z 11 149 powierzchniowych spawnów; 373 spawny na innych piętrach i 28 osobnych potworów początkowych pozostają na swoich miejscach.

## Układ łowisk

Przy nowych formacjach terenu i wybranych dojściach powstają tematyczne układy: czaty, obozowiska, watahy, pajęcze zagajniki, suche brzegi bagien, dziedzińce ruin, legowiska i szczeliny. Wojownicy zajmują skraj łowiska, strzelcy i szamani głębsze lub boczne pozycje. Zwierzęta i duzi przeciwnicy mają inne odstępy niż mieszkańcy obozu.

Kilka niewielkich grup tworzy miejsce do eksploracji. Rozkład pozostawia podejście i wyjście, a nowi mieszkańcy otrzymują sprawdzone połączenie z istniejącą drogą. Dekoracje siedlisk stoją przy ich rzeczywistych mieszkańcach. Reszta dotychczasowych potworów pozostaje w świecie jako tło.

## Zasady zachowania zawartości

- Zachowano układ potworów w początkowej dolinie i wokół Przystani.
- Relokacja zachowuje indeks każdego potwora, jego gatunek, piętro i faktyczną krainę. Nie zwiększa liczby przeciwników.
- Statystyki walki, doświadczenie, łupy, czas odradzania i zasady AI pozostają dotychczasowe.
- Chronione są bossy, pozostałe piętra, nazwane wcześniejsze łowiska, wskazane miejsca łupu i mieszkańcy wskazani w zadaniach.
- Istniejące identyfikatory zadań, odkryć i ważnych miejsc pozostają zachowane. Nowe anonimowe siedliska nie przyznają dodatkowego doświadczenia za odkrycie.
- Odstęp nowych pozycji od drogi uwzględnia zasięg agresji i zwykłe wędrowanie. Po sprowokowaniu przeciwnika nadal działa jego dotychczasowy pościg.

## Sprawdzenia i ograniczenia

Dokładne liczby i wyniki są zapisane w `docs/qa_0.8.18/ui30/summary.json`. Podglądy i pełne dane porównawcze w paczce pełnych źródeł, w tej samej lokalizacji, przedstawiają rzeczywiste pozycje potworów, drogi i przeszkody; nie są zrzutami pełnego interfejsu gry.

Przeszło 67 wykonań testów automatycznych: 11 testów łowisk, 21 wspólnie uruchomionych testów terenu i kontynentu, 13 atlasu, 19 mechanik klienta i 3 renderowania terenu. Ponadto przeszły 4 sprawdzenia HTTP/WebSocket i niezależny audyt świata. Obejrzano 6 dokładnych porównań położeń przed/po i 6 zbliżeń. Zweryfikowano dostęp do wszystkich 1149 nowych stanowisk oraz patrolowanie i odradzanie przedstawicieli 8 rodzin.

Świat jest generowany deterministycznie po uruchomieniu serwera. Rozmieszczenie wykorzystuje istniejące mechanizmy spawnu i odradzania, bez dodatkowego przeliczania podczas każdego kroku gry. Nie wymaga resetowania postaci.

Pełny świeży import serwera trwał około 27 sekund podczas równoległych sprawdzeń na współdzielonej maszynie. Jest to czas przygotowania całego świata przy starcie procesu, a nie pomiar płynności gry ani gwarantowany czas uruchomienia na Railway.

Nie wykonano pełnego testu przeglądarki, fizycznego telefonu, uruchomienia ani eksportu Godota. Paczki przygotowano do wdrożenia; nie wdrożono ich na Railway w ramach tej aktualizacji.
