const {chromium}=require('playwright');
const BASE=process.env.TEST_BASE_URL;
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 const page=await ctx.newPage();
 await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
 await page.fill('#auth-username','pe_'+Date.now().toString(36));await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');await page.click('[data-world="1"]');await page.fill('#character-nickname','Probe E');
 if(await page.locator('#test-consent').count())await page.check('#test-consent');
 await page.click('#character-form [type=submit]');await page.waitForFunction(()=>Network.world?.id===1);
 await page.click('[data-online=dismiss-tutorial]').catch(()=>{});await page.waitForFunction(()=>!Network.busy);
 console.log('state.energy:',await page.evaluate(()=>Network.packet?.state?.energy));
 await page.click('#nav-shop');await page.waitForFunction(()=>Network.panel==='shop'&&!Network.busy);
 const card=await page.locator('.shop-card',{hasText:'Energiapak'}).innerText();
 console.log('ENERGY CARD:',card.replace(/\n+/g,' | '));
 await browser.close();
})().catch(e=>{console.error('PROBE-FAIL',e);process.exit(1);});
