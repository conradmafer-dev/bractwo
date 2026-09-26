# 0.8.17 — sterowanie fokusami i priorytet ręcznej magii

## Komendy

Nie dodano komend. `select_target` nadal utrzymuje wskazanie dla magii, ataków i
pomocników. Różdżka wykonuje podstawowy atak tylko po `attack`; `cast` i `ability`
korzystają ze starej autorytatywnej ścieżki walidacji i wspólnej głównej akcji.
`cast` z `action=bonus`, reakcje oraz Zryw zachowują dotychczasowe zasady.

Ponowne `select_target` z dokładnie tymi samymi identyfikatorami nie czyści
kolejki. Rzeczywista zmiana, wyczyszczenie, śmierć i utrata właściwego piętra celu
nadal usuwają wskazanie / polecenia zgodnie z wcześniejszymi zabezpieczeniami.

## Dane właściciela

`weapon_auto_attack: bool` — wynika z aktualnie założonej broni i formy, nie z
przesłanego przez klienta przełącznika. False dla fokusów arcane poza przemianą.
`auto_enabled` nadal oznacza zamiar obsługi wybranego celu. Do automatycznego
uderzenia bronią potrzebne są **oba** warunki oraz zwykłe kontrole walki.
Cel nadal jest dostępny dla pomocników także przy `weapon_auto_attack=false`.

`queued_spell` — istniejący identyfikator pojedynczej oczekującej komendy.
`action_remaining` — istniejący czas do głównej akcji. Klient tylko wyświetla
stan, nie skraca timera i nie ponawia automatycznie rzucenia za gracza.

W `combat_rules`: `focus_auto_attack: false`. Zachowano pozostałe dane.

## Priorytet

Symulacja realizuje kolejkę przed autoatakiem. Ręczny `attack` też nie może zużyć
gotowej głównej akcji, jeżeli istnieje ważny pending_spell. Zryw nie jest blokowany
tą kontrolą, bo jest odrębną dodatkową akcją z własnym odnowieniem.

Kolejka nie rezerwuje many ani nie wykonuje obrażeń przed czasem. Przy realizacji
sprawdzane są znowu wymagania, stan postaci, koszt, zasięg i PvP. Jej dotychczasowy
czas ważności 4 s pozostaje. Następny czar główny zastępuje poprzedni; nie powstaje
seria odroczonych rzutów. Udany natychmiastowy czar główny czyści stare polecenie,
ale akcje dodatkowe i reakcje nie kasują legalnie oczekującego czaru.

## Zapis i zgodność

Brak migracji bazy, `mana_rules_version=3`, `caster_rules_version=1` jak w 0.8.16.
`weapon_auto_attack` jest obliczany, nie zapisywany. Kolejka, zaznaczenie i
intencja autoataku nadal są stanem sesji. Klient i serwer należy podmienić razem.
