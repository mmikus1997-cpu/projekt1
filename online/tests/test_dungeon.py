"""0.31 Lochy: brama-lochow jako wejście, progres 0-100% (dungeon_progress),
piętra z walkami silnikiem PvP vs NPC, nagrody w wirtualnych $ oraz unikatowe
przedmioty dające statystyki (jednorazowe, nie do kupienia). Zero realnej kasy."""
import json
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import economy as E

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 return create_app(tmp_path/'dg.sqlite3',lambda:clock[0],tmp_path/'setup.txt'),clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,name='Grotołaz'):
 r=c.post('/api/worlds/2/character',json={'nickname':name,'accept_test_reset':True,'class_type':'bokser'});assert r.status_code==200,r.text;return r.json()

def _ready(app,nick,xp=400,tactic='kontrola'):
 with app.state.db.tx() as c:
  s=json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])
  s['xp']=xp;s['tactic']=tactic
  c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def fight(c,seq=None):
 return c.post('/api/worlds/2/dungeon/floor',json={'seq':seq or ['fast','dodge','heavy']})

def db_state(app,nick='Grotołaz'):
 with app.state.db.read() as c:
  return json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])

def set_progress(app,progress,nick='Grotołaz'):
 with app.state.db.tx() as c:
  c.execute('UPDATE characters SET dungeon_progress=?,dungeon_normal=? WHERE nickname=?',(progress,progress//10,nick))  # 6.x: stary % (10 pięter) → piętro Normal

def test_payload_gates_and_entry(env):
 app,clock=env
 a=register(app,'groto');create(a)
 st=a.get('/api/worlds/2/state').json()
 dg=st['dungeon']
 assert dg['progress']==0 and dg['atGate'] is False and dg['completed'] is False and dg['nextFloor']['n']==1
 assert fight(a).status_code==409,'bez lokacji brama-lochow wejście zabronione'
 r=a.post('/api/worlds/2/location',json={'location':'brama-lochow'});assert r.status_code==200
 st=a.get('/api/worlds/2/state').json();assert st['dungeon']['atGate'] is True
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET travel_destination=3 WHERE nickname='Grotołaz'")
 assert fight(a).status_code==409,'w drodze nie wejdziesz'
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET travel_destination=NULL WHERE nickname='Grotołaz'")
 bad=a.post('/api/worlds/2/dungeon/floor',json={'seq':['fast']});assert bad.status_code==409,'0.41: loch od 3. poziomu — nieprawidłowa sekwencja jest ignorowana, liczy się bramka poziomu'

def test_win_progress_rewards_and_loot(env):
 app,clock=env
 a=register(app,'heros');create(a);_ready(app,'Grotołaz')
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET current_location='brama-lochow' WHERE nickname='Grotołaz'")
  s=json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Grotołaz'").fetchone()[0])
  s['stats']=[60,60,60,60,60]  # pewna wygrana na piętrze 1
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Grotołaz'",(json.dumps(s),))
 cash0=a.get('/api/worlds/2/state').json()['state']['cash']
 r=fight(a);assert r.status_code==200,r.text
 data=r.json()
 assert data['cleared'] is True and data['floor']==1 and data['progress']==1
 assert data['rewards']==dict(cash=60,xp=12)
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['cash']==cash0+60 and st['dungeon']['progress']==1 and st['dungeon']['nextFloor']['n']==2
 # Loot z piętra 3 (skok na progres 20) i jego jednorazowość
 set_progress(app,20)
 r=fight(a);assert r.status_code==200 and r.json()['floor']==3
 assert r.json()['loot']==dict(id='buty-cienia',name='Buty Cienia')
 s=db_state(app)
 assert 'buty-cienia' in s['inventory'] and s['dungeonLoot']==['buty-cienia']
 set_progress(app,20)
 r=fight(a);assert r.status_code==200 and r.json()['loot'] is None,'unikat nie wypada drugi raz'
 assert db_state(app)['inventory'].count('buty-cienia')==1

def test_defeat_costs_energy_only(env):
 app,clock=env
 a=register(app,'zierowka');create(a,'Zièrek');_ready(app,'Zièrek')
 a.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 with app.state.db.tx() as c:
  s=json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Zièrek'").fetchone()[0])
  s['stats']=[1,1,1,1,1]
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Zièrek'",(json.dumps(s),))
 st0=a.get('/api/worlds/2/state').json()
 r=fight(a);assert r.status_code==200
 data=r.json()
 assert data['cleared'] is False and data['progress']==0
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['cash']==st0['state']['cash'],'porażka nie zabiera gotówki'
 assert st['state']['energy']<st0['state']['energy'],'porażka kosztuje energię'
 assert st['dungeon']['progress']==0

def test_unique_items_give_stats_and_buy_guard(env, legacy_shop):
 app,clock=env
 a=register(app,'zbieracz');create(a,'Zbieracz');_ready(app,'Zbieracz')
 a.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET dungeon_progress=60 WHERE nickname='Zbieracz'")
  s=json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Zbieracz'").fetchone()[0])
  s['stats']=[60,60,60,60,60]
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Zbieracz'",(json.dumps(s),))
 assert fight(a).json()['floor']==7,'na progresie 60 walczymy piętro 7'
 set_progress(app,90,'Zbieracz')
 r=fight(a);assert r.status_code==200 and r.json()['loot']==dict(id='korona-wladcy',name='Korona Władcy Lochu')
 st=a.get('/api/worlds/2/state').json()['dungeon'];assert st['nextFloor']['n']==11 and st['nextFloor']['series']==2,'6.1: po 10. piętrze seria 2'
 with app.state.db.tx() as c:c.execute("UPDATE characters SET dungeon_normal=100 WHERE nickname='Zbieracz'")
 assert fight(a).status_code==409,'100 pięter = Loch Normal opanowany'
 r=a.post('/api/worlds/2/actions',headers={'Idempotency-Key':uuid.uuid4().hex},json={'action':'equip','item':'korona-wladcy'})
 assert r.status_code==200,r.text
 with app.state.db.tx() as c:
  s=json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Zbieracz'").fetchone()[0])
 eff=E.effective(s)
 assert eff==[62,62,60,62,60],'korona: +2 Siła, +2 Int, +2 Charyzma'
 buy=a.post('/api/worlds/2/actions',headers={'Idempotency-Key':uuid.uuid4().hex},json={'action':'buy','item':'buty-cienia'})
 assert buy.status_code==409,'skarb lochu nie jest na sprzedaż'
 assert 'Lochu' in buy.json()['detail']

def test_dungeon_items_in_catalog_not_ranked(env):
 app,clock=env
 a=register(app,'katalog');create(a)
 items=a.get('/api/worlds/2/state').json()['catalog']['items']
 uniq=[i for i in items if i.get('unique')]
 assert {i['id'] for i in uniq}=={'buty-cienia','rekawice-lochu','korona-wladcy','helm-lochu'}
 with app.state.db.tx() as c:
  before=c.execute('SELECT rating FROM characters WHERE nickname=?',('Grotołaz',)).fetchone()[0]
 set_progress(app,0,'Grotołaz')
 a.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 with app.state.db.tx() as c:
  s=json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Grotołaz'").fetchone()[0])
  s['stats']=[60,60,60,60,60]
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Grotołaz'",(json.dumps(s),))
 fight(a)
 with app.state.db.tx() as c:
  after=c.execute('SELECT rating FROM characters WHERE nickname=?',('Grotołaz',)).fetchone()[0]
 assert before==after,'loch nie rusza Elo/rankingu'
