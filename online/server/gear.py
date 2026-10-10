"""Etap 7 GDD v3.1 — ekwipunek 8 slotów, plecak, 9 setów T1–T4, sklep w Sali Klubowej (rotacja 6 h),
crafting 3→1, kupony (max 100), i18n (pl/en/de/fr) i przelicznik walut (tylko wyświetlanie)."""
import hashlib
import json
import random
from pathlib import Path
from typing import Literal, Optional
from fastapi import Request
from pydantic import BaseModel

# 7.1 sloty postaci (kolejność = UI)
SLOTS = ('gloves', 'shoes', 'pants', 'belt', 'shirt', 'head', 'amulet', 'ring')
ZONE_ARMOR = ('shoes', 'pants', 'belt', 'shirt', 'head')   # 7.3 strefa 1
ZONE_JEWEL = ('gloves', 'amulet', 'ring')                  # 7.3 strefa 2
LEGACY_SLOT = {'head': 'helmet', 'ring': 'accessory'}       # założenie nowego zdejmuje stary slot

# 7.1 plecak: start 5; +5 za $ (poziomy 5..25), +5 za 💎 (po wykupieniu $) → max 15
BAG_START = 20   # plecak 20 miejsc na start (wcześniej 5); rozszerzenia $/💎 dalej działają
BAG_CASH = ((5, 500), (10, 1500), (15, 5000), (20, 15000), (25, 50000))
BAG_DIA = (50, 100, 200, 400, 800)

# 7.2 tiery: poziom wymagany, cena; bazowy bonus jednej części na lvl 1 (interpretacja — raport)
TIERS = {
    1: dict(color='grey', level=1, cash=400, dia=0),
    2: dict(color='green', level=5, cash=1500, dia=0),
    3: dict(color='blue', level=10, cash=6000, dia=0, alt=(3000, 15)),   # $ albo $+💎
    4: dict(color='purple', level=15, cash=20000, dia=60),
}
# Sprzedaż z plecaka: cena losowa w widełkach zależnych od tieru i sumy bonusów (pokazywanych przed sprzedażą).
SELL_BASE = {1: 80, 2: 300, 3: 1200, 4: 4000}
SELL_PER_POINT = 15
SELL_SPREAD = (0.75, 1.25)

def sell_range(tier, bonus):
    mid = SELL_BASE[tier] + SELL_PER_POINT * sum(max(0, b) for b in bonus)
    return round(mid * SELL_SPREAD[0]), round(mid * SELL_SPREAD[1])

# 9 setów: T1×3, T2×2, T3×2, T4×2. bonus: lista (stat, wartość); 'main' = statystyka klasowa
SETS = [
    dict(id='uliczny', tier=1, bonus=[(0, 3)]),
    dict(id='akademicki', tier=1, bonus=[(1, 3)]),
    dict(id='sprinterski', tier=1, bonus=[(2, 3)]),
    dict(id='portowy', tier=2, bonus=[(0, 4), (3, 3)]),
    dict(id='cienia', tier=2, bonus=[(2, 4), (4, 3)]),
    dict(id='mistrzowski', tier=3, bonus=[('main', 7)]),
    dict(id='gwardyjski', tier=3, bonus=[('main', 7)]),
    dict(id='legendarny', tier=4, bonus=None),
    dict(id='cesarski', tier=4, bonus=None),
]
T4_MODES = {'A': [('all', 5)], 'B': [('main', 12)]}
SET_BONUS = 0.30         # komplet 8 części
SCALE_PER_LVL = 0.02     # bonus × (1 + 0.02·(lvl−1))
CLASS_MAIN = {'bokser': 0, 'obronca': 1, 'szybki': 2}
CRAFT_COST = {1: (500, 0), 2: (2000, 0), 3: (10000, 20)}
COUPONS = {'xp': (3000, 15), 'instant': (1500, 8), 'contract': (2000, 10)}
COUPON_MAX = 100
XP_BOOST_MS = 3600 * 1000
ROTATION_MS = 6 * 3600 * 1000
# Sklep 12 ofert: 8 pancerz + 4 biżuteria/broń; każde miejsce z szansą COUPON_CHANCE pokazuje kupon zamiast przedmiotu.
# Oferta widoczna przed zakupem (konkretny produkt, stała cena) — to nie jest lootbox.
SHOP_ZONES = (8, 4)
COUPON_CHANCE = 0.2
REFRESH_CASH = 50   # ręczne odświeżenie oferty za gotówkę (bez limitu)
# 7.6 przelicznik (tylko wyświetlanie; zakupy domyślnie OFF) — kursy stałe względem PLN
RATES = {'PLN': 1.0, 'EUR': 0.23, 'USD': 0.25, 'GBP': 0.20}
SYMBOL = {'PLN': 'zł', 'EUR': '€', 'USD': '$', 'GBP': '£'}
LANGS = ('pl', 'en', 'de', 'fr')

