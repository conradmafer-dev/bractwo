# Reguły Bractwa 0.8 — implementacja i różnice względem SRD

## Kości i poziomy

Akcja główna ma odnowienie 3 s, dodatkowa niezależne 3 s. Reakcja Tarcza ma własną gotowość. Ruch trwa ciągle. Nie jest to inicjatywa ani pełne tury stołowego D&D. Poziomy gry nie mają limitu; poziom bojowy dla biegłości i wybranych zdolności wynosi `min(20, 1 + floor(poziom_gry/5))`. Biegłość wynosi +2…+6. Główna cecha klasy wzrasta o 2 na poziomach 20 i 40, maksymalnie do 20.

Maksymalne HP: kość wytrzymałości + modyfikator KON + `floor((poziom-1) × (kość/2+1+KON)/5)` + 2 za punkt witalności. Klasy mają HD10/10/6/8 dla rycerza/łowcy/czarodzieja/druida. HP nie są losowane na awansie. Potwory mają jawne HP i kości ataku w katalogu, bez automatycznego dopasowania do gracza; warianty regionów zachowują autorskie statystyki.

Atak: naturalna 1 pudłuje, naturalna 20 trafia krytycznie. Krytyk podwaja kości, nie dodatek. Rzuty obronne nie korzystają z automatycznego sukcesu 20 ani porażki 1. Udana obrona daje połowę zaokrągloną w dół albo zero według czaru. Sztuczki rosną na 20/50/80. Rycerz ma 2/3/4 ataki na 20/50/95, łowca 2 od 20, niedźwiedź druida 2 od 40. Każdy atak wykonuje osobny rzut. Nie oznacza to dodatkowych rzuceń czaru.

Broń i pancerze mają ograniczone magiczne premie, zwykle 0…+3. Typ pancerza i ZRĘ wpływają na KP. Trening umiejętności z wcześniejszej gry nadal zapisuje statystyki używania, lecz nie dodaje starych, stale rosnących premii ataku. Długie poziomy nadal zwiększają HP, manę i rozwój świata.

## Mana i kręgi

Czarodziej/druid: I krąg 10, II20, III30, IV40, V50, VI60, VII70, VIII80, IX90. Łowca: I20, II40, III60, IV80, V100. Sztuczki są darmowe. Koszty kręgów: 6/10/16/22/30/40/52/66/84 many. Nie ma zużywalnych slotów, przygotowania, rytuałów ani upcastingu. Regeneracja trwa także w walce (0,6/s); poza walką jest szybsza, dodatkowo w bezpiecznej strefie. Sztuczki pozwalają kontynuować walkę przy zerze many.

Koncentracja utrzymuje jeden taki czar. Obrażenia wymagają obrony KON przeciw `max(10,floor(obrażenia/2))`. Porażka, zgon, rozłączenie albo inny czar koncentracyjny kończy poprzedni efekt. Wezwanie błyskawicy i Promień słońca mogą być ponawiane bez kolejnego kosztu many podczas aktywnej koncentracji. Tarcza to przełączana automatyczna reakcja wydająca 6 many dopiero, gdy +5 KP może zmienić trafienie w pudło; nie unieważnia naturalnego krytyka.

## Zdolności klas

Drugi oddech: `1k10+poziom_bojowy`, 5 many, 30 s odnowienia. Łowca: wilk od 10., koszt8, odnowienie45 s; po śmierci wilka nowe45 s. Towarzysz śledzi właściciela, atakuje wyłącznie jego wybrany cel PvE, ma własne HP/KP i ginie. Porusza się z kolizjami; nie ma globalnego wyszukiwania ścieżki ani teleportu ratunkowego. Przy trudnym zakręcie może wymagać przeprowadzenia gracza bliżej. Po zmianie piętra znika i wymaga ponownego przywołania.

Druid: wilk20, koszt10, `2k4+2`, szybszy bieg; niedźwiedź40, koszt16, dwa ataki `2k6+4`. Obie formy trwają90 s, współdzielą odnowienie60 s, dodają tymczasowe HP odpowiednio 2×/3× poziom bojowy. Formy znikają po wyczerpaniu tymczasowych HP. W formie nie ma rzucania czarów; ponowne użycie przemiany przywraca postać ludzką bez kosztu. To uproszczona mechanika, a nie pełna lista statystyk Wild Shape SRD.

## Wybrane świadome uproszczenia czarów

Zasięgi przeliczono na jednostki mapy; czasy skrócono do walki w czasie rzeczywistym. Własne obszarowe czary nie ranią sojuszników. Obszary losują obrażenia dla kolejnych trafionych potworów osobno. Ochrona przed energią używa tylko wariantu ognia. Lodowa burza spowalnia na rundę. Oplątanie pozwala potworom ponawiać obronę automatycznie co rundę. Pola działają w stałym miejscu; Promień księżyca nie ma osobnego trybu ręcznego przesuwania. Zapalająca chmura nie płynie. Burza ognia ma jeden obszar, a meteory cztery ustalone eksplozje wokół wskazanego celu zamiast czterech dowolnych kliknięć.

Palec śmierci nie tworzy zombie. Leczenie oraz większość buffów mają wybrany, uproszczony zakres odbiorców: leczenie może obejmować drużynę, buffy zazwyczaj właściciela. Uzdrowienie daje70 HP, bez rozbudowanego systemu usuwania chorób. Gwiaździsty ognik oznacza trafionego statusem światła, ale nie ma systemu niewidzialności. Szokujący uścisk zapisuje blokadę reakcji, natomiast potwory nie mają pełnego systemu ataków okazyjnych. Swoboda ruchu usuwa kary terenu i ignoruje obsługiwane magiczne blokady/spowolnienia. Te zakresy nie są pełnym odtworzeniem podręcznikowych efektów.

Część wizualizacji długotrwałego pola może dogasać niezależnie od końca koncentracji; mechanika obrażeń i unieruchomienia jest usuwana na serwerze natychmiast. Nie deklarujemy całkowitego odtworzenia wszystkich reakcji, odporności, immunitetów, składników, podklas ani listy czarów D&D.

## Autoatak, wybór i bezpieczeństwo

Wybrany potwór jest atakowany tylko w zasięgu, na tym samym piętrze i przy linii widzenia. Postać nie goni, nie wybiera nowego celu, nie strzela przez ściany. Jeden czar główny może oczekiwać maksymalnie4 s przed autoatakiem; nowsze zlecenie zastępuje starsze. Wybór sojusznika do leczenia nie wyłącza blokady PvP. Ranking jest tylko odczytem TOP20. Wszystkie kości, wymagania, cele, koszty i czasy sprawdza serwer, nie klient.

Źródło materiału SRD: https://www.dndbeyond.com/srd (SRD 5.2.1, CC BY4.0). Pełna wymagana atrybucja: `../LICENSE-SRD.txt`. Bractwo i jego własna adaptacja nie są oznaczone jako produkt oficjalny.
