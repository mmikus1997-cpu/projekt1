const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3233';
const DB=process.env.TEST_DB||'tests/qa-stats.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
const setStats=(json)=>execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute(\"UPDATE characters SET state_json=json_set(state_json,'$.stats',json(?)) WHERE nickname='Statystyk'\",(sys.argv[2],));c.commit()",DB,json]);
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','stats_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  await p.fill('#character-nickname','Statystyk');
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');
  await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  // Baseline: panel pokazuje same zera (postać 10×5 — klasa Bokser zniwelowana seedem)
  setStats('[10,10,10,10,10]');await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>GameApp.state.stats[0]===10,null,{timeout:15000});
  await p.evaluate(()=>GameApp.showView('character'));await p.waitForSelector('.stats-action');
  const baseTxt=await p.locator('.stats-action').innerText();
  assert.match(baseTxt,/kontrakty −0% czasu/,'baseline: zero bonusu Siły');
  assert.match(baseTxt,/parking \+0 miej\./,'baseline: zero bonusu parkingu');
  // Podnieś staty na bazie → lustra liczb w UI
  setStats('[50,50,50,50,50]');
  await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>GameApp.state.stats[0]===50,null,{timeout:15000});
  const txt=await p.locator('.stats-action').innerText();
  assert.match(txt,/kontrakty −16% czasu/,'Siła: −16%');
  assert.match(txt,/skarbiec firmy \+40%/,'Siła: cap 40%');
  assert.match(txt,/praca PC \+24% gotówki/,'Inteligencja: +24%');
  assert.match(txt,/rozbudowa −12% kosztu/,'Inteligencja: −12%');
  assert.match(txt,/awaria 3% \(−12 p\.p\.\)/,'Refleks: ryzyko 3% (cap redukcji)');
  assert.match(txt,/droga −25%/,'Refleks: cap 25%');
  assert.match(txt,/ceny wyposażenia −9%/,'Charyzma: cap 9%');
  assert.match(txt,/parking \+2 miej\./,'Charyzma: +2 miejsca');
  assert.match(txt,/wpływy inwestycji \+20%/,'Spryt: +20%');
  assert.match(txt,/NPC lochu −6% siły/,'Spryt: cap 6%');
  // Lustro ceny w sklepie: 250 $ × 0,91 = 228 $ (przekreślona stara)
  await p.evaluate(()=>GameApp.showView('character'));await p.waitForSelector('.gear-item');
  const price=await p.locator('.gear-item',{hasText:'Rękawice Urban'}).locator('.gear-price').innerText();
  assert.match(price,/250 \$\s*228 \$/,'cena z rabatem Charyzmy');
  // Koszt rozbudowy: 1000 × 0,88 = 880
  await p.click('#nav-business');await p.waitForFunction(()=>GameApp.view==='business');
  assert.match(await p.locator('.upgrade-action span').first().innerText(),/880 \$/,'koszt rozbudowy z rabatem Inteligencji');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS staty UI: panel „Statystyki w akcji” (zera baseline → pełne bonusy przy 50×5, capi widoczne), lustra cen (228 $), kosztu rozbudowy (880 $); 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
