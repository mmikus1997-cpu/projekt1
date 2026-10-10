"""GDD v3.1 1.8 A1: data urodzenia przy rejestracji, próg 12 lat, zgoda opiekuna < 16 (RODO art. 8)."""
import sqlite3
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import age as AGE

NOW = 1780000000000  # 2026-05-28 UTC
TODAY = AGE.today_from_ms(NOW)


class Spy(AGE.Mailer):
    def __init__(self): self.sent = []
    def send_guardian(self, email, child, token): self.sent.append((email, child, token))


@pytest.fixture
def app(tmp_path):
    a = create_app(tmp_path / 'age.sqlite3', lambda: NOW, tmp_path / 'setup.txt')
    a.state.mailer = Spy()
    return a


def born(years, days=0):
    d = TODAY.replace(year=TODAY.year - years)
    import datetime
    return (d - datetime.timedelta(days=days)).isoformat()


def reg(app, name, **extra):
    return TestClient(app).post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True, **extra})


def row(app, name):
    with sqlite3.connect(app.state.db.path) as d:
        d.row_factory = sqlite3.Row
        return d.execute('SELECT * FROM accounts WHERE username=?', (name,)).fetchone()


def test_no_birth_date_ok_when_flag_off(app):
    assert reg(app, 'bezdaty').status_code == 200
    assert row(app, 'bezdaty')['birth_date'] is None and row(app, 'bezdaty')['guardian_status'] == 'none'


def test_no_birth_date_rejected_when_flag_on(app, monkeypatch):
    monkeypatch.setenv('CITY_REQUIRE_BIRTH_DATE', '1')
    r = reg(app, 'bezdaty2'); assert r.status_code == 422 and 'datę urodzenia' in r.text


def test_under_12_rejected(app):
    r = reg(app, 'malec', birth_date=born(11)); assert r.status_code == 422 and '12 lat' in r.text


def test_12_without_guardian_email_rejected(app):
    r = reg(app, 'dwunastka', birth_date=born(12)); assert r.status_code == 422 and 'opiekuna' in r.text


def test_12_with_guardian_pending_and_hashed_token(app):
    r = reg(app, 'dwunastka2', birth_date=born(12), guardian_email='Mama@Example.com')
    assert r.status_code == 200, r.text
    a = row(app, 'dwunastka2')
    assert a['guardian_status'] == 'pending' and a['guardian_email'] == 'mama@example.com'
    assert a['guardian_token_exp'] == NOW + 7 * 86400000
    email, child, token = app.state.mailer.sent[-1]
    assert email == 'mama@example.com' and child == 'dwunastka2'
    assert a['guardian_token_hash'] == AGE.token_hash(token) and token not in a['guardian_token_hash']


def test_exactly_16_today_no_guardian(app):
    r = reg(app, 'szesnastka', birth_date=born(16)); assert r.status_code == 200
    a = row(app, 'szesnastka')
    assert a['guardian_status'] == 'none' and a['guardian_email'] is None and a['consent'] == '16+'
    assert app.state.mailer.sent == []


def test_day_before_16_needs_guardian(app):
    assert reg(app, 'prawie16', birth_date=born(16, -1)).status_code == 422


def test_bad_format_rejected(app):
    for bad in ('2010/01/01', '2010-13-01', 'wczoraj'):
        assert reg(app, 'zlyformat', birth_date=bad).status_code == 422


def test_future_rejected(app):
    assert reg(app, 'przyszly', birth_date=born(-1)).status_code == 422


def test_audit_has_no_email_or_token(app):
    reg(app, 'tajny', birth_date=born(13), guardian_email='tata@example.com')
    token = app.state.mailer.sent[-1][2]
    with sqlite3.connect(app.state.db.path) as d:
        dump = ' '.join(r[0] or '' for r in d.execute('SELECT details FROM audit'))
    assert 'guardian' in ' '.join(r[0] for r in sqlite3.connect(app.state.db.path).execute('SELECT event FROM audit'))
    assert 'tata@example.com' not in dump and token not in dump


