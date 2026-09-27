"""0.8.4 mana, hotbar and status QA of actual client scripts via a controlled Python WS bridge.
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
OUT=ROOT/'docs'/'qa_0.8.4';OUT.mkdir(parents=True,exist_ok=True)

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
   a,p=await new_page('ManaMage','mage')
   await a.bring_to_front()
   assert p.max_mana==40 and p.mana==40
   assert len(p.hotbar)==16 and len([k for k in p.hotbar if k])==9
   assert await a.locator('#hotbarPageLabel').inner_text()=='1/2'
   assert await a.locator('.hotbar-slot.locked').count()==0
   checks.append('Level-one wizard: 40 MP, nine unlocked spells, two pages, no locked placeholders')
   await a.click('#hotbarNext');assert await a.locator('[data-slot="0"]').get_attribute('data-spell')=='shocking_grasp'
   assert await a.locator('#hotbarPageLabel').inner_text()=='2/2'
   e=Enemy('world_browser084','ogre',p.x+50,p.y,59,p.x+50,p.y)
   e.conditions['restrained']={'until':clock()+1000};e.ready=e.ranged_ready=e.aoe_ready=10000
   g.enemies[e.id]=e;g.reindex_enemy(e)
   await a.wait_for_timeout(250)
   await a.keyboard.press('1');await a.wait_for_timeout(180)
   assert p.last_roll.get('action')=='Porażający uścisk',p.last_roll
   assert any(k.get('spell_id')=='shocking_grasp' for k in sent)
   checks.append('Page-two key 1 casts Shocking Grasp, not page-one Fire Bolt')
   await a.keyboard.press('PageUp');assert await a.locator('#hotbarPageLabel').inner_text()=='1/2'
   await a.keyboard.press('PageDown');assert await a.locator('#hotbarPageLabel').inner_text()=='2/2'
   await a.click('#hotbarPrev');checks.append('Both arrow buttons and Page Up/Down change pages')
   clock.value+=3.1;await a.wait_for_timeout(150)
   await a.click('[data-slot="7"]');await a.wait_for_timeout(180)
   assert p.mana==20 and 'longstrider' in p.buffs
   effect=a.locator('#ownEffects [data-effect="longstrider"]')
   assert await effect.is_visible()
   assert '600 r.' in await effect.inner_text() and '30:00' in await effect.inner_text()
   await effect.click();assert await a.locator('#effectDetail').is_visible()
   assert 'Atak nie przerywa' in await a.locator('#effectDetailText').inner_text()
   await a.screenshot(path=str(OUT/'01_longstrider_status_desktop.png'))
   await a.click('#closeEffectDetail')
   checks.append('Longstrider: 20 MP, visible 600-round/30-minute timer, clickable rule description')
   await a.click('[data-slot="4"]');await a.wait_for_timeout(120)
   assert p.shield_armed and p.mana==20
   assert await a.locator('#ownEffects [data-effect="shield_ready"]').is_visible()
   checks.append('Armed Shield shows a separate persistent status and does not consume mana until triggered')
   clock.value+=3.1;await a.wait_for_timeout(100)
   await a.click('[data-slot="3"]');await a.wait_for_timeout(150)
   assert p.mana==0,p.mana
   clock.value+=3.1;await a.wait_for_timeout(100)
   assert await a.locator('[data-slot="3"]').is_disabled()
   hp=e.hp;await a.keyboard.press('4');await a.wait_for_timeout(100)
   assert e.hp==hp and p.mana==0
   await a.keyboard.press('1');await a.wait_for_timeout(150)
   assert e.hp<hp and p.mana==0
   assert 'longstrider' in p.buffs
   checks.append('Two paid casts exhaust mana; third is blocked, free cantrip still casts and keeps Longstrider')
   await a.click('[data-enemy-id="world_browser084"]');await a.wait_for_timeout(150)
   assert await a.locator('#targetEffects [data-effect="restrained"]').is_visible()
   checks.append('Selected monster has its own visible status row')
   g.stop_auto(p)
   p.level=10;p.mana=p.max_mana
   await a.wait_for_timeout(220);await a.click('#progressionButton');await a.wait_for_timeout(150)
   assert 'krąg 2' in await a.locator('#progressionSubtitle').inner_text()
   assert await a.locator('[data-cast="scorching_ray"]').is_enabled()
   assert await a.locator('[data-cast="fireball"]').is_disabled()
   assert 'Poziom 20' in await a.locator('[data-cast="fireball"]').inner_text()
   assert '140' in await a.locator('#progressionContent').inner_text()
   assert '4× krąg 1 + 2× krąg 2' in await a.locator('#progressionContent').inner_text()
   assert 'scorching_ray' in p.hotbar and 'fireball' not in p.hotbar
   checks.append('Level 10: circle II, 140-MP mixed budget, new spells on hotbar, circle III still gated at 20')
   picker=a.locator('select[aria-label="Przypisz Porażający uścisk do slotu"]')
   assert await picker.locator('option').count()==len(p.hotbar)+1
   await picker.select_option('0');await a.wait_for_timeout(180)
   assert p.hotbar[0]=='shocking_grasp' and p.hotbar[8]=='fire_bolt'
   checks.append('Book changes order by swapping slots across pages without removing unlocked spells')
   await a.locator('[data-cast="scorching_ray"]').scroll_into_view_if_needed()
   await a.screenshot(path=str(OUT/'02_circle_two_book_desktop.png'))
   p.level=20;p.mana=p.max_mana
   await a.wait_for_timeout(200)
   assert await a.locator('[data-cast="fireball"]').is_enabled()
   assert p.max_mana==270 and 'fireball' in p.hotbar
   checks.append('Level 20: circle III, 270 MP and automatically inserted third-circle spells')
   await a.click('#closePanel');await a.keyboard.press('Escape')
   for width,height in ((390,844),(320,700),(844,390)):
    await a.set_viewport_size({'width':width,'height':height});await a.wait_for_timeout(220)
    assert await a.locator('#hotbarNext').is_visible()
    assert await a.locator('#ownEffects [data-effect="longstrider"]').is_visible()
    await a.click('#hotbarNext');await a.click('#hotbarPrev')
    await a.locator('#ownEffects [data-effect="longstrider"]').click()
    assert await a.locator('#effectDetail').is_visible()
    await a.screenshot(path=str(OUT/f'03_status_controls_{width}x{height}.png'))
    await a.click('#closeEffectDetail')
    assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth')
    checks.append(f'Visible/clickable pages, effects and close control, no horizontal overflow at {width}x{height}')
   await a.set_viewport_size({'width':390,'height':844});await a.click('#bookSpell');await a.wait_for_timeout(150)
   await a.locator('[data-cast="longstrider"]').scroll_into_view_if_needed()
   assert not await a.locator('#effectsPanel').is_visible()
   checks.append('Open spell book hides effect overlay so it cannot cover spell controls')
   await a.screenshot(path=str(OUT/'04_spell_book_mobile.png'))
   await a.click('#closePanel')
   checks.append('Mobile spell book exposes costs, circle gates and the complete slot picker')
   b,q=await new_page('ManaDruid','druid');await b.bring_to_front()
   assert q.max_mana==40 and len(q.hotbar)==8 and all(q.hotbar)
   assert not await b.locator('#hotbarPages').is_visible()
   assert await b.locator('[data-slot="5"]').get_attribute('data-spell')=='healing_word'
   assert await b.locator('[data-slot="6"]').get_attribute('data-spell')=='longstrider'
   checks.append('Level-one druid: all eight available spells on one page, including Healing Word and Longstrider')
   await b.click('[data-slot="6"]');await b.wait_for_timeout(120)
   q.level=10;q.mana=q.max_mana;clock.value+=3.1
   class FailedSaveDice:
    def randint(self,lo,hi):return 1 if hi==20 else min(hi,3)
   g.combat_rng=FailedSaveDice();e.x=q.x+80;g.reindex_enemy(e)
   await b.wait_for_timeout(150);await b.click('[data-enemy-id="world_browser084"]');await b.wait_for_timeout(100)
   await b.click('[data-slot="4"]');await b.wait_for_timeout(100)
   clock.value+=3.1;await b.wait_for_timeout(160)
   assert q.concentration=='entangle'
   assert await b.locator('#ownEffects [data-effect="concentration"]').is_visible()
   assert await b.locator('#targetEffects [data-effect="restrained"]').is_visible()
   assert await b.locator('#ownEffects [data-effect="longstrider"]').is_visible()
   g.stop_auto(q)
   await b.screenshot(path=str(OUT/'05_druid_own_and_target_statuses.png'))
   checks.append('Druid shows Longstrider plus named concentration while the target shows root')
   g.break_concentration(q);await b.wait_for_timeout(160)
   assert await b.locator('#ownEffects [data-effect="concentration"]').count()==0
   assert await b.locator('#ownEffects [data-effect="longstrider"]').is_visible()
   checks.append('Breaking concentration removes its status, not Longstrider')
   p.pvp_safety=False;q.pvp_safety=False;p.x=q.x-70;p.attack_cooldown_until=0;p.bonus_cooldown_until=0
   g.combat_rng=Dice()
   await g.cast_spell(p,'ray_of_frost',target_id=q.id)
   await b.wait_for_timeout(150)
   assert await b.locator('#ownEffects [data-effect="slow"]').is_visible()
   clock.value+=3.1;await b.wait_for_timeout(150)
   assert await b.locator('#ownEffects [data-effect="slow"]').count()==0
   checks.append('PvP debuff appears on affected player and disappears when its round expires')
   assert not errors,errors
   checks.append('No JavaScript page errors in two connected clients and desktop/mobile layouts')
   sent=[packet for packet in sent if packet.get('type') not in ('hello','ranking')]
   for ws in sockets_all:await ws.close()
   await browser.close()
 finally:
  for task in tasks:
   if not task.done():task.cancel()
  await runner.cleanup()
  (OUT/'browser-results.json').write_text(json.dumps({'checks':checks,'errors':errors,'commands':sent,
   'method':'Chromium DOM/canvas; actual production JS/CSS; real server over Python WebSocket bridge; synthetic localStorage. Native browser networking, persistent localStorage and physical phones are not tested by this harness.'},ensure_ascii=False,indent=2))
 print(json.dumps({'checks':checks,'errors':errors},ensure_ascii=False,indent=2))
 assert len(checks)==20 and not errors

if __name__=='__main__':asyncio.run(main())
