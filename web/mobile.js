/* Phone HUD: existing game controls, separate presentation and no combat rules. */
(function (root) {
  'use strict';
  const query = '(max-width: 700px), (max-width: 1100px) and (max-height: 600px), (pointer: coarse) and (max-width: 1400px) and (max-height: 900px)';
  const media = root.matchMedia(query);
  const active = () => media.matches;
  const COMPACT_SCALE = 0.74;
  function uiScale(visualScale = root.visualViewport?.scale || 1) {
    // Some Android browsers shrink the normal viewport then reset it in
    // fullscreen. Compensate that shrink once, never a user's zoom above 1.
    const visual = Math.max(0.5, Math.min(1, Number(visualScale) || 1));
    return COMPACT_SCALE / visual;
  }
  function worldScale(width, height, visualScale) {
    // Orientation is a profile; browser bars/fullscreen height are not.
    return (width > height ? 0.95 : 1) * 0.85 * uiScale(visualScale);
  }
  function refreshViewport() {
    document.getElementById('gameUI')?.style.setProperty('--mobile-unit', uiScale()+'px');
  }
  refreshViewport();

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
      refreshViewport();
      const view = root.visualViewport;
      ui.style.setProperty('--mobile-visual-height', (view?.height || innerHeight) + 'px');
      ui.style.setProperty('--mobile-visual-top', (view?.offsetTop || 0) + 'px');
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
    document.addEventListener('fullscreenchange', visualSize);
    document.addEventListener('webkitfullscreenchange', visualSize);
    root.visualViewport?.addEventListener('scroll', visualSize);
    sync();
    return { blocksControls: () => active() && !menu.hidden };
  }
  root.BractwoMobile = { active, create, uiScale, worldScale, refreshViewport };
})(globalThis);
