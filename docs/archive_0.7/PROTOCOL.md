# Protocol 0.6.0 · JSON over WebSocket /ws

Default local endpoint: ws://127.0.0.1:8080/ws. Public hosts require WSS. Client sends commands; server owns positions, combat, inventory, XP, loot and crimes. Simulation20Hz, personalized snapshots10Hz.

## Commands

```json
{"type":"hello","name":"Aren","password":"example-password","create":true,"class_id":"knight"}
{"type":"input","x":0.0,"y":1.0}
{"type":"attack"}
{"type":"attack","target_id":"2"}
{"type":"ability"}
{"type":"pvp_safety","enabled":false}
{"type":"equip","uid":"owned-item-uid"}
{"type":"unequip","slot":"armor"}
{"type":"sell","uid":"owned-item-uid"}
{"type":"buy","item":"health_potion"}
{"type":"potion","item":"mana_potion"}
{"type":"interact"}
{"type":"party_invite","target_id":"2"}
{"type":"party_accept","leader_id":"1"}
{"type":"party_leave"}
{"type":"choose_class","class_id":"druid"}
{"type":"quest_accept","quest_id":"q_rats"}
{"type":"quest_claim","quest_id":"q_rats"}
{"type":"chat","text":"Wyruszamy?"}
{"type":"ping"}
```

Class IDs: knight/paladin/mage/druid. Item slots: weapon/armor/ring. choose_class applies only to an eligible legacy account in town. Class weapons are sword/bow/staff; equipment changes bonuses, not vocation. Abilities are PvE-oriented: offensive skills never hit players; Druid can self-heal and heal nearby party members outside their active PvP combat.

## Messages

- welcome: id and world metadata (width,height,spawn,river,obstacles,zones,classes,items,merchant,safe_zone,pvp_rules,potions,party_rules,abilities).
- state: tick,time,players,enemies,world,effects. IDs are strings. World dimensions are128000×92160; clients must use metadata, not hard-coded bounds.
- notice/error: text. Commands rejected by rules leave authoritative state unchanged.
- party_invite: leader_id,name. Client must explicitly accept.
- chat: id,name,text. Maximum160 printable characters; minimum1.5 seconds between messages.
- pong: acknowledgement useful for ordered protocol tests.

Public player fields include id,name,x,y,hp,max_hp,mana,max_mana,level,class_id,class_chosen,weapon,attack,armor,kills,boss_kills,ability_name,ability_cooldown,facing,attack_until,alive,respawn_in,skull,skull_remaining,combat_remaining,pvp_combat_remaining,disconnected,party_id,party_members.

Only the owning client receives xp,xp_next,gold,pvp_safety,unjust_kills,inventory,equipment,potions,potion_cooldown for its own character. inventory entries have uid,template,name,slot,attack,armor,class_ids,min_level,value,rarity. equipment maps slots to owned item UIDs. Clients do not send item definitions or numerical stat modifications.

Enemy fields include id,kind,name,x,y,hp,max_hp,alive,attack_until,facing. Dead enemies respawn automatically. Boss kills reward again after each respawn; persistent0.1 boss reward rows no longer block rewards.

All displayed cooldown and combat_remaining values are remaining seconds. attack_until and state.time refer to simulation animation time. Persistent skill/potion/PvP deadlines use server wall-clock internally. No client time is trusted.

The sites/chests arrays are empty compatibility metadata. Relic commands are rejected with an explanatory notice; no route depends on relic ownership. Existing save fields may remain only for migration. Bridge and sanctuary passage are permanently open.

For current authoritative numeric content, see CLASSES,ITEMS,ENEMY_TYPES,PVP_RULES and POTIONS in server/server.py. Tests include real WebSocket sessions and migration from0.1.


## Additions in 0.3

World metadata adds `npcs`, `landmarks`, `quests`; clients render the server catalog. Player public data adds `speed`, `attack_facing`, `speech_text`, `speech_until`. `speech_until` uses simulation time. Walking updates `facing` but never rewrites captured attack aim.

The state `effects` list retains recent animation events for snapshot delivery. Each event has `id`, `kind`, `source_id`, `target_id`, `x`, `y`, `target_x`, `target_y`, `time`, `duration`, `radius`. Deduplicate by ID and skip expired animations. Types are sword, arrow, magic_bolt, nature_bolt, piercing_arrow, fire_ring, bulwark and heal. Origin and destination are captured by the server at attack/cast; effects are visual only. Damage is resolved immediately by the server. Coordinates do not follow a moving caster.

Owner-only `quests` contains entries with id,title,description,npc_id,status,objectives,reward,requires. Status values: locked,available,active,ready,claimed. Objectives include type (kill/discover), target,label,count,required. `discoveries` holds known landmark IDs. Counters, prerequisites, rewards and NPC interaction range are validated and persisted on the server. Accepting and claiming requires the matching NPC within150; a full inventory blocks a claim that would give an item, preserving the reward. Earlier discoveries count, kills before acceptance do not. Eligible rewarded party members receive kill-objective credit.

