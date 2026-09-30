/* Lightweight runtime utilities: no graphics settings or network dependencies. */
(function (root) {
  'use strict';
  class SpatialIndex {
    constructor(items = [], cellSize = 512) {
      this.size = cellSize; this.cells = new Map(); this.lastVisited = 0;
      for (const item of items) {
        for (let x = Math.floor(item.left / cellSize); x <= Math.floor(item.right / cellSize); x++) {
          for (let y = Math.floor(item.top / cellSize); y <= Math.floor(item.bottom / cellSize); y++) {
            const key = `${item.floor || 0}:${x}:${y}`;
            if (!this.cells.has(key)) this.cells.set(key, []);
            this.cells.get(key).push(item);
          }
        }
      }
    }
    query(left, top, right, bottom, floor = 0) {
      const result = new Set(); this.lastVisited = 0;
      for (let x = Math.floor(left / this.size); x <= Math.floor(right / this.size); x++) {
        for (let y = Math.floor(top / this.size); y <= Math.floor(bottom / this.size); y++) {
          for (const item of this.cells.get(`${floor}:${x}:${y}`) || []) {
            this.lastVisited++;
            if (item.right >= left && item.left <= right && item.bottom >= top && item.top <= bottom) result.add(item);
          }
        }
      }
      return [...result].sort((a, b) => a.order - b.order);
    }
  }
  class SurfaceMap {
    constructor(world) {
      this.world=world;const entries=[];
      for(const path of world.roads||[])for(let i=1;i<path.length;i++){
        const a=path[i-1],b=path[i];entries.push({kind:'road',a,b,order:entries.length,left:Math.min(a[0],b[0])-34,top:Math.min(a[1],b[1])-34,right:Math.max(a[0],b[0])+34,bottom:Math.max(a[1],b[1])+34});
      }
      for(const p of world.terrain||[])entries.push({kind:'patch',p,order:entries.length,left:p.x,top:p.y,right:p.x+p.w,bottom:p.y+p.h});
      this.index=new SpatialIndex(entries);
    }
    at(x,y,floor=0){
      if(floor)return 'stone';
      if((this.world.cities||[]).some(c=>Math.hypot(x-c.x,y-c.y)<205))return 'stone';
      const entries=this.index.cells.get(`0:${Math.floor(x/512)}:${Math.floor(y/512)}`)||[];
      for(const e of entries)if(e.kind==='road'){
        const dx=e.b[0]-e.a[0],dy=e.b[1]-e.a[1],q=Math.max(0,Math.min(1,((x-e.a[0])*dx+(y-e.a[1])*dy)/Math.max(1,dx*dx+dy*dy)));
        if(Math.hypot(x-e.a[0]-q*dx,y-e.a[1]-q*dy)<=33)return 'path';
      }
      for(let i=entries.length-1;i>=0;i--){const e=entries[i];if(e.kind==='patch'){const p=e.p;if(root.BractwoWorldGeometry?.patchAt(p,x,y)??(((x-p.x-p.w/2)/(p.w/2))**2+((y-p.y-p.h/2)/(p.h/2))**2<=1))return p.kind;}}
      if(x<3200&&y<2304){if(x>1720&&x<2220&&y>1370)return 'mud';if(x>2250)return 'stone';if(y<900&&x<1400)return 'forest';return 'grass';}
      const r=root.BractwoWorldGeometry?.regionAt(this.world,x,y)||(this.world.regions||[]).find(r=>!r.points?.length&&x>=r.x&&x<r.x+r.w&&y>=r.y&&y<r.y+r.h);
      return ({forest:'forest',swamp:'mud',desert:'sand',snow:'snow',lava:'ash',obsidian:'ash',mountain:'stone',ruins:'stone'})[r?.biome]||'grass';
    }
    roads(left,top,right,bottom){return this.index.query(left,top,right,bottom).filter(e=>e.kind==='road');}
  }
  class FrameRateMeter {
    constructor() { this.reset(); }
    reset() { this.started = null; this.frames = 0; }
    sample(now) {
      if (this.started === null) { this.started = now; return null; }
      this.frames++;
      const elapsed = now - this.started;
      if (elapsed < 500) return null;
      const result = { fps: Math.round(this.frames * 1000 / elapsed), ms: elapsed / this.frames };
      this.started = now; this.frames = 0; return result;
    }
  }
  class MotionTrack {
    constructor() { this.points = []; this.result = { x: 0, y: 0 }; }
    push(x, y, time, floor = 0) {
      const last = this.points[this.points.length - 1];
      if (last && (last.floor !== floor || Math.hypot(last.x - x, last.y - y) > 450 || time < last.time)) this.points.length = 0;
      if (last && time === last.time) this.points.pop();
      this.points.push({ x, y, time, floor });
      if (this.points.length > 6) this.points.shift();
    }
    sample(time) {
      const points = this.points; if (!points.length) return this.result;
      let a = points[0], b = a;
      for (let i = 1; i < points.length; i++) { b = points[i]; if (b.time >= time) break; a = b; }
      const t = b.time > a.time ? Math.max(0, Math.min(1, (time - a.time) / (b.time - a.time))) : 0;
      this.result.x = a.x + (b.x - a.x) * t; this.result.y = a.y + (b.y - a.y) * t;
      return this.result;
    }
  }
  function mergeOwner(previous, entry, enabled) {
    return enabled && previous && String(previous.id) === String(entry.id) ? { ...previous, ...entry } : entry;
  }
  function hitActor(visuals, x, y, myId, floor, scale = 1) {
    let selected = null, best = Infinity;
    for (const v of visuals) {
      const e = v.entity;
      if (e.is_companion || e.hp <= 0 || e.alive === false || (e.floor || 0) !== floor || (v.kind === 'p' && String(e.id) === String(myId))) continue;
      const tall = e.kind === 'dragon' || e.kind === 'dragon_lord' || e.kind === 'demon' || e.kind === 'abyss_walker' || /lord|queen|ancient/.test(e.kind || '');
      const size = Number(e.size)||1;
      const d = Math.hypot(v.x - x, v.y - (tall ? 38 : 22)*size - y);
      if (d < (tall ? 50 : 36)*size / Math.min(1, scale) && d < best) { selected = v; best = d; }
    }
    return selected;
  }
  const HOTBAR_ROW_SIZE=12,HOTBAR_PAGE_SIZE=24;
  const HOTBAR_KEYS=['Digit1','Digit2','Digit3','Digit4','Digit5','Digit6','Digit7','Digit8','Digit9','Digit0','Minus','Equal',...Array.from({length:12},(_,i)=>'F'+(i+1))];
  function displayHotbar(player) { return player?.grouped_hotbar||player?.hotbar||[]; }
  function hotbarGroupForSpell(id,world) {
    return Object.entries(world?.hotbar_groups||{}).find(([,group])=>group.members?.includes(id))?.[0]||id;
  }
  function spellCostText(spec,player) {
    const s=spellProfile(spec,player);if(!s)return '';
    if(s.already_active)return 'Aktywna postać';
    if(s.resource_cost>0)return `${s.resource_name||'Użycia'}: koszt ${s.resource_cost} · pozostało ${s.uses_remaining??0}/${s.uses_maximum??0}`;
    if(s.resource_cost===0&&!spellMana(s,player))return 'Bez many i użyć przemiany';
    return spellMana(s,player)?`${spellMana(s,player)} many`:'Bez many';
  }
  function hotbarPageCount(bar) { return Math.max(1,Math.ceil((bar?.length||0)/HOTBAR_PAGE_SIZE)); }
  function hotbarKey(bar,page,slot) { return Array.isArray(bar)&&Number.isInteger(page)&&page>=0&&Number.isInteger(slot)&&slot>=0&&slot<HOTBAR_PAGE_SIZE?bar[page*HOTBAR_PAGE_SIZE+slot]||'':''; }
  function hotbarSlotForCode(code) { return HOTBAR_KEYS.indexOf(code); }
  function hotbarLabel(index,withBank=true) { const slot=index%24;const label=slot<12?['1','2','3','4','5','6','7','8','9','0','-','='][slot]:'F'+(slot-11);return (withBank&&index>=24?'Zestaw '+(Math.floor(index/24)+1)+' · ':'')+label; }
  function formatEffectTime(effect) {
    if(effect.remaining===null||effect.remaining===undefined)return 'aktywne';
    const seconds=Math.max(0,Math.ceil(Number(effect.remaining)||0));
    const rounds=Math.max(0,Math.ceil(Number(effect.rounds)||0));
    if(seconds>=60)return `${Math.floor(seconds/60)}:${String(seconds%60).padStart(2,'0')} · ${rounds} r.`;
    return `${seconds} s · ${rounds} r.`;
  }
  function statusAction(effect,player,target=null) {
    if(!effect||!player)return null;
    const other=!!target,ally=other&&target.party_id&&target.party_id===player.party_id;
    const action=effect.escape_action_id||(effect.escape_action?'escape_restraint':'');
    let packet,label,range=Infinity;
    if(action==='wake'){
      if(effect.spell_id!=='sleep'||!ally||target.alive===false||target.hp<=0)return null;
      packet={type:'circle_spell_action',action,target_id:target.id};label='Obudź sojusznika · akcja';range=32;
    }else if(action==='escape_web'||action==='escape_whirlpool'){
      if(other)return null;
      packet={type:'circle_spell_action',action};label=action==='escape_web'?'Wyrwij się · akcja':'Wydostań się z wiru · akcja';
    }else if(action==='escape_restraint'){
      if(other&&!ally)return null;
      packet={type:'escape_restraint'};if(other)packet.target_id=target.id;
      label=other?'Uwolnij sojusznika · akcja':'Wyrwij się · akcja';range=80;
    }else return null;
    const tooFar=other&&((target.floor||0)!==(player.floor||0)||Math.hypot(target.x-player.x,target.y-player.y)>range);
    const unable=(player.status_effects||[]).some(e=>['paralyzed','unconscious','sleep_pending','stunned','stinking_poison'].includes(e.id));
    return {packet,label,disabled:player.alive===false||player.hp<=0||player.action_remaining>0||unable||tooFar,
      hint:tooFar?'Podejdź do sojusznika.':''};
  }
  function manaBudgetText(budget) {
    if(budget?.progression==='per_level') {
      const bonus=budget.bonus?` + ${budget.bonus} premii`:'';
      const next=budget.next_level_gain>0?` Następny poziom: +${budget.next_level_gain} many.`:'';
      return `Pełna pula: ${budget.base} many${bonus}. Wspólna mana.${next}`;
    }
    if(!budget?.slots?.length)return 'Mana na zdolności klasy.';
    const slots=budget.slots.map((n,i)=>`${n}× krąg ${i+1}`).join(' + ');
    return `Pełna pula: ${budget.base} many${budget.bonus?` + ${budget.bonus} premii`:''}, odpowiednik ${slots}. Wspólna mana: proporcje używanych kręgów możesz zmieniać.`;
  }
  function spellProfile(spec,player) {
    if(!spec)return spec;
    return {...spec,...(player?.spell_profiles?.[spec.id]||{})};
  }
  function spellGate(spec,player) {
    const required=Number(player?.spell_profiles?.[spec?.id]?.required_level??spec?.required_level);if(Number.isFinite(required))return required;
    const cls=player?.class_id;
    if(spec?.class_levels?.[cls]!==undefined)return Number(spec.class_levels[cls]);
    if(cls==='ranger'&&spec?.circle>0)return spec.circle===1?1:(spec.circle-1)*20;
    return Number(spec?.min_level)||1;
  }
  function concentrationWarning(spec,player,spells={}) {
    const current=player?.concentration;
    if(!spec?.concentration||!current||current===spec.id)return '';
    return (spec.kind==='weapon_trigger'?'Po trafieniu zastąpi: ':'Zastąpi: ')+(spells[current]?.name||current);
  }
  function spellMana(spec,player) {
    const s=spellProfile(spec,player);
    return s?.recast&&player?.concentration===s.id?0:Number(s?.mana)||0;
  }
  function spellUsable(spec,player) {
    const s=spellProfile(spec,player);
    if(!s||!player||player.hp<=0||player.alive===false||s.available===false||s.already_active)return false;
    if(s.kind==='wizard_feature'&&(s.action==='bonus'?player.bonus_remaining>0:player.action_remaining>0))return false;
    if(s.kind==='shape'&&player.form||s.kind==='reaction'||s.kind==='weapon_trigger'&&player.ensnaring_armed)return true;
    if(player.form&&!s.cast_in_form&&!['druid_circle','beast_action'].includes(s.kind))return false;
    return !(player.spell_cooldowns?.[s.id]>0)&&player.mana>=spellMana(s,player)&&(s.resource_cost===0||s.uses_remaining===undefined||s.uses_remaining>=(s.resource_cost||1));
  }
  function queuedSpellLabel(spec,player) {
    if(!spec?.id||player?.queued_spell!==spec.id)return '';
    const remaining=Math.max(0,Number(player.action_remaining)||0);
    return remaining>0?`Za ${remaining.toFixed(1)} s`:'W kolejce';
  }
  function combatSummary(roll) {
    if (!roll || !roll.id) return "";
    const who=roll.target_name||'',name=roll.action||'';
    if(roll.check==='save'&&roll.action?.includes('Powalenie'))return `${name} · ${who}: k20 ${roll.roll} + ${roll.bonus} / ST ${roll.defense} · ${roll.saved?'utrzymana równowaga':'powalenie'}`;
    if(roll.graze)return `${name} · ${who}: pudło · Draśnięcie → ${roll.damage} obr.`;
    if(roll.check==='healing')return `${name} · ${who}: ${roll.damage_dice} → +${Math.round(roll.healing||0)}`;
    if(roll.check==='automatic')return `${name} · ${who}: ${roll.damage_dice||''} → ${roll.immune?'odporność':roll.damage+' obr.'}`;
    const rolls=roll.rolls||[roll.roll];
    const die=roll.disadvantage||roll.advantage?`k20 [${rolls.join(', ')}] → ${roll.roll}`:`k20 ${roll.roll}`;
    const saving=roll.check==='save'||roll.check==='concentration'||roll.check==='escape';
    const check=`${die} ${roll.bonus<0?'−':'+'} ${Math.abs(roll.bonus||0)} = ${roll.total} / ${saving?'ST':'KP'} ${roll.defense}`;
    if(roll.check==='escape')return `${name} · ${who}: ${check} · ${roll.saved?'uwolnienie':'pnącza trzymają'} · akcja zużyta`;
    if(roll.check==='concentration')return `${check} · koncentracja ${roll.saved?'utrzymana':'przerwana'}`;
    const result=roll.check==='save'?(roll.saved?(roll.save_half?'obrona · połowa':'obrona · brak obrażeń'):'nieudana obrona'):roll.shielded?'TARCZA':roll.critical?'KRYTYK':roll.hit?'trafienie':'PUDŁO';
    return `${name} · ${who}: ${check} · ${result}${roll.hit?` · ${roll.damage_dice} → ${roll.damage} obr.`:''}`;
  }
  // Manual touch scrolling works even while another finger owns the joystick.
  // Keep taps on their button; capture the pointer only once it becomes a swipe.
  function bindTouchScroll(scroller, enabled = () => true) {
    let gesture = null, lastSwipeEnd = -Infinity;
    function finish(event, canceled = false) {
      if (!gesture || (event && event.pointerId !== gesture.id)) return;
      const old = gesture; gesture = null;
      if (old.dragging || canceled) lastSwipeEnd = Date.now();
      try { if (scroller.hasPointerCapture?.(old.id)) scroller.releasePointerCapture(old.id); } catch {}
    }
    function move(event) {
      if (!gesture || event.pointerId !== gesture.id) return;
      if (!enabled()) { finish(event, true); return; }
      const dx = event.clientX - gesture.x;
      if (!gesture.dragging && Math.abs(dx) <= 12) return;
      if (!gesture.dragging) {
        gesture.dragging = true;
        try { scroller.setPointerCapture(event.pointerId); } catch {}
      }
      event.preventDefault();
      scroller.scrollLeft = Math.max(0, Math.min(scroller.scrollWidth - scroller.clientWidth, gesture.scrollX - dx));
    }
    scroller.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'touch' || gesture || !enabled() || scroller.scrollWidth <= scroller.clientWidth) return;
      gesture = { id: event.pointerId, x: event.clientX, scrollX: scroller.scrollLeft, dragging: false };
    }, true);
    scroller.addEventListener('pointermove', move, { capture: true, passive: false });
    scroller.addEventListener('pointerup', event => { move(event); finish(event); }, true);
    scroller.addEventListener('pointercancel', event => finish(event, true), true);
    scroller.addEventListener('lostpointercapture', event => {
      // A child loses implicit capture when the viewport takes over a swipe.
      if (event.target === scroller) finish(event, true);
    });
    scroller.addEventListener('click', event => {
      const fromTouch = event.pointerType === 'touch' || event.sourceCapabilities?.firesTouchEvents ||
        (!event.pointerType && event.detail > 0);
      if (fromTouch && Date.now() - lastSwipeEnd < 800) { event.preventDefault(); event.stopPropagation(); }
    }, true);
    scroller.addEventListener('contextmenu', event => {
      if (gesture?.dragging) { event.preventDefault(); event.stopPropagation(); finish(null, true); }
    }, true);
    root.addEventListener?.('blur', () => finish(null, true));
    root.document?.addEventListener('visibilitychange', () => { if (root.document.hidden) finish(null, true); });
    return { cancel: () => finish(null, true) };
  }
  // A second finger may produce PointerEvents without a compatibility click.
  // Tap detection observes movement and capture loss without owning the scroll.
  function bindTouchTap(button, activate, scrollParent = () => null) {
    const touches = new Map(); let lastTouchEnd = -Infinity;
    const scrollPosition = el => [el?.scrollLeft || 0, el?.scrollTop || 0];
    function moved(event, touch) {
      const [x, y] = scrollPosition(touch.scroller);
      if (Math.hypot(event.clientX - touch.x, event.clientY - touch.y) > 12 ||
          Math.abs(x - touch.scrollX) > 2 || Math.abs(y - touch.scrollY) > 2) touch.moved = true;
      return touch.moved;
    }
    button.addEventListener('pointerdown', event => {
      if (event.pointerType !== 'touch' || button.disabled) return;
      const scroller = scrollParent(), [scrollX, scrollY] = scrollPosition(scroller);
      touches.set(event.pointerId, { x: event.clientX, y: event.clientY, scroller, scrollX, scrollY, moved: false });
    });
    button.addEventListener('pointermove', event => {
      const touch = touches.get(event.pointerId); if (touch) moved(event, touch);
    });
    button.addEventListener('pointerup', event => {
      const touch = touches.get(event.pointerId); if (!touch) return;
      touches.delete(event.pointerId); lastTouchEnd = Date.now();
      const rect = button.getBoundingClientRect();
      if (button.disabled || moved(event, touch) || event.clientX < rect.left || event.clientX > rect.right ||
          event.clientY < rect.top || event.clientY > rect.bottom) return;
      event.preventDefault(); activate(event);
    });
    const cancel = event => {
      if (touches.delete(event.pointerId)) lastTouchEnd = Date.now();
    };
    button.addEventListener('pointercancel', cancel);
    button.addEventListener('lostpointercapture', cancel);
    button.addEventListener('contextmenu', () => {
      if (touches.size) lastTouchEnd = Date.now(); touches.clear();
    });
    button.addEventListener('click', event => {
      const fromTouch = event.pointerType === 'touch' || event.sourceCapabilities?.firesTouchEvents ||
        (!event.pointerType && event.detail > 0 && Date.now() - lastTouchEnd < 800);
      if (fromTouch) { event.preventDefault(); return; }
      if (!button.disabled) activate(event);
    });
  }
  // Keep beams crossing the viewport, broad server areas and high lightning
  // columns visible even when their origin is outside the camera. No timers or
  // effect state are changed by culling; moving the camera can reveal them.
  function effectVisible(effect, view) {
    const x=Number(effect.x)||0,y=Number(effect.y)||0;
    const tx=Number.isFinite(effect.target_x)?effect.target_x:x;
    const ty=Number.isFinite(effect.target_y)?effect.target_y:y;
    const radius=Math.max(0,Number(effect.radius)||0);
    let left=Math.min(x,tx)-radius,right=Math.max(x,tx)+radius;
    let top=Math.min(y,ty)-radius,bottom=Math.max(y,ty)+radius;
    const bounds=effect.area?.bounds;
    if(Array.isArray(bounds)&&bounds.length===4&&bounds.every(Number.isFinite)){
      left=Math.min(left,bounds[0]);top=Math.min(top,bounds[1]);
      right=Math.max(right,bounds[2]);bottom=Math.max(bottom,bounds[3]);
    }
    for(const target of effect.targets||[]){
      if(!Number.isFinite(target.x)||!Number.isFinite(target.y))continue;
      left=Math.min(left,target.x);right=Math.max(right,target.x);
      top=Math.min(top,target.y);bottom=Math.max(bottom,target.y);
    }
    return right+100>=view.left&&left-100<=view.right&&bottom+100>=view.top&&top-360<=view.bottom;
  }
  const api = { SurfaceMap, SpatialIndex, FrameRateMeter, MotionTrack, mergeOwner, hitActor, effectVisible, HOTBAR_ROW_SIZE, HOTBAR_PAGE_SIZE, displayHotbar, hotbarGroupForSpell, spellCostText, hotbarSlotForCode, hotbarLabel, hotbarPageCount, hotbarKey, formatEffectTime, statusAction, manaBudgetText, spellProfile, spellGate, concentrationWarning, spellMana, spellUsable, queuedSpellLabel, combatSummary, bindTouchTap, bindTouchScroll };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BractwoRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
