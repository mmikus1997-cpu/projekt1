/* Same-origin API client. Economy requests carry intent, never client balances or time. */
const Network=(()=>{
 'use strict';
 const SESSION_KEY='cityEmpirePreviewSessionV1';
 let previewToken='';
 try{previewToken=sessionStorage.getItem(SESSION_KEY)||'';}catch{}
 function storePreviewToken(value){previewToken=value||'';try{if(previewToken)sessionStorage.setItem(SESSION_KEY,previewToken);else sessionStorage.removeItem(SESSION_KEY);}catch{}}
 const N={authSettings:{mode:'production',minPasswordLength:12,previewSessions:false},user:null,csrf:'',world:null,character:null,packet:null,busy:false,panel:null,reportMode:false,generation:0};
 let serverClock=Date.now(),clockAnchor=performance.now(),refreshing=false,authMode='login',worlds=[],adminCache=null;
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const money=n=>Math.floor(n).toLocaleString('pl-PL')+' $';
 const date=n=>new Date(n).toLocaleString('pl-PL',{dateStyle:'short',timeStyle:'short'});
 const key=()=>globalThis.crypto?.randomUUID?.().replaceAll('-','')||Array.from(crypto.getRandomValues(new Uint8Array(24)),x=>x.toString(16).padStart(2,'0')).join('');
 const kindName={standard:'Standardowy',event:'Eventowy',test:'Testowy',experimental:'Eksperymentalny'};
 N.now=()=>serverClock+(performance.now()-clockAnchor);
 function clock(t){if(t){serverClock=t;clockAnchor=performance.now();}}
 async function api(path,method='GET',body=null,headers={}){
  let response;
  const isAuthentication=path==='/auth/login'||path==='/auth/register';
  let requestPath=path,requestMethod=method,requestBody=body;
  let requestHeaders={...(method==='GET'?{}:{'Content-Type':'application/json','X-CSRF-Token':N.csrf}),...headers};
  if(isAuthentication&&N.authSettings.previewSessions){
   requestBody={...body,preview_session:true};
  }else if(previewToken&&N.authSettings.previewSessions&&!['/auth/config','/setup/status','/health'].includes(path)){
   requestPath='/preview/request';requestMethod='POST';
   requestBody={session:previewToken,csrf:N.csrf,method,path,payload:body,idempotency_key:headers['Idempotency-Key']||null};
   requestHeaders={'Content-Type':'application/json'};
  }
  try{response=await fetch('/api'+requestPath,{method:requestMethod,credentials:'same-origin',headers:requestHeaders,...(requestBody===null?{}:{body:JSON.stringify(requestBody)})});}
  catch{const e=Error('Brak połączenia z serwerem. Otwórz podgląd na żywo i spróbuj ponownie.');e.retryable=true;throw e;}
  const data=await response.json().catch(()=>({detail:'Nieprawidłowa odpowiedź serwera.'}));
  if(!response.ok){
   if(response.status===401&&!path.startsWith('/auth/')){storePreviewToken('');N.user=null;N.character=null;showAuth();}
   const text=Array.isArray(data.detail)?data.detail.map(x=>x.msg).join(' · '):data.detail||'Operacja nie powiodła się.';
   const e=Error(text);e.status=response.status;throw e;
  }
  return data;
 }
 N.api=api;
 function setUser(user,csrf){N.user=user;N.csrf=csrf;$('#nav-admin').hidden=user.role!=='admin';$('.avatar-small').textContent=user.username.slice(0,2).toUpperCase();$('.avatar-small').title=user.username;}
 function install(packet){
 if(window.CityAvatar&&packet?.catalog?.gameLooks){
  // gameLooks z pakietu świata: do katalogu (gdy już załadowany) albo do kolejki
  // na chwilę po pierwszym ensureAvatarCatalog (wejście prosto do świata po odświeżeniu).
  const C=window.CityAvatar;
  if(C.catalog){C.catalog.gameLooks=packet.catalog.gameLooks;C.catalog.gameItems=packet.catalog.items;C.catalog.__flat=null;}
  else{window.CityAvatarPendingLooks=packet.catalog.gameLooks;window.CityAvatarPendingItems=packet.catalog.items;}
 }
  N.packet=packet;N.world=packet.world;N.character=packet.character;clock(packet.serverTime);GameApp.install(packet);$('.hud-identity strong').textContent=packet.character.nickname;$('#nav-worlds span').textContent=packet.world.name;
  N.eventsUnread=packet.eventsUnread||0;N.dmUnread=packet.dmUnread||0;updateBadge();applyShopCosmetics(packet.shop);
  const notice=(packet.notices||[]).find(n=>n.text);let seen=-1;try{seen=Number(sessionStorage.getItem('cityNoticeSeen'))||0;}catch{}
  if(notice&&notice.id>seen){const el=$('#world-news');el.innerHTML=icon('city')+'<span><strong>Ogłoszenie administratora:</strong> '+esc(notice.text)+'</span><button class="text-btn" data-online="notice-dismiss">OK</button>';el.hidden=false;}
 }
 function updateBadge(){const b=$('#community-badge');if(!b)return;const n=(N.eventsUnread||0)+(N.dmUnread||0);b.hidden=!n;b.textContent=n>9?'9+':String(n);}
 N.updateBadge=updateBadge;
 function applyShopCosmetics(shop){const el=document.querySelector('.hud-identity');if(!el||!shop)return;el.classList.remove('vip','skin-copper','skin-gold','skin-neon');if(shop.vipActive)el.classList.add('vip');if(shop.skin){const cls=shop.skin.replace('_','-');if(cls==='skin-gold')el.classList.add('vip');else el.classList.add(cls);}const chip=document.getElementById('hud-vip');if(chip){chip.hidden=!shop.vipActive;if(shop.vipActive)chip.textContent='VIP · do '+date(shop.vipUntil);}}
 N.applyShopCosmetics=applyShopCosmetics;
 function error(error){const text=error.message||String(error);if($('#network-dialog').open){let el=$('#network-dialog-error');if(!el){el=document.createElement('p');el.id='network-dialog-error';el.className='form-error';el.setAttribute('role','alert');$('#network-dialog-body').prepend(el);}el.textContent=text;}toast(text);}
 async function guarded(fn){try{return await fn();}catch(e){error(e);return null;}}
 function dialog(title,html){$('#network-dialog-title').textContent=title;$('#network-dialog-body').innerHTML=html;if(!$('#network-dialog').open)$('#network-dialog').showModal();}
 function hideCover(){$('#network-cover').hidden=true;document.body.classList.remove('network-gated');}
 function showCover(html){document.body.classList.add('network-gated');$('#network-cover').innerHTML=html;$('#network-cover').hidden=false;}
 function showAuth(message=''){
  N.panel=null;N.world=null;N.character=null;N.reportMode=false;
  const art=$('#view-city .city-art')?.outerHTML||'';
  showCover(`<div class="auth-shell"><section class="auth-story"><div class="auth-brand">CITY <span>EMPIRE</span></div><span class="auth-kicker">TWOJE MIASTO. TWOJA HISTORIA.</span><h1>Zacznij od małych kroków.<br>Zbuduj coś wielkiego.</h1><p>Rozwijaj postać, prowadź firmy i rywalizuj z innymi graczami na niezależnych światach.</p><div class="auth-city">${art}</div><div class="auth-foot">KONTRAKTY <span>•</span> BIZNES <span>•</span> SPORT</div></section><section class="auth-card"><span class="world-pill"><span class="dot"></span>Wersja sieciowa · DEV 0.54.0</span><h2>${authMode==='login'?'Witaj ponownie.':'Twoja historia zaczyna się tutaj.'}</h2><p>Jedno konto. Osobna postać na każdym świecie.</p><div class="auth-tabs"><button data-auth-mode="login" class="${authMode==='login'?'active':''}">Zaloguj się</button><button data-auth-mode="register" class="${authMode==='register'?'active':''}">Utwórz konto</button></div><form id="auth-form"><label class="field" for="auth-username">Login</label><input id="auth-username" name="username" autocomplete="username" required minlength="3" maxlength="24" pattern="[A-Za-z0-9_\\-]{3,24}" placeholder="np. miejski_strateg"><label class="field" for="auth-password">Hasło ${authMode==='register'?'· minimum '+N.authSettings.minPasswordLength+(N.authSettings.minPasswordLength===4?' znaki (testy)':' znaków'):''}</label><input id="auth-password" type="password" name="password" autocomplete="${authMode==='register'?'new-password':'current-password'}" required minlength="${authMode==='register'?N.authSettings.minPasswordLength:1}" maxlength="128" placeholder="Twoje hasło"><button type="button" class="text-btn pw-toggle" data-pw-show="#auth-password">Pokaż</button>${authMode==='register'?'<label class="field" for="auth-confirm">Powtórz hasło</label><input id="auth-confirm" type="password" autocomplete="new-password" required minlength="'+N.authSettings.minPasswordLength+'" maxlength="128"><button type="button" class="text-btn pw-toggle" data-pw-show="#auth-confirm">Pokaż</button><label class="check-field" for="age-consent"><input id="age-consent" type="checkbox" required><span>Mam ukończone 16 lat albo mam zgodę rodzica lub opiekuna na założenie konta (RODO art. 8).</span></label>':''}<p class="form-error" id="auth-error" role="alert">${esc(message)}</p><button class="btn btn-gold full-width" type="submit">${authMode==='login'?'Wejdź do miasta':'Utwórz konto'} ${icon('arrow')}</button></form><div class="auth-warning">${icon('info')}<p>To wersja rozwojowa, bez prawdziwych płatności. Krótkie hasła służą tylko do testów; użyj hasła nieużywanego gdzie indziej. Nie podawaj danych wrażliwych. Odzyskiwanie hasła nie jest jeszcze dostępne.</p></div></section></div>`);
 }
 async function authenticate(form){
  const button=form.querySelector('button[type=submit]');button.disabled=true;let established=false;
  try{
   const username=$('#auth-username').value.trim(),password=$('#auth-password').value;
   if(authMode==='register'&&password!==$('#auth-confirm').value)throw Error('Hasła nie są takie same.');
   const response=await api('/auth/'+authMode,'POST',{username,password,consent:authMode==='register'&&!!$('#age-consent')?.checked});if(N.authSettings.previewSessions&&!response.previewSessionToken)throw Error('Brak tokenu sesji w odpowiedzi (CE-AUTH-01). Odśwież podgląd wersji 0.48.0.');storePreviewToken(response.previewSessionToken);setUser(response.user,response.csrf);established=true;await showWorlds();
  }catch(e){if(established&&e.status===401){authMode='login';showAuth('Serwer potwierdził login, ale sesja nie dotarła do gry (CE-AUTH-02). Odśwież podgląd i sprawdź, czy widzisz wersję 0.48.0.');}else $('#auth-error').textContent=e.message;}finally{button.disabled=false;}
 }
 async function ensureAvatarCatalog(){
  if(window.CityAvatar?.catalog){
   if(window.CityAvatarPendingLooks){window.CityAvatar.catalog.gameLooks=window.CityAvatarPendingLooks;window.CityAvatar.catalog.gameItems=window.CityAvatarPendingItems;window.CityAvatar.catalog.__flat=null;window.CityAvatarPendingLooks=null;window.CityAvatarPendingItems=null;}
   return window.CityAvatar.catalog;
  }
  try{const c=await api('/avatar/catalog','GET');
   if(window.CityAvatarPendingLooks){c.gameLooks=window.CityAvatarPendingLooks;c.gameItems=window.CityAvatarPendingItems;window.CityAvatarPendingLooks=null;window.CityAvatarPendingItems=null;}
   if(window.CityAvatar)window.CityAvatar.init(c);
   return c;
  }catch(e){return null;}
 }
 function mountCoverAvatars(){
  if(!window.CityAvatar)return;
  const chip=$('#chip-avatar');
  if(chip){let prev=null;try{prev=+sessionStorage.getItem('cityEmpireOnlineWorld');}catch{}
   const withChar=worlds.filter(w=>w.character&&w.character.avatar);
   const pick=withChar.find(w=>w.id===prev)||withChar[0];
   if(pick)window.CityAvatar.mount(chip,pick.character.avatar,{animate:true});
  }
  document.querySelectorAll('[data-card-av]').forEach(el=>{const w=worlds.find(x=>x.id===+el.dataset.cardAv);if(w&&w.character?.avatar)window.CityAvatar.mount(el,w.character.avatar,{animate:true});});
 }
 let creatorPayload=null;
 async function showWorlds(){
  if(playing){toast('Zakończ lub pomiń animację przed zmianą świata.');return;}
  const response=await api('/worlds');clock(response.serverTime);worlds=response.worlds;N.panel=null;try{sessionStorage.setItem('cityWorldsSeen:'+N.user.id,String(response.serverTime));}catch{}$('#world-news').hidden=true;
  await ensureAvatarCatalog();
  const cards=worlds.map(w=>{
   const test=['test','experimental'].includes(w.kind),available=!w.planned&&!w.maintenance;
   const status=w.maintenance?'Przerwa techniczna':w.planned?'Planowany':w.registration_open?'Otwarta rejestracja':'Rejestracja zamknięta';
   return `<article class="world-card ${test?'test-world':''}"><div class="card-av" data-card-av="${w.id}">${w.character&&w.character.avatar?'':'<span class="card-av-empty" title="Awatar utworzysz razem z postacią">?</span>'}</div><div class="world-card-top"><span>${kindName[w.kind]}</span><span class="world-speed">×${w.speed}</span></div><h2>${esc(w.name)}</h2><p class="world-status"><span class="dot"></span>${status}</p><span class="world-more-hint">ℹ️ szczegóły po najechaniu</span><div class="world-more"><div class="world-details"><span>Otwarcie</span><strong>${date(w.opens_at)}</strong><span>Twoja postać</span><strong>${w.character?esc(w.character.nickname):'Jeszcze nie utworzona'}</strong></div>${w.era?`<p class="era-line">🏛️ Era ${w.era.n}/4 · ${esc(w.era.label)} · dzień ${w.era.day}/${w.era.total}${w.era.next?` · następna: Era ${w.era.next.n} (${esc(w.era.next.label)}) za ${w.era.next.inDays} dni — dzielnice 1–${w.era.next.districts}`:w.era.epilog?` · epilog sezonu${w.era.final?`, podsumowanie gotowe`:``}`:``}</p><p class="era-line era-season">🏁 Sezon ${w.era.season.n} kończy się za ${w.era.season.daysLeft} dni — podsumowanie topki i tytuły kosmetyczne (Mistrz/Elita/Lider).</p>`:``}${w.announcement?`<p class="world-announcement">${esc(w.announcement)}</p>`:''}${test?'<p class="test-disclaimer">Świat testowy: niezależne tempo, start 3 000 $ i 240 energii. Postępy mogą być resetowane po komunikacie.</p>':'<p class="test-disclaimer">Niezależna gospodarka. Brak przenoszenia pieniędzy i przedmiotów.</p>'}</div><button class="btn ${test?'':'btn-gold'} full-width" data-world="${w.id}" ${!available||(!w.character&&!w.registration_open)?'disabled':''}>${w.character?'Wejdź do postaci':'Utwórz postać'} ${icon('arrow')}</button></article>`;
  }).join('');
  showCover(`<div class="world-shell"><div class="world-shell-top"><div class="auth-brand">CITY <span>EMPIRE</span></div><div><button class="text-btn profile-chip" data-online="profile" title="Profil i osiągnięcia — także przed wejściem do gry"><span class="chip-av" id="chip-avatar"></span><span>${esc(N.user.username)}</span></button><button class="btn" data-online="rankings" title="Ranking Twoich światów i globalny — także przed wejściem do gry">🥇 Ranking</button><button class="btn" data-online="account">Konto</button><button class="text-btn" data-online="logout">Wyloguj</button></div></div><div class="eyebrow">JEDNO KONTO · WIELE MOŻLIWOŚCI</div><h1>Wybierz swój świat.</h1><p class="lead">Każdy świat to nowy początek. Twoje dotychczasowe postacie pozostają na swoich serwerach.</p><div class="world-grid">${cards}</div><p class="world-note">Na szybki pierwszy test polecamy CITY LAB: kontrakt 10-minutowy trwa tutaj 10 sekund. Ranking testowy jest oddzielony od standardowego.</p></div>`);
  mountCoverAvatars();
 }
 N.showWorlds=()=>guarded(showWorlds);
 async function chooseWorld(id){
  const w=worlds.find(w=>w.id===id);if(!w)return;
  if(w.character){await loadWorld(id);return;}
  const test=['test','experimental'].includes(w.kind);
  await ensureAvatarCatalog();
  const cat=window.CityAvatar?.catalog;
  let crBody={gender:'m',skin:0,hair:1,hairColor:0},crWorn={shirt:'ts1',pants:'pt1',shoes:'bt1'},crTab='body';
  creatorPayload=()=>({body:{...crBody},worn:{...crWorn}});
  const CATS2=cat?[{k:'body',label:'Ciało',icon:'🧍'}].concat(cat.cats):[];
  const catMeta=k=>CATS2.find(c=>c.k===k);
  function crTiles(){
   const box=document.getElementById('ac-tiles');if(!box)return;
   if(crTab==='body'){
    const sw=(arr,key,cls)=>arr.map((v,i)=>`<button type="button" class="av-tile swatch ${crBody[key]===i?'selected':''}" data-body="${key}" data-i="${i}"><span class="sw ${cls||''}" style="background:${v}"></span>${typeof v==='string'&&/^#/.test(v)?'':esc(v)}</button>`).join('');
    box.innerHTML='<p class="tiny">Płeć sylwetki</p><div class="sw-row">'+'<button type="button" class="av-tile swatch gen-b'+(crBody.gender!=='k'?' selected':'')+'" data-gender="m">👨 Mężczyzna</button>'+'<button type="button" class="av-tile swatch gen-b'+(crBody.gender==='k'?' selected':'')+'" data-gender="k">👩 Kobieta</button></div>'+'<p class="tiny">Karnacja</p><div class="sw-row">'+sw(cat.bodies.skins,'skin')+'</div><p class="tiny">Włosy</p><div class="sw-row">'+cat.bodies.hairs.map((h,i)=>`<button type="button" class="av-tile swatch ${crBody.hair===i?'selected':''}" data-body="hair" data-i="${i}">${esc(h)}</button>`).join('')+'</div><p class="tiny">Kolor włosów</p><div class="sw-row">'+sw(cat.bodies.hairColors,'hairColor')+'</div>';
   }else{
    box.innerHTML=cat.items[crTab].map(it=>{const on=crWorn[crTab]===it.id;const locked=it.vip&&!cat.vipActive;
     return `<button type="button" class="av-tile ${on?'selected':''} ${it.vip?'is-vip':''}" data-item="${it.id}" ${locked?'data-locked="1"':''}><span class="av-swatch"><i style="background:${it.c}"></i><i style="background:${it.c2}"></i></span><b>${esc(it.n)}</b><small>${it.vip?'👑 VIP':(on?'założona':'na start · gratis')}</small></button>`;}).join('');
   }
  }
  function crRender(){
   const box=document.getElementById('ac-preview-box');if(box&&window.CityAvatar)window.CityAvatar.mount(box,{body:crBody,worn:crWorn},{animate:true});
   const tabs=document.getElementById('ac-tabs');
   if(tabs)tabs.innerHTML=CATS2.map(c=>`<button type="button" class="av-tab ${crTab===c.k?'active':''}" data-tab="${c.k}">${c.icon} ${esc(c.label)}</button>`).join('');
   crTiles();
   const root=document.getElementById('avatar-creator');
   const rnd=document.getElementById('ac-random');
   if(rnd)rnd.onclick=()=>{const cfg=window.CityAvatar.random(cat.vipActive);crBody=cfg.body;crWorn=cfg.worn;crRender();};
   if(root)root.onclick=e=>{
    if(e.target.id==='ac-random')return;
    const t=e.target.closest('button');if(!t)return;
    if(t.dataset.tab)return void(crTab=t.dataset.tab,crRender());
    if(t.dataset.gender){crBody.gender=t.dataset.gender;crRender();return;}
    if(t.dataset.body){crBody[t.dataset.body]=+t.dataset.i;crRender();return;}
    if(t.dataset.item){
     const it=window.CityAvatar.item(t.dataset.item);if(!it)return;
     const SLOT_OF={cap:'head',hat:'head',pants:'legs',shorts:'legs'};
     if(t.dataset.locked){toast('Rzeczy VIP odblokujesz po aktywacji VIP w sklepie (w grze).');return;}
     if(crWorn[it.k]===it.id)delete crWorn[it.k];
     else{
      const slot=SLOT_OF[it.k];let conflict=null;
      if(slot)for(const k2 of Object.keys(crWorn))if(k2!==it.k&&SLOT_OF[k2]===slot)conflict=k2;
      if(conflict){const lb=k=>(window.CityAvatar&&CityAvatar.cats().find(c=>c.k===k)||{}).label||k;toast('Nie można nosić jednocześnie: zdejmij „'+lb(conflict)+'”, żeby założyć „'+lb(it.k)+'”.');return;}
      crWorn[it.k]=it.id;
     }
     crRender();
    }
   };
  }
  dialog('Nowa postać · '+w.name,`${cat?'<div class="avatar-creator" id="avatar-creator"><div class="ac-preview"><div id="ac-preview-box"></div><p class="tiny">Awatar żyje: oddycha, mruga i kołysze się.</p><button type="button" class="btn" id="ac-random" title="Losuj wygląd i strój">🎲 Losuj</button></div><div class="ac-options"><p class="section-note">Ubierz awatara — rzeczy zwykłe wybierasz na start <b>gratis</b>; rzeczy 👑 VIP odblokujesz później w sklepie.</p><div class="av-tabs" id="ac-tabs"></div><div class="av-tiles" id="ac-tiles"></div></div></div><hr class="ac-sep">':''}<p>Jedna postać na konto na tym świecie. Zaczynasz niezależnie od innych światów.</p><form id="character-form" data-world-id="${id}"><label class="field" for="character-nickname">Publiczna nazwa postaci</label><input id="character-nickname" name="nickname" minlength="3" maxlength="24" required value="${esc(N.user.username)}">${test?'<label class="check-field"><input type="checkbox" id="test-consent" required><span>Rozumiem testowy charakter świata, tempo ×'+w.speed+' oraz możliwość zapowiedzianego resetu postępów.</span></label>':''}<p id="character-error" class="form-error" role="alert"></p><button class="btn btn-gold full-width" type="submit">Utwórz postać</button></form>`);
  if(cat)crRender();
 }
 async function loadWorld(id,provided=null){
  N.generation++;N.reportMode=false;N.panel=null;
  const packet=provided||await api(`/worlds/${id}/state`);install(packet);ensureAvatarCatalog().then(c=>{if(!c)return;if(GameApp.view==='character'||GameApp.tabNow==='postac')GameApp.showView('character');else if(window.updateArenaAvatars)window.updateArenaAvatars();});GameApp.prepareCharacter();hideCover();$('#network-dialog').close();GameApp.showView('city');
  try{sessionStorage.setItem('cityEmpireOnlineWorld',String(id));}catch{}
  if(!packet.state.tutorialDismissed)showTutorial();else showDayBrief();
 }
 N.refresh=async()=>{
  if(!N.user||!N.world||N.busy||refreshing||!$('#network-cover').hidden)return;
  const epoch=N.generation,wid=N.world.id;refreshing=true;
  try{const p=await api(`/worlds/${wid}/state`);if(epoch===N.generation&&wid===N.world?.id)install(p);}
  catch(e){if(N.user){toast(e.message);if(e.message.includes('dostępny'))await showWorlds();}}
  finally{refreshing=false;}
 };
 N.action=async payload=>{
  if(N.busy||!N.world)return;
  N.busy=true;N.generation++;document.body.classList.add('server-busy');
  try{const operationKey=key();let p;try{p=await api(`/worlds/${N.world.id}/actions`,'POST',payload,{'Idempotency-Key':operationKey});}catch(e){if(!e.retryable)throw e;p=await api(`/worlds/${N.world.id}/actions`,'POST',payload,{'Idempotency-Key':operationKey});}install(p);if(p.message)toast(p.message);}
  catch(e){error(e);}
  finally{N.busy=false;document.body.classList.remove('server-busy');}
 };
 function renderNames(list){names[0]=list[0];names[1]=list[1];[0,1].forEach(i=>$('#fighter-'+i+' .fighter-name h2').textContent=list[i]);}
 function showReport(report){
  if(playing){toast('Raport zapisany. Otwórz go po zakończeniu bieżącej animacji.');return;}
  GameApp.prepareCharacter();GameApp.showView('arena');
  let r=JSON.parse(JSON.stringify(report));
  if(r.characterIds?.[1]===N.character.id){
   for(const field of ['stats','profiles','tactics','names','finalHp','ratingChanges','characterIds'])if(r[field])r[field].reverse();
   r.events=r.events.map(e=>({...e,attacker:1-e.attacker,defender:1-e.defender,hp:e.hp.slice().reverse()}));if(r.winner!==null)r.winner=1-r.winner;r.displayMirrored=true;
  }
  if(Array.isArray(r.rounds))r.rounds=r.rounds.length;
  N.reportMode=true;current=r;stats=r.stats.map(a=>a.slice());tactic=r.tactics[0];enemyMode=r.tactics[1];selections=['custom','custom'];renderConfig();renderNames(r.names);[0,1].forEach(i=>$('#fighter-sub-'+i).textContent='Zapisany zestaw · '+N.world.name);$('#view-arena .page-title .eyebrow').textContent='Klub sportowy · Raport rankingowy';playback();
 }
 function attackResult(r){
  const rep=r.report||{},names=rep.names||['Ty','Przeciwnik'],lab={presja:'Presja',kontrola:'Kontrola',kontra:'Kontra',zrowna:'Zrównoważona',szablon:'Szablon obrony'};
  const mine=rep.characterIds&&rep.characterIds[0]===N.character?.id?0:1,rc=rep.ratingChanges||[0,0];
  const res=rep.winner==null?'Remis.':mine===rep.winner?'Wygrana! ⚔️':'Porażka...';
  const fmt=v=>(v>=0?'+':'')+Math.round(v*10)/10;
  dialog('Auto-atak · '+names[1-mine],`<p><b>${res}</b> ${esc(names[mine])} vs ${esc(names[1-mine])}</p><p class="section-note">Taktyki: <b>${lab[rep.tactics?.[mine]]||'—'}</b> vs <b>${lab[rep.tactics?.[1-mine]]||'—'}</b> · zmiana Elo: <b>${fmt(rc[mine])}</b> / ${fmt(rc[1-mine])}</p><p class="tiny">Walka zaliczona do limitu 5 na dobę (UTC). Bez utraty pieniędzy i przedmiotów — obrońcę reprezentowała jego zapisana taktyka, nawet jeśli był offline.</p><div class="modal-actions"><button class="btn" id="atk-replay-btn">▶ Odtwórz raport</button><button class="btn btn-gold" onclick="this.closest('dialog').close()">OK</button></div>`);
  $('#atk-replay-btn').onclick=()=>{$('#network-dialog').close();showReport(r.report);};
  $('#network-dialog').addEventListener('close',()=>{if(N.panel==='pvp'&&!playing)showPvp().catch(()=>{});},{once:true});
 }
 function showDayBrief(){  if(!N.packet)return;  const s=N.packet.state||{},t=N.packet.catalog?.tender,a=N.packet.away,chips=[];
  if(a?.contracts?.length)chips.push(`<span class="ab-chip">📄 ${a.contracts.length} zlec. do odbioru</span>`);
  if(a?.training)chips.push(`<span class="ab-chip">🏋️ Treningi: ${a.training}</span>`);
  if(a?.vault>=1)chips.push(`<span class="ab-chip">💰 ${a.vault.toLocaleString('pl-PL')} $ w skarbcach</span>`);
  if(a?.rest)chips.push(`<span class="ab-chip">⏰ Odpoczynek gotowy</span>`);
  const lvl=(window.GameApp&&GameApp.level)?GameApp.level(s.xp||0):1;
  const done=t&&s.tenderDone===t.day,locked=t&&lvl<t.level;
  const photos=`<div class="brief-photos"><figure><img src="/art/loc-port.jpg" alt="Port nocą"><figcaption>Port</figcaption></figure><figure><img src="/art/loc-business.jpg" alt="Dzielnica biznesowa"><figcaption>Biznes</figcaption></figure><figure><img src="/art/loc-stadium.jpg" alt="Arena miejska"><figcaption>Arena</figcaption></figure></div>`;
  const awayTxt=a?(a.minutes>=60?Math.round(a.minutes/60*10)/10+' h':a.minutes+' min'):'';
  const idleSec=a?`<section class="brief-card"><h3>🏠 Witaj z powrotem</h3><p class="section-note"><b>${awayTxt}</b> poza miastem — miasto pracowało dla Ciebie.</p><div class="brief-chips">${chips.join('')}</div><div class="brief-actions"><button class="btn btn-gold" data-map-go="business">💰 Odbierz dochód</button><button class="btn" data-map-go="contracts">📄 Odbiór zleceń</button></div></section>`:'';
  const tenderSec=t?`<section class="brief-card"><h3>⭐ Przetarg dnia</h3><p><b>${esc(t.name)}</b></p><p class="section-note">💸 ${(t.cash||0).toLocaleString('pl-PL')} $ · ⭐ ${t.xp} XP · ⚡ ${t.energy}${locked?` · 🔒 od poziomu ${t.level}`:''}</p><div class="brief-actions">${done?'<span class="ab-chip">✓ Przyjęty</span>':`<button class="btn btn-gold" data-online="brief-tender" ${locked?'disabled':''}>🚀 Przyjmij przetarg</button>`}<button class="btn" data-map-go="contracts">Szczegóły</button></div></section>`:'';
  dialog('Dzień w mieście · powiadomienie',`<p class="section-note">Twój codzienny briefing: odbierz, co zarobiło się w tle, i rusz z przetargiem dnia.</p>${photos}${idleSec}${tenderSec}<div class="modal-actions"><button class="btn" data-online="brief-close">Zamknij</button></div>`);
 }
 function showTutorial(){
  if(!N.packet)return;
  const s=N.packet.state,steps=[['contracts','Przyjmij i odbierz kontrakt','Gotówka i XP pochodzą z legalnych zleceń.',s.completed.contracts>0],['character','Ukończ trening','Trening zwiększa wybraną statystykę. Nie zmusza do wyboru klasy.',s.completed.training>0],['character','Kup wyposażenie','Załóż przedmiot i zobacz jego bonus w klubie sportowym.',s.inventory.length>4],['business','Odbierz dochód firmy','Firma zarabia również wtedy, gdy nie jesteś zalogowany.',(s.completed.collected||0)>0]];
  dialog('Twoje pierwsze kroki',`<p>Świat <b>${esc(N.world.name)}</b> działa w tempie <b>×${N.world.speed}</b>. To przewodnik, nie płatna przepustka. Nie przyznaje dodatkowych premii do siły.</p><div class="tutorial-steps">${steps.map(([route,title,desc,done],i)=>`<button class="tutorial-step ${done?'done':''}" data-tutorial-go="${route}"><span>${done?icon('check'):i+1}</span><div><strong>${title}</strong><small>${desc}</small></div>${icon('arrow')}</button>`).join('')}</div><p class="tiny">Postęp samouczka jest wyliczany z działań zapisanych na serwerze. Możesz wracać do przewodnika z ekranu miasta.</p><div class="modal-actions"><button class="btn btn-gold" data-online="dismiss-tutorial">Rozumiem, ruszam do miasta</button></div>`);
 }
 N.cafeHTML=s=>Extras.venturesHTML(s);
 function panelHead(tag,title,text){return `<button class="hub-back" data-hub="city">⬅ Powrót do: Nadmorskie</button><div class="page-title game-page-title"><div><div class="eyebrow">${tag}</div><h1>${title}</h1><p class="lead">${text}</p></div><button class="btn" data-online="refresh-panel">${icon('replay')} Odśwież</button></div>`;}
 async function showRanking(season){
  if(playing)return toast('Najpierw zakończ animację.');
  if(!N.world)return showWorlds();
  const wid=N.world.id;
  const [data,g]=await Promise.all([api(`/worlds/${wid}/players`),api(`/ranking/global/${wid}`)]);
  const pick=(season!=null&&g.archive.includes(+season))?+season:0;
  const past=pick?await api(`/ranking/global/season/${pick}`):null;
  const chipsOf=r=>(r.titles||[]).map(t=>`<span class="title-chip">${esc(t)}</span>`).join('');
  const seasonRows=(pick?past.rows:g.rows).map((r,i)=>`<tr><td>${String(pick?r.place:i+1).padStart(2,'0')}</td><td><strong>${esc(r.nickname)}</strong>${r.tag?` <span class="own-tag">${esc(r.tag)}</span>`:''}${chipsOf(r)}</td>${pick?'':`<td>${esc(r.world)}</td>`}<td>${r.level}</td><td class="rating-value">${r.xp}</td></tr>`).join('')||'<tr><td colspan="5">Ten sezon jeszcze nie ma punktów.</td></tr>';
  const chips=[g.season,...g.archive.filter(x=>x!==g.season).sort((a,b)=>b-a)];
  const seasonPanel=`<section class="panel season-panel"><div class="panel-heading"><h2>Globalny ranking · sezony</h2><span class="tiny">PUNKTACJA: XP KARIERY</span></div>${g.me?`<p class="tiny season-me">Twoja pozycja globalna: <b>${g.me.place}</b> · ${g.me.xp} XP · poziom ${g.me.level} (${esc(g.me.world)})${g.me.titles&&g.me.titles.length?' · Tytuły: '+g.me.titles.map(t=>'<b>'+esc(t)+'</b>').join(', '):''}</p>`:''}<div class="season-chips">${chips.map(x=>`<button class="btn${x===pick?' btn-gold':''}" data-season="${x}">${x===g.season?'Sezon '+x+' · bieżący':'Sezon '+x}</button>`).join('')}</div><div class="ranking-table-wrap"><table class="ranking-table"><thead><tr><th>#</th><th>Postać</th>${pick?'':'<th>Świat</th>'}<th>Poziom</th><th>XP</th></tr></thead><tbody>${seasonRows}</tbody></table></div><p class="game-note">${icon('info')}${pick?`Archiwum sezonu ${pick}: połączenie TOP 10 każdego świata (${past.worlds} ${past.worlds===1?'świata':'światów'}).`:'Sezon trwa 28 dni i porządkuje wyłącznie rywalizację — postacie, majątek i organizacje nigdy się nie resetują. XP rośnie od kontraktów i treningu; niczego nie kupisz.'}</p></section>`;
  const html=panelHead(esc(N.world.name)+' · RYWALIZACJA',(['test','experimental'].includes(N.world.kind)?'Ranking testowego świata.':'Ranking Twojego świata.'),'Elo opisuje wyniki pojedynków w tym świecie. Niżej: globalny ranking sezonowy wszystkich światów według XP kariery.')+`<section class="panel"><div class="ranking-table-wrap"><table class="ranking-table"><thead><tr><th>#</th><th>Postać</th><th>Poziom</th><th>Elo</th><th>Wygrane</th><th>Porażki</th><th>Remisy</th></tr></thead><tbody>${data.players.map((p,i)=>`<tr class="${p.own?'own-row':''}"><td>${String(i+1).padStart(2,'0')}</td><td><strong>${esc(p.nickname)}</strong>${p.own?'<span class="own-tag">TY</span>':''}</td><td>${p.level}</td><td class="rating-value">${Math.round(p.rating)}</td><td>${p.wins}</td><td>${p.losses}</td><td>${p.draws}</td></tr>`).join('')}</tbody></table></div><p class="game-note">${icon('info')}Maksymalnie 5 rozliczonych walk na dobę UTC i jedna punktowana walka danej pary na 24 godziny. Startowe Elo: 1 000. Lista pokazuje do 200 postaci.</p></section>`+seasonPanel;
  if(GameApp.external('Ranking świata',html,'nav-ranking'))N.panel='ranking';
 }
 async function wardrobeHTML(){
  const cat=window.CityAvatar?.catalog;if(!cat)return '';
  const av=(N.packet?.state?.avatar)||{body:{},worn:{},owned:[]};
  const owned=new Set(av.owned||[]);const worn=av.worn||{};
  const vip=!!(N.packet?.shop?.vipActive||cat.vipActive);
  const secs=cat.cats.map(c=>{
   const tiles=cat.items[c.k].map(it=>{
    const has=owned.has(it.id);const locked=it.vip&&!vip;const on=worn[c.k]===it.id;
    let btn=on?'<button class="btn" disabled>Założona</button>':has?'<button class="btn" data-online="wardrobe-wear" data-item="'+it.id+'">Załóż</button>':locked?'<button class="btn" disabled title="Wymaga aktywnego VIP">👑 VIP</button>':'<button class="btn btn-gold" data-online="wardrobe-buy" data-item="'+it.id+'">Kup · '+it.p+' $</button>';
    return '<div class="av-tile shop-tile'+(on?' selected':'')+(it.vip?' is-vip':'')+'"><span class="av-swatch"><i style="background:'+it.c+'"></i><i style="background:'+it.c2+'"></i></span><b>'+esc(it.n)+'</b>'+(it.vip?'<span class="vip-tag">VIP</span>':'')+'<small>'+(on?'na sobie':has?'w szafie':it.p+' $')+'</small>'+btn+'</div>';
   }).join('');
   const openAny=Object.keys(worn).some(k=>k===c.k);
   return '<details class="wb-cat"'+(openAny?' open':'')+'><summary>'+c.icon+' '+esc(c.label)+' · 10</summary><div class="av-tiles">'+tiles+'</div></details>';
  }).join('');
  return '<section class="panel wardrobe-panel"><div class="panel-heading"><h2>Garderoba awatara</h2><span class="tiny">KOSMETYKA · 14 KATEGORII × 10 · 3×VIP W KAŻDEJ</span></div><p class="section-note">Rzeczy kupujesz za gotówkę z gry; 👑 wymaga aktywnego VIP. „Załóż” zmienia wygląd od razu — także na ekranie wyboru świata.</p><div class="wb-cats">'+secs+'</div></section>';
 }
 async function showShop(){
  if(playing)return toast('Najpierw zakończ animację.');
  await ensureAvatarCatalog();
  const data=await api('/shop');
  const s=data.state;
  const buy=(sku,price,label)=>`<button class="btn btn-gold" data-shop-buy="${sku}" data-price="${price}">${label||'Kup'}</button>`;
  const cards=data.products.map(p=>{
   let state='',btn='';
   if(p.kind==='vip'){const act=p.activeUntil&&p.activeUntil>Date.now();state=act?`<small class="shop-active">Aktywny do ${date(p.activeUntil)}</small>`:'';btn=buy(p.sku,p.price,act?'Przedłuż':'Kup');}
   else if(p.kind==='starter'){state=p.owned?'<small class="shop-owned">Posiadany · raz na konto</small>':`<small>Pojawi się na świecie: ${esc(N.world?.name||'—')}</small>`;btn=p.owned?'<button class="btn" disabled>Posiadany</button>':buy(p.sku,p.price);}
   else if(p.kind==='energy'){const en=Math.floor(N.packet?.state?.energy||0);const full=en>=240;const partial=!full&&en>=140;state=`<small>Dziś: ${p.usedToday} / ${p.limit} (UTC)</small>`;if(full)state+='<small class="shop-warn">Pełna energia (240/240) — zakup teraz przepadłby.</small>';else if(partial)state+=`<small class="shop-warn">Masz ${en} / 240 energii — część zakupu przepadnie.</small>`;btn=p.usedToday>=p.limit?'<button class="btn" disabled>Limit doby wyczerpany</button>':full?'<button class="btn" disabled>Pełna energia</button>':buy(p.sku,p.price);}
   else if(p.kind==='speedup'){state=`<small>Dziś: ${p.usedToday} / ${p.limit} (UTC)</small>`;btn=p.usedToday>=p.limit?'<button class="btn" disabled>Limit doby wyczerpany</button>':buy(p.sku,p.price);}
   else{state=p.owned?(p.equipped?'<small class="shop-active">Założona</small>':''):'<small>Dostępna w sklepie</small>';btn=p.owned?(p.equipped?'<button class="btn" disabled>Załóżona</button>':`<button class="btn" data-shop-equip="${p.sku}">Załóż</button>`):buy(p.sku,p.price);}
   return `<article class="shop-card"><div class="shop-card-head"><strong>${esc(p.name)}</strong><span class="price-tag">${esc(p.price)}</span></div><p>${esc(p.desc)}</p>${state}<div class="shop-card-actions">${btn}</div></article>`;}).join('');
  const guardianBox=s.guardian?`<div class="guardian-box"><div><span class="eyebrow">ZGODA OPIEKUNA · RODO ART. 8</span><strong>${esc(s.guardian.guardianName)} · limit ${Math.round(s.guardian.weeklyLimit/100)} zł / tydzień</strong><small>Wykorzystano w tym tygodniu: ${(s.guardian.weeklySpent/100).toFixed(2).replace('.',',')} zł</small></div><button class="text-btn" data-online="gc-revoke">Cofnij zgodę</button></div>`:'';
  const gate=`<section class="panel shop-gate"><div class="panel-heading"><h2>Dostęp do zakupów</h2>${s.spendingEnabled?'<span class="tiny shop-on">WŁĄCZONE</span>':'<span class="tiny">WYŁĄCZONE (domyślnie)</span>'}</div>${s.spendingEnabled?`<p class="section-note">Zakupy na tym koncie są włączone. Możesz je wyłączyć w każdej chwili.</p>${guardianBox}<button class="btn" data-shop-gate="0">Wyłącz zakupy</button>`:`<p class="section-note">${esc(data.gate)}</p><label class="check-field"><input type="checkbox" id="shop-statement"><span>Oświadczam, że wydatki w tej wersji są zgodne z wolą moją lub mojego opiekuna (RODO art. 8). Kasa pozorowana, bez prawdziwych płatności.</span></label><div class="shop-age-row"><label class="check-field"><input type="radio" name="shop-age" value="adult" checked><span>Mam ukończone 16 lat.</span></label><label class="check-field"><input type="radio" name="shop-age" value="minor"><span>Mam mniej niż 16 lat — włączam na podstawie zgody opiekuna.</span></label></div><div id="guardian-fields" hidden><label class="field" for="gc-name">Imię i nazwisko opiekuna</label><input id="gc-name" minlength="3" maxlength="60"><label class="field" for="gc-limit">Tygodniowy limit wydatków</label><select id="gc-limit"><option value="500">5 zł tygodniowo</option><option value="1000">10 zł tygodniowo</option><option value="2000">20 zł tygodniowo</option><option value="5000">50 zł tygodniowo</option></select><p class="tiny">Zgoda zapisuje się na koncie. Opiekun może ją cofnąć w każdej chwili — zakupy zostaną wtedy natychmiast wyłączone. Dane opiekuna służą wyłącznie tej zgodzie.</p></div><button class="btn btn-gold" data-shop-gate="1">Włącz zakupy na tym koncie</button>`}</section>`;
  const history=data.history.length?`<section class="panel shop-history"><h2>Ostatnie zamówienia (dev)</h2>${data.history.map(h=>`<div class="session-row"><div><strong>${esc(h.sku)}</strong><small>${date(h.created_at)}</small></div><span>${esc(h.price)} · ${esc(h.status)}</span></div>`).join('')}</section>`:'';
  const html=panelHead('SKLEP · WERSJA ROZWOJOWA','Oferta projektowa z cenami w złotych.','Kasa jest pozorowana: żadna prawdziwa płatność nie jest podłączona. W produkcji: Play Billing / Apple IAP.')+`<div class="shop-banner">${icon('info')}<div><strong>${esc(s.banner)}</strong></div></div>${gate}<div class="shop-grid">${cards}</div>${await wardrobeHTML()}${history}`;
  if(GameApp.external('Sklep (dev)',html,'nav-shop'))N.panel='shop';
 }
 N.chooseTactic=()=>N.chooseFightSetup();
 let editorPayload=null;
 N.avatarEditorPayload=()=>editorPayload?editorPayload():null;
 N.openAvatarEditor=async()=>{
  if(!N.world)return;
  await ensureAvatarCatalog();
  const cat=window.CityAvatar?.catalog;if(!cat)return;
  const cur=JSON.parse(JSON.stringify(N.packet?.state?.avatar||{body:{},worn:{},owned:[]}));
  let edBody={gender:'m',...(cur.body||{})},edWorn={...(cur.worn||{})};
  const CATS2=[{k:'body',label:'Ciało',icon:'🧍'}].concat(cat.cats);
  function edTiles(){
   const box=document.getElementById('ac-tiles');if(!box)return;
   if(edTab==='body'){
    const sw=(arr,key)=>arr.map((v,i)=>`<button type="button" class="av-tile swatch ${edBody[key]===i?'selected':''}" data-body="${key}" data-i="${i}"><span class="sw" style="background:${/^#/.test(v)?v:'transparent'}"></span>${/^#/.test(v)?'':esc(v)}</button>`).join('');
    box.innerHTML='<p class="tiny">Płeć sylwetki</p><div class="sw-row">'+'<button type="button" class="av-tile swatch gen-b'+(edBody.gender!=='k'?' selected':'')+'" data-gender="m">👨 Mężczyzna</button>'+'<button type="button" class="av-tile swatch gen-b'+(edBody.gender==='k'?' selected':'')+'" data-gender="k">👩 Kobieta</button></div>'+'<p class="tiny">Karnacja</p><div class="sw-row">'+sw(cat.bodies.skins,'skin')+'</div><p class="tiny">Włosy</p><div class="sw-row">'+cat.bodies.hairs.map((h,i)=>`<button type="button" class="av-tile swatch ${edBody.hair===i?'selected':''}" data-body="hair" data-i="${i}">${esc(h)}</button>`).join('')+'</div><p class="tiny">Kolor włosów</p><div class="sw-row">'+sw(cat.bodies.hairColors,'hairColor')+'</div>';
   }else{
    box.innerHTML=cat.items[edTab].map(it=>{const on=edWorn[edTab]===it.id;const locked=it.vip&&!cat.vipActive&&!N.packet?.shop?.vipActive;
     return `<button type="button" class="av-tile ${on?'selected':''} ${it.vip?'is-vip':''}" data-item="${it.id}" ${locked?'data-locked="1"':''}><span class="av-swatch"><i style="background:${it.c}"></i><i style="background:${it.c2}"></i></span><b>${esc(it.n)}</b><small>${it.vip?'👑 VIP':(on?'założona':(cur.owned||[]).includes(it.id)?'w szafie':it.p+' $ — kupisz w Sklepie')}</small></button>`;}).join('');
   }
  }
  let edTab='body';
  function edRender(){
   const box=document.getElementById('ac-preview-box');if(box&&window.CityAvatar)window.CityAvatar.mount(box,{body:edBody,worn:edWorn},{animate:true});
   const tabs=document.getElementById('ac-tabs');
   if(tabs)tabs.innerHTML=CATS2.map(c=>`<button type="button" class="av-tab ${edTab===c.k?'active':''}" data-tab="${c.k}">${c.icon} ${esc(c.label)}</button>`).join('');
   edTiles();
   const root=document.getElementById('avatar-creator');
   const rnd=document.getElementById('ac-random');
   if(rnd)rnd.onclick=()=>{const cfg=window.CityAvatar.random(!!(N.packet?.shop?.vipActive||cat.vipActive));edBody=cfg.body;edWorn=cfg.worn;edRender();};
   if(root)root.onclick=e=>{
    if(e.target.id==='ac-random')return;
    const t=e.target.closest('button');if(!t)return;
    if(t.dataset.tab){edTab=t.dataset.tab;edRender();return;}
    if(t.dataset.gender){edBody.gender=t.dataset.gender;edRender();return;}
     if(t.dataset.body){edBody[t.dataset.body]=+t.dataset.i;edRender();return;}
    if(t.dataset.item){
     const it=window.CityAvatar.item(t.dataset.item);if(!it)return;
     if(t.dataset.locked){toast('Rzeczy VIP odblokujesz aktywnym VIP w Sklepie.');return;}
     if(!((cur.owned||[]).includes(it.id))){toast('Najpierw kup „'+it.n+'” w Sklepie (sekcja Garderoba).');return;}
     const SLOT_OF={cap:'head',hat:'head',pants:'legs',shorts:'legs'};
     if(edWorn[it.k]===it.id)delete edWorn[it.k];
     else{
      const slot=SLOT_OF[it.k];let conflict=null;
      if(slot)for(const k2 of Object.keys(edWorn))if(k2!==it.k&&SLOT_OF[k2]===slot)conflict=k2;
      if(conflict){const lb=k=>(window.CityAvatar&&CityAvatar.cats().find(c=>c.k===k)||{}).label||k;toast('Nie można nosić jednocześnie: zdejmij „'+lb(conflict)+'”, żeby założyć „'+lb(it.k)+'”.');return;}
      edWorn[it.k]=it.id;
     }
     edRender();
    }
   };
  }
  editorPayload=()=>({body:{...edBody},worn:{...edWorn}});
  dialog('Edytuj awatara · '+ (N.character?.nickname||'postać'),`<div class="avatar-creator" id="avatar-creator"><div class="ac-preview"><div id="ac-preview-box"></div><p class="tiny">Podgląd na żywo — wygląd zobaczysz też na wyborze światów i w PvP.</p><button type="button" class="btn" id="ac-random">🎲 Losuj</button></div><div class="ac-options"><p class="section-note">Zmieniasz wyłącznie wygląd. Nowych rzeczy szukaj w <b>Sklepie → Garderoba awatara</b>.</p><div class="av-tabs" id="ac-tabs"></div><div class="av-tiles" id="ac-tiles"></div><button class="btn btn-gold full-width" style="margin-top:12px" id="av-editor-save">Zapisz wygląd</button></div></div>`);
  edRender();
  $('#av-editor-save').onclick=async ev=>{
   ev.preventDefault();
   try{const r=await api('/worlds/'+N.world.id+'/avatar','POST',{avatar:{body:edBody,worn:edWorn}});install(await api('/worlds/'+N.world.id+'/state'));$('#network-dialog').close();toast(r.message||'Wygląd zapisany.');}catch(e){toast(e.message);}
  };
 };
 N.chooseFightSetup=()=>new Promise(res=>{
  const needClass=!N.character?.classType,needTac=!N.character?.tactic;
  if(!needClass&&!needTac){res(true);return;}
  const clsCards=[['bokser','🥊','Bokser','Siła 14 · Int 8 · Refleks 10 · Charyzma 10 · Spryt 8','Pasywka: mocniejszy cios'],['obronca','🛡️','Obrońca','Siła 8 · Int 14 · Refleks 8 · Charyzma 12 · Spryt 8','Pasywka: kontratak po uniku'],['szybki','⚡','Szybki','Siła 8 · Int 8 · Refleks 14 · Charyzma 8 · Spryt 12','Pasywka: inicjatywa +3']].map(([k,ic,nm,sts,pas])=>`<label class="class-card"><input type="radio" name="class-choice" value="${k}" ${needClass?'required':''}><span class="class-icon">${ic}</span><b>${nm}</b><span class="class-stats">${sts}</span><span class="class-passive">${pas}</span></label>`).join('');
  const tacCards=[['presja','⚡','Przełamujesz kontrolę — +8% obrażeń przeciw Kontroli.'],['kontrola','🛡️','Neutralizujesz kontry — +8% obrażeń przeciw Kontrze.'],['kontra','🎯','Wykorzystujesz presję — +8% obrażeń przeciw Presji.']].map(([k,ic,desc])=>`<label class="class-card"><input type="radio" name="tactic-choice" value="${k}"><span class="class-icon">${ic}</span><b>${k[0].toUpperCase()+k.slice(1)}</b><span class="class-passive">${desc}</span></label>`).join('');
  const clsSec=needClass?`<p class="section-note">01 / KARTA ZAWODNIKA · klasa <b>jednorazowa i nieodwracalna</b> — określa statystyki startowe i pasywkę w ringu.</p><div class="class-cards" role="radiogroup" aria-label="Klasa postaci">${clsCards}</div>`:'';
  const tacSec=needTac?`<p class="section-note">02 / TAKTYKA · wybór <b>jednorazowy i nieodwracalny</b> — obowiązuje w każdym pojedynku PvP i na każdym piętrze Lochu.</p><div class="class-cards" role="radiogroup" aria-label="Taktyka walki">${tacCards}</div><p class="tiny">Przewaga taktyczna: +8% obrażeń, gdy Twoja taktyka pokonuje taktykę rywala (Presja → Kontrola → Kontra → Presja).</p>`:'';
  dialog('Twoja karta zawodnika.',`${clsSec}${tacSec}<button class="btn btn-gold full-width" style="margin-top:.6rem" id="tactic-confirm" disabled>${needClass&&needTac?'Wydaj kartę i walcz':'Potwierdź'}</button>`);
  const body=$('#network-dialog-body');
  const check=()=>{$('#tactic-confirm').disabled=!((needClass?body.querySelector('input[name=class-choice]:checked'):true)&&(needTac?body.querySelector('input[name=tactic-choice]:checked'):true));};
  body.querySelectorAll('input[name=class-choice],input[name=tactic-choice]').forEach(r=>r.onchange=check);check();
  $('#tactic-confirm').onclick=async()=>{const b=$('#tactic-confirm');b.disabled=true;
   try{
    if(needClass){const cv=body.querySelector('input[name=class-choice]:checked');const rc=await api(`/worlds/${N.world.id}/class`,'POST',{class_type:cv.value});N.character.classType=rc.classType;}
    if(needTac){const tv=body.querySelector('input[name=tactic-choice]:checked');const rt=await api(`/worlds/${N.world.id}/tactic`,'POST',{style:tv.value});N.character.tactic=rt.tactic;}
    $('#network-dialog').close();toast('Karta zawodnika gotowa — powodzenia na ringu!');res(true);
   }catch(e){b.disabled=false;error(e);}
  };
 });
 async function renderPvpPane(){
  const mount=document.getElementById('pvp-mount');if(!mount)return;
  if(playing)return toast('Najpierw zakończ animację.');if(!N.world)return showWorlds();
  // 0.41: PvP od 2. poziomu; przed pierwszym wejściem — jednorazowy wybór taktyki
  if(GameApp.level(GameApp.state.xp)<2){const lock=panelHead(esc(N.world.name)+' · WYZWANIA PvP','Ring czeka na doświadczonych.','Wyzwania PvP odblokowują się na 2. poziomie — zdobywaj XP w kontraktach i w Lochu.')+`<section class="panel"><p class="section-note">🔒 Masz poziom ${GameApp.level(GameApp.state.xp)} — potrzeba poziomu 2.</p><p class="tiny">Ranking i pojedynki nikogo nie kosztują: bez utraty pieniędzy i przedmiotów.</p></section>`;mount.innerHTML=lock;N.panel='pvp';return;}
  if(!N.character?.tactic||!N.character?.classType){const ok=await N.chooseTactic();if(!ok)return;}
  const [pvp,players]=await Promise.all([api(`/worlds/${N.world.id}/pvp`),api(`/worlds/${N.world.id}/players`)]);
  const opponents=players.players.filter(p=>!p.own);N.myOrg=pvp.myOrg||null;
    const tacName={presja:'Presja',kontrola:'Kontrola',kontra:'Kontra'}[N.character?.tactic]||'—';
  const html=panelHead(esc(N.world.name)+' · WYZWANIA PvP','Atakuj, pisz, zapraszaj do gildii — przeciwnicy prosto z rankingu.','Pojedynek rozstrzygają zapisane taktyki oboje graczy. Nie musicie być online jednocześnie. ⚡ Auto-atak rozstrzyga się od razu — obrońcę reprezentuje jego zapisana taktyka. PvP od 2. poziomu.')+`<div class="pvp-summary"><span>${icon('shield')}Dobrowolna rywalizacja</span><span>${icon('trophy')}Dzisiaj: ${pvp.daily_used} / 5 walk UTC</span><span>Bez utraty pieniędzy i przedmiotów</span></div><div class="pvp-columns"><section class="panel"><div class="panel-heading"><h2>Gracze na tym świecie</h2><span class="tiny">${opponents.length} RYWALI</span></div><p class="section-note">🥊 Klasa: <b>${({bokser:'Bokser',obronca:'Obrońca',szybki:'Szybki'})[N.character?.classType]||'—'}</b> · ⚔️ Taktyka: <b>${tacName}</b> <span class="tiny">(wybór jednorazowy — wygląda tak samo dla Twoich przeciwników, gdy przyjmują Twoje wyzwania... i gdy Ty przyjmujesz ich wyzwania)</span></p>${opponents.length?opponents.map((p,i)=>`<div class="opponent-row"><span class="opponent-avatar" data-pvp-av="${p.id}">${window.CityAvatar&&p.avatar?'':esc(p.nickname.slice(0,1).toUpperCase())}</span><div><strong>#${i+1} rankingu · ${esc(p.nickname)}</strong><small>Poziom ${p.level} · ${Math.round(p.rating)} Elo</small></div><div class="row-actions"><button class="btn btn-gold" data-attack="${p.id}" ${pvp.daily_used>=5?'disabled':''} title="Auto-atak: natychmiastowy pojedynek rankingowy — obrońcę reprezentuje jego zapisana taktyka.">⚡ Atakuj</button><button class="btn" data-dm-open="${p.id}" title="Napisz wiadomość do ${esc(p.nickname)}">💬 Napisz</button>${N.myOrg&&N.myOrg.canInvite?`<button class="btn" data-org-invite="${p.id}" title="Zaproś do ${esc(N.myOrg.name)} [${esc(N.myOrg.tag)}]">🛡️ Gildia</button>`:''}</div></div>`).join(''):`<div class="game-empty">${icon('person')}<strong>Jeszcze nie ma innych graczy.</strong><p>Drugi gracz musi założyć konto i postać na tym samym świecie. Do testu możesz użyć osobnego okna prywatnego.</p></div>`}</section><section class="panel match-history"><div class="panel-heading"><h2>Zapisane pojedynki</h2><span class="tiny">OSTATNIE 30</span></div>${pvp.matches.length?pvp.matches.map(m=>`<div class="match-row"><div><strong>${esc(m.attacker_name)} <span>vs</span> ${esc(m.defender_name)}</strong><small>${date(m.created_at)}</small></div><button class="btn" data-match="${m.id}">${icon('play')} Odtwórz raport</button></div>`).join(''):'<p class="section-note">Pierwszy raport pojawi się po pierwszym Auto-ataku.</p>'}</section>`;
  mount.innerHTML=html;N.panel='pvp';
  if(window.CityAvatar)document.querySelectorAll('[data-pvp-av]').forEach(el=>{const t=opponents.find(x=>x.id===+el.dataset.pvpAv);if(t&&t.avatar)window.CityAvatar.mount(el,t.avatar,{animate:true});});
 }
 async function showPvp(){GameApp.clubPane('pvp');}
 N.renderPvpPane=()=>guarded(renderPvpPane);
 N.showPvp=showPvp;
 function ecAdminChart(rows){
 const data=(rows||[]).slice().reverse();
 if(!data.length||!data.some(r=>r.deeds||r.cash||r.shop_cents))return '<p class="section-note">Brak aktywności w ostatnich 14 dniach.</p>';
 const maxD=Math.max.apply(null,data.map(r=>r.deeds).concat([1]));
 const maxS=Math.max.apply(null,data.map(r=>r.shop_cents).concat([1]));
 const w=20;let bars='';
 data.forEach((r,i)=>{const x=i*w;const hd=Math.round(30*r.deeds/maxD);const hs=Math.round(30*r.shop_cents/maxS);
  bars+='<g><title>'+new Date(r.day).toLocaleDateString('pl-PL',{day:'2-digit',month:'2-digit'})+' · czyny: '+r.deeds+' · gotówka: '+r.cash.toLocaleString('pl-PL')+' $ · XP: '+r.xp+' · dev-sklep: '+(r.shop_cents/100).toFixed(2).replace('.',',')+' zł</title>';
  bars+='<rect class="dc-deeds" x="'+(x+2)+'" y="'+(32-hd)+'" width="7" height="'+Math.max(hd,r.deeds?2:0)+'" rx="2"></rect>';
  bars+='<rect class="dc-shop" x="'+(x+11)+'" y="'+(32-hs)+'" width="7" height="'+Math.max(hs,r.shop_cents?2:0)+'" rx="2"></rect></g>';
 });
 return '<div class="daily-chart"><div class="dc-head"><span>OSTATNIE 14 DNI</span><span class="dc-legend"><i class="lg-deeds"></i>czyny <i class="lg-shop"></i>dev-sklep</span></div><svg viewBox="0 0 '+Math.max(data.length*w,40)+' 34" preserveAspectRatio="none" role="img" aria-label="Agregaty świata z 14 dni">'+bars+'</svg></div>';
}
async function showAdmin(){
  if(playing)return toast('Najpierw zakończ animację.');
  const data=await api('/admin/overview');adminCache=data;
  const html=panelHead('PANEL ADMINISTRATORA','Zarządzaj światami.','Otwarcia, rejestracja, komunikaty i moderacja. Każda zmiana trafia do dziennika administratora.')+`<div class="account-actions"><button class="btn" data-extra="reports">Zgłoszenia i odwołania</button><button class="btn" data-extra="backups">Kopie zapasowe</button><button class="btn" data-online="post-notice">Nowe ogłoszenie</button><button class="btn btn-gold" data-online="city-event">Event miejski</button></div><div class="admin-stats"><span><b>${data.worlds.length}</b> światy</span><span><b>${data.accounts.length}</b> ostatnich kont</span><span><b>${data.audit.length}</b> ostatnich zdarzeń</span></div><section class="panel"><div class="panel-heading"><h2>Światy</h2><button class="btn btn-gold" data-online="create-world">+ Nowy świat</button></div><div class="admin-world-list">${data.worlds.map(w=>`<article class="admin-world"><div><strong>${esc(w.name)}</strong><small>${kindName[w.kind]} · ×${w.speed} · ${w.population} postaci</small><small>Otwarcie: ${date(w.opens_at)}</small></div><div class="admin-world-controls"><button class="btn" data-reg-world="${w.id}" data-open="${w.registration_open?0:1}">${w.registration_open?'Zamknij rejestrację':'Otwórz rejestrację'}</button><button class="btn" data-maint-world="${w.id}" data-maint="${w.maintenance?0:1}">${w.maintenance?'Zakończ przerwę':'Przerwa techniczna'}</button><button class="text-btn" data-wsummary="${w.id}">Podsumowanie</button><button class="text-btn" data-announcement="${w.id}">Komunikat</button></div></article>`).join('')}</div></section><section class="panel admin-accounts"><h2>Konta i moderacja</h2><p class="section-note">Maksymalnie 100 ostatnich kont. Ten panel nie zmienia ról administratorów.</p>${data.accounts.map(a=>`<div class="opponent-row"><div><strong>${esc(a.username)}</strong><small>${a.role==='admin'?'Administrator':a.banned?'Konto zawieszone':'Gracz'} · ${date(a.created_at)}</small></div>${a.role==='admin'?'<span class="own-tag">ADMIN</span>':`<button class="btn ${a.banned?'':'danger-btn'}" data-ban="${a.id}" data-banned="${a.banned?0:1}">${a.banned?'Odblokuj':'Zawieś'}</button><button class="text-btn" data-mod="${a.id}" data-on="${a.role==='moderator'?0:1}">${a.role==='moderator'?'Odbierz moderatora':'Mianuj moderatora'}</button>`}</div>`).join('')}</section><section class="panel admin-events-panel"><h2>Eventy miejskie</h2><p class="section-note">Wspólny cel całego świata. Nagroda: odznaka Pioniera dla mieszkańców (czysto kosmetyczna).</p>${data.events.length?data.events.map(e=>`<div class="session-row"><div><strong>${esc(e.name)}</strong><small>${esc(e.kind==='xp'?'XP miasta':'prestiż · '+(e.district||'—'))} · cel ${e.target}</small></div><span class="tiny">${e.status==='active'?`aktywny · ${e.progress}/${e.target} · do ${date(e.deadline)}`:{done:'zaliczony ✓',missed:'wygasł',cancelled:'anulowany'}[e.status]||e.status}</span>${e.status==='active'?`<button class="text-btn" data-ce-cancel="${e.id}">Zakończ</button>`:''}</div>`).join(''):'<p class="section-note">Brak eventów — ustaw pierwszy wspólny cel miasta.</p>'}</section><section class="panel admin-notices-panel"><h2>Tablica ogłoszeń</h2><p class="section-note">Ogłoszenia widać w Społeczności i w banerze gry; znikają po 7 dniach. Zasięg: wszystkie światy albo jeden świat.</p>${data.notices.length?data.notices.map(n=>`<div class="session-row"><div><strong>${esc(n.text)}</strong><small>${n.world_id?(data.worlds.find(w=>w.id===n.world_id)?.name||'świat #'+n.world_id):'wszystkie światy'} · ${date(n.created_at)}</small></div><button class="text-btn" data-notice-del="${n.id}">Usuń</button></div>`).join(''):'<p class="section-note">Brak ogłoszeń — opublikuj pierwsze przyciskiem „Nowe ogłoszenie”.</p>'}</section><section class="panel audit-panel"><h2>Dziennik działań</h2>${data.audit.length?data.audit.slice(0,30).map(a=>`<div class="audit-row"><span>${date(a.created_at)}</span><div><strong>${esc(a.event)}</strong><code>${esc(a.details)}</code></div><small>konto #${a.actor_id??'usunięte'}</small></div>`).join(''):'<p class="section-note">Brak zdarzeń.</p>'}</section>`;
  if(GameApp.external('Administracja',html,'nav-admin'))N.panel='admin';
 }
 async function showAccount(){
  const [setup,security]=await Promise.all([api('/setup/status'),api('/account/security')]);
  const scheduled=!!N.user.deletion_at;
  dialog('Twoje konto',`<div class="account-identity">${icon('person')}<div><strong>${esc(N.user.username)}</strong><span>${N.user.role==='admin'?'Administrator':N.user.role==='moderator'?'Moderator':'Gracz'} · jedno konto na wszystkie światy${N.packet?.shop?.vipActive?` · <b>VIP</b> do ${date(N.packet.shop.vipUntil)} (dev)`:''}${N.packet?.shop?.skin?` · skórka: ${N.packet.shop.skin.replace('skin_','')}`:''}</span></div></div>${scheduled?`<div class="deletion-warning"><strong>Usunięcie konta zaplanowane na ${date(N.user.deletion_at)}.</strong><span>Do tej daty dane są jeszcze przechowywane. Możesz cofnąć decyzję hasłem.</span><form id="cancel-delete-form"><input id="cancel-password" type="password" autocomplete="current-password" required placeholder="Potwierdź hasłem"><button class="btn" type="submit">Anuluj usunięcie konta</button></form></div>`:''}<p>Dane postaci są zapisane w bazie serwera. Nie ma importowania pieniędzy, statystyk ani lokalnych zapisów z poprzedniego prototypu.</p><div class="account-actions"><button class="btn" data-online="export-account">${icon('download')} Eksport danych JSON</button><button class="btn" data-online="worlds">Zmień świat</button><button class="btn" data-online="logout">Wyloguj</button></div>${Extras.securityHTML(security)}${setup.needsAdmin?`<section class="setup-section"><h3>Aktywacja administratora</h3><p>Jednorazowy kod instalacyjny otrzymuje właściciel projektu. Rejestracja zwykłego konta nie nadaje uprawnień administracyjnych.</p><form id="bootstrap-form"><label class="field" for="bootstrap-code">Kod instalacyjny</label><input id="bootstrap-code" type="password" required minlength="10" autocomplete="off"><button class="btn" type="submit">Aktywuj administratora</button></form></section>`:''}<details class="delete-account"><summary>Usunięcie konta i postaci</summary><p>Konto natychmiast przestaje być dostępne (wylogowanie, blokada logowania), a dane wszystkich postaci, wiadomości i raportów trwale opuszczają bazę po 7 dniach karencji. Lider organizacji z członkami musi najpierw przekazać rolę. Do momentu wygaśnięcia karencji możesz cofnąć decyzję hasłem. Najpierw możesz pobrać eksport.</p><form id="delete-account-form"><label class="field" for="delete-password">Potwierdź hasłem</label><input id="delete-password" type="password" autocomplete="current-password" required><label class="check-field"><input type="checkbox" required><span>Rozumiem karencję 7 dni i ostateczne usunięcie danych.</span></label><button class="btn danger-btn" type="submit">${scheduled?'Karencja już trwa':'Zaplanuj usunięcie konta (7 dni)'}</button></form></details><p class="account-disclaimer">Wersja rozwojowa. Panel nie zastępuje kompletnego regulaminu, polityki prywatności, procedur retencji i audytu zgodności przed publikacją.</p>`);
 }
 N.showAccount=()=>guarded(showAccount);
 function worldForm(){dialog('Utwórz nowy świat',`<form id="new-world-form"><label class="field" for="world-name">Nazwa świata</label><input id="world-name" required minlength="3" maxlength="40" placeholder="np. CITY 2"><div class="fields-row"><div><label class="field" for="world-kind">Rodzaj</label><select id="world-kind"><option value="standard">Standardowy</option><option value="event">Eventowy</option><option value="test">Testowy</option><option value="experimental">Eksperymentalny</option></select></div><div><label class="field" for="world-speed">Tempo czasu · standardowy tylko ×1</label><input id="world-speed" type="number" min="1" max="60" value="1" required></div></div><label class="field" for="world-opens">Termin otwarcia · puste = teraz</label><input id="world-opens" type="datetime-local"><label class="check-field"><input id="world-registration" type="checkbox" checked><span>Otwarta rejestracja po uruchomieniu</span></label><label class="field" for="world-announce">Ogłoszenie na liście światów · opcjonalne</label><textarea id="world-announce" maxlength="500" rows="3" placeholder="np. Otwarcie świata: darmowa waluta startowa dla wczesnych rejestracji."></textarea><p class="section-note">Stare światy nie zostaną zamknięte. Rodzaj i tempo tego świata pozostaną stałe w tym etapie projektu.</p><button class="btn btn-gold full-width" type="submit">Utwórz świat</button></form>`);}
 const CLS_L={bokser:'Bokser',obronca:'Obrońca',szybki:'Szybki'};
 async function showProfile(){
  let d;
  try{d=await api('/account/profile','GET');}catch(e){toast(e.message||'Profil niedostępny.');return;}
  const cards=d.characters.map(ch=>{
   const lvl=ch.level,pct=Math.max(0,Math.min(100,Math.round(100*(ch.xp-ch.xpBase)/Math.max(1,ch.xpNext-ch.xpBase))));
   const chips=ch.titles.slice(0,6).map(t=>'<span class="prof-chip">'+esc(t)+'</span>').join('')+(ch.titlesTotal>6?'<span class="prof-chip more">+'+(ch.titlesTotal-6)+' więcej</span>':'');
   return '<section class="panel prof-card"><div class="prof-head"><span class="prof-av" data-prof-av="'+ch.worldId+'"></span><div class="prof-id"><b>👤 '+esc(ch.nickname)+'</b><span>'+esc(ch.world)+(ch.kind==='test'?' · świat testowy':'')+'</span></div>'
    +'<div class="prof-grid">'
    +'<div><small>POZIOM</small><b>'+lvl+'</b></div>'
    +'<div><small>XP KARIERY</small><b>'+ch.xp.toLocaleString('pl-PL')+'</b></div>'
    +'<div><small>KLASA</small><b>'+(ch.clas?(CLS_L[ch.clas]||esc(ch.clas)):'— wybierzesz przy 1. PvP')+'</b></div>'
    +'<div><small>EWOLUCJA</small><b>'+(ch.evolution?esc(String(ch.evolution).replace(/-/g,' ')):'—')+'</b></div>'
    +'<div><small>ELO</small><b>'+Math.round(ch.rating)+'</b></div>'
    +'<div><small>BILANS PvP</small><b>'+ch.wins+' / '+ch.losses+' / '+ch.draws+'</b></div>'
    +'<div><small>LOCH</small><b>'+ch.dungeon+'%</b></div>'
    +'<div><small>CZYNNY DZIEŃ</small><b>'+ch.deeds+'</b></div>'
    +'</div><div class="xp-track"><span style="width:'+pct+'%"></span></div>'
    +'<div class="prof-titles"><small>TYTUŁY I OSIĄGNIĘCIA ('+ch.titlesTotal+')</small>'+(ch.titlesTotal?chips:'<em class="prof-empty">Brak — tytuły sezonowe zdobędziesz w globalnym rankingu.</em>')+'</div></section>';
  }).join('');
  dialog('Profil · '+d.username,'<p class="section-note">Osiągnięcia ze wszystkich Twoich światów — widoczne także przed wejściem do gry. Kliknij „Wejdź do postaci”, aby kontynuować przygodę.</p>'+(cards||'<p class="section-note">Nie masz jeszcze żadnej postaci — wybierz świat i stwórz pierwszą.</p>'));
  await ensureAvatarCatalog();
  if(window.CityAvatar)document.querySelectorAll('[data-prof-av]').forEach(el=>{const ch=d.characters.find(c=>c.worldId===+el.dataset.profAv);if(ch&&ch.avatar)window.CityAvatar.mount(el,ch.avatar,{animate:true});});
 }
 async function showAccountRankings(){
  let d;
  try{d=await api('/account/rankings','GET');}catch(e){toast(e.message||'Ranking niedostępny.');return;}
  const num=v=>Number(v||0).toLocaleString('pl-PL');
  const wrows=d.worlds.map(w=>'<section class="panel rank-card"><div class="prof-head"><b>🏛️ '+esc(w.world)+'</b><span>Twoja pozycja: <b>'+w.place+'</b> · '+num(w.xp)+' XP · '+esc(w.nickname)+'</span></div><div class="ranking-table-wrap"><table class="ranking-table"><thead><tr><th>#</th><th>Postać</th><th>Poziom</th><th>XP</th></tr></thead><tbody>'+w.top.map(r=>'<tr'+(r.nickname===w.nickname?' class="own-row"':'')+'><td>'+String(r.place).padStart(2,'0')+'</td><td><strong>'+esc(r.nickname)+'</strong>'+(r.nickname===w.nickname?'<span class="own-tag">TY</span>':'')+'</td><td>'+r.level+'</td><td class="rating-value">'+num(r.xp)+'</td></tr>').join('')||'<tr><td colspan="4">Ten świat jeszcze nie ma punktów.</td></tr>'+'</tbody></table></div></section>').join('');
  const g='<section class="panel season-panel"><div class="panel-heading"><h2>Globalny ranking · sezon '+d.season+'</h2><span class="tiny">PUNKTACJA: XP KARIERY</span></div>'+(d.myGlobal?'<p class="tiny season-me">Twoja najlepsza pozycja globalna: <b>'+d.myGlobal.place+'</b> · '+esc(d.myGlobal.nickname)+' ('+esc(d.myGlobal.world)+') · '+num(d.myGlobal.xp)+' XP</p>':'')+'<div class="ranking-table-wrap"><table class="ranking-table"><thead><tr><th>#</th><th>Postać</th><th>Świat</th><th>Poziom</th><th>XP</th></tr></thead><tbody>'+(d.globalTop.map(r=>'<tr><td>'+String(r.place).padStart(2,'0')+'</td><td><strong>'+esc(r.nickname)+'</strong></td><td>'+esc(r.world)+'</td><td>'+r.level+'</td><td class="rating-value">'+num(r.xp)+'</td></tr>').join('')||'<tr><td colspan="5">Ten sezon jeszcze nie ma punktów.</td></tr>')+'</tbody></table></div><p class="tiny">Podgląd przed wejściem do gry. Pełne rankingi (Elo, archiwa sezonów) czekają w grze.</p></section>';
  dialog('Ranking · Twoje światy i globalny','<p class="section-note">Wyniki Twoich światów oraz globalny sezon — widoczne także przed wejściem do gry.</p>'+g+wrows);
 }
 async function logout(){authMode='login';await api('/auth/logout','POST',{});storePreviewToken('');N.user=null;N.csrf='';N.character=null;N.world=null;N.generation++;$('#network-dialog').close();try{sessionStorage.removeItem('cityEmpireOnlineWorld');}catch{}showAuth();}
 function download(data,filename){const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 async function refreshPanel(){if(N.panel==='admin')await showAdmin();else if(N.panel==='pvp')await showPvp();else if(N.panel==='ranking')await showRanking();else if(N.panel==='shop')await showShop();}
 async function worldNews(){
  if(!N.user||!N.world||!$('#network-cover').hidden)return;
  try{const data=await api('/worlds');let seen=0;try{seen=Number(sessionStorage.getItem('cityWorldsSeen:'+N.user.id))||0;}catch{}const fresh=data.worlds.filter(w=>w.id!==N.world.id&&w.created_at>seen);const el=$('#world-news');if(fresh.length){el.innerHTML=icon('city')+'<span><strong>Nowy świat: '+esc(fresh[fresh.length-1].name)+'</strong> · Otwarcie '+date(fresh[fresh.length-1].opens_at)+'</span><button class="text-btn" data-online="worlds">Zobacz światy '+icon('arrow')+'</button>';el.hidden=false;}else el.hidden=true;}catch{}
 }
 N.init=async()=>{
  document.body.classList.add('network-gated');$('#network-dialog-close').onclick=()=>$('#network-dialog').close();
  $('#nav-worlds').onclick=N.showWorlds;$('#nav-shop').onclick=()=>guarded(showShop);$('#nav-ranking').onclick=()=>guarded(showRanking);$('#nav-admin').onclick=()=>guarded(showAdmin);
  document.addEventListener('change',e=>{if(e.target?.name!=='shop-age')return;const gf=document.getElementById('guardian-fields');if(gf)gf.hidden=e.target.value!=='minor';});
 document.addEventListener('submit',e=>{
   const form=e.target;if(!['auth-form','character-form','bootstrap-form','new-world-form','announcement-form','delete-account-form','cancel-delete-form','notice-form','city-event-form'].includes(form.id))return;e.preventDefault();
   if(form.id==='auth-form'){authenticate(form);return;}
   guarded(async()=>{
    const submit=form.querySelector('[type=submit]');submit.disabled=true;
    try{
     if(form.id==='character-form'){
      const id=+form.dataset.worldId;
      try{const payload={nickname:$('#character-nickname').value.trim(),accept_test_reset:!!$('#test-consent')?.checked,class_type:null};if(creatorPayload)payload.avatar=creatorPayload();const response=await api(`/worlds/${id}/character`,'POST',payload);creatorPayload=null;await loadWorld(id,response);}catch(e){$('#character-error').textContent=e.message;}
     }else if(form.id==='bootstrap-form'){
      await api('/setup/claim','POST',{code:$('#bootstrap-code').value});const me=await api('/me');setUser(me.user,me.csrf);$('#network-dialog').close();toast('Uprawnienia administratora aktywowane.');if(N.world)await showAdmin();else await showWorlds();
     }else if(form.id==='new-world-form'){
      const value=$('#world-opens').value;const created=await api('/admin/worlds','POST',{name:$('#world-name').value.trim(),kind:$('#world-kind').value,speed:+$('#world-speed').value,opens_at:value?new Date(value).getTime():null,registration_open:$('#world-registration').checked});
      if($('#world-announce')&&$('#world-announce').value.trim())await api('/admin/worlds/'+created.id,'PATCH',{announcement:$('#world-announce').value.trim()});
      $('#network-dialog').close();await showAdmin();toast('Świat został utworzony.');
     }else if(form.id==='city-event-form'){
      const kind=$('#ce-kind').value;
      await api('/admin/events','POST',{world_id:+$('#ce-world').value,name:$('#ce-name').value,description:$('#ce-desc').value,kind,district:kind==='prestige'?$('#ce-district').value:'',target:+$('#ce-target').value,hours:+$('#ce-hours').value});
      $('#network-dialog').close();await showAdmin();toast('Event miejski uruchomiony — miasto dostanie powiadomienie.');
    }else if(form.id==='announcement-form'){
      await api(`/admin/worlds/${form.dataset.worldId}`,'PATCH',{announcement:$('#world-announcement').value});$('#network-dialog').close();await showAdmin();toast('Komunikat opublikowany.');
     }else if(form.id==='cancel-delete-form'){
      await api('/account/delete/cancel','POST',{password:$('#cancel-password').value});const me=await api('/me');setUser(me.user,me.csrf);$('#network-dialog').close();toast('Usunięcie konta zostało anulowane.');
     }else if(form.id==='notice-form'){
      const sel=$('#notice-world').value;await api('/admin/notices','POST',{text:$('#notice-text').value,world_id:sel==='all'?null:+sel});$('#network-dialog').close();await showAdmin();toast('Ogłoszenie opublikowane.');
     }else if(form.id==='delete-account-form'){
      await api('/account/delete','POST',{password:$('#delete-password').value});storePreviewToken('');N.user=null;N.csrf='';N.world=null;N.character=null;$('#network-dialog').close();showAuth('Konto i postacie zostały usunięte.');
     }
    }finally{submit.disabled=false;}
   });
  });
  document.addEventListener('click',e=>{
   const b=e.target.closest('button');if(!b||b.disabled)return;
   if(b.dataset.authMode){authMode=b.dataset.authMode;showAuth();return;}if(b.dataset.tactic&&N.reportMode&&!playing){GameApp.prepareCharacter();}
   guarded(async()=>{
    if(b.dataset.world){await chooseWorld(+b.dataset.world);return;}
    if(b.dataset.tutorialGo){$('#network-dialog').close();GameApp.showView(b.dataset.tutorialGo);return;}
    if(b.dataset.pwShow){const inp=document.querySelector(b.dataset.pwShow);if(inp){inp.type=inp.type==='password'?'text':'password';b.textContent=inp.type==='password'?'Pokaż':'Ukryj';}return;}
  
    if(b.dataset.attack){b.disabled=true;try{const r=await api(`/worlds/${N.world.id}/pvp/attack/${b.dataset.attack}`,'POST',{});attackResult(r);}catch(e){if(/taktyk/i.test(e.message||'')){await N.chooseTactic();}else toast(e.message);}finally{b.disabled=false;}return;}
    if(b.dataset.orgInvite){const pid=+b.dataset.orgInvite,org=N.myOrg;if(!org||!org.canInvite)return;dialog('Zaproszenie do gildii',`<p class="section-note">Zaprosić tego gracza do <b>${esc(org.name)} [${esc(org.tag)}]</b>? Zaproszenie jest ważne 24 h — do tej samej osoby można je wysłać raz na dobę.</p><p class="tiny">Ostateczną decyzję podejmie zaproszony gracz w Społeczności.</p><button class="btn btn-gold full-width" id="org-invite-go">Wysyłam zaproszenie</button>`);$('#org-invite-go').onclick=async()=>{try{await api(`/worlds/${N.world.id}/organizations/invite`,'POST',{target_id:pid});$('#network-dialog').close();toast('Zaproszenie do gildii wysłane — decyzja należy do gracza.');}catch(e){toast(e.message);}};return;}
    if(b.dataset.accept){b.disabled=true;try{const r=await api(`/challenges/${b.dataset.accept}/accept`,'POST',{});showReport(r.report);}finally{b.disabled=false;}return;}
    if(b.dataset.decline){await api(`/challenges/${b.dataset.decline}/decline`,'POST',{});await showPvp();return;}
    if(b.dataset.match){const r=await api('/matches/'+b.dataset.match);showReport(r.report);return;}
    if(b.dataset.season){await showRanking(+b.dataset.season);return;}
    if(b.dataset.shopGate!==undefined){const enable=b.dataset.shopGate==='1';const st=enable&&document.querySelector('#shop-statement');if(enable&&st&&!st.checked){toast('Zaznacz najpierw oświadczenie o zgodzie na wydatki (RODO art. 8).');return;}const minor=enable&&document.querySelector('input[name=shop-age]:checked')?.value==='minor';if(enable&&minor&&!N.packet.shop.guardian){const name=$('#gc-name')?.value.trim()||'';if(name.length<3){toast('Podaj imię i nazwisko opiekuna (min. 3 znaki).');return;}await api('/shop/guardian','POST',{guardian_name:name,weekly_limit:+document.querySelector('#gc-limit').value});}await api('/shop/gate','POST',{enable,statement:!!(st&&st.checked),minor});await showShop();toast(enable?'Zakupy włączone (dev, pozorowana kasa).':'Zakupy wyłączone.');return;}
    if(b.dataset.shopBuy){await api('/shop/checkout','POST',{sku:b.dataset.shopBuy,wid:N.world?.id||0});const shop=await api('/shop');N.packet.shop=shop.state;applyShopCosmetics(shop.state);if(['starter','energy','speedup'].includes(b.dataset.shopBuy))install(await api(`/worlds/${N.world.id}/state`));await showShop();toast('Zakup zakończony (dev — bez prawdziwej płatności). Szczegóły w powiadomieniu produktu.');return;}
    if(b.dataset.shopEquip!==undefined){await api('/shop/equip','POST',{skin:b.dataset.shopEquip});const shop=await api('/shop');N.packet.shop=shop.state;applyShopCosmetics(shop.state);await showShop();toast(b.dataset.shopEquip?'Skórka założona.':'Skórka zdjęta — rama domyślna.');return;}
    if(b.dataset.regWorld){await api('/admin/worlds/'+b.dataset.regWorld,'PATCH',{registration_open:b.dataset.open==='1'});await showAdmin();return;}
    if(b.dataset.maintWorld){await api('/admin/worlds/'+b.dataset.maintWorld,'PATCH',{maintenance:b.dataset.maint==='1'});await showAdmin();return;}
    if(b.dataset.mod){await api('/admin/accounts/'+b.dataset.mod,'PATCH',{moderator:b.dataset.on==='1'});await showAdmin();toast(b.dataset.on==='1'?'Nadano rolę moderatora.':'Odebrano rolę moderatora.');return;}
    if(b.dataset.ban){await api('/admin/accounts/'+b.dataset.ban,'PATCH',{banned:b.dataset.banned==='1'});await showAdmin();return;}
    if(b.dataset.wsummary){
     const s=await api('/admin/worlds/'+b.dataset.wsummary+'/summary');
     const row=(k,v)=>`<div class="session-row"><div><strong>${k}</strong></div><span class="tiny">${v}</span></div>`;
     const ev=s.event?`<div class="session-row"><div><strong>${s.event.status==='active'?'Cel miasta: '+esc(s.event.name):{done:'Ostatni cel (zaliczony): ',missed:'Ostatni cel (wygasł): ',cancelled:'Ostatni cel (anulowany): '}[s.event.status]+esc(s.event.name)}</strong></div><span class="tiny">${s.event.status==='active'?s.event.progress+' / '+s.event.target:'—'}</span></div>`:'';
     const tops=s.top.map(t=>`${esc(t.nickname)} (poz. ${t.level}, ${t.xp.toLocaleString('pl-PL')} XP)`).join(' · ')||'—';
     const orgs=s.topOrgs.map(o=>`${esc(o.name)} [${esc(o.tag)}] — ${o.prestige.toLocaleString('pl-PL')} $ prestiżu, ${o.members} czł.`).join('<br>')||'—';
     dialog('Podsumowanie świata · '+s.world.name,`<div class="session-row"><div><strong>Mieszkańcy</strong></div><span class="tiny">${s.population} · łącznie ${s.cityXp.toLocaleString('pl-PL')} XP</span></div>${s.newest?`<div class="session-row"><div><strong>Najnowszy mieszkaniec</strong></div><span class="tiny">${esc(s.newest.nickname)} · ${date(s.newest.created_at)}</span></div>`:''}${ev}<div class="session-row"><div><strong>Organizacje</strong></div><span class="tiny">${s.orgs}</span></div><div class="session-row"><div><strong>Kontrakty org (aktywne / zaliczone / przepadłe)</strong></div><span class="tiny">${s.contracts.active} / ${s.contracts.done} / ${s.contracts.missed}</span></div>${ecAdminChart(s.daily)}<div class="session-row"><div><strong>Kronika / ogłoszenia aktywne</strong></div><span class="tiny">${s.chronicleCount} wpisów · ${s.noticesCount} ogłoszeń</span></div><div class="session-row"><div><strong>Dev-sklep na tym świecie</strong></div><span class="tiny">${s.shop.purchases} zakupów · ${(s.shop.cents/100).toFixed(2).replace('.',',')} zł (pozorowane) · VIP: ${s.vipResidents} mieszk.</span></div><p class="section-note"><b>Najlepsi:</b> ${tops}</p><p class="section-note"><b>Największe organizacje:</b><br>${orgs}</p><p class="tiny">Obraz tylko-do-odczytu; zakupy w wersji dev są pozorowane.</p>`);
     return;}
    if(b.dataset.announcement){const w=adminCache.worlds.find(x=>x.id===+b.dataset.announcement);dialog('Komunikat · '+w.name,`<form id="announcement-form" data-world-id="${w.id}"><label class="field" for="world-announcement">Treść · maks. 500 znaków</label><textarea id="world-announcement" maxlength="500" rows="5">${esc(w.announcement)}</textarea><p class="section-note">Komunikat będzie widoczny na liście światów.</p><button class="btn btn-gold" type="submit">Opublikuj</button></form>`);return;}
    if(b.dataset.ceCancel){await api(`/admin/events/${b.dataset.ceCancel}/cancel`,'POST',{});await showAdmin();toast('Event zakończony. Mieszkańcy dostali powiadomienie.');return;}
    if(b.dataset.noticeDel){await api(`/admin/notices/${b.dataset.noticeDel}/delete`,'POST',{});await showAdmin();toast('Ogłoszenie usunięte z tablicy.');return;}
    switch(b.dataset.online){
     case 'city-event':{const districts=['Lasy Wschodnie','Centrum','Portowe','Biznesowe','Sportowe','Kopalnia'].map(d=>`<option>${d}</option>`).join('');dialog('Event miejski · wspólny cel',`<form id="city-event-form"><label class="field" for="ce-world">Świat</label><select id="ce-world">${adminCache.worlds.map(w=>`<option value="${w.id}">${esc(w.name)}</option>`).join('')}</select><label class="field" for="ce-name">Nazwa eventu</label><input id="ce-name" required minlength="3" maxlength="60" placeholder="np. Noc Prestiżu w Porcie"><label class="field" for="ce-desc">Opis · opcjonalny</label><textarea id="ce-desc" maxlength="300" rows="2"></textarea><label class="field" for="ce-kind">Rodzaj celu</label><select id="ce-kind"><option value="xp">XP miasta — wszyscy razem</option><option value="prestige">Prestiż organizacji w dzielnicy</option></select><label class="field" for="ce-district">Dzielnica · tylko dla prestiżu</label><select id="ce-district">${districts}</select><label class="field" for="ce-target">Cel</label><input id="ce-target" type="number" min="100" max="500000" step="100" value="500" required><label class="field" for="ce-hours">Czas trwania</label><select id="ce-hours"><option value="24">24 godziny</option><option value="48">48 godzin</option><option value="72">3 dni</option><option value="168">7 dni</option><option value="336">14 dni</option></select><p class="section-note">Nagroda: odznaka „Pionier: …” dla mieszkańców świata w chwili zaliczenia (kosmetyka, zero premii do siły).</p><button class="btn btn-gold full-width" type="submit">Utwórz event</button></form>`);break;}
     case 'worlds':$('#network-dialog').close();await showWorlds();break;
     case 'account':await showAccount();break;
     case 'profile':await showProfile();break;
     case 'rankings':await showAccountRankings();break;
     case 'wardrobe-wear':{const it=window.CityAvatar?.item(b.dataset.item);if(!it||!N.world)break;const cur=N.packet?.state?.avatar||{body:{},worn:{},owned:[]};const worn={...(cur.worn||{})};if(worn[it.k]===it.id)delete worn[it.k];else worn[it.k]=it.id;try{const r=await api(`/worlds/${N.world.id}/avatar`,'POST',{avatar:{body:cur.body||{},worn}});install(await api(`/worlds/${N.world.id}/state`));toast(r.message);await showShop();}catch(e){toast(e.message);}break;}
     case 'wardrobe-buy':{const it=window.CityAvatar?.item(b.dataset.item);if(!it||!N.world)break;try{const r=await api(`/worlds/${N.world.id}/wardrobe`,'POST',{item:it.id});install(await api(`/worlds/${N.world.id}/state`));toast(r.message);await showShop();}catch(e){toast(e.message);}break;}
     case 'logout':await logout();break;
     case 'tutorial':showTutorial();break;
     case 'dismiss-tutorial':$('#network-dialog').close();await N.action({action:'tutorial_dismiss'});break;
      case 'brief-close':$('#network-dialog').close();break;      case 'brief-tender':$('#network-dialog').close();await N.action({action:'tender_accept'});GameApp.showView('contracts');break;
     case 'cafe-buy':await N.action({action:'buy_business',business:'cafe'});break;
     case 'cafe-collect':await N.action({action:'collect',business:'cafe'});break;
     case 'cafe-upgrade':await N.action({action:'upgrade',business:'cafe'});break;
     case 'refresh-panel':await refreshPanel();break;
     case 'create-world':worldForm();break;
     case 'gc-revoke':dialog('Cofnięcie zgody opiekuna',`<p>Cofnięcie zgody natychmiast wyłącza zakupy na koncie (RODO art. 8). Później można zapisać nową zgodę.</p><button class="btn danger-btn" data-online="gc-revoke-confirm">Cofam zgodę opiekuna</button>`);break;
     case 'gc-revoke-confirm':await api('/shop/guardian/revoke','POST',{});$('#network-dialog').close();await showShop();toast('Zgoda opiekuna cofnięta — zakupy wyłączone.');break;
     case 'post-notice':dialog('Nowe ogłoszenie',`<form id="notice-form"><label class="field" for="notice-world">Zasięg</label><select id="notice-world"><option value="all">Wszystkie światy</option>${adminCache.worlds.map(w=>`<option value="${w.id}">${esc(w.name)}</option>`).join('')}</select><label class="field" for="notice-text">Treść · maks. 500 znaków</label><textarea id="notice-text" maxlength="500" rows="4" required minlength="3"></textarea><p class="section-note">Gracze zobaczą ogłoszenie na tablicy w Społeczności i w banerze gry przy najbliższym odświeżeniu. Ogłoszenia znikają po 7 dniach.</p><button class="btn btn-gold" type="submit">Opublikuj</button></form>`);break;
     case 'notice-dismiss':{let seen=0;try{seen=Number(sessionStorage.getItem('cityNoticeSeen'))||0;}catch{}const latest=(N.packet?.notices||[]).reduce((m,n)=>Math.max(m,n.id||0),seen);try{sessionStorage.setItem('cityNoticeSeen',String(latest));}catch{}$('#world-news').hidden=true;break;}
     case 'export-account':download(await api('/account/export'),'CITY_EMPIRE_dane_konta.json');break;
    }
   });
  });
  try{N.authSettings=await api('/auth/config');if(!N.authSettings.previewSessions)storePreviewToken('');const me=await api('/me');setUser(me.user,me.csrf);let previous=null;try{previous=+sessionStorage.getItem('cityEmpireOnlineWorld');}catch{}if(previous){try{await loadWorld(previous);}catch{await showWorlds();}}else await showWorlds();}catch(e){showAuth(e.message==='Zaloguj się ponownie.'?'':e.message);}
  setInterval(()=>N.refresh(),5000);setInterval(worldNews,30000);
 };
 N.ui={esc,dialog,guarded,date,money,key};
 N.reauthenticate=message=>{storePreviewToken('');N.user=null;N.csrf='';N.character=null;N.world=null;N.generation++;authMode='login';$('#network-dialog').close();showAuth(message);};
 return N;
})();
