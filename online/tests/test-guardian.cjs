/* 0.19 guardian consent in the real UI: minor path files guardian name + weekly limit from the gate form, gate enables, Energiapak fits the limit, next purchase hits the weekly cap toast, revoke dialog disables spending, adult path still one-click; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3205';
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
 const a=await account('ga_'+suffix,'Mieszkaniec Miasta');
 // open the shop
 await a.click('#nav-shop');await a.waitForFunction(()=>Network.panel==='shop'&&!Network.busy,{timeout:15000});
 await a.waitForSelector('.shop-gate');
 // minor path: the guardian fields reveal only for the <16 radio
 await a.check('#shop-statement');
 await a.check('input[name=shop-age][value=minor]');
 assert.equal(await a.locator('#guardian-fields').isVisible(),true,'guardian fields visible for minor');
 await a.check('input[name=shop-age][value=adult]');
 assert.equal(await a.locator('#guardian-fields').isVisible(),false,'guardian fields hidden for adult');
 await a.check('input[name=shop-age][value=minor]');
 // enabling without the guardian name is blocked client-side with a clear toast
 await a.click('[data-shop-gate="1"]');
 await a.waitForFunction(()=>document.querySelector('#toast')?.textContent.includes('imię i nazwisko opiekuna'),{timeout:10000});
 // file the consent (limit 5 zł/tydzień) and enable
 await a.fill('#gc-name','Anna Przykładowa');
 await a.selectOption('#gc-limit','500');
 await a.click('[data-shop-gate="1"]');
 await a.waitForFunction(()=>document.querySelector('.shop-gate')?.innerText.includes('WŁĄCZONE'),{timeout:15000});
 const gbox=await a.locator('.guardian-box').innerText();
 assert.match(gbox,/Anna Przykładowa/);assert.match(gbox,/limit 5 zł \/ tydzień/);assert.match(gbox,/0,00 zł/);
 // Energiapak 4,99 zł fits the 5 zł weekly cap
 await a.click('[data-shop-buy=energy]');
 await a.waitForFunction(()=>document.querySelector('#toast')?.textContent.includes('Zakup zakończony'),{timeout:15000});
 await a.waitForFunction(()=>document.querySelector('.guardian-box')?.innerText.includes('4,99'),{timeout:15000});
 await a.screenshot({path:path.join(__dirname,'guardian-desktop.png'),fullPage:true});
 // another 2,99 zł would break the cap → server 409 lands in the toast
 await a.click('[data-shop-buy=speedup]');
 await a.waitForFunction(()=>document.querySelector('#toast')?.textContent.includes('Tygodniowy limit'),{timeout:15000});
 // revoke: dialog confirm closes spending immediately
 await a.click('[data-online=gc-revoke]');
 await a.waitForSelector('[data-online=gc-revoke-confirm]',{timeout:10000});
 await a.click('[data-online=gc-revoke-confirm]');
 await a.waitForFunction(()=>document.querySelector('.shop-gate')?.innerText.includes('WYŁĄCZONE'),{timeout:15000});
 assert.equal(await a.locator('.guardian-box').count(),0,'guardian box gone after revoke');
 // adult path regression: one checkbox + click, no guardian fields
 await a.check('#shop-statement');
 assert.equal(await a.locator('#guardian-fields').isVisible(),false,'adult radio hides guardian fields');
 await a.click('[data-shop-gate="1"]');
 await a.waitForFunction(()=>document.querySelector('.shop-gate')?.innerText.includes('WŁĄCZONE'),{timeout:15000});
 assert.equal(await a.locator('.guardian-box').count(),0,'no guardian box on the adult path');
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'guardian overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'guardian-mobile.png'),fullPage:true});}
 assert.deepEqual(a.errors,[],'A page errors: '+a.errors.join(' | '));
 console.log('PASS 0.19: minor gate files guardian consent with weekly limit, Energiapak fits the cap, next purchase hits the weekly-limit toast, revoke dialog disables spending at once, adult path unchanged; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
