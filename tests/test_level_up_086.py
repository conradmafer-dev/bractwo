"""0.8.6: real per-level gains, durable independent receipts and safe allocation."""
import copy
import json
from pathlib import Path
import sys
import unittest
from aiohttp.test_utils import TestClient,TestServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.server import Player,Game,xp_next,create_app,make_item
from server import level_up as lu,combat_rules as rules
from test_dnd import Clock,WS

class Receipts(unittest.TestCase):
    def setUp(self):
        self.clock=Clock();self.g=Game(':memory:',clock=self.clock)
        self.p=Player('1','Award',WS(),class_id='mage',level=9)
        self.g.starter(self.p);self.g.players['1']=self.p
    def tearDown(self):self.g.db.close()
    def award(self,last=None):
        p=self.p;self.g.award(p,sum(xp_next(v) for v in range(p.level,last or p.level+1)),0)
        return lu.pending(p)['pending_level_ups']
    def rows(self,event):return {r['id']:r['gain'] for r in event['rows']}
    def account(self):
        p=self.p;self.g.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',(1,p.name,p.name.lower(),b's',b'h',json.dumps(p.save_data())))
        self.g.db.commit()
    def test_no_receipt_without_advancement(self):
        self.g.award(self.p,1,0);self.assertEqual(lu.pending(self.p)['level_up_pending_count'],0)
    def test_every_intermediate_level_gets_own_receipt(self):
        self.assertEqual([e['level'] for e in self.award(12)],[10,11,12])
    def test_level_ten_exact_increments(self):
        r=self.rows(self.award()[0]);self.assertEqual(r['hp'],'+1');self.assertEqual(r['mana'],'+11');self.assertEqual(r['circle'],'+1')
        self.assertIn('unlock_scorching_ray',r);self.assertIn('unlock_misty_step',r)
    def test_zero_changes_omitted(self):
        self.p.level=10;r=self.rows(self.award()[0]);self.assertEqual(r['mana'],'+13');self.assertNotIn('proficiency',r);self.assertNotIn('+0',r.values())
    def test_no_before_after_values_in_payload(self):
        text=json.dumps(self.award(12));self.assertNotIn('before',text);self.assertNotIn('after',text);self.assertNotIn('→',text)
    def test_separate_saving_throws(self):
        self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['save_intelligence'],'+2');self.assertEqual(r['save_wisdom'],'+1')
        self.assertNotIn('save_dexterity',r)
    def test_primary_score_mod_and_attack_are_separate(self):
        self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['attribute_intelligence'],'+2');self.assertEqual(r['modifier_intelligence'],'+1');self.assertEqual(r['spell_attack'],'+2')
    def test_cantrips_list_added_dice_not_total(self):
        self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['spell_damage_fire_bolt'],'+1k10');self.assertEqual(r['spell_damage_ray_of_frost'],'+1k8')
    def test_knight_additional_attack(self):
        self.p.class_id='knight';i=make_item('knight_weapon_1');self.p.inventory.append(i);self.p.equipment['weapon']=i['uid'];self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['attacks'],'+1');self.assertEqual(r['weapon_damage'],'+1')
    def test_shillelagh_shows_only_labeled_average_gain(self):
        self.p.class_id='druid';i=make_item('druid_weapon_1');self.p.inventory.append(i);self.p.equipment['weapon']=i['uid'];self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['shillelagh_average'],'+2')
    def test_later_healing_gains_shown(self):
        self.p.class_id='druid';self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['healing_cure_wounds'],'+1')
    def test_new_form_has_icon(self):
        self.p.class_id='druid';self.p.level=4;e=self.award()[0];r=next(r for r in e['rows'] if r['id']=='unlock_wild_shape_wolf');self.assertTrue(r['icon'].endswith('.svg'))
    def test_pet_improvements_match_new_summon(self):
        self.p.class_id='ranger';self.p.level=19;r=self.rows(self.award()[0]);self.assertEqual(r['pet_hp'],'+5');self.assertEqual(r['pet_ac'],'+1')
    def test_single_click_dismisses_only_its_id(self):
        events=self.award(12);self.assertTrue(lu.dismiss(self.p,events[1]['id']));self.assertEqual([e['level'] for e in lu.pending(self.p)['pending_level_ups']],[10,12])
    def test_repeated_dismiss_is_idempotent(self):
        e=self.award()[0];self.assertTrue(lu.dismiss(self.p,e['id']));self.assertFalse(lu.dismiss(self.p,e['id']))
    def test_dismiss_does_not_spend_or_change_stats(self):
        self.p.class_id='knight';self.p.level=49;self.p.promoted=True;e=self.award()[0];stats=(self.p.max_hp,self.p.max_mana,dict(self.p.mastery));lu.dismiss(self.p,e['id']);self.assertEqual(stats,(self.p.max_hp,self.p.max_mana,self.p.mastery));self.assertEqual(lu.mastery_points(self.p),1)
    def test_reject_invalid_ids(self):
        self.award();count=lu.pending(self.p)['level_up_pending_count']
        for bad in (None,[],{},1,True,'wrong','x:-1','x:'+'1'*100):self.assertFalse(lu.dismiss(self.p,bad))
        self.assertEqual(lu.pending(self.p)['level_up_pending_count'],count)
    def test_other_character_cannot_dismiss(self):
        e=self.award()[0];q=Player('2','Other');self.assertFalse(lu.dismiss(q,e['id']));self.assertEqual(lu.pending(self.p)['level_up_pending_count'],1)
    def test_pending_receipts_do_not_expire(self):
        result=copy.deepcopy(self.award());self.clock.advance(86400*100);self.assertEqual(lu.pending(self.p)['pending_level_ups'],result)
    def test_only_owner_receives_history(self):
        self.award();self.assertNotIn('pending_level_ups',self.p.public(self.clock(),private=False));self.assertIn('pending_level_ups',self.p.public(self.clock(),private=True))
    def test_persistence_after_restart(self):
        self.award(12);self.account();saved=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0]);q=self.g.load_player('1','Award',WS(),saved)
        self.assertEqual(lu.pending(q),lu.pending(self.p))
    def test_legacy_save_does_not_spam_past_levels(self):
        self.p.level=80;saved=self.p.save_data();saved.pop('level_up_batches');q=self.g.load_player('1','Award',WS(),saved);self.assertEqual(lu.pending(q)['level_up_pending_count'],0)
    def test_receipt_immutable_after_equipment_or_mastery_change(self):
        events=copy.deepcopy(self.award(12));self.p.mastery={'vitality':10,'focus':4};self.p.inventory=[];self.p.equipment={};self.p._level_up_cache=None
        self.assertEqual(lu.pending(self.p)['pending_level_ups'],events)
    def test_buffs_terrain_and_form_do_not_contaminate_growth(self):
        self.p.level=19;self.p.buffs={'shield':{'until':2000},'mage_armor':{'until':2000}};self.p.form='bear'
        r=self.rows(self.award()[0]);self.assertNotIn('ac',r);self.assertNotIn('attacks',r);self.assertEqual(r['hp'],'+1')
    def test_mastery_action_is_conditional(self):
        self.p.level=49;self.p.promoted=True;e=self.award()[0];self.assertEqual(e['actions'],[{'kind':'mastery','label':'Przydziel punkt','tab':'stats'}]);self.assertEqual(self.rows(e)['mastery'],'+1')
    def test_no_fabricated_feat_or_point_rewards(self):
        self.p.level=19;e=self.award()[0];self.assertEqual(e['actions'],[]);self.assertNotIn('feat',json.dumps(e))
    def test_thousands_of_levels_are_not_dropped_or_allocated_eagerly(self):
        self.p.level=1;count=1000000;xp=count*xp_next(1)+35*count*(count-1)//2;self.g.award(self.p,xp,0)
        result=lu.pending(self.p);self.assertEqual(result['level_up_pending_count'],count);self.assertEqual(len(result['pending_level_ups']),lu.VISIBLE_LIMIT)
        self.assertLess(len(json.dumps(self.p.level_up_batches)),3000);self.assertEqual(len(self.p.level_up_batches),1)
        oldfirst=result['pending_level_ups'][0]['level'];lu.dismiss(self.p,result['pending_level_ups'][-1]['id']);next_=lu.pending(self.p)
        self.assertEqual(next_['level_up_pending_count'],count-1);self.assertEqual(next_['pending_level_ups'][0]['level'],oldfirst-1)
    def test_compact_snapshot_restates_dismissal(self):
        self.award(12);self.g.compact_clients.add(self.p.id);a=self.g.wire_snapshot(self.p);own=next(x for x in a['players'] if x['id']==self.p.id);e=own['pending_level_ups'][0]
        b=self.g.wire_snapshot(self.p);self.assertNotIn('pending_level_ups',next(x for x in b['players'] if x['id']==self.p.id))
        lu.dismiss(self.p,e['id']);c=self.g.wire_snapshot(self.p);self.assertEqual(len(next(x for x in c['players'] if x['id']==self.p.id)['pending_level_ups']),2)

