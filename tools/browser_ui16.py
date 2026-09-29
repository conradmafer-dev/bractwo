"""UI_16: render the production spellbook against an isolated real server.
Chromium local navigation is blocked in this environment, so production files are
embedded with the existing Python WebSocket bridge. No production data is used.
"""
import asyncio, json, sys, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from aiohttp import web
from playwright.async_api import async_playwright
from tools.browser_0818_bridge import Bridge
from server.server import create_app
from server import dnd_content as dnd, spell_scaling
OUT=ROOT/'docs/qa_0.8.18/ui16';OUT.mkdir(parents=True,exist_ok=True)
class Clock:
    value=1000.
    def __call__(self):return self.value
async def until(fn,label):
    for _ in range(200):
        if fn():return
        await asyncio.sleep(.05)
    raise AssertionError(label)
GROUPS="""() => {const groups=[];for(const el of document.querySelector('.sheet-spell-list').children){if(el.dataset.spellSection)groups.push({id:el.dataset.spellSection,label:el.textContent,spells:[]});else if(el.dataset.spell)groups.at(-1).spells.push(el.dataset.spell);}return groups;}"""
async def main():
    report={'ok':False,'checks':[],'errors':[],'limitations':['Production HTML/JS/CSS embedded in about:blank because Chromium local navigation is blocked; real isolated Python server over the existing WS bridge.','No physical Android test or live Railway deployment. No combat-balance regression in this scope.']}
    def save():(OUT/'browser_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
    def passed(name,**details):report['checks'].append(dict(name=name,**details));print('PASS',name,flush=True);save()
    clock=Clock();app=create_app(':memory:',clock=clock);game=app['game'];game.step_monsters=lambda *a,**k:None
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
    bridge=Bridge('http://127.0.0.1:'+str(site._server.sockets[0].getsockname()[1]))
    bridge.html=bridge.html.replace('<head>','''<head><script>const qaStore={};Object.defineProperty(window,'localStorage',{value:{getItem:k=>qaStore[k]??null,setItem:(k,v)=>qaStore[k]=String(v),removeItem:k=>delete qaStore[k]}});</script>''',1)
    async def login(page,name):
        old=page.goto
        async def inline(*a,**k):await page.set_content(bridge.html,wait_until='load',timeout=20000)
        page.goto=inline
        try:await bridge.load(page)
        finally:page.goto=old
        await page.locator('#nameInput').fill(name);await page.locator('#passwordInput').fill('isolated-ui16-tests')
        await page.locator('#classPicker [data-class=druid]').click();await page.locator('#connectButton').click()
        await page.locator('#gameUI').wait_for(state='visible');await until(lambda:any(p.name==name for p in game.players.values()),'login')
        p=next(p for p in game.players.values() if p.name==name);p.level=18;p.druid_circle='stars';game.migrate_druid_circle(p)
        p.hp=p.max_hp;p.mana=p.max_mana;game.clear_caster_caches(p);dnd.sync_hotbar(p)
        await page.locator('.hotbar-slot[data-spell=guidance]').wait_for(state='attached');await page.wait_for_timeout(300)
        await page.locator('#bookSpell').click();await page.locator('#characterContent .sheet-spell[data-spell=guidance]').wait_for()
        return p
    def validate(groups,p):
        ids=[g['id'] for g in groups];rows=[s for g in groups for s in g['spells']]
        assert len(ids)==len(set(ids)),ids;assert len(rows)==len(set(rows)),rows
        expected=[k for k,s in dnd.SPELLS.items() if p.class_id in s['class_ids'] or spell_scaling.client_profiles(p)[k].get('available')]
        assert set(rows)==set(expected)
        assert ids==['circle-'+str(n) for n in range(10)]+['features'],ids
        for g in groups:
            assert g['spells']
            for key in g['spells']:
                s=dnd.SPELLS[key];assert g['id']==('features' if s.get('feature') else 'circle-'+str(s['circle'])),(key,g['id'])
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--no-proxy-server'])
            context=await browser.new_context(viewport={'width':1440,'height':900})
            page=await context.new_page();page.set_default_timeout(12000);page.on('pageerror',lambda e:report['errors'].append(str(e)))
            try:
                p=await login(page,'DesktopUi16');groups=await page.evaluate(GROUPS);validate(groups,p)
                passed('Desktop: all ten spell-rank sections occur once, class features last',groups=groups)
                assert 'guidance' in groups[0]['spells'] and 'shillelagh' in groups[0]['spells']
                assert 'guiding_bolt' in groups[1]['spells'] and 'healing_word' in groups[1]['spells']
                passed('Subclass grants are mixed with native spells of the same base rank')
                assert await page.evaluate("""() => [...document.querySelectorAll('.sheet-spell-list img')].every(i=>i.complete&&i.naturalWidth>0)""")
                passed('All displayed web spell icons load, including Guidance and Guiding Bolt')
                saved=list(p.hotbar)
                await page.locator('.sheet-spell[data-spell=guiding_bolt]').scroll_into_view_if_needed()
                await page.screenshot(path=str(OUT/'desktop-circle-I.png'))
                power=page.locator('.sheet-spell[data-spell=guiding_bolt] .spell-power-picker')
                await power.select_option('1');await power.blur();await until(lambda:p.spell_circle_choices.get('guiding_bolt')==1,'selected rank 1')
                await page.wait_for_timeout(250);assert await page.evaluate(GROUPS)==groups
                await power.select_option('0');await power.blur();await until(lambda:not p.spell_circle_choices.get('guiding_bolt'),'automatic power')
                await page.wait_for_timeout(250);assert await page.evaluate(GROUPS)==groups
                passed('Changing spell power does not move the spell between sections')
                assert p.hotbar==saved
                passed('Opening and refreshing the sorted book preserves saved hotbar order')
                skill=page.locator('.sheet-spell[data-spell=guidance] .circle-spell-options select')
                await skill.select_option('nature');await skill.blur()
                await page.locator('.sheet-spell[data-spell=guidance] .sheet-spell-actions > button').first.click()
                await until(lambda:p.buffs.get('guidance',{}).get('skill')=='nature','Guidance skill cast')
                passed('Guidance skill picker and Use button still send the correct cast')
                await page.locator('.sheet-spell[data-spell=moonbeam] .slot-picker').select_option('0')
                await page.locator('.sheet-spell[data-spell=moonbeam] .slot-picker').blur()
                await until(lambda:dnd.grouped_hotbar(p)[0]=='moonbeam','hotbar binding')
                passed('Shortcut assignment from a sorted row still binds the chosen spell')
                await page.locator('[data-character-tab=stats]').click();await page.locator('[data-character-tab=spells]').click()
                await page.wait_for_timeout(200);assert await page.evaluate(GROUPS)==groups
                passed('Changing tabs keeps the same unique ordered sections')
                await context.close()
                mobile=await browser.new_context(viewport={'width':820,'height':390},screen={'width':850,'height':420},is_mobile=True,has_touch=True,device_scale_factor=2)
                page=await mobile.new_page();page.set_default_timeout(12000);page.on('pageerror',lambda e:report['errors'].append(str(e)))
                mp=await login(page,'MobileUi16');mgroups=await page.evaluate(GROUPS);validate(mgroups,mp)
                assert mgroups==groups;assert await page.evaluate('BractwoMobile.active()')
                await page.locator('.sheet-spell[data-spell=guidance]').scroll_into_view_if_needed()
                await page.screenshot(path=str(OUT/'mobile-landscape-cantrips.png'))
                passed('Touch landscape: identical sections, Guidance in Sztuczki')
                await page.set_viewport_size({'width':390,'height':820});await page.wait_for_timeout(250)
                assert await page.evaluate(GROUPS)==mgroups
                metrics=await page.evaluate("""() => {const c=document.querySelector('#characterContent');return {width:c.clientWidth,scroll:c.scrollWidth,screen:innerWidth,document:document.documentElement.scrollWidth};}""")
                assert metrics['scroll']<=metrics['width']+1,metrics
                await page.locator('.sheet-spell[data-spell=guiding_bolt]').scroll_into_view_if_needed()
                await page.screenshot(path=str(OUT/'mobile-portrait-circle-I.png'))
                passed('Touch portrait: same grouping, no horizontal spellbook overflow',metrics=metrics)
                assert not report['errors'],report['errors'];passed('No JavaScript exceptions during the browser checks')
                report['ok']=True;report['source_hashes']=bridge.source_hashes;save()
            except Exception:
                report['failure']=traceback.format_exc();save();await page.screenshot(path=str(OUT/'failure.png'));raise
            finally:await bridge.close();await browser.close()
    finally:await bridge.close();await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
