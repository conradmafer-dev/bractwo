'use strict';
const assert=require('node:assert/strict');
const {test}=require('node:test');
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');

// Run the shipped controls, reminders and durable receipts against an actual
// stateful DOM fixture. No browser dependency or replica of selection logic.
function fixture(initial,initialWorld={}){
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
 document={activeElement:null,body:ids.gameUI,getElementById:id=>ids[id]||ids.gameUI.querySelectorAll('*').find(el=>el.id===id),createElement:tag=>new Element(tag),addEventListener(){},createTextNode:text=>{const e=new Element('text');e.textContent=text;return e;}};
 let player=initial,world=initialWorld,session=1;const sent=[],opened=[],context={document,innerWidth:420,addEventListener(){},localStorage:{getItem(){return null;},setItem(){}},Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}}};vm.createContext(context);
 for(const file of ['runtime.js','rest_ui.js','fighter_ui.js','caster_ui.js','wizard_spellbook_ui.js','skills_ui.js','level_up.js','inventory_ui.js','character_sheet.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web',file),'utf8'),context,{filename:file});
 const hooks={stop(){},close(){},content,refresh(){},gate:spec=>Number(spec.min_level)||1,state:()=>({player,world}),prepare(){},canTrade:()=>false,nearMaster:()=>false,send:packet=>sent.push(JSON.parse(JSON.stringify(packet))),cast(){},player:()=>player,session:()=>session,open:(...args)=>opened.push(args)};
 return {context,document,ids,content,hooks,sent,opened,world,player:()=>player,set(patch){player={...player,...patch};},sheet(patch){player={...player,character_sheet:{...player.character_sheet,...patch}};},session(n){session=n;},section(){return new Element('section');}};
}

const catalog={spells:{
 spark:{id:'spark',name:'Iskra',circle:0,class_ids:['mage'],min_level:1,mana:0,description:'Sztuczka.'},
 missile:{id:'missile',name:'Magiczny pocisk',circle:1,class_ids:['mage'],min_level:1,mana:5,description:'Pocisk.'},
 shield:{id:'shield',name:'Tarcza',circle:1,class_ids:['mage'],min_level:1,mana:5,description:'Tarcza.'},
 familiar:{id:'familiar',name:'Chowaniec',circle:1,class_ids:['mage'],min_level:1,mana:5,ritual:true,ritual_seconds:10,description:'Chowaniec.'},
 future:{id:'future',name:'Przyszły czar',circle:5,class_ids:['mage'],min_level:9,mana:30,description:'Jeszcze niedostępny.'}
}};
function mage(book={}){return {id:'mage',name:'Czarodziej',class_id:'mage',level:5,hp:20,max_hp:20,mana:40,max_mana:40,alive:true,form:'',combat_remaining:0,rest_block_remaining:0,rest_block_reason:'',rest_safe:true,gold:100,hotbar:['spark','missile'],spell_circle:3,spell_profiles:{spark:{available:true},missile:{available:true},shield:{available:false},familiar:{available:false,ritual_available:true},future:{available:false}},character_sheet:{training:{points:0},caster:{spellbook:{enabled:true,known:['missile','shield','familiar'],prepared:['missile'],prepared_limit:2,free_preparations:1,learning_choices:[],learning_credits:0,pending_learning:false,memorize_available:true,...book}}}};}
function updateBook(f,patch){const p=f.player();f.sheet({caster:{...p.character_sheet.caster,spellbook:{...p.character_sheet.caster.spellbook,...patch}}});}
function bookPanel(f,section='prepare'){const box=f.section(),h={...f.hooks,content:box};const api=f.context.BractwoWizardBookUI;api.header(box,f.player(),f.world,h,section);for(const spec of Object.values(f.world.spells||{})){if(section==='prepare'&&!api.state(f.player(),spec)?.known)continue;api.row(box,f.player(),spec,h,section);}api.sync(box,f.player(),h);return {box,h,api};}
const parsed=x=>JSON.parse(JSON.stringify(x));

