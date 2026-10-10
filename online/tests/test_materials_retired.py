"""2.1c GDD v3.1: surowce wycofane — gather/sell_materials zwracają 409, zapasy znikają bez rekompensaty,
Przemysłowe/Kopalnia/Lasy Wschodnie (2/7/8) zawsze dostępne (usługi od Ery I)."""
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import economy as E

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'retired.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 return app,clock

def player(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf']
 assert c.post('/api/worlds/2/character',json={'nickname':name.title(),'accept_test_reset':True}).status_code==200
 return c

def act(c,**payload):
 return c.post('/api/worlds/2/actions',headers={'Idempotency-Key':uuid.uuid4().hex},json=payload)

def test_gather_and_sell_are_retired(env):
 app,_=env;a=player(app,'kopacz')
 for p in (dict(action='gather',material='tworzywa'),dict(action='sell_materials',material='ruda')):
  r=act(a,**p);assert r.status_code==409 and r.json()['detail']==E.MATERIALS_RETIRED_MSG

def test_catalog_has_no_materials(env):
 app,_=env;a=player(app,'katalog')
 cat=a.get('/api/worlds/2/state').json()['catalog']
 assert cat['materials']=={} and cat['matBuy']=={} and cat['matBase']=={}
 assert not hasattr(E,'MATERIALS') and not hasattr(E,'mat_price')

def test_legacy_stock_dropped_without_compensation():
 s=E.new(0);s['materials']=dict(tworzywa=50,ruda=10,drewno=3);cash=s['cash']
 E.sync(s,0,1)
 assert 'materials' not in s and s['cash']==cash

def test_market_event_replaced():
 ids=[e['id'] for e in E.TIMED_EVENTS]
 assert 'market' not in ids and 'service_rush' in ids and len(ids)==4
 assert all(e['effect']!='mat_cash' for e in E.TIMED_EVENTS)

@pytest.mark.parametrize('target',[2,7,8])
def test_always_open_in_era_one(env,target):
 app,_=env;a=player(app,f'podroznik{target}')
 r=a.post('/api/worlds/2/travel',json={'target_district':target,'mode':'bus'})
 assert r.status_code==200,r.text
