/* Shared coast, biome and terrain geometry for movement, ground and maps. */
(function(root){'use strict';
  function contains(points,x,y){
    if(!Array.isArray(points)||points.length<3)return false;
    let inside=false;
    for(let i=0,j=points.length-1;i<points.length;j=i++){
      const [ax,ay]=points[j],[bx,by]=points[i],cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax);
      if(Math.abs(cross)<1e-7&&x>=Math.min(ax,bx)&&x<=Math.max(ax,bx)&&y>=Math.min(ay,by)&&y<=Math.max(ay,by))return true;
      if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;
    }
    return inside;
  }
  function inBounds(r,x,y){return x>=r.x&&x<=r.x+r.w&&y>=r.y&&y<=r.y+r.h;}
  function inRegion(r,x,y){return inBounds(r,x,y)&&(!r.points?.length||contains(r.points,x,y));}
  function regionAt(world,x,y){return (world.regions||[]).find(r=>inRegion(r,x,y));}
  function patchAt(p,x,y){return p.points?.length?inBounds(p,x,y)&&contains(p.points,x,y):p.w>0&&p.h>0&&((x-p.x-p.w/2)/(p.w/2))**2+((y-p.y-p.h/2)/(p.h/2))**2<=1;}
  const boundsCache=new WeakMap();
  function massBounds(m){let b=boundsCache.get(m);if(!b){const xs=m.points.map(p=>p[0]),ys=m.points.map(p=>p[1]);b={x:Math.min(...xs),y:Math.min(...ys),right:Math.max(...xs),bottom:Math.max(...ys)};boundsCache.set(m,b);}return b;}
  function landAt(world,x,y){return !world.landmasses?.length||world.landmasses.some(l=>{const b=massBounds(l);return x>=b.x&&x<=b.right&&y>=b.y&&y<=b.bottom&&contains(l.points,x,y);});}
  function polygon(g,points,b,width,height){
    (points||[]).forEach(([x,y],i)=>{const px=(x-b.x)*width/b.w,py=(y-b.y)*height/b.h;if(i)g.lineTo(px,py);else g.moveTo(px,py);});g.closePath();
  }
  function outline(g,world,b,width,height){g.beginPath();for(const mass of world.landmasses||[])polygon(g,mass.points,b,width,height);}
  const api={contains,inBounds,inRegion,regionAt,patchAt,landAt,massBounds,polygon,outline};root.BractwoWorldGeometry=api;
  if(typeof module!=='undefined')module.exports=api;
})(globalThis);
