# Aktualizacja 0.6.0

Obowiązujące zmiany, parametry podłoża, AI, premium testowe oraz bieżące liczby są w README.md, CHANGELOG_0.6.md, BESTIARY_0.6.md i WORLD_ATLAS.md. Poniżej zachowano wcześniejsze założenia projektu; historyczne liczby nie opisują bieżącego rozmieszczenia.

# Bractwo 0.4.1 — świat i rozwój

## Założenie

Podróż pomiędzy miastami ma wymagać przygotowania. Pięć odległych ośrodków na kontynencie 128000 × 92160 zastępuje wariant pięciu miast na powierzchni tylko 20 razy większej od startowej mapy. Obecny mnożnik powierzchni wynosi 1600. Domy, NPC, rozmiary postaci i komnaty nie zostały rozciągnięte razem z odległościami.

Pętla: przygotowanie w mieście → wybór dalekiego łowiska → polowanie i odkrycia → powrót z łupem → wyposażenie, trening, promocja i trudniejsza wyprawa. Statki kosztują złoto i działają wyłącznie przy kapitanie. Bank, depozyt i możliwość wyboru miasta odrodzenia pomagają organizować wyprawy.

## Inspiracja klasycznym otwartym RPG

Cztery profesje, trening przez używanie broni/many, runy i dusza, promocja, wypowiadane inkantacje, odradzające się grupy potworów, piętra jaskiń oraz strefy ochronne wzmacniają kierunek Tibia-like. Mapa, statystyki, progi czarów, kara śmierci i szybkość pozostają własnym balansem projektu.

Wrogowie mają stałe statystyki. Zalecenia poziomu na atlasie informują o niebezpieczeństwie, a nie dostosowują świata do gracza. Zwykłe krainy i jaskinie są dostępne od początku. Jedyny nowy próg przejścia to poziom 100 przed ostatnim piętrem Serca Otchłani.

## Konstrukcja kontynentu

20 dużych regionów ma odrębne palety i zestawy przeciwników. Oryginalna Przystań i początkowe zadania zachowują swoje współrzędne. Rozległe obszary korzystają z deterministycznych obozów z grupami pięciu przeciwników, przeszkodami i dekoracjami. Dziesięć podziemi ma po dwa piętra połączonych komnat. Układ komnat i część obozów są powtarzalne; objętość mapy nie oznacza tej samej gęstości ręcznie przygotowanej zawartości co obszar startowy.

Atlas WWW pokazuje cały kontynent i pozwala zaznaczyć cel. Minimapę lokalną oraz kierunek uzupełniają opisowe zalecenia poziomu. Klient Godot udostępnia mapę kontynentu i listy celów w księdze. Nawigacja nie uruchamia automatycznego marszu.

## Progresja

Pełne progi i sterowanie znajdują się w README. Najważniejsze nowe decyzje to promocja za złoto, zarządzanie zapasem run/many/duszy, wybór łowiska, przechowanie łupu przed daleką wyprawą oraz rozwój trzech gałęzi specjalizacji po poziomie 50. Poziomy nie mają limitu, lecz obecne krainy i przedmioty mają skończony zakres.

Nowe ofensywne czary i runy służą PvE. PvP nadal korzysta z celowanego ataku podstawowego, czaszek i ograniczeń dla początkujących. Błogosławieństwo łagodzi jedną zwykłą śmierć, ale nie karę czerwonej czaszki.

## Wydajność i dalsze próby

Serwer indeksuje przeszkody i punkty odrodzenia przestrzennie, aktualizuje przede wszystkim potwory w sąsiedztwie graczy i przesyła pobliskie potwory tego samego piętra. Klient WWW przechowuje fragmenty nowego terenu po 512 × 512; bufor ma minimum 32 miejsca i rozszerza się, aby nie usuwać widocznych fragmentów na dużym ekranie. Osobno pozostaje mapa startowa. Godot zachowuje fragmenty 768 × 768 z tymi samymi kaflami 48 × 48. Nowe fragmenty powstają dopiero przy zmianie widocznej okolicy.

Do dalszej oceny w rozgrywce pozostają atrakcyjność długich tras, gęstość punktów zainteresowania, ekonomia podróży i mikstur, balans wysokich poziomów i urządzenia mobilne. Stan wykonanych sprawdzeń: TEST_REPORT.md. Dokumentacja 0.2/0.3 opisuje historię projektu i nie określa obecnego rozmiaru świata.
