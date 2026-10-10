/* 0.8 residences/rest/away-box in the real UI, over the restricted preview transport. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DIR=__dirname;
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 if(process.env.TEST_STRIP_HEADERS==='1')await ctx.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 const page=await ctx.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.stack));
 const name='idle_'+Date.now().toString(36);
 await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
 await page.fill('#auth-username',name);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');
 await page.click('[data-world="2"]');await page.fill('#character-nickname','Bazyl QA');
 if(await page.locator('#test-consent').count())await page.check('#test-consent');
 await page.click('#character-form [type=submit]');await page.waitForFunction(id=>Network.world?.id===id,2);
 await page.click('[data-online=dismiss-tutorial]');await page.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 async function acted(selector,test,arg){await page.click(selector);await page.waitForFunction(test,arg);await page.waitForFunction(()=>!Network.busy);}
 try{
  // Residence view: base regeneration shown, no residence yet.
  await page.evaluate(()=>GameApp.showView('residence'));await page.waitForFunction(()=>GameApp.view==='residence');
  assert.match(await page.locator('#view-residence .game-summary-bar').innerText(),/Regeneracja: 600 \/ h/);
  assert.equal(await page.locator('#view-residence .contract-card').count(),3);
  await page.screenshot({path:path.join(DIR,'residence-desktop.png'),fullPage:true});
  // Buy the first tier.
  await acted('[data-game=buy-residence][data-residence=studio-flat]',()=>GameApp.state.residence==='studio-flat');
  assert.match(await page.locator('#view-residence .game-summary-bar').innerText(),/Regeneracja: 720 \/ h/);
  assert.match(await page.locator('#view-residence .game-summary-bar').innerText(),/Kawalerka/);
  // Nap requires the rest of the flow: burn energy, start, wait, claim.

  execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE characters SET current_district=3 WHERE world_id=2');c.commit()",process.env.TEST_DB||'tests/qa-idle.sqlite3']);  // 0.45: inwentaryzacja w Centrum
  await page.evaluate(()=>Network.refresh());await page.waitForFunction(()=>Network.packet?.travelInfo?.district===3,null,{timeout:15000});
  await page.click('#nav-contracts');await page.waitForFunction(()=>GameApp.view==='contracts');
  await acted('[data-contract=inventory]',()=>GameApp.state.contracts.length===1);
  await page.evaluate(()=>GameApp.showView('residence'));await page.waitForFunction(()=>GameApp.view==='residence');
  await acted('[data-game=rest-start][data-rest=nap]',()=>!!GameApp.state.rest);
  assert.equal(await page.locator('#rest-claim').isDisabled(),true);
  assert.equal(await page.locator('.rest-option [data-game=rest-start]:not([disabled])').count(),0,'no second rest while one is running');
  await page.screenshot({path:path.join(DIR,'rest-progress.png'),fullPage:true});
  await page.waitForSelector('#rest-claim:not([disabled])',{timeout:30000});
  await acted('#rest-claim',()=>GameApp.state.rest===null);
  assert.equal(await page.evaluate(()=>Math.floor(GameApp.state.energy)),240);
  // Away box: quiet period longer than 30 in-game minutes (=30 s real on ×60).
  const stamp=Date.now();
  await page.evaluate(()=>GameApp.showView('cafe'));await page.waitForFunction(()=>GameApp.view==='cafe');await page.waitForSelector('.away-box',{timeout:60000});
  assert.match(await page.locator('.away-box').innerText(),/Witaj z powrotem/);
  assert.ok(Date.now()-stamp>=25000,'away box may only appear after the quiet period');
  await page.screenshot({path:path.join(DIR,'away-box.png'),fullPage:true});
  await page.click('[data-away-dismiss]');await page.waitForSelector('.away-box',{state:'detached'});
  // Layout coverage on mobile.
  await page.setViewportSize({width:390,height:900});await page.waitForTimeout(150);
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'residence overflow at 390px');
  await page.screenshot({path:path.join(DIR,'residence-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  assert.deepEqual(errors,[]);
  console.log('PASS 0.8: residence purchase + regen label, tiered rest with claim, away box after quiet period, dismissal, mobile layout; headers/cookies stripped.');
 }catch(e){await page.screenshot({path:path.join(DIR,'idle-fail.png'),fullPage:true});throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
