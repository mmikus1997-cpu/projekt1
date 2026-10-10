/* 0.47: awatar — SVG z warstwami kosmetycznymi ORAZ przedmiotów gry (rękawice, strój, buty,
   opaska, hełm, plecak, amulet, korona), animacja (oddech, mruganie, kołysanie), random.
   Katalog i reguły pochodzą z serwera (GET /api/avatar/catalog + gameLooks). */
(function(){
'use strict';
let CAT=null;
function init(catalog){CAT=catalog;ensureStyles();}
function cats(){return CAT?CAT.cats:[];}
function catalog(){return CAT;}
function item(id){
 if(!CAT||!id)return null;
 if(id.indexOf('g:')===0){const look=(CAT.gameLooks||{})[id.slice(2)];if(!look)return null;const gi=(CAT.items.__flat||[])[id.slice(2)];return {id:id,k:look.layer,c:look.c,c2:look.c2,n:gi?gi.name:id.slice(2),game:true};}
 for(const k of Object.keys(CAT.items)){if(k==='__flat')continue;const f=CAT.items[k].find(x=>x.id===id);if(f)return f;}
 return null;
}
function esc(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function indexItems(){ // płaska mapa id→item z gry (do nazw)
 if(!CAT||CAT.items.__flat)return;
 const flat={};
 (CAT.gameItems||[]).forEach(i=>flat[i.id]=i);
 CAT.items.__flat=flat;
}
/* cfg: {body:{skin,hair,hairColor}, layers:{warstwa:id}} (nowe) lub legacy {worn:{kat:id}} */
function layersOf(cfg){
 const out={};
 if(!cfg)return out;
 const w=cfg.layers||cfg.worn||{};
 for(const k of Object.keys(w)){const it=item(w[k]);if(it)out[it.k||k]=it;}
 return out;
}
function bodyOf(cfg){
 const b=(cfg&&cfg.body)||{};const C=CAT?CAT.bodies:{skins:['#f6d7b8'],hairs:['Krótkie'],hairColors:['#1b1b1b']};
 const cl=(v,lo,hi)=>{v=parseInt(v,10);if(!Number.isFinite(v))v=lo;return Math.max(lo,Math.min(hi,v));};
 const g=(b.gender==='k'||b.gender==='m')?b.gender:'m';
 return {gender:g,skin:cl(b.skin,0,(C.skins||[]).length-1),hair:cl(b.hair,0,(C.hairs||[]).length-1),hairColor:cl(b.hairColor,0,(C.hairColors||[]).length-1)};
}
/* cfg z pełnego stanu gry (state): kosmetyka + equipped (gra ma priorytet) — dubluje logikę serwera */
function cfgFromState(state){if(!CAT)return null;
 const av=(state&&state.avatar)||{};
 const layers={};
 for(const k of Object.keys(av.worn||{}))layers[k]=av.worn[k];
 const eq=(state&&state.equipped)||{},gl=(CAT&&CAT.gameLooks)||{};
 for(const slot of Object.keys(eq)){
  const look=gl[eq[slot]];
  if(!look)continue;
  layers[look.layer]='g:'+eq[slot];
  if(look.layer==='helmet'){delete layers.cap;delete layers.hat;}
  if(look.layer==='outfit'){delete layers.shirt;delete layers.hoodie;delete layers.jacket;}
  if(look.layer==='amulet')delete layers.necklace;
 }
 return {body:av.body||{},layers};
}
function random(vipActive){
 const C=CAT||{bodies:{skins:['#f6d7b8'],hairs:['Krótkie'],hairColors:['#1b1b1b']},items:{}};
 const ri=n=>Math.floor(Math.random()*n);
 const worn={};
 for(const k of Object.keys(C.items)){if(k==='__flat')continue;
  const pool=C.items[k].filter(i=>vipActive||!i.vip);
  if(pool.length)worn[k]=pool[ri(pool.length)].id;
 }
 return {body:{gender:Math.random()<.5?'k':'m',skin:ri((C.bodies.skins||[]).length||6),hair:ri((C.bodies.hairs||[]).length||6),hairColor:ri((C.bodies.hairColors||[]).length||8)},worn};
}
let stylesDone=false;
function ensureStyles(){
 if(stylesDone||typeof document==='undefined')return;stylesDone=true;
 const st=document.createElement('style');st.id='ce-avatar-styles';
 st.textContent=
  '.ce-av .av-bob{animation:avBob 2.8s ease-in-out infinite}'+
  '.ce-av .av-br{animation:avBreath 2.8s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}'+
  '.ce-av .av-hd{animation:avHead 5.6s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 95%}'+
  '.ce-av .av-eye{animation:avBlink 4.4s infinite;transform-box:fill-box;transform-origin:center}'+
  '@keyframes avBob{0%,100%{transform:translateY(0)}50%{transform:translateY(1.5px)}}'+
  '@keyframes avBreath{0%,100%{transform:scale(1,1)}50%{transform:scale(1.012,0.988)}}'+
  '@keyframes avHead{0%,100%{transform:rotate(0deg)}30%{transform:rotate(1.7deg)}68%{transform:rotate(-1.5deg)}}'+
  '@keyframes avBlink{0%,92%,100%{transform:scaleY(1)}95.5%{transform:scaleY(.12)}}'+
  '@media (prefers-reduced-motion:reduce){.ce-av *{animation:none!important}}';
 document.head.appendChild(st);
}
/* ---- warstwy ---- */
function legs(L,body){
 const skin=CAT.bodies.skins[body.skin];
 const pants=L.pants,shorts=L.shorts,socks=L.socks,shoes=L.shoes;
 let s='';
 s+='<rect x="38.5" y="86" width="10" height="44" rx="3" fill="'+skin+'"/><rect x="51.5" y="86" width="10" height="44" rx="3" fill="'+skin+'"/>';
 if(socks){s+='<rect x="38.5" y="112" width="10" height="14" fill="'+socks.c+'"/><rect x="51.5" y="112" width="10" height="14" fill="'+socks.c+'"/>';}
 if(pants){
  s+='<rect x="37.5" y="85" width="12" height="40" rx="2.5" fill="'+pants.c+'"/><rect x="50.5" y="85" width="12" height="40" rx="2.5" fill="'+pants.c+'"/>';
  s+='<rect x="35.5" y="84.5" width="29" height="5" rx="2.4" fill="'+pants.c2+'"/>';
 }else if(shorts){
  s+='<rect x="37.5" y="85" width="12" height="20" rx="2.5" fill="'+shorts.c+'"/><rect x="50.5" y="85" width="12" height="20" rx="2.5" fill="'+shorts.c+'"/>';
  s+='<rect x="35.5" y="84.5" width="29" height="5" rx="2.4" fill="'+shorts.c2+'"/>';
 }
 if(shoes){
  const sporty=shoes.game;
  s+='<rect x="36" y="125.5" width="14" height="11" rx="4" fill="'+shoes.c+'"/><rect x="50" y="125.5" width="14" height="11" rx="4" fill="'+shoes.c+'"/>';
  s+='<rect x="36" y="133.6" width="14" height="2.9" rx="1.4" fill="'+shoes.c2+'"/><rect x="50" y="133.6" width="14" height="2.9" rx="1.4" fill="'+shoes.c2+'"/>';
  if(sporty)s+='<path d="M38,129.5 h10 M52,129.5 h10" stroke="'+shoes.c2+'" stroke-width="1.1" opacity=".85"/>';
  else s+='<path d="M39,128.5 l4,2.4 M43,128.5 l-4,2.4 M53,128.5 l4,2.4 M57,128.5 l-4,2.4" stroke="#f2f2f0" stroke-width=".9" opacity=".8"/>';
 }
 return s;
}
function torso(L,body){
 const skin=CAT.bodies.skins[body.skin];
 const outfit=L.outfit,shirt=L.shirt,hoodie=L.hoodie,jacket=L.jacket;
 const female=body.gender==='k';
 const fill=(outfit?outfit.c:(hoodie?hoodie.c:(shirt?shirt.c:(jacket?jacket.c:'#cfd6dd'))));
 let s='';
 if(female){ // 0.48: sylwetka kobieca — węższe ramiona i talia (skala), szersze biodra
  s+='<g transform="translate(50 0) scale(0.87 1) translate(-50 0)">';
  s+='<rect x="33.5" y="46" width="33" height="40" rx="8" fill="'+fill+'"/>';
 }else{
  s+='<rect x="33.5" y="46" width="33" height="42" rx="8" fill="'+fill+'"/>';
 }
 if(outfit){ // strój z gry: bezrękawnik z pasem i dekoltem w barwach klubu
  s+='<path d="M44,46 Q50,51.5 56,46" fill="none" stroke="'+outfit.c2+'" stroke-width="1.7"/>';
  s+='<rect x="33.5" y="70" width="33" height="4.2" rx="2" fill="'+outfit.c2+'"/>';
  s+='<rect x="33.5" y="84.4" width="33" height="3.6" rx="1.8" fill="'+outfit.c2+'"/>';
  s+='<path d="M33.5,50 a8,8 0 0 1 5,-4 M66.5,50 a8,8 0 0 0 -5,-4" stroke="'+outfit.c2+'" stroke-width="1.1" fill="none" opacity=".6"/>';
 }else{
  if(shirt){
   const m=shirt.v%3;
   if(m===0)s+='<path d="M44,46 Q50,51.5 56,46" fill="none" stroke="'+shirt.c2+'" stroke-width="1.6"/>';
   else if(m===1)s+='<path d="M45.5,46 L50,52 L54.5,46 Z" fill="'+skin+'"/>';
   else s+='<rect x="52.5" y="53" width="7.5" height="8.5" rx="1.4" fill="'+shirt.c2+'"/>';
   if(shirt.v===4){s+='<rect x="33.5" y="56" width="33" height="2.6" fill="'+shirt.c2+'" opacity=".75"/><rect x="33.5" y="64" width="33" height="2.6" fill="'+shirt.c2+'" opacity=".75"/><rect x="33.5" y="72" width="33" height="2.6" fill="'+shirt.c2+'" opacity=".75"/>';}
   if(shirt.v>=6)s+='<rect x="33.5" y="84.4" width="33" height="3.6" rx="1.8" fill="'+shirt.c2+'"/>';
  }
  if(hoodie){
   s+='<path d="M36.5,46.5 Q50,54 63.5,46.5 L63.5,41.5 Q50,48.5 36.5,41.5 Z" fill="'+hoodie.c2+'"/>';
   s+='<rect x="39" y="70" width="22" height="11" rx="3.4" fill="'+hoodie.c2+'" opacity=".5"/>';
   s+='<path d="M46,50.5 L46,59 M54,50.5 L54,59" stroke="#f4f2ec" stroke-width="1.2" stroke-linecap="round"/>';
  }
  if(jacket){
   s+='<rect x="45.6" y="47" width="8.8" height="39" rx="3" fill="'+(shirt?shirt.c:'#cfd5da')+'"/>';
   s+='<path d="M50,48 L50,86" stroke="'+jacket.c2+'" stroke-width="1.4"/>';
   s+='<path d="M42.5,46 L50,50.5 L41.5,53 Z" fill="'+jacket.c2+'"/><path d="M57.5,46 L50,50.5 L58.5,53 Z" fill="'+jacket.c2+'"/>';
  }
 }
 if(female){
  s+='</g>';
  s+='<path d="M37.6,67.5 Q33.4,75.5 34.2,85 L65.8,85 Q66.6,75.5 62.4,67.5 Z" fill="'+fill+'"/>';
  s+='<path d="M34.6,80.5 L65.4,80.5" stroke="#000" stroke-opacity=".1" stroke-width="1.2"/>';
  s+='<path d="M38.9,69.5 Q38,76 38.9,84 L41,84 Q40,76 40.9,70 Z" fill="#000" opacity=".08"/>';
 }
 return s;
}
function arms(L,body){
 const skin=CAT.bodies.skins[body.skin];
 const outfit=L.outfit,hoodie=L.hoodie,jacket=L.jacket,shirt=L.shirt,gloves=L.gloves;
 const long=outfit||hoodie||jacket,col=long?(outfit||hoodie||jacket).c:(shirt?shirt.c:null);
 const F=body.gender==='k';const x0=F?38.2:35.5,x1=F?61.8:64.5,w=F?5.6:7;
 let s='<path d="M'+x0+',51 L28.5,82" stroke="'+skin+'" stroke-width="'+w+'" stroke-linecap="round"/><path d="M'+x1+',51 L71.5,82" stroke="'+skin+'" stroke-width="'+w+'" stroke-linecap="round"/>';
 if(col){
  if(long)s+='<path d="M'+x0+',51 L28.5,82" stroke="'+col+'" stroke-width="'+(w+.6)+'" stroke-linecap="round"/><path d="M'+x1+',51 L71.5,82" stroke="'+col+'" stroke-width="'+(w+.6)+'" stroke-linecap="round"/>';
  else s+='<circle cx="'+(F?36:34)+'" cy="53.5" r="'+(F?5:5.4)+'" fill="'+col+'"/><circle cx="'+(F?64:66)+'" cy="53.5" r="'+(F?5:5.4)+'" fill="'+col+'"/>';
 }
 if(gloves){ // rękawice z gry — widowiskowe, bokserki
  s+='<circle cx="28.5" cy="86.5" r="5.2" fill="'+gloves.c+'"/><circle cx="71.5" cy="86.5" r="5.2" fill="'+gloves.c+'"/>';
  s+='<rect x="24.6" y="80.6" width="7.8" height="3.4" rx="1.7" fill="'+gloves.c2+'"/><rect x="67.6" y="80.6" width="7.8" height="3.4" rx="1.7" fill="'+gloves.c2+'"/>';
 }else{
  s+='<circle cx="28.5" cy="85" r="3.6" fill="'+skin+'"/><circle cx="71.5" cy="85" r="3.6" fill="'+skin+'"/>';
 }
 if(L.ring&&!gloves)s+='<circle cx="71.5" cy="87" r="2.1" fill="none" stroke="'+L.ring.c+'" stroke-width="1.3"/>';
 return s;
}
function backpack(L){
 const b=L.backpack;if(!b)return'';
 let s='<g>';
 s+='<rect x="21.5" y="56" width="9.5" height="25" rx="4.5" fill="'+b.c+'"/><rect x="69" y="56" width="9.5" height="25" rx="4.5" fill="'+b.c+'"/>';
 s+='<rect x="23.2" y="60" width="6.1" height="7" rx="2.4" fill="'+b.c2+'" opacity=".65"/><rect x="70.7" y="60" width="6.1" height="7" rx="2.4" fill="'+b.c2+'" opacity=".65"/>';
 if(b.game)s+='<rect x="41.4" y="47" width="3.6" height="19" rx="1.8" fill="'+b.c2+'"/><rect x="55" y="47" width="3.6" height="19" rx="1.8" fill="'+b.c2+'"/>';
 else{s+='<rect x="41.4" y="47" width="3.6" height="19" rx="1.8" fill="'+b.c2+'"/><rect x="55" y="47" width="3.6" height="19" rx="1.8" fill="'+b.c2+'"/>';}
 return s+'</g>';
}
function neck(L){
 const amulet=L.amulet,n=L.necklace;
 let s='<path d="M43,48.5 Q50,55.5 57,48.5" fill="none" stroke="'+(amulet?amulet.c:(n?n.c:'#8a6a45'))+'" stroke-width="1.8" stroke-linecap="round"/>';
 if(amulet){s+='<circle cx="50" cy="57" r="3" fill="'+amulet.c+'" stroke="'+amulet.c2+'" stroke-width="1"/><circle cx="50" cy="57" r="1.1" fill="'+amulet.c2+'"/>';}
 else if(n){const m=n.v%3;
  if(m===0)s+='<circle cx="50" cy="56.5" r="2.5" fill="'+n.c2+'"/>';
  else if(m===1)s+='<path d="M50,54.5 L52.6,58.5 L50,62.5 L47.4,58.5 Z" fill="'+n.c2+'"/>';
  else s+='<rect x="47.6" y="54.6" width="4.8" height="4.8" rx="1" fill="'+n.c2+'"/>';
 }
 return s;
}
function hairBack(body){
 const hc=CAT.bodies.hairColors[body.hairColor];
 if(body.hair===4)return '<path d="M35,26 Q35,15.5 50,15.5 Q65,15.5 65,26 L65,48 Q65,53.5 58,52 L58,30 L42,30 L42,52 Q35,53.5 35,48 Z" fill="'+hc+'"/>';
 return '';
}
function head(L,body){
 const skin=CAT.bodies.skins[body.skin];const hc=CAT.bodies.hairColors[body.hairColor];
 let s='';
 s+='<rect x="46.5" y="38.5" width="7" height="8" rx="2.4" fill="'+skin+'"/>';
 s+='<circle cx="36.8" cy="30" r="2.2" fill="'+skin+'"/><circle cx="63.2" cy="30" r="2.2" fill="'+skin+'"/>';
 s+=hairBack(body);
 s+='<circle cx="50" cy="28" r="13.5" fill="'+skin+'"/>';
 const H=body.hair;
 if(H===1)s+='<path d="M37.1,24 A13.5,13.5 0 0 1 62.9,24 L62.9,22.8 Q50,15.8 37.1,22.8 Z" fill="'+hc+'"/>';
 if(H===2){s+='<path d="M37.1,24 A13.5,13.5 0 0 1 62.9,24 L62.9,22.8 Q50,15.8 37.1,22.8 Z" fill="'+hc+'"/><path d="M37.5,22 Q45,23.5 46.5,30.5 L38.5,27.5 Z" fill="'+hc+'"/>';}
 if(H===3){s+='<path d="M37.1,24 A13.5,13.5 0 0 1 62.9,24 L62.9,22.8 Q50,15.8 37.1,22.8 Z" fill="'+hc+'"/><circle cx="40" cy="17.5" r="3" fill="'+hc+'"/><circle cx="46.5" cy="15" r="3.2" fill="'+hc+'"/><circle cx="53.5" cy="15" r="3.2" fill="'+hc+'"/><circle cx="60" cy="17.5" r="3" fill="'+hc+'"/>';}
 if(H===5){s+='<path d="M38.5,19.5 L42.5,11.5 L46.5,18 L50.5,10.5 L54.5,18 L58.5,11.5 L62,19.5 Q50,14 38.5,19.5 Z" fill="'+hc+'"/>';}
 s+='<g class="av-eye"><circle cx="45.5" cy="30" r="1.7" fill="#22201e"/></g><g class="av-eye"><circle cx="54.5" cy="30" r="1.7" fill="#22201e"/></g>';
 s+='<path d="M43.4,26.6 L47.4,26.2 M52.6,26.2 L56.6,26.6" stroke="#3a332d" stroke-width="1.1" stroke-linecap="round"/>';
 s+='<path d="M46.5,35.2 Q50,38.4 53.5,35.2" fill="none" stroke="#7a4a3a" stroke-width="1.3" stroke-linecap="round"/>';
 if(L.earrings){const e=L.earrings,m=e.v%3;
  if(m===0)s+='<circle cx="36.8" cy="33.6" r="1.9" fill="none" stroke="'+e.c+'" stroke-width="1.2"/><circle cx="63.2" cy="33.6" r="1.9" fill="none" stroke="'+e.c+'" stroke-width="1.2"/>';
  else if(m===1)s+='<circle cx="36.8" cy="34" r="1.4" fill="'+e.c+'"/><circle cx="63.2" cy="34" r="1.4" fill="'+e.c+'"/>';
  else s+='<path d="M36.8,32.4 L36.8,36" stroke="'+e.c+'" stroke-width="1"/><circle cx="36.8" cy="37.4" r="1.7" fill="'+e.c2+'"/><path d="M63.2,32.4 L63.2,36" stroke="'+e.c+'" stroke-width="1"/><circle cx="63.2" cy="37.4" r="1.7" fill="'+e.c2+'"/>';
 }
 if(L.glasses){const g=L.glasses,m=g.v%3;
  if(m===0)s+='<circle cx="45.5" cy="30" r="4.6" fill="'+g.c2+'" fill-opacity=".28" stroke="'+g.c+'" stroke-width="1.6"/><circle cx="54.5" cy="30" r="4.6" fill="'+g.c2+'" fill-opacity=".28" stroke="'+g.c+'" stroke-width="1.6"/><path d="M50.1,30 L49.9,30" stroke="'+g.c+'" stroke-width="1.6"/>';
  else if(m===1)s+='<rect x="41.6" y="26.6" width="7.8" height="6.6" rx="1.6" fill="'+g.c2+'" fill-opacity=".28" stroke="'+g.c+'" stroke-width="1.6"/><rect x="50.6" y="26.6" width="7.8" height="6.6" rx="1.6" fill="'+g.c2+'" fill-opacity=".28" stroke="'+g.c+'" stroke-width="1.6"/>';
  else s+='<path d="M41,28.5 Q45.5,25.5 50,28.5 Q54.5,25.5 59,28.5 L58.6,31.5 Q54.5,34.5 50.4,31.8 L49.6,31.8 Q45.5,34.5 41.4,31.5 Z" fill="'+g.c2+'" fill-opacity=".3" stroke="'+g.c+'" stroke-width="1.3"/>';
 }
 if(L.band){const bd=L.band; // opaska z gry: czołowa, z węzłem
  s+='<path d="M37.6,22.6 Q50,18.4 62.4,22.6 L62.4,25.4 Q50,21.2 37.6,25.4 Z" fill="'+bd.c+'"/>';
  s+='<path d="M61,22.2 L64.6,19.4 L64.2,23.8 Z" fill="'+bd.c2+'"/>';
 }
 if(L.cap){const c=L.cap,m=c.v%3;
  if(m===0){s+='<path d="M38,22.5 A12,11.5 0 0 1 62,22.5 L62,24.6 L38,24.6 Z" fill="'+c.c+'"/><rect x="37.2" y="23.6" width="25.6" height="3.2" rx="1.6" fill="'+c.c2+'"/><circle cx="50" cy="15.5" r="3" fill="'+c.c2+'"/>';}
  else if(m===1){s+='<path d="M38,23 A12,11 0 0 1 62,23 L62,24 L38,24 Z" fill="'+c.c+'"/><path d="M37.5,23.4 Q50,28.6 62.5,23.4 L62.5,21.6 Q50,26 37.5,21.6 Z" fill="'+c.c2+'"/>';}
  else{s+='<path d="M40.5,16.5 L59.5,16.5 L62.5,23.5 L37.5,23.5 Z" fill="'+c.c+'"/><ellipse cx="50" cy="24" rx="14.5" ry="2.9" fill="'+c.c2+'"/>';}
 }else if(L.hat){const h=L.hat,m=h.v%3;
  if(m===0){s+='<ellipse cx="50" cy="22.5" rx="16.5" ry="3.9" fill="'+h.c+'"/><rect x="42.5" y="11.5" width="15" height="10.5" rx="3.4" fill="'+h.c2+'"/><rect x="42.5" y="18" width="15" height="3.1" fill="'+h.c+'"/>';}
  else if(m===1){s+='<ellipse cx="50" cy="21.8" rx="15" ry="3.6" fill="'+h.c+'"/><path d="M43.4,21.5 Q43.4,10.5 50,10.5 Q56.6,10.5 56.6,21.5 Z" fill="'+h.c+'"/><rect x="43.4" y="17" width="13.2" height="3" fill="'+h.c2+'"/>';}
  else{s+='<ellipse cx="50" cy="21.5" rx="14" ry="3.3" fill="'+h.c+'"/><rect x="44" y="5.5" width="12" height="15.5" rx="2.4" fill="'+h.c+'"/><rect x="44" y="16.4" width="12" height="3.2" fill="'+h.c2+'"/>';}
 }
 if(L.helmet){const h=L.helmet; // hełm z gry: kopuła + rynienki + pasek pod brodą
  s+='<path d="M36.8,26 A13.4,13.4 0 0 1 63.2,26 L63.2,21.8 A13.4,13.4 0 0 0 36.8,21.8 Z" fill="'+h.c+'"/>';
  s+='<path d="M36.6,25.4 A13.5,13.5 0 0 1 63.4,25.4 L63.4,22.6 A13.5,13.5 0 0 0 36.6,22.6 Z" fill="'+h.c+'"/>';
  s+='<path d="M37,24 A13,13 0 0 1 63,24 L63,20.5 Q50,10.5 37,20.5 Z" fill="'+h.c+'"/>';
  s+='<path d="M50,11.2 L50,19.8 M43.4,13.2 L44.6,21 M56.6,13.2 L55.4,21" stroke="'+h.c2+'" stroke-width="1.3"/>';
  s+='<path d="M37.6,27.6 Q50,33.8 62.4,27.6" fill="none" stroke="'+h.c2+'" stroke-width="1.3"/>';
 }
 if(L.crown){const cr=L.crown; // korona władcy
  s+='<path d="M41,15.5 L43.5,8.5 L46.5,13.5 L50,6.5 L53.5,13.5 L56.5,8.5 L59,15.5 Z" fill="'+cr.c+'"/>';
  s+='<rect x="41" y="15" width="18" height="3.4" rx="1.4" fill="'+cr.c+'"/><circle cx="50" cy="16.7" r="1.3" fill="'+cr.c2+'"/>';
 }
 return s;
}
function svg(cfg,opts){if(!CAT)return '';
 opts=opts||{};indexItems();
 const body=bodyOf(cfg),L=layersOf(cfg);
 const cls='ce-av'+(body.gender==='k'?' av-g-k':'')+(opts.animate===false?' ce-av-static':'');
 return '<svg class="'+cls+'" viewBox="0 0 100 150" role="img" aria-label="Awatar postaci" xmlns="http://www.w3.org/2000/svg">'
  +'<g class="av-bob"><ellipse cx="50" cy="141.5" rx="21" ry="3.6" fill="rgba(0,0,0,.28)"/>'
  +backpack(L)
  +'<g>'+legs(L,body)+'</g>'
  +'<g class="av-br">'+torso(L,body)+arms(L,body)+'</g>'
  +neck(L)
  +'<g class="av-hd">'+head(L,body)+'</g>'
  +'</g></svg>';
}
function mount(el,cfg,opts){if(!CAT){el.innerHTML='';return;}if(!el)return;el.innerHTML=svg(cfg,opts);}
const API={init:init,cats:cats,item:item,svg:svg,mount:mount,cfgFromState:cfgFromState,random:random,get catalog(){return CAT;}};
window.CityAvatar=API;
})();
