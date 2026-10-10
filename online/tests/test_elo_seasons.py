"""5.4 GDD v3.1: miesięczne sezony Elo per świat — nagrody Top 10/100/1000, reset Elo, brak nowych sezonów XP."""
import json
from server import seasons as S
from server import features as F
from tests.test_pvp_active import env, register, create, grant, attack, _cid  # noqa: F401

OCT = 1790812800000   # 2026-10-01 00:00 UTC
NOV = 1793491200000   # 2026-11-01 00:00 UTC


def test_numbering_and_bounds():
    assert S.month_season(OCT) == 10 and S.month_season(OCT - 1) == 9 and S.month_season(NOV) == 11
    assert S.bounds(10) == (OCT, NOV) and S.bounds(12)[1] == 1798761600000   # 2027-01-01
    assert S.tier_of(1)[0] == 'diamond' and S.tier_of(10)[0] == 'diamond' and S.tier_of(11)[0] == 'gold'
    assert S.tier_of(100)[0] == 'gold' and S.tier_of(101)[0] == 'silver' and S.tier_of(1001) is None


def _state(app, nick):
    with app.state.db.read() as c:
        r = c.execute('SELECT id,rating,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
    return r['rating'], json.loads(r['state_json'])


def test_season_close_rewards_and_reset(env):
    app, clock = env
    clock[0] = OCT + 5 * 86400000
    a = register(app, 'seas_a'); create(a, 2, name='SeasA'); b = register(app, 'seas_b'); create(b, 2, name='SeasB')
    c3 = register(app, 'seas_c'); create(c3, 2, name='Idle')
    grant(app, 'SeasA', tactic='kontrola', xp=400); grant(app, 'SeasB', xp=400)
    assert attack(a, 2, _cid(app, 'SeasB')).status_code == 200
    info = a.get('/api/worlds/2/elo-season').json()
    assert info['season'] == 10 and info['endsAt'] == NOV and info['monthly']
    clock[0] = NOV + 1000                                 # 1 listopada — sezon 10 się zakończył
    with app.state.db.tx() as c:
        assert app.state.seasons['ensure'](c) >= 1                # zamknięcie (sweep/leniwe)
    for nick in ('SeasA', 'SeasB'):
        rating, s = _state(app, nick)
        assert rating == 1000 and 'season-10-diamond' in s['frames'] and s['diamonds'] >= 600
    rating, s = _state(app, 'Idle')
    assert rating == 1000 and not any(f.startswith('season-') for f in s.get('frames', []))   # bez walki = bez nagrody
    with app.state.db.read() as c:
        assert c.execute("SELECT count(*) FROM character_titles WHERE season=10 AND code='season_top10'").fetchone()[0] == 2
        assert c.execute("SELECT count(*) FROM game_events WHERE kind='season.reward'").fetchone()[0] == 2
    with app.state.db.read() as c:
        assert sorted(r[0] for r in c.execute('SELECT place FROM elo_season_results WHERE season=10')) == [1, 2]
    # idempotencja — drugie wywołanie nie dubluje nagród
    d0 = _state(app, 'SeasA')[1]['diamonds']
    with app.state.db.tx() as c:
        assert app.state.seasons['ensure'](c) == 0
    assert _state(app, 'SeasA')[1]['diamonds'] == d0


def test_place_tiers_gold_and_silver(env):
    app, clock = env
    clock[0] = OCT + 86400000
    names = []
    for i in range(3):
        cl = register(app, 'tier' + str(i)); create(cl, 2, name='Tier' + str(i)); names.append('Tier' + str(i))
    with app.state.db.tx() as c:
        day = clock[0] // 86400000 * 86400000
        for i, n in enumerate(names):
            cid = c.execute('SELECT id FROM characters WHERE nickname=?', (n,)).fetchone()[0]
            c.execute('UPDATE characters SET rating=? WHERE id=?', (1500 - i * 100, cid))
            c.execute('INSERT INTO ranked_usage(character_id,day,used) VALUES(?,?,1)', (cid, day))
    old = S.TIERS
    S.TIERS = ((1, 'diamond', 600, 'D'), (2, 'gold', 200, 'Z'), (1000, 'silver', 50, 'S'))   # mini-progi do testu
    try:
        clock[0] = NOV + 1
        cl = register(app, 'viewer'); create(cl, 2, name='Viewer'); cl.get('/api/worlds/2/players')
    finally:
        S.TIERS = old
    h = cl.get('/api/worlds/2/elo-season').json()
    assert h['season'] == 11 and h['history'] == [] and h['rating'] == 1000
    got = [(_state(app, n)[1].get('diamonds', 0), [f for f in _state(app, n)[1]['frames'] if f.startswith('season-')]) for n in names]
    assert got == [(600, ['season-10-diamond']), (200, ['season-10-gold']), (50, ['season-10-silver'])]


def test_xp_seasons_frozen():
    assert F.XP_SEASON_LAST == 9 and F.season_of(OCT) == 10   # 28-dniowa numeracja dobiega 10 → nowa = miesięczna
