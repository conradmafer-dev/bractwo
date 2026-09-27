/* Shared item presentation: backpack, worn items, trader and quick potions. */
(function(root){'use strict';
 const damageNames={acid:'kwas',bludgeoning:'obuchowe',cold:'zimno',fire:'ogień',force:'moc',lightning:'błyskawice',necrotic:'nekrotyczne',piercing:'kłute',poison:'trucizna',psychic:'psychiczne',radiant:'promieniste',slashing:'cięte',thunder:'grzmot'};
 const node=(t,text,cls)=>{const e=document.createElement(t);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(text,fn,disabled=false)=>{const e=node('button',text);e.type='button';e.disabled=disabled;e.onclick=ev=>{ev.stopPropagation();fn();};return e;};
 function facts(item,w={}){
  const lines=[],p=item.preview||{},dtype=damageNames[p.damage_type||item.damage_type]||item.damage_type||'';
  if(item.slot==='potion'){
   lines.push('Odnawia '+(item.effect_summary||item.restore+' punktów'));
   lines.push('Liczba: '+(item.quantity||1));
  }else if(item.slot==='weapon'){
   lines.push(item.weapon_name?(item.weapon_name+(item.weapon_category?' · '+(item.weapon_category==='simple'?'Prosta':'Żołnierska'):'')):'Broń');
   if(Number.isFinite(p.attack))lines.push('Atak  1k20'+(p.attack>=0?'+':'')+p.attack);
   if(p.dice||item.damage_dice)lines.push('Obrażenia  '+(p.dice||item.damage_dice)+(dtype?' '+dtype:''));
   if(p.two_hand_dice)lines.push('Oburącz  '+p.two_hand_dice);
   else if(item.two_handed)lines.push('Dwuręczna');
   if(p.spell_bonus??item.spell_bonus)lines.push('Czary: atak i ST +'+(p.spell_bonus??item.spell_bonus));
   if(p.proficient===false)lines.push('Brak biegłości: −'+p.proficiency+' do trafienia');
   if(p.heavy_penalty)lines.push('Za mała '+(item.ranged?'Zręczność':'Siła')+' — utrudnienie');
   if(item.mastery_name)lines.push('Mistrzostwo  '+item.mastery_name+(p.mastery_active?'':' 🔒'));
  }else if(item.slot==='armor'){
   const kinds={none:'Szata',light:'Lekki pancerz',medium:'Średni pancerz',heavy:'Ciężki pancerz'};
   lines.push(kinds[item.armor_kind]||'Pancerz');
   if(Number.isFinite(p.ac))lines.push('Twoja KP  '+p.ac);
   else if(item.armor_summary)lines.push(item.armor_summary);
   if(p.armor_penalty)lines.push('Brak wyszkolenia — bez czarów, utrudnienie Siły/Zręczności');
   if(p.speed_penalty)lines.push('Za mała Siła — ruch −10 stóp');
  }else if(item.slot==='shield'){
   lines.push('Tarcza · +'+(item.shield_ac||2)+' KP');
   if(Number.isFinite(p.ac))lines.push('Twoja KP  '+p.ac);
   if(p.untrained_shield)lines.push('Brak wyszkolenia — bez premii KP');
  }else if(item.slot==='ring'){
   lines.push('Pierścień');
   if(item.ac_bonus)lines.push('KP +'+item.ac_bonus);
   if(item.attack_bonus)lines.push('Atak bronią +'+item.attack_bonus);
   if(item.attack)lines.push('Obrażenia +'+item.attack);
  }else if(item.description)lines.push(item.description);
  if(item.resistances?.length)lines.push('Odporność: '+item.resistances.map(x=>damageNames[x]||x).join(', '));
  if(item.min_level>1)lines.push('Poziom '+item.min_level);
  if(p.equip_error&&!p.equip_error.startsWith('Wymagany poziom'))lines.push(p.equip_error);
  if(item.sources?.length)lines.push('Zdobyto: '+[...new Set(item.sources.map(x=>x.name))].join(', '));
  return lines;
 }
 let tooltip,owner;
 function hide(){if(tooltip)tooltip.hidden=true;if(owner)owner.removeAttribute('aria-describedby');owner=null;}
 function show(anchor,item,w,x,y){
  if(!tooltip){tooltip=node('aside',undefined,'item-tooltip');tooltip.id='itemTooltip';tooltip.setAttribute('role','tooltip');document.body.append(tooltip);}
  tooltip.replaceChildren();tooltip.append(node('strong',item.name));
  for(const line of facts(item,w))tooltip.append(node('div',line));
  tooltip.hidden=false;owner=anchor;anchor.setAttribute('aria-describedby','itemTooltip');
  const r=anchor.getBoundingClientRect(),width=tooltip.offsetWidth,height=tooltip.offsetHeight;
  let left=(x??r.right)+14,top=(y??r.top)+14;
  if(left+width>innerWidth-8)left=(x??r.left)-width-14;
  if(top+height>innerHeight-8)top=innerHeight-height-8;
  tooltip.style.left=Math.max(8,left)+'px';tooltip.style.top=Math.max(8,top)+'px';
 }
 function bind(anchor,item,w){
  anchor.classList.add('item-hover');anchor.removeAttribute('title');anchor.dataset.itemTemplate=item.template||'';
  anchor.addEventListener('pointerenter',e=>{if(e.pointerType!=='touch')show(anchor,item,w,e.clientX,e.clientY);});
  anchor.addEventListener('pointermove',e=>{if(owner===anchor)show(anchor,item,w,e.clientX,e.clientY);});
  anchor.addEventListener('pointerleave',hide);anchor.addEventListener('focus',()=>show(anchor,item,w));anchor.addEventListener('blur',hide);anchor.addEventListener('pointerdown',hide);
 }
 root.addEventListener?.('scroll',hide,true);root.addEventListener?.('resize',hide);
 function detail(item,p,w,h){
  const pane=node('section',undefined,'sheet-item-detail');pane.dataset.previewUid=item.uid;
  const head=node('div',undefined,'item-preview-head');
  if(item.icon){const img=node('img');img.src=item.icon;img.alt='';head.append(img);}head.append(node('strong',item.name));pane.append(head);
  const stats=node('div',undefined,'item-facts');for(const line of facts(item,w))stats.append(node('div',line));pane.append(stats);
  if(item.mastery_name){const more=node('details',undefined,'item-mastery-info');more.append(node('summary',item.mastery_name),node('p',item.mastery_description||''));pane.append(more);}
  const actions=node('footer',undefined,'item-actions');
  const worn=Object.entries(p.equipment||{}).find(([,uid])=>String(uid)===String(item.uid));
  if(item.slot==='potion'){
   actions.append(button('Użyj',()=>h.send({type:'potion',item:item.template}),!p.alive||p.level<(item.min_level||1)));
   for(const slot of ['q','r'])actions.append(button((p.potion_slots?.[slot]===item.template?'✓ ':'Przypisz ')+slot.toUpperCase(),()=>h.send({type:'potion_bind',slot,item:item.template}),!p.alive||p.level<(item.min_level||1)));
  }else if(worn)actions.append(button('Zdejmij',()=>h.send({type:'unequip',slot:worn[0]}),!p.alive||!!p.form));
  else if(['weapon','armor','ring','shield'].includes(item.slot))actions.append(button('Załóż',()=>h.send({type:'equip',uid:item.uid}),!p.alive||!!p.form||!!item.preview?.equip_error||p.level<(item.min_level||1)));
  if(worn?.[0]==='weapon'&&item.versatile_dice){
   for(const [grip,label] of [['one','Jednorącz'],['two','Oburącz']])actions.append(button((p.character_sheet?.training?.grip===grip?'✓ ':'')+label,()=>h.send({type:'weapon_grip',grip}),!p.alive||!!p.form||p.combat_remaining>0));
  }
  if(h.canTrade?.()&&!worn){
   actions.append(button('Sprzedaj'+(item.slot==='potion'?' 1':'')+' · '+(item.value||0)+' zł',()=>h.send({type:'sell',uid:item.uid}),!p.alive));
   if((item.quantity||1)>1)actions.append(button('Stos · '+(item.value||0)*item.quantity+' zł',()=>h.send({type:'sell',uid:item.uid,quantity:item.quantity}),!p.alive));
  }
  pane.append(actions);return pane;
 }
 function createMerchant(h){
  const panel=node('section',undefined,'merchant-panel');panel.hidden=true;panel.id='merchantPanel';panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Kupiec');
  const header=node('header',undefined,'merchant-header');header.append(node('h2','Kupiec'),button('×',close));header.lastChild.setAttribute('aria-label','Zamknij handel');panel.append(header);
  const tabs=node('nav',undefined,'merchant-tabs');tabs.setAttribute('aria-label','Handel');tabs.setAttribute('role','tablist');
  let tab='buy',signature='',focus;
  for(const [key,label] of [['buy','Kupuj'],['sell','Sprzedaj']]){const b=button(label,()=>{tab=key;signature='';render();});b.dataset.tradeTab=key;b.setAttribute('role','tab');tabs.append(b);}panel.append(tabs);
  const summary=node('p',undefined,'merchant-summary'),body=node('div',undefined,'merchant-content');panel.append(summary,body);
  const foot=node('footer',undefined,'item-actions');foot.append(button('Odpoczynek',()=>h.rest?h.rest():h.send({type:'interact'})),button('Zamknij',close));panel.append(foot);document.getElementById('gameUI').append(panel);
  function close(){panel.hidden=true;hide();if(focus?.isConnected&&focus.getClientRects().length)focus.focus({preventScroll:true});}
  function open(){focus=document.activeElement;h.prepare?.();panel.hidden=false;signature='';render();tabs.firstChild.focus({preventScroll:true});}
  function render(){if(panel.hidden)return;const {player:p,world:w}=h.state();if(!p)return;const trade=h.canTrade();
   const key=JSON.stringify([tab,p.inventory,p.equipment,p.gold,p.level,p.alive,trade,p.item_previews]);if(key===signature)return;signature=key;
   summary.textContent=`Złoto: ${p.gold} · `+(trade?'Wybierz przedmiot.':'Handel tylko przy kupcu, poza walką.');foot.firstChild.disabled=!p.alive;
   for(const b of tabs.children){b.classList.toggle('active',b.dataset.tradeTab===tab);b.setAttribute('aria-selected',String(b.dataset.tradeTab===tab));}
   const scroll=body.scrollTop;body.replaceChildren();
   let items=tab==='buy'?Object.entries(w.items||{}).filter(([,spec])=>Number.isFinite(spec.price)).map(([key,spec])=>({...spec,template:key,preview:p.item_previews?.[key]})):p.inventory.filter(i=>!Object.values(p.equipment||{}).includes(i.uid));
   for(const item of items){const row=node('article',undefined,'merchant-item');row.dataset.template=item.template;
    const img=node('img');img.src=item.icon||'assets/equipment/empty.svg';img.alt='';row.append(img);
    const text=node('div',undefined,'merchant-item-text');text.append(node('strong',item.name+(item.quantity>1?' ×'+item.quantity:'')),node('small',(item.effect_summary||item.armor_summary||item.damage_dice||'')+(item.min_level>1?' · Poziom '+item.min_level:'')));row.append(text);
    const actions=node('div',undefined,'merchant-item-actions');const price=tab==='buy'?item.price:item.value;actions.append(node('span',`${price} zł / szt.`));
    if(tab==='buy')actions.append(button('Kup',()=>h.send({type:'buy',item:item.template}),!trade||p.gold<price||p.level<(item.min_level||1)));
    else{actions.append(button('Sprzedaj'+(item.quantity>1?' 1':''),()=>h.send({type:'sell',uid:item.uid}),!trade));if(item.quantity>1)actions.append(button('Cały stos',()=>h.send({type:'sell',uid:item.uid,quantity:item.quantity}),!trade));}
    row.append(actions);bind(row,item,w);body.append(row);
   }
   if(!items.length)body.append(node('p','Nie masz przedmiotów do sprzedaży. Założone wyposażenie pozostaje chronione.','sheet-hint'));
   body.scrollTop=scroll;
  }
  return {open,close,render,get visible(){return !panel.hidden;}};
 }
 const api={facts,bind,detail,hide,createMerchant};root.BractwoInventoryUI=api;if(typeof module!=='undefined')module.exports={facts};
})(globalThis);
