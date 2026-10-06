"""Elemental Fury through actual Game spell/weapon/PvP/save/profile pipelines."""
import copy
import unittest
from unittest.mock import patch
import test_dnd as base
from server.server import Game, make_item
from server import caster_rules as caster, combat_rules as rules, druid_circles as circles
from server import dnd_content as dnd, elemental_fury as fury, spell_scaling


class ElementalFuryTests(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy

    def setUp(self):
        self.clock = base.Clock()
        self.g = Game(':memory:', clock=self.clock)
        self.g.combat_rng = base.Dice(15, 4)
        for e in self.g.enemies.values(): e.alive = False; e.respawn_at = 0
        self.g.legacy_enemies = []
        self.addCleanup(self.g.db.close)

    def druid(self, level=7, choice='', pid='1'):
        p = self.player('druid', level, pid)
        p.elemental_fury = choice
        p.elemental_damage_type = 'cold'
        return p

    def advance(self):
        self.clock.advance(3.1)
        for p in self.g.players.values(): p.current_wall_time = self.clock()

    def hit(self, p, e):
        return self.g.hit_enemy(p, e, melee=rules.gear.melee(p))

    async def test_class_choice_pending_at_seven_and_no_asi_spent(self):
        p = self.druid(6)
        self.assertFalse(caster.sheet(p)['elemental_fury']['pending'])
        await self.g.choose_elemental_fury(p, 'potent_spellcasting')
        self.assertEqual(p.elemental_fury, '')
        p.level = 7
        self.assertTrue(caster.sheet(p)['elemental_fury']['pending'])
        feats = copy.deepcopy(p.training_feats)
        build = copy.deepcopy(p.ability_build)
        await self.g.choose_elemental_fury(p, 'potent_spellcasting')
        self.assertEqual(p.elemental_fury, 'potent_spellcasting')
        self.assertFalse(caster.sheet(p)['elemental_fury']['pending'])
        self.assertEqual((p.training_feats, p.ability_build), (feats, build))
        await self.g.choose_elemental_fury(p, 'primal_strike')
        self.assertEqual(p.elemental_fury, 'potent_spellcasting')

    async def test_wrong_class_malformed_combat_form_and_disabled_choices(self):
        p = self.druid()
        for key in ([], {}, None, 'other'):
            await self.g.choose_elemental_fury(p, key)
        for state in ('combat', 'pvp', 'form', 'stun'):
            if state == 'combat': p.combat_until = self.clock()+5
            elif state == 'pvp': p.pvp_combat_until = self.clock()+5
            elif state == 'form': p.form = 'wolf'
            else: p.buffs['stunned'] = dict(until=self.clock()+5)
            await self.g.choose_elemental_fury(p, 'primal_strike')
            self.assertEqual(p.elemental_fury, '', state)
            p.combat_until = p.pvp_combat_until = 0; p.form = ''; p.buffs.clear()
        for cls in ('knight', 'ranger', 'mage'):
            q = self.player(cls, 20, cls)
            await self.g.choose_elemental_fury(q, 'primal_strike')
            self.assertEqual(getattr(q, 'elemental_fury', ''), '')
        p.elemental_fury = ['malformed']; p.elemental_damage_type = {}
        fury.sanitize(p)
        self.assertEqual((p.elemental_fury, p.elemental_damage_type), ('', 'cold'))

    def test_potent_actual_cantrip_critical_adds_wisdom_once_not_weapon_or_spell(self):
        p = self.druid(choice='potent_spellcasting'); e = self.enemy()
        wisdom = rules.ability_modifier(p, 'wisdom')
        spec = spell_scaling.resolve(p, 'starry_wisp')
        self.assertEqual(spec['dice'], [2, 8, wisdom])
        self.g.combat_rng = base.Dice(20, 4)
        result = self.g.spell_damage(p, e, spec)
        self.assertTrue(result['critical'])
        self.assertEqual(result['damage'], 4*4+wisdom)
        self.assertEqual(len(result['damage_rolls']), 4)
        self.assertEqual(spell_scaling.resolve(p, 'moonbeam')['dice'][2], 0)
        self.assertEqual(spell_scaling.resolve(p, 'healing_word')['dice'][2], wisdom)
        p.buffs['shillelagh'] = dict(until=self.clock()+60)
        held = rules.weapon_dice(p)
        p.elemental_fury = ''
        self.assertEqual(rules.weapon_dice(p), held)
        self.assertEqual(dnd.SPELLS['starry_wisp']['dice'], [1, 8, 0])

    def test_circle_bonus_cantrips_count_as_druid_cantrips_and_success_save_zero(self):
        p = self.druid(choice='potent_spellcasting')
        p.druid_circle = 'land'; p.druid_circle_state = dict(land='arid')
        wisdom = rules.ability_modifier(p, 'wisdom')
        self.assertEqual(spell_scaling.resolve(p, 'fire_bolt')['dice'], [2, 10, wisdom])
        p.druid_circle_state['land'] = 'tropical'
        e = self.enemy()
        spec = spell_scaling.resolve(p, 'acid_splash')
        self.g.combat_rng = base.Dice(20, 4)
        result = self.g.spell_damage(p, e, spec)
        self.assertTrue(result['saved']); self.assertEqual(result['damage'], 0)
        # Verify the common damage resolver also halves the Wisdom modifier
        # with a half-damage save; Acid Splash itself does not grant this option.
        spec = dict(spec, save_half=True)
        result = self.g.spell_damage(p, e, spec)
        self.assertEqual(result['damage'], (8+wisdom)//2)

    def test_improved_range_checks_official_spell_range_and_actual_targeting(self):
        p = self.druid(14, 'potent_spellcasting')
        e = self.enemy(x=p.x+500, y=p.y)
        with patch.object(self.g, 'line_clear', return_value=True):
            self.assertEqual(self.g.spell_targets(p, spell_scaling.resolve(p, 'thorn_whip'), e.id), [])
            p.level = 15
            spec = spell_scaling.resolve(p, 'thorn_whip')
            self.assertEqual(spec['range'], dnd.SPELLS['thorn_whip']['range']+1920)
            self.assertEqual(self.g.spell_targets(p, spec, e.id), [e])
        self.assertEqual(spell_scaling.resolve(p, 'produce_flame')['range'], dnd.SPELLS['produce_flame']['range'])
        self.assertEqual(spell_scaling.resolve(p, 'shillelagh')['range'], dnd.SPELLS['shillelagh']['range'])
        p.druid_circle = 'land'; p.druid_circle_state = dict(land='temperate')
        self.assertEqual(spell_scaling.resolve(p, 'shocking_grasp')['range'], dnd.SPELLS['shocking_grasp']['range'])
        p.druid_circle_state['land'] = 'arid'
        self.assertEqual(spell_scaling.resolve(p, 'fire_bolt')['range'], dnd.SPELLS['fire_bolt']['range']+1920)
        profile = spell_scaling.client_profiles(p)['fire_bolt']
        self.assertEqual(profile['range'], dnd.SPELLS['fire_bolt']['range']+1920)
        self.assertIn('+300 stóp', profile['power_summary'])

    def test_primal_once_own_turn_miss_spell_offturn_and_multiattack(self):
        p = self.druid(choice='primal_strike'); e = self.enemy()
        self.g.begin_action(p)
        saved_damage = dict(hit=True, check='save', damage=10, damage_dice='2k8')
        self.g.circle_adjust_damage(p, e, saved_damage, weapon=True)
        self.assertNotIn('elemental_strike_rolls', saved_damage)
        self.g.combat_rng = base.Dice(1, 4)
        self.assertNotIn('elemental_strike_rolls', self.hit(p, e))
        self.g.combat_rng = base.Dice(15, 4)
        self.assertNotIn('elemental_strike_rolls', self.g.spell_damage(p, e, spell_scaling.resolve(p, 'starry_wisp')))
        first = self.hit(p, e); second = self.hit(p, e)
        self.assertEqual(first['elemental_strike_rolls'], [4])
        self.assertNotIn('elemental_strike_rolls', second)
        self.advance()
        self.assertNotIn('elemental_strike_rolls', self.hit(p, e))
        self.g.begin_action(p)
        p._off_turn_attack = True
        self.assertNotIn('elemental_strike_rolls', self.hit(p, e))
        p._off_turn_attack = False
        self.assertEqual(self.hit(p, e)['elemental_strike_rolls'], [4])
        self.advance(); self.g.begin_action(p)
        p.form = 'giant_scorpion'; p.form_until = self.clock()+90
        results = []
        for index in range(3):
            p.form_attack_index = index
            results.append(self.hit(p, e))
        self.assertEqual(sum('elemental_strike_rolls' in r for r in results), 1)
        self.assertEqual(results[0]['elemental_strike_rolls'], [4])
        self.assertTrue(any(c['type'] == 'poison' for c in results[2]['damage_components']))

    async def test_real_beast_attack_action_opens_one_turn_for_all_attacks(self):
        p = self.druid(choice='primal_strike'); e = self.enemy(x=p.x+50, y=p.y)
        p.druid_circle = 'moon'; p.form = 'bear'; p.form_until = self.clock()+90
        with patch.object(self.g, 'in_safe', return_value=False), patch.object(self.g, 'line_clear', return_value=True):
            await self.g.dnd_attack(p, enemy_id=e.id)
            self.assertEqual(len(p.combat_log), 2)
            self.assertEqual(sum('elemental_strike_rolls' in r for r in p.combat_log), 1)
            self.assertGreater(p._feat_turn_until, self.clock())
            self.advance()
            await self.g.dnd_attack(p, enemy_id=e.id)
        self.assertEqual(sum('elemental_strike_rolls' in r for r in p.combat_log), 2)

    def test_primal_critical_and_improved_two_dice_resisted_separately_pve(self):
        p = self.druid(15, 'primal_strike'); e = self.enemy()
        self.g.begin_action(p); self.g.combat_rng = base.Dice(20, 4)
        with patch.dict(rules.content.ENEMIES[e.kind], resistances=['cold']):
            result = self.hit(p, e)
        self.assertEqual(result['elemental_strike_rolls'], [4, 4, 4, 4])
        components = result['damage_components']
        self.assertEqual(components[-1], dict(type='cold', damage=16))
        self.assertEqual(result['damage'], components[0]['damage']+8)

    def test_primal_pvp_resistance_is_component_specific_and_critical_preserved(self):
        p = self.druid(15, 'primal_strike'); q = self.player('ranger', 15, '2')
        p.pvp_safety = False
        q.buffs['resist_fire'] = dict(until=self.clock()+20)
        p.elemental_damage_type = 'fire'
        self.g.begin_action(p); self.g.combat_rng = base.Dice(20, 4)
        with patch.object(self.g, 'in_safe', return_value=False):
            result = self.g.hit_player(p, q, pvp=True, melee=True)
        self.assertTrue(result['critical'])
        self.assertEqual(result['elemental_strike_rolls'], [4, 4, 4, 4])
        self.assertEqual(result['damage'], result['damage_components'][0]['damage']+8)

    async def test_damage_type_change_in_form_combat_does_not_reset_own_turn(self):
        p = self.druid(choice='primal_strike'); e = self.enemy()
        p.form = 'wolf'; p.form_until = self.clock()+60
        p.combat_until = self.clock()+10; self.g.begin_action(p)
        first = self.hit(p, e)
        for bad in ([], {}, None, 'necrotic'):
            await self.g.select_elemental_damage_type(p, bad)
            self.assertEqual(p.elemental_damage_type, 'cold')
        await self.g.select_elemental_damage_type(p, 'thunder')
        self.assertEqual(p.elemental_damage_type, 'thunder')
        self.assertEqual(first['elemental_damage_type'], 'cold')
        self.assertNotIn('elemental_strike_rolls', self.hit(p, e))
        self.advance(); self.g.begin_action(p)
        self.assertEqual(self.hit(p, e)['elemental_damage_type'], 'thunder')

    async def test_optional_strike_can_wait_for_later_hit_without_resetting_use(self):
        p = self.druid(choice='primal_strike'); e = self.enemy()
        self.g.begin_action(p)
        for bad in (None, [], {}, 1, 'false'):
            await self.g.set_elemental_strike_enabled(p, bad)
            self.assertTrue(fury.sheet(p)['strike_enabled'])
        await self.g.set_elemental_strike_enabled(p, False)
        self.assertFalse(fury.sheet(p)['strike_enabled'])
        self.assertNotIn('elemental_strike_rolls', self.hit(p, e))
        await self.g.set_elemental_strike_enabled(p, True)
        self.assertEqual(self.hit(p, e)['elemental_strike_rolls'], [4])
        await self.g.set_elemental_strike_enabled(p, False)
        await self.g.set_elemental_strike_enabled(p, True)
        self.assertNotIn('elemental_strike_rolls', self.hit(p, e))
        p.druid_circle_state['elemental_strike_enabled'] = False
        q = self.g.load_player(p.id, p.name, p.ws, p.save_data())
        self.assertFalse(fury.sheet(q)['strike_enabled'])

    def test_save_reload_preserves_choice_type_and_same_turn_rider_limit(self):
        p = self.druid(choice='primal_strike'); e = self.enemy()
        p.elemental_damage_type = 'lightning'; self.g.begin_action(p)
        self.hit(p, e)
        saved = p.save_data()
        self.assertEqual(saved['elemental_fury'], 'primal_strike')
        self.assertEqual(saved['elemental_damage_type'], 'lightning')
        q = self.g.load_player(p.id, p.name, p.ws, saved)
        self.assertEqual((q.elemental_fury, q.elemental_damage_type), ('primal_strike', 'lightning'))
        self.assertNotIn('elemental_strike_rolls', self.hit(q, e))
        self.advance(); self.g.begin_action(q)
        self.assertEqual(self.hit(q, e)['elemental_damage_type'], 'lightning')


if __name__ == '__main__': unittest.main()
