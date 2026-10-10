"""0.49 Garaż w Rezydencji: 5 aut, ulepszenia (3 poziomy), naprawa/serwis, brama VIP."""
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


def create(c, wid=2, name='GarazOne'):
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


def test_garage_catalog_5_plus_1(env):
    """3.1 GDD v3.1: 5 aut na sprzedaż + nagroda Mistrz Rankingu."""
    app, clock, path = env
    c = register(app, 'garage_cat')
    create(c)
    cars = state(c)['catalog']['vehicles']
    assert [g['id'] for g in cars] == ['dostawczak', 'sedan', 'van', 'furgonetka', 'suv', 'mistrz']
    assert all(g.get('img') and g.get('description') for g in cars)
    shop = [g for g in cars if g.get('buyable', True)]
    assert [g['price'] for g in shop] == [2000, 8000, 15000, 25000, 50000]
    assert [g['level'] for g in shop] == [1, 3, 5, 7, 10]
    assert [g['discount'] for g in shop] == [10, 20, 26, 32, 40]
    m = cars[-1]
    assert m['buyable'] is False and m['bonus'] is True and m['discount'] == 45
    assert not any(g.get('vip') or g.get('premium') for g in cars)      # bramki VIP / Ery III usunięte


def test_buy_upgrade_and_discount_stack(env):
    app, clock, path = env
    c = register(app, 'garage_up')
    create(c)
    cid = state(c)['character']['id']
    set_state(app, cid, {'cash': 30000, 'xp': 700})
    # bez rezydencji cap = 1 miejsce: drugie auto nie wejdzie
    assert action(c, 'buy_vehicle', vehicle='dostawczak').status_code == 200
    r = action(c, 'buy_vehicle', vehicle='sedan')
    assert r.status_code == 409 and 'parking' in r.json()['detail']
    # apartament z miejscem parkingowym (slots=1) → cap=2
    assert action(c, 'buy_residence', residence='center-apartment').status_code == 200
    assert action(c, 'buy_vehicle', vehicle='sedan').status_code == 200
    st = state(c)['state']
    assert st['garage'] == ['dostawczak', 'sedan']
    assert st['vehicle']['id'] == 'dostawczak' and st['vehicle']['wear'] == 0
    # ulepszenia: 3 poziomy, +4 p.p. rabatu każdy
    costs = []
    for lvl in range(3):
        before = state(c)['state']['cash']
        r = action(c, 'upgrade_vehicle', vehicle='dostawczak')
        assert r.status_code == 200, r.text
        st = state(c)['state']
        costs.append(before - st['cash'])
        assert st['garageUp']['dostawczak'] == lvl + 1
    assert st['garageUp']['dostawczak'] == E.GARAGE_UP_MAX
    assert costs[0] < costs[1] < costs[2]  # rosnący koszt
    # rabat aktywnego auta: 10% bazowy + 3*4 p.p.
    discount = E.vehicle_discount(st)
    assert discount == 10 + 3 * 4
    # czwarte ulepszenie odrzucone (max)
    r = action(c, 'upgrade_vehicle', vehicle='dostawczak')
    assert r.status_code == 409
    # ulepszenie auta, którego nie ma — błąd
    r = action(c, 'upgrade_vehicle', vehicle='van')
    assert r.status_code == 409


def test_wear_blocks_discount_and_service_fixes(env):
    app, clock, path = env
    c = register(app, 'garage_wear')
    create(c)
    cid = state(c)['character']['id']
    set_state(app, cid, {'cash': 3000})
    assert action(c, 'buy_vehicle', vehicle='dostawczak').status_code == 200
    # zużycie 100% → rabat 0 i serwis dostępny
    set_state(app, cid, {'vehicle': {'id': 'dostawczak', 'wear': 100}})
    st = state(c)['state']
    assert E.vehicle_discount(st) == 0
    r = action(c, 'service_vehicle')
    assert r.status_code == 200, r.text
    st = state(c)['state']
    assert st['vehicle']['wear'] == 0
    assert E.vehicle_discount(st) == 10
    # serwis przed zużyciem — odmowa
    r = action(c, 'service_vehicle')
    assert r.status_code == 409


def test_suv_needs_only_level_and_cash(env):
    """3.1: bez VIP i bez Ery III — tylko poziom (10) i gotówka."""
    app, clock, path = env
    c = register(app, 'garage_vip')
    create(c, name='GarazVip')
    cid = state(c)['character']['id']
    set_state(app, cid, {'cash': 60000, 'xp': 4000})              # poziom 9
    r = action(c, 'buy_vehicle', vehicle='suv')
    assert r.status_code == 409 and 'poziomu 10' in r.json()['detail']
    set_state(app, cid, {'xp': 4500})
    r = action(c, 'buy_vehicle', vehicle='suv')
    assert r.status_code == 200, r.text
    assert state(c)['state']['cash'] == 10000
    r = action(c, 'buy_vehicle', vehicle='mistrz')
    assert r.status_code == 409 and 'nagroda' in r.json()['detail']
