/* Pure runtime utilities: no graphics settings, DOM or network dependencies. */
(function (root) {
  'use strict';
  class SpatialIndex {
    constructor(items = [], cellSize = 512) {
      this.size = cellSize; this.cells = new Map(); this.lastVisited = 0;
      for (const item of items) {
        for (let x = Math.floor(item.left / cellSize); x <= Math.floor(item.right / cellSize); x++) {
          for (let y = Math.floor(item.top / cellSize); y <= Math.floor(item.bottom / cellSize); y++) {
            const key = `${item.floor || 0}:${x}:${y}`;
            if (!this.cells.has(key)) this.cells.set(key, []);
            this.cells.get(key).push(item);
          }
        }
      }
    }
    query(left, top, right, bottom, floor = 0) {
      const result = new Set(); this.lastVisited = 0;
      for (let x = Math.floor(left / this.size); x <= Math.floor(right / this.size); x++) {
        for (let y = Math.floor(top / this.size); y <= Math.floor(bottom / this.size); y++) {
          for (const item of this.cells.get(`${floor}:${x}:${y}`) || []) {
            this.lastVisited++;
            if (item.right >= left && item.left <= right && item.bottom >= top && item.top <= bottom) result.add(item);
          }
        }
      }
      return [...result].sort((a, b) => a.order - b.order);
    }
  }
  class SurfaceMap {
    constructor(world) {
      this.world=world;const entries=[];
      for(const path of world.roads||[])for(let i=1;i<path.length;i++){
        const a=path[i-1],b=path[i];entries.push({kind:'road',a,b,order:entries.length,left:Math.min(a[0],b[0])-34,top:Math.min(a[1],b[1])-34,right:Math.max(a[0],b[0])+34,bottom:Math.max(a[1],b[1])+34});
      }
      for(const p of world.terrain||[])entries.push({kind:'patch',p,order:entries.length,left:p.x,top:p.y,right:p.x+p.w,bottom:p.y+p.h});
      this.index=new SpatialIndex(entries);
    }
    at(x,y,floor=0){
      if(floor)return 'stone';
      if((this.world.cities||[]).some(c=>Math.hypot(x-c.x,y-c.y)<205))return 'stone';
      const entries=this.index.cells.get(`0:${Math.floor(x/512)}:${Math.floor(y/512)}`)||[];
      for(const e of entries)if(e.kind==='road'){
        const dx=e.b[0]-e.a[0],dy=e.b[1]-e.a[1],q=Math.max(0,Math.min(1,((x-e.a[0])*dx+(y-e.a[1])*dy)/Math.max(1,dx*dx+dy*dy)));
        if(Math.hypot(x-e.a[0]-q*dx,y-e.a[1]-q*dy)<=33)return 'path';
      }
      for(let i=entries.length-1;i>=0;i--){const e=entries[i];if(e.kind==='patch'){const p=e.p;if(((x-p.x-p.w/2)/(p.w/2))**2+((y-p.y-p.h/2)/(p.h/2))**2<=1)return p.kind;}}
      if(x<3200&&y<2304){if(x>1720&&x<2220&&y>1370)return 'mud';if(x>2250)return 'stone';if(y<900&&x<1400)return 'forest';return 'grass';}
      const r=(this.world.regions||[]).find(r=>x>=r.x&&x<r.x+r.w&&y>=r.y&&y<r.y+r.h);
      return ({forest:'forest',swamp:'mud',desert:'sand',snow:'snow',lava:'ash',obsidian:'ash',mountain:'stone',ruins:'stone'})[r?.biome]||'grass';
    }
    roads(left,top,right,bottom){return this.index.query(left,top,right,bottom).filter(e=>e.kind==='road');}
  }
  class FrameRateMeter {
    constructor() { this.reset(); }
    reset() { this.started = null; this.frames = 0; }
    sample(now) {
      if (this.started === null) { this.started = now; return null; }
      this.frames++;
      const elapsed = now - this.started;
      if (elapsed < 500) return null;
      const result = { fps: Math.round(this.frames * 1000 / elapsed), ms: elapsed / this.frames };
      this.started = now; this.frames = 0; return result;
    }
  }
  class MotionTrack {
    constructor() { this.points = []; this.result = { x: 0, y: 0 }; }
    push(x, y, time, floor = 0) {
      const last = this.points[this.points.length - 1];
      if (last && (last.floor !== floor || Math.hypot(last.x - x, last.y - y) > 450 || time < last.time)) this.points.length = 0;
      if (last && time === last.time) this.points.pop();
      this.points.push({ x, y, time, floor });
      if (this.points.length > 6) this.points.shift();
    }
    sample(time) {
      const points = this.points; if (!points.length) return this.result;
      let a = points[0], b = a;
      for (let i = 1; i < points.length; i++) { b = points[i]; if (b.time >= time) break; a = b; }
      const t = b.time > a.time ? Math.max(0, Math.min(1, (time - a.time) / (b.time - a.time))) : 0;
      this.result.x = a.x + (b.x - a.x) * t; this.result.y = a.y + (b.y - a.y) * t;
      return this.result;
    }
  }
  function mergeOwner(previous, entry, enabled) {
    return enabled && previous && String(previous.id) === String(entry.id) ? { ...previous, ...entry } : entry;
  }
  function hitActor(visuals, x, y, myId, floor, scale = 1) {
    let selected = null, best = Infinity;
    for (const v of visuals) {
      const e = v.entity;
      if (e.hp <= 0 || e.alive === false || (e.floor || 0) !== floor || (v.kind === 'p' && String(e.id) === String(myId))) continue;
      const tall = e.kind === 'dragon' || e.kind === 'dragon_lord' || e.kind === 'demon' || e.kind === 'abyss_walker' || /lord|queen|ancient/.test(e.kind || '');
      const size = Number(e.size)||1;
      const d = Math.hypot(v.x - x, v.y - (tall ? 38 : 22)*size - y);
      if (d < (tall ? 50 : 36)*size / Math.min(1, scale) && d < best) { selected = v; best = d; }
    }
    return selected;
  }
  const api = { SurfaceMap, SpatialIndex, FrameRateMeter, MotionTrack, mergeOwner, hitActor };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.BractwoRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
