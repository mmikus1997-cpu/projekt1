"""0.9 deeper economy: vehicles with wear, staff boosts, daily market, tenders, district investments."""
import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server import economy as E


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock, tmp_path


def register(app, name):
    client = TestClient(app)
    r = client.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    assert r.status_code == 200, r.text
    client.headers['X-CSRF-Token'] = r.json()['csrf']
    return client


def create(c, wid=2, name='EkoOne'):
    r = c.post(f'/api/worlds/{wid}/character', json={'nickname': name, 'accept_test_reset': True})
    assert r.status_code == 200, r.text
    return r.json()


def action(c, kind, wid=2, **kwargs):
    return c.post(f'/api/worlds/{wid}/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': kind, **kwargs})


def state(c, wid=2):
    return c.get(f'/api/worlds/{wid}/state').json()


def _seed_district(app, d, wid=2):
    with app.state.db.tx() as cx:
        cx.execute('UPDATE characters SET current_district=? WHERE world_id=?', (d, wid))  # 0.45: kontrakty w swoich dzielnicach (świat 2)


def set_state(app, cid, patch):
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        row = db.execute('SELECT state_json FROM characters WHERE id=?', (cid,)).fetchone()
        st = json.loads(row[0]);st.update(patch)
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st), cid))


def test_market_prices_are_deterministic_per_world_day(env):
    app, clock, path = env
    assert E.price_mult(1, 'delivery', 20000) == E.price_mult(1, 'delivery', 20000)
    assert 0.85 <= E.price_mult(2, 'delivery', 20000) <= 1.15
    c = register(app, 'market_one')
    create(c)
    _seed_district(app, 8)
    data = state(c)
    prices = data['catalog']['prices']
    assert set(prices) == {x['id'] for x in data['catalog']['contracts']}
    assert all(0.85 <= v <= 1.15 for v in prices.values())
    # A separate character in the same world sees the same market.
    c2 = register(app, 'market_two')
    create(c2, 2, 'EkoTwo')
    assert state(c2)['catalog']['prices'] == prices


def test_vehicle_speeds_contracts_and_wears_out(env, flat_stats):
    app, clock, path = env
    c = register(app, 'vehicle_one')
    create(c)
    _seed_district(app, 8)
    assert action(c, 'contract', contract='delivery').status_code == 200
    base = state(c)['state']['contracts'][0]
    clock[0] += 3600_000
    assert action(c, 'claim_contract', task_id=base['id']).status_code == 200
    # Buy and ride; new contracts take 10% less time.
    assert action(c, 'buy_vehicle', vehicle='dostawczak').status_code == 200
    assert action(c, 'contract', contract='delivery').status_code == 200
    rower = state(c)['state']['contracts'][-1]
    assert rower['end'] - rower['start'] == round(10 * E.MINUTE * 0.9 / 60)
    # Wear grows on completion; at 100 the discount stops until paid service.
    clock[0] += 3600_000
    assert action(c, 'claim_contract', task_id=rower['id']).status_code == 200
    assert state(c)['state']['vehicle']['wear'] == 6
    cid = state(c)['character']['id']
    set_state(app, cid, {'vehicle': {'id': 'dostawczak', 'wear': 100}})
    assert action(c, 'contract', contract='delivery').status_code == 200
    worn = state(c)['state']['contracts'][-1]
    assert worn['end'] - worn['start'] == round(10 * E.MINUTE / 60)  # no discount
    clock[0] += 3600_000
    assert action(c, 'claim_contract', task_id=worn['id']).status_code == 200
    assert action(c, 'service_vehicle').status_code == 200
    assert state(c)['state']['vehicle']['wear'] == 0


def test_staff_boosts_business_income_for_a_day(env):
    app, clock, path = env
    c = register(app, 'staff_one')
    create(c)
    _seed_district(app, 8)
    # Café gates at level 2, so exercise the boost on the starting courier business.
    assert action(c, 'hire_staff', staff='courier').status_code == 200
    assert action(c, 'hire_staff', staff='courier').status_code == 409
    clock[0] += E.HOUR  # 1 real hour at ×60 = 60 game hours; staff covers the first 24
    vault = state(c)['state']['business']['vault']
    # 24 game hours at 25% boosted 50 $/h = 1200; remaining 36 at 40 $/h = 1440 → 2640.
    assert vault == pytest.approx(2640, abs=1)
    clock[0] += round(23 * E.HOUR / 60)
    assert state(c)['state']['staff']['courier'] < clock[0]
    assert action(c, 'hire_staff', staff='courier').status_code == 200  # rehire after expiry


def test_tender_is_personal_daily_offer_with_fixed_price(env):
    app, clock, path = env
    c = register(app, 'tender_one')
    created = create(c)
    day = E.day_of(clock[0])
    t = state(c)['catalog']['tender']
    assert t['day'] == day and t['cash'] > 0 and t['expires_at'] > clock[0]
    # Level gate respected (this seed may draw fleet/branch/campaign — all above level 1).
    r = action(c, 'tender_accept')
    if t['level'] > 1:
        assert r.status_code == 409
        return
    assert r.status_code == 200
    task = state(c)['state']['contracts'][-1]
    assert task['tender'] and task['cash'] == t['cash']
    assert action(c, 'tender_accept').status_code == 409  # once per day


def test_district_investments_give_personal_bonus_and_world_totals(env, flat_stats):
    app, clock, path = env
    c = register(app, 'invest_one')
    create(c)
    _seed_district(app, 8)
    for _ in range(3):  # LAB grants 3 000 $ — exactly the three investments below
        assert action(c, 'invest', district='Portowe', amount=1000).status_code == 200
    assert action(c, 'invest', district='Nope', amount=100).status_code == 409
    assert action(c, 'invest', district='Portowe', amount=50).status_code == 409
    d = [d for d in state(c)['catalog']['districts'] if d['name'] == 'Portowe'][0]
    assert d['mine'] == 3000 and d['bonus'] == 3 and d['world'] == 3000
    # Bonus applies to Port contracts at claim time (unit check on the payout function).
    s_obj = E.new(clock[0], test=True)
    s_obj['invested'] = {'Portowe': 3000}
    contract = next(x for x in E.CONTRACTS if x['id'] == 'logistics')
    day = E.day_of(clock[0])
    expected = round(400 * E.price_mult(2, 'logistics', day) * 1.11)  # 0.45: +8% dojazd (Port, 2 przystanki)
    assert E.payout(2, s_obj, contract, day) == expected
    assert E.payout(2, s_obj, contract, day) != E.payout(1, s_obj, contract, day) or E.price_mult(1, 'logistics', day) == E.price_mult(2, 'logistics', day)
    # Personal cap: 20000 per district.
    r = action(c, 'invest', district='Portowe', amount=5000)
    assert r.status_code == 409
