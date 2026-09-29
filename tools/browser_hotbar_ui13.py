"""Production Chromium client and local in-memory server. No live player data."""
import asyncio,json,sys,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from aiohttp import web
from playwright.async_api import async_playwright
from tools.browser_0818_bridge import Bridge
from server.server import create_app
from server import dnd_content as dnd, druid_circles as circles
OUT=ROOT/'docs/qa_0.8.18/ui13';OUT.mkdir(parents=True,exist_ok=True)
class Clock:
    value=1000.
    def __call__(self):return self.value
    def advance(self):self.value+=3.1
async def until(fn,label):
    for _ in range(200):
        if fn():return
        await asyncio.sleep(.05)
    raise AssertionError(label)
async def main():
    report={'ok':False,'checks':[],'errors':[],'transport':'production HTML/CSS/JS in Chromium; Python WebSocket bridge to isolated in-memory server', 'limitations':['Browser navigation is blocked by container policy: production client is rendered with set_content in about:blank, an in-memory localStorage shim and the existing Python WebSocket bridge. Native hosting, browser persistence and service workers are not covered.']}
    def save():(OUT/'browser_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    def passed(name,**details):report['checks'].append(dict(name=name,**details));print('PASS',name,flush=True);save()
    clock=Clock();app=create_app(':memory:',clock=clock);game=app['game'];game.step_monsters=lambda *a,**k:None
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    url='http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1])
    bridge=Bridge(url)
    storage="""<script>const qaStore={};Object.defineProperty(window,'localStorage',{value:{getItem(k){return qaStore[k]??null},setItem(k,v){qaStore[k]=String(v)},removeItem(k){delete qaStore[k]},clear(){for(const k in qaStore)delete qaStore[k]}}});</script>"""
    bridge.html=bridge.html.replace('<head>','<head>'+storage,1)
    async def login(page,name):
        original_goto=page.goto
        async def inline_goto(*args,**kwargs):
            return await page.set_content(bridge.html,wait_until='load',timeout=20000)
        page.goto=inline_goto
        try:await bridge.load(page)
        finally:page.goto=original_goto
        await page.evaluate("()=>{window.__qaActions=[];const originalSend=WebSocket.prototype.send;WebSocket.prototype.send=function(raw){try{const p=JSON.parse(raw);if(p.type==='input')window.__qaInput=p;if(!['input','hello'].includes(p.type))window.__qaActions.push(p);}catch(_){}return originalSend.call(this,raw);};return true;}")
        await page.locator('#nameInput').fill(name);await page.locator('#passwordInput').fill('isolated-ui13-qa')
        await page.locator('#classPicker [data-class="druid"]').click();await page.locator('#connectButton').click()
        await page.locator('#gameUI').wait_for(state='visible')
        await until(lambda:any(p.name==name for p in game.players.values()),'registration')
        return next(p for p in game.players.values() if p.name==name)
    def promote(p,circle='stars',level=15):
        p.level=level;p.druid_circle=circle;game.migrate_druid_circle(p);p.hp=p.max_hp;p.mana=p.max_mana;game.clear_caster_caches(p)
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-proxy-server'])
            context=await browser.new_context(viewport={'width':1649,'height':850},device_scale_factor=1)
            await context.add_init_script("window.__qaActions=[];const send=WebSocket.prototype.send;WebSocket.prototype.send=function(raw){try{const p=JSON.parse(raw);if(p.type==='input')window.__qaInput=p;if(!['input','hello'].includes(p.type))window.__qaActions.push(p);}catch(_){}return send.call(this,raw);};")
            page=await context.new_page();page.set_default_timeout(12000);page.on('pageerror',lambda e:report['errors'].append(str(e)))
            try:
                print('Opening',url,flush=True);p=await login(page,'HotbarQA');promote(p)
                star=page.locator('.hotbar-slot[data-spell="group_starry_form"]')
                await star.wait_for(state='visible');await page.wait_for_timeout(200)
                occupied=await page.locator('.hotbar-slot:not(.empty)').count();assert occupied==17,occupied
                passed('Level-15 Stars: 17 occupied slots instead of 21',occupied=occupied)
                await page.screenshot(path=str(OUT/'desktop-level15.png'))
                await star.click();await page.locator('#hotbarGroupMenu').wait_for(state='visible')
                assert await page.locator('#hotbarGroupMenu [data-spell^="circle_star_"]').count()==3
                assert '2/2' in await page.locator('.hotbar-group-resource').inner_text()
                await page.screenshot(path=str(OUT/'desktop-star-menu.png'))
                await page.locator('#hotbarGroupMenu [data-spell="circle_star_archer"]').focus();await page.keyboard.press('Enter')
                await until(lambda:circles.starry_form(p)=='archer','Archer activation')
                await page.wait_for_function("document.querySelector('.hotbar-slot[data-spell=group_starry_form] small').textContent==='Gwiezdna strzała'")
                assert circles.shape_remaining(p)==1;clock.advance();await page.wait_for_timeout(150);await star.click()
                await until(lambda:p.bonus_cooldown_until>clock(),'arrow action')
                actions=await page.evaluate('window.__qaActions');assert actions[-1].get('spell_id')=='circle_star_arrow',actions[-1]
                assert circles.shape_remaining(p)==1
                passed('Archer main shortcut shoots without another transformation use')
                circles.state(p)['shape_spent']=2;game.clear_caster_caches(p);clock.advance();await page.wait_for_timeout(250)
                await star.locator('..').locator('.hotbar-group-toggle').click()
                await page.wait_for_function("document.querySelector('#hotbarGroupMenu [data-spell=circle_star_chalice]').disabled")
                assert '0/2' in await page.locator('.hotbar-group-resource').inner_text()
                assert not await page.locator('#hotbarGroupMenu [data-spell="circle_star_arrow"]').is_disabled()
                await page.screenshot(path=str(OUT/'desktop-empty-resource.png'))
                passed('Zero uses blocks new forms, not the active Archer arrow')
                await page.keyboard.press('Escape');await page.locator('#hotbarGroupMenu').wait_for(state='hidden')
                before=await page.evaluate('window.__qaActions.length');await page.locator('#world').click(position={'x':1100,'y':330})
                assert await page.locator('#groundTargetHint:visible').count()==0
                assert await page.evaluate('window.__qaActions.length')==before
                passed('Empty-ground click neither clears a target nor opens a crosshair')
                await page.keyboard.press('KeyK');await page.locator('#characterPanel').wait_for(state='visible')
                await page.locator('.sheet-spell[data-spell="circle_star_dragon"] .slot-picker').select_option('0')
                await page.wait_for_function("document.querySelector('.hotbar-slot[data-slot=\"0\"]').dataset.spell==='group_starry_form'")
                assert dnd.grouped_hotbar(p)[0]=='group_starry_form'
                assert all(not key or key in dnd.SPELLS for key in p.hotbar)
                await page.keyboard.press('Escape');await page.locator('#characterPanel').wait_for(state='hidden')
                passed('Book assignment moves the whole group and keeps real-spell save data')
                promote(p,'sea',80);p.hotbar=[];p.buffs={};p.form='';clock.advance();game.clear_caster_caches(p)
                await page.wait_for_function("!document.querySelector('#hotbarPages').hidden")
                await page.wait_for_timeout(150);first=await page.locator('#hotbarPageLabel').inner_text()
                await page.locator('#hotbarNext').click();assert await page.locator('#hotbarPageLabel').inner_text()!=first
                await page.keyboard.press('PageUp');assert await page.locator('#hotbarPageLabel').inner_text()==first
                passed('High-level spells remain on extra pages, navigable by mouse and keyboard',pages=len(dnd.grouped_hotbar(p))//24)
                dnd.sync_hotbar(p);await game.bind_grouped_spell(p,0,'fog_cloud')
                await page.wait_for_function("document.querySelector('.hotbar-slot[data-slot=\"0\"]').dataset.spell==='fog_cloud'")
                before_mana=p.mana;await page.keyboard.press('Digit1');await page.locator('#groundTargetHint').wait_for(state='visible')
                assert p.mana==before_mana;await page.screenshot(path=str(OUT/'desktop-explicit-targeting.png'))
                await page.keyboard.press('Escape');await page.locator('#groundTargetHint').wait_for(state='hidden');assert p.mana==before_mana
                await page.keyboard.press('Digit1');await page.locator('#groundTargetHint').wait_for(state='visible')
                await page.locator('#world').click(position={'x':1100,'y':330});await page.locator('#groundTargetHint').wait_for(state='hidden')
                last=await page.evaluate('window.__qaActions.at(-1)')
                assert last['type']=='cast_circle_spell' and last['spell']=='fog_cloud' and 'point' in last['options'],last
                passed('Ground spell arms targeting first; cancel is free; confirmation sends an explicit point')
                mobile=await browser.new_context(viewport={'width':844,'height':390},is_mobile=True,has_touch=True,device_scale_factor=1)
                page=await mobile.new_page();page.set_default_timeout(12000);page.on('pageerror',lambda e:report['errors'].append(str(e)))
                p=await login(page,'MobileHotbar');promote(p);dnd.sync_hotbar(p);await game.bind_grouped_spell(p,0,'circle_star_archer')
                await page.locator('.hotbar-slot[data-slot="0"][data-spell="group_starry_form"]').wait_for(state='visible')
                for width,height in [(844,390),(390,844),(734,260)]:
                    await page.set_viewport_size({'width':width,'height':height});await page.wait_for_timeout(200)
                    await page.locator('.hotbar-slot[data-spell="group_starry_form"]').tap();await page.locator('#hotbarGroupMenu').wait_for(state='visible')
                    rect=await page.locator('#hotbarGroupMenu').bounding_box()
                    assert rect and rect['x']>=0 and rect['y']>=0 and rect['x']+rect['width']<=width+1 and rect['y']+rect['height']<=height+1,rect
                    await page.screenshot(path=str(OUT/f'mobile-menu-{width}x{height}.png'))
                    await page.locator('#hotbarGroupMenu header button').tap()
                    passed(f'Touch menu fits {width}×{height}',bounds=rect)
                scroller=page.locator('.hotbar-viewport');await scroller.evaluate('e=>e.scrollLeft=0')
                joy=await page.locator('#joystick').bounding_box();bar=await scroller.bounding_box()
                assert joy and bar
                cdp=await mobile.new_cdp_session(page)
                finger={'id':1,'x':joy['x']+joy['width']/2,'y':joy['y']+joy['height']/2}
                async def touch(kind,points):
                    await cdp.send('Input.dispatchTouchEvent',{'type':kind,'touchPoints':points})
                    await page.wait_for_timeout(80)
                await touch('touchStart',[finger]);finger['x']+=20;await touch('touchMove',[finger])
                assert (await page.evaluate('window.__qaInput'))['x']>0
                second={'id':2,'x':bar['x']+bar['width']-24,'y':bar['y']+bar['height']/2}
                actions_before=await page.evaluate('window.__qaActions.length')
                await touch('touchStart',[finger,second]);second['x']-=45;await touch('touchMove',[finger,second]);second['x']-=45;await touch('touchMove',[finger,second])
                assert await scroller.evaluate('e=>e.scrollLeft')>20
                # CDP touchEnd lists released contacts, not the contacts remaining down.
                await touch('touchEnd',[second]);assert (await page.evaluate('window.__qaInput'))['x']>0
                assert await page.evaluate('window.__qaActions.length')==actions_before
                await touch('touchEnd',[])
                passed('Second-finger hotbar swipe scrolls grouped slots, casts nothing and keeps joystick movement')
                assert not report['errors'],report['errors'];passed('No browser JavaScript errors');report['ok']=True;save()
            except Exception:
                report['failure']=traceback.format_exc();save()
                try:await page.screenshot(path=str(OUT/'failure.png'))
                except Exception:pass
                raise
            finally:
                await bridge.close()
                await browser.close()
    finally:
        await bridge.close()
        await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
