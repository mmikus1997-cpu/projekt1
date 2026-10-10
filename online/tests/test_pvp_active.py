"""0.28 Wyzwania PvP 2.0: klasy w walce symultanicznej, lista celów bez statystyk,
szablon obrony, limit 5 walk/dobę, aktualizacja Elo i zdarzenie dla obrońcy."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.economy as E
from server import combat as C

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'pvp.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 with app.state.db.tx() as c:c.execute('UPDATE worlds SET created_at=created_at-?',(9*86400000,))  # 0.33 Er-y
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,wid=2,name='Bokser'):
 r=c.post(f'/api/worlds/{wid}/character',json={'nickname':name,'accept_test_reset':True});assert r.status_code==200,r.text;return r.json()

def grant(app,nick,cash=None,stats=None,defense=None,travel=False,tactic=None,xp=None):
 with app.state.db.tx() as db_c:
  s=json.loads(db_c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])
  if cash is not None:s['cash']=cash
  if stats is not None:s['stats']=stats
  if defense is not None:s['pvpDefense']=defense
  if tactic is not None:s['tactic']=tactic
  if xp is not None:s['xp']=xp
  if travel:s['lastTick']=s['lastAction']=1780000000000
  db_c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def targets(c,wid=2,district=None):
 url=f'/api/worlds/{wid}/pvp/targets'+('?district='+str(district) if district is not None else '')
 return c.get(url).json()

def attack(c,wid,tid,payload=None):
 return c.post(f'/api/worlds/{wid}/pvp/attack/{tid}',json=payload or {})  # 0.42: payload ignorowany

def char_row(app,nick):
 with app.state.db.read() as db_c:
  return db_c.execute('SELECT rating,wins,losses,draws FROM characters WHERE nickname=?',(nick,)).fetchone()

def test_engine_classes(env):
 app,clock=env
 box=[60,10,10,20,10]  # Bokser: dominanta Siła
 defn=[10,50,10,30,10]  # Obrońca: dominanta Inteligencja
 r=C.simultaneous(box,defn,['mocny_cios']*3,['unik']*3,7)
 assert r['classes']==['Bokser','Obrońca'] and r['winner'] in (0,1) and min(r['finalHp'])==0  # Combat 3.0: sekwencje ignorowane, walka do KO
 fast=[30,10,50,20,30]  # Szybki: dominanta Refleks
 mid=[30,10,40,20,20]
 r2=C.simultaneous(fast,mid,['szybki_cios']*3,['szybki_cios']*3,9)
 assert r2['classes'][0]=='Szybki' and r2['winner'] in (0,1)  # Combat 3.0: inicjatywa losowana co rundę (Refleks + U(0,20), Szybki +5)
 r3=C.simultaneous(box,fast,['mocny_cios']*3,['mocny_cios']*3,5)
 assert r3['finalHp'][1]<r3['hpStart'][1]  # Combat 3.0: obrażenia z rzutów broni
 assert C.simultaneous(box,defn,['mocny_cios']*3,['unik']*3,7)==C.simultaneous(box,defn,['mocny_cios']*3,['unik']*3,7)  # determinizm

def test_targets_hide_stats_and_class(env):
 app,clock=env;a=register(app,'scout');create(a,2,name='Scout')
 b=register(app,'boxer');create(b,2,name='Twardy')
 d=register(app,'defender');create(d,2,name='Mur')
 grant(app,'Twardy',stats=[50,10,10,20,10])
 grant(app,'Mur',stats=[10,50,10,30,10])
 grant(app,'Scout',stats=[20,20,20,20,20])
 with app.state.db.tx() as db_c:  # skórka konta Twardego (dev-sklep, pozycja kosmetyczna)
  acc=db_c.execute('SELECT account_id FROM characters WHERE nickname=?',('Twardy',)).fetchone()[0]
  db_c.execute("INSERT INTO shop_state(account_id,spending_enabled,skin) VALUES(?,1,'skin_copper') ON CONFLICT(account_id) DO UPDATE SET skin='skin_copper'",(acc,))
 data=targets(a,2,district=1)['targets']
 names={t['nickname']:t for t in data}
 assert set(names)>={'Twardy','Mur'} and 'Scout' not in names  # siebie nie widać na liście
 tw=names['Twardy']
 assert set(tw)== {'id','nickname','level','cls','rating','skin','district','avatar'}  # zero statystyk w payload; 0.47: + awatar
 assert tw['cls']=='Bokser' and names['Mur']['cls']=='Obrońca'
 assert tw['rating']==1000 and tw['skin']=='skin_copper'
 assert all('stats' not in t and 'state' not in t for t in data)
 assert targets(a,2,district=2)['targets']==[]  # dzielnica pusta — nikt tam nie mieszka
 assert targets(a,2)['targets']  # „ogólna arena": wszyscy aktywni

def test_attack_flow_class_tactics_and_elo(env):
 # 5.1 GDD v3.1: Klasa = Taktyka — obie strony walczą sekwencją swojej klasy; szablon obrony i payload ignorowane
 app,clock=env;a=register(app,'agresor');create(a,2,name='Agresor')
 b=register(app,'tarcza');create(b,2,name='Tarcza')
 grant(app,'Agresor',stats=[60,10,10,20,10],xp=400)          # dominanta Siła → Bokser → Presja
 grant(app,'Tarcza',stats=[10,50,10,30,10],defense=['dodge']*3)  # Obrońca → Kontrola (stary szablon nie działa)
 r=attack(a,2,_cid(app,'Tarcza'),{'seq':['mocny_cios','mocny_cios','mocny_cios']})
 assert r.status_code==200,r.text
 data=r.json();rep=data['report']
 assert rep['classes']==['Bokser','Obrońca'] and rep['tactics']==['presja','kontrola'] and rep['advantage']==[False,False]  # Combat 3.0: bez RPS
 assert rep['winner'] in (0,1) and min(rep['finalHp'])==0                       # do 0 HP — KO
 assert rep['ranked'] is True and rep['names']==['Agresor','Tarcza']
 rc=data['ratingChanges'];assert abs(rc[0])==12 and rc[0]==-rc[1]
 ra,rb=char_row(app,'Agresor'),char_row(app,'Tarcza')
 assert ra['rating']==1000+rc[0] and rb['rating']==1000+rc[1]
 with app.state.db.read() as db_c:
  stored=json.loads(db_c.execute('SELECT report_json FROM pvp_battles WHERE id=?',(data['battle'],)).fetchone()[0])
  rd=stored['rounds'][0]
  assert {'attacker_action','defender_reaction','result','exchanges','fatigue'}<=set(rd)   # logi pod animacje Fluttera
  ev=db_c.execute("SELECT kind,payload FROM game_events WHERE character_id=? ORDER BY id DESC LIMIT 1",(_cid(app,'Tarcza'),)).fetchone()
  expected='win' if rep['winner']==1 else 'loss'
  assert ev[0]=='pvp_attacked' and json.loads(ev[1])['result']==expected
  assert {u for _,u in db_c.execute('SELECT character_id,used FROM ranked_usage').fetchall()}=={1}

def test_attack_gates_level_only(env):
 app,clock=env;a=register(app,'niz');create(a,2,name='Niz')
 b=register(app,'cel');create(b,2,name='Cel')
 tid=_cid(app,'Cel')
 r=attack(a,2,tid);assert r.status_code==409 and '2. poziomie' in r.json()['detail'],'PvP od 2 lvl także w auto-ataku'
 grant(app,'Niz',xp=400)
 r=attack(a,2,tid);assert r.status_code==200,r.text                             # 1-Click: bez wyboru taktyki

def test_daily_limit_fifteen_and_pair_four(env):
 app,clock=env;a=register(app,'hunter');create(a,2,name='Hunter')
 foes=[]
 for i in range(6):
  c=register(app,'foe'+str(i));create(c,2,name='Foe'+str(i));foes.append(_cid(app,'Foe'+str(i)))
 grant(app,'Hunter',xp=400)
 for i in range(4):assert attack(a,2,foes[0]).status_code==200
 r=attack(a,2,foes[0]);assert r.status_code==409 and '4 razy' in r.json()['detail']   # 5.3: 5. walka z tym samym — blokada
 for i in range(11):
  r=attack(a,2,foes[1+i%4]);assert r.status_code==200,r.text
 r=attack(a,2,foes[5])
 assert r.status_code==409 and '15 walk' in r.json()['detail']                        # 5.3: limit 15/dobę UTC
 with app.state.db.read() as db_c:
  used=db_c.execute('SELECT used FROM ranked_usage WHERE character_id=?',(_cid(app,'Hunter'),)).fetchone()[0]
 assert used==15

def test_gates_self_and_travel(env):
 app,clock=env;a=register(app,'podroznik');create(a,2,name='Podroznik')
 b=register(app,'cel');create(b,2,name='Cel')
 me=_cid(app,'Podroznik')
 grant(app,'Podroznik',tactic='presja',xp=400)
 assert attack(a,2,me).status_code==409  # nie atakujesz siebie
 a.post('/api/worlds/2/travel',json={'target_district':4,'mode':'bus'})
 r=attack(a,2,_cid(app,'Cel'));assert r.status_code==409
 assert 'Jesteś w drodze' in r.json()['detail']
 with app.state.db.tx() as db_c:  # leniwy settle podróży atakującego
  db_c.execute('UPDATE characters SET travel_destination=NULL,travel_until=NULL,travel_mode=NULL WHERE id=?',(me,))
 r=attack(a,2,_cid(app,'Cel'));assert r.status_code==200,r.text  # po przyjeździe atak działa
 b.post('/api/worlds/2/travel',json={'target_district':3,'mode':'bus'})
 r=attack(a,2,_cid(app,'Cel'));assert r.status_code==409
 assert 'Cel jest w drodze' in r.json()['detail']  # cel w drodze jest nietykalny

def _cid(app,nick):
 with app.state.db.read() as db_c:
  return db_c.execute('SELECT id FROM characters WHERE nickname=?',(nick,)).fetchone()[0]

def test_rewards_both_sides(env):
 """5.3 GDD v3.1: wygrana 500 $/50 XP/+1 PP, przegrana 100 $/10 XP, remis 200 $/25 XP — obie strony."""
 from server import pvp as P
 app,clock=env;a=register(app,'rew_a');create(a,2,name='RewA');b=register(app,'rew_b');create(b,2,name='RewB')
 grant(app,'RewA',xp=400);grant(app,'RewB',xp=400)
 def snap(n):
  with app.state.db.read() as c:
   r=c.execute('SELECT ch.state_json,a.prestige_points FROM characters ch JOIN accounts a ON a.id=ch.account_id WHERE ch.nickname=?',(n,)).fetchone()
  s=json.loads(r[0]);return s['cash'],s['xp'],r[1]
 before=[snap('RewA'),snap('RewB')]
 r=attack(a,2,_cid(app,'RewB'));assert r.status_code==200,r.text
 rw=r.json()['rewards'];w=r.json()['report']['winner']
 exp=[('draw' if w is None else 'win' if w==i else 'loss') for i in (0,1)]
 assert [x['result'] for x in rw]==exp
 for i,n in enumerate(('RewA','RewB')):
  R=P.PVP_REWARDS[exp[i]];c0,x0,p0=before[i];c1,x1,p1=snap(n)
  assert c1-c0==R['cash'] and x1-x0==R['xp'] and p1-p0==R['prestige']
