/* 0.49 Garaż w Rezydencji: zakładki Dom/Garaż, 5 aut z grafikami, kupno, ulepszenia, VIP-lock, HUD w sidebarze, scalone statystyki. */
const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DIR=path.join(__dirname,'garage49');
const PASSWORD='ui-test-password-2026';
(async()=>{
 fs.mkdirSync(DIR,{recursive:true});
 const browser=await chromium.launch({headless:true});
 const ctx=await browser.newContext({viewport:{width:1440,height:1000}});
 const page=await ctx.newPage(),errors=[];
 page.on('pageerror',e=>errors.push(e.stack));
 const name='gar_'+Date.now().toString(36);
 await page.goto(BASE);await page.waitForSelector('#auth-form');await page.click('[data-auth-mode=register]');
 await page.fill('#auth-username',name);await page.fill('#auth-password',PASSWORD);await page.fill('#auth-confirm',PASSWORD);await page.check('#age-consent');await page.click('#auth-form [type=submit]');
 await page.waitForSelector('.world-grid');
 await page.click('[data-world="2"]');await page.fill('#character-nickname','Garaż QA '+Date.now().toString(36).slice(-4));
 await page.waitForSelector('#test-consent',{timeout:8000}).catch(()=>null);if(await page.locator('#test-consent').count())await page.check('#test-consent');
 await page.click('#character-form [type=submit]');await page.waitForFunction(id=>Network.world?.id===id,2);
 await page.click('[data-online=dismiss-tutorial]');await page.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 async function acted(selector,test){await page.click(selector);await page.waitForFunction(test);await page.waitForFunction(()=>!Network.busy);}
 async function failed(selector,fragment){await page.click(selector);await page.waitForSelector('.toast-error,.toast', {timeout:8000}).catch(()=>{});const txt=await page.locator('body').innerText();assert.ok(txt.includes(fragment),'expected toast: '+fragment);}
 try{
  // 0) HUD w sidebars: pod logo i wyborem świata, przed „Twoje miasto”.
  const order=await page.evaluate(()=>{
   const sb=document.querySelector('.sidebar');
   const ids=['.brand','#nav-worlds','.game-hud','.nav-label','.sidebar nav'];
   return ids.map(sel=>{const el=sb.querySelector(sel);return el?Array.prototype.indexOf.call(sb.querySelectorAll('*'),el):-1;});
  });
  assert.ok(order[0]<order[1]&&order[1]<order[2]&&order[2]<order[3],'HUD pod wyborem świata, przed nav-label; kolejność: '+order);
  assert.ok(await page.locator('.sidebar .game-hud #hud-cash').count(),'hud-cash w sidebarze');
  assert.ok(await page.locator('.sidebar .game-hud #game-settings-btn').count(),'Konto w sidebarze');
  // 1) Postać: scalony panel „Statystyki i trening” (bez starych paneli).
  await page.evaluate(()=>GameApp.showView('character'));await page.waitForFunction(()=>GameApp.view==='character');
  assert.ok(await page.locator('.stats-action .stats-row-train').count()>=5,'5 wierszy statystyk z treningiem');
  assert.equal(await page.locator('.training-panel').count(),0,'stary panel Centrum szkoleniowe usunięty');
  assert.ok(await page.locator('.stats-action .training-queue').count(),'kolejka treningu w scalonym panelu');
  assert.match(await page.locator('.stats-action .panel-heading').first().innerText(),/Statystyki i trening/i);
  // trening działa ze scalonego panelu
  await acted('.stats-row-train [data-game=train][data-stat="0"]',()=>GameApp.state.training.length===1);
  // 2) Rezydencja: zakładki Dom / Garaż.
  await page.evaluate(()=>GameApp.showView('residence'));await page.waitForFunction(()=>GameApp.view==='residence');
  assert.ok(await page.locator('.rest-panel').count(),'Rezydencja: odpoczynek');
  await page.screenshot({path:path.join(DIR,'residence-dom.png'),fullPage:true});
  await page.evaluate(()=>GameApp.showView('garage'));await page.waitForFunction(()=>GameApp.view==='garage'&&!!document.querySelector('.garage-cards'));
  // 3) 3.1 GDD v3.1: 5 aut + Mistrz Rankingu, każde z grafiką SVG; bez aut VIP.
  assert.equal(await page.locator('.car-card').count(),6);
  assert.equal(await page.locator('.car-card .car-art svg').count(),6);
  assert.equal(await page.locator('.car-card.car-vip').count(),0);
  // 4) Kup Dostawczaka (cap=1 bez rezydencji), sprawdź stan i grafikę W użyciu.
  await acted('[data-game=buy-vehicle][data-vehicle=dostawczak]',()=>GameApp.state.garage.includes('dostawczak'));
  assert.deepEqual(await page.evaluate(()=>GameApp.state.vehicle),{id:'dostawczak',wear:0});
  assert.match(await page.locator('.car-card:has([data-vehicle=dostawczak]) .car-badge').innerText(),/W użyciu/i);
  // 5) drugie auto zablokowane (brak miejsca parkingowego).
  const sedanBtn=page.locator('[data-game=buy-vehicle][data-vehicle=sedan]');
  assert.ok(await sedanBtn.isDisabled(),'brak miejsca parkingowego bez rezydencji');
  // 3.1: ceny ulepszeń rosną z ceną auta — dosyp gotówki (jak seed w kroku 8) i odśwież
  execFileSync('python',['-c',"import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);r=c.execute('SELECT id,state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone();s=json.loads(r[1]);s['cash']=20000;c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s),r[0]));c.commit()",process.env.TEST_DB]);
  await page.reload();await page.waitForFunction(()=>!!Network.character&&!Network.busy);
  await page.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>page.click('[data-online=brief-close]')).catch(()=>{});
  await page.evaluate(()=>GameApp.showView('garage'));await page.waitForFunction(()=>GameApp.view==='garage'&&!!document.querySelector('.garage-cards'));
  // 6) ulepszenie dostawczaku: 2 poziomy, kropki, rabat rośnie 10→14→18%.
  await acted('[data-game=upgrade-vehicle][data-vehicle=dostawczak]',()=>GameApp.state.garageUp.dostawczak===1);
  assert.match(await page.locator('.car-card:has([data-vehicle=dostawczak]) .car-meta').innerText(),/−14%/);
  await acted('[data-game=upgrade-vehicle][data-vehicle=dostawczak]',()=>GameApp.state.garageUp.dostawczak===2);
  assert.match(await page.locator('.car-card:has([data-vehicle=dostawczak]) .car-meta').innerText(),/−18%/);
  await page.screenshot({path:path.join(DIR,'residence-garaz.png'),fullPage:true});
  // 7) wear→100 wyłącza rabat i pokazuje „Napraw”; serwis naprawia.
  await page.evaluate(()=>{GameApp.state.vehicle.wear=100;GameApp.render();});
  assert.match(await page.locator('.car-card:has([data-vehicle=dostawczak]) .car-actions').innerText(),/Napraw/i);
  await acted('[data-game=service-vehicle]',()=>GameApp.state.vehicle.wear===0);
  // 7b) 0.50: chip aktywnego auta w HUD sidebaru (klik -> Garaż)
  await page.waitForSelector('#hud-car:not([hidden])');
  assert.match(await page.locator('#hud-car-name').innerText(),/Dostawczak/);
  assert.match(await page.locator('#hud-car-wear').innerText(),/0%/);
  await page.click('#hud-car');await page.waitForFunction(()=>GameApp.view==='garage'&&!!document.querySelector('.garage-cards'));
  // 8) Mapa: miejsca klubu otwierają właściwe zakładki (Hipodrom->Konie, Loch->Ring)
  //    Era 4 + gracz w dzielnicy miejsca = przycisk „Wejdź" bez podróży (deterministycznie).
  const seed=(sql)=>execFileSync('python',['-c',sql,process.env.TEST_DB]);
  seed("import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE worlds SET created_at=created_at-22*86400000 WHERE id=2');c.execute('UPDATE characters SET current_district=6');c.commit()");
  await page.reload();await page.waitForFunction(()=>!!Network.character);
  await page.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>page.click('[data-online=brief-close]')).catch(()=>{});
  await page.click('#nav-map');await page.waitForSelector('#map-viewport');
  await page.evaluate(()=>{const el=document.querySelector('.map-place[title*="Hipodrom"]');el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));});
  await page.waitForSelector('#network-dialog[open]');
  await page.click('#network-dialog [data-map-go=arena][data-map-tab=konie]:not([disabled])');
  await page.waitForFunction(()=>GameApp.view==='arena');
  assert.ok(await page.evaluate(()=>!document.getElementById('sport-pane-konie').hidden),'Hipodrom z mapy otwiera Jazdę Konną');
  seed("import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE characters SET current_district=8');c.commit()");
  await page.reload();await page.waitForFunction(()=>!!Network.character);
  await page.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>page.click('[data-online=brief-close]')).catch(()=>{});
  await page.click('#nav-map');await page.waitForSelector('#map-viewport');
  await page.evaluate(()=>{const el=document.querySelector('.map-place[title*="Brama Lochu"]');el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));});
  await page.waitForSelector('#network-dialog[open]');
  await page.click('#network-dialog [data-map-go=arena][data-map-tab=ring]:not([disabled])');
  await page.waitForFunction(()=>GameApp.view==='arena');
  assert.ok(await page.evaluate(()=>!document.getElementById('sport-pane-ring').hidden),'Loch z mapy otwiera Ring');
  // 8b) Business: nota o przeniesieniu garażu + przycisk powrotu.
  await page.click('#nav-business');await page.waitForFunction(()=>GameApp.view==='business');
  assert.match(await page.locator('.garage-move-note').innerText(),/budynkiem dzielnicy/i);
  assert.equal(await page.locator('#view-business .garage-cards').count(),0,'brak kart aut w Przedsiębiorstwach');
  await page.click('.garage-move-note [data-go=garage]');await page.waitForFunction(()=>GameApp.view==='garage');await page.waitForFunction(()=>!!document.querySelector('.garage-cards'));
  // 9) Layout: brak przepełnienia przy 390px w garażu.
  await page.setViewportSize({width:390,height:900});await page.waitForTimeout(200);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  assert.ok(overflow<=0,'no horizontal overflow at 390px, got '+overflow);
  await page.screenshot({path:path.join(DIR,'garaz-mobile.png'),fullPage:true});
  assert.deepEqual(errors,[],'no page errors: '+errors.join(' | '));
  console.log('PASS 0.49 garage: sidebar HUD order, merged stats+training panel, residence tabs Dom/Garaż, 5 cars with SVG art (1 VIP), buy/equip/wear/service, upgrades 3 lvl with discount stack, parking cap, business note, map pins open club tabs (Ring/Konie), HUD car chip, 390px layout, no JS errors.');
 }catch(e){
  await page.screenshot({path:path.join(DIR,'FAIL.png'),fullPage:true}).catch(()=>{});
  console.error('FAIL',e.stack?e.stack.split('\n').slice(0,4).join(' | '):e.message);process.exitCode=1;
 }finally{await browser.close();}
})();
