// M5: kontrola planu i paneli na desktopie oraz telefonie. NODE_PATH wskazuje instalację Playwright.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
 const out = path.resolve(__dirname, '../shots');
 const b = await chromium.launch(); const errors=[];
 const r=await fetch('http://127.0.0.1:8080/api/auth/login',{method:'POST',headers:{'content-type':'application/json','X-City-Preview-Session':'1'},body:JSON.stringify({username:'klub_demo',password:'klub-demo-123'})});
 if(!r.ok) throw Error('Login: '+r.status); const j=await r.json();
 for(const [name,width,height] of [['desktop',1280,900],['mobile',400,850]]) {
  const p=await b.newPage({viewport:{width,height}});
  p.on('pageerror', e=>errors.push(e.message));
  p.on('console', m=>{if(/overflowed|EXCEPTION CAUGHT/.test(m.text())) errors.push(m.text());});
  await p.goto('http://127.0.0.1:8080/');
  await p.evaluate(([t,c])=>{localStorage.setItem('flutter.session.token',JSON.stringify(t));localStorage.setItem('flutter.session.csrf',JSON.stringify(c));localStorage.setItem('flutter.session.world','2');},[j.previewSessionToken,j.csrf]);
  await p.reload();await p.waitForTimeout(8000);await p.keyboard.press('Escape');await p.waitForTimeout(1000);
  const tap=async(x,y)=>{await p.mouse.move(x,y);await p.waitForTimeout(400);await p.mouse.down();await p.waitForTimeout(120);await p.mouse.up();await p.waitForTimeout(1600);};
  await tap(name==='desktop'?90:28,name==='desktop'?90:820);
  if(!p.url().includes('district')) throw Error('Brak nawigacji do dzielnicy: '+p.url());
  await p.screenshot({path:path.join(out,`aligned-${name}.png`)});
  await tap(name==='desktop'?470:90,name==='desktop'?310:180);
  await p.evaluate(()=>document.querySelector('flt-semantics-placeholder')?.click()); await p.waitForTimeout(400);
  if(!await p.getByRole('button',{name:'Zamknij',exact:true}).count()) throw Error('Brak panelu budynku');
  await p.screenshot({path:path.join(out,`aligned-${name}-panel.png`)});
  await p.getByRole('button',{name:'Zamknij',exact:true}).click();await p.waitForTimeout(600);
  if(name==='desktop') {
   for(let stage=1;stage<=4;stage++) {await tap(678+(stage-1)*47,722);await p.screenshot({path:path.join(out,`aligned-stage-${stage}.png`)});}
  }
  await p.close();
 }
 await b.close(); if(errors.length) throw Error(errors.join('\n'));
 console.log('PASS: desktop + mobile, panele otwierane i zamykane, brak wyjątków/overflow; zrzuty 4 etapów zapisane.');
 fs.writeFileSync(path.join(out,'aligned-e2e.txt'),'PASS desktop/mobile: navigation, building panel open/close, no runtime errors or overflow.\n');
})().catch(e=>{console.error(e);process.exit(1);});
