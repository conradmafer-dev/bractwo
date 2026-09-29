'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const source = fs.readFileSync(path.join(__dirname, '../web/windows.js'), 'utf8');

function setup(saved = {}, mobile = false) {
  const storage = new Map(Object.entries(saved)), frames = [], events = new Map();
  let stops = 0, isMobile = mobile;
  const root = { innerWidth: mobile ? 390 : 1440, innerHeight: mobile ? 844 : 900 };
  class Element {
    constructor(tag = 'div') {
      this.tagName = tag.toUpperCase(); this.children = []; this.parentNode = null; this.nodeType = 1;
      this.className = ''; this.dataset = {}; this.attributes = {}; this.handlers = new Map(); this.captures = new Set();
      this.hidden = false; this.disabled = false; this.rect = { x: 20, y: 20, width: 200, height: 80 };
      const props = new Map();
      this.style = { setProperty: (key, value) => props.set(key, value), removeProperty: key => props.delete(key), getPropertyValue: key => props.get(key) || '' };
      this.classList = { contains: name => this.className.split(/\s+/).includes(name), add: (...names) => { this.className = [...new Set([...this.className.split(/\s+/).filter(Boolean), ...names])].join(' '); }, remove: name => { this.className = this.className.split(/\s+/).filter(x => x !== name).join(' '); }, toggle: (name, value) => { const on = value ?? !this.classList.contains(name); on ? this.classList.add(name) : this.classList.remove(name); return on; } };
    }
    get isConnected() { return this === body || Boolean(this.parentNode?.isConnected); }
    append(...nodes) { for (const node of nodes) { if (node.parentNode) node.parentNode.children.splice(node.parentNode.children.indexOf(node), 1); node.parentNode = this; this.children.push(node); } }
    matches(selector) { return selector.startsWith('#') ? this.id === selector.slice(1) : selector.startsWith('.') ? this.classList.contains(selector.slice(1)) : this.tagName === selector.toUpperCase(); }
    querySelectorAll(selector) { const out = []; for (const node of this.children) { if (node.nodeType !== 1) continue; if (node.matches(selector)) out.push(node); out.push(...node.querySelectorAll(selector)); } return out; }
    querySelector(selector) { return this.querySelectorAll(selector)[0] || null; }
    closest(selectors) { return selectors.split(',').some(selector => this.matches(selector)) ? this : this.parentNode?.closest(selectors) || null; }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    getAttribute(key) { return this.attributes[key] ?? null; }
    hasAttribute(key) { return Object.hasOwn(this.attributes, key); }
    toggleAttribute(key, on) { if (on) this.attributes[key] = ''; else delete this.attributes[key]; }
    addEventListener(name, handler) { if (!this.handlers.has(name)) this.handlers.set(name, []); this.handlers.get(name).push(handler); }
    dispatch(name, details = {}) { const e = { target: this, button: 0, pointerId: 1, clientX: 40, clientY: 40, preventDefault() {}, stopPropagation() {}, stopImmediatePropagation() {}, ...details }; for (const handler of this.handlers.get(name) || []) handler(e); return e; }
    click() { if (!this.disabled) { this.onclick?.(); this.dispatch('click'); } }
    setPointerCapture(id) { this.captures.add(id); }
    hasPointerCapture(id) { return this.captures.has(id); }
    releasePointerCapture(id) { this.captures.delete(id); }
    getBoundingClientRect() { const floating = this.classList.contains('hud-floating'); const x = floating ? parseFloat(this.style.getPropertyValue('--float-x')) || this.rect.x : this.rect.x; const y = floating ? parseFloat(this.style.getPropertyValue('--float-y')) || this.rect.y : this.rect.y; const width = floating ? parseFloat(this.style.getPropertyValue('--float-width')) || this.rect.width : this.rect.width; return { x, y, width, height: this.rect.height, top: y, left: x, right: x + width, bottom: y + this.rect.height }; }
  }
  const body = new Element('body'), ui = new Element('section'); ui.id = 'gameUI'; body.append(ui);
  function element(className, id, rect) { const el = new Element(); el.className = className; el.id = id; if (rect) el.rect = rect; ui.append(el); return el; }
  const player = element('player-card', '', { x: 30, y: 30, width: 200, height: 80 });
  element('topbar', '', { x: 10, y: 10, width: 1000, height: 80 });
  element('world-status'); element('pvp-bar'); element('', 'questTracker');
  element('', 'actionDock', { x: 300, y: 730, width: 500, height: 150 });
  const effects = element('', 'effectsPanel'); effects.hidden = true;
  const doc = { getElementById: id => body.querySelector('#' + id), querySelector: selector => body.querySelector(selector), createElement: tag => new Element(tag), createTextNode: text => ({ nodeType: 3, textContent: text }) };
  Object.assign(root, {
    document: doc, localStorage: { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) },
    BractwoMobile: { active: () => isMobile }, requestAnimationFrame: fn => frames.push(fn), setTimeout: () => 1,
    MutationObserver: class { observe() {} }, ResizeObserver: class { observe() {} },
    addEventListener: (name, callback) => events.set(name, callback),
  });
  vm.runInNewContext(source, root, { filename: 'windows.js' });
  const api = root.BractwoWindows.create({ stop: () => { stops++; } });
  function flush() { for (let i = 0; frames.length && i < 50; i++) frames.shift()(); assert.equal(frames.length, 0, 'Layout loop must settle'); }
  flush(); api.sync('hero'); flush();
  const lock = doc.getElementById('hudLayoutLock'), handle = player.querySelector('.window-grip');
  function move(x = 120, y = 100) { handle.dispatch('pointerdown'); handle.dispatch('pointermove', { clientX: x, clientY: y }); handle.dispatch('pointerup', { clientX: x, clientY: y }); flush(); }
  return { api, ui, player, lock, handle, storage, flush, move, stops: () => stops, saved: key => JSON.parse(storage.get(key)), mobile(value) { isMobile = value; root.innerWidth = value ? 390 : 1440; root.innerHeight = value ? 844 : 900; events.get('resize')(); flush(); } };
}
const DESKTOP = 'bractwo-windows-v1:hero:landscape';
const MOBILE = 'bractwo-windows-mobile-v1:hero:portrait';

