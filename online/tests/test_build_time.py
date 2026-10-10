"""M5: czas budowy budynków w dzielnicy — rusztowania, jedna budowa naraz, zakończenie po czasie."""
import pytest
from server import economy as E
from tests.test_npc_shift import T0  # noqa: F401


def fresh(**kw):
    s = E.new(T0); s.update(kw); E.sync(s, T0, 1); return s


def test_build_seconds_curve():
    assert E.build_seconds('residence', 1) == E.BUILD_MIN_S          # 5 min
    assert E.build_seconds('residence', 5) == E.BUILD_MAX_S          # 4 h
    assert E.build_seconds('cafe', 10) == E.BUILD_MAX_S
    assert E.build_seconds('hall', 1) == E.HALL_BUILD_S              # 8 h
    xs = [E.build_seconds('cafe', t) for t in range(1, 11)]
    assert xs == sorted(xs) and len(set(xs)) == 10                   # rośnie z poziomem


def test_upgrade_starts_construction_and_finishes_after_time():
    s = fresh(cash=10**6)
    m = E.action(s, 'upgrade_building', dict(building='residence'), T0, 1)
    assert 'gotowe za' in m
    c = s['construction']
    assert c['building'] == 'residence' and c['target'] == 2
    assert c['endsAt'] - c['startedAt'] == E.build_seconds('residence', 2) * 1000
    assert s['buildings']['residence'] == 1                          # nadal stary poziom
    E.sync(s, c['endsAt'] - 1, 1)
    assert s['buildings']['residence'] == 1 and s.get('construction')
    E.sync(s, c['endsAt'], 1)
    assert s['buildings']['residence'] == 2 and not s.get('construction')
    assert any('budowa zakończona' in str(x) for x in s.get('history', []) )


def test_one_build_at_a_time_and_no_double_charge():
    s = fresh(cash=10**6)
    E.action(s, 'upgrade_building', dict(building='cafe'), T0, 1)
    cash = s['cash']
    with pytest.raises(E.RuleError) as e:
        E.action(s, 'upgrade_building', dict(building='garage'), T0 + 1000, 1)
    assert 'Trwa już budowa' in str(e.value)
    assert s['cash'] == cash                                         # odmowa nie pobiera pieniędzy
    # po zakończeniu można budować dalej
    E.action(s, 'upgrade_building', dict(building='garage'), T0 + 10 * E.HOUR, 1)
    assert s['buildings']['cafe'] == 2 and s['construction']['building'] == 'garage'


def test_world_speed_shortens_build():
    s = fresh(cash=10**6)
    E.action(s, 'upgrade_building', dict(building='residence'), T0, 10)
    c = s['construction']
    assert c['endsAt'] - c['startedAt'] == E.build_seconds('residence', 2) * 1000 // 10


def test_broken_construction_is_dropped():
    s = fresh(cash=10**6)
    s['construction'] = dict(building='bogus', target=3, endsAt=0)
    E.sync(s, T0 + 1, 1)
    assert 'construction' not in s
