const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3232';
const DB=process.env.TEST_DB||'tests/qa-season.sqlite3';
if(!DB.includes('qa'))throw Error('Use a disposable QA database, never the main database.');
(async()=>{
 const browser=await chromium.launch({headless:true}),errors=[];
 const context=await browser.newContext({viewport:{width:1280,height:900}});
 const p=await context.newPage();p.on('pageerror',e=>errors.push(e.stack));
 try{
  await p.goto(BASE);await p.click('[data-auth-mode=register]');
  await p.fill('#auth-username','sezon_ui');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
  await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');
  // Karta świata: kalendarz Ery + sezon
  const card=p.locator('.world-card').first();
  await card.hover();
  await card.locator('.era-line').first().waitFor();
  assert.match(await card.locator('.era-line').first().innerText(),/Era 1\/4 · Czas Pionierów · dzień 1\/28/,'kalendarz ery na karcie');
  assert.match(await card.locator('.era-line').first().innerText(),/następna: Era 2 .* za 7 dni/);
  assert.match(await card.locator('.era-season').innerText(),/Sezon \d+ kończy się za \d+ dni/,'info sezonowe na karcie');
  // W grze: chip ery z dopiskiem sezonu
  await p.click('[data-world="2"]');await p.fill('#character-nickname','Sezon UI');
  if(await p.locator('#test-consent').count())await p.check('#test-consent');
  await p.click('#character-form [type=submit]');
  await p.waitForSelector('[data-online=dismiss-tutorial]');await p.click('[data-online=dismiss-tutorial]');await p.waitForFunction(()=>!Network.busy);
  await p.waitForSelector('.era-chip');
  assert.match(await p.locator('.era-hint').innerText(),/Sezon \d+: \d+ dni do podsumowania/,'sezon w chipie ery');
  const era=await p.evaluate(()=>Network.packet.era);
  assert.equal(era.next.n,2);assert.equal(era.next.inDays,7);
  assert.ok(era.season.n>=1&&era.season.daysLeft>0);
  assert.equal(errors.length,0,'no JS errors: '+errors.join(' | '));
  console.log('PASS sezon UI: kalendarz ery na karcie świata (Era 1/4, następna za 7 dni), info sezonowe, chip z licznikiem podsumowania, payload era.next/season; 0 błędów JS');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1);});
