"""0.8.12: Ranger spells, statuses, single-use weapon trigger and concentration.
Actual client and server via controlled Python WebSocket bridge; see TEST_REPORT.
Test-only dependencies: Playwright and Chromium.
"""
import asyncio
import os
import json
import pathlib
import sys
import base64
from aiohttp import ClientSession, WSMsgType, web
from playwright.async_api import async_playwright
ROOT=pathlib.Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from server.server import create_app, Enemy, make_item, xp_next, Player
from server import dnd_content as dnd
OUT=pathlib.Path(os.environ.get('BRACTWO_QA_OUT',ROOT/'docs'/'qa_0.8.12'));OUT.mkdir(parents=True,exist_ok=True)

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
    for filename in ('style','character_sheet','level_up','loot_ui','hud_layout','windows','fighter'):
     html=html.replace(f'<link rel="stylesheet" href="{filename}.css">','<style>'+(ROOT/f'web/{filename}.css').read_text()+'</style>')
    for filename in ('runtime','atlas_map','spell_vfx','fighter_vfx','inventory_ui','fighter_ui','character_sheet','level_up','loot_ui','windows','game'):
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


   a,p=await new_page('LowcaStart','ranger')
   async def wait(ms=350):await a.wait_for_timeout(ms)
   async def snap(name):await a.screenshot(path=str(OUT/name))
   async def clear():
    for _ in range(4):await a.keyboard.press('Escape')
    await wait()
   async def advance(seconds=3):
    clock.value+=seconds
    await wait()
   async def bar(key):return await a.locator('#hotbarSlots button[data-spell="'+key+'"]').inner_text()
   try:
    assert p.max_mana==40 and p.mana==40
    assert set(filter(None,p.hotbar))=={'hunters_mark','ensnaring_strike','cure_wounds'}
    assert await a.locator('#hotbarSlots button[data-spell="hunters_mark"]').count()==1
    checks.append('New level-one ranger has 40 mana and exactly three usable hotbar spells.')
    await a.keyboard.press('KeyK');await wait()
    assert await a.locator('.sheet-spell:not(.locked)').count()==3
    assert 'Od poziomu 5' in await a.locator('.sheet-spell[data-spell="longstrider"]').inner_text()
    assert '0 many' in await a.locator('.sheet-spell[data-spell="hunters_mark"]').inner_text()
    await snap('01_level_one_spellbook.png')
    checks.append('Spellbook matches authoritative unlocks; Mark is free, Longstrider unlocks at five.')
    await clear()
    p.x,p.y=1200,1180;p.attack_cooldown_until=clock()+3
    e=Enemy('world_ranger_qa','bandit',p.x+155,p.y,500,p.x+155,p.y)
    g.enemies[e.id]=e;g.reindex_enemy(e);e.ready=100000;await wait()
    await a.locator('[data-enemy-id="'+e.id+'"]').click();await wait()
    await a.keyboard.press('Digit1');await wait()
    assert p.concentration=='hunters_mark' and p.mana==40
    assert '30 s' in await bar('hunters_mark')
    assert await a.locator('#targetEffects [data-effect^="hunters_mark:"]').count()==1
    await snap('02_hunters_mark.png')
    checks.append('Mark hotkey applies a visible target status and cooldown without spending mana.')
    await a.keyboard.press('Digit2');await wait()
    assert p.ensnaring_armed and p.mana==40 and p.concentration=='hunters_mark'
    assert 'GOTOWE' in await bar('ensnaring_strike')
    await a.keyboard.press('KeyK');await wait()
    assert 'Po trafieniu zastąpi: Znak łowcy' in await a.locator('.sheet-spell[data-spell="ensnaring_strike"]').inner_text()
    await snap('03_concentration_warning.png')
    checks.append('Arming is free, marked ready and warns which concentration the next hit replaces.')
    await clear();await advance()
    await a.locator('[data-enemy-id="'+e.id+'"]').click();await wait()
    p.attack_cooldown_until=0
    await wait()
    assert p.concentration=='ensnaring_strike' and not p.ensnaring_armed and p.mana==20,(p.concentration,p.ensnaring_armed,p.mana,p.auto_enabled,p.auto_enemy_id,p.last_roll)
    assert 'restrained' in e.conditions
    assert await a.locator('#targetEffects [data-effect="restrained"]').count()==1
    await snap('04_weapon_hit_vines.png')
    checks.append('Real autoattack triggers the one-shot snare, spends 20 mana and replaces Mark with vines.')
    await a.locator('#targetEffects [data-effect="restrained"]').click();await wait()
    assert '1k6' in await a.locator('#effectDetailText').inner_text()
    assert not await a.locator('#escapeRestraint').is_visible()
    checks.append('Monster status details show per-round damage; players cannot help enemy monsters escape.')
    p.auto_enabled=False;p.attack_cooldown_until=clock()+3
    hp=e.hp;await advance()
    assert e.hp==hp-3,(hp,e.hp)
    checks.append('Periodic damage occurs once per three-second round rather than per animation frame.')
    await clear();p.level=5;p.hp=1;p.mana=40;p.attack_cooldown_until=0;await wait()
    assert 'longstrider' in p.hotbar
    await a.keyboard.press('Digit3');await wait()
    assert p.mana==20 and p.hp>1 and p.concentration=='ensnaring_strike'
    checks.append('Healing uses the shared mana pool without breaking ensnaring concentration; level five adds Longstrider.')
    await advance();p.hp=p.max_hp;p.mana=40
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await clear();await a.keyboard.press('KeyK');await wait()
     assert await a.locator('.sheet-spell:not(.locked)').count()==4
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
     await snap('05_spellbook_'+label+'.png')
     checks.append(f'{width}x{height}: readable spellbook, four unlocked spells and no page overflow.')
    await a.set_viewport_size({'width':1440,'height':900});await clear()
    p.level=80;p.mana=p.max_mana;p.attack_cooldown_until=0;await wait();await a.keyboard.press('KeyK');await wait()
    options=await a.locator('.sheet-spell[data-spell="hunters_mark"] .spell-power-picker option').all_text_contents()
    assert all('0 many' in text for text in options[1:]),options
    checks.append('Higher Mark duration ranks are still free in the actual power selector.')
    # A second actual client receives restraint and can spend its action escaping.
    await clear();g.break_concentration(p);p.level=8;p.pvp_safety=False;p.mana=p.max_mana
    b,q=await new_page('CelLowcy','mage');q.level=8;q.hp=q.max_hp;q.x=p.x+65;q.y=p.y;await wait()
    await g.cast_spell(p,'ensnaring_strike');p.bonus_cooldown_until=0
    assert g.trigger_ensnaring_strike(p,q,{'hit':True})
    await wait()
    await b.locator('#ownEffects [data-effect="restrained"]').click();await wait()
    assert await b.locator('#escapeRestraint').is_visible()
    class GoodDice:
     def randint(self,a,b):return 20 if b==20 else min(b,3)
    g.combat_rng=GoodDice();await b.locator('#escapeRestraint').click();await wait()
    assert 'restrained' not in q.buffs and not p.concentration
    assert q.attack_cooldown_until>clock()
    checks.append('Second browser client can escape PvP vines using the status button; its main action is consumed.')
    assert not errors,errors
    checks.append('No JavaScript errors during combat, status effects, spellbook and responsive layout.')
    (OUT/'results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server','monster_ai':'paused; real server spell/attack/tick handlers; deterministic clock and dice'},ensure_ascii=False,indent=2))
   except Exception:
    print('ERRORS',errors,flush=True)
    try:await asyncio.wait_for(snap('failure.png'),4)
    except Exception:pass
    raise
   await browser.close()
 finally:
  closing[0]=True
  for ws in sockets_all:
   if not ws.closed:await ws.close()
  for t in tasks:t.cancel()
  await runner.cleanup()
if __name__=='__main__':asyncio.run(main())
