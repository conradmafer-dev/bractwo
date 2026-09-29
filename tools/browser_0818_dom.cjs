/* Focused real-browser controller QA, without Python/world/game.js/WebSockets.
 * Existing index DOM + production CSS; only windows.js and mobile.js execute.
 * The about:blank fixture deliberately does not test localStorage persistence.
 */
const fs=require('node:fs'),path=require('node:path'),os=require('node:os'),assert=require('node:assert/strict');
const {chromium}=require(path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright'));
const root=path.resolve(__dirname,'..'),web=path.join(root,'web'),out=path.join(root,'docs/qa_0.8.18/dom');
fs.mkdirSync(out,{recursive:true});
const report={ok:false,status:'running',fixture:'Existing index DOM with inline production CSS; only windows.js/mobile.js execute; no gameplay, server or WebSocket.',limitations:['about:blank fixture does not verify localStorage persistence.'],checks:[],geometry:[],errors:[]};
const save=()=>fs.writeFileSync(path.join(out,'browser_results.json'),JSON.stringify(report,null,2));
const pass=(name,detail={})=>{report.checks.push({name,ok:true,...detail});save();process.stdout.write('PASS: '+name+'\n');};
let html=fs.readFileSync(path.join(web,'index.html'),'utf8').replace(/<script\b[^>]*>[\s\S]*?<\/script>/g,'');
html=html.replace(/<link rel="stylesheet" href="([^"]+)">/g,(_,file)=>'<style>'+fs.readFileSync(path.join(web,file),'utf8')+'</style>');
// Avoid unrelated native network requests in this explicitly static fixture.
html=html.replace(/<link\b[^>]*>/g,'');
const measure=()=>{
  const rect=el=>{const r=el.getBoundingClientRect();return {x:r.x,y:r.y,width:r.width,height:r.height,right:r.right,bottom:r.bottom};};
  const joy=rect(document.getElementById('joystick')),bar=rect(document.getElementById('spellbar'));
  const visible=el=>el.getClientRects().length&&getComputedStyle(el).visibility!=='hidden'&&!el.hasAttribute('data-hud-hidden');
  const candidates=[document.querySelector('.player-card'),...document.getElementById('hudLeftRail').children].filter(visible);
  const quest=rect(document.getElementById('questTracker')),top=Math.max(...candidates.map(el=>el.getBoundingClientRect().bottom));
  return {viewport:{width:innerWidth,height:innerHeight},joystick:joy,spellbar:bar,quest,upperBoundary:top,gaps:{left:joy.x,right:bar.x-joy.right,above:joy.y-top,below:innerHeight-joy.bottom}};
};
async function stable(page,selector){
  let previous,identical=0;
  for(let i=0;i<20;i++){
    const box=await page.locator(selector).boundingBox();
    assert.ok(box,'No box for '+selector);
    if(previous&&['x','y','width','height'].every(key=>Math.abs(previous[key]-box[key])<.25))identical++;else identical=0;
    if(identical>=3)return box;
    previous=box;await page.waitForTimeout(150);
  }
  throw Error('Bounds did not settle: '+selector);
}
async function toggle(page,touch){
  if(touch)await page.locator('#mobileMenuButton').click();
  await page.locator('#hudLayoutLock').click();
  if(touch)await page.locator('#mobileMenuClose').click();
}
async function drag(page,touch,dx,dy,selector='.player-card .window-grip'){
  let box=await page.locator(selector).boundingBox();
  if(!box&&selector==='.player-card .window-grip'){
    const card=await page.locator('.player-card').boundingBox();
    box={x:card.x+card.width-22,y:card.y+4,width:18,height:18};
  }
  assert.ok(box,'No drag target bounds');
  const x=box.x+box.width/2,y=box.y+box.height/2;
  if(touch){
    const cdp=await page.context().newCDPSession(page);
    await cdp.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{x,y}]});
    for(const part of [.25,.5,.75,1])await cdp.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{x:x+dx*part,y:y+dy*part}]});
    await cdp.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});await cdp.detach();
  }else{await page.mouse.move(x,y);await page.mouse.down();await page.mouse.move(x+dx,y+dy,{steps:5});await page.mouse.up();}
}
async function lockTest(page,touch,label){
  const initial=await stable(page,'.player-card');
  assert.equal(await page.locator('#hudLayoutLock').getAttribute('aria-pressed'),'true');
  const dx=touch?80:360,dy=touch?60:180;
  await drag(page,touch,dx,dy);
  const blocked=await stable(page,'.player-card');
  assert.ok(Math.abs(blocked.x-initial.x)<1&&Math.abs(blocked.y-initial.y)<1,'Default lock permitted movement');
  await toggle(page,touch);
  assert.equal(await page.locator('#hudLayoutLock').getAttribute('aria-pressed'),'false');
  await drag(page,touch,dx,dy);
  const moved=await stable(page,'.player-card');
  assert.ok(Math.abs(moved.x-initial.x)>20||Math.abs(moved.y-initial.y)>20,'Unlocked drag did not move the panel');
  await toggle(page,touch);
  assert.equal(await page.locator('#hudLayoutLock').getAttribute('aria-pressed'),'true');
  await drag(page,touch,50,40);
  const relocked=await stable(page,'.player-card');
  assert.ok(Math.abs(relocked.x-moved.x)<1&&Math.abs(relocked.y-moved.y)<1,'Relock permitted movement');
  await page.screenshot({path:path.join(out,label+'-relocked.png')});
  pass(label+': default lock, real drag after unlock, relock prevents further drag',{pointer:touch?'native CDP touch':'native mouse',initial,moved,relocked});
}
(async()=>{
  let browser,page,context;
  try{
    process.stdout.write('Launching one lightweight DOM browser\n');
    browser=await chromium.launch({executablePath:process.env.CHROMIUM_BIN||'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',headless:true,args:['--no-proxy-server']});
    for(const [width,height,touch,label] of [[734,390,true,'mobile'],[1280,720,false,'desktop']]){
      context=await browser.newContext({viewport:{width,height},isMobile:touch,hasTouch:touch,deviceScaleFactor:1});
      page=await context.newPage();page.setDefaultTimeout(60000);page.on('pageerror',error=>report.errors.push(String(error)));
      await page.setContent(html,{waitUntil:'domcontentloaded',timeout:60000});
      await page.addScriptTag({content:fs.readFileSync(path.join(web,'windows.js'),'utf8')});
      await page.addScriptTag({content:fs.readFileSync(path.join(web,'mobile.js'),'utf8')});
      await page.evaluate(()=>{
        document.getElementById('authScreen').hidden=true;
        document.getElementById('gameUI').hidden=false;
        document.getElementById('controlTip').hidden=true;
        const quest=document.getElementById('questTracker');quest.hidden=false;
        if(!quest.innerText.trim())quest.innerHTML='<span class="tracker-eyebrow">ZADANIE</span><strong>Szczury na łąkach</strong><span>Przykładowy stan zadania do pomiaru układu.</span>';
        const windows=BractwoWindows.create();windows.sync('IsolatedLayoutQA');BractwoMobile.create();
      });
      await stable(page,'.player-card');
      await page.screenshot({path:path.join(out,label+'-default.png')});
      if(touch){
        await stable(page,'#joystick');
        const geometry=await page.evaluate(measure);report.geometry.push(geometry);save();
        assert.ok(geometry.quest.height>0,'Quest is not visible in landscape fixture');
        assert.ok(Math.abs(geometry.gaps.left-geometry.gaps.right)<=2,'Joystick horizontal gaps differ');
        assert.ok(Math.abs(geometry.gaps.above-geometry.gaps.below)<=2,'Joystick vertical gaps differ');
        assert.ok(Math.min(...Object.values(geometry.gaps))>=0,'Joystick overlaps adjacent panels');
        pass('Visible quest landscape: joystick is centred between left edge/spells and bottom rail/viewport',{geometry});
      }
      await lockTest(page,touch,label);
      if(touch){
        await toggle(page,true);await drag(page,true,45,-35,'.movement-controls .window-grip');
        assert.ok((await page.locator('.movement-controls').getAttribute('class')).includes('hud-floating'),'Joystick did not become movable');
        await toggle(page,true);await page.locator('#mobileMenuButton').click();
        await page.getByRole('button',{name:'Przywróć domyślny układ i widoczność',exact:true}).click();
        await page.locator('#mobileMenuClose').click();
        assert.equal(await page.locator('#hudLayoutLock').getAttribute('aria-pressed'),'true');
        assert.ok(!(await page.locator('.movement-controls').getAttribute('class')).includes('hud-floating'));
        await stable(page,'#joystick');const geometry=await page.evaluate(measure);
        assert.ok(Math.abs(geometry.gaps.left-geometry.gaps.right)<=2&&Math.abs(geometry.gaps.above-geometry.gaps.below)<=2,'Reset did not centre joystick');
        await page.screenshot({path:path.join(out,'mobile-reset-locked.png')});
        pass('Reset while locked restores the default centred joystick',{geometry});
      }
      await context.close();context=null;
    }
    assert.deepEqual(report.errors,[]);report.ok=true;report.status='passed';
  }catch(error){report.status='failed';report.failure=String(error);report.stack=error.stack;process.stderr.write(String(error)+'\n');if(page&&!page.isClosed())try{await page.screenshot({path:path.join(out,'failure.png'),timeout:10000});}catch{}}
  finally{save();if(browser)await browser.close();}
  process.stdout.write(JSON.stringify({ok:report.ok,checks:report.checks.length,report:path.join(out,'browser_results.json')})+'\n');process.exitCode=report.ok?0:1;
})();
