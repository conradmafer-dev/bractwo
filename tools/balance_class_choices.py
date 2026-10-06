"""Seeded actual-Game comparison of Ranger styles and Druid Elemental Fury.

python tools/balance_class_choices.py --trials 40 --output /tmp/choices.json

Starter equipment, full resources, no subclass or feats, a 250 ms warning
reaction and at most one health potion. Identical seeds pair the Druid's
chosen/unselected variants. These are starter bosses, so levels 7/15 are
feature demonstrations rather than difficulty targets for those levels.
All rolls, spell permissions, action economy, damage and AI use Game.
"""
import argparse
import asyncio
import json
from pathlib import Path
import random
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.server import Game, Player
from server import combat_rules as rules, dnd_content as dnd, spell_scaling
from tools.balance_starter_bosses import Clock, Socket, DT, steer, sa


def profiles():
    result = [
        dict(id='ranger_bow_none_3', class_id='ranger', level=3, style='', mode='weapon'),
        dict(id='ranger_archery_3', class_id='ranger', level=3, style='archery', mode='weapon',
             reference='ranger_bow_none_3'),
        dict(id='ranger_druidic_wisp_3', class_id='ranger', level=3, style='druidic_warrior',
             mode='starry_wisp', reference='ranger_bow_none_3'),
        dict(id='ranger_druidic_whip_3', class_id='ranger', level=3, style='druidic_warrior',
             mode='thorn_whip', reference='ranger_bow_none_3'),
    ]
    for level in (7, 15):
        for mode, choice in (('starry_wisp', 'potent_spellcasting'),
                             ('staff', 'primal_strike'), ('wolf', 'primal_strike')):
            base = f'druid_{mode}_none_{level}'
            result.append(dict(id=base, class_id='druid', level=level, mode=mode, fury=''))
            result.append(dict(id=f'druid_{mode}_{choice}_{level}', class_id='druid',
                level=level, mode=mode, fury=choice, reference=base))
    return result


PROFILES = profiles()


async def fight(boss, profile, seed, dodge=True):
    clock = Clock()
    game = Game(':memory:', clock=clock)
    try:
        game.rng = random.Random(seed)
        game.combat_rng = random.Random(seed)
        enemy = next(e for e in game.enemies.values() if e.kind == boss)
        game.enemies = {enemy.id: enemy}
        game.enemy_cells.clear()
        game.enemy_cell_keys.clear()
        game.reindex_enemy(enemy)
        player = Player('1', 'Balance', Socket(), class_id=profile['class_id'],
            level=profile['level'], x=enemy.x,
            y=enemy.y+(180 if boss == sa.CRYPT_BOSS else 230), floor=enemy.floor)
        game.starter(player)
        # Directly instantiate a legal completed build. Server command and UI
        # choice validation are covered by regression tests, not this driver.
        player.fighting_style = profile.get('style', '')
        player.ranger_style_cantrips = ['starry_wisp', 'thorn_whip'] if player.fighting_style == 'druidic_warrior' else []
        player.ranger_cantrip_replacement_level = player.level
        player.elemental_fury = profile.get('fury', '')
        player.elemental_damage_type = 'cold'
        player.hp, player.mana = player.max_hp, player.max_mana
        player.current_wall_time = clock()
        game.players[player.id] = player
        game.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',
            (1, player.name, player.name.lower(), b'salt', b'hash', json.dumps(player.save_data())))
        game.db.commit()
        mode = profile['mode']
        cantrip = mode if mode in ('starry_wisp', 'thorn_whip') else ''
        if cantrip and not dnd.spell_allowed(player, cantrip):
            raise AssertionError(f"{profile['id']}: {cantrip} is not granted")
        if mode == 'wolf' and not dnd.spell_allowed(player, 'wild_shape_wolf'):
            raise AssertionError(f"{profile['id']}: wolf is not granted")
        potion_used = False
        specials = 0
        while game.time < 90 and player.alive and enemy.alive and enemy.hp > 0:
            for hazard in game.hazards:
                if 'noticed_at' not in hazard:
                    hazard['noticed_at'] = game.time
                    if hazard.get('starter'):
                        specials += 1
            reach = min(170, spell_scaling.resolve(player, cantrip)['range']*.85) if cantrip else None
            steer(game, player, enemy, dodge, reach=reach)
            if player.hp < player.max_hp*.45 and not potion_used:
                before = player.potions['health_potion']
                await game.inventory_command(player, 'potion', {'item': 'health_potion'})
                potion_used = player.potions['health_potion'] < before
            if player.class_id == 'ranger' and not player.mark_target:
                await game.cast_spell(player, 'hunters_mark', enemy.id, queue=False)
            elif player.class_id == 'druid':
                if mode == 'wolf' and not player.form:
                    await game.cast_spell(player, 'wild_shape_wolf', queue=False)
                elif mode == 'staff' and not rules.active_buff(player, 'shillelagh'):
                    await game.cast_spell(player, 'shillelagh', queue=False)
                if not player.form and player.hp < player.max_hp*.6:
                    await game.cast_spell(player, 'healing_word', queue=False)
            if clock() >= player.attack_cooldown_until:
                if cantrip:
                    await game.cast_spell(player, cantrip, enemy.id, queue=False)
                else:
                    await game.dnd_attack(player, enemy_id=enemy.id, quiet=True)
            clock.value += DT
            game.step(DT)
            await game.process_player_actions()
        return dict(boss=boss, profile=profile['id'], class_id=player.class_id,
            seed=seed, level=player.level, won=player.alive and enemy.hp <= 0,
            seconds=round(game.time, 2), remaining_hp=round(max(0, player.hp), 2),
            max_hp=player.max_hp, remaining_temp_hp=round(player.temp_hp, 2),
            remaining_mana=round(player.mana, 2), max_mana=player.max_mana,
            potion_used=potion_used, specials=specials,
            timeout=player.alive and enemy.hp > 0)
    finally:
        game.db.close()


