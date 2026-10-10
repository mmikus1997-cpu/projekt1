"""3.2 GDD v3.1: paliwo per auto — spalanie za przystanek (gracz i NPC), przesiadka do busa, tankowanie z VIP −20%."""
import json
import sqlite3
import uuid
from server import npc as N, services as S
from server import economy as E
from tests.test_npc_shift import env, player, patch, cash, post, hire, driver, H, M, T0  # noqa: F401


def st(db):
    with sqlite3.connect(db) as x:
        return json.loads(x.execute('SELECT state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0])


def act(c, **body):
    return c.post('/api/worlds/2/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json=body)


def fuel(db, car):
    return E.fuel_of(st(db), car)


def set_fuel(db, car, v):
    patch(db, lambda s: E.set_fuel(s, car, v))


# --- model i tankowanie ---
def test_defaults_and_need():
    assert E.fuel_of({}, 'sedan') == 100.0                      # brak wpisu = pełny bak (migracja bez zapisu)
    assert E.fuel_need('sedan', 0) == 3 and E.fuel_need('sedan', 2) == 6 and E.fuel_need('suv', 1) == 6
    assert E.refuel_cost({}, 'suv', 50, T0) == 150 and E.refuel_cost({'vipUntil': T0 + 1}, 'suv', 50, T0) == 120


def test_refuel_full_partial_vip_and_guards(env):
    app, clock, db = env
    c = player(app, db, 'tankowiec', garage=['sedan'], vehicle=dict(id='sedan', wear=0))
    assert act(c, action='refuel', vehicle='sedan').status_code == 409        # pełny bak
    assert act(c, action='refuel', vehicle='suv').status_code == 409          # nie ma auta
    set_fuel(db, 'sedan', 40)
    c0 = cash(db)
    r = act(c, action='refuel', vehicle='sedan', amount=20)
    assert r.status_code == 200, r.text
    assert fuel(db, 'sedan') == 60 and cash(db) == c0 - 30                    # 20% × 1,5 $
    with sqlite3.connect(db) as x:                                          # VIP z shop_state (serwer nadpisuje stan)
        acc = x.execute('SELECT account_id FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0]
        x.execute('INSERT INTO shop_state(account_id,vip_until) VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET vip_until=excluded.vip_until', (acc, T0 + H))
    r = act(c, action='refuel', vehicle='sedan')
    assert r.status_code == 200 and 'VIP' in r.json()['message']
    assert fuel(db, 'sedan') == 100 and cash(db) == c0 - 30 - 48              # 40% × 1,5 × 0,8 = 48
    set_fuel(db, 'sedan', 0); patch(db, lambda s: s.update(cash=10))
    r = act(c, action='refuel', vehicle='sedan')
    assert r.status_code == 409 and '120 $' in r.json()['detail']           # 100% × 1,5 × 0,8 (VIP)


def test_refuel_blocked_when_car_on_npc_shift(env):
    app, clock, db = env
    c = player(app, db, 'zajety', garage=['sedan'])
    set_fuel(db, 'sedan', 50)
    a = hire(c, db); driver(c, db)
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan')).status_code == 200
    r = act(c, action='refuel', vehicle='sedan')
    assert r.status_code == 409 and 'zmianie z NPC' in r.json()['detail']


# --- podróż gracza ---
def test_player_travel_burns_fuel_and_blocks_when_empty(env):
    app, clock, db = env
    c = player(app, db, 'kierowca', garage=['dostawczak'], vehicle=dict(id='dostawczak', wear=0))
    r = c.post('/api/worlds/2/travel', json={'target_district': 2, 'mode': 'car'})
    assert r.status_code == 200, r.text
    assert fuel(db, 'dostawczak') == 96                                      # 1 przystanek × 4%
    clock[0] += H
    assert c.post('/api/worlds/2/travel/arrive', json={}).status_code == 200
    set_fuel(db, 'dostawczak', 3)
    r = c.post('/api/worlds/2/travel', json={'target_district': 1, 'mode': 'car'})
    assert r.status_code == 409 and 'Za mało paliwa (3%, potrzeba 4%)' in r.json()['detail']
    assert fuel(db, 'dostawczak') == 3


# --- NPC ---
def test_npc_shift_burns_per_leg_and_returns_rest(env):
    app, clock, db = env
    c = player(app, db, 'flotowy', garage=['sedan'])
    a = hire(c, db); driver(c, db)
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))   # Centrum: 1 przystanek
    assert r.status_code == 200 and r.json()['transport'] == 'car'
    assert fuel(db, 'sedan') == 94                                           # v3.2: kurs DROP = tam + powrót na pusto (2 × 3%)
    clock[0] += 2 * H + 2 * M
    c.get('/api/worlds/2/npcs')
    assert fuel(db, 'sedan') == 88                                           # kurs PICKUP: dojazd na pusto + powrót (2 × 3%)


def test_npc_switches_to_bus_mid_shift_exact_payout(env):
    app, clock, db = env
    c = player(app, db, 'pechowiec', garage=['sedan'])
    set_fuel(db, 'sedan', 7)                                                 # v3.2: starczy na kurs DROP (6%), nie na PICKUP
    a = hire(c, db); driver(c, db)
    with sqlite3.connect(db) as x:
        x.row_factory = sqlite3.Row
        n = dict(x.execute('SELECT * FROM npcs WHERE id=?', (a,)).fetchone())
    est = N.estimate(n, S.BY_ID['minimarket'], 2, 'sedan', T0, 2, E, S, 4.0)   # ten sam przebieg: auto tam, autobus z powrotem
    c0 = cash(db)
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan')).status_code == 200
    clock[0] = T0 + 2 * H + 1000
    j = c.get('/api/worlds/2/npcs').json()['npcs'][0]
    assert j['phase'] == 'to_home' and j['bus'] and j['travelMs'] == 120_000          # autobus ×2,0
    clock[0] = est['endsAt'] + 1
    c.get('/api/worlds/2/npcs')
    assert cash(db) - c0 == est['cash']                                      # prognoza = wypłata (z biletem 20 $)
    assert fuel(db, 'sedan') == 1
    with sqlite3.connect(db) as x:
        assert x.execute("SELECT count(*) FROM game_events WHERE kind='npc.bus_fallback'").fetchone()[0] == 1


def test_fuel_out_event_in_advance():
    n = dict(id=1, character_id=1, name='A', energy=100.0, mood=100.0, hunger=100.0, unhappy_since=None, warned_at=None,
             updated_at=T0, trait='optymista')
    N.clear_shift(n)
    m = N.plan_shift(n, S.BY_ID['minimarket'], 2, 'sedan', T0, 2, E, S, 4.0)
    assert m['shift_fuel'] == 1 and not m['shift_bus']
    _, evs = N.advance(m, T0 + 2 * H + 1000, S)
    assert [e['kind'] for e in evs].count('fuel_out') == 1


def test_dispatch_with_empty_tank_goes_by_bus(env):
    app, clock, db = env
    c = player(app, db, 'pusty', garage=['sedan'])
    set_fuel(db, 'sedan', 2)
    a = hire(c, db); driver(c, db)
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert r.status_code == 200 and r.json()['transport'] == 'bus' and 'autobus' in r.json()['message']
    n = r.json()['npcs'][0]
    assert n['bus'] and n['assigned_car_id'] is None and n['fuel'] is None and fuel(db, 'sedan') == 2
    assert act(c, action='refuel', vehicle='sedan').status_code == 200        # auto wolne w garażu


def test_batch_auto_and_manager_skip_empty_cars(env):
    app, clock, db = env
    c = player(app, db, 'dyspozytor', xp=4500, garage=['dostawczak', 'sedan'])
    set_fuel(db, 'sedan', 5)                                                 # < 6% (najdłuższy odcinek)
    a, b = hire(c, db), hire(c, db)
    driver(c, db)
    j = post(c, 'npcs/batch', dict(action='dispatch', npcs=[a], service_id='minimarket', hours=2, cars='auto')).json()
    assert j['results'][0]['car'] == 'dostawczak'
    post(c, 'npcs/manager', dict(enabled=True, hours=2))
    with sqlite3.connect(db) as x:
        assert x.execute('SELECT assigned_car_id FROM npcs WHERE id=?', (b,)).fetchone()[0] is None


def test_assistant_low_fuel_and_travel_advice(env):
    app, clock, db = env
    c = player(app, db, 'doradzany', garage=['sedan'], vehicle=dict(id='sedan', wear=0))
    set_fuel(db, 'sedan', 2)
    j = c.get('/api/worlds/2/assistant').json()
    low = next(al for al in j['alerts'] if al['kind'] == 'low_fuel')
    assert low['car'] == 'sedan' and low['cost'] == 147                      # 98% × 1,5 $
    to2 = next(o for o in j['travel']['options'] if o['district'] == 2)
    assert to2['recommended'] == 'bus' and 'paliwa' in to2['why'] and to2['car']['fuelNeed'] == 3
