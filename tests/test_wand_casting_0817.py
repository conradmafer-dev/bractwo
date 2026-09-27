"""0.8.17: targeting a creature must not steal a spell's action with a wand spark.

All cases invoke authoritative handlers and a deterministic clock, not UI fakes.
The existing action economy, target protections, mana and caster features remain.
"""
import copy
import unittest
from unittest.mock import patch
import test_dnd as base
from server.server import Player, make_item, ITEMS
from server import combat_rules as rules, dnd_content as dnd


class WandCasting(unittest.IsolatedAsyncioTestCase):
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account

    def setUp(self):
        base.GameRules.setUp(self)
        self.p=self.player('mage')
        self.e.x=1200

    async def select(self):
        await self.g.on_packet(self.p.ws, {'type':'select_target','enemy_id':self.e.id})

    async def queue(self,key='magic_missile'):
        await self.select()
        await self.g.on_packet(self.p.ws, {'type':'attack','enemy_id':self.e.id})
        await self.g.on_packet(self.p.ws, {'type':'cast','spell_id':key,'enemy_id':self.e.id})
        self.assertEqual(self.p.pending_spell.get('spell'),key)

    async def test_select_only_does_not_spend_or_repeat_main_actions(self):
        await self.select()
        before=(self.e.hp,self.p.mana,self.p.attack_cooldown_until)
        for _ in range(5):
            await self.g.process_player_actions();self.clock.advance()
            self.assertEqual((self.e.hp,self.p.mana,self.p.attack_cooldown_until),before)
        self.assertEqual(self.p.auto_enemy_id,self.e.id)
        self.assertFalse(self.p.combat_log)

    async def test_select_then_first_spell_is_immediate(self):
        await self.select();await self.g.process_player_actions()
        await self.g.on_packet(self.p.ws,{'type':'cast','spell_id':'magic_missile'})
        self.assertEqual(self.e.hp,987)
        self.assertEqual(self.p.mana,20)
        self.assertEqual(self.p.attack_cooldown_until,self.clock()+3)
        self.assertFalse(self.p.pending_spell)

    async def test_no_automatic_spark_between_manually_chosen_spells(self):
        await self.select()
        await self.g.cast_spell(self.p,'fire_bolt',self.e.id)
        hp=self.e.hp
        self.clock.advance(9)
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp,hp)
        await self.g.cast_spell(self.p,'ray_of_frost',self.e.id)
        self.assertEqual(self.p.last_roll['action'],'Promień mrozu')
        self.assertLess(self.e.hp,hp)
        self.assertTrue(self.g.enemy_condition(self.e,'slow'))

    async def test_explicit_space_attack_is_still_a_normal_spark(self):
        await self.select()
        await self.g.on_packet(self.p.ws,{'type':'attack'})
        self.assertEqual(self.p.last_roll['action'],'Iskra różdżki')
        self.assertEqual(self.p.last_roll['damage_dice'],'1k4')
        hp=self.e.hp
        await self.g.on_packet(self.p.ws,{'type':'attack'})
        self.assertEqual(self.e.hp,hp)
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.e.hp,hp)
        await self.g.on_packet(self.p.ws,{'type':'attack'})
        self.assertLess(self.e.hp,hp)

    async def test_manual_untargeted_spark_still_picks_nearest_enemy(self):
        await self.g.on_packet(self.p.ws,{'type':'attack'})
        self.assertEqual(self.p.last_roll['action'],'Iskra różdżki')
        self.assertEqual(self.e.hp,996)

    async def test_queued_spell_waits_for_three_second_shared_action(self):
        await self.queue();hp=self.e.hp;mana=self.p.mana
        for advance in (1,1,.99):
            self.clock.advance(advance);await self.g.process_player_actions()
            self.assertEqual(self.e.hp,hp);self.assertEqual(self.p.mana,mana)
        self.clock.advance(.011);await self.g.process_player_actions()
        self.assertEqual(self.e.hp,hp-12);self.assertEqual(self.p.mana,mana-20)
        self.assertFalse(self.p.pending_spell)

    async def test_held_space_cannot_steal_newly_ready_queued_action(self):
        await self.queue();hp=self.e.hp;self.clock.advance(3)
        for _ in range(12):await self.g.on_packet(self.p.ws,{'type':'attack'})
        self.assertEqual(self.e.hp,hp)
        await self.g.process_player_actions()
        self.assertEqual(self.p.last_roll['action'],'Magiczny pocisk')
        self.assertEqual(self.e.hp,hp-12)

    async def test_same_target_reselect_keeps_queued_spell_and_deadline(self):
        await self.queue();pending=copy.deepcopy(self.p.pending_spell)
        for _ in range(10):await self.select()
        self.assertEqual(self.p.pending_spell,pending)
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.p.last_roll['action'],'Magiczny pocisk')

    async def test_changed_target_cancels_queue_without_retargeting_it(self):
        await self.queue();e2=self.enemy('other',x=1250)
        hp=self.e.hp;mana=self.p.mana
        await self.g.select_combat_target(self.p,{'enemy_id':e2.id})
        self.clock.advance();await self.g.process_player_actions()
        self.assertFalse(self.p.pending_spell)
        self.assertEqual((self.e.hp,e2.hp,self.p.mana),(hp,999,mana))

    async def test_clear_target_cancels_queue_without_mana_cost(self):
        await self.queue();hp=self.e.hp;mana=self.p.mana
        await self.g.select_combat_target(self.p,{})
        self.clock.advance();await self.g.process_player_actions()
        self.assertFalse(self.p.pending_spell);self.assertEqual(self.e.hp,hp);self.assertEqual(self.p.mana,mana)

    async def test_latest_queued_spell_replaces_previous_one_not_a_cast_burst(self):
        await self.queue()
        await self.g.cast_spell(self.p,'fire_bolt',self.e.id)
        await self.g.cast_spell(self.p,'ray_of_frost',self.e.id)
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.p.last_roll['action'],'Promień mrozu')
        hp=self.e.hp
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.e.hp,hp);self.assertEqual(self.p.mana,40)

    async def test_immediate_spell_at_ready_time_replaces_older_queue(self):
        await self.queue('fire_bolt');self.clock.advance(3)
        await self.g.cast_spell(self.p,'magic_missile',self.e.id)
        self.assertFalse(self.p.pending_spell)
        hp=self.e.hp;self.clock.advance(3);await self.g.process_player_actions()
        self.assertEqual(self.e.hp,hp)
        self.assertEqual(self.p.spell_history,['magic_missile'])

    async def test_recovery_preserves_queued_spell_and_movement(self):
        self.p.mana=20;self.p.dx=.707;self.p.dy=-.707
        await self.queue();pending=copy.deepcopy(self.p.pending_spell)
        await self.g.cast_spell(self.p,'arcane_recovery')
        self.assertEqual(self.p.pending_spell,pending)
        self.assertEqual((self.p.dx,self.p.dy),(.707,-.707));self.assertEqual(self.p.mana,40)
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.p.mana,20);self.assertEqual(self.p.last_roll['action'],'Magiczny pocisk')
        self.assertEqual(self.p.spell_cooldowns['arcane_recovery'],1000+180)

    async def test_shield_toggle_preserves_queued_spell(self):
        await self.queue();pending=copy.deepcopy(self.p.pending_spell)
        await self.g.cast_spell(self.p,'shield')
        self.assertTrue(self.p.shield_armed);self.assertEqual(self.p.pending_spell,pending)
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.p.last_roll['action'],'Magiczny pocisk')

    async def test_expired_queue_cannot_block_explicit_attack_forever(self):
        await self.queue();hp=self.e.hp;self.clock.advance(4.1)
        await self.g.on_packet(self.p.ws,{'type':'attack'})
        self.assertFalse(self.p.pending_spell);self.assertLess(self.e.hp,hp)
        self.assertEqual(self.p.mana,40)

    async def test_expired_queue_is_removed_even_during_longer_action(self):
        await self.queue();self.p.attack_cooldown_until=self.clock()+30
        self.clock.advance(4.1);await self.g.process_player_actions()
        self.assertFalse(self.p.pending_spell)

    async def test_failed_delayed_cast_does_not_fall_back_to_spark(self):
        await self.queue();hp=self.e.hp;self.p.mana=0
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual(self.e.hp,hp);self.assertEqual(self.p.mana,0)
        self.assertFalse(self.p.pending_spell)

    async def test_queued_spell_rechecks_range_and_line_of_sight(self):
        for failure in ('range','wall','floor','death'):
            with self.subTest(failure=failure):
                self.p=self.player('mage');self.e=self.enemy('dummy',x=1200)
                await self.queue();hp=self.e.hp
                if failure=='range':self.e.x=5000
                elif failure=='floor':self.e.floor=-1
                elif failure=='death':self.e.alive=False
                self.clock.advance()
                with patch.object(self.g,'line_clear',return_value=failure!='wall'):
                    await self.g.process_player_actions()
                self.assertEqual(self.e.hp,hp);self.assertEqual(self.p.mana,40)
                self.assertFalse(self.p.pending_spell)

    async def test_implicit_target_is_frozen_when_cast_is_queued(self):
        await self.select();await self.g.attack(self.p,enemy_id=self.e.id)
        await self.g.cast_spell(self.p,'magic_missile')
        self.assertEqual(self.p.pending_spell['enemy'],self.e.id)

    async def test_focus_resume_and_unlock_packets_never_start_sparks(self):
        await self.select()
        for kind in ({'type':'auto_pause','paused':True},{'type':'auto_pause','paused':False},{'type':'pvp_safety','enabled':False}):
            await self.g.on_packet(self.p.ws,kind);await self.g.process_player_actions()
        self.assertEqual(self.e.hp,999);self.assertEqual(self.p.attack_cooldown_until,0)

    async def test_zero_mana_cantrip_remains_available_without_spark(self):
        await self.select();self.p.mana=0
        await self.g.cast_spell(self.p,'magic_missile',self.e.id)
        await self.g.process_player_actions();self.assertEqual(self.e.hp,999)
        await self.g.cast_spell(self.p,'fire_bolt',self.e.id)
        self.assertLess(self.e.hp,999);self.assertEqual(self.p.mana,0)

    async def test_ranger_knight_and_melee_druid_still_autoattack(self):
        for cls in ('knight','ranger','druid'):
            with self.subTest(cls=cls):
                self.p=self.player(cls);self.e.x=1160;self.e.hp=999;self.e.alive=True
                await self.select();await self.g.process_player_actions()
                self.assertLess(self.e.hp,999)
                self.assertTrue(self.p.public(self.clock(),private=True)['weapon_auto_attack'])

    async def test_mage_with_melee_weapon_uses_weapon_rules_not_class_exemption(self):
        item=make_item('druid_weapon_1');self.p.inventory.append(item);self.p.equipment['weapon']=item['uid']
        self.e.x=1160;await self.select();await self.g.process_player_actions()
        self.assertLess(self.e.hp,999);self.assertNotEqual(self.p.last_roll['action'],'Iskra różdżki')

    async def test_all_arcane_focuses_are_manual_including_upgraded_wands(self):
        found=0
        for key,item in ITEMS.items():
            if not rules.gear.is_focus(item):continue
            found+=1;w=make_item(key);self.p.inventory.append(w);self.p.equipment['weapon']=w['uid']
            self.assertFalse(rules.weapon_autoattack(self.p),key)
        self.assertGreater(found,5)
        self.assertTrue(rules.weapon_autoattack(Player('2','Test',class_id='druid',form='wolf')))

    async def test_public_state_explains_focus_behavior_and_queue(self):
        await self.queue();public=self.p.public(self.clock(),private=True)
        self.assertFalse(public['weapon_auto_attack']);self.assertEqual(public['queued_spell'],'magic_missile')
        self.assertEqual(public['action_remaining'],3);self.assertFalse(self.g.metadata()['combat_rules']['focus_auto_attack'])

    async def test_target_and_queue_do_not_stop_movement(self):
        self.p.dx=.6;self.p.dy=.8;self.p.input_time=self.g.time
        before=self.p.dx,self.p.dy,self.p.input_time
        await self.queue();await self.select()
        self.clock.advance();await self.g.process_player_actions()
        self.assertEqual((self.p.dx,self.p.dy,self.p.input_time),before)

    async def test_save_format_and_mana_growth_do_not_change(self):
        self.p.level=6;self.p.mana=48;self.account(self.p)
        saved=self.p.save_data();loaded=self.g.load_player(self.p.id,self.p.name,self.p.ws,saved)
        self.assertEqual(loaded.max_mana,96);self.assertEqual(loaded.mana,48)
        self.assertNotIn('weapon_auto_attack',saved)
        self.assertFalse(loaded.pending_spell);self.assertEqual(loaded.mana_rules_version,3)

    async def test_selected_player_gets_no_spark_but_legal_spell_works(self):
        self.p.level=20;self.p.pvp_safety=False;self.p.mana=self.p.max_mana
        q=self.player('mage',20,'2');q.x=1200
        hp=q.hp
        await self.g.select_combat_target(self.p,{'target_id':q.id})
        await self.g.process_player_actions();self.assertEqual(q.hp,hp)
        await self.g.cast_spell(self.p,'magic_missile',target_id=q.id)
        self.assertLess(q.hp,hp)

    async def test_selected_protected_player_stays_safe_from_spell_and_spark(self):
        self.p.level=20;self.p.pvp_safety=True
        q=self.player('mage',20,'2');q.x=1200;hp=q.hp;mana=self.p.mana
        await self.g.select_combat_target(self.p,{'target_id':q.id})
        await self.g.process_player_actions()
        await self.g.cast_spell(self.p,'magic_missile',target_id=q.id)
        await self.g.on_packet(self.p.ws,{'type':'attack','target_id':q.id})
        self.assertEqual(q.hp,hp);self.assertEqual(self.p.mana,mana)

    async def test_auto_target_death_clears_even_when_wand_auto_is_disabled(self):
        await self.select();self.e.alive=False
        await self.g.process_player_actions()
        self.assertFalse(self.p.auto_enabled);self.assertFalse(self.p.auto_enemy_id)

if __name__=='__main__':unittest.main()
