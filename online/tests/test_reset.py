"""4.5 GDD v3.1: Sala Chwały — RESET (3 kroki), efekty, zachowane dane, nagrody, bonus dochodu."""
import json
import sqlite3
import uuid
import pytest
from server import economy as E, prestige as P
from tests.test_npc_shift import env, player, patch, cash, hire, T0  # noqa: F401
from tests.test_fuel import st, act


def reset(c, **body):
    return c.post('/api/worlds/2/server_reset', headers={'Idempotency-Key': uuid.uuid4().hex}, json=body)


def q(db, sql, *a):
    with sqlite3.connect(db) as x:
        return x.execute(sql, a).fetchone()


def ready(db):
    patch(db, lambda s: s.update(cash=99999, diamonds=7, buffet=2, stats=[40, 30, 20, 20, 20], evolutionCode='zelazna-piesc',
                                 garage=['sedan'], vehicle=dict(id='sedan', wear=0), horse=dict(id='kuc', name='Kuc', speed=2, stamina=2),
                                 horses={'stable-kuc': {}}, avatar={'body': 'b1', 'worn': [], 'owned': ['x']},
                                 buildings=dict(residence=5, garage=5, cafe=10, nightclub=7, club=1, hall=1)))


def test_gate_requires_hall(env):
    app, clock, db = env
    c = player(app, db, 'nowicjusz')
    r = reset(c); assert r.status_code == 409 and 'Sali Chwały' in r.json()['detail']


def test_three_steps_and_effects(env):
    app, clock, db = env
    c = player(app, db, 'weteran')
    hire(c, db); ready(db)
    xp0 = st(db)['xp']
    assert reset(c, confirm_text=P.RESET_CONFIRM).status_code == 409          # bez kroku 1
    r = reset(c).json()
    assert r['step'] == 1 and r['resetNumber'] == 1 and r['bonusAfter'] == 10 and r['diamondsToAccount'] == 7 and r['npcs'] == 1
    assert reset(c, confirm_text='reset').status_code == 422                     # zły tekst
    clock[0] += 5000
    r = reset(c, confirm_text=P.RESET_CONFIRM); assert r.status_code == 409 and 'Odczekaj' in r.json()['detail']
    clock[0] += 5000
    r = reset(c, confirm_text=P.RESET_CONFIRM)
    assert r.status_code == 200, r.text
    j = r.json(); assert j['done'] and j['bonus'] == 10 and j['prestigePoints'] == 1 and j['premiumCurrency'] == 7
    s = st(db)
    assert s['buildings'] == E.BUILDING_START and s['buffet'] == 0 and s['garage'] == [] and s['vehicle'] is None
    assert s['horse'] is None and s['horses'] == {} and s['stats'] == [10] * 5 and s['evolutionCode'] is None
    assert s['cash'] == E.new(T0)['cash'] and 'diamonds' not in s
    assert s['avatar']['owned'] == ['x'] and s['xp'] == 0 and s['business']['level'] == 1   # korekta: poziom i firmy od zera
    assert 'reset-1' in s['frames']
    assert s['prestige'] == dict(resets=1, bonus=10) and s['frame'] == 'reset-1'
    cid = q(db, "SELECT id FROM characters WHERE nickname LIKE '%' ORDER BY id DESC LIMIT 1")[0]
    assert q(db, 'SELECT count(*) FROM npcs WHERE character_id=?', cid)[0] == 0
    assert q(db, 'SELECT class_evolution FROM characters WHERE id=?', cid)[0] == 1
    assert q(db, "SELECT label FROM character_titles WHERE code='reset_1'")[0] == 'Reset #1'
    assert q(db, "SELECT count(*) FROM audit WHERE event='server.reset'")[0] == 1
    assert q(db, "SELECT count(*) FROM chronicle WHERE kind='server_reset'")[0] == 1
    assert q(db, "SELECT count(*) FROM game_events WHERE kind='prestige.reset'")[0] == 1
    assert reset(c).status_code == 409                                            # Sala Chwały wyzerowana


def test_bonus_cumulative_capped_and_applied():
    assert [P.bonus_for(n) for n in (1, 2, 5, 6, 9)] == [10, 20, 50, 50, 50]
    s = E.new(T0); E.sync(s, T0, 1)
    s['prestige'] = dict(resets=3, bonus=30); s['vaults']['cafe'] = 100.0
    c0 = s['cash']; E.action(s, 'collect', dict(business='cafe'), T0, 1)
    assert s['cash'] == c0 + 130                                                  # +30% od odbioru skarbca
    assert E.prestige_mult(dict(prestige=dict(bonus=90))) == 1.5                  # sufit +50%


def test_second_reset_number_and_bonus(env):
    app, clock, db = env
    c = player(app, db, 'dwukrotny')
    for n in (1, 2):
        ready(db)
        reset(c); clock[0] += 10_000
        j = reset(c, confirm_text=P.RESET_CONFIRM).json()
        assert j['resetNumber'] == n and j['bonus'] == 10 * n and j['prestigePoints'] == n
    assert st(db)['frame'] == 'reset-2'
