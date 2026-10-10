"""0.20 QoL: odznaki (character_titles) w stanie świata — puste domyślnie, Pionier po wspólnym celu, limit 12."""
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
    client.post(f'/api/worlds/{wid}/character', json={'nickname': nickname or name[:14], 'accept_test_reset': True})
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


def titles_payload(client):
    return client.get('/api/worlds/1/state').json()['titles']


def test_titles_empty_then_pioneer_badge_after_city_event(env):
    app, clock, path = env
    a = register(app, 'qo_a' + uuid.uuid4().hex[:4], nickname='QO_alfa')
    assert titles_payload(a) == []  # świeża postać: brak odznak
    set_xp(path, 'QO_alfa', 5000)
    admin = register(app, 'qo_ad' + uuid.uuid4().hex[:4], nickname='QO_admin')
    make_admin(app, path, admin)
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'QoL Maraton', 'kind': 'xp', 'target': 5100, 'hours': 24}).status_code == 200
    set_xp(path, 'QO_alfa', 10100)  # przekracza cel → leniwe rozliczenie + odznaka
    assert a.get('/api/worlds/1/state').json()['cityEvent'] is None
    t = titles_payload(a)
    assert len(t) == 1 and set(t[0]) == {'code', 'label'}
    assert t[0]['label'] == 'Pionier: QoL Maraton' and t[0]['code'] == 'event_1'


def test_titles_cap_twelve_newest_first(env):
    app, clock, path = env
    a = register(app, 'qo_b' + uuid.uuid4().hex[:4], nickname='QO_beta')
    db = sqlite3.connect(path / 'game.sqlite3')
    cid = db.execute('SELECT id FROM characters WHERE nickname=?', ('QO_beta',)).fetchone()[0]
    for i in range(15):
        db.execute('INSERT INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,0,?,?,?)', (cid, 'qa_' + str(i), 'Odznaka %02d' % i, 1780000000000 + i))
    db.commit(); db.close()
    t = titles_payload(a)
    assert len(t) == 12  # limit profilu
    assert t[0]['label'] == 'Odznaka 14' and t[11]['label'] == 'Odznaka 03'  # najnowsze najpierw
