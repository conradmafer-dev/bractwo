"""UI33 regression tests. Run from the repository root:
python -m unittest discover -s tests -p 'test_starter_adventures_ui33.py' -v
"""
import asyncio
from collections import deque
from copy import deepcopy
import json
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server.server import Game, Player, make_item, content, ENEMY_TYPES, ITEMS, POTIONS, OBSTACLES
from server import starter_adventures as sa, combat_rules as rules, equipment_rules as gear, magic_items as magic

class Clock:
    def __init__(self):self.value=1000.0
    def __call__(self):return self.value
    def advance(self,n):self.value+=n
class WS:
    closed=False
    def __init__(self):self.messages=[]
    async def send_json(self,data):self.messages.append(data)
class Dice:
    def randint(self,a,b):return 15 if b==20 else min(4,b)

class StarterAdventures(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.clock=Clock();self.g=Game(':memory:',clock=self.clock);self.g.combat_rng=Dice()
        self.p=self.player()
    def tearDown(self):self.g.db.close()
    def player(self,cls='ranger',level=3,pid='1'):
        p=Player(pid,'Tester'+pid,WS(),class_id=cls,level=level,x=1100,y=1180)
        self.g.starter(p);p.hp=p.max_hp;p.mana=p.max_mana;p.current_wall_time=self.clock()
        self.g.players[p.id]=p
        self.g.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',(int(pid),p.name,p.name.lower(),b'salt',b'hash',json.dumps(p.save_data())))
        self.g.db.commit();return p
    def enemy(self,key):return next(e for e in self.g.enemies.values() if e.kind==key)
    def site(self,key):return next(s for s in content.POIS if s['id']==key)
    def locate(self,p,site):p.x,p.y,p.floor=site['x'],site['y'],site['floor']
    def give(self,p,key):
        i=make_item(key);p.inventory.append(i);p.equipment[i['slot']]=i['uid'];return i
    async def unlock(self,p,key):
        site=self.site(key);e=self.enemy(site['boss_kind']);p.x,p.y,p.floor=e.x+35,e.y,e.floor
        e.contributors[p.id]=self.g.time
        await self.g.defeat(e)
        self.locate(p,site);p.combat_until=0;p.pvp_combat_until=0
        return site

    def test_new_spawn_and_stair_clearance(self):
        for e in self.g.enemies.values():
            if ENEMY_TYPES[e.kind].get('starter_adventure'):
                self.assertFalse(self.g.blocked(e.x,e.y,floor=e.floor),e.kind)
        for s in content.STAIRS:
            if s.get('starter_adventure'):
                self.assertEqual(s['min_level'],1)
                self.assertFalse(self.g.blocked(s['x'],s['y'],floor=s['floor']),s['id'])
                self.assertFalse(self.g.blocked(s['to_x'],s['to_y'],floor=s['to_floor']),s['id'])

    def test_all_rooms_have_a_walkable_route_to_their_objectives(self):
        # Continuous 18px-radius collision checks at 10px intervals, not a
        # point-agent shortcut through blocked diagonal corners.
        for floor,start,targets in [(-1,(2570,445),[(2670,570),(2945,550),(3150,525),(3100,930),(3110,1110)]),
                (1,(740,1810),[(870,2150),(770,2030)]),
                (2,(590,1830),[(870,2150),(780,1990)]),
                (3,(590,2150),[(755,1880),(870,1820)])]:
            points=deque([start]);seen={start};found=set()
            while points and len(found)<len(targets):
                a=points.popleft()
                for i,t in enumerate(targets):
                    if math.dist(a,t)<24:found.add(i)
                for dx,dy in [(20,0),(-20,0),(0,20),(0,-20)]:
                    b=(a[0]+dx,a[1]+dy)
                    if b in seen or self.g.blocked(*b,floor=floor) or self.g.blocked(a[0]+dx/2,a[1]+dy/2,floor=floor):continue
                    seen.add(b);points.append(b)
            self.assertEqual(len(found),len(targets),(floor,found))

    def test_original_surface_rats_and_mine_are_preserved(self):
        self.assertEqual([s for s in content.STARTER_SPAWNS if s[0]=='rat'],[('rat',810,1460),('rat',700,1580),('rat',910,1660)])
        mine=next(s for s in content.STAIRS if s['id']=='down_0')
        self.assertEqual((mine['x'],mine['y'],mine['to_floor']),(1000,2010,-1))
        self.assertFalse(self.g.blocked(mine['x'],mine['y']))

    async def test_round_trip_through_all_stairs_at_level_one(self):
        self.p.level=1
        for s in content.STAIRS:
            if not s.get('starter_adventure'):continue
            self.p.x,self.p.y,self.p.floor=s['x'],s['y'],s['floor']
            self.clock.advance(2)
            await self.g.expansion_command(self.p,'descend',{})
            self.assertEqual((self.p.x,self.p.y,self.p.floor),(s['to_x'],s['to_y'],s['to_floor']),s['id'])

    async def test_chest_needs_real_boss_credit(self):
        site=self.site(sa.TOWER_CHEST);self.locate(self.p,site)
        before=len(self.p.inventory)
        await self.g.interact(self.p)
        self.assertEqual(len(self.p.inventory),before);self.assertNotIn(site['id'],self.p.chests)

    async def test_all_four_tower_rewards_are_guaranteed_at_level_one(self):
        site=await self.unlock(self.p,sa.TOWER_CHEST);self.p.level=1
        before=self.p.gold
        await self.g.interact(self.p)
        self.assertEqual(self.p.gold,before+60)
        for key in sa.TOWER_REWARDS:
            self.assertEqual(sum(i['template']==key for i in self.p.inventory),1)
        self.assertIn(site['id'],self.p.chests)
        for key in sa.TOWER_REWARDS:self.assertEqual(ITEMS[key]['min_level'],1)

    async def test_spamming_open_cannot_duplicate_the_reward(self):
        await self.unlock(self.p,sa.TOWER_CHEST)
        await asyncio.gather(*(self.g.interact(self.p) for _ in range(12)))
        for key in sa.TOWER_REWARDS:self.assertEqual(sum(i['template']==key for i in self.p.inventory),1)
        self.assertEqual(self.p.chests.count(sa.TOWER_CHEST),1)

    async def test_full_bag_keeps_entire_treasure_unclaimed(self):
        await self.unlock(self.p,sa.TOWER_CHEST)
        while len(self.p.inventory)<38:self.p.inventory.append(make_item('cloth'))
        before=deepcopy(self.p.inventory),self.p.gold
        await self.g.interact(self.p)
        self.assertEqual((self.p.inventory,self.p.gold),before)
        self.assertNotIn(sa.TOWER_CHEST,self.p.chests)
        del self.p.inventory[-2:]
        await self.g.interact(self.p)
        self.assertIn(sa.TOWER_CHEST,self.p.chests);self.assertEqual(len(self.p.inventory),40)

    async def test_crypt_potions_stack_without_needing_three_cells(self):
        await self.unlock(self.p,sa.CRYPT_CHEST)
        stack=next(i for i in self.p.inventory if i['template']=='health_potion');stack['quantity']=10
        while len(self.p.inventory)<40:self.p.inventory.append(make_item('cloth'))
        gold=self.p.gold
        await self.g.interact(self.p)
        self.assertEqual(stack['quantity'],13);self.assertEqual(self.p.gold,gold+120)
        self.assertIn(sa.CRYPT_CHEST,self.p.chests)

    async def test_potion_stack_overflow_requires_space_and_is_atomic(self):
        await self.unlock(self.p,sa.CRYPT_CHEST)
        stack=next(i for i in self.p.inventory if i['template']=='health_potion');stack['quantity']=98
        while len(self.p.inventory)<40:self.p.inventory.append(make_item('cloth'))
        await self.g.interact(self.p)
        self.assertEqual(stack['quantity'],98);self.assertNotIn(sa.CRYPT_CHEST,self.p.chests)

    async def test_chest_state_and_boss_credit_persist_across_reload(self):
        await self.unlock(self.p,sa.TOWER_CHEST);await self.g.interact(self.p)
        saved=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0])
        q=self.g.load_player('1',self.p.name,WS(),saved)
        self.assertIn(sa.TOWER_CHEST,q.chests);self.assertIn(sa.TOWER_BOSS,q.starter_bosses)
        before=q.gold;await self.g.interact(q);self.assertEqual(q.gold,before)

    async def test_rewards_are_personal_not_global(self):
        q=self.player(pid='2')
        await self.unlock(self.p,sa.TOWER_CHEST);await self.g.interact(self.p)
        e=self.enemy(sa.TOWER_BOSS);e.alive=True;e.hp=e.max_hp
        await self.unlock(q,sa.TOWER_CHEST);await self.g.interact(q)
        self.assertIn(sa.TOWER_CHEST,q.chests)
        self.assertEqual([i['template'] for i in q.inventory if i['template'] in sa.TOWER_REWARDS],list(sa.TOWER_REWARDS))

    async def test_respawned_guardian_blocks_a_previously_unlocked_chest(self):
        await self.unlock(self.p,sa.TOWER_CHEST)
        e=self.enemy(sa.TOWER_BOSS);e.alive=True;e.hp=e.max_hp
        await self.g.interact(self.p);self.assertNotIn(sa.TOWER_CHEST,self.p.chests)

    async def test_cannot_open_from_another_floor_or_far_away(self):
        site=await self.unlock(self.p,sa.TOWER_CHEST)
        self.p.floor=2;await self.g.open_starter_treasure(self.p,site)
        self.assertNotIn(sa.TOWER_CHEST,self.p.chests)
        self.p.floor=3;self.p.x-=200;await self.g.open_starter_treasure(self.p,site)
        self.assertNotIn(sa.TOWER_CHEST,self.p.chests)

    async def test_pvp_block_is_not_bypassed_by_the_three_second_pve_pause(self):
        await self.unlock(self.p,sa.TOWER_CHEST);self.p.pvp_combat_until=self.clock()+20
        await self.g.interact(self.p);self.assertNotIn(sa.TOWER_CHEST,self.p.chests)
        self.p.pvp_combat_until=0;self.p.combat_until=self.clock()+20
        await self.g.interact(self.p);self.assertNotIn(sa.TOWER_CHEST,self.p.chests)
        self.clock.advance(3.1);await self.g.interact(self.p)
        self.assertIn(sa.TOWER_CHEST,self.p.chests)

    def test_old_save_inside_new_tower_moves_to_its_door_without_reset(self):
        old=self.p.save_data();old.update(x=700,y=1880,floor=0,world_revision=30,gold=321)
        q=self.g.load_player('1',self.p.name,WS(),old)
        self.assertEqual((q.x,q.y,q.floor),(740,1750,0))
        self.assertEqual(q.level,self.p.level);self.assertEqual(q.gold,321)
        self.assertEqual(q.equipment,self.p.equipment)

    def test_ring_dc_bonus_does_not_change_spell_attack_or_damage(self):
        p=self.player('mage',pid='2');before=rules.spell_dc(p),rules.spell_bonus(p),rules.weapon_dice(p)
        self.give(p,'ring_focused_will')
        self.assertEqual(rules.spell_dc(p),before[0]+1)
        self.assertEqual((rules.spell_bonus(p),rules.weapon_dice(p)),before[1:])
        p.equipment['ring']='';self.assertEqual(rules.spell_dc(p),before[0])

    def test_signet_only_buffs_constitution_saves_and_not_the_ability(self):
        p=self.p;before={a:rules.save_bonus(p,a) for a in p.spec['attributes']};attrs=rules.attributes(p)
        self.give(p,'ring_headless_signet')
        for a,b in before.items():self.assertEqual(rules.save_bonus(p,a),b+(a=='constitution'),a)
        self.assertEqual(rules.attributes(p),attrs)
        p.equipment['ring']='';self.assertEqual(rules.save_bonus(p,'constitution'),before['constitution'])

    def test_original_magic_catalog_migration_does_not_replace_new_rings(self):
        for key in ['ring_focused_will','ring_headless_signet']:
            i=self.give(self.p,key);magic.migrate(self.p,ITEMS)
            self.assertEqual(i['template'],key);self.assertEqual(i['magic_id'],key)

    def test_rapier_uses_dexterity_and_only_grants_item_specific_training(self):
        p=self.player('mage',pid='2');feats=deepcopy(p.training_feats);attrs=rules.attributes(p)
        self.assertFalse(gear.has(p,'martial_weapons'))
        i=self.give(p,'echo_rapier')
        self.assertTrue(gear.proficient(p));self.assertEqual(rules.attack_ability(p),'dexterity')
        dex=rules.ability_modifier(p,'dexterity')
        self.assertEqual(rules.attack_bonus(p),rules.proficiency(p)+dex)
        self.assertEqual(rules.weapon_dice(p),(1,8,dex))
        self.assertFalse(gear.has(p,'martial_weapons'));self.assertEqual(p.training_feats,feats)
        self.assertEqual(rules.attributes(p),attrs)
        self.assertEqual(gear.check_equip(p,ITEMS['echo_rapier']),'')
        self.give(p,'magic_longsword_1');self.assertFalse(gear.proficient(p))
        p.equipment['weapon']=i['uid'];self.assertTrue(gear.proficient(p))

    def test_magic_medium_armor_and_shield_do_not_double_count_plus_one(self):
        p=self.p;p.equipment={}
        self.give(p,'old_tower_breastplate_1');self.assertEqual(p.armor_class,17)
        self.give(p,'echo_rapier');self.give(p,'old_tower_shield_1');self.assertEqual(p.armor_class,20)
        mage=self.player('mage',pid='2');self.give(mage,'old_tower_breastplate_1')
        self.assertTrue(gear.armor_penalty(mage))
        ac=mage.armor_class;self.give(mage,'old_tower_shield_1');self.assertEqual(mage.armor_class,ac)

    def test_special_line_is_fixed_and_can_be_sidestepped(self):
        e=self.enemy(sa.TOWER_BOSS);p=self.p;p.x,p.y,p.floor=755,2130,3
        self.g.queue_enemy_attack(e,p,special=True);h=self.g.hazards[-1]
        self.assertTrue(sa.in_telegraph(h,p));p.x+=100;self.assertFalse(sa.in_telegraph(h,p))
        hp=p.hp;self.g.time=2;self.clock.advance(2);self.g.resolve_hazards()
        self.assertEqual(p.hp,hp);self.assertFalse(any(h.get('starter') for h in self.g.hazards))

    def test_special_arrow_hits_when_not_dodged(self):
        e=self.enemy(sa.TOWER_BOSS);p=self.p;p.x,p.y,p.floor=755,2130,3
        hp=p.hp;self.g.queue_enemy_attack(e,p,special=True)
        self.g.time=2;self.clock.advance(2);self.g.resolve_hazards()
        self.assertLess(p.hp,hp)

    def test_tower_pillar_really_blocks_the_special_arrow(self):
        e=self.enemy(sa.TOWER_BOSS);e.x,e.y=675,1870;p=self.p;p.x,p.y,p.floor=675,2140,3
        self.assertFalse(self.g.line_clear(e,p));hp=p.hp
        self.g.queue_enemy_attack(e,p,special=True)
        self.g.time=2;self.clock.advance(2);self.g.resolve_hazards();self.assertEqual(p.hp,hp)

    def test_sweep_is_local_and_cancelled_if_boss_dies(self):
        e=self.enemy(sa.CRYPT_BOSS);p=self.p;p.x,p.y,p.floor=e.x+50,e.y,-1
        hp=p.hp;self.g.queue_enemy_attack(e,p,special=True)
        h=self.g.hazards[-1];self.assertTrue(sa.in_telegraph(h,p))
        p.x+=140;self.assertFalse(sa.in_telegraph(h,p))
        p.x-=140;e.hp=0
        self.g.time=2;self.clock.advance(2);self.g.resolve_hazards()
        self.assertEqual(p.hp,hp);self.assertFalse(any(h.get('starter') for h in self.g.hazards))

    def test_public_personal_chest_state_and_custom_assets_exist(self):
        data=self.p.public(self.clock(),private=True)
        self.assertEqual(data['starter_adventures'],{'defeated':[],'claimed':[]})
        root=Path(__file__).resolve().parents[1]
        for key in (*sa.TOWER_REWARDS,'ring_headless_signet'):
            self.assertTrue((root/'web'/ITEMS[key]['icon']).is_file())
        meta=self.g.metadata();self.assertEqual(meta['world_revision'],33)
        self.assertEqual(meta['starter_adventures']['recommended_level'],3)


