'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const {SpatialIndex,FrameRateMeter,MotionTrack,mergeOwner,hitActor} = require('../web/runtime.js');

test('spatial queries preserve every visible object at boundaries and across floors',()=>{
  const items=Array.from({length:4000},(_,i)=>({order:i,floor:i%3-2,left:(i*419)%128000-220,top:(i*233)%92160-220,right:(i*419)%128000+330,bottom:(i*233)%92160+340}));
  const index=new SpatialIndex(items);
  for(let i=0;i<70;i++){
    const x=(i*1777)%120000,y=(i*1301)%90000,floor=i%3-2;
    const expected=items.filter(q=>q.floor===floor&&q.right>=x&&q.left<=x+1800&&q.bottom>=y&&q.top<=y+1200).map(q=>q.order);
    assert.deepEqual(index.query(x,y,x+1800,y+1200,floor).map(q=>q.order),expected);
  }
  assert(index.lastVisited<items.length/20);
});
test('FPS measures actual frame timestamps, including slow frames and reset',()=>{
  const fps=new FrameRateMeter();let last;
  for(let i=0;i<=60;i++){const v=fps.sample(i*1000/60);if(v)last=v;}
  assert.equal(last.fps,60);
  fps.reset();for(let i=0;i<=15;i++){const v=fps.sample(i*1000/15);if(v)last=v;}
  assert.equal(last.fps,15);assert.equal(fps.sample(1001),null);
  fps.reset();assert.equal(fps.sample(60000),null);
});
test('motion interpolates evenly and snaps on floor change or distant travel',()=>{
  const motion=new MotionTrack();motion.push(0,0,0);motion.push(10,0,.1);motion.push(20,0,.2);
  assert.equal(motion.sample(.05).x,5);assert.equal(motion.sample(.15).x,15);assert.equal(motion.sample(.8).x,20);
  motion.push(32000,34560,.3);assert.equal(motion.sample(.2).x,32000);
  motion.push(32010,34560,.4,-1);assert.equal(motion.sample(.3).x,32010);
});
test('picking uses drawn positions, ignores corpses/other floors, selects monsters and players',()=>{
  const visuals=[{kind:'e',x:80,y:100,entity:{id:'rat',x:150,y:100,hp:12,kind:'rat',floor:0}},{kind:'p',x:300,y:100,entity:{id:'other',hp:50,floor:0}},{kind:'p',x:80,y:100,entity:{id:'self',hp:100,floor:0}}];
  assert.equal(hitActor(visuals,80,78,'self',0).entity.id,'rat');
  assert.equal(hitActor(visuals,300,78,'self',0).entity.id,'other');
  assert.equal(hitActor(visuals,80,78,'self',-1),null);
  visuals[0].entity.hp=0;assert.equal(hitActor(visuals,80,78,'self',0),null);
});
test('owner deltas retain unchanged bags but replace empty lists and never merge other accounts',()=>{
  const previous={id:'1',inventory:[{uid:'a'}],quests:[{id:'q'}],hp:50};
  const current=mergeOwner(previous,{id:'1',hp:40},true);
  assert.deepEqual(current.inventory,previous.inventory);assert.equal(current.hp,40);
  assert.deepEqual(mergeOwner(current,{id:'1',inventory:[]},true).inventory,[]);
  assert.equal(mergeOwner(current,{id:'2',hp:100},true).inventory,undefined);
});

test('surface index gives trails priority, curved segments, ellipse edges and floor stone', () => {
  const {SurfaceMap}=require('../web/runtime.js');
  const terrain=new SurfaceMap({roads:[[[0,0],[200,100],[350,0]]],cities:[],regions:[],terrain:[{x:50,y:-100,w:400,h:400,kind:'mud'}]});
  assert.equal(terrain.at(100,50),'path');
  assert.equal(terrain.at(275,50),'path');
  assert.equal(terrain.at(250,200),'mud');
  assert.equal(terrain.at(50,299),'forest');
  assert.equal(terrain.at(100,50,-1),'stone');
  assert.equal(terrain.roads(-10,-10,400,160).length,2);
});

test('large monster picking follows species size and ignores other floors', () => {
  const {hitActor}=require('../web/runtime.js');
  const dragon={kind:'e',x:500,y:500,entity:{id:'large',kind:'dragon',size:2,hp:100,alive:true,floor:0}};
  assert.equal(hitActor([dragon],500,355,'me',0),dragon);
  assert.equal(hitActor([dragon],500,355,'me',-1),null);
});
