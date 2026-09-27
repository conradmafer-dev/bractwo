"""0.8.15: only Arcane Recovery changes; exercise authoritative code and saves."""
import asyncio
import copy
import json
import unittest
import test_dnd as base
from server import caster_rules as caster, dnd_content as dnd, spell_scaling
from server.server import make_item

KEY = 'arcane_recovery'

class Recovery(unittest.IsolatedAsyncioTestCase):
    setUp = base.GameRules.setUp
    tearDown = base.GameRules.tearDown
    player = base.GameRules.player
    enemy = base.GameRules.enemy
    account = base.GameRules.account

    async def test_free_instant_restore_with_no_gold_or_mana(self):
        p = self.player('mage'); p.mana = p.gold = 0
        await self.g.cast_spell(p, KEY)
        self.assertEqual((p.mana, p.gold), (20, 0))
        self.assertFalse(p.casting_channel)
        self.assertNotIn('arcane_channel', p.buffs)
        self.assertEqual(p.spell_cooldowns[KEY], self.clock()+180)

    def test_profile_and_both_descriptions_agree(self):
        p = self.player('mage'); s = spell_scaling.resolve(p, KEY)
        self.assertEqual((s['action'], s['mana'], s['cooldown'], s['restore_mana']), ('bonus', 0, 180, 20))
        self.assertFalse(s.get('channel_seconds')); self.assertFalse(s.get('ritual'))
        feature = next(f for f in caster.feature_rows(p) if f['id'] == KEY)
        for text in (s['description'], feature['description']):
            self.assertIn('natychmiast', text.lower()); self.assertNotIn('4 s', text); self.assertNotIn('Poza walką', text)

    async def test_cast_matches_authoritative_scaling_amount(self):
        for level in (1, 5, 10, 15, 20, 35, 50, 80, 100):
            with self.subTest(level=level):
                p = self.player('mage', level); p.mana = 0
                await self.g.cast_spell(p, KEY)
                self.assertEqual(p.mana, caster.recovery_amount(p))

    async def test_bonus_action_does_not_consume_or_reset_main_action(self):
        p = self.player('mage'); p.mana = 0
        p.attack_cooldown_until = self.clock()+2.5
        p.reaction_ready = self.clock()+1
        p.potion_cooldown_until = self.clock()+1.8
        await self.g.cast_spell(p, KEY)
        self.assertEqual(p.bonus_cooldown_until, self.clock()+3)
        self.assertEqual(p.attack_cooldown_until, self.clock()+2.5)
        self.assertEqual(p.reaction_ready, self.clock()+1)
        self.assertEqual(p.potion_cooldown_until, self.clock()+1.8)
        self.assertEqual(p.mana, 20)

    async def test_regular_spell_can_follow_without_waiting(self):
        p = self.player('mage'); p.mana = 0
        await self.g.cast_spell(p, KEY)
        await self.g.cast_spell(p, 'mage_armor')
        self.assertEqual(p.mana, 0); self.assertIn('mage_armor', p.buffs)
        self.assertEqual(p.attack_cooldown_until, self.clock()+3)

    async def test_pve_and_pvp_timers_are_not_cleared(self):
        p = self.player('mage', 20); p.mana = 0
        p.combat_until = self.clock()+20; p.pvp_combat_until = self.clock()+90
        p.pvp_safety = False; p.aggressors = {'2': self.clock()+90}
        old = (p.combat_until, p.pvp_combat_until, p.pvp_safety, dict(p.aggressors))
        await self.g.cast_spell(p, KEY)
        self.assertGreater(p.mana, 0)
        self.assertEqual((p.combat_until, p.pvp_combat_until, p.pvp_safety, p.aggressors), old)

    async def test_self_only_even_with_player_target(self):
        p = self.player('mage', 20); q = self.player('druid', 20, '2')
        p.mana = q.mana = 0; hp = q.hp
        await self.g.cast_spell(p, KEY, target_id=q.id)
        self.assertGreater(p.mana, 0); self.assertEqual(q.mana, 0); self.assertEqual(q.hp, hp)
        self.assertEqual(self.g.effects[-1]['target_id'], p.id)

    async def test_movement_target_and_queued_spell_are_preserved(self):
        p = self.player('mage'); p.mana = 0
        p.dx, p.dy, p.input_time = 1, -1, self.g.time
        p.auto_enemy_id = self.e.id; p.auto_enabled = True
        p.pending_spell = {'spell': 'magic_missile', 'enemy': self.e.id, 'until': self.clock()+4}
        old = (p.dx, p.dy, p.input_time, p.auto_enemy_id, p.auto_enabled, copy.deepcopy(p.pending_spell))
        await self.g.cast_spell(p, KEY)
        self.assertEqual((p.dx, p.dy, p.input_time, p.auto_enemy_id, p.auto_enabled, p.pending_spell), old)

    async def test_concentration_and_existing_buffs_are_preserved(self):
        p = self.player('mage', 30); p.mana = 0
        p.concentration = 'wall_of_fire'; p.concentration_until = self.clock()+30
        p.concentration_profile = {'id': 'wall_of_fire', 'mana': 60}
        p.buffs = {'mage_armor': {'until': self.clock()+60}}
        old = (p.concentration, p.concentration_until, copy.deepcopy(p.concentration_profile), copy.deepcopy(p.buffs))
        await self.g.cast_spell(p, KEY)
        self.assertEqual((p.concentration, p.concentration_until, p.concentration_profile, p.buffs), old)

    async def test_full_mana_does_not_spend_action_or_start_cd(self):
        p = self.player('mage'); before = copy.deepcopy(p.spell_history)
        await self.g.cast_spell(p, KEY)
        self.assertNotIn(KEY, p.spell_cooldowns); self.assertEqual(p.bonus_cooldown_until, 0)
        self.assertEqual(p.spell_history, before); self.assertFalse(self.g.effects)

    async def test_fractional_missing_mana_capped_and_reported(self):
        p = self.player('mage'); p.mana = p.max_mana - .5
        await self.g.cast_spell(p, KEY)
        self.assertEqual(p.mana, p.max_mana)
        self.assertTrue(any('+0.5 many' in str(m) for m in p.ws.messages))
        self.assertEqual(p.spell_cooldowns[KEY], self.clock()+180)

    async def test_bonus_action_busy_does_not_spend_cd(self):
        p = self.player('mage'); p.mana = 0; p.bonus_cooldown_until = self.clock()+2
        await self.g.cast_spell(p, KEY)
        self.assertEqual(p.mana, 0); self.assertNotIn(KEY, p.spell_cooldowns)
        self.clock.advance(2)
        await self.g.cast_spell(p, KEY); self.assertEqual(p.mana, 20)

    async def test_rapid_parallel_commands_restore_only_once(self):
        p = self.player('mage', 80); p.mana = 0
        before = len(p.spell_history)
        await asyncio.gather(*(self.g.cast_spell(p, KEY) for _ in range(25)))
        self.assertEqual(p.mana, caster.recovery_amount(p))
        self.assertEqual(len(p.spell_history), before+1)
        self.assertEqual(len([e for e in self.g.effects if e.get('spell_id')==KEY]), 1)

    async def test_cooldown_boundary_and_no_early_reuse(self):
        p = self.player('mage'); p.mana = 0
        await self.g.cast_spell(p, KEY); p.mana = 0
        self.clock.advance(179)
        await self.g.cast_spell(p, KEY); self.assertEqual(p.mana, 0)
        self.clock.advance(1)
        await self.g.cast_spell(p, KEY); self.assertEqual(p.mana, 20)
        self.assertEqual(p.spell_cooldowns[KEY], self.clock()+180)

    async def test_immediate_persistence_and_real_load(self):
        p = self.player('mage'); self.account(p); p.mana = 0
        await self.g.cast_spell(p, KEY)
        raw = json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?', (p.id,)).fetchone()[0])
        self.assertEqual(raw['mana'], 20); self.assertEqual(raw['spell_cooldowns'][KEY], self.clock()+180)
        self.clock.advance(10)
        q = self.g.load_player(p.id, p.name, p.ws, raw); q.mana = 0
        await self.g.cast_spell(q, KEY)
        self.assertEqual(q.mana, 0); self.assertEqual(q.spell_cooldowns[KEY], self.clock()+170)

    async def test_previous_version_cooldown_is_not_reset(self):
        p = self.player('mage'); raw = p.save_data(); raw['spell_cooldowns'] = {KEY: self.clock()+99}; raw['mana'] = 0
        q = self.g.load_player(p.id, p.name, p.ws, raw)
        await self.g.cast_spell(q, KEY)
        self.assertEqual(q.mana, 0); self.assertEqual(q.spell_cooldowns[KEY], self.clock()+99)

    async def test_dead_transformed_and_disconnected_cannot_use(self):
        for state in ('dead', 'form', 'disconnected'):
            with self.subTest(state=state):
                p = self.player('mage'); p.mana = 0
                if state=='dead': p.hp = 0
                if state=='form': p.form = 'cat'
                if state=='disconnected': p.ws = None
                await self.g.cast_spell(p, KEY)
                self.assertEqual(p.mana, 0); self.assertNotIn(KEY, p.spell_cooldowns)

    async def test_other_classes_do_not_gain_recovery(self):
        for cls in ('knight', 'ranger', 'druid'):
            with self.subTest(cls=cls):
                p = self.player(cls, 100); p.mana = 0
                await self.g.cast_spell(p, KEY)
                self.assertEqual(p.mana, 0); self.assertNotIn(KEY, p.spell_cooldowns)

    async def test_invalid_targets_do_not_spend_recovery(self):
        p = self.player('mage'); p.mana = 0
        for target in ({}, [], 1): await self.g.cast_spell(p, KEY, target_id=target)
        await self.g.cast_spell(p, KEY, enemy_id=self.e.id, target_id=p.id)
        self.assertEqual(p.mana, 0); self.assertNotIn(KEY, p.spell_cooldowns)

    async def test_ritual_path_cannot_bypass_recovery_cd(self):
        p = self.player('mage'); p.mana = 0
        for ritual in (False, True): await self.g.start_caster_channel(p, KEY, ritual)
        self.g.complete_channel(p)
        self.assertEqual(p.mana, 0); self.assertFalse(p.casting_channel); self.assertNotIn(KEY, p.spell_cooldowns)

    async def test_recovery_during_ritual_is_rejected_without_cancelling_ritual(self):
        p = self.player('mage'); p.mana = 0
        await self.g.start_caster_channel(p, 'alarm', True)
        channel = copy.deepcopy(p.casting_channel)
        await self.g.cast_spell(p, KEY)
        self.assertEqual(p.casting_channel, channel); self.assertEqual(p.mana, 0)
        self.assertNotIn(KEY, p.spell_cooldowns)
        self.g.cancel_channel(p, '')
        await self.g.cast_spell(p, KEY); self.assertEqual(p.mana, 20)

    async def test_regeneration_delay_is_unchanged(self):
        p = self.player('mage'); p.mana = 0; p.mana_recovery_until = self.clock()+12
        await self.g.cast_spell(p, KEY)
        self.assertEqual(p.mana_recovery_until, self.clock()+12)

    async def test_untrained_armor_does_not_block_class_feature(self):
        p = self.player('mage'); p.mana = 0; item = make_item('fighter_chain_mail')
        p.inventory.append(item); p.equipment['armor'] = item['uid']
        await self.g.cast_spell(p, KEY)
        self.assertEqual(p.mana, 20)

    async def test_rituals_still_need_channel_outside_combat(self):
        p = self.player('mage'); p.mana = 0; p.combat_until = self.clock()+20
        await self.g.start_caster_channel(p, 'alarm', True)
        self.assertFalse(p.casting_channel)
        p.combat_until = 0
        await self.g.start_caster_channel(p, 'alarm', True)
        self.assertEqual(p.casting_channel['total'], 10); self.assertNotIn(p.id, self.g.alarms)
        self.clock.advance(10); self.g.tick_dnd(.1)
        self.assertIn(p.id, self.g.alarms); self.assertEqual(p.mana, 0)
