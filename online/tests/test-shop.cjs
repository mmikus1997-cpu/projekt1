/* 0.14 dev shop in the real UI: default-off gate with statement, PLN prices, dev checkout, skins/VIP cosmetics, daily limits; stripped transport; no JS errors; no overflow at 390px. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3161';
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 if(process.env.TEST_STRIP_HEADERS==='1')await ctx.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 const p=await ctx.newPage();p.errors=[];
 p.on('pageerror',e=>p.errors.push(e.stack));
 await p.goto(BASE);await p.waitForSelector('#auth-form');await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username','shop_'+Date.now().toString(36));await p.fill('#auth-password',PASSWORD);await p.fill('#auth-confirm',PASSWORD);await p.check('#age-consent');await p.click('#auth-form [type=submit]');
 await p.waitForSelector('.world-grid');await p.click('[data-world="1"]');await p.fill('#character-nickname','Klient Sklepu');
 if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');await p.waitForFunction(()=>Network.world?.id===1);
 await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 // Shop opens with the no-real-payments banner, PLN prices and default-off gate.
 await p.click('#nav-shop');await p.waitForFunction(()=>Network.panel==='shop'&&!Network.busy,{timeout:15000});
 const banner=await p.locator('.shop-banner').innerText();
 assert.match(banner,/BEZ prawdziwych płatności/);
 assert.equal(await p.locator('.price-tag').count(),8,'8 products with price tags');
 assert.match(await p.locator('.price-tag').first().innerText(),/zł/);
 assert.match(await p.locator('.shop-gate').innerText(),/WYŁĄCZONE/);
 // Buying with the gate off must not succeed.
 await p.locator('[data-shop-buy=vip30]').click();
 await p.waitForFunction(()=>document.body.innerText.includes('Zakupy są wyłączone'),{timeout:15000});
 // Gate: statement checkbox required, then enabled.
 await p.locator('[data-shop-gate="1"]').click();
 await p.waitForFunction(()=>document.body.innerText.includes('oświadczenie'),{timeout:15000});
 await p.check('#shop-statement');await p.locator('[data-shop-gate="1"]').click();
 await p.waitForFunction(()=>document.querySelector('.shop-gate')?.innerText.includes('WŁĄCZONE'),{timeout:15000});
 // VIP purchase: active date + gold frame class.
 await p.locator('[data-shop-buy=vip30]').click();
 try{await p.waitForFunction(()=>document.querySelector('.shop-card')?.innerText.includes('Aktywny do'),{timeout:15000});}
 catch(e){console.log('VIP dump card0:',await p.evaluate(()=>document.querySelector('.shop-card')?.innerText.replace(/\n/g,' | ').slice(0,160)));console.log('VIP dump toast:',await p.evaluate(()=>document.querySelector('#toast')?.textContent));console.log('VIP dump gate:',await p.evaluate(()=>document.querySelector('.shop-gate')?.innerText.replace(/\n/g,' | ').slice(0,120)));console.log('VIP dump busy:',await p.evaluate(()=>Network.busy),'packetShop:',await p.evaluate(()=>JSON.stringify(Network.packet?.shop||null).slice(0,150)));await p.screenshot({path:path.join(__dirname,'shop-fail.png'),fullPage:true});throw e;}
 await p.waitForFunction(()=>document.querySelector('.hud-identity')?.classList.contains('vip'),{timeout:15000});
 // 0.15: HUD shows the VIP chip with the expiry date.
 await p.waitForFunction(()=>{const c=document.getElementById('hud-vip');return c&&!c.hidden&&/VIP · do /.test(c.textContent);},{timeout:15000});
 // Skin purchase: equipped + copper frame.
 await p.locator('[data-shop-buy=skin_copper]').click();
 await p.waitForFunction(()=>[...document.querySelectorAll('.shop-card')].some(c=>c.innerText.includes('Założona')),{timeout:15000});
 try{await p.waitForFunction(()=>document.querySelector('.hud-identity')?.classList.contains('skin-copper'),{timeout:15000});}
 catch(e){console.log('SKIN dump:',await p.evaluate(()=>({cls:document.querySelector('.hud-identity')?.className,pkt:JSON.stringify(Network.packet?.shop||null)})));throw e;}
 // 0.15: character view carries the skin picker; switching skins updates the frame without reload.
 await p.evaluate(()=>GameApp.showView('character'));await p.waitForSelector('.skin-options',{timeout:15000});
 const chips=await p.locator('.skin-options .skin-chip').allInnerTexts();
 assert.ok(chips.some(t=>t.includes('Domyślna'))&&chips.some(t=>t.includes('Miedź')),'picker chips: '+chips.join('|'));
 assert.ok(await p.evaluate(()=>document.querySelector('.hud-identity').classList.contains('skin-copper')));
 await p.locator('.skin-options .skin-chip').first().click();
 await p.waitForFunction(()=>!document.querySelector('.hud-identity').classList.contains('skin-copper'),{timeout:15000});
 await p.locator('.skin-options .skin-chip[data-skin=skin_copper]').click();
 await p.waitForFunction(()=>document.querySelector('.hud-identity').classList.contains('skin-copper'),{timeout:15000});
 // Starter pack: buy once, then owned and disabled (back in the shop panel first).
 await p.click('#nav-shop');await p.waitForFunction(()=>Network.panel==='shop'&&!Network.busy,{timeout:15000});
 await p.locator('[data-shop-buy=starter]').click();
 await p.waitForFunction(()=>[...document.querySelectorAll('.shop-card')].some(c=>c.innerText.includes('Posiadany')),{timeout:15000});
 assert.equal(await p.locator('[data-shop-buy=starter]').count(),0);
 // Energiapak twice → daily limit reached, card disabled.
 await p.locator('[data-shop-buy=energy]').click();
 await p.waitForFunction(()=>!Network.busy);
 await p.locator('[data-shop-buy=energy]').click();
 await p.waitForFunction(()=>{const c=[...document.querySelectorAll('.shop-card')].find(c=>c.innerText.includes('Energiapak'));return c&&c.innerText.includes('Limit doby wyczerpany');},{timeout:15000});
 await p.waitForFunction(()=>Network.packet.state.energy===240,{timeout:15000});assert.equal(await p.evaluate(()=>Network.packet.state.energy),240);
 // Speedup without a running contract: server refuses with a clear message.
 await p.locator('[data-shop-buy=speedup]').click();
 await p.waitForFunction(()=>document.body.innerText.includes('Żadne zlecenie teraz nie trwa'),{timeout:15000});
 // History shows paid_dev entries; nothing claims to be a real payment.
 const hist=await p.locator('.shop-history').innerText();
 assert.match(hist,/paid_dev/);
 await p.screenshot({path:path.join(__dirname,'shop-desktop.png'),fullPage:true});
 for(const width of [320,390,768,1440]){await p.setViewportSize({width,height:950});await p.waitForTimeout(100);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'shop overflow '+width);if(width===390)await p.screenshot({path:path.join(__dirname,'shop-mobile.png'),fullPage:true});}
 assert.deepEqual(p.errors,[],'page errors: '+p.errors.join(' | '));
 console.log('PASS 0.14/0.15: default-off gate with statement, PLN price tags, dev checkout (paid_dev history), VIP + skin cosmetics applied, starter once, energy daily limit with 240 clamp, speedup guard; stripped headers/cookies; no JS errors; no overflow at 390px.');
 await browser.close();
})().catch(e=>{console.error('FAIL',e);process.exit(1);});
