"""0.8.5: shared AoE geometry, visual metadata, character sheet, 24 slots and adaptive F."""
import json
import math
from pathlib import Path
from types import SimpleNamespace as Point
import unittest
from aiohttp.test_utils import TestClient,TestServer
import test_dnd as base
from server import spell_geometry as geo, dnd_content as dnd, combat_rules as rules, character_sheet
from server.server import Player, create_app
ROOT=Path(__file__).resolve().parents[1]

class Geometry(unittest.TestCase):
    def setUp(self):self.p=Point(x=0,y=0,facing=[1,0]);self.e=Point(x=80,y=0)
    def area(self,key):return geo.build(dnd.SPELLS[key],self.p,self.e)
    def test_cone_is_triangular_not_padded_circle(self):
        a=self.area('burning_hands');self.assertEqual(a['polygons'],[[[0,0],[96,-48],[96,48]]])
        for x,y in ((1,0),(48,24),(96,48),(96,-48)):self.assertTrue(geo.contains(a,x,y))
        for x,y in ((-1,0),(97,0),(48,24.01),(20,15)):self.assertFalse(geo.contains(a,x,y))
    def test_cone_far_corners_not_dropped_by_radial_query(self):
        a=self.area('cone_of_cold');self.assertTrue(geo.contains(a,384,192));self.assertGreater(geo.query_radius(a,self.p),math.hypot(384,192))
    def test_cone_rotates_with_target(self):
        self.e.x=0;self.e.y=80;a=self.area('burning_hands')
        self.assertTrue(geo.contains(a,48,96));self.assertFalse(geo.contains(a,49,96));self.assertFalse(geo.contains(a,0,-1))
    def test_line_width_and_length_inclusive(self):
        a=self.area('lightning_bolt');self.assertEqual(a['width'],32)
        for p in ((0,0),(640,16),(20,-16)):self.assertTrue(geo.contains(a,*p))
        for p in ((-1,0),(641,0),(100,16.01)):self.assertFalse(geo.contains(a,*p))
    def test_entangle_square_not_circle(self):
        a=self.area('entangle');self.assertTrue(geo.contains(a,144,64));self.assertFalse(geo.contains(a,145,0));self.assertFalse(geo.contains(a,145,65))
    def test_fireball_circle_boundary(self):
        a=self.area('fireball');self.assertTrue(geo.contains(a,208,0));self.assertFalse(geo.contains(a,208.1,0));self.assertFalse(geo.contains(a,208,128))
    def test_fire_storm_ten_adjacent_cubes(self):
        a=self.area('fire_storm');self.assertEqual(len(a['polygons']),10)
        for polygon in a['polygons']:
            xs,ys=zip(*polygon);self.assertEqual(max(xs)-min(xs),64);self.assertEqual(max(ys)-min(ys),64)
        self.assertTrue(geo.contains(a,-80,-64));self.assertTrue(geo.contains(a,240,64));self.assertFalse(geo.contains(a,241,64))
    def test_four_meteor_centres_and_outside_bounds(self):
        a=self.area('meteor_swarm');self.assertEqual(len(a['circles']),4);self.assertEqual(len({tuple(c[:2]) for c in a['circles']}),4)
        for x,y,r in a['circles']:self.assertTrue(geo.contains(a,x,y));self.assertEqual(r,256)
        self.assertFalse(geo.contains(a,497,0));self.assertTrue(geo.contains(a,496,0))
    def test_same_position_target_uses_facing_not_nan(self):
        self.e.x=0;a=self.area('burning_hands');self.assertEqual(a['direction'],[1,0]);json.dumps(a,allow_nan=False)
    def test_catalogue_shapes_and_dimensions(self):
        for key in ('burning_hands','cone_of_cold'):self.assertEqual(dnd.SPELLS[key]['shape'],'cone')
        for key in ('lightning_bolt','sunbeam'):self.assertEqual(dnd.SPELLS[key]['shape'],'line')
        for key in ('moonbeam','spike_growth','fireball','ice_storm'):self.assertEqual(dnd.SPELLS[key]['shape'],'circle')
    def test_every_spell_has_local_original_art_in_both_clients(self):
        for key,s in dnd.SPELLS.items():
            self.assertEqual(s['id'],key);self.assertEqual(len(s['visual']['colors']),3)
            a=ROOT/'web'/s['icon'];b=ROOT/'client'/s['icon']
            self.assertTrue(a.is_file(),key);self.assertEqual(a.read_bytes(),b.read_bytes(),key)
            text=a.read_text();self.assertIn('<svg',text);self.assertNotIn('<script',text);self.assertNotIn('<image',text)
    def test_rays_and_missiles_have_distinct_visuals(self):
        self.assertEqual(dnd.SPELLS['magic_missile']['visual']['style'],'missiles');self.assertEqual(dnd.SPELLS['magic_missile']['shots'],3)
        self.assertEqual(dnd.SPELLS['ray_of_frost']['visual']['style'],'beam');self.assertEqual(dnd.SPELLS['ray_of_frost']['visual']['theme'],'cold')

