"""2.2 GDD v3.1: 12 lokacji usługowych — tu pracują NPC i zarabiają $ za godzinę.

Moduł na razie tylko katalog + odczyt (GET). Odblokowanie za gotówkę, przydział NPC,
dojazd i naliczanie zarobku dochodzą w zadaniach 2.3/2.4 (npc.py).

Emocje na godzinę pracy: energy/mood ujemne = zużycie, dodatnie = regeneracja.
Głód zawsze rośnie: +3 przy pracy fizycznej (zużywa energię), +2 w pozostałych.
"""
import hashlib
import json
import re
from fastapi import Depends, Request

# d = dzielnica (travel.DISTRICTS); level = wymagany poziom postaci; unlock = jednorazowy koszt odblokowania $
SERVICES = [
    dict(id='biblioteka', name='Biblioteka',           icon='📚', d=1, rate=95,  energy=0,  mood=+1, hunger=2, level=10, unlock=10000),
    dict(id='sprzatanie', name='Firma sprzątająca',    icon='🧹', d=2, rate=80,  energy=-5, mood=0,  hunger=3, level=3,  unlock=0),
    dict(id='kurier',     name='Firma kurierska',      icon='🚚', d=2, rate=100, energy=-4, mood=0,  hunger=3, level=5,  unlock=2000),
    dict(id='minimarket', name='Mini-market',          icon='🏪', d=3, rate=50,  energy=0,  mood=-2, hunger=2, level=1,  unlock=0),
    dict(id='kawiarnia',  name='Kawiarnia Usługowa',   icon='☕', d=3, rate=60,  energy=-3, mood=-1, hunger=3, level=1,  unlock=0),
    dict(id='klinika',    name='Prywatna klinika',     icon='🏥', d=3, rate=200, energy=-6, mood=0,  hunger=3, level=15, unlock=25000),
    dict(id='callcenter', name='Call center',          icon='🏢', d=4, rate=90,  energy=0,  mood=-3, hunger=2, level=5,  unlock=2000),
    dict(id='marketing',  name='Agencja marketingowa', icon='👔', d=5, rate=150, energy=0,  mood=-3, hunger=2, level=10, unlock=10000),
    dict(id='grafika',    name='Studio graficzne',     icon='🎨', d=5, rate=180, energy=0,  mood=-1, hunger=2, level=15, unlock=25000),
    dict(id='park',       name='Park rozrywki',        icon='🎪', d=6, rate=160, energy=0,  mood=+2, hunger=2, level=20, unlock=50000),
    dict(id='warsztat',   name='Warsztat',             icon='🔧', d=7, rate=120, energy=-4, mood=0,  hunger=3, level=7,  unlock=5000),
    dict(id='hotel',      name='Hotel butikowy',       icon='🏨', d=8, rate=220, energy=-5, mood=0,  hunger=3, level=20, unlock=50000),
]
# 2.2b GDD v3.1: stawka katalogowa to base_rate; zarobek = base_rate × popyt. `rate` zostaje jako alias (zgodność).
for _x in SERVICES:
    _x['base_rate'] = _x['rate']
BY_ID = {s['id']: s for s in SERVICES}

# 2.2b GDD v3.1: dynamiczny popyt „Żyjące Miasto” — 50–150%, zmiana co 6 h, deterministyczny (hash świat/usługa/okno),
# identyczny dla wszystkich graczy świata, bez zapisu w bazie. Zamrażany w zmianie NPC przy wysłaniu.
DEMAND_WINDOW_MS = 6 * 3_600_000
DEMAND_MIN, DEMAND_MAX = 0.50, 1.50


def demand(wid, sid, t):
    """Popyt usługi `sid` w świecie `wid` w chwili `t` (ms), zaokrąglony do 0,01."""
    w = int(t) // DEMAND_WINDOW_MS
    h = hashlib.sha256(f'{wid}:{sid}:{w}'.encode()).digest()
    return round(DEMAND_MIN + (DEMAND_MAX - DEMAND_MIN) * int.from_bytes(h[:4], 'big') / 2**32, 2)


