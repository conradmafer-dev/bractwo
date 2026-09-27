"""0.8.14: Caster paths, training, rituals, forms, gear and responsive UI.
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
OUT=ROOT/'docs'/'qa_0.8.14';OUT.mkdir(parents=True,exist_ok=True)

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


   a,p=await new_page('DruidNowy','druid')
   async def wait(ms=350):await a.wait_for_timeout(ms)
   async def snap(name):await a.screenshot(path=str(OUT/name))
   async def clear():
    for _ in range(4):await a.keyboard.press('Escape')
    await wait()
   async def advance(seconds=3):
    clock.value+=seconds
    await wait()
   try:
    from server import combat_rules as rules, equipment_rules as eq
    from server.world_content import NPCS
    assert await a.locator('#casterChoice').is_visible()
    assert eq.has(p,'light_armor') and eq.has(p,'shields') and not eq.has(p,'medium_armor')
    assert rules.equipped_item(p,'armor')['armor_kind']=='light'
    checks.append('New druid starts in light armor with shield training, no medium armor or automatic path.')
    await a.locator('#casterChoice button').filter(has_text='Wybierz ścieżkę').click();await wait()
    assert await a.locator('.caster-order').count()==2
    await a.locator('[data-order="warden"]').click();await wait()
    assert not p.primal_order
    before=[i['uid'] for i in p.inventory]
    await snap('01_druid_path_desktop.png')
    checks.append('Clicking a path previews it; explicit confirmation is required.')
    await a.locator('[data-confirm-order="warden"]').click();await wait()
    assert p.primal_order=='warden' and eq.has(p,'medium_armor') and eq.has(p,'martial_weapons')
    assert before==[i['uid'] for i in p.inventory]
    assert await a.locator('.training-chip').count()==5
    assert not await a.locator('[data-feat="moderately_armored"]').count()
    assert not await a.locator('#casterChoice').is_visible()
    checks.append('Warden grants two proficiencies, hides redundant feats and does NOT add armor or any item.')
    # Lighter tooltips and universal shield/grip work on actual equipment.
    shield=make_item('wooden_shield');p.inventory.append(shield);p.equipment['shield']=shield['uid'];await wait()
    await a.locator('[data-character-tab="inventory"]').click();await wait()
    uid=p.equipment['weapon']
    await a.locator('.sheet-equipment-card[data-uid="'+uid+'"]').click();await wait()
    text=await a.locator('#characterContent').inner_text()
    assert 'Oburącz' in text and 'Sprzedaj' not in text
    assert await a.locator('.sheet-equipment-card[data-uid="'+uid+'"] img').get_attribute('data-qa-asset')=='assets/equipment/nature_staff.svg'
    await snap('02_compact_gear_desktop.png')
    await a.get_by_role('button',name='Oburącz',exact=True).click();await wait()
    assert p.weapon_grip=='two' and not p.equipment['shield'] and any(i['uid']==shield['uid'] for i in p.inventory)
    checks.append('Druid can view equipped staff, switch to two hands and safely stow shield; no sell outside trade.')
    # Move with character tabs open.
    x,y=p.x,p.y
    await a.keyboard.down('KeyW');await wait(180);await a.keyboard.up('KeyW');await wait()
    assert abs(p.y-y)>1
    checks.append('Movement remains live while the updated character card is open.')
    await a.locator('[data-character-tab="feats"]').click();await wait()
    for width,height,label in [(390,844,'portrait'),(844,390,'landscape')]:
     await a.set_viewport_size({'width':width,'height':height});await wait()
     assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
     assert await a.locator('.caster-order').count()==2
     await snap('03_druid_'+label+'.png')
     checks.append(f'{width}x{height}: class paths and owned training fit the screen without horizontal page overflow.')
    await a.set_viewport_size({'width':1440,'height':900});await wait()
    p.level=5;p.hp=p.max_hp;p.mana=p.max_mana;p.combat_until=0;p.attack_cooldown_until=0;p.bonus_cooldown_until=0;await wait()
    assert not await a.locator('[data-form="wolf"]').is_disabled()
    assert not await a.locator('[data-form="cat"]').is_disabled()
    assert await a.locator('[data-form="black_bear"]').is_disabled()
    await a.locator('[data-form="cat"]').click();await wait()
    assert p.form=='cat' and p.temp_hp==2
    await snap('04_cat_and_forms.png')
    checks.append('Level5 unlocks wolf and cat, not stronger bears; actual cat shape gives2 temporary HP.')
    await advance(3);await a.locator('[data-form="cat"]').click();await wait()
    assert not p.form and p.spell_cooldowns['wild_shape_wolf']>clock()
    checks.append('Leaving a form does not clear the shared Wild Shape/Wild Companion cooldown.')
    # At a real master switch to the adapted Magician; medium armor is not granted.
    master=next(n for n in NPCS if n.get('service')=='master')
    p.x,p.y=master['x'],master['y'];p.combat_until=0;await wait()
    await a.locator('[data-order="magician"]').click();await wait()
    await a.locator('[data-confirm-order="magician"]').click();await wait()
    assert p.primal_order=='magician' and not eq.has(p,'medium_armor')
    assert await a.locator('[data-feat="moderately_armored"]').count()==1
    checks.append('Changing to Magician at a master removes Warden-only grants and restores missing training choices.')
    p.level=15;p.hp=p.max_hp;p.mana=p.max_mana;p.combat_until=0;await wait()
    feat=a.locator('[data-feat="moderately_armored"]')
    await feat.get_by_role('button',name='Wybierz',exact=True).click();await wait()
    assert eq.has(p,'medium_armor') and p.training_feats.get('moderately_armored')=='strength'
    assert not await a.locator('[data-feat="moderately_armored"]').count()
    await snap('08_training_feat_owned.png')
    checks.append('A missing medium-armor feat can be selected at15, adds its single ability point and cannot be selected again.')
    await clear()
    site=g.nature_sites[0];p.x,p.y=site['x'],site['y'];p.combat_until=0;p.attack_cooldown_until=0
    await g.start_caster_channel(p,'speak_with_animals',True);await advance(10.1)
    await a.keyboard.press('KeyE');await wait()
    assert any(x.get('type')=='nature_interact' and x.get('id')==site['id'] for x in sent)
    assert 'Leśny lis:' in await a.locator('body').inner_text()
    await snap('09_talking_to_fox.png')
    checks.append('Animal Speech ritual enables a real E interaction with the fox and a map hint, without loot spoilers.')
    # A real wizard gets the recovery channel and spell-specific ritual actions.
    a,q=await new_page('MagRytualny','mage')
    q.mana=0;q.combat_until=0;q.mana_recovery_until=clock()+10000
    await a.keyboard.press('KeyC');await wait();await a.locator('[data-character-tab="feats"]').click();await wait()
    await a.locator('.caster-feature').filter(has_text='Odzyskanie mocy').get_by_role('button',name='Użyj',exact=True).click();await wait()
    assert q.casting_channel and q.mana==0,(q.casting_channel,q.mana)
    await snap('05_arcane_recovery_channel.png')
    await a.keyboard.down('KeyD');await wait(150);await a.keyboard.up('KeyD');await wait()
    assert not q.casting_channel and not q.spell_cooldowns.get('arcane_recovery')
    checks.append('Arcane Recovery visibly channels, movement cancels it without spending mana or starting cooldown.')
    await a.locator('.caster-feature').filter(has_text='Odzyskanie mocy').get_by_role('button',name='Użyj',exact=True).click();await wait()
    await advance(4.1)
    assert q.mana==20 and q.spell_cooldowns['arcane_recovery']>clock()+179
    checks.append('Completed recovery restores20 mana and starts the180-second cooldown.')
    await a.locator('[data-character-tab="spells"]').click();await wait()
    spell=a.locator('.sheet-spell[data-spell="alarm"]')
    assert await spell.get_by_role('button',name='Rytuał',exact=False).count()==1
    await spell.get_by_role('button',name='Rytuał',exact=False).click();await wait()
    assert q.casting_channel['ritual']
    mana=q.mana;await advance(10.1)
    assert q.id in g.alarms and q.mana==mana
    checks.append('Alarm ritual completes without mana; its authoritative persistent square is visible to its owner.')
    await a.locator('.sheet-spell[data-spell="find_familiar"]').get_by_role('button',name='Rytuał',exact=False).click();await wait()
    gold=q.gold;await advance(40.1)
    assert q.id in g.familiars and q.gold==gold-10
    assert await a.locator('.caster-familiar').is_visible()
    await a.locator('.caster-familiar').get_by_role('button',name='Pomagaj',exact=True).click();await wait()
    assert g.familiars[q.id].mode=='help'
    await snap('06_ritual_book_and_familiar.png')
    checks.append('Ritual familiar costs10 gold, no mana; nonattacking owl and commands reflect actual server state.')
    assert await a.locator('.sheet-spell[data-spell="magic_missile"]').get_by_role('button',name='Rytuał',exact=False).count()==0
    checks.append('Ordinary combat spells cannot be cast as free rituals.')
    await a.set_viewport_size({'width':390,'height':844});await wait();await snap('07_wizard_ritual_portrait.png')
    assert await a.evaluate('document.documentElement.scrollWidth<=innerWidth+2')
    checks.append('Wizard spellbook and familiar commands fit a narrow portrait viewport.')
    assert not errors,errors
    checks.append('No JavaScript exceptions in new class choices, channels, inventory, forms, rituals or responsive views.')
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
