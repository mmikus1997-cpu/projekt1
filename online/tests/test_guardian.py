"""0.19 Zgoda opiekuna (RODO art. 8): ścieżka <16 lat, tygodniowy limit wydatków, cofnięcie zamyka zakupy."""
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]  # czwartek 1970-01-22 UTC; tydzień wystartuje w poniedziałek 1970-01-19
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, tmp_path


def register(app, name, wid=1, nickname=None):
    client = TestClient(app)
    r = client.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    client.post(f'/api/worlds/{wid}/character', json={'nickname': nickname or name[:14], 'accept_test_reset': True})
    return client


def relogin(app, name):
    client = TestClient(app)
    r = client.post('/api/auth/login', json={'username': name, 'password': 'test-password-long-123'})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    return client


class Keys:
    def __init__(self):self.n = 0
    def next(self):
        self.n += 1
        return {'Idempotency-Key': 'guardian-test-key-%018d' % self.n}


def buy(client, sku, keys, wid=1):
    return client.post('/api/shop/checkout', json={'sku': sku, 'wid': wid}, headers=keys.next())


def shop_state(client):
    return client.get('/api/shop').json()['state']


def test_minor_gate_needs_consent_weekly_limit_enforced(env):
    app, clock, path = env
    uname = 'gd_a' + uuid.uuid4().hex[:4]
    a = register(app, uname, nickname='GD_alfa')
    keys = Keys()
    # minor bez zgody opiekuna: włączenie blokowane
    assert a.post('/api/shop/gate', json={'enable': True, 'statement': True, 'minor': True}).status_code == 422
    # walidacje formularza zgody
    assert a.post('/api/shop/guardian', json={'guardian_name': 'A', 'weekly_limit': 500}).status_code == 422
    assert a.post('/api/shop/guardian', json={'guardian_name': 'Anna Przykładowa', 'weekly_limit': 100}).status_code == 422
    assert a.post('/api/shop/guardian', json={'guardian_name': 'Anna Przykładowa', 'weekly_limit': 30000}).status_code == 422
    r = a.post('/api/shop/guardian', json={'guardian_name': 'Anna Przykładowa', 'weekly_limit': 500})
    assert r.status_code == 200, r.text
    g = r.json()['guardian']
    assert g['weeklyLimit'] == 500 and g['weeklySpent'] == 0 and g['guardianName'] == 'Anna Przykładowa'
    assert a.post('/api/shop/guardian', json={'guardian_name': 'Inny Opiekun', 'weekly_limit': 1000}).status_code == 409  # jedna aktywna zgoda
    # brama dla osoby <16 przechodzi dopiero po zgodzie
    assert a.post('/api/shop/gate', json={'enable': True, 'statement': True, 'minor': True}).status_code == 200
    # energiapak 4,99 zł mieści się w limicie 5 zł/tydzień
    assert buy(a, 'energy', keys).status_code == 200
    g = shop_state(a)['guardian']
    assert g['weeklySpent'] == 499
    # kolejny zakup 2,99 zł przekroczyłby limit → 409
    r = buy(a, 'speedup', keys)
    assert r.status_code == 409 and 'limit' in r.json()['detail'].lower()
    # nowy tydzień (poniedziałek +8 dni) — licznik startuje od zera; świeża sesja tego samego konta
    clock[0] += 8 * 24 * 3600 * 1000
    a = relogin(app, uname)
    assert buy(a, 'energy', keys).status_code == 200  # nowy doba UTC → dzienny limit energii od nowa
    g = shop_state(a)['guardian']
    assert g['weeklySpent'] == 499  # starzy wydatki wypadły z bieżącego tygodnia


def test_revoke_disables_spending_and_leaves_trace(env):
    app, clock, path = env
    a = register(app, 'gd_c' + uuid.uuid4().hex[:4], nickname='GD_gamma')
    keys = Keys()
    a.post('/api/shop/guardian', json={'guardian_name': 'Jan Testowy', 'weekly_limit': 2000})
    a.post('/api/shop/gate', json={'enable': True, 'statement': True, 'minor': True})
    assert buy(a, 'energy', keys).status_code == 200
    assert a.post('/api/shop/guardian/revoke', json={}).status_code == 200
    assert a.post('/api/shop/guardian/revoke', json={}).status_code == 404  # drugi raz niczego nie cofa
    s = shop_state(a)
    assert s['spendingEnabled'] is False and s['guardian'] is None  # zgoda cofnięta, zakupy zamknięte
    assert buy(a, 'energy', keys).status_code == 403  # brama domknięta revokacją
    # po revokacji można zapisać nową zgodę i włączyć zakupy ponownie
    assert a.post('/api/shop/guardian', json={'guardian_name': 'Jan Testowy', 'weekly_limit': 1000}).status_code == 200
    assert a.post('/api/shop/gate', json={'enable': True, 'statement': True, 'minor': True}).status_code == 200
    assert buy(a, 'skin_copper', keys).status_code == 200  # 3,99 zł: 4,99 + 3,99 = 8,98 ≤ 10 zł nowego limitu
    db = sqlite3.connect(path / 'game.sqlite3')
    events = [r[0] for r in db.execute("SELECT event FROM audit WHERE event LIKE 'shop.%' ORDER BY id")]
    db.close()
    for ev in ('shop.guardian_consent', 'shop.guardian_revoke', 'shop.gate_enabled', 'shop.paid_dev'):
        assert ev in events, ev


def test_adult_path_unchanged_and_export_grows(env):
    app, clock, path = env
    a = register(app, 'gd_d' + uuid.uuid4().hex[:4], nickname='GD_delta')
    keys = Keys()
    # ścieżka 16+: bez zgody opiekuna, pole minor domyślnie False
    assert a.post('/api/shop/gate', json={'enable': True, 'statement': True}).status_code == 200
    assert buy(a, 'energy', keys).status_code == 200
    s = shop_state(a)
    assert s['spendingEnabled'] is True and s['guardian'] is None
    # eksport konta dalej działa (RODO: dostęp do danych)
    r = a.get('/api/account/export')
    assert r.status_code == 200
