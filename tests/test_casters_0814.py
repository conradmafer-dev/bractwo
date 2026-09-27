"""Caster and equipment regression coverage against real authoritative code."""
import asyncio,copy,json,math,unittest
from pathlib import Path
import test_dnd as base
from server.server import ITEMS,Player,make_item,create_app
from server import equipment_rules as gear,caster_rules as caster,combat_rules as rules,dnd_content as dnd,spell_scaling,fighter_rules as fighter
from aiohttp.test_utils import TestClient,TestServer

class Catalog(unittest.TestCase):
 def test_no_exotic_weapon_category(self):
  for k,s in ITEMS.items():
   if s['slot']=='weapon' and not gear.is_focus(s):self.assertIn(s['weapon_category'],('simple','martial'),k);self.assertIn(s['weapon_type'],gear.WEAPON_TYPES,k)
 def test_armor_categories_every_item(self):
  for k,s in ITEMS.items():
   if s['slot']=='armor':self.assertIn(s['armor_kind'],('none','light','medium','heavy'),k)
 def test_ranged_short_and_longbow_training(self):
  self.assertEqual(ITEMS['skeleton_shortbow']['weapon_category'],'simple');self.assertEqual(ITEMS['bandit_longbow']['weapon_category'],'martial')
 def test_plain_gear_not_class_locked(self):
  for k,s in ITEMS.items():
   if s['slot'] in ('weapon','armor','shield') and not gear.is_focus(s):self.assertEqual(set(s['class_ids']),set(gear.ALL_CLASSES),k)
 def test_only_real_rituals(self):
  self.assertEqual({k for k,s in dnd.SPELLS.items() if s.get('ritual')},{'alarm','find_familiar','speak_with_animals'})
  self.assertFalse(dnd.SPELLS['longstrider'].get('ritual'));self.assertFalse(dnd.SPELLS['cure_wounds'].get('ritual'))
 def test_all_new_art_in_both_clients(self):
  root=Path(__file__).resolve().parents[1]
  paths=[s['icon'] for s in dnd.SPELLS.values()]+[f'assets/feats/{k}.svg' for k in gear.TRAINING]+[s['icon'] for s in caster.ORDERS.values()]
  for path in paths:self.assertEqual((root/'web'/path).read_bytes(),(root/'client'/path).read_bytes(),path)
 def test_druid_form_gates(self):
  for k,n in [('wolf',5),('cat',5),('black_bear',15),('bear',35)]:self.assertEqual(dnd.spell_level(dnd.SPELLS['wild_shape_'+k],'druid'),n)
 def test_recovery_slot_cap_not_high_circle(self):
  self.assertEqual(caster.recovery_amount(Player('1','A',class_id='mage')),20)
  self.assertEqual(caster.recovery_amount(Player('1','A',class_id='mage',level=10)),40)
  for n in range(1,101):self.assertLessEqual(caster.recovery_amount(Player('1','A',class_id='mage',level=n)),200)
 def test_feat_levels_map_four_to_fifteen(self):self.assertEqual(gear.FEAT_LEVELS,(15,35,55,75))

