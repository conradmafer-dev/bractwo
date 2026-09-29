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
 // Field snapshots are authoritative: no local timeout or independent spawning.
 // Constant particle budgets avoid work growing with spell radius/upcast rank.
 const FIELD_KEYS=new Set(['fog_cloud','sleet_storm','wall_of_stone','web','stinking_cloud','insect_plague','gust_of_wind','control_water','conjure_elemental','conjure_animals']);
 const handlesField=key=>FIELD_KEYS.has(key);
 const FIELD_COLORS={fog_cloud:['#8da6ae20','#dce9e399'],sleet_storm:['#769eb729','#b5dbe7b8'],web:['#b4bd8f16','#e4e4c394'],stinking_cloud:['#7c903d24','#bdc7769c'],insect_plague:['#8d794220','#d4bd808c'],control_water:['#276f9229','#98d9dda9'],conjure_elemental:['#9d795c20','#ddbe959c'],conjure_animals:['#73ae9920','#a8e5c7a6']};
 function finite(value,fallback){return Number.isFinite(Number(value))?Number(value):fallback;}
 function seedOf(value){let n=2166136261;for(const c of String(value||'')){n^=c.charCodeAt(0);n=Math.imul(n,16777619);}return (n>>>0)/4294967296;}
 function fieldGeometry(f){const radius=Math.max(1,finite(f.radius,32)),direction=f.direction||[0,1];return {radius,
  shape:f.key==='gust_of_wind'?'line':f.shape==='square'||['web','control_water'].includes(f.key)?'square':'circle',
  length:Math.max(1,finite(f.length,384)),angle:Math.atan2(finite(direction[1],1),finite(direction[0],0))};}
 function boundary(ctx,g){ctx.beginPath();if(g.shape==='square')ctx.rect(-g.radius,-g.radius,g.radius*2,g.radius*2);else if(g.shape==='line')ctx.rect(0,-g.radius,g.length,g.radius*2);else ctx.arc(0,0,g.radius,0,TAU);}
 function ellipse(ctx,x,y,rx,ry,color,rotation=0){ctx.fillStyle=color;ctx.beginPath();ctx.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),rotation,0,TAU);ctx.fill();}
 function stroke(ctx,color,width=1){ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();}
 function vapor(ctx,r,t,seed,poison){
  // Low rolling banks leave actors and their status indicators fully readable.
  const count=12;
  for(let i=0;i<count;i++){
   const a=i*2.39996+seed*TAU,rr=r*Math.sqrt((i+.5)/count)*.8;
   const x=Math.cos(a)*rr+Math.sin(t*.16+i)*r*.09,y=Math.sin(a)*rr+Math.cos(t*.13+i*2)*r*.06;
   const size=r*(.17+(i%3)*.045),lift=Math.sin(t*.35+i)*3;
   ellipse(ctx,x,y+lift,size*1.5,size*.7,poison?'#83994d26':'#d7e4e328');
   ellipse(ctx,x-size*.45,y-size*.28+lift,size*.9,size*.65,poison?'#bbbf6322':'#eff5ed26');
   ellipse(ctx,x+size*.65,y+size*.12+lift,size,size*.62,poison?'#69773b22':'#8fa6ad20');
  }
  if(poison){for(let i=0;i<7;i++){const q=(t*.1+i/7)%1,a=i*2.3+seed*TAU;
   const x=Math.cos(a)*r*.65,y=Math.sin(a)*r*.58-q*r*.22;
   ctx.globalAlpha=.55*(1-q);ctx.beginPath();ctx.arc(x,y,3+q*6,0,TAU);stroke(ctx,'#d6d586',1.2);
  }ctx.globalAlpha=1;}
  else{ctx.beginPath();for(let i=0;i<3;i++){const y=(i-1)*r*.42+Math.sin(t*.3+i)*3;ctx.moveTo(-r*.8,y);ctx.bezierCurveTo(-r*.3,y-r*.1,r*.22,y+r*.1,r*.8,y);}stroke(ctx,'#dfebe72c',1.1);}
 }
 function sleet(ctx,r,t,seed){
  ellipse(ctx,0,0,r*.94,r*.73,'#accfd517');
  for(let i=0;i<3;i++){ctx.beginPath();ctx.ellipse(0,0,r*(.45+i*.22),r*(.24+i*.16),-.25,t*.12+i*2,t*.12+i*2+2.4);stroke(ctx,'#c5e8ed55',1.6);}
  ctx.beginPath();for(let i=0;i<24;i++){const x=(((i*.618+seed-t*.075)%1+1)%1*2-1)*r;
   const y=(((i*.414+t*.33)%1+1)%1*2-1)*r;ctx.moveTo(x+3,y-6);ctx.lineTo(x-2,y+3);}
  stroke(ctx,'#e0edf0a3',1.25);
  for(let i=0;i<7;i++){const a=i*2.4+seed*TAU,rr=r*(.2+(i%4)*.18),x=Math.cos(a)*rr,y=Math.sin(a)*rr;
   ctx.beginPath();ctx.moveTo(x-6,y+2);ctx.lineTo(x,y-6);ctx.lineTo(x+8,y);ctx.lineTo(x+2,y+4);ctx.closePath();ctx.fillStyle='#b5d3df38';ctx.fill();stroke(ctx,'#d3e9ed4c',.8);}
 }
 function silk(ctx,r,t,seed){
  const cx=Math.sin(seed*TAU)*r*.18,cy=Math.cos(seed*TAU)*r*.12;
  const anchors=[[-r,-r],[0,-r],[r,-r],[r,0],[r,r],[0,r],[-r,r],[-r,0]];
  ctx.beginPath();for(const [x,y] of anchors){ctx.moveTo(cx,cy);ctx.quadraticCurveTo((x+cx)*.5,(y+cy)*.5+4,x,y);}stroke(ctx,'#d8dbb385',1.1);
  for(let ring=1;ring<=5;ring++){const q=ring/5;ctx.beginPath();for(let i=0;i<=8;i++){
   const a=anchors[i%8],b=anchors[(i+7)%8],x=cx+(a[0]-cx)*q,y=cy+(a[1]-cy)*q;
   if(!i)ctx.moveTo(x,y);else ctx.quadraticCurveTo(cx+((a[0]+b[0])*.5-cx)*q*.82,cy+((a[1]+b[1])*.5-cy)*q*.82,x,y);
  }stroke(ctx,ring%2?'#f0ecd078':'#b4c5b058',ring===5?1.2:.8);}
  for(let i=0;i<6;i++){const a=anchors[i],q=.24+(i%3)*.2;ellipse(ctx,cx+(a[0]-cx)*q,cy+(a[1]-cy)*q,1.1,1.8,'#f7eedaaa');}
 }
 function insects(ctx,r,t,seed){
  // Each insect has a body and paired wings; no noise-driven flicker.
  for(let i=0;i<28;i++){const a=i*2.4+seed*TAU+t*(.18+(i%3)*.06),rr=r*(.18+(i%6)*.125);
   const x=Math.cos(a)*rr+Math.sin(t*1.4+i)*4,y=Math.sin(a)*rr+Math.cos(t*1.1+i)*4;
   const wing=1.5+Math.sin(t*11+i)*.55;
   ellipse(ctx,x-2,y-1,2.8,wing,'#d4c8966e',-.45);ellipse(ctx,x+2,y-1,2.8,wing,'#c4cfaa65',.45);
   ellipse(ctx,x,y,1.1,2.5,'#253d35cc',a);
  }
 }
 function waves(ctx,r,t,color,lanes=7){
  ctx.beginPath();for(let i=0;i<lanes;i++){const y=-r+(i+.5)*r*2/lanes+Math.sin(t*.85+i)*3;
   ctx.moveTo(-r,y);ctx.bezierCurveTo(-r*.5,y-7+Math.sin(t+i)*3,r*.3,y+7,r,y-3);}
  stroke(ctx,color,1.4);
 }
 function water(ctx,f,r,t){
  const variant=f.water_variant||f.variant||'flood',flow=f.flow||[1,0],angle=Math.atan2(finite(flow[1],0),finite(flow[0],1));
  if(variant==='whirlpool'){
   ellipse(ctx,0,0,r*.55,r*.55,'#1d4e6d4c');
   for(let arm=0;arm<4;arm++){ctx.beginPath();for(let j=0;j<=24;j++){const q=j/24,a=q*TAU*1.3+arm*TAU/4-t*.7,rr=r*(.04+.87*q);const x=Math.cos(a)*rr,y=Math.sin(a)*rr;if(j)ctx.lineTo(x,y);else ctx.moveTo(x,y);}stroke(ctx,arm%2?'#83c8d68c':'#d0e8dc85',1.7);}
   ellipse(ctx,0,0,r*.065,r*.055,'#244b659c');
  }else if(variant==='part'){
   ctx.save();ctx.rotate(angle);waves(ctx,r*1.5,t,'#b8e7e579');
   ctx.fillStyle='#938b593f';ctx.fillRect(-r*1.5,-r*.24,r*3,r*.48);
   for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(-r*1.5,side*r*.24);ctx.bezierCurveTo(-r*.5,side*r*.31,r*.5,side*r*.2,r*1.5,side*r*.24);stroke(ctx,'#def0dba8',2.1);
    for(let i=0;i<6;i++){const x=-r+(i+.4)*r/3;ellipse(ctx,x,side*r*.25,r*.08,r*.025,'#cff0e74c');}}
   ctx.restore();
  }else if(variant==='redirect'){
   ctx.save();ctx.rotate(angle);waves(ctx,r*1.5,t,'#9edbdc55',8);
   ctx.beginPath();for(let i=0;i<12;i++){const q=(t*.17+i*.618)%1,x=(q*2-1)*r*1.35,y=((i*.414)%1*2-1)*r;
    ctx.moveTo(x-18,y+2);ctx.quadraticCurveTo(x,y-3,x+15,y);ctx.lineTo(x+8,y-4);ctx.moveTo(x+15,y);ctx.lineTo(x+8,y+5);}
   stroke(ctx,'#d7eeeaa1',1.5);ctx.restore();
  }else{
   waves(ctx,r,t,'#b1dfdc83');
   for(let i=0;i<8;i++){const a=i*2.4,rr=r*(.28+(i%3)*.22);ctx.beginPath();ctx.ellipse(Math.cos(a)*rr,Math.sin(a)*rr,7+(i%3)*3,2.5,0,0,Math.PI*1.6);stroke(ctx,'#d2ebe37a',1.2);}
   // Thin edge foam follows the actual square of raised water.
   ctx.strokeStyle='#d6efde64';ctx.lineWidth=4;ctx.strokeRect(-r+3,-r+3,r*2-6,r*2-6);
  }
 }
 function spiritWolf(ctx,x,y,angle,t,index){
  ctx.save();ctx.translate(x,y);ctx.rotate(angle);ctx.scale(1,.85);const step=Math.sin(t*7+index)*4;
  ctx.beginPath();ctx.moveTo(-19,-5);ctx.lineTo(-8,-10);ctx.lineTo(8,-8);ctx.lineTo(17,-16);ctx.lineTo(18,-9);ctx.lineTo(27,-6);ctx.lineTo(22,-1);ctx.lineTo(13,1);ctx.lineTo(8,7);ctx.lineTo(-8,7);ctx.lineTo(-17,1);ctx.lineTo(-27,-7);ctx.closePath();ctx.fillStyle='#a8e4ce68';ctx.fill();stroke(ctx,'#d1eee6a3',1.2);
  ctx.beginPath();ctx.moveTo(-10,4);ctx.lineTo(-14+step,15);ctx.moveTo(-2,6);ctx.lineTo(1-step,14);ctx.moveTo(9,2);ctx.lineTo(12+step,12);stroke(ctx,'#c1ead19a',2);
  ellipse(ctx,18,-6,1.2,1.2,'#eff9cfb0');ctx.beginPath();ctx.moveTo(-17,-2);ctx.quadraticCurveTo(-30,5,-38,0);stroke(ctx,'#85c8b346',3);ctx.restore();
 }
 function animals(ctx,r,t,seed){
  ctx.beginPath();ctx.arc(0,0,r*.54,0,TAU);stroke(ctx,'#94cbae2b',1.3);
  for(let i=0;i<3;i++){const a=t*.32+i*TAU/3+seed*TAU,x=Math.cos(a)*r*.5,y=Math.sin(a)*r*.5;
   spiritWolf(ctx,x,y,a+Math.PI/2,t,i);
   for(let j=0;j<2;j++){const old=a-.4-j*.18;ellipse(ctx,Math.cos(old)*r*.5,Math.sin(old)*r*.5,2,3,'#c0e6cb2d',old);}}
 }
 function elemental(ctx,f,r,t,seed){
  const type=f.damage_type||'fire';
  if(type==='fire'){
   ellipse(ctx,0,4,r*.58,r*.32,'#e59d4920');
   for(let i=0;i<7;i++){const a=i*2.4,rr=r*(.14+(i%3)*.18),x=Math.cos(a)*rr,y=Math.sin(a)*rr,h=15+(i%3)*7+Math.sin(t*3+i)*3;
    ctx.beginPath();ctx.moveTo(x-8,y+7);ctx.quadraticCurveTo(x-13,y-h*.25,x-3,y-h);ctx.quadraticCurveTo(x+2,y-h*.35,x+6,y-h*.65);ctx.quadraticCurveTo(x+15,y+3,x+3,y+9);ctx.closePath();ctx.fillStyle=i%2?'#d76a4283':'#f5ac588a';ctx.fill();
    ctx.beginPath();ctx.moveTo(x-3,y+5);ctx.quadraticCurveTo(x-2,y-8,x+2,y-h*.5);ctx.quadraticCurveTo(x+8,y+5,x-3,y+5);ctx.fillStyle='#ffe3a79a';ctx.fill();}
  }else if(type==='cold'){
   for(let i=0;i<3;i++){const a=t*.6+i*2.1;ctx.beginPath();ctx.ellipse(0,0,r*(.35+i*.16),r*(.2+i*.13),a,0,Math.PI*1.5);stroke(ctx,'#96dfe4a0',3-i*.6);}
   ctx.beginPath();ctx.moveTo(-13,8);ctx.bezierCurveTo(-29,-15,-9,-17,3,-34);ctx.bezierCurveTo(0,-15,28,-13,14,9);ctx.quadraticCurveTo(0,18,-13,8);ctx.fillStyle='#76bedb61';ctx.fill();stroke(ctx,'#c4f1e28a',1.4);
   for(let i=0;i<5;i++){const a=t*.5+i*2.4;ellipse(ctx,Math.cos(a)*r*.65,Math.sin(a)*r*.65,2,3,'#ccebea9a');}
  }else if(type==='thunder'){
   // Earth is thunder in the authoritative elemental damage mapping.
   for(let i=0;i<7;i++){const a=i*2.4+seed*TAU,rr=r*(.18+(i%3)*.21),x=Math.cos(a)*rr,y=Math.sin(a)*rr,sz=6+i%3*3,lift=3+Math.sin(t*1.3+i)*2;
    ellipse(ctx,x,y+4,sz*1.2,sz*.42,'#3e4b3333');ctx.beginPath();ctx.moveTo(x-sz,y-lift);ctx.lineTo(x-sz*.5,y-sz-lift);ctx.lineTo(x+sz*.55,y-sz*.8-lift);ctx.lineTo(x+sz,y-lift);ctx.lineTo(x+sz*.2,y+sz*.65-lift);ctx.closePath();ctx.fillStyle=i%2?'#9c947b9c':'#b5ab889c';ctx.fill();stroke(ctx,'#d6caa783',1);}
   ctx.beginPath();ctx.moveTo(-r*.65,r*.65);ctx.lineTo(-r*.1,r*.15);ctx.lineTo(r*.05,r*.4);ctx.lineTo(r*.4,-r*.3);stroke(ctx,'#d2be873d',1.5);
  }else{
   // Air spirit: stacked moving wind ribbons and faint static, not a flash.
   for(let i=0;i<5;i++){const y=12-i*9,w=12+i*6,a=t*.65+i*.8;ctx.beginPath();ctx.ellipse(Math.sin(a)*3,y,w,5+i*1.5,-.12,a,a+Math.PI*1.65);stroke(ctx,i%2?'#a2ccdda3':'#e0e9d496',1.8);}
   ctx.beginPath();ctx.moveTo(-8,-28);ctx.lineTo(-1,-17);ctx.lineTo(-5,-8);ctx.lineTo(6,4);stroke(ctx,'#c7e6e16a',1.2);
  }
 }
 function wind(ctx,g,t,seed){
  for(let i=0;i<9;i++){const q=(t*.24+i*.618+seed)%1,x=q*g.length,y=Math.sin(i*2.4)*g.radius*.76;
   ctx.beginPath();ctx.moveTo(x-40,y+3);ctx.bezierCurveTo(x-26,y-3,x-5,y+3,x+8,y-1);stroke(ctx,'#cee4de95',1.4);
   ctx.beginPath();ctx.moveTo(x+7,y-1);ctx.quadraticCurveTo(x+21,y-10,x+18,y-1);stroke(ctx,'#a2c6c455',1);
   if(i%2===0){ctx.beginPath();ctx.ellipse(x-20,y+7,3,1.6,Math.sin(t+i),0,TAU);ctx.fillStyle='#a7bb7683';ctx.fill();}}
 }
 function stoneWall(ctx,f,t){
  for(const s of f.segments||[]){if(s.hp<=0||![s.x,s.y].every(Number.isFinite))continue;
   const w=Math.max(1,finite(s.w,32)),h=Math.max(1,finite(s.h,32)),hp=Math.max(0,finite(s.hp,1))/Math.max(1,finite(s.max_hp,s.hp||1));
   ctx.fillStyle='#364b3b3f';ctx.fillRect(s.x+3,s.y+5,w,h);ctx.fillStyle='#7f8b77';ctx.fillRect(s.x,s.y,w,h);ctx.strokeStyle='#c5c6a8b5';ctx.lineWidth=1.2;ctx.strokeRect(s.x,s.y,w,h);
   ctx.save();ctx.beginPath();ctx.rect(s.x,s.y,w,h);ctx.clip();ctx.beginPath();
   const horizontal=w>=h;
   for(let i=1;i<5;i++){if(horizontal){const x=s.x+w*i/5;ctx.moveTo(x,s.y);ctx.lineTo(x-3,s.y+h);}else{const y=s.y+h*i/5;ctx.moveTo(s.x,y);ctx.lineTo(s.x+w,y-3);}}
   stroke(ctx,'#4e6051a1',1);ctx.fillStyle='#b7bda359';ctx.fillRect(s.x+1,s.y+1,Math.max(1,w-2),Math.min(3,h));
   if(hp<.65){ctx.beginPath();ctx.moveTo(s.x+w*.2,s.y+h*.12);ctx.lineTo(s.x+w*.48,s.y+h*.46);ctx.lineTo(s.x+w*.34,s.y+h*.62);ctx.lineTo(s.x+w*.67,s.y+h*.9);stroke(ctx,'#3d4f42b0',1.3);}
   ctx.restore();
  }
 }
 function fields(ctx,entries,t){
  t=finite(t,0);
  for(const f of entries||[]){if(!f||![f.x,f.y].every(Number.isFinite))continue;ctx.save();
   if(f.key==='wall_of_stone'){stoneWall(ctx,f,t);ctx.restore();continue;}
   const g=fieldGeometry(f),r=g.radius,seed=seedOf(f.id||f.key),clock=t+seed*19;
   ctx.translate(f.x,f.y);if(g.shape==='line')ctx.rotate(g.angle);
   const palette=FIELD_COLORS[f.key]||['#80b99b20','#c3edd191'];boundary(ctx,g);ctx.fillStyle=palette[0];ctx.fill();
   ctx.save();boundary(ctx,g);ctx.clip();
   if(f.key==='fog_cloud')vapor(ctx,r,clock,seed,false);
   else if(f.key==='stinking_cloud')vapor(ctx,r,clock,seed,true);
   else if(f.key==='sleet_storm')sleet(ctx,r,clock,seed);
   else if(f.key==='web')silk(ctx,r,clock,seed);
   else if(f.key==='insect_plague')insects(ctx,r,clock,seed);
   else if(f.key==='control_water')water(ctx,f,r,clock);
   else if(f.key==='conjure_animals')animals(ctx,r,clock,seed);
   else if(f.key==='conjure_elemental')elemental(ctx,f,r,clock,seed);
   else if(f.key==='gust_of_wind')wind(ctx,g,clock,seed);
   ctx.restore();boundary(ctx,g);stroke(ctx,palette[1],1.15);ctx.restore();
  }
 }
 const api={ground,overlay,form,fields,fieldGeometry,handlesField};root.BractwoCircleVFX=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
