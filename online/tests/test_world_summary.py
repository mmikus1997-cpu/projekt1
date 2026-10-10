"""0.22 Podsumowanie świata dla administratora: obraz świata tylko-do-odczytu, per świat."""
import json
import sqlite3
import uuid

import pytest

from server import economy as E
from fastapi.testclient import TestClient

from server.app import create_app


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, tmp_path


def register(app, name, wid=1, nickname=None):
    client = TestClient(app)
    r = client.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    r = client.post(f'/api/worlds/{wid}/character', json={'nickname': nickname or name[:14], 'accept_test_reset': True})
    assert r.status_code == 200, r.text
    return client


def make_admin(app, path, client):
    code = (path / 'setup.txt').read_text().splitlines()[2].strip()
    r = client.post('/api/setup/claim', json={'code': code})
    assert r.status_code == 200, r.text
    return client


def set_xp(path, nick, xp):
    db = sqlite3.connect(path / 'game.sqlite3')
    row = db.execute('SELECT id,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
    st = json.loads(row[1]); st['xp'] = xp
    db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st, separators=(',', ':')), row[0]))
    db.commit(); db.close()


def test_summary_full_picture_world_one(env):
    app, clock, path = env
    a = register(app, 'ws_a' + uuid.uuid4().hex[:4], nickname='WS_alfa')
    set_xp(path, 'WS_alfa', 5000)
    org = a.post('/api/worlds/1/organizations', json={'name': 'Podsumowa QA', 'tag': 'PQA', 'description': ''}).json()
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'district': '', 'target': 200, 'hours': 24})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    admin = register(app, 'ws_ad' + uuid.uuid4().hex[:4], nickname='WS_admin')
    make_admin(app, path, admin)
    assert admin.post('/api/admin/notices', json={'text': 'Ogłoszenie testowe.', 'world_id': 1}).status_code == 200
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Cel Świata', 'kind': 'xp', 'target': 100, 'hours': 24}).status_code == 200
    # dev-sklep: energia na świecie 1 + VIP na koncie mieszkańca
    a.post('/api/shop/gate', json={'enable': True, 'statement': True})
    keys = iter({'Idempotency-Key': 'ws-key-%021d' % i} for i in range(1, 9))
    assert a.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 1}, headers=next(keys)).status_code == 200
    assert a.post('/api/shop/checkout', json={'sku': 'vip30'}, headers=next(keys)).status_code == 200
    # dostęp: gracz 403, anonim 401, zły świat 404
    assert a.get('/api/admin/worlds/1/summary').status_code == 403
    assert TestClient(app).get('/api/admin/worlds/1/summary').status_code == 401
    assert admin.get('/api/admin/worlds/999/summary').status_code == 404
    s = admin.get('/api/admin/worlds/1/summary').json()
    assert s['world']['id'] == 1 and s['world']['name'] and 'speed' in s['world']
    assert s['population'] == 2  # alfa + admin (świat 1)
    assert s['cityXp'] >= 5000
    assert s['top'][0]['nickname'] == 'WS_alfa' and s['top'][0]['xp'] >= 5000 and s['top'][0]['level'] >= 1
    assert s['newest']['nickname'] == 'WS_admin'
    assert s['orgs'] == 1
    assert s['topOrgs'] == [dict(name='Podsumowa QA', tag='PQA', prestige=100, members=1)]
    assert s['contracts'] == dict(active=0, done=1, missed=0)
    assert s['event'] and s['event']['status'] == 'active' and s['event']['name'] == 'Cel Świata' and s['event']['progress'] == 0
    kinds = set()
    db = sqlite3.connect(path / 'game.sqlite3')
    kinds = {r[0] for r in db.execute('SELECT kind FROM chronicle WHERE world_id=1')}
    db.close()
    assert {'org_founded', 'city_new', 'org_done'} <= kinds
    assert s['chronicleCount'] >= 3
    assert s['noticesCount'] == 1
    # w podsumowaniu liczą się zakupy per świat (energia/starter/przyspieszenie); VIP jest kontowy → poza tym licznikiem
    assert s['shop']['purchases'] == 1 and s['shop']['cents'] == 499
    assert s['vipResidents'] == 1
    assert set(s) == {'world', 'population', 'cityXp', 'top', 'newest', 'orgs', 'topOrgs', 'contracts', 'event', 'chronicleCount', 'noticesCount', 'shop', 'vipResidents', 'daily'}
    # dzienne agregaty: czyny (wpłaty/inwestycja) + dev-sklep w jednym wierszu dziś
    assert s['daily'][0]['deeds'] == 4 and s['daily'][0]['shop_cents'] == 499 and s['daily'][0]['day'] == E.day_start(1780000000000)


def test_summary_empty_second_world(env):
    app, clock, path = env
    a = register(app, 'ws_b' + uuid.uuid4().hex[:4], nickname='WS_beta')  # świat 1
    admin = register(app, 'ws_bd' + uuid.uuid4().hex[:4], nickname='WS_admin2')
    make_admin(app, path, admin)
    s = admin.get('/api/admin/worlds/2/summary').json()
    assert s['world']['id'] == 2
    assert s['population'] == 0 and s['cityXp'] == 0 and s['top'] == [] and s['newest'] is None
    assert s['orgs'] == 0 and s['topOrgs'] == []
    assert s['contracts'] == dict(active=0, done=0, missed=0)
    assert s['event'] is None and s['chronicleCount'] == 0 and s['noticesCount'] == 0
    assert s['shop'] == dict(purchases=0, cents=0) and s['vipResidents'] == 0
