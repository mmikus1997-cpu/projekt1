/* 0.51.3 audit: zrzuty ranking/community/business/character/shop + overflow 1440/390. */
const {chromium}=require('playwright');
const fs=require('node:fs');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DIR=path.join(__dirname,'..','screens51');
fs.mkdirSync(DIR,{recursive:true});
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 if(process.env.TEST_STRIP_HEADERS==='1')await ctx.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 const page=await ctx.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.stack));
 const name='aud_'+Date.now().toString(36);
 await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
 await page.fill('#auth-username',name);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');
 await page.click('[data-world="2"]');await page.fill('#character-nickname','Audytor QA');
 if(await page.locator('#test-consent').count())await page.check('#test-consent');
 await page.click('#character-form [type=submit]');await page.waitForFunction(()=>Network.world?.id===2);
 await page.click('[data-online=dismiss-tutorial]');await page.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 const views=[['ranking','#nav-ranking','09-ranking','panel'],['community','#nav-community','10-community','panel'],['business','#nav-business','11-business','view'],['character','@character','12-character','view'],['shop','#nav-shop','13-shop','panel']];
 for(const[v,nav,file,mode]of views){
  if(nav==='@character')await page.evaluate(()=>GameApp.showView('character'));else await page.click(nav);
  if(mode==='panel')await page.waitForFunction(vv=>Network.panel===vv&&!Network.busy,v,{timeout:15000});
  else if(mode==='view')await page.waitForFunction(vv=>GameApp.view===vv,v,{timeout:15000});
  else await page.waitForSelector('.story-panel',{timeout:15000});
  await page.waitForTimeout(700);
  await page.screenshot({path:path.join(DIR,file+'-desktop.png'),fullPage:true});
 }
 await page.setViewportSize({width:390,height:844});await page.waitForTimeout(400);
 const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
 if(errors.length)throw new Error('JS: '+errors.join(' | ').slice(0,300));
 if(overflow)console.log('UWAGA: overflow 390px');
 await browser.close();
 console.log('AUDIT OK: 5 widoków, 0 błędów JS'+(overflow?', UWAGA overflow':''));
})().catch(e=>{console.error('FATAL:',e.message.slice(0,300));process.exit(1)});
