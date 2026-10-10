const {chromium}=require('playwright');
const {execFileSync}=require('node:child_process');
const DB=(process.env.TEST_DB||'tests/qa-smoke.sqlite3');
const clickAt=(p,sel)=>p.evaluate(s=>{const el=document.querySelector(s);if(!el)throw Error('brak: '+s);el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));},sel);
(async()=>{
 const b=await chromium.launch();const p=await (await b.newContext({viewport:{width:1360,height:900}})).newPage();
 const errs=[];p.on('pageerror',e=>errs.push(e.message.slice(0,120)));
 const B=process.env.TEST_BASE_URL||'http://127.0.0.1:3240';
 await p.goto(B);await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username','fix451');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
 await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');await p.click('[data-world="2"]');
 await p.fill('#character-nickname','Testers');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
 await p.click('#nav-map');await p.waitForSelector('#map-viewport');
 // 1) ZOOM Z CENTRUM (kursor daleko od środka)
 const t0=await p.evaluate(()=>document.getElementById('map-world').style.transform);
 await p.mouse.move(400,300);
 await p.mouse.wheel(0,-240);
 const t1=await p.evaluate(()=>document.getElementById('map-world').style.transform);
 console.log('zoom:',t0,'->',t1);
 // 2) QUICK POD KURSOREM
 const pin=await p.locator('[data-map-cpin=inventory]').evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};});
 await p.mouse.move(pin.x,pin.y);await p.waitForTimeout(350);
 const q=await p.locator('#map-quick').evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.left,y:r.top,hidden:el.hidden,txt:el.innerText.slice(0,90)};});
 console.log('quick przy kursorze?',!q.hidden&&Math.abs((q.x-16)-pin.x)<60&&Math.abs((q.y-18)-pin.y)<60,'| pozycja:',Math.round(q.x),Math.round(q.y),'vs pin',Math.round(pin.x),Math.round(pin.y));
 console.log('quick treść:',q.txt.replace(/\n/g,' / '));
 // 3) MGŁA — era + dni
 const fog=await p.locator('.map-place.fog').first().evaluate(el=>{const r=el.getBoundingClientRect();return {x:r.left+r.width/2,y:r.top+r.height/2};});
 await p.mouse.move(fog.x,fog.y);await p.waitForTimeout(350);
 console.log('quick mgła:',(await p.locator('#map-quick').innerText()).slice(0,130).replace(/\n/g,' / '));
 // 4) dialog zablokowanej dzielnicy (klik w kafelek D4)
 await p.mouse.move(10,10);
 await clickAt(p,'.map-district[data-map-d="4"] .map-d-num');
 await p.waitForFunction(()=>document.getElementById('network-dialog').open);
 console.log('lock-D4:',(await p.locator('#network-dialog').innerText()).slice(0,150).replace(/\n/g,' '));
 await clickAt(p,'#network-dialog [onclick]');
 // 5) VIP speedup: seed VIP + podróż -> Przyspiesz
 execFileSync('python',['-c',"import sqlite3,json;c=sqlite3.connect('"+DB+"');r=c.execute(\"SELECT state_json FROM characters WHERE nickname='Testers'\").fetchone()[0];st=json.loads(r);st['vipUntil']=4102444800000;c.execute(\"UPDATE characters SET state_json=? WHERE nickname='Testers'\",(json.dumps(st),));c.commit()"]);
 await p.evaluate(()=>Network.refresh());await p.waitForFunction(()=>!Network.busy);
 await p.evaluate(async()=>{await Network.api('/worlds/2/travel','POST',{target_district:3,mode:'bus'});});
 await p.waitForFunction(()=>Network.packet&&Network.packet.travelInfo&&Network.packet.travelInfo.travel,null,{timeout:15000});
 await clickAt(p,'[data-extra=travel-speedup]');
 await p.waitForTimeout(1200);
 console.log('po speedup:',await p.evaluate(()=>{const t=document.querySelector('.toast');return t?t.innerText.slice(0,90):'(brak toastu)';}),'| err:',errs.length?errs.join('|'):'0');
 await b.close();
})().catch(e=>{console.error('FATAL:',e.message.slice(0,220));process.exit(1)});
