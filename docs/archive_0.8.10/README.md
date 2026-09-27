# Bractwo 0.8.10 — okna, ekwipunek i mikstury

Aktualizacja pełnych źródeł 0.8.9. Nie wymaga resetu postaci. Zmienia układ i obsługę interfejsu, przenosi zapasy mikstur do plecaka, zapisuje poznane źródła łupu i poprawia zachowanie potworów oraz broń z zadań.

## Przesuwanie okien i widoczność paneli

Przeciągnij nagłówek okna lub uchwyt **⋮⋮** na panelu. Dotyczy karty postaci, dziennika, kupca, pomocy, podglądów, poszczególnych awansów oraz elementów HUD-u: regionu, celu/PvP, zadania, mapy, pasków czarów, mikstur, czatu i statusów. Pozycje klienta WWW zapisują się osobno dla postaci i orientacji ekranu na tym urządzeniu. Przeciągnięte elementy można celowo nałożyć na siebie; układ domyślny nie wymusza tych kolizji.

**Panele** i przycisk **↺** są nad informacją o regionie. Pierwszy pokazuje ustawienia widoczności; drugi przywraca domyślne położenia i włącza panele. Ukrycie awansów nie kasuje ich zapisanej historii. Przyciski na dole są wyrównane, mikstury pozostają pomiędzy czatem i paskami. Statusy nadal nie mają wspólnego tła.

Cel, PvP i zadanie zajmują oddzielne miejsca w lewej kolumnie. Na komputerze kaskada awansów jest obok niej. Na wąskim ekranie pionowym lewa kolumna przewija się, aby udostępnić wszystkie sekcje i przyciski zamykania bez zasłaniania dolnych pasków. Każdy awans nadal zamyka się osobno.

## Przedmioty, handel i poznane łupy

Najechanie lub ustawienie fokusu na przedmiocie pokazuje jego statystyki. Kliknięcie założonej broni, pancerza lub pierścienia otwiera podgląd bez zdejmowania. Opis, wymagania i akcje są rozdzielone; **Załóż / Zdejmij / Sprzedaj** znajdują się w osobnym dolnym wierszu.

Kupiec ma zakładki **Kupuj / Sprzedaj**. Sprzedaż nie obejmuje założonego sprzętu. Można sprzedać jedną miksturę albo cały stos. Serwer sprawdza rzeczywiste posiadanie przedmiotu, ilość, złoto, odległość od kupca i blokadę walki.

**Skąd zdobyć** pokazuje tylko te źródła, z których ta postać naprawdę otrzymała dany przedmiot. Samo zobaczenie lub zabicie potwora nie wystarcza. Zakup, nagroda zadania i łup utracony przez brak miejsca nie odkrywają źródła. Dotyczy to też okna łupów zaznaczonego potwora. Starsze zapisy nie przechowywały tej historii: nie odtwarzamy jej przez zgadywanie; odkrywanie zaczyna się od nowych zdobyczy.

## Mikstury są przedmiotami

Osiem odmian ma własne ikony, opis siły, wartość i ilość w plecaku. Jeden stos mieści do **99 sztuk**. W podglądzie wybierz **Przypisz Q** albo **Przypisz R**. Skrót używa dokładnie tej odmiany — nie przełącza się automatycznie na mocniejszą ani inną po wyczerpaniu zapasu. Oba skróty mogą wskazywać mikstury zdrowia lub many.

| Odmiana | Zdrowie | Mana | Wymagany poziom |
|---|---|---|---:|
| Mała | 2k4+2 HP | 18 | 1 |
| Większa | 4k4+4 HP | 35 | 20 |
| Potężna | 8k4+8 HP | 60 | 50 |
| Najwyższa | 10k4+20 HP | 100 | 80 |

Zachowano wspólne odnowienie 3 sekund i dotychczasowe siły mikstur. Nie zużywa się mikstury, gdy dany zasób jest pełny. Stare zapasy przenoszą się jednorazowo do rzeczywistych stosów. Pełny stary plecak nie powoduje utraty mikstur podczas tej migracji — może chwilowo przekroczyć limit, dopóki nie zrobisz miejsca.

