'use strict';
const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const { bindTouchScroll, bindTouchTap } = require('../web/runtime.js');

// Minimal DOM propagation and touch capture: a swipe transfers implicit button
// capture to the viewport, so the child's lostpointercapture bubbles through it.
function setup() {
  const captures = new Map(), pending = new Map(), casts = [];
  let enabled = true;
  function node(parent = null) {
    return { parent, listeners: new Map(), disabled: false,
      addEventListener(type, fn, options) {
        if (!this.listeners.has(type)) this.listeners.set(type, []);
        this.listeners.get(type).push({ fn, capture: options === true || !!options?.capture });
      },
      setPointerCapture(id) { pending.set(id, this); },
      hasPointerCapture(id) { return captures.get(id) === this || pending.get(id) === this; },
      releasePointerCapture(id) { pending.set(id, null); }
    };
  }
  const windowNode = node(), scroller = node(windowNode), button = node(scroller);
  Object.assign(scroller, { scrollLeft: 0, scrollTop: 0, scrollWidth: 400, clientWidth: 180 });
  button.getBoundingClientRect = () => ({ left: 100 - scroller.scrollLeft,
    right: 154 - scroller.scrollLeft, top: 200, bottom: 256 });
  function dispatch(target, type, props) {
    const event = { pointerId: 22, pointerType: 'touch', isPrimary: false,
      clientX: 125, clientY: 225, detail: 0, ...props, type, target,
      defaultPrevented: false, stopped: false,
      preventDefault() { this.defaultPrevented = true; },
      stopPropagation() { this.stopped = true; }
    };
    const chain = []; for (let item = target; item; item = item.parent) chain.push(item);
    for (const capture of [true, false]) {
      for (const current of capture ? chain.slice().reverse() : chain) {
        event.currentTarget = current;
        for (const entry of current.listeners.get(type) || []) if (entry.capture === capture) entry.fn(event);
        if (event.stopped) return event;
      }
    }
    return event;
  }
  function flushCapture() {
    for (const [id, next] of [...pending]) {
      pending.delete(id);
      const old = captures.get(id);
      if (next) captures.set(id, next); else captures.delete(id);
      if (old && old !== next) dispatch(old, 'lostpointercapture', { pointerId: id });
    }
  }
  function emit(target, type, props = {}) {
    flushCapture();
    const id = props.pointerId ?? 22;
    const touch = (props.pointerType ?? 'touch') === 'touch';
    if (type === 'pointerdown' && touch) captures.set(id, target);
    const routed = ['pointermove', 'pointerup', 'pointercancel'].includes(type) ? captures.get(id) || target : target;
    const event = dispatch(routed, type, props);
    flushCapture();
    if (type === 'pointerup' || type === 'pointercancel') {
      const old = captures.get(id); captures.delete(id);
      if (old) dispatch(old, 'lostpointercapture', { pointerId: id });
    }
    return event;
  }
  const control = bindTouchScroll(scroller, () => enabled);
  bindTouchTap(button, event => casts.push(event.pointerId), () => scroller);
  return { windowNode, scroller, button, captures, casts, emit, control,
    enable(value) { enabled = value; } };
}

test('second-finger swipe keeps joystick movement and survives child capture loss', () => {
  const a = setup();
  const game = fs.readFileSync(path.join(__dirname, '../web/game.js'), 'utf8');
  const start = game.indexOf('  function releasePointer(event) {');
  const end = game.indexOf('  addEventListener("pointerup", releasePointer)', start);
  assert.ok(start > 0 && end > start);
  const context = { joystick: { pointer: 11, x: .8, y: .2 }, attackPointer: null, attackHeld: false,
    playing: true, ui: { joystickKnob: { style: { transform: 'held' } },
      attackButton: { classList: { remove() {} } } }, send() {} };
  vm.runInNewContext(game.slice(start, end), context);
  a.windowNode.addEventListener('pointerup', context.releasePointer);
  a.windowNode.addEventListener('pointercancel', context.releasePointer);
  assert.equal(a.emit(a.button, 'pointerdown').defaultPrevented, false);
  a.emit(a.button, 'pointermove', { clientX: 100 });
  assert.equal(a.scroller.scrollLeft, 25);
  assert.equal(a.captures.get(22), a.scroller);
  a.emit(a.button, 'pointermove', { clientX: 80 });
  assert.equal(a.scroller.scrollLeft, 45, 'child lostpointercapture must not end the swipe');
  a.emit(a.button, 'pointerup', { clientX: 75 });
  assert.equal(a.scroller.scrollLeft, 50);
  assert.equal(context.joystick.pointer, 11);
  assert.equal(context.joystick.x, .8);
  assert.deepEqual(a.casts, []);
  a.emit(a.windowNode, 'pointerup', { pointerId: 11 });
  assert.equal(context.joystick.pointer, null);
  assert.equal(context.joystick.x, 0);
});

