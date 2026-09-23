/* Browser regression for 0.3. Run with tools/run_browser_smoke.py.
   All gameplay uses UI/keyboard/touch input and a fresh server database. The
   test-only WebSocket/canvas taps observe public packets and rendered text;
   they do not change game state, time, levels or production client code. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const url = process.env.GAME_URL || 'http://127.0.0.1:8080';
const output = process.env.QA_DIR || '/tmp/bractwo-03-qa';
fs.mkdirSync(output, { recursive: true });

(async () => {
  const browser = await chromium.launch({executablePath: process.env.CHROMIUM_BIN || undefined,
    headless:true,args:['--no-sandbox','--disable-dev-shm-usage']});
  const errors=[], checks=[];
  const desktop=await browser.newContext({viewport:{width:1440,height:900}});
  const mobile=await browser.newContext({viewport:{width:844,height:390},isMobile:true,hasTouch:true,deviceScaleFactor:1});
  for(const context of [desktop,mobile]) await context.addInitScript(()=>{
    window.__qaSent=[];window.__qaChats=[];window.__qaStates=[];window.__qaEffects=[];window.__qaDrawn=[];
    const effectIds=new Set(), NativeSocket=window.WebSocket;
    window.WebSocket=class extends NativeSocket {
      constructor(...args){super(...args);this.addEventListener('message',event=>{
        const data=JSON.parse(event.data);
        if(data.type==='state'){
          window.__qaState=data;window.__qaStates.push(data);
          if(window.__qaStates.length>350)window.__qaStates.shift();
          for(const effect of data.effects||[])if(!effectIds.has(effect.id)){
            effectIds.add(effect.id);window.__qaEffects.push(effect);
          }
        }
        if(data.type==='welcome')window.__qaWelcome=data;
        if(data.type==='chat')window.__qaChats.push(data);
      });}
      send(message){window.__qaSent.push({at:performance.now(),packet:JSON.parse(message)});return super.send(message);}
    };
    const fillText=CanvasRenderingContext2D.prototype.fillText;
    CanvasRenderingContext2D.prototype.fillText=function(text,...args){
      if(this.canvas.id==='world'){
        window.__qaDrawn.push({text:String(text),at:performance.now()});
        if(window.__qaDrawn.length>3000)window.__qaDrawn.splice(0,1000);
      }
      return fillText.call(this,text,...args);
    };
  });
  const first=await desktop.newPage(),second=await mobile.newPage();
  for(const page of [first,second]){
    page.setDefaultTimeout(12000);
    page.on('pageerror',error=>errors.push(error.message));
  }
  const password='qa-world-034-password';
  const player=page=>page.evaluate(()=>window.__qaState.players.find(p=>p.id===window.__qaWelcome.id));
  const waitPlayer=(page,predicate,arg,timeout=12000)=>page.waitForFunction(({source,arg})=>{
    const p=window.__qaState?.players.find(p=>p.id===window.__qaWelcome?.id);
    return p && (new Function('p','arg',`return (${source})(p,arg)`))(p,arg);
  },{source:predicate.toString(),arg},{timeout});
  const check=message=>{checks.push(message);console.log(`PASS ${message}`);};
  const screenshot=(page,name)=>page.screenshot({path:path.join(output,name+'.png')});
  async function register(page,name,classId){
    await page.goto(url);
    await page.locator('#registerTab').click();
    await page.locator('#nameInput').fill(name);
    await page.locator('#passwordInput').fill(password);
    await page.locator(`#classPicker [data-class="${classId}"]`).click();
    await page.locator('#connectButton').click();
    await page.locator('#gameUI').waitFor({state:'visible'});
    await waitPlayer(page,(p,id)=>p.class_id===id,classId);
  }
  async function closePanel(page){
    if(await page.locator('#sidePanel').isVisible())await page.locator('#closePanel').click();
  }
  async function walk(page,x,y,{tolerance=26,timeout=22000}={}){
    await closePanel(page);
    const deadline=Date.now()+timeout;let active=[];
    try{
      while(Date.now()<deadline){
        const p=await player(page);assert(p.hp>0,'Player died while walking');
        if(Math.hypot(p.x-x,p.y-y)<tolerance)return;
        const keys=[];if(p.x<x-5)keys.push('d');if(p.x>x+5)keys.push('a');if(p.y<y-5)keys.push('s');if(p.y>y+5)keys.push('w');
        for(const key of active)if(!keys.includes(key))await page.keyboard.up(key);
        for(const key of keys)if(!active.includes(key))await page.keyboard.down(key);
        active=keys;await page.waitForTimeout(70);
      }
      const p=await player(page);throw new Error(`Walk failed ${x},${y}; got ${p.x},${p.y}`);
    }finally{for(const key of active)await page.keyboard.up(key);}
  }
  async function hotkeyChatChecks(){
    // This is deliberately the first keyboard action after login. A hidden auth
    // input retaining focus used to prevent gameplay Enter from opening chat.
    await first.keyboard.press('Enter');
    await first.locator('#chatForm').waitFor({state:'visible'});
    assert.equal(await first.locator('#chatInput').evaluate(el=>el===document.activeElement),true);
    const before=await player(first), sent=await first.evaluate(()=>window.__qaSent.length);
    await first.keyboard.type('wasd f 1 2 ');
    await first.keyboard.down('w');await first.waitForTimeout(350);await first.keyboard.up('w');
    await first.keyboard.press('f');await first.keyboard.press('Space');
    const after=await player(first);
    assert(Math.hypot(after.x-before.x,after.y-before.y)<1,'Typing moved the player');
    assert.equal(after.mana,before.mana);
    assert.deepEqual(after.potions,before.potions);
    const bad=await first.evaluate(start=>window.__qaSent.slice(start).filter(({packet:p})=>
      ['attack','ability','potion'].includes(p.type)||(p.type==='input'&&(p.x||p.y))),sent);
    assert.deepEqual(bad,[],'Typing leaked game actions');
    await first.keyboard.press('Escape');
    await first.locator('#chatForm').waitFor({state:'hidden'});
    assert.equal(await first.evaluate(()=>window.__qaChats.length),0);
    check('Enter immediately after login opens focused chat; WASD, F, Space and potion keys type only; Escape cancels without sending.');
  }
  async function questJourney(){
    const start=await player(first);
    const quest=start.quests.find(q=>q.status==='available'&&q.objectives.some(o=>o.type==='kill'&&o.target==='rat'));
    assert(quest,'No available introductory rat quest');
    const npc=await first.evaluate(id=>window.__qaWelcome.world.npcs.find(n=>n.id===id),quest.npc_id);
    assert(npc,'Introductory quest NPC missing');
    await walk(first,npc.x,npc.y,{tolerance:30});
    await first.keyboard.press('e');
    await first.locator('#journalView').waitFor({state:'visible'});
    await first.locator(`[data-quest-accept="${quest.id}"]`).click();
    await waitPlayer(first,(p,id)=>p.quests.some(q=>q.id===id&&q.status==='active'),quest.id);
    await closePanel(first);
    await first.keyboard.press('j');await first.locator('#journalView').waitFor({state:'visible'});
    await screenshot(first,'journal-desktop');await closePanel(first);
    assert((await first.locator('#questTrackerTitle').innerText()).trim().length>0);
    check('E at the quest NPC opens the journal; accepting a real quest updates the tracker and J reopens its progress.');
    await first.keyboard.down('Space');
    const deadline=Date.now()+85000;
    try{
      while(Date.now()<deadline){
        const p=await player(first),q=p.quests.find(q=>q.id===quest.id);
        if(q.status==='ready')break;
        assert(p.hp>0,'Knight died in introductory quest');
        if(p.hp<p.max_hp*.5 && p.potions.health_potion>0 && !p.potion_cooldown)await first.keyboard.press('1');
        const rat=await first.evaluate(()=>{
          const p=window.__qaState.players.find(p=>p.id===window.__qaWelcome.id);
          return window.__qaState.enemies.filter(e=>e.kind==='rat'&&e.alive)
            .sort((a,b)=>Math.hypot(a.x-p.x,a.y-p.y)-Math.hypot(b.x-p.x,b.y-p.y))[0];
        });
        if(rat)await walk(first,rat.x,rat.y,{tolerance:55,timeout:15000});
        await first.waitForTimeout(750);
      }
    }finally{await first.keyboard.up('Space');}
    await waitPlayer(first,(p,id)=>p.quests.some(q=>q.id===id&&q.status==='ready'),quest.id);
    const ready=await player(first);assert(ready.kills>=3);assert(ready.level>1||ready.xp>0);
    await first.keyboard.press('j');
    const claim=first.locator(`[data-quest-claim="${quest.id}"]`);
    assert.equal(await claim.isEnabled(),false,'Remote quest claim was enabled');
    await closePanel(first);await screenshot(first,'hunt-desktop');
    await walk(first,npc.x,npc.y,{tolerance:30});
    await first.keyboard.press('e');await claim.click();
    await waitPlayer(first,(p,id)=>p.quests.some(q=>q.id===id&&q.status==='claimed'),quest.id);
    const rewarded=await player(first);
    assert(rewarded.gold>ready.gold);assert(rewarded.level>1&&rewarded.speed>100,'Quest level increase did not gradually increase movement speed');
    await screenshot(first,'quest-reward-desktop');await closePanel(first);
    check('A fresh knight kills three rats with normal movement/attacks, levels up, cannot claim remotely, and returns to the NPC for the quest reward.');
    // Walk the next expedition to a real landmark if the catalogue exposes the
    // intended mill discovery. No world position is injected into the client.
    const next=(await player(first)).quests.find(q=>q.status==='available'&&q.objectives.some(o=>o.type==='discover'));
    if(next){
      const giver=await first.evaluate(id=>window.__qaWelcome.world.npcs.find(n=>n.id===id),next.npc_id);
      await walk(first,giver.x,giver.y,{tolerance:30});await first.keyboard.press('e');
      await first.locator(`[data-quest-accept="${next.id}"]`).click();await closePanel(first);
      const objective=next.objectives.find(o=>o.type==='discover');
      const place=await first.evaluate(id=>window.__qaWelcome.world.landmarks.find(n=>n.id===id),objective.target);
      assert(place,'Discovery objective has no landmark');
      // Approach the mill from the east meadow to avoid houses in Przystan.
      await walk(first,Math.max(850,giver.x),giver.y,{tolerance:28});
      await walk(first,Math.max(850,giver.x),place.y,{tolerance:28});
      await walk(first,place.x,place.y,{tolerance:55});
      await waitPlayer(first,(p,id)=>p.discoveries.includes(id),place.id);
      await first.keyboard.press('j');
      await first.locator(`#discoveryList [data-landmark-id="${place.id}"]`).waitFor();
      await screenshot(first,'exploration-desktop');await closePanel(first);
      const beforeReward=await player(first);
      await walk(first,850,place.y,{tolerance:28});await walk(first,850,giver.y,{tolerance:28});
      await walk(first,giver.x,giver.y,{tolerance:30});await first.keyboard.press('e');
      await first.locator(`[data-quest-claim="${next.id}"]`).click();
      await waitPlayer(first,(p,id)=>p.quests.some(q=>q.id===id&&q.status==='claimed'),next.id);
      const rewarded=await player(first);
      assert(rewarded.inventory.length>beforeReward.inventory.length,'Mill quest did not award its guaranteed weapon');
      assert(rewarded.quests.some(q=>q.status==='available'&&q.objectives.some(o=>o.target==='goblin')),'Goblin expedition did not unlock');
      await closePanel(first);await first.keyboard.press('i');
      const weapon=rewarded.inventory.find(item=>item.template===`${rewarded.class_id}_weapon_2`);
      assert(weapon,'Mill quest awarded no matching class weapon');
      await first.locator(`[data-equip="${weapon.uid}"]`).click();
      await waitPlayer(first,(p,n)=>p.attack===n+5,rewarded.attack);await closePanel(first);
      check('The mill is discovered in the atlas; returning grants a usable class weapon (+5 attack) and unlocks the goblin expedition.');
    }
  }
  async function mageEffects(){
    await first.locator('#logoutButton').click();await register(first,'Selene','mage');
    // Northern meadow lies outside protection and within range of wolves. Stop
    // early enough to cast at range and strafe east while the enemy is north.
    await walk(first,590,900,{tolerance:12});
    const p=await player(first),marker=await first.evaluate(()=>window.__qaEffects.length);
    await first.keyboard.down('d');await first.keyboard.down('Space');
    await first.waitForFunction(({id,start})=>window.__qaEffects.slice(start).some(e=>e.source_id===id&&e.kind==='magic_bolt'),{id:p.id,start:marker});
    await first.keyboard.up('Space');await first.waitForTimeout(130);
    const aim=await first.evaluate(({id,start})=>{
      const effect=window.__qaEffects.slice(start).find(e=>e.source_id===id&&e.kind==='magic_bolt');
      return {effect,player:window.__qaState.players.find(p=>p.id===id),states:window.__qaStates.filter(s=>s.effects?.some(e=>e.id===effect.id)).slice(-5)};
    },{id:p.id,start:marker});
    const effect=aim.effect,dx=effect.target_x-effect.x,dy=effect.target_y-effect.y,len=Math.hypot(dx,dy);
    assert(len>1,'Mage effect has no actual target');
    assert.equal(effect.target_id?.startsWith('e'),true,'Mage effect did not target a monster');
    assert(Math.abs(aim.player.attack_facing[0]-dx/len)<.03&&Math.abs(aim.player.attack_facing[1]-dy/len)<.03,'Mage aim does not point at hit target');
    assert(Math.hypot(aim.player.attack_facing[0]-aim.player.facing[0],aim.player.attack_facing[1]-aim.player.facing[1])>.3,'Test did not exercise sideways movement and separate attack aim');
    for(const state of aim.states){
      const same=state.effects.find(e=>e.id===effect.id);assert.deepEqual([same.x,same.y,same.target_x,same.target_y],[effect.x,effect.y,effect.target_x,effect.target_y]);
    }
    await screenshot(first,'mage-moving-shot');await first.keyboard.up('d');
    check('A mage strafes while shooting: the real target and projectile endpoints stay fixed and attack aim differs from walking direction.');
    const ringStart=await first.evaluate(()=>window.__qaEffects.length);
    await first.keyboard.press('f');
    await first.waitForFunction(({id,start})=>window.__qaEffects.slice(start).some(e=>e.source_id===id&&e.kind==='fire_ring'),{id:p.id,start:ringStart});
    await first.waitForTimeout(100);await screenshot(first,'mage-fire-ring-early');
    await first.waitForTimeout(230);await screenshot(first,'mage-fire-ring-late');
    const ring=await first.evaluate(({id,start})=>window.__qaEffects.slice(start).find(e=>e.source_id===id&&e.kind==='fire_ring'),{id:p.id,start:ringStart});
    assert.equal(ring.radius,320);assert(ring.duration>=.8);
    await waitPlayer(first,p=>p.ability_cooldown>0&&p.mana<p.max_mana);
    const potions=(await player(first)).potions.mana_potion;
    await first.keyboard.press('2');await waitPlayer(first,(p,n)=>p.potions.mana_potion===n-1,potions);
    check('Mage fire ring emits a timed area effect, is captured at two animation phases, costs mana, and the potion hotkey consumes an owned potion.');
  }
  let failure;
  try{
    await first.goto(url);await screenshot(first,'login-desktop');
    await register(first,'Aren','knight');await hotkeyChatChecks();
    await register(second,'Lira','druid');
    await Promise.all([first,second].map(p=>p.waitForFunction(()=>window.__qaState.players.length===2)));
    assert.notEqual((await player(first)).max_mana,(await player(second)).max_mana);
    check('Knight and Druid registration creates distinct class stats in the same shared world.');
    const a=await player(first);assert.equal(a.speed,100);
    await first.keyboard.down('d');await first.waitForTimeout(1000);await first.keyboard.up('d');await first.waitForTimeout(160);
    const moved=await player(first),distance=Math.hypot(moved.x-a.x,moved.y-a.y);
    assert(distance>75&&distance<135,`Level-one movement should be about 100 px/s, got ${distance}`);
    await second.waitForFunction(({id,x})=>window.__qaState.players.find(p=>p.id===id).x>x+70,{id:a.id,x:a.x});
    check('Level-one movement is about 100 px/s and is visible to the second client.');
    await first.keyboard.press('e');await first.locator('#inventoryView').waitFor({state:'visible'});
    assert.equal(await first.locator('#journalView').isVisible(),false,'E at merchant chose an overlapping quest NPC');
    assert.equal(await first.locator('#equipmentSlots').locator(':scope > *').count(),3);
    const equippedBefore=await player(first),armorUid=equippedBefore.equipment.armor;
    await first.locator('[data-unequip="armor"]').click();await waitPlayer(first,(p,n)=>p.armor===n-1,equippedBefore.armor);
    await first.locator(`[data-equip="${armorUid}"]`).click();await waitPlayer(first,(p,n)=>p.armor===n,equippedBefore.armor);
    assert.equal((await player(first)).gold,0);assert.equal(await first.locator('#buyHealth').isEnabled(),false);
    await screenshot(first,'inventory-desktop');
    check('E beside the merchant opens inventory despite overlapping NPC ranges; equipment changes authoritative armor and purchases without gold are disabled.');
    await first.locator('#playersTab').click();await first.locator('#playersList button[data-action="invite"]').first().click();
    await second.locator('#partyInvite').waitFor({state:'visible'});await second.locator('#acceptInvite').click();
    await Promise.all([first,second].map(p=>waitPlayer(p,p=>p.party_members?.length===2)));
    await closePanel(first);
    check('Party invitation and acceptance work between desktop and touch clients.');
    await first.locator('#mapButton').click();await first.keyboard.press('Enter');
    await first.locator('#chatForm').waitFor({state:'visible'});
    assert.equal(await first.locator('#chatInput').evaluate(el=>el===document.activeElement),true);
    await first.keyboard.press('Control+A');await first.keyboard.press('Backspace');
    const speech='Razem na wyprawę!';await first.keyboard.type(speech);await first.keyboard.press('Enter');
    await second.waitForFunction(text=>window.__qaChats.some(p=>p.text===text),speech);
    await second.waitForFunction(({id,text})=>window.__qaState.players.some(p=>p.id===id&&p.speech_text===text),{id:a.id,text:speech});
    await second.locator('#chatLog').getByText(speech,{exact:false}).waitFor();
    await second.waitForFunction(text=>window.__qaDrawn.some(d=>d.text===text&&performance.now()-d.at<1000),speech);
    await screenshot(second,'speech-other-client');
    check('Enter opens chat with a HUD button focused; another client receives the public speech, draws it over the character and retains it in the chat log.');
    await first.locator('#mapButton').click();
    const joy=await second.locator('#joystick').boundingBox();assert(joy);
    const beforeTouch=await player(second),cdp=await mobile.newCDPSession(second),cx=joy.x+joy.width/2,cy=joy.y+joy.height/2;
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x:cx,y:cy,id:1}]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:cx,y:cy-35,id:1}]});await second.waitForTimeout(600);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
    await waitPlayer(second,(p,y)=>p.y<y-20,beforeTouch.y);
    await screenshot(first,'game-desktop');await screenshot(second,'game-mobile-landscape');
    await second.setViewportSize({width:390,height:844});await second.waitForTimeout(150);await screenshot(second,'game-mobile-portrait');
    assert.equal(await second.evaluate(()=>document.documentElement.scrollWidth>innerWidth+1),false);
    await second.locator('#inventoryButton').click();await screenshot(second,'inventory-mobile');await closePanel(second);
    check('Real touch movement works; desktop, landscape, portrait and mobile inventory render without page overflow.');
    await first.locator('#partyButton').click();await first.locator('#playersList button[data-action="target"]').first().click();await closePanel(first);
    await first.locator('#targetCard').waitFor({state:'visible'});assert.equal((await player(first)).pvp_safety,true);
    await first.locator('#safetyButton').click();await waitPlayer(first,p=>p.pvp_safety===false);
    const defender=await player(second);await first.keyboard.down('Space');await first.waitForTimeout(450);await first.keyboard.up('Space');
    assert.equal((await player(second)).hp,defender.hp);assert.equal((await player(first)).skull,'none');await first.locator('#clearTarget').click();
    check('Explicit PvP target and safety toggle work; a protected beginner in town takes no damage and causes no skull.');
    const id=(await player(first)).id;
    await first.locator('#logoutButton').click();await first.locator('#authScreen').waitFor({state:'visible'});
    await first.locator('#passwordInput').fill(password);await first.locator('#connectButton').click();await first.locator('#gameUI').waitFor({state:'visible'});
    await waitPlayer(first,p=>p.pvp_safety===true);assert.equal((await player(first)).id,id);assert.equal((await player(first)).class_id,'knight');
    assert(!(await first.evaluate(()=>JSON.stringify(localStorage))).includes(password));
    check('Relog preserves account/class and resets PvP safety; localStorage contains no password.');
    await questJourney();await mageEffects();
    await first.locator('#logoutButton').click();await register(first,'Rowan','paladin');assert.equal((await player(first)).weapon,'bow');
    check('All four registration choices were used against the real server; Paladin uses a bow.');
    assert.deepEqual(errors,[]);
  }catch(error){
    failure=error;console.error(error);
    await Promise.allSettled([screenshot(first,'failure-desktop'),screenshot(second,'failure-mobile')]);
  }finally{
    if(!failure)for(const name of ['failure-desktop.png','failure-mobile.png'])fs.rmSync(path.join(output,name),{force:true});
    const report={ok:!failure,checks,errors,...(failure?{failure:String(failure.stack||failure)}:{})};
    fs.writeFileSync(path.join(output,'browser-report.json'),JSON.stringify(report,null,2));
    console.log(JSON.stringify(report,null,2));await browser.close();
  }
  if(failure)throw failure;
})().catch(error=>{console.error(error);process.exitCode=1;});