test('book tabs separate ready spells, owned spells and learning catalogue without changing other classes',()=>{
 const f=fixture(mage(),catalog),ui=f.context.BractwoWizardBookUI,all=f.context.BractwoCharacterSheet.spellSections(catalog,f.player());
 const ids=section=>ui.sections(all,f.player(),section).flatMap(g=>g.entries.map(e=>e.id));
 assert.deepEqual(parsed(ids('ready')),['spark','missile']);assert.deepEqual(new Set(ids('book')),new Set(['missile','shield','familiar']));assert.deepEqual(parsed(ids('learn')),['future']);
 const druid={...f.player(),class_id:'druid'};assert.equal(ui.sections(all,druid,'learn'),all);assert.equal(ui.book(druid),null);
});

test('learning button sends one eligible explicit choice and rechecks stale player state',()=>{
 const f=fixture(mage({known:[],prepared:[],learning_choices:['missile'],learning_credits:6,pending_learning:true}),catalog),{box,h,api}=bookPanel(f,'learn');
 assert.equal(box.querySelector('[data-wizard-learn="missile"]').disabled,false);assert.equal(box.querySelector('[data-wizard-learn="future"]').disabled,true);
 const learn=box.querySelector('[data-wizard-learn="missile"]');f.set({combat_remaining:2});learn.listeners.get('click')();assert.equal(f.sent.length,0);api.sync(box,f.player(),h);assert.equal(learn.disabled,true);
 f.set({combat_remaining:0});api.sync(box,f.player(),h);learn.click();assert.deepEqual(f.sent,[{type:'wizard_learn',spell:'missile'}]);assert.deepEqual(f.player().character_sheet.caster.spellbook.known,[]);
});

test('preparation checkboxes preserve active spells, enforce capacity and send one atomic long-rest transaction',()=>{
 const f=fixture(mage(),catalog),{box,h,api}=bookPanel(f),before=JSON.stringify(f.player());
 const shield=box.querySelector('[data-wizard-prepared="shield"]');shield.checked=true;shield.change('');assert.equal(box.querySelector('[data-wizard-prepared="familiar"]').disabled,true);assert.equal(box.querySelector('[data-wizard-draft-count]').textContent,'Wybrany zestaw: 2/2');assert.equal(f.sent.length,0);assert.equal(JSON.stringify(f.player()),before);
 box.querySelector('[data-wizard-long]').click();assert.deepEqual(f.sent,[{type:'rest',kind:'long',recover:true,wizard_preparation:{prepared:['missile','shield']}}]);assert.deepEqual(f.player().character_sheet.caster.spellbook.prepared,['missile']);
 f.set({rest:{kind:'long',remaining:20,total:30}});api.sync(box,f.player(),h);assert.equal(box.querySelector('[data-wizard-long]').disabled,true);
});

test('free preparation adds only awarded slots and never substitutes an existing spell',()=>{
 const f=fixture(mage(),catalog),{box,api}=bookPanel(f);api.draft(f.player()).prepared.add('shield');assert.deepEqual(parsed(api.freePacket(f.player())),{type:'wizard_prepare',spells:['missile','shield']});api.draft(f.player()).prepared.delete('missile');assert.equal(api.freePacket(f.player()),null);assert(api.restPacket(f.player(),catalog,'long'));
 updateBook(f,{free_preparations:0});assert.equal(api.freePacket(f.player()),null);
});

test('rest preparation uses rest gates rather than the older combat tag and rejects late movement or death',()=>{
 const f=fixture(mage(),catalog),{box,h,api}=bookPanel(f);f.set({combat_remaining:15});assert(api.restPacket(f.player(),catalog,'long'));assert.equal(api.freePacket(f.player()),null);
 for(const patch of [{rest_block_reason:'moving'},{rest_block_reason:'',rest_block_remaining:.1},{rest_block_remaining:0,rest_long_remaining:1},{rest_long_remaining:0,alive:false}]){f.set(patch);api.sync(box,f.player(),h);assert.equal(box.querySelector('[data-wizard-long]').disabled,true);box.querySelector('[data-wizard-long]').listeners.get('click')();assert.equal(f.sent.length,0);}
});

