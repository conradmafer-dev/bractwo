"""Pure Wizard book rules: earned choices, saved state and atomic preparation."""
import copy
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from server import caster_rules, dnd_content as dnd, wizard_spellbook as book


FIRST_SIX = ['magic_missile', 'burning_hands', 'shield', 'mage_armor', 'longstrider', 'alarm']


class WizardSpellbookTests(unittest.TestCase):
    def setUp(self):
        # The server installs the ritual catalogue during startup. Test the same
        # configuration without importing the large generated game world.
        catalog = copy.deepcopy(dnd.SPELLS)
        caster_rules.configure(catalog, copy.deepcopy(dnd.CLASS_SPECS), {})
        self.patch = patch.object(dnd, 'SPELLS', catalog)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def wizard(self, level=1, **extra):
        p = SimpleNamespace(class_id='mage', level=level, wizard_spellbook={},
                            wizard_school='', promoted=False, hotbar=[])
        for key, value in extra.items():
            setattr(p, key, value)
        book.migrate(p)
        return p

    def learn_start(self, p):
        for key in FIRST_SIX:
            self.assertEqual(book.learn(p, key), '')

    def prepared_wizard(self, level=5):
        p = self.wizard(level)
        self.learn_start(p)
        self.assertEqual(book.fill(p, FIRST_SIX[:4]), '')
        return p

    def test_new_book_starts_with_six_level_one_choices_and_four_free_slots(self):
        p = self.wizard()
        s = book.sheet(p)
        self.assertEqual((s['known'], s['prepared']), ([], []))
        self.assertEqual((s['learning_credits'], s['free_preparations'], s['prepared_limit']), (6, 4, 4))
        self.learn_start(p)
        self.assertTrue(book.learn(p, 'find_familiar'))
        self.assertTrue(book.learn(p, 'scorching_ray'))
        self.assertTrue(book.learn(p, 'fire_bolt'))
        self.assertTrue(book.learn(p, 'arcane_recovery'))
        self.assertEqual(book.fill(p, FIRST_SIX[:4]), '')
        self.assertEqual(book.sheet(p)['free_preparations'], 0)

    def test_prepared_caps_follow_2024_table_and_ignore_intelligence(self):
        expected = [4, 5, 6, 7, 9, 10, 11, 12, 14, 15, 16, 16, 17, 18, 19, 21, 22, 23, 24, 25]
        self.assertEqual([book.prepared_limit(n) for n in range(1, 21)], expected)
        self.assertEqual(book.prepared_limit(100), 25)
        self.assertEqual(book.prepared_limit(-5), 4)

    def test_old_learning_credit_cannot_buy_later_circle(self):
        p = self.wizard()
        self.learn_start(p)
        p.level = 2
        book.sync(p)
        self.assertEqual(book.learn(p, 'find_familiar'), '')
        self.assertEqual(book.sheet(p)['learning_credits'], 1)
        self.assertFalse(book.sheet(p)['pending_learning'])
        self.assertTrue(book.sheet(p)['catalog_limited'])
        p.level = 3
        book.sync(p)
        for key in ('scorching_ray', 'misty_step'):
            self.assertEqual(book.learn(p, key), '')
        p.level = 5
        book.sync(p)
        for key in ('fireball', 'lightning_bolt'):
            self.assertEqual(book.learn(p, key), '')
        self.assertTrue(book.learn(p, 'protection_from_energy'))
        self.assertEqual(book.sheet(p)['learning_credits'], 3)
        self.assertFalse(book.sheet(p)['pending_learning'])

    def test_repeated_sync_and_roundtrip_never_refill_choices(self):
        p = self.wizard(3)
        self.learn_start(p)
        self.assertEqual(book.learn(p, 'scorching_ray'), '')
        self.assertEqual(book.fill(p, FIRST_SIX[:4]), '')
        before = copy.deepcopy(p.wizard_spellbook)
        for _ in range(4):
            book.sync(p)
            book.migrate(p, legacy=True)
        self.assertEqual(p.wizard_spellbook, before)
        p.wizard_spellbook = json.loads(json.dumps(p.wizard_spellbook))
        book.migrate(p)
        self.assertEqual(p.wizard_spellbook, before)

    def test_school_choices_are_real_spells_of_earned_school_and_circle(self):
        p = self.wizard(3, promoted=True, wizard_school='evocation')
        school = [row for row in p.wizard_spellbook['grants'] if row['school']]
        self.assertEqual([(r['level'], r['max_circle'], r['remaining']) for r in school], [(3, 2, 2)])
        # Exhaust general choices to isolate the Savant restriction.
        for row in p.wizard_spellbook['grants']:
            if not row['school']:
                row['remaining'] = 0
        self.assertTrue(book.learn(p, 'misty_step'))
        self.assertTrue(book.learn(p, 'fireball'))
        self.assertEqual(book.learn(p, 'magic_missile'), '')
        self.assertEqual(book.learn(p, 'scorching_ray'), '')
        self.assertFalse(book.prepared(p, 'scorching_ray'))
        p.level = 5
        book.sync(p)
        later = [r for r in p.wizard_spellbook['grants'] if r['school'] and r['level'] == 5]
        self.assertEqual([(r['max_circle'], r['remaining']) for r in later], [(3, 1)])
        self.assertTrue(book.learn(p, 'ice_storm'))

    def test_unimplemented_school_catalogue_does_not_create_required_empty_choices(self):
        p = self.wizard(3, promoted=True, wizard_school='illusion')
        for row in p.wizard_spellbook['grants']:
            if not row['school']:
                row['remaining'] = 0
        s = book.sheet(p)
        self.assertEqual(s['learning_credits'], 2)
        self.assertEqual(s['learning_choices'], [])
        self.assertFalse(s['pending_learning'])
        self.assertTrue(s['catalog_limited'])

    def test_school_grants_wait_for_promotion_then_never_repeat(self):
        p = self.wizard(5, wizard_school='abjuration')
        self.assertFalse(any(row['school'] for row in p.wizard_spellbook['grants']))
        p.promoted = True
        book.sync(p)
        rows = [r for r in p.wizard_spellbook['grants'] if r['school']]
        self.assertEqual([(r['level'], r['remaining']) for r in rows], [(3, 2), (5, 1)])
        before = copy.deepcopy(p.wizard_spellbook)
        book.sync(p)
        self.assertEqual(p.wizard_spellbook, before)

    def test_legacy_keeps_known_spells_and_hotbar_preparation_without_past_credits(self):
        p = SimpleNamespace(class_id='mage', level=3, wizard_spellbook={},
                            wizard_school='evocation', promoted=True,
                            hotbar=['fire_bolt', 'misty_step', 'shield', 'alarm'])
        book.migrate(p, legacy=True)
        self.assertEqual(set(p.wizard_spellbook['known']), set(FIRST_SIX + ['find_familiar', 'scorching_ray', 'misty_step']))
        self.assertEqual(p.wizard_spellbook['prepared'][:3], ['misty_step', 'shield', 'alarm'])
        self.assertEqual(len(p.wizard_spellbook['prepared']), 6)
        self.assertEqual(book.sheet(p)['learning_credits'], 0)
        self.assertEqual(book.sheet(p)['free_preparations'], 0)
        self.assertTrue(book.sheet(p)['legacy_migrated'])
        p.level = 5
        book.sync(p)
        self.assertEqual(book.sheet(p)['learning_credits'], 5)
        self.assertEqual(book.sheet(p)['free_preparations'], 3)

    def test_free_fill_adds_only_and_levelup_gives_only_cap_delta(self):
        p = self.wizard()
        self.learn_start(p)
        self.assertEqual(book.fill(p, FIRST_SIX[:4]), '')
        before = copy.deepcopy(p.wizard_spellbook)
        self.assertTrue(book.fill(p, FIRST_SIX[1:5]))
        self.assertEqual(p.wizard_spellbook, before)
        p.level = 2
        book.sync(p)
        self.assertEqual(book.sheet(p)['free_preparations'], 1)
        self.assertEqual(book.fill(p, FIRST_SIX[:5]), '')
        self.assertTrue(book.fill(p, FIRST_SIX))

    def test_long_preparation_applies_atomically_and_cannot_bank_free_slots(self):
        p = self.prepared_wizard()
        before = book.signature(p)
        plan = {'prepared': ['shield', 'alarm']}
        self.assertEqual(book.validate_rest(p, 'long', plan), '')
        self.assertEqual(book.signature(p), before)
        self.assertEqual(book.finish_rest(p, 'long', plan), '')
        self.assertEqual(p.wizard_spellbook['prepared'], ['shield', 'alarm'])
        self.assertEqual(p.wizard_spellbook['free_preparations'], 0)
        self.assertTrue(book.fill(p, ['shield', 'alarm', 'mage_armor']))

    def test_memorize_requires_level_five_and_exactly_one_prepared_exchange(self):
        p = self.prepared_wizard(4)
        plan = {'memorize': {'forget': 'shield', 'prepare': 'alarm'}}
        self.assertTrue(book.validate_rest(p, 'short', plan))
        p.level = 5
        book.sync(p)
        before = list(p.wizard_spellbook['prepared'])
        self.assertEqual(book.validate_rest(p, 'short', plan), '')
        self.assertEqual(p.wizard_spellbook['prepared'], before)
        self.assertEqual(book.finish_rest(p, 'short', plan), '')
        self.assertEqual(len(p.wizard_spellbook['prepared']), len(before))
        self.assertNotIn('shield', p.wizard_spellbook['prepared'])
        self.assertIn('alarm', p.wizard_spellbook['prepared'])
        self.assertIn('shield', p.wizard_spellbook['known'])
        self.assertEqual(p.wizard_spellbook['free_preparations'], 0)
        self.assertTrue(book.finish_rest(p, 'short', plan))

    def test_invalid_rest_payloads_change_nothing_and_finish_revalidates(self):
        p = self.prepared_wizard()
        invalid = [
            ('long', {'prepared': ['shield', 'shield']}),
            ('long', {'prepared': ['fireball']}),
            ('long', {'prepared': ['fire_bolt']}),
            ('long', {'prepared': ['shield'], 'memorize': {}}),
            ('short', {'prepared': ['shield']}),
            ('short', {'memorize': {'forget': 'shield', 'prepare': 'mage_armor'}}),
            ('short', {'memorize': {'forget': 'shield', 'prepare': 'shield'}}),
            ('short', {'memorize': {'forget': 'alarm', 'prepare': 'longstrider'}}),
            ('short', {'memorize': {'forget': 'shield', 'prepare': 'alarm', 'extra': True}}),
            ('short', {'memorize': {'forget': [], 'prepare': 'alarm'}}),
        ]
        before = copy.deepcopy(p.wizard_spellbook)
        for kind, plan in invalid:
            with self.subTest(plan=plan):
                self.assertTrue(book.finish_rest(p, kind, plan))
                self.assertEqual(p.wizard_spellbook, before)
        plan = {'memorize': {'forget': 'shield', 'prepare': 'alarm'}}
        self.assertEqual(book.validate_rest(p, 'short', plan), '')
        p.wizard_spellbook['known'].remove('alarm')
        self.assertTrue(book.finish_rest(p, 'short', plan))
        self.assertTrue(book.prepared(p, 'shield'))

    def test_known_unprepared_ritual_is_allowed_but_normal_spell_is_not(self):
        p = self.wizard()
        self.assertFalse(book.ritual_allowed(p, 'alarm'))
        self.learn_start(p)
        self.assertTrue(book.knows(p, 'alarm'))
        self.assertFalse(book.prepared(p, 'alarm'))
        self.assertTrue(book.ritual_allowed(p, 'alarm'))
        self.assertFalse(book.ritual_allowed(p, 'longstrider'))
        self.assertFalse(book.ritual_allowed(p, 'find_familiar'))

    def test_malformed_persisted_state_is_bounded_and_does_not_refill(self):
        p = self.wizard()
        self.learn_start(p)
        self.assertEqual(book.fill(p, FIRST_SIX[:4]), '')
        data = p.wizard_spellbook
        data['known'] += ['shield', 'fireball', [], 'cure_wounds', 'fire_bolt']
        data['prepared'] += ['alarm', 'fireball', {}]
        data['free_preparations'] = True
        data['grants'] = [{'id': 'base:1', 'remaining': '6'}, {'id': 'base:1', 'remaining': 6},
                          {'id': 'invented', 'remaining': 99999}, None]
        book.sync(p)
        self.assertEqual(data['known'], FIRST_SIX)
        self.assertEqual(data['prepared'], FIRST_SIX[:4])
        self.assertEqual(book.sheet(p)['learning_credits'], 0)
        self.assertEqual(data['free_preparations'], 0)
        data['prepared'] = ['not_a_spell']
        book.sync(p)
        self.assertEqual(data['prepared'], [])
        self.assertEqual(data['free_preparations'], 0)

    def test_missing_and_malformed_read_state_deny_casting_except_historical_projection(self):
        p = SimpleNamespace(class_id='mage', level=1)
        self.assertFalse(book.prepared(p, 'shield'))
        self.assertFalse(book.knows(p, 'shield'))
        self.assertEqual(book.sheet(p)['known'], [])
        p.wizard_spellbook = {}
        self.assertFalse(book.prepared(p, 'shield'))
        self.assertFalse(book.ritual_allowed(p, 'alarm'))
        p._legacy_wizard_catalog = True
        self.assertTrue(book.prepared(p, 'shield'))
        self.assertFalse(book.prepared(p, 'fireball'))
        self.assertFalse(book.knows(p, 'cure_wounds'))
        p._legacy_wizard_catalog = False
        p.wizard_spellbook = {'version': True, 'known': ['shield'], 'prepared': ['shield']}
        self.assertFalse(book.prepared(p, 'shield'))
        book.migrate(p)
        self.assertEqual(book.sheet(p)['learning_credits'], 0)
        self.assertEqual(book.sheet(p)['free_preparations'], 0)

    def test_invalid_negative_watermarks_never_reissue_spent_budgets(self):
        p = self.wizard(5, promoted=True, wizard_school='evocation')
        self.learn_start(p)
        self.assertEqual(book.fill(p, FIRST_SIX[:4]), '')
        self.assertEqual(book.finish_rest(p, 'long', {'prepared': FIRST_SIX[:4]}), '')
        for row in p.wizard_spellbook['grants']:
            row['remaining'] = 0
        for watermark in ('granted_level', 'preparation_level', 'savant_granted_level'):
            p.wizard_spellbook[watermark] = -1
        book.sync(p)
        self.assertEqual(book.sheet(p)['learning_credits'], 0)
        self.assertEqual(book.sheet(p)['free_preparations'], 0)
        for watermark in ('granted_level', 'preparation_level', 'savant_granted_level'):
            self.assertEqual(p.wizard_spellbook[watermark], 5)

    def test_read_gates_and_sheet_do_not_mutate_or_grant_new_level_choices(self):
        p = self.prepared_wizard()
        p.level = 7
        before = copy.deepcopy(p.wizard_spellbook)
        self.assertTrue(book.knows(p, 'shield'))
        self.assertTrue(book.prepared(p, 'shield'))
        self.assertTrue(book.ritual_allowed(p, 'alarm'))
        book.signature(p)
        book.sheet(p)
        self.assertEqual(p.wizard_spellbook, before)
        book.sync(p)
        self.assertGreater(book.sheet(p)['learning_credits'], sum(r['remaining'] for r in before['grants']))

    def test_other_classes_do_not_acquire_wizard_spells(self):
        p = self.wizard()
        p.class_id = 'druid'
        self.assertTrue(book.learn(p, 'shield'))
        self.assertTrue(book.fill(p, []))
        self.assertFalse(book.knows(p, 'shield'))
        self.assertFalse(book.prepared(p, 'shield'))
        self.assertFalse(book.sheet(p)['enabled'])
        book.migrate(p)
        self.assertEqual(p.wizard_spellbook, {})


if __name__ == '__main__':
    unittest.main()
