# 0.8.10 — zmiany względem 0.8.9

## Interfejs WWW

- Wspólne przeciąganie okien i paneli myszą/dotykiem, uchwyty z obsługą strzałek, ograniczenie do widocznego obszaru, zapis lokalny postaci/orientacji i reset.
- Sterowanie widocznością nad informacją o regionie. Niezależne sekcje region / cel i PvP / zadanie, kaskada obok, przewijana kolumna na wąskim ekranie.
- Wyrównany dół interfejsu; dokładne ikony i liczniki mikstur Q/R. Czytelność ikon podczas odnowienia.
- Wspólne podglądy przedmiotów po najechaniu/fokusie, wybór założonego przedmiotu bez zdejmowania, rozdzielone opisy i przyciski.
- Okno kupca z Kupuj/Sprzedaj, ceną jednostkową, zakupem mikstur, sprzedażą jednej sztuki/całego stosu i odpoczynkiem przez właściwą interakcję serwera.
- Osobiste poznane źródła w ekwipunku, depozycie i podglądzie łupu potwora; brak pełnych tabel w globalnych metadanych klienta.
- Osiem ikon mikstur współdzielonych z klientem natywnym.

## Serwer i zapisy

- `inventory_rules.py`: rejestracja mikstur jako przedmiotów, stosy do 99 sztuk, migracja dawnych liczników, wiązania Q/R, osobiste źródła łupu.
- Migracja idempotentna i bez utraty dawnych zapasów przy pełnym plecaku. Pole `potions` pozostaje tylko lustrzanym podsumowaniem rzeczywistego ekwipunku.
- Zakupy/nagrody mikstur sprawdzają miejsce na stosy przed zmianą złota/zadania. Walidacja ilości, wymaganych poziomów, własności, zasięgu i blokady walki.
- Broń z drugiego/trzeciego etapu dla wszystkich klas ma +1/+2. Różdżki poprawiają atak i ST czaru, nie bazowe obrażenia Iskry. Wczytanie zachowuje UID oraz aktualizuje kanoniczne parametry starych egzemplarzy.
- Odkrycie źródła tylko po rzeczywistym dostarczeniu łupu z konkretnego potwora. Brak zgadywanej historii sprzed migracji.
- Lokalne szukanie celu przez 24 s, potem powrót pieszo po zapamiętanej trasie. Praca poza ekranem, ponowne reagowanie na wrogów, brak teleportu/uzdrawiającego resetu/nietykalności.
- Nowe trasy HTTP `/inventory_ui.js`, `/windows.js`, `/windows.css`; wersja zdrowia serwera 0.8.10.

## Godot

Zmiany źródeł dla przesuwania okien, menu widoczności, podglądów, sklepu, stosów i przypisań Q/R. To aktualizacja źródeł, **bez uruchomienia lub kompilacji w silniku**. Nie stanowi wyniku testu natywnej aplikacji.

## Zgodność

Reset nie jest potrzebny. Wymagana wspólna aktualizacja serwera i klienta. Nowych zapisów po migracji nie należy otwierać starym serwerem; cofnięcie wymaga przedaktualizacyjnej kopii bazy. Zachowano świat, 57 gatunków potworów, tabele szans lootu, kręgi czarów, pasy umiejętności i wcześniejszą kaskadę awansów.
