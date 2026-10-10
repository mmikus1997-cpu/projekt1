/* 0.51.2: hover na karcie świata NIE przemieszcza przycisku i NIE rozciąga sąsiada; szczegóły w popoverze. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
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
 const name='wshot_'+Date.now().toString(36);
 await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
 await page.fill('#auth-username',name);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');await page.waitForTimeout(400);
 const btn=page.locator('.test-world [data-world="2"]');
 const sib=page.locator('.world-card:not(.test-world)').first();
 const y1=(await btn.boundingBox()).y, h1=(await sib.boundingBox()).height;
 await page.screenshot({path:path.join(DIR,'06-worlds-idle.png'),fullPage:true});
 await page.hover('.test-world');await page.waitForTimeout(450);
 const y2=(await btn.boundingBox()).y, h2=(await sib.boundingBox()).height;
 const popVisible=await page.evaluate(()=>{const m=document.querySelector('.test-world .world-more');const cs=getComputedStyle(m);return cs.position==='absolute'&&parseFloat(cs.opacity)>0.9&&m.getBoundingClientRect().height>60;});
 await page.screenshot({path:path.join(DIR,'07-worlds-hover.png'),fullPage:true});
 assert.ok(Math.abs(y1-y2)<2,'przycisk przesunął się o '+Math.abs(y1-y2).toFixed(1)+'px');
 assert.ok(Math.abs(h1-h2)<2,'sąsiednia karta rozciągnęła się o '+Math.abs(h1-h2).toFixed(1)+'px');
 assert.ok(popVisible,'popover szczegółów nie jest widoczny/absolutny');
 // mobile: szczegóły nadal inline (zawsze widoczne)
 await page.setViewportSize({width:390,height:844});await page.mouse.move(5,5);await page.waitForTimeout(300);
 const mobInline=await page.evaluate(()=>{const m=document.querySelector('.test-world .world-more');const cs=getComputedStyle(m);return cs.position==='static'&&cs.maxHeight==='none'&&cs.opacity==='1';});
 assert.ok(mobInline,'mobile: szczegóły przestały być inline');
 await page.screenshot({path:path.join(DIR,'08-worlds-mobile.png'),fullPage:true});
 if(errors.length)throw new Error(errors.join('\n'));
 await browser.close();
 console.log('PASS 0.51.2 worlds: przycisk w miejscu (Δ'+Math.abs(y1-y2).toFixed(1)+'px), sąsiad bez zmian (Δ'+Math.abs(h1-h2).toFixed(1)+'px), popover działa, mobile inline OK');
})().catch(e=>{console.error('FATAL:',e.message.slice(0,300));process.exit(1)});
