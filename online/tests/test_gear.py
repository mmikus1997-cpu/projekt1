"""7.1–7.6 GDD v3.1: 8 slotów + plecak, 9 setów T1–T4 (skalowanie, komplet +30%, tryby T4), sklep z rotacją 6 h,
crafting 3→1, kupony (max 100), i18n i przelicznik walut."""
import json
import uuid
from server import gear as G, economy as E
from tests.test_dungeon import env, register, create  # noqa: F401

W = '/api/worlds/2'


def patch(app, nick, **kw):
    with app.state.db.tx() as c:
        s = json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?', (nick,)).fetchone()[0])
        s.update(kw)
        c.execute('UPDATE characters SET state_json=? WHERE nickname=?', (json.dumps(s), nick))


def st(app, nick):
    with app.state.db.read() as c:
        return json.loads(c.execute('SELECT state_json FROM characters WHERE nickname=?', (nick,)).fetchone()[0])


def make(app, user='gear7', nick='Gear7'):
    a = register(app, user); create(a, nick); return a


def test_catalog_nine_sets_eight_slots():
    assert len(G.SETS) == 9 and len(G.ITEMS) == 72
    assert [sum(1 for x in G.SETS if x['tier'] == t) for t in (1, 2, 3, 4)] == [3, 2, 2, 2]
    assert G.SLOTS == ('gloves', 'shoes', 'pants', 'belt', 'shirt', 'head', 'amulet', 'ring')
    s = dict(xp=0, stats=[10] * 5, cls='bokser')
    assert G.piece_bonus(G.BY_ID['uliczny-head'], s, E) == [3, 0, 0, 0, 0]
    assert G.piece_bonus(G.BY_ID['portowy-ring'], s, E) == [4, 0, 0, 3, 0]
    assert G.piece_bonus(G.BY_ID['mistrzowski-ring'], dict(s, cls='obronca'), E) == [0, 7, 0, 0, 0], 'T3 → statystyka klasowa'
    assert G.piece_bonus(G.BY_ID['legendarny-ring'], s, E, 'A') == [5] * 5
    assert G.piece_bonus(G.BY_ID['legendarny-ring'], dict(s, cls='szybki'), E, 'B') == [0, 0, 12, 0, 0]
    assert G.piece_bonus(G.BY_ID['uliczny-head'], dict(s, xp=32500), E) == [4.5, 0, 0, 0, 0], 'lvl 26 → ×1.5'


def test_equip_full_set_bonus_and_legacy_slots(env):
    app, clock = env
    a = make(app)
    eff0 = E.effective(st(app, 'Gear7'))
    patch(app, 'Gear7', backpack=['uliczny-head'], equipped=dict(st(app, 'Gear7')['equipped'], helmet='basic-helmet'))
    r = a.post(W + '/gear/equip', json={'item': 'uliczny-head'}); assert r.status_code == 200, r.text
    s = st(app, 'Gear7')
    assert s['equipped']['head'] == 'uliczny-head' and 'helmet' not in s['equipped'] and s['backpack'] == []
    assert E.effective(s)[0] == eff0[0] + 3
    patch(app, 'Gear7', backpack=[f'uliczny-{sl}' for sl in G.SLOTS if sl != 'head'])
    for sl in G.SLOTS:
        if sl != 'head':
            assert a.post(W + '/gear/equip', json={'item': f'uliczny-{sl}'}).status_code == 200
    g = a.get(W + '/gear').json()
    assert g['fullSets'] == ['uliczny'] and g['gearBonus'][0] == round(8 * 3 * 1.3)
    # zdjęcie części łamie komplet
    assert a.post(W + '/gear/unequip', json={'slot': 'ring'}).status_code == 200
    g = a.get(W + '/gear').json(); assert g['fullSets'] == [] and g['gearBonus'][0] == 21
    assert a.post(W + '/gear/equip', json={'item': 'cienia-ring'}).json()['detail'] == 'Nie masz tego przedmiotu w plecaku.'


def test_tier4_mode_and_level_gate(env):
    app, clock = env
    a = make(app)
    patch(app, 'Gear7', backpack=['cesarski-gloves'])
    assert 'Wymagany poziom 15' in a.post(W + '/gear/equip', json={'item': 'cesarski-gloves', 'mode': 'B'}).json()['detail']
    patch(app, 'Gear7', xp=10500)
    assert a.post(W + '/gear/equip', json={'item': 'cesarski-gloves'}).status_code == 409, 'T4 wymaga wyboru trybu'
    s0 = E.effective(st(app, 'Gear7'))
    assert a.post(W + '/gear/equip', json={'item': 'cesarski-gloves', 'mode': 'B'}).status_code == 200
    s = st(app, 'Gear7'); assert s['gearModes']['gloves'] == 'B'
    assert E.effective(s)[0] - s0[0] == round(12 * 1.28), 'Bokser: tryb B → Siła, ×(1+0.02·14)'