# ───────────── 1.8 A2: /api/me, uzupełnienie daty, weryfikacja opiekuna ─────────────

def client(app, name, **extra):
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True, **extra})
    assert r.status_code == 200, r.text
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    return c


def test_me_age_gate_fields(app):
    old = client(app, 'staremeto')
    g = old.get('/api/me').json()['ageGate']
    assert g['needsBirthDate'] is True and g['guardianStatus'] == 'none' and g['required'] is False
    kid = client(app, 'dzieckome', birth_date=born(13), guardian_email='o@example.com')
    g = kid.get('/api/me').json()['ageGate']
    assert g['needsBirthDate'] is False and g['guardianStatus'] == 'pending' and g['guardianExpiresAt'] == NOW + 7 * 86400000
    assert 'birth_date' not in str(kid.get('/api/me').json()) and 'o@example.com' not in str(kid.get('/api/me').json())


def test_birth_date_adult_saved_once(app):
    c = client(app, 'dorosly')
    r = c.post('/api/account/birth-date', json={'birth_date': born(30)}); assert r.status_code == 200 and r.json()['guardianStatus'] == 'none'
    assert row(app, 'dorosly')['birth_date'] == born(30)
    assert c.post('/api/account/birth-date', json={'birth_date': born(20)}).status_code == 409


def test_birth_date_minor_pending_and_mail(app):
    c = client(app, 'trzynastka')
    assert c.post('/api/account/birth-date', json={'birth_date': born(13)}).status_code == 422  # brak e-maila opiekuna
    r = c.post('/api/account/birth-date', json={'birth_date': born(13), 'guardian_email': 'ojciec@example.com'})
    assert r.status_code == 200 and r.json()['guardianStatus'] == 'pending'
    assert app.state.mailer.sent[-1][:2] == ('ojciec@example.com', 'trzynastka')


def test_birth_date_under_12_deletes_account(app):
    c = client(app, 'jedenastka')
    r = c.post('/api/account/birth-date', json={'birth_date': born(11)})
    assert r.status_code == 422 and 'usunięte' in r.text
    assert row(app, 'jedenastka') is None
    with sqlite3.connect(app.state.db.path) as d:
        assert d.execute("SELECT count(*) FROM audit WHERE event='guardian.rejected_underage'").fetchone()[0] == 1
        assert d.execute("SELECT count(*) FROM audit WHERE event='account.purged'").fetchone()[0] == 1


def test_guardian_verify_ok_and_single_use(app):
    client(app, 'weryfik', birth_date=born(14), guardian_email='m@example.com')
    token = app.state.mailer.sent[-1][2]
    anon = TestClient(app)
    r = anon.post('/api/guardian/verify', json={'token': token}); assert r.status_code == 200, r.text
    a = row(app, 'weryfik')
    assert a['guardian_status'] == 'verified' and a['guardian_token_hash'] is None
    assert anon.post('/api/guardian/verify', json={'token': token}).status_code == 404


def test_guardian_verify_expired(tmp_path):
    clock = [NOW]
    a = create_app(tmp_path / 'exp.sqlite3', lambda: clock[0], tmp_path / 's.txt'); a.state.mailer = Spy()
    client(a, 'wygasly', birth_date=born(14), guardian_email='m@example.com')
    token = a.state.mailer.sent[-1][2]
    clock[0] += 7 * 86400000 + 1
    assert TestClient(a).post('/api/guardian/verify', json={'token': token}).status_code == 404


def test_guardian_verify_bad_token(app):
    assert TestClient(app).post('/api/guardian/verify', json={'token': 'x' * 43}).status_code == 404


