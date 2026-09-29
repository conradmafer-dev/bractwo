'use strict';
const assert=require('node:assert/strict'),{test}=require('node:test'),fs=require('node:fs'),vm=require('node:vm');
globalThis.BractwoRuntime=require('../web/runtime.js');
const Hotbar=require('../web/hotbar_ui.js');
const spells={};for(const f of ['archer','chalice','dragon','arrow'])spells['circle_star_'+f]={id:'circle_star_'+f,kind:'druid_circle',name:f,mana:0,min_level:10};
const world={spells,hotbar_groups:{group_starry_form:{name:'Gwiezdna postać',icon:'starry.svg',members:Object.keys(spells)}}};
function player(){return {level:15,hp:31,alive:true,mana:0,circle_visual:{starry_form:'archer'},spell_profiles:Object.fromEntries(Object.keys(spells).map(id=>[id,{available:true,resource_cost:id.endsWith('arrow')?0:1,uses_remaining:0,uses_maximum:2}])),druid_forms:{starry_form:'archer',can_shoot:true,can_dismiss_star:true,shape_remaining:0,shape_maximum:2,arrow_ready_in:0}};}
test('owner form overrides stale visuals; explicit empty never resurrects cached form',()=>{
 const p=player();p.circle_visual.starry_form='dragon';assert.equal(Hotbar.activeStar(p),'archer');
 p.druid_forms.starry_form='';assert.equal(Hotbar.activeStar(p),'');assert.equal(Hotbar.groupState('group_starry_form',p,world).primary,null);
});
test('legacy fallback uses visuals, then sheet; empty visual overrides older sheet',()=>{
 const p=player();delete p.druid_forms;assert.equal(Hotbar.activeStar(p),'archer');
 p.circle_visual.starry_form='';p.character_sheet={caster:{circle:{starry_form:'dragon'}}};assert.equal(Hotbar.activeStar(p),'');
 delete p.circle_visual;assert.equal(Hotbar.activeStar(p),'dragon');
});
test('active archer has short distinct label, icon and zero-cost arrow action',()=>{
 const state=Hotbar.groupState('group_starry_form',player(),world);
 assert.equal(state.shortLabel,'Strzała');assert.equal(state.primary.id,'circle_star_arrow');assert.match(state.icon,/star_arrow/);assert.equal(state.disabled,false);
 assert.deepEqual(state.pool,{remaining:0,maximum:2});
});
test('bonus cooldown disables arrow without disabling resource-free dismissal',()=>{
 const p=player();p.druid_forms.arrow_ready_in=2.8;
 const s=Hotbar.groupState('group_starry_form',p,world);assert.equal(s.disabled,true);assert.equal(s.readyIn,2.8);assert.equal(Hotbar.canDismiss(p),true);
});
test('Kielich and Smok main action is dismissal, not another paid activation',()=>{
 for(const f of ['chalice','dragon']){const p=player();p.druid_forms.starry_form=f;
 const s=Hotbar.groupState('group_starry_form',p,world);assert.equal(s.command,'dismiss_star_form');assert.equal(s.primary,null);assert.equal(s.disabled,false);}
});
test('blocked and dead states do not offer dismissal',()=>{
 const p=player();p.druid_forms.can_dismiss_star=false;assert.equal(Hotbar.canDismiss(p),false);
 p.druid_forms.can_dismiss_star=true;p.hp=0;assert.equal(Hotbar.canDismiss(p),false);
});
function mobile(){const props={};const ctx={matchMedia:()=>({matches:true}),document:{getElementById:()=>({style:{setProperty:(k,v)=>props[k]=v}})},visualViewport:{scale:1}};vm.createContext(ctx);vm.runInContext(fs.readFileSync(require.resolve('../web/mobile.js'),'utf8'),ctx);return ctx.BractwoMobile;}
test('compact scale is identical before/after fullscreen at a fixed visual viewport scale',()=>{
 const m=mobile();assert.equal(m.uiScale(1),.74);assert.equal(m.worldScale(760,340,1),m.worldScale(800,400,1));
 assert.equal(m.worldScale(1000,599,1),m.worldScale(1100,650,1));
});
test('browser shrink reset is compensated once for HUD and world',()=>{
 const m=mobile();for(const scale of [.73,.74,.85,1]){
 assert.ok(Math.abs(m.uiScale(scale)*scale-.74)<1e-10);
 assert.ok(Math.abs(m.worldScale(1000,500,scale)*scale-m.worldScale(1000,500,1))<1e-10);
 }
});
test('portrait profile is stable; user zoom above 1 remains available',()=>{
 const m=mobile();assert.equal(m.worldScale(390,650,1),m.worldScale(390,850,1));assert.equal(m.uiScale(2),.74);
 assert.equal(m.uiScale(NaN),.74);assert.ok(Number.isFinite(m.uiScale(-1)));
});
