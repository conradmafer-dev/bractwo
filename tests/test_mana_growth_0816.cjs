const test=require('node:test');
const assert=require('node:assert/strict');
const {manaBudgetText,spellProfile}=require('../web/runtime.js');
const {rowText}=require('../web/level_up.js');

test('intermediate pool tooltip does not equate smooth mana with old slots',()=>{
 const text=manaBudgetText({base:84,bonus:0,slots:[3],shared:true,progression:'per_level',next_level_gain:12,slots_are_reference:true});
 assert(text.includes('84'));assert(text.includes('+12 many'));assert(text.includes('Wspólna mana'));
 assert(!text.includes('3×'));assert(!text.includes('odpowiednik'));
});
test('focus remains a separate bonus in the mana tooltip',()=>{
 const text=manaBudgetText({base:84,bonus:12,progression:'per_level',next_level_gain:12});
 assert(text.includes('84 many + 12 premii'));
});
test('knight tooltip has real pool and no imaginary next gain',()=>{
 const text=manaBudgetText({base:30,bonus:0,slots:[],progression:'per_level',next_level_gain:0});
 assert(text.includes('30 many'));assert(!text.includes('Następny'));assert(!text.includes('+0'));
});
test('end cap tooltip does not promise further mana',()=>{
 const text=manaBudgetText({base:1330,bonus:0,progression:'per_level',next_level_gain:0});
 assert(text.includes('1330'));assert(!text.includes('Następny'));
});
test('award lines show only each earned delta',()=>{
 assert.equal(rowText({label:'Mana',gain:'+12'}),'Mana +12');
 assert.equal(rowText({label:'Odzyskanie mocy',gain:'+2',unit:'many'}),'Odzyskanie mocy +2 many');
});
test('hotbar spell profile uses the server intermediate recovery amount',()=>{
 const spec={id:'arcane_recovery',mana:0,cooldown:180};
 const p={spell_profiles:{arcane_recovery:{restore_mana:29,power_summary:'+29 many',next_upgrade:'Poziom 6: +2 many'}}};
 const s=spellProfile(spec,p);assert.equal(s.restore_mana,29);assert.equal(s.cooldown,180);assert.equal(s.mana,0);
 assert.equal(spec.restore_mana,undefined);
});
