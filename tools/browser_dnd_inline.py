"""Browser DOM/canvas QA using set_content and Python WS transport.
Chromium's environment blocks navigation; real server HTTP/WS is tested separately.
The browser application JS/CSS is unmodified. localStorage is a persistent test double.
"""
import sys,asyncio,json,pathlib,re
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from aiohttp import web,ClientSession,WSMsgType
from server.server import create_app,Enemy
from playwright.async_api import async_playwright
OUT=ROOT/'builds'/'browser_qa';OUT.mkdir(exist_ok=True)
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
window.__storage=STORAGE_JSON;
Object.defineProperty(window,'localStorage',{value:{getItem:k=>window.__storage[k]??null,setItem:(k,v)=>window.__storage[k]=String(v),removeItem:k=>delete window.__storage[k]}});
'''
async def main():
 app=create_app(':memory:');runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',8086);await site.start();g=app['game']
 errors=[];qa=[];tasks=[]
 try:
  async with ClientSession() as session,async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   context=await browser.new_context(viewport={'width':1440,'height':900})
   async def new_page(storage=None):
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
      ws=await session.ws_connect('http://127.0.0.1:8086/ws');sockets[sid]=ws
      await emit(sid,'open');tasks.append(asyncio.create_task(pump(sid,ws)))
     except Exception as e:errors.append('open '+str(e));await emit(sid,'error')
    async def ws_send(sid,data):
     if sid in sockets and not sockets[sid].closed:await sockets[sid].send_str(data)
    async def ws_close(sid):
     if sid in sockets:await sockets[sid].close()
    await page.expose_function('__wsOpen',ws_open);await page.expose_function('__wsSend',ws_send);await page.expose_function('__wsClose',ws_close)
    html=(ROOT/'web/index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(ROOT/'web/style.css').read_text()+'</style>')
    html=html.replace('<script src="runtime.js"></script>','<script>'+BRIDGE.replace('STORAGE_JSON',json.dumps(storage or {}))+'</script><script>'+(ROOT/'web/runtime.js').read_text()+'</script>')
    html=html.replace('<script src="game.js"></script>','<script>'+(ROOT/'web/game.js').read_text()+'</script>')
    await page.set_content(html,wait_until='load');await page.evaluate("document.getElementById('serverInput').value='ws://127.0.0.1:8086/ws';document.getElementById('serverInput').dispatchEvent(new Event('change'))")
    page.__qa_sockets=sockets
    return page
   page=await new_page();await page.wait_for_timeout(500)
   await page.screenshot(path=str(OUT/'01_login.png'))
   await page.click('#registerTab');await page.fill('#nameInput','DruidTest');await page.fill('#passwordInput','testpass888');await page.click('[data-class=druid]');await page.click('#connectButton')
   await page.wait_for_selector('#gameUI:not([hidden])',timeout=20000);await page.wait_for_timeout(800)
   await page.screenshot(path=str(OUT/'02_druid_start.png'))
   print('hotbar',await page.locator('.hotbar-slot').count(),await page.locator('.hotbar-slot').all_text_contents(),flush=True)
   assert await page.locator('.hotbar-slot').count()==8;qa.append('Eight spell hotbar slots visible')
   assert await page.locator('#controlTip').is_visible();await page.click('#closeControlTip');assert not await page.locator('#controlTip').is_visible()
   assert await page.evaluate("localStorage.getItem('bractwo.controlTip.dismissed')")=='1';qa.append('Control tip closes and writes dismissal preference')
   p=next(iter(g.players.values()));p.level=40;p.hp=p.max_hp;p.mana=p.max_mana;p.gold=1000
   await page.wait_for_timeout(500)
   await page.click('#bookSpell');await page.wait_for_timeout(200)
   await page.screenshot(path=str(OUT/'03_spellbook.png'))
   await page.locator('article.progress-entry').filter(has=page.locator('[data-cast=healing_word]')).locator('select').select_option('0')
   await page.wait_for_timeout(250);print('bound',p.hotbar,flush=True);assert p.hotbar[0]=='healing_word';qa.append('Spellbook binding reaches authoritative server and hotbar')
   await page.click('#closePanel');await page.click('[data-slot="6"]');await page.wait_for_timeout(250);print('form',p.form,flush=True);assert p.form=='wolf'
   await page.screenshot(path=str(OUT/'04_wolf.png'));qa.append('Druid wolf form button changes real server state and render')
   await page.click('[data-slot="6"]');await page.wait_for_timeout(250);assert not p.form
   p.x,p.y=1100,1180;p.bonus_cooldown_until=0;p.attack_cooldown_until=0
   for e in g.enemies.values():e.alive=False;e.respawn_at=0
   e=Enemy('dummy','ogre',1170,1180,999,1170,1180);g.enemies[e.id]=e;g.legacy_enemies=[e]
   await page.wait_for_timeout(500)
   await page.locator('#battleEnemies button').first.click();await page.wait_for_timeout(600)
   print('auto',p.auto_enabled,p.auto_enemy_id,p.last_roll,flush=True)
   assert p.auto_enabled and p.auto_enemy_id=='dummy' and p.last_roll;qa.append('Battle list target triggers automatic rolled attack')
   await page.screenshot(path=str(OUT/'05_autoattack.png'))
   await page.keyboard.press('Escape');await page.wait_for_timeout(200);assert not p.auto_enabled;qa.append('Escape stops automatic attacks')
   storage=await page.evaluate('window.__storage');p.combat_until=0
   for ws in page.__qa_sockets.values():await ws.close()
   await page.close();await asyncio.sleep(.2)
   page=await new_page(storage);await page.wait_for_timeout(500)
   print('ranking',await page.locator('#rankingList').inner_text(),flush=True)
   assert 'DruidTest' in await page.locator('#rankingList').inner_text();qa.append('Unauthenticated login screen shows real ranked account')
   await page.fill('#nameInput','DruidTest');await page.fill('#passwordInput','testpass888');await page.click('#connectButton');await page.wait_for_selector('#gameUI:not([hidden])');await page.wait_for_timeout(300)
   assert not await page.locator('#controlTip').is_visible();qa.append('New page using stored preference keeps tip hidden')
   await page.set_viewport_size({'width':390,'height':844});await page.wait_for_timeout(300);await page.screenshot(path=str(OUT/'06_mobile.png'))
   await page.click('#bookSpell');await page.wait_for_timeout(150);await page.screenshot(path=str(OUT/'07_mobile_book.png'));await page.click('#closePanel')
   await page.set_viewport_size({'width':960,'height':540});await page.wait_for_timeout(150);await page.screenshot(path=str(OUT/'08_landscape.png'))
   for ws in page.__qa_sockets.values():await ws.close()
   await page.close();page=await new_page(storage);await page.set_viewport_size({'width':390,'height':844});await page.wait_for_timeout(400);await page.screenshot(path=str(OUT/'09_mobile_login.png'))
   assert await page.locator('#rankingList').is_visible();qa.append('Mobile login keeps ranking visible')
   print('errors',errors,flush=True);qa.append('No browser JavaScript errors' if not errors else str(errors))
   for ws in page.__qa_sockets.values():await ws.close()
   await page.close();await browser.close()
 finally:
  await runner.cleanup()
  for t in tasks:
   if not t.done():t.cancel()
 (OUT/'results.json').write_text(json.dumps({'checks':qa,'errors':errors,'method':'Chromium set_content; unmodified JS/CSS; actual server with Python WS bridge; localStorage test double, not browser network/navigation'},ensure_ascii=False,indent=2))
 print('DONE',flush=True);assert not errors,errors
asyncio.run(main())
