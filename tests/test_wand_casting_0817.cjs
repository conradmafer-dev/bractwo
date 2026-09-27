const test=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {queuedSpellLabel}=require('../web/runtime.js');
const spec={id:'magic_missile',name:'Magiczny pocisk'};
test('only the server-acknowledged pending spell gets a queue caption',()=>{
 assert.equal(queuedSpellLabel(spec,{queued_spell:'magic_missile',action_remaining:2.5}),'Za 2.5 s');
 assert.equal(queuedSpellLabel(spec,{queued_spell:'fire_bolt',action_remaining:2.5}),'');
});
test('ready pending command remains visible until the server executes it',()=>{
 assert.equal(queuedSpellLabel(spec,{queued_spell:'magic_missile',action_remaining:0}),'W kolejce');
 assert.equal(queuedSpellLabel(spec,{queued_spell:'magic_missile',action_remaining:-1}),'W kolejce');
});
test('no empty slot or absent player can show a phantom pending spell',()=>{
 assert.equal(queuedSpellLabel(undefined,undefined),'');
 assert.equal(queuedSpellLabel({},{}),'');
 assert.equal(queuedSpellLabel(spec,{}),'');
});
test('queue label disappears after completion or cancellation',()=>{
 const p={queued_spell:'magic_missile',action_remaining:1.28};
 assert.equal(queuedSpellLabel(spec,p),'Za 1.3 s');
 p.queued_spell='';assert.equal(queuedSpellLabel(spec,p),'');
});
test('hotbar, F and book share the same queue formatter',()=>{
 const game=fs.readFileSync(path.join(__dirname,'../web/game.js'),'utf8');
 const book=fs.readFileSync(path.join(__dirname,'../web/character_sheet.js'),'utf8');
 assert(game.includes('Runtime.queuedSpellLabel(abilitySpec,me)'));
 assert(game.includes('Runtime.queuedSpellLabel(s,me)'));
 assert(book.includes('BractwoRuntime.queuedSpellLabel(s,p)'));
});
test('wand instruction is determined by actual weapon and mentions manual Space',()=>{
 const game=fs.readFileSync(path.join(__dirname,'../web/game.js'),'utf8');
 assert(game.includes('me.weapon_auto_attack===false'));
 assert(game.includes('Iskra różdżki tylko na Spację lub przycisk ataku'));
});
test('native client mirrors the queue and actual weapon instruction',()=>{
 const main=fs.readFileSync(path.join(__dirname,'../client/scripts/main.gd'),'utf8');
 const sheet=fs.readFileSync(path.join(__dirname,'../client/scripts/character_sheet.gd'),'utf8');
 assert(main.includes('func _queued_spell_label(key: String) -> String:'));
 assert(main.includes('player.get("weapon_auto_attack", true)'));
 assert(sheet.includes('cast.text = queue_label if not queue_label.is_empty()'));
});
