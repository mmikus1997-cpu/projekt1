"""GDD v3.1 1.6: wersja silnika walki zapisywana w matches (1.0) i pvp_battles (2.0) z fallbackiem."""
import sqlite3
from server.app import create_app
from server import combat as C
from tests.test_pvp_active import env, register, create, grant, attack  # noqa: F401


def _cid(app, nick):
    with app.state.db.read() as c:
        return c.execute('SELECT id FROM characters WHERE nickname=?', (nick,)).fetchone()[0]


def _spar(app):
    a = register(app, 'cv_a'); b = register(app, 'cv_b')
    create(a, 2, 'CvA'); bb = create(b, 2, 'CvB')['character']
    grant(app, 'CvA', xp=400, tactic='presja'); grant(app, 'CvB', xp=400, tactic='kontra')  # sparing od 2. poziomu
    q = a.post('/api/worlds/2/challenges', json={'target_id': bb['id'], 'tactic': 'presja'})
    assert q.status_code == 200, q.text
    r = b.post(f"/api/challenges/{q.json()['id']}/accept", json={'tactic': 'kontra'})
    assert r.status_code == 200, r.text
    return a, r.json()['match_id']


def test_sparring_saves_v1(env):
    app, _ = env
    a, mid = _spar(app)
    assert a.get(f'/api/matches/{mid}').json()['combat_version'] == C.ENGINE_V1 == '3.0'
    with app.state.db.read() as c:
        assert c.execute('SELECT combat_version FROM matches WHERE id=?', (mid,)).fetchone()[0] == '3.0'


def test_pvp_attack_saves_v2(env):
    app, _ = env
    a = register(app, 'cv_att'); create(a, 2, 'CvAtt')
    b = register(app, 'cv_def'); create(b, 2, 'CvDef')
    grant(app, 'CvAtt', stats=[60, 10, 10, 20, 10], tactic='presja', xp=400)
    r = attack(a, 2, _cid(app, 'CvDef'))
    assert r.status_code == 200, r.text
    assert r.json()['combat_version'] == C.ENGINE_V2 == '3.0'
    with app.state.db.read() as c:
        assert c.execute('SELECT combat_version FROM pvp_battles WHERE id=?', (r.json()['battle'],)).fetchone()[0] == '3.0'


def test_legacy_null_falls_back(env):
    app, _ = env
    a, mid = _spar(app)
    with app.state.db.tx() as c:
        c.execute('UPDATE matches SET combat_version=NULL WHERE id=?', (mid,))
    assert a.get(f'/api/matches/{mid}').json()['combat_version'] == '1.0'


def test_migration_adds_column_to_old_db(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'old.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    with sqlite3.connect(app.state.db.path) as db:   # symulacja bazy v0.59: brak kolumn
        db.execute('ALTER TABLE matches DROP COLUMN combat_version')
        db.execute('ALTER TABLE pvp_battles DROP COLUMN combat_version')
    app2 = create_app(tmp_path / 'old.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    with sqlite3.connect(app2.state.db.path) as db:
        for t in ('matches', 'pvp_battles'):
            assert 'combat_version' in [r[1] for r in db.execute(f'PRAGMA table_info({t})')]
