"""Known working transport fallback: real server WS, embedded production client."""
import asyncio
import base64
import json
import re
from collections import deque
from hashlib import sha256
from pathlib import Path
from aiohttp import ClientSession, WSMsgType

ROOT = Path(__file__).resolve().parents[1]


class Bridge:
    def __init__(self, base):
        self.base = base
        self.session = ClientSession()
        self.sockets = []
        self.tasks = []
        self.closing = False
        self.max_queue = 0
        self.source_hashes = {str(path.relative_to(ROOT)).replace('\\','/'):sha256(path.read_bytes()).hexdigest()
                              for path in (ROOT/'web').iterdir() if path.suffix in ('.js','.css','.html','.webmanifest')}
        original = (ROOT / 'tools/browser_0817_wand.py').read_text(encoding='utf-8')
        bridge = re.search("BRIDGE='''(.*?)'''", original, re.S).group(1).split('window.__storage={};')[0]
        assets = {str(path.relative_to(ROOT / 'web')).replace('\\', '/'):
                  'data:' + ('image/png' if path.suffix == '.png' else 'image/svg+xml') + ';base64,' + base64.b64encode(path.read_bytes()).decode()
                  for directory in ('assets', 'icons') for path in (ROOT / 'web' / directory).rglob('*') if path.suffix in ('.png', '.svg')}
        image_bridge = "window.__qaAssets=" + json.dumps(assets) + ";const srcDesc=Object.getOwnPropertyDescriptor(HTMLImageElement.prototype,'src');Object.defineProperty(HTMLImageElement.prototype,'src',{get:srcDesc.get,set(v){srcDesc.set.call(this,window.__qaAssets[v]||v);}});"
        html = (ROOT / 'web/index.html').read_text(encoding='utf-8')
        html = re.sub(r'<link rel="stylesheet" href="([^"]+)">', lambda m: '<style>'+(ROOT/'web'/m[1]).read_text(encoding='utf-8')+'</style>', html)
        html = re.sub(r'<script src="([^"]+)"></script>', lambda m: '<script>'+((bridge+image_bridge) if m[1]=='runtime.js' else '')+(ROOT/'web'/m[1]).read_text(encoding='utf-8')+'</script>', html)
        self.html = re.sub(r"url\(['\"]?(assets/[^)'\"\s]+)['\"]?\)", lambda m: 'url("'+assets.get(m[1],m[1])+'")', html)

    async def load(self, page):
        sockets = {}
        async def emit(sid, kind, data=None):
            if self.closing or page.is_closed():
                return
            try:
                await page.evaluate('([sid,kind,data])=>window.__deliver(sid,kind,data)', [sid,kind,data])
            except Exception:
                pass
        async def pump(sid, ws):
            # Keep aiohttp receive running while Chromium renders: receive also
            # answers the real server's heartbeat pings. Serial page.evaluate
            # inside this loop caused false disconnections on a memory-starved host.
            pending = deque()
            wake = asyncio.Event()
            finished = False
            async def deliver():
                while not self.closing and not page.is_closed():
                    await wake.wait()
                    while pending:
                        kind, data = pending.popleft()
                        await emit(sid,kind,data)
                    wake.clear()
                    if finished:
                        return
            delivery = asyncio.create_task(deliver())
            self.tasks.append(delivery)
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    pending.append(('message',msg.data))
                    self.max_queue = max(self.max_queue,len(pending))
                    wake.set()
            finished = True
            pending.append(('close',None))
            wake.set()
        async def open_ws(sid, url):
            ws = await self.session.ws_connect(self.base+'/ws')
            sockets[sid] = ws
            self.sockets.append(ws)
            await emit(sid,'open')
            self.tasks.append(asyncio.create_task(pump(sid,ws)))
        async def send_ws(sid, data):
            if sid in sockets and not sockets[sid].closed:
                await sockets[sid].send_str(data)
        async def close_ws(sid):
            if sid in sockets:
                await sockets[sid].close()
        await page.expose_function('__wsOpen',open_ws)
        await page.expose_function('__wsSend',send_ws)
        await page.expose_function('__wsClose',close_ws)
        await page.route('http://bractwo.local/',lambda route: route.fulfill(status=200,content_type='text/html; charset=utf-8',body=self.html))
        await page.goto('http://bractwo.local/',wait_until='load',timeout=120000)
        await page.evaluate("url=>document.getElementById('serverInput').value=url",self.base.replace('http:','ws:')+'/ws')

    async def close(self):
        self.closing = True
        for ws in self.sockets:
            if not ws.closed:
                await ws.close()
        for task in self.tasks:
            task.cancel()
        await asyncio.gather(*self.tasks,return_exceptions=True)
        await self.session.close()
