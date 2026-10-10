"""Prototyp Combat 3.0 — TYLKO do symulacji parametrów do PROJEKT-COMBAT-3.md.
Nie jest importowany przez serwer. Po zatwierdzeniu projektu logika trafi do server/combat.py."""
import random
import statistics
import sys

# --- broń (slot Rękawice) → zakres obrażeń ---
WEAPON = {None: (15, 25), 'basic': (20, 30), 1: (30, 45), 2: (45, 65), 3: (65, 90), 4: (85, 115)}
P = dict(
    hp_base=500, hp_cha=10, hp_lvl=8,
    str_mult=0.02,               # +2% obrażeń za punkt Siły
    heavy_chance={'bokser': 1 / 6, 'obronca': 1 / 10, 'szybki': 1 / 10}, heavy_mult=1.6, bokser_dmg=0.12,   # Bokser: pasywnie +15% obrażeń
    crit_base=0.05, crit_cunning=0.003, crit_mult=1.75,
    szybki_crit_stack=0.05, szybki_crit_cap=0.25,
    dodge_base=0.10, dodge_szybki=0.08, dodge_min=0.03, dodge_max=0.40,
    block_base=0.15, block_obronca=-0.05, block_min=0.05, block_max=0.40, block_red=0.5,
    parry_obronca=0.0,
    obronca_red=0.20, obronca_counter=1 / 8,
    szybki_counter=0.30, counter_mult=0.6,
    guard_bonus=0.20,            # StatusEffect nextAttackDamageBonus po udanym bloku/parowaniu
    fat_from=20, fat_step=0.10,
)


def clamp(v, a, b):
    return max(a, min(b, v))


def keff(me, op):  # z 2.3: przewaga statystyk tłumi obronę słabszego
    return clamp(2 - sum(op) / max(1, sum(me)), 0, 1)


class F:
    def __init__(self, name, cls, stats, lvl=10, weapon=None, evo=None):
        self.name, self.cls, self.st, self.lvl, self.weapon, self.evo = name, cls, stats, lvl, weapon, evo
        self.hp = P['hp_base'] + P['hp_cha'] * stats[3] + P['hp_lvl'] * lvl
        self.effects = {}        # StatusEffects: nextAttackDamageBonus, critStacks


def fight(a, b, seed, log=False):
    rng = random.Random(seed)
    f = [a, b]
    k = [keff(a.st, b.st), keff(b.st, a.st)]
    r = 0
    ex = []
    while a.hp > 0 and b.hp > 0 and r < 1000:
        r += 1
        fat = max(0, r - P['fat_from']) * P['fat_step']
        order = sorted((0, 1), key=lambda i: -(f[i].st[2] + rng.uniform(0, 20) + (5 if f[i].cls == 'szybki' else 0)))
        for s in order:
            o = 1 - s
            if f[s].hp <= 0 or f[o].hp <= 0:
                continue
            ex += strike(rng, f, k, s, o, fat, r)
    return (0 if a.hp > 0 else 1) if (a.hp <= 0) != (b.hp <= 0) else None, r, ex


def roll_dmg(rng, att, mult=1.0):
    lo, hi = WEAPON[att.weapon]
    return rng.uniform(lo, hi) * (1 + P['str_mult'] * att.st[0]) * mult


