/* 0.57.0 „Sojusze”: panel budynków sojuszu w Społeczności, budowa z funduszu (lider),
   poziomy 1→3 i MAKS, przycisk zablokowany przy pustym funduszu, 0 błędów JS. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const sql=q=>execFileSync('python',['-c',"import sqlite3,sys;c=sqlite3.connect(sys.argv[1]);c.execute(sys.argv[2]);c.commit()",process.env.TEST_DB,q]);
(async()=>{
 const b=await chromium.launch({headless:true});
 const p=await b.newPage({viewport:{width:1280,height:900}});
 const errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(process.env.TEST_BASE_URL);
 const uid='ally_'+Date.now().toString(36);
 await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username',uid);await p.fill('#auth-password','test-password-long-123');await p.fill('#auth-confirm','test-password-long-123');
 await p.check('#age-consent');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');
 await p.click('[data-world="1"]');
 await p.fill('#character-nickname','Sojusznik');if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');
 await p.waitForFunction(()=>Network.world?.id===1);
 await p.waitForSelector('[data-online=dismiss-tutorial]',{timeout:6000}).then(()=>p.click('[data-online=dismiss-tutorial]')).catch(()=>{});
 await p.evaluate(()=>Network.api('/worlds/1/organizations','POST',{name:'Sojusz QA',tag:'SQA',description:''}));
 // 1) Panel: 3 budynki, poziom 0, przyciski zablokowane przy pustym funduszu
 await p.evaluate(()=>Extras.showCommunity());
 await p.waitForSelector('.ally-panel .ally-card',{timeout:15000});
 assert.deepEqual(await p.$$eval('.ally-card',x=>x.map(e=>e.dataset.ally)),['fast_build','cheap_repair','freedom'],'3 budynki sojuszu');
 assert.match(await p.locator('.ally-panel').innerText(),/Wolność/,'nazwa Wolność');
 assert.ok(await p.locator('[data-extra=ally-build][data-building=freedom]').isDisabled(),'zablokowany bez funduszu');
 // 2) Fundusz 17000 → Wolność do MAKS przez UI
 sql("UPDATE organizations SET fund=17000 WHERE tag='SQA'");
 await p.evaluate(()=>Extras.showCommunity());
 for(const lv of [1,2,3]){
  await p.waitForSelector('[data-extra=ally-build][data-building=freedom]:not([disabled])');
  await p.click('[data-extra=ally-build][data-building=freedom]');
  await p.waitForFunction(l=>document.querySelector('.ally-card[data-ally=freedom] .ally-lv')?.textContent.includes('POZIOM '+l+'/3'),lv,{timeout:10000});
 }
 assert.match(await p.locator('.ally-card[data-ally=freedom]').innerText(),/MAKS/,'MAKS po 3 poziomie');
 assert.match(await p.locator('.ally-card[data-ally=freedom] .ally-lv').innerText(),/−30%/,'premia −30%');
 assert.ok(await p.locator('.ally-card[data-ally=freedom].on').count(),'karta aktywna');
 assert.match(await p.locator('.ally-panel .eyebrow').innerText(),/FUNDUSZ\s*\$?0|FUNDUSZ 0/,'fundusz wydany do zera');
 assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
 console.log('PASS alliance: 3 budynki sojuszu, blokada bez funduszu, Wolność 1→3 + MAKS, −30%, 0 błędów JS');
 await b.close();
})().catch(e=>{console.error('ERR',e.message);process.exit(1)});
