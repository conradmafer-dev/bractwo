/* Durable per-level receipts. No timers, replacement, before/after or modal focus theft. */
(function(root){'use strict';
  const node=(tag,cls,text)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(text!==undefined)e.textContent=text;return e;};
  const button=(text,fn,cls='')=>{const e=node('button',cls,text);e.type='button';e.addEventListener('click',fn);return e;};
  function rowText(row){return `${row.label} ${row.gain}${row.unit?' '+row.unit:''}`;}
  function create(h){
    const panel=document.getElementById('levelUpCascade'),viewport=panel.querySelector('.level-up-viewport'),layer=panel.querySelector('.level-up-layer'),counter=panel.querySelector('.level-up-counter');
    const cards=new Map(),closing=new Set();let player=null,active='',account='',lastIds='',lastLayout='';
    function reset(){cards.clear();closing.clear();layer.replaceChildren();panel.hidden=true;lastIds='';active='';account='';}
    function raise(id){if(!cards.has(id))return;active=id;layout(false);viewport.scrollTop=Math.max(0,(cards.size-1)*(innerWidth<560?36:42));}
    function dismiss(id){if(!h.ready())return;closing.add(id);h.send({type:'dismiss_level_up',id});cards.get(id)?.remove();cards.delete(id);lastIds='';layout(false);if(cards.size){const ids=[...cards.keys()];raise(ids.at(-1));cards.get(ids.at(-1))?.querySelector('.level-up-title').focus({preventScroll:true});}}
    function make(event){
      const card=node('article','level-up-card');card.dataset.id=event.id;card.dataset.level=event.level;card.setAttribute('aria-label',`Awans na poziom ${event.level}`);
      const head=node('header','level-up-header');const title=button('',()=>raise(event.id),'level-up-title');title.append(node('span','level-up-emblem','⇧'),node('span','',`Poziom ${event.level}`));title.title='Pokaż ten awans na wierzchu';
      const x=button('×',()=>dismiss(event.id),'level-up-x');x.setAttribute('aria-label',`Zamknij awans na poziom ${event.level}`);head.append(title,x);card.append(head);
      const body=node('div','level-up-body');
      for(const row of event.rows||[]){const r=node('div','level-up-row');r.dataset.change=row.id;
        if(row.icon){const img=node('img');img.src=row.icon;img.alt='';img.width=24;img.height=24;r.append(img);}
        const text=node('span','level-up-row-text');text.append(node('span','level-up-label',row.label+' '),node('strong','level-up-gain',row.gain));if(row.unit)text.append(document.createTextNode(' '+row.unit));r.append(text);body.append(r);
        if(row.id==='mastery'){const a=(event.actions||[]).find(a=>a.kind==='mastery');if(a)r.append(actionButton(a));}
      }
      for(const a of event.actions||[])if(a.kind!=='mastery')body.append(actionButton(a));
      if(!body.childNodes.length)body.append(node('p','level-up-empty','Nowy poziom zdobyty.'));
      card.append(body);const footer=node('footer','level-up-footer');footer.append(button('Zamknij',()=>dismiss(event.id),'level-up-close'));card.append(footer);
      card.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.stopPropagation();}});
      layer.append(card);cards.set(event.id,card);return card;
    }
    function actionButton(a){const b=button(a.label||'Wybierz',()=>h.open(['abilities','feats','skills','stats'].includes(a.tab)?a.tab:'stats',a.section||(a.kind==='skill_expertise'?'training':a.kind==='mastery'?'mastery':undefined)),'level-up-action');b.dataset.kind=a.kind;b.dataset.original=a.label||'Wybierz';return b;}
    function actions(){for(const card of cards.values())for(const b of card.querySelectorAll('[data-kind]')){const assigned=(b.dataset.kind==='mastery'&&!(player?.mastery_points>0))||(b.dataset.kind==='training_feat'&&!(player?.character_sheet?.training?.points>0))||(b.dataset.kind==='skill_expertise'&&!(player?.character_sheet?.skills?.choices?.find(pool=>pool.source==='expertise')?.remaining>0));b.disabled=assigned;b.textContent=assigned?'Przydzielono':b.dataset.original;}}
    function layout(toNewest=false){
      panel.hidden=cards.size===0;if(panel.hidden)return;
      const narrow=innerWidth<560,height=viewport.clientHeight,width=viewport.clientWidth;
      const gap=narrow?36:42,shift=narrow?7:10,cardWidth=width-3*shift-6;
      if(toNewest||!cards.has(active))active=[...cards.keys()].at(-1);
      const ordered=[...cards].filter(([id])=>id!==active).concat(cards.has(active)?[[active,cards.get(active)]]:[]);
      let i=0,maxBottom=0;
      for(const[id,card]of ordered){
        card.style.left=`${Math.min(i,3)*shift}px`;card.style.top=`${i*gap}px`;card.style.width=`${cardWidth}px`;card.style.maxHeight=`${Math.max(82,height-4)}px`;
        card.style.zIndex=String(i+1);card.classList.toggle('front',id===active);
        maxBottom=Math.max(maxBottom,i*gap+card.offsetHeight);i++;
      }
      layer.style.height=`${maxBottom+4}px`;
      const geometry=[width,height,maxBottom].join(':');
      if(toNewest||geometry!==lastLayout)viewport.scrollTop=Math.max(0,maxBottom+4-height);
      lastLayout=geometry;
    }
    function sync(p){
      if(!p)return;
      if(account&&account!==String(p.id))reset();account=String(p.id);player=p;
      const events=p.pending_level_ups||[],incoming=new Set(events.map(e=>e.id));
      for(const id of [...closing])if(!incoming.has(id))closing.delete(id);
      const visible=events.filter(e=>!closing.has(e.id)),key=visible.map(e=>e.id).join('|');
      if(key!==lastIds){const newIds=visible.filter(e=>!cards.has(e.id)).map(e=>e.id);
        for(const[id,card]of cards)if(!visible.some(e=>e.id===id)){card.remove();cards.delete(id);}
        for(const e of visible)if(!cards.has(e.id))make(e);
        // Stable chronological order after a closed middle panel or older backlog entry.
        const sorted=visible.map(e=>[e.id,cards.get(e.id)]);cards.clear();for(const[k,v]of sorted){cards.set(k,v);layer.append(v);}
        lastIds=key;layout(newIds.length>0);if(!cards.has(active)&&cards.size)raise([...cards.keys()].at(-1));
      }
      const total=Math.max(0,(p.level_up_pending_count||events.length)-closing.size);
      counter.textContent=total>cards.size?`Awanse: ${total} · wcześniejsze po zamknięciu tych paneli`:`Awanse: ${total}`;
      const hide=cards.size<2&&total<2;if(counter.hidden!==hide){counter.hidden=hide;layout(false);}actions();
    }
    const resize=()=>layout(false);root.addEventListener('resize',resize);
    return {sync,reset,dismiss,layout,get count(){return cards.size;}};
  }
  const api={create,rowText};root.BractwoLevelUp=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
