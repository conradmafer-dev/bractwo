# Bractwo Krain 0.8.18 · UI_32 — wydarzenia w świecie

## Co zmienia aktualizacja

Osiemnaście punktów oznaczonych złotą kostką k20 zastępuje osiem odrębnych scen.
Na placu startowym nie ma już skupiska kostek. Sześć zdarzeń rozłożono w okolicy
Przystani, młyna, przeprawy, obozu i ruin. Dwa dalsze spotkania czekają w Zielonej
Dolinie i przy Brzezinie. Między najbliższymi scenami jest ponad pięć pól.
Nazwy pojawiają się dopiero po podejściu; ukończenia nie zastępują scen wielkimi
znacznikami ani zielonymi kostkami.

| Wydarzenie | Co widać | Możliwe działania i rezultat |
| --- | --- | --- |
| Ranny strażnik | Siedzący strażnik pod wierzbą na zachodnim brzegu rzeki, tarcza i złamana włócznia. | Opatrzenie rany, oddanie małej mikstury zdrowia lub rzucenie Leczenia ran z okna wydarzenia. Po pomocy strażnik stoi i dziękuje. |
| Zablokowany wóz młynarza | Przechylony wóz, worki mąki, zaklinowana belka i woźnica. | Podważenie wozu, uwolnienie belki lub rozpoznanie usterki. Po pomocy wóz stoi prosto, a belka leży obok. |
| Podejrzany poborca | Zatrzymana podróżna i obcy z dokumentem na północnym trakcie. | Zastraszenie, wypytanie o rozkazy lub przekonanie do odejścia. Poborca odchodzi i znika, podróżna pozostaje. |
| Sakwa przy przeprawie | Kamienie, trzciny, ślady i częściowo ukryta sakwa po wschodniej stronie rzeki. | Wypatrzenie lub przeszukanie miejsca. Zabrana sakwa znika ze sceny. |
| Skradzione zapasy | Skrzynie, płachta, zwalony pień, sznur i drzemiący goblin. | Skradanie, podstęp lub zręczne przejście po pniu. Po odzyskaniu zapasów skrzynie pozostają otwarte. |
| Zapomniany relikwiarz | Kamienna skrzynia wśród pękniętych kolumn. | Rozpoznanie run, królewskich znaków lub obrządku. Po sukcesie pokrywa pozostaje otwarta. |
| Zielarka z doliny | Siedząca zielarka, rośliny, koszyk i fiolki. | Rozpoznanie ziół lub odnalezienie rozwianej wiązki. Pojawiają się przygotowane lekarstwa. Spotkanie od poziomu 10. |
| Spłoszony kuc | Poruszający łbem kuc z uprzężą, karawaniarz i toboły. | Uspokojenie zwierzęcia albo spokojna melodia. Kuc przestaje się płoszyć i opuszcza głowę. Spotkanie od poziomu 10. |

Sceny rysuje klient gry w tym samym stylu co otoczenie. Nie wymagają pobierania
nowych bibliotek ani osobnych skryptów graficznych.

## Korzystanie w grze

Podejdź do sceny i naciśnij **E**, **Rozmawiaj** lub **Zbadaj**. Na komputerze
można również kliknąć pobliską scenę. Otwiera się krótka rozmowa z dostępnymi
czynnościami. Samo obejrzenie sceny, otwarcie opisu ani zamknięcie okna nie
uruchamia próby i niczego nie zużywa. **E**, **Esc** i przycisk zamknięcia pozwalają
odejść. Na wąskim ekranie treść okna przewija się pionowo.

Działania oparte na umiejętnościach wykonują rzeczywiste rzuty. Ich wyniki trafiają
do tego samego czytelnego panelu, który wprowadzono w FIX5, oraz do rozmowy.
Opisy nie zawierają przeliczników poziomów D&D na Bractwo.

Przy rannym strażniku oddanie mikstury zabiera jedną małą miksturę z plecaka,
a wybranie Leczenia ran zużywa manę i odnawia czar zgodnie z ustawionym kręgiem.
Przycisk jest niedostępny dla postaci, która nie zna czaru lub nie ma zasobów.
Nie leczy to równocześnie samego gracza. Leczenie strażnika wybiera się w oknie
wydarzenia; nie dodano ogólnego celowania czarami z paska w wszystkich NPC.

