const {test}=require('node:test'),assert=require('node:assert/strict');
const {rowText}=require('../web/level_up.js');const {mergeOwner}=require('../web/runtime.js');
test('single line only contains name and the gained HP',()=>assert.equal(rowText({label:'HP',gain:'+1'}),'HP +1'));
test('each saving throw can be shown independently',()=>assert.equal(rowText({label:'Rzut obronny: Mądrość',gain:'+1'}),'Rzut obronny: Mądrość +1'));
test('movement delta retains its units and decimal comma',()=>assert.equal(rowText({label:'Ruch',gain:'+0,43',unit:'stopy / rundę'}),'Ruch +0,43 stopy / rundę'));
test('spell unlock is a gain, not before and after',()=>assert.equal(rowText({label:'Nowy czar',gain:'+ Kula ognia'}),'Nowy czar + Kula ognia'));
test('compact owner state preserves pending receipts until changed',()=>{const p={id:'1',pending_level_ups:[{id:'a:10'}]};assert.deepEqual(mergeOwner(p,{id:'1',hp:2},true).pending_level_ups,p.pending_level_ups);});
test('authoritative empty queue clears receipt history',()=>{const p={id:'1',pending_level_ups:[{id:'a:10'}]};assert.deepEqual(mergeOwner(p,{id:'1',pending_level_ups:[]},true).pending_level_ups,[]);});