def strike(rng, f, k, s, o, fat, r, counter=False):
    A, D = f[s], f[o]
    out = []
    heavy = not counter and rng.random() < P['heavy_chance'][A.cls]
    action = 'KNEE_STRIKE' if counter else ('PUNCH_HEAVY' if heavy else 'PUNCH_FAST')
    defmul = max(0.0, 1 - fat) * k[o]           # FATIGUE + przewaga statystyk tłumią obronę
    # 1) unik
    dodge = clamp(P['dodge_base'] + 0.5 * (D.st[2] - A.st[2]) / (D.st[2] + A.st[2]) + (P['dodge_szybki'] if D.cls == 'szybki' else 0),
                  P['dodge_min'], P['dodge_max']) * defmul
    if rng.random() < dodge:
        out.append((r, s, action, 'DODGE_SIDE', 'MISSED', 0))
        if D.cls == 'szybki' and not counter and rng.random() < P['szybki_counter']:
            out += strike(rng, f, k, o, s, fat, r, counter=True)
        return out
    # 2) parowanie (Obrońca) / blok
    reaction, result, mult = 'TAKE_HIT', 'FULL_HIT', 1.0
    if D.cls == 'obronca' and rng.random() < P['parry_obronca'] * defmul:
        reaction, result, mult = 'PARRY_HAND', 'PARRIED', 0.0
    else:
        block = clamp(P['block_base'] + 0.5 * (D.st[1] - A.st[0]) / (D.st[1] + A.st[0]) + (P['block_obronca'] if D.cls == 'obronca' else 0), P['block_min'], P['block_max']) * defmul
        if rng.random() < block:
            reaction, result, mult = 'GUARD_BLOCK', 'BLOCKED_PARTIAL', P['block_red']
    # 3) crit
    crit_ch = P['crit_base'] + P['crit_cunning'] * A.st[4] + A.effects.get('critStacks', 0)
    crit = mult > 0 and rng.random() < crit_ch
    # 4) obrażenia
    dmg = roll_dmg(rng, A, (P['heavy_mult'] if heavy else 1) * (P['counter_mult'] if counter else 1) * mult)
    dmg *= 1 + A.effects.pop('nextAttackDamageBonus', 0)
    if A.cls == 'bokser':
        dmg *= 1 + P['bokser_dmg']
    if crit:
        dmg *= P['crit_mult']; result = 'CRITICAL_HIT'
        A.effects['critStacks'] = 0
    elif mult > 0 and A.cls == 'szybki':
        A.effects['critStacks'] = min(P['szybki_crit_cap'], A.effects.get('critStacks', 0) + P['szybki_crit_stack'])
    if D.cls == 'obronca':
        dmg *= 1 - P['obronca_red']
    dmg *= 1 + fat
    D.hp = max(0, D.hp - dmg)
    out.append((r, s, action, reaction, result, round(dmg, 1)))
    if reaction in ('GUARD_BLOCK', 'PARRY_HAND'):
        D.effects['nextAttackDamageBonus'] = P['guard_bonus']
        if D.cls == 'obronca' and not counter and D.hp > 0 and rng.random() < P['obronca_counter']:
            out += strike(rng, f, k, o, s, fat, r, counter=True)
    return out


def rate(ac, dc, sa, sd, wa=None, wd=None, n=2000):
    w = 0; rounds = []
    for seed in range(n):
        win, r, _ = fight(F('A', ac, sa, weapon=wa), F('D', dc, sd, weapon=wd), seed)
        w += win == 0; rounds.append(r)
    return w / n, statistics.mean(rounds), max(rounds)


if __name__ == '__main__':
    C = ['bokser', 'obronca', 'szybki']
    print('== Równe staty 20, bez broni: % wygranych wiersza (atakujący) / średnio rund ==')
    for a in C:
        print(a.ljust(8), '  '.join(f"{d[:3]}:{rate(a, d, [20]*5, [20]*5)[0]:.0%}/{rate(a, d, [20]*5, [20]*5, n=300)[1]:.1f}r" for d in C))
    print('== Przewaga statystyk (silniejszy atakuje i broni się — min z obu ról) ==')
    for mult in (1.25, 1.5, 2.0, 3.0):
        worst = min(min(rate(a, d, [round(10*mult)]*5, [10]*5, n=500)[0], 1 - rate(d, a, [10]*5, [round(10*mult)]*5, n=500)[0]) for a in C for d in C)
        print(f'{mult}x: najgorsza para {worst:.1%}')
    print('== Szybki 30 vs Obrońca 10 ==', rate('szybki', 'obronca', [30]*5, [10]*5)[0])
    print('== Broń przy równych statach 20 (bokser vs bokser) ==')
    for wa, wd in ((1, None), (2, 1), (4, 3), (4, None)):
        w, rr, mx = rate('bokser', 'bokser', [20]*5, [20]*5, wa, wd, n=1000)
        print(f'T{wa} vs {wd}: {w:.0%}  śr. {rr:.1f} rund, max {mx}')
    print('== Długość walki, broń T2 obie strony, staty 20 ==', rate('obronca', 'szybki', [20]*5, [20]*5, 2, 2, n=1000)[1:])
    if '--log' in sys.argv:
        _, _, ex = fight(F('Ty', 'szybki', [20]*5, weapon=2), F('Wróg', 'obronca', [20]*5, weapon=2), 7)
        for e in ex[:16]:
            print(e)
