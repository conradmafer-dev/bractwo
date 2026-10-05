/* Promoted martial archetypes: preview locally, commit choices through the server. */
(function(root){'use strict';
 const ARCHETYPES={knight:['battle_master','champion'],ranger:['hunter']};
 const NAMES={battle_master:'Mistrz Bitewny',champion:'Czempion',hunter:'Myśliwy',precision:'Precyzyjny atak',riposte:'Riposta',parry:'Parowanie',trip:'Podcięcie',menacing:'Zastraszający atak',colossus_slayer:'Pogromca kolosów',horde_breaker:'Rozbijacz hord',giant_killer:'Zabójca olbrzymów'};
 const OFFENSE=['precision','trip','menacing'],REACTIONS=['riposte','parry'],PREY=['colossus_slayer','horde_breaker','giant_killer'];
 const candidates=new Map();
 const list=value=>Array.isArray(value)?value:[];
 const state=p=>p?.character_sheet?.martial||{};
 const key=p=>String(p?.id)+':'+String(p?.class_id);
 const icon=id=>'assets/feats/martial_'+id+'.svg';
 const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(text,fn)=>{const b=node('button',text);b.type='button';b.onclick=fn;return b;};
 function image(id){const e=node('img');e.src=icon(id);e.alt='';e.width=e.height=44;return e;}
 function options(p){return list(state(p).options).filter(o=>o&&ARCHETYPES[p?.class_id]?.includes(o.id));}
 function maneuvers(p){return list(state(p).maneuvers).filter(m=>m&&[...OFFENSE,...REACTIONS].includes(m.id));}
 function preyOptions(p){return list(state(p).prey_options).filter(o=>o&&PREY.includes(o.id));}
 function choiceReason(p){
  const s=state(p);
  if(!ARCHETYPES[p?.class_id])return 'Specjalizacje są dostępne dla wojownika i łowcy.';
  if(s.id)return 'Specjalizacja została już wybrana.';
  if(p.alive!==true)return 'Specjalizację wybierzesz po odrodzeniu.';
  if(p.form)return 'Specjalizację wybierzesz po zakończeniu przemiany.';
  if(p.rest?.kind||p.rest?.remaining>0)return 'Najpierw zakończ odpoczynek.';
  if(p.combat_remaining>0)return 'Specjalizację wybierzesz po zakończeniu walki.';
  const required=s.required_level??p.promotion?.required_level??3;
  if(!Number.isFinite(p.level)||p.level<required)return `Wybór od poziomu ${required} po uzyskaniu promocji.`;
  if(!(s.promotion_met===true||s.promotion_met===undefined&&p.promoted===true))return 'Najpierw kup promocję u mistrza profesji w mieście.';
  if(s.pending!==true||s.eligible!==true||!options(p).length)return s.selection_reason||'Wybór specjalizacji jest teraz niedostępny.';
  return '';
 }
 function selectionReason(p,c){
  const blocked=choiceReason(p);if(blocked)return blocked;
  if(!c||!options(p).some(o=>o.id===c.id))return 'Wybierz specjalizację.';
  if(c.id==='battle_master'){
   const ids=list(c.maneuvers),available=new Set(maneuvers(p).map(m=>m.id));
   if(ids.length!==3||new Set(ids).size!==3||ids.some(id=>!available.has(id)))return 'Wybierz dokładnie trzy różne manewry.';
  }
  if(c.id==='hunter'&&!preyOptions(p).some(o=>o.id===c.prey))return 'Wybierz jedną zdolność myśliwego.';
  if(c.confirmed!==true)return 'Potwierdź, że wybór specjalizacji i jej zdolności jest stały.';
  return '';
 }
 function selectionPacket(p,c){
  if(selectionReason(p,c))return null;
  return {type:'martial_choice',archetype:c.id,...(c.id==='battle_master'?{maneuvers:[...c.maneuvers]}:c.id==='hunter'?{prey:c.prey}:{})};
 }
 function armed(p,id){const s=state(p);return REACTIONS.includes(id)?s.reaction===id:s.armed_maneuver===id;}
 function validDice(d){return !!d&&[d.remaining,d.maximum,d.sides].every(Number.isInteger)&&d.maximum>0&&d.remaining>=0&&d.remaining<=d.maximum&&[8,10,12].includes(d.sides);}
 function actionReason(p,id){
  const s=state(p),m=maneuvers(p).find(m=>m.id===id);
  if(p?.class_id!=='knight'||s.id!=='battle_master'||!m||m.learned!==true)return 'Ten manewr nie jest opanowany.';
  if(p.alive!==true)return 'Manewr będzie dostępny po odrodzeniu.';
  if(p.form)return 'Manewr jest niedostępny podczas przemiany.';
  if(p.rest?.kind||p.rest?.remaining>0)return 'Najpierw zakończ odpoczynek.';
  if(s.actions_available!==true)return 'Manewry są teraz niedostępne.';
  if(!armed(p,id)&&(!validDice(s.dice)||s.dice.remaining<=0))return 'Brak kości przewagi. Odzyskaj je podczas krótkiego lub długiego odpoczynku.';
  return '';
 }
 function actionPacket(p,id){if(actionReason(p,id))return null;return {type:'martial_action',action:REACTIONS.includes(id)?'reaction':'maneuver',maneuver:armed(p,id)?'':id};}
 function actionLabel(p,id){return armed(p,id)?(REACTIONS.includes(id)?'Wyłącz reakcję':'Anuluj przygotowanie'):(REACTIONS.includes(id)?'Włącz reakcję':'Przygotuj na atak');}
 function diceText(p){const d=state(p).dice;if(!validDice(d))return 'Kości przewagi: —';return `Kości przewagi: ${d.remaining}/${d.maximum} · k${d.sides}`;}
 function sync(parent,p){
  const c=candidates.get(key(p));
  for(const b of parent.querySelectorAll('[data-martial-confirm]')){const reason=selectionReason(p,c);b.disabled=!!reason;b.title=reason;}
  for(const hint of parent.querySelectorAll('[data-martial-choice-reason]'))hint.textContent=selectionReason(p,c);
  for(const b of parent.querySelectorAll('[data-martial-action]')){const id=b.dataset.martialAction,reason=actionReason(p,id);b.disabled=!!reason;b.title=reason;b.textContent=actionLabel(p,id);b.setAttribute('aria-pressed',String(armed(p,id)));}
  for(const row of parent.querySelectorAll('[data-martial-control]'))row.classList.toggle('active',armed(p,row.dataset.martialControl));
  for(const chip of parent.querySelectorAll('[data-martial-dice]'))chip.textContent=diceText(p);
 }
 function actions(parent,p,h){
  const s=state(p);if(p?.class_id!=='knight'||s.id!=='battle_master')return;
  const current=()=>h.state?.().player||p,box=node('section',undefined,'martial-actions');box.append(node('h3','Manewry Mistrza Bitewnego','sheet-section-title'));
  const resource=node('strong',diceText(p),'martial-resource');resource.dataset.martialDice='';resource.setAttribute('aria-live','polite');box.append(resource,node('p','Kości odnawiają się po krótkim lub długim odpoczynku. Przygotowanie manewru nie zużywa kości.','sheet-hint'));
  const learned=maneuvers(p).filter(m=>m.learned===true);
  for(const [ids,title,hint] of [[OFFENSE,'Następny atak','Przygotuj jeden manewr ofensywny. Zadziała przy najbliższym odpowiednim ataku bronią.'],[REACTIONS,'Reakcja','Włącz Ripostę albo Parowanie. Reakcja uruchomi się automatycznie przy spełnieniu warunków, jeśli masz kość przewagi i dostępną reakcję.']]){
   const entries=learned.filter(m=>ids.includes(m.id));if(!entries.length)continue;
   box.append(node('h4',title),node('p',hint,'sheet-hint'));
   for(const m of entries){const row=node('article',undefined,'martial-control');row.dataset.martialControl=m.id;row.append(image(m.id));const text=node('div');text.append(node('strong',m.name||NAMES[m.id]),node('p',m.description||''),node('small',REACTIONS.includes(m.id)?'Koszt: 1 kość przewagi i reakcja.':'Koszt: 1 kość przewagi; część ataku bronią.'));const b=button(actionLabel(p,m.id),()=>{const packet=actionPacket(current(),m.id);if(packet)h.send(packet);});b.dataset.martialAction=m.id;text.append(b);row.append(text);box.append(row);}
  }
  box.append(node('small','Pula rośnie do 5 kości na poziomie 7 i 6 na poziomie 15. Kości rosną do k10 na poziomie 10 i k12 na poziomie 18.','sheet-hint'));parent.append(box);sync(box,p);
 }
 function feats(parent,p,h){
  if(!ARCHETYPES[p?.class_id])return;
  const section=node('section',undefined,'martial-section');parent.append(section);
  const current=()=>h.state?.().player||p;
  function paint(){
   const latest=current(),s=state(latest),k=key(latest);section.replaceChildren();section.append(node('h3',latest.class_id==='knight'?'Archetyp wojownika':'Specjalizacja łowcy','sheet-section-title'));
   if(s.id){
    const id=s.id,chosen=options(latest).find(o=>o.id===id);if(!ARCHETYPES[latest.class_id]?.includes(id)){section.append(node('p','Specjalizacja jest teraz niedostępna.','sheet-hint'));return;}
    const title=node('div',undefined,'martial-current');title.append(image(id),node('strong',s.name||chosen?.name||NAMES[id]));section.append(title);
    if(id==='champion'){const threshold=[18,19].includes(s.critical_threshold)?s.critical_threshold:19;section.append(node('p',`Trafienie krytyczne bronią przy naturalnym ${threshold===18?'18, 19 lub 20':'19 lub 20'} na k20.`),node('small','Od poziomu 15: trafienie krytyczne również przy naturalnym 18.','sheet-hint'));}
    if(id==='hunter'){const prey=preyOptions(latest).find(o=>o.id===s.prey);if(prey){const row=node('article',undefined,'martial-control');row.append(image(prey.id));const text=node('div');text.append(node('strong',prey.name||NAMES[prey.id]),node('p',prey.description||''),node('small',prey.id==='giant_killer'?'Działa automatycznie; zużywa dostępną reakcję.':'Działa automatycznie przy spełnieniu warunków.'));row.append(text);section.append(row);}}
    actions(section,latest,h);return;
   }
   section.append(node('p',`Od poziomu ${s.required_level??latest.promotion?.required_level??3} po uzyskaniu promocji. Wybór jest bezpłatny i stały; nie zużywa punktu atutu.`,'sheet-hint'));
   const c=candidates.get(k)||{id:'',maneuvers:[],prey:'',confirmed:false},grid=node('div',undefined,'martial-options');grid.setAttribute('aria-label','Wybór specjalizacji');
   for(const o of options(latest)){const b=button('',()=>{const old=candidates.get(k);candidates.set(k,old?.id===o.id?old:{id:o.id,maneuvers:[],prey:'',confirmed:false});paint();});b.className='martial-option'+(c.id===o.id?' selected':'');b.dataset.martialArchetype=o.id;b.setAttribute('aria-pressed',String(c.id===o.id));b.append(image(o.id),node('strong',o.name||NAMES[o.id]),node('small',o.description||''));grid.append(b);}section.append(grid);
   const selected=options(latest).find(o=>o.id===c.id);
   if(selected){
    if(c.id==='battle_master'){
     section.append(node('h4',`Wybierz trzy manewry · ${list(c.maneuvers).length}/3`),node('p','Otrzymasz 4 kości przewagi k8. Każdy manewr kosztuje jedną kość.','sheet-hint'));
     const grid=node('div',undefined,'martial-maneuver-options');
     for(const m of maneuvers(latest)){const checked=list(c.maneuvers).includes(m.id),b=button('',()=>{const old=candidates.get(k);if(!old||old.id!=='battle_master')return;const ids=list(old.maneuvers);if(!ids.includes(m.id)&&ids.length>=3)return;candidates.set(k,{...old,maneuvers:ids.includes(m.id)?ids.filter(id=>id!==m.id):[...ids,m.id],confirmed:false});paint();});b.className='martial-option martial-maneuver-option'+(checked?' selected':'');b.dataset.martialManeuver=m.id;b.setAttribute('aria-pressed',String(checked));b.disabled=!checked&&list(c.maneuvers).length>=3;b.append(image(m.id),node('strong',m.name||NAMES[m.id]),node('small',m.description||''),node('em',checked?'Wybrany':REACTIONS.includes(m.id)?'Reakcja':'Atak'));grid.append(b);}section.append(grid);
    }
    if(c.id==='hunter'){
     section.append(node('h4','Wybierz jedną zdolność myśliwego'));const grid=node('div',undefined,'martial-prey-options');
     for(const o of preyOptions(latest)){const b=button('',()=>{const old=candidates.get(k);if(old?.id!=='hunter')return;candidates.set(k,{...old,prey:o.id,confirmed:false});paint();});b.className='martial-option'+(c.prey===o.id?' selected':'');b.dataset.martialPrey=o.id;b.setAttribute('aria-pressed',String(c.prey===o.id));b.append(image(o.id),node('strong',o.name||NAMES[o.id]),node('small',o.description||''));grid.append(b);}section.append(grid);
    }
    const label=node('label',undefined,'martial-acknowledge'),check=node('input');check.type='checkbox';check.checked=c.confirmed===true;check.dataset.martialAcknowledge='';check.addEventListener('change',()=>{const old=candidates.get(k);if(old?.id===selected.id)candidates.set(k,{...old,confirmed:check.checked});sync(section,current());});label.append(check,node('span','Potwierdzam stały wybór specjalizacji'+(c.id==='battle_master'?' i trzech manewrów':c.id==='hunter'?' i jednej zdolności':'')+'.'));section.append(label);
    const confirm=button('Potwierdź wybór: '+(selected.name||NAMES[selected.id]),()=>{const latest=current();const packet=selectionPacket(latest,candidates.get(key(latest)));if(packet){confirm.disabled=true;h.send(packet);}});confirm.dataset.martialConfirm=selected.id;section.append(confirm);
   }
   const reason=node('p',undefined,'martial-reason');reason.dataset.martialChoiceReason='';reason.setAttribute('aria-live','polite');section.append(reason);sync(section,latest);
  }paint();
 }
 function createPrompt(h){
  const panel=node('aside',undefined,'fighter-choice martial-choice');panel.id='martialChoice';panel.hidden=true;panel.setAttribute('aria-label','Wybór specjalizacji po promocji');const head=node('header'),title=node('strong'),closed=new Set(),dismissKey=p=>'bractwo-martial-choice-v1:'+key(p);
  const close=button('×',()=>{const p=h.player();if(p){closed.add(key(p));try{root.localStorage?.setItem(dismissKey(p),'1');}catch{}}syncPrompt();});close.setAttribute('aria-label','Wybierz specjalizację później');head.append(title,close);panel.append(head,node('p','Promocja odblokowała nowe zdolności. Wybierz specjalizację w karcie postaci.'),button('Wybierz specjalizację',()=>h.open('feats')));(document.getElementById('hudLeftRail')||document.getElementById('gameUI')).append(panel);
  function syncPrompt(){const p=h.player();let hidden=!!choiceReason(p);if(p){hidden=hidden||closed.has(key(p));try{hidden=hidden||root.localStorage?.getItem(dismissKey(p))==='1';}catch{}}panel.hidden=hidden;title.textContent=p?.class_id==='ranger'?'Specjalizacja łowcy':'Archetyp wojownika';}
  return {sync:syncPrompt};
 }
 const api={feats,actions,sync,createPrompt,choiceReason,selectionReason,selectionPacket,actionReason,actionPacket,actionLabel,diceText};root.BractwoMartialUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
