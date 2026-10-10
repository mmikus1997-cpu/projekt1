import sqlite3
import pytest
from fastapi.testclient import TestClient
from server.app import create_app

@pytest.fixture
def env(tmp_path):
 now=[1780000000000]
 app=create_app(tmp_path/'auth.sqlite3',lambda:now[0],tmp_path/'setup.txt',mode='development')
 return app,now,tmp_path


def test_development_minimum_four_and_no_silent_shortening(env):
 app,now,path=env
 with TestClient(app) as c:
  config=c.get('/api/auth/config').json()
  assert config['minPasswordLength']==4 and config['previewSessions']
  assert c.post('/api/auth/register',json={'username':'short_reject','password':'abc','consent':True}).status_code==422
  r=c.post('/api/auth/register',json={'username':'short_ok','password':'abcd','consent':True})
  assert r.status_code==200,r.text
  assert 'previewSessionToken' not in r.json() # Requires explicit opt-in.
  assert c.post('/api/auth/login',json={'username':'short_ok','password':'abc'}).status_code==401
  assert c.post('/api/auth/login',json={'username':'short_ok','password':'abcd','consent':True}).status_code==200
  assert c.post('/api/auth/login',json={'username':'short_ok','password':'abcdextra'}).status_code==401
 with sqlite3.connect(path/'auth.sqlite3') as c:
  hashed=c.execute("SELECT password_hash FROM accounts WHERE username='short_ok'").fetchone()[0]
  assert hashed.startswith('$argon2id$') and hashed!='abcd'


def test_preview_session_without_cookies_csrf_and_logout(env):
 app,now,path=env
 with TestClient(app) as c:
  r=c.post('/api/auth/register',headers={'X-City-Preview-Session':'1'},json={'username':'no_cookie','password':'abcd','consent':True})
  assert r.status_code==200
  token=r.json()['previewSessionToken'];csrf=r.json()['csrf']
  assert len(token)>=40 and r.headers['cache-control']=='no-store'
  c.cookies.clear()
  assert c.get('/api/me').status_code==401
  c.headers['Authorization']='Bearer '+token
  assert c.get('/api/me').json()['user']['username']=='no_cookie'
  assert 'previewSessionToken' not in c.get('/api/me').json()
  assert c.get('/api/worlds').status_code==200
  assert c.post('/api/worlds/1/character',json={'nickname':'No Cookie'}).status_code==403
  c.headers['X-CSRF-Token']=csrf
  assert c.post('/api/worlds/1/character',json={'nickname':'No Cookie'}).status_code==200
  assert c.get('/api/admin/overview').status_code==403
  assert token not in c.get('/api/account/export').text
  assert c.post('/api/auth/logout',json={}).status_code==200
  assert c.get('/api/me').status_code==401
  r=c.post('/api/auth/login',headers={'X-City-Preview-Session':'1'},json={'username':'no_cookie','password':'abcd','consent':True})
  assert r.status_code==200 and r.json()['previewSessionToken']!=token
  c.cookies.clear();c.headers['Authorization']='Bearer '+r.json()['previewSessionToken']
  assert c.get('/api/me').status_code==200
  now[0]+=8*24*3600000
  assert c.get('/api/me').status_code==401


def test_invalid_bearer_cannot_fall_back_to_another_identity(env):
 app,now,path=env
 with TestClient(app) as c:
  assert c.post('/api/auth/register',json={'username':'cookie_user','password':'abcd','consent':True}).status_code==200
  assert c.get('/api/me').status_code==200
  assert c.get('/api/me',headers={'Authorization':'Bearer not-a-session'}).status_code==401
  assert c.get('/api/me',headers={'Authorization':'Basic anything'}).status_code==401


def test_production_keeps_minimum_twelve_and_disables_preview_token(tmp_path):
 app=create_app(tmp_path/'prod.sqlite3',bootstrap_path=tmp_path/'prod-setup.txt',mode='production')
 with TestClient(app,base_url='https://testserver') as c:
  config=c.get('/api/auth/config').json()
  assert config['minPasswordLength']==12 and not config['previewSessions']
  assert c.post('/api/auth/register',json={'username':'short_fail','password':'abcd','consent':True}).status_code==422
  r=c.post('/api/auth/register',headers={'X-City-Preview-Session':'1'},json={'username':'prod_user','password':'long-test-password','consent':True})
  assert r.status_code==200
  assert 'previewSessionToken' not in r.json()
  assert c.get('/api/me').status_code==200
  assert c.get('/api/me',headers={'Authorization':'Bearer ignored-even-with-valid-cookie'}).status_code==401
  c.headers['X-CSRF-Token']=r.json()['csrf']
  r=c.post('/api/auth/logout',json={})
  assert r.status_code==200
  cookie=r.headers['set-cookie']
  assert 'Secure' in cookie and 'HttpOnly' in cookie and 'Partitioned' in cookie
  assert c.get('/api/me').status_code==401


def test_old_long_password_is_still_valid_after_preview_login(env):
 app,now,path=env
 with TestClient(app) as c:
  password='a-long-old-test-password'
  assert c.post('/api/auth/register',json={'username':'long_user','password':password,'consent':True}).status_code==200
  c.cookies.clear()
  r=c.post('/api/auth/login',json={'username':'long_user','password':password,'consent':True},headers={'X-City-Preview-Session':'1'})
  assert r.status_code==200
  c.cookies.clear();c.headers['Authorization']='Bearer '+r.json()['previewSessionToken']
  assert c.get('/api/worlds').status_code==200


def test_mode_typo_is_not_treated_as_development(tmp_path):
 with pytest.raises(RuntimeError):create_app(tmp_path/'typo.sqlite3',bootstrap_path=tmp_path/'setup.txt',mode='prodction')


def test_x_city_session_header_wins_over_foreign_authorization(env):
 """Proxy podglądu może podmienić Authorization — token w X-City-Session nadal działa; zły token = 401."""
 app,now,path=env
 with TestClient(app) as c:
  r=c.post('/api/auth/register',headers={'X-City-Preview-Session':'1'},json={'username':'hdr_user','password':'abcd','consent':True})
  tok=r.json()['previewSessionToken']; c.cookies.clear()
  assert c.get('/api/me',headers={'X-City-Session':tok,'Authorization':'Basic proxy'}).status_code==200
  assert c.get('/api/me',headers={'X-City-Session':'not-a-session'}).status_code==401
