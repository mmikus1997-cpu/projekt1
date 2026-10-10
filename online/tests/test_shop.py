"""0.14 Sklep dev: brama zakupów domyślnie wyłączona, pozorowana kasa, realne efekty VIP/starter/energia/przyspieszenie."""
import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, tmp_path


def register(app, name, wid=1, nickname=None):
    client = TestClient(app);client.app_ref = app
    r = client.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    client.post(f'/api/worlds/{wid}/character', json={'nickname': nickname or name[:14], 'accept_test_reset': True})
    return client


def enable(app, c):
    r = c.post('/api/shop/gate', json={'enable': True, 'statement': True})
    assert r.status_code == 200, r.text
    return r


def state_of(c, wid=1):
    return c.get(f'/api/worlds/{wid}/state').json()['state']


class Keys:
    def __init__(self):self.n = 0
    def next(self):
        self.n += 1
        return {'Idempotency-Key': 'shop-test-key-%019d' % self.n}


def start_contract(c, keys, contract='inventory'):
    d = {'inventory': 3, 'delivery': 8, 'event': 3}.get(contract)  # 0.45: kontrakty w swoich dzielnicach
    if d:
        with c.app_ref.state.db.tx() as cx:
            cx.execute('UPDATE characters SET current_district=? WHERE world_id=1', (d,))
    r = c.post('/api/worlds/1/actions', json={'action': 'contract', 'contract': contract}, headers=keys.next())
    assert r.status_code == 200, r.text


def claim_contract(c, keys):
    tid = state_of(c)['contracts'][0]['id']
    r = c.post('/api/worlds/1/actions', json={'action': 'claim_contract', 'task_id': tid}, headers=keys.next())
    assert r.status_code == 200, r.text
    return r.json()


def test_gate_default_off_statement_and_audit(env):
    app, clock, path = env
    a = register(app, 'shopa' + uuid.uuid4().hex[:4], nickname='Shop_alfa')
    r = a.post('/api/shop/checkout', json={'sku': 'vip7', 'wid': 1})
    assert r.status_code == 403 and 'wyłączone' in r.json()['detail']
    assert a.post('/api/shop/gate', json={'enable': True}).status_code == 422  # brak oświadczenia
    assert a.post('/api/shop/gate', json={'enable': True, 'statement': False}).status_code == 422
    enable(app, a)
    assert a.get('/api/shop').json()['state']['spendingEnabled'] is True
    assert a.post('/api/shop/gate', json={'enable': False}).status_code == 200
    assert a.get('/api/shop').json()['state']['spendingEnabled'] is False
    enable(app, a)
    r = a.post('/api/shop/checkout', json={'sku': 'vip7', 'wid': 1})
    assert r.status_code == 200 and r.json()['sku'] == 'vip7'
    db = sqlite3.connect(path / 'game.sqlite3')
    audit = db.execute("SELECT event FROM audit WHERE event LIKE 'shop.%' ORDER BY id").fetchall()
    purchases = db.execute('SELECT sku,price,status FROM shop_purchases').fetchall()
    db.close()
    assert any(ev[0] == 'shop.gate_enabled' for ev in audit) and any(ev[0] == 'shop.paid_dev' for ev in audit)
    assert purchases and purchases[0][0] == 'vip7' and purchases[0][1] == '7,99 zł' and purchases[0][2] == 'paid_dev'
    shop = a.get('/api/shop').json()
    assert shop['history'][0]['price'] == '7,99 zł' and shop['history'][0]['status'] == 'paid_dev'
    assert all(p['price'].endswith('zł') for p in shop['products'])  # ceny zawsze w realnej walucie


def test_vip_contract_bonus_stacking_and_new_character(env, flat_stats):
    app, clock, path = env
    a = register(app, 'shopb' + uuid.uuid4().hex[:4], nickname='Shop_beta')
    enable(app, a)
    keys = Keys()
    start_contract(a, keys);clock[0] += 6 * 60 * 1000
    claim_contract(a, keys)
    base = state_of(a)['cash']
    start_contract(a, keys);clock[0] += 6 * 60 * 1000
    claim_contract(a, keys)
    gain_no_vip = state_of(a)['cash'] - base
    assert gain_no_vip > 0
    assert a.post('/api/shop/checkout', json={'sku': 'vip7', 'wid': 1}).status_code == 200
    until7 = a.get('/api/shop').json()['state']['vipUntil']
    assert a.post('/api/shop/checkout', json={'sku': 'vip30', 'wid': 1}).status_code == 200
    until30 = a.get('/api/shop').json()['state']['vipUntil']
    assert until30 - until7 == 30 * 24 * 3600 * 1000  # VIP sumuje okresy, nie zastępuje
    assert state_of(a)['vipUntil'] == until30  # stan postaci opieczętowany
    start_contract(a, keys);clock[0] += 6 * 60 * 1000
    before = state_of(a)['cash']
    claim_contract(a, keys)
    gain_vip = state_of(a)['cash'] - before
    assert gain_vip == round(gain_no_vip * 1.25)  # ten sam kontrakt, ten sam dzień
    # postać utworzona po zakupie też dziedziczy VIP
    db = sqlite3.connect(path / 'game.sqlite3')
    row = db.execute("SELECT state_json FROM characters WHERE nickname='Shop_beta'").fetchone()
    db.close()
    assert json.loads(row[0])['vipUntil'] == until30


