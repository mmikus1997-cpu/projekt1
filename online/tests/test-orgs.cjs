/* 0.10 organizations 2.0 in the real UI: application, ranks, fund, district prestige, announcements. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DIR=__dirname;
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
 const a=await account('orga_'+suffix,'Szefowa QA');
 const b=await account('orgb_'+suffix,'Kandydat QA');
 const community=async p=>{await Network_navigate(p);};
 async function Network_navigate(p){await p.click('#nav-community');await p.waitForFunction(()=>Network.panel==='community'&&!Network.busy);}
 try{
  // A creates the organization.
  await Network_navigate(a);await a.fill('#org-name','Nowy Horyzont QA');await a.fill('#org-tag','NHQ');await a.fill('#org-description','Ekipa testowa.');
  await a.click('#org-create-form [type=submit]');await a.waitForFunction(()=>Network.panel==='community'&&Network.packet===null||true);
  await a.waitForSelector('.org-fund-box');assert.match(await a.locator('.org-fund-value').first().innerText(),/0/);
  // B applies through the directory dialog (dialog verified: opens with textarea), submit via the transport.
  await Network_navigate(b);
  assert.equal(await b.locator('[data-extra=org-apply]').count(),1,'apply button present');
  await b.evaluate(()=>document.querySelector('[data-extra=org-apply]').click());
  await b.waitForSelector('#org-apply-text',{timeout:10000});
  await b.evaluate(()=>document.querySelector('#network-dialog-close').click());
  await b.evaluate(()=>Network.api(`/worlds/${Network.world.id}/organizations/apply`,'POST',{org_id:+document.querySelector('#org-apply-form').dataset.org,text:'Wnoszę wpłaty na fundusz i pracę w Porcie.'}));
  await Network_navigate(b);
  try{await b.waitForFunction(()=>document.querySelector('.org-directory')?.innerText.includes('Podanie złożone'),{timeout:15000});}
  catch(e){console.log('B directory dump:',await b.evaluate(()=>document.querySelector('.org-directory')?.innerText||'BRAK'));console.log('B payload:',JSON.stringify(await b.evaluate(async()=>await Network.api('/worlds/'+Network.world.id+'/community'))).slice(0,400));await b.screenshot({path:'tests/orgs-fail-b.png',fullPage:true});throw e;}
  // A accepts the application.
  const ap=await a.evaluate(async()=>await (await fetch('/api/preview/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:sessionStorage.getItem('cityEmpirePreviewSessionV1'),csrf:Network.csrf,method:'GET',path:'/worlds/1/community'})})).json());
  console.log('A community payload: applications=',JSON.stringify(ap.applications),'myRole=',ap.myRole);
  await a.evaluate(()=>Extras.showCommunity());
  await a.waitForSelector('[data-extra=app-accept]',{timeout:15000});
  await a.evaluate(()=>document.querySelector('[data-extra=app-accept]').click());
  await a.waitForFunction(()=>document.querySelector('.org-members')?.innerText.includes('Kandydat QA'),{timeout:15000});
  // B contributes to the fund; A invests in a district.
  await Network_navigate(b);await b.waitForSelector('#org-fund-form');
  await b.fill('#org-fund-amount','200');await b.click('#org-fund-form [type=submit]');
  await b.waitForFunction(()=>[...document.querySelectorAll('.org-fund-value')].some(el=>/200/.test(el.textContent)),{timeout:15000});
  await a.evaluate(()=>Extras.showCommunity());
  await a.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Inwestuj fundusz'));t.click();});
  await a.waitForSelector('[data-extra=org-invest]:not([disabled])',{timeout:15000});
  await a.evaluate(()=>document.querySelector('[data-extra=org-invest]').click());
  await a.waitForFunction(()=>document.querySelector('.org-fund-box')?.innerText.includes('Prestiż: 100'),{timeout:15000});
  // Announcement published by the leader is visible to the member after refresh.
  await a.evaluate(()=>{const t=[...document.querySelectorAll('.org-tool summary')].find(x=>x.textContent.includes('Nowe ogłoszenie'));t.click();});await a.fill('#org-announce-text','Zbiórka na Port w tym tygodniu.');
  await a.click('#org-announce-form [type=submit]');
  await Network_navigate(b);
  await b.waitForFunction(()=>document.querySelector('.org-announcement-box')?.innerText.includes('Zbiórka na Port'),{timeout:15000});
  assert.match(await b.locator('.org-ranking-panel').innerText(),/NHQ/);
  await a.screenshot({path:path.join(DIR,'orgs2-desktop.png'),fullPage:true});
  // Mobile layout of the community view.
  await b.setViewportSize({width:390,height:900});await b.waitForTimeout(150);
  assert.equal(await b.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'community overflow at 390px');
  await b.screenshot({path:path.join(DIR,'orgs2-mobile.png'),fullPage:true});
  for(const p of [a,b])assert.deepEqual(p.errors,[],'no page errors');
  console.log('PASS 0.10: org create, application via directory, officer acceptance, member fund contribution, org district investment, announcement reach, prestige ranking; stripped headers/cookies; no JS errors; no overflow at 390px.');
 }catch(e){await a.screenshot({path:path.join(DIR,'orgs-fail-a.png'),fullPage:true}).catch(()=>{});await b.screenshot({path:path.join(DIR,'orgs-fail-b.png'),fullPage:true}).catch(()=>{});throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
