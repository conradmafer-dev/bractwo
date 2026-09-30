/* Canvas effects for real weapon properties, with no new particle sprites. */
(function(root){'use strict';
 function draw(ctx,e,q){if(!String(e.kind).startsWith('fighter_'))return false;if(q<0||q>1)return true;
  // Parry protects the source of its reaction; offensive effects mark the target.
  const key=e.mastery,x=key==='parry'?e.x:e.target_x??e.x,y=(key==='parry'?e.y:e.target_y??e.y)-18;ctx.save();ctx.translate(x,y);ctx.globalAlpha=1-q;ctx.lineCap='round';
  if(key==='sap'){ctx.strokeStyle='#e8ca71';ctx.lineWidth=3;for(let i=0;i<3;i++){ctx.beginPath();ctx.moveTo(-18+i*16,-25-q*18);ctx.lineTo(-12+i*16,-13-q*18);ctx.lineTo(-5+i*16,-23-q*18);ctx.stroke();}}
  else if(key==='topple'||key==='trip'){ctx.strokeStyle='#dbc897';ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(0,18,16+38*q,7+13*q,0,0,Math.PI*2);ctx.stroke();for(let i=0;i<8;i++){const a=i*Math.PI/4;ctx.fillStyle=i%2?'#c7ad75':'#eee0b8';ctx.fillRect(Math.cos(a)*(12+32*q),18+Math.sin(a)*(5+14*q),4,3);}}
  else if(key==='precision'){
   const r=11+14*(1-q);ctx.strokeStyle='#fff1ad';ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,r,0,Math.PI*2);ctx.stroke();
   for(let i=0;i<4;i++){const a=i*Math.PI/2;ctx.beginPath();ctx.moveTo(Math.cos(a)*(r-5),Math.sin(a)*(r-5));ctx.lineTo(Math.cos(a)*(r+9),Math.sin(a)*(r+9));ctx.stroke();}ctx.fillStyle='#fff8d6';ctx.fillRect(-2,-2,4,4);
  }
  else if(key==='parry'){
   ctx.strokeStyle='#b5f1f6';ctx.fillStyle='rgba(58,151,178,.3)';ctx.lineWidth=3;ctx.beginPath();ctx.moveTo(0,-25);ctx.lineTo(21,-16);ctx.lineTo(17,9);ctx.lineTo(0,24);ctx.lineTo(-17,9);ctx.lineTo(-21,-16);ctx.closePath();ctx.fill();ctx.stroke();ctx.beginPath();ctx.moveTo(0,-16);ctx.lineTo(0,13);ctx.stroke();
   for(let i=0;i<5;i++){const a=-Math.PI+i*Math.PI/4;ctx.beginPath();ctx.moveTo(Math.cos(a)*24,Math.sin(a)*22);ctx.lineTo(Math.cos(a)*(28+q*23),Math.sin(a)*(26+q*23));ctx.stroke();}
  }
  else if(key==='riposte'){
   ctx.strokeStyle='#abedf0';ctx.lineWidth=4;ctx.beginPath();ctx.arc(-9,8,23+q*10,-2.8+q,.8+q);ctx.stroke();ctx.strokeStyle='#ffffff';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-26+q*25,23-q*22);ctx.lineTo(22+q*5,-24-q*5);ctx.lineTo(13+q*5,-21-q*5);ctx.stroke();
  }
  else if(key==='menacing'){
   const r=15+q*25;ctx.strokeStyle='#d69dc2';ctx.fillStyle='rgba(48,12,51,.4)';ctx.lineWidth=3;ctx.beginPath();for(let i=0;i<16;i++){const a=i*Math.PI/8,rr=r+(i%2?4:-4);const x=Math.cos(a)*rr,y=Math.sin(a)*rr;i?ctx.lineTo(x,y):ctx.moveTo(x,y);}ctx.closePath();ctx.fill();ctx.stroke();ctx.strokeStyle='#f2b0c4';ctx.beginPath();ctx.moveTo(-12,-5);ctx.lineTo(-4,-1);ctx.moveTo(12,-5);ctx.lineTo(4,-1);ctx.stroke();
  }
  else if(key==='colossus_slayer'){
   ctx.strokeStyle='#e9b747';ctx.lineWidth=6;ctx.beginPath();ctx.moveTo(-24+q*10,27-q*10);ctx.lineTo(26+q*10,-25-q*10);ctx.stroke();ctx.strokeStyle='#fff5c0';ctx.lineWidth=2;ctx.beginPath();ctx.moveTo(-21,21);ctx.lineTo(24,-24);ctx.stroke();for(let i=0;i<3;i++){ctx.beginPath();ctx.moveTo(-9+i*10,-14+i*9);ctx.lineTo(-2+i*10,-7+i*9);ctx.stroke();}
  }
  else if(key==='horde_breaker'){
   ctx.strokeStyle='#bfe3a2';ctx.lineWidth=3;for(let i=0;i<2;i++){const x=-13+i*24,y=-15-q*16;ctx.beginPath();ctx.moveTo(x,25-q*17);ctx.lineTo(x,y);ctx.moveTo(x-6,y+7);ctx.lineTo(x,y);ctx.lineTo(x+6,y+7);ctx.stroke();}ctx.strokeStyle='#e6f4c3';ctx.lineWidth=1;ctx.beginPath();ctx.arc(0,0,19+q*20,0,Math.PI*2);ctx.stroke();
  }
  else if(key==='giant_killer'){
   ctx.strokeStyle='#d2e9b6';ctx.lineWidth=5;for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(side*(-28-q*8),27+q*8);ctx.lineTo(side*(24+q*8),-24-q*8);ctx.stroke();}ctx.strokeStyle='#fff6cd';ctx.lineWidth=2;ctx.beginPath();ctx.arc(0,0,8+q*17,0,Math.PI*2);ctx.stroke();
  }
  else{ctx.strokeStyle=key==='surge'?'#fff2b0':'#d5e6e4';ctx.lineWidth=key==='surge'?4:2;
   for(let i=0;i<(key==='surge'?3:1);i++){ctx.beginPath();ctx.arc(-14+i*12,6,20+q*25,-1.5+q,0.8+q);ctx.stroke();}
   for(let i=0;i<6;i++){const a=i*1.047;ctx.beginPath();ctx.moveTo(Math.cos(a)*8,Math.sin(a)*8);ctx.lineTo(Math.cos(a)*(12+30*q),Math.sin(a)*(12+30*q));ctx.stroke();}
  }ctx.restore();return true;
 }
 function statuses(ctx,e,x,y,t){const statuses=e.status_effects||[];if(statuses.some(s=>s.id==='sap')){ctx.save();ctx.strokeStyle='#f7da8a';ctx.lineWidth=2;ctx.translate(x,y-46);for(let i=0;i<3;i++){ctx.beginPath();ctx.moveTo(-10+i*10,-3);ctx.lineTo(-7+i*10,2);ctx.lineTo(-3+i*10,-3);ctx.stroke();}ctx.restore();}
  if(statuses.some(s=>s.id==='prone')){ctx.save();ctx.strokeStyle='#ddc89b';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(x,y+5,25,9,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#edd995';ctx.font='bold 12px sans-serif';ctx.fillText('↘',x+17,y-17);ctx.restore();}
  if(statuses.some(s=>s.id==='frightened')){ctx.save();ctx.translate(x,y-45);ctx.globalAlpha=.65+.25*Math.sin((Number(t)||0)*5);ctx.strokeStyle='#e4a4ce';ctx.lineWidth=2;for(const side of [-1,1]){ctx.beginPath();ctx.moveTo(side*6,-3);ctx.lineTo(side*11,-9);ctx.lineTo(side*9,-15);ctx.stroke();}ctx.restore();}
 }
 const api={draw,statuses};root.BractwoFighterVFX=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
