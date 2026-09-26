> Aktualizacja łowcy w 0.8.12: patrz CHANGELOG_0.8.12.md i PROTOCOL_0.8.12.md. Starsze progi łowcy i koszt Znaku poniżej zastępują nowe zasady.

# Reguły Bractwa 0.8 / 0.8.1 / 0.8.2 / 0.8.3 / 0.8.4 / 0.8.5 — implementacja i różnice względem SRD

## Zmiana 0.8.5 — karta, geometria i skróty

Aktualne szczegóły: `CHANGELOG_0.8.5.md` i `../README.md`. Obszar trafienia i animacja używają wspólnej geometrii: trójkąt stożka, prostokąt linii, koło, kwadrat oraz wieloczęściowe obszary Burzy ognia i Roju meteorów. Wybrany cel ustala środek/kierunek, a ściany, piętra i ochrona PvP nadal filtrują odbiorców. Nie dodano swobodnego wskazywania ziemi. Ta część zastępuje wcześniejsze uproszczenia kształtów.

Pasek ma teraz strony po **24 pola** w rzędach **12 + 12**: 1–0, −, = i F1–F12; nie po osiem. Samodzielna karta C ma Ekwipunek, Statystyki, Atuty i Czary (K). F wybiera rzeczywiście najczęstszy czar/zdolność z ostatnich 100 udanych użyć, z rozstrzygnięciem remisu na korzyść ostatniego. Starsze opisy paska i klasowego F są zastąpione tymi zasadami. Mana, kręgi, Długonogi i pościg z 0.8.4 pozostają bez zmiany.

Uzupełnienie dotyczące wszystkich czarów i zdolności w PvP: `PVP_0.8.1.md`.

## Kości i poziomy

Akcja główna ma odnowienie 3 s, dodatkowa niezależne 3 s. Reakcja Tarcza ma własną gotowość. Ruch trwa ciągle. Nie jest to inicjatywa ani pełne tury stołowego D&D. Poziomy gry nie mają limitu; poziom bojowy dla biegłości i wybranych zdolności wynosi `min(20, 1 + floor(poziom_gry/5))`. Biegłość wynosi +2…+6. Główna cecha klasy wzrasta o 2 na poziomach 20 i 40, maksymalnie do 20.

Maksymalne HP: kość wytrzymałości + modyfikator KON + `floor((poziom-1) × (kość/2+1+KON)/5)` + 2 za punkt witalności. Klasy mają HD10/10/6/8 dla rycerza/łowcy/czarodzieja/druida. HP nie są losowane na awansie. Potwory mają jawne HP i kości ataku w katalogu, bez automatycznego dopasowania do gracza; warianty regionów zachowują autorskie statystyki.

Atak: naturalna 1 pudłuje, naturalna 20 trafia krytycznie. Krytyk podwaja kości, nie dodatek. Rzuty obronne nie korzystają z automatycznego sukcesu 20 ani porażki 1. Udana obrona daje połowę zaokrągloną w dół albo zero według czaru. Sztuczki rosną na 20/50/80. Rycerz ma 2/3/4 ataki na 20/50/95, łowca 2 od 20, niedźwiedź druida 2 od 40. Każdy atak wykonuje osobny rzut. Nie oznacza to dodatkowych rzuceń czaru.

Broń i pancerze mają ograniczone magiczne premie, zwykle 0…+3. Typ pancerza i ZRĘ wpływają na KP. Trening umiejętności z wcześniejszej gry nadal zapisuje statystyki używania, lecz nie dodaje starych, stale rosnących premii ataku. Długie poziomy nadal zwiększają HP i rozwój świata; pula many pełnych czarujących jest ograniczona tabelą poziomów bojowych 1–20 i premią Skupienia.

## Różdżka a sztuczki — zmiana 0.8.2

Podstawowy atak czarodzieja jest autorską Iskrą różdżki: 1k4 ognia bez skalowania i bez modyfikatora obrażeń. Nie jest Ognistym pociskiem ani nową sztuczką SRD. Magiczne różdżki zachowują premię trafienia, wspólną również dla ataków czarami; nie wyświetlają już nieskutecznej premii do obrażeń iskry. Naturalny krytyk iskry to dwie kości k4. Ognisty pocisk z księgi zachowuje kości k10 i progi 20/50/80, a pozostałe sztuczki zachowują efekty i dotychczasowe skalowanie. Sztuczki są bezpłatne. Iskra i sztuczka akcji głównej zużywają tę samą akcję. Kolejka czaru z paska ma pierwszeństwo przed następną iskrą, ale nie zmienia na stałe rodzaju autoataku. Nie zmieniono kości broni pozostałych klas ani odblokowań.

## Pościg — zmiana 0.8.2

