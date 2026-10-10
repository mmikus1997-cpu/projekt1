"""2.4b GDD v3.1: zmiana pracy NPC (auto-pilot) — fazy, zarobek z bonusem, autobus/auto, recall, sweep; 2.3c: przemęczenie ×0,5."""
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
EV = E.ev_mult(T0, 'service_cash') * S.demand(2, 'minimarket', T0)  # event × popyt (2.2b), oba zamrażane przy starcie   # „Szczyt Usług” może trwać w chwili T0 — mnożnik zamrażany przy starcie


@pytest.fixture
def env(tmp_path):
    clock = [T0]
    db = tmp_path / 'shift.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, db


def player(app, db, name, **state):
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/2/character', json={'nickname': name.title(), 'accept_test_reset': True}).status_code == 200
    patch(db, lambda s: s.update({'cash': 5000, **state}))
    return c


def patch(db, fn):
    with sqlite3.connect(db) as d:
        cid, raw = d.execute('SELECT id,state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()
        s = json.loads(raw); fn(s)
        d.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s), cid))


def cash(db):
    with sqlite3.connect(db) as d:
        return json.loads(d.execute('SELECT state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0])['cash']


def post(c, path, body=None):
    return c.post('/api/worlds/2/' + path, json=body or {}, headers={'Idempotency-Key': uuid.uuid4().hex})


def hire(c, db=None, trait='optymista'):
    """Rekrutacja; cecha ustawiana na neutralną dla zarobku (optymista), by kwoty w testach były stałe."""
    nid = post(c, 'npcs/recruit').json()['npcs'][-1]['id']
    if db is not None:
        with sqlite3.connect(db) as d:
            d.execute('UPDATE npcs SET trait=? WHERE id=?', (trait, nid))
    return nid

def driver(c, db, trait='optymista'):
    """v3.2: kierowca (rola DRIVER) — autami z garażu jeżdżą tylko kierowcy."""
    nid = post(c, 'npcs/recruit', dict(role='driver')).json()['npcs'][-1]['id']
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET trait=? WHERE id=?', (trait, nid))
    return nid



def shift_row(service, energy=100.0, mood=100.0, hunger=100.0, hours=4, car=None, event=1.0):
    """NPC tuż po dispatch (jak w endpoincie)."""
    n = dict(id=1, character_id=1, name='Ania', energy=energy, mood=mood, hunger=hunger, unhappy_since=None, warned_at=None,
             updated_at=T0)
    N.clear_shift(n)
    from server import economy as E
    n.update(assigned_service_id=service, assigned_car_id=car, autopilot_mode=f'{hours}h', autopilot_expires_at=T0 + hours * H,
             shift_started_at=T0, travel_ms=S.travel_ms(S.BY_ID[service], car, E), shift_bonus=N.AUTOPILOT[hours],
             shift_event=event, shift_bus=0 if car else 1)
    N._start_leg(n, 'to_work', T0)
    return n


def test_autopilot_bonuses():
    assert N.AUTOPILOT == {2: 0.0, 4: 0.05, 8: 0.10, 12: 0.15}


# --- zmiana bez spadku energii: praca do końca zmiany, wypłata z bonusem minus bilety ---
def test_minimarket_4h_bus_payout():
    n = shift_row('minimarket', hours=4)                     # Centrum: autobus 120 s
    n, evs = N.advance(n, T0 + 1 * H, S)
    assert n['phase'] == 'working' and evs == []
    n, evs = N.advance(n, T0 + 4 * H + 2 * M, S)             # koniec zmiany + powrót
    work_h = 4 - 2 / 60
    assert evs == [dict(kind='done', cash=round(work_h * 50 * 1.05 - 40), service='minimarket', recalled=False,
                        at=T0 + 4 * H + 2 * M, car=None, manager=False, fuel=None, pref=None)]   # 2.7: chwila powrotu, auto, flaga managera
    assert n['phase'] is None and n['status'] == 'idle' and n['assigned_service_id'] is None


# --- pełny cykl: praca → zmęczenie → dom → sen → praca → koniec ---
def test_klinika_full_cycle_exact_phases():
    n = shift_row('klinika', energy=45.0, hours=12, car='sedan')   # sedan: 48 s; klinika −6 energii/h
    leg = 48_000
    t_tired = T0 + leg + 2.5 * H                              # 45 → 30 (TIRED, 2.3c) przy −6/h = 2,5 h
    a, _ = N.advance(n, int(t_tired) - 1000, S); assert a['phase'] == 'working'
    a, _ = N.advance(n, int(t_tired) + 1000, S); assert a['phase'] == 'to_home'
    t_wake = t_tired + leg + 6 * H                            # sen 30 → 90 przy +10/h
    assert not N.exhausted(N.advance(n, int(t_tired) + 1000, S)[0]), 'powrót przy 30 wyprzedza przemęczenie'
    a, _ = N.advance(n, int(t_wake) - 1000, S); assert a['phase'] == 'sleeping' and a['status'] == 'sleeping'
    a, _ = N.advance(n, int(t_wake) + 1000, S); assert a['phase'] == 'to_work'
    a, evs = N.advance(n, T0 + 12 * H + leg + 1000, S)
    second = (T0 + 12 * H) - (t_wake + leg)                   # druga sesja pracy do końca zmiany
    expected = round((2.5 * H + second) / H * 200 * 1.15)     # auto → bez biletów
    assert len(evs) == 1 and evs[0]['kind'] == 'done' and abs(evs[0]['cash'] - expected) <= 1
    assert a['phase'] is None


def test_event_multiplier_frozen():
    a, evs = N.advance(shift_row('minimarket', hours=2, event=1.25), T0 + 2 * H + 2 * M, S)
    assert evs[0]['cash'] == round((2 - 2 / 60) * 50 * 1.25 - 40)


def test_burnout_mid_shift_halves_pay():
    # call center: nastrój −3/h; start 39 → < 30 po 3 h pracy; dalej zarobek ×0,5 (NPC nie znika)
    n = shift_row('callcenter', mood=39.0, hours=8)          # Portowe: autobus 240 s
    a, evs = N.advance(n, T0 + 8 * H + 4 * M, S)
    kinds = [e['kind'] for e in evs]
    assert kinds == ['burnout', 'done'] and evs[0]['cause'] == 'mood'
    leg_h = 4 / 60
    full, half = 3, 8 - leg_h - 3
    assert abs(evs[-1]['cash'] - round(90 * 1.10 * (full + 0.5 * half) - 40)) <= 1
    assert N.exhausted(a) and a['phase'] is None


# --- API ---
def test_dispatch_and_payout_via_api(env):
    app, clock, db = env
    c = player(app, db, 'dyspozytor')
    nid = hire(c, db); c0 = cash(db)
    r = post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=4))
    assert r.status_code == 200, r.text
    n = r.json()['npcs'][0]; assert n['phase'] == 'to_work' and n['bus'] and n['travelMs'] == 120000
    clock[0] += 4 * H + 2 * M
    j = c.get('/api/worlds/2/npcs').json()['npcs'][0]
    assert j['phase'] is None and j['status'] == 'idle'
    assert abs(cash(db) - (c0 + round((4 - 2 / 60) * 50 * 1.05 * EV - 40))) <= 1
    with sqlite3.connect(db) as d:
        assert d.execute("SELECT count(*) FROM game_events WHERE kind='npc.shift_done'").fetchone()[0] == 1


