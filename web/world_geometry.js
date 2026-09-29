/* Shared continent outlines for the ground, atlas and minimap. */
(function(root){'use strict';
  function contains(points,x,y){
    let inside=false;
    for(let i=0,j=points.length-1;i<points.length;j=i++){
      const [ax,ay]=points[j],[bx,by]=points[i],cross=(x-ax)*(by-ay)-(y-ay)*(bx-ax);
      if(Math.abs(cross)<1e-7&&x>=Math.min(ax,bx)&&x<=Math.max(ax,bx)&&y>=Math.min(ay,by)&&y<=Math.max(ay,by))return true;
      if((ay>y)!==(by>y)&&x<(bx-ax)*(y-ay)/(by-ay)+ax)inside=!inside;
    }
    return inside;
  }
  function landAt(world,x,y){return !world.landmasses?.length||world.landmasses.some(l=>contains(l.points,x,y));}
  function outline(g,world,b,width,height){
    g.beginPath();
    for(const mass of world.landmasses||[]){
      (mass.points||[]).forEach(([x,y],i)=>{const px=(x-b.x)*width/b.w,py=(y-b.y)*height/b.h;if(i)g.lineTo(px,py);else g.moveTo(px,py);});
      g.closePath();
    }
  }
  const api={contains,landAt,outline};root.BractwoWorldGeometry=api;
  if(typeof module!=='undefined')module.exports=api;
})(globalThis);
