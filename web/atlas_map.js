/* Shared map geometry and a persistent atlas camera. Opening a book does not pause play. */
(function(root){'use strict';
  const WATER='#559ebc',BRIDGE='#e3c388';
  const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
  class View {
    constructor(width,height){this.width=Math.max(1,width);this.height=Math.max(1,height);this.x=width/2;this.y=height/2;this.zoom=1;this.aspect=700/505;}
    bounds(){const w=Math.max(this.width,this.height*this.aspect)/this.zoom,h=w/this.aspect;return {x:this.x-w/2,y:this.y-h/2,w,h};}
    limit(){const b=this.bounds();this.x=b.w>=this.width?this.width/2:clamp(this.x,b.w/2,this.width-b.w/2);this.y=b.h>=this.height?this.height/2:clamp(this.y,b.h/2,this.height-b.h/2);}
    point(u,v){const b=this.bounds();return {x:b.x+u*b.w,y:b.y+v*b.h,floor:0};}
    scale(factor,u=.5,v=.5){const p=this.point(u,v);this.zoom=clamp(this.zoom*factor,1,64);const b=this.bounds();this.x=p.x+(.5-u)*b.w;this.y=p.y+(.5-v)*b.h;this.limit();return this.zoom;}
    pan(dx,dy){const b=this.bounds();this.x-=dx*b.w;this.y-=dy*b.h;this.limit();}
    all(){this.zoom=1;this.x=this.width/2;this.y=this.height/2;}
    nearby(p){this.zoom=32;this.x=Number.isFinite(p?.x)?p.x:this.width/2;this.y=Number.isFinite(p?.y)?p.y:this.height/2;this.limit();}
  }
  function waterways(w){
    const out=[];const r=w.river;
    if(r&&r.w>0&&r.h>0)out.push({kind:'water',shape:'rect',x:r.x,y:r.y||0,w:r.w,h:r.h});
    for(const r of w.waterways||[])if(r.a&&r.b)out.push({kind:'water',shape:'line',a:r.a,b:r.b,width:r.width||24});
    // Bridges must be drawn AFTER every waterway, also at crossings.
    if(r&&r.bridge_h>0)out.push({kind:'bridge',shape:'rect',x:r.x,y:r.bridge_y,w:r.w,h:r.bridge_h});
    for(const b of w.bridges||[])if(b.a&&b.b)out.push({kind:'bridge',shape:'line',a:b.a,b:b.b,width:b.width||64});
    return out;
  }
  function drawWater(g,w,b,width,height){
    const sx=width/b.w,sy=height/b.h;
    for(const p of waterways(w)){
      // The continent has >1,000 water segments; issue canvas commands only
      // for the current local view. Keep the original bridge in this same pass.
      const pad=p.shape==='line'?(p.width||0)/2:0;
      const x=p.shape==='rect'?p.x:Math.min(p.a[0],p.b[0])-pad;
      const y=p.shape==='rect'?p.y:Math.min(p.a[1],p.b[1])-pad;
      const right=p.shape==='rect'?p.x+p.w:Math.max(p.a[0],p.b[0])+pad;
      const bottom=p.shape==='rect'?p.y+p.h:Math.max(p.a[1],p.b[1])+pad;
      if(right<b.x||bottom<b.y||x>b.x+b.w||y>b.y+b.h)continue;
      g.fillStyle=g.strokeStyle=p.kind==='bridge'?BRIDGE:WATER;
      if(p.shape==='rect')g.fillRect((p.x-b.x)*sx,(p.y-b.y)*sy,Math.max(1,p.w*sx),Math.max(1,p.h*sy));
      else {g.lineWidth=Math.max(p.kind==='bridge'?2:1.5,p.width*Math.min(sx,sy));g.beginPath();g.moveTo((p.a[0]-b.x)*sx,(p.a[1]-b.y)*sy);g.lineTo((p.b[0]-b.x)*sx,(p.b[1]-b.y)*sy);g.stroke();}
    }
  }
  function drawTerrain(g,w,b,width,height,floor=0){
    const sx=width/b.w,sy=height/b.h;
    const point=(x,y)=>[(x-b.x)*sx,(y-b.y)*sy];
    g.fillStyle=floor?'#252831':w.landmasses?.length?'#244f64':'#446446';g.fillRect(0,0,width,height);
    if(floor){
      for(const d of [...(w.dungeons||[]),...(w.elevations||[])])if(d.floor===floor)for(const r of d.rooms||[]){g.fillStyle='#a1937a';g.fillRect((r.x-b.x)*sx,(r.y-b.y)*sy,r.w*sx,r.h*sy);}
    } else {
      if(w.landmasses?.length){g.save();root.BractwoWorldGeometry.outline(g,w,b,width,height);g.clip();g.fillStyle='#446446';g.fillRect(0,0,width,height);}
      for(const r of w.regions||[]){g.fillStyle=r.color;g.fillRect((r.x-b.x)*sx,(r.y-b.y)*sy,r.w*sx,r.h*sy);g.strokeStyle='#eeeecc25';g.lineWidth=1;g.strokeRect((r.x-b.x)*sx,(r.y-b.y)*sy,r.w*sx,r.h*sy);}
      g.strokeStyle='#d5bd85';g.lineWidth=Math.max(1,64*sx);
      for(const road of w.roads||[]){g.beginPath();road.forEach(([x,y],i)=>{const p=point(x,y);if(i)g.lineTo(...p);else g.moveTo(...p);});g.stroke();}
      drawWater(g,w,b,width,height);
      if(b.w<16000){
        for(const o of w.obstacles||[])if(!(o.floor||0)&&(o.type==='house'||o.kind==='house')){g.fillStyle='#ab8a5b';g.fillRect((o.x-b.x)*sx,(o.y-b.y)*sy,o.w*sx,o.h*sy);}
      }
      if(w.landmasses?.length){
        g.restore();root.BractwoWorldGeometry.outline(g,w,b,width,height);g.strokeStyle='#bfc39a';g.lineWidth=1.5;g.stroke();
        g.save();g.setLineDash([4,5]);g.strokeStyle='#a4d3df88';g.lineWidth=1;
        const drawn=new Set();
        for(const route of w.sea_routes||[]){const pair=[route.from_id,route.to_id].sort().join('|');if(drawn.has(pair))continue;drawn.add(pair);
          const from=(w.ports||[]).find(p=>p.id===route.from_id),to=(w.ports||[]).find(p=>p.id===route.to_id);if(!from||!to)continue;
          g.beginPath();g.moveTo(...point(from.x,from.y));g.lineTo(...point(to.x,to.y));g.stroke();
        }
        g.restore();
        for(const port of w.ports||[]){const [x,y]=point(port.x,port.y);g.fillStyle='#bde8ed';g.fillRect(x-2,y-2,4,4);if(!port.city_id&&b.w<22000){g.font='10px system-ui';g.textAlign='center';g.fillText(port.name,x,y-7);}}
      }
      for(const r of w.regions||[]){
        if(r.w*sx<85)continue;
        if(w.landmasses?.length&&!root.BractwoWorldGeometry.landAt(w,r.x+r.w/2,r.y+r.h/2))continue;
        const x=clamp((r.x+r.w/2-b.x)*sx,(r.x-b.x)*sx+55,(r.x+r.w-b.x)*sx-55),y=(r.y+r.h/2-b.y)*sy;
        if(x<0||x>width||y<0||y>height)continue;
        g.font='12px system-ui';g.textAlign='center';g.fillStyle='#f5eccd';g.strokeStyle='#22392d';g.lineWidth=3;g.strokeText(r.name,x,y);g.fillText(r.name,x,y);
        g.font='10px system-ui';g.fillText(`${r.min_level}–${r.max_level}`,x,y+15);
      }
    }
    for(const s of w.stairs||[])if((s.floor||0)===floor){const [x,y]=point(s.x,s.y);g.fillStyle='#ddb8e9';g.fillRect(x-2,y-2,4,4);}
    if(!floor)for(const c of w.cities||[]){
      const [x,y]=point(c.x,c.y);if(x<-20||y<-20||x>width+20||y>height+20)continue;
      g.fillStyle='#ffd989';g.beginPath();g.arc(x,y,4,0,Math.PI*2);g.fill();g.fillStyle='#fff1c8';g.font='bold 11px system-ui';g.textAlign=x<70?'left':'center';g.fillText(c.name,Math.max(6,x),Math.max(14,y-9));
    }
  }
  function mount(parent,options){
    const w=options.world,view=options.view||new View(w.width,w.height);
    const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text)e.textContent=text;if(cls)e.className=cls;return e;};
    const box=node('section',null,'atlas-map');parent.append(box);
    const tools=node('div',null,'atlas-tools');box.append(tools);
    let player=options.player,goal=options.goal,choosing=false,drag=null,suppressClick=false;
    function button(text,title,fn){const el=node('button',text);el.type='button';el.title=title;el.setAttribute('aria-label',title);el.onclick=fn;tools.append(el);return el;}
    const less=button('−','Oddal mapę',()=>{view.scale(.5);draw();});
    const more=button('+','Przybliż mapę',()=>{view.scale(2);draw();});
    button('Cały świat','Pokaż cały świat',()=>{view.all();draw();});
    button('Moja okolica','Pokaż okolicę postaci',()=>{view.nearby(player);draw();});
    const target=button('Wyznacz cel','Kliknij mapę, aby wyznaczyć cel nawigacji',()=>{choosing=!choosing;draw();});
    const info=node('span',null,'atlas-zoom');tools.append(info);
    const canvas=node('canvas',null,'atlas-canvas');canvas.id='atlasCanvas';canvas.width=700;canvas.height=505;canvas.setAttribute('aria-label','Atlas: kliknij, aby przybliżyć. Prawy przycisk oddala.');box.append(canvas);
    const help=node('p','Klik: przybliż · prawy klik: oddal · przeciągnij: przesuń. Na telefonie użyj także + i −.','atlas-help');box.append(help);
    const base=document.createElement('canvas');base.width=700;base.height=505;let baseKey='';
    const uv=e=>{const r=canvas.getBoundingClientRect();return {u:clamp((e.clientX-r.left)/r.width,0,1),v:clamp((e.clientY-r.top)/r.height,0,1)};};
    function draw(){
      const floor=Number(player?.floor)||0,b=view.bounds(),key=JSON.stringify([b,floor]);
      if(key!==baseKey){baseKey=key;drawTerrain(base.getContext('2d'),w,b,700,505,floor);}
      const g=canvas.getContext('2d');g.drawImage(base,0,0);
      function mark(p,color,r){if(!p||(p.floor||0)!==floor)return;const x=(p.x-b.x)/b.w*700,y=(p.y-b.y)/b.h*505;g.beginPath();g.arc(x,y,r,0,Math.PI*2);g.fillStyle=color;g.strokeStyle='#183627';g.lineWidth=2;g.fill();g.stroke();}
      mark(goal,'#ffd473',7);mark(player,'#ffffff',4);
      info.textContent=view.zoom+'×'+(floor?' · piętro '+floor:'');more.disabled=view.zoom>=64;less.disabled=view.zoom<=1;
      target.classList.toggle('active',choosing);target.setAttribute('aria-pressed',String(choosing));canvas.classList.toggle('choosing-goal',choosing);canvas.dataset.zoom=String(view.zoom);canvas.dataset.bounds=JSON.stringify(b);
      help.textContent=choosing?'Kliknij punkt mapy, aby wyznaczyć cel. Atlas pozostanie otwarty.':'Klik: przybliż · prawy klik: oddal · przeciągnij: przesuń. Na telefonie użyj także + i −.';
    }
    canvas.addEventListener('click',e=>{
      if(suppressClick){suppressClick=false;return;}const p=uv(e);
      if(choosing){const dest=view.point(p.u,p.v);dest.x=clamp(dest.x,0,w.width);dest.y=clamp(dest.y,0,w.height);dest.floor=Number(player?.floor)||0;dest.name='Punkt na mapie';goal=dest;choosing=false;options.navigate?.(dest);}
      else view.scale(2,p.u,p.v);
      draw();
    });
    canvas.addEventListener('contextmenu',e=>{e.preventDefault();const p=uv(e);view.scale(.5,p.u,p.v);draw();});
    canvas.addEventListener('wheel',e=>{e.preventDefault();const p=uv(e);view.scale(e.deltaY<0?2:.5,p.u,p.v);draw();},{passive:false});
    canvas.addEventListener('pointerdown',e=>{if(e.button!==0)return;suppressClick=false;drag={id:e.pointerId,x:e.clientX,y:e.clientY,startX:e.clientX,startY:e.clientY,moved:false};canvas.setPointerCapture(e.pointerId);});
    canvas.addEventListener('pointermove',e=>{if(!drag||drag.id!==e.pointerId)return;if(!drag.moved&&Math.hypot(e.clientX-drag.startX,e.clientY-drag.startY)<5)return;drag.moved=true;const r=canvas.getBoundingClientRect();view.pan((e.clientX-drag.x)/r.width,(e.clientY-drag.y)/r.height);drag.x=e.clientX;drag.y=e.clientY;draw();});
    function end(e){if(!drag||drag.id!==e.pointerId)return;suppressClick=drag.moved;drag=null;if(canvas.hasPointerCapture(e.pointerId))canvas.releasePointerCapture(e.pointerId);}
    canvas.addEventListener('pointerup',end);canvas.addEventListener('pointercancel',end);
    draw();return {view,canvas,update(p,g){player=p;goal=g;draw();}};
  }
  const api={View,waterways,drawWater,drawTerrain,mount,WATER,BRIDGE};root.BractwoAtlas=api;if(typeof module!=='undefined'&&module.exports)module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
