"""Opening encounters use the easier balance through live combat paths."""
from collections import Counter
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import combat_rules as rules
from server.server import Game, Player


class Clock:
    def __init__(self):
        self.value = 1000.0

    def __call__(self):
        return self.value


class Dice:
    def __init__(self, d20=15, damage=4):
        self.d20 = d20
        self.damage = damage

    def randint(self, low, high):
        return self.d20 if high == 20 else min(high, max(low, self.damage))


class OpeningBalance(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()
        self.game = Game(':memory:', clock=self.clock)
        self.addCleanup(self.game.db.close)
        self.player = Player('1', 'OpeningTester', class_id='knight')
        self.game.starter(self.player)
        self.player.hp = self.player.max_hp
        self.player.current_wall_time = self.clock()
        self.game.players[self.player.id] = self.player

    def boss_arena(self):
        boss = self.game.enemies['boss']
        self.player.level = 10
        self.player.hp = self.player.max_hp
        self.player.x, self.player.y = boss.x, boss.y-200
        self.player.dx = self.player.dy = 0
        self.player.input_time = -10
        self.assertFalse(self.game.blocked(self.player.x, self.player.y))
        self.assertFalse(self.game.in_safe(self.player))
        self.assertTrue(self.game.line_clear(boss, self.player))
        return boss

    def resolve_attack(self):
        hazard = self.game.hazards[-1]
        hp = self.player.hp
        self.game.time = hazard['resolve']-.01
        self.clock.value = 1000+self.game.time
        self.game.resolve_hazards()
        self.assertEqual(self.player.hp, hp, 'Telegraph must precede damage')
        self.game.time = hazard['resolve']+.01
        self.clock.value = 1000+self.game.time
        self.game.resolve_hazards()
        self.assertFalse(self.game.hazards)

    def latest_roll(self):
        return next(effect for effect in reversed(self.game.effects)
                    if effect['kind'] == 'combat_roll')

    def test_runtime_starter_population_leaves_one_wisp_and_two_spiders(self):
        starters = self.game.legacy_enemies
        self.assertEqual(Counter(enemy.kind for enemy in starters), {
            'wolf': 6, 'wisp': 1, 'guardian': 3, 'boss': 1,
            'rat': 3, 'boar': 3, 'goblin': 3, 'spider': 2, 'skeleton': 3,
        })
        positions = lambda kind: {(enemy.home_x, enemy.home_y)
                                  for enemy in starters if enemy.kind == kind}
        self.assertEqual(positions('wisp'), {(2140, 1240)})
        self.assertEqual(positions('spider'), {(1840, 1900), (2120, 1740)})
        self.assertEqual(positions('rat'), {(810, 1460), (700, 1580), (910, 1660)})
        self.assertEqual(positions('boss'), {(2530, 1900)})

    def test_starter_weapon_hits_rats_and_wolves_at_the_lower_threshold(self):
        for kind, armor_class in (('rat', 8), ('wolf', 11)):
            enemy = next(enemy for enemy in self.game.legacy_enemies if enemy.kind == kind)
            self.player.x, self.player.y = enemy.x-40, enemy.y
            bonus = rules.attack_bonus(self.player)
            for total, hits in ((armor_class-1, False), (armor_class, True)):
                with self.subTest(kind=kind, total=total):
                    self.game.combat_rng = Dice(d20=total-bonus, damage=1)
                    hp = enemy.hp
                    result = self.game.hit_enemy(self.player, enemy, melee=True)
                    self.assertEqual(result['total'], total)
                    self.assertEqual(result['hit'], hits)
                    self.assertEqual(enemy.public()['armor_class'], armor_class)
                    if hits:
                        self.assertLess(enemy.hp, hp)
                    else:
                        self.assertEqual(enemy.hp, hp)

    def test_queued_boss_projectile_uses_reduced_damage(self):
        boss = self.boss_arena()
        self.game.combat_rng = Dice()
        hp = self.player.hp
        self.game.queue_enemy_attack(boss, self.player)
        self.resolve_attack()
        result = self.latest_roll()
        self.assertEqual(result['check'], 'attack')
        self.assertTrue(result['hit'])
        self.assertFalse(result['critical'])
        self.assertEqual(result['damage_dice'], '2k4+3')
        self.assertEqual(hp-self.player.hp, 11)

    def test_queued_boss_area_damage_respects_both_save_outcomes(self):
        boss = self.boss_arena()
        for d20, saved, damage in ((1, False, 15), (20, True, 7)):
            with self.subTest(saved=saved):
                self.player.hp = self.player.max_hp
                self.game.combat_rng = Dice(d20=d20)
                boss.special_count = 0
                hp = self.player.hp
                self.game.queue_enemy_attack(boss, self.player, special=True)
                self.resolve_attack()
                result = self.latest_roll()
                self.assertEqual(result['check'], 'save')
                self.assertEqual(result['saved'], saved)
                self.assertEqual(result['damage_dice'], '3k6+3')
                self.assertEqual(hp-self.player.hp, damage)

    def test_boss_projectile_and_area_aim_can_still_be_dodged(self):
        boss = self.boss_arena()
        self.game.combat_rng = Dice()
        for special in (False, True):
            with self.subTest(special=special):
                self.player.x, self.player.y = boss.x, boss.y-200
                boss.special_count = 0
                hp = self.player.hp
                self.game.queue_enemy_attack(boss, self.player, special=special)
                self.player.x += 200
                self.assertFalse(self.game.blocked(self.player.x, self.player.y))
                self.resolve_attack()
                self.assertEqual(self.player.hp, hp)


if __name__ == '__main__':
    unittest.main()
