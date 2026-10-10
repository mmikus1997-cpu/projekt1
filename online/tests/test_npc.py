"""2.3 GDD v3.1: NPC — migracja, rekrutacja (ceny/miejsca), 3 emocje (advance); 2.3c: przemęczenie zamiast ucieczki."""
import json
import sqlite3
import uuid
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import npc as N, services as S

H = 3_600_000
T0 = 1780000000000


@pytest.fixture
def env(tmp_path):
    clock = [T0]
    db = tmp_path / 'npc.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, db


def player(app, name):
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/2/character', json={'nickname': name.title(), 'accept_test_reset': True}).status_code == 200
    return c


def patch_state(db, fn):
    with sqlite3.connect(db) as d:
        cid, raw = d.execute('SELECT id,state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()
        s = json.loads(raw); fn(s)
        d.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s), cid))
    return cid


def recruit(c, key=None):
    return c.post('/api/worlds/2/npcs/recruit', json={}, headers={'Idempotency-Key': key or uuid.uuid4().hex})


def events(db, kind):
    with sqlite3.connect(db) as d:
        return [json.loads(p) for (p,) in d.execute('SELECT payload FROM game_events WHERE kind=? ORDER BY id', (kind,))]


def npc_row(i=1, **kw):
    base = dict(id=i, character_id=1, name='Ania', energy=100.0, mood=100.0, hunger=100.0, status='idle',
                assigned_service_id=None, unhappy_since=None, warned_at=None, updated_at=T0)
    base.update(kw)
    return base


# --- 1. migracja ---
def test_schema_and_idempotent_migration(env, tmp_path):
    app, clock, db = env
    create_app(db, lambda: clock[0], tmp_path / 'setup.txt')  # ponowny start
    with sqlite3.connect(db) as d:
        cols = {r[1] for r in d.execute('PRAGMA table_info(npcs)')}
        idx = {r[1] for r in d.execute('PRAGMA index_list(npcs)')}
    assert {'energy', 'mood', 'hunger', 'status', 'assigned_service_id', 'assigned_car_id', 'autopilot_mode',
            'autopilot_expires_at', 'unhappy_since', 'warned_at', 'updated_at'} <= cols
    assert {'npcs_character', 'npcs_unhappy'} <= idx


# --- 2. ceny i miejsca ---
def test_cost_tiers_and_slots():
    # v3.2 D1: limit 20, Rezydencja × 4, #16–20 po 30 000 $
    assert [N.recruit_cost(k) for k in range(20)] == [500] * 3 + [1500] * 3 + [5000] * 4 + [15000] * 5 + [30000] * 5
    assert [N.slots({'buildings': {'residence': l}}) for l in (1, 2, 3, 4, 5, 9)] == [4, 8, 12, 16, 20, 20]


# --- 3. rekrutacja + limit miejsc ---
def test_recruit_prices_and_slot_limit(env):
    app, clock, db = env
    c = player(app, 'rekruter')
    patch_state(db, lambda s: s.update(cash=10000))
    for _ in range(4):
        assert recruit(c).status_code == 200
    j = c.get('/api/worlds/2/npcs').json()
    assert j['count'] == 4 and j['slots'] == 4 and j['nextCost'] is None
    r = recruit(c); assert r.status_code == 409 and 'Brak miejsc' in r.json()['detail']
    patch_state(db, lambda s: s.setdefault('buildings', {}).update(residence=2))
    r = recruit(c); assert r.status_code == 200 and r.json()['cash'] == 10000 - 1500 - 1500 - 1500
    assert r.json()['nextCost'] == 1500 and r.json()['npcs'][0]['energy'] == 100


# --- 4. warunki rekrutacji ---
def test_recruit_requires_cash_home_and_not_traveling(env):
    app, clock, db = env
    c = player(app, 'biedny')
    patch_state(db, lambda s: s.update(cash=100))
    r = recruit(c); assert r.status_code == 409 and '500' in r.json()['detail']
    patch_state(db, lambda s: s.update(cash=5000))
    assert c.post('/api/worlds/2/travel', json={'target_district': 2, 'mode': 'bus'}).status_code == 200
    r = recruit(c); assert r.status_code == 409 and 'drodze' in r.json()['detail']
    clock[0] += 7 * H; assert c.post('/api/worlds/2/travel/arrive', json={}).status_code == 200
    r = recruit(c); assert r.status_code == 409 and 'Nadmorskie' in r.json()['detail']


