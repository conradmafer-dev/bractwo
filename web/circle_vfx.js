/* Lightweight world-space effects and animal art; no gameplay rules. */
(function(root){'use strict';
 const TAU=Math.PI*2,images=new Map(),forms=new Set(['mammoth','elephant','giant_scorpion','polar_bear','eagle']);
 function star(ctx,x,y,r,color){ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(x,y-r);ctx.lineTo(x+r*.3,y-r*.3);ctx.lineTo(x+r,y);ctx.lineTo(x+r*.3,y+r*.3);ctx.lineTo(x,y+r);ctx.lineTo(x-r*.3,y+r*.3);ctx.lineTo(x-r,y);ctx.lineTo(x-r*.3,y-r*.3);ctx.closePath();ctx.fill();}
 function ground(ctx,x,y,player,t){
  const v=player?.circle_visual;if(!v)return;ctx.save();
  if(v.sea_radius>0){
   const r=v.sea_radius;ctx.fillStyle='#3bafce18';ctx.strokeStyle='#9cdef2b0';ctx.lineWidth=1.4;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();ctx.stroke();
   for(let i=0;i<3;i++){const a=t*.45+i*TAU/3;ctx.strokeStyle='#d3f7ffb0';ctx.beginPath();ctx.arc(x,y,r-3-Math.sin(t*2+i)*2,a,a+.6);ctx.stroke();}
  }
  if(v.sanctuary){const s=v.sanctuary,cx=Number.isFinite(s.x)?s.x:x,cy=Number.isFinite(s.y)?s.y:y,half=48;ctx.fillStyle='#88b86813';ctx.strokeStyle='#d4e2a4aa';ctx.lineWidth=1.4;ctx.fillRect(cx-half,cy-half,half*2,half*2);ctx.strokeRect(cx-half,cy-half,half*2,half*2);for(let i=0;i<4;i++)star(ctx,cx+(i%2?half:-half),cy+(i<2?-half:half)-Math.sin(t*2+i)*2,3,'#dcf4b9');}
  if(v.flight){ctx.strokeStyle='#d5edf09c';ctx.lineWidth=1.4;for(let i=0;i<2;i++){ctx.beginPath();ctx.ellipse(x,y+3+i*5,11+i*5,3,0,.15,Math.PI-.15);ctx.stroke();}}
  ctx.restore();
 }
 function overlay(ctx,x,y,player,t){
  const v=player?.circle_visual;if(!v)return;ctx.save();
  if(v.starry_form){
   const nodes=[[-10,-30],[3,-42],[12,-25],[-3,-13],[-13,-5]],phase=t*.7;ctx.strokeStyle='#addcffa0';ctx.lineWidth=1;ctx.beginPath();nodes.forEach(([dx,dy],i)=>{if(i)ctx.lineTo(x+dx,y+dy);else ctx.moveTo(x+dx,y+dy);});ctx.stroke();
   nodes.forEach(([dx,dy],i)=>star(ctx,x+dx,y+dy,2.3+.6*Math.sin(phase+i),'#d9f0ff'));
   ctx.strokeStyle='#99cff5';ctx.lineWidth=1.5;ctx.beginPath();
   if(v.starry_form==='archer'){ctx.arc(x+17,y-25,13,-1.1,1.1);ctx.moveTo(x+23,y-37);ctx.lineTo(x+23,y-13);ctx.moveTo(x+13,y-25);ctx.lineTo(x+35,y-25);}
   else if(v.starry_form==='chalice'){ctx.moveTo(x-23,y-31);ctx.quadraticCurveTo(x-25,y-13,x-14,y-16);ctx.quadraticCurveTo(x-5,y-16,x-7,y-31);ctx.closePath();ctx.moveTo(x-15,y-16);ctx.lineTo(x-15,y-9);ctx.moveTo(x-22,y-8);ctx.lineTo(x-8,y-8);}
   else{ctx.moveTo(x+18,y-45);ctx.lineTo(x+29,y-34);ctx.lineTo(x+20,y-33);ctx.lineTo(x+29,y-18);ctx.lineTo(x+20,y-12);ctx.lineTo(x+26,y-5);}
   ctx.stroke();
  }
  if(v.flight){const lift=Math.sin(t*3)*2;ctx.strokeStyle='#d4edfac0';ctx.lineWidth=1.4;ctx.beginPath();ctx.moveTo(x-9,y-37);ctx.lineTo(x-22,y-43-lift);ctx.lineTo(x-18,y-32);ctx.moveTo(x+9,y-37);ctx.lineTo(x+22,y-43-lift);ctx.lineTo(x+18,y-32);ctx.stroke();}
  if(v.submerged){ctx.fillStyle='#479abe55';ctx.beginPath();ctx.ellipse(x,y-12,19,20,0,0,TAU);ctx.fill();ctx.strokeStyle='#c1eeffad';ctx.lineWidth=1.2;for(let i=0;i<3;i++){const progress=(t*.5+i/3)%1;ctx.beginPath();ctx.arc(x+Math.sin(i*2+t)*12,y-18-progress*27,1.6+i*.4,0,TAU);ctx.stroke();}ctx.beginPath();ctx.ellipse(x,y+1,22,5,0,0,TAU);ctx.stroke();}
  ctx.restore();
 }
 function form(ctx,x,y,entity,t){
  const kind=entity?.kind||entity?.form;if(!forms.has(kind))return false;
  let sprite=images.get(kind);if(!sprite){if(typeof Image==='undefined')return false;sprite=new Image();sprite.src='assets/creatures/'+kind+'.svg';images.set(kind,sprite);}
  if(!sprite.complete||!sprite.naturalWidth)return false;
  const size=Math.max(.5,Number(entity.size)||1),width=(kind==='eagle'?60:kind==='polar_bear'?74:kind==='giant_scorpion'?78:92)*size,height=width*.75;
  const face=entity.facing||[1,0],flip=face[0]<0?-1:1,bob=Math.sin(t*5)*.7;
  ctx.save();ctx.translate(x,y+bob);ctx.scale(flip,1);ctx.drawImage(sprite,-width/2,-height+7,width,height);ctx.restore();return true;
 }
 function fields(ctx,entries,t){
  for(const f of entries||[]){
   const r=Math.max(1,Number(f.radius)||32);ctx.save();
   if(f.key==='wall_of_stone'){
    for(const s of f.segments||[]){if(s.hp<=0)continue;const w=s.w||32,h=s.h||32;ctx.fillStyle='#536253aa';ctx.fillRect(s.x+3,s.y+5,w,h);ctx.fillStyle='#899482';ctx.fillRect(s.x,s.y,w,h);ctx.strokeStyle='#4e5c51';ctx.lineWidth=1.5;ctx.strokeRect(s.x,s.y,w,h);ctx.fillStyle='#b9bc9d';ctx.fillRect(s.x+2,s.y+2,Math.max(1,w-4),3);ctx.beginPath();ctx.moveTo(s.x,s.y+h*.5);ctx.lineTo(s.x+w,s.y+h*.5);ctx.moveTo(s.x+w*.33,s.y);ctx.lineTo(s.x+w*.33,s.y+h*.5);ctx.moveTo(s.x+w*.7,s.y+h*.5);ctx.lineTo(s.x+w*.7,s.y+h);ctx.stroke();}
    ctx.restore();continue;
   }
   ctx.translate(f.x,f.y);
   if(f.key==='gust_of_wind'){
    const d=f.direction||[0,1],length=Number(f.length)||384;ctx.rotate(Math.atan2(d[1],d[0]));ctx.fillStyle='#a3d5d322';ctx.fillRect(0,-r,length,r*2);ctx.strokeStyle='#d9f6ea99';ctx.lineWidth=1.4;
    for(let i=0;i<7;i++){const phase=(t*.3+i/7)%1,x=phase*length,y=Math.sin(i*2)*r*.8;ctx.beginPath();ctx.moveTo(x-15,y);ctx.lineTo(x,y);ctx.lineTo(x-5,y-3);ctx.stroke();}ctx.restore();continue;
   }
   const palette={fog_cloud:['#b8cbce30','#cbdcdda0'],sleet_storm:['#a9d6e62c','#c8f2ffe0'],web:['#d7dab91c','#e4e4c9a0'],stinking_cloud:['#8caa4435','#bfd16a8f'],insect_plague:['#a89c5522','#d8c58491'],control_water:['#4dabe333','#8bdce9b0'],conjure_elemental:['#bd94722b','#edc891a0'],conjure_animals:['#8ad0b427','#bcead999']}[f.key]||['#80b99b25','#c3edd191'];
   const square=['web','control_water'].includes(f.key);ctx.fillStyle=palette[0];ctx.strokeStyle=palette[1];ctx.lineWidth=1.2;
   if(square){ctx.fillRect(-r,-r,r*2,r*2);ctx.strokeRect(-r,-r,r*2,r*2);}else{ctx.beginPath();ctx.arc(0,0,r,0,TAU);ctx.fill();ctx.stroke();}
   if(f.key==='web'){for(let i=1;i<6;i++){const q=-r+i*r/3;ctx.beginPath();ctx.moveTo(-r,q);ctx.lineTo(r,-q);ctx.moveTo(q,-r);ctx.lineTo(-q,r);ctx.stroke();}}
   else if(f.key==='control_water'){for(let i=0;i<5;i++){const yy=-r+(i+.5)*r*.4+Math.sin(t+i)*2;ctx.beginPath();ctx.moveTo(-r+4,yy);ctx.quadraticCurveTo(-r/3,yy+5,r/3,yy);ctx.quadraticCurveTo(r*.7,yy-5,r-4,yy);ctx.stroke();}if((f.variant||f.water_variant)==='whirlpool'){for(let i=1;i<4;i++){ctx.beginPath();ctx.arc(0,0,r*i/4,t+i,t+i+Math.PI*1.4);ctx.stroke();}}}
   else if(f.key==='conjure_animals'){for(let i=0;i<3;i++){const a=t*.5+i*TAU/3,x=Math.cos(a)*r*.45,y=Math.sin(a)*r*.45;ctx.fillStyle='#b3e8d7a0';ctx.beginPath();ctx.ellipse(x,y,13,6,a,0,TAU);ctx.fill();star(ctx,x+Math.cos(a)*12,y+Math.sin(a)*12,4,'#e0fff0');}}
   else{const count=f.key==='insect_plague'?18:8;for(let i=0;i<count;i++){const a=i*2.4+t*.07,rr=r*(.2+(i%5)*.15),x=Math.cos(a)*rr,y=Math.sin(a)*rr+Math.sin(t+i)*3;if(f.key==='insect_plague'){ctx.fillStyle='#263d30a0';ctx.fillRect(x,y,2,2);}else if(f.key==='sleet_storm'){ctx.beginPath();ctx.moveTo(x,y-3);ctx.lineTo(x-2,y+4);ctx.stroke();}else{ctx.fillStyle=palette[0];ctx.beginPath();ctx.ellipse(x,y,r*.25,r*.2,0,0,TAU);ctx.fill();}}}
   ctx.restore();
  }
 }
 const api={ground,overlay,form,fields};root.BractwoCircleVFX=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
