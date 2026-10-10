const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3223';
const DB=process.env.TEST_DB||'tests/qa-racing.sqlite3';
// 0.33: hipodrom (dzielnica 6) wymaga Ery III — postarz świat przed wyścigami
execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE worlds SET created_at=created_at-?',(16*86400000,));c.commit()",DB]);
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 const grant=(nick,cash,xp,stats)=>execFileSync('python',['-c',"import sqlite3,json,sys;c=sqlite3.connect(sys.argv[1]);r=c.execute('SELECT state_json FROM characters WHERE nickname=?',(sys.argv[2],)).fetchone();s=json.loads(r[0]);s['cash']=int(sys.argv[3]);s['xp']=int(sys.argv[4]);s['stats'][3]=int(sys.argv[5]);s['stats'][4]=int(sys.argv[6]);c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),sys.argv[2]));c.commit()",DB,nick,cash,xp,stats[0],stats[1]]);
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','racer_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  await p.fill('#character-nickname','Racer UI');if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  await p.evaluate(()=>GameApp.clubPane('konie'));await p.waitForSelector('#hipodrom:not([hidden])');
  assert.match(await p.locator('#hipodrom').innerText(),/ZERO ZAKŁADÓW/,'hipodrom renderuje się z zasadami');
  grant('Racer UI',50000,3600,[45,45]);
  await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
  await p.evaluate(()=>GameApp.clubPane('konie'));await p.waitForFunction(()=>{const b=document.querySelector('[data-extra=horse-buy][data-id=champion]');return b&&!b.disabled;},{timeout:15000});
  await p.click('[data-extra=horse-buy][data-id=champion]');
  await p.waitForFunction(()=>Network.packet?.racing?.horse?.id==='champion'&&!Network.busy,{timeout:15000});
  assert.match(await p.locator('#hipodrom .hp-horse').innerText(),/Czempion/,'koń w stajni');
  // Dojazd na tor (D6) przez API sieci gry — potem wyścig NPC z UI.
  await p.evaluate(()=>Network.api('/worlds/2/travel','POST',{target_district:6,mode:'bus'}));
  await p.waitForFunction(()=>Network.packet?.travelInfo?.travel,null,{timeout:15000});
  await p.waitForFunction(()=>Network.packet?.travelInfo?.district===6,null,{timeout:120000});  // leniwy settle po czasie jazdy
  await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
  await p.evaluate(()=>GameApp.clubPane('konie'));await p.waitForFunction(()=>!document.querySelector('[data-extra=race-comp][data-comp=wyscigi]')?.disabled,{timeout:15000});
  await p.click('#hipodrom [data-extra=race-comp][data-comp=wyscigi]');
  await p.waitForFunction(()=>{const rows=document.querySelectorAll('#hipodrom .hp-result');return rows.length>=1&&rows[0].innerText.includes('Racer UI');},{timeout:15000});
  assert.equal(await p.locator('#hipodrom .hp-result b').count(),3,'tabela wyścigu: 3 miejsca');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS racing UI: hipodrom panel, horse purchase, travel to district 6, NPC race table; no JS errors');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
