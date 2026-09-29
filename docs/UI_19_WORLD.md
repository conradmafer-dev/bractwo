# Bractwo 0.8.18 UI_19 — kontynent, wyspy i lokalne wyprawy

UI_19 przebudowuje geografię, drogi i osady, zachowując identyfikatory dotychczasowych zadań, odkryć i miast. Początkowa dolina Przystani pozostaje rozpoznawalna. Stare wejścia do podziemi zachowują swoje położenia i połączenia; zmienione wybrzeże uwzględnia ich dostępność.

## Geografia i krainy

Mapa ma rzeczywiste morze, zatoki, rzeczne dopływy, mosty i pomosty. Ląd tworzą **Kontynent Pogranicza**, **Wyspy Słonecznych Wydm**, **Wyspy Żaru**, **Archipelag Lodowej Korony**, **Smocze Wyspy**, **Wyspy Rozdarcia**, **Archipelag Obsydianu**, **Wyspy Morza Popiołu** oraz mniejsze **Solne Ławice**, **Wyspa Białej Latarni** i **Czarne Ławice**. Dodatkowe przylądki chronią dojścia do dawnych miejsc wypraw.

Każda z 20 krain ma osobny układ dróg i terenów:

| Kraina | Charakter układu |
| --- | --- |
| Marchie Przystani | Doliny, pola i szlaki pierwszych wypraw |
| Bory Szeptów | Leśne ostępy i połączone polany |
| Wyżyna Orków | Rozgałęzione warowne trakty |
| Złote Wybrzeże | Drogi nadmorskie i dojścia do portu |
| Wydmy Zapomnianych | Szlaki pomiędzy wydmami i oazami |
| Bagna Trzcin | Rozlewiska, groble i mokradła |
| Zielona Dolina | Polany i leśne osady |
| Cmentarz Królów | Cmentarne aleje i boczne dziedzińce |
| Pustynne Grobowce | Szlak grobowców i kamienne odnogi |
| Wulkaniczne Pustkowia | Drogi wokół krateru |
| Równiny Minotaurów | Pastwiska i dłuższe otwarte trakty |
| Góry Żelaznego Serca | Przełęcze kamieniołomów |
| Śnieżna Granica | Tundra i przejścia między śnieżnymi polami |
| Kraina Lodowej Korony | Fiordy i lodowe szlaki |
| Smocze Urwiska | Granie i podejścia na wyspie |
| Miasto Pod Korzeniami | Ruiny w leśnej sieci dróg |
| Królestwo Bez Słońca | Martwe knieje i zamknięte obwody ruin |
| Rozdarcie Demonów | Rozgałęzienia wokół pęknięć ziemi |
| Obsydianowy Bastion | Obwód tarasów i wewnętrzne przejścia |
| Morze Popiołu | Szlaki między polami popiołu |

38 dawnych punktów typu „Stary obóz” i „Kamienny krąg” otrzymało indywidualne nazwy. Ich identyfikatory oraz zaliczone odkrycia pozostają zachowane. Atlas i minimapa pokazują tę samą geografię co świat gry.

## Dziesięć miast i osad

Rozmiar wpływa na zabudowę, bruk i zasięg bezpiecznej strefy. Kupcy mają własny asortyment; serwer sprawdza dostępność towaru u konkretnego sprzedawcy.

