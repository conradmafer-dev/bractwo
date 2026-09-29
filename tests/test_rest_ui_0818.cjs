const { test } = require('node:test');
const assert = require('node:assert/strict');
const { model } = require('../web/rest_ui.js');
const living = { hp: 4, alive: true, rest_safe: true };
test('rest UI uses the server gate rather than the twenty-second combat tag', () => {
  const state = model({ ...living, combat_remaining: 17, rest_block_remaining: 0, rest_block_reason: '' });
  assert.equal(state.canShort, true); assert.equal(state.canLong, true);
  for (const reason of ['moving', 'channel', 'disconnected']) {
    const blocked = model({ ...living, rest_block_remaining: 0, rest_block_reason: reason });
    assert.equal(blocked.canShort, false); assert.equal(blocked.canLong, false);
    assert(blocked.restriction.length > 0);
  }
});
test('rest UI keeps PvP and the last fractional second blocked', () => {
  const state = model({ ...living, rest_block_remaining: .1, rest_block_reason: 'combat_pvp' });
  assert.equal(state.canShort, false); assert.equal(state.canLong, false);
  assert.match(state.restriction, /graczem.*1 s/);
});
test('both rests work in the field unless the server explicitly restricts long rest', () => {
  const field = model({ ...living, rest_safe: false });
  assert.equal(field.canShort, true); assert.equal(field.canLong, true);
  assert.equal(field.longNeedsCity, false);
  const restricted = model({ ...living, rest_safe: false }, { long_safe_only: true });
  assert.equal(restricted.canShort, true); assert.equal(restricted.canLong, false);
  assert.match(restricted.longRestriction, /mieście/);
  assert.equal(model(living, { long_safe_only: true }).canLong, true);
  for (const player of [{ ...living, hp: 0 }, { ...living, alive: false }, null]) {
    assert.equal(model(player).canShort, false); assert.equal(model(player).canLong, false);
  }
});
test('active rest exposes progress and suppresses duplicate starts', () => {
  for (const [kind, total, remaining] of [['short', 10, 4], ['long', 30, 12]]) {
    const state = model({ ...living, rest: { kind, total, remaining } });
    assert.equal(state.active, true); assert.equal(state.kind, kind);
    assert.equal(state.progress, .6); assert.equal(state.remaining, remaining);
    assert.equal(state.canShort, false); assert.equal(state.canLong, false);
  }
});
test('rest descriptions follow published server settings', () => {
  const defaults = model(living);
  assert.deepEqual([defaults.shortSeconds, defaults.longSeconds], [10, 30]);
  const hitDice = { id: 'hit_dice', remaining: 2, maximum: 4 };
  const state = model({ ...living, rest_resources: [hitDice] }, { short_seconds: 9, long_seconds: 21 });
  assert.deepEqual([state.shortSeconds, state.longSeconds], [9, 21]);
  assert.deepEqual(state.hitDice, hitDice);
});
test('short and long cooldowns are independent and include the last fractional second', () => {
  const short = model({ ...living, rest_short_remaining: .1, rest_long_remaining: 0 });
  assert.deepEqual([short.shortCooldown, short.longCooldown], [1, 0]);
  assert.equal(short.canShort, false); assert.equal(short.canLong, true);
  assert.match(short.shortRestriction, /Krótki.*1 s/);
  const long = model({ ...living, rest_short_remaining: 0, rest_long_remaining: .1 });
  assert.deepEqual([long.shortCooldown, long.longCooldown], [0, 1]);
  assert.equal(long.canShort, true); assert.equal(long.canLong, false);
  assert.match(long.longRestriction, /Długi.*1 s/);
  const both = model({ ...living, rest_short_remaining: 15, rest_long_remaining: 60 });
  assert.equal(both.canShort, false); assert.equal(both.canLong, false);
  const ready = model({ ...living, rest_short_remaining: 0, rest_long_remaining: 0 });
  assert.equal(ready.canShort, true); assert.equal(ready.canLong, true);
});
