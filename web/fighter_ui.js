/* Permanent fighting-style choice. Browsing never sends a gameplay command. */
(function(root){'use strict';
 const node=(tag,text,cls)=>{const el=document.createElement(tag);if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el;};
 const img=path=>{const e=node('img');e.src=path;e.alt='';e.width=e.height=44;return e;};
 const button=(text,fn,disabled=false)=>{const e=node('button',text);e.type='button';e.disabled=disabled;e.onclick=fn;return e;};
 const candidateByPlayer=new Map();
 function canChoose(p,nearMaster){return p.class_id==='knight'&&!!p.alive&&!(p.combat_remaining>0)&&(!p.character_sheet?.fighter?.style||nearMaster);}
 function feats(parent,p,h){
  const f=p.character_sheet?.fighter;
  if(!f||!f.choices){const empty=node('div',undefined,'sheet-empty-feats');empty.append(node('h3','Atuty'),node('p','Nie masz jeszcze atutów.'));parent.append(empty);return;}
  const section=node('section',undefined,'fighter-section');parent.append(section);
  function paint(){
   section.replaceChildren();section.append(node('h3','Styl walki','sheet-section-title'));
   const editable=canChoose(p,!!h.nearMaster?.());
   const current=f.choices.find(c=>c.id===f.style);
   section.append(node('p',current?`Wybrany: ${current.name} · ${f.style_active?'aktywny':'nieaktywny z obecnym wyposażeniem'}`:'Masz jeden dostępny wybór. Nie zużywa punktu cechy ani późniejszego atutu.','fighter-current'));
   const candidate=candidateByPlayer.get(String(p.id))||f.style||'';
   const grid=node('div',undefined,'fighter-style-grid');grid.setAttribute('aria-label','Style walki');
   for(const style of f.choices){
    const card=button('',()=>{candidateByPlayer.set(String(p.id),style.id);paint();});
    card.className='fighter-style'+(candidate===style.id?' selected':'');card.dataset.style=style.id;card.setAttribute('aria-pressed',String(candidate===style.id));
    card.append(img(style.icon),node('strong',style.name),node('span',style.description),node('small',style.active_with_gear?'Działa z obecnym wyposażeniem':style.requirement,style.active_with_gear?'style-compatible':'style-incompatible'));
    grid.append(card);
   }section.append(grid);
   const selected=f.choices.find(c=>c.id===candidate);
   if(selected){const confirm=node('div',undefined,'fighter-confirm');confirm.append(node('span',selected.name));
    const apply=button(f.style===candidate?'Wybrany styl':f.style?'Zmień styl bez opłaty':'Wybierz ten styl',()=>{apply.disabled=true;h.send({type:'fighting_style',style:candidate});},!editable||f.style===candidate);apply.dataset.confirmStyle=candidate;confirm.append(apply);section.append(confirm);
   }
   section.append(node('p',p.combat_remaining>0?'Wybór jest dostępny po zakończeniu walki.':current?'Zmiana bez opłaty u mistrza profesji w osadzie. Zmiana broni nie zmienia stylu.':'Kliknij kafelek, przeczytaj opis i zatwierdź wybór przyciskiem.','sheet-hint'));
  }paint();
  const section2=node('section',undefined,'fighter-section');section2.append(node('h3','Mistrzostwo broni','sheet-section-title'),node('p','Opanowane trzy rodzaje broni. Przy ataku działa właściwość aktualnie używanej broni.','sheet-hint'));
  for(const m of f.masteries||[]){const row=node('article',undefined,'fighter-mastery'+(m.active?' active':''));row.append(img(m.icon));const text=node('div');text.append(node('strong',m.name+' · '+m.effect_name),node('p',m.description),node('small',m.active?'Aktywne z obecną bronią':'Użyj tego rodzaju broni'));row.append(text);section2.append(row);}
  parent.append(section2);
  if(f.can_change_grip){const grip=node('section',undefined,'fighter-section');grip.append(node('h3','Chwyt broni','sheet-section-title'),node('p','Jednorącz: możesz nosić tarczę. Oburącz: większa kość broni wszechstronnej; tarcza pozostaje w plecaku.','sheet-hint'));
   const actions=node('div',undefined,'item-actions');for(const [key,label]of [['one','Jednorącz'],['two','Oburącz']])actions.append(button((f.weapon_grip===key?'✓ ':'')+label,()=>h.send({type:'weapon_grip',grip:key}),!p.alive||p.combat_remaining>0||f.weapon_grip===key));grip.append(actions);parent.append(grip);
  }
 }
 function createPrompt(h){
  const panel=node('aside',undefined,'fighter-choice');panel.id='fighterChoice';panel.hidden=true;panel.setAttribute('aria-label','Wybierz styl walki');
  const head=node('header');head.append(node('strong','Wybierz styl walki'));const close=button('×',()=>{const p=h.player();if(!p)return;closed.add(String(p.id));try{localStorage.setItem(key(p),'1');}catch{}panel.hidden=true;});close.setAttribute('aria-label','Wybierz styl później');head.append(close);
  panel.append(head,node('p','Masz jeden dostępny wybór.'),button('Wybierz styl',()=>h.open('feats')));
  (document.getElementById('hudLeftRail')||document.getElementById('gameUI')).append(panel);
  const closed=new Set(),key=p=>'bractwo-fighter-choice-v1:'+p.id;
  function sync(){const p=h.player();let hidden=!p||!p.character_sheet?.fighter?.pending;
   if(p){try{hidden=hidden||localStorage.getItem(key(p))==='1';}catch{}hidden=hidden||closed.has(String(p.id));}
   panel.hidden=hidden;
  }
  return {sync};
 }
 const api={feats,createPrompt,canChoose};root.BractwoFighterUI=api;if(typeof module!=='undefined')module.exports={canChoose};
})(globalThis);
