"""Ranking Świata (Flutter): GET /api/worlds/{wid}/rankings — 4 zestawienia."""
import json
import pytest
from fastapi.testclient import TestClient
from server.app import create_app


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    return create_app(tmp_path / 'rk.sqlite3', lambda: clock[0], tmp_path / 'setup.txt'), clock


def register(app, name):
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    return c


def make(app, name, cash=0, rating=1000, dn=0, dh=0, dnm=0):
    a = register(app, name.lower())
    r = a.post('/api/worlds/2/character', json={'nickname': name, 'accept_test_reset': True})
    assert r.status_code in (200, 201), r.text
    with app.state.db.tx() as c:
        s = json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?', (name,)).fetchone()[0])
        s['cash'] = cash
        c.execute('UPDATE characters SET state_json=?,rating=?,dungeon_normal=?,dungeon_hard=?,dungeon_nightmare=? WHERE nickname=?',
                  (json.dumps(s), rating, dn, dh, dnm, name))
    return a


def test_cztery_rankingi(env):
    app, clock = env
    a = make(app, 'Bogacz', cash=90000, rating=1100, dn=40)
    make(app, 'Lochowy', cash=100, rating=1300, dn=100, dh=12)
    make(app, 'Koszmar', cash=500, rating=900, dn=100, dh=30, dnm=2)
    r = a.get('/api/worlds/2/rankings'); assert r.status_code == 200, r.text
    j = r.json()
    assert j['seasonEndsAt'] > j['serverTime']
    assert [x['nickname'] for x in j['pvp']['rows']][:3] == ['Lochowy', 'Bogacz', 'Koszmar']
    assert j['wealth']['rows'][0]['nickname'] == 'Bogacz' and j['wealth']['me']['place'] == 1
    assert j['dungeon']['rows'][0]['nickname'] == 'Koszmar' and j['dungeon']['rows'][0]['mode'] == 'nightmare'
    assert j['dungeon']['rows'][1]['nickname'] == 'Lochowy' and j['dungeon']['rows'][1]['mode'] == 'hard'
    assert j['prestige']['total'] == 3 and all(x['value'] == 0 for x in j['prestige']['rows'])


def test_profil_prestiz_i_ramki(env):
    app, clock = env
    a = make(app, 'Ramkowy')
    with app.state.db.tx() as c:
        s = json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Ramkowy'").fetchone()[0])
        s['frames'] = ['season-10-gold']
        c.execute("UPDATE characters SET state_json=? WHERE nickname='Ramkowy'", (json.dumps(s),))
    j = a.get('/api/account/profile').json()
    ch = [x for x in j['characters'] if x['worldId'] == 2][0]
    assert j['prestigePoints'] == 0 and ch['frames'] == ['season-10-gold'] and ch['resets'] == 0 and ch['createdAt'] == 1780000000000
