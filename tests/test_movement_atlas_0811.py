"""0.8.11: actual class gates, unchanged SRD healing, target/movement independence."""
import unittest
from server.server import Game,Player,Enemy
from server import progression_guide as guide,dnd_content as dnd,combat_rules as rules,spell_scaling as scale
from test_dnd import Clock,WS

class ProgressionGuide(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.catalog=guide.catalog()
 def test_all_and_only_current_classes(self):self.assertEqual(set(self.catalog),set(dnd.CLASS_SPECS))
 def test_each_spell_listed_exactly_at_its_actual_class_gate(self):
  for cls,entries in self.catalog.items():
   listed={key:row['level'] for row in entries for key in row['spells']}
   expected={key:dnd.spell_level(s,cls) for key,s in dnd.SPELLS.items() if cls in s['class_ids'] and dnd.spell_level(s,cls)<=100}
   self.assertEqual(listed,expected,cls)
 def test_no_spell_listed_twice(self):
  for entries in self.catalog.values():
   keys=[key for row in entries for key in row['spells']];self.assertEqual(len(keys),len(set(keys)))
 def test_druid_level10_circle_and_mana_match_current_stats(self):
  entry=next(x for x in self.catalog['druid'] if x['level']==10)
  self.assertIn('II krąg',entry['name']);self.assertIn('Mana +11',entry['description'])
  self.assertEqual(set(entry['spells']),{'moonbeam','barkskin','spike_growth'})
 def test_ranger_does_not_receive_full_caster_circles(self):
  for row in self.catalog['ranger']:
   if 'krąg' in row['name']:self.assertIn(row['level'],[1,20,40,60,80])
 def test_knight_extra_attack_thresholds_match_actual_weapon_rolls(self):
  entries=[r['level'] for r in self.catalog['knight'] if 'Ataki bronią na rundę +' in r['description']]
  self.assertEqual(entries,[20,50,95])
 def test_level20_proficiency_and_attributes_are_not_invented(self):
  for cls in self.catalog:
   before,after=Player('a','A',class_id=cls,level=19),Player('a','A',class_id=cls,level=20)
   row=next(x for x in self.catalog[cls] if x['level']==20)
   for key,value in rules.attributes(after).items():
    diff=value-rules.attributes(before)[key]
    if diff:self.assertIn(f'{guide.ATTRIBUTE_NAMES[key]} +{diff}',row['description'])
   self.assertIn(f'Biegłość +{rules.proficiency(after)-rules.proficiency(before)}',row['description'])
 def test_guide_contains_no_undiscovered_loot_or_legacy_generic_gates(self):
  text=str(self.catalog);self.assertNotIn('loot',text);self.assertNotIn('czwarty atak od 80',text)
 def test_guide_is_ordered_and_detached(self):
  for entries in self.catalog.values():
   self.assertEqual([e['level'] for e in entries],sorted({e['level'] for e in entries}))
  fresh=guide.catalog();fresh['mage'][0]['description']='changed';self.assertNotEqual(fresh['mage'][0],self.catalog['mage'][0])
 def test_healing_before_and_after_circle2_is_srd_2024(self):
  for lvl,n in [(1,2),(9,2),(10,4),(19,4),(20,6)]:
   p=Player('a','A',class_id='druid',level=lvl)
   for key,die in [('cure_wounds',8),('healing_word',4)]:
    with self.subTest(level=lvl,spell=key):self.assertEqual(scale.resolve(p,key)['dice'][:2],[n,die])
 def test_player_can_keep_lower_rank_after_unlock(self):
  p=Player('a','A',class_id='druid',level=20)
  # Stored key is verified against the server's current preference field.
  for key in ['cure_wounds','healing_word']:
   self.assertTrue(scale.choose_circle(p,key,1));s=scale.resolve(p,key);self.assertEqual(s['dice'][0],2);self.assertEqual(s['mana'],20)

class TargetMovement(unittest.IsolatedAsyncioTestCase):
 def setUp(self):
  self.clock=Clock();self.g=Game(':memory:',clock=self.clock)
  self.p=Player('qa','QA',WS(),x=2100,y=1700,level=10);self.p.hp=self.p.max_hp
  self.g.players[self.p.id]=self.p;self.p.dx=0.707;self.p.dy=-0.707
  self.e=Enemy('world_qa_monster','rat',2200,1700,10,2200,1700);self.g.enemies[self.e.id]=self.e;self.g.reindex_enemy(self.e)
 def tearDown(self):self.g.db.close()
 async def test_select_and_deselect_leave_held_movement(self):
  await self.g.select_combat_target(self.p,{'enemy_id':self.e.id});self.assertTrue(self.p.auto_enabled)
  self.assertEqual((self.p.dx,self.p.dy),(.707,-.707))
  await self.g.select_combat_target(self.p,{});self.assertFalse(self.p.auto_enabled)
  self.assertEqual((self.p.dx,self.p.dy),(.707,-.707))
 async def test_kill_target_then_process_preserves_direction(self):
  await self.g.select_combat_target(self.p,{'enemy_id':self.e.id})
  await self.g.defeat(self.e);await self.g.process_player_actions()
  self.assertFalse(self.p.auto_enabled);self.assertEqual((self.p.dx,self.p.dy),(.707,-.707))
 async def test_wrong_target_does_not_clear_direction(self):
  await self.g.select_combat_target(self.p,{'enemy_id':'not_real'})
  self.assertEqual((self.p.dx,self.p.dy),(.707,-.707))
 def test_metadata_has_original_river_bridge_and_new_class_guide(self):
  w=self.g.metadata();self.assertEqual(w['river']['bridge_y'],1080)
  self.assertEqual(w['river']['bridge_h'],150);self.assertEqual(w['class_progression'],guide.catalog())

if __name__=='__main__':unittest.main()
