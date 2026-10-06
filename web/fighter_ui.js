/* Permanent fighting-style choice. Browsing never sends a gameplay command. */
(function(root){'use strict';
 const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;};
 const img=path=>{const e=node('img');e.src=path;e.alt='';e.width=e.height=44;return e;};
 const button=(text,fn,disabled=false)=>{const e=node('button',text);e.type='button';e.disabled=disabled;e.onclick=fn;return e;};
 const candidateByPlayer=new Map(),cantripByPlayer=new Map();
 const fighter=p=>p?.character_sheet?.fighter||{};
 const reactionEnabled=p=>fighter(p).reaction_enabled??fighter(p).ranger_style_reactions?.enabled??true;
 function canChoose(p,nearMaster){const f=fighter(p);return !!p?.alive&&!p.form&&!p.polymorph&&!(p.combat_remaining>0)&&(p.class_id==='knight'?(!f.style||nearMaster):p.class_id==='ranger'&&p.level>=(f.required_level||2)&&(!f.style&&f.pending||f.can_change_style===true));}
 function cantripOptions(p){const f=fighter(p);return f.cantrips||f.cantrip_options||[];}
 function selectedCantrips(p){const f=fighter(p);return f.chosen_cantrips||f.selected_cantrips||cantripOptions(p).filter(s=>s.selected).map(s=>s.id);}
 function selectionPacket(p,style,cantrips,nearMaster=false){
  const f=fighter(p);if(!canChoose(p,nearMaster)||!f.choices?.some(s=>s.id===style)||f.style===style)return null;
  if(style==='druidic_warrior'){
   const ids=Array.isArray(cantrips)?cantrips:[],available=new Set(cantripOptions(p).map(s=>s.id));
   if(ids.length!==2||new Set(ids).size!==2||ids.some(id=>!available.has(id)))return null;
   return {type:'fighting_style',style,cantrips:[...ids]};
  }return {type:'fighting_style',style};
 }
 function sync(parent,p,h){for(const b of parent.querySelectorAll('[data-confirm-style]')){const ids=cantripByPlayer.get(String(p.id))||selectedCantrips(p);b.disabled=!selectionPacket(p,b.dataset.confirmStyle,ids,!!h?.nearMaster?.());}
  for(const b of parent.querySelectorAll('[data-cantrip-replace]'))b.disabled=!p?.alive||!!p.form||p.combat_remaining>0||!fighter(p).cantrip_replacement_available;
 }
 function feats(parent,p,h){
  const f=p.character_sheet?.fighter;
  if(!f||!f.choices){const empty=node('div',undefined,'sheet-empty-feats');empty.append(node('h3','Atuty'),node('p','Nie masz jeszcze atutów.'));parent.append(empty);return;}
  const section=node('section',undefined,'fighter-section');parent.append(section);
  const currentPlayer=()=>h.state?.().player||p;
  function paint(){
   p=currentPlayer();const f=fighter(p);
   section.replaceChildren();section.append(node('h3','Styl walki','sheet-section-title'));
   const editable=canChoose(p,!!h.nearMaster?.());
   const current=f.choices.find(c=>c.id===f.style);
   section.append(node('p',current?`Wybrany: ${current.name} · ${f.style_active?'aktywny':'nieaktywny z obecnym wyposażeniem'}`:'Masz jeden dostępny wybór. Nie zużywa punktu cechy ani późniejszego atutu.','fighter-current'));
   const candidate=candidateByPlayer.get(String(p.id))||f.style||'';
   const grid=node('div',undefined,'fighter-style-grid');grid.setAttribute('aria-label','Style walki');
   for(const style of f.choices){
    const card=button('',()=>{candidateByPlayer.set(String(p.id),style.id);paint();});
    card.className='fighter-style'+(candidate===style.id?' selected':'');card.dataset.style=style.id;card.setAttribute('aria-pressed',String(candidate===style.id));
    card.append(img(style.icon||'assets/equipment/weapon.svg'),node('strong',style.name),node('span',style.description),node('small',style.active_with_gear?'Działa z obecnym wyposażeniem':style.requirement||'',style.active_with_gear?'style-compatible':'style-incompatible'));
    grid.append(card);
   }section.append(grid);
   const selected=f.choices.find(c=>c.id===candidate);
   if(selected){
    if(candidate==='druidic_warrior'&&f.style!==candidate){
     const key=String(p.id),picked=cantripByPlayer.get(key)||selectedCantrips(p);cantripByPlayer.set(key,picked);
     section.append(node('h4',`Wybierz dwie sztuczki druida · ${picked.length}/2`),node('p','Atak czarem i ST korzystają z Mądrości. Obrażenia sztuczek rosną na poziomach 5, 11 i 17.','sheet-hint'));
     const grid=node('div',undefined,'fighter-cantrip-grid');
     for(const spell of cantripOptions(p)){const chosen=picked.includes(spell.id),b=button('',()=>{const old=cantripByPlayer.get(key)||[];if(!old.includes(spell.id)&&old.length>=2)return;cantripByPlayer.set(key,old.includes(spell.id)?old.filter(id=>id!==spell.id):[...old,spell.id]);paint();},!chosen&&picked.length>=2);b.className='fighter-style'+(chosen?' selected':'');b.dataset.styleCantrip=spell.id;b.setAttribute('aria-pressed',String(chosen));b.append(node('strong',spell.name),node('span',spell.description||''));grid.append(b);}section.append(grid);
    }
    const confirm=node('div',undefined,'fighter-confirm');confirm.append(node('span',selected.name));
    const apply=button(f.style===candidate?'Wybrany styl':f.style?'Zmień styl':'Wybierz ten styl',()=>{const latest=currentPlayer(),packet=selectionPacket(latest,candidate,cantripByPlayer.get(String(latest.id))||selectedCantrips(latest),!!h.nearMaster?.());if(packet){apply.disabled=true;h.send(packet);}},!editable||!selectionPacket(p,candidate,cantripByPlayer.get(String(p.id))||selectedCantrips(p),!!h.nearMaster?.()));apply.dataset.confirmStyle=candidate;confirm.append(apply);section.append(confirm);
   }
   section.append(node('p',p.combat_remaining>0?'Wybór jest dostępny po zakończeniu walki.':current?p.class_id==='ranger'?(f.style_change_reason||'Styl walki łowcy jest stałym wyborem. Druidyczny wojownik może zastąpić jedną sztuczkę po zdobyciu poziomu.'):'Zmiana bez opłaty u mistrza profesji w osadzie. Zmiana broni nie zmienia stylu.':'Kliknij kafelek, przeczytaj opis i zatwierdź wybór przyciskiem.','sheet-hint'));
   if(['interception','protection'].includes(f.style)){const active=reactionEnabled(p),b=button((active?'✓ ':'')+'Automatyczna reakcja · '+(active?'włączona':'wyłączona'),()=>h.send({type:'style_reaction',enabled:!active}),!p.alive);b.setAttribute('aria-pressed',String(active));section.append(b,node('small','Działanie zużywa dostępną reakcję. Możesz wyłączyć je, aby zachować reakcję na inne zdolności.'));}
   if(f.style==='druidic_warrior')cantripReplacement(section,p,h);
  }paint();
  if(h.featSection==='ranger_style')return;
  if(f.masteries?.length){const section2=node('section',undefined,'fighter-section');section2.append(node('h3','Mistrzostwo broni','sheet-section-title'),node('p',`Opanowane rodzaje broni: ${f.masteries.length}. Przy ataku działa właściwość aktualnie używanej broni.`,'sheet-hint'));
  for(const m of f.masteries||[]){const row=node('article',undefined,'fighter-mastery'+(m.active?' active':''));row.append(img(m.icon));const text=node('div');text.append(node('strong',m.name+' · '+m.effect_name),node('p',m.description),node('small',m.active?'Aktywne z obecną bronią':'Użyj tego rodzaju broni'));row.append(text);section2.append(row);}
  parent.append(section2);}
  if(f.can_change_grip){const grip=node('section',undefined,'fighter-section');grip.append(node('h3','Chwyt broni','sheet-section-title'),node('p','Jednorącz: możesz nosić tarczę. Oburącz: większa kość broni wszechstronnej; tarcza pozostaje w plecaku.','sheet-hint'));
   const actions=node('div',undefined,'item-actions');for(const [key,label]of [['one','Jednorącz'],['two','Oburącz']])actions.append(button((f.weapon_grip===key?'✓ ':'')+label,()=>h.send({type:'weapon_grip',grip:key}),!p.alive||p.combat_remaining>0||f.weapon_grip===key));grip.append(actions);parent.append(grip);
  }
 }
 function cantripReplacement(parent,p,h){const f=fighter(p),chosen=selectedCantrips(p);if(!chosen.length)return;
  const section=node('section',undefined,'fighter-cantrip-replacement');section.append(node('h4','Sztuczki Druidycznego wojownika'),node('p',chosen.map(id=>cantripOptions(p).find(s=>s.id===id)?.name||id).join(' · '),'sheet-hint'));
  if(f.cantrip_replacement_available){const from=node('select'),to=node('select');from.setAttribute('aria-label','Sztuczka do zastąpienia');to.setAttribute('aria-label','Nowa sztuczka');for(const spell of cantripOptions(p))(chosen.includes(spell.id)?from:to).append(new Option(spell.name,spell.id));
   const apply=button('Zastąp jedną sztuczkę',()=>{const latest=h.state?.().player||p;if(latest.alive&&!latest.form&&!(latest.combat_remaining>0)&&fighter(latest).cantrip_replacement_available&&from.value&&to.value){apply.disabled=true;h.send({type:'ranger_cantrip',old_spell:from.value,new_spell:to.value});}},!p.alive||!!p.form||p.combat_remaining>0);apply.dataset.cantripReplace='';section.append(from,to,apply,node('small','Przy zdobyciu poziomu łowcy możesz zastąpić jedną sztuczkę inną sztuczką druida.'));
  }parent.append(section);
 }
 function createCombatMenu(h){const host=document.getElementById('attackButton')?.parentElement;if(!host)return {sync(){},close(){}};
  const toggle=button('▾',()=>{h.stop?.();panel.hidden=!panel.hidden;toggle.setAttribute('aria-expanded',String(!panel.hidden));if(!panel.hidden)sync();});toggle.id='weaponActionToggle';toggle.className='weapon-action-toggle';toggle.setAttribute('aria-label','Sposób ataku i działania broni');toggle.setAttribute('aria-haspopup','dialog');toggle.setAttribute('aria-controls','weaponActionMenu');toggle.setAttribute('aria-expanded','false');
  const panel=node('section',undefined,'weapon-action-menu');panel.id='weaponActionMenu';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Działania broni');host.append(toggle,panel);let signature='';
  function close(){panel.hidden=true;toggle.setAttribute('aria-expanded','false');}
  function send(packet){h.send(packet);close();}
  function sync(){const p=h.player(),w=p?.character_sheet?.weapon_actions;toggle.hidden=!w;toggle.disabled=!p?.alive;if(!p?.alive){close();return;}if(panel.hidden)return;
   const target=h.target?.(),e=p.character_sheet?.caster?.elemental_fury,key=JSON.stringify([p.id,p.alive,p.form,w?.mode,w?.modes,w?.offhand_enabled,w?.offhand_reason,w?.can_grapple,target,e,fighter(p).style,reactionEnabled(p)]);if(key===signature)return;if(panel.contains(document.activeElement)&&document.activeElement.tagName==='SELECT')return;signature=key;
   panel.replaceChildren();panel.append(node('strong','Sposób ataku'));
   for(const mode of w?.modes||[]){const labels={weapon:'Broń',throw:'Rzut bronią',unarmed:'Bez broni'},b=button((w.mode===mode.id?'✓ ':'')+labels[mode.id],()=>send({type:'weapon_attack_mode',mode:mode.id}),!p.alive||!!p.form||!mode.enabled||w.mode===mode.id);b.dataset.combatWeaponMode=mode.id;b.setAttribute('aria-pressed',String(w.mode===mode.id));panel.append(b);}
   if(w?.offhand?.uid){const b=button('Atak drugą bronią · akcja dodatkowa',()=>{const latest=h.player();if(latest?.character_sheet?.weapon_actions?.offhand_enabled)send({type:'offhand_attack',...(h.target?.()||{})});},!w.offhand_enabled);b.dataset.combatOffhand='';b.title=w.offhand_reason||'';panel.append(b);if(w.offhand_reason)panel.append(node('small',w.offhand_reason));}
   if(['interception','protection'].includes(fighter(p).style)){const active=reactionEnabled(p),b=button((active?'✓ ':'')+'Reakcja stylu · '+(active?'włączona':'wyłączona'),()=>send({type:'style_reaction',enabled:!active}));b.dataset.combatStyleReaction='';b.setAttribute('aria-pressed',String(active));panel.append(b);}
   const grapple=button('Chwyć zaznaczony cel',()=>{const latest=h.player(),target=h.target?.();if(latest?.alive&&latest.character_sheet?.weapon_actions?.can_grapple&&target)send({type:'grapple',...target});},!w?.can_grapple||!target||!!p.form);grapple.dataset.combatGrapple='';panel.append(grapple,node('small',`Chwyt: ST ${w?.grapple_dc||'—'}. Wymaga wolnej ręki i celu w zasięgu.`));
   if(e?.id==='primal_strike'){const label=node('label',undefined,'elemental-damage-picker'),select=node('select');label.append(node('span','Żywioł Pierwotnego uderzenia'));select.setAttribute('aria-label','Żywioł Pierwotnego uderzenia');for(const type of e.damage_types||[]){const id=typeof type==='string'?type:type.id;select.append(new Option(typeof type==='string'?type:type.name,id));}select.value=e.damage_type;select.addEventListener('change',()=>{h.send({type:'elemental_damage_type',damage_type:select.value});select.blur();});label.append(select);const toggle=node('label',undefined,'elemental-strike-toggle'),input=node('input');input.type='checkbox';input.checked=e.strike_enabled!==false;input.dataset.combatElementalEnabled='';input.addEventListener('change',()=>h.send({type:'elemental_strike',enabled:input.checked}));toggle.append(input,node('span','Pierwotne uderzenie przy trafieniu'));panel.append(label,toggle);}
  }
  panel.addEventListener('keydown',event=>{if(event.key==='Escape'){event.stopPropagation();close();toggle.focus({preventScroll:true});}});return {sync,close};
 }
 function createPrompt(h){
  const panel=node('aside',undefined,'fighter-choice');panel.id='fighterChoice';panel.hidden=true;panel.setAttribute('aria-label','Wybierz styl walki');
  const head=node('header');head.append(node('strong','Wybierz styl walki'));const close=button('×',()=>{const p=h.player();if(!p)return;closed.add(String(p.id));try{localStorage.setItem(key(p),'1');}catch{}panel.hidden=true;});close.setAttribute('aria-label','Wybierz styl później');head.append(close);
  panel.append(head,node('p','Masz jeden dostępny wybór.'),button('Wybierz styl',()=>h.open('feats')));
  (document.getElementById('hudLeftRail')||document.getElementById('gameUI')).append(panel);
  const closed=new Set(),key=p=>'bractwo-fighter-choice-v1:'+p.id;
  function sync(){const p=h.player();let hidden=!p||p.class_id!=='knight'||!p.character_sheet?.fighter?.pending;
   if(p){try{hidden=hidden||localStorage.getItem(key(p))==='1';}catch{}hidden=hidden||closed.has(String(p.id));}
   panel.hidden=hidden;
  }
  return {sync};
 }
 const api={feats,createPrompt,canChoose,selectionPacket,sync,cantripOptions,selectedCantrips,createCombatMenu};root.BractwoFighterUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