def test_preview_allowlist_has_birth_date(tmp_path):
    a = create_app(tmp_path / 'pv.sqlite3', lambda: NOW, tmp_path / 's.txt', mode='development')
    with TestClient(a) as c:
        s = c.post('/api/auth/register', json={'username': 'tunel', 'password': 'test', 'preview_session': True, 'consent': True}).json()
        c.cookies.clear()
        r = c.post('/api/preview/request', json=dict(session=s['previewSessionToken'], csrf=s['csrf'], method='POST', path='/account/birth-date', payload={'birth_date': born(25)}, idempotency_key=None))
        assert r.status_code == 200, r.text
        r = c.post('/api/preview/request', json=dict(session=s['previewSessionToken'], csrf=s['csrf'], method='POST', path='/guardian/verify', payload={'token': 'y' * 43}, idempotency_key=None))
        assert r.status_code == 404 and 'nieważny' in r.text  # trasa przepuszczona, token zły


# ───────────── 1.8 A3: blokada kont pending, auto-usuwanie po 7 dniach, resend ─────────────

def clocked(tmp_path, name='clk'):
    clock = [NOW]
    a = create_app(tmp_path / f'{name}.sqlite3', lambda: clock[0], tmp_path / f'{name}.txt'); a.state.mailer = Spy()
    return a, clock


def test_pending_blocked_everywhere_else(app):
    kid = client(app, 'blokada', birth_date=born(13), guardian_email='g@example.com')
    assert kid.get('/api/worlds').status_code == 403
    r = kid.post('/api/worlds/2/character', json={'nickname': 'Dzieciak', 'accept_test_reset': True})
    assert r.status_code == 403 and 'zgodę rodzica' in r.text
    assert kid.get('/api/worlds/2/chat/world').status_code == 403
    assert kid.get('/api/shop').status_code == 403


def test_pending_open_paths_work(app):
    kid = client(app, 'otwarte', birth_date=born(13), guardian_email='g@example.com')
    assert kid.get('/api/me').status_code == 200
    assert kid.get('/api/account/export').status_code == 200
    r = kid.post('/api/account/delete', json={'password': 'test-password-long-123'})
    assert r.status_code == 200, r.text                      # usunięcie kończy sesje
    kid2 = client(app, 'otwarte2', birth_date=born(13), guardian_email='g@example.com')
    assert kid2.post('/api/auth/logout', json={}).status_code == 200


def test_verified_unlocks(app):
    kid = client(app, 'odblok', birth_date=born(14), guardian_email='g@example.com')
    assert kid.get('/api/worlds').status_code == 403
    TestClient(app).post('/api/guardian/verify', json={'token': app.state.mailer.sent[-1][2]})
    assert kid.get('/api/worlds').status_code == 200


def test_flag_on_missing_birth_date_blocked(app, monkeypatch):
    old = client(app, 'bezdatyflag')
    monkeypatch.setenv('CITY_REQUIRE_BIRTH_DATE', '1')
    r = old.get('/api/worlds'); assert r.status_code == 403 and 'datę urodzenia' in r.text
    assert old.get('/api/me').status_code == 200
    assert old.post('/api/account/birth-date', json={'birth_date': born(20)}).status_code == 200
    assert old.get('/api/worlds').status_code == 200


def test_flag_off_missing_birth_date_works(app):
    assert client(app, 'bezdatyok').get('/api/worlds').status_code == 200


def test_expired_pending_is_purged(tmp_path):
    a, clock = clocked(tmp_path, 'purge')
    client(a, 'nieczeka', birth_date=born(13), guardian_email='g@example.com')
    client(a, 'dorosly2', birth_date=born(30))
    clock[0] += 7 * 86400000 + 1
    assert a.state.purge_guardian() == 1
    a.state.purge()
    assert row(a, 'nieczeka') is None and row(a, 'dorosly2') is not None
    with sqlite3.connect(a.state.db.path) as d:
        ev = [r[0] for r in d.execute('SELECT event FROM audit')]
    assert 'guardian.expired' in ev and 'account.purged' in ev


