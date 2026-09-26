/* Class grants, explicit druid path selection and duplicate-safe general feats. */
(function(root){'use strict';
 const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
 const button=(label,fn,disabled=false)=>{const b=node('button',label);b.type='button';b.disabled=disabled;b.onclick=fn;return b;};
 const image=path=>{const i=node('img');i.src=path;i.alt='';i.width=i.height=42;return i;};
 const abilityNames={strength:'Siła',dexterity:'Zręczność',constitution:'Kondycja'};
 const candidates=new Map();
 function canRecover(p){return !!p&&p.class_id==='mage'&&!!p.alive&&!p.form&&!p.character_sheet?.caster?.channel?.key&&p.mana<p.max_mana&&!(p.bonus_remaining>0)&&!((p.spell_cooldowns?.arcane_recovery||0)>0);}
 function canChoose(p,nearMaster){return p.class_id==='druid'&&!!p.alive&&!p.form&&!(p.combat_remaining>0)&&(!p.character_sheet?.caster?.order||!!nearMaster);}
 function actions(parent,p,h){
  const c=p.character_sheet?.caster||{};
  if(c.channel?.key){const row=node('div',undefined,'caster-channel');row.append(node('strong',c.channel.name),node('small','Pozostało '+Math.max(0,Math.ceil(c.channel.remaining||0))+' s'),button('Przerwij',()=>h.send({type:'channel_cancel'})));parent.append(row);}
  if(c.familiar?.max_hp>0){const row=node('section',undefined,'caster-familiar');row.append(image('assets/spells/find_familiar.svg'),node('strong','Chowaniec · '+(c.familiar.mode==='help'?'Pomaga':'Podąża')));
   for(const [mode,label] of [['follow','Za mną'],['help','Pomagaj'],['scout','Zwiad'],['dismiss','Odeślij']])row.append(button(label,()=>h.send({type:'familiar_command',mode}),!p.alive));parent.append(row);}
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
  }
  if(c.features?.length){const box=node('section',undefined,'caster-features');box.append(node('h3','Zdolności klasy'));
   for(const f of c.features){const row=node('article',undefined,'caster-feature');row.append(image(f.icon));const text=node('div');text.append(node('strong',f.name),node('small',f.description));row.append(text);if(f.id==='arcane_recovery')row.append(button('Użyj',()=>h.cast(f.id),!canRecover(p)));box.append(row);}parent.append(box);}
  actions(parent,p,h);
  if(c.forms?.length){const box=node('section',undefined,'caster-forms');box.append(node('h3','Postacie zwierzęce'));
   for(const f of c.forms){const b=button('',()=>h.cast('wild_shape_'+f.id),!f.unlocked||!p.alive||(!p.form&&(p.spell_cooldowns?.['wild_shape_'+f.id]||0)>0));b.dataset.form=f.id;b.className='caster-form'+(f.unlocked?'':' locked');b.append(image('assets/spells/wild_shape_'+f.id+'.svg'),node('strong',f.name),node('small',f.unlocked?`KP ${f.ac} · +${f.temp_hp} tymczasowych HP`:`Poziom ${f.level}`));box.append(b);}parent.append(box);}
  const train=node('section',undefined,'training-owned');train.append(node('h3','Wyszkolenie'));
  for(const t of tr.granted||[]){const item=node('div',undefined,'training-chip');item.append(image(t.icon),node('span',t.name));item.title=t.sources.join(' · ');train.append(item);}parent.append(train);
  if(tr.chosen?.length){const row=node('section',undefined,'training-selected');row.append(node('h3','Wybrane atuty'));for(const f of tr.chosen)row.append(node('p',f.name+' · +1 '+(abilityNames[f.ability]||f.ability)+(f.active===false?' · wymagania niespełnione':'')));parent.append(row);}
  const available=node('section',undefined,'training-available');available.append(node('h3','Atuty wyposażenia'+(tr.points?' · dostępne wybory: '+tr.points:'')));
  if(!tr.points)available.append(node('small','Wybory na poziomach '+(tr.levels||[]).join(', ')+'.'));
  const options=tr.options||[];
  for(const f of options){const row=node('article',undefined,'training-option');row.dataset.feat=f.id;row.append(image(f.icon));const text=node('div');text.append(node('strong',f.name),node('small',f.description));row.append(text);
   const select=node('select');select.setAttribute('aria-label',f.name+' · cecha');for(const a of f.abilities||[])select.append(new Option('+1 '+abilityNames[a],a));row.append(select);
   row.append(button('Wybierz',()=>h.send({type:'training_feat',feat:f.id,ability:select.value}),!tr.points||!p.alive||!!p.form||p.combat_remaining>0||!(f.abilities?.length)));available.append(row);}
  if(!options.length)available.append(node('p','Masz już dostępne wyszkolenia. Niewydane wybory pozostają zapisane.','sheet-hint'));
  parent.append(available);
 }
 function createPrompt(h){const p=node('section',undefined,'fighter-choice caster-choice');p.id='casterChoice';p.hidden=true;
  const head=node('header');head.append(node('strong','Ścieżka druida'),button('×',close));p.append(head,node('p','Strażnik czy Mistyk natury?'),button('Wybierz ścieżkę',()=>h.open('feats')));
  (document.getElementById('hudLeftRail')||document.getElementById('gameUI')).append(p);const closed=new Set();
  function key(x){return 'bractwo-druid-choice-v1:'+x.id;}
  function close(){const x=h.player();if(x){closed.add(String(x.id));try{localStorage.setItem(key(x),'1');}catch{}}sync();}
  function sync(){const x=h.player();let hidden=!x?.character_sheet?.caster?.order_pending;if(x){hidden=hidden||closed.has(String(x.id));try{hidden=hidden||localStorage.getItem(key(x))==='1';}catch{}}p.hidden=hidden;}
  return{sync};
 }
 root.BractwoCasterUI={feats,actions,createPrompt,canChoose,canRecover};if(typeof module!=='undefined')module.exports={canChoose,canRecover};
})(globalThis);
