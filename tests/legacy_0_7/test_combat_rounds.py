"""0.7: exact dice semantics and real WebSocket action/movement regressions."""
from collections import deque
import random
import unittest

import test_server as legacy
import test_living_world as living
from server import server as core, combat_rules as rules


class Dice:
    def __init__(self, *checks, damage=3):
        self.checks = deque(checks)
        self.damage = damage
        self.calls = 0

    def randint(self, low, high):
        self.calls += 1
        if high == 20:
            if not self.checks:
                raise AssertionError("Unexpected d20: action was duplicated or queued")
            return self.checks.popleft()
        return min(high, max(low, self.damage))


class DiceRulesTests(unittest.TestCase):
    def test_ac_equality_natural_one_and_critical_double_dice_not_modifier(self):
        ordinary = rules.roll_attack(Dice(10), 4, 14, (2, 6, 7))
        self.assertTrue(ordinary['hit'])
        self.assertEqual(ordinary['damage'], 13)
        miss = rules.roll_attack(Dice(1), 100, 1, (2, 6, 7))
        self.assertFalse(miss['hit']); self.assertEqual(miss['damage'], 0)
        critical = rules.roll_attack(Dice(20), 0, 100, (2, 6, 7))
        self.assertTrue(critical['critical']); self.assertEqual(critical['damage'], 19)
        self.assertEqual(critical['damage_rolls'], [3, 3, 3, 3])
        self.assertEqual(critical['damage_modifier'], 7)

    def test_disadvantage_keeps_lower_roll_including_natural_results(self):
        miss = rules.roll_attack(Dice(20, 1), 99, 10, (2, 8, 5), True)
        self.assertFalse(miss['hit']); self.assertFalse(miss['critical'])
        normal = rules.roll_attack(Dice(20, 19), 4, 13, (2, 8, 5), True)
        self.assertTrue(normal['hit']); self.assertFalse(normal['critical'])
        self.assertEqual((normal['rolls'], normal['roll']), ([20, 19], 19))

    def test_saves_half_damage_and_use_total_without_automatic_one_or_twenty(self):
        damage = rules.roll_damage(Dice(), (2, 6, 7))
        success = rules.roll_save(Dice(1), 20, 21, damage)
        failure = rules.roll_save(Dice(20), 0, 21, damage)
        self.assertTrue(success['saved']); self.assertEqual(success['damage'], 6)
        self.assertFalse(failure['saved']); self.assertEqual(failure['damage'], 13)

    def test_seeded_hit_distribution_has_both_misses_and_criticals(self):
        rng = random.Random(707)
        results = [rules.roll_attack(rng, 4, 14, (2, 6, 7)) for _ in range(20000)]
        self.assertAlmostEqual(sum(r['hit'] for r in results)/len(results), .55, delta=.015)
        self.assertAlmostEqual(sum(r['critical'] for r in results)/len(results), .05, delta=.01)


class CombatRoundTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = legacy.AuthoritativeServerTests.asyncSetUp
    asyncTearDown = legacy.AuthoritativeServerTests.asyncTearDown
    start_server = legacy.AuthoritativeServerTests.start_server
    restart = legacy.AuthoritativeServerTests.restart
    packet = legacy.AuthoritativeServerTests.packet
    connect = legacy.AuthoritativeServerTests.connect
    sync = legacy.AuthoritativeServerTests.sync
    command = legacy.AuthoritativeServerTests.command
    state = legacy.AuthoritativeServerTests.state
    place = legacy.AuthoritativeServerTests.place
    step = living.LivingWorldTests.step

    def arena(self, p, kind='goblin', distance=45):
        enemy = living.LivingWorldTests.arena(self, p, kind, 11000, 1000, distance)
        enemy.ready = enemy.aoe_ready = self.game.time + 1000
        enemy.hp = 10000
        return enemy

    async def test_manual_without_selection_hits_nearest_visible_monster_only(self):
        ws, p, welcome = await self.connect('ManualArcher', class_id='paladin')
        near = self.arena(p, distance=100)
        far = core.Enemy('far', 'wolf', p.x+200, p.y, 1000, p.x+200, p.y)
        self.game.enemies[far.id] = far; self.game.legacy_enemies.append(far)
        _, other, _ = await self.connect('NearbyPlayer')
        self.place(other, p.x+25, p.y, level=8)
        self.game.combat_rng = Dice(19)
        await self.command(ws, 'attack')
        self.assertLess(near.hp, 10000); self.assertEqual(far.hp, 1000)
        self.assertEqual(other.hp, other.max_hp)
        self.assertEqual(p.last_roll['target_id'], near.id)
        self.assertEqual(welcome['world']['combat_rules']['round_seconds'], 3)
        self.assertFalse(welcome['world']['combat_rules']['target_required'])

    async def test_round_boundary_repeat_packets_and_no_delayed_auto_attack(self):
        ws, p, _ = await self.connect('RoundBoundary')
        e = self.arena(p)
        self.game.combat_rng = Dice(19, 19)
        await self.command(ws, 'attack')
        hp = e.hp; deadline = p.attack_cooldown_until
        for _ in range(5):
            await self.command(ws, 'attack')
        self.clock.value = deadline - .001
        await self.command(ws, 'attack')
        self.assertEqual(e.hp, hp)
        self.clock.value = deadline
        await self.command(ws, 'attack')
        self.assertLess(e.hp, hp)
        report = p.last_roll['id']; trained = dict(p.skill_tries)
        self.step(4)
        self.assertEqual(p.last_roll['id'], report)
        self.assertEqual(p.skill_tries, trained)
        self.assertEqual(self.state(p)['action_remaining'], 0)

    async def test_movement_continues_during_round_and_press_does_not_queue(self):
        ws, p, _ = await self.connect('MovingFighter')
        e = self.arena(p)
        self.game.combat_rng = Dice(19)
        await self.command(ws, 'attack')
        y = p.y; report = p.last_roll['id']
        for _ in range(5):
            await self.command(ws, 'input', x=0, y=1)
            await self.command(ws, 'attack')
            self.step(.2)
        self.assertGreater(p.y, y+60)
        self.assertGreater(self.state(p)['action_remaining'], 1.9)
        await self.command(ws, 'input', x=0, y=0)
        self.step(3)
        self.assertEqual(p.last_roll['id'], report)
        self.assertEqual(e.attacker_id, p.id)

    async def test_shared_actions_cannot_bypass_round_in_any_class(self):
        for class_id in core.CLASSES:
            with self.subTest(class_id=class_id):
                ws, p, _ = await self.connect('Actions'+class_id, class_id=class_id)
                e = self.arena(p, 'boss', distance=100)
                p.level = 80; p.promoted = True; p.mana = p.max_mana; p.hp = p.max_hp-100
                p.runes['fire'] = 2
                await self.command(ws, 'attack', enemy_id=e.id)
                after = (p.mana, p.runes['fire'], e.hp)
                await self.command(ws, 'ability', enemy_id=e.id)
                await self.command(ws, 'cast', spell_id='mend')
                await self.command(ws, 'rune_use', rune_id='fire')
                self.assertEqual((p.mana, p.runes['fire'], e.hp), after)
                self.clock.advance(3)
                await self.command(ws, 'ability', enemy_id=e.id)
                self.assertLess(p.mana, after[0])
                after = (p.mana, p.runes['fire'], e.hp)
                await self.command(ws, 'attack', enemy_id=e.id)
                await self.command(ws, 'rune_use', rune_id='fire')
                self.assertEqual((p.mana, p.runes['fire'], e.hp), after)
                self.clock.advance(3); p.hp = p.max_hp-150
                await self.command(ws, 'cast', spell_id='mend')
                self.assertLess(p.mana, after[0])
                after = (p.mana, p.runes['fire'], e.hp)
                await self.command(ws, 'attack', enemy_id=e.id)
                await self.command(ws, 'rune_use', rune_id='fire')
                self.assertEqual((p.mana, p.runes['fire'], e.hp), after)
                self.clock.advance(3)
                await self.command(ws, 'rune_use', rune_id='fire')
                self.assertEqual(p.runes['fire'], 1)
                hp = e.hp
                await self.command(ws, 'attack', enemy_id=e.id)
                self.assertEqual(e.hp, hp)

    async def test_invalid_target_or_no_target_costs_no_round(self):
        ws, p, _ = await self.connect('InvalidRound')
        e = self.arena(p, distance=900)
        self.game.combat_rng = Dice()
        for fields in ({}, {'enemy_id':e.id}, {'enemy_id':'unknown'}):
            await self.command(ws, 'attack', **fields)
            self.assertEqual(p.attack_cooldown_until, 0)
        e.x = p.x+30; e.floor = -1
        await self.command(ws, 'attack')
        self.assertEqual(p.attack_cooldown_until, 0)
        self.assertEqual(self.game.combat_rng.calls, 0)

    async def test_forged_roll_is_ignored_and_miss_provokes_without_loot_credit(self):
        ws, p, _ = await self.connect('RealDice')
        e = self.arena(p)
        self.game.combat_rng = Dice(1)
        await self.command(ws, 'attack', roll=20, damage=99999, attack_bonus=999, action_remaining=0)
        self.assertEqual(e.hp, 10000)
        self.assertEqual(p.last_roll['roll'], 1)
        self.assertEqual(e.attacker_id, p.id)
        self.assertNotIn(p.id, e.contributors)
        self.assertEqual(self.state(p)['action_remaining'], 3)
        self.assertGreater(p.combat_until, self.clock())

    async def test_close_ranged_attack_uses_lower_die_but_sword_does_not(self):
        ws, p, _ = await self.connect('CloseArcher', class_id='paladin')
        e = self.arena(p, distance=35)
        self.game.combat_rng = Dice(20, 1)
        await self.command(ws, 'attack')
        self.assertEqual(e.hp, 10000); self.assertTrue(p.last_roll['disadvantage'])
        e.x = p.x+200; self.clock.advance(3)
        self.game.combat_rng = Dice(19)
        await self.command(ws, 'attack')
        self.assertLess(e.hp, 10000); self.assertFalse(p.last_roll['disadvantage'])
        sword_ws, sword, _ = await self.connect('CloseKnight')
        e = self.arena(sword, distance=35)
        self.game.combat_rng = Dice(19)
        await self.command(sword_ws, 'attack')
        self.assertLess(e.hp, 10000); self.assertFalse(sword.last_roll['disadvantage'])

    async def test_pvp_miss_still_marks_aggression_and_preserves_victim_hp(self):
        ws, p, _ = await self.connect('MissingAggressor')
        self.arena(p)
        _, victim, _ = await self.connect('DodgingVictim')
        self.place(victim, p.x+40, p.y, level=8)
        await self.command(ws, 'pvp_safety', enabled=False)
        self.game.combat_rng = Dice(1)
        await self.command(ws, 'attack', target_id=victim.id)
        self.assertEqual(victim.hp, victim.max_hp)
        self.assertEqual(p.skull(self.clock()), 'white')
        self.assertGreater(victim.aggressors[p.id], self.clock())
        self.assertGreater(p.pvp_combat_until, self.clock())
        self.assertEqual(p.attack_cooldown_until, self.clock()+3)
        self.assertEqual((p.xp, victim.xp), (0, 0))

    async def test_monster_melee_rolls_and_respects_own_recovery(self):
        _, p, _ = await self.connect('MonsterDice')
        e = self.arena(p, distance=30); e.ready = 0
        self.game.combat_rng = Dice(1, 20)
        hp = p.hp
        self.step(.1)
        self.assertEqual(p.hp, hp)
        first = next(f for f in self.game.effects if f['kind']=='combat_roll')
        self.assertFalse(first['hit'])
        self.step(2.8)
        self.assertEqual(p.hp, hp)
        self.step(.2)
        self.assertLess(p.hp, hp)
        last = [f for f in self.game.effects if f['kind']=='combat_roll'][-1]
        self.assertTrue(last['critical'])

    async def test_projectiles_use_ac_boss_areas_use_saves_and_can_be_dodged(self):
        _, p, _ = await self.connect('ProjectileDice')
        e = self.arena(p, 'boss', distance=180)
        self.game.combat_rng = Dice(1)
        self.game.queue_enemy_attack(e, p)
        self.game.time += 2; self.game.resolve_hazards()
        self.assertEqual(p.hp, p.max_hp)
        self.assertEqual(self.game.effects[-1]['check'], 'attack')
        self.assertFalse(self.game.effects[-1]['hit'])
        losses = []
        for check in (20, 1):
            p.hp = p.max_hp; e.special_count = 2
            self.game.combat_rng = Dice(check)
            self.game.queue_enemy_attack(e, p, special=True)
            self.game.time += 2; self.game.resolve_hazards()
            losses.append(p.max_hp-p.hp)
            self.assertEqual(self.game.effects[-1]['check'], 'save')
        self.assertEqual(losses[0], losses[1]//2)
        self.game.combat_rng = Dice()
        self.game.queue_enemy_attack(e, p)
        p.y += 250; hp = p.hp
        self.game.time += 2; self.game.resolve_hazards()
        self.assertEqual(p.hp, hp); self.assertEqual(self.game.combat_rng.calls, 0)

    async def test_rolled_damage_uses_kp_once_and_retains_bulwark_and_ward(self):
        _, p, _ = await self.connect('ArmoredDefense')
        e = self.arena(p, 'boss')
        self.game.combat_rng = Dice(20)
        result = self.game.hit_player(e, p, 40)
        full = result['damage']
        p.hp = p.max_hp; p.bulwark_until = p.ward_until = self.clock()+90
        self.game.combat_rng = Dice(20)
        reduced = self.game.hit_player(e, p, 40)
        self.assertAlmostEqual(reduced['damage'], round(full*.5*.88, 1))
        self.assertEqual(full, sum(result['damage_rolls'])+result['damage_modifier'])

    async def test_old_items_and_shared_deadline_survive_reload_with_bounded_defenses(self):
        ws, p, _ = await self.connect('OldSaveDice')
        e = self.arena(p)
        p.level = 150
        armor = core.make_item('cloth'); p.inventory.append(armor); p.equipment['armor'] = armor['uid']
        armor['armor'] = armor['ac_bonus'] = 99999  # instance overrides never affect canonical defense
        self.assertLess(p.armor_class, 40)
        expected = (p.level, p.armor_class, p.attack_bonus, dict(p.equipment))
        self.game.combat_rng = Dice(19)
        await self.command(ws, 'attack', enemy_id=e.id)
        deadline = p.attack_cooldown_until
        for item in p.inventory:
            item.pop('ac_bonus', None); item.pop('attack_bonus', None)
        self.game.persist()
        await self.restart()
        ws, p, _ = await self.connect('OldSaveDice', create=False)
        self.assertEqual((p.level, p.armor_class, p.attack_bonus, p.equipment), expected)
        self.assertEqual(p.attack_cooldown_until, deadline)
        self.assertEqual(self.state(p)['action_remaining'], 3)
        self.assertTrue(all('ac_bonus' in i and 'attack_bonus' in i for i in p.inventory))
        _, spectator, _ = await self.connect('RollPrivacy')
        other = next(q for q in self.game.snapshot(spectator)['players'] if q['id']==p.id)
        self.assertNotIn('last_roll', other); self.assertNotIn('action_remaining', other)
