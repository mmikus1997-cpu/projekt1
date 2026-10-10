import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import economy as E

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'game.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 return app,clock,tmp_path

def register(app,name):
 client=TestClient(app);client.app_ref=app;r=client.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;client.headers['X-CSRF-Token']=r.json()['csrf'];return client

def create(c,wid=1,name='PlayerOne'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True,'class_type':'bokser'});assert r.status_code==200,r.text
 if getattr(c,'app_ref',None):_combat_ready(c.app_ref,name)  # 0.41: xp+taktyka po kreacji — bramy testuje test_tactics
 return r.json()
def _combat_ready(app,nick,xp=150,tactic='kontrola'):
 import json
 with app.state.db.tx() as c:
  row=c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()
  st=json.loads(row['state_json']);st['xp']=xp;st['tactic']=tactic
  c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(st),nick))

def action(c,kind,wid=1,key=None,**kwargs):
 return c.post(f'/api/worlds/{wid}/actions',headers={'Idempotency-Key':key or uuid.uuid4().hex},json={'action':kind,**kwargs})
def set_district(app,d,wid=1,nick='PlayerOne'):
 with app.state.db.tx() as cx:cx.execute('UPDATE characters SET current_district=? WHERE nickname=? AND world_id=?',(d,nick,wid))  # 0.45: kontrakty w swoich dzielnicach
def admin(app,path):
 c=register(app,'operator');code=(path/'setup.txt').read_text().splitlines()[2]
 assert c.post('/api/setup/claim',json={'code':code}).status_code==200;return c

def test_auth_and_csrf(env):
 app,clock,path=env;c=register(app,'first_user');assert c.get('/api/me').status_code==200
 create(c);r=c.post('/api/worlds/1/actions',json={'action':'train','stat':0},headers={'X-CSRF-Token':'wrong','Idempotency-Key':uuid.uuid4().hex});assert r.status_code==403
 assert c.post('/api/auth/login',json={'username':'first_user','password':'wrong'}).status_code==401
 assert c.post('/api/auth/login',json={'username':'first_user','password':'test-password-long-123'},headers={'Origin':'https://evil.example'}).status_code==403
 assert c.get('/data/city_empire.sqlite3').status_code==404
 assert c.get('/server/app.py').status_code==404
 assert c.get('/api/admin/overview').status_code==403
 assert c.post('/api/auth/logout',json={}).status_code==200;assert c.get('/api/me').status_code==401

def test_unique_character_and_world_isolation(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a)
 assert a.post('/api/worlds/1/character',json={'nickname':'OtherNick'}).status_code==409
 assert a.post('/api/worlds/2/character',json={'nickname':'LabNick'}).status_code==422
 create(a,2,'LabNick');assert a.get('/api/worlds/1/state').json()['state']['cash']==300
 assert a.get('/api/worlds/2/state').json()['state']['cash']==3000
 assert b.get('/api/worlds/1/state').status_code==404
 assert a.post('/api/worlds/1/actions',headers={'Idempotency-Key':uuid.uuid4().hex},json={'action':'train','stat':0,'cash':100000}).status_code==422

def test_atomic_rewards_costs_and_idempotency(env, legacy_shop, flat_stats):
 app,clock,path=env;c=register(app,'first_user');create(c)
 import json as _jn
 with app.state.db.tx() as c2:
  st=_jn.loads(c2.execute("SELECT state_json FROM characters WHERE nickname='PlayerOne'").fetchone()[0]);st['stats']=[10]*5  # baza 10/10/10/10/10 — test wzorow, nie klasy
  c2.execute("UPDATE characters SET state_json=? WHERE nickname='PlayerOne'",(_jn.dumps(st),))
 set_district(app,8)  # 0.45: dostawy z Przedmieść
 key=uuid.uuid4().hex;r=action(c,'contract',key=key,contract='delivery');assert r.status_code==200
 task=r.json()['state']['contracts'][0]['id'];assert action(c,'contract',key=key,contract='delivery').json()==r.json()
 assert action(c,'train',key=key,stat=0).status_code==409
 assert action(c,'claim_contract',task_id=task).status_code==409
 assert action(c,'train',stat=0).json()['state']['cash']==100  # QA 3: siłownia 50+10×15 $
 clock[0]+=15*E.MINUTE
 mult=c.get('/api/worlds/1/state').json()['catalog']['prices']['delivery']
 assert action(c,'claim_contract',task_id=task).json()['state']['cash']==100+round(100*mult*1.04)  # 0.45: +4% dojazd
 assert action(c,'claim_contract',task_id=task).status_code==409
 assert c.get('/api/worlds/1/state').json()['state']['stats'][0]==11  # QA 3: trening natychmiastowy, bez kolejki
 assert action(c,'buy',item='urban-gloves').status_code==409  # QA 3: droższa siłownia → 211 $ < 250 $
 assert action(c,'buy',item='counter-gloves').status_code==409
 assert c.get('/api/worlds/1/state').json()['state']['cash']==100+round(100*mult*1.04)  # nieudany zakup nic nie pobiera

