'use strict';
const assert=require('node:assert/strict');
const {test}=require('node:test');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');

// Run the shipped controls, reminders and durable receipts against an actual
// stateful DOM fixture. No browser dependency or replica of selection logic.
function fixture(initial){
 let document;
 class Element{
  constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attributes={};this.listeners=new Map();this.className='';this.hidden=false;this.disabled=false;this.value='';this.scrollTop=0;this.clientWidth=320;this.clientHeight=220;this.offsetHeight=130;this.style={};this.isConnected=true;this._text='';this.classList={toggle:(key,on)=>{const classes=new Set(this.className.split(/\s+/).filter(Boolean));if(on)classes.add(key);else classes.delete(key);this.className=[...classes].join(' ');},add:key=>{this.className+=' '+key;}};}
  get textContent(){return this._text+this.children.map(x=>x.textContent||'').join('');}
  set textContent(value){this._text=String(value??'');this.children=[];}
  get childNodes(){return this.children;}get parentElement(){return this.parentNode;}get firstChild(){return this.children[0];}get lastChild(){return this.children.at(-1);}
  append(...children){for(const child of children){if(child.parentNode){const old=child.parentNode.children;old.splice(old.indexOf(child),1);}child.parentNode=this;this.children.push(child);if(this.tagName==='SELECT'&&this.children.length===1)this.value=child.value;}}
  prepend(...children){this.children.unshift(...children);for(const child of children)child.parentNode=this;}
  replaceChildren(...children){for(const child of this.children)child.parentNode=null;this.children=[];this._text='';this.append(...children);}
  remove(){if(this.parentNode){const old=this.parentNode.children;old.splice(old.indexOf(this),1);this.parentNode=null;}}
  after(...elements){if(!this.parentNode)return;const parent=this.parentNode,index=parent.children.indexOf(this);parent.children.splice(index+1,0,...elements);for(const el of elements)el.parentNode=parent;}
  setAttribute(key,value){this.attributes[key]=String(value);}removeAttribute(key){delete this.attributes[key];}
  addEventListener(name,handler){this.listeners.set(name,handler);}
  contains(node){return this===node||this.children.some(child=>child.contains(node));}
  matches(selector){if(selector.startsWith('.'))return this.className.split(/\s+/).includes(selector.slice(1));const attribute=selector.match(/^\[data-([\w-]+)(?:="([^"]+)")?\]$/);if(attribute){const key=attribute[1].replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return key in this.dataset&&(attribute[2]===undefined||this.dataset[key]===attribute[2]);}return this.tagName===selector.toUpperCase();}
  querySelectorAll(selector){return this.children.flatMap(child=>[...(child.matches(selector)?[child]:[]),...child.querySelectorAll(selector)]);}
  querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
  focus(){document.activeElement=this;}blur(){if(document.activeElement===this)document.activeElement=null;}getClientRects(){return [{}];}
  click(){if(!this.disabled){const event={target:this,stopPropagation(){},preventDefault(){}};this.onclick?.(event);this.listeners.get('click')?.(event);}}
  change(value){this.value=value;this.listeners.get('change')?.({target:this});}
  scrollIntoView(){}
 }
 const ids={};for(const id of ['gameUI','hudLeftRail','characterPanel','characterContent','characterName','characterSubtitle','levelUpCascade','attackButton'])ids[id]=new Element('section');
 const panel=ids.characterPanel,content=ids.characterContent;panel.hidden=true;panel.append(content);const close=new Element('button');close.className='character-close';panel.append(close);
 for(const tab of ['inventory','stats','feats','abilities','skills','spells']){const b=new Element('button');b.dataset.characterTab=tab;panel.append(b);}
 for(const cls of ['level-up-viewport','level-up-layer','level-up-counter']){const el=new Element('div');el.className=cls;ids.levelUpCascade.append(el);}
 ids.gameUI.append(ids.hudLeftRail,panel,ids.levelUpCascade);const combat=new Element('div');combat.append(ids.attackButton);ids.gameUI.append(combat);
 document={activeElement:null,body:ids.gameUI,getElementById:id=>ids[id]||ids.gameUI.querySelectorAll('*').find(el=>el.id===id),createElement:tag=>new Element(tag),createTextNode:text=>{const e=new Element('text');e.textContent=text;return e;}};
 let player=initial,session=1;const sent=[],opened=[],context={document,innerWidth:420,addEventListener(){},localStorage:{getItem(){return null;},setItem(){}},Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}}};vm.createContext(context);
 for(const file of ['fighter_ui.js','caster_ui.js','skills_ui.js','level_up.js','inventory_ui.js','character_sheet.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web',file),'utf8'),context,{filename:file});
 const hooks={state:()=>({player,world:{}}),prepare(){},canTrade:()=>false,nearMaster:()=>false,send:packet=>sent.push(JSON.parse(JSON.stringify(packet))),cast(){},player:()=>player,session:()=>session,open:(...args)=>opened.push(args)};
 return {context,document,ids,content,hooks,sent,opened,player:()=>player,set(patch){player={...player,...patch};},sheet(patch){player={...player,character_sheet:{...player.character_sheet,...patch}};},session(n){session=n;},section(){return new Element('section');}};
}
const styles=['archery','blind_fighting','defense','dueling','great_weapon_fighting','interception','protection','thrown_weapon_fighting','two_weapon_fighting','unarmed_fighting','druidic_warrior'];
const cantrips=['produce_flame','starry_wisp','thorn_whip','shillelagh','guidance'].map(id=>({id,name:id,description:'Sztuczka '+id}));
function ranger(){return {id:'r1',name:'Łowca',class_id:'ranger',level:2,alive:true,form:'',combat_remaining:0,character_sheet:{fighter:{pending:true,style:'',required_level:2,can_change_style:false,choices:styles.map(id=>({id,name:id,description:id,requirement:'Wymagania sprzętu'})),cantrips,chosen_cantrips:[],masteries:[]},training:{points:0}}};}
function druid(){return {id:'d1',name:'Druid',class_id:'druid',level:7,alive:true,form:'',combat_remaining:0,character_sheet:{caster:{elemental_fury:{id:'',pending:true,required_level:7,upgrade_level:15,options:[{id:'potent_spellcasting',name:'Potężne sztuczki',description:'+ Mądrość',upgrade_description:'Większy zasięg'},{id:'primal_strike',name:'Pierwotne uderzenie',description:'1k8 raz na turę',upgrade_description:'2k8 raz na turę'}]}},training:{points:0}}};}