def demand_board(wid, t):
    """Popyt teraz i w następnym oknie + moment zmiany + 3 najlepsze usługi (baner w UI)."""
    nxt = (int(t) // DEMAND_WINDOW_MS + 1) * DEMAND_WINDOW_MS
    now_d = {x['id']: demand(wid, x['id'], t) for x in SERVICES}
    top = sorted(SERVICES, key=lambda x: -now_d[x['id']])[:3]
    return dict(now=now_d, next={x['id']: demand(wid, x['id'], nxt) for x in SERVICES}, changesAt=nxt,
                top=[dict(id=x['id'], name=x['name'], icon=x['icon'], demand=now_d[x['id']]) for x in top])

# Lokacje regenerujące nastrój (Biblioteka +1, Park rozrywki +2) — NPC odpoczywa pracując.
REGEN = tuple(s['id'] for s in SERVICES if s['mood'] > 0)

# Transport NPC (egzekwowane w 2.4): minimalny czas dojazdu i globalny cooldown.
TRANSPORT_MIN_MS = 30_000          # min. 30 s dojazdu
COOLDOWN_AFTER = 10                # po 10 trasach z rzędu…
COOLDOWN_MS = 120_000              # …2 min przerwy


# 2.4 GDD v3.1: czas dojazdu = max(30 s, przystanki od Nadmorskiego × 60 s × współczynnik auta).
# Bez auta NPC jedzie autobusem (×2,0) i płaci bilet za każdy odcinek.
TRAVEL_FACTOR = {'mistrz': 0.6, 'suv': 0.7, 'sedan': 0.8, 'furgonetka': 0.85, 'van': 0.9, 'dostawczak': 1.2}  # 3.1 GDD v3.1
BUS_FACTOR = 2.0
HOP_MS = 60_000


def travel_ms(service, car, E, trait_factor=1.0, worn=False):
    """Czas jednego odcinka dojazdu NPC do usługi (ms). trait_factor: cecha „kierowca” = 0,8 (2.3b).

    3.3: auto zużyte w 100% traci przyspieszenie — współczynnik nie lepszy niż 1,0."""
    hops = E.HOPS.get(service['d'], 0)
    f = TRAVEL_FACTOR.get(car, 1.0) if car else BUS_FACTOR
    if car and worn:
        f = max(f, 1.0)
    return max(TRANSPORT_MIN_MS, int(hops * HOP_MS * f * trait_factor))


def unlocked_ids(s):
    """Usługi odblokowane przez gracza: darmowe (unlock=0) + kupione (s['servicesUnlocked'], od 2.3/2.4)."""
    bought = set(s.get('servicesUnlocked') or [])
    return {x['id'] for x in SERVICES if x['unlock'] == 0 or x['id'] in bought}


def view(s, level, board=None):
    """Katalog z perspektywy gracza: czy usługa jest dostępna i czy stać go na odblokowanie."""
    have = unlocked_ids(s)
    out = []
    for x in SERVICES:
        lvl_ok = level >= x['level']
        row = {**x, 'levelOk': lvl_ok, 'unlocked': lvl_ok and x['id'] in have,
               'canUnlock': lvl_ok and x['id'] not in have and (s.get('cash') or 0) >= x['unlock']}
        if board:   # 2.2b: popyt teraz/następny i stawka bieżąca
            dm = board['now'][x['id']]
            row.update(baseRate=x['base_rate'], demand=dm, rateNow=round(x['base_rate'] * dm, 2),
                       demandNext=board['next'][x['id']], demandChangesAt=board['changesAt'])
        out.append(row)
    return out


def install(app, d, E):
    db, world, own, auth = d.db, d.world, d.own, d.auth
    now, fail, rate, audit = d.now, d.fail, d.rate, d.audit

    @app.get('/api/worlds/{wid}/services')
    def services_list(wid: int, u=Depends(auth)):
        with db.tx() as c:
            world(c, wid)
            ch = own(c, u['id'], wid)
            s = json.loads(ch['state_json'])
            board = demand_board(wid, now())
            return dict(services=view(s, E.level(s['xp']), board), regen=list(REGEN), demandTop=board['top'],
                        demandChangesAt=board['changesAt'], demandWindowMs=DEMAND_WINDOW_MS,
                        transportMinMs=TRANSPORT_MIN_MS, cooldownAfter=COOLDOWN_AFTER, cooldownMs=COOLDOWN_MS)

    @app.post('/api/worlds/{wid}/services/{sid}/unlock')
    def services_unlock(wid: int, sid: str, request: Request, u=Depends(auth)):
        """2.4a: jednorazowe odblokowanie usługi za gotówkę (wymagany poziom). Bez wymogu obecności — gra idle."""
        key = request.headers.get('idempotency-key', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
            fail(422, 'Brak poprawnego identyfikatora operacji.')
        rate(request, 'service-unlock-' + str(u['id']), 20, 3_600_000)
        okey = 'service-unlock:' + key
        with db.tx() as c:
            old = c.execute('SELECT response_json FROM operations WHERE account_id=? AND world_id=? AND key=?',
                            (u['id'], wid, okey)).fetchone()
            if old:
                return json.loads(old['response_json'])
            x = BY_ID.get(sid)
            if not x:
                fail(404, 'Nieznana usługa.')
            w = world(c, wid, True)
            ch = own(c, u['id'], wid)
            s = json.loads(ch['state_json'])
            E.sync(s, now(), w['speed'])
            if E.level(s['xp']) < x['level']:
                fail(409, f"{x['name']} wymaga {x['level']}. poziomu.")
            if sid in unlocked_ids(s):
                fail(409, f"{x['name']} jest już odblokowana.")
            if s['cash'] < x['unlock']:
                fail(409, f"Odblokowanie kosztuje {x['unlock']} $.")
            s['cash'] -= x['unlock']
            s['servicesUnlocked'] = sorted(set(s.get('servicesUnlocked') or []) | {sid})
            E.log(s, f"Odblokowano usługę {x['name']} (−{x['unlock']} $).", now())
            c.execute('UPDATE characters SET state_json=? WHERE id=?',
                      (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))
            audit(c, u['id'], 'service.unlock', dict(character=ch['id'], service=sid, cost=x['unlock']))
            result = dict(message=f"{x['name']} odblokowana.", cash=s['cash'], services=view(s, E.level(s['xp']), demand_board(wid, now())))
            c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',
                      (u['id'], wid, okey, 'service-unlock', json.dumps(result, ensure_ascii=False), now()))
            return result

    return dict(view=view, unlocked_ids=unlocked_ids, travel_ms=travel_ms, demand=demand)
