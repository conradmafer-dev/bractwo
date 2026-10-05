'use strict';
const assert = require('node:assert/strict');
const {test} = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const R = require('../web/runtime.js');
const Martial = require('../web/martial_ui.js');
const Caster = require('../web/caster_ui.js');

// The XP label is cumulative; filling a new level from 300/900 must start at 0%.
test('D&D cumulative XP and within-level bar stay distinct at each boundary', () => {
  for (const [player, total, next, ratio] of [
    [{level:1,xp:0,xp_next:300,xp_total:0,xp_next_total:300},0,300,0],
    [{level:2,xp:0,xp_next:600,xp_total:300,xp_next_total:900},300,900,0],
    [{level:2,xp:300,xp_next:600,xp_total:600,xp_next_total:900},600,900,.5],
    [{level:3,xp:0,xp_next:1800,xp_total:900,xp_next_total:2700},900,2700,0],
    [{level:20,xp:25000,xp_next:50000,xp_total:380000,xp_next_total:405000},380000,405000,.5],
    [{level:21,xp:0,xp_next:50000,xp_total:405000,xp_next_total:455000},405000,455000,0],
  ]) {
    const result=R.experienceProgress(player);
    assert.equal(result.total,total);assert.equal(result.nextTotal,next);assert.equal(result.ratio,ratio);
  }
});

test('XP presentation tolerates incomplete owner snapshots and clamps fill', () => {
  assert.deepEqual(R.experienceProgress({xp:150,xp_next:600,xp_level_start:300}),{total:450,nextTotal:900,progress:150,needed:600,ratio:.25});
  assert.equal(R.experienceProgress({xp:900,xp_next:600}).ratio,1);
  assert.equal(R.experienceProgress({xp:-1,xp_next:300}).ratio,0);
  assert(Number.isFinite(R.experienceProgress({}).ratio));
});

test('ranger spell fallback uses levels 1, 5, 9, 13, 17 and respects authoritative profiles', () => {
  const p={class_id:'ranger'};
  assert.deepEqual([1,2,3,4,5].map(circle=>R.spellGate({circle},p)),[1,5,9,13,17]);
  assert.equal(R.spellGate({id:'spell',circle:3,class_levels:{ranger:7}},p),7);
  assert.equal(R.spellGate({id:'spell',circle:3},{...p,spell_profiles:{spell:{required_level:6}}}),6);
});

test('level-three martial characters can choose specializations without waiting to ten', () => {
  const p={class_id:'knight',level:3,alive:true,promoted:true,character_sheet:{martial:{required_level:3,promotion_met:true,pending:true,eligible:true,options:[{id:'champion'}]}}};
  assert.equal(Martial.choiceReason(p),'');
  assert.deepEqual(Martial.selectionPacket(p,{id:'champion',confirmed:true}),{type:'martial_choice',archetype:'champion'});
  assert.match(Martial.choiceReason({...p,level:2}),/poziomu 3/);
});

test('caster choices use normalized server levels and new fallback', () => {
  const p={class_id:'mage',level:3,alive:true,promoted:true,character_sheet:{caster:{school:{pending:true,eligible:true,promotion_met:true,required_level:3}}}};
  assert.equal(Caster.schoolReason(p),'');
  assert.match(Caster.schoolReason({...p,level:2}),/poziomu 3/);
  const druid={...p,class_id:'druid',character_sheet:{caster:{circle:{pending:true,required_promotion:true,promotion_met:true}}}};
  assert.equal(Caster.circleReason(druid),'');
  assert.match(Caster.circleReason({...druid,level:2}),/poziomu 3/);
});

test('both web XP displays use cumulative data and mobile XP bar uses level progress', () => {
  const read=file=>fs.readFileSync(path.join(__dirname,'..',file),'utf8');
  const game=read('web/game.js'),sheet=read('web/character_sheet.js'),mobile=read('client/scripts/main.gd');
  assert.match(game,/xpText\.textContent=.*experience\.total.*experience\.nextTotal/);
  assert.match(game,/xpFill\.style\.width=.*experience\.ratio/);
  assert.match(sheet,/Doświadczenie.*experienceProgress\(p\)\.total.*experienceProgress\(p\)\.nextTotal/);
  assert.match(mobile,/xp_bar\.value = float\(player\.get\("xp", 0\)\)/);
  assert.match(mobile,/vital_label\.text = .*xp_total.*xp_next_total/);
});
