/* Original pixel-art atlas rendering and transparent, species-owned drop preview. */
(function(root){'use strict';
  const cache=new Map();
  const percent=x=>(Number(x)*100).toLocaleString('pl-PL',{maximumFractionDigits:2})+'%';
  function entries(spec,world){return (spec?.loot?.entries||[]).map(e=>({...e,...(e.kind==='potion'?world.potions?.[e.template]:world.items?.[e.template]),chance:e.chance}));}
  function frame(move,frames=4){return ((Math.floor(Math.max(0,Number(move)||0)*3)%frames)+frames)%frames;}
  function drawMonster(ctx,v,spec,time){
    if(!spec.sprite)return false;
    let image=cache.get(spec.sprite);
    if(!image){image=new Image();image.src=spec.sprite;cache.set(spec.sprite,image);}
    if(!image.complete||!image.naturalWidth)return false;
    const fw=spec.sprite_frame_width||80,fh=spec.sprite_frame_height||80,z=spec.size||1;
    const n=frame(v.move,spec.sprite_frames||4),e=v.entity,flip=(e.facing?.[0]||1)<0?-1:1;
    ctx.save();ctx.translate(Math.round(v.x),Math.round(v.y));ctx.scale(flip*z,z);ctx.imageSmoothingEnabled=false;
    ctx.fillStyle='#233b3566';ctx.beginPath();ctx.ellipse(0,6,21,7,0,0,Math.PI*2);ctx.fill();
    ctx.drawImage(image,n*fw,0,fw,fh,-40,-68,80,80);
    if((e.attack_until||0)>time){ctx.strokeStyle=spec.color||'#e9cd8f';ctx.lineWidth=2;ctx.beginPath();ctx.arc(18,-24,22,-1.1,.6);ctx.stroke();}
    ctx.restore();return true;
  }
  function create(h){
    const panel=document.createElement('section');panel.className='loot-preview';panel.hidden=true;panel.id='lootPreview';panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');panel.setAttribute('aria-labelledby','lootTitle');document.body.append(panel);
    const el=(tag,text,cls)=>{const x=document.createElement(tag);if(text!==undefined)x.textContent=text;if(cls)x.className=cls;return x;};let restore;
    function close(){panel.hidden=true;if(restore?.isConnected)restore.focus({preventScroll:true});}
    function open(spec){if(!spec)return;h.prepare?.();restore=document.activeElement;panel.replaceChildren();panel.hidden=false;
      const head=el('header'),title=el('h2',spec.name);title.id='lootTitle';head.append(title);const x=el('button','×');x.type='button';x.setAttribute('aria-label','Zamknij łupy');x.onclick=close;head.append(x);panel.append(head);
      panel.append(el('p',`Poziom ${spec.level||1}${spec.boss?' · Boss':''} · ${spec.loot_origin||'Możliwe łupy'}`,'loot-level'));
      const list=el('div',undefined,'loot-list'),world=h.world();
      for(const item of entries({loot:{entries:h.player()?.known_loot?.[spec.kind]||[]}},world)){const row=el('div',undefined,'loot-row '+(item.rarity||'common'));
        if(item.icon){const art=el('img');art.src=item.icon;art.alt='';row.append(art);}else row.append(el('span',item.kind==='potion'?'✦':'◆','loot-fallback'));
        const text=el('div');text.append(el('strong',item.name||item.template));
        const detail=item.armor_summary|| (item.damage_dice?`${item.damage_dice}${item.attack?' +'+item.attack:''}${item.attack_bonus?' · trafienie +'+item.attack_bonus:''}`:item.slot==='trophy'?'Trofeum na sprzedaż':item.description||(item.slot==='ring'?'Pierścień'+(item.ac_bonus?' · KP +'+item.ac_bonus:''):item.kind==='potion'?'Mikstura':'Przedmiot'));
        text.append(el('small',detail));row.append(text,el('b',percent(item.chance),'loot-percent'));list.append(row);
      }panel.append(list);
      panel.append(el('p',(h.player()?.known_loot?.[spec.kind]?.length?'Tylko przedmioty, które ta postać zdobyła z tego gatunku. Każdy łup losowany osobno.':'Nie zdobyłeś jeszcze łupu z tego gatunku.'),'loot-note'));
      const b=el('button','Zamknij','loot-close');b.type='button';b.onclick=close;panel.append(b);x.focus({preventScroll:true});
    }
    panel.addEventListener('keydown',e=>{if(e.key==='Tab'){const a=[...panel.querySelectorAll('button')],first=a[0],last=a.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus();}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus();}}});
    return {open,close,get visible(){return !panel.hidden;}};
  }
  root.BractwoLootUI={percent,entries,frame,drawMonster,create};
  if(typeof module!=='undefined')module.exports=root.BractwoLootUI;
})(globalThis);
