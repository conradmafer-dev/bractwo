const test=require('node:test'),assert=require('node:assert/strict');
const ui=require('../web/loot_ui.js');
test('Polish drop chance percentages',()=>{assert.equal(ui.percent(.05),'5%');assert.equal(ui.percent(.015),'1,5%');assert.equal(ui.percent(.008),'0,8%');assert.equal(ui.percent(1),'100%');});
test('Loot preview uses canonical item and unconditional chance',()=>{const rows=ui.entries({loot:{entries:[{kind:'item',template:'wand',chance:.05}]}},{items:{wand:{name:'Różdżka',chance:999,icon:'wand.svg'}},potions:{}});assert.equal(rows[0].name,'Różdżka');assert.equal(rows[0].chance,.05);assert.equal(rows[0].icon,'wand.svg');});
test('Potion previews use potion catalog',()=>assert.equal(ui.entries({loot:{entries:[{kind:'potion',template:'heal',chance:.04}]}},{potions:{heal:{name:'Mikstura'}}})[0].name,'Mikstura'));
test('Unknown species has no invented drops',()=>assert.deepEqual(ui.entries({},{}),[]));
test('Atlas frame is always bounded for normal movement',()=>{for(let m=0;m<1000;m+=.03)assert.ok(ui.frame(m)>=0&&ui.frame(m)<4);});
test('Atlas idle and invalid movement safe default',()=>{assert.equal(ui.frame(0),0);assert.equal(ui.frame(-10),0);assert.equal(ui.frame(undefined),0);});
test('Atlas four walking frames loop in order',()=>assert.deepEqual([0,.34,.67,1,1.34].map(x=>ui.frame(x)),[0,1,2,3,0]));
