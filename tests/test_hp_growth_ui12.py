"""Exact D&D checkpoint totals, integer interpolation and existing-save migration."""
import copy
import json
import unittest
from types import SimpleNamespace
from server.server import Game, Player
from server import combat_rules as rules, level_up
from test_dnd import Clock, WS


class HitPointGrowth(unittest.TestCase):
    def test_every_dnd_checkpoint_and_every_intermediate_level(self):
        for cls,die in (('knight',10),('ranger',10),('druid',8),('mage',6)):
            p=Player('1','HP',class_id=cls)
            for constitution_bonus in range(4):
                p.training_feats={('ability_score_improvement' if i==0 else f'ability_score_improvement_{i+1}'):'constitution+constitution' for i in range(constitution_bonus)}
                con=2+constitution_bonus;gain=die//2+1+con
                for n in range(1,21):
                    p.level=1 if n==1 else (n-1)*5
                    self.assertEqual(p.max_hp,die+con+(n-1)*gain,(cls,p.level,con))
                p.level=1;previous=p.max_hp
                for level in range(2,96):
                    p.level=level
                    self.assertGreater(p.max_hp,previous,(cls,level,con))
                    self.assertIsInstance(p.max_hp,int)
                    previous=p.max_hp
                for level in (96,100,1000000):
                    p.level=level;self.assertEqual(p.max_hp,previous)

    def test_initial_and_regular_intervals_carry_fractional_gains(self):
        for cls,expected in (('knight',[12,14,16,18,20]),('druid',[10,11,13,15,17]),('mage',[8,9,11,12,14])):
            p=Player('1','HP',class_id=cls)
            actual=[]
            for level in range(1,6):p.level=level;actual.append(p.max_hp)
            self.assertEqual(actual,expected)
        p=Player('1','HP',class_id='druid',level=5);previous=p.max_hp;gains=[]
        for level in range(6,11):
            p.level=level;gains.append(p.max_hp-previous);previous=p.max_hp
        self.assertEqual(gains,[1,1,2,1,2]);self.assertEqual(sum(gains),7)

    def test_constitution_is_retroactive_and_minimum_dnd_gain_is_one(self):
        p=Player('1','HP',class_id='druid',level=15)
        self.assertEqual(p.max_hp,31)
        p.training_feats={'ability_score_improvement':'constitution+wisdom'}
        self.assertEqual(p.max_hp,31)
        p.training_feats={'ability_score_improvement':'constitution+constitution'}
        self.assertEqual(p.max_hp,35)
        p.level=17;self.assertEqual(p.max_hp,38)
        p.training_feats={};self.assertEqual(p.max_hp,33)
        low=SimpleNamespace(spec={'attributes':{'constitution':1},'hit_die':6},class_id='mage',level=5,training_feats={})
        self.assertEqual(rules.max_hp(low),2)
        low.level=10;self.assertEqual(rules.max_hp(low),3)

    def test_tough_is_separate_and_shapes_do_not_replace_own_constitution(self):
        p=Player('1','HP',class_id='druid',level=17)
        base=p.max_hp;p.training_feats={'tough':''}
        self.assertEqual(p.max_hp,base+8)
        p.form='mammoth';self.assertEqual(p.max_hp,base+8)
        p.level=20;self.assertEqual(p.max_hp,48)
        p.level=95;self.assertEqual(p.max_hp,183)
        p.level=1000;self.assertEqual(p.max_hp,183)

    def test_new_and_historical_receipts_keep_their_own_hp_rules(self):
        p=Player('1','HP',class_id='mage',level=9)
        level_up.record(p,10,10);new=copy.deepcopy(p.level_up_batches[0])
        old=copy.deepcopy(new);old['context'].pop('hp_rules_version')
        def gain(batch):return next(r['gain'] for r in level_up.receipt(p,batch,10)['rows'] if r['id']=='hp')
        self.assertEqual(gain(old),'+1');self.assertEqual(gain(new),'+2')
        p.level=10;level_up.record(p,11,15)
        gains=[int(next(r['gain'] for r in e['rows'] if r['id']=='hp')) for e in level_up.pending(p)['pending_level_ups']]
        self.assertEqual(gains,[2,1,1,1,1,2])


class HitPointMigration(unittest.TestCase):
    def setUp(self):self.g=Game(':memory:',clock=Clock())
    def tearDown(self):self.g.db.close()

    def test_legacy_health_fraction_vitality_refund_and_relogin(self):
        p=Player('1','HP',WS(),class_id='druid',level=55,promoted=True,hp_rules_version=0)
        self.g.starter(p);p.mastery={'vitality':1,'focus':1};p.training_feats={'tough':''}
        for fraction in (0,.25,1):
            p.hp=p.max_hp*fraction
            saved=json.loads(json.dumps(p.save_data()));saved.pop('hp_rules_version')
            loaded=self.g.load_player(p.id,p.name,WS(),saved)
            self.assertEqual(loaded.hp_rules_version,rules.HP_RULES_VERSION)
            self.assertEqual(loaded.mastery,{'focus':1});self.assertEqual(level_up.mastery_points(loaded),1)
            self.assertAlmostEqual(loaded.hp,loaded.max_hp*fraction)
            again=self.g.load_player(p.id,p.name,WS(),json.loads(json.dumps(loaded.save_data())))
            self.assertEqual(again.hp,loaded.hp);self.assertEqual(again.mastery,loaded.mastery)
            self.assertEqual(again.hp<=0,fraction==0)

    def test_pre_dnd_save_is_not_rescaled_twice(self):
        p=Player('1','HP',WS(),class_id='druid',level=15,hp_rules_version=0)
        self.g.starter(p);p.mastery={'vitality':2}
        saved=json.loads(json.dumps(p.save_data()));saved.pop('hp_rules_version');saved['rules_version']=7
        saved['hp']=(100+14*11+2*12)*.25
        loaded=self.g.load_player(p.id,p.name,WS(),saved)
        self.assertEqual(loaded.max_hp,31);self.assertAlmostEqual(loaded.hp,31*.25)
        self.assertNotIn('vitality',loaded.mastery)


if __name__=='__main__':unittest.main()
