# Uzupełnienie protokołu 0.8

Bazowy handshake, ruch, konta i świat: `archive_0.7/PROTOCOL.md`. Źródłem prawdy jest obsługa pakietów w server.py. Nowe pakiety:

```json
{"type":"ranking"}
{"type":"select_target","enemy_id":"enemy-id"}
{"type":"select_target","target_id":"player-id"}
{"type":"select_target"}
{"type":"auto_pause","paused":true}
{"type":"hotbar","slot":0,"spell_id":"fire_bolt"}
{"type":"cast","spell_id":"fire_bolt","enemy_id":"enemy-id"}
{"type":"cast","spell_id":"healing_word","target_id":"party-player-id"}
```

Sloty mają indeksy0…7; pusty `spell_id` czyści slot. Nie wolno podawać jednocześnie `enemy_id` i `target_id`. Ranking działa przed logowaniem także przez HTTP GET `/ranking`; zwraca20 publicznych wyników bez danych konta. Pasek w prywatnym stanie właściciela: `hotbar`; pozostałe pola: `attributes`, `proficiency`, `spell_circle`, `damage_dice`, `attacks_per_round`, `bonus_remaining`, `shield_armed`, `concentration`, `statuses`, `form`, `temp_hp`, `queued_spell`, `auto_enabled`. Stan świata zawiera `companions`.

Wartości obrażeń klienta są ignorowane. Po utracie focusu klient wysyła auto_pause, po powrocie wznawia tylko istniejący wybór. Przy rozłączeniu serwer nie wykonuje dalszych autoataków postaci. Publiczne pola innych postaci nadal nie ujawniają prywatnego ekwipunku.
