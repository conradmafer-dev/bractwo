# Protocol additions — 0.8.12

- World spells include `class_levels`, a mapping of allowed class IDs to actual minimum character levels. The clients use it instead of guessing Ranger gates from a universal formula. Longstrider uses ranger=5, druid/mage=1.
- Spell `ensnaring_strike` has kind `weapon_trigger`, targeting `self`, action `bonus`, circle=1. `cast` toggles a one-shot preparation. It does not spend resources until a successful weapon hit by that player. Preparation is not persisted.
- Private player state adds `ensnaring_armed: boolean`. Successful triggered casts use normal spell history, rolled combat results and paid concentration profiles.
- Hunter's Mark is `free_cast: true`, mana=0, cooldown=30. All useful duration ranks remain free; cooldown is saved as an absolute deadline and transmitted as remaining seconds.
- Existing `status_effects` entries for Mark and restrained pnącza include spell_id, description and timer. Ensnaring restraint adds `escape_action: true`. The indefinite `ensnaring_ready` status has remaining=null and rounds=null and is not a target restraint.
- Client packet `{ "type": "escape_restraint" }` attempts self-release. Optional string `target_id` requests help for a living, adjacent member of the same party. All permission/range/turn tests and Strength checks occur on the server. One main action is spent per legal attempt, whether successful or not.
- New spell visual styles: `vines` and `mark`. Persistent target overlays are derived from status_effects; no separate lingering client timer. Generic field polygons and spell paths remain unchanged.
- Ranger circles: [1,20,40,60,80]. `mana_rules_version=2`; version-1 Ranger mana is rescaled using the old/new maximum and stored fill ratio. Other classes' mana is unchanged. Older pre-slot migrations remain supported.
- No new network port or hosting environment variables; update server and all web/client assets together. Authentication, PvP safety, movement and inventory packet validation are unchanged.