class AdaptiveHotbar(unittest.TestCase):
    def player(self):
        p=Player('1','Mage',class_id='mage',level=1);dnd.sync_hotbar(p);return p
    def test_default_fallback_before_first_cast(self):self.assertEqual(dnd.favorite_spell(self.player()),dnd.CLASS_SPECS['mage']['default_ability'])
    def test_one_cast_changes_fallback(self):
        p=self.player();dnd.record_spell_use(p,'ray_of_frost');self.assertEqual(dnd.favorite_spell(p),'ray_of_frost')
    def test_actual_most_frequent_not_last_spell(self):
        p=self.player()
        for k in ['ray_of_frost']*4+['fire_bolt']*3:dnd.record_spell_use(p,k)
        self.assertEqual(dnd.favorite_spell(p),'ray_of_frost')
    def test_equal_counts_choose_most_recent(self):
        p=self.player()
        for k in ['ray_of_frost','fire_bolt','ray_of_frost','fire_bolt']:dnd.record_spell_use(p,k)
        self.assertEqual(dnd.favorite_spell(p),'fire_bolt')
    def test_window_bounded_and_adapts_to_new_style(self):
        p=self.player()
        for _ in range(150):dnd.record_spell_use(p,'ray_of_frost')
        for _ in range(51):dnd.record_spell_use(p,'fire_bolt')
        self.assertEqual(len(p.spell_history),100);self.assertEqual(dnd.favorite_spell(p),'fire_bolt')
    def test_bad_or_foreign_history_does_not_unlock_f(self):
        p=self.player();p.spell_history=['fireball',{},7,None,'cure_wounds','ray_of_frost'];dnd.sanitize_spell_history(p)
        self.assertEqual(p.spell_history,['ray_of_frost']);self.assertEqual(dnd.favorite_spell(p),'ray_of_frost')
    def test_history_wrong_type_cleared(self):
        p=self.player();p.spell_history={'spell':'ray_of_frost'};dnd.sanitize_spell_history(p);self.assertEqual(p.spell_history,[])
    def test_old_eight_slot_positions_preserved_during_expansion(self):
        p=self.player();p.hotbar=['magic_missile','ray_of_frost','','fire_bolt','','','','shield'];dnd.sync_hotbar(p)
        self.assertEqual(len(p.hotbar),24);self.assertEqual(p.hotbar[0],'magic_missile');self.assertEqual(p.hotbar[7],'shield')
        self.assertEqual(len([k for k in p.hotbar if k]),12)
    def test_all_level_available_spells_in_24_slot_banks(self):
        for cls in dnd.CLASS_SPECS:
            for level in (1,3,5,9,17,21):
                p=Player('1','Hero',class_id=cls,level=level);dnd.sync_hotbar(p)
                self.assertEqual(len(p.hotbar)%24,0);self.assertGreaterEqual(len(p.hotbar),24)
                self.assertEqual({k for k in p.hotbar if k},{k for k in dnd.SPELLS if dnd.spell_allowed(p,k)})

