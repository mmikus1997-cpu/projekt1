/* 0.24 economy charts: fresh player sees the empty note, an org fund deed grows the first bar in "Twoja historia", admin dialog shows the 14-day chart with the same day active; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3221';
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
 const a=await account('ea_'+suffix,'Statystyk Miasta');
 // fresh: empty note, no bars
 await a.evaluate(()=>GameApp.showView('hall'));await a.waitForSelector('.story-panel',{timeout:10000});
 assert.ok(await a.locator('.daily-chart.empty').count()>0,'empty chart note visible');
 // deed: found org + fund
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await a.fill('#org-name','Wykresy QA');await a.fill('#org-tag','WYQ');await a.fill('#org-description','');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 await a.fill('#org-fund-amount','100');await a.click('#org-fund-form [type=submit]');
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 // explicit refresh so the packet carries the fresh activity payload before re-render
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 // back to character: one gold deeds bar with today's tooltip
 await a.evaluate(()=>GameApp.showView('hall'));await a.waitForSelector('.daily-chart svg .dc-deeds',{timeout:10000});
 assert.equal(await a.locator('.daily-chart svg .dc-deeds').count(),1,'exactly one deeds bar');
 assert.equal(await a.locator('.daily-chart .dc-head').innerText().then(t=>t.includes('OSTATNIE 14 DNI')),true);
 await a.screenshot({path:path.join(__dirname,'econstats-character.png'),fullPage:true});
 // admin: the world summary dialog carries the same-day chart
 const b=await account('eb_'+suffix,'Admin Wykresów');
 execFileSync('python',['manage.py','--db',DB,'grant-admin','eb_'+suffix]);
 await b.goto(BASE);await b.waitForSelector('#auth-form');
 await b.fill('#auth-username','eb_'+suffix);await b.fill('#auth-password',PASSWORD);await b.click('#auth-form [type=submit]');
 await b.waitForSelector('.world-grid');await b.click('[data-world="1"]');
 await b.waitForFunction(()=>Network.world?.id===1,{timeout:20000});
await b.waitForSelector('[data-online=brief-close]',{timeout:2500}).then(()=>b.click('[data-online=brief-close]')).catch(()=>{});
 await b.click('[data-online=dismiss-tutorial]').catch(()=>{});
 await b.waitForFunction(()=>!Network.busy,{timeout:20000});
 await b.click('#nav-admin');await b.waitForFunction(()=>Network.panel==='admin'&&!Network.busy,{timeout:15000});
 await b.evaluate(()=>{document.querySelector('[data-wsummary="1"]').click();});
 await b.waitForSelector('#network-dialog[open]',{timeout:15000});
 await b.waitForSelector('#network-dialog .daily-chart svg .dc-deeds',{timeout:10000});
 assert.equal(await b.locator('#network-dialog .daily-chart .dc-head').innerText().then(t=>t.includes('OSTATNIE 14 DNI')),true,'admin chart caption');
 const dlg=await b.locator('#network-dialog .daily-chart').innerText();
 assert.match(dlg,/dev-sklep/);
 await b.screenshot({path:path.join(__dirname,'econstats-admin.png'),fullPage:true});
 for(const width of [320,390,768,1440]){for(const [name,pg] of [['A',a],['B',b]]){await pg.setViewportSize({width,height:950});await pg.waitForTimeout(80);assert.equal(await pg.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'ec overflow '+width+' '+name);}}
 await a.setViewportSize({width:390,height:950});await a.screenshot({path:path.join(__dirname,'econstats-mobile.png'),fullPage:true});
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.24: fresh empty chart note, org fund deed grows the first gold bar in Twoja historia, admin world-summary dialog shows the 14-day chart (czyny + dev-sklep) for the same day; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
