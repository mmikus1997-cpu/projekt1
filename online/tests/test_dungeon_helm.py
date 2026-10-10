"""GDD v3.1 1.9: Hełm Lochu wypada na 9. piętrze (Strażnik Bramy), raz na postać."""
import json
import uuid
from server import dungeon as D, economy as E
from tests.test_dungeon import env, register, create, _ready, fight, set_progress  # noqa: F401


def test_every_dungeon_item_has_a_floor():
    assert set(D.LOOT_FLOORS.values()) == {i['id'] for i in E.DUNGEON_ITEMS}
    assert D.LOOT_FLOORS[9] == 'helm-lochu' and D.FLOORS[8]['name'] == 'Strażnik Bramy'


def test_floor9_drops_helm_once_and_equips(env):
    app, clock = env
    a = register(app, 'helmowy'); create(a, 'Helmowy'); _ready(app, 'Helmowy')
    a.post('/api/worlds/2/location', json={'location': 'brama-lochow'})
    with app.state.db.tx() as c:
        s = json.loads(c.execute("SELECT state_json FROM characters WHERE nickname='Helmowy'").fetchone()[0])
        s['stats'] = [60, 60, 60, 60, 60]
        c.execute("UPDATE characters SET state_json=? WHERE nickname='Helmowy'", (json.dumps(s),))
    set_progress(app, 80, 'Helmowy')
    r = fight(a); assert r.status_code == 200, r.text
    assert r.json()['floor'] == 9 and r.json()['loot'] == dict(id='helm-lochu', name='Hełm Lochu')
    set_progress(app, 80, 'Helmowy')
    assert fight(a).json()['loot'] is None, 'unikat nie wypada drugi raz'
    r = a.post('/api/worlds/2/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': 'equip', 'item': 'helm-lochu'})
    assert r.status_code == 200, r.text
