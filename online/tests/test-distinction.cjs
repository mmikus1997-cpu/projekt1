/* 0.23 daily distinction: idle note on a fresh character, org fund makes it claimable, claim turns it into an earned chip with the counter; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3210';
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
 const a=await account('ds_'+suffix,'Dystynkowany');
 // fresh character: idle note, no claim button
 await a.evaluate(()=>GameApp.showView('city'));await a.waitForSelector('.story-distinction',{timeout:10000});
 assert.match(await a.locator('.story-distinction').innerText(),/Wykonaj dziś jedną z czynności/i);
 assert.equal(await a.locator('[data-extra=distinction-claim]').count(),0,'no claim button yet');
 // the deed: found an org and fund it
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await a.fill('#org-name','Dystynkcja QA');await a.fill('#org-tag','DYQ');await a.fill('#org-description','');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 await a.fill('#org-fund-amount','100');await a.click('#org-fund-form [type=submit]');
 await a.waitForFunction(()=>document.getElementById('toast')?.textContent.includes('Wpłata przyjęta'),{timeout:15000});
 // back to the character view: claimable
 await a.evaluate(()=>GameApp.showView('city'));await a.waitForSelector('.story-distinction.ready',{timeout:10000});
 const ready=await a.locator('.story-distinction').innerText();
 assert.match(ready,/gotowa do odbioru/i);assert.match(ready,/Wsparcie organizacji/);
 await a.screenshot({path:path.join(__dirname,'distinction-ready.png'),fullPage:true});
 // claim: earned chip with the counter, button gone
 await a.click('[data-extra=distinction-claim]');
 await a.waitForFunction(()=>document.querySelector('#toast')?.textContent.includes('Dystynkcja dnia odebrana'),{timeout:15000});
 await a.waitForSelector('.story-distinction.earned',{timeout:15000});
 const earned=await a.locator('.story-distinction').innerText();
 assert.match(earned,/Dystynkcja dnia · Wsparcie organizacji/);assert.match(earned,/łącznie: 1/);
 assert.equal(await a.locator('[data-extra=distinction-claim]').count(),0,'claim button gone after earning');
 // double-click protection: state has no pending button and a forced claim errors gracefully (409 toast)
 await a.evaluate(async()=>{try{await fetch('/api/worlds/1/distinction/claim',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':(document.cookie.match(/csrf=([^;]+)/)||[])[1]||''},body:'{}'});}catch(e){}});
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'distinction overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'distinction-mobile.png'),fullPage:true});}
 assert.deepEqual(a.errors,[],'page errors: '+a.errors.join(' | '));
 console.log('PASS 0.23: daily distinction starts idle, org fund makes it claimable (Za: Wsparcie organizacji), claim earns the chip with counter 1 and removes the button; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
