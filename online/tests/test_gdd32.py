"""GDD v3.2: role NPC (SERVICE/DRIVER), limit 20, logistyka kursów, Taxi, cechy kierowcy, lojalność."""
import json
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import npc as N, services as S
from server import economy as E

H = 3_600_000
M = 60_000
T0 = 1780000000000


@pytest.fixture
def env(tmp_path):
    clock = [T0]
    db = tmp_path / 'v32.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, db


def player(app, db, name, **state):
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/2/character', json={'nickname': name.title(), 'accept_test_reset': True}).status_code == 200
    patch(db, lambda s: s.update({'cash': 50000, **state}))
    return c


def patch(db, fn):
    with sqlite3.connect(db) as d:
        cid, raw = d.execute('SELECT id,state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()
        s = json.loads(raw); fn(s)
        d.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s), cid))


def state(db):
    with sqlite3.connect(db) as d:
        return json.loads(d.execute('SELECT state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0])


def post(c, path, body=None):
    return c.post('/api/worlds/2/' + path, json=body or {}, headers={'Idempotency-Key': uuid.uuid4().hex})


def hire(c, db, role='service', trait='optymista'):
    r = post(c, 'npcs/recruit', dict(role=role))
    assert r.status_code == 200, r.text
    nid = max(n['id'] for n in r.json()['npcs'])
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET trait=? WHERE id=?', (trait, nid))
    return nid


def npc(c, nid):
    return next(n for n in c.get('/api/worlds/2/npcs').json()['npcs'] if n['id'] == nid)


# --- Zad. 1: role i limit 20 ---
def test_recruit_with_role_and_role_change(env):
    app, clock, db = env
    c = player(app, db, 'role32', buildings={'residence': 5})
    d = hire(c, db, 'driver')
    s = hire(c, db)
    assert npc(c, d)['role'] == 'driver' and npc(c, s)['role'] == 'service'
    r = post(c, f'npcs/{d}/dispatch', dict(service_id='minimarket', hours=2))
    assert r.status_code == 409 and 'kierowcą' in r.json()['detail']
    r = post(c, f'npcs/{d}/role', dict(role='service')); assert r.status_code == 200
    assert npc(c, d)['role'] == 'service'
    r = post(c, f'npcs/{d}/role', dict(role='driver'))
    assert r.status_code == 409 and '24 h' in r.json()['detail']
    clock[0] += 24 * H + 1
    assert post(c, f'npcs/{d}/role', dict(role='driver')).status_code == 200
    assert post(c, f'npcs/{d}/role', dict(role='driver')).status_code == 409   # już kierowca
    assert post(c, 'npcs/recruit', dict(role='boss')).status_code == 422


def test_capacity_twenty(env):
    app, clock, db = env
    c = player(app, db, 'dwadziescia', buildings={'residence': 5}, cash=10 ** 6)
    for _ in range(20):
        assert post(c, 'npcs/recruit').status_code == 200
    j = c.get('/api/worlds/2/npcs').json()
    assert j['count'] == 20 and j['slots'] == 20 and j['maxSlots'] == 20
    assert post(c, 'npcs/recruit').status_code == 409
    assert state(db)['cash'] == 10 ** 6 - (3 * 500 + 3 * 1500 + 4 * 5000 + 5 * 15000 + 5 * 30000)


def test_trait_pools_and_rally_driver_only_for_driver():
    assert 'kierowca_rajdowy' not in N.trait_pool('service') and 'analityk' not in N.trait_pool('driver')
    assert 'kierowca_rajdowy' in N.trait_pool('driver') and 'analityk' in N.trait_pool('service')
    assert N.trait_of(dict(trait='kierowca_rajdowy', role='service')) == {}
    assert N.trait_of(dict(trait='kierowca', role='driver'))['travel'] == 0.8   # alias dawnej cechy
    assert N.trait_of(dict(trait='kierowca_rajdowy', role='driver'))['wear'] == 2.0


def test_migration_old_driver_trait_becomes_driver(tmp_path):
    db = tmp_path / 'mig.sqlite3'
    app = create_app(db, lambda: T0, tmp_path / 'setup.txt')
    c = player(app, db, 'stary')
    nid = post(c, 'npcs/recruit').json()['npcs'][0]['id']
    with sqlite3.connect(db) as d:   # symulacja bazy sprzed v3.2: dawna cecha, bez kolumn v3.2
        d.execute("UPDATE npcs SET trait='kierowca' WHERE id=?", (nid,))
        for col, _ in N.V32_COLUMNS:
            d.execute('ALTER TABLE npcs DROP COLUMN ' + col)
    app2 = create_app(db, lambda: T0, tmp_path / 'setup.txt')
    with sqlite3.connect(db) as d:
        assert d.execute('SELECT role,trait FROM npcs WHERE id=?', (nid,)).fetchone() == ('driver', 'kierowca_rajdowy')


# --- Zad. 3: logistyka ---
def rides(db):
    with sqlite3.connect(db) as d:
        d.row_factory = sqlite3.Row
        return [dict(r) for r in d.execute('SELECT * FROM npc_rides ORDER BY id')]


def test_car_requires_driver_and_bus_without(env):
    app, clock, db = env
    c = player(app, db, 'bezkierowcy', garage=['sedan'])
    a = hire(c, db)
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert r.status_code == 409 and 'kierowc' in r.json()['detail']
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2))
    assert r.status_code == 200 and r.json()['transport'] == 'bus' and npc(c, a)['travelMs'] == 120000
    assert rides(db) == []


