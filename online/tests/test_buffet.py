"""4.4 GDD v3.1: Buffet w Rezydencji — rozbudowa, 3 posiłki, feed_npc, all_to_buffet, koniec przemęczenia z głodu."""
import sqlite3
import uuid
import pytest
from server import economy as E, npc as N
from tests.test_npc_shift import env, player, patch, cash, post, hire, T0  # noqa: F401
from tests.test_fuel import st, act


def set_npc(db, nid, **kw):
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET ' + ','.join(k + '=?' for k in kw) + ' WHERE id=?', (*kw.values(), nid))


def feed(c, **body):
    return c.post('/api/worlds/2/npcs/feed', headers={'Idempotency-Key': uuid.uuid4().hex}, json=body)


def test_upgrade_buffet_gate_and_costs():
    s = E.new(T0); E.sync(s, T0, 1); s['cash'] = 10**6
    with pytest.raises(E.RuleError, match='Rezydencji'): E.action(s, 'upgrade_buffet', {}, T0, 1)
    s['buildings']['residence'] = 2
    for lv in range(3):
        c0 = s['cash']; E.action(s, 'upgrade_buffet', {}, T0, 1)
        assert E.buffet_level(s) == lv + 1 and s['cash'] == c0 - E.BUFFET_COSTS[lv]
    with pytest.raises(E.RuleError, match='najwyższym'): E.action(s, 'upgrade_buffet', {}, T0, 1)


def test_meals_table():
    assert [(m['cost'], m['hunger'], m['mood'], m['energy']) for m in N.MEALS.values()] == [(10, 15, 0, 0), (25, 25, 5, 0), (60, 40, 15, 5)]


def test_basic_meal_always_higher_need_buffet(env):
    app, clock, db = env
    c = player(app, db, 'bezbufetu')
    a = hire(c, db); set_npc(db, a, hunger=50)
    r = feed(c, npc_id=a, meal=2); assert r.status_code == 409 and 'poziomie 2' in r.json()['detail']
    c0 = cash(db)
    r = feed(c, npc_id=a); assert r.status_code == 200, r.text            # korekta: Zwykłe jedzenie bez Buffetu
    assert cash(db) == c0 - 10 and r.json()['npcs'][0]['hunger'] == 65
    patch(db, lambda s: s.update(buffet=2))
    assert feed(c, npc_id=a, meal=2).status_code == 200
    assert feed(c, npc_id=a, meal=4).status_code == 422


def test_premium_effects_and_cap(env):
    app, clock, db = env
    c = player(app, db, 'smakosz', buffet=3)
    a = hire(c, db); set_npc(db, a, hunger=70, mood=90, energy=98)
    n = feed(c, npc_id=a).json()['npcs'][0]                     # domyślnie najlepszy: Premium
    assert n['hunger'] == 100 and n['mood'] == 100 and n['energy'] == 100   # obcięte do 100
    assert feed(c, npc_id=a).status_code == 409                # najedzony


def test_hunger_only_cause_recovers_instantly_other_cause_not(env):
    app, clock, db = env
    c = player(app, db, 'zmeczony', buffet=1)
    a, b = hire(c, db), hire(c, db)
    set_npc(db, a, hunger=20, mood=50, energy=50, unhappy_since=clock[0])   # tylko głód < 30
    set_npc(db, b, hunger=20, mood=20, energy=50, unhappy_since=clock[0])   # także nastrój < 30
    r = c.post('/api/worlds/2/npcs/batch', headers={'Idempotency-Key': uuid.uuid4().hex},
               json=dict(action='all_to_buffet', npcs=[a, b], meal=1)).json()
    by = {x['npc']: x for x in r['results']}
    assert r['okCount'] == 2 and by[a]['exhausted'] is False and by[b]['exhausted'] is True
