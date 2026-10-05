"""Authoritative timed rests; existing combat and passive recovery remain independent."""
import copy
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
import test_dnd as base
from server.server import REST_RULES, SPAWN
from server import caster_rules, rest_rules


class RestRules(unittest.IsolatedAsyncioTestCase):
    tearDown = base.GameRules.tearDown
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    account = base.GameRules.account

    def setUp(self):
        base.GameRules.setUp(self)
        self.e.alive = False
        self.p = self.player('mage', 5)
        self.p.hp = self.p.max_hp*.25
        self.p.mana = 0
        self.p.mana_recovery_until = self.clock()+100

    def state(self):
        return self.p.public(self.clock(), self.g.time, private=True)

    def advance(self, seconds):
        self.clock.advance(seconds)
        self.g.time += seconds
        self.g.tick_rest(self.p)

    def safe(self):
        self.p.x, self.p.y, self.p.floor = SPAWN['x'], SPAWN['y'], 0
        self.assertTrue(self.g.in_safe(self.p))

    def timers(self):
        p = self.p
        return (p.combat_until, p.pvp_combat_until, p.mana_recovery_until,
                p.attack_cooldown_until, p.bonus_cooldown_until, p.potion_cooldown_until,
                copy.deepcopy(p.spell_cooldowns))

    async def test_short_after_three_seconds_is_atomic_and_does_not_reset_cooldowns(self):
        p = self.p
        self.g.tag(p)
        p.attack_cooldown_until = self.clock()+40
        p.bonus_cooldown_until = self.clock()+41
        p.potion_cooldown_until = self.clock()+42
        p.spell_cooldowns = {'arcane_recovery': self.clock()+180, 'wild_shape_wolf': self.clock()+60}
        timers = self.timers()
        hp, mana = p.hp, p.mana
        self.assertEqual(self.state()['rest_block_reason'], 'combat_pve')
        self.assertEqual(self.state()['rest_block_remaining'], 3)
        await self.g.start_rest(p, 'short')
        self.assertFalse(p.rest_state)
        self.clock.advance(2.999)
        await self.g.start_rest(p, 'short')
        self.assertFalse(p.rest_state)
        self.clock.advance(.001)
        await self.g.on_packet(p.ws, {'type': 'rest', 'kind': 'short'})
        seconds = REST_RULES['short_seconds']
        self.assertEqual(self.state()['rest'], {'kind': 'short', 'total': seconds, 'remaining': seconds})
        self.assertEqual(p.rest_cooldown_until, 0)
        self.advance(seconds-.001)
        self.assertEqual((p.hp, p.mana), (hp, mana))
        self.advance(.001)
        self.assertFalse(p.rest_state)
        self.assertEqual(p.hp, p.max_hp)
        self.assertEqual(p.mana, caster_rules.recovery_amount(p))
        self.assertLess(p.mana, p.max_mana)
        self.assertGreater(rest_rules.spent(p, 'hit_dice'), 0)
        self.assertEqual(rest_rules.spent(p, 'arcane_recovery'), 1)
        self.assertEqual(p.rest_resources['short_ready'], self.clock()+REST_RULES['short_cooldown_seconds'])
        self.assertEqual(p.rest_cooldown_until, 0)
        self.assertEqual(self.timers(), timers)
        self.assertGreater(p.combat_until, self.clock())

    async def test_pvp_wait_stays_twenty_seconds_even_if_general_timer_is_cleared(self):
        p = self.p
        self.g.tag(p, pvp=True)
        self.assertEqual(self.state()['rest_block_remaining'], 20)
        self.clock.advance(3)
        p.combat_until = 0
        self.assertEqual(self.state()['rest_block_reason'], 'combat_pvp')
        self.assertEqual(self.state()['rest_block_remaining'], 17)
        await self.g.start_rest(p)
        self.assertFalse(p.rest_state)
        self.clock.advance(17)
        await self.g.start_rest(p)
        self.assertTrue(p.rest_state)

    async def test_both_rest_kinds_are_available_in_field_and_clear_queued_actions(self):
        p = self.p
        p.auto_enemy_id, p.auto_enabled = self.e.id, True
        p.pending_spell = {'spell': 'fire_bolt', 'until': self.clock()+10}
        self.assertFalse(self.state()['rest_safe'])
        self.assertEqual(self.state()['rest_block_reason'], '')
        await self.g.start_rest(p, 'long')
        self.assertEqual(p.rest_state['kind'], 'long')
        self.assertEqual((p.auto_enemy_id, p.auto_target_id, p.auto_enabled, p.pending_spell), ('', '', False, {}))
        self.g.cancel_rest(p)
        await self.g.start_rest(p, 'short')
        self.assertTrue(p.rest_state)
        self.assertEqual((p.auto_enemy_id, p.auto_target_id, p.auto_enabled, p.pending_spell), ('', '', False, {}))

    async def test_long_thirty_seconds_restores_resources_and_costs_no_gold(self):
        p = self.p
        self.safe()
        p.spell_cooldowns = {'arcane_recovery': self.clock()+180}
        timers, gold, resources = self.timers(), p.gold, (p.hp, p.mana)
        await self.g.start_rest(p, 'long')
        self.advance(REST_RULES['long_seconds']-.001)
        self.assertEqual((p.hp, p.mana), resources)
        self.advance(.001)
        self.assertEqual((p.hp, p.mana), (p.max_hp, p.max_mana))
        self.assertEqual((self.timers(), p.gold), (timers, gold))

    async def test_duplicate_start_cannot_shorten_or_restart_rest(self):
        self.safe()
        await self.g.start_rest(self.p, 'long')
        original = dict(self.p.rest_state)
        self.advance(1)
        for kind in ('long', 'short'):
            await self.g.start_rest(self.p, kind)
            self.assertEqual(self.p.rest_state, original)

    async def test_legacy_merchant_interact_no_longer_refills_instantly(self):
        p = self.p
        p.x, p.y = 680, 1180
        self.assertTrue(self.g.merchant_near(p))
        resources = p.hp, p.mana
        self.g.tag(p)
        await self.g.interact(p)
        self.assertFalse(p.rest_state)
        self.assertEqual((p.hp, p.mana), resources)
        self.clock.advance(3)
        self.assertGreater(p.combat_until, self.clock())
        await self.g.interact(p)
        self.assertEqual((p.hp, p.mana), resources)
        self.assertEqual(p.rest_state['kind'], 'long')
        self.advance(REST_RULES['long_seconds'])
        self.assertEqual((p.hp, p.mana), (p.max_hp, p.max_mana))

    async def test_zero_input_does_not_interrupt_but_actual_movement_does(self):
        p = self.p
        resources = p.hp, p.mana
        await self.g.start_rest(p)
        for _ in range(20):
            await self.g.on_packet(p.ws, {'type': 'input', 'x': 0, 'y': 0})
            self.advance(.1)
        self.assertTrue(p.rest_state)
        await self.g.on_packet(p.ws, {'type': 'input', 'x': 1, 'y': 0})
        self.assertFalse(p.rest_state)
        self.advance(10)
        self.assertEqual((p.hp, p.mana), resources)

    async def test_held_movement_blocks_start_without_changing_target(self):
        p = self.p
        p.auto_enemy_id = self.e.id
        await self.g.on_packet(p.ws, {'type': 'input', 'x': 1, 'y': 0})
        self.assertEqual(self.state()['rest_block_reason'], 'moving')
        await self.g.start_rest(p)
        self.assertFalse(p.rest_state)
        self.assertEqual(p.auto_enemy_id, self.e.id)
        await self.g.on_packet(p.ws, {'type': 'input', 'x': 0, 'y': 0})
        await self.g.start_rest(p)
        self.assertTrue(p.rest_state)

    async def test_position_and_floor_interrupt_but_safe_zone_is_not_required(self):
        p = self.p
        for field, value in (('x', p.x+1), ('floor', -1)):
            with self.subTest(field=field):
                p.x, p.y, p.floor = 1100, 1180, 0
                before = p.hp, p.mana
                await self.g.start_rest(p)
                setattr(p, field, value)
                self.advance(REST_RULES['short_seconds'])
                self.assertFalse(p.rest_state)
                self.assertEqual((p.hp, p.mana), before)
        self.safe()
        await self.g.start_rest(p, 'long')
        with patch.object(self.g, 'in_safe', return_value=False):
            self.g.tick_rest(p)
        self.assertTrue(p.rest_state)

    async def test_dead_selected_enemy_does_not_block_rest_or_cancel_it_on_invalid_attack(self):
        p = self.p
        p.auto_enemy_id, p.auto_enabled = self.e.id, True
        self.e.hp = 0
        await self.g.start_rest(p)
        self.assertTrue(p.rest_state)
        await self.g.attack(p, enemy_id=self.e.id)
        self.assertTrue(p.rest_state)
        self.assertEqual(p.combat_until, 0)
        self.e.hp, self.e.alive = 999, True
        await self.g.attack(p, enemy_id=self.e.id)
        self.assertFalse(p.rest_state)
        self.assertGreater(p.combat_until, self.clock())

    async def test_rejected_spell_preserves_rest_but_executed_spell_cancels(self):
        p = self.p
        p.mana = p.max_mana
        await self.g.start_rest(p)
        await self.g.cast_spell(p, 'fire_bolt', self.e.id)
        self.assertTrue(p.rest_state)
        await self.g.cast_spell(p, 'longstrider')
        self.assertFalse(p.rest_state)
        self.assertIn('longstrider', p.buffs)

    async def test_real_ritual_cancels_rest_and_blocks_a_new_rest(self):
        p = self.p
        p.mana = p.max_mana
        await self.g.start_rest(p)
        await self.g.start_caster_channel(p, 'alarm', ritual=True)
        self.assertFalse(p.rest_state)
        self.assertTrue(p.casting_channel)
        self.assertEqual(self.state()['rest_block_reason'], 'channel')
        await self.g.start_rest(p)
        self.assertFalse(p.rest_state)

    async def test_damage_on_completion_tick_wins_over_rest_reward(self):
        p = self.p
        self.g.tag(p)
        self.clock.advance(3)
        await self.g.start_rest(p)
        before = p.hp, p.mana
        self.clock.advance(REST_RULES['short_seconds'])
        with patch.object(self.g, 'step_monsters', side_effect=lambda *args: self.g.damage_player(p, 1)):
            self.g.step(.05)
        self.assertFalse(p.rest_state)
        self.assertLess(p.hp, before[0])
        self.assertEqual(p.mana, before[1])

    async def test_manual_cancel_and_dead_or_disconnected_start_have_no_reward(self):
        p = self.p
        before = p.hp, p.mana
        await self.g.start_rest(p)
        await self.g.on_packet(p.ws, {'type': 'rest_cancel'})
        self.advance(20)
        self.assertEqual((p.hp, p.mana), before)
        self.assertEqual(p.rest_cooldown_until, 0)
        self.assertEqual(self.state()['rest_cooldown_remaining'], 0)
        await self.g.start_rest(p)
        self.assertTrue(p.rest_state)
        self.g.cancel_rest(p)
        p.hp = 0
        await self.g.start_rest(p)
        self.assertEqual(self.state()['rest_block_reason'], 'dead')
        self.assertFalse(p.rest_state)
        p.hp, p.ws = before[0], None
        await self.g.start_rest(p)
        self.assertEqual(self.state()['rest_block_reason'], 'disconnected')
        self.assertFalse(p.rest_state)

    async def test_disconnect_while_combat_avatar_remains_clears_rest_and_save_omits_it(self):
        p = self.p
        self.account(p)
        self.g.tag(p)
        self.clock.advance(3)
        await self.g.start_rest(p)
        self.assertNotIn('rest_state', p.save_data())
        await self.g.disconnect(p.ws)
        self.assertIn(p.id, self.g.players)
        self.assertFalse(p.rest_state)
        saved = json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?', (p.id,)).fetchone()[0])
        self.assertNotIn('rest_state', saved)
        loaded = self.g.load_player(p.id, p.name, base.WS(), saved)
        self.assertFalse(loaded.rest_state)
        self.assertEqual(loaded.combat_until, p.combat_until)

    async def test_completion_is_saved_once_and_caps_resources(self):
        p = self.p
        p.hp, p.mana = p.max_hp-1, p.max_mana-1
        self.account(p)
        await self.g.start_rest(p)
        self.advance(REST_RULES['short_seconds'])
        saved = json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?', (p.id,)).fetchone()[0])
        self.assertEqual((saved['hp'], saved['mana']), (p.max_hp, p.max_mana))
        p.hp, p.mana = 1, 0
        self.advance(REST_RULES['short_seconds'])
        self.assertEqual((p.hp, p.mana), (1, 0))

    async def test_invalid_rest_kinds_do_not_mutate_gameplay(self):
        p = self.p
        p.auto_enemy_id = self.e.id
        for kind in (None, {}, [], 7, 'instant', ''):
            await self.g.on_packet(p.ws, {'type': 'rest', 'kind': kind})
            self.assertFalse(p.rest_state)
            self.assertEqual(p.auto_enemy_id, self.e.id)

    def test_rules_and_owner_fields_are_exposed_without_runtime_internals(self):
        self.assertEqual(self.g.metadata()['rest_rules'], REST_RULES)
        self.assertEqual(REST_RULES, {'short_seconds': 10, 'long_seconds': 30,
                                    'short_cooldown_seconds': 15, 'long_cooldown_seconds': 60,
                                    'pve_delay_seconds': 3, 'long_safe_only': False})
        self.assertEqual(self.state()['rest'], {})
        self.assertEqual(self.state()['rest_cooldown_remaining'], 0)
        self.assertEqual(self.state()['rest_short_remaining'], 0)
        self.assertEqual(self.state()['rest_long_remaining'], 0)
        self.assertNotIn('rest_state', self.state())
        self.assertNotIn('rest', self.p.public(self.clock()))
        self.assertNotIn('rest_cooldown_remaining', self.p.public(self.clock()))
        self.assertNotIn('rest_short_remaining', self.p.public(self.clock()))
        self.assertNotIn('rest_long_remaining', self.p.public(self.clock()))

    async def test_separate_cooldowns_apply_to_each_kind_and_merchant_until_exact_boundary(self):
        p = self.p
        p.x, p.y = 680, 1180
        self.assertTrue(self.g.merchant_near(p))
        await self.g.start_rest(p, 'short')
        self.advance(REST_RULES['short_seconds'])
        deadline = p.rest_resources['short_ready']
        self.assertEqual(self.state()['rest_short_remaining'], 15)
        self.assertEqual(self.state()['rest_long_remaining'], 0)
        p.hp, p.mana = 1, 0
        await self.g.on_packet(p.ws, {'type': 'rest', 'kind': 'short'})
        self.assertFalse(p.rest_state)
        await self.g.on_packet(p.ws, {'type': 'rest', 'kind': 'long'})
        self.assertEqual(p.rest_state['kind'], 'long')
        self.g.cancel_rest(p)
        await self.g.interact(p)
        self.assertEqual(p.rest_state['kind'], 'long')
        self.g.cancel_rest(p)
        self.assertEqual((p.hp, p.mana), (1, 0))
        self.clock.value = deadline-.001
        await self.g.start_rest(p, 'short')
        self.assertFalse(p.rest_state)
        self.clock.value = deadline
        await self.g.start_rest(p, 'short')
        self.assertTrue(p.rest_state)
        self.g.cancel_rest(p)
        await self.g.start_rest(p, 'long')
        self.assertTrue(p.rest_state)
        self.advance(REST_RULES['long_seconds'])
        self.assertEqual((p.hp, p.mana), (p.max_hp, p.max_mana))
        deadline = p.rest_resources['long_ready']
        self.assertEqual(self.state()['rest_long_remaining'], 60)
        self.assertEqual(self.state()['rest_short_remaining'], 0)
        await self.g.start_rest(p, 'short')
        self.assertTrue(p.rest_state)
        self.g.cancel_rest(p)
        await self.g.interact(p)
        self.assertFalse(p.rest_state)
        self.clock.value = deadline-.001
        await self.g.start_rest(p, 'long')
        self.assertFalse(p.rest_state)
        self.clock.value = deadline
        await self.g.interact(p)
        self.assertEqual(p.rest_state['kind'], 'long')

    async def test_wall_clock_cooldown_survives_reconnect_restart_and_old_saves(self):
        p = self.p
        self.account(p)
        await self.g.start_rest(p)
        self.advance(REST_RULES['short_seconds'])
        deadline = p.rest_resources['short_ready']
        await self.g.disconnect(p.ws)
        saved = json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?', (p.id,)).fetchone()[0])
        self.assertEqual(saved['rest_resources']['short_ready'], deadline)
        loaded = self.g.load_player(p.id, p.name, base.WS(), saved)
        await self.g.start_rest(loaded)
        self.assertFalse(loaded.rest_state)
        self.assertEqual(loaded.public(self.clock(), private=True)['rest_short_remaining'], 15)
        legacy = dict(saved)
        legacy.pop('rest_resources')
        old = self.g.load_player(p.id, p.name, base.WS(), legacy)
        self.assertEqual(old.rest_resources.get('short_ready', 0), 0)
        self.assertEqual(old.rest_resources.get('long_ready', 0), 0)
        with tempfile.TemporaryDirectory() as directory:
            database = Path(directory)/'world.sqlite3'
            with closing(sqlite3.connect(database)) as backup:
                self.g.db.backup(backup)
            self.clock.advance(10)
            restarted = base.Game(database, clock=self.clock)
            try:
                stored = json.loads(restarted.db.execute('SELECT data FROM accounts WHERE id=?', (p.id,)).fetchone()[0])
                player = restarted.load_player(p.id, p.name, base.WS(), stored)
                restarted.players[player.id] = player
                restarted.compact_clients.add(player.id)
                for expected in (5, 4):
                    packet = restarted.wire_snapshot(player)
                    owner = next(row for row in packet['players'] if row['id'] == player.id)
                    self.assertEqual(owner['rest_short_remaining'], expected)
                    self.clock.advance(1)
                await restarted.start_rest(player)
                self.assertFalse(player.rest_state)
                self.clock.value = deadline
                await restarted.start_rest(player)
                self.assertTrue(player.rest_state)
            finally:
                restarted.db.close()


if __name__ == '__main__':
    unittest.main()
