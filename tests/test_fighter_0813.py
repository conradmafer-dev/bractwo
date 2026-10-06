"""0.8.13 authoritative warrior regressions; no external services."""
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import test_dnd as base
from server.server import Player, make_item, ITEMS, CLASSES, create_app
from server import combat_rules as rules, dnd_content as dnd, fighter_rules as fighter, spell_scaling, character_sheet, level_up
from aiohttp.test_utils import TestClient, TestServer

class FighterData(unittest.TestCase):
    def test_knight_and_ranger_have_class_style_sheets(self):
        for cls in CLASSES:
            f=character_sheet.build(Player('1','T',class_id=cls))['fighter']
            self.assertEqual(bool(f),cls in ('knight','ranger'))
    def test_three_choice_styles_and_three_distinct_masteries(self):
        self.assertEqual(set(fighter.STYLES),{'dueling','defense','great_weapon'})
        self.assertEqual({m['effect'] for m in fighter.MASTERIES.values()},{'sap','graze','topple'})
    def test_second_wind_free_and_sixty_seconds(self):
        for lv in (1,2,5,20,21):
            p=Player('1','T',level=lv);s=spell_scaling.resolve(p,'second_wind')
            self.assertEqual((s['mana'],s['cooldown'],s['action']),(0,60,'bonus'))
            self.assertEqual(s['dice'],[1,10,min(20,lv)])
    def test_surge_only_knight_at_five(self):
        for cls in CLASSES:
            for lv in (1,2,5,20,21):
                p=Player('1','T',class_id=cls,level=lv)
                self.assertEqual(dnd.spell_allowed(p,'action_surge'),cls=='knight' and lv>=2)
    def test_surge_is_free_not_a_spell_circle(self):
        s=spell_scaling.resolve(Player('1','T',level=2),'action_surge')
        self.assertEqual((s['mana'],s['cooldown'],s['action'],s['circle']),(0,90,'extra',0))
        self.assertTrue(s['feature'])
    def test_receipt_level_two_surge_and_second_wind_increment(self):
        p=Player('1','T',level=2);level_up.record(p,2,2)
        rows=level_up.pending(p)['pending_level_ups'][0]['rows']
        self.assertTrue(any('Zryw akcji' in str(x) for x in rows),rows)
        self.assertTrue(any(x.get('label')=='Drugi oddech' and x.get('gain')=='+1' for x in rows),rows)
    def test_original_icons_and_same_assets_in_both_clients(self):
        root=Path(__file__).resolve().parents[1]
        paths=[s['icon'] for s in fighter.STYLES.values()]+[s['icon'] for s in fighter.MASTERIES.values()]+[dnd.SPELLS['action_surge']['icon']]+[ITEMS[k]['icon'] for k in ('fighter_chain_mail','fighter_shield','training_greatsword','training_maul')]
        self.assertEqual(len(set(paths)),11)
        for path in paths:
            a=root/'web'/path;b=root/'client'/path
            self.assertTrue(a.is_file(),path);self.assertEqual(a.read_bytes(),b.read_bytes())
    def test_old_magic_weapons_keep_exact_magic_bonus(self):
        for k,b in [('knight_weapon_1',0),('knight_weapon_2',1),('knight_weapon_3',2)]:
            self.assertEqual(ITEMS[k]['attack_bonus'],b);self.assertEqual(ITEMS[k]['attack'],b)
            self.assertEqual(ITEMS[k]['weapon_type'],'longsword')
    def test_new_items_are_buyable_but_not_invented_loot(self):
        for k in ('fighter_chain_mail','fighter_shield','training_greatsword','training_maul'):
            self.assertGreater(ITEMS[k]['price'],0);self.assertEqual(set(ITEMS[k]['class_ids']),{'knight','mage','druid','ranger'});self.assertEqual(ITEMS[k]['min_level'],1)

