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
      if((this.world.cities||[]).some(c=>Math.hypot(x-c.x,y-c.y)<(c.paving_radius||205)))return 'stone';
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
    if(s.kind==='martial_feature')return `${s.martial_role==='reaction'?'Reakcja':'Przygotowanie'} · 1 kość przewagi przy wykonaniu · pozostało ${s.uses_remaining??0}/${s.uses_maximum??0}`;
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
  function experienceProgress(player) {
    const progress=Math.max(0,Number(player?.xp)||0);
    const needed=Math.max(1,Number(player?.xp_next)||1);
    const start=Math.max(0,Number(player?.xp_level_start)||0);
    const total=Math.max(0,Number(player?.xp_total??(start+progress))||0);
    const nextTotal=Math.max(0,Number(player?.xp_next_total??(start+needed))||0);
    return {total,nextTotal,progress,needed,ratio:Math.max(0,Math.min(1,progress/needed))};
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
    if(cls==='ranger'&&spec?.circle>0)return spec.circle===1?1:(spec.circle-1)*4+1;
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
    if(s.kind==='martial_feature'){
      if(player.form||player.rest?.kind||player.rest?.remaining>0||player.character_sheet?.martial?.actions_available!==true)return false;
      // Preparing is free; the shared die and reaction are paid on execution.
      // An exhausted warrior can still cancel a previously armed preference.
      return s.armed===true||Number.isFinite(s.uses_remaining)&&s.uses_remaining>=1;
    }
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
  function martialHotbarLabel(spec,player) {
    const s=spellProfile(spec,player);
    return s?.kind==='martial_feature'?`${s.armed?'ON':'OFF'} ${s.uses_remaining??0}/${s.uses_maximum??0}`:'';
  }
  // One presentation for every resolved roll. These functions never roll dice,
  // infer a missing face from the final total, or recalculate combat outcomes.
  const finite = n => typeof n === 'number' && Number.isFinite(n);
  const number = n => finite(n) ? String(Math.round(n * 100) / 100).replace('.', ',') : '—';
  const sum = a => a.reduce((n, v) => n + v, 0);
  const validDice = a => Array.isArray(a) && a.length <= 200 && a.every(n => Number.isInteger(n) && n >= 1 && n <= 1000);
  function diceResult(values, sides) {
    if (!validDice(values) || !values.length || !Number.isInteger(sides) || sides < 1 || values.some(n => n > sides)) return '';
    return `${values.length}k${sides} = ${values.map(number).join(' + ')}${values.length > 1 ? ' = ' + number(sum(values)) : ''}`;
  }
  function numericFormula(parts) {
    if (!parts.length || !parts.every(finite)) return '';
    return number(parts[0]) + parts.slice(1).filter(n => n !== 0).map(n => ` ${n < 0 ? '−' : '+'} ${number(Math.abs(n))}`).join('');
  }
  function baseDie(roll) {
    const match = /^\s*(\d+)k(\d+)(?:\s*([+−-])\s*(\d+))?/i.exec(roll?.damage_dice || '');
    return {sides: Number.isInteger(roll?.damage_sides) ? roll.damage_sides : match ? Number(match[2]) : null,
      modifier: finite(roll?.damage_modifier) ? roll.damage_modifier : match ? (match[3] === '-' || match[3] === '−' ? -1 : 1) * Number(match[4] || 0) : null};
  }
  function checkOutcome(roll) {
    if (roll.check === 'ability') return roll.saved ? 'sukces' : 'niepowodzenie';
    if (roll.check === 'escape') return roll.saved ? 'uwolnienie' : 'pnącza trzymają';
    if (roll.check === 'concentration') return roll.saved ? 'koncentracja utrzymana' : 'koncentracja przerwana';
    if (roll.check === 'save') return roll.action?.includes('Powalenie') ? (roll.saved ? 'utrzymana równowaga' : 'powalenie')
      : roll.saved ? (roll.save_half || roll.potent_cantrip ? 'obrona · połowa' : 'obrona · brak obrażeń') : 'nieudana obrona';
    return roll.graze ? 'pudło · Draśnięcie' : roll.illusory_self ? 'iluzja' : roll.shielded && !roll.hit ? 'TARCZA' : roll.critical ? 'KRYTYK' : roll.hit ? 'trafienie' : 'PUDŁO';
  }
  function checkRollLines(roll) {
    if (!roll || !['attack', 'save', 'ability', 'escape', 'concentration'].includes(roll.check)) return [];
    const lines = [], saving = roll.check !== 'attack';
    if (roll.automatic_failure) return ['Obrona: automatyczne niepowodzenie'];
    const faces = validDice(roll.rolls) && roll.rolls.length ? roll.rolls : Number.isInteger(roll.roll) && roll.roll >= 1 && roll.roll <= 20 ? [roll.roll] : [];
    if (!faces.length) return [checkOutcome(roll)];
    const beforeLucky = roll.lucky ? roll.lucky_previous : roll.roll;
    if (roll.portent) lines.push(`Przepowiednia: 1k20 = ${number(roll.roll)}`);
    else if (faces.length === 1) lines.push(`Rzut: ${diceResult(faces, 20)}`);
    else {
      // Choose only the result the server recorded, including ties.
      const chosen = faces.indexOf(beforeLucky);
      lines.push(`${roll.disadvantage ? 'Utrudnienie' : roll.advantage ? 'Przewaga' : 'Rzuty'}: ` + faces.map((v, i) => `1k20 = ${number(v)}${i === chosen ? ' ✓ wybrany' : ''}`).join(' / '));
    }
    if (!roll.portent && !faces.includes(beforeLucky) && finite(beforeLucky)) lines.push(`Wynik: ${number(roll.disadvantage ? Math.min(...faces) : Math.max(...faces))} → ${number(beforeLucky)}`);
    if (roll.lucky && Number.isInteger(roll.lucky_roll)) lines.push(`Szczęściarz: 1k20 = ${number(roll.lucky_roll)}${roll.roll === roll.lucky_roll && roll.lucky_roll > roll.lucky_previous ? ' ✓ wybrany' : ' · pozostaje ' + number(roll.lucky_previous)}`);
    const bonusDice = (Array.isArray(roll.check_extra_rolls) ? roll.check_extra_rolls : []).filter(g => g && diceResult(g.rolls, g.sides));
    for (const g of bonusDice) lines.push(`${g.name || 'Premia'}: ${diceResult(g.rolls, g.sides)}${g.sign === -1 ? ' (odejmij)' : ''}`);
    const rolledBonus = sum(bonusDice.map(g => sum(g.rolls) * (g.sign === -1 ? -1 : 1)));
    const bonus = finite(roll.bonus) ? roll.bonus : 0;
    const parts = [roll.roll, bonus - rolledBonus, ...bonusDice.map(g => sum(g.rolls) * (g.sign === -1 ? -1 : 1))];
    const label = roll.check === 'attack' ? 'Trafienie' : roll.check === 'ability' ? 'Test' : roll.check === 'concentration' ? 'Koncentracja' : 'Obrona';
    if (finite(roll.roll) && finite(roll.total) && finite(roll.defense)) {
      const calculated = sum(parts), formula = numericFormula(parts);
      // A server adjustment may change total separately (e.g. Precision). Never
      // print a false equality if an older receipt lacks its component dice.
      lines.push(`${label}: ${formula}${Math.abs(calculated - roll.total) < .001 ? '' : ' = ' + number(calculated) + ' · po premii'} → ${number(roll.total)} / ${saving ? 'ST' : 'KP'} ${number(roll.defense)} · ${checkOutcome(roll)}`);
    } else lines.push(checkOutcome(roll));
    return lines;
  }
  function damageRollDetails(roll) {
    if (!roll) return null;
    const base = baseDie(roll), savage = savageAttackDetails(roll);
    const dice = validDice(roll.damage_rolls) && roll.damage_rolls.length ? roll.damage_rolls
      : savage ? savage.sets[savage.chosen].scored : [];
    const groups = [];
    if (dice.length && diceResult(dice, base.sides)) {
      const raw = validDice(roll.raw_damage_rolls) && roll.raw_damage_rolls.length === dice.length ? roll.raw_damage_rolls : dice;
      groups.push({name: roll.damage_maximized ? 'Maksymalne kości' : 'Rzut', sides: base.sides, dice, raw, modifier: base.modifier ?? 0, base: true});
    }
    const explicit = Array.isArray(roll.extra_damage_rolls) ? roll.extra_damage_rolls : [];
    let complete = true;
    for (const g of explicit) {
      if (!g || !diceResult(g.rolls, g.sides)) {complete = false;continue;}
      groups.push({name: (g.name || 'Dodatkowe obrażenia') + (g.maximized ? ' · maksimum' : ''), sides: g.sides, dice: g.rolls, raw: g.rolls, modifier: finite(g.modifier) ? g.modifier : 0});
    }
    // Existing saved receipts remain readable. These are recorded dice, not
    // reconstructed outcomes; unfamiliar extra pools only show the final total.
    if (!explicit.length) {
      for (const [key, name, sides] of [['mark_rolls','Znak łowcy',6],['lunar_rolls','Księżyc',10],['colossus_rolls','Pogromca kolosów',8]]) {
        if (validDice(roll[key]) && roll[key].length) groups.push({name,sides,dice:roll[key],raw:roll[key],modifier:0});
      }
      for (const key of ['extra_rolls','beast_extra_rolls','superiority_rolls']) if (validDice(roll[key]) && roll[key].length && !(key === 'superiority_rolls' && roll.martial_maneuver === 'precision')) complete = false;
    }
    // A constant heal or damage effect has no invented die roll.
    const constant = !dice.length && /^\s*\d+(?:[.,]\d+)?\s*$/.test(roll.damage_dice || '') ? Number(roll.damage_dice.replace(',', '.')) : null;
    if (!groups.length && constant === null && !(Array.isArray(roll.damage_rolls) && !roll.damage_rolls.length && finite(base.modifier))) return null;
    const fixed = groups.some(g => g.base) ? 0 : constant ?? base.modifier ?? 0;
    const parts = groups.length ? [] : [fixed];
    if (groups.length && fixed) parts.push(fixed);
    for (const g of groups) {
      const value = sum(g.dice) + g.modifier;
      // Negative healing bonuses are clamped for each independent pool.
      if (value < 0) parts.push(0);
      else {parts.push(sum(g.dice));if (g.modifier) parts.push(g.modifier);}
    }
    return {groups,parts,total:sum(parts),complete};
  }
  function damageRollLines(roll, skipBase = false) {
    if (!roll || !['attack','save','automatic','healing'].includes(roll.check)) return [];
    if (roll.immune) return ['Obrażenia: 0 · niewrażliwość'];
    if (roll.shielded && !roll.hit) return [];
    if (roll.check === 'attack' && !roll.hit && !roll.graze && !roll.potent_cantrip) return [];
    const healing = roll.check === 'healing', label = healing ? 'Leczenie' : 'Obrażenia';
    const final = healing ? roll.healing : roll.damage;
    if (!finite(final)) return [];
    const lines = [], details = damageRollDetails(roll);
    if (roll.rest_rolls?.length) {
      const draws = roll.rest_rolls.filter(g => g && diceResult([g.value],g.sides));
      for (const [i,g] of draws.entries()) {
        lines.push(`Kość ${i+1}: 1k${g.sides} = ${number(g.first)}${finite(g.reroll) ? ' · Uzdrowiciel: 1k'+g.sides+' = '+number(g.reroll)+' ✓ wybrany' : ''} · ${numericFormula([g.value,g.modifier])} → ${number(g.potential)}`);
      }
      if (draws.length === roll.rest_rolls.length) {
        const parts=draws.map(g=>g.potential),total=sum(parts);
        lines.push(parts.length>1 ? `${label}: ${numericFormula(parts)} → ${number(total)}` : `${label}: ${number(total)}`);
        if(Math.abs(total-final)>.001)lines.push(`Odzyskano: ${number(final)} zdrowia (do pełna)`);
      } else lines.push(`${label}: +${number(final)} zdrowia`);
      return lines;
    }
    if (details) {
      for (const g of details.groups) {
        if (g.base && skipBase) continue;
        const adjusted = g.raw.some((v,i)=>v!==g.dice[i]);
        lines.push(`${g.name}: ${diceResult(g.raw,g.sides)}${adjusted ? ' → '+g.dice.map(number).join(' + ')+(g.dice.length>1?' = '+number(sum(g.dice)):'')+' (styl walki)' : ''}`);
      }
      if (Array.isArray(roll.piercer_reroll) && roll.piercer_reroll.length === 2) {
        const sides = baseDie(roll).sides;
        if (diceResult([roll.piercer_reroll[0]],sides) && diceResult([roll.piercer_reroll[1]],sides)) lines.push(`Przebijacz: 1k${sides} = ${number(roll.piercer_reroll[0])} → 1k${sides} = ${number(roll.piercer_reroll[1])}`);
      }
      if (Number.isInteger(roll.piercer_critical) && diceResult([roll.piercer_critical],baseDie(roll).sides)) lines.push(`Przebijacz · krytyk: ${diceResult([roll.piercer_critical],baseDie(roll).sides)}`);
      if (details.complete) {
        lines.push(details.parts.slice(1).some(n=>n!==0) ? `${label}: ${numericFormula(details.parts)} → ${number(details.total)}` : `${label}: ${number(details.total)}`);
        if(finite(roll.parry_roll)&&finite(roll.parry_sides))lines.push(`Parowanie: 1k${roll.parry_sides} = ${number(roll.parry_roll)} · ${numericFormula([roll.parry_roll,roll.parry_modifier||0])} → ${number(Math.max(0,roll.parry_roll+(roll.parry_modifier||0)))} · blokuje ${number(roll.parry_reduction)} obr.`);
        if (Math.abs(final-details.total) > .001) lines.push(healing ? `Odzyskano: ${number(final)} zdrowia (do pełna)` : `Po obronie i pozostałych efektach: ${number(final)} obr.`);
      } else lines.push(`${label}: ${number(final)}${healing ? ' zdrowia' : ' obr.'}`);
    } else {
      if(roll.damage_dice && /k\d+/.test(roll.damage_dice))lines.push(`Kości: ${roll.damage_dice}`);
      lines.push(`${label}: ${healing ? '+' : ''}${number(final)}${healing ? ' zdrowia' : ' obr.'}`);
    }
    return lines;
  }

  // Display receipts from the server. No dice are rolled in the browser.
  function savageAttackDetails(roll) {
    if (!roll?.id || roll.check !== 'attack' || !roll.hit || roll.savage_attacker !== true) return null;
    const valid = sets => Array.isArray(sets) && sets.length === 2 && sets.every(set =>
      Array.isArray(set) && set.length > 0 && set.length <= 24 &&
      set.every(n => Number.isInteger(n) && n >= 1 && n <= 100)) && sets[0].length === sets[1].length;
    const raw = roll.savage_damage_rolls;
    if (!valid(raw) || ![0, 1].includes(roll.savage_chosen)) return null;
    const scored = valid(roll.savage_scored_rolls) && roll.savage_scored_rolls[0].length === raw[0].length
      ? roll.savage_scored_rolls : raw;
    return {chosen: roll.savage_chosen, sets: raw.map((dice, index) => ({
      dice: [...dice], scored: [...scored[index]], total: scored[index].reduce((a, b) => a + b, 0),
      adjusted: dice.some((n, i) => n !== scored[index][i]), selected: index === roll.savage_chosen
    }))};
  }
  function savageDiceText(set, sides) {
    const raw = set.dice.join(' + '), scored = set.scored.join(' + ');
    const prefix = Number.isInteger(sides) ? `${set.dice.length}k${sides} = ` : '';
    return prefix + (set.adjusted ? `${raw} → ${scored}` : raw) + (set.dice.length > 1 ? ` = ${set.total}` : '');
  }
  function savageAttackSummary(roll) {
    const details = savageAttackDetails(roll);
    return details ? 'Zacięty atak: ' + details.sets.map((set, i) =>
      `Rzut ${i + 1}: ${savageDiceText(set, baseDie(roll).sides)}${set.selected ? ' ✓ wybrany' : ''}`).join(' / ') : '';
  }
  function combatNoticeEntries(player, simulationTime) {
    if (!player) return [];
    const latest = player.last_roll?.id ? player.last_roll : null;
    const recent = (Array.isArray(player.combat_log) ? player.combat_log.slice(-8) : []).filter(roll =>
      roll?.id && Number.isFinite(roll.time) && Number.isFinite(simulationTime) &&
      simulationTime >= roll.time && simulationTime - roll.time < 8);
    if (latest) recent.push(latest);
    // A later shot or a saving throw must not erase the two damage sets.
    // Limit the HUD to the newest feat receipt plus the latest result.
    const savage = recent.filter(roll => savageAttackDetails(roll)).sort((a, b) =>
      (Number(a.time) || 0) - (Number(b.time) || 0)).at(-1);
    return savage ? [savage, ...(latest && String(latest.id) !== String(savage.id) ? [latest] : [])]
      : latest ? [latest] : [];
  }
  const combatNoticeCache = new WeakMap();
  function renderCombatNotice(host, player, simulationTime, session = '') {
    if (!host) return;
    const entries = combatNoticeEntries(player, simulationTime);
    const signature = JSON.stringify([player?.id ?? null, session, entries]);
    if (combatNoticeCache.get(host) === signature) return;
    combatNoticeCache.set(host, signature);
    if (host.hidden !== !entries.length) host.hidden = !entries.length;
    host.classList.toggle('has-savage-roll', entries.some(roll => savageAttackDetails(roll)));
    host.classList.toggle('has-roll-breakdown', !!entries.length);
    host.replaceChildren();
    const doc = host.ownerDocument;
    const node = (tag, cls, text) => {const n = doc.createElement(tag);n.className = cls;if (text !== undefined) n.textContent = text;return n;};
    for (const roll of entries) {
      const details = savageAttackDetails(roll);
      if (!details) {
        const card=node('div','combat-current-result');
        card.append(node('strong','combat-result-heading',[roll.action,roll.target_name].filter(Boolean).join(' · ')));
        for(const text of [...checkRollLines(roll),...damageRollLines(roll)])card.append(node('div','combat-result-line',text));
        if(roll.check==='ward')card.append(node('div','combat-result-line',`Osłona pochłonęła: ${number(roll.absorbed)} obr.`));
        host.append(card);continue;
      }
      const box = node('div', 'savage-receipt');box.dataset.rollId = String(roll.id);
      const header = node('div', 'savage-heading');
      header.append(node('strong', '', 'Zacięty atak'), node('span', 'savage-target', roll.target_name || roll.action || 'Cel'));
      box.append(header);
      for(const text of checkRollLines(roll))box.append(node('div','savage-hit',text));
      const attempts = node('div', 'savage-attempts');
      details.sets.forEach((set, i) => {
        const attempt = node('div', 'savage-attempt' + (set.selected ? ' selected' : ''));
        attempt.dataset.attempt = String(i + 1);attempt.dataset.selected = String(set.selected);
        attempt.append(node('span', 'savage-attempt-name', `Rzut ${i + 1}`),
          node('b', 'savage-dice', savageDiceText(set, baseDie(roll).sides)),
          node('span', 'savage-choice', set.selected ? '✓ wybrany' : ''));
        attempts.append(attempt);
      });
      box.append(attempts);
      for(const text of damageRollLines(roll,true))box.append(node('div','savage-result',text));
      box.title = combatSummary(roll);
      host.append(box);
    }
  }
  function combatSummary(roll) {
    if (!roll || !roll.id) return '';
    const heading=[roll.action,roll.target_name].filter(Boolean).join(' · ');
    const savage=savageAttackSummary(roll);
    const lines=[...checkRollLines(roll),...(savage?[savage]:[]),...damageRollLines(roll,!!savage)];
    if(roll.check==='ward')lines.push(`Osłona pochłonęła: ${number(roll.absorbed)} obr.`);
    return [heading,...lines].filter(Boolean).join(' · ');
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
  const api = { SurfaceMap, SpatialIndex, FrameRateMeter, MotionTrack, mergeOwner, hitActor, effectVisible, HOTBAR_ROW_SIZE, HOTBAR_PAGE_SIZE, displayHotbar, hotbarGroupForSpell, spellCostText, hotbarSlotForCode, hotbarLabel, hotbarPageCount, hotbarKey, formatEffectTime, statusAction, experienceProgress, manaBudgetText, spellProfile, spellGate, concentrationWarning, spellMana, spellUsable, queuedSpellLabel, martialHotbarLabel, combatSummary, diceResult, numericFormula, checkRollLines, damageRollDetails, damageRollLines, savageAttackDetails, savageAttackSummary, combatNoticeEntries, renderCombatNotice, bindTouchTap, bindTouchScroll };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BractwoRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
