'use strict';
const assert=require('node:assert/strict'),{test}=require('node:test'),{execFileSync}=require('node:child_process');
const path=require('node:path');
globalThis.BractwoRuntime=require('../web/runtime.js');
require('../web/character_sheet.js');
const {spellSections}=globalThis.BractwoCharacterSheet;
const player=(extra={})=>({class_id:'druid',level:18,spell_profiles:{},...extra});
const spell=(id,circle,min_level=1,extra={})=>({id,name:id,circle,min_level,class_ids:['druid'],...extra});
const sectionIds=sections=>sections.map(s=>s.id);
const spellIds=sections=>sections.flatMap(s=>s.entries.map(e=>e.id));
const groupFor=(sections,id)=>sections.find(s=>s.entries.some(e=>e.id===id))?.id;
const sample={spells:{
 shillelagh:spell('shillelagh',0),
 healing_word:spell('healing_word',1),
 wild_shape_wolf:spell('wild_shape_wolf',0,5,{feature:true}),
 moonbeam:spell('moonbeam',2,10),
 guidance:spell('guidance',0,10,{class_ids:[],name:'Wskazówki'}),
 guiding_bolt:spell('guiding_bolt',1,10,{class_ids:[],name:'Wiodący pocisk'}),
 circle_star_archer:spell('circle_star_archer',0,10,{feature:true}),
 wild_shape_bear:spell('wild_shape_bear',0,35,{feature:true}),
 sunburst:spell('sunburst',8,70),
}};
const star=()=>player({spell_profiles:{guidance:{available:true,required_level:10},guiding_bolt:{available:true,required_level:10,cast_circle:2,mana:30}}});

test('late-granted cantrips and circle-I spells stay in the first matching section',()=>{
 const sections=spellSections(sample,star());
 assert.deepEqual(sectionIds(sections),['circle-0','circle-1','circle-2','circle-8','features']);
 assert.equal(groupFor(sections,'guidance'),'circle-0');assert.equal(groupFor(sections,'guiding_bolt'),'circle-1');
 assert.equal(sections[0].label,'Sztuczki');assert.equal(sections[1].label,'Krąg I');
});
test('class features are in one final section, never between spell circles',()=>{
 const sections=spellSections(sample,star());const features=sections.at(-1);
 assert.equal(features.label,'Zdolności klasy');assert.deepEqual(features.entries.map(e=>e.id),['wild_shape_wolf','circle_star_archer','wild_shape_bear']);
 assert.equal(sections.filter(s=>s.id==='features').length,1);
});
test('upcasting cannot move a base circle-I spell to circle-II or create a new group',()=>{
 const p=star(),before=sectionIds(spellSections(sample,p));p.spell_profiles.guiding_bolt.cast_circle=9;
 const sections=spellSections(sample,p);assert.deepEqual(sectionIds(sections),before);
 assert.equal(groupFor(sections,'guiding_bolt'),'circle-1');assert.equal(sections[1].entries.find(e=>e.id==='guiding_bolt').spec.cast_circle,9);
});
test('the catalogue is the authority for section rank even with a profile override',()=>{
 const p=star();p.spell_profiles.guiding_bolt.circle=7;
 assert.equal(groupFor(spellSections(sample,p),'guiding_bolt'),'circle-1');
});
test('spells are alphabetic inside each circle using Polish collation',()=>{
 const world={spells:Object.fromEntries(['Żar','Łaska','Dębowa skóra','Zbroja','Ąka'].map((name,i)=>['s'+i,spell('s'+i,2,10,{name})]))};
 assert.deepEqual(spellSections(world,player())[0].entries.map(e=>e.spec.name),['Ąka','Dębowa skóra','Łaska','Zbroja','Żar']);
});
test('class plus subclass access creates only one row, not two copies',()=>{
 const p=player({spell_profiles:{moonbeam:{available:true,required_level:5}}});
 const sections=spellSections(sample,p);assert.equal(spellIds(sections).filter(id=>id==='moonbeam').length,1);
});
test('visibility and locked-state rules are preserved, and unrelated classes stay hidden',()=>{
 const p=player({level:1,spell_profiles:{moonbeam:{available:false},guidance:{available:false}}});
 const sections=spellSections({...sample,spells:{...sample.spells,fireball:spell('fireball',3,20,{class_ids:['mage']})}},p);
 assert(!spellIds(sections).includes('fireball'));assert(!spellIds(sections).includes('guidance'));
 assert.equal(sections.find(s=>s.id==='circle-2').entries[0].unlocked,false);
});
test('empty or incomplete state does not create empty sections or fail',()=>{
 assert.deepEqual(spellSections({},null),[]);assert.deepEqual(spellSections({},player()),[]);
 assert.deepEqual(spellSections({spells:{broken:null,missing:{id:'missing'}}},player()),[]);
});
test('building sections never mutates the catalogue, profiles or saved hotbar',()=>{
 const p=star();p.hotbar=['moonbeam','guidance'];p.grouped_hotbar=['group_starry_form','moonbeam'];
 const before=JSON.stringify([p,sample]);spellSections(sample,p);assert.equal(JSON.stringify([p,sample]),before);
});

// Real server catalogue/profiles at all representative class and subclass gates.
const fixture=JSON.parse(execFileSync('python',['-c',`
import json
from server.server import Player
from server import dnd_content as d, spell_scaling as s, druid_circles as c
samples=[]
variants=[('druid','',None),('druid','stars',None),('druid','moon',None),('druid','sea',None)]
variants += [('druid','land',land) for land in c.LANDS]
variants += [('mage','',None),('ranger','',None),('knight','',None)]
for cls,circle,land in variants:
 for level in (1,10,18,20,45,80,100):
  p=Player('1','SpellbookQA',class_id=cls,level=level);p.current_wall_time=1000;p.druid_circle=circle
  if land:c.state(p)['land']=land
  profiles=s.client_profiles(p)
  expected=[key for key,spec in d.SPELLS.items() if cls in spec['class_ids'] or profiles[key].get('available') is True]
  samples.append(dict(name=f'{cls}/{circle or "base"}/{land or ""}/{level}',player=dict(class_id=cls,level=level,spell_profiles=profiles),expected=expected))
print(json.dumps(dict(world=dict(spells=d.SPELLS),samples=samples)))
`],{cwd:path.resolve(__dirname,'..'),encoding:'utf8',maxBuffer:32*1024*1024}));
for(const sample of fixture.samples)test('production catalogue: '+sample.name,()=>{
 const sections=spellSections(fixture.world,sample.player),rows=spellIds(sections),ids=sectionIds(sections);
 assert.equal(new Set(ids).size,ids.length);assert.equal(new Set(rows).size,rows.length);
 assert.deepEqual(rows.slice().sort(),sample.expected.slice().sort());
 assert.deepEqual(sections.map(s=>s.rank),sections.map(s=>s.rank).sort((a,b)=>a-b));
 for(const section of sections)for(const row of section.entries){
  const base=fixture.world.spells[row.id];assert.equal(section.id,base.feature?'features':'circle-'+base.circle);
 }
});
