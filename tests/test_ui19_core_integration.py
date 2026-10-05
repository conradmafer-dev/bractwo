"""Five focused scenarios using the real UI19 Game and SQLite persistence.

Run this file directly to also write docs/qa_0.8.18/ui19/integration_results.json.
No legacy unittest modules or mocked command handlers are imported.
"""
import json
import os
from pathlib import Path
import sys
import time
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from server.server import Game, Player, ITEMS, POTIONS, LANDMARKS, make_item
from server import world_content as content, inventory_rules, magic_items
from server.progression import merchant_at


class Clock:
    def __init__(self):self.value=10000.0
    def __call__(self):return self.value
    def advance(self,seconds):self.value+=seconds


class WS:
    closed=False
    def __init__(self):self.messages=[]
    async def send_json(self,value):self.messages.append(value)
    async def close(self):self.closed=True


class GameIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock=Clock();self.game=Game(':memory:',clock=self.clock)

    def tearDown(self):self.game.db.close()

    def player(self,class_id='knight',level=5):
        city=next(c for c in content.CITIES if c['id']=='przystan')
        p=Player('1','Integration',WS(),class_id=class_id,level=level,x=city['x'],y=city['y'],gold=10000)
        self.game.starter(p);p.current_wall_time=self.clock();p.hp=p.max_hp;p.mana=p.max_mana
        self.game.players[p.id]=p
        self.game.db.execute('INSERT INTO accounts(id,name,name_key,salt,password_hash,data) VALUES(?,?,?,?,?,?)',
            (1,p.name,p.name.lower(),b'test-salt',b'test-hash',json.dumps(p.save_data())))
        self.game.db.commit()
        return p

    def stored(self,p):
        return json.loads(self.game.db.execute('SELECT data FROM accounts WHERE id=?',(p.id,)).fetchone()[0])

    def save(self,p):
        with self.game.db:self.game.save_player(p)
        return self.stored(p)

    def reload(self,p):
        loaded=self.game.load_player(p.id,p.name,WS(),self.stored(p))
        self.game.players[p.id]=loaded
        return loaded

    def give(self,p,key):
        item=make_item(key);p.inventory.append(item);return item

    async def test_01_local_boat_payment_destination_home_and_remote_rejection(self):
        p=self.player();route=next(r for r in content.SEA_ROUTES if r['id']=='boat_przystan_brzezina')
        source=next(s for s in content.PORTS if s['id']==route['from_id'])
        destination=next(s for s in content.PORTS if s['id']==route['to_id'])
        boatman=next(n for n in content.NPCS if n['id']==source['npc_id'])
        p.x,p.y,p.floor=boatman['x'],boatman['y'],boatman.get('floor',0)
        # Isolate the ticket price from incidental first-visit exploration rewards.
        p.discoveries=[point['id'] for point in LANDMARKS]
        initial=(p.x,p.y,p.floor,p.gold,p.home_city)
        await self.game.boat_command(p,{'route_id':'boat_forged_unknown'})
        self.assertEqual((p.x,p.y,p.floor,p.gold,p.home_city),initial)
        remote=next(r for r in content.SEA_ROUTES if r['from_id'] not in (route['from_id'],route['to_id']))
        await self.game.boat_command(p,{'route_id':remote['id']})
        self.assertEqual((p.x,p.y,p.floor,p.gold,p.home_city),initial)
        self.assertIn(route['id'],boatman['routes'])
        await self.game.boat_command(p,{'route_id':route['id']})
        self.assertEqual((p.x,p.y,p.floor),(destination['x'],destination['y'],destination.get('floor',0)))
        self.assertEqual(p.gold,initial[3]-route['cost'])
        self.assertEqual(p.home_city,'brzezina')
        saved=self.stored(p)
        self.assertEqual(saved['home_city'],'brzezina');self.assertEqual(saved['gold'],p.gold)

    async def test_02_nearest_merchant_stock_is_authoritative(self):
        p=self.player();seller=next(n for n in content.NPCS if n['id']=='merchant_zloty_port')
        p.x,p.y,p.floor=seller['x'],seller['y'],seller.get('floor',0)
        self.assertEqual(merchant_at(p)['id'],seller['id'])
        allowed='magic_longsword_1';foreign='magic_quarterstaff_1'
        self.assertIn(allowed,seller['stock']);self.assertNotIn(foreign,seller['stock'])
        gold=p.gold;count=len(p.inventory)
        await self.game.inventory_command(p,'buy',{'item':foreign})
        self.assertEqual((p.gold,len(p.inventory)),(gold,count))
        await self.game.inventory_command(p,'buy',{'item':allowed})
        self.assertEqual(p.gold,gold-ITEMS[allowed]['price'])
        self.assertEqual(len(p.inventory),count+1)
        self.assertEqual(p.inventory[-1]['template'],allowed)
        saved=self.stored(p)
        self.assertEqual(saved['inventory'][-1]['template'],allowed)
        self.assertEqual(saved['gold'],p.gold)

    async def test_03_potion_and_spell_share_bonus_action_across_save_load(self):
        p=self.player('druid');p.hp=1
        count=inventory_rules.count(p,'health_potion');self.assertGreater(count,1)
        main=p.attack_cooldown_until
        await self.game.inventory_command(p,'potion',{'item':'health_potion'})
        self.assertEqual(inventory_rules.count(p,'health_potion'),count-1)
        self.assertGreater(p.hp,1);self.assertEqual(p.attack_cooldown_until,main)
        deadline=self.clock()+3
        self.assertEqual(p.bonus_cooldown_until,deadline)
        await self.game.cast_spell(p,'shillelagh',queue=False)
        self.assertNotIn('shillelagh',p.buffs)
        # A main-action spell remains available in the same turn.
        mana=p.mana
        await self.game.cast_spell(p,'cure_wounds',target_id=p.id,queue=False)
        self.assertGreater(p.attack_cooldown_until,self.clock());self.assertLess(p.mana,mana)
        self.save(p);p=self.reload(p)
        self.assertEqual(p.bonus_cooldown_until,deadline)
        p.hp=1;remaining=inventory_rules.count(p,'health_potion')
        await self.game.inventory_command(p,'potion',{'item':'health_potion'})
        await self.game.cast_spell(p,'shillelagh',queue=False)
        self.assertEqual(inventory_rules.count(p,'health_potion'),remaining)
        self.assertNotIn('shillelagh',p.buffs)
        self.clock.advance(3.1);p.current_wall_time=self.clock()
        await self.game.cast_spell(p,'shillelagh',queue=False)
        self.assertIn('shillelagh',p.buffs)
        await self.game.inventory_command(p,'potion',{'item':'health_potion'})
        self.assertEqual(inventory_rules.count(p,'health_potion'),remaining)

    async def test_04_attunement_full_rest_interrupt_and_persistence(self):
        p=self.player();item=self.give(p,'ring_protection');p.equipment['ring']=item['uid']
        await magic_items.command(self.game,p,{'action':'attune','uid':item['uid']})
        self.assertEqual(p.rest_state['total'],10)
        p.x+=1;self.game.tick_rest(p)
        self.assertFalse(p.rest_state)
        self.clock.advance(11);p.current_wall_time=self.clock();self.game.tick_rest(p)
        self.assertFalse(magic_items.effect(p,'protection'))
        await magic_items.command(self.game,p,{'action':'attune','uid':item['uid']})
        self.assertTrue(p.rest_state)
        self.clock.advance(9.9);p.current_wall_time=self.clock();self.game.tick_rest(p)
        self.assertFalse(magic_items.effect(p,'protection'));self.assertTrue(p.rest_state)
        self.clock.advance(.11);p.current_wall_time=self.clock();self.game.tick_rest(p)
        self.assertFalse(p.rest_state);self.assertEqual(magic_items.effect(p,'protection'),1)
        self.assertEqual(self.stored(p)['magic_attunements'][0]['uid'],item['uid'])
        p=self.reload(p)
        self.assertEqual(magic_items.effect(p,'protection'),1)
        self.assertEqual(p.magic_attunements[0]['uid'],item['uid'])

    def test_05_ocean_migration_only_moves_legacy_revision(self):
        p=self.player();ring=self.give(p,'ring_swimming');p.equipment['ring']=ring['uid']
        candidates=((x,y) for x in range(5000,content.WIDTH-5000,5000) for y in range(5000,content.HEIGHT-5000,5000))
        ocean=next(((x,y) for x,y in candidates if content.WATER_MAP.is_ocean(x,y) and not self.game.blocked_for(p,x,y)),None)
        self.assertIsNotNone(ocean,'The current world must expose a valid, unobstructed swimming position.')
        p.x,p.y=ocean;p.floor=0;p.home_city='brzezina';p.world_revision=18
        saved=self.save(p)
        legacy=self.game.load_player(p.id,p.name,WS(),saved)
        home=next(c for c in content.CITIES if c['id']=='brzezina')
        self.assertEqual((legacy.x,legacy.y,legacy.floor),(home['x'],home['y'],0))
        self.assertEqual(legacy.world_revision,19)
        current=json.loads(json.dumps(saved));current['world_revision']=19
        swimmer=self.game.load_player(p.id,p.name,WS(),current)
        self.assertEqual((swimmer.x,swimmer.y,swimmer.floor),(*ocean,0))
        self.assertEqual(swimmer.home_city,'brzezina')
        self.assertEqual(magic_items.effect(swimmer,'swim'),40)
        deferred=json.loads(json.dumps(saved));deferred['combat_until']=self.clock()+8
        waiting=self.game.load_player(p.id,p.name,WS(),deferred)
        self.assertEqual(waiting.world_revision,18)
        self.assertEqual((waiting.x,waiting.y),ocean)
        self.clock.advance(9)
        rescued=self.game.load_player(p.id,p.name,WS(),waiting.save_data())
        self.assertEqual((rescued.x,rescued.y),(home['x'],home['y']))
        self.assertEqual(rescued.world_revision,19)


