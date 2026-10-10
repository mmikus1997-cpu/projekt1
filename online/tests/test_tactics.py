"""5.1 GDD v3.1: Klasa = Taktyka (Bokser=Presja, Obrońca=Kontrola, Szybki=Kontra) — bez wyboru taktyki; PvP od 2 lvl, Loch od 3 lvl."""
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.combat as C

@pytest.fixture
def env(tmp_path):
    clock=[1780000000000]
    app=create_app(tmp_path/'tactics.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
    return app,clock

def register(app,name):
    c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
    assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid,name,cls='bokser'):
    r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True,'class_type':cls});assert r.status_code==200,r.text;return r.json()

def set_xp(app,nick,xp):
    import json
    with app.state.db.tx() as c:
        row=c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()
        st=json.loads(row['state_json']);st['xp']=xp
        c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(st),nick))

def char_id(c,name):
    rows=c.get('/api/worlds/1/players').json()['players']
    return next(p['id'] for p in rows if p['nickname']==name)

def tactic_of(app,nick):
    import json
    with app.state.db.tx() as c:
        row=c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()
        return json.loads(row['state_json']).get('tactic')

def test_tactic_endpoint_removed_and_class_tactic(env):
    app,clock=env
    c=register(app,'taktyk');create(c,1,'Taktyk')
    assert c.post('/api/worlds/1/tactic',json={'style':'presja'}).status_code==404     # endpoint usunięty
    assert c.post('/api/worlds/1/pvp/defense',json={'seq':['unik']*3}).status_code==404
    assert c.get('/api/worlds/1/state').json()['character']['tactic']=='presja'       # Bokser → Presja (wyliczane)
    assert tactic_of(app,'Taktyk') is None                                            # pole nie jest zapisywane
    assert C.CLASS_TACTIC=={'Bokser':'presja','Obrońca':'kontrola','Szybki':'kontra'}

def test_legacy_tactic_stripped(env):
    import json
    app,clock=env
    c=register(app,'stary');create(c,1,'Stary','szybki')
    with app.state.db.tx() as db:
        st=json.loads(db.execute("SELECT state_json FROM characters WHERE nickname='Stary'").fetchone()[0]);st['tactic']='presja';st['pvpDefense']=['dodge']*3
        db.execute("UPDATE characters SET state_json=? WHERE nickname='Stary'",(json.dumps(st),))
    assert c.get('/api/worlds/1/state').json()['character']['tactic']=='kontra'        # klasa wygrywa ze starym wyborem
    assert tactic_of(app,'Stary') is None

def test_pvp_gates(env):
    app,clock=env
    a=register(app,'adami');create(a,1,'Adami','bokser')
    b=register(app,'barti');create(b,1,'Barti','szybki')
    bid=char_id(a,'Barti')
    r=a.post('/api/worlds/1/challenges',json={'target_id':bid,'tactic':'presja'})
    assert r.status_code==409 and '2. poziomie' in r.json()['detail'],r.text
    set_xp(app,'Adami',150)  # lvl2 — bez wyboru taktyki walczy od razu (1-Click)
    r=a.post('/api/worlds/1/challenges',json={'target_id':bid,'tactic':'kontra'});assert r.status_code==200,r.text
    r=b.post(f"/api/challenges/{r.json()['id']}/accept",json={'tactic':'presja'});assert r.status_code==200,r.text
    rep=r.json()['report']
    assert rep['tactics']==['presja','kontra'] and rep['classes']==['Bokser','Szybki']   # z klas, payload ignorowany
    assert rep['advantage']==[False,False]                                               # Combat 3.0: bez RPS
    assert a.post('/api/worlds/1/spar',json={'tactic':'presja','opponent':'rookie'}).status_code==404

def test_dungeon_gate_and_style(env):
    app,clock=env
    c=register(app,'cezar');create(c,1,'Cezar','obronca')
    c.post('/api/worlds/1/location',json={'location':'brama-lochow'})
    r=c.post('/api/worlds/1/dungeon/floor',json={'seq':['fast','fast','fast']})
    assert r.status_code==409 and '3. poziomie' in r.json()['detail'],r.text
    set_xp(app,'Cezar',400)  # lvl3
    r=c.post('/api/worlds/1/dungeon/floor',json={});assert r.status_code==200,r.text
    assert r.json()['report']['classes'][0]=='Obrońca'                                  # Combat 3.0: klasa zamiast sekwencji
    st=c.get('/api/worlds/1/state').json()
    assert st['character']['tactic']=='kontrola' and st['dungeon']['tacticSet'] is True and st['dungeon']['locked'] is False
