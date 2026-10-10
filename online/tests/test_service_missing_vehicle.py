"""GDD v3.1 1.2: service_vehicle nie może rzucać StopIteration dla wycofanego modelu."""
from server import economy as E
from tests.test_routes import env, register, create, action, state, set_state, cid_of  # noqa: F401


def test_service_retired_model_unequips_free(env):
    app, clock, _ = env
    c = register(app, 'wycofany')
    create(c)
    set_state(app, cid_of(c), dict(vehicle=dict(id='model-wycofany', wear=100), cash=5000))
    r = action(c, 'service_vehicle')
    assert r.status_code == 200, r.text
    st = state(c)['state']
    assert st['vehicle'] is None and st['cash'] == 5000
    assert 'wycofany z gry' in r.json().get('message', r.text)


def test_service_normal_still_works(env):
    app, clock, _ = env
    c = register(app, 'serwisZwykly')
    create(c)
    g = E.GARAGE[0]
    set_state(app, cid_of(c), dict(vehicle=dict(id=g['id'], wear=100), garage=[g['id']], cash=5000))
    r = action(c, 'service_vehicle')
    assert r.status_code == 200, r.text
    st = state(c)['state']
    assert st['vehicle']['wear'] == 0 and st['cash'] < 5000
    assert action(c, 'service_vehicle').status_code == 409  # wear 0 → nie wymaga serwisu
