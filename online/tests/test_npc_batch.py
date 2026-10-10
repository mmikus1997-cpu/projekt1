"""2.5 GDD v3.1: akcje zbiorcze NPC — dispatch/recall/feed, 'best', auta 'auto', częściowy sukces, licznik tras = 1."""
import sqlite3
from server import npc as N, services as S
from server import economy as E
from tests.test_npc_shift import env, player, patch, cash, post, hire, driver, H, M, T0  # noqa: F401


def batch(c, **body):
    return post(c, 'npcs/batch', body)


def test_dispatch_idle_partial_success(env):
    app, clock, db = env
    c = player(app, db, 'zbiorowy')
    a, b, d = hire(c, db), hire(c, db), hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET energy=10 WHERE id=?', (d,))
    r = batch(c, action='dispatch', npcs='idle', service_id='minimarket', hours=2)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j['okCount'] == 2 and j['message'] == 'Wysłano 2/3 NPC.'
    bad = next(x for x in j['results'] if x['npc'] == d)
    assert not bad['ok'] and 'zmęczony' in bad['message']
    assert sorted(n['id'] for n in j['npcs'] if n['phase']) == sorted([a, b])


def test_batch_counts_as_one_route(env):
    app, clock, db = env
    c = player(app, db, 'hurtownik', cash=200000)
    patch(db, lambda s: s.setdefault('buildings', {}).update(residence=5))
    team = [hire(c) for _ in range(15)]
    assert batch(c, action='dispatch', npcs=team[:12], service_id='minimarket', hours=2).json()['okCount'] == 12
    with sqlite3.connect(db) as x:
        import json
        disp = json.loads(x.execute('SELECT state_json FROM characters').fetchone()[0])['dispatch']
    assert disp['streak'] == 1 and not disp.get('cooldownUntil')
    for i in range(12, 15):                    # pojedyncze dalej liczą się po 1
        assert post(c, f'npcs/{team[i]}/dispatch', dict(service_id='minimarket', hours=2)).status_code == 200


def test_batch_blocked_during_cooldown(env):
    app, clock, db = env
    c = player(app, db, 'przerwa')
    a = hire(c)
    patch(db, lambda s: s.update(dispatch=dict(cooldownUntil=T0 + M, streak=0, lastAt=T0)))
    r = batch(c, action='dispatch', npcs=[a], service_id='minimarket', hours=2)
    assert r.status_code == 409 and 'Przerwa dyspozytora' in r.json()['detail']


def test_cars_auto_fastest_first_then_bus(env):
    app, clock, db = env
    c = player(app, db, 'flota', garage=['dostawczak', 'suv'])
    team = [hire(c) for _ in range(3)]
    driver(c, db)
    j = batch(c, action='dispatch', npcs=team, service_id='minimarket', hours=2, cars='auto').json()
    # v3.2: jeden kierowca, najszybsze auto (SUV, 4 miejsca) — wszyscy trzej jednym kursem
    assert [x['car'] for x in j['results']] == ['suv'] * 3 and j['rideCount'] == 1
    by = {n['id']: n for n in j['npcs']}
    assert not any(by[i]['bus'] for i in team) and len({by[i]['rideId'] for i in team}) == 1


def test_best_picks_highest_estimate(env):
    app, clock, db = env
    c = player(app, db, 'optymalny', xp=1000)
    a = hire(c, db)
    patch(db, lambda s: s.update(servicesUnlocked=['kurier', 'callcenter']))
    j = batch(c, action='dispatch', npcs=[a], service_id='best', hours=4).json()
    assert j['okCount'] == 1
    with sqlite3.connect(db) as x:
        x.row_factory = sqlite3.Row
        n = dict(x.execute('SELECT * FROM npcs WHERE id=?', (a,)).fetchone())
    sid = j['results'][0]['service']
    import json
    st = json.loads(sqlite3.connect(db).execute('SELECT state_json FROM characters').fetchone()[0])
    n.update(energy=100, mood=100, hunger=100, unhappy_since=None)
    best = N.ranked(dict(n, phase=None), st, 4, None, T0, 2, E, S)
    assert best and sid == best[0]['service'] and len(best) >= 4


def test_recall_and_feed_batch(env):
    app, clock, db = env
    c = player(app, db, 'kucharz', buffet=3)
    team = [hire(c, db) for _ in range(2)]
    batch(c, action='dispatch', npcs='idle', service_id='minimarket', hours=8)
    clock[0] += H
    r = batch(c, action='recall', npcs='all').json()
    assert r['okCount'] == 2
    clock[0] += 5 * M
    c.get('/api/worlds/2/npcs')
    c0 = cash(db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET hunger=20')
    r = batch(c, action='feed', npcs=team).json()
    assert r['okCount'] == 2 and cash(db) == c0 - 2 * N.MEALS[3]['cost']   # Premium catering: 20 → 60
    r = batch(c, action='all_to_buffet', npcs=team).json()
    assert r['okCount'] == 2                 # 60 → 100 (4.4: all_to_buffet = feed)
    r = batch(c, action='feed', npcs=team).json()
    assert r['okCount'] == 0 and all('najedzony' in x['message'] for x in r['results'])


def test_validation(env):
    app, clock, db = env
    c = player(app, db, 'walidator')
    a = hire(c)
    assert batch(c, action='dispatch', npcs=[a]).status_code == 422
    assert batch(c, action='dispatch', npcs=[999], service_id='minimarket', hours=2).status_code == 404
    assert batch(c, action='feed', npcs=[]).status_code == 422
    assert batch(c, action='recall', npcs='all').json()['okCount'] == 0


def test_estimate_matches_real_settlement(env):
    """Prognoza = rzeczywista wypłata (ta sama funkcja advance)."""
    app, clock, db = env
    c = player(app, db, 'prognosta', xp=300)
    a = hire(c, db)
    with sqlite3.connect(db) as x:
        x.row_factory = sqlite3.Row
        n = dict(x.execute('SELECT * FROM npcs WHERE id=?', (a,)).fetchone())
    est = N.estimate(n, S.BY_ID['sprzatanie'], 8, None, T0, 2, E, S)
    c0 = cash(db)
    assert post(c, f'npcs/{a}/dispatch', dict(service_id='sprzatanie', hours=8)).status_code == 200
    clock[0] = est['endsAt'] + 1
    c.get('/api/worlds/2/npcs')
    assert cash(db) - c0 == est['cash']
