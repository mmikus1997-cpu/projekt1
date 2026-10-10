"""6.1–6.4 GDD v3.1: Loch Normal 10×10, Hard 2×10, Nightmare 3×10 — bramki, koszty, dropy, kosmetyka, zwierzęta premium, historia."""
import json
from server import dungeon as D, economy as E, combat as C
from tests.test_dungeon import env, register, create  # noqa: F401


def strong(app, nick, xp, energy=240, stats=300):
    with app.state.db.tx() as c:
        s = json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?', (nick,)).fetchone()[0])
        s['xp'] = xp; s['energy'] = energy; s['stats'] = [stats] * 5
        c.execute('UPDATE characters SET state_json=?,current_location=? WHERE nickname=?', (json.dumps(s), 'brama-lochow', nick))


def state(app, nick):
    with app.state.db.read() as c:
        r = c.execute('SELECT * FROM characters WHERE nickname=?', (nick,)).fetchone()
    return dict(r), json.loads(r['state_json'])


def go(c, mode='normal'):
    return c.post('/api/worlds/2/dungeon/floor', json={'mode': mode})


def set_best(app, nick, mode, floor):
    with app.state.db.tx() as c:
        c.execute(f'UPDATE characters SET {D.MODE_COLUMN[mode]}=? WHERE nickname=?', (floor, nick))


def test_structure_series_and_bosses():
    assert (D.total_floors('normal'), D.total_floors('hard'), D.total_floors('nightmare')) == (100, 20, 30)
    assert [D.MODES[m]['level'] for m in D.MODES] == [3, 7, 15] and [D.MODES[m]['energy'] for m in D.MODES] == [8, 15, 25]
    assert D.npc_for('normal', 1)['name'] == 'Szczur z Kanałów' and D.npc_for('normal', 10)['stats'] == D.FLOORS[9]['stats']
    n = D.npc_for('normal', 23)
    assert n['series'] == 3 and n['pos'] == 3 and n['boss'] and n['theme'] == 'Złomowiska' and n['name'] == 'Herszt Złomowiska'
    assert [D.npc_for('normal', f)['boss'] for f in range(1, 11)] == [False, False, True, False, False, True, False, False, False, True]
    # rosnąca trudność: seria > seria, Hard > wczesny Normal, Nightmare > Hard
    p = lambda m, f: sum(D.npc_for(m, f)['stats'])
    assert p('normal', 20) > p('normal', 10) and p('normal', 100) > p('normal', 90)
    assert p('hard', 10) > p('normal', 30) and p('nightmare', 10) > p('hard', 20)   # ta sama pozycja w serii


def test_level_gates_and_energy(env):
    app, clock = env
    a = register(app, 'loch6'); create(a, 'Loch6')
    strong(app, 'Loch6', xp=400)                       # lvl 3
    assert go(a, 'hard').status_code == 409 and '7. poziomie' in go(a, 'hard').json()['detail']
    e0 = state(app, 'Loch6')[1]['energy']; assert go(a).status_code == 200
    assert e0 - state(app, 'Loch6')[1]['energy'] == 8
    strong(app, 'Loch6', xp=2100)                      # lvl 7
    assert go(a, 'nightmare').status_code == 409
    e0 = state(app, 'Loch6')[1]['energy']; r = go(a, 'hard'); assert r.status_code == 200, r.text
    assert e0 - state(app, 'Loch6')[1]['energy'] == 15
    strong(app, 'Loch6', xp=10500)                     # lvl 15
    e0 = state(app, 'Loch6')[1]['energy']; r = go(a, 'nightmare'); assert r.status_code == 200, r.text
    assert e0 - state(app, 'Loch6')[1]['energy'] == 25
    modes = a.get('/api/worlds/2/state').json()['dungeon']['modes']
    assert modes['hard']['best'] == 1 and modes['nightmare']['best'] == 1 and not modes['nightmare']['locked']


def test_drop_pool_from_gear_sets_boss_higher_tier(env):
    """7.x: pula dropu Normal = sety (8 slotów); serie 1–5 zwykli T1 / boss T2, serie 6–10 zwykli T2 / boss T3."""
    from server import gear as G
    app, clock = env
    a = register(app, 'boss6'); create(a, 'Boss6'); strong(app, 'Boss6', xp=400)
    set_best(app, 'Boss6', 'normal', 12)               # następne: piętro 13 = boss serii 2
    r = go(a); assert r.status_code == 200 and r.json()['cleared'], r.text
    drops = r.json()['drops']; assert len(drops) == 1, 'boss: 100% drop'
    it = G.BY_ID[drops[0]['id']]; assert it['tier'] == 2 and drops[0]['to'] == 'backpack'
    clock[0] += 4 * 60000; strong(app, 'Boss6', xp=400); set_best(app, 'Boss6', 'normal', 52)   # boss serii 6
    d = go(a).json()['drops']; assert G.BY_ID[d[0]['id']]['tier'] == 3
    assert {i['slot'] for i in G.ITEMS} == set(G.SLOTS) and 'accessory' not in G.SLOTS and 'backpack' not in G.SLOTS


