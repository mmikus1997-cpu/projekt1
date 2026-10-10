"""0.18 Tablica ogłoszeń świata: zasięg globalny/per świat, okno 7 dni, braki i limity."""
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


def make_admin(app, path, client):
    code = (path / 'setup.txt').read_text().splitlines()[2].strip()
    r = client.post('/api/setup/claim', json={'code': code})
    assert r.status_code == 200, r.text
    return client


def board(client, wid=1):
    return client.get(f'/api/worlds/{wid}/state').json()['notices']


def test_board_flow_world_global_and_delete(env):
    app, clock, path = env
    a = register(app, 'tb_a' + uuid.uuid4().hex[:4], nickname='TB_alfa')
    assert board(a) == []
    admin = register(app, 'tb_ad' + uuid.uuid4().hex[:4], nickname='TB_admin')
    make_admin(app, path, admin)
    r1 = admin.post('/api/admin/notices', json={'text': 'Serwerowa przerwa techniczna w niedzielę.', 'world_id': 1})
    assert r1.status_code == 200, r1.text
    r2 = admin.post('/api/admin/notices', json={'text': 'Globalne ogłoszenie dla wszystkich światów.', 'world_id': None})
    assert r2.status_code == 200, r2.text
    rows = board(a)
    assert [r['text'] for r in rows] == ['Globalne ogłoszenie dla wszystkich światów.', 'Serwerowa przerwa techniczna w niedzielę.']  # najnowsze first
    assert rows[0]['world_id'] is None and rows[1]['world_id'] == 1
    assert set(rows[0]) == {'id', 'text', 'world_id', 'created_at'}
    # gracz nie może publikować ani usuwać
    assert a.post('/api/admin/notices', json={'text': 'Nielegalne ogłoszenie gracza.'}).status_code == 403
    assert a.post(f"/api/admin/notices/{r1.json()['id']}/delete", json={}).status_code == 403
    # usuwanie: nieznane id 404, potem wpis znika a globalny zostaje
    assert admin.post('/api/admin/notices/999999/delete', json={}).status_code == 404
    assert admin.post(f"/api/admin/notices/{r1.json()['id']}/delete", json={}).status_code == 200
    assert admin.post(f"/api/admin/notices/{r1.json()['id']}/delete", json={}).status_code == 404
    rows = board(a)
    assert [r['text'] for r in rows] == ['Globalne ogłoszenie dla wszystkich światów.']
    # odpowiedź społeczności też niesie tablicę (panel czyta ją przy każdym otwarciu)
    comm = a.get('/api/worlds/1/community').json()['notices']
    assert [c['text'] for c in comm] == ['Globalne ogłoszenie dla wszystkich światów.']
    # panel administratora listuje tablicę
    ov = admin.get('/api/admin/overview').json()['notices']
    assert [o['text'] for o in ov] == ['Globalne ogłoszenie dla wszystkich światów.']
    # ślad w dzienniku
    db = sqlite3.connect(path / 'game.sqlite3')
    events = {r[0] for r in db.execute('SELECT event FROM audit').fetchall()}
    db.close()
    assert {'notice.posted', 'notice.delete'} <= events


def test_board_world_scoping_and_seven_day_window(env):
    app, clock, path = env
    a = register(app, 'tb_b' + uuid.uuid4().hex[:4], nickname='TB_beta')
    admin = register(app, 'tb_bd' + uuid.uuid4().hex[:4], nickname='TB_admin2')
    make_admin(app, path, admin)
    assert admin.post('/api/admin/notices', json={'text': 'Ogłoszenie innego świata.', 'world_id': 2}).status_code == 200
    assert board(a) == []  # obcy świat nie miesza się do tablicy
    assert admin.post('/api/admin/notices', json={'text': 'Twoje ogłoszenie.', 'world_id': 1}).status_code == 200
    assert [r['text'] for r in board(a)] == ['Twoje ogłoszenie.']
    clock[0] += 8 * 24 * 3600 * 1000
    # świeża sesja (stara token wygasa po skoku zegara); po oknie 7 dni tablica jest pusta
    b = register(app, 'tb_c' + uuid.uuid4().hex[:4], nickname='TB_gamma')
    assert board(b) == []


def test_board_validation_and_cap_20(env):
    app, clock, path = env
    a = register(app, 'tb_d' + uuid.uuid4().hex[:4], nickname='TB_delta')
    admin = register(app, 'tb_dd' + uuid.uuid4().hex[:4], nickname='TB_admin3')
    make_admin(app, path, admin)
    assert admin.post('/api/admin/notices', json={'text': 'x' * 2}).status_code == 422  # poniżej minimum 3 znaków
    assert admin.post('/api/admin/notices', json={'text': 'x' * 501}).status_code == 422
    assert admin.post('/api/admin/notices', json={'text': 'Nie ma takiego świata.', 'world_id': 999}).status_code == 404
    assert admin.post('/api/admin/notices', json={'text': 'x' * 501 + ' ', 'world_id': 1}).status_code == 422
    for i in range(22):
        r = admin.post('/api/admin/notices', json={'text': 'Ogłoszenie numer ' + str(i), 'world_id': 1})
        assert r.status_code == 200
    db = sqlite3.connect(path / 'game.sqlite3')
    count = db.execute('SELECT count(*) FROM notices').fetchone()[0]
    oldest = db.execute('SELECT text FROM notices ORDER BY id ASC LIMIT 1').fetchone()[0]
    db.close()
    assert count == 20  # cap globalny tabeli
    assert oldest == 'Ogłoszenie numer 2'  # dwa najstarsze poleciały
    rows = board(a)
    assert rows[0]['text'] == 'Ogłoszenie numer 21' and len(rows) == 10  # tablica pokazuje do 10 najnowszych
