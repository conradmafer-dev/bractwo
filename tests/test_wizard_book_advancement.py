"""Wizard book choices remain explicit and saved advancement stays historical."""
import copy
import unittest

from server import level_up, progression_guide, wizard_spellbook
from server.server import Player


class WizardBookAdvancement(unittest.TestCase):
    def player(self, level=5, class_id='mage'):
        # Advancement projects permanent values; it needs neither a live world
        # nor rest resources from a Game instance.
        p=Player('book_guide','Czytelnik',class_id=class_id,level=level)
        p.wizard_spellbook={}
        wizard_spellbook.migrate(p)
        return p

    def receipt(self, level, class_id='mage'):
        p=self.player(level,class_id)
        level_up.record(p,level,level)
        return level_up.pending(p)['pending_level_ups'][0]

    def test_five_offers_learning_preparation_and_memorize(self):
        receipt=self.receipt(5)
        rows={row['id']:row for row in receipt['rows']}
        self.assertIn('+2',rows['wizard_book_learning']['gain'])
        self.assertIn('3. kręgu',rows['wizard_book_learning']['gain'])
        self.assertEqual(rows['wizard_prepared_slots']['gain'],'+2')
        self.assertIn('jednego',rows['memorize_spell']['gain'])
        actions=[action for action in receipt['actions'] if action['kind']=='wizard_book']
        self.assertEqual({a['section'] for a in actions},{'learn','prepare','memorize'})
        self.assertEqual({a['tab'] for a in actions},{'spells'})

    def test_fixed_preparation_table_and_twenty_level_limit(self):
        limits=[4,5,6,7,9,10,11,12,14,15,16,16,17,18,19,21,22,23,24,25]
        previous=0
        for level,limit in enumerate(limits,1):
            with self.subTest(level=level):
                rows={row['id']:row for row in self.receipt(level)['rows']}
                self.assertIn(f'+{6 if level==1 else 2}',rows['wizard_book_learning']['gain'])
                if limit>previous:
                    self.assertEqual(rows['wizard_prepared_slots']['gain'],f'+{limit-previous}')
                else:
                    self.assertNotIn('wizard_prepared_slots',rows)
                self.assertEqual('memorize_spell' in rows,level==5)
                previous=limit
        later=self.receipt(21)
        self.assertFalse(any(a['kind']=='wizard_book' for a in later['actions']))
        self.assertFalse(any(r['id']=='wizard_book_learning' for r in later['rows']))

    def test_circle_unlocks_offer_learning_without_claiming_known_spells(self):
        rows={row['id']:row for row in self.receipt(5)['rows']}
        self.assertEqual(rows['learn_fireball']['label'],'Możliwy do nauki')
        self.assertNotIn('unlock_fireball',rows)
        self.assertIn('spell_damage_fire_bolt',rows)

    def test_book_actions_do_not_leak_to_other_classes(self):
        for class_id in ('knight','ranger','druid'):
            with self.subTest(class_id=class_id):
                receipt=self.receipt(5,class_id)
                self.assertFalse(any(a['kind']=='wizard_book' for a in receipt['actions']))
                self.assertFalse(any(r['id']=='memorize_spell' for r in receipt['rows']))

    def test_snapshot_and_permanent_projection_own_their_nested_state(self):
        p=self.player()
        p.wizard_spellbook={'known':['magic_missile'],'prepared':['magic_missile'],
                            'nested':{'choices':['shield']}}
        level_up.record(p,5,5)
        context=p.level_up_batches[0]['context']
        expected=copy.deepcopy(context['wizard_spellbook'])
        p.wizard_spellbook['known'].append('shield')
        self.assertEqual(context['wizard_spellbook'],expected)
        projected=level_up.permanent(p,5,context)
        projected.wizard_spellbook['prepared'].clear()
        projected.wizard_spellbook['nested']['choices'].append('fireball')
        self.assertEqual(context['wizard_spellbook'],expected)
        self.assertFalse(projected._legacy_wizard_catalog)

    def test_old_receipt_does_not_inherit_current_book_or_new_choice_prompts(self):
        p=self.player()
        level_up.record(p,5,5)
        batch=copy.deepcopy(p.level_up_batches[0])
        del batch['context']['wizard_spellbook']
        old=level_up.receipt(p,batch,5)
        self.assertTrue(any(row['id']=='unlock_fireball' for row in old['rows']))
        self.assertTrue(any(row['id']=='spell_shots_magic_missile' for row in old['rows']))
        self.assertFalse(any(a['kind']=='wizard_book' for a in old['actions']))
        p.wizard_spellbook={'known':['fireball'],'prepared':['fireball']}
        self.assertEqual(level_up.receipt(p,batch,5),old)
        projected=level_up.permanent(p,5,batch['context'])
        self.assertEqual(projected.wizard_spellbook,{})
        self.assertTrue(projected._legacy_wizard_catalog)

    def test_guide_explains_book_rituals_preparation_and_short_rest(self):
        guide={row['level']:row for row in progression_guide.catalog()['mage']}
        first=guide[1]['description']
        self.assertIn('6 czarów I kręgu',first)
        self.assertIn('przygotuj 4',first)
        self.assertIn('Rytuały',first)
        five=guide[5]
        self.assertIn('Memorize Spell',five['name'])
        self.assertIn('krótkiego odpoczynku',five['description'])
        self.assertIn('jeden przygotowany czar',five['description'])
        self.assertIn('Limit przygotowanych czarów: 9',five['description'])
        self.assertIn('Możliwe do nauki w księdze',five['description'])
        self.assertNotIn('Dopisz 2',guide[21]['description'])


if __name__=='__main__':unittest.main()
