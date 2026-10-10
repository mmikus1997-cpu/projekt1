"""0.57.0 Sojusze: wspólne budynki organizacji kupowane z funduszu; premie dla członków."""
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


def register(app, name, nick):
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/1/character', json={'nickname': nick, 'accept_test_reset': True}).status_code == 200
    return c


def sql(app, q, args=()):
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        return db.execute(q, args).fetchall()


def patch_state(app, nick, patch):
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        cid, sj = db.execute('SELECT id,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
        st = json.loads(sj); st.update(patch)
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st), cid))


def build(c, b):
    return c.post('/api/worlds/1/organizations/building', json={'building': b})


def test_catalog_and_mult():
    assert [b['id'] for b in E.ALLY_BUILDINGS] == ['fast_build', 'cheap_repair', 'freedom']
    assert E.ALLY_COST == [2000, 5000, 10000] and E.ALLY_MAX == 3
    assert E.ally_mult({'ally': {'freedom': 2}}, 'freedom') == pytest.approx(0.8)
    assert E.ally_mult({'ally': {'cheap_repair': 9}}, 'cheap_repair') == pytest.approx(0.55)  # cap 3
    assert E.ally_mult({}, 'fast_build') == 1


def test_build_from_fund_with_gates(env):
    app, clock, path = env
    a = register(app, 'al_a' + uuid.uuid4().hex[:4], 'Lider')
    b = register(app, 'al_b' + uuid.uuid4().hex[:4], 'Obcy')
    assert b.get('/api/worlds/1/state').json()['catalog']['allyBuildings'][2]['name'] == 'Wolność'
    r = a.post('/api/worlds/1/organizations', json={'name': 'Sojusz Test', 'tag': 'SOJ', 'description': ''})
    assert r.status_code == 200, r.text
    # spoza organizacji: 403
    assert build(b, 'freedom').status_code == 403
    # za mało funduszu: 409
    r = build(a, 'freedom'); assert r.status_code == 409 and 'funduszu' in r.json()['detail']
    sql(app, "UPDATE organizations SET fund=20000 WHERE tag='SOJ'")
    assert build(a, 'bogus').status_code == 422
    for lv, left in ((1, 18000), (2, 13000), (3, 3000)):
        r = build(a, 'freedom'); assert r.status_code == 200, r.text
        assert r.json()['buildings']['freedom'] == lv and r.json()['fund'] == left
    r = build(a, 'freedom'); assert r.status_code == 409 and 'maksymalny' in r.json()['detail']
    com = a.get('/api/worlds/1/community').json()
    assert com['organization']['buildings'] == {'freedom': 3}


def test_cheap_repair_discounts_service(env):
    app, clock, path = env
    a = register(app, 'al_r' + uuid.uuid4().hex[:4], 'Mechanik')
    a.post('/api/worlds/1/organizations', json={'name': 'Warsztat', 'tag': 'WRS', 'description': ''})
    sql(app, "UPDATE organizations SET fund=2000 WHERE tag='WRS'")
    assert build(a, 'cheap_repair').status_code == 200
    patch_state(app, 'Mechanik', {'garage': ['dostawczak'], 'vehicle': {'id': 'dostawczak', 'wear': 100}, 'cash': 1000})
    r = a.post('/api/worlds/1/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': 'service_vehicle'})
    assert r.status_code == 200, r.text
    st = a.get('/api/worlds/1/state').json()['state']
    assert st['cash'] == 1000 - round(300 * 0.85)  # 3.1: serwis Dostawczaka 300 $ → 255 $
