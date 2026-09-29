'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const appSource = fs.readFileSync(path.join(__dirname, '../web/app_shell.js'), 'utf8');
const swSource = fs.readFileSync(path.join(__dirname, '../web/sw.js'), 'utf8');

class Events {
  constructor() { this.listeners = new Map(); }
  addEventListener(name, handler) {
    if (!this.listeners.has(name)) this.listeners.set(name, []);
    this.listeners.get(name).push(handler);
  }
  async emit(name, event = {}) {
    for (const handler of this.listeners.get(name) || []) await handler(event);
  }
}
class Element extends Events {
  constructor(doc, tag) {
    super(); this.doc = doc; this.tag = tag; this.children = []; this.dataset = {};
    this.attributes = {}; this.textContent = ''; this.hidden = false; this.open = false;
  }
  append(...elements) { this.children.push(...elements); }
  insertBefore(element, before) { const i = this.children.indexOf(before); this.children.splice(i < 0 ? this.children.length : i, 0, element); }
  querySelector(selector) { return selector === '.auth-foot' ? this.doc.authFoot : null; }
  setAttribute(key, value) { this.attributes[key] = value; }
  getAttribute(key) { return this.attributes[key]; }
  replaceChildren(...children) { this.children = children; }
  focus() { this.doc.activeElement = this; }
  showModal() { this.open = true; }
  close() { this.open = false; this.emit('close'); }
}
function app({ userAgent = '', standalone = false, secure = true } = {}) {
  const doc = new Events();
  doc.elements = [];
  doc.createElement = tag => { const el = new Element(doc, tag); doc.elements.push(el); return el; };
  doc.body = doc.createElement('body'); doc.documentElement = doc.createElement('html');
  doc.authCard = doc.createElement('section'); doc.authFoot = doc.createElement('div'); doc.authCard.append(doc.authFoot);
  doc.actions = doc.createElement('div'); const logout = doc.createElement('button'); logout.id = 'logoutButton'; doc.actions.append(logout);
  const game = doc.createElement('section'); game.id = 'gameUI';
  doc.getElementById = id => doc.elements.find(el => el.id === id);
  doc.querySelector = selector => selector.includes('auth-card') ? doc.authCard : doc.actions;
  const root = new Events(), media = new Events(); media.matches = standalone;
  const registrations = [];
  Object.assign(root, {
    document: doc, navigator: { userAgent, platform: '', maxTouchPoints: 0, serviceWorker: { register: async (...args) => { registrations.push(args); } } },
    matchMedia: () => media, isSecureContext: secure, setTimeout: () => 1, clearTimeout: () => {},
  });
  vm.runInNewContext(appSource, root, { filename: 'app_shell.js' });
  let stops = 0;
  const api = root.BractwoAppShell.create({ stop: () => { stops++; } });
  return { root, doc, api, registrations, stops: () => stops, button: id => doc.getElementById(id) };
}

test('fullscreen is requested by a click and browser events synchronize every control', async () => {
  const a = app(); let enters = 0, exits = 0;
  a.doc.documentElement.requestFullscreen = async () => { enters++; a.doc.fullscreenElement = a.doc.documentElement; };
  a.doc.exitFullscreen = async () => { exits++; a.doc.fullscreenElement = null; };
  assert.equal(enters, 0);
  await a.button('mobileFullscreenButton').emit('click');
  assert.equal(enters, 1); assert.equal(a.button('fullscreenButton').getAttribute('aria-pressed'), 'true');
  assert.equal(a.button('authFullscreenButton').textContent, '⛶ Opuść pełny ekran');
  await a.button('fullscreenButton').emit('click');
  assert.equal(exits, 1); assert.equal(a.button('mobileFullscreenButton').getAttribute('aria-pressed'), 'false');
  a.doc.fullscreenElement = a.doc.documentElement; await a.doc.emit('fullscreenchange');
  assert.equal(a.button('fullscreenButton').dataset.mobileLabel, 'Opuść pełny ekran');
  assert.equal(a.stops(), 2);
});

test('fullscreen denial opens dismissible help, stops movement and permits retry', async () => {
  const a = app();
  a.doc.documentElement.requestFullscreen = async () => { throw new Error('NotAllowedError'); };
  await a.button('fullscreenButton').emit('click');
  assert.equal(a.api.blocksControls(), true);
  assert.match(a.button('appHelpTitle').textContent, /Nie udało/);
  let prevented = false, stopped = false;
  await a.root.emit('keydown', { key: 'Escape', preventDefault: () => { prevented = true; }, stopImmediatePropagation: () => { stopped = true; } });
  assert.equal(prevented && stopped, true); assert.equal(a.api.blocksControls(), false);
  a.doc.documentElement.requestFullscreen = async () => { a.doc.fullscreenElement = a.doc.documentElement; };
  await a.button('fullscreenButton').emit('click');
  assert.equal(a.button('fullscreenButton').getAttribute('aria-pressed'), 'true');
});

