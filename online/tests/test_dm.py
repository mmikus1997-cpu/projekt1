"""0.38 DM z mapy: wątki dwojga mieszkańców, blokady, mute, limity (3 s / 30 h)."""
import pytest
from fastapi.testclient import TestClient
from server.app import create_app

@pytest.fixture
def env(tmp_path):
    clock=[1780000000000]
    app=create_app(tmp_path/'dm.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
    return app,clock

def register(app,name):
    c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
    assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid,name):
    r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def char_id(c,name):
    rows=c.get('/api/worlds/1/players').json()['players']
    return next(p['id'] for p in rows if p['nickname']==name)

def test_dm_flow(env):
    app,clock=env
    a=register(app,'anna');create(a,1,'Ania')
    b=register(app,'bart');create(b,1,'Bartek')
    bid=char_id(a,'Bartek')
    r=a.post('/api/worlds/1/dm/%d'%bid,json={'text':'Hej z mapy! Widzę Cię w Centrum.'});assert r.status_code==200,r.text
    t=a.get('/api/worlds/1/dm/%d'%bid).json()
    assert t['partner']['nickname']=='Bartek' and t['partner']['online'] is True
    assert len(t['messages'])==1 and t['messages'][0]['mine'] and 'mapy' in t['messages'][0]['body']
    lst=b.get('/api/worlds/1/dm').json()['threads']
    assert len(lst)==1 and lst[0]['pid']==char_id(b,'Ania') and lst[0]['mine'] is False and lst[0]['last'].endswith('Centrum.')
    clock[0]+=4000
    r=b.post('/api/worlds/1/dm/%d'%char_id(b,'Ania'),json={'text':'Siema, widzę Cię też!'});assert r.status_code==200,r.text
    t=a.get('/api/worlds/1/dm/%d'%bid).json()
    assert [m['mine'] for m in t['messages']]==[True,False]

def test_dm_self_and_missing(env):
    app,clock=env
    a=register(app,'celina');create(a,1,'Celina')
    me=char_id(a,'Celina')
    assert a.get('/api/worlds/1/dm/%d'%me).status_code==409
    assert a.post('/api/worlds/1/dm/%d'%me,json={'text':'halo'}).status_code==409
    assert a.get('/api/worlds/1/dm/999999').status_code==404
    assert a.post('/api/worlds/1/dm/999999',json={'text':'halo'}).status_code==404

def test_dm_blocks_symmetric(env):
    app,clock=env
    a=register(app,'ela');create(a,1,'Ela')
    b=register(app,'franek');create(b,1,'Franek')
    aid,bid=char_id(a,'Ela'),char_id(a,'Franek')
    r=a.post('/api/worlds/1/blocks',json={'target_id':bid});assert r.status_code==200,r.text
    assert a.get('/api/worlds/1/dm/%d'%bid).status_code==409
    assert a.post('/api/worlds/1/dm/%d'%bid,json={'text':'halo'}).status_code==409
    assert b.post('/api/worlds/1/dm/%d'%aid,json={'text':'czesc'}).status_code==409  # symetrycznie
    b_acc=b.get('/api/me').json()['user']['id']
    r=a.post('/api/account/blocks/remove',json={'account_id':b_acc});assert r.status_code==200,r.text
    assert a.post('/api/worlds/1/dm/%d'%bid,json={'text':'odblokowane'}).status_code==200

def test_dm_unread_and_packet(env):
    app,clock=env
    a=register(app,'irena');create(a,1,'Irena')
    b=register(app,'janek');create(b,1,'Janek')
    aid=char_id(a,'Irena')
    st=b.get('/api/worlds/1/state').json()
    assert st['dmUnread']==0
    r=a.post('/api/worlds/1/dm/%d'%char_id(a,'Janek'),json={'text':'masz nową wiadomość'});assert r.status_code==200,r.text
    # Janek: packet ma licznik, lista wątków pokazuje unread=1
    assert b.get('/api/worlds/1/state').json()['dmUnread']==1
    th=b.get('/api/worlds/1/dm').json()['threads']
    assert th[0]['unread']==1 and th[0]['nickname']=='Irena'
    # badge: eventsUnread+dmUnread liczone po stronie UI; tu API: odczyt wątku zeruje
    b.get('/api/worlds/1/dm/%d'%aid).raise_for_status()
    assert b.get('/api/worlds/1/state').json()['dmUnread']==0
    th=b.get('/api/worlds/1/dm').json()['threads']
    assert th[0]['unread']==0
    # nadawca nie dostaje unread od własnej wiadomości
    assert a.get('/api/worlds/1/state').json()['dmUnread']==0

def test_dm_limits_and_mute(env):
    app,clock=env
    a=register(app,'gosia');create(a,1,'Gosia')
    b=register(app,'heniek');create(b,1,'Heniek')
    bid=char_id(a,'Heniek')
    assert a.post('/api/worlds/1/dm/%d'%bid,json={'text':'#1'}).status_code==200
    clock[0]+=1000
    assert a.post('/api/worlds/1/dm/%d'%bid,json={'text':'#2 za szybko'}).status_code==429
    clock[0]+=4000
    assert a.post('/api/worlds/1/dm/%d'%bid,json={'text':'#3 ok'}).status_code==200
    with app.state.db.tx() as c:c.execute('INSERT OR REPLACE INTO chat_mutes(account_id,until_at) VALUES((SELECT account_id FROM characters WHERE id=?),?)',(bid,clock[0]+600000))
    clock[0]+=4000
    assert b.post('/api/worlds/1/dm/%d'%char_id(b,'Gosia'),json={'text':'zmuteowany'}).status_code==403
    clock[0]+=4000
    sent=2
    while sent<30:
        clock[0]+=4000
        assert a.post('/api/worlds/1/dm/%d'%bid,json={'text':'spam %d'%sent}).status_code==200;sent+=1
    clock[0]+=4000
    r=a.post('/api/worlds/1/dm/%d'%bid,json={'text':'#31'})
    assert r.status_code==429 and '30' in r.json()['detail']
