"""2.7 GDD v3.1: AI Manager — automatyczne ponawianie zmian (max/safe), prowizja 10%, posiłki, offline (sweep)."""
import json
import sqlite3
from server import npc as N, services as S
from server import economy as E
from tests.test_npc_shift import env, player, patch, cash, post, hire, driver, H, M, T0  # noqa: F401

LVL10 = 4500


def row(db, nid):
    with sqlite3.connect(db) as x:
        x.row_factory = sqlite3.Row
        return dict(x.execute('SELECT * FROM npcs WHERE id=?', (nid,)).fetchone())


def st(db):
    with sqlite3.connect(db) as x:
        return json.loads(x.execute('SELECT state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0])


def mgr(c, **body):
    return post(c, 'npcs/manager', dict(dict(enabled=True), **body))


def test_level_gate_and_validation(env):
    app, clock, db = env
    c = player(app, db, 'nowicjusz')
    hire(c, db)
    r = mgr(c)
    assert r.status_code == 409 and '10. poziomu' in r.json()['detail']
    patch(db, lambda s: s.update(xp=LVL10))
    assert mgr(c, duration_h=0).status_code == 422
    assert mgr(c, exclude=[999]).status_code == 404
    assert post(c, 'npcs/manager', dict(enabled=False)).status_code == 409   # nieaktywny


def test_enable_dispatches_idle_now(env):
    app, clock, db = env
    c = player(app, db, 'szefowa', xp=LVL10)
    a, b = hire(c, db), hire(c, db)
    r = mgr(c, hours=4, exclude=[b])
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['manager']['active'] and j['manager']['until'] == T0 + 24 * H and j['manager']['shifts'] == 1
    ra, rb = row(db, a), row(db, b)
    assert ra['phase'] == 'to_work' and ra['shift_manager'] == 1 and ra['shift_started_at'] == T0
    assert rb['phase'] is None                                   # wykluczony
    best = N.best_plan(dict(ra, phase=None, energy=100, mood=100, hunger=100), st(db), 4, None, T0, 2, E, S)
    assert ra['assigned_service_id'] == best['service']


def test_chain_offline_exact_restart_and_commission(env):
    app, clock, db = env
    c = player(app, db, 'nieobecna', xp=LVL10)
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.row_factory = sqlite3.Row
        n0 = dict(x.execute('SELECT * FROM npcs WHERE id=?', (a,)).fetchone())
    c0 = cash(db)
    mgr(c, hours=2)
    first = N.best_plan(n0, st(db), 2, None, T0, 2, E, S)
    done_at = first['endsAt'] - 1                                # estimate: powrót + 1 ms
    clock[0] = done_at + 5 * M
    app.state.npc['sweep']()                                     # gracz offline
    r = row(db, a)
    assert r['shift_manager'] == 1 and r['shift_started_at'] == done_at   # druga zmiana od razu, co do ms
    m = st(db)['aiManager']
    fee = round(first['cash'] * N.MANAGER_COMMISSION)
    assert m['shifts'] == 2 and m['fees'] == fee and m['earned'] == first['cash'] - fee
    assert cash(db) - c0 == first['cash'] - fee


def test_long_offline_many_shifts_until_expiry(env):
    app, clock, db = env
    c = player(app, db, 'urlopowicz', xp=LVL10, cash=100000)
    a = hire(c, db)
    mgr(c, hours=2, duration_h=12)
    clock[0] += 30 * H
    app.state.npc['sweep']()
    m = st(db)['aiManager']
    assert 3 <= m['shifts'] <= 6                                 # ~2 h zmiany + dojazdy, z odpoczynkami
    r = row(db, a)
    assert r['phase'] is None                                    # po wygaśnięciu nikt nie wysyła dalej
    assert m['fees'] > 0 and abs(m['fees'] - (m['earned'] + m['fees']) * 0.1) <= m['shifts']
    assert c.get('/api/worlds/2/npcs').json()['manager']['active'] is False


def test_resting_npc_dispatched_when_energy_back(env):
    app, clock, db = env
    c = player(app, db, 'cierpliwy', xp=LVL10)
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET energy=20 WHERE id=?', (a,))
    mgr(c, hours=2)
    assert row(db, a)['phase'] is None
    clock[0] += 3 * H
    c.get('/api/worlds/2/npcs')
    assert row(db, a)['shift_started_at'] == T0 + 2 * H + 1      # 20 → 40 przy +10/h, +1 ms za progiem


def test_feed_before_dispatch(env):
    app, clock, db = env
    c = player(app, db, 'karmiciel', xp=LVL10, buffet=1)
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET hunger=20 WHERE id=?', (a,))
    c0 = cash(db)
    mgr(c, hours=2)
    r = row(db, a)
    assert r['phase'] == 'to_work' and r['hunger'] == 35 and st(db)['aiManager']['feeds'] == 1
    assert cash(db) == c0 - N.MEALS[1]['cost']                 # 4.4: Zwykłe jedzenie z Buffetu lvl 1


def test_feed_off(env):
    app, clock, db = env
    c = player(app, db, 'oszczedny', xp=LVL10)
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET hunger=20 WHERE id=?', (a,))
    mgr(c, hours=2, feed=False)
    assert row(db, a)['hunger'] == 20 and st(db)['aiManager'].get('feeds', 0) == 0


def test_safe_avoids_burnout(env):
    app, clock, db = env
    c = player(app, db, 'ostrozny', xp=LVL10)
    patch(db, lambda s: s.update(servicesUnlocked=['callcenter', 'marketing']))   # same usługi obniżające nastrój
    a, b = hire(c, db), hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET mood=34')
    n = row(db, a)
    ests = N.ranked(n, st(db), 8, None, T0, 2, E, S)
    assert any(e['burnout'] for e in ests) and any(not e['burnout'] for e in ests)
    mgr(c, hours=8, policy='safe', exclude=[b])
    assert row(db, a)['assigned_service_id'] == next(e for e in ests if not e['burnout'])['service']
    mgr(c, hours=8, policy='max')                                # b dochodzi (a już pracuje)
    assert row(db, b)['assigned_service_id'] == ests[0]['service']


def test_safe_falls_back_to_regen_when_exhausted(env):
    app, clock, db = env
    c = player(app, db, 'zmeczony', xp=LVL10)
    patch(db, lambda s: s.update(servicesUnlocked=['biblioteka']))
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET mood=20, unhappy_since=? WHERE id=?', (T0, a))
    mgr(c, hours=4, policy='safe')
    assert row(db, a)['assigned_service_id'] in S.REGEN


def test_disable_stops_chain_but_running_shift_pays_fee(env):
    app, clock, db = env
    c = player(app, db, 'rezygnacja', xp=LVL10)
    a = hire(c, db)
    mgr(c, hours=2)
    clock[0] += 10 * M
    r = post(c, 'npcs/manager', dict(enabled=False))
    assert r.status_code == 200 and not r.json()['manager']['active'] and r.json()['manager']['shifts'] == 1
    clock[0] += 5 * H
    c.get('/api/worlds/2/npcs')
    m = st(db)['aiManager']
    assert row(db, a)['phase'] is None and m['shifts'] == 1 and m['fees'] > 0


def test_manager_keeps_car(env):
    app, clock, db = env
    c = player(app, db, 'kierownik', xp=LVL10, garage=['sedan'])
    a = hire(c, db); driver(c, db)
    mgr(c, hours=2)
    assert row(db, a)['pref_car'] == 'sedan' and row(db, a)['leg_mode'] == 'car'   # v3.2: auto preferowane + kurs
    clock[0] += 3 * H
    c.get('/api/worlds/2/npcs')
    r = row(db, a)
    assert r['shift_manager'] == 1 and r['pref_car'] == 'sedan' and st(db)['aiManager']['shifts'] == 2


def test_manual_shift_has_no_commission(env):
    app, clock, db = env
    c = player(app, db, 'reczny', xp=LVL10)
    a, b = hire(c, db), hire(c, db)
    post(c, f'npcs/{b}/dispatch', dict(service_id='minimarket', hours=2))   # ręcznie, przed managerem
    mgr(c, hours=2, exclude=[a])
    clock[0] += 2 * H + 3 * M
    c.get('/api/worlds/2/npcs')
    m = st(db)['aiManager']
    assert m.get('fees', 0) == 0                                  # ręczna zmiana b — bez prowizji
    rb = row(db, b)                                              # b wrócił → od razu przejęty przez managera
    assert m['shifts'] == 1 and rb['shift_manager'] == 1 and rb['shift_started_at'] == T0 + 2 * H + 2 * M
    assert row(db, a)['phase'] is None                           # a wykluczony
