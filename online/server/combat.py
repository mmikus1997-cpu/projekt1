"""Combat 3.0 — silnik walki napisany od nowa wg zatwierdzonego PROJEKT-COMBAT-3.md (D1–D5).

Najważniejsze zasady:
- Broń = slot Rękawice → zakres obrażeń (gołe pięści 15–25 … T4 85–115); Siła mnoży +2%/pkt.
- Pancerz i biżuteria (pozostałe 7 slotów) dają HP i DEF (redukcja obrażeń) — D2 (a).
- Każda akcja to niezależne rzuty RNG: typ ciosu → unik → blok → crit → wartość obrażeń.
- RPS (Presja/Kontrola/Kontra) usunięty; zamiast niego StatusEffects (nextAttackDamageBonus, critStacks, combo).
- Klasy: Bokser 1/6 Mocnego Ciosu (+12% dmg), główna statystyka +1%/pkt obrażeń (Bokser Siła, Obrońca Int, Szybki Refleks), Obrońca −20% otrzymywanych i 1/8 Kontry po bloku (−5 pp bloku),
  Szybki 30% Kontry po uniku i stosy critu +5%/trafienie (max 25%), unik +8 pp, inicjatywa +5.
- Fatigue od 21. rundy: +10% otrzymywanych obrażeń i −10 pp uniku/bloku za każdą rundę → zawsze KO.
- Seed zapisany w raporcie → walkę można odtworzyć 1:1 (testy, spory).
Publiczne API (simultaneous, fight, pvp_class, ewolucje, poziom PvP) zachowuje nazwy z 2.x — wywołujące moduły
przekazują dodatkowo ekwipunek (a_gear/d_gear = słownik `equipped` ze stanu postaci albo gotowy loadout).
"""
import random
import secrets

ENGINE = '3.0'
# Wersje zapisywane przy walkach (stare wiersze zachowują swoje — raporty 1.x/2.x dalej się wyświetlają)
ENGINE_V1_LEGACY = '1.0'; ENGINE_V2_LEGACY = '2.0'
ENGINE_V1 = ENGINE          # fight(): wyzwania rankingowe
ENGINE_V2 = ENGINE          # simultaneous(): PvP, turniej, Loch
ENGINE_V2_PREV = '2.3'
MAX_ROUNDS_GUARD = 1000     # bezpiecznik (przy Fatigue walka kończy się dużo wcześniej)


def clamp(v, a, b):
    return max(a, min(b, v))


# ---------------------------------------------------------------- parametry (zatwierdzone w projekcie)
WEAPON = {                  # zakres obrażeń broni (slot Rękawice)
    'fists': (15, 25, 'Gołe pięści'),
    'basic': (20, 30, 'Rękawice treningowe'),
    'legacy': (25, 35, 'Rękawice klubowe'),
    1: (30, 45, 'Rękawice T1'),
    2: (45, 65, 'Rękawice T2'),
    3: (65, 90, 'Rękawice T3'),
    4: (85, 115, 'Rękawice T4'),
}
ARMOR = {                   # na część pancerza/biżuterii: (HP, DEF) — DEF = ułamek redukcji obrażeń
    'legacy': (15, 0.0),
    1: (30, 0.010),
    2: (60, 0.015),
    3: (100, 0.020),
    4: (150, 0.025),
}
DEF_CAP = 0.35
HP_BASE, HP_CHA, HP_LVL = 300, 6, 6
STR_MULT = 0.02
# Główna statystyka klasy daje dodatkowo +1% obrażeń za punkt (Bokser: Siła, Obrońca: Inteligencja, Szybki: Refleks)
PRIME_STAT = {'Bokser': 0, 'Obrońca': 1, 'Szybki': 2}; PRIME_MULT = 0.01
HEAVY = {'Bokser': 1 / 6, 'Obrońca': 1 / 10, 'Szybki': 1 / 10}; HEAVY_MULT = 1.6
BOKSER_DMG = 0.12
CRIT_BASE, CRIT_CUNNING, CRIT_MULT = 0.05, 0.003, 1.75
SZYBKI_STACK, SZYBKI_STACK_CAP = 0.05, 0.25
DODGE_BASE, DODGE_SZYBKI, DODGE_MIN, DODGE_MAX = 0.10, 0.08, 0.03, 0.40
BLOCK_BASE, BLOCK_OBRONCA, BLOCK_MIN, BLOCK_MAX, BLOCK_RED = 0.15, -0.05, 0.05, 0.40, 0.5
OBRONCA_RED, OBRONCA_COUNTER = 0.20, 1 / 8
SZYBKI_COUNTER, COUNTER_MULT = 0.30, 0.6
GUARD_BONUS = 0.20          # StatusEffect nextAttackDamageBonus po udanym bloku
INIT_SZYBKI = 5
FATIGUE_FROM, FATIGUE_STEP, FATIGUE_DEF_STEP = 20, 0.10, 0.10


