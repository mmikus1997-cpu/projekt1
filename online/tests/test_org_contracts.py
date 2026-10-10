"""0.15: kontrakty organizacyjne (wspólne cele, zero premii do siły) + sklep: ownedSkins."""
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


def org_with_member(app, env):
    app, clock, path = env
    a = register(app, 'oca' + uuid.uuid4().hex[:4], nickname='OC_szef')
    b = register(app, 'ocb' + uuid.uuid4().hex[:4], nickname='OC_member')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Celowi QA', 'tag': 'OCQ', 'description': ''}).json()['id']
    aid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Chcę wspólny cel z ekipą.'}).json()['id']
    a.post(f'/api/org-applications/{aid}/accept', json={})
    return a, b, oid


def comm(c, wid=1):
    return c.get(f'/api/worlds/{wid}/community').json()


def test_fund_goal_flow_completion_and_counter(env):
    app, clock, path = env
    a, b, oid = org_with_member(app, env)
    r = a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24})
    assert r.status_code == 200 and 'id' in r.json()
    # baseline excludes the current fund: progress starts at 0
    assert comm(a)['orgContract']['progress'] == 0
    assert [e['kind'] for e in comm(b)['events']][0] == 'org.contract_created'
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 150}).status_code == 200
    assert b.post('/api/worlds/1/organizations/fund', json={'amount': 150}).status_code == 200
    data = comm(a)
    assert data['orgContract'] is None and data['orgContractsDone'] == 1
    assert [e['kind'] for e in data['events']][0] == 'org.contract_done'
    assert [e['kind'] for e in comm(b)['events']][0] == 'org.contract_done'
    # a new contract can start after completion
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 200, 'hours': 24}).status_code == 200


def test_prestige_goal_ignores_existing_investments_and_no_power(env):
    app, clock, path = env
    a, b, oid = org_with_member(app, env)
    a.post('/api/worlds/1/organizations/fund', json={'amount': 300})
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})  # before the goal: baseline
    r = a.post('/api/worlds/1/organizations/contract', json={'kind': 'prestige', 'district': 'Portowe', 'target': 200, 'hours': 48})
    assert r.status_code == 200, r.text
    assert comm(a)['orgContract']['progress'] == 0  # existing prestige does not count
    r = a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    assert r.status_code == 200
    assert comm(b)['orgContract']['progress'] == 100
    st_before = a.get('/api/worlds/1/state').json()['state']
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    data = comm(a)
    assert data['orgContractsDone'] == 1 and data['orgContract'] is None
    st_after = a.get('/api/worlds/1/state').json()['state']
    assert st_after['stats'] == st_before['stats'] and st_after['cash'] == st_before['cash']  # czysta reputacja


def test_gates_validation_single_active_and_cancel(env):
    app, clock, path = env
    a, b, oid = org_with_member(app, env)
    out = register(app, 'oco' + uuid.uuid4().hex[:4], nickname='OC_obcy')
    assert out.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 403
    assert b.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 403  # członek, nie oficer
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 100, 'hours': 24}).status_code == 422  # cel za mały
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'prestige', 'district': 'NieMa', 'target': 300, 'hours': 24}).status_code == 422
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 12}).status_code == 422  # zbyt krótko
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 200
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 409  # jedno aktywne
    assert b.post('/api/worlds/1/organizations/contract/cancel', json={}).status_code == 403
    assert a.post('/api/worlds/1/organizations/contract/cancel', json={}).status_code == 200
    assert comm(a)['orgContract'] is None
    assert [e['kind'] for e in comm(b)['events']][0] == 'org.contract_cancelled'
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 200


def test_lazy_deadline_miss_event(env):
    app, clock, path = env
    a, b, oid = org_with_member(app, env)
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 200
    clock[0] += 25 * 3600 * 1000
    data = comm(a)
    assert data['orgContract'] is None and data['orgContractsDone'] == 0
    assert [e['kind'] for e in data['events']][0] == 'org.contract_missed'
    # after expiry a new goal is possible
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'target': 300, 'hours': 24}).status_code == 200
