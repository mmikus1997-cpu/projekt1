/* 0.11 territory influence in the real UI: invest, claim, kronika, takeover by rival org, chips; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3111';
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
 const Network_navigate=async p=>{await p.click('#nav-community');await p.waitForFunction(()=>Network.panel==='community'&&!Network.busy);};
 const ownFund=async(p,v)=>{await p.waitForFunction(v=>{const el=document.querySelector('.org-fund-box .org-fund-value');return el&&parseInt(el.textContent.replace(/[^\d]/g,''),10)===v;},v,{timeout:15000});};
 const openInvest=async p=>{await p.waitForFunction(()=>!Network.busy);await p.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Inwestuj fundusz'));t.click();});await p.waitForFunction(()=>[...document.querySelectorAll('details.org-tool')].some(t=>t.open&&t.querySelector('[data-extra=org-invest]')),{timeout:10000});};
 const investPort=async p=>{await p.evaluate(()=>document.querySelector('[data-extra=org-invest][data-district=Portowe]:not([disabled])').click());};
 const suffix=Date.now().toString(36);
 const a=await account('ta_'+suffix,'Szefowa Terytoriów');
 const b=await account('tb_'+suffix,'Rywal Terytoriów');
 // A founds the first org and claims Port with 100 $ of prestige.
 await Network_navigate(a);
 await a.fill('#org-name','Straż Portowa QA');await a.fill('#org-tag','TGA');await a.fill('#org-description','Trzymamy Port.');
 await a.click('#org-create-form [type=submit]');await a.waitForSelector('#org-fund-form');
 await a.fill('#org-fund-amount','100');await a.click('#org-fund-form [type=submit]');
 await ownFund(a,100);
 await openInvest(a);await investPort(a);
 await a.waitForFunction(()=>{const el=document.querySelector('.org-influence-panel');return el&&el.innerText.includes('Straż Portowa QA')&&el.innerText.includes('1. miejsce');},{timeout:15000});
 assert.match(await a.locator('.org-held-chips').first().innerText(),/Port/);
 // B founds a rival org, funds it with all starting cash and overtakes Port by repeated 100 $ investments.
 await Network_navigate(b);
 await b.fill('#org-name','Konsorcjum QA');await b.fill('#org-tag','TGB');await b.fill('#org-description','Port zmienia właściciela.');
 await b.click('#org-create-form [type=submit]');await b.waitForSelector('#org-fund-form');
 await b.fill('#org-fund-amount','300');await b.click('#org-fund-form [type=submit]');
 await ownFund(b,300);
 for(let i=3;i>0;i--){await openInvest(b);await investPort(b);await ownFund(b,(i-1)*100);}
 await b.waitForFunction(()=>document.querySelector('.org-influence-panel')?.innerText.includes('odjęte TGA'),{timeout:15000});
 assert.match(await b.locator('.org-influence-panel').innerText(),/1\. miejsce/);
 // A sees the loss after refresh (nav re-click does not refetch — render explicitly): no chip, rival leads Port, kronika records the takeover.
 await a.evaluate(()=>Extras.showCommunity());await a.waitForFunction(()=>!Network.busy);
 const panelA=await a.locator('.org-influence-panel').innerText();
 assert.match(panelA,/TGB/);assert.match(panelA,/Konsorcjum QA/);assert.match(panelA,/odjęte TGA/);assert.match(panelA,/2\. miejsce · 100/);
 assert.equal(await a.locator('.org-held-chips').count(),0,'lost chip removed');
 await a.screenshot({path:path.join(__dirname,'territory-desktop.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await a.setViewportSize({width,height:950});await a.waitForTimeout(100);assert.equal(await a.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'influence overflow '+width);if(width===390)await a.screenshot({path:path.join(__dirname,'territory-mobile.png'),fullPage:true});}
 for(const [name,pg] of [['A',a],['B',b]])assert.deepEqual(pg.errors,[],name+' page errors: '+pg.errors.join(' | '));
 console.log('PASS 0.11: org invest claims Port with prestige, influence panel + kronika, rival takeover recorded, chips update on both sides; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
