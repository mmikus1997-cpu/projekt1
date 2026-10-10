"""0.47/0.48 Awatary: katalog (kosmetyki + gameLooks), reguły noszenia (sloty, konflikty,
covers), płeć sylwetki (m/k), sprzęt startowy, kreacja z wyglądem, garderoba (kupno/przymiarka/
VIP), rankingi konta, awatary i gear w raportach PvP. Wygląd to wyłącznie prezentacja."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.economy as E
from server import avatar as AV

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'av.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(9*86400000,))
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid=2,name='Bokser',avatar=None):
 payload={'nickname':name,'accept_test_reset':True}
 if avatar is not None:payload['avatar']=avatar
 r=c.post(f'/api/worlds/{wid}/character',json=payload);assert r.status_code==200,r.text;return r.json()

def grant(app,nick,cash=None,xp=None,tactic=None):
 with app.state.db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])
  if cash is not None:s['cash']=cash
  if xp is not None:s['xp']=xp
  if tactic is not None:s['tactic']=tactic
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def test_catalog_shape(env):
 app,clock=env;a=register(app,'cat'+uuid.uuid4().hex[:6])
 cat=a.ok('/api/avatar/catalog') if hasattr(a,'ok') else a.get('/api/avatar/catalog').json()
 items=cat['items']
 cats=[k for k in items if k!='__flat']
 assert len(cats)==14
 assert all(len(items[k])==10 for k in cats)
 assert sum(1 for k in cats for it in items[k] if it['vip'])==14*3
 assert len(AV.GAME_LOOKS)==len(E.ITEMS)+len(E.DUNGEON_ITEMS)
 assert set(cat['bodies']['genders'])=={'m','k'}

def test_validate_rules_and_slots(env):
 app,clock=env
 # ta sama kategoria podmienia; konfliktowe (cap/hat, pants/shorts) zamieniają się slotowo po stronie serwera
 a=register(app,'val'+uuid.uuid4().hex[:6])
 ok,_=AV.validate({'body':{'gender':'m','skin':1,'hair':2,'hairColor':3},'worn':{'cap':'cp1','shirt':'ts1'}},False,set(),True)
 assert ok and ok['worn']['cap']=='cp1'
 ok2,_=AV.validate({'body':{'gender':'m','skin':1,'hair':2,'hairColor':3},'worn':{'cap':'cp1','hat':'ht1'}},False,set(),True)
 assert ok2['worn'].get('hat')=='ht1' and 'cap' not in ok2['worn']  # slot head: nowa rzecz zastępuje
 ok3,err=AV.validate({'body':{'gender':'x'},'worn':{}},False,set(),True)
 assert ok3 is None and 'Płeć' in err

def test_game_looks_compose(env):
 # hełm zdejmuje czapkę/kapelusz, amulet naszyjnik, strój koszulkę; covers bez samozakryć
 st={'avatar':{'body':{'gender':'k','skin':2,'hair':4,'hairColor':1},'worn':{'cap':'cp1','shirt':'ts1','necklace':'nk1'},'owned':['cp1','ts1','nk1']},
     'equipped':{'gloves':'basic-gloves','shirt':'basic-shirt','shoes':'basic-shoes','helmet':'basic-helmet','backpack':'basic-backpack','amulet':'basic-amulet','accessory':'basic-accessory'}}
 layers,_=AV.compose(st)
 assert 'cap' not in layers and 'shirt' not in layers and 'necklace' not in layers
 assert layers['helmet']=='basic-helmet' and layers['outfit']=='basic-shirt' and layers['amulet']=='basic-amulet'
 for k in ('gloves','shoes','backpack','band'):
  assert k in layers,k

def test_gender_brief_and_legacy(env):
 # nowa płeć przechodzi; stare postacie (bez gender) → 'm'
 st={'avatar':{'body':{'skin':0,'hair':1,'hairColor':0},'worn':{}}}
 assert AV.brief(st)['body']['gender']=='m'
 st2={'avatar':{'body':{'gender':'k','skin':0,'hair':1,'hairColor':0},'worn':{}}}
 assert AV.brief(st2)['body']['gender']=='k'

def test_new_gear_slots(env):
 app,clock=env
 # nowa postać startuje ubrana: 7 slotów basic, które widać na awatarze
 a=register(app,'gear'+uuid.uuid4().hex[:6])
 create(a,2,'Ubrana47')
 with app.state.db.read() as c:
  s=json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',('Ubrana47',)).fetchone()[0])
 eq=s['equipped']
 assert set(eq)=={'gloves','shirt','shoes','accessory','helmet','backpack','amulet'}
 assert all(v.startswith('basic-') for v in eq.values())
 assert set(s['inventory'])==set(eq.values())
 layers,_=AV.compose(s)
 assert layers.get('helmet')=='basic-helmet'

def test_creation_with_avatar(env):
 app,clock=env
 a=register(app,'cre'+uuid.uuid4().hex[:6])
 r=create(a,2,'Awatarka',avatar={'body':{'gender':'k','skin':3,'hair':4,'hairColor':6},'worn':{'shirt':'ts2','hat':'ht2'}})
 assert r['character']['nickname']=='Awatarka'
 with app.state.db.read() as c:
  s=json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',('Awatarka',)).fetchone()[0])
 assert s['avatar']['body']['gender']=='k' and s['avatar']['worn']['hat']=='ht2'

def test_wardrobe_buy_wear_vip(env):
 app,clock=env
 a=register(app,'war'+uuid.uuid4().hex[:6])
 create(a,2,'Modnisia')
 grant(app,'Modnisia',cash=5000,xp=600)  # poziom + kasa na zakupy
 r=a.post('/api/worlds/2/wardrobe',json={'item':'cp1'})
 assert r.status_code==200,r.text
 r=a.post('/api/worlds/2/avatar',json={'avatar':{'body':{'gender':'k','skin':1,'hair':1,'hairColor':1},'worn':{'cap':'cp1'}}})
 assert r.status_code==200,r.text
 # VIP: pierwsza rzecz VIP w kategorii cap to cp8 (3 ostatnie = VIP)
 with app.state.db.tx() as c:
  c.execute("UPDATE shop_state SET vip_until=4102444800000 WHERE account_id=(SELECT account_id FROM characters WHERE nickname='Modnisia')")
 r=a.post('/api/worlds/2/wardrobe',json={'item':'cp8'})
 assert r.status_code==200,r.text

def test_account_rankings(env):
 app,clock=env
 a=register(app,'ran'+uuid.uuid4().hex[:6])
 create(a,2,'Rankingowa')
 r=a.get('/api/account/rankings')
 assert r.status_code==200
 data=r.json()
 assert 'globalTop' in data and 'myGlobal' in data

def test_pvp_report_has_avatars(env):
 app,clock=env
 a=register(app,'pva'+uuid.uuid4().hex[:6]);b=register(app,'pvb'+uuid.uuid4().hex[:6])
 create(a,2,'Uderzacz',avatar={'body':{'gender':'m','skin':0,'hair':1,'hairColor':0},'worn':{'glasses':'gl3'}})
 create(b,2,'Pancerz')
 grant(app,'Uderzacz',xp=600,tactic='kontrola');grant(app,'Pancerz',xp=600)
 r=a.post('/api/worlds/2/pvp/attack/'+str(_cid(app,'Pancerz')),json={})
 assert r.status_code==200,r.text
 rep=r.json()['report']
 assert 'avatars' in rep and 'gear' in rep
 assert rep['avatars'][0]['body']['gender']=='m'
 assert rep['avatars'][0]['layers'].get('glasses')=='gl3'
 assert rep['gear'][0].get('gloves')=='basic-gloves'

def _cid(app,nick):
 with app.state.db.read() as c:return c.execute('SELECT id FROM characters WHERE nickname=?',(nick,)).fetchone()[0]

def test_avatar_catalog_requires_auth(env):
 app,clock=env
 c=TestClient(app)
 r=c.get('/api/avatar/catalog')
 assert r.status_code==401

def test_pvp_panel_my_org(env):
 app,clock=env
 # 0.48: panel PvP dźwiga moją organizację + prawo zapraszania (lider/officer)
 a=register(app,'org'+uuid.uuid4().hex[:6]);b=register(app,'org2'+uuid.uuid4().hex[:6])
 create(a,2,'Liderka');create(b,2,'Samotna')
 r=a.post('/api/worlds/2/organizations',json={'name':'Gildia Test','tag':'GT','description':'Testowa'})
 assert r.status_code==200,r.text
 pvp=a.get('/api/worlds/2/pvp').json()
 assert pvp['myOrg'] and pvp['myOrg']['canInvite'] is True and pvp['myOrg']['tag']=='GT'
 pvp2=b.get('/api/worlds/2/pvp').json()
 assert pvp2['myOrg'] is None
