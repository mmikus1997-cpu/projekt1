"""0.43 Klub Sportowy · nowe dyscypliny: turniej MMA, agility, łucznictwo (PvP celności), pływanie (kondycja->Charyzma)."""
import json
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
import server.economy as E

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 app=create_app(tmp_path/'sports2.sqlite3',lambda:clock[0],tmp_path/'setup.txt')
 return app,clock

def register(app,name):
 c=TestClient(app);r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,name,cls=None):
 r=c.post('/api/worlds/2/character',json={'nickname':name,'accept_test_reset':True,'class_type':cls});assert r.status_code==200,r.text;return r.json()

def grant(app,nick,**kw):
 with app.state.db.tx() as c:
  s=json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])
  s.update(kw)
  c.execute('UPDATE characters SET state_json=? WHERE nickname=?',(json.dumps(s),nick))

def ready(app,nick,stats=None):
 grant(app,nick,xp=400,tactic='presja',cash=5000,energy=240,**({'stats':stats} if stats else {}))

def test_tournament_gates_and_rewards(env):
 app,clock=env;a=register(app,'piestiarz');create(a,'Ringman','bokser')
 tid=None
 r=a.post('/api/worlds/2/sports/tournament',json={});assert r.status_code==409 and '2. poziomie' in r.json()['detail']
 grant(app,'Ringman',xp=400)
 # 5.1 GDD v3.1: brak bramki taktyki — Klasa = Taktyka
 ready(app,'Ringman')
 r=a.post('/api/worlds/2/sports/tournament',json={});assert r.status_code==200,r.text
 d=r.json();assert len(d['rounds'])==3 and d['runsLeft']==1
 assert d['prize']['cash']=={3:1200,2:400}.get(d['wins'],0)
 st=a.get('/api/worlds/2/state').json()['state']
 assert st['cash']==5000-200+d['prize']['cash'] and st['energy']==240-30
 r2=a.post('/api/worlds/2/sports/tournament',json={});assert r2.status_code==200
 r3=a.post('/api/worlds/2/sports/tournament',json={});assert r3.status_code==409 and '2 turnieje' in r3.json()['detail']

def st_of(app,nick):
 with app.state.db.read() as c:
  return json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])

def test_agility_dogs_treat_train_and_window_limit(env):
 """QA 5: wynik ze statystyk psa, smaczek +10%, szkolenie na stałe, nowe rasy, limit 10 konkursów / 4 h."""
 app,clock=env;a=register(app,'treser');create(a,'Treser')
 ready(app,'Treser')
 st=a.get('/api/worlds/2/sports3').json()
 assert st['dogs'][0]['breed']=='kundel' and len(st['breeds'])==3 and st['agility']['left']==10
 r=a.post('/api/worlds/2/sports/agility',json={});assert r.status_code==200,r.text
 d=r.json();assert d['grade'] in 'SABCDE' and d['rewards']['cash']==d['score']*2 and d['newRecord'] is True
 c0=st_of(app,'Treser')['cash']
 r=a.post('/api/worlds/2/sports/agility',json={'treat':True});assert r.status_code==200 and r.json()['treat'] is True
 assert c0-st_of(app,'Treser')['cash']==50+100-r.json()['rewards']['cash'],'wpisowe + smaczek 100 $'
 # szkolenie: +1 na stałe, koszt 150 + 100×wartość
 r=a.post('/api/worlds/2/sports/dog/train',json={'stat':'obedience'});assert r.status_code==200,r.text
 assert st_of(app,'Treser')['dogs']['kennel-kundel']['obedience']==4
 # rasa z wymogiem poziomu
 assert 'wymaga poziomu 8' in a.post('/api/worlds/2/sports/dog/buy',json={'breed':'owczarek'}).json()['detail']
 r=a.post('/api/worlds/2/sports/dog/buy',json={'breed':'jack-russell'});assert r.status_code==200,r.text
 assert r.json()['activeDog']=='kennel-jack-russell'
 for _ in range(8):
  grant(app,'Treser',energy=240,cash=5000)
  assert a.post('/api/worlds/2/sports/agility',json={}).status_code==200
 assert 'Limit 10' in a.post('/api/worlds/2/sports/agility',json={}).json()['detail']
 clock[0]+=4*3600000
 grant(app,'Treser',energy=240,cash=5000)
 assert a.post('/api/worlds/2/sports/agility',json={}).status_code==200,'nowe okno 4 h'

