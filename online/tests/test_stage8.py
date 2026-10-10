"""Etap 8 GDD v3.1: 8.1 staż 7–1000 dni, 8.2 capy PvE, 8.3 inwestycje >55% + federacje + NPC +5%."""
import json
import sqlite3
from server import economy as E, longplay as LP
from tests import test_territory as TT
from tests import test_npc_shift as NS

DAY = 86400000


# ---------- 8.1 ----------
def test_staz_table_matches_gdd():
    assert [(k, v['days']) for k, v in LP.STAZ.items()] == [('staz_7', 7), ('staz_14', 14), ('staz_30', 30), ('staz_90', 90),
                                                           ('staz_180', 180), ('staz_365', 365), ('staz_1000', 1000)]
    assert [LP.STAZ[k].get('dia', 0) for k in LP.STAZ] == [50, 70, 100, 300, 500, 1000, 0]
    assert LP.STAZ['staz_7']['income'] == 10 and LP.STAZ['staz_1000']['income'] == 5


def test_staz_rewards_granted_once_across_days(tmp_path):
    clock = [1780000000000]
    from server.app import create_app
    db = tmp_path / 'g.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 's.txt')
    c = NS.player(app, db, 'stazysta')
    st = lambda: json.loads(sqlite3.connect(db).execute('SELECT state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0])
    c.get('/api/worlds/2/state')
    with sqlite3.connect(db) as x:   # przeskok licznika: 999 dni aktywności (dni nie muszą być kolejne)
        x.execute('UPDATE longplay_milestones SET active_days=999')
    clock[0] += DAY
    r = c.get('/api/worlds/2/state'); assert r.status_code == 200, r.text
    s = st()
    assert s['diamonds'] == 50 + 70 + 100 + 300 + 500 + 1000
    assert s['seniority'] == 15 and abs(E.prestige_mult(s) - 1.15) < 1e-9, '+10% (7 dni) + 5% (1000 dni) dochodu na stałe'
    assert s['buildings']['residence'] >= 2 and s['buildings']['nightclub'] >= 1 and s['buildings']['cafe'] >= 1
    assert 'kennel-staz-30' in s['dogs'] and 'stable-staz-30' in s['horses']
    assert {'outfit-legenda', 'pomnik-ikona'} <= set(s['cosmetics']) and 'magnat' in s['frames'] and s['nickColor'] == '#d4af37'
    assert s['perks'] == ['ankiety', 'discord'] and s['monument']['district'] >= 1
    assert 'mistrz' in s['garage']
    with sqlite3.connect(db) as x:
        titles = [r[0] for r in x.execute('SELECT label FROM character_titles')]
    assert {'🎖️ Debiutant', '📚 Praktykant', '🏅 Weteran', '👑 Legenda', '💎 Magnat', '🌟 Ikona', '🏛️ Założyciel'} <= set(titles)
    m = c.get('/api/worlds/2/milestones').json()
    assert all(x['claimed'] for x in m['milestones']) and next(x for x in m['milestones'] if x['code'] == 'staz_365')['diamonds'] == 1000
    assert c.get('/api/worlds/2/monuments').json()['monuments'][0]['nickname'] == 'Stazysta'
    clock[0] += DAY; c.get('/api/worlds/2/state')
    assert st()['diamonds'] == 2020, 'nagrody jednorazowe'


# ---------- 8.2 ----------
def test_pve_caps_saturate_at_30():
    s = E.new(0); s['stats'] = [30, 30, 30, 30, 30]
    assert [E.pve_pct(s, i) for i in range(5)] == [10, 15, 10, 15, 10]
    s['stats'] = [90, 90, 90, 90, 90]
    assert [E.pve_pct(s, i) for i in range(5)] == [10, 15, 10, 15, 10], 'powyżej 30 pkt — tylko PvP'
    s['stats'] = [15, 15, 15, 15, 15]
    assert [E.pve_pct(s, i) for i in range(5)] == [5, 7.5, 5, 7.5, 5], 'liniowo: cap × stat/30'
    s['stats'] = [0] * 5
    assert [E.pve_pct(s, i) for i in range(5)] == [0] * 5
    assert E.stat_pct(dict(s, stats=[200] * 5), 0, 2, 40) == 10, 'stare wywołania nie przekroczą capu GDD'


# ---------- 8.3 ----------
def _orgs(app):
    a = TT.register(app, 'alfa8', nickname='Alfa8'); TT.make_org(a, 'ALF')
    b = TT.register(app, 'beta8', nickname='Beta8'); TT.make_org(b, 'BET')
    g = TT.register(app, 'gamma8', nickname='Gamma8'); TT.make_org(g, 'GAM')
    with app.state.db.tx() as x:
        x.execute('UPDATE organizations SET fund=100000')
    return a, b, g


def inv(c, amount, district='Portowe'):
    return c.post('/api/worlds/1/organizations/invest', json={'district': district, 'amount': amount})


def holder(c):
    return TT.port(TT.comm(c)['influence'])['holderSince'], TT.comm(c)['myHeld']


def test_no_invest_cap_and_55_percent_threshold(tmp_path):
    clock = [1780000000000]
    from server.app import create_app
    app = create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    a, b, g = _orgs(app)
    for c in (a,):
        with app.state.db.tx() as x:
            x.execute("UPDATE organizations SET fund=100000 WHERE tag='ALF'")
    for _ in range(5):
        assert inv(a, 5000).status_code == 200
    assert TT.port(TT.comm(a)['influence'])['myTotal'] == 25000, 'bez limitu 20 000 $'
    assert inv(b, 5000).status_code == 200 and inv(b, 5000).status_code == 200 and inv(b, 5000).status_code == 200
    # ALF 25 000 / BET 15 000 → 62,5% → ALF trzyma
    assert holder(a)[1] == ['Portowe']
    assert inv(b, 5000).status_code == 200      # 25 000 / 20 000 → 55,6% → nadal ALF
    assert holder(a)[1] == ['Portowe']
    assert inv(g, 1000).status_code == 200      # 25 000 / 46 000 → 54,3% → neutralna
    assert holder(a) == (None, []) and holder(b)[1] == []


def test_federation_sums_shares_and_npc_bonus(tmp_path):
    clock = [1780000000000]
    from server.app import create_app
    app = create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    a, b, g = _orgs(app)
    with app.state.db.tx() as x:
        x.execute("UPDATE organizations SET fund=100000")
    for c, n in ((a, 4), (b, 3), (g, 3)):
        for _ in range(n):
            assert inv(c, 5000).status_code == 200
    assert holder(a) == (None, []), '40/30/30 — nikt >55%'
    r = a.post('/api/worlds/1/federations', json={'name': 'Pakt Portowy'}); assert r.status_code == 200, r.text
    assert a.post('/api/worlds/1/federations/invite', json={'tag': 'BET'}).status_code == 200
    assert b.post('/api/worlds/1/federations/invite', json={'tag': 'GAM'}).status_code == 403, 'zaprasza lider federacji'
    fid = b.get('/api/worlds/1/federations').json()['invites'][0]['id']
    r = b.post(f'/api/worlds/1/federations/{fid}/accept', json={}); assert r.status_code == 200, r.text
    assert len(r.json()['federation']['members']) == 2
    assert holder(a)[1] == ['Portowe'], 'federacja ALF+BET = 70% → kontrola'
    with app.state.db.read() as x:
        cid_b = x.execute("SELECT id FROM characters WHERE nickname='Beta8'").fetchone()[0]
        cid_g = x.execute("SELECT id FROM characters WHERE nickname='Gamma8'").fetchone()[0]
        assert E.TERRITORY_HOOK[0](x, cid_b, 'Portowe') is True, 'członek federacji korzysta z kontroli'
        assert E.TERRITORY_HOOK[0](x, cid_g, 'Portowe') is False
    assert b.post('/api/worlds/1/federations/leave', json={}).status_code == 200
    assert holder(a) == (None, []), 'wyjście z federacji przelicza kontrolę'


def test_npc_shift_bonus_in_controlled_district(tmp_path, monkeypatch):
    clock = [NS.T0]
    from server.app import create_app
    db = tmp_path / 'shift.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 's.txt')
    c = NS.player(app, db, 'terytor')
    monkeypatch.setattr(E, 'TERRITORY_HOOK', [lambda cx, cid, d: d == 'Centrum'])   # minimarket: dzielnica 3 = Centrum
    nid = NS.hire(c, db); c0 = NS.cash(db)
    assert NS.post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=4)).status_code == 200
    clock[0] += 4 * NS.H + 2 * NS.M
    c.get('/api/worlds/2/npcs')
    net = round((4 - 2 / 60) * 50 * 1.05 * NS.EV - 40)
    assert abs(NS.cash(db) - (c0 + round(net * 1.05))) <= 1, '+5% $ z pracy NPC w dzielnicy sojuszu'


