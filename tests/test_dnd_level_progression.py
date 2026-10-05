"""Native level thresholds, authoritative awards and lossless save migration."""
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from server import level_rules, level_up, dnd_content, caster_rules
from server.server import Game, Player, xp_next, ENEMY_TYPES, PVP_RULES


class ExperienceRules(unittest.TestCase):
    def test_official_cumulative_thresholds_and_both_sides_of_every_boundary(self):
        expected = (0, 300, 900, 2700, 6500, 14000, 23000, 34000,
                    48000, 64000, 85000, 100000, 120000, 140000,
                    165000, 195000, 225000, 265000, 305000, 355000)
        for level, total in enumerate(expected, 1):
            self.assertEqual(level_rules.xp_floor(level), total)
            self.assertEqual(level_rules.level_for_xp(total), level)
            if level > 1:
                self.assertEqual(level_rules.level_for_xp(total - 1), level - 1)
        self.assertEqual(xp_next(2), 600)
        self.assertEqual(level_rules.xp_floor(21), 405000)
        self.assertEqual(level_rules.level_for_xp(405000), 21)
        self.assertEqual(level_rules.level_for_xp(404999), 20)

    def test_awards_use_total_thresholds_and_retain_excess(self):
        p = Player('1', 'Awans', class_id='mage')
        Game.award(None, p, 299, 2)
        self.assertEqual((p.level, p.xp, p.gold), (1, 299, 2))
        Game.award(None, p, 1, 0)
        self.assertEqual((p.level, p.xp), (2, 0))
        Game.award(None, p, 601, 0)
        self.assertEqual((p.level, p.xp), (3, 1))
        self.assertEqual(p.max_mana, 140)
        self.assertEqual(p.max_hp, 20)
        state = p.public(0, private=True)
        self.assertEqual((state['xp_total'], state['xp_next_total']), (901, 2700))
        self.assertEqual((state['xp'], state['xp_next']), (1, 1800))

    def test_huge_multilevel_award_and_receipts_are_bounded(self):
        p = Player('1', 'Daleko')
        total = level_rules.xp_floor(1000000) + 17
        Game.award(None, p, total, 0)
        self.assertEqual((p.level, p.xp), (1000000, 17))
        self.assertEqual(len(p.level_up_batches), 1)
        self.assertEqual(p.level_up_batches[0]['ranges'], [[2, 1000000]])
        self.assertEqual(len(level_up.pending(p)['pending_level_ups']), 32)

    def test_world_and_class_milestones_use_the_same_numbering(self):
        self.assertEqual(PVP_RULES['min_level'], 2)
        self.assertEqual(dnd_content.circle_for('mage', 3), 2)
        self.assertEqual(dnd_content.circle_for('mage', 5), 3)
        self.assertEqual(dnd_content.circle_for('ranger', 5), 2)
        self.assertEqual(ENEMY_TYPES['dawn_headless_skeleton']['level'], 3)
        self.assertEqual(ENEMY_TYPES['dawn_headless_skeleton']['hp'], 64)
        self.assertEqual(ENEMY_TYPES['old_tower_archer']['hp'], 60)


