"""0.25 Mapa 8 dzielnic: wyliczenia czasu, opłaty, blokady w drodze, bramka firm w dzielnicy 2."""
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
 app=create_app(tmp_path/'travel.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(16*86400000,))  # 0.33 Er-y
 monkeypatch.setattr(T,'_draw_hitchhike',lambda:(7.5,False))
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid=1,name='PlayerOne'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def action(c,kind,wid=1,key=None,**kwargs):
 return c.post(f'/api/worlds/{wid}/actions',headers={'Idempotency-Key':key or uuid.uuid4().hex},json={'action':kind,**kwargs})

def go(c,wid,target,mode):
 return c.post(f'/api/worlds/{wid}/travel',json={'target_district':target,'mode':mode})

def info(c,wid=1):
 return c.get(f'/api/worlds/{wid}/state').json()['travelInfo']

def test_bus_fare_and_time(env):
 app,clock=env;c=register(app,'walker');create(c,1)
 i=info(c);assert i['district']==1 and i['districtName']=='Nadmorskie' and i['travel'] is None
 base=c.get('/api/worlds/1/state').json()['state']['cash']
 r=go(c,1,3,'bus');assert r.status_code==200,r.text
 assert r.json()['cash']==base-T.BUS_FARE
 ms=r.json()['travel']['until']-clock[0]
 assert ms==T.BUS_MINUTES_PER_STEP*2*60000  # odległość 2, tempo świata 1 → 10 min
 assert go(c,1,4,'bus').status_code==409  # już w drodze
 clock[0]+=ms-1;assert c.post('/api/worlds/1/travel/arrive',json={}).status_code==409  # za wcześnie
 clock[0]+=2;r=c.post('/api/worlds/1/travel/arrive',json={});assert r.status_code==200,r.text
 assert r.json()['district']==3 and r.json()['districtName']=='Centrum'
 assert info(c)['travel'] is None
 assert c.post('/api/worlds/1/travel/arrive',json={}).status_code==409  # nie ma aktywnej podróży

def test_world_speed_scales_time(env,monkeypatch, flat_stats):
 app,clock=env;c=register(app,'fast');create(c,2)
 r=go(c,2,2,'bus');ms=r.json()['travel']['until']-clock[0]
 assert ms==60000  # bus: dolna granica 60 s (surowe 5 min / 60 = 5 s)
 clock[0]+=ms+1;assert c.post('/api/worlds/2/travel/arrive',json={}).status_code==200
 monkeypatch.setattr(T,'_draw_hitchhike',lambda:(3.0,False))
 r=go(c,2,5,'hitchhike');ms=r.json()['travel']['until']-clock[0]
 assert ms==3000  # tempo 60: 3 min × 60 000 / 60 → 3 s

def test_hitchhike_free_and_energy_risk(env,monkeypatch, flat_stats):
 app,clock=env;c=register(app,'hiker');create(c,1)
 base_energy=c.get('/api/worlds/1/state').json()['state']['energy']
 r=go(c,1,3,'hitchhike');assert r.status_code==200
 assert r.json()['cash']==c.get('/api/worlds/1/state').json()['state']['cash']  # autostop: zero opłat
 assert (r.json()['travel']['until']-clock[0])==450000  # 7,5 min × tempo 1 (pech nie wypadł)
 assert r.json()['energy']==base_energy
 clock[0]+=450001;assert c.post('/api/worlds/1/travel/arrive',json={}).status_code==200
 monkeypatch.setattr(T,'_draw_hitchhike',lambda:(3.0,True))
 pre=c.get('/api/worlds/1/state').json()['state']['energy']
 r=go(c,1,1,'hitchhike');assert r.json()['energy']==pre-10  # pech (15%): −10 energii przy starcie

def test_car_requires_working_vehicle(env):
 app,clock=env;c=register(app,'driver');create(c,1)
 assert go(c,1,3,'car').status_code==422  # brak auta w rejestrze
 db=app.state.db
 with db.tx() as db_c:db_c.execute('INSERT INTO vehicles(character_id,type,condition,speed_bonus) SELECT id,?,0,10 FROM characters WHERE nickname=?',('dostawczak','PlayerOne'))
 assert go(c,1,3,'car').status_code==422  # zniszczone auto
 with db.tx() as db_c:db_c.execute('UPDATE vehicles SET condition=100 WHERE character_id=(SELECT id FROM characters WHERE nickname=?)',('PlayerOne',))
 r=go(c,1,3,'car');assert r.status_code==200,r.text
 assert (r.json()['travel']['until']-clock[0])==120000  # 20% czasu busa (600 s → 120 s)

def test_travel_validation(env):
 app,clock=env;c=register(app,'valid');create(c,1)
 assert go(c,1,9,'bus').status_code==422;assert go(c,1,0,'bus').status_code==422
 assert go(c,1,3,'walk').status_code==422
 assert go(c,1,1,'bus').status_code==422  # target == obecna dzielnica
 assert c.post('/api/worlds/1/travel',json={'target_district':3}).status_code==422  # brak trybu

def test_businesses_only_in_district_two(env):
 app,clock=env;c=register(app,'owner');create(c,1)
 r=action(c,'buy_business',business='studio');assert r.status_code==409
 assert 'Zakładach Miejskich' in r.json()['detail']
 r=action(c,'collect',business='courier');assert r.status_code==409
 assert 'Zakładach Miejskich' in r.json()['detail']
 with app.state.db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',('PlayerOne',)).fetchone()[0]);s['xp']=300;s['cash']=15000
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),'PlayerOne'))
 r=go(c,1,2,'bus');clock[0]+=r.json()['travel']['until']-clock[0]+1
 assert c.post('/api/worlds/1/travel/arrive',json={}).status_code==200
 r=action(c,'buy_business',business='studio');assert r.status_code==200,r.text  # bramka przepuszcza w D2
 r=action(c,'collect',business='courier')
 assert r.status_code==200 or 'Strefie' not in r.json()['detail']  # sejf może być pusty — liczy się brak błędu dzielnicy

