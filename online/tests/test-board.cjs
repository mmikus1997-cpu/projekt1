/* 0.18 notice board in the real UI: admin posts world-scoped and global notices from the panel, player board shows scoped entries with chips, banner shows the latest and dismisses, admin deletes an entry and the board updates; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3203';
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
 const a=await account('ba_'+suffix,'Mieszkaniec Miasta');
 const b=await account('bb_'+suffix,'Admin Miasta');
 // B becomes admin via the disposable QA fixture, then full re-login refreshes the session role.
 execFileSync('python',['manage.py','--db',DB,'grant-admin','bb_'+suffix]);
 await b.goto(BASE);await b.waitForSelector('#auth-form');
 await b.fill('#auth-username','bb_'+suffix);await b.fill('#auth-password',PASSWORD);await b.click('#auth-form [type=submit]');
 await b.waitForSelector('.world-grid');await b.click('[data-world="1"]');
 await b.waitForFunction(()=>Network.world?.id===1,{timeout:20000});
await b.waitForSelector('[data-online=brief-close]',{timeout:2500}).then(()=>b.click('[data-online=brief-close]')).catch(()=>{});
 await b.click('[data-online=dismiss-tutorial]').catch(()=>{});
 await b.waitForFunction(()=>!Network.busy,{timeout:20000});
 // B posts a world-scoped notice, then a global one.
 await b.click('#nav-admin');await b.waitForFunction(()=>Network.panel==='admin'&&!Network.busy,{timeout:15000});
 await b.click('[data-online=post-notice]');
 await b.waitForSelector('#notice-form',{timeout:10000});
 await b.selectOption('#notice-world','1');
 await b.fill('#notice-text','Przerwa techniczna w sobotę rano.');
 await b.click('#notice-form [type=submit]');
 await b.waitForFunction(()=>document.querySelector('.admin-notices-panel')?.innerText.includes('Przerwa techniczna w sobotę rano.'),{timeout:15000});
 await b.click('[data-online=post-notice]');
 await b.waitForSelector('#notice-form',{timeout:10000});
 await b.selectOption('#notice-world','all');
 await b.fill('#notice-text','Witajcie w nowym tygodniu.');
 await b.click('#notice-form [type=submit]');
 await b.waitForFunction(()=>document.querySelector('.admin-notices-panel')?.innerText.includes('Witajcie w nowym tygodniu.'),{timeout:15000});
 await b.screenshot({path:path.join(__dirname,'board-admin.png'),fullPage:true});
 // A: banner picks the latest notice; dismiss hides it.
 await a.evaluate(()=>Network.refresh().catch(()=>{}));
 await a.waitForFunction(()=>!document.querySelector('#world-news')?.hidden,{timeout:15000});
 assert.match(await a.locator('#world-news').innerText(),/Witajcie w nowym tygodniu\./);
 await a.click('[data-online=notice-dismiss]');
 await a.waitForFunction(()=>document.querySelector('#world-news')?.hidden,{timeout:10000});
 // A: the community board lists both with scope chips.
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await a.waitForSelector('.notice-board-panel',{timeout:15000});
 const boardText=await a.locator('.notice-board-panel').innerText();
 assert.match(boardText,/Przerwa techniczna w sobotę rano\./);assert.match(boardText,/Witajcie w nowym tygodniu\./);
 assert.match(boardText,/TEN ŚWIAT/);assert.match(boardText,/GLOBALNE/);
 await a.screenshot({path:path.join(__dirname,'board-desktop.png'),fullPage:true});
 // B deletes the world-scoped entry; the admin list updates.
 await b.evaluate(()=>{const row=[...document.querySelectorAll('.admin-notices-panel .session-row')].find(x=>x.textContent.includes('Przerwa techniczna'));row.querySelector('[data-notice-del]').click();});
 await b.waitForFunction(()=>!Network.busy,{timeout:15000});
 await b.waitForFunction(()=>{const p=document.querySelector('.admin-notices-panel');return p&&!p.innerText.includes('Przerwa techniczna')&&p.innerText.includes('Witajcie w nowym tygodniu.');},{timeout:15000});
 // A: the board refresh button re-fetches the community payload; the deleted entry disappears.
 await a.click('[data-extra=community]');
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 await a.waitForFunction(()=>![...document.querySelectorAll('.notice-board-panel .notice-row p')].some(p=>p.textContent.includes('Przerwa techniczna')),{timeout:15000});
 const boardText2=await a.locator('.notice-board-panel').innerText();
 assert.doesNotMatch(boardText2,/Przerwa techniczna/);assert.match(boardText2,/Witajcie w nowym tygodniu\./);
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'notice board overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'board-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.18: admin posts world-scoped and global notices from the panel, player board shows scoped entries with chips, banner shows latest and dismisses, admin deletes an entry and the board updates; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
