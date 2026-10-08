"""The public count exposes saved characters without touching identity or play state."""
from pathlib import Path
import sys
import unittest
from unittest.mock import AsyncMock, Mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp.test_utils import TestClient, TestServer
from server.google_auth import GoogleAuthService, GoogleIdentity
from server.server import create_app


class PublicStatsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.app = create_app(":memory:", google_auth_service=GoogleAuthService())
        self.game = self.app["game"]
        # HTTP count tests need the real database/routes, not a running world.
        self.app.cleanup_ctx.clear()
        self.client = TestClient(TestServer(self.app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.game.db.close()

    async def test_anonymous_count_is_read_only_and_contains_no_identity(self):
        before = tuple(self.game.db.iterdump())
        response = await self.client.get("/api/public-stats")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "application/json")
        self.assertEqual(await response.json(), {"characters_created": 0})
        self.assertEqual(response.headers["Cache-Control"], "public, max-age=60")
        self.assertEqual(response.headers["X-Robots-Tag"], "noindex, nofollow")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertNotIn("Set-Cookie", response.headers)
        self.assertEqual(tuple(self.game.db.iterdump()), before)

    async def test_all_saved_characters_count_including_offline_and_legacy(self):
        with self.game.db:
            self.game.db.executemany(
                "INSERT INTO google_accounts(subject,created_at) VALUES(?,0)",
                [("owner-one",), ("owner-two",)],
            )
            self.game.db.executemany(
                "INSERT INTO accounts(name,name_key,salt,password_hash,data) VALUES(?,?,X'00',X'00','{}')",
                [(f"Bohater {i}", f"bohater {i}") for i in range(23)],
            )
            self.game.db.executemany(
                "INSERT INTO google_characters VALUES(?,?,0)", [(1, 1), (1, 2), (2, 3)]
            )
        self.assertEqual(len(self.game.players), 0)
        # Neither a 20-entry ranking page, 3 linked saves nor 2 Google accounts.
        response = await self.client.get("/api/public-stats")
        self.assertEqual(await response.json(), {"characters_created": 23})

    async def test_successful_character_creation_updates_count_but_login_does_not(self):
        service = Mock(enabled=True, allowed_origin="http://localhost")
        service.peek_ticket.return_value = GoogleIdentity("new-owner")
        ws = Mock(closed=False, send_json=AsyncMock(), close=AsyncMock())
        await self.game.hello_google(ws, {
            "mode": "create", "name": "Nowy Bohater", "class_id": "knight", "ticket": "test-ticket"
        }, service, "test-binding", service.allowed_origin)
        self.assertEqual(service.consume_ticket.call_count, 1)
        response = await self.client.get("/api/public-stats")
        self.assertEqual(await response.json(), {"characters_created": 1})
        character_id = self.game.db.execute("SELECT id FROM accounts").fetchone()[0]
        await self.game.disconnect(ws)
        await self.game.hello_google(ws, {
            "mode": "select", "character_id": str(character_id), "ticket": "next-ticket"
        }, service, "test-binding", service.allowed_origin)
        self.assertEqual(service.consume_ticket.call_count, 2)
        response = await self.client.get("/api/public-stats")
        self.assertEqual(await response.json(), {"characters_created": 1})


if __name__ == "__main__":
    unittest.main()