test('Memorize exchanges exactly one known unprepared spell after short rest without modifying the long-rest draft',()=>{
 const f=fixture(mage(),catalog),{box,api}=bookPanel(f);assert.equal(box.querySelector('[data-wizard-short]').disabled,true);
 box.querySelector('[data-wizard-memorize-pick="forget"]').change('missile');box.querySelector('[data-wizard-memorize-pick="prepare"]').change('familiar');box.querySelector('[data-wizard-short]').click();assert.deepEqual(f.sent,[{type:'rest',kind:'short',recover:true,wizard_preparation:{memorize:{forget:'missile',prepare:'familiar'}}}]);assert.deepEqual([...api.draft(f.player()).prepared],['missile']);
 updateBook(f,{memorize_available:false});assert.equal(api.restPacket(f.player(),catalog,'short'),null);assert.equal(bookPanel(f).box.querySelector('[data-wizard-short]'),null);
});

test('a completed server preparation supersedes an obsolete local draft',()=>{
 const f=fixture(mage(),catalog),api=f.context.BractwoWizardBookUI;api.draft(f.player()).prepared.add('shield');updateBook(f,{prepared:['familiar'],free_preparations:0});assert.deepEqual([...api.draft(f.player()).prepared],['familiar']);
});

test('real spell rows give known unprepared rituals a ritual button, while normal use and hotbar remain disabled',()=>{
 const f=fixture(mage(),catalog),sheet=f.context.BractwoCharacterSheet.create(f.hooks);sheet.open('spells','book');const row=f.content.querySelector('[data-spell="familiar"]'),buttons=row.querySelectorAll('button');assert.equal(buttons.find(b=>b.textContent==='Użyj').disabled,true);const ritual=buttons.find(b=>b.textContent.startsWith('Rytuał'));assert.equal(ritual.disabled,false);ritual.click();assert.deepEqual(f.sent,[{type:'ritual',spell_id:'familiar'}]);assert.equal(row.querySelector('select').disabled,true);
 sheet.open('spells','learn');assert.equal(f.content.querySelector('[data-spell="future"]').querySelectorAll('button').some(b=>b.textContent.startsWith('Rytuał')),false);
});

test('wizard reminder opens learning and returns for a new award, but finite exhausted catalogue does not nag',()=>{
 const f=fixture(mage({known:[],prepared:[],learning_choices:['missile'],learning_credits:6,pending_learning:true}),catalog),prompt=f.context.BractwoSkillsUI.createPrompt(f.hooks),panel=f.ids.gameUI.querySelector('.advancement-choice');prompt.sync();assert.equal(panel.hidden,false);panel.querySelector('[data-advancement-class]').click();assert.deepEqual(f.opened,[['spells','learn']]);panel.querySelector('[data-advancement-dismiss]').click();prompt.sync();assert.equal(panel.hidden,true);
 updateBook(f,{learning_credits:8});prompt.sync();assert.equal(panel.hidden,false);updateBook(f,{learning_choices:[],pending_learning:false,free_preparations:0,catalog_limited:true});prompt.sync();assert.equal(panel.hidden,true);
});

test('level-up book actions route to spells and Memorize remains accessible after all learning choices are used',()=>{
 const p=mage({pending_learning:true,learning_choices:['future']});p.pending_level_ups=[{id:'lv5',level:5,actions:[{kind:'wizard_book',label:'Poznaj czary',tab:'spells',section:'learn'},{kind:'wizard_book',label:'Zapamiętaj czar',tab:'spells',section:'memorize'}]}];const f=fixture(p,catalog),receipt=f.context.BractwoLevelUp.create({...f.hooks,ready:()=>true});receipt.sync(p);const buttons=f.ids.levelUpCascade.querySelectorAll('[data-kind="wizard_book"]');buttons[0].click();buttons[1].click();assert.deepEqual(f.opened,[['spells','learn'],['spells','memorize']]);updateBook(f,{pending_learning:false,learning_choices:[]});receipt.sync(f.player());assert.equal(buttons[0].disabled,true);assert.equal(buttons[1].disabled,false);
});

test('learning grant summary distinguishes low-circle credits and school-restricted credits',()=>{
 const f=fixture(mage(),catalog);assert.equal(f.context.BractwoWizardBookUI.grantSummary({learning_grants:[{remaining:2,max_circle:1,school:''},{remaining:2,max_circle:1,school:''},{remaining:1,max_circle:3,school:'evocation'}]}),'4 × do 1. kręgu / 1 × do 3. kręgu · Ewokacja');
});