def test_offline_upgrade_and_cafe(env, flat_stats):
 app,clock,path=env;c=register(app,'first_user');create(c,2)
 import json as _jn
 with app.state.db.tx() as c2:
  st=_jn.loads(c2.execute("SELECT state_json FROM characters WHERE nickname='PlayerOne'").fetchone()[0]);st['stats']=[10]*5  # baza 10/10/10/10/10 — test wzorow, nie klasy
  c2.execute("UPDATE characters SET state_json=? WHERE nickname='PlayerOne'",(_jn.dumps(st),))
 import json
import uuid
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import economy as E

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'game.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 return app,clock,tmp_path

def register(app,name):
 client=TestClient(app);client.app_ref=app;r=client.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;client.headers['X-CSRF-Token']=r.json()['csrf'];return client

def create(c,wid=1,name='PlayerOne'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True,'class_type':'bokser'});assert r.status_code==200,r.text
 if getattr(c,'app_ref',None):_combat_ready(c.app_ref,name)  # 0.41: xp+taktyka po kreacji — bramy testuje test_tactics
 return r.json()
def _combat_ready(app,nick,xp=150,tactic='kontrola'):
 import json
 with app.state.db.tx() as c:
  row=c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()
  st=json.loads(row['state_json']);st['xp']=xp;st['tactic']=tactic
  c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(st),nick))

def action(c,kind,wid=1,key=None,**kwargs):
 return c.post(f'/api/worlds/{wid}/actions',headers={'Idempotency-Key':key or uuid.uuid4().hex},json={'action':kind,**kwargs})
def admin(app,path):
 c=register(app,'operator');code=(path/'setup.txt').read_text().splitlines()[2]
 assert c.post('/api/setup/claim',json={'code':code}).status_code==200;return c

def test_auth_and_csrf(env):
 app,clock,path=env;c=register(app,'first_user');assert c.get('/api/me').status_code==200
 create(c);r=c.post('/api/worlds/1/actions',json={'action':'train','stat':0},headers={'X-CSRF-Token':'wrong','Idempotency-Key':uuid.uuid4().hex});assert r.status_code==403
 assert c.post('/api/auth/login',json={'username':'first_user','password':'wrong'}).status_code==401
 assert c.post('/api/auth/login',json={'username':'first_user','password':'test-password-long-123'},headers={'Origin':'https://evil.example'}).status_code==403
 assert c.get('/data/city_empire.sqlite3').status_code==404
 assert c.get('/server/app.py').status_code==404
 assert c.get('/api/admin/overview').status_code==403
 assert c.post('/api/auth/logout',json={}).status_code==200;assert c.get('/api/me').status_code==401

def test_unique_character_and_world_isolation(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a)
 assert a.post('/api/worlds/1/character',json={'nickname':'OtherNick'}).status_code==409
 assert a.post('/api/worlds/2/character',json={'nickname':'LabNick'}).status_code==422
 create(a,2,'LabNick');assert a.get('/api/worlds/1/state').json()['state']['cash']==300
 assert a.get('/api/worlds/2/state').json()['state']['cash']==3000
 assert b.get('/api/worlds/1/state').status_code==404
 assert a.post('/api/worlds/1/actions',headers={'Idempotency-Key':uuid.uuid4().hex},json={'action':'train','stat':0,'cash':100000}).status_code==422

