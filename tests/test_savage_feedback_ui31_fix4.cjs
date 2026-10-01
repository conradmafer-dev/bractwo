'use strict';
const {test}=require('node:test'), assert=require('node:assert/strict');
const R=require('../web/runtime.js');
const roll=(extra={})=>({id:1,time:10,check:'attack',action:'Atak',target_name:'Szczur',roll:15,rolls:[15],bonus:5,total:20,defense:12,hit:true,damage_dice:'1k8+3',damage:9,savage_attacker:true,savage_damage_rolls:[[2],[6]],savage_chosen:1,...extra});
test('both real rolls and the authoritative selection are visible',()=>{
 const d=R.savageAttackDetails(roll());assert.deepEqual(d.sets.map(s=>s.dice),[[2],[6]]);assert.equal(d.chosen,1);
 const s=R.combatSummary(roll());assert.match(s,/1k20 = 15/);assert.match(s,/Rzut 1: 1k8 = 2/);assert.match(s,/Rzut 2: 1k8 = 6 ✓ wybrany/);assert.match(s,/Obrażenia: 6 \+ 3 → 9/);
});
test('first stays selected when second is worse',()=>{assert.match(R.savageAttackSummary(roll({savage_damage_rolls:[[7],[2]],savage_chosen:0})),/Rzut 1: 1k8 = 7 ✓ wybrany/);});
test('equal rolls still display both and select only the server winner',()=>{const d=R.savageAttackDetails(roll({savage_damage_rolls:[[4],[4]],savage_chosen:0}));assert.equal(d.sets.filter(s=>s.selected).length,1);assert.equal(d.sets[0].selected,true);});
test('critical and multi-die weapons show entire sets, not a best-die mixture',()=>{const r=roll({critical:true,savage_damage_rolls:[[1,2,3,4],[6,5,4,3]]});const s=R.combatSummary(r);assert.match(s,/KRYTYK/);assert.match(s,/1 \+ 2 \+ 3 \+ 4 = 10/);assert.match(s,/6 \+ 5 \+ 4 \+ 3 = 18/);});
test('style-adjusted lower raw sum is visibly explained without recomputing the winner',()=>{
 const r=roll({savage_damage_rolls:[[1,6],[4,4]],savage_scored_rolls:[[3,6],[4,4]],savage_chosen:0});
 assert.match(R.savageAttackSummary(r),/1 \+ 6 → 3 \+ 6 = 9 ✓ wybrany/);
 assert.equal(R.savageAttackDetails(r).sets[1].total,8);
});
test('old server receipts without scored dice stay compatible',()=>{assert.equal(R.savageAttackDetails(roll()).sets[0].adjusted,false);});
test('misses, spells and invalid receipts do not invent a second roll',()=>{
 for(const extra of [{hit:false},{check:'save'},{savage_attacker:false},{savage_damage_rolls:[]},{savage_chosen:2},{savage_damage_rolls:[[2],['6']]},{savage_damage_rolls:[[2],[6,7]]}])assert.equal(R.savageAttackDetails(roll(extra)),null);
});
test('spell riders and final reductions are separate from the weapon dice comparison',()=>{const s=R.combatSummary(roll({damage_dice:'1k8+3 + 1k6 (Znak)',mark_rolls:[4],damage:6}));assert.match(s,/Rzut 1: 1k8 = 2/);assert.match(s,/Rzut 2: 1k8 = 6/);assert.match(s,/Znak łowcy: 1k6 = 4.*6 obr/);});
test('Horde Breaker cannot overwrite the feat receipt',()=>{
 const first=roll(),second=roll({id:2,action:'Rozbijacz hord',target_name:'Drugi szczur',savage_attacker:false});
 const p={id:'a',last_roll:second,combat_log:[first,second]};assert.deepEqual(R.combatNoticeEntries(p,10).map(r=>r.id),[1,2]);
});
test('extra attacks, saving throws and concentration keep only one newest feat plus latest result',()=>{
 const first=roll(),newer=roll({id:3,time:13}),latest={id:4,time:13,check:'concentration'};
 assert.deepEqual(R.combatNoticeEntries({last_roll:latest,combat_log:[first,newer,latest]},13).map(r=>r.id),[3,4]);
});
test('no duplicate display for an identical latest roll and no stale history',()=>{
 const p={last_roll:roll(),combat_log:[roll()]};assert.equal(R.combatNoticeEntries(p,10).length,1);
 assert.deepEqual(R.combatNoticeEntries({...p,last_roll:{}},18),[]);assert.deepEqual(R.combatNoticeEntries(null,10),[]);
});
test('unknown simulation clock never revives old history',()=>{assert.deepEqual(R.combatNoticeEntries({last_roll:{},combat_log:[roll()]},undefined),[]);});
