"""0.8.8 authoritative loot, balance invariants, equipment, saves, new habitats and HTTP assets."""
import json
from pathlib import Path
import random
import sys
import unittest
import xml.etree.ElementTree as ET
from collections import Counter
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from aiohttp.test_utils import TestClient, TestServer
from server.server import Game,Player,Enemy,ITEMS,ENEMY_TYPES,POTIONS,make_item,create_app,content,INVENTORY_CAP
from server import loot_content as loot,loot_tables,hunt_content as hunts,combat_rules as rules

class WS:
    closed=False
    def __init__(self):self.messages=[]
    async def send_json(self,d):self.messages.append(d)
    async def close(self):self.closed=True
class Clock:
    def __call__(self):return 1000.
class Dice:
    def __init__(self,crit=False):self.crit=crit
    def randint(self,a,b):return (20 if self.crit else 10) if b==20 else min(b,3)
class Fixed:
    def __init__(self,n):self.n=n
    def random(self):return self.n

def wear(p,key):
    item=make_item(key);p.inventory.append(item);p.equipment[item['slot']]=item['uid'];return item

def player(cls='knight',level=100):
    p=Player('1','Tester',WS(),class_id=cls,level=level,x=1100,y=1180)
    p.current_wall_time=1000.;p.hp=p.max_hp;p.mana=p.max_mana;return p

class Catalog(unittest.TestCase):
    def test_count_and_equipment_types(self):
        self.assertEqual(Counter(i['slot'] for i in ITEMS.values() if i.get('content_version')=='0.8.8'),{'weapon':30,'armor':23,'ring':6,'trophy':20})
    def test_every_monster_has_one_named_table(self):
        self.assertEqual(set(loot.DROPS),set(ENEMY_TYPES));self.assertEqual(len(ENEMY_TYPES),57)
        for k,s in ENEMY_TYPES.items():
            with self.subTest(k=k):
                self.assertTrue(s['loot']['independent']);self.assertIn('entries',s['loot'])
                self.assertEqual(s['loot']['equipment_chance'],0);self.assertEqual(s['loot']['unique_chance'],0)
    def test_valid_probabilities_and_templates(self):
        for k,s in ENEMY_TYPES.items():
            seen=set()
            for e in s['loot']['entries']:
                with self.subTest(k=k,e=e):
                    self.assertGreater(e['chance'],0);self.assertLessEqual(e['chance'],1)
                    self.assertIn(e['template'],POTIONS if e['kind']=='potion' else ITEMS)
                    self.assertNotIn(e['template'],seen);seen.add(e['template'])
    def test_loot_sources_match_authoritative_tables(self):
        for key,item in ITEMS.items():
            expected={k:e['chance'] for k,s in ENEMY_TYPES.items() for e in s['loot']['entries'] if e['kind']=='item' and e['template']==key}
            self.assertEqual({s['kind']:s['chance'] for s in item.get('sources',[])},expected,key)
    def test_every_new_equippable_item_has_source(self):
        for k,s in ITEMS.items():
            if s.get('content_version')=='0.8.8':self.assertTrue(s.get('sources'),k)
    def test_equipment_levels_do_not_exceed_source_level(self):
        for k,drops in loot.DROPS.items():
            for key,_ in drops:self.assertLessEqual(ITEMS[key]['min_level'],ENEMY_TYPES[k]['level'],(k,key))
    def test_no_legendary_items_on_weak_monsters(self):
        for k,ls in loot.DROPS.items():
            for key,chance in ls:
                if ITEMS[key].get('enchantment',0)==3:
                    self.assertGreaterEqual(ENEMY_TYPES[k]['level'],120)
                    self.assertLessEqual(chance,9)
    def test_beasts_do_not_drop_weapons_and_potions(self):
        for k in loot.NO_POTIONS:
            for e in ENEMY_TYPES[k]['loot']['entries']:
                self.assertEqual(e['kind'],'item');self.assertEqual(ITEMS[e['template']]['slot'],'trophy',(k,e))
    def test_boss_gear_not_guaranteed_but_trophy_guaranteed(self):
        for k,s in ENEMY_TYPES.items():
            if not s.get('boss'):continue
            for e in s['loot']['entries']:
                if e['kind']=='item':self.assertEqual(e['chance']==1,ITEMS[e['template']]['slot']=='trophy',(k,e))
    def test_no_class_dependent_replacement(self):
        for k,s in ENEMY_TYPES.items():
            rolls=[loot_tables.roll(c,s,random.Random(792)) for c in ('knight','ranger','druid','mage')]
            self.assertEqual(rolls,[rolls[0]]*4,k)
    def test_exact_probability_boundaries(self):
        for kind,key,chance in [('mummy','mummy_wand',.05),('skeleton_archer','crypt_bow',.015),('bandit','bandit_sabre',.03)]:
            spec=ENEMY_TYPES[kind]
            self.assertIn(('item',key),loot_tables.roll('knight',spec,Fixed(chance-.00001)))
            self.assertNotIn(('item',key),loot_tables.roll('knight',spec,Fixed(chance)))
    def test_independent_rolls_can_return_multiple_items(self):
        spec=ENEMY_TYPES['mummy'];drops=loot_tables.roll('ranger',spec,Fixed(0))
        self.assertEqual(len(drops),len(spec['loot']['entries']))
    def test_zero_drops_is_possible(self):
        self.assertEqual(loot_tables.roll('mage',ENEMY_TYPES['mummy'],Fixed(.9999)),[])
    def test_seeded_drop_frequencies(self):
        for kind,key,rate in [('mummy','mummy_wand',.05),('skeleton_archer','crypt_bow',.015),('bandit','bandit_sabre',.03),('bandit_captain','captain_greatsword',.18)]:
            rng=random.Random(8807);n=80000
            count=sum(('item',key) in loot_tables.roll('mage',ENEMY_TYPES[kind],rng) for _ in range(n))
            self.assertLess(abs(count/n-rate),.006,(kind,count/n))
    def test_original_sprite_assets_same_in_both_clients(self):
        for k in hunts.NEW_KINDS+['mummy','skeleton_archer']:
            s=ENEMY_TYPES[k];path=ROOT/'web'/s['sprite'];self.assertTrue(path.exists())
            self.assertEqual(path.read_bytes(),(ROOT/'client'/s['sprite']).read_bytes())
            # PNG IHDR has exact four-frame dimensions; no imaging dependency for game tests.
            data=path.read_bytes();self.assertEqual(data[:8],b'\x89PNG\r\n\x1a\n')
            self.assertEqual(int.from_bytes(data[16:20],'big'),320);self.assertEqual(int.from_bytes(data[20:24],'big'),80)
    def test_new_icons_are_valid_svg_and_client_mirrors(self):
        for k,i in ITEMS.items():
            if i.get('content_version')!='0.8.8':continue
            b=(ROOT/'web'/i['icon']).read_bytes();self.assertEqual(ET.fromstring(b).tag,'{http://www.w3.org/2000/svg}svg')
            self.assertEqual(b,(ROOT/'client'/i['icon']).read_bytes(),k)
    def test_specific_percentages_requested_by_player(self):
        for k,item,chance in [('mummy','mummy_wand',5),('skeleton_archer','skeleton_shortbow',7),('bandit','bandit_sabre',3)]:
            self.assertIn((item,chance),loot.DROPS[k])

