"""0.8.15: Arcane Recovery in combat, movement, hotbar, book and feats.
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
OUT=ROOT/'docs'/'qa_0.8.15';OUT.mkdir(parents=True,exist_ok=True)

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


   a,q=await new_page('MagOdzyskanie','mage')
   async def wait(ms=350):await a.wait_for_timeout(ms)
   async def snap(name):await a.screenshot(path=str(OUT/name))
   async def advance(seconds):
    clock.value+=seconds
    for p in g.players.values():p.current_wall_time=clock()
    await wait()
   try:
    q.mana=0;q.combat_until=clock()+20;q.pvp_combat_until=clock()+90
    q.mana_recovery_until=clock()+10000;q.attack_cooldown_until=clock()+2.5
    await a.keyboard.press('KeyC');await wait();await a.locator('[data-character-tab="feats"]').click();await wait()
    feature=a.locator('.caster-feature').filter(has_text='Odzyskanie mocy')
    use=feature.get_by_role('button',name='Użyj',exact=True)
    assert not await use.is_disabled()
    text=await feature.inner_text()
    assert 'natychmiast' in text and '4 s' not in text and '180 s' in text
    await snap('01_recovery_ready_in_combat.png')
    checks.append('Atuty: Recovery is enabled in PvE/PvP combat with no mana and a busy main action; wording is updated.')
    # Hold a movement key while clicking the ability. A real server tick moves the avatar.
    start=(q.x,q.y)
    await a.keyboard.down('KeyD');await wait(100)
    await use.click();await wait(150)
    dx_during=q.dx
    await a.keyboard.up('KeyD');await wait()
    assert abs(q.x-start[0])+abs(q.y-start[1])>1 and dx_during>0,(start,q.x,q.y,dx_during)
    assert q.mana==20 and not q.casting_channel and q.spell_cooldowns['arcane_recovery']==clock()+180
    assert q.attack_cooldown_until==clock()+2.5 and q.bonus_cooldown_until==clock()+3
    assert q.combat_until>clock() and q.pvp_combat_until>clock()
    await snap('02_recovery_used.png')
    checks.append('Real click restores20 mana immediately while moving, consumes bonus action only, keeps combat timers and starts180-second cooldown.')
    assert await use.is_disabled()
    await a.locator('[data-character-tab="spells"]').click();await wait()
    book=a.locator('.sheet-spell[data-spell="arcane_recovery"]')
    assert await book.get_by_role('button',name='Użyj',exact=True).is_disabled()
    hotbar=a.locator('.hotbar-slot[data-spell="arcane_recovery"]')
    assert await hotbar.is_disabled()
    assert '180 s' in await hotbar.inner_text()
    checks.append('Feat button, spellbook and hotbar all lock after use; hotbar shows180s.')
    assert await a.locator('.sheet-spell.locked').count()>0
    await a.locator('[data-character-tab="feats"]').click();await wait()
    assert await a.locator('.training-available [data-feat]').count()>0
    checks.append('Unowned feats and future spells remain unchanged; no scrolls or unrelated visibility changes.')
    # Reuse through the book, after the actual cooldown expires.
    await advance(180)
    q.mana=0;q.combat_until=clock()+20;q.pvp_combat_until=clock()+90
    q.attack_cooldown_until=clock()+1.5
    await a.locator('[data-character-tab="spells"]').click();await wait()
    assert not await book.get_by_role('button',name='Użyj',exact=True).is_disabled()
    await book.get_by_role('button',name='Użyj',exact=True).click();await wait()
    assert q.mana==20 and not q.casting_channel and q.attack_cooldown_until==clock()+1.5
    checks.append('Spellbook casts instant Recovery during combat after cooldown expires, without delaying main action.')
    # Hotkey F now selects Recovery based on actual successful uses.
    await advance(180);q.mana=0;q.combat_until=clock()+20;q.pvp_combat_until=clock()+90
    await a.keyboard.press('Escape');await wait()
    favorite=a.locator('#abilityButton')
    assert await favorite.get_attribute('data-spell')=='arcane_recovery'
    assert not await favorite.is_disabled()
    await a.keyboard.press('KeyF');await wait()
    assert q.mana==20 and q.spell_cooldowns['arcane_recovery']==clock()+180
    checks.append('Actual most-used ability under F invokes Recovery in combat and cannot bypass cooldown.')
    # Hotbar pointer use during combat.
    await advance(180);q.mana=0;q.combat_until=clock()+20;q.pvp_combat_until=clock()+90
    await wait();assert not await hotbar.is_disabled()
    await hotbar.click();await wait()
    assert q.mana==20 and q.spell_cooldowns['arcane_recovery']==clock()+180
    checks.append('Hotbar click invokes the same authoritative instant Recovery.')
    # Full mana must not waste the now available skill.
    await advance(180);q.mana=q.max_mana;await wait()
    assert await hotbar.is_disabled() and await favorite.is_disabled()
    await a.keyboard.press('KeyC');await wait();await a.locator('[data-character-tab="feats"]').click();await wait()
    assert await use.is_disabled()
    checks.append('Full mana disables Recovery on card, hotbar and F instead of wasting the cooldown.')
    # Short bonus-action lock must update even when mana and other card values do not change.
    q.mana=0;q.combat_until=clock()+20;q.pvp_combat_until=clock()+90;q.bonus_cooldown_until=clock()+3
    await wait();assert await use.is_disabled()
    await advance(3);assert not await use.is_disabled()
    checks.append('Card readiness refreshes when only the three-second bonus-action lock expires.')
    # Small screens use the same functional button and concise description.
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await wait()
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
     assert not await use.is_disabled()
     await snap('03_recovery_'+label+'.png')
     checks.append(f'{width}x{height}: Recovery remains readable and usable in combat, without horizontal page overflow.')
    await a.set_viewport_size({'width':1440,'height':900})
    # Rituals are not affected by the new instant feature.
    q.combat_until=q.pvp_combat_until=0;q.attack_cooldown_until=0
    await a.locator('[data-character-tab="spells"]').click();await wait()
    await a.locator('.sheet-spell[data-spell="alarm"]').get_by_role('button',name='Rytuał',exact=False).click();await wait()
    assert q.casting_channel['ritual'] and q.casting_channel['total']==10
    assert await book.get_by_role('button',name='Użyj',exact=True).is_disabled()
    await advance(10.1)
    assert not q.casting_channel and q.id in g.alarms and q.mana==0
    checks.append('Alarm still uses its ten-second out-of-combat ritual; Recovery cannot silently cancel or skip it.')
    assert not errors,errors
    checks.append('No JavaScript exceptions during all tested controls and responsive layouts.')
    (OUT/'browser_results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server','monster_ai':'paused; real server handlers; deterministic clock'},ensure_ascii=False,indent=2))
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
