"""0.27 Hipodrom: wyliczanie wyników, bramy (poziom 5, dzielnica 6, podróż), pule 60/30/10,
puchar w Kronice Miasta (0.17) i prestiż organizacji — oraz zero realnych pieniędzy."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.economy as E
import server.sports as S

@pytest.fixture
def env(tmp_path, monkeypatch):
 clock=[1780000000000]
 app=create_app(tmp_path/'racing.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(16*86400000,))  # 0.33: hipodrom (d6) wymaga Ery III
 monkeypatch.setattr(S,'_race_seed',lambda *a:12345)  # deterministyczne wyścigi w testach
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def login(app,name):
 c=TestClient(app);r=c.post('/api/auth/login',json={'username':name,'password':'test-password-long-123'})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid=2,name='Dzokej'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def action(c,kind,wid=2,key=None,**kwargs):
 return c.post(f'/api/worlds/{wid}/actions',headers={'Idempotency-Key':key or uuid.uuid4().hex},json={'action':kind,**kwargs})

def travel_to(c,wid,target,clock):
 r=c.post(f'/api/worlds/{wid}/travel',json={'target_district':target,'mode':'bus'});assert r.status_code==200,r.text
 clock[0]+=r.json()['travel']['until']-clock[0]+1
 r=c.post(f'/api/worlds/{wid}/travel/arrive',json={});assert r.status_code==200,r.text

def grant(app,nick,cash=None,xp=None,stats=None):
 with app.state.db.read() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])
  if cash is not None:s['cash']=cash
  if xp is not None:s['xp']=xp
  if stats is not None:
   for i,v in stats.items():s['stats'][i]=v
 with app.state.db.tx() as db_c:
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def feed(app,wid=2):
 with app.state.db.read() as db_c:
  return [dict(r) for r in db_c.execute('SELECT kind,title,description FROM chronicle WHERE world_id=? ORDER BY id DESC',(wid,))]

def expected_place(nick,horse,stats,npcs=S.NPC_RUNNERS[:2]):
 entries=[dict(name=nick,speed=horse['speed'],stamina=horse['stamina'],charisma=stats[3],cunning=stats[4])]+[dict(cid=None,**n) for n in npcs]
 table=S.resolve(entries,12345)
 return next(i+1 for i,e in enumerate(table) if e['name']==nick),[e['name'] for e in table]

def ready_djockey(app,c,nick,clock,horse='champion',stats=None):
 grant(app,nick,cash=50000,xp=3600,stats=stats or {3:40,4:40})  # poziom 8 + silna charyzma/spryt
 assert action(c,'buy_residence',2,residence='studio-flat').status_code==200  # rezydencja bazowa dla treningów (nie wymagana, ale realistyczny stan)
 r=c.post('/api/worlds/2/racing/horse',json={'horse':horse});assert r.status_code==200,r.text
 travel_to(c,2,S.HIP_DISTRICT,clock)

def test_scoring_and_split(env):
 base=S.run_score(3,3,10,10,7)
 assert base==S.run_score(3,3,10,10,7)  # determinizm
 assert round(base/ (3*3+2.5*3+2*10+1.5*10),2)<=1.13  # rozstrojenie w widełkach ±12%
 table=S.resolve([dict(name='slaby',speed=1,stamina=1,charisma=1,cunning=1),dict(name='mocny',speed=8,stamina=8,charisma=30,cunning=30)],5)
 assert table[0]['name']=='mocny' and table[1]['name']=='slaby'
 assert S.split_pot(150)==(90,45,15) and sum(S.split_pot(150))==150
 assert S.SPLIT==(60,30,10)

def test_npc_race_gates_and_flow(env):
 app,clock=env;c=register(app,'junior');create(c,2,name='junior')
 assert c.post('/api/worlds/2/racing/horse',json={'horse':'mustang'}).status_code==409  # poziom<5
 grant(app,'junior',cash=5000,xp=1000)
 assert c.post('/api/worlds/2/racing/horse',json={'horse':'mustang'}).status_code==200
 r=c.post('/api/worlds/2/racing/npc',json={});assert r.status_code==409 and 'Sportowe' in r.json()['detail']  # zła dzielnica
 travel_to(c,2,S.HIP_DISTRICT,clock)
 grant(app,'junior',stats={3:30,4:30})
 r=c.post('/api/worlds/2/racing/npc',json={});assert r.status_code==200,r.text
 data=r.json()
 place,names=expected_place('junior',dict(speed=3,stamina=3),[10,10,10,30,30])
 assert data['place']==place and len(data['table'])==3
 assert [e['name'] for e in data['table']]==names
 assert data['payout']==S.split_pot(3*S.HIP_ENTRY)[place-1]
 with app.state.db.read() as db_c:
  s=json.loads(db_c.execute("SELECT state_json FROM characters WHERE nickname='junior'").fetchone()[0])
 assert s['cash']==5000-800-20-S.HIP_ENTRY+data['payout']  # koń + autobus (20) + wpisowe − nagroda; zero innych kosztów
 c.post('/api/worlds/2/travel',json={'target_district':3,'mode':'bus'})
 assert c.post('/api/worlds/2/racing/npc',json={}).status_code==409  # w drodze start niedostępny

def test_cup_chronicle_and_org_prestige(env):
 app,clock=env;c=register(app,'czempion');create(c,2,name='czempion')
 assert c.post('/api/worlds/2/organizations',json={'name':'Stajnia Kreatywna','tag':'STK','description':'Drużyna hipodromu'}).status_code==200
 ready_djockey(app,c,'czempion',clock)
 r=c.post('/api/worlds/2/racing/npc',json={});assert r.status_code==200,r.text
 assert r.json()['place']==1 and r.json()['payout']==90  # puchar: 60% z 150 $
 rows=feed(app)
 cup=[x for x in rows if x['kind']=='hipodrom']
 assert cup and 'czempion' in cup[0]['title'] and 'bez zakładów' in cup[0]['description']
 with app.state.db.read() as db_c:
  tot=db_c.execute("SELECT total FROM org_investments WHERE district='Hipodrom'").fetchone()[0]
 assert tot==S.CUP_PRESTIGE
 r=c.post('/api/worlds/2/racing/npc',json={});assert r.status_code==200 and r.json()['place']==1
 with app.state.db.read() as db_c:
  tot=db_c.execute("SELECT total FROM org_investments WHERE district='Hipodrom'").fetchone()[0]
 assert tot==2*S.CUP_PRESTIGE  # drugi puchar dokłada, nie nadpisuje
 assert len([x for x in feed(app) if x['kind']=='hipodrom'])==2

def test_duel_race_lifecycle(env):
 app,clock=env;a=register(app,'starter');create(a,2,name='Startujący')
 b=register(app,'rival');create(b,2,name='Rywal')
 ready_djockey(app,a,'Startujący',clock,horse='thoroughbred',stats={3:30,4:30})
 grant(app,'Rywal',cash=50000,xp=3600,stats={3:35,4:35})
 assert b.post('/api/worlds/2/racing/horse',json={'horse':'champion'}).status_code==200
 r=a.post('/api/worlds/2/racing/open',json={});assert r.status_code==200,r.text
 rid=r.json()['race']
 assert a.post('/api/worlds/2/racing/open',json={}).status_code==409  # drugi otwarty wyścig
 assert b.post(f'/api/worlds/2/racing/join/{rid}',json={}).status_code==409  # rywal poza dzielnicą
 travel_to(b,2,S.HIP_DISTRICT,clock)
 assert a.post(f'/api/worlds/2/racing/join/{rid}',json={}).status_code==409  # autor nie dołącza do siebie
 r=b.post(f'/api/worlds/2/racing/join/{rid}',json={});assert r.status_code==200,r.text
 data=r.json();assert len(data['table'])==3
 places={e['name']:i+1 for i,e in enumerate(data['table'])}
 pay={p:S.split_pot(150)[places[p]-1] for p in ('Startujący','Rywal')}
 with app.state.db.read() as db_c:
  row=db_c.execute('SELECT status,pot,result_json FROM horse_races WHERE id=?',(rid,)).fetchone()
  assert row[0]=='done' and row[1]==150
  ca=json.loads(db_c.execute("SELECT state_json FROM characters WHERE nickname='Startujący'").fetchone()[0])['cash']
  cb=json.loads(db_c.execute("SELECT state_json FROM characters WHERE nickname='Rywal'").fetchone()[0])['cash']
 assert ca==50000-1200-3000-20-S.HIP_ENTRY+pay['Startujący']  # rezydencja z helpera + koń + autobus + wpisowe − nagroda
 assert cb==50000-8000-20-S.HIP_ENTRY+pay['Rywal']
 winner=data['table'][0]['name']
 assert winner in [x['title'] for x in feed(app) if x['kind']=='hipodrom'][0]
 assert b.post(f'/api/worlds/2/racing/join/{rid}',json={}).status_code==409  # zakończony
 r=a.post('/api/worlds/2/racing/open',json={});rid2=r.json()['race']
 assert a.post(f'/api/worlds/2/racing/cancel/{rid2}',json={}).status_code==200
 assert b.post(f'/api/worlds/2/racing/join/{rid2}',json={}).status_code==409  # odwołany
 assert a.post('/api/worlds/2/racing/cancel/9999',json={}).status_code==404
 with app.state.db.read() as db_c:
  ca2=json.loads(db_c.execute("SELECT state_json FROM characters WHERE nickname='Startujący'").fetchone()[0])['cash']
 assert ca2==ca  # wpisowe z odwołanego wyścigu wróciło (open2 i refund się znoszą)

def test_no_real_money(env):
 app,clock=env;c=register(app,'czysty');create(c,2,name='czysty')
 ready_djockey(app,c,'czysty',clock,stats={3:40,4:40})
 for _ in range(3):assert c.post('/api/worlds/2/racing/npc',json={}).status_code==200
 with app.state.db.read() as db_c:
  assert db_c.execute('SELECT count(*) FROM shop_purchases').fetchone()[0]==0  # dev-sklep nietknięty
  shop_events=[r[0] for r in db_c.execute("SELECT DISTINCT event FROM audit WHERE event LIKE 'shop.%'")]
  race_events=[r[0] for r in db_c.execute("SELECT DISTINCT event FROM audit WHERE event LIKE 'racing.%'")]
 assert not shop_events and set(race_events)<={'racing.horse','racing.npc'}

def test_payload_lists_open_races(env):
 app,clock=env;a=register(app,'wystawiajacy');create(a,2,name='Wystawiający')
 b=register(app,'obserwator');create(b,2,name='Obserwator')
 ready_djockey(app,a,'Wystawiający',clock,horse='mustang',stats={3:20,4:20})
 assert a.post('/api/worlds/2/racing/open',json={}).status_code==200
 pa=a.get('/api/worlds/2/state').json()['racing'];pb=b.get('/api/worlds/2/state').json()['racing']
 assert pa['horse']['id']=='mustang' and pa['open']==[]  # własnych otwartych wyścigów nie ma na liście
 assert len(pb['open'])==1 and pb['open'][0]['creator']=='Wystawiający'
 assert S.BOXING['spar']==['rookie','clubmate','challenger']  # sekcja boksowa: sparingi bez zmian

def test_racing_variants_breed_and_stable(env):
 # 0.43: skoki/ujeżdżenie (wagi konkurencji), stajnia i hodowla (źrebak, cooldown 24 h)
 app,clock=env
 c=register(app,'dzokej');create(c,name='Dżokej')
 c.post('/api/worlds/2/travel',json={'target_district':6,'mode':'bus'});clock[0]+=7*3600000
 c.post('/api/worlds/2/travel/arrive',json={})
 with app.state.db.tx() as db_c:
  s=json.loads(db_c.execute("SELECT state_json FROM characters WHERE nickname='Dżokej'").fetchone()[0]);s['cash']=20000;s['xp']=3000
  db_c.execute("UPDATE characters SET state_json=? WHERE nickname='Dżokej'",(json.dumps(s),))
 r=c.post('/api/worlds/2/racing/horse',json={'horse':'mustang'});assert r.status_code==200,r.text
 r=c.post('/api/worlds/2/racing/horse',json={'horse':'thoroughbred'});assert r.status_code==200,r.text
 rp=c.get('/api/worlds/2/state').json()
 stable=[x for x in rp['racing']['stable'] if x['breed']=='mustang' or x['breed']=='thoroughbred']
 assert len(stable)==2,'dwie rasy w stajni'
 rn=c.post('/api/worlds/2/racing/npc',json={'comp':'skoki'});assert rn.status_code==200,rn.text
 ru=c.post('/api/worlds/2/racing/npc',json={'comp':'ujezdzanie'});assert ru.status_code==200,ru.text
 rw=c.post('/api/worlds/2/racing/npc',json={});assert rw.status_code==200,rw.text
 assert 'score' in rw.json()['table'][0]
 rb=c.post('/api/worlds/2/racing/breed',json={});assert rb.status_code==200,rb.text
 foal=rb.json()['foal'];assert foal['gen']==2 and foal['breed']=='foal'
 rb2=c.post('/api/worlds/2/racing/breed',json={});assert rb2.status_code==409 and '24 h' in rb2.json()['detail']
 rs=c.post('/api/worlds/2/racing/stable',json={'key':foal['key']});assert rs.status_code==200,rs.text
 assert rs.json()['horse']['name']==foal['name']
 rs2=c.post('/api/worlds/2/racing/stable',json={'key':'nie-ma'});assert rs2.status_code==404
