# 0.8.16 — wersjonowany wzrost many

## Zapis

`mana_rules_version=3` domyślnie dla nowych postaci. Migracja wersji 0/1/2 zachowuje
`mana / old_max_mana`, a następnie mnoży ten udział przez nową maksymalną pulę.
Obliczana jest raz, bez pośredniego podwójnego skalowania. Wersja 1 łowcy używa
jego historycznego maksimum przed wprowadzeniem magii na starcie. Zapis 3 nie jest
ponownie skalowany. Pozostałe cooldowny i zasoby nie są zmieniane.

## Migawka właściciela

`max_mana` jest autorytatywne, liczone z poziomu i wersji plus premia Skupienia.
W `mana_budget` dodano:

- `progression: "per_level"`
- `next_level_gain`: całkowity przyrost bazowy przy następnym poziomie, 0 po limicie
- `slots_are_reference: true`

`base`, `bonus`, `costs` i `shared` zachowano. `slots` to historyczna tabela
odniesienia dla danego efektywnego poziomu klasy, NIE odpowiednik aktualnego
interpolowanego maksimum i NIE liczniki dostępnych rzuceń. Klient dla per_level
opisuje base/bonus/next_level_gain, nie sumę slots.

`character_sheet.caster.recovery_amount` oraz
`spell_profiles.arcane_recovery.restore_mana` to ta sama wygładzona wartość.
`power_summary` i `next_upgrade` są liczone na serwerze; następny wzrost tej
zdolności jest wyszukiwany po pojedynczych poziomach. Komenda cast i koszt akcji
nie zmieniają się. Cooldown, bonus_remaining, PvP i koncentracja jak w 0.8.15.

## Podsumowania awansów

Nowy `level_up_batches[].context.mana_rules_version=3`. Brak tej wartości w
starym podsumowaniu oznacza historyczny skokowy wzrost. Nowe podsumowania nie
łączą się ze starymi batchami o innej wersji. Zmieniono tylko format jednostki
Odzyskania mocy na krótkie `many`, np. `Odzyskanie mocy +2 many`.
Nie dopisuje się awansów wstecz. Stare ID, zamykanie i limit kaskady są zachowane.

Wersje 0.8.15 i starsze powinny korzystać z kopii bazy sprzed migracji przy rollbacku.
Klienta i serwer należy aktualizować razem. Nie zmieniono formatu przedmiotów.
