"""0.8.10: real supplies, private discoveries, meaningful rewards and late returns."""
import copy
import math
import unittest
from unittest.mock import patch
from aiohttp.test_utils import TestClient, TestServer
from server.server import Game,Player,Enemy,ITEMS,POTIONS,ENEMY_TYPES,make_item,create_app,INVENTORY_CAP
from server import inventory_rules as inv
from server.monster_ai import SEARCH_SECONDS,SEARCH_RADIUS
from test_dnd import Clock,WS,Dice

class Supplies(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.clock=Clock();self.g=Game(':memory:',clock=self.clock)
  self.p=Player('one','Tester',WS(),class_id='mage',level=50,x=680,y=1180)
  self.g.players[self.p.id]=self.p;self.g.starter(self.p);self.p.hp=self.p.max_hp;self.p.mana=self.p.max_mana;self.p.gold=1000
  self.g.combat_rng=Dice(d20=10)
 def tearDown(self):self.g.db.close()
 async def cmd(self,kind,**data):await self.g.inventory_command(self.p,kind,data)
 def test_starter_supplies_are_owned_stacks(self):
  self.assertEqual(len(self.p.inventory),4)
  self.assertEqual(inv.count(self.p,'health_potion'),3);self.assertEqual(inv.count(self.p,'mana_potion'),3)
 def test_migration_full_bag_preserves_and_is_idempotent(self):
  p=Player('old','Old',WS());p.inventory=[make_item('loot_trophy_rat') for _ in range(40)];p.potions={'mana_potion':110,'health_potion':2}
  inv.ensure(p,ITEMS,POTIONS,make_item);uids=[i['uid'] for i in p.inventory]
  self.assertEqual(len(p.inventory),43);self.assertEqual(inv.count(p,'mana_potion'),110)
  inv.ensure(p,ITEMS,POTIONS,make_item);self.assertEqual([i['uid'] for i in p.inventory],uids)
  self.assertTrue(inv.add(p,'health_potion',1,make_item,40));self.assertFalse(inv.add(p,'mana_potion_2',1,make_item,40))
 def test_stacks_fill_then_add_new_cell(self):
  self.assertTrue(inv.add(self.p,'health_potion',101,make_item,40))
  self.assertEqual([i['quantity'] for i in self.p.inventory if i['template']=='health_potion'],[99,5])
 def test_atomic_full_bag_add_does_not_partially_fill(self):
  stack=next(i for i in self.p.inventory if i['template']=='health_potion');stack['quantity']=98
  self.p.inventory += [make_item('loot_trophy_rat') for _ in range(40-len(self.p.inventory))]
  self.assertFalse(inv.add(self.p,'health_potion',2,make_item,40));self.assertEqual(stack['quantity'],98)
 async def test_q_and_r_accept_exact_owned_kind(self):
  inv.add(self.p,'mana_potion_2',2,make_item,40)
  await self.cmd('potion_bind',slot='q',item='mana_potion_2');self.assertEqual(self.p.potion_slots['q'],'mana_potion_2')
  self.p.mana=0;await self.cmd('potion',slot='q');self.assertEqual(self.p.mana,35)
  self.assertEqual(inv.count(self.p,'mana_potion_2'),1);self.assertEqual(inv.count(self.p,'mana_potion'),3)
 async def test_no_automatic_stronger_selection(self):
  inv.add(self.p,'mana_potion_3',2,make_item,40);self.p.mana=0
  await self.cmd('potion',slot='r');self.assertEqual(self.p.mana,18);self.assertEqual(inv.count(self.p,'mana_potion_3'),2)
 async def test_empty_binding_cannot_consume_other_potions(self):
  self.p.potion_slots['q']='';self.p.hp=1;await self.cmd('potion',slot='q');self.assertEqual(self.p.hp,1)
 async def test_unowned_or_level_locked_bind_is_rejected(self):
  await self.cmd('potion_bind',slot='q',item='mana_potion_2');self.assertEqual(self.p.potion_slots['q'],'health_potion')
  inv.add(self.p,'mana_potion_4',1,make_item,40);await self.cmd('potion_bind',slot='q',item='mana_potion_4');self.assertEqual(self.p.potion_slots['q'],'health_potion')
 async def test_forged_legacy_count_is_not_owned_inventory(self):
  self.p.inventory=[i for i in self.p.inventory if i['template']!='mana_potion'];self.p.potions['mana_potion']=999;self.p.mana=0
  await self.cmd('potion',slot='r');self.assertEqual(self.p.mana,0);self.assertEqual(self.p.potions['mana_potion'],0)
 async def test_full_resource_does_not_consume(self):
  await self.cmd('potion',slot='r');self.assertEqual(inv.count(self.p,'mana_potion'),3);self.assertEqual(self.p.potion_cooldown_until,0)
 async def test_shared_cooldown(self):
  self.p.hp=1;self.p.mana=0;await self.cmd('potion',slot='q');await self.cmd('potion',slot='r');self.assertEqual(self.p.mana,0)
  self.clock.advance(3.01);await self.cmd('potion',slot='r');self.assertEqual(self.p.mana,18)
 async def test_last_potion_removes_stack_but_keeps_binding(self):
  inv.consume(self.p,'mana_potion',2);self.p.mana=0;await self.cmd('potion',slot='r')
  self.assertEqual(inv.count(self.p,'mana_potion'),0);self.assertEqual(self.p.potion_slots['r'],'mana_potion')
 async def test_buy_charges_and_stacks(self):
  before=len(self.p.inventory);await self.cmd('buy',item='mana_potion');self.assertEqual(len(self.p.inventory),before)
  self.assertEqual(self.p.gold,1000-POTIONS['mana_potion']['price']);self.assertEqual(inv.count(self.p,'mana_potion'),4)
 async def test_buy_full_bag_does_not_charge(self):
  self.p.inventory += [make_item('loot_trophy_rat') for _ in range(40-len(self.p.inventory))]
  await self.cmd('buy',item='mana_potion_2');self.assertEqual(self.p.gold,1000)
 async def test_sell_stack_pays_per_unit(self):
  item=next(i for i in self.p.inventory if i['template']=='mana_potion');await self.cmd('sell',uid=item['uid'],quantity=3)
  self.assertEqual(self.p.gold,1000+3*ITEMS['mana_potion']['value']);self.assertEqual(inv.count(self.p,'mana_potion'),0)
 async def test_invalid_sell_quantity_never_changes_state(self):
  item=next(i for i in self.p.inventory if i['template']=='mana_potion')
  for n in [-1,0,4,True,1.5,'3']:
   await self.cmd('sell',uid=item['uid'],quantity=n);self.assertEqual(self.p.gold,1000);self.assertEqual(inv.count(self.p,'mana_potion'),3)
 async def test_trading_in_combat_is_blocked(self):
  self.p.combat_until=self.clock()+50;await self.cmd('buy',item='mana_potion');self.assertEqual(self.p.gold,1000)
  item=next(i for i in self.p.inventory if i['template']=='mana_potion');await self.cmd('sell',uid=item['uid']);self.assertEqual(inv.count(self.p,'mana_potion'),3)
 async def test_cannot_equip_potion_as_weapon(self):
  before=copy.deepcopy(self.p.equipment);item=next(i for i in self.p.inventory if i['template']=='mana_potion');await self.cmd('equip',uid=item['uid']);self.assertEqual(before,self.p.equipment)
 def test_depot_is_not_available_to_shortcut(self):
  item=next(i for i in self.p.inventory if i['template']=='mana_potion');self.p.inventory.remove(item);self.p.depot.append(item)
  inv.ensure(self.p,ITEMS,POTIONS,make_item);self.assertEqual(self.p.potions['mana_potion'],0)
 def test_save_load_preserves_stack_and_binding(self):
  self.p.potion_slots['q']='mana_potion';loaded=self.g.load_player(self.p.id,self.p.name,WS(),self.p.save_data())
  self.assertEqual(loaded.inventory,self.p.inventory);self.assertEqual(loaded.potion_slots,self.p.potion_slots)
 def test_metadata_does_not_spoil_sources(self):
  meta=self.g.metadata();self.assertTrue(all('sources' not in i for i in meta['items'].values()))
  self.assertTrue(all(not s['loot'].get('entries') for s in meta['enemy_types'].values()))
 def test_inventory_not_retroactive_discovery(self):
  self.p.inventory.append(make_item('mummy_wand'));self.assertEqual(inv.public_item(self.p,self.p.inventory[-1],ENEMY_TYPES)['sources'],[])
 def test_actual_delivered_drop_records_only_that_source(self):
  self.g.grant_loot(self.p,[('item','mummy_wand')],source_kind='mummy');self.g.grant_loot(self.p,[('item','mummy_wand')],source_kind='mummy')
  self.assertEqual(self.p.loot_discoveries['mummy_wand'],['mummy'])
  self.assertEqual(inv.sources(self.p,'mummy_wand',ENEMY_TYPES)[0]['chance'],.05)
 def test_quest_chest_buy_not_monster_discovery(self):
  self.g.grant_loot(self.p,[('item','mummy_wand')]);self.assertFalse(self.p.loot_discoveries)
 def test_failed_drop_not_discovered(self):
  self.p.inventory += [make_item('loot_trophy_rat') for _ in range(40-len(self.p.inventory))]
  self.g.grant_loot(self.p,[('item','mummy_wand')],source_kind='mummy');self.assertFalse(self.p.loot_discoveries)
 def test_discoveries_owned_and_persisted(self):
  self.g.grant_loot(self.p,[('item','mummy_wand')],source_kind='mummy');loaded=self.g.load_player(self.p.id,self.p.name,WS(),self.p.save_data())
  self.assertEqual(loaded.loot_discoveries,self.p.loot_discoveries)
  other=Player('other','Other',WS());self.assertFalse(inv.sources(other,'mummy_wand',ENEMY_TYPES))
  self.assertNotIn('known_loot',self.p.public(self.clock(),private=False))
 def test_invalid_monster_source_never_creates_discovery(self):
  inv.discover(self.p,'mummy_wand','rat',ENEMY_TYPES);inv.discover(self.p,'mummy_wand','nonexistent',ENEMY_TYPES);self.assertFalse(self.p.loot_discoveries)
 def test_all_quest_weapons_are_real_upgrades(self):
  for cls in ['knight','ranger','mage','druid']:
   with self.subTest(cls=cls):
    a,b,c=[ITEMS[f'{cls}_weapon_{i}'] for i in [1,2,3]]
    self.assertGreater(b['attack_bonus'],a['attack_bonus']);self.assertGreater(c['attack_bonus'],b['attack_bonus'])
    if cls=='mage':self.assertEqual(a['damage_dice'],b['damage_dice']);self.assertEqual(b['attack'],0)
    else:self.assertGreater(b['attack'],a['attack']);self.assertGreater(c['attack'],b['attack'])
 def test_old_reward_refreshes_with_same_uid(self):
  item=make_item('druid_weapon_2');item['attack_bonus']=0;self.p.inventory.append(item)
  loaded=self.g.load_player(self.p.id,self.p.name,WS(),self.p.save_data());renewed=next(i for i in loaded.inventory if i['uid']==item['uid'])
  self.assertEqual(renewed['attack_bonus'],1);self.assertEqual(renewed['attack'],1)

class DelayedHome(unittest.TestCase):
 def setUp(self):
  self.g=Game(':memory:');self.g.enemies.clear();self.g.enemy_cells.clear();self.g.enemy_cell_keys.clear();self.g.chasing_enemies.clear();self.g.recovering_enemies.clear()
  self.e=Enemy('world_home','wolf',10800,10000,3,10000,10000);self.e.has_engaged=True;self.e.chase_id='gone';self.e.home_trail=[(10000,10000),(10400,10000),(10800,10000)]
  self.g.enemies[self.e.id]=self.e;self.g.reindex_enemy(self.e);self.g.chasing_enemies[self.e.id]=self.e
  self.flat=patch.object(self.g,'blocked',return_value=False);self.flat.start();self.g.stop_enemy_chase(self.e)
 def tearDown(self):self.flat.stop();self.g.db.close()
 def steps(self,seconds):
  for _ in range(round(seconds/.05)):
   self.g.time+=.05;self.g.step_monsters(.05,{},set())
 def test_local_search_and_fixed_deadline(self):
  deadline=self.e.return_at;self.steps(20);self.assertEqual(self.e.return_at,deadline)
  self.assertFalse(self.e.returning);self.assertLessEqual(math.dist((self.e.x,self.e.y),(10800,10000)),SEARCH_RADIUS+1)
 def test_returns_when_no_player_nearby_without_teleport(self):
  self.steps(25);self.assertTrue(self.e.returning);self.assertGreater(self.e.x,10600)
  self.steps(25);self.assertFalse(self.e.has_engaged);self.assertLess(math.dist((self.e.x,self.e.y),(10000,10000)),29)
  self.assertNotIn(self.e.id,self.g.recovering_enemies)
 def test_return_does_not_reset_hp_or_cooldown(self):
  self.e.ready=1000;self.steps(25);self.assertEqual(self.e.ready,1000);self.assertLess(self.e.hp,self.e.max_hp)
 def test_attack_interrupts_return(self):
  self.steps(25);p=Player('hit','Hit',WS(),level=100,x=self.e.x+100,y=self.e.y);self.g.players[p.id]=p
  self.g.provoke_enemy(self.e,p);self.assertFalse(self.e.returning);self.assertEqual(self.e.return_at,0)
  self.assertNotIn(self.e.id,self.g.recovering_enemies);self.assertIn(self.e.id,self.g.chasing_enemies)
 def test_zero_hp_cannot_walk_home(self):
  pos=(self.e.x,self.e.y);self.e.hp=0;self.steps(35);self.assertEqual((self.e.x,self.e.y),pos)
 def test_deadline_restarts_after_new_chase_not_idle_tick(self):
  old=self.e.return_at;self.steps(4);self.g.provoke_enemy(self.e,Player('x','X',WS()));self.g.stop_enemy_chase(self.e)
  self.assertGreater(self.e.return_at,old);self.assertAlmostEqual(self.e.return_at,self.g.time+SEARCH_SECONDS)

class NewAssets(unittest.IsolatedAsyncioTestCase):
 async def test_windows_inventory_and_potion_assets_are_served(self):
  c=TestClient(TestServer(create_app(':memory:')));await c.start_server()
  try:
   for path in ['/windows.js','/windows.css','/inventory_ui.js','/assets/equipment/mana_potion_2.svg','/assets/equipment/health_potion_4.svg']:
    r=await c.get(path);self.assertEqual(r.status,200,path);self.assertTrue(await r.read())
  finally:await c.close()
if __name__=='__main__':unittest.main()