def test_regular_drop_rate_and_items_to_backpack(env):
    from server import gear as G
    app, clock = env
    a = register(app, 'farm6'); create(a, 'Farm6')
    got = 0; regular = 0; tiers = set()
    for f in range(11, 101):
        if D.npc_for('normal', f)['boss']:
            continue
        clock[0] += 4 * 60000; strong(app, 'Farm6', xp=400); set_best(app, 'Farm6', 'normal', f - 1)
        r = go(a); assert r.status_code == 200 and r.json()['cleared'], r.text
        regular += 1; got += len(r.json()['drops']); tiers |= {G.BY_ID[x['id']]['tier'] for x in r.json()['drops']}
    assert regular == 63 and 1 <= got <= 16, f'~10% szansy na drop ({got}/{regular})'
    assert tiers <= {1, 2}
    _, s = state(app, 'Farm6')
    assert len(s['backpack']) == got and all(x in G.BY_ID for x in s['backpack']), 'dropy (także duplikaty) lądują w plecaku, bez zamiany na $'


def test_hard_cosmetics_and_nightmare_pets(env):
    app, clock = env
    a = register(app, 'kosm6'); create(a, 'Kosm6')
    for f in (3, 6, 10):
        strong(app, 'Kosm6', xp=2100); set_best(app, 'Kosm6', 'hard', f - 1)
        r = go(a, 'hard'); assert r.status_code == 200 and r.json()['cleared'], r.text
    _, s = state(app, 'Kosm6')
    assert set(s['cosmetics']) == {'npc-outfit-hard-1', 'car-skin-hard-1'} and 'dungeon-hard-1' in s['frames']
    strong(app, 'Kosm6', xp=2100); set_best(app, 'Kosm6', 'hard', 0)
    r = go(a, 'hard'); assert r.json()['cosmetics'] == [] and r.json()['rewards'] == dict(cash=600, xp=105)   # zwykły: tylko $ + XP
    for f in (3, 6, 10):
        strong(app, 'Kosm6', xp=10500); set_best(app, 'Kosm6', 'nightmare', f - 1)
        r = go(a, 'nightmare'); assert r.status_code == 200 and r.json()['cleared'], r.text
    _, s = state(app, 'Kosm6')
    prem = [h for h in s['horses'].values() if h.get('premium')]; dogs = list(s['dogs'].values())
    assert len(prem) == 2 and len(dogs) == 2 and all(d['premium'] and d['gen'] == 1 for d in dogs)
    assert max(h['speed'] for h in prem) > 6, 'konie premium mocniejsze od Czempiona (speed 6)'


def test_history_and_engine(env):
    app, clock = env
    a = register(app, 'hist6'); create(a, 'Hist6'); strong(app, 'Hist6', xp=400)
    r = go(a); assert r.status_code == 200
    rep = r.json()['report']
    assert r.json()['combat_version'] == C.ENGINE_V2
    assert rep['hpStart'][0] == C.hp_v3(300, 3) + rep['loadouts'][0]['hp'], 'Combat 3.0: HP 300 + 6×Cha + 6×Lvl + pancerz'
    assert {'attacker_action', 'defender_reaction', 'result', 'exchanges'} <= set(rep['rounds'][0])
    strong(app, 'Hist6', xp=400, stats=1)              # słaby → porażka też trafia do historii
    assert go(a).json()['cleared'] is False
    h = a.get('/api/worlds/2/dungeon/history').json()
    assert h['stats']['normal'] == dict(best=1, floors=100, attempts=2, wins=1) and h['stats']['hard']['attempts'] == 0
    assert [x['win'] for x in h['runs']] == [False, True]
    full = a.get(f"/api/worlds/2/dungeon/runs/{h['runs'][1]['id']}").json()
    assert full['win'] and full['report']['winner'] == 0 and full['combat_version'] == C.ENGINE_V2
    b = register(app, 'obcy6'); create(b, 'Obcy6')
    assert b.get(f"/api/worlds/2/dungeon/runs/{h['runs'][1]['id']}").status_code == 404
