"""Comment API authorization, persisted posting limits and safe public output."""
import asyncio
from datetime import datetime
import json
from pathlib import Path
import secrets
import sqlite3
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer, make_mocked_request
from multidict import CIMultiDict
from server.comments import CommentError, CommentService, MAX_BODY_BYTES, SESSION_TTL, register_routes
from server.google_auth import GoogleAuthService, GoogleIdentity, register_routes as register_auth
from server.profanity import contains_profanity


ORIGIN = "http://localhost"
CLIENT_ID = "comments-test.apps.googleusercontent.com"
COMMENT_HEADERS = {"Origin": ORIGIN, "X-Bractwo-Comments": "1"}
AUTH_HEADERS = {"Origin": ORIGIN, "X-Bractwo-Auth": "1"}


class Clock:
    def __init__(self):
        self.value = 1790856000.0

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


def database(path=":memory:"):
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript("""
      CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS google_accounts(id INTEGER PRIMARY KEY,subject TEXT UNIQUE NOT NULL,created_at REAL NOT NULL);
      CREATE TABLE IF NOT EXISTS google_characters(google_account_id INTEGER NOT NULL REFERENCES google_accounts(id),
        character_id INTEGER UNIQUE NOT NULL REFERENCES accounts(id),linked_at REAL NOT NULL);
      INSERT OR IGNORE INTO google_accounts VALUES(1,'account-one',0),(2,'account-two',0);
      INSERT OR IGNORE INTO accounts VALUES(1,'Rycerz'),(2,'Druid'),(3,'Łowca'),(4,'Kurwa');
    """)
    with connection:
        for owner, character in ((1, 1), (1, 2), (2, 3), (1, 4)):
            connection.execute("INSERT OR IGNORE INTO google_characters VALUES(?,?,0)", (owner, character))
    return connection


class CommentsHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.db = database()
        self.clock = Clock()
        self.claims = {}
        self.auth = GoogleAuthService(CLIENT_ID, ORIGIN, verifier=self.claims.__getitem__,
                                      clock=self.clock, wall_clock=self.clock)
        self.service = CommentService(self.db, ORIGIN, clock=self.clock, wall_clock=self.clock)
        app = web.Application(client_max_size=2048)
        register_auth(app, self.auth, on_verified=self.service.on_verified)
        register_routes(app, self.service)
        self.client = TestClient(TestServer(app))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.db.close()

    async def login(self, subject="account-one", *, valid=True):
        start = await self.client.post("/auth/google/start", json={}, headers=AUTH_HEADERS)
        self.assertEqual(start.status, 200)
        challenge = await start.json()
        credential = "fixture." + secrets.token_urlsafe(24) + ".fixture"
        self.claims[credential] = {"aud": CLIENT_ID, "iss": "https://accounts.google.com", "sub": subject,
                                  "nonce": challenge["nonce"] if valid else "x" * 43,
                                  "iat": self.clock() - 1, "exp": self.clock() + 600}
        response = await self.client.post("/auth/google/verify", headers=AUTH_HEADERS,
                                          json={"challenge": challenge["challenge"], "credential": credential})
        self.assertEqual(response.status, 200 if valid else 401)
        return response

    async def post(self, body="Dobra przygoda w świecie fantasy.", character_id="1", **extra):
        return await self.client.post("/api/comments", headers=COMMENT_HEADERS,
                                      json={"character_id": character_id, "body": body, **extra})

    async def test_public_read_requires_no_login_but_post_requires_verified_cookie(self):
        response = await self.client.get("/api/comments")
        self.assertEqual(response.status, 200)
        self.assertEqual(await response.json(), {"items": [], "next_cursor": None})
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["Vary"], "Cookie")
        self.assertIn("noindex", response.headers["X-Robots-Tag"])
        session = await self.client.get("/api/comments/session")
        self.assertEqual(await session.json(), {"authenticated": False, "characters": [], "max_length": 1000})
        for cookie in (None, "x" * 43):
            headers = dict(COMMENT_HEADERS)
            if cookie:
                headers["Cookie"] = self.service.cookie_name + "=" + cookie
            denied = await self.client.post("/api/comments", headers=headers,
                                            json={"character_id": "1", "body": "Nieautoryzowany wpis."})
            self.assertEqual(denied.status, 401)
        failed = await self.login(valid=False)
        self.assertNotIn(self.service.cookie_name, failed.cookies)
        self.assertEqual(self.service._sessions, {})
        verified = await self.login()
        self.assertIn(self.service.cookie_name, verified.cookies)
        token = verified.cookies[self.service.cookie_name].value
        self.assertNotIn(token, repr(self.service._sessions))
        session = await self.client.get("/api/comments/session")
        payload = await session.json()
        self.assertTrue(payload["authenticated"])
        self.assertEqual([item["id"] for item in payload["characters"]], ["1", "2", "4"])
        self.assertNotIn("Kurwa", json.dumps(payload))

    async def test_comment_session_is_independent_of_consumed_game_ticket(self):
        verified = await self.login()
        payload = await verified.json()
        cookie = self.client.session.cookie_jar.filter_cookies(self.client.make_url("/"))[self.auth.cookie_name].value
        self.auth.consume_ticket(payload["ticket"], cookie)
        posted = await self.post()
        self.assertEqual(posted.status, 201)
        self.clock.advance(301)
        session = await self.client.get("/api/comments/session")
        self.assertTrue((await session.json())["authenticated"])

    async def test_author_identity_ownership_delete_and_plain_text_output(self):
        await self.login()
        denied = await self.post(character_id="3")
        self.assertEqual(denied.status, 403)
        source = '<script>alert("przygoda")</script> & dobra gra'
        posted = await self.post(source, author="Cudzy autor", email="untrusted@example.test", google_account_id=2)
        self.assertEqual(posted.status, 201)
        item = (await posted.json())["item"]
        self.assertEqual(item["author"], "Rycerz")
        self.assertEqual(item["body"], source)
        self.assertTrue(item["can_delete"])
        self.assertTrue(item["created_at"].endswith("Z"))
        datetime.fromisoformat(item["created_at"].replace("Z", "+00:00"))
        rendered = self.service.render_public_list()
        self.assertIn("&lt;script&gt;", rendered)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("button", rendered)
        own_list = await self.client.get("/api/comments")
        self.assertTrue((await own_list.json())["items"][0]["can_delete"])
        await self.login("account-two")
        other_list = await self.client.get("/api/comments")
        self.assertFalse((await other_list.json())["items"][0]["can_delete"])
        denied = await self.client.delete("/api/comments/" + item["id"], headers=COMMENT_HEADERS)
        self.assertEqual(denied.status, 403)
        await self.login()
        deleted = await self.client.delete("/api/comments/" + item["id"], headers=COMMENT_HEADERS)
        self.assertEqual(deleted.status, 200)
        self.assertEqual(await deleted.json(), {"deleted": True})
        self.assertEqual(self.service.list_comments()["items"], [])
        duplicate = await self.post(source)
        self.assertEqual(duplicate.status, 409)

    async def test_mutations_reject_cross_site_missing_duplicate_headers_and_wrong_content_type(self):
        await self.login()
        mutations = [("post", "/api/comments"), ("delete", "/api/comments/1"), ("post", "/api/comments/logout")]
        invalid = [{}, {"Origin": ORIGIN}, {"X-Bractwo-Comments": "1"},
                   {**COMMENT_HEADERS, "Origin": "https://evil.example"},
                   {**COMMENT_HEADERS, "Origin": ORIGIN + ".evil.example"},
                   {**COMMENT_HEADERS, "Sec-Fetch-Site": "cross-site"},
                   {**COMMENT_HEADERS, "X-Bractwo-Comments": "0"},
                   CIMultiDict([("Origin", ORIGIN), ("Origin", ORIGIN), ("X-Bractwo-Comments", "1")])]
        for method, path in mutations:
            for headers in invalid:
                with self.subTest(method=method, headers=headers):
                    response = await self.client.request(method, path, headers=headers, json={})
                    self.assertEqual(response.status, 403)
                    self.assertEqual((await response.json())["error"], "invalid_origin")
        wrong_type = await self.client.post("/api/comments", headers=COMMENT_HEADERS, data="{}")
        self.assertEqual(wrong_type.status, 415)
        self.assertEqual(self.service.list_comments()["items"], [])

    async def test_body_validation_profanity_control_characters_and_bounded_stream(self):
        await self.login()
        for value in (None, 123, [], "  ", "a", "A" * 1001, "tekst\x00dalej", "tekst\ud800", "K.U.R.W.A", "f.u.c.k"):
            with self.subTest(value=repr(value)[:60]):
                response = await self.post(value)
                self.assertEqual(response.status, 400)
        for character_id in (1, True, "0", "1 OR 1=1", "9999999999999999999999999"):
            response = await self.post(character_id=character_id)
            self.assertEqual(response.status, 400)
        response = await self.client.post("/api/comments", headers={**COMMENT_HEADERS, "Content-Type": "application/json"},
                                          data=b'{"body":NaN}')
        self.assertEqual(response.status, 400)
        async def huge_body():
            yield b"x" * 9000
            yield b"x" * 9000
        oversized = await self.client.post("/api/comments", headers={**COMMENT_HEADERS, "Content-Type": "application/json"},
                                           data=huge_body())
        self.assertEqual(oversized.status, 413)
        oversized = await self.client.post("/api/comments", headers={**COMMENT_HEADERS, "Content-Type": "application/json"},
                                           data=b"x" * (MAX_BODY_BYTES + 1))
        self.assertEqual(oversized.status, 413)
        source = "  Słuchaj, kucharz z Scunthorpe gra.\r\nDobry\u200b wieczór!  "
        posted = await self.post(source)
        self.assertEqual(posted.status, 201)
        self.assertEqual((await posted.json())["item"]["body"], "Słuchaj, kucharz z Scunthorpe gra.\nDobry wieczór!")

    async def test_old_vulgar_character_uses_safe_public_name(self):
        await self.login()
        posted = await self.post("Przygoda bardzo mi się podoba.", character_id="4")
        self.assertEqual(posted.status, 201)
        self.assertEqual((await posted.json())["item"]["author"], "Gracz Bractwa Krain")

    async def test_logout_rotation_expiry_and_cookie_flags(self):
        verified = await self.login()
        first_cookie = verified.cookies[self.service.cookie_name]
        self.assertTrue(first_cookie["httponly"])
        self.assertEqual(first_cookie["samesite"], "Strict")
        self.assertEqual(first_cookie["path"], "/")
        self.assertEqual(int(first_cookie["max-age"]), SESSION_TTL)
        self.assertFalse(first_cookie["secure"])
        verified_again = await self.login()
        second_token = verified_again.cookies[self.service.cookie_name].value
        self.assertNotEqual(first_cookie.value, second_token)
        old_request = make_mocked_request("GET", "/api/comments/session",
                                          headers={"Cookie": self.service.cookie_name + "=" + first_cookie.value})
        self.assertIsNone(self.service.account_for_request(old_request))
        logged_out = await self.client.post("/api/comments/logout", headers=COMMENT_HEADERS, json={})
        self.assertEqual(logged_out.status, 200)
        self.assertEqual(logged_out.cookies[self.service.cookie_name]["max-age"], "0")
        replay = await self.client.post("/api/comments", headers={**COMMENT_HEADERS, "Cookie": self.service.cookie_name + "=" + second_token},
                                        json={"character_id": "1", "body": "Próba po wylogowaniu"})
        self.assertEqual(replay.status, 401)
        await self.login()
        self.clock.advance(SESSION_TTL)
        expired = await self.client.get("/api/comments/session")
        self.assertFalse((await expired.json())["authenticated"])

    async def test_pagination_is_stable_with_new_posts_and_hides_old_vulgar_rows(self):
        with self.db:
            for number in range(25):
                self.db.execute("INSERT INTO public_comments(google_account_id,character_id,author,body,created_at) VALUES(1,1,?,?,?)",
                                ("Rycerz", "Wspomnienie z wyprawy numer " + str(number), self.clock()))
            self.db.execute("INSERT INTO public_comments(google_account_id,character_id,author,body,created_at) VALUES(1,1,'Rycerz','kurwa',?)", (self.clock(),))
        first = await self.client.get("/api/comments")
        page = await first.json()
        self.assertEqual([item["id"] for item in page["items"]], [str(number) for number in range(25, 5, -1)])
        self.assertTrue(all(not item["can_delete"] for item in page["items"]))
        self.assertEqual(page["next_cursor"], "6")
        self.assertNotIn("kurwa", self.service.render_public_list())
        await self.login()
        self.assertEqual((await self.post()).status, 201)
        second = await self.client.get("/api/comments", params={"cursor": page["next_cursor"]})
        rest = await second.json()
        self.assertEqual([item["id"] for item in rest["items"]], ["5", "4", "3", "2", "1"])
        self.assertIsNone(rest["next_cursor"])
        for query in ({"cursor": "1 OR 1=1"}, {"cursor": "-1"}, {"limit": "21"}, {"limit": "0"}):
            response = await self.client.get("/api/comments", params=query)
            self.assertEqual(response.status, 400)

    async def test_parallel_posts_and_character_switch_cannot_bypass_account_cooldown(self):
        await self.login()
        results = await asyncio.gather(self.post("Pierwsza dobra wyprawa."), self.post("Druga dobra wyprawa.", "2"))
        self.assertEqual(sorted(response.status for response in results), [201, 429])
        limited = next(response for response in results if response.status == 429)
        self.assertEqual(limited.headers["Retry-After"], "30")
        self.assertEqual((await limited.json())["retry_after"], 30)
        self.assertEqual(len(self.service.list_comments()["items"]), 1)