def test_dispatch_validation(env):
    app, clock, db = env
    c = player(app, db, 'walidator', garage=['sedan'])
    a, b = hire(c, db), hire(c, db)   # stała cecha — „kierowca” skróciłby dojazd (48 s → 38,4 s)
    driver(c, db)                     # v3.2: auto prowadzi kierowca
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='klinika', hours=4)).status_code == 409        # nieodblokowana
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=3)).status_code == 422     # zły czas
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=4, car_id='suv')).status_code == 409
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=4, car_id='sedan'))
    assert r.status_code == 200 and r.json()['npcs'][0]['travelMs'] == 48000 and not r.json()['npcs'][0]['bus']
    r = post(c, f'npcs/{b}/dispatch', dict(service_id='minimarket', hours=4, car_id='sedan'))
    # v3.2: kierowca i sedan są w kursie → b jedzie autobusem (fallback bez blokowania gry)
    assert r.status_code == 200 and r.json()['transport'] == 'bus' and r.json()['npcs'][1]['travelMs'] == 120000
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='kawiarnia', hours=2))
    assert r.status_code == 409 and 'już na zmianie' in r.json()['detail']
    z = hire(c, db)
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET energy=10 WHERE id=?', (z,))
    r = post(c, f'npcs/{z}/dispatch', dict(service_id='minimarket', hours=2))
    assert r.status_code == 409 and 'zmęczony' in r.json()['detail']
    assert post(c, 'npcs/999/dispatch', dict(service_id='minimarket', hours=2)).status_code == 404


def test_car_busy_on_old_route_blocks_dispatch(env):
    app, clock, db = env
    c = player(app, db, 'trasowy', garage=['sedan'])
    patch(db, lambda s: s.setdefault('npcRoutes', dict(runs=[], done=0, cash=0, xp=0))['runs'].append(
        dict(vehicle='sedan', end=T0 + H)))
    a = hire(c); driver(c, db)
    r = post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    assert r.status_code == 200 and r.json()['transport'] == 'bus'      # v3.2: auto na starej trasie → autobus


