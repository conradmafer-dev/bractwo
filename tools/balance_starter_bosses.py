"""Seeded, server-driven solo starter-boss benchmark.

python tools/balance_starter_bosses.py --trials 40 --level 3 --output /tmp/balance.json
Level 3 is the native D&D equivalent of the old Bractwo level 10.
Use the same script on both revisions: the original UI33 script was not saved.
No combat math is duplicated: actions, movement, AI and damage use Game.
"""
import argparse
import asyncio
import json
import math
from pathlib import Path
import random
import statistics
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.server import Game, Player
from server import starter_adventures as sa, combat_rules as rules, spell_scaling, dnd_content as dnd

CLASSES = ('knight', 'ranger', 'mage', 'druid')
DT = .05


class Clock:
    value = 1000.0

    def __call__(self):
        return self.value


class Socket:
    closed = False

    async def send_json(self, data):
        pass


def threatened(h, x, y):
    if h.get('starter'):
        return sa.in_telegraph(h, SimpleNamespace(x=x, y=y))
    return math.hypot(x-h['target_x'], y-h['target_y']) <= h['radius']+12


def steer(game, player, enemy, dodge, reach=None):
    """Approach attack range; react to visible warnings after 250ms.

    Ranged characters hold position between warnings (no perfect kiting).
    A short local direction search respects the real room walls and pillars.
    """
    warnings = [h for h in game.hazards if h['floor'] == player.floor]
    danger = [h for h in warnings if game.time >= h['noticed_at']+.25
              and threatened(h, player.x, player.y)] if dodge else []
    dx, dy = enemy.x-player.x, enemy.y-player.y
    distance = math.hypot(dx, dy)
    if reach is None:
        reach = 170 if player.class_id == 'mage' else min(170, rules.attack_range(player)*.85)
    vx, vy = (dx/distance, dy/distance) if distance > reach else (0, 0)
    if danger:
        candidates = []
        for i in range(16):
            ux, uy = math.cos(i*math.tau/16), math.sin(i*math.tau/16)
            x, y = player.x+ux*80, player.y+uy*80
            if any(game.blocked(player.x+ux*d, player.y+uy*d, floor=player.floor)
                   for d in (10, 30, 50, 80)):
                continue
            score = sum(threatened(h, x, y) for h in warnings)*10000
            # Shortest escape for circles; sidestep the fixed aim for lines.
            score += math.hypot(x-enemy.x, y-enemy.y)*.01
            for h in danger:
                if h.get('shape') == 'circle':
                    score -= math.hypot(x-h['x'], y-h['y'])
            candidates.append((score, i, ux, uy))
        if candidates:
            _, _, vx, vy = min(candidates)
    elif dodge and warnings:
        # Do not walk straight back into a warning just avoided.
        if any(threatened(h, player.x+vx*20, player.y+vy*20) for h in warnings):
            vx, vy = 0, 0
    player.dx, player.dy, player.input_time = vx, vy, game.time


