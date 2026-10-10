"""0.29 Frontend/UX: przycisk „Przyspiesz" dla VIP w podróży oraz skrót organizacji w czacie."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'hub.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(9*86400000,))  # 0.33 Er-y
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid=2,name='Mieszkaniec'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def state(c,wid=2):
 return c.get(f'/api/worlds/{wid}/state').json()

def grant_vip(app,nick,until):
 with app.state.db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0]);s['vipUntil']=until
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def test_travel_speedup_vip_gate(env):
 app,clock=env;c=register(app,'vipuser');create(c,2,name='VIP Test')
 assert c.post('/api/worlds/2/travel/speedup',json={}).status_code==409  # nie jesteś w drodze
 r=c.post('/api/worlds/2/travel',json={'target_district':5,'mode':'bus'});assert r.status_code==200,r.text
 until=r.json()['travel']['until']
 r=c.post('/api/worlds/2/travel/speedup',json={})
 assert r.status_code==403 and 'VIP' in r.json()['detail']  # bez VIP funkcja niedostępna
 grant_vip(app,'VIP Test',clock[0]+24*3600*1000)
 r=c.post('/api/worlds/2/travel/speedup',json={});assert r.status_code==200,r.text
 data=r.json()
 remaining=until-clock[0]
 assert data['remaining']==max(1000,remaining//2)  # połowa pozostałego czasu, min. 1 s
 assert data['until']<until
 r=c.post('/api/worlds/2/travel/speedup',json={});assert r.status_code==200  # kolejne skrócenie (½ z ½)
 assert r.json()['remaining']<data['remaining']

def test_chat_carries_org_tag(env):
 app,clock=env;a=register(app,'czytacz');create(a,2,name='Czytacz')
 b=register(app,'czlonek');create(b,2,name='Członek')
 assert b.post('/api/worlds/2/organizations',json={'name':'Tagowa Ekipa','tag':'TGE','description':'Org do testu taga'}).status_code==200
 assert b.post('/api/worlds/2/chat/world',json={'text':'Cześć z TGE!','client_id':'a'*20}).status_code==200
 data=a.get('/api/worlds/2/chat/world').json()
 msgs=[m for m in data['messages'] if m['text']=='Cześć z TGE!']
 assert msgs and msgs[0]['org_tag']=='TGE' and msgs[0]['own'] is False
 # autor pierwszej wiadomości to lider założyciel — tag działa przez fallback leader_id
 assert msgs[0]['nickname']=='Członek'
