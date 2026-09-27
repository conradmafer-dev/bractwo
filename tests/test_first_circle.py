"""Circle-I regression, updated for 0.8.4 mana, ten-level gates and paginated saved bars."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from aiohttp.test_utils import TestClient, TestServer
from server.server import Player, create_app
from server import dnd_content as dnd, combat_rules as rules
import test_dnd as base


class FirstCircleCatalogue(unittest.TestCase):
    def test_entire_first_circle_available_at_level_one(self):
        expected = {
            'mage': {'magic_missile', 'burning_hands', 'shield', 'mage_armor', 'longstrider','alarm','find_familiar'},
            'druid': {'cure_wounds', 'healing_word', 'entangle', 'longstrider','speak_with_animals'},
        }
        for cls, keys in expected.items():
            p = Player('1', 'Test', class_id=cls)
            actual = {k for k, s in dnd.SPELLS.items() if s['circle'] == 1 and dnd.spell_allowed(p, k)}
            self.assertEqual(actual, keys)
            self.assertEqual(dnd.circle_for(cls, 1), 1)

    def test_circle_display_matches_actual_spell_access(self):
        for cls in ('mage', 'druid', 'ranger', 'knight'):
            p = Player('1', 'Test', class_id=cls)
            for level in range(1, 106):
                p.level = level
                for key, spec in dnd.SPELLS.items():
                    if cls in spec['class_ids'] and spec['circle'] > 0:
                        with self.subTest(cls=cls, level=level, spell=key):
                            self.assertEqual(dnd.spell_allowed(p, key), spec['circle'] <= dnd.circle_for(cls, level) and level >= spec.get('class_min_levels',{}).get(cls,1))

    def test_second_and_later_circles_at_ten_level_milestones(self):
        for cls in ('mage', 'druid'):
            p = Player('1', 'Test', class_id=cls)
            for key, spec in dnd.SPELLS.items():
                if cls in spec['class_ids'] and spec['circle'] >= 2:
                    gate = (spec['circle'] - 1) * 10
                    self.assertEqual(dnd.spell_level(spec, cls), gate)
                    p.level = gate - 1
                    self.assertFalse(dnd.spell_allowed(p, key), key)
                    p.level = gate
                    self.assertTrue(dnd.spell_allowed(p, key), key)
            for level in (1, 5, 9):
                self.assertEqual(dnd.circle_for(cls, level), 1)

    def test_ranger_initial_spells_and_longstrider_gates(self):
        for key,gate in [('cure_wounds',1),('hunters_mark',1),('ensnaring_strike',1),('longstrider',5)]:
            self.assertEqual(dnd.spell_level(dnd.SPELLS[key], 'ranger'),gate)
            for level in (1,4,5,9,10,19,20):
                self.assertEqual(dnd.spell_allowed(Player('1','Test',class_id='ranger',level=level),key),level>=gate)

    def test_class_features_keep_their_gates(self):
        for key, cls, gate in (('second_wind', 'knight', 1), ('animal_companion', 'ranger', 10),
                               ('wild_shape_wolf', 'druid', 5), ('wild_shape_bear', 'druid', 35)):
            self.assertEqual(dnd.spell_level(dnd.SPELLS[key], cls), gate)

    def test_default_hotbar_first_circle_slots_are_unlocked(self):
        for cls, slots in (('mage', ('magic_missile', 'shield')), ('druid', ('cure_wounds', 'entangle'))):
            p = Player('1', 'Test', class_id=cls)
            self.assertEqual(dnd.DEFAULT_HOTBARS[cls][3:5], list(slots))
            self.assertTrue(all(dnd.spell_allowed(p, k) for k in slots))
            dnd.sync_hotbar(p)
            self.assertTrue(all(dnd.spell_allowed(p, k) for k in p.hotbar if k))

    def test_higher_mana_cost_without_cantrip_scaling_changes(self):
        for spec in dnd.SPELLS.values():
            if not spec.get('feature'):
                if spec['circle'] == 0:
                    self.assertEqual(spec['mana'], 0)
                elif spec['circle'] == 1:
                    self.assertEqual(spec['mana'], 0 if spec.get('free_cast') else 20)
        for level, count in ((1, 1), (19, 1), (20, 2), (49, 2), (50, 3), (80, 4)):
            self.assertEqual(rules.cantrip_count(Player('1', 'Test', class_id='mage', level=level)), count)


class FirstCircleGameplay(unittest.IsolatedAsyncioTestCase):
    # Reuse only fixture helpers; do not inherit and rerun the old test methods.
    setUp = base.GameRules.setUp
    tearDown = base.GameRules.tearDown
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    account = base.GameRules.account

    async def test_level_one_magic_missile_rolls_and_cost(self):
        p = self.player('mage'); mana = p.mana
        await self.g.cast_spell(p, 'magic_missile', self.e.id)
        self.assertEqual(self.e.hp, 987)
        self.assertEqual(p.mana, mana - 20)
        self.assertEqual(len(p.combat_log), 3)
        self.assertGreater(p.attack_cooldown_until, self.clock())

    async def test_level_one_burning_hands_area_and_cost(self):
        p = self.player('mage'); mana = p.mana
        await self.g.cast_spell(p, 'burning_hands', self.e.id)
        self.assertLess(self.e.hp, 999)
        self.assertEqual(p.mana, mana - 20)
        self.assertEqual(p.last_roll['damage_dice'], '3k6')

    async def test_level_one_shield_charges_only_on_reaction(self):
        p = self.player('mage'); mana = p.mana; hp = p.hp
        await self.g.cast_spell(p, 'shield')
        self.assertTrue(p.shield_armed); self.assertEqual(p.mana, mana)
        self.g.combat_rng = base.Dice(8)
        result = self.g.hit_player(self.e, p)
        self.assertTrue(result['shielded']); self.assertEqual(p.hp, hp)
        self.assertEqual(p.mana, mana - 20)

    async def test_level_one_mage_armor(self):
        p = self.player('mage'); mana = p.mana
        await self.g.cast_spell(p, 'mage_armor')
        self.assertTrue(rules.active_buff(p, 'mage_armor'))
        self.assertGreaterEqual(p.armor_class, 15)
        self.assertEqual(p.mana, mana - 20)

    async def test_level_one_longstrider_both_full_casters(self):
        for cls in ('mage', 'druid'):
            p = self.player(cls); speed = p.speed; mana = p.mana
            await self.g.cast_spell(p, 'longstrider')
            self.assertGreater(p.speed, speed)
            self.assertEqual(p.mana, mana - 20)

    async def test_level_one_cure_wounds(self):
        p = self.player('druid'); p.hp = 1; mana = p.mana
        await self.g.cast_spell(p, 'cure_wounds')
        self.assertEqual(p.hp, p.max_hp)
        self.assertEqual(p.last_roll['damage_dice'], '2k8+3')
        self.assertEqual(p.mana, mana - 20)

    async def test_level_one_healing_word_bonus_action(self):
        p = self.player('druid'); p.hp = 1; mana = p.mana
        await self.g.cast_spell(p, 'healing_word')
        self.assertGreater(p.hp, 1)
        self.assertEqual(p.mana, mana - 20)
        self.assertGreater(p.bonus_cooldown_until, self.clock())
        self.assertEqual(p.attack_cooldown_until, 0)

    async def test_level_one_entangle_concentration_and_save(self):
        p = self.player('druid'); mana = p.mana; self.g.combat_rng = base.Dice(1)
        await self.g.cast_spell(p, 'entangle', self.e.id)
        self.assertTrue(self.g.enemy_condition(self.e, 'restrained'))
        self.assertEqual(p.concentration, 'entangle')
        self.assertEqual(p.mana, mana - 20)

    async def test_low_mana_still_blocks_first_circle_but_not_cantrips(self):
        for cls, spell, cantrip in (('mage', 'magic_missile', 'fire_bolt'), ('druid', 'entangle', 'produce_flame')):
            p = self.player(cls); p.mana = 5; hp = self.e.hp
            await self.g.cast_spell(p, spell, self.e.id)
            self.assertEqual(p.mana, 5); self.assertEqual(self.e.hp, hp)
            self.assertEqual(p.attack_cooldown_until, 0)
            p.mana = 0
            await self.g.cast_spell(p, cantrip, self.e.id)
            self.assertLess(self.e.hp, hp); self.assertEqual(p.mana, 0)

    async def test_level_one_hotbar_spell_queues_before_autoattack(self):
        p = self.player('mage'); self.e.x = 1200
        await self.g.select_combat_target(p, {'enemy_id': self.e.id})
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp,999)  # selection only aims the wand
        await self.g.attack(p, enemy_id=self.e.id)
        await self.g.cast_spell(p, p.hotbar[3], self.e.id)
        self.assertEqual(p.pending_spell['spell'], 'magic_missile')
        hp = self.e.hp; self.clock.advance()
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp, hp - 12)
        self.assertEqual(p.last_roll['action'], 'Magiczny pocisk')
        self.assertFalse(p.pending_spell)

    async def test_ranger_cannot_bypass_later_spell_gates(self):
        p=self.player('ranger',1);p.hp=1;mana=p.mana
        for spell in ('longstrider','spike_growth','animal_companion'):
            await self.g.cast_spell(p,spell,self.e.id)
        self.assertEqual(p.hp,1);self.assertEqual(p.mana,mana)
        self.assertFalse(p.buffs);self.assertFalse(p.concentration)

    async def test_second_circle_denied_before_level_ten(self):
        for cls, spell in (('mage', 'scorching_ray'), ('druid', 'moonbeam')):
            for level in (1, 5, 9):
                p = self.player(cls, level); mana = p.mana; hp = self.e.hp
                await self.g.cast_spell(p, spell, self.e.id)
                self.assertEqual(p.mana, mana); self.assertEqual(self.e.hp, hp)
                self.assertFalse(p.pending_spell); self.assertFalse(p.concentration)

    async def test_existing_save_gains_circle_without_losing_custom_hotbar(self):
        for cls, spell in (('mage', 'magic_missile'), ('druid', 'entangle')):
            for level in (1, 5, 9):
                p = self.player(cls, level); saved = p.save_data()
                saved['rules_version'] = 8
                saved['hotbar'] = [spell, '', '', '', '', '', '', '']
                saved['gold'] = 123; saved['xp'] = 3
                loaded = self.g.load_player(p.id, p.name, p.ws, saved)
                self.assertEqual(loaded.hotbar[0], saved['hotbar'][0])
                self.assertEqual({k for k in loaded.hotbar if k}, {k for k in dnd.SPELLS if dnd.spell_allowed(loaded,k)})
                self.assertEqual((loaded.level, loaded.xp, loaded.gold), (level, 3, 123))
                self.assertTrue(dnd.spell_allowed(loaded, spell))
                self.assertEqual(loaded.public(self.clock(), private=True)['spell_circle'], 1)

    async def test_level_one_pvp_protection_remains_despite_unlocked_spells(self):
        p = self.player('mage'); q = self.player('knight', 20, '2')
        p.pvp_safety = False; mana = p.mana; hp = q.hp
        await self.g.cast_spell(p, 'magic_missile', target_id=q.id)
        self.assertEqual(q.hp, hp); self.assertEqual(p.mana, mana)
        self.assertEqual(p.attack_cooldown_until, 0)


class FirstCircleNetwork(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app(':memory:')))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_registered_full_casters_receive_level_one_catalogue_and_state(self):
        for cls in ('mage', 'druid'):
            ws = await self.client.ws_connect('/ws')
            await ws.send_json({'type': 'hello', 'name': 'Start' + cls, 'password': 'testpassword99', 'class_id': cls, 'create': True})
            packet = await ws.receive_json(timeout=10)
            self.assertEqual(packet['type'], 'welcome')
            spells = packet['world']['spells']
            first = [s for s in spells.values() if cls in s['class_ids'] and s['circle'] == 1]
            self.assertTrue(first)
            self.assertTrue(all(s['min_level'] == 1 for s in first))
            game = self.client.server.app['game']
            player = next(p for p in game.players.values() if p.class_id == cls)
            self.assertEqual(player.level, 1)
            self.assertEqual(player.public(game.now(), private=True)['spell_circle'], 1)
            self.assertTrue(all(dnd.spell_allowed(player, key) for key in player.hotbar[3:5]))
            await ws.close()

    async def test_help_and_milestones_use_new_gate(self):
        html = await (await self.client.get('/')).text()
        self.assertIn('I krąg od poziomu 1, II od 10', html)
        self.assertNotIn('I krąg od poziomu 10', html)
        from server import world_content as content
        first = next(m for m in content.MILESTONES if m[0] == 1)
        tenth = next(m for m in content.MILESTONES if m[0] == 10)
        self.assertIn('I krąg', first[1]); self.assertIn('od początku', first[2])
        self.assertIn('towarzysz', tenth[1])


if __name__ == '__main__':
    unittest.main()
