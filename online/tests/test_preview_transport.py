import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app

@pytest.fixture
def env(tmp_path):
 now=[1780000000000]
 app=create_app(tmp_path/'transport.sqlite3',lambda:now[0],tmp_path/'setup.txt',mode='development')
 return app,now,tmp_path

def login(c,name='json_user'):
 r=c.post('/api/auth/register',json={'username':name,'password':'test','preview_session':True,'consent':True})
 assert r.status_code==200,r.text
 data=r.json();c.cookies.clear();return data

def call(c,s,path,method='GET',payload=None,csrf=None,key=None):
 return c.post('/api/preview/request',json=dict(session=s['previewSessionToken'],csrf=s['csrf'] if csrf is None else csrf,method=method,path=path,payload=payload,idempotency_key=key))

def test_body_only_login_read_mutate_reload_and_logout(env, flat_stats):
 app,now,path=env
 with TestClient(app) as c:
  s=login(c)
  assert c.get('/api/auth/config').json()['previewTransport']=='json-v1'
  assert not c.cookies
  assert call(c,s,'/me').json()['user']['username']=='json_user'
  assert call(c,s,'/worlds').status_code==200
  assert call(c,s,'/worlds/1/character','POST',{'nickname':'JSON Player'}).status_code==200
  key=uuid.uuid4().hex
  r=call(c,s,'/worlds/1/actions','POST',{'action':'train','stat':0},key=key)
  assert r.status_code==200,r.text
  assert r.json()['state']['cash']==100  # QA 3: siłownia 50+10×15 $
  assert call(c,s,'/worlds/1/actions','POST',{'action':'train','stat':0},key=key).json()==r.json()
  assert call(c,s,'/worlds/1/state').json()['state']['cash']==100
  assert call(c,s,'/auth/logout','POST',{}).status_code==200
  assert call(c,s,'/me').status_code==401
  r=c.post('/api/auth/login',json={'username':'json_user','password':'test','preview_session':True});assert r.status_code==200
  s2=r.json();c.cookies.clear();assert call(c,s2,'/worlds/1/state').json()['state']['cash']==100

def test_rpc_preserves_csrf_roles_and_server_authority(env):
 app,now,path=env
 with TestClient(app) as c:
  s=login(c)
  assert call(c,s,'/worlds/1/character','POST',{'nickname':'Blocked'},csrf='').status_code==403
  assert call(c,s,'/admin/overview').status_code==403
  assert call(c,s,'/admin/worlds','POST',{'name':'Bad World'}).status_code==403
  assert call(c,s,'/worlds/1/character','POST',{'nickname':'Valid Player'}).status_code==200
  r=call(c,s,'/worlds/1/actions','POST',{'action':'train','stat':0,'cash':99999},key=uuid.uuid4().hex)
  assert r.status_code==422
  assert call(c,s,'/worlds/1/state').json()['state']['cash']==300
  bad={**s,'previewSessionToken':'not-a-session'}
  assert call(c,bad,'/me').status_code==401
  # A different valid browser cookie must not substitute for a bad body token.
  c.post('/api/auth/login',json={'username':'json_user','password':'test'})
  assert call(c,bad,'/worlds').status_code==401
  assert call(c,s,'/auth/logout','POST',{},csrf='bad').status_code==403

def test_rpc_cannot_proxy_arbitrary_paths_or_recurse(env):
 app,now,path=env
 with TestClient(app) as c:
  s=login(c)
  for target in ['/preview/request','/auth/login','/auth/register','/setup/status','/../admin/overview','/worlds?x=1','//other.example/worlds','https://other.example/','/data/city_empire.sqlite3','/worlds/%31/state']:
   assert call(c,s,target).status_code==404,target
  assert call(c,s,'/worlds',payload={'unexpected':True}).status_code==422
  assert call(c,s,'/worlds/1/character','GET').status_code==404
  assert c.post('/api/preview/request',json={}).status_code==422
  r=c.post('/api/preview/request',json=dict(session=s['previewSessionToken'],csrf=s['csrf'],method='GET',path='/worlds'),headers={'Origin':'https://evil.example'})
  assert r.status_code==403

def test_production_disables_body_token_and_gateway(tmp_path):
 app=create_app(tmp_path/'prod.sqlite3',bootstrap_path=tmp_path/'setup.txt',mode='production')
 with TestClient(app) as c:
  r=c.post('/api/auth/register',json={'username':'prod_user','password':'long-test-password','preview_session':True,'consent':True})
  assert r.status_code==200 and 'previewSessionToken' not in r.json()
  assert c.get('/api/auth/config').json()['previewTransport'] is None
  assert c.post('/api/preview/request',json=dict(session='anything',csrf='',method='GET',path='/worlds')).status_code==404

def test_json_gateway_admin_changes_are_audited(env):
 app,now,path=env
 with TestClient(app) as c:
  s=login(c);code=(path/'setup.txt').read_text().splitlines()[2]
  assert call(c,s,'/setup/claim','POST',{'code':code}).status_code==200
  assert call(c,s,'/me').json()['user']['role']=='admin'
  created=call(c,s,'/admin/worlds','POST',{'name':'JSON WORLD','kind':'standard'})
  assert created.status_code==200
  wid=created.json()['id']
  assert call(c,s,f'/admin/worlds/{wid}','PATCH',{'registration_open':False}).status_code==200
  data=call(c,s,'/admin/overview').json()
  assert not next(w for w in data['worlds'] if w['id']==wid)['registration_open']
  assert len(data['audit'])==3

def test_json_gateway_expired_session_and_cross_account_isolation(env):
 app,now,path=env
 with TestClient(app) as a,TestClient(app) as b:
  sa=login(a,'first_user');sb=login(b,'second_user')
  assert call(a,sa,'/worlds/1/character','POST',{'nickname':'First'}).status_code==200
  assert call(b,sb,'/worlds/1/state').status_code==404
  now[0]+=8*24*3600000
  assert call(a,sa,'/worlds/1/state').status_code==401
