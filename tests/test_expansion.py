"""0.4 integration coverage: live WebSocket commands, disposable SQLite saves.
Fixture levels/positions isolate rules; no development commands enter production.
"""
import json
import asyncio
import math
import unittest
from collections import deque
import test_server as legacy
from server import server as core
from server import world_content as content
from server.progression import skill_level


class ExpansionTests(unittest.IsolatedAsyncioTestCase):
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
    elapsed=legacy.AuthoritativeServerTests.elapsed
    enemy_fixture=legacy.AuthoritativeServerTests.enemy_fixture
    give_item=legacy.AuthoritativeServerTests.give_item

    def npc(self,p,service,city='przystan'):
        n=next(n for n in core.NPCS if n.get('service')==service and n.get('city_id')==city)
        p.x,p.y,p.floor=n['x'],n['y'],0
        p.combat_until=p.pvp_combat_until=0
        return n

    async def test_world_size_spacing_catalogue_and_no_blocked_spawns(self):
        self.assertEqual((core.WIDTH,core.HEIGHT),(128000,92160))
        self.assertEqual(core.WIDTH*core.HEIGHT//(3200*2304),1600)
        self.assertEqual(len(content.CITIES),5)
        self.assertEqual(len(content.REGIONS),20)
        self.assertEqual(len(content.DUNGEONS),30)
        minimum=min(math.hypot(a['x']-b['x'],a['y']-b['y']) for i,a in enumerate(content.CITIES) for b in content.CITIES[i+1:])
        self.assertGreater(minimum,34000)
        self.assertGreater(len(self.game.enemies),7000)
        for e in self.game.enemies.values():
            self.assertFalse(self.game.blocked(e.x,e.y,floor=e.floor),(e.id,e.kind,e.x,e.y,e.floor))
        for s in content.STAIRS:
            self.assertFalse(self.game.blocked(s['x'],s['y'],floor=s['floor']),s['id'])
            self.assertFalse(self.game.blocked(s['to_x'],s['to_y'],floor=s['to_floor']),s['id'])

    async def test_dungeon_rooms_form_continuous_walkable_routes(self):
        # Walk a collision-checked grid from each arrival to its onward stair.
        for d in content.DUNGEONS:
            index=int(d['id'].split('_')[1]);floor=d['floor']
            entry=next(s for s in content.STAIRS if s['id']==f'up_{index}' and floor==-1 or s['id']==f'return_{index}' and floor==-2)
            start=(round(entry['x']),round(entry['y']))
            goal=next(s for s in content.STAIRS if s['id']==f'deep_{index}') if floor==-1 else {'x':start[0]+620,'y':start[1]+120}
            todo=deque([start]);seen={start};found=False
            while todo:
                x,y=todo.popleft()
                if math.hypot(x-goal['x'],y-goal['y'])<45:found=True;break
                for dx,dy in ((20,0),(-20,0),(0,20),(0,-20)):
                    pt=(x+dx,y+dy)
                    if pt not in seen and not self.game.blocked(*pt,floor=floor):seen.add(pt);todo.append(pt)
            self.assertTrue(found,d['id'])

    async def test_stairs_gate_floor_isolation_exit_and_persistence(self):
        ws,p,_=await self.connect('FloorWalker')
        p.level=100;p.hp=p.max_hp;p.mana=p.max_mana
        entry=next(s for s in content.STAIRS if s['id']=='down_0')
        self.place(p,entry['x'],entry['y'])
        await self.command(ws,'descend',to_x=999999,floor=-2)
        self.assertEqual((p.floor,p.x,p.y),(-1,entry['to_x'],entry['to_y']))
        before=p.floor;await self.command(ws,'descend');self.assertEqual(p.floor,before)
        p.transition_ready=0;await self.command(ws,'descend');self.assertEqual(p.floor,0)
        gate=next(s for s in content.STAIRS if s['id']=='deep_19')
        self.place(p,gate['x'],gate['y'],level=99);p.floor=-1;p.transition_ready=0
        await self.command(ws,'descend');self.assertEqual(p.floor,-1)
        p.level=100;p.pvp_combat_until=self.clock()+20
        await self.command(ws,'descend');self.assertEqual(p.floor,-1)
        p.pvp_combat_until=0
        await self.command(ws,'descend');self.assertEqual(p.floor,-2)
        self.game.persist();await self.restart()
        _,p,_=await self.connect('FloorWalker',create=False)
        self.assertEqual(p.floor,-2)
        self.assertFalse(self.game.blocked(p.x,p.y,floor=p.floor))

    async def test_spells_require_level_vocation_promotion_mana_and_cooldown(self):
        ws,p,_=await self.connect('SpellMage',class_id='mage')
        self.place(p,1000,2010,level=7);p.hp-=30;old=(p.hp,p.mana)
        await self.command(ws,'cast',spell_id='mend');self.assertEqual((p.hp,p.mana),old)
        p.level=8
        await self.command(ws,'cast',spell_id='mend');self.assertGreater(p.hp,old[0]);self.assertEqual(p.mana,old[1]-20)
        p.hp-=10;old=(p.hp,p.mana)
        await self.command(ws,'cast',spell_id='mend');self.assertEqual((p.hp,p.mana),old)
        self.clock.advance(4);p.level=30;p.mana=p.max_mana
        e=self.enemy_fixture(p,'boss');old=e.hp
        await self.command(ws,'cast',spell_id='flame_wave');self.assertEqual(e.hp,old)
        p.promoted=True
        await self.command(ws,'cast',spell_id='whirl');self.assertEqual(e.hp,old)
        await self.command(ws,'cast',spell_id='flame_wave');self.assertLess(e.hp,old)
        self.clock.advance(9);p.mana=0;old=e.hp
        await self.command(ws,'cast',spell_id='flame_wave');self.assertEqual(e.hp,old)
        p.mana=p.max_mana;self.clock.advance(2)
        speed=self.state(p)['speed'];await self.command(ws,'cast',spell_id='haste')
        self.assertAlmostEqual(self.state(p)['speed'],speed*1.3,delta=.002)
        self.clock.advance(16);self.assertAlmostEqual(self.state(p)['speed'],speed,delta=.002)

    async def test_promotion_mastery_blessing_bank_depot_and_save(self):
        ws,p,_=await self.connect('CityVeteran')
        self.place(p,1000,2010,level=50);p.gold=10000
        await self.command(ws,'promote');self.assertFalse(p.promoted)
        self.npc(p,'master');await self.command(ws,'promote');self.assertTrue(p.promoted);self.assertEqual(p.gold,8000)
        await self.command(ws,'promote');self.assertEqual(p.gold,8000)
        hp=p.max_hp;await self.command(ws,'mastery',branch='vitality');self.assertEqual(p.max_hp,hp+12)
        await self.command(ws,'mastery',branch='power');self.assertEqual(p.mastery.get('power',0),0)
        await self.command(ws,'bless');self.assertTrue(p.blessed)
        self.npc(p,'bank');await self.command(ws,'bank_deposit',amount='all');self.assertEqual((p.gold,p.bank_gold),(0,7500))
        for invalid in (-1,1.5,True,999999,{},[]):
            await self.command(ws,'bank_withdraw',amount=invalid)
        self.assertEqual((p.gold,p.bank_gold),(0,7500))
        await self.command(ws,'bank_withdraw',amount=100);self.assertEqual((p.gold,p.bank_gold),(100,7400))
        item=self.give_item(p,'knight_weapon_4')
        await self.command(ws,'depot_store',uid=p.equipment['weapon']);self.assertEqual(len(p.depot),0)
        await self.command(ws,'depot_store',uid=item['uid']);self.assertEqual(len(p.depot),1)
        await self.command(ws,'depot_store',uid=item['uid']);self.assertEqual(len(p.depot),1)
        self.npc(p,'bank','brzezina');await self.command(ws,'bind_city')
        await self.command(ws,'depot_take',uid=item['uid']);self.assertEqual(len(p.depot),0);self.assertIn(item,p.inventory)
        await self.command(ws,'depot_store',uid=item['uid'])
        self.game.persist();await self.restart();_,p,_=await self.connect('CityVeteran',create=False)
        self.assertTrue(p.promoted);self.assertEqual(p.home_city,'brzezina');self.assertEqual(p.bank_gold,7400)
        self.assertEqual(p.depot[0]['uid'],item['uid']);self.assertEqual(p.mastery,{'vitality':1})
        p.gold=100;p.xp=40;p.hp=1
        self.game.damage_player(p,1000)
        self.assertEqual((p.gold,p.xp,p.bank_gold,len(p.depot)),(97,38,7400,1));self.assertFalse(p.blessed)
        self.clock.advance(5);self.game.step(.05)
        city=next(c for c in content.CITIES if c['id']=='brzezina')
        self.assertEqual((p.x,p.y,p.floor),(city['x'],city['y'],0))

    async def test_travel_requires_port_money_level_and_no_combat(self):
        ws,p,_=await self.connect('SeaWalker');p.gold=10000
        self.npc(p,'captain');origin=(p.x,p.y)
        await self.command(ws,'travel',city_id='brzezina');self.assertEqual((p.x,p.y),origin)
        p.level=8;p.combat_until=self.clock()+20
        await self.command(ws,'travel',city_id='brzezina');self.assertEqual((p.x,p.y),origin)
        p.combat_until=0;p.gold=0
        await self.command(ws,'travel',city_id='brzezina');self.assertEqual((p.x,p.y),origin)
        p.gold=10000;await self.command(ws,'travel',city_id='brzezina')
        self.assertGreater(p.x,30000);self.assertIn('city_brzezina',p.discoveries);self.assertLess(p.gold,10000)
        old=(p.x,p.y,p.gold);self.place(p,p.x+800,p.y)
        await self.command(ws,'travel',city_id='przystan');self.assertEqual(p.gold,old[2]);self.assertGreater(p.x,30000)

    async def test_runes_consume_resources_cannot_hit_other_floor_and_train(self):
        ws,p,_=await self.connect('RuneMage',class_id='mage');self.place(p,1000,2010,level=60)
        before=p.mana;await self.command(ws,'rune_craft',rune_id='fire')
        self.assertEqual((p.runes['fire'],p.mana,p.soul),(1,before-70,96))
        await self.command(ws,'rune_craft',rune_id='fire');self.assertEqual(p.runes['fire'],1)
        self.clock.advance(4);e=self.enemy_fixture(p,'boss');e.floor=-1;hp=e.hp
        for other in self.game.nearby_enemies(p,650):
            if other.id!=e.id:other.alive=False
        await self.command(ws,'rune_use',rune_id='fire');self.assertEqual(p.runes['fire'],1);self.assertEqual(e.hp,hp)
        e.floor=0;await self.command(ws,'rune_use',rune_id='fire');self.assertEqual(p.runes['fire'],0);self.assertLess(e.hp,hp)
        self.clock.advance(4);self.npc(p,'merchant','brzezina');p.gold=100
        await self.command(ws,'rune_buy',rune_id='fire');self.assertEqual(p.gold,65);self.assertEqual(p.runes['fire'],1)
        self.assertGreater(p.skill_tries.get('magic',0),0)

    async def test_combat_skills_streaming_and_floor_privacy(self):
        ws,p,_=await self.connect('CombatTrainer');self.place(p,1200,1800,level=20)
        enemy=self.enemy_fixture(p,'boss',hp=100000)
        for _ in range(31):
            self.clock.advance(1)
            await self.command(ws,'attack')
            await asyncio.sleep(.04)
        self.assertGreaterEqual(skill_level(p,'melee'),11)
        for _ in range(30):self.game.damage_player(p,1)
        self.assertGreaterEqual(skill_level(p,'shielding'),11)
        ws2,p2,_=await self.connect('OtherFloor');p2.x,p2.y,p2.floor=p.x,p.y,-1
        hp=enemy.hp;await self.command(ws2,'attack');self.assertEqual(enemy.hp,hp)
        state=self.game.snapshot(p2)
        self.assertTrue(all(e['floor']==-1 for e in state['enemies']))
        self.assertLess(len(state['enemies']),100)
        own=next(q for q in state['players'] if q['id']==p.id)
        for key in ('depot','bank_gold','runes','skills','mastery'):self.assertNotIn(key,own)
        self.assertEqual(self.game.metadata()['width'],128000)

    async def test_advanced_potions_and_quest_unlock_are_authoritative(self):
        ws,p,_=await self.connect('Supplies')
        p.x,p.y,p.gold=680,1180,1000
        await self.command(ws,'buy',item='health_potion_3');self.assertNotIn('health_potion_3',p.potions)
        p.level=50;p.hp=p.max_hp-700
        await self.command(ws,'buy',item='health_potion_3');self.assertEqual(p.potions['health_potion_3'],1)
        hp=p.hp;await self.command(ws,'potion',item='health_potion_3');self.assertEqual(p.hp,hp+520)
        quest=next(q for q in core.QUESTS if q['id']=='hunt_19');npc=next(n for n in core.NPCS if n['id']==quest['npc_id'])
        self.place(p,npc['x'],npc['y'])
        await self.command(ws,'quest_accept',quest_id=quest['id']);self.assertNotIn(quest['id'],p.quest_progress)
        p.level=110;await self.command(ws,'quest_accept',quest_id=quest['id']);self.assertTrue(p.quest_progress[quest['id']]['accepted'])

    async def test_new_commands_reject_malformed_fields_and_remote_actions(self):
        ws,p,_=await self.connect('MaliciousInputs');before=p.save_data()
        for kind,field in [('cast','spell_id'),('rune_buy','rune_id'),('rune_craft','rune_id'),('travel','city_id'),('depot_store','uid'),('mastery','branch')]:
            for invalid in ([],{},None,True,123):
                await self.command(ws,kind,**{field:invalid})
                await asyncio.sleep(.04)
        self.assertEqual(p.gold,before['gold']);self.assertEqual(p.level,before['level']);self.assertFalse(p.promoted)
        await self.command(ws,'input',x=0,y=0,floor=-2,promoted=True,bank_gold=99999,mastery={'power':20})
        self.assertEqual((p.floor,p.bank_gold,p.promoted,p.mastery),(0,0,False,{}))
