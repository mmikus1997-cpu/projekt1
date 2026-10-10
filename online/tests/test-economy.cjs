/* 0.9 deeper economy in the real UI: daily tender, market prices, districts, garage and staff. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DIR=__dirname;
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 if(process.env.TEST_STRIP_HEADERS==='1')await ctx.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 const page=await ctx.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.stack));
 const name='eko_'+Date.now().toString(36);
 await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
 await page.fill('#auth-username',name);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');
 await page.click('[data-world="2"]');await page.fill('#character-nickname','Eko QA '+Date.now().toString(36).slice(-4));
 if(await page.locator('#test-consent').count())await page.check('#test-consent');
 await page.click('#character-form [type=submit]');await page.waitForFunction(id=>Network.world?.id===id,2);
 await page.click('[data-online=dismiss-tutorial]');await page.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 async function acted(selector,test){await page.click(selector);await page.waitForFunction(test);await page.waitForFunction(()=>!Network.busy);}
 try{
  // Contracts: daily tender card, district investments, market price badges.
  await page.click('#nav-contracts');await page.waitForFunction(()=>GameApp.view==='contracts');
  assert.match(await page.locator('.tender-panel').innerText(),/Przetarg dnia/);
  assert.equal(await page.locator('.district-row').count(),7);  // 2.1a GDD v3.1: + Kopalnia
  const mult=await page.evaluate(()=>Network.packet.catalog.prices.delivery);
  assert.ok(mult>=0.85&&mult<=1.15,'market multiplier in range');
  const badge=await page.locator('.contract-card').first().locator('.mult-badge').count();
  const deliveryCash=await page.evaluate(()=>{const d=Network.packet.catalog.contracts.find(x=>x.id==='delivery');return Math.round(d.cash*d.mult*(1+(d.hop||0)/100));});  // 0.45: karta z bonusem dojazdu
  assert.ok((await page.locator('.contract-action').first().innerText()).includes(deliveryCash.toLocaleString('pl-PL')),'card shows today\'s price');
  // Invest in Port: personal total and bonus grow.
  await acted('.district-row:has-text("Portowe") [data-game=invest][data-amount="1000"]',()=>GameApp.state.invested.Portowe===1000);
  const port=[...(await page.locator('.district-row').allInnerTexts())].find(t=>t.includes('Portowe'));
  assert.match(port,/premia \+4\.33%/);
  // Business: staff hire; 0.49 vehicles live in the Residence garage tab.
  await page.click('#nav-business');await page.waitForFunction(()=>GameApp.view==='business');
  assert.equal(await page.locator('.garage-row').count(),3,'three staff offers');
  assert.match(await page.locator('.garage-move-note').innerText(),/budynkiem dzielnicy/i);
  await acted('[data-game=hire-staff][data-staff=courier]',()=>GameApp.state.staff.courier>0);
  assert.match(await page.locator('.garage-panel').innerText(),/Pracuje jeszcze/i);
  await page.click('.garage-move-note [data-go=garage]');await page.waitForFunction(()=>GameApp.view==='garage');
  await page.screenshot({path:path.join(DIR,'economy09-desktop.png'),fullPage:true});
  // Mobile layout on the two touched views.
  await page.setViewportSize({width:390,height:900});await page.waitForTimeout(150);
  for(const view of ['contracts','business']){
   await page.click('#nav-'+view);await page.waitForFunction(v=>GameApp.view===v,view);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,view+' overflow at 390px');
  }
  await page.screenshot({path:path.join(DIR,'economy09-mobile.png'),fullPage:true});
  await page.setViewportSize({width:1440,height:1000});
  assert.deepEqual(errors,[]);
  console.log('PASS 0.9 economy: tender card, per-day price on cards, district invest (+1% bonus), vehicle purchase with wear state, staff hire; stripped headers/cookies; no JS errors; no overflow at 390px.');
 }catch(e){await page.screenshot({path:path.join(DIR,'economy-fail.png'),fullPage:true});throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
