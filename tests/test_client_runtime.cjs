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


test('combat readout explains lower d20, misses, criticals and saving throws', () => {
  const {combatSummary}=require('../web/runtime.js');
  const attack={id:'fx1',target_name:'Goblin',rolls:[20,1],roll:1,bonus:4,total:5,defense:12,check:'attack',hit:false,critical:false,disadvantage:true,damage:0};
  const miss=combatSummary(attack);
  assert(miss.includes('k20 [20, 1] → 1 + 4 = 5 / KP 12'));
  assert(miss.includes('PUDŁO'));assert(!miss.includes('obr.'));
  const critical=combatSummary({...attack,disadvantage:false,roll:20,total:24,hit:true,critical:true,damage:31});
  assert(critical.includes('KRYTYK') && critical.includes('31 obr.'));
  const save=combatSummary({...attack,check:'save',saved:true,disadvantage:false,roll:15,total:19,hit:true,damage:12});
  assert(save.includes('/ ST 12') && save.includes('12 obr.'));
  assert.equal(combatSummary({}), '');
});

test('companion cannot be accidentally selected as a hostile monster',()=>{
 const c={kind:'c',x:80,y:100,entity:{id:'pet-1',kind:'wolf',hp:20,floor:0,is_companion:true}};
 assert.equal(hitActor([c],80,78,'self',0),null);
});
test('combat summary exposes actual damage dice and zero save damage',()=>{
 const {combatSummary}=require('../web/runtime.js');
 const text=combatSummary({id:'roll1',target_name:'Goblin',action:'Ognisty pocisk',check:'attack',rolls:[15],roll:15,bonus:5,total:20,defense:13,hit:true,damage:6,damage_dice:'1k10'});
 assert(text.includes('1k10')&&text.includes('6 obr.'));
 const save=combatSummary({id:'roll2',check:'save',rolls:[15],roll:15,bonus:0,total:15,defense:13,saved:true,hit:true,damage:0,save_half:false,damage_dice:'1k6'});
 assert(save.includes('0 obr.'));assert(!save.includes('połowa'));
});

test('paginated hotbar keeps twenty-four keys and exposes every unlocked spell',()=>{
 const {hotbarPageCount,hotbarKey}=require('../web/runtime.js');
 const bar=Array.from({length:48},(_,i)=>'s'+i);
 assert.equal(hotbarPageCount(bar),2);
 assert.equal(hotbarKey(bar,0,11),'s11');assert.equal(hotbarKey(bar,0,23),'s23');
 assert.equal(hotbarKey(bar,1,0),'s24');assert.equal(hotbarKey(bar,1,23),'s47');
 assert.equal(hotbarKey(bar,4,0),'');assert.equal(hotbarKey(bar,0,24),'');
});
test('hotbar pages handle empty lists and exact twenty-four-slot boundaries',()=>{
 const {hotbarPageCount}=require('../web/runtime.js');
 assert.equal(hotbarPageCount([]),1);assert.equal(hotbarPageCount(null),1);
 assert.equal(hotbarPageCount(Array(24)),1);assert.equal(hotbarPageCount(Array(48)),2);
 assert.equal(hotbarPageCount(Array(25)),2);
});
test('status timer distinguishes six hundred rounds from real-world duration',()=>{
 const {formatEffectTime}=require('../web/runtime.js');
 assert.equal(formatEffectTime({remaining:1800,rounds:600}),'30:00 · 600 r.');
 assert.equal(formatEffectTime({remaining:2.1,rounds:1}),'3 s · 1 r.');
 assert.equal(formatEffectTime({remaining:null,rounds:null}),'aktywne');
});
test('mana budget UI names mixed slot distribution and flexible pool',()=>{
 const {manaBudgetText}=require('../web/runtime.js');
 const text=manaBudgetText({base:140,bonus:0,slots:[4,2],shared:true});
 assert(text.includes('140'));assert(text.includes('4× krąg 1'));assert(text.includes('2× krąg 2'));
 assert(text.toLowerCase().includes('wspólna'));
});

test('spell profile overlays owner scaling without mutating the shared catalogue',()=>{
 const {spellProfile}=require('../web/runtime.js');
 const spec={id:'magic_missile',name:'Magiczny pocisk',mana:20,shots:3,dice:[1,4,1]};
 const p={spell_profiles:{magic_missile:{mana:50,shots:5,cast_circle:3,power_summary:'5 × 1k4+1'}}};
 const value=spellProfile(spec,p);
 assert.equal(value.mana,50);assert.equal(value.shots,5);assert.equal(value.name,spec.name);
 assert.equal(spec.mana,20);assert.equal(spec.shots,3);assert.notEqual(value,spec);
});
test('hotbar mana uses selected casting rank, never static base spell cost',()=>{
 const {spellMana}=require('../web/runtime.js');
 const s={id:'magic_missile',mana:20};
 assert.equal(spellMana(s,{spell_profiles:{magic_missile:{mana:130}}}),130);
 assert.equal(spellMana(s,{spell_profiles:{magic_missile:{mana:20}}}),20);
 assert.equal(spellMana({id:'fire_bolt',mana:0},{spell_profiles:{fire_bolt:{mana:0}}}),0);
});
test('repeating active concentration is free, other spell costs remain payable',()=>{
 const {spellMana}=require('../web/runtime.js');
 const p={concentration:'call_lightning',spell_profiles:{call_lightning:{mana:90},magic_missile:{mana:90}}};
 assert.equal(spellMana({id:'call_lightning',mana:50,recast:true},p),0);
 assert.equal(spellMana({id:'magic_missile',mana:20},p),90);
 p.concentration='';assert.equal(spellMana({id:'call_lightning',mana:50,recast:true},p),90);
});
test('missing locked spell profile falls back to a safe base and empty slots stay empty',()=>{
 const {spellProfile,spellMana}=require('../web/runtime.js');
 assert.equal(spellProfile(null,{}),null);assert.equal(spellMana(undefined,{}),0);
 assert.deepEqual(spellProfile({id:'fireball',mana:50},{}),{id:'fireball',mana:50});
});
test('owner delta replaces spell profiles completely and never leaks them across accounts',()=>{
 const p={id:'1',spell_profiles:{magic_missile:{shots:4,mana:30}}};
 const next=mergeOwner(p,{id:'1',hp:10},true);assert.equal(next.spell_profiles.magic_missile.shots,4);
 assert.deepEqual(mergeOwner(next,{id:'1',spell_profiles:{}},true).spell_profiles,{});
 assert.equal(mergeOwner(next,{id:'2'},true).spell_profiles,undefined);
});
