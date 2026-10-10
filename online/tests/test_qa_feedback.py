"""QA live feedback: siłownia natychmiastowa z rosnącą ceną, unikaty z Lochu w Ekwipunku, Rękawice = Broń."""
import uuid

from server import combat, economy as E
from tests.test_gear import W, make, patch, st, env  # noqa: F401


def act(a, **body):
    return a.post(W + '/actions', json=body, headers={'Idempotency-Key': uuid.uuid4().hex})


def test_silownia_natychmiast_i_rosnacy_koszt(env):
    app, clock = env
    a = make(app, 'gymqa', 'GymQA')
    patch(app, 'GymQA', cash=5000, energy=100, stats=[10, 20, 10, 10, 10])
    s0 = st(app, 'GymQA')
    c0 = E.gym_cost(s0, 0); c1 = E.gym_cost(s0, 1)
    assert c1 > c0, 'wyższa statystyka = drożej'
    r = act(a, action='train', stat=0); assert r.status_code == 200, r.text
    s = st(app, 'GymQA')
    assert s['stats'][0] == 11 and s['training'] == [], 'od razu +1, bez kolejki'
    assert s0['cash'] - s['cash'] == c0 and s0['energy'] - s['energy'] == 5
    # następny trening tej samej statystyki jest droższy o 15 $ (przed rabatem Charyzmy)
    assert E.gym_cost(s, 0) > c0
    assert a.get(W + '/state').json()['catalog']['gymCosts'][0] == E.gym_cost(s, 0)


def test_unikat_z_lochu_widoczny_i_zakladany(env):
    app, clock = env
    a = make(app, 'uniqqa', 'UniqQA')
    s = st(app, 'UniqQA')
    patch(app, 'UniqQA', inventory=list(s['inventory']) + ['rekawice-lochu', 'helm-lochu'])
    g = a.get(W + '/gear').json()
    ids = {u['id']: u for u in g['uniques']}
    assert set(ids) == {'rekawice-lochu', 'helm-lochu'} and ids['helm-lochu']['slot'] == 'head'
    assert ids['rekawice-lochu']['dmgMin'] == combat.WEAPON[2][0]
    r = a.post(W + '/gear/equip', json={'item': 'rekawice-lochu'}); assert r.status_code == 200, r.text
    assert st(app, 'UniqQA')['equipped']['gloves'] == 'rekawice-lochu'
    assert combat.loadout(st(app, 'UniqQA')['equipped'])['weapon'] == list(combat.WEAPON[2][:2])
    assert a.post(W + '/gear/equip', json={'item': 'korona-wladcy'}).status_code == 409, 'nieposiadany unikat'


def test_rekawice_maja_obrazenia_w_api(env):
    app, clock = env
    a = make(app, 'dmgqa', 'DmgQA')
    patch(app, 'DmgQA', backpack=['uliczny-gloves', 'uliczny-head'])
    g = a.get(W + '/gear').json()
    gl = next(i for i in g['backpack'] if i['id'] == 'uliczny-gloves')
    hd = next(i for i in g['backpack'] if i['id'] == 'uliczny-head')
    assert (gl['dmgMin'], gl['dmgMax']) == combat.WEAPON[1][:2] and 'dmgMin' not in hd
    assert g['fists'] == dict(dmgMin=15, dmgMax=25)