class CasterGame(unittest.IsolatedAsyncioTestCase):
 setUp=base.GameRules.setUp
 tearDown=base.GameRules.tearDown
 player=base.GameRules.player
 enemy=base.GameRules.enemy
 account=base.GameRules.account
 def advance(self,n=3.1,tick=True):
  self.clock.advance(n);self.g.time+=n
  for p in self.g.players.values():p.current_wall_time=self.clock();p.dx=p.dy=0
  if tick:self.g.tick_dnd(min(n,.1))
 def wear(self,p,key,slot=None):
  item=make_item(key);p.inventory.append(item);p.equipment[slot or ITEMS[key]['slot']]=item['uid'];return item
 def test_class_grants_exact_and_no_bonus_attributes(self):
  for cls in gear.ALL_CLASSES:
   p=self.player(cls,pid=cls);self.assertEqual(set(gear.training_sources(p)),set(gear.CLASS_TRAINING[cls]));self.assertEqual(rules.attributes(p),p.spec['attributes']);self.assertFalse(p.training_feats)
 def test_druid_starts_light_no_shield_or_medium_gift(self):
  p=self.player('druid');self.assertEqual(rules.equipped_item(p,'armor')['armor_kind'],'light');self.assertFalse(p.equipment['shield']);self.assertFalse(any(ITEMS[i['template']].get('armor_kind')=='medium' for i in p.inventory))
 async def test_warden_grants_no_items_or_attribute_points(self):
  p=self.player('druid');inv=copy.deepcopy(p.inventory);attrs=rules.attributes(p)
  await self.g.select_primal_order(p,'warden');self.assertTrue(gear.has(p,'medium_armor'));self.assertTrue(gear.has(p,'martial_weapons'));self.assertEqual(p.inventory,inv);self.assertEqual(rules.attributes(p),attrs)
 async def test_mystic_only_spell_attack_and_dc(self):
  p=self.player('druid');atk=rules.attack_bonus(p);sp=rules.spell_bonus(p);dmg=rules.weapon_dice(p);maxmana=p.max_mana
  await self.g.select_primal_order(p,'magician');self.assertEqual(rules.spell_bonus(p),sp+1);self.assertEqual(rules.spell_dc(p),8+sp+1);self.assertEqual(rules.attack_bonus(p),atk);self.assertEqual(rules.weapon_dice(p),dmg);self.assertEqual(p.max_mana,maxmana)
 async def test_path_reject_wrong_class_invalid_and_combat(self):
  await self.g.select_primal_order(self.p,'warden');self.assertFalse(self.p.primal_order)
  p=self.player('druid');p.combat_until=self.clock()+9
  for key in ['warden','magician',{},None,'fake']:await self.g.select_primal_order(p,key)
  self.assertFalse(p.primal_order)
 async def test_change_requires_master(self):
  p=self.player('druid');await self.g.select_primal_order(p,'warden');await self.g.select_primal_order(p,'magician');self.assertEqual(p.primal_order,'warden')
  from server.world_content import NPCS
  m=next(n for n in NPCS if n.get('service')=='master');p.x,p.y,p.floor=m['x'],m['y'],m.get('floor',0)
  await self.g.select_primal_order(p,'magician');self.assertEqual(p.primal_order,'magician')
 async def test_first_path_is_saved(self):
  p=self.player('druid');self.account(p);await self.g.select_primal_order(p,'warden')
  raw=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=?',(p.id,)).fetchone()[0]);self.assertEqual(raw['primal_order'],'warden')
 def test_legacy_medium_grace_then_new_restrictions(self):
  p=self.player('druid');self.wear(p,'hide_armor');p.caster_rules_version=0;self.g.migrate_caster(p)
  self.assertTrue(p.legacy_medium_grace);self.assertFalse(gear.armor_penalty(p));p.primal_order='magician';self.assertTrue(gear.armor_penalty(p));self.assertFalse(gear.has(p,'medium_armor'))
 async def test_training_missing_only_duplicate_rejected(self):
  p=self.player('druid',15);before=rules.attributes(p)['strength'];await self.g.choose_training_feat(p,'moderately_armored','strength')
  self.assertTrue(gear.has(p,'medium_armor'));self.assertEqual(rules.attributes(p)['strength'],before+1);self.assertEqual(gear.feat_points(p),0)
  for _ in range(3):await self.g.choose_training_feat(p,'moderately_armored','strength')
  self.assertEqual(rules.attributes(p)['strength'],before+1);self.assertNotIn('moderately_armored',[f['id'] for f in gear.training_sheet(p)['options']])
 async def test_warden_cannot_buy_redundant_armor_feat(self):
  p=self.player('druid',15);await self.g.select_primal_order(p,'warden');await self.g.choose_training_feat(p,'moderately_armored','strength');self.assertFalse(p.training_feats);self.assertEqual(gear.feat_points(p),1)
 async def test_low_level_no_free_feat_selection(self):
  p=self.player('mage',1);await self.g.choose_training_feat(p,'lightly_armored','dexterity');self.assertFalse(p.training_feats)
 async def test_mage_light_feat_grants_shield_but_not_medium(self):
  p=self.player('mage',15);await self.g.choose_training_feat(p,'lightly_armored','dexterity');self.assertTrue(gear.has(p,'light_armor'));self.assertTrue(gear.has(p,'shields'));self.assertFalse(gear.has(p,'medium_armor'))
 def test_fighter_has_no_duplicate_training_options(self):self.assertFalse(gear.training_sheet(self.p)['options'])
 def test_prerequisite_loss_disables_dependent_feat_until_regained(self):
  p=self.player('druid',35);p.primal_order='warden';p.training_feats={'heavily_armored':'strength'};self.assertTrue(gear.has(p,'heavy_armor'));p.primal_order='magician';self.assertFalse(gear.has(p,'heavy_armor'));p.training_feats['moderately_armored']='dexterity';self.assertTrue(gear.has(p,'heavy_armor'))
 def test_weapon_proficiency_only_changes_hit(self):
  p=self.player('druid');self.wear(p,'bandit_longsword');a=rules.attack_bonus(p);d=rules.weapon_dice(p);p.primal_order='warden';self.assertEqual(rules.attack_bonus(p),a+2);self.assertEqual(rules.weapon_dice(p),d)
 def test_warden_does_not_get_fighter_mastery(self):
  p=self.player('druid');p.primal_order='warden';item=self.wear(p,'bandit_longsword');self.assertFalse(gear.preview(p,item)['mastery_active']);self.assertEqual(fighter.class_sheet(p),{})
 async def test_all_classes_can_equip_actual_weapons(self):
  p=self.player('mage');i=make_item('training_greatsword');p.inventory.append(i);await self.g.inventory_command(p,'equip',{'uid':i['uid']});self.assertEqual(p.equipment['weapon'],i['uid']);self.assertFalse(gear.proficient(p));self.assertTrue(gear.weapon_disadvantage(p))
 def test_ranged_attack_depends_on_equipped_weapon_not_class(self):
  p=self.player('druid');self.wear(p,'skeleton_shortbow');self.assertFalse(gear.melee(p));self.assertEqual(rules.attack_ability(p),'dexterity');self.assertEqual(rules.attack_range(p),310)
 async def test_two_handed_staff_removes_shield_but_preserves_item(self):
  p=self.player('druid');item=self.wear(p,'wooden_shield');ac=p.armor_class;await self.g.set_weapon_grip(p,'two');self.assertEqual(p.weapon_grip,'two');self.assertFalse(p.equipment['shield']);self.assertIn(item,p.inventory);self.assertEqual(p.armor_class,ac-2);self.assertEqual(rules.weapon_dice(p),(1,8,2))
 def test_shield_training_not_universal(self):
  p=self.player('mage');self.wear(p,'wooden_shield');self.assertEqual(fighter.shield_bonus(p),0)
  q=self.player('druid',pid='2');self.wear(q,'wooden_shield');self.assertEqual(fighter.shield_bonus(q),2)
 async def test_untrained_armor_blocks_spells_and_ritual(self):
  p=self.player('mage');self.wear(p,'fighter_chain_mail');before=p.mana;await self.g.cast_spell(p,'mage_armor');await self.g.start_caster_channel(p,'alarm',True);self.assertFalse(p.casting_channel);self.assertEqual(p.mana,before);self.assertNotIn('mage_armor',p.buffs)
 async def test_shillelagh_does_not_affect_martial_weapons(self):
  p=self.player('druid');self.wear(p,'training_greatsword');await self.g.cast_spell(p,'shillelagh');self.assertNotIn('shillelagh',p.buffs)
  p.buffs['shillelagh']={'until':self.clock()+60};self.assertEqual(rules.attack_ability(p),'strength')
 def test_preview_is_real_and_does_not_mutate(self):
  p=self.player('druid');p.primal_order='warden';i=make_item('knight_weapon_2');old=copy.deepcopy(p.equipment);res=gear.preview(p,i)
  p.inventory.append(i);p.equipment['weapon']=i['uid'];self.assertEqual(res['attack'],rules.attack_bonus(p));self.assertEqual(res['dice'],rules.dice_text(rules.weapon_dice(p)));p.equipment=old;self.assertNotEqual(p.equipment['weapon'],i['uid'])
 # Recovery changed in 0.8.15: instant bonus action, not a channel.
 async def test_recovery_is_immediate(self):
  p=self.player('mage');p.mana=5;await self.g.cast_spell(p,'arcane_recovery');self.assertEqual(p.mana,25);self.assertFalse(p.casting_channel);self.assertAlmostEqual(p.spell_cooldowns['arcane_recovery'],self.clock()+180)
 async def test_recovery_movement_does_not_undo_it(self):
  p=self.player('mage');p.mana=0;p.dx=1;await self.g.cast_spell(p,'arcane_recovery');self.assertEqual(p.dx,1);p.x+=1;self.advance(4.1);self.assertEqual(p.mana,20);self.assertFalse(p.casting_channel)
 async def test_recovery_damage_does_not_undo_it(self):
  p=self.player('mage');p.mana=0;await self.g.cast_spell(p,'arcane_recovery');self.g.damage_player(p,1);self.advance(4.1);self.assertEqual(p.mana,20);self.assertFalse(p.casting_channel)
 async def test_recovery_works_in_combat(self):
  p=self.player('mage');p.mana=0;p.combat_until=self.clock()+10;await self.g.cast_spell(p,'arcane_recovery');self.assertFalse(p.casting_channel);self.assertEqual(p.mana,20)
 async def test_recovery_cd_survives_save_load(self):
  p=self.player('mage');self.account(p);p.mana=0;await self.g.cast_spell(p,'arcane_recovery');raw=p.save_data();q=self.g.load_player(p.id,p.name,p.ws,raw);self.assertEqual(q.spell_cooldowns['arcane_recovery'],self.clock()+180);self.assertEqual(q.mana,20);self.assertNotIn('casting_channel',raw)
 async def test_ritual_no_mana_cost_success(self):
  p=self.player('mage');p.mana=0;await self.g.start_caster_channel(p,'alarm',True);self.assertEqual(p.casting_channel['total'],10);self.advance(10.1);self.assertIn(p.id,self.g.alarms);self.assertEqual(p.mana,0);self.assertIn('ritual_alarm',p.buffs)
 async def test_fake_ritual_cannot_cast_heal_free(self):
  p=self.player('druid');p.mana=0;await self.g.start_caster_channel(p,'cure_wounds',True);self.assertFalse(p.casting_channel)
 async def test_ritual_familiar_consumes_gold_once_no_attack(self):
  p=self.player('mage');p.mana=0;p.gold=10;await self.g.start_caster_channel(p,'find_familiar',True);self.advance(40.1);self.assertEqual(p.gold,0);self.assertEqual(p.mana,0);self.assertIn(p.id,self.g.familiars);pet=self.g.familiars[p.id];self.assertEqual(pet.dice,(0,1,0));self.g.complete_channel(p);self.assertEqual(p.gold,0)
 async def test_failed_familiar_material_no_channel(self):
  p=self.player('mage');p.gold=9;await self.g.start_caster_channel(p,'find_familiar',True);self.assertFalse(p.casting_channel)
 async def test_familiar_help_not_damage_and_consumed_once(self):
  p=self.player('mage');self.g.summon_familiar(p);await self.g.familiar_command(p,'help');p.auto_enemy_id=self.e.id;pet=self.g.familiars[p.id];pet.x,pet.y=self.e.x,self.e.y;hp=self.e.hp;self.g.tick_dnd(.1)
  self.assertEqual(self.e.hp,hp);self.assertTrue(rules.active_buff(p,'familiar_help'));self.assertTrue(self.g.caster_attack_advantage(p,self.e));self.assertFalse(self.g.caster_attack_advantage(p,self.e))
 async def test_familiar_pvp_respects_safety(self):
  p=self.player('mage',20);q=self.player('druid',20,'2');q.x=p.x+30;self.g.summon_familiar(p);await self.g.familiar_command(p,'help');p.auto_target_id=q.id;self.g.tick_dnd(.1);self.assertNotIn('familiar_help',p.buffs);self.assertFalse(p.aggressors)
 async def test_familiar_dismiss_and_death_clean_up(self):
  p=self.player('mage');self.g.summon_familiar(p);await self.g.familiar_command(p,'dismiss');self.assertNotIn(p.id,self.g.familiars);self.assertFalse(p.familiar_state)
  self.g.summon_familiar(p);self.g.familiars[p.id].hp=0;self.g.tick_dnd(.1);self.assertNotIn(p.id,self.g.familiars)
 async def test_speech_requires_spell_and_sign_requires_druid(self):
  p=self.player('druid');s=self.g.nature_sites[0];p.x,p.y=s['x'],s['y'];await self.g.nature_interaction(p,s['id']);self.assertFalse(any(m['type']=='nature_hint' for m in p.ws.messages))
  p.buffs['speak_with_animals']={'until':self.clock()+30};await self.g.nature_interaction(p,s['id']);self.assertTrue(any(m['type']=='nature_hint' for m in p.ws.messages))
 def test_nature_metadata_does_not_leak_hidden_hints(self):
  for s in self.g.metadata()['nature_sites']:self.assertNotIn('text',s);self.assertNotIn('hint_x',s)
 async def test_shape_fifth_level_own_hp_and_temp_hp(self):
  p=self.player('druid',5);hp=p.max_hp;p.hp=7;await self.g.cast_spell(p,'wild_shape_wolf');self.assertEqual(p.form,'wolf');self.assertEqual(p.max_hp,hp);self.assertEqual(p.hp,7);self.assertEqual(p.temp_hp,2);self.assertEqual(p.armor_class,12);self.assertEqual(rules.weapon_dice(p),(1,6,2))
 async def test_shape_temp_loss_does_not_end_form(self):
  p=self.player('druid',5);await self.g.cast_spell(p,'wild_shape_wolf');self.g.damage_player(p,3);self.assertEqual(p.temp_hp,0);self.assertEqual(p.form,'wolf');self.assertGreater(p.hp,0)
 async def test_shape_shared_cooldown_return_not_refund(self):
  p=self.player('druid',5);await self.g.cast_spell(p,'wild_shape_wolf');self.advance();await self.g.cast_spell(p,'wild_shape_wolf');self.assertFalse(p.form);self.advance();await self.g.cast_spell(p,'wild_shape_cat');self.assertFalse(p.form);await self.g.cast_spell(p,'wild_companion');self.assertNotIn(p.id,self.g.familiars)
 async def test_shape_magic_block_concentration_kept(self):
  p=self.player('druid',5);p.concentration='entangle';p.concentration_until=self.clock()+30;await self.g.cast_spell(p,'wild_shape_wolf');mana=p.mana;self.advance();await self.g.cast_spell(p,'cure_wounds');self.assertEqual(p.mana,mana);self.assertEqual(p.concentration,'entangle')
 async def test_shape_no_equipment_or_spell_bonuses(self):
  p=self.player('druid',50);self.wear(p,'druid_weapon_3');self.wear(p,'wooden_shield');await self.g.cast_spell(p,'wild_shape_black_bear');self.assertEqual(p.armor_class,11);self.assertEqual(rules.weapon_dice(p),(1,6,2));self.assertEqual(rules.attacks_per_round(p),2);self.assertEqual(fighter.shield_bonus(p),0)
 async def test_shape_high_forms_gated(self):
  p=self.player('druid',5);await self.g.cast_spell(p,'wild_shape_black_bear');self.assertFalse(p.form);await self.g.cast_spell(p,'wild_shape_bear');self.assertFalse(p.form)
 async def test_wild_companion_no_mana_or_gold_uses_shape_cd(self):
  p=self.player('druid',5);p.mana=p.gold=0;await self.g.cast_spell(p,'wild_companion');self.assertIn(p.id,self.g.familiars);self.assertEqual(p.gold,0);self.assertGreater(p.spell_cooldowns['wild_shape_shared'],self.clock())
 def test_owner_sheet_is_private(self):
  p=self.player('druid');self.assertIn('character_sheet',p.public(self.clock(),self.g.time,True));self.assertNotIn('character_sheet',p.public(self.clock(),self.g.time,False));self.assertNotIn('item_previews',p.public(self.clock(),self.g.time,False))
 def test_level_up_new_shapes_and_feat_points(self):
  p=self.player('druid',4);from server import level_up as lu
  lu.record(p,5,5);p.level=5;rows=lu.pending(p)['pending_level_ups'][0]['rows'];self.assertIn('unlock_wild_shape_wolf',[r['id'] for r in rows]);self.assertFalse(dnd.spell_allowed(p,'wild_shape_black_bear'))

 def test_nature_sites_are_walkable(self):
  for site in self.g.nature_sites:self.assertFalse(self.g.blocked(site['x'],site['y'],radius=12,floor=site['floor']),site['id'])
 async def test_alarm_real_entry_not_initial_occupants(self):
  p=self.player('mage');await self.g.start_caster_channel(p,'alarm',True);self.advance(10.1);p.caster_messages=[]
  self.e.x,self.e.y=p.x+20,p.y;self.g.reindex_enemy(self.e);self.g.tick_dnd(.1)
  self.assertTrue(any('Alarm!' in message for message in p.caster_messages));p.caster_messages=[];self.g.tick_dnd(.1);self.assertFalse(p.caster_messages)
 async def test_alarm_owner_only_snapshot_and_same_party_ignored(self):
  p=self.player('mage');q=self.player('druid',1,'2');p.party_id=q.party_id='group';await self.g.start_caster_channel(p,'alarm',True);self.advance(10.1);p.caster_messages=[]
  q.x,q.y=p.x,p.y;self.g.tick_dnd(.1);self.assertFalse(any('Alarm!' in m for m in p.caster_messages))
  self.assertEqual(len(self.g.snapshot(p.id)['alarms']),1);self.assertEqual(self.g.snapshot(q.id)['alarms'],[])
 def test_familiar_takes_actual_monster_damage(self):
  p=self.player('mage');self.g.summon_familiar(p);pet=self.g.familiars[p.id]
  self.g.hit_player(self.e,pet);self.assertLess(pet.hp,3);self.assertEqual(p.hp,p.max_hp)
 def test_staff_focus_bonus_not_advertised_to_fighter(self):
  self.assertEqual(gear.preview(self.p,make_item('druid_weapon_2')).get('spell_bonus'),0)
 def test_shillelagh_book_remains_staff_specific_with_a_sword(self):
  p=self.player('druid');self.wear(p,'bandit_longsword');s=spell_scaling.resolve(p,'shillelagh');self.assertEqual(s['weapon_dice'],[1,8,3])
 def test_armor_disadvantage_applies_to_str_dex_not_shillelagh_wis(self):
  p=self.player('druid');self.wear(p,'fighter_chain_mail');self.assertTrue(gear.weapon_disadvantage(p));p.buffs['shillelagh']={'until':self.clock()+30};self.assertFalse(gear.weapon_disadvantage(p))

class HTTP(unittest.IsolatedAsyncioTestCase):
 async def test_all_caster_assets_served(self):
  app=create_app(':memory:');client=TestClient(TestServer(app));await client.start_server()
  try:
   for path in ['caster_ui.js','caster_vfx.js','caster.css','assets/spells/arcane_recovery.svg','assets/feats/warden.svg','assets/equipment/wooden_shield.svg']:
    r=await client.get('/'+path);self.assertEqual(r.status,200,path);self.assertGreater(len(await r.read()),50)
  finally:await client.close()
