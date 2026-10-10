/* 0.16 city events in the real UI: admin creates a prestige goal from the panel, player sees the city card, org invest completes it, Pioneer badge event + admin history; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3201';
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
 const a=await account('ca_'+suffix,'Mieszkaniec Miasta');
 const b=await account('cb_'+suffix,'Admin Miasta');
 // B: org for the prestige goal.
 await b.click('#nav-community');await b.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await b.fill('#org-name','Eventowa QA');await b.fill('#org-tag','EVQ');await b.fill('#org-description','Cel miasta w tescie.');
 await b.click('#org-create-form [type=submit]');await b.waitForSelector('#org-fund-form');
 await b.fill('#org-fund-amount','300');await b.click('#org-fund-form [type=submit]');
 await b.waitForFunction(()=>!Network.busy);
 // B becomes admin via the disposable QA fixture, then re-enters to refresh the session role.
 execFileSync('python',['manage.py','--db',DB,'grant-admin','cb_'+suffix]);
 await b.goto(BASE);await b.waitForSelector('#auth-form');
 await b.fill('#auth-username','cb_'+suffix);await b.fill('#auth-password',PASSWORD);await b.click('#auth-form [type=submit]');
 await b.waitForSelector('.world-grid');await b.click('[data-world="1"]');
 await b.waitForFunction(()=>Network.world?.id===1,{timeout:20000});
await b.waitForSelector('[data-online=brief-close]',{timeout:2500}).then(()=>b.click('[data-online=brief-close]')).catch(()=>{});
 await b.click('[data-online=dismiss-tutorial]').catch(()=>{});  // tutorial already dismissed for this character
 await b.waitForFunction(()=>!Network.busy,{timeout:20000});
 // Admin panel: create the city event through the dialog form.
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
 assert.match(await b.locator('.admin-events-panel').innerText(),/Noc Prestiżu w Porcie/);
 // A sees the city card on the home view.
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForSelector('.city-event-card',{timeout:15000});
 const card=await a.locator('.city-event-card').innerText();
 assert.match(card,/Noc Prestiżu w Porcie/);assert.match(card,/PRESTIŻ ORGANIZACJI · PORT/);assert.match(card,/0 /);
 await a.screenshot({path:path.join(__dirname,'cityevent-desktop.png'),fullPage:true});
 // B invests 100 into Port: the goal completes (back to community view first).
 await b.click('#nav-community');await b.waitForFunction(()=>Network.panel==='community'&&!Network.busy,{timeout:15000});
 await b.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Inwestuj fundusz'));t.click();});
 await b.waitForSelector('[data-extra=org-invest]:not([disabled])',{timeout:15000});
 await b.evaluate(()=>document.querySelector('[data-extra=org-invest][data-district=Portowe]').click());
 await b.waitForFunction(()=>!Network.busy);
 // A: card settles away; centrum zdarzeń announces the badge.
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForFunction(()=>!Network.packet.cityEvent,{timeout:15000});
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 assert.match(await a.locator('.events-panel').innerText(),/Event miejski „Noc Prestiżu w Porcie” zaliczony! Zdobywasz odznakę Pioniera/);
 // Admin history shows the finished event.
 await b.click('#nav-admin');await b.waitForFunction(()=>Network.panel==='admin'&&!Network.busy,{timeout:15000});
 assert.match(await b.locator('.admin-events-panel').innerText(),/zaliczony ✓/);
 await b.screenshot({path:path.join(__dirname,'cityevent-admin.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'city event overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'cityevent-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.16: admin creates city prestige goal from panel, home card shows shared progress, org invest completes it, Pioneer badge event on player side, admin history marks done; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