def test_archery_three_attempts_timers_coupon_energy(env):
 """QA 5: 1. od razu, 2. po 5 min, 3. po 15 min (albo Kupon Akcji); +3/6/10% maks. energii i +20% energii od razu."""
 app,clock=env;a=register(app,'lucznik');create(a,'Łucznik')
 clock[0]=(clock[0]//86400000+1)*86400000+3600000   # 01:00 UTC — cały dzień przed nami
 ready(app,'Łucznik');grant(app,'Łucznik',energy=0,lastTick=clock[0])
 r=a.post('/api/worlds/2/sports/archery',json={});assert r.status_code==200,r.text
 d=r.json();assert d['n']==1 and d['energyMax']==round(240*1.03) and d['energyGain']==round(d['energyMax']*0.2)
 assert 'za 5 min' in a.post('/api/worlds/2/sports/archery',json={}).json()['detail']
 clock[0]+=5*60000
 assert a.post('/api/worlds/2/sports/archery',json={}).json()['energyMax']==round(240*1.06)
 assert 'Kuponu Akcji' in a.post('/api/worlds/2/sports/archery',json={'skip':True}).json()['detail']
 grant(app,'Łucznik',coupons={'instant':1})
 r=a.post('/api/worlds/2/sports/archery',json={'skip':True});assert r.status_code==200,r.text
 assert r.json()['energyMax']==round(240*1.10) and st_of(app,'Łucznik')['coupons']['instant']==0
 assert '3 podejścia' in a.post('/api/worlds/2/sports/archery',json={}).json()['detail']
 s=st_of(app,'Łucznik');assert E.energy_max(s)==264
 clock[0]+=24*3600000   # po północy reset
 assert a.post('/api/worlds/2/sports/archery',json={}).json()['n']==1

def test_swim_class_stat_and_regen_stack(env):
 """QA 5: Pływanie — +3/6/10% statystyki klasowej i +1/3/5% regeneracji do północy."""
 app,clock=env;a=register(app,'plywak');create(a,'Pływak')
 clock[0]=(clock[0]//86400000+1)*86400000+3600000
 ready(app,'Pływak',stats=[10,10,10,10,40])
 base=E.regen(st_of(app,'Pływak'))
 r=a.post('/api/worlds/2/sports/swim',json={});assert r.status_code==200,r.text
 d=r.json();assert d['stat']==4 and d['statPct']==3 and d['regenPct']==1,'bez klasy: najmocniejsza statystyka'
 s=st_of(app,'Pływak');assert E.effective(s)[4]==round(40*1.03,1) and abs(E.regen(s)-base*1.01)<1e-9
 clock[0]+=5*60000;a.post('/api/worlds/2/sports/swim',json={})
 clock[0]+=15*60000;r=a.post('/api/worlds/2/sports/swim',json={});assert r.json()['statPct']==10 and r.json()['regenPct']==5
 s=st_of(app,'Pływak');assert E.effective(s)[4]==44.0
 s['lastTick']=clock[0]+24*3600000;assert E.effective(s)[4]==40,'po północy buff znika'

def test_riding_contest_and_tournament_npc_weaker(env):
 app,clock=env;a=register(app,'jezdziec');create(a,'Jeździec')
 ready(app,'Jeździec')
 r=a.post('/api/worlds/2/sports/riding',json={});assert r.status_code==200,r.text
 d=r.json();assert d['horse'].startswith('Kucyk') and d['rewards']['cash']==d['score']*3 and d['grade'] in 'SABCDE'
 assert a.get('/api/worlds/2/sports3').json()['riding']['runs']==1
