/* Wilderness scenery. Ground details are baked into the existing 512px cache. */
(function(root){'use strict';
  const TAU=Math.PI*2,START_X=7000,START_Y=6600;
  const spriteCache=new Map(),SPRITE_PIXELS=4000000;
  let spritePixels=0;
  const palette={
    meadow:{base:'#7eaa50',shade:'#6f9847',light:'#91b65e',soil:'#9a9962',tuft:'#59873c',tip:'#aec978'},
    forest:{base:'#547b45',shade:'#456e3e',light:'#648a4b',soil:'#6a7650',tuft:'#3d6539',tip:'#8aab60'},
    swamp:{base:'#777853',shade:'#6c704d',light:'#85835a',soil:'#76634d',tuft:'#566a3e',tip:'#a49862'},
    desert:{base:'#cbb177',shade:'#bda16a',light:'#dcc58b',soil:'#ac956c',tuft:'#9e9460',tip:'#c4bb82'},
    snow:{base:'#c6d9db',shade:'#aec5ce',light:'#e0e9e5',soil:'#a7babd',tuft:'#8a9f9e',tip:'#edf2e9'},
    mountain:{base:'#95998a',shade:'#838d80',light:'#afb09b',soil:'#777e74',tuft:'#737f60',tip:'#bec1a0'},
    ruins:{base:'#8b9784',shade:'#7e8979',light:'#a4ad94',soil:'#717b6e',tuft:'#637f4e',tip:'#b7c298'},
    orc:{base:'#a08f60',shade:'#8b7e56',light:'#b09d68',soil:'#746a4f',tuft:'#767345',tip:'#b6b17a'},
    lava:{base:'#806354',shade:'#71574e',light:'#957058',soil:'#574c49',tuft:'#9c7b59',tip:'#ba9472'},
    obsidian:{base:'#696071',shade:'#5b5465',light:'#7b6e7e',soil:'#4c4757',tuft:'#8b8090',tip:'#ae9ca6'}
  };
  const surfacePalette={grass:palette.meadow,forest:palette.forest,mud:{...palette.swamp,base:'#8a775b',shade:'#79684f',light:'#a08c6a'},sand:palette.desert,snow:palette.snow,stone:palette.mountain,ash:palette.obsidian};
  function rng(seed){return()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};}
  function hash(x,y,salt=0){return (Math.imul(x,73856093)^Math.imul(y,19349663)^Math.imul(salt,83492791))>>>0;}
  function block(g,x,y,w,h,color){g.fillStyle=color;g.fillRect(Math.round(x),Math.round(y),Math.round(w),Math.round(h));}
  function path(g,points){g.beginPath();for(let i=0;i<points.length;i++){const[x,y]=points[i];i?g.lineTo(x,y):g.moveTo(x,y);}g.closePath();}
  function polygon(g,points,color){path(g,points);g.fillStyle=color;g.fill();}
  function line(g,points,color,width=1){g.beginPath();for(let i=0;i<points.length;i++){const[x,y]=points[i];i?g.lineTo(x,y):g.moveTo(x,y);}g.strokeStyle=color;g.lineWidth=width;g.stroke();}
  function ellipse(g,x,y,rx,ry,color){g.beginPath();g.ellipse(x,y,Math.max(.5,rx),Math.max(.5,ry),0,0,TAU);g.fillStyle=color;g.fill();}
  function outsideStarter(x,y){return x>=START_X||y>=START_Y;}
  function overlaps(r,l,t,right,bottom,pad=0){return r.x+r.w>=l-pad&&r.x<=right+pad&&r.y+r.h>=t-pad&&r.y<=bottom+pad;}
  function irregular(x,y,rx,ry,random,count=11){return Array.from({length:count},(_,i)=>{const a=i/count*TAU,r=.74+random()*.27;return[Math.round(x+Math.cos(a)*rx*r),Math.round(y+Math.sin(a)*ry*r)];});}
  function regionPath(g,r){if(r.points?.length)path(g,r.points);else{g.beginPath();g.rect(r.x,r.y,r.w,r.h);}}
  function patchPath(g,p){if(p.points?.length)path(g,p.points);else{g.beginPath();g.ellipse(p.x+p.w/2,p.y+p.h/2,p.w/2,p.h/2,0,0,TAU);}}
  function cityAt(world,x,y,margin=0){return(world.cities||[]).some(c=>Math.hypot(x-c.x,y-c.y)<(c.paving_radius||205)+margin);}
  function biomeAt(world,x,y){return root.BractwoWorldGeometry.regionAt(world,x,y)?.biome||'meadow';}
  function terrainAt(map,x,y){return map?.at(x,y)||'grass';}
  function surfaceColors(kind,biome){return kind==='ash'?(palette[biome]||surfacePalette.ash):surfacePalette[kind]||palette[biome]||palette.meadow;}

  // Every macro shape has a global cell seed, so patterns continue across chunks.
  function paintPatterns(g,pal,l,t,right,bottom,salt){
    for(let by=Math.floor((t-100)/176);by<=Math.floor((bottom+100)/176);by++)for(let bx=Math.floor((l-100)/176);bx<=Math.floor((right+100)/176);bx++){
      const random=rng(hash(bx,by,salt)),x=bx*176+random()*110,y=by*176+random()*110;
      polygon(g,irregular(x,y,72+random()*88,32+random()*58,random),pal.shade+'48');
      polygon(g,irregular(x+40,y-12,40+random()*90,23+random()*48,random),pal.light+'48');
      if(random()>.56)polygon(g,irregular(x-35,y+30,30+random()*47,11+random()*19,random,8),pal.soil+'2b');
    }
  }
  function paintPatch(g,p,l,t,right,bottom){
    const biome=p.relief_biome||(/snow|frost/.test(p.relief_theme||'')?'snow':/desert|dune/.test(p.relief_theme||'')?'desert':/ash/.test(p.relief_theme||'')?'obsidian':null);
    const pal=surfaceColors(p.kind,biome);
    g.save();patchPath(g,p);g.fillStyle=pal.base;g.fill();
    // Narrow tonal rims soften the silhouette without inventing new surface types.
    g.strokeStyle=pal.light+'55';g.lineWidth=7;g.stroke();g.clip();
    paintPatterns(g,pal,l,t,right,bottom,31+p.kind.length);
    if(p.relief_layer==='accent'){
      patchPath(g,p);g.strokeStyle=pal.shade+'80';g.lineWidth=3;g.stroke();
    }
    g.restore();
  }
  function grass(g,x,y,pal,random){
    for(let k=0;k<3;k++){
      const dx=Math.round(random()*15-8),dy=Math.round(random()*8-4),h=3+Math.round(random()*5);
      block(g,x+dx,y+dy,2,h,pal.tuft);block(g,x+dx+2,y+dy-2,2,3,pal.tip);
    }
  }
  function flower(g,x,y,color){block(g,x,y,2,6,'#587540');block(g,x-2,y-2,6,2,color);block(g,x,y-4,2,6,color);block(g,x,y-2,2,2,'#e9cc73');}
  function leafLitter(g,x,y,random){
    for(let i=0;i<9;i++){const xx=x+random()*36-18,yy=y+random()*17-8;polygon(g,[[xx-3,yy],[xx,yy-2],[xx+4,yy+1],[xx,yy+3]],i%3===0?'#bc9d6166':i%2?'#8b884b8c':'#a6985980');}
    if(random()>.7)line(g,[[x-13,y+9],[x-1,y+4],[x+9,y+5]],'#524d37',2);
  }
  function contour(g,x,y,random,pal,snow){
    const w=43+random()*40;
    for(let i=0;i<3;i++){const yy=y+i*(snow?8:6);line(g,[[x-w,yy+5],[x-w*.5,yy],[x+w*.2,yy-3],[x+w,yy+3]],i===0?pal.light+'aa':pal.shade+'58',snow?2:1);}
    if(!snow&&random()>.68){ellipse(g,x+26,y+22,9,3,pal.shade);line(g,[[x+20,y+19],[x+31,y+18]],pal.light,2);}
  }
  function strata(g,x,y,random,pal,ruins){
    const w=13+random()*25;
    polygon(g,[[x-w,y],[x-w*.4,y-7],[x+w*.5,y-6],[x+w,y+2],[x+w*.3,y+6],[x-w*.7,y+6]],pal.shade+'90');
    line(g,[[x-w*.7,y-1],[x,y-4],[x+w*.6,y-3]],pal.light,2);
    line(g,[[x-3,y-3],[x+2,y+1],[x-2,y+5]],pal.soil,1);
    if(ruins&&random()>.52){block(g,x+20,y+8,12,8,'#8b9380');block(g,x+21,y+8,9,2,'#b9bba0');}
  }
  function reeds(g,x,y,random){
    ellipse(g,x,y+3,18,5,'#73694a66');
    for(let k=0;k<4;k++){
      const xx=x+k*4-8,h=12+random()*12;line(g,[[xx,y+4],[xx-2,y-h]],'#576b3f',2);block(g,xx-3,y-h-4,3,7,k%2?'#ad9761':'#8c7b4d');
    }
    line(g,[[x-15,y+8],[x-2,y+9],[x+10,y+7]],'#b09d7355',1);
  }
  function paintScatter(g,world,map,l,t,right,bottom){
    for(let by=Math.floor((t-48)/72);by<=Math.floor((bottom+48)/72);by++)for(let bx=Math.floor((l-48)/72);bx<=Math.floor((right+48)/72);bx++){
      const random=rng(hash(bx,by,87)),x=bx*72+13+random()*47,y=by*72+13+random()*47;
      if(!outsideStarter(x,y)||!root.BractwoWorldGeometry.landAt(world,x,y)||cityAt(world,x,y,15))continue;
      const kind=terrainAt(map,x,y),biome=biomeAt(world,x,y),pal=surfaceColors(kind,biome);
      if(kind==='path')continue;
      if(kind==='sand'){if(random()>.22)contour(g,x,y,random,pal,false);if(random()>.85)grass(g,x,y,pal,random);}
      else if(kind==='snow'){if(random()>.25)contour(g,x,y,random,pal,true);if(random()>.85)strata(g,x,y,random,{...pal,shade:'#9bafb2',light:'#e5ece7'},false);}
      else if(kind==='forest'){leafLitter(g,x,y,random);if(random()>.5)grass(g,x,y,pal,random);if(random()>.94)flower(g,x,y,'#e0d9a0');}
      else if(kind==='mud'){if(random()>.3)polygon(g,irregular(x,y,15+random()*22,5+random()*9,random,8),pal.shade+'77');if(biome==='swamp'&&random()>.53)reeds(g,x,y,random);}
      else if(kind==='stone'||kind==='ash'){
        if(random()>.31)strata(g,x,y,random,pal,biome==='ruins');
        if(kind==='stone'&&random()>.78)grass(g,x+17,y,pal,random);
        if(biome==='lava'&&random()>.94)line(g,[[x-9,y+3],[x+1,y-2],[x+9,y+4]],'#b5896a',1);
      }else{
        grass(g,x,y,pal,random);
        if(random()>.65){const color=['#f1d993','#d5b2dc','#dce5a7','#8cc4bf'][Math.floor(random()*4)];for(let i=0;i<3;i++)flower(g,x+random()*20-10,y+random()*11-5,color);}
        if(random()>.82)polygon(g,irregular(x+19,y+11,8,3,random,7),pal.soil+'88');
      }
    }
  }
  function paintRoads(g,entries,world,map,l,t,right,bottom){
    const roads=entries.filter(e=>e.kind==='road');if(!roads.length)return;g.lineJoin=g.lineCap='round';
    // Paint complete width layers before the next one. Short curved segments
    // then join into one track rather than outlining every round segment cap.
    for(const [width,color]of[[82,'#8b805155'],[72,'#797c4d66'],[66,'#b7a073'],[47,'#c4ae7d']]){
      g.beginPath();for(const e of roads){g.moveTo(e.a[0],e.a[1]);g.lineTo(e.b[0],e.b[1]);}g.strokeStyle=color;g.lineWidth=width;g.stroke();
    }
    // Texture follows global cells and checks the authoritative road surface.
    for(let by=Math.floor(t/18);by<=Math.floor(bottom/18);by++)for(let bx=Math.floor(l/22);bx<=Math.floor(right/22);bx++){
      const random=rng(hash(bx,by,190)),x=bx*22+random()*10,y=by*18+random()*9;
      const onRoad=roads.some(e=>{
        if(x<e.left||x>e.right||y<e.top||y>e.bottom)return false;
        const dx=e.b[0]-e.a[0],dy=e.b[1]-e.a[1],q=Math.max(0,Math.min(1,((x-e.a[0])*dx+(y-e.a[1])*dy)/Math.max(1,dx*dx+dy*dy)));
        return Math.hypot(x-e.a[0]-q*dx,y-e.a[1]-q*dy)<30;
      });
      if(!onRoad||cityAt(world,x,y))continue;
      block(g,x,y,7+random()*8,2,'#a18b64');if(random()>.75)block(g,x+1,y-2,3,2,'#d6c38e');
    }
    g.lineCap='butt';g.lineJoin='miter';
  }
  function paintCities(g,world,l,t,right,bottom){
    for(const c of world.cities||[]){const r=c.paving_radius||205;if(c.x+r<l||c.x-r>right||c.y+r<t||c.y-r>bottom)continue;
      g.save();g.beginPath();g.arc(c.x,c.y,r,0,TAU);g.clip();g.fillStyle='#a29e88';g.fillRect(c.x-r,c.y-r,r*2,r*2);
      for(let y=Math.floor(Math.max(t,c.y-r)/19)*19;y<=Math.min(bottom,c.y+r);y+=19)for(let x=Math.floor(Math.max(l,c.x-r)/28)*28;x<=Math.min(right,c.x+r);x+=28){
        const offset=(Math.floor(y/19)%2)*14,random=rng(hash(x,y,23));block(g,x+offset+1,y+1,25,16,random()>.5?'#bcb69a':'#b4af95');block(g,x+offset+2,y+1,23,2,'#d1c8aa');
      }g.restore();
    }
  }
  function paintShore(g,world,map,l,t,right,bottom){
    for(const mass of world.landmasses||[])for(let i=0;i<mass.points.length;i++){
      const a=mass.points[i],b=mass.points[(i+1)%mass.points.length];
      if(Math.max(a[0],b[0])<l-20||Math.min(a[0],b[0])>right+20||Math.max(a[1],b[1])<t-20||Math.min(a[1],b[1])>bottom+20)continue;
      const dx=b[0]-a[0],dy=b[1]-a[1],len=Math.hypot(dx,dy)||1,steps=Math.ceil(len/64);
      for(let s=0;s<steps;s++){
        const aa=[a[0]+dx*s/steps,a[1]+dy*s/steps],bb=[a[0]+dx*(s+1)/steps,a[1]+dy*(s+1)/steps],x=(aa[0]+bb[0])/2,y=(aa[1]+bb[1])/2;
        if(x<l-80||x>right+80||y<t-80||y>bottom+80||cityAt(world,x,y,12)||terrainAt(map,x,y)==='path')continue;
        const biome=biomeAt(world,x,y),dark=['lava','obsidian'].includes(biome),snow=biome==='snow',rock=biome==='mountain';
        line(g,[aa,bb],dark?'#a2979777':snow?'#edf2e6':rock?'#bcb8a0':'#c7b681',12);
        line(g,[aa,bb],dark?'#403f4d':snow?'#92afb7':rock?'#747f7a':'#8c9670',3);
        const sign=root.BractwoWorldGeometry.landAt(world,x-dy/len*9,y+dx/len*9)?1:-1;
        const xx=x-dy/len*sign*14,yy=y+dx/len*sign*14,random=rng(hash(Math.round(xx),Math.round(yy),90));
        if(random()>.4){block(g,xx,yy,3+random()*4,2,dark?'#aea0a1':snow?'#eaf0e4':'#d5c695');}
      }
    }
  }
  function paintChunk(g,{world,surfaceMap,cx,cy,floor=0}){
    const l=cx*512,t=cy*512,right=l+512,bottom=t+512;
    if(floor||right<=START_X&&bottom<=START_Y)return;
    g.save();g.translate(-l,-t);
    // This exact clip keeps every existing pixel in the opening area unchanged.
    g.beginPath();g.rect(START_X,0,Math.max(0,world.width-START_X),world.height);g.rect(0,START_Y,START_X,Math.max(0,world.height-START_Y));g.clip();
    // Complete outside chunks bypass the old per-tile terrain pass. Sea uses
    // the same solid-blue language and is never introduced inside a landmass.
    g.fillStyle='#326f87';g.fillRect(l,t,512,512);
    for(let by=Math.floor(t/64);by<=Math.floor(bottom/64);by++)for(let bx=Math.floor(l/64);bx<=Math.floor(right/64);bx++){
      const random=rng(hash(bx,by,204)),x=bx*64+random()*36,y=by*64+random()*40;
      if(random()>.42)line(g,[[x,y],[x+16,y],[x+24,y-3]],'#70a9b366',1);
    }
    if(world.landmasses?.length){g.beginPath();for(const mass of world.landmasses){mass.points.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();}g.clip();}
    g.fillStyle=palette.meadow.base;g.fillRect(l,t,512,512);paintPatterns(g,palette.meadow,l,t,right,bottom,9);
    const regions=(world.regions||[]).filter(r=>overlaps(r,l,t,right,bottom,32));
    for(const region of regions){const pal=palette[region.biome]||palette.meadow;g.save();regionPath(g,region);g.fillStyle=pal.base;g.fill();g.clip();paintPatterns(g,pal,l,t,right,bottom,11+(region.biome||'').length);g.restore();}
    // Indexed once per chunk, rather than scanning all polygons on every frame.
    const entries=surfaceMap?.index.query(l-48,t-48,right+48,bottom+48,0)||[];
    for(const entry of entries)if(entry.kind==='patch')paintPatch(g,entry.p,l,t,right,bottom);
    paintScatter(g,world,surfaceMap,l,t,right,bottom);paintRoads(g,entries,world,surfaceMap,l,t,right,bottom);paintCities(g,world,l,t,right,bottom);paintShore(g,world,surfaceMap,l,t,right,bottom);
    g.restore();
  }

  function reliefPalette(o){
    const theme=o.relief_theme||'',biome=o.relief_biome||'';
    if(biome==='desert'||/desert|dune/.test(theme))return{dark:'#80654b',face:'#ab835d',light:'#d3b382',top:o.relief_color||'#b8996f',crest:'#e4c58e',growth:'#a49663'};
    if(biome==='snow'||/snow|frost/.test(theme))return{dark:'#6f858b',face:'#91a5a8',light:'#bfccca',top:o.relief_color||'#b7c8cb',crest:'#edf1e8',growth:'#83989a'};
    if(biome==='lava'||biome==='obsidian'||/ash|basalt|rift/.test(theme))return{dark:'#373541',face:'#554c60',light:'#837287',top:o.relief_color||'#665a70',crest:'#a796a7',growth:'#96818b'};
    if(o.type==='grove'||/wood|marsh|reed/.test(theme))return{dark:'#3f5140',face:'#656d4c',light:'#88956c',top:o.relief_color||'#687c4d',crest:'#a4b981',growth:'#3e653c'};
    if(biome==='ruins'||/ruin/.test(theme))return{dark:'#53635c',face:'#7c8578',light:'#b1b5a0',top:o.relief_color||'#949d86',crest:'#d0c9ac',growth:'#748b58'};
    return{dark:'#53615d',face:'#7c8780',light:'#a4ada0',top:o.relief_color||'#8e9788',crest:'#c9cbb5',growth:'#778862'};
  }
  function reliefTree(g,x,y,scale,random,marsh){
    g.save();g.translate(Math.round(x),Math.round(y));g.scale(scale,scale);
    ellipse(g,0,4,21,7,'#24392a50');block(g,-5,-32,10,35,'#61482f');block(g,-2,-29,4,29,'#957544');
    const colors=marsh?['#36573c','#4c7350','#74915d','#a1af75']:['#2f6037','#427a3d','#659549','#94b763'];
    const crown=[[-28,-50,56,22,0],[-20,-66,42,20,0],[-11,-76,26,13,0],[-32,-41,65,15,0],[-24,-61,42,21,1],[-28,-45,48,22,1],[-6,-56,35,24,1],[-14,-70,27,17,2],[-22,-52,27,18,2],[5,-45,23,13,2],[-9,-68,16,5,3],[-19,-50,12,5,3],[11,-42,9,4,3]];
    for(const [xx,yy,ww,hh,color]of crown)block(g,xx,yy,ww,hh,colors[color]);
    if(random()>.64){block(g,-11,-41,4,3,'#c4a168');block(g,12,-50,3,3,'#c1ae76');}g.restore();
  }
  function paintWoodedBank(g,o,pal,random){
    const w=o.w,h=o.h,rootRidge=/root/.test(o.relief_theme||''),lip=rootRidge?14:8;
    ellipse(g,w*.51,h*.68,w*.55,h*.39,'#2b443a44');
    polygon(g,[[0,h*.14],[w*.17,0],[w*.82,0],[w,h*.17],[w,h*.88],[w*.7,h],[w*.25,h],[0,h*.86]],'#49664166');
    const rim=[[0,h*.78],[w*.19,h*.82-2],[w*.42,h*.74],[w*.68,h*.8+2],[w,h*.76]];
    polygon(g,rim.concat([[w,h*.76+lip],[w*.67,h*.8+lip],[w*.4,h*.74+lip],[w*.17,h*.82+lip],[0,h*.78+lip]]),'#796d48');
    line(g,rim,'#8c9a5c',3);
    for(let k=0;k<4;k++){
      const x=9+random()*Math.max(1,w-18),y=h*.79;line(g,[[x,y-7],[x-5,y+3],[x+7,y+lip]],'#59482f',2);if(k%2)line(g,[[x-3,y],[x-13,y+5]],'#9c8957',2);
    }
    const cols=Math.max(2,Math.min(4,Math.round(w/48))),rows=h>78?2:1,trees=[];
    for(let row=0;row<rows;row++)for(let col=0;col<cols;col++)trees.push({x:(col+.5)*w/cols+random()*12-6,y:h*(.35+row*.38)+random()*10,size:.69+random()*.2});
    trees.sort((a,b)=>a.y-b.y);for(const tree of trees)reliefTree(g,tree.x,tree.y,tree.size,random,o.relief_biome==='swamp');
    for(let k=0;k<4;k++)grass(g,random()*w,h*.86+random()*h*.07,palette.forest,random);
  }
  function paintMarshBank(g,o,pal,random){
    const w=o.w,h=o.h;
    ellipse(g,w*.52,h*.73,w*.56,h*.31,'#4a503e55');
    polygon(g,[[0,h*.16],[w*.12,0],[w*.53,0],[w*.85,h*.05],[w,h*.23],[w,h*.91],[w*.73,h],[w*.23,h],[0,h*.81]],'#686b4d');
    polygon(g,[[0,h*.16],[w*.12,0],[w*.53,0],[w*.85,h*.05],[w,h*.23],[w*.92,h*.56],[w*.69,h*.66],[w*.38,h*.61],[w*.1,h*.72],[0,h*.53]],'#8c9568');
    line(g,[[w*.09,h*.71],[w*.36,h*.62],[w*.69,h*.67],[w*.9,h*.58]],'#b2b488',2);
    for(let k=0;k<4;k++){const x=12+random()*Math.max(1,w-24),y=h*.3+random()*h*.33;reeds(g,x,y,random);}
    for(let k=0;k<4;k++)grass(g,10+random()*Math.max(1,w-20),h*.68+random()*h*.2,palette.swamp,random);
  }
  function paintRelief(g,o,index){
    const w=o.w,h=o.h,rise=Math.max(14,Math.min(66,Number(o.relief_height)||30)),theme=o.relief_theme||'',pal=reliefPalette(o),random=rng(hash(o.x,o.y,index));
    const biome=o.relief_biome||'',wood=o.type==='grove',wet=/marsh|reed/.test(theme),snow=biome==='snow'||/snow|frost/.test(theme),desert=biome==='desert'||/desert|dune/.test(theme),basalt=biome==='lava'||biome==='obsidian'||/ash|basalt|rift/.test(theme),ridge=/ridge|pass/.test(theme);
    if(wood){paintWoodedBank(g,o,pal,random);return;}
    if(wet){paintMarshBank(g,o,pal,random);return;}
    ellipse(g,w*.54,h*.76,w*.56,h*.32,'#202b2655');
    // The base fills the complete rectangular collider; relief rises above it.
    const top=[[0,0],[w*.1,-rise*.3],[w*.27,-rise*.8],[w*.5,-rise],[w*.74,-rise*.68],[w*.92,-rise*.2],[w,0],[w,h*.6],[w*.74,h*.68],[w*.49,h*.58],[w*.25,h*.67],[0,h*.56]];
    polygon(g,[[0,0],[w,0],[w,h],[0,h]],pal.dark);
    polygon(g,[[0,h*.34],[w,h*.34],[w,h],[w*.73,h-3],[w*.46,h],[w*.2,h-2],[0,h]],pal.face);
    polygon(g,top,pal.top);
    line(g,top.slice(6),pal.crest,3);
    for(let band=0;band<3;band++){
      const y=h*.69+band*h*.105;
      line(g,[[2,y],[w*.23,y+3],[w*.42,y-1],[w*.71,y+3],[w-2,y-1]],band===0?pal.light:pal.dark+'99',2+band%2);
    }
    for(let x=18;x<w-10;x+=35+random()*29){line(g,[[x,h*.62],[x-5,h*.79],[x+2,h-2]],pal.dark,2);line(g,[[x-2,h*.66],[x+3,h*.79]],pal.light+'aa',2);}
    if(ridge||desert||basalt){
      const count=Math.max(2,Math.min(7,Math.ceil(w/70)));
      for(let k=0;k<count;k++){
        const x=(k+.5)*w/count,y=h*.25+random()*h*.22,rw=Math.min(w/count*.6,35),peak=rise*(ridge?1.35:.78)+random()*24;
        polygon(g,[[x-rw,y+22],[x-rw*.65,y-peak*.2],[x-rw*.1,y-peak],[x+rw*.45,y-peak*.65],[x+rw,y+17]],k%2?pal.face:pal.dark);
        polygon(g,[[x-rw,y+22],[x-rw*.65,y-peak*.2],[x-rw*.1,y-peak],[x+rw*.03,y+12]],pal.light);
        line(g,[[x-rw*.1,y-peak+3],[x+rw*.45,y-peak*.61],[x+rw*.7,y+4]],pal.crest,2);
        if(desert)for(let j=0;j<3;j++)line(g,[[x-rw*.5,y+j*6],[x+rw*.6,y+j*6+2]],pal.face,2);
        if(basalt)line(g,[[x+rw*.4,y-peak*.4],[x+rw*.31,y+16]],pal.crest+'88',2);
      }
    }
    for(let k=0;k<Math.max(3,Math.floor(w*h/4300));k++){
      const x=10+random()*Math.max(1,w-20),y=random()*h*.46;
      ellipse(g,x,y,3+random()*5,2,pal.dark+'77');line(g,[[x-3,y-2],[x+3,y-3]],pal.light,1);
    }
    if(snow){
      polygon(g,top.slice(0,7).concat([[w*.96,h*.18],[w*.73,h*.25],[w*.46,h*.16],[w*.22,h*.21],[w*.03,h*.15]]),pal.crest);
      for(let k=0;k<3;k++)line(g,[[w*.08,h*.24+k*7],[w*.37,h*.18+k*7],[w*.72,h*.22+k*7]],'#adc4cc',2);
      for(let x=17;x<w;x+=48){polygon(g,[[x,h*.6],[x+17,h*.62],[x+12,h*.72],[x+4,h*.67]],'#e6ede7');}
    }
    if(/ruin/.test(theme)){for(let k=0;k<3;k++){const x=10+k*w*.29,y=h*.27+k*3;block(g,x,y,Math.min(38,w*.2),14,pal.face);block(g,x,y,Math.min(38,w*.2),3,pal.crest);line(g,[[x+13,y+4],[x+12,y+13]],pal.dark,1);}}
    if(basalt&&/rift/.test(theme))line(g,[[w*.36,h*.7],[w*.43,h*.83],[w*.39,h*.96]],'#a88684',1);
  }
  function drawRelief(g,o,index=0){
    if(!o.relief_theme)return false;
    const key=`${o.relief_id||''}:${o.x}:${o.y}:${o.w}:${o.h}:${o.relief_theme}`;
    let sprite=spriteCache.get(key);
    if(sprite){spriteCache.delete(key);spriteCache.set(key,sprite);}
    else{
      const pad=130,c=document.createElement('canvas');c.width=Math.ceil(o.w+24);c.height=Math.ceil(o.h+pad+14);
      const painter=c.getContext('2d');painter.translate(12,pad);paintRelief(painter,o,index);sprite={canvas:c,pad};
      while(spritePixels+c.width*c.height>SPRITE_PIXELS&&spriteCache.size){const oldest=spriteCache.keys().next().value,old=spriteCache.get(oldest);spritePixels-=old.canvas.width*old.canvas.height;old.canvas.width=1;spriteCache.delete(oldest);}
      spriteCache.set(key,sprite);spritePixels+=c.width*c.height;
    }
    g.drawImage(sprite.canvas,Math.round(o.x-12),Math.round(o.y-sprite.pad));return true;
  }
  function clear(){for(const s of spriteCache.values())s.canvas.width=1;spriteCache.clear();spritePixels=0;}
  const api={paintChunk,drawRelief,clear,starter:{x:START_X,y:START_Y},cacheStats:()=>({sprites:spriteCache.size,pixels:spritePixels})};
  root.BractwoTerrainArt=api;if(typeof module!=='undefined')module.exports=api;
})(globalThis);
