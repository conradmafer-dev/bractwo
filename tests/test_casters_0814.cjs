const test=require('node:test'),assert=require('node:assert/strict');
const {canChoose}=require('../web/caster_ui.js');const {facts}=require('../web/inventory_ui.js');
const druid=(extra={})=>({class_id:'druid',alive:true,form:'',combat_remaining:0,character_sheet:{caster:{order:''}},...extra});
test('first druid path does not require a master',()=>assert(canChoose(druid(),false)));
test('reselection requires master',()=>{const p=druid({character_sheet:{caster:{order:'warden'}}});assert(!canChoose(p,false));assert(canChoose(p,true));});
test('dead, combat, transformed and non-druid cannot pick path',()=>{for(const p of [druid({alive:false}),druid({form:'cat'}),druid({combat_remaining:1}),druid({class_id:'mage'})])assert(!canChoose(p,true));});
test('simple and martial labels; no third/exotic fallback',()=>{for(const [cat,label] of [['simple','Prosta'],['martial','Żołnierska']])assert(facts({slot:'weapon',weapon_name:'Łuk',weapon_category:cat})[0].endsWith(label));});
test('proficient weapon has no redundant affirmative proficiency row',()=>assert(!facts({slot:'weapon',preview:{proficient:true,proficiency:2}}).some(s=>s.includes('biegło'))));
test('missing weapon training shown once, does not subtract from actual attack twice',()=>{let x=facts({slot:'weapon',preview:{proficient:false,proficiency:2,attack:2,dice:'1k8+2'}});assert(x.includes('Brak biegłości: −2 do trafienia'));assert(x.includes('Atak  1k20+2'));});
test('personalized zero spell bonus overrides staff nominal focus bonus for noncasters',()=>assert(!facts({slot:'weapon',spell_bonus:2,preview:{spell_bonus:0}}).some(s=>s.startsWith('Czary:'))));
test('mastery lock independent of proficiency',()=>{let x=facts({slot:'weapon',mastery_name:'Osłabienie',preview:{proficient:true,mastery_active:false}});assert(x.includes('Mistrzostwo  Osłabienie 🔒'));});
test('armor shows actual wearer AC and warns about missing training',()=>{let x=facts({slot:'armor',armor_kind:'medium',preview:{ac:14,armor_penalty:true}});assert(x.includes('Twoja KP  14'));assert(x.some(s=>s.includes('bez czarów')));});
test('untrained shield explicitly denies AC bonus',()=>{let x=facts({slot:'shield',shield_ac:2,preview:{ac:12,untrained_shield:true}});assert(x.includes('Brak wyszkolenia — bez premii KP'));});
test('tooltip text remains text not injected HTML',()=>{let x=facts({slot:'weapon',sources:[{name:'<img src=x onerror=attack()>'}]});assert.equal(x.at(-1),'Zdobyto: <img src=x onerror=attack()>');const fs=require('fs');assert(fs.readFileSync(require.resolve('../web/inventory_ui.js'),'utf8').includes('e.textContent=text'));});

require('../web/character_sheet.js');
test('shared staff and bow artwork follows type rather than former class restriction',()=>{const icon=globalThis.BractwoCharacterSheet.equipmentIcon;const all=['knight','ranger','mage','druid'];assert.equal(icon({weapon_type:'quarterstaff',class_ids:all},'weapon'),'assets/equipment/nature_staff.svg');assert.equal(icon({weapon_type:'longbow',class_ids:all},'weapon'),'assets/equipment/bow.svg');assert.equal(icon({weapon_type:'longsword',class_ids:all},'weapon'),'assets/equipment/weapon.svg');assert.equal(icon({icon:'assets/equipment/root_staff.svg',weapon_type:'quarterstaff'},'weapon'),'assets/equipment/root_staff.svg');});
test('untrained armor warning renders the message, not its CSS class',()=>{const fs=require('fs'),s=fs.readFileSync(require.resolve('../web/character_sheet.js'),'utf8');assert(s.includes("node('p','caster-status-warning','Brak wyszkolenia w pancerzu:"));});
