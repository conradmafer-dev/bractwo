/* UI_14: grouped shortcuts; the server still validates every actual spell. */
(function(root){
  'use strict';
  const names={archer:'Łucznik',chalice:'Kielich',dragon:'Smok'};
  const Runtime=()=>root.BractwoRuntime;
  function activeStar(player){
    // An explicit empty owner state must win over older visuals/sheet data.
    for(const state of [player?.druid_forms,player?.circle_visual,player?.character_sheet?.caster?.circle]){
      if(state&&Object.prototype.hasOwnProperty.call(state,'starry_form'))
        return Object.prototype.hasOwnProperty.call(names,state.starry_form)?state.starry_form:'';
    }
    return '';
  }
  function canDismiss(player){
    if(!player?.alive||player.hp<=0)return false;
    if(player.druid_forms)return player.druid_forms.can_dismiss_star===true;
    return !player.status_effects?.some(s=>['incapacitated','paralyzed','unconscious','stunned','sleep_pending','stinking_poison','polymorph'].includes(s.id));
  }
  function pool(player){
    if(player?.druid_forms)return {remaining:player.druid_forms.shape_remaining,maximum:player.druid_forms.shape_maximum};
    const resource=player?.character_sheet?.caster?.circle?.resources?.find(r=>r.id==='shape');
    if(resource)return {remaining:resource.remaining,maximum:resource.maximum};
    const entry=Object.entries(player?.spell_profiles||{}).find(([id,s])=>id.startsWith('wild_shape_')&&s.uses_remaining!==undefined);
    return {remaining:entry?.[1].uses_remaining??0,maximum:entry?.[1].uses_maximum??0};
  }
  function groupState(id,player,world){
    const group=world?.hotbar_groups?.[id];if(!group||!player)return null;
    const members=(group.members||[]).map(key=>Runtime().spellProfile(world.spells?.[key],player))
      .filter(s=>s&&s.available!==false&&(s.available===true||Runtime().spellGate(s,player)<=player.level));
    const star=activeStar(player);
    let primary=null,label=group.name,active=false;
    if(id==='group_starry_form'&&star){
      active=true;label=names[star]||group.name;
      if(star==='archer'){primary=members.find(s=>s.id==='circle_star_arrow')||null;label='Gwiezdna strzała';}
    }
    if(id==='group_wild_shape'&&player.form){
      active=true;primary=members.find(s=>s.kind==='shape'&&s.form===player.form)||members.find(s=>s.kind==='shape')||null;
      label='Powrót do druida';
    }
    const readyIn=star==='archer'?Math.max(0,Number(player.druid_forms?.arrow_ready_in??player.bonus_remaining)||0):0;
    const command=id==='group_starry_form'&&star&&star!=='archer'?'dismiss_star_form':null;
    const shortLabel=id==='group_starry_form'?(star==='archer'?'Strzała':star?names[star]:'Gwiazdy'):label;
    const icon=id==='group_starry_form'&&star==='archer'?'assets/spells/star_arrow.svg':group.icon;
    const disabled=!player.alive||!!(primary&&!Runtime().spellUsable(primary,player))||readyIn>0||
      !!(command&&!canDismiss(player))||!!(star==='archer'&&player.druid_forms&&player.druid_forms.can_shoot!==true);
    return {id,group,members,star,primary,label,shortLabel,icon,command,disabled,readyIn,active,pool:pool(player)};
  }
  function create(host){
    const panel=document.createElement('section');panel.className='hotbar-group-menu';panel.id='hotbarGroupMenu';panel.hidden=true;
    panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Wybór postaci druida');
    const head=document.createElement('header'),title=document.createElement('strong'),closeButton=document.createElement('button');
    closeButton.type='button';closeButton.textContent='×';closeButton.setAttribute('aria-label','Zamknij wybór postaci');
    head.append(title,closeButton);
    const summary=document.createElement('p');summary.className='hotbar-group-resource';
    const list=document.createElement('div');list.className='hotbar-group-options';
    const current=document.createElement('div');current.className='hotbar-group-current';
    panel.append(head,summary,current,list);host.parent.append(panel);
    let groupId='',anchor=null,signature='';
    function close(){panel.hidden=true;groupId='';signature='';anchor?.setAttribute('aria-expanded','false');}
    closeButton.addEventListener('click',close);
    function position(){
      if(panel.hidden||!anchor)return;
      const rect=anchor.getBoundingClientRect(),width=Math.min(390,innerWidth-20);
      panel.style.width=width+'px';panel.style.maxHeight=Math.max(100,innerHeight-24)+'px';
      panel.style.left=Math.max(10,Math.min(innerWidth-width-10,rect.left))+'px';
      panel.style.top=Math.max(12,Math.min(innerHeight-panel.offsetHeight-12,rect.top-panel.offsetHeight-8))+'px';
    }
    function addRow(name,description,cost,spell,disabled=false,action=null,parent=list){
      const button=document.createElement('button');button.type='button';button.className='hotbar-group-option';button.disabled=disabled;
      if(spell)button.dataset.spell=spell;
      const strong=document.createElement('strong');strong.textContent=name;
      const small=document.createElement('small');small.textContent=description;
      const em=document.createElement('em');em.textContent=cost;
      button.append(strong,small,em);
      button.addEventListener('click',()=>{if(button.disabled)return;close();if(action)action();else host.cast(spell);});
      parent.append(button);return button;
    }
    function refresh(){
      if(panel.hidden)return;
      const {player,world}=host.state(),state=groupState(groupId,player,world);
      if(!player?.alive||!state?.members.length){close();return;}
      const next=JSON.stringify([groupId,player.level,player.form,state.star,state.pool,Math.floor(player.mana),
        Math.ceil(player.bonus_remaining||0),state.disabled,canDismiss(player),player.status_effects?.map(e=>e.id),state.members.map(s=>[s.id,s.already_active,s.resource_cost,s.uses_remaining,s.available,Math.ceil(player.spell_cooldowns?.[s.id]||0)])]);
      if(next===signature){position();return;}signature=next;
      const focused=panel.contains(document.activeElement)?document.activeElement.dataset.spell:null;
      title.textContent=state.group.name;
      summary.textContent=`Wspólna pula Dzikiego kształtu: ${state.pool.remaining}/${state.pool.maximum}.`;
      list.replaceChildren();current.replaceChildren();
      if(groupId==='group_starry_form'&&state.star){
        summary.textContent=`${names[state.star]} aktywny · Dziki kształt: ${state.pool.remaining}/${state.pool.maximum}. `+
          (state.star==='archer'?'Strzelaj przyciskiem Strzała na pasku.':'Kliknięcie aktywnej postaci na pasku kończy przemianę.');
        const leave=addRow('Powrót do druida','','Bez kosztu. Nie zwraca wydanego użycia.','',!canDismiss(player),
          ()=>host.send({type:'circle_command',action:'dismiss_star_form'}),current);
        leave.dataset.action='dismiss_star_form';
      }
      if(groupId==='group_wild_shape'&&player.form&&state.primary){
        addRow('Powrót do druida','Zakończ przemianę w zwierzę.','Nie zużywa użycia przemiany.',state.primary.id,
          !Runtime().spellUsable(state.primary,player));
      }
      const members=state.members.slice().sort((a,b)=>(a.id==='circle_star_arrow'?-1:b.id==='circle_star_arrow'?1:0));
      for(const s of members){
        const isShape=s.kind==='shape',isStar=/^circle_star_(archer|chalice|dragon)$/.test(s.id);
        const current=isShape?player.form===s.form:isStar?state.star===s.id.split('_').pop():!!s.already_active;
        const label=isShape?s.name.replace(/^Dziki kształt\s*[·–-]\s*/,''):isStar?names[s.id.split('_').pop()]:s.name;
        let cost=current?'Aktywna postać':Runtime().spellCostText(s,player);
        if(isShape&&player.form&&!current)cost='Najpierw wróć do postaci druida.';
        else if(!current&&s.resource_cost>0&&s.uses_remaining<s.resource_cost)cost='Brak użyć Dzikiego kształtu — odpocznij.';
        addRow(label,s.power_summary||s.description||'',cost,s.id,
          current||!!(isShape&&player.form)||!Runtime().spellUsable(s,player)||(s.id==='circle_star_arrow'&&state.disabled));
      }
      if(focused)list.querySelector(`[data-spell="${focused}"]`)?.focus({preventScroll:true});
      position();
    }
    function open(id,button){
      if(!panel.hidden&&groupId===id){close();return;}
      close();groupId=id;anchor=button;signature='';panel.hidden=false;anchor?.setAttribute('aria-expanded','true');refresh();
    }
    document.addEventListener('pointerdown',event=>{
      if(!panel.hidden&&!panel.contains(event.target)&&!event.target.closest?.('.hotbar-cell'))close();
    },true);
    addEventListener('resize',position);
    return {open,close,refresh,get visible(){return !panel.hidden;},get groupId(){return groupId;}};
  }
  const api={activeStar,canDismiss,pool,groupState,create};root.BractwoHotbarUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