NPC metadata: id,name,x,y,role,radius. Landmark metadata: id,name,x,y,radius,description,biome. Quest metadata is also available before personalized progress arrives. Reach a landmark within its radius to discover it and receive a one-time reward. See the actual server catalog for coordinates, reward values and monster stats; `CONTRACT_03.md` records the implementation contract.


## Additions in 0.4

Authoritative catalogs are in `server/world_content.py`, progression rules in `server/progression.py`. Server simulation remains 20 Hz and personalized snapshots 10 Hz.

```json
{"type":"cast","spell_id":"mend"}
{"type":"cast","spell_id":"haste"}
{"type":"rune_craft","rune_id":"fire"}
{"type":"rune_buy","rune_id":"ice"}
{"type":"rune_use","rune_id":"death"}
{"type":"descend"}
{"type":"travel","city_id":"brzezina"}
{"type":"bank_deposit","amount":"all"}
{"type":"bank_withdraw","amount":100}
{"type":"depot_store","uid":"owned-item-uid"}
{"type":"depot_take","uid":"stored-item-uid"}
{"type":"bind_city"}
{"type":"promote"}
{"type":"bless"}
{"type":"mastery","branch":"power"}
{"type":"mastery_reset"}
```

`descend` chooses a nearby stair on the current floor. The client never supplies a destination position or floor. PvP combat blocks floor transitions; a one-second transition cooldown prevents repeated crossings. Only the deepest final entrance requires level 100. Travel validates captain range, floor, level, destination, price and combat state. Bank amounts must be positive integers or the exact string `all`; booleans/fractions are rejected. Services persist before acknowledging completion.

World metadata adds `version`, `regions`, `cities`, `safe_zones`, `stairs`, `dungeons`, `roads`, `hunting_grounds`, `spells`, `runes`, `milestones` and enemy appearance metadata. Surface is floor 0; caves are floors -1 and -2. Spatial entities carry a `floor` value, defaulting to 0 for legacy objects. Each dungeon provides walkable room rectangles. Enemy stats are fixed by species, not by player level.

Public players include `floor` and `promoted`. Owner-only progression includes `profession`, `skills`, `runes`, `soul`, `max_soul`, `bank_gold`, `depot`, `home_city`, `blessed`, `mastery`, `mastery_points`, `spell_cooldowns`, `haste_remaining`, `rune_cooldown`. Each skill has `level`, `progress`, `next`. Spell cooldowns are remaining seconds. Private inventory, bank and progression details never appear in another player's entry.

Enemy snapshots are filtered to the owner's floor and a local 1800-unit radius; absence means out of interest, not death. Clients must discard stale distant actors and request no enemy positions. Effects are also floor/local filtered. Attack direction and captured origin/destination semantics from 0.3 remain. New effects include `ice_ring` and `haste`.

Area spells and runes damage only monsters, validate line of sight and floor, and use server-side mana/soul/charge/level/vocation/promotion/cooldown checks. Ordinary spells and rune use share a short exhaustion gate. Crafting is restricted to mage and druid; all vocations can buy/use level-appropriate runes.

Potions add `health_potion_2`/`mana_potion_2`, `_3`, `_4`, requiring levels 20, 50, 80. Use the `potions` catalog for restoration values and prices. Regional quests add `min_level`; objectives include destination coordinates and floor for navigation even when monsters are not in the current local snapshot.

The server never accepts client position, floor, XP, bank balance, skill or inventory definitions as authoritative command values. Integration coverage is in `tests/test_expansion.py` together with legacy tests.


## Additions in 0.4.1

```json
{"type":"hello","name":"Aren","password":"example-password","create":false,"compact_state":true}
{"type":"attack","enemy_id":"world_10"}
{"type":"ability","enemy_id":"world_10"}
{"type":"rune_use","rune_id":"death","enemy_id":"world_10"}
```

Monster IDs and PvP targets use separate fields. `attack` rejects conflicting targets and malformed monster IDs. A selected monster is validated for life, floor, range and line of sight; failure never falls back to a nearer target. `ability.enemy_id` directs the paladin's single-target attack; existing area/self abilities keep their original areas. Rune use directs its primary hit/area center to the selected monster. Without selection, nearest-target behavior remains available. PvP protection is never bypassed by monster selection.

With `compact_state: true`, welcome contains `owner_deltas: true`. State packets may contain `owner_delta: true`; only the owning player's `quests`, `discoveries`, `inventory`, `equipment`, `depot`, `skills`, `runes`, `mastery`, `potions` may be absent when unchanged. Merge the own-player record shallowly onto the previous own-player record. An explicit empty array/dictionary replaces the previous value. Public player fields remain complete; never merge other players' private state. Enemy/effect lists remain complete local lists, not deltas. First login state is complete and owner cache is cleared on reconnect. Legacy clients that omit the opt-in get the original complete format.

