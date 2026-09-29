'use strict';
const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

// Run the actual sheet and feat UI with a focused native-select DOM fixture.
function fixture(){
  let document;
  class Element{
    constructor(tag){this.tagName=tag.toUpperCase();this.children=[];this.dataset={};this.attributes={};this.listeners=new Map();this.className='';this.hidden=false;this.disabled=false;this.value='';this.scrollTop=0;this.classList={toggle:()=>{}};}
    append(...children){for(const child of children){child.parentNode=this;this.children.push(child);if(this.tagName==='SELECT'&&this.children.length===1)this.value=child.value;}}
    replaceChildren(...children){for(const child of this.children)child.parentNode=null;this.children=[];this.append(...children);}
    setAttribute(key,value){this.attributes[key]=String(value);}
    addEventListener(name,handler){this.listeners.set(name,handler);}
    contains(node){return this===node||this.children.some(child=>child.contains(node));}
    matches(selector){if(selector.startsWith('.'))return this.className.split(/\s+/).includes(selector.slice(1));const attribute=selector.match(/^\[data-([\w-]+)(?:="([^"]+)")?\]$/);if(attribute){const key=attribute[1].replace(/-([a-z])/g,(_,c)=>c.toUpperCase());return key in this.dataset&&(attribute[2]===undefined||this.dataset[key]===attribute[2]);}return this.tagName===selector.toUpperCase();}
    querySelectorAll(selector){return this.children.flatMap(child=>[...(child.matches(selector)?[child]:[]),...child.querySelectorAll(selector)]);}
    querySelector(selector){return this.querySelectorAll(selector)[0]||null;}
    focus(){document.activeElement=this;}
    click(){if(!this.disabled){this.onclick?.();this.listeners.get('click')?.({target:this});}}
  }
  const ids={};
  for(const id of ['characterPanel','characterContent','characterName','characterSubtitle'])ids[id]=new Element('section');
  const panel=ids.characterPanel,content=ids.characterContent,tab=new Element('button'),close=new Element('button');
  tab.dataset.characterTab='feats';close.className='character-close';panel.hidden=true;panel.append(tab,close,content);
  document={activeElement:null,getElementById:id=>ids[id],createElement:tag=>new Element(tag)};
  let player={id:'druid-15',name:'Druid',class_id:'druid',level:15,alive:true,form:'',hp:10,mana:10,combat_remaining:20,
    character_sheet:{caster:{order:'warden'},training:{points:1,levels:[15,35,55,75],options:[{id:'heavily_armored',name:'Ciężko opancerzony',abilities:['strength','constitution']}]}}};
  const sent=[],context={document,Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}}};
  vm.createContext(context);
  for(const file of ['caster_ui.js','character_sheet.js'])vm.runInContext(fs.readFileSync(path.join(__dirname,'../web',file),'utf8'),context,{filename:file});
  const api=context.BractwoCharacterSheet.create({state:()=>({player,world:{}}),prepare:()=>{},canTrade:()=>false,nearMaster:()=>false,send:packet=>sent.push({...packet})});
  api.open('feats');
  const row=content.querySelector('.training-option'),select=row.querySelector('select'),confirm=row.querySelector('button');
  select.focus();select.value='constitution';select.listeners.get('change')({target:select});
  return {api,content,select,confirm,sent,document,player:()=>player,set(patch){player={...player,...patch};api.render();},training(patch){player={...player,character_sheet:{...player.character_sheet,training:{...player.character_sheet.training,...patch}}};api.render();}};
}

test('druid 15 can confirm after combat expires while the stat selector retains focus',()=>{
  const f=fixture();assert.equal(f.confirm.disabled,true);assert.match(f.confirm.title,/walki/);
  f.set({combat_remaining:0});
  assert.equal(f.confirm.disabled,false);assert.equal(f.document.activeElement,f.select);
  assert.equal(f.content.querySelector('select'),f.select);assert.equal(f.select.value,'constitution');
  f.confirm.click();assert.deepEqual(f.sent,[{type:'training_feat',feat:'heavily_armored',ability:'constitution'}]);
});

test('spent points and a feat removed from the latest snapshot disable the focused form',()=>{
  const f=fixture();f.set({combat_remaining:0});f.training({points:0});
  assert.equal(f.confirm.disabled,true);f.confirm.onclick();assert.equal(f.sent.length,0);
  f.training({points:1,options:[]});assert.equal(f.confirm.disabled,true);
  f.confirm.onclick();assert.equal(f.sent.length,0);
});

test('missing or no-longer-eligible stat never enables confirmation',()=>{
  const f=fixture();f.set({combat_remaining:0});f.select.value='';f.select.listeners.get('change')({target:f.select});
  assert.equal(f.confirm.disabled,true);f.confirm.onclick();assert.equal(f.sent.length,0);
  f.select.value='constitution';f.training({options:[{id:'heavily_armored',abilities:['strength']}]});
  assert.equal(f.confirm.disabled,true);assert.equal(f.select.value,'constitution');
});

test('fresh death, transformation and combat gates remain authoritative without reconnecting',()=>{
  const f=fixture();f.set({combat_remaining:0});assert.equal(f.confirm.disabled,false);
  for(const patch of [{alive:false},{alive:true,form:'wolf'},{form:'',combat_remaining:3}]){
    f.set(patch);assert.equal(f.confirm.disabled,true);f.confirm.onclick();
  }
  assert.equal(f.sent.length,0);assert.equal(f.document.activeElement,f.select);
  f.set({combat_remaining:0});assert.equal(f.confirm.disabled,false);
});
