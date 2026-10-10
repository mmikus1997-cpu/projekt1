'use strict';
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const paths={arena:'<path d="M3 8h18v12H3zM3 12h18M3 16h18M5 4v17M19 4v17M8 8V5h8v3"/>',sliders:'<path d="M4 7h16M4 17h16M8 4v6M16 14v6"/>',report:'<path d="M6 3h9l4 4v14H6zM14 3v5h5M9 12h7M9 16h5"/>',book:'<path d="M12 5v15M12 5C8 2 5 3 2 4v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-3-1-6-2-10 1Z"/>',edit:'<path d="m15 4 5 5M4 20l5-1L21 7l-5-5L4 14z"/>',info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7v1"/>',shield:'<path d="m12 3 8 3v6c0 5-8 9-8 9s-8-4-8-9V6zM8 12l3 3 5-6"/>',bolt:'<path d="m14 2-10 12h7l-1 8 10-12h-7z"/>',target:'<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="4"/><path d="M12 1v4M12 19v4M1 12h4M19 12h4"/>',pause:'<path d="M8 5v14M16 5v14"/>',play:'<path d="m8 4 12 8-12 8z"/>',skip:'<path d="m4 5 11 7-11 7zM19 5v14"/>',download:'<path d="M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5"/>',activity:'<path d="M2 12h5l3-8 5 16 3-8h4"/>',replay:'<path d="M3 11a9 9 0 1 1 2 7M3 4v7h7"/>',trophy:'<path d="M7 3h10v7a5 5 0 0 1-10 0zM7 5H3v3a5 5 0 0 0 5 5M17 5h4v3a5 5 0 0 1-5 5M12 15v6M8 21h8"/>'};
const icon=n=>`<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[n]||paths.info}</svg>`;
Object.assign(paths,{helmet:'<path d="M4 13a8 8 0 0 1 16 0v2H4zM2 15h20M8 15v-3m8 3v-3M12 5v10"/>',backpack:'<path d="M6 8a6 6 0 0 1 12 0v13H6zM6 12h12M9 8V5h6v3M9 17h6"/>',amulet:'<path d="M12 3v4M8 7h8l-1.5 5a4.5 4.5 0 0 1-5 0zM9.5 12 8 21h8l-1.5-9"/>',map:'<path d="M9 4 3 6v14l6-2 6 2 6-2V4l-6 2-6-2zM9 4v14M15 6v14"/>',home:'<path d="m3 11 9-8 9 8M5 9.5V21h14V9.5M9 21v-6h6v6"/>',city:'<path d="M3 21V9l6-3v15M9 21V3h7v18M16 21V11h5v10M1 21h22M12 7h1m-1 4h1m-1 4h1"/>',briefcase:'<rect x="3" y="7" width="18" height="14" rx="2"/><path d="M8 7V3h8v4M3 12l9 3 9-3M12 12v5"/>',business:'<path d="M3 21V8h18v13M1 8l3-5h16l3 5M8 21v-7h8v7M1 21h22"/>',person:'<circle cx="12" cy="7" r="4"/><path d="M4 22v-3a8 8 0 0 1 16 0v3"/>',wallet:'<path d="M3 6h18v15H3V4l15-2v4M21 11h-7v5h7M16 13.5h1"/>',star:'<path d="m12 2 3 6 7 1-5 5 1 7-6-3-6 3 1-7-5-5 7-1z"/>',truck:'<path d="M2 5h12v12H2zM14 9h5l3 4v4h-8M16 9v5h6"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="19" r="2"/>',route:'<circle cx="5" cy="5" r="2"/><circle cx="19" cy="19" r="2"/><path d="M7 5h9a4 4 0 0 1 0 8H8a3 3 0 0 0 0 6h9"/>',clock:'<circle cx="12" cy="12" r="9"/><path d="M12 6v6l4 2"/>',arrow:'<path d="M4 12h16m-6-6 6 6-6 6"/>',check:'<path d="m5 12 4 4L20 5"/>',shirt:'<path d="m8 3-6 4 3 5 3-2v11h8V10l3 2 3-5-6-4c-2 3-6 3-8 0Z"/>',shoe:'<path d="M3 11V5h5l3 7 9 3q3 1 2 6H2v-7zM2 17h20M12 12l-2 3M15 13l-2 3"/>',glove:'<path d="M5 22v-7L3 9q-1-4 3-5l10-1q5 0 5 5v4q0 4-5 5v5zM5 18h11M8 5v4m4-5v4m4-4v4"/>',band:'<rect x="3" y="6" width="18" height="12" rx="5"/><path d="M8 6v12M16 6v12m-5-8 2 2-2 2"/>'});
function icons(root=document){root.querySelectorAll('[data-icon]').forEach(el=>el.outerHTML=icon(el.dataset.icon));}icons();
const labels=['Siła','Inteligencja','Refleks','Charyzma','Spryt'];const short=['Siła','Intel.','Refleks','Charyz.','Spryt'];const names=['Aleks','Maks'];
const presets={free:{name:'Bez zakupów · 162 pkt',stats:[33,33,32,32,32]},vip:{name:'VIP · 190 pkt',stats:[38,38,38,38,38]},max:{name:'VIP + energia · 246 pkt',stats:[50,49,49,49,49]},power:{name:'Uderzeniowy · 190 pkt',stats:[60,30,35,30,35]},technical:{name:'Techniczny · 190 pkt',stats:[35,50,45,30,30]},endurance:{name:'Wytrzymałościowy · 190 pkt',stats:[35,35,30,60,30]},counter:{name:'Kontrujący · 190 pkt',stats:[35,30,50,30,45]}};
let selections=['free','vip'],stats=[presets.free.stats.slice(),presets.vip.stats.slice()],tactic='kontrola',speed=1,enemyMode='random',current=null,step=0,playing=false,paused=false,timer=null,editSide=0,toastTimer,pendingEvent=null,actionClock=null,frameId=null;
function portrait(enemy){const id=enemy?'b':'a',accent=enemy?'#8caecf':'#e5bf7e',skin=enemy?'#a77b5c':'#d9a681',shadow=enemy?'#704b3c':'#996955',hair=enemy?'#29282a':'#3c3029',shirt=enemy?'#31475b':'#34382e',glove=enemy?'#547a9b':'#af8450';return `<svg class="art" viewBox="0 0 380 260" fill="none" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Ilustracja zawodnika ${enemy?'Maksa':'Aleksa'} w stroju sportowym"><defs><radialGradient id="glow-${id}"><stop stop-color="${accent}" stop-opacity=".23"/><stop offset="1" stop-color="${accent}" stop-opacity="0"/></radialGradient><linearGradient id="body-${id}" x1="130" y1="140" x2="245" y2="255" gradientUnits="userSpaceOnUse"><stop stop-color="${shirt}"/><stop offset="1" stop-color="#171f25"/></linearGradient><linearGradient id="skin-${id}" x1="170" y1="56" x2="225" y2="133" gradientUnits="userSpaceOnUse"><stop stop-color="${skin}"/><stop offset="1" stop-color="${shadow}"/></linearGradient><linearGradient id="fade-${id}" x1="0" y1="195" x2="0" y2="260" gradientUnits="userSpaceOnUse"><stop stop-color="#151c23" stop-opacity="0"/><stop offset="1" stop-color="#151c23"/></linearGradient></defs><ellipse class="portrait-glow" cx="190" cy="135" rx="175" ry="141" fill="url(#glow-${id})"/><circle cx="190" cy="135" r="103" stroke="${accent}" stroke-opacity=".13"/><circle class="portrait-orbit" cx="190" cy="135" r="86" stroke="${accent}" stroke-opacity=".1" stroke-dasharray="3 9"/><path d="M18 191h344M18 208h344M36 163v70M344 163v70" stroke="${accent}" stroke-opacity=".09"/><path d="M60 92v34M43 109h34M310 62v20M300 72h20" stroke="${accent}" stroke-opacity=".24"/><text x="${enemy?238:27}" y="163" fill="${accent}" opacity=".055" font-family="Arial,sans-serif" font-weight="900" font-size="94">${enemy?'02':'01'}</text><g ${enemy?'transform="translate(380 0) scale(-1 1)"':''}><g class="athlete"><g class="combat-body"><path d="M175 111 166 143 190 164 216 140 208 106" fill="${shadow}"/><path d="M178 109v22l15 12 12-14 1-20" fill="${skin}"/><path d="M163 135 130 144q-18 7-24 31l-13 79h196l-14-78q-5-22-29-31l-32-12-22 23z" fill="url(#body-${id})"/><path d="m163 135 28 24 23-26 11 5-33 35-37-33z" fill="${accent}" fill-opacity=".65"/><path d="m130 147-7 59M246 148l10 57" stroke="${accent}" stroke-opacity=".22" stroke-width="3"/><path d="m157 145-5 100M227 145l8 100" stroke="#fff" stroke-opacity=".07"/><path d="M165 73q-11-12-11 3v15q0 11 12 12M213 73q11-12 11 3v14q0 12-12 13" fill="${shadow}"/><path d="M162 49q26-24 54 3l1 42q-3 25-25 35-24-8-30-34z" fill="url(#skin-${id})"/><path d="m164 92 11 18 17 9 18-10-4 13-14 8-15-8-9-16z" fill="${hair}" fill-opacity=".65"/><path d="m166 72 14-2 4 3-15 2M197 72l13-2 4 5-15-1" fill="${hair}"/><path class="athlete-eyes" d="m172 80 8 1M200 81l8-1" stroke="#302b29" stroke-width="2.5" stroke-linecap="round"/><path d="m190 80-3 17 7 1" stroke="${shadow}" stroke-width="2"/><path d="m182 107 15 1" stroke="#644534" stroke-width="2" stroke-linecap="round"/>${enemy?`<path d="M159 71q-5-30 13-35 15-9 35 0 19 8 12 38l-6-12-4-13-18-6-24 10-1 15z" fill="${hair}"/><path d="m169 45 13-5 17 1" stroke="#54514b" stroke-width="2"/>`:`<path d="M161 72q-9-16-6-29 2-12 13-14l27-9 27 13-3 28-6 14-5-24-21 5-18-8-1 19z" fill="${hair}"/><path d="m162 39 27-11 21 7M169 44l22-10" stroke="#665044" stroke-width="3"/>`}<g class="arm-rear"><path d="m131 154-13 12q-10 19-14 37l-4 20q0 17 15 22 14 4 24-10l16-38-21-13-6 22-5-2 10-29" fill="url(#skin-${id})"/><path d="m137 192 21 8 5-12-24-11z" fill="#bfc2b6"/><path d="m139 183 22 9M138 188l22 9" stroke="#626e70"/><path d="m139 177-1-18q2-12 13-13 14-3 22 7l4 20q0 14-14 18l-24-10z" fill="${glove}"/><path d="m142 157 21-4 8 6M143 161l1 16" stroke="${accent}" stroke-opacity=".45" stroke-width="2"/></g><g class="arm-lead"><path d="M242 152q15 2 23 24l13 35q6 18-10 24-14 2-19-15l-13-40z" fill="url(#skin-${id})"/><g class="forearm"><path d="M272 233q-10 6-20-5l-36-40 18-16 39 42q8 12-1 19z" fill="url(#skin-${id})"/><path d="m219 196 19-15-7-10-24 16z" fill="#bfc2b6"/><path d="m214 184 20-13m-17 19 20-14" stroke="#626e70"/><path d="m206 185-7-24q-3-12 9-19 15-9 26 0l9 19q7 12-5 20l-21 14z" fill="${glove}"/><path d="m208 152 14-7 10 7M212 157l6 17" stroke="${accent}" stroke-opacity=".45" stroke-width="2"/></g></g><g class="punch-trail" aria-hidden="true" stroke="${accent}" stroke-linecap="round"><path d="M252 131q26-8 47 0" stroke-width="2"/><path d="M264 143q26-6 47 0" stroke-width="1"/></g><path d="M179 188h26v23h-26z" fill="#0c1319" fill-opacity=".5"/><path d="M185 204v-9h4v9m4 0v-13h4v13" stroke="${accent}" stroke-width="1.6"/></g></g><g class="contact-mark" aria-hidden="true" stroke="${accent}" stroke-width="1.6"><circle cx="190" cy="100" r="23"/><path d="m157 92-7-2m78 2 7-2m-47-23-1-7m13 76 3 7"/></g></g><g class="ambient-dust" aria-hidden="true"><circle cx="87" cy="138" r="1.2"/><circle cx="295" cy="192" r="1"/><circle cx="115" cy="87" r=".9"/><circle cx="262" cy="92" r="1.2"/></g><rect y="204" width="380" height="56" fill="url(#fade-${id})"/></svg>`;}
$('#portrait-0').innerHTML=portrait(false);$('#portrait-1').innerHTML=portrait(true);
// 0.47: portrety zawodników = żywe awatary (własny wygląd + założone rzeczy), a każdy cios
// pokazuje, czego zawodnik użył (rękawice/buty/hełm). Czysta prezentacja — wynik liczy serwer.
function escHtml(x){return String(x).replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function itemName(id){const list=(typeof Network!=='undefined'&&Network.packet?.catalog?.items)||[];const f=list.find(x=>x.id===id);return f?f.name:(id||'');}
function gearOf(side){
 if(current&&current.gear&&current.gear[side])return current.gear[side];
 if(side===0&&typeof Network!=='undefined'&&Network.packet?.state){const eq=Network.packet.state.equipped||{};return {gloves:eq.gloves,shoes:eq.shoes,helmet:eq.helmet};}
 return {};
}
function moveFor(side,round){
 const g=gearOf(side)||(side===1?{gloves:'basic-gloves',shoes:'basic-shoes',helmet:'basic-helmet'}:{});
 const moves=[];
 if(g.gloves)moves.push({icon:'🥊',label:'Cios',type:'fist',item:g.gloves,name:itemName(g.gloves)});
 if(g.shoes)moves.push({icon:'🦵',label:'Kop',type:'boot',item:g.shoes,name:itemName(g.shoes)});
 if(g.helmet)moves.push({icon:'🪖',label:'Uderzenie hełmem',type:'helm',item:g.helmet,name:itemName(g.helmet)});
 if(!moves.length)moves.push({icon:'🥊',label:'Cios',type:'fist',item:null,name:''});
 const m=moves[(round||0)%moves.length];
 if(window.CityAvatar&&m.item){const it=window.CityAvatar.item(m.item);if(it)m.colors=[it.c,it.c2];}
 return m;
}
function moveChip(side,round){
 const m=moveFor(side,round);
 return `<span class="move-chip">${m.icon} ${m.label}${m.name?' · '+escHtml(m.name):''}</span>`;
}
window.updateArenaAvatars=function(cfgB){
 if(!window.CityAvatar)return;
 const p0=$('#portrait-0'),p1=$('#portrait-1');if(!p0||!p1)return;
 let a=null,b=cfgB||null;
 if(typeof Network!=='undefined'&&Network.packet?.state)a=window.CityAvatar.cfgFromState(Network.packet.state);
 if(current&&current.avatars){a=window.CityAvatar.cfgFromState({avatar:{body:current.avatars[0].body,worn:current.avatars[0].layers||current.avatars[0].worn},equipped:{}});b=window.CityAvatar.cfgFromState({avatar:{body:current.avatars[1].body,worn:current.avatars[1].layers||current.avatars[1].worn},equipped:{}});}
if(a)p0.innerHTML='<div class="av-fighter">'+window.CityAvatar.svg(a,{animate:true})+'</div>';
 if(!b&&!current&&window.CityAvatar){const key=(typeof selections!=='undefined'&&selections[1])||'rookie';if(window.__sparKey!==key){window.__sparKey=key;window.__sparCfg=window.CityAvatar.random(false);}b=window.__sparCfg;}
 if(!b&&current&&current.demo&&window.CityAvatar)b={body:window.CityAvatar.random(false).body,worn:{shirt:'ts2',pants:'pt1',shoes:'bt1',gloves:'gl1'}};
 if(b)p1.innerHTML='<div class="av-fighter flip">'+window.CityAvatar.svg(b,{animate:true})+'</div>';
};
window.updateArenaAvatars();
function newSeed(){const a=new Uint32Array(1);if(globalThis.crypto?.getRandomValues){crypto.getRandomValues(a);return a[0];}return (Date.now()^Math.floor(Math.random()*4294967296))>>>0;}
const tacticLabel=t=>({presja:'Presja',kontrola:'Kontrola',kontra:'Kontra'})[t];
function toast(text){clearTimeout(toastTimer);$('#toast').textContent=text;$('#toast').hidden=false;toastTimer=setTimeout(()=>$('#toast').hidden=true,3400);}
function save(){try{localStorage.setItem('cityEmpireArenaV02',JSON.stringify({selections,stats,tactic,speed,enemyMode}));}catch{}}
function load(){try{const s=JSON.parse(localStorage.getItem('cityEmpireArenaV02'));if(!s)return;stats=s.stats.map(v=>{CityCombat.profile(v);return v;});if(stats.length!==2)throw Error();selections=s.selections.map((x,i)=>presets[x]&&presets[x].stats.every((v,j)=>v===stats[i][j])?x:'custom');tactic=s.tactic in CityCombat.BEATS?s.tactic:'kontrola';speed=[1,2,4].includes(s.speed)?s.speed:1;enemyMode=['random','presja','kontrola','kontra'].includes(s.enemyMode)?s.enemyMode:'random';}catch{selections=['free','vip'];stats=[presets.free.stats.slice(),presets.vip.stats.slice()];}}
function renderConfig(){if($('#combat-speed'))$('#combat-speed').textContent='Tempo: '+speed+'×';syncCombatControls();for(let i=0;i<2;i++){const select=$('#preset-'+i);select.innerHTML=Object.entries(presets).map(([key,p])=>`<option value="${key}">${p.name}</option>`).join('')+(selections[i]==='custom'?`<option value="custom">Własny zestaw · ${stats[i].reduce((a,b)=>a+b,0)} pkt</option>`:'');select.value=selections[i];$('#stats-'+i).innerHTML=stats[i].map((n,j)=>`<div class="stat-item" title="${labels[j]}"><span>${short[j]}</span><b>${n}</b></div>`).join('');$('#fighter-sub-'+i).textContent=selections[i]==='custom'?'Własny rozkład · tryb testowy':['power','technical','endurance','counter'].includes(selections[i])?'Specjalizacja · 190 punktów':'Rozwój zbalansowany · dzień 7';}$$('[data-tactic]').forEach(b=>{b.classList.toggle('selected',b.dataset.tactic===tactic);b.setAttribute('aria-pressed',b.dataset.tactic===tactic);});$$('[data-speed]').forEach(b=>{b.classList.toggle('selected',+b.dataset.speed===speed);b.setAttribute('aria-pressed',+b.dataset.speed===speed);});$('#opponent-tactic').value=enemyMode;}
function hpUpdate(values,max){values.forEach((h,i)=>{const pct=Math.max(0,100*h/max[i]);$('#hp-'+i).style.width=pct+'%';$('#hp-'+i).classList.toggle('low',pct<25);$('#hp-num-'+i).textContent=`${Math.ceil(h)} / ${Math.ceil(max[i])}`;$('#hp-bar-'+i).setAttribute('aria-valuemax',Math.ceil(max[i]));$('#hp-bar-'+i).setAttribute('aria-valuenow',Math.ceil(h));});}
function setLocked(on){$$('[data-edit],.preset-select,[data-tactic],[data-preview]').forEach(b=>b.disabled=on);$('#fight-btn').disabled=on;$('#replay-btn').disabled=on;$('#opponent-tactic').disabled=on;$('#reset-btn').disabled=on;const sb=$('#skip-btn');if(sb)sb.disabled=!on;}
function clearMatch(){if(playing)return;cancelAnimationFrame(frameId);actionClock=null;pendingEvent=null;clearActionMotion();current=null;step=0;$('#result-banner').hidden=true;$('#export-btn').disabled=true;$('#round').textContent='—';$('#feed-count').textContent='0 AKCJI';$('#status').textContent='Gotowi do sparingu';(document.getElementById('fight-message')||{}).textContent=enemyMode==='random'?'Przeciwnik ujawni taktykę po starcie.':`Tryb testowy: rywal wybierze ${tacticLabel(enemyMode).toLowerCase()}.`;$('#report-note').textContent='Każda akcja ma znaczenie. Tutaj zobaczysz jej wynik.';$('#feed').innerHTML=`<div class="feed-empty">${icon('activity')}<strong>Arena czeka na pierwszy ruch.</strong><p>Rozpocznij pojedynek, aby zobaczyć trafienia, uniki i przebieg każdej rundy.</p></div>`;[0,1].forEach(i=>$('#fighter-'+i).classList.remove('winner','loser','attack','hit'));const hp=stats.map(s=>CityCombat.profile(s).hp);hpUpdate(hp,hp);$('#fight-btn').innerHTML=icon('arena')+'<span>Rozpocznij pojedynek</span>';$('#lab-result').hidden=true;}
function invalidate(){clearMatch();renderConfig();save();}
function eventHTML(e){let text;if(!e.landed)text=`<b>${names[e.defender]}</b> zbija rękawicę i unika ciosu. <span class="miss">Bez utraty kondycji.</span>`;else text=`<b>${names[e.attacker]}</b> ${e.critical?'trafia krytycznie':'trafia'} · <strong>−${Math.round(e.damage)} HP</strong>`;return `<div class="feed-item ${e.attacker===1?'enemy-event':''}"><span class="feed-round">R${String(e.round).padStart(2,'0')}</span><span>${text}</span></div>`;}
function resetAnimationClass(el,cls){el.classList.remove(cls);void el.offsetWidth;el.classList.add(cls);}
function clearActionMotion(){
 CombatFX.clear();
 document.querySelectorAll('.move-chip').forEach(el=>el.remove());
 [0,1].forEach(i=>$('#fighter-'+i).classList.remove('attack','hit','dodge','heavy-strike'));
 document.querySelectorAll('.av-fighter,.portrait .art,.portrait').forEach(el=>el.classList.remove('av-hit-a','av-hit-b','av-hit-c','av-hit-crit','av-dodge-lean','av-dodge-duck','av-dodge-side','av-dodge-weave'));
}
function beginAttack(e){
 clearActionMotion();
 $('.fighters').style.setProperty('--action-time',((e.critical?790:1050)/speed)+'ms');
 $('.fighters').style.setProperty('--reaction-time',(600/speed)+'ms');
 $('.fighters').style.setProperty('--number-time',(740/speed)+'ms');
 const attacker=$('#fighter-'+e.attacker);
 if(e.critical)attacker.classList.add('heavy-strike');
 resetAnimationClass(attacker,'attack');
 const port=attacker.querySelector('.portrait');if(port)port.insertAdjacentHTML('beforeend',moveChip(e.attacker,e.round));
 $('#round').textContent=String(e.round).padStart(2,'0');
 return CombatFX.launch(e,moveFor(e.attacker,e.round));
}
function showEvent(e,animate=true){
 $('#round').textContent=String(e.round).padStart(2,'0');
 hpUpdate(e.hp,current.profiles.map(p=>p.hp));
 $('#feed').insertAdjacentHTML('beforeend',eventHTML(e));
 $('#feed-count').textContent=step+' AKCJI';
 $('#feed').scrollTop=$('#feed').scrollHeight;
 if(animate){
  resetAnimationClass($('#fighter-'+e.defender),e.landed?'hit':'dodge');
  const dEl=$('#fighter-'+e.defender);
  const stage=dEl&&(dEl.querySelector('.av-fighter')||dEl.querySelector('.portrait .art')||dEl.querySelector('.portrait'));
  if(stage){const pose=e.landed?(e.critical?'av-hit-crit':['av-hit-a','av-hit-b','av-hit-c'][(e.round||0)%3]):['av-dodge-lean','av-dodge-duck','av-dodge-side','av-dodge-weave'][(e.round||0)%4];resetAnimationClass(stage,pose);}
  const impact=$('#impact-'+e.defender);
  impact.innerHTML=e.landed?`−${Math.round(e.damage)}${e.critical?'<small>Trafienie krytyczne</small>':''}`:'<small>Parada · unik</small>';
  impact.classList.toggle('critical',e.critical);
  resetAnimationClass(impact,'show');
 }
}
function finish(){cancelAnimationFrame(frameId);actionClock=null;pendingEvent=null;clearActionMotion();document.body.classList.remove('is-fighting','is-paused');clearTimeout(timer);playing=false;paused=false;setLocked(false);$('#status').textContent='Pojedynek zakończony';$('#round').textContent=String(current.rounds).padStart(2,'0');$('#fight-btn').innerHTML=icon('arena')+'<span>Nowy pojedynek</span>';$('#export-btn').disabled=false;const w=current.winner;const title=current.demo?'Podgląd: '+current.demo:w===null?'Remis po 100 rundach':w===0?'Zwycięstwo należy do Ciebie.':'Tym razem wygrywa '+names[1]+'.';$('#result-title').textContent=title;$('#result-text').textContent=current.ranked?`${current.rounds} rund · Wynik zapisany na serwerze · Zmiana Elo: ${current.ratingChanges[0]>=0?'+':''}${current.ratingChanges[0].toFixed(1)}`:current.demo?'Przykład pojedynczej akcji. To nie wynik pełnego pojedynku.':`${current.rounds} rund · ${current.events.length} akcji · Sparing bez nagród i zmiany rankingu.`;$('#result-banner').hidden=false;[0,1].forEach(i=>{const el=$('#fighter-'+i);el.classList.remove('attack','hit');el.classList.toggle('winner',w===i);el.classList.toggle('loser',w!==null&&w!==i);});$('#feed').insertAdjacentHTML('beforeend',`<div class="feed-item result-event">${icon('trophy')}<span>${current.demo?'Koniec podglądu efektu':w===null?'Remis':names[w]+' zwycięża'}. Raport został zapisany w tej sesji.</span></div>`);$('#feed .result-event svg').style.cssText='width:16px;flex-shrink:0';$('#feed').scrollTop=$('#feed').scrollHeight;$('#announcement').textContent=title+' '+current.rounds+' rund.';}
function animationFrame(now){
 if(!playing||!actionClock)return;
 const action=actionClock;
 const delta=Math.min(Math.max(now-action.last,0),64);
 action.last=now;
 if(!paused&&!document.hidden){
  action.elapsed+=delta*speed;
  CombatFX.render(action.elapsed);
  if(pendingEvent&&action.elapsed>=action.contact){
   const event=pendingEvent;pendingEvent=null;showEvent(event);
  }
  if(action.elapsed>=action.duration){actionClock=null;next();return;}
 }
 frameId=requestAnimationFrame(animationFrame);
}
function next(){
 if(!playing||paused)return;
 if(actionClock){
  cancelAnimationFrame(frameId);actionClock.last=performance.now();
  frameId=requestAnimationFrame(animationFrame);return;
 }
 if(step>=current.events.length){finish();return;}
 pendingEvent=current.events[step++];
 const timing=beginAttack(pendingEvent);
 actionClock={...timing,elapsed:0,last:performance.now(),speedAtStart:speed};
 frameId=requestAnimationFrame(animationFrame);
}
function syncCombatControls(){const slow=$('#combat-slow-btn');if(slow)slow.hidden=motionEnabled()&&speed===1;}
function playback(){$('#arena').scrollIntoView({behavior:document.body.classList.contains('motion-off')?'instant':'smooth',block:'start'});cancelAnimationFrame(frameId);actionClock=null;pendingEvent=null;clearActionMotion();document.body.classList.add('is-fighting');document.body.classList.remove('is-paused');clearTimeout(timer);playing=true;paused=false;step=0;setLocked(true);$('#result-banner').hidden=true;$('#export-btn').disabled=true;$('#feed').classList.remove('instant-feed');$('#feed').innerHTML='';$('#feed-count').textContent='0 AKCJI';$('#round').textContent='01';$('#status').textContent=current.demo?'Podgląd animacji':'Pojedynek w toku';$('#fight-btn').innerHTML=icon('activity')+'<span>Pojedynek w toku…</span>';$('#report-note').textContent=(current.authoritative?'RAPORT SERWEROWY · ':current.demo?'PODGLĄD EFEKTU · ':'')+`${names[0]}: ${tacticLabel(current.tactics[0])} · ${names[1]}: ${tacticLabel(current.tactics[1])} · Ziarno ${current.seed}`;const [ta,tb]=current.tactics;const adv=CityCombat.BEATS[ta]===tb?names[0]:CityCombat.BEATS[tb]===ta?names[1]:null;(document.getElementById('fight-message')||{}).textContent=adv?`${adv}: przewaga taktyczna +8% obrażeń.`:'Takie same taktyki. Bez premii.';[0,1].forEach(i=>$('#fighter-'+i).classList.remove('winner','loser','attack','hit'));const max=current.profiles.map(p=>p.hp);hpUpdate(max,max);window.updateArenaAvatars&&window.updateArenaAvatars();$('#announcement').textContent='Pojedynek rozpoczęty. Taktyka rywala: '+tacticLabel(tb);timer=setTimeout(next,500/speed);}
function start(){if(playing)return;if(typeof Network!=='undefined'&&GameApp.arenaMode==='character')return;const seed=newSeed();const enemy=enemyMode==='random'?['presja','kontrola','kontra'][Math.floor(CityCombat.rng(seed^0xABC123)()*3)]:enemyMode;current=CityCombat.simulate(stats[0],stats[1],tactic,enemy,seed);playback();}
$('#fight-btn').addEventListener('click',start);$('#replay-btn').addEventListener('click',()=>{if(current&&!playing)playback();});$('#skip-btn').addEventListener('click',()=>{if(!playing)return;clearTimeout(timer);$('#feed').classList.add('instant-feed');if(pendingEvent){showEvent(pendingEvent,false);pendingEvent=null;}while(step<current.events.length){const e=current.events[step++];showEvent(e,false);}finish();});
$$('[data-speed]').forEach(b=>b.addEventListener('click',()=>{speed=+b.dataset.speed;if(actionClock){$$('.fighter .art').forEach(el=>el.getAnimations({subtree:true}).filter(a=>a.animationName?.startsWith('sport-')).forEach(a=>a.playbackRate=speed/actionClock.speedAtStart));}renderConfig();save();}));$$('[data-tactic]').forEach(b=>b.addEventListener('click',()=>{if(playing)return;tactic=b.dataset.tactic;invalidate();}));[0,1].forEach(i=>$('#preset-'+i).addEventListener('change',e=>{if(playing||!presets[e.target.value])return;selections[i]=e.target.value;stats[i]=presets[e.target.value].stats.slice();invalidate();}));
function openDialog(id){$('#'+id).showModal();}$$('[data-close]').forEach(b=>b.addEventListener('click',()=>$('#'+b.dataset.close).close()));$$('dialog').forEach(d=>d.addEventListener('click',e=>{if(e.target===d){const r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}}));$('#rules-btn').onclick=()=>openDialog('rules-dialog');$('#nav-rules').onclick=()=>openDialog('rules-dialog');$('#nav-lab').onclick=()=>openDialog('lab-dialog');{const na=$('#nav-arena');if(na)na.onclick=()=>$('#arena').scrollIntoView({behavior:'smooth',block:'start'});}$('#nav-report').onclick=()=>{$('#report-panel').scrollIntoView({behavior:'smooth',block:'center'});$('#feed').focus({preventScroll:true});};
function total(){const values=$$('#stat-fields input[type=number]').map(e=>Number(e.value));$('#edit-total').textContent=values.reduce((a,b)=>a+b,0).toLocaleString('pl-PL')+' pkt';}
$$('[data-edit]').forEach(b=>b.onclick=()=>{if(playing)return;editSide=+b.dataset.edit;$('#edit-title').textContent='Przygotuj zawodnika · '+names[editSide];$('#stat-fields').innerHTML=labels.map((l,j)=>`<div class="form-stat"><label for="num-${j}">${l}</label><input aria-label="${l} — suwak" type="range" min="10" max="160" step="1" value="${Math.min(160,stats[editSide][j])}" data-range="${j}"><input aria-label="${l} — wartość" id="num-${j}" type="number" min="10" max="10000" step="1" required value="${stats[editSide][j]}" data-num="${j}"></div>`).join('');$$('[data-range]').forEach(r=>r.oninput=()=>{$('#num-'+r.dataset.range).value=r.value;total();});$$('[data-num]').forEach(n=>n.oninput=()=>{$(`[data-range="${n.dataset.num}"]`).value=n.value;total();});total();openDialog('edit-dialog');});
$('#edit-form').onsubmit=e=>{e.preventDefault();if(playing)return;const values=$$('#stat-fields input[type=number]').map(n=>Number(n.value));try{CityCombat.profile(values);}catch(err){toast(err.message);return;}stats[editSide]=values;selections[editSide]='custom';$('#edit-dialog').close();invalidate();toast('Zestaw zawodnika został zapisany.');};
$('#opponent-tactic').onchange=e=>{if(playing)return;enemyMode=e.target.value;invalidate();};$('#lab-tactic').onchange=()=>$('#lab-result').hidden=true;
$('#reset-btn').onclick=()=>{if(playing)return;selections=['free','vip'];stats=[presets.free.stats.slice(),presets.vip.stats.slice()];tactic='kontrola';enemyMode='random';speed=1;invalidate();toast('Przywrócono zestawy startowe.');};
$('#batch-btn').onclick=async()=>{const btn=$('#batch-btn'),a=stats[0].slice(),b=stats[1].slice(),ta=tactic,tb=$('#lab-tactic').value;btn.disabled=true;btn.textContent='Symuluję…';let wins=0,draws=0,rounds=0;for(let k=0;k<10;k++){for(let j=0;j<100;j++){const r=CityCombat.simulate(a,b,ta,tb,20260927+k*100+j);wins+=r.winner===0;draws+=r.winner===null;rounds+=r.rounds;}await new Promise(r=>setTimeout(r,0));}const p=wins/10,q=(1000-wins-draws)/10;$('#lab-result').innerHTML=`<div class="lab-labels"><b>Aleks · ${p.toFixed(1)}%</b><b>Maks · ${q.toFixed(1)}%</b></div><div class="lab-bar"><span style="width:${p}%"></span></div><p>${wins} zwycięstw Aleksa, ${1000-wins-draws} zwycięstw Maksa, ${draws} remisów.<br>Średnio ${(rounds/1000).toFixed(1)} rund. Taktyki: ${tacticLabel(ta)} / ${tacticLabel(tb)}.<br>Losowy błąd próby przy 1 000 walk może wynosić do około ±3,1 p.p. (95%). To nie ocena pełnego balansu gry.</p>`;$('#lab-result').hidden=false;btn.disabled=false;btn.innerHTML=icon('activity')+'Symuluj 1 000 walk';};
$('#export-btn').onclick=()=>{if(!current||playing)return;const payload={game:'CITY EMPIRE',type:'local-demo',createdAt:new Date().toISOString(),fighters:names,result:current};const blob=new Blob([JSON.stringify(payload,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='city-empire-pojedynek-'+current.seed+'.json';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);toast('Raport JSON został przygotowany do pobrania.');};
const motionMedia=matchMedia('(prefers-reduced-motion: reduce)');
let motionChoice='system';
try{const stored=localStorage.getItem('cityEmpireSubtleMotion');if(['on','off'].includes(stored))motionChoice=stored;}catch{}
load();renderConfig();clearMatch();

// System setting is the default, not a permanently disabled control.
// An explicit player opt-in may override reduced motion; no combat result changes.
function motionEnabled(){return motionChoice==='on'||(motionChoice==='system'&&!motionMedia.matches);}
function applyMotion(){
 const enabled=motionEnabled();
 document.body.classList.toggle('motion-off',!enabled);
 document.body.classList.toggle('motion-forced',enabled&&motionChoice==='on');
 const button=$('#motion-btn');
 button.setAttribute('aria-pressed',String(enabled));
 button.setAttribute('aria-label',enabled?'Wyłącz animacje walki i tła':'Włącz animacje walki i tła');
 button.title=enabled?'Wyłącz animacje walki i tła':'Włącz animacje walki i tła, także przy systemowym ograniczeniu ruchu';
 button.disabled=false;
 const local=$('#combat-motion-btn');
 syncCombatControls();
 if(local){
  local.setAttribute('aria-pressed',String(enabled));
  local.textContent=enabled?'Wyłącz animacje':'Włącz animacje · 1×';
  $('#combat-motion-status').textContent='Animacje zawsze włączone — tempo 1×/2×/4× albo „Pomiń”.';
  $('#combat-motion-help').textContent=enabled?'Rozpocznij pojedynek lub zapisz się na ring. Rękawica przemieszcza się między zawodnikami.':'Wynik i punkty HP nadal się zmieniają, ale ruch rękawic jest ukryty. Możesz świadomie włączyć efekty przyciskiem obok.';
  $('#combat-motion-controls').classList.toggle('effects-disabled',!enabled);
  $('#combat-slow-btn').textContent=speed===1?'Zwolnij do 1×':'Przełącz na 1× (teraz '+speed+'×)';
 }
}
function toggleMotion(){
 const enabled=!motionEnabled();motionChoice=enabled?'on':'off';
 try{localStorage.setItem('cityEmpireSubtleMotion',motionChoice);}catch{}
 applyMotion();
 if(enabled)document.querySelector('[data-speed="1"]').click();
 toast(enabled?'Animacje włączone · tempo 1×.':'Animacje wyłączone. Wynik walki pozostaje bez zmian.');
}
$('#motion-btn').addEventListener('click',toggleMotion);
$('#combat-motion-btn')?.addEventListener('click',toggleMotion);
$('#combat-slow-btn')?.addEventListener('click',()=>document.querySelector('[data-speed="1"]').click());
motionMedia.addEventListener('change',applyMotion);
document.addEventListener('visibilitychange',()=>document.body.classList.toggle('tab-hidden',document.hidden));
applyMotion();

// Isolated visual previews use the first real event from a deterministic simulated report.
function previewMotion(kind){
 if(playing)return;
 for(let seed=1;seed<10000;seed++){
  const report=CityCombat.simulate(stats[0],stats[1],tactic,'kontrola',seed);
  const event=report.events[0];
  if(event.attacker!==0)continue;
  if(kind==='hit'&&(!event.landed||event.critical))continue;
  if(kind==='dodge'&&event.landed)continue;
  if(kind==='crit'&&(!event.landed||!event.critical))continue;
  current={...report,events:[event],rounds:1,winner:null,finalHp:event.hp.slice(),demo:{hit:'cios prosty',dodge:'parada / unik',crit:'krytyczne uderzenie'}[kind]};
  speed=1;renderConfig();save();playback();
  break;
 }
}
window.previewMotion=previewMotion;
$$('[data-preview]').forEach(button=>button.addEventListener('click',()=>previewMotion(button.dataset.preview)));
