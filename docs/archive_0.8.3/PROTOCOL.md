# Uzupełnienie protokołu 0.8 / 0.8.1

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

Pozytywny czar z `target_id` wymaga członka drużyny, jeżeli nie jest skierowany w siebie. Brak `target_id` oznacza własną postać albo działanie drużynowe/osobiste według typu. Klient, mając wybranego wroga, nie przesyła jego ID z leczeniem lub buffem. `ability` korzysta z identycznego kierowania celami jak czar domyślny klasy. `shield`, `second_wind`, `shillelagh`, formy, teleport i towarzysz pozostają osobiste.

Katalog `spells` udostępnia dla każdego wpisu `targeting`: `hostile`, `ally`, `party` lub `self`, oraz `pvp:true` (integracja zasad wpisu z walką graczy, nie dowolna zmiana odbiorcy). Pole `abilities.offense` metadanych: `PvE_and_unlocked_PvP`. To informacja interfejsu, nie uprawnienie zastępujące kontrole serwera.

Sloty mają indeksy 0…7; pusty `spell_id` czyści slot. Ranking działa przed logowaniem również przez HTTP GET `/ranking`; zwraca 20 publicznych wyników bez danych konta. Pasek w prywatnym stanie właściciela: `hotbar`; pozostałe pola: `attributes`, `proficiency`, `spell_circle`, `damage_dice`, `attacks_per_round`, `bonus_remaining`, `shield_armed`, `concentration`, `statuses`, `form`, `temp_hp`, `queued_spell`, `auto_enabled`. Stan świata zawiera `companions`.

Wartości obrażeń klienta są ignorowane. Koszt, gotowość, rzut, stan celu i kary wynikają z serwera. Po utracie aktywności okna klient wysyła `auto_pause`; po powrocie wznawia wyłącznie istniejący wybór. Publiczne pola innych postaci nie ujawniają prywatnego ekwipunku. Aktualizuj serwer i oba rodzaje klienta razem; schemat bazy 0.8 nie zmienia się.
