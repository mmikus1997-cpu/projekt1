"""Authoritative economy. Call only within a database write transaction."""
import json
import math
import random
import time

MINUTE=60_000
HOUR=3_600_000
RATES=[40,55,75,100,135,175,225]
COSTS=[1000,2500,5000,9000,15000,24000]
CAFE_RATES=[30,45,65,90]
CAFE_COSTS=[1500,3500,7000]
CONTRACTS=[
 dict(id='delivery',name='Dostawa do Lasów Wschodnich',district='Lasy Wschodnie',d=8,description='Dostarcz lokalnym sklepom paczki z centrum logistycznego.',duration=10*MINUTE,energy=10,cash=100,xp=20,level=1,icon='truck'),
 dict(id='inventory',name='Inwentaryzacja lokalu',district='Centrum',d=3,description='Sprawdź i uporządkuj stany magazynowe lokalnej kawiarni.',duration=5*MINUTE,energy=5,cash=50,xp=10,level=1,icon='briefcase'),
 dict(id='event',name='Obsługa wydarzenia',district='Centrum',d=3,description='Przygotuj stanowiska partnerów na miejskim wydarzeniu.',duration=20*MINUTE,energy=20,cash=200,xp=40,level=2,icon='briefcase'),
 dict(id='logistics',name='Koordynacja transportu',district='Portowe',d=4,description='Zaplanuj transport dla lokalnych przedsiębiorstw.',duration=40*MINUTE,energy=40,cash=400,xp=80,level=3,icon='route'),
 dict(id='audit',name='Audyt procesów dostaw',district='Biznesowe',d=5,description='Pomóż firmie usprawnić planowanie tras i odbiorów.',duration=30*MINUTE,energy=30,cash=300,xp=60,level=3,icon='book'),
]
# 0.26 Zlecenie specjalne: praca zdalna na PC w rezydencji (brama 7 dni — wiek postaci albo świata).
REMOTE_JOB=dict(id='remote',name='Zlecenie specjalne · praca zdalna',duration=15*MINUTE,energy=10,cash=150,xp=25)

# 2.1c GDD v3.1: surowce (tworzywa/ruda/drewno), wydobycie i skup wycofane z gry.
# Zarobek przechodzi na lokacje usługowe (server/services.py). Akcje gather/sell_materials zwracają 409.
MATERIALS_RETIRED_MSG='Surowce zostały wycofane z gry — zarabiaj w lokacjach usługowych.'
ITEMS=[
 dict(id='basic-gloves',slot='gloves',name='Rękawice treningowe',price=0,bonus=[0,0,0,0,0]),
 dict(id='basic-shirt',slot='shirt',name='Strój klubowy',price=0,bonus=[0,0,0,0,0]),
 dict(id='basic-shoes',slot='shoes',name='Buty sportowe',price=0,bonus=[0,0,0,0,0]),
 dict(id='basic-accessory',slot='accessory',name='Opaska treningowa',price=0,bonus=[0,0,0,0,0]),
 dict(id='urban-gloves',slot='gloves',name='Rękawice Urban',price=250,bonus=[2,0,0,0,0]),
 dict(id='focus-shirt',slot='shirt',name='Strój Focus',price=350,bonus=[0,2,0,1,0]),
 dict(id='sprint-shoes',slot='shoes',name='Buty Sprint',price=300,bonus=[0,0,2,0,0]),
 dict(id='tactical-band',slot='accessory',name='Opaska taktyczna',price=200,bonus=[0,0,0,1,2]),
 dict(id='counter-gloves',slot='gloves',name='Rękawice Counter',price=500,bonus=[2,0,0,0,2]),
]
CONTRACTS.extend([
 dict(id='campaign',name='Kampania lokalnej marki',district='Sportowe',d=6,description='Zaplanuj legalną kampanię dla sąsiedzkiej firmy.',duration=25*MINUTE,energy=25,cash=230,xp=60,level=2,icon='star'),
 dict(id='expo',name='Koordynacja targów biznesowych',district='Kopalnia',d=7,description='Połącz wystawców z usługodawcami i dopilnuj terminów.',duration=60*MINUTE,energy=60,cash=660,xp=100,level=4,icon='business'),
 dict(id='fleet',name='Kontrakt flotowy',district='Portowe',d=4,description='Koordynujesz flotę dostawczą większego klienta. Zlecenie na kilka dni.',duration=8*HOUR,energy=80,cash=1600,xp=240,level=5,icon='route'),
 dict(id='branch',name='Zarządzanie filią',district='Biznesowe',d=5,description='Samodzielnie prowadzisz filię firmy przez pełną dobę.',duration=24*HOUR,energy=140,cash=6000,xp=900,level=7,icon='business'),
])
ITEMS.extend([
 dict(id='analyst-band',slot='accessory',name='Opaska Analyst',price=750,bonus=[0,3,0,0,2],level=2,tier='Specjalistyczne'),
 dict(id='agile-shoes',slot='shoes',name='Buty Agile',price=750,bonus=[0,0,3,0,2],level=2,tier='Specjalistyczne'),
 dict(id='captain-shirt',slot='shirt',name='Strój Captain',price=1200,bonus=[0,2,0,4,0],level=3,tier='Specjalistyczne'),
 dict(id='basic-helmet',slot='helmet',name='Kask treningowy',price=0,bonus=[0,0,0,0,0]),
 dict(id='basic-backpack',slot='backpack',name='Plecak podróżny',price=0,bonus=[0,0,0,0,0]),
 dict(id='basic-amulet',slot='amulet',name='Sznurek z krzemieniem',price=0,bonus=[0,0,0,0,0]),
 dict(id='spartan-helmet',slot='helmet',name='Hełm Spartan',price=800,bonus=[2,0,0,0,1],level=2,tier='Specjalistyczne'),
 dict(id='trekker-pack',slot='backpack',name='Plecak Trekker',price=450,bonus=[0,0,1,0,1],level=2,tier='Specjalistyczne'),
 dict(id='focus-amulet',slot='amulet',name='Amulet Skupienia',price=500,bonus=[0,2,0,0,0],level=2,tier='Specjalistyczne'),
 dict(id='charm-amulet',slot='amulet',name='Amulet Charyzmy',price=650,bonus=[0,0,0,2,0],level=3,tier='Specjalistyczne'),
])
VENTURES={
 # 4.1 GDD v3.1: Corner Café usunięta (decyzja usera) — dochód kawiarni daje budynek „Kawiarnia” w dzielnicy
 'studio':dict(id='studio',name='Studio Forma',level=3,price=4000,rates=[55,80,115,160],costs=[2400,5000,10000]),
}
RESIDENCES=[
 dict(id='studio-flat',name='Kawalerka na Przedmieściach',level=1,price=1200,regen=2,restBonus=0,slots=0,perk='+2 energii / h · bez garażu',description='Własny kąt z dala od miejskiego zgiełku. Sen bez przeszkód, jedno auto pod chmurką.'),
 dict(id='center-apartment',name='Apartament z Miejscem Parkingowym',level=3,price=6000,regen=4,restBonus=10,slots=1,perk='+4 energii / h · odpoczynek +10% · parking na 1 auto',description='Cichy balkon nad bulwarami i miejsce w hali garażowej. Krótsza droga do pełnej formy.'),
 dict(id='green-villa',name='Willa z Garażem Podziemnym',level=5,price=20000,regen=8,restBonus=25,slots=3,perk='+8 energii / h · odpoczynek +25% · garaż na 3 auta',description='Ogród, sauna, cisza i podziemny garaż dla całej floty. Regeneracja na poziomie zawodowca.'),
]
# 3.1 GDD v3.1: katalog 5 aut + nagroda „Mistrz Rankingu”. fuel = spalanie (% baku) na przystanek, fuelPrice = $ za 1% baku.
# Odblokowanie wyłącznie poziomem i gotówką (bez bramek Ery III / VIP — decyzja usera). img = grafiki z 0.59 do czasu Fluttera.
GARAGE=[
 dict(id='dostawczak',name='Dostawczak',price=2000,discount=10,level=1,service=300,fuel=4,fuelPrice=1.0,icon='truck',img='rower',description='Tani start floty: mały, oszczędny, dowiezie wszystko po mieście.'),
 dict(id='sedan',name='Sedan',price=8000,discount=20,level=3,service=800,fuel=3,fuelPrice=1.5,img='sedan',description='Komfort na co dzień: cichy, szybki i najoszczędniejszy w trasie.'),
 dict(id='van',name='Van Rodzinny',price=15000,discount=26,level=5,service=1400,fuel=5,fuelPrice=2.0,icon='truck',img='bus',description='Pojemny i wygodny — dla całej ekipy i większych zleceń.'),
 dict(id='furgonetka',name='Furgonetka',price=25000,discount=32,level=7,service=2000,fuel=5,fuelPrice=2.5,icon='truck',img='furgonetka',description='Zawodowy transport dla dużych kontraktów.'),
 dict(id='suv',name='SUV',price=50000,discount=40,level=10,service=3000,fuel=6,fuelPrice=3.0,img='supercar',description='Mocny, szybki, prestiżowy. Pali sporo, ale dojeżdża najszybciej z aut na sprzedaż.'),
 dict(id='mistrz',name='Mistrz Rankingu',price=0,discount=45,level=1,service=2000,fuel=3,fuelPrice=2.0,img='supercar',buyable=False,bonus=True,description='Nagroda za 7 dni gry. Nie zajmuje miejsca w garażu.'),
]
GARAGE_V=2
LEGACY_CARS={'rower':'dostawczak','bus':'van','supercar':'suv'}  # 3.1: mapowanie po typie (sedan i furgonetka bez zmiany id)
def car(vid):return next((g for g in GARAGE if g['id']==vid),{})
# 3.2 GDD v3.1: paliwo per auto w s['cars'][id]['fuel'] (0–100 %, brak wpisu = pełny bak)
FUEL_VIP=0.8          # VIP: tankowanie −20%
FUEL_MAX_HOPS=2       # najdłuższy odcinek NPC (HOPS) — auto bez paliwa na taki odcinek nie jest przydzielane automatycznie
def fuel_need(vid,hops):return max(1,int(hops or 0))*car(vid).get('fuel',0)
def fuel_of(s,vid):return float(((s.get('cars') or {}).get(vid) or {}).get('fuel',100))
def set_fuel(s,vid,val):
 if not isinstance(s.get('cars'),dict):s['cars']={}
 s['cars'].setdefault(vid,{})['fuel']=round(max(0.0,min(100.0,float(val))),2)
