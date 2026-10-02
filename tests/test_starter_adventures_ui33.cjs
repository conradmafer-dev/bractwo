'use strict';
const assert=require('node:assert/strict');
const A=require('../web/starter_adventures.js');
const site={id:'treasure',boss_kind:'boss',action:'starter_treasure',x:10,y:20,floor:3,name:'Skarb'};
const hero={x:10,y:20,floor:3,starter_adventures:{defeated:[],claimed:[]}};
assert.equal(A.chestState(site,hero,{}),'guarded');
hero.starter_adventures.defeated.push('boss');
assert.equal(A.chestState(site,hero,{enemies:[]}),'ready');
assert.equal(A.chestState(site,hero,{enemies:[{kind:'boss',floor:3,hp:32,alive:true}]}),'guarded');
assert.equal(A.chestState(site,hero,{enemies:[{kind:'boss',floor:3,hp:0,alive:false}]}),'ready');
hero.starter_adventures.claimed.push('treasure');
assert.equal(A.chestState(site,hero,{enemies:[{kind:'boss',floor:3,hp:32,alive:true}]}),'claimed');
assert.equal(A.chestState(site,{starter_adventures:{defeated:[],claimed:[]}},{}),'guarded');
// Procedural drawing should be safe and balance canvas saves/restores at any phase.
let depth=0,calls=0;
const c=new Proxy({save(){depth++;},restore(){assert(depth>0);depth--;},measureText(s){return{width:s.length*6};}},
 {get(o,k){return k in o?o[k]:(...args)=>{calls++;for(const x of args)if(typeof x==='number')assert(Number.isFinite(x));};},set(o,k,v){o[k]=v;return true;}});
for(const type of ['old_starter_tower','dawn_mausoleum','dawn_sarcophagus','dawn_brazier','tower_cover','tower_crates'])
 assert.equal(A.obstacle(c,{type,x:0,y:0,w:60,h:80,starter_adventure:true},1),true);
for(const starter_visual of ['headless','crypt_skeleton','tower_archer','tower_lookout'])
 assert.equal(A.actor(c,{x:100,y:100,move:.4,entity:{hp:10,max_hp:30,facing:[-1,1],name:'Strażnik'}},{starter_visual,size:1.2,boss:true},1),true);
for(const q of [0,.5,1])for(const shape of ['circle','line'])for(const kind of ['starter_warning','starter_strike'])
 assert.equal(A.effect(c,{kind,shape,x:0,y:0,target_x:100,target_y:140,radius:110,width:22},q),true);
A.chest(c,site,hero,{},1);
assert.equal(A.obstacle(c,{type:'unrelated'}),false);assert.equal(A.effect(c,{kind:'fireball'}),false);
assert.equal(depth,0);assert(calls>100);
console.log('UI33: chest states, personal claims, all six props, four actors, telegraphs and canvas state OK.');
