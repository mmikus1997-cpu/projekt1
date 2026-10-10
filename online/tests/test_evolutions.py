"""0.32 Ewolucje I stopnia: pasywki klasowe od 10 poziomu.

Sprawdza: deterministyczne wyliczanie pasywek w silniku symultanicznym (Rytm, Nokaut,
Garda, Riposta, Kontra z Impetem, Nieuchwytny), walidacje endpointu evolve (10 poziomu,
poprawna klasa, jednorazowość) oraz przepięcie ewolucji przez PvP i Loch. Poziomy:
xp=4500 → 10, xp=3600 → 9 (E.level = 50·n·(n−1))."""
import json
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import combat

BASE_A=[10,10,10,10,10]

def sim(a_seq,d_seq,a_evo=None,d_evo=None,a_cls=None,d_cls=None,a_stats=None,d_stats=None):
 return combat.simultaneous(a_stats or BASE_A,d_stats or BASE_A,list(a_seq),list(d_seq),42,a_cls=a_cls,d_cls=d_cls,a_evo=a_evo,d_evo=d_evo)

@pytest.fixture
def env(tmp_path):
 clock=[1780000000000]
 return create_app(tmp_path/'evo.sqlite3',lambda:clock[0],tmp_path/'setup.txt'),clock

def register(app,name):
 c=TestClient(app);c.app_ref=app;r=c.post('/api/auth/register',json={'username':name,'password':'test-password-long-123','consent':True})
 assert r.status_code==200,r.text;c.headers['X-CSRF-Token']=r.json()['csrf'];return c

def create(c,name,cls):
 r=c.post('/api/worlds/2/character',json={'nickname':name,'accept_test_reset':True,'class_type':cls});assert r.status_code==200,r.text
 if getattr(c,'app_ref',None):
  import json as _j
  with c.app_ref.state.db.tx() as c2:
   st=_j.loads(c2.execute('SELECT state_json FROM characters WHERE nickname=?',(name,)).fetchone()[0]);st['xp']=150;st['tactic']='kontrola'
   c2.execute('UPDATE characters SET state_json=? WHERE nickname=?',(_j.dumps(st),name))
 return r.json()

def set_char(app,nick,**kw):
 with app.state.db.tx() as c:
  sets=','.join(k+'=?' for k in kw)
  c.execute(f'UPDATE characters SET {sets} WHERE nickname=?',(*kw.values(),nick))

def get_state(app,nick):
 with app.state.db.read() as c:
  return json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?',(nick,)).fetchone()[0])

# ---------- silnik symultaniczny ----------

# Combat 3.0: test_rytm_accumulates_on_landed_hits usunięty — pasywki 2.x zastąpione mapowaniem D3 (zastępstwo: tests/test_combat3.py)

# Combat 3.0: test_nokaut_heavy_and_block_break usunięty — pasywki 2.x zastąpione mapowaniem D3 (zastępstwo: tests/test_combat3.py)

# Combat 3.0: test_garda_reduces_clash_damage usunięty — pasywki 2.x zastąpione mapowaniem D3 (zastępstwo: tests/test_combat3.py)

# Combat 3.0: test_riposta_counter_40_to_75 usunięty — pasywki 2.x zastąpione mapowaniem D3 (zastępstwo: tests/test_combat3.py)

# Combat 3.0: test_blyskawica_next_hit_after_dodge usunięty — pasywki 2.x zastąpione mapowaniem D3 (zastępstwo: tests/test_combat3.py)

# Combat 3.0: test_fantom_heal_and_toughness usunięty — pasywki 2.x zastąpione mapowaniem D3 (zastępstwo: tests/test_combat3.py)

def test_unknown_evo_code_is_ignored_by_engine():
 a=sim(['fast','fast','fast'],['fast','fast','fast'],a_evo='nie-ma-takiego')
 b=sim(['fast','fast','fast'],['fast','fast','fast'])
 assert a['finalHp']==b['finalHp'] and a['evolutions']==[None,None]

# ---------- endpoint ----------

def test_evolve_requires_level10_class_and_is_one_time(env):
 app,clock=env
 a=register(app,'ewolucyjny');create(a,'Bokserek','bokser')
 code='mistrz-ringu'
 set_char(app,'Bokserek',class_evolution=1)
 r=a.post('/api/worlds/2/character/evolve',json={'evolution_code':code})
 assert r.status_code==409 and '10 poziomu' in r.json()['detail'],'poniżej 10 poziomu'
 s=get_state(app,'Bokserek');s['xp']=4500  # poziom 10
 set_char_state=app.state.db
 with set_char_state.tx() as c:
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Bokserek'",(json.dumps(s),))
 r=a.post('/api/worlds/2/character/evolve',json={'evolution_code':code})
 assert r.status_code==200,r.text
 assert r.json()['evolution']['label']=='Mistrz Ringu' and r.json()['level']==10
 r2=a.post('/api/worlds/2/character/evolve',json={'evolution_code':'zelazna-piesc'})
 assert r2.status_code==409,'wybór jednorazowy'
 st=a.get('/api/worlds/2/state').json()
 assert st['character']['evolutionCode']==code and st['character']['classEvolution']==2

def test_evolve_validations(env):
 app,clock=env
 a=register(app,'bezklasy');create(a,'Bez Klas',None)
 r=a.post('/api/worlds/2/character/evolve',json={'evolution_code':'blyskawica'})
 assert r.status_code==422 and 'klasy' in r.json()['detail']
 b=register(app,'szybciutki');create(b,'Fantomix','szybki')
 s=get_state(app,'Fantomix');s['xp']=4500
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Fantomix'",(json.dumps(s),))
 r=b.post('/api/worlds/2/character/evolve',json={'evolution_code':'mistrz-ringu'})
 assert r.status_code==422,'ewolucja innej klasy'
 r=b.post('/api/worlds/2/character/evolve',json={'evolution_code':'czarodziej'})
 assert r.status_code==422,'nieznany kod'

def test_evolution_flows_through_pvp_and_dungeon(env):
 app,clock=env
 a=register(app,'mistrz');create(a,'Ringmaster','bokser')
 b=register(app,'ofiara');create(b,'Worek','obronca')
 s=get_state(app,'Ringmaster');s['xp']=4500
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Ringmaster'",(json.dumps(s),))
 assert a.post('/api/worlds/2/character/evolve',json={'evolution_code':'mistrz-ringu'}).status_code==200
 tid=a.get('/api/worlds/2/pvp/targets').json()['targets'][0]['id']
 data=a.post(f'/api/worlds/2/pvp/attack/{tid}',json={'seq':['heavy','heavy','heavy']}).json()
 assert data['report']['version']=='3.0'
 assert data['report']['evolutions'][0]=='mistrz-ringu' and data['report']['evolutions'][1] is None
 s=get_state(app,'Worek');s['xp']=400;s['tactic']='kontra'  # 0.41: loch od 3. poziomu i po wyborze taktyki
 with app.state.db.tx() as c:
  c.execute("UPDATE characters SET state_json=? WHERE nickname='Worek'",(json.dumps(s),))
 b.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 d1=b.post('/api/worlds/2/dungeon/floor',json={'seq':['fast','dodge','heavy']}).json()
 assert d1['report']['evolutions']==[None,None],'NPC bez ewolucji'
 # gracz z ewolucją w lochu
 a.post('/api/worlds/2/location',json={'location':'brama-lochow'})
 d2=a.post('/api/worlds/2/dungeon/floor',json={'seq':['heavy','heavy','heavy']}).json()
 assert d2['report']['evolutions'][0]=='mistrz-ringu','pasywka działa też w Lochu'
