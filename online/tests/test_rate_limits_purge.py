"""GDD v3.1 1.5: wygasłe wpisy rate_limits są czyszczone, indeks na until_at istnieje."""
import sqlite3
from fastapi.testclient import TestClient
from server.app import create_app

DAY = 24 * 3600000


def make(tmp_path):
    clock = [1780000000000]
    return create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 'setup.txt'), clock


def test_purge_removes_only_old(tmp_path):
    app, clock = make(tmp_path)
    with sqlite3.connect(app.state.db.path) as db:
        db.executemany('INSERT INTO rate_limits VALUES(?,?,?)', [('old', 1, clock[0] - 2 * DAY), ('recent', 1, clock[0] - 3600000), ('live', 1, clock[0] + 60000)])
    assert app.state.purge_rates() == 1
    with sqlite3.connect(app.state.db.path) as db:
        assert sorted(r[0] for r in db.execute('SELECT key FROM rate_limits')) == ['live', 'recent']


def test_index_exists(tmp_path):
    app, _ = make(tmp_path)
    with sqlite3.connect(app.state.db.path) as db:
        assert 'rate_limits_until' in [r[1] for r in db.execute('PRAGMA index_list(rate_limits)')]


def test_limit_still_enforced_after_purge(tmp_path):
    app, _ = make(tmp_path)
    c = TestClient(app)
    codes = [c.post('/api/auth/login', json={'username': 'nikt', 'password': 'zle-haslo-123456', 'consent': True}).status_code for _ in range(40)]
    app.state.purge_rates()
    codes.append(c.post('/api/auth/login', json={'username': 'nikt', 'password': 'zle-haslo-123456', 'consent': True}).status_code)
    assert 429 in codes and codes[-1] == 429
