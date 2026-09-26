/* Canvas effects for real weapon properties, with no new particle sprites. */
(function(root){'use strict';
 function draw(ctx,e,q){if(!String(e.kind).startsWith('fighter_'))return false;if(q<0||q>1)return true;
  const key=e.mastery,x=e.target_x??e.x,y=(e.target_y??e.y)-18;ctx.save();ctx.translate(x,y);ctx.globalAlpha=1-q;ctx.lineCap='round';
  if(key==='sap'){ctx.strokeStyle='#e8ca71';ctx.lineWidth=3;for(let i=0;i<3;i++){ctx.beginPath();ctx.moveTo(-18+i*16,-25-q*18);ctx.lineTo(-12+i*16,-13-q*18);ctx.lineTo(-5+i*16,-23-q*18);ctx.stroke();}}
  else if(key==='topple'){ctx.strokeStyle='#dbc897';ctx.lineWidth=3;ctx.beginPath();ctx.ellipse(0,18,16+38*q,7+13*q,0,0,Math.PI*2);ctx.stroke();for(let i=0;i<8;i++){const a=i*Math.PI/4;ctx.fillStyle=i%2?'#c7ad75':'#eee0b8';ctx.fillRect(Math.cos(a)*(12+32*q),18+Math.sin(a)*(5+14*q),4,3);}}
  else{ctx.strokeStyle=key==='surge'?'#fff2b0':'#d5e6e4';ctx.lineWidth=key==='surge'?4:2;
   for(let i=0;i<(key==='surge'?3:1);i++){ctx.beginPath();ctx.arc(-14+i*12,6,20+q*25,-1.5+q,0.8+q);ctx.stroke();}
   for(let i=0;i<6;i++){const a=i*1.047;ctx.beginPath();ctx.moveTo(Math.cos(a)*8,Math.sin(a)*8);ctx.lineTo(Math.cos(a)*(12+30*q),Math.sin(a)*(12+30*q));ctx.stroke();}
  }ctx.restore();return true;
 }
 function statuses(ctx,e,x,y,t){const statuses=e.status_effects||[];if(statuses.some(s=>s.id==='sap')){ctx.save();ctx.strokeStyle='#f7da8a';ctx.lineWidth=2;ctx.translate(x,y-46);for(let i=0;i<3;i++){ctx.beginPath();ctx.moveTo(-10+i*10,-3);ctx.lineTo(-7+i*10,2);ctx.lineTo(-3+i*10,-3);ctx.stroke();}ctx.restore();}
  if(statuses.some(s=>s.id==='prone')){ctx.save();ctx.strokeStyle='#ddc89b';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(x,y+5,25,9,0,0,Math.PI*2);ctx.stroke();ctx.fillStyle='#edd995';ctx.font='bold 12px sans-serif';ctx.fillText('↘',x+17,y-17);ctx.restore();}
 }
 const api={draw,statuses};root.BractwoFighterVFX=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
