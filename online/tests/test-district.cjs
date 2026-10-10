/* 0.55.0 „Moja dzielnica": 6 budynków zastępuje zakładki — karty, poziomy,
   klub-hub z kartami dyscyplin, bramka i odblokowanie Sali Chwały, rozbudowa. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const DIR=path.join(__dirname,'..','screens52');
(async()=>{
 const b=await chromium.launch({headless:true});
 const p=await b.newPage({viewport:{width:1280,height:900}});
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(process.env.TEST_BASE_URL);
 const uid='district_'+Date.now().toString(36);
 await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username',uid);await p.fill('#auth-password','test-password-long-123');await p.fill('#auth-confirm','test-password-long-123');
 await p.check('#age-consent');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');
 await p.click('[data-world="1"]');
 await p.fill('#character-nickname','Dzielnik');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');
 await p.waitForFunction(()=>Network.world?.id===1);
 await p.waitForSelector('[data-online=dismiss-tutorial]',{timeout:6000}).then(()=>p.click('[data-online=dismiss-tutorial]')).catch(()=>{});
 // 1) Hub dzielnicy: 6 kart budynków, Sala Chwały pod bramką, paski poziomu
 await p.click('#nav-city');
 await p.waitForSelector('.bld-card[data-bld]',{timeout:15000});
 const keys=await p.evaluate(()=>[...document.querySelectorAll('.bld-card[data-bld]')].map(x=>x.dataset.bld));
 assert.deepEqual(keys.sort(),['cafe','club','garage','gym','hall','residence'],'6 kart budynków');
 assert.ok(await p.locator('.bld-card[data-bld=hall].locked').count(),'Sala Chwały zablokowana na start');
 assert.match(await p.locator('.bld-card[data-bld=residence] .bld-level').innerText(),/POZIOM 1/,'poziom na karcie');
 // 2) Garaż: 5 aut z grafikami; Siłownia: pasek budynku
 await p.evaluate(()=>GameApp.showView('garage'));await p.waitForFunction(()=>GameApp.view==='garage');
 assert.equal(await p.locator('.car-card').count(),6,'5 aut + Mistrz Rankingu w Garażu (3.1)');
 assert.ok(await p.locator('#view-garage .bld-bar .bld-pips').count(),'pasek poziomu z pipsami w Garażu');
 await p.evaluate(()=>GameApp.showView('character'));await p.waitForFunction(()=>GameApp.view==='character');
 assert.ok(await p.locator('#view-character .bld-bar').count(),'Siłownia: pasek poziomu');
 // 3) Sala Klubowa: hub z kartami dyscyplin, powrót
 await p.evaluate(()=>GameApp.showView('arena'));await p.waitForFunction(()=>GameApp.view==='arena');
 await p.waitForSelector('#club-hub .club-card[data-tab]',{timeout:15000});
 assert.equal(await p.locator('#club-hub .club-card[data-tab]').count(),8,'8 kart dyscyplin w hubie klubu');
 assert.equal(await p.locator('#club-back:visible').count(),0,'hub bez przycisku powrotu');
 await p.click('#club-hub .club-card[data-tab="ring"]');
 await p.waitForSelector('#sport-pane-ring:not([hidden])',{timeout:10000});
 assert.ok(await p.locator('#club-back:visible').count(),'przycisk powrotu w widoku dyscypliny');
 await p.click('#club-back');
 await p.waitForSelector('#club-hub:not([hidden]) .club-card[data-tab]');
 // 4) Sala Chwały: bramka 5 wierszy + historia z wykresem pod bramką
 await p.evaluate(()=>GameApp.showView('hall'));await p.waitForFunction(()=>GameApp.view==='hall');
 await p.waitForSelector('.hall-gate',{timeout:10000});
 assert.equal(await p.locator('.hall-gate .hall-row').count(),5,'5 wierszy w bramce (bez Sali Chwały)');
 assert.ok(await p.locator('#view-hall .story-panel').count(),'historia widoczna pod bramką');
 assert.ok(await p.locator('#view-hall .daily-chart').count(),'wykres dzienny w Sali Chwały');
 assert.equal(await p.locator('.hall-board-panel').count(),0,'panel tablicy dopiero po odblokowaniu');
 // 5) Rozbudowa przez UI: 1→2 za 500 $
 execFileSync('python',[path.join(__dirname,'..','manage.py'),'--db',process.env.TEST_DB,'grant-cash',uid,'2000']);
 await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
 await p.evaluate(()=>GameApp.showView('residence'));await p.waitForFunction(()=>GameApp.view==='residence');
 await p.waitForSelector('#view-residence [data-game=upgrade-building][data-building=residence]');
 await p.click('#view-residence [data-game=upgrade-building][data-building=residence]');
 await p.waitForFunction(()=>GameApp.state.buildings.residence===2,null,{timeout:15000});
 await p.waitForFunction(()=>!Network.busy);
 assert.equal(await p.evaluate(()=>GameApp.state.cash),2000+300-500,'koszt 500 $ pobrany');
 // 6) Odblokowanie Sali Chwały: wszystkie na 5 → bramka znika, tablica 6 wierszy
 execFileSync('python',['-c',
  "import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);r=c.execute('SELECT id,state_json FROM characters WHERE nickname=?',(sys.argv[2],)).fetchone();st=json.loads(r[1]);st['buildings']={'residence':5,'garage':5,'cafe':10,'nightclub':7,'club':1,'hall':0};st['cash']=10000;c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(st),r[0]));c.commit()",
  process.env.TEST_DB,'Dzielnik']);
 await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
 await p.evaluate(()=>GameApp.showView('hall'));await p.waitForFunction(()=>GameApp.view==='hall');
 // 4.1 GDD v3.1: stary web zna tylko starą bramkę (Siłownia/Sala Klubowa 5) — otwarcie przez API, UI we Flutterze
 await p.evaluate(()=>Network.action({action:'upgrade_building',building:'hall'}));
 await p.waitForFunction(()=>GameApp.state.buildings.hall===1,null,{timeout:15000});
 await p.waitForFunction(()=>!Network.busy);
 await p.waitForSelector('.hall-board',{timeout:10000});
 assert.equal(await p.locator('.hall-board .hall-row').count(),6,'6 wierszy na tablicy po odblokowaniu');
 assert.equal(await p.locator('.hall-gate').count(),0,'bramka znika po odblokowaniu');
 assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
 console.log('PASS district: 6 budynków, klub hub 8 kart, bramka+odblokowanie Sali Chwały, rozbudowa, 0 błędów JS');
 await b.close();
})().catch(e=>{console.error('ERR',e.message);process.exit(1)});
