"""2.4e GDD v3.1: stare trasy NPC wycofane — wysyłka 409, odbiór tras trwających w chwili migracji działa.

Pomocnicze funkcje (env, register, create, action, state, set_state, cid_of) importują inne testy."""
import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server import economy as E


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


def create(c, wid=2, name='Trasowy'):
    r = c.post(f'/api/worlds/{wid}/character', json={'nickname': name, 'accept_test_reset': True})
    assert r.status_code == 200, r.text
    return r.json()


def action(c, kind, wid=2, **kwargs):
    return c.post(f'/api/worlds/{wid}/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': kind, **kwargs})


def state(c, wid=2):
    return c.get(f'/api/worlds/{wid}/state').json()


def set_state(app, cid, patch):
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        row = db.execute('SELECT state_json FROM characters WHERE id=?', (cid,)).fetchone()
        st = json.loads(row[0]);st.update(patch)
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st), cid))


def cid_of(c):
    return state(c)['character']['id']


def inflight(app, c, clock, vehicle='dostawczak', end_delta=-1, ev=None):
    """Trasa wysłana przed 2.4e (wstrzyknięta do stanu)."""
    run = dict(route='courier', vehicle=vehicle, start=clock[0] - 15 * 60000, end=clock[0] + end_delta)
    if ev is not None:
        run['ev'] = ev
    set_state(app, cid_of(c), {'garage': ['dostawczak', 'sedan'], 'cash': 0, 'xp': 0,
                               'npcRoutes': dict(runs=[run], done=0, cash=0, xp=0)})


def test_dispatch_retired(env):
    app, clock, path = env
    c = register(app, 'rt_ret')
    create(c)
    set_state(app, cid_of(c), {'garage': ['dostawczak'], 'cash': 5000})
    r = action(c, 'route_dispatch', route='courier', vehicle='dostawczak')
    assert r.status_code == 409 and r.json()['detail'] == E.ROUTES_RETIRED
    st = state(c)['state']
    assert st['npcRoutes']['runs'] == [] and st['cash'] == 5000


def test_inflight_run_still_claimable(env):
    app, clock, path = env
    c = register(app, 'rt_fly')
    create(c)
    inflight(app, c, clock, end_delta=60000)
    assert action(c, 'route_claim').status_code == 409          # jeszcze w drodze
    clock[0] += 60001
    r = action(c, 'route_claim')
    assert r.status_code == 200, r.text
    st = state(c)['state']
    assert st['npcRoutes']['runs'] == [] and st['npcRoutes']['done'] == 1
    assert st['cash'] == 153 and st['xp'] == 8                  # kurier 180 × rower 0,85


def test_inflight_frozen_rush_bonus_kept(env):
    app, clock, path = env
    c = register(app, 'rt_rush')
    create(c)
    inflight(app, c, clock, ev=dict(contract_cash=1.0, contract_xp=1.0, route_cash=1.5))
    assert action(c, 'route_claim').status_code == 200
    assert state(c)['state']['cash'] == round(153 * 1.5)        # premia zamrożona przy wysłaniu zostaje


def test_route_cash_event_gone():
    assert all(e['effect'] != 'route_cash' for e in E.TIMED_EVENTS)
    assert E.ev_mult(0, 'route_cash') == 1.0
