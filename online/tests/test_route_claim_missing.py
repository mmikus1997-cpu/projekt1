"""GDD v3.1 1.1: route_claim nie może rzucać StopIteration, gdy trasa zniknęła z katalogu."""
from server import economy as E
from tests.test_routes import env, register, create, action, state, set_state, cid_of  # noqa: F401


def test_claim_missing_route_frees_car_and_pays_rest(env):
    app, clock, _ = env
    c = register(app, 'brakTrasy')
    create(c)
    cid = cid_of(c)
    good = E.NPC_ROUTES[0]
    runs = [dict(route='usunieta-trasa', vehicle='dostawczak', start=clock[0] - 10, end=clock[0] - 1),
            dict(route=good['id'], vehicle='sedan', start=clock[0] - 10, end=clock[0] - 1)]
    set_state(app, cid, dict(npcRoutes=dict(runs=runs, done=0, cash=0, xp=0), garage=['dostawczak', 'sedan']))
    cash0 = state(c)['state']['cash']
    r = action(c, 'route_claim')
    assert r.status_code == 200, r.text
    st = state(c)['state']
    assert st['npcRoutes']['runs'] == []          # oba auta wolne
    assert st['npcRoutes']['done'] == 1           # liczy się tylko istniejąca trasa
    assert st['cash'] > cash0                     # wypłata za istniejącą trasę
    assert 'wycofano z gry' in r.json().get('message', r.text)


def test_claim_only_missing_route_no_crash(env):
    app, clock, _ = env
    c = register(app, 'tylkoBrak')
    create(c)
    cid = cid_of(c)
    set_state(app, cid, dict(npcRoutes=dict(runs=[dict(route='nie-ma', vehicle='dostawczak', start=0, end=clock[0] - 1)], done=0, cash=0, xp=0)))
    cash0 = state(c)['state']['cash']
    r = action(c, 'route_claim')
    assert r.status_code == 200, r.text
    st = state(c)['state']
    assert st['npcRoutes']['runs'] == [] and st['cash'] == cash0
    assert any('nie istnieje już w katalogu' in str(h) for h in st['history'])