class ExistingProgress(unittest.TestCase):
    def test_milestones_fractional_progress_and_idempotence(self):
        for old, new in ((1, 1), (5, 2), (10, 3), (15, 4), (20, 5), (95, 20), (150, 31)):
            saved = {'level': old, 'xp': 0, 'gold': 177, 'training_feats': {'tough': ''}}
            original = copy.deepcopy(saved)
            migrated = level_rules.migrate_saved(saved)
            self.assertEqual((migrated['level'], migrated['xp']), (new, 0))
            self.assertEqual(migrated['training_feats'], saved['training_feats'])
            self.assertEqual(saved, original)
            self.assertIs(level_rules.migrate_saved(migrated), migrated)
        # Original level1->5 costs430XP. Half of that becomes150/300XP.
        migrated = level_rules.migrate_saved({'level': 3, 'xp': 70})
        self.assertEqual((migrated['level'], migrated['xp']), (1, 150))

    def test_partial_growth_is_retained_then_absorbed_without_double_gains(self):
        p = Player('1', 'Migracja', class_id='mage', level=5, legacy_growth_level=23)
        self.assertEqual(p.max_hp, 35)
        self.assertEqual(p.max_mana, 303)
        self.assertEqual(caster_rules.recovery_amount(p), 66)
        self.assertAlmostEqual(p.base_speed, 100 + 90 * 22 / 102)
        level_up.record(p, 6, 6)
        receipt = level_up.receipt(p, p.level_up_batches[0], 6)
        hp_gain = next(row['gain'] for row in receipt['rows'] if row['id'] == 'hp')
        self.assertEqual(hp_gain, '+3')
        p.level = 6
        fresh = Player('2', 'Nowa', class_id='mage', level=6)
        self.assertEqual((p.max_hp, p.max_mana, p.speed), (fresh.max_hp, fresh.max_mana, fresh.speed))

    def test_old_receipt_history_and_current_choices_survive(self):
        old = {'level': 23, 'xp': 80, 'training_feats': {'tough': ''},
               'mastery': {}, 'level_up_batches': [{'id': 'old', 'ranges': [[20, 23]], 'context': {}}]}
        new = level_rules.migrate_saved(old)
        self.assertEqual(new['legacy_level_up_batches'], old['level_up_batches'])
        self.assertEqual(new['level_up_batches'], [])
        self.assertEqual(new['training_feats'], old['training_feats'])
        self.assertEqual(new['level_migration_notice'], {'old_level': 23, 'level': 5})

    def test_database_backup_is_atomic_and_migration_runs_only_once(self):
        db = sqlite3.connect(':memory:')
        db.execute('CREATE TABLE accounts(id INTEGER PRIMARY KEY, data TEXT)')
        originals = [json.dumps({'level': 23, 'xp': 90}), json.dumps({'level': 10, 'xp': 0})]
        db.executemany('INSERT INTO accounts VALUES(?,?)', enumerate(originals, 1))
        db.commit()
        level_rules.migrate_database(db)
        first = db.execute('SELECT data FROM accounts ORDER BY id').fetchall()
        self.assertEqual([json.loads(r[0])['level'] for r in first], [5, 3])
        self.assertEqual([r[0] for r in db.execute('SELECT data FROM level_migration_backups ORDER BY player_id')], originals)
        level_rules.migrate_database(db)
        self.assertEqual(db.execute('SELECT data FROM accounts ORDER BY id').fetchall(), first)
        self.assertEqual(db.execute('SELECT count(*) FROM level_migration_backups').fetchone()[0], 2)
        # A later invalid save aborts the complete transaction, including any
        # earlier row's converted JSON and backup insertion.
        db.execute('DELETE FROM accounts')
        db.execute('DELETE FROM level_migration_backups')
        db.executemany('INSERT INTO accounts VALUES(?,?)', [(1, originals[0]), (2, '{broken')])
        db.commit()
        with self.assertRaises(json.JSONDecodeError):
            level_rules.migrate_database(db)
        self.assertEqual(db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0], originals[0])
        self.assertEqual(db.execute('SELECT count(*) FROM level_migration_backups').fetchone()[0], 0)
        db.close()

    def test_startup_migrates_offline_ranking_and_login_keeps_equipment_and_resources(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'world.db'
            game = Game(path)
            p = Player('1', 'Stara', class_id='mage', class_chosen=True, level=5, legacy_growth_level=23)
            game.starter(p)
            p.hp = 17
            p.mana = 101
            saved = p.save_data()
            saved.update(level=23, xp=100)
            saved.pop('level_rules_version')
            saved.pop('legacy_growth_level')
            game.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)', (1, 'Stara', 'stara', b'salt', b'hash', json.dumps(saved)))
            game.db.commit()
            game.db.close()
            restarted = Game(path)
            self.assertEqual(restarted.ranking()['ranking'][0]['level'], 5)
            encoded = restarted.db.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0]
            loaded = restarted.load_player('1', 'Stara', None, json.loads(encoded))
            self.assertEqual((loaded.level, loaded.hp, loaded.mana), (5, 17, 101))
            self.assertEqual((loaded.max_hp, loaded.max_mana), (35, 303))
            self.assertEqual(loaded.equipment, p.equipment)
            self.assertEqual([i['uid'] for i in loaded.inventory], [i['uid'] for i in p.inventory])
            again = restarted.load_player('1', 'Stara', None, loaded.save_data())
            self.assertEqual((again.level, again.xp, again.max_hp, again.max_mana), (loaded.level, loaded.xp, loaded.max_hp, loaded.max_mana))
            restarted.db.close()


if __name__ == '__main__':
    unittest.main()
