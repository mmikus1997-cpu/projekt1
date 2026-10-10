"""0.9 safety & RODO: consent gate, per-address account cap, deletion grace, moderator role, appeals, notices."""
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app, digest


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, tmp_path


def register(app, name, consent=True):
    client = TestClient(app)
    payload = {'username': name, 'password': 'test-password-long-123'}
    if consent:
        payload['consent'] = True
    r = client.post('/api/auth/register', json=payload)
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    return client


def admin(app, path):
    c = register(app, 'operator')
    code = (path / 'setup.txt').read_text().splitlines()[2]
    assert c.post('/api/setup/claim', json={'code': code}).status_code == 200
    return c


def create(c, wid=1, name='SafeOne'):
    r = c.post(f'/api/worlds/{wid}/character', json={'nickname': name, 'accept_test_reset': True})
    assert r.status_code == 200, r.text
    return r.json()


def test_registration_requires_age_or_guardian_attestation(env):
    app, clock, path = env
    c = TestClient(app)
    assert c.post('/api/auth/register', json={'username': 'minor', 'password': 'test-password-long-123'}).status_code == 422
    ok = register(app, 'minor_with_consent')
    assert ok.get('/api/me').status_code == 200
    with app.state.db.read() as db:
        row = db.execute("SELECT consent FROM accounts WHERE username='minor_with_consent'").fetchone()
    assert row['consent'] == '16+'


def test_account_cap_per_address(env):
    app, clock, path = env
    import sqlite3
    with sqlite3.connect(app.state.db.path, timeout=15) as db:  # same address, outside the rate window
        for i in range(8):
            db.execute("INSERT INTO accounts(username,password_hash,created_at,ip_hash) VALUES(?,?,?,?)", (f'farm_{i}', 'x', clock[0], digest('ip|testclient')))
    r = TestClient(app).post('/api/auth/register', json={'username': 'farm_8', 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 409
    assert 'Limit 8 kont' in r.json()['detail']


def test_deletion_grace_period_and_cancel(env):
    app, clock, path = env
    c = register(app, 'leaver')
    create(c)
    r = c.post('/api/account/delete', json={'password': 'test-password-long-123'})
    assert r.status_code == 200 and r.json()['scheduled'] is True
    assert c.get('/api/me').status_code == 401  # logged out immediately
    # Data still present during the grace window; login shows the scheduled marker.
    c2 = TestClient(app)
    again = c2.post('/api/auth/login', json={'username': 'leaver', 'password': 'test-password-long-123'})
    assert again.status_code == 200
    assert again.json()['user']['deletion_at'] > clock[0]
    with app.state.db.read() as db:
        assert db.execute("SELECT 1 FROM characters WHERE nickname='SafeOne'").fetchone()
    # Cancel restores the account.
    c2.headers['X-CSRF-Token'] = again.json()['csrf']
    assert c2.post('/api/account/delete/cancel', json={'password': 'wrong'}).status_code == 403
    assert c2.post('/api/account/delete/cancel', json={'password': 'test-password-long-123'}).status_code == 200
    with app.state.db.read() as db:
        assert db.execute("SELECT deletion_at FROM accounts WHERE username='leaver'").fetchone()['deletion_at'] is None
    # Purge only removes accounts past their deadline.
    assert c2.post('/api/account/delete', json={'password': 'test-password-long-123'}).status_code == 200
    app.state.purge()
    with app.state.db.read() as db:
        assert db.execute("SELECT 1 FROM characters WHERE nickname='SafeOne'").fetchone()
    clock[0] += 8 * 24 * 3600 * 1000
    app.state.purge()
    with app.state.db.read() as db:
        assert not db.execute("SELECT 1 FROM characters WHERE nickname='SafeOne'").fetchone()
        assert not db.execute('PRAGMA foreign_key_check').fetchall()


def test_moderator_role_boundary_and_appeals(env):
    app, clock, path = env
    op = admin(app, path)
    mod = register(app, 'helper')
    uid = op.get('/api/admin/overview').json()['accounts'][0]['id']
    helper_id = next(a['id'] for a in op.get('/api/admin/overview').json()['accounts'] if a['username'] == 'helper')
    assert mod.get('/api/admin/reports').status_code == 403
    assert op.patch(f'/api/admin/accounts/{helper_id}', json={'moderator': True}).status_code == 200
    assert mod.get('/api/admin/reports').status_code == 200
    assert mod.post('/api/admin/worlds', json={'name': 'Nope World'}).status_code == 403  # moderation ≠ administration
    assert mod.get('/api/admin/overview').status_code == 403
    # Appeals require mute history; full cycle ends with the mute lifted.
    assert mod.post('/api/account/appeals', json={'text': 'Proszę o rozpatrzenie kary.'}).status_code == 409
    import sqlite3
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        db.execute("INSERT INTO chat_mutes VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET until_at=excluded.until_at", (helper_id, clock[0] + 86_400_000))
    r = mod.post('/api/account/appeals', json={'text': 'Krótkie odwołanie.'})
    assert r.status_code == 200
    assert mod.post('/api/account/appeals', json={'text': 'Drugie odwołanie od razu.'}).status_code == 409
    appeal = mod.get('/api/account/security').json()['appeals'][0]
    assert appeal['status'] == 'pending'
    assert op.post(f"/api/staff/appeals/{appeal['id']}/resolve", json={'uphold': True}).status_code == 200
    with app.state.db.read() as db:
        assert not db.execute('SELECT 1 FROM chat_mutes WHERE account_id=?', (helper_id,)).fetchone()
    assert mod.get('/api/account/security').json()['appeals'][0]['status'] == 'upheld'
    # Demotion removes staff access.
    assert op.patch(f'/api/admin/accounts/{helper_id}', json={'moderator': False}).status_code == 200
    assert mod.get('/api/admin/reports').status_code == 403


def test_admin_notices_reach_players_and_expire(env):
    app, clock, path = env
    op = admin(app, path)
    c = register(app, 'reader')
    create(c)
    create(c, 2, 'ReaderLab')
    assert op.post('/api/admin/notices', json={'text': 'Nowy świat startuje w piątek.'}).status_code == 200
    assert op.post('/api/admin/notices', json={'text': 'Światowe zlecenia.', 'world_id': 1}).status_code == 200
    data = c.get('/api/worlds/1/state').json()
    texts = [n['text'] for n in data['notices']]
    assert 'Nowy świat startuje w piątek.' in texts and 'Światowe zlecenia.' in texts
    lab = c.get('/api/worlds/2/state').json()
    assert 'Nowy świat startuje w piątek.' in [n['text'] for n in lab['notices']]
    assert 'Światowe zlecenia.' not in [n['text'] for n in lab['notices']]
    assert c.post('/api/admin/notices', json={'text': 'Próba z konta gracza.'}).status_code == 403
    clock[0] += 8 * 24 * 3600 * 1000  # past both notice retention and the 7-day session life
    fresh = TestClient(app)
    fresh.headers['X-CSRF-Token'] = fresh.post('/api/auth/login', json={'username': 'reader', 'password': 'test-password-long-123'}).json()['csrf']
    assert fresh.get('/api/worlds/2/state').json()['notices'] == []
