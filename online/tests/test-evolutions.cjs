const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3231';
const DB=process.env.TEST_DB||'tests/qa-evolutions.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
const setXp=(nick,xp)=>execFileSync('python',['-c',"import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);s=json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(sys.argv[2],)).fetchone()[0]);s['xp']=int(sys.argv[3]);c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),sys.argv[2]));c.commit()",DB,nick,String(xp)]);
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','evo_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  await p.fill('#character-nickname','Strażnik UI');
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');
  await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  // 0.43: klasa wybierana przy pierwszym PvP, nie w kreacji — seedujemy obroncę (tu: flow ewolucji)
  execFileSync('python',['-c',"import sqlite3,json,sys;c=sqlite3.connect(sys.argv[1]);r=c.execute(\"SELECT state_json FROM characters WHERE nickname='Strażnik UI'\").fetchone()[0];st=json.loads(r);st['cls']='obronca';c.execute(\"UPDATE characters SET class_type='obronca' WHERE nickname='Strażnik UI'\");c.execute(\"UPDATE characters SET state_json=? WHERE nickname='Strażnik UI'\",(json.dumps(st),));c.commit()",DB]);
  await p.reload();await p.waitForFunction(()=>!!Network.character);
  await p.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>p.click('[data-online=brief-close]')).catch(()=>{});
  await p.evaluate(()=>GameApp.showView('character'));await p.waitForSelector('.class-line');
  assert.match(await p.locator('.class-line').innerText(),/bez ewolucji/);
  assert.equal(await p.locator('.evo-banner').count(),0,'poziom 1: brak banera');
  // Awans na poziom 10 (xp=4500) → baner z 2 kartami po odświeżeniu
  setXp('Strażnik UI',4500);
  await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>GameApp.state.xp===4500,null,{timeout:15000});
  await p.waitForSelector('.evo-banner');
  assert.equal(await p.locator('.evo-card').count(),2,'dwie karty specjalizacji');
  assert.match(await p.locator('.evo-banner .eyebrow').innerText(),/DOSTĘPNA EWOLUCJA KLASOWA/);
  assert.match(await p.locator('.evo-card').first().innerText(),/Murarz Ringu/);
  assert.match(await p.locator('.evo-card').last().innerText(),/Żelazny Strażnik/);
  // Klik bez wyboru → toast, brak zmian
  await p.click('[data-extra=evolve]');
  await p.waitForFunction(()=>Network.packet?.character?.evolutionCode===undefined,null,{timeout:5000}).catch(()=>{});
  assert.equal(await p.evaluate(()=>Network.packet?.character?.evolutionCode??null),null,'bez karty nie wybiera');
  // Wybór Riposty
  await p.click('.evo-card:has(input[value=zelazny-straznik])');
  await p.click('[data-extra=evolve]');
  await p.waitForFunction(()=>Network.packet?.character?.evolutionCode==='zelazny-straznik',null,{timeout:15000});
  await p.waitForFunction(()=>document.querySelector('.evo-banner')===null,null,{timeout:15000});
  assert.match(await p.locator('.class-line').innerText(),/Żelazny Strażnik/,'linia klasy z ewolucją');
  assert.match(await p.locator('.class-line').innerText(),/Riposta/,'pasywka w profilu');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS ewolucje UI: poziom 1 bez banera, od 10 poziomu baner z 2 kartami, klik bez wyboru odrzucony, Riposta wybrana jednorazowo, linia klasy z pasywką, baner znika; 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
