"""Responsive QA against the actual client and an isolated in-memory game server.

Install aiohttp + playwright, then set CHROMIUM_BIN when a system browser is used.
Screenshots, hit-target diagnostics and the report go to docs/qa_mobile by default.
No production service or existing save is accessed. --strict fails on layout issues.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / ".qa-python").is_dir():
    sys.path.insert(0, str(ROOT / ".qa-python"))

from aiohttp import ClientSession, WSMsgType, web
from playwright.async_api import async_playwright
from server.server import create_app


def chromium_path():
    if os.environ.get("CHROMIUM_BIN"):
        return os.environ["CHROMIUM_BIN"]
    for candidate in (
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/usr/bin/chromium",
    ):
        if Path(candidate).is_file():
            return candidate
    return None


MEASURE = """() => {
  const selectors=['.player-card','.top-actions','.world-status','.pvp-bar',
    '#minimapCard','#questTracker','#battleList','#actionDock','#spellbar',
    '#joystick','#attackButton','#interactButton','#healthPotion','#manaPotion',
    '#bookSpell','#abilityButton','#chatButton','#mobileMenuButton'];
  const boxes={}, issues=[];
  for (const selector of selectors) {
    const el=document.querySelector(selector); if(!el)continue;
    const r=el.getBoundingClientRect(),s=getComputedStyle(el);
    if(!r.width||!r.height||s.display==='none'||s.visibility==='hidden')continue;
    boxes[selector]={x:r.x,y:r.y,width:r.width,height:r.height};
    if(r.x < -1 || r.y < -1 || r.right > innerWidth+1 || r.bottom > innerHeight+1)
      issues.push(`${selector} extends beyond viewport`);
    if(el.matches('button')||selector==='#joystick') {
      const hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);
      if(hit!==el&&!el.contains(hit))issues.push(`${selector} center blocked by ${hit?.id||hit?.className||hit?.tagName}`);
    }
  }
  if(document.documentElement.scrollWidth>innerWidth+1)issues.push('Horizontal page overflow');
  return {viewport:{width:innerWidth,height:innerHeight},boxes,issues};
}"""


async def stable_box(page, locator):
    previous = None
    stable = 0
    for _ in range(16):
        box = await locator.bounding_box()
        if previous and all(abs(box[key] - previous[key]) < 0.25 for key in ("x", "y", "width", "height")):
            stable += 1
            if stable >= 3:
                return box
        else:
            stable = 0
        previous = box
        await page.wait_for_timeout(200)
    raise AssertionError("Card bounds did not settle after resize")

async def main(args):
    # Reuse an already installed Node when available; no browser download is needed.
    bundled_node = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe"
    if bundled_node.is_file():
        os.environ.setdefault("PLAYWRIGHT_NODEJS_PATH", str(bundled_node))
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {"ok": False, "status": "running", "connection": "Python WebSocket bridge to isolated aiohttp server; production HTML/CSS/JS and embedded assets" if args.bridge else "native HTTP/WebSocket to isolated local aiohttp server", "checks": [], "errors": [], "layouts": []}
    app = create_app(":memory:")
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    print(f"Local game ready: http://127.0.0.1:{port}", flush=True)
    sockets_all = []
    socket_tasks = []
    page_sockets = {}
    closing = False
    session = ClientSession()
    async def close_bridge(page):
        for socket in page_sockets.get(page, {}).values():
            if not socket.closed:
                await socket.close()
    async def load_page(page):
        if not args.bridge:
            await page.goto(f"http://127.0.0.1:{port}", wait_until="domcontentloaded", timeout=60000)
            return
        sockets = {}
        page_sockets[page] = sockets
        async def emit(sid, kind, data=None):
            if closing or page.is_closed():
                return
            try:
                await page.evaluate("([sid,kind,data])=>window.__deliver(sid,kind,data)", [sid,kind,data])
            except Exception:
                pass
        async def pump(sid, ws):
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    await emit(sid, "message", msg.data)
            await emit(sid, "close")
        async def ws_open(sid, url):
            ws = await session.ws_connect(f"http://127.0.0.1:{port}/ws")
            sockets[sid] = ws
            sockets_all.append(ws)
            await emit(sid, "open")
            socket_tasks.append(asyncio.create_task(pump(sid, ws)))
        async def ws_send(sid, data):
            if sid in sockets and not sockets[sid].closed:
                await sockets[sid].send_str(data)
        async def ws_close(sid):
            if sid in sockets:
                await sockets[sid].close()
        await page.expose_function("__wsOpen", ws_open)
        await page.expose_function("__wsSend", ws_send)
        await page.expose_function("__wsClose", ws_close)
        old_smoke = (ROOT / "tools/browser_0817_wand.py").read_text(encoding="utf-8")
        bridge = re.search("BRIDGE='''(.*?)'''", old_smoke, re.S).group(1)
        bridge = bridge.split("window.__storage={};")[0]
        assets = {str(f.relative_to(ROOT / "web")).replace("\\", "/"):
                  "data:" + ("image/png" if f.suffix == ".png" else "image/svg+xml") + ";base64," + base64.b64encode(f.read_bytes()).decode()
                  for f in (ROOT / "web/assets").rglob("*") if f.suffix in (".png", ".svg")}
        asset_bridge = "window.__qaAssets=" + json.dumps(assets) + ";const srcDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,'src');Object.defineProperty(HTMLImageElement.prototype,'src',{get:srcDesc.get,set(v){srcDesc.set.call(this,window.__qaAssets[v]||v);}});"
        html = (ROOT / "web/index.html").read_text(encoding="utf-8")
        html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', lambda m: "<style>" + (ROOT / "web" / m[1]).read_text(encoding="utf-8") + "</style>", html)
        html = re.sub(r'<script src="([^"]+)"></script>', lambda m: "<script>" + (bridge + asset_bridge if m[1] == "runtime.js" else "") + (ROOT / "web" / m[1]).read_text(encoding="utf-8") + "</script>", html)
        # CSS-backed potion icons also use the exact source image bytes.
        html = re.sub(r"url\(['\"]?(assets/[^)'\"\s]+)['\"]?\)", lambda m: 'url("' + assets.get(m[1], m[1]) + '")', html)
        print("Loading embedded production client with the 0.8.17 WebSocket bridge", flush=True)
        await page.route("http://bractwo.local/", lambda route: route.fulfill(status=200, content_type="text/html; charset=utf-8", body=html))
        await page.goto("http://bractwo.local/", wait_until="load", timeout=60000)
        assert await page.evaluate("()=>{localStorage.setItem('__qaProbe','ok');const valid=localStorage.getItem('__qaProbe')==='ok';localStorage.removeItem('__qaProbe');return valid;}"), "Native localStorage does not work at the test origin"
        await page.add_style_tag(content=(ROOT / "web/mobile.css").read_text(encoding="utf-8"))
        await page.evaluate("url=>document.getElementById('serverInput').value=url", f"ws://127.0.0.1:{port}/ws")
    browser = None
    pw = None
    try:
        pw = await async_playwright().start()
        print("Launching local Chromium", flush=True)
        browser = await pw.chromium.launch(executable_path=chromium_path(), headless=True)
        print("Chromium ready", flush=True)
        context = await browser.new_context(viewport={"width": 844, "height": 390}, is_mobile=True, has_touch=True, device_scale_factor=1)
        page = await context.new_page()
        page.set_default_timeout(60000)
        page.on("pageerror", lambda error: report["errors"].append(str(error)))
        await load_page(page)
        await page.screenshot(path=str(output / "auth-loaded.png"))
        print("Game client loaded; registering QA mage", flush=True)
        await page.locator("#registerTab").click()
        await page.locator("#nameInput").fill("MobileQA")
        await page.locator("#passwordInput").fill("mobile-qa-password")
        await page.locator('#classPicker [data-class="mage"]').click()
        await page.locator("#connectButton").click()
        await page.locator("#gameUI").wait_for(state="visible", timeout=120000)
        await page.screenshot(path=str(output / "game-first.png"))
        await page.wait_for_timeout(700)
        if await page.locator("#closeControlTip").is_visible():
            await page.locator("#closeControlTip").click()
        report["checks"].append("Mage registration through production UI and the actual game server succeeds")
        player = next(p for p in app["game"].players.values() if p.name == "MobileQA")
        await app["game"].bind_spell(player, 23, "fire_bolt")
        await page.locator('#hotbarFunctionSlots .hotbar-slot[data-spell="fire_bolt"]').wait_for(state="visible")
        report["checks"].append("Known Fire Bolt is assigned to F12 through the actual server handler for a meaningful late-slot scrolling check")
        if not args.profile_only:
            for width, height in [(734,260),(568,280),(915,330),(844,390),(667,375),(390,844),(360,640)]:
                await page.set_viewport_size({"width": width, "height": height})
                await page.wait_for_timeout(250)
                await page.add_style_tag(content=(ROOT / "web/mobile.css").read_text(encoding="utf-8"))
                layout = await page.evaluate(MEASURE)
                layout["screenshot"] = f"game-{width}x{height}.png"
                report["layouts"].append(layout)
                (output / "browser_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
                await page.screenshot(path=str(output / layout["screenshot"]))
                print(f"{width}x{height}: {layout['issues'] or 'all measured controls fit'}", flush=True)
            await page.set_viewport_size({"width": 734, "height": 260})
            await page.wait_for_timeout(250)
            await page.locator("#mobileMenuButton").click()
            await page.locator("#mobileMenu").wait_for(state="visible")
            await page.screenshot(path=str(output / "menu-734x260.png"))
            await page.locator("#mobileMenuClose").click()
            await page.locator("#mobileMenu").wait_for(state="hidden")
            await page.locator("#chatButton").click()
            await page.locator("#chatForm").wait_for(state="visible")
            await page.screenshot(path=str(output / "chat-734x260.png"))
            await page.locator("#mobileChatClose").click()
            await page.locator("#chatForm").wait_for(state="hidden")
            report["checks"].append("Mobile menu and chat open and close at 734x260")
            bar_scroll = await page.locator(".hotbar-viewport").evaluate("el=>{const before=el.scrollLeft;el.scrollLeft=el.scrollWidth;return {before,after:el.scrollLeft,width:el.clientWidth,full:el.scrollWidth};}")
            assert bar_scroll["full"] <= bar_scroll["width"] or bar_scroll["after"] > 0, "Hotbar cannot scroll to the late slots"
            last_slot = page.locator("#hotbarFunctionSlots .hotbar-slot").last
            if await last_slot.count():
                await last_slot.scroll_into_view_if_needed()
                box = await last_slot.bounding_box()
                assert box and box["x"] >= -1 and box["x"] + box["width"] <= 735, "Last function slot is outside the viewport after scrolling"
            await page.screenshot(path=str(output / "spells-scrolled-734x260.png"))
            report["checks"].append("Horizontal hotbar scrolling exposes the last function slot")
            await page.set_viewport_size({"width": 844, "height": 390})
            await page.wait_for_timeout(250)
            joy = await page.locator("#joystick").bounding_box()
            player = next(p for p in app["game"].players.values() if p.name == "MobileQA")
            before = player.x, player.y
            cdp = await context.new_cdp_session(page)
            cx, cy = joy["x"]+joy["width"]/2, joy["y"]+joy["height"]/2
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x":cx,"y":cy,"id":1}]})
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x":cx+30,"y":cy,"id":1}]})
            await page.wait_for_timeout(500)
            await cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            await page.wait_for_timeout(150)
            assert (player.x-before[0])**2+(player.y-before[1])**2>100, "Touch joystick did not move the player"
            report["checks"].append("Native touch input on the joystick moves the server player")
            await page.locator("#bookSpell").click()
            await page.locator("#characterPanel").wait_for(state="visible")
            await page.screenshot(path=str(output / "spells-landscape.png"))
            await page.keyboard.press("Enter")
            await page.locator("#chatForm").wait_for(state="visible")
            assert await page.locator("#chatInput").evaluate("el=>{const r=el.getBoundingClientRect();return document.elementFromPoint(r.x+r.width/2,r.y+r.height/2)===el;}"), "Chat input is covered by the character sheet"
            await page.screenshot(path=str(output / "chat-over-character.png"))
            await page.locator("#mobileChatClose").click()
            await page.locator("#chatForm").wait_for(state="hidden")
            report["checks"].append("Enter opens a hittable chat above the character sheet and the touch close works")
            await page.locator(".character-close").click()
            report["checks"].append("Touch-accessible spellbook opens and closes")
        await close_bridge(page)
        await context.close()
        desktop = await browser.new_context(viewport={"width":1440,"height":900}, is_mobile=False, has_touch=False)
        desktop.set_default_timeout(60000)
        desktop_page = await desktop.new_page()
        desktop_page.on("pageerror", lambda error: report["errors"].append(str(error)))
        await load_page(desktop_page)
        await desktop_page.locator("#loginTab").click()
        await desktop_page.locator("#nameInput").fill("MobileQA")
        await desktop_page.locator("#passwordInput").fill("mobile-qa-password")
        await desktop_page.locator("#connectButton").click()
        await desktop_page.locator("#gameUI").wait_for(state="visible", timeout=120000)
        await desktop_page.wait_for_timeout(500)
        layout = await desktop_page.evaluate(MEASURE)
        layout["screenshot"] = "game-desktop-1440x900.png"
        report["layouts"].append(layout)
        await desktop_page.screenshot(path=str(output / layout["screenshot"]))
        report["checks"].append("Desktop login and layout use a separate context without touch emulation")
        desktop_key = f"bractwo-windows-v1:{player.id}:landscape"
        saved = json.dumps({"positions":{"player":{"x":0.62,"y":0.4,"width":280}},"hidden":{}})
        original = await desktop_page.evaluate("key=>localStorage.getItem(key)", desktop_key)
        await desktop_page.evaluate("([key,value])=>localStorage.setItem(key,value)", [desktop_key,saved])
        for width,height in [(734,260),(1440,900)]:
            await desktop_page.set_viewport_size({"width":width,"height":height})
            await desktop_page.wait_for_timeout(200)
        card = desktop_page.locator(".player-card")
        assert "hud-floating" in (await card.get_attribute("class")), "Desktop profile did not restore the stored position"
        first_immediate = await card.bounding_box()
        desktop_position = await stable_box(desktop_page, card)
        await desktop_page.screenshot(path=str(output / "desktop-profile-first.png"))
        await desktop_page.set_viewport_size({"width":734,"height":260})
        await desktop_page.wait_for_timeout(250)
        assert "hud-floating" not in (await card.get_attribute("class")), "Desktop floating position leaked into mobile"
        assert await desktop_page.evaluate("key=>localStorage.getItem(key)", desktop_key) == saved
        await desktop_page.set_viewport_size({"width":1440,"height":900})
        await desktop_page.wait_for_timeout(250)
        restored_immediate = await card.bounding_box()
        restored = await stable_box(desktop_page, card)
        report["desktop_profile"] = {"saved":json.loads(saved), "first_immediate":first_immediate, "first_stable":desktop_position, "restored_immediate":restored_immediate, "restored_stable":restored}
        print("PROFILE " + json.dumps(report["desktop_profile"]), flush=True)
        await desktop_page.screenshot(path=str(output / "desktop-profile-restored.png"))
        assert all(abs(restored[key]-desktop_position[key])<2 for key in ("x","y","width")), "Desktop position changed after mobile rotation"
        await desktop_page.evaluate("([key,value])=>value===null?localStorage.removeItem(key):localStorage.setItem(key,value)", [desktop_key,original])
        report["checks"].append("Desktop saved positions survive desktop-to-mobile-to-desktop without appearing on mobile")
        assert not report["errors"], report["errors"]
        issues = [issue for layout in report["layouts"] for issue in layout["issues"]]
        if args.strict:
            assert not issues, issues
        report["ok"] = True
        report["status"] = "passed"
        print("Mobile browser QA complete", flush=True)
        await browser.close()
        browser = None
    except Exception as error:
        report["failure"] = str(error)
        report["status"] = "failed"
        if browser:
            for index, open_page in enumerate([p for c in browser.contexts for p in c.pages if not p.is_closed()]):
                try:
                    await asyncio.wait_for(open_page.screenshot(path=str(output / f"failure-{index}.png")), 12)
                except Exception as capture_error:
                    report.setdefault("capture_errors", []).append(str(capture_error))
        raise
    finally:
        closing = True
        (output / "browser_results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        for ws in sockets_all:
            if not ws.closed:
                await ws.close()
        for task in socket_tasks:
            task.cancel()
        await asyncio.gather(*socket_tasks, return_exceptions=True)
        await session.close()
        if browser:
            try:
                await browser.close()
            except Exception:
                pass
        if pw:
            await pw.stop()
        await runner.cleanup()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "docs" / "qa_mobile"))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--profile-only", action="store_true", help="Run only the desktop restoration diagnostic; skip the mobile matrix and interactions")
    parser.add_argument("--bridge", action="store_true", help="Use the proven 0.8.17 Python WebSocket bridge when browser loopback is unavailable")
    asyncio.run(main(parser.parse_args()))