class RecordedResult(unittest.TextTestResult):
    def __init__(self,*args,**kwargs):super().__init__(*args,**kwargs);self.cases=[]
    def addSuccess(self,test):super().addSuccess(test);self.cases.append({'test':test.id(),'status':'passed'})
    def addFailure(self,test,err):super().addFailure(test,err);self.cases.append({'test':test.id(),'status':'failed','detail':self._exc_info_to_string(err,test)})
    def addError(self,test,err):super().addError(test,err);self.cases.append({'test':test.id(),'status':'error','detail':self._exc_info_to_string(err,test)})


if __name__=='__main__':
    started=time.perf_counter()
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(GameIntegration)
    result=unittest.TextTestRunner(verbosity=2,resultclass=RecordedResult).run(suite)
    report={'suite':'tests/test_ui19_core_integration.py','status':'passed' if result.wasSuccessful() else 'failed',
        'tests_run':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
        'duration_seconds':round(time.perf_counter()-started,3),'game':'real UI19 Game with in-memory SQLite',
        'cases':result.cases,'scope':'Only five requested core integration scenarios; no legacy suite discovery.'}
    path=ROOT/'docs/qa_0.8.18/ui19/integration_results.json';path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('w',encoding='utf-8') as handle:
        json.dump(report,handle,ensure_ascii=False,indent=2);handle.write('\n');handle.flush();os.fsync(handle.fileno())
    raise SystemExit(0 if result.wasSuccessful() else 1)
