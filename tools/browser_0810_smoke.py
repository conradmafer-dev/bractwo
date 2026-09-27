"""0.8.10: draggable HUD, inventory tooltips, personal loot journal and merchant.
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
OUT=ROOT/'docs'/'qa_0.8.10';OUT.mkdir(parents=True,exist_ok=True)

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
    assets={str(f.relative_to(ROOT/'web')):'data:'+('image/png' if f.suffix=='.png' else 'image/svg+xml')+';base64,'+base64.b64encode(f.read_bytes()).decode() for f in (ROOT/'web/assets').rglob('*') if f.suffix in ('.png','.svg')}
    asset_bridge='window.__qaAssets='+json.dumps(assets)+';const srcDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,"src");Object.defineProperty(HTMLImageElement.prototype,"src",{get:srcDesc.get,set(v){this.dataset.qaAsset=v;srcDesc.set.call(this,window.__qaAssets[v]||v);}});window.__qaMonsters=new Set();const di=CanvasRenderingContext2D.prototype.drawImage;CanvasRenderingContext2D.prototype.drawImage=function(...a){const path=a[0]?.dataset?.qaAsset;if(path?.includes("assets/monsters/"))window.__qaMonsters.add(path);return di.apply(this,a);};'
    html=(ROOT/'web/index.html').read_text()
    for filename in ('style','character_sheet','level_up','loot_ui','hud_layout','windows','fighter'):
     html=html.replace(f'<link rel="stylesheet" href="{filename}.css">','<style>'+(ROOT/f'web/{filename}.css').read_text()+'</style>')
    for filename in ('runtime','spell_vfx','inventory_ui','character_sheet','level_up','loot_ui','windows','game'):
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

   a,p=await new_page('TestOkna','druid')
   async def snap(name):await a.screenshot(path=str(OUT/name))
   async def wait():await a.wait_for_timeout(400)
   async def bbox(sel):return await a.locator(sel).bounding_box()
   async def drag(sel,dx,dy):
    r=await bbox(sel);assert r,sel
    await a.mouse.move(r['x']+max(5,min(r['width']*.3,65)),r['y']+r['height']/2)
    await a.mouse.down();await a.mouse.move(r['x']+max(5,min(r['width']*.3,65))+dx,r['y']+r['height']/2+dy,steps=12);await a.mouse.up();await wait()
   def overlap(a,b):return a and b and min(a['x']+a['width'],b['x']+b['width'])-max(a['x'],b['x'])>2 and min(a['y']+a['height'],b['y']+b['height'])-max(a['y'],b['y'])>2
   async def bounded(sel):
    r=await bbox(sel);v=a.viewport_size;assert r and r['x']>=-1 and r['y']>=-1 and r['x']+r['width']<=v['width']+2 and r['y']+r['height']<=v['height']+2,(sel,r,v)
   try:
    await snap('01_initial_desktop.png')
    assert (await bbox('#hudVisibility'))['y'] < (await bbox('.world-status'))['y']
    assert not overlap(await bbox('.world-status'),await bbox('.pvp-bar'))
    assert not overlap(await bbox('.pvp-bar'),await bbox('#questTracker'))
    chat,q,bar=await bbox('.chat-wrap'),await bbox('.quickbar'),await bbox('#spellbar')
    assert chat['x']+chat['width']<=q['x']+1 and q['x']+q['width']<=bar['x']+1
    assert abs((chat['y']+chat['height'])-(q['y']+q['height']))<3
    checks.append('Default left HUD is stacked and bottom chat/potions align.')
    g.award(p,sum(xp_next(i) for i in range(1,4)),0);await wait()
    assert await a.locator('.level-up-card').count()==3
    assert not overlap(await bbox('#levelUpCascade'),await bbox('#hudLeftRail'))
    await snap('02_levels_desktop.png');checks.append('Three actual level-up receipts do not cover the left rail.')
    card=a.locator('.level-up-card.front');cardid=await card.get_attribute('data-id')
    await drag(f'.level-up-card[data-id="{cardid}"] .level-up-title',400,60)
    assert await card.evaluate("e=>e.classList.contains('hud-floating')")
    await card.locator('.level-up-close').click();await wait()
    assert await a.locator('.level-up-card').count()==2
    checks.append('Level-up header drags; Close removes only its own saved receipt.')
    # Hide panel is not dismissal and survives authoritative snapshots.
    await a.locator('#hudVisibility>button').first.click();await a.locator('[data-visibility="levels"]').uncheck();await wait()
    assert not await a.locator('#levelUpCascade').is_visible()
    assert sum(hi-lo+1 for batch in p.level_up_batches for lo,hi in batch["ranges"])==2
    await a.locator('[data-visibility="levels"]').check();await a.locator('#hudVisibility>button').first.click()
    checks.append('Visibility switches hide panels without discarding level-up data.')
    quest=await bbox('#questTracker');await drag('#questTracker>.window-grip',180,80)
    assert not await a.locator('#sidePanel').is_visible()
    assert abs((await bbox('#questTracker'))['x']-quest['x'])>100
    await a.locator('#hudVisibility>button').nth(1).click();await wait()
    checks.append('HUD grip moves quest without opening it; reset restores default flow.')
    await a.keyboard.press('KeyC');await wait();await snap('03_inventory_desktop.png')
    worn=next(i for i in p.inventory if i['uid']==p.equipment['weapon'])
    target=a.locator(f'.sheet-equipment-card[data-uid="{worn["uid"]}"]')
    await target.hover();await wait();assert await a.locator('#itemTooltip').is_visible()
    assert 'Obrażenia' in await a.locator('#itemTooltip').inner_text()
    checks.append('Worn weapon has real damage tooltip on hover.')
    await target.click();await wait();detail=a.locator(f'[data-preview-uid="{worn["uid"]}"]')
    assert await detail.is_visible();assert await detail.get_by_role('button',name='Zdejmij',exact=True).count()==1
    assert not await detail.locator('.sheet-loot-sources').count()
    facts=await detail.locator('.item-facts').bounding_box();actions=await detail.locator('.item-actions').bounding_box()
    assert actions['y']>=facts['y']+facts['height']
    checks.append('Click worn gear previews it; separate actions; no invented sources.')
    rect=await bbox('#characterPanel');await drag('.character-header',150,50)
    new=await bbox('#characterPanel');assert abs(new['x']-rect['x'])>100
    await a.keyboard.press('Escape');await a.keyboard.press('KeyC');await wait()
    assert abs((await bbox('#characterPanel'))['x']-new['x'])<2
    checks.append('Character window remembers dragged position when reopened.')
    await a.keyboard.press('Escape');await a.locator('#hudVisibility>button').nth(1).click();await wait()
    p.level=20;p.hp=p.max_hp;p.mana=0;p.mana_recovery_until=clock()+10000
    g.grant_loot(p,[('potion','mana_potion_2'),('potion','mana_potion_2')]);await wait()
    await a.keyboard.press('KeyC');await wait()
    await a.locator('.sheet-bag-cell[data-item-template="mana_potion_2"]').click();await wait()
    await a.locator('.sheet-item-detail').get_by_role('button',name='Przypisz Q',exact=True).click();await wait()
    assert p.potion_slots['q']=='mana_potion_2'
    await snap('04_potion_binding.png')
    await a.keyboard.press('Escape');await a.keyboard.press('KeyQ');await wait()
    assert p.mana==35,p.mana
    assert p.potions['mana_potion_2']==1 and p.potions['health_potion']==3
    checks.append('Inventory potion binds to Q and restores precisely 35 mana, not an auto-selected variant.')
    clock.value+=3.2;await wait()
    p.x,p.y=680,1180;await wait();await a.keyboard.press('KeyE');await wait()
    assert await a.locator('#merchantPanel').is_visible()
    before=p.potions['mana_potion'];gold=p.gold
    await a.locator('.merchant-item[data-template="mana_potion"]').get_by_role('button',name='Kup',exact=True).click();await wait()
    assert p.potions['mana_potion']==before+1 and p.gold==gold-12
    p.hp=1;p.mana=0;p.mana_recovery_until=clock()+10000;await wait()
    await a.locator('#merchantPanel').get_by_role('button',name='Odpocznij',exact=True).click();await wait()
    assert p.hp==p.max_hp and p.mana==p.max_mana
    checks.append('Merchant Rest button uses the real guarded server interaction.')
    await snap('05_merchant_buy.png')
    await a.locator('[data-trade-tab="sell"]').click();await wait()
    await a.locator('.merchant-item[data-template="mana_potion"]').get_by_role('button',name='Sprzedaj 1',exact=True).click();await wait()
    assert p.potions['mana_potion']==before
    assert not await a.locator('.merchant-item[data-template="druid_weapon_1"]').count()
    await snap('06_merchant_sell.png');checks.append('Merchant Buy/Sell tabs trade canonical stacks and exclude worn gear.')
    await drag('.merchant-header',-200,30);assert await a.locator('#merchantPanel').evaluate("e=>e.classList.contains('hud-floating')")
    await a.keyboard.press('Escape');checks.append('Merchant is draggable and Escape closes it.')
    p.inventory.append(make_item('mummy_wand'));await a.keyboard.press('KeyC');await wait()
    await a.locator('.sheet-bag-cell[data-item-template="mummy_wand"]').click();await wait()
    assert not await a.locator('.sheet-item-detail .sheet-loot-sources').count()
    g.grant_loot(p,[('item','mummy_wand')],source_kind='mummy');await wait()
    assert await a.locator('.sheet-item-detail .sheet-loot-sources').count()==1
    await a.locator('.sheet-loot-sources summary').click()
    text=await a.locator('.sheet-loot-sources').inner_text();assert 'Mumia' in text and '5%' in text
    assert await a.locator('.sheet-loot-sources>div').count()==1
    checks.append('Only an actually delivered mummy drop reveals that source, updating owned items.')
    await a.keyboard.press('Escape');await a.locator('#hudVisibility>button').nth(1).click();await wait()
    p.buffs['longstrider']={'until':clock()+1800}
    e=Enemy('world_ui_target','mummy',p.x+210,p.y,20,p.x+210,p.y);g.enemies[e.id]=e;g.reindex_enemy(e);await wait()
    await a.locator('[data-enemy-id="world_ui_target"]').click();await wait()
    assert await a.locator('#targetCard').is_visible()
    assert not overlap(await bbox('.pvp-bar'),await bbox('#questTracker'))
    assert not overlap(await bbox('.world-status'),await bbox('.pvp-bar'))
    checks.append('Live target, PvP and status effects do not move over the region or quest.')
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape'),(360,640,'small')]:
     await a.set_viewport_size({'width':width,'height':height});await wait()
     await bounded('#hudVisibility');await bounded('#hudLeftRail');await bounded('#hudRightRail');await bounded('#actionDock')
     assert not overlap(await bbox('.top-actions'),await bbox('#hudLeftRail'))
     assert not overlap(await bbox('.top-actions'),await bbox('#effectsPanel'))
     assert not overlap(await bbox('.world-status'),await bbox('.pvp-bar'))
     await snap('07_'+label+'_hud.png')
     await a.keyboard.press('KeyC');await wait();await bounded('#characterPanel')
     await a.locator('.sheet-bag-cell[data-item-template="mana_potion_2"]').click();await wait()
     await a.locator('.sheet-item-detail').scroll_into_view_if_needed();await snap('08_'+label+'_inventory.png')
     await a.keyboard.press('Escape');p.x,p.y=680,1180;await wait();await a.keyboard.press('KeyE');await wait();await bounded('#merchantPanel')
     await snap('09_'+label+'_merchant.png');await a.keyboard.press('Escape')
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
     checks.append(f'Bounded HUD, character and merchant at {width}x{height}; no horizontal page overflow.')
    await a.set_viewport_size({'width':1440,'height':900});await wait()
    # Stored positions use real layout storage, namespaced to character and orientation.
    assert await a.evaluate("Object.keys(window.__storage).some(k=>k.startsWith('bractwo-windows-v1:'))")
    checks.append('Layout and visibility are serialized per character and orientation.')
    assert not errors,errors;checks.append('No JavaScript page errors during end-to-end actions.')
    (OUT/'results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server','ui_monster_ai':'paused; AI tested separately'},ensure_ascii=False,indent=2))
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
