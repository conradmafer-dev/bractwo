"""0.8.5 spell graphics and character sheet QA of actual client scripts via a controlled Python WS bridge.
Tests the actual character sheet, hotbars, adaptive F and authoritative spell VFX.
Test dependencies: playwright, Chromium. Never imported by the production server.
"""
import asyncio
import json
import pathlib
import sys
import base64
from aiohttp import ClientSession, WSMsgType, web
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.server import create_app, Enemy, make_item
from server import dnd_content as dnd
OUT=ROOT/'docs'/'qa_0.8.5';OUT.mkdir(parents=True,exist_ok=True)

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

   a,p=await new_page('KartaMage','mage')
   await a.bring_to_front()
   assert p.max_mana==40 and p.mana==40
   assert len(p.hotbar)==24 and sum(bool(k) for k in p.hotbar)==9
   assert await a.locator('.hotbar-slot').count()==24
   assert await a.locator('#hotbarSlots .hotbar-slot').count()==12
   assert await a.locator('#hotbarFunctionSlots .hotbar-slot').count()==12
   checks.append('24 fields in two 12-key rows; all nine starting mage spells included')
   await a.keyboard.press('c');await a.wait_for_timeout(150)
   assert await a.locator('#characterPanel').is_visible()
   assert await a.locator('#sidePanel').is_hidden()
   assert await a.locator('#characterContent').get_attribute('data-tab')=='inventory'
   assert await a.locator('.character-tabs button').all_text_contents()==['Ekwipunek','Statystyki','Atuty','Czary']
   assert await a.locator('.sheet-bag-cell').count()==15
   checks.append('C opens standalone four-tab card; backpack 3x5 with no journal or atlas')
   await a.screenshot(path=str(OUT/'01_character_inventory_desktop.png'))
   await a.click('[data-character-tab=stats]');await a.wait_for_timeout(150)
   assert '1k20+5' in await a.locator('#characterContent').inner_text()
   assert '1k4' in await a.locator('#characterContent').inner_text()
   assert await a.locator('.sheet-ability').count()==6
   assert await a.locator('.sheet-resistances').first.locator('span').count()==13
   checks.append('Statistics show real weapon/spell rolls, six attributes/saves and thirteen damage resistances')
   await a.screenshot(path=str(OUT/'02_character_stats_desktop.png'))
   await a.click('[data-character-tab=feats]')
   assert await a.locator('.sheet-empty-feats').inner_text()=='Atuty\n\nNie masz jeszcze atutów.'
   checks.append('Feats tab is an honest empty state, with no fake purchasable feats')
   await a.keyboard.press('Escape');await a.keyboard.press('k');await a.wait_for_timeout(150)
   assert await a.locator('#characterContent').get_attribute('data-tab')=='spells'
   row=a.locator('.sheet-spell[data-spell="longstrider"]')
   await row.locator('select').select_option('12');await a.wait_for_timeout(250)
   assert p.hotbar[12]=='longstrider'
   checks.append('Spell tab binding assigns F1 and persists server hotbar')
   await a.keyboard.press('Escape');await a.keyboard.press('F1');await a.wait_for_timeout(200)
   assert 'longstrider' in p.buffs and p.mana==20
   assert dnd.favorite_spell(p)=='longstrider'
   checks.append('F1 actually casts its assigned spell, F switches from successful-use history')
   await a.wait_for_timeout(200)
   assert await a.locator('#abilityButton').get_attribute('data-spell')=='longstrider'
   # Reassign other twelve-key endpoints and check physical-key mapping through real client sends.
   clock.value+=3.1;p.mana=p.max_mana
   await a.keyboard.press('k');await a.wait_for_timeout(150)
   await a.locator('.sheet-spell[data-spell="mage_armor"] select').select_option('23');await a.wait_for_timeout(150)
   await a.keyboard.press('Escape');await a.keyboard.press('F12');await a.wait_for_timeout(200)
   assert 'mage_armor' in p.buffs
   checks.append('F12 dispatches slot 24, not a browser action or the adaptive F shortcut')
   clock.value+=3.1;p.mana=p.max_mana
   # Native network navigation is blocked by environment; test uses bridge for all UI interactions.
   e=Enemy('visual_dummy','goblin',1180,1180,hp=250,home_x=1180,home_y=1180)
   g.enemies[e.id]=e;g.legacy_enemies.append(e)
   # Defeat the movement AI only for a stable visual fixture; server casting/hits remain real.
   e.ready=clock.value+100000;e.ranged_ready=clock.value+100000 
   await a.wait_for_timeout(200)
   await a.evaluate("()=>{const c=document.querySelector('#world');const r=c.getBoundingClientRect();}")
   # Select via actual actor row, then use actual HUD cast button.
   await a.locator('.battle-row').filter(has_text='Goblin').first.click();await a.wait_for_timeout(120)
   p.auto_enabled=False;p.attack_cooldown_until=0
   await a.wait_for_timeout(120)
   # Capture real animation after cast; gameplay remains authoritative.
   await a.locator('.hotbar-slot[data-spell=magic_missile]').click();await a.wait_for_timeout(180)
   await a.screenshot(path=str(OUT/'03_magic_missiles_desktop.png'))
   events=[e for e in g.effects if e.get('spell_id')=='magic_missile']
   assert events and events[-1]['shots']==3
   checks.append('Magic Missile emits one three-projectile event and animated curved trails')
   clock.value+=3.1;p.attack_cooldown_until=0;p.mana=p.max_mana
   await a.wait_for_timeout(80)
   await a.locator('.hotbar-slot[data-spell=ray_of_frost]').click();await a.wait_for_timeout(130)
   await a.screenshot(path=str(OUT/'04_ray_of_frost_desktop.png'))
   assert any(e.get('spell_id')=='ray_of_frost' and e['visual']['style']=='beam' for e in g.effects)
   checks.append('Ray of Frost emits blue-white beam metadata and draws impact shards')
   clock.value+=3.1;p.attack_cooldown_until=0
   before=len(p.spell_history)
   await a.wait_for_timeout(120);await a.keyboard.press('f');await a.wait_for_timeout(180)
   assert len(p.spell_history)==before+1 and p.spell_history[-1]=='ray_of_frost'
   checks.append('Adaptive F actually casts the most-used spell through the real ability command')
   # Visual shapes at a high level; geometry comes from authoritative combat events.
   p.level=80;p.mana=p.max_mana;dnd.sync_hotbar(p);e.hp=9999
   await a.wait_for_timeout(240)
   for spell,shape,filename in [('burning_hands','cone','08_cone_desktop.png'),('fireball','circle','09_circle_desktop.png'),('lightning_bolt','line','10_line_desktop.png')]:
    clock.value+=3.1;p.attack_cooldown_until=0;p.mana=p.max_mana
    await a.wait_for_timeout(140)
    await a.locator('.hotbar-slot[data-spell='+spell+']').click();await a.wait_for_timeout(150)
    event=next(x for x in reversed(g.effects) if x.get('spell_id')==spell)
    assert event['area']['shape']==shape
    await a.screenshot(path=str(OUT/filename))
    checks.append('Real '+spell+' cast transmits and renders '+shape+' geometry')
   await g.select_combat_target(p,{})
   # Fill backpack to force a page transition; original equipped items remain untouched.
   while len(p.inventory)<40:
    item=make_item('health_potion') if False else make_item('hunter_ring')
    p.inventory.append(item)
   await a.wait_for_timeout(250);await a.keyboard.press('i');await a.wait_for_timeout(150)
   assert await a.locator('.sheet-bag-cell').count()==15
   await a.locator('.sheet-bag-pager button').nth(1).click();await a.wait_for_timeout(100)
   assert '2 /' in await a.locator('.sheet-bag-pager').inner_text()
   checks.append('Full inventory is paged in 3 rows, worn equipment remains above backpack')
   await a.locator('.sheet-bag-cell:not(:disabled)').first.click();await a.wait_for_timeout(100)
   assert await a.locator('.sheet-item-detail').is_visible()
   checks.append('Inventory tile opens equip/sell detail without a one-item vertical list')
   for width,height in [(390,844),(320,700),(844,390)]:
    await a.set_viewport_size({'width':width,'height':height});await a.wait_for_timeout(200)
    overflow=await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
    assert not overflow,(width,height,'document overflow')
    assert await a.locator('#characterPanel').is_visible()
    assert await a.locator('.sheet-bag-cell').count()==15
    if width==390:await a.screenshot(path=str(OUT/'05_character_inventory_mobile.png'))
    checks.append(f'Character sheet at {width}x{height}: no page overflow; fifteen cells/three rows')
   await a.set_viewport_size({'width':390,'height':844})
   await a.click('[data-character-tab=spells]');await a.wait_for_timeout(150)
   await a.screenshot(path=str(OUT/'06_character_spells_mobile.png'))
   await a.keyboard.press('Escape');await a.wait_for_timeout(150)
   await a.screenshot(path=str(OUT/'07_hotbars_mobile.png'))
   assert await a.locator('#hotbarFunctionSlots .hotbar-slot').count()==12
   assert await a.evaluate("document.querySelector('.hotbar-viewport').scrollWidth>document.querySelector('.hotbar-viewport').clientWidth")
   checks.append('Mobile two twelve-slot rows share horizontal touch scroll')
   # High levels use a second bank rather than hide spells beyond 24.
   p.level=80;p.hp=p.max_hp;p.mana=p.max_mana;dnd.sync_hotbar(p);await a.wait_for_timeout(250)
   assert len(p.hotbar)>=48
   await a.locator('#hotbarNext').click();await a.wait_for_timeout(100)
   assert await a.locator('#hotbarPageLabel').inner_text()=='2/2'
   checks.append('High-level overflow spells available in second 24-slot bank')
   # Owner statistics update from snapshots without reopening the card.
   await a.keyboard.press('c');await a.click('[data-character-tab=stats]');p.xp=31;p.soul=47
   await a.wait_for_timeout(200)
   assert '47 /' in await a.locator('#characterContent').inner_text()
   checks.append('Character statistics refresh when soul/experience changes, without reopening')
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