## Lepsze nagrody i powrót potworów

Drugi zestaw broni każdej klasy (nagrody strażnika) ma teraz **+1 do trafienia i obrażeń**, trzeci **+2**. Różdżki zamiast podnoszenia obrażeń Iskry dają odpowiednio +1/+2 do trafienia i ST czarów. Poszczególne wersje nie stają się już identyczne podczas przeliczania starych statystyk. Posiadane egzemplarze są aktualizowane przy wczytaniu, z zachowaniem identyfikatorów i założonego sprzętu.

Po zgubieniu gracza potwór przez **24 sekundy** pozostaje w okolicy i lokalnie wędruje. Potem wraca pieszo w stronę swojego miejsca odrodzenia, korzystając z zapamiętanej trasy. Powrót działa także poza ekranem graczy. Nie ma teleportu, nietykalności, resetu zdrowia ani gotowości ataku. Ponowne wykrycie lub zaatakowanie przerywa powrót; następne zgubienie celu rozpoczyna nowe odliczanie. Zachowano zwykłą regenerację poza walką: 0,25 HP/s po 12 sekundach, bez przyspieszonego leczenia przy odwrocie.

## Instalacja i aktualizacja

Zatrzymaj serwer i zabezpiecz bazę przed podmianą. Zaktualizuj **serwer oraz cały katalog web razem**, łącznie z `inventory_ui.js`, `windows.js`, `windows.css` i ikonami mikstur. Nowy serwer udostępnia nowe pliki przez HTTP. Po uruchomieniu odśwież przeglądarkę Ctrl+F5.

Na istniejącym Railway zachowaj tę samą usługę, wolumen i ścieżkę bazy (dla przygotowanej konfiguracji `/data/world.sqlite3`). Paczka Railway ma pliki bezpośrednio w katalogu głównym ZIP-a. Pełna paczka ma katalog `Bractwo_0.8.10/` i dodatkowo źródła Godota. Nie wysyłaj bazy ani samego ZIP-a do repozytorium. `/health` powinno pokazywać `0.8.10`.

Migracja zapisuje nowe pola. **Nie uruchamiaj starszego serwera na już zmigrowanej bazie**; do cofnięcia aktualizacji użyj również kopii bazy wykonanej przed aktualizacją. Nowe konto nie jest potrzebne.

Lokalnie na Windows uruchom `start_windows.bat`, a następnie `http://127.0.0.1:8080`. Nie otwieraj samego `web/index.html` z dysku, jeśli zależy Ci na sprawdzaniu kompletu plików serwowanych przez aktualny serwer. Alternatywnie:

```sh
python -m pip install -r requirements.txt
python run.py
```

Projekt natywny: `client/project.godot`. Konfiguracja istniejącego hostingu: `docs/RAILWAY.md` i `RAILWAY_VARIABLES.txt`.

## Sprawdzenie

**545 testów Python, 52 testy JavaScript, 19 sprawdzeń Chromium i 15 sprawdzeń lokalnego procesu/HTTP/WebSocket/restartu — wszystkie zakończone powodzeniem.** Raport, logi i zrzuty: `docs/TEST_REPORT.md`, `docs/qa_0.8.10/`.

Chromium uruchamiał rzeczywisty klient i serwer przez kontrolowany most WebSocket Python. To nie był fizyczny telefon ani serwer produkcyjny. Źródła Godota są zmienione, ale silnika, importu, kompilacji ani eksportu nie uruchamiano. Nie budowano obrazu Docker i nie wdrażano nic na koncie Railway. Paczki nie zawierają APK/AAB/EXE.

Atrybucja zasad: `LICENSE-SRD.txt`. Pełne developerskie tabele lootu pozostają w `docs/LOOT_0.8.8.md`; nie są automatycznie ujawniane postaciom w grze.