class PersistenceAndHTTP(StarterAdventures):
    # Only additional tests in this class; inherited scenarios are omitted from
    # collection below to keep the count and runtime readable.
    async def test_failed_save_rolls_back_every_part_of_the_treasure(self):
        from unittest.mock import patch
        await self.unlock(self.p,sa.TOWER_CHEST)
        old=deepcopy(self.p.inventory),self.p.gold,list(self.p.chests)
        old_db=self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0]
        with patch.object(self.g,'save_player',side_effect=RuntimeError('test write failure')):
            with self.assertRaises(RuntimeError):await self.g.interact(self.p)
        self.assertEqual((self.p.inventory,self.p.gold,self.p.chests),old)
        self.assertEqual(self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0],old_db)
        await self.g.interact(self.p)
        self.assertIn(sa.TOWER_CHEST,self.p.chests)

    async def test_real_database_reopen_keeps_receipt_and_equipment(self):
        import sqlite3
        from tempfile import TemporaryDirectory
        await self.unlock(self.p,sa.TOWER_CHEST);await self.g.interact(self.p)
        with TemporaryDirectory() as folder:
            path=str(Path(folder)/'save.sqlite3')
            with sqlite3.connect(path) as destination:self.g.db.backup(destination)
            restarted=Game(path,clock=self.clock)
            try:
                data=json.loads(restarted.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0])
                p=restarted.load_player('1',self.p.name,WS(),data)
                self.assertIn(sa.TOWER_CHEST,p.chests);self.assertIn(sa.TOWER_BOSS,p.starter_bosses)
                self.assertEqual(p.gold,self.p.gold)
                self.assertEqual(p.inventory,self.p.inventory)
            finally:restarted.db.close()

    async def test_http_serves_new_module_icons_and_current_revision(self):
        from aiohttp.test_utils import TestClient,TestServer
        from server.server import create_app
        app=create_app(':memory:');app.cleanup_ctx.clear()
        try:
            async with TestClient(TestServer(app)) as client:
                response=await client.get('/health');data=await response.json()
                self.assertEqual(data['ui_revision'],'UI_34');self.assertEqual(data['world_revision'],33)
                for route in ['/starter_adventures.js','/game.js','/assets/equipment/echo_rapier.svg']:
                    response=await client.get(route)
                    self.assertEqual(response.status,200,route);self.assertGreater(len(await response.read()),200)
                response=await client.get('/');html=await response.text()
                self.assertIn('starter_adventures.js?v=ui33',html)
                self.assertIn('game.js?v=ui33',html)
        finally:app['game'].db.close()

# Reuse only the helpers, without running every parent test twice.
for _method in dir(StarterAdventures):
    if _method.startswith('test_') and _method not in PersistenceAndHTTP.__dict__:
        setattr(PersistenceAndHTTP,_method,None)

if __name__=='__main__':unittest.main()
