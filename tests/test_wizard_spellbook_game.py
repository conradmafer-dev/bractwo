"""Wizard book choices must survive login and only commit with a completed rest."""
import copy
import json
import unittest

import test_dnd as base
from server.server import Game, REST_RULES, SPAWN
from server import dnd_content as dnd


class WizardSpellbookGame(unittest.IsolatedAsyncioTestCase):
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    account = base.GameRules.account

    STARTER = ('magic_missile', 'burning_hands', 'shield', 'mage_armor', 'alarm', 'find_familiar')
    PREPARED = ('magic_missile', 'burning_hands', 'shield', 'mage_armor')

    def setUp(self):
        self.clock = base.Clock()
        self.g = Game(':memory:', clock=self.clock)
        self.g.combat_rng = base.Dice()
        for enemy in self.g.enemies.values():
            enemy.alive = False
            enemy.respawn_at = 0
        self.g.legacy_enemies = []
        self.addCleanup(self.g.db.close)

    def advance(self, seconds):
        self.clock.advance(seconds)
        for player in self.g.players.values():
            player.current_wall_time = self.clock()

    async def packet(self, p, packet_type, **data):
        await self.g.on_packet(p.ws, dict(type=packet_type, **data))

    async def wizard(self, level=1, pid='1'):
        p = self.player('mage', level, pid)
        for key in self.STARTER:
            await self.packet(p, 'wizard_learn', spell=key)
        await self.packet(p, 'wizard_prepare', spells=list(self.PREPARED))
        self.assertEqual(self.prepared(p), set(self.PREPARED))
        return p

    @staticmethod
    def prepared(p):
        return set(p.wizard_spellbook.get('prepared', []))

    async def rest(self, p, kind, plan):
        await self.packet(p, 'rest', kind=kind, wizard_preparation=plan)
        self.assertEqual(p.rest_state.get('kind'), kind)

    def finish_rest(self, p):
        self.advance(p.rest_state['until'] - self.clock() + .01)
        self.g.tick_rest(p)
        self.assertFalse(p.rest_state)

    @staticmethod
    def memorize(forget='magic_missile', prepare='alarm'):
        return {'memorize': {'forget': forget, 'prepare': prepare}}

    async def test_new_character_must_learn_and_prepare_but_cantrips_and_features_work(self):
        p = self.player('mage', 1)
        self.assertFalse(dnd.spell_allowed(p, 'magic_missile'))
        self.assertTrue(dnd.spell_allowed(p, 'fire_bolt'))
        self.assertTrue(dnd.spell_allowed(p, 'arcane_recovery'))
        enemy = self.enemy()
        mana, hp = p.mana, enemy.hp
        await self.g.cast_spell(p, 'magic_missile', enemy.id)
        self.assertEqual((p.mana, enemy.hp), (mana, hp))
        await self.packet(p, 'wizard_learn', spell='magic_missile')
        self.assertFalse(dnd.spell_allowed(p, 'magic_missile'))
        await self.packet(p, 'wizard_prepare', spells=['magic_missile'])
        await self.g.cast_spell(p, 'magic_missile', enemy.id)
        self.assertLess(enemy.hp, hp)
        self.assertLess(p.mana, mana)

    async def test_normal_cast_and_automatic_shield_respect_preparation(self):
        p = await self.wizard(5)
        enemy = self.enemy()
        mana, hp = p.mana, enemy.hp
        await self.g.cast_spell(p, 'fireball', enemy.id)
        await self.g.cast_spell(p, 'alarm')
        self.assertEqual((p.mana, enemy.hp), (mana, hp))
        self.assertFalse(p.casting_channel)
        await self.rest(p, 'long', {'prepared': ['magic_missile', 'burning_hands', 'mage_armor', 'alarm']})
        self.finish_rest(p)
        p.shield_armed = True  # A saved armed reaction is not permission to cast it.
        mana = p.mana
        result = dict(hit=True, critical=False, roll=10, total=p.armor_class + 1)
        self.g.shield_reaction(p, result)
        self.assertEqual(p.mana, mana)
        self.assertTrue(result['hit'])
        self.assertNotIn('shield', p.buffs)

    async def test_invalid_and_other_class_learning_packets_do_not_mutate_book(self):
        p = self.player('mage', 1)
        before = copy.deepcopy(p.wizard_spellbook)
        for key in (None, [], {}, 42, '', 'missing_spell', 'fireball', 'fire_bolt', 'arcane_recovery', 'cure_wounds'):
            with self.subTest(spell=key):
                await self.packet(p, 'wizard_learn', spell=key)
                self.assertEqual(p.wizard_spellbook, before)
        for cls in ('knight', 'ranger', 'druid'):
            other = self.player(cls, 5, cls)
            before = copy.deepcopy(other.wizard_spellbook)
            await self.packet(other, 'wizard_learn', spell='magic_missile')
            await self.packet(other, 'wizard_prepare', spells=['magic_missile'])
            self.assertEqual(other.wizard_spellbook, before)
            self.assertFalse(dnd.spell_allowed(other, 'magic_missile'))
        druid = self.g.players['druid']
        self.assertTrue(dnd.spell_allowed(druid, 'cure_wounds'))

    async def test_old_unselected_character_gets_new_wizard_choices_on_class_selection(self):
        p = self.player('knight', 1)
        p.class_chosen = False
        p.x, p.y, p.floor = SPAWN['x'], SPAWN['y'], 0
        await self.packet(p, 'choose_class', class_id='mage')
        self.assertEqual(p.class_id, 'mage')
        self.assertTrue(p.class_chosen)
        self.assertEqual(p.wizard_spellbook['known'], [])
        self.assertEqual(p.wizard_spellbook['prepared'], [])
        self.assertFalse(dnd.spell_allowed(p, 'magic_missile'))
        self.assertTrue(dnd.spell_allowed(p, 'fire_bolt'))
        await self.packet(p, 'wizard_learn', spell='magic_missile')
        await self.packet(p, 'wizard_prepare', spells=['magic_missile'])
        self.assertTrue(dnd.spell_allowed(p, 'magic_missile'))

    async def test_learning_is_persistent_and_reconnect_does_not_grant_more_choices(self):
        p = await self.wizard()
        before = copy.deepcopy(p.wizard_spellbook)
        for _ in range(3):
            saved = json.loads(json.dumps(p.save_data()))
            self.assertEqual(saved['wizard_spellbook'], before)
            p = self.g.load_player(p.id, p.name, base.WS(), saved)
            self.g.players[p.id] = p
            self.assertEqual(p.wizard_spellbook, before)
            await self.packet(p, 'wizard_learn', spell='longstrider')
            await self.packet(p, 'wizard_learn', spell='magic_missile')
            self.assertEqual(p.wizard_spellbook, before)

    async def test_saved_legacy_mage_keeps_previous_spells_with_hotbar_priority(self):
        p = self.player('mage', 5)
        saved = json.loads(json.dumps(p.save_data()))
        saved.pop('wizard_spellbook', None)
        saved['hotbar'] = ['find_familiar', 'alarm', 'fireball', 'shield', 'magic_missile']
        old_available = {
            key for key, spec in dnd.SPELLS.items()
            if not spec.get('feature') and spec.get('circle', 0) > 0
            and 'mage' in spec.get('class_ids', []) and p.level >= dnd.spell_level(spec, 'mage')
        }
        q = self.g.load_player(p.id, p.name, base.WS(), saved)
        self.assertEqual(set(q.wizard_spellbook['known']), old_available)
        self.assertEqual(len(self.prepared(q)), 9)
        self.assertTrue(set(saved['hotbar']).issubset(self.prepared(q)))
        again = self.g.load_player(q.id, q.name, base.WS(), q.save_data())
        self.assertEqual(again.wizard_spellbook, q.wizard_spellbook)

    async def test_known_unprepared_ritual_completes_without_mana_and_unknown_does_not_start(self):
        p = await self.wizard()
        self.assertNotIn('alarm', self.prepared(p))
        mana = p.mana
        await self.packet(p, 'ritual', spell_id='alarm')
        self.assertEqual(p.casting_channel.get('key'), 'alarm')
        self.advance(p.casting_channel['until'] - self.clock() + .01)
        self.g.complete_channel(p)
        self.assertIn('ritual_alarm', p.buffs)
        self.assertEqual(p.mana, mana)
        other = self.player('mage', 1, '2')
        for key in ('alarm', 'find_familiar', [], {}, None):
            await self.packet(other, 'ritual', spell_id=key)
            self.assertFalse(other.casting_channel)

    async def test_ritual_revalidates_knowledge_before_charging_or_applying(self):
        p = await self.wizard()
        await self.packet(p, 'ritual', spell_id='find_familiar')
        self.assertTrue(p.casting_channel)
        before = p.mana, p.gold
        p.wizard_spellbook['known'].remove('find_familiar')
        self.advance(p.casting_channel['until'] - self.clock() + .01)
        self.g.complete_channel(p)
        self.assertEqual((p.mana, p.gold), before)
        self.assertNotIn(p.id, self.g.familiars)
        self.assertFalse(p.casting_channel)

    async def test_memorize_commits_once_on_completion_and_each_short_rest_allows_it(self):
        p = await self.wizard(5)
        initial = self.prepared(p)
        await self.rest(p, 'short', self.memorize())
        self.assertEqual(self.prepared(p), initial)
        self.advance(REST_RULES['short_seconds'] - .1)
        self.g.tick_rest(p)
        self.assertEqual(self.prepared(p), initial)
        self.advance(.2)
        self.g.tick_rest(p)
        expected = (initial - {'magic_missile'}) | {'alarm'}
        self.assertEqual(self.prepared(p), expected)
        self.g.tick_rest(p)
        self.assertEqual(self.prepared(p), expected)
        self.advance(REST_RULES['short_cooldown_seconds'] + .01)
        await self.rest(p, 'short', self.memorize('alarm', 'magic_missile'))
        self.finish_rest(p)
        self.assertEqual(self.prepared(p), initial)

    async def test_memorize_requires_level_five_and_exactly_one_known_replacement(self):
        for level in (4, 5):
            p = await self.wizard(level, str(level))
            initial = self.prepared(p)
            plans = [
                {'memorize': [{'forget': 'magic_missile', 'prepare': 'alarm'}, {'forget': 'shield', 'prepare': 'find_familiar'}]},
                {'memorize': {'forget': 'magic_missile', 'prepare': 'fireball'}},
                {'memorize': {'forget': 'alarm', 'prepare': 'find_familiar'}},
                {'memorize': {'forget': 'magic_missile', 'prepare': 'shield'}},
                {'prepared': ['alarm', 'find_familiar']},
            ]
            if level == 4:
                plans.append(self.memorize())
            for plan in plans:
                with self.subTest(level=level, plan=plan):
                    await self.packet(p, 'rest', kind='short', wizard_preparation=plan)
                    self.assertFalse(p.rest_state)
                    self.assertEqual(self.prepared(p), initial)

    async def test_interrupted_short_and_long_rests_never_change_prepared_spells(self):
        for kind in ('short', 'long'):
            for interruption in ('cancel', 'movement', 'combat', 'death', 'disconnect'):
                with self.subTest(kind=kind, interruption=interruption):
                    p = await self.wizard(5)
                    before = copy.deepcopy(p.wizard_spellbook)
                    plan = self.memorize() if kind == 'short' else {'prepared': ['alarm', 'find_familiar']}
                    await self.rest(p, kind, plan)
                    if interruption == 'cancel':
                        await self.packet(p, 'rest_cancel')
                    elif interruption == 'movement':
                        p.x += 1
                    elif interruption == 'combat':
                        self.g.tag(p)
                    elif interruption == 'death':
                        p.hp = 0
                    else:
                        p.ws.closed = True
                    self.g.tick_rest(p)
                    self.advance(REST_RULES[kind + '_seconds'] + .01)
                    self.g.tick_rest(p)
                    self.assertFalse(p.rest_state)
                    self.assertEqual(p.wizard_spellbook, before)

    async def test_rest_plan_is_copied_and_cannot_be_replaced_by_a_second_packet(self):
        p = await self.wizard(5)
        plan = self.memorize()
        await self.rest(p, 'short', plan)
        plan['memorize']['prepare'] = 'find_familiar'
        await self.packet(p, 'rest', kind='short', wizard_preparation=self.memorize('shield', 'find_familiar'))
        self.finish_rest(p)
        self.assertEqual(self.prepared(p), (set(self.PREPARED) - {'magic_missile'}) | {'alarm'})

    async def test_long_rest_replaces_list_atomically_and_rejects_invalid_or_duplicate_entries(self):
        p = await self.wizard()
        initial = self.prepared(p)
        for spells in (None, 'alarm', ['alarm', 'alarm'], ['alarm', 'fireball'], list(self.STARTER), ['alarm', {}]):
            with self.subTest(spells=spells):
                await self.packet(p, 'rest', kind='long', wizard_preparation={'prepared': spells})
                self.assertFalse(p.rest_state)
                self.assertEqual(self.prepared(p), initial)
        final = ['alarm', 'find_familiar', 'mage_armor', 'shield']
        await self.rest(p, 'long', {'prepared': final})
        self.assertEqual(self.prepared(p), initial)
        self.finish_rest(p)
        self.assertEqual(self.prepared(p), set(final))

    async def test_known_unprepared_power_preference_survives_reload_without_allowing_cast(self):
        p = await self.wizard(5)
        await self.rest(p, 'short', self.memorize())
        self.finish_rest(p)
        await self.packet(p, 'spell_power', spell_id='magic_missile', circle=2)
        self.assertEqual(p.spell_circle_choices.get('magic_missile'), 2)
        q = self.g.load_player(p.id, p.name, base.WS(), p.save_data())
        self.assertEqual(q.spell_circle_choices.get('magic_missile'), 2)
        self.assertFalse(dnd.spell_allowed(q, 'magic_missile'))
        enemy = self.enemy()
        before = q.mana, enemy.hp
        await self.g.cast_spell(q, 'magic_missile', enemy.id)
        self.assertEqual((q.mana, enemy.hp), before)

    async def test_malformed_free_preparation_packets_do_not_spend_slots(self):
        p = self.player('mage', 1)
        await self.packet(p, 'wizard_learn', spell='magic_missile')
        before = copy.deepcopy(p.wizard_spellbook)
        for spells in (None, {}, 'magic_missile', ['magic_missile', 'magic_missile'], ['magic_missile', {}], ['fireball']):
            with self.subTest(spells=spells):
                await self.packet(p, 'wizard_prepare', spells=spells)
                self.assertEqual(p.wizard_spellbook, before)

    async def test_free_preparation_only_adds_awarded_slots_and_empty_rest_does_not_create_more(self):
        p = self.player('mage', 1)
        for key in self.STARTER:
            await self.packet(p, 'wizard_learn', spell=key)
        await self.packet(p, 'wizard_prepare', spells=['magic_missile'])
        await self.packet(p, 'wizard_prepare', spells=list(self.PREPARED))
        self.assertEqual(self.prepared(p), set(self.PREPARED))
        await self.packet(p, 'wizard_prepare', spells=['alarm', 'find_familiar', 'shield', 'mage_armor'])
        self.assertEqual(self.prepared(p), set(self.PREPARED))
        await self.rest(p, 'long', {'prepared': []})
        self.finish_rest(p)
        self.assertEqual(self.prepared(p), set())
        await self.packet(p, 'wizard_prepare', spells=list(self.PREPARED))
        self.assertEqual(self.prepared(p), set())

    async def test_learning_and_free_preparation_are_blocked_for_full_combat_deadline_and_unsafe_states(self):
        for state in ('combat', 'pvp', 'moving', 'channel', 'rest', 'dead', 'disconnected'):
            with self.subTest(state=state):
                p = self.player('mage', 1)
                await self.packet(p, 'wizard_learn', spell='magic_missile')
                if state == 'combat':
                    self.g.tag(p)
                    self.advance(4)  # PvE rest can start, but instant book edits cannot.
                elif state == 'pvp':
                    self.g.tag(p, pvp=True)
                elif state == 'moving':
                    p.dx, p.input_time = 1, self.g.time
                elif state == 'channel':
                    p.casting_channel = {'key': 'alarm', 'until': self.clock() + 10}
                elif state == 'rest':
                    await self.g.start_rest(p, 'short')
                elif state == 'dead':
                    p.hp = 0
                else:
                    p.ws.closed = True
                before = copy.deepcopy(p.wizard_spellbook)
                await self.packet(p, 'wizard_learn', spell='shield')
                await self.packet(p, 'wizard_prepare', spells=['magic_missile'])
                self.assertEqual(p.wizard_spellbook, before)

    async def test_logout_during_rest_discards_plan_and_does_not_change_saved_list(self):
        p = await self.wizard(5)
        before = copy.deepcopy(p.wizard_spellbook)
        await self.rest(p, 'short', self.memorize())
        saved = json.loads(json.dumps(p.save_data()))
        self.assertNotIn('rest_state', saved)
        q = self.g.load_player(p.id, p.name, base.WS(), saved)
        self.assertFalse(q.rest_state)
        self.advance(REST_RULES['short_seconds'] + .01)
        self.g.tick_rest(q)
        self.assertEqual(q.wizard_spellbook, before)

    async def test_owner_snapshot_and_compact_cache_follow_book_changes_without_public_leak(self):
        p = await self.wizard(5)
        other = self.player('knight', 1, '2')
        self.g.compact_clients.add(p.id)
        first = self.g.wire_snapshot(p)
        own = next(row for row in first['players'] if row['id'] == p.id)
        self.assertEqual(own['character_sheet']['caster']['spellbook']['known'], p.wizard_spellbook['known'])
        self.assertTrue(own['spell_profiles']['magic_missile']['available'])
        self.assertFalse(own['spell_profiles']['alarm']['available'])
        self.assertIn('magic_missile', own['hotbar'])
        await self.rest(p, 'short', self.memorize())
        self.finish_rest(p)
        changed = self.g.wire_snapshot(p)
        own = next(row for row in changed['players'] if row['id'] == p.id)
        self.assertIn('character_sheet', own)
        self.assertIn('spell_profiles', own)
        self.assertTrue(own['spell_profiles']['alarm']['available'])
        self.assertFalse(own['spell_profiles']['magic_missile']['available'])
        self.assertIn('alarm', own['hotbar'])
        self.assertNotIn('magic_missile', own['hotbar'])
        stranger_view = next(row for row in self.g.snapshot(other)['players'] if row['id'] == p.id)
        for private_key in ('wizard_spellbook', 'character_sheet', 'spell_profiles', 'hotbar'):
            self.assertNotIn(private_key, stranger_view)
        json.dumps(changed, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
