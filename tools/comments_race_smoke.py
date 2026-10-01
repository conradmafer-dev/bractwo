"""Check comments/Google auth races in Chromium with controlled HTTP responses.

Run: python tools/comments_race_smoke.py

Uses the real landing markup and frontend scripts with a fake Google SDK and
in-memory API fixtures. Every browser request is intercepted; no server, real
Google credentials, production domain, or external network is used.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path
import re
import shutil

from playwright.async_api import async_playwright, expect


WEB = Path(__file__).resolve().parents[1] / "web"
ORIGIN = "http://comments.local"
CHARACTER = {"id": 7, "name": "Rycerz", "class_id": "knight", "level": 1}
SDK_FIXTURE = """
<script src="/google_auth.js"></script><script src="/comments.js"></script>
<script>
window.google = {accounts: {id: {
  initialize(options) { window.__googleOptions = options; },
  renderButton(container) {
    const button = document.createElement('button');
    button.id = 'fakeGoogle'; button.textContent = 'Google test';
    button.onclick = () => window.__googleOptions.callback({credential: 'fixture.credential.fixture'});
    container.append(button);
  },
  cancel() {}, disableAutoSelect() {}
}}};
window.__auth = BractwoGoogleAuth.mount({
  server: 'ws://comments.local/ws', canStart: () => true, connect() {}
});
</script>
"""


async def main():
    html = re.sub(r"<script\b[^>]*>.*?</script>", "", (WEB / "index.html").read_text(), flags=re.S)
    html = html.replace("</body>", SDK_FIXTURE + "</body>")
    state = {
        "auth": True,
        "items": [{"id": 1, "author": '<img src=x onerror="alert(1)">',
                   "body": "<script>alert(2)</script>", "created_at": "2026-10-01T12:00:00Z"}],
        "calls": [], "fail_list": False, "fail_logout": False,
        "session_gate": None, "verify_gate": None, "logout_gate": None,
    }

    def call_count(path):
        return sum(request_path == path for _, request_path in state["calls"])

    def is_request(path):
        return lambda request: request.url == ORIGIN + path

    async with async_playwright() as playwright:
        executable = shutil.which("chromium") or shutil.which("chromium-browser")
        browser = await playwright.chromium.launch(
            **({"executable_path": executable} if executable else {}),
            headless=True, args=["--no-sandbox"],
        )
        page = await browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))

        async def handle(route):
            request = route.request
            if not request.url.startswith(ORIGIN + "/"):
                await route.fulfill(status=404)
                return
            path = request.url.removeprefix(ORIGIN)
            state["calls"].append((request.method, path))
            if path == "/":
                await route.fulfill(content_type="text/html", body=html)
            elif path == "/api/comments/session":
                response = {"authenticated": state["auth"], "max_length": 1000,
                            "characters": [CHARACTER] if state["auth"] else []}
                gate, state["session_gate"] = state["session_gate"], None
                if gate:
                    await gate.wait()
                await route.fulfill(json=response)
            elif path == "/api/comments/logout":
                assert request.headers["x-bractwo-comments"] == "1"
                assert json.loads(request.post_data) == {}
                if state["logout_gate"]:
                    await state["logout_gate"].wait()
                if state["fail_logout"]:
                    await route.fulfill(status=503, json={"message": "Wylogowanie chwilowo niedostępne"})
                else:
                    state["auth"] = False
                    await route.fulfill(status=204)
            elif path == "/auth/google/config":
                await route.fulfill(json={"enabled": True, "client_id": "fixture.apps.googleusercontent.com"})
            elif path == "/auth/google/start":
                await route.fulfill(json={"challenge": "challenge", "nonce": "nonce", "expires_in": 300})
            elif path == "/auth/google/verify":
                if state["verify_gate"]:
                    await state["verify_gate"].wait()
                state["auth"] = True
                await route.fulfill(json={"ticket": "ticket", "expires_in": 300,
                                          "account": {"characters": [CHARACTER]}})
            elif path == "/api/comments" and request.method == "GET":
                if state["fail_list"]:
                    await route.fulfill(status=503, json={"message": "Lista chwilowo niedostępna"})
                else:
                    await route.fulfill(json={"items": [dict(item, can_delete=state["auth"])
                                                         for item in state["items"]], "next_cursor": None})
            elif path == "/api/comments" and request.method == "POST":
                assert request.headers["x-bractwo-comments"] == "1"
                data = json.loads(request.post_data)
                state["items"].insert(0, {"id": 2, "author": "Rycerz", "body": data["body"],
                                          "created_at": "2026-10-01T12:01:00Z", "can_delete": True})
                await route.fulfill(status=201, json=state["items"][0])
            elif path.startswith("/api/comments/") and request.method == "DELETE":
                assert request.headers["x-bractwo-comments"] == "1"
                identifier = int(path.rsplit("/", 1)[1])
                state["items"] = [item for item in state["items"] if item["id"] != identifier]
                await route.fulfill(status=204)
            elif path.endswith((".css", ".js")) and (WEB / path.lstrip("/")).is_file():
                await route.fulfill(path=str(WEB / path.lstrip("/")))
            else:
                await route.fulfill(status=404)

        await page.route("**/*", handle)
        await page.goto(ORIGIN + "/", wait_until="load")
        await expect(page.locator("#fakeGoogle")).to_be_visible()
        await page.locator("#commentsRefresh").click()
        await expect(page.locator(".comment-body")).to_have_text("<script>alert(2)</script>")
        await expect(page.locator(".comment-item strong")).to_have_text('<img src=x onerror="alert(1)">')
        await expect(page.locator(".comment-item img, .comment-item script")).to_have_count(0)
        print("PASS author/body stay text; injected HTML is not rendered", flush=True)

        # Deliver an authenticated session captured before sign-out only after sign-out.
        session_gate = state["session_gate"] = asyncio.Event()
        async with page.expect_request(is_request("/api/comments/session")):
            await page.evaluate("void BractwoComments.refresh()")
        await page.evaluate("""() => {
          window.__signOut = BractwoComments.logout();
          window.__sameSignOut = window.__signOut === BractwoComments.logout();
        }""")
        assert await page.evaluate("__sameSignOut")
        assert await page.evaluate("__signOut") is True
        session_gate.set()
        await page.wait_for_timeout(100)
        await expect(page.locator("#commentForm")).to_be_hidden()
        assert not state["auth"]
        print("PASS deduplicated logout/204; stale session cannot restore the form", flush=True)

        # Google verification writes a cookie. Logout must follow that response.
        state["verify_gate"] = asyncio.Event()
        baseline = call_count("/api/comments/logout")
        async with page.expect_request(is_request("/auth/google/verify")):
            await page.locator("#fakeGoogle").click()
        # Use void: page.evaluate otherwise waits for the Promise before releasing our gate.
        await page.evaluate("void (window.__signOut = BractwoComments.logout())")
        await expect(page.locator("#googleRetry")).to_be_disabled()
        await page.wait_for_timeout(100)
        assert call_count("/api/comments/logout") == baseline
        state["verify_gate"].set()
        assert await page.evaluate("__signOut") is True
        assert not state["auth"]
        await expect(page.locator("#commentForm")).to_be_hidden()
        assert call_count("/api/comments/logout") == baseline + 1
        print("PASS pending Google verification settles before logout", flush=True)

        # A saved post with a failing list refresh must report both outcomes accurately.
        state["verify_gate"] = None
        await page.locator("#fakeGoogle").click()
        await expect(page.locator("#commentForm")).to_be_visible()
        await page.locator("#commentBody").fill("Nowy komentarz testowy")
        state["fail_list"] = True
        await page.locator("#commentSubmit").click()
        await expect(page.locator("#commentsStatus")).to_contain_text("ale nie udało się")
        await expect(page.locator("#commentBody")).to_have_value("")
        assert len(state["items"]) == 2
        state["fail_list"] = False
        await page.locator("#commentsRefresh").click()
        page.on("dialog", lambda dialog: dialog.accept())
        await page.locator('[data-comment-id="2"] .comment-delete').click()
        await expect(page.locator("#commentsStatus")).to_have_text("Komentarz został usunięty.")
        assert len(state["items"]) == 1
        await expect(page.locator("#commentsRefresh")).to_be_focused()
        print("PASS explicit refresh error after POST; DELETE/204 and focus recovery", flush=True)

        # Switching Google accounts must not prepare another login until logout completes.
        state["logout_gate"] = asyncio.Event()
        baseline = call_count("/auth/google/start")
        async with page.expect_request(is_request("/api/comments/logout")):
            await page.locator("#googleCancel").click()
        await page.wait_for_timeout(100)
        assert call_count("/auth/google/start") == baseline
        state["logout_gate"].set()
        await expect(page.locator("#fakeGoogle")).to_be_visible()
        assert call_count("/auth/google/start") == baseline + 1
        print("PASS Google account switch waits for comment-cookie logout", flush=True)

        # An unsuccessful logout keeps the old session and offers a working logout retry.
        state["logout_gate"] = None
        await page.locator("#fakeGoogle").click()
        await expect(page.locator("#commentForm")).to_be_visible()
        state["fail_logout"] = True
        baseline = call_count("/auth/google/start")
        await page.locator("#commentsLogout").click()
        await expect(page.locator("#googleStatus")).to_contain_text("Nie udało się wylogować")
        await expect(page.locator("#googleRetry")).to_be_enabled()
        await expect(page.locator("#commentForm")).to_be_visible()
        assert state["auth"] and call_count("/auth/google/start") == baseline
        state["fail_logout"] = False
        await page.locator("#googleRetry").click()
        await expect(page.locator("#fakeGoogle")).to_be_visible()
        await expect(page.locator("#commentForm")).to_be_hidden()
        assert not state["auth"] and call_count("/auth/google/start") == baseline + 1
        assert not errors, errors
        print("PASS failed logout is retryable; all scenarios have no JavaScript errors", flush=True)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
