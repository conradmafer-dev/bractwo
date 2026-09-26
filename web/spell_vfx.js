/* Original, resolution-independent spell effects. Server areas are drawn verbatim. */
(function(root){
  'use strict';
  const TAU=Math.PI*2;
  function polygonContains(p,x,y){let sign=0;for(let i=0;i<p.length;i++){const a=p[i],b=p[(i+1)%p.length],c=(b[0]-a[0])*(y-a[1])-(b[1]-a[1])*(x-a[0]);if(Math.abs(c)<1e-6)continue;const s=Math.sign(c);if(sign&&sign!==s)return false;sign=s;}return true;}
  function areaContains(area,x,y){return (area.circles||[]).some(([cx,cy,r])=>(cx-x)**2+(cy-y)**2<=r*r+1e-6)||(area.polygons||[]).some(p=>polygonContains(p,x,y));}
  function missilePoint(a,b,t,index,total=3){const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy)||1;const bend=(total<=3?[-96,32,105][index%3]:-150+300*index/Math.max(1,total-1))*Math.min(1,len/130),u=1-t;return [u*u*a[0]+2*u*t*((a[0]+b[0])/2-dy/len*bend)+t*t*b[0],u*u*a[1]+2*u*t*((a[1]+b[1])/2+dx/len*bend-18)+t*t*b[1]];}
  function path(ctx,area){ctx.beginPath();for(const [x,y,r]of area.circles||[]){ctx.moveTo(x+r,y);ctx.arc(x,y,r,0,TAU);}for(const p of area.polygons||[]){if(!p.length)continue;ctx.moveTo(...p[0]);for(const xy of p.slice(1))ctx.lineTo(...xy);ctx.closePath();}}
  function line(ctx,points,color,width){if(points.length<2)return;ctx.strokeStyle=color;ctx.lineWidth=width;ctx.lineCap='round';ctx.lineJoin='round';ctx.beginPath();ctx.moveTo(...points[0]);for(const p of points.slice(1))ctx.lineTo(...p);ctx.stroke();}
  function orb(ctx,x,y,r,colors,alpha=1){ctx.save();ctx.globalAlpha*=alpha;const g=ctx.createRadialGradient(x,y,0,x,y,Math.max(1,r));g.addColorStop(0,colors[2]);g.addColorStop(.17,colors[1]);g.addColorStop(.4,colors[0]+'cc');g.addColorStop(1,colors[0]+'00');ctx.fillStyle=g;ctx.beginPath();ctx.arc(x,y,r,0,TAU);ctx.fill();ctx.restore();}
  function burst(ctx,x,y,colors,q,scale=1,ice=false){if(q<0||q>1)return;ctx.save();ctx.globalAlpha*=1-q;orb(ctx,x,y,28*scale,colors,.7);for(let i=0;i<14;i++){const a=i*2.3999,d=(8+28*q)*scale;const xx=x+Math.cos(a)*d,yy=y+Math.sin(a)*d;line(ctx,[[xx,yy],[xx+Math.cos(a)*7*scale,yy+Math.sin(a)*7*scale]],i%2?colors[2]:colors[1],ice?2:3);}ctx.restore();}
  function beam(ctx,a,b,colors,q,icy=false,seed=0){ctx.save();ctx.globalAlpha*=Math.sin(Math.PI*Math.min(.98,q))*.95;const points=[];for(let i=0;i<=20;i++){const t=i/20,wiggle=(i===0||i===20)?0:Math.sin(i*4.1+q*21+seed)*3;points.push([a[0]+(b[0]-a[0])*t+wiggle,a[1]+(b[1]-a[1])*t-wiggle]);}line(ctx,points,colors[0]+'40',19);line(ctx,points,colors[0]+'a0',10);line(ctx,points,colors[1],5);line(ctx,[a,b],colors[2],1.8);orb(ctx,...a,17,colors);burst(ctx,...b,colors,((q*2)%1),1.15,icy);if(icy){for(let i=0;i<7;i++){const t=(q*.8+i/7)%1,x=a[0]+(b[0]-a[0])*t,y=a[1]+(b[1]-a[1])*t;line(ctx,[[x-3,y-9],[x+2,y],[x+7,y-6]],colors[2]+'aa',1.5);}}ctx.restore();}
  function particlesInArea(ctx,e,q,colors,now){const area=e.area,b=area.bounds;if(!b)return;const count=e.persistent?42:58;
    ctx.save();path(ctx,area);ctx.clip();
    for(let i=0;i<count;i++){const rx=((Math.sin(i*127.1+3)*43758.5453)%1+1)%1,ry=((Math.sin(i*311.7+7)*93758.2153)%1+1)%1;const x=b[0]+rx*(b[2]-b[0]),y=b[1]+ry*(b[3]-b[1]);if(!areaContains(area,x,y))continue;const v=(q*1.3+i*.071)%1;ctx.globalAlpha=e.persistent?.5+.25*Math.sin(now*2+i):Math.sin(Math.PI*q)*.8;
      if(['entangle','spike_growth','plant_growth'].includes(e.spell_id)){line(ctx,[[x-7,y+4],[x,y-15-6*Math.sin(now+i)],[x+3,y]],colors[1],2.5);line(ctx,[[x,y-7],[x+8,y-12]],colors[0],2);}
      else if(e.visual.theme==='cold'){line(ctx,[[x-3,y-8],[x,y+7],[x+5,y-2]],colors[2],2);}
      else if(e.visual.theme==='fire'){orb(ctx,x,y-v*9,9+5*Math.sin(i),colors,.9);}
      else{ctx.fillStyle=colors[i%3];ctx.fillRect(x,y-v*10,3,6);}
    }ctx.restore();
  }
  function drawArea(ctx,e,q,colors,now){const area=e.area;if(!area)return;ctx.save();const persistent=!!e.persistent;
    ctx.globalAlpha=persistent?.18+.035*Math.sin(now*2):.24*Math.sin(Math.PI*Math.min(.98,q));path(ctx,area);ctx.fillStyle=colors[0];ctx.fill('nonzero');ctx.globalAlpha=persistent?.68:Math.sin(Math.PI*Math.min(.98,q))*.95;ctx.strokeStyle=colors[1];ctx.lineWidth=2;ctx.stroke();
    ctx.globalAlpha=1;
    if(area.shape==='line'){const [ox,oy]=area.origin,[ux,uy]=area.direction,len=area.length;ctx.save();path(ctx,area);ctx.clip();beam(ctx,[ox,oy],[ox+ux*len,oy+uy*len],colors,q);ctx.restore();}
    else if(area.shape==='cone'){const [ox,oy]=area.origin,[ux,uy]=area.direction;ctx.save();path(ctx,area);ctx.clip();for(let i=0;i<13;i++){const spread=(i/12-.5)*area.length,end=[ox+ux*area.length-uy*spread,oy+uy*area.length+ux*spread];const t=Math.min(1,q*1.9);line(ctx,[[ox,oy],[ox+(end[0]-ox)*t,oy+(end[1]-oy)*t]],colors[i%2]+(i%2?'90':'50'),5+i%3);}ctx.restore();particlesInArea(ctx,e,q,colors,now);}
    else if(area.shape==='chain'){}
    else {particlesInArea(ctx,e,q,colors,now);for(const[x,y,r]of area.circles||[]){
      if(e.spell_id==='moonbeam'){ctx.save();const g=ctx.createLinearGradient(x,y-150,x,y);g.addColorStop(0,colors[0]+'00');g.addColorStop(.65,colors[1]+'28');g.addColorStop(1,colors[2]+'80');ctx.fillStyle=g;ctx.fillRect(x-r,y-150,r*2,150);orb(ctx,x,y,r*1.15,colors,.5);ctx.restore();}
      else if(e.spell_id==='meteor_swarm'){const t=Math.min(1,q/.58);line(ctx,[[x-120*(1-t),y-190*(1-t)],[x-80*(1-t),y-120*(1-t)]],colors[0]+'b0',15);orb(ctx,x-80*(1-t),y-120*(1-t),22,colors);if(q>.5){ctx.globalAlpha=1-q;ctx.strokeStyle=colors[1];ctx.lineWidth=6;ctx.beginPath();ctx.arc(x,y,r*Math.min(1,(q-.5)*2.5),0,TAU);ctx.stroke();}}
      else if(!persistent){ctx.globalAlpha=(1-q)*.75;ctx.strokeStyle=colors[2];ctx.lineWidth=3;ctx.beginPath();ctx.arc(x,y,r*Math.min(1,q*1.7),0,TAU);ctx.stroke();orb(ctx,x,y,r*.65,colors,(1-q)*.38);}
    }}ctx.restore();
  }
  // Live status overlays are driven by the server; no detached effect timer.
  function mark(ctx,x,y,now,scale=1,alpha=1){ctx.save();ctx.globalAlpha*=alpha;const cy=y-49*scale,r=10*scale;ctx.strokeStyle='#eec768';ctx.lineWidth=2;ctx.beginPath();ctx.arc(x,cy,r,0,TAU);ctx.stroke();for(let i=0;i<4;i++){const a=i*TAU/4;line(ctx,[[x+Math.cos(a)*r*.65,cy+Math.sin(a)*r*.65],[x+Math.cos(a)*r*1.45,cy+Math.sin(a)*r*1.45]],'#fff0ab',2);}ctx.globalAlpha*=.35+.1*Math.sin(now*3);ctx.beginPath();ctx.ellipse(x,y+1,20*scale,8*scale,0,0,TAU);ctx.stroke();ctx.restore();}
  function vines(ctx,x,y,now,scale=1,alpha=1){ctx.save();ctx.globalAlpha*=alpha;for(let side=-1;side<=1;side+=2){const points=[];for(let j=0;j<=14;j++){const t=j/14;points.push([x+side*(13+Math.sin(t*9+now*1.5)*5)*scale,y-t*37*scale]);}line(ctx,points,'#173f2b',6*scale);line(ctx,points,'#66b857',3*scale);for(let j=3;j<14;j+=4){const a=points[j],dx=side*9*scale;ctx.fillStyle='#c2ea89';ctx.beginPath();ctx.moveTo(...a);ctx.quadraticCurveTo(a[0]+dx,a[1]-12*scale,a[0]+dx,a[1]-3*scale);ctx.quadraticCurveTo(a[0]+dx*.5,a[1]+2*scale,...a);ctx.fill();}}ctx.restore();}
  function drawStatuses(ctx,statuses,x,y,now=0,scale=1){if(!Array.isArray(statuses))return;scale=Math.max(.7,Math.min(2.2,Number(scale)||1));let marked=false,ensnared=false;for(const s of statuses){if(s.id==='concentration'||s.id==='ensnaring_ready')continue;if(s.spell_id==='hunters_mark'&&!marked){mark(ctx,x,y,now,scale);marked=true;}if(s.spell_id==='ensnaring_strike'&&s.id==='restrained'&&!ensnared){vines(ctx,x,y,now,scale);ensnared=true;}}}
  function draw(ctx,e,q,now=0){if(e.kind!=='spell')return false;const colors=e.visual?.colors||['#648bdb','#aaceff','#ffffff'],style=e.visual?.style||'projectile',a=[e.x,e.y-20],b=[e.target_x??e.x,(e.target_y??e.y)-20];ctx.save();
    if(e.area&&style!=='chain'){drawArea(ctx,e,q,colors,now);}
    else if(style==='missiles'){
      const progress=Math.min(1,q/.75),count=Math.max(1,Math.min(11,e.shots||3));for(let i=0;i<count;i++){const pts=[];for(let k=0;k<12;k++){const t=Math.max(0,progress-(11-k)*.013);pts.push(missilePoint(a,b,t,i,count));}line(ctx,pts,colors[0]+'60',10);line(ctx,pts,colors[1],3.4);const pos=missilePoint(a,b,progress,i,count);if(progress<1){orb(ctx,...pos,15,colors);ctx.fillStyle=colors[2];ctx.beginPath();ctx.arc(...pos,3,0,TAU);ctx.fill();}else burst(ctx,...b,colors,(q-.75)/.25,1.2);}
    }else if(style==='vines'){vines(ctx,b[0],b[1]+20,now,1,Math.sin(Math.PI*q));burst(ctx,b[0],b[1]+20,colors,q,.8);}
    else if(style==='mark'){mark(ctx,b[0],b[1]+20,now,1,Math.sin(Math.PI*q));}
    else if(style==='beam'){for(let i=0;i<(e.shots||1);i++)beam(ctx,[a[0],a[1]+(i-((e.shots||1)-1)/2)*7],b,colors,q,e.spell_id==='ray_of_frost',i);}
    else if(style==='chain'){const main=(e.targets||[])[0];if(main){const end=[main.x,main.y-20];beam(ctx,a,end,colors,q);for(const target of (e.targets||[]).slice(1))beam(ctx,end,[target.x,target.y-20],colors,q,false,2);}}
    else if(style==='projectile'){const t=Math.min(1,q/.7),pos=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];line(ctx,[[a[0]+(b[0]-a[0])*Math.max(0,t-.2),a[1]+(b[1]-a[1])*Math.max(0,t-.2)],pos],colors[0]+'90',7);if(t<1)orb(ctx,...pos,18,colors);else burst(ctx,...b,colors,(q-.7)/.3,1);}
    else {const c=[b[0],b[1]+20],fade=Math.sin(Math.PI*q);ctx.globalAlpha=fade;ctx.strokeStyle=colors[1];ctx.lineWidth=2.5;ctx.beginPath();ctx.ellipse(...c,30+22*q,18+14*q,0,0,TAU);ctx.stroke();orb(ctx,c[0],c[1]-25,46,colors,.4);
      if(e.spell_id==='shield'||e.spell_id==='mage_armor'){line(ctx,[[c[0]-24,c[1]-48],[c[0],c[1]-61],[c[0]+24,c[1]-48],[c[0]+19,c[1]-15],[c[0],c[1]],[c[0]-19,c[1]-15],[c[0]-24,c[1]-48]],colors[2],3);}
      else if(style==='heal'){for(let i=0;i<7;i++){const x=c[0]+Math.cos(i*2.4)*24,y=c[1]-20-Math.sin(i*2.4)*16-q*45;line(ctx,[[x-4,y],[x+4,y]],colors[2],2);line(ctx,[[x,y-4],[x,y+4]],colors[2],2);}}
      else for(let i=0;i<12;i++){const t=i/12*TAU+q*2,x=c[0]+Math.cos(t)*(25+q*12),y=c[1]-20+Math.sin(t)*20-q*28;line(ctx,[[x,y],[x-3,y+9]],colors[i%3],2.5);}
      if(style==='teleport'){orb(ctx,...a,45,colors,fade);orb(ctx,...b,45,colors,fade);}
    }ctx.restore();return true;
  }
  const api={draw,drawStatuses,areaContains,missilePoint};if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.BractwoSpellVFX=api;
})(typeof globalThis!=='undefined'?globalThis:this);
