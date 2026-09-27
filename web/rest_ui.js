/* One-click full recovery; progress and cooldown follow authoritative server state. */
(function (root) {
  'use strict';
  const seconds = value => Math.max(0, Math.ceil(Number(value) || 0));
  const reasons = {
    combat_pve: 'Przerwa po walce z potworami',
    combat_pvp: 'Trwa blokada walki z graczem',
    cooldown: 'Odpoczynek będzie ponownie dostępny',
    dead: 'Odpoczynek jest dostępny dla żywej postaci.',
    moving: 'Zatrzymaj się, aby odpocząć.',
    disconnected: 'Połącz się ponownie, aby odpocząć.',
    channel: 'Najpierw zakończ trwającą czynność.'
  };
  function model(player, rules = {}) {
    const p = player || {};
    const rest = p.rest || {};
    const active = ['short', 'long'].includes(rest.kind) && Number(rest.remaining) > 0;
    const cooldown = seconds(p.rest_cooldown_remaining);
    const wait = Math.max(seconds(p.rest_block_remaining), cooldown);
    const alive = !!player && p.hp > 0 && p.alive !== false;
    const reason = p.rest_block_reason || (cooldown ? 'cooldown' : '');
    const blocked = !alive || wait > 0 || !!reason;
    let restriction = !alive ? reasons.dead : reason ? (reasons[reason] || reason) : '';
    if (wait) restriction = (restriction || 'Przerwa po walce') + ` — jeszcze ${wait} s.`;
    return {
      active, kind: rest.kind, remaining: seconds(rest.remaining), cooldown,
      progress: active ? Math.max(0, Math.min(1, 1 - Number(rest.remaining) / Math.max(1, Number(rest.total) || 1))) : 0,
      shortSeconds: seconds(rules.short_seconds || 15), longSeconds: seconds(rules.long_seconds || 15),
      hpPercent: Math.round(100 * (rules.short_hp_fraction ?? 1)),
      manaPercent: Math.round(100 * (rules.short_mana_fraction ?? 1)),
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
    const icon = el('span', null, '☾');
    toggle.append(el('kbd', null, 'R'), icon, el('small', null, 'Odpoczynek'));
    toggle.className = 'rest-launcher'; toggle.title = 'Rozpocznij pełny odpoczynek';
    toggle.setAttribute('aria-label', 'Odpoczynek'); toggle.dataset.mobileLabel = 'Odpoczynek';
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
    const status = el('p', 'restStatus'); status.className = 'sr-only'; status.setAttribute('role', 'status');
    ui.append(status);
    function open() {
      const { player, world } = h.state();
      if (!player) return;
      const m = model(player, world.rest_rules);
      if (m.active) { h.send({ type: 'rest_cancel' }); return; }
      if (m.cooldown > 0) { h.notice?.(`Odpoczynek dostępny za ${m.cooldown} s.`); return; }
      h.prepare?.(); h.stop?.();
      // The server validates the current combat gate and reports any remaining wait.
      h.send({ type: 'rest', kind: 'short' });
    }
    function render() {
      const { player, world } = h.state(), m = model(player, world.rest_rules);
      positionButton();
      toggle.classList.toggle('rest-active', m.active);
      const coolingDown = !m.active && m.cooldown > 0;
      toggle.classList.toggle('rest-cooldown', coolingDown);
      toggle.disabled = coolingDown;
      icon.textContent = coolingDown ? `${m.cooldown}s` : '☾';
      toggle.title = m.active ? `R · Przerwij odpoczynek — ${m.remaining} s` : coolingDown ? `R · Odpoczynek dostępny za ${m.cooldown} s` : `R · Pełny odpoczynek · ${m.shortSeconds} s · całe HP i mana`;
      toggle.setAttribute('aria-label', m.active ? 'Przerwij odpoczynek' : coolingDown ? toggle.title : 'Pełny odpoczynek');
      toggle.dataset.mobileLabel = m.active ? 'Przerwij odpoczynek' : 'Odpoczynek';
      const announcement = m.active ? 'Trwa odpoczynek. Postęp jest nad postacią. Ruch lub przycisk Odpoczynek przerywa regenerację.' : coolingDown ? 'Odpoczynek się odnawia. Pozostały czas jest na przycisku.' : '';
      if (status.textContent !== announcement) status.textContent = announcement;
    }
    // Keep the shared window lifecycle API without creating a modal.
    return { open, close: () => {}, render, blocksControls: () => false };
  }
  const api = { model, create }; root.BractwoRestUI = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);