def test_backpack_capacity_and_unlocks(env):
    app, clock = env
    a = make(app)
    g = a.get(W + '/gear').json(); assert g['capacity'] == 20 and g['maxCapacity'] == 30
    assert a.post(W + '/gear/bag/unlock', json={'currency': 'diamonds'}).status_code == 409, 'najpierw $'
    assert 'Wymagany poziom 5' in a.post(W + '/gear/bag/unlock', json={'currency': 'cash'}).json()['detail']
    patch(app, 'Gear7', xp=32500, cash=100000, diamonds=2000)
    costs = []
    for _ in range(5):
        c0 = st(app, 'Gear7')['cash']; assert a.post(W + '/gear/bag/unlock', json={'currency': 'cash'}).status_code == 200
        costs.append(c0 - st(app, 'Gear7')['cash'])
    assert costs == [500, 1500, 5000, 15000, 50000]
    assert a.post(W + '/gear/bag/unlock', json={'currency': 'cash'}).status_code == 409
    for _ in range(5):
        assert a.post(W + '/gear/bag/unlock', json={'currency': 'diamonds'}).status_code == 200
    s = st(app, 'Gear7'); assert s['diamonds'] == 2000 - 1550 and G.capacity(s) == 30
    assert a.post(W + '/gear/bag/unlock', json={'currency': 'diamonds'}).status_code == 409


