"""0.10 Organizacje 2.0: ranks, applications, fund, district prestige, announcements."""
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


def org_of(c, wid=1):
    return c.get(f'/api/worlds/{wid}/community').json()


def test_ranks_gate_officer_powers(env):
    app, clock, path = env
    a = register(app, 'boss', nickname='Szef')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Vanguard', 'tag': 'VG', 'description': ''}).json()['id']
    b = register(app, 'member1', nickname='Czlonek')
    outsider = register(app, 'member2', nickname='Obcy')
    aid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Chcę pomagać zespołowi.'}).json()['id']
    assert outsider.post(f'/api/org-applications/{aid}/accept', json={}).status_code == 403  # outsiders cannot decide
    assert a.post(f'/api/org-applications/{aid}/accept', json={}).status_code == 200
    cid_b = org_of(b)['character_id']
    cid_out = org_of(outsider)['character_id']
    # plain member has no powers
    assert b.post('/api/worlds/1/organizations/invite', json={'target_id': cid_out}).status_code == 403
    assert b.post('/api/worlds/1/organizations/role', json={'target_id': cid_b, 'role': 'officer'}).status_code == 403
    assert b.post('/api/worlds/1/organizations/announcement', json={'text': 'Nieautoryzowane ogłoszenie.'}).status_code == 403
    # leader promotes the member to officer
    assert a.post('/api/worlds/1/organizations/role', json={'target_id': cid_b, 'role': 'officer'}).status_code == 200
    assert org_of(b)['myRole'] == 'officer'
    # officer can announce, invite, accept applications and remove plain members — not the leader
    assert b.post('/api/worlds/1/organizations/announcement', json={'text': 'Zbiórka na inwestycję.'}).status_code == 200
    e = register(app, 'newbie', nickname='Nowak')
    eid = e.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Mam czas i gotówkę na start.'}).json()['id']
    assert b.post(f'/api/org-applications/{eid}/accept', json={}).status_code == 200
    cid_e = org_of(e)['character_id']
    assert b.post('/api/worlds/1/organizations/remove-member', json={'target_id': cid_e}).status_code == 200
    assert b.post('/api/worlds/1/organizations/remove-member', json={'target_id': org_of(a)['character_id']}).status_code == 403
    assert b.post('/api/worlds/1/organizations/role', json={'target_id': cid_e, 'role': 'officer'}).status_code == 403  # leader-only
    # leader removes the officer outright
    assert a.post('/api/worlds/1/organizations/remove-member', json={'target_id': cid_b}).status_code == 200
    assert org_of(b).get('organization') is None


def test_applications_flow_with_capacity_and_blocks(env):
    app, clock, path = env
    a = register(app, 'recruiter')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Atlas', 'tag': 'AT', 'description': ''}).json()['id']
    b = register(app, 'candidate')
    r = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Krótkie podanie kandydata.'})
    assert r.status_code == 200
    assert b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Drugie takie samo podanie.'}).status_code == 409
    aid = r.json()['id']
    # decline path
    assert a.post(f'/api/org-applications/{aid}/decline', json={}).status_code == 200
    assert org_of(b)['appliedTo'] is None
    # accept path auto-declines the applicant's other pending applications
    c2 = register(app, 'other_org')
    oid2 = c2.post('/api/worlds/1/organizations', json={'name': 'Zenith', 'tag': 'ZN', 'description': ''}).json()['id']
    b1 = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Podanie do pierwszej ekipy.'}).json()['id']
    b2 = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid2, 'text': 'Podanie do drugiej ekipy.'}).json()['id']
    assert a.post(f'/api/org-applications/{b1}/accept', json={}).status_code == 200
    rows = org_of(c2)['applications']
    assert all(x['id'] != b2 for x in rows)  # resolved by the auto-decline
    # blocked contact refuses the application
    b.post('/api/worlds/1/blocks', json={'target_id': org_of(a)['character_id']})
    r = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Podanie mimo blokady kontaktu.'})
    assert r.status_code == 409


def test_fund_and_prestige_without_power_bonus(env):
    app, clock, path = env
    a = register(app, 'treasurer')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Meridian', 'tag': 'MR', 'description': ''}).json()['id']
    b = register(app, 'donor', wid=1)
    aid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Wpłacę na fundusz startowy.'}).json()['id']
    a.post(f'/api/org-applications/{aid}/accept', json={})
    cash0 = b.get('/api/worlds/1/state').json()['state']['cash']
    assert b.post('/api/worlds/1/organizations/fund', json={'amount': 40}).status_code == 422   # below minimum
    assert b.post('/api/worlds/1/organizations/fund', json={'amount': 6000}).status_code == 422  # above maximum
    assert b.post('/api/worlds/1/organizations/fund', json={'amount': 200}).json()['fund'] == 200
    cash1 = b.get('/api/worlds/1/state').json()['state']['cash']
    assert cash1 == cash0 - 200
    # investing needs officer rank
    assert b.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100}).status_code == 403
    cid_b = org_of(b)['character_id']
    assert a.post('/api/worlds/1/organizations/role', json={'target_id': cid_b, 'role': 'officer'}).status_code == 200
    assert b.post('/api/worlds/1/organizations/invest', json={'district': 'Nope', 'amount': 100}).status_code == 422
    inv = b.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 200}).json()
    assert (inv['fund'], inv['invested']) == (0, 200) and inv['claimed'] == 'MR' and inv['held'] == ['Portowe']
    assert b.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100}).status_code == 409  # empty fund
    data = org_of(a)
    assert data['organization']['fund'] == 0 and data['organization']['prestige'] == 200
    assert data['ranking'][0]['tag'] == 'MR' and data['ranking'][0]['prestige'] == 200
    # org prestige must not touch personal district investments nor stats
    st = b.get('/api/worlds/1/state').json()
    port = [d for d in st['catalog']['districts'] if d['name'] == 'Portowe'][0]
    assert port['world'] == 0 and port['mine'] == 0
    assert st['state']['stats'] == [10] * 5
    assert st['state']['cash'] == cash1  # org spend never touches member wallets


def test_announcements_and_role_migration_of_old_rows(env):
    app, clock, path = env
    a = register(app, 'founder')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Legacy', 'tag': 'LG', 'description': ''}).json()['id']
    # simulate a member row created before 0.10 (role defaulted via migration, not 'leader')
    founder = org_of(a)['character_id']
    import sqlite3
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        db.execute("UPDATE org_members SET role='member' WHERE character_id=?", (founder,))
    data = org_of(a)
    assert data['myRole'] == 'leader' and data['is_leader']  # leader_id outranks the stored role
    assert a.post('/api/worlds/1/organizations/announcement', json={'text': 'Witajcie w Legacy!'}).status_code == 200
    assert org_of(a)['organization']['announcement'] == 'Witajcie w Legacy!'
    assert a.post('/api/worlds/1/organizations/announcement', json={'text': 'Zobacz http://spam.example'}).status_code == 422
    # transfer moves the leader rank and demotes the old leader to officer
    b = register(app, 'heir')
    hid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Gotów przejąć stery zespołu.'}).json()['id']
    a.post(f'/api/org-applications/{hid}/accept', json={})
    assert a.post('/api/worlds/1/organizations/transfer', json={'target_id': org_of(b)['character_id']}).status_code == 200
    assert org_of(a)['myRole'] == 'officer' and org_of(b)['myRole'] == 'leader'
