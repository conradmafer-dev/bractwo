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

    // In portrait, all pending choices share one scrollable column.
    const rail = document.getElementById('hudLeftRail');
    const advancement = document.getElementById('advancementChoice');
    const scrollControl = document.createElement('input');
    scrollControl.id = 'mobileRailScroll'; scrollControl.type = 'range';
    scrollControl.min = '0'; scrollControl.max = '1'; scrollControl.step = '1'; scrollControl.value = '0';
    scrollControl.hidden = true; scrollControl.setAttribute('orient', 'vertical');
    scrollControl.setAttribute('aria-orientation', 'vertical');
    scrollControl.setAttribute('aria-label', 'Przewiń zadania i wybory rozwoju');
    scrollControl.setAttribute('aria-controls', 'hudLeftRail');
    scrollControl.title = 'Przeciągnij, aby przewinąć panel'; ui.append(scrollControl);
    scrollControl.addEventListener('input', () => { rail.scrollTop = Number(scrollControl.value); });
    scrollControl.addEventListener('keydown', event => event.stopPropagation());
    scrollControl.addEventListener('pointerdown', () => stop());
    let railQueued = false;
    function queueRail() {
      if (railQueued) return;
      railQueued = true;
      requestAnimationFrame(() => { railQueued = false; updateRail(); });
    }
    function updateRail() {
      const portrait = active() && innerWidth <= 700 && innerWidth < innerHeight;
      const parent = portrait ? rail : ui;
      if (advancement.parentElement !== parent) parent.append(advancement);
      const maximum = Math.max(0, rail.scrollHeight - rail.clientHeight);
      const visible = portrait && !ui.hidden && maximum > 1;
      if (scrollControl.hidden === visible) scrollControl.hidden = !visible;
      if (!visible) return;
      const rect = rail.getBoundingClientRect();
      scrollControl.style.left = (rect.right + 3) + 'px';
      scrollControl.style.top = rect.top + 'px';
      scrollControl.style.height = rect.height + 'px';
      scrollControl.max = String(maximum); scrollControl.value = String(Math.round(rail.scrollTop));
      scrollControl.setAttribute('aria-valuetext', Math.round(100 * rail.scrollTop / maximum) + '% panelu');
    }
    rail.addEventListener('scroll', queueRail, { passive: true });
    const railResize = new ResizeObserver(queueRail);
    railResize.observe(rail);
    for (const panel of [...rail.children, advancement]) railResize.observe(panel);
    const railChanges = new MutationObserver(mutations => {
      if (mutations.some(m => m.type === 'attributes' || [...m.addedNodes, ...m.removedNodes].some(n => n.nodeType === 1))) queueRail();
    });
    railChanges.observe(ui, { subtree: true, childList: true, attributes: true, attributeFilter: ['hidden', 'data-hud-hidden'] });

    function visualSize() {
      refreshViewport();
      const view = root.visualViewport;
      ui.style.setProperty('--mobile-visual-height', (view?.height || innerHeight) + 'px');
      ui.style.setProperty('--mobile-visual-top', (view?.offsetTop || 0) + 'px');
      queueRail();
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
