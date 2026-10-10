/* 0.12 events center + global season ranking in the real UI: nav badge, unread rows, mark-read, acceptance event, season panel; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3131';
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
 const a=await account('ea_'+suffix,'Dowodzaca Zdarzen');
 const b=await account('eb_'+suffix,'Kandydat Zdarzen');
 // A founds the org [TGE].
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await a.fill('#org-name','Ekipa Zdarzen QA');await a.fill('#org-tag','TGE');await a.fill('#org-description','Test centrum zdarzen.');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 // B applies through the directory dialog (open verified), submit via the transport.
 await b.click('#nav-community');await b.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 assert.equal(await b.locator('[data-extra=org-apply]').count(),1);
 await b.evaluate(()=>document.querySelector('[data-extra=org-apply]').click());
 await b.waitForSelector('#org-apply-text',{timeout:10000});
 await b.evaluate(()=>document.querySelector('#network-dialog-close').click());
 await b.evaluate(()=>Network.api(`/worlds/${Network.world.id}/organizations/apply`,'POST',{org_id:+document.querySelector('#org-apply-form').dataset.org,text:'Prosba z centrum zdarzen testu.'}));
 // A gets a badge on the nav button and an unread event row.
 await a.waitForFunction(()=>!document.querySelector('#community-badge').hidden&&document.querySelector('#community-badge').textContent==='1',{timeout:15000});
 await a.evaluate(()=>Extras.showCommunity());await a.waitForFunction(()=>!Network.busy);
 const row=await a.locator('.events-panel .event-row').first().innerText();
 assert.match(row,/Podanie do \[TGE\]/);assert.match(row,/Kandydat Zdarzen/);
 assert.equal(await a.locator('.events-panel .event-row.unread').count(),1);
 await a.screenshot({path:path.join(__dirname,'events-desktop.png'),fullPage:true});
 await a.evaluate(()=>document.querySelector('[data-extra=events-read]').click());
 await a.waitForFunction(()=>document.querySelector('#community-badge').hidden,{timeout:15000});
 await a.waitForFunction(()=>!Network.busy&&document.querySelectorAll('.events-panel .event-row.unread').length===0,{timeout:15000});
 assert.equal(await a.locator('.events-panel .event-row.unread').count(),0);
 // A accepts: B receives the acceptance event and badge.
 await a.waitForSelector('[data-extra=app-accept]',{timeout:15000});
 await a.evaluate(()=>document.querySelector('[data-extra=app-accept]').click());
 await b.waitForFunction(()=>!document.querySelector('#community-badge').hidden,{timeout:15000});
 await b.evaluate(()=>Extras.showCommunity());await b.waitForFunction(()=>!Network.busy);
 assert.match(await b.locator('.events-panel').innerText(),/Przyjęto Cię do organizacji \[TGE\]/);
 // Global season ranking panel exists with the personal line and world column.
 await a.click('#nav-ranking');await a.waitForFunction(()=>Network.panel==='ranking'&&!Network.busy,{timeout:15000});
 const season=await a.locator('.season-panel').innerText();
 assert.match(season,/Globalny ranking · sezony/);assert.match(season,/Twoja pozycja globalna/);assert.match(season,/CITY 1/);assert.match(season,/bieżący/);
 await a.screenshot({path:path.join(__dirname,'ranking-global.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'events overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'events-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.12: application lights the nav badge and unread event row, mark-read clears it, acceptance event reaches the applicant, global season panel with personal place; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
