"""0.13: sezonowe tytuły reputacyjne — nadawanie, publikacja, zero wpływu na siłę."""
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


def set_xp(path, nick, xp):
    db = sqlite3.connect(path / 'game.sqlite3')
    row = db.execute('SELECT id,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
    st = json.loads(row[1]); st['xp'] = xp
    db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st, separators=(',', ':')), row[0]))
    db.commit(); db.close()


def test_titles_granted_published_and_harmless(env):
    app, clock, path = env
    aname = 'titaa' + uuid.uuid4().hex[:4]
    a = register(app, aname, nickname='Tit_alfa')     # world 1
    register(app, 'titbe' + uuid.uuid4().hex[:4], wid=2, nickname='Tit_beta')  # world 2
    register(app, 'titga' + uuid.uuid4().hex[:4], wid=2, nickname='Tit_gamma')
    register(app, 'titde' + uuid.uuid4().hex[:4], nickname='Tit_delta')
    set_xp(path, 'Tit_beta', 50000)   # global champion (world 2)
    set_xp(path, 'Tit_alfa', 20000)   # global 2nd, world 1 leader
    set_xp(path, 'Tit_gamma', 8000)   # global 3rd, world 2 second
    st_before = a.get('/api/worlds/1/state').json()['state']

    clock[0] += 29 * 86400000
    probe = register(app, 'titpr' + uuid.uuid4().hex[:4], nickname='Tit_probe')
    probe.get('/api/ranking/global/1')  # ranking read triggers the lazy finalization + titles
    db = sqlite3.connect(path / 'game.sqlite3')
    titles = [(r[0], r[1], r[2]) for r in db.execute('SELECT season,code,label FROM character_titles')]
    db.close()
    season1 = {(c, l) for sn, c, l in titles if sn == 1}
    assert ('champion', 'Mistrz Sezonu 1') in season1
    # every world grants its own leader, even when that player also holds a global title
    assert {l for sn, c, l in titles if sn == 1 and c == 'world_leader'} == {'Lider Świata CITY 1', 'Lider Świata CITY LAB'}
    # the jump crossed six season boundaries (anchor makes test time season 7): seasons 1..6 all finalize
    assert sum(1 for _, c, _ in titles if c == 'elite') == 12 and sum(1 for _, c, _ in titles if c == 'world_leader') == 12

    g = probe.get('/api/ranking/global/1').json()
    assert g['rows'][0]['nickname'] == 'Tit_beta' and 'Mistrz Sezonu 1' in g['rows'][0]['titles']
    assert g['rows'][1]['titles'] and 'Lider Świata CITY 1' in g['rows'][1]['titles']
    assert g['me']['titles'] == []  # the probe has no titles
    past = probe.get('/api/ranking/global/season/1').json()
    assert set(past['rows'][0]['titles']) == {'Mistrz Sezonu 1', 'Lider Świata CITY LAB'}  # champion + own-world leader
    ev = a.post('/api/worlds/1/events/read', json={'ids': []})  # endpoint alive; no state change expected
    db = sqlite3.connect(path / 'game.sqlite3')
    kinds = [r[0] for r in db.execute("SELECT kind FROM game_events WHERE kind LIKE 'season.title'")]
    db.close()
    assert len(kinds) == 30  # 5 titles (champion, 2x elite, 2x world leader) per finalized season, seasons 1..6

    # purely reputational: champion's stats and cash untouched (session expired during the jump: re-login)
    r = a.post('/api/auth/login', json={'username': aname, 'password': 'test-password-long-123'})
    a.headers['X-CSRF-Token'] = r.json()['csrf']
    st_after = a.get('/api/worlds/1/state').json()['state']
    assert st_after['stats'] == st_before['stats'] and st_after['cash'] == st_before['cash']
    # idempotent: repeated reads do not duplicate titles
    probe.get('/api/ranking/global/1')
    db = sqlite3.connect(path / 'game.sqlite3')
    assert db.execute('SELECT count(*) FROM character_titles').fetchone()[0] == 30
    db.close()
    # titles exist only for finished seasons, never the current one
    db = sqlite3.connect(path / 'game.sqlite3')
    assert {r[0] for r in db.execute('SELECT DISTINCT season FROM character_titles')} == {1, 2, 3, 4, 5, 6}
    db.close()