def refuel_cost(s,vid,pct,now,vip=None):
 # vip: status z shop_state (parametr action); bez niego — s['vipUntil'] (asystent)
 v=vip if vip is not None else s.get('vipUntil',0)>now
 return math.ceil(pct*car(vid).get('fuelPrice',1.0)*(FUEL_VIP if v else 1)-1e-9)
def fuel_ready(s,vid):return fuel_of(s,vid)+1e-9>=fuel_need(vid,FUEL_MAX_HOPS)
# 3.3 GDD v3.1: zużycie per auto w s['cars'][id]['wear'] (0–100). s['vehicle']['wear'] = lustro aktywnego auta (zgodność wstecz).
AUTO_MECHANIC_COST=2000   # serwis wszystkich aut naraz (VIP: połowa); wariant 💎 za flagą premium — po włączeniu waluty
def wear_of(s,vid):return float(((s.get('cars') or {}).get(vid) or {}).get('wear',0))
def set_wear(s,vid,val):
 if not isinstance(s.get('cars'),dict):s['cars']={}
 s['cars'].setdefault(vid,{})['wear']=max(0,min(100,int(round(val))))
 if isinstance(s.get('vehicle'),dict) and s['vehicle'].get('id')==vid:s['vehicle']['wear']=s['cars'][vid]['wear']
def worn(s,vid):return wear_of(s,vid)>=100
def migrate_wear(s):
 # 3.3: leniwa migracja — zużycie aktywnego auta trafia do s['cars'], pozostałe auta 0%; potem lustro
 v=s.get('vehicle') if isinstance(s.get('vehicle'),dict) else None
 # zgodność wstecz: zapis w starym polu s['vehicle']['wear'] (stary kod/narzędzia) ma pierwszeństwo nad lustrem
 if v and v.get('id') and (not s.get('wearV') or int(v.get('wear',0))!=int(wear_of(s,v['id']))):set_wear(s,v['id'],v.get('wear',0))
 s['wearV']=1
def migrate_garage(s):
 # 3.1 GDD v3.1: leniwa, wersjonowana (idempotentna) migracja aut z katalogu 0.59 — bez utraty wartości
 if int(s.get('garageV') or 1)>=GARAGE_V:return False
 m=lambda v:LEGACY_CARS.get(v,v)
 s['garage']=list(dict.fromkeys(m(v) for v in (s.get('garage') or [])))
 if isinstance(s.get('vehicle'),dict) and s['vehicle'].get('id'):s['vehicle']['id']=m(s['vehicle']['id'])
 s['garageUp']={m(k):v for k,v in (s.get('garageUp') or {}).items()}
 if s.get('travelCar'):s['travelCar']=m(s['travelCar'])
 for r in (s.get('npcRoutes') or {}).get('runs') or []:
  if isinstance(r,dict) and r.get('vehicle'):r['vehicle']=m(r['vehicle'])
 s['garageV']=GARAGE_V;return True
STAFF={
 'courier':dict(id='kurier',name='Kurier junior',business='City Courier',cost=300,boost=25,hours=24,description='Wzmacnia dochód firmy kurierskiej o 25% przez dobę.'),
 'cafe':dict(id='barista',name='Barista',business='Kawiarnia',cost=250,boost=25,hours=24,description='Szybsza obsługa: dochód kawiarni +25% przez dobę.'),
 'studio':dict(id='trener',name='Trener personalny',business='Studio Forma',cost=500,boost=25,hours=24,description='Więcej klientów: dochód studia +25% przez dobę.'),
}
# 2.1 GDD v3.1: Kopalnia na liście inwestycji (kontrakt expo)
DISTRICTS=['Przemysłowe','Centrum','Portowe','Biznesowe','Sportowe','Kopalnia','Lasy Wschodnie']
# 0.55.0 Moja dzielnica: 6 budynków zamiast zakładek. Poziomy = rozbudowa + bramka Sali Chwały.
BUILDINGS={
 'residence':dict(name='Rezydencja',icon='🏠'),
 'garage':dict(name='Garaż',icon='🚗'),
 'cafe':dict(name='Kawiarnia',icon='☕'),
 'nightclub':dict(name='Klub Nocny',icon='🌃'),  # 4.1 GDD v3.1: nowy budynek, skarbiec 72 h
 'club':dict(name='Sala Klubowa',icon='🥊'),  # 4.1: hub dyscyplin + podmoduł Siłowni (Siłownia nie jest już budynkiem)
 'hall':dict(name='Sala Chwały',icon='🏆'),
}
BUILDING_MAX=5
BUILDING_UPGRADE_COST=[0,500,1500,3000,6000]  # koszt z poziomu i do i+1 (indeks = obecny poziom)
HALL_UNLOCK_COST=10000  # Sala Chwały: opłata za otwarcie, gdy wszystkie budynki mają poziom 5
BUILDING_START=dict(residence=1,garage=1,cafe=1,nightclub=0,club=1,hall=0)  # 4.1: Klub Nocny trzeba wybudować (poziom 0)
# 4.1 GDD v3.1: maksymalne poziomy i koszty per budynek (indeks = obecny poziom → koszt wejścia na następny)
BUILDING_MAXES=dict(residence=5,garage=5,cafe=10,nightclub=7,club=1,hall=1)
CAFE_BUILD_COST=[0,500,1500,3000,6000,10000,16000,25000,38000,55000]
NIGHTCLUB_COST=[5000,4000,8000,15000,25000,40000,60000]  # [0] = budowa 0→1
BUILDING_COSTS=dict(residence=BUILDING_UPGRADE_COST,garage=BUILDING_UPGRADE_COST,cafe=CAFE_BUILD_COST,nightclub=NIGHTCLUB_COST,club=[0])
# M5: czas budowy — po zapłacie budynek stoi w rusztowaniach (działa na starym poziomie), nowy poziom po upływie czasu.
# Jedna budowa naraz, bez przyspieszania. Czas rośnie wykładniczo z poziomem: 5 min → 4 h; Sala Chwały 8 h. Dzielone przez tempo świata.
BUILD_MIN_S=300;BUILD_MAX_S=4*3600;HALL_BUILD_S=8*3600
def build_seconds(b,target):
 if b=='hall':return HALL_BUILD_S
 m=BUILDING_MAXES.get(b,1)
 if m<=1:return BUILD_MIN_S
 f=max(0,min(1,(target-1)/(m-1)))
 return int(round(BUILD_MIN_S*(BUILD_MAX_S/BUILD_MIN_S)**f))
def fmt_build(secs):
 m=max(1,math.ceil(secs/60))
 return f'{m} min' if m<60 else (f'{m//60} h' if m%60==0 else f'{m//60} h {m%60} min')
def construction_sync(s,now):
 c=s.get('construction')
 if c is None:return
 if not isinstance(c,dict) or c.get('building') not in BUILDINGS:s.pop('construction',None);return
 if now<int(c.get('endsAt') or 0):return
 b=c['building'];bl=s['buildings'];t=min(int(c.get('target') or 0),BUILDING_MAXES[b])
 bl[b]=max(int(bl.get(b,0) or 0),t);s.pop('construction',None)
 log(s,(BUILDINGS[b]['name']+' — budowa zakończona, poziom '+str(t)+'.'),int(c.get('endsAt') or now))
