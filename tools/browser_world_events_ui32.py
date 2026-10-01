"""Local Chromium + real Game/on_packet WebSocket event integration.

A loopback-only test login replaces Google. No production accounts or saves.
Public comments/gallery/auth are outside this test. Game JS and event handlers
are loaded unchanged; only the unrelated login script is replaced by a fixture.
"""
import asyncio,base64,contextlib,json,os,re,sys,time,traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT),str(ROOT/'tests')]
# The old FULL_SOURCE upload does not contain the independent GitHub comments
# module. This optional test-only shim is never installed as a production module.
if os.environ.get('BRACTWO_QA_COMMENTS_SHIM')=='1':
    import types
    sys.modules.setdefault('server.comments',types.ModuleType('server.comments'))
from aiohttp import web,WSMsgType,ClientSession
from playwright.async_api import async_playwright
from server.server import Game,Player
from server import inventory_rules
import test_dnd as base
OUT=Path(os.environ.get('BRACTWO_QA_OUT',str(ROOT/'docs/qa_ui32')));OUT.mkdir(parents=True,exist_ok=True)
report={'ok':False,'checks':[],'page_errors':[],'server_errors':[], 'limitations':[
 'Loopback test login and an in-memory SQLite database; no Google or Railway requests.',
 'The complete game client uses an in-process browser binding to a real Python loopback WebSocket; event packets enter unchanged Game.on_packet.',
 'Browser URL navigation is blocked by the environment. HTML, CSS, scripts and images are injected from the local workspace; browser security policies are unchanged.',
 'Hostile monsters are disabled in this UI test, separate from server tests of combat restrictions.',
 'No physical Android device. Public comments, SEO and unrelated gallery assets are not under test.']}
def save(): (OUT/'browser_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
def record(name,**data):print(name,data,flush=True);report['checks'].append({'name':name,**data});save()

async def load_game(page, port, scene):
    """Offline browser fixture; no browser navigation or policy modifications."""
    html=(ROOT/'web/index.html').read_text()
    scripts=re.findall(r'<script[^>]* src=["\']([^"\']+)["\'][^>]*></script>',html)
    html=re.sub(r'<script\b[^>]*>.*?</script>','',html,flags=re.S)
    styles=[]
    for name in re.findall(r'<link[^>]*rel="stylesheet"[^>]*href="([^"]+)"[^>]*>',html):
        path=ROOT/'web'/name.lstrip('/')
        if path.is_file():styles.append(path.read_text())
    html=re.sub(r'<link\b[^>]*>','',html)
    html=html.replace('</head>','<style>'+''.join(styles)+'</style></head>')
    images={}
    for asset in (ROOT/'web/assets').rglob('*.svg'):
        key=asset.relative_to(ROOT/'web').as_posix()
        images[key]='data:image/svg+xml;base64,'+base64.b64encode(asset.read_bytes()).decode()
    html=re.sub(r'<img\b[^>]*>',lambda m:re.sub(r'src="([^"]+)"',lambda n:'src="'+images.get(n[1].lstrip('/'),'data:,')+'"',m[0]),html)
    await page.set_content(html,wait_until='domcontentloaded')
    await page.evaluate(r"""images=>{const desc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,'src');Object.defineProperty(HTMLImageElement.prototype,'src',{get:desc.get,set(value){desc.set.call(this,images[String(value).replace(/^\//,'')]||value);}});const data=new Map();Object.defineProperty(window,'localStorage',{value:{getItem:k=>data.get(k)||null,setItem:(k,v)=>data.set(k,String(v)),removeItem:k=>data.delete(k)}});window.fetch=async()=>({ok:true,json:async()=>({})});}""",images)
    session=ClientSession();sockets={};tasks=[]
    async def wire(source,op,num,payload=None):
        if op=='open':
            ws=await session.ws_connect(f'http://127.0.0.1:{port}/ws');sockets[num]=ws
            await page.evaluate('num=>window.__sockets.get(num)._emit("open")',num)
            async def read():
                try:
                    async for msg in ws:
                        if page.is_closed():break
                        if msg.type==WSMsgType.TEXT:await page.evaluate('([num,data])=>window.__sockets.get(num)?._emit("message",data)',[num,msg.data])
                except Exception:
                    if not page.is_closed():raise
            tasks.append(asyncio.create_task(read()))
        elif op=='send':await sockets[num].send_str(payload)
        elif op=='close':
            if num in sockets:await sockets[num].close()
    await page.expose_binding('__ui32Wire',wire)
    await page.add_script_tag(content="""window.__sockets=new Map();window.WebSocket=class extends EventTarget{static CONNECTING=0;static OPEN=1;static CLOSING=2;static CLOSED=3;constructor(url){super();this.readyState=0;this.id=window.__sockets.size+1;window.__sockets.set(this.id,this);window.__ui32Wire('open',this.id);}send(data){window.__ui32Wire('send',this.id,data);}close(){this.readyState=3;window.__ui32Wire('close',this.id);} _emit(kind,data){if(kind==='open')this.readyState=1;this.dispatchEvent(kind==='message'?new MessageEvent('message',{data}):new Event(kind));}};""")
    fixture="globalThis.BractwoGoogleAuth={sameOriginServer:()=>true,mount(h){setTimeout(()=>h.connect({type:'hello_google',ticket:'ui32-local-test',site:"+json.dumps(scene)+"}),80);return {setBusy(){},success(){},logout(){},connectionError(){}}}};"
    for name in scripts:
        if name.endswith('google_auth.js'):await page.add_script_tag(content=fixture)
        elif not name.endswith('comments.js'):
            path=ROOT/'web'/name.lstrip('/')
            if path.is_file():await page.add_script_tag(content=path.read_text())
    async def cleanup():
        print('cleanup: page',flush=True)
        await page.close()
        print('cleanup: tasks',flush=True)
        for task in tasks:
            task.cancel()
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError,asyncio.TimeoutError):await asyncio.wait_for(task,2)
        print('cleanup: sockets',flush=True)
        for ws in sockets.values():
            with contextlib.suppress(asyncio.TimeoutError):await asyncio.wait_for(ws.close(),1)
        await session.close()
        print('cleanup: done',flush=True)
    return cleanup