def test_recall_strips_bonus(env):
    app, clock, db = env
    c = player(app, db, 'odwolany')
    nid = hire(c, db); c0 = cash(db)
    post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=8))
    clock[0] += 1 * H
    r = post(c, f'npcs/{nid}/recall'); assert r.status_code == 200 and r.json()['npcs'][0]['phase'] == 'to_home'
    assert post(c, f'npcs/{nid}/recall').status_code in (200, 409)
    clock[0] += 2 * M
    c.get('/api/worlds/2/npcs')
    assert abs(cash(db) - (c0 + round((1 - 2 / 60) * 50 * EV - 40))) <= 1      # bez +10%


def test_sweep_pays_offline(env):
    app, clock, db = env
    c = player(app, db, 'nieobecny')
    nid = hire(c, db); c0 = cash(db)
    post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=2))
    clock[0] += 3 * H
    app.state.npc['sweep']()
    assert abs(cash(db) - (c0 + round((2 - 2 / 60) * 50 * EV - 40))) <= 1


# --- 2.4c GDD v3.1: przerwa dyspozytora + auto NPC zajęte dla starych tras i podróży ---
def test_dispatcher_cooldown_streak(env):
    app, clock, db = env
    c = player(app, db, 'szef', cash=100000)
    team = [hire(c) for _ in range(3)]
    patch(db, lambda s: s.setdefault('buildings', {}).update(residence=4))
    team += [hire(c) for _ in range(7)] + [hire(c)]
    assert len(team) == 11
    for i in range(10):                                 # 10 tras w odstępach 10 s
        r = post(c, f'npcs/{team[i]}/dispatch', dict(service_id='minimarket', hours=2))
        assert r.status_code == 200, (i, r.text)
        clock[0] += 10_000
    r = post(c, f'npcs/{team[10]}/dispatch', dict(service_id='minimarket', hours=2))
    assert r.status_code == 409 and 'Przerwa dyspozytora' in r.json()['detail']
    assert c.get('/api/worlds/2/npcs').json()['dispatchCooldownUntil'] > clock[0]
    clock[0] += 2 * M
    assert post(c, f'npcs/{team[10]}/dispatch', dict(service_id='minimarket', hours=2)).status_code == 200


def test_streak_resets_after_pause(env):
    app, clock, db = env
    c = player(app, db, 'spokojny', cash=100000)
    patch(db, lambda s: s.setdefault('buildings', {}).update(residence=4))
    team = [hire(c) for _ in range(11)]
    for i in range(11):                                 # odstęp 2 min → nigdy „z rzędu”
        assert post(c, f'npcs/{team[i]}/dispatch', dict(service_id='minimarket', hours=2)).status_code == 200
        clock[0] += 2 * M


def test_npc_car_not_in_saved_state(env):
    app, clock, db = env
    c = player(app, db, 'dwutorowy', garage=['sedan'])
    nid = hire(c); driver(c, db)
    assert post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan')).status_code == 200
    r = c.post('/api/worlds/2/actions', headers={'Idempotency-Key': uuid.uuid4().hex},
               json={'action': 'route_dispatch', 'route': 'courier', 'vehicle': 'sedan'})
    assert r.status_code == 409 and 'wycofane' in r.json()['detail']      # 2.4e
    with sqlite3.connect(db) as d:                       # wstrzyknięcie nie trafia do zapisanego stanu
        assert 'npcCars' not in json.loads(d.execute('SELECT state_json FROM characters').fetchone()[0])


def test_bus_free_event_frozen(env):
    """2.4e: wysłany w oknie Darmowej Komunikacji — bilety 0 $ przez całą zmianę (także po końcu okna)."""
    app, clock, db = env
    W = E.EVENT_WINDOW
    base = (clock[0] // W) * W
    clock[0] = next(base + k * W for k in range(1, 5) if E.timed_event(base + k * W)['effect'] == 'bus_free') + W - H
    c = player(app, db, 'gapowicz')
    nid = hire(c, db); c0 = cash(db); t0 = clock[0]
    post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=2))
    clock[0] += 3 * H                                    # okno minęło w trakcie zmiany
    c.get('/api/worlds/2/npcs')
    mult = E.ev_mult(t0, 'service_cash') * S.demand(2, 'minimarket', t0)
    assert abs(cash(db) - (c0 + round((2 - 2 / 60) * 50 * mult))) <= 1   # bez −40 $ za bilety


def test_vehicle_busy_until_sees_npc_cars():
    s = {'npcRoutes': {'runs': []}, 'npcCars': {'sedan': T0 + H}}
    assert E.vehicle_busy_until(s, 'sedan', T0) == T0 + H and E.vehicle_busy_until(s, 'bus', T0) == 0