test('new layouts start locked; pointer and keyboard cannot move panels', () => {
  const a = setup();
  assert.equal(a.api.locked, true); assert.equal(a.lock.getAttribute('aria-pressed'), 'true');
  assert.equal(a.lock.title, 'Odblokuj przesuwanie paneli');
  assert.equal(a.handle.disabled, true); assert.equal(a.ui.classList.contains('hud-layout-locked'), true);
  a.move(); a.handle.dispatch('keydown', { key: 'ArrowRight' });
  assert.equal(a.player.classList.contains('hud-floating'), false);
  assert.equal(Object.keys(a.api.positions).length, 0); assert.equal(a.handle.captures.size, 0);
});

test('legacy saved positions and visibility survive default-lock migration', () => {
  const old = { positions: { player: { x: .3, y: .2, width: 210 } }, hidden: { region: true } };
  const a = setup({ [DESKTOP]: JSON.stringify(old) });
  assert.equal(a.api.locked, true); assert.equal(a.player.classList.contains('hud-floating'), true);
  assert.equal(a.ui.querySelector('.world-status').hasAttribute('data-hud-hidden'), true);
  assert.equal(JSON.stringify(a.api.positions), JSON.stringify(old.positions));
  a.lock.click();
  assert.equal(a.saved(DESKTOP).locked, false);
  assert.deepEqual(a.saved(DESKTOP).positions, old.positions); assert.deepEqual(a.saved(DESKTOP).hidden, old.hidden);
});

test('explicit unlock permits drag and arrow movement, and locking preserves placement', () => {
  const a = setup(); a.lock.click(); a.flush();
  assert.equal(a.handle.disabled, false); assert.equal(a.api.locked, false);
  a.move(); const dragged = { ...a.api.positions.player };
  assert.equal(a.player.classList.contains('hud-floating'), true); assert.ok(dragged.x > 0);
  a.handle.dispatch('keydown', { key: 'ArrowRight' }); a.flush();
  assert.ok(a.api.positions.player.x > dragged.x);
  const before = JSON.stringify(a.api.positions);
  a.lock.click(); a.move(250, 250); a.handle.dispatch('keydown', { key: 'ArrowLeft' });
  assert.equal(JSON.stringify(a.api.positions), before); assert.equal(a.saved(DESKTOP).locked, true);
  assert.equal(a.player.classList.contains('hud-floating'), true);
});

test('locking mid-drag releases capture and restores the last committed position', () => {
  const a = setup(); a.lock.click(); a.move();
  const before = JSON.stringify(a.api.positions), rect = a.player.getBoundingClientRect();
  a.handle.dispatch('pointerdown'); a.handle.dispatch('pointermove', { clientX: 240, clientY: 180 });
  assert.equal(a.handle.captures.size, 1);
  a.lock.click(); a.flush();
  assert.equal(a.handle.captures.size, 0); assert.equal(JSON.stringify(a.api.positions), before);
  assert.deepEqual(a.player.getBoundingClientRect(), rect); assert.ok(a.stops() > 0);
});

test('reset preserves current lock state while clearing positions and hidden panels', () => {
  const a = setup(); a.api.reset(); a.flush(); assert.equal(a.api.locked, true);
  a.lock.click(); a.move(); a.api.reset(); a.flush();
  assert.equal(a.api.locked, false); assert.equal(a.player.classList.contains('hud-floating'), false);
  assert.deepEqual(a.saved(DESKTOP), { positions: {}, hidden: {}, locked: false });
});

test('mobile unlock permits moving panels and relock preserves separate saved placement', () => {
  const a = setup(); a.lock.click(); a.move(); const desktop = a.storage.get(DESKTOP);
  a.mobile(true); assert.equal(a.api.locked, true); assert.equal(a.lock.disabled, false);
  a.move(); assert.equal(Object.keys(a.api.positions).length, 0);
  a.lock.click(); a.move(80, 160);
  assert.equal(a.api.locked, false); assert.equal(a.player.classList.contains('hud-floating'), true);
  assert.ok(a.saved(MOBILE).positions.player); assert.equal(a.storage.get(DESKTOP), desktop);
  const moved = JSON.stringify(a.api.positions); a.lock.click(); a.flush();
  assert.equal(a.api.locked, true); assert.equal(JSON.stringify(a.api.positions), moved);
  assert.equal(a.player.classList.contains('hud-floating'), true);
  const mobile = a.storage.get(MOBILE);
  a.mobile(false); assert.equal(a.api.locked, false); assert.equal(JSON.stringify(a.api.positions), JSON.stringify(JSON.parse(desktop).positions));
  a.mobile(true); assert.equal(a.api.locked, true); assert.equal(a.storage.get(MOBILE), mobile);
});

test('only an explicit boolean false unlocks a stored profile', () => {
  for (const locked of [undefined, null, 0, 'false', true]) {
    const a = setup({ [DESKTOP]: JSON.stringify({ locked }) }); assert.equal(a.api.locked, true);
  }
  assert.equal(setup({ [DESKTOP]: JSON.stringify({ locked: false }) }).api.locked, false);
});