def test_atomic_rewards_costs_and_idempotency(env, legacy_shop, flat_stats):
 app,clock,path=env;c=register(app,'first_user');create(c)
 import json as _jn
 with app.state.db.tx() as c2:
  st=_jn.loads(c2.execute("SELECT state_json FROM characters WHERE nickname='PlayerOne'").fetchone()[0]);st['stats']=[10]*5  # baza 10/10/10/10/10 — test wzorow, nie klasy
  c2.execute("UPDATE characters SET state_json=? WHERE nickname='PlayerOne'",(_jn.dumps(st),))
 set_district(app,8)  # 0.45: dostawy z Przedmieść
 key=uuid.uuid4().hex;r=action(c,'contract',key=key,contract='delivery');assert r.status_code==200
 task=r.json()['state']['contracts'][0]['id'];assert action(c,'contract',key=key,contract='delivery').json()==r.json()
 assert action(c,'train',key=key,stat=0).status_code==409
 assert action(c,'claim_contract',task_id=task).status_code==409
 assert action(c,'train',stat=0).json()['state']['cash']==100  # QA 3: siłownia 50+10×15 $
 clock[0]+=15*E.MINUTE
 mult=c.get('/api/worlds/1/state').json()['catalog']['prices']['delivery']
 assert action(c,'claim_contract',task_id=task).json()['state']['cash']==100+round(100*mult*1.04)  # 0.45: +4% dojazd
 assert action(c,'claim_contract',task_id=task).status_code==409
 assert c.get('/api/worlds/1/state').json()['state']['stats'][0]==11  # QA 3: trening natychmiastowy, bez kolejki
 assert action(c,'buy',item='urban-gloves').status_code==409  # QA 3: droższa siłownia → 211 $ < 250 $
 assert action(c,'buy',item='counter-gloves').status_code==409
 assert c.get('/api/worlds/1/state').json()['state']['cash']==100+round(100*mult*1.04)  # nieudany zakup nic nie pobiera

def test_offline_upgrade_and_cafe(env, flat_stats):
 app,clock,path=env;c=register(app,'first_user');create(c,2)
 import json as _jn
 with app.state.db.tx() as c2:
  st=_jn.loads(c2.execute("SELECT state_json FROM characters WHERE nickname='PlayerOne'").fetchone()[0]);st['stats']=[10]*5  # baza 10/10/10/10/10 — test wzorow, nie klasy
  c2.execute("UPDATE characters SET state_json=? WHERE nickname='PlayerOne'",(_jn.dumps(st),))
 with app.state.db.tx() as db:db.execute('UPDATE characters SET current_district=8 WHERE nickname=?',('PlayerOne',))  # 0.45: dostawy z Przedmieść
 # Four deliveries, then one more, on the accelerated test world.
 set_district(app,8,wid=2)
 for i in range(4):assert action(c,'contract',2,contract='delivery').status_code==200
 clock[0]+=60_000
 s=c.get('/api/worlds/2/state').json()['state']
 for task in s['contracts']:assert action(c,'claim_contract',2,task_id=task['id']).status_code==200
 r=action(c,'contract',2,contract='delivery');clock[0]+=11_000;assert action(c,'claim_contract',2,task_id=r.json()['state']['contracts'][0]['id']).status_code==200
 with app.state.db.tx() as db:db.execute('UPDATE characters SET current_district=2 WHERE nickname=?',('PlayerOne',))
 assert action(c,'buy_business',2,business='cafe').status_code==409  # 4.1 GDD v3.1: Corner Café zamknięta
 clock[0]+=2*24*E.HOUR
 s=c.get('/api/worlds/2/state').json()['state'];assert s['business']['vault']==40*60*24;assert s['vaults']['cafe']==30*60*24;assert s['energy']==240  # skarbiec budynku Kawiarnia (24 h)
 assert action(c,'collect',2,business='courier').status_code==200
 assert action(c,'upgrade',2,business='courier').status_code==200
 clock[0]+=15_000
 s=c.get('/api/worlds/2/state').json()['state'];assert s['business']['level']==2
 assert abs(s['business']['vault']-11.25)<.0001

