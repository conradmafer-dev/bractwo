> Aktualizacja łowcy w 0.8.12: patrz CHANGELOG_0.8.12.md i PROTOCOL_0.8.12.md. Starsze progi łowcy i koszt Znaku poniżej zastępują nowe zasady.

> Aktualizacja 0.8.11: dodatkowe metadane rozwoju klas i atlas — zobacz `PROTOCOL_0.8.11.md`. Starsze sekcje poniżej opisują bazowy protokół.

# Uzupełnienie protokołu 0.8–0.8.7

Bazowy handshake, ruch, konta i świat: `archive_0.7/PROTOCOL.md`. Źródłem prawdy jest obsługa pakietów w `server/server.py` i `server/dnd_game.py`. Przykłady:

```json
{"type":"ranking"}
{"type":"select_target","enemy_id":"enemy-id"}
{"type":"select_target","target_id":"player-id"}
{"type":"select_target"}
{"type":"auto_pause","paused":true}
{"type":"hotbar","slot":0,"spell_id":"fire_bolt"}
{"type":"pvp_safety","enabled":false}
{"type":"cast","spell_id":"fire_bolt","enemy_id":"enemy-id"}
{"type":"cast","spell_id":"magic_missile","target_id":"player-id"}
{"type":"ability","target_id":"player-id"}
{"type":"cast","spell_id":"healing_word","target_id":"party-player-id"}
{"type":"cast","spell_id":"healing_word"}
{"type":"cast","spell_id":"protection_from_energy","target_id":"party-player-id"}
{"type":"pvp_safety","enabled":true}
```

`enabled:false` wyłącza blokadę atakowania graczy; nie wyłącza ochrony osad, drużyny i niskich poziomów. Nie oznacza nietykalności odbiorcy z `enabled:true`. Nie wolno podawać jednocześnie `enemy_id` i `target_id`. Ofensywny pakiet z konkretnym nieprawidłowym graczem nie zastępuje go automatycznie innym potworem. Brak celu może użyć aktualnego wybranego celu ofensywnego; bez wybranego gracza nie wyszukuje samoczynnie graczy do ataku. Walidacja jest ponawiana przy wykonaniu zakolejkowanego czaru oraz każdym impulsie pola lub ataku wilka.

Pozytywny czar z `target_id` wymaga członka drużyny, jeżeli nie jest skierowany w siebie. Brak `target_id` oznacza własną postać albo działanie drużynowe/osobiste według typu. Klient, mając wybranego wroga, nie przesyła jego ID z leczeniem lub buffem. `ability` wybiera `favorite_spell` właściciela na podstawie historii skutecznych użyć (lub domyślną zdolność klasy przy pustej historii) i stosuje reguły odbiorców wybranego czaru. `shield`, `second_wind`, `shillelagh`, formy, teleport i towarzysz pozostają osobiste.

Katalog `spells` udostępnia dla każdego wpisu `targeting`: `hostile`, `ally`, `party` lub `self`, oraz `pvp:true` (integracja zasad wpisu z walką graczy, nie dowolna zmiana odbiorcy). Pole `abilities.offense` metadanych: `PvE_and_unlocked_PvP`. To informacja interfejsu, nie uprawnienie zastępujące kontrole serwera.

Sloty mają indeksy 0…`len(hotbar)-1`; klient wyświetla strony po 24 w dwóch rzędach po 12. `hotbar_page_size` = 24; `hotbar_row_size` = 12. Wszystkie odblokowane czary muszą być na pasku; pusty wpis jest ponownie uzupełniany przy normalizacji. Przypisanie czaru z innego slotu zamienia oba wpisy miejscami. Zablokowane czary i obce klasy są odrzucane. Każda klasa zaczyna od 24 slotów; czarodziej ma na starcie 9 wpisów, druid 8. Numer strony jest stanem lokalnego klienta; pakiet `hotbar` podaje indeks globalny. Ranking działa przed logowaniem również przez HTTP GET `/ranking`; zwraca 20 publicznych wyników bez danych konta. Pasek w prywatnym stanie właściciela: `hotbar`; pozostałe pola: `attributes`, `proficiency`, `spell_circle`, `damage_dice`, `attacks_per_round`, `bonus_remaining`, `shield_armed`, `concentration`, `statuses`, `form`, `temp_hp`, `queued_spell`, `auto_enabled`. Stan świata zawiera `companions`.

Wartości obrażeń klienta są ignorowane. Koszt, gotowość, rzut, stan celu i kary wynikają z serwera. Po utracie aktywności okna klient wysyła `auto_pause`; po powrocie wznawia wyłącznie istniejący wybór. Publiczne pola innych postaci nie ujawniają prywatnego ekwipunku. Aktualizuj serwer i oba rodzaje klienta razem; schemat bazy 0.8 nie zmienia się.

## Pola 0.8.4

