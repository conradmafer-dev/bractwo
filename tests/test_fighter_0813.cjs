'use strict';
const {test}=require('node:test');const assert=require('node:assert/strict');
const {canChoose}=require('../web/fighter_ui.js');const VFX=require('../web/fighter_vfx.js');const Runtime=require('../web/runtime.js');
function player(style=''){return{class_id:'knight',alive:true,combat_remaining:0,character_sheet:{fighter:{style}}};}
test('Initial warrior choice needs no master or points',()=>{assert(canChoose(player(),false));});
test('Changing a chosen style requires the master',()=>{assert(!canChoose(player('dueling'),false));assert(canChoose(player('dueling'),true));});
test('Dead warriors and active combat cannot change style',()=>{assert(!canChoose({...player(),alive:false},true));assert(!canChoose({...player(),combat_remaining:1},true));});
test('No other class receives warrior-style choice',()=>{for(const cls of ['mage','druid','ranger'])assert(!canChoose({...player(),class_id:cls},true));});
function ctx(){let depth=0,calls=0;return new Proxy({save(){depth++;},restore(){assert(depth>0);depth--;},depth:()=>depth,calls:()=>calls},{get(o,k){if(k in o)return o[k];return(...args)=>{calls++;for(const n of args)if(typeof n==='number')assert(Number.isFinite(n),k);};},set(o,k,v){o[k]=v;return true;}});}
test('Four mastery/surge effects draw finite commands and balance the canvas stack',()=>{for(const key of ['sap','topple','graze','surge'])for(const t of [0,.05,.3,.8,1]){const c=ctx();assert(VFX.draw(c,{kind:'fighter_'+key,mastery:key,x:0,y:0,target_x:75,target_y:28},t));assert.equal(c.depth(),0);assert(c.calls()>0);}});
test('Expired effects do not leave any marks on the canvas',()=>{for(const t of [-1,1.1]){const c=ctx();VFX.draw(c,{kind:'fighter_sap',mastery:'sap',x:0,y:0},t);assert.equal(c.calls(),0);assert.equal(c.depth(),0);}});
test('Old spell effects remain handled by their original renderer',()=>assert.equal(VFX.draw(ctx(),{kind:'spell'},.5),false));
test('Sap and prone overlays are visible only while authoritative status exists',()=>{for(const id of ['sap','prone']){const c=ctx();VFX.statuses(c,{status_effects:[{id}]},10,20,1000);assert(c.calls()>0);assert.equal(c.depth(),0);}const c=ctx();VFX.statuses(c,{status_effects:[]},10,20,1000);assert.equal(c.calls(),0);});
test('Graze is displayed as miss damage rather than a hit or harmless miss',()=>{const s=Runtime.combatSummary({id:'roll1',check:'attack',rolls:[1],roll:1,bonus:5,total:6,defense:18,hit:false,graze:true,damage:3,action:'Atak',target_name:'Cel'});assert(s.includes('Draśnięcie'));assert(s.includes('3'));});
