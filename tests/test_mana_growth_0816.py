"""0.8.16: whole-point mana growth, recovery, legacy receipts and save migration.

Explicit expected tables come from the approved design and 0.8.15 anchor totals,
not from the interpolation helper under test. Real Game/Player code is exercised.
"""
import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from server.server import Player, xp_next
from server import dnd_content as dnd, caster_rules as caster, level_up as lu
from server import spell_scaling as scaling, progression_guide as guide
import test_dnd as base

FULL = [40, 51, 62, 73, 84, 96, 107, 118, 129, 140]
HALF = [40, 42, 44, 47, 49, 51, 53, 56, 58, 60]
RECOVERY = [20, 22, 24, 27, 29, 31, 33, 36, 38, 40]
ANCHORS = {
    1: (40, 40, 20), 10: (140, 60, 40), 20: (270, 140, 60),
    30: (380, 170, 80), 40: (570, 270, 90), 50: (730, 320, 110),
    60: (830, 380, 130), 70: (940, 440, 140), 80: (1070, 570, 160),
    90: (1230, 640, 180), 95: (1330, 640, 180),
}


def player(cls='mage', level=1, **kwargs):
    return Player('1', 'ManaTest', class_id=cls, level=level, **kwargs)


class GrowthNumbers(unittest.TestCase):
    def test_full_casters_every_level_one_to_ten(self):
        for cls in ('mage', 'druid'):
            self.assertEqual([player(cls, n).max_mana for n in range(1, 11)], FULL)

    def test_ranger_every_level_one_to_ten(self):
        self.assertEqual([player('ranger', n).max_mana for n in range(1, 11)], HALF)

    def test_recovery_every_level_one_to_ten(self):
        self.assertEqual([caster.recovery_amount(player(level=n)) for n in range(1, 11)], RECOVERY)

    def test_level_ten_to_twenty_full_and_half_and_recovery(self):
        for level in range(10, 21):
            p = player(level=level)
            self.assertEqual(p.max_mana, 140 + 13*(level-10))
            self.assertEqual(player('druid', level).max_mana, p.max_mana)
            self.assertEqual(player('ranger', level).max_mana, 60 + 8*(level-10))
            self.assertEqual(caster.recovery_amount(p), 40 + 2*(level-10))

    def test_every_original_milestone_and_final_cap_preserved(self):
        for level, (full, half, recovery) in ANCHORS.items():
            with self.subTest(level=level):
                self.assertEqual(player(level=level).max_mana, full)
                self.assertEqual(player('druid', level).max_mana, full)
                self.assertEqual(player('ranger', level).max_mana, half)
                self.assertEqual(caster.recovery_amount(player(level=level)), recovery)
        for level in (96, 100, 1000, 10**12):
            self.assertEqual(player(level=level).max_mana, 1330)
            self.assertEqual(player('ranger', level).max_mana, 640)
            self.assertEqual(caster.recovery_amount(player(level=level)), 180)

    def test_all_awards_are_integer_monotone_and_bounded(self):
        for cls, cap in (('mage', 1330), ('druid', 1330), ('ranger', 640)):
            values = [player(cls, n).max_mana for n in range(1, 201)]
            self.assertEqual(values, sorted(values))
            self.assertTrue(all(type(v) is int and v <= cap for v in values))
            self.assertTrue(all(values[n-1] >= dnd.legacy_base_mana(cls, n) for n in range(1, 201)))
        values = [caster.recovery_amount(player(level=n)) for n in range(1, 201)]
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(type(v) is int and v <= 180 for v in values))

    def test_interpolation_rounds_halves_up_and_clamps_boundaries(self):
        points = ((1, 20), (3, 21))
        self.assertEqual([dnd.interpolate_growth(n, points) for n in (-1, 0, 1, 2, 3, 4)], [20,20,20,21,21,21])

    def test_knight_mana_is_unchanged_including_focus(self):
        for level in (1, 5, 10, 20, 50, 95, 10000):
            self.assertEqual(player('knight', level).max_mana, 30)
            self.assertEqual(player('knight', level, mastery={'focus': 3}).max_mana, 42)
            self.assertEqual(dnd.mana_budget_info(player('knight', level))['next_level_gain'], 0)

    def test_focus_bonus_added_after_smoothing_once_and_capped(self):
        for focus, bonus in ((-1,0), (0,0), (3,12), (20,80), (99,80)):
            p=player(level=5, mastery={'focus': focus})
            self.assertEqual(p.max_mana, 84+bonus)
            self.assertEqual(dnd.mana_budget_info(p)['bonus'], bonus)
            self.assertEqual(caster.recovery_amount(p), 29)

    def test_spells_costs_and_circle_gates_are_unchanged(self):
        self.assertEqual(dnd.MANA_COSTS, (0,20,30,50,60,70,90,100,110,130))
        for cls in ('mage','druid','ranger'):
            for level in range(1, 101):
                self.assertEqual(dnd.circle_for(cls, level), min(5,1+level//20) if cls=='ranger' else min(9,1+level//10))
        s=scaling.resolve(player(level=9), 'magic_missile')
        self.assertEqual((s['cast_circle'],s['mana'],s['shots']), (1,20,3))
        s=scaling.resolve(player(level=10), 'magic_missile')
        self.assertEqual((s['cast_circle'],s['mana'],s['shots']), (2,30,4))
        self.assertEqual(caster.ARCANE_COOLDOWN, 180)

    def test_intermediate_mana_is_not_misrepresented_as_slots(self):
        info=dnd.mana_budget_info(player(level=5))
        self.assertEqual((info['base'],info['next_level_gain'],info['progression']), (84,12,'per_level'))
        self.assertTrue(info['slots_are_reference'])
        self.assertNotEqual(info['base'], sum(n*dnd.MANA_COSTS[i+1] for i,n in enumerate(info['slots'])))
        self.assertEqual(dnd.mana_budget_info(player('knight'))['base'],30)

    def test_next_recovery_upgrade_is_next_level_not_next_fifth(self):
        for level, expected in ((1,'Poziom 2: +2 many'), (3,'Poziom 4: +3 many'), (5,'Poziom 6: +2 many'), (89,'Poziom 90: +2 many'), (90,'')):
            self.assertEqual(scaling.next_upgrade(player(level=level),'arcane_recovery'), expected)
        self.assertEqual(scaling.next_upgrade(player(level=1,mana_rules_version=2),'arcane_recovery'), 'Poziom 10: +20 many')

    def test_guide_lists_small_gains_and_recovery_only_for_mage(self):
        catalog=guide.catalog()
        mage={e['level']:e for e in catalog['mage']}
        self.assertIn('Mana +12.',mage[6]['description'])
        self.assertIn('Odzyskanie mocy +2 many.',mage[6]['description'])
        self.assertIn('Mana +11.',mage[10]['description'])
        for cls in ('druid','ranger','knight'):
            self.assertTrue(all('Odzyskanie mocy' not in e['description'] for e in catalog[cls]))


class LiveGrowth(unittest.IsolatedAsyncioTestCase):
    setUp=base.GameRules.setUp
    tearDown=base.GameRules.tearDown
    player=base.GameRules.player
    account=base.GameRules.account
    enemy=base.GameRules.enemy

    def gains(self,p,level):
        event=next(e for e in lu.pending(p)['pending_level_ups'] if e['level']==level)
        return {r['id']:r for r in event['rows']}

    def test_each_award_gets_a_separate_mana_line(self):
        for cls, amounts in (('mage',FULL),('druid',FULL),('ranger',HALF)):
            p=self.player(cls)
            for level in range(2,11):
                self.g.award(p,xp_next(p.level),0)
                row=self.gains(p,level)['mana']
                self.assertEqual(row['gain'], f'+{amounts[level-1]-amounts[level-2]}')
                self.assertEqual(p.mana,p.max_mana)
                if cls=='mage':
                    row=self.gains(p,level)['spell_restore_mana_arcane_recovery']
                    self.assertEqual(row['gain'],f'+{RECOVERY[level-1]-RECOVERY[level-2]}')
                    self.assertEqual(row['unit'],'many')

    def test_multi_level_award_equals_individual_level_awards(self):
        p=self.player('mage');q=self.player('mage',pid='2')
        total=sum(xp_next(level) for level in range(1,21))
        self.g.award(p,total,0)
        for _ in range(20):self.g.award(q,xp_next(q.level),0)
        self.assertEqual((p.level,p.mana,p.max_mana,p.xp),(q.level,q.mana,q.max_mana,q.xp))
        a=lu.pending(p)['pending_level_ups'];b=lu.pending(q)['pending_level_ups']
        self.assertEqual([e['rows'] for e in a],[e['rows'] for e in b])
        self.assertEqual(sum(int(self.gains(p,n)['mana']['gain']) for n in range(2,22)),p.max_mana-40)

    def test_private_snapshot_book_feats_and_cache_use_current_values(self):
        p=self.player('mage',5)
        for level,mana,recovery in ((5,84,29),(6,96,31)):
            p.level=level;p.mana=mana
            s=p.public(self.clock(),private=True)
            self.assertEqual(s['max_mana'],mana)
            self.assertEqual(s['spell_profiles']['arcane_recovery']['restore_mana'],recovery)
            self.assertIn(f'+{recovery} many',s['spell_profiles']['arcane_recovery']['power_summary'])
            self.assertEqual(s['character_sheet']['caster']['recovery_amount'],recovery)
            self.assertTrue(any(f'+{recovery} many' in f['description'] for f in s['character_sheet']['caster']['features']))

    async def test_in_combat_recovery_at_intermediate_levels_is_real(self):
        for level,amount in ((2,22),(5,29),(9,38),(15,50),(55,120)):
            p=self.player('mage',level);p.mana=0;p.combat_until=self.clock()+20
            await self.g.cast_spell(p,'arcane_recovery')
            self.assertEqual(p.mana,amount)
            self.assertEqual(p.spell_cooldowns['arcane_recovery'],self.clock()+180)
            self.assertEqual(p.bonus_cooldown_until,self.clock()+3)

    async def test_recovery_stays_capped_at_missing_mana(self):
        p=self.player('mage',5);p.mana=p.max_mana-7
        await self.g.cast_spell(p,'arcane_recovery')
        self.assertEqual(p.mana,84)
        self.assertTrue(any('+7 many' in str(m) for m in p.ws.messages))

    async def test_leveling_does_not_clear_paid_recovery_cooldown(self):
        p=self.player('mage',5);p.mana=0
        await self.g.cast_spell(p,'arcane_recovery')
        until=p.spell_cooldowns['arcane_recovery']
        self.g.award(p,xp_next(5),0)
        self.assertEqual(p.spell_cooldowns['arcane_recovery'],until)
        p.mana=0
        await self.g.cast_spell(p,'arcane_recovery')
        self.assertEqual(p.mana,0)
        self.clock.advance(180)
        await self.g.cast_spell(p,'arcane_recovery')
        self.assertEqual(p.mana,31)

    def test_all_classes_old_save_ratio_preserved_exactly_once(self):
        for cls in ('mage','druid','ranger','knight'):
            for level in (1,5,9,10,19,55,85,95):
                p=self.player(cls,level);p.mastery={'focus':3}
                saved=copy.deepcopy(p.save_data());saved['mana_rules_version']=2
                old_max=dnd.legacy_base_mana(cls,level)+12
                for ratio in (0,.25,.5,1):
                    with self.subTest(cls=cls,level=level,ratio=ratio):
                        saved['mana']=old_max*ratio
                        q=self.g.load_player(p.id,p.name,p.ws,saved)
                        self.assertAlmostEqual(q.mana,q.max_mana*ratio)
                        self.assertEqual(q.mana_rules_version,3)
                        r=self.g.load_player(q.id,q.name,q.ws,copy.deepcopy(q.save_data()))
                        self.assertEqual(r.mana,q.mana)
                        self.assertEqual(r.inventory,q.inventory)
                        self.assertEqual(r.level,q.level)

    def test_migration_keeps_cooldowns_choices_xp_hp_and_gear(self):
        p=self.player('mage',7)
        p.hp=3;p.xp=13;p.mastery={'focus':2};p.spell_circle_choices={'magic_missile':1}
        p.spell_cooldowns={'arcane_recovery':self.clock()+71};p.bonus_cooldown_until=self.clock()+2
        p.mana_recovery_until=self.clock()+9
        saved=copy.deepcopy(p.save_data());saved['mana_rules_version']=2;saved['mana']=19
        q=self.g.load_player(p.id,p.name,p.ws,saved)
        for attr in ('spell_cooldowns','spell_circle_choices','bonus_cooldown_until','mana_recovery_until','equipment','inventory','hp','xp','gold','training_feats','mastery'):
            self.assertEqual(getattr(q,attr),saved[attr],attr)
        self.assertAlmostEqual(q.mana,19/68*115)

    def test_version_zero_migration_direct_to_new_pool(self):
        for cls,old_max in (('mage',65),('druid',58),('ranger',41),('knight',34)):
            p=self.player(cls,5);saved=copy.deepcopy(p.save_data())
            saved.pop('mana_rules_version');saved['mana']=old_max/2
            q=self.g.load_player(p.id,p.name,p.ws,saved)
            self.assertEqual(q.mana,q.max_mana/2)

    def test_version_one_migration_full_caster_and_ranger(self):
        for cls,level,old_max in (('mage',5,60),('druid',15,170),('ranger',5,35),('ranger',25,40)):
            p=self.player(cls,level);saved=copy.deepcopy(p.save_data())
            saved['mana_rules_version']=1;saved['mana']=old_max/2
            q=self.g.load_player(p.id,p.name,p.ws,saved)
            self.assertEqual(q.mana,q.max_mana/2)

    def test_current_save_does_not_refill_partial_mana(self):
        p=self.player('mage',8);p.mana=7.125
        for _ in range(5):
            p=self.g.load_player(p.id,p.name,p.ws,copy.deepcopy(p.save_data()))
            self.assertEqual(p.mana,7.125)

    def test_old_unclosed_receipts_keep_original_gains(self):
        p=self.player('mage',9);p.mana_rules_version=2
        self.g.award(p,xp_next(9),0)
        # Real 0.8.15 batches did not yet have this stamp.
        p.level_up_batches[0]['context'].pop('mana_rules_version')
        p._level_up_cache=None
        old=copy.deepcopy(lu.pending(p))
        self.assertEqual(self.gains(p,10)['mana']['gain'],'+80')
        self.assertEqual(self.gains(p,10)['spell_restore_mana_arcane_recovery']['gain'],'+20')
        q=self.g.load_player(p.id,p.name,p.ws,copy.deepcopy(p.save_data()))
        self.assertEqual(lu.pending(q),old)
        self.g.award(q,xp_next(10),0)
        self.assertEqual(len(q.level_up_batches),2)
        self.assertEqual(self.gains(q,10)['mana']['gain'],'+80')
        self.assertEqual(self.gains(q,11)['mana']['gain'],'+13')
        self.assertEqual(self.gains(q,11)['spell_restore_mana_arcane_recovery']['gain'],'+2')

    def test_migrating_does_not_create_retroactive_level_ups(self):
        p=self.player('druid',19);saved=copy.deepcopy(p.save_data());saved['mana_rules_version']=2
        q=self.g.load_player(p.id,p.name,p.ws,saved)
        self.assertEqual(lu.pending(q)['level_up_pending_count'],0)

    def test_db_roundtrip_saves_new_version_and_receipt_context(self):
        p=self.player('mage',5);saved=copy.deepcopy(p.save_data());saved['mana_rules_version']=2;saved['mana']=30
        q=self.g.load_player(p.id,p.name,p.ws,saved);self.account(q)
        reloaded=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0])
        self.assertEqual((reloaded['mana_rules_version'],reloaded['mana']),(3,42))
        self.g.award(q,xp_next(5),0)
        with self.g.db:self.g.save_player(q)
        encoded=json.loads(self.g.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0])
        r=self.g.load_player(q.id,q.name,q.ws,encoded)
        self.assertEqual(r.max_mana,96)
        self.assertEqual(lu.pending(r),lu.pending(q))
        self.assertEqual(r.level_up_batches[0]['context']['mana_rules_version'],3)

if __name__=='__main__':unittest.main()
