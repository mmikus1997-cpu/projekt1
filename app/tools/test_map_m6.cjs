// M6: okolica, usługi, powrót i responsywność — bez zmiany zapisu konta.
const {chromium}=require('playwright');
const assert=require('assert/strict'),fs=require('fs'),path=require('path');
(async()=>{
 const base=process.argv[2]||'http://127.0.0.1:8080';
 const login=await fetch(base+'/api/auth/login',{method:'POST',headers:{'content-type':'application/json','X-City-Preview-Session':'1'},body:JSON.stringify({username:'klub_demo',password:'klub-demo-123'})});
 assert(login.ok);const j=await login.json();const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:900}});const errors=[];
 p.on('pageerror',e=>errors.push(e.message));p.on('console',m=>{if(/overflowed|EXCEPTION CAUGHT/.test(m.text()))errors.push(m.text());});
 await p.goto(base);await p.evaluate(([t,c])=>{localStorage.setItem('flutter.session.token',JSON.stringify(t));localStorage.setItem('flutter.session.csrf',JSON.stringify(c));localStorage.setItem('flutter.session.world','2');},[j.previewSessionToken,j.csrf]);
 await p.reload();await p.waitForTimeout(8000);await p.keyboard.press('Escape');await p.evaluate(()=>document.querySelector('flt-semantics-placeholder')?.click());await p.waitForTimeout(500);
 if(process.env.M6_WORKER_FIXTURE) await p.route('**/api/worlds/2/npcs',async route=>{
  const r=await route.fetch();const data=await r.json();const now=Date.now();
  data.npcs=[{id:99999,name:'Pracownik QA M6',phase:'working',assigned_service_id:'kawiarnia',shiftStartedAt:now-600000,shiftEndsAt:now+600000}];
  await route.fulfill({response:r,json:data});
 });
 const out=path.resolve(__dirname,'../shots');fs.mkdirSync(out,{recursive:true});
 for(const width of [1280,800,400,320]) {
  await p.setViewportSize({width:1280,height:900});await p.waitForTimeout(700);
  await p.getByRole('button',{name:/Centrum/}).first().click();await p.waitForTimeout(1100);
  await p.setViewportSize({width,height:width>=800?900:740});await p.waitForTimeout(900);
  await p.getByRole('button',{name:/Mapa świata/}).waitFor();
  await p.screenshot({path:path.join(out,`m6-region-${width}.jpg`),type:'jpeg',quality:86});
  await p.getByRole('button',{name:/Kawiarnia/}).first().click();await p.waitForTimeout(800);
  assert(await p.getByRole('button',{name:/Wyślij.*NPC/}).count(),'Brak akcji NPC przy usłudze');
  if(process.env.M6_WORKER_FIXTURE) {
   await p.getByRole('button',{name:'Wyślij kolejnego NPC'}).waitFor({timeout:15000});
   assert((await p.content()).includes('Pracownik QA M6'),'Brak danych pracownika w panelu');
  }
  await p.screenshot({path:path.join(out,`m6-service-${width}.jpg`),type:'jpeg',quality:86});
  await p.getByRole('button',{name:/Mapa świata/}).click();await p.waitForTimeout(600);
  assert.equal(await p.getByRole('button',{name:/Mapa świata/}).count(),0,'Powrót nie zamknął okolicy');
 }
 await b.close();assert.equal(errors.length,0,errors.join('\n'));console.log('PASS M6: 1280/800/400/320 px — okolica, panel usługi, przycisk NPC, powrót, bez wyjątków/overflow.');
})().catch(e=>{console.error(e);process.exit(1);});