Pierwotny `home_x/home_y` służy do odrodzenia i początkowego patrolu. Po pierwszym sprowokowaniu żywy potwór nie wraca do tych współrzędnych. Po utracie celu stoi w miejscu zakończenia pościgu i może z niego podjąć następny. Stary parametr `leash` oznacza teraz granicę aktualnego dystansu potwór–cel: 850 jednostek dla zwykłych stworzeń i 1100 dla bossów. Od 0.8.4 początkowy promień `aggro` niebossów z bazowym HP do 18 jest zmniejszony o 25%, przy HP 19–34 o 12%; silniejsze i bossowie bez zmian. Zasięgi ataków i granica pościgu nie zmieniają się. Przejście przez granicę starego spawnu nie przerywa walki.

Przeszkody, piętra, śmierć i bezpieczne osady są respektowane. Po utracie widoczności potwór przez maksymalnie 12 s zmierza ku ostatnio widzianemu miejscu, nie zna nowych współrzędnych za ścianą. Gdy cel naprawdę zniknął, nie ma ruchu w kierunku domu. Nie kasuje się odnawiania ataków ani otrzymanych obrażeń. Regeneracja wynosi 0,25 HP/s, dopiero po 12 s bez kontaktu bojowego, w symulowanej okolicy; nie ma premii do leczenia za oddalenie od spawnu. Trwające pociski/telegraphy mogą się jeszcze rozstrzygnąć, nie są nowym atakiem ani resetem AI.

Żywe potwory są indeksowane według bieżącej pozycji; śmierć przekierowuje indeks odrodzenia do pierwotnego spawnu. Odrodzenie jest nadal lokalnie aktywowane: jeśli nikt nie odwiedza spawnu, nastąpi po wejściu gracza w okolicę i upływie istniejącego czasu odrodzenia. Po śmierci i odrodzeniu potwór odzyskuje zwykły początkowy patrol. Nie dodano zapisu położeń potworów między restartami serwera.

## Mana i kręgi

Od 0.8.4 czarodziej/druid: I1, II10, III20, IV30, V40, VI50, VII60, VIII70, IX80. Łowca: I20, II40, III60, IV80, V100. Cały dostępny katalog jest znany bez kupowania. Sztuczki kosztują zero, kręgi I–IX: 20/30/50/60/70/90/100/110/130. Pełna mana to suma kosztów slotów tabeli SRD dla poziomu bojowego (pełni czarujący) plus 4 za punkt Skupienia, maks. 20 pkt. Łowca otrzymuje budżet opóźniony, I–V, zaczynając od 2×I na poziomie 20. Jest to **wspólna ważona pula**, nie osobne limity slotów: proporcje rzucanych kręgów można zmieniać. Start maga/druida: 40 many na dwa czary I kręgu; poziom 10: 140 (4×I+2×II); poziom 20: 270 (4×I+3×II+2×III). Pula bez bonusów przestaje rosnąć po osiągnięciu poziomu bojowego 20.

Brak pasywnej regeneracji many w walce i PvP. Poza walką i po 12 s od wydania many: pełna pula w 240 s w terenie lub 20 s w osadzie; promocja daje +25% do tempa. Odnowienie nie przekracza maksimum. Mikstury i usługi odpoczynku nadal dostarczają dodatkowej many. To nie jest podręcznikowy długi odpoczynek. Nie ma przygotowania, rytuałów, upcastingu ani nowych kosztów zdolności klasowych.

Koncentracja utrzymuje jeden taki czar. Obrażenia wymagają obrony KON przeciw `max(10,floor(obrażenia/2))`. Porażka, zgon, rozłączenie albo inny czar koncentracyjny kończy poprzedni efekt. Wezwanie błyskawicy i Promień słońca mogą być ponawiane bez kolejnego kosztu many podczas aktywnej koncentracji. Tarcza to przełączana automatyczna reakcja wydająca 20 many, gdy +5 KP może zmienić trafienie w pudło albo zatrzymać Magiczny pocisk; nie unieważnia naturalnego krytyka. Aktywna Tarcza blokuje wszystkie pociski Magicznego pocisku.

## Długonogi, pasek i widoczne statusy — 0.8.4

Długonogi: akcja główna, 20 many, dotyk (108 jednostek, tak jak Leczenie ran), siebie lub członka drużyny. W SRD: +10 stóp szybkości na godzinę, bez koncentracji; atak ani obrażenia go nie kończą. Godzina = 600 rund stołowych po 6 s. W grze zachowano 600 rund, czyli **1800 s / 30 minut rzeczywistego czasu** przy odnowieniu rundy 3 s. Premia to stałe `10*(32/5)/3` jednostek mapy/s przed mnożnikami ruchu, nie dawny procent szybkości. Nie zwiększa liczby ataków. Recast odświeża czas bez kumulowania. Zakończenie koncentracji innego czaru nie usuwa Długonogiego. Dotychczasowe wylogowanie/restart nadal usuwa aktywne buffy, a rzucanie z wyższego kręgu nie jest obsługiwane.

Pasek ma kolejne strony po 8, tylko odblokowane czary i zdolności. Własne poprawne pozycje pozostają, zablokowane/dublujące wpisy zastępują brakujące czary. Zmiana pozycji w księdze jest zamianą, nie usunięciem drugiego czaru. Awans automatycznie uzupełnia listę.