# ---------- 8.4 ----------
from server import battlepass as BP  # noqa: E402


def test_bp_calendar_month_and_rotation():
    t = 1790812800000                                    # 2026-10-01 00:00 UTC
    assert BP.season_of(t) == '2026-10' and BP.season_of(t - 1) == '2026-09'
    assert BP.season_end(t) == 1793491200000             # 2026-11-01 00:00 UTC
    assert BP.season_end(1798761600000 - 1000) == 1798761600000, 'grudzień → 1 stycznia'
    assert len(BP.THEMES) == 12 and len(set(BP.THEMES)) == 12
    a, b = BP.premium_reward(20, '2026-10'), BP.premium_reward(20, '2027-10')
    assert a['kind'] == 'dog' and a['id'] != b['id'], 'unikaty z kluczem sezonu — nie powtarzają się'
    kinds = {BP.premium_reward(lv, '2026-10')['kind'] for lv in (5, 10, 15, 20, 25, 30)}
    assert kinds == {'frame', 'cosmetic', 'dog', 'horse'}


def test_bp_xp_sources_claims_and_premium(tmp_path):
    clock = [NS.T0]
    from server.app import create_app
    db = tmp_path / 'bp.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 's.txt')
    c = NS.player(app, db, 'przepustka')
    st = lambda: json.loads(sqlite3.connect(db).execute('SELECT state_json FROM characters ORDER BY id DESC LIMIT 1').fetchone()[0])
    g = c.get('/api/worlds/2/battlepass').json()
    assert g['level'] == 0 and g['levels'] == 30 and g['price'] == dict(diamonds=400, pln='29,99 zł', plnEnabled=False)
    # XP z pracy NPC (prawdziwa zmiana)
    nid = NS.hire(c, db)
    assert NS.post(c, f'npcs/{nid}/dispatch', dict(service_id='minimarket', hours=2)).status_code == 200
    clock[0] += 2 * NS.H + 2 * NS.M; c.get('/api/worlds/2/npcs')
    assert c.get('/api/worlds/2/battlepass').json()['xp'] == BP.XP['npc']
    assert c.post('/api/worlds/2/battlepass/claim', json={'level': 1, 'track': 'free'}).status_code == 409, 'poziom 1 jeszcze nie osiągnięty'
    with app.state.db.tx() as x:
        x.execute("UPDATE battlepass SET xp=1000")
    cash0 = st()['cash']
    r = c.post('/api/worlds/2/battlepass/claim', json={'level': 1, 'track': 'free'}); assert r.status_code == 200, r.text
    assert st()['cash'] == cash0 + 250
    assert c.post('/api/worlds/2/battlepass/claim', json={'level': 1, 'track': 'free'}).status_code == 409, 'jednorazowo'
    assert c.post('/api/worlds/2/battlepass/claim', json={'level': 5, 'track': 'premium'}).json()['detail'] == 'Ta nagroda wymaga Premium.'
    assert c.post('/api/worlds/2/battlepass/premium', json={}).json()['detail'] == 'Premium kosztuje 400💎.'
    NS.patch(db, lambda s: s.update(diamonds=450))
    assert c.post('/api/worlds/2/battlepass/premium', json={}).status_code == 200 and st()['diamonds'] == 50
    season = BP.season_of(clock[0])
    assert c.post('/api/worlds/2/battlepass/claim', json={'level': 5, 'track': 'premium'}).status_code == 200
    assert f'bp-{season}-frame' in st()['frames'], 'Premium wsteczne — odbierasz też wcześniejsze poziomy'
    assert c.post('/api/worlds/2/battlepass/claim', json={'level': 11, 'track': 'free'}).status_code == 409
    # nowy miesiąc = nowy sezon od zera
    clock[0] = BP.season_end(clock[0]) + 1000
    g = c.get('/api/worlds/2/battlepass').json()
    assert g['season'] != season and g['xp'] == 0 and g['premium'] is False


