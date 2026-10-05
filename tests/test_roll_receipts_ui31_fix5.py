"""Read-only dice telemetry: actual combat, checks and rest receipts (local DB)."""
import copy
import json
from pathlib import Path
import unittest
import test_dnd as base
from test_general_feats_0818 import wear
from server.server import Game, Player
from server import combat_rules as rules, feat_rules, rest_rules


class TraceDice:
    def __init__(self, *values):
        self.values=iter(values);self.calls=[]
    def randint(self, lo, hi):
        value=next(self.values)
        assert lo <= value <= hi, (lo,hi,value)
        self.calls.append((lo,hi,value))
        return value


class TelemetryRules(unittest.TestCase):
    def test_roll_type_and_critical_count_preserve_exact_rng_calls(self):
        for critical,values in ((False,[2,6]),(True,[1,3,4,6])):
            rng=TraceDice(*values)
            r=rules.roll_damage(rng,(2,6,3),critical)
            self.assertEqual(r['damage_sides'],6)
            self.assertEqual(r['damage_rolls'],values)
            self.assertEqual(r['damage'],sum(values)+3)
            self.assertEqual(len(rng.calls),len(values))
    def test_maximized_damage_is_explicit_and_does_not_call_rng(self):
        rng=TraceDice();r=rules.roll_damage(rng,(3,8,2),maximize=True)
        self.assertEqual(r['damage_rolls'],[8,8,8]);self.assertEqual(r['damage'],26)
        self.assertTrue(r['damage_maximized']);self.assertEqual(rng.calls,[])

    def test_extra_rolls_are_copied_without_mutating_or_rerolling(self):
        rng=TraceDice(2,5);draw=rules.roll_damage(rng,(2,8,1));receipt={}
        rules.record_damage_roll(receipt,draw,'Zimno')
        draw['damage_rolls'].append(7)
        self.assertEqual(receipt['extra_damage_rolls'],[dict(name='Zimno',sides=8,rolls=[2,5],modifier=1)])
        self.assertEqual(len(rng.calls),2)
    def test_healer_receipt_has_both_faces_without_extra_rng_calls(self):
        for feat,values,expected in (('healer',[1,7],7),('healer',[4],4),('',[1],1)):
            p=Player('1','Test',class_id='ranger',origin_feat=feat)
            rng=TraceDice(*values);record={}
            self.assertEqual(feat_rules.rest_die(p,rng,record),expected)
            self.assertEqual(record['first'],values[0])
            self.assertEqual(record['reroll'],values[1] if len(values)>1 else None)
            self.assertEqual(record['sides'],10)
            self.assertEqual(len(rng.calls),len(values))
    def test_optional_receipts_do_not_change_old_rest_die_callers(self):
        p=Player('1','Test',origin_feat='healer')
        self.assertEqual(feat_rules.rest_die(p,TraceDice(1,5)),5)


