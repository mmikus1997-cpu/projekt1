"""3.3 GDD v3.1: zużycie per auto, utrata bonusów przy 100%, serwis pojedynczy i Automatyczny Mechanik."""
import sqlite3
from server import economy as E, services as S
from tests.test_npc_shift import env, player, patch, cash, H, T0  # noqa: F401
from tests.test_fuel import st, act


def vip(db):
    with sqlite3.connect(db) as x:
        acc = x.execute('SELECT account_id FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0]
        x.execute('INSERT INTO shop_state(account_id,vip_until) VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET vip_until=excluded.vip_until', (acc, T0 + 10 * H))


def test_lazy_migration_moves_active_wear_only():
    s = E.new(T0); s['garage'] = ['sedan', 'suv']; s['vehicle'] = dict(id='sedan', wear=42); s.pop('wearV', None)
    E.migrate_wear(s)
    assert E.wear_of(s, 'sedan') == 42 and E.wear_of(s, 'suv') == 0 and s['wearV'] == 1


def test_wear_survives_switching_cars(env):
    app, clock, db = env
    c = player(app, db, 'przesiadka', garage=['sedan', 'suv'], vehicle=dict(id='sedan', wear=0))
    patch(db, lambda s: E.set_wear(s, 'sedan', 60))
    assert act(c, action='equip_vehicle', vehicle='suv').status_code == 200
    assert act(c, action='equip_vehicle', vehicle='sedan').status_code == 200
    s = st(db)
    assert E.wear_of(s, 'sedan') == 60 and s['vehicle']['wear'] == 60     # dawniej zmiana auta zerowała zużycie


def test_full_wear_drops_discount_and_npc_speed():
    s = E.new(T0); s['garage'] = ['suv']; s['vehicle'] = dict(id='suv', wear=0); E.migrate_wear(s)
    assert E.vehicle_discount(s) > 0
    E.set_wear(s, 'suv', 100)
    assert E.vehicle_discount(s) == 0 and s['vehicle']['wear'] == 100
    x = next(x for x in S.SERVICES if x['d'] != 1)
    assert S.travel_ms(x, 'suv', E, 1.0, True) > S.travel_ms(x, 'suv', E)  # NPC: brak przyspieszenia
    assert S.travel_ms(x, 'dostawczak', E, 1.0, True) == S.travel_ms(x, 'dostawczak', E)  # wolne auto nie zwalnia bardziej (1,2)


def test_service_single_car_by_id(env):
    app, clock, db = env
    c = player(app, db, 'serwisant', garage=['sedan', 'suv'], vehicle=dict(id='sedan', wear=0))
    assert act(c, action='service_vehicle', vehicle='suv').status_code == 409          # 0% — nic do roboty
    assert act(c, action='service_vehicle', vehicle='van').status_code == 409          # nie ma w garażu
    patch(db, lambda s: E.set_wear(s, 'suv', 30))
    c0 = cash(db)
    r = act(c, action='service_vehicle', vehicle='suv')
    assert r.status_code == 200, r.text
    assert E.wear_of(st(db), 'suv') == 0 and cash(db) == c0 - 3000               # cennik SUV


def test_auto_mechanic_all_cars_and_vip(env):
    app, clock, db = env
    c = player(app, db, 'mechanik', garage=['sedan', 'suv'], vehicle=dict(id='sedan', wear=0))
    assert act(c, action='auto_mechanic').status_code == 409                       # wszystko sprawne
    patch(db, lambda s: (E.set_wear(s, 'sedan', 100), E.set_wear(s, 'suv', 20)))
    c0 = cash(db)
    r = act(c, action='auto_mechanic')
    assert r.status_code == 200, r.text
    s = st(db)
    assert E.wear_of(s, 'sedan') == 0 and E.wear_of(s, 'suv') == 0 and s['vehicle']['wear'] == 0 and cash(db) == c0 - 2000
    vip(db); patch(db, lambda s: E.set_wear(s, 'suv', 50))
    c0 = cash(db)
    r = act(c, action='auto_mechanic')
    assert r.status_code == 200 and 'VIP' in r.json()['message'] and cash(db) == c0 - 1000
    patch(db, lambda s: (E.set_wear(s, 'suv', 50), s.update(cash=500)))
    r = act(c, action='auto_mechanic')
    assert r.status_code == 409 and '1000 $' in r.json()['detail']
