/* UI24: school art uses live server state. No local timers or spawned particles.
 * Ward and illusion overlays follow interpolated actors; shelter stays at its
 * authoritative origin and disappears with the live server snapshot. */
(function(root){'use strict';
  const TAU=Math.PI*2,clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,Number(n)||0));
  const COLORS={ward:'#83d9ec',wardLight:'#e1fbff',illusion:'#bba6ef',illusionLight:'#ece4ff',eye:'#eed188'};
  function line(c,points,color,width=1){c.strokeStyle=color;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.beginPath();c.moveTo(...points[0]);for(let i=1;i<points.length;i++)c.lineTo(...points[i]);c.stroke();}
  function ring(c,x,y,rx,ry,color,width=1,start=0,end=TAU){c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.ellipse(x,y,Math.max(.1,rx),Math.max(.1,ry),0,start,end);c.stroke();}
  function diamond(c,x,y,r,color,angle=0){c.save();c.translate(x,y);c.rotate(angle);line(c,[[0,-r],[r*.62,0],[0,r],[-r*.62,0],[0,-r]],color,1.1);c.restore();}
  function mote(c,x,y,r,color){c.fillStyle=color;c.beginPath();c.arc(x,y,r,0,TAU);c.fill();}
  function echo(c,x,y,t,alpha=1,spread=0){c.save();c.translate(x,y);c.globalAlpha*=alpha;
    const sway=Math.sin(t*1.4)*2;c.fillStyle='#ac95d524';c.strokeStyle=COLORS.illusion;c.lineWidth=1.25;
    c.beginPath();c.moveTo(-13-spread,1);c.lineTo(-10,-24);c.quadraticCurveTo(0,-35,10,-24);c.lineTo(13+spread,1);c.quadraticCurveTo(0,-5,-13-spread,1);c.fill();c.stroke();
    ring(c,sway,-36,7,9,COLORS.illusionLight,1.2);line(c,[[-6+sway,-44],[sway,-49],[6+sway,-44]],COLORS.illusion,1.3);
    line(c,[[11,-24],[20+sway,-13],[23+sway,-34]],COLORS.illusionLight,1);diamond(c,23+sway,-37,4,COLORS.illusion,Math.PI/4);
    ring(c,0,3,18,5,'#d5bff17a');for(let i=0;i<3;i++){const q=(t*.22+i/3)%1;mote(c,-15+i*14+Math.sin(t+i)*3,1-q*36,1.1,COLORS.illusionLight);}c.restore();
  }
  function ward(c,x,y,t,strength=1,flash=0){c.save();c.translate(x,y);const pulse=.55+.08*Math.sin(t*2),alpha=.35+.5*clamp(strength);c.globalAlpha*=alpha;
    ring(c,0,4,25,8,COLORS.ward,1.2);ring(c,0,-22,27,36,'#83d9ec58',1);
    for(let i=0;i<4;i++){const a=t*.25+i*TAU/4;diamond(c,Math.cos(a)*25,4+Math.sin(a)*8,3.3,COLORS.wardLight,a);}
    // Broken meridians suggest a shell while the actor stays clearly visible.
    ring(c,0,-22,27,36,COLORS.ward,1.2,.1+Math.sin(t*.5)*.1,Math.PI*.78);
    ring(c,0,-22,27,36,COLORS.ward,1.2,Math.PI+.1,Math.PI*1.78);
    c.globalAlpha*=pulse;line(c,[[-22,-36],[-12,-52],[12,-52],[22,-36]],COLORS.wardLight,1);
    if(flash>0){c.globalAlpha*=clamp(flash)*.55;c.fillStyle='#bcf0ff';c.beginPath();c.ellipse(0,-23,28,37,0,0,TAU);c.fill();}
    c.restore();
  }
  function eye(c,x,y,t,alpha=1){c.save();c.translate(x,y-84);c.globalAlpha*=alpha;const open=5+.5*Math.sin(t*2);
    c.strokeStyle=COLORS.eye;c.lineWidth=1.4;c.beginPath();c.moveTo(-13,0);c.quadraticCurveTo(0,-open*2,13,0);c.quadraticCurveTo(0,open*2,-13,0);c.stroke();
    ring(c,0,0,3,4,'#fff4c6',1.4);mote(c,0,0,1.2,COLORS.eye);
    for(let i=0;i<3;i++){const a=-Math.PI/2+(i-1)*.6;line(c,[[Math.cos(a)*12,Math.sin(a)*12],[Math.cos(a)*16,Math.sin(a)*16]],'#eed188a0',1);}c.restore();
  }
  function wolf(c,x,y,t,move=0,flip=1,alpha=1){c.save();c.translate(x,y);c.scale(flip,1);c.globalAlpha*=alpha;
    const step=Math.sin(move*8)*3,bob=Math.sin(t*2)*.7;
    ring(c,0,6,24,7,'#c0b3ee66');
    // Wispy outlines trail a translucent angular wolf, not the ranger's coat.
    for(let i=0;i<3;i++){const q=(t*.25+i/3)%1;c.save();c.globalAlpha*=.28*(1-q);line(c,[[-15-q*17,-8],[-33-q*12,-15-q*9],[-42-q*6,-24-q*12]],COLORS.illusionLight,2-i*.35);c.restore();}
    c.translate(0,bob);for(const [px,s]of[[-16,step],[-8,-step],[11,-step],[19,step]])line(c,[[px,-12],[px-3,-2+s],[px+3,6+s]],'#c1b9efb0',3);
    c.beginPath();c.moveTo(-24,-11);c.lineTo(-20,-25);c.lineTo(-6,-28);c.lineTo(9,-24);c.lineTo(16,-36);c.lineTo(15,-46);c.lineTo(23,-39);c.lineTo(30,-42);c.lineTo(30,-31);c.lineTo(39,-26);c.lineTo(34,-20);c.lineTo(24,-19);c.lineTo(17,-9);c.lineTo(3,-10);c.lineTo(-13,-8);c.closePath();c.fillStyle='#969ed970';c.fill();c.strokeStyle='#dfd5ffc0';c.lineWidth=1.5;c.stroke();
    line(c,[[-21,-17],[-8,-22],[8,-19],[19,-27],[24,-32]],'#f0e6ff88',1);line(c,[[-20,-13],[-32,-21],[-43,-32],[-38,-18],[-24,-7]],'#c2b1e7b0',2);
    mote(c,29,-32,2.1,'#efffff');mote(c,29,-32,3.7,'#b6eaff38');diamond(c,5,-18,4,'#eae1ffa0',Math.PI/4);c.restore();
  }
  function actor(c,v,t){const e=v.entity;if(!(e.wizard_phantasm||e.kind==='spectral_wolf')||e.hp<=0)return false;
    wolf(c,v.x,v.y,t,v.move||0,(e.facing?.[0]||1)<0?-1:1,.9);return true;
  }
  function statuses(c,e,x,y,t){if(e.hp<=0||e.disconnected)return;const v=e.wizard_visual;if(!v)return;
    if(v.ward_hp>0)ward(c,x,y,t,clamp(v.ward_hp/Math.max(1,v.ward_max)));
    if(v.decoy||v.decoy_remaining>0){echo(c,x-28,y+2,t,.48);echo(c,x+28,y+2,t+1,.32);}
    if(v.third_eye||v.third_eye_remaining>0)eye(c,x,y,t,.85);
  }
  function shelter(c,s,t){const r=clamp(s.radius||96,1,512),fade=clamp(s.remaining/1.5);c.save();c.translate(s.x,s.y);c.globalAlpha*=fade;
    c.fillStyle='#b3a5e508';c.beginPath();c.arc(0,0,r,0,TAU);c.fill();ring(c,0,0,r,r,'#c2b4e59a',1.25);
    // Four translucent pillars and suspended arches leave the battlefield open.
    for(let i=0;i<4;i++){const a=Math.PI/4+i*TAU/4,x=Math.cos(a)*r,y=Math.sin(a)*r;
      line(c,[[x-4,y],[x-4,y-36],[x,y-43],[x+4,y-36],[x+4,y]],'#b5a3e960',1.3);diamond(c,x,y-42,4,'#e0d4ffba',t*.2);
      const b=a+TAU/4,xx=Math.cos(b)*r,yy=Math.sin(b)*r;c.strokeStyle='#d8c8ef38';c.lineWidth=1;c.beginPath();c.moveTo(x,y-39);c.quadraticCurveTo((x+xx)*.5,(y+yy)*.5-55,xx,yy-39);c.stroke();}
    for(let i=0;i<8;i++){const a=i*TAU/8;diamond(c,Math.cos(a)*r,Math.sin(a)*r,3.6,'#e4d8ee98',a+Math.PI/2);}
    c.restore();
  }
  function fields(c,players,viewer,t){if(!viewer||!Array.isArray(players))return;for(const p of players){const s=p.wizard_visual?.shelter;if(!s||p.hp<=0||p.disconnected||!(s.remaining>0)||(s.floor||0)!==(viewer.floor||0)||Math.hypot(s.x-viewer.x,s.y-viewer.y)>1600)continue;shelter(c,s,t);}}
  const FEATURES=new Set(['ward_recharge','arcane_ward','projected_ward','decoy','phantasm','illusory_self','self_restore','shelter','third_eye']);
  function draw(c,e,q,t=0){if(e.kind!=='spell')return false;const key=e.wizard_feature||(e.spell_id||'').replace(/^wizard_/,'');if(!FEATURES.has(key))return false;
    q=clamp(q);const duration=Number(e.duration)||.85,age=q*duration,short=clamp(age/.85),fade=Math.sin(Math.PI*short),x=e.target_x??e.x,y=e.target_y??e.y;
    // Live effects come from snapshots, never the original cast coordinates.
    if(key==='shelter'||age>=.85||q>=1)return true;
    c.save();c.globalAlpha*=fade;
    if(['ward_recharge','arcane_ward','projected_ward'].includes(key)){
      if(key==='projected_ward'){const end=clamp(short*3);line(c,[[e.x,e.y-22],[e.x+(x-e.x)*end,e.y-22+(y-e.y)*end]],'#baf4ffb0',2);for(let i=0;i<4;i++){const n=clamp(end-i*.07);diamond(c,e.x+(x-e.x)*n,e.y-22+(y-e.y)*n,3,COLORS.wardLight,short*2);}}
      ward(c,x,y,t,1,e.phase==='absorb'?(1-short)*.55:0);ring(c,x,y+4,25+short*13,8+short*5,COLORS.wardLight,1.3);
      if(e.phase==='absorb')for(let i=0;i<8;i++){const a=i*TAU/8;diamond(c,x+Math.cos(a)*(27+short*13),y-22+Math.sin(a)*(36+short*11),3*(1-short)+1,COLORS.wardLight,a);}
    }else if(key==='third_eye'){eye(c,x,y,t);for(let i=0;i<5;i++){const a=i*TAU/5-short;diamond(c,x+Math.cos(a)*(15+short*25),y-84+Math.sin(a)*(15+short*20),2.8,COLORS.eye,a);}}
    else if(key==='phantasm'){ring(c,x,y+4,28+short*11,10+short*4,COLORS.illusionLight,1.5);wolf(c,x,y-14*(1-short),t,short*2,1,.8);for(let i=0;i<8;i++){const a=i*2.399;diamond(c,x+Math.cos(a)*30,y+Math.sin(a)*12-short*45,2.6,COLORS.illusionLight,a);}}
    else {const shatter=e.phase==='shatter',spread=shatter?short*32:short*17;echo(c,x-15-spread,y,t,.7,shatter?short*8:0);echo(c,x+15+spread,y,t+.7,.7,shatter?short*8:0);
      if(shatter)for(let i=0;i<12;i++){const a=i*2.399;diamond(c,x+Math.cos(a)*(12+short*35),y-24+Math.sin(a)*(12+short*30),4*(1-short)+1,COLORS.illusionLight,a+short);}}
    c.restore();return true;
  }
  const api={draw,statuses,actor,fields};root.BractwoWizardVFX=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
