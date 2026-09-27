"""Real local TCP/WebSocket + process restart check. Uses a temporary database only."""
from __future__ import annotations
import asyncio
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time

import aiohttp

ROOT = Path(__file__).resolve().parents[1]
checks: list[str] = []


def check(ok: bool, label: str) -> None:
    if not ok:
        raise AssertionError(label)
    checks.append(label)
    print('PASS:', label, flush=True)


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


async def packet(ws, kind: str, predicate=None):
    async with asyncio.timeout(12):
        while True:
            msg = await ws.receive()
            if msg.type != aiohttp.WSMsgType.TEXT:
                raise AssertionError(f'Unexpected WebSocket state: {msg.type}')
            data = json.loads(msg.data)
            if data.get('type') == 'error':
                raise AssertionError(data)
            if data.get('type') == kind and (predicate is None or predicate(data)):
                return data


async def auth(session, base, name, password, create, cls):
    ws = await session.ws_connect(base + '/ws', max_msg_size=16 * 1024 * 1024)
    await ws.send_json({'type': 'hello', 'name': name, 'password': password,
                       'create': create, 'class_id': cls, 'compact_state': False})
    welcome = await packet(ws, 'welcome')
    state = await packet(ws, 'state')
    return ws, welcome, state


async def await_health(session, base, proc):
    for _ in range(100):
        if proc.poll() is not None:
            raise AssertionError('Server exited during startup')
        try:
            async with session.get(base + '/health') as resp:
                if resp.status == 200:
                    return await resp.json()
        except aiohttp.ClientError:
            pass
        await asyncio.sleep(.1)
    raise AssertionError('Server failed healthcheck')


async def close_for_restart(ws):
    async with asyncio.timeout(12):
        while not ws.closed:
            msg = await ws.receive()
            if msg.type in (aiohttp.WSMsgType.CLOSE, aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSING):
                break
        await ws.close()


def owner(state, pid):
    return next(p for p in state['players'] if str(p['id']) == str(pid))