def test_ranked_challenge_atomic_and_private(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');z=register(app,'third_user')
 aa=create(a,name='Alpha')['character'];bb=create(b,name='Beta')['character'];create(z,name='Gamma')
 q=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'});assert q.status_code==200,q.text;cid=q.json()['id']
 incoming=b.get('/api/worlds/1/pvp').json();assert 'presja' not in json.dumps(incoming);assert 'snapshot' not in json.dumps(incoming)
 assert a.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontra'}).status_code==403
 r=b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontra'});assert r.status_code==200,r.text
 report=r.json()['report'];assert report['authoritative'];assert len(report['events'])>0
 again=b.post(f'/api/challenges/{cid}/accept',json={'tactic':'presja'});assert again.json()==r.json()
 rows=a.get('/api/worlds/1/players').json()['players'];assert sum(x['wins']+x['losses']+x['draws'] for x in rows)==2
 assert a.get(f"/api/matches/{r.json()['match_id']}").json()['report']==report
 assert z.get(f"/api/matches/{r.json()['match_id']}").status_code==404
 for _ in range(3):  # 5.3 GDD v3.1: ta sama para — najwyżej 4 walki na 24 h
  q=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'});assert q.status_code==200,q.text
  assert b.post(f"/api/challenges/{q.json()['id']}/accept",json={'tactic':'kontra'}).status_code==200
 r4=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'});assert r4.status_code==409 and '4 razy' in r4.json()['detail']
 assert a.get('/api/worlds/1/state').json()['state']['cash']>=300+4*100  # 5.3: nagrody PvP (min. 100 $ za walkę)

def test_admin_world_lifecycle_moderation_and_delete(env):
 app,clock,path=env;op=admin(app,path);player=register(app,'first_user');create(player)
 assert not (path/'setup.txt').exists()
 assert op.post('/api/admin/worlds',json={'name':'BAD','kind':'standard','speed':60}).status_code==422
 r=op.post('/api/admin/worlds',json={'name':'CITY 3','kind':'standard','opens_at':clock[0]+E.HOUR,'registration_open':True,'speed':1});assert r.status_code==200;wid=r.json()['id']
 assert player.post(f'/api/worlds/{wid}/character',json={'nickname':'Future'}).status_code==409
 clock[0]+=E.HOUR+1;create(player,wid,'Future')
 assert op.patch('/api/admin/worlds/1',json={'registration_open':False}).status_code==200
 assert player.get('/api/worlds/1/state').status_code==200
 new_player=register(app,'second_user');assert new_player.post('/api/worlds/1/character',json={'nickname':'NoEntry'}).status_code==409
 op.patch('/api/admin/worlds/1',json={'maintenance':True});assert player.get('/api/worlds/1/state').status_code==409
 op.patch('/api/admin/worlds/1',json={'maintenance':False});assert player.get('/api/worlds/1/state').status_code==200
 uid=new_player.get('/api/me').json()['user']['id'];assert op.patch(f'/api/admin/accounts/{uid}',json={'banned':True}).status_code==200;assert new_player.get('/api/me').status_code==401
 assert len(op.get('/api/admin/overview').json()['audit'])>=5
 export=player.get('/api/account/export').json();assert len(export['characters'])==2;assert 'password' not in json.dumps(export)
 assert player.post('/api/account/delete',json={'password':'wrong'}).status_code==403
 assert player.post('/api/account/delete',json={'password':'test-password-long-123'}).status_code==200
 assert player.get('/api/me').status_code==401

def test_concurrent_reward_claim(env, flat_stats):
 app,clock,path=env;c=register(app,'first_user');create(c);set_district(app,8);r=action(c,'contract',contract='delivery');task=r.json()['state']['contracts'][0]['id'];clock[0]+=11*E.MINUTE  # 0.45
 # Two independent HTTP requests with different keys: only one may pay out.
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:action(c,'claim_contract',task_id=task),range(2)))
 assert sorted(r.status_code for r in responses)==[200,409]
 mult=c.get('/api/worlds/1/state').json()['catalog']['prices']['delivery']
 assert c.get('/api/worlds/1/state').json()['state']['cash']==300+round(100*mult*1.04)  # 0.45

def test_concurrent_duplicate_action_and_accept(env, flat_stats):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a,name='Alpha');bb=create(b,name='Beta')['character'];key=uuid.uuid4().hex
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:action(a,'train',stat=0,key=key),range(2)))
 assert all(r.status_code==200 for r in results);assert results[0].json()==results[1].json()
 assert a.get('/api/worlds/1/state').json()['state']['cash']==40  # QA 3: jeden trening 50+14×15 $
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id']}).json()['id']
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontrola'}),range(2)))
 assert all(r.status_code==200 for r in results);assert results[0].json()==results[1].json()
 assert len(a.get('/api/worlds/1/pvp').json()['matches'])==1
 assert sum(p['wins']+p['losses']+p['draws'] for p in a.get('/api/worlds/1/players').json()['players'])==2

