"""0.8.3 first-circle QA of actual client scripts via a controlled Python WS bridge.
Tests freshly registered level-one casters, hotbars, casting, and ranger gates.
Test dependencies: playwright, Chromium. Never imported by the production server.
"""
import asyncio
import json
import pathlib
import sys
from aiohttp import ClientSession, WSMsgType, web
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.server import create_app, Enemy
OUT=ROOT/'docs'/'qa_0.8.3';OUT.mkdir(parents=True,exist_ok=True)

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
    p.level=1;p.hp=p.max_hp;p.mana=p.max_mana;p.gold=1000;p.x=1100 if cls=='mage' else 1200;p.y=1180
    await page.wait_for_timeout(250)
    if await page.locator('#controlTip').is_visible():await page.click('#closeControlTip')
    return page,p
   a,p=await new_page('StartMage','mage')
   assert p.level==1 and p.public(clock(),private=True)['spell_circle']==1
   checks.append('New wizard starts at level 1 with circle I')
   await a.click('#progressionButton');await a.wait_for_timeout(200)
   assert 'krąg 1' in await a.locator('#progressionSubtitle').inner_text()
   for key in ('magic_missile','burning_hands','shield','mage_armor','longstrider'):
    assert await a.locator(f'[data-cast="{key}"]').is_enabled(),key
   assert await a.locator('[data-cast="scorching_ray"]').is_disabled()
   assert 'Poziom 20' in await a.locator('[data-cast="scorching_ray"]').inner_text()
   checks.append('Wizard book enables all five circle-I spells, keeps circle II locked at 20')
   assert await a.locator('[data-slot="3"]').is_enabled() and await a.locator('[data-slot="4"]').is_enabled()
   assert await a.locator('[data-slot="5"]').is_disabled()
   assert 'poz. 1 · 6 many' in await a.locator('[data-slot="3"]').get_attribute('title')
   checks.append('Wizard default slots 4 and 5 unlock with level-1 tooltips and unchanged mana cost')
   await a.locator('[data-cast="magic_missile"]').scroll_into_view_if_needed()
   await a.screenshot(path=str(OUT/'01_first_circle_wizard_desktop.png'))
   await a.click('#closePanel')
   e=Enemy('world_browser083','ogre',1300,1180,99,1300,1180)
   e.conditions['restrained']={'until':clock()+1000};e.ready=e.ranged_ready=e.aoe_ready=10000
   g.enemies[e.id]=e;g.reindex_enemy(e)
   await a.wait_for_timeout(300);await a.click('[data-enemy-id="world_browser083"]');await a.wait_for_timeout(200)
   hp=e.hp;mana=p.mana
   await a.click('[data-slot="3"]');await a.wait_for_timeout(100)
   assert p.pending_spell.get('spell')=='magic_missile'
   clock.value+=3.1;await a.wait_for_timeout(250)
   assert e.hp==hp-12 and p.last_roll['action']=='Magiczny pocisk',(e.hp,hp,p.last_roll)
   assert mana-6<=p.mana<mana-4,(p.mana,mana)
   checks.append('Level-1 Magic Missile casts through default hotbar, three dice, mana and queue')
   g.stop_auto(p);mana=p.mana
   await a.click('[data-slot="4"]');await a.wait_for_timeout(150)
   assert p.shield_armed and p.mana>=mana
   checks.append('Level-1 Shield can be armed from hotbar without upfront mana charge')
   await a.click('#progressionButton');await a.set_viewport_size({'width':390,'height':844});await a.wait_for_timeout(200)
   await a.locator('[data-cast="magic_missile"]').scroll_into_view_if_needed()
   assert await a.locator('[data-cast="magic_missile"]').is_enabled()
   assert await a.locator('.hotbar-slot').count()==8
   await a.screenshot(path=str(OUT/'02_first_circle_wizard_mobile.png'))
   checks.append('Wizard circle I and eight spell slots render at 390x844')

   b,q=await new_page('StartDruid','druid');await b.bring_to_front()
   assert q.level==1 and q.public(clock(),private=True)['spell_circle']==1
   await b.click('#progressionButton');await b.wait_for_timeout(200)
   for key in ('cure_wounds','healing_word','entangle','longstrider'):
    assert await b.locator(f'[data-cast="{key}"]').is_enabled(),key
   assert await b.locator('[data-cast="moonbeam"]').is_disabled()
   assert await b.locator('[data-cast="wild_shape_wolf"]').is_disabled()
   assert await b.locator('[data-slot="3"]').is_enabled() and await b.locator('[data-slot="4"]').is_enabled()
   checks.append('New level-1 druid has all four circle-I spells; circle II and wild shape remain locked')
   await b.locator('[data-cast="cure_wounds"]').scroll_into_view_if_needed()
   await b.screenshot(path=str(OUT/'03_first_circle_druid_desktop.png'))
   await b.click('#closePanel');q.hp=1;mana=q.mana;await b.wait_for_timeout(200)
   await b.click('[data-slot="3"]');await b.wait_for_timeout(180)
   assert q.hp==q.max_hp and q.last_roll['action']=='Leczenie ran'
   assert mana-6<=q.mana<mana-4
   checks.append('Level-1 Cure Wounds heals through default slot 4 and consumes mana')
   await b.click('[data-enemy-id="world_browser083"]');await b.wait_for_timeout(120)
   class FailedSaveDice:
    def randint(self,lo,hi):return 1 if hi==20 else min(hi,3)
   g.combat_rng=FailedSaveDice()
   await b.click('[data-slot="4"]');await b.wait_for_timeout(100)
   assert q.pending_spell.get('spell')=='entangle'
   clock.value+=3.1;await b.wait_for_timeout(250)
   assert q.concentration=='entangle' and g.enemy_condition(e,'restrained')
   checks.append('Level-1 Entangle from slot 5 applies concentration and root after failed save')
   g.stop_auto(q)
   await b.click('#progressionButton');await b.set_viewport_size({'width':390,'height':844});await b.wait_for_timeout(200)
   await b.locator('[data-cast="cure_wounds"]').scroll_into_view_if_needed()
   assert await b.locator('[data-cast="cure_wounds"]').is_enabled()
   assert await b.locator('.hotbar-slot').count()==8
   await b.screenshot(path=str(OUT/'04_first_circle_druid_mobile.png'))
   checks.append('Druid first-circle labels and controls render at 390x844')

   c,r=await new_page('StartRanger','ranger');await c.bring_to_front()
   await c.click('#progressionButton');await c.wait_for_timeout(200)
   assert r.level==1 and r.public(clock(),private=True)['spell_circle']==0
   for key in ('cure_wounds','hunters_mark','longstrider'):
    assert await c.locator(f'[data-cast="{key}"]').is_disabled(),key
    assert 'Poziom 20' in await c.locator(f'[data-cast="{key}"]').inner_text()
   checks.append('Level-1 ranger still sees shared first-circle spells locked at level 20')
   await c.click('#closePanel');await c.click('#helpButton');await c.wait_for_timeout(100)
   help_text=await c.locator('#helpPanel').inner_text()
   assert 'I krąg od poziomu 1, II od 20' in help_text and 'I krąg od poziomu 10' not in help_text
   checks.append('In-game help explains new first gate and unchanged later progression')
   assert not errors,errors
   checks.append('No JavaScript page errors across three clients and desktop/mobile layouts')
   sent=[packet for packet in sent if packet.get('type') not in ('hello','ranking')]
   for ws in sockets_all:await ws.close()
   await browser.close()
 finally:
  for task in tasks:
   if not task.done():task.cancel()
  await runner.cleanup()
  (OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'errors':errors,'commands':sent,
   'method':'Chromium DOM/canvas; unmodified game JS/CSS; real server over Python WebSocket bridge; synthetic localStorage. Native browser networking and persistent localStorage are not tested by this harness.'},ensure_ascii=False,indent=2))
 print(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
 assert len(checks)==13 and not errors

if __name__=='__main__':asyncio.run(main())
