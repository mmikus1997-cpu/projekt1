"""0.16 Eventy miejskie: wspólny cel świata, odznaki Pioniera, leniwe rozliczanie."""
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


def titles_of(path, nick):
    db = sqlite3.connect(path / 'game.sqlite3')
    rows = db.execute("SELECT label FROM character_titles t JOIN characters c ON c.id=t.character_id WHERE c.nickname=?", (nick,)).fetchall()
    db.close()
    return [r[0] for r in rows]


def test_city_event_xp_flow_baseline_completion_and_pioneer(env):
    app, clock, path = env
    a = register(app, 'ce_a' + uuid.uuid4().hex[:4], nickname='CE_alfa')
    set_xp(path, 'CE_alfa', 5000)  # before the event: baseline only
    admin = register(app, 'ce_ad' + uuid.uuid4().hex[:4], nickname='CE_admin')
    make_admin(app, path, admin)
    r = admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Maraton Miejski', 'description': 'Zdobądźmy razem XP!', 'kind': 'xp', 'target': 5100, 'hours': 48})
    assert r.status_code == 200, r.text
    ev = a.get('/api/worlds/1/state').json()['cityEvent']
    assert ev['name'] == 'Maraton Miejski' and ev['progress'] == 0 and ev['target'] == 5100 and ev['endsAt'] > clock[0]
    assert [k for k in ev] == ['id', 'name', 'description', 'kind', 'district', 'target', 'progress', 'endsAt']
    assert [e['kind'] for e in a.get('/api/worlds/1/community').json()['events']][0] == 'city.event_created'
    # non-admin cannot create; second active event blocked
    assert a.post('/api/admin/events', json={'world_id': 1, 'name': 'Nielegalny', 'kind': 'xp', 'target': 100, 'hours': 24}).status_code == 403
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Podwójny', 'kind': 'xp', 'target': 100, 'hours': 24}).status_code == 409
    # progress grows with XP; completion grants the Pioneer badge to residents
    set_xp(path, 'CE_alfa', 10100)
    st = a.get('/api/worlds/1/state').json()
    assert st['cityEvent'] is None  # settled lazily, card disappears
    assert 'Pionier: Maraton Miejski' in titles_of(path, 'CE_alfa')
    assert [e['kind'] for e in a.get('/api/worlds/1/community').json()['events']][0] == 'city.event_done'
    ov = admin.get('/api/admin/overview').json()['events']
    assert ov[0]['status'] == 'done' and ov[0]['name'] == 'Maraton Miejski'
    # new event possible after completion; new resident also gets a badge when it lands later
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Druga Runda', 'kind': 'xp', 'target': 100, 'hours': 24}).status_code == 200


def test_prestige_event_uses_org_investments(env):
    app, clock, path = env
    a = register(app, 'ce_b' + uuid.uuid4().hex[:4], nickname='CE_beta')
    a.post('/api/worlds/1/organizations', json={'name': 'Event Org', 'tag': 'EVO', 'description': ''})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 300})
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})  # baseline
    admin = register(app, 'ce_bd' + uuid.uuid4().hex[:4], nickname='CE_beta2')
    make_admin(app, path, admin)
    r = admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Noc Prestiżu', 'kind': 'prestige', 'district': 'Portowe', 'target': 100, 'hours': 24})
    assert r.status_code == 200, r.text
    ev = a.get('/api/worlds/1/state').json()['cityEvent']
    assert ev['progress'] == 0 and ev['district'] == 'Portowe'  # existing prestige excluded
    r = a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    assert r.status_code == 200
    st = a.get('/api/worlds/1/state').json()
    assert st['cityEvent'] is None
    assert 'Pionier: Noc Prestiżu' in titles_of(path, 'CE_beta')


def test_deadline_miss_no_badge_and_cancel(env):
    app, clock, path = env
    a = register(app, 'ce_c' + uuid.uuid4().hex[:4], nickname='CE_gamma')
    admin = register(app, 'ce_cd' + uuid.uuid4().hex[:4], nickname='CE_gamma2')
    make_admin(app, path, admin)
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Wyścig z Czasem', 'kind': 'xp', 'target': 499999, 'hours': 24}).status_code == 200
    clock[0] += 25 * 3600 * 1000
    a2 = register(app, 'ce_c2' + uuid.uuid4().hex[:4], nickname='CE_gamma3')  # fresh session (old expired)
    st = a2.get('/api/worlds/1/state').json()
    assert st['cityEvent'] is None
    assert [e['kind'] for e in a2.get('/api/worlds/1/community').json()['events']][0] == 'city.event_missed'
    assert titles_of(path, 'CE_gamma') == []  # expired event grants nothing
    # cancel path: admin ends an active event; residents present at cancel time get notified, no badge
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Do Anulacji', 'kind': 'xp', 'target': 100, 'hours': 48}).status_code == 200
    a3 = register(app, 'ce_c3' + uuid.uuid4().hex[:4], nickname='CE_gamma4')  # resident before the cancel
    eid = admin.get('/api/admin/overview').json()['events'][0]['id']
    assert admin.post(f'/api/admin/events/{eid}/cancel', json={}).status_code == 200
    assert admin.post(f'/api/admin/events/{eid}/cancel', json={}).status_code == 409
    assert [e['kind'] for e in a3.get('/api/worlds/1/community').json()['events']][0] == 'city.event_cancelled'
    assert titles_of(path, 'CE_gamma3') == []
    # validation: unknown district, bad target range, unknown world
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Zły', 'kind': 'prestige', 'district': 'NieMa', 'target': 100, 'hours': 24}).status_code == 422
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Zły', 'kind': 'xp', 'target': 50, 'hours': 24}).status_code == 422
    assert admin.post('/api/admin/events', json={'world_id': 999, 'name': 'Zły', 'kind': 'xp', 'target': 100, 'hours': 24}).status_code == 404