def test_frozen_attacker_snapshot_and_cross_world_rejection(env, legacy_shop):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');aa=create(a,name='Alpha')['character'];bb=create(b,name='Beta')['character'];lab=create(b,2,'BetaLab')['character']
 assert a.post('/api/worlds/1/challenges',json={'target_id':lab['id']}).status_code==404
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'}).json()['id']
 assert action(a,'buy',item='urban-gloves').status_code==200
 report=b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontra'}).json()['report']
 assert report['stats'][0]==[14,8,10,10,8],'zamrożony snapshot atakującego (Bokser) z momentu zaproszenia'
 assert report['tactics']==[{'Bokser':'presja','Obrońca':'kontrola','Szybki':'kontra'}[x] for x in report['classes']],'5.1: Klasa = Taktyka — payload ignorowany'
 assert report['characterIds']==[aa['id'],bb['id']]
 # # 0.41: sparing usunięty — klub sportowy to tylko wyzwania PvP 2.0.
 before=a.get('/api/worlds/1/state').json()['character']['rating']
 assert a.post('/api/worlds/1/spar',json={'opponent':'clubmate','tactic':'kontrola'}).status_code==404,'sparing został usunięty w 0.41'
 assert a.get('/api/worlds/1/state').json()['character']['rating']==before

def test_challenge_expiration_and_account_export_deletion(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a,name='Alpha');bb=create(b,name='Beta')['character']
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id']}).json()['id'];clock[0]+=24*E.HOUR+1
 assert b.post(f'/api/challenges/{cid}/accept',json={'tactic':'presja'}).status_code==409
 assert a.get('/api/worlds/1/pvp').json()['challenges'][0]['status']=='expired'
 assert b.post('/api/account/delete',json={'password':'test-password-long-123'}).status_code==200
 # Grace period is a storage detail: pull the deadline into the past and run the sweep.
 with app.state.db.tx() as c:c.execute("UPDATE accounts SET deletion_at=? WHERE username='second_user'",(clock[0]-1,))
 app.state.purge()
 assert len(a.get('/api/worlds/1/players').json()['players'])==1;assert not a.get('/api/worlds/1/pvp').json()['challenges']

def test_daily_limits_and_test_ranking_isolation(env):
 app,clock,path=env;clients=[register(app,'player_'+str(i)) for i in range(7)]
 chars=[create(c,name='Player'+str(i))['character'] for i,c in enumerate(clients)]
 for i in list(range(1,6))*3:  # 5.3 GDD v3.1: limit 15/dobę (5 rywali × 3 walki — limit pary)
  q=clients[0].post('/api/worlds/1/challenges',json={'target_id':chars[i]['id']});assert q.status_code==200,q.text
  r=clients[i].post('/api/challenges/'+str(q.json()['id'])+'/accept',json={'tactic':'kontrola'});assert r.status_code==200,r.text
 assert clients[0].get('/api/worlds/1/pvp').json()['daily_used']==15
 clock[0]+=11*E.MINUTE  # antyspam 15 wyzwań/10 min to osobny mechanizm
 assert clients[0].post('/api/worlds/1/challenges',json={'target_id':chars[6]['id']}).status_code==409
 create(clients[0],2,'OtherWorld');players=clients[0].get('/api/worlds/2/players').json()['players'];assert len(players)==1;assert players[0]['rating']==1000;assert players[0]['wins']==0
 clock[0]+=24*E.HOUR+1
 assert clients[0].post('/api/worlds/1/challenges',json={'target_id':chars[6]['id']}).status_code==200