class LiveSpells(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp;tearDown=base.GameRules.tearDown
    player=base.GameRules.player;enemy=base.GameRules.enemy;account=base.GameRules.account
    async def test_f_uses_history_and_pays_actual_spell_cost(self):
        p=self.player('mage');dnd.record_spell_use(p,'magic_missile')
        before=self.e.hp;await self.g.ability(p,self.e.id)
        self.assertEqual(p.mana,20);self.assertEqual(self.e.hp,before-12);self.assertEqual(p.spell_history,['magic_missile']*2)
    async def test_failed_cast_does_not_enter_history(self):
        p=self.player('mage');p.mana=0;await self.g.cast_spell(p,'magic_missile',self.e.id)
        await self.g.cast_spell(p,'fireball',self.e.id);await self.g.cast_spell(p,'fire_bolt','no_such_enemy')
        self.assertEqual(p.spell_history,[])
    async def test_queued_cast_recorded_only_when_executed(self):
        p=self.player('mage');p.attack_cooldown_until=self.clock()+3
        await self.g.cast_spell(p,'ray_of_frost',self.e.id);self.assertEqual(p.spell_history,[])
        self.clock.advance(3.1);await self.g.process_player_actions()
        self.assertEqual(p.spell_history,['ray_of_frost'])
    async def test_shield_toggle_not_counted_actual_reaction_counted(self):
        p=self.player('mage');await self.g.cast_spell(p,'shield');self.assertEqual(p.spell_history,[])
        self.assertTrue(self.g.shield_blocks_missiles(p));self.assertEqual(p.spell_history,['shield'])
        self.assertTrue(self.g.shield_blocks_missiles(p));self.assertEqual(p.spell_history,['shield'])
    async def test_missile_damage_three_rolls_one_history_entry_one_visual(self):
        p=self.player('mage');await self.g.cast_spell(p,'magic_missile',self.e.id)
        events=[e for e in self.g.effects if e.get('spell_id')=='magic_missile']
        self.assertEqual(len(events),1);self.assertEqual(events[0]['shots'],3);self.assertEqual(len(p.combat_log),3);self.assertEqual(p.spell_history,['magic_missile'])
    async def test_ray_metadata_exact_target_and_cold_style(self):
        p=self.player('mage');await self.g.cast_spell(p,'ray_of_frost',self.e.id)
        effect=next(e for e in self.g.effects if e.get('spell_id')=='ray_of_frost')
        self.assertEqual((effect['target_x'],effect['target_y']),(self.e.x,self.e.y));self.assertEqual(effect['visual']['style'],'beam');self.assertIn('slow',self.e.conditions)
    async def test_burning_hands_geometry_excludes_old_padding(self):
        p=self.player('mage');self.e.x=p.x+70;self.e.y=p.y
        inside=self.enemy('inside',p.x+80,p.y+39);outside=self.enemy('outside',p.x+80,p.y+41)
        behind=self.enemy('behind',p.x-10,p.y);beyond=self.enemy('beyond',p.x+97,p.y)
        await self.g.cast_spell(p,'burning_hands',self.e.id)
        self.assertLess(inside.hp,999)
        for e in (outside,behind,beyond):self.assertEqual(e.hp,999)
        fx=next(e for e in self.g.effects if e.get('spell_id')=='burning_hands')
        for e in (self.e,inside,outside,behind,beyond):self.assertEqual(geo.contains(fx['area'],e.x,e.y),e.hp<999)
    async def test_lightning_can_hit_beyond_primary_inside_line_only(self):
        p=self.player('mage',5);inside=self.enemy('inside',p.x+300,p.y+15);outside=self.enemy('outside',p.x+300,p.y+17)
        await self.g.cast_spell(p,'lightning_bolt',self.e.id);self.assertLess(inside.hp,999);self.assertEqual(outside.hp,999)
    async def test_entangle_hits_square_corner_but_not_outside(self):
        p=self.player('druid');self.g.combat_rng=base.Dice(1,3)
        inside=self.enemy('inside',self.e.x+63,self.e.y+63);outside=self.enemy('outside',self.e.x+65,self.e.y+65)
        await self.g.cast_spell(p,'entangle',self.e.id);self.assertIn('restrained',inside.conditions);self.assertNotIn('restrained',outside.conditions)
    async def test_meteor_overlap_does_not_multiply_damage(self):
        p=self.player('mage',17);before=self.e.hp;await self.g.cast_spell(p,'meteor_swarm',self.e.id)
        self.assertEqual(before-self.e.hp,120);fx=next(e for e in self.g.effects if e.get('spell_id')=='meteor_swarm');self.assertEqual(len(fx['area']['circles']),4)
    async def test_field_visual_has_duration_and_ends_with_concentration(self):
        p=self.player('druid',3);await self.g.cast_spell(p,'moonbeam',self.e.id)
        self.assertTrue(self.g.spell_fields);field=self.g.spell_fields[0]
        fx=next(e for e in self.g.effects if e['id']==field['effect_id']);self.assertTrue(fx['persistent']);self.assertEqual(fx['duration'],dnd.SPELLS['moonbeam']['duration'])
        self.g.break_concentration(p);self.assertTrue(fx['ended']);self.assertNotIn(field['effect_id'],self.g.snapshot(p)['active_field_effects'])
    async def test_history_and_slot_24_persist(self):
        p=self.player('mage');self.account(p);await self.g.bind_spell(p,23,'ray_of_frost');await self.g.cast_spell(p,'ray_of_frost',self.e.id)
        saved=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?',(p.id,)).fetchone()[0]);q=self.g.load_player(p.id,p.name,p.ws,saved)
        self.assertEqual(q.hotbar[23],'ray_of_frost');self.assertEqual(q.spell_history,['ray_of_frost']);self.assertEqual(dnd.favorite_spell(q),'ray_of_frost')
    async def test_both_hotbar_rows_last_positions_accept_assignment(self):
        p=self.player('mage')
        for slot in (8,9,10,11,12,23):
            await self.g.bind_spell(p,slot,'magic_missile');self.assertEqual(p.hotbar[slot],'magic_missile')
    async def test_character_sheet_is_owner_only(self):
        p=self.player('mage');self.assertNotIn('character_sheet',p.public(self.clock(),private=False))
        info=p.public(self.clock(),private=True)['character_sheet'];self.assertEqual(info['spell_attack_bonus'],rules.spell_bonus(p));self.assertEqual(len(info['saving_throws']),6);self.assertEqual(len(info['resistances']),13)
    async def test_sheet_resistances_are_the_same_as_damage_rules(self):
        p=self.player('mage',9);p.buffs['stoneskin']={'until':self.clock()+60};p.buffs['resist_fire']={'until':self.clock()+60}
        data=character_sheet.build(p)
        for r in data['resistances']:
            self.assertEqual(r['multiplier'],rules.resistance_multiplier(p,r['type']))
        self.assertEqual({r['type'] for r in data['resistances'] if r['multiplier']==.5},{'fire','bludgeoning','piercing','slashing'})
    async def test_snapshot_contains_adaptive_spell_and_only_own_sheet(self):
        p=self.player('mage');q=self.player('druid',1,'2');dnd.record_spell_use(p,'ray_of_frost')
        snapshot=self.g.snapshot(p)
        own=next(x for x in snapshot['players'] if x['id']==p.id);other=next(x for x in snapshot['players'] if x['id']==q.id)
        self.assertEqual(own['favorite_spell'],'ray_of_frost');self.assertIn('character_sheet',own);self.assertNotIn('character_sheet',other);self.assertNotIn('spell_history',own)
    async def test_feats_not_fabricated(self):self.assertEqual(character_sheet.build(self.p)['feats'],[])
    async def test_expired_resistance_not_shown(self):
        self.p.buffs['stoneskin']={'until':self.clock()-1};self.assertTrue(all(r['multiplier']==1 for r in character_sheet.build(self.p)['resistances']))

class HTTPAssets(unittest.IsolatedAsyncioTestCase):
    async def test_character_and_vfx_assets_served_by_real_app(self):
        async with TestClient(TestServer(create_app(':memory:'))) as client:
            for path in ('/character_sheet.js','/character_sheet.css','/spell_vfx.js','/assets/spells/magic_missile.svg','/assets/spells/ray_of_frost.svg'):
                response=await client.get(path);self.assertEqual(response.status,200,path);self.assertGreater(len(await response.read()),40)
