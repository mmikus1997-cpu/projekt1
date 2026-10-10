/* 0.17 chronicle in the real UI: org founding + city prestige goal land in the shared home chronicle panel (player and admin view), prestige contract kind reveals the district picker (0.15 leftover), card + chronicle coexist on home; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3202';
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
 const a=await account('ka_'+suffix,'Kronikarz Miasta');
 // fresh world: no chronicle panel on home
 assert.equal(await a.locator('.chronicle-panel').count(),0,'chronicle hidden on a fresh world');
 // A founds an org; while the contract accordion is open the 0.15 fix must show the district picker for prestige goals
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await a.fill('#org-name','Kronikowa QA');await a.fill('#org-tag','KRQ');await a.fill('#org-description','Ekipa z historia.');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 await a.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Ustaw wspólny cel'));t.click();});
 await a.waitForSelector('#org-contract-kind',{timeout:10000});
 assert.equal(await a.locator('#org-contract-district-wrap').isVisible(),false,'district picker hidden for fund goals');
 await a.selectOption('#org-contract-kind','prestige');
 assert.equal(await a.locator('#org-contract-district-wrap').isVisible(),true,'district picker appears for prestige goals');
 await a.selectOption('#org-contract-kind','fund');
 assert.equal(await a.locator('#org-contract-district-wrap').isVisible(),false,'district picker hides back for fund goals');
 // home shows the founding entry
 await a.click('#nav-city');await a.waitForFunction(()=>!Network.busy);
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForSelector('.chronicle-panel',{timeout:15000});
 assert.match(await a.locator('.chronicle-panel').innerText(),/Powstaje organizacja Kronikowa QA \[KRQ\]/);
 await a.screenshot({path:path.join(__dirname,'chronicle-founded.png'),fullPage:true});
 // B becomes admin (disposable QA fixture), re-enters, creates the prestige city goal from the panel
 const b=await account('kb_'+suffix,'Admin Miasta');
 execFileSync('python',['manage.py','--db',DB,'grant-admin','kb_'+suffix]);
 await b.goto(BASE);await b.waitForSelector('#auth-form');
 await b.fill('#auth-username','kb_'+suffix);await b.fill('#auth-password',PASSWORD);await b.click('#auth-form [type=submit]');
 await b.waitForSelector('.world-grid');await b.click('[data-world="1"]');
 await b.waitForFunction(()=>Network.world?.id===1,{timeout:20000});
await b.waitForSelector('[data-online=brief-close]',{timeout:2500}).then(()=>b.click('[data-online=brief-close]')).catch(()=>{});
 await b.click('[data-online=dismiss-tutorial]').catch(()=>{});
 await b.waitForFunction(()=>!Network.busy,{timeout:20000});
 await b.click('#nav-admin');await b.waitForFunction(()=>Network.panel==='admin'&&!Network.busy,{timeout:15000});
 await b.click('[data-online=city-event]');
 await b.waitForSelector('#city-event-form',{timeout:10000});
 await b.selectOption('#ce-world','1');
 await b.fill('#ce-name','Noc Prestiżu w Porcie');
 await b.fill('#ce-desc','Wspólny cel testowego miasta.');
 await b.selectOption('#ce-kind','prestige');
 await b.selectOption('#ce-district','Portowe');
 await b.fill('#ce-target','100');
 await b.selectOption('#ce-hours','24');
 await b.click('#city-event-form [type=submit]');
 await b.waitForFunction(()=>document.querySelector('.admin-events-panel')?.innerText.includes('aktywny'),{timeout:15000});
 // the goal announcement is shared history: admin sees it in the chronicle on home
 await b.click('#nav-city');await b.waitForFunction(()=>!Network.busy);
 await b.evaluate(()=>Network.refresh().catch(()=>{}));
 await b.waitForSelector('.chronicle-panel',{timeout:15000});
 assert.match(await b.locator('.chronicle-panel').innerText(),/Miasto ogłasza wyzwanie: Noc Prestiżu w Porcie/);
 // A sees both the active goal card and the chronicle entry
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForSelector('.city-event-card',{timeout:15000});
 const homeText=await a.locator('.city-event-card').innerText();
 assert.match(homeText,/Noc Prestiżu w Porcie/);assert.match(homeText,/PRESTIŻ ORGANIZACJI · PORT/);
 assert.match(await a.locator('.chronicle-panel').innerText(),/Miasto ogłasza wyzwanie: Noc Prestiżu w Porcie/);
 // A funds the org and invests 100 into Port: the goal completes and the chronicle records it on top
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy,{timeout:15000});
 await a.fill('#org-fund-amount','300');await a.click('#org-fund-form [type=submit]');
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 // full re-entry: the community panel re-rendered after the fund POST, so navigate away and back for a fresh DOM
 await a.click('#nav-city');await a.waitForFunction(()=>!Network.busy);
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy,{timeout:15000});
 await a.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Inwestuj fundusz'));t.click();});
 await a.waitForSelector('[data-extra=org-invest]:not([disabled])',{timeout:15000});
 await a.evaluate(()=>document.querySelector('[data-extra=org-invest][data-district=Portowe]').click());
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 await a.click('#nav-city');await a.waitForFunction(()=>!Network.busy);
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForFunction(()=>!Network.packet.cityEvent,{timeout:15000});
 // 0.39 hardening: czekaj na wpis ZALICZONE w DOM (widoczność pierwszego elementu bywa loterią pod obciążeniem)
 await a.waitForFunction(()=>{const ok=[...document.querySelectorAll('.chronicle-panel .chronicle-item')].some(x=>x.dataset.kind==='city_done');if(!ok&&!Network.busy)Network.refresh().catch(()=>{});return ok;},null,{timeout:30000,polling:250});
 assert.equal(await a.locator('.chronicle-panel .chronicle-item').count(),3,'three chronicle entries: done, announcement, founding');
 const first=await a.locator('.chronicle-panel .chronicle-item').first().innerText();
 assert.match(first,/ZALICZONE/);assert.match(first,/Wyzwanie „Noc Prestiżu w Porcie” zaliczone/);assert.match(first,/Pioniera/);
 const panelText=await a.locator('.chronicle-panel').innerText();
 assert.match(panelText,/Miasto ogłasza wyzwanie: Noc Prestiżu w Porcie/);
 assert.match(panelText,/Powstaje organizacja Kronikowa QA \[KRQ\]/);
 await a.screenshot({path:path.join(__dirname,'chronicle-desktop.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'chronicle overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'chronicle-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.17: org founding and city prestige goal land in the shared chronicle panel for player and admin, prestige contract kind reveals district picker, completed goal recorded on top with Pionier note; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
