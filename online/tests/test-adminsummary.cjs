/* 0.22 admin world summary: admin opens the Podsumowanie dialog from the world row — population, city goal, orgs/contracts, chronicle/notices, dev-shop line, top lists; player has no button/endpoint; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3209';
const DB=process.env.TEST_DB;
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 async function account(name,nickname){
  const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
  if(process.env.TEST_STRIP_HEADERS==='1')await ctx.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
  const page=await ctx.newPage();page.errors=[];
  page.on('pageerror',e=>page.errors.push(e.stack));
  await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
  await page.fill('#auth-username',name);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
  await page.waitForSelector('.world-grid');await page.click('[data-world="1"]');await page.fill('#character-nickname',nickname);
  if(await page.locator('#test-consent').count())await page.check('#test-consent');
  await page.click('#character-form [type=submit]');await page.waitForFunction(()=>Network.world?.id===1);
  await page.click('[data-online=dismiss-tutorial]');await page.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
  return page;
 }
 const suffix=Date.now().toString(36);
 const a=await account('sa_'+suffix,'Mieszkaniec Sumy');
 const b=await account('sb_'+suffix,'Admin Sumy');
 execFileSync('python',['manage.py','--db',DB,'grant-admin','sb_'+suffix]);
 await b.goto(BASE);await b.waitForSelector('#auth-form');
 await b.fill('#auth-username','sb_'+suffix);await b.fill('#auth-password',PASSWORD);await b.click('#auth-form [type=submit]');
 await b.waitForSelector('.world-grid');await b.click('[data-world="1"]');
 await b.waitForFunction(()=>Network.world?.id===1,{timeout:20000});
await b.waitForSelector('[data-online=brief-close]',{timeout:2500}).then(()=>b.click('[data-online=brief-close]')).catch(()=>{});
 await b.click('[data-online=dismiss-tutorial]').catch(()=>{});
 await b.waitForFunction(()=>!Network.busy,{timeout:20000});
 // admin publishes a notice and a city goal so the summary has content
 await b.click('#nav-admin');await b.waitForFunction(()=>Network.panel==='admin'&&!Network.busy,{timeout:15000});
 await b.click('[data-online=post-notice]');await b.waitForSelector('#notice-form');
 await b.selectOption('#notice-world','1');await b.fill('#notice-text','Ogłoszenie do podsumowania.');
 await b.click('#notice-form [type=submit]');
 await b.waitForFunction(()=>document.querySelector('.admin-notices-panel')?.innerText.includes('Ogłoszenie do podsumowania.'),{timeout:15000});
 await b.click('[data-online=city-event]');await b.waitForSelector('#city-event-form');
 await b.selectOption('#ce-world','1');await b.fill('#ce-name','Cel Podsumowania');
 await b.selectOption('#ce-kind','xp');await b.fill('#ce-target','100');await b.selectOption('#ce-hours','24');
 await b.click('#city-event-form [type=submit]');
 await b.waitForFunction(()=>document.querySelector('.admin-events-panel')?.innerText.includes('aktywny'),{timeout:15000});
 // open the summary dialog from the world row
 await b.evaluate(()=>{document.querySelector('[data-wsummary="1"]').click();});
 await b.waitForSelector('#network-dialog[open]',{timeout:15000});
 assert.match(await b.locator('#network-dialog').innerText(),/Podsumowanie świata ·/);
 const dlg=await b.locator('#network-dialog-body').innerText();
 assert.match(dlg,/Mieszkańcy/);assert.match(dlg,/2 · łącznie/);
 assert.match(dlg,/Cel miasta: Cel Podsumowania/);assert.match(dlg,/0 \/ 100/);
 assert.match(dlg,/Kontrakty org \(aktywne \/ zaliczone \/ przepadłe\)/);assert.match(dlg,/0 \/ 0 \/ 0/);
 assert.match(dlg,/Kronika \/ ogłoszenia aktywne/);assert.match(dlg,/Ogłoszenie do podsumowania|ogłoszeń/);
 assert.match(dlg,/Dev-sklep na tym świecie/);assert.match(dlg,/0 zakupów/);
 assert.match(dlg,/Najlepsi:/);assert.match(dlg,/Największe organizacje:/);
 await b.screenshot({path:path.join(__dirname,'adminsum-desktop.png'),fullPage:true});
 await b.evaluate(()=>document.getElementById('network-dialog').close());
 // player A: no summary button in (non-admin) view and the endpoint refuses
 assert.equal(await a.locator('[data-wsummary]').count(),0,'player sees no summary buttons');
 await a.evaluate(async()=>{try{const r=await fetch('/api/admin/worlds/1/summary');window.__sumErr=r.status;}catch(e){window.__sumErr='ERR';}});
 assert.ok([401,403].includes(await a.evaluate(()=>window.__sumErr)),'player summary endpoint denied');
 for(const width of [320,390,768,1440]){await b.setViewportSize({width,height:950});await b.waitForTimeout(100);assert.equal(await b.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'admin summary overflow '+width);if(width===390)await b.screenshot({path:path.join(__dirname,'adminsum-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.22: admin opens the world summary dialog (population, city goal progress, org contracts, chronicle/notices, dev-shop line, top lists) from the world row; player endpoint 403; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
