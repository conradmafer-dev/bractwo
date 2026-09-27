"""Deployment-only tests. Execute from repository root: python -m unittest discover -s tests -v"""
import asyncio
from contextlib import closing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from run import (Settings, StartupError, settings_from_env, exclusive_database,
                 backup_existing_database, graceful_shutdown, readiness)
from server.server import Game, create_app
from aiohttp.test_utils import TestClient, TestServer


class ConfigurationTests(unittest.TestCase):
    def test_default_local_settings(self):
        cfg = settings_from_env({})
        self.assertEqual(cfg.port, 8080)
        self.assertEqual(cfg.database.name, 'world.sqlite3')
        self.assertFalse(cfg.railway)

    def test_railway_port_and_mounted_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = settings_from_env({'PORT': '9191', 'RAILWAY_PROJECT_ID': 'qa',
                                     'RAILWAY_VOLUME_MOUNT_PATH': tmp})
            self.assertEqual(cfg.port, 9191)
            self.assertEqual(cfg.database, Path(tmp) / 'world.sqlite3')
            self.assertTrue(cfg.railway)

    def test_explicit_database_within_volume(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = settings_from_env({'RAILWAY_SERVICE_ID': 'qa',
                    'RAILWAY_VOLUME_MOUNT_PATH': tmp, 'BRACTWO_DB_PATH': tmp + '/saves/world.sqlite3'})
            self.assertEqual(cfg.database, Path(tmp) / 'saves/world.sqlite3')

    def test_railway_without_volume_is_rejected(self):
        with self.assertRaisesRegex(StartupError, 'Brak trwalego dysku'):
            settings_from_env({'RAILWAY_SERVICE_ID': 'qa'})

    def test_database_outside_volume_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(StartupError, 'na wolumenie'):
                settings_from_env({'RAILWAY_SERVICE_ID': 'qa',
                    'RAILWAY_VOLUME_MOUNT_PATH': tmp, 'BRACTWO_DB_PATH': '/tmp/unmounted.sqlite3'})

    def test_bad_port_is_rejected(self):
        for port in ('0', '-1', '65536', '', 'hello'):
            with self.subTest(port=port), self.assertRaises(StartupError):
                settings_from_env({'PORT': port})

    def test_in_memory_database_is_rejected(self):
        with self.assertRaises(StartupError):
            settings_from_env({'BRACTWO_DB_PATH': ':memory:'})

    def test_second_process_lock_is_rejected_and_released(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'world.sqlite3'
            with exclusive_database(db):
                with self.assertRaisesRegex(StartupError, 'juz uzywana'):
                    with exclusive_database(db):
                        self.fail('lock should reject second writer')
            with exclusive_database(db):
                pass


class BackupTests(unittest.TestCase):
    def test_new_world_requires_no_backup(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.sqlite3'
            self.assertIsNone(backup_existing_database(path))
            self.assertFalse(path.exists())

    def test_backup_preserves_saved_accounts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.sqlite3'
            game = Game(path)
            game.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',
                            (1, 'QA', 'qa', b'salt', b'hash', '{"level":10}'))
            game.db.commit()
            # Backup must include committed data still present in WAL.
            backup = backup_existing_database(path)
            self.assertIsNotNone(backup)
            with closing(sqlite3.connect(backup)) as snap:
                self.assertEqual(snap.execute('SELECT data FROM accounts WHERE id=1').fetchone()[0], '{"level":10}')
                self.assertEqual(snap.execute('PRAGMA integrity_check').fetchone(), ('ok',))
            game.db.close()

    def test_keep_only_five_startup_backups(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.sqlite3'
            game = Game(path); game.db.close()
            for _ in range(7):
                backup_existing_database(path)
            self.assertEqual(len(list((Path(tmp) / 'backups').glob('bractwo-*.sqlite3'))), 5)

    def test_foreign_database_is_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.sqlite3'
            with closing(sqlite3.connect(path)) as conn:
                conn.execute('CREATE TABLE unrelated (id INTEGER)'); conn.commit()
            before = path.read_bytes()
            with self.assertRaisesRegex(StartupError, 'nie jest rozpoznana baza'):
                backup_existing_database(path)
            self.assertEqual(before, path.read_bytes())

    def test_corrupt_file_is_not_modified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.sqlite3'; path.write_bytes(b'not a database')
            with self.assertRaises(StartupError): backup_existing_database(path)
            self.assertEqual(path.read_bytes(), b'not a database')

    def test_empty_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'world.sqlite3'; path.touch()
            with self.assertRaises(StartupError): backup_existing_database(path)
            self.assertEqual(path.stat().st_size, 0)


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.app = create_app(str(Path(self.temp.name) / 'world.sqlite3'))
        self.app.middlewares.append(readiness)
        self.app.on_shutdown.append(graceful_shutdown)
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.temp.cleanup()

    async def test_health_ranking_and_web_assets(self):
        response = await self.client.get('/health')
        self.assertEqual(response.status, 200)
        self.assertEqual((await response.json())['version'], '0.8.17')
        for path in ('/', '/ranking', '/game.js', '/runtime.js', '/atlas_map.js', '/level_up.js',
                     '/character_sheet.js', '/spell_vfx.js', '/assets/spells/magic_missile.svg'):
            with self.subTest(path=path):
                self.assertEqual((await self.client.get(path)).status, 200)

    async def test_health_rejects_stopped_simulation(self):
        task = self.app['game'].task
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task
        self.assertEqual((await self.client.get('/health')).status, 503)

    async def test_database_and_backup_are_not_public_assets(self):
        for path in ('/data/world.sqlite3', '/backups/world.sqlite3', '/run.py', '/server/server.py'):
            self.assertEqual((await self.client.get(path)).status, 404)

    async def test_websocket_is_closed_by_graceful_shutdown(self):
        ws = await self.client.ws_connect('/ws')
        await graceful_shutdown(self.app)
        msg = await ws.receive(timeout=4)
        self.assertIn(msg.type.name, ('CLOSE', 'CLOSED', 'CLOSING'))
        await ws.close()


if __name__ == '__main__':
    unittest.main()
