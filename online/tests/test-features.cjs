const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const path=require('node:path');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
const DB=process.env.TEST_DB||'tests/qa07.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const contexts=await Promise.all([1,2,3].map(()=>browser.newContext({viewport:{width:1440,height:1000}})));
 for(const context of contexts)await context.addInitScript(()=>{const original=fetch;window.fetch=(url,options={})=>{const h=new Headers(options.headers),keep={};if(h.has('Content-Type'))keep['Content-Type']=h.get('Content-Type');return original(url,{...options,credentials:'omit',headers:keep});};});
 const [a,b,c]=await Promise.all(contexts.map(x=>x.newPage()));for(const p of [a,b,c])p.on('pageerror',e=>errors.push(e.stack));
 const suffix=Date.now().toString(36),ua='team_a_'+suffix,ub='team_b_'+suffix;
 async function register(p,name){await p.goto(BASE);await p.click('[data-auth-mode=register]');await p.fill('#auth-username',name);await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');await p.fill('#character-nickname',name);await p.check('#test-consent');await p.click('#character-form [type=submit]');await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>Network.packet?.state.tutorialDismissed&&!Network.busy);}
 async function login(p,name,password='test'){await p.goto(BASE);await p.waitForSelector('#auth-form');await p.fill('#auth-username',name);await p.fill('#auth-password',password);await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');await p.waitForFunction(()=>Network.world?.id===2);await p.waitForTimeout(500);if(await p.locator('#network-dialog[open]').count())await p.click('[data-online=brief-close]');}
 async function community(p){await p.click('#nav-community');await p.waitForSelector('#chat-form');await p.waitForFunction(()=>!document.querySelector('#chat-status').textContent.includes('Ładowanie'));}
 async function refresh(p){await p.click('.game-page-title [data-extra=community]');await p.waitForTimeout(250);}
 async function send(p,text){await p.fill('#chat-text',text);await p.click('#chat-form [type=submit]');await p.waitForFunction(()=>document.querySelector('#chat-text')?.value==='');}
 async function chooseChannel(p,kind){await p.click(`[data-channel=${kind}]`);await p.waitForFunction(kind=>document.querySelector(`[data-channel=${kind}]`)?.getAttribute('aria-pressed')==='true',kind);await p.waitForTimeout(150);}
 async function confirm(p){await p.click('#network-dialog [data-extra=confirm]');await p.waitForFunction(()=>!document.querySelector('#network-dialog').open);await p.waitForFunction(()=>!Network.busy,null,{timeout:10000});}
 async function account(p){await p.evaluate(()=>Network.showAccount());await p.waitForSelector('#network-dialog[open] .security-section');}
 async function summary(p,text){await p.locator('summary').filter({hasText:text}).click();}
 async function close(p){await p.click('#network-dialog-close');}
 try{
  await register(a,ua);await register(b,ub);await community(a);
  await a.fill('#org-name','Horyzont '+suffix);await a.fill('#org-tag','H'+suffix.slice(-4));await a.fill('#org-description','Nasze wspólne miejsce w mieście.');await a.click('#org-create-form [type=submit]');await a.waitForSelector('.org-identity');
  await a.selectOption('#org-target',{label:ub});await a.click('#org-invite-form [type=submit]');await community(b);await b.waitForSelector('[data-extra=accept]');await b.click('[data-extra=accept]');await b.waitForSelector('.org-identity');
  assert.equal(await b.locator('.org-members .session-row').count(),2);await refresh(a);
  await chooseChannel(a,'organization');await send(a,'Cześć ekipo! <img src=x onerror=alert(1)>');await chooseChannel(b,'organization');assert.match(await b.locator('#chat-messages').innerText(),/<img src=x/);assert.equal(await b.locator('#chat-messages img').count(),0);
  await chooseChannel(b,'world');assert.doesNotMatch(await b.locator('#chat-messages').innerText(),/Cześć ekipo/);await chooseChannel(b,'organization');
  await send(b,'Wiadomość do sprawdzenia przez moderatora.');await refresh(a);await a.locator('.chat-message').filter({hasText:'Wiadomość do sprawdzenia'}).locator('[data-extra=report]').click();await a.fill('#report-reason','Test naruszenia zasad czatu');await a.click('#chat-report-form [type=submit]');await a.waitForFunction(()=>!document.querySelector('#network-dialog').open);
  await b.locator('.chat-message').filter({hasText:'Cześć ekipo'}).locator('[data-extra=block]').click();await confirm(b);await b.waitForFunction(()=>!/Cześć ekipo/.test(document.querySelector('#chat-messages')?.innerText||''),null,{timeout:10000});assert.doesNotMatch(await b.locator('#chat-messages').innerText(),/Cześć ekipo/);
  await account(b);await summary(b,'Zablokowane kontakty');await b.click('[data-extra=unblock]');await close(b);await refresh(b);assert.match(await b.locator('#chat-messages').innerText(),/Cześć ekipo/);
  await a.click('.org-members [data-extra=transfer]');await confirm(a);await a.waitForFunction(()=>!document.querySelector('[data-extra=transfer]'),null,{timeout:10000});assert.equal(await a.locator('#org-invite-form').count(),1);assert.equal(await a.locator('[data-extra=org-role]').count(),0);await refresh(b);await b.click('.org-members [data-extra=transfer]');await confirm(b);await refresh(a);await a.waitForSelector('#org-invite-form');
  await a.screenshot({path:path.join(__dirname,'community-desktop.png'),fullPage:true});
  for(const width of [320,390,768,1440]){await b.setViewportSize({width,height:950});await b.waitForTimeout(100);assert.equal(await b.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'community overflow '+width);if(width===390)await b.screenshot({path:path.join(__dirname,'community-mobile.png'),fullPage:true});}
  // Operator actions and fixture boosts below are restricted to the disposable QA database.
  execFileSync('python',['manage.py','--db',DB,'grant-admin',ua]);await login(a,ua);
  await a.click('#nav-admin');await a.waitForSelector('[data-extra=reports]');await a.click('[data-extra=reports]');await a.waitForSelector('[data-action=hide_mute]');await a.locator('.moderation-card').filter({hasText:'Test naruszenia zasad czatu'}).locator('[data-action=hide_mute]').click();await a.waitForFunction(()=>document.querySelector('#network-dialog-body').textContent.includes('Rozpatrzone: hide_mute'));await close(a);
  await refresh(b);assert.match(await b.locator('#chat-messages').innerText(),/Wiadomość ukryta/);assert.equal(await b.locator('#chat-form [type=submit]').isDisabled(),true);
  await a.click('[data-extra=backups]');await a.waitForSelector('[data-extra=backup-create]');await a.click('[data-extra=backup-create]');await a.waitForFunction(()=>document.querySelector('.backup-list')?.textContent.includes('Ręczna'));await close(a);
  execFileSync('python',['-c',"import sqlite3,json,sys;c=sqlite3.connect(sys.argv[1]);r=c.execute('SELECT c.id,c.state_json FROM characters c JOIN accounts a ON a.id=c.account_id WHERE a.username=? AND c.world_id=2',(sys.argv[2],)).fetchone();s=json.loads(r[1]);s['xp']=600;s['cash']=15000;c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s),r[0]));c.execute('UPDATE characters SET current_district=2 WHERE id=?',(r[0],));c.commit()",DB,ua]);
  await a.evaluate(()=>Network.refresh());await a.evaluate(()=>GameApp.showView('character'));await a.waitForSelector('[data-item=analyst-band]:not([disabled])');await a.click('[data-item=analyst-band]');await a.waitForTimeout(800);await a.waitForFunction(()=>!Network.busy);assert.ok(!(await a.evaluate(()=>GameApp.state.inventory.includes('analyst-band'))),'7.3 GDD v3.1: stary sklep zamknięty — sety w Sali Klubowej');
  await a.click('#nav-business');await a.click('[data-extra=venture][data-id=studio][data-action=buy_business]');await a.waitForFunction(()=>GameApp.state.ventures.studio&&!Network.busy);await a.click('[data-id=studio][data-action=upgrade]');await a.waitForFunction(()=>GameApp.state.ventures.studio.level===2,{},{timeout:20000});
  execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE worlds SET created_at=created_at-?',(16*86400000,));c.commit()",DB]);  // 0.45: Era III — kampania (D6) i expo (D7) dostępne
  execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute('UPDATE characters SET current_district=6 WHERE world_id=2');c.commit()",DB]);await a.evaluate(()=>Network.refresh());await a.waitForFunction(()=>Network.packet?.travelInfo?.district===6,null,{timeout:15000});  // 0.45: kampania w D6
  await a.click('#nav-contracts');
  assert.equal(await a.locator('[data-contract=campaign]').isEnabled(),true);assert.ok(await a.locator('[data-extra=contract-go][data-d="7"]').count(),'expo: CTA podróży do D7');
  await login(c,ub);await account(b);await summary(b,'Aktywne sesje');await b.fill('#session-password','test');await b.locator('[data-extra=revoke-session][data-id]').click();await c.evaluate(()=>Network.refresh());await c.waitForSelector('#auth-form');
  await summary(b,'Zmień hasło');await b.fill('#old-password','test');await b.fill('#new-password','abcd');await b.fill('#repeat-password','different');await b.click('#password-change-form [type=submit]');await b.waitForSelector('#network-dialog-error');assert.match(await b.locator('#network-dialog-error').innerText(),/nie są takie same/);await b.fill('#repeat-password','abcd');await b.click('#password-change-form [type=submit]');await b.waitForSelector('#auth-form');
  await login(b,ub,'abcd');await account(b);await summary(b,'Aktywne sesje');await b.screenshot({path:path.join(__dirname,'account-security.png'),fullPage:true});await close(b);await community(b);assert.equal(await b.locator('.org-identity').count(),1);
  await b.click('[data-extra=leave]');await confirm(b);await b.waitForFunction(()=>document.querySelector('[data-channel=organization]')?.disabled===true,null,{timeout:10000});assert.equal(await b.locator('[data-channel=organization]').isDisabled(),true);
  assert.deepEqual(errors,[]);console.log('PASS 0.7: stripped headers/cookies; organization create/invite/join/transfer/leave, private channels, escaped UGC, report/block/unblock, admin hide/mute/backups, studio/gear, session revocation and password change; 4 responsive community widths; no JS errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