ITEMS = [dict(id=f"{st['id']}-{sl}", set=st['id'], slot=sl, tier=st['tier']) for st in SETS for sl in SLOTS]
BY_ID = {i['id']: i for i in ITEMS}
SET_BY_ID = {st['id']: st for st in SETS}

_I18N = {}
def strings(lang):
    if lang not in _I18N:
        _I18N[lang] = json.loads((Path(__file__).parent / 'i18n' / f'{lang}.json').read_text(encoding='utf-8'))
    return _I18N[lang]

def tr(lang, key, **kw):
    s = strings(lang).get(key) or strings('pl').get(key) or key
    return s.format(**kw) if kw else s

def pick_lang(header, account_lang=None):
    """Konto ma pierwszeństwo, potem Accept-Language (pierwszy obsługiwany), domyślnie pl."""
    if account_lang in LANGS:
        return account_lang
    for part in (header or '').split(','):
        code = part.split(';')[0].strip().lower()[:2]
        if code in LANGS:
            return code
    return 'pl'

def lvl_of(s, E):
    return E.level(s.get('xp', 0))

def main_stat(s):
    return CLASS_MAIN.get(s.get('cls'), max(range(5), key=lambda i: s['stats'][i]))

def piece_bonus(item, s, E, mode=None):
    st = SET_BY_ID[item['set']]
    spec = T4_MODES[mode or 'A'] if st['tier'] == 4 else st['bonus']
    v = [0.0] * 5
    for k, n in spec:
        for i in (range(5) if k == 'all' else [main_stat(s) if k == 'main' else k]):
            v[i] += n
    f = 1 + SCALE_PER_LVL * (lvl_of(s, E) - 1)
    return [x * f for x in v]

def worn(s):
    return {sl: BY_ID[i] for sl, i in (s.get('equipped') or {}).items() if sl in SLOTS and i in BY_ID}

def full_sets(s):
    w = worn(s)
    sets = {i['set'] for i in w.values()}
    return [x for x in sets if all(w.get(sl, {}).get('set') == x for sl in SLOTS)]

def bonus(s, E):
    """Hook do E.effective: suma bonusów setów (zaokrąglona per statystyka), komplet ×1.3."""
    full = set(full_sets(s))
    tot = [0.0] * 5
    for sl, it in worn(s).items():
        b = piece_bonus(it, s, E, (s.get('gearModes') or {}).get(sl))
        m = 1 + SET_BONUS if it['set'] in full else 1
        tot = [a + x * m for a, x in zip(tot, b)]
    return [round(x) for x in tot]

def capacity(s):
    u = s.get('bagUnlocks') or {}
    return BAG_START + u.get('cash', 0) + u.get('dia', 0)

def rng(*parts):
    h = hashlib.sha256(':'.join(map(str, parts)).encode()).digest()
    return random.Random(int.from_bytes(h[:8], 'big'))

def window(now):
    return now // ROTATION_MS

def shop_key(s, now):
    """Klucz oferty: okno 6 h + liczba płatnych odświeżeń w tym oknie."""
    w = window(now)
    return f"{w}:{(s.get('shopRefresh') or {}).get(str(w), 0)}"

def offer(cid, s, now, E):
    """12 ofert (8 pancerz + 4 biżuteria/broń) z puli dla poziomu; stałe na okno 6 h (lub do płatnego odświeżenia).
    Każde miejsce może zamiast przedmiotu wylosować kupon (szansa COUPON_CHANCE, może być kilka)."""
    lvl = lvl_of(s, E); key = shop_key(s, now)
    w, n = key.split(':')
    r = rng('shop', cid, w) if n == '0' else rng('shop', cid, w, 'refresh', n)  # bez odświeżeń = dotychczasowe ziarno
    ok = [i for i in ITEMS if TIERS[i['tier']]['level'] <= lvl]
    out = []
    for zone, n in zip((ZONE_ARMOR, ZONE_JEWEL), SHOP_ZONES):
        pool = [i for i in ok if i['slot'] in zone]
        z = 1 if zone is ZONE_ARMOR else 2
        for i in r.sample(pool, min(n, len(pool))):
            if r.random() < COUPON_CHANCE:
                out.append(dict(zone=z, kind='coupon', coupon=r.choice(sorted(COUPONS))))
            else:
                out.append(dict(zone=z, kind='item', **i))
    return out

