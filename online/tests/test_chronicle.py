"""0.17 Kronika miasta: wpis powstaje w tej samej transakcji co fakt; 15 wpisów w stanie; 300/world."""
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


def make_admin(app, path, client):
    code = (path / 'setup.txt').read_text().splitlines()[2].strip()
    r = client.post('/api/setup/claim', json={'code': code})
    assert r.status_code == 200, r.text
    return client


def kinds(client, wid=1):
    return [e['kind'] for e in client.get(f'/api/worlds/{wid}/state').json()['chronicle']]


def test_chronicle_records_full_city_and_org_story(env):
    app, clock, path = env
    a = register(app, 'kr_a' + uuid.uuid4().hex[:4], nickname='KR_alfa')
    assert kinds(a) == []  # czysty świat: kronika pusta
    # założenie organizacji trafia do kroniki
    a.post('/api/worlds/1/organizations', json={'name': 'Kronika Test', 'tag': 'KRT', 'description': 'Ekipa z historią.'})
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'org_founded'
    assert feed[0]['title'] == 'Powstaje organizacja Kronika Test [KRT]'
    assert feed[0]['description'] == 'Ekipa z historią.'
    assert set(feed[0]) == {'id', 'kind', 'title', 'description', 'district', 'created_at'}
    # administrator ogłasza wyzwanie miasta
    admin = register(app, 'kr_ad' + uuid.uuid4().hex[:4], nickname='KR_admin')
    make_admin(app, path, admin)
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Maraton Kroniki', 'description': 'Zdobądźmy XP!', 'kind': 'xp', 'target': 100000, 'hours': 24}).status_code == 200
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'city_new' and feed[0]['district'] == ''
    assert feed[0]['title'] == 'Miasto ogłasza wyzwanie: Maraton Kroniki'
    assert 'Zdobądźmy XP!' in feed[0]['description'] and 'Wspólny cel: 100 000 XP miasta.' in feed[0]['description']
    # przepadnięcie po terminie zapisuje się leniwie przy odczycie
    clock[0] += 25 * 3600 * 1000
    b = register(app, 'kr_b' + uuid.uuid4().hex[:4], nickname='KR_beta')  # świeża sesja: stare wygasły
    assert kinds(b)[0] == 'city_missed'
    assert 'Termin minął bez zaliczenia wspólnego celu.' in b.get('/api/worlds/1/state').json()['chronicle'][0]['description']
    # kontrakt organizacji zaliczony → wpis z kwotą sformatowaną po ludzku
    a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'district': '', 'target': 200, 'hours': 24})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 200})
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'org_done'
    assert feed[0]['title'] == 'Kronika Test [KRT] zalicza wspólny cel'
    assert feed[0]['description'] == 'Zbiórka 200 $ do funduszu zakończona.'
    # anulowanie wyzwania przez administratora też jest historią
    assert admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Do Anulacji', 'kind': 'xp', 'target': 100, 'hours': 48}).status_code == 200
    eid = admin.get('/api/admin/overview').json()['events'][0]['id']
    assert admin.post(f'/api/admin/events/{eid}/cancel', json={}).status_code == 200
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'city_cancel' and 'Do Anulacji' in feed[0]['title']
    assert kinds(a) == ['city_cancel', 'city_new', 'org_done', 'city_missed', 'city_new', 'org_founded']  # najnowsze first


def test_prestige_entry_world_scoping_and_cap(env):
    app, clock, path = env
    a = register(app, 'kr_c' + uuid.uuid4().hex[:4], nickname='KR_gamma')
    a.post('/api/worlds/1/organizations', json={'name': 'Portowa QA', 'tag': 'PQA', 'description': ''})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 300})
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})  # baseline
    admin = register(app, 'kr_cd' + uuid.uuid4().hex[:4], nickname='KR_admin2')
    make_admin(app, path, admin)
    r = admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Noc Prestiżu', 'kind': 'prestige', 'district': 'Portowe', 'target': 100, 'hours': 24})
    assert r.status_code == 200, r.text
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'city_new' and feed[0]['district'] == 'Portowe'
    assert 'prestiżu w Port' in feed[0]['description']
    a.post('/api/worlds/1/organizations/invest', json={'district': 'Portowe', 'amount': 100})
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'city_done'
    assert feed[0]['title'] == 'Wyzwanie „Noc Prestiżu” zaliczone'
    assert 'Pioniera' in feed[0]['description']
    # kronika jest per świat: wpisy innego świata nie mieszają się do feedu
    db = sqlite3.connect(path / 'game.sqlite3')
    for i in range(5):
        db.execute('INSERT INTO chronicle(world_id,kind,title,description,district,created_at) VALUES(2,?,?,?,?,?)', ('filler', 'Obcy świat ' + str(i), '', '', clock[0] + i))
    db.commit()
    assert kinds(a) and all('Obcy świat' not in e['title'] for e in a.get('/api/worlds/1/state').json()['chronicle'])
    # limit 300 wpisów na świat (przycinanie po każdym wpisie)
    for i in range(305):
        db.execute('INSERT INTO chronicle(world_id,kind,title,description,district,created_at) VALUES(1,?,?,?,?,?)', ('filler', 'Wypełniacz ' + str(i), '', '', clock[0] + 1000 + i))
    db.commit()
    admin.post('/api/admin/events', json={'world_id': 1, 'name': 'Po Limicie', 'kind': 'xp', 'target': 100, 'hours': 24})
    count = db.execute('SELECT count(*) FROM chronicle WHERE world_id=1').fetchone()[0]
    assert count == 300
    first = db.execute('SELECT title FROM chronicle WHERE world_id=1 ORDER BY id DESC LIMIT 1').fetchone()[0]
    assert first == 'Miasto ogłasza wyzwanie: Po Limicie'  # najnowszy przetrwał, najstarsze poleciały
    db.close()


def test_org_contract_missed_is_chronicled(env):
    app, clock, path = env
    a = register(app, 'kr_d' + uuid.uuid4().hex[:4], nickname='KR_delta')
    a.post('/api/worlds/1/organizations', json={'name': 'Spóźnialscy', 'tag': 'SPZ', 'description': ''})
    assert a.post('/api/worlds/1/organizations/contract', json={'kind': 'fund', 'district': '', 'target': 5000, 'hours': 24}).status_code == 200
    clock[0] += 25 * 3600 * 1000
    b = register(app, 'kr_e' + uuid.uuid4().hex[:4], nickname='KR_eps')
    b.get('/api/worlds/1/community')  # leniwe wygaszenie kontraktów przy odczycie społeczności
    feed = a.get('/api/worlds/1/state').json()['chronicle']
    assert feed[0]['kind'] == 'org_missed'
    assert feed[0]['title'] == 'Spóźnialscy [SPZ] nie zdążyła z celem'
    assert feed[0]['description'] == 'Zbiórka do funduszu wygasła bez realizacji.'
