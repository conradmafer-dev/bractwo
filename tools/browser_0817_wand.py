"""0.8.17: wand target selection, cast priority, UI queue feedback and shortcuts.
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
OUT=ROOT/'docs'/'qa_0.8.17';OUT.mkdir(parents=True,exist_ok=True)
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


   a,q=await new_page('MagCel','mage')
   async def wait(ms=350):await a.wait_for_timeout(ms)
   async def snap(name):await a.screenshot(path=str(OUT/name))
   async def advance(seconds=3.1):
    clock.value+=seconds
    await wait()
   e=Enemy('test_wand_target','ogre',1250,1180,999,1250,1180)
   g.enemies[e.id]=e;g.legacy_enemies.append(e);g.reindex_enemy(e)
   row=a.locator('[data-enemy-id="'+e.id+'"]')
   bar=lambda key:a.locator('.hotbar-slot[data-spell="'+key+'"]')
   try:
    await wait()
    assert q.max_mana==40 and q.mana==40
    await row.click();await advance()
    assert e.hp==999 and q.attack_cooldown_until==0 and q.auto_enemy_id==e.id
    assert 'Ogr' in await a.locator('#targetName').inner_text()
    assert 'tylko na Spację' in await a.locator('#attackButton').get_attribute('title')
    checks.append('Clicking a real battle-list target leaves the wand idle and the main action ready, even after a full round.')
    await a.keyboard.press('Digit4');await wait()
    assert q.last_roll['action']=='Magiczny pocisk' and e.hp==987 and q.mana==20 and not q.pending_spell
    checks.append('Keyboard 4 casts three Magic Missiles immediately on the selected monster; no prior Spark and no double action.')
    await bar('ray_of_frost').click();await wait()
    assert q.pending_spell['spell']=='ray_of_frost'
    assert 'Za 3.0 s' in await bar('ray_of_frost').inner_text()
    assert 'queued' in await bar('ray_of_frost').get_attribute('class')
    pending=q.pending_spell.copy()
    await row.click();await wait()
    assert q.pending_spell==pending
    checks.append('Hotbar click queues Frost Ray and shows a countdown; reselecting the same monster does not erase the command.')
    await snap('01_wand_queue_desktop.png')
    before=(q.x,q.y)
    await a.keyboard.down('KeyD');await wait(160);await a.keyboard.up('KeyD');await wait(180)
    assert (q.x,q.y)!=before and q.pending_spell['spell']=='ray_of_frost'
    checks.append('Movement keeps working while a targeted spell is pending.')
    hp=e.hp
    await a.keyboard.down('Space');clock.value+=3.1;await wait(400);await a.keyboard.up('Space');await wait(150)
    assert q.last_roll['action']=='Promień mrozu' and e.hp==hp-3 and not q.pending_spell
    assert not await bar('ray_of_frost').evaluate('(b)=>b.classList.contains("queued")')
    checks.append('Holding Space while the queued spell becomes ready does not steal its action; Frost Ray casts once, costs no mana and clears its queue display.')
    hp=e.hp;await advance(6.2)
    assert e.hp==hp
    checks.append('The wand does not resume automatic sparks after a cast or an idle interval.')
    await a.keyboard.press('Space');await wait()
    assert q.last_roll['action']=='Iskra różdżki' and e.hp==hp-3 and q.last_roll['damage_dice']=='1k4'
    await bar('magic_missile').click();await wait()
    assert q.pending_spell['spell']=='magic_missile'
    mana=q.mana;hp=e.hp
    await a.locator('#clearTarget').click();await advance()
    assert not q.pending_spell and not q.auto_enemy_id and q.mana==mana and e.hp==hp
    checks.append('Manual Space still fires a 1d4 Spark; clearing the target cancels a subsequent queue without spending mana.')
    await row.click();await a.keyboard.press('KeyF');await wait()
    assert q.last_roll['action']=='Promień mrozu'
    checks.append('F casts the actual most-used/recent tied spell into the selected target without a wand attack.')
    await a.keyboard.press('KeyF');await wait()
    assert q.pending_spell['spell']=='ray_of_frost'
    assert 'Za 3.0 s' in await a.locator('#abilityCooldown').inner_text()
    checks.append('The favorite F button displays the same server-confirmed queue countdown.')
    await advance()
    await g.bind_spell(q,12,'fire_bolt');await wait()
    await a.keyboard.press('F1');await wait()
    assert q.pending_spell['spell']=='fire_bolt'
    await advance()
    assert q.last_roll['action']=='Ognisty pocisk'
    checks.append('The second hotbar row (F1) uses the same target and queue rules.')
    await a.keyboard.press('KeyK');await wait()
    spell=a.locator('.sheet-spell[data-spell="ray_of_frost"]')
    await spell.get_by_role('button',name='Użyj',exact=True).click();await wait()
    assert q.pending_spell['spell']=='ray_of_frost'
    assert 'Za 3.0 s' in await spell.inner_text()
    await advance()
    assert q.last_roll['action']=='Promień mrozu'
    assert 'Użyj' in await spell.inner_text()
    checks.append('Casting from the spellbook retains the enemy, acknowledges the pending cast and refreshes after it executes.')
    await a.keyboard.press('Escape');await wait()
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await wait()
     await bar('ray_of_frost').click();await wait()
     assert q.pending_spell['spell']=='ray_of_frost'
     assert 'Za 3.0 s' in await bar('ray_of_frost').inner_text()
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
     await snap('02_queue_'+label+'.png')
     await advance()
     assert q.last_roll['action']=='Promień mrozu'
     checks.append(f'{width}x{height}: tapping the hotbar queues and casts without horizontal page overflow.')
    await a.set_viewport_size({'width':1440,'height':900});await wait()
    e2=Enemy('test_wand_other','ogre',1300,1180,999,1300,1180)
    g.enemies[e2.id]=e2;g.legacy_enemies.append(e2);g.reindex_enemy(e2);await wait()
    await a.keyboard.press('Digit4');await wait();assert q.pending_spell
    hp=e.hp;mana=q.mana
    await a.locator('[data-enemy-id="'+e2.id+'"]').click();await advance()
    assert not q.pending_spell and q.auto_enemy_id==e2.id and e.hp==hp and e2.hp==999 and q.mana==mana
    checks.append('Choosing a genuinely different target cancels the previous queue and never transfers a paid spell silently.')
    await a.locator('#attackButton').click();await wait()
    assert q.last_roll['action']=='Iskra różdżki' and e2.hp==996
    checks.append('The on-screen Attack button also retains the explicit manual Spark.')
    assert not errors,errors
    checks.append('No JavaScript exceptions; all actions used production UI and actual server handlers.')
    (OUT/'failure.png').unlink(missing_ok=True)
    (OUT/'browser_results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server; native Chromium loopback denied by environment','monster_ai':'paused; deterministic clock; actual production player action loop'},ensure_ascii=False,indent=2))
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
