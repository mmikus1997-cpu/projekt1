"""0.23 Dystynkcja dnia: raz na dobę UTC za zapracowany czyn; czysto kosmetyczna, bez presji."""
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
    client = TestClient(app)
    r = client.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    r = client.post(f'/api/worlds/{wid}/character', json={'nickname': nickname or name[:14], 'accept_test_reset': True})
    assert r.status_code == 200, r.text
    return client


def relogin(app, name):
    client = TestClient(app)
    r = client.post('/api/auth/login', json={'username': name, 'password': 'test-password-long-123'})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    return client


def state(c, wid=1):
    return c.get(f'/api/worlds/{wid}/state').json()


def claim(c, wid=1):
    return c.post(f'/api/worlds/{wid}/distinction/claim', json={})


def test_claim_requires_a_deed_and_is_once_per_day(env):
    app, clock, path = env
    a = register(app, 'dd_a' + uuid.uuid4().hex[:4], nickname='DD_alfa')
    d = state(a)['distinction']
    assert d['eligible'] is False and d['claimed'] is None and d['pending'] is None and d['count'] == 0
    r = claim(a)
    assert r.status_code == 409 and 'zapracowała' in r.json()['detail']
    # czyn: wpłata do funduszu organizacji (najpierw org — tworzenie jest bezpłatne)
    a.post('/api/worlds/1/organizations', json={'name': 'Dystynk QA', 'tag': 'DYQ', 'description': ''})
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 100}).status_code == 200
    d = state(a)['distinction']
    assert d['eligible'] is True and d['pending']['kind'] == 'fund' and d['claimed'] is None
    r = claim(a)
    assert r.status_code == 200 and r.json()['kind'] == 'fund' and 'Wsparcie organizacji' in r.json()['label']
    d = state(a)['distinction']
    assert d['eligible'] is False and d['claimed']['kind'] == 'fund' and d['count'] == 1
    # kolejny czyn tego samego dnia nie daje drugiej dystynkcji
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 50}).status_code == 200
    assert claim(a).status_code == 409 and 'już odebrana' in claim(a).json()['detail']
    # anonim: brak sesji → odmowa
    assert TestClient(app).post('/api/worlds/1/distinction/claim', json={}).status_code in (401, 403)


def test_next_day_resets_and_contract_deed_counts(env):
    app, clock, path = env
    uname = 'dd_b' + uuid.uuid4().hex[:4]
    a = register(app, uname, nickname='DD_beta')
    with app.state.db.tx() as cx:
        cx.execute('UPDATE characters SET current_district=8 WHERE world_id=1')  # 0.45: dostawa z Przedmieść
    a.post('/api/worlds/1/organizations', json={'name': 'Nowy Dzień QA', 'tag': 'NDQ', 'description': ''})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    assert claim(a).status_code == 200
    # kontrakt: start → upływ czasu → odbiór nagrody = czyn dnia
    keys = iter({'Idempotency-Key': 'dd-contract-%019d' % i} for i in range(1, 9))
    r = a.post('/api/worlds/1/actions', json={'action': 'contract', 'contract': 'delivery'}, headers=next(keys))
    assert r.status_code == 200, r.text
    clock[0] += 11 * 60 * 1000  # dostawa trwa 10 minut
    r = a.post('/api/worlds/1/actions', json={'action': 'claim_contract', 'task_id': 1}, headers=next(keys))
    assert r.status_code == 200, r.text
    d = state(a)['distinction']
    assert d['eligible'] is False and d['claimed']['kind'] == 'fund'  # dziś już odebrana (fund)
    assert d['pending']['kind'] == 'contract'  # ale czyn kontraktowy dnia został odnotowany
    clock[0] += 26 * 3600 * 1000  # nowy dzień UTC
    a = relogin(app, uname)
    d = state(a)['distinction']
    assert d['eligible'] is False and d['claimed'] is None and d['count'] == 1  # licznik trwa, dzień czysty
    # QA 3: trening natychmiastowy jest czynem nowego dnia
    r = a.post('/api/worlds/1/actions', json={'action': 'train', 'stat': 0}, headers=next(keys))
    assert r.status_code == 200, r.text
    r = claim(a)
    assert r.status_code == 200 and r.json()['kind'] == 'training' and 'Trening dnia' in r.json()['label']
    assert state(a)['distinction']['count'] == 2
    # ślad w bazie: unikalność (character, day)
    db = sqlite3.connect(path / 'game.sqlite3')
    rows = db.execute('SELECT day,kind FROM daily_distinctions ORDER BY id').fetchall()
    db.close()
    assert len({r[0] for r in rows}) == 2 and {r[1] for r in rows} == {'fund', 'training'}


def test_world_scope_isolation(env):
    app, clock, path = env
    a = register(app, 'dd_c' + uuid.uuid4().hex[:4], wid=1, nickname='DD_gamma')
    b = register(app, 'dd_d' + uuid.uuid4().hex[:4], wid=2, nickname='DD_delta')
    a.post('/api/worlds/1/organizations', json={'name': 'Izolacja QA', 'tag': 'IZQ', 'description': ''})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    assert claim(a).status_code == 200
    # ten sam dzień, inny świat: b zaczyna z czystą kartą
    d = state(b, wid=2)['distinction']
    assert d['count'] == 0 and d['claimed'] is None and d['eligible'] is False
