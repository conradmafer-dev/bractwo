# Bractwo 0.8.2 — pościg i sztuczki

Baza: `BRACTWO_0.8.1_DND_PVP_PELNE_CZARY_FULL_SOURCE.zip`. Pełny serwer Python, WWW oraz źródła Godota. Nie wymaga nowej bazy ani resetu kont.

## Naprawa nadużywania odwrotu potworów

* Usunięto zależność pościgu od odległości gracza do spawnu. Zgubienie następuje według aktualnego dystansu do potwora, nie przekroczenia niewidzialnej granicy wokół domu.
* Po utracie celu potwór pozostaje dokładnie na bieżącej pozycji, bez powrotu i bez wznowienia starego patrolu. Może z tej pozycji ponownie wykryć gracza lub towarzysza. Początkowy patrol zachowano dla stworzeń, które jeszcze nie walczyły.
* Ostatnio widziana pozycja i 12-sekundowa pamięć zastępują odświeżającą się w nieskończoność pamięć napastnika przez ściany. Nie zmieniono lokalnego omijania przeszkód na pełne wyszukiwanie ścieżki.
* Usunięto przyspieszone leczenie odwrotu. Regeneracja 0,25 HP/s po 12 sekundach bez kontaktu bojowego; brak resetowania HP i odnowienia ataków na granicy pościgu.
* Koniec pościgu jest sprawdzany także po ucieczce gracza poza obszar symulacji, usunięciu jego postaci, śmierci lub zmianie piętra. Po utracie pierwszego celu inny prawidłowy cel może przejąć uwagę potwora.
* Zachowano ochronę osad i poprawiono spójność granicy ochrony (`<= radius`, jak w sprawdzaniu bezpieczeństwa postaci).
* Indeks świata śledzi aktualną pozycję potwora, także po przyciągnięciu/przesunięciu czarem. Przekroczenie komórki aktualizuje tylko właściwe koszyki zamiast przebudowywać indeks wszystkich 11 235 potworów.
* Poprawiono wyszukiwanie celu bossa przez dwie granice komórek (zasięg 1100, komórka 1024).
* Śmierć i lokalnie aktywowane odrodzenie nadal używają oryginalnego spawnu, z resetem stanów i początkowym patrolem. Potwór mający już 0 HP nie może wykonać ruchu ani sam się uleczyć przed rozliczeniem śmierci.

## Różdżka nie zastępuje sztuczki

* Podstawowy strzał czarodzieja: **Iskra różdżki — 1k4 ognia**, bez wzrostu liczby kości z poziomem. Jest własną regułą Bractwa, nie nazwanym czarem SRD.
* **Ognisty pocisk — 1k10 / 2k10 / 3k10 / 4k10** na poziomach 1/20/50/80. Pozostałe sztuczki zachowują swoje obrażenia, skalowanie, typy i efekty. Nie zwiększono ich obrażeń ponad dotychczasową implementację.
* Sztuczki nadal nie zużywają many. Zwykły strzał i główny czar dzielą akcję 3 s. Jeden czar zlecony z paska podczas odnowienia ma pierwszeństwo przed autoatakiem; nie ma dodatkowego strzału w tej samej akcji.
* Zwykłe i unikatowe różdżki zachowują premie do trafienia ataków czarami, ale nie wyświetlają pozornej premii do obrażeń iskry. Opisy, księga WWW/Godot i tooltip podstawowego ataku opisują różnicę.
* Identyczne kości i wspólny czas akcji w PvE oraz odblokowanym PvP. Nie zmieniono blokady, czaszek, wsparcia, koncentracji ani ochrony drużyny.

## Aktualizacja

Zatrzymaj stary serwer i wykonaj kopię `data/world.sqlite3`. Przenieś bazę do folderu `data` nowej paczki; podmień cały serwer i klienta. Na WWW odśwież stronę (w razie starego cache: Ctrl+F5). W Godocie importuj nowy `client/project.godot`. Statystyki przedmiotów są odczytywane z nowych szablonów; istniejące UID, konta, ekwipunek i zadania zostają. Położenia potworów, jak wcześniej, nie są zapisywane między restartami.

## Weryfikacja

224 testy Python (187 poprzednich + 37 nowych), 10 Node, 16 sprawdzeń Chromium z rzeczywistym serwerem przez kontrolowany transport. Szczegóły: `TEST_REPORT.md` i `qa_0.8.2/`. Godot nie został uruchomiony ani wyeksportowany; brak APK/AAB/EXE.
