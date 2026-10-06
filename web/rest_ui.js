/* Small rest chooser; progress stays above the character in the world. */
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
    const shortCooldown = seconds(p.rest_short_remaining), longCooldown = seconds(p.rest_long_remaining);
    const wait = seconds(p.rest_block_remaining);
    const alive = !!player && p.hp > 0 && p.alive !== false;
    const reason = p.rest_block_reason || '';
    const longNeedsCity=!!rules.long_safe_only,longPlaceAllowed=!longNeedsCity||p.rest_safe===true;
    const blocked = !alive || wait > 0 || !!reason;
    let restriction = !alive ? reasons.dead : reason ? (reasons[reason] || reason) : '';
    if (wait) restriction = (restriction || 'Przerwa po walce') + ` — jeszcze ${wait} s.`;
    return {
      active, kind: rest.kind, remaining: seconds(rest.remaining), shortCooldown, longCooldown,
      progress: active ? Math.max(0, Math.min(1, 1 - Number(rest.remaining) / Math.max(1, Number(rest.total) || 1))) : 0,
      shortSeconds: seconds(rules.short_seconds || 10), longSeconds: seconds(rules.long_seconds || 30),
      canShort: !blocked && !active && !shortCooldown, canLong: !blocked && !active && !longCooldown && longPlaceAllowed,
      safe: p.rest_safe === true, longNeedsCity, longPlaceAllowed, restriction,
      shortRestriction: restriction || (shortCooldown?`Krótki odpoczynek dostępny za ${shortCooldown} s.`:''),
      longRestriction: restriction || (!longPlaceAllowed?'Długi odpoczynek jest dostępny tylko w mieście.':longCooldown?`Długi odpoczynek dostępny za ${longCooldown} s.`:''),
      hitDice:p.rest_resources?.find(r=>r.id==='hit_dice')
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
    const toggle = button('restMenuButton', '', () => open());
    const icon = el('span', null, '☾');
    toggle.append(el('kbd', null, 'R'), icon, el('small', null, 'Odpoczynek'));
    toggle.className = 'rest-launcher'; toggle.title = 'Wybierz odpoczynek';
    toggle.setAttribute('aria-label', 'Odpoczynek'); toggle.dataset.mobileLabel = 'Odpoczynek';
    toggle.setAttribute('aria-controls','restMenu');toggle.setAttribute('aria-expanded','false');
    const menu=el('section','restMenu');menu.hidden=true;menu.setAttribute('role','dialog');menu.setAttribute('aria-label','Wybierz odpoczynek');
    const head=el('header');head.append(el('strong',null,'Odpoczynek'),button('restMenuClose','×',close));
    const shortButton=button('restShortButton','',()=>open('short')),longButton=button('restLongButton','',()=>open('long'));
    const shortInfo=el('small','restShortInfo'),longInfo=el('small','restLongInfo'),restriction=el('p','restRestriction');
    const wizardButton=button('restWizardBook','Przygotuj czary z księgi…',()=>{close();h.openBook?.('prepare');});wizardButton.hidden=true;
    menu.append(head,shortButton,shortInfo,longButton,longInfo,wizardButton,restriction);ui.append(menu);
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
      if(!menu.hidden)positionMenu();
    }
    function positionMenu(){const r=toggle.getBoundingClientRect(),width=menu.getBoundingClientRect().width,height=menu.getBoundingClientRect().height;menu.style.left=Math.max(8,Math.min(innerWidth-width-8,r.right-width))+'px';menu.style.top=Math.max(8,r.top-height-8)+'px';}
    root.addEventListener('resize', () => requestAnimationFrame(positionButton));
    const status = el('p', 'restStatus'); status.className = 'sr-only'; status.setAttribute('role', 'status');
    ui.append(status);
    function close(){menu.hidden=true;toggle.setAttribute('aria-expanded','false');}
    document.addEventListener('pointerdown',event=>{if(!menu.hidden&&!menu.contains(event.target)&&!toggle.contains(event.target))close();},true);
    document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!menu.hidden){close();event.preventDefault();event.stopPropagation();}},true);
    function open(kind) {
      const { player, world } = h.state();
      if (!player) return;
      const m = model(player, world.rest_rules);
      if (m.active) { close();h.send({ type: 'rest_cancel' }); return; }
      if(kind!=='short'&&kind!=='long'){const show=menu.hidden;h.prepare?.();h.stop?.();menu.hidden=!show;toggle.setAttribute('aria-expanded',String(show));render();return;}
      const allowed=kind==='short'?m.canShort:m.canLong;
      if(!allowed){h.notice?.(kind==='short'?m.shortRestriction:m.longRestriction);return;}
      close();h.prepare?.();h.stop?.();
      h.send({ type: 'rest', kind });
    }
    function render() {
      const { player, world } = h.state(), m = model(player, world.rest_rules);
      positionButton();
      toggle.classList.toggle('rest-active', m.active);
      const cooldown=m.longPlaceAllowed?Math.min(m.shortCooldown,m.longCooldown):m.shortCooldown,coolingDown=!m.active&&cooldown>0;
      toggle.classList.toggle('rest-cooldown', coolingDown);
      toggle.disabled = !player;
      icon.textContent = coolingDown ? `${cooldown}s` : '☾';
      toggle.title = m.active ? `R · Przerwij odpoczynek — ${m.remaining} s` : `R · krótki (${m.shortSeconds} s); Shift+R · długi (${m.longSeconds} s${m.longNeedsCity?', w mieście':''})`;
      toggle.setAttribute('aria-label', m.active ? 'Przerwij odpoczynek' : 'Wybierz krótki lub długi odpoczynek');
      toggle.dataset.mobileLabel = m.active ? 'Przerwij odpoczynek' : 'Odpoczynek';
      shortButton.textContent=`Krótki · ${m.shortSeconds} s · R${m.shortCooldown?' · za '+m.shortCooldown+' s':''}`;shortButton.disabled=!m.canShort;shortButton.title=m.shortRestriction;
      shortInfo.textContent='Leczenie z kości zdrowia'+(m.hitDice?` (${m.hitDice.remaining}/${m.hitDice.maximum})`:'')+', część użyć zdolności i dostępne odzyskanie many.';
      longButton.textContent=`Długi · ${m.longSeconds} s · Shift+R${m.longCooldown?' · za '+m.longCooldown+' s':''}`;longButton.disabled=!m.canLong;longButton.title=m.longRestriction;
      wizardButton.hidden=!root.BractwoWizardBookUI?.book(player);wizardButton.disabled=!player?.alive||!h.openBook;
      longInfo.textContent=(m.longNeedsCity?'Tylko w mieście: ':'')+'Całe HP i mana oraz wszystkie zasoby odpoczynku.';
      restriction.textContent=m.restriction||(!m.longPlaceAllowed?'Wróć do miasta, aby rozpocząć długi odpoczynek.':'');restriction.hidden=!restriction.textContent;
      if(m.active)close();else if(!menu.hidden)positionMenu();
      const announcement = m.active ? 'Trwa odpoczynek. Postęp jest nad postacią. Ruch lub przycisk Odpoczynek przerywa regenerację.' : coolingDown ? 'Odpoczynek się odnawia. Pozostały czas jest na przycisku.' : '';
      if (status.textContent !== announcement) status.textContent = announcement;
    }
    return { open, close, render, blocksControls: () => false };
  }
  const api = { model, create }; root.BractwoRestUI = api;
  if (typeof module !== 'undefined') module.exports = api;
})(globalThis);
