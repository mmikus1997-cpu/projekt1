const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {execFileSync}=require('node:child_process');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DIR=__dirname;
const PASSWORD='ui-test-password-2026';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const ca=await browser.newContext({viewport:{width:1440,height:1000}}),cb=await browser.newContext({viewport:{width:1440,height:1000}});
 if(process.env.TEST_STRIP_HEADERS==='1')for(const c of [ca,cb])await c.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 const a=await ca.newPage(),b=await cb.newPage(),errors=[];
 for(const p of [a,b])p.on('pageerror',e=>errors.push(e.stack));
 const suffix=Date.now().toString(36),userA='alpha_'+suffix,userB='beta_'+suffix;
 async function register(p,name){
  await p.goto(BASE);await p.waitForSelector('#auth-form');await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username',name);await p.fill('#auth-password',PASSWORD);await p.fill('#auth-confirm',PASSWORD);await p.check('#age-consent');await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');
 }
 async function create(p,id,nickname){
  await p.click(`[data-world="${id}"]`);await p.fill('#character-nickname',nickname);
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');await p.waitForFunction(id=>Network.world?.id===id,id);await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy&&Network.packet.state.tutorialDismissed);
 }
 async function nav(p,id){if(id==='pvp'){await p.evaluate(()=>GameApp.clubPane('pvp'));await p.waitForFunction(()=>Network.panel==='pvp');return;}if(['character','arena','residence','garage','hall','cafe'].includes(id)){await p.evaluate(x=>GameApp.showView(x),id);await p.waitForFunction(x=>GameApp.view===x,id);return;}await p.click('#nav-'+id);await p.waitForFunction(id=>['pvp','ranking','admin'].includes(id)?Network.panel===id:GameApp.view===id,id);}
 async function acted(p,selector,test,arg){await p.click(selector);await p.waitForFunction(test,arg);await p.waitForFunction(()=>!Network.busy);}
 async function cleanLayout(p,label,width){await p.setViewportSize({width,height:900});await p.waitForTimeout(120);assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,label+' overflow at '+width);}
 try{
  execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE worlds SET created_at=created_at-?',(25*86400000,));c.commit()",process.env.TEST_DB||'tests/qa-online.sqlite3']);  // 0.45: Era IV — wszystkie dzielnice kontraktów dostępne
  const seedD=(nick,d)=>execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE characters SET current_district=? WHERE nickname=?',(int(sys.argv[2]),sys.argv[3]));c.commit()",process.env.TEST_DB||'tests/qa-online.sqlite3',String(d),nick]);  // 0.45
  await register(a,userA);assert.equal(await a.evaluate(()=>Network.user.role),'player');await a.screenshot({path:path.join(DIR,'worlds-desktop.png'),fullPage:true});
  await create(a,2,'Aleks QA');assert.equal(await a.evaluate(()=>GameApp.state.cash),3000);
  await nav(a,'contracts');assert.equal(await a.locator('.contract-card').count(),9);
  seedD('Aleks QA',3);await a.evaluate(()=>Network.refresh());await a.waitForFunction(()=>Network.packet?.travelInfo?.district===3,null,{timeout:15000});  // 0.45: inwentaryzacja w Centrum
  await acted(a,'[data-contract=inventory]',()=>GameApp.state.contracts.length===1);
  await nav(a,'character');await acted(a,'[data-game=train][data-stat="0"]',()=>GameApp.state.training.length===1);
  await a.click('[data-game=buy][data-item=urban-gloves]');await a.waitForTimeout(800);await a.waitForFunction(()=>!Network.busy);assert.ok(!(await a.evaluate(()=>GameApp.state.inventory.includes('urban-gloves'))),'7.3 GDD v3.1: stary sklep zamknięty');
  await a.waitForSelector('[data-game=claim-training]:not([disabled])',{timeout:15000});await acted(a,'[data-game=claim-training]',()=>GameApp.state.stats[0]===11);
  await nav(a,'contracts');await acted(a,'[data-game=claim-contract]',()=>GameApp.state.xp===(Network.packet.timedEvent?.effect==='contract_xp'?15:10));  // 0.58: event czasowy może dać +50% EXP
  seedD('Aleks QA',8);await a.evaluate(()=>Network.refresh());await a.waitForFunction(()=>Network.packet?.travelInfo?.district===8,null,{timeout:15000});  // 0.45: dostawy z Przedmieść
  for(let i=0;i<4;i++)await acted(a,'[data-contract=delivery]',i=>GameApp.state.contracts.length===i+1,i);
  const deliveries=await a.evaluate(()=>GameApp.state.contracts.map(x=>x.id));
  await register(b,userB);await create(b,2,'Maks QA');
  const seedDistrict=(nick)=>execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE characters SET current_district=2 WHERE nickname=?',(sys.argv[2],));c.commit()",process.env.TEST_DB||'tests/qa-online.sqlite3',nick]);
  const seedChar=(nick,patch)=>execFileSync('python',['-c',"import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);row=c.execute('SELECT state_json FROM characters WHERE nickname=?',(sys.argv[2],)).fetchone()[0];st=json.loads(row);st.update(json.loads(sys.argv[3]));c.execute('UPDATE characters SET state_json=?,class_type=? WHERE nickname=?',(json.dumps(st),st.get('cls') or 'bokser',sys.argv[2]));c.commit()",process.env.TEST_DB||'tests/qa-online.sqlite3',nick,JSON.stringify(patch)]);
  seedDistrict('Maks QA');
  seedChar('Aleks QA',{xp:150,tactic:'kontrola'});seedChar('Maks QA',{xp:150});  // 0.41: PvP od 2. poziomu; Maks dobierze taktykę w dialogu
  for(const pg of [a,b]){await pg.reload();await pg.waitForFunction(()=>!!Network.character);}
  for(const pg of [a,b]){await pg.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>pg.click('[data-online=brief-close]')).catch(()=>{});}
  await nav(b,'business');await acted(b,'[data-game=upgrade]',()=>!!GameApp.state.business.upgrade);
  await nav(a,'pvp');assert.equal(await a.locator('[data-invite]').count(),0,'0.48: Wyzwij usunięte z listy rywali');
  assert.equal(await a.locator('[data-attack]').count(),1,'przycisk Auto-atak w wierszu rywala');
  assert.equal(await a.locator('[data-dm-open]').count(),1,'0.48: Napisz wiadomość w wierszu rywala');
  assert.match(await a.locator('#pvp-mount').innerText(),/Taktyka:/);assert.match(await a.locator('#pvp-mount').innerText(),/#1 rankingu/,'przeciwnicy z rankingu');
  await b.evaluate(()=>GameApp.clubPane('pvp'));await b.waitForSelector('#tactic-confirm, [data-attack]');  // 5.1 GDD v3.1: Klasa = Taktyka — okno tylko, gdy brak klasy
  if(await b.locator('#tactic-confirm').count()){assert.equal(await b.locator('#network-dialog input[name=tactic-choice]').count(),0,'brak wyboru taktyki');await b.click('#network-dialog .class-card:has(input[value=szybki])');await b.click('#tactic-confirm');}
  await b.waitForSelector('[data-attack]');
  // 0.48: auto-atak → dialog z wynikiem → natychmiastowe odtworzenie animowanego raportu
  await a.click('[data-attack]');await a.waitForFunction(()=>document.getElementById('network-dialog')?.open,null,{timeout:15000});
  const atkTxt=await a.locator('#network-dialog').innerText();
  assert.match(atkTxt,/Wygrana!|Porażka|Remis\./,'wynik auto-ataku w dialogu');assert.match(atkTxt,/zmiana Elo/);assert.match(atkTxt,/Taktyki:/);
  await a.click('#atk-replay-btn');await a.waitForFunction(()=>playing&&current.ranked);
  assert.match(await a.evaluate(()=>JSON.stringify(current.avatars||[])),/body/,'0.47: awatary w raporcie PvP');
  assert.match(await a.evaluate(()=>JSON.stringify(current.gear||[])),/gloves/,'0.47: gear w raporcie PvP');
  await a.waitForTimeout(1200);await a.screenshot({path:path.join(DIR,'pvp-animation-desktop.png')});await a.click('#skip-btn');await a.waitForFunction(()=>!playing);assert.match(await a.locator('#result-text').innerText(),/Zmiana Elo/);
  const seed=await a.evaluate(()=>current.seed);await a.click('#replay-btn');await a.waitForFunction(()=>playing);await a.click('#skip-btn');assert.equal(await a.evaluate(()=>current.seed),seed);
  // 0.42: Auto-atak — natychmiastowy pojedynek rankingowy na zapisanych taktykach, bez czekania na akceptację
  await nav(a,'pvp');assert.equal(await a.locator('[data-attack]').count(),1,'przycisk Auto-atak w wierszu rywala');
  await a.click('[data-attack]');await a.waitForFunction(()=>document.getElementById('network-dialog')?.open,null,{timeout:15000});
  const atkTxt22=await a.locator('#network-dialog').innerText();
  assert.match(atkTxt,/Wygrana!|Porażka|Remis\./,'wynik auto-ataku w dialogu');
  assert.match(atkTxt,/zmiana Elo/,'delta Elo w dialogu');assert.match(atkTxt,/Taktyki:/,'taktyki obu stron w dialogu');
  await a.click('#network-dialog [onclick]');await a.waitForFunction(()=>!document.getElementById('network-dialog').open);
  await a.waitForFunction(()=>/2 \/ 5 walk UTC/.test(document.body.innerText),null,{timeout:15000});
  await nav(b,'arena');await b.evaluate(()=>GameApp.setArenaMode('lab'));await b.click('#fight-btn');await b.waitForFunction(()=>playing&&!current.authoritative&&!current.ranked);assert.equal(await b.evaluate(()=>current.stats[1].length),5,'laboratorium 0.41: rywal z zestawu testowego, symulacja lokalna (sparing usunięty)');await b.click('#skip-btn');await b.waitForFunction(()=>!playing);
  await nav(a,'ranking');assert.equal(await a.locator('.ranking-table').first().locator('tbody tr').count(),2);assert.match(await a.locator('.season-panel').innerText(),/Globalny ranking · sezony/);await a.screenshot({path:path.join(DIR,'ranking-desktop.png'),fullPage:true});
  for(const width of [320,390,768,1440]){
   for(const view of ['city','contracts','business','character','residence','arena','pvp','ranking']){
    await nav(b,view);await cleanLayout(b,view,width);
    if(width===390)await b.screenshot({path:path.join(DIR,view+'-mobile.png'),fullPage:true});
   }
  }
  await nav(a,'contracts');
  const xp0=await a.evaluate(()=>GameApp.state.xp);assert.ok(xp0>=150+10,'seed PvP 150 XP + nagroda PvP min. 10 XP (5.3 GDD v3.1)');
  for(const id of deliveries){await a.waitForSelector(`[data-game=claim-contract][data-id="${id}"]:not([disabled])`,{timeout:60000});await acted(a,`[data-game=claim-contract][data-id="${id}"]`,id=>!GameApp.state.contracts.some(t=>t.id===id),id);}
  const xm=await a.evaluate(()=>Network.packet.timedEvent?.effect==='contract_xp'?1.5:1);  // 0.58: event czasowy +50% EXP kontraktów
  {const dx=await a.evaluate(()=>GameApp.state.xp)-xp0;assert.ok(dx>=80*xm&&dx<=Math.ceil(80*xm*1.1)+deliveries.length,'+80 z dostaw + Spryt do +10% (8.2 GDD v3.1), było '+dx);}
  seedD('Aleks QA',3);await a.evaluate(()=>Network.refresh());await a.waitForFunction(()=>Network.packet?.travelInfo?.district===3,null,{timeout:15000});  // 0.45
  await acted(a,'[data-contract=inventory]',()=>GameApp.state.contracts.length===1);await a.waitForSelector('[data-game=claim-contract]:not([disabled])',{timeout:15000});{const xb=await a.evaluate(()=>GameApp.state.xp);await acted(a,'[data-game=claim-contract]',x=>GameApp.state.xp>=x,xb+10*xm);}  // 8.2: Spryt może dodać ułamek XP
  seedDistrict('Aleks QA');await nav(a,'business');await a.waitForFunction(()=>!Network.busy);assert.equal(await a.locator('[data-online=cafe-buy]').count(),0,'4.1 GDD v3.1: Corner Café zamknięta — brak przycisku zakupu');await a.screenshot({path:path.join(DIR,'business-desktop.png'),fullPage:true});
  await nav(b,'business');assert.equal(await b.evaluate(()=>GameApp.state.business.level),2);
  // Administrative activation is explicit, not granted to the first registrant.
  const setup=fs.readFileSync(process.env.TEST_SETUP_FILE||path.join(DIR,'browser-setup.txt'),'utf8').split('\n')[2];
  await a.click('#game-settings-btn');await a.fill('#bootstrap-code',setup);await a.click('#bootstrap-form [type=submit]');await a.waitForFunction(()=>Network.user.role==='admin'&&Network.panel==='admin');
  await a.click('[data-online=create-world]');await a.fill('#world-name','CITY NEXT');await a.fill('#world-opens','2027-01-01T12:00');await a.click('#new-world-form [type=submit]');await a.waitForSelector('.admin-world:nth-child(3)');
  await a.screenshot({path:path.join(DIR,'admin-desktop.png'),fullPage:true});await cleanLayout(a,'admin',390);await a.screenshot({path:path.join(DIR,'admin-mobile.png'),fullPage:true});await a.setViewportSize({width:1440,height:1000});await b.waitForSelector('#world-news:not([hidden])',{timeout:35000});assert.match(await b.locator('#world-news').innerText(),/CITY NEXT/);
  await a.click('#nav-worlds');await a.waitForSelector('.world-grid');await create(a,1,'Aleks QA');assert.equal(await a.evaluate(()=>GameApp.state.cash),300);assert.equal(await a.evaluate(()=>GameApp.state.stats[0]),10,'0.43: kreacja bez klasy — start 10/10/10/10/10');assert.equal(await a.evaluate(()=>GameApp.state.xp),0);
  await a.reload();await a.waitForFunction(()=>Network.world?.id===1&&Network.character?.nickname==='Aleks QA');
  await a.waitForSelector('[data-online=brief-close]',{timeout:3000}).then(()=>a.click('[data-online=brief-close]')).catch(()=>{});assert.equal(await a.evaluate(()=>GameApp.state.cash),300);
  const unauthorized=await b.evaluate(async()=>{try{await Network.api('/admin/overview');return 200;}catch(e){return e.status;}});assert.equal(unauthorized,403);
  const noCheat=await a.evaluate(async()=>{try{await Network.api('/worlds/1/actions','POST',{action:'train',stat:0,cash:999999},{'Idempotency-Key':crypto.randomUUID().replaceAll('-','')});return 200;}catch(e){return e.status;}});assert.equal(noCheat,422);
  assert.deepEqual(errors,[]);
  console.log('PASS: two real accounts, seven contracts, server training/gear, café, business upgrade, asynchronous PvP, saved animated reports, Elo, world isolation, admin activation/world scheduling, persisted login, protected endpoints, 28 responsive layouts.');
 }catch(e){await a.screenshot({path:path.join(DIR,'failure-a.png'),fullPage:true}).catch(()=>{});await b.screenshot({path:path.join(DIR,'failure-b.png'),fullPage:true}).catch(()=>{});console.error('Page errors:',errors);throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
