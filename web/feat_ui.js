/* Explicit, paginated feat choice. Never spend a slot until Confirm is pressed. */
(function(root){'use strict';
 const names={strength:'Siła',dexterity:'Zręczność',constitution:'Kondycja',intelligence:'Inteligencja',wisdom:'Mądrość',charisma:'Charyzma'};
 const PAGE_SIZE=6;
 let panel,backdrop,hook,owner,mode='origin',candidate='',page=0,selection='',signature='',previousFocus,pending=false,pendingAt=0,receipt='';
 const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
 const button=(label,fn,cls='')=>{const b=node('button',cls,label);b.type='button';b.onclick=fn;return b;};
 function options(p,kind){const tr=p?.character_sheet?.training;return kind==='origin'?(tr?.origin?.points>0&&!tr.origin.chosen?tr.origin.options||[]:[]):tr?.points>0?(tr.options||[]).filter(f=>f.id!=='ability_score_improvement'):[];}
 function token(p,kind){const t=p?.character_sheet?.training;return kind==='origin'?String(t?.origin?.chosen?.id||''):String(t?.spent??'');}
 function reason(p,kind,id,ability){const f=options(p,kind).find(f=>f.id===id);if(!f)return 'Wybierz dostępny atut.';return kind==='origin'?root.BractwoSkillsUI.originReason(p,id):root.BractwoCasterUI.trainingReason(p,f,ability);}
 function close(){if(!panel)return;panel.hidden=true;backdrop.hidden=true;pending=false;signature='';if(previousFocus?.isConnected)previousFocus.focus({preventScroll:true});}
 function ensure(){if(panel)return;
  panel=node('section','feat-picker');panel.id='featPicker';panel.hidden=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');panel.setAttribute('aria-labelledby','featPickerTitle');
  panel.addEventListener('keydown',e=>{e.stopPropagation();if(e.key==='Escape'){e.preventDefault();close();}if(e.key==='Tab'){const list=[...panel.querySelectorAll('button:not(:disabled),select:not(:disabled)')].filter(e=>e.getClientRects().length);const first=list[0],last=list.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last?.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first?.focus();}}});
  for(const event of ['keyup','pointerdown','touchstart'])panel.addEventListener(event,e=>e.stopPropagation());
  backdrop=node('div','feat-picker-backdrop');backdrop.hidden=true;backdrop.setAttribute('aria-hidden','true');
  for(const event of ['pointerdown','touchstart','wheel'])backdrop.addEventListener(event,e=>{e.preventDefault();e.stopPropagation();panel.querySelector('button')?.focus({preventScroll:true});},{passive:false});
  document.getElementById('gameUI').append(backdrop,panel);
 }
 function open(kind,p,h){ensure();previousFocus=document.activeElement;hook=h;owner=String(p.id);mode=kind==='origin'?'origin':'general';candidate='';page=0;selection='';signature='';pending=false;hook.stop?.();backdrop.hidden=false;panel.hidden=false;sync(p);panel.querySelector('button')?.focus({preventScroll:true});}
 function sync(p){if(!panel||panel.hidden)return;if(!p||String(p.id)!==owner){close();return;}
  const available=options(p,mode);
  if(pending&&token(p,mode)!==receipt){close();return;}
  // A rejected or lost request must not leave the confirmation permanently locked.
  if(pending&&Date.now()-pendingAt>2500)pending=false;
  const key=JSON.stringify([available,p.attributes,p.alive,p.form,p.class_chosen,p.polymorph,p.combat_remaining>0,pending,mode,page,candidate,selection,token(p,mode)]);
  if(key===signature)return;signature=key;
  const focused=panel.contains(document.activeElement)?document.activeElement.dataset.focusKey:null;
  const scroll=panel.scrollTop;panel.replaceChildren();
  const header=node('header','feat-picker-header'),title=node('h2','',mode==='origin'?'Wybierz pierwszy atut':'Wybierz atut');title.id='featPickerTitle';
  const x=button('×',close);x.setAttribute('aria-label','Zamknij wybór atutu');x.dataset.focusKey='close';header.append(title,x);panel.append(header);
  panel.append(node('p','feat-picker-note',mode==='origin'?'Od poziomu 1 · jeden osobny, bezpłatny wybór.':'Dostępne wybory: '+(p.character_sheet?.training?.points||0)+'. Atut zużywa tę samą pulę co rozwój cech.'));
  if(!available.length){panel.append(node('p','feat-picker-description','Wszystkie wybory z tej puli zostały wykorzystane.'),button('Zamknij',close));return;}
  const pages=Math.ceil(available.length/PAGE_SIZE);page=Math.min(page,pages-1);
  const list=node('div','feat-picker-options');list.setAttribute('aria-label','Dostępne atuty');
  for(const f of available.slice(page*PAGE_SIZE,(page+1)*PAGE_SIZE)){
   const b=button('',()=>{candidate=f.id;selection=f.abilities?.[0]||'';signature='';sync(hook.state?.().player||p);},'feat-picker-option'+(f.id===candidate?' selected':''));b.dataset.featOption=f.id;b.dataset.focusKey=f.id;b.setAttribute('aria-pressed',String(f.id===candidate));
   const img=node('img');img.src=f.icon;img.alt='';b.append(img,node('strong','',f.name));list.append(b);
  }panel.append(list);
  if(pages>1){const nav=node('div','feat-picker-pages'),prev=button('‹',()=>{page--;signature='';sync(hook.state?.().player||p);}),next=button('›',()=>{page++;signature='';sync(hook.state?.().player||p);});prev.disabled=page===0;next.disabled=page===pages-1;prev.setAttribute('aria-label','Poprzednia strona atutów');next.setAttribute('aria-label','Następna strona atutów');prev.dataset.focusKey='prev';next.dataset.focusKey='next';nav.append(prev,node('span','',`${page+1} / ${pages}`),next);panel.append(nav);}
  const chosen=available.find(f=>f.id===candidate),detail=node('div','feat-picker-detail');
  if(chosen){detail.append(node('h3','',chosen.name),node('p','feat-picker-description',chosen.description));
   if(chosen.abilities?.length){const label=node('label','feat-picker-ability','Zwiększana cecha '),select=node('select');select.setAttribute('aria-label',chosen.name+' · cecha');select.dataset.focusKey='ability';for(const ability of chosen.abilities)select.append(new Option('+1 '+(names[ability]||ability),ability));if(!chosen.abilities.includes(selection))selection=chosen.abilities[0];select.value=selection;select.onchange=()=>{selection=select.value;signature='';sync(hook.state?.().player||p);};label.append(select);detail.append(label);}
  }else detail.append(node('p','feat-picker-description','Wskaż atut, aby zobaczyć jego działanie. Samo wskazanie niczego nie wydaje.'));
  panel.append(detail);
  const why=reason(p,mode,candidate,selection);panel.append(node('p','feat-picker-reason',why||'Wybór jest stały. Zatwierdź dopiero po przeczytaniu opisu.'));
  const footer=node('footer','feat-picker-footer'),cancel=button('Wróć',close),confirm=button(pending?'Zapisywanie…':'Zatwierdź wybór',()=>{
   const latest=hook.state?.().player||p;
   if(pending||reason(latest,mode,candidate,selection))return;
   receipt=token(latest,mode);pending=true;pendingAt=Date.now();
   const packet=mode==='origin'?{type:'origin_feat',feat:candidate}:root.BractwoSkillsUI.trainingPacket(latest,candidate,{ability:selection});hook.send(packet);signature='';sync(latest);
  },'feat-picker-confirm');confirm.disabled=pending||!!why;confirm.dataset.featConfirm='';confirm.dataset.focusKey='confirm';cancel.dataset.focusKey='cancel';footer.append(cancel,confirm);panel.append(footer);
  panel.scrollTop=scroll;if(focused)[...panel.querySelectorAll('[data-focus-key]')].find(e=>e.dataset.focusKey===focused)?.focus({preventScroll:true});
 }
 const api={open,close,sync,options,reason,get visible(){return !!panel&&!panel.hidden;}};root.BractwoFeatUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