# 4.2/4.3 GDD v3.1: skarbce idle budynków — stawki $/h per poziom (progresja geometryczna) i pojemność w godzinach
CAFE_VAULT_RATES=[30,41,55,75,101,137,186,252,342,465]
NIGHTCLUB_RATES=[80,127,202,320,508,806,1280]
BUILDING_VAULTS=dict(cafe=dict(rates=CAFE_VAULT_RATES,hours=24),nightclub=dict(rates=NIGHTCLUB_RATES,hours=72))
# 4.4 GDD v3.1: Buffet — ulepszenie wewnątrz Rezydencji (od poziomu 2 Rezydencji), 3 poziomy posiłków
BUFFET_MIN_RESIDENCE=2
BUFFET_COSTS=[1500,4000,10000]  # koszt wejścia na Buffet lvl 1/2/3 (propozycja — GDD nie podaje)
def prestige_mult(s):
 # 4.5 GDD v3.1: stały bonus dochodu za resety na tym świecie (+10% za reset, max +50%)
 # 8.1 GDD v3.1: + stały bonus stażu (7 dni +10%, 1000 dni +5%) — przeżywa reset
 return 1+min(50,max(0,int((s.get('prestige') or {}).get('bonus',0))))/100+max(0,int(s.get('seniority') or 0))/100
def buffet_level(s):return max(0,min(3,int(s.get('buffet') or 0)))
HALL_REQUIRES=('residence','garage','cafe','nightclub','club')  # 4.1: wszystkie na swoim maksimum (decyzja usera)
def migrate_buildings(s):
 # 4.1 GDD v3.1: idempotentna migracja — Siłownia znika (bez zwrotu), Sala Klubowa max 1,
 # Corner Café → skarbiec wypłacony do gotówki, poziom budynku Kawiarnia = max(budynek, firma)
 bl=s['buildings'];bl.pop('gym',None)
 for k,v in BUILDING_START.items():bl.setdefault(k,v)
 for k,m in BUILDING_MAXES.items():bl[k]=max(0,min(int(bl.get(k,0) or 0),m))
 if not isinstance(s.get('vaults'),dict):s['vaults']={}
 for k in BUILDING_VAULTS:s['vaults'].setdefault(k,0)
 v=(s.get('ventures') or {}).pop('cafe',None) if isinstance(s.get('ventures'),dict) else None
 if isinstance(v,dict):
  s['cash']=s.get('cash',0)+math.floor(v.get('vault',0)+1e-7)
  bl['cafe']=max(bl['cafe'],min(int(v.get('level',1)),BUILDING_MAXES['cafe']))
def vault_sync(s,old,now,speed,cap_mult):
 # 4.2/4.3: naliczanie skarbców Kawiarni (24 h) i Klubu Nocnego (72 h); Barista dalej przyspiesza Kawiarnię
 for k,cfg in BUILDING_VAULTS.items():
  lv=s['buildings'].get(k,0)
  if lv<1:continue
  b=dict(level=lv,vault=s['vaults'].get(k,0),upgrade=None)
  business_sync(b,old,now,cfg['rates'],speed,s['staff'].get(k,0),cap_mult*cfg['hours']/24)
  s['vaults'][k]=b['vault']
# === 0.56.0 — Trasy NPC: kierowcy z Rezydencji wożą flotą z Garażu (offline → kasa + EXP) ===
NPC_ROUTES=[
 dict(id='courier',name='Kurierka miejska',line='Nadmorskie ↔ Przemysłowe',minutes=15,cash=180,xp=8),
 dict(id='tram',name='Tramwaj towarowy',line='Centrum ↔ Portowe',minutes=30,cash=380,xp=16),
 dict(id='portbiz',name='Port–Biznes',line='Portowe ↔ Biznesowe',minutes=45,cash=620,xp=26),
 dict(id='ring',name='Ring sportowy',line='Biznesowe ↔ Sportowe',minutes=60,cash=900,xp=40),
 dict(id='timber',name='Tarcica z Lasów',line='Lasy Wschodnie ↔ Przemysłowe',minutes=75,cash=1150,xp=55),
 dict(id='ore',name='Transport rudy',line='Kopalnia Rudy ↔ Biznesowe',minutes=90,cash=1500,xp=70),
]
# === 0.57.0 — Sojusze: wspólne budynki organizacji (z funduszu), premie dla wszystkich członków ===
ALLY_BUILDINGS=[
 dict(id='fast_build',name='Szybka Budowa',icon='🏗️',pct=10,desc='Rozbudowa firmy krótsza o 10% na poziom.'),
 dict(id='cheap_repair',name='Tanie Naprawy',icon='🔧',pct=15,desc='Serwis auta tańszy o 15% na poziom.'),
 dict(id='freedom',name='Wolność',icon='🕊️',pct=10,desc='Podróże po mieście krótsze o 10% na poziom.'),
]
ALLY_MAX=3
ALLY_COST=[2000,5000,10000]
def ally_levels(c,cid):
 row=c.execute('SELECT o.buildings FROM organizations o JOIN org_members m ON m.org_id=o.id WHERE m.character_id=?',(cid,)).fetchone()
 if not row:return {}
 try:v=json.loads(row[0] or '{}')
 except Exception:v={}
 return v if isinstance(v,dict) else {}
def ally_mult(s,key):
 b=next(x for x in ALLY_BUILDINGS if x['id']==key)
 return 1-b['pct']*min(ALLY_MAX,int((s.get('ally') or {}).get(key,0)))/100
