"""Verify deterministic build assets and aiohttp content negotiation."""
import gzip
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / '.qa-python').is_dir():
    sys.path.insert(0, str(ROOT / '.qa-python'))

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from server.server import _search_response_headers, _static_encoding
from tools.precompress_web import precompress_web


class PrecompressWebTests(unittest.TestCase):
    def test_sidecars_are_deterministic_and_only_written_when_smaller(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            assets = {
                'app.js': b'const title = "Bractwo";\n' * 100,
                'nested/site.css': b'body { color: white; }\n' * 100,
                'icons/logo.svg': b'<svg><path d="M0 0 L10 10"/></svg>\n' * 100,
            }
            for name, source in assets.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(source)
            (root / 'tiny.js').write_bytes(b'1;')
            (root / 'tiny.js.gz').write_bytes(b'obsolete sidecar')
            (root / 'image.png').write_bytes(b'compressible binary fixture' * 100)

            count, original_bytes, gzip_bytes = precompress_web(root)
            self.assertEqual(count, len(assets))
            self.assertEqual(original_bytes, sum(map(len, assets.values())))
            self.assertLess(gzip_bytes, original_bytes)
            first = {name: (root / (name + '.gz')).read_bytes() for name in assets}
            precompress_web(root)
            for name, source in assets.items():
                self.assertEqual((root / name).read_bytes(), source)
                self.assertEqual((root / (name + '.gz')).read_bytes(), first[name])
                self.assertEqual(gzip.decompress(first[name]), source)
            self.assertFalse((root / 'tiny.js.gz').exists())
            self.assertFalse((root / 'image.png.gz').exists())


class PrecompressedHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_static_and_file_response_negotiate_gzip_and_identity(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            source = b'/* static asset content */\n' * 100
            for name in ('app.js', 'site.css', 'logo.svg'):
                (root / name).write_bytes(source)
            precompress_web(root)

            async def file_response(request):
                return web.FileResponse(root / 'app.js')

            app = web.Application(middlewares=[_static_encoding])
            app.on_response_prepare.append(_search_response_headers)
            app.router.add_get('/file.js', file_response)
            app.router.add_static('/static/', root)
            async with TestClient(TestServer(app), auto_decompress=False) as client:
                for route, content_types in {
                    '/file.js': {'application/javascript', 'text/javascript'},
                    '/static/app.js': {'application/javascript', 'text/javascript'},
                    '/static/site.css': {'text/css'},
                    '/static/logo.svg': {'image/svg+xml'},
                }.items():
                    with self.subTest(route=route):
                        response = await client.get(route, headers={'Accept-Encoding': 'gzip'})
                        self.assertEqual(response.status, 200)
                        self.assertEqual(response.headers['Content-Encoding'], 'gzip')
                        self.assertIn('Accept-Encoding', response.headers.get('Vary', ''))
                        self.assertIn(response.content_type, content_types)
                        compressed = await response.read()
                        self.assertLess(len(compressed), len(source))
                        self.assertEqual(gzip.decompress(compressed), source)

                        response = await client.get(route, headers={'Accept-Encoding': 'identity'})
                        self.assertEqual(response.status, 200)
                        self.assertNotIn('Content-Encoding', response.headers)
                        self.assertIn('Accept-Encoding', response.headers.get('Vary', ''))
                        self.assertIn(response.content_type, content_types)
                        self.assertEqual(await response.read(), source)
                        identity_etag = response.headers['ETag']

                        for encoding in ('gzip;q=0, identity;q=1', 'gzip;q=0, *;q=1', 'gzip;q=invalid'):
                            rejected = await client.get(route, headers={'Accept-Encoding': encoding})
                            self.assertEqual(rejected.status, 200)
                            self.assertNotIn('Content-Encoding', rejected.headers)
                            self.assertEqual(await rejected.read(), source)

                        wildcard = await client.get(route, headers={'Accept-Encoding': '*'})
                        self.assertEqual(wildcard.headers['Content-Encoding'], 'gzip')
                        self.assertEqual(gzip.decompress(await wildcard.read()), source)

                        headers = {'Accept-Encoding': 'gzip;q=0, identity;q=1'}
                        not_modified = await client.get(route, headers={**headers, 'If-None-Match': identity_etag})
                        self.assertEqual(not_modified.status, 304)
                        self.assertIn('Accept-Encoding', not_modified.headers.get('Vary', ''))
                        self.assertEqual(await not_modified.read(), b'')
                        head = await client.head(route, headers=headers)
                        self.assertEqual(head.status, 200)
                        self.assertNotIn('Content-Encoding', head.headers)
                        self.assertEqual(int(head.headers['Content-Length']), len(source))
                        self.assertEqual(await head.read(), b'')
                        partial = await client.get(route, headers={**headers, 'Range': 'bytes=0-9'})
                        self.assertEqual(partial.status, 206)
                        self.assertEqual(partial.headers['Content-Range'], f'bytes 0-9/{len(source)}')
                        self.assertEqual(await partial.read(), source[:10])


if __name__ == '__main__':
    unittest.main()