def test_strict_payloads_cookie_security_and_rate_limits(env):
 app,clock,path=env;c=register(app,'first_user');create(c)
 assert action(c,'train',stat=True).status_code==422
 assert action(c,'train',stat=-1).status_code==409
 assert action(c,'train',stat=99).status_code==409
 assert c.post('/api/worlds/1/actions',json={'action':'train','stat':0}).status_code==422
 secure=TestClient(app,base_url='https://testserver');r=secure.post('/api/auth/login',json={'username':'first_user','password':'test-password-long-123'})
 cookie=r.headers['set-cookie'];assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=none' in cookie and 'Partitioned' in cookie
 assert secure.get('/api/me').status_code==200
 for _ in range(10):r=c.post('/api/auth/login',json={'username':'nonexistent','password':'not-a-valid-password'})
 assert r.status_code==401
 assert c.post('/api/auth/login',json={'username':'nonexistent','password':'not-a-valid-password'}).status_code==429

def test_opponent_deletion_does_not_reset_daily_usage(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a,name='Alpha');bb=create(b,name='Beta')['character']
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id']}).json()['id'];assert b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontrola'}).status_code==200
 assert a.get('/api/worlds/1/pvp').json()['daily_used']==1
 assert b.post('/api/account/delete',json={'password':'test-password-long-123'}).status_code==200
 assert a.get('/api/worlds/1/pvp').json()['daily_used']==1
 assert a.get('/api/account/export').json()['ranked_usage'][0]['used']==1

 # Four deliveries, then one more, on the accelerated test world.
 set_district(app,8,wid=2)
 for i in range(4):assert action(c,'contract',2,contract='delivery').status_code==200
 clock[0]+=60_000
 s=c.get('/api/worlds/2/state').json()['state']
 for task in s['contracts']:assert action(c,'claim_contract',2,task_id=task['id']).status_code==200
 r=action(c,'contract',2,contract='delivery');clock[0]+=11_000;assert action(c,'claim_contract',2,task_id=r.json()['state']['contracts'][0]['id']).status_code==200
 assert action(c,'buy_business',2,business='cafe').status_code==409  # 4.1 GDD v3.1: Corner Café zamknięta
 clock[0]+=2*24*E.HOUR
 s=c.get('/api/worlds/2/state').json()['state'];assert s['business']['vault']==40*60*24;assert s['vaults']['cafe']==30*60*24;assert s['energy']==240  # skarbiec budynku Kawiarnia (24 h)
 assert action(c,'collect',2,business='courier').status_code==200
 assert action(c,'upgrade',2,business='courier').status_code==200
 clock[0]+=15_000
 s=c.get('/api/worlds/2/state').json()['state'];assert s['business']['level']==2
 assert abs(s['business']['vault']-11.25)<.0001

