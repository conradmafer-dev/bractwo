"""0.5 regressions for real simulation, network commands and world accessibility."""
import math
import unittest
from types import SimpleNamespace
from collections import Counter
import test_server as legacy
from server import server as core
from server.living_world import SurfaceMap, SURFACES


class LivingWorldTests(unittest.IsolatedAsyncioTestCase):
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

    def arena(self,p,kind,x=10000,y=10000,distance=360):
        # Isolate mechanics from generated encounters, while preserving real walls.
        for e in self.game.enemies.values():e.alive=False;e.respawn_at=0
        self.place(p,x,y,level=8);p.hp=p.max_hp;p.dx=p.dy=0;p.input_time=-10
        e=core.Enemy('test_enemy',kind,x+distance,y,core.ENEMY_TYPES[kind]['hp'],x+distance,y)
        self.game.enemies[e.id]=e;self.game.legacy_enemies.append(e)
        self.game.hazards=[]
        return e

    def step(self,seconds):
        for _ in range(round(seconds/.05)):
            self.clock.advance(.05);self.game.step(.05)

    async def test_premium_is_mock_server_owned_expiring_and_persistent(self):
        ws,p,w=await self.connect('PremiumTest')
        self.assertEqual(w['world']['premium']['mode'],'simulation')
        self.assertEqual(w['world']['premium']['price_pln'],10)
        original=self.state(p)['speed'];before=p.gold
        for invalid in ('true',1,None,{},[]):
            await self.command(ws,'premium_demo',enabled=invalid)
            self.assertEqual(p.premium_demo_until,0)
        await self.command(ws,'input',x=0,y=0,premium_demo_until=9999999999,speed=9999)
        self.assertEqual(p.premium_demo_until,0)
        await self.command(ws,'premium_demo',enabled=True,price=0,multiplier=999)
        expiry=p.premium_demo_until
        self.assertEqual(expiry,self.clock()+30*86400)
        self.assertAlmostEqual(self.state(p)['speed'],original*1.2,delta=.002)
        await self.command(ws,'premium_demo',enabled=True)
        self.assertEqual(p.premium_demo_until,expiry);self.assertEqual(p.gold,before)
        self.game.persist();await self.restart()
        ws,p,_=await self.connect('PremiumTest',create=False)
        self.assertEqual(p.premium_demo_until,expiry)
        self.clock.advance(30*86400+1)
        self.assertFalse(self.state(p)['premium_demo'])
        self.assertAlmostEqual(self.state(p)['speed'],original,delta=.002)
        await self.command(ws,'premium_demo',enabled=True)
        await self.command(ws,'premium_demo',enabled=False)
        self.assertEqual(p.premium_demo_until,0)

    async def test_terrain_speed_is_authoritative_and_composes_with_premium_haste(self):
        ws,p,_=await self.connect('GroundWalker')
        # Class/level speed stays common; surface classification comes from server data.
        p.current_wall_time=self.clock()
        for point in [(560,1180),(6000,3000),(5600,1600),(2000,2000),(13000,11520)]:
            p.x,p.y=point
            kind=core.content.SURFACE_MAP.at(*point)
            self.assertAlmostEqual(p.speed,core.player_speed(p.level)*SURFACES[kind]['speed'])
        p.haste_until=self.clock()+15;p.premium_demo_until=self.clock()+100
        kind=core.content.SURFACE_MAP.at(p.x,p.y)
        self.assertAlmostEqual(p.speed,core.player_speed(p.level)*1.3*1.2*SURFACES[kind]['speed'])
        local=SurfaceMap([[[0,0],[1000,0]]],[{'x':100,'y':-200,'w':400,'h':400,'kind':'mud'}],[],[])
        self.assertEqual(local.at(300,0),'path') # trail crosses bog
        self.assertEqual(local.at(300,100),'mud')
        self.assertEqual(local.at(300,100,-1),'stone')
        self.assertEqual(local.at(0,0),'path')

    async def test_detection_beyond_bow_and_idle_roaming_without_interaction(self):
        ws,p,_=await self.connect('RoamingWitness')
        e=self.arena(p,'wolf',distance=600)
        origin=(e.x,e.y);hp=p.hp;self.step(3)
        self.assertGreater(math.dist(origin,(e.x,e.y)),5)
        self.assertEqual(p.hp,hp);self.assertEqual(e.attacker_id,'')
        e.x=e.home_x=p.x+350;e.y=e.home_y=p.y;e.wander_ready=0
        self.assertGreater(core.distance(p,e),core.WEAPONS['bow']['range'])
        origin=e.x;self.step(.3)
        self.assertLess(e.x,origin);self.assertEqual(e.attacker_id,p.id)
        self.assertTrue(all(s['aggro']>core.WEAPONS['bow']['range'] for s in core.ENEMY_TYPES.values()))
        self.assertGreater(core.ENEMY_TYPES['vampire']['speed'],core.ENEMY_TYPES['golem']['speed'])
        self.assertGreater(core.ENEMY_TYPES['wolf']['speed'],core.ENEMY_TYPES['skeleton']['speed'])

    async def test_ranged_enemy_returns_damage_outside_player_range(self):
        ws,p,_=await self.connect('RangedWitness',class_id='paladin')
        e=self.arena(p,'bandit_archer',distance=370);hp=p.hp
        self.step(.1)
        self.assertGreater(core.distance(p,e),core.WEAPONS['bow']['range'])
        self.assertEqual(p.hp,hp)
        self.assertTrue(any(fx['kind']=='danger_zone' for fx in self.game.effects))
        self.step(.8)
        self.assertLess(p.hp,hp)
        self.assertTrue(any(fx['kind']=='enemy_arrow' for fx in self.game.effects))

    async def test_boss_has_telegraph_dodgeable_aoe_and_phase_variety(self):
        ws,p,_=await self.connect('BossWitness')
        e=self.arena(p,'boss',distance=300);hp=p.hp;e.aoe_ready=0
        self.step(.1)
        warning=next(fx for fx in self.game.effects if fx['kind']=='danger_zone' and fx['special'])
        self.assertGreaterEqual(warning['duration'],1)
        self.assertEqual(p.hp,hp)
        p.y-=260;e.ready=100 # sidestep fixed aim, with no new basic shot
        self.step(1.6);self.assertEqual(p.hp,hp)
        p.x,p.y=e.x-300,e.y;e.special_count=0
        self.game.queue_enemy_attack(e,p,special=True)
        self.step(1.6);self.assertLess(p.hp,hp)
        self.game.hazards=[];e.special_count=1
        self.game.queue_enemy_attack(e,p,special=True)
        self.assertEqual(len(self.game.hazards),3)
        self.game.hazards=[];e.special_count=2
        self.game.queue_enemy_attack(e,p,special=True)
        self.assertEqual(self.game.hazards[0]['radius'],245)
        self.game.hazards=[];e.kind='ancient_dragon';e.special_count=0
        self.game.queue_enemy_attack(e,p,special=True)
        self.assertEqual(len(self.game.hazards),4)
        self.assertEqual({h['element'] for h in self.game.hazards},{'fire'})

    async def test_running_in_bow_range_with_premium_and_haste_is_not_invulnerability(self):
        ws,p,_=await self.connect('KitingPaladin',class_id='paladin')
        e=self.arena(p,'boss',x=11285,y=1000,distance=-285)
        p.level=50;p.hp=p.max_hp
        p.premium_demo_until=self.clock()+100;p.haste_until=self.clock()+100
        initial=p.hp
        # A clear, obstacle-free orbit within bow range, with continuous input.
        for i in range(400):
            a=math.atan2(p.y-1000,p.x-11000)+.1
            tx,ty=11000+math.cos(a)*285,1000+math.sin(a)*285
            self.assertFalse(self.game.blocked(tx,ty))
            d=math.hypot(tx-p.x,ty-p.y)
            p.dx,p.dy=(tx-p.x)/d,(ty-p.y)/d;p.input_time=self.game.time
            self.step(.05)
        self.assertLess(p.hp,initial)
        self.assertGreater(p.hp,0) # demanding, without an instant unavoidable death
        self.assertLess(core.distance(p,e),core.WEAPONS['bow']['range'])

    async def test_retreating_boss_recovers_to_prevent_edge_of_leash_farming(self):
        ws,p,_=await self.connect('LeashWitness')
        e=self.arena(p,'boss',x=11000,y=1000,distance=0)
        e.x=e.home_x+900;e.hp=e.max_hp*.3
        p.x=e.home_x+core.ENEMY_TYPES[e.kind]['leash']+100
        e.attacker_id=p.id;e.attacker_until=self.game.time+20
        initial=e.hp;self.step(1)
        self.assertGreater(e.hp,initial+e.max_hp*.1)
        self.assertLess(e.x,e.home_x+900)

    async def test_enemy_shots_respect_walls_floor_safe_zone_and_death(self):
        ws,p,_=await self.connect('ShotBounds')
        e=self.arena(p,'cyclops',x=1440,y=900,distance=280);hp=p.hp
        self.game.queue_enemy_attack(e,p);self.step(1.2)
        self.assertEqual(p.hp,hp) # river/wall absorbs attack
        e.x=e.home_x=10000;p.x,p.y=10300,10000;e.y=e.home_y=10000
        self.game.queue_enemy_attack(e,p);p.floor=-1;self.step(1.2)
        self.assertEqual(p.hp,hp)
        p.floor=0;p.x,p.y=560,1180;e.x,e.y=830,1180
        self.game.queue_enemy_attack(e,p);self.step(1.2)
        self.assertEqual(p.hp,hp)
        p.x,p.y=10300,10000;e.x,e.y=10000,10000
        self.game.queue_enemy_attack(e,p);e.alive=False;self.step(1.2)
        self.assertEqual(p.hp,hp)

    async def test_world_ecology_early_variety_and_optional_large_threats(self):
        c=core.content
        new={'bandit_archer','skeleton_archer','spitting_spider','cyclops','bear','harpy','ghoul','ogre','scorpion'}
        self.assertTrue(new<=core.ENEMY_TYPES.keys())
        self.assertTrue(new<={e.kind for e in self.game.enemies.values()})
        self.assertEqual(set(core.ENEMY_TYPES),{e.kind for e in self.game.enemies.values()})
        for q in core.QUESTS:
            if not q['id'].startswith('hunt_'):continue
            region=c.REGIONS[int(q['id'].split('_')[1])]
            for objective in q['objectives']:
                if objective['type']=='kill':
                    self.assertTrue(any(e.kind==objective['target'] and e.floor==0 and math.hypot(e.home_x-objective['x'],e.home_y-objective['y'])<1 for e in self.game.enemies.values()),q['id'])
        nearby=[e for e in self.game.enemies.values() if e.x<6500 and e.y<6500 and e.floor==0]
        self.assertGreaterEqual(len({e.kind for e in nearby}),20)
        self.assertGreaterEqual(len([l for l in core.LANDMARKS if l.get('hint')]),10)
        for ground in c.HUNTING_GROUNDS:
            if ground['decoration']=='camp':
                self.assertTrue(set(ground['members'])<={'goblin','troll','bandit','bandit_archer','orc','orc_shaman'})
        self.assertTrue(any({'skeleton','skeleton_archer','vampire'}<=set(g['members']) for g in c.HUNTING_GROUNDS))
        self.assertTrue(any(g['members']==['cyclops'] for g in c.HUNTING_GROUNDS))
        self.assertTrue(any(e.kind=='dragon' and e.floor==-1 and e.x<6500 for e in self.game.enemies.values()))
        self.assertGreater(core.ENEMY_TYPES['dragon']['size'],core.ENEMY_TYPES['wolf']['size'])
        self.assertGreater(core.ENEMY_TYPES['demon']['size'],core.ENEMY_TYPES['goblin']['size'])
        self.assertGreater(sum(o.get('type')=='mountain' for o in core.OBSTACLES),100)

    async def test_all_road_centrelines_and_entry_points_are_walkable(self):
        samples=0
        for ri,road in enumerate(core.content.ROADS):
            for a,b in zip(road,road[1:]):
                n=max(1,math.ceil(math.dist(a,b)/20))
                for i in range(n):
                    x=a[0]+(b[0]-a[0])*i/n;y=a[1]+(b[1]-a[1])*i/n
                    self.assertFalse(self.game.blocked(x,y),(ri,round(x),round(y)))
                    samples+=1
        self.assertGreater(samples,100000)
        self.assertTrue(all(len(path)>3 for path in core.content.ROADS))