class Equipment(unittest.TestCase):
    def test_light_armor_all_dexterity(self):
        p=player('ranger');wear(p,'bandit_leather');self.assertEqual(rules.armor_class(p),16)
    def test_medium_armor_caps_dexterity(self):
        p=player('ranger');wear(p,'orc_scale');self.assertEqual(rules.armor_class(p),16)
    def test_heavy_armor_ignores_dexterity(self):
        p=player();wear(p,'dwarf_plate');self.assertEqual(rules.armor_class(p),18)
    def test_enchanted_armor_and_ring_bonuses(self):
        p=player();wear(p,'obsidian_plate');wear(p,'captain_ring');self.assertEqual(rules.armor_class(p),21)
    def test_mage_armor_works_with_enchanted_robes(self):
        p=player('mage');wear(p,'mummy_robe');p.buffs['mage_armor']={'until':1100}
        self.assertEqual(rules.armor_class(p),13+rules.ability_modifier(p,'dexterity')+1)
    def test_real_two_hand_damage_and_enchantment(self):
        p=player(level=20);wear(p,'captain_greatsword');self.assertEqual(rules.weapon_dice(p),(2,6,5))
    def test_enchantment_added_only_once(self):
        p=player(level=8);wear(p,'bandit_sabre');self.assertEqual(rules.weapon_dice(p),(1,8,4))
    def test_critical_new_weapon_doubles_dice_only(self):
        p=player(level=20);wear(p,'captain_greatsword');r=rules.roll_attack(Dice(True),10,10,rules.weapon_dice(p))
        self.assertEqual(r['damage_rolls'],[3,3,3,3]);self.assertEqual(r['damage'],17)
    def test_hammer_bludgeoning(self):
        p=player();wear(p,'dwarf_hammer');self.assertEqual(rules.damage_type(p),'bludgeoning')
    def test_all_new_wands_keep_weak_spark(self):
        for k,i in loot.NEW_ITEMS.items():
            if i.get('class_ids')==['mage'] and i['slot']=='weapon':
                p=player('mage',150);base=rules.spell_bonus(p);wear(p,k)
                self.assertEqual(rules.weapon_dice(p),(1,4,0));self.assertEqual(rules.spell_bonus(p)-base,i['enchantment'])
    def test_druid_enchantment_remains_in_shillelagh(self):
        p=player('druid',20);wear(p,'thorn_staff');p.buffs['shillelagh']={'until':1100}
        self.assertEqual(rules.weapon_dice(p),(1,10,rules.ability_modifier(p,'wisdom')+1))
    def test_elemental_resistance_and_nonstacking(self):
        p=player('ranger');wear(p,'dragon_scale');wear(p,'ember_ring');p.buffs['resist_fire']={'until':1100}
        self.assertEqual(rules.resistance_multiplier(p,'fire'),.5);self.assertEqual(rules.resistance_multiplier(p,'cold'),1)
    def test_form_does_not_retain_worn_item_resistance(self):
        p=player('druid');wear(p,'winter_ring');p.form='bear'
        self.assertEqual(rules.resistance_multiplier(p,'cold'),1)

