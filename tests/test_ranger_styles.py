"""Real ranger choices, spell casts, equipment and shared defensive reactions."""
import json
import unittest
from unittest.mock import patch

import test_dnd as base
from server.server import Player, make_item, ITEMS
from server import combat_rules as rules, dnd_content as dnd, fighter_rules as fighter, ranger_styles as styles, spell_scaling, weapon_actions


class SequenceDice(base.Dice):
    def __init__(self, checks, die=3):
        super().__init__(10, die)
        self.values = iter(checks)
    def randint(self, a, b):
        if b == 20:
            self.checks += 1
            return next(self.values, 10)
        return min(b, max(a, self.die))


class RangerStyleRules(unittest.TestCase):
    def test_choices_unlock_at_two_without_altering_warrior_catalogue(self):
        expected = {'archery', 'blind_fighting', 'defense', 'dueling', 'great_weapon',
                    'interception', 'protection', 'thrown_weapon', 'two_weapon', 'unarmed', 'druidic_warrior'}
        self.assertEqual(set(styles.RANGER_STYLES), expected)
        self.assertEqual(set(fighter.STYLES), {'dueling', 'defense', 'great_weapon'})
        for level, pending in ((1, False), (2, True), (21, True)):
            sheet = fighter.class_sheet(Player('r', 'R', class_id='ranger', level=level))
            self.assertEqual(sheet['pending'], pending)
            self.assertEqual(sheet['required_level'], 2)
            self.assertFalse(sheet['can_change_style'])
        self.assertEqual(fighter.class_sheet(Player('d', 'D', class_id='druid')), {})

    def test_druidic_warrior_grants_only_two_chosen_cantrips(self):
        p = Player('r', 'R', class_id='ranger', level=7)
        for key in styles.available_cantrips():self.assertFalse(dnd.spell_allowed(p, key))
        p.fighting_style = 'druidic_warrior'
        p.ranger_style_cantrips = ['starry_wisp', 'guidance']
        self.assertTrue(dnd.spell_allowed(p, 'guidance'))
        self.assertTrue(dnd.spell_allowed(p, 'starry_wisp'))
        self.assertFalse(dnd.spell_allowed(p, 'thorn_whip'))
        self.assertFalse(dnd.spell_allowed(p, 'circle_star_archer'))
        self.assertFalse(dnd.spell_allowed(p, 'wild_shape_wolf'))
        p.level = 1
        self.assertFalse(dnd.spell_allowed(p, 'starry_wisp'))

    def test_ranger_cantrips_have_free_scaling_and_wisdom_without_fury(self):
        for level, count in ((2, 1), (4, 1), (5, 2), (10, 2), (11, 3), (16, 3), (17, 4), (25, 4)):
            p = Player('r', 'R', class_id='ranger', level=level, fighting_style='druidic_warrior')
            p.ranger_style_cantrips = ['starry_wisp', 'thorn_whip']
            p.elemental_fury = 'potent_spellcasting'  # hostile/corrupted cross-class data
            for key, sides in (('starry_wisp', 8), ('thorn_whip', 6)):
                spec = spell_scaling.resolve(p, key)
                self.assertEqual(spec['dice'], [count, sides, 0])
                self.assertEqual(spec['mana'], 0)
                self.assertEqual(spec['cast_circle'], 0)
            self.assertEqual(rules.spell_ability(p), 'wisdom')


