const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const BASE=process.env.TEST_BASE_URL||'http://127.0.0.1:3001';
(async()=>{
 // The routed wrapper has no real DNS address; bypass only the local-network check
 // so it can load the loopback test server. Cookie transport and all extra request headers remain explicitly disabled.
 const browser=await chromium.launch({headless:true,args:['--disable-features=LocalNetworkAccessChecks']});
 const errors=[];const context=await browser.newContext({viewport:{width:1360,height:1000}});
 // A separate-origin parent plus a cookie-free fetch models restricted embedded previews.
 await context.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};});
 await context.route('http://localhost:3001/__qa_wrapper',route=>route.fulfill({contentType:'text/html',body:`<!doctype html><html><body style="margin:0"><iframe id="game" src="${BASE}" sandbox="allow-scripts allow-same-origin allow-forms allow-modals allow-downloads" style="border:0;width:100%;height:100vh"></iframe></body></html>`}));
 const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
 const username='qa_frame_'+Date.now().toString(36),password='abcd';
 const frame=()=>page.frames().find(f=>f.url().startsWith(BASE));
 const ui=page.frameLocator('#game');
 async function login(pass=password){await ui.locator('#auth-username').fill(username);await ui.locator('#auth-password').fill(pass);await ui.locator('#auth-form [type=submit]').click();}
 try{
  await page.goto('http://localhost:3001/__qa_wrapper');await ui.locator('#auth-form').waitFor();
  await ui.locator('[data-auth-mode=register]').click();
  assert.equal(await ui.locator('#auth-password').getAttribute('minlength'),'4');
  assert.equal(await ui.locator('#auth-confirm').getAttribute('minlength'),'4');
  await ui.locator('#auth-username').fill(username);await ui.locator('#auth-password').fill(password);await ui.locator('#auth-confirm').fill(password);await ui.locator('#age-consent').check();await ui.locator('#auth-form [type=submit]').click();
  await ui.locator('.world-grid').waitFor();
  assert.equal(await frame().evaluate(()=>Network.user.username),username);
  assert.equal(await frame().evaluate(()=>document.cookie),'');
  assert.equal(await frame().evaluate(()=>!!sessionStorage.getItem('cityEmpirePreviewSessionV1')),true);
  assert.equal(await frame().evaluate(()=>Object.keys(localStorage).some(k=>/PreviewSession/.test(k))),false);
  await ui.locator('[data-world="2"]').click();await ui.locator('#character-nickname').fill('Test logowania');await ui.locator('#test-consent').check();await ui.locator('#character-form [type=submit]').click();
  await ui.locator('[data-online=dismiss-tutorial]').click();await frame().waitForFunction(()=>!Network.busy&&Network.world?.id===2);
  await page.reload();await ui.locator('#view-city').waitFor();await frame().waitForFunction(()=>Network.character?.nickname==='Test logowania'&&Network.world?.id===2);
  await ui.locator('[data-online=brief-close]').click({timeout:3000}).catch(()=>{});
  assert.equal(await frame().evaluate(()=>GameApp.state.cash),3000);
  const oldToken=await frame().evaluate(()=>sessionStorage.getItem('cityEmpirePreviewSessionV1'));
  await ui.locator('#game-settings-btn').click();await ui.locator('[data-online=logout]').click();await ui.locator('#auth-form').waitFor();
  assert.equal(await frame().evaluate(()=>sessionStorage.getItem('cityEmpirePreviewSessionV1')),null);
  const status=await frame().evaluate(async token=>(await fetch('/api/preview/request',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({session:token,method:'GET',path:'/me'})})).status,oldToken);assert.equal(status,401);
  await login('nope');await frame().waitForFunction(()=>document.querySelector('#auth-error')?.textContent.includes('Nieprawidłowy'));
  await login();await ui.locator('.world-grid').waitFor();await ui.locator('[data-world="2"]').click();await frame().waitForFunction(()=>Network.character?.nickname==='Test logowania');
  await ui.locator('[data-online=brief-close]').click({timeout:3000}).catch(()=>{});

  await frame().evaluate(async()=>{try{await Network.api('/worlds/2/travel','POST',{target_district:3,mode:'bus'});}catch(e){}});  // 0.45: inwentaryzacja w Centrum — najpierw dojazd
  for(let i=0;i<45;i++){await new Promise(r=>setTimeout(r,1000));try{await frame().evaluate(()=>Network.refresh());}catch(e){}if(await frame().evaluate(()=>Network.packet?.travelInfo?.district===3&&!Network.packet?.travelInfo?.travel))break;}
  await ui.locator('#nav-contracts').click();await ui.locator('[data-contract=inventory]').click();await frame().waitForFunction(()=>GameApp.state.contracts.length===1&&!Network.busy);
  // Delete only the disposable QA account through the authenticated API.
  await frame().evaluate(pass=>Network.api('/account/delete','POST',{password:pass}),password);
  await context.close();
  const memoryContext=await browser.newContext();
  await memoryContext.addInitScript(()=>{const original=window.fetch;window.fetch=(url,options={})=>{const headers=new Headers(options.headers);const keep={};if(headers.has('Content-Type'))keep['Content-Type']=headers.get('Content-Type');return original(url,{...options,headers:keep,credentials:'omit'});};for(const method of ['getItem','setItem','removeItem'])Storage.prototype[method]=()=>{throw new DOMException('Storage blocked','SecurityError');};});
  const memoryPage=await memoryContext.newPage();memoryPage.on('pageerror',e=>errors.push(e.message));
  await memoryPage.goto(BASE);await memoryPage.click('[data-auth-mode=register]');
  await memoryPage.fill('#auth-username','qa_memory_'+Date.now().toString(36));await memoryPage.fill('#auth-password',password);await memoryPage.fill('#auth-confirm',password);await memoryPage.check('#age-consent');await memoryPage.click('#auth-form [type=submit]');await memoryPage.waitForSelector('.world-grid');
  const saved=await memoryPage.evaluate(()=>Network.api('/worlds/1/character','POST',{nickname:'Memory Test'}));assert.equal(saved.character.nickname,'Memory Test');
  await memoryPage.evaluate(pass=>Network.api('/account/delete','POST',{password:pass}),password);await memoryContext.close();
  assert.deepEqual(errors,[]);
  console.log('PASS: 4-character registration, embedded cross-origin preview with cookies and custom headers stripped, world/character creation, authenticated action, reload, logout revocation, wrong-password error and correct re-login; also works in memory when storage is blocked; no JS errors.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