def test_ranked_challenge_atomic_and_private(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');z=register(app,'third_user')
 aa=create(a,name='Alpha')['character'];bb=create(b,name='Beta')['character'];create(z,name='Gamma')
 q=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'});assert q.status_code==200,q.text;cid=q.json()['id']
 incoming=b.get('/api/worlds/1/pvp').json();assert 'presja' not in json.dumps(incoming);assert 'snapshot' not in json.dumps(incoming)
 assert a.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontra'}).status_code==403
 r=b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontra'});assert r.status_code==200,r.text
 report=r.json()['report'];assert report['authoritative'];assert len(report['events'])>0
 again=b.post(f'/api/challenges/{cid}/accept',json={'tactic':'presja'});assert again.json()==r.json()
 rows=a.get('/api/worlds/1/players').json()['players'];assert sum(x['wins']+x['losses']+x['draws'] for x in rows)==2
 assert a.get(f"/api/matches/{r.json()['match_id']}").json()['report']==report
 assert z.get(f"/api/matches/{r.json()['match_id']}").status_code==404
 for _ in range(3):  # 5.3 GDD v3.1: ta sama para — najwyżej 4 walki na 24 h
  q=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'});assert q.status_code==200,q.text
  assert b.post(f"/api/challenges/{q.json()['id']}/accept",json={'tactic':'kontra'}).status_code==200
 r4=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'});assert r4.status_code==409 and '4 razy' in r4.json()['detail']
 assert a.get('/api/worlds/1/state').json()['state']['cash']>=300+4*100  # 5.3: nagrody PvP (min. 100 $ za walkę)

def test_admin_world_lifecycle_moderation_and_delete(env):
 app,clock,path=env;op=admin(app,path);player=register(app,'first_user');create(player)
 assert not (path/'setup.txt').exists()
 assert op.post('/api/admin/worlds',json={'name':'BAD','kind':'standard','speed':60}).status_code==422
 r=op.post('/api/admin/worlds',json={'name':'CITY 3','kind':'standard','opens_at':clock[0]+E.HOUR,'registration_open':True,'speed':1});assert r.status_code==200;wid=r.json()['id']
 assert player.post(f'/api/worlds/{wid}/character',json={'nickname':'Future'}).status_code==409
 clock[0]+=E.HOUR+1;create(player,wid,'Future')
 assert op.patch('/api/admin/worlds/1',json={'registration_open':False}).status_code==200
 assert player.get('/api/worlds/1/state').status_code==200
 new_player=register(app,'second_user');assert new_player.post('/api/worlds/1/character',json={'nickname':'NoEntry'}).status_code==409
 op.patch('/api/admin/worlds/1',json={'maintenance':True});assert player.get('/api/worlds/1/state').status_code==409
 op.patch('/api/admin/worlds/1',json={'maintenance':False});assert player.get('/api/worlds/1/state').status_code==200
 uid=new_player.get('/api/me').json()['user']['id'];assert op.patch(f'/api/admin/accounts/{uid}',json={'banned':True}).status_code==200;assert new_player.get('/api/me').status_code==401
 assert len(op.get('/api/admin/overview').json()['audit'])>=5
 export=player.get('/api/account/export').json();assert len(export['characters'])==2;assert 'password' not in json.dumps(export)
 assert player.post('/api/account/delete',json={'password':'wrong'}).status_code==403
 assert player.post('/api/account/delete',json={'password':'test-password-long-123'}).status_code==200
 assert player.get('/api/me').status_code==401

def test_concurrent_reward_claim(env, flat_stats):
 app,clock,path=env;c=register(app,'first_user');create(c);set_district(app,8);r=action(c,'contract',contract='delivery');task=r.json()['state']['contracts'][0]['id'];clock[0]+=11*E.MINUTE  # 0.45
 # Two independent HTTP requests with different keys: only one may pay out.
 with ThreadPoolExecutor(max_workers=2) as pool:responses=list(pool.map(lambda _:action(c,'claim_contract',task_id=task),range(2)))
 assert sorted(r.status_code for r in responses)==[200,409]
 mult=c.get('/api/worlds/1/state').json()['catalog']['prices']['delivery']
 assert c.get('/api/worlds/1/state').json()['state']['cash']==300+round(100*mult*1.04)  # 0.45

def test_concurrent_duplicate_action_and_accept(env, flat_stats):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a,name='Alpha');bb=create(b,name='Beta')['character'];key=uuid.uuid4().hex
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:action(a,'train',stat=0,key=key),range(2)))
 assert all(r.status_code==200 for r in results);assert results[0].json()==results[1].json()
 assert a.get('/api/worlds/1/state').json()['state']['cash']==40  # QA 3: jeden trening 50+14×15 $
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id']}).json()['id']
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontrola'}),range(2)))
 assert all(r.status_code==200 for r in results);assert results[0].json()==results[1].json()
 assert len(a.get('/api/worlds/1/pvp').json()['matches'])==1
 assert sum(p['wins']+p['losses']+p['draws'] for p in a.get('/api/worlds/1/players').json()['players'])==2

def test_frozen_attacker_snapshot_and_cross_world_rejection(env, legacy_shop):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');aa=create(a,name='Alpha')['character'];bb=create(b,name='Beta')['character'];lab=create(b,2,'BetaLab')['character']
 assert a.post('/api/worlds/1/challenges',json={'target_id':lab['id']}).status_code==404
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id'],'tactic':'presja'}).json()['id']
 assert action(a,'buy',item='urban-gloves').status_code==200
 report=b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontra'}).json()['report']
 assert report['stats'][0]==[14,8,10,10,8],'zamrożony snapshot atakującego (Bokser) z momentu zaproszenia'
 assert report['tactics']==[{'Bokser':'presja','Obrońca':'kontrola','Szybki':'kontra'}[x] for x in report['classes']],'5.1: Klasa = Taktyka — payload ignorowany'
 assert report['characterIds']==[aa['id'],bb['id']]
 # # 0.41: sparing usunięty — klub sportowy to tylko wyzwania PvP 2.0.
 before=a.get('/api/worlds/1/state').json()['character']['rating']
 assert a.post('/api/worlds/1/spar',json={'opponent':'clubmate','tactic':'kontrola'}).status_code==404,'sparing został usunięty w 0.41'
 assert a.get('/api/worlds/1/state').json()['character']['rating']==before

