"""UI_17: positive level-up receipt and unchanged free casting in the real web UI.

Embedded production web client + Python WS bridge, isolated in-memory server.
This is a Chromium desktop/touch simulation, not a physical Android test.
"""
import asyncio
import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aiohttp import web
from playwright.async_api import async_playwright
from tools.browser_0818_bridge import Bridge
from server.server import create_app, xp_next
from server import dnd_content as dnd, level_up

OUT = ROOT / 'docs/qa_0.8.18/ui17'
OUT.mkdir(parents=True, exist_ok=True)


class Clock:
    value = 1000.0
    def __call__(self):
        return self.value


async def until(fn, label):
    for _ in range(200):
        if fn():
            return
        await asyncio.sleep(.05)
    raise AssertionError(label)


async def main():
    report = {'ok': False, 'checks': [], 'errors': [], 'limitations': [
        'Production HTML/JS/CSS embedded in about:blank using the existing Python WebSocket bridge; isolated real server in memory.',
        'No physical Android or live Railway test; no full-game regression.',
    ]}
    def save():
        (OUT / 'browser_results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    def passed(name, **details):
        report['checks'].append(dict(name=name, **details))
        print('PASS', name, flush=True)
        save()

    clock = Clock()
    app = create_app(':memory:', clock=clock)
    game = app['game']
    game.step_monsters = lambda *a, **k: None
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    bridge = Bridge('http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1]))
    bridge.html = bridge.html.replace('<head>', '''<head><script>const qaStore={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>qaStore[k]??null,setItem:(k,v)=>qaStore[k]=String(v),removeItem:k=>delete qaStore[k]}});</script>''', 1)

    async def login(page, name):
        old = page.goto
        async def inline(*a, **k):
            await page.set_content(bridge.html, wait_until='load', timeout=20000)
        page.goto = inline
        try:
            await bridge.load(page)
        finally:
            page.goto = old
        assert 'UI_17' in await page.locator('.auth-foot').inner_text()
        await page.locator('#nameInput').fill(name)
        await page.locator('#passwordInput').fill('isolated-ui17-tests')
        await page.locator('#classPicker [data-class=druid]').click()
        await page.locator('#connectButton').click()
        await page.locator('#gameUI').wait_for(state='visible')
        await until(lambda: any(p.name == name for p in game.players.values()), 'login')
        p = next(p for p in game.players.values() if p.name == name)
        p.level = 19
        p.druid_circle = 'stars'
        game.migrate_druid_circle(p)
        p.druid_circle_state.update(map_equipped=True, guiding_bolt_spent=3)
        p.level_up_batches = []
        p._level_up_cache = None
        p.hp = p.max_hp
        p.mana = p.max_mana
        p.xp = 0
        game.clear_caster_caches(p)
        dnd.sync_hotbar(p)
        await page.locator('.hotbar-slot[data-spell=guiding_bolt]').wait_for(state='attached')
        return p

    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True,
                                               args=['--no-sandbox', '--no-proxy-server'])
            for mode in ('desktop', 'touch-landscape'):
                config = {'viewport': {'width': 1440, 'height': 900}} if mode == 'desktop' else {
                    'viewport': {'width': 820, 'height': 390}, 'screen': {'width': 850, 'height': 420},
                    'is_mobile': True, 'has_touch': True, 'device_scale_factor': 2,
                }
                context = await browser.new_context(**config)
                page = await context.new_page()
                page.set_default_timeout(12000)
                page.on('pageerror', lambda error: report['errors'].append(str(error)))
                try:
                    p = await login(page, 'DesktopUi17' if mode == 'desktop' else 'MobileUi17')
                    await page.locator('#bookSpell').click()
                    spell = page.locator('.sheet-spell[data-spell=guiding_bolt]')
                    await spell.wait_for()
                    await page.wait_for_function("document.querySelector('.sheet-spell[data-spell=guiding_bolt]')?.textContent.includes('Poziom 20: +1k6')")
                    passed(mode + ': positive next-upgrade hint at level 19')
                    await page.locator('#characterPanel .character-close').click()
                    game.award(p, xp_next(19), 0)
                    event = level_up.pending(p)['pending_level_ups'][-1]
                    card = page.locator('.level-up-card[data-level="20"]')
                    await card.wait_for()
                    damage = card.locator('[data-change=spell_damage_dice_guiding_bolt]')
                    mana = card.locator('[data-change=spell_mana_guiding_bolt]')
                    assert await damage.locator('.level-up-gain').inner_text() == '+1k6'
                    assert await mana.locator('.level-up-gain').inner_text() == '+20'
                    assert '-1k6' not in await card.inner_text()
                    assert await damage.locator('img').evaluate('(i) => i.complete && i.naturalWidth > 0')
                    await mana.scroll_into_view_if_needed()
                    await page.screenshot(path=str(OUT / (mode + '-level-20.png')))
                    passed(mode + ': real award renders +1k6 and +20, icon loads',
                           damage=await damage.inner_text(), mana=await mana.inner_text())
                    bar = list(p.hotbar)
                    p.druid_circle_state['guiding_bolt_spent'] = 0
                    game.clear_caster_caches(p)
                    await page.wait_for_timeout(350)
                    assert await damage.locator('.level-up-gain').inner_text() == '+1k6'
                    assert p.hotbar == bar
                    passed(mode + ': resource update neither rewrites receipt nor rearranges shortcuts')
                    await card.locator('.level-up-close').click()
                    await until(lambda: not level_up.pending(p)['pending_level_ups'], 'receipt closed')
                    await page.locator('#bookSpell').click()
                    await spell.wait_for()
                    await page.wait_for_function("document.querySelector('.sheet-spell[data-spell=guiding_bolt]')?.textContent.includes('Poziom 30: +1k6')")
                    profiles = p.public(clock(), private=True)['spell_profiles']['guiding_bolt']
                    assert profiles['dice'] == [4, 6, 0] and profiles['mana'] == 0
                    sections = await page.locator('[data-spell-section]').evaluate_all('(rows) => rows.map(r=>r.dataset.spellSection)')
                    assert len(sections) == len(set(sections)) and sections[-1] == 'features'
                    assert await page.evaluate('BractwoMobile.active()') == (mode == 'touch-landscape')
                    passed(mode + ': dismiss works, free basic bolt unchanged, ordered sections retained')
                except Exception:
                    report['failure'] = traceback.format_exc()
                    save()
                    await page.screenshot(path=str(OUT / 'browser-failure.png'))
                    raise
                finally:
                    await context.close()
            assert not report['errors'], report['errors']
            report['ok'] = True
            report['source_hashes'] = bridge.source_hashes
            save()
            await bridge.close()
            await browser.close()
    finally:
        await bridge.close()
        await runner.cleanup()


if __name__ == '__main__':
    asyncio.run(main())
