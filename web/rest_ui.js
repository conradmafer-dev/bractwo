/* Rest choices and progress follow authoritative server state. */
(function (root) {
  'use strict';
  const seconds = value => Math.max(0, Math.ceil(Number(value) || 0));
  const reasons = {
    combat_pve: 'Przerwa po walce z potworami',
    combat_pvp: 'Trwa blokada walki z graczem',
    dead: 'Odpoczynek jest dostępny dla żywej postaci.',
    moving: 'Zatrzymaj się, aby odpocząć.',
    disconnected: 'Połącz się ponownie, aby odpocząć.',
    channel: 'Najpierw zakończ trwającą czynność.'
  };
  function model(player, rules = {}) {
    const p = player || {};
    const rest = p.rest || {};
    const active = ['short', 'long'].includes(rest.kind) && Number(rest.remaining) > 0;
    const wait = seconds(p.rest_block_remaining);
    const alive = !!player && p.hp > 0 && p.alive !== false;
    const reason = p.rest_block_reason || '';
    const blocked = !alive || wait > 0 || !!reason;
    let restriction = !alive ? reasons.dead : reason ? (reasons[reason] || reason) : '';
    if (wait) restriction = (restriction || 'Przerwa po walce') + ` — jeszcze ${wait} s.`;
    return {
      active, kind: rest.kind, remaining: seconds(rest.remaining),
      progress: active ? Math.max(0, Math.min(1, 1 - Number(rest.remaining) / Math.max(1, Number(rest.total) || 1))) : 0,
      shortSeconds: seconds(rules.short_seconds || 6), longSeconds: seconds(rules.long_seconds || 15),
      hpPercent: Math.round(100 * (rules.short_hp_fraction ?? .25)),
      manaPercent: Math.round(100 * (rules.short_mana_fraction ?? .25)),
      canShort: !blocked && !active, canLong: !blocked && !active && p.rest_safe === true,
      safe: p.rest_safe === true, restriction
    };
  }
  function create(h) {
    const ui = document.getElementById('gameUI');
    const el = (tag, id, text) => {
      const node = document.createElement(tag);
      if (id) node.id = id;
      if (text) node.textContent = text;
      return node;
    };
    const button = (id, text, callback) => {
      const node = el('button', id, text); node.type = 'button'; node.addEventListener('click', callback); return node;
    };
    const toggle = button('restMenuButton', '', open);
    toggle.append(el('span', null, '☾'), el('small', null, 'Odpoczynek'));
    toggle.className = 'rest-launcher'; toggle.title = 'Krótki lub długi odpoczynek';
    toggle.setAttribute('aria-label', 'Odpoczynek'); toggle.dataset.mobileLabel = 'Odpoczynek';
    toggle.setAttribute('aria-controls', 'restPanel');
    const book = document.getElementById('bookSpell');
    const toolbar = book.closest('.hotbar-toolbar');
    const combat = ui.querySelector('.combat-controls');
    book.parentElement.append(toggle);
    function positionButton() {
      const mobile = root.BractwoMobile?.active?.();
      const parent = mobile ? combat : book.parentElement;
      if (toggle.parentElement !== parent) parent.append(toggle);
      if (ui.hidden) return;
      const b = book.getBoundingClientRect();
      if (!b.width || !b.height) return;
      const pages = document.getElementById('hotbarPages').getBoundingClientRect();
      let width = b.width, x = b.left, y = Math.min(b.top, pages.height ? pages.top : b.top) - b.height - 6;
      if (mobile) {
        const talk = document.getElementById('interactButton').getBoundingClientRect();
        width = document.getElementById('abilityButton').getBoundingClientRect().width;
        x = talk.left + (talk.width - width) / 2; y = b.top;
        const t = toolbar.getBoundingClientRect();
        // Narrow portrait screens need a separate row to keep the existing controls clear.
        if (x < t.right && x + width > t.left) y = t.top - b.height - 8;
      }
      const values = { left: x, top: y, width, height: b.height };
      for (const [key, value] of Object.entries(values)) {
        const pixels = Math.round(value) + 'px';
        if (toggle.style[key] !== pixels) toggle.style[key] = pixels;
      }
    }
    root.addEventListener('resize', () => requestAnimationFrame(positionButton));
    const panel = el('dialog', 'restPanel'); panel.hidden = true;
    panel.setAttribute('aria-labelledby', 'restTitle');
    const header = el('header'); header.append(el('h2', 'restTitle', 'Odpoczynek'));
    const closeButton = button('closeRestPanel', '×', close);
    closeButton.setAttribute('aria-label', 'Zamknij odpoczynek'); header.append(closeButton);
    const restriction = el('p', 'restRestriction'); restriction.setAttribute('role', 'status');
    const choices = el('div', 'restChoices');
    const shortCard = el('section'), longCard = el('section');
    const shortTitle = el('h3'), longTitle = el('h3');
    const shortDetails = el('p'), longDetails = el('p', null, 'Pełne zdrowie i mana. Tylko w bezpiecznej osadzie.');
    const shortButton = button('shortRestButton', 'Krótki odpoczynek', () => start('short'));
    const longButton = button('longRestButton', 'Długi odpoczynek', () => start('long'));
    shortCard.append(shortTitle, shortDetails, shortButton); longCard.append(longTitle, longDetails, longButton);
    choices.append(shortCard, longCard);
    const status = el('p', 'restStatus'); status.className = 'sr-only'; status.setAttribute('role', 'status');
    const note = el('p', 'restNote', 'Postęp zobaczysz nad postacią. Ruch, walka lub ponowne naciśnięcie Odpoczynek przerywają regenerację.');
    panel.append(header, restriction, choices, note); ui.append(panel, status);
    let focus = null;
    function open() {
      const { player, world } = h.state();
      if (!player) return;
      if (model(player, world.rest_rules).active) { h.send({ type: 'rest_cancel' }); return; }
      focus = document.activeElement; h.prepare?.(); h.stop?.();
      panel.hidden = false; render();
      if (!panel.open) panel.showModal();
      closeButton.focus({ preventScroll: true });
    }
    function close() {
      if (panel.hidden && !panel.open) return;
      if (panel.open) panel.close(); panel.hidden = true;
      const target = focus?.isConnected && focus.getClientRects().length ? focus : document.getElementById('mobileMenuButton');
      target?.focus({ preventScroll: true });
    }
    function start(kind) {
      const { player, world } = h.state(), m = model(player, world.rest_rules);
      if (!(kind === 'short' ? m.canShort : m.canLong)) return;
      h.stop?.(); h.clearTarget?.(); h.send({ type: 'rest', kind });
      close();
    }
    function render() {
      const { player, world } = h.state(), m = model(player, world.rest_rules);
      positionButton();
      toggle.classList.toggle('rest-active', m.active);
      toggle.title = m.active ? `Przerwij odpoczynek — ${m.remaining} s` : 'Krótki lub długi odpoczynek';
      toggle.setAttribute('aria-label', m.active ? 'Przerwij odpoczynek' : 'Odpoczynek');
      toggle.dataset.mobileLabel = m.active ? 'Przerwij odpoczynek' : 'Odpoczynek';
      const announcement = m.active ? 'Trwa odpoczynek. Postęp jest nad postacią. Ruch lub przycisk Odpoczynek przerywa regenerację.' : '';
      if (status.textContent !== announcement) status.textContent = announcement;
      if (m.active) { close(); return; }
      if (panel.hidden) return;
      if (!player) { close(); return; }
      shortTitle.textContent = `Krótki · ${m.shortSeconds} s`;
      longTitle.textContent = `Długi · ${m.longSeconds} s`;
      shortDetails.textContent = `Odnawia ${m.hpPercent}% maks. zdrowia i ${m.manaPercent}% maks. many. Także w terenie.`;
      shortButton.disabled = !m.canShort; longButton.disabled = !m.canLong;
      restriction.textContent = m.restriction || (m.safe ? 'Możesz rozpocząć odpoczynek. Bez opłaty.' : 'Długi odpoczynek wymaga bezpiecznej osady. Krótki jest dostępny także tutaj.');
    }
    panel.addEventListener('cancel', event => { event.preventDefault(); close(); });
    return { open, close, render, blocksControls: () => panel.open };
  }
  const api = { model, create }; root.BractwoRestUI = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);