def test_challenge_expiration_and_account_export_deletion(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a,name='Alpha');bb=create(b,name='Beta')['character']
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id']}).json()['id'];clock[0]+=24*E.HOUR+1
 assert b.post(f'/api/challenges/{cid}/accept',json={'tactic':'presja'}).status_code==409
 assert a.get('/api/worlds/1/pvp').json()['challenges'][0]['status']=='expired'
 assert b.post('/api/account/delete',json={'password':'test-password-long-123'}).status_code==200
 # Grace period is a storage detail: pull the deadline into the past and run the sweep.
 with app.state.db.tx() as c:c.execute("UPDATE accounts SET deletion_at=? WHERE username='second_user'",(clock[0]-1,))
 app.state.purge()
 assert len(a.get('/api/worlds/1/players').json()['players'])==1;assert not a.get('/api/worlds/1/pvp').json()['challenges']

def test_daily_limits_and_test_ranking_isolation(env):
 app,clock,path=env;clients=[register(app,'player_'+str(i)) for i in range(7)]
 chars=[create(c,name='Player'+str(i))['character'] for i,c in enumerate(clients)]
 for i in list(range(1,6))*3:  # 5.3 GDD v3.1: limit 15/dobę (5 rywali × 3 walki — limit pary)
  q=clients[0].post('/api/worlds/1/challenges',json={'target_id':chars[i]['id']});assert q.status_code==200,q.text
  r=clients[i].post('/api/challenges/'+str(q.json()['id'])+'/accept',json={'tactic':'kontrola'});assert r.status_code==200,r.text
 assert clients[0].get('/api/worlds/1/pvp').json()['daily_used']==15
 clock[0]+=11*E.MINUTE  # antyspam 15 wyzwań/10 min to osobny mechanizm
 assert clients[0].post('/api/worlds/1/challenges',json={'target_id':chars[6]['id']}).status_code==409
 create(clients[0],2,'OtherWorld');players=clients[0].get('/api/worlds/2/players').json()['players'];assert len(players)==1;assert players[0]['rating']==1000;assert players[0]['wins']==0
 clock[0]+=24*E.HOUR+1
 assert clients[0].post('/api/worlds/1/challenges',json={'target_id':chars[6]['id']}).status_code==200

def test_strict_payloads_cookie_security_and_rate_limits(env):
 app,clock,path=env;c=register(app,'first_user');create(c)
 assert action(c,'train',stat=True).status_code==422
 assert action(c,'train',stat=-1).status_code==409
 assert action(c,'train',stat=99).status_code==409
 assert c.post('/api/worlds/1/actions',json={'action':'train','stat':0}).status_code==422
 secure=TestClient(app,base_url='https://testserver');r=secure.post('/api/auth/login',json={'username':'first_user','password':'test-password-long-123'})
 cookie=r.headers['set-cookie'];assert 'Secure' in cookie and 'HttpOnly' in cookie and 'SameSite=none' in cookie and 'Partitioned' in cookie
 assert secure.get('/api/me').status_code==200
 for _ in range(10):r=c.post('/api/auth/login',json={'username':'nonexistent','password':'not-a-valid-password'})
 assert r.status_code==401
 assert c.post('/api/auth/login',json={'username':'nonexistent','password':'not-a-valid-password'}).status_code==429

def test_opponent_deletion_does_not_reset_daily_usage(env):
 app,clock,path=env;a=register(app,'first_user');b=register(app,'second_user');create(a,name='Alpha');bb=create(b,name='Beta')['character']
 cid=a.post('/api/worlds/1/challenges',json={'target_id':bb['id']}).json()['id'];assert b.post(f'/api/challenges/{cid}/accept',json={'tactic':'kontrola'}).status_code==200
 assert a.get('/api/worlds/1/pvp').json()['daily_used']==1
 assert b.post('/api/account/delete',json={'password':'test-password-long-123'}).status_code==200
 assert a.get('/api/worlds/1/pvp').json()['daily_used']==1
 assert a.get('/api/account/export').json()['ranked_usage'][0]['used']==1
