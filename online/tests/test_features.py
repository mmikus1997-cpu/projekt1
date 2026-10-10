import json
import sqlite3
import uuid
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from server.app import create_app, digest
from server import economy as E
from server.backups import Backups

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000];app=create_app(tmp_path/'social.sqlite3',lambda:clock[0],tmp_path/'setup.txt',mode='development')
 return app,clock,tmp_path

class Player:
 def __init__(self,env,name,wid=1):
  self.app,self.clock,self.path=env;self.c=TestClient(self.app);self.name=name;self.wid=wid
  self.s=self.c.post('/api/auth/register',json=dict(username=name,password='test',preview_session=True,consent=True)).json();self.c.cookies.clear()
  self.ch=self.ok(f'/worlds/{wid}/character','POST',dict(nickname=name,accept_test_reset=True,class_type='bokser'))['character']['id']
  import json as _jf  # 0.41: domyślna taktyka (bez xp — testy katalogowe wymagają lvl1/kasy 300)
  with self.app.state.db.tx() as c:
   st=_jf.loads(c.execute('SELECT state_json FROM characters WHERE id=?',(self.ch,)).fetchone()[0]);st['tactic']='kontrola'
   c.execute('UPDATE characters SET state_json=? WHERE id=?',(_jf.dumps(st),self.ch))
 def call(self,path,method='GET',payload=None,**extra):
  return self.c.post('/api/preview/request',json=dict(session=self.s['previewSessionToken'],csrf=self.s['csrf'],method=method,path=path,payload=payload,**extra))
 def ok(self,*args,**kw):
  r=self.call(*args,**kw);assert r.status_code==200,r.text;return r.json()
 def post(self,path,**data):return self.call(path,'POST',data)
 def org(self,tag='TEAM'):return self.ok(f'/worlds/{self.wid}/organizations','POST',dict(name='City '+tag,tag=tag,description='Gramy razem'))['id']
 def send(self,text='Cześć miasto',kind='world',client_id=None):return self.post(f'/worlds/{self.wid}/chat/{kind}',text=text,client_id=client_id or uuid.uuid4().hex)
 def join(self,leader):
  inv=leader.ok(f'/worlds/{self.wid}/organizations/invite','POST',dict(target_id=self.ch))
  return self.ok(f'/organization-invites/{inv["id"]}/accept','POST',{})
 def advance(self,ms=4000):self.clock[0]+=ms

def test_new_catalog_and_old_save_migration(env):
 a=Player(env,'catalog');packet=a.ok('/worlds/1/state');assert len(packet['catalog']['contracts'])==9;assert len(packet['catalog']['items'])==23  # 19 sklepowych + 4 unikaty z Lochu (0.44+)
 assert any(x['id']=='studio' for x in packet['catalog']['ventures'])
 assert packet['state']['ventures']['studio'] is None
 for payload in [dict(action='buy',item='analyst-band'),dict(action='buy_business',business='studio'),dict(action='contract',contract='campaign')]:
  assert a.call('/worlds/1/actions','POST',payload,idempotency_key=uuid.uuid4().hex).status_code==409
 assert a.ok('/worlds/1/state')['state']['cash']==300
 s=E.new(1000,True);old_cash=s['cash'];E.sync(s,2000,1);assert s['cash']==old_cash and s['ventures']['studio'] is None

def test_studio_and_gear_are_authoritative(env, legacy_shop):
 a=Player(env,'builder');db=a.app.state.db
 with db.tx() as c:c.execute('UPDATE characters SET current_district=2 WHERE id=?',(a.ch,))
 with db.tx() as c:
  row=c.execute('SELECT state_json FROM characters WHERE id=?',(a.ch,)).fetchone();s=json.loads(row[0]);s['xp']=600;s['cash']=15000;s['stats']=[10]*5  # baza — test wzorów, nie klasy
  c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s),a.ch))
 def act(**payload):return a.ok('/worlds/1/actions','POST',payload,idempotency_key=uuid.uuid4().hex)['state']
 s=act(action='buy_business',business='studio');assert s['cash']==11000 and s['ventures']['studio']['level']==1
 a.advance(E.HOUR);s=act(action='collect',business='studio');assert s['cash']==11055 and s['ventures']['studio']['vault']==0
 s=act(action='upgrade',business='studio');a.advance(10*E.MINUTE);s=a.ok('/worlds/1/state')['state'];assert s['ventures']['studio']['level']==2
 s=act(action='buy',item='analyst-band');assert E.effective(s)[1]==13 and E.effective(s)[4]==12
 assert a.call('/worlds/1/actions','POST',dict(action='collect',business='nonexistent'),idempotency_key=uuid.uuid4().hex).status_code==409

