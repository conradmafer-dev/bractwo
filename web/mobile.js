/* Phone HUD: existing game controls, separate presentation and no combat rules. */
(function (root) {
  'use strict';
  const query = '(max-width: 700px), (max-width: 1100px) and (max-height: 600px)';
  const media = root.matchMedia(query);
  const active = () => media.matches;

  function create({ stop = () => {}, closeChat = () => {} } = {}) {
    const ui = document.getElementById('gameUI');
    const chat = ui.querySelector('.chat-wrap');
    const chatButton = document.getElementById('chatButton');
    const chatForm = document.getElementById('chatForm');
    const button = (id, text, label) => {
      const el = document.createElement('button');
      el.type = 'button'; el.id = id; el.className = 'mobile-control';
      el.textContent = text; el.setAttribute('aria-label', label);
      return el;
    };
    const toggle = button('mobileMenuButton', '☰', 'Otwórz menu gry');
    toggle.setAttribute('aria-controls', 'mobileMenu');
    toggle.setAttribute('aria-expanded', 'false');
    const menu = document.createElement('aside');
    menu.id = 'mobileMenu'; menu.hidden = true;
    menu.setAttribute('aria-label', 'Menu gry');
    const head = document.createElement('header');
    const title = document.createElement('strong'); title.textContent = 'Menu gry';
    const close = button('mobileMenuClose', '×', 'Zamknij menu gry');
    head.append(title, close); menu.append(head); ui.append(toggle, menu);

    // Move the actual controls, so listeners, server state and tab order stay intact.
    const moved = ['.gold-chip', '.top-actions', '#safetyButton', '#skullStatus', '#hudVisibility'].map(selector => {
      const el = ui.querySelector(selector), anchor = document.createComment('desktop ' + selector);
      el.before(anchor); return { el, anchor };
    });
    for (const el of ui.querySelectorAll('.top-actions .icon-button')) {
      el.dataset.mobileLabel = el.getAttribute('aria-label') || el.title;
    }
    document.getElementById('mapButton').dataset.mobileLabel = 'Pokaż / ukryj minimapę';

    const map = button('mobileAtlasButton', '', 'Otwórz atlas świata');
    map.title = 'Otwórz atlas świata';
    map.addEventListener('click', () => document.getElementById('atlasButton').click());
    document.getElementById('minimapCard').append(map);
    const chatClose = button('mobileChatClose', '×', 'Zamknij czat');
    chat.append(chatClose);
    chatClose.addEventListener('click', () => { closeChat(); chatButton.focus({ preventScroll: true }); });
    chatButton.setAttribute('aria-controls', 'chatLog chatForm');
    document.getElementById('chatInput').setAttribute('aria-label', 'Wiadomość do graczy');

    function setOpen(open, focus = true) {
      const wasOpen = !menu.hidden;
      menu.hidden = !open;
      ui.classList.toggle('mobile-menu-open', open);
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Zamknij menu gry' : 'Otwórz menu gry');
      if (open) { stop(); closeChat(); if (focus) close.focus({ preventScroll: true }); }
      else if (wasOpen && focus) toggle.focus({ preventScroll: true });
    }
    toggle.addEventListener('click', () => setOpen(menu.hidden));
    close.addEventListener('click', () => setOpen(false));
    menu.addEventListener('click', event => {
      if (event.target.closest('.top-actions .icon-button')) setOpen(false, false);
    });
    document.addEventListener('pointerdown', event => {
      if (!menu.hidden && !menu.contains(event.target) && !toggle.contains(event.target)) setOpen(false, false);
    }, true);
    root.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !menu.hidden) {
        event.preventDefault(); event.stopImmediatePropagation(); setOpen(false);
      }
    }, true);

    function visualSize() {
      const view = root.visualViewport;
      ui.style.setProperty('--mobile-visual-height', (view?.height || innerHeight) + 'px');
      ui.style.setProperty('--mobile-visual-top', (view?.offsetTop || 0) + 'px');
      queueJoystick();
    }
    // Centre the default joystick in the free left-hand rectangle. In portrait
    // the full-width spell row sits above the bottom controls instead of beside them.
    let joystickQueued = false;
    function queueJoystick() {
      if (joystickQueued) return;
      joystickQueued = true;
      requestAnimationFrame(() => { joystickQueued = false; positionJoystick(); });
    }
    function positionJoystick() {
      if (!active() || ui.hidden) return;
      const movement = ui.querySelector('.movement-controls');
      if (movement.classList.contains('hud-floating')) return;
      const joystick = document.getElementById('joystick').getBoundingClientRect();
      const bar = document.getElementById('spellbar').getBoundingClientRect();
      const visible = el => el && el.getClientRects().length && getComputedStyle(el).visibility !== 'hidden' && !el.hasAttribute('data-hud-hidden');
      const padding = 8, gap = 8;
      const style = getComputedStyle(ui);
      const edge = parseFloat(style.getPropertyValue('--mobile-screen-left')) || 0;
      const floor = innerHeight - (parseFloat(style.getPropertyValue('--mobile-screen-bottom')) || 0);
      let right = bar.left, top;
      if (right - edge >= joystick.width + padding + gap) {
        const rail = document.getElementById('hudLeftRail');
        const candidates = [ui.querySelector('.player-card'), ...rail.children].filter(visible);
        top = Math.max(padding, ...candidates.map(el => el.getBoundingClientRect().bottom));
      } else {
        const interact = document.getElementById('interactButton').getBoundingClientRect();
        right = interact.left;
        top = bar.bottom + gap;
      }
      const left = Math.max(edge + padding, (edge + right - joystick.width) / 2);
      const y = Math.max(padding, Math.min(floor - padding - joystick.height, (top + floor - joystick.height) / 2));
      ui.style.setProperty('--mobile-joystick-x', Math.round(left) + 'px');
      ui.style.setProperty('--mobile-joystick-y', Math.round(y) + 'px');
      if (!ui.classList.contains('joystick-centered')) ui.classList.add('joystick-centered');
    }
    const joystickResize = new ResizeObserver(queueJoystick);
    for (const id of ['questTracker', 'hudLeftRail', 'actionDock', 'spellbar', 'interactButton']) joystickResize.observe(document.getElementById(id));
    const joystickChanges = new MutationObserver(queueJoystick);
    for (const el of [ui, ui.querySelector('.movement-controls'), document.getElementById('questTracker')]) {
      joystickChanges.observe(el, { attributes: true, attributeFilter: ['hidden', 'class', 'data-hud-hidden'] });
    }
    function sync() {
      stop(); setOpen(false, false);
      const mobile = active();
      ui.classList.toggle('mobile-hud', mobile);
      for (const { el, anchor } of moved) {
        if (mobile) menu.append(el); else anchor.after(el);
      }
      document.getElementById('spellbar').setAttribute('aria-label', mobile
        ? 'Czary — przesuń pasek w bok, aby zobaczyć kolejne'
        : 'Dwa paski czarów: 1–0, minus, równa się oraz F1–F12');
      visualSize();
    }
    const chatObserver = new MutationObserver(() => {
      chatButton.setAttribute('aria-expanded', String(!chatForm.hidden));
      ui.classList.toggle('mobile-chat-open', !chatForm.hidden);
      if (!chatForm.hidden) setOpen(false, false);
    });
    chatObserver.observe(chatForm, { attributes: true, attributeFilter: ['hidden'] });
    chatButton.setAttribute('aria-expanded', 'false');
    media.addEventListener('change', sync);
    root.addEventListener('resize', () => { stop(); visualSize(); });
    root.visualViewport?.addEventListener('resize', visualSize);
    root.visualViewport?.addEventListener('scroll', visualSize);
    sync();
    return { blocksControls: () => active() && !menu.hidden };
  }
  root.BractwoMobile = { active, create };
})(globalThis);
