"""0.8 rules + authoritative game regression tests. Run: python -m unittest discover -s tests -v"""
import asyncio
import json
import math
from pathlib import Path
import random
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from aiohttp.test_utils import TestClient, TestServer
from server.server import Game, Player, Enemy, create_app, CLASSES, ITEMS, ENEMY_TYPES, POTIONS, make_item
from server import combat_rules as rules, dnd_content as dnd

class Clock:
    value=1000.0
    def __call__(self):return self.value
    def advance(self,t=3.1):self.value+=t

class WS:
    closed=False
    def __init__(self):self.messages=[]
    async def send_json(self,data):self.messages.append(data)
    async def close(self):self.closed=True

class Dice:
    def __init__(self,d20=10,die=3):self.d20=d20;self.die=die;self.checks=0
    def randint(self,a,b):
        if b==20:self.checks+=1;return self.d20
        return min(b,max(a,self.die))

class PureRules(unittest.TestCase):
    def test_starting_hp(self):
        self.assertEqual({c:Player('1','Test',class_id=c).max_hp for c in CLASSES},{'knight':12,'ranger':12,'mage':8,'druid':10})
    def test_damage_not_linear_in_game_level(self):
        for level,damage in ((1,(1,8,3)),(10000,(1,8,5))):
            p=Player('1','Test',level=level);i=make_item('knight_weapon_1');p.inventory=[i];p.equipment['weapon']=i['uid'];self.assertEqual(rules.weapon_dice(p),damage)
    def test_bounded_proficiency(self):
        self.assertEqual(rules.proficiency(Player('1','A')),2)
        self.assertEqual(rules.proficiency(Player('1','A',level=10000)),6)
    def test_cantrips_scale_without_multiple_casts(self):
        for level,n in ((1,1),(4,1),(5,2),(10,2),(11,3),(17,4),(999,4)):
            p=Player('1','A',class_id='mage',level=level);i=make_item('mage_weapon_1');p.inventory=[i];p.equipment['weapon']=i['uid']
            self.assertEqual(rules.cantrip_count(p),n);self.assertEqual(rules.weapon_dice(p),(1,4,0));self.assertEqual(rules.attacks_per_round(p),1)
    def test_weapon_extra_attacks(self):
        for cls,levels in (('knight',[(1,1),(5,2),(11,3),(20,4)]),('ranger',[(1,1),(5,2),(20,2)]),('druid',[(20,1)])):
            for lv,count in levels:self.assertEqual(rules.attacks_per_round(Player('1','A',class_id=cls,level=lv)),count)
    def test_circles_full(self):
        for level in range(1,25):
            self.assertEqual(dnd.circle_for('mage',level),min(9,1+(level-1)//2));self.assertEqual(dnd.circle_for('druid',level),min(9,1+(level-1)//2))
    def test_circles_ranger(self):
        for level in range(1,25):self.assertEqual(dnd.circle_for('ranger',level),min(5,1+(level-1)//4))
    def test_knight_no_spells(self):self.assertEqual(dnd.circle_for('knight',100),0)
    def test_critical_doubles_dice_not_modifier(self):
        result=rules.roll_attack(Dice(20,4),5,99,(1,8,3))
        self.assertEqual(result['damage'],11);self.assertEqual(result['damage_rolls'],[4,4])
    def test_natural_one_misses(self):self.assertFalse(rules.roll_attack(Dice(1),99,1,(1,8,3))['hit'])
    def test_zero_damage_on_successful_save(self):self.assertEqual(rules.roll_save(Dice(20),0,12,{'damage':9},False)['damage'],0)
    def test_half_damage_round_down(self):self.assertEqual(rules.roll_save(Dice(20),0,12,{'damage':9},True)['damage'],4)
    def test_negative_modifier(self):self.assertEqual(rules.dice_text((1,8,-1)),'1k8-1')
    def test_advantage_disadvantage_cancel(self):
        rng=Dice();r=rules.roll_attack(rng,1,10,(1,6,0),True,True);self.assertEqual(len(r['rolls']),1)
    def test_every_monster_has_explicit_damage_dice(self):
        for key,s in ENEMY_TYPES.items():
            self.assertEqual(len(s['damage_dice']),3,key);self.assertLessEqual(s['armor_class'],22);self.assertGreater(s['hp'],0)
    def test_early_monsters_low_hp(self):self.assertEqual([ENEMY_TYPES[k]['hp'] for k in ('rat','goblin','wolf','boss')],[4,7,11,90])
    def test_potion_dice(self):self.assertEqual(POTIONS['health_potion']['dice'],[2,4,2])
    def test_spell_catalogue(self):
        self.assertEqual(len(dnd.SPELLS),56)
        for s in dnd.SPELLS.values():
            if not s.get('feature') and s['circle']==0:self.assertEqual(s['mana'],0)
        self.assertEqual(dnd.SPELLS['fireball']['dice'],[8,6,0]);self.assertEqual(dnd.SPELLS['magic_missile']['shots'],3)

class GameRules(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock=Clock();self.g=Game(':memory:',clock=self.clock);self.g.combat_rng=Dice()
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[]
        self.p=self.player()
        self.e=self.enemy()
    def tearDown(self):self.g.db.close()
    def player(self,cls='knight',level=1,pid='1'):
        p=Player(pid,'Test'+pid,WS(),class_id=cls,level=level,x=1100,y=1180,gold=1000)
        self.g.starter(p);p.hp=p.max_hp;p.mana=p.max_mana;p.current_wall_time=self.clock()
        self.g.players[pid]=p;return p
    def enemy(self,eid='dummy',x=1170,y=1180,kind='ogre'):
        e=Enemy(eid,kind,x,y,999,x,y);self.g.enemies[eid]=e;self.g.legacy_enemies.append(e);return e
    def account(self,p):
        self.g.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',(int(p.id),p.name,p.name.lower(),b'salt',b'hash',json.dumps(p.save_data())))
        self.g.save_player(p);self.g.db.commit()
    async def test_malformed_cast_target_rejected_without_cost(self):
        p=self.player('druid',7);mana=p.mana
        for target in ([],{},42):await self.g.cast_spell(p,'healing_word',target_id=target)
        await self.g.cast_spell(p,'healing_word',enemy_id=self.e.id,target_id=p.id)
        self.assertEqual(p.mana,mana);self.assertFalse(p.pending_spell)
    async def test_repeated_concentration_spell_free_with_empty_mana(self):
        p=self.player('druid',7);await self.g.cast_spell(p,'call_lightning',self.e.id)
        p.mana=0;before=self.e.hp;self.clock.advance(3.1)
        await self.g.cast_spell(p,'call_lightning',self.e.id)
        self.assertEqual(p.mana,0);self.assertLess(self.e.hp,before)
    async def test_freedom_of_movement_cancels_magical_movement_penalty(self):
        p=self.player('druid',9);base=p.speed
        p.buffs['restrained']={'until':self.clock()+20};self.assertEqual(p.speed,0)
        await self.g.cast_spell(p,'freedom_of_movement');self.assertGreaterEqual(p.speed,base)
    async def test_real_weapon_damage(self):
        await self.g.attack(self.p,enemy_id=self.e.id);self.assertEqual(self.e.hp,993);self.assertEqual(self.p.last_roll['damage_dice'],'1k8+3')
    async def test_attack_cooldown_cannot_spam(self):
        await self.g.attack(self.p,enemy_id=self.e.id);hp=self.e.hp
        for _ in range(10):await self.g.attack(self.p,enemy_id=self.e.id)
        self.assertEqual(hp,self.e.hp)
    async def test_extra_attacks_all_rolled_separately(self):
        self.p.level=20;await self.g.attack(self.p,enemy_id=self.e.id)
        self.assertEqual(self.g.combat_rng.checks,4);self.assertEqual(len(self.p.combat_log),4)
    async def test_druid_basic_melee_range(self):
        p=self.player('druid');self.e.x=1300;await self.g.attack(p,enemy_id=self.e.id);self.assertEqual(self.e.hp,999)
    async def test_druid_shillelagh_bonus_and_primary_attack(self):
        p=self.player('druid');await self.g.cast_spell(p,'shillelagh');self.assertEqual(p.mana,p.max_mana)
        self.assertEqual(rules.weapon_dice(p),(1,8,3));self.assertGreater(p.bonus_cooldown_until,self.clock());self.assertEqual(p.attack_cooldown_until,0)
        await self.g.attack(p,enemy_id=self.e.id);self.assertLess(self.e.hp,999)
    async def test_free_cantrip_with_zero_mana(self):
        p=self.player('mage');p.mana=0;await self.g.cast_spell(p,'fire_bolt',self.e.id)
        self.assertLess(self.e.hp,999);self.assertEqual(p.mana,0)
    async def test_wrong_class_spells_denied(self):
        await self.g.cast_spell(self.p,'fireball',self.e.id);self.assertEqual(self.e.hp,999);self.assertEqual(self.p.mana,self.p.max_mana)
    async def test_first_circle_from_level_one(self):
        p=self.player('mage',1);mana=p.mana
        await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(self.e.hp,987);self.assertEqual(p.mana,mana-20)
    async def test_ranger_early_magic(self):
        p=self.player('ranger',1);await self.g.cast_spell(p,'hunters_mark',self.e.id);self.assertEqual(p.mark_target,self.e.id)
        p.level=5;await self.g.cast_spell(p,'hunters_mark',self.e.id);self.assertEqual(p.mark_target,self.e.id)
    async def test_magic_missile_base_circle_three_automatic_hits(self):
        p=self.player('mage',3);p.spell_circle_choices['magic_missile']=1;self.g.combat_rng=Dice(1,2);await self.g.cast_spell(p,'magic_missile',self.e.id)
        self.assertEqual(self.e.hp,990);self.assertEqual(self.g.combat_rng.checks,0);self.assertEqual(len(p.combat_log),3)
    async def test_scorching_ray_three_attack_rolls(self):
        p=self.player('mage',5);p.spell_circle_choices['scorching_ray']=2;self.e.x=1200;await self.g.cast_spell(p,'scorching_ray',self.e.id)
        self.assertEqual(self.g.combat_rng.checks,3)
    async def test_fireball_save_and_damage(self):
        p=self.player('mage',7);p.spell_circle_choices['fireball']=3;self.g.combat_rng=Dice(1,3);await self.g.cast_spell(p,'fireball',self.e.id)
        self.assertEqual(self.e.hp,999-24);self.assertEqual(p.last_roll['damage_dice'],'8k6')
    async def test_meteor_hits_selected_center_once(self):
        p=self.player('mage',19);self.g.combat_rng=Dice(1,3);await self.g.cast_spell(p,'meteor_swarm',self.e.id)
        self.assertEqual(self.e.hp,879);self.assertEqual(len(p.combat_log),1)
    async def test_healing_uses_dice_and_ability(self):
        p=self.player('druid',3);p.spell_circle_choices['cure_wounds']=1;p.hp=1;await self.g.cast_spell(p,'cure_wounds')
        self.assertEqual(p.hp,10);self.assertEqual(p.last_roll['damage_dice'],'2k8+3')
    async def test_healing_full_hp_no_cost(self):
        p=self.player('druid',3);mana=p.mana;await self.g.cast_spell(p,'cure_wounds');self.assertEqual(p.mana,mana)
    async def test_heal_other_player_only_party(self):
        p=self.player('druid',3);q=self.player(pid='2');q.hp=1
        await self.g.cast_spell(p,'healing_word',target_id=q.id);self.assertEqual(q.hp,1)
        p.party_id=q.party_id='party';await self.g.cast_spell(p,'healing_word',target_id=q.id);self.assertGreater(q.hp,1)
    async def test_friendly_heal_rejects_pvp_combat_while_safety_locked(self):
        p=self.player('druid',3);q=self.player(pid='2');q.hp=1;p.party_id=q.party_id='party';q.pvp_combat_until=2000
        await self.g.cast_spell(p,'cure_wounds',target_id=q.id);self.assertEqual(q.hp,1)
    async def test_hunters_mark_each_attack(self):
        p=self.player('ranger',5);self.e.x=1200;await self.g.cast_spell(p,'hunters_mark',self.e.id)
        before=self.e.hp;await self.g.attack(p,enemy_id=self.e.id)
        self.assertEqual(before-self.e.hp,20);self.assertEqual(p.last_roll['mark_rolls'],[3])
    async def test_one_concentration_only(self):
        p=self.player('druid',5);self.g.combat_rng=Dice(1);await self.g.cast_spell(p,'entangle',self.e.id)
        self.assertTrue(self.g.enemy_condition(self.e,'restrained'));self.clock.advance()
        await self.g.cast_spell(p,'moonbeam',self.e.id);self.assertEqual(p.concentration,'moonbeam');self.assertFalse(self.g.enemy_condition(self.e,'restrained'))
    async def test_damage_breaks_concentration(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'moonbeam',self.e.id);self.g.combat_rng=Dice(1)
        self.g.damage_player(p,2,rolled=True);self.assertFalse(p.concentration);self.assertFalse(self.g.spell_fields)
    async def test_concentration_expires(self):
        p=self.player('ranger',5);await self.g.cast_spell(p,'hunters_mark',self.e.id);self.clock.advance(600*dnd.GAME_ROUND_SECONDS+1);self.g.tick_dnd(.05);self.assertFalse(p.mark_target)
    async def test_shield_can_turn_hit_into_miss(self):
        p=self.player('mage',3);await self.g.cast_spell(p,'shield');self.g.combat_rng=Dice(8)
        hp=p.hp;mana=p.mana;result=self.g.hit_player(self.e,p)
        self.assertTrue(result['shielded']);self.assertEqual(p.hp,hp);self.assertEqual(p.mana,mana-20)
    async def test_shield_does_not_cancel_critical(self):
        p=self.player('mage',11);await self.g.cast_spell(p,'shield');self.g.combat_rng=Dice(20);hp=p.hp
        result=self.g.hit_player(self.e,p);self.assertTrue(result['critical']);self.assertLess(p.hp,hp)
    async def test_barkskin_minimum_ac(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'barkskin');self.assertGreaterEqual(p.armor_class,17)
    async def test_stoneskin_halves_physical_damage(self):
        p=self.player('druid',9);await self.g.cast_spell(p,'stoneskin');self.g.combat_rng=Dice(20)
        hp=p.hp;self.g.damage_player(p,10,rolled=True,damage_type='slashing');self.assertEqual(p.hp,hp-5)
    async def test_no_damage_minimum_one_after_zero_save(self):
        hp=self.p.hp;self.g.damage_player(self.p,0,rolled=True);self.assertEqual(hp,self.p.hp)
    async def test_blind_or_entangle_retries_save(self):
        p=self.player('druid',3);self.g.combat_rng=Dice(1);await self.g.cast_spell(p,'entangle',self.e.id)
        self.g.combat_rng=Dice(20);self.clock.advance();self.g.tick_dnd(.05);self.assertFalse(self.g.enemy_condition(self.e,'restrained'))
    async def test_moonbeam_periodic_not_each_frame(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'moonbeam',self.e.id);self.g.tick_dnd(.05);hp=self.e.hp
        for _ in range(50):self.g.tick_dnd(.05)
        self.assertEqual(self.e.hp,hp);self.clock.advance();self.g.tick_dnd(.05);self.assertLess(self.e.hp,hp)
    async def test_spike_growth_damage_only_on_movement(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'spike_growth',self.e.id);self.g.tick_dnd(.05);self.assertEqual(self.e.hp,999)
        self.e.x+=35;self.g.tick_dnd(.05);self.assertEqual(self.e.hp,993)
    async def test_concentration_recast_free(self):
        p=self.player('druid',7);await self.g.cast_spell(p,'call_lightning',self.e.id);mana=p.mana;self.clock.advance()
        await self.g.cast_spell(p,'call_lightning',self.e.id);self.assertEqual(mana,p.mana)
    async def test_every_spell_executes(self):
        for key,s in dnd.SPELLS.items():
            with self.subTest(key=key):
                p=self.player(s['class_ids'][0],21);p.hp=p.max_hp//2;p.mana=999
                self.g.companions={};self.g.spell_fields=[];self.e.hp=999;self.e.alive=True;self.e.x=1170;self.e.y=1180
                await self.g.cast_spell(p,key,self.e.id if s['kind'] in ('attack','save','field','missiles','mark','control') else None)
                self.g.tick_dnd(.05)
                if s['kind'] in ('attack','save','missiles'):self.assertGreater(p.attack_cooldown_until,self.clock())
    async def test_shape_has_temporary_health(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'wild_shape_wolf');hp=p.hp;temp=p.temp_hp
        self.assertEqual(p.form,'wolf');self.assertEqual(rules.weapon_dice(p),(1,6,2));self.g.damage_player(p,temp+1,rolled=True)
        self.assertEqual(p.hp,hp-1);self.assertEqual(p.form,'wolf')
    async def test_bear_two_attacks(self):
        p=self.player('druid',9);await self.g.cast_spell(p,'wild_shape_bear');self.assertEqual(rules.attacks_per_round(p),2)
    async def test_no_casting_in_shape_and_free_return(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'wild_shape_wolf');mana=p.mana
        await self.g.cast_spell(p,'produce_flame',self.e.id);self.assertEqual(self.e.hp,999)
        self.clock.advance();await self.g.cast_spell(p,'wild_shape_wolf');self.assertFalse(p.form);self.assertEqual(mana,p.mana)
    async def test_pet_gate_and_real_actor(self):
        p=self.player('ranger',2);await self.g.cast_spell(p,'animal_companion');self.assertFalse(self.g.companions)
        p.level=3;await self.g.cast_spell(p,'animal_companion');self.assertEqual(len(self.g.snapshot(p)['companions']),1)
    async def test_pet_only_attacks_selected_enemy(self):
        p=self.player('ranger',3);await self.g.cast_spell(p,'animal_companion');pet=self.g.companions[p.id]
        self.g.tick_dnd(.05);self.assertEqual(self.e.hp,999)
        await self.g.select_combat_target(p,{'enemy_id':self.e.id});self.g.tick_dnd(.05);self.assertLess(self.e.hp,999)
        self.assertGreater(pet.ready,self.clock())
    async def test_pet_death_cooldown(self):
        p=self.player('ranger',3);await self.g.cast_spell(p,'animal_companion');pet=self.g.companions[p.id]
        self.g.damage_player(pet,999,rolled=True);self.g.tick_dnd(.05);self.assertFalse(self.g.companions)
        self.assertGreaterEqual(p.spell_cooldowns['animal_companion'],self.clock()+45)
    async def test_pet_removed_on_floor_change(self):
        p=self.player('ranger',3);await self.g.cast_spell(p,'animal_companion');p.floor=-1;self.g.tick_dnd(.05);self.assertFalse(self.g.companions)
    async def test_select_starts_auto_and_round_cooldown(self):
        await self.g.select_combat_target(self.p,{'enemy_id':self.e.id});await self.g.process_player_actions();hp=self.e.hp
        self.assertLess(hp,999);await self.g.process_player_actions();self.assertEqual(hp,self.e.hp)
        self.clock.advance();await self.g.process_player_actions();self.assertLess(self.e.hp,hp)
    async def test_auto_does_not_chase_or_retarget(self):
        self.e.x=1400;pos=(self.p.x,self.p.y);await self.g.select_combat_target(self.p,{'enemy_id':self.e.id});await self.g.process_player_actions()
        self.assertEqual(pos,(self.p.x,self.p.y));self.assertEqual(self.e.hp,999)
        self.e.alive=False;await self.g.process_player_actions();self.assertFalse(self.p.auto_enabled)
    async def test_clear_target_stops_auto(self):
        await self.g.select_combat_target(self.p,{'enemy_id':self.e.id});await self.g.select_combat_target(self.p,{});await self.g.process_player_actions();self.assertEqual(self.e.hp,999)
    async def test_auto_floor_isolation(self):
        self.e.floor=-1;await self.g.select_combat_target(self.p,{'enemy_id':self.e.id});self.assertFalse(self.p.auto_enabled)
    async def test_auto_pvp_safety_never_implicitly_disabled(self):
        q=self.player(pid='2',level=5);self.p.level=5;await self.g.select_combat_target(self.p,{'target_id':q.id});await self.g.process_player_actions()
        self.assertTrue(self.p.pvp_safety);self.assertFalse(self.p.auto_enabled)
    async def test_queued_spell_preempts_auto(self):
        p=self.player('mage',3);self.e.x=1200;await self.g.select_combat_target(p,{'enemy_id':self.e.id});await self.g.process_player_actions();await self.g.attack(p,enemy_id=self.e.id)
        await self.g.cast_spell(p,'magic_missile',self.e.id);self.assertEqual(p.pending_spell['spell'],'magic_missile')
        self.clock.advance();await self.g.process_player_actions();self.assertEqual(p.last_roll['action'],'Magiczny pocisk');self.assertFalse(p.pending_spell)
    async def test_auto_pause_clears_spell_queue(self):
        p=self.player('mage',3);await self.g.select_combat_target(p,{'enemy_id':self.e.id});p.attack_cooldown_until=2000
        await self.g.cast_spell(p,'magic_missile',self.e.id);await self.g.on_packet(p.ws,{'type':'auto_pause','paused':True});self.assertFalse(p.pending_spell);self.assertFalse(p.auto_enabled)
    async def test_hotbar_persisted(self):
        p=self.player('mage',5);self.account(p);await self.g.bind_spell(p,0,'fireball');saved=json.loads(self.g.db.execute('SELECT data FROM accounts').fetchone()[0]);self.assertEqual(saved['hotbar'][0],'fireball')
        loaded=self.g.load_player(p.id,p.name,p.ws,saved);self.assertEqual(loaded.hotbar[0],'fireball');self.assertFalse(loaded.auto_enabled)
    async def test_hotbar_rejects_foreign_and_bad_slot(self):
        before=self.p.hotbar[:]
        for slot,key in ((-1,'second_wind'),(24,'second_wind'),(True,'second_wind'),(0,'fireball'),(0,{})):
            await self.g.bind_spell(self.p,slot,key)
        self.assertEqual(before,self.p.hotbar)
    async def test_ranking_public_and_no_private_data(self):
        self.account(self.p);q=self.player('ranger',5,'2');self.account(q)
        await self.g.on_packet(WS(),{'type':'ranking'})
        board=self.g.ranking()['ranking'];self.assertEqual(board[0]['name'],q.name)
        self.assertFalse(any(key in json.dumps(board) for key in ('password','inventory','salt','_pid')))
    async def test_ranking_empty_accounts(self):self.assertEqual(self.g.ranking()['ranking'],[])
    async def test_migrate_paladin_gear_uid_and_hp(self):
        p=self.player('ranger',5);self.account(p);saved=p.save_data();saved.pop('rules_version');saved.pop('level_rules_version',None);saved['level']=20;saved['class_id']='paladin';saved['hp']=(115+19*13)/2
        saved['inventory'][0]['template']=saved['inventory'][0]['template'].replace('ranger','paladin');uid=saved['inventory'][0]['uid']
        migrated=self.g.load_player(p.id,p.name,p.ws,saved)
        self.assertEqual(migrated.class_id,'ranger');self.assertEqual(migrated.inventory[0]['uid'],uid);self.assertAlmostEqual(migrated.hp,migrated.max_hp/2)
    async def test_migration_keeps_dead_character_dead(self):
        saved=self.p.save_data();saved.pop('rules_version');saved['hp']=0
        loaded=self.g.load_player('1','Test',WS(),saved);self.assertFalse(loaded.alive);self.assertGreater(loaded.respawn_until,self.clock())
    async def test_removed_runes_refund_once(self):
        saved=self.p.save_data();saved.pop('rules_version');saved['runes']={'fire':2};loaded=self.g.load_player('1','Test',WS(),saved)
        self.assertEqual(loaded.gold,self.p.gold+50);again=self.g.load_player('1','Test',WS(),loaded.save_data());self.assertEqual(again.gold,loaded.gold)
    async def test_death_stops_auto_and_shape(self):
        p=self.player('druid',5);await self.g.cast_spell(p,'wild_shape_wolf');await self.g.select_combat_target(p,{'enemy_id':self.e.id});self.g.damage_player(p,999,rolled=True)
        self.assertFalse(p.auto_enabled);self.assertFalse(p.form);self.assertEqual(p.temp_hp,0)
    async def test_world_terrain_preserved(self):
        self.assertGreater(len(self.g.enemies),10000);self.assertGreater(len(self.g.metadata()['regions']),10);self.assertGreater(len(self.g.metadata()['stairs']),10)
    async def test_snapshot_private_vs_public(self):
        self.account(self.p);q=self.player(pid='2');self.assertIn('hotbar',self.g.snapshot(self.p)['players'][0]);self.assertNotIn('hotbar',q.public(self.clock()))
    async def test_compact_snapshot_restores_hotbar_on_change(self):
        self.g.compact_clients.add(self.p.id);a=self.g.wire_snapshot(self.p);b=self.g.wire_snapshot(self.p)
        self.assertIn('hotbar',a['players'][0]);self.assertNotIn('hotbar',b['players'][0]);await self.g.bind_spell(self.p,1,'second_wind');self.assertIn('hotbar',self.g.wire_snapshot(self.p)['players'][0])

class NetworkRules(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client=TestClient(TestServer(create_app(':memory:')));await self.client.start_server()
    async def asyncTearDown(self):await self.client.close()
    async def test_public_ranking_http_no_auth(self):
        response=await self.client.get('/ranking');self.assertEqual(response.status,200);self.assertEqual((await response.json())['ranking'],[])
    async def test_health_version(self):self.assertEqual((await (await self.client.get('/health')).json())['version'],'0.8.17')
    async def test_registration_and_ws_ranking(self):
        ws=await self.client.ws_connect('/ws');await ws.send_json({'type':'hello','name':'RangerTest','password':'testpassword99','class_id':'ranger','create':True})
        packet=await ws.receive_json(timeout=10);self.assertEqual(packet['type'],'welcome');self.assertIn('ranger',packet['world']['classes']);self.assertNotIn('paladin',packet['world']['classes']);await ws.close()
        public=await self.client.ws_connect('/ws');await public.send_json({'type':'ranking'});packet=await public.receive_json(timeout=5);self.assertEqual(packet['ranking'][0]['name'],'RangerTest');await public.close()
    async def test_unauthed_hotbar_is_rejected(self):
        ws=await self.client.ws_connect('/ws');await ws.send_json({'type':'hotbar','slot':0,'spell_id':'fireball'});self.assertEqual((await ws.receive_json(timeout=5))['type'],'error');await ws.close()
    async def test_web_assets_delivered(self):
        for path in ('/','/game.js','/style.css','/runtime.js'):
            response=await self.client.get(path);self.assertEqual(response.status,200,path);self.assertGreater(len(await response.read()),100)

if __name__=='__main__':unittest.main()