class CommentStorageTests(unittest.TestCase):
    def test_public_reads_cache_moderation_and_cooldown_precedes_filtering(self):
        db = database()
        clock = Clock()
        with patch("server.comments.contains_profanity", wraps=contains_profanity) as moderation:
            service = CommentService(db, ORIGIN, clock=clock, wall_clock=clock)
            try:
                service.create_comment(1, "1", "Spokojna przygoda w krainie fantasy.")
                calls = moderation.call_count
                self.assertGreater(calls, 0)
                service.list_comments()
                service.render_public_list()
                self.assertEqual(moderation.call_count, calls)
                with self.assertRaises(CommentError) as error:
                    service.create_comment(1, "2", "Kolejna wyprawa inną postacią.")
                self.assertEqual(error.exception.status, 429)
                self.assertEqual(moderation.call_count, calls)
                with db:
                    db.execute("INSERT INTO public_comments(google_account_id,character_id,author,body,created_at) VALUES(1,1,'Rycerz','kurwa',?)", (clock(),))
                self.assertEqual(len(service.list_comments()["items"]), 1)
                self.assertEqual(moderation.call_count, calls + 1)
                service.render_public_list()
                self.assertEqual(moderation.call_count, calls + 1)
            finally:
                service.close()
                db.close()

    def test_comments_duplicate_cooldown_and_hourly_budget_survive_restart_and_deletion(self):
        with TemporaryDirectory() as directory:
            path = str(Path(directory) / "world.sqlite3")
            clock = Clock()
            db = database(path)
            service = CommentService(db, ORIGIN, clock=clock, wall_clock=clock)
            first = service.create_comment(1, "1", "Pierwsze wrażenie z gry.")
            service.close()
            db.close()
            db = database(path)
            service = CommentService(db, ORIGIN, clock=clock, wall_clock=clock)
            try:
                self.assertEqual(service.list_comments()["items"][0]["id"], first["id"])
                self.assertEqual(service._sessions, {})
                service.delete_comment(1, first["id"])
                for body, expected in (("PIERWSZE   WRAŻENIE Z GRY.", "duplicate"), ("Nowe wrażenie.", "rate_limited")):
                    with self.assertRaises(CommentError) as error:
                        service.create_comment(1, "2", body)
                    self.assertEqual(error.exception.code, expected)
                started = clock()
                for number in range(19):
                    clock.advance(31)
                    item = service.create_comment(1, "2", "Opinia z kolejnej wyprawy numer " + str(number))
                    service.delete_comment(1, item["id"])
                clock.advance(31)
                with self.assertRaises(CommentError) as error:
                    service.create_comment(1, "1", "Kolejna spokojna wyprawa.")
                self.assertEqual(error.exception.status, 429)
                self.assertGreater(error.exception.retry_after, 30)
                clock.value = started + 3601
                service.create_comment(1, "1", "Kolejna spokojna wyprawa.")
                self.assertEqual(len(service.list_comments()["items"]), 1)
            finally:
                service.close()
                db.close()

    def test_secure_sessions_are_bounded_hashed_and_expire(self):
        db = database()
        clock = Clock()
        service = CommentService(db, "https://bractwo.example", clock=clock, wall_clock=clock, max_sessions=2)
        try:
            cookies = []
            for subject in ("account-one", "account-two", "account-three"):
                request = make_mocked_request("POST", "/auth/google/verify")
                response = web.Response()
                service.on_verified(request, response, GoogleIdentity(subject))
                cookie = response.cookies[service.cookie_name]
                cookies.append(cookie.value)
                self.assertEqual(service.cookie_name, "__Host-bractwo_comments")
                self.assertTrue(cookie["secure"])
                self.assertTrue(cookie["httponly"])
                self.assertEqual(cookie["samesite"], "Strict")
                self.assertFalse(cookie["domain"])
                self.assertNotIn(cookie.value, repr(service._sessions))
            self.assertEqual(len(service._sessions), 2)
            first = make_mocked_request("GET", "/api/comments/session", headers={"Cookie": service.cookie_name + "=" + cookies[0]})
            self.assertIsNone(service.account_for_request(first))
            last = make_mocked_request("GET", "/api/comments/session", headers={"Cookie": service.cookie_name + "=" + cookies[-1]})
            self.assertIsNotNone(service.account_for_request(last))
            clock.advance(SESSION_TTL)
            self.assertIsNone(service.account_for_request(last))
        finally:
            service.close()
            db.close()


if __name__ == "__main__":
    unittest.main()
