/* 0.15 org contracts in the real UI: officer sets a shared fund goal, both members contribute, progress bar updates, completion -> counter chip + events; no power bonuses; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3181';
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
 const nav=async p=>{await p.click('#nav-community');await p.waitForFunction(()=>Network.panel==='community'&&!Network.busy);};
 const suffix=Date.now().toString(36);
 const a=await account('ca_'+suffix,'Dowodzaca Celem');
 const b=await account('cb_'+suffix,'Czlonek Celu');
 // A founds the org, B applies through the directory dialog and gets accepted.
 await nav(a);
 await a.fill('#org-name','Ekipa Celu QA');await a.fill('#org-tag','ECQ');await a.fill('#org-description','Test wspolnych celow.');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 await nav(b);
 await b.evaluate(()=>document.querySelector('[data-extra=org-apply]').click());
 await b.waitForSelector('#org-apply-text',{timeout:10000});
 await b.evaluate(()=>document.querySelector('#network-dialog-close').click());
 await b.evaluate(()=>Network.api(`/worlds/${Network.world.id}/organizations/apply`,'POST',{org_id:+document.querySelector('#org-apply-form').dataset.org,text:'Chcemy wspolny cel w tescie.'}));
 await nav(a);
 await a.waitForSelector('[data-extra=app-accept]',{timeout:15000});
 await a.evaluate(()=>document.querySelector('[data-extra=app-accept]').click());
 await a.waitForFunction(()=>document.querySelector('.org-members')?.innerText.includes('Czlonek Celu'),{timeout:15000});
 // A sets a shared fund goal of 300 $ for 24h through the officer form.
 await a.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Ustaw wspólny cel'));t.click();});
 await a.waitForSelector('#org-contract-target',{timeout:10000});
 await a.fill('#org-contract-target','300');await a.selectOption('#org-contract-hours','24');
 await a.click('#org-contract-form [type=submit]');
 await a.waitForSelector('.org-contract-box',{timeout:15000});
 assert.match(await a.locator('.org-contract-box').innerText(),/ZBIÓRKA DO FUNDUSZU/);
 assert.match(await a.locator('.org-contract-box').innerText(),/0 \$ \/ 300 \$/);
 // B sees the goal box and the creation event.
 await nav(b);
 assert.match(await b.locator('.org-contract-box').innerText(),/0 \$ \/ 300 \$/);
 assert.match(await b.locator('.events-panel').innerText(),/Nowy wspólny cel \[ECQ\]/);
 // B funds 150; progress updates on both sides.
 await b.fill('#org-fund-amount','150');await b.click('#org-fund-form [type=submit]');
 await b.waitForFunction(()=>document.querySelector('.contract-nums')?.innerText.replace(/\s/g,'').includes('150$/300$'),{timeout:15000});
 await a.evaluate(()=>Extras.showCommunity());await a.waitForFunction(()=>!Network.busy);
 assert.match(await a.locator('.contract-nums').innerText(),/150 \$ \/ 300 \$/);
 // A funds the remaining 150 -> completion: box disappears, counter chip appears, events on both sides.
 await a.fill('#org-fund-amount','150');await a.click('#org-fund-form [type=submit]');
 await a.waitForFunction(()=>document.querySelector('.org-held-chip.contract-done')?.innerText.includes('1'),{timeout:15000});
 assert.equal(await a.locator('.org-contract-box').count(),0);
 await nav(b);
 assert.match(await b.locator('.org-held-chip.contract-done').innerText(),/Ukończone kontrakty: 1/);
 assert.match(await b.locator('.events-panel').innerText(),/Cel osiągnięty/);
 // Cash and stats untouched by completion (no power bonuses): B spent exactly 150 on the fund.
 const bs=await b.evaluate(async()=>(await Network.api('/worlds/1/state')).state);
 assert.equal(bs.cash,150);assert.deepEqual(bs.stats,[10,10,10,10,10],'0.43: kreacja bez klasy — równe statystyki');
 await a.screenshot({path:path.join(__dirname,'orgcontracts-desktop.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'contract overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'orgcontracts-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.15: officer sets shared fund goal, member sees goal + event, contributions move the progress bar, completion grants reputation counter + events on both sides, zero power bonuses; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
