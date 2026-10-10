/* 0.58.0 „Eventy czasowe”: baner w Mojej dzielnicy — nazwa/opis z pakietu, odliczanie, zapowiedź następnego. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
(async()=>{
 const b=await chromium.launch({headless:true});
 const p=await b.newPage({viewport:{width:1280,height:900}});
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(process.env.TEST_BASE_URL);
 const uid='tev_'+Date.now().toString(36);
 await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username',uid);await p.fill('#auth-password','test-password-long-123');await p.fill('#auth-confirm','test-password-long-123');
 await p.check('#age-consent');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');
 await p.click('[data-world="1"]');
 await p.fill('#character-nickname','Eventnik');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');
 await p.waitForFunction(()=>Network.world?.id===1);
 await p.waitForSelector('[data-online=dismiss-tutorial]',{timeout:6000}).then(()=>p.click('[data-online=dismiss-tutorial]')).catch(()=>{});
 await p.click('#nav-city');
 await p.waitForSelector('.tev-panel',{timeout:15000});
 const ev=await p.evaluate(()=>Network.packet.timedEvent);
 assert.ok(['gold_rush','bus_free','study','service_rush'].includes(ev.id),'znany event');
 assert.equal(await p.locator('.tev-panel').getAttribute('data-tev'),ev.id,'baner = event z pakietu');
 const txt=await p.locator('.tev-panel').innerText();
 assert.ok(txt.includes(ev.name)&&txt.includes(ev.desc),'nazwa+opis');
 assert.ok(txt.includes('Następny: '+ev.next.icon+' '+ev.next.name),'zapowiedź następnego');
 await p.waitForFunction(()=>/\d/.test(document.querySelector('.tev-panel [data-countdown]').textContent),null,{timeout:5000});
 // licznik = timerText(end-now) (powyżej 1 h format „Xh MMm” bez sekund — porównujemy z wyliczeniem)
 assert.ok(await p.evaluate(()=>{const el=document.querySelector('.tev-panel [data-countdown]'),exp=[0,1500].map(d=>GameApp.timerText?GameApp.timerText(+el.dataset.countdown-Network.now()+d):null);return exp[0]===null||exp.includes(el.textContent)||/^\d+h \d\dm$|^\d\d:\d\d$/.test(el.textContent);}),'odliczanie zgodne z czasem');
 assert.equal(await p.locator('.tev-panel [data-countdown]').getAttribute('data-countdown'),String(ev.end),'licznik do końca okna');
 assert.ok(await p.locator('.bld-card[data-bld]').count()===6,'karty budynków nadal na miejscu');
 assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
 console.log('PASS timedevent: baner eventu w dzielnicy, opis, następny, odliczanie, 0 błędów JS');
 await b.close();
})().catch(e=>{console.error('ERR',e.message);process.exit(1)});
