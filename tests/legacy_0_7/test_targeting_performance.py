"""0.4.1 regressions: selected enemies, retaliation, compact owner updates."""
import json
import math
import unittest
import test_server as legacy
from server import server as core


class TargetingPerformanceTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=legacy.AuthoritativeServerTests.asyncSetUp
    asyncTearDown=legacy.AuthoritativeServerTests.asyncTearDown
    start_server=legacy.AuthoritativeServerTests.start_server
    packet=legacy.AuthoritativeServerTests.packet
    connect=legacy.AuthoritativeServerTests.connect
    sync=legacy.AuthoritativeServerTests.sync
    command=legacy.AuthoritativeServerTests.command
    place=legacy.AuthoritativeServerTests.place

    def arena(self,p):
        self.place(p,10000,10000,level=30)
        for e in self.game.enemies.values():
            e.alive=False;e.respawn_at=0

    def enemy(self,p,kind='goblin',offset=250):
        e=next(e for e in self.game.legacy_enemies if e.kind==kind and not e.alive)
        e.x=e.home_x=p.x+offset;e.y=e.home_y=p.y;e.floor=p.floor
        e.hp=5000;e.alive=True;e.ready=0;e.attacker_id='';e.attacker_until=0
        return e

    async def test_explicit_enemy_target_ignores_nearer_monster_and_pvp_lock(self):
        ws,p,_=await self.connect('SelectArcher',class_id='paladin');self.arena(p)
        close=self.enemy(p,offset=45);far=self.enemy(p,offset=230)
        self.assertTrue(p.pvp_safety)
        await self.command(ws,'attack',enemy_id=far.id)
        self.assertLess(far.hp,5000);self.assertEqual(close.hp,5000)
        self.assertEqual(far.attacker_id,p.id)
        self.assertEqual(p.skull(self.clock()),'none')

    async def test_selected_target_rejects_invalid_floor_wall_range_and_player_ids(self):
        ws,p,_=await self.connect('TargetChecks',class_id='paladin');self.arena(p)
        e=self.enemy(p,offset=100)
        for bad in ['missing',p.id,[],{},False,123,None,'']:
            await self.command(ws,'attack',enemy_id=bad)
            self.assertEqual(e.hp,5000)
        await self.command(ws,'attack',enemy_id=e.id,target_id=p.id)
        self.assertEqual(e.hp,5000)
        e.floor=-1;await self.command(ws,'attack',enemy_id=e.id);self.assertEqual(e.hp,5000)
        e.floor=0;e.x=p.x+900;await self.command(ws,'attack',enemy_id=e.id);self.assertEqual(e.hp,5000)
        p.x,p.y=1450,950;e.x,e.y=1700,950
        self.assertFalse(self.game.line_clear(p,e))
        await self.command(ws,'attack',enemy_id=e.id);self.assertEqual(e.hp,5000)
        e.alive=False;await self.command(ws,'attack',enemy_id=e.id);self.assertEqual(e.hp,5000)

    async def test_shot_records_attacker_and_ranged_enemy_returns_fire(self):
        ws,p,_=await self.connect('ProvokeMage',class_id='mage');self.arena(p)
        e=self.enemy(p,offset=250)
        # 0.5 deliberately detects before player range: no unprovoked safe shot.
        self.assertGreater(core.ENEMY_TYPES[e.kind]['aggro'],core.WEAPONS['bow']['range'])
        await self.command(ws,'attack',enemy_id=e.id)
        start_hp=p.hp
        for _ in range(120):
            self.clock.advance(.05);self.game.step(.05)
        self.assertLess(p.hp,start_hp)
        self.assertGreater(e.attacker_until,self.game.time)
        self.assertLess(core.distance(p,e),core.ENEMY_TYPES[e.kind]['range'])

    async def test_retaliation_respects_safe_zone_floor_and_finite_leash(self):
        ws,p,_=await self.connect('RetaliationBounds',class_id='mage');self.arena(p)
        e=self.enemy(p,offset=250)
        await self.command(ws,'attack',enemy_id=e.id)
        p.floor=-1;hp=p.hp;self.game.step(.05)
        self.assertEqual(e.x,e.home_x);self.assertEqual(p.hp,hp)
        p.floor=0;p.x=e.home_x-core.ENEMY_TYPES[e.kind]["leash"]-100;e.attacker_until=self.game.time+20
        self.game.step(.05);self.assertLessEqual(math.hypot(e.x-e.home_x,e.y-e.home_y),core.ENEMY_TYPES[e.kind]["wander"]+5);self.assertEqual(p.hp,hp)
        p.x,p.y=560,1180;e.x=e.home_x=830;e.y=e.home_y=1180
        e.attacker_until=self.game.time+20;hp=p.hp
        self.game.step(.05);self.assertLessEqual(math.hypot(e.x-e.home_x,e.y-e.home_y),core.ENEMY_TYPES[e.kind]["wander"]+5);self.assertEqual(p.hp,hp)

    async def test_abilities_spells_and_runes_provoke_and_use_selected_single_target(self):
        ws,p,_=await self.connect('MagicProvocation',class_id='mage');self.arena(p)
        p.level=80;p.promoted=True;p.mana=p.max_mana
        e=self.enemy(p,offset=250)
        for kind,fields in [('ability',{}),('cast',{'spell_id':'flame_wave'}),('rune_use',{'rune_id':'fire','enemy_id':e.id})]:
            self.clock.advance(30);p.mana=p.max_mana;p.runes['fire']=5;e.attacker_id='';e.hp=5000
            await self.command(ws,kind,**fields)
            self.assertLess(e.hp,5000);self.assertEqual(e.attacker_id,p.id)
        close=self.enemy(p,kind='wolf',offset=60)
        self.clock.advance(30);p.runes['death']=1;e.hp=5000
        await self.command(ws,'rune_use',rune_id='death',enemy_id=e.id)
        self.assertLess(e.hp,5000);self.assertEqual(close.hp,5000)
        p.class_id='paladin';p.mana=p.max_mana;self.clock.advance(30);e.hp=5000
        await self.command(ws,'ability',enemy_id=e.id)
        self.assertLess(e.hp,5000);self.assertEqual(close.hp,5000)

    async def test_compact_wire_updates_reconstruct_owner_and_reset_on_reconnect(self):
        ws=await self.client.ws_connect('/ws')
        hello={'type':'hello','name':'CompactReader','password':'testpass123','create':True,'class_id':'knight','compact_state':True}
        await ws.send_json(hello);welcome=await self.packet(ws,'welcome')
        self.assertTrue(welcome['owner_deltas']);pid=welcome['id'];p=self.game.players[pid]
        first=await self.packet(ws,'state');owner=next(q for q in first['players'] if q['id']==pid)
        self.assertIn('quests',owner);self.assertIn('inventory',owner)
        await self.game.broadcast_states();second=await self.packet(ws,'state')
        delta=next(q for q in second['players'] if q['id']==pid)
        self.assertNotIn('quests',delta);self.assertNotIn('inventory',delta)
        self.assertLess(len(json.dumps(second)),len(json.dumps(first))*.5)
        p.runes['fire']=3
        await self.game.broadcast_states();third=await self.packet(ws,'state')
        owner.update(delta);owner.update(next(q for q in third['players'] if q['id']==pid))
        self.assertEqual(owner['runes']['fire'],3);self.assertIn('inventory',owner)
        p.ws=None
        await ws.close()
        fresh=await self.client.ws_connect('/ws');hello['create']=False
        await fresh.send_json(hello);await self.packet(fresh,'welcome')
        initial=await self.packet(fresh,'state');own=next(q for q in initial['players'] if q['id']==pid)
        self.assertIn('quests',own);self.assertIn('inventory',own)
        self.assertEqual(own['runes']['fire'],3)

    async def test_legacy_packets_stay_full_and_private_data_never_leaks(self):
        a,p,_=await self.connect('LegacyOwner');b,q,_=await self.connect('OtherOwner')
        self.game.compact_clients.add(p.id)
        self.game.wire_snapshot(p)
        reduced=self.game.wire_snapshot(p)
        foreign=next(x for x in reduced['players'] if x['id']==q.id)
        self.assertNotIn('quests',foreign);self.assertNotIn('bank_gold',foreign)
        for _ in range(2):
            packet=self.game.wire_snapshot(q)
            self.assertNotIn('owner_delta',packet)
            own=next(x for x in packet['players'] if x['id']==q.id)
            self.assertIn('quests',own);self.assertIn('inventory',own)
        response=await self.client.get('/runtime.js')
        self.assertEqual(response.status,200)
        self.assertIn('BractwoRuntime',await response.text())