test('ranger picker browses all styles without sending, and requires two distinct Druidic cantrips',()=>{
 const f=fixture(ranger()),box=f.section();f.context.BractwoFighterUI.feats(box,f.player(),{...f.hooks,featSection:'ranger_style'});
 assert.equal(box.querySelectorAll('[data-style]').length,11);box.querySelector('[data-style="archery"]').click();assert.equal(f.sent.length,0);
 box.querySelector('[data-style="druidic_warrior"]').click();assert.equal(box.querySelector('[data-confirm-style]').disabled,true);
 box.querySelector('[data-style-cantrip="produce_flame"]').click();assert.equal(box.querySelector('[data-confirm-style]').disabled,true);
 box.querySelector('[data-style-cantrip="starry_wisp"]').click();assert.equal(box.querySelector('[data-confirm-style]').disabled,false);assert.equal(box.querySelector('[data-style-cantrip="guidance"]').disabled,true);
 box.querySelector('[data-confirm-style]').click();assert.deepEqual(f.sent,[{type:'fighting_style',style:'druidic_warrior',cantrips:['produce_flame','starry_wisp']}]);
});

test('fresh ranger state prevents late selection during combat, death or transformation and preserves knight picker',()=>{
 const f=fixture(ranger()),box=f.section();f.context.BractwoFighterUI.feats(box,f.player(),{...f.hooks,featSection:'ranger_style'});box.querySelector('[data-style="archery"]').click();const confirm=box.querySelector('[data-confirm-style]');
 for(const patch of [{combat_remaining:2},{combat_remaining:0,alive:false},{alive:true,form:'wolf'}]){f.set(patch);f.context.BractwoFighterUI.sync(box,f.player(),f.hooks);assert.equal(confirm.disabled,true);confirm.onclick();}
 assert.equal(f.sent.length,0);f.set({form:''});f.context.BractwoFighterUI.sync(box,f.player(),f.hooks);confirm.click();assert.deepEqual(f.sent,[{type:'fighting_style',style:'archery'}]);
 const k={class_id:'knight',alive:true,character_sheet:{fighter:{style:'dueling'}}};assert.equal(f.context.BractwoFighterUI.canChoose(k,false),false);assert.equal(f.context.BractwoFighterUI.canChoose(k,true),true);
});

