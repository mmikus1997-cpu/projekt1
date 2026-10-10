/* Prezentacja walki — bez losowości, nagród i liczenia wyniku.
   0.48: animacje wg założonych rzeczy — pięść/but/hełm atakującego leci do celu
   (5 wariantów lotu: prosty, górniak, obrót, zwód, seria), obrońca zasłania się
   tarczą (4 warianty:podniesienie, ukos, wybijenie, absorpcja), a uniki to pozy
   awatara sterowane z app.js. Warianty wybierane deterministycznie z numeru rundy,
   więc powtórka raportu odtwarza te same animacje.
   Animacje są ZAWSZE włączone — tempo (1×/2×/4×) i „Pomiń” sterują tylko odtwarzaniem. */
const CombatFX=(()=>{
 let svg=null,fx=null;
 const NS='http://www.w3.org/2000/svg';
 const clamp=(v,a=0,b=1)=>Math.max(a,Math.min(b,v));
 const mix=(a,b,t)=>a+(b-a)*t;
 const smooth=t=>t*t*(3-2*t);
 const pick=(seed,n)=>{let h=(seed|0)%n;return h<0?h+n:h;};
 const SPRITES={
  fist:'<g id="fx-it-fist"><path d="M-43-19h25v43h-25z" fill="var(--cuff)" stroke="#17202a" stroke-width="2.5"/><path d="M-39-12h17m-17 7h17m-17 7h17m-17 7h17" stroke="#c8c9bd" stroke-opacity=".5" stroke-width="1.5"/><path d="M-24-18q2-16 16-19l24 1q20 1 26 15l5 11q3 11-7 18l-9 6q-3 15-21 16l-23-3q-12-2-15-14z" fill="var(--glove)" stroke="#17202a" stroke-width="3"/><path d="M-24-18q2-16 16-19l24 1q20 1 26 15l5 11q3 11-7 18l-9 6q-3 15-21 16l-23-3q-12-2-15-14z" fill="url(#fx-glove-light)"/><path d="M-15-24q18-9 34-2m-27-7 2 10m13-10 2 10m12-6 2 9M-20 5q20-9 20 8v9" fill="none" stroke="#fff" stroke-opacity=".38" stroke-width="2.5" stroke-linecap="round"/><path d="M7 19q12 3 23-5" stroke="#17202a" stroke-opacity=".35" stroke-width="2"/></g>',
  boot:'<g id="fx-it-boot"><path d="M-34-26h26l4 22 34 10q6 2 5 12l-1 4H-38V-20z" fill="var(--glove)" stroke="#17202a" stroke-width="2.6"/><path d="M-36 22h72" stroke="var(--cuff)" stroke-width="7" stroke-linecap="round"/><path d="M-30-18h12m-12 9h12m-12 9h12" stroke="var(--cuff)" stroke-opacity=".55" stroke-width="2"/><path d="M0-2 24 6m-28 4 22 8" stroke="#fff" stroke-opacity=".35" stroke-width="2" stroke-linecap="round"/></g>',
  helm:'<g id="fx-it-helm"><path d="M-30 14a30 30 0 0 1 60 0v6H-30z" fill="var(--glove)" stroke="#17202a" stroke-width="2.6"/><path d="M-34 20h68" stroke="var(--cuff)" stroke-width="6" stroke-linecap="round"/><path d="M0-16v22m-14-18 3 16m25-16-3 16" stroke="var(--cuff)" stroke-width="2.4"/><path d="M-22 20q22 12 44 0" fill="none" stroke="var(--cuff)" stroke-width="2.4"/></g>',
  shield:'<g id="fx-it-shield"><path d="M0-34q26 8 30 10v22q0 26-30 36Q-30 24-30-2v-22Q-26-26 0-34z" fill="var(--sg)" stroke="#17202a" stroke-width="3"/><path d="M0-26q20 6 23 8v18q0 20-23 29Q-23 20-23 0v-18q3-2 23-8z" fill="none" stroke="var(--sc)" stroke-width="2.4"/><path d="M0-18v30m-12-12h24" stroke="var(--sc)" stroke-width="3.4" stroke-linecap="round"/></g>'
 };
 const CAPTIONS={fist:'CIOS PROSTY',boot:'KOPNIĘCIE',helm:'UDERZENIE HEŁMEM'};
 function init(){
  if(svg)return;
  svg=document.createElementNS(NS,'svg');svg.classList.add('combat-fx');svg.setAttribute('aria-hidden','true');svg.setAttribute('focusable','false');
  svg.innerHTML=`<defs>
   <linearGradient id="fx-glove-light" x1="0" y1="0" x2=".9" y2="1"><stop stop-color="#fff" stop-opacity=".4"/><stop offset=".65" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".22"/></linearGradient>
   <filter id="fx-blur" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="7"/></filter>
   ${SPRITES.fist}${SPRITES.boot}${SPRITES.helm}${SPRITES.shield}
  </defs>
  <g class="fx-layer" opacity="0">
   <path class="fx-glow-trail" fill="none" stroke-linecap="round" filter="url(#fx-blur)"/>
   <path class="fx-trail" fill="none" stroke-linecap="round"/>
   <g class="fx-speed-lines" fill="none" stroke-linecap="round"/>
   <g class="fx-projectile"><ellipse class="fx-aura" rx="64" ry="46" fill="#ffd68a" opacity="0" filter="url(#fx-blur)"/><use class="fx-it" href="#fx-it-fist"/></g>
   <g class="fx-projectile2" opacity="0"><use class="fx-it" href="#fx-it-fist"/></g>
   <g class="fx-guard"><use href="#fx-it-shield"/></g>
   <g class="fx-contact" fill="none" stroke-linecap="round"><circle class="fx-ring"/><circle class="fx-ring-2"/><g class="fx-sparks"/></g>
   <g class="fx-caption"><rect x="-78" y="-17" width="156" height="32" rx="8"/><text text-anchor="middle" y="4"></text></g>
  </g>`;
  document.querySelector('.fighters').appendChild(svg);
 }
 function node(c){return svg.querySelector('.'+c);}
 function attr(el,attrs){for(const [k,v] of Object.entries(attrs))el.setAttribute(k,v);}
 function point(side,x,y,selector='.art'){
  const r=document.querySelector('.fighters').getBoundingClientRect();
  const el=document.querySelector(`#fighter-${side} ${selector}`);
  if(el&&el.getScreenCTM){const matrix=el.getScreenCTM();if(matrix){const p=new DOMPoint(x,y).matrixTransform(matrix);return {x:p.x-r.left,y:p.y-r.top};}}
  // Awatary nie mają .art/.forearm — celuj w ramkę portretu (procent szerokości/wysokości).
  const box=document.querySelector(`#fighter-${side} .portrait`);
  if(box){const b=box.getBoundingClientRect();return {x:b.left-r.left+b.width*(x/380),y:b.top-r.top+b.height*(y/260)};}
  return {x:r.width*(side===0?.35:.65),y:r.height*.4};
 }
 function geometry(){
  const r=document.querySelector('.fighters').getBoundingClientRect();fx.width=r.width;fx.height=r.height;svg.setAttribute('viewBox',`0 0 ${r.width} ${r.height}`);
  fx.source=point(fx.e.attacker,220,162,'.forearm');fx.guardSource=point(fx.e.defender,220,162,'.forearm');
  fx.target=point(fx.e.defender,190,106);if(!fx.e.landed){fx.target.x-=fx.dir*18;fx.target.y+=9;}
  fx.size=r.width<500?.66:r.width<800?.88:1.02;if(fx.e.critical)fx.size*=1.2;
  if(fx.type==='boot')fx.size*=1.12;if(fx.type==='helm')fx.size*=.98;
 }
 // Animacje zawsze włączone (0.48) — brak wyłącznika; tempo i pominięcie należą do odtwarzacza.
 function enabled(){return true;}
 function launch(e,move){
  init();clear();
  move=move||{};
  const type=SPRITES['fx-it-'+move.type]?move.type:'fist';
  const seed=(e.round||1)*7+(e.attacker||0)*3+(e.critical?11:0);
  fx={e,dir:e.attacker===0?1:-1,av:pick(seed,5),sv:pick(seed*3+5,4),type,
      windup:e.critical?130:180,contact:e.critical?680:680,duration:e.critical?1120:1360,released:false};
  fx.contact=e.critical?460:680;
  if(fx.av===3){fx.windup=Math.max(120,fx.windup-30);fx.contact+=170;fx.duration+=260;}  // zwód: dłuższa akcja
  geometry();
  const colors=(move.colors&&move.colors.length===2)?move.colors:(e.attacker===0?['#ecc071','#766244']:['#92bade','#4c6984']);
  const dcolors=e.defender===0?['#ecc071','#766244']:['#92bade','#4c6984'];
  node('fx-projectile').style.cssText=`--glove:${colors[0]};--cuff:${colors[1]}`;
  node('fx-projectile2').style.cssText=`--glove:${colors[0]};--cuff:${colors[1]}`;
  node('fx-guard').style.cssText=`--sg:${dcolors[0]};--sc:${dcolors[1]}`;
  node('fx-contact').setAttribute('stroke',e.landed?colors[0]:dcolors[0]);
  node('fx-glow-trail').setAttribute('stroke',e.critical?'#ffc553':colors[0]);node('fx-trail').setAttribute('stroke',e.critical?'#fff1c2':colors[0]);
  node('fx-speed-lines').setAttribute('stroke',colors[0]);
  const rays=Array.from({length:e.critical?10:6},(_,i)=>{const angle=i*2*Math.PI/(e.critical?10:6);return `<path d="M${Math.cos(angle)*24} ${Math.sin(angle)*24}l${Math.cos(angle)*19} ${Math.sin(angle)*19}"/>`;}).join('');node('fx-sparks').innerHTML=rays;
  node('fx-projectile').querySelector('.fx-it').setAttribute('href','#fx-it-'+type);
  node('fx-projectile2').querySelector('.fx-it').setAttribute('href','#fx-it-'+type);
  render(0);return {contact:fx.contact,duration:fx.duration};
 }
 function flightT(raw){
  // warianty lotu: 0 prosty · 1 górniak · 2 obrót · 3 zwód · 4 seria
  if(fx.av===3){const r=raw;return r<0.5?r*1.1:r<0.72?0.55-(r-0.5)*0.85:0.375+(r-0.72)/0.28*0.625;}
  return raw;
 }
 function render(ms){
  if(!fx)return;
  if(!enabled()){node('fx-layer').setAttribute('opacity',0);return;}
  const {e,dir,windup,contact,duration}=fx;
  if(Math.abs(document.querySelector('.fighters').getBoundingClientRect().width-fx.width)>1)geometry();
  node('fx-layer').setAttribute('opacity',1);
  if(ms>=windup&&!fx.released){fx.source=point(e.attacker,220,162,'.forearm');fx.released=true;}
  const before=ms<contact,raw=clamp((ms-windup)/(contact-windup)),t0=e.critical?raw*raw:raw*raw*(3-2*raw);
  const t=fx.av===3?flightT(raw):t0;
  const recovery=clamp((ms-contact)/(duration-contact));
  const from=fx.source,to=fx.target;
  let lift=e.critical?10:24;
  if(fx.av===1)lift=64;                                      // górniak — wysoki łuk
  if(fx.av===4)lift=e.critical?16:30;                        // seria — dwie pięści
  let spin=0;
  if(fx.av===2)spin=360*t*dir;                               // obrót w locie
  if(fx.type==='helm')spin+=520*t*dir;                       // hełm zawsze koziołkuje
  let x=mix(from.x,to.x,t),y=mix(from.y,to.y,t)-Math.sin(Math.PI*t)*lift;
  let rotation=(dir===1?0:180)+(fx.type==='boot'?-24*dir:0)+spin;
  if(fx.type==='boot')rotation+=Math.sin(t*Math.PI)*16*dir;
  let opacity=ms<windup?clamp(ms/windup)*.65:1;
  if(!before){
   if(e.landed){x=to.x-dir*22*smooth(recovery);y=to.y+14*recovery;rotation+=dir*15*recovery;opacity=1-clamp(recovery*2.6);}
   else{x=to.x+dir*78*Math.sin(recovery*Math.PI/2);y=to.y-108*smooth(recovery);rotation+=dir*95*recovery;opacity=1-clamp((recovery-.28)/.65);}
  }
  node('fx-projectile').setAttribute('transform',`translate(${x} ${y}) rotate(${rotation}) scale(${fx.size})`);node('fx-projectile').setAttribute('opacity',opacity);
  // seria (wariant 4): drugi, duchowy pocisk chwilę za pierwszym
  const g2=clamp(raw-0.22),t2=g2*g2;
  const g2x=mix(from.x,to.x,t2),g2y=mix(from.y,to.y,t2)-Math.sin(Math.PI*t2)*lift;
  node('fx-projectile2').setAttribute('transform',`translate(${g2x} ${g2y}) rotate(${rotation*0.9}) scale(${fx.size*.82})`);
  node('fx-projectile2').setAttribute('opacity',fx.av===4&&raw>0.22&&before?0.75:0);
  node('fx-aura').setAttribute('opacity',e.critical?.52:0);
  const distance=Math.abs(to.x-from.x),length=Math.min(distance*.65,e.critical?230:110)*clamp(raw*3);
  const trailOpacity=ms<windup?0:before?(e.critical?.9:.5):e.landed?0:.35*(1-recovery);
  let tx=x-dir*length,ty=y+(e.critical?3:9);
  if(!before&&!e.landed){tx=to.x;ty=to.y;}
  const trail=`M${tx} ${ty}Q${(tx+x)/2} ${ty-15} ${x-dir*22} ${y}`;
  attr(node('fx-trail'),{d:trail,'stroke-width':e.critical?10:5,opacity:trailOpacity});
  attr(node('fx-glow-trail'),{d:trail,'stroke-width':e.critical?32:14,opacity:e.critical?trailOpacity*.8:trailOpacity*.2});
  node('fx-speed-lines').innerHTML=before&&ms>=windup?[-1,1].map((sign,i)=>`<path d="M${x-dir*(length+15)} ${y+sign*26}l${dir*length*.65} ${-sign*4}" stroke-width="${e.critical?3:1.6}" opacity="${trailOpacity}"/>`).join(''):'';
  // tarcza obrońcy: 0 podniesienie · 1 ukos · 2 wybijenie · 3 absorpcja
  const guard=clamp((raw-.4)/.6),guardEase=smooth(guard);
  let gx=mix(fx.guardSource.x,to.x+dir*16,guardEase),gy=mix(fx.guardSource.y,to.y+18,guardEase);
  if(fx.sv===0)gy+=(1-guardEase)*70;
  let gr=(dir===1?-12:12)+(fx.sv===1?-24*dir:0),gs=fx.size*1.05;
  if(!before&&e.landed){
   if(fx.sv===2)gx-=dir*24*smooth(recovery);
   if(fx.sv===3)gs*=1+0.18*Math.sin(recovery*Math.PI);
   gr+=dir*26*recovery;gy+=16*recovery;
  }
  if(!before&&!e.landed)gy+=54*smooth(recovery);
  const gOpacity=e.landed?(before?guard:1-clamp(recovery*1.6)):(before?guard:1-clamp((recovery-.4)*2));
  attr(node('fx-guard'),{transform:`translate(${gx} ${gy}) rotate(${gr}) scale(${gs})`,opacity:gOpacity});
  const impactProgress=clamp((ms-contact)/420),impactOpacity=before?0:Math.pow(1-impactProgress,1.3);
  attr(node('fx-contact'),{transform:`translate(${to.x} ${to.y})`,opacity:impactOpacity});
  const radius=mix(12,e.critical?94:58,impactProgress);
  attr(node('fx-ring'),{r:radius,'stroke-width':e.critical?5:3});
  attr(node('fx-ring-2'),{r:radius*.65,'stroke-width':2,opacity:e.critical?.7:.25});
  attr(node('fx-sparks'),{transform:`scale(${mix(.7,e.critical?2.1:1.4,impactProgress)})`,'stroke-width':e.critical?3:2});
  const label=e.critical?'KRYTYCZNE · '+(CAPTIONS[fx.type]||'CIOS'):!e.landed&&!before?'PARADA · UNIK':(CAPTIONS[fx.type]||'CIOS');
  node('fx-caption').querySelector('text').textContent=label;
  node('fx-caption').classList.toggle('is-critical',e.critical);
  attr(node('fx-caption'),{transform:`translate(${fx.width/2} ${Math.max(50,Math.min(from.y,to.y)-74)})`,opacity:Math.min(clamp(ms/100),1-clamp((recovery-.75)*4))});
 }
 function clear(){if(svg)node('fx-layer').setAttribute('opacity',0);fx=null;}
 return {launch,render,clear,variants:{attack:5,shield:4}};
})();