def test_bp_xp_from_dungeon_and_build(tmp_path):
    from tests.test_dungeon import register, create
    clock = [1780000000000]
    from server.app import create_app
    app = create_app(tmp_path / 'g.sqlite3', lambda: clock[0], tmp_path / 's.txt')
    a = register(app, 'bpdung'); create(a, 'Bpdung')
    with app.state.db.tx() as x:
        s = json.loads(x.execute("SELECT state_json FROM characters WHERE nickname='Bpdung'").fetchone()[0])
        s.update(xp=400, stats=[300] * 5, cash=50000)
        x.execute("UPDATE characters SET state_json=?,current_location='brama-lochow' WHERE nickname='Bpdung'", (json.dumps(s),))
    assert a.post('/api/worlds/2/dungeon/floor', json={'mode': 'normal'}).json()['cleared']
    assert a.get('/api/worlds/2/battlepass').json()['xp'] == BP.XP['dungeon']
    import uuid
    r = a.post('/api/worlds/2/actions', headers={'Idempotency-Key': uuid.uuid4().hex}, json={'action': 'upgrade_building', 'building': 'cafe'})
    assert r.status_code == 200, r.text
    assert a.get('/api/worlds/2/battlepass').json()['xp'] == BP.XP['dungeon'] + BP.XP['build']


