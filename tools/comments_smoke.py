"""Exercise the public gallery and comments in local Chromium.

Run: python tools/comments_smoke.py --output /tmp/bractwo-comments-browser

Uses an in-memory game database and the fixture Google SDK/verifier from the
existing gameplay smoke test. Every browser request is either served locally,
fulfilled by that SDK fixture, or blocked. No real accounts or services are used.
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import re
import shutil
import sys
import time
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp import web
from playwright.async_api import async_playwright, expect
from server.comments import COOLDOWN_SECONDS
from server.google_auth import GoogleAuthService
from server.server import Player, create_app
from tools.seo_gameplay_smoke import GOOGLE_SDK, fixture_verifier


GOOGLE_SDK_URL = "https://accounts.google.com/gsi/client?hl=pl"
COMMENT_API = "/api/comments"
ITEMS = "#commentsList li.comment-item"
VULGAR_BODY = "Ten komentarz zawiera słowo kurwa."
XSS_BODY = '<img src=x onerror="window.__commentSmokeXSS=true"> Przygoda <b>bez HTML</b> & skarb'
VIEWPORTS = (
    ("desktop", {"width": 1440, "height": 900}, False),
    ("mobile", {"width": 390, "height": 844}, True),
)


class CommentClock:
    """Advance only comment timestamps/rate limits; auth uses its real clock."""

    def __init__(self):
        self.offset = 0

    def __call__(self):
        return time.time() + self.offset

    def advance(self):
        self.offset += COOLDOWN_SECONDS + 1


def seed_character(game, subject, name, class_id="knight"):
    """Create an offline saved character owned by the fixture Google subject."""
    google_id = game._google_account_id(subject)
    player = Player("", name, None, class_id=class_id)
    game.starter(player)
    player.hp, player.mana = player.max_hp, player.max_mana
    with game.db:
        cursor = game.db.execute(
            "INSERT INTO accounts(name,name_key,salt,password_hash,data) VALUES(?,?,?,?,?)",
            (name, name.casefold(), b"comments-smoke-salt", b"", json.dumps(player.save_data())),
        )
        character_id = cursor.lastrowid
        game.db.execute(
            "INSERT INTO google_characters(google_account_id,character_id,linked_at) VALUES(?,?,?)",
            (google_id, character_id, game.now()),
        )
    return {"google_id": google_id, "id": str(character_id), "name": name}


def seed_comments(game, character, clock):
    """More than one public page, without spending any fixture account quota."""
    with game.db:
        game.db.executemany(
            "INSERT INTO public_comments(google_account_id,character_id,author,body,created_at) "
            "VALUES(?,?,?,?,?)",
            [(character["google_id"], int(character["id"]), character["name"],
              f"Wpis przygotowany {index:02d}: wspólna wyprawa przez krainy.", clock() - 1000 - index)
             for index in range(1, 23)],
        )


def api_response(method, path=COMMENT_API):
    return lambda response: (response.request.method == method
                             and urlsplit(response.url).path == path)


async def assert_no_overflow(page, label):
    measurements = await page.evaluate("""() => {
      const selectors = ['html', '#authScreen', '#galeria', '#komentarze'];
      return selectors.map(selector => {
        const node = document.querySelector(selector);
        return {selector, width: node.clientWidth, scrollWidth: node.scrollWidth};
      });
    }""")
    assert all(item["scrollWidth"] <= item["width"] + 1 for item in measurements), (label, measurements)


async def check_gallery(page):
    images = page.locator("#galeria img")
    await expect(images).to_have_count(6)
    for index in range(6):
        image = images.nth(index)
        await image.scroll_into_view_if_needed()
        await expect(image).to_be_visible()
        await page.wait_for_function(
            "index => { const image = document.querySelectorAll('#galeria img')[index]; "
            "return image.complete && image.naturalWidth > 0; }", arg=index,
        )
    return await images.evaluate_all("nodes => nodes.map(node => ({src: node.getAttribute('src'), "
                                     "width: node.naturalWidth, height: node.naturalHeight}))")


async def main(output):
    output.mkdir(parents=True, exist_ok=True)
    auth = GoogleAuthService("seo-smoke.apps.googleusercontent.com", "http://127.0.0.1:1",
                             verifier=fixture_verifier)
    app = create_app(":memory:", google_auth_service=auth)
    game = app["game"]
    clock = CommentClock()
    app["comments"]._wall_clock = clock
    public_author = seed_character(game, "seo-smoke-public-writer", "Kronikarz")
    seed_comments(game, public_author, clock)
    characters = {}
    for label, _, _ in VIEWPORTS:
        subject = "seo-smoke-comments-" + label
        characters[label] = [seed_character(game, subject, "Forum" + label.title()),
                             seed_character(game, subject, "Forum" + label.title() + "Alt", "druid")]

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    base = "http://127.0.0.1:" + str(site._server.sockets[0].getsockname()[1])
    auth.allowed_origin = app["comments"].allowed_origin = base
    report, errors, external_requests = [], [], []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which("chromium") or None,
                headless=True, args=["--no-sandbox"],
            )
            try:
                async def new_context(viewport, mobile, subject):
                    context = await browser.new_context(viewport=viewport, is_mobile=mobile,
                                                        has_touch=mobile, service_workers="block")

                    async def route_request(route):
                        if route.request.url.startswith(base + "/"):
                            await route.continue_()
                        elif route.request.url == GOOGLE_SDK_URL:
                            await route.fulfill(status=200, content_type="application/javascript", body=GOOGLE_SDK)
                        else:
                            external_requests.append(route.request.url)
                            await route.abort()

                    await context.route("**/*", route_request)
                    await context.add_init_script("window.__seoFixtureSubject=" + json.dumps(subject))
                    page = await context.new_page()
                    page.on("pageerror", lambda error: errors.append(str(error)))
                    page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
                    return context, page

                for label, viewport, mobile in VIEWPORTS:
                    context, page = await new_context(viewport, mobile, "seo-smoke-comments-" + label)
                    observer_context, observer = await new_context(viewport, mobile, "seo-smoke-observer-" + label)
                    try:
                        response = await page.goto(base + "/", wait_until="load")
                        assert response.status == 200
                        await page.get_by_test_id("fixture-google").wait_for(state="visible")
                        gallery = await check_gallery(page)
                        await page.locator("#komentarze").scroll_into_view_if_needed()
                        await expect(page.locator("#commentForm")).to_be_hidden()
                        await expect(page.locator("#commentsLoginPrompt")).to_be_visible()
                        await expect(page.locator(ITEMS).first).to_be_visible()
                        assert await page.locator("#commentsStatus").get_attribute("role") == "status"
                        await expect(page.locator("#commentsMore")).to_be_visible()
                        first_page_count = await page.locator(ITEMS).count()
                        await page.locator("#commentsMore").click()
                        await page.wait_for_function(
                            "count => document.querySelectorAll('#commentsList li.comment-item').length > count",
                            arg=first_page_count,
                        )
                        await expect(page.locator(ITEMS).filter(has_text="Wpis przygotowany 22:")).to_be_visible()
                        await assert_no_overflow(page, label + " anonymous")

                        await page.get_by_test_id("fixture-google").click()
                        await expect(page.locator("#commentForm")).to_be_visible()
                        await expect(page.locator("#gameUI")).to_be_hidden()
                        assert not game.players, "Comment login unexpectedly entered the game"
                        options = await page.locator("#commentCharacter option").evaluate_all(
                            "nodes => nodes.filter(node => node.value).map(node => ({id: node.value, name: node.textContent}))"
                        )
                        assert {option["id"] for option in options} == {item["id"] for item in characters[label]}, options
                        selected = characters[label][1]
                        await page.locator("#commentCharacter").select_option(selected["id"])
                        assert await page.locator("#commentBody").get_attribute("minlength") == "3"
                        assert await page.locator("#commentBody").get_attribute("maxlength") == "1000"

                        normal_body = f"Wyprawa {label}: podoba mi się wspólne odkrywanie krain."
                        clock.advance()
                        await page.locator("#commentBody").fill(normal_body)
                        async with page.expect_response(api_response("POST")) as submitted:
                            await page.locator("#commentSubmit").click()
                        posted = await submitted.value
                        assert posted.status == 201, (label, await posted.text())
                        normal_row = page.locator(ITEMS).filter(has_text=normal_body)
                        await expect(normal_row).to_be_visible()
                        await expect(normal_row).to_contain_text(selected["name"])
                        await expect(page.locator("#commentBody")).to_have_value("")

                        await observer.goto(base + "/#komentarze", wait_until="load")
                        await expect(observer.locator(ITEMS).filter(has_text=normal_body)).to_be_visible()
                        await expect(observer.locator("#commentForm")).to_be_hidden()
                        assert not await observer.locator(ITEMS).get_by_role("button", name=re.compile("^Usuń")).count()

                        # Rate limiting precedes moderation; exercise the filter
                        # only after the previous successful post's cooldown.
                        clock.advance()
                        await page.locator("#commentBody").fill(VULGAR_BODY)
                        async with page.expect_response(api_response("POST")) as rejected:
                            await page.locator("#commentSubmit").click()
                        rejection = await rejected.value
                        assert rejection.status == 400, (label, await rejection.text())
                        assert (await rejection.json())["error"] == "profanity"
                        await expect(page.locator("#commentsStatus")).not_to_be_empty()
                        assert not await page.locator(ITEMS).filter(has_text=VULGAR_BODY).count()

                        clock.advance()
                        xss_body = XSS_BODY + " " + label
                        await page.locator("#commentBody").fill(xss_body)
                        async with page.expect_response(api_response("POST")) as escaped:
                            await page.locator("#commentSubmit").click()
                        escaped_response = await escaped.value
                        assert escaped_response.status == 201, (label, await escaped_response.text())
                        xss_data = await escaped_response.json()
                        xss_row = page.locator(ITEMS).filter(has_text=xss_body)
                        await expect(xss_row).to_be_visible()
                        assert not await xss_row.locator("img,script,iframe").count()
                        assert not await page.evaluate("Boolean(window.__commentSmokeXSS)")
                        await observer.reload(wait_until="load")
                        await expect(observer.locator(ITEMS).filter(has_text=xss_body)).to_be_visible()
                        assert not await observer.evaluate("Boolean(window.__commentSmokeXSS)")
                        await assert_no_overflow(page, label + " authenticated")
                        if mobile:
                            await page.set_viewport_size({"width": 320, "height": 780})
                            await assert_no_overflow(page, "narrow mobile authenticated")
                            await page.set_viewport_size(viewport)
                        await page.locator("#komentarze").scroll_into_view_if_needed()
                        await page.screenshot(path=str(output / (label + "-comments.png")))

                        async with page.expect_response(api_response("DELETE", COMMENT_API + "/" + xss_data["item"]["id"])) as deleted:
                            await xss_row.get_by_role("button", name=re.compile("^Usuń")).click()
                        deletion = await deleted.value
                        assert deletion.status == 200, (label, await deletion.text())
                        await expect(page.locator(ITEMS).filter(has_text=xss_body)).to_have_count(0)
                        await observer.reload(wait_until="load")
                        await expect(observer.locator(ITEMS).filter(has_text=normal_body)).to_be_visible()
                        await expect(observer.locator(ITEMS).filter(has_text=xss_body)).to_have_count(0)

                        async with page.expect_response(api_response("POST", COMMENT_API + "/logout")) as logged_out:
                            await page.locator("#commentsLogout").click()
                        assert (await logged_out.value).status == 200
                        await expect(page.locator("#commentForm")).to_be_hidden()
                        await expect(page.locator("#commentsLoginPrompt")).to_be_visible()
                        session = await page.evaluate("async () => (await fetch('/api/comments/session')).json()")
                        assert session["authenticated"] is False, session
                        await assert_no_overflow(page, label + " after logout")
                        report.append({"viewport": label, "gallery": gallery,
                                       "anonymous_read_and_pagination": True,
                                       "google_login_without_entering_game": True,
                                       "owned_character_author": selected["name"],
                                       "post_visible_to_other_browser": True,
                                       "profanity_rejected": True, "html_rendered_as_text": True,
                                       "own_delete_publicly_visible": True, "logout_revoked_session": True,
                                       "horizontal_overflow": False})
                    finally:
                        await observer_context.close()
                        await context.close()
                assert not errors, errors
                assert not external_requests, external_requests
            finally:
                await browser.close()
    finally:
        await runner.cleanup()
    result = {"ok": True, "checks": report, "javascript_errors": errors,
              "unexpected_external_requests": external_requests,
              "limitations": ["Local Chromium and fixture Google authentication only; no production or physical-device checks."]}
    (output / "report.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/bractwo-comments-browser"))
    asyncio.run(main(parser.parse_args().output))
