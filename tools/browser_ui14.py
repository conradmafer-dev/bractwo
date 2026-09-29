"""UI_14: actual browser controls + isolated production server via WS bridge.
Fullscreen API is real; viewport/visual-scale transitions are controlled simulations.
No access to live Railway, no production credentials, no physical Android device.
"""
import asyncio,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from aiohttp import web
from playwright.async_api import async_playwright
from tools.browser_0818_bridge import Bridge
from server.server import create_app
from server import druid_circles as circles,dnd_content as dnd
OUT=ROOT/'docs/qa_0.8.18/ui14';OUT.mkdir(parents=True,exist_ok=True)
class Clock:
    value=1000.
    def __call__(self):return self.value
    def advance(self,dt=3.1):self.value+=dt
async def until(fn,label):
    for _ in range(200):
        if fn():return
        await asyncio.sleep(.05)
    raise AssertionError(label)
METRICS="""() => {const rect=s=>{const r=document.querySelector(s).getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}};const slot=rect('.hotbar-slot:not(.empty)'),bar=rect('.hotbar-viewport');return {w:innerWidth,h:innerHeight,visualScale:visualViewport.scale,dpr:devicePixelRatio,full:!!document.fullscreenElement,mobile:BractwoMobile.active(),unit:BractwoMobile.uiScale(),camera:window.__qaWorldScale,slot,bar,card:rect('.player-card'),ui:rect('#gameUI'),fullyVisibleSlots:[...document.querySelectorAll('.hotbar-slot:not(.empty)')].filter(e=>{const r=e.getBoundingClientRect();return r.left>=bar.x-.5&&r.right<=bar.x+bar.w+.5}).length,docWidth:document.documentElement.scrollWidth}}"""
async def main():
    report={'ok':False,'checks':[],'errors':[],'transport':'Embedded production HTML/CSS/JS, Chromium with actual in-memory Python server over existing WS bridge',
        'limitations':['Navigation blocked in container: about:blank/set_content, in-memory localStorage shim and Python WS bridge; no native HTTP navigation, persistent browser storage or service-worker lifecycle test.',
        'Fullscreen API invoked by real touch. Android OS bar changes are modeled by controlled viewport resizing; browser shrink modeled by overriding VisualViewport.scale and emitting resize. This is not a physical-phone test.']}
    def save():(OUT/'browser_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    def passed(name,**detail):report['checks'].append(dict(name=name,**detail));print('PASS',name,flush=True);save()
    clock=Clock();app=create_app(':memory:',clock=clock);g=app['game'];g.step_monsters=lambda *a,**k:None
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    bridge=Bridge('http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]))
    storage="""<script>const qaStore={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>qaStore[k]??null,setItem:(k,v)=>qaStore[k]=String(v),removeItem:k=>delete qaStore[k]}});</script>"""
    bridge.html=bridge.html.replace('<head>','<head>'+storage,1)
    async def login(page,name):
        original=page.goto
        async def inline(*args,**kwargs):await page.set_content(bridge.html,wait_until='load',timeout=20000)
        page.goto=inline
        try:await bridge.load(page)
        finally:page.goto=original
        await page.evaluate("""()=>{window.__qaActions=[];const send=WebSocket.prototype.send;WebSocket.prototype.send=function(raw){const p=JSON.parse(raw);if(p.type==='input')window.__qaInput=p;else if(p.type!=='hello')window.__qaActions.push(p);return send.call(this,raw)};
          const scale=CanvasRenderingContext2D.prototype.scale;CanvasRenderingContext2D.prototype.scale=function(x,y){const m=this.getTransform(),dpr=Math.min(devicePixelRatio,2);if(this.canvas.id==='world'&&Math.abs(m.a-dpr)<1e-5&&Math.abs(m.e-Math.round(innerWidth/2)*dpr)<.1&&Math.abs(m.f-Math.round(innerHeight/2)*dpr)<.1)window.__qaWorldScale=x;return scale.call(this,x,y);};} """)
        await page.locator('#nameInput').fill(name);await page.locator('#passwordInput').fill('isolated-ui14-tests')
        await page.locator('#classPicker [data-class=druid]').click();await page.locator('#connectButton').click()
        await page.locator('#gameUI').wait_for(state='visible');await until(lambda:any(p.name==name for p in g.players.values()),'login')
        p=next(p for p in g.players.values() if p.name==name)
        p.level=15;p.druid_circle='stars';g.migrate_druid_circle(p);p.hp=p.max_hp;p.mana=p.max_mana
        p.caster_path='warden';g.clear_caster_caches(p);await g.bind_grouped_spell(p,0,'circle_star_archer')
        await page.locator('.hotbar-slot[data-slot="0"][data-spell=group_starry_form]').wait_for(state='visible')
        # Close an optional newly-unlocked path prompt without changing production UI.
        await page.evaluate("document.querySelector('.caster-path-prompt button[aria-label]')?.click()")
        await page.wait_for_timeout(350)
        return p
    async def settled(page):await page.wait_for_timeout(280)
    async def close_menu(page):await page.locator('#hotbarGroupMenu header button').tap()
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-proxy-server'])
            context=await browser.new_context(viewport={'width':760,'height':340},screen={'width':800,'height':400},device_scale_factor=2,is_mobile=True,has_touch=True)
            page=await context.new_page();page.set_default_timeout(12000);page.on('pageerror',lambda e:report['errors'].append(str(e)))
            try:
                p=await login(page,'MobileUi14')
                star=page.locator('.hotbar-slot[data-spell=group_starry_form]');toggle=star.locator('..').locator('.hotbar-group-toggle')
                normal=await page.evaluate(METRICS);assert normal['fullyVisibleSlots']>=12,normal
                assert normal['slot']['w']<41 and normal['docWidth']==normal['w'],normal
                assert abs(normal['camera']-.95*.85*.74)<.0001,normal
                passed('Compact mobile HUD and actual render zoom',metrics=normal)
                await page.screenshot(path=str(OUT/'mobile-normal.png'))
                await star.tap();await page.locator('#hotbarGroupMenu [data-spell=circle_star_archer]').tap()
                await until(lambda:circles.starry_form(p)=='archer','archer');await page.wait_for_function("document.querySelector('[data-spell=group_starry_form] small').textContent==='Strzała'")
                assert await star.is_disabled()
                assert 'Łucznik' in await page.locator('#effectsPanel').inner_text()
                icon=await star.locator('img').evaluate('(e)=>({loaded:e.complete&&e.naturalWidth>0,source:e.src})')
                assert icon['loaded']
                assert await star.locator('img').get_attribute('src')!=await page.locator('.hotbar-slot[data-spell=starry_wisp] img').get_attribute('src')
                passed('Touch activation shows Strzała, loaded distinct icon, named status and cooldown')
                clock.advance();await settled(page);await star.tap()
                await until(lambda:p.bonus_cooldown_until>clock(),'arrow');last=await page.evaluate('window.__qaActions.at(-1)')
                assert last.get('spell_id')=='circle_star_arrow',last;assert circles.shape_remaining(p)==1
                passed('Main touch sends Star Arrow, never another transformation')
                circles.state(p)['shape_spent']=2;g.clear_caster_caches(p);await settled(page)
                for w,h in [(760,340),(734,260),(390,844)]:
                    await page.set_viewport_size({'width':w,'height':h});await settled(page)
                    await toggle.tap();await page.locator('#hotbarGroupMenu').wait_for(state='visible')
                    leave=page.locator('[data-action=dismiss_star_form]');r=await leave.bounding_box();panel=await page.locator('#hotbarGroupMenu').bounding_box()
                    assert r and r['y']>=0 and r['y']+r['height']<=h,r
                    assert not await leave.is_disabled();assert '0/2' in await page.locator('.hotbar-group-resource').inner_text()
                    assert panel['x']>=0 and panel['y']>=0 and panel['x']+panel['width']<=w+1 and panel['y']+panel['height']<=h+1,panel
                    await page.locator('.hotbar-group-options').evaluate('e=>e.scrollTop=e.scrollHeight')
                    after=await leave.bounding_box();assert abs(after['y']-r['y'])<.1
                    await page.screenshot(path=str(OUT/f'dismiss-{w}x{h}.png'))
                    passed(f'Powrót do druida stays visible and enabled at 0/2, {w}×{h}',bounds=r)
                    await close_menu(page)
                await toggle.tap();await page.locator('[data-action=dismiss_star_form]').tap()
                await until(lambda:not circles.starry_form(p),'dismiss at zero');await page.wait_for_function("document.querySelector('[data-spell=group_starry_form] small').textContent==='Gwiazdy'")
                assert circles.shape_remaining(p)==0;assert not p.buffs.get('starry_form')
                passed('Touch dismissal works with no uses and during bonus cooldown; no refund')
                await page.set_viewport_size({'width':760,'height':340});await settled(page)
                circles.state(p)['shape_spent']=0;clock.advance();g.clear_caster_caches(p);await settled(page)
                await star.tap();await page.locator('#hotbarGroupMenu [data-spell=circle_star_chalice]').tap()
                await until(lambda:circles.starry_form(p)=='chalice','chalice');await page.wait_for_function("document.querySelector('[data-spell=group_starry_form] small').textContent==='Kielich'")
                assert 'Powrót' in await star.inner_text();await star.tap();await until(lambda:not circles.starry_form(p),'chalice main dismissal')
                assert circles.shape_remaining(p)==1
                passed('Kielich main shortcut returns to druid without a second activation')
                clock.advance();await settled(page);await star.tap();await page.locator('#hotbarGroupMenu [data-spell=circle_star_archer]').tap()
                await until(lambda:circles.starry_form(p)=='archer','last-use archer');clock.advance();await settled(page)
                await star.tap();await until(lambda:p.bonus_cooldown_until>clock(),'zero-use arrow')
                assert circles.shape_remaining(p)==0 and (await page.evaluate('window.__qaActions.at(-1)')).get('spell_id')=='circle_star_arrow'
                passed('Last-use Archer continues shooting with pool 0/2')
                # Actual fullscreen entry, with controlled Android-like drawable-area change.
                await page.locator('#mobileFullscreenButton').tap();await page.wait_for_function('!!document.fullscreenElement')
                await page.set_viewport_size({'width':800,'height':400});await settled(page)
                full=await page.evaluate(METRICS)
                for field in ['slot','card']:assert abs(full[field]['w']-normal[field]['w'])<.1,(field,normal,full)
                assert abs(full['camera']-normal['camera'])<.00001 and full['fullyVisibleSlots']>=normal['fullyVisibleSlots'],full
                await page.screenshot(path=str(OUT/'mobile-fullscreen.png'));passed('Fullscreen keeps compact HUD/world scale when drawable area grows',metrics=full)
                await toggle.tap();await page.locator('[data-action=dismiss_star_form]').tap();await until(lambda:not circles.starry_form(p),'fullscreen dismissal')
                passed('Druid dismissal also works in fullscreen')
                await page.locator('#mobileFullscreenButton').tap();await page.wait_for_function('!document.fullscreenElement')
                await page.set_viewport_size({'width':760,'height':340});await settled(page);back=await page.evaluate(METRICS)
                assert abs(back['slot']['w']-normal['slot']['w'])<.1 and abs(back['camera']-normal['camera'])<.00001
                passed('Leaving fullscreen restores available area, not a larger HUD or camera')
                for w,h in [(1000,599),(1100,650)]:
                    await page.set_viewport_size({'width':w,'height':h});await settled(page);metrics=await page.evaluate(METRICS)
                    assert metrics['mobile'] and abs(metrics['camera']-normal['camera'])<.00001 and abs(metrics['slot']['w']-normal['slot']['w'])<.1,metrics
                passed('Touch profile and world zoom survive former height/breakpoint transition')
                await page.set_viewport_size({'width':760,'height':340});await settled(page)
                await page.evaluate("Object.defineProperty(visualViewport,'scale',{configurable:true,get:()=>0.73});visualViewport.dispatchEvent(new Event('resize'))")
                await settled(page);shrunk=await page.evaluate(METRICS)
                assert abs(shrunk['slot']['w']*.73-normal['slot']['w'])<.08,(normal,shrunk)
                assert abs(shrunk['camera']*.73-normal['camera'])<.00001
                await page.evaluate("delete visualViewport.scale;visualViewport.dispatchEvent(new Event('resize'))")
                await settled(page);restored=await page.evaluate(METRICS)
                assert abs(restored['slot']['w']-normal['slot']['w'])<.1 and abs(restored['camera']-normal['camera'])<.00001
                passed('Controlled browser shrink-to-1 reset is compensated exactly once',shrunk=shrunk,restored=restored)
                # Confirm ordinary desktop rendering is not forced into compact mobile.
                desktop=await browser.new_context(viewport={'width':1649,'height':850},device_scale_factor=1)
                dp=await desktop.new_page();dp.on('pageerror',lambda e:report['errors'].append(str(e)))
                await login(dp,'DesktopUi14');dm=await dp.evaluate(METRICS)
                assert not dm['mobile'] and abs(dm['camera']-1.2)<.00001,dm
                passed('Desktop retains its own layout and camera profile',metrics=dm)
                assert not report['errors'],report['errors'];passed('No browser JavaScript errors')
                report['source_hashes']=bridge.source_hashes;report['ok']=True;save()
            except Exception:
                report['failure']=traceback.format_exc();save();await page.screenshot(path=str(OUT/'failure.png'));raise
            finally:await bridge.close();await browser.close()
    finally:await bridge.close();await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
