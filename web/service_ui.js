/* One selected NPC and one service at a time, in the right-hand panel. */
(function(root){'use strict';
 const MENUS={bank:[['bank','Bank'],['depot','Depozyt']],master:[['promotion','Promocja'],['blessing','Błogosławieństwo'],['mastery','Mistrzostwo']],boat:[['boat','Przeprawy']],binding_stone:[['binding','Odrodzenie']]};
 function reason(p,npc){
  if(!p||p.hp<=0)return 'Usługa jest dostępna dla żywej postaci.';
  if(!npc||(p.floor||0)!==(npc.floor||0)||Math.hypot(p.x-npc.x,p.y-npc.y)>(npc.radius||125))return 'Podejdź bliżej tej postaci lub kamienia.';
  if(p.combat_remaining>0)return 'Zakończ walkę i zaczekaj na koniec blokady.';
  return '';
 }
 function create(h){
  const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
  const btn=(text,fn,disabled=false)=>{const b=el('button',text);b.type='button';b.disabled=disabled;b.onclick=()=>{if(!b.disabled)fn();};return b;};
  const panel=el('section',undefined,'service-panel');panel.id='servicePanel';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-labelledby','serviceTitle');
  const head=el('header'),headText=el('div'),eyebrow=el('small','USŁUGI'),title=el('h2');title.id='serviceTitle';headText.append(eyebrow,title);
  const exit=btn('×',close);exit.setAttribute('aria-label','Zamknij usługę');head.append(headText,exit);
  const tabs=el('nav',undefined,'service-tabs');tabs.setAttribute('aria-label','Wybierz usługę');
  const warning=el('p',undefined,'service-warning');warning.setAttribute('role','status');
  const body=el('div',undefined,'service-body');body.id='serviceBody';body.setAttribute('role','tabpanel');
  panel.append(head,tabs,warning,body);document.getElementById('gameUI').append(panel);
  let npcId='',tab='',depotMode='deposit',signature='',focus;
  const state=()=>{const s=h.state();return {...s,npc:s.world?.npcs?.find(n=>n.id===npcId)};};
  function close(){panel.hidden=true;signature='';if(focus?.isConnected&&focus.getClientRects().length)focus.focus({preventScroll:true});}
  function open(npc){if(!MENUS[npc?.service])return;focus=document.activeElement;h.prepare?.();npcId=npc.id;tab=MENUS[npc.service][0][0];depotMode='deposit';signature='';panel.hidden=false;render();exit.focus({preventScroll:true});}
  function command(type,extra={}){const {player:p,npc}=state();if(reason(p,npc))return;h.send({type,npc_id:npcId,...extra});}
  function text(message,cls){body.append(el('p',message,cls));}
  function action(label,type,disabled=false,extra={}){const b=btn(label,()=>command(type,extra),disabled);b.dataset.serviceAction=type;body.append(b);return b;}
  function render(){
   if(panel.hidden)return;const {player:p,world:w,npc}=state();if(!p||p.hp<=0||!npc){close();return;}
   const lock=reason(p,npc),home=(w.cities||[]).find(c=>c.id===p.home_city)?.name||'Przystań';
   const next=JSON.stringify([npcId,tab,depotMode,lock,p.gold,p.bank_gold,p.inventory,p.equipment,p.depot,p.home_city,p.level,p.promoted,p.blessed,p.mastery,p.mastery_points,p.promotion]);
   if(next===signature)return;signature=next;const scroll=body.scrollTop;body.replaceChildren();tabs.replaceChildren();
   title.textContent=npc.name;eyebrow.textContent=npc.service==='binding_stone'?'KAMIEŃ PRZYPISANIA':'USŁUGI · '+(npc.role||'Mieszkaniec');
   warning.textContent=lock;warning.hidden=!lock;panel.dataset.service=npc.service;panel.dataset.npcId=npcId;panel.dataset.tab=tab;
   for(const[id,label]of MENUS[npc.service]){const b=btn(label,()=>{tab=id;signature='';body.scrollTop=0;render();});b.dataset.serviceTab=id;b.setAttribute('aria-pressed',String(id===tab));b.setAttribute('aria-controls','serviceBody');tabs.append(b);}
   const blocked=!!lock;
   if(tab==='bank'){
    body.append(el('div','Skarbiec','service-eyebrow'),el('h3',(p.bank_gold||0).toLocaleString('pl-PL')+' złota'));
    text('Przy sobie: '+p.gold.toLocaleString('pl-PL')+' złota. Złoto w banku jest chronione przed karą śmierci.');
    action('Wpłać wszystko','bank_deposit',blocked||p.gold<1,{amount:'all'});
    action('Wypłać 100 złota','bank_withdraw',blocked||p.bank_gold<100,{amount:100});
    action('Wypłać wszystko','bank_withdraw',blocked||p.bank_gold<1,{amount:'all'});
   }else if(tab==='depot'){
    text(`Depozyt: ${(p.depot||[]).length}/120 · Plecak: ${(p.inventory||[]).length}/40`);
    const modes=el('nav',undefined,'service-tabs service-subtabs');modes.setAttribute('aria-label','Kierunek przenoszenia');
    for(const[id,label]of[['deposit','Odłóż z plecaka'],['withdraw','Zabierz z depozytu']]){const b=btn(label,()=>{depotMode=id;signature='';body.scrollTop=0;render();});b.dataset.depotMode=id;b.setAttribute('aria-pressed',String(depotMode===id));modes.append(b);}body.append(modes);
    const depositing=depotMode==='deposit',items=depositing?(p.inventory||[]).filter(i=>!Object.values(p.equipment||{}).includes(i.uid)):(p.depot||[]);
    const full=depositing?(p.depot||[]).length>=120:(p.inventory||[]).length>=40;
    if(!items.length)text(depositing?'Brak przedmiotów do odłożenia. Zdejmij wyposażenie, jeśli chcesz je zdeponować.':'Depozyt jest pusty.');
    for(const item of items){const row=el('article',undefined,'service-item'),img=el('img');img.src=item.icon||w.items?.[item.template]?.icon||'assets/equipment/empty.svg';img.alt='';row.append(img,el('strong',item.name+(item.quantity>1?' ×'+item.quantity:'')));
     const type=depositing?'depot_store':'depot_take',b=btn(depositing?'Odłóż':'Zabierz',()=>command(type,{uid:item.uid}),blocked||full);b.dataset.serviceAction=type;row.append(b);body.append(row);root.BractwoInventoryUI?.bind(row,item,w);}
   }else if(tab==='promotion'){
    const level=p.promotion?.required_level??3,cost=p.promotion?.cost??2000;
    body.append(el('h3',p.promoted?'Promocja uzyskana':'Wyższa ranga profesji'));
    text(p.promoted?'Masz już promocję.':`Od poziomu ${level} · jednorazowo ${cost} złota. Przy sobie: ${p.gold} złota.`);
    if(['mage','druid'].includes(p.class_id))text(p.class_id==='mage'?'Promocja odblokowuje wybór szkoły czarodzieja w C → Atuty.':'Promocja odblokowuje wybór kręgu druida w C → Atuty.');
    action(p.promoted?'✓ Promowany':'Kup promocję','promote',blocked||p.promoted||p.level<level||p.gold<cost);
    if(p.promoted&&['mage','druid'].includes(p.class_id))body.append(btn('Otwórz Atuty',()=>h.character?.('feats')));
   }else if(tab==='blessing'){
    body.append(el('h3',p.blessed?'Błogosławieństwo aktywne':'Ochrona na kolejną wyprawę'));
    text('Poziom 9 · 500 złota. Chroni połowę zwykłej kary złota i PD przy następnej śmierci. Czerwona czaszka wyłącza ochronę.');
    action(p.blessed?'✓ Aktywne':'Kup błogosławieństwo','bless',blocked||p.blessed||p.level<9||p.gold<500);
   }else if(tab==='mastery'){
    text(`Punkty mistrzostwa: ${p.mastery_points||0}. Pierwszy od poziomu 11 po promocji, następne co poziom.`);
    for(const[id,label]of[['power','Potęga'],['focus','Skupienie']]){body.append(el('h3',`${label}: ${p.mastery?.[id]||0}/20`));text(id==='focus'?'+4 maksymalnej many za punkt.':p.class_id==='mage'?'Nie wzmacnia Iskry ani czarów.':'Ataki bronią: +1 obrażeń co 10 punktów, maksymalnie +2.');action('Dodaj punkt','mastery',blocked||!p.promoted||p.level<11||!p.mastery_points||(p.mastery?.[id]||0)>=20,{branch:id});}
    action('Wyzeruj przydział · 200 złota','mastery_reset',blocked||p.gold<200||!Object.values(p.mastery||{}).some(n=>n>0));
   }else if(tab==='boat'){
    text('Bezpieczna przystań · wybierz miejsce docelowe.','service-safe');
    for(const route of(w.sea_routes||[]).filter(r=>(npc.routes||[]).includes(r.id))){const port=w.ports?.find(d=>d.id===route.to_id);if(!port)continue;const row=el('article',undefined,'service-route');row.append(el('h3',port.name),el('p',root.BractwoAdventureUI.routeText(route)));
     const why=root.BractwoAdventureUI.boatReason(p,npc,route),b=btn('Wypłyń',()=>command('boat',{route_id:route.id}),!!why);b.dataset.routeId=route.id;b.title=why;row.append(b);if(why)row.append(el('small',why,'service-warning'));body.append(row);}
   }else if(tab==='binding'){
    const city=w.cities?.find(c=>c.id===npc.city_id);body.append(el('h3',city?.name||'Miasto'));text('Obecne miejsce odrodzenia: '+home+'.');
    text('Przypisz się do tego kamienia, aby po śmierci wracać tutaj. Przypisanie jest bezpłatne; zmienisz je przy kamieniu w innym mieście.');
    action(p.home_city===npc.city_id?'✓ Przypisano tutaj':'Przypisz odrodzenie','bind_city',blocked||p.home_city===npc.city_id);
   }
   if((p.quests||[]).some(q=>q.npc_id===npc.id)||npc.dialogue)body.append(btn('Rozmowa i zlecenia',()=>h.conversation?.(npc),blocked));
   body.scrollTop=scroll;
  }
  return {open,close,render,get visible(){return !panel.hidden;}};
 }
 const api={create,reason,menus:MENUS};root.BractwoServiceUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
