'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const Runtime=require('../web/runtime.js');
const VFX=require('../web/spell_vfx.js');
const fs=require('node:fs');
const path=require('node:path');
function ctx(){let depth=0,calls=0;const x={save(){depth++;},restore(){assert(depth>0);depth--;},createRadialGradient(){return{addColorStop(){}}},depth:()=>depth,calls:()=>calls};return new Proxy(x,{get(o,k){if(k in o)return o[k];return(...args)=>{calls++;for(const v of args)if(typeof v==='number')assert(Number.isFinite(v),k)}},set(o,k,v){o[k]=v;return true}})}
test('Ranger uses per-class authoritative unlocks, including level-five Longstrider',()=>{
 assert.equal(Runtime.spellGate({circle:1,min_level:1,class_levels:{ranger:5}},{class_id:'ranger'}),5);
 assert.equal(Runtime.spellGate({circle:1,min_level:1,class_levels:{druid:1,ranger:5}},{class_id:'druid'}),1);
 assert.equal(Runtime.spellGate({circle:2,min_level:10,class_levels:{ranger:20}},{class_id:'ranger'}),20);
});
test('Concentration warning distinguishes preparation from immediate replacement',()=>{
 const spells={hunters_mark:{name:'Znak łowcy'}};
 assert.equal(Runtime.concentrationWarning({id:'ensnaring_strike',kind:'weapon_trigger',concentration:true},{concentration:'hunters_mark'},spells),'Po trafieniu zastąpi: Znak łowcy');
 assert.equal(Runtime.concentrationWarning({id:'cure_wounds',kind:'heal'},{concentration:'hunters_mark'},spells),'');
});
test('Live ranger overlays are balanced and finite at all actor scales',()=>{
 for(const size of [.2,1,1.85,3])for(const t of [0,.2,5000]){
  const c=ctx();VFX.drawStatuses(c,[{id:'hunters_mark:1',spell_id:'hunters_mark'},{id:'restrained',spell_id:'ensnaring_strike'}],17,23,t,size);
  assert.equal(c.depth(),0);assert(c.calls()>10);
 }
});
test('Caster concentration and armed intent never draw target overlays on caster',()=>{
 const c=ctx();VFX.drawStatuses(c,[{id:'concentration',spell_id:'hunters_mark'},{id:'ensnaring_ready',spell_id:'ensnaring_strike'}],0,0);
 assert.equal(c.calls(),0);assert.equal(c.depth(),0);
});
test('Same target with multiple marks renders one readable symbol',()=>{
 const one=ctx(),two=ctx();VFX.drawStatuses(one,[{id:'hunters_mark:1',spell_id:'hunters_mark'}],0,0);
 VFX.drawStatuses(two,[{id:'hunters_mark:1',spell_id:'hunters_mark'},{id:'hunters_mark:2',spell_id:'hunters_mark'}],0,0);
 assert.equal(one.calls(),two.calls());
});
test('No live conditions means no lingering graphic',()=>{
 const c=ctx();VFX.drawStatuses(c,[],0,0);VFX.drawStatuses(c,null,0,0);assert.equal(c.calls(),0);
});
test('New spell uses the same distinct vector icon in both clients',()=>{
 const root=path.resolve(__dirname,'..'),a=fs.readFileSync(path.join(root,'web/assets/spells/ensnaring_strike.svg'));
 assert.equal(a.toString(),fs.readFileSync(path.join(root,'client/assets/spells/ensnaring_strike.svg')).toString());
 assert.notEqual(a.toString(),fs.readFileSync(path.join(root,'web/assets/spells/entangle.svg')).toString());
});