def fatigue(round_no):
    """Mnożnik dodatkowych obrażeń: +10% za każdą rundę ponad 20."""
    return FATIGUE_STEP * max(0, round_no - FATIGUE_FROM)


def hp_v3(cha, level):
    return HP_BASE + HP_CHA * cha + HP_LVL * level


# Formuły HP 1.x/2.x — tylko do odczytu starych raportów i testów zgodności
def hp_v1(cha, level): return 200 + 5 * cha + 2 * level
def hp_v2(cha, level): return 80 + 2 * cha + level


def counter_eff(me, op):
    """Balans 2.3 (zostaje): przewaga statystyk tłumi obronę słabszego — 1 przy równych, 0 przy 2× przewadze."""
    pm, po = max(1.0, sum(me)), max(1.0, sum(op))
    return clamp(2 - po / pm, 0.0, 1.0)


# ---------------------------------------------------------------- ekwipunek → loadout
def loadout(equipped=None):
    """Z `equipped` (slot → id przedmiotu) liczy broń i pancerz. Akceptuje też gotowy loadout (dict z 'weapon')."""
    if isinstance(equipped, dict) and 'weapon' in equipped and 'hp' in equipped:
        return equipped
    from . import gear as G   # leniwy import (gear nie importuje combat — brak cyklu)
    eq = equipped or {}
    gloves = eq.get('gloves')
    if gloves in G.BY_ID:
        wkey = G.BY_ID[gloves]['tier']
    elif not gloves:
        wkey = 'fists'
    elif gloves == 'basic-gloves':
        wkey = 'basic'
    elif gloves == 'rekawice-lochu':
        wkey = 2   # QA 4: unikat z bossa Lochu = broń tieru T2
    else:
        wkey = 'legacy'
    hp, df, pieces = 0, 0.0, []
    for slot, iid in eq.items():
        if slot == 'gloves' or not iid:
            continue
        if iid in G.BY_ID:
            t = G.BY_ID[iid]['tier']; a = ARMOR[t]; pieces.append(t)
        elif not str(iid).startswith('basic-'):
            a = ARMOR['legacy']; pieces.append(0)
        else:
            continue
        hp += a[0]; df += a[1]
    lo, hi, label = WEAPON[wkey]
    return dict(weapon=[lo, hi], weaponTier=wkey, weaponLabel=label, hp=hp, def_=round(min(DEF_CAP, df), 3), armor=pieces)


def npc_loadout(player_gear=None, boss=False):
    """NPC (Loch): trudność niosą statystyki NPC (strojone pod progresję pięter), więc NPC walczy bronią tego samego
    tieru co gracz — przewagę dają pancerz gracza i ewolucje. Boss dostaje 3 części pancerza tego tieru (min. T1)."""
    pl = loadout(player_gear)
    tier = pl['weaponTier']
    lo, hi, label = WEAPON[tier]
    at = tier if isinstance(tier, int) else 1
    n = 3 if boss else 0
    a = ARMOR[at]
    return dict(weapon=[lo, hi], weaponTier=tier, weaponLabel=label, hp=a[0] * n, def_=round(min(DEF_CAP, a[1] * n), 3), armor=[at] * n)


