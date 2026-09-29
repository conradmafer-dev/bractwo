"""0.8.18 UI/PWA smoke on an isolated in-memory server and native localhost.

Uses real Chromium HTTP, WebSocket, fullscreen and service-worker APIs. Only the
denied/unsupported fullscreen cases mock those APIs, in separate contexts.
The server clock is controlled and monster AI paused for deterministic rest QA.
Run: python -u tools/browser_0818_smoke.py
"""
from __future__ import annotations

print('0.8.18 smoke: importing Python dependencies and world data', flush=True)

import argparse
import asyncio
import json
import os
from pathlib import Path
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
if (ROOT / '.qa-python').is_dir():
    sys.path.insert(0, str(ROOT / '.qa-python'))

from aiohttp import web
from playwright.async_api import async_playwright
from server.server import create_app
from tools.browser_mobile_smoke import MEASURE, chromium_path

print('0.8.18 smoke: imports complete', flush=True)


class Clock:
    value = 1000.0
    def __call__(self):
        return self.value


async def eventually(predicate, message, timeout=30):
    deadline = asyncio.get_running_loop().time() + timeout
    while asyncio.get_running_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(.05)
    raise AssertionError(message)


async def main(args):
    node = Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
    if node.is_file():
        os.environ.setdefault('PLAYWRIGHT_NODEJS_PATH', str(node))
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = {'ok': False, 'status': 'running', 'transport': 'native localhost HTTP/WebSocket; --no-proxy-server',
              'fixtures': ['isolated :memory: database', 'controlled server clock', 'monster AI paused'],
              'checks': [], 'layouts': [], 'errors': [], 'limitations': ['OS-level PWA installation is not automated.']}
    def save():
        (output / 'browser_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    def passed(name, **detail):
        report['checks'].append({'name': name, 'ok': True, **detail})
        save()
        print('PASS: ' + name, flush=True)
    clock = Clock()
    print('Building isolated in-memory game', flush=True)
    app = create_app(':memory:', clock=clock)
    game = app['game']
    game.step_monsters = lambda *args, **kwargs: None
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    base = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
    report['origin'] = base
    print('Native local game ready: ' + base, flush=True)
    browser = pw = None
    bridge = None
    if args.bridge:
        from tools.browser_0818_bridge import Bridge
        bridge = Bridge(base)
        report['source_sha256'] = bridge.source_hashes
        report['transport'] = 'Python WebSocket bridge to isolated aiohttp server; production HTML/CSS/JS and embedded assets at routed bractwo.local origin'
        report['limitations'].append('Native localhost page.goto timed out with --no-proxy-server; service-worker/offline integration is not exercised by this bridge run.')
    contexts = []

    async def new_page(width, height, touch=False, init=None):
        context = await browser.new_context(viewport={'width': width, 'height': height},
                                            is_mobile=touch, has_touch=touch, device_scale_factor=1)
        contexts.append(context)
        if init:
            await context.add_init_script(init)
        page = await context.new_page()
        page.set_default_timeout(60000)
        page.on('pageerror', lambda error: report['errors'].append(str(error)))
        print(f'Loading {"bridge" if bridge else "native HTTP"} {width}x{height}', flush=True)
        if bridge:
            await bridge.load(page)
        else:
            await page.goto(base, wait_until='domcontentloaded', timeout=45000)
        await page.locator('#authFullscreenButton').wait_for(state='visible')
        return context, page

    async def login(page, name):
        await page.locator('#registerTab').click()
        await page.locator('#nameInput').fill(name)
        await page.locator('#passwordInput').fill('isolated-qa-0818')
        await page.locator('#classPicker [data-class="mage"]').click()
        await page.locator('#connectButton').click()
        await page.locator('#gameUI').wait_for(state='visible', timeout=120000)
        await page.screenshot(path=str(output / f'game-visible-{name}.png'))
        await eventually(lambda: any(p.name == name for p in game.players.values()), 'Server player missing')
        if await page.locator('#closeControlTip').is_visible():
            await page.locator('#closeControlTip').click()
        await page.wait_for_timeout(400)
        return next(p for p in game.players.values() if p.name == name)

    async def open_rest(page):
        if await page.locator('#mobileMenuButton').is_visible():
            await page.locator('#mobileMenuButton').click()
        await page.locator('#restMenuButton').click()
        await page.locator('#restPanel').wait_for(state='visible')

    async def wait_enabled(page, selector, enabled=True):
        await page.wait_for_function('(arg)=>document.querySelector(arg[0]).disabled!==arg[1]', arg=[selector, enabled])

    async def fullscreen(page, selector):
        supported = await page.evaluate('Boolean(document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen)')
        assert supported, 'Test Chromium does not expose native fullscreen'
        await page.locator(selector).click()
        await page.wait_for_function('Boolean(document.fullscreenElement || document.webkitFullscreenElement)')
        assert await page.locator(selector).get_attribute('aria-pressed') == 'true'
        await page.locator(selector).click()
        await page.wait_for_function('!document.fullscreenElement && !document.webkitFullscreenElement')
        assert await page.locator(selector).get_attribute('aria-pressed') == 'false'

    try:
        pw = await async_playwright().start()
        print('Launching Chromium with --no-proxy-server', flush=True)
        browser = await pw.chromium.launch(executable_path=chromium_path(), headless=True, args=['--no-proxy-server'])
        if args.layout_only:
            from tools.browser_0818_layout_checks import run
            await run(new_page, login, output, report, passed)
            assert not report['errors'], '\n'.join(report['errors'])
            report.update(ok=True, status='passed')
            return 0
        mobile_context, page = await new_page(734, 260, True)
        await page.screenshot(path=str(output / 'auth-734x260.png'))
        await fullscreen(page, '#authFullscreenButton')
        passed('Native fullscreen enters/exits from authentication screen')
        player = await login(page, 'RestMobileQA')
        await page.screenshot(path=str(output / 'game-first.png'))
        passed('Registration and gameplay use the actual server through ' + ('the documented WebSocket bridge' if bridge else 'native browser WebSocket'))
        for width, height in [(734, 260), (390, 844)]:
            await page.set_viewport_size({'width': width, 'height': height})
            await page.wait_for_timeout(400)
            measure = MEASURE.replace("'#mobileMenuButton'", "'#mobileMenuButton','#mobileFullscreenButton'")
            layout = await page.evaluate(measure)
            layout['screenshot'] = f'game-{width}x{height}.png'
            report['layouts'].append(layout)
            await page.screenshot(path=str(output / layout['screenshot']))
            save()
            await open_rest(page)
            await page.screenshot(path=str(output / f'rest-{width}x{height}.png'))
            bounds = await page.locator('#restPanel').bounding_box()
            assert bounds and bounds['x'] >= -1 and bounds['y'] >= -1 and bounds['x'] + bounds['width'] <= width + 1 and bounds['y'] + bounds['height'] <= height + 1, 'Rest dialog outside viewport'
            overflow = await page.locator('#restPanel').evaluate("el=>({content:el.scrollHeight,height:el.clientHeight,pointerEvents:getComputedStyle(el).pointerEvents})")
            assert overflow['pointerEvents'] == 'auto', 'Dialog text/background cannot receive scrolling input'
            if overflow['content'] > overflow['height'] + 1:
                await page.mouse.move(bounds['x']+20,bounds['y']+bounds['height']-24)
                await page.mouse.wheel(0,180)
                await page.wait_for_function("document.getElementById('restPanel').scrollTop > 0")
            for selector in ['#shortRestButton', '#longRestButton', '#closeRestPanel']:
                await page.locator(selector).scroll_into_view_if_needed()
                assert await page.locator(selector).is_visible()
            await page.locator('#closeRestPanel').click()
            passed(f'Rest menu/dialog accessible at {width}x{height}')
        await fullscreen(page, '#mobileFullscreenButton')
        passed('Native fullscreen enters/exits from mobile game control')

        # Leave the legacy combat timer active to suppress unrelated passive HP.
        player.x, player.y, player.floor = 1100, 1180, 0
        assert not game.in_safe(player)
        player.hp, player.mana = player.max_hp * .2, player.max_mana * .2
        player.mana_recovery_until = clock.value + 3600
        game.tag(player, pvp=False)
        await open_rest(page)
        await wait_enabled(page, '#shortRestButton', False)
        clock.value += 3.01
        await wait_enabled(page, '#shortRestButton')
        assert await page.locator('#longRestButton').is_disabled()
        passed('PvE rest block expires after 3 seconds; long rest remains disabled in field')
        hp_before, mana_before = player.hp, player.mana
        await page.locator('#shortRestButton').click()
        await eventually(lambda: bool(player.rest_state), 'Short rest not started')
        await page.locator('#cancelRestButton').wait_for(state='visible')
        clock.value += 3
        await page.wait_for_function("document.getElementById('restProgress').value > .4")
        await page.screenshot(path=str(output / 'short-rest-progress.png'))
        clock.value += 3.01
        await eventually(lambda: not player.rest_state, 'Short rest did not finish')
        await wait_enabled(page, '#shortRestButton')
        assert abs(player.hp - (hp_before + player.max_hp * .25)) < .01
        assert abs(player.mana - (mana_before + player.max_mana * .25)) < .01
        passed('Short rest grants 25 percent max HP/mana after full 6 seconds', hp_before=hp_before, hp_after=player.hp, mana_before=mana_before, mana_after=player.mana)
        await page.locator('#shortRestButton').click()
        await eventually(lambda: bool(player.rest_state), 'Cancel fixture did not start')
        hp_before, mana_before = player.hp, player.mana
        await page.locator('#cancelRestButton').click()
        await eventually(lambda: not player.rest_state, 'Cancel command ignored')
        assert player.hp == hp_before and player.mana == mana_before
        passed('Cancel rest button stops without reward')
        player.x, player.y, player.floor = 560, 1180, 0
        assert game.in_safe(player)
        await wait_enabled(page, '#longRestButton')
        await page.locator('#longRestButton').click()
        await eventually(lambda: bool(player.rest_state), 'Long rest not started')
        await page.locator('#cancelRestButton').wait_for(state='visible')
        clock.value += 15.01
        await eventually(lambda: not player.rest_state, 'Long rest did not finish')
        assert player.hp == player.max_hp and player.mana == player.max_mana
        passed('Long rest in safe settlement restores full HP/mana after 15 seconds')
        game.tag(player, pvp=True)
        await wait_enabled(page, '#shortRestButton', False)
        clock.value += 3.01
        await page.wait_for_timeout(250)
        assert await page.locator('#shortRestButton').is_disabled()
        clock.value += 17.01
        await wait_enabled(page, '#shortRestButton')
        passed('PvP rest block retains full 20 seconds')
        await page.locator('#closeRestPanel').click()
        await mobile_context.close()

        desktop_context, desktop = await new_page(1440, 900)
        await login(desktop, 'RestDesktopQA')
        layout = await desktop.evaluate(MEASURE)
        layout['screenshot'] = 'game-1440x900.png'
        report['layouts'].append(layout)
        await desktop.screenshot(path=str(output / layout['screenshot']))
        save()
        await open_rest(desktop)
        await desktop.screenshot(path=str(output / 'rest-1440x900.png'))
        await desktop.locator('#closeRestPanel').click()
        await fullscreen(desktop, '#fullscreenButton')
        passed('Desktop rest dialog and native fullscreen work without touch emulation')
        await desktop_context.close()

        if args.bridge:
            from tools.browser_0818_layout_checks import run
            await run(new_page, login, output, report, passed)
            for kind, script, expected_text in [
                ('unsupported', "Object.defineProperty(Element.prototype,'requestFullscreen',{value:undefined,configurable:true});Object.defineProperty(Element.prototype,'webkitRequestFullscreen',{value:undefined,configurable:true});", 'nie udostępnia'),
                ('denied', "Object.defineProperty(Element.prototype,'requestFullscreen',{value:function(){return Promise.reject(new DOMException('QA denied','NotAllowedError'));},configurable:true});", 'odmówiła'),
            ]:
                fallback_context, fallback = await new_page(390,844,init=script)
                await fallback.locator('#authFullscreenButton').click()
                await fallback.locator('#appHelpDialog').wait_for(state='visible')
                assert expected_text in await fallback.locator('#appHelpBody').inner_text()
                await fallback.screenshot(path=str(output/f'fullscreen-{kind}.png'))
                await fallback.keyboard.press('Escape')
                await fallback.locator('#appHelpDialog').wait_for(state='hidden')
                passed('Fullscreen fallback: '+kind,simulation='fullscreen API deliberately replaced in isolated context')
                await fallback.locator('#authInstallButton').click()
                await fallback.locator('#appHelpDialog').wait_for(state='visible')
                assert 'internetu' in await fallback.locator('#appHelpBody').inner_text()
                await fallback.locator('#appHelpClose').click()
                await fallback_context.close()
            passed('Install help explains internet requirement and closes normally')
            issues = [issue for layout in report['layouts'] for issue in layout.get('issues',[])]
            assert not issues, '\n'.join(issues)
            assert not report['errors'], '\n'.join(report['errors'])
            report.update(ok=True,status='passed_with_transport_limitation')
            return 0

        # Independent unauthenticated page keeps deliberate offline navigation
        # from triggering an expected gameplay disconnection in the main checks.
        pwa_context, pwa = await new_page(390, 844)
        await pwa.wait_for_function('navigator.serviceWorker.controller !== null', timeout=60000)
        sw = await pwa.evaluate('''async()=>{const r=await navigator.serviceWorker.ready;return {scope:r.scope,active:r.active?.state,secure:isSecureContext};}''')
        assert sw['scope'] == base + '/' and sw['active'] == 'activated' and sw['secure']
        await pwa.evaluate("fetch('/health').then(r=>r.json())")
        cache = await pwa.evaluate('''async()=>{const out={};for(const name of await caches.keys()){const c=await caches.open(name);out[name]=(await c.keys()).map(r=>new URL(r.url).pathname).sort();}return out;}''')
        expected = sorted(['/offline.html', '/icons/icon-192.png', '/icons/icon-512.png', '/icons/apple-touch-icon.png'])
        assert cache == {'bractwo-app-shell-0.8.18': expected}, cache
        passed('Native service worker controls localhost and caches only offline page/icons', service_worker=sw, cache=cache)
        # Browsers may expose a real install prompt. UI tests use the deterministic
        # help branch in a fresh context with only beforeinstallprompt suppressed.
        help_context, help_page = await new_page(390, 844, init="window.addEventListener('beforeinstallprompt',e=>{e.preventDefault();e.stopImmediatePropagation();},true)")
        await help_page.locator('#authInstallButton').click()
        await help_page.locator('#appHelpDialog').wait_for(state='visible')
        assert 'internetu' in await help_page.locator('#appHelpBody').inner_text()
        await help_page.screenshot(path=str(output / 'install-help.png'))
        await help_page.locator('#appHelpClose').click()
        passed('Install guidance opens and closes when no install prompt is available', simulation='beforeinstallprompt suppressed only')
        await help_context.close()
        await pwa_context.set_offline(True)
        await pwa.goto(base + '/?qa-offline=1', wait_until='domcontentloaded')
        assert 'brak połączenia' in (await pwa.title()).lower()
        assert 'wymaga internetu' in await pwa.locator('body').inner_text()
        api_failed = await pwa.evaluate("fetch('/health').then(()=>false).catch(()=>true)")
        assert api_failed, 'Offline API incorrectly received cached content'
        await pwa.screenshot(path=str(output / 'offline-390x844.png'))
        await pwa_context.set_offline(False)
        await pwa.locator('a').click()
        await pwa.locator('#authScreen').wait_for(state='visible')
        passed('Offline navigation shows honest connection page; API fails; reconnect loads current game')
        await pwa_context.close()

        for kind, script, expected_text in [
            ('unsupported', "Object.defineProperty(Element.prototype,'requestFullscreen',{value:undefined,configurable:true});Object.defineProperty(Element.prototype,'webkitRequestFullscreen',{value:undefined,configurable:true});", 'nie udostępnia'),
            ('denied', "Object.defineProperty(Element.prototype,'requestFullscreen',{value:function(){return Promise.reject(new DOMException('QA denied','NotAllowedError'));},configurable:true});", 'odmówiła'),
        ]:
            fallback_context, fallback = await new_page(390, 844, init=script)
            await fallback.locator('#authFullscreenButton').click()
            await fallback.locator('#appHelpDialog').wait_for(state='visible')
            assert expected_text in await fallback.locator('#appHelpBody').inner_text()
            assert not await fallback.locator('#authFullscreenButton').is_disabled()
            await fallback.screenshot(path=str(output / f'fullscreen-{kind}.png'))
            await fallback.keyboard.press('Escape')
            await fallback.locator('#appHelpDialog').wait_for(state='hidden')
            passed('Fullscreen fallback: ' + kind, simulation='fullscreen API deliberately replaced in isolated context')
            await fallback_context.close()
        issues = [issue for layout in report['layouts'] for issue in layout['issues']]
        assert not issues, '\n'.join(issues)
        assert not report['errors'], '\n'.join(report['errors'])
        report.update(ok=True, status='passed')
    except Exception as error:
        report.update(status='failed', failure=str(error), traceback=traceback.format_exc())
        print(report['traceback'], flush=True)
        for i, context in enumerate(contexts):
            for j, page in enumerate(context.pages):
                try:
                    await page.screenshot(path=str(output / f'failure-{i}-{j}.png'), timeout=10000)
                except Exception:
                    pass
    finally:
        if bridge:
            report['bridge_max_queued_messages'] = bridge.max_queue
        save()
        if bridge:
            await bridge.close()
        if browser:
            await browser.close()
        if pw:
            await pw.stop()
        await runner.cleanup()
    print(json.dumps({'ok': report['ok'], 'checks': len(report['checks']), 'layouts': len(report['layouts']), 'report': str(output / 'browser_results.json')}, ensure_ascii=False), flush=True)
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'docs/qa_0818'))
    parser.add_argument('--layout-only', action='store_true', help='Only verify the later joystick/drag-lock changes')
    parser.add_argument('--bridge', action='store_true', help='Use the established local Python WebSocket bridge; native SW checks are excluded and reported')
    raise SystemExit(asyncio.run(main(parser.parse_args())))
