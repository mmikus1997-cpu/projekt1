const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3236';
const DB=process.env.TEST_DB||'tests/qa-map.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
async function apiRegister(nick){
 const un='sonda_'+Math.random().toString(36).slice(2,7);
 const r=await fetch(BASE+'/api/auth/register',{method:'POST',headers:{'content-type':'application/json','x-city-preview-session':'1'},body:JSON.stringify({username:un,password:'test',consent:true,preview_session:true})});
 if(!r.ok)throw Error('register: '+r.status+' '+await r.text());
 const d=await r.json();
 const c=await fetch(BASE+'/api/worlds/2/character',{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer '+d.previewSessionToken,'x-csrf-token':d.csrf},body:JSON.stringify({nickname:nick,accept_test_reset:true,class_type:null})});
 if(!c.ok)throw Error('character: '+c.status+' '+await c.text());
 return {username:un,token:d.previewSessionToken,csrf:d.csrf};
}
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
  // atomiczny klik: query + dispatch w jednym zadaniu JS (poll-render nie zdąży odpiąć węzła)
  const clickAt=sel=>p.evaluate(s=>{const el=document.querySelector(s);if(!el)throw Error('brak elementu: '+s);el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));},sel);
  const armDlgLog=()=>p.evaluate(()=>{const d=document.getElementById('network-dialog');window.__dlgLog=[];window.__t0=Date.now();new MutationObserver(()=>{window.__dlgLog.push([Date.now()-window.__t0,d.open]);}).observe(d,{attributes:true,attributeFilter:['open']});});
  const dlgLog=()=>p.evaluate(()=>({log:window.__dlgLog,open:document.getElementById('network-dialog').open,suppress:typeof mapSuppress!=='undefined'?mapSuppress:'?',view:typeof GameApp!=='undefined'?GameApp.view:'?'}));
 try{
  const sonda=await apiRegister('Sonda');  // drugi gracz online w dzielnicy 1
  // 0.38: admin + event miejski (XP całego miasta → odznaka 📣 na Centrum mapy)
  const adm=await apiRegister('Prefekt');
  const {execFileSync}=require('node:child_process');
  execFileSync('python',['manage.py','--db',DB,'grant-admin',adm.username]);
  const lg=await (await fetch(BASE+'/api/auth/login',{method:'POST',headers:{'content-type':'application/json','x-city-preview-session':'1'},body:JSON.stringify({username:adm.username,password:'test',preview_session:true})})).json();
  if(!lg.previewSessionToken)throw Error('admin login bez tokenu');
  const ev=await fetch(BASE+'/api/admin/events',{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer '+lg.previewSessionToken,'x-csrf-token':lg.csrf},body:JSON.stringify({world_id:2,name:'Noc XP w Centrum',description:'Wspólny cel miasta widoczny z mapy',kind:'xp',district:'',target:500,hours:48})});
  if(!ev.ok)throw Error('admin/events: '+ev.status+' '+await ev.text());
  await p.goto(BASE);await armDlgLog();await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','mapa_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
  await p.fill('#character-nickname','Kartograf');
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');
  await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy,null,{timeout:30000,polling:200});
  // Zakładka Mapa: 0.54.0 — (2.1d) 5 miast + 3 dzielnice zawsze otwarte, Era I blokuje miasta 4–6
  // 0.38 Mini-mapa w hubie: Twoja dzielnica + klik → wielka mapa
  await p.waitForSelector('.mini-map-panel');
  assert.equal(await p.locator('.mm-dot.me').count(),1,'mini-mapa: pozycja 📍');
  assert.match(await p.locator('.mini-map-cta').innerText(),/Nadmorskie/);
  await p.click('.mini-map-cta');
  await p.waitForFunction(()=>GameApp.view==='map',null,{timeout:20000,polling:100});
  await p.click('#nav-map');await p.waitForSelector('.bigmap-viewport');
  assert.equal(await p.locator('.map-district').count(),8,'8 dzielnic na wielkiej mapie');
  assert.equal(await p.locator('.map-district.locked').count(),3,'Era I: 3 zamknięte miasta (4–6 — 2/7/8 zawsze otwarte)');
  assert.equal(await p.locator('.map-district.here').count(),1,'marker Jesteś tutaj');
  assert.match(await p.locator('.map-district.here').innerText(),/Nadmorskie/);
  // 2.1d GDD v3.1: brak UI surowców na mapie
  assert.equal(await p.locator('.map-mat-panel').count(),0,'panele surowców usunięte');
  assert.ok(!/surowc/i.test(await p.locator('#view-map, .game-view:visible').first().innerText()),'brak tekstów o surowcach');
  assert.ok(await p.locator('.map-place').count()>=10,'przedsiębiorstwa/lokale na mapie');
  assert.ok(await p.locator('.map-place.owned').count()>=1,'⭐ własne przedsiębiorstwo (City Courier)');
  // 0.37 Mgła wojny er: zamknięte dzielnice jako place budowy, detale ukryte
  assert.equal(await p.locator('.map-district.fog').count(),3,'mgła na 3 zamkniętych miastach');
  assert.equal(await p.locator('.map-place.fog').count(),6,'place budowy w zamkniętych miastach (d4:1, d5:2, d6:3)');
  assert.match(await p.locator('.map-district.fog').first().innerText(),/Plac budowy/);
  // 0.38 Eventy i sezon na mapie
  await p.waitForSelector('.map-badge.event',{timeout:20000});
  assert.equal(await p.locator('.map-badge.event').count(),1,'📣 na Centrum (cel ogólnomiejski)');
  assert.equal(await p.locator('.map-badge.season').count(),1,'🏁 sezon na Centrum');
  await clickAt('.map-badge.season');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Sezon rankingowy 1/);
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  await clickAt('.map-badge.event');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Noc XP w Centrum/);
  assert.match(await p.locator('#network-dialog').innerText(),/XP całego miasta/);
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  // 0.37 Presence: dymki graczy online na ich dzielnicach
  await p.waitForSelector('.map-player',{timeout:15000});
  assert.ok((await p.locator('.map-player').first().innerText()).includes('Sonda'),'dymek gracza online Sonda');
  // 0.38 DM z mapy: dymek → dialog → wysyłka → odpowiedź przez poll
  const roster=await (await fetch(BASE+'/api/worlds/2/players',{headers:{'authorization':'Bearer '+sonda.token,'x-csrf-token':sonda.csrf}})).json();
  const kartId=roster.players.find(x=>x.nickname==='Kartograf').id;
  await clickAt('.map-player[data-map-player]');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/DM · Sonda/);
  await p.fill('#dm-input','Hej z wielkiej mapy!');
  await p.click('[data-dm-send]');
  await p.waitForFunction(()=>document.getElementById('dm-thread')?.innerText.includes('Hej z wielkiej mapy!'),null,{timeout:15000,polling:200});
  const rep=await fetch(BASE+'/api/worlds/2/dm/'+kartId,{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer '+sonda.token,'x-csrf-token':sonda.csrf},body:JSON.stringify({text:'Cześć! Widzę Twój marker.'})});
  if(!rep.ok)throw Error('dm reply: '+rep.status+' '+await rep.text());
  await p.waitForFunction(()=>document.getElementById('dm-thread')?.innerText.includes('Twój marker'),null,{timeout:15000,polling:500});
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  const chipTexts=await p.locator('.map-players').allInnerTexts();
  assert.ok(!chipTexts.join('|').includes('Kartograf'),'własny marker to 📍, nie dymek');
  // 0.37 Klikalne budynki: Urząd Miejski → widok city
  await clickAt('.map-district[data-map-d="1"] [data-map-place="1"]');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Urząd Miejski/);
  await p.click('[data-map-go=city]');
  await p.waitForFunction(()=>GameApp.view==='city',null,{timeout:20000,polling:100});
  // Corner Café (niekupione) → Przedsiębiorstwa
  await p.click('#nav-map');await p.waitForSelector('.bigmap-viewport');await p.waitForSelector('.map-player');
  await clickAt('.map-district[data-map-d="3"] [data-map-place="4"]');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Lokuj firmę|Jedź i wejdź/);
  await p.click('[data-map-go=business]');
  await p.waitForFunction(()=>GameApp.view==='business',null,{timeout:20000,polling:100});
  for(let i=0;i<60;i++){await p.waitForTimeout(1000);try{await p.evaluate(()=>Network.refresh());}catch(e){}if(await p.evaluate(()=>Network.packet?.travelInfo?.district===3&&!Network.packet?.travelInfo?.travel))break;}  // 0.45: dojazd do D3
  await p.click('#nav-map');await p.waitForSelector('.bigmap-viewport');await p.waitForSelector('.map-player');
  // 0.54.0 Brama Lochu w d8 (Lasy Wschodnie — zawsze otwarte) → realne okno; bramka lochu: Era III + poz. 3 (serwer)
  await clickAt('.map-district[data-map-d="8"] .map-place');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Loch/);
  assert.match(await p.locator('#network-dialog').innerText(),/Wyprawa/);
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  // 0.40 Wizytówka: City Courier (miejsce 2) → właściciele online (Sonda) + DM
  await clickAt('.map-district[data-map-d="2"] [data-map-place="2"]');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  const bizTxt=await p.locator('#network-dialog').innerText();
  assert.match(bizTxt,/Prowadzą tu online/);
  assert.match(bizTxt,/Sonda/);
  assert.match(bizTxt,/Wyślij DM/);
  await clickAt('#network-dialog [onclick]');
  await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  // 0.39 Kafelki hubów: Biuro Zleceń → Kontrakty, Arena Pojedynków → PvP
  await clickAt('.map-district[data-map-d="3"] [data-map-place="12"]');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Biuro Zleceń/);
  await p.click('[data-map-go=contracts]');
  await p.waitForFunction(()=>GameApp.view==='contracts',null,{timeout:20000,polling:100});
  await p.click('#nav-map');await p.waitForSelector('.bigmap-viewport');
  // Arena Pojedynków leży w zablokowanej d6 → mgła bez kliku, klik w dzielnicę = bramka Ery III
  await clickAt('.map-district[data-map-d="6"] .map-place');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Erze 3/);
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  // ścieżka data-map-go=pvp: sąd rozpatruje programowo (tile w otwartej dzielnicy pojawi się w Erze III)
  await p.evaluate(()=>{const b=document.createElement('button');b.setAttribute('data-map-go','pvp');b.style.display='none';document.querySelector('.content').appendChild(b);b.click();b.remove();});
  await p.waitForFunction(()=>Network.panel==='pvp',null,{timeout:20000,polling:100});
  await p.click('#nav-map');await p.waitForSelector('.bigmap-viewport');
  // 0.39 Dźwięki podróży: toggle zapisuje preferencję
  await clickAt('[data-map-sound]');
  assert.equal(await p.evaluate(()=>localStorage.getItem('ce-sound')),'0','toggle wyłącza dźwięki');
  await clickAt('[data-map-sound]');
  assert.equal(await p.evaluate(()=>localStorage.getItem('ce-sound')),'1','toggle włącza dźwięki');
  // Pan myszą przesuwa świat
  const vp=await p.locator('#map-viewport').boundingBox();
  const t0=await p.locator('#map-world').evaluate(el=>el.style.transform);
  await p.mouse.move(vp.x+vp.width/2,vp.y+vp.height/2);
  await p.mouse.down();await p.mouse.move(vp.x+vp.width/2+140,vp.y+vp.height/2+80,{steps:6});await p.mouse.up();
  const t1=await p.locator('#map-world').evaluate(el=>el.style.transform);
  assert.notEqual(t0,t1,'pan zmienia transform');
  // Przesunięcie nie może kliknąć: klik po dragu nie otwiera popupa
  assert.equal(await p.evaluate(()=>document.getElementById('network-dialog').open),false,'drag bez kliknięcia');
  // Klik zamkniętej dzielnicy (Port) → bramka Ery II
  await clickAt('.map-district[data-map-d="4"]');
  try{await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:10000,polling:100});}
  catch(e){console.error('DLGDBG d4:',JSON.stringify(await dlgLog()));await clickAt('.map-district[data-map-d="4"]');
   await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:10000,polling:100});}
  assert.match(await p.locator('#network-dialog').innerText(),/Erze 2 \(Rozwój Przemysłu\)/);
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  // Klik otwartej dzielnicy (Przemysłowe) → popup z podróżą → Bus
  await clickAt('.map-district[data-map-d="2"]');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/Bus · 20 \$/);
  await p.click('[data-map-travel=bus]');
  await p.waitForFunction(()=>Network.packet?.travelInfo?.travel,null,{timeout:15000});
  // 0.37 Żywa mapa: started w payloa, trasa po szynach, marker w ruchu
  assert.ok(await p.evaluate(()=>Network.packet?.travelInfo?.travel?.started>0),'travel.started w payload');
  await p.waitForSelector('.map-route',{timeout:15000});
  await p.waitForSelector('#map-traveler',{timeout:15000});
  const leftA=await p.locator('#map-traveler').evaluate(el=>el.style.left);
  await p.waitForTimeout(1200);
  const leftB=await p.locator('#map-traveler').evaluate(el=>el.style.left);
  assert.notEqual(leftA,leftB,'marker jedzie po trasie (animacja po szynach)');
  // 0.40 Kongestia: Sonda jedzie autostopem (API) → złota szyna z szerokością
  const stv=await fetch(BASE+'/api/worlds/2/travel',{method:'POST',headers:{'content-type':'application/json','authorization':'Bearer '+sonda.token,'x-csrf-token':sonda.csrf},body:JSON.stringify({target_district:3,mode:'hitchhike'})});
  if(!stv.ok)throw Error('sonda travel: '+stv.status+' '+await stv.text());
  await p.evaluate(()=>GameApp.mapLoadPlayers());
  await p.waitForSelector('.map-rails line[stroke-width]',{timeout:20000,state:'attached'});
  assert.ok(await p.locator('.map-rails line[stroke="#d4af70"]').count()>=1,'szyna z ruchem jest złota');
  assert.match(await p.locator('#travel-overlay').innerText(),/Przemysłowe/,'overlay podróży po mapie');
  await p.waitForFunction(()=>GameApp.view==='map');
  assert.equal(await p.locator('.map-district.goal').count(),1,'dzielnica-cel oznaczona');
  // 0.39 Skrzynka DM w Społeczności: wątek z Sondą, klik → dialog DM (overlay podróży przykrywa nav → dispatch)
  await clickAt('#nav-community');
  await p.waitForSelector('.dm-inbox',{timeout:20000});
  await p.waitForFunction(()=>document.querySelector('.dm-row')?.innerText.includes('Sonda'),null,{timeout:20000,polling:200});
  await clickAt('.dm-row');
  await p.waitForFunction(()=>document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  assert.match(await p.locator('#network-dialog').innerText(),/DM · Sonda/);
  await clickAt('#network-dialog [onclick]');await p.waitForFunction(()=>!document.getElementById('network-dialog').open,null,{timeout:20000,polling:100});
  // 0.40 Sesja foto: canvas → PNG (bez uploadu)
  await clickAt('[data-map-photo]');
  await p.waitForFunction(()=>!!window.__lastPhoto,null,{timeout:15000,polling:200});
  const photo=await p.evaluate(()=>window.__lastPhoto);
  assert.ok(photo.startsWith('data:image/png')&&photo.length>15000,'PNG mapy wygenerowany lokalnie');
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS mapa 0.40: mini-mapa w hubie, mgła wojny er, event/sezon, presence, DM z mapy i skrzynka, wizytówki firm online (⭐×N + DM), kongestia na szynach (autostop Sondy → złota linia), kafelki hubów, toggle dźwięków, sesja foto PNG, pan, bramka Ery, podróż z trasą i markerem; 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