def test_pooling_by_capacity_and_bus_overflow(env):
    app, clock, db = env
    c = player(app, db, 'pula', garage=['sedan', 'dostawczak'], buildings={'residence': 5})
    pax = [hire(c, db) for _ in range(4)]
    d1, d2 = hire(c, db, 'driver'), hire(c, db, 'driver')
    j = post(c, 'npcs/batch', dict(action='dispatch', npcs=pax, service_id='minimarket', hours=2)).json()
    cars = [r['car'] for r in j['results']]
    assert cars == ['sedan', 'sedan', 'dostawczak', None] and j['rideCount'] == 2     # 1+2, 1+1, reszta autobusem
    rs = rides(db)
    assert [(r['car_id'], json.loads(r['passengers'])) for r in rs] == [('sedan', pax[:2]), ('dostawczak', pax[2:3])]
    assert {r['driver_id'] for r in rs} == {d1, d2} and all(r['kind'] == 'drop' for r in rs)
    assert npc(c, pax[3])['transport'] == 'bus'
    assert npc(c, d1)['duty'] == 'ferry' and npc(c, d1)['busyUntil'] == rs[0]['back_at']


def test_tired_driver_does_not_drive(env):
    app, clock, db = env
    c = player(app, db, 'zmeczony', garage=['sedan'])
    a, d = hire(c, db), hire(c, db, 'driver')
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET energy=25 WHERE id=?', (d,))
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert r.status_code == 200 and r.json()['transport'] == 'bus'


def test_full_shift_drop_and_pickup_with_driver_costs(env):
    app, clock, db = env
    c = player(app, db, 'pelna', garage=['sedan'])
    a, d = hire(c, db), hire(c, db, 'driver')
    c0 = state(db)['cash']
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan')).json()['transport'] == 'car'
    clock[0] += 2 * H + 5 * M
    j = c.get('/api/worlds/2/npcs').json()
    assert [r['kind'] for r in rides(db)] == ['drop', 'pickup'] and all(n['phase'] is None for n in j['npcs'])
    s = state(db)
    assert s['cars']['sedan']['fuel'] == 88 and s['cars']['sedan']['wear'] == 4      # 4 odcinki × 3% / × 1%
    work_h = (2 * H - 48_000) / H                                                       # brak biletów
    ev = E.ev_mult(T0, 'service_cash') * S.demand(2, 'minimarket', T0)
    assert abs((s['cash'] - c0) - round(work_h * 50 * ev * E.prestige_mult(s))) <= 1
    dr = npc(c, d)
    assert dr['duty'] is None and dr['energy'] == 100                                    # kursy ~minuty, potem regeneracja


def test_rally_driver_faster_double_wear(env):
    app, clock, db = env
    c = player(app, db, 'rajd', garage=['sedan'])
    a, d = hire(c, db), hire(c, db, 'driver', trait='kierowca_rajdowy')
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert npc(c, a)['travelMs'] == round(48_000 * 0.8)
    assert state(db)['cars']['sedan']['wear'] == 4                                      # 2 odcinki × 1% × 2


