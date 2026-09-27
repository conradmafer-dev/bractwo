"""0.8.11: held movement, target death, nonmodal windows and zoomable complete atlas.
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
OUT=ROOT/'docs'/'qa_0.8.11';OUT.mkdir(parents=True,exist_ok=True)

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


   a,p=await new_page('TestRuch','druid')
   async def wait(ms=300):await a.wait_for_timeout(ms)
   async def snap(name):await a.screenshot(path=str(OUT/name))
   async def clear_windows():
    for _ in range(5):await a.keyboard.press('Escape')
    await wait(100)
   async def moving(dx,dy):
    await wait(180)
    assert (abs(p.dx)>0.1)==bool(dx) and (abs(p.dy)>0.1)==bool(dy),(p.dx,p.dy,dx,dy)
    if dx:assert p.dx*dx>0
    if dy:assert p.dy*dy>0
   async def enemy(eid):
    e=Enemy(eid,'rat',p.x+140,p.y,500,p.x+140,p.y);g.enemies[e.id]=e;g.reindex_enemy(e)
    p.attack_cooldown_until=clock()+5000
    await wait();return e
   try:
    # Every test below uses the real client input and the real server's input handler.
    for i,(key,dx,dy) in enumerate([('KeyW',0,-1),('KeyS',0,1),('KeyA',-1,0),('KeyD',1,0)]):
     p.x,p.y=2200,1200;await wait()
     e=await enemy('world_qa_death_'+str(i))
     await a.keyboard.down(key);await moving(dx,dy)
     await a.locator(f'[data-enemy-id="{e.id}"]').click();await moving(dx,dy)
     x,y=p.x,p.y;await g.defeat(e);await moving(dx,dy)
     assert (p.x-x)*dx+(p.y-y)*dy>1,(key,p.x-x,p.y-y)
     assert not await a.locator('#targetCard').is_visible()
     await a.keyboard.up(key);await wait();assert abs(p.dx)+abs(p.dy)==0
     checks.append(f'{key}: select monster, actual server death, automatic deselection keep held direction; release stops.')
    p.x,p.y=2200,1200;e=await enemy('world_qa_clear_diagonal')
    await a.keyboard.down('KeyW');await a.keyboard.down('KeyD');await moving(1,-1)
    await a.locator(f'[data-enemy-id="{e.id}"]').click();await moving(1,-1)
    await a.locator('#clearTarget').click();await moving(1,-1)
    await a.keyboard.up('KeyW');await moving(1,0);await a.keyboard.up('KeyD');await wait()
    checks.append('Manual target X and separate key releases preserve diagonal movement correctly.')
    # Ordinary windows no longer own the movement state. Clicks on action buttons keep WASD.
    for key,sel in [('KeyC','#characterPanel'),('KeyI','#characterPanel'),('KeyK','#characterPanel'),('KeyJ','#sidePanel'),('KeyP','#sidePanel'),('KeyH','#helpPanel')]:
     await clear_windows();p.x,p.y=2200,1200;await wait()
     await a.keyboard.down('KeyD');await moving(1,0)
     await a.keyboard.press(key);await wait();assert await a.locator(sel).is_visible(),key
     await moving(1,0)
     await a.keyboard.press('Escape');await moving(1,0)
     assert not await a.locator(sel).is_visible(),key
     await a.keyboard.up('KeyD');await wait()
     checks.append(f'{key}: window opens and Escape closes without stopping held movement.')
    # E opens atlas when no interaction nearby, closes it even after walking away.
    await clear_windows();p.x,p.y=2200,1200;await wait()
    await a.keyboard.down('KeyS');await moving(0,1)
    await a.keyboard.press('KeyE');await wait();assert await a.locator('#sidePanel').is_visible()
    await moving(0,1);await a.keyboard.press('KeyE');await wait()
    assert not await a.locator('#sidePanel').is_visible();await moving(0,1)
    await a.keyboard.up('KeyS');checks.append('E toggles world/atlas while held movement continues both ways.')
    p.x,p.y=680,1180;await wait();await a.keyboard.press('KeyE');await wait()
    assert await a.locator('#merchantPanel').is_visible()
    await a.keyboard.down('KeyD');await moving(1,0);await a.keyboard.press('KeyE');await wait()
    assert not await a.locator('#merchantPanel').is_visible();await moving(1,0)
    await a.keyboard.up('KeyD');checks.append('E also closes the actual merchant window while movement continues.')
    # Test safe typing and loss of application focus, not a workaround with latched movement.
    p.x,p.y=2200,1200;await wait();await a.keyboard.down('KeyD');await moving(1,0)
    await a.keyboard.press('Enter');await wait();assert p.dx==p.dy==0
    await a.keyboard.up('KeyD');await a.keyboard.type('wasd test');await wait();assert p.dx==p.dy==0
    await a.keyboard.press('Escape');await a.keyboard.down('KeyD');await moving(1,0)
    await a.evaluate("window.dispatchEvent(new Event('blur'))");await wait();assert p.dx==p.dy==0
    await a.keyboard.up('KeyD');await a.evaluate("window.dispatchEvent(new Event('focus'))");await wait()
    assert p.dx==p.dy==0;checks.append('Chat typing and real blur/reset safety still stop motion; no stuck key after focus.')
    # Atlas interaction and persistent camera, screenshots use starting river and bridge.
    await clear_windows();p.x,p.y=560,1180;await wait()
    await a.evaluate("document.getElementById('minimapCard').hidden=false")
    await wait();await snap('01_minimap_original_river.png')
    # Pixel projection on actual minimap canvas: original bridge must be drawn on water.
    pixels=await a.evaluate('''([x,y])=>{const c=document.getElementById('minimap'),g=c.getContext('2d'),mw=4800,mh=3400;
      const pixel=(wx,wy)=>Array.from(g.getImageData(Math.floor((wx-x+mw/2)/mw*c.width),Math.floor((wy-y+mh/2)/mh*c.height),1,1).data);
      return {water:pixel(1560,930),bridge:pixel(1560,1150)}}''',[p.x,p.y])
    assert pixels['water'][:3]==[85,158,188],pixels
    assert pixels['bridge'][:3]==[227,195,136],pixels
    checks.append('Minimap actual canvas pixels include original river and correctly overlaid starter bridge.')
    p.x,p.y=2200,1200;await wait();await a.keyboard.press('KeyE');await wait()
    assert await a.locator('#atlasCanvas').is_visible()
    def zoom():return a.locator('#atlasCanvas').get_attribute('data-zoom')
    assert await zoom()=='1'
    await a.locator('#atlasCanvas').click(position={'x':170,'y':170});await wait()
    assert await zoom()=='2' and await a.locator('#sidePanel').is_visible()
    await a.locator('#atlasCanvas').click(button='right',position={'x':170,'y':170});await wait()
    assert await zoom()=='1'
    await a.get_by_role('button',name='Pokaż okolicę postaci',exact=True).click();await wait();assert await zoom()=='32'
    await snap('02_atlas_nearby_desktop.png')
    checks.append('Atlas left click zooms in, right click zooms out, Nearby centers camera; never closes.')
    # A real window drag must not reset a held direction or trigger map navigation.
    before_rect=await a.locator('#sidePanel').bounding_box()
    head=await a.locator('#sidePanel .panel-grip').bounding_box()
    await a.keyboard.down('KeyD');await moving(1,0)
    await a.mouse.move(head['x']+10,head['y']+8);await a.mouse.down()
    await a.mouse.move(head['x']-100,head['y']+18,steps=10);await a.mouse.up();await moving(1,0)
    await a.keyboard.up('KeyD');await wait()
    assert await a.locator('#sidePanel').evaluate("e=>e.classList.contains('hud-floating')")
    assert abs((await a.locator('#sidePanel').bounding_box())['x']-before_rect['x'])>50
    checks.append('Dragging an open atlas window does not clear held movement or its map camera.')
    await a.locator('#hudVisibility>button').nth(1).click();await wait()

    map_pixels=await a.evaluate('''()=>{const c=document.getElementById('atlasCanvas'),g=c.getContext('2d'),b=JSON.parse(c.dataset.bounds);
      const pix=(x,y)=>Array.from(g.getImageData(Math.floor((x-b.x)/b.w*c.width),Math.floor((y-b.y)/b.h*c.height),1,1).data);
      return {water:pix(1560,930),bridge:pix(1560,1120)}}''')
    assert map_pixels['water'][:3]==[85,158,188],map_pixels
    assert map_pixels['bridge'][:3]==[227,195,136],map_pixels
    checks.append('Atlas actual canvas pixels show the same original river and starter bridge as the game world.')
    await a.locator('#atlasCanvas').hover();await a.mouse.wheel(0,-100);await wait();assert await zoom()=='64'
    await a.mouse.wheel(0,100);await wait();assert await zoom()=='32'
    await a.get_by_role('button',name='Oddal mapę',exact=True).click();await wait();assert await zoom()=='16'
    await a.get_by_role('button',name='Przybliż mapę',exact=True).click();await wait();assert await zoom()=='32'
    checks.append('Wheel and accessible plus/minus controls change zoom within limits.')
    canvas=a.locator('#atlasCanvas');rect=await canvas.bounding_box();old=await canvas.get_attribute('data-bounds')
    await a.mouse.move(rect['x']+rect['width']*.6,rect['y']+rect['height']*.6);await a.mouse.down()
    await a.mouse.move(rect['x']+rect['width']*.4,rect['y']+rect['height']*.4,steps=10);await a.mouse.up();await wait()
    assert await zoom()=='32';assert await canvas.get_attribute('data-bounds')!=old
    checks.append('Dragging atlas pans view without a stray zoom or closing event.')
    before=await canvas.get_attribute('data-bounds');await a.keyboard.down('KeyD');await moving(1,0);await wait(600)
    await a.keyboard.up('KeyD');await wait();assert await canvas.get_attribute('data-bounds')==before
    await a.keyboard.press('KeyE');await wait();assert not await a.locator('#sidePanel').is_visible()
    await a.keyboard.press('KeyE');await wait();assert await zoom()=='32'
    assert await a.locator('#atlasCanvas').get_attribute('data-bounds')==before
    checks.append('Map zoom/pan survive movement snapshots and closing/reopening with E.')
    await a.get_by_role('button',name='Kliknij mapę, aby wyznaczyć cel nawigacji',exact=True).click()
    await a.locator('#atlasCanvas').click(position={'x':170,'y':160});await wait();assert await zoom()=='32'
    assert await a.locator('#sidePanel').is_visible();assert 'Punkt na mapie' in await a.locator('#questTracker').inner_text()
    checks.append('Explicit navigation selection sets a waypoint without changing zoom or closing atlas.')
    # authoritative class gates, not global legacy milestones
    await a.locator('#progressionNav [data-view="growth"]').click();await wait()
    growth=await a.locator('#progressionContent').inner_text()
    assert 'II krąg' in growth and 'Promień księżyca' in growth and 'Mana +80' in growth
    assert 'Magiczny pocisk' not in growth and 'Palący promień' not in growth
    assert 'nie zwiększają' in growth
    await snap('03_growth_druid_desktop.png')
    checks.append('Development shows only authoritative druid gates and labels old training counters without fake bonuses.')
    # help styles, mobile map controls, ordinary windows and keyboard on landscape
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await wait()
     await a.locator('#progressionNav [data-view="atlas"]').click();await wait()
     await a.get_by_role('button',name='Pokaż okolicę postaci',exact=True).click();await wait()
     await a.get_by_role('button',name='Oddal mapę',exact=True).click();await wait();assert await zoom()=='16'
     await a.get_by_role('button',name='Przybliż mapę',exact=True).click();await wait();assert await zoom()=='32'
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
     map_rect=await a.locator('#atlasCanvas').bounding_box();window_rect=await a.locator('#sidePanel').bounding_box()
     visible_map=min(map_rect['y']+map_rect['height'],window_rect['y']+window_rect['height'])-max(map_rect['y'],window_rect['y'])
     assert visible_map>=100,('unusable map strip',width,height,visible_map)

     await snap('04_atlas_'+label+'.png')
     await a.keyboard.press('KeyE');await wait();assert not await a.locator('#sidePanel').is_visible()
     await a.keyboard.press('KeyC');await wait();await a.keyboard.down('KeyD');await moving(1,0);await a.keyboard.up('KeyD')
     await a.keyboard.press('Escape');await a.keyboard.press('KeyE');await wait()
     checks.append(f'{width}x{height}: usable map zoom buttons, bounded page, E close and moving with character sheet.')
    await a.set_viewport_size({'width':1440,'height':900});await clear_windows()
    p.x,p.y=2200,1200;p.level=10;p.hp=p.max_hp;p.mana=p.max_mana;await wait()
    await a.keyboard.press('KeyK');await wait();await snap('05_spells_unchanged_scaling.png')
    assert not errors,errors;checks.append('No JavaScript errors across input, window, map and inventory regression actions.')
    (OUT/'results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server','monster_ai':'paused; actual enemy death via server defeat()','held_movement':'real browser key events and authoritative dx/dy/position'},ensure_ascii=False,indent=2))
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