`mana_budget`: `slots` (liczebność od I kręgu), `base`, `bonus`, `costs` (indeksy 0–9), `shared:true`. `mana_recovery_remaining` pokazuje pozostałą przerwę po zapłacie; warunkiem regeneracji jest także brak walki. W zapisie są `mana_rules_version:1` i absolutne `mana_recovery_until`; migracja stosuje procent starej puli tylko raz.

`status_effects` występuje w prywatnym i publicznym stanie graczy oraz w stanie potworów. Wpisy zawierają `id`, `name`, `icon`, `description`, `harmful`, `remaining` (sekundy lub null), `rounds` (liczba pozostałych rund lub null); efekty czarów dodatkowo `spell_id` i `concentration`. Pola wewnętrzne owner/dc/retry nie są wysyłane. `shield_ready`, `concentration`, `wild_shape`, `temp_hp` to wirtualne statusy interfejsu. Stare `statuses` pozostaje dla zgodności.

Katalog świata zawiera `status_catalog` oraz poprawione progi w `spells`, `milestones` i `combat_rules`. Efekty wygasają autorytatywnie na serwerze. Zmieniaj serwer i klienta razem.


## Pola i grafika 0.8.5

Prywatny stan właściciela zawiera `character_sheet` z wyliczonymi cechami/obronami, atakiem czarami, typem obrażeń, odpornościami, szybkością i pustym `feats`, oraz `favorite_spell`, `hotbar_page_size:24`, `hotbar_row_size:12`. Publiczne dane innych graczy nie zawierają karty, ekwipunku ani historii. `spell_history` jest zapisywaną listą ostatnich 100 kluczy; nie jest wymagane jej przesyłanie klientowi. Skrót F wysyła dotychczasowy pakiet `ability`; serwer, nie klient, rozstrzyga najczęściej używany czar.

Każdy wpis katalogu czarów ma `id`, `shape`, `visual` (styl, motyw, kolory, liczba pocisków), `icon` i `effect:'spell'`. Zdarzenie graficzne `kind:'spell'` zawiera `spell_id`, profil `visual`, `shots`, rzeczywistych `targets` i `area`. Geometria `area` ma `shape`, `origin`, `center`, `direction`, `length`, `width`, `radius`, `polygons`, `circles`, `bounds`; pozycje są w jednostkach świata. Klient nie przelicza osobno szerokości stożka ani nie zgaduje obszaru po nazwie.

Długotrwałe efekty mają `persistent:true` i identyfikator. Stan zawiera `active_field_effects` — aktywne ID pól; klient usuwa nieaktywne lub zakończone efekty. Szkody, odbiorcy i rzuty pozostają wyłącznie po stronie serwera. Warstwa dekoracyjna może sięgać poza granicę trafienia. Dotychczasowe zdarzenia ataków potworów i innych efektów korzystają ze starego renderera jako fallback.

Nowe statyczne zasoby WWW: `/spell_vfx.js`, `/character_sheet.js`, `/character_sheet.css`, `/assets/spells/*.svg`, `/assets/equipment/*.svg`. Kontrolki karty i banków są stanem klienta, a globalne indeksy paska i historia zapisują się na serwerze.

## 0.8.6 — trwałe podsumowania awansów

Wyłącznie stan właściciela zawiera `pending_level_ups` (lista podsumowań) oraz `level_up_pending_count` (liczba wszystkich niepotwierdzonych poziomów). Element: `id`, `level`, `rows`, `actions`. Wiersz: `id`, `label`, `gain`, opcjonalnie `unit`, `icon`. `gain` jest gotowym przyrostem (np. `+1`, `+1k10`, `+ Nowy czar`), nigdy wartością sprzed awansu lub końcową sumą. Dane liczy serwer z niezmiennego kontekstu chwili awansu, bez chwilowych buffów.

Potwierdzenie jednego podsumowania: `{"type":"dismiss_level_up","id":"<identyfikator podsumowania>"}`. Serwer usuwa tylko to podsumowanie z historii zalogowanej postaci i zapisuje bazę. Nie wydaje przy tym punktów. ID obce, nieistniejące lub błędnego typu nie zmienia historii. Potwierdzenie jest dozwolone także w walce/po śmierci; to operacja UI.

Kolejka przechowuje zakresy poziomów i materializuje maksymalnie 32 ostatnie podsumowania do widoku. Pozostałe są nadal niezamknięte i uzupełniają zwolnione miejsca. Stan kompaktowy pomija niezmienione `pending_level_ups`; klient scala je jak inne prywatne kolekcje. Pusta lista zastępuje poprzednią listę po ostatnim potwierdzeniu.

Akcja `{"kind":"mastery","label":"Przydziel punkt","tab":"stats"}` otwiera statystyki. Klient przydziela rzeczywisty punkt dotychczasową komendą `{"type":"mastery","branch":"vitality"}` (także `power`, `focus`). Serwer utrzymuje limity i blokadę walki, ale sam przydział nie wymaga NPC. Reset i promocja nadal wymagają NPC. Klienci obsługują `tab:"feats"` dla przyszłych prawdziwych wyborów; serwer tej wersji nie przyznaje atutów.

