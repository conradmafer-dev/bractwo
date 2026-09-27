"""0.8.13: Warrior choices, gear, effects, free features and responsive UI.
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
OUT=ROOT/'docs'/'qa_0.8.13';OUT.mkdir(parents=True,exist_ok=True)

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


   a,p=await new_page('WojownikStart','knight')
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
    from server import combat_rules as rules
    from server.world_content import NPCS
    assert p.armor_class==18 and rules.weapon_dice(p)==(1,8,3)
    assert await a.locator('#fighterChoice').is_visible()
    checks.append('Level-one warrior has actual AC18, sword, shield and a nonblocking style reminder.')
    await a.locator('#fighterChoice button').filter(has_text='Wybierz styl').click();await wait()
    assert await a.locator('.fighter-style').count()==3
    await a.locator('.fighter-style[data-style="dueling"]').click();await wait()
    assert p.fighting_style==''
    await snap('01_style_choice_desktop.png')
    checks.append('Three style tiles; clicking previews without spending any point or changing the character.')
    await a.locator('[data-confirm-style="dueling"]').click();await wait()
    assert p.fighting_style=='dueling' and rules.weapon_dice(p)==(1,8,5)
    assert not await a.locator('#fighterChoice').is_visible()
    assert await a.locator('.fighter-mastery').count()==3
    checks.append('Explicit confirmation enables Dueling, hides reminder and shows three weapon masteries.')
    await a.locator('.fighter-style[data-style="defense"]').click();await wait()
    assert await a.locator('[data-confirm-style="defense"]').is_disabled()
    assert p.fighting_style=='dueling'
    checks.append('Restyling outside a master is disabled; existing style remains selected.')
    await a.locator('[data-character-tab="stats"]').click();await wait()
    assert '1k8+5' in await a.locator('#characterContent').inner_text()
    assert 'Pojedynek' in await a.locator('#characterContent').inner_text()
    checks.append('Character statistics display the actual style, mastery and 1d8+5 weapon damage.')
    await a.locator('[data-character-tab="inventory"]').click();await wait()
    assert await a.locator('.sheet-equipment-card').count()==4
    shield=p.equipment['shield']
    await a.locator('.sheet-equipment-card[data-uid="'+shield+'"]').click();await wait()
    assert 'Tarcza wojownika' in await a.locator('#characterContent').inner_text()
    await snap('02_shield_inventory_desktop.png')
    checks.append('Four independent equipment slots; worn shield is clickable and has a real preview.')
    oldx=p.x;await a.keyboard.down('KeyD');await a.wait_for_timeout(180);await a.keyboard.up('KeyD');await wait()
    assert p.x>oldx
    checks.append('Movement remains possible while the new equipment and feat sheet are open.')
    master=next(n for n in NPCS if n.get('service')=='master');p.x,p.y=master['x'],master['y'];p.combat_until=0
    await a.locator('[data-character-tab="feats"]').click();await wait()
    await a.locator('.fighter-style[data-style="defense"]').click();await wait()
    gold=p.gold;await a.locator('[data-confirm-style="defense"]').click();await wait()
    assert p.fighting_style=='defense' and p.armor_class==19 and p.gold==gold
    checks.append('At a town master, style changes for free and Defense updates actual AC to19.')
    await a.locator('.fighter-style[data-style="great_weapon"]').click();await wait()
    await a.locator('[data-confirm-style="great_weapon"]').click();await wait()
    await a.get_by_role('button',name='Oburącz',exact=True).click();await wait()
    assert p.weapon_grip=='two' and not p.equipment['shield'] and rules.weapon_dice(p)==(1,10,3)
    checks.append('Two-hand versatile grip stows the shield, uses d10 and enables Great Weapon Fighting.')
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await wait(400)
     await a.locator('.fighter-style[data-style="dueling"]').click();await wait()
     assert await a.locator('[data-confirm-style="dueling"]').is_visible()
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
     await snap('03_styles_'+label+'.png')
     checks.append(f'{width}x{height}: style cards and confirmation accessible without horizontal page overflow.')
    await a.set_viewport_size({'width':1440,'height':900});await wait()
    await a.locator('.fighter-style[data-style="dueling"]').click();await wait()
    await a.locator('[data-confirm-style="dueling"]').click();await wait()
    await a.get_by_role('button',name='Jednorącz',exact=True).click();await wait()
    await clear();p.x,p.y=1200,1180;p.hp=1;p.mana=0;p.attack_cooldown_until=0;p.bonus_cooldown_until=0;p.combat_until=clock()+30;await wait()
    await a.keyboard.press('Digit1');await wait()
    assert p.hp==5 and p.mana==0 and p.spell_cooldowns.get('second_wind')==clock()+60,(p.hp,p.mana,p.spell_cooldowns,p.hotbar)
    assert '60 s' in await bar('second_wind')
    checks.append('Second Wind works at zero mana and the hotbar displays its60-second cooldown.')
    await a.keyboard.press('Digit1');await wait();assert p.hp==5
    checks.append('Repeated Second Wind input cannot bypass its cooldown.')
    p.level=5;p.hp=p.max_hp;p.combat_until=0;p.attack_cooldown_until=0;p.bonus_cooldown_until=0;await wait()
    assert await a.locator('#hotbarSlots button[data-spell="action_surge"]').count()==1
    await a.keyboard.press('KeyK');await wait()
    assert '90 s' in await a.locator('.sheet-spell[data-spell="action_surge"]').inner_text()
    await snap('04_level5_features.png')
    checks.append('At level5 Action Surge is unlocked automatically and the book discloses its90-second cooldown.')
    await clear()
    e=Enemy('world_warrior_qa','bandit',p.x+65,p.y,500,p.x+65,p.y);e.ready=100000;g.enemies[e.id]=e;g.reindex_enemy(e)
    p.attack_cooldown_until=clock()+3
    await wait();await a.locator('[data-enemy-id="'+e.id+'"]').click();await wait()
    before=e.hp;ready=p.attack_cooldown_until
    await a.keyboard.press('Digit2');await wait(180)
    assert e.hp<before and p.attack_cooldown_until==ready and p.spell_cooldowns['action_surge']==clock()+90
    assert 'sap' in e.conditions
    await snap('05_surge_sap_effect.png')
    checks.append('Action Surge hits during main-action cooldown without resetting it; Sap appears on the target.')
    assert await a.locator('#targetEffects [data-effect="sap"]').count()==1
    await a.locator('#targetEffects [data-effect="sap"]').click();await wait()
    assert 'Osłabienie' in await a.locator('#effectDetail').inner_text()
    checks.append('Weapon mastery status is clickable and explains its effect.')
    await clear();await g.select_combat_target(p,{})
    # Create the maul and expose its actual inventory preview, rather than spoofing UI data.
    maul=make_item('training_maul');p.inventory.append(maul);p.equipment['weapon']=maul['uid'];p.equipment['shield']='';p.combat_until=0;p.attack_cooldown_until=clock()+100
    await wait();await a.keyboard.press('KeyC');await wait();await a.locator('[data-character-tab="feats"]').click();await wait()
    assert 'Młot dwuręczny' in await a.locator('.fighter-mastery.active').inner_text()
    assert not p.fighting_style=='great_weapon'
    checks.append('Changing weapon changes active mastery but does not automatically change the fighting style.')
    b,q=await new_page('DruidBezStylu','druid');await b.keyboard.press('KeyC');await wait();await b.locator('[data-character-tab="feats"]').click();await wait()
    assert await b.locator('.fighter-style').count()==0 and not await b.locator('#fighterChoice').is_visible()
    checks.append('Druid receives no warrior choice, items or mastery interface.')
    assert not errors,errors
    checks.append('No JavaScript exceptions during choices, combat, movement, effects and responsive rendering.')
    (OUT/'results.json').write_text(json.dumps({'checks':checks,'errors':errors,'connection':'controlled Python WebSocket bridge to real aiohttp server','monster_ai':'paused; real server handlers; deterministic clock and dice'},ensure_ascii=False,indent=2))
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
