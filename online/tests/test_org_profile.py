"""0.21 Wizytówka organizacji: publiczny profil per świat — skład, prestiż, wpływy, historia z kroniki."""
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


def test_profile_full_picture_after_contract_done(env):
    app, clock, path = env
    a = register(app, 'op_a' + uuid.uuid4().hex[:4], nickname='OP_alfa')
    org = a.post('/api/worlds/1/organizations', json={'name': 'Wizytowa QA', 'tag': 'WQA', 'description': 'Opis publiczny wizytówki.'}).json()
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 100}).status_code == 200  # gotówka 300→200
    assert a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100}).status_code == 200  # fundusz 100→0, prestiż Port 100
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'district': '', 'target': 200, 'hours': 24}).status_code == 200  # baza 0
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 100}).status_code == 200
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 100}).status_code == 200  # 0+200=200 → zaliczony
    # inny mieszkaniec świata (bez org) czyta wizytówkę
    b = register(app, 'op_b' + uuid.uuid4().hex[:4], nickname='OP_beta')
    p = b.get(f"/api/worlds/1/organizations/{org['id']}").json()
    assert p['name'] == 'Wizytowa QA' and p['tag'] == 'WQA' and p['description'] == 'Opis publiczny wizytówki.'
    assert p['leader'] == 'OP_alfa' and p['members'] == [{'nickname': 'OP_alfa', 'role': 'leader'}]
    assert p['prestige'] == 100 and p['held'] == ['Portowe'] and p['contractsDone'] == 1
    assert set(p) == {'name', 'tag', 'description', 'created_at', 'leader', 'members', 'prestige', 'held', 'contractsDone', 'history'}
    kinds = [h['kind'] for h in p['history']]
    assert kinds == ['org_done', 'org_founded'], kinds  # najnowsze najpierw
    assert 'Wizytowa QA [WQA] zalicza wspólny cel' == p['history'][0]['title']
    # bez sesji: brak dostępu
    assert a.app is not None
    anon = TestClient(app)
    assert anon.get(f"/api/worlds/1/organizations/{org['id']}").status_code == 401


def test_profile_404_wrong_org_and_cross_world(env):
    app, clock, path = env
    a = register(app, 'op_c' + uuid.uuid4().hex[:4], nickname='OP_gamma')
    org = a.post('/api/worlds/1/organizations', json={'name': 'Lokalna QA', 'tag': 'LQA', 'description': ''}).json()
    assert a.get('/api/worlds/1/organizations/999999').status_code == 404
    # ta sama organizacja oglądana z drugiego świata: 404 (mieszkaniec świata 2 nie jądra)
    b = register(app, 'op_d' + uuid.uuid4().hex[:4], wid=2, nickname='OP_delta')
    assert b.get(f"/api/worlds/1/organizations/{org['id']}").status_code == 404
    assert a.get(f"/api/worlds/1/organizations/{org['id']}").status_code == 200