test('Druidic replacement sends old/new spell only when gained-level allowance is still available',()=>{
 const p=ranger();p.level=3;Object.assign(p.character_sheet.fighter,{style:'druidic_warrior',pending:false,chosen_cantrips:['produce_flame','starry_wisp'],cantrip_replacement_available:true});
 const f=fixture(p),box=f.section();f.context.BractwoFighterUI.feats(box,p,{...f.hooks,featSection:'ranger_style'});const selects=box.querySelectorAll('select');selects[0].change('starry_wisp');selects[1].change('guidance');box.querySelector('[data-cantrip-replace]').click();assert.deepEqual(f.sent,[{type:'ranger_cantrip',old_spell:'starry_wisp',new_spell:'guidance'}]);
 f.sheet({fighter:{...p.character_sheet.fighter,cantrip_replacement_available:false}});f.context.BractwoFighterUI.sync(box,f.player(),f.hooks);assert.equal(box.querySelector('[data-cantrip-replace]').disabled,true);
});

test('Elemental Fury choice is explicitly confirmed, level-gated and independent from feat points',()=>{
 const f=fixture(druid()),box=f.section();f.context.BractwoCasterUI.elementalPanel(box,f.player(),f.hooks);box.querySelector('[data-elemental-choice="primal_strike"]').click();assert.equal(f.sent.length,0);assert.match(box.textContent,/2k8/);const confirm=box.querySelector('[data-elemental-confirm]');
 f.set({level:6});f.context.BractwoCasterUI.syncElemental(box,f.player());assert.equal(confirm.disabled,true);confirm.onclick();assert.equal(f.sent.length,0);
 f.set({level:7});f.context.BractwoCasterUI.syncElemental(box,f.player());confirm.click();assert.deepEqual(f.sent,[{type:'elemental_fury',choice:'primal_strike'}]);
});

test('Primal Strike element can change in combat and animal form without choosing the feature again',()=>{
 const p=druid();p.form='wolf';p.combat_remaining=12;Object.assign(p.character_sheet.caster.elemental_fury,{id:'primal_strike',pending:false,damage_type:'cold',damage_types:[{id:'cold',name:'Zimno'},{id:'fire',name:'Ogień'}]});
 const f=fixture(p),box=f.section();f.context.BractwoCasterUI.elementalPanel(box,p,f.hooks);const select=box.querySelector('[data-elemental-damage]');assert.equal(select.disabled,false);select.change('fire');const toggle=box.querySelector('[data-elemental-enabled]');assert.equal(toggle.checked,true);toggle.checked=false;toggle.change('');assert.deepEqual(f.sent,[{type:'elemental_damage_type',damage_type:'fire'},{type:'elemental_strike',enabled:false}]);assert.equal(box.querySelector('[data-elemental-confirm]'),null);
});

test('existing eligible players see a class-choice reminder on login and again after reconnect if dismissed',()=>{
 for(const p of [ranger(),druid()]){p.level=12;const f=fixture(p),prompt=f.context.BractwoSkillsUI.createPrompt(f.hooks);prompt.sync();const panel=f.ids.gameUI.querySelector('.advancement-choice');assert.equal(panel.hidden,false);const choose=panel.querySelector('[data-advancement-class]');choose.click();assert.deepEqual(f.opened,[['feats',p.class_id==='ranger'?'ranger_style':'elemental_fury']]);panel.querySelector('[data-advancement-dismiss]').click();prompt.sync();assert.equal(panel.hidden,true);f.session(2);prompt.sync();assert.equal(panel.hidden,false);
  if(p.class_id==='ranger')f.sheet({fighter:{...p.character_sheet.fighter,pending:false,style:'archery'}});else f.sheet({caster:{...p.character_sheet.caster,elemental_fury:{...p.character_sheet.caster.elemental_fury,pending:false,id:'primal_strike'}}});prompt.sync();assert.equal(panel.hidden,true);
 }
});