# --- 5. idempotencja ---
def test_recruit_idempotent(env):
    app, clock, db = env
    c = player(app, 'powtorka')
    patch_state(db, lambda s: s.update(cash=1000))
    k = uuid.uuid4().hex
    a, b = recruit(c, k).json(), recruit(c, k).json()
    assert a == b and c.get('/api/worlds/2/npcs').json()['count'] == 1


# --- 7. praca wg katalogu usługi ---
def test_working_rates_from_service():
    n, _ = N.advance(npc_row(status='working', assigned_service_id='klinika'), T0 + 10 * H, S)
    assert (n['energy'], n['mood'], n['hunger']) == (40, 100, 70)       # −6/h, 0, sytość −3/h
    n, _ = N.advance(npc_row(status='working', assigned_service_id='park', mood=50.0), T0 + 10 * H, S)
    assert n['mood'] == 70 and n['hunger'] == 80                        # +2/h regeneracja, sytość −2/h


def test_sweep_settles_offline_players(env):
    app, clock, db = env
    c = player(app, 'offline')
    patch_state(db, lambda s: s.update(cash=1000))
    recruit(c)
    clock[0] += 10 * H; app.state.npc['sweep']()
    with sqlite3.connect(db) as d:
        hunger, upd = d.execute('SELECT hunger,updated_at FROM npcs').fetchone()
    assert hunger == 90 and upd == clock[0]


# --- 6. bezczynność ---
def test_idle_rates():
    n, ev = N.advance(npc_row(energy=50.0), T0 + 5 * H, S)
    assert n['energy'] == 100 and n['mood'] == 100 and n['hunger'] == 95 and ev == []


# --- 2.3c: przemęczenie zamiast ucieczki ---
def test_burnout_exact_entry_any_emotion():
    # klinika: sytość 36 −3/h → < 30 po 2 h (energia i nastrój wysoko — wystarczy JEDNA emocja)
    row = npc_row(status='working', assigned_service_id='klinika', energy=100.0, mood=100.0, hunger=36.0)
    n, evs = N.advance(row, T0 + 3 * H, S)
    assert abs(n['unhappy_since'] - (T0 + 2 * H)) <= 1 and evs == [dict(kind='burnout', cause='hunger')]


def test_burnout_hysteresis_recovers_at_40():
    row = npc_row(energy=20.0, unhappy_since=T0 - H)          # bezczynny: energia +10/h
    n, evs = N.advance(row, T0 + int(1.5 * H), S)             # 35 — nadal przemęczony (próg wyjścia 40)
    assert N.exhausted(n) and evs == []
    n, evs = N.advance(row, T0 + 3 * H, S)                    # 40 po 2 h → wyjście
    assert not N.exhausted(n) and evs == [dict(kind='recovered')]


def test_no_flee_ever(env):
    app, clock, db = env
    c = player(app, 'wytrwaly')
    patch_state(db, lambda s: s.update(cash=1000))
    nid = recruit(c).json()['npcs'][0]['id']
    with sqlite3.connect(db) as d:
        d.execute('UPDATE npcs SET energy=5,mood=5,hunger=5,updated_at=? WHERE id=?', (clock[0], nid))
    for _ in range(10):
        clock[0] += 10 * H; app.state.npc['sweep']()
    j = c.get('/api/worlds/2/npcs').json()
    assert j['count'] == 1 and j['npcs'][0]['id'] == nid, 'NPC nigdy nie znika'
    assert j['npcs'][0]['exhausted'] and j['npcs'][0]['earnMult'] == 0.5
    ev = events(db, 'npc.burnout'); assert len(ev) == 1 and ev[0]['npc'] == nid, 'jedno powiadomienie, bez spamu'
    assert events(db, 'npc.fled') == []
    with sqlite3.connect(db) as d:
        assert d.execute("SELECT count(*) FROM audit WHERE event='npc.fled'").fetchone()[0] == 0

