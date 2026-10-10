const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3227';
const DB=process.env.TEST_DB||'tests/qa-classes.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','klasy_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  // 0.43: kreator BEZ wyboru klasy — start 10/10/10/10/10
  await p.fill('#character-nickname','Blyskawica');
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');
  await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  assert.equal(await p.evaluate(()=>GameApp.state.stats.join(',')),'10,10,10,10,10','kreacja bez klasy: równe statystyki');
  // Profil: bez klasy przed pierwszym PvP (linia klasy pojawia się dopiero po wyborze)
  // Pierwsze wejście w PvP = okno "Twoja karta zawodnika": klasa + taktyka, oba jednorazowe (PvP od 2 lvl -> seed XP)
  // Rywal do rankingu — przez API (jedno konto na przeglądarkę), aby panel PvP miał cele
  const reg=await fetch(BASE+'/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json','x-city-preview-session':'1'},body:JSON.stringify({username:'cien_cls',password:'test-password-long-123',consent:true})});
  const rj=await reg.json();assert.ok(rj.csrf&&rj.previewSessionToken,'rejestracja rywala: '+JSON.stringify(rj).slice(0,80));
  const ch=await fetch(BASE+'/api/worlds/2/character',{method:'POST',headers:{'Content-Type':'application/json','Authorization':'Bearer '+rj.previewSessionToken,'X-CSRF-Token':rj.csrf},body:JSON.stringify({nickname:'Cien',accept_test_reset:true})});
  assert.ok(ch.ok,'postać rywala: HTTP '+ch.status);
  // PvP od 2 lvl -> seed XP przed pierwszym wejściem w ranking
  const {execFileSync}=require('node:child_process');
  execFileSync('python',['-c',"import sqlite3,json,os;c=sqlite3.connect(os.environ.get('TEST_DB','tests/qa-classes.sqlite3'));r=c.execute(\"SELECT state_json FROM characters WHERE nickname='Blyskawica'\").fetchone()[0];st=json.loads(r);st['xp']=400;c.execute(\"UPDATE characters SET state_json=? WHERE nickname='Blyskawica'\",(json.dumps(st),));c.commit()"]);
  await p.reload();await p.waitForFunction(()=>!!Network.character);
  await p.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>p.click('[data-online=brief-close]')).catch(()=>{});
  await p.evaluate(()=>GameApp.clubPane('pvp'));await p.waitForSelector('#tactic-confirm',{timeout:15000});
  assert.ok(await p.locator('#tactic-confirm').isDisabled(),'potwierdzenie zablokowane do wyboru klasy');
  assert.equal(await p.locator('#network-dialog input[name=class-choice]').count(),3,'3 klasy w oknie PvP');
  assert.equal(await p.locator('#network-dialog input[name=tactic-choice]').count(),0,'5.1 GDD v3.1: Klasa = Taktyka — brak wyboru taktyki');
  await p.click('#network-dialog .class-card:has(input[value=szybki])');
  await p.click('#tactic-confirm');
  await p.waitForFunction(()=>Network.character?.classType==='szybki',null,{timeout:15000});
  await p.waitForSelector('#pvp-mount [data-attack]',{timeout:15000});
  // Statystyki Szybkiego po wydaniu karty zawodnika
  await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>Network.packet&&!Network.busy);
  assert.equal(await p.evaluate(()=>GameApp.state.stats.join(',')),'8,8,14,8,12','klasa wybrana w PvP: statystyki Szybkiego');
  await p.evaluate(()=>GameApp.showView('character'));await p.waitForSelector('.class-line');
  assert.match(await p.locator('.class-line').innerText(),/Szybki/,'klasa w profilu');
  assert.match(await p.locator('.class-line').innerText(),/Lokacja: Ulica/,'lokacja startowa w profilu');
  // Drugie wejście w PvP: bez okna — panel prosto (wybory jednorazowe)
  await p.evaluate(()=>GameApp.clubPane('pvp'));await p.waitForSelector('#pvp-mount [data-attack]',{timeout:15000});
  assert.equal(await p.locator('#network-dialog[open]').count(),0,'okno wyboru już nie wraca');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS klasy UI 0.43: kreacja bez klasy (10×5), karta zawodnika przy 1. PvP (3 klasy + 3 taktyki, jednorazowo), statystyki 8/8/14/8/12, panel PvP bez ponownego okna; 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
