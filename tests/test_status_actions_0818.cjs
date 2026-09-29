const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const Runtime=require('../web/runtime.js');

test('status controls let noncasters escape hazards and wake allies without spell access',()=>{
  class Element{
    constructor(id=''){this.id=id;this.children=[];this.dataset={};this.events={};this.hidden=false;this.disabled=false;this.classList={toggle(){}};}
    addEventListener(type,fn){this.events[type]=fn;}
    append(child){child.parent=this;this.children.push(child);}
    remove(){this.parent.children=this.parent.children.filter(c=>c!==this);}
    setAttribute(){}
    click(){this.events.click?.();}
  }
  const ui=Object.fromEntries(['escapeRestraint','ownEffects','targetEffects','effectDetail','effectDetailName','effectDetailText','ownEffectsRow','targetEffectsRow','effectsPanel'].map(id=>[id,new Element(id)]));
  const me={id:'knight',class_id:'knight',hp:30,alive:true,action_remaining:0,x:0,y:0,floor:0,party_id:'party',hotbar:[],spell_profiles:{},status_effects:[]};
  const ally={id:'friend',hp:20,alive:true,x:20,y:0,floor:0,party_id:'party',status_effects:[]};
  const sent=[];
  const ctx=vm.createContext({ui,me,Runtime,snapshot:{players:[me,ally],enemies:[]},selectedTarget:'',selectedEnemy:'',document:{createElement:()=>new Element()},send:packet=>sent.push(JSON.parse(JSON.stringify(packet)))});
  const game=fs.readFileSync(require.resolve('../web/game.js'),'utf8');
  const start=game.indexOf("  let selectedEffectId='',effectActionPacket=null;");
  const end=game.indexOf('  ui.controlTip.hidden=',start);
  assert(start>=0&&end>start);
  vm.runInContext(game.slice(start,end),ctx);
  const effect=(id,action,spell_id='')=>({id,escape_action_id:action,spell_id,name:id,description:'',remaining:30});
  const refresh=()=>vm.runInContext('updateEffects()',ctx);
  const open=(own=true)=>{refresh();const container=own?ui.ownEffects:ui.targetEffects;assert(container.children.length);container.children[0].click();};
  me.status_effects=[effect('web_restrained','escape_web')];open();
  assert.equal(ui.escapeRestraint.hidden,false);assert.equal(ui.escapeRestraint.disabled,false);
  ui.escapeRestraint.click();assert.deepEqual(sent.pop(),{type:'circle_spell_action',action:'escape_web'});
  me.action_remaining=2;refresh();assert.equal(ui.escapeRestraint.disabled,true);ui.escapeRestraint.click();assert.equal(sent.length,0);
  me.action_remaining=0;refresh();assert.equal(ui.escapeRestraint.disabled,false);
  me.status_effects=[effect('whirlpool','escape_whirlpool')];open();ui.escapeRestraint.click();
  assert.deepEqual(sent.pop(),{type:'circle_spell_action',action:'escape_whirlpool'});
  me.status_effects=[effect('elemental_restrained','')];open();assert.equal(ui.escapeRestraint.hidden,true);
  me.status_effects=[];ally.status_effects=[effect('unconscious','wake','sleep')];ctx.selectedTarget=ally.id;open(false);
  assert.equal(ui.escapeRestraint.hidden,false);assert.equal(ui.escapeRestraint.disabled,false);ui.escapeRestraint.click();
  assert.deepEqual(sent.pop(),{type:'circle_spell_action',action:'wake',target_id:ally.id});
  ally.x=33;refresh();assert.equal(ui.escapeRestraint.disabled,true);ally.x=20;
  ally.floor=1;refresh();assert.equal(ui.escapeRestraint.disabled,true);ally.floor=0;
  ally.party_id='other';refresh();assert.equal(ui.escapeRestraint.hidden,true);ally.party_id='party';
  ally.status_effects[0].spell_id='other_sleep';refresh();assert.equal(ui.escapeRestraint.hidden,true);
  ally.status_effects=[effect('web_restrained','escape_web','web')];open(false);assert.equal(ui.escapeRestraint.hidden,true);
  ctx.selectedTarget='';me.status_effects=[effect('unconscious','wake','sleep')];open();assert.equal(ui.escapeRestraint.hidden,true);
  me.status_effects=[{...effect('restrained',''),escape_action:true}];open();ui.escapeRestraint.click();
  assert.deepEqual(sent.pop(),{type:'escape_restraint'});
});