# ---------------------------------------------------------------- klasy, ewolucje (opisy pod UI)
CLASS_LABEL = {'bokser': 'Bokser', 'obronca': 'Obrońca', 'szybki': 'Szybki'}
CLASS_TACTIC = {'Bokser': 'presja', 'Obrońca': 'kontrola', 'Szybki': 'kontra'}  # tylko etykieta „taktyki” = klasa (bez RPS)
BEATS = {'presja': 'kontrola', 'kontrola': 'kontra', 'kontra': 'presja'}        # legacy (stary endpoint /tactic)
PVP_ACTIONS = ('fast', 'heavy', 'dodge')
PVP_DEFAULT_DEFENSE = ['fast', 'dodge', 'heavy']
STYLE = {   # legacy: opisy stylów dla starych raportów; Combat 3.0 nie używa sekwencji
    'presja': dict(label='Presja', icon='⚡', desc='Styl Boksera — Mocne Ciosy.', seq=['fast', 'heavy', 'fast']),
    'kontrola': dict(label='Kontrola', icon='🛡️', desc='Styl Obrońcy — blok i Kontra.', seq=['fast', 'dodge', 'heavy']),
    'kontra': dict(label='Kontra', icon='🎯', desc='Styl Szybkiego — unik i Kontra.', seq=['dodge', 'fast', 'dodge']),
}
PVP_ALIAS = {'szybki_cios': 'fast', 'mocny_cios': 'heavy', 'unik': 'dodge', 'fast': 'fast', 'heavy': 'heavy', 'dodge': 'dodge'}


def style_seq(t):
    st = STYLE.get(t)
    return list(st['seq']) if st else list(PVP_DEFAULT_DEFENSE)


def pvp_class(stats, cls=None):
    # klasa wybrana przy odblokowaniu PvP ma pierwszeństwo; bez niej dominanta statystyk (stare postacie)
    if cls:
        if cls in CLASS_LABEL: return CLASS_LABEL[cls]
        if cls in ('Bokser', 'Obrońca', 'Szybki'): return cls
    dom = max(range(5), key=lambda i: stats[i])
    return ['Bokser', 'Obrońca', 'Szybki', 'Obrońca', 'Szybki'][dom]


def class_tactic(stats, cls=None): return CLASS_TACTIC[pvp_class(stats, cls)]
def class_seq(stats, cls=None): return style_seq(class_tactic(stats, cls))
def advantage(c1, c2): return False   # Combat 3.0: brak przewagi RPS


# Ewolucje I (od PvP 5) — mapowanie D3
EVOLUTIONS = {
    'zelazna-piesc': dict(cls='bokser', icon='👊', label='Żelazna Pięść', passive='Nokaut', desc='Szansa na Mocny Cios rośnie z 1/6 do 1/4.'),
    'mistrz-ringu': dict(cls='bokser', icon='👑', label='Mistrz Ringu', passive='Rytm', desc='Każde trafienie z rzędu +8% obrażeń (max 3 stosy; unik/parowanie rywala zeruje).'),
    'murarz-ringu': dict(cls='obronca', icon='🧱', label='Murarz Ringu', passive='Garda', desc='Redukcja otrzymywanych obrażeń rośnie z 20% do 28%.'),
    'zelazny-straznik': dict(cls='obronca', icon='⚔️', label='Żelazny Strażnik', passive='Riposta', desc='Szansa na Kontrę po bloku rośnie z 1/8 do 1/5.'),
    'blyskawica': dict(cls='szybki', icon='⚡', label='Błyskawica', passive='Kontra z Impetem', desc='Szansa na Kontrę po uniku rośnie z 30% do 42%.'),
    'nokaut-fantom': dict(cls='szybki', icon='👤', label='Nokaut Fantom', passive='Nieuchwytny', desc='Szansa na unik +6 pp.'),
}
# Ewolucje II (od PvP 10)
EVOLUTIONS2 = {
    'czempion': dict(cls='bokser', icon='🏆', label='Czempion', passive='Kondycja mistrza', desc='+12% punktów życia na starcie walki.'),
    'niszczyciel': dict(cls='bokser', icon='💥', label='Niszczyciel', passive='Ciężka ręka', desc='Mocny Cios zadaje ×1,9 zamiast ×1,6.'),
    'bastion': dict(cls='obronca', icon='🏰', label='Bastion', passive='Pancerz', desc='Szansa na blok +8 pp.'),
    'mistrz-riposty': dict(cls='obronca', icon='🤺', label='Mistrz Riposty', passive='Zabójcza riposta', desc='Kontry zadają 150% obrażeń.'),
    'cien': dict(cls='szybki', icon='🌑', label='Cień', passive='Pierwszy krok', desc='+5 inicjatywy, stos critu 7% zamiast 5%.'),
    'zabojca': dict(cls='szybki', icon='🗡️', label='Zabójca', passive='Cios w lukę', desc='Crit zadaje ×2,1 zamiast ×1,75.'),
}

