"""0.33 System Er Świata: 28-dniowy cykl żywotności świata od created_at.

Era I (1-7) Czas Pionierów: dzielnice 1-3, firmy do poziomu 2.
Era II (8-14) Rozwój Przemysłu: dzielnice 4-5, przepustka na pracę PC.
Era III (15-21) Wielki Biznes: dzielnice 6-7, pojazdy premium.
Era IV (22-28+) Metropolia & Epilog: dzielnica 8. Testy: blokady podróży,
rozwój firm, automatyczne przejścia zegara (kolumna world_era + kronika)."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app

DAY=86400000

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'eras.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 def age(days):
  with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(days*DAY,))
 def clock_fwd(ms):clock[0]+=ms
 return app,clock,age,clock_fwd

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def era(c):
 return c.get('/api/worlds/2/state').json()['era']

def world_era_col(app):
 with app.state.db.read() as c:
  return c.execute('SELECT world_era FROM worlds WHERE id=2').fetchone()[0]

def chronicle_kinds(app):
 with app.state.db.read() as c:
  return [r['kind'] for r in c.execute("SELECT kind FROM chronicle WHERE world_id=2 AND kind='era'")]

def travel(c,target,mode='bus'):
 return c.post('/api/worlds/2/travel',json={'target_district':target,'mode':mode})

def finish(c,clock,ms=None):
 r=c.post('/api/worlds/2/travel/arrive',json={})
 if r.status_code==409 and 'Jeszcze w drodze' in r.json().get('detail',''):
  clock[0]+=7*3600000  # dalekie dzielnice: maks. kilka minut/dzielnicę — godzina wystarcza
  r=c.post('/api/worlds/2/travel/arrive',json={})
 assert r.status_code==200,r.text

def act(c,**payload):
 return c.post('/api/worlds/2/actions',headers={'Idempotency-Key':uuid.uuid4().hex},json=payload)

def test_era_schedule_and_automatic_transitions(env):
 app,clock,age,fwd=env
 a=register(app,'kronikarz')
 a.post('/api/worlds/2/character',json={'nickname':'Kronikarz','accept_test_reset':True})
 e=era(a)
 assert (e['n'],e['label'],e['day'],e['total'])==(1,'Czas Pionierów',1,28)
 assert e['districts']==3 and e['business']==2 and e['pc'] is False and e['premium'] is False
 age(6)
 e=era(a);assert (e['n'],e['day'])==(1,7),'dzień 7 to jeszcze Era I'
 age(1)
 e=era(a);assert (e['n'],e['label'],e['day'])==(2,'Rozwój Przemysłu',8),'dzień 8 = Era II'
 assert world_era_col(app)==2 and chronicle_kinds(app)==['era'],'auto-przejście zapisane w kolumnie i Kronice'
 with app.state.db.read() as c:
  row=c.execute("SELECT title FROM chronicle WHERE world_id=2 AND kind='era'").fetchone()
 assert 'Rozwój Przemysłu' in row['title']
 age(7);e=era(a);assert e['n']==3 and e['label']=='Wielki Biznes' and world_era_col(app)==3
 age(7);e=era(a);assert e['n']==4 and e['label']=='Metropolia & Epilog' and e['districts']==8
 assert len(chronicle_kinds(app))==3,'po jednym wpisie na przejście (II, III, IV)'
 age(10)
 e=era(a);assert (e['n'],e['day'],e['final'])==(4,28,True),'po 28 dniu Era IV trwa, licznik dzień/28 stoi'
 assert world_era_col(app)==4

def test_travel_blocked_outside_era_districts(env):
 app,clock,age,fwd=env
 a=register(app,'podroznik');a.post('/api/worlds/2/character',json={'nickname':'Podróżnik','accept_test_reset':True})
 r=travel(a,4)
 assert r.status_code==409 and r.json()['detail']=='Dzielnica niedostępna w obecnej Erze świata.'
 assert travel(a,2).status_code==200,'Przemysłowe (zawsze otwarte) w Erze I dostępne'
 finish(a,clock)
 assert travel(a,7).status_code==200,'0.54.0: Kopalnia (surowce) zawsze otwarta';finish(a,clock)
 assert travel(a,8).status_code==200,'0.54.0: Lasy (surowce) zawsze otwarte';finish(a,clock)
 age(8)  # Era II
 assert travel(a,4).status_code==200 and travel(a,5).status_code==409  # 5 w kolejce? nie: 4 jedziemy, 5 zaraz
 r=travel(a,4);assert r.status_code==409 and 'już w drodze' in r.json()['detail']  # właśnie jesteśmy w drodze do 4
 finish(a,clock)
 assert travel(a,5).status_code==200;finish(a,clock)
 assert travel(a,6).status_code==409 and 'Erze świata' in travel(a,6).json()['detail']
 age(7)  # dzień 15 = Era III
 assert travel(a,6).status_code==200;finish(a,clock)
 age(7)  # dzień 22 = Era IV — miasta otwarte, surowce zawsze były
 assert travel(a,1).status_code==200;finish(a,clock)

def test_business_level_cap_in_era_one(env):
 app,clock,age,fwd=env
 a=register(app,'przedsiebiorca');a.post('/api/worlds/2/character',json={'nickname':'Przedsiębiorca','accept_test_reset':True})
 assert travel(a,2).status_code==200,'Przemysłowe w Erze I dostępne';finish(a,clock)
 assert act(a,action='upgrade',business='courier').status_code==200,'rozbudowa 1→2 dozwolona'
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=json_set(state_json,'$.business.upgrade.end',?) WHERE nickname='Przedsiębiorca'",(clock[0]+1,))
 clock[0]+=2  # business_sync rozlicza w przedziale from_ < end <= now
 r=act(a,action='upgrade',business='courier')
 assert r.status_code==409 and 'poziomu 2' in r.json()['detail'],'cap Ery I: level 2→3 zablokowany'
 age(8)  # Era II
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=json_set(state_json,'$.cash',20000) WHERE nickname='Przedsiębiorca'")
 r=act(a,action='upgrade',business='courier')
 assert r.status_code==200,'Era II otwiera kolejne poziomy firm'
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['business']['upgrade']['target']==3

def test_pc_work_and_premium_vehicle_gates(env):
 app,clock,age,fwd=env
 a=register(app,'zdalniak');a.post('/api/worlds/2/character',json={'nickname':'Zdalniak','accept_test_reset':True})
 assert act(a,action='buy_residence',residence='studio-flat').status_code==200
 age(6)  # dzień 7 (Era I): świat ma 6 dni — brama ery jeszcze zamknięta
 r=act(a,action='remote_work')
 assert r.status_code==409 and 'Erze II' in r.json()['detail'],'przepustka PC to brama ery'
 age(2)  # dzień 9 = Era II
 assert act(a,action='remote_work').status_code==200
 # 3.1 GDD v3.1: bramka Ery III dla aut usunięta — Van (poziom 5) do kupienia już w Erze II
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=json_set(json_set(state_json,'$.cash',20000),'$.xp',1500) WHERE nickname='Zdalniak'")
 assert act(a,action='buy_vehicle',vehicle='van').status_code==200
 st=a.get('/api/worlds/2/state').json()
 assert 'van' in st['state']['garage'] and era(a)['n']==2