The owner cache is per connection/session, never a persistent gameplay field. JSON comparisons detect nested changes before omission. This optimization reduces repeated transmission of quest text and bags without reducing simulation or state update frequency.


## Additions in 0.5.0

- `{"type":"premium_demo","enabled":true}` enables a **free simulation**, not a purchase, for 30 server-clock days. `false` disables it. `enabled` must be a Boolean. Re-enabling an already active demo is idempotent. No automatic renewal, currency deduction or payment provider exists. Persisted field: `premium_demo_until`. Do not reuse this publicly callable test endpoint as authorization for a future paid entitlement.
- `world.premium` describes mock mode, display price 10 PLN, period and multiplier 1.2. Owner state includes `premium_demo`, `premium_demo_remaining`, `surface`; `speed` is the final authoritative speed including terrain, level, premium and haste.
- `world.terrain` contains ellipse bounds and surface IDs. `world.surfaces` contains name/color/multiplier. Surface priority: underground stone, city paving, distance ≤33 from a road segment, last matching ellipse, biome fallback. Python, JS and GDScript implement the same classifier; gameplay never trusts client classification.
- `hunting_grounds`: `decoration`, `members`, optional `name`, stable per-world ID. Do not render tents for every habitat. `landmarks[].hint` marks suggested local destinations. Surface spawns are irregular, indexed by home coordinates; maximum chase radius 1100, index padding 1120.
- Enemy public state adds `size`; type metadata includes size, aggro, leash, speed, projectile, windup, attack_interval and boss special range. Current idle patrols simulate only around players; distant residents sleep without ticking.
- Enemy FX: `danger_zone` (ground warning at target_x/target_y, radius, duration, element, special), `enemy_arrow`, `enemy_stone`, `enemy_venom`, `enemy_fire`, `enemy_ice`, `enemy_shadow`, `enemy_arcane`, `enemy_feather`, `enemy_impact`. Damage resolves on the server after windup plus 0.32 seconds. The impact checks radius, floor, protection zone and line of sight. Killing the source cancels pending damage. Effects are floor-filtered in clients.
- Snapshot scope and compact private deltas remain compatible. The welcome catalogue is about 2.4 MB; native Godot input buffer is 8 MiB instead of the default 64 KiB. Per-tick states do not repeat the world catalogue.


## Additions in 0.6.0

World metadata adds `elevations` (bounded rooms on floors +1/+2/+3), `waterways` and `bridges` (segments with a/b, width, bounds), `canyons`, `pois` and `rarities`. Every obstacle carries a floor (default 0). Obstacles on other floors are neither collision nor scenery on the player's current floor. Nonzero floors require all player corners to remain inside a room union. Existing `descend` handles stairs in either direction: client-supplied coordinates, floor and destinations are ignored. PvP floor lock and one-second transition cooldown remain.

Use `{ "type": "interact" }` beside a POI. Server resolves the nearest canonical site by floor, radius and line of sight, then checks life, level, combat and saved cooldown. Actions: `spring` (full HP/mana, cooldown180s), `wind` (+15% movement90s, cooldown300s), `ward` (12% PvE damage reduction90s, cooldown300s), `cache` (tier gear + family trophy, eligible 6% bonus named family item, cooldown1800s). Three free bag slots are required before opening a cache; a rejected request does not roll or consume it. The `sites` and `chests` legacy arrays remain empty; new content uses `pois`.

New owner-only fields: `site_cooldowns` maps site IDs to remaining seconds, `wind_remaining`, `ward_remaining`. Server saves absolute deadlines. Buffs expire normally across logout and are removed on death; site cooldowns survive death. Ward does not modify PvP damage. Wind multiplies the existing surface, haste and mock-premium bonuses.

Enemy metadata adds `combat_role`, `melee_range`, `melee_damage`, `ranged_interval`, `loot`. Hybrid monsters approach melee distance regardless of projectile range; regular projectiles allow 70% movement while winding up, special boss attacks pause only for their telegraph. Ranged and melee cooldowns are separate. Collision, line of sight, floor and safe-zone checks stay authoritative.

Loot odds are per eligible reward recipient; rolls are independent. Tier gear, species trophies, existing stackable potions, named family gear and high-level legendary relics can drop together. Full bags/potion stacks reject excess loot with a notice. Items with `slot: trophy` cannot be equipped; they can be sold or stored. Existing equipment slots remain weapon/armor/ring. Named weapons match the recipient's vocation. Canonical `ITEMS` supply all bonuses and sell values. `legendary` adds a rarity label and gold accent in WWW; native UI shows the same rarity text.