def test_starter_pack_once_gear_rest_charge(env):
    app, clock, path = env
    a = register(app, 'shopc' + uuid.uuid4().hex[:4], nickname='Shop_gamma')
    enable(app, a)
    r = a.post('/api/shop/checkout', json={'sku': 'starter', 'wid': 1})
    assert r.status_code == 200 and '5 000' in r.json()['message']
    st = state_of(a)
    assert st['cash'] == 5300  # 300 start + 5000
    for item in ('analyst-band', 'agile-shoes', 'captain-shirt'):
        assert item in st['inventory']
    assert st['restInstant'] == 1
    assert a.post('/api/shop/checkout', json={'sku': 'starter', 'wid': 1}).status_code == 409
    assert a.get('/api/shop').json()['state']['starter'] is True
    # charge z pakietu: najbliższy odpoczynek kończy się natychmiast
    keys = Keys()
    a.post('/api/worlds/1/actions', json={'action': 'buy_residence', 'residence': 'studio-flat'}, headers=keys.next())
    r = a.post('/api/worlds/1/actions', json={'action': 'rest_start', 'rest': 'nap'}, headers=keys.next())
    assert 'natychmiast' in (r.json().get('message') or ''), r.text
    st = state_of(a)
    assert st['restInstant'] == 0 and st['rest']['end'] == st['rest']['start']
    r = a.post('/api/worlds/1/actions', json={'action': 'rest_claim'}, headers=keys.next()).json()
    assert r['state']['energy'] == 130 and r['state']['rest'] is None  # nap (+10) claimed instantly


def test_energy_limit_and_clamp(env):
    app, clock, path = env
    a = register(app, 'shopd' + uuid.uuid4().hex[:4], nickname='Shop_delta')
    enable(app, a)
    assert a.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 1}).status_code == 200
    assert a.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 1}).status_code == 200
    assert a.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 1}).status_code == 409
    assert state_of(a)['energy'] == 240  # 120 + 100 + 100, klamra na 240
    db = sqlite3.connect(path / 'game.sqlite3')
    used = db.execute("SELECT count FROM shop_usage WHERE sku='energy'").fetchone()[0]
    db.close()
    assert used == 2


def test_speedup_halves_running_contract(env):
    app, clock, path = env
    a = register(app, 'shope' + uuid.uuid4().hex[:4], nickname='Shop_epsylon')
    enable(app, a)
    assert a.post('/api/shop/checkout', json={'sku': 'speedup', 'wid': 1}).status_code == 409  # nic nie trwa
    keys = Keys()
    start_contract(a, keys)
    t0 = state_of(a)['contracts'][0]
    assert a.post('/api/shop/checkout', json={'sku': 'speedup', 'wid': 1}).status_code == 200
    t1 = state_of(a)['contracts'][0]
    assert t1['end'] == t0['end'] - (t0['end'] - t0['start']) // 2
    for _ in range(2):
        start_contract(a, keys)
        assert a.post('/api/shop/checkout', json={'sku': 'speedup', 'wid': 1}).status_code == 200
    assert a.post('/api/shop/checkout', json={'sku': 'speedup', 'wid': 1}).status_code == 409  # limit 3/dzień


def test_skins_buy_equip_and_state_summary(env):
    app, clock, path = env
    a = register(app, 'shopf' + uuid.uuid4().hex[:4], nickname='Shop_feniks')
    assert a.post('/api/shop/equip', json={'skin': 'skin_gold'}).status_code == 409  # nie kupiona
    enable(app, a)
    assert a.post('/api/shop/checkout', json={'sku': 'skin_copper'}).status_code == 200
    assert a.post('/api/shop/checkout', json={'sku': 'skin_copper'}).status_code == 409  # drugi raz nie
    assert a.get('/api/worlds/1/state').json()['shop']['skin'] == 'skin_copper'
    assert a.post('/api/shop/equip', json={'skin': 'skin_gold'}).status_code == 409  # gold niezakupiona
    assert a.post('/api/shop/equip', json={'skin': ''}).status_code == 200
    assert a.get('/api/worlds/1/state').json()['shop']['skin'] == ''
    shop_state = a.get('/api/worlds/1/state').json()['shop']
    assert set(shop_state) == {'spendingEnabled', 'vipActive', 'vipUntil', 'starter', 'skin', 'ownedSkins', 'guardian', 'banner'}
    assert 'skin_copper' in shop_state['ownedSkins']  # owned list drives the character-view picker
    assert 'BEZ prawdziwych płatności' in shop_state['banner']