async def main():
    processes = []
    with tempfile.TemporaryDirectory(prefix='bractwo-railway-qa-') as temporary:
        tmp = Path(temporary)
        database = tmp / 'world.sqlite3'
        env = {k: v for k, v in os.environ.items() if not k.startswith('RAILWAY_')}
        env.update({'RAILWAY_SERVICE_ID': 'local-qa', 'RAILWAY_VOLUME_MOUNT_PATH': str(tmp),
                    'BRACTWO_DB_PATH': str(database), 'PYTHONUNBUFFERED': '1'})
        log = (tmp / 'server.log').open('w')
        password = secrets.token_urlsafe(16)
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as session:
                env['PORT'] = str(free_port())
                base = 'http://127.0.0.1:' + env['PORT']
                proc = subprocess.Popen([sys.executable, 'run.py'], cwd=ROOT, env=env,
                                        stdout=log, stderr=subprocess.STDOUT)
                processes.append(proc)
                health = await await_health(session, base, proc)
                check(health.get('version') == '0.8.17' and health.get('ok'), 'HTTP health reports Bractwo 0.8.17')
                for file in sorted((ROOT / 'web').rglob('*')):
                    if file.is_file():
                        route = '/' + file.relative_to(ROOT / 'web').as_posix()
                        if route == '/index.html': route = '/'
                        async with session.get(base + route) as resp:
                            assert resp.status == 200, route
                            assert await resp.read() == file.read_bytes(), route
                check(True, 'All shipped web files and icons served byte-for-byte')
                for route in ('/data/world.sqlite3', '/backups/world.sqlite3', '/server/server.py'):
                    async with session.get(base + route) as resp:
                        assert resp.status == 404, route
                check(True, 'Save files and server source are not served over HTTP')
                ws1, welcome1, state1 = await auth(session, base, 'HostingMageQA', password, True, 'mage')
                pid1 = str(welcome1['id'])
                check(owner(state1, pid1)['class_id'] == 'mage', 'Register and enter as wizard using native WebSocket')
                ws2, welcome2, state2 = await auth(session, base, 'HostingDruidQA', password, True, 'druid')
                pid2 = str(welcome2['id'])
                check(len(state2['players']) == 2, 'Two separate clients share the same world')
                await ws1.send_json({'type': 'cast', 'spell_id': 'longstrider'})
                await packet(ws1, 'state', lambda s: owner(s, pid1).get('favorite_spell') == 'longstrider')
                check(True, 'Server executes an actual first-circle spell')
                await ws1.send_json({'type': 'cast', 'spell_id': 'arcane_recovery'})
                recovery_state = await packet(ws1, 'state', lambda s: owner(s, pid1).get('spell_cooldowns', {}).get('arcane_recovery', 0) > 0)
                recovered = owner(recovery_state, pid1)
                check(recovered['mana'] == recovered['max_mana'] and not recovered['character_sheet']['caster']['channel'],
                      'Native WebSocket Recovery restores20 mana immediately without channeling')
                await ws1.send_json({'type': 'hotbar', 'slot': 0, 'spell_id': 'longstrider'})
                await packet(ws1, 'state', lambda s: owner(s, pid1)['hotbar'][0] == 'longstrider')
                check(True, 'Hotbar update round-trips through the real game server')
                started = time.monotonic()
                proc.send_signal(signal.SIGTERM)
                await asyncio.gather(close_for_restart(ws1), close_for_restart(ws2))
                code = await asyncio.to_thread(proc.wait, 15)
                check(code == 0 and time.monotonic() - started < 15,
                      'SIGTERM closes connected clients and exits cleanly within draining budget')
                with closing(sqlite3.connect(database)) as conn:
                    check(conn.execute('PRAGMA integrity_check').fetchone() == ('ok',), 'SQLite integrity check after shutdown')
                    saved = json.loads(conn.execute('SELECT data FROM accounts WHERE id=?', (pid1,)).fetchone()[0])
                    check(saved['hotbar'][0] == 'longstrider' and saved['spell_history'][-1] == 'arcane_recovery',
                          'Last hotbar change and actual spell history persist on shutdown')
                env['PORT'] = str(free_port())
                base = 'http://127.0.0.1:' + env['PORT']
                proc2 = subprocess.Popen([sys.executable, 'run.py'], cwd=ROOT, env=env,
                                         stdout=log, stderr=subprocess.STDOUT)
                processes.append(proc2)
                await await_health(session, base, proc2)
                backups = list((tmp / 'backups').glob('bractwo-*.sqlite3'))
                check(len(backups) == 1, 'Restart snapshots the existing save before opening the game')
                with closing(sqlite3.connect(backups[0])) as conn:
                    check(conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0] == 2,
                          'Pre-start backup includes both accounts')
                ws3, welcome3, state3 = await auth(session, base, 'HostingMageQA', password, False, 'mage')
                check(str(welcome3['id']) == pid1 and owner(state3, pid1)['hotbar'][0] == 'longstrider',
                      'Same account logs in after process restart with its saved settings')
                remaining = owner(state3, pid1).get('spell_cooldowns', {}).get('arcane_recovery', 0)
                check(150 < remaining < 180, 'Arcane Recovery cooldown survives the real process restart without reset')
                async with session.get(base + '/ranking') as resp:
                    check(resp.status == 200 and bool(await resp.json()), 'Public ranking works after restart')
                proc2.send_signal(signal.SIGTERM)
                await close_for_restart(ws3)
                check(await asyncio.to_thread(proc2.wait, 15) == 0, 'Second shutdown exits successfully')
        finally:
            for proc in processes:
                if proc.poll() is None:
                    proc.terminate()
                    try: proc.wait(timeout=12)
                    except subprocess.TimeoutExpired: proc.kill(); proc.wait()
            log.close()
            print('\nServer log:\n' + (tmp / 'server.log').read_text())
    print(json.dumps({'checks': len(checks), 'passed': len(checks), 'aiohttp': aiohttp.__version__,
                      'python': sys.version.split()[0], 'scope': 'local TCP and WebSocket; not Railway'}, indent=2))


if __name__ == '__main__':
    asyncio.run(main())