test('iPhone without fullscreen receives honest Add to Home Screen instructions', async () => {
  const a = app({ userAgent: 'Mozilla/5.0 (iPhone) Safari/604.1' });
  await a.button('mobileFullscreenButton').emit('click');
  const text = a.button('appHelpBody').children.map(el => el.textContent).join(' ');
  assert.match(text, /Safari/); assert.match(text, /Dodaj do ekranu początkowego/); assert.match(text, /internetu/);
  assert.equal(a.button('mobileFullscreenButton').getAttribute('aria-pressed'), 'false');
});

test('accepted install prompt does not falsely report completed installation', async () => {
  const a = app(); let prompted = 0, prevented = false;
  await a.root.emit('beforeinstallprompt', { preventDefault: () => { prevented = true; }, prompt: async () => { prompted++; }, userChoice: Promise.resolve({ outcome: 'accepted' }) });
  assert.equal(prevented, true); assert.equal(prompted, 0);
  await a.button('installAppButton').emit('click');
  assert.equal(prompted, 1); assert.equal(a.button('installAppButton').hidden, false);
  assert.match(a.button('appShellStatus').textContent, /Dokończ/);
  await a.root.emit('appinstalled');
  assert.equal(a.button('installAppButton').hidden, true); assert.equal(a.button('authInstallButton').hidden, true);
  assert.match(a.button('appShellStatus').textContent, /zostało dodane/);
});

test('dismissed install consumes the prompt and the next click offers manual help', async () => {
  const a = app(); let prompted = 0;
  await a.root.emit('beforeinstallprompt', { preventDefault() {}, prompt: async () => { prompted++; }, userChoice: Promise.resolve({ outcome: 'dismissed' }) });
  await a.button('installAppButton').emit('click');
  assert.match(a.button('appShellStatus').textContent, /anulowano/);
  await a.button('installAppButton').emit('click');
  assert.equal(prompted, 1); assert.equal(a.api.blocksControls(), true);
  assert.match(a.button('appHelpBody').children.map(el => el.textContent).join(' '), /wymaga internetu/);
});

test('standalone mode hides install affordances and worker only registers on secure origins', () => {
  const a = app({ standalone: true });
  assert.equal(a.button('installAppButton').hidden, true);
  assert.equal(a.registrations.length, 1);
  assert.equal(a.registrations[0][0], '/sw.js');
  assert.equal(a.registrations[0][1].updateViaCache, 'none');
  assert.equal(app({ secure: false }).registrations.length, 0);
});

function worker() {
  const root = new Events(), deleted = [], cached = [], fetches = [];
  const fallback = { body: 'offline page' };
  const cache = { addAll: async paths => cached.push(...paths), match: async key => key === '/offline.html' ? fallback : undefined };
  let failure = false, claimed = 0, skipped = 0;
  Object.assign(root, {
    location: { origin: 'https://bractwo.example' }, clients: { claim: async () => { claimed++; } }, skipWaiting: async () => { skipped++; },
  });
  const context = {
    self: root, URL, caches: { open: async () => cache, keys: async () => ['unrelated-project', 'bractwo-app-shell-0.8.17', 'bractwo-app-shell-0.8.18'], delete: async name => deleted.push(name) },
    fetch: async request => { fetches.push(request); if (failure) throw new Error('offline'); return { body: 'fresh network' }; },
  };
  vm.runInNewContext(swSource, context, { filename: 'sw.js' });
  async function lifecycle(name) { let pending; await root.emit(name, { waitUntil: p => { pending = p; } }); await pending; }
  async function request(pathname, options = {}) {
    let response;
    await root.emit('fetch', { request: { url: 'https://bractwo.example' + pathname, method: 'GET', mode: 'cors', ...options }, respondWith: p => { response = p; } });
    return response;
  }
  return { lifecycle, request, deleted, cached, fetches, fallback, setOffline: () => { failure = true; }, counts: () => ({ claimed, skipped }) };
}

test('worker precaches only disconnected page and icons, and preserves unrelated caches', async () => {
  const w = worker(); await w.lifecycle('install'); await w.lifecycle('activate');
  assert.deepEqual(w.cached, ['/offline.html', '/icons/icon-192.png', '/icons/icon-512.png', '/icons/apple-touch-icon.png']);
  assert.deepEqual(w.deleted, ['bractwo-app-shell-0.8.17']);
  assert.deepEqual(w.counts(), { claimed: 1, skipped: 1 });
});

test('worker never intercepts game code, API, credential POST or cross-origin requests', async () => {
  const w = worker();
  for (const [url, options] of [['/game.js', {}], ['/health', {}], ['/ws', {}], ['/login', { method: 'POST' }], ['/icons/icon-192.png?v=2', {}], ['/icons/icon-192.png', { url: 'https://elsewhere.example/icons/icon-192.png' }]]) {
    assert.equal(await w.request(url, options), undefined);
  }
  assert.equal(w.fetches.length, 0);
});

test('navigation loads fresh HTML online and falls back to disconnected page offline', async () => {
  const w = worker();
  assert.deepEqual(await w.request('/', { mode: 'navigate' }), { body: 'fresh network' });
  w.setOffline();
  assert.equal(await w.request('/', { mode: 'navigate' }), w.fallback);
  assert.equal(w.fetches.length, 2);
});