class FighterGame(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    enemy=base.GameRules.enemy
    account=base.GameRules.account
    def advance(self,n=3.1):
        self.clock.advance(n);self.g.time+=n
        for p in self.g.players.values():p.current_wall_time=self.clock()
    def wear(self,key,slot='weapon'):
        i=make_item(key);self.p.inventory.append(i);self.p.equipment[slot]=i['uid'];return i
    def master(self):
        from server.world_content import NPCS
        n=next(x for x in NPCS if x.get('service')=='master');self.p.x=n['x'];self.p.y=n['y'];self.p.floor=n.get('floor',0)
        return n
    def pvp(self):
        self.e.alive=False;self.p.level=5;self.p.hp=self.p.max_hp;self.p.pvp_safety=False
        q=self.player('knight',5,'2');q.x=self.p.x+70;q.hp=q.max_hp;q.pvp_safety=False
        return q
    def test_starter_chain_shield_real_ac18(self):
        self.assertEqual(self.p.armor_class,18)
        self.assertEqual(rules.weapon_dice(self.p),(1,8,3))
        self.assertTrue(self.p.equipment['shield']);self.assertEqual(len({i['uid'] for i in self.p.inventory}),len(self.p.inventory))
    def test_other_classes_get_no_free_warrior_gear(self):
        for c in ('mage','druid','ranger'):
            p=self.player(c,pid=c)
            self.assertFalse(any(i['template'].startswith('fighter_') for i in p.inventory));self.assertEqual(p.equipment['shield'],'')
    def test_migration_does_not_duplicate_or_replace_existing_magic_armor(self):
        self.p.inventory=[i for i in self.p.inventory if not i['template'].startswith('fighter_')];self.p.equipment['shield']=''
        heavy=next(k for k,v in ITEMS.items() if v.get('slot')=='armor' and v.get('armor_kind')=='heavy' and v.get('ac_bonus',0)>0)
        old=self.wear(heavy,'armor');self.p.fighter_rules_version=0
        for _ in range(3):self.g.migrate_fighter(self.p,make_item)
        self.assertEqual(self.p.equipment['armor'],old['uid'])
        for key in ('fighter_chain_mail','fighter_shield'):self.assertEqual(sum(i['template']==key for i in self.p.inventory),1)
    def test_migration_overfull_bag_loses_nothing(self):
        self.p.inventory=[make_item('cloth') for _ in range(40)];self.p.equipment={'weapon':'','armor':'','ring':''};self.p.fighter_rules_version=0
        old={i['uid'] for i in self.p.inventory};self.g.migrate_fighter(self.p,make_item)
        self.assertEqual(len(self.p.inventory),42);self.assertTrue(old.issubset({i['uid'] for i in self.p.inventory}))
    async def test_choice_is_one_separate_from_points(self):
        points=dict(self.p.mastery);self.assertFalse(self.p.fighting_style)
        await self.g.select_fighting_style(self.p,'dueling')
        self.assertEqual(self.p.fighting_style,'dueling');self.assertEqual(self.p.mastery,points);self.assertEqual(rules.weapon_dice(self.p),(1,8,5))
    async def test_repeat_and_unknown_choices_cannot_stack(self):
        for key in ('dueling','dueling',{},None,'fake'):
            await self.g.select_fighting_style(self.p,key)
        self.assertEqual(self.p.fighting_style,'dueling');self.assertEqual(rules.weapon_dice(self.p),(1,8,5))
    async def test_changing_style_requires_master_and_no_combat(self):
        await self.g.select_fighting_style(self.p,'dueling')
        await self.g.select_fighting_style(self.p,'defense');self.assertEqual(self.p.fighting_style,'dueling')
        self.master();self.p.combat_until=self.clock()+10
        await self.g.select_fighting_style(self.p,'defense');self.assertEqual(self.p.fighting_style,'dueling')
        self.advance(11);gold=self.p.gold
        await self.g.select_fighting_style(self.p,'defense');self.assertEqual(self.p.fighting_style,'defense');self.assertEqual(self.p.gold,gold);self.assertEqual(self.p.armor_class,19)
    async def test_dead_or_wrong_class_cannot_choose(self):
        self.p.hp=0;await self.g.select_fighting_style(self.p,'dueling');self.assertFalse(self.p.fighting_style)
        for cls in ('ranger','mage','druid'):
            p=self.player(cls,pid=cls);await self.g.select_fighting_style(p,'dueling');self.assertFalse(p.fighting_style)
    async def test_choice_and_gear_survive_save_load(self):
        await self.g.select_fighting_style(self.p,'defense');self.account(self.p)
        data=json.loads(json.dumps(self.p.save_data()));q=self.g.load_player(self.p.id,self.p.name,base.WS(),data)
        self.assertEqual(q.fighting_style,'defense');self.assertEqual(q.armor_class,19)
        self.assertEqual({i['uid'] for i in q.inventory},{i['uid'] for i in self.p.inventory})
    def test_defense_needs_armor_not_cloth(self):
        self.p.fighting_style='defense';self.wear('cloth','armor')
        self.assertFalse(fighter.style_active(self.p));self.assertEqual(self.p.armor_class,13)
    def test_form_disables_shield_and_styles(self):
        self.p.fighting_style='defense';self.p.form='wolf'
        self.assertEqual(fighter.shield_bonus(self.p),0);self.assertFalse(fighter.style_active(self.p));self.assertEqual(self.p.armor_class,12)
    async def test_twohand_equip_stows_shield_not_destroy(self):
        i=make_item('training_greatsword');self.p.inventory.append(i);shield=self.p.equipment['shield']
        self.p.fighting_style='dueling';await self.g.on_packet(self.p.ws,{'type':'equip','uid':i['uid']})
        self.assertEqual(self.p.equipment['weapon'],i['uid']);self.assertEqual(self.p.equipment['shield'],'');self.assertTrue(any(i['uid']==shield for i in self.p.inventory))
        self.assertEqual(self.p.fighting_style,'dueling');self.assertFalse(fighter.style_active(self.p));self.assertEqual(self.p.armor_class,16)
        await self.g.on_packet(self.p.ws,{'type':'equip','uid':shield});self.assertEqual(self.p.equipment['shield'],'')
    async def test_versatile_grip_is_true_d10_no_shield(self):
        self.p.fighting_style='great_weapon';await self.g.set_weapon_grip(self.p,'two')
        self.assertEqual(rules.weapon_dice(self.p),(1,10,3));self.assertTrue(fighter.style_active(self.p));self.assertEqual(self.p.armor_class,16)
        await self.g.set_weapon_grip(self.p,'one');self.assertEqual(rules.weapon_dice(self.p),(1,8,3));self.assertFalse(fighter.style_active(self.p))
    async def test_grip_locked_in_combat(self):
        self.p.combat_until=self.clock()+10;before=self.p.equipment['shield'];await self.g.set_weapon_grip(self.p,'two')
        self.assertEqual(self.p.weapon_grip,'one');self.assertEqual(self.p.equipment['shield'],before)
    async def test_great_weapon_floor_actual_rolls_not_flat_bonus(self):
        self.p.fighting_style='great_weapon';self.wear('training_greatsword');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(10,1)
        r=self.g.hit_enemy(self.p,self.e,melee=True)
        self.assertEqual(r['raw_damage_rolls'],[1,1]);self.assertEqual(r['damage_rolls'],[3,3]);self.assertEqual(r['damage'],9)
    async def test_great_weapon_critical_floors_each_weapon_die(self):
        self.p.fighting_style='great_weapon';self.wear('training_greatsword');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(20,2)
        r=self.g.hit_enemy(self.p,self.e,melee=True);self.assertEqual(r['damage_rolls'],[3]*4);self.assertEqual(r['damage'],15)
    def test_great_weapon_never_changes_spell_dice(self):
        self.p.fighting_style='great_weapon';self.wear('training_greatsword');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(20,1)
        r=self.g.hit_enemy(self.p,self.e,spell=True,dice=(1,6,0),melee=True)
        self.assertEqual(r['damage_rolls'],[1,1]);self.assertNotIn('raw_damage_rolls',r)
    async def test_sap_is_once_only_and_does_not_spend_any_resource(self):
        mana=self.p.mana;await self.g.attack(self.p,enemy_id=self.e.id)
        self.assertIn('sap',self.e.conditions);self.assertEqual(self.p.mana,mana)
        r=self.g.hit_player(self.e,self.p);self.assertTrue(r['disadvantage']);self.assertEqual(len(r['rolls']),2)
        r=self.g.hit_player(self.e,self.p);self.assertFalse(r['disadvantage'])
    async def test_sap_expires_after_next_round(self):
        await self.g.attack(self.p,enemy_id=self.e.id);self.advance(3.1)
        self.assertFalse(self.g.hit_player(self.e,self.p)['disadvantage'])
    async def test_sap_not_consumed_by_save_based_attack(self):
        await self.g.attack(self.p,enemy_id=self.e.id)
        self.g.hit_player(self.e,self.p,area=True)
        self.assertIn('sap',self.e.conditions)
    def test_graze_miss_damage_has_no_magic_or_style_bonuses(self):
        self.wear('training_greatsword');self.p.equipment['shield']='';self.p.fighting_style='great_weapon';self.g.combat_rng=base.Dice(1,6)
        before=self.e.hp;r=self.g.hit_enemy(self.p,self.e,melee=True)
        self.assertFalse(r['hit']);self.assertTrue(r['graze']);self.assertEqual(r['damage'],3);self.assertEqual(before-self.e.hp,3);self.assertEqual(r['damage_rolls'],[])
    async def test_graze_can_kill_and_award_kill(self):
        self.wear('training_greatsword');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(1,6);self.e.hp=2;old=self.p.kills
        await self.g.attack(self.p,enemy_id=self.e.id);self.assertFalse(self.e.alive);self.assertEqual(self.p.kills,old+1)
    async def test_topple_save_failure_and_auto_standing(self):
        self.wear('training_maul');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(1)
        self.g.fighter_on_weapon_hit(self.p,self.e,{'hit':True})
        self.assertIn('prone',self.e.conditions);self.assertAlmostEqual(self.e.conditions['prone']['until'],self.clock()+1.5)
        r=self.g.hit_player(self.e,self.p);self.assertTrue(r['disadvantage'])
        self.advance(1.6);self.assertFalse(self.g.hit_player(self.e,self.p)['disadvantage'])
    def test_topple_save_success_no_prone(self):
        self.wear('training_maul');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(20)
        self.g.fighter_on_weapon_hit(self.p,self.e,{'hit':True});self.assertNotIn('prone',self.e.conditions)
    def test_prone_gives_melee_advantage_distant_disadvantage(self):
        self.e.conditions['prone']={'until':self.clock()+1.5};self.e.x=self.p.x+70
        self.assertTrue(self.g.hit_enemy(self.p,self.e,melee=True)['advantage'])
        self.e.x=self.p.x+200;p=self.player('ranger');self.assertTrue(self.g.hit_enemy(p,self.e)['disadvantage'])
    async def test_pvp_sap_on_heavy_armored_knight(self):
        q=self.pvp();self.g.combat_rng=base.Dice(20)
        await self.g.attack(self.p,target_id=q.id);self.assertIn('sap',q.buffs);self.assertLess(q.hp,q.max_hp)
        self.assertTrue(self.g.hit_player(q,self.p,pvp=True)['disadvantage'])
    async def test_pvp_graze_resistance_and_protection(self):
        q=self.pvp();self.wear('training_greatsword');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(1)
        q.buffs['stoneskin']={'until':self.clock()+30};before=q.hp
        await self.g.attack(self.p,target_id=q.id);self.assertEqual(before-q.hp,4)  # two attacks; level-5 STR +4, halved to 2 each
        self.advance();self.p.pvp_safety=True;before=q.hp
        await self.g.attack(self.p,target_id=q.id);self.assertEqual(q.hp,before)
    def test_pvp_prone_stops_movement_until_standing(self):
        q=self.pvp();self.wear('training_maul');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(1)
        self.g.fighter_on_weapon_hit(self.p,q,{'hit':True});self.assertEqual(q.speed,0)
        self.advance(1.6);self.assertGreater(q.speed,0)
    async def test_second_wind_zero_mana_shared_bonus_and_sixty_cooldown(self):
        p=self.p;p.mana=0;p.hp=1
        await self.g.cast_spell(p,'second_wind');self.assertEqual(p.hp,5);self.assertEqual(p.mana,0)
        self.assertEqual(p.attack_cooldown_until,0);self.assertEqual(p.bonus_cooldown_until,self.clock()+3)
        self.assertEqual(p.spell_cooldowns['second_wind'],self.clock()+60)
        self.advance(3);await self.g.cast_spell(p,'second_wind');self.assertEqual(p.hp,5)
        self.advance(57);await self.g.cast_spell(p,'second_wind');self.assertEqual(p.hp,9)
    async def test_second_wind_not_great_weapon_dice(self):
        self.p.fighting_style='great_weapon';self.wear('training_greatsword');self.p.equipment['shield']='';self.g.combat_rng=base.Dice(10,1)
        self.p.hp=1;await self.g.cast_spell(self.p,'second_wind');self.assertEqual(self.p.hp,3)
    async def test_second_wind_cooldown_survives_save(self):
        self.p.hp=1;await self.g.cast_spell(self.p,'second_wind')
        q=self.g.load_player(self.p.id,self.p.name,base.WS(),json.loads(json.dumps(self.p.save_data())))
        self.assertEqual(q.spell_cooldowns['second_wind'],self.clock()+60)
    async def test_surge_additional_attack_does_not_reset_other_actions(self):
        self.p.level=2;self.p.mana=0;self.p.bonus_cooldown_until=self.clock()+2
        await self.g.attack(self.p,enemy_id=self.e.id);main=self.p.attack_cooldown_until;before=self.e.hp
        await self.g.cast_spell(self.p,'action_surge',enemy_id=self.e.id)
        self.assertLess(self.e.hp,before);self.assertEqual(self.p.attack_cooldown_until,main);self.assertEqual(self.p.bonus_cooldown_until,self.clock()+2);self.assertEqual(self.p.mana,0)
        self.assertEqual(self.p.spell_cooldowns['action_surge'],self.clock()+90)
        self.assertEqual(self.p.spell_history[-1],'action_surge')
    async def test_surge_extra_attacks_all_levels(self):
        for lv,n in ((2,1),(5,2),(11,3),(20,4)):
            self.p.level=lv;self.p.spell_cooldowns={};self.g.combat_rng=base.Dice(20);self.e.hp=9999
            await self.g.cast_spell(self.p,'action_surge',enemy_id=self.e.id)
            self.assertEqual(self.g.combat_rng.checks,n)
    async def test_surge_spam_and_invalid_target_never_reset_cooldown(self):
        self.p.level=2;self.e.x=self.p.x+999
        await self.g.cast_spell(self.p,'action_surge',enemy_id=self.e.id);self.assertNotIn('action_surge',self.p.spell_cooldowns)
        self.e.x=self.p.x+70;await self.g.cast_spell(self.p,'action_surge',enemy_id=self.e.id);hp=self.e.hp
        for _ in range(8):await self.g.cast_spell(self.p,'action_surge',enemy_id=self.e.id)
        self.assertEqual(self.e.hp,hp)
    async def test_surge_respects_walls_floors_safety(self):
        q=self.pvp();before=q.hp
        self.p.pvp_safety=True;await self.g.cast_spell(self.p,'action_surge',target_id=q.id);self.assertEqual(q.hp,before)
        self.p.pvp_safety=False;q.floor=-1;await self.g.cast_spell(self.p,'action_surge',target_id=q.id);self.assertEqual(q.hp,before)
        q.floor=0
        with patch.object(self.g,'line_clear',return_value=False):await self.g.cast_spell(self.p,'action_surge',target_id=q.id)
        self.assertEqual(q.hp,before);self.assertNotIn('action_surge',self.p.spell_cooldowns)
    async def test_surge_cooldown_persistent_and_main_attack_still_available(self):
        self.p.level=2;await self.g.cast_spell(self.p,'action_surge',enemy_id=self.e.id);self.assertEqual(self.p.attack_cooldown_until,0)
        q=self.g.load_player(self.p.id,self.p.name,base.WS(),json.loads(json.dumps(self.p.save_data())))
        self.assertEqual(q.spell_cooldowns['action_surge'],self.clock()+90)
    async def test_shop_buy_actual_weapon_and_persistent_inventory(self):
        self.p.x=680;self.p.y=1180;gold=self.p.gold;old=len(self.p.inventory)
        await self.g.on_packet(self.p.ws,{'type':'buy','item':'training_maul'})
        self.assertEqual(len(self.p.inventory),old+1);self.assertEqual(self.p.gold,gold-15)
        self.assertEqual(self.p.inventory[-1]['template'],'training_maul')

class FighterHTTP(unittest.IsolatedAsyncioTestCase):
    async def test_new_scripts_css_and_icons_available(self):
        c=TestClient(TestServer(create_app(':memory:')));await c.start_server()
        try:
            for path in ('/fighter_ui.js','/fighter_vfx.js','/fighter.css','/assets/feats/dueling.svg','/assets/equipment/fighter_shield.svg','/assets/spells/action_surge.svg'):
                r=await c.get(path);self.assertEqual(r.status,200,path);self.assertGreater(len(await r.read()),30)
        finally:await c.close()
