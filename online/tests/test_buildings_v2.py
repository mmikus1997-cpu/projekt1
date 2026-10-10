"""4.1–4.3 GDD v3.1: 6 budynków, Kawiarnia lvl 10 (skarbiec 24 h), Klub Nocny lvl 7 (skarbiec 72 h), migracja."""
import pytest
from server import economy as E
from tests.test_npc_shift import env, player, patch, cash, T0  # noqa: F401
from tests.test_fuel import st, act

H = E.HOUR


def fresh(**kw):
    s = E.new(T0); s.update(kw); E.sync(s, T0, 1); return s


def test_migration_gym_club_and_corner_cafe():
    s = E.new(T0)
    s['buildings'] = dict(residence=3, garage=2, cafe=2, gym=4, club=5, hall=0)
    s['ventures'] = dict(cafe=dict(level=4, vault=123.9, upgrade=None), studio=None)
    c0 = s['cash']
    E.sync(s, T0, 1)
    b = s['buildings']
    assert 'gym' not in b and b['club'] == 1 and b['nightclub'] == 0          # Siłownia bez zwrotu, Sala Klubowa max 1
    assert b['cafe'] == 4 and 'cafe' not in s['ventures'] and s['cash'] == c0 + 123  # skarbiec Café → gotówka, poziom max(2,4)
    E.sync(s, T0, 1)                                                           # idempotentnie
    assert s['cash'] == c0 + 123 and b['cafe'] == 4


def test_tables_shape():
    assert len(E.CAFE_VAULT_RATES) == 10 and E.CAFE_VAULT_RATES[0] == 30 and E.CAFE_VAULT_RATES[-1] == 465
    assert len(E.NIGHTCLUB_RATES) == 7 and E.NIGHTCLUB_RATES[0] == 80 and E.NIGHTCLUB_RATES[-1] == 1280
    for k, m in E.BUILDING_MAXES.items():
        if k != 'hall':
            assert len(E.BUILDING_COSTS[k]) == m, k                            # koszt na każdy poziom


def _up(s, b):
    # M5: rozbudowa trwa — kończymy ją przesunięciem zegara
    m = E.action(s, 'upgrade_building', dict(building=b), T0, 1)
    E.construction_sync(s, T0 + 10 * E.HOUR)
    return m


def test_cafe_to_10_and_nightclub_build_to_7():
    s = fresh(cash=10**7)
    for lv in range(1, 10):
        c0 = s['cash']; _up(s, 'cafe')
        assert s['buildings']['cafe'] == lv + 1 and s['cash'] == c0 - E.CAFE_BUILD_COST[lv]
    with pytest.raises(E.RuleError): E.action(s, 'upgrade_building', dict(building='cafe'), T0, 1)
    m = _up(s, 'nightclub')
    assert 'budowa' in m.lower() and s['buildings']['nightclub'] == 1
    for _ in range(6): _up(s, 'nightclub')
    assert s['buildings']['nightclub'] == 7
    with pytest.raises(E.RuleError): E.action(s, 'upgrade_building', dict(building='nightclub'), T0, 1)
    with pytest.raises(E.RuleError): E.action(s, 'upgrade_building', dict(building='club'), T0, 1)   # max 1
    with pytest.raises(E.RuleError): E.action(s, 'upgrade_building', dict(building='gym'), T0, 1)    # nie istnieje


def test_vault_rates_and_caps(flat_stats):
    s = fresh()
    s['buildings'].update(cafe=10, nightclub=7)
    E.sync(s, T0 + 2 * H, 1)
    assert round(s['vaults']['cafe']) == 930 and round(s['vaults']['nightclub']) == 2560
    E.sync(s, T0 + 100 * H, 1)
    assert round(s['vaults']['cafe']) == 465 * 24                               # Kawiarnia: limit 24 h
    assert round(s['vaults']['nightclub']) == 1280 * 72                         # Klub Nocny: limit 72 h


def test_nightclub_not_built_accrues_nothing():
    s = fresh(); E.sync(s, T0 + 10 * H, 1)
    assert s['vaults']['nightclub'] == 0
    with pytest.raises(E.RuleError, match='wybuduj'): E.action(s, 'collect_nightclub', {}, T0 + 10 * H, 1)


def test_collect_anywhere_via_api(env):
    app, clock, db = env
    c = player(app, db, 'skarbnik')                                             # dzielnica 1 (nie Zakłady Miejskie)
    patch(db, lambda s: (s['buildings'].update(nightclub=1), s['vaults'].update(nightclub=500.7, cafe=40.2)))
    c0 = cash(db)
    r = act(c, action='collect_nightclub')
    assert r.status_code == 200, r.text
    assert cash(db) == c0 + 500 and st(db)['vaults']['nightclub'] < 1
    r = act(c, action='collect', business='cafe')
    assert r.status_code == 200, r.text
    assert cash(db) == c0 + 540
    assert act(c, action='collect', business='courier').status_code == 409      # firmy dalej tylko w dzielnicy 2


def test_old_cafe_buttons_compat():
    s = fresh(cash=10**6)
    with pytest.raises(E.RuleError, match='Corner Café'): E.action(s, 'buy_business', dict(business='cafe'), T0, 1, district=2)
    E.action(s, 'upgrade', dict(business='cafe'), T0, 1, district=2)           # stary przycisk → rozbudowa budynku
    E.construction_sync(s, T0 + 10 * E.HOUR)                                   # M5: po czasie budowy
    assert s['buildings']['cafe'] == 2


def test_barista_boosts_cafe_building():
    s = fresh(cash=10**6)
    E.action(s, 'hire_staff', dict(staff='cafe'), T0, 1)
    E.sync(s, T0 + H, 1)
    assert round(s['vaults']['cafe'], 1) == 37.5                               # 30 $/h +25%
