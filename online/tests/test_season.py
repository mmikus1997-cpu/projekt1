"""0.34 Sezonowe Podsumowanie i kalendarz Er: spięcie 28-dniowych sezonów
rankingowych (features: season_of/SEASON_*, archiwum topki XP, tytuły kosmetyczne)
z Erami świata — kalendarz na liście światów, sezon i przejście w payloadzie ery."""
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import features

DAY=86400000

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'season.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 def age(days):
  with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(days*DAY,))
 return app,clock,age

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def worlds_era(app,c):
 return [w.get('era') for w in c.get('/api/worlds').json()['worlds'] if w['id']==2][0]

def test_world_card_era_calendar(env):
 app,clock,age=env
 a=register(app,'planista')
 e=worlds_era(app,a)
 assert e['n']==1 and e['label']=='Czas Pionierów' and e['day']==1
 assert e['next']==dict(n=2,label='Rozwój Przemysłu',districts=5,inDays=7),'kalendarz: następna era z terminem'
 assert e['season']['daysLeft']>0
 age(8)
 e=worlds_era(app,a)
 assert e['n']==2 and e['next']['n']==3 and e['next']['inDays']==6,'dzień 9: 6 dni do Ery III'
 age(20)  # dzień 29
 e=worlds_era(app,a)
 assert e['next'] is None and e['epilog'] is True and e['final'] is True,'Era IV bez następnej — epilog'

def test_era_payload_carries_global_season(env):
 app,clock,age=env
 a=register(app,'sezonowy');a.post('/api/worlds/2/character',json={'nickname':'Sezonowy','accept_test_reset':True})
 st=a.get('/api/worlds/2/state').json()
 sn=features.season_of(st['serverTime'])
 era=st['era']['season']
 assert era['n']==sn
 assert era['endsAt']==features.SEASON_ANCHOR+sn*features.SEASON_LEN,'koniec sezonu wg wspólnego zegara 28-dniowego'
 assert era['daysLeft']==-(-(era['endsAt']-st['serverTime'])//DAY)

def test_season_machinery_untouched_by_eras(env):
 app,clock,age=env
 a=register(app,'topowy');a.post('/api/worlds/2/character',json={'nickname':'Topowy','accept_test_reset':True})
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=json_set(state_json,'$.xp',5000) WHERE nickname='Topowy'")
 age(29)  # koniec pierwszego cyklu ery
 r=a.get('/api/ranking/global/season/1')
 assert r.status_code==200,r.text
 data=r.json()
 assert data['season']>=1 and data['rows'],'ranking sezonowy działa niezależnie od Er świata'
 with app.state.db.read() as c:
  arch=c.execute('SELECT season,payload FROM season_archive ORDER BY season').fetchall()
 assert len(arch)>=1,'archiwum sezonowe istnieje'
 top=__import__('json').loads(arch[-1]['payload'])
 assert any(e['nickname']=='Topowy' for e in top),'topka XP archiwizowana jak dotychczas'
 with app.state.db.read() as c:
  titles=c.execute("SELECT code,label FROM character_titles WHERE season=?",((arch[-1]['season']),)).fetchall()
 assert titles,'tytuły kosmetyczne sezonu przyznane (zero statystyk)'
