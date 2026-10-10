/* 0.21 org showcase: another player opens the public org profile from the directory — basics, members, prestige, held districts and the chronicle history dialog; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3208';
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
 // A builds the org story: founding + fund + investment into Port
 const a=await account('oa_'+suffix,'Lider Wizytówki');
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 await a.fill('#org-name','Wizytowa QA');await a.fill('#org-tag','WQA');await a.fill('#org-description','Ekipa z historią do pokazania.');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 await a.fill('#org-fund-amount','100');await a.click('#org-fund-form [type=submit]');
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 await a.click('#nav-city');await a.waitForFunction(()=>!Network.busy);
 await a.click('#nav-community');await a.waitForFunction(()=>Network.panel==='community'&&!Network.busy,{timeout:15000});
 await a.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Inwestuj fundusz'));t.click();});
 await a.waitForSelector('[data-extra=org-invest]:not([disabled])',{timeout:15000});
 await a.evaluate(()=>document.querySelector('[data-extra=org-invest][data-district=Portowe]').click());
 await a.waitForFunction(()=>!Network.busy,{timeout:15000});
 // B, a resident without an org, opens the public profile from the directory
 const b=await account('ob_'+suffix,'Ciekawski Sąsiad');
 await b.click('#nav-community');await b.waitForFunction(()=>Network.panel==='community'&&!Network.busy);
 const card=b.locator('.org-directory article',{hasText:'Wizytowa QA'});
 await card.locator('[data-extra=org-profile]').click();
 await b.waitForSelector('#network-dialog[open]',{timeout:15000});
 const dlg=await b.locator('#network-dialog-body').innerText();
 assert.match(dlg,/Wizytowa QA \[WQA\]/);
 assert.match(dlg,/Lider: Lider Wizytówki/);
 assert.match(dlg,/Członkowie: 1 \/ 20/);
 assert.match(dlg,/prestiż: 100/);
 assert.match(dlg,/wpływy: Port/);
 assert.match(dlg,/Historia z kroniki/i);
 assert.match(dlg,/Powstaje organizacja Wizytowa QA \[WQA\]/);
 assert.match(dlg,/publiczna dla mieszkańców świata/);
 await b.screenshot({path:path.join(__dirname,'orgprofile-desktop.png'),fullPage:true});
 await b.click('#network-dialog [data-close], #network-dialog .dialog-close, #network-dialog button:has-text("Zamknij")').catch(async()=>{await b.evaluate(()=>document.getElementById('network-dialog').close());});
 for(const width of [320,390,768,1440]){await b.setViewportSize({width,height:950});await b.waitForTimeout(100);assert.equal(await b.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'org profile overflow '+width);if(width===390)await b.screenshot({path:path.join(__dirname,'orgprofile-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.21: another resident opens the org showcase from the directory — basics, leader, members, prestige, held districts and chronicle history in a dialog; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
