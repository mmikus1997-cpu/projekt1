"""0.30 Klasy i Baza: bezpieczna migracja additive, wybór jednej z 3 klas przy tworzeniu
(unikalne statystyki startowe, każda klasa łącznie 50 pkt), lokacje postaci — oraz
regresja: stary kod (postać bez class_type, legacy baza bez nowych kolumn) działa bez błędów."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import combat

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 return create_app(tmp_path/'cls.sqlite3',lambda:clock[0],tmp_path/'setup.txt'),clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,cls=None,wid=2,name='Mieszkaniec'):
 payload={'nickname':name,'accept_test_reset':True}
 if cls:payload['class_type']=cls
 r=c.post(f'/api/worlds/{wid}/character',json=payload);assert r.status_code==200,r.text;return r.json()

LEGACY_CHARACTERS=("CREATE TABLE characters(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL,world_id INTEGER NOT NULL,"
 "nickname TEXT NOT NULL,state_json TEXT NOT NULL,rating REAL NOT NULL DEFAULT 1000,wins INTEGER NOT NULL DEFAULT 0,"
 "losses INTEGER NOT NULL DEFAULT 0,draws INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,"
 "current_district INTEGER,travel_destination INTEGER,travel_until INTEGER,travel_mode TEXT)")

def test_migration_is_safe_on_legacy_db(tmp_path):
 # Baza sprzed 0.30: characters bez czterech nowych kolumn i z istniejącym wierszem.
 db=tmp_path/'legacy.sqlite3'
 con=sqlite3.connect(db)
 con.execute(LEGACY_CHARACTERS)
 con.execute("INSERT INTO characters(account_id,world_id,nickname,state_json,created_at,current_district) VALUES(1,2,'Staruszek','{}',1,3)")
 con.commit();con.close()
 create_app(db,lambda:1780000000000,tmp_path/'setup.txt')
 con=sqlite3.connect(db)
 cols={r[1] for r in con.execute('PRAGMA table_info(characters)')}
 assert {'class_type','class_evolution','current_location','dungeon_progress'}<=cols
 row=con.execute('SELECT class_type,class_evolution,current_location,dungeon_progress,nickname,current_district FROM characters').fetchone()
 assert row==(None,1,'ulica',0,'Staruszek',3),'stary wiersz musi przetrwać migrację z bezpiecznymi defaults'

def test_class_creation_stats_and_payload(env):
 app,clock=env
 a=register(app,'wojownik');create(a,'szybki',name='Blysk')
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['stats']==[8,8,14,8,12],'Szybki: Refleks 14, Spryt 12, razem 50 pkt'
 ch=st['character']
 assert ch['classType']=='szybki' and ch['classEvolution']==1 and ch['currentLocation']=='ulica' and ch['dungeonProgress']==0
 b=register(app,'tarczownik');create(b,'obronca',name='Mur')
 st=b.get('/api/worlds/2/state').json()
 assert st['state']['stats']==[8,14,8,12,8] and st['character']['classType']=='obronca'
 assert sum(st['state']['stats'])==50
 bad=register(app,'czarodziej')
 r=bad.post('/api/worlds/2/character',json={'nickname':'Mag','accept_test_reset':True,'class_type':'mag'})
 assert r.status_code==422

def test_creation_without_class_stays_compatible(env):
 # 0.41: kreator postaci WYMUSZA klasę (radio required + walidacja submit — nie da się pominąć);
 # API akceptuje null wyłącznie dla kompatybilności (stare zapisy/klienci), walka liczy klasę z dominanty.
 app,clock=env
 a=register(app,'klasyk');create(a,None,name='Klasyk')
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['stats']==[10]*5 and st['character']['classType'] is None
 assert combat.pvp_class(st['state']['stats'])=='Bokser','bez class_type klasa z dominanty jak dotychczas'

def test_location_move(env):
 app,clock=env
 a=register(app,'spacerowicz');create(a,'bokser',name='Spacer')
 r=a.post('/api/worlds/2/location',json={'location':'silownia'})
 assert r.status_code==200 and r.json()['currentLocation']=='silownia'
 assert a.get('/api/worlds/2/state').json()['character']['currentLocation']=='silownia'
 assert a.post('/api/worlds/2/location',json={'location':'loch'}).status_code==422
 assert a.post('/api/worlds/2/location',json={'location':'brama-lochow'}).json()['currentLocation']=='brama-lochow'

def test_pvp_uses_chosen_classes(env):
 app,clock=env
 a=register(app,'szybciutki');create(a,'szybki',name='Blysk')
 b=register(app,'twardziel');create(b,'obronca',name='Mur')
 targets=b.get('/api/worlds/2/pvp/targets').json()
 row=[x for x in targets['targets'] if x['nickname']=='Blysk'][0]
 assert row['cls']=='Szybki','lista celów pokazuje klasę wybraną, nie wyliczoną'
 rep=combat.simultaneous([10]*5,[10]*5,['fast','heavy','dodge'],['fast','dodge','heavy'],42,a_cls='szybki')
 assert rep['classes']==['Szybki','Bokser'],'jawna klasa nadpisze dominantę'
 import json as _j
 with app.state.db.tx() as c:  # 0.42: auto-atak wymaga 2. poziomu i zapisanej taktyki
  st=_j.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Blysk'").fetchone()[0]);st['xp']=400;st['tactic']='kontrola'
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Blysk'",(_j.dumps(st),))
 tid=a.get('/api/worlds/2/pvp/targets').json()['targets'][0]['id']
 data=a.post(f'/api/worlds/2/pvp/attack/{tid}',json={'seq':['fast','heavy','dodge']}).json()  # payload ignorowany
 assert data['report']['classes']==['Szybki','Obrońca'],'atak rozstrzyga silnik z klasami wybranymi'

def test_class_pick_after_creation_one_time(env):
 # 0.43: klasa przeniesiona z kreacji do pierwszego wejścia w PvP — wybór raz, staty się przesuwają
 app,clock=env
 a=register(app,'pozny');create(a,None,name='Pózny')
 st=a.get('/api/worlds/2/state').json()
 assert st['state']['stats']==[10]*5 and st['character']['classType'] is None
 r=a.post('/api/worlds/2/class',json={'class_type':'szybki'});assert r.status_code==200,r.text
 d=r.json();assert d['classType']=='szybki' and d['stats']==[8,8,14,8,12]
 st=a.get('/api/worlds/2/state').json()
 assert st['character']['classType']=='szybki' and st['state']['stats']==[8,8,14,8,12]
 r=a.post('/api/worlds/2/class',json={'class_type':'bokser'});assert r.status_code==409 and 'jednorazowa' in r.json()['detail']
 r=a.post('/api/worlds/2/class',json={'class_type':'smok'});assert r.status_code==422
 # trening przed wyborem klasy zostaje zachowany (przesunięcie, nie nadpisanie)
 b=register(app,'cwiczek');create(b,None,name='Cwiczek')
 with app.state.db.tx() as c:
  import json as _j
  stx=_j.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Cwiczek'").fetchone()[0]);stx['stats']=[12,10,10,10,10]
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Cwiczek'",(_j.dumps(stx),))
 rb=b.post('/api/worlds/2/class',json={'class_type':'bokser'});assert rb.status_code==200
 assert rb.json()['stats']==[16,8,10,10,8],'12 Siły + przesunięcie Boksera (+4/-2) = 16/8/10/10/8'