## 0.8.7 — opłacony krąg i skalowanie

`{"type":"spell_power","spell_id":"magic_missile","circle":1}` wybiera krąg I; `circle:0` przywraca Auto. Serwer dopuszcza wyłącznie odblokowane, rzeczywiście skalowalne czary właściwej klasy i użyteczne kręgi. `circle` musi być liczbą całkowitą, nie tekstem ani wartością logiczną. Preferencje są zapisywane jako `spell_circle_choices`; właściciel jest ustalany na podstawie zalogowanego połączenia, nie ID podanego przez klienta.

Prywatny stan właściciela zawiera `spell_profiles`: mapę kluczy czarów na obliczone nadpisania katalogu świata. Dostępne pola: `cast_circle`, `power_choice`, `power_options`, `mana`, `dice`, `extra_dice`, `weapon_dice`, `flat_heal`, `shots`, `max_targets`, `ally_targets`, `duration`, `duration_rounds`, `power_summary`, `next_upgrade`, opcjonalnie `recast_active`. Klient łączy je z bazowym `spells[id]`; nigdy nie modyfikuje wspólnego katalogu. Stan kompaktowy pomija niezmieniony obiekt; otrzymany nowy/pusty obiekt zastępuje cały wcześniejszy zestaw. Przy zmianie konta poprzedni profil nie może być zachowany. Profile innych graczy nie są publikowane.

`cast` i `ability` nie przyjmują obrażeń ani dowolnego kręgu z klienta. Używają ostatniej prawidłowej preferencji właściciela, a krąg, koszty, zasięgi, gotowość i PvP są ponownie walidowane w momencie wykonania. Zmiana preferencji podczas oczekiwania dotyczy późniejszego wykonania; wybrana moc musi być wtedy opłacona. Aktywne pole i powtarzany czar utrzymują swój opłacony profil, nie najnowszy profil właściciela.

`{"type":"stop_concentration"}` dobrowolnie przerywa własną koncentrację, usuwa zależne od niej pola/statusy przez istniejącą ścieżkę i czyści zakolejkowany czar; nie zeruje odnowienia akcji ani zobowiązań PvP. Pole `concentration_profile` to wewnętrzny stan sesji, niezapisywany do bazy. Efekty graficzne czarów mają rzeczywiste `shots` oraz `cast_circle`; liczba łuków animacji zgadza się z liczbą pocisków profilu.

Nowe zakresy `level_up_batches` mają `spell_scaling_version:1`. Stare zakresy bez tej flagi zachowują stare podsumowania. Wiersze w protokole podsumowań nadal używają jedynie `label`, `gain`, `unit`, `icon`; klient nie oblicza przyrostu lokalnie. Przyrost opisuje nową maksymalnie dostępną moc, nie wymusza zmiany ręcznej preferencji rzucania.


## 0.8.8 — łupy i grafiki

Metadane `enemy_types[*].loot.entries` zawierają `kind` (`item`/`potion`), `template` i bezwarunkową `chance` w 0..1. Te same wpisy są losowane na serwerze. Katalog `items[*]` ma `icon`, `armor_summary`, `sources` (`kind`,`name`,`chance`), nowe bronie także `weapon_dice`, a pancerze/pierścienie opcjonalne `resistances`. Wartości źródeł odświeżają się z kanonicznego katalogu przy logowaniu. `loot_hunts` zawiera dziewięć nowych znaczników łowisk.

Nowe gatunki mają `sprite` (lokalny atlas PNG), rozmiary klatki 80×80 i `sprite_frames=4`. Nie ma nowej komendy klienta rozdającej łupy; podgląd jest wyłącznie odczytem. `equip`, `sell` i pozostałe dotychczasowe komendy weryfikuje serwer.


## Inventory protocol additions — 0.8.10

`{"type":"potion_bind","slot":"q","item":"mana_potion_2"}` assigns an owned variant to q/r. An empty item clears the binding. `{"type":"potion","slot":"q"}` consumes one unit of that exact bound template; no automatic strongest/cheapest fallback. Historical `item`-based potion requests remain supported only against real owned stacks.

`{"type":"sell","uid":"<uid>","quantity":1}` sells validated integer quantities (default 1). Whole-stack sale sends its actual quantity. `buy` still uses the canonical template. Server enforces range, combat, life state, capacity, ownership, gold and level checks. Merchant rest uses existing `interact`; there is no new `rest` opcode.

Private player state adds `potion_slots`, `known_loot` and potion `quantity` on inventory instances. `potions` is a compatibility count mirror, not separate storage. Item `sources` contains only the owner's personally received drops. Global metadata strips item sources and replaces enemy loot tables with discovered-only flags. Journal discoveries are saved per character but not exposed in other players' public snapshots.

Persistent additions: `inventory_rules_version`, `potion_slots`, `loot_discoveries`. Migration converts old supplies exactly once without throwing away overflow. Canonical quest gear stats refresh while retaining UIDs. No backward migration is implemented: restore a pre-upgrade database to downgrade.
