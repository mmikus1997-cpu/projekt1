/* CITY EMPIRE PvP v0.2 — local design demonstrator, not a production backend. */
(function(root){
 'use strict';
 const KEYS=['strength','intelligence','reflex','charisma','cunning'];
 const BEATS={presja:'kontrola',kontrola:'kontra',kontra:'presja'};
 const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
 function rng(seed){ let a=seed>>>0;return function(){a+=0x6D2B79F5;let t=a;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return((t^(t>>>14))>>>0)/4294967296;}; }
 function validate(stats){if(!Array.isArray(stats)||stats.length!==5||stats.some(x=>!Number.isFinite(x)||x<5||x>10000))throw Error('Każda statystyka musi wynosić od 5 do 10 000 (klasy startują od 8).');}
 function profile(stats){validate(stats);const [s,i,r,c,t]=stats.map(x=>10+10*Math.log(x/10));return {hp:500+10*c,damage:50+s+.2*t,received:60/(60+i),crit:.05+.6*t/(t+40),reflex:r,effective:[s,i,r,c,t]};}
 function simulate(a,b,ta,tb,seed){
  if(!(ta in BEATS)||!(tb in BEATS))throw Error('Nieprawidłowa taktyka');
  const random=rng(seed),p=[profile(a),profile(b)],tactics=[ta,tb],hp=p.map(x=>x.hp),events=[];
  const hit=[0,1].map(i=>clamp(.8+.4*(p[i].reflex-p[1-i].reflex)/(p[i].reflex+p[1-i].reflex+40),.65,.95));
  const first=clamp(.5+.2*(p[0].reflex-p[1].reflex)/(p[0].reflex+p[1].reflex+40),.35,.65);
  let winner=null,round=0;
  outer:for(round=1;round<=100;round++){
   const order=random()<first?[0,1]:[1,0];
   for(const attacker of order){
    const defender=1-attacker;let damage=0,critical=false,landed=random()<hit[attacker];
    if(landed){critical=random()<p[attacker].crit;const variation=.85+.3*random();const buff=BEATS[tactics[attacker]]===tactics[defender]?1.08:1;damage=Math.max(1,p[attacker].damage*p[defender].received*variation*(critical?2:1)*buff);hp[defender]=Math.max(0,hp[defender]-damage);}
    events.push({round,attacker,defender,landed,critical,damage,hp:[...hp]});
    if(hp[defender]<=0){winner=attacker;break outer;}
   }
  }
  return {version:'0.2',seed:seed>>>0,stats:[a.slice(),b.slice()],tactics,profiles:p,events,winner,rounds:Math.min(round,100),finalHp:hp};
 }
 const api={KEYS,BEATS,profile,simulate,rng};root.CityCombat=api;if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
