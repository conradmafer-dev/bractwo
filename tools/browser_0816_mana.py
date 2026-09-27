"""0.8.16: gradual mana growth, per-level receipts, spellbook and feat figures.
Actual client and server via controlled Python WebSocket bridge; see TEST_REPORT.
Test-only dependencies: Playwright and Chromium.
"""
import asyncio
import json
import pathlib
import sys
import base64
from aiohttp import ClientSession, WSMsgType, web
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.server import create_app, Enemy, make_item, xp_next, Player
from server import dnd_content as dnd
OUT=ROOT/'docs'/'qa_0.8.16';OUT.mkdir(parents=True,exist_ok=True)
(OUT/'browser_results.json').unlink(missing_ok=True)

BRIDGE='''
window.__sockets=new Map();window.__nextSocket=0;
class QAWebSocket extends EventTarget {
 static CONNECTING=0;static OPEN=1;static CLOSING=2;static CLOSED=3;
 constructor(url){super();this.url=url;this.readyState=0;this.id=++window.__nextSocket;window.__sockets.set(this.id,this);setTimeout(()=>window.__wsOpen(this.id,url),0);}
 send(data){if(this.readyState!==1)throw Error('Socket not open');window.__wsSend(this.id,data);}
 close(){if(this.readyState>=2)return;this.readyState=2;window.__wsClose(this.id);}
}
window.WebSocket=QAWebSocket;
window.__deliver=(id,type,data)=>{let s=window.__sockets.get(id);if(!s)return;if(type==='open')s.readyState=1;if(type==='close')s.readyState=3;s.dispatchEvent(type==='message'?new MessageEvent(type,{data}):new Event(type));};
window.__storage={};
Object.defineProperty(window,'localStorage',{value:{getItem:k=>window.__storage[k]??null,setItem:(k,v)=>window.__storage[k]=String(v),removeItem:k=>delete window.__storage[k]}});
'''
class Checks(list):
 def append(self, message):
  super().append(message)
  print(f"PASS {len(self)}: {message}",flush=True)

class Clock:
 value=1000
 def __call__(self):return self.value
class Dice:
 def randint(self,a,b):return 10 if b==20 else min(b,3)

