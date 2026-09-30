/* Shared map geometry and a persistent atlas camera. Opening a book does not pause play. */
(function(root){'use strict';
  const WATER='#559ebc',BRIDGE='#e3c388',roadBounds=new WeakMap();
  function roadBox(points){let b=roadBounds.get(points);if(!b){let left=Infinity,top=Infinity,right=-Infinity,bottom=-Infinity;for(const [x,y] of points){left=Math.min(left,x);top=Math.min(top,y);right=Math.max(right,x);bottom=Math.max(bottom,y);}b={x:left-40,y:top-40,w:right-left+80,h:bottom-top+80};roadBounds.set(points,b);}return b;}
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
  function drawTerrain(g,w,b,width,height,floor=0,details=true){
    const sx=width/b.w,sy=height/b.h,geo=root.BractwoWorldGeometry,coasts=!!w.landmasses?.length;
    const point=(x,y)=>[(x-b.x)*sx,(y-b.y)*sy],visible=r=>r.x+r.w>=b.x&&r.y+r.h>=b.y&&r.x<=b.x+b.w&&r.y<=b.y+b.h;
    const path=r=>{g.beginPath();if(r.points?.length)geo.polygon(g,r.points,b,width,height);else g.rect((r.x-b.x)*sx,(r.y-b.y)*sy,r.w*sx,r.h*sy);};
    const occupied=[];
    function label(text,x,y,color='#f5eccd',size=11,bold=false){
      if(x<8||x>width-8||y<10||y>height-8)return false;
      g.font=`${bold?'600 ':''}${size}px system-ui`;g.textAlign='center';g.textBaseline='middle';
      const hw=g.measureText(text).width/2+4,r={x:x-hw,y:y-size/2-3,w:hw*2,h:size+6};
      if(r.x<2||r.x+r.w>width-2||occupied.some(q=>r.x<q.x+q.w&&r.x+r.w>q.x&&r.y<q.y+q.h&&r.y+r.h>q.y))return false;
      occupied.push(r);g.strokeStyle='#1b3439e8';g.lineWidth=3;g.lineJoin='round';g.strokeText(text,x,y);g.fillStyle=color;g.fillText(text,x,y);return true;
    }
    g.save();g.fillStyle=floor?'#252831':coasts?'#214d62':'#446446';g.fillRect(0,0,width,height);
    if(floor){
      for(const d of [...(w.dungeons||[]),...(w.elevations||[])])if(d.floor===floor)for(const r of d.rooms||[]){if(!visible(r))continue;g.fillStyle='#a1937a';g.fillRect((r.x-b.x)*sx,(r.y-b.y)*sy,r.w*sx,r.h*sy);g.strokeStyle='#d0b99066';g.lineWidth=.7;g.strokeRect((r.x-b.x)*sx,(r.y-b.y)*sy,r.w*sx,r.h*sy);}
    } else {
      if(coasts){
        // This same server-authored coastline is used by world collision and the ground.
        geo.outline(g,w,b,width,height);g.strokeStyle='#367b8a';g.lineJoin='round';g.lineWidth=8;g.stroke();
        g.save();geo.outline(g,w,b,width,height);g.clip();g.fillStyle='#607f50';g.fillRect(0,0,width,height);
      }
      for(const r of w.regions||[]){if(!visible(r))continue;path(r);g.fillStyle=r.color||'#6b8c58';g.fill();}
      // Real forest clearings, dunes, marshes and passes retain their own irregular outline.
      for(const p of w.terrain||[]){if(!visible(p))continue;g.save();g.globalAlpha=p.relief_layer==='edge'?.16:p.relief_theme?.42:.34;g.fillStyle=w.surfaces?.[p.kind]?.color||({forest:'#2e633b',sand:'#e1c582',stone:'#91958b',mud:'#426d64',snow:'#e2eaee',ash:'#64555a'})[p.kind]||'#7da052';
        if(p.points?.length){path(p);g.fill();}else{g.beginPath();g.ellipse((p.x+p.w/2-b.x)*sx,(p.y+p.h/2-b.y)*sy,p.w*sx/2,p.h*sy/2,0,0,Math.PI*2);g.fill();}g.restore();}
      // Sparse topographic symbols describe the biome without hiding its geography.
      if(details&&b.w>18000){
        const spacing=Math.max(1100,b.w/28);
        for(const r of w.regions||[]){if(!visible(r))continue;g.save();path(r);g.clip();
          for(let yy=Math.ceil(r.y/spacing)*spacing;yy<r.y+r.h;yy+=spacing)for(let xx=Math.ceil(r.x/spacing)*spacing;xx<r.x+r.w;xx+=spacing){
            const wx=xx+Math.sin(yy*.0013+xx*.0021)*spacing*.23,wy=yy+Math.cos(xx*.0017)*spacing*.22;
            if(!geo.inRegion(r,wx,wy))continue;const [x,y]=point(wx,wy);if(x<0||y<0||x>width||y>height)continue;
            g.lineWidth=.7;g.strokeStyle='#31483166';g.fillStyle='#254c3466';
            if(r.biome==='forest'){g.beginPath();g.moveTo(x,y-4);g.lineTo(x-3,y+2);g.lineTo(x+3,y+2);g.closePath();g.fill();g.fillRect(x-.5,y+2,1,2);}
            else if(['mountain','snow','orc'].includes(r.biome)){g.strokeStyle=r.biome==='snow'?'#6b919a88':'#444c4290';g.beginPath();g.moveTo(x-5,y+3);g.lineTo(x-1,y-4);g.lineTo(x+4,y+3);g.moveTo(x-1,y-4);g.lineTo(x+1,y+1);g.stroke();}
            else if(r.biome==='desert'){g.strokeStyle='#94733b70';g.beginPath();g.moveTo(x-5,y+2);g.quadraticCurveTo(x,y-4,x+6,y+2);g.stroke();}
            else if(['lava','obsidian'].includes(r.biome)){g.strokeStyle='#392f4770';g.beginPath();g.moveTo(x-4,y+2);g.lineTo(x,y-4);g.lineTo(x+4,y+2);g.moveTo(x-1,y);g.lineTo(x+3,y+4);g.stroke();}
            else if(r.biome==='swamp'){g.strokeStyle='#2d67677a';g.beginPath();g.moveTo(x-5,y+2);g.lineTo(x+5,y+2);g.moveTo(x,y);g.lineTo(x-1,y-4);g.stroke();}
          }g.restore();
        }
      }
      g.strokeStyle='#d5bd85';g.lineWidth=Math.max(.6,64*sx);g.lineCap='round';g.lineJoin='round';
      for(const road of w.roads||[]){if(road.length<2||!visible(roadBox(road)))continue;g.beginPath();road.forEach(([x,y],i)=>{const p=point(x,y);if(i)g.lineTo(...p);else g.moveTo(...p);});g.stroke();}
      drawWater(g,w,b,width,height);
      if(b.w<16000){for(const o of w.obstacles||[])if(!(o.floor||0)&&visible(o)){
        if((o.type||o.kind)==='house'){g.fillStyle='#ab8a5b';g.fillRect((o.x-b.x)*sx,(o.y-b.y)*sy,o.w*sx,o.h*sy);}
        else if(['mountain','canyon','terrace','grove'].includes(o.type)||o.relief_theme){g.fillStyle=o.type==='grove'?'#315d35':o.relief_color||'#646c62';g.fillRect((o.x-b.x)*sx,(o.y-b.y)*sy,o.w*sx,o.h*sy);}
      }}
      if(coasts){g.restore();geo.outline(g,w,b,width,height);g.strokeStyle='#c8c297';g.lineWidth=1.2;g.stroke();}
      // Routes are indexed by server port IDs. Both directions share one visible line.
      const ports=new Map((w.ports||[]).map(p=>[p.id,p])),drawn=new Set();g.save();g.setLineDash([3,5]);g.strokeStyle='#aad4de9a';g.lineWidth=1;
      for(const route of w.sea_routes||[]){const pair=[route.from_id,route.to_id].sort().join('|');if(drawn.has(pair))continue;drawn.add(pair);
        const from=ports.get(route.from_id),to=ports.get(route.to_id);if(!from||!to)continue;
        const points=route.points?.length?route.points:[[from.shore_x??from.x,from.shore_y??from.y],[to.shore_x??to.x,to.shore_y??to.y]];
        g.beginPath();points.forEach(([x,y],i)=>i?g.lineTo(...point(x,y)):g.moveTo(...point(x,y)));g.stroke();
      }g.restore();
      for(const port of ports.values()){const [x,y]=point(port.shore_x??port.x,port.shore_y??port.y);if(x<-8||y<-8||x>width+8||y>height+8)continue;
        g.fillStyle='#bfedf0';g.strokeStyle='#254b5a';g.lineWidth=1;g.beginPath();g.moveTo(x-4,y-1);g.lineTo(x+4,y-1);g.lineTo(x+2,y+3);g.lineTo(x-2,y+3);g.closePath();g.fill();g.stroke();g.beginPath();g.moveTo(x,y-1);g.lineTo(x,y-5);g.stroke();
      }
      if(details){
        for(const c of w.cities||[]){const [x,y]=point(c.x,c.y);g.fillStyle='#ffd989';g.strokeStyle='#4b4935';g.lineWidth=1;g.beginPath();g.arc(x,y,3.2,0,Math.PI*2);g.fill();g.stroke();label(c.name,clamp(x,45,width-45),y-10,'#fff1c8',11,true);}
        if(b.w>85000){
          for(const m of w.landmasses||[]){if(m.group==='headlands'||m.id==='mainland')continue;const mb=geo.massBounds(m);if((mb.right-mb.x)*sx<36)continue;const [x,y]=point(m.label_x??(mb.x+mb.right)/2,m.label_y??(mb.y+mb.bottom)/2);label(m.name,x,y,'#e9e4c5',10,true);}
        }else{
          for(const r of w.regions||[]){if(r.w*sx<85)continue;const wx=r.label_x??r.x+r.w/2,wy=r.label_y??r.y+r.h/2;if(coasts&&!geo.landAt(w,wx,wy))continue;const [x,y]=point(wx,wy);if(label(r.name,x,y,'#f5eccd',12,true))label(`${r.min_level}–${r.max_level}`,x,y+16,'#e2dfc6',10);}
          if(b.w<35000)for(const p of ports.values())if(!p.city_id){const [x,y]=point(p.x,p.y);label(p.name,x,y-10,'#c3edf0',10);}
        }
      }
    }
    for(const s of w.stairs||[])if((s.floor||0)===floor){const [x,y]=point(s.x,s.y);if(x<0||y<0||x>width||y>height)continue;g.fillStyle='#ddbfed';g.fillRect(x-1.5,y-1.5,3,3);}
    g.restore();
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
    const help=node('p','Klik: przybliż · przeciągnij: przesuń · żółty punkt: miasto · łódź i przerywana linia: przeprawa · fioletowy punkt: podziemia.','atlas-help');box.append(help);
    const base=document.createElement('canvas');base.width=700;base.height=505;let baseKey='';
    const uv=e=>{const r=canvas.getBoundingClientRect();return {u:clamp((e.clientX-r.left)/r.width,0,1),v:clamp((e.clientY-r.top)/r.height,0,1)};};
    function draw(){
      const floor=Number(player?.floor)||0,b=view.bounds(),key=JSON.stringify([b,floor,w.world_revision]);
      if(key!==baseKey){baseKey=key;drawTerrain(base.getContext('2d'),w,b,700,505,floor);}
      const g=canvas.getContext('2d');g.drawImage(base,0,0);
      function mark(p,color,r){if(!p||(p.floor||0)!==floor)return;const x=(p.x-b.x)/b.w*700,y=(p.y-b.y)/b.h*505;g.beginPath();g.arc(x,y,r,0,Math.PI*2);g.fillStyle=color;g.strokeStyle='#183627';g.lineWidth=2;g.fill();g.stroke();}
      mark(goal,'#ffd473',7);mark(player,'#ffffff',4);
      info.textContent=view.zoom+'×'+(floor?' · piętro '+floor:'');more.disabled=view.zoom>=64;less.disabled=view.zoom<=1;
      target.classList.toggle('active',choosing);target.setAttribute('aria-pressed',String(choosing));canvas.classList.toggle('choosing-goal',choosing);canvas.dataset.zoom=String(view.zoom);canvas.dataset.bounds=JSON.stringify(b);
      help.textContent=choosing?'Kliknij punkt mapy, aby wyznaczyć cel. Atlas pozostanie otwarty.':'Klik: przybliż · przeciągnij: przesuń · żółty punkt: miasto · łódź i przerywana linia: przeprawa · fioletowy punkt: podziemia.';
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