class TelemetryIntegration(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock)
        self.g.combat_rng=base.Dice(15,4)
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[];self.addCleanup(self.g.db.close)
    def save_fixture(self,name,p):
        path=Path(__file__).parent/'fixtures'/'rolls_fix5';path.mkdir(exist_ok=True,parents=True)
        state=p.public(self.clock(),self.g.time,private=True)
        (path/(name+'.json')).write_text(json.dumps(dict(id=state['id'],last_roll=state['last_roll'],combat_log=state['combat_log'],simulation_time=self.g.time),ensure_ascii=False,indent=2))
    async def test_user_bow_example_exposes_two_d8_results_and_only_one_modifier(self):
        p=self.player('ranger',3);p.origin_feat='savage_attacker';wear(p,'bandit_longbow')
        target=self.enemy('target',p.x+150,p.y,'ogre');self.g.combat_rng=TraceDice(15,2,6)
        await self.g.dnd_attack(p,enemy_id=target.id)
        r=p.last_roll
        self.assertEqual(r['savage_damage_rolls'],[[2],[6]])
        self.assertEqual(r['damage_sides'],8)
        self.assertEqual(r['savage_chosen'],1)
        self.assertEqual(r['damage_rolls'],[6])
        self.assertEqual(r['damage'],6+r['damage_modifier'])
        self.assertEqual(len(self.g.combat_rng.calls),3)
        self.save_fixture('savage',p)
    async def test_mark_records_its_own_die_without_replacing_the_weapon(self):
        p=self.player('ranger',3);p.origin_feat='savage_attacker';wear(p,'bandit_longbow')
        target=self.enemy('target',p.x+150,p.y,'ogre')
        await self.g.cast_spell(p,'hunters_mark',target.id)
        self.g.combat_rng=TraceDice(15,2,6,4)
        await self.g.dnd_attack(p,enemy_id=target.id)
        r=p.last_roll
        self.assertEqual(r['damage_rolls'],[6])
        self.assertEqual(r['extra_damage_rolls'],[dict(name='Znak łowcy',sides=6,rolls=[4],modifier=0)])
        self.assertEqual(r['damage'],6+r['damage_modifier']+4)
        self.assertEqual(len(self.g.combat_rng.calls),4)
        self.save_fixture('mark',p)
    async def test_attack_save_automatic_spells_include_actual_dice(self):
        for i,(spell,expected) in enumerate((('fire_bolt',10),('fireball',6),('magic_missile',4))):
            p=self.player('mage',5,str(i+1));target=self.enemy('target'+str(i),p.x+150,p.y,'ogre')
            await self.g.cast_spell(p,spell,target.id)
            r=p.last_roll
            self.assertEqual(r['damage_sides'],expected,(spell,r))
            self.assertTrue(r['damage_rolls'],spell)
            self.assertTrue(all(n<=expected for n in r['damage_rolls']))
            self.save_fixture(spell,p)
    async def test_healing_and_potion_show_actual_roll_and_capped_gain(self):
        p=self.player('druid',1);p.hp=p.max_hp-1
        await self.g.cast_spell(p,'cure_wounds')
        r=p.last_roll
        self.assertEqual(r['check'],'healing');self.assertEqual(r['damage_sides'],8)
        self.assertEqual(r['healing'],1);self.assertTrue(r['damage_rolls'])
        self.save_fixture('healing',p)
        p.hp=1;await self.g.on_packet(p.ws,dict(type='potion',slot='q'))
        r=p.last_roll
        self.assertEqual(r['check'],'healing');self.assertEqual(r['damage_sides'],4)
        self.assertEqual(len(r['damage_rolls']),2)
        self.save_fixture('potion',p)
    async def test_guidance_keeps_the_actual_bonus_die_and_d20(self):
        p=self.player('druid',1)
        p.buffs['guidance']=dict(until=self.clock()+100,skill='athletics')
        self.g.combat_rng=TraceDice(15,4)
        r=self.g.environment_ability_check(p,'strength',10,'athletics')
        self.assertEqual(r['rolls'],[15]);self.assertEqual(r['check_extra_rolls'],[dict(name='Wskazówki',sides=4,rolls=[4],sign=1)])
        self.assertEqual(r['total'],15+r['bonus'])
        self.assertEqual(len(self.g.combat_rng.calls),2)
        self.save_fixture('guidance',p)
    async def test_short_rest_reports_healer_reroll_and_long_rest_invents_no_dice(self):
        p=self.player('ranger',3);p.origin_feat='healer';p.hp=p.max_hp-5
        self.g.combat_rng=TraceDice(1,6)
        await self.g.start_rest(p,'short');self.assertTrue(p.rest_state)
        self.clock.advance(10);self.g.time+=10;self.g.tick_rest(p)
        self.assertEqual(p.hp,p.max_hp)
        r=p.last_roll;self.assertEqual(r['check'],'healing');self.assertEqual(r['action'],'Krótki odpoczynek')
        self.assertEqual(r['healing'],5)
        self.assertEqual(r['rest_rolls'],[dict(first=1,reroll=6,value=6,sides=10,modifier=2,potential=8)])
        self.assertEqual(len(self.g.combat_rng.calls),2)
        self.save_fixture('rest',p)
        before=copy.deepcopy(p.combat_log)
        p.hp=1;self.clock.advance(3)
        await self.g.start_rest(p,'long');self.clock.advance(30);self.g.time+=30;self.g.tick_rest(p)
        self.assertEqual(p.hp,p.max_hp);self.assertEqual(p.combat_log,before)
    async def test_roll_metadata_is_private_and_serializable(self):
        p=self.player('ranger',3);p.origin_feat='savage_attacker'
        target=self.enemy('target',p.x+150,p.y)
        await self.g.dnd_attack(p,enemy_id=target.id)
        state=p.public(self.clock(),self.g.time,private=True)
        self.assertIn('damage_sides',state['last_roll'])
        self.assertNotIn('last_roll',p.public(self.clock(),self.g.time,private=False))
        json.dumps(state)


if __name__=='__main__':unittest.main()
