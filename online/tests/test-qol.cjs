/* 0.20 QoL: clean console during registration (valid pattern attr), password visibility toggle, Energiapak guarded at full energy, "Twoja historia" panel with badge chips; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3206';
const DB=process.env.TEST_DB;
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 if(process.env.TEST_STRIP_HEADERS==='1')await ctx.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 const page=await ctx.newPage();page.errors=[];page.consoleErrors=[];
 page.on('pageerror',e=>page.errors.push(e.stack));
 page.on('console',m=>{if(m.type()==='error')page.consoleErrors.push(m.text());});
 await page.goto(BASE);await page.waitForSelector('#auth-form');
 // login tab: the eye toggle flips the password input type both ways
 await page.click('[data-auth-mode=login]');
 await page.click('[data-pw-show="#auth-password"]');
 assert.equal(await page.evaluate(()=>document.querySelector('#auth-password').type),'text','password revealed');
 assert.equal(await page.evaluate(()=>document.querySelector('[data-pw-show="#auth-password"]').textContent),'Ukryj');
 await page.click('[data-pw-show="#auth-password"]');
 assert.equal(await page.evaluate(()=>document.querySelector('#auth-password').type),'password','password hidden again');
 // register: with the fixed pattern attr, Chrome must not log an invalid-regex console error
 await page.click('[data-auth-mode=register]');
 const suffix=Date.now().toString(36);
 await page.fill('#auth-username','qo_'+suffix);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');await page.click('[data-world="1"]');await page.fill('#character-nickname','Odznaka QA');
 if(await page.locator('#test-consent').count())await page.check('#test-consent');
 await page.click('#character-form [type=submit]');await page.waitForFunction(()=>Network.world?.id===1);
 await page.click('[data-online=dismiss-tutorial]');await page.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 assert.ok(!page.consoleErrors.some(t=>t.includes('Invalid regular expression')),'pattern attr console error: '+page.consoleErrors.join(' | '));
 // shop: Energiapak card on a fresh character (120/240) — no warning, buy enabled
 await page.click('#nav-shop');await page.waitForFunction(()=>Network.panel==='shop'&&!Network.busy,{timeout:15000});
 let energyCard=await page.locator('.shop-card',{hasText:'Energiapak'}).innerText();
 assert.doesNotMatch(energyCard,/przepadnie|przepadłby/);
 assert.equal(await page.locator('.shop-card',{hasText:'Energiapak'}).locator('button').isDisabled(),false,'fresh buy enabled');
 const setEnergy=v=>execFileSync('python',['-c',"import sqlite3,os,sys,json;db=sqlite3.connect(os.environ['TEST_DB']);cid=db.execute(\"SELECT id,state_json FROM characters WHERE nickname='Odznaka QA'\").fetchone();st=json.loads(cid[1]);st['energy']=float(sys.argv[1]);db.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(st,separators=(',',':')),cid[0]));db.commit();db.close();",String(v)],{env:{...process.env,TEST_DB:DB}});
 const reopenShop=async()=>{await page.evaluate(()=>Network.refresh().catch(()=>{}));await page.waitForFunction(()=>!Network.busy,{timeout:15000});await page.click('#nav-city');await page.waitForFunction(()=>!Network.busy);await page.click('#nav-shop');await page.waitForFunction(()=>Network.panel==='shop'&&!Network.busy,{timeout:15000});};
 // 150/240: partial waste → visible warning, purchase still possible (honest choice)
 setEnergy(150);await reopenShop();
 energyCard=await page.locator('.shop-card',{hasText:'Energiapak'}).innerText();
 assert.match(energyCard,/Masz 150 \/ 240 energii — część zakupu przepadnie\./);
 assert.equal(await page.locator('.shop-card',{hasText:'Energiapak'}).locator('button').isDisabled(),false,'partial still enabled');
 // 240/240: full → disabled with the hard warning
 setEnergy(240);await reopenShop();
 energyCard=await page.locator('.shop-card',{hasText:'Energiapak'}).innerText();
 assert.match(energyCard,/Pełna energia \(240\/240\) — zakup teraz przepadłby\./);
 assert.equal(await page.locator('.shop-card',{hasText:'Energiapak'}).locator('button').isDisabled(),true,'energy buy disabled at full energy');
 // character view: the story panel with counters and the empty-badges note
 await page.evaluate(()=>GameApp.showView('hall'));await page.waitForSelector('.story-panel',{timeout:10000});
 const storyText=await page.locator('.story-panel').innerText();
 assert.match(storyText,/Twoja historia/);assert.match(storyText,/kontrakty ukończone/i);assert.match(storyText,/Jeszcze bez odznak/);
 // seed a badge straight into the QA db; the profile picks it up after a refresh
 execFileSync('python',[path.join(__dirname,'seed_qol.py'),'Odznaka QA','Odznaka QA · test'],{env:{...process.env,TEST_DB:DB}});
 await page.evaluate(()=>Network.refresh().catch(()=>{}));
 await page.waitForFunction(()=>!Network.busy,{timeout:15000});
 await page.click('#nav-city');await page.waitForFunction(()=>!Network.busy);
 await page.evaluate(()=>GameApp.showView('hall'));await page.waitForSelector('.story-panel',{timeout:10000});
 assert.match(await page.locator('.story-panel').innerText(),/Odznaka QA · test/);
 await page.screenshot({path:path.join(__dirname,'qol-character.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await page.setViewportSize({width,height:950});await page.waitForTimeout(100);assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'qol overflow '+width);if(width===390)await page.screenshot({path:path.join(__dirname,'qol-mobile.png'),fullPage:true});}
 assert.deepEqual(page.errors,[],'page errors: '+page.errors.join(' | '));
 assert.ok(!page.consoleErrors.some(t=>t.includes('Invalid regular expression')),'pattern attr console error: '+page.consoleErrors.join(' | '));
 console.log('PASS 0.20: registration console-clean (valid pattern attr), password eye toggle both ways, Energiapak disabled with a warning at full energy, Twoja historia panel shows counters and badge chips; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