async def main():
    game=Game(':memory:');game.combat_rng=base.Dice(20,4)
    for e in game.enemies.values():e.alive=False;e.respawn_at=10**12
    game.legacy_enemies=[]
    clients={};serial=0
    async def asset(request):
        path=request.match_info.get('path','') or 'index.html'
        if path=='google_auth.js':
            return web.Response(content_type='application/javascript',text='''globalThis.BractwoGoogleAuth={sameOriginServer:()=>true,mount(h){setTimeout(()=>h.connect({type:'hello_google',ticket:'ui32-local-test',site:new URLSearchParams(location.search).get('site')||'scout_first_aid'}),80);return {setBusy(){},success(){},logout(){},connectionError(){}}}};''')
        if path=='comments.js':return web.Response(text='',content_type='application/javascript')
        if path=='comments.css':return web.Response(text='',content_type='text/css')
        resolved=(ROOT/'web'/path).resolve()
        if not resolved.is_relative_to((ROOT/'web').resolve()) or not resolved.is_file():raise web.HTTPNotFound()
        return web.FileResponse(resolved,headers={'Cache-Control':'no-store'})
    async def websocket(request):
        nonlocal serial
        ws=web.WebSocketResponse();await ws.prepare(request);p=None
        try:
            async for msg in ws:
                if msg.type!=WSMsgType.TEXT:continue
                data=json.loads(msg.data)
                if data.get('type')=='hello_google':
                    if data.get('ticket')!='ui32-local-test':await ws.close();break
                    site=game.skill_challenge_sites().get(data.get('site'))
                    if site is None:await ws.close();break
                    serial+=1;p=Player(str(serial),'Wędrowiec',ws,class_id='ranger',level=20,x=site['x'],y=site['y']+75,gold=100)
                    game.starter(p);p.hp=p.max_hp;p.mana=p.max_mana;p.origin_feat='alert';p.current_wall_time=game.now()
                    p.pending_level_ups=[];game.players[p.id]=p;clients[p.id]=p
                    game.db.execute('INSERT INTO accounts VALUES(?,?,?,?,?,?)',(int(p.id),p.name,p.name+str(serial),b'qa',b'qa',json.dumps(p.save_data())));game.db.commit()
                    metadata=game.metadata();metadata['spawn']={'x':p.x,'y':p.y}
                    await ws.send_json({'type':'welcome','id':p.id,'world':metadata,'owner_deltas':False});await ws.send_json(game.snapshot(p))
                elif p is not None:
                    await game.on_packet(ws,data)
        except Exception:
            report['server_errors'].append(traceback.format_exc());save()
        finally:
            if p:game.players.pop(p.id,None)
        return ws
    async def peek(request):
        return web.json_response({k:{'x':p.x,'y':p.y,'hp':p.hp,'mana':p.mana,'gold':p.gold,'count':inventory_rules.count(p,'health_potion'),'progress':p.skill_progress} for k,p in clients.items()})
    app=web.Application();app.router.add_get('/ws',websocket);app.router.add_get('/qa/state',peek)
    app.router.add_get('/ranking',lambda r:web.json_response(game.ranking()));app.router.add_get('/{path:.*}',asset)
    runner=web.AppRunner(app);await runner.setup();site=web.TCPSite(runner,'127.0.0.1',0);await site.start();port=site._server.sockets[0].getsockname()[1]
    async def ticks():
        while True:
            game.step(.1)
            await game.broadcast_states();await asyncio.sleep(.1)
    task=asyncio.create_task(ticks())
    try:
        async with async_playwright() as pw:
            browser=await pw.chromium.launch(executable_path=os.environ.get('CHROMIUM_BIN','/usr/bin/chromium'),headless=True,args=['--no-sandbox'])
            report['chromium']=browser.version
            for w,h,touch in [(1440,900,False),(390,844,True),(320,568,True),(844,390,True)]:
                print('next viewport',w,h,flush=True)
                ctx=await browser.new_context(viewport={'width':w,'height':h},has_touch=touch,is_mobile=touch)
                page=await ctx.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                cleanup=await load_game(page,port,'scout_first_aid')
                await page.locator('#gameUI').wait_for(state='visible');await page.wait_for_timeout(1000)
                # Dismiss unrelated pre-existing level/feat prompts for the screenshot.
                for sel in ['[data-advancement-dismiss]','.fighter-choice button:last-child','.caster-choice button:last-child']:
                    loc=page.locator(sel)
                    if await loc.count() and await loc.first.is_visible():
                        with contextlib.suppress(Exception):await loc.first.click(timeout=300)
                await page.screenshot(path=str(OUT/f'guard-world-{w}x{h}.png'))
                await page.locator('#interactButton').click();await page.locator('#worldEventPanel').wait_for(state='visible')
                assert await page.locator('#worldEventTitle').inner_text()=='Ranny strażnik'
                assert await page.locator('[data-event-action]').count()==3
                assert await page.locator('.world-event-close').evaluate('(e)=>{const r=e.getBoundingClientRect();return e===document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);}'), 'Another HUD control covers the event close button'
                # A moving snapshot must not repeatedly replace a stationary button.
                identity=await page.locator('[data-event-action="potion"]').evaluate('(e)=>{window.__sameEventButton=e;return true}')
                await page.wait_for_timeout(450)
                assert await page.evaluate('window.__sameEventButton===document.querySelector("[data-event-action=potion]")')
                layout=await page.locator('#worldEventPanel').evaluate('''e=>{const r=e.getBoundingClientRect();return {left:r.left,top:r.top,right:r.right,bottom:r.bottom,overflow:e.querySelector('.world-event-body').scrollWidth-e.querySelector('.world-event-body').clientWidth}}''')
                assert layout['left']>=0 and layout['top']>=0 and layout['right']<=w+1 and layout['bottom']<=h+1 and layout['overflow']<=1,layout
                await page.screenshot(path=str(OUT/f'guard-dialogue-{w}x{h}.png'));record('dialogue, stable button, viewport',width=w,height=h,geometry=layout)
                state_before=await (await page.request.get(f'http://127.0.0.1:{port}/qa/state')).json();pid=str(serial);before=state_before[pid]
                # Reading/opening/cancelling cannot consume a potion.
                await page.locator('.world-event-close').click();await page.locator('#interactButton').click()
                state_read=await (await page.request.get(f'http://127.0.0.1:{port}/qa/state')).json()
                assert state_read[pid]['count']==before['count']
                await page.locator('[data-event-action="potion"]').click();await page.locator('.world-event-result').wait_for(state='visible')
                after=(await (await page.request.get(f'http://127.0.0.1:{port}/qa/state')).json())[pid]
                assert after['count']==before['count']-1 and after['gold']==before['gold']+25 and after['hp']==before['hp']
                assert 'scout_first_aid' in after['progress']['completed']
                assert await page.locator('[data-event-action]').count()==0
                assert await page.locator('.world-event-description').count()==0
                await page.screenshot(path=str(OUT/f'guard-complete-{w}x{h}.png'));record('potion real WebSocket and completion',width=w,height=h)
                await page.keyboard.press('Escape');assert not await page.locator('#worldEventPanel').is_visible()
                await page.locator('#interactButton').click();assert await page.locator('.world-event-result').is_visible()
                after_reopen=(await (await page.request.get(f'http://127.0.0.1:{port}/qa/state')).json())[pid]
                assert after_reopen['gold']==after['gold'];record('reopen completed scene, no duplicate reward',width=w,height=h)
                await cleanup()
            # Every authored scene opens from the actual game client; all check
            # choices are covered by the deterministic server integration suite.
            for key in game.skill_challenge_sites():
                ctx=await browser.new_context(viewport={'width':1280,'height':800});page=await ctx.new_page();page.set_default_timeout(10000);page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
                cleanup=await load_game(page,port,key);await page.locator('#gameUI').wait_for(state='visible');await page.wait_for_timeout(500)
                await page.keyboard.press('KeyE');await page.locator('#worldEventPanel').wait_for(state='visible');assert await page.locator('#worldEventTitle').inner_text()==game.skill_challenge_sites()[key]['name']
                await page.screenshot(path=str(OUT/f'{key}-1280x800.png'));record('E opens real scene',scene=key)
                if key=='scout_first_aid':
                    await page.locator('[data-event-action="heal"]').click();await page.locator('.world-event-result').wait_for(state='visible');assert await page.locator('.world-event-roll').is_visible();record('healing spell receipt in dialogue')
                if key=='mill_tangled_pouch':
                    await page.locator('[data-event-action="lift"]').click();await page.locator('.world-event-result').wait_for(state='visible');assert '1k20' in await page.locator('.world-event-roll').inner_text();record('skill check receipt in dialogue')
                await cleanup()
            report['ok']=not report['page_errors'] and not report['server_errors'];save()
            await browser.close()
        assert not report['page_errors'],report['page_errors'];assert not report['server_errors'],report['server_errors']
        report['ok']=True;save()
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):await task
        await runner.cleanup();game.db.close();save()
if __name__=='__main__':asyncio.run(main())
