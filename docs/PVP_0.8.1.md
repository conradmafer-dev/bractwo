# Magia i zdolności w PvP — Bractwo 0.8.1

## Jak używać

Wyłącz blokadę PvP świadomym przyciskiem, zaznacz gracza na mapie albo liście i użyj paska 1–8, księgi lub zdolności F. Samo wskazanie gracza przy włączonej blokadzie nie wykonuje ataku. Odblokowanie może uruchomić autoatak już wybranego gracza, jeśli jest prawidłowym celem. Esc / × celu usuwa wybór. Postać ani wilk nie wybierają samodzielnie kolejnego przeciwnika będącego graczem.

Wspierający czar skierujesz na członka drużyny, zaznaczając go przed rzuceniem. Zaznaczenie przeciwnika nie przekierowuje na niego własnego leczenia: pasek użyje wtedy czaru na własnej postaci. Drugi oddech, Shillelagh, Tarcza, przemiany, teleport i przywołanie towarzysza są zdolnościami osobistymi; nie można ich przekazać innemu graczowi. Leczenie obszarowe wybiera uprawnionych członków drużyny w zasięgu.

## Co objęto obsługą graczy

Cały obecny katalog 47 wpisów: 43 czary/sztuczki oraz 4 zdolności klasowe. Ofensywne wpisy mogą wybierać graczy; osobiste i wspierające wpisy zachowują swój sens, zamiast działać jako atak. Dotyczy to pojedynczych pocisków, wielokrotnych promieni, stożków, linii, eksplozji, łańcucha błyskawic, meteorów, utrzymywanych pól i obrażeń za ruch. Pola uwzględniają graczy również wtedy, gdy utworzono je na potworze.

Gracze wykonują własne rzuty obronne zgodne z cechą czaru. ZRĘ przy unieruchomieniu oraz Przewidywanie uwzględniają niekorzyść/korzyść. Porażający uścisk blokuje reakcję, Promień mrozu spowalnia, Ciernisty bicz przyciąga, Oplątanie pozwala ponawiać obronę. Koncentracja kończy własny efekt rzucającego także wtedy, gdy nałożono go na inną postać. Nie usuwa cudzego efektu tylko dlatego, że nosi tę samą nazwę.

Tarcza może zmienić trafienie w pudło i blokuje Magiczny pocisk. Odporności działają na odpowiednie składniki obrażeń, np. przy Lodowej burzy lub meteorach. Tymczasowe HP, zerwanie koncentracji, śmierć i przypisanie zabójstwa stosują wspólną ścieżkę obrażeń gracza.

Łowca może oznaczyć gracza Znakiem łowcy. Wilk uderza w wybrany przez właściciela, dozwolony cel PvP, z własnym rzutem trafienia; konsekwencje agresji obciążają właściciela. Przemieniony druid atakuje według statystyk formy, nadal nie rzucając czarów w formie. Dodatkowe ataki pozostają oddzielnymi rzutami.

## Ochrona i ponowne zablokowanie

Blokada dotyczy wykonywania własnych ataków na graczy, nie jest zgodą obu stron ani nietykalnością. Przeciwnik nie musi mieć odblokowanej własnej blokady, aby stać się celem uprawnionej agresji. Obie postacie muszą żyć, mieć co najmniej 8. poziom, być na tym samym piętrze i poza bezpieczną osadą. Nie wolno atakować samego siebie ani członka drużyny. Zaklęcia respektują własny zasięg, geometrię i linię widzenia; serwer nie ufa kosztom ani obrażeniom przysłanym przez klienta.

Obszary i pola sprawdzają każdego gracza oddzielnie; chronieni gracze są pomijani, a potwory nadal mogą otrzymać obrażenia. Po odblokowaniu PvP przypadkowa osoba w dozwolonym obszarze może zostać trafiona nawet przy zaznaczonym potworze. Agresja podlega tym samym zasadom czaszek i kar co broń. Nawet odparty ofensywny czar jest próbą agresji. Skuteczne unieruchomienie lub przyciągnięcie nie omija przypisania udziału w śmierci.

Ponowne włączenie blokady natychmiast zatrzymuje autoatak gracza, oczekujący czar skierowany w gracza i własne szkodliwe statusy na postaciach. Pola i wilk sprawdzają blokadę przed każdym kolejnym działaniem, więc nie zadają dalszych obrażeń PvP. Pole może nadal działać na potwory; ponowne odblokowanie może przywrócić jego szkodliwe działanie na uprawnionych graczy. Zablokowanie nie zeruje czasu walki, czaszki, prawa obrony ani kar. Kontrole dotyczą także zmiany drużyny, piętra, ochrony początkującego i strefy bezpiecznej. Wilk nie może atakować z bezpiecznej strefy ani wejść do niej podczas aktywnej walki PvP.

## Wsparcie drużyny podczas PvP

Poza PvP członków drużyny można leczyć i wzmacniać bez wyłączania blokady. W trakcie PvP rzucający wspierający czar na inną postać musi wyłączyć własną blokadę. Rzucający i odbiorca muszą mieć przynajmniej 8. poziom i znajdować się poza strefą bezpieczną. Wsparcie włącza rzucającego do walki i daje aktywnym przeciwnikom prawo obrony przed nim. Wsparcie postaci oznaczonej czaszką może nadać białą czaszkę wspierającemu. Nie można bezkarnie wspierać walki z osady ani niskopoziomowym kontem.

Własne leczenie pozostaje dozwolone przy włączonej blokadzie, także podczas obrony przed atakiem. Nie usuwa czasu walki ani oznaczeń. Koncentracja na pozytywnym czarze należy do rzucającego, a nie do leczonego/wzmacnianego sojusznika; porażka rzucającego w obronie koncentracji kończy odpowiedni efekt u odbiorcy.

## Zakres wersji

Nie zmieniono progów poziomów, kosztów many ani katalogu czarów z 0.8.0. Nie dodano pełnego stołowego systemu D&D ani nowych klas. Interfejs nie otrzymał nowego trybu ręcznego zaznaczania cudzych towarzyszy; zmiana obejmuje działanie istniejącego wilka przeciw wybranemu graczowi. Nie przeprowadzono długiego testu balansu PvP ani testu na fizycznym urządzeniu. Dokładny zakres weryfikacji: `TEST_REPORT.md`.
