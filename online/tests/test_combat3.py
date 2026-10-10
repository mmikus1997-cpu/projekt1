"""Combat 3.0 — testy silnika wg zatwierdzonego PROJEKT-COMBAT-3.md."""
from server import combat as C
from server import gear as G

S = [20] * 5


def set_eq(tier):
    st = [s['id'] for s in G.SETS if s['tier'] == tier][0]
    return {sl: f'{st}-{sl}' for sl in G.SLOTS}


def rate(ca, cd, sa=S, sd=S, ga=None, gd=None, n=300, lv=(15, 15)):
    w = 0; R = []
    for i in range(n):
        r = C.simultaneous(sa, sd, seed=i, a_cls=ca, d_cls=cd, levels=lv, a_gear=ga, d_gear=gd)
        w += r['winner'] == 0; R.append(len(r['rounds']))
    return w / n, sum(R) / n, max(R)


def test_wersja_silnika():
    assert C.ENGINE == '3.0' and C.ENGINE_V1 == '3.0' and C.ENGINE_V2 == '3.0'
    assert not hasattr(C, 'CLASS_BEATS'), 'RPS usunięty'


def test_bron_z_rekawic_daje_zakres():
    assert C.loadout({})['weapon'] == [15, 25], 'gołe pięści'
    assert C.loadout({'gloves': 'basic-gloves'})['weapon'] == [20, 30]
    t4 = [s['id'] for s in G.SETS if s['tier'] == 4][0]
    assert C.loadout({'gloves': f'{t4}-gloves'})['weapon'] == [85, 115]


def test_pancerz_daje_hp_i_def():
    lo = C.loadout(set_eq(4))
    assert lo['hp'] == 7 * C.ARMOR[4][0] and abs(lo['def_'] - 7 * C.ARMOR[4][1]) < 1e-9
    r = C.simultaneous(S, S, seed=1, a_gear=set_eq(4), d_gear={})
    assert r['hpStart'][0] - r['hpStart'][1] == 7 * C.ARMOR[4][0]


def test_obrazenia_w_zakresie_broni():
    for seed in range(40):
        r = C.simultaneous(S, S, seed=seed, a_cls='szybki', d_cls='szybki')
        for rd in r['rounds']:
            for ex in rd['exchanges']:
                lo, hi = ex['rolls']['dmg'][1:] if 'dmg' in ex['rolls'] else (15, 25)
                assert (lo, hi) == (15, 25)
                if 'dmg' in ex['rolls']:
                    assert lo <= ex['rolls']['dmg'][0] <= hi


def test_niezalezne_rzuty_w_raporcie():
    r = C.simultaneous(S, S, seed=7)
    ex = [e for rd in r['rounds'] for e in rd['exchanges'] if e['result'] != 'MISSED'][0]
    assert {'dodge', 'block', 'crit', 'dmg'} <= set(ex['rolls'])


def test_determinizm_seed():
    a = C.simultaneous(S, [22, 18, 25, 20, 19], seed=1234, a_cls='bokser', d_cls='szybki', a_gear=set_eq(2))
    b = C.simultaneous(S, [22, 18, 25, 20, 19], seed=1234, a_cls='bokser', d_cls='szybki', a_gear=set_eq(2))
    assert a == b and a['seed'] == 1234


def test_fatigue_zawsze_ko():
    for seed in range(60):
        r = C.simultaneous([40] * 5, [40] * 5, seed=seed, a_cls='obronca', d_cls='obronca', levels=(30, 30), a_gear=set_eq(4), d_gear=set_eq(4))
        assert r['winner'] is not None and len(r['rounds']) <= 40
    assert C.fatigue(20) == 0 and abs(C.fatigue(25) - 0.5) < 1e-9


def test_macierz_klas_rownowaga():
    K = ['bokser', 'obronca', 'szybki']
    for a in K:
        for d in K:
            w = rate(a, d)[0]
            assert 0.30 <= w <= 0.70, (a, d, w)


def test_przewaga_statystyk_x2_wygrywa():
    for a in ('bokser', 'obronca', 'szybki'):
        for d in ('bokser', 'obronca', 'szybki'):
            assert rate(a, d, [40] * 5, [20] * 5, n=60)[0] >= 0.98


