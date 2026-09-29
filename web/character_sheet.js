/* Standalone character sheet. No journal, atlas or account data in this window. */
(function(root){'use strict';
  const labels={strength:'Siła',dexterity:'Zręczność',constitution:'Kondycja',intelligence:'Inteligencja',wisdom:'Mądrość',charisma:'Charyzma'};
  const skillNames={melee:'Walka wręcz',distance:'Walka dystansowa',magic:'Magia',shielding:'Obrona'};
  const masteryNames={power:'Potęga',focus:'Skupienie'};
  const signed=n=>Number(n)>=0?'+'+n:String(n), dice=n=>'1k20'+signed(n);
  const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
  function button(text,fn,disabled=false){const e=node('button','',text);e.type='button';e.disabled=disabled;e.addEventListener('click',fn);return e;}
  function image(path,alt=''){const e=node('img');e.src=path;e.alt=alt;e.width=48;e.height=48;return e;}
  function equipmentIcon(item,slot='empty'){
    if(item?.icon)return item.icon;
    if(slot!=='weapon')return `assets/equipment/${['armor','ring','shield'].includes(slot)?slot:'empty'}.svg`;
    // Ordinary weapons are shared between classes; art follows the actual type.
    const type=item?.weapon_type;
    if(type==='focus')return 'assets/equipment/staff.svg';
    if(type==='quarterstaff'||type==='club')return 'assets/equipment/nature_staff.svg';
    if(type==='shortbow'||type==='longbow'||item?.ranged)return 'assets/equipment/bow.svg';
    return `assets/equipment/${!type&&item?.class_ids?.length===1&&item.class_ids[0]==='mage'?'staff':!type&&item?.class_ids?.length===1&&item.class_ids[0]==='druid'?'nature_staff':!type&&item?.class_ids?.length===1&&item.class_ids[0]==='ranger'?'bow':'weapon'}.svg`;
  }
  function create(h){
    const panel=document.getElementById('characterPanel'),content=document.getElementById('characterContent'),tabButtons=[...panel.querySelectorAll('[data-character-tab]')];
    let tab='inventory',signature='',bagPage=0,selectedItem='',restoreFocus=null;
    function close(){const wasOpen=!panel.hidden;panel.hidden=true;root.BractwoInventoryUI?.hide();signature='';if(!wasOpen)return;h.changed?.();if(restoreFocus?.isConnected&&restoreFocus.getClientRects().length)restoreFocus.focus({preventScroll:true});}
    function open(which=tab){restoreFocus=document.activeElement;h.prepare();tab=which;panel.hidden=false;signature='';render();panel.querySelector(`[data-character-tab="${tab}"]`)?.focus({preventScroll:true});h.changed?.();}
    function toggle(which){if(!panel.hidden&&(!which||which===tab))close();else open(which||tab);}
    for(const b of tabButtons)b.addEventListener('click',()=>{tab=b.dataset.characterTab;signature='';content.scrollTop=0;render();});
    panel.querySelector('.character-close').addEventListener('click',close);
    panel.addEventListener('keydown',e=>{if(e.key!=='Tab')return;const list=[...panel.querySelectorAll('button:not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(x=>x.offsetParent!==null),first=list[0],last=list.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}});
    function heading(text,parent=content){parent.append(node('h3','sheet-section-title',text));}
    function tiles(entries,parent=content){const grid=node('div','sheet-stat-grid');for(const [label,value]of entries){const e=node('div','sheet-stat');e.append(node('small','',label),node('strong','',String(value)));grid.append(e);}parent.append(grid);return grid;}
    function selectItem(uid){selectedItem=uid;signature='';render();content.querySelector('.sheet-item-detail > .item-actions')?.scrollIntoView({block:'nearest'});}
    function equipment(p,w){
      const inv=p.inventory||[],worn=p.equipment||{},equippedIds=new Set(Object.values(worn).map(String));
      const wornGrid=node('div','sheet-equipped');heading('Założone przedmioty');
      for(const[slot,label]of[['weapon','Broń'],['armor','Pancerz'],['shield','Tarcza'],['ring','Pierścień']]){
        const item=inv.find(i=>String(i.uid)===String(worn[slot])),cell=node('article','sheet-equipment-card');
        cell.append(image(equipmentIcon(item,slot)),node('small','',label),node('strong','',item?.name||'Brak'));
        if(item){cell.dataset.uid=item.uid;cell.tabIndex=0;cell.setAttribute('role','button');cell.setAttribute('aria-label','Podgląd: '+item.name);cell.classList.toggle('selected',String(item.uid)===String(selectedItem));
          const select=()=>selectItem(item.uid);cell.addEventListener('click',select);cell.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();e.stopPropagation();select();}});
          root.BractwoInventoryUI.bind(cell,item,w);
        }wornGrid.append(cell);
      }content.append(wornGrid);
      const bag=inv.filter(i=>!equippedIds.has(String(i.uid))),pageSize=15,pages=Math.max(1,Math.ceil(bag.length/pageSize));bagPage=Math.min(bagPage,pages-1);
      const title=node('div','sheet-section-row');title.append(node('h3','sheet-section-title','Plecak'),node('small','',`${inv.length} / ${w.inventory_cap||40}`));content.append(title);
      const grid=node('div','sheet-bag-grid');grid.setAttribute('aria-label','Plecak — trzy rzędy');
      for(let i=0;i<pageSize;i++){
        const item=bag[bagPage*pageSize+i];const cell=button('',()=>selectItem(item.uid),!item);cell.className='sheet-bag-cell'+(item?' '+(item.rarity||'common'):' empty');
        if(item){cell.dataset.uid=item.uid;cell.title=item.name;cell.classList.toggle('selected',String(item.uid)===String(selectedItem));cell.append(image(equipmentIcon(item,item.slot)),node('span','',item.name));if(item.quantity>1)cell.append(node('b','item-stack',String(item.quantity)));if(item.slot==='potion'){const slots=Object.entries(p.potion_slots||{}).filter(([,key])=>key===item.template).map(([k])=>k.toUpperCase());if(slots.length)cell.append(node('em','item-binding',slots.join('/')));}root.BractwoInventoryUI.bind(cell,item,w);}
        else cell.append(node('span','empty-mark','·'));grid.append(cell);
      }content.append(grid);
      const pager=node('div','sheet-bag-pager');pager.append(button('‹',()=>{bagPage--;signature='';render();},bagPage===0),node('span','',`${bagPage+1} / ${pages}`),button('›',()=>{bagPage++;signature='';render();},bagPage>=pages-1));content.append(pager);
      const item=inv.find(i=>String(i.uid)===String(selectedItem));
      if(item)content.append(root.BractwoInventoryUI.detail(item,p,w,h));
      else content.append(node('p','sheet-hint','Wybierz przedmiot z plecaka lub założonego wyposażenia, aby zobaczyć szczegóły.'));
    }
    function allocation(p){const points=p.mastery_points||0;if(!points)return;
      const box=node('section','sheet-allocation');box.append(node('h3','',`Punkty mistrzostwa do przydzielenia: ${points}`),node('p','',p.combat_remaining>0?'Punkty przydzielisz po zakończeniu walki.':'Wybierz, co chcesz wzmocnić.'));
      for(const[k,label,desc]of[['power','Potęga','+1 do obrażeń broni za każde 10 punktów'],['focus','Skupienie','+4 many za punkt']]){
        const row=node('div','sheet-allocation-row'),text=node('div');text.append(node('strong','',`${label} · ${p.mastery?.[k]||0}/20`),node('small','',desc));const b=button('+1 punkt',()=>{b.disabled=true;h.send({type:'mastery',branch:k});},!p.alive||p.combat_remaining>0||(p.mastery?.[k]||0)>=20);b.dataset.mastery=k;row.append(text,b);box.append(row);
      }content.append(box);
    }
    function stats(p,w){const s=p.character_sheet||{};allocation(p);
      tiles([['Zdrowie',`${Math.ceil(p.hp)} / ${p.max_hp}`],['Mana',`${Math.floor(p.mana)} / ${p.max_mana}`],['Klasa Pancerza',p.armor_class],['Doświadczenie',`${p.xp} / ${p.xp_next}`]]);
      if(s.caster?.order)tiles([['Ścieżka',s.caster.orders?.find(o=>o.id===s.caster.order)?.name||'']]);if(s.training?.armor_penalty)content.append(node('p','caster-status-warning','Brak wyszkolenia w pancerzu: czary zablokowane; utrudnienie Siły/Zręczności.'));
      if(s.caster?.circle?.id)tiles([['Krąg druida',s.caster.circle.name||'']]);
      if(s.fighter?.style)tiles([['Styl walki',s.fighter.style_name+(s.fighter.style_active?'':' · nieaktywny')],['Mistrzostwo broni',s.fighter.masteries?.find(m=>m.active)?.effect_name||'—']]);
      heading('Walka');tiles([['Atak bronią',dice(p.attack_bonus)],['Obrażenia',`${p.damage_dice} · ${s.damage_name||''}`],['Ataki na rundę',p.attacks_per_round],['Atak czarem',dice(s.spell_attack_bonus||0)],['ST obrony przed czarami',p.save_dc],['Premia z biegłości',signed(p.proficiency)],['Krąg czarów',p.spell_circle||'—'],['Trafienie krytyczne','20 na k20']]);
      heading('Cechy i rzuty obronne');const grid=node('div','sheet-abilities');
      for(const[k,v]of Object.entries(p.attributes||{})){const c=node('article','sheet-ability');c.append(node('small','',labels[k]||k),node('strong','',`${v} (${signed(s.ability_modifiers?.[k]||0)})`),node('span','',`Obrona ${dice(s.saving_throws?.[k]||0)}${s.proficient_saves?.includes(k)?' ✦':''}`));grid.append(c);}content.append(grid);
      heading('Odporności');const resistance=node('div','sheet-resistances');for(const r of s.resistances||[]){const c=node('span',r.multiplier<1?'resistant':'',r.name+(r.multiplier===.5?' · połowa obrażeń':r.multiplier===0?' · niewrażliwość':' · zwykłe obrażenia'));resistance.append(c);}content.append(resistance);
      if(s.ward_reduction)content.append(node('p','sheet-hint',`Kamienna osłona: obrażenia od potworów −${s.ward_reduction}%.`));
      heading('Ruch i rozwój');tiles([['Ruch w rundzie',`${s.movement_per_round||0} stóp`],['Zasięg broni',`${Math.round((p.attack_range||0)/6.4)} stóp`],['Kość zdrowia',s.hit_die||'—'],['Złoto',p.gold],['Złoto w banku',p.bank_gold||0],['Dusza',`${p.soul||0} / ${p.max_soul||100}`],['Pokonane potwory',p.kills||0],['Pokonani bossowie',p.boss_kills||0]]);
      const trained=Object.entries(p.skills||{}).map(([k,v])=>[skillNames[k]||k,`${v.level} · ${v.progress}/${v.next}`]);if(trained.length){heading('Wyszkolenie');tiles(trained);}
      const mastery=Object.entries(p.mastery||{}).filter(([,v])=>v>0).map(([k,v])=>[masteryNames[k]||k,v]);if(mastery.length){heading('Mistrzostwo');tiles(mastery);}
      heading('Aktywne efekty');const effects=node('div','sheet-resistances');for(const e of p.status_effects||[]){const chip=node('span',e.harmful?'harmful':'resistant',`${e.name} · ${root.BractwoRuntime.formatEffectTime(e)}`);chip.title=e.description||'';effects.append(chip);}if(!effects.childNodes.length)effects.append(node('p','sheet-hint','Brak aktywnych efektów.'));content.append(effects);
      if(p.form)content.append(node('p','',`Postać zwierzęca: ${({wolf:'wilk',cat:'kot',black_bear:'niedźwiedź czarny',bear:'niedźwiedź brunatny'}[p.form]||p.form)} · ${p.temp_hp||0} tymczasowych HP`));
      if(p.blessed)content.append(node('p','','Błogosławieństwo aktywne.'));
    }
    function spells(p,w){const bar=root.BractwoRuntime.displayHotbar(p);root.BractwoCasterUI.actions(content,p,h);const info=node('div','sheet-spell-summary');info.append(node('span','',`Krąg ${p.spell_circle||0} · mana ${Math.floor(p.mana)}/${p.max_mana}`),node('span','',`F · ${w.spells?.[p.favorite_spell]?.name||'—'}`));content.append(info);
      const list=node('div','sheet-spell-list');const available=Object.entries(w.spells||{}).filter(([id,s])=>s.class_ids.includes(p.class_id)||p.spell_profiles?.[id]?.available===true).sort((a,b)=>(h.gate(a[1])-h.gate(b[1]))||(a[1].circle-b[1].circle));let group='';
      for(const[id,base]of available){const s=root.BractwoRuntime.spellProfile(base,p);const gate=h.gate(s),unlocked=s.available??p.level>=gate,label=s.feature?'Zdolności klasy':s.circle?`Krąg ${s.circle}`:'Sztuczki';if(group!==label){heading(label,list);group=label;}
        const row=node('article','sheet-spell'+(unlocked?'':' locked'));row.dataset.spell=id;row.append(image(s.icon||`assets/spells/${id}.svg`));const text=node('div','sheet-spell-text');text.append(node('strong','',s.name));
        const parts=[root.BractwoRuntime.spellCostText(s,p),s.action==='bonus'?'Akcja dodatkowa':s.action==='reaction'?'Reakcja':s.action==='extra'?'Dodatkowa akcja':'Akcja'];if(s.gold)parts.push(s.gold+' zł');if(s.ritual)parts.push('Rytuał '+s.ritual_seconds+' s');if(!unlocked)parts.push(p.level<gate?`Od poziomu ${gate}`:'Czar obecnie niedostępny');text.append(node('small','',parts.join(' · ')));
        // Player-facing original summaries; no implementation labels.
        const desc=String(s.description||'').replace(/W tej adaptacji /g,'').replace(/w adaptacji /g,'').replace(/(\d+) jednost(?:ek|ki)/g,(_,n)=>`${Math.round(Number(n)/6.4)} stóp`);
        if(s.power_summary)text.append(node('p','spell-power-summary',s.power_summary));
        text.append(node('p','',desc));
        const warning=root.BractwoRuntime.concentrationWarning(s,p,w.spells);
        if(warning)text.append(node('p','spell-concentration-warning',warning));
        if(unlocked&&s.next_upgrade)text.append(node('small','spell-next-upgrade',s.next_upgrade));
        row.append(text);const actions=node('div','sheet-spell-actions'),revert=s.kind==='shape'&&p.form;
        const usable=unlocked&&(s.kind==='recovery'?root.BractwoCasterUI.canRecover(p):root.BractwoRuntime.spellUsable(s,p));
        actions.append(button(root.BractwoRuntime.queuedSpellLabel(s,p)|| (revert?'Powrót':s.kind==='recovery'?'Odpocznij i odzyskaj':s.kind==='reaction'?(p.shield_armed?'Wyłącz':'Włącz'):s.kind==='weapon_trigger'?(p.ensnaring_armed?'Anuluj':'Przygotuj'):'Użyj'),()=>h.cast(id),!usable));
        root.BractwoCircleSpellUI?.append(actions,p,s,h,unlocked);
        if(unlocked&&s.ritual)actions.append(button('Rytuał · 0 many',()=>h.send({type:'ritual',spell_id:id}),!p.alive||!!p.form||p.combat_remaining>0||!!p.character_sheet?.caster?.channel?.key||p.gold<(s.gold||0)||p.character_sheet?.training?.armor_penalty));
        if(unlocked&&s.power_options?.length>1){
          const power=node('select','spell-power-picker');power.setAttribute('aria-label',`Moc czaru: ${s.name}`);
          power.append(new Option('Auto · najwyższa moc','0'));
          for(const rank of s.power_options)power.append(new Option(`Krąg ${rank} · ${s.free_cast?0:p.mana_budget?.costs?.[rank]??'?'} many`,String(rank)));
          power.value=String(s.power_choice||0);
          power.addEventListener('change',()=>{h.send({type:'spell_power',spell_id:id,circle:Number(power.value)});power.blur();});actions.append(power);
        }
        if(s.recast_active)actions.append(button('Zakończ czar',()=>h.send({type:'stop_concentration'})));
        const select=node('select','slot-picker');select.setAttribute('aria-label',`Skrót: ${s.name}`);select.append(new Option('Przypisz skrót…',''));for(let i=0;i<(bar.length||24);i++)select.append(new Option(`${root.BractwoRuntime.hotbarLabel(i)}${bar[i]===root.BractwoRuntime.hotbarGroupForSpell(id,w)?' ✓':''} · ${w.hotbar_groups?.[bar[i]]?.name||w.spells?.[bar[i]]?.name||'Pusty'}`,String(i)));select.disabled=!unlocked;select.addEventListener('change',()=>{if(select.value!=='')h.send({type:'hotbar',slot:Number(select.value),spell_id:id,grouped:!!p.grouped_hotbar});select.blur();});actions.append(select);row.append(actions);list.append(row);
      }content.append(list);
    }
    function render(){if(panel.hidden)return;const {player:p,world:w}=h.state();if(!p)return;
      // Native mobile pickers keep focus after selection: refresh gates without replacing them.
      if(tab==='feats')root.BractwoCasterUI.syncTraining(content,p,h);
      if(tab==='spells')root.BractwoCasterUI.syncCircle(content,p,h);
      if(panel.contains(document.activeElement)&&document.activeElement.tagName==='SELECT')return;
      const next=JSON.stringify([tab,bagPage,selectedItem,p.inventory,p.equipment,p.level,Math.floor(p.mana),Math.ceil(p.hp),p.hotbar,p.grouped_hotbar,p.attributes,p.character_sheet,p.skills,p.mastery,p.mastery_points,p.combat_remaining>0,p.bonus_remaining>0,p.xp,p.xp_next,p.max_hp,p.max_mana,p.attack_bonus,p.damage_dice,p.armor_class,p.save_dc,p.attacks_per_round,p.bank_gold,p.soul,p.kills,p.boss_kills,p.gold,p.potions,p.potion_slots,p.form,p.shield_armed,p.ensnaring_armed,p.concentration,p.queued_spell,p.queued_spell?Math.ceil((p.action_remaining||0)*10):0,p.spell_cooldowns,p.spell_profiles,p.environment,p.rest_resources,p.status_effects?.map(e=>[e.id,Math.ceil(e.remaining)]),h.canTrade(),h.nearMaster?.()]);if(signature===next)return;signature=next;
      document.getElementById('characterName').textContent=p.name;document.getElementById('characterSubtitle').textContent=`${p.profession||w.classes?.[p.class_id]?.name||''} · poziom ${p.level}`;
      tabButtons.forEach(b=>{const active=b.dataset.characterTab===tab;b.classList.toggle('active',active);b.setAttribute('aria-selected',String(active));});
      const scroll=content.scrollTop;content.replaceChildren();content.dataset.tab=tab;
      if(tab==='inventory')equipment(p,w);else if(tab==='stats')stats(p,w);else if(tab==='spells')spells(p,w);else root.BractwoCasterUI.feats(content,p,h);
      content.scrollTop=scroll;
    }
    return {open,close,toggle,render,get visible(){return !panel.hidden;},get tab(){return tab;}};
  }
  root.BractwoCharacterSheet={create,equipmentIcon};
})(globalThis);
