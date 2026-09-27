/* Movable HUD and dialogs. Pointer/touch/keyboard drag; per-account local layout.
 * Default placement uses rails. User-moved panels can intentionally overlap.
 */
(function(root){'use strict';
 function clampPosition(x,y,width,height,vw,vh){return{x:Math.max(6,Math.min(vw-Math.min(width,vw-12)-6,x)),y:Math.max(6,Math.min(vh-Math.min(height,vh-12)-6,y))};}
 function create(h={}){
  const ui=document.getElementById('gameUI'),records=new Map();let account='',profile='',data={positions:{},hidden:{},locked:true},z=110,queued=false,drag=null,portraitLevels='';
  const button=(text)=>{const b=document.createElement('button');b.type='button';b.textContent=text;return b;};
  const left=document.createElement('aside');left.id='hudLeftRail';ui.append(left);
  const settings=document.createElement('div');settings.id='hudVisibility';settings.className='hud-visibility';
  const toggle=button('☷ Panele'),reset=button('↺'),lock=button('🔒');toggle.setAttribute('aria-expanded','false');reset.title='Przywróć domyślny układ i widoczność';reset.setAttribute('aria-label',reset.title);lock.id='hudLayoutLock';
  const menu=document.createElement('div');menu.id='hudVisibilityMenu';menu.hidden=true;toggle.setAttribute('aria-controls',menu.id);settings.append(toggle,reset,lock,menu);left.append(settings);
  for(const sel of ['.world-status','.pvp-bar','#questTracker']){const e=ui.querySelector(sel);if(e)left.append(e);}
  const right=document.createElement('aside');right.id='hudRightRail';ui.append(right);
  for(const sel of ['#minimapCard','#battleList']){const e=ui.querySelector(sel);if(e)right.append(e);}
  const groups=[['character','.player-card','Postać'],['region','.world-status','Region'],['pvp','.pvp-bar','Cel i PvP'],['quest','#questTracker','Zadanie'],['fighter','#fighterChoice','Wybór stylu walki'],['caster','#casterChoice','Ścieżka druida'],['minimap','#minimapCard','Minimapa'],['nearby','#battleList','Potwory w pobliżu'],['statuses','#effectsPanel','Statusy'],['levels','#levelUpCascade','Awanse'],['chat','.chat-wrap','Czat'],['potions','.quickbar','Mikstura Q'],['spells','#spellbar','Paski czarów'],['actions','.combat-controls','Atak / rozmowa'],['messages','.notice-feed','Komunikaty']];
  const labels=new Map();
  for(const [id,sel,title] of groups){const label=document.createElement('label'),input=document.createElement('input');input.type='checkbox';input.checked=true;input.dataset.visibility=id;
   input.onchange=()=>{data.hidden[id]=!input.checked;applyHidden();save();schedule();};label.append(input,document.createTextNode(title));menu.append(label);labels.set(id,{sel,input});}
  const tip=document.createElement('small');tip.id='hudLayoutHint';menu.append(tip);lock.setAttribute('aria-describedby',tip.id);
  toggle.onclick=()=>{menu.hidden=!menu.hidden;toggle.setAttribute('aria-expanded',String(!menu.hidden));schedule();};
  reset.onclick=()=>{cancelDrag();data={positions:{},hidden:{},locked:locked()};for(const rec of records.values())clearFloat(rec.el);applyHidden();applyLock();save();schedule();h.levelLayout?.();};
  lock.onclick=()=>{cancelDrag();h.stop?.();data.locked=!locked();applyLock();save();schedule();};
  function mobile(){return !!root.BractwoMobile?.active?.();}
  function locked(){return data.locked!==false;}
  function applyLock(){const value=locked();ui.classList.toggle('hud-layout-locked',value);ui.classList.toggle('hud-layout-unlocked',!value);lock.textContent=value?'🔒':'🔓';lock.title=value?'Odblokuj przesuwanie paneli':'Zablokuj przesuwanie paneli';lock.setAttribute('aria-label',lock.title);lock.setAttribute('aria-pressed',String(value));tip.textContent=value?'Przesuwanie paneli jest zablokowane. Odblokuj kłódką, aby zmienić układ.':'Przeciągnij nagłówek albo uchwyt ⋮⋮. Po zmianie układu zamknij kłódkę. Pozycje zapisują się na tym urządzeniu.';for(const grip of ui.querySelectorAll('.window-grip')){grip.disabled=value;grip.setAttribute('aria-disabled',String(value));}}
  function key(){return (mobile()?'bractwo-windows-mobile-v1:':'bractwo-windows-v1:')+account+':'+(innerWidth<innerHeight?'portrait':'landscape');}
  function save(){try{localStorage.setItem(key(),JSON.stringify(data));}catch{/* private browsing / quota: layout remains usable */}}
  function sync(id){const next=String(id||'guest'),name=(mobile()?'mobile:':'desktop:')+next+':'+(innerWidth<innerHeight?'portrait':'landscape');if(name===profile)return;cancelDrag();account=next;profile=name;
   try{const raw=JSON.parse(localStorage.getItem(key())||'{}');data={positions:raw.positions||{},hidden:raw.hidden||{},locked:raw.locked!==false};}catch{data={positions:{},hidden:{},locked:true};}
   for(const rec of records.values())clearFloat(rec.el);applyHidden();applyLock();schedule();
  }
  function applyHidden(){for(const[id,{sel,input}]of labels){const el=ui.querySelector(sel);el?.toggleAttribute('data-hud-hidden',!!data.hidden[id]);input.checked=!data.hidden[id];}}
  function clearFloat(el){el.classList.remove('hud-floating');for(const k of ['--float-x','--float-y','--float-width','--float-z'])el.style.removeProperty(k);}
  function cancelDrag(){const current=drag;if(!current)return;drag=null;if(current.handle.hasPointerCapture(current.id))current.handle.releasePointerCapture(current.id);clearFloat(current.rec.el);restore(current.rec);h.stop?.();}
  function floatAt(rec,x,y,width,remember=false){
   const el=rec.el,w=Math.min(width||el.getBoundingClientRect().width,innerWidth-12);el.style.setProperty('--float-width',Math.round(w)+'px');el.classList.add('hud-floating');
   const box=el.getBoundingClientRect(),pos=clampPosition(x,y,w,box.height,innerWidth,innerHeight);
   el.style.setProperty('--float-x',Math.round(pos.x)+'px');el.style.setProperty('--float-y',Math.round(pos.y)+'px');
   if(remember){data.positions[rec.id]={x:pos.x/Math.max(1,innerWidth-w-12),y:pos.y/Math.max(1,innerHeight-box.height-12),width:w};save();}
  }
  function restore(rec){if(mobile()&&rec.id==='chat'&&rec.el.classList.contains('writing')){clearFloat(rec.el);return;}const p=data.positions[rec.id];if(!p||rec.el.hidden||!rec.el.isConnected)return;
   // Clamp saved widths to the current viewport; CSS max-height keeps Close reachable.
   const w=Math.min(Number(p.width)||rec.el.getBoundingClientRect().width,innerWidth-12);
   // Restore the saved width before measuring height: wrapping may differ from the mobile/default layout.
   rec.el.style.setProperty('--float-width',Math.round(w)+'px');rec.el.classList.add('hud-floating');
   const box=rec.el.getBoundingClientRect();
   floatAt(rec,(Number(p.x)||0)*Math.max(1,innerWidth-w-12),(Number(p.y)||0)*Math.max(1,innerHeight-box.height-12),w);
  }
  function register(el,id,handleSelector){if(!el)return;const old=records.get(el);if(old?.handle?.isConnected)return;const rec={el,id};records.set(el,rec);el.dataset.movable=id;
   let handle=handleSelector&&el.querySelector(handleSelector);
   if(!handle){handle=button('⋮⋮');handle.className='window-grip';handle.setAttribute('aria-label','Przesuń: '+(el.getAttribute('aria-label')||id));handle.title='Przeciągnij, aby przesunąć panel. Strzałki po zaznaczeniu też przesuwają.';el.append(handle);}
   rec.handle=handle;handle.classList.add('window-handle');handle.style.touchAction='none';
   if(handle.classList.contains('window-grip')){handle.disabled=locked();handle.setAttribute('aria-disabled',String(locked()));}
   handle.addEventListener('pointerdown',e=>{
    if(locked()){cancelDrag();return;}
    if(e.button!==0||drag)return;if(e.target.closest('button,input,select,textarea,a')&&!e.target.closest('.window-grip,.level-up-title'))return;
    const rect=el.getBoundingClientRect();drag={rec,handle,id:e.pointerId,sx:e.clientX,sy:e.clientY,x:rect.x,y:rect.y,width:rect.width,moved:false};handle.setPointerCapture(e.pointerId);e.stopPropagation();
   });
   handle.addEventListener('pointermove',e=>{if(locked()){cancelDrag();return;}if(!drag||drag.handle!==handle||e.pointerId!==drag.id)return;
    const dx=e.clientX-drag.sx,dy=e.clientY-drag.sy;if(!drag.moved&&Math.hypot(dx,dy)<5)return;
    if(!drag.moved){drag.moved=true;h.stop?.();el.style.setProperty('--float-z',String(++z));}
    e.preventDefault();floatAt(rec,drag.x+dx,drag.y+dy,drag.width);schedule();
   });
   const finish=e=>{if(locked()){cancelDrag();return;}if(!drag||drag.handle!==handle||e.pointerId!==drag.id)return;const moved=drag.moved;drag=null;if(moved){const r=el.getBoundingClientRect();floatAt(rec,r.x,r.y,r.width,true);handle.dataset.justDragged='1';setTimeout(()=>delete handle.dataset.justDragged,80);schedule();}if(handle.hasPointerCapture(e.pointerId))handle.releasePointerCapture(e.pointerId);};
   handle.addEventListener('pointerup',finish);handle.addEventListener('pointercancel',finish);
   handle.addEventListener('click',e=>{if(handle.dataset.justDragged||handle.classList.contains('window-grip')){e.preventDefault();e.stopImmediatePropagation();}},true);
   handle.addEventListener('keydown',e=>{if(!handle.classList.contains('window-grip')&&!e.target.closest('.window-grip'))return;if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;e.preventDefault();e.stopPropagation();if(locked()){cancelDrag();return;}h.stop?.();const r=el.getBoundingClientRect(),step=e.shiftKey?30:10;floatAt(rec,r.x+(e.key==='ArrowRight'?step:e.key==='ArrowLeft'?-step:0),r.y+(e.key==='ArrowDown'?step:e.key==='ArrowUp'?-step:0),r.width,true);schedule();});
   el.addEventListener('pointerdown',()=>{if(el.classList.contains('hud-floating'))el.style.setProperty('--float-z',String(++z));},true);
   restore(rec);
  }
  function scan(){
   const specs=[['.player-card','player'],['.gold-chip','gold'],['.top-actions','menu'],['#hudVisibility','visibility'],['.world-status','region'],['.pvp-bar','pvp'],['#questTracker','quest'],['#minimapCard','minimap'],['#battleList','nearby'],['.notice-feed','messages'],['#interactPrompt','interaction'],['#partyInvite','invitation','#inviteText'],['#actionDock','dock'],['.chat-wrap','chat'],['.quickbar','potions'],['#spellbar','spells'],['.combat-controls','combat'],['.movement-controls','joystick'],['#controlTip','controltip','span'],['#effectsPanel','statuses'],['#effectDetail','effect-detail','#effectDetailName'],['#levelUpCascade','levels'],['#fighterChoice','fighter-choice','header'],['#casterChoice','caster-choice','header'],['#characterPanel','character-window','.character-header'],['#sidePanel','journal-window','.panel-head'],['#helpPanel','help-window','h2'],['#lootPreview','loot-window','header'],['#merchantPanel','merchant-window','.merchant-header'],['#deathPanel','death-window','h2'],['#disconnectPanel','connection-window','h2'],['#legacyClassPanel','class-window','h2']];
   for(const [sel,id,handle]of specs)register(ui.querySelector(sel)||document.querySelector(sel),id,handle);
   for(const card of ui.querySelectorAll('.level-up-card'))register(card,'level:'+card.dataset.id,'.level-up-header');
   for(const[el,rec]of records){if(!el.isConnected){records.delete(el);continue;}if(!drag)restore(rec);}
  }
  function defaults(){
   const levels=ui.querySelector('#levelUpCascade'),effects=ui.querySelector('#effectsPanel'),dock=ui.querySelector('#actionDock');
   if(mobile()){
    for(const rail of [left,right])for(const property of ['top','max-height','overflow','overflow-y','pointer-events'])rail.style.removeProperty(property);
    if(levels?.parentNode===left)ui.append(levels);
    for(const property of ['--status-top','--status-left'])effects?.style.removeProperty(property);
    for(const property of ['--levels-x','--levels-y','--levels-height'])levels?.style.removeProperty(property);
    portraitLevels='';h.levelLayout?.();return;
   }
   const top=ui.querySelector('.topbar').getBoundingClientRect(),short=innerHeight<550,portrait=innerWidth<701&&innerHeight>innerWidth;
   const hasEffects=effects&&!effects.hidden&&!effects.hasAttribute('data-hud-hidden');
   const topY=Math.max(80,Math.round(top.bottom+10))+(portrait&&hasEffects?32:0);
   left.style.top=topY+'px';right.style.top=topY+'px';
   const floor=dock&&!dock.classList.contains('hud-floating')?dock.getBoundingClientRect().top-12:innerHeight-160;
   if(portrait){
    if(levels&&levels.parentNode!==left&&!levels.classList.contains('hud-floating'))left.append(levels);
    left.style.maxHeight=Math.max(92,floor-topY)+'px';left.style.overflowY='auto';left.style.pointerEvents='auto';
    right.style.maxHeight=Math.max(92,floor-topY)+'px';right.style.overflowY='auto';right.style.pointerEvents='auto';
   }else{
    if(levels?.parentNode===left)ui.append(levels);
    left.style.maxHeight='';left.style.overflowY='';left.style.pointerEvents='';right.style.maxHeight='';right.style.overflowY='';right.style.pointerEvents='';portraitLevels='';
   }
   if(effects&&!effects.classList.contains('hud-floating')){effects.style.setProperty('--status-top',topY+'px');effects.style.setProperty('--status-left',(portrait?12:Math.ceil(left.getBoundingClientRect().right+12))+'px');}
   const effectBottom=hasEffects?effects.getBoundingClientRect().bottom:topY;
   if(levels&&!levels.classList.contains('hud-floating')){
    const rail=left.getBoundingClientRect(),y=portrait?0:Math.max(topY,effectBottom+8);
    levels.style.setProperty('--levels-x',(portrait?0:Math.ceil(rail.right+12))+'px');levels.style.setProperty('--levels-y',Math.round(y)+'px');
    levels.style.setProperty('--levels-height',Math.max(100,Math.min(portrait?230:short?210:470,portrait?floor-topY:floor-y))+'px');
   }
   h.levelLayout?.();
   const ids=portrait&&levels&&!levels.hidden&&!levels.hasAttribute('data-hud-hidden')?[...levels.querySelectorAll('.level-up-card')].map(c=>c.dataset.id).join(','):'';
   if(ids&&ids!==portraitLevels&&levels.parentNode===left){portraitLevels=ids;requestAnimationFrame(()=>{left.scrollTop=left.scrollHeight;});}
  }

  function schedule(){if(queued)return;queued=true;requestAnimationFrame(()=>{queued=false;scan();defaults();});}
  // Only structural changes and visibility affect placement, not every HP tick.
  const observer=new MutationObserver(mutations=>{if(mutations.some(m=>m.type==='childList'&&[...m.addedNodes,...m.removedNodes].some(n=>n.nodeType===1)||m.type==='attributes'))schedule();});
  observer.observe(ui,{subtree:true,childList:true,attributes:true,attributeFilter:['hidden','data-hud-hidden']});
  const ro=new ResizeObserver(schedule);ro.observe(left);ro.observe(right);ro.observe(ui.querySelector('#actionDock'));ro.observe(ui.querySelector('#effectsPanel'));
  root.addEventListener('resize',()=>{cancelDrag();sync(account);schedule();});sync('guest');schedule();
  return{sync,refresh:schedule,reset:()=>reset.click(),get positions(){return data.positions;},get locked(){return locked();}};
 }
 const api={create,clampPosition};root.BractwoWindows=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
