"""Real server receipts for UI31 FIX4; no production database or account."""
import json
import unittest
import test_dnd as base
from test_general_feats_0818 import Rolls, wear
from server.server import Game, Player
from server import combat_rules as rules


class ReceiptRules(unittest.TestCase):
    def test_both_sets_are_preserved_for_bows_first_second_tie_and_critical(self):
        for weapon in ('ranger_weapon_1', 'bandit_longbow'):
            for first,second in ((2,6),(6,2),(4,4)):
                for crit in (False,True):
                    with self.subTest(weapon=weapon,first=first,second=second,critical=crit):
                        p=Player('1','Tester',class_id='ranger',level=15,origin_feat='savage_attacker')
                        wear(p,weapon)
                        count=2 if crit else 1
                        result=rules.roll_attack(Rolls(20 if crit else 15,*([first]*count)),10,1,rules.weapon_dice(p))
                        before=result['damage']
                        rules.savage_attacker_damage(p,result,Rolls(*([second]*count)),1000)
                        expected=1 if second>first else 0
                        self.assertEqual(result['savage_damage_rolls'],[[first]*count,[second]*count])
                        self.assertEqual(result['savage_scored_rolls'],result['savage_damage_rolls'])
                        self.assertEqual(result['savage_chosen'],expected)
                        self.assertGreaterEqual(result['damage'],before)
                        json.dumps(result)

    def test_style_scored_sets_make_lower_raw_sum_choice_understandable(self):
        p=Player('1','Tester',level=35,origin_feat='savage_attacker',fighting_style='great_weapon')
        wear(p,'training_greatsword')
        r=rules.roll_attack(Rolls(15,1,6),20,10,rules.weapon_dice(p))
        rules.savage_attacker_damage(p,r,Rolls(4,4),1000)
        self.assertEqual(r['savage_damage_rolls'],[[1,6],[4,4]])
        self.assertEqual(r['savage_scored_rolls'],[[3,6],[4,4]])
        self.assertEqual(r['savage_chosen'],0)
        self.assertEqual(r['damage_rolls'],[1,6])

    def test_miss_does_not_consume_and_a_second_hit_cannot_roll_again(self):
        p=Player('1','Tester',class_id='ranger',origin_feat='savage_attacker');wear(p,'ranger_weapon_1')
        miss=rules.roll_attack(Rolls(1),5,12,rules.weapon_dice(p));rules.savage_attacker_damage(p,miss,Rolls(),1000)
        self.assertNotIn('savage_attacker',miss)
        first=rules.roll_attack(Rolls(15,2),5,12,rules.weapon_dice(p));rules.savage_attacker_damage(p,first,Rolls(6),1000)
        self.assertIn('savage_scored_rolls',first)
        second=rules.roll_attack(Rolls(15,4),5,12,rules.weapon_dice(p));rules.savage_attacker_damage(p,second,Rolls(),1001)
        self.assertNotIn('savage_attacker',second)


class ReceiptIntegration(unittest.IsolatedAsyncioTestCase):
    player=base.GameRules.player
    enemy=base.GameRules.enemy

    def setUp(self):
        self.clock=base.Clock();self.g=Game(':memory:',clock=self.clock);self.g.combat_rng=base.Dice(15,4)
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[];self.addCleanup(self.g.db.close)

    async def test_horde_breaker_preserves_both_sets_in_private_snapshot_when_last_changes(self):
        p=self.player('ranger',10);p.origin_feat='savage_attacker';p.promoted=True;p.martial_archetype='hunter';p.martial_state={'hunter_choice':'horde_breaker'}
        a=self.enemy('first',p.x+150,p.y,'rat');b=self.enemy('second',p.x+198,p.y,'rat');a.hp=a.max_hp;b.hp=b.max_hp
        await self.g.dnd_attack(p,enemy_id=a.id)
        self.assertEqual(p.last_roll['action'],'Rozbijacz hord')
        receipt=next(r for r in p.combat_log if r.get('savage_attacker'))
        self.assertEqual(receipt['savage_damage_rolls'],[[4],[4]])
        state=p.public(self.clock(),self.g.time,private=True)
        self.assertIn('savage_damage_rolls',state['combat_log'][0])
        self.assertNotIn('combat_log',p.public(self.clock(),self.g.time,private=False))
        # Fixture uses actual server output, then is consumed by JS/browser tests.
        from pathlib import Path
        target=Path(__file__).parent/'fixtures'/'savage_horde_fix4.json';target.parent.mkdir(exist_ok=True)
        target.write_text(json.dumps({'id':state['id'],'last_roll':state['last_roll'],'combat_log':state['combat_log'],'simulation_time':self.g.time},ensure_ascii=False),encoding='utf-8')

    async def test_two_level_twenty_attacks_do_not_overwrite_the_first_receipt(self):
        p=self.player('ranger',20);p.origin_feat='savage_attacker';e=self.enemy('target',p.x+150,p.y)
        await self.g.dnd_attack(p,enemy_id=e.id)
        attacks=[r for r in p.combat_log if r.get('check')=='attack']
        self.assertEqual(len(attacks),2)
        self.assertEqual(sum(bool(r.get('savage_attacker')) for r in attacks),1)
        self.assertNotEqual(attacks[0]['id'],p.last_roll['id'])
