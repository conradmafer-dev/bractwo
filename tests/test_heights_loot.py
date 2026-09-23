"""0.6 regressions: vertical routes, hybrid combat and authoritative exploration loot."""
import math
import random
import unittest
from collections import deque, Counter
from types import SimpleNamespace
import test_server as legacy
import test_living_world as living
from server import server as core, loot_tables


class HeightsLootTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=legacy.AuthoritativeServerTests.asyncSetUp
    asyncTearDown=legacy.AuthoritativeServerTests.asyncTearDown
    start_server=legacy.AuthoritativeServerTests.start_server
    restart=legacy.AuthoritativeServerTests.restart
    packet=legacy.AuthoritativeServerTests.packet
    connect=legacy.AuthoritativeServerTests.connect
    sync=legacy.AuthoritativeServerTests.sync
    command=legacy.AuthoritativeServerTests.command
    state=legacy.AuthoritativeServerTests.state
    place=legacy.AuthoritativeServerTests.place
    arena=living.LivingWorldTests.arena
    step=living.LivingWorldTests.step

    async def test_all_raised_floors_connect_arrival_stairs_and_sites(self):
        c=core.content
        self.assertEqual(len(c.ELEVATIONS),23)
        self.assertEqual({a['floor'] for a in c.ELEVATIONS},{1,2,3})
        for area in c.ELEVATIONS:
            floor=area['floor'];room=area['rooms'][0]
            def within(p):return room['x']<=p['x']<=room['x']+room['w'] and room['y']<=p['y']<=room['y']+room['h']
            stairs=[s for s in c.STAIRS if s['floor']==floor and within(s)]
            entry=next(s for s in stairs if s['to_floor']==floor-1)
            targets=stairs+[p for p in c.POIS if p['floor']==floor and within(p)]
            start=(round(entry['x']),round(entry['y']));todo=deque([start]);seen={start}
            while todo:
                x,y=todo.popleft()
                targets=[p for p in targets if math.hypot(p['x']-x,p['y']-y)>30]
                if not targets:break
                for dx,dy in [(20,0),(-20,0),(0,20),(0,-20)]:
                    q=x+dx,y+dy
                    if q not in seen and not self.game.blocked(*q,floor=floor):
                        seen.add(q);todo.append(q)
            self.assertFalse(targets,(area['id'],[p['id'] for p in targets]))
            # A positive floor is bounded: stepping off a cliff never becomes flying.
            p=core.Player('boundary','Boundary',x=room['x']+25,y=room['y']+room['h']-65,floor=floor)
            self.game.move(p,-100,0)
            self.assertGreaterEqual(p.x,room['x']+core.RADIUS)
            self.assertEqual(p.floor,floor)

    async def test_climb_to_plus_three_return_and_persist(self):
        ws,p,_=await self.connect('MountainWalker')
        p.level=30;p.hp=p.max_hp
        for floor in [1,2,3]:
            stair=next(s for s in core.content.STAIRS if s['id']==f'height_harpy_{floor}_up')
            p.x,p.y,p.floor=stair['x'],stair['y'],stair['floor'];p.transition_ready=0
            await self.command(ws,'descend',floor=99,to_x=1,to_y=1)
            self.assertEqual((p.floor,p.x,p.y),(floor,stair['to_x'],stair['to_y']))
        self.game.persist();await self.restart()
        ws,p,_=await self.connect('MountainWalker',create=False)
        self.assertEqual(p.floor,3);self.assertFalse(self.game.blocked(p.x,p.y,floor=3))
        p.transition_ready=0;p.pvp_combat_until=self.clock()+20
        await self.command(ws,'descend');self.assertEqual(p.floor,3)
        p.pvp_combat_until=0
        await self.command(ws,'descend');self.assertEqual(p.floor,2)

    async def test_water_is_blocking_and_road_bridges_are_walkable(self):
        c=core.content
        self.assertGreater(max(w['b'][1] for w in c.WATERWAYS),90000)
        river=next(w for w in c.WATERWAYS if w['y']>4000 and c.WATER_MAP.blocked(*w['a']))
        x,y=river['a'];self.assertTrue(self.game.blocked(x,y))
        actor=core.Player('swim','NoSwimming',x=x-220,y=y)
        if not self.game.blocked(actor.x,actor.y):
            self.game.move(actor,440,0)
            self.assertLess(actor.x,x)
        self.assertGreater(len(c.BRIDGES),20)
        for bridge in c.BRIDGES:
            a,b=bridge['a'],bridge['b']
            for t in (0,.5,1):
                self.assertFalse(self.game.blocked(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t),bridge['id'])

    async def test_hybrids_close_to_melee_while_retaining_ranged_attacks(self):
        ws,p,_=await self.connect('HybridWitness')
        for kind in ['boss','cyclops','ogre','harpy','dragon','demon']:
            e=self.arena(p,kind,x=11000,y=1000,distance=350)
            p.level=120;p.hp=p.max_hp;e.aoe_ready=self.game.time+100
            self.step(.1)
            self.assertTrue(self.game.hazards,kind)
            initial=e.x
            self.step(.3)
            self.assertLess(e.x,initial,kind) # a regular throw does not freeze the chase
            self.step(3)
            self.assertLess(core.distance(p,e),100,kind)
            old=p.hp;e.ranged_ready=self.game.time+100;e.ready=0
            self.game.hazards=[]
            self.step(1.5)
            self.assertLess(p.hp,old,kind)
            self.assertTrue(any(fx['kind']=='sword' and fx['source_id']==e.id for fx in self.game.effects),kind)

    async def test_boss_resumes_chase_after_special_and_archer_keeps_range(self):
        ws,p,_=await self.connect('CombatRoles')
        e=self.arena(p,'boss',x=11000,y=1000,distance=420)
        p.level=100;p.hp=p.max_hp;e.aoe_ready=0
        self.step(.1);initial=e.x
        self.assertTrue(any(fx.get('special') for fx in self.game.effects))
        self.step(1.7)
        self.assertLess(e.x,initial-25)
        self.step(3)
        self.assertLess(core.distance(e,p),100)
        e=self.arena(p,'bandit_archer',x=11000,y=1000,distance=360)
        p.level=100;p.hp=p.max_hp;self.step(4)
        self.assertGreater(core.distance(e,p),250)

    async def test_hybrid_cannot_hit_between_floors(self):
        ws,p,_=await self.connect('FloorCombat')
        e=self.arena(p,'boss',x=11000,y=1000,distance=40)
        p.floor=1;old=p.hp
        self.step(3)
        self.assertEqual(p.hp,old)
        self.assertEqual(e.attacker_id,'')

    async def test_sites_reject_remote_use_floor_forgery_level_and_combat(self):
        ws,p,_=await self.connect('SiteBounds')
        site=next(s for s in core.content.POIS if s['action']=='wind')
        await self.command(ws,'interact',site_id=site['id'],x=site['x'],y=site['y'],floor=site['floor'])
        self.assertEqual(p.wind_until,0)
        p.x,p.y,p.floor=site['x'],site['y'],0;p.level=100
        await self.command(ws,'interact');self.assertEqual(p.wind_until,0)
        p.floor=site['floor'];p.level=1
        await self.command(ws,'interact');self.assertEqual(p.wind_until,0)
        p.level=100;p.combat_until=self.clock()+20
        await self.command(ws,'interact');self.assertEqual(p.wind_until,0)
        p.combat_until=0
        speed=self.state(p)['speed'];await self.command(ws,'interact')
        self.assertAlmostEqual(self.state(p)['speed'],speed*1.15,delta=.002)
        expiry=p.wind_until;self.clock.advance(5)
        await self.command(ws,'interact');self.assertEqual(p.wind_until,expiry)
        self.game.persist();await self.restart()
        ws,p,_=await self.connect('SiteBounds',create=False)
        self.assertEqual(p.wind_until,expiry)
        self.clock.advance(90);self.assertAlmostEqual(self.state(p)['speed'],speed,delta=.002)
        await self.command(ws,'interact');self.assertEqual(p.wind_until,expiry)

    async def test_spring_and_ward_have_real_effects_without_pvp_advantage(self):
        ws,p,_=await self.connect('SpringUser')
        p.level=100;p.hp=p.max_hp-80;p.mana=0
        spring=next(s for s in core.content.POIS if s['action']=='spring')
        p.x,p.y,p.floor=spring['x'],spring['y'],spring['floor']
        await self.command(ws,'interact')
        self.assertEqual((p.hp,p.mana),(p.max_hp,p.max_mana))
        p.hp-=20;await self.command(ws,'interact');self.assertEqual(p.hp,p.max_hp-20)
        ward=next(s for s in core.content.POIS if s['action']=='ward')
        p.x,p.y,p.floor=ward['x'],ward['y'],ward['floor']
        await self.command(ws,'interact');self.assertGreater(p.ward_until,self.clock())
        old=p.hp;self.game.damage_player(p,100);guarded=old-p.hp
        p.ward_until=0;old=p.hp;self.game.damage_player(p,100);normal=old-p.hp
        self.assertAlmostEqual(guarded,normal*.88)
        # This exploration effect never reduces damage from a player.
        attacker=core.Player('attacker','Attacker');p.ward_until=self.clock()+100
        old=p.hp;self.game.damage_player(p,100,killer=attacker)
        self.assertAlmostEqual(old-p.hp,normal)

    async def test_cache_rewards_capacity_cooldown_and_restart_are_atomic(self):
        ws,p,_=await self.connect('CacheKeeper')
        site=next(s for s in core.content.POIS if s['action']=='cache')
        p.x,p.y,p.floor=site['x'],site['y'],site['floor'];p.level=100
        p.inventory=[core.make_item('copper_ring') for _ in range(38)]
        await self.command(ws,'interact')
        self.assertNotIn(site['id'],p.site_cooldowns)
        p.inventory=[];old=p.gold
        await self.command(ws,'interact')
        self.assertIn(len(p.inventory),(2,3));items=[i['uid'] for i in p.inventory]
        self.assertTrue(any(i['slot']=='trophy' for i in p.inventory))
        self.assertEqual(p.gold,old)
        await self.command(ws,'interact')
        self.assertEqual(items,[i['uid'] for i in p.inventory])
        self.game.persist();await self.restart()
        ws,p,_=await self.connect('CacheKeeper',create=False)
        await self.command(ws,'interact')
        self.assertEqual(items,[i['uid'] for i in p.inventory])
        self.clock.advance(1801);await self.command(ws,'interact')
        self.assertGreater(len(p.inventory),len(items))

    async def test_trophies_sell_but_cannot_be_equipped(self):
        ws,p,_=await self.connect('TrophyTrader')
        trophy=core.make_item('trophy_dragon');p.inventory.append(trophy)
        before=dict(p.equipment)
        await self.command(ws,'equip',uid=trophy['uid'],slot='ring',attack=10000)
        self.assertEqual(p.equipment,before)
        p.x,p.y,p.floor=680,1180,0;old=p.gold
        await self.command(ws,'sell',uid=trophy['uid'])
        self.assertEqual(p.gold,old+trophy['value']);self.assertNotIn(trophy,p.inventory)
        await self.command(ws,'sell',uid=trophy['uid']);self.assertEqual(p.gold,old+trophy['value'])

    async def test_loot_tables_have_valid_class_gear_and_credible_frequencies(self):
        rng=random.Random(6050);counts=Counter();samples=40000
        for kind,spec in core.ENEMY_TYPES.items():
            for vocation in core.CLASSES:
                for _ in range(20):
                    drops=loot_tables.roll(vocation,spec,rng)
                    if spec.get('boss'):self.assertTrue(any(t=='item' and core.ITEMS[k]['slot']!='trophy' for t,k in drops))
                    for t,key in drops:
                        if t=='potion':self.assertIn(key,core.POTIONS)
                        else:
                            item=core.ITEMS[key]
                            self.assertTrue(item['slot']=='trophy' or vocation in item['class_ids'])
        for _ in range(samples):
            drops=loot_tables.roll('paladin',core.ENEMY_TYPES['cyclops'],rng)
            for t,k in drops:
                counts['trophy' if k.startswith('trophy_') else 'unique' if k.startswith('unique_') else t]+=1
        for key,rate in [('item',.12),('trophy',.24),('potion',.07),('unique',.015)]:
            self.assertAlmostEqual(counts[key]/samples,rate,delta=.009)
        for kind in ['rat','wolf','spider','goblin']:
            self.assertEqual(core.ENEMY_TYPES[kind]['loot']['legendary_chance'],0)
        self.assertEqual(core.ENEMY_TYPES['ancient_dragon']['loot']['legendary_chance'],.002)