# === 0.58.0 — Eventy czasowe: globalna rotacja okien 6 h z zegara serwera (te same dla wszystkich) ===
EVENT_WINDOW=6*HOUR
TIMED_EVENTS=[
 dict(id='gold_rush',name='Gorączka Kontraktów',icon='💼',effect='contract_cash',mult=1.25,desc='Kontrakty płacą +25% gotówki.'),
 dict(id='bus_free',name='Darmowa Komunikacja',icon='🚌',effect='bus_free',mult=0.0,desc='NPC wysłani na zmianę w tym oknie nie płacą za bilety autobusowe przez całą zmianę.'),  # 2.4e: zamiast Szczytu Przewozów (trasy wycofane); mult = mnożnik ceny biletu
 dict(id='study',name='Dzień Nauki',icon='📚',effect='contract_xp',mult=1.5,desc='Kontrakty dają +50% EXP.'),  # 1.10 GDD v3.1: okno 6 h — „Dzień”, nie „Tydzień”
 dict(id='service_rush',name='Szczyt Usług',icon='🏪',effect='service_cash',mult=1.25,desc='Zarobek NPC w lokacjach usługowych +25%.'),  # 2.1c: zamiast Dnia Targowego (efekt działa od 2.4)
]
ROUTES_RETIRED='Trasy miejskie wycofane na rzecz systemu zatrudnienia usługowego.'
def timed_event(now):
 i=int(now//EVENT_WINDOW);start=i*EVENT_WINDOW
 cur=TIMED_EVENTS[i%len(TIMED_EVENTS)];nxt=TIMED_EVENTS[(i+1)%len(TIMED_EVENTS)]
 return dict(cur,start=start,end=start+EVENT_WINDOW,next=dict(id=nxt['id'],name=nxt['name'],icon=nxt['icon'],desc=nxt['desc']))
def ev_mult(now,effect):
 e=timed_event(now);return e['mult'] if e['effect']==effect else 1.0
def vehicle_busy_until(s,veh,now):
 # 1.4 GDD v3.1: koniec najdłuższej trwającej trasy NPC tym autem (0 = auto wolne)
 if not veh:return 0
 npc_end=int((s.get('npcCars') or {}).get(veh) or 0)  # 2.4c GDD v3.1: auto na zmianie NPC (wstrzykiwane z tabeli npcs)
 return max([x.get('end',0) for x in (s.get('npcRoutes') or {}).get('runs',[]) if isinstance(x,dict) and x.get('vehicle')==veh and x.get('end',0)>now]+([npc_end] if npc_end>now else []) or [0])
def clock_hm(ms):
 # Godzina UTC HH:MM dla komunikatów (klient dostaje też liczbę minut)
 return time.strftime('%H:%M',time.gmtime(ms/1000))+' UTC'
def ev_snapshot(now):
 # 1.3 GDD v3.1: mnożniki eventu zamrażane przy starcie zadania (odbiór nie liczy ich od nowa)
 return dict(contract_cash=ev_mult(now,'contract_cash'),contract_xp=ev_mult(now,'contract_xp'),route_cash=ev_mult(now,'route_cash'))
def ev_frozen(task,effect):
 # Zadania sprzed 1.3 (bez zapisu): mnożnik z chwili UKOŃCZENIA (end), nigdy z chwili odbioru
 ev=task.get('ev')
 return ev.get(effect,1.0) if isinstance(ev,dict) else ev_mult(task.get('end',0),effect)
VEH_MULT={'dostawczak':0.85,'furgonetka':1.0,'sedan':1.15,'van':1.25,'suv':1.45,'mistrz':1.45}  # 3.1: tylko odbiór tras sprzed 2.4e
def route_slots(s):
 return max(1,int((s.get('buildings') or {}).get('residence',1)))
def route_payout(s,base,veh):
 g=max(1,int((s.get('buildings') or {}).get('garage',1)))
 return round(base*VEH_MULT.get(veh,1.0)*(1+0.02*(g-1)))

INVEST_RENAME={'Przedmieścia':'Lasy Wschodnie','Port':'Portowe','Dzielnica biznesowa':'Biznesowe','Dzielnica kreatywna':'Sportowe','Centrum konferencyjne':'Kopalnia','Strefa Przemysłowa':'Przemysłowe','Zakłady Miejskie':'Przemysłowe'}  # 2.1b GDD v3.1
INVEST_STEP=1000
INVEST_CAP=None  # 8.3 GDD v3.1: bez limitu kwotowego na dzielnicę (było 20 000 $); jednorazowa wpłata nadal 100–5000 $
BP_HOOK=[None]  # 8.4: battlepass.add_xp(c,cid,source) — XP przepustki (npc/pvp/dungeon/build)
TERRITORY_HOOK=[None]  # 8.3: features.controls(c,cid,district) — czy sojusz/federacja postaci trzyma dzielnicę (>55%)
CONTROL_SHARE=0.55
CONTROL_NPC_BONUS=0.05
RESTS=[
 dict(id='nap',name='Krótki sen',duration=20*MINUTE,energy=10,tier=1,icon='clock',description='Dwadzieścia minut drzemki. +10 energii po przebudzeniu.'),
 dict(id='night',name='Nocny odpoczynek',duration=4*HOUR,energy=70,tier=2,icon='clock',description='Przespana noc. +70 energii po przebudzeniu.'),
 dict(id='spa',name='Weekend w spa',duration=8*HOUR,energy=160,tier=3,icon='clock',description='Sauna, masaż, cisza. +160 energii po przebudzeniu.'),
]
class RuleError(Exception): pass

def _seed(*parts):
 import hashlib
 return int.from_bytes(hashlib.sha256('|'.join(str(x) for x in parts).encode()).digest()[:4],'big')
def price_mult(wid,key,day):
 # Same for every player of a world on a given UTC day: 0.85..1.15 of list price.
 return round(0.85+_seed(wid,key,day)%31/100,2)
def day_of(ms):return ms//(24*HOUR)
def daily_tender(wid,cid,day):
 pool=[c for c in CONTRACTS if c['duration']>=20*MINUTE]
 c=pool[_seed(wid,cid,day,'tender')%len(pool)]
 return dict(day=day,contract=c['id'],name=c['name'],duration=round(c['duration']),energy=c['energy'],xp=c['xp'],level=c['level'],cash=round(c['cash']*(1.10+_seed(wid,cid,day,'cash')%21/100)),expires_at=(day+1)*24*HOUR)
def invest_bonus(s,district):return min(15,(s.get('invested',{}).get(district,0))//INVEST_STEP)+stat_pct(s,4,0.5,25)  # 0.35: Spryt wzmacnia wpływy
HOPS={2:1,3:1,4:2,5:2,6:1,7:2,8:1}  # 0.45: odległość koleją od Mojego Miasta (przystanki)
def hop_bonus(c):return 4*HOPS.get(c.get('d'),0)  # 0.45: bonus za dojazd rozdzielony na kontrakty (+4% / przystanek)
def payout(wid,s,c,day):
 # List price × daily market × district investments. Tender tasks carry a fixed price.
 return round(c['cash']*price_mult(wid,c['id'],day)*(1+(invest_bonus(s,c['district'])+hop_bonus(c))/100))
GARAGE_UP_MAX=3  # 0.49: trzy poziomy ulepszeń (silnik, zawieszenie, lakier)
def garage_up_bonus(lvl):
 return 4*int(lvl or 0)
def garage_up_cost(g,lvl):
 return int(round(g['price']*0.4*(int(lvl)+1)/10)*10)
def vehicle_discount(s):
 v=s.get('vehicle')
 if not v or worn(s,v['id']):return 0  # 3.3: 100% zużycia = brak rabatu
 g=next((g for g in GARAGE if g['id']==v['id']),None)
 return (g['discount'] if g else 0)+garage_up_bonus(s.get('garageUp',{}).get(v['id'],0))

def level(xp): return int((1+math.sqrt(1+8*xp/100))//2)
CLASSES={'bokser':dict(label='Bokser',icon='🥊',stats=[14,8,10,10,8],passive='1/6 szansy na Mocny Cios (×1,6) i +12% obrażeń',desc='Siła i presja — wymiana ciosów to Twój żywioł.'),'obronca':dict(label='Obrońca',icon='🛡️',stats=[8,14,8,12,8],passive='−20% otrzymywanych obrażeń, 1/8 szansy na Kontrę po bloku',desc='Inteligencja i charyzma — twardy orzech, który jeszcze odbija.'),'szybki':dict(label='Szybki',icon='⚡',stats=[8,8,14,8,12],passive='30% szansy na Kontrę po uniku, unik +8 pp, crit rośnie z każdym trafieniem (do +25%), inicjatywa +5',desc='Refleks i spryt — pierwszy uderzasz, pierwszy znikasz.')}
LOCATIONS={'ulica':'Ulica','silownia':'Siłownia','klub':'Klub Sportowy','targ':'Targ','brama-lochow':'Brama Lochu'}
def new(now,test=False,stats=None):
 return dict(version=1,offset=0,lastTick=now,cash=3000 if test else 300,xp=0,energy=240 if test else 120,stats=list(stats) if stats else [10]*5,business=dict(level=1,vault=0,upgrade=None),contracts=[],training=[],inventory=[i['id'] for i in ITEMS if i['price']==0],equipped={i['slot']:i['id'] for i in ITEMS if i['price']==0},completed=dict(contracts=0,training=0,collected=0),sequence=0,history=[],ventures=dict(cafe=None),tutorialDismissed=False,residence=None,rest=None,lastAction=now,vehicle=None,garage=[],garageUp={},staff={},invested={},tenderDone=None,materials=dict(tworzywa=0,ruda=0,drewno=0),buildings=dict(BUILDING_START))
def residence_of(s):return next((r for r in RESIDENCES if r['id']==s.get('residence')),None)
ENERGY_BASE=240
DAY_MS=24*3600000
# QA 5: Łucznictwo i Pływanie — 3 podejścia dziennie, efekty kumulują się do północy (UTC, jak reszta liczników dobowych)
ARCHERY_MAX_PCT=(0,3,6,10)    # +% maks. energii po 1/2/3 podejściach
SWIM_STAT_PCT=(0,3,6,10)      # +% statystyki klasowej
SWIM_REGEN_PCT=(0,1,3,5)      # +% regeneracji energii
CLASS_STAT={'bokser':0,'obronca':1,'szybki':2}
def daily_stack(s,key):
 # liczba podejść dzisiaj (0–3); dzień liczony z lastTick, który sync() przesuwa na „teraz”
 d=((s.get('sports2') or {}).get(key) or {})
 return min(3,int(d.get('n',0))) if d.get('day')==int(s.get('lastTick') or 0)//DAY_MS else 0
def energy_max(s):return round(ENERGY_BASE*(1+ARCHERY_MAX_PCT[daily_stack(s,'archery3')]/100))
def regen(s):return (10+(residence_of(s) or dict(regen=0))['regen'])*(1+SWIM_REGEN_PCT[daily_stack(s,'swim3')]/100)
def log(s,text,now):
 s['history'].insert(0,dict(text=text,at=now));s['history']=s['history'][:20]
def business_sync(b,from_,now,rates,speed,boost_until=0,cap_mult=1.0):
 # Accrue per segment so a staff contract that expires mid-way splits the windows exactly.
 def accrue(a,z,boosted):
  ms=z-a
  if ms<=0:return
  r=rates[b['level']-1]*(1+boost/100 if boosted else 1)
  b['vault']=min(b['vault']+ms/HOUR*r*speed,r*speed*24*cap_mult)
 boost=25 if boost_until else 0
 u=b.get('upgrade')
 pts={from_,now}
 if u and from_<u['end']<=now:pts.add(u['end'])
 if from_<boost_until<now:pts.add(boost_until)
 for a,z in zip(sorted(pts),sorted(pts)[1:]):
  accrue(a,z,boost_until>=z)
  if u and z==u['end']:b['level']=u['target'];b['upgrade']=None
def sync(s,now,speed):
 for k in ('tactic','pvpDefense'):s.pop(k,None)  # 5.1 GDD v3.1: Klasa = Taktyka — wybór taktyki i szablony obrony usunięte ze stanu (migracja leniwa)
 for key,value in (('residence',None),('rest',None),('lastAction',now),('vehicle',None),('garage',[]),('garageUp',{}),('staff',{}),('buildings',dict(BUILDING_START)),('invested',{}),('tenderDone',None),('horse',None),('pvpDefense',None),('npcRoutes',dict(runs=[],done=0,cash=0,xp=0))):
  # States saved by earlier development builds predate 0.8/0.9 keys; absent keys default safely.
  if key not in s:s[key]=value
 # 0.45.2: type guards — states seeded or saved by interim builds may hold wrong shapes (list instead of dict, object instead of id).
 if not isinstance(s['staff'],dict):s['staff']={}
 s.pop('materials',None)  # 2.1c GDD v3.1: surowce wycofane, bez rekompensaty (decyzja usera)
 if not isinstance(s.get('buildings'),dict):s['buildings']=dict(BUILDING_START)
 migrate_buildings(s)  # 4.1 GDD v3.1
 if not isinstance(s['invested'],dict):s['invested']={}
 if not isinstance(s.get('npcRoutes'),dict):s['npcRoutes']=dict(runs=[],done=0,cash=0,xp=0)
 if not isinstance(s['npcRoutes'].get('runs'),list):s['npcRoutes']['runs']=[]
 s['npcRoutes']['runs']=[x for x in s['npcRoutes']['runs'] if isinstance(x,dict)]
 # 0.54.0: migracja kluczy inwestycji po przemianowaniu dzielnic (miasta + surowce).
 for old,new in INVEST_RENAME.items():
  if old in s['invested']:s['invested'][new]=s['invested'].get(new,0)+s['invested'].pop(old)
 if not isinstance(s['garage'],list):s['garage']=[]
 if not isinstance(s.get('garageUp'),dict):s['garageUp']={}
 migrate_garage(s)  # 3.1 GDD v3.1
 migrate_wear(s)  # 3.3 GDD v3.1
 if not isinstance(s['invested'],dict):s['invested']={}
 if s['residence'] is not None and not isinstance(s['residence'],str):s['residence']=None
 s.setdefault('completed',{})
 for k in ('contracts','training','collected','rests'):s['completed'].setdefault(k,0)
 now=max(s['lastTick'],now);old=s['lastTick'];s['energy']=min(energy_max(s),s['energy']+(now-old)/HOUR*regen(s)*speed);s['energyMax']=energy_max(s)
 previous=s['business']['level'];vcap=1+stat_pct(s,0,2,40)/100  # 0.35: Siła powiększa skarbiec
 business_sync(s['business'],old,now,RATES,speed,s['staff'].get('courier',0),vcap)
 if s['business']['level']!=previous:log(s,'City Courier: zakończono rozbudowę.',now)
 for key,v in VENTURES.items():
  s['ventures'].setdefault(key,None)
  if s['ventures'][key]:business_sync(s['ventures'][key],old,now,v['rates'],speed,s['staff'].get(key,0),vcap)
 vault_sync(s,old,now,speed,vcap)  # 4.2/4.3 GDD v3.1
 construction_sync(s,now)  # M5: zakończenie budowy po upływie czasu
 s['lastTick']=now
 return s

def spend(s,cash=0,energy=0):
 if s['cash']<cash: raise RuleError('Za mało gotówki.')
 if s['energy']+1e-8<energy:raise RuleError('Za mało energii.')
 s['cash']-=cash;s['energy']=max(0,s['energy']-energy)
DUNGEON_ITEMS=[
 dict(id='buty-cienia',slot='shoes',name='Buty Cienia',price=0,unique=True,bonus=[0,0,2,0,1]),
 dict(id='rekawice-lochu',slot='gloves',name='Rękawice Lochu',price=0,unique=True,bonus=[2,0,0,0,1]),
 dict(id='korona-wladcy',slot='accessory',name='Korona Władcy Lochu',price=0,unique=True,bonus=[2,2,0,2,0]),
 dict(id='helm-lochu',slot='helmet',name='Hełm Lochu',price=0,unique=True,bonus=[1,0,0,0,1]),
]
GEAR_HOOK=[None]  # 7.2 GDD v3.1: gear.bonus(s) — sety T1–T4 (skalowanie z poziomem, komplet +30%)
LEGACY_SHOP_OPEN=False  # 7.3 GDD v3.1: stary sklep wycofany — sety w Sali Klubowej (przedmioty graczy zostają)
def effective(s):
 stats=s['stats'].copy()
 for id_ in s['equipped'].values():
  item=next((i for i in ITEMS+DUNGEON_ITEMS if i['id']==id_),None)  # 7.1: przedmioty setów liczy GEAR_HOOK
  if item:stats=[a+b for a,b in zip(stats,item['bonus'])]
 if GEAR_HOOK[0]:stats=[a+b for a,b in zip(stats,GEAR_HOOK[0](s))]
 # QA 5: Pływanie — +3/6/10% do statystyki klasowej do północy (zastępuje kondycję 48 h z 0.43)
 n=daily_stack(s,'swim3')
 if n:
  i=((s.get('sports2') or {}).get('swim3') or {}).get('stat',0)
  stats[i]=round(stats[i]*(1+SWIM_STAT_PCT[n]/100),1)
 return stats

def over(s,i):  # 0.35: staty ogólne grają w całej grze — bonus od każdego punktu powyżej 10 (efektowne, z wyposażeniem)
 return max(0,effective(s)[i]-10)
# 8.2 GDD v3.1: capy PvE — każdy bonus poza walką rośnie liniowo do 30 pkt statystyki i tam się zatrzymuje
# (decyzja usera: cap zawsze przy 30 pkt → bonus = cap × min(stat,30)/30). Powyżej 30 pkt statystyka działa już tylko w PvP.
PVE_CAP=[10,15,10,15,10]  # Siła: szybsze kontrakty · Int: firmy · Refleks: transport · Charyzma: zarobki · Spryt: kontrakty
PVE_MAX_STAT=30
def pve_pct(s,i):
 return round(PVE_CAP[i]*min(max(0,effective(s)[i]),PVE_MAX_STAT)/PVE_MAX_STAT,2)
STAT_NAMES=('Siła','Inteligencja','Refleks','Charyzma','Spryt')
GYM_BASE,GYM_PER_POINT=50,15  # QA 3: Koszt = 50 $ + wartość statystyki × 15 $
def gym_cost(s,i):
 # bazowa statystyka (bez ekwipunku); Charyzma nadal targuje cenę (0.35) w ramach capu GDD
 return round((GYM_BASE+int(s['stats'][i])*GYM_PER_POINT)*(1-stat_pct(s,3,0.3,9)/100))
def stat_pct(s,i,per,cap):
 # 'per' zostaje w sygnaturze (stare wywołania); efekt nigdy nie przekracza capu GDD danej statystyki
 return min(cap,pve_pct(s,i))

def action(s,kind,p,now,speed,wid=0,cid=0,district=1,traveling=False,veteran=False,era=4,vip=False):
 sync(s,now,speed);message='Zapisano.'
 if traveling and kind in ('contract','train','tender_accept','home_train','remote_work'):raise RuleError('Jesteś w drodze — kontrakty i treningi poczekają na przyjazd.')
 if kind in ('gather','sell_materials'):raise RuleError(MATERIALS_RETIRED_MSG)  # 2.1c GDD v3.1
 if kind=='upgrade_buffet':
  # 4.4 GDD v3.1: rozbudowa Buffetu w Rezydencji
  if s['buildings'].get('residence',1)<BUFFET_MIN_RESIDENCE:raise RuleError('Buffet wymaga Rezydencji na poziomie '+str(BUFFET_MIN_RESIDENCE)+'.')
  lv=buffet_level(s)
  if lv>=3:raise RuleError('Buffet jest na najwyższym poziomie (Premium catering).')
  cost=BUFFET_COSTS[lv]
  if s['cash']<cost:raise RuleError('Buffet poziom '+str(lv+1)+' kosztuje '+str(cost)+' $ — brakuje gotówki.')
  spend(s,cash=cost);s['buffet']=lv+1
  message='🍽️ Buffet poziom '+str(lv+1)+' — '+('Zwykłe jedzenie','Dobre jedzenie','Premium catering')[lv]+'.'
  log(s,message,now);s['lastAction']=now;return message
 if kind=='upgrade_building':
  b=p.get('building') or ''
  if b not in BUILDINGS:raise RuleError('Nieznany budynek.')
  bl=s.setdefault('buildings',dict(BUILDING_START))
  construction_sync(s,now)
  if s.get('construction'):
   cb=s['construction'];left=max(1,math.ceil((int(cb['endsAt'])-now)/60000))
   raise RuleError('Trwa już budowa: '+BUILDINGS[cb['building']]['name']+' (jeszcze '+str(left)+' min). Jedna budowa naraz.')
  def start_build(b,target):
   secs=max(1,int(build_seconds(b,target)/max(speed,1e-9)))
   s['construction']=dict(building=b,target=target,startedAt=now,endsAt=now+secs*1000)
   return secs
  if b=='hall':
   if bl.get('hall',0)>=1:raise RuleError('Sala Chwały jest już odblokowana.')
   if any(bl.get(k,0)<BUILDING_MAXES[k] for k in HALL_REQUIRES):raise RuleError('Sala Chwały otwiera się, gdy wszystkie budynki osiągną maksymalny poziom (Rezydencja 5, Garaż 5, Kawiarnia 10, Klub Nocny 7, Sala Klubowa 1).')
   spend(s,cash=HALL_UNLOCK_COST);secs=start_build('hall',1);message='🏗️ Ruszyła budowa Sali Chwały — gotowe za '+fmt_build(secs)+'.'
  else:
   lv=bl.get(b,BUILDING_START[b])
   if lv>=BUILDING_MAXES[b]:raise RuleError('Budynek jest na najwyższym poziomie.')
   cost=BUILDING_COSTS[b][lv]
   if s['cash']<cost:raise RuleError(('Budowa' if lv==0 else 'Rozbudowa')+' kosztuje '+str(cost)+' $ — brakuje gotówki.')
   spend(s,cash=cost);secs=start_build(b,lv+1)
   message=('🏗️ Ruszyła budowa: '+BUILDINGS[b]['name'] if lv==0 else '🏗️ Ruszyła rozbudowa: '+BUILDINGS[b]['name']+' → poziom '+str(lv+1))+' — gotowe za '+fmt_build(secs)+'.'
  log(s,message,now);s['lastAction']=now;return message
 if kind=='collect_nightclub' or (kind=='collect' and p.get('business') in BUILDING_VAULTS):
  # 4.2/4.3 GDD v3.1: odbiór skarbca budynku z dowolnego miejsca (decyzja usera)
  k='nightclub' if kind=='collect_nightclub' else p['business']
  if s['buildings'].get(k,0)<1:raise RuleError('Najpierw wybuduj '+BUILDINGS[k]['name']+'.')
  amount=math.floor(s['vaults'].get(k,0)+1e-7)
  if amount<1:raise RuleError('W skarbcu nie ma jeszcze 1 $.')
  s['vaults'][k]-=amount;amount=round(amount*prestige_mult(s));s['cash']+=amount;  # 4.5: bonus resetu
  s['completed']['collected']=s['completed'].get('collected',0)+amount
  message=f'{BUILDINGS[k]["icon"]} Odebrano {amount} $ — {BUILDINGS[k]["name"]}.';log(s,message,now);s['lastAction']=now;return message
 if kind=='buy_business' and p.get('business')=='cafe':raise RuleError('Corner Café została zamknięta — Kawiarnia to teraz budynek w Twojej dzielnicy.')
 if kind=='upgrade' and p.get('business')=='cafe':return action(s,'upgrade_building',dict(building='cafe'),now,speed,wid,cid,district,traveling,veteran,era,vip)  # zgodność ze starym przyciskiem
 if district!=2 and kind in ('collect','upgrade','buy_business'):raise RuleError('Zarządzanie firmami odbywa się w Zakładach Miejskich (dzielnica 2) — najpierw tam pojedź.')
 if kind=='contract':
  c=next((x for x in CONTRACTS if x['id']==p.get('contract')),None)
  if not c:raise RuleError('Nieznany kontrakt.')
  if level(s['xp'])<c['level']:raise RuleError('Wymagany wyższy poziom postaci.')
  if c.get('d') and district!=c['d']:raise RuleError('Zlecenie czeka w lokalizacji: '+c['district']+' (dzielnica '+str(c['d'])+') — jedź tam z mapy.')  # 0.45
  if len(s['contracts'])>=4:raise RuleError('Kolejka kontraktów jest pełna.')
  spend(s,energy=c['energy']);start=max([now]+[t['end'] for t in s['contracts']]);s['sequence']+=1
  disc=min(50,vehicle_discount(s)+stat_pct(s,0,0.4,20))  # 0.35: Siła skraca kontrakty (jak pojazd, wspólny limit 50%)
  s['contracts'].append(dict(id=s['sequence'],contract=c['id'],start=start,end=start+round(c['duration']*(100-disc)/100/speed),ev=ev_snapshot(now)))
  message='Przyjęto: '+c['name']+'.'+(f' {disc}% szybciej dzięki pojazdowi i sile.' if disc else '');log(s,message,now)
 elif kind in ('claim_contract','claim_training'):
  training=kind=='claim_training';queue=s['training' if training else 'contracts'];t=next((t for t in queue if t['id']==p.get('task_id')),None)
  if not t:raise RuleError('Nagroda została już odebrana albo zadanie nie istnieje.')
  if t['end']>now:raise RuleError('Zadanie jeszcze trwa.')
  if training:
   s['stats'][t['stat']]+=1;s['completed']['training']+=1;message='Trening ukończony. +1 punkt statystyki.'
  else:
   c=next((c for c in CONTRACTS if c['id']==t['contract']),REMOTE_JOB if t.get('contract')=='remote' else None)
   cash=t.get('cash') if t.get('tender') else payout(wid,s,c,day_of(t['end']))
   cash=cash if isinstance(cash,int) and cash>0 else c['cash']
   if t['contract']=='remote':cash=round(cash*(1+stat_pct(s,1,0.6,30)/100))  # 0.35: Inteligencja podnosi stawki PC
   if s.get('vipUntil',0)>now:cash=round(cash*1.25)  # 0.14 VIP (dev shop): +25% contract cash
   cash=round(cash*(1+pve_pct(s,3)/100))  # 8.2: Charyzma — zarobki (max +15% przy 30 pkt)
   cash=round(cash*ev_frozen(t,'contract_cash')*prestige_mult(s));s['cash']+=cash;s['xp']+=round(c['xp']*ev_frozen(t,'contract_xp')*(1+pve_pct(s,4)/100));s['completed']['contracts']+=1  # 8.2: Spryt — kontrakty (XP, max +10%)
   if s.get('vehicle') and t['contract']!='remote':  # praca zdalna nie zużywa auta
    set_wear(s,s['vehicle']['id'],wear_of(s,s['vehicle']['id'])+6)  # 3.3: zużycie per auto
    if worn(s,s['vehicle']['id']):log(s,'Pojazd wymaga serwisu — utracił przyspieszenie.',now)
   message=f"Odebrano {cash} $ i {c['xp']} XP."
  queue.remove(t);log(s,message,now)
 elif kind=='train':
  # QA 3: siłownia NATYCHMIASTOWA — płacisz i od razu +1; koszt rośnie z poziomem statystyki
  index=p.get('stat')
  if type(index)!=int or not 0<=index<5:raise RuleError('Nieznana statystyka.')
  if s['stats'][index]>=9990:raise RuleError('Limit statystyki w wersji rozwojowej.')
  cost=gym_cost(s,index)
  spend(s,cash=cost,energy=5)
  s['stats'][index]+=1;s['completed']['training']+=1
  message=f'💪 {STAT_NAMES[index]} +1 (teraz {s["stats"][index]}) · zapłacono {cost} $.'
 elif kind=='home_train':  # 0.26 trening domowy: koszt tylko energii, bez opłat trenerskich klubu
  if not residence_of(s):raise RuleError('Trening domowy wymaga własnego mieszkania — najpierw się wprowadź.')
  index=p.get('stat')
  if type(index)!=int or not 0<=index<5:raise RuleError('Nieznana statystyka.')
  if len(s['training'])>=4:raise RuleError('Kolejka treningów jest pełna.')
  spend(s,energy=12);start=max([now]+[t['end'] for t in s['training']]);s['sequence']+=1
  s['training'].append(dict(id=s['sequence'],stat=index,start=start,end=start+round(10*MINUTE/speed)));message='Trening domowy w kolejce — wolniejszy niż klubowy, ale bez opłat.'
 elif kind in ('buy','equip'):
  item=next((i for i in ITEMS+DUNGEON_ITEMS if i['id']==p.get('item')),None)
  if not item:raise RuleError('Nieznany przedmiot.')
  if kind=='buy':
   if not LEGACY_SHOP_OPEN:raise RuleError('Stary sklep jest zamknięty — sety kupisz w Sali Klubowej.')  # 7.3 GDD v3.1
   if item.get('unique'):raise RuleError('To skarb z Lochu — nie do kupienia.')
   if level(s['xp'])<item.get('level',1):raise RuleError('Ten przedmiot wymaga wyższego poziomu postaci.')
   if item['id'] in s['inventory'] or item['price']==0:raise RuleError('Ten przedmiot już posiadasz.')
   spend(s,cash=round(item['price']*(1-stat_pct(s,3,0.3,9)/100)))  # 0.35: Charyzma targuje się u wyposażeniowca
   s['inventory'].append(item['id']);message='Kupiono i założono: '+item['name']+'.'
  elif item['id'] not in s['inventory']:raise RuleError('Nie posiadasz tego przedmiotu.')
  else:message='Założono: '+item['name']+'.'
  s['equipped'][item['slot']]=item['id'];log(s,message,now)
 elif kind=='buy_business':
  key=p.get('business');v=VENTURES.get(key)
  if not v:raise RuleError('Nieznana firma.')
  if s['ventures'][key]:raise RuleError('Już posiadasz tę firmę.')
  if level(s['xp'])<v['level']:raise RuleError('Firma wymaga poziomu '+str(v['level'])+'.')
  spend(s,cash=v['price']);s['ventures'][key]=dict(level=1,vault=0,upgrade=None);message='Otwarto '+v['name']+'.';log(s,message,now)
 elif kind in ('collect','upgrade'):
  key=p.get('business','courier')
  if key!='courier' and key not in VENTURES:raise RuleError('Nieznana firma.')
  b=s['business'] if key=='courier' else s['ventures'][key]
  rates=RATES if key=='courier' else VENTURES[key]['rates'];costs=COSTS if key=='courier' else VENTURES[key]['costs']
  if not b:raise RuleError('Nie posiadasz tej firmy.')
  if kind=='collect':
   amount=math.floor(b['vault']+1e-7)
   if amount<1:raise RuleError('W skarbcu nie ma jeszcze 1 $.')
   b['vault']=max(0,b['vault']-amount);amount=round(amount*prestige_mult(s));s['cash']+=amount;  # 4.5: bonus resetu
   s['completed']['collected']=s['completed'].get('collected',0)+amount;message=f'Odebrano {amount} $ z firmy.'
  else:
   if b['upgrade']:raise RuleError('Rozbudowa już trwa.')
   if era<2 and b['level']>=2:raise RuleError('W Erze I (Czas Pionierów) firmy rosną najwyżej do poziomu 2 — kolejny poziom odblokuje Era II (Rozwój Przemysłu).')
   if b['level']>=len(rates):raise RuleError('Maksymalny poziom w wersji rozwojowej.')
   ucost=round(costs[b['level']-1]*(1-stat_pct(s,1,0.3,15)/100))  # 0.35: Inteligencja negocjuje ceny rozbudowy
   spend(s,cash=ucost);b['upgrade']=dict(target=b['level']+1,start=now,end=now+round(10*MINUTE/speed*ally_mult(s,'fast_build')));message='Rozbudowa rozpoczęta.'+(f' Inteligencja zaoszczędziła {costs[b["level"]-1]-ucost} $.' if ucost<costs[b["level"]-1] else '')
  log(s,message,now)
 elif kind=='tutorial_dismiss':s['tutorialDismissed']=True;message='Samouczek zamknięty. Możesz go otworzyć ponownie.'
 elif kind=='buy_residence':
  r=next((r for r in RESIDENCES if r['id']==p.get('residence')),None)
  if not r:raise RuleError('Nieznana rezydencja.')
  current=residence_of(s)
  if current and current['id']!=r['id'] and current['regen']>=r['regen']:raise RuleError('Masz już rezydencję z lepszą regeneracją.')
  if current and current['id']==r['id']:raise RuleError('Tam już mieszkasz.')
  if level(s['xp'])<r['level']:raise RuleError('Ta rezydencja wymaga poziomu '+str(r['level'])+'.')
  spend(s,cash=r['price']);s['residence']=r['id'];message='Zamieszkałeś: '+r['name']+'.'
 elif kind=='remote_work':  # 0.26 praca zdalna na PC: gotówka i XP kariery bez wychodzenia z domu
  if not residence_of(s):raise RuleError('Praca zdalna wymaga własnego mieszkania — najpierw się wprowadź.')
  if era<2:raise RuleError('Przepustka na pracę zdalną na PC otwiera się w Erze II (Rozwój Przemysłu) — po 7 dniach życia świata.')
  if not veteran:raise RuleError('Zlecenia specjalne na PC odblokowują się po 7 dniach — liczy się wiek postaci albo świata.')
  if any(t.get('contract')=='remote' for t in s['contracts']):raise RuleError('Zlecenie specjalne już trwa — odbierz je zanim przyjmiesz następne.')
  if len(s['contracts'])>=4:raise RuleError('Kolejka zleceń jest pełna.')
  spend(s,energy=REMOTE_JOB['energy']);start=max([now]+[t['end'] for t in s['contracts']]);s['sequence']+=1
  s['contracts'].append(dict(id=s['sequence'],contract='remote',tender=True,cash=REMOTE_JOB['cash'],start=start,end=start+round(REMOTE_JOB['duration']/speed),ev=ev_snapshot(now)));message='Praca zdalna w kolejce — komputer w domu pracuje za Ciebie.'
 elif kind=='rest_start':
  r=next((r for r in RESTS if r['id']==p.get('rest')),None)
  if not r:raise RuleError('Nieznany odpoczynek.')
  res=residence_of(s);tier=RESIDENCES.index(res)+1 if res else 0
  if tier<r['tier']:raise RuleError('Ten odpoczynek wymaga lepszej rezydencji.')
  old=s.get('rest')
  if old and old['end']>now:raise RuleError('Odpoczynek już trwa.')
  if old and old['end']<=now:
   missed=min(old['gain'],max(0,energy_max(s)-s['energy']));s['energy']+=missed;s['rest']=None
   if missed<old['gain']:log(s,'Nieodebrany odpoczynek przepadł — pasek energii był pełny.',now)
  gain=round(r['energy']*(1+(res['restBonus'] if res else 0)/100))
  end=now+round(r['duration']/speed)
  if s.get('restInstant',0)>0:  # 0.14 starter pack charge: this rest finishes immediately
   s['restInstant']-=1;end=now;message='Odpoczynek rozpoczęty i natychmiast ukończony (pakiet startowy). '
  s['rest']=dict(id=r['id'],start=now,end=end,gain=gain)
  if not message:message='Odpoczynek rozpoczęty: '+r['name']+'.'
  else:message+='Odpoczynek rozpoczęty: '+r['name']+'.'
 elif kind=='buy_vehicle':
  g=next((g for g in GARAGE if g['id']==p.get('vehicle')),None)
  if not g:raise RuleError('Nieznany pojazd.')
  if g['id'] in s['garage']:raise RuleError('Ten pojazd już stoi w garażu.')
  if level(s['xp'])<g['level']:raise RuleError('Ten pojazd wymaga poziomu '+str(g['level'])+'.')
  if not g.get('buyable',True):raise RuleError('Tego auta nie da się kupić — to nagroda za 7 dni gry.')  # 3.1
  res=residence_of(s);cap=((1+res['slots']) if res else 1)+over(s,3)//20  # 0.35: Charyzma = sąsiedzi pozwalają parkować (+1 miejsce / 20 pkt)
  if len([v for v in s['garage'] if not car(v).get('bonus')])>=cap:raise RuleError('Brak miejsca parkingowego — '+((res['name']+' mieści '+(str(res['slots']) if res['slots'] else 'nic')+' poza autem w użyciu.') if res else 'własne M z parkingiem pozwoli trzymać więcej aut.'))
  spend(s,cash=g['price']);s['garage'].append(g['id'])
  set_wear(s,g['id'],0)
  if not s.get('vehicle'):s['vehicle']=dict(id=g['id'],wear=0)
  message='Zakupiono: '+g['name']+'.'
 elif kind=='equip_vehicle':
  g=next((g for g in GARAGE if g['id']==p.get('vehicle')),None)
  if not g or g['id'] not in s['garage']:raise RuleError('Nie posiadasz tego pojazdu.')
  s['vehicle']=dict(id=g['id'],wear=int(wear_of(s,g['id'])))  # 3.3: każde auto ma własne zużycie (zmiana auta go nie zeruje)
  message='Wyjeżdżasz: '+g['name']+'.'
 elif kind=='upgrade_vehicle':
  g=next((g for g in GARAGE if g['id']==p.get('vehicle')),None)
  if not g or g['id'] not in s['garage']:raise RuleError('Kup najpierw ten pojazd.')
  lvl=int(s.get('garageUp',{}).get(g['id'],0))
  if lvl>=GARAGE_UP_MAX:raise RuleError(g['name']+' ma już maksymalny poziom ulepszeń.')
  cost=garage_up_cost(g,lvl)
  if s['cash']<cost:raise RuleError('Ulepszenie kosztuje '+str(cost)+' $ — brakuje gotówki.')
  spend(s,cash=cost);s.setdefault('garageUp',{})[g['id']]=lvl+1
  message=g['name']+': ulepszenie poziom '+str(lvl+1)+' — rabat czasu '+str(g['discount']+garage_up_bonus(lvl+1))+'%.'
 elif kind=='service_vehicle':
  # 3.3 GDD v3.1: serwis jednego auta (domyślnie aktywnego); koszt z cennika × zniżka sojuszu
  v=s.get('vehicle')
  vid=p.get('vehicle') or (v or {}).get('id')
  if not vid:raise RuleError('Nie masz wybranego pojazdu.')
  if p.get('vehicle') and vid not in s['garage']:raise RuleError('Tego auta nie ma w Garażu.')
  g=next((g for g in GARAGE if g['id']==vid),None)
  if g is None:
   # 1.2 GDD v3.1: model wycofany z katalogu — odstawiamy auto z użycia bez opłaty (bez błędu 500).
   # Garaż gracza zostaje nietknięty; rekompensata za wycofane modele w migracji zadania 3.1.
   s['vehicle']=None;message='Ten model auta został wycofany z gry — odstawiono go z użycia. Wybierz inne auto w Garażu.';log(s,message,now)
  else:
   if wear_of(s,vid)<=0:raise RuleError('Pojazd jeszcze nie wymaga serwisu.')
   spend(s,cash=round(g['service']*ally_mult(s,'cheap_repair')));set_wear(s,vid,0);message='Serwis zakończony. '+g['name']+' jak nowy.'
 elif kind=='auto_mechanic':
  # 3.3 GDD v3.1: Automatyczny Mechanik — wszystkie auta do 0% naraz; 2000 $ (VIP 1000 $)
  todo=[x for x in s['garage'] if wear_of(s,x)>0]
  if not todo:raise RuleError('Wszystkie auta są sprawne — mechanik nie ma co robić.')
  cost=AUTO_MECHANIC_COST//2 if vip else AUTO_MECHANIC_COST
  if s['cash']<cost:raise RuleError('Automatyczny Mechanik kosztuje '+str(cost)+' $ — brakuje gotówki.')
  spend(s,cash=cost)
  for x in todo:set_wear(s,x,0)
  message='🔧 Automatyczny Mechanik: '+str(len(todo))+' aut(a) jak nowe za '+str(cost)+' $'+(' (VIP −50%)' if vip else '')+'.'
 elif kind=='refuel':
  # 3.2 GDD v3.1: tankowanie za gotówkę (VIP −20%); domyślnie do pełna
  vid=p.get('vehicle') or ''
  if vid not in s['garage']:raise RuleError('Tego auta nie ma w Garażu.')
  if traveling:raise RuleError('Jesteś w drodze — zatankujesz po przyjeździe.')
  if vid in (s.get('npcCars') or {}):raise RuleError('To auto jest na zmianie z NPC — zatankujesz po jego powrocie.')
  have=fuel_of(s,vid);room=round(100-have,2)
  if room<=0:raise RuleError('Bak jest pełny.')
  try:pct=room if p.get('amount') in (None,'') else min(room,float(p.get('amount')))
  except (TypeError,ValueError):raise RuleError('Nieprawidłowa ilość paliwa.')
  if pct<=0:raise RuleError('Nieprawidłowa ilość paliwa.')
  cost=refuel_cost(s,vid,pct,now,vip)
  if s['cash']<cost:raise RuleError('Tankowanie kosztuje '+str(cost)+' $ — brakuje gotówki.')
  spend(s,cash=cost);set_fuel(s,vid,have+pct)
  message='⛽ '+car(vid)['name']+': +'+str(round(pct))+'% paliwa za '+str(cost)+' $'+(' (VIP −20%)' if vip else '')+'.'
 elif kind=='hire_staff':
  key=p.get('staff');offer=STAFF.get(key)
  if not offer:raise RuleError('Nieznane stanowisko.')
  b=s['business'] if key=='courier' else (s['buildings'].get(key,0) if key in BUILDING_VAULTS else s['ventures'].get(key))  # 4.2: Barista pracuje w budynku Kawiarnia
  if not b:raise RuleError('Najpierw kup '+offer['business']+'.')
  if s['staff'].get(key,0)>now:raise RuleError('To stanowisko jest już obsadzone.')
  spend(s,cash=offer['cost']);s['staff'][key]=now+round(offer['hours']*HOUR/speed)
  message=offer['name']+' zaczyna pracę. +'+str(offer['boost'])+'% dochodu na '+str(offer['hours'])+' h.'
 elif kind=='tender_accept':
  if s.get('tenderDone')==day_of(now):raise RuleError('Dzisiejszy przetarg został już przyjęty.')
  t=daily_tender(wid,cid,day_of(now))
  if now>=t['expires_at']:raise RuleError('Przetarg na dziś wygasł.')
  if level(s['xp'])<t['level']:raise RuleError('Ten przetarg wymaga poziomu '+str(t['level'])+'.')
  if len(s['contracts'])>=4:raise RuleError('Kolejka kontraktów jest pełna.')
  spend(s,energy=t['energy']);start=max([now]+[x['end'] for x in s['contracts']]);s['sequence']+=1
  s['contracts'].append(dict(id=s['sequence'],contract=t['contract'],start=start,end=start+round(t['duration']/speed),cash=t['cash'],tender=True,ev=ev_snapshot(now)))
  s['tenderDone']=day_of(now);message='Przetarg przyjęty: '+t['name']+' za '+str(t['cash'])+' $.'
 elif kind=='invest':
  district=p.get('district');amount=p.get('amount')
  if district not in DISTRICTS:raise RuleError('Nieznana dzielnica.')
  if type(amount)!=int or not 100<=amount<=5000:raise RuleError('Jednorazowo można zainwestować 100–5000 $.')
  if INVEST_CAP and s['invested'].get(district,0)+amount>INVEST_CAP:raise RuleError('Limit inwestycji w dzielnicy to '+str(INVEST_CAP)+' $.')
  spend(s,cash=amount);s['invested'][district]=s['invested'].get(district,0)+amount
  message='Zainwestowano '+str(amount)+' $ w dzielnicę '+district+'.'
  log(s,message,now)
 elif kind=='rest_claim':
  old=s.get('rest')
  if not old:raise RuleError('Nie masz zaplanowanego odpoczynku.')
  if old['end']>now:raise RuleError('Odpoczynek jeszcze trwa.')
  gain=min(old['gain'],max(0,energy_max(s)-s['energy']));s['energy']+=gain;s['rest']=None
  s['completed']['rests']=s['completed'].get('rests',0)+1
  message='Wypoczęty. +'+str(int(gain))+' energii.'+((' Część przepadła — pasek był pełny.') if gain<old['gain'] else '')
 elif kind=='route_dispatch':
  # 2.4e GDD v3.1: stare trasy NPC wycofane — zarobek auto-pilota przejął system usług (npc.py). Odbiór trwających tras działa.
  raise RuleError(ROUTES_RETIRED)
 elif kind=='route_claim':
  runs=s['npcRoutes']['runs'];ready=[x for x in runs if x.get('end',0)<=now]
  if not ready:raise RuleError('Żadna trasa nie jest jeszcze gotowa — kierowcy w drodze.')
  cash=0;xp=0
  lost=0  # 1.1 GDD v3.1: trasy usunięte z katalogu (brak definicji w NPC_ROUTES)
  for x in ready:
   r=next((y for y in NPC_ROUTES if y['id']==x.get('route')),None)
   if r is None:
    # Trasa zniknęła z katalogu: bez wypłaty, auto wraca do garażu (zwolnienie przebiegu), wpis do dziennika
    lost+=1;log(s,'Trasa „'+str(x.get('route'))+'” nie istnieje już w katalogu — auto wróciło do garażu bez wypłaty.',now)
    continue
   cash+=round(route_payout(s,r['cash'],x.get('vehicle'))*ev_frozen(x,'route_cash'));xp+=r['xp']
  s['npcRoutes']['runs']=[x for x in runs if x.get('end',0)>now]
  nr=s['npcRoutes'];nr['done']=nr.get('done',0)+len(ready)-lost;nr['cash']=nr.get('cash',0)+cash;nr['xp']=nr.get('xp',0)+xp
  s['cash']+=cash;s['xp']+=xp
  message='🏁 Trasy zakończone ('+str(len(ready))+'): +'+str(cash)+' $ i +'+str(xp)+' XP.'
  if lost:message+=' Uwaga: '+str(lost)+' tras(y) wycofano z gry — auta wróciły do garażu.'
 else:raise RuleError('Nieobsługiwana operacja.')
 s['lastAction']=now
 return message

# --- 0.23 Dystynkcja dnia: raz na dobę UTC, czysto kosmetyczny zaszczyt za zapracowany czyn. ---
DAY_MS=24*HOUR
MARKS={'contract':'Kontrakt dnia','training':'Trening dnia','collect':'Dochód dnia','fund':'Wsparcie organizacji','invest':'Inwestycja dzielnicowa','remote':'Praca na PC dnia','rest':'Wypoczynek dnia'}


def day_start(ms):return ms//DAY_MS*DAY_MS


def mark_daily(c,cid,kind,ts):
 # wywoływane w transakcji czynu: dziś coś udało się zrobić → najnowszy czyn dnia zostaje w znaku
 c.execute('INSERT INTO daily_actions(character_id,day,kind,updated_at) VALUES(?,?,?,?) ON CONFLICT(character_id,day) DO UPDATE SET kind=excluded.kind,updated_at=excluded.updated_at',(cid,day_start(ts),kind,ts))


def distinction_state(c,cid,ts):
 day=day_start(ts)
 d=c.execute('SELECT kind FROM daily_actions WHERE character_id=? AND day=?',(cid,day)).fetchone()
 q=c.execute('SELECT kind,created_at FROM daily_distinctions WHERE character_id=? AND day=?',(cid,day)).fetchone()
 count=c.execute('SELECT count(*) FROM daily_distinctions WHERE character_id=?',(cid,)).fetchone()[0]
 return dict(eligible=bool(d and not q),claimed=dict(kind=q['kind'],at=q['created_at']) if q else None,pending=dict(kind=d['kind']) if d else None,count=count)


# --- 0.24 Ekonomia w liczbach: dzienne agregaty czynów (additive, liczone w transakcjach czynów). ---
def bump(c,wid,cid,ts,deeds=0,cash=0,xp=0,cents=0):
 day=day_start(ts)
 if wid and (deeds or cash or xp or cents):
  c.execute('INSERT INTO world_daily(world_id,day,deeds,cash,xp,shop_cents) VALUES(?,?,?,?,?,?) ON CONFLICT(world_id,day) DO UPDATE SET deeds=deeds+excluded.deeds,cash=cash+excluded.cash,xp=xp+excluded.xp,shop_cents=shop_cents+excluded.shop_cents',(wid,day,deeds,cash,xp,cents))
 if cid and (deeds or cash or xp):
  c.execute('INSERT INTO char_daily(character_id,day,deeds,cash,xp) VALUES(?,?,?,?,?) ON CONFLICT(character_id,day) DO UPDATE SET deeds=deeds+excluded.deeds,cash=cash+excluded.cash,xp=xp+excluded.xp',(cid,day,deeds,cash,xp))
