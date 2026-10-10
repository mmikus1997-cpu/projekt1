"""0.8 return-to-play: residences, rest, long contracts and the away summary.

Runs entirely against an injected clock so absence can be simulated exactly.
"""
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server import economy as E

pytestmark = pytest.mark.usefixtures()


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, tmp_path


def register(app, name):
    client = TestClient(app)
    r = client.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    return client


def create(c, wid=2, name='IdleOne'):
    r = c.post(f'/api/worlds/{wid}/character', json={'nickname': name, 'accept_test_reset': True})
    assert r.status_code == 200, r.text
    return r.json()


def action(c, kind, wid=2, **kwargs):
    return c.post(f'/api/worlds/{wid}/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': kind, **kwargs})


def state(c, wid=2):
    r = c.get(f'/api/worlds/{wid}/state')
    assert r.status_code == 200, r.text
    return r.json()


def set_district(app, d, wid=2, nick=None):
    with app.state.db.tx() as cx:
        if nick:
            cx.execute('UPDATE characters SET current_district=? WHERE nickname=? AND world_id=?', (d, nick, wid))
        else:
            cx.execute('UPDATE characters SET current_district=? WHERE world_id=?', (d, wid))  # 0.45


def test_residence_speeds_energy_regen(env, flat_stats):
    app, clock, path = env
    c = register(app, 'idle_regen')
    create(c)
    data = state(c)
    assert data['catalog']['regenPerHour'] == 600  # 10 * speed 60
    assert data['catalog']['residences'][0]['id'] == 'studio-flat'
    for kind,extra,dst in (('contract',dict(contract='delivery'),8),('contract',dict(contract='inventory'),3),('train',dict(stat=0),None),('train',dict(stat=1),None)):
        if dst:
            set_district(app, dst)  # 0.45: kontrakty w swoich dzielnicach
        assert action(c, kind, **extra).status_code == 200  # make 25 energy of head-room below the cap
    data = state(c)
    before = data['state']['energy']
    clock[0] += 60_000
    after = state(c)['state']['energy']
    assert abs(after - before - 10) < 0.6
    r = action(c, 'buy_residence', residence='studio-flat')
    assert r.status_code == 200, r.text
    data = state(c)
    assert data['state']['residence'] == 'studio-flat'
    assert data['state']['cash'] == 3000 - 1200 - 400  # rezydencja minus dwa treningi (QA 3: 50+10×15 $)
    assert data['catalog']['regenPerHour'] == 720  # (10 + 2) * 60
    before = data['state']['energy']
    clock[0] += 60_000
    after = state(c)['state']['energy']
    assert abs(after - before - 12) < 0.6
    # Same tier twice and cheaper downgrade are refused; higher tier needs level.
    assert action(c, 'buy_residence', residence='studio-flat').status_code == 409
    assert action(c, 'buy_residence', residence='green-villa').status_code == 409


def test_rest_flow_tier_gates_and_overflow(env):
    app, clock, path = env
    c = register(app, 'idle_rest')
    create(c)
    # Night rest requires residence tier 2.
    assert action(c, 'rest_start', rest='night').status_code == 409
    assert action(c, 'buy_residence', residence='studio-flat').status_code == 200
    # Burn some energy first, otherwise the gain would honestly be 0.
    set_district(app, 3)  # 0.45: inwentaryzacja w Centrum
    assert action(c, 'contract', contract='inventory').status_code == 200
    energy = state(c)['state']['energy']
    assert energy == 235
    r = action(c, 'rest_start', rest='nap')
    assert r.status_code == 200, r.text
    rest = state(c)['state']['rest']
    assert rest['id'] == 'nap' and rest['gain'] == 10
    assert action(c, 'rest_start', rest='nap').status_code == 409
    assert action(c, 'rest_claim').status_code == 409
    clock[0] += 20_000 - 1
    assert action(c, 'rest_claim').status_code == 409
    clock[0] += 1
    r = action(c, 'rest_claim')
    assert r.status_code == 200, r.text
    s = state(c)['state']
    assert s['rest'] is None
    assert s['energy'] == pytest.approx(240, abs=0.6)
    assert s['completed']['rests'] == 1


def test_away_summary_appears_once_after_absence(env):
    app, clock, path = env
    c = register(app, 'idle_away')
    create(c)
    set_district(app, 3)  # 0.45: inwentaryzacja w Centrum
    assert action(c, 'contract', contract='inventory').status_code == 200
    # Threshold is 30 in-game minutes: 30 * 60_000 / speed 60 = 30 s real.
    assert state(c)['away'] is None
    clock[0] += 45_000  # inventory task (5 s real) finished; player "returned" later
    data = state(c)
    away = data['away']
    assert away, 'absence should produce a welcome-back summary'
    assert len(away['contracts']) == 1
    assert away['training'] == 0
    assert away['energy'] == int(data['state']['energy'])
    assert away['vault'] == 52  # 45 min gry: kurier 30 $ + Kawiarnia lvl 1 22 $ (4.2 GDD v3.1: budynek ze skarbcem)
    assert away['minutes'] >= 0
    assert state(c)['away'] is None  # one-shot acknowledgement


def test_long_contracts_in_catalog_and_level_gates(env):
    app, clock, path = env
    c = register(app, 'idle_long')
    create(c)
    ids = {x['id']: x for x in state(c)['catalog']['contracts']}
    assert {'fleet', 'branch'} <= set(ids)
    assert ids['fleet']['duration'] == 8 * 3_600_000 // 60
    assert ids['branch']['duration'] == 24 * 3_600_000 // 60
    assert action(c, 'contract', contract='fleet').status_code == 409  # level 5 required
    # Unit-level check of acceptance and rewards at the intended progression point.
    s = E.new(clock[0], test=True)
    s['xp'] = 1013  # exactly level 5
    E.action(s, 'contract', dict(contract='fleet'), clock[0], 1, district=4)  # 0.45
    s['xp'] = 2113  # exactly level 7
    E.action(s, 'contract', dict(contract='branch'), clock[0], 1, district=5)  # 0.45
    kinds = [t['contract'] for t in s['contracts']]
    assert kinds == ['fleet', 'branch']


def test_old_states_keep_working(env):
    app, clock, path = env
    c = register(app, 'idle_old')
    created = create(c)
    legacy = E.new(clock[0], test=True)
    for key in ('residence', 'rest', 'lastAction'):
        legacy.pop(key)
    with app.state.db.tx() as db:
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(legacy), created['character']['id']))
    data = state(c)
    assert data['state']['residence'] is None
    assert data['state']['rest'] is None
    assert data['away'] is None
    assert action(c, 'buy_residence', residence='studio-flat').status_code == 200