def test_resend_new_token_same_deadline_and_limit(tmp_path):
    a, clock = clocked(tmp_path, 'resend')
    kid = client(a, 'ponow', birth_date=born(13), guardian_email='g@example.com')
    old_token = a.state.mailer.sent[-1][2]
    clock[0] += 3600000
    r = kid.post('/api/guardian/resend', json={}); assert r.status_code == 200, r.text
    assert r.json()['guardianExpiresAt'] == NOW + 7 * 86400000          # termin bez zmian
    new_token = a.state.mailer.sent[-1][2]
    anon = TestClient(a)
    assert anon.post('/api/guardian/verify', json={'token': old_token}).status_code == 404
    assert kid.post('/api/guardian/resend', json={}).status_code == 200
    assert kid.post('/api/guardian/resend', json={}).status_code == 200
    assert kid.post('/api/guardian/resend', json={}).status_code == 429   # 4. w dobie
    assert anon.post('/api/guardian/verify', json={'token': a.state.mailer.sent[-1][2]}).status_code == 200
    assert kid.post('/api/guardian/resend', json={}).status_code in (409, 429)


# ───────────── 1.8 A4: sklep — niepełnoletność z daty urodzenia ─────────────

def verified_kid(app, name, years=14):
    kid = client(app, name, birth_date=born(years), guardian_email='g@example.com')
    assert TestClient(app).post('/api/guardian/verify', json={'token': app.state.mailer.sent[-1][2]}).status_code == 200
    return kid


def gate(c, minor):
    return c.post('/api/shop/gate', json={'enable': True, 'statement': True, 'minor': minor})


def test_shop_minor_declaration_ignored_for_known_kid(app):
    kid = verified_kid(app, 'sklep14')
    r = gate(kid, False); assert r.status_code == 422 and 'opiekuna' in r.text
    assert kid.get('/api/shop').json()['minor'] is True and kid.get('/api/shop').json()['minorSource'] == 'birth_date'


def test_shop_kid_with_consent_enabled_and_weekly_limit(app):
    kid = verified_kid(app, 'sklep14b')
    assert kid.post('/api/shop/guardian', json={'guardian_name': 'Mama Test', 'weekly_limit': 500}).status_code == 200
    assert gate(kid, False).status_code == 200
    assert kid.post('/api/worlds/2/character', json={'nickname': 'Kupiec', 'accept_test_reset': True}).status_code == 200
    assert kid.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 2}).status_code == 200    # 4,99 zł ≤ 5 zł
    r = kid.post('/api/shop/checkout', json={'sku': 'energy', 'wid': 2}); assert r.status_code == 409 and 'Tygodniowy' in r.text


def test_shop_adult_declaring_minor_needs_no_consent(app):
    adult = client(app, 'sklep30', birth_date=born(30))
    assert gate(adult, True).status_code == 200
    assert adult.get('/api/shop').json()['minor'] is False


def test_shop_no_birth_date_keeps_declaration(app):
    old = client(app, 'sklepstary')
    assert gate(old, True).status_code == 422
    assert gate(old, False).status_code == 200
    assert old.get('/api/shop').json()['minorSource'] == 'declared'


def test_checkout_rechecks_age_after_birth_date(app):
    c = client(app, 'pozniejdata')
    assert gate(c, False).status_code == 200                       # deklaracja „dorosły”
    assert c.post('/api/worlds/2/character', json={'nickname': 'Pozniej', 'accept_test_reset': True}).status_code == 200
    assert c.post('/api/account/birth-date', json={'birth_date': born(14), 'guardian_email': 'g@example.com'}).status_code == 200
    TestClient(app).post('/api/guardian/verify', json={'token': app.state.mailer.sent[-1][2]})
    r = c.post('/api/shop/checkout', json={'sku': 'skin_copper'}); assert r.status_code == 403 and 'mniej niż 16' in r.text
    assert c.post('/api/shop/guardian', json={'guardian_name': 'Tata Test', 'weekly_limit': 2000}).status_code == 200
    assert c.post('/api/shop/checkout', json={'sku': 'skin_copper'}).status_code == 200