class RangerStyleGame(unittest.IsolatedAsyncioTestCase):
    setUp = base.GameRules.setUp
    tearDown = base.GameRules.tearDown
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    account = base.GameRules.account

    def ranger(self, level=2):
        self.p = self.player('ranger', level)
        return self.p

    def wear(self, p, key, slot='weapon'):
        item = make_item(key)
        p.inventory.append(item)
        p.equipment[slot] = item['uid']
        return item

    def advance(self, seconds=3.1):
        self.clock.advance(seconds)
        self.g.time += seconds
        for p in self.g.players.values():p.current_wall_time = self.clock()

    def ally(self, cls='mage', level=3):
        ally = self.player(cls, level, '2')
        self.p.party_id = ally.party_id = 'test_party'
        ally.x = self.p.x+12
        ally.y = self.p.y
        return ally

    def defensive_style(self, key):
        p = self.ranger()
        p.fighting_style = key
        self.wear(p, 'training_dagger')
        self.wear(p, 'fighter_shield', 'shield')
        return p

    async def test_selection_is_level_gated_separate_and_one_time(self):
        p = self.ranger(1)
        await self.g.select_fighting_style(p, 'archery')
        self.assertEqual(p.fighting_style, '')
        p.level = 2
        points = dict(p.mastery)
        feats = dict(p.training_feats)
        await self.g.on_packet(p.ws, {'type':'fighting_style', 'style':'archery'})
        self.assertEqual(p.fighting_style, 'archery')
        self.assertEqual(p.mastery, points)
        self.assertEqual(p.training_feats, feats)
        for key in ('defense', 'archery', {}, None, 'fake'):
            await self.g.select_fighting_style(p, key)
        self.assertEqual(p.fighting_style, 'archery')
        self.assertFalse(fighter.class_sheet(p)['pending'])

    async def test_druidic_choice_validates_exact_two_and_copies_input(self):
        p = self.ranger()
        for picks in (None, [], ['starry_wisp'], ['starry_wisp','starry_wisp'],
                      ['fire_bolt','starry_wisp'], ['starry_wisp', {}], ['starry_wisp','thorn_whip','guidance']):
            await self.g.select_fighting_style(p, 'druidic_warrior', picks)
            self.assertEqual(p.fighting_style, '')
            self.assertEqual(p.ranger_style_cantrips, [])
        picks = ['starry_wisp','thorn_whip']
        await self.g.select_fighting_style(p, 'druidic_warrior', picks)
        picks[0] = 'fire_bolt'
        self.assertEqual(p.ranger_style_cantrips, ['starry_wisp','thorn_whip'])
        self.assertIn('starry_wisp', p.hotbar)
        self.assertIn('thorn_whip', p.hotbar)
        self.assertNotIn('produce_flame', p.hotbar)

    async def test_one_cantrip_replacement_per_gained_level_survives_reload(self):
        p = self.ranger()
        await self.g.select_fighting_style(p, 'druidic_warrior', ['starry_wisp','thorn_whip'])
        await self.g.replace_ranger_cantrip(p, 'thorn_whip', 'produce_flame')
        self.assertIn('thorn_whip', p.ranger_style_cantrips)
        p.level = 3
        self.assertTrue(fighter.class_sheet(p)['cantrip_replacement_available'])
        for old, new in (('fire_bolt','guidance'), ('thorn_whip','starry_wisp'), ('thorn_whip', {})):
            await self.g.replace_ranger_cantrip(p, old, new)
        await self.g.on_packet(p.ws, {'type':'ranger_cantrip', 'old_spell':'thorn_whip', 'new_spell':'produce_flame'})
        self.assertEqual(p.ranger_style_cantrips, ['starry_wisp','produce_flame'])
        self.assertNotIn('thorn_whip', p.hotbar)
        self.assertIn('produce_flame', p.hotbar)
        await self.g.replace_ranger_cantrip(p, 'produce_flame', 'guidance')
        self.assertEqual(p.ranger_style_cantrips, ['starry_wisp','produce_flame'])
        data = json.loads(json.dumps(p.save_data()))
        q = self.g.load_player(p.id, p.name, base.WS(), data)
        self.assertEqual(q.fighting_style, 'druidic_warrior')
        self.assertEqual(q.ranger_style_cantrips, p.ranger_style_cantrips)
        self.assertEqual(q.ranger_cantrip_replacement_level, 3)
        self.assertFalse(styles.can_replace_cantrip(q))
        q.level = 4
        self.assertTrue(styles.can_replace_cantrip(q))

    async def test_combat_death_and_form_block_choices_without_spending(self):
        p = self.ranger()
        for field, value in (('combat_until', self.clock()+10), ('hp', 0), ('form', 'wolf')):
            old = getattr(p, field)
            setattr(p, field, value)
            await self.g.select_fighting_style(p, 'archery')
            self.assertEqual(p.fighting_style, '')
            setattr(p, field, old)

    async def test_archery_changes_weapon_roll_not_spell_roll_or_thrown_melee_weapon(self):
        p = self.ranger()
        base_bonus = rules.attack_bonus(p)
        spell_bonus = rules.spell_bonus(p)
        await self.g.select_fighting_style(p, 'archery')
        self.assertEqual(rules.attack_bonus(p), base_bonus+2)
        self.assertEqual(rules.spell_bonus(p), spell_bonus)
        result = self.g.hit_enemy(p, self.e)
        self.assertEqual(result['bonus'], base_bonus+2)
        dagger = self.wear(p, 'training_dagger')
        with weapon_actions.attack_context(p, ITEMS['training_dagger'], attack_mode='throw'):
            self.assertEqual(styles.attack_bonus(p), 0)
        p.weapon_attack_mode = 'unarmed'
        self.assertEqual(styles.attack_bonus(p), 0)

    async def test_defense_dueling_and_great_weapon_use_actual_gear(self):
        p = self.ranger()
        p.fighting_style = 'defense'
        self.wear(p, 'fighter_chain_mail', 'armor')
        with_style = p.armor_class
        p.fighting_style = ''
        self.assertEqual(p.armor_class, with_style-1)
        p.fighting_style = 'defense'
        self.wear(p, 'cloth', 'armor')
        self.assertFalse(fighter.style_active(p))
        self.wear(p, 'training_dagger')
        p.fighting_style = 'dueling'
        self.assertEqual(rules.weapon_dice(p)[2], rules.ability_modifier(p, 'dexterity')+2)
        self.wear(p, 'training_dagger', 'offhand')
        self.assertFalse(fighter.style_active(p))
        p.equipment['offhand'] = ''
        self.wear(p, 'training_greatsword')
        p.equipment['shield'] = ''
        p.fighting_style = 'great_weapon'
        self.g.combat_rng = base.Dice(20, 1)
        result = self.g.hit_enemy(p, self.e, melee=True)
        self.assertEqual(result['raw_damage_rolls'], [1]*4)
        self.assertEqual(result['damage_rolls'], [3]*4)
        self.assertEqual(result['damage'], 12+rules.ability_modifier(p, 'strength'))

    async def test_great_weapon_floors_attack_rider_dice_but_not_cantrips(self):
        p = self.ranger()
        self.wear(p, 'training_greatsword')
        p.fighting_style = 'great_weapon'
        p.concentration = 'hunters_mark'
        p.concentration_until = self.clock()+30
        p.mark_target = self.e.id
        self.g.combat_rng = base.Dice(20, 1)
        result = self.g.hit_enemy(p, self.e, melee=True)
        self.assertEqual(result['damage_rolls'], [3]*4)
        self.assertEqual(result['mark_rolls'], [3, 3])
        self.assertEqual(result['damage'], 18+rules.ability_modifier(p, 'strength'))
        p.mark_target = ''
        result = self.g.hit_enemy(p, self.e, dice=(1,8,0), spell=True, damage_kind='radiant')
        self.assertEqual(result['damage_rolls'], [1,1])
        self.assertEqual(result['damage'], 2)

    async def test_blind_fighting_perceives_only_within_ten_feet_and_not_walls(self):
        p = self.ranger()
        p.fighting_style = 'blind_fighting'
        self.wear(p, 'training_dagger')
        p.buffs['blind'] = dict(until=self.clock()+30)
        self.e.x = p.x+64
        self.e.y = p.y
        self.e.conditions['blur'] = dict(until=self.clock()+30)
        self.assertTrue(self.g.environment_can_see(p, self.e))
        result = self.g.hit_enemy(p, self.e, melee=True)
        self.assertFalse(result['disadvantage'])
        self.e.x += 1
        self.assertFalse(self.g.environment_can_see(p, self.e))
        result = self.g.hit_enemy(p, self.e, melee=True)
        self.assertTrue(result['disadvantage'])
        self.e.x -= 1
        with patch.object(self.g, 'line_clear', return_value=False):
            self.assertFalse(self.g.environment_can_see(p, self.e))
        p.form = 'wolf'
        self.assertEqual(styles.blindsight(p), 0)

    async def test_thrown_and_two_weapon_bonuses_require_selected_style_and_attack_mode(self):
        p = self.ranger()
        dagger = self.wear(p, 'training_dagger')
        p.fighting_style = 'thrown_weapon'
        ordinary = rules.weapon_dice(p)
        p.weapon_attack_mode = 'throw'
        self.assertEqual(rules.weapon_dice(p)[2], ordinary[2]+2)
        p.fighting_style = 'archery'
        self.assertEqual(rules.weapon_dice(p)[2], ordinary[2])
        p.weapon_attack_mode = 'weapon'
        other = self.wear(p, 'training_dagger', 'offhand')
        actual = dict(ITEMS['training_dagger'], uid=other['uid'])
        with weapon_actions.attack_context(p, actual, offhand=True):
            self.assertEqual(rules.weapon_dice(p)[2], 0)
            p.fighting_style = 'two_weapon'
            self.assertEqual(rules.weapon_dice(p)[2], rules.ability_modifier(p, 'dexterity'))
        p.fighting_style = 'unarmed'
        p.weapon_attack_mode = 'unarmed'
        self.assertEqual(rules.weapon_dice(p), (1,6,rules.ability_modifier(p,'strength')))
        p.equipment['weapon'] = p.equipment['offhand'] = p.equipment['shield'] = ''
        self.assertEqual(rules.weapon_dice(p), (1,8,rules.ability_modifier(p,'strength')))
        p.fighting_style = 'archery'
        self.assertEqual(rules.weapon_dice(p), (0,1,1+rules.ability_modifier(p,'strength')))

    async def test_druidic_real_cast_pve_pvp_and_shillelagh_use_wisdom(self):
        p = self.ranger(5)
        await self.g.select_fighting_style(p, 'druidic_warrior', ['starry_wisp','shillelagh'])
        mana = p.mana
        self.g.combat_rng = base.Dice(10, 4)
        await self.g.cast_spell(p, 'starry_wisp', enemy_id=self.e.id)
        self.assertEqual(p.last_roll['damage_rolls'], [4, 4])
        self.assertEqual(p.last_roll['damage'], 8)
        self.assertEqual(p.last_roll['bonus'], rules.spell_bonus(p))
        self.assertEqual(p.mana, mana)
        self.advance()
        staff = next(k for k, item in ITEMS.items() if item.get('weapon_type') == 'quarterstaff' and item.get('min_level', 1) == 1)
        self.wear(p, staff)
        await self.g.cast_spell(p, 'shillelagh')
        self.assertEqual(rules.attack_ability(p), 'wisdom')
        self.assertEqual(rules.weapon_dice(p)[:2], (1, 10))
        self.assertEqual(rules.weapon_dice(p)[2], rules.ability_modifier(p, 'wisdom'))
        self.advance()
        target = self.player('knight', 5, '2')
        target.x = p.x+70
        p.pvp_safety = target.pvp_safety = False
        self.g.combat_rng = base.Dice(20, 4)
        await self.g.cast_spell(p, 'starry_wisp', target_id=target.id)
        self.assertEqual(p.last_roll['damage_rolls'], [4]*4)
        self.assertEqual(p.last_roll['damage'], 16)
        self.assertEqual(p.mana, mana)

    async def test_guidance_is_a_real_usable_selected_ranger_cantrip(self):
        p = self.ranger()
        await self.g.select_fighting_style(p, 'druidic_warrior', ['guidance','starry_wisp'])
        mana = p.mana
        await self.g.cast_spell(p, 'guidance')
        self.assertTrue(self.g.target_condition(p, 'guidance'))
        self.assertEqual(p.mana, mana)
        self.assertEqual(p.concentration, 'guidance')

    async def test_protection_changes_roll_and_covers_later_attacks_until_leaving(self):
        p = self.defensive_style('protection')
        ally = self.ally()
        self.g.combat_rng = SequenceDice([18, 1])
        first = self.g.hit_player(self.e, ally)
        self.assertFalse(first['hit'])
        self.assertTrue(first['disadvantage'])
        self.assertEqual(p.reaction_ready, self.clock()+3)
        self.g.combat_rng = SequenceDice([18, 1])
        second = self.g.hit_player(self.e, ally)
        self.assertFalse(second['hit'])
        self.assertTrue(second['disadvantage'])
        p.x -= 40
        self.g.ranger_tick_protection(ally)
        p.x += 40
        self.g.combat_rng = SequenceDice([18, 1])
        third = self.g.hit_player(self.e, ally)
        self.assertTrue(third['hit'])
        self.assertFalse(third['disadvantage'])

    async def test_protection_rejects_self_stranger_range_walls_and_unseen_attacker(self):
        p = self.defensive_style('protection')
        ally = self.ally()
        self.assertFalse(self.g.ranger_protection(self.e, p))
        ally.party_id = 'stranger'
        self.assertFalse(self.g.ranger_protection(self.e, ally))
        ally.party_id = p.party_id
        ally.x = p.x+33
        self.assertFalse(self.g.ranger_protection(self.e, ally))
        ally.x = p.x+12
        with patch.object(self.g, 'line_clear', return_value=False):
            self.assertFalse(self.g.ranger_protection(self.e, ally))
        p.buffs['blind'] = dict(until=self.clock()+3)
        self.assertFalse(self.g.ranger_protection(self.e, ally))
        self.assertEqual(p.reaction_ready, 0)

    async def test_interception_reduces_components_before_resistance_and_shared_reaction(self):
        p = self.defensive_style('interception')
        ally = self.ally('druid')
        ally.buffs['stoneskin'] = dict(until=self.clock()+60)
        self.g.combat_rng = base.Dice(10, 3)
        start = ally.hp
        result = dict(check='attack', hit=True, roll=10, total=20, bonus=10, defense=10,
                      damage=18, damage_type='piercing', damage_rolls=[4,4], damage_modifier=3,
                      damage_components=[dict(type='piercing', damage=11), dict(type='force', damage=7)])
        self.g.resolve_player_hit(self.e, ally, result, 'Test')
        self.assertEqual(result['intercepted'], 5)
        self.assertEqual(result['damage_components'], [dict(type='piercing', damage=6), dict(type='force', damage=7)])
        self.assertEqual(start-ally.hp, 10)
        self.assertEqual(p.reaction_ready, self.clock()+3)
        another = dict(check='attack', hit=True, damage=10)
        self.assertFalse(self.g.ranger_interception(self.e, ally, another))
        self.assertEqual(another['damage'], 10)

    async def test_interception_never_spends_reaction_for_save_miss_or_zero_damage(self):
        p = self.defensive_style('interception')
        ally = self.ally()
        for result in (dict(check='save', hit=True, damage=10), dict(check='attack', hit=False, damage=10),
                       dict(check='attack', hit=True, damage=0)):
            self.assertFalse(self.g.ranger_interception(self.e, ally, result))
            self.assertEqual(p.reaction_ready, 0)
        p.buffs['no_reactions'] = dict(until=self.clock()+3)
        self.assertFalse(self.g.ranger_interception(self.e, ally, dict(check='attack',hit=True,damage=10)))

    async def test_style_reaction_can_be_disabled_without_changing_choice(self):
        p = self.defensive_style('protection')
        ally = self.ally()
        await self.g.on_packet(p.ws, {'type':'style_reaction', 'enabled':False})
        self.assertFalse(self.g.ranger_protection(self.e, ally))
        self.assertEqual(p.fighting_style, 'protection')
        await self.g.on_packet(p.ws, {'type':'style_reaction', 'enabled':True})
        self.assertTrue(self.g.ranger_protection(self.e, ally))

    async def test_protection_expires_on_next_guard_turn_token(self):
        p = self.defensive_style('protection')
        ally = self.ally()
        rules.begin_feat_turn(p, self.clock())
        self.assertTrue(self.g.ranger_protection(self.e, ally))
        old_turn = p._feat_turn_until
        # Beginning the next turn invalidates the old benefit even if its
        # three-second fallback has not elapsed; no unused reaction is granted.
        p._feat_turn_until = old_turn+3
        self.g.ranger_tick_protection(ally)
        self.assertNotIn('ranger_protection', ally.buffs)
        self.assertFalse(self.g.ranger_protection(self.e, ally))

    async def test_pvp_defense_joins_support_without_starting_an_autoattack(self):
        p = self.defensive_style('protection')
        ally = self.ally()
        source = self.player('knight', 3, '3')
        source.x = p.x+65
        p.pvp_safety = ally.pvp_safety = source.pvp_safety = False
        self.g.combat_rng = SequenceDice([18, 1])
        result = self.g.hit_player(source, ally, pvp=True, melee=True)
        self.assertIsNotNone(result)
        self.assertTrue(result['disadvantage'])
        self.assertFalse(result['hit'])
        self.assertGreater(p.pvp_combat_until, self.clock())
        self.assertFalse(p.auto_enabled)
        self.assertEqual(p.auto_target_id, '')
        self.assertGreater(source.aggressors.get(p.id, 0), self.clock())

    async def test_protection_and_interception_support_owned_companions(self):
        from server.dnd_game import Companion
        p = self.defensive_style('protection')
        pet = Companion('pet_'+p.id, p.id, 'Pet', p.x+12, p.y, p.floor, 30, 30, 4, 13, (1,8,2))
        self.assertTrue(self.g.ranger_protection(self.e, pet))
        self.advance()
        p.fighting_style = 'interception'
        result = dict(check='attack', hit=True, damage=12, damage_type='piercing')
        self.assertTrue(self.g.ranger_interception(self.e, pet, result))
        self.assertEqual(result['damage'], 7)

    async def test_incoming_hostile_pet_attack_uses_protection_and_shared_reaction(self):
        from server.dnd_game import Companion
        p = self.defensive_style('protection')
        ally = self.ally()
        attacker = self.player('ranger', 3, '3')
        attacker.x = p.x+65
        p.pvp_safety = ally.pvp_safety = attacker.pvp_safety = False
        attacker.auto_target_id = ally.id
        attacker.auto_enabled = True
        pet = Companion('pet_'+attacker.id, attacker.id, 'Hostile pet', ally.x+20, ally.y,
                        ally.floor, 30, 30, 5, 13, (1,8,2))
        self.g.companions[attacker.id] = pet
        self.g.combat_rng = SequenceDice([18, 1])
        hp = ally.hp
        self.g.tick_dnd(0)
        self.assertEqual(ally.hp, hp)
        self.assertEqual(p.reaction_ready, self.clock()+3)
        self.assertFalse(p.auto_enabled)

    async def test_consumed_reaction_and_pvp_support_persist_immediately(self):
        for index, key in enumerate(('protection', 'interception'), 11):
            with self.subTest(style=key):
                p = self.player('ranger', 2, str(index))
                self.p = p
                p.fighting_style = key
                self.wear(p, 'training_dagger')
                self.wear(p, 'fighter_shield', 'shield')
                ally = self.ally()
                source = self.player('knight', 3, '3')
                source.x = p.x+65
                p.pvp_safety = ally.pvp_safety = source.pvp_safety = False
                ally.white_until = self.clock()+120
                ally.aggressors[source.id] = self.clock()+120
                self.g.begin_pvp_hostility(source, ally)
                self.account(p)
                if key == 'protection':
                    self.assertTrue(self.g.ranger_protection(source, ally))
                else:
                    self.assertTrue(self.g.ranger_interception(source, ally, dict(check='attack', hit=True, damage=10)))
                # No explicit save/disconnect follows the reaction. Read the
                # actual account row to model an abrupt restart at this point.
                row = self.g.db.execute('SELECT data FROM accounts WHERE id=?', (p.id,)).fetchone()
                saved = json.loads(row[0])
                self.assertEqual(saved['reaction_ready'], self.clock()+3)
                self.assertEqual(saved['white_until'], p.white_until)
                self.assertGreater(saved['white_until'], self.clock())
                self.assertEqual(saved['pvp_combat_until'], p.pvp_combat_until)
                loaded = self.g.load_player(p.id, p.name, base.WS(), saved)
                self.assertEqual(loaded.reaction_ready, p.reaction_ready)
                self.assertEqual(loaded.white_until, p.white_until)
                self.assertEqual(loaded.pvp_combat_until, p.pvp_combat_until)
                self.assertFalse(self.g._ranger_guard_ready(loaded, source, ally, key))

    def test_saved_reaction_toggle_accepts_only_real_boolean(self):
        p = self.ranger()
        p.fighting_style = 'protection'
        for raw, expected in ((False, False), (True, True), ('false', True), (0, True), (None, True), ({}, True)):
            with self.subTest(raw=raw):
                p.ranger_style_reaction_enabled = raw
                styles.sanitize(p)
                self.assertIs(p.ranger_style_reaction_enabled, expected)


if __name__ == '__main__':unittest.main()
