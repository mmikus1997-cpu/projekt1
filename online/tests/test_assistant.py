"""2.6 GDD v3.1: Asystent Podróży — plany NPC (estimate), alerty, porady podróży gracza."""
import sqlite3
from server import npc as N, services as S
from server import economy as E
from tests.test_npc_shift import env, player, patch, cash, post, hire, driver, H, M, T0  # noqa: F401


def ask(c, hours=8):
    r = c.get(f'/api/worlds/2/assistant?hours={hours}')
    assert r.status_code == 200, r.text
    return r.json()


def test_plans_top3_with_cars_and_batch_hint(env):
    app, clock, db = env
    c = player(app, db, 'doradzany', xp=1000, garage=['sedan'])
    a, b = hire(c, db), hire(c, db)
    driver(c, db)                                          # v3.2: auta tylko z kierowcą
    j = ask(c, 4)
    assert j['hours'] == 4 and len(j['plans']) == 2
    p0, p1 = j['plans']
    assert p0['car'] == 'sedan' and p1['car'] is None
    assert len(p0['options']) == 3
    cs = [o['cash'] for o in p0['options']]
    assert cs == sorted(cs, reverse=True)
    assert j['expectedTotal'] == p0['options'][0]['cash'] + p1['options'][0]['cash']
    assert j['batch'] == dict(action='dispatch', npcs='idle', service_id='best', hours=4, cars='auto')
    # wskazówka jest dokładna: wysłanie wg planu daje prognozowaną kwotę
    o = p0['options'][0]; c0 = cash(db)   # v3.2: plan z autem — kierowca wiezie tam i z powrotem
    assert post(c, f"npcs/{p0['npc']}/dispatch", dict(service_id=o['service'], hours=4, car_id='sedan')).status_code == 200
    clock[0] = o['endsAt'] + 1
    c.get('/api/worlds/2/npcs')
    assert cash(db) - c0 == o['cash']


def test_assistant_is_read_only_for_state(env):
    app, clock, db = env
    c = player(app, db, 'tylkoczyta')
    hire(c, db)
    c0 = cash(db)
    ask(c); ask(c)
    assert cash(db) == c0


def test_alerts_exhausted_hungry_resting(env):
    app, clock, db = env
    c = player(app, db, 'alarmowy')
    a, b = hire(c, db), hire(c, db)
    with sqlite3.connect(db) as x:
        x.execute('UPDATE npcs SET hunger=20, unhappy_since=? WHERE id=?', (T0, a))
        x.execute('UPDATE npcs SET energy=20 WHERE id=?', (b,))
    j = ask(c)
    kinds = {(al['kind'], al.get('npc')) for al in j['alerts']}
    assert ('exhausted', a) in kinds and ('hungry', a) in kinds
    ex = next(al for al in j['alerts'] if al['kind'] == 'exhausted')
    assert ex['cause'] == 'hunger' and 'głodny' in ex['text']
    rest = next(r for r in j['resting'] if r['npc'] == b)
    assert rest['readyAt'] == T0 + 2 * H                  # 20 → 40 przy +10/h (optymista)
    assert all(p['npc'] != b for p in j['plans'])


def test_alert_shift_ending_and_cars_idle(env):
    app, clock, db = env
    c = player(app, db, 'zmianowy', garage=['dostawczak'])
    a = hire(c, db)
    post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2))   # autobusem, rower wolny
    clock[0] += 70 * M
    assert any(al['kind'] == 'need_driver' for al in ask(c)['alerts'])       # v3.2: brak kierowcy
    driver(c, db)
    j = ask(c)
    end = next(al for al in j['alerts'] if al['kind'] == 'shift_ending')
    assert end['npc'] == a and '50 min' in end['text']
    idle = next(al for al in j['alerts'] if al['kind'] == 'cars_idle')
    assert idle['cars'] == ['dostawczak']


def test_alert_demand_change_window(env):
    app, clock, db = env
    c = player(app, db, 'rynkowy')
    nxt = (clock[0] // S.DEMAND_WINDOW_MS + 1) * S.DEMAND_WINDOW_MS
    clock[0] = nxt - 10 * M
    assert any(al['kind'] == 'demand_change' and '10 min' in al['text'] for al in ask(c)['alerts'])
    clock[0] = nxt + 10 * M
    assert not any(al['kind'] == 'demand_change' for al in ask(c)['alerts'])


def test_alert_can_recruit(env):
    app, clock, db = env
    c = player(app, db, 'rekruter')
    assert any(al['kind'] == 'can_recruit' for al in ask(c)['alerts'])
    patch(db, lambda s: s.update(cash=10))
    assert not any(al['kind'] == 'can_recruit' for al in ask(c)['alerts'])


def test_travel_advice(env):
    app, clock, db = env
    c = player(app, db, 'podroznik')
    t = ask(c)['travel']
    assert not t['traveling'] and t['from_'] == 1
    to2 = next(o for o in t['options'] if o['district'] == 2)
    assert to2['open'] and to2['recommended'] == 'bus' and to2['bus']['fare'] == 20
    assert to2['bus']['ms'] >= 60000 and to2['car']['ms'] is None
    patch(db, lambda s: s.update(vehicle=dict(id='sedan', wear=0), garage=['sedan']))
    to2 = next(o for o in ask(c)['travel']['options'] if o['district'] == 2)
    assert to2['recommended'] == 'car' and to2['car']['ms'] < to2['bus']['ms']
    a = hire(c, db); driver(c, db)                         # auto w kursie kierowcy NPC → autobus
    post(c, f'npcs/{a}/dispatch', dict(service_id='minimarket', hours=2, car_id='sedan'))
    to2 = next(o for o in ask(c)['travel']['options'] if o['district'] == 2)
    assert to2['recommended'] == 'bus' and to2['car']['busyUntil'] and 'NPC' in to2['why']
    patch(db, lambda s: s.update(cash=5))
    to2 = next(o for o in ask(c)['travel']['options'] if o['district'] == 2)
    assert to2['recommended'] == 'hitchhike'


def test_hours_validation(env):
    app, clock, db = env
    c = player(app, db, 'walid')
    assert c.get('/api/worlds/2/assistant?hours=3').status_code == 422
