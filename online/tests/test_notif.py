"""0.59.0 Chmurka powiadomień: eventsRecent (8 ostatnich, z flagą read) w pakiecie stanu."""
import json
import sqlite3
import uuid

from fastapi.testclient import TestClient

from server.app import create_app


def test_events_recent_in_packet(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': 'nt' + uuid.uuid4().hex[:5], 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/1/character', json={'nickname': 'Dzwonek', 'accept_test_reset': True}).status_code == 200
    pk = c.get('/api/worlds/1/state').json()
    assert pk['eventsRecent'] == []
    with sqlite3.connect(app.state.db.path) as db:
        cid = db.execute("SELECT id FROM characters WHERE nickname='Dzwonek'").fetchone()[0]
        for i in range(10):
            db.execute('INSERT INTO game_events(world_id,character_id,kind,payload,created_at) VALUES(1,?,?,?,?)',
                       (cid, 'org.building', json.dumps({'tag': 'T', 'org': 'O', 'building': 'Wolność', 'level': i}), clock[0] + i))
    pk = c.get('/api/worlds/1/state').json()
    ev = pk['eventsRecent']
    assert len(ev) == 8 and ev[0]['payload']['level'] == 9 and ev[0]['read'] is False
    assert pk['eventsUnread'] == 10
    assert c.post('/api/worlds/1/events/read', json={'all': True}).status_code == 200
    pk = c.get('/api/worlds/1/state').json()
    assert pk['eventsUnread'] == 0 and all(e['read'] for e in pk['eventsRecent'])
