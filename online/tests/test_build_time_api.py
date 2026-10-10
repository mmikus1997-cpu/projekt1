"""Końcowa regresja budowy: trwałość zapisu, ponowienia i dokładna granica czasu."""
import uuid
from server.app import create_app
from fastapi.testclient import TestClient
from tests.test_buildings import env, register, create, action, state  # noqa: F401


def test_pending_build_survives_new_app_instance(env):
    app, clock, path = env
    c = register(app, 'build_persist')
    create(c)
    r = action(c, 'upgrade_building', building='residence')
    assert r.status_code == 200
    before = state(c)
    end = before['state']['construction']['endsAt']
    assert before['state']['buildings']['residence'] == 1
    restarted = create_app(app.state.db.path, lambda: clock[0], path / 'setup.txt')
    fresh = TestClient(restarted)
    login = fresh.post('/api/auth/login', json={'username': 'build_persist', 'password': 'test-password-long-123'})
    assert login.status_code == 200
    pending = state(fresh)
    assert pending['state']['construction']['endsAt'] == end
    assert pending['state']['buildings']['residence'] == 1
    clock[0] = end - 1
    assert state(fresh)['state']['buildings']['residence'] == 1
    clock[0] = end
    done = state(fresh)['state']
    assert done['buildings']['residence'] == 2
    assert not done.get('construction')


def test_repeated_request_does_not_charge_twice(env):
    app, clock, path = env
    c = register(app, 'build_repeat')
    create(c)
    key = uuid.uuid4().hex
    args = {'headers': {'Idempotency-Key': key}, 'json': {'action': 'upgrade_building', 'building': 'residence'}}
    first = c.post('/api/worlds/2/actions', **args)
    assert first.status_code == 200
    saved = state(c)['state']
    second = c.post('/api/worlds/2/actions', **args)
    assert second.status_code == 200
    after = state(c)['state']
    assert after['cash'] == saved['cash']
    assert after['construction'] == saved['construction']
    assert after['buildings']['residence'] == 1


def test_rejected_second_build_preserves_cash_and_target(env):
    app, clock, path = env
    c = register(app, 'build_blocked')
    create(c)
    assert action(c, 'upgrade_building', building='residence').status_code == 200
    before = state(c)['state']
    denied = action(c, 'upgrade_building', building='garage')
    assert denied.status_code == 409
    after = state(c)['state']
    assert after['cash'] == before['cash']
    assert after['construction'] == before['construction']
    assert after['buildings']['garage'] == 1