def _scenario(tmp_path, tag):
    clock = [T0]
    db = tmp_path / f'det-{tag}.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / f'setup-{tag}.txt')
    c = player(app, db, 'det' + tag, garage=['sedan', 'dostawczak'], buildings={'residence': 5}, xp=4500)
    pax = [hire(c, db) for _ in range(4)]
    hire(c, db, 'driver'); hire(c, db, 'driver', trait='kierowca_rajdowy')
    patch(db, lambda s: s.update(servicesUnlocked=['kurier', 'callcenter', 'kawiarnia']))
    post(c, 'npcs/batch', dict(action='dispatch', npcs=pax[:3], service_id='minimarket', hours=8))
    post(c, f'npcs/{pax[3]}/dispatch', dict(service_id='kurier', hours=12))
    return app, clock, db, c


def test_settle_is_deterministic_regardless_of_frequency(tmp_path):
    """Kluczowy niezmiennik v3.2: wynik nie zależy od tego, jak często (i czy online) rozliczamy ekipę."""
    a_app, a_clock, a_db, a_c = _scenario(tmp_path, 'a')
    b_app, b_clock, b_db, b_c = _scenario(tmp_path, 'b')
    end = T0 + 30 * H
    a_clock[0] = end
    a_app.state.npc['sweep']()                              # jeden sweep po 30 h
    while b_clock[0] < end:                                 # sweep co 10 min
        b_clock[0] = min(end, b_clock[0] + 10 * M)
        b_app.state.npc['sweep']()
    sa, sb = state(a_db), state(b_db)
    assert sa['cash'] == sb['cash'] and sa['cars'] == sb['cars']
    key = lambda r: (r['driver_id'], r['car_id'], r['kind'], r['depart_at'], r['back_at'], r['passengers'])
    assert [key(r) for r in rides(a_db)] == [key(r) for r in rides(b_db)] and len(rides(a_db)) >= 4
    with sqlite3.connect(a_db) as x, sqlite3.connect(b_db) as y:
        q = 'SELECT id,energy,mood,hunger,phase,loyalty FROM npcs ORDER BY id'
        for ra, rb in zip(x.execute(q), y.execute(q)):
            assert ra[0] == rb[0] and ra[4] == rb[4] and ra[5] == rb[5]
            assert all(abs(p - q_) < 1e-6 for p, q_ in zip(ra[1:4], rb[1:4]))


# --- Zad. 2: Shift Taxi ---
def _taxi(app, db, name, garage=('sedan',), **upd):
    c = player(app, db, name, garage=list(garage))
    d = hire(c, db, 'driver')
    if upd:
        with sqlite3.connect(db) as x:
            x.execute('UPDATE npcs SET ' + ','.join(k + '=?' for k in upd) + ' WHERE id=?', (*upd.values(), d))
    return c, d


def test_taxi_calibration_fuel_wear(env):
    app, clock, db = env
    c, d = _taxi(app, db, 'taksowkarz')
    c0 = state(db)['cash']
    r = post(c, f'npcs/{d}/taxi', dict(hours=2))
    assert r.status_code == 200 and r.json()['car'] == 'sedan' and npc(c, d)['duty'] == 'taxi'
    clock[0] += H
    assert npc(c, d)['taxiCash'] == 46                                 # 40 × 1,15 (sedan) × 1 h
    clock[0] += H + 1
    j = npc(c, d)
    s = state(db)
    assert j['duty'] is None and s['cash'] - c0 == round(92 * E.prestige_mult(s))
    assert s['cars']['sedan']['fuel'] == 94 and s['cars']['sedan']['wear'] == 2   # 2 h × 3% / × 1%
    assert abs(j['energy'] - 88) <= 1 and abs(j['mood'] - 97) <= 1                # −6/h; optymista −3/h × 0,5
    assert rides(db)[-1]['kind'] == 'taxi' and rides(db)[-1]['cash'] == 92


def test_taxi_burnout_halves(env):
    app, clock, db = env
    c, d = _taxi(app, db, 'zmeczonytaxi', mood=20.0)
    c0 = state(db)['cash']
    post(c, f'npcs/{d}/taxi', dict(hours=2))
    clock[0] += 2 * H + 1
    c.get('/api/worlds/2/npcs')
    s = state(db)
    assert s['cash'] - c0 == round(46 * E.prestige_mult(s))           # przemęczenie ×0,5