Po nieudanym teście kolejną próbę umiejętności można podjąć po 90 sekundach.
Zmiana umiejętności w tej samej scenie nie omija oczekiwania. Rannemu strażnikowi
można jednak pomóc miksturą lub czarem po zakończeniu bieżącej akcji.

## Percepcja i Czujny

Percepcja pozwala zauważyć krótki szczegół otoczenia z bliska i przy wolnej linii
widzenia. Czujny zwiększa tę szansę przez istniejącą premię do Percepcji. Nie
wykonuje automatycznie zadania i nie przyznaje nagrody. Wskazówka nie pojawia się
martwej ani oślepionej postaci. Zostaje również widoczna w otwartej rozmowie.

## Postacie i zapis

Każda postać rozwiązuje wydarzenia dla siebie. Ich ukończenia i wygląd po
rozwiązaniu są osobiste, nie stanowią wspólnego, globalnego zdarzenia zużywanego
przez pierwszego gracza. Zwykłe postacie niezależne, kupcy i potwory nie zostały
zastąpione ani usunięte.

Nagroda jest jednorazowa. Ponowne kliknięcie, druga metoda, ponowne logowanie
ani równoczesne żądania nie przyznają kolejnej nagrody. Postęp korzysta z
istniejącego zapisu postaci; nie wymaga resetu bazy.

Dawne osiemnaście identyfikatorów zadań jest nadal rozpoznawane. Część dawnych
punktów połączono w jeden nowy. Jeśli postać odebrała już nagrodę za którykolwiek
z tych punktów, powiązane wydarzenie pozostaje ukończone. Dzięki temu aktualizacja
nie uruchamia ponownie rozdawania nagród. Dawne teleportujące skróty z prób zostały
zastąpione lokalnymi wydarzeniami; nie przenoszą już postaci po rozwiązaniu.

## Zawartość paczki i wdrożenie

To **aktualizacja do istniejącego repozytorium UI_31 z galerią i komentarzami**, a
nie samodzielny pełny projekt. Zawiera komplet zmienianych plików poprzedniej
paczki FIX5, z naniesionymi zmianami UI_32. Zachowuje poprawkę Rozbijacza hord,
oba rzuty Zaciętego ataku, czytelne rozliczenia pozostałych rzutów, prosty opis
Twardego oraz udostępnienie plików wyboru atutów.

Nie podmienia `web/index.html`, galerii, poradników, komentarzy, ich arkuszy,
ustawień logowania, Dockerfile ani zapisów. `server/server.py` pochodzi z FIX5 i
zmienia oznaczenie interfejsu na UI_32. Sceny i okno znajdują się w już serwowanych
`skills_ui.js`, `game.js` i `hud_layout.css`, więc nie ma nowych adresów zasobów
do dopisywania w HTML lub serwerze.

Zrób kopię repozytorium, wypakuj ZIP i skopiuj zawartość `server` oraz `web` do
odpowiadających im folderów. Zastąp pliki o tych samych nazwach, ale **nie kasuj
całych katalogów**. Dodaj również testy i dokumentację. Zatwierdź wszystkie zmiany
razem i wyślij je na GitHuba. Po zakończeniu wdrożenia na Railway zamknij grę i
uruchom ją ponownie; w przeglądarce odśwież stronę z pominięciem pamięci podręcznej.

Nie dodawaj samego ZIP-a zamiast wypakowanej zawartości. Nie zmieniaj trwałego
wolumenu ani bazy SQLite. Aktualizacja nie została automatycznie wysłana na
GitHuba ani wdrożona na Railway.

## Sprawdzenia

Szczegóły, liczniki i ograniczenia są w `UI_32_RAPORT_TESTOW.json`.
Testy zdarzeń obejmują wszystkie metody umiejętności, koszt mikstury i czaru,
blokady stanów, odległość, widoczność, zapis, migrację każdego starego identyfikatora,
ponawianie żądań oraz osobne rozstrzygnięcia dwóch graczy.

Test przeglądarkowy uruchamia pełny klient i przekazuje prawdziwe pakiety do
lokalnego `Game.on_packet`, ale zastępuje Google testowym logowaniem i mostem
transportowym. Nie dotyka kont ani danych produkcyjnych. Nie jest testem
fizycznego telefonu ani nowego wdrożenia Railway.
