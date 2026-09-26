# 0.8.15 — Odzyskanie mocy

Komenda pozostaje `{"type":"cast","spell_id":"arcane_recovery"}`. Serwer wylicza ilość many; klient nie dostarcza własnej wartości. Odbiorcą jest wyłącznie rzucający, niezależnie od zaznaczenia.

Profil: `kind=recovery`, `feature=true`, `action=bonus`, `mana=0`, `cooldown=180`, bez channel_seconds i bez ritual. `restore_mana` nadal pochodzi z niezmienionej funkcji `caster_rules.recovery_amount`. Klient używa `bonus_remaining`, `spell_cooldowns.arcane_recovery`, alive/form/channel oraz mana/max_mana do wyświetlania gotowości. Nie sprawdza combat_remaining ani action_remaining jako blokady tej zdolności.

Serwer sprawdza klasę/poziom, życie, połączenie, formę, trwający rytuał, odnowienie, akcję dodatkową oraz brakującą manę. Udane użycie atomowo odnawia manę, ustawia bonus_cooldown_until i 180-sekundowy spell_cooldowns, rejestruje jedno faktyczne użycie oraz zapisuje gracza przed wysłaniem komunikatu. Nie zmienia attack_cooldown_until, dx/dy/input_time, celów, pending_spell, koncentracji, opóźnienia regeneracji, reakcji ani mikstur. Zdolność nie jest zaklęciem: brak wyszkolenia w pancerzu nie blokuje samego Odzyskania mocy (jak w 0.8.14).

Próba przy pełnej manie lub podczas odnowienia nie zużywa akcji i nie dopisuje historii. Zdolność nie jest kanałem, więc channel_cancel ani komenda ritual nie pozwalają ominąć jej odnowienia. Rytuały nadal używają starego kanału poza walką; ich zasoby pobiera ukończenie kanału.

Format zapisu i caster_rules_version bez zmiany. Istniejące odnowienie z 0.8.14 jest respektowane. Pozostały protokół opisuje PROTOCOL_0.8.14.md. Ta zmiana jest własną adaptacją Bractwa, nie nowym odtworzeniem reguł odpoczynków D&D.
