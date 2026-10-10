"""0.11 Wpływy terytorialne: prestiż decyduje o dzielnicy, przejęcia logowane, zero bonusów do siły."""
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


def comm(c, wid=1):
    return c.get(f'/api/worlds/{wid}/community').json()


def make_org(c, tag, fund=None):
    oid = c.post('/api/worlds/1/organizations', json={'name': 'Org ' + tag, 'tag': tag, 'description': ''}).json()['id']
    if fund:
        r = c.post('/api/worlds/1/organizations/fund', json={'amount': fund})
        assert r.status_code == 200, r.text
    return oid


def port(districts):
    return next(d for d in districts if d['district'] == 'Portowe')


def test_takeover_flow_log_and_tie(env):
    app, clock, path = env
    a = register(app, 'alfa' + uuid.uuid4().hex[:6], nickname='Alfa')
    make_org(a, 'TAGA', fund=100)
    r = a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    assert r.status_code == 200 and r.json()['claimed'] == 'TAGA' and r.json()['held'] == ['Portowe']
    data = comm(a)
    p = port(data['influence'])
    assert p['leader']['tag'] == 'TAGA' and p['total'] == 100 and p['myRank'] == 1 and p['holderSince']
    assert data['myHeld'] == ['Portowe'] and data['organizations'][0]['held'] == ['Portowe']
    assert len(data['territoryLog']) == 1 and data['territoryLog'][0]['tag'] == 'TAGA' and data['territoryLog'][0]['prev_tag'] == ''

    # Rival org overtakes Port with a higher prestige sum.
    b = register(app, 'beta' + uuid.uuid4().hex[:6], nickname='Beta')
    make_org(b, 'TAGB', fund=300)
    r = b.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 200})
    assert r.json()['claimed'] == 'TAGB'
    data_a, data_b = comm(a), comm(b)
    pa, pb = port(data_a['influence']), port(data_b['influence'])
    assert pa['leader']['tag'] == 'TAGB' and pa['myRank'] == 2 and pa['myTotal'] == 100 and data_a['myHeld'] == []
    assert pb['myRank'] == 1 and data_b['myHeld'] == ['Portowe']
    held_of = lambda data, tag: next(o['held'] for o in data['organizations'] if o['tag'] == tag)
    assert held_of(data_a, 'TAGA') == [] and held_of(data_b, 'TAGB') == ['Portowe']
    log = data_a['territoryLog']
    assert len(log) == 2 and log[0]['tag'] == 'TAGB' and log[0]['prev_tag'] == 'TAGA'

    # 8.3 GDD v3.1: 100/200/200 → nikt nie ma >55% → dzielnica neutralna (wpis w logu, bez posiadacza).
    c_ = register(app, 'gamm' + uuid.uuid4().hex[:6], nickname='Gamma')
    make_org(c_, 'TAGC', fund=300)
    r = c_.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 200})
    assert r.status_code == 200 and r.json()['claimed'] is None
    data_c = comm(c_)
    assert port(data_c['influence'])['leader']['tag'] == 'TAGB', 'ranking udziałów bez zmian (remis → starszy sojusz pierwszy)'
    assert port(data_c['influence'])['myRank'] == 2 and port(data_c['influence'])['holderSince'] is None
    assert len(data_c['territoryLog']) == 3 and data_c['territoryLog'][0]['prev_tag'] == 'TAGB'

    # Other districts stay untouched; worlds are isolated.
    other = [d for d in data_c['influence'] if d['district'] != 'Portowe']
    assert all(d['leader'] is None and d['total'] == 0 and d['holderSince'] is None for d in other)


def test_no_power_bonus_from_holdings(env):
    app, clock, path = env
    a = register(app, 'alf2' + uuid.uuid4().hex[:6], nickname='Alfa2')
    make_org(a, 'TAGX', fund=200)
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Centrum', 'amount': 200})
    st = a.get('/api/worlds/1/state').json()['state']
    assert st['stats'] == [10] * 5
    assert st['cash'] == 100  # 300 start - 200 funded; holding a district grants no cash or stats
    assert not st.get('invested')  # org investments never mirror into personal district bonuses


def test_gates_and_outsider_view(env):
    app, clock, path = env
    a = register(app, 'alf3' + uuid.uuid4().hex[:6], nickname='Alfa3')
    oid = make_org(a, 'TAGY', fund=100)
    b = register(app, 'beto' + uuid.uuid4().hex[:6], nickname='Beto')
    aid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Prośba o przyjęcie.'}).json()['id']
    a.post(f'/api/org-applications/{aid}/accept', json={})
    assert b.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100}).status_code == 403
    assert a.post('/api/worlds/1/organizations/invest', json={'district': 'NieMa', 'amount': 100}).status_code == 422
    assert a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 50}).status_code == 422
    out = register(app, 'outs' + uuid.uuid4().hex[:6], nickname='Obserwator')
    data = comm(out)
    assert data['myHeld'] == [] and data['influence'] and data['territoryLog'] == []
    assert all(d['myRank'] is None for d in data['influence'])
