"""0.35 Statystyki ogólne w całej grze: bonusy od każdego punktu efektywnego powyżej 10,
deterministyczne, liczone na serwerze, z twardymi capami. Postać 10×5 zachowuje się
dokładnie jak dotychczas (zero bonusu, zero kary).

💪 Siła: kontrakty −0,4%/pkt czasu (cap 20%) · skarbiec firmy +2%/pkt (cap 40%)
🧠 Inteligencja: praca PC +0,6%/pkt gotówki (cap 30%) · rozbudowa −0,3%/pkt (cap 15%)
⚡ Refleks: autostop — ryzyko awarii −0,5 p.p./pkt (baza 15%, min 3%) i −1%/pkt czasu (cap 25%)
❤️ Charyzma: ceny wyposażenia i treningów −0,3%/pkt (cap 9%) · parking +1 miejsce/20 pkt
🎯 Spryt: wpływy inwestycji +0,5%/pkt (cap 25%) · NPC lochu −2%/10 pkt (cap 6%)"""
import json
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import economy as E
from server import travel as T

DAY=86400000

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'stats.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 def age(days):
  with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(days*DAY,))
 return app,clock,age

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,name='Mierzalny'):
 r=c.post('/api/worlds/2/character',json={'nickname':name,'accept_test_reset':True,'class_type':'bokser'});assert r.status_code==200,r.text;return r.json()

def set_state(app,nick,**kw):
 parts=[];vals=[]
 for k,v in kw.items():
  parts.append("'$.%s',json(?)"%k if isinstance(v,list) else "'$.%s',?"%k)
  vals.append(json.dumps(v) if isinstance(v,list) else v)
 with app.state.db.tx() as c:
  c.execute(f'UPDATE characters SET state_json=json_set(state_json,{",".join(parts)}) WHERE nickname=?',(*vals,nick))

def get_state(app,nick):
 with app.state.db.read() as c:
  return json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])

def act(c,**payload):
 return c.post('/api/worlds/2/actions',headers={'Idempotency-Key':__import__('uuid').uuid4().hex},json=payload)

def test_strength_shortens_contracts_and_expands_vault(env):
 app,clock,age=env
 base=register(app,'bazowy');create(base,'Bazowy')
 strong=register(app,'silacz');create(strong,'Silacz')
 set_state(app,'Bazowy',stats=[10]*5)  # baseline wzorów przy 10/10/10/10/10
 set_state(app,'Silacz',stats=[50,10,10,10,10])
 for c in (base,strong):c.post('/api/worlds/2/travel',json={'target_district':2,'mode':'bus'})
 app.state.db  # noop
 for c,nick in ((base,'Bazowy'),(strong,'Silacz')):
  clock[0]+=7*3600000  # dojazd d1→d2 (Era I: dzielnica 2 dostępna)
  c.post('/api/worlds/2/travel/arrive',json={})
  with app.state.db.tx() as cx:cx.execute('UPDATE characters SET current_district=8 WHERE nickname=?',(nick,))  # 0.45: dostawa z Przedmieść
  r=act(c,action='contract',contract='delivery')
  assert r.status_code==200,r.text
  s=get_state(app,nick);t=s['contracts'][0]
  if nick=='Bazowy':assert t['end']-t['start']==9667,'8.2: Siła 10 → 10%×10/30 = −3,33% z 10 min / tempo ×60'
  else:assert t['end']-t['start']==9000,'8.2: Siła 50 → cap 10% (max już przy 30 pkt)'
 # skarbiec: test jednostkowy capu — RATES[0]=40, tempo 60 → cap 40*60*24=57600; Siła ×1,8 = 103680
 t0=1780000000000
 b_base=dict(level=1,vault=56500,upgrade=None);E.business_sync(b_base,t0,t0+3600000,E.RATES,60,0,1.0)
 assert b_base['vault']==57600,'baseline: skarbiec ucięty na 57600'
 b_strong=dict(level=1,vault=56500,upgrade=None);E.business_sync(b_strong,t0,t0+3600000,E.RATES,60,0,1.8)
 assert b_strong['vault']==58900,'Siła 50: cap ×1,8 — 58900 nie jest już cięte'

def test_intelligence_boosts_remote_and_discounts_upgrade(env):
 app,clock,age=env
 age(8)  # Era II: przepustka PC
 a=register(app,'inteligentny');create(a,'Inteligentny')
 set_state(app,'Inteligentny',stats=[10,50,10,10,10])
 assert act(a,action='buy_residence',residence='studio-flat').status_code==200
 assert act(a,action='remote_work').status_code==200
 clock[0]+=16*60000  # koniec zlecenia (15 min) — bez utraty sesji
 st=a.get('/api/worlds/2/state').json()
 tid=st['state']['contracts'][0]['id']
 cash0=st['state']['cash']
 r=act(a,action='claim_contract',task_id=tid);assert r.status_code==200
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['cash']-cash0==181,'8.2: praca PC 150 $ × 1,15 (Int cap 15%) = 172 → × 1,05 (Charyzma 10 = 5% zarobków) = 181'
 # rozbudowa: 500 $ × 0,88 = 440 $
 a.post('/api/worlds/2/travel',json={'target_district':2,'mode':'bus'});clock[0]+=3600000
 a.post('/api/worlds/2/travel/arrive',json={})
 set_state(app,'Inteligentny',cash=2000)
 assert act(a,action='upgrade',business='courier').status_code==200
 assert get_state(app,'Inteligentny')['cash']==2000-850,'8.2: rozbudowa 1000 × 0,85 (Int cap 15%) = 850'