# --- 4.4 GDD v3.1: posiłek z Buffetu (zastąpił prowizorkę 2.4d) ---
def test_feed(env):
    app, clock, db = env
    c = player(app, db, 'glodny', buffet=2)
    nid = hire(c)
    r = post(c, f'npcs/{nid}/feed'); assert r.status_code == 409 and 'najedzony' in r.json()['detail']
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET energy=80,mood=80,hunger=10,unhappy_since=?,updated_at=? WHERE id=?', (clock[0], clock[0], nid))
    c0 = cash(db)
    r = post(c, f'npcs/{nid}/feed'); assert r.status_code == 200
    n = r.json()['npcs'][0]
    assert n['hunger'] == 35 and n['mood'] == 85 and not n['exhausted'] and n['earnMult'] == 1.0 and cash(db) == c0 - 25   # 4.4: głód jedyną przyczyną → koniec przemęczenia od razu
    with sqlite3.connect(db) as d:
        assert d.execute("SELECT count(*) FROM game_events WHERE kind='npc.recovered'").fetchone()[0] == 1
    patch(db, lambda s: s.update(cash=10))
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET hunger=40 WHERE id=?', (nid,))
    r = post(c, f'npcs/{nid}/feed'); assert r.status_code == 409 and '25 $' in r.json()['detail']


# --- 2.3b GDD v3.1: osobowość NPC ---
def test_traits_catalog():
    assert set(N.TRAITS) == {'pracoholik', 'spioch', 'ambitny', 'optymista', 'analityk', 'kierowca_rajdowy'}


def _work(trait, service, hours=2, **kw):
    n = shift_row(service, hours=hours, car='sedan', **kw); n['trait'] = trait
    return n


def test_trait_earnings():
    base = N.advance(_work(None, 'minimarket'), T0 + 3 * H, S)[1][-1]['cash']
    for trait, pct in (('pracoholik', .10), ('spioch', -.10), ('ambitny', .15), ('optymista', 0), ('kierowca', 0)):
        got = N.advance(_work(trait, 'minimarket'), T0 + 3 * H, S)[1][-1]['cash']
        if trait == 'kierowca':
            assert got >= base, 'krótszy dojazd = więcej minut pracy'
        else:
            assert abs(got - base * (1 + pct)) <= 1, trait
    a = N.advance(_work('analityk', 'callcenter'), T0 + 3 * H, S)[1][-1]['cash']
    b = N.advance(_work(None, 'callcenter'), T0 + 3 * H, S)[1][-1]['cash']
    assert abs(a - b * 1.15) <= 1
    assert N.advance(_work('analityk', 'minimarket'), T0 + 3 * H, S)[1][-1]['cash'] == base, 'analityk tylko biuro'


def test_trait_drains_and_sleep():
    n = _work('pracoholik', 'klinika', hours=12); n.update(phase='working', status='working', updated_at=T0)
    a, _ = N.advance(n, T0 + H, S); assert abs(a['energy'] - (100 - 6 * 1.2)) < 1e-6
    n = _work('ambitny', 'callcenter', hours=12); n.update(phase='working', status='working', updated_at=T0)
    a, _ = N.advance(n, T0 + H, S); assert abs(a['mood'] - (100 - 3 * 1.5)) < 1e-6
    n = _work('optymista', 'callcenter', hours=12); n.update(phase='working', status='working', updated_at=T0)
    a, _ = N.advance(n, T0 + H, S); assert abs(a['mood'] - (100 - 1.5)) < 1e-6
    n = _work('optymista', 'park', hours=12, mood=50.0); n.update(phase='working', status='working', updated_at=T0)
    a, _ = N.advance(n, T0 + H, S); assert abs(a['mood'] - 52) < 1e-6, 'regeneracja Parku bez zmian'
    idle = dict(id=1, character_id=1, name='A', energy=50.0, mood=100.0, hunger=100.0, unhappy_since=None, warned_at=None,
                updated_at=T0, trait='spioch'); N.clear_shift(idle)
    a, _ = N.advance(idle, T0 + H, S); assert abs(a['energy'] - 63) < 1e-6, 'śpioch: +13/h'


def test_trait_driver_travel():
    k = S.BY_ID['klinika']
    assert S.travel_ms(k, None, E, 0.8) == 96000 and S.travel_ms(k, 'mistrz', E, 0.8) == 30000, 'min. 30 s'


def test_recruit_assigns_trait_and_migration_backfills(env, tmp_path):
    app, clock, db = env
    c = player(app, db, 'charakter')
    j = post(c, 'npcs/recruit').json()['npcs'][0]
    assert j['trait'] in N.TRAITS and j['traitLabel'] and j['traitDesc']
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET trait=NULL')
    create_app(db, lambda: clock[0], tmp_path / 'setup.txt')   # ponowny start → uzupełnienie
    with sqlite3.connect(db) as d:
        nid, tr = d.execute('SELECT id,trait FROM npcs').fetchone()
    assert tr == N.TRAIT_IDS[nid % 6]
