"""0.37 Żywa mapa: presence na /players (district tylko dla online), travel.started dla animacji markera."""
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.travel as T

@pytest.fixture
def env(tmp_path, monkeypatch):
    clock=[1780000000000]
    app=create_app(tmp_path/'presence.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
    with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(16*86400000,))  # 0.33 Er-y
    monkeypatch.setattr(T,'_draw_hitchhike',lambda:(7.5,False))
    return app,clock

def register(app,name):
    c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
    assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid,name):
    r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def players(c,wid=1):
    r=c.get(f'/api/worlds/{wid}/players');assert r.status_code==200,r.text;return {p['nickname']:p for p in r.json()['players']}

def test_presence_online_offline_traveling(env):
    app,clock=env
    a=register(app,'alpha');create(a,1,'Alfa')
    b=register(app,'beta');create(b,1,'Beta')
    ps=players(a)
    assert ps['Alfa']['own'] and ps['Alfa']['online'],ps['Alfa']
    assert ps['Alfa']['district']==1 and not ps['Alfa']['traveling']
    assert ps['Beta']['online'] and not ps['Beta']['own'] and ps['Beta']['district']==1
    # Beta w drodze → district = cel podróży, traveling=True
    r=b.post('/api/worlds/1/travel',json={'target_district':2,'mode':'bus'});assert r.status_code==200,r.text
    ps=players(a)
    assert ps['Beta']['traveling'] and ps['Beta']['district']==2,ps['Beta']
    # travel payload ma started (podstawa animacji po trasie)
    tv=b.get('/api/worlds/1/state').json()['travelInfo']['travel']
    assert tv['started'] and 0<=clock[0]-tv['started']<5000,tv
    # przyjazd (settle) czyści podróż i started
    clock[0]=tv['until']+1000
    ti=b.get('/api/worlds/1/state').json()['travelInfo']
    assert ti['travel'] is None and ti['district']==2
    # offline (last_seen 10 min wstecz) → district None, online False; własna dzielnica zawsze widoczna
    with app.state.db.tx() as c:
        c.execute("UPDATE sessions SET last_seen=last_seen-600000 WHERE account_id=(SELECT id FROM accounts WHERE username='beta')")
    ps=players(a)
    assert not ps['Beta']['online'] and ps['Beta']['district'] is None and not ps['Beta']['traveling']
    ps=players(b)
    assert ps['Beta']['own'] and ps['Beta']['district']==2

def test_presence_biz_and_origin(env):
    app,clock=env
    a=register(app,'kaja');create(a,1,'Kaja')
    b=register(app,'larek');create(b,1,'Lar')
    # Lar kupuje Corner Café (firma w Strefie Przemysłowej — najpierw podróż, settle, potem zakup)
    r=b.post('/api/worlds/1/travel',json={'target_district':2,'mode':'bus'});assert r.status_code==200,r.text
    tv=b.get('/api/worlds/1/state').json()['travelInfo']['travel'];clock[0]=tv['until']+1000
    b.get('/api/worlds/1/state').json()  # lazy settle → dzielnica 2
    import json as _j
    with app.state.db.tx() as c:
        row=c.execute("SELECT state_json FROM characters WHERE nickname='Lar'").fetchone()
        st=_j.loads(row['state_json']);st['xp']=500;st['cash']=5000  # poziom 2 + kasa na firmę (bez zależności od cen)
        c.execute("UPDATE characters SET state_json=? WHERE nickname='Lar'",(_j.dumps(st),))
    r=b.post('/api/worlds/1/actions',headers={'Idempotency-Key':'biztest000000000001'},json={'action':'buy_business','business':'studio'})
    assert r.status_code==200,r.text
    ps=players(a)
    assert ps['Lar']['biz']=={'courier':1,'studio':1,'cafe':1},ps['Lar']   # 4.1: Kawiarnia = budynek (lvl 1 od startu)
    assert ps['Kaja']['biz']=={'courier':1,'cafe':1}
    # Lar w drodze (d2→d3) → origin = dzielnica startowa podróży (2), district = cel
    r=b.post('/api/worlds/1/travel',json={'target_district':3,'mode':'bus'});assert r.status_code==200,r.text
    ps=players(a)
    assert ps['Lar']['traveling'] and ps['Lar']['origin']==2 and ps['Lar']['district']==3,ps['Lar']
    # offline → biz None
    with app.state.db.tx() as c:
        c.execute("UPDATE sessions SET last_seen=last_seen-600000 WHERE account_id=(SELECT id FROM accounts WHERE username='larek')")
    ps=players(a)
    assert ps['Lar']['biz'] is None and ps['Lar']['origin'] is None

def test_players_fields_backward_compatible(env):
    app,clock=env
    c=register(app,'gamma');create(c,1,'Gamma')
    r=c.get('/api/worlds/1/players');assert r.status_code==200,r.text
    row=r.json()['players'][0]
    for key in ('id','nickname','rating','wins','losses','draws','level','own'):
        assert key in row,key
    assert row['own'] is True
