"""8.4 GDD v3.1 — Battle Pass miesięczny.

- Sezon = miesiąc kalendarzowy UTC (reset 1. dnia o 00:00 UTC), klucz 'YYYY-MM'.
- 30 poziomów po 100 XP. XP przepustki z: pracy NPC, PvP, Lochów, rozbudowy budynków.
- Ścieżka Darmowa i Premium. Premium za 400💎 (💎 z nagród). Cena 29,99 zł jest tylko informacją:
  płatności PLN są zablokowane (zakupy domyślnie OFF), więc SKU nie jest sprzedawane.
- Unikaty Premium (ramki, outfity, skórki aut, psy, konie) mają id z kluczem sezonu, więc nigdy się nie powtarzają.
  Motyw miesiąca pochodzi z rotacji 12 motywów.
- Bez losowości: każda nagroda jest znana z góry.
"""
import json
import time
from typing import Literal
from fastapi import Depends
from pydantic import BaseModel, Field

LEVELS = 30
XP_PER_LEVEL = 100
PREMIUM_DIAMONDS = 400
PREMIUM_PLN = '29,99 zł'
XP = {'npc': 10, 'pvp': 15, 'dungeon': 20, 'build': 30}
THEMES = ['Zimowy Ring', 'Neonowe Miasto', 'Wiosenny Sprint', 'Portowa Mgła', 'Złota Arena', 'Letni Bulwar',
          'Upalny Asfalt', 'Nocne Wyścigi', 'Jesienna Liga', 'Stalowy Port', 'Mroźna Gwardia', 'Gala Mistrzów']  # styczeń…grudzień

SCHEMA = """
CREATE TABLE IF NOT EXISTS battlepass(
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  season TEXT NOT NULL,
  xp INTEGER NOT NULL DEFAULT 0,
  premium INTEGER NOT NULL DEFAULT 0,
  claimed TEXT NOT NULL DEFAULT '[]',
  PRIMARY KEY(character_id, season)
);
"""


def season_of(t):
    return time.strftime('%Y-%m', time.gmtime(t / 1000))


def season_end(t):
    y, m = time.gmtime(t / 1000)[:2]
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    import calendar
    return calendar.timegm((y, m, 1, 0, 0, 0)) * 1000


def theme(season):
    return THEMES[int(season[5:7]) - 1]


def free_reward(lv):
    if lv % 10 == 0:
        return dict(kind='diamonds', amount=25)
    if lv % 5 == 0:
        return dict(kind='coupon', coupon='xp', amount=1)
    return dict(kind='cash', amount=250 * lv) if lv % 2 else dict(kind='diamonds', amount=5)