# Poziom PvP: wygrana 3, remis 2, przegrana 1 pkt; co 15 pkt +1 poziom (max 30). Ewolucja I od PvP 5, II od PvP 10.
PVP_LEVEL_STEP = 15; PVP_LEVEL_MAX = 30; EVO1_PVP = 5; EVO2_PVP = 10
def pvp_points(wins, losses, draws): return 3 * int(wins or 0) + 2 * int(draws or 0) + int(losses or 0)
def pvp_level(wins, losses, draws): return min(PVP_LEVEL_MAX, 1 + pvp_points(wins, losses, draws) // PVP_LEVEL_STEP)
def _evo_card(code, e): return dict(code=code, label=e['label'], icon=e['icon'], passive=e['passive'], desc=e['desc'])


def evolution_status(cls, wins, losses, draws, evo1, evo2):
    """Stan ewolucji dla UI: poziom PvP, wybrane ewolucje i — jeśli dostępna — kolejny etap z 2 kartami do wyboru."""
    pts = pvp_points(wins, losses, draws); lvl = pvp_level(wins, losses, draws)
    stage = 1 + (1 if evo1 in EVOLUTIONS else 0) + (1 if evo2 in EVOLUTIONS2 else 0)
    nxt = None
    if cls and stage < 3:
        req = EVO1_PVP if stage == 1 else EVO2_PVP; pool = EVOLUTIONS if stage == 1 else EVOLUTIONS2
        nxt = dict(stage=stage, reqLevel=req, available=lvl >= req, options=[_evo_card(k, v) for k, v in pool.items() if v['cls'] == cls])
    return dict(pvpLevel=lvl, pvpPoints=pts, pvpNextAt=(lvl * PVP_LEVEL_STEP if lvl < PVP_LEVEL_MAX else None), stage=stage,
                evolution1=_evo_card(evo1, EVOLUTIONS[evo1]) if evo1 in EVOLUTIONS else None,
                evolution2=_evo_card(evo2, EVOLUTIONS2[evo2]) if evo2 in EVOLUTIONS2 else None, next=nxt)


# ---------------------------------------------------------------- zawodnik i silnik
class Fighter:
    def __init__(self, stats, cls, evo1, evo2, level, gear):
        self.st = [float(x) for x in stats]
        self.cls = cls
        self.evo1 = evo1 if evo1 in EVOLUTIONS else None
        self.evo2 = evo2 if evo2 in EVOLUTIONS2 else None
        self.lo = loadout(gear)
        hp = hp_v3(self.st[3], level) + self.lo['hp']
        if self.evo2 == 'czempion': hp *= 1.12
        self.hp = self.hp_start = round(hp, 1)
        e1, e2 = self.evo1, self.evo2
        self.heavy_ch = 1 / 4 if e1 == 'zelazna-piesc' else HEAVY[cls]
        self.heavy_mult = 1.9 if e2 == 'niszczyciel' else HEAVY_MULT
        self.red = (0.28 if e1 == 'murarz-ringu' else OBRONCA_RED) if cls == 'Obrońca' else 0.0
        self.counter_block = (1 / 5 if e1 == 'zelazny-straznik' else OBRONCA_COUNTER) if cls == 'Obrońca' else 0.0
        self.counter_dodge = (0.42 if e1 == 'blyskawica' else SZYBKI_COUNTER) if cls == 'Szybki' else 0.0
        self.counter_mult = COUNTER_MULT * (1.5 if e2 == 'mistrz-riposty' else 1.0)
        self.dodge_bonus = (DODGE_SZYBKI if cls == 'Szybki' else 0) + (0.06 if e1 == 'nokaut-fantom' else 0)
        self.block_bonus = (BLOCK_OBRONCA if cls == 'Obrońca' else 0) + (0.08 if e2 == 'bastion' else 0)
        self.crit_stack = (0.07 if e2 == 'cien' else SZYBKI_STACK) if cls == 'Szybki' else 0.0
        self.crit_mult = 2.1 if e2 == 'zabojca' else CRIT_MULT
        self.init_bonus = (INIT_SZYBKI if cls == 'Szybki' else 0) + (5 if e2 == 'cien' else 0)
        self.effects = {}   # StatusEffects: nextAttackDamageBonus, critStacks, combo


def _effects_view(f):
    return [dict(id=k, value=round(v, 3) if isinstance(v, float) else v, turns=None) for k, v in f.effects.items() if v]


def _strike(rng, F, k, s, o, rnd, fat, counter=False):
    """Jedna akcja zawodnika s na o. Zwraca listę wymian (z kontrą, jeśli wypadła)."""
    A, D = F[s], F[o]
    out = []
    heavy = (not counter) and rng.random() < A.heavy_ch
    action = 'KNEE_STRIKE' if counter else ('PUNCH_HEAVY' if heavy else 'PUNCH_FAST')
    defpen = FATIGUE_DEF_STEP * max(0, rnd - FATIGUE_FROM)       # Fatigue: −10 pp obrony na rundę
    rolls = {}
    # 1) unik
    ra, rd = A.st[2], D.st[2]
    dodge = clamp(DODGE_BASE + 0.5 * (rd - ra) / max(1.0, rd + ra) + D.dodge_bonus, DODGE_MIN, DODGE_MAX) * k[o]
    dodge = max(0.0, dodge - defpen)
    rolls['dodge'] = [round(rng.random(), 4), round(dodge, 4)]
    if rolls['dodge'][0] < dodge:
        A.effects.pop('combo', None)
        out.append(dict(striker=s, attacker_action=action, defender_reaction='DODGE_SIDE', result='MISSED', damage=0, rolls=rolls))
        if not counter and D.counter_dodge and D.hp > 0:
            rc = rng.random(); rolls['counter'] = [round(rc, 4), D.counter_dodge]
            if rc < D.counter_dodge:
                out += _strike(rng, F, k, o, s, rnd, fat, counter=True)
        return out
    # 2) blok
    bi, bs = D.st[1], A.st[0]
    block = clamp(BLOCK_BASE + 0.5 * (bi - bs) / max(1.0, bi + bs) + D.block_bonus, BLOCK_MIN, BLOCK_MAX) * k[o]
    block = max(0.0, block - defpen)
    rolls['block'] = [round(rng.random(), 4), round(block, 4)]
    blocked = rolls['block'][0] < block
    reaction, result, mult = ('GUARD_BLOCK', 'BLOCKED_PARTIAL', BLOCK_RED) if blocked else ('TAKE_HIT', 'FULL_HIT', 1.0)
    # 3) crit
    crit_ch = CRIT_BASE + CRIT_CUNNING * A.st[4] + A.effects.get('critStacks', 0.0)
    rolls['crit'] = [round(rng.random(), 4), round(crit_ch, 4)]
    crit = rolls['crit'][0] < crit_ch
    # 4) obrażenia — rzut z zakresu broni
    lo, hi = A.lo['weapon']
    base = rng.uniform(lo, hi); rolls['dmg'] = [round(base, 1), lo, hi]
    dmg = base * (1 + STR_MULT * A.st[0] + PRIME_MULT * A.st[PRIME_STAT.get(A.cls, 0)]) * mult
    if heavy: dmg *= A.heavy_mult
    if counter: dmg *= A.counter_mult
    if A.cls == 'Bokser': dmg *= 1 + BOKSER_DMG
    if A.evo1 == 'mistrz-ringu': dmg *= 1 + 0.08 * A.effects.get('combo', 0)
    dmg *= 1 + A.effects.pop('nextAttackDamageBonus', 0.0)
    if crit:
        dmg *= A.crit_mult; result = 'CRITICAL_HIT'; A.effects.pop('critStacks', None)
    elif A.crit_stack:
        A.effects['critStacks'] = min(SZYBKI_STACK_CAP, A.effects.get('critStacks', 0.0) + A.crit_stack)
    if A.evo1 == 'mistrz-ringu': A.effects['combo'] = min(3, A.effects.get('combo', 0) + 1)
    dmg *= (1 - D.red) * (1 - D.lo['def_'])
    dmg *= 1 + fat
    dmg = round(max(1.0, dmg), 1)
    D.hp = round(max(0.0, D.hp - dmg), 1)
    out.append(dict(striker=s, attacker_action=action, defender_reaction=reaction, result=result, damage=dmg, rolls=rolls))
    if blocked:
        D.effects['nextAttackDamageBonus'] = GUARD_BONUS
        if not counter and D.counter_block and D.hp > 0:
            rc = rng.random(); rolls['counter'] = [round(rc, 4), round(D.counter_block, 4)]
            if rc < D.counter_block:
                out += _strike(rng, F, k, o, s, rnd, fat, counter=True)
    return out


def duel(a_stats, d_stats, seed, a_cls=None, d_cls=None, a_evo=None, d_evo=None, a_evo2=None, d_evo2=None,
         levels=(1, 1), a_gear=None, d_gear=None):
    """Rdzeń Combat 3.0. Zwraca raport w formacie zgodnym z ekranem walki (rounds/exchanges/events)."""
    rng = random.Random(seed)
    ca, cd = pvp_class(a_stats, a_cls), pvp_class(d_stats, d_cls)
    F = [Fighter(a_stats, ca, a_evo, a_evo2, levels[0], a_gear), Fighter(d_stats, cd, d_evo, d_evo2, levels[1], d_gear)]
    k = [counter_eff(a_stats, d_stats), counter_eff(d_stats, a_stats)]
    hp_start = [F[0].hp_start, F[1].hp_start]
    rounds, events = [], []
    rnd = 0
    while F[0].hp > 0 and F[1].hp > 0 and rnd < MAX_ROUNDS_GUARD:
        rnd += 1
        fat = fatigue(rnd)
        ini = [F[i].st[2] + F[i].init_bonus + rng.uniform(0, 20) for i in (0, 1)]
        first = 0 if ini[0] >= ini[1] else 1
        exchanges = []; dealt = [0.0, 0.0]
        for s in (first, 1 - first):
            if F[s].hp <= 0 or F[1 - s].hp <= 0:
                continue
            for ex in _strike(rng, F, k, s, 1 - s, rnd, fat):
                ex['hp'] = [F[0].hp, F[1].hp]
                exchanges.append(ex); dealt[ex['striker']] = round(dealt[ex['striker']] + ex['damage'], 1)
                events.append(dict(round=rnd, attacker=ex['striker'], defender=1 - ex['striker'], landed=ex['damage'] > 0,
                                   critical=ex['result'] == 'CRITICAL_HIT', damage=ex['damage'], hp=list(ex['hp']),
                                   attacker_action=ex['attacker_action'], defender_reaction=ex['defender_reaction'], result=ex['result']))
                if F[0].hp <= 0 or F[1].hp <= 0:
                    break
        head = exchanges[0] if exchanges else dict(attacker_action=None, defender_reaction=None, result=None)
        rounds.append(dict(r=rnd, fatigue=round(fat, 2), first=first, initiative=[round(x, 1) for x in ini], dealt=dealt,
                           hp=[F[0].hp, F[1].hp], attacker_action=head['attacker_action'], defender_reaction=head['defender_reaction'],
                           result=head['result'], exchanges=exchanges, effects=[_effects_view(F[0]), _effects_view(F[1])]))
    winner = None if (F[0].hp > 0) == (F[1].hp > 0) else (0 if F[0].hp > 0 else 1)
    return dict(engine=ENGINE, version=ENGINE, seed=seed, classes=[ca, cd], tactics=[CLASS_TACTIC[ca], CLASS_TACTIC[cd]],
                advantage=[False, False], evolutions=[F[0].evo1, F[1].evo1], evolutions2=[F[0].evo2, F[1].evo2],
                loadouts=[F[0].lo, F[1].lo], counterEff=[round(k[0], 3), round(k[1], 3)], rounds=rounds, events=events,
                winner=winner, finalHp=[F[0].hp, F[1].hp], hpStart=hp_start, stalemate=False, authoritative=True,
                profiles=[dict(hp=hp_start[0]), dict(hp=hp_start[1])])


def simultaneous(a_stats, d_stats, a_seq=None, d_seq=None, seed=None, a_cls=None, d_cls=None, a_evo=None, d_evo=None,
                 levels=(1, 1), hp_mode=None, a_evo2=None, d_evo2=None, a_gear=None, d_gear=None):
    """Zgodność wywołań 2.x: a_seq/d_seq i hp_mode są ignorowane (Combat 3.0 nie ma sekwencji RPS)."""
    if seed is None: seed = secrets.randbits(32)
    return duel(a_stats, d_stats, seed, a_cls, d_cls, a_evo, d_evo, a_evo2, d_evo2, levels, a_gear, d_gear)


def fight(a, b, ta=None, tb=None, levels=(1, 1), classes=(None, None), evos=((None, None), (None, None)), gears=(None, None), seed=None):
    """Wyzwania rankingowe — ten sam silnik 3.0; `rounds` w tym raporcie = liczba rund (zgodność z 1.x)."""
    if seed is None: seed = secrets.randbits(32)
    rep = duel(a, b, seed, classes[0], classes[1], evos[0][0], evos[1][0], evos[0][1], evos[1][1], levels, gears[0], gears[1])
    rep['roundLog'] = rep['rounds']; rep['rounds'] = len(rep['roundLog']); rep['stats'] = [a, b]
    return rep
