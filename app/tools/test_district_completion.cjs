// Końcowy E2E: prawdziwe API na osobnej świeżej instalacji, bez mocków i zmiany zapisów podglądu.
// Użycie: NODE_PATH=... node tools/test_district_completion.cjs http://127.0.0.1:8081
const { chromium } = require('playwright');
const fs=require('fs'), path=require('path'), assert=require('assert/strict');
(async()=>{
 const base=process.argv[2]; if(!base) throw Error('Podaj URL osobnej instalacji testowej.');
 const j=await (await fetch(base+'/api/auth/register',{method:'POST',headers:{'content-type':'application/json','X-City-Preview-Session':'1'},body:JSON.stringify({username:'qa_'+Date.now().toString().slice(-9),password:'final-qa-password-123',consent:true,birth_date:'2000-01-01'})})).json();
 assert(j.previewSessionToken,'Rejestracja nieudana');
 const headers={'content-type':'application/json','X-City-Preview-Session':'1','X-City-Session':j.previewSessionToken,'X-CSRF-Token':j.csrf};
 const api=async(url,body)=>{const r=await fetch(base+'/api'+url,{method:body?'POST':'GET',headers,body:body&&JSON.stringify(body)});const data=await r.json();assert(r.ok,JSON.stringify(data));return data;};
 await api('/worlds/2/character',{nickname:'QA '+Date.now().toString().slice(-6),accept_test_reset:true});
 const b=await chromium.launch();const p=await b.newPage({viewport:{width:1280,height:900}});const errors=[];if(process.env.CE_BLOCK_EXTERNAL) await p.route('**/*', route => new URL(route.request().url()).origin === new URL(base).origin ? route.continue() : (console.log('ZABLOKOWANE', route.request().url()), route.abort()));p.on('pageerror',e=>errors.push(e.stack || e.message));
 const tap=async(x,y)=>{await p.mouse.move(x,y);await p.waitForTimeout(400);await p.mouse.down();await p.waitForTimeout(120);await p.mouse.up();await p.waitForTimeout(650);};
 await p.goto(base);await p.evaluate(([t,c])=>{localStorage.setItem('flutter.session.token',JSON.stringify(t));localStorage.setItem('flutter.session.csrf',JSON.stringify(c));localStorage.setItem('flutter.session.world','2');},[j.previewSessionToken,j.csrf]);
 await p.reload();await p.waitForTimeout(8000);await p.keyboard.press('Escape');await tap(90,90);
 await p.evaluate(()=>document.querySelector('flt-semantics-placeholder')?.click());await p.waitForTimeout(500);
 assert(p.url().includes('district'),'Nie otwarto Dzielnicy');
 // Rezydencja na etapie pierwszym.
 await tap(460,295);
 await p.getByRole('button',{name:/Rozbuduj do Lvl 2/}).click();await p.waitForTimeout(600);
 const started=await api('/worlds/2/state');assert.equal(started.state.buildings.residence,1);assert.equal(started.state.construction.building,'residence');
 const out=path.resolve(__dirname,'../shots');fs.mkdirSync(out,{recursive:true});
 await p.screenshot({path:path.join(out,'final-construction.jpg'),type:'jpeg',quality:88});
 await p.getByLabel(/do poziomu 2/).waitFor({timeout:3000});
 await p.getByRole('button',{name:'Zamknij',exact:true}).click();
 // Garaż: przycisk zablokowany podczas cudzej budowy.
 await tap(450,530);const blocked=p.getByRole('button',{name:/Trwa budowa: Rezydencja/});assert(await blocked.isDisabled(),'Druga budowa nie jest zablokowana');
 await p.getByRole('button',{name:'Zamknij',exact:true}).click();await tap(460,295);
 await p.waitForFunction(() => [...document.querySelectorAll('[aria-label]')].some(x => (x.getAttribute('aria-label')||'').includes('Lvl 2/5')), {timeout:30000}).catch(async e => { fs.writeFileSync('/tmp/final-dom.txt',await p.content()); await p.screenshot({path:path.join(out,'final-debug.jpg'),type:'jpeg'});throw e;});
 const done=await api('/worlds/2/state');assert.equal(done.state.buildings.residence,2);assert(!done.state.construction);
 await p.screenshot({path:path.join(out,'final-construction-done.jpg'),type:'jpeg',quality:88});
 await p.getByRole('button',{name:'Zamknij',exact:true}).click();
 // Kawiarnia: odbiór bez przewijania do kart.
 await tap(760,285);await p.screenshot({path:path.join(out,'final-cafe.jpg'),type:'jpeg'});
 const collect=p.getByRole('button',{name:/ODBIERZ SKARBIEC/});await collect.last().click();await p.waitForTimeout(600);
 const claimed=await api('/worlds/2/state');assert(claimed.state.vaults.cafe<done.state.vaults.cafe,'Skarbiec nie został odebrany');
 await p.getByRole('button',{name:'Zamknij',exact:true}).click();
 assert.equal(errors.length,0,errors.join('\n'));await b.close();
 console.log('PASS: czysta instalacja, rejestracja, postać, rozbudowa bez natychmiastowego poziomu, odliczanie, blokada innego budynku, automatyczne zakończenie, odbiór skarbca z panelu.');
})().catch(e=>{console.error(e);process.exit(1);});
