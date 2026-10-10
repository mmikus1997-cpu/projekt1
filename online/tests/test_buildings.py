"""0.55 Moja dzielnica: 6 budynków, rozbudowa 1-5, bramka Sali Chwały."""
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


def create(c, wid=2, name='Budowniczy'):
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


def test_buildings_catalog_and_start(env):
    app, clock, path = env
    c = register(app, 'bld_cat')
    create(c)
    cat = state(c)['catalog']
    assert set(cat['buildings']) == {'residence', 'garage', 'cafe', 'nightclub', 'club', 'hall'}  # 4.1 GDD v3.1
    assert all(v.get('name') and v.get('icon') for v in cat['buildings'].values())
    assert cat['buildingMax'] == 5
    assert cat['buildingCosts'] == [0, 500, 1500, 3000, 6000]
    assert cat['hallCost'] == 10000
    st = state(c)['state']
    assert st['buildings'] == dict(residence=1, garage=1, cafe=1, nightclub=0, club=1, hall=0)
    assert cat['buildingMaxes'] == dict(residence=5, garage=5, cafe=10, nightclub=7, club=1, hall=1)


def test_upgrade_building_costs_and_cap(env):
    app, clock, path = env
    c = register(app, 'bld_up')
    create(c)
    st0 = state(c)['state']
    cash0 = st0['cash']
    r = action(c, 'upgrade_building', building='residence')
    assert r.status_code == 200, r.text
    assert state(c)['state']['buildings']['residence'] == 1   # M5: najpierw budowa (rusztowania)
    clock[0] += 9 * 3600_000
    st = state(c)['state']
    assert st['buildings']['residence'] == 2
    assert st['cash'] == cash0 - 500  # koszt 1->2
    # 2->3 = 1500
    r = action(c, 'upgrade_building', building='residence')
    assert r.status_code == 200, r.text
    assert state(c)['state']['cash'] == cash0 - 500 - 1500
    clock[0] += 9 * 3600_000
    # sufit poziomu 5
    set_state(app, r_json_cid(c), {'cash': 50000, 'buildings': dict(residence=5, garage=1, cafe=1, nightclub=0, club=1, hall=0)})
    r = action(c, 'upgrade_building', building='residence')
    assert r.status_code == 409, r.text


def r_json_cid(c):
    # character id z dowolnego stanu — potrzebne do set_state
    return state(c)['character']['id']


def test_hall_gate_requires_all_max(env):
    app, clock, path = env
    c = register(app, 'bld_hall')
    create(c)
    # bramka: bez 5 poziomów wszystkich budynków → 409
    r = action(c, 'upgrade_building', building='hall')
    assert r.status_code == 409, r.text
    assert 'poziom' in r.json()['detail'].lower()
    # 4.1: stare „wszystkie na 5” już nie wystarcza (Kawiarnia 10, Klub Nocny 7)
    set_state(app, r_json_cid(c), {'cash': 50000, 'buildings': dict(residence=5, garage=5, cafe=5, nightclub=5, club=1, hall=0)})
    assert action(c, 'upgrade_building', building='hall').status_code == 409
    # wszystkie na max, ale brak kasy → 409
    set_state(app, r_json_cid(c), {'cash': 100, 'buildings': dict(residence=5, garage=5, cafe=10, nightclub=7, club=1, hall=0)})
    r = action(c, 'upgrade_building', building='hall')
    assert r.status_code == 409, r.text
    # gotowi + 10000 → otwarcie
    set_state(app, r_json_cid(c), {'cash': 10000})
    r = action(c, 'upgrade_building', building='hall')
    assert r.status_code == 200, r.text
    clock[0] += 9 * 3600_000   # M5: Sala Chwały buduje się 8 h
    st = state(c)['state']
    assert st['buildings']['hall'] == 1
    assert st['cash'] == 0
    # drugi raz → 409
    r = action(c, 'upgrade_building', building='hall')
    assert r.status_code == 409, r.text


def test_upgrade_building_validation(env):
    app, clock, path = env
    c = register(app, 'bld_val')
    create(c)
    # nieznany budynek
    r = action(c, 'upgrade_building', building='bogus')
    assert r.status_code == 409, r.text
    # brak kasy na 1->2 (500) przy 3000 starcie? — ustaw 0
    set_state(app, r_json_cid(c), {'cash': 0})
    r = action(c, 'upgrade_building', building='cafe')
    assert r.status_code == 409, r.text
