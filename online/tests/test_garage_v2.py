"""3.1 GDD v3.1: migracja aut z katalogu 0.59 (po typie: rower→dostawczak, bus→van, supercar→suv) + SQL npcs/vehicles."""
import json
import sqlite3
from server import economy as E
from server.app import create_app
from tests.test_routes import env, register, create, action, state, set_state, cid_of  # noqa: F401


def legacy(**extra):
    s = E.new(1780000000000)
    s.update(dict(garage=['rower', 'sedan', 'furgonetka', 'bus', 'supercar'], vehicle=dict(id='supercar', wear=37),
                  garageUp={'rower': 2, 'supercar': 1}, travelCar='bus',
                  npcRoutes=dict(runs=[dict(route='courier', vehicle='rower', start=0, end=1)], done=0, cash=0, xp=0)), **extra)
    s.pop('garageV', None)
    return s


def test_migrate_maps_by_type_and_is_idempotent():
    s = legacy()
    assert E.migrate_garage(s) is True
    assert s['garage'] == ['dostawczak', 'sedan', 'furgonetka', 'van', 'suv']
    assert s['vehicle'] == dict(id='suv', wear=37)                 # zużycie zostaje
    assert s['garageUp'] == {'dostawczak': 2, 'suv': 1}
    assert s['travelCar'] == 'van' and s['npcRoutes']['runs'][0]['vehicle'] == 'dostawczak'
    assert s['garageV'] == E.GARAGE_V
    snap = json.dumps(s, sort_keys=True)
    assert E.migrate_garage(s) is False and json.dumps(s, sort_keys=True) == snap


def test_no_value_lost():
    old = {'rower': 600, 'furgonetka': 2400, 'sedan': 4200, 'bus': 7000, 'supercar': 16000}
    for vid, price in old.items():
        assert E.car(E.LEGACY_CARS.get(vid, vid))['price'] >= price


def test_new_state_needs_no_migration():
    s = E.new(1780000000000)
    E.sync(s, 1780000000000, 1)
    assert s['garageV'] == E.GARAGE_V


def test_lazy_migration_on_read_and_inflight_route_pays(env):
    app, clock, path = env
    c = register(app, 'g2_lazy')
    create(c)
    cid = cid_of(c)
    with sqlite3.connect(app.state.db.path) as db:
        st = json.loads(db.execute('SELECT state_json FROM characters WHERE id=?', (cid,)).fetchone()[0])
        st.pop('garageV', None)
        st.update(cash=0, xp=0, garage=['rower'], vehicle=dict(id='rower', wear=0),
                  npcRoutes=dict(runs=[dict(route='courier', vehicle='rower', start=0, end=clock[0] - 1)], done=0, cash=0, xp=0))
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st), cid))
    s = state(c)['state']
    assert s['garage'] == ['dostawczak'] and s['vehicle']['id'] == 'dostawczak'
    assert action(c, 'route_claim').status_code == 200
    assert state(c)['state']['cash'] == 153                        # 180 × 0,85 (VEH_MULT dostawczaka = dawny rower)


def test_sql_migration_npcs_and_vehicles(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    c = register(app, 'g2_sql')
    create(c)
    cid = cid_of(c)
    with sqlite3.connect(app.state.db.path) as db:
        db.execute("INSERT INTO npcs(character_id,name,avatar,hired_at,updated_at,assigned_car_id) VALUES(?,?,?,?,?,?)",
                   (cid, 'Ania', 'npc-01', clock[0], clock[0], 'supercar'))
        db.execute("INSERT INTO vehicles(character_id,type,condition,speed_bonus) VALUES(?,?,?,?)", (cid, 'bus', 80, 30))
    create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 's.txt')   # restart = migracja przy starcie
    with sqlite3.connect(app.state.db.path) as db:
        assert db.execute('SELECT assigned_car_id FROM npcs').fetchone()[0] == 'suv'
        assert db.execute('SELECT type FROM vehicles').fetchone()[0] == 'van'


def test_bonus_car_takes_no_slot(env):
    app, clock, path = env
    c = register(app, 'g2_slot')
    create(c)
    set_state(app, cid_of(c), {'cash': 10000, 'garage': ['mistrz'], 'vehicle': dict(id='mistrz', wear=0)})
    assert action(c, 'buy_vehicle', vehicle='dostawczak').status_code == 200   # cap 1 bez rezydencji, mistrz się nie liczy
    assert action(c, 'equip_vehicle', vehicle='mistrz').status_code == 200