class GameIntegration(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.g=Game(':memory:',clock=Clock());self.g.combat_rng=Dice();self.p=player(level=20);self.g.players[self.p.id]=self.p
        for e in self.g.enemies.values():e.alive=False;e.respawn_at=0
        self.g.legacy_enemies=[]
    def tearDown(self):self.g.db.close()
    def account(self,p):
        self.g.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',(int(p.id),p.name,p.name.lower(),b'salt',b'hash',json.dumps(p.save_data())))
        self.g.db.commit()
    async def test_untrained_heavy_armor_can_be_worn_but_prevents_magic(self):
        p=player('mage');i=make_item('dwarf_plate');p.inventory.append(i)
        await self.g.inventory_command(p,'equip',{'uid':i['uid']});self.assertEqual(p.equipment.get('armor'),i['uid']);self.assertTrue(rules.gear.armor_penalty(p))
    async def test_server_rejects_trophy_equipping(self):
        i=make_item('loot_trophy_rat');self.p.inventory.append(i)
        await self.g.inventory_command(self.p,'equip',{'uid':i['uid']});self.assertNotIn(i['uid'],self.p.equipment.values())
    async def test_server_rejects_underlevel_equipment(self):
        i=make_item('obsidian_greatsword');self.p.inventory.append(i)
        await self.g.inventory_command(self.p,'equip',{'uid':i['uid']});self.assertNotEqual(self.p.equipment.get('weapon'),i['uid'])
    async def test_server_equips_allowed_medium_armor(self):
        p=player('druid');i=make_item('root_breastplate');p.inventory.append(i)
        await self.g.inventory_command(p,'equip',{'uid':i['uid']});self.assertEqual(p.equipment.get('armor'),i['uid'])
    async def test_actual_attack_uses_two_d6(self):
        self.p.level=12;wear(self.p,'veteran_greatsword');e=Enemy('test','ogre',1170,1180,999,1170,1180)
        self.g.enemies[e.id]=e;self.g.legacy_enemies.append(e)
        await self.g.attack(self.p,enemy_id=e.id)
        self.assertEqual(e.hp,990);self.assertEqual(self.p.last_roll['damage_dice'],'2k6+3')
    async def test_monster_damage_obeys_item_resistance(self):
        self.p.level=100;self.p.hp=self.p.max_hp;wear(self.p,'winter_ring');before=self.p.hp
        self.g.damage_player(self.p,11,rolled=True,damage_type='cold');self.assertEqual(before-self.p.hp,5)
    async def test_pvp_damage_obeys_same_resistance(self):
        self.p.level=100;self.p.hp=self.p.max_hp;wear(self.p,'winter_ring');before=self.p.hp
        self.g.damage_player(self.p,11,killer=player('mage'),rolled=True,damage_type='cold');self.assertEqual(before-self.p.hp,5)
    async def test_mixed_damage_resisted_separately(self):
        self.p.hp=self.p.max_hp;wear(self.p,'winter_ring');before=self.p.hp
        self.g.damage_player(self.p,22,rolled=True,damage_components=[{'damage':11,'type':'cold'},{'damage':11,'type':'bludgeoning'}])
        self.assertEqual(before-self.p.hp,16)
    async def test_actual_kill_grants_own_table_and_not_twice(self):
        self.account(self.p);self.g.rng=Fixed(0)
        e=Enemy('loot_mummy','mummy',1170,1180,1,1170,1180);e.contributors={self.p.id:self.g.time}
        self.g.enemies[e.id]=e
        await self.g.defeat(e);self.assertIn('mummy_wand',[i['template'] for i in self.p.inventory])
        self.assertEqual(self.p.kills,1);items=len(self.p.inventory)
        await self.g.defeat(e);self.assertEqual(len(self.p.inventory),items);self.assertEqual(self.p.kills,1)
    async def test_necromantic_projectile_respects_tomb_robe(self):
        p=player('mage',100);p.shield_armed=False;wear(p,'hierophant_robe');self.g.players[p.id]=p
        e=Enemy('acolyte_bolt','grave_acolyte',1170,1180,45,1170,1180);self.g.enemies[e.id]=e
        before=p.hp;self.g.queue_enemy_attack(e,p,projectile='shadow')
        self.g.time=self.g.hazards[-1]['resolve']+.01;self.g.resolve_hazards()
        self.assertEqual(before-p.hp,2) # (1d8 roll 3 + 2), halved once and rounded down

    async def test_full_bag_reports_overflow_and_never_equips(self):
        self.g.starter(self.p) # Complete legacy supply migration before filling the bag.
        self.p.inventory=[make_item('loot_trophy_rat') for _ in range(INVENTORY_CAP)]
        text=self.g.grant_loot(self.p,[('item','mummy_wand')])
        self.assertEqual(len(self.p.inventory),INVENTORY_CAP);self.assertIn('Brak miejsca',text)
    async def test_saved_new_items_and_depot_refresh_keep_uids(self):
        i=wear(self.p,'captain_greatsword');d=make_item('mummy_wand');self.p.depot.append(d)
        saved=self.p.save_data();saved['inventory'][0]['attack']=999
        loaded=self.g.load_player(self.p.id,self.p.name,WS(),saved)
        self.assertEqual(loaded.equipment['weapon'],i['uid']);self.assertEqual(loaded.inventory[0]['attack'],1)
        self.assertEqual(loaded.depot[0]['uid'],d['uid']);self.assertEqual(loaded.depot[0]['sources'],ITEMS['mummy_wand']['sources'])
    async def test_old_gear_not_removed_or_unequipped(self):
        self.g.starter(self.p);saved=self.p.save_data();old=Counter(i['template'] for i in self.p.inventory);eq=self.p.equipment.copy()
        loaded=self.g.load_player(self.p.id,self.p.name,WS(),saved)
        self.assertEqual(Counter(i['template'] for i in loaded.inventory),old);self.assertEqual(loaded.equipment,eq)
    async def test_all_new_spawns_safe_and_walkable(self):
        new=[s for s in content.SPAWNS if s[0] in hunts.NEW_KINDS];self.assertEqual(len(new),126)
        self.assertEqual({x[0] for x in new},set(hunts.NEW_KINDS))
        for k,x,y,z in new:
            self.assertEqual(z,0);self.assertFalse(self.g.blocked(x,y,floor=z),(k,x,y));self.assertFalse(self.g.in_safe(player_at(x,y)),(k,x,y))
    async def test_exactly_two_new_bosses_have_single_spawn(self):
        counts=Counter(k for k,x,y,z in content.SPAWNS)
        self.assertEqual({k for k in hunts.NEW_KINDS if ENEMY_TYPES[k]['boss']},hunts.BOSSES)
        for k in hunts.BOSSES:self.assertEqual(counts[k],1)
    async def test_hunts_exposed_and_landmarks_present(self):
        self.assertEqual(len(content.LOOT_HUNTS),9)
        for h in content.LOOT_HUNTS:
            self.assertIn(h['kind'],hunts.NEW_KINDS);self.assertTrue(h['region']);self.assertGreater(h['count'],0)


def player_at(x,y):
    p=player();p.x=x;p.y=y;return p

class HTTPAssets(unittest.IsolatedAsyncioTestCase):
    async def test_health_new_assets_and_route_registration(self):
        async with TestClient(TestServer(create_app(':memory:'))) as c:
            r=await c.get('/health');self.assertEqual((await r.json())['version'],'0.8.17')
            paths=['/loot_ui.js','/loot_ui.css','/game.js']+[ '/'+i['icon'] for i in ITEMS.values() if i.get('content_version')=='0.8.8']+['/'+ENEMY_TYPES[k]['sprite'] for k in hunts.NEW_KINDS]
            for path in paths:
                r=await c.get(path);self.assertEqual(r.status,200,path);self.assertGreater(len(await r.read()),20,path)
            r=await c.get('/');html=await r.text();self.assertIn('loot_ui.js',html);self.assertIn('targetLoot',html)

if __name__=='__main__':unittest.main()