def test_shop_rotation_buy_sold_full_and_coupons(env, monkeypatch):
    app, clock = env
    monkeypatch.setattr(G, 'COUPON_CHANCE', 0)  # ten test sprawdza same przedmioty
    monkeypatch.setattr(G, 'BAG_START', 5)      # mały plecak, by sprawdzić „Plecak jest pełny”
    a = make(app)
    patch(app, 'Gear7', cash=50000, diamonds=100)
    sh = a.get(W + '/gear/shop').json()
    assert len(sh['items']) == 12 and [i['zone'] for i in sh['items']].count(1) == 8
    assert all(i['slot'] in G.ZONE_ARMOR for i in sh['items'] if i['zone'] == 1) and all(i['tier'] == 1 for i in sh['items']), 'lvl 1 → tylko T1'
    assert a.get(W + '/gear/shop').json()['items'] == sh['items'], 'oferta stała w oknie'
    r = a.post(W + '/gear/shop/buy', json={'offer': 0}); assert r.status_code == 200, r.text
    s = st(app, 'Gear7'); assert s['cash'] == 50000 - 400 and s['backpack'] == [sh['items'][0]['id']]
    assert a.post(W + '/gear/shop/buy', json={'offer': 0}).json()['detail'].startswith('Ta oferta jest już sprzedana')
    for n in range(1, 5):
        assert a.post(W + '/gear/shop/buy', json={'offer': n}).status_code == 200
    assert a.post(W + '/gear/shop/buy', json={'offer': 5}).json()['detail'] == 'Plecak jest pełny.'
    clock[0] = (clock[0] // G.ROTATION_MS + 1) * G.ROTATION_MS + 1000
    new = a.get(W + '/gear/shop').json()
    assert new['items'] != sh['items'] and not any(i['sold'] for i in new['items']), 'reset co 6 h'
    # kupony: stałe produkty, za $ albo 💎, bez losowości
    assert a.post(W + '/gear/shop/buy', json={'coupon': 'xp'}).status_code == 200
    assert a.post(W + '/gear/shop/buy', json={'coupon': 'instant', 'pay': 'diamonds'}).status_code == 200
    s = st(app, 'Gear7'); assert s['coupons'] == dict(xp=1, instant=1) and s['diamonds'] == 92
    patch(app, 'Gear7', coupons=dict(xp=100))
    assert a.post(W + '/gear/shop/buy', json={'coupon': 'xp'}).json()['detail'].startswith('Masz już maksymalnie 100')


def test_mixed_price_for_blue(env):
    app, clock = env
    a = make(app)
    patch(app, 'Gear7', xp=4500, cash=50000, diamonds=40)
    blue = None
    for _ in range(30):   # rotacja co 6 h aż pojawi się niebieski
        blue = next((i for i in a.get(W + '/gear/shop').json()['items'] if i['tier'] == 3), None)
        if blue:
            break
        clock[0] += G.ROTATION_MS
    assert blue, 'w 30 rotacjach musi trafić się T3'
    if True:
        assert blue['alt'] == dict(cash=3000, diamonds=15)
        assert a.post(W + '/gear/shop/buy', json={'offer': blue['offer'], 'pay': 'mixed'}).status_code == 200
        s = st(app, 'Gear7'); assert (s['cash'], s['diamonds']) == (47000, 25)


def test_craft_three_to_one(env):
    app, clock = env
    a = make(app)
    patch(app, 'Gear7', cash=20000, diamonds=10, backpack=['uliczny-head', 'akademicki-belt', 'sprinterski-ring', 'portowy-head', 'mistrzowski-head', 'gwardyjski-ring', 'mistrzowski-belt'])
    assert a.post(W + '/gear/craft', json={'items': ['uliczny-head', 'akademicki-belt', 'portowy-head']}).json()['detail'].startswith('Wszystkie 3')
    r = a.post(W + '/gear/craft', json={'items': ['uliczny-head', 'akademicki-belt', 'sprinterski-ring']}); assert r.status_code == 200, r.text
    assert G.BY_ID[r.json()['result']['id']]['tier'] == 2
    s = st(app, 'Gear7'); assert s['cash'] == 19500 and len(s['backpack']) == 5
    assert a.post(W + '/gear/craft', json={'items': ['mistrzowski-head', 'gwardyjski-ring', 'mistrzowski-belt']}).json()['detail'] == 'Za mało diamentów.'
    patch(app, 'Gear7', diamonds=20)
    r = a.post(W + '/gear/craft', json={'items': ['mistrzowski-head', 'gwardyjski-ring', 'mistrzowski-belt']}); assert r.status_code == 200
    s = st(app, 'Gear7'); assert G.BY_ID[r.json()['result']['id']]['tier'] == 4 and s['diamonds'] == 0 and s['cash'] == 9500


def test_coupons_xp_contract_instant(env):
    app, clock = env
    a = make(app); b = make(app, 'ctrl7', 'Ctrl7')   # b = postać kontrolna bez kuponów
    act = lambda cl, **p: cl.post(W + '/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json=p)
    patch(app, 'Gear7', coupons=dict(xp=1, instant=2, contract=1), residence='studio-flat')
    r = act(a, action='home_train', stat=0); assert r.status_code == 200, r.text
    assert a.post(W + '/gear/coupon/use', json={'type': 'instant', 'task': 'training'}).status_code == 200
    tr = st(app, 'Gear7')['training'][0]; assert tr['end'] <= clock[0]
    assert act(a, action='claim_training', task_id=tr['id']).status_code == 200, 'pominięty timer → od razu do odebrania'
    assert a.post(W + '/gear/coupon/use', json={'type': 'xp'}).status_code == 200
    assert st(app, 'Gear7')['xpBoostUntil'] == clock[0] + 3600 * 1000
    assert a.post(W + '/gear/coupon/use', json={'type': 'contract'}).status_code == 200
    assert a.post(W + '/gear/coupon/use', json={'type': 'contract'}).json()['detail'] == 'Nie masz takiego kuponu.'
    with app.state.db.tx() as c:
        c.execute("UPDATE characters SET current_district=3 WHERE nickname IN ('Gear7','Ctrl7')")   # zlecenie 'inventory' czeka w Centrum
    gains = {}
    for cl, nick in ((a, 'Gear7'), (b, 'Ctrl7')):
        r = act(cl, action='contract', contract='inventory'); assert r.status_code == 200, r.text
        t = st(app, nick)['contracts'][-1]
        clock[0] = max(clock[0], t['end']) + 1000
        x0 = st(app, nick)['xp']; r = act(cl, action='claim_contract', task_id=t['id']); assert r.status_code == 200, r.text
        gains[nick] = st(app, nick)['xp'] - x0
    base = gains['Ctrl7']
    assert gains['Gear7'] == 2 * (base + round(base * 0.10)), gains
    s = st(app, 'Gear7'); assert 'contractBoost' not in s and s['coupons'] == dict(xp=0, instant=1, contract=0)


def test_i18n_language_and_currency(env):
    app, clock = env
    a = make(app)
    assert set(G.strings('pl')) == set(G.strings('en')) == set(G.strings('de')) == set(G.strings('fr'))
    r = a.post(W + '/gear/equip', json={'item': 'xxx'}, headers={'Accept-Language': 'de-DE,de;q=0.9'})
    assert r.json()['detail'] == 'Unbekannter Gegenstand.'
    assert a.post(W + '/gear/equip', json={'item': 'xxx'}, headers={'Accept-Language': 'es,fr;q=0.8'}).json()['detail'] == 'Objet inconnu.'
    assert a.post(W + '/gear/equip', json={'item': 'xxx'}).json()['detail'] == 'Nieznany przedmiot.'
    assert a.post('/api/account/language', json={'language': 'en'}).status_code == 200
    assert a.post(W + '/gear/equip', json={'item': 'xxx'}, headers={'Accept-Language': 'de'}).json()['detail'] == 'Unknown item.', 'konto ma pierwszeństwo'
    assert a.get(W + '/gear').json()['slots'][0]['label'] == 'Gloves'
    assert a.get('/api/i18n/fr').json()['strings']['slot.ring'] == 'Bague' and a.get('/api/i18n/xx').status_code == 404
    p = a.get('/api/shop/prices?currency=EUR').json()
    vip = next(x for x in p['prices'] if x['sku'] == 'vip30')
    assert p['displayOnly'] and vip['cents'] == round(1999 * 0.23) and vip['display'].endswith('€')
    assert a.get('/api/shop/prices?currency=JPY').status_code == 422


def test_legacy_shop_closed(env):
    app, clock = env
    a = make(app)
    r = a.post(W + '/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': 'buy', 'item': 'urban-gloves'})
    assert r.status_code == 409 and 'Sali Klubowej' in r.json()['detail']


def test_shop_coupons_in_rotation_and_paid_refresh(env, monkeypatch):
    app, clock = env
    a = make(app)
    patch(app, 'Gear7', cash=10000, diamonds=0)
    monkeypatch.setattr(G, 'COUPON_CHANCE', 1)  # wszystkie miejsca = kupony
    sh = a.get(W + '/gear/shop').json()
    assert len(sh['items']) == 12 and all(i['kind'] == 'coupon' for i in sh['items']) and sh['refreshCost'] == 50
    c0 = sh['items'][0]
    r = a.post(W + '/gear/shop/buy', json={'offer': 0}); assert r.status_code == 200, r.text
    s = st(app, 'Gear7'); assert s['coupons'][c0['coupon']] == 1 and s['cash'] == 10000 - c0['price']['cash']
    assert a.post(W + '/gear/shop/buy', json={'offer': 0}).json()['detail'].startswith('Ta oferta jest już sprzedana')
    monkeypatch.setattr(G, 'COUPON_CHANCE', 0.2)
    before = a.get(W + '/gear/shop').json()
    cash = st(app, 'Gear7')['cash']
    r = a.post(W + '/gear/shop/refresh', json={}); assert r.status_code == 200, r.text
    new = r.json()['shop']
    assert st(app, 'Gear7')['cash'] == cash - 50 and new['refreshes'] == 1 and not any(i['sold'] for i in new['items'])
    assert new['items'] != before['items'], 'odświeżenie losuje nową ofertę'
    assert a.get(W + '/gear/shop').json()['items'] == new['items'], 'nowa oferta stała do kolejnego odświeżenia'
    patch(app, 'Gear7', cash=10)
    assert a.post(W + '/gear/shop/refresh', json={}).status_code == 409


def test_stat_breakdown_sums_to_effective(env):
    app, clock = env
    a = make(app)
    patch(app, 'Gear7', stats=[12, 10, 10, 10, 10], equipped={'gloves': 'uliczny-gloves'})
    g = a.get(W + '/gear').json()
    sb = g['statBreakdown']
    assert len(sb) == 5 and sb[0]['name'] == 'Siła' and sb[0]['base'] == 12
    for r in sb:
        assert abs(r['base'] + r['gear'] + r['unique'] + r['other'] - r['total']) < 0.11
    assert sb[0]['gear'] == g['gearBonus'][0]


def test_sell_random_price_in_range(env):
    app, clock = env
    a = make(app)
    patch(app, 'Gear7', cash=0, backpack=['uliczny-head', 'uliczny-head'], equipped={})
    g = a.get(W + '/gear').json()
    rng = g['backpack'][0]['sell']; assert 0 < rng['min'] < rng['max']
    r = a.post(W + '/gear/sell', json={'item': 'uliczny-head'}); assert r.status_code == 200, r.text
    p = r.json()['price']; assert rng['min'] <= p <= rng['max']
    s = st(app, 'Gear7'); assert s['cash'] == p and s['backpack'] == ['uliczny-head']
    assert a.post(W + '/gear/sell', json={'item': 'mistrzowski-head'}).status_code == 409
    # wyższy tier = wyższe widełki
    assert G.sell_range(4, [7] * 5)[0] > G.sell_range(1, [3, 0, 0, 0, 0])[1]