def test_taxi_ends_early_on_fuel_and_energy(env):
    app, clock, db = env
    c, d = _taxi(app, db, 'bakowy')
    patch(db, lambda s: s.setdefault('cars', {}).setdefault('sedan', {}).update(fuel=4))
    post(c, f'npcs/{d}/taxi', dict(hours=4))
    clock[0] += 4 * H
    c.get('/api/worlds/2/npcs')
    assert rides(db)[-1]['back_at'] == T0 + int(4 / 3 * H) and state(db)['cars']['sedan']['fuel'] == 0
    with sqlite3.connect(db) as x:
        ev = json.loads(x.execute("SELECT payload FROM game_events WHERE kind='npc.taxi_done'").fetchone()[0])
    assert ev['reason'] == 'fuel' and ev['cash'] == round(46 * 4 / 3)
    c2, d2 = _taxi(app, db, 'senny', energy=45.0)
    t0 = clock[0]
    post(c2, f'npcs/{d2}/taxi', dict(hours=4))
    clock[0] += 4 * H
    c2.get('/api/worlds/2/npcs')
    assert abs(rides(db)[-1]['back_at'] - (t0 + 2.5 * H)) <= 2                    # energia 45 → 30 przy −6/h


def test_taxi_recall_validation_and_blocks_car(env):
    app, clock, db = env
    c, d = _taxi(app, db, 'odwolany')
    a = hire(c, db)
    assert post(c, f'npcs/{a}/taxi', dict(hours=2)).status_code == 409                # SERVICE nie jeździ Taxi
    assert post(c, f'npcs/{d}/taxi', dict(hours=3)).status_code == 422
    assert post(c, f'npcs/{d}/taxi', dict(hours=2, car_id='suv')).status_code == 409
    assert post(c, f'npcs/{d}/taxi', dict(hours=8)).status_code == 200
    assert post(c, f'npcs/{d}/taxi', dict(hours=2)).status_code == 409                # już jeździ
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert r.json()['transport'] == 'bus'                                               # D4: Taxi blokuje kierowcę i auto
    c0 = state(db)['cash']
    clock[0] += H
    assert post(c, f'npcs/{d}/recall').status_code == 200
    s = state(db)
    assert npc(c, d)['duty'] is None and s['cash'] - c0 == round(46 * E.prestige_mult(s))


def test_taxi_always_profitable_but_below_services():
    for v, g in ((v, E.car(v)) for v in N.SEATS):
        assert 0 < N.taxi_net(v, E) < 50, v                            # najsłabsza usługa: 50 $/h


