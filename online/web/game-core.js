/* CITY EMPIRE local economy. Pure state transitions, not a production backend. */
(function(root){
'use strict';
const HOUR=3600000,MIN=60000,MAX_ENERGY=240;
const RATES=[40,55,75,100,135,175,225],COSTS=[1000,2500,5000,9000,15000,24000];
const CONTRACTS=[
 {id:'delivery',name:'Dostawa na Przedmieścia',district:'Lasy Wschodnie',description:'Dostarcz lokalnym sklepom paczki z centrum logistycznego.',duration:10*MIN,energy:10,cash:100,xp:20,level:1,icon:'truck'},
 {id:'event',name:'Obsługa wydarzenia',district:'Centrum',description:'Przygotuj stanowiska partnerów na miejskim wydarzeniu.',duration:20*MIN,energy:20,cash:200,xp:40,level:2,icon:'briefcase'},
 {id:'logistics',name:'Koordynacja transportu',district:'Portowe',description:'Zaplanuj i dopilnuj transportu dla lokalnych przedsiębiorstw.',duration:40*MIN,energy:40,cash:400,xp:80,level:3,icon:'route'}
];
const ITEMS=[
 {id:'basic-gloves',slot:'gloves',name:'Rękawice treningowe',price:0,bonus:[0,0,0,0,0],tier:'Podstawowe'},
 {id:'basic-shirt',slot:'shirt',name:'Strój klubowy',price:0,bonus:[0,0,0,0,0],tier:'Podstawowe'},
 {id:'basic-shoes',slot:'shoes',name:'Buty sportowe',price:0,bonus:[0,0,0,0,0],tier:'Podstawowe'},
 {id:'basic-accessory',slot:'accessory',name:'Opaska treningowa',price:0,bonus:[0,0,0,0,0],tier:'Podstawowe'},
 {id:'urban-gloves',slot:'gloves',name:'Rękawice Urban',price:250,bonus:[2,0,0,0,0],tier:'Ulepszone'},
 {id:'focus-shirt',slot:'shirt',name:'Strój Focus',price:350,bonus:[0,2,0,1,0],tier:'Ulepszone'},
 {id:'sprint-shoes',slot:'shoes',name:'Buty Sprint',price:300,bonus:[0,0,2,0,0],tier:'Ulepszone'},
 {id:'tactical-band',slot:'accessory',name:'Opaska taktyczna',price:200,bonus:[0,0,0,1,2],tier:'Ulepszone'},
 {id:'counter-gloves',slot:'gloves',name:'Rękawice Counter',price:500,bonus:[2,0,0,0,2],tier:'Specjalistyczne'}
];
function create(now=Date.now()){
 return {version:1,offset:0,lastTick:now,cash:300,xp:0,energy:120,stats:[10,10,10,10,10],business:{level:1,vault:0,upgrade:null},contracts:[],training:[],inventory:ITEMS.filter(x=>!x.price).map(x=>x.id),equipped:{gloves:'basic-gloves',shirt:'basic-shirt',shoes:'basic-shoes',accessory:'basic-accessory'},completed:{contracts:0,training:0},sequence:0,history:[]};
}
function level(xp){return Math.floor((1+Math.sqrt(1+8*xp/100))/2);}
function xpAt(lvl){return 100*(lvl-1)*lvl/2;}
function log(s,text,now){s.history.unshift({text,at:now});s.history=s.history.slice(0,20);}
function income(s,ms){s.business.vault=Math.min(s.business.vault+Math.max(0,ms)/HOUR*RATES[s.business.level-1],24*RATES[s.business.level-1]);}
function sync(s,now){
 now=Math.max(s.lastTick,now);const from=s.lastTick;
 s.energy=Math.min(MAX_ENERGY,s.energy+(now-from)/HOUR*10);
 const u=s.business.upgrade;
 if(u&&u.end<=now){income(s,Math.max(0,u.end-from));s.business.level=u.target;s.business.upgrade=null;income(s,now-Math.max(from,u.end));log(s,'Firma osiągnęła poziom '+s.business.level+'.',u.end);}
 else income(s,now-from);
 s.lastTick=now;return s;
}
function spend(s,cash,energy){if(s.cash<cash)throw Error('Za mało gotówki. Odbierz kontrakt lub dochód firmy.');if(s.energy+1e-8<energy)throw Error('Za mało energii. Poczekaj na regenerację.');s.cash-=cash;s.energy=Math.max(0,s.energy-energy);}
function contract(s,id,now){
 sync(s,now);const c=CONTRACTS.find(x=>x.id===id);if(!c)throw Error('Nieznany kontrakt.');if(level(s.xp)<c.level)throw Error('Ten kontrakt wymaga poziomu '+c.level+'.');if(s.contracts.length>=4)throw Error('Kolejka jest pełna. Odbierz ukończone zlecenia.');
 spend(s,0,c.energy);const start=Math.max(now,...s.contracts.map(x=>x.end));const task={id:++s.sequence,contract:c.id,start,end:start+c.duration};s.contracts.push(task);log(s,'Przyjęto: '+c.name+'.',now);return task;
}
function claimContract(s,id,now){sync(s,now);const i=s.contracts.findIndex(t=>t.id===id);if(i<0)throw Error('Ten kontrakt został już odebrany.');const task=s.contracts[i];if(now<task.end)throw Error('Kontrakt jeszcze trwa.');const c=CONTRACTS.find(x=>x.id===task.contract);s.cash+=c.cash;s.xp+=c.xp;s.contracts.splice(i,1);s.completed.contracts++;log(s,`Kontrakt ukończony: +${c.cash} $ i +${c.xp} XP.`,now);return c;}
function train(s,index,now){sync(s,now);if(!Number.isInteger(index)||index<0||index>4)throw Error('Nieznana statystyka.');if(s.training.length>=4)throw Error('Kolejka treningów jest pełna.');if(s.stats[index]+s.training.filter(t=>t.stat===index).length>=9990)throw Error('Limit statystyki w prototypie.');spend(s,50,5);const start=Math.max(now,...s.training.map(x=>x.end));const task={id:++s.sequence,stat:index,start,end:start+5*MIN};s.training.push(task);return task;}
function claimTraining(s,id,now){sync(s,now);const i=s.training.findIndex(t=>t.id===id);if(i<0)throw Error('Ten trening został już odebrany.');const task=s.training[i];if(now<task.end)throw Error('Trening jeszcze trwa.');s.stats[task.stat]++;s.training.splice(i,1);s.completed.training++;log(s,'Ukończono trening. +1 punkt statystyki.',now);return task.stat;}
function collect(s,now){sync(s,now);const amount=Math.floor(s.business.vault+1e-7);if(amount<1)throw Error('Skarbiec nie zgromadził jeszcze 1 $.');s.business.vault=Math.max(0,s.business.vault-amount);s.cash+=amount;log(s,`Odebrano ${amount} $ z firmy.`,now);return amount;}
function upgrade(s,now){sync(s,now);if(s.business.upgrade)throw Error('Rozbudowa już trwa.');if(s.business.level>=RATES.length)throw Error('Maksymalny poziom w prototypie.');spend(s,COSTS[s.business.level-1],0);s.business.upgrade={target:s.business.level+1,start:now,end:now+10*MIN};log(s,'Rozpoczęto rozbudowę firmy.',now);return s.business.upgrade;}
function buy(s,id,now){sync(s,now);const item=ITEMS.find(x=>x.id===id);if(!item||!item.price)throw Error('Nieznany produkt.');if(s.inventory.includes(id))throw Error('Masz już ten przedmiot.');spend(s,item.price,0);s.inventory.push(id);s.equipped[item.slot]=id;log(s,'Kupiono i założono: '+item.name+'.',now);return item;}
function equip(s,id){const item=ITEMS.find(x=>x.id===id);if(!item||!s.inventory.includes(id))throw Error('Nie posiadasz tego przedmiotu.');s.equipped[item.slot]=id;}
function bonuses(s){return Object.values(s.equipped).reduce((a,id)=>{const item=ITEMS.find(x=>x.id===id);return a.map((v,i)=>v+item.bonus[i]);},[0,0,0,0,0]);}
function effective(s){const add=bonuses(s);return s.stats.map((v,i)=>v+add[i]);}
function validate(s){
 const number=(v,min,max)=>typeof v==='number'&&Number.isFinite(v)&&v>=min&&v<=max;
 if(!s||s.version!==1||!number(s.cash,0,1e12)||!number(s.energy,0,240)||!number(s.xp,0,1e10)||!number(s.offset,0,1e13)||!number(s.lastTick,0,1e14))return false;
 if(!Array.isArray(s.stats)||s.stats.length!==5||s.stats.some(v=>!Number.isInteger(v)||v<10||v>9990))return false;
 const b=s.business;if(!b||!Number.isInteger(b.level)||b.level<1||b.level>7||!number(b.vault,0,24*RATES[b.level-1]+1e-6))return false;
 if(b.upgrade&&(!number(b.upgrade.start,0,1e14)||!number(b.upgrade.end,b.upgrade.start,1e14)||b.upgrade.target!==b.level+1||b.upgrade.target>7))return false;
 if(!Array.isArray(s.inventory)||s.inventory.length>ITEMS.length||new Set(s.inventory).size!==s.inventory.length||s.inventory.some(id=>!ITEMS.some(x=>x.id===id)))return false;
 if(!s.equipped||['gloves','shirt','shoes','accessory'].some(slot=>!s.inventory.includes(s.equipped[slot])||!ITEMS.some(x=>x.id===s.equipped[slot]&&x.slot===slot)))return false;
 if(!s.completed||!number(s.completed.contracts,0,1e10)||!number(s.completed.training,0,1e10)||!Number.isInteger(s.sequence)||s.sequence<0)return false;
 for(const kind of ['contracts','training']){
  if(!Array.isArray(s[kind])||s[kind].length>4)return false;
  if(s[kind].some(t=>!Number.isInteger(t.id)||t.id<1||t.id>s.sequence||!number(t.start,0,1e14)||!number(t.end,t.start,1e14)||(kind==='contracts'?!CONTRACTS.some(c=>c.id===t.contract):!Number.isInteger(t.stat)||t.stat<0||t.stat>4)))return false;
 }
 if(new Set([...s.contracts,...s.training].map(t=>t.id)).size!==s.contracts.length+s.training.length)return false;
 if(!Array.isArray(s.history)||s.history.length>20||s.history.some(x=>typeof x.text!=='string'||x.text.length>200||!number(x.at,0,1e14)))return false;
 return true;
}
const api={HOUR,MIN,MAX_ENERGY,RATES,COSTS,CONTRACTS,ITEMS,create,level,xpAt,sync,contract,claimContract,train,claimTraining,collect,upgrade,buy,equip,bonuses,effective,validate};root.CityGame=api;if(typeof module!=='undefined')module.exports=api;
})(typeof globalThis!=='undefined'?globalThis:this);
