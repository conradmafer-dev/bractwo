/* D&D ability choices, proficiencies and actual checks. All results belong to the server. */
(function(root){'use strict';
 const abilityNames={strength:'Siła',dexterity:'Zręczność',constitution:'Kondycja',intelligence:'Inteligencja',wisdom:'Mądrość',charisma:'Charyzma'};
 const ids=Object.keys(abilityNames),drafts=new Map(),skillPicks=new Map(),asiPicks=new Map();
 const signed=n=>Number(n)>=0?'+'+n:String(n);
 const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
 const button=(label,fn)=>{const b=node('button','',label);b.type='button';b.onclick=fn;return b;};
 const current=(h,p)=>h.state?.().player||p;
 function choiceReason(p){if(!p?.alive)return 'Wybór po odrodzeniu.';if(p.class_chosen===false)return 'Najpierw wybierz profesję.';if(p.form||p.polymorph)return 'Wybór po zakończeniu przemiany.';if(p.combat_remaining>0)return 'Wybór po zakończeniu walki.';return '';}
 function buildCost(config,scores){if(!scores||ids.some(id=>!Number.isInteger(scores[id])||scores[id]<8||scores[id]>15||!Number.isFinite(Number(config?.costs?.[scores[id]]))))return NaN;return ids.reduce((sum,id)=>sum+Number(config.costs[scores[id]]),0);}
 function buildReason(p,draft){const reason=choiceReason(p),config=p?.character_sheet?.ability_build;if(reason)return reason;if(!config||config.chosen)return 'Cechy początkowe zostały już zatwierdzone.';const cost=buildCost(config,draft?.scores);if(!Number.isFinite(cost))return 'Każda cecha bazowa musi wynosić od 8 do 15.';if(cost!==config.points)return `Wydaj dokładnie ${config.points} punktów na cechy bazowe.`;const bonuses=ids.map(id=>draft?.background?.[id]);if(bonuses.some(v=>!Number.isInteger(v)||v<0||v>2)||bonuses.reduce((a,b)=>a+b,0)!==(config.background_points||3))return 'Premia pochodzenia: +2 i +1 albo +1 do trzech różnych cech.';return '';}
 function trainingPacket(p,feat,fields={}){return {type:'training_feat',feat,...fields,...(Number.isInteger(p.character_sheet?.training?.spent)?{expected_spent:p.character_sheet.training.spent}:{})};}
 function asiReason(p,selected){const reason=choiceReason(p),tr=p?.character_sheet?.training,option=tr?.options?.find(f=>f.id==='ability_score_improvement');if(reason)return reason;if(!(tr?.points>0))return 'Brak dostępnego wyboru rozwoju.';if(!option)return 'Zwiększenie cech jest obecnie niedostępne.';if(!Array.isArray(selected)||selected.length!==2||selected.some(id=>!option.abilities?.includes(id)))return 'Przydziel oba punkty cech.';const gains={};for(const id of selected)gains[id]=(gains[id]||0)+1;if(Object.entries(gains).some(([id,n])=>Number(p.attributes?.[id]||0)+n>(tr.score_cap||20)))return `Cecha nie może przekroczyć ${tr.score_cap||20}.`;return '';}
 function skillReason(p,source,id){const reason=choiceReason(p),pool=p?.character_sheet?.skills?.choices?.find(x=>x.source===source);if(reason)return reason;if(!(pool?.remaining>0))return 'Wszystkie wybory z tej puli zostały wykorzystane.';if(!pool.options?.some(x=>x.id===id))return 'Wybierz dostępną umiejętność.';return '';}
 function challengeReason(p,entry){if(!p?.alive)return 'Próba po odrodzeniu.';if(!entry)return 'To wyzwanie nie jest już w pobliżu.';if(entry.completed&&!entry.repeatable)return 'Wyzwanie ukończone.';if(entry.available!==true)return [entry.reason||'Podejdź bliżej, aby wykonać próbę.',entry.cooldown_remaining>0?`Kolejna próba za ${Math.ceil(entry.cooldown_remaining)} s.`:''].filter(Boolean).join(' ');return '';}
 function getDraft(p){const key=String(p.id),c=p.character_sheet.ability_build;let d=drafts.get(key);if(!d){d={scores:{...(c.initial_scores||Object.fromEntries(ids.map((id,i)=>[id,[15,14,13,12,10,8][i]])))},background:{...Object.fromEntries(ids.map(id=>[id,0])),...(c.initial_background||{strength:2,constitution:1})},open:false};drafts.set(key,d);}return d;}
 function refreshBuild(box,p,d){const c=p.character_sheet?.ability_build||{},cost=buildCost(c,d.scores);box.querySelector('[data-build-budget]').textContent=`Punkty cech: ${Number.isFinite(cost)?cost:'—'} / ${c.points||27} · premia pochodzenia: ${ids.reduce((n,id)=>n+(Number(d.background[id])||0),0)} / ${c.background_points||3}`;for(const row of box.querySelectorAll('[data-build-ability]')){const id=row.dataset.buildAbility,v=Number(d.scores[id])+Number(d.background[id]);row.querySelector('output').textContent=`${v} (${signed(Math.floor((v-10)/2))})`;}
  const reason=buildReason(p,d),b=box.querySelector('[data-build-confirm]');b.disabled=!!reason;b.title=reason;box.querySelector('[data-build-reason]').textContent=reason||'Zatwierdzenie jest jednorazowe. Atuty zdobyte na wyższych poziomach doliczą się osobno.';}
 function abilityBuild(parent,p,h){const c=p.character_sheet?.ability_build;if(!c||c.chosen)return;const d=getDraft(p),box=node('details','sheet-build');box.open=h.initialExpanded||d.open;box.append(node('summary','',`Cechy początkowe · wybierz własny rozkład ${c.points} punktów`));box.addEventListener('toggle',()=>{d.open=box.open;});box.append(node('p','sheet-hint','Możesz jednorazowo zastąpić domyślne cechy profesji. Baza: 8–15. Premia pochodzenia: +2 i +1 albo trzy razy +1.'));
  const budget=node('strong','sheet-build-budget');budget.dataset.buildBudget='';box.append(budget);const grid=node('div','sheet-build-grid');
  for(const id of ids){const row=node('div','sheet-build-row');row.dataset.buildAbility=id;row.append(node('strong','',abilityNames[id]));for(const [kind,label]of [['scores','Baza'],['background','Pochodzenie']]){const wrap=node('label'),select=node('select');select.setAttribute('aria-label',`${abilityNames[id]} · ${label}`);for(let n=kind==='scores'?8:0;n<=(kind==='scores'?15:2);n++)select.append(new Option(kind==='scores'?`${n} · koszt ${c.costs[n]}`:`+${n}`,String(n)));select.value=String(d[kind][id]);select.addEventListener('change',()=>{d[kind][id]=Number(select.value);refreshBuild(box,current(h,p),d);});wrap.append(node('small','',label),select);row.append(wrap);}row.append(node('output'));grid.append(row);}box.append(grid);
  const hint=node('p','sheet-choice-reason');hint.dataset.buildReason='';const confirm=button('Zatwierdź cechy na stałe',()=>{const latest=current(h,p);if(!buildReason(latest,d)){confirm.disabled=true;h.send({type:'ability_build',scores:{...d.scores},background:{...d.background}});}});confirm.dataset.buildConfirm='';box.append(hint,confirm);parent.append(box);refreshBuild(box,p,d);
 }
 function advancement(parent,p,h){const tr=p.character_sheet?.training;if(!tr)return;const box=node('section','sheet-advancement');box.append(node('h3','',`Rozwój cech i atutów · wybory: ${tr.points||0}`));
  const next=(tr.levels||[]).find(n=>n>p.level);box.append(node('p','sheet-hint',`Jeden wybór daje +2 do jednej cechy, +1 do dwóch cech albo jeden atut. Limit cechy: ${tr.score_cap||20}.${next?` Kolejny wybór: poziom ${next}.`:''}`));if(tr.migration_notice)box.append(node('p','sheet-hint',tr.migration_notice));
  if(tr.points>0){const option=tr.options?.find(f=>f.id==='ability_score_improvement');if(option){const key=String(p.id),saved=asiPicks.get(key),eligible=option.abilities||[],selected=saved||[eligible[0],eligible.find(id=>id!==eligible[0])||eligible[0]];asiPicks.set(key,selected);const controls=node('div','sheet-asi-controls');for(let i=0;i<2;i++){const label=node('label'),select=node('select');label.append(node('small','',`Punkt cechy ${i+1}`));select.setAttribute('aria-label',`Rozwój cech · punkt ${i+1}`);for(const id of eligible)select.append(new Option('+1 '+(abilityNames[id]||id),id));select.value=selected[i]||'';select.addEventListener('change',()=>{selected[i]=select.value;syncAdvancement(box,current(h,p));});label.append(select);controls.append(label);}const confirm=button('Zwiększ cechy',()=>{const latest=current(h,p),choices=asiPicks.get(key);if(!asiReason(latest,choices)){confirm.disabled=true;h.send(trainingPacket(latest,'ability_score_improvement',{abilities:[...choices]}));}});confirm.dataset.asiConfirm='';controls.append(confirm);box.append(controls);const reason=node('p','sheet-choice-reason');reason.dataset.asiReason='';box.append(reason);}
   box.append(button('Poznaj atuty zamiast zwiększania cech',()=>h.open?.('feats')));
  }else box.append(node('small','',`Poziomy rozwoju tej profesji: ${(tr.levels||[]).join(', ')}.`));parent.append(box);syncAdvancement(box,p);
 }
 function syncAdvancement(parent,p){const b=parent.querySelector('[data-asi-confirm]');if(!b)return;const choices=asiPicks.get(String(p.id)),reason=asiReason(p,choices);b.disabled=!!reason;b.title=reason;const summary={};for(const id of choices||[])summary[id]=(summary[id]||0)+1;parent.querySelector('[data-asi-reason]').textContent=reason||Object.entries(summary).map(([id,n])=>`${abilityNames[id]}: ${p.attributes?.[id]} → ${Number(p.attributes?.[id]||0)+n}`).join(' · ');}
 function originReason(p,id){const why=choiceReason(p),origin=p?.character_sheet?.training?.origin;if(why)return why;if(!origin||origin.chosen||!(origin.points>0))return 'Atut pochodzenia został już wybrany.';if(!origin.options?.some(o=>o.id===id))return 'Ten atut nie jest dostępny.';return '';}
 function origin(parent,p,h){const o=p.character_sheet?.training?.origin;if(!o)return;const box=node('section','sheet-advancement');
  if(o.chosen){box.append(node('h3','','Pierwszy atut · '+o.chosen.name),node('p','sheet-hint',o.chosen.description));}
  else if(o.points>0){box.append(node('h3','','Pierwszy atut · od poziomu 1'),node('p','sheet-hint','Masz jeden bezpłatny wybór. Nie zużywa on późniejszych wyborów cech lub atutów.'),button('Wybierz pierwszy atut',()=>root.BractwoFeatUI.open('origin',current(h,p),h)));}
  else return;parent.append(box);}

 function abilities(parent,p,h){advancement(parent,p,h);abilityBuild(parent,p,h);origin(parent,p,h);sync(parent,p,h);}
 function challenges(parent,p,h){
  const box=node('section','sheet-challenges'),data=h.state?.().skill_challenges||{nearby:[]};
  box.append(node('h3','',`Wydarzenia · ukończono ${data.completed_count||0}/${data.total||0}`));
  const entries=(data.nearby||[]).filter(e=>e.discovered||e.distance<=230).slice().sort((a,b)=>Number(a.completed)-Number(b.completed)||a.distance-b.distance);
  if(!entries.length)box.append(node('p','sheet-hint','Wypatruj ludzi potrzebujących pomocy, porzuconych zapasów i śladów przy drodze. Podejdź i naciśnij E albo kliknij wydarzenie.'));
  for(const e of entries){const row=node('article','sheet-challenge'+(e.completed?' completed':''));row.dataset.worldEventLink=e.id;row.append(node('strong','',e.name),node('p','',e.completed?e.aftermath:e.description));
   row.append(button(e.completed?'Przypomnij wydarzenie':'Przyjrzyj się',()=>h.openEvent?.(e)));
   if(h.navigate&&!e.completed)row.append(button('Wyznacz kierunek',()=>h.navigate(e)));box.append(row);
  }parent.append(box);
 }
 function skills(parent,p,h,section='list'){const s=p.character_sheet?.skills;if(!s){parent.append(node('p','sheet-hint','Oczekiwanie na umiejętności postaci…'));return;}const summary=node('div','sheet-skill-intro');summary.append(node('h3','',`Umiejętności · premia z biegłości ${signed(s.proficiency_bonus)}`),node('p','sheet-hint',s.description||'Test umiejętności: 1k20 + modyfikator cechy + biegłość, jeśli ją posiadasz. Ekspertyza podwaja premię z biegłości.'));if(section==='list')summary.append(button('Wydarzenia w pobliżu',()=>h.open?.('skills','challenges')));const expertise=s.choices?.find(pool=>pool.source==='expertise');if(section==='training'&&expertise&&!(expertise.remaining>0))summary.append(node('p','sheet-hint',expertise.description));parent.append(summary);
  if(section==='list'&&p.environment?.hide){const box=node('section','sheet-skill-choice'),b=button('',()=>{const latest=current(h,p),hide=latest.environment?.hide;if(latest.alive&&(hide?.active||hide?.available)){b.disabled=true;h.send({type:'environment_action',action:hide.active?'unhide':'hide'});}});b.dataset.hideAction='';box.append(node('strong','','Skradanie się przed potworami'),node('p','sheet-hint','Ukryj się przy osłonie lub we mgle. Test Zręczności (Skradanie), ST 15. Ukrycie działa na potwory; inni gracze nadal cię widzą.'),b);const reason=node('p','sheet-choice-reason');reason.dataset.hideReason='';box.append(reason);parent.append(box);}
  const roll=p.last_roll;if(section==='challenges'&&roll?.check==='ability'){const skill=s.skills?.find(x=>x.id===roll.skill);parent.append(node('p','sheet-hint',`Ostatni test · ${skill?.name||abilityNames[roll.ability]||'Umiejętność'}: ${root.BractwoRuntime?.checkRollLines(roll).join(' · ')||('1k20 = '+roll.roll+' · '+roll.roll+signed(roll.bonus)+' → '+roll.total+' / ST '+roll.defense+' · '+(roll.saved?'sukces':'niepowodzenie'))}`));}
  if(section==='training'){let pending=0;for(const pool of s.choices||[]){if(!(pool.remaining>0))continue;pending+=pool.remaining;const box=node('section','sheet-skill-choice');box.dataset.skillSource=pool.source;box.append(node('strong','',`${pool.name} · pozostało ${pool.remaining}/${pool.total}`),node('p','sheet-hint',pool.description));const key=String(p.id)+':'+pool.source,select=node('select'),controls=node('div','sheet-skill-choice-controls');select.setAttribute('aria-label',pool.name);select.append(new Option('Wybierz umiejętność…',''));for(const item of pool.options||[])select.append(new Option(`${item.name} · ${item.ability_name}`,item.id));select.value=skillPicks.get(key)||'';select.addEventListener('change',()=>{skillPicks.set(key,select.value);sync(parent,current(h,p),h);});const confirm=button(pool.source==='expertise'?'Wybierz ekspertyzę':'Wybierz biegłość',()=>{const latest=current(h,p),id=skillPicks.get(key);if(!skillReason(latest,pool.source,id)){confirm.disabled=true;h.send({type:'skill_train',source:pool.source,skill_id:id});}});confirm.dataset.skillConfirm=pool.source;const reason=node('p','sheet-choice-reason');reason.dataset.skillReason='';controls.append(select,confirm);box.append(controls,reason);parent.append(box);}if(!pending)parent.append(node('p','sheet-hint','Wszystkie dostępne biegłości zostały wybrane. Atut Wszechstronny pozwala nauczyć się trzech kolejnych.'));}
  if(section==='list'){const grid=node('div','sheet-skill-grid');for(const skill of s.skills||[]){const row=node('article','sheet-skill'+(skill.expertise?' expert':skill.proficient?' proficient':''));row.dataset.skill=skill.id;const head=node('div','sheet-skill-head');head.append(node('strong','',skill.name),node('b','sheet-skill-bonus',signed(skill.bonus)));row.append(head,node('small','sheet-skill-state',`${skill.ability_name} · ${skill.expertise?'Ekspertyza':skill.proficient?'Biegłość':'Bez biegłości'}`),node('p','',skill.description));if(skill.sources?.length)row.append(node('small','',skill.sources.join(' · ')));if(skill.id==='perception')row.append(node('small','',`Pasywna Percepcja: ${skill.passive}`));grid.append(row);}parent.append(grid);}if(section==='challenges')challenges(parent,p,h);sync(parent,p,h);
 }
 function sync(parent,p,h){syncAdvancement(parent,p);const build=parent.querySelector('.sheet-build');if(build&&p.character_sheet?.ability_build)refreshBuild(build,p,getDraft(p));for(const b of parent.querySelectorAll('[data-hide-action]')){const hide=p.environment?.hide;b.disabled=!p.alive||!(hide?.active||hide?.available);b.textContent=hide?.active?'Wyjdź z ukrycia':'Ukryj się';const reason=hide?.active?`Ukrycie aktywne${hide.remaining>0?' · '+Math.ceil(hide.remaining)+' s':''}`:hide?.reason||'';b.title=reason;parent.querySelector('[data-hide-reason]').textContent=reason;}for(const b of parent.querySelectorAll('[data-origin-feat]')){const reason=originReason(p,b.dataset.originFeat);b.disabled=!!reason;b.title=reason;}for(const row of parent.querySelectorAll('[data-skill-source]')){const source=row.dataset.skillSource,key=String(p.id)+':'+source,reason=skillReason(p,source,skillPicks.get(key)),b=row.querySelector('[data-skill-confirm]');b.disabled=!!reason;b.title=reason;row.querySelector('[data-skill-reason]').textContent=reason;}
  for(const row of parent.querySelectorAll('[data-skill-challenge]')){const entry=h.state?.().skill_challenges?.nearby?.find(e=>e.id===row.dataset.skillChallenge),reason=challengeReason(p,entry),b=row.querySelector('[data-challenge-confirm]');b.disabled=!!reason;b.title=reason;row.querySelector('[data-challenge-reason]').textContent=reason;}}
 function reminderState(){let sessionKey,closed=new Set();const key=p=>String(p?.id)+':'+(p?.character_sheet?.training?.earned??((p?.character_sheet?.training?.spent||0)+(p?.character_sheet?.training?.points||0)));
  function sync(p,session){if(session!==sessionKey){sessionKey=session;closed.clear();}const points=p?.character_sheet?.training?.points,count=Number.isInteger(points)&&points>0?points:0;return {count,visible:count>0&&!closed.has(key(p))};}
  return {sync,dismiss(p,session){sync(p,session);if(p)closed.add(key(p));return sync(p,session);}};
 }
 function originReminderState(){let sessionKey,closed=new Set();function sync(p,session){if(session!==sessionKey){sessionKey=session;closed.clear();}const o=p?.character_sheet?.training?.origin;return {visible:!!p&&p.class_chosen!==false&&p.alive!==false&&o?.points===1&&!o.chosen&&!closed.has(String(p.id))};}return {sync,dismiss(p,session){sync(p,session);if(p)closed.add(String(p.id));}};}
 function classChoice(p){const wizard=root.BractwoWizardBookUI?.pending(p);if(wizard)return wizard;const f=p?.character_sheet?.fighter,e=p?.character_sheet?.caster?.elemental_fury;if(p?.class_id==='ranger'&&p.level>=(f?.required_level||2)&&f?.pending&&!f.style)return {id:'ranger_style',title:'Styl walki łowcy',description:'Poziom 2 odblokował jeden bezpłatny styl walki albo dwie sztuczki Druidycznego wojownika.',label:'Wybierz styl walki'};if(p?.class_id==='druid'&&p.level>=(e?.required_level||7)&&e?.pending&&!e.id)return {id:'elemental_fury',title:'Furia żywiołów druida',description:'Poziom 7 odblokował wybór: Potężne sztuczki albo Pierwotne uderzenie.',label:'Wybierz Furię żywiołów'};return null;}
 function classReminderState(){let sessionKey,closed=new Set();const key=(p,choice)=>String(p?.id)+':'+choice?.id+':'+(choice?.token||'');function sync(p,session){if(session!==sessionKey){sessionKey=session;closed.clear();}const choice=classChoice(p);return {choice,visible:!!choice&&!closed.has(key(p,choice))};}return {sync,dismiss(p,session){const result=sync(p,session);if(result.choice)closed.add(key(p,result.choice));return sync(p,session);}};}
 function createPrompt(h){const state=reminderState(),originState=originReminderState(),classState=classReminderState(),panel=node('aside','advancement-choice');panel.id='advancementChoice';panel.hidden=true;panel.setAttribute('aria-label','Dostępny rozwój postaci');const head=node('header'),title=node('strong','','Rozwiń postać'),description=node('p');description.setAttribute('aria-live','polite');const close=button('×',()=>{state.dismiss(h.player(),h.session?.());originState.dismiss(h.player(),h.session?.());classState.dismiss(h.player(),h.session?.());refresh();});close.dataset.advancementDismiss='';close.setAttribute('aria-label','Przypomnij o rozwoju przy następnym logowaniu');head.append(title,close);const choices=node('div','advancement-choice-actions');
  const classButton=button('Wybierz zdolność klasy',()=>{const choice=classChoice(h.player());if(choice)h.open(choice.tab||'feats',choice.section||choice.id);});classButton.dataset.advancementClass='';choices.append(classButton);
  const first=button('Wybierz pierwszy atut',()=>h.pick?h.pick('origin'):h.open('feats','origin'));first.dataset.advancementOrigin='';choices.append(first);
  for(const [tab,label]of [['abilities','Rozwiń cechy'],['feats','Wybierz atut']]){const open=button(label,()=>tab==='feats'&&h.pick?h.pick('general'):h.open(tab));open.dataset.advancementOpen=tab;choices.append(open);}panel.append(head,description,choices);document.getElementById('gameUI').append(panel);
  function refresh(){const p=h.player(),result=state.sync(p,h.session?.()),origin=originState.sync(p,h.session?.()),classResult=classState.sync(p,h.session?.());panel.hidden=(!result.visible&&!origin.visible&&!classResult.visible)||p?.class_chosen===false||p?.alive===false;title.textContent=classResult.visible?classResult.choice.title:origin.visible?'Wybierz pierwszy atut':'Rozwiń postać';first.hidden=!origin.visible;classButton.hidden=!classResult.visible;classButton.textContent=classResult.choice?.label||'Wybierz zdolność klasy';classButton.dataset.advancementClass=classResult.choice?.id||'';for(const b of choices.querySelectorAll('[data-advancement-open]'))b.hidden=!result.visible;description.textContent=[classResult.visible?classResult.choice.description:'',origin.visible?'Masz bezpłatny wybór atutu od poziomu 1.':'',result.visible?`Dostępne wybory rozwoju: ${result.count}.`:''].filter(Boolean).join(' ');}
  return {sync:refresh};
 }

 const api={abilities,advancement,abilityBuild,origin,skills,sync,choiceReason,buildCost,buildReason,asiReason,skillReason,challengeReason,trainingPacket,originReason,reminderState,originReminderState,classChoice,classReminderState,createPrompt};root.BractwoSkillsUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);

/* UI_32: small world scenes, not map markers. The server owns every outcome. */
(function(root){'use strict';
 const ui=root.BractwoSkillsUI,TAU=Math.PI*2;
 function drawEvent(g,site,state={},time=0){
  if(!site?.scene)return;
  const done=!!state.completed,phase=time+(site.x||0)*.01;
  const rect=(x,y,w,h,c)=>{g.fillStyle=c;g.fillRect(Math.round(x),Math.round(y),w,h);};
  const oval=(x,y,rx,ry,c)=>{g.fillStyle=c;g.beginPath();g.ellipse(x,y,rx,ry,0,0,TAU);g.fill();};
  const line=(points,c,w=2)=>{g.strokeStyle=c;g.lineWidth=w;g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.stroke();};
  const poly=(points,c)=>{g.fillStyle=c;g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();g.fill();};
  const stone=(x,y,w=22)=>{poly([[x-w,y],[x-w+4,y-13],[x+6,y-20],[x+w,y-7],[x+w-3,y+5]],'#778276');line([[x-w+5,y-11],[x+6,y-16],[x+w-5,y-6]],'#bac0a0',3);};
  const sack=(x,y)=>{oval(x,y+7,13,6,'#172a234b');rect(x-10,y-15,20,24,'#b49a64');rect(x-8,y-17,16,5,'#decc8f');rect(x-8,y-8,5,13,'#d1bb81');line([[x-9,y-13],[x+9,y-13]],'#77603d');};
  const bottle=(x,y)=>{rect(x-3,y-9,6,4,'#b49961');rect(x-5,y-5,10,13,'#698e80');rect(x-3,y-3,6,9,'#bbd397');rect(x-3,y-3,2,5,'#e9f3c8');};
  const box=(x,y,open=false)=>{oval(x,y+10,25,8,'#16251b44');rect(x-22,y-14,44,27,'#775733');rect(x-20,y-12,40,22,'#a77c45');for(const xx of [-13,9])rect(x+xx,y-13,4,25,'#d2b074');line([[x-20,y],[x+20,y]],'#735636');if(open){rect(x-20,y-12,40,11,'#342f25');poly([[x-22,y-14],[x-16,y-37],[x+27,y-31],[x+22,y-13]],'#a48656');}else{rect(x-22,y-21,44,8,'#c5a269');rect(x-4,y-16,8,11,'#d6c47d');}};
  function human(x,y,coat='#8d794b',pose='stand',guard=false){
   const seated=pose==='sit',b=seated?Math.sin(phase*1.7)*.7:0;
   g.save();g.translate(x,y);oval(0,5,17,6,'#192a205c');
   if(seated){rect(-16,-3,33,8,'#414b3c');rect(10,1,22,5,'#645439');rect(22,0,7,6,'#dfd3ac');rect(31,3,6,5,'#48382d');}
   else{rect(-9,-3,7,9,'#5b4b36');rect(4,-3,7,9,'#5b4b36');rect(-10,4,9,4,'#322e27');rect(4,4,9,4,'#322e27');}
   const lift=seated?12:0;
   rect(-13,-26+lift+b,26,26-lift,guard?'#718781':coat);rect(-9,-25+lift+b,18,20-lift,guard?'#b1beb0':coat);
   rect(-8,-24+lift+b,5,15-lift,guard?'#d6decb':'#c1af7880');rect(-11,-8,23,4,'#625135');rect(-2,-8,5,4,'#d5bd77');
   line([[-13,-22+lift+b],[-17,-11+b],[-9,-5]],guard?'#82958c':coat,5);rect(-11,-8,6,5,'#e9bd86');
   line([[13,-22+lift+b],[16,-10+b],[10,-5]],coat,5);rect(8,-8,6,5,'#e9bd86');
   rect(-7,-40+lift+b,15,16,'#735137');rect(-6,-37+lift+b,13,12,'#e8b784');rect(-4,-37+lift+b,6,6,'#f3d0a0');rect(-4,-31+lift+b,2,2,'#343d30');rect(3,-31+lift+b,2,2,'#343d30');rect(-1,-27+lift+b,4,1,'#a57251');
   if(guard){rect(-9,-42+lift+b,19,7,'#94a69e');rect(-6,-46+lift+b,13,6,'#bbc9b9');rect(-1,-46+lift+b,4,7,'#ba6952');}
   else{rect(-9,-41+lift+b,18,4,coat);rect(-6,-46+lift+b,13,6,coat);}
   g.restore();
  }
  function reed(x,y){line([[x,y],[x-3,y-22]],'#52683d');line([[x,y],[x+7,y-19]],'#8d9b52');rect(x-6,y-25,5,7,'#a29155');}
  g.save();g.translate(site.x||0,site.y||0);g.lineJoin='round';g.lineCap='round';
  if(site.scene==='wounded_guard'){
   oval(0,6,62,20,'#354a2838');stone(19,-3,30);
   // A leaning river willow and low hanging fronds frame the patrol's shelter.
   poly([[30,-10],[36,-15],[43,-68],[38,-91],[33,-89],[36,-64]],'#6b6140');line([[38,-62],[21,-83],[4,-87]],'#8c7950',6);
   for(const [x,y]of [[6,-83],[24,-87],[44,-91],[58,-80]]){oval(x,y,21,11,'#4c713d');line([[x-7,y],[x-9,y+28],[x-13,y+37]],'#88a35a',4);line([[x+7,y],[x+5,y+20]],'#698a46',4);}
   if(done)human(-9,6,'#816c47','stand',true);else human(-8,8,'#816c47','sit',true);
   poly([[-48,4],[-48,-20],[-27,-21],[-25,2],[-36,12]],'#637a79');poly([[-44,-17],[-30,-17],[-30,0],[-36,7],[-43,0]],'#b3c2b2');rect(-38,-14,4,17,'#9b593f');
   line([[-62,19],[-22,25]],'#aa8d5a',3);poly([[-61,15],[-73,17],[-61,23]],'#bac8bd');line([[-6,27],[15,30]],'#aa8d5a',3);reed(63,17);
  }else if(site.scene==='broken_cart'){
   oval(-4,11,67,18,'#494c2d38');line([[-59,5],[54,7]],'#816039',5);line([[-58,12],[51,15]],'#b69861',2);
   g.save();g.translate(-5,0);if(!done)g.rotate(-.11);
   rect(-39,-31,76,32,'#6a4c2e');for(let i=0;i<4;i++)rect(-37,-29+i*7,71,5,i%2?'#b59155':'#caa568');
   for(const xx of[-32,27]){rect(xx,-34,5,41,'#6f5637');oval(xx,7,14,14,'#594932');oval(xx,7,10,10,'#c29e60');for(let i=0;i<6;i++){const a=i*TAU/6;line([[xx,7],[xx+10*Math.cos(a),7+10*Math.sin(a)]],'#674e31',2);}oval(xx,7,3,3,'#e0bd77');}
   sack(-18,-32);sack(8,-34);g.restore();
   if(!done){line([[6,18],[45,5]],'#665138',9);line([[8,15],[45,2]],'#c09c64',3);}
   else line([[-62,23],[-37,29]],'#8b6b43',6);
   human(64,8,'#a38b50',done?'stand':'sit');sack(49,31);
  }else if(site.scene==='road_dispute'){
   oval(0,7,64,18,'#54533825');human(28,12,'#668b8f');rect(36,-7,13,14,'#94704b');line([[38,-10],[43,-15],[48,-10]],'#5b4933');
   const age=Number.isFinite(state.completed_age)?state.completed_age:60;
   if(!done||age<4){g.save();if(done){g.translate(-Math.min(age,4)*15,-Math.min(age,4)*3);g.globalAlpha=Math.max(0,1-age/4);}human(-31,0,'#76563e');rect(-13,-22,13,10,'#ddc991');rect(-6,-18,3,3,'#a95343');g.restore();}
   line([[-66,10],[-66,-43]],'#7f633e',5);rect(-76,-43,31,14,'#b49b65');line([[-71,-38],[-51,-38]],'#6b5534');
  }else if(site.scene==='lost_pouch'){
   stone(-27,9,22);stone(24,13,19);reed(-45,22);reed(39,6);line([[-15,8],[4,5],[18,19]],'#806343',4);
   for(const [x,y]of[[-8,24],[-1,32],[-10,42]])oval(x,y,3,5,'#716f444f');
   if(!done){rect(-9,-3,20,17,'#704c2e');rect(-7,-2,16,12,'#a67940');rect(-6,-9,13,8,'#b38d50');rect(-1,-6,5,7,'#d9bb70');
    if(state.hint){const a=.45+Math.sin(phase*2)*.2;g.save();g.globalAlpha=a;line([[-4,-4],[6,-4]],'#fff1c6',1);line([[1,-9],[1,2]],'#fff1c6',1);g.restore();}}
  }else if(site.scene==='stolen_supplies'){
   poly([[-65,-5],[-26,-61],[29,-9]],'#81764f');poly([[-26,-61],[-16,-8],[29,-9]],'#5a6541');line([[-27,-61],[-70,7]],'#cbb17b',2);line([[-27,-61],[35,5]],'#cbb17b',2);
   line([[-65,25],[29,31]],'#655138',12);line([[-62,22],[27,28]],'#a28554',4);oval(-65,25,6,6,'#c2a16a');line([[-55,26],[-18,30]],'#443f2a',2);
   box(17,13,done);box(-25,7,done);if(!done){rect(11,-10,14,7,'#cfdbb5');line([[16,-9],[16,-4]],'#8d6c44',2);}
   oval(60,15,15,6,'#293e2b55');rect(48,-10,25,20,'#6c6241');oval(59,-17+Math.sin(phase)*.4,12,10,'#8ea652');poly([[49,-21],[40,-24],[47,-14]],'#8ea652');poly([[67,-21],[78,-24],[70,-13]],'#8ea652');line([[51,-18],[55,-18]],'#3c502e',2);line([[62,-18],[66,-18]],'#3c502e',2);oval(61,28,9,4,'#b09a66');
   if(!done)line([[34,8],[60,26]],'#baab7855',1);
  }else if(site.scene==='sealed_relic'){
   oval(0,8,68,25,'#4d5c4238');for(const [x,y]of[[-54,7],[49,-17]]){rect(x-10,y-32,22,38,'#858d78');rect(x-14,y-35,30,6,'#c6c4a1');rect(x-15,y+2,33,9,'#a6ad8f');rect(x-6,y-26,4,23,'#bec4a3');}
   rect(-34,-26,71,43,'#657266');rect(-30,-23,63,34,'#9da789');rect(-26,-20,55,27,done?'#36483c':'#7a8b75');
   if(done){poly([[-37,-27],[-28,-61],[45,-48],[36,-27]],'#c1c4a1');line([[-26,-55],[36,-45]],'#e1d7b0',2);}
   else{rect(-37,-34,76,10,'#c6c9a6');for(const x of[-18,0,18]){line([[x-4,-12],[x,-21],[x+5,-12],[x,-7],[x-4,-12]],'#cfcea4',2);}if(state.hint)rect(-20,-33,5,2,'#f2dc9c');}
   for(const [x,y]of[[-41,23],[-29,25],[40,20]]){rect(x,y,10,4,'#6a8344');rect(x+4,y-4,7,4,'#8ba358');}
  }else if(site.scene==='herbalist'){
   oval(-10,9,64,19,'#45533828');human(36,5,'#6e8c50','sit');oval(10,17,15,8,'#806240');line([[-3,10],[0,1],[18,1],[23,10]],'#b89a60',3);
   for(const [i,x,y]of[[0,-51,7],[1,-29,19],[2,-6,-4],[3,-37,-13]]){line([[x,y],[x,y-18]],'#496b39',2);oval(x-5,y-10,7,3,'#7f9a4c');oval(x+5,y-15,7,3,'#a2b85b');if(!done||i>1){rect(x-2,y-22,5,6,i%2?'#c3b677':'#d4ddb0');}}
   bottle(22,21);if(done){bottle(6,22);bottle(-5,20);}else rect(11,10,8,3,'#94b55b');stone(-66,-7,12);
  }else if(site.scene==='frightened_pony'){
   human(58,6,'#9e7f49');const hop=done?0:Math.max(0,Math.sin(phase*3)) * 2;
   g.save();g.translate(-22,-hop);oval(0,16,34,9,'#26382144');for(const x of[-23,16]){rect(x,0,7,20,'#ad8051');rect(x-1,16,9,5,'#51412e');}oval(0,-4,31,17,'#b28a57');oval(-8,-8,19,11,'#d2ae76');
   const nod=done?6:Math.sin(phase*2)*3;g.save();g.translate(25,-12+nod);poly([[-9,7],[-3,-26],[14,-27],[18,-1]],'#c49c67');oval(11,-24,13,11,'#d4b583');oval(20,-19,11,7,'#e1c495');poly([[1,-30],[0,-46],[7,-34]],'#c9a370');poly([[12,-31],[16,-44],[18,-29]],'#c9a370');rect(11,-28,3,3,'#3c342b');line([[-3,-31],[-9,-21],[-8,-1]],'#6b5035',6);line([[14,-24],[21,-14]],'#806641',2);g.restore();
   line([[-28,-10],[-39,-6],[-41,10+Math.sin(phase*2)*2]],'#6b5035',5);rect(-12,-15,26,19,'#776f48');rect(-10,-14,22,15,'#a39962');rect(-3,-15,4,20,'#635838');g.restore();
   line([[28,-25],[42,-9]],'#a08a5b',2);sack(65,28);sack(42,31);
  }
  g.restore();
 }
 function createEvents(h){
  const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
  const panel=node('section','world-event-panel');panel.id='worldEventPanel';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-labelledby','worldEventTitle');
  const header=node('header','world-event-header'),title=node('h2','', '');title.id='worldEventTitle';
  const closeButton=node('button','world-event-close','×');closeButton.type='button';closeButton.setAttribute('aria-label','Zamknij wydarzenie');closeButton.onclick=close;
  header.append(title,closeButton);const body=node('div','world-event-body');panel.append(header,body);document.getElementById('gameUI').append(panel);
  let id='',owner='',signature='',focus=null,pending=false,pendingUntil=0,receipt='',hintSession='',hints=new Set();
  function close(){if(panel.hidden)return;panel.hidden=true;pending=false;signature='';h.closed?.();if(focus?.isConnected&&focus.getClientRects().length)focus.focus({preventScroll:true});}
  function entry(){return h.state?.().skill_challenges?.nearby?.find(e=>e.id===id);}
  function open(site){if(!site?.id)return;focus=document.activeElement;h.prepare?.();owner=String(h.state?.().player?.id);id=site.id;signature='';pending=false;panel.hidden=false;render();closeButton.focus({preventScroll:true});}
  function render(){
   const state=h.state?.(),p=state?.player,session=String(h.session?.()??'')+':'+String(p?.id??'');
   if(session!==hintSession){hintSession=session;hints.clear();}
   const hint=(state?.skill_challenges?.nearby||[]).find(e=>e.hint&&!hints.has(e.id));
   if(hint){hints.add(hint.id);h.notice?.('Dostrzegasz: '+hint.hint);}
   if(panel.hidden)return;
   if(!p||!p.alive||String(p.id)!==owner){close();return;}
   const e=entry();if(!e){close();return;}
   const token=JSON.stringify([e.completed,e.cooldown_remaining>0,p.last_roll?.id]);
   if(pending&&(token!==receipt||performance.now()>pendingUntil))pending=false;
   const key=JSON.stringify([e.name,e.completed,e.description,e.dialogue,e.aftermath,e.failure,e.options,e.hint,p.last_roll?.target_name===e.name?p.last_roll.id:null,pending]);
   if(key===signature)return;signature=key;const scroll=body.scrollTop,focused=body.contains(document.activeElement)?document.activeElement.dataset.eventAction:null;body.replaceChildren();title.textContent=e.name;
   const canvas=node('canvas','world-event-preview');canvas.width=720;canvas.height=230;canvas.setAttribute('aria-hidden','true');const g=canvas.getContext('2d');g.scale(2,2);g.fillStyle='#203c30';g.fillRect(0,0,360,115);g.save();g.translate(180,80);g.scale(.75,.75);drawEvent(g,{...e,x:0,y:0},e,0);g.restore();body.append(canvas);
   if(!e.completed)body.append(node('p','world-event-description',e.description));body.append(node('p','world-event-dialogue',e.completed?e.aftermath:e.dialogue));
   if(e.hint&&!e.completed)body.append(node('p','world-event-hint',e.hint));
   const roll=p.last_roll;if(roll?.target_name===e.name){const receiptBox=node('div','world-event-roll');receiptBox.setAttribute('aria-live','polite');if(roll.check==='ability'){for(const line of root.BractwoRuntime?.checkRollLines(roll)||[])receiptBox.append(node('div','',line));receiptBox.append(node('b','',roll.saved?'Udało się':'Nie tym razem'));}else if(roll.check==='healing')receiptBox.append(node('div','',root.BractwoRuntime?.combatSummary(roll)||'Leczenie udane'));body.append(receiptBox);}
   if(e.completed){body.append(node('p','world-event-result',e.result),node('small','world-event-reward','Nagroda odebrana · '+e.reward_hint));}
   else{
    if(e.failure)body.append(node('p','world-event-failure',e.failure));
    const actions=node('div','world-event-actions');
    for(const option of e.options||[]){const b=node('button','world-event-action');b.type='button';b.dataset.eventAction=option.id;b.append(node('strong','',option.label));
     const cost=option.skill_name||option.cost_hint||'';if(cost)b.append(node('small','',cost));
     b.disabled=pending||!option.available;b.title=option.reason||'';
     if(option.reason)b.append(node('span','world-event-lock',option.reason));
     b.onclick=()=>{const latest=entry(),o=latest?.options?.find(o=>o.id===option.id);if(pending||!o?.available)return;receipt=JSON.stringify([latest.completed,latest.cooldown_remaining>0,h.state().player?.last_roll?.id]);pending=true;pendingUntil=performance.now()+2500;h.send({type:'skill_challenge',challenge_id:id,action_id:o.id});signature='';render();};actions.append(b);
    }body.append(actions);if(pending)body.append(node('p','world-event-working','Działasz…'));
    body.append(node('small','world-event-reward',e.reward_hint));
   }
   const leave=node('button','world-event-leave',e.completed?'Ruszaj dalej':'Odejdź');leave.type='button';leave.onclick=close;body.append(leave);body.scrollTop=scroll;
   if(focused)body.querySelector('[data-event-action="'+focused+'"]')?.focus({preventScroll:true});
  }
  panel.addEventListener('keydown',e=>{if(e.code==='Escape'||e.code==='KeyE'){e.preventDefault();e.stopPropagation();close();}else if(['Enter','Space'].includes(e.code))e.stopPropagation();});
  for(const event of ['pointerdown','touchstart','wheel'])panel.addEventListener(event,e=>e.stopPropagation());
  return {open,close,render,get visible(){return !panel.hidden;},get element(){return panel;}};
 }
 ui.drawEvent=drawEvent;ui.createEvents=createEvents;
})(globalThis);
