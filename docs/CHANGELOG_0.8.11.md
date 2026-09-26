# 0.8.11 — ruch, okna, rozwój i atlas

## Poprawione
- Usunięcie celu po śmierci nie wywołuje resetu klawiszy ani joysticka.
- Wybór celu gracza nie kasuje ruchu. Ręczne X celu również go nie kasuje.
- Zwykłe okna i ich przeciąganie nie wyłączają ruchu; keyup obsługiwany w fazie capture. Blokada przy pisaniu, utracie aktywności i śmierci pozostaje.
- E przełącza otwarte okno świata/usług i zamyka kupca. Otwarcie książki nie jest już blokadą dla tej samej komendy.
- Przy zamykaniu podglądów fokus nie wraca do niewidocznego pola wejściowego.
- Księga świata i pomoc są nad zwykłymi panelami HUD także w widoku pionowym.
- Rozwój odczytuje autorytatywną ścieżkę danej klasy, a nie przestarzałe wspólne milestones.
- Liczniki treningu nie udają premii D&D. Opis mistrzostwa i warunki przydziału są zgodne z obecnym kodem, bez zmiany efektów.
- Atlas ma kamerę 1–64×: klik lewy/prawy, kółko, przesuwanie, przyciski zoomu, okolica i cały świat. Osobna komenda wskazuje cel bez zamykania.
- Ruch i kolejne snapshoty nie zerują kamery atlasu. Zamykanie/otwieranie w tej samej sesji zachowuje widok.
- Starterowa rzeka i jej most rysowane z `world.river`; późniejsze z `waterways` i `bridges`. Wszystkie mosty rysowane po wodzie.
- Segmenty rzek poza widocznym fragmentem nie wydają poleceń rysowania; atlas buforuje warstwę terenu podczas ruchu postaci.

## Bez zmian balansu i zapisów
- Cure Wounds / Leczenie ran: +2k8 za wyższy krąg; Healing Word / Uzdrawiające słowo: +2k4. Zgodne z używanym SRD 5.2.1 / zasadami 2024.
- Kręgi, mana, koszty, czasy czarów, HP, przedmioty i łupy bez zmiany.
- Zachowane wszystkie funkcje 0.8.10. Brak nowej migracji danych względem 0.8.10.
- Pełny serwer/WWW oraz odpowiadające źródła Godota. Godot nie uruchamiany w silniku; brak eksportów binarnych.