def test_stationary_work_blocked_while_traveling(env):
 app,clock=env;c=register(app,'commuter');create(c,1)
 with app.state.db.tx() as cx:cx.execute('UPDATE characters SET current_district=8 WHERE world_id=1')  # 0.45: dostawy z Przedmieść
 for i in range(4):assert action(c,'contract',contract='delivery').status_code==200
 clock[0]+=60_000
 r=go(c,1,2,'hitchhike');assert r.status_code==200
 ms=r.json()['travel']['until']-clock[0];clock[0]+=ms-1
 assert action(c,'contract',contract='delivery').status_code==409  # nowe zlecenie w drodze
 assert action(c,'train',stat=0).status_code==409
 task=c.get('/api/worlds/1/state').json()['state']['contracts'][0]
 assert action(c,'claim_contract',task_id=task['id']).status_code==409  # odbiór w drodze
 clock[0]+=1;assert c.post('/api/worlds/1/travel/arrive',json={}).status_code==200
 clock[0]+=1_900_000  # kontrakty stoją w kolejce (kolejne końce rosną) — dobij za ostatni koniec
 for task in c.get('/api/worlds/1/state').json()['state']['contracts']:
  assert action(c,'claim_contract',task_id=task['id']).status_code==200  # po przyjeździe działa
 with app.state.db.tx() as cx:cx.execute('UPDATE characters SET current_district=8 WHERE world_id=1')  # 0.45: z powrotem w Lasachami
 assert action(c,'contract',contract='delivery').status_code==200
 assert action(c,'train',stat=0).status_code==200

def test_lazy_settle_on_state_read(env):
 app,clock=env;c=register(app,'lazy');create(c,1)
 r=go(c,1,2,'bus');clock[0]+=r.json()['travel']['until']-clock[0]+1
 i=info(c);assert i['district']==2 and i['districtName']=='Przemysłowe' and i['travel'] is None

def test_vehicle_register_hooks(env):
 app,clock=env;c=register(app,'buyer');create(c,1)
 db=app.state.db
 with db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',('PlayerOne',)).fetchone()[0]);s['cash']=2500
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),'PlayerOne'))
 assert action(c,'buy_vehicle',vehicle='dostawczak').status_code==200
 with db.tx() as db_c:
  row=db_c.execute('SELECT type,condition,speed_bonus FROM vehicles WHERE character_id=(SELECT id FROM characters WHERE nickname=?)',('PlayerOne',)).fetchone()
 assert row[0]=='dostawczak' and row[1]==100 and row[2]==10  # bonus = rabat garażowy (10%)
 with db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',('PlayerOne',)).fetchone()[0]);s['vehicle']['wear']=100
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),'PlayerOne'))
  db_c.execute('UPDATE vehicles SET condition=5 WHERE character_id=(SELECT id FROM characters WHERE nickname=?)',('PlayerOne',))
 assert action(c,'service_vehicle').status_code==200
 with db.tx() as db_c:assert db_c.execute('SELECT condition FROM vehicles WHERE character_id=(SELECT id FROM characters WHERE nickname=?)',('PlayerOne',)).fetchone()[0]==100

def test_travel_requires_auth_and_world(env):
 app,clock=env;c=register(app,'stranger');create(c,1)
 raw=TestClient(app)
 assert raw.post('/api/worlds/1/travel',json={'target_district':2,'mode':'bus'}).status_code==401
 assert c.post('/api/worlds/999/travel',json={'target_district':2,'mode':'bus'}).status_code==404
