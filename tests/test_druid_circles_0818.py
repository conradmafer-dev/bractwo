"""Focused circle rules/resource/target regression tests; no player database."""
import unittest
import test_dnd as base
from server.server import Game
from server import druid_circles as circles, dnd_content as dnd
from server.druid_circle_game import DruidCircleGame


class CircleRules(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy

    def setUp(self):
        self.clock = base.Clock()
        cls = Game if issubclass(Game, DruidCircleGame) else type('CircleHarness', (DruidCircleGame, Game), {})
        self.g = cls(':memory:', clock=self.clock)
        self.g.combat_rng = base.Dice(1, 3)
        for enemy in self.g.enemies.values(): enemy.alive = False; enemy.respawn_at = 0
        self.g.legacy_enemies = []
        circles.configure(dnd.SPELLS, dnd.STATUS_SPECS)

    def tearDown(self): self.g.db.close()

    def druid(self, circle, level=14, pid='1'):
        p = self.player('druid', level, pid)
        p.druid_circle = circle
        self.g.migrate_druid_circle(p)
        return p

    def advance(self, seconds=3.1):
        self.clock.advance(seconds)
        for p in self.g.players.values(): p.current_wall_time = self.clock()

    def test_level_mapping_and_shape_resources(self):
        p = self.druid('moon', 3)
        self.assertEqual(circles.effective_level(p), 3)
        self.assertEqual(circles.form_temp_hp(p), 9)
        self.assertEqual(circles.max_form_cr(p), 1)
        self.assertEqual(circles.shape_max(p), 2)
        self.assertTrue(circles.spend_shape(p, 2))
        self.assertFalse(circles.spend_shape(p))
        self.g.on_circle_rest(p, 'short')
        self.assertEqual(circles.shape_remaining(p), 1)
        self.g.on_circle_rest(p, 'long')
        self.assertEqual(circles.shape_remaining(p), 2)
        p.level = 18
        self.assertEqual(circles.max_form_cr(p), 6)
        self.assertEqual(circles.shape_max(p), 4)

    def test_bonus_spell_access_and_natural_recovery_commits_once(self):
        p = self.druid('land', 6)
        p.druid_circle_state.update(land='arid', natural_free_armed=True)
        self.assertIn('fireball', circles.bonus_spells(p))
        self.assertNotIn('cone_of_cold', circles.bonus_spells(p))
        spell = dict(id='fireball', circle=3, cast_circle=3, mana=50)
        cost, token = self.g.circle_spell_cost(p, spell)
        self.assertEqual((cost, token), (0, 'natural_free'))
        self.assertEqual(circles.spent(p, token), 0)
        self.g.circle_commit_spell(p, spell, token)
        self.assertEqual(self.g.circle_spell_cost(p, spell), (50, ''))
        p.mana = 0
        self.g.on_circle_rest(p, 'short'); mana = p.mana
        self.assertGreater(mana, 0)
        self.g.on_circle_rest(p, 'short')
        self.assertEqual(p.mana, mana)
        self.g.on_circle_rest(p, 'long')
        self.assertEqual(circles.spent(p, 'natural_free'), 0)

    async def test_star_dragon_and_chalice_have_real_effects(self):
        p = self.druid('stars', 10)
        await self.g.cast_circle_feature(p, 'circle_star_dragon')
        self.assertEqual(circles.roll_floor(p, 'constitution', 'concentration'), 10)
        self.assertEqual(circles.roll_floor(p, 'constitution', 'save'), 1)
        p.concentration = 'moonbeam'; p.concentration_until = self.clock()+30
        self.g.concentration_damage(p, 10)
        self.assertEqual(p.concentration, 'moonbeam')
        self.advance()
        before = circles.shape_remaining(p)
        await self.g.cast_circle_feature(p, 'circle_star_chalice')
        self.assertEqual(circles.shape_remaining(p), before)
        p.hp = 1
        self.g.circle_after_heal(p, dict(circle=1), [p], 20)
        self.assertEqual(p.hp, 1+6+circles.wisdom(p))

    async def test_land_aid_damage_heal_and_invalid_target_no_resource(self):
        p = self.druid('land', 3)
        target = self.enemy(x=p.x+25, y=p.y)
        p.hp = 1
        initial = circles.shape_remaining(p)
        await self.g.cast_circle_feature(p, 'circle_lands_aid', enemy_id='missing')
        self.assertEqual(circles.shape_remaining(p), initial)
        await self.g.cast_circle_feature(p, 'circle_lands_aid', enemy_id=target.id)
        self.assertEqual(target.hp, 999-6)
        self.assertEqual(p.hp, 7)
        self.assertEqual(circles.shape_remaining(p), initial-1)

    async def test_sea_aura_damage_and_push_share_wild_shape_resource(self):
        p = self.druid('sea', 6)
        target = self.enemy(x=p.x+20, y=p.y)
        start = target.x
        await self.g.cast_circle_feature(p, 'circle_wrath_of_sea', enemy_id=target.id)
        self.assertTrue(circles.active(p, 'wrath_of_sea'))
        self.assertLess(target.hp, 999)
        self.assertGreater(target.x, start)
        self.assertEqual(circles.spent(p, 'shape'), 1)
        self.assertTrue(circles.can_swim(p))

    async def test_moon_teleport_and_single_extra_damage_per_turn(self):
        p = self.druid('moon')
        target = self.enemy()
        start = (p.x, p.y)
        await self.g.cast_circle_feature(p, 'circle_moonlight_step')
        self.assertNotEqual((p.x, p.y), start)
        self.assertTrue(self.g.caster_attack_advantage(p, target))
        self.assertFalse(self.g.caster_attack_advantage(p, target))
        p.form = 'wolf'
        one = dict(hit=True, critical=False, damage=5, damage_type='piercing', damage_dice='1k6+2')
        self.g.circle_adjust_damage(p, target, one)
        self.assertEqual(one['damage'], 11)
        two = dict(hit=True, critical=False, damage=5, damage_type='piercing', damage_dice='1k6+2')
        self.g.circle_adjust_damage(p, target, two)
        self.assertEqual(two['damage'], 5)

    def test_omen_reaction_respects_floor_range_and_uses(self):
        p = self.druid('stars', 6)
        p.druid_circle_state.update(omen='weal', omen_armed=True)
        self.assertEqual(self.g.circle_roll_adjustment(p), 3)
        self.assertEqual(circles.spent(p, 'omen'), 1)
        self.assertEqual(self.g.circle_roll_adjustment(p), 0)
        self.advance()
        p.druid_circle_state['omen_spent'] = max(1, circles.wisdom(p))
        self.assertEqual(self.g.circle_roll_adjustment(p), 0)

    def test_higher_beast_forms_have_progressive_cr_and_actual_poison(self):
        p = self.druid('moon', 6)
        self.assertTrue(circles.form_allowed(p, 'polar_bear'))
        self.assertFalse(circles.form_allowed(p, 'giant_scorpion'))
        p.level = 9; p.form = 'giant_scorpion'; p.form_attack_index = 2
        self.assertTrue(circles.form_allowed(p, p.form))
        hit = dict(hit=True, critical=False, damage=6, damage_type='piercing', damage_dice='1k8+3')
        self.g.circle_adjust_damage(p, self.enemy(), hit)
        self.assertEqual(hit['damage'], 12)
        self.assertEqual(hit['damage_components'][-1], dict(type='poison', damage=6))
        p.druid_circle = 'land'; p.level = 20
        self.assertFalse(circles.form_allowed(p, 'polar_bear'))

    async def test_scorpion_grapple_releases_without_action(self):
        p = self.druid('moon', 9); p.form = 'giant_scorpion'; p.form_until = self.clock()+100
        target = self.enemy(x=p.x+20, y=p.y); p.form_attack_index = 0
        self.g.beast_on_hit(p, target, dict(hit=True))
        self.assertEqual(target.conditions['grappled']['dc'], 13)
        self.assertNotIn('restrained', target.conditions)
        self.assertTrue(circles.runtime(p)['grapple_slow'])
        await self.g.circle_command(p, 'release_grapples')
        self.assertNotIn('grappled', target.conditions)
        self.assertEqual(p.attack_cooldown_until, 0)


if __name__ == '__main__': unittest.main()
