/* Spell choices are kept per character; the server validates every cast. */
(function(root){'use strict';
 const choices=new Map();
 const pickers=[['variants','variant','Wariant'],['forms','form','Postać'],['skills','skill','Umiejętność']];
 const skills={acrobatics:'Akrobatyka',animal_handling:'Opieka nad zwierzętami',arcana:'Wiedza tajemna',athletics:'Atletyka',deception:'Oszustwo',history:'Historia',insight:'Intuicja',intimidation:'Zastraszanie',investigation:'Śledztwo',medicine:'Medycyna',nature:'Przyroda',perception:'Percepcja',performance:'Występy',persuasion:'Perswazja',religion:'Religia',sleight_of_hand:'Zwinne dłonie',stealth:'Skradanie',survival:'Sztuka przetrwania'};
 const key=(id,p)=>String(p?.id||'')+':'+id;
 function permitted(option,p){return option.available!==false&&!option.disabled&&(!option.level||p?.level>=option.level);}
 function options(id,p,spec){
  const saved=choices.get(key(id,p))||{},result={};
  for(const [list,field]of pickers){const available=(spec?.circle_options?.[list]||[]).filter(option=>permitted(option,p));if(!available.length)continue;const fallback=field==='skill'?'perception':id==='conjure_elemental'?'fire':'';result[field]=available.find(option=>option.id===saved[field])?.id||available.find(option=>option.id===fallback)?.id||available[0].id;}
  return result;
 }
 function append(parent,p,spec,h,unlocked=true){
  const metadata=spec?.circle_options;if(!metadata)return;
  const box=document.createElement('div');box.className='circle-spell-options';
  const current=()=>h.state?.().player||p;
  for(const [list,field,label]of pickers){
   const values=(metadata[list]||[]).filter(option=>permitted(option,p));if(!values.length)continue;
   const wrapper=document.createElement('label'),caption=document.createElement('span'),select=document.createElement('select');caption.textContent=label;select.setAttribute('aria-label',spec.name+' · '+label.toLowerCase());
   for(const value of values)select.append(new Option((field==='skill'?skills[value.id]||value.name:value.name)+(value.cr!==undefined?' · SW '+value.cr:''),value.id));select.value=options(spec.id,p,spec)[field];select.disabled=!unlocked;
   select.addEventListener('change',()=>choices.set(key(spec.id,current()),{...choices.get(key(spec.id,current())),[field]:select.value}));wrapper.append(caption,select);box.append(wrapper);
  }
  for(const action of metadata.actions||[]){
   const b=document.createElement('button');b.type='button';b.textContent=action.name;b.dataset.circleSpellAction=action.id;
   const allyRequired=action.id==='wake';b.disabled=!unlocked||!p.alive||action.enabled===false||(allyRequired&&!h.selectedAlly?.());
   b.addEventListener('click',()=>{
    const latest=current();if(!latest.alive)return;
    const packet={type:'circle_spell_action',action:action.id,spell:spec.id};
    if(['move_pack','redirect_wind','tree_step','attack_wall'].includes(action.id)){const point=h.targetPoint?.();if(point)packet.point=point;}
    if(action.id==='control_water')packet.variant=options(spec.id,latest,spec).variant;
    if(action.id==='wake'){const ally=h.selectedAlly?.();if(!ally)return;packet.target_id=String(ally.id);}
    h.send(packet);
   });box.append(b);
  }
  if(metadata.actions?.some(action=>['move_pack','redirect_wind','tree_step'].includes(action.id))){const hint=document.createElement('small');hint.textContent='Kliknij wybrane miejsce w świecie, a następnie użyj przycisku tej zdolności.';hint.className='circle-spell-point-hint';box.append(hint);}
  if(box.childNodes.length)parent.append(box);
 }
 const api={options,append};root.BractwoCircleSpellUI=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
