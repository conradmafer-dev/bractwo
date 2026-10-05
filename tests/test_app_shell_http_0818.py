"""HTTP contract for the installable application shell (isolated memory DB)."""
import json
from pathlib import Path
import struct
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / '.qa-python').is_dir():
    sys.path.insert(0, str(ROOT / '.qa-python'))

from aiohttp.test_utils import TestClient, TestServer
from server.server import create_app


class AppShellHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = TestClient(TestServer(create_app(':memory:')))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()

    async def test_manifest_and_linked_icon_dimensions(self):
        response = await self.client.get('/manifest.webmanifest')
        self.assertEqual(response.status, 200)
        self.assertIn(response.content_type, ('application/manifest+json', 'application/json'))
        manifest = json.loads(await response.text())
        self.assertEqual(manifest['display'], 'standalone')
        self.assertEqual(manifest['scope'], '/')
        self.assertEqual(manifest['start_url'], '/')
        self.assertEqual({icon['sizes'] for icon in manifest['icons']}, {'192x192', '512x512'})
        for icon in manifest['icons']:
            result = await self.client.get(icon['src'])
            self.assertEqual(result.status, 200)
            self.assertEqual(result.content_type, 'image/png')
            data = await result.read()
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            width, height = struct.unpack('>II', data[16:24])
            self.assertEqual(f'{width}x{height}', icon['sizes'])

    async def test_shell_and_rest_routes_have_correct_content_types(self):
        for route, content_types in {
            '/app_shell.js': ('application/javascript', 'text/javascript'),
            '/app_shell.css': ('text/css',), '/rest_ui.js': ('application/javascript', 'text/javascript'),
            '/rest_ui.css': ('text/css',), '/offline.html': ('text/html',),
            '/circle_spell_ui.js': ('application/javascript', 'text/javascript'),
            '/circle_vfx.js': ('application/javascript', 'text/javascript'),
            '/icons/apple-touch-icon.png': ('image/png',),
        }.items():
            with self.subTest(route=route):
                response = await self.client.get(route)
                self.assertEqual(response.status, 200)
                self.assertIn(response.content_type, content_types)
                self.assertTrue(await response.read())

    async def test_service_worker_is_revalidated_and_served_at_root(self):
        response = await self.client.get('/sw.js')
        self.assertEqual(response.status, 200)
        self.assertIn(response.content_type, ('application/javascript', 'text/javascript'))
        self.assertTrue(any(value in response.headers.get('Cache-Control', '') for value in ('no-cache', 'no-store', 'max-age=0')))
        self.assertIn('offline.html', await response.text())

    async def test_auth_page_links_manifest_and_current_shell(self):
        response = await self.client.get('/')
        self.assertEqual(response.status, 200)
        html = await response.text()
        for asset in ('manifest.webmanifest', 'app_shell.js', 'app_shell.css', 'rest_ui.js', 'rest_ui.css', 'apple-touch-icon.png'):
            self.assertIn(asset, html)
        health = await self.client.get('/health')
        self.assertEqual(health.status, 200)
        self.assertIn(health.content_type, ('application/json',))
        self.assertEqual((await health.json())['opening_balance_revision'], 1)


if __name__ == '__main__':
    unittest.main()