def test_organizations_world_role_and_membership_boundaries(env):
 a=Player(env,'leader');b=Player(env,'member');outside=Player(env,'outsider');other=Player(env,'otherworld',2)
 a.org();assert outside.post('/worlds/1/organizations',name='Duplicate',tag='team').status_code==409
 assert a.post('/worlds/1/organizations/invite',target_id=other.ch).status_code==404
 b.join(a);data=b.ok('/worlds/1/community');assert len(data['members'])==2 and not data['is_leader']
 assert b.post('/worlds/1/organizations/invite',target_id=outside.ch).status_code==403
 assert b.post('/worlds/1/organizations',name='Other',tag='OT').status_code==409
 assert a.post('/worlds/1/organizations/leave').status_code==409
 assert a.post('/worlds/1/organizations/transfer',target_id=b.ch).status_code==200
 assert a.post('/worlds/1/organizations/remove-member',target_id=b.ch).status_code==403
 assert b.post('/worlds/1/organizations/remove-member',target_id=a.ch).status_code==200
 assert a.ok('/worlds/1/community')['organization'] is None
 assert a.call('/worlds/1/chat/organization').status_code==403
 assert b.post('/worlds/1/organizations/leave').status_code==200
 assert not b.ok('/worlds/1/community')['organizations']

def test_invitation_privacy_decline_expiry_and_retry(env):
 a=Player(env,'leader');b=Player(env,'member');x=Player(env,'stranger');a.org()
 inv=a.ok('/worlds/1/organizations/invite','POST',dict(target_id=b.ch))['id']
 assert x.post(f'/organization-invites/{inv}/accept').status_code==403
 assert b.post(f'/organization-invites/{inv}/decline').status_code==200
 assert a.post('/worlds/1/organizations/invite',target_id=b.ch).status_code==409
 a.advance(86400001);inv=a.ok('/worlds/1/organizations/invite','POST',dict(target_id=b.ch))['id'];a.advance(86400001)
 assert b.post(f'/organization-invites/{inv}/accept').status_code==409
 inv=a.ok('/worlds/1/organizations/invite','POST',dict(target_id=b.ch))['id']
 assert b.post(f'/organization-invites/{inv}/accept').status_code==200
 assert b.post(f'/organization-invites/{inv}/accept').status_code==200

def test_chat_privacy_rate_plain_text_and_idempotency(env):
 a=Player(env,'leader');b=Player(env,'member');x=Player(env,'stranger');a.org();b.join(a)
 key=uuid.uuid4().hex;r=a.send('<img src=x onerror=alert(1)>','organization',key);assert r.status_code==200
 assert a.send('<img src=x onerror=alert(1)>','organization',key).json()==r.json()
 assert a.send('Different','organization',key).status_code==409
 assert x.call('/worlds/1/chat/organization').status_code==403
 assert not x.ok('/worlds/1/chat/world')['messages']
 rows=b.ok('/worlds/1/chat/organization')['messages'];assert len(rows)==1 and rows[0]['text'].startswith('<img')
 assert a.send().status_code==429
 a.advance();assert a.send().status_code==200
 assert a.send('kontakt@example.com').status_code==422
 assert a.send('example.com').status_code==422
 assert a.send('https://example.com').status_code==422
 assert a.send('x'*301).status_code==422
 assert x.post('/worlds/1/reports',message_id=r.json()['id'],reason='Niepoprawne').status_code==404

def test_account_wide_blocks_and_existing_challenges(env):
 a=Player(env,'author');b=Player(env,'reader')
 import json as _jf
 with env[0].state.db.tx() as c:  # 0.41: PvP od 2. poziomu — podnieś obu przed pierwszym wyzwaniem
  for pl in (a,b):
   st=_jf.loads(c.execute('SELECT state_json FROM characters WHERE id=?',(pl.ch,)).fetchone()[0]);st['xp']=150
   c.execute('UPDATE characters SET state_json=? WHERE id=?',(_jf.dumps(st),pl.ch))
 a.org();a.send();b.send('Dzień dobry')
 assert len(a.ok('/worlds/1/chat/world')['messages'])==2
 a.ok('/worlds/1/challenges','POST',dict(target_id=b.ch))
 assert b.post('/worlds/1/blocks',target_id=a.ch).status_code==200
 assert len(a.ok('/worlds/1/chat/world')['messages'])==1
 assert len(b.ok('/worlds/1/chat/world')['messages'])==1
 assert a.post('/worlds/1/organizations/invite',target_id=b.ch).status_code==409
 assert a.post('/worlds/1/challenges',target_id=b.ch).status_code==409
 assert b.ok('/worlds/1/pvp')['challenges'][0]['status']=='declined'
 for p in (a,b):p.ok('/worlds/2/character','POST',dict(nickname=p.name,accept_test_reset=True));p.advance()
 r=a.ok('/worlds/2/chat/world','POST',dict(text='Inny świat',client_id=uuid.uuid4().hex))
 assert not b.ok('/worlds/2/chat/world')['messages']
 target=b.ok('/account/security')['blocks'][0]['account_id'];assert b.post('/account/blocks/remove',account_id=target).status_code==200
 assert len(b.ok('/worlds/2/chat/world')['messages'])==1

