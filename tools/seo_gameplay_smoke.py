"""Local Chromium regression: real game/auth HTTP and WS, fixture Google SDK.

Uses an ephemeral in-memory database and listens on localhost only. Google's
signature verification is replaced inside this process; no external requests,
real Google account, production server or persistent game save are used.
Run with: python3 tools/seo_gameplay_smoke.py
"""
import asyncio
import base64
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aiohttp import web
from playwright.async_api import async_playwright
from server.google_auth import GoogleAuthService
from server.server import create_app


GOOGLE_SDK = """(() => {
  let options;
  window.google = {accounts: {id: {
    initialize(value) { options = value; },
    renderButton(container) {
      const button = document.createElement('button');
      button.type = 'button'; button.textContent = 'Google — konto testowe';
      button.dataset.testid = 'fixture-google';
      button.addEventListener('click', () => {
        const now = Math.floor(Date.now() / 1000);
        const claims = {iss: 'https://accounts.google.com', aud: options.client_id,
          sub: window.__seoFixtureSubject, nonce: options.nonce, iat: now - 1, exp: now + 600};
        options.callback({credential: 'fixture.' + btoa(JSON.stringify(claims)) + '.fixture'});
      });
      container.append(button);
    }, cancel() {}, disableAutoSelect() {}
  }}};
})();
"""

PROBE = """window.__seoProbe = {draws: 0, worldDraws: 0, frames: 0};
const fillRect = CanvasRenderingContext2D.prototype.fillRect;
CanvasRenderingContext2D.prototype.fillRect = function (...args) {
  window.__seoProbe.draws++;
  if (this.canvas.id === 'world') window.__seoProbe.worldDraws++;
  return fillRect.apply(this, args);
};
const raf = window.requestAnimationFrame;
window.requestAnimationFrame = callback => raf(time => {
  window.__seoProbe.frames++;
  callback(time);
});
"""


def fixture_verifier(credential):
    header, payload, signature = credential.split('.')
    assert header == signature == 'fixture'
    claims = json.loads(base64.b64decode(payload))
    assert claims['sub'].startswith('seo-smoke-')
    return claims


async def main():
    auth = GoogleAuthService('seo-smoke.apps.googleusercontent.com',
                             'http://127.0.0.1:1', verifier=fixture_verifier)
    app = create_app(':memory:', google_auth_service=auth)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 0)
    await site.start()
    base = 'http://127.0.0.1:' + str(site._server.sockets[0].getsockname()[1])
    auth.allowed_origin = base
    app['comments'].allowed_origin = base
    report = []
    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                executable_path=shutil.which('chromium') or None,
                headless=True, args=['--no-sandbox'])
            try:
                for label, viewport, mobile in [('desktop', {'width': 1440, 'height': 900}, False),
                                                ('mobile', {'width': 390, 'height': 844}, True)]:
                    context = await browser.new_context(viewport=viewport, is_mobile=mobile,
                                                        has_touch=mobile, service_workers='block')
                    page = await context.new_page()
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))

                    async def route_request(route):
                        if route.request.url.startswith(base + '/'):
                            await route.continue_()
                        elif route.request.url == 'https://accounts.google.com/gsi/client?hl=pl':
                            await route.fulfill(status=200, content_type='application/javascript', body=GOOGLE_SDK)
                        else:
                            await route.abort()

                    await page.route('**/*', route_request)
                    await page.add_init_script(PROBE + '\nwindow.__seoFixtureSubject=' + json.dumps('seo-smoke-' + label))
                    await page.goto(base + '/', wait_until='load')
                    await page.get_by_test_id('fixture-google').wait_for(state='visible')
                    await page.wait_for_timeout(300)
                    idle = await page.evaluate('({...window.__seoProbe})')
                    await page.wait_for_timeout(350)
                    settled = await page.evaluate('({...window.__seoProbe})')
                    assert settled['draws'] == 0, (label, 'Landing rendered canvas', settled)
                    assert settled['frames'] == idle['frames'], (label, 'Landing has a repeating animation loop', idle, settled)

                    await page.get_by_test_id('fixture-google').click()
                    await page.locator('#googleName').fill('Seo' + label.title())
                    await page.locator('#googleContinue').click()
                    await page.locator('#gameUI').wait_for(state='visible')
                    await page.wait_for_function("document.querySelector('#playerName').textContent.startsWith('Seo')")
                    await page.wait_for_function('window.__seoProbe.worldDraws > 1')
                    assert not await page.locator('#authScreen').is_visible()
                    assert await page.evaluate("Array.from(document.querySelectorAll('link[rel=stylesheet]')).every(link => link.sheet && link.media !== 'print')")

                    before = await page.evaluate('window.__seoProbe.worldDraws')
                    await page.wait_for_timeout(200)
                    assert await page.evaluate('window.__seoProbe.worldDraws') > before
                    # Exercise an actual HUD panel after its stylesheet was loaded asynchronously.
                    await page.keyboard.press('c')
                    await page.locator('#characterPanel').wait_for(state='visible')
                    await page.locator('.character-close').click()

                    if mobile:
                        await page.locator('#mobileMenuButton').click()
                    await page.locator('#logoutButton').click()
                    await page.locator('#authScreen').wait_for(state='visible')
                    await page.get_by_test_id('fixture-google').wait_for(state='visible')
                    await page.wait_for_timeout(150)
                    stopped = await page.evaluate('window.__seoProbe.worldDraws')
                    await page.wait_for_timeout(200)
                    assert await page.evaluate('window.__seoProbe.worldDraws') == stopped

                    await page.get_by_test_id('fixture-google').click()
                    await page.locator('.google-character').click()
                    await page.locator('#gameUI').wait_for(state='visible')
                    await page.wait_for_function('before => window.__seoProbe.worldDraws > before', arg=stopped)
                    assert not errors, errors
                    report.append({'viewport': label, 'landing_canvas_draws': settled['draws'],
                                   'landing_recurring_frames': settled['frames'] - idle['frames'],
                                   'login_create_hud_logout_relogin': 'passed', 'javascript_errors': errors})
                    await context.close()
            finally:
                await browser.close()
    finally:
        await runner.cleanup()
    print(json.dumps({'ok': True, 'checks': report}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