async def fight(boss, class_id, seed, level=3, dodge=True):
    clock = Clock()
    game = Game(':memory:', clock=clock)
    try:
        game.rng = random.Random(seed)
        game.combat_rng = random.Random(seed)
        enemy = next(e for e in game.enemies.values() if e.kind == boss)
        # Isolate the duel while retaining the actual arena and collision map.
        game.enemies = {enemy.id: enemy}
        game.enemy_cells.clear()
        game.enemy_cell_keys.clear()
        game.reindex_enemy(enemy)
        player = Player('1', 'Balance', Socket(), class_id=class_id, level=level,
                        x=enemy.x, y=enemy.y+(180 if boss == sa.CRYPT_BOSS else 230),
                        floor=enemy.floor)
        game.starter(player)
        if class_id == 'mage':
            # The duel assumes a completed starting choice, just like its
            # equipped weapon. Use the real book commands, not a cast bypass.
            await game.wizard_book_command(player, 'wizard_learn', {'spell': 'magic_missile'})
            await game.wizard_book_command(player, 'wizard_prepare', {'spells': ['magic_missile']})
            if not dnd.spell_allowed(player, 'magic_missile'):
                raise AssertionError('The benchmark wizard must prepare Magic Missile')
        player.hp, player.mana = player.max_hp, player.max_mana
        player.current_wall_time = clock()
        game.players[player.id] = player
        game.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',
                        (1, player.name, player.name.lower(), b'salt', b'hash', json.dumps(player.save_data())))
        game.db.commit()
        potion_used = False
        specials = 0
        while game.time < 90 and player.alive and enemy.alive and enemy.hp > 0:
            for h in game.hazards:
                if 'noticed_at' not in h:
                    h['noticed_at'] = game.time
                    if h.get('starter'):
                        specials += 1
            steer(game, player, enemy, dodge)
            if player.hp < player.max_hp*.45 and not potion_used:
                before = player.potions['health_potion']
                await game.inventory_command(player, 'potion', {'item': 'health_potion'})
                potion_used = player.potions['health_potion'] < before
            if class_id == 'knight' and player.hp < player.max_hp*.65:
                await game.cast_spell(player, 'second_wind', queue=False)
            elif class_id == 'ranger' and not player.mark_target:
                await game.cast_spell(player, 'hunters_mark', enemy.id, queue=False)
            elif class_id == 'druid':
                if not rules.active_buff(player, 'shillelagh'):
                    await game.cast_spell(player, 'shillelagh', queue=False)
                if player.hp < player.max_hp*.6:
                    await game.cast_spell(player, 'healing_word', queue=False)
            if clock() >= player.attack_cooldown_until:
                if class_id == 'mage':
                    if player.mana < spell_scaling.resolve(player, 'magic_missile')['mana']:
                        player.spell_circle_choices['magic_missile'] = 1
                    key = 'magic_missile' if player.mana >= spell_scaling.resolve(player, 'magic_missile')['mana'] else 'fire_bolt'
                    await game.cast_spell(player, key, enemy.id, queue=False)
                else:
                    await game.dnd_attack(player, enemy_id=enemy.id, quiet=True)
            clock.value += DT
            game.step(DT)
            await game.process_player_actions()
        return dict(boss=boss, class_id=class_id, seed=seed, level=level,
                    won=player.alive and enemy.hp <= 0, seconds=round(game.time, 2),
                    remaining_hp=round(max(0, player.hp), 2), max_hp=player.max_hp,
                    remaining_mana=round(player.mana, 2), max_mana=player.max_mana,
                    potion_used=potion_used, specials=specials,
                    timeout=player.alive and enemy.hp > 0)
    finally:
        game.db.close()


def summarize(runs):
    result = []
    for boss in sa.BOSSES:
        for cls in CLASSES:
            rows = [r for r in runs if r['boss'] == boss and r['class_id'] == cls]
            if not rows:
                continue
            wins = [r for r in rows if r['won']]
            result.append(dict(boss=boss, class_id=cls, trials=len(rows), wins=len(wins),
                mean_seconds=round(statistics.mean(r['seconds'] for r in rows), 2),
                mean_win_seconds=round(statistics.mean(r['seconds'] for r in wins), 2) if wins else None,
                mean_remaining_hp=round(statistics.mean(r['remaining_hp'] for r in rows), 2),
                mean_remaining_mana=round(statistics.mean(r['remaining_mana'] for r in rows), 2),
                potion_used=sum(r['potion_used'] for r in rows),
                mean_specials=round(statistics.mean(r['specials'] for r in rows), 2),
                timeouts=sum(r['timeout'] for r in rows)))
    return result


async def simulate(trials=40, seed_start=0, level=3, dodge=True):
    runs = []
    for boss in sa.BOSSES:
        for cls in CLASSES:
            for seed in range(seed_start, seed_start+trials):
                runs.append(await fight(boss, cls, seed, level, dodge))
            print(json.dumps(summarize(runs)[-1]), flush=True)
    return dict(protocol_version=1, trials=trials, seed_start=seed_start, level=level,
                dodge=dodge, summary=summarize(runs), runs=runs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=40)
    parser.add_argument('--seed-start', type=int, default=0)
    parser.add_argument('--level', type=int, default=3)
    parser.add_argument('--no-dodge', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.trials < 1:
        parser.error('--trials must be positive')
    report = asyncio.run(simulate(args.trials, args.seed_start, args.level, not args.no_dodge))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
