/* Nearby conversations, local quests and actual boat connections. */
(function(root){'use strict';
  // One explanation for every actual lock; destination danger is advisory.
  function boatReason(p,npc,route){
    if(!p||p.hp<=0)return 'Rejs jest dostępny dla żywej postaci.';
    if((p.floor||0)!==(npc.floor||0)||Math.hypot(p.x-npc.x,p.y-npc.y)>(npc.radius||125))return 'Podejdź bliżej przewoźnika.';
    if(p.combat_remaining>0)return 'Zakończ walkę i zaczekaj na koniec blokady.';
    if(p.gold<route.cost)return `Brakuje ${route.cost-p.gold} złota.`;
    return '';
  }
  function routeText(route){
    const danger=route.recommended_level||route.min_level||1;
    return `${route.cost?route.cost+' złota':'Przeprawa bezpłatna'}${danger>1?' · zalecany poziom '+danger:''}`;
  }
  function create(h){
    const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
    const button=(text,fn,disabled=false)=>{const e=node('button',text);e.type='button';e.disabled=disabled;e.onclick=fn;return e;};
    const panel=node('section',undefined,'adventure-panel');panel.id='adventurePanel';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-labelledby','adventureTitle');
    const header=node('header'),title=node('h2');title.id='adventureTitle';const exit=button('×',close);exit.setAttribute('aria-label','Zamknij rozmowę');header.append(title,exit);
    const body=node('div',undefined,'adventure-body');panel.append(header,body);document.getElementById('gameUI').append(panel);
    let npcId='',signature='',topic='',focus;
    function close(){panel.hidden=true;signature='';if(focus?.isConnected&&focus.getClientRects().length)focus.focus({preventScroll:true});}
    function open(npc){if(!npc)return;focus=document.activeElement;h.prepare?.();npcId=npc.id;topic='';signature='';panel.hidden=false;render();exit.focus({preventScroll:true});}
    function render(){
      if(panel.hidden)return;
      const {player:p,world:w}=h.state();const npc=w?.npcs?.find(n=>n.id===npcId);
      if(!p||p.hp<=0||!npc){close();return;}
      const closeEnough=(p.floor||0)===(npc.floor||0)&&Math.hypot(p.x-npc.x,p.y-npc.y)<=(npc.radius||125);
      const quests=(p.quests||[]).filter(q=>q.npc_id===npc.id),routes=(w.sea_routes||[]).filter(r=>(npc.routes||[]).includes(r.id));
      const next=JSON.stringify([npcId,topic,closeEnough,quests,p.gold,p.level,p.combat_remaining>0,p.discoveries]);if(next===signature)return;signature=next;
      const scroll=body.scrollTop;title.textContent=npc.name;body.replaceChildren();
      if(npc.role)body.append(node('p',npc.role,'adventure-role'));
      if(!closeEnough)body.append(node('p','Podejdź bliżej, aby porozmawiać i skorzystać z usług.','adventure-warning'));
      const dialogue=npc.dialogue||{},selected=(dialogue.topics||[]).find(t=>t.id===topic);
      body.append(node('p',selected?.text||dialogue.greeting||npc.description||'Witaj na szlaku. Sprawdź miejscowe zlecenia.','adventure-speech'));
      if(dialogue.topics?.length){const topics=node('nav',undefined,'adventure-topics');topics.setAttribute('aria-label','Tematy rozmowy');for(const t of dialogue.topics){const b=button(t.title,()=>{topic=t.id;signature='';render();},!closeEnough);b.setAttribute('aria-pressed',String(t.id===topic));topics.append(b);}body.append(topics);}
      if(npc.service==='merchant')body.append(button('Pokaż towary',()=>{close();h.trade?.(npc);},!closeEnough||p.combat_remaining>0));
      if(['bank','master','boat','binding_stone'].includes(npc.service))body.append(button('Usługi',()=>{close();h.services?.(npc);},!closeEnough));
      for(const q of quests){
        const row=node('article',undefined,'adventure-quest');row.dataset.questId=q.id;row.append(node('h3',q.title));
        const speech=q.status==='ready'?dialogue.quest_complete:q.status==='active'?dialogue.quest_progress:dialogue.quest_offer;
        if(speech)row.append(node('p',typeof speech==='string'?speech:speech[q.id]||''));
        row.append(node('p',q.description));
        for(const o of q.objectives||[])row.append(node('small',`${o.count>=o.required?'✓ ':''}${o.label} · ${o.count}/${o.required}`));
        if(q.status==='available'||q.status==='ready'){const ready=q.status==='ready';row.append(button(ready?'Odbierz nagrodę':'Przyjmij zlecenie',()=>h.send({type:ready?'quest_claim':'quest_accept',quest_id:q.id}),!closeEnough));}
        if(['available','active','ready'].includes(q.status))row.append(button('Śledź zadanie',()=>{h.track?.(q.id);close();}));
        if(q.status==='locked'){const requirements=(Array.isArray(q.requires)?q.requires:[q.requires]).filter(Boolean).map(id=>(p.quests||[]).find(x=>x.id===id)?.title||id);row.append(node('small',q.min_level>p.level?`Wymagany poziom ${q.min_level}`:requirements.length?'Najpierw: '+requirements.join(', '):'Kolejny etap wyprawy.'));}
        if(q.status==='claimed')row.append(node('small','✓ Zlecenie ukończone'));
        const reward=q.reward||{};row.append(node('small',[reward.xp?reward.xp+' PD':'',reward.gold?reward.gold+' złota':'',reward.item?w.items?.[reward.item]?.name||'Nagroda rzeczowa':''].filter(Boolean).join(' · '),'adventure-reward'));
        body.append(row);
      }
      body.scrollTop=scroll;
    }
    return {open,close,render,get visible(){return !panel.hidden;}};
  }
  root.BractwoAdventureUI={create,boatReason,routeText};
  if(typeof module!=='undefined')module.exports=root.BractwoAdventureUI;
})(globalThis);
