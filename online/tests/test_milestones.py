"""3.4 GDD v3.1: licznik dni aktywności (UTC) i auto „Mistrz Rankingu” za 7 dni."""
import sqlite3
from tests.test_npc_shift import env, player, patch, T0  # noqa: F401
from tests.test_fuel import st

DAY = 86400000


def lp(db):
    with sqlite3.connect(db) as x:
        x.row_factory = sqlite3.Row
        return dict(x.execute('SELECT * FROM longplay_milestones ORDER BY character_id DESC LIMIT 1').fetchone())


def count(db, sql):
    with sqlite3.connect(db) as x:
        return x.execute(sql).fetchone()[0]


def test_seven_active_days_unlock_mistrz_once(env):
    app, clock, db = env
    c = player(app, db, 'wytrwaly', garage=['sedan'], vehicle=dict(id='sedan', wear=0))
    patch(db, lambda s: s['garage'].remove('mistrz') if 'mistrz' in s['garage'] else None)
    assert c.get('/api/worlds/2/state').status_code == 200
    base = lp(db)['active_days']
    for _ in range(3):                                   # ten sam dzień UTC — bez zmian
        c.get('/api/worlds/2/state')
    assert lp(db)['active_days'] == base
    day = base
    while day < 6:
        clock[0] += DAY; c.get('/api/worlds/2/state'); day += 1
        assert lp(db)['active_days'] == day and 'mistrz' not in st(db)['garage']
    clock[0] += DAY
    r = c.get('/api/worlds/2/state')
    assert r.status_code == 200 and 'mistrz' in r.json()['state']['garage']     # odpowiedź już z nagrodą
    assert lp(db)['active_days'] == 7 and 'mistrz_7d' in lp(db)['claimed_milestones']
    assert st(db)['vehicle']['id'] == 'sedan'                                    # aktywne auto bez zmian
    assert count(db, "SELECT count(*) FROM game_events WHERE kind='milestone.unlocked'") == 2   # 8.1: mistrz_7d + staz_7 (Debiutant)
    assert count(db, "SELECT count(*) FROM audit WHERE event='milestone.unlocked'") == 2
    m = c.get('/api/worlds/2/milestones').json()
    assert m['activeDays'] == 7 and m['milestones'][0]['claimed'] is True
    with sqlite3.connect(db) as x:                       # kolejny dzień (sesja testowa ma limit 7 dni → cofamy datę w bazie)
        x.execute("UPDATE longplay_milestones SET last_active_utc='1970-01-01'")
    assert c.get('/api/worlds/2/state').status_code == 200
    assert lp(db)['active_days'] == 8 and st(db)['garage'].count('mistrz') == 1
    assert count(db, "SELECT count(*) FROM game_events WHERE kind='milestone.unlocked'") == 2   # 8.1: mistrz_7d + staz_7 (Debiutant)


def test_mistrz_becomes_active_when_no_car(env):
    app, clock, db = env
    c = player(app, db, 'pieszy', garage=[], vehicle=None)
    with sqlite3.connect(db) as x:
        cid = x.execute('SELECT id FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0]
        x.execute("INSERT OR REPLACE INTO longplay_milestones VALUES(?,6,'1970-01-01','[]')", (cid,))
    c.get('/api/worlds/2/state')
    s = st(db)
    assert s['garage'] == ['mistrz'] and s['vehicle']['id'] == 'mistrz' and s['cars']['mistrz']['fuel'] == 100