def test_reports_moderation_mute_and_authorization(env):
 a=Player(env,'author');b=Player(env,'reader');op=Player(env,'operator')
 setup=(env[2]/'setup.txt').read_text().splitlines()[2];op.ok('/setup/claim','POST',dict(code=setup))
 mid=a.send('Treść do zgłoszenia').json()['id'];assert b.post('/worlds/1/reports',message_id=mid,reason='Naruszenie zasad').status_code==200
 assert b.post('/worlds/1/reports',message_id=mid,reason='Powtórka').status_code==200
 assert b.call('/admin/reports').status_code==403
 reports=op.ok('/admin/reports')['reports'];assert len(reports)==1;rid=reports[0]['id']
 assert op.post(f'/admin/reports/{rid}/resolve',action='hide_mute').status_code==200
 assert 'ukryta' in b.ok('/worlds/1/chat/world')['messages'][0]['text']
 a.advance();assert a.send().status_code==403
 assert op.post(f'/admin/reports/{rid}/resolve',action='dismiss').status_code==409
 a.advance(86400001);assert a.send().status_code==200

def test_delete_leader_requires_transfer_and_social_export_cleanup(env):
 a=Player(env,'leader');b=Player(env,'member');a.org();b.join(a);mid=a.send().json()['id'];b.post('/worlds/1/reports',message_id=mid,reason='Test danych')
 export=a.ok('/account/export');assert len(export['community']['messages'])==1;assert len(export['community']['memberships'])==1
 assert len(export['community']['organizations_led'])==1
 assert 'password_hash' not in json.dumps(export) and a.s['previewSessionToken'] not in json.dumps(export)
 assert a.post('/account/delete',password='test').status_code==409
 assert a.post('/worlds/1/organizations/transfer',target_id=b.ch).status_code==200
 assert a.post('/account/delete',password='test').status_code==200
 assert a.call('/me').status_code==401
 with env[0].state.db.tx() as c:c.execute("UPDATE accounts SET deletion_at=1 WHERE username='leader'")
 env[0].state.purge()
 assert b.ok('/worlds/1/community')['is_leader']
 assert not b.ok('/worlds/1/chat/world')['messages']
 with env[0].state.db.read() as c:assert not c.execute('PRAGMA foreign_key_check').fetchall();assert c.execute('SELECT message_id FROM chat_reports').fetchone()[0] is None
 assert b.post('/account/delete',password='test').status_code==200
 with env[0].state.db.tx() as c:c.execute("UPDATE accounts SET deletion_at=1 WHERE username='member'")
 env[0].state.purge()
 with env[0].state.db.read() as c:assert c.execute('SELECT count(*) FROM organizations').fetchone()[0]==0

def test_sessions_public_ids_and_revoke_others(env):
 a=Player(env,'owner');other=a.c.post('/api/auth/login',json=dict(username=a.name,password='test',preview_session=True)).json();a.c.cookies.clear()
 data=a.ok('/account/security');assert len(data['sessions'])==2
 for s in data['sessions']:assert s['id'] not in [a.s['previewSessionToken'],other['previewSessionToken'],digest(a.s['previewSessionToken']),digest(other['previewSessionToken'])]
 sid=next(s['id'] for s in data['sessions'] if not s['current']);current=next(s['id'] for s in data['sessions'] if s['current'])
 assert a.post('/account/sessions/revoke',password='wrong',session_id=sid).status_code==403
 assert a.post('/account/sessions/revoke',password='test',session_id=current).status_code==409
 assert a.post('/account/sessions/revoke',password='test',session_id='foreign-session').status_code==404
 assert a.post('/account/sessions/revoke',password='test',session_id=sid).status_code==200
 original=a.s;a.s=other;assert a.call('/me').status_code==401;a.s=original
 assert len(a.ok('/account/security')['sessions'])==1

def test_password_change_revokes_every_session_and_preserves_progress(env):
 a=Player(env,'owner');a.org();old=a.s
 assert a.post('/account/password',current_password='test',new_password='abc').status_code==422
 assert a.post('/account/password',current_password='bad',new_password='abcd').status_code==403
 assert a.post('/account/password',current_password='test',new_password='abcd').status_code==200
 assert a.call('/me').status_code==401
 assert a.c.post('/api/auth/login',json=dict(username=a.name,password='test')).status_code==401
 a.s=a.c.post('/api/auth/login',json=dict(username=a.name,password='abcd',preview_session=True)).json();a.c.cookies.clear()
 assert a.ok('/worlds/1/state')['state']['cash']==300
 assert a.ok('/worlds/1/community')['organization']['tag']=='TEAM'

