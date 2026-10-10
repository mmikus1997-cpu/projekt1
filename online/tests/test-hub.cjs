const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3224';
const DB=process.env.TEST_DB||'tests/qa-hub.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','hub_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  await p.fill('#character-nickname','Hubster');if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  await p.click('#nav-city');await p.waitForSelector('.district-grid');
  assert.equal(await p.locator('.bld-card').count(),6,'6 budynków dzielnicy');
  assert.equal(await p.locator('.bld-card.locked').count(),1,'Sala Chwały pod bramką');
  assert.equal(await p.locator('.hub-back:visible').count(),0,'hub nie ma paska powrotu');
  await p.waitForSelector('.era-chip');
  assert.match(await p.locator('.era-chip').innerText(),/Era 1 \/ 4 · Czas Pionierów \(Dzień 1\/28\)/,'wskaźnik Ery na hubie');
  // Kafel → Przedsiębiorstwa i powrót
  await p.click('.map-pin[data-go=business]');await p.waitForFunction(()=>GameApp.view==='business');
  await p.waitForSelector('.hub-back');
  assert.match(await p.locator('.hub-back:visible').first().innerText(),/Powrót do: Nadmorskie/);
  await p.click('.hub-back');await p.waitForFunction(()=>GameApp.view==='city');
  await p.waitForSelector('.district-grid');
  // Panel sklepu też ma pasek powrotu
  await p.click('#nav-shop');await p.waitForFunction(()=>Network.panel==='shop');
  await p.waitForSelector('#view-external .hub-back');
  await p.click('#view-external .hub-back:visible');await p.waitForFunction(()=>GameApp.view==='city');
  // Podróż: overlay z odliczaniem, bez przycisku VIP dla zwykłego gracza
  await p.evaluate(()=>Network.api('/worlds/2/travel','POST',{target_district:2,mode:'bus'}));
  await p.waitForFunction(()=>Network.packet?.travelInfo?.travel,null,{timeout:15000});
  await p.waitForSelector('#travel-overlay:not([hidden])');
  const ov=await p.locator('#travel-overlay').innerText();
  assert.match(ov,/W drodze do: Przemysłowe/,'cel na overlayu');
  assert.match(ov,/Pozostało: \d{2}:\d{2}/,'odliczanie MM:SS');
  assert.equal(await p.locator('[data-extra=travel-speedup]').count(),0,'bez VIP brak Przyspiesz');
  // Czat: własna wiadomość w złotym dymku po prawej
  await p.evaluate(()=>Network.panel=null);
  await p.click('#nav-community');await p.waitForSelector('#chat-form');
  await p.fill('#chat-text','Hej z huba UI!');await p.click('#chat-form [type=submit]');
  await p.waitForSelector('#chat-messages .chat-own',{timeout:15000});
  assert.match(await p.locator('#chat-messages .chat-own p').last().innerText(),/Hej z huba UI!/);
  assert.equal(await p.locator('#chat-messages .chat-own').count(),1);
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS hub UI: 6 kafelków, nawigacja kaflami, pasek powrotu (widok+panel), overlay podróży z MM:SS, własny dymek czatu; 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
