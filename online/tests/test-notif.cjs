/* 0.59.0 „Chmurka powiadomień”: dzwonek z licznikiem, wyskakujący dymek przy nowej gotowej rzeczy,
   dymek z sekcjami Gotowe/Zdarzenia, przejście do budynku, oznaczanie przeczytanych. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const py=(code,...a)=>execFileSync('python3',['-c',code,process.env.TEST_DB,...a]).toString();
(async()=>{
 const b=await chromium.launch({headless:true});
 const p=await b.newPage({viewport:{width:1280,height:900}});
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(process.env.TEST_BASE_URL);
 const uid='notif_'+Date.now().toString(36);
 await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username',uid);await p.fill('#auth-password','test-password-long-123');await p.fill('#auth-confirm','test-password-long-123');
 await p.check('#age-consent');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');
 await p.click('[data-world="1"]');
 await p.fill('#character-nickname','Dzwonek');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');
 await p.waitForFunction(()=>Network.world?.id===1);
 await p.waitForSelector('[data-online=dismiss-tutorial]',{timeout:6000}).then(()=>p.click('[data-online=dismiss-tutorial]')).catch(()=>{});
 // 1) Dzwonek widoczny, bez licznika
 await p.waitForSelector('#notif-bell:not([hidden]) .notif-btn',{timeout:10000});
 assert.equal(await p.locator('#notif-bell .notif-count:visible').count(),0,'start: brak licznika');
 // 2) Trasa kończy się za 4 s → wyskakujący dymek + licznik 1
 const end=await p.evaluate(()=>Math.round(Network.now())+4000);
 py("import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);r=c.execute(\"SELECT id,state_json FROM characters WHERE nickname='Dzwonek'\").fetchone();st=json.loads(r[1]);st['garage']=['rower'];st['npcRoutes']={'runs':[{'route':'courier','vehicle':'rower','start':1,'end':int(sys.argv[2])}],'done':0,'cash':0,'xp':0};c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(st),r[0]));c.commit()",String(end));
 await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
 await p.waitForSelector('#notif-bell .notif-pop:not([hidden])',{timeout:12000});
 assert.match(await p.locator('#notif-bell .notif-pop').innerText(),/Trasy NPC gotowe/,'dymek o trasach');
 assert.equal(await p.locator('#notif-bell .notif-count').innerText(),'1','licznik 1');
 // 3) Zdarzenie serwera (nieprzeczytane) → licznik 2, tekst w chmurce
 py("import sqlite3,sys,json;c=sqlite3.connect(sys.argv[1]);cid=c.execute(\"SELECT id FROM characters WHERE nickname='Dzwonek'\").fetchone()[0];c.execute('INSERT INTO game_events(world_id,character_id,kind,payload,created_at) VALUES(1,?,?,?,1)',(cid,'org.building',json.dumps({'tag':'SQA','org':'Sojusz','building':'Wolność','level':2})));c.commit()");
 await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
 await p.waitForFunction(()=>document.querySelector('#notif-bell .notif-count').textContent==='2',null,{timeout:5000});
 await p.click('#notif-bell .notif-btn');
 await p.waitForSelector('#notif-bell .notif-cloud:not([hidden])');
 const cloud=await p.locator('#notif-bell .notif-cloud').innerText();
 assert.match(cloud,/GOTOWE DO ODBIORU/);assert.match(cloud,/ZDARZENIA/);
 assert.match(cloud,/Sojusz \[SQA\] rozbudował Wolność do poziomu 2/,'tekst zdarzenia');
 assert.equal(await p.locator('#notif-bell .notif-item.unread').count(),1,'1 nieprzeczytane');
 // 4) Oznacz przeczytane → licznik 1
 await p.click('#notif-bell [data-notif-read]');
 await p.waitForFunction(()=>document.querySelector('#notif-bell .notif-count').textContent==='1',null,{timeout:5000});
 assert.equal(await p.locator('#notif-bell .notif-item.unread').count(),0,'brak nieprzeczytanych');
 // 5) Klik „Trasy NPC gotowe” → Garaż, chmurka zamknięta
 await p.click('#notif-bell [data-notif-go=garage]');
 await p.waitForFunction(()=>GameApp.view==='garage');
 assert.ok(await p.locator('#notif-bell .notif-cloud').isHidden(),'chmurka zamknięta');
 assert.ok(await p.locator('[data-game=route-claim]').count(),'przycisk odbioru tras w Garażu');
 // 6) Odbiór → licznik znika; klik poza zamyka
 await p.click('[data-game=route-claim]');await p.waitForFunction(()=>!Network.busy);
 await p.waitForFunction(()=>document.querySelector('#notif-bell .notif-count').hidden,null,{timeout:5000});
 await p.click('#notif-bell .notif-btn');await p.waitForSelector('#notif-bell .notif-cloud:not([hidden])');
 await p.mouse.click(600,300);
 assert.ok(await p.locator('#notif-bell .notif-cloud').isHidden(),'klik poza zamyka');
 assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
 console.log('PASS notif: dzwonek, dymek przy gotowej trasie, zdarzenia + przeczytane, przejście do Garażu, 0 błędów JS');
 await b.close();
})().catch(e=>{console.error('ERR',e.message);process.exit(1)});
