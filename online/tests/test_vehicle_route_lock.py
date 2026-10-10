"""GDD v3.1 1.4: auto nie może jednocześnie jechać w trasie NPC i wieźć gracza (oba kierunki)."""
import json
import sqlite3
from tests.test_travel import env, register, create, action, go  # noqa: F401


def patch(app, nick, upd):
    with sqlite3.connect(app.state.db.path, timeout=15) as db:
        cid, sj = db.execute('SELECT id,state_json FROM characters WHERE nickname=?', (nick,)).fetchone()
        st = json.loads(sj); st.update(upd)
        db.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(st), cid))


def fleet(app, nick, clock, end_delta):
    patch(app, nick, dict(cash=5000, garage=['furgonetka', 'dostawczak'], vehicle=dict(id='furgonetka', wear=0),
                          npcRoutes=dict(runs=[dict(route='courier', vehicle='furgonetka', start=clock[0], end=clock[0] + end_delta)], done=0, cash=0, xp=0)))


def test_car_in_active_route_blocks_travel(env):
    app, clock = env; c = register(app, 'lock1'); create(c, 1, 'Lock1')
    fleet(app, 'Lock1', clock, 15 * 60000)
    r = go(c, 1, 3, 'car')
    assert r.status_code == 409, r.text
    assert 'Auto zajęte w trasie NPC do' in r.text and '15 min' in r.text and 'UTC' in r.text


def test_other_active_car_can_travel(env):
    app, clock = env; c = register(app, 'lock2'); create(c, 1, 'Lock2')
    fleet(app, 'Lock2', clock, 15 * 60000)
    patch(app, 'Lock2', dict(vehicle=dict(id='dostawczak', wear=0)))
    assert go(c, 1, 3, 'car').status_code == 200


def test_finished_unclaimed_route_does_not_block(env):
    app, clock = env; c = register(app, 'lock3'); create(c, 1, 'Lock3')
    fleet(app, 'Lock3', clock, -1)
    assert go(c, 1, 3, 'car').status_code == 200


def test_bus_always_allowed(env):
    app, clock = env; c = register(app, 'lock4'); create(c, 1, 'Lock4')
    fleet(app, 'Lock4', clock, 15 * 60000)
    assert go(c, 1, 3, 'bus').status_code == 200


def test_dispatch_retired_even_for_free_car(env):
    # 2.4e: wysyłka tras wycofana — blokada „auto wiezie gracza” nie jest już potrzebna
    app, clock = env; c = register(app, 'lock5'); create(c, 1, 'Lock5')
    patch(app, 'Lock5', dict(cash=5000, garage=['furgonetka', 'dostawczak'], vehicle=dict(id='furgonetka', wear=0)))
    r = action(c, 'route_dispatch', 1, route='courier', vehicle='dostawczak')
    assert r.status_code == 409 and 'wycofane' in r.text
