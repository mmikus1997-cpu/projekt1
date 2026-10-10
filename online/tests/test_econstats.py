"""0.24 Ekonomia w liczbach: dzienne agregaty czynów (gracz i świat) + dev-sklep w podsumowaniu."""
import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from server import economy as E
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


def make_admin(app, path, client):
    code = (path / 'setup.txt').read_text().splitlines()[2].strip()
    r = client.post('/api/setup/claim', json={'code': code})
    assert r.status_code == 200, r.text
    return client


def seed_finished_contract(path, nick, ts):
    """Wstawia do stanu postaci zakończony kontrakt (dostawa) gotowy do odbioru."""
    db = sqlite3.connect(path / 'game.sqlite3')
    row = db.execute('SELECT id,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
    st = json.loads(row[1])
    st['contracts'] = [dict(id=st.get('sequence', 0) + 1, contract='delivery', start=ts - 12 * 60 * 1000, end=ts - 1000)]
    st['sequence'] = st.get('sequence', 0) + 1
    db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st, separators=(',', ':')), row[0]))
    db.commit(); db.close()


def test_activity_empty_then_deeds_and_money_flow(env, flat_stats):
    app, clock, path = env
    uname = 'ec_a' + uuid.uuid4().hex[:4]
    a = register(app, uname, nickname='EC_alfa')
    day = E.day_start(clock[0])
    assert a.get('/api/worlds/1/state').json()['activity'] == []  # czysty start: brak wierszy
    # czyn 1: wpłata do funduszu organizacji
    a.post('/api/worlds/1/organizations', json={'name': 'Ekonomia QA', 'tag': 'EKQ', 'description': ''})
    assert a.post('/api/worlds/1/organizations/fund', json={'amount': 100}).status_code == 200
    act = a.get('/api/worlds/1/state').json()['activity']
    assert len(act) == 1 and act[0]['day'] == day and act[0]['deeds'] == 1 and act[0]['cash'] == 0 and act[0]['xp'] == 0
    # czyn 2: odbiór zakończonego kontraktu (seed wprost do stanu) — gotówka i XP wpadają
    seed_finished_contract(path, 'EC_alfa', clock[0])
    keys = {'Idempotency-Key': 'ec-claim-key-%019d' % 1}
    r = a.post('/api/worlds/1/actions', json={'action': 'claim_contract', 'task_id': 1}, headers=keys)
    assert r.status_code == 200, r.text
    act = a.get('/api/worlds/1/state').json()['activity']
    assert act[0]['deeds'] == 2 and act[0]['xp'] == 20 and act[0]['cash'] > 0  # dostawa: 20 XP, gotówka z rynku dnia
    # admin: podsumowanie świata widzi te same agregaty
    admin = register(app, 'ec_ad' + uuid.uuid4().hex[:4], nickname='EC_admin')
    make_admin(app, path, admin)
    s = admin.get('/api/admin/worlds/1/summary').json()
    assert s['daily'][0]['day'] == day and s['daily'][0]['deeds'] == 2 and s['daily'][0]['cash'] == act[0]['cash'] and s['daily'][0]['xp'] == 20
    # dev-sklep: energiapak na świecie 1 → centy w agregacie świata (nie w czynach gracza)
    a.post('/api/shop/gate', json={'enable': True, 'statement': True})
    r = a.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 1}, headers={'Idempotency-Key': 'ec-shop-key-%018d' % 1})
    assert r.status_code == 200, r.text
    s = admin.get('/api/admin/worlds/1/summary').json()
    assert s['daily'][0]['shop_cents'] == 499 and s['daily'][0]['deeds'] == 2  # zakup nie jest czynem
    act = a.get('/api/worlds/1/state').json()['activity']
    assert act[0].get('shop_cents') is None  # payload gracza bez centów
    assert set(s) == {'world', 'population', 'cityXp', 'top', 'newest', 'orgs', 'topOrgs', 'contracts', 'event', 'chronicleCount', 'noticesCount', 'shop', 'vipResidents', 'daily'}


def test_second_day_splits_rows_and_cap_fourteen(env):
    app, clock, path = env
    uname = 'ec_b' + uuid.uuid4().hex[:4]
    a = register(app, uname, nickname='EC_beta')
    a.post('/api/worlds/1/organizations', json={'name': 'Dni QA', 'tag': 'DNQ', 'description': ''})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    clock[0] += 26 * 3600 * 1000  # nowa doba UTC
    a = register(app, 'ec_b2' + uuid.uuid4().hex[:4], nickname='EC_beta2')  # sesja po skoku
    db = sqlite3.connect(path / 'game.sqlite3')
    cid = db.execute("SELECT id FROM characters WHERE nickname='EC_beta2'").fetchone()
    db.close()
    # bezczynny dzień: brak wiersza; wypełniacz 20 dni wstecz (limit okna 14)
    db = sqlite3.connect(path / 'game.sqlite3')
    for i in range(1, 21):
        db.execute('INSERT INTO char_daily(character_id,day,deeds,cash,xp) VALUES(?,?,?,?,?)', (cid[0], E.day_start(clock[0]) - i * 86400000, 3, 100, 50))
    db.commit(); db.close()
    act = a.get('/api/worlds/1/state').json()['activity']
    assert len(act) == 14  # okno nigdy nie przekracza dwóch tygodni
    days = {r['day'] for r in act}
    assert E.day_start(clock[0]) - 20 * 86400000 not in days and E.day_start(clock[0]) - 7 * 86400000 in days


def test_world_isolation_of_aggregates(env):
    app, clock, path = env
    a = register(app, 'ec_c' + uuid.uuid4().hex[:4], wid=1, nickname='EC_gamma')
    a.post('/api/worlds/1/organizations', json={'name': 'Izolacja EK', 'tag': 'IEK', 'description': ''})
    a.post('/api/worlds/1/organizations/fund', json={'amount': 100})
    b = register(app, 'ec_d' + uuid.uuid4().hex[:4], wid=2, nickname='EC_delta')
    assert b.get('/api/worlds/2/state').json()['activity'] == []
    admin = register(app, 'ec_cd' + uuid.uuid4().hex[:4], nickname='EC_admin2')
    make_admin(app, path, admin)
    assert admin.get('/api/admin/worlds/2/summary').json()['daily'] == []
