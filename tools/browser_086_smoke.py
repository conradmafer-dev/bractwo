"""0.8.6: real advancement receipts, delta-only cascade, dismissal and allocation.
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
from server.server import create_app, Enemy, make_item, xp_next
from server import dnd_content as dnd
OUT=ROOT/'docs'/'qa_0.8.6';OUT.mkdir(parents=True,exist_ok=True)

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
 errors=[];checks=Checks();tasks=[];sockets_all=[];sent=[]
 try:
  async with ClientSession() as session,async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   context=await browser.new_context(viewport={'width':1440,'height':900})
   context.set_default_timeout(10000)
   print('Chromium ready; loading actual client and bridge',flush=True)
   async def new_page(name,cls):
    page=await context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));sockets={}
    async def emit(sid,kind,data=None):
     if not page.is_closed():
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
     if packet.get('type') not in ('input','ping'):sent.append({'page':name,**packet})
     if sid in sockets and not sockets[sid].closed:await sockets[sid].send_str(data)
    async def ws_close(sid):
     if sid in sockets:await sockets[sid].close()
    await page.expose_function('__wsOpen',ws_open);await page.expose_function('__wsSend',ws_send);await page.expose_function('__wsClose',ws_close)
    assets={str(f.relative_to(ROOT/'web')):'data:image/svg+xml;base64,'+base64.b64encode(f.read_bytes()).decode() for f in (ROOT/'web/assets').rglob('*.svg')}
    asset_bridge='window.__qaAssets='+json.dumps(assets)+';const srcDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,"src");Object.defineProperty(HTMLImageElement.prototype,"src",{get:srcDesc.get,set(v){srcDesc.set.call(this,window.__qaAssets[v]||v);}});'
    html=(ROOT/'web/index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(ROOT/'web/style.css').read_text()+'</style>')
    html=html.replace('<link rel="stylesheet" href="character_sheet.css">','<style>'+(ROOT/'web/character_sheet.css').read_text()+'</style>')
    html=html.replace('<script src="spell_vfx.js"></script>','<script>'+(ROOT/'web/spell_vfx.js').read_text()+'</script>')
    html=html.replace('<script src="character_sheet.js"></script>','<script>'+(ROOT/'web/character_sheet.js').read_text()+'</script>')
    html=html.replace('<script src="runtime.js"></script>','<script>'+BRIDGE+asset_bridge+'</script><script>'+(ROOT/'web/runtime.js').read_text()+'</script>')
    html=html.replace('<script src="game.js"></script>','<script>'+(ROOT/'web/game.js').read_text()+'</script>')
    html=html.replace('<link rel="stylesheet" href="level_up.css">','<style>'+(ROOT/'web/level_up.css').read_text()+'</style>')
    html=html.replace('<script src="level_up.js"></script>','<script>'+(ROOT/'web/level_up.js').read_text()+'</script>')
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

   from server import level_up as lu
   a,p=await new_page('AwansPanel','mage')
   await a.bring_to_front()
   assert await a.locator('#levelUpCascade').is_hidden()
   checks.append('No retroactive receipts on login')
   p.level=9;p.xp=0;g.award(p,xp_next(9)+xp_next(10),0)
   await a.wait_for_function("document.querySelectorAll('.level-up-card').length===2")
   assert await a.locator('.level-up-card').evaluate_all('(cards)=>cards.map(c=>c.dataset.level)')==['10','11']
   text=await a.locator('#levelUpCascade').inner_text()
   assert 'HP +1' in text and 'Mana +80' in text and 'Krąg czarów +1' in text and '→' not in text
   assert await a.locator('.level-up-close').all_text_contents()==['Zamknij','Zamknij']
   checks.append('Two levels from one award; separate deltas and bottom Zamknij')
   poses=await a.locator('.level-up-card').evaluate_all('(cs)=>cs.map(c=>({top:parseFloat(c.style.top),left:parseFloat(c.style.left)}))')
   assert poses[1]['top']>poses[0]['top'] and poses[1]['left']>poses[0]['left']
   await a.screenshot(path=str(OUT/'01_cascade_desktop.png'))
   checks.append('Each new receipt offset down and right in cascade')
   await a.locator('.level-up-card[data-level="10"] .level-up-title').click()
   assert 'front' in await a.locator('.level-up-card[data-level="10"]').get_attribute('class')
   await a.screenshot(path=str(OUT/'02_level_10_deltas.png'))
   checks.append('Earlier receipt can be raised by its header')
   await a.wait_for_timeout(9500)
   assert await a.locator('.level-up-card').count()==2
   checks.append('Receipts survive ordinary notification timeout')
   g.award(p,xp_next(11),0);await a.wait_for_function("document.querySelectorAll('.level-up-card').length===3")
   await a.locator('.level-up-card[data-level="11"] .level-up-title').click()
   await a.locator('.level-up-card[data-level="11"] .level-up-close').click()
   await a.wait_for_timeout(250)
   assert await a.locator('.level-up-card').evaluate_all('(cs)=>cs.map(c=>c.dataset.level)')==['10','12']
   assert [e['level'] for e in lu.pending(p)['pending_level_ups']]==[10,12]
   checks.append('Closing middle receipt keeps both surrounding receipts')
   async def close_all():
    while await a.locator('.level-up-card').count():
     c=a.locator('.level-up-card').last
     await c.locator('.level-up-title').click()
     await c.locator('.level-up-close').click()
     await a.wait_for_timeout(150)
   await close_all()
   assert await a.locator('#levelUpCascade').is_hidden()
   checks.append('Closing last receipt hides only the cascade')
   p.level=19;p.xp=0;g.award(p,xp_next(19),0)
   await a.wait_for_selector('.level-up-card[data-level="20"]')
   text=await a.locator('.level-up-card').inner_text()
   assert 'Rzut obronny: Inteligencja +2' in text and 'Rzut obronny: Mądrość +1' in text
   assert 'Ognisty pocisk · obrażenia +1k10' in text and 'Nowy czar + Kula ognia' in text
   await a.screenshot(path=str(OUT/'03_level_20_deltas_desktop.png'))
   checks.append('Separate saving throws, primary score, added dice and spell unlocks with icons')
   for width,height in [(390,844),(320,700),(844,390)]:
    await a.set_viewport_size({'width':width,'height':height});await a.wait_for_timeout(300)
    assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
    box=await a.locator('.level-up-close').bounding_box();vp=await a.locator('.level-up-viewport').bounding_box()
    assert box and vp and box['y']>=vp['y'] and box['y']+box['height']<=vp['y']+vp['height']+2,(box,vp)
    assert await a.locator('.level-up-body').evaluate('(e)=>e.scrollHeight>e.clientHeight')
    await a.screenshot(path=str(OUT/f'04_level_20_{width}x{height}.png'))
    checks.append(f'{width}x{height}: scrollable long summary, bottom Close visible, no overflow')
   await a.set_viewport_size({'width':390,'height':844})
   g.award(p,xp_next(20),0);await a.wait_for_function("document.querySelectorAll('.level-up-card').length===2")
   await a.screenshot(path=str(OUT/'05_mobile_cascade.png'))
   await a.locator('.level-up-card[data-level="21"] .level-up-close').click();await a.wait_for_timeout(200)
   assert await a.locator('.level-up-card[data-level="20"]').is_visible()
   checks.append('Mobile Close reveals previous receipt')
   await a.set_viewport_size({'width':1440,'height':900});await a.wait_for_timeout(200);await close_all()
   p.class_id='knight';p.level=49;p.xp=0;p.promoted=True;g.starter(p);g.award(p,xp_next(49),0)
   await a.wait_for_selector('.level-up-action[data-kind=mastery]')
   assert 'Punkt mistrzostwa +1' in await a.locator('.level-up-card').inner_text()
   await a.screenshot(path=str(OUT/'06_level_50_point.png'))
   await a.locator('.level-up-action').click();await a.wait_for_timeout(200)
   assert await a.locator('#characterContent').get_attribute('data-tab')=='stats'
   assert await a.locator('.sheet-allocation').is_visible()
   hp=p.max_hp
   await a.locator('[data-mastery=vitality]').click();await a.wait_for_timeout(300)
   assert p.mastery.get('vitality')==1 and p.max_hp==hp+2
   assert await a.locator('.sheet-allocation').count()==0
   await a.keyboard.press('Escape');await a.wait_for_timeout(100)
   assert await a.locator('.level-up-card').is_visible()
   assert await a.locator('.level-up-action').is_disabled()
   assert await a.locator('.level-up-action').inner_text()=='Przydzielono'
   checks.append('Action opens Statistics, allocates actual mastery, updates HP, leaves receipt')
   p.level=54;p.xp=0;g.award(p,xp_next(54),0);p.combat_until=clock.value+100
   await a.wait_for_timeout(250)
   await a.locator('.level-up-card').last.locator('.level-up-action').click();await a.wait_for_timeout(200)
   assert await a.locator('[data-mastery=focus]').is_disabled()
   await a.screenshot(path=str(OUT/'07_point_allocation_stats.png'))
   checks.append('Cannot allocate while the existing combat lock is active')
   await a.keyboard.press('Escape');p.combat_until=0;await a.wait_for_timeout(200)
   g.persist();expected=[e['id'] for e in lu.pending(p)['pending_level_ups']]
   await a.click('#logoutButton');await a.wait_for_timeout(200)
   await a.click('#loginTab');await a.fill('#nameInput','AwansPanel');await a.fill('#passwordInput','testpassword99')
   await a.click('#connectButton');await a.wait_for_selector('#gameUI:not([hidden])');await a.wait_for_timeout(350)
   p=next(p for p in g.players.values() if p.name=='AwansPanel')
   assert await a.locator('.level-up-card').evaluate_all('(cs)=>cs.map(c=>c.dataset.id)')==expected
   assert p.mastery.get('vitality')==1
   checks.append('Reconnect restores only outstanding receipts and allocated stats')
   count=lu.mastery_points(p);await close_all();assert lu.mastery_points(p)==count
   assert not lu.pending(p)['pending_level_ups']
   checks.append('Closing summaries does not consume an unassigned point')
   b,q=await new_page('OtherAwans','mage')
   assert await b.locator('#levelUpCascade').is_hidden()
   checks.append('Separate account cannot see another player receipts')
   assert not errors,errors
   print(json.dumps({'checks':checks,'count':len(checks),'errors':errors},ensure_ascii=False,indent=2))
   (OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'count':len(checks),'errors':errors,'sent':sent},ensure_ascii=False,indent=2))
   await browser.close()
 finally:
  for ws in sockets_all:
   if not ws.closed:
    try:await asyncio.wait_for(ws.close(),3)
    except TimeoutError:pass
  for task in tasks:task.cancel()
  await asyncio.gather(*tasks,return_exceptions=True)
  try:await asyncio.wait_for(runner.cleanup(),5)
  except TimeoutError:pass

if __name__=='__main__':asyncio.run(main())
