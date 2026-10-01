'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

// Run the actual render lifecycle and frame function with a deterministic
// browser clock. Canvas and scenery are the only rendering substitutes.
const source = fs.readFileSync(path.join(__dirname, '../web/game.js'), 'utf8');
const start = source.indexOf('  function stopRendering(){');
const end = source.indexOf('  const spellIcons=', start);
assert.ok(start >= 0 && end > start, 'Render lifecycle source boundaries changed');

function fixture() {
  let time = 1000, nextId = 0, paints = 0, resets = 0;
  const pending = new Map(), listeners = new Map();
  const noop = () => {};
  const ctx = new Proxy({}, { get: (_, key) => key === 'fillRect' ? () => paints++ : noop, set: () => true });
  const scope = {
    animationFrame: null, playing: false, me: null, lastFrame: 0,
    performance: { now: () => time },
    document: { hidden: false, addEventListener: (name, listener) => listeners.set(name, listener) },
    requestAnimationFrame: callback => { const id = ++nextId; pending.set(id, callback); return id; },
    cancelAnimationFrame: id => pending.delete(id),
    fpsMeter: { reset: () => resets++, sample: () => null },
    snapshot: { players: [], time: 0 }, lastSnapshotAt: 1000, visuals: new Map(), myId: 'hero',
    camera: { x: 100, y: 100, scale: 1 }, viewport: { w: 390, h: 844, dpr: 1 },
    world: { width: 3200, height: 2304 }, ui: { connectionStatus: { textContent: ' ONLINE' } }, ctx,
    drawGround: noop, drawWaterways: noop, drawRiver: noop, drawSafeZone: noop, drawVillage: noop,
    nearbyDrawables: () => [], drawGoal: noop, drawTreeTargets: noop, drawWorldPoint: noop,
    drawEffects: noop, drawParticles: noop, drawMinimap: noop,
    BractwoCasterVFX: { world: noop },
  };
  vm.createContext(scope);
  vm.runInContext(source.slice(start, end), scope, { filename: 'game.js:render-lifecycle' });
  return {
    scope, pending, paints: () => paints, resets: () => resets,
    tick() { time += 16; const callbacks = [...pending.values()]; pending.clear(); for (const callback of callbacks) callback(time); },
    visible(visible) { scope.document.hidden = !visible; listeners.get('visibilitychange')(); },
  };
}

test('landing and an incomplete login do not schedule or draw game frames', () => {
  const f = fixture();
  f.scope.startRendering();
  f.scope.frame(1000);
  assert.equal(f.pending.size, 0);
  assert.equal(f.paints(), 0);
  f.scope.playing = true;
  f.scope.startRendering();
  f.scope.frame(1016);
  assert.equal(f.pending.size, 0, 'Wait for the first state containing the player');
  assert.equal(f.paints(), 0);
});

test('first player state starts one continuous render loop', () => {
  const f = fixture();
  f.scope.playing = true;
  f.scope.me = { floor: 0 };
  f.scope.startRendering();
  f.scope.startRendering();
  assert.equal(f.pending.size, 1, 'Repeated state packets must not duplicate the loop');
  f.tick(); f.tick();
  assert.equal(f.paints(), 2);
  assert.equal(f.pending.size, 1);
});

test('hidden tabs stop and resume rendering with a fresh frame clock', () => {
  const f = fixture();
  f.scope.playing = true;
  f.scope.me = { floor: 0 };
  f.scope.startRendering(); f.tick();
  f.visible(false);
  f.scope.startRendering();
  assert.equal(f.pending.size, 0);
  f.tick();
  assert.equal(f.paints(), 1);
  const before = f.scope.lastFrame;
  f.visible(true);
  assert.ok(f.scope.lastFrame > before, 'Hidden time must not be interpolated as one frame');
  assert.equal(f.pending.size, 1);
  f.tick();
  assert.equal(f.paints(), 2);
  assert.ok(f.resets() >= 3);
});

test('logout, disconnect and a missing player leave no render loop', () => {
  for (const reason of ['logout', 'disconnect', 'missing-player']) {
    const f = fixture();
    f.scope.playing = true; f.scope.me = { floor: 0 };
    f.scope.startRendering(); f.tick();
    if (reason === 'missing-player') f.scope.me = null;
    else { f.scope.playing = false; f.scope.stopRendering(); }
    f.tick(); f.visible(true);
    assert.equal(f.pending.size, 0, reason);
    assert.equal(f.paints(), 1, reason);
  }
});

test('empty level-up layout does not retrigger the HUD visibility observer', () => {
  let hidden = true, writes = 0;
  const panel = {
    get hidden() { return hidden; },
    set hidden(value) { hidden = value; writes++; },
    querySelector: () => ({}),
  };
  const context = { document: { getElementById: () => panel }, addEventListener() {} };
  vm.createContext(context);
  vm.runInContext(fs.readFileSync(path.join(__dirname, '../web/level_up.js'), 'utf8'), context);
  const levels = context.BractwoLevelUp.create({});
  levels.layout(); levels.layout();
  assert.equal(writes, 0, 'An already hidden panel must not emit another attribute mutation');
  hidden = false;
  levels.layout(); levels.layout();
  assert.equal(writes, 1, 'A real visibility change is applied exactly once');
  assert.equal(hidden, true);
});
