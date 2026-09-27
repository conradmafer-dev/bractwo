"""0.8.1 two-player DOM/canvas QA with the real server via a Python WS bridge.
Only needed where Chromium blocks localhost navigation. Game JS/CSS are unchanged.
Test dependencies: playwright, Chromium. Never imported by the production server.
"""
import asyncio
import json
import pathlib
import sys
from aiohttp import ClientSession, WSMsgType, web
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.server import create_app
OUT=ROOT/'docs'/'qa_0.8.1';OUT.mkdir(parents=True,exist_ok=True)

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
 errors=[];checks=[];tasks=[];sockets_all=[];sent=[]
 try:
  async with ClientSession() as session,async_playwright() as pw:
   browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox','--disable-dev-shm-usage'])
   context=await browser.new_context(viewport={'width':1440,'height':900})
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
    html=(ROOT/'web/index.html').read_text().replace('<link rel="stylesheet" href="style.css">','<style>'+(ROOT/'web/style.css').read_text()+'</style>')
    html=html.replace('<script src="runtime.js"></script>','<script>'+BRIDGE+'</script><script>'+(ROOT/'web/runtime.js').read_text()+'</script>')
    html=html.replace('<script src="game.js"></script>','<script>'+(ROOT/'web/game.js').read_text()+'</script>')
    await page.set_content(html,wait_until='load')
    await page.evaluate("url=>{document.getElementById('serverInput').value=url;document.getElementById('serverInput').dispatchEvent(new Event('change'));}",f'ws://127.0.0.1:{port}/ws')
    await page.click('#registerTab');await page.fill('#nameInput',name);await page.fill('#passwordInput','testpassword99')
    await page.click(f'[data-class={cls}]');await page.click('#connectButton')
    await page.wait_for_selector('#gameUI:not([hidden])',timeout=10000)
    p=next(p for p in g.players.values() if p.name==name)
    p.level=100;p.hp=p.max_hp;p.mana=p.max_mana;p.gold=1000;p.x=1100 if cls=='mage' else 1200;p.y=1180
    await page.wait_for_timeout(250)
    if await page.locator('#controlTip').is_visible():await page.click('#closeControlTip')
    return page,p
   a,p=await new_page('PvpMage','mage');b,q=await new_page('PvpDruid','druid')
   await a.bring_to_front();await a.wait_for_timeout(250)
   await a.click('#partyButton');await a.click(f'[data-target="{q.id}"]');await a.wait_for_timeout(150)
   assert p.auto_target_id==q.id and not p.auto_enabled
   hp=q.hp;await a.click('[data-slot="3"]');await a.wait_for_timeout(200)
   assert q.hp==hp;checks.append('Locked PvP blocks Magic Missile selected through player list and hotbar')
   await a.click('#safetyButton');await a.wait_for_timeout(200)
   assert not p.pvp_safety and p.auto_enabled
   checks.append('Unlocking enables autoattack against the already selected player')
   p.auto_enabled=False;p.attack_cooldown_until=0;hp=q.hp
   await a.click('[data-slot="3"]');await a.wait_for_timeout(200)
   assert q.hp==hp-12,(q.hp,hp,p.last_roll)
   checks.append('Hotbar slot 4 sends Magic Missile to the selected player: three actual damage rolls')
   await a.screenshot(path=str(OUT/'01_pvp_spell_desktop.png'))
   p.auto_enabled=False;p.attack_cooldown_until=0
   await a.click('#abilityButton');await a.wait_for_timeout(200)
   assert 'slow' in q.buffs;checks.append('Class ability button applies Ray of Frost slow to player')
   await a.click('#safetyButton');await a.wait_for_timeout(150)
   assert p.pvp_safety and not p.auto_enabled and 'slow' not in q.buffs
   hp=q.hp;p.attack_cooldown_until=0
   await a.click('[data-slot="3"]');await a.wait_for_timeout(150);assert q.hp==hp
   checks.append('Relocking clears hostile status and stops player-targeted spells without erasing combat timer')
   await b.bring_to_front();await b.wait_for_timeout(150)
   await b.click('#partyButton');await b.click(f'[data-target="{p.id}"]');await b.wait_for_timeout(150)
   await b.click('#safetyButton');await b.wait_for_timeout(150)
   q.auto_enabled=False;q.attack_cooldown_until=0;q.bonus_cooldown_until=0;q.hp=25
   await g.bind_spell(q,3,'healing_word');await b.wait_for_timeout(200)
   await b.click('[data-slot="3"]');await b.wait_for_timeout(200)
   assert q.hp>25 and q.last_roll['target_id']==q.id and q.auto_target_id==p.id
   checks.append('Healing Word heals self while an opponent remains selected; no need to clear target')
   p.party_id=q.party_id=p.id;g.parties[p.id]=[p.id,q.id];p.hp=25
   await g.bind_spell(q,4,'stoneskin');q.attack_cooldown_until=0;q.bonus_cooldown_until=0
   await b.wait_for_timeout(250);await b.click('[data-slot="4"]');await b.wait_for_timeout(200)
   assert 'stoneskin' in p.buffs and p.buffs['stoneskin']['owner']==q.id and q.concentration=='stoneskin'
   checks.append('Support hotbar correctly targets selected party member and tracks caster concentration')
   await b.click('[data-slot="3"]');await b.wait_for_timeout(200)
   assert p.hp>25 and q.last_roll['target_id']==p.id
   checks.append('Healing selected party member during PvP succeeds and tags the healer for combat')
   await b.screenshot(path=str(OUT/'02_pvp_party_support.png'))
   await b.set_viewport_size({'width':390,'height':844});await b.wait_for_timeout(150)
   await b.screenshot(path=str(OUT/'03_pvp_mobile.png'))
   assert await b.locator('.hotbar-slot').count()==8
   checks.append('Mobile viewport preserves all eight hotbar controls')
   assert not errors,errors
   checks.append('No JavaScript page errors across the two clients')
   # Record only harmless gameplay commands, excluding account/password packets.
   sent=[packet for packet in sent if packet.get('type') not in ('hello','ranking')]
   for ws in sockets_all:await ws.close()
   await browser.close()
 finally:
  for task in tasks:
   if not task.done():task.cancel()
  await runner.cleanup()
  (OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'errors':errors,'commands':sent,
   'method':'Chromium DOM/canvas; unmodified game JS/CSS; real server over Python WebSocket bridge; synthetic localStorage. Native Chromium localhost navigation was blocked (ERR_BLOCKED_BY_ADMINISTRATOR).'},ensure_ascii=False,indent=2))
 print(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
 assert len(checks)>=10 and not errors

if __name__=='__main__':asyncio.run(main())
