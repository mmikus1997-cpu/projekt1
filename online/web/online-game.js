/* Online view layer. State is read from the server; local timers are presentation only. */
const GameApp=(()=>{
'use strict';
const G={...CityGame,get ITEMS(){return Network.packet?.catalog.items||CityGame.ITEMS;},bonuses:s=>[0,1,2,3,4].map(i=>Object.values(s.equipped).reduce((sum,id)=>sum+(G.ITEMS.find(x=>x.id===id)?.bonus[i]||0),0)),effective:s=>s.stats.map((v,i)=>v+G.bonuses(s)[i]),sync:s=>s,get RATES(){return CityGame.RATES.map(x=>x*(Network.world?.speed||1));},get CONTRACTS(){return Network.packet?.catalog.contracts||CityGame.CONTRACTS;}};
const durationLabel=ms=>ms<60000?Math.round(ms/1000)+' s':Math.round(ms/60000)+' min';
const money=n=>Math.floor(n).toLocaleString('pl-PL')+' $';
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const SLOT_NAMES={gloves:'Rękawice',shirt:'Strój',shoes:'Obuwie',accessory:'Akcesorium',helmet:'Nakrycie',backpack:'Plecak',amulet:'Amulet'};
const CLASS_META={bokser:['🥊','Bokser'],obronca:['🛡️','Obrońca'],szybki:['⚡','Szybki']};
const LOC_META={ulica:'Ulica',silownia:'Siłownia',klub:'Klub Sportowy',targ:'Targ','brama-lochow':'Brama Lochu'};
const EVO_META={'mistrz-ringu':['👑','Mistrz Ringu','Rytm','Każdy celny cios: +5% do następnego (kumuluje się)'],'zelazna-piesc':['👊','Żelazna Pięść','Nokaut','Ciosy mocne +15%; przełama bloku w zderzeniu mocnych'],'murarz-ringu':['🧱','Murarz Ringu','Garda','W zderzeniach otrzymujesz o 20% mniej obrażeń'],'zelazny-straznik':['⚔️','Żelazny Strażnik','Riposta','Kontratak po udanym uniku: 40% → 75% szybkiego ciosu'],'blyskawica':['⚡','Błyskawica','Kontra z Impetem','Po udanym uniku następny celny cios ×1,25'],'nokaut-fantom':['👤','Nokaut Fantom','Nieuchwytny','Otrzymujesz ×0,9 obrażeń; udany unik leczy +15 HP']};
const CLASS_EVOS={bokser:['mistrz-ringu','zelazna-piesc'],obronca:['murarz-ringu','zelazny-straznik'],szybki:['blyskawica','nokaut-fantom']};
const SLOT_ICONS={gloves:'glove',shirt:'shirt',shoes:'shoe',accessory:'band',helmet:'helmet',backpack:'backpack',amulet:'amulet'};
let state,view='city',arenaMode='character',itemFilter='all',storageOK=true,lastSave=0,lastSignature='',activeArenaSignature='',corruptSave=false,pendingImport=null,awayBox=null;
state=CityGame.create();
function now(){return Network.now();}
function persist(){}
function prefs(){}
function timerText(ms){if(ms<=0)return 'Gotowe do odbioru';let sec=Math.ceil(ms/1000);const h=Math.floor(sec/3600),m=Math.floor(sec%3600/60),s=sec%60;return h?`${h}h ${String(m).padStart(2,'0')}m`:`${String(m).padStart(2,'0')}:${String(s).padStart(2,'0')}`;}
const over=(st,i)=>Math.max(0,G.effective(st)[i]-10);
const statPct=(st,i,per,cap)=>Math.min(cap,over(st,i)*per);
function statsInAction(bonus){const st=state;if(!st)return '';bonus=bonus||G.bonuses(st);
 const f=statPct(st,0,0.4,20),vc=statPct(st,0,2,40),pc=statPct(st,1,0.6,30),uc=statPct(st,1,0.3,15),
 hh=statPct(st,2,1.0,25),hr=Math.max(3,15-statPct(st,2,0.5,12)),pr=statPct(st,3,0.3,9),pk=Math.floor(over(st,3)/20),
 inf=statPct(st,4,0.5,25),dg=Math.min(6,Math.floor(over(st,4)/10)*2);
 const r1=v=>{const x=Math.round(v*10)/10;return (x%1?x.toFixed(1):String(x)).replace('.',',');};
 const rows=[['💪','Siła',`kontrakty −${r1(f)}% czasu`,`skarbiec firmy +${r1(vc)}%`],
  ['🧠','Inteligencja',`praca PC +${r1(pc)}% gotówki`,`rozbudowa −${r1(uc)}% kosztu`],
  ['⚡','Refleks',`autostop: awaria ${r1(hr)}% (−${r1(15-hr)} p.p.)`,`droga −${r1(hh)}%`],
  ['❤️','Charyzma',`ceny wyposażenia −${r1(pr)}%`,`parking +${pk} miej.`],
  ['🎯','Spryt',`wpływy inwestycji +${r1(inf)}%`,`NPC lochu −${dg}% siły`]];
 return `<section class="panel stats-action"><div class="panel-heading"><h2>Statystyki i trening</h2><span class="tiny">CENTRUM SZKOLENIOWE · KOLEJKA ${st.training.length} / 4</span></div><div class="stats-action-grid stats-train-grid">${rows.map((r,i)=>`<div class="stats-row stats-row-train"><span class="stats-ico">${r[0]}</span><b>${r[1]}</b><span class="stats-eff">${r[2]}</span><span class="stats-eff">${r[3]}</span><span class="training-value"><strong>${st.stats[i]}</strong>${bonus[i]?`<span>+${bonus[i]}</span>`:''}</span>${btn('+ Trenuj','train',`data-stat="${i}"`,st.cash<50||st.energy<5||st.training.length>=4,st.cash<50||st.energy<5||st.training.length>=4?'btn':'btn btn-gold')}</div>`).join('')}</div><section class="panel training-queue-panel stats-queue"><div class="panel-heading"><h2>Zaplanowane treningi</h2><span class="tiny">50 $ + 5 ENERGII · +1 PKT · ${durationLabel(Network.packet?.catalog.trainingDuration||300000)}</span></div><div class="training-queue">${taskCards('training')}</div></section><p class="game-note">${icon('info')} Bonusy od każdego pkt powyżej 10 · zielone punkty pochodzą z wyposażenia i nie zużywają się w walce.</p></section>`;}
function bonusText(item){const arr=item.bonus.flatMap((n,i)=>n?['+'+n+' '+labels[i]]:[]);return arr.length?arr.join(' · '):'Bez bonusów · wyposażenie startowe';}
const eraChip=e=>e?`<div class="era-wrap"><span class="era-chip" title="Cykl żywotności świata: 28 dni">🏛️ Era ${e.n} / 4 · ${esc(e.label)} (Dzień ${e.day}/${e.total})</span><span class="era-hint">otwarte dzielnice 1–${e.districts}${e.business<7?' · firmy do poziomu '+e.business:''}${e.pc?' · praca PC':''}${e.premium?' · pojazdy premium':''}${e.season?' · Sezon '+e.season.n+': '+e.season.daysLeft+' dni do podsumowania':''}</span></div>`:'';
/* --- 0.36 Wielka Mapa Miasta: pan/pinch/wheel, dzielnice z bramkami Er, przedsiębiorstwa --- */
const MAP_DISTRICTS=[
 {id:1,name:'Nadmorskie',icon:'🏠',x:720,y:860,kind:'city'},
 {id:2,name:'Przemysłowe',icon:'🏭',x:100,y:520,kind:'open'},  // 2.1d GDD v3.1: 2/7/8 zawsze otwarte (dawne surowce)
 {id:3,name:'Centrum',icon:'🏛️',x:720,y:480,kind:'city'},
 {id:4,name:'Portowe',icon:'⚓',x:100,y:140,kind:'city'},
 {id:5,name:'Biznesowe',icon:'💼',x:1340,y:520,kind:'city'},
 {id:6,name:'Sportowe',icon:'🏟️',x:100,y:860,kind:'city'},
 {id:7,name:'Kopalnia',icon:'⛏️',x:1340,y:140,kind:'open'},
 {id:8,name:'Lasy Wschodnie',icon:'🌲',x:1340,y:860,kind:'open'}];
const MAP_C=Object.fromEntries(MAP_DISTRICTS.map(d=>[d.id,d]));
const MAP_RAILS=[[1,2],[1,3],[1,6],[1,8],[2,3],[2,4],[3,4],[3,5],[3,6],[3,7],[5,7],[6,8]];
const MAP_PLACES=[
 {d:1,icon:'🏠',label:'Twoja rezydencja',go:'residence',info:'Odpoczynek, trening domowy, garaż i flota pojazdów.'},
 {d:1,icon:'🏛️',label:'Urząd Miejski',go:'city',info:'Inwestycje miejskie, kronika miasta i wpływy w dzielnicach.'},
 {d:2,icon:'🚚',label:'City Courier',v:'courier',go:'business',info:'Firma kurierska: zlecenia dostaw, rozwój i skarbiec.'},
 {d:2,icon:'📦',label:'Magazyny miejskie',go:'business',info:'Skarbiec i przepływy towarów twoich firm.'},
 {d:3,icon:'☕',label:'Corner Café',v:'cafe',go:'business',info:'Kawiarnia w centrum — lokuj firmę i zbieraj przychód.'},
 {d:3,icon:'📰',label:'Redakcja Miejska',go:'city',info:'Kronika miasta, wydarzenia i sezony.'},
 {d:5,icon:'🎨',label:'Studio Forma',v:'studio',go:'business',info:'Studio kreatywne — lokuj firmę i zbieraj przychód.'},
 {d:5,icon:'🏦',label:'Giełda Południowa',go:'city',info:'Parkiety inwestycyjne i wpływy w dzielnicach.'},
 {d:6,icon:'🥊',label:'Klub Sportowy',go:'arena',tab:'boks',info:'Ring sparingowy i wyścigi konne.'},
 {d:6,icon:'🏇',label:'Hipodrom',go:'arena',tab:'konie',info:'Zawody umiejętności — wpisowe w wirtualnych $, zero obstawiania.'},
 {d:4,icon:'🎪',label:'Hala Targów',go:'character',info:'Sklep i plecak — handel ekwipunkiem za gotówkę z gry.'},
 {d:8,icon:'🚪',label:'Brama Lochu',go:'arena',tab:'ring',info:'Wyprawa: 8 energii / piętro, unikatowe skarby jednorazowe.'},
 {d:3,icon:'📋',label:'Biuro Zleceń',go:'contracts',info:'Kontrakty dnia: gotówka i XP za pracę — pełna lista zleceń.'},
 {d:6,icon:'⚔️',label:'Arena Pojedynków',go:'pvp',info:'Wyzwania PvP: taktyka 3 zagrań, ranking i rewanże.'}];
 const MAP_ART={1:'loc-residential.jpg',2:'loc-industry.jpg',3:'auth-city.jpg',4:'loc-port.jpg',5:'loc-business.jpg',6:'loc-stadium.jpg',7:'loc-quarry.jpg',8:'loc-forest.jpg'};
const ERAS_NAME={1:'Czas Pionierów',2:'Rozwój Przemysłu',3:'Wielki Biznes',4:'Metropolia & Epilog'};
const CPIN_IC={delivery:"🛵",inventory:"🏪",event:"🎪",logistics:"⚓",audit:"📊",campaign:"📣",expo:"🤝",fleet:"🚢",branch:"🏢"};
const INVEST_NAME={3:"Centrum",4:"Portowe",5:"Biznesowe",6:"Sportowe",7:"Kopalnia",8:"Lasy Wschodnie"};
const MAP_GO_LABEL={city:'Moja dzielnica',business:'Przedsiębiorstwa',residence:'Rezydencja',garage:'Garaż',hall:'Sala Chwały',cafe:'Kawiarnia',arena:'Sala Klubowa',character:'Siłownia',contracts:'Zlecenia',map:'Mapa'};
const MAPPAN={x:0,y:0,s:1,ready:false};
let mapDrag=null,mapPinch=null,mapSuppress=false,mapRecentre=true;const mapPtr=new Map();
function mapApply(){const w=document.getElementById('map-world');if(!w)return;w.style.transform=`translate(${MAPPAN.x}px,${MAPPAN.y}px) scale(${MAPPAN.s})`;}
function mapCenterOn(id){const v=document.getElementById('map-viewport');if(!v)return;const c=MAP_C[id||1],r=v.getBoundingClientRect();
 MAPPAN.x=Math.min(60,r.width/2-(c.x+180)*MAPPAN.s);MAPPAN.y=Math.min(40,r.height/2-(c.y+120)*MAPPAN.s);mapApply();}
function mapView(){
 const era=Network.packet?.era,t=Network.packet?.travelInfo||{},cur=t.district,tv=t.travel;
 const unlock=era?era.districts:8,eraOf=d=>d<=3?1:d<=5?2:d<=7?3:4;
 const eraName={1:'Czas Pionierów',2:'Rozwój Przemysłu',3:'Wielki Biznes',4:'Metropolia & Epilog'};
 if(now()-mapPlayersAt>45000)mapLoadPlayers();
 const byD={};for(const pl of mapPlayers){if(!pl.online||pl.own||!pl.district)continue;(byD[pl.district]=byD[pl.district]||[]).push(pl);}
 const chipsFor=d=>{const list=byD[d.id]||[];if(!list.length)return '';const chips=list.slice(0,3).map(pl=>`<span class="map-player" role="button" data-map-player="${pl.id}" title="DM do ${esc(pl.nickname)} · Poziom ${pl.level}${pl.traveling?' · w drodze 🚌':''}">🧍${esc(pl.nickname)}</span>`).join('')+(list.length>3?`<span class="map-player more" title="${esc(list.slice(3).map(x=>x.nickname).join(', '))}">+${list.length-3}</span>`:'');return `<span class="map-players">${chips}</span>`;};
 const ev=Network.packet?.cityEvent,evD=mapEventDistrict(ev),season=era&&era.season?era.season:null;
 const cards=MAP_DISTRICTS.map(d=>{const locked=d.kind==='city'&&d.id>unlock,here=d.id===cur&&!tv,goal=!!tv&&tv.to===d.id;
  const badges=`<span class="map-badges">${ev&&evD===d.id?`<button type="button" class="map-badge event" data-map-event="1" title="Event miejski: ${esc(ev.name)}">📣</button>`:''}${season&&d.id===3?`<button type="button" class="map-badge season" data-map-season="1" title="Sezon rankingowy ${season.n} · ${season.daysLeft} dni">🏁</button>`:''}</span>`;
  const places=MAP_PLACES.filter(p=>p.d===d.id).map(p=>{if(locked)return `<span class="map-place fog" data-map-fog="${d.id}" title="🚧 Plac budowy — otwarcie w Erze ${eraOf(d.id)} (${ERAS_NAME[eraOf(d.id)]})">🚧</span>`;const owned=p.v==='courier'||(p.v&&state.ventures[p.v]);const fo=p.v?mapPlayers.filter(x=>!x.own&&x.online&&(x.biz||{})[p.v]):[];
   return `<button type="button" class="map-place${owned?' owned':''}" data-map-place="${MAP_PLACES.indexOf(p)}" title="${p.label}${owned?' · Twoje ⭐ — klik':' — klik'}">${p.icon}${fo.length?`<span class="map-own-badge" title="Online z tą firmą: ${esc(fo.map(x=>x.nickname).join(', '))}">⭐×${fo.length}</span>`:''}</button>`;}).join('');
  const cpins=locked?'':(Network.packet?.catalog?.contracts||[]).filter(x=>x.d===d.id).map(x=>`<button type="button" class="map-place cpin${here?' athere':''}" data-map-cpin="${x.id}" title="Zlecenie: ${esc(x.name)} — kliknij po szczegóły">${CPIN_IC[x.id]||'📋'}${x.hop?`<span class="cpin-hop">+${x.hop}%</span>`:''}</button>`).join('');
  const sub=locked?`🚧 Plac budowy · Era ${eraOf(d.id)} · ${eraName[eraOf(d.id)]}`:here?'Jesteś tutaj':goal?'Twój cel podróży':'Kliknij, aby podróżować';
  return `<div class="map-district${locked?' locked fog':''}${here?' here':''}${goal?' goal':''}" data-map-d="${d.id}" style="left:${d.x}px;top:${d.y}px"><span class="map-d-num">${d.id}/8</span><span class="map-d-icon">${locked?'🚧':d.icon}</span><b>${d.name}</b><span class="map-d-sub">${sub}</span><span class="map-d-places">${places}${cpins}</span>${chipsFor(d)}${badges}${here?'<span class="map-me">📍</span>':''}${goal?'<span class="map-me moving">⛳</span>':''}</div>`;}).join('');
 const railUse={};for(const pl of mapPlayers){if(!pl.online||!pl.traveling||pl.own||!pl.origin||!pl.district)continue;const rt=mapRoute(pl.origin,pl.district);for(let i=0;i<rt.length-1;i++){const a=Math.min(rt[i],rt[i+1]),b=Math.max(rt[i],rt[i+1]);railUse[a+'-'+b]=(railUse[a+'-'+b]||0)+1;}}
 const rails=MAP_RAILS.map(([a,b])=>{const A=MAP_C[a],B=MAP_C[b];const n=railUse[a+'-'+b]||0;return `<line x1="${A.x+180}" y1="${A.y+120}" x2="${B.x+180}" y2="${B.y+120}"${n?` stroke="#d4af70" stroke-opacity=".55" stroke-width="${(3+Math.min(5,n)*1.3).toFixed(1)}"`:''}><title>${n?`Ruch kolejowy: ${n} w drodze`:'Linia kolejowa'}</title></line>`;}).join('');
 const route=tv?mapRoute(cur,tv.to):null;
 const routePts=route?route.map(id=>[MAP_C[id].x+180,MAP_C[id].y+120]):null;
 const routeEl=routePts?`<polyline class="map-route" points="${routePts.map(q=>q.join(',')).join(' ')}"/>`:'';
 setTimeout(()=>{if(GameApp.view==='map'){if(mapRecentre||!MAPPAN.ready){MAPPAN.s=1;mapCenterOn(cur);MAPPAN.ready=true;mapRecentre=false;}mapApply();if(tv&&route)mapAnim(tv,route);}},0);
 return heading('Mapa świata','Osiem dzielnic · lokacje usługowe.',`Przemysłowe, Kopalnia i Lasy Wschodnie są otwarte od początku świata, pozostałe miasta odblokowują kolejne Ery. Kliknij dzielnicę, aby podróżować (kolej miejska łączy świat).`,'')+`<div class="bigmap-wrap"><div class="bigmap-viewport" id="map-viewport"><div class="bigmap-world" id="map-world"><svg class="map-rails" viewBox="0 0 1800 1200" preserveAspectRatio="none">${rails}${routeEl}</svg>${cards}${tv?'<div id="map-traveler" class="'+(tv.mode==='bus'?'bus':'foot')+'" title="W drodze do '+esc(tv.toName)+'">'+(tv.mode==='bus'?'🚌':'🚶')+'</div>':''}</div><div class="map-quick" id="map-quick" hidden></div><div class="map-controls"><button class="btn" data-map-photo type="button" title="Zapisz obraz mapy (PNG)">📸</button><button class="btn" data-map-sound type="button" title="Dźwięki podróży: włącz/wyłącz">${mapSoundOn()?'🔊':'🔇'}</button><button class="btn" data-map-reset type="button">Wyśrodkuj</button><button class="btn" data-map-zoom="1" type="button" title="Przybliż">＋</button><button class="btn" data-map-zoom="-1" type="button" title="Oddal">−</button></div></div><p class="game-note">${icon('info')} ${era?`Otwarte dzielnice 1–${era.districts} (Era ${era.n} · ${era.label}).`:''} ⭐ = Twoje przedsiębiorstwo. Złote linie kolejowe = ruch graczy w drodze. Bus 20 $ albo autostop za darmo.</p></div>`;
}
let mapAudio=null;
function mapSoundOn(){try{return localStorage.getItem('ce-sound')!=='0';}catch{return true;}}
function mapSound(kind){if(!mapSoundOn())return;try{const AC=window.AudioContext||window.webkitAudioContext;if(!AC)return;if(!mapAudio)mapAudio=new AC();const ctx=mapAudio;if(ctx.state==='suspended')ctx.resume();
 const t0=ctx.currentTime,mk=(f0,f1,at,dur)=>{const o=ctx.createOscillator(),g=ctx.createGain();o.type='triangle';o.frequency.setValueAtTime(f0,t0+at);o.frequency.exponentialRampToValueAtTime(f1,t0+at+dur);
  g.gain.setValueAtTime(0,t0+at);g.gain.linearRampToValueAtTime(.045,t0+at+.02);g.gain.exponentialRampToValueAtTime(.0001,t0+at+dur);o.connect(g).connect(ctx.destination);o.start(t0+at);o.stop(t0+at+dur+.05);};
 if(kind==='depart'){mk(392,523,0,.16);mk(523,659,.13,.2);}else{mk(659,523,0,.22);mk(523,392,.18,.3);}}catch{}}
// 2.1d GDD v3.1: mapMatPanel (wydobycie/skup surowców) usunięty razem z systemem surowców.
function mapPhoto(){const t=Network.packet?.travelInfo||{},cur=t.district,tv=t.travel,era=Network.packet?.era,st=state;
 const cv=document.createElement('canvas');cv.width=1200;cv.height=800;const g=cv.getContext('2d');
 const X=x=>120+x*0.62,Y=y=>90+y*0.52;
 g.fillStyle='#0d151c';g.fillRect(0,0,1200,800);
 g.fillStyle='#f2e3c0';g.font='700 34px sans-serif';g.textAlign='left';g.fillText('CITY EMPIRE',60,60);
 g.fillStyle='#9fc0d4';g.font='400 16px sans-serif';g.fillText('Mapa miasta · '+new Date().toLocaleDateString('pl-PL',{dateStyle:'full'}),60,86);
 g.strokeStyle='#2e4152';g.lineWidth=3;for(const[a,b]of MAP_RAILS){g.beginPath();g.moveTo(X(MAP_C[a].x+180),Y(MAP_C[a].y+120));g.lineTo(X(MAP_C[b].x+180),Y(MAP_C[b].y+120));g.stroke();}
 for(const d of MAP_DISTRICTS){const x=X(d.x+180),y=Y(d.y+120),locked=d.kind==='city'&&d.id>(era?era.districts:8),here=d.id===cur&&!tv,goal=!!tv&&tv.to===d.id;
  g.beginPath();g.arc(x,y,34,0,7);g.fillStyle=locked?'#182430':here?'#5c4a1e':goal?'#1e3b28':'#20313c';g.fill();g.lineWidth=4;g.strokeStyle=here?'#d4af70':goal?'#57b26a':'#3d5a6b';g.stroke();
  g.fillStyle='#cfe3ee';g.font='700 26px sans-serif';g.textAlign='center';g.fillText(String(d.id),x,y+9);
  g.fillStyle=locked?'#5c7183':'#8fb0c4';g.font='400 15px sans-serif';g.fillText(locked?'Era '+(d.id<=3?1:d.id<=5?2:d.id<=7?3:4):d.name,x,y+62);g.textAlign='left';}
 if(!tv){const c=MAP_C[cur]||MAP_C[1];g.beginPath();g.arc(X(c.x+180),Y(c.y+120),48,0,7);g.strokeStyle='#ffd57a';g.lineWidth=3;g.stroke();g.fillStyle='#ffd57a';g.font='700 16px sans-serif';g.textAlign='center';g.fillText('TY',X(c.x+180),Y(c.y+120)-58);g.textAlign='left';}
 g.fillStyle='#132029';g.fillRect(0,706,1200,94);g.fillStyle='#d4af70';g.fillRect(0,706,1200,3);
 const nick=Network.character?.nickname||'Mieszkaniec',lvl=G.level(st.xp);
 g.fillStyle='#e8eef2';g.font='600 21px sans-serif';g.fillText(nick+'  ·  Poziom '+lvl,60,750);
 g.fillStyle='#9fc0d4';g.font='400 17px sans-serif';g.fillText(money(st.cash)+'  ·  '+st.xp.toLocaleString('pl-PL')+' XP  ·  Era '+(era?era.n:1)+(era?' · '+era.label:'')+'  ·  Sezon '+(era&&era.season?era.season.n:'-'),60,780);
 const url=cv.toDataURL('image/png');try{window.__lastPhoto=url;}catch{}
 const a=document.createElement('a');a.href=url;a.download='city-empire-mapa.png';document.body.appendChild(a);a.click();a.remove();}
function mapHolder(id){const h=(Network.packet?.territory||{})[INVEST_NAME[id]];if(!h)return null;const days=Math.max(1,Math.round((now()-h.since)/86400000));return `<p class="map-ruler">🏛️ Rządzi: <b>[${esc(h.tag)}] ${esc(h.name)}</b> · od ${days} dni</p>`;}
function mapRulerLine(id){return mapHolder(id)||`<p class="map-ruler neutral">Dzielnica neutralna — władzę przejmie organizacja z największym prestiżem (wpływy w Społeczności).</p>`;}
function eraDaysTo(era,k){if(!era)return null;if(era.next&&k===era.n+1)return era.next.inDays;return Math.max(0,7*(k-1)+1-era.day);}
function mapEventDistrict(ev){if(!ev)return null;const d=(ev.district||'').toLowerCase();if(!d)return 3;
 if(d.includes('konfer'))return 7;if(d.includes('port'))return 4;if(d.includes('biznes'))return 5;
 if(d.includes('kreatyw'))return 6;if(d.includes('przedmieś'))return 8;if(d.includes('centrum'))return 3;return 3;}
function mapRoute(from,to){const adj={};for(const d of MAP_DISTRICTS)adj[d.id]=[];for(const[a,b]of MAP_RAILS){adj[a].push(b);adj[b].push(a);}
 const prev={[from]:0},q=[from];while(q.length){const n=q.shift();if(n===to)break;for(const m of adj[n])if(!(m in prev)){prev[m]=n;q.push(m);}}
 if(!(to in prev))return[from];const path=[to];while(path[0]!==from)path.unshift(prev[path[0]]);return path;}
let mapAnimToken=0;
function mapAnim(tv,route){const tok=++mapAnimToken;const pts=route.map(id=>[MAP_C[id].x+180,MAP_C[id].y+120]);const segs=[];let total=0;
 for(let i=0;i<pts.length-1;i++){const L=Math.hypot(pts[i+1][0]-pts[i][0],pts[i+1][1]-pts[i][1]);segs.push(L);total+=L;}
 const t0=tv.started||now();
 const step=()=>{const el=document.getElementById('map-traveler');if(tok!==mapAnimToken||GameApp.view!=='map'||!el)return;
  let f=tv.until>t0?(now()-t0)/(tv.until-t0):1;f=Math.max(0,Math.min(1,f));
  let d=f*total,i=0;while(i<segs.length-1&&d>segs[i]){d-=segs[i];i++;}
  const A=pts[i],B=pts[i+1]||pts[i],k=segs[i]?Math.min(1,d/segs[i]):1;
  el.style.left=(A[0]+(B[0]-A[0])*k)+'px';el.style.top=(A[1]+(B[1]-A[1])*k)+'px';el.style.opacity=.55+.45*Math.min(1,f*8);
  if(f<1)requestAnimationFrame(step);};
 step();}
let mapPlayers=[],mapPlayersAt=0,mapPlayersToken=0;
async function mapLoadPlayers(){const tok=++mapPlayersToken;try{const r=await Network.api(`/worlds/${Network.world.id}/players`);if(tok!==mapPlayersToken)return;mapPlayers=r.players||[];mapPlayersAt=now();if(GameApp.view==='map')render();}catch(e){}}
let dmPoll=null,dmPid=null;
function dmThreadHtml(t){return t.messages.map(m=>`<div class="dm-msg ${m.mine?'own':''}"><p>${esc(m.body)}</p><time>${new Date(m.created_at).toLocaleString('pl-PL',{dateStyle:'short',timeStyle:'short'})}</time></div>`).join('')||'<p class="tiny">Pusta rozmowa — napisz pierwszą wiadomość.</p>';}
async function mapOpenDm(pid){try{const t=await Network.api(`/worlds/${Network.world.id}/dm/${pid}`);if(dmPoll){clearInterval(dmPoll);dmPoll=null;}
 const html=`<p class="section-note">🧍 <b>${esc(t.partner.nickname)}</b> · Poziom ${t.partner.level} · ${t.partner.online?'🟢 online':'⚪ offline'}</p><div class="dm-thread" id="dm-thread">${dmThreadHtml(t)}</div><div class="dm-compose"><input id="dm-input" maxlength="500" placeholder="Wiadomość DM — bez linków i danych osobowych…"><button class="btn btn-gold" data-dm-send="${t.partner.id}">Wyślij</button></div><p class="tiny">Filtry jak na czacie świata · limit 30 DM/h · blokadasz przez czat światowy („Zablokuj kontakt”).</p><button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById('network-dialog').close()">Zamknij</button>`;
 Network.ui.dialog('DM · '+t.partner.nickname,html);
 dmPid=t.partner.id;
 const el0=document.getElementById('dm-thread');if(el0)el0.scrollTop=el0.scrollHeight;
 dmPoll=setInterval(async()=>{try{if(!document.getElementById('network-dialog').open||!document.getElementById('dm-thread')){clearInterval(dmPoll);dmPoll=null;return;}
  const nt=await Network.api(`/worlds/${Network.world.id}/dm/${dmPid}`);const box=document.getElementById('dm-thread');if(!box)return;const stick=box.scrollHeight-box.scrollTop-box.clientHeight<60;box.innerHTML=dmThreadHtml(nt);if(stick)box.scrollTop=box.scrollHeight;}catch{}},6000);}catch(err){toast(err.message);}}
document.addEventListener('pointerdown',e=>{const v=e.target.closest&&e.target.closest('#map-viewport');if(!v||e.target.closest('.map-controls'))return;mapPtr.set(e.pointerId,{x:e.clientX,y:e.clientY});
 if(mapPtr.size===1)mapDrag={sx:e.clientX,sy:e.clientY,ox:MAPPAN.x,oy:MAPPAN.y,moved:false};
 else if(mapPtr.size===2){const[a,b]=[...mapPtr.values()];mapPinch={d:Math.hypot(a.x-b.x,a.y-b.y),s:MAPPAN.s};mapDrag=null;}});
document.addEventListener('pointermove',e=>{if(!mapPtr.has(e.pointerId))return;mapPtr.set(e.pointerId,{x:e.clientX,y:e.clientY});
 if(mapPinch&&mapPtr.size===2){const[a,b]=[...mapPtr.values()];MAPPAN.s=Math.min(2.2,Math.max(0.5,mapPinch.s*Math.hypot(a.x-b.x,a.y-b.y)/mapPinch.d));mapApply();return;}
 if(!mapDrag)return;const dx=e.clientX-mapDrag.sx,dy=e.clientY-mapDrag.sy;if(Math.abs(dx)+Math.abs(dy)>6)mapDrag.moved=true;MAPPAN.x=mapDrag.ox+dx;MAPPAN.y=mapDrag.oy+dy;mapApply();});
const mapUp=e=>{mapPtr.delete(e.pointerId);if(mapPtr.size<2)mapPinch=null;if(mapDrag&&mapPtr.size===0){if(mapDrag.moved){mapSuppress=true;setTimeout(()=>mapSuppress=false,0);}mapDrag=null;}};
document.addEventListener('pointerup',mapUp);document.addEventListener('pointercancel',mapUp);
document.getElementById('view-map').addEventListener('wheel',e=>{if(!e.target.closest('#map-viewport'))return;e.preventDefault();const v=document.getElementById('map-viewport'),r=v.getBoundingClientRect();mapZoomBy(e.deltaY<0?1.12:0.89,r);},{passive:false});
function mapZoomBy(f,r){const v=r||document.getElementById('map-viewport').getBoundingClientRect();const ns=Math.min(2.2,Math.max(0.5,MAPPAN.s*f));if(ns===MAPPAN.s)return;const k=ns/MAPPAN.s,cx=v.width/2,cy=v.height/2;MAPPAN.x=cx-(cx-MAPPAN.x)*k;MAPPAN.y=cy-(cy-MAPPAN.y)*k;MAPPAN.s=ns;mapApply();}
function mapQuickFill(el,evt){
 const q=document.getElementById('map-quick');if(!q)return;
 const era=Network.packet?.era,cur=Network.packet?.travelInfo?.district;
 const eraOf=d=>d<=3?1:d<=5?2:d<=7?3:4;
 const unlock=era?era.districts:8;
 let title='',l1='',l2='',foot='';
 const cp=el.dataset.mapCpin;
 if(cp){
  const c=(Network.packet?.catalog?.contracts||[]).find(x=>x.id===cp);
  if(c){
   const pay=Math.round(c.cash*(c.mult||1)*(1+(c.hop||0)/100));
   title=(CPIN_IC[cp]||'📋')+' '+c.name;
   l1='📍 '+c.district+' · dzielnica '+c.d;
   l2='💸 '+money(pay)+(c.hop?' · +'+c.hop+'% za dojazd':'')+' · ⚡ '+c.energy+' · ⭐ '+c.xp+' XP';
   foot=c.d!==cur?'Kliknij: szczegóły i podróż':'Kliknij: przyjmij zlecenie';
  }
 }else if(el.dataset.mapPlace!=null){
  const pl=MAP_PLACES[+el.dataset.mapPlace];
  if(pl){
   const locked=pl.d>unlock,days=eraDaysTo(era,eraOf(pl.d));
   title=(pl.icon||'')+' '+pl.label;
   l1='📍 '+((MAP_C[pl.d]||{}).name||'');
   if(locked)l2='🚧 Otwarcie w Erze '+eraOf(pl.d)+' — za '+(days==null?'?':days)+' dni';
   else{l2=pl.info||'';foot=pl.d===cur?'Kliknij, aby wejść':'Kliknij: jedź i wejdź';}
  }
 }else if(el.dataset.mapD){
  const id=+el.dataset.mapD,d=(MAP_DISTRICTS.find(x=>x.id===id)||{});
  const locked=id>unlock,days=eraDaysTo(era,eraOf(id));
  const h=(Network.packet?.territory||{})[INVEST_NAME[id]];
  title=(d.icon||'')+' '+(d.name||'');
  l1=locked?('🚧 Otwarcie w Erze '+eraOf(id)+' ('+ERAS_NAME[eraOf(id)]+') — za '+(days==null?'?':days)+' dni'):'Dzielnica otwarta'+(era?(' · Era '+era.n+' ('+ERAS_NAME[era.n]+'), dzień '+era.day+'/'+era.total):'');
  l2=h?('🏛️ Rządzi: ['+h.tag+'] '+h.name):'🏛️ Dzielnica neutralna';
  foot='Kliknij: podróż';
 }
 if(!title&&el.dataset.mapFog){
  const id=+el.dataset.mapFog,days=eraDaysTo(era,eraOf(id));
  title='🚧 Plac budowy';
  l1='Otwarcie w Erze '+eraOf(id)+' ('+ERAS_NAME[eraOf(id)]+')';
  l2='Za '+(days==null?'?':days)+' dni'+(era?' (dziś dzień '+era.day+'/'+era.total+')':'')+'. Otwarte dzielnice: 1–'+unlock+'.';
  foot='Kliknij: szczegóły dzielnicy';
 }
 if(title){
  q.innerHTML='<b>'+esc(title)+'</b><span>'+esc(l1)+'</span>'+(l2?'<span>'+esc(l2)+'</span>':'')+(foot?'<em>'+esc(foot)+'</em>':'');
  q.hidden=false;
  const v=document.getElementById('map-viewport'),vr=v.getBoundingClientRect();
  let x,y;
  if(evt){x=evt.clientX-vr.left+16;y=evt.clientY-vr.top+18;}
  else{const er=el.getBoundingClientRect();x=(er.left+er.width/2-vr.left)/MAPPAN.s;y=(er.top-vr.top)/MAPPAN.s-8;}
  x=Math.max(8,Math.min(x,Math.max(8,vr.width-252)));y=Math.max(8,Math.min(y,Math.max(8,vr.height-110)));
  q.style.left=x+'px';q.style.top=y+'px';
 }else q.hidden=true;
}
document.getElementById('view-map').addEventListener('mouseover',e=>{if(mapDrag||mapSuppress)return;const t=e.target.closest('[data-map-cpin],[data-map-place],[data-map-d],[data-map-fog]');if(t)mapQuickFill(t,e);});
document.getElementById('view-map').addEventListener('mouseout',e=>{if(e.target.closest('[data-map-cpin],[data-map-place],[data-map-d],[data-map-fog]')){const q=document.getElementById('map-quick');if(q)q.hidden=true;}});
document.addEventListener('click',e=>{
 const mt=e.target.closest('[data-map-travel]');if(mt){if(mt.disabled)return;mt.disabled=true;const d=+mt.dataset.mapD;
  Network.api(`/worlds/${Network.world.id}/travel`,'POST',{target_district:d,mode:mt.dataset.mapTravel}).then(async()=>{document.getElementById('network-dialog').close();mapSound('depart');toast('Wyruszyłeś w drogę.');await Network.refresh();}).catch(err=>{mt.disabled=false;toast(err.message);});return;}
 const mg=e.target.closest('[data-map-go]');if(mg&&!mapSuppress){document.getElementById('network-dialog').close();
  const goTab=()=>{const tb=mg.dataset.mapTab;if(tb)setSportTab(tb);};
  if(mg.dataset.mapGo==='pvp'){clubPane('pvp');return;}
  const to=+mg.dataset.mapEnter||0;
  if(to&&Network.packet?.travelInfo?.travel){showView(mg.dataset.mapGo);goTab();return;}
  if(to&&to!==(Network.packet?.travelInfo?.district)){mg.disabled=true;Network.api(`/worlds/${Network.world.id}/travel`,'POST',{target_district:to,mode:'bus'}).then(async()=>{mapSound('depart');toast('Wyruszyłeś — wejście po przyjeździe.');showView(mg.dataset.mapGo);goTab();await Network.refresh();}).catch(err=>{toast(err.message||'Podróż nie wyszła.');mg.disabled=false;});return;}
  showView(mg.dataset.mapGo);goTab();return;}
 const dp=e.target.closest('[data-dm-pid]');if(dp){document.getElementById('network-dialog').close();GameApp.mapOpenDm(+dp.dataset.dmPid);return;}
 const ds=e.target.closest('[data-dm-send]');if(ds&&!ds.disabled){ds.disabled=true;const body=($('#dm-input')||{}).value||'';
  Network.api(`/worlds/${Network.world.id}/dm/${ds.dataset.dmSend}`,'POST',{text:body}).then(async()=>{const nt=await Network.api(`/worlds/${Network.world.id}/dm/${ds.dataset.dmSend}`);const box=document.getElementById('dm-thread');if(box){box.innerHTML=dmThreadHtml(nt);box.scrollTop=box.scrollHeight;}const inp=$('#dm-input');if(inp){inp.value='';inp.focus();}ds.disabled=false;}).catch(err=>{ds.disabled=false;toast(err.message);});}});
let mapWasTraveling=false;
function updateTravelOverlay(){
 const el=document.getElementById('travel-overlay');if(!el)return;
 const t=Network.packet?.travelInfo;
 if(!t||!t.travel){el.hidden=true;el.innerHTML='';if(mapWasTraveling){mapWasTraveling=false;mapSound('arrive');}return;}
 mapWasTraveling=true;
 const vip=(state.vipUntil||0)>now();
 el.hidden=false;
 el.innerHTML='<div class="tv-copy"><strong>W drodze do: '+esc(t.travel.toName)+'…</strong><span class="tv-line">transport: '+esc(t.travel.mode)+' · Pozostało: <b data-countdown="'+t.travel.until+'">'+timerText(Math.max(0,t.travel.until-now()))+'</b></span></div><div class="tv-bar" aria-hidden="true"><span></span></div>'+(vip?'<button class="btn btn-gold" data-extra="travel-speedup">⚡ Przyspiesz (VIP)</button>':'')+'<small class="tv-note">praca stacjonarna czeka na przyjazd</small>';
}
// 0.55.0 Moja dzielnica: 6 budynków zamiast zakładek.
const BUILDINGS=[
 ['residence','🏠','Rezydencja','residence','loc-residential.jpg','Odpoczynek i regeneracja energii — wyższe progi otwierają dłuższy relaks.'],
 ['garage','🚗','Garaż','garage','loc-industry.jpg','Pięć aut, ulepszenia do 3 poziomów i serwis floty.'],
 ['cafe','☕','Kawiarnia','cafe','bld-cafe.jpg','Dochody naliczają się także offline — wracaj i odbieraj.'],
 ['gym','💪','Siłownia','character','bld-gym.jpg','Trening statystyk za energię, wyposażenie i klasa postaci.'],
 ['club','🥊','Sala Klubowa','arena','loc-stadium.jpg','Hub mini-gier i PvP: boks, konie, ring, pojedynki.'],
 ['hall','🏆','Sala Chwały','hall','bld-hall.jpg','Tytuły, historia i poziomy budynków — bramka całej dzielnicy.'],
];
function bldLevel(key){const b=(state&&state.buildings)||{};return key==='hall'?(b.hall||0):(b[key]!=null?b[key]:1);}
function bldCost(key){const cat=Network.packet?.catalog||{};if(key==='hall')return cat.hallCost||10000;const lv=bldLevel(key);return (cat.buildingCosts||[])[lv]||0;}
function bldPips(key){const lv=bldLevel(key),max=(Network.packet?.catalog||{}).buildingMax||5;let out='';for(let i=1;i<=max;i++)out+='<i class="'+(i<=(key==='hall'&&lv?max:lv)?'on':'')+'"></i>';return '<span class="bld-pips" aria-label="poziom '+lv+'">'+out+'</span>';}
function bldBar(key){const cat=Network.packet?.catalog||{},max=cat.buildingMax||5,lv=bldLevel(key),hallKey=key==='hall';
 const ready=['residence','garage','cafe','gym','club'].every(k=>bldLevel(k)>=max);
 if(hallKey&&!lv){return `<div class="bld-bar locked">${bldPips(key)}<span class="tiny">ZAMKNIĘTA · WSZYSTKIE BUDYNKI POZ. ${max}</span>${ready?`<button class="btn btn-gold" data-game="upgrade-building" data-building="hall">🏆 Otwórz Salę Chwały · ${money(bldCost('hall'))}</button>`:'<span class="tiny">Bramka poziomów — rozbuduj wszystkie budynki.</span>'}</div>`;}
 const maxed=lv>=max;
 return `<div class="bld-bar">${bldPips(key)}<span class="tiny">POZIOM ${lv} / ${max}</span>${hallKey?'<span class="ab-chip">✓ Odblokowana</span>':`<button class="btn ${maxed?'':'btn-gold'}" data-game="upgrade-building" data-building="${key}" ${maxed?'disabled':''}>${maxed?'Maksymalny poziom':'Rozbuduj · '+money(bldCost(key))}</button>`}</div>`;}
function bldGrid(){return `<div class="district-grid" aria-label="Budynki dzielnicy">${BUILDINGS.map(([k,ic,name,view,art,desc])=>{const lv=bldLevel(k),locked=k==='hall'&&!lv;return `<button class="bld-card${locked?' locked':''}" data-go="${view}" data-bld="${k}" style="background-image:url(/art/${art})"><span class="bld-ic" aria-hidden="true">${ic}</span><span class="bld-level">${locked?'🔒':'POZIOM '+lv}</span><b>${name}</b><small>${locked?'Bramka: wszystkie budynki poziom 5':desc}</small></button>`;}).join('')}</div>`;}
function heading(eyebrow,title,description,extra=''){return `${view!=='city'?'<button class="hub-back" data-hub="city">⬅ Powrót do: Nadmorskie</button>':''}<div class="page-title game-page-title"><div><div class="eyebrow">${eyebrow}</div><h1>${title}</h1><p class="lead">${description}</p></div>${extra}</div>`;}
function btn(label,action,extra='',disabled=false,cls='btn'){return `<button class="${cls}" data-game="${action}" ${extra} ${disabled?'disabled':''}>${label}</button>`;}
function cityArt(){
 const iso=(x,y,z=0)=>[495+(x-y)*32,300+(x+y)*16-z];
 const points=arr=>arr.map(p=>p.join(',')).join(' ');
 let shapes='';
 const polygon=(p,fill,other='')=>`<polygon points="${points(p)}" fill="${fill}" ${other}/>`;
 shapes+=polygon([iso(-1,-1),iso(11,-1),iso(11,10),iso(-1,10)],'#1e2a33','stroke="#3f4c54" stroke-width="1"');
 for(let i=0;i<11;i++){
  shapes+=`<path d="M${iso(i,-1)}L${iso(i,10)}M${iso(-1,i)}L${iso(11,i)}" stroke="#30404c" stroke-width="1"/>`;
 }
 shapes+=polygon([iso(4,-1),iso(5,-1),iso(5,10),iso(4,10)],'#101c27');
 shapes+=polygon([iso(-1,4),iso(11,4),iso(11,5),iso(-1,5)],'#101c27');
 shapes+=`<path d="M${iso(4.5,-1)}L${iso(4.5,10)}M${iso(-1,4.5)}L${iso(11,4.5)}" stroke="#6d705d" stroke-width="1.3" stroke-dasharray="5 10"/>`;
 const towers=[[1,0,1.4,1.4,110],[3,0,.8,1.4,62],[6,0,1.2,1.7,150],[8,0,1,1.4,70],[0,2,1.8,1.4,60],[2.3,2,.9,1.4,130],[6,2,1.6,1.3,80],[8,2,1.4,1.3,115],[0,6,1.3,1.1,48],[2,6,1.3,1.1,88],[6,6,1.2,1.5,155],[8,6,1.2,1.6,72],[0,8,1.2,1.2,28],[2,8,1.4,1.2,50],[6,8,1.3,1.2,68],[8,8,1.5,1.2,42]];
 towers.sort((a,b)=>a[0]+a[1]-b[0]-b[1]);
 towers.forEach(([x,y,w,d,h],k)=>{
  const a=iso(x,y),b=iso(x+w,y),c=iso(x+w,y+d),dd=iso(x,y+d),A=iso(x,y,h),B=iso(x+w,y,h),C=iso(x+w,y+d,h),D=iso(x,y+d,h);
  const warm=[0,3,6,10,14].includes(k);
  shapes+=polygon([b,c,C,B],warm?'#625443':'#354b5b');shapes+=polygon([c,dd,D,C],warm?'#413d34':'#243743');shapes+=polygon([A,B,C,D],warm?'#9a825b':'#5d7885','stroke="#96a09a" stroke-opacity=".23"');
  shapes+=`<path d="M${C}L${c}" stroke="${warm?'#d4af70':'#78a6bb'}" stroke-opacity=".35"/>`;
  for(let z=12;z<h-8;z+=15)for(let n=.2;n<d-.1;n+=.35){const lit=(Math.round(z)+k+Math.floor(n*10))%3!==0;shapes+=polygon([iso(x+w,y+n,z),iso(x+w,y+n+.16,z),iso(x+w,y+n+.16,z+6),iso(x+w,y+n,z+6)],lit?(warm?'#ecc080':'#91b8c9'):'#273840',`opacity="${lit?.65:.8}"`);}
  for(let z=12;z<h-8;z+=15)for(let n=.18;n<w-.1;n+=.34){shapes+=polygon([iso(x+n,y+d,z),iso(x+n+.14,y+d,z),iso(x+n+.14,y+d,z+5),iso(x+n,y+d,z+5)],(k+z)%4?'#a5bbab':'#e2b675','opacity=".45"');}
  if(h>100){const top=iso(x+w/2,y+d/2,h);shapes+=`<path d="M${top}v-19" stroke="#a3b7c0" stroke-width="1.5"/><circle cx="${top[0]}" cy="${top[1]-19}" r="2" fill="#e3bd7f"/>`;}
 });
 for(const [x,y] of [[10,2],[10,3],[10,6],[3.7,8],[.2,3.8],[2,3.8]]){const q=iso(x,y);shapes+=`<path d="M${q}v-18" stroke="#70634d" stroke-width="3"/><ellipse cx="${q[0]}" cy="${q[1]-20}" rx="10" ry="15" fill="#4e7560"/><ellipse cx="${q[0]-3}" cy="${q[1]-25}" rx="6" ry="9" fill="#75967c"/>`;}
 for(const [x,y] of [[4.3,1.8],[4.7,6.5],[2.2,4.3],[8.5,4.7]]){const q=iso(x,y);shapes+=`<path d="M${q[0]-4} ${q[1]+2}l10 5 6-3-10-5z" fill="#d9ad68"/><path d="M${q[0]-4} ${q[1]+2}l-12-6" stroke="#d9ad68" opacity=".3"/>`;}
 return `<svg class="city-art" viewBox="0 0 980 670" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Izometryczna ilustracja fikcyjnego miasta"><defs><radialGradient id="cityGlow"><stop stop-color="#7b6d473a"/><stop offset="1" stop-color="#10212e00"/></radialGradient></defs><ellipse cx="530" cy="375" rx="440" ry="280" fill="url(#cityGlow)"/>${shapes}</svg>`;
}
const mapArt=cityArt();
function taskCards(type){
 const list=state[type],t=now();
 if(!list.length)return `<div class="game-empty">${icon(type==='contracts'?'briefcase':'activity')}<strong>${type==='contracts'?'Kolejka czeka na pierwsze zlecenie.':'Dobry trening zaczyna się od decyzji.'}</strong><p>${type==='contracts'?'Wybierz kontrakt. Energia zostanie pobrana przy przyjęciu.':'Wybierz statystykę. Trening i kontrakty mogą działać równolegle.'}</p></div>`;
 return list.map(task=>{
  const c=type==='contracts'?G.CONTRACTS.find(x=>x.id===task.contract):null,ready=t>=task.end,waiting=t<task.start;
  const name=c?c.name:'Trening: '+labels[task.stat];
  const reward=!c?'+1 '+labels[task.stat]:task.tender?`${money(task.cash)} · przetarg`:`${c.cash} $ · ${c.xp} XP`;
  const pct=100*Math.max(0,Math.min(1,(t-task.start)/(task.end-task.start)));
  return `<article class="queue-task ${ready?'ready':''}"><div class="queue-top"><span class="queue-icon">${icon(ready?'check':waiting?'clock':type==='contracts'?'truck':'activity')}</span><div><strong>${name}</strong><small>${waiting?'Oczekuje w kolejce':ready?'Ukończono':type==='contracts'?'W realizacji':'Trening w toku'}</small></div><span class="queue-reward">${reward}</span></div><div class="task-progress"><span data-task-progress data-start="${task.start}" data-end="${task.end}" style="width:${pct}%"></span></div><div class="queue-bottom"><span data-countdown="${task.end}">${timerText(task.end-t)}</span>${btn(ready?'Odbierz '+(c?money(c.cash):'punkt'):'W toku',type==='contracts'?'claim-contract':'claim-training',`data-id="${task.id}"`,!ready,ready?'btn btn-gold':'btn')}</div></article>`;
 }).join('');
}
function regenPerHour(){const cat=Network.packet?.catalog;if(cat&&cat.regenPerHour!=null)return cat.regenPerHour;const cur=(cat?.residences||[]).find(r=>r.id===state.residence);return (10+(cur?.regen||0))*(Network.world?.speed||1);}
function awayHTML(){
 const a=awayBox;if(!a)return '';const parts=[];
 if(a.contracts?.length)parts.push(`<div class="away-item">${icon('briefcase')}<div><strong>${a.contracts.length} ${a.contracts.length===1?'zlecenie ukończone':'zlecenia ukończone'}</strong><span>Kolejka rozliczyła się bez Ciebie. Odbiór w Kontraktach.</span></div></div>`);
 if(a.training)parts.push(`<div class="away-item">${icon('activity')}<div><strong>Treningi ukończone: ${a.training}</strong><span>Punkty statystyk czekają na odbiór.</span></div></div>`);
 if(a.vault>=1)parts.push(`<div class="away-item">${icon('wallet')}<div><strong>${money(a.vault)} w skarbcach firm</strong><span>Firmy pracowały na pełnej prędkości.</span></div></div>`);
 if(a.rest)parts.push(`<div class="away-item">${icon('clock')}<div><strong>Odpoczynek ukończony</strong><span>Energia czeka na odbiór w Rezydencji.</span></div></div>`);
 const away=a.minutes>=60?Math.round(a.minutes/60*10)/10+' h':a.minutes+' min';
 const chip=(ic,txt)=>`<span class="ab-chip">${ic}<b>${txt}</b></span>`;
 const chips=[];
 if(a.contracts?.length)chips.push(chip(icon('briefcase'),a.contracts.length===1?'1 zlecenie ukończone':a.contracts.length+' zlecenia ukończone'));
 if(a.training)chips.push(chip(icon('activity'),'Treningi: '+a.training));
 if(a.vault>=1)chips.push(chip(icon('wallet'),money(a.vault)+' w skarbcach'));
 if(a.rest)chips.push(chip(icon('clock'),'Odpoczynek gotowy'));
 if(!chips.length)chips.push('<span class="ab-chip mute">Spokojny okres — miasto czekało.</span>');
 return `<section class="panel away-box away-slim"><div class="ab-ico">${icon('home')}</div><div class="ab-main"><strong>Witaj z powrotem</strong><span class="tiny">${esc(away).toUpperCase()} POZA MIASTEM</span></div><div class="ab-chips">${chips.join('')}</div><button class="ab-close" data-away-dismiss data-away-close aria-label="Zamknij powitanie" title="Zamknij">×</button></section>`;
}
/* --- 0.49 Garaż w Rezydencji: grafiki aut (SVG), zakładki, ulepszenia --- */
function carArt(id){
 const A={
  rower:`<svg viewBox="0 0 120 64" role="img" aria-label="Rower dostawczy"><ellipse cx="60" cy="57" rx="46" ry="3" fill="#000" opacity=".35"/><circle cx="32" cy="44" r="12" fill="none" stroke="#9db7c9" stroke-width="2.6"/><circle cx="88" cy="44" r="12" fill="none" stroke="#9db7c9" stroke-width="2.6"/><path d="M32 44 50 26 70 26 88 44 M50 26 56 44 32 44 M70 26 64 44 88 44" fill="none" stroke="#c9d8e4" stroke-width="2.4"/><path d="M66 20h12M72 20v6" stroke="#c9d8e4" stroke-width="2.4"/><path d="M44 20h10l-2 6h-6z" fill="#c9d8e4"/><rect x="58" y="10" width="26" height="14" rx="2.5" fill="#4f7ba8"/><rect x="58" y="10" width="26" height="4" rx="2" fill="#6d97c2"/><circle cx="32" cy="44" r="2.6" fill="#dfe9f1"/><circle cx="88" cy="44" r="2.6" fill="#dfe9f1"/></svg>`,
  furgonetka:`<svg viewBox="0 0 120 64" role="img" aria-label="Furgonetka"><ellipse cx="60" cy="57" rx="50" ry="3" fill="#000" opacity=".35"/><rect x="8" y="14" width="72" height="32" rx="4" fill="#8aa06f"/><rect x="8" y="14" width="72" height="7" rx="3.5" fill="#a3b98a"/><path d="M80 22h16l12 12v12H80z" fill="#cdd9c0"/><path d="M84 25h10l8 8h-18z" fill="#3d4f63"/><rect x="8" y="40" width="100" height="6" fill="#6d8256"/><circle cx="30" cy="48" r="8.5" fill="#232b33"/><circle cx="30" cy="48" r="3.6" fill="#8b98a5"/><circle cx="92" cy="48" r="8.5" fill="#232b33"/><circle cx="92" cy="48" r="3.6" fill="#8b98a5"/><rect x="14" y="26" width="16" height="10" rx="1.5" fill="#3d4f63"/><rect x="34" y="26" width="16" height="10" rx="1.5" fill="#3d4f63"/><rect x="104" y="34" width="6" height="4" fill="#e8c96a"/></svg>`,
  sedan:`<svg viewBox="0 0 120 64" role="img" aria-label="Sedan miejski"><ellipse cx="60" cy="57" rx="52" ry="3" fill="#000" opacity=".35"/><path d="M8 46c0-6 4-10 12-11l12-10c3-3 8-5 14-5h16c6 0 11 2 14 5l10 10c10 1 16 4 16 11v4H8z" fill="#3f6ea8"/><path d="M34 25c2-3 6-4 10-4h8v12H30zM56 21h10c4 0 8 2 10 4l8 8H56z" fill="#b9d2e8"/><rect x="6" y="46" width="108" height="6" rx="2" fill="#325a8c"/><circle cx="32" cy="49" r="8.5" fill="#1d242c"/><circle cx="32" cy="49" r="3.4" fill="#93a3b2"/><circle cx="90" cy="49" r="8.5" fill="#1d242c"/><circle cx="90" cy="49" r="3.4" fill="#93a3b2"/><rect x="110" y="40" width="6" height="4" rx="1" fill="#e8c96a"/></svg>`,
  bus:`<svg viewBox="0 0 120 64" role="img" aria-label="Bus flotowy"><ellipse cx="60" cy="58" rx="54" ry="3" fill="#000" opacity=".35"/><rect x="4" y="10" width="108" height="38" rx="6" fill="#b08d3e"/><rect x="4" y="10" width="108" height="8" rx="4" fill="#c9a851"/><rect x="10" y="22" width="16" height="12" rx="2" fill="#33424f"/><rect x="30" y="22" width="16" height="12" rx="2" fill="#33424f"/><rect x="50" y="22" width="16" height="12" rx="2" fill="#33424f"/><rect x="70" y="22" width="16" height="12" rx="2" fill="#33424f"/><rect x="94" y="20" width="14" height="18" rx="2" fill="#33424f"/><rect x="4" y="40" width="108" height="8" fill="#8f7030"/><circle cx="26" cy="50" r="8" fill="#1d242c"/><circle cx="26" cy="50" r="3.2" fill="#93a3b2"/><circle cx="92" cy="50" r="8" fill="#1d242c"/><circle cx="92" cy="50" r="3.2" fill="#93a3b2"/><rect x="100" y="14" width="10" height="3" rx="1.5" fill="#e8c96a"/></svg>`,
  supercar:`<svg viewBox="0 0 120 64" role="img" aria-label="Hiper Widok GT — auto VIP"><defs><linearGradient id="carGt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#e06a5a"/><stop offset="1" stop-color="#a8322a"/></linearGradient></defs><ellipse cx="60" cy="57" rx="53" ry="3" fill="#000" opacity=".35"/><path d="M4 48l6-6h8l6-8 2-6c10-4 30-8 44-4l14 4 16 2c8 1 14 5 14 10v8H4z" fill="url(#carGt)"/><path d="M30 34l4-6c8-3 24-6 36-3l8 3-6 8H34z" fill="#20262d"/><path d="M76 31l10 3 12 2-4 4-16-2z" fill="#20262d"/><path d="M4 48l6-6h8l-4 6zM112 42l4 6h-10z" fill="#d8a13c"/><rect x="2" y="30" width="14" height="3" rx="1.5" fill="#d8a13c"/><path d="M10 30v-4h3v4" fill="#d8a13c"/><circle cx="32" cy="49" r="9.5" fill="#14181d"/><circle cx="32" cy="49" r="4" fill="#d8a13c"/><circle cx="90" cy="49" r="9.5" fill="#14181d"/><circle cx="90" cy="49" r="4" fill="#d8a13c"/></svg>`};
 return `<div class="car-art${id==='supercar'?' car-art-vip':''}">${A[id]||''}</div>`;
}
function garageTabHTML(){
 const cat=Network.packet?.catalog||{},vehicles=cat.vehicles||[],veh=state.vehicle,up=state.garageUp||{};
 const vip=!!(Network.packet?.shop?.vipActive);
 const res=(cat.residences||[]).find(r=>r.id===state.residence);
 const cap=((1+(res?res.slots||0:0)))+Math.floor(Math.max(0,state.stats[3]-10)/20);
 const cards=vehicles.map(g=>{
  const owned=state.garage.includes(g.id),active=!!(veh&&veh.id===g.id),locked=G.level(state.xp)<g.level;
  const lvl=up[g.id]||0,maxed=lvl>=3,cost=Math.round(g.price*0.4*(lvl+1)/10)*10;
  const disc=g.discount+(owned?4*lvl:0),wear=active?veh.wear:0;
  const vipLock=g.vip&&!vip,parkingFull=!owned&&state.garage.length>=cap;
  const dots=[0,1,2].map(i=>`<i class="${i<lvl?'on':''}"></i>`).join('');
  const status=!owned?(vipLock?'<span class="car-badge vip">👑 VIP</span>':parkingFull?'<span class="car-badge warn">Brak miejsca</span>':locked?`<span class="car-badge warn">Od lvl ${g.level}</span>`:''):(active?'<span class="car-badge live">W użyciu</span>':'<span class="car-badge own">W garażu</span>');
  let act='';
  const upBtn=btn(maxed?'Ulepszone · max':'Ulepsz '+money(cost),'upgrade-vehicle',`data-vehicle="${g.id}"`,maxed||state.cash<cost,maxed||state.cash<cost?'btn':'btn');
  if(!owned)act=btn(vipLock?'Zablokowane · VIP':parkingFull?'Brak miejsca parkingowego':locked?'Od poziomu '+g.level:(state.cash<g.price?'Za mało gotówki':'Kup '+money(g.price)),'buy-vehicle',`data-vehicle="${g.id}"`,vipLock||parkingFull||locked||state.cash<g.price,vipLock||parkingFull||locked||state.cash<g.price?'btn':'btn btn-gold');
  else if(active)act=(wear>=100?btn('Napraw · serwis '+money(g.service),'service-vehicle','data-vehicle="'+g.id+'"',false,'btn btn-gold'):btn('W użyciu · zużycie '+wear+'%','equip-vehicle','data-vehicle="'+g.id+'"',true,'btn'))+upBtn;
  else act=btn('Wybierz','equip-vehicle',`data-vehicle="${g.id}"`,!!veh&&veh.wear>=100&&veh.id!==g.id,'btn')+upBtn;
  return `<article class="car-card${g.vip?' car-vip':''}">${status}${carArt(g.img)}<div class="car-body"><h3>${esc(g.name)}</h3><p class="car-desc">${esc(g.description)}</p><div class="car-meta"><span>${icon('clock')} Rabat czasu: <strong>−${disc}%</strong></span><span>${icon('truck')} Serwis: ${money(g.service)}</span><span class="car-up" title="Poziom ulepszeń">Ulepszenia ${dots}</span></div><div class="car-actions">${act}</div>${active?`<div class="car-wear"><span style="width:${wear}%"></span></div>`:''}</div></article>`;
 }).join('');
 return `<div class="game-summary-bar"><span>🚗 Auta w garażu: <strong>${state.garage.length} / ${cap}</strong></span><span>${icon('home')} Miejsca parkingowe: <strong>${cap}</strong>${res?' · '+esc(res.name):' · kup rezydencję, by mieć więcej'}</span><span>${icon('clock')} Każde zlecenie: +6% zużycia aktywnego auta</span></div>
 <div class="garage-cards">${cards}</div>
 <p class="game-note">${icon('info')} Ulepszenie (3 poziomy: silnik, zawieszenie, lakier) zwiększa rabat czasu o +4 p.p. każdy. Zużycie 100% wyłącza rabat do czasu serwisu. Hiper Widok GT to auto VIP — odblokujesz je ikoną 👑 w Sklepie (tryb rozwojowy, bez prawdziwych płatności).</p>`;
}
function routesPanelHTML(){
 const cat=Network.packet?.catalog||{},routes=cat.npcRoutes||[],vm=cat.routeVehMult||{},nr=state.npcRoutes||{runs:[]},runs=nr.runs||[],slots=Math.max(1,bldLevel('residence'));
 const vname=id=>((cat.vehicles||[]).find(v=>v.id===id)||{}).name||id;
 const busy=new Set(runs.map(r=>r.vehicle)),idle=(state.garage||[]).filter(c=>!busy.has(c));
 const runCards=runs.map(r=>{const def=routes.find(x=>x.id===r.route)||{},ready=(r.end||0)<=Date.now();return `<article class="route-run${ready?' ready':''}"><div class="route-line"><b>${esc(def.name||r.route)}</b><span class="tiny">${esc(def.line||'')} · ${esc(vname(r.vehicle))}</span></div><div class="route-timer">${ready?'✅ <strong>Gotowe do odbioru</strong>':icon('clock')+' <span data-countdown="'+r.end+'"></span>'}</div></article>`;}).join('');
 const cards=routes.map(r=>{const opts=idle.map(v=>`<option value="${v}">${esc(vname(v))} · x${(vm[v]||1).toFixed(2)}</option>`).join('');return `<article class="route-card"><div class="route-line"><b>${esc(r.name)}</b><span class="tiny">${esc(r.line)}</span></div><div class="route-meta"><span>⏱ ${timerText(r.duration)}</span><span>💰 ${money(r.cash)}+</span><span>⭐ +${r.xp} XP</span></div>${idle.length?`<div class="route-actions"><select data-route-veh="${r.id}" aria-label="Pojazd na trasę">${opts}</select><button class="btn btn-gold" data-game="route-dispatch" data-route="${r.id}">Wyślij</button></div>`:'<p class="tiny">Brak wolnych pojazdów — wracają po odbiorze tras.</p>'}</article>`;}).join('');
 return `<section class="panel routes-panel"><div class="panel-heading"><h2>🚚 Trasy NPC</h2><span class="tiny">KIEROWCY Z REZYDENCJI · ${runs.length}/${slots}</span></div><p class="section-note">Kierowcy z Twojej Rezydencji wożą ładunki flotą z Garażu — także po zamknięciu strony. Poziom budynku Rezydencja = liczba tras naraz (rozbudowa = więcej tras), a Garaż dokłada +2%/poziom do wypłat.</p>${runs.length?`<div class="route-runs">${runCards}</div><button class="btn btn-gold" data-game="route-claim">🏁 Odbierz gotowe trasy</button>`:`<p class="game-note">${icon('info')} Żaden kierowca nie jest w drodze — wybierz trasę poniżej.</p>`}<div class="route-list">${cards}</div>${nr.done?`<p class="game-note">${icon('check')} Dokończone trasy: <b>${nr.done}</b> · zarobek <b>${money(nr.cash||0)}</b> · +${nr.xp||0} XP.</p>`:''}</section>`;
}
function garageView(){return heading('Garaż','Flota miasta.','Kupuj auta, ulepszaj do 3 poziomów i serwisuj po zużyciu. Część aut to grafiki VIP.')+bldBar('garage')+garageTabHTML()+routesPanelHTML();}
function cafeView(){return heading('Kawiarnia','Dochód pracuje w tle.','Podsumowanie nieobecności i skarbiec kawiarni — odbierz, co zarobiło się offline.')+bldBar('cafe')+(awayBox?awayHTML():'')+Network.cafeHTML(state)+`<p class="game-note">${icon('info')} Dochody firm i kawiarni naliczają się także podczas Twojej nieobecności (do 24 h).</p>`;}
function hallView(){const b=(state&&state.buildings)||{},max=(Network.packet?.catalog||{}).buildingMax||5,keys=['residence','garage','cafe','gym','club'];
 const board=BUILDINGS.filter(([k])=>k!=='hall').map(([k,ic,name])=>`<div class="hall-row"><span>${ic} ${name}</span>${bldPips(k)}<span class="tiny">POZIOM ${bldLevel(k)} / ${max}</span></div>`).join('');
 const boardFull=board+`<div class="hall-row"><span>🏆 Sala Chwały</span>${bldPips('hall')}<span class="tiny">${bldLevel('hall')?'ODBLOKOWANA':'ZAMKNIĘTA'}</span></div>`;
 if(!bldLevel('hall')){const ready=keys.every(k=>bldLevel(k)>=max);
  return heading('Sala Chwały','Bramka dzielnicy.','Sala Chwały otwiera się, gdy wszystkie budynki osiągną poziom '+max+'.')+`<section class="panel hall-gate"><div class="panel-heading"><h2>${icon('trophy')} Bramka poziomów</h2><span class="tiny">WSZYSTKIE BUDYNKI · POZIOM ${max}</span></div><div class="hall-board">${board}</div>${ready?`<button class="btn btn-gold" data-game="upgrade-building" data-building="hall">🏆 Otwórz Salę Chwały · ${money(bldCost('hall'))}</button>`:`<p class="section-note">Rozbuduj wszystkie ${keys.length} budynków do poziomu ${max}, aby otworzyć Salę Chwały.</p>`}</section>`+
   `<section class="panel story-panel"><div class="panel-heading"><h2>Twoja historia</h2><span class="tiny">KARIERA · CZYSTO OPISOWA</span></div>${dailyChart(Network.packet?.activity)}<div class="story-grid"><div><span>Kontrakty ukończone</span><strong>${state.completed.contracts||0}</strong></div><div><span>Treningi</span><strong>${state.completed.training||0}</strong></div><div><span>Pojedynki · wygrane</span><strong>${Network.character?.wins||0}</strong></div><div><span>Pojedynki · rating</span><strong>${Network.character?.rating==null?'—':Math.round(Network.character.rating)}</strong></div></div><div class="story-badges">${(Network.packet?.titles||[]).map(t=>`<span class="org-held-chip story-badge">${esc(t.label)}</span>`).join('')||'<small class="tiny">Jeszcze bez odznak — pojawią się za wspólne cele miasta i sezony rankingowe.</small>'}</div></section>`;}
 return heading('Sala Chwały','Chwała miasta.','Tytuły, historia i poziomy całej dzielnicy.')+bldBar('hall')+
 `
 <section class="panel hall-board-panel"><div class="panel-heading"><h2>Poziomy budynków</h2><span class="tiny">TWOJA DZIELNICA</span></div><div class="hall-board">${boardFull}</div></section>`;}
function residenceView(){
 const cat=Network.packet?.catalog||{},residences=cat.residences||[],rests=cat.rests||[];
 const current=residences.find(r=>r.id===state.residence),tier=current?residences.indexOf(current)+1:0;
 const rest=state.rest,restDef=rest?rests.find(r=>r.id===rest.id):null;
 return heading('Rezydencja','Własny kąt w mieście.','Odpoczynek regeneruje energię, a wyższy próg rezydencji otwiera dłuższe formy relaksu.')+bldBar('residence')+`<p class="game-note">${icon('car')} Kierowcy z tej Rezydencji wożą <b>Trasy NPC</b> w Garażu — poziom budynku = liczba tras naraz (0.56).</p>`+`
 <div class="game-summary-bar"><span>${icon('bolt')} <strong data-energy>${Math.floor(state.energy)}</strong> / 240 energii</span><span>${icon('clock')} Regeneracja: ${Math.round(regenPerHour())} / h</span><span>${icon('home')} ${current?esc(current.name):'Nie masz jeszcze mieszkania'}</span></div>
 <div class="game-two-columns residence-layout"><div class="contract-list">${residences.map((r,i)=>{const owned=state.residence===r.id,better=current&&current.id!==r.id&&current.regen>=r.regen,locked=G.level(state.xp)<r.level,poor=state.cash<r.price;return `<article class="contract-card"><div class="contract-art residence-art-${i}">${icon('home')}<span>0${i+1}</span><small>${r.perk}</small></div><div class="contract-body"><div class="contract-title"><span class="eyebrow">Próg ${i+1}</span><span class="tiny">${owned?'Zamieszkane':better?'Masz lepszą':locked?'Od poziomu '+r.level:'Dostępna'}</span></div><h2>${r.name}</h2><p>${r.description}</p><div class="contract-metrics"><span>${icon('bolt')}+${r.regen} energii / h</span><span>${icon('star')}odpoczynek +${r.restBonus}%</span><span>${icon('truck')}parking: ${r.slots||0} aut${r.slots===1?'o':'a'}</span></div><div class="contract-action"><strong>${money(r.price)}</strong>${btn(owned?'Zamieszkane':better?'Masz lepszą rezydencję':locked?'Wymagany poziom '+r.level:poor?'Potrzebujesz '+money(r.price-state.cash)+' więcej':'Zamieszkaj '+icon('arrow'),'buy-residence',`data-residence="${r.id}"`,owned||better||locked||poor,owned?'btn':'btn btn-gold')}</div></div></article>`;}).join('')}<p class="game-note">${icon('info')} Wyższy próg zastępuje poprzedni bez zwrotu ceny. Rezydencja należy do postaci w tym świecie — postęp nie przenosi się gdzie indziej.</p></div>
 <aside class="panel rest-panel"><div class="panel-heading"><h2>Odpoczynek</h2><span class="tiny">${current?'PRÓG '+tier:'BRAK MIESZKANIA'}</span></div><p class="section-note">Jeden odpoczynek naraz. Po zakończeniu odbierasz energię; nadwyżka ponad 240 przepada.</p>
 ${rest&&restDef?`<div class="upgrade-in-progress rest-progress"><div>${icon('clock')}<strong>${restDef.name} · +${rest.gain} energii</strong><span data-countdown="${rest.end}">${timerText(rest.end-now())}</span></div><div class="task-progress"><span data-task-progress data-start="${rest.start}" data-end="${rest.end}" style="width:${100*Math.max(0,Math.min(1,(now()-rest.start)/(rest.end-rest.start)))}%"></span></div>${btn(now()>=rest.end?'Odbierz energię':'W toku','rest-claim','id="rest-claim"',now()<rest.end,'btn btn-gold full-width')}</div>`:''}
 <div class="rest-options">${rests.map(r=>{const tierOK=tier>=r.tier,resting=!!rest;return `<div class="rest-option"><div><strong>${r.name}</strong><small>${r.description}</small></div>${btn(resting?'Zajęte':tierOK?'Śpij':'Potrzebny próg '+r.tier,'rest-start',`data-rest="${r.id}"`,resting||!tierOK,tierOK&&!resting?'btn btn-gold':'btn')}</div>`;}).join('')}</div>
 <p class="game-note">${icon('info')} Dłuższe odpoczyny wymagają wyższego progu rezydencji. Odpoczynek nie blokuje kontraktów ani treningów.</p></aside></div>`;
}
function garageHTML(){
 const cat=Network.packet?.catalog||{},vehicles=cat.vehicles||[],offers=cat.staffOffers||[];
 const veh=state.vehicle;
 const vehicleCards=vehicles.map(g=>{const owned=state.garage.includes(g.id),active=veh&&veh.id===g.id,locked=G.level(state.xp)<g.level;
  return `<div class="garage-row"><div class="district-info"><strong>${g.name}${active?' · W UŻYCIU':''}</strong><small>${g.description}</small><small>Rabat czasu: -${g.discount}% · serwis ${money(g.service)}</small></div><div class="district-actions">${owned?`${btn(active?'Serwuj '+money(g.service):'Wybierz','equip-vehicle',`data-vehicle="${g.id}"`,!active&&veh?false:active&&!veh,false)}${veh&&veh.id===g.id&&veh.wear>=100?btn('Serwis '+money(g.service),'service-vehicle','',false,'btn btn-gold'):''}`:btn(locked?'Od poziomu '+g.level:'Kup '+money(g.price),'buy-vehicle',`data-vehicle="${g.id}"`,locked||state.cash<g.price,locked||state.cash<g.price?'btn':'btn btn-gold')}</div></div>`;}).join('');
 const staffCards=offers.map(o=>{const b=o.slot==='courier'?state.business:state.ventures[o.slot],active=(state.staff[o.slot]||0)>now();
  return `<div class="garage-row"><div class="district-info"><strong>${o.name} · ${o.business}</strong><small>${o.description}</small>${active?`<small>Pracuje jeszcze <span data-countdown="${state.staff[o.slot]}">${timerText(state.staff[o.slot]-now())}</span></small>`:''}</div><div class="district-actions">${btn(active?'Obsadzone':'Zatrudnij '+money(o.cost),'hire-staff',`data-staff="${o.slot}"`,active||state.cash<o.cost||(o.slot!=='courier'&&!b),active||state.cash<o.cost||(o.slot!=='courier'&&!b)?'btn':'btn btn-gold')}</div></div>`;}).join('');
 return `<section class="panel garage-panel"><div class="panel-heading"><h2>${icon('truck')} Zespół firmowy</h2><span class="tiny">LUDZIE WZMACNIAJĄ DOCHÓD · POJAZDY W REZYDENCJI</span></div>
 <div class="garage-grid"><div><h3 class="garage-title">Pojazdy → przenieśliśmy je do Rezydencji</h3><div class="garage-move-note"><p>Garaż jest teraz osobnym <strong>budynkiem dzielnicy</strong>: 5 aut z grafikami, ulepszenia (3 poziomy) i serwis. <button type="button" class="btn btn-gold" data-go="garage">Otwórz Garaż</button></p></div>${veh?`<p class="game-note">${icon('info')} Zużycie: ${veh.wear}%${veh.wear>=100?' — pojazd czeka na serwis i nie skraca zleceń.':''} Każde ukończone zlecenie dodaje 6%.</p>`:''}</div>
 <div><h3 class="garage-title">Zespół na dobę</h3>${staffCards}<p class="game-note">${icon('info')} Pracownik wzmacnia dochód firmy przez 24 h (liczone tempem świata). Stała kostka, bez długów — po dobie można zatrudnić ponownie.</p></div></div></section>`;
}
function miniMap(){const t=Network.packet?.travelInfo||{},cur=t.district,tv=t.travel;const C=MAP_C[cur]||MAP_C[1];
 const dots=MAP_DISTRICTS.map(d=>`<g class="mm-hit" data-map-d="${d.id}"><circle class="mm-hit-area" cx="${d.x+180}" cy="${d.y+120}" r="64"/><circle class="mm-dot${d.id===cur?' me':tv&&tv.to===d.id?' goal':''}" cx="${d.x+180}" cy="${d.y+120}" r="36"/><text class="mm-num" x="${d.x+180}" y="${d.y+132}" text-anchor="middle">${d.id}</text></g>`).join('');
 const rails=MAP_RAILS.map(([a,b])=>{const A=MAP_C[a],B=MAP_C[b];return `<line x1="${A.x+180}" y1="${A.y+120}" x2="${B.x+180}" y2="${B.y+120}"/>`;}).join('');
 return `<section class="panel mini-map-panel"><div class="panel-heading"><h2>Mini-mapa miasta</h2><span class="tiny">${tv?('W DRODZE ⛳ '+esc(tv.toName).toUpperCase()):('STOISZ W: '+esc((MAP_C[cur]||{name:''}).name).toUpperCase())}</span></div><button type="button" class="mini-map-btn" data-go="map" title="Otwórz wielką mapę miasta"><svg class="mini-map-svg" viewBox="0 0 1800 1200" role="img" aria-label="Mini-mapa ośmiu dzielnic — klik otwiera wielką mapę">${rails}${dots}${tv?`<circle class="mm-bus" cx="${C.x+180}" cy="${C.y+120}" r="24"><animate attributeName="opacity" values="1;.25;1" dur="1.4s" repeatCount="indefinite"/></circle>`:''}</svg><span class="mini-map-cta">📍 ${esc((MAP_C[cur]||{name:''}).name)}${tv?' → ⛳ '+esc(tv.toName):''} · kliknij, aby otworzyć wielką mapę</span></button></section>`;}
function timedEventHTML(){const e=Network.packet?.timedEvent;if(!e)return '';
 return `<section class="panel tev-panel" data-tev="${e.id}"><div class="tev-ico">${e.icon}</div><div class="tev-body"><span class="tiny">⏳ EVENT CZASOWY · DLA WSZYSTKICH GRACZY</span><h3>${esc(e.name)}</h3><p>${esc(e.desc)}</p></div><div class="tev-side"><span class="tiny">KOŃCZY SIĘ ZA</span><strong data-countdown="${e.end}"></strong><small>Następny: ${e.next.icon} ${esc(e.next.name)}</small></div></section>`;}
function home(){
 const lvl=G.level(state.xp),steps=[['Pierwszy kontrakt',state.completed.contracts>0,'contracts'],['Pierwszy trening',state.completed.training>0,'character'],['Nowe wyposażenie',state.inventory.length>4,'character'],['Odbiór dochodu',(state.completed.collected||0)>0,'business']];
 const done=steps.filter(x=>x[1]).length;
 const quick=`<div class="city-quick-grid"><article class="quick-card"><span class="quick-icon">${icon('briefcase')}</span><span class="tiny">KONTRAKTY</span><h3>${state.contracts.length?state.contracts.length+' zlecenia w kolejce':'Czas na pierwszy ruch.'}</h3><p>Legalne zlecenia. Gotówka i doświadczenie.</p><button class="text-btn" data-go="contracts">Przejdź do kontraktów ${icon('arrow')}</button></article><article class="quick-card"><span class="quick-icon blue">${icon('business')}</span><span class="tiny">CITY COURIER · POZIOM ${state.business.level}</span><h3><span data-vault>${money(state.business.vault)}</span> w skarbcu</h3><p>${G.RATES[state.business.level-1]} $ / h · dochód także podczas nieobecności.</p><button class="text-btn" data-go="business">Zarządzaj firmą ${icon('arrow')}</button></article><article class="quick-card"><span class="quick-icon green">${icon('person')}</span><span class="tiny">${esc(Network.character?.nickname||'Postać')} · POZIOM ${lvl}</span><h3>${G.effective(state).reduce((a,b)=>a+b,0)} punktów statystyk</h3><p>Trenuj, dobieraj wyposażenie, sprawdzaj się w sporcie.</p><button class="text-btn" data-go="character">Rozwijaj postać ${icon('arrow')}</button></article></div>`;
 return '<div class="hub-head">'+heading(esc(Network.world?.name||'Świat')+' · Moja dzielnica','Sześć budynków. Twoje zasady.','Rozbuduj je wszystkie, aby otworzyć Salę Chwały.',`<span class="world-pill"><span class="dot"></span>Połączono · tempo ×${Network.world?.speed||1}</span>`)+timedEventHTML()+quick+'</div>'+`
  ${bldGrid()}${storyDistinction()}
 
 ${(()=>{const ev=Network.packet?.cityEvent;if(!ev)return '';const pct=Math.min(100,Math.round(100*ev.progress/Math.max(1,ev.target)));const unit=ev.kind==='xp'?'XP':'$';const label=ev.kind==='xp'?'XP MIASTA (RAZEM)':'PRESTIŻ ORGANIZACJI · '+ev.district.toUpperCase();const ends=new Date(ev.endsAt).toLocaleString('pl-PL',{dateStyle:'short',timeStyle:'short'});return `<section class="panel city-event-card"><div class="panel-heading"><h2>${esc(ev.name)}</h2><span class="tiny">EVENT MIEJSKI · WSPÓLNY CEL</span></div>${ev.description?`<p class="section-note">${esc(ev.description)}</p>`:''}<div class="ce-progress-row"><span class="ce-unit">${label}</span><strong class="ce-nums">${ev.progress.toLocaleString('pl-PL')} / ${ev.target.toLocaleString('pl-PL')} ${unit}</strong></div><div class="contract-track ce-track"><span style="width:${pct}%"></span></div><small class="tiny">Cel miasta działa do: ${ends}. Nagroda: odznaka Pioniera dla mieszkańców (kosmetyka).</small></section>`;})()}
 ${(()=>{const cr=Network.packet?.chronicle||[];if(!cr.length)return '';const chip=k=>({'city_new':'WYZWANIE','city_done':'ZALICZONE','city_missed':'PRZEPADŁO','city_cancel':'ANULOWANE','org_founded':'ZAŁOŻENIE','org_done':'KONTRAKT','org_missed':'KONTRAKT'}[k]||'MIASTO');return `<section class="panel chronicle-panel"><div class="panel-heading"><h2>Kronika miasta</h2><span class="tiny">HISTORIA WSPÓLNYCH CELI</span></div><div class="chronicle-list">${cr.map(it=>`<article class="chronicle-item" data-kind="${esc(it.kind)}"><span class="chronicle-kind">${chip(it.kind)}</span><div class="chronicle-body"><strong>${esc(it.title)}</strong>${it.description?`<small>${esc(it.description)}</small>`:''}<time>${new Date(it.created_at).toLocaleString('pl-PL',{dateStyle:'short',timeStyle:'short'})}</time></div></article>`).join('')}</div><p class="tiny chronicle-note">Kronika zapisuje wspólne chwile świata: wyzwania miasta i kontrakty organizacji. Czysto opisowa — bez wpływu na rozgrywkę.</p></section>`;})()}
 <div class="city-overview"><div class="city-map"><div class="map-copy"><span class="map-kicker">WITAJ W MIEŚCIE</span><h2>Mały początek.<br>Wielkie możliwości.</h2><p>Kontrakty, biznes i sport.<br>Jedna postać. Twoja droga.</p></div>${mapArt}<button class="map-pin pin-business" data-go="business">${icon('business')}<span>Twoja firma</span></button><button class="map-pin pin-contracts" data-go="contracts">${icon('briefcase')}<span>Kontrakty</span></button><button class="map-pin pin-arena" data-go="arena">${icon('arena')}<span>Sala Klubowa</span></button><button class="map-pin pin-training" data-go="character">${icon('activity')}<span>Siłownia</span></button><button class="map-pin pin-residence" data-go="residence">${icon('home')}<span>Rezydencja</span></button><div class="map-caption"><span>01 / MIASTO MOŻLIWOŚCI</span><span>Wybierz miejsce na mapie ${icon('arrow')}</span></div></div>
 ${travelBox()}
 <aside class="hub-side">${miniMap()}${done<4?`<aside class="panel first-steps"><div class="panel-heading"><h2>Pierwsze kroki</h2><span class="step-count">${done} / 4</span></div><p class="section-note">Poznaj miasto we własnym tempie.</p><div class="onboarding-track"><span style="width:${done*25}%"></span></div>${steps.map(([text,yes,route],i)=>`<button class="step-item ${yes?'complete':''}" data-go="${route}"><span>${yes?icon('check'):String(i+1).padStart(2,'0')}</span><strong>${text}</strong>${icon('arrow')}</button>`).join('')}<div class="starter-note">${icon('info')}<p>Postęp należy do tego świata.<br><b>Czas i nagrody rozlicza serwer.</b><br>Te cele nie przyznają dodatkowych nagród.</p></div><div class="fast-start"><span>Potrzebujesz wskazówki?</span><button class="text-btn" data-online="tutorial">Otwórz samouczek ${icon('arrow')}</button></div></aside>`:''}</aside></div>
 <div class="activity-strip"><div><span class="dot"></span>OSTATNIO W TWOIM MIEŚCIE</div><p>${state.history.length?esc(state.history[0].text):'Twoja historia dopiero się zaczyna. Wybierz pierwszy kontrakt.'}</p><span class="tiny">Zapis serwerowy</span></div>`;
}
function tenderHTML(){
 const t=Network.packet?.catalog?.tender;if(!t)return '';
 const lvl=G.level(state.xp),done=state.tenderDone===t.day,full=state.contracts.length>=4,low=state.energy<t.energy,locked=lvl<t.level;
 return `<section class="panel tender-panel tender-bar"><div class="tb-ico">${icon('star')}</div><div class="tb-title"><strong>Przetarg dnia</strong><span class="tiny" data-countdown="${t.expires_at}">${timerText(t.expires_at-now())}</span></div><div class="tb-info"><strong title="${esc(t.name)}">${t.name}</strong><small>💸 <b class="tender-cash">${money(t.cash)}</b> · ⭐ ${t.xp} XP · ⚡ ${t.energy}${locked?` · 🔒 od poziomu ${t.level}`:''}${full?' · kolejka pełna':''}</small></div><div class="tb-side">${btn(done?'Przyjęty':'Przyjmij przetarg','tender-accept','',done||full||low||locked,done||full||low||locked?'btn':'btn btn-gold')}</div></section>`;
}
function districtsHTML(){
 const cat=Network.packet?.catalog||{},list=cat.districts||[];if(!list.length)return '';
 const cap=cat.investCap||20000;
 return `<section class="panel districts-panel"><div class="panel-heading"><h2>${icon('city')} Inwestycje dzielnicowe</h2><span class="tiny">+1% STAWKI ZA ${money(cat.investStep||1000)}</span></div><p class="section-note">Wspieraj legalne projekty w dzielnicach. Twoja inwestycja podnosi stawki Twoich kontraktów w danej dzielnicy (do +15%); suma miasta pokazuje, które dzielnice rosną najszybciej.</p><div class="district-grid">${list.map(d=>{const maxed=d.mine>=cap;return `<div class="district-row"><div class="district-info"><strong>${d.name}</strong><small>Twoje: ${money(d.mine)} · premia +${d.bonus}% · miasto: ${money(d.world)}</small></div><div class="district-actions">${[100,500,1000].map(a=>`<button class="btn" data-game="invest" data-district="${d.name}" data-amount="${a}" ${state.cash<a||maxed?'disabled':''} title="${maxed?'Osiągnięto limit inwestycji':''}">+${a} $</button>`).join('')}</div></div>`;}).join('')}</div></section>`;
}
function contractsView(){const lvl=G.level(state.xp);
 return heading('Praca i kontrakty','Każde zlecenie to krok dalej.','Kontrakty stoją w swoich lokalizacjach na mapie — pojedź, przyjmij, odbierz. Dalsze dzielnice płacą więcej.')+`
 ${tenderHTML()}
 <div class="game-summary-bar"><span>${icon('bolt')} <strong data-energy>${Math.floor(state.energy)}</strong> / 240 energii</span><span>${icon('clock')} Regeneracja: ${Math.round(regenPerHour())} / h</span><span>${icon('briefcase')} Kolejka: ${state.contracts.length} / 4</span></div>
 <div class="game-two-columns"><div class="contract-list">${G.CONTRACTS.map((c,i)=>{const full=state.contracts.length>=4,low=state.energy<c.energy,cur=Network.packet?.travelInfo?.district,era45=Network.packet?.era,lockD=!!c.d&&era45&&MAP_C[c.d]?.kind==='city'&&c.d>era45.districts,locked=lockD||lvl<c.level,away=!lockD&&!!c.d&&c.d!==cur,tv=Network.packet?.travelInfo?.travel;const pay=Math.round(c.cash*c.mult*(1+(c.hop||0)/100));return `<article class="contract-card${away?' away':''}"><div class="contract-art contract-art-${i}">${icon(c.icon)}<span>0${i+1}</span><small>${c.district}</small></div><div class="contract-body"><div class="contract-title"><span class="eyebrow">${c.district}${c.d?` · dzielnica ${c.d}`:''}</span><span class="tiny">${lockD?'Otwarcie w Erze '+(c.d<=3?1:c.d<=5?2:c.d<=7?3:4):!locked&&away?'Poza dzielnicą':'Dostępny'}</span></div><h2 title="${esc(c.name)}">${c.name}</h2><p>${c.description}</p><div class="contract-loc"><span>📍 Lokalizacja: ${c.district}${c.d?` (jedź z mapy)`:''}</span>${c.hop?`<b class="hop">🚆 +${c.hop}% za dojazd</b>`:''}</div><div class="contract-metrics"><span>${icon('clock')}${durationLabel(c.duration)}</span><span>${icon('bolt')}${c.energy} energii</span><span>${icon('star')}+${c.xp} XP</span></div><div class="contract-action"><strong>+${money(pay)}</strong>${Math.round(c.mult*100)!==100?`<small class="mult-badge ${c.mult>=1?'up':'down'}">${c.mult>=1?'+':''}${Math.round((c.mult-1)*100)}% dziś</small>`:''}${away&&!locked?`<button class="btn btn-gold" data-extra="contract-go" data-d="${c.d}" ${tv?'disabled':''}>🚌 Jedź (20 $)</button>`:''}${btn(lockD?'Zamknięte — otwarcie w kolejnej erze':!lockD&&locked?'Wymagany poziom '+c.level:full?'Kolejka pełna':low?'Brak energii':away?'Bądź w dzielnicy '+c.d:'Przyjmij kontrakt '+icon('arrow'),'start-contract',`data-contract="${c.id}" ${away?`title="Zlecenie czeka w ${esc(c.district)} — jedź tam z mapy."`:''}`,locked||full||low||away,'btn btn-gold')}</div></div></article>`;}).join('')}<p class="game-note">${icon('info')} Wynagrodzenie gwarantowane, bonus za dojazd wliczony. Energia pobierana przy przyjęciu; gotówkę i XP odbierasz po zakończeniu.</p></div><aside class="panel queue-panel"><div class="panel-heading"><h2>Twoje zlecenia</h2><span class="tiny">${state.contracts.length} / 4</span></div><p class="section-note">Zlecenia działają także po zamknięciu strony.</p><div class="queue-list">${taskCards('contracts')}</div></aside></div>
 ${districtsHTML()}`;
}
function courierArt(){return `<svg class="courier-art" viewBox="0 0 580 280" fill="none" aria-label="Budynek i samochód firmy kurierskiej" role="img"><path d="M30 237 289 104 552 231 292 278Z" fill="#22333d"/><path d="m133 108 147-69 142 69-143 71Z" fill="#74868a"/><path d="M133 108v104l146 68V179Z" fill="#344954"/><path d="M279 179v101l143-70V108Z" fill="#4b626b"/><path d="m146 106 134-59 126 61-127 63Z" fill="#9d9b80"/><path d="m168 113 80-36 108 47-78 37Z" fill="#667e85"/><path d="M168 113v15l110 49v-16M278 177l78-38v-15" fill="#344b58"/><path d="m300 180 51-24v71l-51 26Z" fill="#12212a"/><path d="m355 153 48-23v72l-48 24Z" fill="#1a2b35"/><path d="M306 188v49m8-53v49m8-53v49m8-53v49m8-53v49M363 164v47m9-51v47m9-51v47m9-51v47" stroke="#6e878e" stroke-width="2"/><path d="m151 140 100 47v17l-100-47Z" fill="#d2aa66"/><text x="175" y="83" transform="matrix(.9 .44 0 1 -14 8)" fill="#212c2c" font-size="13" font-weight="800" letter-spacing="2">CITY COURIER</text><g transform="translate(377 178)"><path d="m0 7 49-25 67 31-49 25Z" fill="#f0d19a"/><path d="M0 7v43l67 33V38Z" fill="#b88b50"/><path d="m67 38 49-25v43L67 83Z" fill="#dfb573"/><path d="m116 38 21 10 13 24-34 17-19-9V53Z" fill="#d8ae6b"/><path d="m120 48 13 6 8 15-21-10Z" fill="#304c61"/><ellipse cx="23" cy="62" rx="10" ry="14" fill="#111d28"/><ellipse cx="23" cy="62" rx="4" ry="7" fill="#708087"/><ellipse cx="123" cy="83" rx="9" ry="12" fill="#111d28"/><ellipse cx="123" cy="83" rx="4" ry="6" fill="#708087"/><path d="m11 28 40 19" stroke="#f9daa4" stroke-width="3"/></g><path d="m46 200 32-16 31 15-32 16Z" fill="#c09b69"/><path d="M46 200v23l31 15v-23Z" fill="#896b49"/><path d="m77 215 32-16v23l-32 16Z" fill="#a78156"/></svg>`;}
function businessView(){const b=state.business,rate=G.RATES[b.level-1],u=b.upgrade,next=b.level<7?G.RATES[b.level]:null,cost=Math.round(G.COSTS[b.level-1]*(1-statPct(state,1,0.3,15)/100)),vcap=1+statPct(state,0,2,40)/100;
 return heading('Twoje przedsiębiorstwa','Niech miasto pracuje dla Ciebie.','Rozwijaj firmę, odbieraj dochód i reinwestuj we własnym tempie.')+`
 <div class="business-layout"><div>${busGateNote()}<section class="business-hero"><div class="business-hero-copy"><span class="world-pill">LOGISTYKA · PRZEDMIEŚCIA</span><h2>City Courier</h2><p>Mała firma. Wielki potencjał.</p><span class="business-level">POZIOM ${b.level} <span>/ 7</span></span></div>${courierArt()}<div class="business-hero-bottom"><span><i class="dot"></i>Firma działa</span><span>Dochód netto · bez ukrytych opłat</span></div></section><div class="business-stats"><article><span>DOCHÓD NETTO</span><strong>${rate} <small>$ / h</small></strong></article><article><span>NA PEŁNĄ DOBĘ</span><strong>${money(rate*24)}</strong></article><article><span>POJEMNOŚĆ SKARBCA</span><strong>24 <small>godziny</small></strong></article></div><section class="panel upgrade-panel"><div class="panel-heading"><h2>Rozbudowa firmy</h2><span class="tiny">INWESTUJ W PRZYSZŁOŚĆ</span></div>${u?`<p class="section-note">Nowe stanowiska i usprawnienia logistyczne. Firma nadal zarabia podczas prac.</p><div class="upgrade-in-progress"><div>${icon('business')}<strong>Poziom ${b.level} → ${u.target}</strong><span data-countdown="${u.end}">${timerText(u.end-now())}</span></div><div class="task-progress"><span data-task-progress data-start="${u.start}" data-end="${u.end}" style="width:${100*(now()-u.start)/(u.end-u.start)}%"></span></div></div>`:next?`<p class="section-note">Wyższy poziom zwiększa dochód i pojemność skarbca. Prace trwają ${durationLabel(Network.packet?.catalog.upgradeDuration||600000)}.</p><div class="upgrade-comparison"><div><span>OBECNIE</span><strong>${rate} $ / h</strong></div>${icon('arrow')}<div><span>POZIOM ${b.level+1}</span><strong>${next} $ / h</strong></div></div><div class="upgrade-action"><span>Koszt: <b>${money(cost)}</b></span>${btn(state.cash<cost?'Potrzebujesz '+money(cost-state.cash)+' więcej':'Rozbuduj firmę '+icon('arrow'),'upgrade','',state.cash<cost,'btn btn-gold')}</div>`:`<p class="section-note">Osiągnięto maksymalny poziom firmy w tym prototypie.</p>`}</section></div><aside><section class="panel vault-panel"><div class="panel-heading"><h2>Skarbiec firmy</h2>${icon('wallet')}</div><p class="section-note">Twój dochód czeka na odbiór.</p><div class="vault-value" data-vault>${money(b.vault)}</div><div class="vault-cap">z ${money(rate*24*vcap)} pojemności${vcap>1?` (Siła +${Math.round((vcap-1)*100)}%)`:''}</div><div class="vault-track"><span data-vault-progress style="width:${b.vault/(rate*24*vcap)*100}%"></span></div>${btn(icon('wallet')+' Odbierz dochód','collect','id="collect-income"',b.vault<1,'btn btn-gold full-width')}<p class="game-note">${icon('info')} Pełny skarbiec zatrzymuje produkcję. Zgromadzone pieniądze nie znikają.</p></section><section class="panel time-panel"><span class="eyebrow">CZAS SERWEROWY</span><h3>Tempo świata: ×${Network.world?.speed||1}.</h3><p>Dochód i terminy są rozliczane na serwerze, także po zamknięciu przeglądarki.</p><button class="btn full-width" data-online="worlds">Zmień świat</button><small>Przyspieszenie świata testowego nie wpływa na standardowe światy.</small></section></aside></div>
 ${garageHTML()}${Network.cafeHTML(state)}`;
}
function storyDistinction(){
 const d=Network.packet?.distinction;
 if(!d)return '';
 const names={contract:'Kontrakt dnia',training:'Trening dnia',collect:'Dochód dnia',fund:'Wsparcie organizacji',invest:'Inwestycja dzielnicowa',remote:'Praca na PC dnia',rest:'Wypoczynek dnia'};
 if(d.claimed)return '<div class="story-distinction earned">'+icon('check')+'<div><strong>Dystynkcja dnia · '+esc(names[d.claimed.kind]||d.claimed.kind)+'</strong><small>Czysty zaszczyt — dystynkcje łącznie: '+d.count+'</small></div></div>';
 if(d.eligible)return '<div class="story-distinction ready"><div><strong>Dystynkcja dnia gotowa do odbioru</strong><small>Za: '+esc(names[d.pending.kind]||d.pending.kind)+'</small></div><button class="btn btn-gold" data-extra="distinction-claim">Odbierz</button></div>';
 return '<div class="story-distinction idle"><small>Wykonaj dziś jedną z czynności — kontrakt, trening, odbiór dochodu, wpłata do funduszu albo inwestycja dzielnicowa — i odbierz codzienną dystynkcję. Czysto kosmetyczna, bez premii.</small></div>';
}
function dailyChart(rows){
 const data=(rows||[]).slice().reverse();
 if(!data.length||!data.some(r=>r.deeds||r.cash))return '<div class="daily-chart empty"><small>Brak aktywności w ostatnich 14 dniach — kontrakt, trening, odbiór, wpłata albo inwestycja i tu urośnie wykres.</small></div>';
 const maxD=Math.max.apply(null,data.map(r=>r.deeds).concat([1]));
 const maxC=Math.max.apply(null,data.map(r=>r.cash).concat([1]));
 const w=20;let bars='';
 data.forEach((r,i)=>{const x=i*w;const hd=Math.round(30*r.deeds/maxD);const hc=Math.round(30*r.cash/maxC);
  const t=new Date(r.day).toLocaleDateString('pl-PL',{day:'2-digit',month:'2-digit'}); 
  bars+='<g><title>'+t+' · czyny: '+r.deeds+' · gotówka: '+r.cash.toLocaleString('pl-PL')+' $ · XP: '+r.xp+'</title>';
  bars+='<rect class="dc-deeds" x="'+(x+2)+'" y="'+(32-hd)+'" width="7" height="'+Math.max(hd,r.deeds?2:0)+'" rx="2"><title>czyny: '+r.deeds+'</title></rect>';
  bars+='<rect class="dc-cash" x="'+(x+11)+'" y="'+(32-hc)+'" width="7" height="'+Math.max(hc,r.cash?2:0)+'" rx="2"><title>gotówka: '+r.cash+'</title></rect></g>';
 });
 return '<div class="daily-chart"><div class="dc-head"><span>OSTATNIE 14 DNI</span><span class="dc-legend"><i class="lg-deeds"></i>czyny <i class="lg-cash"></i>gotówka</span></div><svg viewBox="0 0 '+Math.max(data.length*w,40)+' 34" preserveAspectRatio="none" role="img" aria-label="Aktywność z 14 dni">'+bars+'</svg></div>';
}

const TRAVEL_DISTRICTS=[[1,'Nadmorskie'],[2,'Przemysłowe'],[3,'Centrum'],[4,'Portowe'],[5,'Biznesowe'],[6,'Sportowe'],[7,'Kopalnia'],[8,'Lasy Wschodnie']];
function travelBox(){
 const t=Network.packet?.travelInfo;if(!t)return '';
 if(t.travel)return '<div class="travel-box on-road">'+eraChip(Network.packet?.era)+'<div class="panel-heading"><h2>W drodze</h2><span class="tiny">MAPA MIASTA · 8 DZIELNIC</span></div><p class="section-note">Kierunek: <strong>'+esc(t.travel.toName)+'</strong> · transport: '+esc(t.travel.mode)+' · przyjazd za <span data-countdown="'+t.travel.until+'">'+timerText(t.travel.until-now())+'</span>.</p><p class="game-note">'+icon('info')+' Podczas drogi kontrakty i treningi stacjonarne czekają na przyjazd.</p><button class="btn" data-extra="travel-arrive">Ogłoś przyjazd</button></div>';
 const era=Network.packet?.era,unlock=era?era.districts:8,eraOf=d=>d<=3?1:d<=5?2:d<=7?3:4;
 const opts=TRAVEL_DISTRICTS.filter(d=>d[0]!==t.district).map(d=>d[0]>unlock?'<option value="'+d[0]+'" disabled>'+esc(d[1])+' · Era '+eraOf(d[0])+' 🔒</option>':'<option value="'+d[0]+'">'+esc(d[1])+'</option>').join('');
 const modes=[['bus','Bus · 20 $ · 5 min za dzielnicę'],['hitchhike','Autostop · 0 $ · '+Math.round(3*(1-statPct(state,2,1.0,25)/100))+'-'+Math.round(10*(1-statPct(state,2,1.0,25)/100))+' min · '+Math.max(3,15-statPct(state,2,0.5,12))+'% szansy na -10 energii'],['car','Własne auto · wymaga sprawnego pojazdu · 20% czasu busa']];
 return '<div class="travel-box">'+eraChip(Network.packet?.era)+'<div class="panel-heading"><h2>Mapa miasta · podróże</h2><span class="tiny">JESTEŚ W: '+esc(t.districtName)+'</span></div><div class="travel-form"><label class="field" for="travel-target"><span>Dokąd jedziesz?</span><select id="travel-target">'+opts+'</select></label><label class="field" for="travel-mode"><span>Transport</span><select id="travel-mode">'+modes.map(m=>'<option value="'+m[0]+'">'+m[1]+'</option>').join('')+'</select></label><button class="btn btn-gold" data-extra="travel-go">Wyrusz w drogę</button></div><p class="game-note">'+icon('info')+' Firmy stoją w Zakładach Miejskich (dzielnica 2) — rozbudowa i odbiór dochodów wymagają pobytu na miejscu. W podróży praca stacjonarna odpoczywa.</p></div>';
}
function busGateNote(){
 const t=Network.packet?.travelInfo;
 if(!t||t.district===2)return '';
 const away=t.traveling?'<small>Jesteś w drodze — zarządzanie firmami odblokuje się po przyjeździe.</small>':'<button class="btn btn-gold" data-extra="biz-go">🚌 Pojedź do Strefy Przemysłowej</button><small>Autostop: 0 $ · Bus: 20 $.</small>';
 return '<div class="biz-away"><div><strong>Firmy działają w Strefie Przemysłowej (dzielnica 2).</strong><small>Odbiór dochodu, rozbudowa i nowe firmy wymagają pobytu na miejscu — jedziesz?</small></div>'+away+'</div>';
}
function dungeonPanelHTML(){return `<section class="panel dungeon-panel"><div class="panel-heading"><h2>Brama Lochu</h2><span class="tiny">WYPRAWA · 8 ENERGII / PIĘTRO</span></div>${(()=>{const dg=Network.packet?.dungeon;if(!dg)return '<p class="section-note">Loch jeszcze się ładuje…</p>';const bar='<div class="dungeon-track"><span style="width:'+dg.progress+'%"></span></div><div class="dungeon-meta"><span>Postęp: <b>'+dg.progress+'%</b></span><span>'+(dg.completed?'Loch opanowany 💯':'Piętro '+(dg.nextFloor?dg.nextFloor.n:'—')+' z 10')+'</span></div>';const loot=(dg.loot&&dg.loot.length)?'<div class="dungeon-loot">'+dg.loot.map(id=>'<span class="loot-chip">🎁 '+esc(dg.lootNames[id]||id)+'</span>').join('')+'</div>':'';if(dg.completed)return bar+'<p class="section-note">Cały Loch Twój. Nowy zjazd wkrótce.</p>'+loot;if(!dg.atGate)return bar+'<p class="section-note">Wejście prowadzi spod Bramy Lochu (lokacja).</p><button class="btn btn-gold" data-dungeon-go>Przejdź do: Brama Lochu</button>'+loot;if(dg.locked)return bar+'<p class="section-note">🔒 Loch odblokowuje się na <b>3. poziomie</b> — zdobywaj XP w kontraktach i pracach.</p>'+loot;const nf=dg.nextFloor;const tacName={presja:'Presja',kontrola:'Kontrola',kontra:'Kontra'}[dg.tactic];return bar+'<p class="section-note">Piętro '+nf.n+': <b>'+esc(nf.name)+'</b> ('+((CLASS_META[nf.cls]||['🎖️',nf.cls])[1])+'). Na stole: <b>'+nf.cash+' $</b> i '+nf.xp+' XP.</p><div class="dungeon-actions"><button class="btn btn-gold" data-dungeon-fight>⚔️ Walcz'+(tacName?' · taktyka: '+tacName:'')+'</button></div><p class="tiny">Jedna taktyka na całą wyprawę — ta sama, którą walczysz w PvP (wybór jednorazowy). Porażka kosztuje tylko energię.</p>'+loot;})()}</section>`;}
function characterView(){const bonus=G.bonuses(state),lvl=G.level(state.xp),nextXp=G.xpAt(lvl+1),baseXp=G.xpAt(lvl);const avCat=(window.CityAvatar&&window.CityAvatar.catalog&&window.CityAvatar.catalog.gameLooks)?window.CityAvatar.cfgFromState(state):null;const playerArt=window.CityAvatar&&avCat?'<div class="av-fighter">'+window.CityAvatar.svg(avCat,{animate:true})+'</div>':portrait(false).replaceAll('-a','-player');
 return heading('Siłownia','Trening czyni mistrza.','Statystyki, trening za energię i wyposażenie — wszystko, co buduje formę.')+bldBar('gym')+`
 <div class="character-layout"><section class="panel player-profile"><div class="eyebrow">TWOJA POSTAĆ</div><div class="profile-portrait">${playerArt}</div><h2>${esc(Network.character?.nickname||'Postać')} <span>Poziom ${lvl}</span><button class="btn" data-extra="avatar-edit" style="margin-left:auto;font-size:9px;padding:7px 10px" title="Zmień wygląd awatara">🧍 Edytuj awatara</button></h2><p>Mieszkaniec ${esc(Network.world?.name||'świata')} · własna droga</p>${(()=>{const ct=Network.character?.classType;if(!ct)return '';const meta=CLASS_META[ct]||['🎖️',ct];const loc=LOC_META[Network.character?.currentLocation]||Network.character?.currentLocation||'ulica';const code=Network.character?.evolutionCode;const em=code?EVO_META[code]:null;const line=`<p class="class-line">${meta[0]} <b>${meta[1]}</b> · ${em?`${em[0]} <b>${em[1]}</b> („${em[2]}")`:'bez ewolucji'} · Lokacja: ${loc}${Network.character?.dungeonProgress?` · Loch: ${Network.character.dungeonProgress}%`:''}</p>`;const banner=!em&&lvl>=10?`<div class="evo-banner"><div class="eyebrow">DOSTĘPNA EWOLUCJA KLASOWA!</div><div class="evo-cards" role="radiogroup" aria-label="Ewolucja klasowa">${(CLASS_EVOS[ct]||[]).map(c=>{const x=EVO_META[c];return `<label class="evo-card"><input type="radio" name="evo-choice" value="${c}"><span class="class-icon">${x[0]}</span><b>${x[1]}</b><span class="class-passive">„${x[2]}”</span><span class="class-stats">${x[3]}</span></label>`;}).join('')}</div><button class="btn btn-gold" data-extra="evolve">Wybierz Ewolucję</button><p class="tiny">Wybór jednorazowy i nieodwracalny. Pasywka działa w PvP i w Lochu.</p></div>`:'';return line+banner;})()}<div class="xp-track"><span style="width:${100*(state.xp-baseXp)/(nextXp-baseXp)}%"></span></div><div class="xp-label"><span>${state.xp} XP</span><span>Następny poziom: ${nextXp} XP</span></div><div class="profile-total"><span>SUMA STATYSTYK</span><strong>${G.effective(state).reduce((a,b)=>a+b,0)}</strong><small>Podstawa + wyposażenie</small></div><div class="profile-look"><div class="eyebrow">WYGLĄD PROFILU</div><div class="skin-options">${(()=>{const shop=Network.packet?.shop;if(!shop)return '<p class="tiny">Sklep jeszcze niezaładowany.</p>';const owned=shop.ownedSkins||[];const names={ '':'Domyślna',skin_copper:'Miedź',skin_gold:'Złoto',skin_neon:'Neon'};return [''].concat(owned).map(k=>`<button class="btn skin-chip${(shop.skin||'')===k?' active':''}" data-extra="skin-equip" data-skin="${k}">${names[k]||k}${k==='skin_gold'&&shop.vipActive?' · VIP':''}</button>`).join('')})()}</div><p class="tiny">Skórki to czysta kosmetyka (rama profilu) — zero statystyk. Kupisz je w Sklepie.</p></div></section>
 ${statsInAction(bonus)}
 <div class="equipment-heading"><div><div class="eyebrow">PRZYGOTUJ SIĘ DO ARENY</div><h2>Twoje wyposażenie</h2></div><span class="tiny">7 MIEJSC · BEZ LOSOWYCH SKRZYNEK</span></div><div class="eq-doll"><div class="eq-grid">${(()=>{const cell=slot=>{const id=state.equipped[slot],item=id?G.ITEMS.find(x=>x.id===id):null;return item?`<div class="equipment-slot eq-cell eq-filled" data-eq-slot="${slot}"><span class="equipment-art ${item.price?'upgraded':''}">${icon(SLOT_ICONS[slot])}</span><span class="tiny">${SLOT_NAMES[slot]}</span><h3>${item.name}</h3><p>${bonusText(item)}</p><span class="equipped-badge">${icon('check')} Założone</span></div>`:`<div class="equipment-slot eq-cell eq-empty" data-eq-slot="${slot}"><span class="equipment-art">${icon(SLOT_ICONS[slot])}</span><span class="tiny">${SLOT_NAMES[slot]}</span><h3>Pusty slot</h3><p>Kup sprzęt w „Sklepie i plecaku” poniżej — „Załóż” wskakuje tu jednym klikiem.</p></div>`;};return cell('amulet')+cell('shirt')+cell('backpack')+cell('gloves')+`<div class="eq-cell eq-figure">${playerArt}<span class="eq-nick">${esc(Network.character?.nickname||'Zawodnik')}</span><small>Twoja postać · wygląd z założonych rzeczy</small></div>`+cell('accessory')+cell('helmet')+cell('shoes')+`<button class="eq-cell eq-edit" data-extra="avatar-edit" title="Edytuj wygląd awatara"><span class="eq-gi">🎲</span><span class="tiny">Wygląd</span><em>Edytuj awatara</em></button>`;})()}</div><p class="tiny eq-hint">Ekwipunek jak w klasycznych RPG: siedem slotów wokół zawodnika — co założysz, widać na awatarze (też w PvP i przy wyborze świata). „Załóż” w „Sklepie i plecaku” podmienia przedmiot w slocie.</p></div>
 <section class="panel gear-shop"><div class="panel-heading"><h2>Sklep i plecak</h2><span class="tiny">PŁATNOŚĆ GOTÓWKĄ Z GRY</span></div><p class="section-note">Kupujesz konkretny przedmiot. Możesz swobodnie zmieniać posiadane wyposażenie.</p><div class="gear-filters" role="group" aria-label="Filtr wyposażenia">${[['all','Wszystko'],...Object.entries(SLOT_NAMES)].map(([key,name])=>`<button class="${itemFilter===key?'active':''}" data-filter="${key}" aria-pressed="${itemFilter===key}">${name}</button>`).join('')}</div><div class="gear-list">${G.ITEMS.filter(i=>itemFilter==='all'||i.slot===itemFilter).map(item=>{const owned=state.inventory.includes(item.id),equipped=state.equipped[item.slot]===item.id,locked=G.level(state.xp)<(item.level||1),uniq=item.unique,buyPrice=Math.round(item.price*(1-statPct(state,3,0.3,9)/100));return `<article class="gear-item"><div class="gear-icon ${item.price?'upgraded':''}">${icon(SLOT_ICONS[item.slot])}</div><div class="gear-info"><strong>${item.name}</strong><small>${bonusText(item)}</small></div><span class="gear-price">${owned?'W plecaku':uniq?'Skarb Lochu 💎':buyPrice<item.price?`<s>${money(item.price)}</s> ${money(buyPrice)}`:money(item.price)}</span>${btn(equipped?'Założone':owned?'Załóż':uniq?'Tylko z Lochu':locked?'Od poziomu '+item.level:'Kup i załóż',owned?'equip':'buy',`data-item="${item.id}"`,equipped||(!owned&&(uniq||locked||state.cash<buyPrice)),!owned?'btn btn-gold':'btn')}</article>`;}).join('')}</div></section>`;
}
// === 0.59.0 — Chmurka powiadomień: dzwonek + dymek (gotowe do odbioru + zdarzenia serwera) ===
let notifSeen=null,notifOpen=false;
function notifReady(time){const out=[],st=state;
 const rr=((st.npcRoutes||{}).runs||[]).filter(r=>(r.end||0)<=time).length;if(rr)out.push({k:'routes',ico:'🚚',t:'Trasy NPC gotowe: '+rr,go:'garage'});
 const cc=(st.contracts||[]).filter(t=>(t.end||0)<=time).length;if(cc)out.push({k:'contracts',ico:'💼',t:'Kontrakty do odbioru: '+cc,go:'contracts'});
 const tt=(st.training||[]).filter(t=>(t.end||0)<=time).length;if(tt)out.push({k:'training',ico:'💪',t:'Trening zakończony: '+tt,go:'character'});
 if(st.rest&&(st.rest.end||0)<=time)out.push({k:'rest',ico:'🛋️',t:'Odpoczynek gotowy do odbioru',go:'residence'});
 return out;}
function notifEl(){let b=document.getElementById('notif-bell');if(b)return b;
 b=document.createElement('div');b.id='notif-bell';b.innerHTML='<button type="button" class="notif-btn" aria-label="Powiadomienia">🔔<span class="notif-count" hidden></span></button><div class="notif-cloud" hidden></div><div class="notif-pop" hidden></div>';document.body.appendChild(b);
 b.querySelector('.notif-btn').onclick=()=>{notifOpen=!notifOpen;renderNotif();};
 b.addEventListener('click',async e=>{const go=e.target.closest('[data-notif-go]');if(go){notifOpen=false;showView(go.dataset.notifGo);renderNotif();return;}
  if(e.target.closest('[data-notif-read]')){try{await Network.api(`/worlds/${Network.world.id}/events/read`,'POST',{all:true});}catch(_){}Network.eventsUnread=0;(Network.packet.eventsRecent||[]).forEach(x=>x.read=true);Network.updateBadge&&Network.updateBadge();renderNotif();}});
 document.addEventListener('click',e=>{if(notifOpen&&!e.target.closest('#notif-bell')){notifOpen=false;renderNotif();}});
 return b;}
function renderNotif(){if(!Network.world||!state){const o=document.getElementById('notif-bell');if(o)o.hidden=true;return;}
 const b=notifEl();b.hidden=false;const ready=notifReady(now()),unread=Network.eventsUnread||0,n=ready.length+unread;
 const c=b.querySelector('.notif-count');c.hidden=!n;c.textContent=n>9?'9+':String(n);b.classList.toggle('has',!!n);
 const keys=ready.map(r=>r.k).join(',');
 if(notifSeen!==null){const fresh=ready.filter(r=>!notifSeen.split(',').includes(r.k));if(fresh.length){const pop=b.querySelector('.notif-pop');pop.textContent=fresh[0].ico+' '+fresh[0].t;pop.hidden=false;clearTimeout(renderNotif._t);renderNotif._t=setTimeout(()=>{pop.hidden=true;},4500);}}
 notifSeen=keys;
 const cloud=b.querySelector('.notif-cloud');cloud.hidden=!notifOpen;if(!notifOpen)return;
 const evs=Network.packet?.eventsRecent||[],txt=e=>{try{return Extras.eventText(e);}catch(_){return 'Zdarzenie: '+e.kind;}};
 cloud.innerHTML=`<div class="notif-head"><b>Powiadomienia</b>${unread?`<button type="button" class="text-btn" data-notif-read>Oznacz przeczytane</button>`:''}</div>`+
  `<div class="notif-sec">GOTOWE DO ODBIORU</div>`+(ready.length?ready.map(r=>`<button type="button" class="notif-item ready" data-notif-go="${r.go}"><span>${r.ico}</span>${esc(r.t)}</button>`).join(''):'<p class="notif-empty">Nic nie czeka — kolejka pracuje.</p>')+
  `<div class="notif-sec">ZDARZENIA</div>`+(evs.length?evs.map(e=>`<div class="notif-item${e.read?'':' unread'}" data-notif-ev="${e.id}"><span>${e.read?'•':'🔵'}</span>${esc(txt(e))}</div>`).join(''):'<p class="notif-empty">Brak zdarzeń.</p>');}
function updateDynamic(){const time=now();
 renderNotif();
 (()=>{const hc=$('#hud-car');if(!hc)return;const v=state.vehicle&&state.vehicle.id?state.vehicle:null;const cv=v?(Network.packet?.catalog?.vehicles||[]).find(x=>x.id===v.id):null;hc.hidden=!cv;if(!cv)return;$('#hud-car-name').textContent=cv.name;const w=v.wear||0,we=$('#hud-car-wear');we.textContent=w>=100?'serwis!':w+'%';we.classList.toggle('bad',w>=100);hc.classList.toggle('worn',w>=100);})();
 $('#hud-cash').textContent=money(state.cash);$('#hud-energy').textContent=`${Math.floor(state.energy)} / 240`;$('#hud-energy-fill').style.width=(state.energy/240*100)+'%';$('#hud-xp').textContent=state.xp.toLocaleString('pl-PL')+' XP';$('#hud-level').textContent='Poziom '+G.level(state.xp)+' · '+(Network.world?.name||'Świat');
 $$('[data-vault]').forEach(el=>el.textContent=money(state.business.vault));$$('[data-vault-progress]').forEach(el=>el.style.width=(100*state.business.vault/(24*G.RATES[state.business.level-1]))+'%');
 $$('[data-energy]').forEach(el=>el.textContent=Math.floor(state.energy));
 $$('[data-countdown]').forEach(el=>el.textContent=timerText(+el.dataset.countdown-time));
 if(typeof updateTravelOverlay==='function')updateTravelOverlay();
 $$('[data-task-progress]').forEach(el=>el.style.width=(100*Math.max(0,Math.min(1,(time-(+el.dataset.start))/(+el.dataset.end-(+el.dataset.start)))))+'%');
 if($('#collect-income'))$('#collect-income').disabled=state.business.vault<1;
 $('#storage-notice').hidden=true;
 $('.hud-identity strong').textContent=Network.character?.nickname||'Postać';
 $('#nav-worlds span').textContent=Network.world?.name||'Wybierz świat';

}
function signature(){const t=now();return [state.business.level,!!state.business.upgrade,Math.floor(state.energy),...state.contracts.map(x=>x.id+':'+(t>=x.end?'ready':t>=x.start?'active':'wait')),...state.training.map(x=>x.id+':'+(t>=x.end?'ready':t>=x.start?'active':'wait')),state.rest?state.rest.id+':'+(t>=state.rest.end?'ready':'rest'):'norest',state.tenderDone||'',(state.vehicle?state.vehicle.id+state.vehicle.wear:'noveh')].join('|');}
function render(){if(view!=='arena'&&view!=='external')$('#view-'+view).innerHTML=({city:home,contracts:contractsView,business:businessView,character:characterView,residence:residenceView,garage:garageView,hall:hallView,cafe:cafeView,map:mapView})[view]();lastSignature=signature();updateDynamic();}

function renderRacing(){
 const box=document.getElementById('hipodrom');const r=Network.packet?.racing;
 if(!box)return;if(!r||playing){box.hidden=true;return;}
 box.hidden=false;
 const horses=r.horses||[];
 const horse=r.horse?'<div class="hp-horse"><strong>'+esc(r.horse.name)+'</strong><small>Szybkość '+r.horse.speed+' · Wytrzymałość '+r.horse.stamina+'</small></div>':horses.map(h=>'<button class="btn" data-extra="horse-buy" data-id="'+h.id+'"'+(r.level<h.level||state.cash<h.price?' disabled':'')+'>Kup: '+esc(h.name)+' · '+money(h.price)+' <small>(od poz. '+h.level+')</small></button>').join('');
 const canLevel=r.level>=r.hipLevel,canDistrict=r.district===r.hipDistrict;
 const gate=!canLevel?'Wymagany poziom '+r.hipLevel+'.':!canDistrict?'Tor czeka w '+esc(r.hipName)+' (dzielnica '+r.hipDistrict+') — pojedź z mapy miasta.':r.traveling?'Jesteś w drodze.':!r.horse?'Najpierw kup konia w stajni.':state.cash<r.entry?'Potrzebujesz '+money(r.entry-state.cash)+' na wpisowe.':'';
 const open=(r.open||[]).map(o=>'<div class="hp-row"><span>'+esc(o.creator)+' · wpisowe '+money(o.entry)+'</span><button class="btn btn-gold" data-extra="race-join" data-id="'+o.id+'">Dołącz</button></div>').join('')||'<small class="tiny">Brak otwartych wyścigów innych dżokejów.</small>';
 const recent=(r.recent||[]).map(rc=>'<div class="hp-row hp-result"><span>'+(rc.table||[]).map((e,i)=>'<b>'+(i+1)+'.</b> '+esc(e.name)+' <small>'+e.score+'</small>').join(' · ')+'</span><small class="tiny">'+({npc:'NPC',duel:'pojedynek',skoki:'skoki',ujezdzanie:'ujeżdżenie',wyscigi:'wyścigi'}[rc.kind]||rc.kind)+'</small></div>').join('')||'<small class="tiny">Jeszcze bez przejazdów — Twój pierwszy start pisze historię stajni.</small>';
 box.innerHTML='<div class="panel-heading"><h2>Hipodrom · zawody konne</h2><span class="tiny">ZAWODY UMIEJĘTNOŚCI · ZERO ZAKŁADÓW · WPISOWE '+money(r.entry)+'</span></div>'
  +'<p class="section-note">Wynik z charyzmy dżokeja (kondycja), sprytu na torze i statystyk konia. Pula wpisowych dzieli się 60/30/10 % dla miejsc 1–3. Puchar trafia do Kroniki Miasta i podnosi prestiż Twojej organizacji.</p>'
  +'<div class="hipo-grid"><div><h3 class="hp-title">Twoja stajnia</h3>'+(r.horse?horse:'<div class="hp-buy">'+horse+'</div>')+(r.stable&&r.stable.length?'<div class="stable-list">'+r.stable.map(h=>'<div class="stable-row'+(r.horse&&r.horse.name===h.name?' active':'')+'"><div><strong>'+esc(h.name)+'</strong><small>Szybkość '+h.speed+' · Wytrzymałość '+h.stamina+' · gen '+h.gen+'</small></div>'+(r.horse&&r.horse.name===h.name?'<span class="grade-chip">AKTYWNY</span>':'<button class="btn" data-extra="stable-pick" data-key="'+esc(h.key)+'">Ustaw aktywnego</button>')+'</div>').join('')+'</div>':'')+'<div style="margin-top:8px"><b>Hodowla</b> · 300 $'+(r.breedAt>(Network.packet?.serverTime||0)?' <small>(stajnia odpoczywa)</small>':'')+'</div><button class="btn" data-extra="breed"'+((r.stable&&r.stable.length>1&&!(r.breedAt>(Network.packet?.serverTime||0)))?'':' disabled')+'>🐾 Hoduj źrebaka (2 konie)</button></div>'
  +'<div><h3 class="hp-title">Start · wybierz konkurencję</h3><button class="btn btn-gold" data-extra="race-comp" data-comp="wyscigi"'+(gate?' disabled':'')+'>🏇 Wyścigi konne · '+money(r.entry)+'</button><button class="btn" data-extra="race-comp" data-comp="skoki"'+(gate?' disabled':'')+'>🦘 Skoki przez przeszkody · '+money(r.entry)+'</button><button class="btn" data-extra="race-comp" data-comp="ujezdzanie"'+(gate?' disabled':'')+'>🎗️ Ujeżdżenie · '+money(r.entry)+'</button><button class="btn" data-extra="race-open"'+(gate?' disabled':'')+'>Otwórz pojedynek o tor</button>'+(gate?'<p class="game-note">'+icon('info')+' '+esc(gate)+'</p>':'')+'</div>'
  +'<div><h3 class="hp-title">Otwarte pojedynki</h3>'+open+'</div>'
  +'<div><h3 class="hp-title">Ostatnie przejazdy</h3>'+recent+'</div></div>'
  +'<p class="game-note">'+icon('info')+' Nowe walki: Wyzwania PvP (od 2. poziomu) i Loch (od 3. poziomu) — obie korzystają z Twojej jednorazowej taktyki. Tutaj odtwarzasz raporty pojedynków.</p>';
}
const SPORTS=[['pvp','⚔️','Pojedynki PvP'],['boks','🥊','Boks/MMA'],['konie','🏇','Jazda Konna'],['agility','🐕','Agility Psów'],['silownia','🏋️','Wyzwania siłowe'],['luk','🎯','Łucznictwo'],['plywanie','🏊','Pływanie'],['ring','🐉','Ring']];
let sportTab='',sportsData=null,sportsFetched=false;
try{const t=localStorage.getItem('ce-sport-tab');if(t===''||t===null)sportTab='';else if(SPORTS.some(x=>x[0]===t))sportTab=t;}catch{}
function initSportTabs(){const hub=document.getElementById('club-hub');if(!hub)return;
 hub.innerHTML=bldBar('club')+SPORTS.map(x=>`<button class="club-card" role="tab" data-extra="sport-tab" data-tab="${x[0]}" aria-selected="${x[0]===sportTab}"><span class="club-ic">${x[1]}</span><b>${x[2]}</b></button>`).join('');
 applySportTab();}
function setSportTab(key){sportTab=key;try{localStorage.setItem('ce-sport-tab',key);}catch{}initSportTabs();}
function applySportTab(){const hub=document.getElementById('club-hub'),back=document.getElementById('club-back');
 if(hub)hub.hidden=!!sportTab;if(back)back.hidden=!sportTab;
 SPORTS.forEach(x=>{const pane=document.getElementById('sport-pane-'+x[0]);if(pane)pane.hidden=x[0]!==sportTab;});
 if(sportTab==='konie')renderRacing();
 if(['boks','agility','luk','plywanie'].includes(sportTab))refreshSportPanes();
 if(sportTab==='silownia')renderSilownia();
 if(sportTab==='pvp'&&typeof Network!=='undefined'&&Network.renderPvpPane)Network.renderPvpPane();
 if(sportTab==='ring'){const dg=document.getElementById('dungeon-pane');if(dg)dg.innerHTML=dungeonPanelHTML();}}
async function refreshSportPanes(){const wid=Network.world?.id;if(!wid||Network.busy&&false)return;
 try{const d=await Network.api('/worlds/'+wid+'/sports2');sportsData=d;}catch(e){sportsData=sportsData||null;}
 renderSportPanes();}
function clubPane(key){if(playing){toast('Najpierw zakończ animację.');return false;}showView('arena');setSportTab(key);$('.breadcrumb').innerHTML=esc(Network.world?.name||'Świat')+' <span>›</span> <strong>'+esc(({pvp:'Sala Klubowa · Pojedynki PvP',boks:'Sala Klubowa · Boks/MMA',konie:'Sala Klubowa · Jazda Konna',ring:'Sala Klubowa · Ring'})[key]||'Sala Klubowa')+'</strong>';return true;}
function sportPanel(title,sub,body){return '<div class="panel-heading"><h2>'+title+'</h2><span class="tiny">'+sub+'</span></div>'+body;}
function statRow(k,v){return '<div class="sport-stat"><span>'+k+'</span><b>'+v+'</b></div>';}
function renderSportPanes(){
 const dg=document.getElementById('dungeon-pane');if(dg)dg.innerHTML=dungeonPanelHTML();
 const d=sportsData;
 const tp=document.getElementById('agility-panel');
 if(tp)tp.innerHTML=sportPanel('🐕 Agility Psów · tor przeszkód','ZAWODY · WPISOWE 50 $ · ENERGIA 15','<p class="section-note">Prowadź psa przez tor: liczą się Refleks i Spryt. Za wynik dostajesz ocenę tresury (A–E), gotówkę i XP. Najlepszy wynik zostaje w karierze.</p><div class="sport-grid">'+statRow('Najlepszy wynik',d?d.agil.best:'—')+statRow('Przejścia',d?d.agil.runs:'—')+'</div><button class="btn btn-gold" data-extra="sport-run" data-kind="agility" style="margin-top:10px">🐕 Przebiegnij tor (50 $)</button><p class="game-note tiny">Ocena tresury: A ≥ 95 · B ≥ 80 · C ≥ 65 · D ≥ 50 · E poniżej.</p>');
 const lp=document.getElementById('luk-panel');
 if(lp)lp.innerHTML=sportPanel('🎯 Łucznictwo · PvP celności','ASYNC · WPISOWE 30 $ · ENERGIA 10','<p class="section-note">Osobny mini-system walki dystansowej: trafiaasz tarczę (Inteligencja + Refleks), a Twój wynik mierzy się z <b>zapisanym najlepszym wynikiem rywala z rankingu</b> — nie musi być online. Bez rywala: par Mistrza Kolegium.</p><div class="sport-grid">'+statRow('Twój rekord',d?d.luk.best:'—')+statRow('Wygrane',d?d.luk.wins:'—')+statRow('Porażki',d?d.luk.losses:'—')+statRow('Remisy',d?d.luk.draws:'—')+'</div><button class="btn btn-gold" data-extra="sport-run" data-kind="archery" style="margin-top:10px">🎯 Seria trzech strzał (30 $)</button>');
 const pp=document.getElementById('plywanie-panel');
 if(pp)pp.innerHTML=sportPanel('🏊 Pływanie · kondycja','BOOST CHARYZMY · ENERGIA 10','<p class="section-note">Trening pływacki buduje kondycję (max 30, okno 48 h). Kondycja podnosi <b>❤️ Charyzmę</b> we wszystkich walkach: +1 co 6 pkt kondycji (max +5).</p><div class="sport-grid">'+statRow('Kondycja',d?d.swim.kondycja:'—')+statRow('Bonus Charyzmy','+'+(d?d.swim.bonus:0))+'</div><button class="btn btn-gold" data-extra="sport-run" data-kind="swim" style="margin-top:10px">🏊 Trening w basenie</button>');
 const bp=document.getElementById('sport-pane-boks');
 if(bp&&d&&!document.getElementById('turniej-panel')){const t=document.createElement('section');t.className='panel';t.id='turniej-panel';bp.insertBefore(t,bp.firstChild);}
 const tn=document.getElementById('turniej-panel');
 if(tn&&d)tn.innerHTML=sportPanel('🥊 Turniej Klubu · Boks/MMA','PvE GAUNTLET · WPISOWE 200 $ · ENERGIA 30','<p class="section-note">Trzy walki wieczoru na Twojej taktyce (silnik PvP): Kolegialny Nowicjusz → Czeladnik Ringu → Mistrz Kolegium. 3/3 = 1200 $ + 150 XP · 2/3 = 400 $ + 60 XP. Limit 2 turnieje na dobę.</p><div class="sport-grid">'+statRow('Dzisiaj',d.tourn.runs+' / 2')+statRow('Najlepszy wieczór',d.tourn.best+' / 3')+'</div><button class="btn btn-gold" data-extra="sport-run" data-kind="tournament" style="margin-top:10px">🏆 Staw się na ringu (200 $)</button>');
}
function renderSilownia(){const sp=document.getElementById('silownia-panel');if(!sp)return;
 const tr=state.training||[];
 const slots=tr.map(t=>'<div class="stable-row"><div><strong>'+(t.stat!=null?['Siła','Inteligencja','Refleks','Charyzma','Spryt'][t.stat]:'Trening')+' · w toku</strong><small>Koniec: '+new Date(t.end).toLocaleTimeString('pl-PL',{hour:'2-digit',minute:'2-digit'})+'</small></div><button class="btn btn-gold" data-extra="gym-claim" data-id="'+t.id+'" '+(t.end>Date.now()?'disabled':'')+'>Odbierz</button></div>').join('');
 const train=[0,1,2,3,4].map(i=>'<button class="btn" data-extra="gym-train" data-stat="'+i+'" '+(tr.length>=2||state.energy<10?'disabled':'')+'>'+['Siła','Inteligencja','Refleks','Charyzma','Spryt'][i]+'</button>').join('');
 sp.innerHTML=sportPanel('🏋️ Siłownia · buff i trening','STATYSTYKI · REGENERACJA','<p class="section-note">Trening statystyk (energia + czas świata) i regeneracja przez odpoczynek w Rezydencji. Te same suwaki co w „Postać i trening” — wszystko rozlicza serwer.</p><div class="sport-grid"><div><h3 class="hp-title">Rozpocznij trening</h3><div style="display:flex;gap:6px;flex-wrap:wrap">'+train+'</div></div><div><h3 class="hp-title">W toku ('+tr.length+'/2)</h3>'+(slots||'<small class="tiny">Brak aktywnych treningów.</small>')+'</div></div><p class="game-note tiny">Regeneracja energii: odpoczynek w Rezydencji albo naturalna regeneracja co godzinę (tempo świata).</p>');
}

function arenaSync(force=false){const dp=document.getElementById('dungeon-pane');if(dp)dp.innerHTML=dungeonPanelHTML();if(!playing)renderRacing();if(playing)return;const lab=arenaMode==='lab';const fb=$('#fight-btn');if(fb)fb.hidden=!lab;
 if(Network.reportMode){$('#preset-0').disabled=true;$('#preset-1').disabled=true;$('[data-edit="0"]').disabled=true;$('[data-edit="1"]').disabled=true;return;}if(arenaMode==='character'){
 const sig=G.effective(state).join(',')+'|'+G.level(state.xp);if(force||sig!==activeArenaSignature){enemyMode='random';stats[0]=G.effective(state);selections[0]='custom';if(!['rookie','clubmate','challenger'].includes(selections[1])){selections[1]='rookie';stats[1]=presets.rookie.stats.slice();}clearMatch();renderConfig();activeArenaSignature=sig;}
 $('#preset-0').disabled=true;$('#preset-1').disabled=false;$('[data-edit="0"]').disabled=true;$('[data-edit="1"]').disabled=true;$('#preset-0 option:checked').textContent='Moja postać · '+G.effective(state).reduce((a,b)=>a+b,0)+' pkt';$('#fighter-sub-0').textContent='Poziom '+G.level(state.xp)+' · statystyki + wyposażenie';
 if(['rookie','clubmate','challenger'].includes(selections[1]))$('#fighter-sub-1').textContent='Partner treningowy · bez nagród';
 }else{$('#preset-0').disabled=false;$('#preset-1').disabled=false;$('[data-edit="0"]').disabled=false;$('[data-edit="1"]').disabled=false;}
 $('#view-arena .page-title .eyebrow').textContent=arenaMode==='character'?'Klub sportowy · Sparing bez nagród':'Laboratorium · Lokalny test bez rankingu';
}
function showView(next){if(next!=='external')Network.panel=null;if(next==='map')mapRecentre=true;if(playing&&next!==view){toast('Najpierw zakończ lub pomiń animację pojedynku.');return;}if(!['city','contracts','business','character','residence','garage','hall','cafe','arena','map','external'].includes(next))return;if(next==='arena'){initSportTabs();window.updateArenaAvatars&&window.updateArenaAvatars();}
 view=next;$$('.game-view').forEach(el=>el.hidden=el.id!=='view-'+view);$$('.nav-btn').forEach(el=>el.classList.toggle('active',el.id==='nav-'+(['garage','hall','cafe','character','residence','arena'].includes(view)?'city':view)));
 const titles={city:'Moje miasto',contracts:'Kontrakty',business:'Przedsiębiorstwo',character:'Postać i trening',residence:'Rezydencja',arena:'Klub sportowy',external:'Społeczność',map:'Mapa miasta'};$('.breadcrumb').innerHTML=esc(Network.world?.name||'Świat')+' <span>›</span> <strong>'+titles[view]+'</strong>';
 G.sync(state,now());render();if(view==='arena')arenaSync();prefs();window.scrollTo({top:0,behavior:'instant'});
}
async function act(payload){if(playing){toast('Najpierw zakończ pojedynek.');return;}await Network.action(payload);}
function fast(){toast('Czas jest rozliczany przez serwer. Do szybkich testów wybierz CITY LAB.');}
Object.assign(presets,{rookie:{name:'Nowicjusz · 50 pkt',stats:[10,10,10,10,10]},clubmate:{name:'Partner klubowy · 59 pkt',stats:[13,12,11,12,11]},challenger:{name:'Doświadczony rywal · 90 pkt',stats:[18,18,18,18,18]}});
const originalSetLocked=setLocked;setLocked=function(on){originalSetLocked(on);const hp=document.getElementById('hipodrom');if(hp)hp.hidden=!!on||!Network.packet?.racing;if(!on)arenaSync();};
const originalRenderConfig=renderConfig;renderConfig=function(){if(arenaMode==='character'&&!Network.reportMode&&!['rookie','clubmate','challenger'].includes(selections[1])){selections[1]='rookie';stats[1]=presets.rookie.stats.slice();}originalRenderConfig();if(arenaMode==='character'&&!Network.reportMode){$$('#preset-1 option').filter(o=>!['rookie','clubmate','challenger'].includes(o.value)).forEach(o=>o.remove());$('[data-edit="1"]').disabled=true;names[0]=Network.character?.nickname||'Postać';names[1]=({rookie:'Nowicjusz',clubmate:'Partner klubowy',challenger:'Doświadczony rywal'})[selections[1]];[0,1].forEach(i=>$('#fighter-'+i+' .fighter-name h2').textContent=names[i]);$('#preset-0').disabled=true;$('[data-edit="0"]').disabled=true;$('#fighter-sub-0').textContent='Poziom '+G.level(state.xp)+' · statystyki + wyposażenie';if($('#preset-0 option:checked'))$('#preset-0 option:checked').textContent='Moja postać · '+G.effective(state).reduce((a,b)=>a+b,0)+' pkt';}if(['rookie','clubmate','challenger'].includes(selections[1]))$('#fighter-sub-1').textContent='Partner treningowy · bez nagród';};
function setArenaMode(m){if(playing)return;Network.reportMode=false;arenaMode=m;activeArenaSignature='';if(m==='lab'){stats=[presets.free.stats.slice(),presets.vip.stats.slice()];selections=['free','vip'];clearMatch();renderConfig();save();}arenaSync(true);prefs();}
for(const name of ['city','contracts','business','map']){const nb=$('#nav-'+name);if(nb)nb.onclick=()=>showView(name);}
const originalResetArena=$('#reset-btn').onclick;$('#reset-btn').onclick=()=>{Network.reportMode=false;originalResetArena();if(arenaMode==='character')arenaSync(true);};
$('#nav-lab').onclick=()=>{if(!playing){showView('arena');if(arenaMode!=='lab')setArenaMode('lab');}$('#lab-dialog').showModal();};
$('#lab-exit').onclick=()=>{$('#lab-dialog').close();if(arenaMode!=='character')setArenaMode('character');};
$('#nav-report').onclick=()=>{showView('arena');if(view==='arena'){$('#report-panel').scrollIntoView({behavior:document.body.classList.contains('motion-off')?'instant':'smooth',block:'center'});$('#feed').focus({preventScroll:true});}};
$('.content').addEventListener('click',e=>{
 const mc=e.target.closest('[data-map-player]');
  if(mc&&!mapSuppress){mapOpenDm(+mc.dataset.mapPlayer);return;}else if(mc){}
  const mso=e.target.closest('[data-map-sound]');
  if(mso){const on=!mapSoundOn();try{localStorage.setItem('ce-sound',on?'1':'0');}catch{}mso.textContent=on?'🔊':'🔇';mso.title='Dźwięki podróży: '+(on?'włączone':'wyłączone');if(on)mapSound('depart');return;}
  const mev=e.target.closest('[data-map-event]');
  if(mev&&!mapSuppress){const ev=Network.packet?.cityEvent;if(!ev)return;const pct=Math.min(100,Math.round(100*(ev.progress||0)/Math.max(1,ev.target)));const ends=new Date(ev.endsAt).toLocaleString('pl-PL',{dateStyle:'short',timeStyle:'short'});
   Network.ui.dialog('Event miejski',`<p><b>${esc(ev.name)}</b></p>${ev.description?`<p class="section-note">${esc(ev.description)}</p>`:''}<p class="section-note">${ev.kind==='xp'?'Cel: XP całego miasta':'Cel: prestiż organizacji w dzielnicy '+esc(ev.district||'')} — ${(ev.progress||0).toLocaleString('pl-PL')} / ${(ev.target||0).toLocaleString('pl-PL')} ${ev.kind==='xp'?'XP':'$'} (${pct}%)</p><div class="contract-track ce-track"><span style="width:${pct}%"></span></div><p class="tiny">Działa do: ${ends}. Nagroda: odznaka Pioniera (kosmetyka).</p><button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById('network-dialog').close()">Zamknij</button>`);return;}
  const msn=e.target.closest('[data-map-season]');
  if(msn&&!mapSuppress){const sn=Network.packet?.era?.season;if(!sn)return;
   Network.ui.dialog('Sezon rankingowy '+sn.n,`<p class="section-note">🏁 Sezon <b>${sn.n}</b> kończy się za <b>${sn.daysLeft} dni</b>.</p><p>Po zakończeniu sezonu topka dostaje kosmetyczne tytuły (Mistrz/Elita/Lider), a świat wchodzi w nowy sezon. Liczy się XP całej kariery w globalnym rankingu.</p><button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById('network-dialog').close()">Zamknij</button>`);return;}
  const mph=e.target.closest('[data-map-photo]');
  if(mph){mapPhoto();toast('Obraz mapy zapisany (PNG).');return;}
  const mp=e.target.closest('[data-map-place]');
  if(mp&&!mapSuppress){const pl=MAP_PLACES[+mp.dataset.mapPlace];if(!pl)return;const era=Network.packet?.era,unlock=era?era.districts:8;
   const plArt=`<div class="map-dlg-art" style="background-image:url(/art/${MAP_ART[pl.d]||'city-map.jpg'})"><b>${pl.icon} ${pl.label}</b></div>`;
    const dlg=(html)=>Network.ui.dialog('Mapa · '+pl.label,plArt+html+'<button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById(\'network-dialog\').close()">Zamknij</button>');
   if(MAP_C[pl.d]&&MAP_C[pl.d].kind==='city'&&pl.d>unlock){const e2=pl.d<=3?1:pl.d<=5?2:pl.d<=7?3:4,en=ERAS_NAME[e2],days=eraDaysTo(era,e2);
    dlg(`<p class="section-note">🚧 <b>${esc(pl.label)}</b> to jeszcze plac budowy. Otwarcie w <b>Erze ${e2} (${en})</b> — za <b>${days==null?'?':days} dni</b>${era?` (dziś dzień ${era.day}/${era.total} świata)`:''}.</p><p class="section-note">Otwarte dzielnice: 1–${unlock}. Kliknij kafelek dzielnicy, aby zobaczyć władcę i podróż.</p>`);return;}
   const owned=pl.v==='courier'||(pl.v&&state.ventures[pl.v]);
   const cur=Network.packet?.travelInfo?.district,tv=Network.packet?.travelInfo?.travel,lvl=G.level(state.xp);
   const REQ={'Arena Pojedynków':[[lvl>=2,'Poziom 2+ (PvP od 2 lvl)'],[!!Network.character?.tactic,'Taktyka — wybór jednorazowy']],'Hipodrom':[[lvl>=5,'Poziom 5 (konie)'],[pl.d===6&&cur===6,'Bądź w Dzielnicy Kreatywnej (6)']],'Brama Lochu':[[lvl>=3,'Poziom 3 (wejście do lochu)']]};
   const reqs=(REQ[pl.label]||[]).map(r=>`<div class="map-req ${r[0]?'ok':'no'}">${r[0]?'✓':'✗'} ${r[1]}</div>`).join('');
   const cta=owned?`⭐ Twoje przedsiębiorstwo — zarządzaj nim`:(pl.v?`Lokuj tu swoją firmę`:`Przejdź do: ${MAP_GO_LABEL[pl.go]||pl.go}`);
   const fo=pl.v?mapPlayers.filter(x=>!x.own&&x.online&&(x.biz||{})[pl.v]):[];
   const rows=fo.map(x=>`<div class="biz-card"><span>🧍 <b>${esc(x.nickname)}</b> · Poziom ${x.level}${(x.biz[pl.v]||1)>1?' · firma poz. '+x.biz[pl.v]:''}</span><small class="tiny">${esc((MAP_C[x.district]||{name:''}).name)}${x.traveling?' · w drodze':''} · 🟢 online</small><button class="btn" data-dm-pid="${x.id}">Wyślij DM</button></div>`).join('');
   const owners=pl.v?(fo.length?`<p class="section-note">Prowadzą tu online (${fo.length}):</p>${rows}`:'<p class="tiny">Nikt online nie prowadzi tu jeszcze firmy.</p>'):'';
   dlg(`${mapRulerLine(pl.d)}<p>${esc(pl.info||'')}</p>${reqs?`<div class="map-reqs">${reqs}</div>`:''}${owners}<p class="section-note">${cta}</p><button class="btn btn-gold full-width" data-map-go="${pl.go}" data-map-tab="${pl.tab||''}" ${pl.d!==cur?`data-map-enter="${pl.d}" ${tv?'disabled':''}`:''}>${pl.d!==cur?`🚌 Jedź i wejdź (20 $)`:(owned?'Zarządzaj firmą':pl.v?'Lokuj firmę w Przedsiębiorstwach':'Wejdź: '+(MAP_GO_LABEL[pl.go]||pl.go))}</button>${pl.d!==cur?'<p class="tiny">Po przyjeździe autobusem wejście otwiera się automatycznie (akcje w dzielnicy ważne po przyjeździe).</p>':''}<button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById(\'network-dialog\').close()">Zamknij</button>`);
   return;}
const mcp=e.target.closest('[data-map-cpin]');
  if(mcp&&!mapSuppress){const cid=mcp.dataset.mapCpin,c=(Network.packet?.catalog?.contracts||[]).find(x=>x.id===cid);if(!c)return;const era=Network.packet?.era,cur=Network.packet?.travelInfo?.district,t=Network.packet?.travelInfo||{},tv=t.travel;
   const cpArt=`<div class="map-dlg-art" style="background-image:url(/art/${MAP_ART[c.d]||'city-map.jpg'})"><b>📍 ${esc(c.district)}</b></div>`;
    const dlg=(html)=>Network.ui.dialog('Zlecenie · '+c.name,cpArt+html+'<button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById(\'network-dialog\').close()">Zamknij</button>');
   if(c.d>(era?era.districts:8))return;
   const pay=Math.round(c.cash*(c.mult||1)*(1+(c.hop||0)/100));
   const away=c.d!==cur;
   dlg(`${mapRulerLine(c.d)}<p>${esc(c.description||'')}</p><p class="section-note">📍 <b>${esc(c.district)}</b> (dzielnica ${c.d}) · ⏱ ${Math.round(c.duration/60000)} min · ⚡ ${c.energy} energii · ⭐ +${c.xp} XP${c.level>1?` · 🔒 od poziomu ${c.level}`:''}</p><p class="section-note">💸 Wynagrodzenie: <b>${money(pay)}</b>${c.hop?` (w tym <b>+${c.hop}%</b> za dojazd — dalsze dzielnice płacą więcej)`:''}${c.mult&&Math.round(c.mult*100)!==100?` · rynek dziś: ${Math.round((c.mult-1)*100)>0?'+':''}${Math.round((c.mult-1)*100)}%`:''}</p>${away?`<p class="section-note">🚧 Jesteś w innej dzielnicy — najpierw pojedź (bus 20 $ albo autostop z mapy).</p>`:''}<button class="btn btn-gold full-width" data-map-go="contracts" ${away?`data-map-enter="${c.d}" ${tv?'disabled':''}`:''}>${away?'🚌 Jedź do zlecenia (20 $)':'Otwórz Zlecenia i przyjmij'}</button>${away?'<p class="tiny">Po przyjeździe przyjmujesz zlecenie w widoku Zlecenia — przycisk odblokuje się automatycznie.</p>':''}`);
   return;}
const md=e.target.closest('[data-map-d]');
  if(md&&!mapSuppress){const id=+md.dataset.mapD,era=Network.packet?.era,t=Network.packet?.travelInfo||{},unlock=era?era.districts:8;
   const D=MAP_C[id]||{},art=`<div class="map-dlg-art" style="background-image:url(/art/${MAP_ART[id]||'city-map.jpg'})"><b>${D.icon||''} ${D.name||('Dzielnica '+id)} · ${D.kind==='city'?'MIASTO':'ZAWSZE OTWARTA'}</b></div>`;
   const places=(id<=unlock||D.kind==='open')?`<div class="map-dlg-places">${MAP_PLACES.filter(p=>p.d===id).map(p=>`<button type="button" class="map-dlg-place" data-map-go="${p.go}" data-map-tab="${p.tab||''}" ${id!==t.district&&!t.travel?`data-map-enter="${id}"`:''}>${p.icon}<span><b>${p.label}</b><small>${p.info||''}</small></span>${icon('arrow')}</button>`).join('')}</div>`:'';
   const panel='';  // 2.1d GDD v3.1: panele wydobycia/skupu surowców usunięte
   const dlg=(html)=>Network.ui.dialog('Mapa · dzielnica '+id,art+html+panel+places+'<button class="btn full-width" style="margin-top:.6rem" onclick="document.getElementById(\'network-dialog\').close()">Zamknij</button>');
   if(D.kind==='city'&&id>unlock){const en={1:'Czas Pionierów',2:'Rozwój Przemysłu',3:'Wielki Biznes',4:'Metropolia & Epilog'},en2=d=>d<=3?1:d<=5?2:d<=7?3:4;const dd=eraDaysTo(era,en2(id));dlg(mapRulerLine(id)+`<p class="section-note">🔒 Dzielnica jeszcze nieaktywna. Otwarcie w <b>Erze ${en2(id)} (${en[en2(id)]})</b> — ${dd!=null?`za <b>${dd} dni</b> (dziś dzień ${era?era.day:'?'}/28, odliczanie jak na karcie świata)`:'cykl świata to 28 dni'}.</p><p class="section-note">Obecnie otwarte: 1–${unlock}. Plac budowy zamieni się w pełną dzielnicę z nowymi lokalizacjami.</p>`);}
   else if(t.travel)dlg(`<p class="section-note">Jesteś w drodze do <b>${esc(t.travel.toName)}</b>. Status podróży widoczny u góry ekranu.</p>`);
   else if(id===(t.district))dlg(mapRulerLine(id)+`<p class="section-note">Tu jesteś. 📍</p>`);
   else dlg(mapRulerLine(id)+`<p class="section-note">Podróż do <b>${esc((MAP_DISTRICTS.find(x=>x.id===id)||{}).name||'')}</b>.</p><div style="display:flex;gap:.5rem;margin-top:.5rem"><button class="btn btn-gold" data-map-travel="bus" data-map-d="${id}">🚌 Bus · 20 $</button><button class="btn" data-map-travel="hitchhike" data-map-d="${id}">🚶 Autostop · 0 $</button></div><p class="tiny">Autostop: 3–10 min, 15% szansy na −10 energii (Refleks pomaga).</p>`);
   return;}

  if(e.target.closest('[data-map-reset]')){MAPPAN.s=1;mapCenterOn(Network.packet?.travelInfo?.district||1);return;}
  const mq=document.getElementById('map-quick');if(mq&&!mq.hidden)mq.hidden=true;
  const mz=e.target.closest('[data-map-zoom]');
  if(mz){mapZoomBy(mz.dataset.mapZoom==='1'?1.15:0.87);return;}
  const nav=e.target.closest('[data-go]');if(nav){if(nav.dataset.go==='arena'&&!playing){arenaMode='character';activeArenaSignature='';}showView(nav.dataset.go);return;}
 const filter=e.target.closest('[data-filter]');if(filter){itemFilter=filter.dataset.filter;render();return;}
 const dismiss=e.target.closest('[data-away-dismiss]');if(dismiss){awayBox=null;render();return;}


});
document.addEventListener('click',e=>{
 const cg=e.target.closest('[data-club-grid]');if(cg){setSportTab('');return;}
 const button=e.target.closest('[data-game]');if(!button||button.disabled)return;
 const d=button.dataset;
 switch(d.game){
  case 'start-contract':act({action:'contract',contract:d.contract});break;
  case 'claim-contract':act({action:'claim_contract',task_id:+d.id});break;
  case 'train':act({action:'train',stat:+d.stat});break;
  case 'claim-training':act({action:'claim_training',task_id:+d.id});break;
  case 'collect':act({action:'collect',business:'courier'});break;
  case 'upgrade':act({action:'upgrade',business:'courier'});break;
  case 'buy':act({action:'buy',item:d.item});break;
  case 'equip':act({action:'equip',item:d.item});break;
  case 'fast':fast();break;
  case 'buy-residence':act({action:'buy_residence',residence:d.residence});break;
  case 'buy-vehicle':act({action:'buy_vehicle',vehicle:d.vehicle});break;
  case 'equip-vehicle':act({action:'equip_vehicle',vehicle:d.vehicle});break;
  case 'service-vehicle':act({action:'service_vehicle'});break;
  case 'upgrade-vehicle':act({action:'upgrade_vehicle',vehicle:d.vehicle});break;
  case 'hire-staff':act({action:'hire_staff',staff:d.staff});break;
  case 'tender-accept':act({action:'tender_accept'});break;
  case 'invest':act({action:'invest',district:d.district,amount:+d.amount});break;
 case 'upgrade-building':act({action:'upgrade_building',building:d.building});break;
  case 'rest-start':act({action:'rest_start',rest:d.rest});break;
  case 'rest-claim':act({action:'rest_claim'});break;
 case 'route-dispatch':{const sel=document.querySelector('[data-route-veh="'+d.route+'"]');act({action:'route_dispatch',route:d.route,vehicle:sel?sel.value:''});break;}
 case 'route-claim':act({action:'route_claim'});break;
 }
});
$('#game-settings-btn').onclick=()=>Network.showAccount();
(()=>{const hc=$('#hud-car');if(hc)hc.onclick=()=>{if(state.vehicle&&state.vehicle.id){showView('garage');}};})();
render();
setInterval(()=>{if(Network.character){if(signature()!==lastSignature&&view!=='arena'&&view!=='external')render();else updateDynamic();}},1000);
function install(packet){
 state=packet.state;Network.packet=packet;if(packet.away)awayBox=packet.away;
 if(view!=='external'&&view!=='arena')render();else updateDynamic();
 if(view==='arena'&&!playing)arenaSync();
}
function external(title,html,navId){
 if(playing){toast('Najpierw zakończ animację.');return false;}
 showView('external');$('#view-external').innerHTML=html;$$('.nav-btn').forEach(b=>b.classList.toggle('active',b.id===navId));$('.breadcrumb').innerHTML=esc(Network.world?.name||'Świat')+' <span>›</span> <strong>'+esc(title)+'</strong>';return true;
}
function prepareCharacter(){Network.reportMode=false;enemyMode='random';arenaMode='character';activeArenaSignature='';arenaSync(true);}
window.renderRacing=renderRacing;  // extras woła globalnie (naprawa cichego ReferenceError)
return {get state(){return state;},get view(){return view;},get tabNow(){return view==='arena'?sportTab:null;},clubPane,get arenaMode(){return arenaMode;},mapOpenDm,mapLoadPlayers,now,showView,render,install,external,prepareCharacter,setArenaMode,level:(...a)=>G.level(...a),sportTab:setSportTab,sportRefresh:()=>{refreshSportPanes();renderSilownia();}};
})();