# --- Zad. 4: cechy wg roli, burnout bez ucieczek ---
def test_rally_trait_ignored_for_passenger_and_bus(env):
    app, clock, db = env
    c = player(app, db, 'pasazer', garage=['sedan'])
    a = hire(c, db, trait='kierowca_rajdowy')                        # wymuszona cecha u SERVICE — bez efektu
    assert npc(c, a)['traitActive'] is False
    post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2))
    assert npc(c, a)['travelMs'] == 120_000                          # autobus ×2,0, bez −20%
    b = hire(c, db); hire(c, db, 'driver')                           # zwykły kierowca → 48 s, nie 38,4 s
    post(c, f'npcs/{b}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert npc(c, b)['travelMs'] == 48_000


def test_burnout_never_removes_npc(env):
    app, clock, db = env
    c = player(app, db, 'wytrwaly')
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET energy=5, mood=5, hunger=5 WHERE id=?', (a,))
    clock[0] += 14 * 24 * H
    app.state.npc['sweep']()                                         # (sesja klienta już wygasła — sprawdzamy bazę)
    with sqlite3.connect(db) as x:
        e, m, h, since = x.execute('SELECT energy,mood,hunger,unhappy_since FROM npcs WHERE id=?', (a,)).fetchone()
    assert since is not None and e == 100                            # nadal w ekipie, przemęczony (głód), wypoczęty


# --- Zad. 5: lojalność ---
DAY = 24 * H


def _idle(day0, **kw):
    n = dict(id=1, character_id=1, name='Jan', energy=100.0, mood=100.0, hunger=100.0, unhappy_since=None, warned_at=None,
             updated_at=day0, hired_at=day0 - 1, loy_day=day0 // DAY, loy_min=100.0, loyalty=0, loyal_since=None,
             trait='ambitny', role='service')
    N.clear_shift(n)
    n.update(kw)
    return n


def test_loyalty_plus_one_per_full_day_only_above_50():
    day0 = (T0 // DAY + 1) * DAY
    n, evs = N.advance(_idle(day0), day0 + 3 * DAY + H, S)            # sytość −1/h: 76 → 52 → 28
    assert n['loyalty'] == 2 and evs == [] or [e['kind'] for e in evs if e['kind'] == 'loyal'] == []
    assert n['loyalty'] == 2                                           # 3. doba: sytość < 50
    m, _ = N.advance(_idle(day0, hired_at=day0 + 1), day0 + DAY + 1, S)
    assert m['loyalty'] == 0                                           # zatrudniony w trakcie doby — nie liczy się
    k, _ = N.advance(_idle(day0, loy_day=None, loy_min=None), day0 + DAY + 1, S)
    assert k['loyalty'] == 0                                           # NPC sprzed v3.2 — pierwsza doba niepełna


def test_loyalty_never_drops_and_max_one_per_day():
    day0 = (T0 // DAY + 1) * DAY
    n, _ = N.advance(_idle(day0, loyalty=40, hunger=10.0), day0 + 2 * DAY, S)
    assert n['loyalty'] == 40
    one = N.advance(_idle(day0), day0 + DAY + 1, S)[0]['loyalty']
    split = _idle(day0)
    for k in range(1, 25):
        split = N.advance(split, day0 + k * H, S)[0]
    assert one == 1 and N.advance(split, day0 + DAY + 1, S)[0]['loyalty'] == 1


def test_loyal_status_bonus_and_trait_without_negatives():
    day0 = (T0 // DAY + 1) * DAY
    n, evs = N.advance(_idle(day0, loyalty=99), day0 + DAY + 1, S)
    assert n['loyalty'] == 100 and n['loyal_since'] == day0 + DAY and [e['kind'] for e in evs] == ['loyal']
    assert N.trait_of(n) == {k: v for k, v in N.TRAITS['ambitny'].items() if k != 'mood_drain'}   # ambitny: +15% bez kary
    assert N.trait_of(dict(trait='kierowca_rajdowy', role='driver', loyal_since=1)).get('wear') is None
    assert N.trait_of(dict(trait='spioch', loyal_since=1)).get('earn') is None
    base = dict(phase=None, duty='taxi', taxi_until=day0 + 10 * H, busy_until=day0 + 10 * H, taxi_mult=1.0, taxi_cash=0,
                ride_car='furgonetka', taxi_started_at=day0, trait='optymista', role='driver')
    a = N.advance(_idle(day0, **base), day0 + H, S)[0]['taxi_cash']
    b = N.advance(_idle(day0, loyal_since=1, **base), day0 + H, S)[0]['taxi_cash']
    assert abs(a - 40) < 1e-6 and abs(b - 42) < 1e-6                   # +5%


def test_loyal_event_and_journal(env):
    app, clock, db = env
    c = player(app, db, 'lojalny')
    a = hire(c, db)
    day = (clock[0] // DAY + 1) * DAY
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET loyalty=99, hired_at=?, loy_day=?, loy_min=100 WHERE id=?',
                  (day - DAY - 1, day // DAY - 1, a))                # bieżąca doba, zatrudniony od jej początku
    clock[0] = day + 1
    j = npc(c, a)
    assert j['loyal'] and j['loyalty'] == 100
    with sqlite3.connect(db) as x:
        txt = json.loads(x.execute("SELECT payload FROM game_events WHERE kind='npc.loyal'").fetchone()[0])['text']
    assert 'staje się wobec Ciebie lojalny' in txt and any('lojalny' in e['text'] for e in state(db)['history'])


# --- API: dashboard + i18n ---
def test_dashboard_roles_drivers_loyal_and_i18n(env):
    app, clock, db = env
    c = player(app, db, 'pulpit32', garage=['sedan'])
    a, d = hire(c, db), hire(c, db, 'driver')
    post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    npc_ = c.get('/api/worlds/2/dashboard').json()['npc']
    assert npc_['capacity'] == 4 and npc_['byRole'] == {'service': 1, 'driver': 1}
    assert npc_['drivers'] == {'total': 1, 'free': 0} and npc_['rides'] == 1 and npc_['loyal'] == 0
    c.post('/api/account/language', json={'language': 'en'}, headers={'Idempotency-Key': uuid.uuid4().hex})
    r = post(c, f'npcs/{d}/dispatch', dict(service_id='minimarket', hours=2))
    assert r.status_code == 409 and 'is a driver' in r.json()['detail']
