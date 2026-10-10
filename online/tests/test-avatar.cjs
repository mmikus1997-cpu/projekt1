// E2E 0.48.0 — awatary w grze: kompaktowe karty światów (szczegóły na hover),
// kreator: wybór płci (👨/👩), 🎲 Losuj, konflikt kategorii (czapka⇄kapelusz blokuje klik),
// podmiana w tej samej kategorii, postać: awatar na profilu, 7 slotów EQ, edytor awatara,
// Sklep → Garderoba (140 kosmetyk), arena: awatary + chip ruchu + zawsze włączone animacje.
const {chromium}=require('playwright');
const clickAt=(p,sel)=>p.evaluate(s=>{const el=document.querySelector(s);if(!el)throw Error('brak: '+s);el.dispatchEvent(new MouseEvent('click',{bubbles:true,cancelable:true}));},sel);
const ok=(name,cond)=>console.log((cond?'OK  ':'FAIL')+' '+name)||(!cond&&process.exitCode!==1&&(process.exitCode=1));
(async()=>{
 const b=await chromium.launch();
 const p=await (await b.newContext({viewport:{width:1360,height:900}})).newPage();
 const errs=[];p.on('pageerror',e=>errs.push(e.message.slice(0,140)));
 const B=process.env.TEST_BASE_URL||'http://127.0.0.1:3244';
 await p.goto(B);await p.click('[data-auth-mode=register]');
 await p.fill('#auth-username','av48x');await p.fill('#auth-password','test');await p.fill('#auth-confirm','test');await p.check('#age-consent');
 await p.click('#auth-form [type=submit]');await p.waitForSelector('.world-grid');

 // 1) kompaktowe karty światów + szczegóły na hover
 const fs=await p.locator('.world-card h2').first().evaluate(el=>getComputedStyle(el).fontSize);
 ok('karty światów kompaktowe (h2 '+fs+')',parseFloat(fs)<=21);
 const hint=await p.locator('.world-more-hint').first().isVisible();
 ok('hint „szczegóły po najechaniu”',hint);
 await p.hover('.world-card >> nth=0');await p.waitForTimeout(450);
 const after=await p.locator('.world-more').first().evaluate(el=>getComputedStyle(el).opacity);
 ok('hover odsłania szczegóły (opacity '+after+')',after==='1');

 // 2) kreator: awatar + płeć + 🎲 Losuj
 await clickAt(p,'[data-world="2"]');await p.waitForSelector('#avatar-creator');
 const av=await p.locator('.ce-av').count();
 ok('kreator pokazuje żywy awatar (ce-av)',av>0);
 await p.click('#ac-tiles [data-gender=k]');await p.waitForTimeout(120);
 const fem=await p.locator('#ac-preview-box .ce-av.av-g-k').count();
 ok('0.48: wybór płci — 👩 daje sylwetkę av-g-k',fem>0);
 await p.click('#ac-tiles [data-gender=m]');await p.waitForTimeout(120);
 const masc=await p.locator('#ac-preview-box .ce-av.av-g-k').count();
 ok('0.48: powrót na 👩→👨 czyści klasę av-g-k',masc===0);
 const skin0=await p.evaluate(()=>document.querySelector('#ac-preview-box .ce-av')?.outerHTML.slice(0,400));
 let skin1=skin0;
 for(let i=0;i<12&&skin1===skin0;i++){await clickAt(p,'#ac-random');await p.waitForTimeout(60);skin1=await p.evaluate(()=>document.querySelector('#ac-preview-box .ce-av')?.outerHTML.slice(0,400));}
 ok('🎲 Losuj zmienia wygląd',skin1!==skin0);

 // 3) konflikt kategorii: czapka + kapelusz → toast, bez zdejmowania
 for(const tab of ['cap','hat']){
  await p.click(`#ac-tabs [data-tab=${tab}]`);await p.waitForTimeout(50);
  const sel=p.locator('#ac-tiles .av-tile.selected');
  if(await sel.count())await sel.first().click();
  await p.waitForTimeout(60);
 }
 await p.click('#ac-tabs [data-tab=cap]');await p.waitForTimeout(50);
 await p.click('#ac-tiles [data-item^=cp]');await p.waitForTimeout(80);
 const capSel=await p.locator('#ac-tiles [data-item^=cp].selected').count();
 ok('czapka zakłada się',capSel>=1);
 await p.click('#ac-tabs [data-tab=hat]');await p.waitForTimeout(50);
 await p.click('#ac-tiles [data-item^=ht]');await p.waitForTimeout(120);
 const toastTxt=await p.evaluate(()=>{const t=document.getElementById('toast');return t&&!t.hidden?t.textContent:'';});
 ok('konflikt: toast blokujący ("'+toastTxt.slice(0,44)+'…")',toastTxt.includes('Nie można nosić jednocześnie'));
 const hatOn=await p.locator('#ac-tiles [data-item^=ht].selected').count();
 await p.click('#ac-tabs [data-tab=cap]');await p.waitForTimeout(60);
 const capStill=await p.locator('#ac-tiles [data-item^=cp].selected').count();
 ok('kapelusz NIE założony, czapka została',hatOn===0&&capStill>=1);

 // 4) ta sama kategoria → podmiana
 await p.click('#ac-tiles [data-item^=cp] >> nth=1');await p.waitForTimeout(80);
 const caps=await p.evaluate(()=>[...document.querySelectorAll('#ac-tiles [data-item^=cp]')].map(b2=>b2.classList.contains('selected')));
 ok('ta sama kategoria podmienia (wybrana dokładnie 1)',caps.filter(Boolean).length===1);
 await p.click('#ac-tabs [data-tab=cap]');await p.click('#ac-tiles [data-item^=cp].selected');await p.waitForTimeout(60);
 await p.click('#ac-tabs [data-tab=hat]');await p.click('#ac-tiles [data-item^=ht]');await p.waitForTimeout(60);
 const hatOn2=await p.locator('#ac-tiles [data-item^=ht].selected').count();
 ok('po zdjęciu czapki kapelusz się zakłada',hatOn2===1);

 // 5) utwórz postać
 await p.fill('#character-nickname','Awatarnica48');
 if(await p.locator('#test-consent').count())await p.check('#test-consent');
 await p.click('#character-form [type=submit]');
 await p.waitForSelector('[data-online=dismiss-tutorial]');await clickAt(p,'[data-online=dismiss-tutorial]');
 await p.waitForFunction(()=>!Network.busy);

 // 6) ekran postaci: awatar na profilu + 7 slotów + edycja
 await p.evaluate(()=>GameApp.showView('character'));await p.waitForTimeout(500);
 const prof=await p.locator('.profile-portrait .ce-av').count();
 ok('profil: awatar zamiast boksera',prof>0);
 const slots=await p.evaluate(()=>[...document.querySelectorAll('[data-eq-slot]')].map(e=>e.dataset.eqSlot));
 ok('EQ: sloty '+slots.join(','),['gloves','shirt','shoes','accessory','helmet','backpack','amulet'].every(s=>slots.includes(s)));
 const fig=await p.locator('.eq-figure .ce-av').count();
 ok('figura EQ = awatar',fig>0);
 await p.click('[data-extra=avatar-edit]');
 await p.waitForSelector('#av-editor-save');await p.waitForTimeout(300);
 ok('edytor awatara otwiera się z ekranu postaci',true);
 await p.click('#ac-tiles [data-gender=k]').catch(()=>{});
 await p.waitForTimeout(150);
 const edFem=await p.locator('#ac-preview-box .ce-av.av-g-k').count();
 ok('0.48: płeć w edytorze awatara',edFem>0);
 await clickAt(p,'#av-editor-save');await p.waitForTimeout(500);

 // 7) Sklep → Garderoba (140 kosmetyk, 14×10)
 await clickAt(p,'#nav-shop');await p.waitForTimeout(800);
 const cats=await p.locator('.wardrobe-panel .wb-cat').count();
 const tiles=await p.locator('.wardrobe-panel .av-tile').count();
 ok('Garderoba w Sklepie: kategorie='+cats+' kafle='+tiles,cats===14&&tiles===140);

 // 8) wybór światów: awatar postaci na karcie
 await clickAt(p,'#nav-worlds');await p.waitForTimeout(700);
 const cardAv=await p.locator('[data-card-av] .ce-av').count();
 ok('karta świata pokazuje awatar postaci',cardAv>0);

 // 9) klub sportowy: awatary obu zawodników + chip ruchu + animacje zawsze włączone
 await p.evaluate(()=>GameApp.showView('arena'));await p.waitForTimeout(500);
 const arenaAv=await p.locator('#portrait-0 .ce-av').count();
 const sparAv=await p.locator('#portrait-1 .ce-av').count();
 ok('arena: portrety to awatary (ja: '+arenaAv+', sparingpartner: '+sparAv+')',arenaAv>0&&sparAv>0);
 const motionBtn=await p.locator('#combat-motion-btn').evaluate(el=>getComputedStyle(el).display);
 const speedBtns=await p.locator('.speed [data-speed]').count();
 ok('0.48: animacje zawsze włączone (Wyłącz ukryty: '+motionBtn+', tempo: '+speedBtns+' przyciski)',motionBtn==='none'&&speedBtns>=3);
 await p.evaluate(()=>window.previewMotion('hit'));await p.waitForTimeout(1400);
 const chip=await p.locator('.move-chip').count();
 const chipTxt=chip?await p.locator('.move-chip').first().textContent():'';
 ok('ruch z itemu widoczny ("'+chipTxt.slice(0,40)+'")',chip>0&&/Cios|Kop|hełmem/.test(chipTxt));
 const fx=await p.locator('.combat-fx .fx-projectile use').first().getAttribute('href');
 ok('0.48: FX rysuje sprite ruchu ('+fx+')',/fx-it-(fist|boot|helm)/.test(fx||''));

 ok('zero błędów JS: '+(errs.length?errs.join(' | '):'czysto'),errs.length===0);
 await b.close();
})().catch(e=>{console.error('BŁĄD:',e.message);process.exit(1);});
