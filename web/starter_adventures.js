/* UI33. Small starter dungeons: original canvas art, readable telegraphs and
   personal chest state. No full-screen panels and no client-owned rewards. */
(function(root){'use strict';
  const TAU=Math.PI*2;
  const box=(c,x,y,w,h,color)=>{c.fillStyle=color;c.fillRect(Math.round(x),Math.round(y),w,h);};
  const stroke=(c,p,color,w=2)=>{c.strokeStyle=color;c.lineWidth=w;c.beginPath();p.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();};
  const oval=(c,x,y,rx,ry,color)=>{c.fillStyle=color;c.beginPath();c.ellipse(x,y,rx,ry,0,0,TAU);c.fill();};
  function text(c,s,x,y,color='#eeddb5',size=11){c.save();c.font=`600 ${size}px sans-serif`;c.textAlign='center';c.lineWidth=3;c.strokeStyle='#282c2b';c.strokeText(s,x,y);c.fillStyle=color;c.fillText(s,x,y);c.restore();}
  function masonry(c,x,y,w,h){
    box(c,x,y,w,h,'#7c827a');
    for(let j=0;j<h;j+=20)for(let i=0;i<w;i+=38){
      const left=x+i+(j%40?16:0);if(left>=x+w)continue;
      const ww=Math.min(35,x+w-left);
      box(c,left+1,y+j+1,ww,17,j%40?'#a2a38e':'#999d8a');
      box(c,left+2,y+j+2,Math.max(0,ww-2),2,'#c6c4a6');
    }
  }
  function obstacle(c,o,t=0){
    if(!o.starter_adventure)return false;
    const{x,y,w,h}=o;c.save();
    oval(c,x+w/2+5,y+h-2,w*.61,h*.23,'#242a285a');
    if(o.type==='old_starter_tower'){
      box(c,x+8,y+10,w-16,h-12,'#686d64');
      box(c,x+25,y+29,w-50,h-56,'#7c7763');
      for(let i=0;i<7;i++)box(c,x+26,y+34+i*24,w-53,2,'#aca28a');
      masonry(c,x,y,42,h);masonry(c,x+w-42,y,42,h);
      masonry(c,x+40,y+h-49,w-80,49);
      masonry(c,x+40,y,w/2-66,42);masonry(c,x+w/2+25,y,w/2-65,42);
      box(c,x+w/2-24,y+3,48,28,'#2a302c');
      for(let j=0;j<3;j++)box(c,x+w/2-22,y-5+j*9,44,6,'#c7b89a');
      for(const xx of [x-9,x+w-46])for(const yy of [y+7,y+h-63]){
        masonry(c,xx,yy,55,62);box(c,xx-3,yy-6,61,10,'#c4c1a3');
        for(let i=0;i<3;i++)box(c,xx+i*21-3,yy-20,16,17,'#c1bfa3');
        box(c,xx+21,yy+21,10,25,'#414b47');
      }
      stroke(c,[[x+46,y+73],[x+65,y+94],[x+51,y+123]],'#535d55',3);
      box(c,x+w-36,y+96,20,46,'#694b42');box(c,x+w-34,y+97,16,24,'#b6845b');
      text(c,'STARA WIEŻA',x+w/2,y+h+23,'#efe2bd',12);
    }else if(o.type==='dawn_mausoleum'){
      masonry(c,x,y-37,w,h+37);box(c,x-9,y-49,w+18,13,'#d5c8a8');
      box(c,x+6,y-65,w-12,16,'#aaa993');
      for(const xx of [x+7,x+w-21]){box(c,xx,y-32,14,h+31,'#b4b6a0');box(c,xx+2,y-28,3,h+24,'#e0d6b7');}
      box(c,x+w/2-24,y-13,48,h+13,'#303533');
      oval(c,x+w/2,y-12,24,15,'#303533');
      text(c,'☼',x+w/2,y-43,'#d7bd74',19);
    }else if(o.type==='dawn_sarcophagus'){
      box(c,x,y+7,w,h-7,'#555e5e');box(c,x-2,y,w+4,h-10,'#a5a597');box(c,x+5,y+4,w-10,h-19,'#c2beaa');
      oval(c,x+w/2,y+21,8,8,'#848d83');stroke(c,[[x+w/2,y+30],[x+w/2,y+h-23]],'#858b80',12);
      stroke(c,[[x+15,y+40],[x+w-15,y+40]],'#81877b',6);
      stroke(c,[[x+w-16,y+7],[x+w-23,y+18],[x+w-13,y+29]],'#707c73',2);
    }else if(o.type==='dawn_brazier'){
      box(c,x,y+7,w,h-7,'#6a6860');box(c,x-4,y+3,w+8,7,'#b7a583');
      const cx=x+w/2;oval(c,cx,y+3,21,16,'#e4b45b22');
      box(c,cx-6,y-9,12,16,'#d78d43');box(c,cx-3,y-15+Math.sin(t*5)*2,7,18,'#ffd591');
    }else if(o.type==='tower_cover'){
      masonry(c,x,y-21,w,h+21);box(c,x-5,y-26,w+10,12,'#c9c5a6');
      stroke(c,[[x+12,y-10],[x+18,y+7],[x+8,y+30]],'#626e64',3);
    }else if(o.type==='tower_crates'){
      box(c,x,y,w,h,'#725842');box(c,x+4,y+3,w-8,h-9,'#a08050');
      stroke(c,[[x+8,y+7],[x+w-8,y+h-17],[x+w-8,y+7],[x+8,y+h-17]],'#cab080',5);
      box(c,x+1,y+h-10,w-2,6,'#4d5045');
    }else{c.restore();return false;}
    c.restore();return true;
  }
  function actor(c,v,spec,t){
    const kind=spec.starter_visual;if(!kind)return false;
    const{x,y,entity:e}=v,z=spec.size||1,step=Math.sin((v.move||0)*8)*2.5;
    c.save();c.translate(x,y);c.scale((e.facing?.[0]<0?-1:1)*z,z);
    oval(c,0,5,22,8,'#27302c66');
    const bone=kind==='headless'||kind==='crypt_skeleton';
    if(bone){
      if(kind==='headless'){
        box(c,-15,-31,28,27,'#725d66');box(c,-15,-26,7,30,'#9c7a7a');box(c,9,-24,6,28,'#72555e');
        box(c,-16,-33,31,8,'#8a9185');box(c,-13,-35,25,3,'#c3bca1');
      }
      stroke(c,[[-8,-9],[-10,-1+step],[-11,9+step]],'#b8b59e',5);
      stroke(c,[[7,-9],[9,-1-step],[11,9-step]],'#d8ceb1',5);
      box(c,-15,7+step,10,4,'#ded2ad');box(c,7,7-step,10,4,'#bebba2');
      box(c,-10,-30,21,19,'#756f60');
      for(let i=0;i<4;i++)box(c,-10,-29+i*5,21,3,'#ddd2b1');
      box(c,-2,-34,4,25,'#e5d9b8');box(c,-10,-9,22,4,'#b7b8a5');
      stroke(c,[[-13,-29],[-20,-16],[-17,-6]],'#c5bea0',4);
      stroke(c,[[14,-29],[23,-18],[22,-7]],'#d8d1b6',4);
      if(kind!=='headless'){
        box(c,-9,-49,20,18,'#dad3b7');box(c,-6,-44,5,5,'#4b514a');box(c,4,-44,4,5,'#4b514a');box(c,-5,-34,13,4,'#b7b8a4');
      }else{
        // Intentionally no skull: exposed dry neck bone, no gore.
        box(c,-2,-40,5,7,'#d9cba4');
      }
      stroke(c,[[24,-4],[30,-37]],'#76614a',4);box(c,23,-43,18,11,'#aeb7ae');box(c,24,-45,17,3,'#e1dfc0');
    }else{
      box(c,-12,-36,26,33,'#5f705e');box(c,-14,-29,6,30,'#778879');
      box(c,-9,-8,8,19+step,'#5f5545');box(c,5,-8,8,19-step,'#514b40');
      box(c,-12,7+step,12,5,'#3d443e');box(c,4,7-step,13,5,'#3d443e');
      box(c,-12,-31,24,25,'#b09a70');box(c,-10,-28,20,10,'#92734e');
      box(c,-12,-11,25,4,'#655544');box(c,-2,-12,5,6,'#d5b870');
      box(c,-10,-53,23,21,'#53685a');box(c,-5,-48,14,15,'#d3b18c');
      box(c,-12,-56,24,8,'#718574');box(c,-10,-48,6,18,'#718574');
      box(c,4,-44,3,3,'#373f34');box(c,3,-36,8,3,'#8b6952');
      if(kind==='tower_archer'){
        box(c,-20,-44,7,25,'#674e3c');for(let i=0;i<3;i++)stroke(c,[[-19+i*3,-40],[-21+i*3,-56]],'#d8c698',2);
        stroke(c,[[-12,-26],[-21,-18],[-13,-9]],'#c4ac80',5);
        stroke(c,[[12,-28],[23,-26],[27,-22]],'#d2b38b',5);
        stroke(c,[[27,-48],[37,-36],[39,-19],[28,-3]],'#cfb47d',4);
        stroke(c,[[27,-48],[24,-23],[28,-3]],'#e8dfb9',1);
        stroke(c,[[8,-23],[45,-23]],'#e7d4a3',2);
      }else{stroke(c,[[15,-24],[21,-13],[22,-4]],'#c5ab85',4);stroke(c,[[23,-7],[32,-34]],'#cbd1bc',4);}
    }
    c.restore();
    const yy=y-(kind==='headless'?65:76)*z,w=spec.boss?62:36;
    text(c,e.name||spec.name,x,yy,spec.boss?'#f3d491':'#e4dbc1',spec.boss?11:9);
    box(c,x-w/2,yy+7,w,5,'#38443b');box(c,x-w/2+1,yy+8,(w-2)*Math.max(0,e.hp/e.max_hp),3,'#d77f5d');
    return true;
  }
  function chestState(site,me,snapshot){
    if(me?.starter_adventures?.claimed?.includes(site.id))return 'claimed';
    if(!me?.starter_adventures?.defeated?.includes(site.boss_kind))return 'guarded';
    if((snapshot?.enemies||[]).some(e=>e.kind===site.boss_kind&&e.alive!==false&&e.hp>0&&e.floor===site.floor))return 'guarded';
    return 'ready';
  }
  function chest(c,site,me,snapshot,t){
    if(site.action!=='starter_treasure')return false;
    const{x,y}=site,state=chestState(site,me,snapshot),opened=state==='claimed';c.save();
    oval(c,x,y+10,33,15,'#27312d66');
    if(state==='ready')oval(c,x,y+6,36+Math.sin(t*2)*3,21,'#e6ca702e');
    box(c,x-26,y-16,52,34,'#785239');box(c,x-23,y-12,46,26,opened?'#514d3e':'#ad8349');
    box(c,x-26,y-(opened?45:31),52,opened?21:18,opened?'#805e3f':'#c49a59');
    if(opened)box(c,x-20,y-12,40,9,'#2c3832');
    for(const dx of [-19,15])box(c,x+dx,y-(opened?44:30),5,opened?20:47,'#d6bd79');
    if(!opened){box(c,x-5,y-8,10,12,state==='guarded'?'#879a93':'#edcf7d');box(c,x-1,y-5,3,5,'#4c5142');}
    text(c,site.name,x,y-64,opened?'#b5bbaa':'#f1d591',10);
    if(me&&Math.hypot(me.x-x,me.y-y)<120){
      text(c,state==='claimed'?'Nagroda odebrana':state==='guarded'?'Pokonaj strażnika':'[E] Otwórz skarb',x,y+36,opened?'#bdc4b3':'#f0df9d',10);
    }
    c.restore();return true;
  }
  function effect(c,e,q){
    if(!['starter_warning','starter_strike'].includes(e.kind))return false;
    const warning=e.kind==='starter_warning',x=e.x,y=e.y,tx=e.target_x??x,ty=e.target_y??y;c.save();
    c.strokeStyle=warning?'#edd097':'#fff0c6';c.fillStyle=warning?'#de7b4d2c':'#f0d4973d';
    c.lineWidth=warning?2:5;c.globalAlpha=warning?1:1-q;
    if(e.shape==='line'){
      const a=Math.atan2(ty-y,tx-x),dx=-Math.sin(a)*(e.width||22),dy=Math.cos(a)*(e.width||22);
      c.beginPath();c.moveTo(x+dx,y+dy);c.lineTo(tx+dx,ty+dy);c.lineTo(tx-dx,ty-dy);c.lineTo(x-dx,y-dy);c.closePath();c.fill();
      if(warning)c.setLineDash([7,5]);c.stroke();c.setLineDash([]);
      stroke(c,[[x,y],[warning?x+(tx-x)*q:tx,warning?y+(ty-y)*q:ty]],warning?'#f7dfbb':'#fff4d5',warning?2:4);
      if(warning)text(c,'STRZAŁ MIERZONY',x,y-71,'#f4d38d',10);
    }else{
      c.beginPath();c.arc(x,y,e.radius||110,0,TAU);c.fill();c.setLineDash(warning?[7,5]:[]);c.stroke();c.setLineDash([]);
      c.beginPath();c.arc(x,y,(e.radius||110)*(warning?q:1),-Math.PI/2,-Math.PI/2+TAU*q);c.stroke();
      if(warning)text(c,'ŚLEPY ZAMACH',x,y-72,'#f4d38d',10);
    }
    c.restore();return true;
  }
  function ground(c,world,floor,view){
    if(!floor)return;
    for(const area of [...(world.dungeons||[]),...(world.elevations||[])]){
      if(!area.starter_adventure||area.floor!==floor||area.x>view.right||area.x+area.w<view.left||area.y>view.bottom||area.y+area.h<view.top)continue;
      c.save();
      if(area.theme==='old_tower'){
        const r=area.rooms[0];c.strokeStyle='#d0c3a0';c.lineWidth=7;c.strokeRect(r.x+4,r.y+4,r.w-8,r.h-8);
        for(let xx=r.x+15;xx<r.x+r.w-20;xx+=43){box(c,xx,r.y+3,24,13,'#a2a590');box(c,xx,r.y+r.h-17,24,14,'#a2a590');}
        // Rugs break up the stone floor without hiding either staircase.
        if(floor<3){box(c,705,1870,110,150,'#87726166');c.strokeStyle='#c3aa7855';c.lineWidth=3;c.strokeRect(711,1876,98,138);}
        else{oval(c,748,1887,59,39,'#7a796733');stroke(c,[[718,1885],[778,1885],[748,1860],[748,1915]],'#b3aa8c88',3);}
      }else{
        for(const [xx,yy] of [[2570,445],[3025,475],[3100,930]]){
          oval(c,xx,yy,58,40,'#8e927a55');stroke(c,[[xx-32,yy],[xx+32,yy],[xx,yy-27],[xx,yy+27]],'#c0b59477',3);
        }
      }
      c.restore();
    }
  }
  root.BractwoStarterAdventures={obstacle,actor,chest,chestState,effect,ground};
  if(typeof module!=='undefined')module.exports=root.BractwoStarterAdventures;
})(globalThis);
