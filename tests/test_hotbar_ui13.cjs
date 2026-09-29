'use strict';
const assert=require('node:assert/strict'),{test}=require('node:test');
const Runtime=require('../web/runtime.js');
globalThis.BractwoRuntime=Runtime;
const Hotbar=require('../web/hotbar_ui.js');
const world={hotbar_groups:{group_starry_form:{name:'Gwiezdna postać',members:['circle_star_archer','circle_star_chalice','circle_star_dragon','circle_star_arrow']}},spells:{}};
for(const id of world.hotbar_groups.group_starry_form.members)world.spells[id]={id,kind:'druid_circle',name:id,mana:0,min_level:10};
function player(){return {level:15,hp:30,alive:true,mana:100,hotbar:['circle_star_archer'],grouped_hotbar:['group_starry_form'],spell_profiles:Object.fromEntries(Object.keys(world.spells).map(id=>[id,{available:id!=='circle_star_arrow',resource_cost:1,uses_remaining:0,uses_maximum:2}]))};}
test('grouped projection and book refer to the same slot',()=>{
 const p=player();assert.deepEqual(Runtime.displayHotbar(p),['group_starry_form']);
 assert.equal(Runtime.hotbarGroupForSpell('circle_star_dragon',world),'group_starry_form');
 assert.equal(Runtime.hotbarGroupForSpell('cure_wounds',world),'cure_wounds');
 delete p.grouped_hotbar;assert.deepEqual(Runtime.displayHotbar(p),p.hotbar);
});
test('exhausted transformations are disabled, zero-cost arrow and switch remain valid',()=>{
 const p=player(),s=world.spells.circle_star_chalice;
 assert.equal(Runtime.spellUsable(s,p),false);
 p.spell_profiles[s.id].resource_cost=0;assert.equal(Runtime.spellUsable(s,p),true);
 p.spell_profiles[s.id].already_active=true;assert.equal(Runtime.spellUsable(s,p),false);
 p.spell_profiles[s.id]={available:true,resource_cost:2,uses_remaining:1};assert.equal(Runtime.spellUsable(s,p),false);
});
test('archer main button is an arrow, not another activation',()=>{
 const p=player();assert.equal(Hotbar.groupState('group_starry_form',p,world).primary,null);
 p.circle_visual={starry_form:'archer'};p.spell_profiles.circle_star_arrow={available:true,resource_cost:0};
 const active=Hotbar.groupState('group_starry_form',p,world);
 assert.equal(active.primary.id,'circle_star_arrow');assert.equal(active.label,'Gwiezdna strzała');
 assert.equal(Runtime.spellUsable(active.primary,p),true);
});
test('resource cost text is distinct from zero mana',()=>{
 const p=player(),s=world.spells.circle_star_chalice;p.spell_profiles[s.id].resource_name='Dziki kształt';
 assert.match(Runtime.spellCostText(s,p),/Dziki kształt.*koszt 1.*0\/2/);
 p.spell_profiles[s.id].resource_cost=0;assert.match(Runtime.spellCostText(s,p),/Bez many i użyć/);
});
