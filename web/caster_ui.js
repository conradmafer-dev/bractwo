/* Class grants, explicit druid path selection and duplicate-safe general feats. */
(function(root){'use strict';
 const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(label,fn,disabled=false)=>{const b=node('button',label);b.type='button';b.disabled=disabled;b.onclick=fn;return b;};
 const image=path=>{const i=node('img');i.src=path;i.alt='';i.width=i.height=42;return i;};
 const abilityNames={strength:'Siła',dexterity:'Zręczność',constitution:'Kondycja',intelligence:'Inteligencja',wisdom:'Mądrość',charisma:'Charyzma'};
 const candidates=new Map(),circleCandidates=new Map(),schoolCandidates=new Map(),trainingChoices=new Map(),elementalCandidates=new Map();
 const elemental=p=>p?.character_sheet?.caster?.elemental_fury||{};
 const elementalNames={potent_spellcasting:'Potężne sztuczki',primal_strike:'Pierwotne uderzenie'};
 const elementalDamageNames={cold:'Zimno',fire:'Ogień',lightning:'Błyskawice',thunder:'Grzmot'};
 function elementalReason(p,choice){const e=elemental(p);
  if(p?.class_id!=='druid')return 'Furia żywiołów jest zdolnością druida.';
  if(e.id)return 'Furia żywiołów została już wybrana.';
  if(!p.alive)return 'Wybór po odrodzeniu.';
  if(p.form||p.polymorph)return 'Wybór po zakończeniu przemiany.';
  if(p.combat_remaining>0)return 'Wybór po zakończeniu walki.';
  if(p.level<(e.required_level||7))return 'Wybór od poziomu '+(e.required_level||7)+'.';
  if(!e.pending)return 'Wybór jest obecnie niedostępny.';
  if(choice&&!e.options?.some(o=>o.id===choice))return 'Wybierz jedną dostępną opcję.';
  return '';
 }
 function elementalPacket(p,choice){return choice&&!elementalReason(p,choice)?{type:'elemental_fury',choice}:null;}
 function syncElemental(parent,p){const e=elemental(p);
  for(const b of parent.querySelectorAll('[data-elemental-confirm]')){const reason=elementalReason(p,b.dataset.elementalConfirm);b.disabled=!!reason;b.title=reason;}
  for(const hint of parent.querySelectorAll('[data-elemental-reason]'))hint.textContent=elementalReason(p);
  for(const select of parent.querySelectorAll('[data-elemental-damage]')){select.disabled=!p?.alive||e.id!=='primal_strike';if(document.activeElement!==select)select.value=e.damage_type||'cold';}
  for(const input of parent.querySelectorAll('[data-elemental-enabled]')){input.disabled=!p?.alive||e.id!=='primal_strike';input.checked=e.strike_enabled!==false;}
 }
 function elementalPanel(parent,p,h){const e=elemental(p);if(p.class_id!=='druid'||!Object.keys(e).length)return;
  const box=node('section',undefined,'caster-elemental-fury'),current=()=>h.state?.().player||p;box.append(node('h3','Furia żywiołów · poziom '+(e.required_level||7)));
  if(!e.id){const selected=elementalCandidates.get(String(p.id))||'',grid=node('div',undefined,'caster-order-grid');box.append(node('p','Wybierz jedną stałą zdolność: wzmocnienie sztuczek albo trafień bronią i ataków w przemianie. Wybór jest bezpłatny i nie zużywa atutu.','sheet-hint'));
   for(const option of e.options||[]){const b=button('',()=>{elementalCandidates.set(String(p.id),option.id);box.remove();elementalPanel(parent,current(),h);});b.className='caster-order'+(selected===option.id?' candidate':'');b.dataset.elementalChoice=option.id;b.setAttribute('aria-pressed',String(selected===option.id));b.append(image(option.icon||'assets/spells/'+(option.id==='primal_strike'?'shillelagh':'produce_flame')+'.svg'),node('strong',option.name||elementalNames[option.id]),node('small',option.description||''));if(option.upgrade_description)b.append(node('small',`Poziom ${e.upgrade_level||15}: ${option.upgrade_description}`));grid.append(b);}box.append(grid);
   if(selected){const choice=e.options?.find(o=>o.id===selected);if(choice){const confirm=button('Wybierz: '+(choice.name||elementalNames[selected]),()=>{const packet=elementalPacket(current(),selected);if(packet){confirm.disabled=true;h.send(packet);}},!!elementalReason(p,selected));confirm.dataset.elementalConfirm=selected;box.append(confirm);}}
   const hint=node('p',elementalReason(p),'sheet-choice-reason');hint.dataset.elementalReason='';box.append(hint);
  }else{const choice=e.options?.find(o=>o.id===e.id);box.append(node('strong',e.name||choice?.name||elementalNames[e.id]));if(e.description||choice?.description)box.append(node('p',e.description||choice.description,'sheet-hint'));if(e.upgrade_description||choice?.upgrade_description)box.append(node('p',`${p.level>=(e.upgrade_level||15)?'Ulepszenie aktywne':'Poziom '+(e.upgrade_level||15)}: ${e.upgrade_description||choice.upgrade_description}`,'sheet-hint'));if(e.id==='primal_strike')elementalDamagePicker(box,p,h);}
  parent.append(box);syncElemental(box,p);
 }
 function elementalDamagePicker(parent,p,h){const e=elemental(p),label=node('label',undefined,'elemental-damage-picker'),select=node('select');label.append(node('span','Żywioł następnego Pierwotnego uderzenia'));select.setAttribute('aria-label','Żywioł Pierwotnego uderzenia');select.dataset.elementalDamage='';
  for(const type of e.damage_types||['cold','fire','lightning','thunder']){const id=typeof type==='string'?type:type.id;select.append(new Option(typeof type==='string'?elementalDamageNames[id]||id:type.name||elementalDamageNames[id]||id,id));}select.value=e.damage_type||'cold';select.disabled=!p.alive;select.addEventListener('change',()=>{const latest=h.state?.().player||p;if(latest.alive&&elemental(latest).id==='primal_strike')h.send({type:'elemental_damage_type',damage_type:select.value});select.blur();});label.append(select);const toggle=node('label',undefined,'elemental-strike-toggle'),input=node('input');input.type='checkbox';input.dataset.elementalEnabled='';input.checked=e.strike_enabled!==false;input.disabled=!p.alive;input.addEventListener('change',()=>{const latest=h.state?.().player||p;if(latest.alive&&elemental(latest).id==='primal_strike')h.send({type:'elemental_strike',enabled:input.checked});});toggle.append(input,node('span','Pierwotne uderzenie przy trafieniu'));parent.append(label,toggle,node('small','Żywioł możesz zmienić przed kolejnym trafieniem. Wyłącz uderzenie, aby zachować je na późniejsze trafienie w tej turze. Działa raz na twoją turę.'));
 }
 function canRecover(p){return !!p&&p.class_id==='mage'&&!!p.alive&&!p.form&&!p.character_sheet?.caster?.channel?.key&&p.mana<p.max_mana&&p.character_sheet?.caster?.arcane_recovery_remaining>0&&!(p.rest?.remaining>0)&&!(p.rest_short_remaining>0)&&!(p.rest_block_remaining>0)&&!p.rest_block_reason;}
 function hasShapeUse(p){const resource=p?.character_sheet?.caster?.circle?.resources?.find(r=>r.id==='shape');return !resource||resource.remaining>0;}
 function canChoose(p,nearMaster){return p.class_id==='druid'&&!!p.alive&&!p.form&&!(p.combat_remaining>0)&&(!p.character_sheet?.caster?.order||!!nearMaster);}
 function trainingReason(p,feat,selection){
  if(!p?.alive)return 'Atut wybierzesz po odrodzeniu.';
  if(p.class_chosen===false)return 'Najpierw wybierz profesję.';
  if(p.form||p.polymorph)return 'Atut wybierzesz po zakończeniu przemiany.';
  if(p.combat_remaining>0)return 'Atut wybierzesz po zakończeniu walki.';
  if(!(p.character_sheet?.training?.points>0))return 'Brak dostępnego wyboru atutu.';
  if(!feat)return 'Ten atut nie jest już dostępny.';
  if(feat.ability_points===2){
   if(!Array.isArray(selection)||selection.length!==2||selection.some(a=>!feat.abilities?.includes(a)))return 'Przydziel oba punkty cech.';
   const allocation={};for(const a of selection)allocation[a]=(allocation[a]||0)+1;
   if(Object.entries(allocation).some(([a,n])=>Number(p.attributes?.[a]||0)+n>20))return 'Cecha nie może przekroczyć 20. Wybierz inny podział punktów.';
  }else if(feat.abilities?.length&&!feat.abilities.includes(selection))return 'Wybierz dostępną cechę poniżej 20.';
  return '';
 }
 function trainingSelection(row){const selects=Array.from(row.querySelectorAll('select'));return row.dataset.abilityPoints==='2'?selects.map(s=>s.value):selects[0]?.value||'';}
 function trainingSummary(f){
  const allocation=f.allocation||Object.fromEntries(String(f.ability||'').split('+').filter(Boolean).map(a=>[a,String(f.ability).split('+').filter(x=>x===a).length]));
  const gains=Object.entries(allocation).map(([a,n])=>`+${n} ${abilityNames[a]||a}`);
  return f.name+(gains.length?' · '+gains.join(', '):'')+(f.active===false?' · wymagania niespełnione':'');
 }
 function syncTraining(parent,p,h){
  const options=p?.character_sheet?.training?.options||[];
  for(const row of parent.querySelectorAll('.training-option')){
   const confirm=row.querySelector('button'),feat=options.find(f=>f.id===row.dataset.feat);
   const reason=trainingReason(p,feat,trainingSelection(row));
   confirm.disabled=!!reason;confirm.title=reason;
   row.querySelector('.training-reason').textContent=reason;
  }syncCircle(parent,p,h);root.BractwoFighterUI?.sync(parent,p,h);syncElemental(parent,p);
 }
 const circleIcons={land:'assets/spells/entangle.svg',moon:'assets/spells/moonbeam.svg',sea:'assets/spells/ray_of_frost.svg',stars:'assets/spells/starry_wisp.svg'};
 function circleReason(p){
  const c=p?.character_sheet?.caster?.circle;
  if(c?.id)return 'Krąg został już wybrany.';
  if(!p?.alive)return 'Krąg wybierzesz po odrodzeniu.';
  if(p.form)return 'Krąg wybierzesz po zakończeniu przemiany.';
  if(p.combat_remaining>0)return 'Krąg wybierzesz po zakończeniu walki.';
  if(p.level<(c?.required_level||3))return 'Wybór od poziomu '+(c?.required_level||3)+'.';
  if(c?.required_promotion&&!(c.promotion_met??p.promoted))return `Najpierw kup promocję u mistrza profesji w mieście: ${p.promotion?.cost??2000} złota.`;
  return c?.pending?'':'Wybór kręgu jest teraz niedostępny.';
 }
 const circleToggleValue=(circle,id)=>!!circle?.[id==='star_map'?'map_equipped':id];
 function circleActionLabel(action,circle){return action.name+(action.kind==='toggle'?(circleToggleValue(circle,action.id)?' · włączone':' · wyłączone'):'');}
 function circleTargetAllowed(p,ally,action){return !!p?.alive&&!!ally&&ally.hp>0&&String(ally.id)!==String(p.id)&&(ally.floor||0)===(p.floor||0)&&Math.hypot(ally.x-p.x,ally.y-p.y)<=(action==='shared_moonlight_target'?64:192);}
 function syncCircle(parent,p,h){
  const c=p?.character_sheet?.caster?.circle||{};
  for(const b of parent.querySelectorAll('[data-circle-confirm]')){const reason=circleReason(p);b.disabled=!!reason;b.title=reason;}
  for(const hint of parent.querySelectorAll('.circle-choice-reason'))hint.textContent=circleReason(p);
  for(const b of parent.querySelectorAll('[data-circle-action]')){
   const action=c.actions?.find(a=>a.id===b.dataset.circleAction);b.disabled=!p?.alive||!action?.enabled;
   if(action){b.textContent=circleActionLabel(action,c);if(action.kind==='toggle')b.setAttribute('aria-pressed',String(circleToggleValue(c,action.id)));}
  }
  for(const chip of parent.querySelectorAll('[data-circle-resource]')){const resource=c.resources?.find(r=>r.id===chip.dataset.circleResource);if(resource)chip.textContent=`${resource.name}: ${resource.remaining}/${resource.maximum}`;}
  for(const b of parent.querySelectorAll('[data-circle-land-confirm]'))b.disabled=!p?.alive||!!p.form||p.combat_remaining>0||!c.land_change_ready;
  for(const chip of parent.querySelectorAll('[data-rest-resource]')){const resource=p?.rest_resources?.find(r=>r.id===chip.dataset.restResource);if(resource)chip.textContent=`${resource.name}: ${resource.remaining}/${resource.maximum}${resource.recovery?' · '+resource.recovery:''}`;}
  for(const b of parent.querySelectorAll('[data-arcane-recovery]'))b.disabled=!canRecover(p);
  for(const b of parent.querySelectorAll('[data-form]')){const form=p?.character_sheet?.caster?.forms?.find(f=>f.id===b.dataset.form);b.disabled=!p?.alive||!form?.unlocked||(!p.form&&!hasShapeUse(p));}
  for(const b of parent.querySelectorAll('[data-circle-target]'))b.disabled=b.dataset.circleTargetMode==='selected'?!circleTargetAllowed(p,h?.selectedAlly?.(),b.dataset.circleTarget):!p?.alive;
  for(const b of parent.querySelectorAll('[data-dive]')){b.disabled=!p?.alive||!p.environment?.in_water;b.textContent=p.environment?.submerged?'Wynurz się':'Zanurkuj';}
  for(const hint of parent.querySelectorAll('[data-breath]'))hint.textContent=p?.environment?.submerged&&Number.isFinite(p.environment.breath_remaining)?`Pozostały oddech: ${Math.ceil(p.environment.breath_remaining)} s`:'';
  for(const b of parent.querySelectorAll('[data-study]'))b.disabled=!p?.alive||p.action_remaining>0||!h?.studyTarget?.();
  for(const b of parent.querySelectorAll('[data-search]'))b.disabled=!p?.alive||p.action_remaining>0;
  syncSchool(parent,p,h);syncElemental(parent,p);
 }
 function circlePanel(parent,p,h){
  const c=p.character_sheet?.caster?.circle;if(!c)return;
  const box=node('section',undefined,'caster-circles'),current=()=>h.state?.().player||p;
  box.append(node('h3','Krąg druida'));
  if(!c.id){
   const choice=circleCandidates.get(String(p.id))||{},candidate=choice.id||'',cards=node('div',undefined,'caster-order-grid');
   box.append(node('small','Wybierz jeden krąg od poziomu '+(c.required_level||3)+(c.required_promotion?' po uzyskaniu promocji.':'.')+' Wybór jest stały.'));
   for(const option of c.options||[]){
    const b=button('',()=>{circleCandidates.set(String(p.id),{...choice,id:option.id});parent.replaceChildren();feats(parent,current(),h);});b.className='caster-order'+(candidate===option.id?' candidate':'');b.dataset.circle=option.id;b.setAttribute('aria-pressed',String(candidate===option.id));
    b.append(image(option.icon||circleIcons[option.id]),node('strong',option.name),node('small',option.description));cards.append(b);
   }box.append(cards);
   const selected=c.options?.find(option=>option.id===candidate);
   if(selected){
    if(candidate==='land'){
     const select=node('select');select.setAttribute('aria-label','Początkowy rodzaj lądu');for(const land of c.lands||[])select.append(new Option(land.name,land.id));select.value=choice.land||c.land||'arid';
     select.addEventListener('change',()=>circleCandidates.set(String(p.id),{id:candidate,land:select.value}));box.append(select);
    }
    const b=button('Wybierz: '+selected.name,()=>{const latest=current(),picked=circleCandidates.get(String(p.id));if(!circleReason(latest)&&picked?.id)h.send({type:'druid_circle',circle:picked.id,land:picked.land||'arid'});},!!circleReason(p));b.dataset.circleConfirm=candidate;box.append(b);
    for(const feature of selected.features||[])box.append(node('p',`Poziom ${feature.level}: ${feature.name} — ${feature.description}`,'circle-feature-preview'));
   }
   box.append(node('small',circleReason(p),'circle-choice-reason'));
  }else{
   const selected=c.options?.find(option=>option.id===c.id);box.append(node('strong',c.name||selected?.name));if(selected?.description)box.append(node('p',selected.description));
   for(const feature of c.features||[]){const row=node('article',undefined,'circle-feature'+(feature.unlocked?'':' locked'));row.append(node('strong',feature.name),node('small',feature.description),node('small',feature.unlocked?'Dostępne':'Od poziomu '+feature.level));box.append(row);}
   if(c.id==='land'&&c.lands?.length){
    const controls=node('div',undefined,'circle-land-controls'),select=node('select');select.setAttribute('aria-label','Rodzaj lądu');for(const land of c.lands)select.append(new Option(land.name,land.id));select.value=c.land;
    const b=button('Zmień rodzaj lądu',()=>{const latest=current(),circle=latest.character_sheet?.caster?.circle;if(latest.alive&&!latest.form&&!(latest.combat_remaining>0)&&circle?.land_change_ready)h.send({type:'circle_command',action:'land',value:select.value});});b.dataset.circleLandConfirm='';controls.append(select,b);box.append(controls,node('small','Nowy rodzaj lądu możesz wybrać po długim odpoczynku.'));
   }
  }parent.append(box);
 }
 function circleActions(parent,p,h){
  const c=p.character_sheet?.caster?.circle;if(!c?.id&&!c?.resources?.length)return;
  const box=node('section',undefined,'circle-actions');box.append(node('h3',c.name||'Zasoby druida'));
  if(c.starry_form)box.append(node('p','Gwiezdna postać: '+({archer:'Łucznik',chalice:'Kielich',dragon:'Smok'}[c.starry_form]||c.starry_form)));
  if(c.id==='stars'&&c.features?.some(f=>f.id==='cosmic_omen'&&f.unlocked))box.append(node('small','Kosmiczny omen: '+(c.omen==='woe'?'Nieszczęście':'Pomyślność')));
  const resources=node('div',undefined,'circle-resources');for(const resource of c.resources||[]){const chip=node('span',`${resource.name}: ${resource.remaining}/${resource.maximum}`);chip.dataset.circleResource=resource.id;resources.append(chip);}if(resources.childNodes.length)box.append(resources);
  const buttons=node('div',undefined,'circle-action-buttons');
  for(const action of c.actions||[]){
   const b=button(circleActionLabel(action,c),()=>{const latest=h.state?.().player||p,circle=latest.character_sheet?.caster?.circle,current=circle?.actions?.find(a=>a.id===action.id);if(!latest.alive||!current?.enabled)return;if(current.kind==='spell')h.cast(current.id);else h.send({type:'circle_command',action:current.id,...(current.kind==='toggle'?{value:!circleToggleValue(circle,current.id)}:{})});},!p.alive||!action.enabled);b.dataset.circleAction=action.id;if(action.kind==='toggle')b.setAttribute('aria-pressed',String(circleToggleValue(c,action.id)));buttons.append(b);
  }box.append(buttons);
  const targetAction=c.id==='stars'?'chalice_target':c.id==='moon'&&c.features?.some(f=>f.id==='lunar_form'&&f.unlocked)?'shared_moonlight_target':'';
  if(targetAction){
   const targets=node('div',undefined,'circle-target-controls');targets.append(node('small',targetAction==='chalice_target'?'Dodatkowe leczenie Kielicha · sojusznik w 30 stopach':'Wspólny Księżycowy krok · sojusznik w 10 stopach'));
   const choose=button('Użyj zaznaczonego sojusznika',()=>{const latest=h.state?.().player||p,ally=h.selectedAlly?.();if(circleTargetAllowed(latest,ally,targetAction))h.send({type:'circle_command',action:targetAction,value:String(ally.id)});});choose.dataset.circleTarget=targetAction;choose.dataset.circleTargetMode='selected';
   const reset=button(targetAction==='chalice_target'?'Leczenie domyślne':'Bez towarzysza',()=>h.send({type:'circle_command',action:targetAction,value:''}));reset.dataset.circleTarget=targetAction;reset.dataset.circleTargetMode='reset';targets.append(choose,reset);box.append(targets);
  }
  parent.append(box);syncCircle(parent,p,h);
 }
 const schoolIcons=Object.fromEntries(['evocation','abjuration','divination','illusion'].map(id=>[id,'assets/feats/wizard_'+id+'.svg']));
 const portentModes={attack:'Mój atak',enemy_save:'Obrona wroga',self_save:'Moja obrona'};
 function schoolReason(p){
  const s=p?.character_sheet?.caster?.school;
  if(p?.class_id!=='mage')return 'Szkoły są dostępne dla czarodzieja.';
  if(s?.id)return 'Szkoła została już wybrana.';
  if(!p?.alive)return 'Szkołę wybierzesz po odrodzeniu.';
  if(p.form)return 'Szkołę wybierzesz po zakończeniu przemiany.';
  if(p.combat_remaining>0)return 'Szkołę wybierzesz po zakończeniu walki.';
  if(p.level<(s?.required_level||3))return `Wybór od poziomu ${s?.required_level||3}. Promocja u mistrza profesji w mieście: ${p.promotion?.cost??2000} złota.`;
  if(!(s?.promotion_met??p.promoted))return `Najpierw kup promocję u mistrza profesji w mieście: ${p.promotion?.cost??2000} złota.`;
  return s?.pending&&s.eligible!==false?'':'Wybór szkoły jest teraz niedostępny.';
 }
 const schoolState=p=>p?.character_sheet?.caster?.school||{};
 function schoolActionValue(s,a){return !!(a?.value??s?.[a?.id]);}
 function schoolActionLabel(s,a){return a.name+(a.kind==='toggle'?(schoolActionValue(s,a)?' · włączone':' · wyłączone'):'');}
 function schoolActionAvailable(p,s,a,h){
  if(!p?.alive||p.form||s.active===false||!a?.enabled)return false;
  if(a.kind!=='spell')return true;
  const id=a.spell_id||a.id,base=h?.state?.().world?.spells?.[id],runtime=root.BractwoRuntime;
  return !base||!runtime?.spellUsable||runtime.spellUsable(runtime.spellProfile({...base,id},p),p);
 }
 function schoolTargetAllowed(p,ally){return !!p?.alive&&!!ally&&ally.hp>0&&String(ally.id)!==String(p.id)&&(ally.floor||0)===(p.floor||0)&&Math.hypot(ally.x-p.x,ally.y-p.y)<=192;}
 function portentAvailable(p,index,value){
  const s=schoolState(p),die=s.portents?.find(d=>Number(d.index)===Number(index));
  const action=s.actions?.find(a=>a.id==='arm_portent');
  return !!p?.alive&&!p.form&&s.active!==false&&s.id==='divination'&&!!die&&!die.spent&&Number(die.value)===Number(value)&&action?.enabled!==false;
 }
 function syncSchool(parent,p,h){
  const s=schoolState(p),choice=schoolCandidates.get(String(p?.id));
  for(const hint of parent.querySelectorAll('.school-choice-reason'))hint.textContent=schoolReason(p);
  for(const b of parent.querySelectorAll('[data-school-confirm]')){const reason=schoolReason(p)||(!choice?.confirmed?'Potwierdź, że wybór szkoły jest stały.':'');b.disabled=!!reason;b.title=reason;}
  for(const b of parent.querySelectorAll('[data-school-action]')){
   const a=s.actions?.find(a=>a.id===b.dataset.schoolAction);b.disabled=!schoolActionAvailable(p,s,a,h);
   if(a){b.textContent=schoolActionLabel(s,a);if(a.kind==='toggle')b.setAttribute('aria-pressed',String(schoolActionValue(s,a)));}
  }
  for(const chip of parent.querySelectorAll('[data-school-resource]')){const r=s.resources?.find(r=>r.id===chip.dataset.schoolResource);chip.textContent=r?`${r.name}: ${r.remaining}/${r.maximum}`:'';}
  for(const chip of parent.querySelectorAll('[data-school-ward]'))chip.textContent=`Magiczna osłona: ${s.ward?.hp||0}/${s.ward?.maximum||0} HP`;
  for(const b of parent.querySelectorAll('[data-portent-index]')){
   b.disabled=!portentAvailable(p,b.dataset.portentIndex,b.dataset.portentValue);
   b.setAttribute('aria-pressed',String(Number(s.armed_portent?.index)===Number(b.dataset.portentIndex)&&s.armed_portent?.mode===b.dataset.portentMode));
  }
  for(const row of parent.querySelectorAll('[data-portent-row]')){const die=s.portents?.find(d=>Number(d.index)===Number(row.dataset.portentRow));row.querySelector('.portent-die').textContent=die&&!die.spent?String(die.value):'—';row.querySelector('.portent-status').textContent=die&&!die.spent?'Wynik k20':'Zużyty wynik';row.classList.toggle('spent',!die||!!die.spent);}
  for(const hint of parent.querySelectorAll('[data-armed-portent]')){const die=s.portents?.find(d=>Number(d.index)===Number(s.armed_portent?.index));hint.textContent=s.armed_portent&&die?`Przygotowane: ${die.value} · ${portentModes[s.armed_portent.mode]||''}. Wynik zastąpi następny pasujący rzut k20.`:'Wybierz wynik i rodzaj następnego rzutu k20, który ma zastąpić.';}
  for(const b of parent.querySelectorAll('[data-portent-clear]'))b.disabled=!p?.alive||!s.armed_portent;
  for(const hint of parent.querySelectorAll('[data-school-target-state]')){const ally=h?.selectedAlly?.(),id=s.projected_ward_target;hint.textContent=id?(String(ally?.id)===String(id)?'Osłaniasz: '+(ally.name||'członka drużyny')+'.':'Osłona przygotowana na członka drużyny.'):'Osłona chroni ciebie.';}
  for(const b of parent.querySelectorAll('[data-school-target]')){const a=s.actions?.find(a=>a.id==='projected_ward');b.disabled=!p?.alive||!a?.enabled||(b.dataset.schoolTarget==='selected'&&!schoolTargetAllowed(p,h?.selectedAlly?.()));}
 }
 function schoolPanel(parent,p,h){
  const s=p.character_sheet?.caster?.school;if(p.class_id!=='mage'||!s)return;
  const box=node('section',undefined,'caster-schools'),current=()=>h.state?.().player||p;
  box.append(node('h3','Szkoła czarodzieja'));
  if(!s.id){
   const choice=schoolCandidates.get(String(p.id))||{},cards=node('div',undefined,'caster-order-grid wizard-school-grid');
   box.append(node('small','Jedna szkoła od poziomu '+(s.required_level||3)+', po uzyskaniu promocji na Arcymaga. Możesz wcześniej poznać wszystkie zdolności.'));
   for(const option of s.options||[]){
    const b=button('',()=>{const old=schoolCandidates.get(String(p.id));schoolCandidates.set(String(p.id),{id:option.id,confirmed:old?.id===option.id&&!!old.confirmed});parent.replaceChildren();feats(parent,current(),h);});
    b.className='caster-order wizard-school'+(choice.id===option.id?' candidate':'');b.dataset.school=option.id;b.setAttribute('aria-pressed',String(choice.id===option.id));
    b.append(image(option.icon||schoolIcons[option.id]),node('strong',option.name),node('small',option.description));cards.append(b);
   }box.append(cards);
   const selected=s.options?.find(o=>o.id===choice.id);
   if(selected){
    const preview=node('div',undefined,'school-preview');preview.append(node('h4',selected.name));
    for(const f of selected.features||[])preview.append(node('p',`Poziom ${f.level}: ${f.name} — ${f.description}`,'circle-feature-preview'));
    const label=node('label',undefined,'school-permanent-confirm'),check=node('input');check.type='checkbox';check.checked=!!choice.confirmed;check.dataset.schoolAcknowledge=selected.id;
    check.addEventListener('change',()=>{const picked=schoolCandidates.get(String(p.id));if(picked?.id===selected.id)schoolCandidates.set(String(p.id),{...picked,confirmed:check.checked});syncSchool(parent,current(),h);});
    label.append(check,node('span','Rozumiem, że wybór szkoły jest stały.'));preview.append(label);
    const confirm=button('Potwierdź wybór: '+selected.name,()=>{const latest=current(),picked=schoolCandidates.get(String(p.id));if(!schoolReason(latest)&&picked?.confirmed&&picked.id===selected.id&&schoolState(latest).options?.some(o=>o.id===picked.id))h.send({type:'wizard_school',school:picked.id});});confirm.dataset.schoolConfirm=selected.id;preview.append(confirm);box.append(preview);
   }
   box.append(node('small',schoolReason(p),'school-choice-reason'));
  }else{
   const selected=s.options?.find(o=>o.id===s.id),title=node('div',undefined,'school-current');title.append(image(s.icon||selected?.icon||schoolIcons[s.id]),node('strong',s.name||selected?.name||s.id));box.append(title);
   if(s.description||selected?.description)box.append(node('p',s.description||selected.description));
   for(const f of s.features||[]){const row=node('article',undefined,'circle-feature'+(f.unlocked?'':' locked'));row.append(node('strong',f.name),node('small',f.description),node('small',f.unlocked?'Dostępne':'Od poziomu '+f.level));box.append(row);}
  }parent.append(box);syncSchool(parent,p,h);
 }
 function schoolActions(parent,p,h){
  const s=schoolState(p);if(p.class_id!=='mage'||!s.id)return;
  const box=node('section',undefined,'wizard-school-actions'),current=()=>h.state?.().player||p;box.append(node('h3',s.name||'Zdolności szkoły'));
  const resources=node('div',undefined,'circle-resources');
  for(const r of s.resources||[]){const chip=node('span',`${r.name}: ${r.remaining}/${r.maximum}`);chip.dataset.schoolResource=r.id;resources.append(chip);}
  if(s.id==='abjuration'&&s.ward){const chip=node('span');chip.dataset.schoolWard='';resources.append(chip);}if(resources.childNodes.length)box.append(resources);
  const buttons=node('div',undefined,'circle-action-buttons');
  for(const action of s.actions||[]){
   if(['arm_portent','clear_portent','projected_ward'].includes(action.id))continue;
   const b=button(schoolActionLabel(s,action),()=>{const latest=current(),school=schoolState(latest),a=school.actions?.find(a=>a.id===action.id);if(!schoolActionAvailable(latest,school,a,h))return;if(a.kind==='spell')h.cast(a.spell_id||a.id);else h.send({type:'wizard_school_action',action:a.id,...(a.kind==='toggle'?{value:!schoolActionValue(school,a)}:{})});});
   b.dataset.schoolAction=action.id;if(action.description)b.title=action.description;buttons.append(b);
  }if(buttons.childNodes.length)box.append(buttons);
  if(s.id==='divination'){
   const portents=node('div',undefined,'wizard-portents');portents.append(node('strong','Przepowiednie'));
   for(const die of s.portents||[]){
    const row=node('div',undefined,'wizard-portent'+(die.spent?' spent':''));row.dataset.portentRow=String(die.index);row.append(node('strong',die.spent?'—':String(die.value),'portent-die'),node('small',die.spent?'Zużyty wynik':'Wynik k20','portent-status'));
    const controls=node('div',undefined,'portent-controls');
    for(const [mode,label] of Object.entries(portentModes)){
     const b=button(label,()=>{const latest=current();if(portentAvailable(latest,die.index,die.value))h.send({type:'wizard_school_action',action:'arm_portent',index:Number(die.index),mode});});b.dataset.portentIndex=String(die.index);b.dataset.portentValue=String(die.value);b.dataset.portentMode=mode;controls.append(b);
    }row.append(controls);portents.append(row);
   }
   const hint=node('small');hint.dataset.armedPortent='';portents.append(hint);
   const clear=button('Anuluj przygotowaną przepowiednię',()=>{const latest=current();if(latest.alive&&schoolState(latest).armed_portent)h.send({type:'wizard_school_action',action:'clear_portent'});});clear.dataset.portentClear='';portents.append(clear,node('small','Wyniki odnawiają się po długim odpoczynku. Przygotowanie przepowiedni nie zużywa jej; zużywa ją dopiero pasujący rzut.'));box.append(portents);
  }
  if(s.actions?.some(a=>a.id==='projected_ward')){
   const targets=node('div',undefined,'circle-target-controls');targets.append(node('small','Przeniesiona osłona · zaznacz członka drużyny w zasięgu 30 stóp, widocznego na tym samym piętrze.'));
   const choose=button('Osłaniaj zaznaczonego sojusznika',()=>{const latest=current(),ally=h.selectedAlly?.();if(schoolState(latest).actions?.find(a=>a.id==='projected_ward')?.enabled&&schoolTargetAllowed(latest,ally))h.send({type:'wizard_school_action',action:'projected_ward',target_id:String(ally.id)});});choose.dataset.schoolTarget='selected';
   const clear=button('Osłaniaj siebie',()=>{const latest=current();if(latest.alive&&schoolState(latest).actions?.find(a=>a.id==='projected_ward')?.enabled)h.send({type:'wizard_school_action',action:'projected_ward',target_id:''});});clear.dataset.schoolTarget='self';const hint=node('small');hint.dataset.schoolTargetState='';targets.append(choose,clear,hint);box.append(targets);
  }
  parent.append(box);syncSchool(parent,p,h);
 }
 function actions(parent,p,h){
  const c=p.character_sheet?.caster||{};
  if(c.channel?.key){const row=node('div',undefined,'caster-channel');row.append(node('strong',c.channel.name),node('small','Pozostało '+Math.max(0,Math.ceil(c.channel.remaining||0))+' s'),button('Przerwij',()=>h.send({type:'channel_cancel'})));parent.append(row);}
  if(c.familiar?.max_hp>0){const row=node('section',undefined,'caster-familiar');row.append(image('assets/spells/find_familiar.svg'),node('strong','Chowaniec · '+(c.familiar.mode==='help'?'Pomaga':'Podąża')));
   for(const [mode,label] of [['follow','Za mną'],['help','Pomagaj'],['scout','Zwiad'],['dismiss','Odeślij']])row.append(button(label,()=>h.send({type:'familiar_command',mode}),!p.alive));parent.append(row);}
  circleActions(parent,p,h);schoolActions(parent,p,h);
  if(elemental(p).id==='primal_strike'&&h.featSection!=='elemental_fury'){const box=node('section',undefined,'caster-elemental-actions');box.append(node('h3','Pierwotne uderzenie'));elementalDamagePicker(box,p,h);parent.append(box);}
  if(p.environment?.in_water){const box=node('section',undefined,'caster-water');box.append(node('strong','W wodzie'));const b=button(p.environment.submerged?'Wynurz się':'Zanurkuj',()=>{const latest=h.state?.().player||p;if(latest.alive&&latest.environment?.in_water)h.send({type:'environment_action',action:'dive',enabled:!latest.environment.submerged});},!p.alive);b.dataset.dive='';const breath=node('small',p.environment.submerged&&Number.isFinite(p.environment.breath_remaining)?`Pozostały oddech: ${Math.ceil(p.environment.breath_remaining)} s`:'');breath.dataset.breath='';box.append(b,breath);parent.append(box);}
  const exploration=node('section',undefined,'caster-exploration'),study=button('Zbadaj zaznaczony cel',()=>{const latest=h.state?.().player||p,target=h.studyTarget?.();if(latest.alive&&!(latest.action_remaining>0)&&target)h.send({type:'environment_action',action:'study',...target});},!p.alive||p.action_remaining>0||!h.studyTarget?.()),search=button('Rozejrzyj się',()=>{const latest=h.state?.().player||p;if(latest.alive&&!(latest.action_remaining>0))h.send({type:'environment_action',action:'search'});},!p.alive||p.action_remaining>0);study.dataset.study='';search.dataset.search='';exploration.append(study,search,node('small','Badanie i rozglądanie zużywają akcję. Wskazówki pomagają w teście wybranej umiejętności.'));parent.append(exploration);
 }
 function feats(parent,p,h){
  const c=p.character_sheet?.caster||{},tr=p.character_sheet?.training||{};
  if(h.featSection==='ranger_style'){root.BractwoFighterUI.feats(parent,p,h);return;}
  if(h.featSection==='elemental_fury'){elementalPanel(parent,p,h);return;}
  if(!['general','training'].includes(h.featSection)){
  if(['knight','ranger'].includes(p.class_id))root.BractwoFighterUI.feats(parent,p,h);
  if(p.class_id==='druid'){
   const box=node('section',undefined,'caster-orders');box.append(node('h3','Ścieżka druida'));
   const candidate=candidates.get(p.id)||c.order||'';
   const cards=node('div',undefined,'caster-order-grid');
   for(const s of c.orders||[]){const b=button('',()=>{candidates.set(p.id,s.id);parent.replaceChildren();feats(parent,p,h);});b.className='caster-order'+(candidate===s.id?' candidate':'')+(c.order===s.id?' selected':'');b.dataset.order=s.id;b.append(image(s.icon),node('strong',s.name),node('small',s.description));if(c.order===s.id)b.append(node('em','Wybrana'));cards.append(b);}
   box.append(cards);
   if(candidate&&candidate!==c.order){const b=button(c.order?'Zmień ścieżkę':'Wybierz tę ścieżkę',()=>h.send({type:'primal_order',order:candidate}),!canChoose(p,h.nearMaster?.()));b.dataset.confirmOrder=candidate;box.append(b);}
   if(c.order)box.append(node('small','Zmiana u mistrza, poza walką.'));
   else box.append(node('small','Jeden bezpłatny wybór. Strażnik nie dodaje pancerza do plecaka.'));
   if(c.legacy_medium_grace)box.append(node('p','Wybierz ścieżkę, zanim zaczną obowiązywać nowe wymagania twojego średniego pancerza.','caster-warning'));
   parent.append(box);
   circlePanel(parent,p,h);elementalPanel(parent,p,h);
  }
  if(p.class_id==='mage')schoolPanel(parent,p,h);
  if(c.features?.length){const box=node('section',undefined,'caster-features');box.append(node('h3','Zdolności klasy'));
   for(const f of c.features){const row=node('article',undefined,'caster-feature');row.append(image(f.icon));const text=node('div');text.append(node('strong',f.name),node('small',f.description));row.append(text);if(f.id==='arcane_recovery'){const b=button('Odpocznij i odzyskaj',()=>h.cast(f.id),!canRecover(p));b.dataset.arcaneRecovery='';row.append(b);}box.append(row);}parent.append(box);}
  actions(parent,p,h);
  if(p.rest_resources?.length){const box=node('section',undefined,'rest-resource-list');box.append(node('h3','Zasoby odnawiane odpoczynkiem'));for(const resource of p.rest_resources){const chip=node('p',`${resource.name}: ${resource.remaining}/${resource.maximum}${resource.recovery?' · '+resource.recovery:''}`);chip.dataset.restResource=resource.id;box.append(chip);}parent.append(box);}
  if(c.forms?.length){const box=node('section',undefined,'caster-forms');box.append(node('h3','Postacie zwierzęce'));
   for(const f of c.forms){const b=button('',()=>h.cast('wild_shape_'+f.id),!f.unlocked||!p.alive||(!p.form&&!hasShapeUse(p)));b.dataset.form=f.id;b.className='caster-form'+(f.unlocked?'':' locked');const art=['mammoth','elephant','giant_scorpion','polar_bear','eagle'].includes(f.id)?'assets/creatures/'+f.id+'.svg':h.state?.().world?.spells?.['wild_shape_'+f.id]?.icon||'assets/spells/wild_shape_'+(['wolf','cat','black_bear','bear'].includes(f.id)?f.id:'bear')+'.svg';b.append(image(art),node('strong',p.form?'Powrót z przemiany':f.name),node('small',f.unlocked?`KP ${f.ac} · +${f.temp_hp} tymczasowych HP`:`Poziom ${f.level}`));box.append(b);}parent.append(box);}
  }
  if(h.featSection==='class')return;
  if(h.featSection!=='general'){
  const train=node('section',undefined,'training-owned');train.append(node('h3','Wyszkolenie'));
  for(const t of tr.granted||[]){const item=node('div',undefined,'training-chip');item.append(image(t.icon),node('span',t.name));item.title=t.sources.join(' · ');train.append(item);}parent.append(train);}
  if(h.featSection==='training')return;
  const owned=[...(tr.origin?.chosen?[tr.origin.chosen]:[]),...(tr.chosen||[])];
  if(owned.length){const row=node('section',undefined,'training-selected');row.append(node('h3','Wybrane atuty'));for(const f of owned){const item=node('article',undefined,'training-owned-feat');item.append(image(f.icon),node('strong',trainingSummary(f)),node('p',f.description));row.append(item);}parent.append(row);}
  const available=node('section',undefined,'training-available');
  if(tr.origin?.points>0)available.append(button('Wybierz pierwszy atut · poziom 1',()=>root.BractwoFeatUI.open('origin',h.state?.().player||p,h)));
  if(tr.points>0){available.append(node('h3','Dostępne wybory rozwoju: '+tr.points),button('Wybierz atut',()=>root.BractwoFeatUI.open('general',h.state?.().player||p,h)));}
  available.append(node('small','Kolejne wybory: '+(tr.levels||[]).join(', ')+'. Atuty i cechy korzystają ze wspólnej puli; pierwszy atut jest osobny.'));
  parent.append(available);

 }
 function createPrompt(h){const p=node('section',undefined,'fighter-choice caster-choice');p.id='casterChoice';p.hidden=true;
  const head=node('header'),title=node('strong'),description=node('p'),choose=button('Wybierz',()=>h.open('feats'));head.append(title,button('×',close));p.append(head,description,choose);
  (document.getElementById('hudLeftRail')||document.getElementById('gameUI')).append(p);const closed=new Set();
  function pending(x){const c=x?.character_sheet?.caster;return c?.school?.pending&&(c.school.promotion_met??x.promoted)&&x.level>=(c.school.required_level||3)?'school':c?.circle?.pending?'circle':c?.order_pending?'order':'';}
  function key(x){return pending(x)==='school'?'bractwo-wizard-school-choice-v1:'+x.id:pending(x)==='circle'?'bractwo-druid-circle-choice-v1:'+x.id:'bractwo-druid-choice-v1:'+x.id;}
  function close(){const x=h.player();if(x){closed.add(key(x));try{localStorage.setItem(key(x),'1');}catch{}}sync();}
  function sync(){const x=h.player(),kind=pending(x);let hidden=!kind;if(x){hidden=hidden||closed.has(key(x));try{hidden=hidden||localStorage.getItem(key(x))==='1';}catch{}}p.hidden=hidden;title.textContent=kind==='school'?'Szkoła czarodzieja':kind==='circle'?'Krąg druida':'Ścieżka druida';description.textContent=kind==='school'?'Promocja odblokowała wybór szkoły magii. Poznaj cztery szkoły i wybierz jedną.':kind==='circle'?'Wybierz krąg Ziemi, Księżyca, Morza lub Gwiazd.':'Strażnik czy Mistyk natury?';choose.textContent=kind==='school'?'Wybierz szkołę':kind==='circle'?'Wybierz krąg':'Wybierz ścieżkę';}
  return{sync};
 }
 root.BractwoCasterUI={trainingReason,feats,actions,createPrompt,canChoose,canRecover,hasShapeUse,syncTraining,syncCircle,syncSchool,elementalPanel,elementalReason,elementalPacket,syncElemental};if(typeof module!=='undefined')module.exports={canChoose,canRecover,hasShapeUse,trainingReason,trainingSummary,circleReason,schoolReason,schoolTargetAllowed,portentAvailable,elementalReason,elementalPacket};
})(globalThis);