def test_feature_csrf_and_gateway_closed_paths(env):
 a=Player(env,'owner');csrf=a.s['csrf'];a.s['csrf']='wrong'
 for path,data in [('/worlds/1/organizations',dict(name='Fail',tag='NO')),('/worlds/1/chat/world',dict(text='Fail',client_id=uuid.uuid4().hex)),('/account/password',dict(current_password='test',new_password='abcd'))]:assert a.post(path,**data).status_code==403
 a.s['csrf']=csrf
 for path in ['/admin/backups/files','/worlds/1/chat/unknown','/worlds/1/organizations/destroy','/account/sessions/token']:
  assert a.call(path).status_code==404

def test_backups_private_verified_retained_and_restore_rehearsal(env,tmp_path):
 a=Player(env,'operator');a.ok('/setup/claim','POST',dict(code=(env[2]/'setup.txt').read_text().splitlines()[2]))
 service=Backups(env[0].state.db.path,tmp_path/'snapshots');legacy=service.directory/'city-empire-owner.sqlite3';legacy.parent.mkdir();legacy.write_bytes(b'preserve owner backups')
 for _ in range(8):service.create('auto')
 service.create('manual');copies=service.status()['copies'];assert len(copies)==7 and legacy.exists()
 for record in copies:
  path=service.directory/record['name'];assert path.stat().st_mode&0o777==0o600
  with sqlite3.connect(path) as c:assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok'
 source=sqlite3.connect(service.directory/copies[0]['name']);destination=sqlite3.connect(tmp_path/'rehearsal.sqlite3')
 source.backup(destination);assert destination.execute('SELECT count(*) FROM accounts').fetchone()[0]==1;source.close();destination.close()
 assert a.post('/admin/backups').status_code==200
 assert a.ok('/admin/backups')['copies']
 assert a.c.get('/data/backups/'+copies[0]['name']).status_code==404

def test_production_password_policy_and_cookie_feature_access(tmp_path):
 app=create_app(tmp_path/'prod.sqlite3',bootstrap_path=tmp_path/'prod-setup.txt',mode='production');c=TestClient(app)
 r=c.post('/api/auth/register',json=dict(username='production',password='long-password-123',consent=True));assert r.status_code==200
 c.headers['X-CSRF-Token']=r.json()['csrf'];assert c.get('/api/account/security').status_code==200
 assert c.post('/api/account/password',json=dict(current_password='long-password-123',new_password='four')).status_code==422
 assert c.post('/api/account/password',json=dict(current_password='long-password-123',new_password='another-long-password')).status_code==200
 assert c.get('/api/me').status_code==401

def test_existing_session_migration_is_non_destructive(tmp_path):
 from server.app import SCHEMA
 path=tmp_path/'old.sqlite3';con=sqlite3.connect(path);con.executescript(SCHEMA)
 con.execute("INSERT INTO accounts(id,username,password_hash,role,banned,created_at) VALUES(1,'legacy','unused','player',0,1000)")
 con.execute('INSERT INTO sessions VALUES(?,?,?,?)',(digest('legacy-token'),1,'legacy-csrf',9999999999999));con.commit();con.close()
 app=create_app(path,bootstrap_path=tmp_path/'legacy-setup.txt');c=TestClient(app);c.headers['Authorization']='Bearer legacy-token'
 r=c.get('/api/account/security');assert r.status_code==200 and r.json()['sessions'][0]['current'];assert r.json()['sessions'][0]['created_at']==0
 assert c.get('/api/me').json()['user']['username']=='legacy'

def test_concurrent_chat_retries_insert_once(env):
 from concurrent.futures import ThreadPoolExecutor
 a=Player(env,'concurrent');key=uuid.uuid4().hex
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda _:a.send('Jedna wiadomość',client_id=key),range(2)))
 assert all(r.status_code==200 for r in results)
 assert results[0].json()==results[1].json()
 assert len(a.ok('/worlds/1/chat/world')['messages'])==1

def test_concurrent_password_changes_cannot_overwrite_a_newer_password(env):
 from concurrent.futures import ThreadPoolExecutor
 a=Player(env,'concurrent')
 with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(lambda value:a.post('/account/password',current_password='test',new_password=value),['new1','new2']))
 assert sum(r.status_code==200 for r in results)==1
 assert all(r.status_code in (200,401,409) for r in results)
 assert a.call('/me').status_code==401

def test_startup_backup_lifecycle_and_player_denial(env):
 a=Player(env,'player');assert a.call('/admin/backups').status_code==403;assert a.post('/admin/backups').status_code==403
 with TestClient(env[0]):
  directory=env[2]/'backups';assert len(list(directory.glob('auto-*.sqlite3')))==1
  assert json.loads(next(directory.glob('auto-*.json')).read_text())['verified']
