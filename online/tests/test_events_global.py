"""0.12: centrum zdarzeń (powiadomienia w grze) + globalny ranking sezonowy."""
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


def comm(c, wid=1):
    return c.get(f'/api/worlds/{wid}/community').json()


def kinds(c, wid=1):
    return [e['kind'] for e in comm(c, wid)['events']]


def test_event_feed_application_accept_and_read(env):
    app, clock, path = env
    a = register(app, 'evboss' + uuid.uuid4().hex[:4], nickname='Ev_szef')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Fara QA', 'tag': 'FQA', 'description': ''}).json()['id']
    b = register(app, 'evcand' + uuid.uuid4().hex[:4], nickname='Ev_kandydat')
    aid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Proszę o przyjęcie teraz.'}).json()['id']
    assert a.get('/api/worlds/1/state').json()['eventsUnread'] == 1
    ev = comm(a)['events']
    assert ev[0]['kind'] == 'org.application' and ev[0]['payload']['nick'].startswith('Ev_kandydat') and not ev[0]['read']
    assert a.post(f'/api/org-applications/{aid}/accept', json={}).status_code == 200
    assert kinds(b)[0] == 'org.accepted' and comm(b)['eventsUnread'] == 1
    assert b.post('/api/worlds/1/events/read', json={'all': True}).status_code == 200
    assert comm(b)['eventsUnread'] == 0 and all(e['read'] for e in comm(b)['events'])
    # selective ids path
    ev = comm(a)['events']
    assert a.post('/api/worlds/1/events/read', json={'ids': [ev[0]['id']]}).status_code == 200


def test_event_kinds_announcement_role_invite_invest(env):
    app, clock, path = env
    a = register(app, 'kinboss' + uuid.uuid4().hex[:4], nickname='Kin_szef')
    oid = a.post('/api/worlds/1/organizations', json={'name': 'Puls QA', 'tag': 'PQA', 'description': ''}).json()['id']
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    b = register(app, 'kinmem' + uuid.uuid4().hex[:4], nickname='Kin_member')
    aid = b.post('/api/worlds/1/organizations/apply', json={'org_id': oid, 'text': 'Biorę udział w walce o Port.'}).json()['id']
    a.post(f'/api/org-applications/{aid}/accept', json={})
    b.post('/api/worlds/1/events/read', json={'all': True})
    assert a.post('/api/worlds/1/organizations/announcement', json={'text': 'Zbiórka na inwestycję.'}).status_code == 200
    assert kinds(b)[0] == 'org.announcement'
    cid_b = comm(b)['character_id']
    assert a.post('/api/worlds/1/organizations/role', json={'target_id': cid_b, 'role': 'officer'}).status_code == 200
    assert kinds(b)[0] == 'org.role' and comm(b)['events'][0]['payload']['role'] == 'officer'
    # takeover events: my org gains, rival loses
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    assert kinds(b)[0] == 'territory.gained'
    c2 = register(app, 'kinrival' + uuid.uuid4().hex[:4], nickname='Kin_rywal')
    c2.post('/api/worlds/1/organizations', json={'name': 'Cień QA', 'tag': 'CQA', 'description': ''})
    c2.post('/api/worlds/1/organizations/fund', json={'amount': 300})
    r = c2.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 200})
    assert r.status_code == 200
    kb = kinds(b)[0]
    assert kb == 'territory.lost' and comm(b)['events'][0]['payload']['by'] == 'CQA'
    # invite event reaches the target
    d = register(app, 'kinnew' + uuid.uuid4().hex[:4], nickname='Kin_nowy')
    cid_d = comm(d)['character_id']
    assert a.post('/api/worlds/1/organizations/invite', json={'target_id': cid_d}).status_code == 200
    assert kinds(d)[0] == 'org.invite'


def test_global_ranking_seasons_and_no_reset(env):
    app, clock, path = env
    a = register(app, 'gloalfa' + uuid.uuid4().hex[:4], nickname='Glo_alfa')
    register(app, 'globeta' + uuid.uuid4().hex[:4], wid=2, nickname='Glo_beta')
    db = sqlite3.connect(path / 'game.sqlite3')
    for nick, xp in (('Glo_alfa', 12000), ('Glo_beta', 34000)):
        row = db.execute('SELECT id,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
        st = json.loads(row[1]); st['xp'] = xp
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st, separators=(',', ':')), row[0]))
    db.commit(); db.close()
    g = a.get('/api/ranking/global/1').json()
    assert g['season'] >= 1 and g['rows'][0]['nickname'] == 'Glo_beta' and g['rows'][0]['world'] == 'CITY LAB'
    assert g['rows'][1]['nickname'] == 'Glo_alfa' and g['rows'][1]['xp'] == 12000
    assert g['me']['place'] == 2 and g['me']['world'] == 'CITY 1'
    assert g['seasonEndsAt'] > clock[0]
    # no preview of other players' private state: rows carry only public fields
    assert set(g['rows'][0]) <= {'place', 'nickname', 'world', 'level', 'xp', 'tag', 'titles'}  # titles are public cosmetic labels

    # 29 days later: previous seasons are archived lazily; old sessions expired, so use a fresh one.
    clock[0] += 29 * 86400000
    a2 = register(app, 'glogamma' + uuid.uuid4().hex[:4], nickname='Glo_gamma')
    g2 = a2.get('/api/ranking/global/1').json()
    prev = g['season']
    assert all(s in g2['archive'] for s in range(1, prev + 1))
    past = a2.get(f'/api/ranking/global/season/{prev}').json()
    assert past['season'] == prev and past['rows'][0]['nickname'] in ('Glo_alfa', 'Glo_beta') and past['worlds'] >= 2
    ev = a2.get('/api/worlds/1/community').json()['events']
    assert any(e['kind'] == 'season.end' and e['payload']['season'] == prev for e in ev)
    st = a2.get('/api/worlds/1/state').json()
    assert st['character']['nickname'] == 'Glo_gamma' and st['eventsUnread'] >= 1  # season notice waits unread
    # progress was never reset by the season rollover
    db = sqlite3.connect(path / 'game.sqlite3')
    xp_alfa = json.loads(db.execute('SELECT state_json FROM characters WHERE nickname=?', ('Glo_alfa',)).fetchone()[0])['xp']
    db.close()
    assert xp_alfa == 12000
    assert a2.get('/api/ranking/global/season/9999').status_code == 422
