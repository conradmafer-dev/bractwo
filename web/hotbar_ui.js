/* UI_13: grouped shortcuts; the server still validates every actual spell. */
(function(root){
  'use strict';
  const names={archer:'Łucznik',chalice:'Kielich',dragon:'Smok'};
  const Runtime=()=>root.BractwoRuntime;
  function pool(player){
    const resource=player?.character_sheet?.caster?.circle?.resources?.find(r=>r.id==='shape');
    if(resource)return {remaining:resource.remaining,maximum:resource.maximum};
    const entry=Object.entries(player?.spell_profiles||{}).find(([id,s])=>id.startsWith('wild_shape_')&&s.uses_remaining!==undefined);
    return {remaining:entry?.[1].uses_remaining??0,maximum:entry?.[1].uses_maximum??0};
  }
  function groupState(id,player,world){
    const group=world?.hotbar_groups?.[id];if(!group||!player)return null;
    const members=(group.members||[]).map(key=>Runtime().spellProfile(world.spells?.[key],player))
      .filter(s=>s&&s.available!==false&&(s.available===true||Runtime().spellGate(s,player)<=player.level));
    const star=player.circle_visual?.starry_form||'';
    let primary=null,label=group.name,active=false;
    if(id==='group_starry_form'&&star){
      active=true;label=names[star]||group.name;
      if(star==='archer'){primary=members.find(s=>s.id==='circle_star_arrow')||null;label='Gwiezdna strzała';}
    }
    if(id==='group_wild_shape'&&player.form){
      active=true;primary=members.find(s=>s.kind==='shape'&&s.form===player.form)||members.find(s=>s.kind==='shape')||null;
      label='Powrót do druida';
    }
    return {id,group,members,star,primary,label,active,pool:pool(player)};
  }
  function create(host){
    const panel=document.createElement('section');panel.className='hotbar-group-menu';panel.id='hotbarGroupMenu';panel.hidden=true;
    panel.setAttribute('role','dialog');panel.setAttribute('aria-label','Wybór postaci druida');
    const head=document.createElement('header'),title=document.createElement('strong'),closeButton=document.createElement('button');
    closeButton.type='button';closeButton.textContent='×';closeButton.setAttribute('aria-label','Zamknij wybór postaci');
    head.append(title,closeButton);
    const summary=document.createElement('p');summary.className='hotbar-group-resource';
    const list=document.createElement('div');list.className='hotbar-group-options';
    panel.append(head,summary,list);host.parent.append(panel);
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
    function addRow(name,description,cost,spell,disabled=false,action=null){
      const button=document.createElement('button');button.type='button';button.className='hotbar-group-option';button.disabled=disabled;
      if(spell)button.dataset.spell=spell;
      const strong=document.createElement('strong');strong.textContent=name;
      const small=document.createElement('small');small.textContent=description;
      const em=document.createElement('em');em.textContent=cost;
      button.append(strong,small,em);
      button.addEventListener('click',()=>{if(button.disabled)return;close();if(action)action();else host.cast(spell);});
      list.append(button);
    }
    function refresh(){
      if(panel.hidden)return;
      const {player,world}=host.state(),state=groupState(groupId,player,world);
      if(!player?.alive||!state?.members.length){close();return;}
      const next=JSON.stringify([groupId,player.level,player.form,state.star,state.pool,Math.floor(player.mana),
        Math.ceil(player.bonus_remaining||0),player.status_effects?.map(e=>e.id),state.members.map(s=>[s.id,s.already_active,s.resource_cost,s.uses_remaining,s.available,Math.ceil(player.spell_cooldowns?.[s.id]||0)])]);
      if(next===signature){position();return;}signature=next;
      const focused=panel.contains(document.activeElement)?document.activeElement.dataset.spell:null;
      title.textContent=state.group.name;
      summary.textContent=`Wspólna pula Dzikiego kształtu: ${state.pool.remaining}/${state.pool.maximum}.`;
      list.replaceChildren();
      if(groupId==='group_wild_shape'&&player.form&&state.primary){
        addRow('Powrót do druida','Zakończ przemianę w zwierzę.','Nie zużywa użycia przemiany.',state.primary.id,
          !Runtime().spellUsable(state.primary,player));
      }
      const members=state.members.slice().sort((a,b)=>(a.id==='circle_star_arrow'?-1:b.id==='circle_star_arrow'?1:0));
      for(const s of members){
        const isShape=s.kind==='shape',isStar=/^circle_star_(archer|chalice|dragon)$/.test(s.id);
        const current=isShape?player.form===s.form:!!s.already_active;
        const label=isShape?s.name.replace(/^Dziki kształt\s*[·–-]\s*/,''):isStar?names[s.id.split('_').pop()]:s.name;
        let cost=current?'Aktywna postać':Runtime().spellCostText(s,player);
        if(isShape&&player.form&&!current)cost='Najpierw wróć do postaci druida.';
        else if(!current&&s.resource_cost>0&&s.uses_remaining<s.resource_cost)cost='Brak użyć Dzikiego kształtu — odpocznij.';
        addRow(label,s.power_summary||s.description||'',cost,s.id,
          current||!!(isShape&&player.form)||!Runtime().spellUsable(s,player));
      }
      if(groupId==='group_starry_form'&&state.star){
        addRow('Zakończ gwiezdną postać','Powróć do zwykłego wyglądu.','Nie odnawia wydanego użycia.','',false,
          ()=>host.send({type:'circle_command',action:'dismiss_star_form'}));
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
  const api={pool,groupState,create};root.BractwoHotbarUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