def test_dlugosc_walk_t3_t4():
    for t in (3, 4):
        _, avg, _ = rate('bokser', 'szybki', ga=set_eq(t), gd=set_eq(t), n=200)
        assert 8 <= avg <= 15, (t, avg)


def test_bokser_mocny_cios_i_ewolucja():
    def heavy_share(evo):
        h = n = 0
        for seed in range(150):
            r = C.simultaneous(S, S, seed=seed, a_cls='bokser', d_cls='bokser', a_evo=evo)
            for rd in r['rounds']:
                for ex in rd['exchanges']:
                    if ex['striker'] == 0:
                        n += 1; h += ex['attacker_action'] == 'PUNCH_HEAVY'
        return h / n
    base, evo = heavy_share(None), heavy_share('zelazna-piesc')
    assert 0.13 < base < 0.21 and 0.21 < evo < 0.30


def test_kontry_klasowe():
    obr = szy = 0
    for seed in range(150):
        r = C.simultaneous(S, S, seed=seed, a_cls='bokser', d_cls='obronca')
        exs = [e for rd in r['rounds'] for e in rd['exchanges']]
        obr += sum(1 for i, e in enumerate(exs) if e['attacker_action'] == 'KNEE_STRIKE' and e['striker'] == 1 and exs[i - 1]['defender_reaction'] == 'GUARD_BLOCK')
        r = C.simultaneous(S, S, seed=seed, a_cls='bokser', d_cls='szybki')
        exs = [e for rd in r['rounds'] for e in rd['exchanges']]
        szy += sum(1 for i, e in enumerate(exs) if e['attacker_action'] == 'KNEE_STRIKE' and e['striker'] == 1 and exs[i - 1]['defender_reaction'] == 'DODGE_SIDE')
    assert obr > 0 and szy > 0
    # Bokser nie ma kontr
    r = C.simultaneous(S, S, seed=3, a_cls='szybki', d_cls='bokser')
    assert not any(e['attacker_action'] == 'KNEE_STRIKE' and e['striker'] == 1 for rd in r['rounds'] for e in rd['exchanges'])


def test_status_effect_po_bloku():
    found = False
    for seed in range(50):
        r = C.simultaneous(S, S, seed=seed)
        for rd in r['rounds']:
            for side in (0, 1):
                if any(e['id'] == 'nextAttackDamageBonus' for e in rd['effects'][side]):
                    found = True
    assert found


def test_obronca_redukcja_20():
    f = C.Fighter(S, 'Obrońca', None, None, 1, {})
    assert f.red == 0.20 and f.counter_block == 1 / 8
    f = C.Fighter(S, 'Obrońca', 'murarz-ringu', 'bastion', 1, {})
    assert f.red == 0.28 and abs(f.block_bonus - 0.03) < 1e-9


def test_ewolucje_mapowanie():
    sz = C.Fighter(S, 'Szybki', 'blyskawica', 'zabojca', 1, {})
    assert sz.counter_dodge == 0.42 and sz.crit_mult == 2.1
    bk = C.Fighter(S, 'Bokser', None, 'czempion', 10, {})
    assert abs(bk.hp_start - C.hp_v3(20, 10) * 1.12) < 0.2
    assert C.Fighter(S, 'Bokser', None, 'niszczyciel', 1, {}).heavy_mult == 1.9
    assert abs(C.Fighter(S, 'Obrońca', None, 'mistrz-riposty', 1, {}).counter_mult - 0.9) < 1e-9 and C.Fighter(S, 'Obrońca', None, None, 1, {}).counter_mult == 0.6
    cien = C.Fighter(S, 'Szybki', 'nokaut-fantom', 'cien', 1, {})
    assert cien.crit_stack == 0.07 and cien.init_bonus == 10 and abs(cien.dodge_bonus - 0.14) < 1e-9


def test_fight_zgodnosc_wyzwan():
    r = C.fight(S, S, classes=('bokser', 'szybki'), seed=5)
    assert isinstance(r['rounds'], int) and r['roundLog'] and r['winner'] in (0, 1)