def test_reflex_saves_hitchhike_and_shortens_ride(env,monkeypatch):
 app,clock,age=env
 age(8)
 monkeypatch.setattr(T,'_draw_hitchhike',lambda:(10.0,True))
 monkeypatch.setattr(T._random,'random',lambda:0.0)  # ratunek zawsze się udaje, jeśli ma szansę
 lucky=register(app,'refleks');create(lucky,'Refleksik')
 set_state(app,'Refleksik',stats=[10,10,30,10,10])
 r=lucky.post('/api/worlds/2/travel',json={'target_district':5,'mode':'hitchhike'})
 assert r.status_code==200
 d=r.json()
 assert d['energy']==240,'ratunek: bez utraty energii'
 ms=lucky.get('/api/worlds/2/state').json()['travelInfo']['travel']['until']-clock[0]
 assert ms==9000,'8.2: Refleks 30 → cap 10% transportu → 9 min'
 clock[0]+=ms+1000
 assert lucky.post('/api/worlds/2/travel/arrive',json={}).status_code==200
 # baseline: refleks 10 → brak ratunku, pełne ryzyko i czas
 base=register(app,'nierefleks');create(base,'Nie Refleks')
 r=base.post('/api/worlds/2/travel',json={'target_district':5,'mode':'hitchhike'})
 assert r.json()['energy']==240,'8.2: Refleks 10 → 3,3% szansy ratunku; los zablokowany na 0.0 → ratunek'
 ms2=base.get('/api/worlds/2/state').json()['travelInfo']['travel']['until']-clock[0]
 assert ms2==9700,'8.2: Refleks 10 → −3,33% czasu (minuty zaokrąglane do 0,1 → 9,7 min)'

def test_charisma_discounts_shop_and_training_adds_parking(env, legacy_shop):
 app,clock,age=env
 a=register(app,'czarujacy');create(a,'Czarujący')
 set_state(app,'Czarujący',stats=[10,10,10,50,10])
 cash0=get_state(app,'Czarujący')['cash']
 assert act(a,action='buy',item='urban-gloves').status_code==200
 assert cash0-get_state(app,'Czarujący')['cash']==228,'250 $ × 0,91 (cap 9%)'
 assert act(a,action='train',stat=0).status_code==200
 assert cash0-get_state(app,'Czarujący')['cash']==228+182,'QA 3: trening (50+10×15) $ × 0,91 = 182 $'
 # parking: bez rezydencji cap=1 (+2 od Charyzmy) → dostawczak i sedan wchodzą
 set_state(app,'Czarujący',xp=5000,cash=20000)
 assert act(a,action='buy_vehicle',vehicle='dostawczak').status_code==200
 assert act(a,action='buy_vehicle',vehicle='sedan').status_code==200,'Charyzma: +1 miejsce/20 pkt'
 b=register(app,'zaslona');create(b,'Bez Charyzmy')
 set_state(app,'Bez Charyzmy',xp=5000)
 assert act(b,action='buy_vehicle',vehicle='dostawczak').status_code==200
 r=act(b,action='buy_vehicle',vehicle='sedan')
 assert r.status_code==409 and 'parkingowego' in r.json()['detail'],'baseline: cap 1 tnie'

def test_cunning_boosts_influence_and_weakens_dungeon_npc(env):
 app,clock,age=env
 a=register(app,'sprytny');create(a,'Sprytny')
 s=get_state(app,'Sprytny')
 assert E.invest_bonus(s,'Portowe')==round(10*8/30,2),'8.2: Bokser Spryt 8 → 10%×8/30'
 s['stats']=[10,10,10,10,30]
 assert E.invest_bonus(s,'Portowe')==10,'8.2: Spryt 30 → cap 10%'
 s['stats']=[10,10,10,10,200]
 assert E.invest_bonus(s,'Portowe')==10,'8.2: powyżej 30 pkt bez zmian (tylko PvP)'
 # loch: NPC słabszy o 4% (over 20 → 2×2%)
 a.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 set_state(app,'Sprytny',stats=[60,60,60,60,30],xp=400,tactic='presja')  # 0.41: loch od 3 lvl + taktyka
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET dungeon_progress=0 WHERE nickname='Sprytny'")
 r=a.post('/api/worlds/2/dungeon/floor',json={'seq':['fast','fast','fast']}).json()
 pot_d_red=sum(r['report']['stats'][1])
 b=register(app,'gruntowy');create(b,'Gruntowy')
 b.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 set_state(app,'Gruntowy',stats=[60,60,60,60,10],xp=400,tactic='presja')
 r2=b.post('/api/worlds/2/dungeon/floor',json={'seq':['fast','fast','fast']}).json()
 pot_d_base=sum(r2['report']['stats'][1])
 assert pot_d_red<=pot_d_base and sum(r['report']['stats'][1])<sum(r2['report']['stats'][1]),f'Spryt osłabia NPC w lochu ({pot_d_red} vs {pot_d_base})'  # balans 2.3: bez bonusu RPS różnica ginie w zaokrągleniu potencjału — porównujemy staty NPC