Serwer podaje `status_effects` dla właściciela, publicznych graczy i potworów: nazwę, opis, ikonę, pozostałe sekundy, zaokrągloną w górę liczbę rund oraz informację o koncentracji. Gotowość Tarczy nie jest mylona z aktywnym bonusem KP. Liczniki wygasają z właściwym efektem, nie według lokalnego zegara klienta. Przy udostępnianiu statusów nie wysyła się wewnętrznych identyfikatorów właścicieli efektów.

## Zdolności klas

Drugi oddech: `1k10+poziom_bojowy`, 5 many, 30 s odnowienia. Łowca: wilk od 10., koszt8, odnowienie45 s; po śmierci wilka nowe45 s. Towarzysz śledzi właściciela, atakuje wybranego przez niego potwora albo dozwolony cel PvP po odblokowaniu blokady, ma własne HP/KP i ginie. Porusza się z kolizjami; nie ma globalnego wyszukiwania ścieżki ani teleportu ratunkowego. Przy trudnym zakręcie może wymagać przeprowadzenia gracza bliżej. Po zmianie piętra znika i wymaga ponownego przywołania.

Druid: wilk20, koszt10, `2k4+2`, szybszy bieg; niedźwiedź40, koszt16, dwa ataki `2k6+4`. Obie formy trwają90 s, współdzielą odnowienie60 s, dodają tymczasowe HP odpowiednio 2×/3× poziom bojowy. Formy znikają po wyczerpaniu tymczasowych HP. W formie nie ma rzucania czarów; ponowne użycie przemiany przywraca postać ludzką bez kosztu. To uproszczona mechanika, a nie pełna lista statystyk Wild Shape SRD.

## Wybrane świadome uproszczenia czarów

Zasięgi przeliczono na jednostki mapy; większość wcześniejszych czasów skrócono do walki w czasie rzeczywistym. Długonogi ma osobno opisaną wyżej zgodność liczby rund z SRD. Własne obszarowe czary nie ranią sojuszników. Obszary losują obrażenia dla kolejnych trafionych przeciwników osobno. Ochrona przed energią używa tylko wariantu ognia. Lodowa burza spowalnia na rundę. Oplątanie pozwala potworom i graczom ponawiać obronę automatycznie co rundę. Pola działają w stałym miejscu; Promień księżyca nie ma osobnego trybu ręcznego przesuwania. Zapalająca chmura nie płynie. Burza ognia ma jeden obszar, a meteory cztery ustalone eksplozje wokół wskazanego celu zamiast czterech dowolnych kliknięć.

Palec śmierci nie tworzy zombie. Leczenie oraz większość buffów mają wybrany, uproszczony zakres odbiorców: leczenie oraz pozytywne buffy obejmują siebie lub drużynę według pola `targeting`; osobiste zdolności pozostają osobiste. Uzdrowienie daje70 HP, bez rozbudowanego systemu usuwania chorób. Gwiaździsty ognik oznacza trafionego statusem światła, ale nie ma systemu niewidzialności. Szokujący uścisk zapisuje blokadę reakcji, natomiast potwory nie mają pełnego systemu ataków okazyjnych. Swoboda ruchu usuwa kary terenu i ignoruje obsługiwane magiczne blokady/spowolnienia. Te zakresy nie są pełnym odtworzeniem podręcznikowych efektów.

Część wizualizacji długotrwałego pola może dogasać niezależnie od końca koncentracji; mechanika obrażeń i unieruchomienia jest usuwana na serwerze natychmiast. Nie deklarujemy całkowitego odtworzenia wszystkich reakcji, odporności, immunitetów, składników, podklas ani listy czarów D&D.

## Autoatak, wybór i bezpieczeństwo

Wybrany potwór albo dozwolony gracz po odblokowaniu PvP jest atakowany tylko w zasięgu, na tym samym piętrze i przy linii widzenia. Postać nie goni, nie wybiera nowego celu, nie strzela przez ściany. Jeden czar główny może oczekiwać maksymalnie4 s przed autoatakiem; nowsze zlecenie zastępuje starsze. Wybór sojusznika do leczenia nie wyłącza blokady PvP. Ranking jest tylko odczytem TOP20. Wszystkie kości, wymagania, cele, koszty i czasy sprawdza serwer, nie klient.

Źródło materiału SRD: https://www.dndbeyond.com/srd (SRD 5.2.1, CC BY4.0). Pełna wymagana atrybucja: `../LICENSE-SRD.txt`. Bractwo i jego własna adaptacja nie są oznaczone jako produkt oficjalny.

Źródła sprawdzone dla zmiany 0.8.4: https://www.dndbeyond.com/spells/2619004-longstrider ; https://www.dndbeyond.com/sources/dnd/free-rules/playing-the-game ; https://www.dndbeyond.com/sources/dnd/free-rules/character-classes . Tabela slotów jest źródłem liczebności; wagi many i tempo odnowienia są adaptacją Bractwa.
