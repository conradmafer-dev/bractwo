"""Focused follow-up for joystick centring and explicitly unlocked HUD dragging."""
from tools.browser_mobile_smoke import stable_box


JOYSTICK_GAPS = """() => {
  const rect = el => {const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
  const joy=rect(document.getElementById('joystick'));
  const bar=rect(document.getElementById('spellbar'));
  const visible=el=>el.getClientRects().length && getComputedStyle(el).visibility!=='hidden' && !el.hasAttribute('data-hud-hidden');
  const rail=[document.querySelector('.player-card'),...document.getElementById('hudLeftRail').children].filter(visible);
  const landscape=innerWidth>innerHeight;
  const top=landscape?Math.max(...rail.map(el=>el.getBoundingClientRect().bottom)):bar.bottom+8;
  const right=landscape?bar.x:document.getElementById('interactButton').getBoundingClientRect().left;
  const floor=innerHeight;
  return {viewport:{width:innerWidth,height:innerHeight},issues:[],joystick:joy,bar,top,right,floor,
    gaps:{left:joy.x,right:right-joy.right,above:joy.y-top,below:floor-joy.bottom}};
}"""


async def run(new_page, login, output, report, passed):
    async def toggle_lock(page):
        mobile = await page.locator('#mobileMenuButton').is_visible()
        if mobile:
            await page.locator('#mobileMenuButton').click()
        await page.locator('#hudLayoutLock').click()
        if mobile:
            await page.locator('#mobileMenuClose').click()

    async def drag(page, delta_x, delta_y, touch, selector='.player-card .window-grip'):
        box = await page.locator(selector).bounding_box()
        if not box and selector == '.player-card .window-grip':
            # Locked grips are intentionally display:none. Try the card edge a
            # user can actually touch; hidden-handle events are covered by units.
            card = await page.locator('.player-card').bounding_box()
            box = {'x':card['x']+card['width']-22,'y':card['y']+4,'width':18,'height':18}
        assert box, 'Drag target has no bounds'
        x, y = box['x'] + box['width']/2, box['y'] + box['height']/2
        if touch:
            cdp = await page.context.new_cdp_session(page)
            await cdp.send('Input.dispatchTouchEvent', {'type':'touchStart','touchPoints':[{'x':x,'y':y}]})
            for part in (0.25, .5, .75, 1):
                await cdp.send('Input.dispatchTouchEvent', {'type':'touchMove','touchPoints':[{'x':x+delta_x*part,'y':y+delta_y*part}]})
            await cdp.send('Input.dispatchTouchEvent', {'type':'touchEnd','touchPoints':[]})
            await cdp.detach()
        else:
            await page.mouse.move(x, y)
            await page.mouse.down()
            await page.mouse.move(x+delta_x, y+delta_y, steps=5)
            await page.mouse.up()

    async def lock_check(page, touch, label):
        card = page.locator('.player-card')
        await page.locator('.player-card .window-grip').wait_for(state='attached')
        assert await page.locator('#hudLayoutLock').get_attribute('aria-pressed') == 'true'
        original = await stable_box(page, card)
        delta_x, delta_y = (80,60) if touch else (360,180)
        await drag(page, delta_x, delta_y, touch)
        still_locked = await stable_box(page, card)
        assert abs(still_locked['x']-original['x']) < 1 and abs(still_locked['y']-original['y']) < 1, 'Default lock allowed dragging'
        await toggle_lock(page)
        assert await page.locator('#hudLayoutLock').get_attribute('aria-pressed') == 'false'
        await drag(page, delta_x, delta_y, touch)
        moved = await stable_box(page, card)
        assert abs(moved['x']-original['x']) > 20 or abs(moved['y']-original['y']) > 20, 'Unlock did not enable dragging'
        await toggle_lock(page)
        assert await page.locator('#hudLayoutLock').get_attribute('aria-pressed') == 'true'
        await drag(page, 50, 40, touch)
        relocked = await stable_box(page, card)
        assert abs(relocked['x']-moved['x']) < 1 and abs(relocked['y']-moved['y']) < 1, 'Relocking allowed another drag'
        stored = await page.evaluate("()=>Object.fromEntries(Object.entries(localStorage).filter(([key])=>key.startsWith('bractwo-windows-')).map(([key,value])=>[key,JSON.parse(value)]))")
        prefix = 'bractwo-windows-mobile-v1:' if touch else 'bractwo-windows-v1:'
        profiles = {key:value for key,value in stored.items() if key.startswith(prefix) and value.get('positions',{}).get('player')}
        assert profiles and all(value.get('locked') is True for value in profiles.values()), 'Moved/locked profile not saved'
        await page.screenshot(path=str(output / f'layout-{label}-relocked.png'))
        passed(f'{label}: default lock prevents drag, unlock permits drag, relock prevents further movement', pointer='native CDP touch' if touch else 'native mouse', before=original, moved=moved, relocked=relocked, profiles=profiles)

    mobile_context, mobile = await new_page(734, 260, True)
    await login(mobile, 'LockMobileQA')
    for width, height in [(734,260),(390,844)]:
        await mobile.set_viewport_size({'width':width,'height':height})
        await stable_box(mobile, mobile.locator('#joystick'))
        measure = await mobile.evaluate(JOYSTICK_GAPS)
        gaps = measure['gaps']
        assert abs(gaps['left'] - gaps['right']) <= 2, f'Joystick horizontal gaps differ: {gaps}'
        assert abs(gaps['above'] - gaps['below']) <= 2, f'Joystick vertical gaps differ: {gaps}'
        assert min(gaps.values()) >= 0, f'Joystick overlaps surrounding controls: {gaps}'
        screenshot = f'joystick-{width}x{height}.png'
        measure['screenshot'] = screenshot
        report['layouts'].append(measure)
        await mobile.screenshot(path=str(output / screenshot))
        passed(f'Joystick has balanced free-space gaps at {width}x{height}', gaps=gaps)
    await mobile.set_viewport_size({'width':734,'height':260})
    await lock_check(mobile, True, 'mobile')
    await toggle_lock(mobile)
    await drag(mobile, 45, -35, True, '.movement-controls .window-grip')
    assert 'hud-floating' in await mobile.locator('.movement-controls').get_attribute('class'), 'Explicit joystick drag did not create a floating position'
    await toggle_lock(mobile)
    await mobile.locator('#mobileMenuButton').click()
    await mobile.get_by_role('button', name='Przywróć domyślny układ i widoczność', exact=True).click()
    await mobile.locator('#mobileMenuClose').click()
    assert await mobile.locator('#hudLayoutLock').get_attribute('aria-pressed') == 'true', 'Reset changed the locked state'
    assert 'hud-floating' not in await mobile.locator('.movement-controls').get_attribute('class')
    await stable_box(mobile, mobile.locator('#joystick'))
    reset_measure = await mobile.evaluate(JOYSTICK_GAPS)
    reset_gaps = reset_measure['gaps']
    assert abs(reset_gaps['left']-reset_gaps['right']) <= 2 and abs(reset_gaps['above']-reset_gaps['below']) <= 2
    await mobile.screenshot(path=str(output / 'joystick-reset-locked.png'))
    passed('Reset while locked restores the centred joystick after an explicit manual move', geometry=reset_measure)
    await mobile_context.close()
    desktop_context, desktop = await new_page(1440, 900)
    await login(desktop, 'LockDesktopQA')
    await lock_check(desktop, False, 'desktop')
    await desktop.locator('#hudLayoutLock').focus()
    await desktop.keyboard.press('Space')
    assert await desktop.locator('#hudLayoutLock').get_attribute('aria-pressed') == 'false'
    await desktop.keyboard.press('Enter')
    assert await desktop.locator('#hudLayoutLock').get_attribute('aria-pressed') == 'true'
    assert not await desktop.locator('#chatForm').is_visible(), 'Enter on lock opened chat'
    passed('Space/Enter activate the focused lock without opening chat')
    await desktop_context.close()
