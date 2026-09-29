'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { bindTouchTap } = require('../web/runtime.js');

function setup() {
  const listeners = new Map(), casts = [], scroller = { scrollLeft: 0, scrollTop: 0 };
  const button = {
    disabled: false,
    addEventListener(type, listener) { if (!listeners.has(type)) listeners.set(type, []); listeners.get(type).push(listener); },
    getBoundingClientRect: () => ({ left: 100, right: 154, top: 200, bottom: 256 })
  };
  bindTouchTap(button, event => casts.push(event.pointerId ?? 'click'), () => scroller);
  function emit(type, props = {}) {
    const event = { pointerId: 22, pointerType: 'touch', isPrimary: false, clientX: 125, clientY: 225,
      defaultPrevented: false, preventDefault() { this.defaultPrevented = true; }, ...props };
    for (const listener of listeners.get(type) || []) listener(event);
    return event;
  }
  return { button, casts, scroller, emit };
}

test('second-finger touch casts on release without click and ignores its compatibility click', () => {
  const a = setup();
  assert.equal(a.emit('pointerdown').defaultPrevented, false);
  assert.equal(a.casts.length, 0);
  a.emit('pointerup'); assert.deepEqual(a.casts, [22]);
  a.emit('click', { detail: 1 });
  a.emit('click', { pointerType: undefined, detail: 1 });
  assert.deepEqual(a.casts, [22]);
});

test('horizontal swipe, changed scroll position and canceled gestures never cast', () => {
  for (const mode of ['swipe', 'scroll', 'cancel', 'capture-lost', 'contextmenu']) {
    const a = setup(); a.emit('pointerdown');
    if (mode === 'swipe') {
      assert.equal(a.emit('pointermove', { clientX: 145 }).defaultPrevented, false);
      a.emit('pointermove', { clientX: 125 }); // Returning to the start is still a swipe.
    }
    if (mode === 'scroll') a.scroller.scrollLeft = 20;
    if (mode === 'cancel') a.emit('pointercancel');
    if (mode === 'capture-lost') a.emit('lostpointercapture');
    if (mode === 'contextmenu') a.emit('contextmenu');
    a.emit('pointerup'); a.emit('click', { detail: 1 });
    assert.equal(a.casts.length, 0, mode);
  }
});

test('release outside the button or a newly disabled button does not cast', () => {
  const outside = setup(); outside.emit('pointerdown', { clientX: 150 }); outside.emit('pointerup', { clientX: 156 });
  assert.equal(outside.casts.length, 0);
  const disabled = setup(); disabled.emit('pointerdown'); disabled.button.disabled = true; disabled.emit('pointerup');
  assert.equal(disabled.casts.length, 0);
});

test('mouse and keyboard clicks still work immediately after a touch', () => {
  const a = setup(); a.emit('pointerdown'); a.emit('pointerup');
  a.emit('pointerdown', { pointerType: 'mouse', pointerId: 1 });
  a.emit('pointerup', { pointerType: 'mouse', pointerId: 1 });
  assert.equal(a.casts.length, 1);
  a.emit('click', { pointerType: 'mouse', pointerId: 1, detail: 1 });
  a.emit('click', { pointerType: '', pointerId: -1, detail: 0 });
  assert.deepEqual(a.casts, [22, 1, -1]);
});

test('touches are independent: canceling one pointer does not discard another tap', () => {
  const a = setup(); a.emit('pointerdown', { pointerId: 22 }); a.emit('pointerdown', { pointerId: 23 });
  a.emit('pointercancel', { pointerId: 22 }); a.emit('pointerup', { pointerId: 23 });
  assert.deepEqual(a.casts, [23]);
});

test('actual game release handler preserves the joystick when another finger is released', () => {
  const game = fs.readFileSync(path.join(__dirname, '../web/game.js'), 'utf8');
  const start = game.indexOf('  function releasePointer(event) {');
  const end = game.indexOf('  addEventListener("pointerup", releasePointer)', start);
  assert.ok(start > 0 && end > start);
  const context = { joystick: { pointer: 11, x: .8, y: .2 }, attackPointer: 7, attackHeld: true, playing: true,
    ui: { joystickKnob: { style: { transform: 'held' } }, attackButton: { classList: { remove() {} } } }, send() {} };
  vm.runInNewContext(game.slice(start, end), context);
  context.releasePointer({ pointerId: 22 });
  assert.equal(context.joystick.pointer, 11); assert.equal(context.joystick.x, .8); assert.equal(context.attackHeld, true);
  context.releasePointer({ pointerId: 11 });
  assert.equal(context.joystick.pointer, null); assert.equal(context.joystick.x, 0); assert.equal(context.attackHeld, true);
});
