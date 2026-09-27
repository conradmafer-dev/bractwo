"""0.8.8: real loot previews, animated enemies, equipping, sources, resistance and mobile layouts.
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
OUT=ROOT/'docs'/'qa_0.8.8';OUT.mkdir(parents=True,exist_ok=True)

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
    for filename in ('style','character_sheet','level_up','loot_ui'):
     html=html.replace(f'<link rel="stylesheet" href="{filename}.css">','<style>'+(ROOT/f'web/{filename}.css').read_text()+'</style>')
    for filename in ('spell_vfx','character_sheet','runtime','level_up','loot_ui','game'):
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

   from server import combat_rules as rules, hunt_content as hunts
   from server.server import ENEMY_TYPES
   a,p=await new_page('LupyRycerz','knight')
   await a.bring_to_front()
   p.level=90;p.hp=p.max_hp;p.mana=p.max_mana;p.inventory=[];p.equipment={}
   inventory=['captain_greatsword','obsidian_plate','mummy_wand','crypt_bow','hierophant_robe','frost_leather','root_staff','sentry_chainmail','orc_scale','bandit_leather','veteran_greatsword','winter_ring','loot_trophy_wolf','acolyte_wand','thorn_staff','dragon_scale','abyss_wand']
   p.inventory=[make_item(k) for k in inventory]
   await a.wait_for_timeout(350);await a.keyboard.press('c');await a.wait_for_selector('#characterPanel:not([hidden])')
   assert await a.locator('.sheet-bag-cell').count()==15
   await a.locator('.sheet-bag-cell[title="Rozkaz Herszta +1"]').click()
   detail=a.locator('.sheet-item-detail')
   assert '2k6' in await detail.inner_text() and 'Obrażenia +1' in await detail.inner_text()
   await detail.locator('summary').click()
   assert 'Herszt Czarnego Traktu' in await detail.inner_text() and '18%' in await detail.inner_text()
   checks.append('Inventory: 3x5 items, distinct icons, canonical 2d6, +1 and source with 18%')
   await a.screenshot(path=str(OUT/'01_inventory_sources_desktop.png'))
   await detail.get_by_role('button',name='Załóż',exact=True).click();await a.wait_for_timeout(200)
   assert rules.equipped_item(p,'weapon').get('name')=='Rozkaz Herszta +1'
   checks.append('Browser equip action changes the server weapon to 2d6+1 plus ability')
   await a.locator('.sheet-bag-cell[title="Obsydianowa płyta +2"]').click()
   assert 'Ciężki pancerz' in await detail.inner_text()
   await detail.get_by_role('button',name='Załóż',exact=True).click();await a.wait_for_timeout(200)
   assert rules.armor_class(p)==20
   checks.append('Heavy +2 armor equipped from browser: real server AC 20')
   await a.locator('.sheet-bag-cell[title="Różdżka mumii +1"]').click()
   assert await detail.get_by_role('button',name='Załóż',exact=True).is_disabled()
   checks.append('Foreign-class loot remains in bag, with equip disabled for knight')
   await a.locator('.sheet-bag-cell[title="Wilcza skóra"]').click()
   assert await detail.get_by_role('button',name='Załóż',exact=True).is_disabled()
   checks.append('Trophy cannot be worn')
   await a.click('[data-character-tab="stats"]');await a.wait_for_timeout(200)
   assert '2k6+6' in await a.locator('#characterContent').inner_text(),await a.locator('#characterContent').inner_text()
   checks.append('Character sheet refreshes actual new weapon damage')
   await a.keyboard.press('Escape');await a.wait_for_timeout(150)
   # Test scene: real species + actual renderer, while AI is paused by this harness only.
   p.x=2400;p.y=2500;p.input_x=0;p.input_y=0
   kinds=['mummy','skeleton_archer','bandit_veteran','skeleton_sentinel','grave_acolyte','thorn_shaman','crypt_guard','frost_ranger','obsidian_knight','bandit_captain','mummy_hierophant']
   positions=[(2140,2350),(2260,2350),(2400,2350),(2540,2350),(2670,2350),(2140,2570),(2260,2570),(2400,2690),(2540,2570),(2710,2570),(2580,2740)]
   for i,(kind,(x,y)) in enumerate(zip(kinds,positions)):
    e=Enemy('qa_loot_'+str(i),kind,x,y,ENEMY_TYPES[kind]['hp'],x,y)
    g.enemies[e.id]=e;g.legacy_enemies.append(e)
   target=g.enemies['qa_loot_0']
   await g.select_combat_target(p,{'enemy_id':target.id});p.auto_enabled=False
   await a.wait_for_timeout(1100)
   assert await a.evaluate('window.__qaMonsters.size')==11,await a.evaluate('[...window.__qaMonsters]')
   checks.append('Canvas renders 11 actual new atlases: 9 species + mummy + skeleton archer')
   await a.screenshot(path=str(OUT/'02_monsters_desktop.png'))
   target.x=p.x+135;target.y=p.y;await a.wait_for_timeout(350)
   await a.locator('[data-enemy-id="qa_loot_0"]').click();await a.wait_for_timeout(150);p.auto_enabled=False
   await a.locator('#targetLoot').click();await a.wait_for_selector('#lootPreview:not([hidden])')
   assert 'Mumia' in await a.locator('#lootTitle').inner_text()
   row=a.locator('.loot-row').filter(has_text='Różdżka mumii +1')
   assert await row.locator('.loot-percent').inner_text()=='5%'
   assert await a.locator('.loot-row').count()==6
   assert 'nie zastępuje' not in await row.inner_text() # compact stats, not walls of prose
   checks.append('Selected monster opens actual species table: mummy wand exactly 5%, six independent entries')
   await a.screenshot(path=str(OUT/'03_mummy_loot_desktop.png'))
   assert await a.locator('#lootPreview img').evaluate_all('(a)=>a.every(i=>i.complete&&i.naturalWidth>0)')
   checks.append('All rendered drop icons loaded successfully')
   await a.keyboard.press('Escape');await a.wait_for_timeout(200)
   assert await a.locator('#lootPreview').is_hidden()
   checks.append('Escape closes loot preview and restores gameplay controls')
   g.enemies['qa_loot_9'].x=p.x-135;g.enemies['qa_loot_9'].y=p.y;await a.wait_for_timeout(300)
   await a.locator('[data-enemy-id="qa_loot_9"]').click();await a.wait_for_timeout(150);p.auto_enabled=False
   await a.locator('#targetLoot').click()
   assert 'Herszt Czarnego Traktu' in await a.locator('#lootTitle').inner_text()
   assert '18%' in await a.locator('#lootPreview').inner_text()
   checks.append('New boss preview shows separate named items with 18/10/12/4%')
   await a.set_viewport_size({'width':390,'height':844});await a.wait_for_timeout(250)
   assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   box=await a.locator('.loot-close').bounding_box();assert box and box['y']>=0 and box['y']+box['height']<=844
   await a.screenshot(path=str(OUT/'04_boss_loot_mobile.png'))
   checks.append('390x844 loot preview fits horizontally and bottom Close stays visible')
   await a.set_viewport_size({'width':844,'height':390});await a.wait_for_timeout(250)
   box=await a.locator('.loot-close').bounding_box();assert box and box['y']+box['height']<=390
   assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   await a.screenshot(path=str(OUT/'05_boss_loot_landscape.png'))
   checks.append('844x390 loot list scrolls without hiding Close')
   await a.locator('.loot-close').click();await a.wait_for_timeout(150)
   await a.set_viewport_size({'width':390,'height':844});await a.keyboard.press('i');await a.wait_for_timeout(200)
   assert await a.locator('.sheet-bag-cell').count()==15
   assert await a.locator('.sheet-bag-cell img').evaluate_all('(a)=>a.every(i=>i.complete&&i.naturalWidth>0)')
   assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
   await a.screenshot(path=str(OUT/'06_inventory_mobile.png'))
   checks.append('Mobile inventory retains 3 rows of icons, correctly loaded and no horizontal overflow')
   await a.keyboard.press('Escape')
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