def summarize(runs, selected):
    result = []
    for boss in sa.BOSSES:
        for profile in selected:
            rows = [row for row in runs if row['boss'] == boss and row['profile'] == profile['id']]
            if not rows:
                continue
            wins = [row for row in rows if row['won']]
            result.append(dict(boss=boss, profile=profile['id'], level=profile['level'],
                trials=len(rows), wins=len(wins),
                mean_seconds=round(statistics.mean(row['seconds'] for row in rows), 2),
                mean_win_seconds=round(statistics.mean(row['seconds'] for row in wins), 2) if wins else None,
                mean_remaining_hp=round(statistics.mean(row['remaining_hp'] for row in rows), 2),
                mean_remaining_temp_hp=round(statistics.mean(row['remaining_temp_hp'] for row in rows), 2),
                mean_remaining_mana=round(statistics.mean(row['remaining_mana'] for row in rows), 2),
                potion_used=sum(row['potion_used'] for row in rows),
                mean_specials=round(statistics.mean(row['specials'] for row in rows), 2),
                timeouts=sum(row['timeout'] for row in rows)))
    return result


def paired_comparisons(runs, selected):
    result = []
    indexed = {(row['boss'], row['profile'], row['seed']): row for row in runs}
    for boss in sa.BOSSES:
        for profile in selected:
            reference = profile.get('reference')
            if not reference:
                continue
            pairs = [(row, indexed.get((boss, reference, row['seed']))) for row in runs
                     if row['boss'] == boss and row['profile'] == profile['id']]
            pairs = [(chosen, base) for chosen, base in pairs if base is not None]
            if not pairs:
                continue
            result.append(dict(boss=boss, profile=profile['id'], reference=reference, pairs=len(pairs),
                mean_seconds_change=round(statistics.mean(chosen['seconds']-base['seconds'] for chosen, base in pairs), 2),
                mean_hp_change=round(statistics.mean(chosen['remaining_hp']-base['remaining_hp'] for chosen, base in pairs), 2),
                mean_mana_change=round(statistics.mean(chosen['remaining_mana']-base['remaining_mana'] for chosen, base in pairs), 2),
                faster=sum(chosen['seconds'] < base['seconds'] for chosen, base in pairs),
                equal_time=sum(chosen['seconds'] == base['seconds'] for chosen, base in pairs),
                slower=sum(chosen['seconds'] > base['seconds'] for chosen, base in pairs)))
    return result


async def simulate(trials, seed_start, selected):
    runs = []
    for boss in sa.BOSSES:
        for profile in selected:
            for seed in range(seed_start, seed_start+trials):
                runs.append(await fight(boss, profile, seed))
            print(json.dumps(summarize(runs, selected)[-1]), flush=True)
    return dict(protocol_version=1, trials=trials, seed_start=seed_start, dodge=True,
        profiles=selected, summary=summarize(runs, selected),
        paired_comparisons=paired_comparisons(runs, selected), runs=runs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=40)
    parser.add_argument('--seed-start', type=int, default=0)
    parser.add_argument('--profiles', help='Comma-separated profile IDs; by default run every profile.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    requested = set(args.profiles.split(',')) if args.profiles else None
    selected = [profile for profile in PROFILES if requested is None or profile['id'] in requested]
    if requested and requested != {profile['id'] for profile in selected}:
        parser.error('Unknown profile in --profiles')
    report = asyncio.run(simulate(args.trials, args.seed_start, selected))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
