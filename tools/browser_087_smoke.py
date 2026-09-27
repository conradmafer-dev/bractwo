"""0.8.7: live casting ranks, dice and missile count, advancement deltas and mobile power controls.
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
OUT=ROOT/'docs'/'qa_0.8.7';OUT.mkdir(parents=True,exist_ok=True)

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

   from server import level_up as lu, spell_scaling as scale
   a,p=await new_page('SkalowanieMag','mage')
   await a.bring_to_front()
   async def close_all(page):
    while await page.locator('.level-up-card').count():
     c=page.locator('.level-up-card').last
     await c.locator('.level-up-title').click()
     await c.locator('.level-up-close').click()
     await page.wait_for_timeout(150)
   assert await a.locator('#levelUpCascade').is_hidden()
   p.level=9;p.xp=0;g.award(p,xp_next(9)+xp_next(10),0)
   await a.wait_for_function("document.querySelectorAll('.level-up-card').length===2")
   card=a.locator('.level-up-card[data-level="10"]')
   await card.locator('.level-up-title').click()
   text=await card.inner_text()
   assert 'Magiczny pocisk +1 pocisk' in text,text
   assert 'Płonące dłonie +1k6 do obrażeń' in text,text
   assert 'Długonogi +1 cel' in text,text
   assert '→' not in text and 'przed' not in text.lower()
   assert await a.locator('.level-up-close').all_text_contents()==['Zamknij','Zamknij']
   checks.append('Level 10: projectile, damage die, ally and cost deltas; no before/after')
   await a.screenshot(path=str(OUT/'01_spell_gains_cascade_desktop.png'))
   await card.locator('.level-up-close').click();await a.wait_for_timeout(200)
   assert await a.locator('.level-up-card[data-level="11"]').count()==1
   checks.append('Cascaded receipts remain until their individual bottom Close')
   await close_all(a)
   p.level=10;p.mana=p.max_mana
   await a.keyboard.press('k');await a.wait_for_timeout(300)
   missile=a.locator('.sheet-spell[data-spell="magic_missile"]')
   assert '4 × 1k4+1' in await missile.inner_text(),await missile.inner_text()
   assert 'Poziom 20: +1 pocisk' in await missile.inner_text()
   assert await missile.locator('.spell-power-picker option').count()==3
   assert '30' in await missile.inner_text()
   checks.append('Spell book displays four missiles, selected cost and next level gain')
   await a.screenshot(path=str(OUT/'02_spell_power_book_desktop.png'))
   await missile.locator('.spell-power-picker').select_option('1');await a.wait_for_timeout(300)
   assert p.spell_circle_choices.get('magic_missile')==1
   assert '3 × 1k4+1' in await missile.inner_text()
   checks.append('Power picker sends actual base-circle preference and refreshes dice/cost')
   await a.keyboard.press('Escape');await a.wait_for_timeout(150)
   e=Enemy('scaling_dummy','ogre',1300,1180,99999,1300,1180)
   g.enemies[e.id]=e;g.legacy_enemies=[e]
   await g.select_combat_target(p,{'enemy_id':e.id})
   p.auto_enabled=False
   before=p.mana;p.attack_cooldown_until=0
   # Cast through the actual browser book control, retaining the selected target.
   await a.keyboard.press('k');await a.wait_for_timeout(200)
   await missile.get_by_role('button',name='Użyj',exact=True).click();await a.wait_for_timeout(300)
   assert p.mana==before-20,(p.mana,before)
   volley=[fx for fx in g.effects if fx.get('spell_id')=='magic_missile'][-1]
   assert volley['shots']==3 and len(p.combat_log)==3
   checks.append('Browser cast at chosen circle really spends 20 mana and resolves three hits')
   p.attack_cooldown_until=0
   await missile.locator('.spell-power-picker').select_option('0');await a.wait_for_timeout(300)
   before=p.mana;old_logs=len(p.combat_log)
   await missile.get_by_role('button',name='Użyj',exact=True).click();await a.wait_for_timeout(250)
   assert p.mana==before-30 and len(p.combat_log)==old_logs+4
   assert [fx for fx in g.effects if fx.get('spell_id')=='magic_missile'][-1]['shots']==4
   checks.append('Auto restores the highest unlocked rank and four authoritative projectiles')
   for width,height in [(390,844),(320,700),(844,390)]:
    await a.set_viewport_size({'width':width,'height':height});await a.wait_for_timeout(250)
    await missile.scroll_into_view_if_needed()
    assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
    picker=missile.locator('.spell-power-picker');box=await picker.bounding_box()
    assert box and box['x']>=0 and box['x']+box['width']<=width+1,box
    await picker.select_option('1');await a.wait_for_timeout(180)
    assert p.spell_circle_choices.get('magic_missile')==1
    await picker.select_option('0');await a.wait_for_timeout(180)
    await a.screenshot(path=str(OUT/f'03_spell_power_{width}x{height}.png'))
    checks.append(f'{width}x{height}: power controls usable, current values visible, no page overflow')
   await a.set_viewport_size({'width':1440,'height':900});await a.keyboard.press('Escape')
   p.level=80;p.mana=p.max_mana;p.hp=p.max_hp;p.attack_cooldown_until=0
   await a.wait_for_timeout(300)
   # Capture actual scaled effect; controlled phase avoids reliance on frame timing.
   await g.cast_spell(p,'magic_missile',e.id)
   fx=[fx for fx in g.effects if fx.get('spell_id')=='magic_missile'][-1]
   assert fx['shots']==11 and fx['visual']['shots']==11
   await a.evaluate('''fx=>{const c=document.createElement('canvas');c.width=1100;c.height=350;c.id='qaMissile';c.style.cssText='position:fixed;left:170px;top:240px;z-index:99999;background:#12232c;border:1px solid #557788;border-radius:14px';document.body.append(c);const ctx=c.getContext('2d');ctx.fillStyle='#eeeeee';ctx.font='22px sans-serif';ctx.fillText('Magiczny pocisk · krąg IX · 11 pocisków',28,36);ctx.translate(150,190);window.BractwoSpellVFX.draw(ctx,{...fx,x:0,y:0,target_x:800,target_y:0,targets:[{x:800,y:0}]},0.55,1000);}''',fx)
   await a.screenshot(path=str(OUT/'04_eleven_projectile_renderer.png'))
   await a.evaluate("document.getElementById('qaMissile').remove()")
   checks.append('Maximum rank emits and renders eleven missiles using the real effect payload/renderer')
   b,q=await new_page('SkalowanieDruid','druid');q.level=19;q.xp=0;g.award(q,xp_next(19),0)
   await b.wait_for_selector('.level-up-card[data-level="20"]')
   text=await b.locator('.level-up-card').inner_text()
   assert 'Leczenie ran +2k8 do leczenia' in text,text
   assert 'Leczenie ran +1 do leczenia' in text,text
   assert 'Promień księżyca +1k10 do obrażeń' in text,text
   checks.append('Druid level 20 separates upcast dice and ability modifier gains; field dice included')
   await b.screenshot(path=str(OUT/'05_druid_level_20_deltas.png'))
   await b.set_viewport_size({'width':390,'height':844});await b.wait_for_timeout(250)
   assert not await b.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   close=await b.locator('.level-up-close').bounding_box()
   assert close and close['y']+close['height']<=844
   await b.screenshot(path=str(OUT/'06_druid_mobile_deltas.png'))
   checks.append('Mobile spell growth panel scrolls, with Close remaining accessible')
   await close_all(b);await b.set_viewport_size({'width':1440,'height':900})
   q.level=20;q.mana=q.max_mana;q.hp=q.max_hp;q.x=1100
   await g.cast_spell(q,'moonbeam',e.id)
   field=g.spell_fields[-1];assert field['profile']['dice']==[3,10,0]
   q.level=40;assert field['profile']['dice']==[3,10,0]
   checks.append('Persistent area retains its original paid dice after a later circle unlock')
   g.break_concentration(q);q.level=20;q.attack_cooldown_until=0
   await g.cast_spell(q,'call_lightning',e.id)
   q.level=30;q.mana=0
   await b.keyboard.press('k');await b.wait_for_timeout(350)
   lightning=b.locator('.sheet-spell[data-spell="call_lightning"]')
   assert '3k10' in await lightning.inner_text(),await lightning.inner_text()
   assert 'Utrzymywany czar' in await lightning.inner_text()
   assert await lightning.get_by_role('button',name='Zakończ czar',exact=True).count()==1
   await lightning.get_by_role('button',name='Zakończ czar',exact=True).click();await b.wait_for_timeout(300)
   assert not q.concentration
   assert '4k10' in await lightning.inner_text()
   assert await lightning.get_by_role('button',name='Użyj',exact=True).is_disabled()
   checks.append('Repeated concentration shows locked rank; stopping exposes the new paid rank, disabled at zero mana')
   g.persist()
   assert not errors,errors
   data={'checks':checks,'count':len(checks),'errors':errors,'transport':'controlled Python WebSocket bridge','sent':sent}
   (OUT/'browser-results.json').write_text(json.dumps(data,ensure_ascii=False,indent=2))
   print(json.dumps(data,ensure_ascii=False,indent=2))
   closing[0]=True
   for ws in sockets_all:
    if not ws.closed:await ws.close()
   for task in tasks:task.cancel()
   await asyncio.gather(*tasks,return_exceptions=True)
   await asyncio.sleep(.2)
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
