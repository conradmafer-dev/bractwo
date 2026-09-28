/* Class grants, explicit druid path selection and duplicate-safe general feats. */
(function(root){'use strict';
 const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(label,fn,disabled=false)=>{const b=node('button',label);b.type='button';b.disabled=disabled;b.onclick=fn;return b;};
 const image=path=>{const i=node('img');i.src=path;i.alt='';i.width=i.height=42;return i;};
 const abilityNames={strength:'Siła',dexterity:'Zręczność',constitution:'Kondycja',intelligence:'Inteligencja',wisdom:'Mądrość',charisma:'Charyzma'};
 const candidates=new Map(),circleCandidates=new Map(),trainingChoices=new Map();
 function canRecover(p){return !!p&&p.class_id==='mage'&&!!p.alive&&!p.form&&!p.character_sheet?.caster?.channel?.key&&p.mana<p.max_mana&&p.character_sheet?.caster?.arcane_recovery_remaining>0&&!(p.rest?.remaining>0)&&!(p.rest_short_remaining>0)&&!(p.rest_block_remaining>0)&&!p.rest_block_reason;}
 function hasShapeUse(p){const resource=p?.character_sheet?.caster?.circle?.resources?.find(r=>r.id==='shape');return !resource||resource.remaining>0;}
 function canChoose(p,nearMaster){return p.class_id==='druid'&&!!p.alive&&!p.form&&!(p.combat_remaining>0)&&(!p.character_sheet?.caster?.order||!!nearMaster);}
 function trainingReason(p,feat,selection){
  if(!p?.alive)return 'Atut wybierzesz po odrodzeniu.';
  if(p.form)return 'Atut wybierzesz po zakończeniu przemiany.';
  if(p.combat_remaining>0)return 'Atut wybierzesz po zakończeniu walki.';
  if(!(p.character_sheet?.training?.points>0))return 'Brak dostępnego wyboru atutu.';
  if(!feat)return 'Ten atut nie jest już dostępny.';
  if(feat.ability_points===2){
   if(!Array.isArray(selection)||selection.length!==2||selection.some(a=>!feat.abilities?.includes(a)))return 'Przydziel oba punkty cech.';
   const allocation={};for(const a of selection)allocation[a]=(allocation[a]||0)+1;
   if(Object.entries(allocation).some(([a,n])=>Number(p.attributes?.[a]||0)+n>20))return 'Cecha nie może przekroczyć 20. Wybierz inny podział punktów.';
  }else if(!['tough','savage_attacker'].includes(feat.id)&&!feat.abilities?.includes(selection))return 'Wybierz dostępną cechę poniżej 20.';
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
  }syncCircle(parent,p,h);
 }
 const circleIcons={land:'assets/spells/entangle.svg',moon:'assets/spells/moonbeam.svg',sea:'assets/spells/ray_of_frost.svg',stars:'assets/spells/starry_wisp.svg'};
 function circleReason(p){
  const c=p?.character_sheet?.caster?.circle;
  if(c?.id)return 'Krąg został już wybrany.';
  if(!p?.alive)return 'Krąg wybierzesz po odrodzeniu.';
  if(p.form)return 'Krąg wybierzesz po zakończeniu przemiany.';
  if(p.combat_remaining>0)return 'Krąg wybierzesz po zakończeniu walki.';
  if(p.level<(c?.required_level||10))return 'Wybór od poziomu '+(c?.required_level||10)+'.';
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
 }
 function circlePanel(parent,p,h){
  const c=p.character_sheet?.caster?.circle;if(!c)return;
  const box=node('section',undefined,'caster-circles'),current=()=>h.state?.().player||p;
  box.append(node('h3','Krąg druida'));
  if(!c.id){
   const choice=circleCandidates.get(String(p.id))||{},candidate=choice.id||'',cards=node('div',undefined,'caster-order-grid');
   box.append(node('small','Wybierz jeden krąg od poziomu '+(c.required_level||10)+'. Wybór jest stały.'));
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
  const targetAction=c.id==='stars'?'chalice_target':c.id==='moon'&&p.level>=65?'shared_moonlight_target':'';
  if(targetAction){
   const targets=node('div',undefined,'circle-target-controls');targets.append(node('small',targetAction==='chalice_target'?'Dodatkowe leczenie Kielicha · sojusznik w 30 stopach':'Wspólny Księżycowy krok · sojusznik w 10 stopach'));
   const choose=button('Użyj zaznaczonego sojusznika',()=>{const latest=h.state?.().player||p,ally=h.selectedAlly?.();if(circleTargetAllowed(latest,ally,targetAction))h.send({type:'circle_command',action:targetAction,value:String(ally.id)});});choose.dataset.circleTarget=targetAction;choose.dataset.circleTargetMode='selected';
   const reset=button(targetAction==='chalice_target'?'Leczenie domyślne':'Bez towarzysza',()=>h.send({type:'circle_command',action:targetAction,value:''}));reset.dataset.circleTarget=targetAction;reset.dataset.circleTargetMode='reset';targets.append(choose,reset);box.append(targets);
  }
  parent.append(box);syncCircle(parent,p,h);
 }
 function actions(parent,p,h){
  const c=p.character_sheet?.caster||{};
  if(c.channel?.key){const row=node('div',undefined,'caster-channel');row.append(node('strong',c.channel.name),node('small','Pozostało '+Math.max(0,Math.ceil(c.channel.remaining||0))+' s'),button('Przerwij',()=>h.send({type:'channel_cancel'})));parent.append(row);}
  if(c.familiar?.max_hp>0){const row=node('section',undefined,'caster-familiar');row.append(image('assets/spells/find_familiar.svg'),node('strong','Chowaniec · '+(c.familiar.mode==='help'?'Pomaga':'Podąża')));
   for(const [mode,label] of [['follow','Za mną'],['help','Pomagaj'],['scout','Zwiad'],['dismiss','Odeślij']])row.append(button(label,()=>h.send({type:'familiar_command',mode}),!p.alive));parent.append(row);}
  circleActions(parent,p,h);
  if(p.environment?.in_water){const box=node('section',undefined,'caster-water');box.append(node('strong','W wodzie'));const b=button(p.environment.submerged?'Wynurz się':'Zanurkuj',()=>{const latest=h.state?.().player||p;if(latest.alive&&latest.environment?.in_water)h.send({type:'environment_action',action:'dive',enabled:!latest.environment.submerged});},!p.alive);b.dataset.dive='';const breath=node('small',p.environment.submerged&&Number.isFinite(p.environment.breath_remaining)?`Pozostały oddech: ${Math.ceil(p.environment.breath_remaining)} s`:'');breath.dataset.breath='';box.append(b,breath);parent.append(box);}
  const exploration=node('section',undefined,'caster-exploration'),study=button('Zbadaj zaznaczony cel',()=>{const latest=h.state?.().player||p,target=h.studyTarget?.();if(latest.alive&&!(latest.action_remaining>0)&&target)h.send({type:'environment_action',action:'study',...target});},!p.alive||p.action_remaining>0||!h.studyTarget?.()),search=button('Rozejrzyj się',()=>{const latest=h.state?.().player||p;if(latest.alive&&!(latest.action_remaining>0))h.send({type:'environment_action',action:'search'});},!p.alive||p.action_remaining>0);study.dataset.study='';search.dataset.search='';exploration.append(study,search,node('small','Badanie i rozglądanie zużywają akcję. Wskazówki pomagają w teście wybranej umiejętności.'));parent.append(exploration);
 }
 function feats(parent,p,h){
  const c=p.character_sheet?.caster||{},tr=p.character_sheet?.training||{};
  if(p.class_id==='knight')root.BractwoFighterUI.feats(parent,p,h);
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
   circlePanel(parent,p,h);
  }
  if(c.features?.length){const box=node('section',undefined,'caster-features');box.append(node('h3','Zdolności klasy'));
   for(const f of c.features){const row=node('article',undefined,'caster-feature');row.append(image(f.icon));const text=node('div');text.append(node('strong',f.name),node('small',f.description));row.append(text);if(f.id==='arcane_recovery'){const b=button('Odpocznij i odzyskaj',()=>h.cast(f.id),!canRecover(p));b.dataset.arcaneRecovery='';row.append(b);}box.append(row);}parent.append(box);}
  actions(parent,p,h);
  if(p.rest_resources?.length){const box=node('section',undefined,'rest-resource-list');box.append(node('h3','Zasoby odnawiane odpoczynkiem'));for(const resource of p.rest_resources){const chip=node('p',`${resource.name}: ${resource.remaining}/${resource.maximum}${resource.recovery?' · '+resource.recovery:''}`);chip.dataset.restResource=resource.id;box.append(chip);}parent.append(box);}
  if(c.forms?.length){const box=node('section',undefined,'caster-forms');box.append(node('h3','Postacie zwierzęce'));
   for(const f of c.forms){const b=button('',()=>h.cast('wild_shape_'+f.id),!f.unlocked||!p.alive||(!p.form&&!hasShapeUse(p)));b.dataset.form=f.id;b.className='caster-form'+(f.unlocked?'':' locked');const art=['mammoth','elephant','giant_scorpion','polar_bear','eagle'].includes(f.id)?'assets/creatures/'+f.id+'.svg':h.state?.().world?.spells?.['wild_shape_'+f.id]?.icon||'assets/spells/wild_shape_'+(['wolf','cat','black_bear','bear'].includes(f.id)?f.id:'bear')+'.svg';b.append(image(art),node('strong',p.form?'Powrót z przemiany':f.name),node('small',f.unlocked?`KP ${f.ac} · +${f.temp_hp} tymczasowych HP`:`Poziom ${f.level}`));box.append(b);}parent.append(box);}
  const train=node('section',undefined,'training-owned');train.append(node('h3','Wyszkolenie'));
  for(const t of tr.granted||[]){const item=node('div',undefined,'training-chip');item.append(image(t.icon),node('span',t.name));item.title=t.sources.join(' · ');train.append(item);}parent.append(train);
  if(tr.chosen?.length){const row=node('section',undefined,'training-selected');row.append(node('h3','Wybrane atuty'));for(const f of tr.chosen)row.append(node('p',trainingSummary(f)));parent.append(row);}
  const available=node('section',undefined,'training-available');available.append(node('h3','Atuty'+(tr.points?' · dostępne wybory: '+tr.points:'')));
  if(!tr.points)available.append(node('small','Wybory na poziomach '+(tr.levels||[]).join(', ')+'.'));
  const options=tr.options||[];
  for(const f of options){const row=node('article',undefined,'training-option');row.dataset.feat=f.id;row.dataset.abilityPoints=String(f.ability_points||1);row.append(image(f.icon));const text=node('div');text.append(node('strong',f.name),node('small',f.description));row.append(text);
   const current=()=>h.state?.().player||p,key=String(p.id)+':'+f.id,saved=trainingChoices.get(key),pickers=node('div',undefined,'training-pickers');
   if(f.ability_points===2)pickers.append(node('small','Wybierz tę samą cechę dwa razy (+2) albo dwie różne (+1 i +1).'));
   for(let i=0;i<(f.abilities?.length?(f.ability_points===2?2:1):0);i++){
    const select=node('select');select.setAttribute('aria-label',f.name+(f.ability_points===2?' · punkt '+(i+1):' · cecha'));
    for(const a of f.abilities)select.append(new Option('+1 '+(abilityNames[a]||a),a));
    const remembered=Array.isArray(saved)?saved[i]:saved;if(f.abilities.includes(remembered))select.value=remembered;
    else if(i===1&&Number(p.attributes?.[select.value]||0)>=19){const other=f.abilities.find(a=>a!==select.value);if(other)select.value=other;}
    select.addEventListener('change',()=>{trainingChoices.set(key,trainingSelection(row));syncTraining(parent,current(),h);});pickers.append(select);
   }
   if(pickers.childNodes.length)text.append(pickers);
   text.append(node('small','','training-reason'));
   row.append(button('Wybierz',()=>{const latest=current(),feat=latest.character_sheet?.training?.options?.find(option=>option.id===f.id),selection=trainingSelection(row);if(!trainingReason(latest,feat,selection))h.send({type:'training_feat',feat:f.id,...(Array.isArray(selection)?{abilities:selection}:{ability:selection})});}));available.append(row);}
  if(!options.length)available.append(node('p','Brak dostępnych atutów. Niewydane wybory pozostają zapisane.','sheet-hint'));
  parent.append(available);syncTraining(parent,p,h);
 }
 function createPrompt(h){const p=node('section',undefined,'fighter-choice caster-choice');p.id='casterChoice';p.hidden=true;
  const head=node('header'),title=node('strong'),description=node('p'),choose=button('Wybierz',()=>h.open('feats'));head.append(title,button('×',close));p.append(head,description,choose);
  (document.getElementById('hudLeftRail')||document.getElementById('gameUI')).append(p);const closed=new Set();
  function pending(x){const c=x?.character_sheet?.caster;return c?.circle?.pending?'circle':c?.order_pending?'order':'';}
  function key(x){return pending(x)==='circle'?'bractwo-druid-circle-choice-v1:'+x.id:'bractwo-druid-choice-v1:'+x.id;}
  function close(){const x=h.player();if(x){closed.add(key(x));try{localStorage.setItem(key(x),'1');}catch{}}sync();}
  function sync(){const x=h.player(),kind=pending(x);let hidden=!kind;if(x){hidden=hidden||closed.has(key(x));try{hidden=hidden||localStorage.getItem(key(x))==='1';}catch{}}p.hidden=hidden;title.textContent=kind==='circle'?'Krąg druida':'Ścieżka druida';description.textContent=kind==='circle'?'Wybierz krąg Ziemi, Księżyca, Morza lub Gwiazd.':'Strażnik czy Mistyk natury?';choose.textContent=kind==='circle'?'Wybierz krąg':'Wybierz ścieżkę';}
  return{sync};
 }
 root.BractwoCasterUI={feats,actions,createPrompt,canChoose,canRecover,hasShapeUse,syncTraining,syncCircle};if(typeof module!=='undefined')module.exports={canChoose,canRecover,hasShapeUse,trainingReason,trainingSummary,circleReason};
})(globalThis);
