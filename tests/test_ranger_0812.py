"""Ranger 0.8.12: resources, concentration, weapon trigger, escapes and migration."""
import json
import unittest
from unittest.mock import patch
import test_dnd as base
from server.server import Player
from server import dnd_content as dnd, combat_rules as rules, spell_scaling
from server.ranger_magic import ENSNARING

class RangerData(unittest.TestCase):
    def test_three_initial_spells_and_no_features_or_cantrips(self):
        p=Player('1','R',class_id='ranger')
        self.assertEqual({k for k in dnd.SPELLS if dnd.spell_allowed(p,k)}, {'hunters_mark',ENSNARING,'cure_wounds'})
        self.assertEqual(p.max_mana,40)
    def test_gates_and_longstrider(self):
        for level in range(1,106):
            p=Player('1','R',class_id='ranger',level=level)
            self.assertEqual(dnd.circle_for('ranger',level),min(5,1+level//20))
            self.assertEqual(dnd.spell_allowed(p,'longstrider'),level>=5)
            self.assertEqual(dnd.spell_allowed(p,'animal_companion'),level>=10)
            self.assertEqual(rules.attacks_per_round(p),2 if level>=20 else 1)
    def test_mana_budget(self):
        for level,expected in [(1,40),(5,49),(10,60),(20,140),(40,270),(60,380),(80,570),(95,640)]:
            self.assertEqual(Player('1','R',class_id='ranger',level=level).max_mana,expected,level)
    def test_all_power_choices_of_mark_are_free(self):
        p=Player('1','R',class_id='ranger',level=100)
        for rank in (1,3,5):
            p.spell_circle_choices={'hunters_mark':rank}
            s=spell_scaling.resolve(p,'hunters_mark')
            self.assertEqual(s['mana'],0);self.assertEqual(s['cooldown'],30)
            self.assertEqual(s['dice'],[1,6,0])
    def test_ensnaring_scales_every_ranger_circle_not_character_level(self):
        for level,n in [(1,1),(19,1),(20,2),(39,2),(40,3),(80,5)]:
            p=Player('1','R',class_id='ranger',level=level)
            s=spell_scaling.resolve(p,ENSNARING)
            self.assertEqual(s['dice'],[n,6,0]);self.assertEqual(s['duration'],30)
    def test_knight_mage_and_druid_start_unchanged(self):
        expected={'knight':(12,30,0),'mage':(8,40,1),'druid':(10,40,1)}
        for cls,(hp,mana,circle) in expected.items():
            p=Player('1','T',class_id=cls)
            self.assertEqual((p.max_hp,p.max_mana,dnd.circle_for(cls,1)),(hp,mana,circle))
            self.assertFalse(dnd.spell_allowed(p,ENSNARING))
    def test_authoritative_class_levels_match_every_spec(self):
        for s in dnd.SPELLS.values():
            for cls in s['class_ids']:self.assertEqual(s['class_levels'][cls],dnd.spell_level(s,cls))

class RangerReceipts(unittest.TestCase):
    def receipt(self,level):
        from server import level_up
        p=Player('1','R',class_id='ranger',level=level)
        level_up.record(p,level,level)
        return level_up.pending(p)['pending_level_ups'][0]['rows']
    def test_level_five_unlocks_longstrider_without_another_circle(self):
        rows=self.receipt(5)
        self.assertTrue(any('Długonogi' in str(r) for r in rows))
        self.assertFalse(any(r.get('label')=='Krąg czarów' for r in rows))
    def test_level_twenty_shows_exact_ensnaring_damage_increment(self):
        rows=self.receipt(20)
        self.assertTrue(any(r.get('label')=='Uderzenie oplątujące' and r['gain']=='+1k6' for r in rows))
        self.assertFalse(any(r.get('label')=='Znak łowcy' and 'koszt' in r.get('unit','') for r in rows))

class RangerGame(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account
    def ranger(self,level=1):
        p=self.player('ranger',level);self.e.kind='bandit';self.e.ready=100000
        return p
    def advance(self,seconds=3):
        self.clock.advance(seconds);self.g.time+=seconds
    async def snare(self,p=None,target=None):
        p=p or self.ranger();target=target or self.e
        await self.g.cast_spell(p,ENSNARING)
        self.assertTrue(self.g.trigger_ensnaring_strike(p,target,{'hit':True}))
        self.assertIn('restrained',self.g.target_conditions(target))
        return p
    async def test_mark_free_even_zero_mana_and_bonus_only(self):
        p=self.ranger();p.mana=0
        await self.g.cast_spell(p,'hunters_mark',self.e.id)
        self.assertEqual(p.concentration,'hunters_mark');self.assertEqual(p.mana,0)
        self.assertEqual(p.spell_cooldowns['hunters_mark'],self.clock()+30)
        self.assertEqual(p.attack_cooldown_until,0);self.assertGreater(p.bonus_cooldown_until,self.clock())
    async def test_mark_cd_prevents_transfer_and_persists_on_death(self):
        p=self.ranger();second=self.enemy('second',kind='bandit')
        await self.g.cast_spell(p,'hunters_mark',self.e.id);cd=p.spell_cooldowns['hunters_mark']
        self.advance(3);await self.g.cast_spell(p,'hunters_mark',second.id)
        self.assertEqual(p.mark_target,self.e.id)
        self.e.hp=0;await self.g.defeat(self.e)
        await self.g.cast_spell(p,'hunters_mark',second.id)
        self.assertEqual(p.spell_cooldowns['hunters_mark'],cd)
        self.advance(27);await self.g.cast_spell(p,'hunters_mark',second.id)
        self.assertEqual(p.mark_target,second.id);self.assertEqual(p.mana,p.max_mana)
    async def test_mark_cd_survives_save_migration(self):
        p=self.ranger();await self.g.cast_spell(p,'hunters_mark',self.e.id)
        data=json.loads(json.dumps(p.save_data()));q=Player('2','R',class_id='ranger')
        for k,v in data.items():
            if hasattr(q,k):setattr(q,k,v)
        self.g.migrate_dnd(q,data)
        self.assertEqual(q.spell_cooldowns['hunters_mark'],self.clock()+30)
        self.assertFalse(q.concentration)
    async def test_mark_one_per_caster_replaces_old_status(self):
        p=self.ranger();second=self.enemy('second',kind='bandit')
        await self.g.cast_spell(p,'hunters_mark',self.e.id);self.advance(30)
        await self.g.cast_spell(p,'hunters_mark',second.id)
        self.assertNotIn('hunters_mark:'+p.id,self.e.conditions)
        self.assertIn('hunters_mark:'+p.id,second.conditions)
    async def test_mark_status_is_visible_on_enemy_and_caster(self):
        p=self.ranger();await self.g.cast_spell(p,'hunters_mark',self.e.id)
        own=dnd.status_effects(p.buffs,self.clock(),p);enemy=dnd.status_effects(self.e.conditions,self.clock())
        self.assertTrue(any(s.get('spell_id')=='hunters_mark' for s in own))
        self.assertTrue(any(s.get('spell_id')=='hunters_mark' and s['harmful'] for s in enemy))
    async def test_mark_single_hit_adds_one_d6_without_extra_drain(self):
        p=self.ranger();await self.g.cast_spell(p,'hunters_mark',self.e.id)
        await self.g.attack(p,enemy_id=self.e.id)
        self.assertEqual(self.e.hp,990);self.assertEqual(p.mana,40)
    async def test_mark_cannot_be_cast_on_safe_missing_or_wrong_floor_target(self):
        for mode in ['missing','safe','floor','far']:
            p=self.ranger();self.e.x=1170;self.e.floor=0
            if mode=='safe':self.e.x=560
            if mode=='floor':self.e.floor=-1
            if mode=='far':self.e.x=6000
            await self.g.cast_spell(p,'hunters_mark','missing' if mode=='missing' else self.e.id)
            self.assertFalse(p.concentration);self.assertNotIn('hunters_mark',p.spell_cooldowns)
    async def test_arming_costs_nothing_preserves_mark_and_no_favorite_use(self):
        p=self.ranger();await self.g.cast_spell(p,'hunters_mark',self.e.id)
        history=list(p.spell_history);bonus=p.bonus_cooldown_until
        await self.g.cast_spell(p,ENSNARING)
        self.assertTrue(p.ensnaring_armed);self.assertEqual(p.mana,40)
        self.assertEqual(p.concentration,'hunters_mark');self.assertEqual(history,p.spell_history)
        self.assertEqual(bonus,p.bonus_cooldown_until)
    async def test_cancel_arm_with_zero_mana(self):
        p=self.ranger();await self.g.cast_spell(p,ENSNARING);p.mana=0
        await self.g.cast_spell(p,ENSNARING);self.assertFalse(p.ensnaring_armed)
    async def test_cannot_arm_without_mana(self):
        p=self.ranger();p.mana=19;await self.g.cast_spell(p,ENSNARING)
        self.assertFalse(p.ensnaring_armed)
    async def test_miss_does_not_consume_arm_or_resources(self):
        p=self.ranger();self.g.combat_rng=base.Dice(1)
        await self.g.cast_spell(p,ENSNARING);await self.g.attack(p,enemy_id=self.e.id)
        self.assertTrue(p.ensnaring_armed);self.assertEqual(p.mana,40);self.assertFalse(p.concentration)
    async def test_dead_target_does_not_consume_arm(self):
        p=self.ranger();await self.g.cast_spell(p,ENSNARING);self.e.hp=0
        self.assertFalse(self.g.trigger_ensnaring_strike(p,self.e,{'hit':True}));self.assertEqual(p.mana,40)
        self.assertTrue(p.ensnaring_armed)
    async def test_weapon_hit_activates_once_and_uses_bonus(self):
        p=self.ranger();await self.g.cast_spell(p,ENSNARING)
        await self.g.attack(p,enemy_id=self.e.id)
        self.assertFalse(p.ensnaring_armed);self.assertEqual(p.mana,20);self.assertIn('restrained',self.e.conditions)
        self.assertEqual(p.concentration,ENSNARING);self.assertGreater(p.bonus_cooldown_until,self.clock())
        self.assertEqual(p.spell_history[-1],ENSNARING)
        self.advance();await self.g.attack(p,enemy_id=self.e.id);self.assertEqual(p.mana,20)
    async def test_busy_bonus_waits_for_later_hit(self):
        p=self.ranger();await self.g.cast_spell(p,'hunters_mark',self.e.id);await self.g.cast_spell(p,ENSNARING)
        await self.g.attack(p,enemy_id=self.e.id)
        self.assertTrue(p.ensnaring_armed);self.assertEqual(p.concentration,'hunters_mark')
        self.advance();await self.g.attack(p,enemy_id=self.e.id)
        self.assertFalse(p.ensnaring_armed);self.assertEqual(p.concentration,ENSNARING)
        self.assertNotIn('hunters_mark:'+p.id,self.e.conditions)
    async def test_initial_save_success_still_spends_cast(self):
        p=self.ranger();self.g.combat_rng=base.Dice(20)
        await self.g.cast_spell(p,ENSNARING)
        self.assertTrue(self.g.trigger_ensnaring_strike(p,self.e,{'hit':True}))
        self.assertEqual(p.mana,20);self.assertFalse(p.concentration);self.assertNotIn('restrained',self.e.conditions)
    async def test_large_initial_save_has_advantage_not_escape_check(self):
        p=self.ranger();self.e.kind='ogre';self.g.combat_rng=base.Dice(1)
        await self.snare(p);self.assertEqual(self.g.combat_rng.checks,2)
        self.g.try_restraint_escape(self.e,self.e,self.e.conditions['restrained'],p)
        self.assertEqual(self.g.combat_rng.checks,3)
    async def test_ten_damage_turns_including_last_without_extra_frames(self):
        p=await self.snare();hp=self.e.hp
        for i in range(10):
            self.advance();self.g.tick_dnd(3);self.g.tick_dnd(0)
            self.assertEqual(self.e.hp,hp-3*(i+1))
        self.assertFalse(p.concentration);self.assertNotIn('restrained',self.e.conditions)
    async def test_paid_damage_does_not_grow_after_level_up(self):
        p=await self.snare();p.level=80;hp=self.e.hp
        self.advance();self.g.tick_dnd(3);self.assertEqual(self.e.hp,hp-3)
    async def test_monster_uses_attack_turn_for_escape_failure(self):
        p=await self.snare();self.e.ready=0;self.g.combat_rng=base.Dice(1)
        self.advance();self.g.tick_dnd(3)
        self.assertIn('restrained',self.e.conditions);self.assertGreaterEqual(self.e.ready,self.g.time+3)
        self.assertGreaterEqual(self.e.ranged_ready,self.g.time+3)
    async def test_monster_escape_success_ends_concentration(self):
        p=await self.snare();self.e.ready=0;self.g.combat_rng=base.Dice(20)
        self.advance();self.g.tick_dnd(3)
        self.assertNotIn('restrained',self.e.conditions);self.assertFalse(p.concentration)
    async def test_stop_concentration_removes_vines_and_damage(self):
        p=await self.snare();self.g.break_concentration(p);hp=self.e.hp
        self.advance();self.g.tick_dnd(3);self.assertEqual(self.e.hp,hp);self.assertFalse(self.e.conditions)
    async def test_recasting_mark_breaks_vines_but_stays_free(self):
        p=await self.snare();self.advance();await self.g.cast_spell(p,'hunters_mark',self.e.id)
        self.assertEqual(p.mana,20);self.assertEqual(p.concentration,'hunters_mark');self.assertNotIn('restrained',self.e.conditions)
    async def test_healing_does_not_break_mark(self):
        p=self.ranger();p.hp=1;await self.g.cast_spell(p,'hunters_mark',self.e.id)
        await self.g.cast_spell(p,'cure_wounds')
        self.assertEqual(p.hp,9);self.assertEqual(p.mana,20);self.assertEqual(p.concentration,'hunters_mark')
    async def test_deselection_does_not_reset_mark_or_cd(self):
        p=self.ranger();await self.g.cast_spell(p,'hunters_mark',self.e.id);p.auto_enabled=False;p.auto_enemy_id=''
        self.advance();self.g.tick_dnd(3)
        self.assertEqual(p.mark_target,self.e.id);self.assertEqual(p.spell_cooldowns['hunters_mark'],1030)
    async def test_forbidden_high_circle_packet_never_crashes(self):
        p=self.ranger()
        for key in ['wish','meteor_swarm','foresight']:
            if key in dnd.SPELLS:await self.g.cast_spell(p,key,self.e.id)
        self.assertEqual(p.mana,40)
    async def test_old_mana_percent_migrates_once(self):
        for level,oldmax in [(1,35),(19,35),(20,40),(40,140),(80,380)]:
            p=self.player('ranger',level);saved=p.save_data();saved['mana_rules_version']=1;saved['mana']=oldmax*.5;p.mana=saved['mana']
            self.g.migrate_dnd(p,saved);self.assertEqual(p.mana,p.max_mana*.5,(level,p.mana,p.max_mana))
            before=p.mana;self.g.migrate_dnd(p,p.save_data());self.assertEqual(p.mana,before)
    def duel(self):
        p=self.ranger(8);q=self.player('mage',8,'2');q.x=1200;p.pvp_safety=False
        return p,q
    async def test_pvp_mark_and_vines(self):
        p,q=self.duel();await self.g.cast_spell(p,'hunters_mark',target_id=q.id)
        self.assertEqual(p.mana,p.max_mana);self.assertIn('hunters_mark:'+p.id,q.buffs)
        self.advance();await self.snare(p,q)
        self.assertTrue(q.buffs['restrained']['escape_action']);self.assertEqual(q.speed,0)
        self.assertGreater(q.aggressors.get(p.id,0),self.clock())
    async def test_pvp_escape_costs_action_on_failure_no_mana(self):
        p,q=self.duel();await self.snare(p,q);self.g.combat_rng=base.Dice(1);mana=q.mana
        await self.g.escape_restraint(q)
        self.assertIn('restrained',q.buffs);self.assertGreater(q.attack_cooldown_until,self.clock());self.assertEqual(q.mana,mana)
        self.g.combat_rng=base.Dice(20);await self.g.escape_restraint(q)
        self.assertIn('restrained',q.buffs)
        self.advance();await self.g.escape_restraint(q)
        self.assertNotIn('restrained',q.buffs);self.assertFalse(p.concentration)
    async def test_pvp_safety_blocks_trigger_even_client_fakes_hit(self):
        p,q=self.duel();p.pvp_safety=True;await self.g.cast_spell(p,ENSNARING)
        self.assertFalse(self.g.trigger_ensnaring_strike(p,q,{'hit':True}));self.assertEqual(p.mana,p.max_mana)
    async def test_pvp_lock_cancels_existing_vines(self):
        p,q=self.duel();await self.snare(p,q);p.pvp_safety=True;self.g.cancel_player_hostility(p)
        self.assertNotIn('restrained',q.buffs);self.assertFalse(p.concentration)
    async def test_escape_help_requires_party_and_melee_range(self):
        p,q=self.duel();await self.snare(p,q);ally=self.player('knight',8,'3');ally.x=q.x+20
        self.g.combat_rng=base.Dice(20)
        await self.g.escape_restraint(ally,q.id);self.assertIn('restrained',q.buffs)
        ally.party_id=q.party_id='party';ally.pvp_safety=False
        await self.g.escape_restraint(ally,q.id);self.assertNotIn('restrained',q.buffs)
        self.assertGreater(ally.attack_cooldown_until,self.clock())
    async def test_periodic_kill_is_awarded(self):
        p=await self.snare();self.e.hp=2;xp=p.xp
        self.advance();self.g.tick_dnd(3)
        # Death application is deferred to the normal game step / defeat queue.
        await self.g.process_player_actions()
        self.assertEqual(self.e.hp,0);self.assertFalse(p.concentration)
        self.assertGreater(p.xp,xp);self.assertFalse(self.e.alive)
    async def test_no_armed_state_is_persisted(self):
        p=self.ranger();await self.g.cast_spell(p,ENSNARING)
        self.assertNotIn('ensnaring_armed',p.save_data())
    async def test_status_contains_damage_dice_and_escape_affordance(self):
        p=await self.snare();rows=dnd.status_effects(self.e.conditions,self.clock())
        row=next(s for s in rows if s['id']=='restrained')
        self.assertTrue(row['escape_action']);self.assertIn('1k6',row['description']);self.assertEqual(row['rounds'],10)
