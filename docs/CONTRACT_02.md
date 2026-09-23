# Implementation contract 0.2 — authoritative fields and commands

New design: no relic progression; river bridge and sanctuary gate permanently open. All enemies, including boss, respawn. Four permanent classes knight/paladin/mage/druid (Rycerz/Paladyn/Mag/Druid). No designed level cap. Server simulation/protocol based on 0.1.

Existing JSON hello adds class_id for registration. Old hello without class_id defaults knight for compatibility. Existing 0.1 accounts migrate to class_id=knight, class_chosen=false, with one class choice at town using choose_class. New accounts chosen=true. Preserve old level/xp/gold, remove obsolete relic/chest objectives, keep legacy save fields harmless if required.

Commands (all validated on server):
- hello {name,password,create,class_id}
- input {x,y}, attack (monster auto-target) OR attack {target_id:player_id} for deliberate PvP only
- ability (class skill; optional target_id only if appropriate)
- choose_class {class_id} once for legacy chars, town only
- equip {uid}, unequip {slot}, sell {uid}, buy {item:"health_potion"|"mana_potion"}, potion {item:"health_potion"|"mana_potion"}
- interact: merchant info/heal in town (no relics)
- pvp_safety {enabled:bool}; default true on reconnect, explicit false required to attack players
- party_invite {target_id}, party_accept {leader_id}, party_leave
- chat, ping. Old weapon/relic command rejected with helpful explanation (no free weapon/class swaps).

welcome.world additionally: classes {knight:{name,description,ability_name,weapon,...},...}, items {template:{name,slot,attack,armor,class_ids,min_level,value,...},...}, merchant {x:680,y:1180,name:"Kupiec"}, safe_zone {x:560,y:1180,radius:260}, pvp_rules {min_level:8,...}. Authoritative exact values exposed in metadata.

Player snapshot additions: class_id, class_chosen, mana,max_mana,attack,armor, ability_name,ability_cooldown, potions:{health_potion:int,mana_potion:int}, inventory:[{uid,template,name,slot,attack,armor,class_ids,min_level,value,rarity}], equipment:{weapon:uid,armor:uid,ring:uid}, pvp_safety,skull:"none"|"white"|"red",skull_remaining,combat_remaining,unjust_kills,party_id (leader id or empty string),party_members:[id], disconnected:bool. Existing x,y,hp,max_hp,level,xp,xp_next,gold,weapon,kills,alive etc retained. Every client sees only its own inventory/items/potions (other players omit private fields), server creates personalized snapshots; tests can use snapshot(for_player=...) or compatible public base if needed. Parties may be state.parties optional.
party invitation message {type:"party_invite",leader_id,name}; acceptance explicit. Other command outcomes via notice/error. Inventory always from state, never client-authoritative. Chat max160, name3..20.

Classes: knight sword + defensive bulwark/monster taunt; paladin bow + stronger shot; mage staff + AoE against monsters; druid staff + heal self and nearby party (or self when alone). Mana, cooldowns, class stats meaningful; no swapping class after creation. Skills must respect PvP protections and never auto-hit players. Direct basic PvP attack only with explicit target; offensive class skills can remain PvE-only in this version and document it. Death respawns in town.

Loot: persistent individual equipment drops, slots weapon/armor/ring, actual stat bonuses and min-level/class requirements. Inventory cap40; server handles full inventory with clear notice. Shop sells health/mana potions for gold, buys unequipped gear near merchant. Equip/sell/potion commands must be idempotent through actual ownership and cooldowns. Boss rewards repeat after respawn, once per player per kill; remove legacy permanent boss reward blocking.

Party: up to4, invite/accept/leave; nearby party members share PvE XP pool (small party bonus) and each gets own loot roll; support can participate. No PvP XP or gold generation. Use reasonable participation/range rules and expose/document them.

PvP defaults: protected town radius260 and all chars below level8. Explicit safety-off and target required. First unjust attack gives white skull120s, combat tag20s to both. Retaliation vs marked aggressor justified; crime timestamps and red skull persistent. 3 unjust kills in rolling24h => red skull24h (refresh after further unjust kills). Normal death: lose5% carried gold and10% current level progress XP, no level loss. Red death:20% gold and20% current-level XP plus one unequipped item (if killer available and has capacity, transfer; otherwise loss or world drop must clearly document). No XP for kills; no bounty creating money. Cannot enter safe town during combat. Disconnected combat avatar remains targetable until combat tag expires; reconnect reuses it without restoring HP or moving to safety. All deadlines persisted using wall-clock, not simulation clock; tests can advance server clock abstraction.

Expose metadata and notify other agents promptly if exact shape must change. Implement each agent only in own assigned files. This file is shared contract, root owns updates.

Final implementation notes: public pvp_combat_remaining is separate from general combat_remaining. Town entry checks PvP only; general combat retains disconnected avatars and blocks shop/rest. Party level3:1 ratio applies pairwise across rewarded members. Druid can heal self but cannot heal other players currently PvP-tagged. Recent PvP attacker attribution lasts20s for environmental finishers. Full inventory loses new item with notice; red-death item transfers to killer if space, otherwise destroyed. New chars start0gold,3health/3mana potions; merchant prices15/12, potion cooldown3s, per-typecap99.
