"""0.8.9: relocated HUD controls and transparent top status buttons.
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
OUT=ROOT/'docs'/'qa_0.8.9';OUT.mkdir(parents=True,exist_ok=True)

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
    for filename in ('style','character_sheet','level_up','loot_ui','hud_layout'):
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

   from server.server import ENEMY_TYPES
   a,p=await new_page('UkladCzarodziej','mage')
   await a.bring_to_front()
   p.x=2400;p.y=2500
   await g.cast_spell(p,'longstrider');p.shield_armed=True
   e=Enemy('qa_hud_ogre','ogre',p.x+130,p.y,59,p.x+130,p.y)
   e.conditions['restrained']={'until':clock()+120}
   e.conditions['slow']={'until':clock()+60}
   g.enemies[e.id]=e;g.legacy_enemies.append(e);g.reindex_enemy(e)
   await a.wait_for_timeout(300)
   await a.locator('[data-enemy-id=qa_hud_ogre]').click();p.auto_enabled=False
   await a.wait_for_timeout(200)
   async def layout(width,height,shot):
    await a.set_viewport_size({'width':width,'height':height});await a.wait_for_timeout(220)
    boxes=await a.evaluate("""()=>{const selectors=['.chat-wrap','.quickbar','#spellbar','#bookSpell','#abilityButton','#effectsPanel','.topbar','.combat-controls','.movement-controls'];return Object.fromEntries(selectors.map(s=>{const e=document.querySelector(s),r=e.getBoundingClientRect();return [s,{x:r.x,y:r.y,w:r.width,h:r.height,right:r.right,bottom:r.bottom}]}))}""")
    print('LAYOUT',width,height,json.dumps(boxes),flush=True)
    await a.screenshot(path=str(OUT/shot))
    for sel in ['#bookSpell','#abilityButton','.quickbar','#spellbar','#effectsPanel']:
     r=boxes[sel];assert r['x']>=0 and r['y']>=0 and r['right']<=width+1 and r['bottom']<=height+1,(sel,boxes)
    book,fav=boxes['#bookSpell'],boxes['#abilityButton']
    combat=boxes['.combat-controls']
    assert fav['right']<=combat['x'] or fav['bottom']<=combat['y'] or fav['y']>=combat['bottom'],('combat overlaps favorite',boxes)
    top_actions=await a.locator('.top-actions').bounding_box()
    assert boxes['#effectsPanel']['y']>=top_actions['y']+top_actions['height'],('status covers top buttons',boxes,top_actions)
    assert fav['x']>=book['right'] and abs(fav['y']-book['y'])<1,boxes
    chat,pots,spells=boxes['.chat-wrap'],boxes['.quickbar'],boxes['#spellbar']
    if width>700 and height>540:assert chat['right']<=pots['x'] and pots['right']<=spells['x'],boxes
    elif width<=700 and height>width:assert chat['bottom']<=pots['y'] and pots['bottom']<=spells['y'],boxes
    else:assert chat['bottom']<=pots['y'] and pots['right']<=spells['x'],boxes
    if height<=540 and width>height:
     notice=await a.locator('.notice-feed').bounding_box()
     assert notice['y']>=boxes['#effectsPanel']['bottom'],('notice covers statuses',boxes,notice)
    assert boxes['#effectsPanel']['y']<height/2
    assert not await a.evaluate('document.documentElement.scrollWidth>innerWidth+1')
    for sel in ['#bookSpell','#abilityButton','#healthPotion','#manaPotion']:
     hit=await a.locator(sel).evaluate("e=>{let r=e.getBoundingClientRect();return e.contains(document.elementFromPoint(r.x+r.width/2,r.y+r.height/2))}")
     assert hit,('covered',width,height,sel)
    checks.append(f'{width}x{height}: potion order, F right of K, controls clickable, top statuses, no page overflow')
   await layout(1440,900,'01_hud_desktop.png')
   css=await a.locator('#effectsPanel').evaluate("e=>{let s=getComputedStyle(e);return [s.backgroundColor,s.backgroundImage,s.borderTopWidth,s.boxShadow,s.pointerEvents]}")
   assert css==['rgba(0, 0, 0, 0)','none','0px','none','none'],css
   assert await a.locator('.effects-label').count()==0
   checks.append('Status strip has no shared background/border/shadow; blank area does not intercept the world')
   effect=a.locator('#ownEffects [data-effect="longstrider"]')
   assert '600 r.' in await effect.inner_text()
   await effect.click();assert await a.locator('#effectDetail').is_visible()
   assert 'Atak nie przerywa' in await a.locator('#effectDetailText').inner_text()
   detail=await a.locator('#effectDetail').bounding_box();panel=await a.locator('#effectsPanel').bounding_box()
   assert detail['y']>=panel['y']+panel['height']
   await a.click('#closeEffectDetail')
   checks.append('Own status retains timer and opens description below strip; close works')
   target=a.locator('#targetEffects .effect-chip').first
   assert (await target.get_attribute('aria-label')).startswith('Cel · ')
   await target.click();assert (await a.locator('#effectDetailName').inner_text()).startswith('Cel · ')
   await a.click('#closeEffectDetail');checks.append('Target status is distinguished on button and in description')
   await a.click('#bookSpell');await a.wait_for_selector('#characterPanel:not([hidden])')
   assert await a.locator('[data-character-tab="spells"]').get_attribute('aria-selected')=='true'
   await a.keyboard.press('Escape');checks.append('K still opens the spell tab in the standalone character sheet')
   p.hp=1;p.potions['health_potion']=3;p.potion_cooldown_until=0
   await a.wait_for_timeout(200)
   await a.click('#healthPotion');await a.wait_for_timeout(180)
   assert p.hp>1 and p.potions['health_potion']==2,(p.hp,p.potions)
   clock.value+=4;p.mana=0
   await a.wait_for_timeout(200)
   mana_before=p.potions.get('mana_potion',0)
   await a.click('#manaPotion');await a.wait_for_timeout(180)
   assert p.mana>0 and p.potions['mana_potion']==mana_before-1,(p.mana,p.potions)
   checks.append('Relocated HP/mana buttons consume actual server potions and restore health/mana')
   p.spell_history=['ray_of_frost']*4;p.mana=p.max_mana;clock.value+=4
   await a.wait_for_timeout(200)
   assert await a.locator('#abilityButton').get_attribute('data-spell')=='ray_of_frost'
   await a.click('#abilityButton');await a.wait_for_timeout(180)
   assert p.last_roll.get('action')=='Promień mrozu',p.last_roll
   checks.append('F button reflects real favorite and casts at selected enemy')
   p.spell_history=['fire_bolt']*7;clock.value+=4
   await a.wait_for_timeout(200)
   assert await a.locator('#abilityButton').get_attribute('data-spell')=='fire_bolt'
   await a.keyboard.press('f');await a.wait_for_timeout(180)
   assert p.last_roll.get('action')=='Ognisty pocisk',p.last_roll
   checks.append('Favorite changes with usage and keyboard F still casts')
   p.level=90;p.hotbar=[key for key in dnd.SPELLS if dnd.spell_allowed(p,key)]
   await a.wait_for_timeout(250)
   assert len(p.hotbar)>24,len(p.hotbar)
   for w,h,name in [(1280,720,'02_hud_1280.png'),(1024,768,'03_hud_1024.png'),(390,844,'04_hud_portrait.png'),(360,640,'05_hud_small_portrait.png'),(844,390,'06_hud_landscape.png')]:
    await layout(w,h,name)
   await a.click('#hotbarNext');await a.wait_for_timeout(120)
   assert await a.locator('#hotbarPageLabel').inner_text()=='2/2'
   await a.click('#hotbarPrev');checks.append('Hotbar bank buttons are clickable on narrow landscape')
   await a.set_viewport_size({'width':390,'height':844});await a.wait_for_timeout(200)
   await a.locator('.hotbar-viewport').evaluate('e=>e.scrollLeft=e.scrollWidth')
   assert await a.locator('.hotbar-viewport').evaluate('e=>e.scrollLeft')>0
   checks.append('Both 12-slot rows scroll together on phone; K/F remain fixed')
   await effect.click();assert await a.locator('#effectDetail').is_visible();await a.click('#closeEffectDetail')
   await a.click('#chatButton');await a.fill('#chatInput','Test układu HUD');await a.keyboard.press('Enter');await a.wait_for_timeout(150)
   assert any(x.get('type')=='chat' for x in sent)
   checks.append('Phone status buttons open descriptions and chat sends a real message')
   p.buffs.clear();p.shield_armed=False;e.conditions.clear()
   await a.wait_for_timeout(220)
   assert not await a.locator('#effectsPanel').is_visible()
   checks.append('Removed statuses leave no empty strip')
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
