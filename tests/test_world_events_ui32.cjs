'use strict';
const assert=require('node:assert/strict');
const {test}=require('node:test');
const fs=require('node:fs');
const path=require('node:path');
require('../web/skills_ui.js');
const ui=globalThis.BractwoSkillsUI;
const scenes=['wounded_guard','broken_cart','road_dispute','lost_pouch','stolen_supplies','sealed_relic','herbalist','frightened_pony'];
function draw(scene,completed=false){
 const commands=[];let depth=0;
 const g=new Proxy({}, {get(target,name){if(name==='save')return()=>{depth++;commands.push(['save']);};if(name==='restore')return()=>{depth--;assert(depth>=0);commands.push(['restore']);};return(...args)=>{assert(args.every(n=>typeof n!=='number'||Number.isFinite(n)),String(name));commands.push([name,...args]);};},set(t,key,v){commands.push([key,v]);return true;}});
 ui.drawEvent(g,{scene,x:100,y:150},{completed,completed_age:60,hint:'Wskazówka'},1.2);
 assert.equal(depth,0,'Canvas transforms must be restored after every scene');return commands;
}
for(const scene of scenes){
 test('scene '+scene+' uses balanced, finite canvas commands',()=>{assert(draw(scene).length>40);assert(draw(scene,true).length>30);});
 test('scene '+scene+' changes visibly after completion',()=>{assert.notDeepEqual(draw(scene),draw(scene,true));});
}
test('new scenes never draw a dice number or a completed tick',()=>{
 for(const scene of scenes)for(const done of[false,true])assert(!draw(scene,done).some(c=>['fillText','strokeText'].includes(c[0])));
});
test('all scene renderers are distinct, not reused markers',()=>{
 assert.equal(new Set(scenes.map(s=>JSON.stringify(draw(s)))).size,8);
});
test('game routes interactions into conversations and retains real feat/result helpers',()=>{
 const game=fs.readFileSync(path.join(__dirname,'../web/game.js'),'utf8');
 assert(game.includes('createEvents('));assert(game.includes('eventPanel.open(skillSite)'));assert(game.includes('openEvent:site=>'));
 assert(game.includes('Runtime.renderCombatNotice'));assert(game.includes('BractwoFeatUI'));
 assert(!game.includes('drawSkillChallenge('));assert(game.includes('drawWorldEvent('));
});
test('event renderer is bundled in an existing served script, not a missing import',()=>{
 const server=fs.readFileSync(path.join(__dirname,'../server/server.py'),'utf8');
 assert(server.includes('("/skills_ui.js","skills_ui.js")'));
 assert(server.includes('("/feat_ui.js","feat_ui.js")'));assert(server.includes('("/feat_ui.css","feat_ui.css")'));
 assert.equal(typeof ui.createEvents,'function');
});
