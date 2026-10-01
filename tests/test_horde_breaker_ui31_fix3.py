"""Horde Breaker: live bow/rat reproduction and one-tile neighbour regression.

Run from the project root:
    python -m unittest discover -s tests -p test_horde_breaker_ui31_fix3.py -v
No production account, database, network, or live server is used.
"""
import math
import unittest
from unittest.mock import patch

import test_dnd as base
from server.server import Game, make_item
from server import combat_rules, equipment_rules, martial_rules
from server.martial_combat import FIVE_FEET, HORDE_BREAKER_RADIUS


class AttackSequence:
    def __init__(self, rolls, die=4):
        self.rolls = iter(rolls)
        self.die = die
        self.checks = 0

    def randint(self, low, high):
        if high == 20:
            self.checks += 1
            return next(self.rolls)
        return min(high, max(low, self.die))


class HordeBreakerTests(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy

    def setUp(self):
        self.clock = base.Clock()
        self.g = Game(':memory:', clock=self.clock)
        self.g.combat_rng = base.Dice(15, 4)
        for enemy in self.g.enemies.values():
            enemy.alive = False
            enemy.respawn_at = 0
        self.g.legacy_enemies = []
        self.addCleanup(self.g.db.close)

    def hero(self, level=10, weapon=None):
        p = self.player('ranger', level)
        p.promoted = True
        p.martial_archetype = 'hunter'
        p.martial_state = {'hunter_choice': 'horde_breaker'}
        if weapon:
            item = make_item(weapon)
            p.inventory.append(item)
            p.equipment['weapon'] = item['uid']
        return p

    def pair(self, p, distance=48, hp=None, indexed=False):
        prefix = 'world_fix3_' if indexed else 'fix3_'
        a = self.enemy(prefix+'first', x=p.x+150, kind='rat')
        b = self.enemy(prefix+'second', x=a.x+distance, kind='rat')
        a.hp = a.max_hp if hp is None else hp
        b.hp = b.max_hp if hp is None else hp
        self.g.legacy_enemies = [] if indexed else [a, b]
        if indexed:
            self.g.reindex_enemy(a)
            self.g.reindex_enemy(b)
        return a, b

    def shots(self):
        return [fx for fx in self.g.effects if fx['kind'] == 'arrow']

    async def test_neighbouring_rats_die_and_both_receive_a_bow_shot(self):
        for gap in (20, 32, 40, 48, 64):
            with self.subTest(gap=gap):
                self.clock.advance(3.1)
                self.g.effects = []
                p = self.hero()
                a, b = self.pair(p, gap)
                before = self.g.combat_rng.checks
                await self.g.dnd_attack(p, enemy_id=a.id)
                self.assertFalse(a.alive)
                self.assertFalse(b.alive)
                self.assertEqual(self.g.combat_rng.checks-before, 2)
                self.assertEqual([fx['target_id'] for fx in self.shots()], [a.id, b.id])
                self.assertEqual(p.kills, 2)
                self.assertEqual(p.last_roll['action'], 'Rozbijacz hord')

    async def test_does_not_hit_beyond_one_tile_or_spend_the_extra_attack(self):
        for gap in (64.01, 65, 80, 120):
            with self.subTest(gap=gap):
                self.clock.advance(3.1)
                p = self.hero()
                a, b = self.pair(p, gap)
                await self.g.dnd_attack(p, enemy_id=a.id)
                self.assertEqual(b.hp, b.max_hp)
                self.assertEqual(p.martial_state.get('horde_until', 0), 0)

    async def test_primary_miss_can_still_produce_a_successful_second_shot(self):
        p = self.hero()
        a, b = self.pair(p)
        self.g.combat_rng = AttackSequence([1, 15])
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertEqual(a.hp, a.max_hp)
        self.assertFalse(b.alive)
        self.assertTrue(p.last_roll['hit'])
        self.assertEqual(p.last_roll['action'], 'Rozbijacz hord')

    async def test_second_shot_has_its_own_miss_and_visual_event(self):
        p = self.hero()
        a, b = self.pair(p)
        self.g.combat_rng = AttackSequence([15, 1])
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertFalse(a.alive)
        self.assertEqual(b.hp, b.max_hp)
        self.assertFalse(p.last_roll['hit'])
        self.assertEqual(p.last_roll['action'], 'Rozbijacz hord')
        self.assertEqual([fx['target_id'] for fx in self.shots()], [a.id, b.id])
        self.assertTrue(any(fx.get('mastery') == 'horde_breaker' and fx['target_id'] == b.id
                            for fx in self.g.effects))
        self.assertGreater(p.martial_state['horde_until'], self.clock())

    async def test_no_third_target_even_with_two_regular_attacks_at_level_20(self):
        p = self.hero(20)
        a, b = self.pair(p, hp=999)
        third = self.enemy('fix3_third', x=a.x+60, kind='rat')
        third.hp = third.max_hp
        before = self.g.combat_rng.checks
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertLess(a.hp, 999)
        self.assertLess(b.hp, 999)
        self.assertEqual(third.hp, third.max_hp)
        self.assertEqual(self.g.combat_rng.checks-before, 3)
        self.assertEqual(sum(fx['target_id'] == b.id for fx in self.shots()), 1)

    async def test_cooldown_does_not_extend_the_main_attack_and_renews_after_three_seconds(self):
        p = self.hero()
        a, b = self.pair(p, hp=999)
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertEqual(p.attack_cooldown_until, self.clock()+3)
        self.assertEqual(p.martial_state['horde_until'], self.clock()+3)
        hp = b.hp
        self.clock.advance(2.99)
        self.assertIsNone(self.g.martial_horde_breaker(p, a))
        self.assertEqual(b.hp, hp)
        self.clock.advance(.01)
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertLess(b.hp, hp)

    async def test_secondary_has_to_be_in_bow_range(self):
        p = self.hero()
        a, b = self.pair(p, hp=999)
        a.x = p.x+300
        b.x = p.x+320
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertLess(a.hp, 999)
        self.assertEqual(b.hp, 999)
        self.assertEqual(p.martial_state.get('horde_until', 0), 0)

    async def test_other_floor_wall_and_safe_zone_are_not_bypassed(self):
        for blocked in ('floor', 'wall', 'safe'):
            with self.subTest(blocked=blocked):
                self.clock.advance(3.1)
                p = self.hero()
                a, b = self.pair(p, hp=999)
                if blocked == 'floor':
                    b.floor = -99
                original_line = self.g.line_clear
                original_safe = self.g.in_safe
                with patch.object(self.g, 'line_clear', side_effect=lambda s, t: False if blocked == 'wall' and t is b else original_line(s, t)), \
                     patch.object(self.g, 'in_safe', side_effect=lambda t: True if blocked == 'safe' and t is b else original_safe(t)):
                    await self.g.dnd_attack(p, enemy_id=a.id)
                self.assertLess(a.hp, 999)
                self.assertEqual(b.hp, 999)
                self.assertEqual(p.martial_state.get('horde_until', 0), 0)

    async def test_spatially_indexed_world_rats_are_found(self):
        p = self.hero()
        a, b = self.pair(p, distance=48, indexed=True)
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertFalse(a.alive)
        self.assertFalse(b.alive)

    async def test_short_and_long_bow_both_qualify(self):
        for weapon in ('ranger_weapon_1', 'bandit_longbow'):
            with self.subTest(weapon=weapon):
                self.clock.advance(3.1)
                p = self.hero(weapon=weapon)
                a, b = self.pair(p)
                await self.g.dnd_attack(p, enemy_id=a.id)
                self.assertFalse(a.alive)
                self.assertFalse(b.alive)
                self.assertEqual(p.last_roll['action'], 'Rozbijacz hord')

    async def test_melee_weapon_still_requires_its_own_range(self):
        p = self.hero(weapon='knight_weapon_1')
        a, b = self.pair(p, hp=999)
        a.x, b.x = p.x+70, p.x+100
        await self.g.dnd_attack(p, enemy_id=a.id)
        self.assertLess(a.hp, 999)
        self.assertLess(b.hp, 999)
        self.assertEqual(p.last_roll['action'], 'Rozbijacz hord')

    def test_pvp_safety_party_and_uninvolved_players_remain_protected(self):
        p = self.hero()
        a, b = self.pair(p)
        b.alive = False
        q = self.player('knight', 10, '2')
        q.x = a.x+48
        for mode in ('uninvolved', 'safety', 'party', 'low_level'):
            with self.subTest(mode=mode):
                p.pvp_safety = mode == 'safety'
                p.party_id = q.party_id = 'group' if mode == 'party' else ''
                q.level = 1 if mode == 'low_level' else 10
                p.aggressors = {} if mode == 'uninvolved' else {q.id: self.clock()+20}
                self.assertIsNone(self.g.martial_horde_breaker(p, a))
        p.pvp_safety = False
        p.party_id = q.party_id = ''
        q.level = 10
        before = q.hp
        self.assertIs(self.g.martial_horde_breaker(p, a), q)
        self.assertLess(q.hp, before)

    async def test_savage_attacker_is_still_once_for_the_whole_attack_sequence(self):
        p = self.hero()
        p.origin_feat = 'savage_attacker'
        a, b = self.pair(p, hp=999)
        await self.g.dnd_attack(p, enemy_id=a.id)
        attacks = [r for r in p.combat_log if r.get('check') == 'attack']
        self.assertEqual(len(attacks), 2)
        self.assertEqual(sum(bool(r.get('savage_attacker')) for r in attacks), 1)

    def test_only_horde_neighbour_radius_changed_and_descriptions_are_plain(self):
        self.assertEqual(HORDE_BREAKER_RADIUS, 64)
        self.assertEqual(FIVE_FEET, 32)
        description = martial_rules.PREY['horde_breaker']['description']
        self.assertIn('1 pola', description)
        self.assertIn('łukiem', description)
        self.assertIn('może chybić', description)
        self.assertNotIn('stóp', description)
        tough = equipment_rules.GENERAL_FEATS['tough']['description']
        self.assertIn('5 poziomów', tough)
        self.assertNotIn('D&D', tough)
        self.assertNotIn('×', tough)

    def test_tough_description_change_does_not_change_its_health_bonus(self):
        p = self.hero()
        for level, expected in ((1, 2), (5, 4), (10, 6), (23, 10), (95, 40), (500, 40)):
            with self.subTest(level=level):
                p.level = level
                p.origin_feat = ''
                without = combat_rules.max_hp(p)
                p.origin_feat = 'tough'
                self.assertEqual(combat_rules.max_hp(p)-without, expected)
