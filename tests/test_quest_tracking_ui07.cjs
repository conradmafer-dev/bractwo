const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

// Execute the production functions; DOM/storage are the only lightweight hooks.
const source=fs.readFileSync(path.join(__dirname,'../web/game.js'),'utf8');
const start=source.indexOf('  function directionTo(');
const end=source.indexOf('  function rewardDescription(',start);
assert.ok(start>=0&&end>start,'Quest-tracker source boundaries changed');
const fragment=source.slice(start,end);
assert.match(fragment,/function updateQuestTracker\(/);
const quest=(id,status='active',extra={})=>({id,title:id,status,npc_id:'guide',objectives:[],...extra});
function fixture(quests,{myId='player-a',storage=new Map(),world={}}={}){
  const classes=new Set();
  const context={myId,trackedQuestId:null,questSignature:'old',navigationGoal:null,activeGoal:null,
    me:{x:0,y:0,floor:0,quests,discoveries:[]},world:{npcs:[],landmarks:[],...world},snapshot:{enemies:[]},
    ui:{sidePanel:{hidden:false},questTracker:{classList:{remove:name=>classes.delete(name),toggle:(name,on)=>on?classes.add(name):classes.delete(name)}},questTrackerTitle:{textContent:''},questTrackerProgress:{textContent:''},questTrackerDirection:{textContent:''}},
    localStorage:{getItem:key=>storage.has(key)?storage.get(key):null,setItem:(key,value)=>storage.set(key,String(value))},
    distance:(a,b)=>Math.hypot(a.x-b.x,a.y-b.y),sameFloor:(a,b)=>(a.floor||0)===(b.floor||0),notice:()=>{},storage,classes};
  context.updateHUD=()=>context.updateQuestTracker();
  vm.createContext(context);vm.runInContext(fragment,context,{filename:'game.js:quest-tracking'});
  return context;
}

test('manual quest replaces atlas navigation and persists separately for myId',()=>{
  const quests=[quest('other'),quest('chosen')],storage=new Map();
  const ui=fixture(quests,{storage});ui.navigationGoal={x:99,y:99,label:'Atlas'};
  ui.toggleQuestTracking('chosen');
  assert.equal(ui.navigationGoal,null);assert.equal(ui.selectedQuest().id,'chosen');
  assert.equal(ui.ui.sidePanel.hidden,true);assert.equal(ui.ui.questTrackerTitle.textContent,'chosen');
  assert.equal(storage.get('bractwo.trackedQuest.player-a'),'chosen');
  const restored=fixture(quests,{storage});restored.trackedQuestId=restored.readTrackedQuest();
  assert.equal(restored.selectedQuest().id,'chosen');
  const otherPlayer=fixture(quests,{storage,myId:'player-b'});
  assert.equal(otherPlayer.readTrackedQuest(),null);otherPlayer.saveTrackedQuest('other');
  assert.equal(storage.get('bractwo.trackedQuest.player-a'),'chosen');
  assert.equal(storage.get('bractwo.trackedQuest.player-b'),'other');
});

test('another ready quest does not replace an explicitly selected active quest',()=>{
  const quests=[quest('other'),quest('chosen')],ui=fixture(quests);
  ui.toggleQuestTracking('chosen');quests[0].status='ready';ui.updateQuestTracker();
  assert.equal(ui.selectedQuest().id,'chosen');assert.equal(ui.trackedQuestId,'chosen');
  assert.equal(ui.ui.questTrackerTitle.textContent,'chosen');assert.equal(ui.classes.has('ready'),false);
});

test('first unfinished objective advances to the next and then NPC, preserving fallback coordinates and floors',()=>{
  const trip=quest('trip','active',{objectives:[
    {type:'kill',target:'rat',label:'Szczury',count:2,required:2},
    {type:'discover',target:'missing-site',label:'Ruiny',count:0,required:1,x:320,y:160,floor:-1},
    {type:'kill',target:'boar',label:'Dziki',count:0,required:2,x:640,y:96,floor:1}
  ]});
  const ui=fixture([trip],{world:{npcs:[{id:'guide',name:'Strażniczka',x:32,y:32,floor:0}]}});
  ui.saveTrackedQuest('trip');ui.updateQuestTracker();
  assert.equal(ui.activeGoal.label,'Ruiny');assert.equal(ui.activeGoal.x,320);assert.equal(ui.activeGoal.y,160);assert.equal(ui.activeGoal.floor,-1);
  assert.match(ui.ui.questTrackerDirection.textContent,/Piętro -1/);
  trip.objectives[1].count=1;ui.updateQuestTracker();
  assert.equal(ui.activeGoal.label,'Dziki');assert.equal(ui.activeGoal.x,640);assert.equal(ui.activeGoal.y,96);assert.equal(ui.activeGoal.floor,1);
  assert.match(ui.ui.questTrackerDirection.textContent,/Piętro 1/);
  trip.objectives[2].count=2;trip.status='ready';ui.updateQuestTracker();
  assert.equal(ui.activeGoal.id,'guide');assert.equal(ui.activeGoal.x,32);assert.equal(ui.activeGoal.y,32);assert.equal(ui.activeGoal.floor,0);
  assert.equal(ui.classes.has('ready'),true);assert.match(ui.ui.questTrackerProgress.textContent,/Wróć po nagrodę/);
});

test('claiming the tracked quest ends tracking instead of switching to another quest or landmark',()=>{
  const chosen=quest('chosen'),ui=fixture([chosen,quest('other','ready')],{world:{landmarks:[{id:'new',name:'Nowe miejsce',x:9,y:9}]}});
  ui.saveTrackedQuest('chosen');chosen.status='claimed';ui.updateQuestTracker();ui.updateQuestTracker();
  assert.equal(ui.trackedQuestId,'');assert.equal(ui.activeGoal,null);
  assert.equal(ui.storage.get('bractwo.trackedQuest.player-a'),'');
  assert.equal(ui.ui.questTrackerTitle.textContent,'Wybierz zadanie');
});

test('explicit off survives reload and locked or claimed quests cannot be selected',()=>{
  const quests=[quest('chosen'),quest('other','ready'),quest('locked','locked'),quest('claimed','claimed')];
  const ui=fixture(quests);ui.saveTrackedQuest('chosen');ui.toggleQuestTracking('chosen');
  assert.equal(ui.trackedQuestId,'');assert.equal(ui.selectedQuest(),null);
  const restored=fixture(quests,{storage:ui.storage});restored.trackedQuestId=restored.readTrackedQuest();restored.updateQuestTracker();
  assert.equal(restored.trackedQuestId,'');assert.equal(restored.activeGoal,null);
  const atlas={x:8,y:8,label:'Atlas'};restored.navigationGoal=atlas;
  for(const id of ['locked','claimed'])restored.toggleQuestTracking(id);
  assert.equal(restored.trackedQuestId,'');assert.equal(restored.navigationGoal,atlas);
  assert.equal(restored.ui.sidePanel.hidden,false);assert.equal(restored.storage.get('bractwo.trackedQuest.player-a'),'');
});
