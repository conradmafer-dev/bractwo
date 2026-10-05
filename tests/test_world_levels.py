"""World numbering changes must not retune authored encounters or rewards."""
from copy import deepcopy
from types import SimpleNamespace
import unittest

from server import world_levels


class WorldLevelConversion(unittest.TestCase):
    def test_shared_catalogues_convert_once_and_keep_encounter_stats(self):
        enemy = dict(level=10, hp=64, armor_class=8, xp=150, gold=28,
                     damage_dice=[1, 8, 2], special_windup=1.65,
                     loot=dict(tier=3, entries=[dict(template='ring', chance=.02)]))
        item = dict(min_level=10, value=350, enchantment=1)
        area = dict(min_level=1, recommended_level=10, max_level=12, floor=3,
                    reward=dict(xp=120, gold=50))
        content = SimpleNamespace(ENEMIES={'boss': enemy}, ITEMS={'ring': item},
                                  DUNGEONS=[area], POIS=[area],
                                  TIER_LEVELS={1:1, 2:3, 3:8, 4:20, 9:110})
        before = deepcopy(enemy)
        pvp = dict(min_level=8, white_seconds=120)
        world_levels.configure(content, [area], {'boss': enemy}, pvp)
        self.assertEqual(enemy, dict(before, level=3))
        self.assertEqual(item['min_level'], 3)
        self.assertEqual(area['recommended_level'], 3)
        self.assertEqual(area['max_level'], 3)
        self.assertEqual(area['floor'], 3)
        self.assertEqual(area['reward'], {'xp':120, 'gold':50})
        self.assertEqual(pvp, {'min_level':2, 'white_seconds':120})
        self.assertEqual(content.TIER_LEVELS, {1:1, 2:1, 3:2, 4:5, 9:23})
        world_levels.configure(content, [area], pvp)
        self.assertEqual(enemy['level'], 3)
        self.assertEqual(area['recommended_level'], 3)
        self.assertEqual(content.TIER_LEVELS[9], 23)

    def test_class_spells_and_dungeon_floors_do_not_convert(self):
        spells = {'new_spell': dict(level=3, circle=2)}
        content = SimpleNamespace(SPELLS=spells, MILESTONES=[(4, 'Atut', '')],
            LANDMARKS=[dict(name='Krypty · poziom 2 / 3', floor=-3,
                description='Zalecany poziom walki: 10; wejście jest dostępne od początku.')])
        world_levels.configure(content)
        self.assertEqual(spells['new_spell'], {'level':3, 'circle':2})
        self.assertEqual(content.MILESTONES[0][0], 4)
        self.assertEqual(content.LANDMARKS[0]['name'], 'Krypty · poziom 2 / 3')
        self.assertEqual(content.LANDMARKS[0]['floor'], -3)
        self.assertIn('walki: 3;', content.LANDMARKS[0]['description'])

    def test_requirement_prose_and_difficulty_ranges_use_the_new_units(self):
        self.assertEqual(world_levels.level_text('Łowisko poziomów 6–12. 3 mikstury.'),
                         'Łowisko poziomów 2–3. 3 mikstury.')
        self.assertEqual(world_levels.level_text('Wymaga poziomu 110. Łup z bossów poziomu 110+.'),
                         'Wymaga poziomu 23. Łup z bossów poziomu 23+.')
        point = dict(level_range=(10, 20), discovery_difficulty=dict(
            site_level=10, biome_level=20, enemy_level=0, city_distance=500))
        content = SimpleNamespace(LANDMARKS=[point])
        world_levels.configure(content)
        self.assertEqual(point['level_range'], (3, 5))
        self.assertEqual(point['discovery_difficulty'], dict(
            site_level=3, biome_level=5, enemy_level=0, city_distance=500))


if __name__ == '__main__':
    unittest.main()
