const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const assert=require('node:assert/strict');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3230';
const DB=process.env.TEST_DB||'tests/qa-dungeon.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','loch_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  await p.fill('#character-nickname','Groto UI');
  
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');
  await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  // loch od 3. poziomu — dosyp xp; 5.1 GDD v3.1: klasa Szybki (= taktyka Kontra) ustawiona w bazie
  execFileSync('python',['-c',"import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);row=c.execute('SELECT state_json FROM characters WHERE nickname=?',('Groto UI',)).fetchone()[0];st=json.loads(row);st['xp']=400;c.execute('UPDATE characters SET state_json=?,class_type=? WHERE nickname=?',(json.dumps(st),'szybki','Groto UI'));c.commit()",process.env.TEST_DB||'tests/qa-dungeon.sqlite3']);
  await p.reload();await p.waitForFunction(()=>!!Network.character);
  await p.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>p.click('[data-online=brief-close]')).catch(()=>{});
  // Panel lochu w profilu: brak bramy → CTA lokacji
  await p.evaluate(()=>GameApp.clubPane('ring'));await p.waitForSelector('#sport-pane-ring:not([hidden]) .dungeon-panel');  // 0.44: loch w Klubie Sportowym (zakładka Boks/MMA)
  assert.match(await p.locator('.dungeon-meta').innerText(),/Postęp: 0%/);
  await p.waitForSelector('[data-dungeon-go]');await p.click('[data-dungeon-go]');
  await p.waitForSelector('.dungeon-panel [data-dungeon-fight]',{timeout:15000});
  assert.match(await p.locator('.dungeon-panel').innerText(),/Szczur z Kanałów/,'następne piętro z nazwą NPC');
  // Walka: Szybki = Kontra → wygrana (deterministyczna vs piętro 1)
  await p.click('[data-dungeon-fight]');  // 0.41: bez własnego wyboru taktyki lochu — użyje taktyki z PvP (tu: kreator przy 1. walce)
  if(await p.locator('#tactic-confirm').count()){
   await p.click('#network-dialog .class-card:has(input[value=szybki])');  // 0.43: klasa przy pierwszej walce (nie przy kreacji)
   await p.click('#tactic-confirm');  // 5.1 GDD v3.1: Klasa = Taktyka (Szybki → Kontra) — bez wyboru taktyki
  }
  await p.waitForFunction(()=>(document.getElementById('network-dialog')?.innerText||'').includes('Wygrana!'),null,{timeout:15000});
  const dialogText=await p.locator('#network-dialog').innerText();
  assert.match(dialogText,/Wygrana!/,'dialog z wygraną');
  assert.match(dialogText,/Piętro 1/,'numer piętra w dialogu');
  await p.click('#network-dialog [onclick]');
  await p.waitForFunction(()=>!document.getElementById('network-dialog').open);
  await p.waitForFunction(()=>Network.packet?.dungeon?.progress===1,null,{timeout:15000});
  assert.equal(await p.locator('.dungeon-track span').evaluate(el=>el.style.width),'1%','6.1 GDD v3.1: pasek progresu 1% (1 ze 100 pięter Normal)');
  assert.equal(await p.locator('.loot-chip').count(),0,'piętro 1 bez unikatu');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS lochy UI: panel z progressem 0%, CTA lokacji → Brama Lochu, walka Zrównoważoną vs Szczur z Kanałów, dialog wygranej, pasek 1%, brak unikatu na piętrze 1; 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
