"""UI_17: progression must not mistake a new free base cast for a nerf.

python -m unittest discover -s tests -p 'test_guiding_bolt_growth_ui17.py' -v
Uses isolated players/in-memory servers; never accesses production accounts.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.server import Player, Game, xp_next
from server import druid_circles as dc, spell_scaling as scale, level_up as lu
import test_dnd as base


def stars(level=19, spent=3, choice=0, equipped=True):
    p = Player('1', 'GrowthTest', class_id='druid', level=level, druid_circle='stars')
    p.druid_circle_state = {'map_equipped': equipped, 'guiding_bolt_spent': spent}
    if choice:
        p.spell_circle_choices = {'guiding_bolt': choice}
    return p


def changes(p, level):
    q = copy.deepcopy(p)
    q.level = level
    return scale.level_gains(p, q, 'guiding_bolt')


class PermanentGrowth(unittest.TestCase):
    def test_exact_reported_level_20_case_is_a_positive_gain(self):
        p = stars()
        q = copy.deepcopy(p)
        q.level = 20
        self.assertEqual((dc.wisdom(p), dc.wisdom(q)), (3, 4))
        self.assertEqual((dc.feature_remaining(p, 'guiding_bolt'),
                          dc.feature_remaining(q, 'guiding_bolt')), (0, 1))
        self.assertEqual(changes(p, 20), [
            {'metric': 'damage_dice', 'amount': '+1k6', 'unit': 'do obrażeń'},
            {'metric': 'mana', 'amount': 20, 'unit': 'do kosztu many'},
        ])

    def test_projection_is_the_highest_useful_paid_circle(self):
        for level, dice, mana in [(19, 5, 30), (20, 6, 50)]:
            s = scale.resolve(stars(level), 'guiding_bolt', automatic=True, active=False)
            self.assertEqual((s['dice'], s['mana']), ([dice, 6, 0], mana))

    def test_charges_and_choices_do_not_change_gains_map_access_is_respected(self):
        expected = changes(stars(), 20)
        for spent in (0, 2, 3, 4, 100):
            for choice in (0, 1, 2):
                for equipped in (False, True):
                    with self.subTest(spent=spent, choice=choice, equipped=equipped):
                        self.assertEqual(changes(stars(spent=spent, choice=choice,
                                                      equipped=equipped), 20), expected if equipped else [])

    def test_next_upgrade_is_positive_and_independent_of_live_resources(self):
        for spent in (0, 3, 4, 100):
            for choice in (0, 1, 2):
                with self.subTest(spent=spent, choice=choice):
                    self.assertEqual(scale.next_upgrade(stars(spent=spent, choice=choice),
                                                        'guiding_bolt'),
                                     'Poziom 20: +1k6 do obrażeń')

    def test_all_later_levels_follow_paid_spell_progression(self):
        for level in range(11, 101):
            for spent in (0, 3, 4, 100):
                with self.subTest(level=level, spent=spent):
                    result = changes(stars(level - 1, spent), level)
                    dice = [c['amount'] for c in result if c['metric'] == 'damage_dice']
                    self.assertEqual(dice, ['+1k6'] if level % 10 == 0 and level <= 80 else [])
                    for c in result:
                        self.assertFalse(str(c['amount']).startswith(('-', '−')), c)

    def test_unlocked_spell_cap_has_no_fabricated_future_bonus(self):
        self.assertEqual(scale.next_upgrade(stars(80), 'guiding_bolt'), '')
        self.assertEqual(changes(stars(80), 81), [])

    def test_existing_open_receipt_recomputes_without_changing_id_or_save(self):
        p = stars()
        lu.record(p, 20, 20)
        batch = json.loads(json.dumps(p.level_up_batches))
        q = stars(20)
        q.level_up_batches = batch
        event = lu.pending(q)['pending_level_ups'][0]
        self.assertEqual(event['id'], batch[0]['id'] + ':20')
        rows = {r['id']: r['gain'] for r in event['rows']}
        self.assertEqual(rows['spell_damage_dice_guiding_bolt'], '+1k6')
        self.assertEqual(rows['spell_mana_guiding_bolt'], '+20')
        self.assertEqual(q.level_up_batches, batch)

    def test_receipt_is_stable_after_resources_rest_and_power_choice_change(self):
        p = stars()
        lu.record(p, 20, 20)
        original = copy.deepcopy(lu.pending(p))
        for spent, choice in ((0, 1), (3, 2), (100, 0)):
            p.druid_circle_state['guiding_bolt_spent'] = spent
            p.spell_circle_choices = {'guiding_bolt': choice} if choice else {}
            p._level_up_cache = None
            self.assertEqual(lu.pending(p), original)

    def test_projection_does_not_modify_player_or_shared_catalogue(self):
        from server import dnd_content as dnd
        p = stars(choice=2)
        p.concentration = 'call_lightning'
        p.concentration_until = 9999
        p.buffs = {'starry_form': {'until': 9999, 'form': 'archer'}}
        state = copy.deepcopy(p.__dict__)
        catalogue = copy.deepcopy(dnd.SPELLS)
        scale.level_gains(p, stars(20), 'guiding_bolt')
        scale.next_upgrade(p, 'guiding_bolt')
        self.assertEqual(p.__dict__, state)
        self.assertEqual(dnd.SPELLS, catalogue)

    def test_land_free_cast_toggle_does_not_hide_highest_paid_progression(self):
        p = stars(29)
        p.druid_circle = 'land'
        p.druid_circle_state = {'land': 'arid', 'natural_free_armed': True,
                                'natural_free_spent': 0}
        # Use an upcastable Land spell available at this tier.
        from server import dnd_content as dnd
        keys = [k for k in dc.bonus_spells(p) if k in scale.UPCAST
                and dnd.SPELLS[k]['circle'] < dnd.circle_for(p.class_id, p.level)]
        self.assertTrue(keys)
        for key in keys:
            with self.subTest(key=key):
                self.assertEqual(scale.resolve(p, key)['cast_circle'], dnd.SPELLS[key]['circle'])
                self.assertEqual(scale.resolve(p, key, automatic=True, active=False)['cast_circle'], 3)

    def test_a_real_negative_delta_is_not_abs_converted_or_hidden(self):
        high = scale.resolve(stars(20, 100), 'guiding_bolt')
        low = scale.resolve(stars(19, 100), 'guiding_bolt')
        self.assertEqual(scale._changes(high, low)[0]['amount'], '-1k6')
        self.assertEqual(lu.number(-10), '-10')


class LiveCastingUnchanged(unittest.IsolatedAsyncioTestCase):
    setUp = base.GameRules.setUp
    tearDown = base.GameRules.tearDown
    player = base.GameRules.player
    enemy = base.GameRules.enemy

    def druid(self, level=20, spent=3, choice=0):
        p = self.player('druid', level)
        p.druid_circle = 'stars'
        p.druid_circle_state = {'guiding_bolt_spent': spent, 'map_equipped': True}
        p.spell_circle_choices = {'guiding_bolt': choice} if choice else {}
        p.mana = p.max_mana
        return p

    async def test_live_auto_still_prefers_free_base_cast_when_available(self):
        p = self.druid()
        s = scale.resolve(p, 'guiding_bolt')
        self.assertEqual((s['cast_circle'], s['dice']), (1, [4, 6, 0]))
        self.assertEqual(self.g.circle_spell_cost(p, s), (0, 'guiding_bolt'))
        mana = p.mana
        await self.g.cast_spell(p, 'guiding_bolt', enemy_id=self.e.id)
        self.assertEqual(p.mana, mana)
        self.assertEqual(dc.spent(p, 'guiding_bolt'), 4)
        self.assertEqual(scale.resolve(p, 'guiding_bolt')['dice'], [6, 6, 0])

    async def test_highest_paid_cast_still_costs_50_at_level_20(self):
        p = self.druid(spent=4)
        s = scale.resolve(p, 'guiding_bolt')
        self.assertEqual((s['cast_circle'], s['dice'], s['mana']), (3, [6, 6, 0], 50))
        mana = p.mana
        await self.g.cast_spell(p, 'guiding_bolt', enemy_id=self.e.id)
        self.assertEqual(p.mana, mana - 50)
        self.assertEqual(dc.spent(p, 'guiding_bolt'), 4)

    async def test_explicit_second_circle_remains_available_and_unchanged(self):
        p = self.druid(choice=2)
        s = scale.resolve(p, 'guiding_bolt')
        self.assertEqual((s['cast_circle'], s['dice'], s['mana']), (2, [5, 6, 0], 30))
        mana = p.mana
        await self.g.cast_spell(p, 'guiding_bolt', enemy_id=self.e.id)
        self.assertEqual(p.mana, mana - 30)
        self.assertEqual(dc.spent(p, 'guiding_bolt'), 3)

    async def test_actual_award_publishes_positive_receipt_and_extra_free_use(self):
        p = self.druid(19, spent=3)
        self.g.award(p, xp_next(19), 0)
        self.assertEqual(p.level, 20)
        self.assertEqual(dc.feature_remaining(p, 'guiding_bolt'), 1)
        owner = p.public(self.clock(), private=True)
        event = owner['pending_level_ups'][-1]
        row = next(r for r in event['rows'] if r['id'] == 'spell_damage_dice_guiding_bolt')
        self.assertEqual(row['gain'], '+1k6')
        profile = owner['spell_profiles']['guiding_bolt']
        self.assertEqual((profile['dice'], profile['mana']), ([4, 6, 0], 0))
        self.assertEqual(profile['next_upgrade'], 'Poziom 30: +1k6 do obrażeń')

    async def test_dismissed_level_panel_does_not_reappear(self):
        p = self.druid(19, spent=3)
        self.g.award(p, xp_next(19), 0)
        event = lu.pending(p)['pending_level_ups'][-1]
        self.assertTrue(lu.dismiss(p, event['id']))
        p._level_up_cache = None
        self.assertEqual(lu.pending(p)['pending_level_ups'], [])


if __name__ == '__main__':
    unittest.main()