class Commands(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock=Clock();self.g=Game(':memory:',clock=self.clock);self.p=Player('1','Award',WS(),class_id='knight',level=50,promoted=True,x=1100,y=1180);self.g.players['1']=self.p
    def tearDown(self):self.g.db.close()
    async def test_allocate_from_sheet_without_master_nearby(self):
        self.assertIsNone(self.g.near_service(self.p,'master'));hp=self.p.max_hp
        await self.g.on_packet(self.p.ws,{'type':'mastery','branch':'vitality'});self.assertEqual(self.p.mastery,{'vitality':1});self.assertEqual(self.p.max_hp,hp+2)
    async def test_cannot_spend_same_point_twice(self):
        await self.g.on_packet(self.p.ws,{'type':'mastery','branch':'focus'});await self.g.on_packet(self.p.ws,{'type':'mastery','branch':'focus'});self.assertEqual(self.p.mastery,{'focus':1})
    async def test_dead_or_fighting_cannot_allocate(self):
        self.p.combat_until=2000;await self.g.on_packet(self.p.ws,{'type':'mastery','branch':'focus'});self.assertFalse(self.p.mastery)
        self.p.combat_until=0;self.p.hp=0;await self.g.on_packet(self.p.ws,{'type':'mastery','branch':'focus'});self.assertFalse(self.p.mastery)
    async def test_promotion_and_reset_still_need_master(self):
        self.p.mastery={'focus':1};self.p.gold=1000;await self.g.on_packet(self.p.ws,{'type':'mastery_reset'});self.assertEqual(self.p.mastery,{'focus':1})
    async def test_branch_and_prerequisites_are_validated(self):
        for bad in (None,[],{},'strength',''):await self.g.on_packet(self.p.ws,{'type':'mastery','branch':bad})
        self.assertFalse(self.p.mastery);self.p.promoted=False;await self.g.on_packet(self.p.ws,{'type':'mastery','branch':'focus'});self.assertFalse(self.p.mastery)
    async def test_close_command_persists_even_in_combat(self):
        self.p.level=49;self.g.award(self.p,xp_next(49),0);e=lu.pending(self.p)['pending_level_ups'][0];self.p.combat_until=2000
        self.g.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',(1,'Award','award',b's',b'h',json.dumps(self.p.save_data())));self.g.db.commit()
        await self.g.on_packet(self.p.ws,{'type':'dismiss_level_up','id':e['id']});saved=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0]);self.assertEqual(saved['level_up_batches'],[])
    async def test_new_assets_served_by_real_http(self):
        async with TestClient(TestServer(create_app(':memory:'))) as client:
            for path in ('/level_up.js','/level_up.css'):
                response=await client.get(path);self.assertEqual(response.status,200);self.assertGreater(len(await response.read()),100)
            response=await client.get('/');html=await response.text();self.assertIn('levelUpCascade',html);self.assertIn('level_up.js',html)