test('level-up receipts route directly to class choices and reflect an assigned choice without losing the receipt',()=>{
 for(const [p,kind,level] of [[ranger(),'ranger_style',2],[druid(),'elemental_fury',7]]){p.pending_level_ups=[{id:'level-'+level,level,rows:[{id:kind,label:'Dostępny wybór',gain:'+1'}],actions:[{kind,label:'Wybierz zdolność',tab:'feats',section:kind}]}];const f=fixture(p),receipt=f.context.BractwoLevelUp.create({...f.hooks,ready:()=>true});receipt.sync(p);const button=f.ids.levelUpCascade.querySelector('[data-kind]');button.click();assert.deepEqual(f.opened,[['feats',kind]]);assert.equal(receipt.count,1);
  if(kind==='ranger_style')f.sheet({fighter:{...p.character_sheet.fighter,pending:false,style:'archery'}});else f.sheet({caster:{...p.character_sheet.caster,elemental_fury:{...p.character_sheet.caster.elemental_fury,pending:false,id:'primal_strike'}}});receipt.sync(f.player());assert.equal(button.disabled,true);assert.equal(button.textContent,'Przydzielono');assert.equal(receipt.count,1);
 }
});

test('a later Druidic Warrior receipt keeps cantrip replacement accessible until that level allowance is spent',()=>{
 const p=ranger();p.level=3;Object.assign(p.character_sheet.fighter,{style:'druidic_warrior',pending:false,cantrip_replacement_available:true});p.pending_level_ups=[{id:'l3',level:3,actions:[{kind:'ranger_cantrip',label:'Sprawdź sztuczki',tab:'feats',section:'ranger_style'}]}];const f=fixture(p),receipt=f.context.BractwoLevelUp.create({...f.hooks,ready:()=>true});receipt.sync(p);const button=f.ids.levelUpCascade.querySelector('[data-kind="ranger_cantrip"]');assert.equal(button.disabled,false);button.click();assert.deepEqual(f.opened,[['feats','ranger_style']]);f.sheet({fighter:{...p.character_sheet.fighter,cantrip_replacement_available:false}});receipt.sync(f.player());assert.equal(button.disabled,true);
});

test('character sheet opens focused class subtabs and keeps the two choices out of general feat spending',()=>{
 for(const [p,section,selector] of [[ranger(),'ranger_style','[data-style]'],[druid(),'elemental_fury','[data-elemental-choice]']]){const f=fixture(p),sheet=f.context.BractwoCharacterSheet.create(f.hooks);sheet.open('feats',section);assert.equal(f.content.dataset.section,section);assert(f.content.querySelector(selector));assert.equal(f.content.querySelector('.training-available'),null);assert.equal(f.content.scrollTop,0);}
});

test('compact attack menu sends targeted offhand and grapple actions and honors current server availability',()=>{
 const p=ranger();p.character_sheet.weapon_actions={mode:'weapon',modes:[{id:'weapon',enabled:true},{id:'throw',enabled:true},{id:'unarmed',enabled:true}],offhand:{uid:'dagger'},offhand_enabled:true,can_grapple:true,grapple_dc:13};const f=fixture(p),menu=f.context.BractwoFighterUI.createCombatMenu({...f.hooks,target:()=>({enemy_id:'e1'})});f.ids.gameUI.querySelector('.weapon-action-toggle').click();const panel=f.ids.gameUI.querySelector('.weapon-action-menu');panel.querySelector('[data-combat-offhand]').click();assert.deepEqual(f.sent,[{type:'offhand_attack',enemy_id:'e1'}]);assert.equal(panel.hidden,true);
 f.ids.gameUI.querySelector('.weapon-action-toggle').click();panel.querySelector('[data-combat-grapple]').click();assert.deepEqual(f.sent[1],{type:'grapple',enemy_id:'e1'});f.set({alive:false});menu.sync();assert.equal(panel.hidden,true);
});

test('ground-weapon list preserves exact instance UID and disables pickups across floors or outside reach',()=>{
 const p=ranger();Object.assign(p,{x:0,y:0,floor:0,thrown_weapons:[{item:{uid:'unique-dagger',name:'Sztylet'},x:32,y:0,floor:0},{item:{uid:'remote',name:'Toporek'},x:32,y:0,floor:1}]});const f=fixture(p),box=f.section();f.context.BractwoInventoryUI.thrownWeapons(box,p,f.hooks);const buttons=box.querySelectorAll('button');assert.equal(buttons[0].disabled,false);assert.equal(buttons[1].disabled,true);buttons[0].click();assert.deepEqual(f.sent,[{type:'recover_thrown',uid:'unique-dagger'}]);
});