| Osada | Funkcja i handel | Dostępne usługi |
| --- | --- | --- |
| Przystań | Wioska wyprawowa; podstawowy ekwipunek i zapasy | Kupiec, bank/depozyt, mistrz profesji, przewoźnik |
| Brzezina | Osada łowców i zielarzy; łuki, skóry, laski i fokusy | Kupcy, bank/depozyt, mistrz profesji, przewoźnik |
| Złoty Port | Największe miasto kupieckie; pancerze, broń, relikty i handel zamorski | Kupcy, bank/depozyt, mistrz profesji, przewoźnik |
| Mroźna Przystań | Port wypraw polarnych; wyposażenie ekspedycji i ciężka broń | Kupcy, bank/depozyt, mistrz profesji, przewoźnik |
| Popielny Port | Warowna przystań; uzbrojenie na najdalsze wyprawy | Kupcy, bank/depozyt, mistrz profesji, przewoźnik |
| Solna Przystań | Rybacka osada; lekkie uzbrojenie i zapasy | Kupiec, przewoźnik |
| Żarowe Nabrzeże | Osada górników; broń i pancerze z kuźni | Kupiec, przewoźnik |
| Przełom Rzeki | Mały przystanek rzeczny; zapasy podróżne | Kupiec, przewoźnik |
| Przystań Cieni | Osada badaczy ruin; fokusy i wyposażenie badaczy | Kupiec, przewoźnik |
| Bazaltowa Strażnica | Strażnica na wyspie; tarcze i ciężkie uzbrojenie | Kupiec, przewoźnik |

Nie każda osada ma bank, depozyt lub mistrza profesji. Odwiedzenie miasta nadal automatycznie zapisuje je jako miejsce odrodzenia, zgodnie z [UI_18](UI_18_RESPAWN_CITY.md).

## Czternaście portów i siedemnaście tras

Port ma każda z dziesięciu osad. Cztery dodatkowe przystanie to **Smocza Przeprawa**, **Solne Ławice**, **Biała Latarnia** i **Czarne Ławice**. Same przystanie nie są nowymi miastami ani miejscami odrodzenia.

Przewoźnik oferuje tylko lokalne połączenia ze swojego portu. Dalsza podróż może wymagać przesiadki. Wszystkie poniższe trasy są dwukierunkowe — razem **34 kierunkowe rejsy**. Cena dotyczy pojedynczego przejazdu.

| Połączenie | Złoto | Minimalny poziom |
| --- | ---: | ---: |
| Przystań ↔ Brzezina | 45 | 8 |
| Brzezina ↔ Przełom Rzeki | 25 | 8 |
| Przystań ↔ Złoty Port | 90 | 8 |
| Złoty Port ↔ Solna Przystań | 55 | 15 |
| Solna Przystań ↔ Żarowe Nabrzeże | 45 | 20 |
| Żarowe Nabrzeże ↔ Mroźna Przystań | 65 | 25 |
| Mroźna Przystań ↔ Bazaltowa Strażnica | 75 | 30 |
| Przełom Rzeki ↔ Przystań Cieni | 70 | 25 |
| Przystań Cieni ↔ Bazaltowa Strażnica | 45 | 30 |
| Bazaltowa Strażnica ↔ Popielny Port | 55 | 35 |
| Mroźna Przystań ↔ Złoty Port | 80 | 20 |
| Mroźna Przystań ↔ Smocza Przeprawa | 35 | 30 |
| Solna Przystań ↔ Solne Ławice | 18 | 15 |
| Żarowe Nabrzeże ↔ Biała Latarnia | 25 | 20 |
| Biała Latarnia ↔ Mroźna Przystań | 25 | 20 |
| Przełom Rzeki ↔ Czarne Ławice | 35 | 25 |
| Czarne Ławice ↔ Przystań Cieni | 25 | 25 |

## Nowe wyprawy

Dodano **18 zadań**, **12 terenowych rozmówców** i **68 punktów odkryć związanych z przygodami**. Osiem nowych kompleksów obejmuje sześć małych podziemi oraz większe jaskinie i katakumby — łącznie **13 podziemnych kondygnacji**:

- Piwnice Złamanego Dzwonu;
- Jaskinie Szeptającego Korzenia — 4 poziomy;
- Katakumby Siedmiu Imion — 3 poziomy;
- Komnata Zagubionego Południka;
- Sztolnia Czerwonego Oddechu;
- Schronisko pod Lodowym Łukiem;
- Krypta Strażników Grani;
- Archiwum Wygaszonych Pieczęci.

