"""0.26 Rezydencja 2.0: brama 7 dni dla pracy zdalnej (wiek postaci ALBO świata),
miejsca parkingowe garażu, trening domowy, regeneracja i dystynkcje (praca na PC, wypoczynek)."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.economy as E
import server.travel as T

@pytest.fixture
def env(tmp_path, monkeypatch):
 clock=[1780000000000]
 app=create_app(tmp_path/'residence.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 monkeypatch.setattr(T,'_draw_hitchhike',lambda:(7.5,False))
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid=2,name='Mieszkaniec'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def action(c,kind,wid=2,key=None,**kwargs):
 return c.post(f'/api/worlds/{wid}/actions',headers={'Idempotency-Key':key or uuid.uuid4().hex},json={'action':kind,**kwargs})

def state(c,wid=2):
 return c.get(f'/api/worlds/{wid}/state').json()

def login(app,name):
 c=TestClient(app)
 r=c.post('/api/auth/login',json={'username':name,'password':'test-password-long-123'})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def grant(app,nick,cash=None,xp=None,energy=None,at=None,vehicle=None):
 with app.state.db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])
  if cash is not None:s['cash']=cash
  if xp is not None:s['xp']=xp
  if energy is not None:
   s['energy']=energy;s['lastTick']=at if at is not None else s.get('lastTick')
  if vehicle is not None:s['vehicle']=vehicle
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def last_deed(app):
 with app.state.db.read() as db_c:
  row=db_c.execute('SELECT kind FROM daily_actions ORDER BY updated_at DESC LIMIT 1').fetchone()
 return row[0] if row else None

def test_remote_work_gate_seven_days(env):
 app,clock=env;c=register(app,'newcomer');create(c,2)
 assert action(c,'remote_work').status_code==409 and 'mieszkania' in action(c,'remote_work').json()['detail']
 assert action(c,'buy_residence',residence='studio-flat').status_code==200
 r=action(c,'remote_work');assert r.status_code==409 and '7 dni' in r.json()['detail']
 clock[0]+=7*E.DAY_MS+1  # postać ma już tydzień — brama otwiera się (skok zegara = nowa sesja)
 c=login(app,'newcomer')
 assert action(c,'remote_work').status_code==200
 # Ścieżka „albo świat”: świeża postać w tym samym starym świecie też ma dostęp.
 c2=register(app,'second');create(c2,2,name='Nowy Sąsiad')
 assert action(c2,'buy_residence',residence='studio-flat').status_code==200
 assert action(c2,'remote_work').status_code==200

def test_remote_work_flow_and_distinction(env, flat_stats):
 app,clock=env;c=register(app,'remote');create(c,2)
 clock[0]+=8*E.DAY_MS  # świat ma ponad tydzień — brama otwarta dla każdej postaci
 c=login(app,'remote')
 assert action(c,'buy_residence',residence='studio-flat').status_code==200
 grant(app,'Mieszkaniec',vehicle=dict(id='dostawczak',wear=50))
 e0=state(c)['state']['energy']
 r=action(c,'remote_work');assert r.status_code==200,r.text
 s=state(c)['state'];task=[t for t in s['contracts'] if t['contract']=='remote']
 assert len(task)==1 and s['cash']==1800 and abs(s['energy']-(e0-10))<1  # start: bez opłaty, −10 energii
 assert action(c,'remote_work').status_code==409  # zlecenie specjalne już trwa
 assert action(c,'claim_contract',task_id=task[0]['id']).status_code==409  # za wcześnie
 clock[0]+=15001  # 15 min w tempie świata 60 → 15 s
 r=action(c,'claim_contract',task_id=task[0]['id']);assert r.status_code==200,r.text
 s=state(c)['state'];assert s['cash']==1950 and s['xp']==25  # stała stawka 150 $ + 25 XP, bez przelicznika cen
 assert s['vehicle']['wear']==50  # praca zdalna nie zużywa auta
 assert last_deed(app)=='remote'
 d=state(c)['distinction'];assert d['eligible'] and d['pending']['kind']=='remote'
 r=c.post('/api/worlds/2/distinction/claim',json={});assert r.status_code==200 and 'Praca na PC' in r.json()['label']
 cid=state(c)['character']['id']
 with app.state.db.read() as db_c:  # tylko odczyt — żądania HTTP nigdy wewnątrz tx()
  row=db_c.execute('SELECT deeds,cash FROM char_daily WHERE character_id=?',(cid,)).fetchone()
 assert row[0]>=1 and row[1]==150
 # W drodze pracy zdalnej nie rozpoczniesz — to praca stacjonarna.
 r=c.post('/api/worlds/2/travel',json={'target_district':3,'mode':'hitchhike'});assert r.status_code==200
 assert action(c,'remote_work').status_code==409 and 'w drodze' in action(c,'remote_work').json()['detail']

def test_home_training(env):
 app,clock=env;c=register(app,'home');create(c,2)
 assert action(c,'home_train',stat=0).status_code==409  # brak mieszkania
 assert action(c,'buy_residence',residence='studio-flat').status_code==200
 base=state(c)['state']['cash'];e0=state(c)['state']['energy']
 r=action(c,'home_train',stat=0);assert r.status_code==200,r.text
 s=state(c)['state']
 assert s['cash']==base and abs(s['energy']-(e0-12))<1  # koszt wyłącznie energii (−12), zero trenerskich
 assert len(s['training'])==1
 clock[0]+=10001  # 10 min / tempo 60 → 10 s
 r=action(c,'claim_training',task_id=s['training'][0]['id']);assert r.status_code==200,r.text
 s=state(c)['state'];assert s['stats'][0]==11 and s['completed']['training']==1
 assert last_deed(app)=='training'
 for i in range(4):assert action(c,'home_train',stat=1).status_code==200
 assert action(c,'home_train',stat=1).status_code==409  # kolejka (4) pełna

def test_parking_slots(env):
 app,clock=env
 with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(16*86400000,))  # 3.1: bez bramki Ery III
 app,clock=env;c=register(app,'driver');create(c,2)
 grant(app,'Mieszkaniec',cash=70000,xp=1500)  # poziom 6; 3.1: Van 15 000 $ + rezydencje
 assert action(c,'buy_vehicle',vehicle='dostawczak').status_code==200
 r=action(c,'buy_vehicle',vehicle='sedan');assert r.status_code==409 and 'parkingowego' in r.json()['detail']
 assert action(c,'buy_residence',residence='studio-flat').status_code==200  # 0 miejsc: nadal tylko auto w użyciu
 assert action(c,'buy_vehicle',vehicle='sedan').status_code==409
 assert action(c,'buy_residence',residence='center-apartment').status_code==200  # 1 miejsce parkingowe
 assert action(c,'buy_vehicle',vehicle='sedan').status_code==200
 assert action(c,'buy_vehicle',vehicle='van').status_code==409
 assert action(c,'buy_residence',residence='green-villa').status_code==200  # garaż na 3 auta
 assert action(c,'buy_vehicle',vehicle='van').status_code==200
 s=state(c)['state'];assert sorted(s['garage'])==['dostawczak','sedan','van']
 assert action(c,'equip_vehicle',vehicle='dostawczak').status_code==200  # zamiana miejsc nie wymaga dodatkowego parkingu
 assert action(c,'buy_vehicle',vehicle='van').status_code==409  # duplikat nadal złapany

def test_regeneration_and_rest_distinction(env):
 app,clock=env;c=register(app,'sleeper');create(c,1)  # świat 1, tempo 1 — regeneracja co do liczby
 assert action(c,'rest_start',1,rest='nap').status_code==409  # odpoczynek wymaga rezydencji
 grant(app,'Mieszkaniec',cash=50000)
 assert action(c,'buy_residence',1,residence='studio-flat').status_code==200
 grant(app,'Mieszkaniec',energy=120,at=clock[0])
 clock[0]+=E.HOUR
 e=state(c,1)['state']['energy'];assert abs(e-132)<0.01  # 10 bazowa + 2 z kawalerki = 12/h
 assert action(c,'rest_start',1,rest='spa').status_code==409  # spa wymaga progu 3
 assert action(c,'rest_start',1,rest='nap').status_code==200
 assert action(c,'rest_claim',1).status_code==409  # drzemka jeszcze trwa
 clock[0]+=20*E.MINUTE+1
 r=action(c,'rest_claim',1);assert r.status_code==200,r.text
 assert last_deed(app)=='rest'
 d=state(c,1)['distinction'];assert d['eligible'] and d['pending']['kind']=='rest'
 # Willa: maksymalny bonus — spa 160 × 1,25 = 200 energii.
 c2=register(app,'rich');create(c2,1,name='Właściciel Willli')
 grant(app,'Właściciel Willli',cash=50000,xp=1500)
 assert action(c2,'buy_residence',1,residence='green-villa').status_code==200
 grant(app,'Właściciel Willli',energy=30,at=clock[0])
 assert action(c2,'rest_start',1,rest='spa').status_code==200
 assert state(c2,1)['state']['rest']['gain']==200  # 160 × 1,25 — maksymalny bonus rezydencji
 clock[0]+=8*E.HOUR+1
 assert action(c2,'rest_claim',1).status_code==200  # regen bierny w oknie odpoczynku domyka pasek
 assert state(c2,1)['state']['rest'] is None

def test_residence_catalog_carries_slots(env):
 app,clock=env;c=register(app,'reader');create(c,2)
 cat=state(c)['catalog']['residences']
 slots={r['id']:r['slots'] for r in cat}
 assert slots=={'studio-flat':0,'center-apartment':1,'green-villa':3}