test('swiping never casts or ghost-clicks; the next tap, mouse and keyboard still cast', () => {
  const a = setup();
  a.emit(a.button, 'pointerdown');
  a.emit(a.button, 'pointermove', { clientX: 85 });
  a.emit(a.button, 'pointermove', { clientX: 125 });
  a.emit(a.button, 'pointerup'); // Returning to the starting point remains a swipe.
  assert.equal(a.scroller.scrollLeft, 0);
  assert.equal(a.emit(a.button, 'click', { detail: 1 }).defaultPrevented, true);
  assert.equal(a.emit(a.button, 'click', { pointerType: '', detail: 1 }).defaultPrevented, true);
  assert.deepEqual(a.casts, []);
  a.emit(a.button, 'pointerdown', { pointerId: 23 });
  a.emit(a.button, 'pointerup', { pointerId: 23 });
  a.emit(a.button, 'click', { pointerId: 23, detail: 1 });
  a.emit(a.button, 'click', { pointerId: 1, pointerType: 'mouse', detail: 1 });
  a.emit(a.button, 'click', { pointerId: -1, pointerType: '', detail: 0 });
  assert.deepEqual(a.casts, [23, 1, -1]);
});

test('gaps and disabled-slot hit targets scroll; pointer IDs, cancellation and edges stay independent', () => {
  const a = setup();
  a.button.disabled = true;
  // Mobile disabled slots use pointer-events:none, so the viewport is hit.
  a.emit(a.scroller, 'pointerdown', { clientX: 100 });
  a.emit(a.scroller, 'pointermove', { clientX: 500 });
  assert.equal(a.scroller.scrollLeft, 0);
  a.emit(a.scroller, 'pointermove', { clientX: -500 });
  assert.equal(a.scroller.scrollLeft, 220);
  a.emit(a.scroller, 'pointerdown', { pointerId: 23, clientX: 100 });
  a.emit(a.scroller, 'pointermove', { pointerId: 23, clientX: 200 });
  a.emit(a.scroller, 'pointercancel', { pointerId: 23 });
  assert.equal(a.scroller.scrollLeft, 220);
  a.emit(a.scroller, 'pointermove', { clientX: 80 });
  assert.equal(a.scroller.scrollLeft, 20, 'unrelated cancellation must keep the first gesture');
  a.emit(a.scroller, 'pointercancel');
  a.emit(a.scroller, 'pointermove', { clientX: -500 });
  assert.equal(a.scroller.scrollLeft, 20);
  a.emit(a.scroller, 'pointerdown', { pointerId: 24, clientX: 100 });
  a.emit(a.scroller, 'pointermove', { pointerId: 24, clientX: 60 });
  assert.equal(a.scroller.scrollLeft, 60);
  a.control.cancel();
  a.emit(a.scroller, 'pointerup', { pointerId: 24, clientX: -500 });
  assert.equal(a.scroller.scrollLeft, 60);
  assert.deepEqual(a.casts, []);
});

test('desktop, mouse and non-overflow rows are not taken over by touch scrolling', () => {
  for (const mode of ['desktop', 'mouse', 'fits']) {
    const a = setup();
    if (mode === 'desktop') a.enable(false);
    if (mode === 'fits') a.scroller.scrollWidth = a.scroller.clientWidth;
    const props = mode === 'mouse' ? { pointerType: 'mouse', pointerId: 1 } : {};
    a.emit(a.button, 'pointerdown', props);
    assert.equal(a.emit(a.button, 'pointermove', { ...props, clientX: 50 }).defaultPrevented, false, mode);
    assert.notEqual(a.captures.get(props.pointerId ?? 22), a.scroller, mode);
    a.emit(a.button, 'pointerup', { ...props, clientX: 50 });
    assert.equal(a.scroller.scrollLeft, 0, mode);
  }
});
