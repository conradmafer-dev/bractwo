# Walka 0.7 — rundy w czasie rzeczywistym

Każda postać ma własny czas gotowości. Pierwszy atak wykonujesz natychmiast, kolejna akcja jest dostępna po 3 sekundach. Świat, ruch i potwory działają przez cały ten czas. Nie ma wspólnej kolejki uczestników ani zatrzymywania gry.

## Sterowanie

- Spacja / przycisk Atakuj: jedna próba ataku. Przytrzymanie ponawia próby, kiedy wraca gotowość. Puszczenie przerywa ponawianie.
- Bez celu: najbliższy żywy potwór w zasięgu broni, na tym samym piętrze i bez przeszkody na linii ataku. Nigdy przypadkowy gracz.
- Opcjonalne kliknięcie potwora / wiersza listy: wybór konkretnego celu. Gdy wybrany cel jest poza zasięgiem, serwer nie atakuje za ciebie innego. Esc usuwa zaznaczenie.
- Atak, F, czar i użycie runy zużywają tę samą akcję. Ich własne koszty oraz dłuższe odnowienia również obowiązują.
- Naciśnięcie podczas odnowienia jest odrzucane, bez kosztu i bez kolejki. Samo zaznaczenie nie uruchamia walki.
- Pusta próba bez poprawnego celu nie rozpoczyna odnowienia. Udana próba trafienia, także pudło, rozpoczyna 3 s odnowienia.
- Mikstury i tworzenie run zachowują własne odnowienia. Premia szybkości ruchu nie skraca rundy.

Przykład: atak o czasie 0,0 s; ruch i unik przez następne sekundy; naciśnięcie o 1,0 s zostaje odrzucone; kolejny atak wymaga naciśnięcia po 3,0 s albo dalszego przytrzymywania przycisku. Nie nastąpi sam, jeśli puścisz przycisk wcześniej.

## Trafienie i obrażenia

| Próba | Rozstrzygnięcie |
| --- | --- |
| Cios, strzał, pocisk magiczny, pojedyncza runa | k20 + premia trafienia ≥ KP celu |
| Naturalne 1 | Pudło, niezależnie od premii |
| Naturalne 20 | Trafienie krytyczne; dwa razy więcej kości obrażeń, stały dodatek liczony raz |
| Strzał / pocisk magiczny z przeciwnikiem do 72 jednostek | Dwie k20; wybierana niższa |
| Czar / runa obszarowa | Cel rzuca k20 + obrona przeciw ST czaru; sukces zmniejsza obrażenia o połowę |
| Specjalne pola bossów | Wyjście z pola unika trafienia; pozostając w polu, wykonujesz rzut obronny |

Naturalne 1 i 20 nie zastępują porównania sumy w rzutach obronnych. Zwykłe pociski potworów, ciosy i ataki graczy sprawdzają KP. Specjalne ataki bossów używają obrony przeciw ST. W obu przypadkach obowiązują piętro, strefy bezpieczeństwa i linia widzenia.

Początkowy rycerz z kurtką ma KP 13 i premię trafienia +4. Jego zwykłe obrażenia to 3k6+12. Przeciw goblinowi o KP 12 wynik k20 = 11 daje sumę 15 i trafienie. Kości obrażeń 2, 4, 5 oznaczają 23 obrażenia. Krytyk tej samej broni używa 6k6+12. To liczby obecnego balansu gry.

Losowania wykonuje wyłącznie serwer. HUD pokazuje faktyczny wynik, próg i obrażenia. Dane o rzucie lub gotowości przesłane w komendzie klienta nie zmieniają rezultatu.

## Przeniesienie dotychczasowych statystyk

Osiągnięte poziomy, trening, specjalizacja i łupy pozostają. Nie przeskalowano kont do 20. poziomu. Rozwój zwiększa obrażenia i zdrowie jak wcześniej; premie do k20/KP rosną wolniej, z ograniczonym wkładem każdego składnika.

- Premia trafienia: 4 + do 6 za poziom + do 3 za trening właściwej umiejętności + premie założonych przedmiotów.
- Bazowe KP: rycerz/paladyn 12, mag 10, druid 11; dodatkowo do 4 za poziom, do 2 za trening obrony i premie wyposażenia.
- Przedmiot: premia KP to zaokrąglony w górę pierwiastek starej wartości pancerza. Premia trafienia to zaokrąglony w górę pierwiastek premii obrażeń podzielony przez 5, maksymalnie +3 na przedmiot. Statystyki są pobierane z szablonu serwera.
- Obrażenia zachowują zbliżoną średnią pojedynczego dotychczasowego ciosu. Broń używa k6 (miecz), k8 (łuk) lub k10 (pocisk). Liczba kości i stały dodatek rosną wraz z bazowymi obrażeniami. Limit liczby zwykłych kości wynosi 24; dalszy rozwój podnosi dodatek.
- KP zastępuje odejmowanie starego pancerza w walce z rzutami. Bastion i osłona kapliczki nadal redukują obrażenia po trafieniu. Osłona kapliczki nie działa w PvP.
- Potwory mają KP wynikające z gatunku i przedziału poziomu, własną premię trafienia i obrony. Szybki wilk atakuje co 2,7 s, ciężki golem co 3,4 s, większość gatunków co 3 s. Ruch nie czeka na odnowienie. Specjalności bossów mają osobny rytm.

Tempo zabijania zmienia się: wolniejsze akcje i możliwość pudła wydłużają walkę. Potwory również atakują rzadziej i mogą chybić. Testy sprawdzają reguły oraz zachowanie pościgu; długie sesje balansujące nie zostały przeprowadzone.

## Zapis i bezpieczeństwo

Wspólna gotowość korzysta z zapisywanego terminu serwera. Wylogowanie i restart nie pozwalają ominąć rundy. Stare przedmioty otrzymują nowe statystyki z katalogu bez zmiany UID ani założonych slotów.

Pudło prowokuje potwora, ale samo nie daje udziału w łupie. W PvP próba ataku nadal oznacza agresję, nawet gdy chybi. Dotychczasowe zasady ochrony początkujących, miast, drużyn i czaszek pozostają.

To pierwszy etap adaptacji D&D. Mana, profesje i wcześniejsze czary nadal obowiązują. Sloty, koncentracja, reakcje, dodatkowe ataki, sześć cech oraz inicjatywa nie są częścią 0.7.