Trzy nowe wzgórza przy Komnacie Zagubionego Południka, Schronisku pod Lodowym Łukiem i Krypcie Strażników Grani mają po dwa dostępne tarasy. To kolejne **6 obszarów na dodatnich poziomach**. Szczegóły rozmów, łańcuchów zadań, przeciwników i nagród: [UI_19 — wyprawy](UI_19_WYPRAWY.md).

## Walka, przedmioty i interfejs

- Czas ponownego pojawiania się potworów zwiększono **1,75 raza**, z minimum **45 s** dla zwykłych przeciwników i **180 s** dla bossów. Nie zmienia to czasu odrodzenia postaci gracza.
- Wypicie mikstury zdrowia zużywa **akcję dodatkową**, zgodnie z D&D 2024. Dzieli jej dostępność z pozostałymi akcjami dodatkowymi; osobny dawny cooldown mikstury został zastąpiony tą zasadą.
- Usunięto nieaktualne paski treningu: walki wręcz, walki dystansowej, poziomu magicznego i obrony tarczą.
- Nowe magiczne przedmioty, ich działanie, dostrojenie i dostępność opisuje [UI_19 — magiczne przedmioty](UI_19_MAGIC_ITEMS.md).

Te zmiany dotyczą wskazanych mechanik. Bractwo nadal ma własną geografię, skalę poziomów, czas rundy i system many; aktualizacja nie oznacza pełnej zgodności całej wcześniejszej gry z zasadami D&D.

## Aktualizacja z paczki RAILWAY_GITHUB_READY

1. Zachowaj istniejący wolumen Railway, bazę graczy i ustawienia usługi. Sprawdź kopię zapisu przed aktualizacją. `run.py` wykonuje kopię istniejącej bazy przez API SQLite do folderu `backups` obok bazy przed uruchomieniem migracji.
2. Rozpakuj zawartość paczki **UI_19 RAILWAY_GITHUB_READY** do katalogu głównego dotychczasowego repozytorium. `Dockerfile`, `run.py`, `requirements.txt`, `server/` i `web/` mają pozostać na tym samym poziomie. Nie zastępuj pliku bazy ani katalogu danych pustym zapisem z innego środowiska.
3. Zachowaj dotychczasowy `BRACTWO_DB_PATH`, jeśli jest ustawiony. Bez własnej wartości serwer używa `world.sqlite3` na podłączonym wolumenie Railway; lokalnie jest to `data/world.sqlite3`. Wolumen ma pozostać podpięty do tej samej usługi. Uruchamiaj jedną replikę korzystającą z tej bazy.
4. Wyślij zmiany do gałęzi wdrażanej przez Railway i uruchom nową wersję serwera. Aktualizacja wymaga nowych plików serwera oraz przeglądarki.
5. Odśwież stronę lub ponownie otwórz zainstalowaną aplikację gry. Sprawdź oznaczenie **UI_19**, dotychczasową postać oraz Atlas. Samo przygotowanie paczki nie wdraża jej na Railway.

Reset kont i postaci nie jest potrzebny. Zachowane są wyposażenie, postęp, identyfikatory starych zadań i zaliczone odkrycia. Przy wczytaniu starszej postaci stojącej na powierzchni zamienionej teraz w morze serwer przenosi ją poza aktywną blokadą walki do ostatnio odwiedzonego miasta. Brak rozpoznanego miasta oznacza Przystań. Migracja mapy nie przyznaje nowego poziomu ani nagród za ponowne odkrycie już zaliczonego miejsca.

## Kontrola geometrii

Raport [continent_results.json](qa_0.8.18/ui19/continent_results.json) obejmuje trzy celowane kontrole: kolizje punktów i spawnów, piesze dojścia do usług i wejść oraz spójność sieci rejsów i odmienność dróg. Zapisany wynik: **3/3 PASS**; dokładne liczby sprawdzonych obiektów znajdują się w raporcie. Wnętrza mają również odrębne kontrole opisane w dokumentacji wypraw. Nie jest to deklaracja pełnej regresji wszystkich mechanik gry.
