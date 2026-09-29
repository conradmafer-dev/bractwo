"""Focused UI_19 expedition topology and official creature-trait regressions."""
import asyncio
from collections import deque
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

import test_dnd as base
from server.server import Game,Player,Enemy,ENEMY_TYPES,NPCS,QUESTS,LANDMARKS,OBSTACLES,ITEMS,POTIONS
from server import adventure_content as adventure,world_content as content,environment_rules as environment,dnd_content as dnd


class AdventureWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(':memory:',clock=base.Clock())
    @classmethod
    def tearDownClass(cls):cls.g.db.close()

    def test_content_references_and_unique_rewards(self):
        quests=[q for q in QUESTS if q.get('adventure')];npcs=[n for n in NPCS if n.get('adventure')]
        points=[p for p in LANDMARKS if p.get('adventure')]
        self.assertEqual((len(quests),len(npcs)),(18,12));self.assertGreaterEqual(len(points),30)
        ids={q['id'] for q in QUESTS};npc_ids={n['id'] for n in npcs};point_ids={p['id'] for p in points}
        rewards=[q['reward']['item'] for q in quests if q['reward'].get('item')]
        self.assertEqual(len(rewards),8);self.assertEqual(len(set(rewards)),8)
        self.assertEqual(len({n['dialogue']['greeting'] for n in npcs}),12)
        for q in quests:
            self.assertIn(q['npc_id'],npc_ids);self.assertTrue(set(q['requires'])<=ids)
            for o in q['objectives']:
                if o['type']=='discover':self.assertIn(o['target'],point_ids)
                else:self.assertGreaterEqual(sum(s[0]==o['target'] and s[3]==o['floor'] for s in content.SPAWNS),o['required'],q['id'])
        for rows in (QUESTS,NPCS,LANDMARKS,content.STAIRS):
            self.assertEqual(len({r['id'] for r in rows}),len(rows))

    def test_every_chamber_and_objective_is_reachable_inside_its_floor(self):
        """Flood-fill actual collision, not only overlapping decorative rectangles."""
        g=self.g;step=20
        areas=[a for a in [*content.DUNGEONS,*content.ELEVATIONS] if a.get('adventure')]
        self.assertEqual(len(areas),19)
        for area in areas:
            floor=area['floor'];x0=area['x'];y0=area['y']
            xmax=int(area['w']//step)+1;ymax=int(area['h']//step)+1
            def inside(x,y):return x0<=x<=x0+area['w'] and y0<=y<=y0+area['h']
            entrances=[s for s in content.STAIRS if s['to_floor']==floor and inside(s['to_x'],s['to_y'])]
            self.assertTrue(entrances,area['id']);entry=entrances[0]
            valid={}
            def free(ix,iy):
                if ix<0 or iy<0 or ix>xmax or iy>ymax:return False
                if (ix,iy) not in valid:valid[ix,iy]=not g.blocked(x0+ix*step,y0+iy*step,floor=floor)
                return valid[ix,iy]
            start=(round((entry['to_x']-x0)/step),round((entry['to_y']-y0)/step))
            self.assertTrue(free(*start),(area['id'],'start',start));seen={start};todo=deque([start])
            while todo:
                ix,iy=todo.popleft()
                for point in ((ix+1,iy),(ix-1,iy),(ix,iy+1),(ix,iy-1)):
                    if point not in seen and free(*point):seen.add(point);todo.append(point)
            targets=[(p['x'],p['y'],p['id']) for p in LANDMARKS if p.get('adventure') and p.get('floor',0)==floor and inside(p['x'],p['y'])]
            targets += [(s['x'],s['y'],s['id']) for s in content.STAIRS if s['floor']==floor and inside(s['x'],s['y'])]
            targets += [(s[1],s[2],s[0]) for s in content.SPAWNS if s[3]==floor and inside(s[1],s[2])]
            for x,y,label in targets:
                ix,iy=round((x-x0)/step),round((y-y0)/step)
                self.assertFalse(g.blocked(x,y,floor=floor),(area['id'],label,'blocked'))
                self.assertTrue(any((ix+dx,iy+dy) in seen for dx,dy in ((0,0),(-1,0),(1,0),(0,-1),(0,1))),(area['id'],label,'unreachable'))

    def test_monster_stat_blocks_and_svg_assets(self):
        root=Path(__file__).resolve().parents[1]
        for kind,source in adventure.MONSTERS.items():
            s=ENEMY_TYPES[kind]
            self.assertEqual((s['hp'],s['armor_class'],s['attack_bonus'],s['xp']),
                             (source['hp'],source['ac'],source['ab'],source['xp']))
            self.assertEqual(s['adventure_attacks'],source['attacks'])
            self.assertFalse(s['boss']);self.assertEqual(s['resistances'],[])
            for drop in s['loot']['entries']:
                self.assertIn(drop['template'],POTIONS if drop['kind']=='potion' else ITEMS)
                self.assertNotEqual(ITEMS.get(drop['template'],{}).get('slot'),'ring')
            image=ET.parse(root/'web'/s['sprite']).getroot()
            self.assertEqual((image.get('width'),image.get('height')),('320','80'))
            self.assertEqual(len(image),4)
        self.assertEqual(ENEMY_TYPES['adv_flying_sword']['saves']['dexterity'],4)
        self.assertEqual(ENEMY_TYPES['adv_ogre_zombie']['saves']['wisdom'],0)


class AdventureCombat(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.clock=base.Clock();cls.g=Game(':memory:',clock=cls.clock)
        for e in cls.g.enemies.values():e.alive=False
        cls.g.legacy_enemies=[]
    @classmethod
    def tearDownClass(cls):cls.g.db.close()
    def setUp(self):
        self.g.players.clear();self.g._adventure_grapples={};self.g.effects=[]
        self.g.combat_rng=base.Dice(20,3)
        self.p=Player('199','Próba',base.WS(),class_id='knight',level=95,x=8400,y=5600,floor=-10)
        self.g.starter(self.p);self.p.hp=self.p.max_hp;self.p.temp_hp=1000;self.p.current_wall_time=self.clock()
        self.g.players[self.p.id]=self.p
    def enemy(self,kind):
        e=Enemy('adv_test',kind,8424,5600,ENEMY_TYPES[kind]['hp'],8424,5600,floor=-10)
        e.current_wall_time=self.clock();self.g.enemies[e.id]=e;return e

    def test_multiattack_rolls_separately_and_damage_types_match(self):
        e=self.enemy('adv_animated_armor');checks=self.g.combat_rng.checks
        self.g.hit_player(e,self.p)
        self.assertEqual(self.g.combat_rng.checks-checks,2)
        attacks=[f for f in self.g.effects if f.get('kind')=='combat_roll' or f.get('action','').startswith('Ożywiona zbroja')]
        self.assertEqual(len([f for f in attacks if f.get('action','').endswith('Uderzenie')]),2)
        e=self.enemy('adv_giant_bat');result=self.g.hit_player(e,self.p)
        self.assertEqual(result['damage_type'],'piercing')

    async def test_grick_grapple_is_persistent_escapable_and_ends_out_of_reach(self):
        e=self.enemy('adv_grick');self.g.hit_player(e,self.p)
        self.assertIn('grappled',self.p.buffs);self.assertEqual(self.p.buffs['grappled']['dc'],12)
        self.assertTrue(dnd.spell_allowed(self.p,'escape_grapple'))
        self.g.tick_target_conditions(self.p);self.assertIn('grappled',self.p.buffs)
        self.assertEqual(self.p.speed,0)
        await self.g.cast_spell(self.p,'escape_grapple')
        self.assertNotIn('grappled',self.p.buffs)
        self.g._adventure_grapple(e,self.p,12);e.x+=100
        self.g.tick_dnd(.01);self.assertNotIn('grappled',self.p.buffs)

    def test_undead_fortitude_con_save_and_exceptions(self):
        e=self.enemy('adv_ogre_zombie');e.hp=5
        self.g.environment_damage_enemy(e,15,self.p)
        self.assertEqual(e.hp,1)
        for extra in ({'critical':True},{'damage_type':'radiant'},
                      {'components':[{'type':'bludgeoning','damage':14},{'type':'radiant','damage':1}]}):
            e.hp=5;checks=self.g.combat_rng.checks
            self.g.environment_damage_enemy(e,15,self.p,**extra)
            self.assertEqual(e.hp,0);self.assertEqual(self.g.combat_rng.checks,checks)
        e.hp=5;self.g.combat_rng=base.Dice(1,3);self.g.environment_damage_enemy(e,15,self.p)
        self.assertEqual(e.hp,0)
        # Exercise the real weapon-attack caller, which must forward critical.
        e.hp=5;self.g.combat_rng=base.Dice(20,3)
        hit=self.g.hit_enemy(self.p,e,dice=(1,6,0),melee=True,damage_kind='slashing')
        self.assertTrue(hit['critical']);self.assertEqual(e.hp,0)

    def test_poison_condition_immunity_and_flight_speed(self):
        for kind in ('adv_animated_armor','adv_flying_sword','adv_gargoyle','adv_ogre_zombie'):
            e=self.enemy(kind)
            self.assertFalse(self.g.apply_status(self.p,e,'poisoned',30,{'id':'poison'}))
            self.assertFalse(self.g.apply_status(self.p,e,'stinking_poison',30,{'id':'stinking_cloud'}))
            hp=e.hp;self.g.environment_damage_enemy(e,20,self.p,damage_type='poison');self.assertEqual(e.hp,hp)
        bat=self.enemy('adv_giant_bat');self.assertTrue(environment.flying(bat))
        self.assertAlmostEqual(environment.movement_speed(bat,ENEMY_TYPES[bat.kind]['speed']),200)


if __name__=='__main__':unittest.main()