def premium_reward(lv, season):
    th = theme(season)
    uniq = {5: ('frame', f'bp-{season}-frame', f'Ramka „{th}”'),
            10: ('cosmetic', f'outfit-bp-{season}', f'Outfit „{th}”'),
            15: ('cosmetic', f'car-skin-bp-{season}', f'Skórka auta „{th}”'),
            20: ('dog', f'kennel-bp-{season}', f'Pies „{th}”'),
            25: ('horse', f'stable-bp-{season}', f'Koń „{th}”'),
            30: ('frame', f'bp-{season}-legend', f'Ramka Legendy „{th}”')}
    if lv in uniq:
        k, i, name = uniq[lv]
        return dict(kind=k, id=i, name=name, unique=True)
    if lv % 3 == 0:
        return dict(kind='coupon', coupon=('instant', 'contract')[lv // 3 % 2], amount=1)
    return dict(kind='diamonds', amount=10) if lv % 2 else dict(kind='cash', amount=500 * lv)


def grant(s, r):
    k = r['kind']
    if k == 'cash':
        s['cash'] += r['amount']
    elif k == 'diamonds':
        s['diamonds'] = int(s.get('diamonds') or 0) + r['amount']
    elif k == 'coupon':
        cp = s.setdefault('coupons', {})
        cp[r['coupon']] = min(100, cp.get(r['coupon'], 0) + r['amount'])
    elif k == 'frame':
        s['frames'] = sorted(set((s.get('frames') or []) + [r['id']]))
    elif k == 'cosmetic':
        s.setdefault('cosmetics', [])
        if r['id'] not in s['cosmetics']:
            s['cosmetics'].append(r['id'])
    elif k in ('dog', 'horse'):
        e = dict(key=r['id'], breed='battlepass', name=r['name'], speed=9, stamina=9, gen=1, premium=True)
        s.setdefault('dogs' if k == 'dog' else 'horses', {})[r['id']] = e


class Claim(BaseModel):
    level: int = Field(ge=1, le=LEVELS)
    track: Literal['free', 'premium']


def install(app, d, E):
    db, now, fail, world, own, auth, audit = d.db, d.now, d.fail, d.world, d.own, d.auth, d.audit
    with db.tx() as c:
        c.executescript(SCHEMA)

    def row(c, cid, season):
        r = c.execute('SELECT * FROM battlepass WHERE character_id=? AND season=?', (cid, season)).fetchone()
        return dict(r) if r else dict(character_id=cid, season=season, xp=0, premium=0, claimed='[]')

    def put(c, r):
        c.execute('INSERT INTO battlepass(character_id,season,xp,premium,claimed) VALUES(?,?,?,?,?) ON CONFLICT(character_id,season) '
                  'DO UPDATE SET xp=excluded.xp,premium=excluded.premium,claimed=excluded.claimed',
                  (r['character_id'], r['season'], r['xp'], r['premium'], r['claimed']))

    def add_xp(c, cid, source):
        """Hak dla NPC/PvP/Lochu/rozbudowy. XP ponad poziom 30 nie przepada w raporcie, ale nie daje nagród."""
        r = row(c, cid, season_of(now()))
        r['xp'] = min(LEVELS * XP_PER_LEVEL, r['xp'] + XP.get(source, 0))
        put(c, r)

    E.BP_HOOK[0] = add_xp

    def view(r, s):
        claimed = set(json.loads(r['claimed']))
        lvl = min(LEVELS, r['xp'] // XP_PER_LEVEL)
        tracks = [dict(level=lv, free=dict(free_reward(lv), claimed=f'free:{lv}' in claimed),
                       premium=dict(premium_reward(lv, r['season']), claimed=f'premium:{lv}' in claimed)) for lv in range(1, LEVELS + 1)]
        return dict(season=r['season'], theme=theme(r['season']), endsAt=season_end(now()), xp=r['xp'], level=lvl,
                    xpPerLevel=XP_PER_LEVEL, levels=LEVELS, premium=bool(r['premium']), xpSources=XP,
                    price=dict(diamonds=PREMIUM_DIAMONDS, pln=PREMIUM_PLN, plnEnabled=False),
                    diamonds=int(s.get('diamonds') or 0), tracks=tracks)

    def load(c, u, wid):
        world(c, wid, True)
        ch = own(c, u['id'], wid)
        return ch, json.loads(ch['state_json'])

    def save(c, ch, s):
        c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))

    @app.get('/api/worlds/{wid}/battlepass')
    def bp_get(wid: int, u=Depends(auth)):
        with db.tx() as c:
            ch, s = load(c, u, wid)
            return view(row(c, ch['id'], season_of(now())), s)

    @app.post('/api/worlds/{wid}/battlepass/premium')
    def bp_premium(wid: int, u=Depends(auth)):
        with db.tx() as c:
            ch, s = load(c, u, wid)
            r = row(c, ch['id'], season_of(now()))
            if r['premium']:
                fail(409, 'Masz już Premium w tym sezonie.')
            if int(s.get('diamonds') or 0) < PREMIUM_DIAMONDS:
                fail(409, 'Premium kosztuje 400💎.')
            s['diamonds'] = int(s['diamonds']) - PREMIUM_DIAMONDS
            r['premium'] = 1
            put(c, r); save(c, ch, s)
            audit(c, u['id'], 'battlepass.premium', dict(character_id=ch['id'], season=r['season'], diamonds=PREMIUM_DIAMONDS))
            return view(r, s)

    @app.post('/api/worlds/{wid}/battlepass/claim')
    def bp_claim(wid: int, data: Claim, u=Depends(auth)):
        with db.tx() as c:
            ch, s = load(c, u, wid)
            r = row(c, ch['id'], season_of(now()))
            claimed = json.loads(r['claimed'])
            key = f'{data.track}:{data.level}'
            if r['xp'] // XP_PER_LEVEL < data.level:
                fail(409, 'Ten poziom przepustki nie jest jeszcze odblokowany.')
            if data.track == 'premium' and not r['premium']:
                fail(409, 'Ta nagroda wymaga Premium.')
            if key in claimed:
                fail(409, 'Nagroda została już odebrana.')
            rew = free_reward(data.level) if data.track == 'free' else premium_reward(data.level, r['season'])
            grant(s, rew)
            claimed.append(key); r['claimed'] = json.dumps(claimed)
            put(c, r); save(c, ch, s)
            return dict(reward=rew, battlepass=view(r, s))

    return dict(add_xp=add_xp, season_of=season_of)