# ---------- 8.6 ----------
def test_dashboard_single_request(tmp_path):
    clock = [NS.T0]
    from server.app import create_app
    db = tmp_path / 'd.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 's.txt')
    c = NS.player(app, db, 'pulpit')
    NS.hire(c, db)
    d = c.get('/api/worlds/2/dashboard'); assert d.status_code == 200, d.text
    j = d.json()
    assert set(j) >= {'state', 'npc', 'assistant', 'events', 'vaults', 'battlepass', 'milestones'}
    assert j['state']['state']['cash'] == c.get('/api/worlds/2/state').json()['state']['cash']
    assert j['npc']['count'] == 1 and sum(j['npc']['byStatus'].values()) == 1
    assert j['vaults']['total'] >= 0 and j['battlepass']['levels'] == 30 and 'activeDays' in j['milestones']
    other = NS.player(app, db, 'obcy')
    assert other.get('/api/worlds/1/dashboard').status_code in (403, 404), 'bez postaci w świecie — brak dostępu'


def test_error_messages_translated(tmp_path):
    """8.5: komunikaty 409/4xx tłumaczone wg języka konta, potem Accept-Language; domyślnie pl."""
    from server import err_i18n as ERRI
    assert ERRI.translate('Za mało gotówki — potrzeba 500 $.', 'en') == 'Not enough cash — you need 500 $.'
    assert ERRI.translate('Ten pojazd wymaga poziomu 7.', 'de') == 'Dieses Fahrzeug erfordert Stufe 7.'
    assert ERRI.translate('Tekst spoza słownika', 'fr') == 'Tekst spoza słownika'
    clock = [NS.T0]
    from server.app import create_app
    db = tmp_path / 'd.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 's.txt')
    c = NS.player(app, db, 'jezyk')
    r = NS.post(c, 'battlepass/premium'); assert r.status_code == 409 and r.json()['detail'] == 'Premium kosztuje 400💎.'
    c.headers['Accept-Language'] = 'fr-FR,fr;q=0.9'
    assert NS.post(c, 'battlepass/premium').json()['detail'] == 'Le Premium coûte 400💎.'
    assert c.post('/api/account/language', json={'language': 'de'}).status_code == 200
    assert NS.post(c, 'battlepass/premium').json()['detail'] == 'Premium kostet 400💎.', 'konto ma pierwszeństwo'
    assert c.get('/api/worlds/999/state').status_code in (403, 404)


def test_dashboard_diamonds_and_alliance(tmp_path):
    """Pulpit zwraca 💎 i sojusz (dla Fluttera — jedno żądanie)."""
    clock = [NS.T0]
    from server.app import create_app
    db = tmp_path / 'd.sqlite3'
    app = create_app(db, lambda: clock[0], tmp_path / 's.txt')
    c = NS.player(app, db, 'pulpit2')
    j = c.get('/api/worlds/2/dashboard').json()
    assert j['diamonds'] == 0 and j['alliance'] is None
    r = NS.post(c, 'organizations', {'name': 'Pulpit Team', 'tag': 'PLT'}); assert r.status_code == 200, r.text
    a = c.get('/api/worlds/2/dashboard').json()['alliance']
    assert a['tag'] == 'PLT' and a['role'] == 'leader' and a['members'] == 1 and a['federation'] is None