async def main():
 clock=Clock();app=create_app(':memory:',clock=clock);runner=web.AppRunner(app)
 await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start()
 port=site._server.sockets[0].getsockname()[1];g=app['game'];g.combat_rng=Dice()
 for e in g.enemies.values():e.alive=False;e.respawn_at=0
 g.step_monsters=lambda *args:None
 errors=[];checks=Checks();tasks=[];sockets_all=[];sent=[];closing=[False]
 try:
  async with ClientSession() as session,async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   context=await browser.new_context(viewport={'width':1440,'height':900})
   context.set_default_timeout(10000)
   print('Chromium ready; loading actual client and bridge',flush=True)
   async def new_page(name,cls):
    page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));sockets={}
    async def emit(sid,kind,data=None):
     if not closing[0] and not page.is_closed():
      try:await page.evaluate('([sid,kind,data])=>window.__deliver(sid,kind,data)',[sid,kind,data])
      except Exception as e:
       if 'Target' not in str(e):errors.append('bridge '+str(e))
    async def pump(sid,ws):
     try:
      async for msg in ws:
       if msg.type==WSMsgType.TEXT:await emit(sid,'message',msg.data)
     finally:await emit(sid,'close')
    async def ws_open(sid,url):
     try:
      ws=await session.ws_connect(f'http://127.0.0.1:{port}/ws');sockets[sid]=ws;sockets_all.append(ws)
      await emit(sid,'open');tasks.append(asyncio.create_task(pump(sid,ws)))
     except Exception as e:errors.append('open '+str(e));await emit(sid,'error')
    async def ws_send(sid,data):
     packet=json.loads(data)
     if packet.get('type') != 'ping':sent.append({'page':name,**packet})
     if sid in sockets and not sockets[sid].closed:await sockets[sid].send_str(data)
    async def ws_close(sid):
     if sid in sockets:await sockets[sid].close()
    await page.expose_function('__wsOpen',ws_open);await page.expose_function('__wsSend',ws_send);await page.expose_function('__wsClose',ws_close)
    assets={str(f.relative_to(ROOT/'web')):'data:'+('image/png' if f.suffix=='.png' else 'image/svg+xml')+';base64,'+base64.b64encode(f.read_bytes()).decode() for f in (ROOT/'web/assets').rglob('*') if f.suffix in ('.png','.svg')}
    asset_bridge='window.__qaAssets='+json.dumps(assets)+';const srcDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,"src");Object.defineProperty(HTMLImageElement.prototype,"src",{get:srcDesc.get,set(v){this.dataset.qaAsset=v;srcDesc.set.call(this,window.__qaAssets[v]||v);}});window.__qaMonsters=new Set();const di=CanvasRenderingContext2D.prototype.drawImage;CanvasRenderingContext2D.prototype.drawImage=function(...a){const path=a[0]?.dataset?.qaAsset;if(path?.includes("assets/monsters/"))window.__qaMonsters.add(path);return di.apply(this,a);};'
    html=(ROOT/'web/index.html').read_text()
    for filename in ('style','character_sheet','level_up','loot_ui','hud_layout','windows','fighter','caster'):
     html=html.replace(f'<link rel="stylesheet" href="{filename}.css">','<style>'+(ROOT/f'web/{filename}.css').read_text()+'</style>')
    for filename in ('runtime','atlas_map','spell_vfx','fighter_vfx','inventory_ui','fighter_ui','caster_ui','caster_vfx','character_sheet','level_up','loot_ui','windows','game'):
     prefix=BRIDGE+asset_bridge if filename=='runtime' else ''
     html=html.replace(f'<script src="{filename}.js"></script>','<script>'+prefix+(ROOT/f'web/{filename}.js').read_text()+'</script>')
    await page.set_content(html,wait_until='load')
    print('Client loaded; creating QA account',flush=True)
    await page.evaluate("url=>{document.getElementById('serverInput').value=url;document.getElementById('serverInput').dispatchEvent(new Event('change'));}",f'ws://127.0.0.1:{port}/ws')
    await page.click('#registerTab');await page.fill('#nameInput',name);await page.fill('#passwordInput','testpassword99')
    await page.click(f'[data-class={cls}]');await page.click('#connectButton')
    await page.wait_for_selector('#gameUI:not([hidden])',timeout=10000)
    p=next(p for p in g.players.values() if p.name==name)
    p.level=1;p.hp=p.max_hp;p.mana=p.max_mana;p.gold=1000;p.x=1100 if cls=='mage' else 1200;p.y=1180
    await page.wait_for_timeout(250)
    if await page.locator('#controlTip').is_visible():await page.click('#closeControlTip')
    return page,p


   a,q=await new_page('MagMana','mage')
   async def wait(ms=400):await a.wait_for_timeout(ms)
   async def snap(name):await a.screenshot(path=str(OUT/name))
   def set_test_state(p):
    p.mana_recovery_until=clock()+10000;p.combat_until=clock()+20
   try:
    assert q.max_mana==40 and q.mana==40
    checks.append('Mage still starts at 40/40 mana.')
    g.award(q,sum(xp_next(n) for n in range(1,5)),0);set_test_state(q);await wait()
    assert q.level==5 and q.mana==84 and q.max_mana==84
    assert '84' in await a.locator('#manaText').inner_text()
    assert await a.locator('.level-up-card').count()==4
    for level,gain,recovery in [(2,11,2),(3,11,2),(4,11,3),(5,11,2)]:
     card=a.locator(f'.level-up-card[data-level="{level}"]')
     assert await card.locator('[data-change="mana"]').inner_text()==f'Mana +{gain}'
     assert await card.locator('[data-change="spell_restore_mana_arcane_recovery"]').inner_text()==f'Odzyskanie mocy +{recovery} many'
    checks.append('Four real XP level-ups produce four cascade cards, with only individual mana/recovery gains.')
    q.mana=0;await a.keyboard.press('KeyC');await wait()
    await a.locator('[data-character-tab="feats"]').click();await wait()
    feature=a.locator('.caster-feature').filter(has_text='Odzyskanie mocy')
    use=feature.get_by_role('button',name='Użyj',exact=True)
    assert '+29 many' in await feature.inner_text() and not await use.is_disabled()
    checks.append('At level 5 the Feats card displays real recovery +29 and enables it in combat.')
    await use.click();await wait()
    assert q.mana==29 and q.spell_cooldowns['arcane_recovery']==clock()+180
    assert '29/84' in (await a.locator('#manaText').inner_text()).replace(' ','')
    checks.append('Clicking Recovery at level 5 really restores29 mana and starts unchanged180-second cooldown.')
    g.award(q,xp_next(5),0);await a.keyboard.press('Escape');await wait()
    assert q.level==6 and q.max_mana==96
    card=a.locator('.level-up-card[data-level="6"]')
    assert await card.locator('[data-change="mana"]').inner_text()=='Mana +12'
    assert await card.locator('[data-change="spell_restore_mana_arcane_recovery"]').inner_text()=='Odzyskanie mocy +2 many'
    assert q.spell_cooldowns['arcane_recovery']==clock()+180
    await snap('01_level6_growth_desktop.png')
    checks.append('Level6: max96, Mana+12, Recovery+2; level-up does not clear the active cooldown.')
    title=await a.locator('#manaText').evaluate('(e)=>e.parentElement.title')
    assert '96 many' in title and '+11 many' in title and 'odpowiednik' not in title
    checks.append('Mana tooltip shows current96 and next gain11, not a false tabletop-slot equivalent.')
    await a.keyboard.press('KeyK');await wait()
    book=a.locator('.sheet-spell[data-spell="arcane_recovery"]')
    text=await book.inner_text()
    assert '+31 many' in text and 'Poziom 7: +2 many' in text,text
    checks.append('Spellbook at level6 refreshes to recovery31 and next-level +2, without waiting for a five-level threshold.')
    await a.locator('[data-character-tab="feats"]').click();await wait()
    assert '+31 many' in await feature.inner_text()
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await wait()
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
     assert '+31 many' in await feature.inner_text()
     await snap('02_recovery_level6_'+label+'.png')
     checks.append(f'{width}x{height}: updated recovery amount and card render without horizontal page overflow.')
    await a.set_viewport_size({'width':1440,'height':900})
    await a.keyboard.press('Escape');g.award(q,sum(xp_next(n) for n in range(6,10)),0);await wait()
    assert q.level==10 and q.max_mana==140
    card=a.locator('.level-up-card[data-level="10"]')
    assert await card.locator('[data-change="mana"]').inner_text()=='Mana +11'
    assert await card.locator('[data-change="circle"]').inner_text()=='Krąg czarów +1'
    assert await card.locator('[data-change="spell_restore_mana_arcane_recovery"]').inner_text()=='Odzyskanie mocy +2 many'
    assert q.public(clock(),private=True)['spell_profiles']['magic_missile']['mana']==30
    await snap('03_level10_mana_and_circle.png')
    checks.append('Level10 preserves140 total, unlocks circleII as before and adds only11 mana; spell cost remains30.')
    clock.value+=180;q.mana=0;q.current_wall_time=clock();set_test_state(q);await wait()
    await a.keyboard.press('KeyF');await wait()
    assert q.mana==40 and q.spell_cooldowns['arcane_recovery']==clock()+180
    checks.append('F uses actual favorite Recovery and restores the unchanged40 mana at level10.')
    for cls,total,gain in [('druid',140,11),('ranger',60,2),('knight',30,0)]:
     page,p=await new_page('Mana'+cls,cls)
     p.level=9;p.mana=p.max_mana;set_test_state(p);g.award(p,xp_next(9),0)
     await page.wait_for_function('(total)=>document.getElementById("manaText").textContent.replace(/\\s/g, "")===`${total}/${total}`',arg=total)
     await page.locator('.level-up-card[data-level="10"]').wait_for(state='attached')
     assert p.level==10 and p.max_mana==total
     assert str(total) in await page.locator('#manaText').inner_text()
     card=page.locator('.level-up-card[data-level="10"]')
     if gain:assert await card.locator('[data-change="mana"]').inner_text()==f'Mana +{gain}'
     else:assert await card.locator('[data-change="mana"]').count()==0
     assert await card.locator('[data-change="spell_restore_mana_arcane_recovery"]').count()==0
     checks.append(f'{cls}: level10 pool{total}, mana gain{gain}, no fabricated Arcane Recovery.')
    assert not errors,errors
    checks.append('No JavaScript errors; production handlers and actual UI used throughout.')
    (OUT/'failure.png').unlink(missing_ok=True)
    (OUT/'browser_results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server','monster_ai':'paused; real server handlers; deterministic clock'},ensure_ascii=False,indent=2))
   except Exception:
    print('ERRORS',errors,flush=True)
    try:await asyncio.wait_for(snap('failure.png'),4)
    except Exception:pass
    raise
   closing[0]=True
   for ws in sockets_all:
    if not ws.closed:await ws.close()
   for t in tasks:t.cancel()
   await asyncio.gather(*tasks,return_exceptions=True)
   await browser.close()
 finally:
  closing[0]=True
  for ws in sockets_all:
   if not ws.closed:await ws.close()
  for t in tasks:t.cancel()
  await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
