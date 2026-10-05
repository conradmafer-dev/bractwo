"""Boss-specific mechanics and a deterministic solo difficulty budget.

Run: python -m unittest discover -s tests -p 'test_starter_boss_balance.py' -v
The small 8-seed regression is supplemented by the 40-seed CLI report.
"""
import asyncio
import unittest

import test_starter_adventures_ui33 as base
from server import starter_adventures as sa
from server.server import ENEMY_TYPES
from tools.balance_starter_bosses import CLASSES, fight, summarize


class BossRecovery(unittest.IsolatedAsyncioTestCase):
    setUp = base.StarterAdventures.setUp
    tearDown = base.StarterAdventures.tearDown
    player = base.StarterAdventures.player
    enemy = base.StarterAdventures.enemy

    def advance_monster(self, seconds):
        self.g.time = seconds
        self.clock.value = 1000+seconds
        p = self.p
        self.g.step_monsters(.05, {(p.floor, int(p.x//1024), int(p.y//1024)): [p]}, {p.id})

    def test_special_resolves_before_recovery_and_cannot_double_hit(self):
        for kind in sa.BOSSES:
            with self.subTest(boss=kind):
                self.g.time = 0
                self.clock.value = 1000
                self.g.hazards.clear()
                e = self.enemy(kind)
                p = self.p
                p.x, p.y, p.floor = e.x+50, e.y, e.floor
                p.hp = p.max_hp
                self.g.queue_enemy_attack(e, p, special=True)
                h = self.g.hazards[-1]
                hp = p.hp
                self.g.time = h['resolve']-.01
                self.g.resolve_hazards()
                self.assertEqual(p.hp, hp)
                self.g.time = h['resolve']+.01
                self.g.resolve_hazards()
                self.assertLess(p.hp, hp)
                self.assertGreater(e.cast_until, self.g.time)
                hp = p.hp
                self.g.resolve_hazards()
                self.assertEqual(p.hp, hp)

    def test_both_bosses_hold_position_and_attacks_then_resume(self):
        for kind in sa.BOSSES:
            with self.subTest(boss=kind):
                self.g.time = 0
                self.clock.value = 1000
                self.g.hazards.clear()
                e = self.enemy(kind)
                p = self.p
                p.x, p.y, p.floor = e.x+140, e.y, e.floor
                p.hp = p.max_hp
                self.g.queue_enemy_attack(e, p, special=True)
                e.aoe_ready = 100
                recovery_end = e.cast_until
                # Move behind the locked aim, outside the sweep, with real LOS.
                p.x, p.y = e.x, e.y-140
                self.assertTrue(self.g.line_clear(e, p))
                before = e.x, e.y, p.hp
                self.advance_monster(recovery_end-.01)
                self.assertEqual((e.x, e.y, p.hp), before)
                self.assertFalse(self.g.hazards)
                self.advance_monster(recovery_end+.01)
                if kind == sa.CRYPT_BOSS:
                    self.assertNotEqual((e.x, e.y), before[:2])
                else:
                    self.assertTrue(self.g.hazards, 'Archer must resume ordinary shots')

    def test_recovery_never_shortens_an_existing_cooldown(self):
        e = self.enemy(sa.CRYPT_BOSS)
        e.ready, e.ranged_ready = 20, 25
        self.g.queue_enemy_attack(e, self.p, special=True)
        self.assertEqual((e.ready, e.ranged_ready), (20, 25))

    def test_normal_arrow_keeps_its_original_windup(self):
        e = self.enemy(sa.TOWER_BOSS)
        self.g.queue_enemy_attack(e, self.p)
        self.assertEqual(e.cast_until, ENEMY_TYPES[e.kind]['windup'])
        self.assertNotIn('starter', self.g.hazards[-1])


class SoloBalance(unittest.TestCase):
    def test_level_three_starter_builds_have_comparable_encounters(self):
        async def sample():
            return [await fight(boss, cls, seed)
                    for boss in sa.BOSSES for cls in CLASSES for seed in range(8)]

        rows = summarize(asyncio.run(sample()))
        for boss in sa.BOSSES:
            encounters = [r for r in rows if r['boss'] == boss]
            with self.subTest(boss=boss):
                for row in encounters:
                    self.assertEqual(row['wins'], row['trials'], row)
                    self.assertEqual(row['timeouts'], 0, row)
                    self.assertLessEqual(row['mean_seconds'], 35, row)
                    self.assertGreaterEqual(row['mean_specials'], 1.5, row)
                times = [r['mean_seconds'] for r in encounters]
                # Permit burst/attrition identities without a 3x+ gap. This
                # fails on cf1e946 with the identical controller and seeds.
                self.assertLessEqual(max(times)/min(times), 2.5, encounters)


if __name__ == '__main__':
    unittest.main()
