'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {areaContains,missilePoint,draw}=require('../web/spell_vfx.js');
const Runtime=require('../web/runtime.js');
const fixtures=JSON.parse(execFileSync('python',['-c',`
import json
from types import SimpleNamespace as P
from server.dnd_content import SPELLS
from server.spell_geometry import build,contains
p=P(x=0,y=0,facing=[1,0]);t=P(x=80,y=0)
rows=[]
for key,s in SPELLS.items():
 a=build(s,p,t)
 samples=[[x,y,contains(a,x,y)] for x in range(-96,740,19) for y in range(-70,200,23)]
 rows.append(dict(key=key,spec=s,area=a,samples=samples))
print(json.dumps(rows))
`],{cwd:require('node:path').resolve(__dirname,'..'),encoding:'utf8'}));
test('physical row one uses digits 1..0, Minus and Equal',()=>{
 for(const [i,k]of ['Digit1','Digit2','Digit3','Digit4','Digit5','Digit6','Digit7','Digit8','Digit9','Digit0','Minus','Equal'].entries())assert.equal(Runtime.hotbarSlotForCode(k),i);
 assert.equal(Runtime.hotbarSlotForCode('Numpad1'),-1);
});
test('F1..F12 occupy row two while adaptive F is not a slot',()=>{
 for(let i=1;i<=12;i++)assert.equal(Runtime.hotbarSlotForCode('F'+i),11+i);
 assert.equal(Runtime.hotbarSlotForCode('KeyF'),-1);assert.equal(Runtime.hotbarSlotForCode('KeyC'),-1);
});
test('labels remain correct for second row and overflow bank',()=>{
 assert.equal(Runtime.hotbarLabel(8),'9');assert.equal(Runtime.hotbarLabel(9),'0');
 assert.equal(Runtime.hotbarLabel(11),'=');assert.equal(Runtime.hotbarLabel(12),'F1');assert.equal(Runtime.hotbarLabel(23),'F12');
 assert(Runtime.hotbarLabel(24).includes('2'));assert(Runtime.hotbarLabel(47).includes('F12'));
});
test('all rendered shapes agree with Python geometry at sampled boundaries',()=>{
 for(const f of fixtures)for(const [x,y,inside]of f.samples)assert.equal(areaContains(f.area,x,y),inside,`${f.key}: ${x},${y}`);
});
test('three missiles take distinct curved paths and converge at one target',()=>{
 const a=[10,30],b=[210,30],middle=[];
 for(let i=0;i<3;i++){assert.deepEqual(missilePoint(a,b,0,i),a);assert.deepEqual(missilePoint(a,b,1,i),b);middle.push(missilePoint(a,b,.5,i));}
 assert.equal(new Set(middle.map(p=>p[1])).size,3);assert(middle.some(p=>p[1]<30));assert(middle.some(p=>p[1]>30));
});
test('missiles do not produce NaN when actor positions coincide',()=>{
 for(let i=0;i<3;i++)for(const t of [0,.2,.5,1])assert(missilePoint([1,1],[1,1],t,i).every(Number.isFinite));
});
function context(){let depth=0,calls=0;
 const methods={save(){depth++;},restore(){assert(depth>0);depth--;},createRadialGradient(){return {addColorStop(){}};},createLinearGradient(){return {addColorStop(){}};},depth:()=>depth,calls:()=>calls};
 return new Proxy(methods,{get(o,k){if(k in o)return o[k];return (...args)=>{calls++;for(const a of args)if(typeof a==='number')assert(Number.isFinite(a),k);};},set(o,k,v){o[k]=v;return true;}});
}
test('every current spell draws valid canvas commands and balances save/restore',()=>{
 for(const f of fixtures)for(const t of [0,.1,.5,.8,.999]){
  const ctx=context(),e={kind:'spell',spell_id:f.key,x:0,y:0,target_x:80,target_y:0,visual:f.spec.visual,shots:f.spec.shots||1,targets:[{x:80,y:0},{x:100,y:40}],persistent:f.spec.kind==='field'};
  if(f.spec.area||f.spec.party)e.area=f.area;
  assert.equal(draw(ctx,e,t,1000),true,f.key);assert.equal(ctx.depth(),0,f.key);assert(ctx.calls()>0,f.key);
 }
});
test('legacy effects remain with the existing renderer',()=>assert.equal(draw(context(),{kind:'arrow'},.5),false));

test('all upcast magic missiles have separate curves and converge on the target',()=>{
 for(let total=4;total<=11;total++){
  const paths=[];
  for(let i=0;i<total;i++){
   assert.deepEqual(missilePoint([10,30],[210,30],0,i,total),[10,30]);
   assert.deepEqual(missilePoint([10,30],[210,30],1,i,total),[210,30]);
   paths.push(missilePoint([10,30],[210,30],.5,i,total)[1]);
  }
  assert.equal(new Set(paths).size,total);
 }
});
test('eleven coincident-origin missiles remain finite at all animation phases',()=>{
 for(let i=0;i<11;i++)for(const t of [0,.1,.5,.85,1])assert(missilePoint([1,1],[1,1],t,i,11).every(Number.isFinite));
});
test('scaled missile volleys and scorching rays draw all animation phases without canvas imbalance',()=>{
 for(const key of ['magic_missile','scorching_ray'])for(const shots of [3,4,7,10,11])for(const t of [.05,.3,.65,.95]){
  const f=fixtures.find(f=>f.key===key),ctx=context();
  assert(draw(ctx,{kind:'spell',spell_id:key,x:0,y:0,target_x:180,target_y:40,shots,visual:{...f.spec.visual,shots},targets:[{x:180,y:40}]},t,1000));
  assert.equal(ctx.depth(),0);assert(ctx.calls()>0);
 }
});