def craft_result(cid, s, tier):
    return rng('craft', cid, s.get('sequence', 0), tier).choice([i for i in ITEMS if i['tier'] == tier + 1])


class Equip(BaseModel):
    item: str
    mode: Optional[Literal['A', 'B']] = None

class Unequip(BaseModel):
    slot: str

class Unlock(BaseModel):
    currency: Literal['cash', 'diamonds']

class Craft(BaseModel):
    items: list[str]

class Sell(BaseModel):
    item: str

class Buy(BaseModel):
    offer: Optional[int] = None
    coupon: Optional[Literal['xp', 'instant', 'contract']] = None
    pay: Literal['cash', 'mixed', 'diamonds'] = 'cash'

class UseCoupon(BaseModel):
    type: Literal['xp', 'instant', 'contract']
    task: Optional[Literal['contract', 'training']] = None

class Language(BaseModel):
    language: Literal['pl', 'en', 'de', 'fr']


def install(app, d, E):
    db, now, fail, world, own, auth, audit = d.db, d.now, d.fail, d.world, d.own, d.auth, d.audit
    E.GEAR_HOOK[0] = lambda s: bonus(s, E)
    with db.tx() as c:
        if 'language' not in {r[1] for r in c.execute('PRAGMA table_info(accounts)')}:
            c.execute('ALTER TABLE accounts ADD COLUMN language TEXT')  # 7.6 migracja addytywna

    def lang(request, u):
        acc = None
        try:
            acc = u['language']
        except (KeyError, IndexError, TypeError):
            with db.read() as c:
                r = c.execute('SELECT language FROM accounts WHERE id=?', (u['id'],)).fetchone()
                acc = r['language'] if r else None
        return pick_lang(request.headers.get('accept-language'), acc)

    def weapon_of(key):
        from . import combat as CB   # leniwy import (combat importuje gear)
        lo, hi, _ = CB.WEAPON[key]; return dict(dmgMin=lo, dmgMax=hi)

    def item_view(it, L, s, sl=None):
        v = dict(id=it['id'], set=it['set'], slot=it['slot'], tier=it['tier'], color=TIERS[it['tier']]['color'],
                 name=f"{tr(L, 'slot.' + it['slot'])} · {tr(L, 'set.' + it['set'])}",
                 bonus=[round(x) for x in piece_bonus(it, s, E, (s.get('gearModes') or {}).get(sl) if sl else None)])
        lo, hi = sell_range(it['tier'], v['bonus'])
        v['sell'] = dict(min=lo, max=hi)
        if it['slot'] == 'gloves':
            v.update(weapon_of(it['tier']))   # QA 4: Rękawice = Broń (Combat 3.0)
        return v

    # QA 2: unikaty z Lochu (stary katalog E.DUNGEON_ITEMS) — widoczne i zakładane w Ekwipunku
    UNIQUE_SLOT = {'helmet': 'head', 'accessory': 'ring', 'gloves': 'gloves', 'shoes': 'shoes'}
    UNIQUES = {i['id']: i for i in E.DUNGEON_ITEMS}

    def unique_view(iid, s):
        u = UNIQUES[iid]; sl = UNIQUE_SLOT.get(u['slot'], u['slot'])
        v = dict(id=iid, name=u['name'], slot=sl, unique=True, bonus=list(u.get('bonus') or [0] * 5),
                 equipped=(s.get('equipped') or {}).get(sl) == iid)
        if sl == 'gloves':
            v.update(weapon_of(2))
        return v

    def stat_breakdown(s):
        """Skąd się bierze każda statystyka: baza (trening) + zestawy ekwipunku + unikaty z Lochu + reszta (np. Pływanie) = efektywna."""
        base = [float(x) for x in s['stats']]
        sets = bonus(s, E)
        uniq = [0.0] * 5
        for iid in (s.get('equipped') or {}).values():
            if iid in UNIQUES:
                uniq = [a + b for a, b in zip(uniq, UNIQUES[iid].get('bonus') or [0] * 5)]
        tot = E.effective(s)
        return [dict(stat=i, name=E.STAT_NAMES[i], base=round(base[i], 1), gear=sets[i], unique=round(uniq[i], 1),
                     other=round(tot[i] - base[i] - sets[i] - uniq[i], 1), total=round(tot[i], 1)) for i in range(5)]

    def view(s, L):
        eq = s.get('equipped') or {}
        return dict(slots=[dict(slot=sl, label=tr(L, 'slot.' + sl), item=item_view(BY_ID[eq[sl]], L, s, sl) if eq.get(sl) in BY_ID else None,
                                legacy=eq.get(sl) if eq.get(sl) and eq.get(sl) not in BY_ID else None,
                                mode=(s.get('gearModes') or {}).get(sl)) for sl in SLOTS],
                    backpack=[item_view(BY_ID[i], L, s) if i in BY_ID else dict(id=i, legacy=True) for i in s.get('backpack', [])],
                    uniques=[unique_view(i, s) for i in dict.fromkeys(list(s.get('inventory') or []) + list(s.get('backpack') or []) + list((s.get('equipped') or {}).values())) if i in UNIQUES],
                    fists=weapon_of('fists'),
                    capacity=capacity(s), maxCapacity=BAG_START + len(BAG_CASH) + len(BAG_DIA),
                    fullSets=full_sets(s), gearBonus=bonus(s, E), statBreakdown=stat_breakdown(s), coupons=s.get('coupons', {}),
                    xpBoostUntil=s.get('xpBoostUntil', 0), contractBoost=bool(s.get('contractBoost')),
                    diamonds=int(s.get('diamonds') or 0), cash=s['cash'])

    def load(c, u, wid):
        world(c, wid, True); ch = own(c, u['id'], wid); s = json.loads(ch['state_json'])
        s.setdefault('backpack', []); s.setdefault('coupons', {}); s['cls'] = ch['class_type'] if 'class_type' in ch.keys() else s.get('cls')
        return ch, s

    def save(c, ch, s):
        c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))

    def pay(s, L, cash=0, dia=0):
        if s['cash'] < cash:
            fail(409, tr(L, 'err.cash'))
        if int(s.get('diamonds') or 0) < dia:
            fail(409, tr(L, 'err.diamonds'))
        s['cash'] -= cash; s['diamonds'] = int(s.get('diamonds') or 0) - dia

    @app.get('/api/worlds/{wid}/gear')
    def gear(wid: int, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            return view(s, L)

    @app.post('/api/worlds/{wid}/gear/equip')
    def equip(wid: int, data: Equip, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            it = BY_ID.get(data.item)
            if not it and data.item in UNIQUES:   # QA 2: zakładanie unikatu z Lochu
                owned = data.item in (s.get('inventory') or []) or data.item in s['backpack']
                if not owned:
                    fail(409, tr(L, 'err.not_owned'))
                sl = UNIQUE_SLOT.get(UNIQUES[data.item]['slot'], UNIQUES[data.item]['slot']); eq = s['equipped']
                if eq.get(sl) in BY_ID:
                    s['backpack'].append(eq[sl])
                elif eq.get(sl) and eq[sl] not in s['inventory']:
                    s['inventory'].append(eq[sl])
                if data.item in s['backpack']:
                    s['backpack'].remove(data.item)
                    s['inventory'].append(data.item) if data.item not in s['inventory'] else None
                old = LEGACY_SLOT.get(sl)
                if old and old in eq:
                    eq.pop(old)
                eq[sl] = data.item; (s.get('gearModes') or {}).pop(sl, None)
                save(c, ch, s)
                return dict(message=f"Założono: {UNIQUES[data.item]['name']}.", gear=view(s, L))
            if not it:
                fail(409, tr(L, 'err.unknown'))
            if data.item not in s['backpack']:
                fail(409, tr(L, 'err.not_owned'))
            if lvl_of(s, E) < TIERS[it['tier']]['level']:
                fail(409, tr(L, 'err.level', level=TIERS[it['tier']]['level']))
            if it['tier'] == 4 and not data.mode:
                fail(409, tr(L, 'err.mode'))
            sl = it['slot']; eq = s['equipped']
            s['backpack'].remove(data.item)
            if eq.get(sl) in BY_ID:
                s['backpack'].append(eq[sl])
            elif eq.get(sl):
                s['inventory'].append(eq[sl]) if eq[sl] not in s['inventory'] else None
            old = LEGACY_SLOT.get(sl)
            if old and old in eq:
                eq.pop(old)   # stary helmet/accessory zdejmowany (zostaje w kolekcji)
            eq[sl] = data.item
            s.setdefault('gearModes', {})
            if it['tier'] == 4:
                s['gearModes'][sl] = data.mode
            else:
                s['gearModes'].pop(sl, None)
            save(c, ch, s)
            return dict(message=tr(L, 'ok.equip', name=item_view(it, L, s)['name']), gear=view(s, L))

    @app.post('/api/worlds/{wid}/gear/unequip')
    def unequip(wid: int, data: Unequip, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            cur = s['equipped'].get(data.slot)
            if data.slot not in SLOTS or cur not in BY_ID:
                fail(409, tr(L, 'err.empty'))
            if len(s['backpack']) >= capacity(s):
                fail(409, tr(L, 'err.full'))
            s['backpack'].append(s['equipped'].pop(data.slot)); (s.get('gearModes') or {}).pop(data.slot, None)
            save(c, ch, s)
            return dict(message=tr(L, 'ok.unequip'), gear=view(s, L))

    @app.post('/api/worlds/{wid}/gear/bag/unlock')
    def unlock(wid: int, data: Unlock, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            un = s.setdefault('bagUnlocks', {}); nc, nd = un.get('cash', 0), un.get('dia', 0)
            if data.currency == 'cash':
                if nc >= len(BAG_CASH):
                    fail(409, tr(L, 'err.bag_cash_max'))
                lv, cost = BAG_CASH[nc]
                if lvl_of(s, E) < lv:
                    fail(409, tr(L, 'err.level', level=lv))
                pay(s, L, cash=cost); un['cash'] = nc + 1
            else:
                if nc < len(BAG_CASH):
                    fail(409, tr(L, 'err.bag_cash_first'))
                if nd >= len(BAG_DIA):
                    fail(409, tr(L, 'err.bag_max'))
                pay(s, L, dia=BAG_DIA[nd]); un['dia'] = nd + 1
            save(c, ch, s)
            return dict(message=tr(L, 'ok.unlock', n=capacity(s)), gear=view(s, L))

    @app.post('/api/worlds/{wid}/gear/craft')
    def craft(wid: int, data: Craft, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            if len(data.items) != 3 or any(i not in BY_ID for i in data.items):
                fail(409, tr(L, 'err.craft3'))
            tiers = {BY_ID[i]['tier'] for i in data.items}
            if len(tiers) != 1:
                fail(409, tr(L, 'err.craft_tier'))
            t = tiers.pop()
            if t >= 4:
                fail(409, tr(L, 'err.craft_max'))
            bag = list(s['backpack'])
            for i in data.items:
                if i not in bag:
                    fail(409, tr(L, 'err.not_owned'))
                bag.remove(i)
            cash, dia = CRAFT_COST[t]
            pay(s, L, cash=cash, dia=dia)
            res = craft_result(ch['id'], s, t)   # 7.4 decyzja usera: wynik losowy (deterministyczny seed)
            s['sequence'] = s.get('sequence', 0) + 1
            s['backpack'] = bag + [res['id']]
            audit(c, u['id'], 'gear.craft', dict(character_id=ch['id'], used=data.items, result=res['id'], cash=cash, dia=dia))
            save(c, ch, s)
            return dict(message=tr(L, 'ok.craft', name=item_view(res, L, s)['name']), result=item_view(res, L, s), gear=view(s, L))

    @app.get('/api/worlds/{wid}/gear/shop')
    def shop(wid: int, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            return shop_view(ch, s, L)

    def shop_view(ch, s, L):
        w = window(now()); bought = (s.get('shopBought') or {}).get(shop_key(s, now()), [])
        items = []
        for n, it in enumerate(offer(ch['id'], s, now(), E)):
            if it['kind'] == 'coupon':
                k = it['coupon']; cash, dia = COUPONS[k]
                items.append(dict(offer=n, zone=it['zone'], kind='coupon', coupon=k, name=tr(L, 'coupon.' + k), sold=n in bought,
                                  price=dict(cash=cash, diamonds=dia), owned=s['coupons'].get(k, 0)))
                continue
            t = TIERS[it['tier']]
            items.append(dict(offer=n, zone=it['zone'], kind='item', sold=n in bought, price=dict(cash=t['cash'], diamonds=t['dia']),
                              alt=dict(cash=t['alt'][0], diamonds=t['alt'][1]) if t.get('alt') else None,
                              level=t['level'], **item_view(BY_ID[it['id']], L, s)))
        return dict(name=tr(L, 'shop.name'), zones={1: tr(L, 'shop.zone1'), 2: tr(L, 'shop.zone2')}, items=items,
                    coupons=[dict(type=k, name=tr(L, 'coupon.' + k), cash=v[0], diamonds=v[1], owned=s['coupons'].get(k, 0)) for k, v in COUPONS.items()],
                    resetAt=(w + 1) * ROTATION_MS, capacity=capacity(s), used=len(s['backpack']),
                    refreshCost=REFRESH_CASH, refreshes=(s.get('shopRefresh') or {}).get(str(w), 0))

    @app.post('/api/worlds/{wid}/gear/sell')
    def sell(wid: int, data: Sell, request: Request, u=Depends_auth(auth)):
        """Sprzedaż przedmiotu z plecaka za losową kwotę z widełek sell_range (unikatów z Lochu nie sprzedajemy)."""
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            if data.item not in BY_ID or data.item not in s.get('backpack', []):
                fail(409, 'Tego przedmiotu nie ma w plecaku.')
            it = BY_ID[data.item]
            v = item_view(it, L, s)
            lo, hi = v['sell']['min'], v['sell']['max']
            price = random.randint(lo, hi)
            s['backpack'].remove(data.item)
            s['cash'] += price
            save(c, ch, s)
            return dict(message=f"💰 Sprzedano {v['name']} za {price} $ (widełki {lo}–{hi} $).", price=price, gear=view(s, L))

    @app.post('/api/worlds/{wid}/gear/shop/refresh')
    def shop_refresh(wid: int, request: Request, u=Depends_auth(auth)):
        """Nowe losowanie oferty za REFRESH_CASH $ (kupione wcześniej oferty nie przechodzą)."""
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            if (s.get('buildings') or {}).get('club', 0) < 1:
                fail(409, tr(L, 'err.club'))
            pay(s, L, cash=REFRESH_CASH)
            w = str(window(now())); sr = s.setdefault('shopRefresh', {})
            for k in [k for k in sr if k != w]:
                sr.pop(k)
            sr[w] = sr.get(w, 0) + 1
            save(c, ch, s)
            return dict(message=f'🔄 Nowa oferta (−{REFRESH_CASH} $).', shop=shop_view(ch, s, L))

    @app.post('/api/worlds/{wid}/gear/shop/buy')
    def buy(wid: int, data: Buy, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            if (s.get('buildings') or {}).get('club', 0) < 1:
                fail(409, tr(L, 'err.club'))
            if data.coupon:
                cash, dia = COUPONS[data.coupon]
                if s['coupons'].get(data.coupon, 0) >= COUPON_MAX:
                    fail(409, tr(L, 'err.coupon_max'))
                pay(s, L, **(dict(dia=dia) if data.pay == 'diamonds' else dict(cash=cash)))
                s['coupons'][data.coupon] = s['coupons'].get(data.coupon, 0) + 1
                name = tr(L, 'coupon.' + data.coupon)
            else:
                offers = offer(ch['id'], s, now(), E)
                if data.offer is None or not 0 <= data.offer < len(offers):
                    fail(409, tr(L, 'err.unknown'))
                w = shop_key(s, now()); sb = s.setdefault('shopBought', {})
                for k in [k for k in sb if k != w]:
                    sb.pop(k)
                if data.offer in sb.get(w, []):
                    fail(409, tr(L, 'err.sold'))
                if offers[data.offer]['kind'] == 'coupon':
                    k = offers[data.offer]['coupon']; cash, dia = COUPONS[k]
                    if s['coupons'].get(k, 0) >= COUPON_MAX:
                        fail(409, tr(L, 'err.coupon_max'))
                    pay(s, L, **(dict(dia=dia) if data.pay == 'diamonds' else dict(cash=cash)))
                    s['coupons'][k] = s['coupons'].get(k, 0) + 1
                    sb.setdefault(w, []).append(data.offer)
                    save(c, ch, s)
                    return dict(message=tr(L, 'ok.buy', name=tr(L, 'coupon.' + k)), shop=shop_view(ch, s, L), gear=view(s, L))
                if len(s['backpack']) >= capacity(s):
                    fail(409, tr(L, 'err.full'))
                it = offers[data.offer]; t = TIERS[it['tier']]
                if data.pay == 'mixed' and t.get('alt'):
                    pay(s, L, cash=t['alt'][0], dia=t['alt'][1])
                else:
                    pay(s, L, cash=t['cash'], dia=t['dia'])
                sb.setdefault(w, []).append(data.offer); s['backpack'].append(it['id'])
                name = item_view(BY_ID[it['id']], L, s)['name']
            save(c, ch, s)
            return dict(message=tr(L, 'ok.buy', name=name), shop=shop_view(ch, s, L), gear=view(s, L))

    @app.post('/api/worlds/{wid}/gear/coupon/use')
    def use(wid: int, data: UseCoupon, request: Request, u=Depends_auth(auth)):
        L = lang(request, u)
        with db.tx() as c:
            ch, s = load(c, u, wid)
            if s['coupons'].get(data.type, 0) < 1:
                fail(409, tr(L, 'err.no_coupon'))
            t = now()
            if data.type == 'xp':
                s['xpBoostUntil'] = max(t, s.get('xpBoostUntil', 0)) + XP_BOOST_MS
            elif data.type == 'contract':
                if s.get('contractBoost'):
                    fail(409, tr(L, 'err.boost_active'))
                s['contractBoost'] = 1
            else:
                key = {'contract': 'contracts', 'training': 'training'}.get(data.task or 'contract')
                run = [x for x in s.get(key, []) if x.get('end', 0) > t]
                if not run:
                    fail(409, tr(L, 'err.no_task'))
                job = min(run, key=lambda x: x['end'])
                shift = job['end'] - t
                for x in s[key]:   # kolejka przesuwa się razem z pominiętym zadaniem
                    if x.get('end', 0) >= job['end']:
                        x['end'] -= shift
                        if 'start' in x and x is not job:
                            x['start'] = max(t, x['start'] - shift)
            s['coupons'][data.type] -= 1
            save(c, ch, s)
            return dict(message=tr(L, 'ok.coupon.' + data.type), gear=view(s, L))

    @app.get('/api/i18n/{code}')
    def i18n(code: str):
        if code not in LANGS:
            fail(404, 'Nie znaleziono zasobu.')
        return dict(language=code, strings=strings(code))

    @app.post('/api/account/language')
    def set_language(data: Language, u=Depends_auth(auth)):
        with db.tx() as c:
            c.execute('UPDATE accounts SET language=? WHERE id=?', (data.language, u['id']))
        return dict(language=data.language)

    @app.get('/api/shop/prices')
    def prices(currency: str = 'PLN'):
        from . import shop as SH
        cur = currency.upper()
        if cur not in RATES:
            fail(422, 'Nieobsługiwana waluta.')
        out = []
        for sku, v in SH.SKU.items():
            amt = round(v['cents'] * RATES[cur]) / 100
            out.append(dict(sku=sku, cents=round(v['cents'] * RATES[cur]), amount=amt, display=f'{amt:.2f} {SYMBOL[cur]}'))
        return dict(currency=cur, rate=RATES[cur], displayOnly=True, prices=out)

    def after_action(s, action, xp0, cash0, t):
        """Wołane z /actions: kupon XP (×2 XP z akcji) i kupon Kontrakt (+10% $ i XP następnego kontraktu)."""
        dxp, dcash = s['xp'] - xp0, s['cash'] - cash0
        if action == 'claim_contract' and s.get('contractBoost') and (dxp > 0 or dcash > 0):
            s['cash'] += round(max(0, dcash) * 0.10); s['xp'] += round(max(0, dxp) * 0.10); s.pop('contractBoost')
            dxp = s['xp'] - xp0
        if s.get('xpBoostUntil', 0) > t and dxp > 0:
            s['xp'] += dxp

    return dict(after_action=after_action)


def Depends_auth(auth):
    from fastapi import Depends
    return Depends(auth)
