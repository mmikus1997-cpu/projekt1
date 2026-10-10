"""0.25 Mapa 8 dzielnic i podróże: stan na kolumnach `characters`, pojazdy w tabeli `vehicles`.

Dzielnica 1 = „Nadmorskie” (start), dzielnica 2 = „Przemysłowe” (firmy). Podróż
zapisuje kolumny travel_*; dojazd rozlicza endpoint arrive albo leniwy odczyt stanu.
W trakcie drogi nie działa praca stacjonarna (kontrakty, treningi, zlecenie dnia), a zarządzanie
firmami wymaga przebywania w dzielnicy 2 (bramka w economy.action, parametr `district`).
Tryby: bus (20 $, 5 min × odległość / tempo świata), hitchhike (0 $, losowo 3–10 min, 15% szans
na utratę 10 energii), car (sprawne auto z tabeli `vehicles`, czas = 20% czasu busa).
"""
import json
import random as _random

from fastapi import Depends, Request
from pydantic import BaseModel, Field
from typing import Literal

# 2.1b GDD v3.1: 1 Ostoja → Nadmorskie, 2 Zakłady Miejskie → Przemysłowe
DISTRICTS = [(1, 'Nadmorskie'), (2, 'Przemysłowe'), (3, 'Centrum'), (4, 'Portowe'), (5, 'Biznesowe'), (6, 'Sportowe'), (7, 'Kopalnia'), (8, 'Lasy Wschodnie')]
# 2.1c GDD v3.1: Przemysłowe, Kopalnia i Lasy Wschodnie zawsze dostępne (usługi od Ery I) — dawne RESOURCE_DISTRICTS.
ALWAYS_OPEN = (2, 7, 8)
BUS_FARE = 20
BUS_MINUTES_PER_STEP = 5
CAR_SHARE = 0.2  # auto skraca czas busa o 80%

VEHICLES_DDL = '''
CREATE TABLE IF NOT EXISTS vehicles(id INTEGER PRIMARY KEY AUTOINCREMENT,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,type TEXT NOT NULL,condition INTEGER NOT NULL DEFAULT 100,speed_bonus INTEGER NOT NULL DEFAULT 0);
CREATE INDEX IF NOT EXISTS vehicles_char ON vehicles(character_id,id DESC);
'''


class Travel(BaseModel):
    target_district: int = Field(ge=1, le=8)
    mode: Literal['bus', 'hitchhike', 'car']


def name_of(district_id):
    return next((n for i, n in DISTRICTS if i == district_id), 'Nieznana')


def _draw_hitchhike():
    # punkt kontrolny dla testów: (minuty 3–10, czy los wyszedł pechowy — 15%)
    return _random.uniform(3.0, 10.0), _random.random() < 0.15


def install(app, d, E):
    db, now, fail, world, own, auth, rate, audit, era = d.db, d.now, d.fail, d.world, d.own, d.auth, d.rate, d.audit, d.era
    c = db.connect()
    try:
        columns = {r[1] for r in c.execute('PRAGMA table_info(characters)')}
        for name, definition in [('current_district', 'INTEGER NOT NULL DEFAULT 1'), ('travel_destination', 'INTEGER'), ('travel_until', 'INTEGER'), ('travel_mode', 'TEXT'), ('travel_started', 'INTEGER')]:
            if name not in columns:c.execute('ALTER TABLE characters ADD COLUMN '+name+' '+definition)
        c.executescript(VEHICLES_DDL)
        c.commit()
    finally:
        c.close()

    def w_speed(c, wid):
        r = c.execute('SELECT speed FROM worlds WHERE id=?', (wid,)).fetchone()
        return r['speed'] if r else 1

    def travel_ms(mode, distance, speed, minutes=None):
        base = round(BUS_MINUTES_PER_STEP * distance * 60000 / speed)
        if mode == 'car':return max(1000, round(base * CAR_SHARE))
        if mode == 'hitchhike':return max(1000, round(minutes * 60000 / speed))
        return max(60000, base)

    def settle(c, ch, ts):
        c.execute('UPDATE characters SET current_district=travel_destination,travel_destination=NULL,travel_until=NULL,travel_mode=NULL,travel_started=NULL WHERE id=?', (ch['id'],))
        return dict(ok=True, district=ch['travel_destination'], districtName=name_of(ch['travel_destination']), mode=ch['travel_mode'])

    def row(c, cid):
        return c.execute('SELECT * FROM characters WHERE id=?', (cid,)).fetchone()

    def lazy(c, cid, ts):
        ch = row(c, cid)
        if ch['travel_destination'] and ch['travel_until'] and ch['travel_until'] <= ts:settle(c, ch, ts)

    def info(c, cid):
        ch = row(c, cid)
        district = ch['current_district'] or 1
        travel = dict(to=ch['travel_destination'], toName=name_of(ch['travel_destination']), until=ch['travel_until'], mode=ch['travel_mode'], started=ch['travel_started']) if ch['travel_destination'] else None
        return dict(district=district, districtName=name_of(district), travel=travel)

    def ensure_vehicle_row(c, ch, s):
        # konta sprzed 0.25 mają pojazd tylko w stanie — dopisujemy go do rejestru przy pierwszym użyciu
        v = s.get('vehicle')
        if v and not c.execute('SELECT 1 FROM vehicles WHERE character_id=? AND type=?', (ch['id'], v['id'])).fetchone():
            g = next((g for g in E.GARAGE if g['id'] == v['id']), None)
            c.execute('INSERT INTO vehicles(character_id,type,condition,speed_bonus) VALUES(?,?,?,?)', (ch['id'], v['id'], max(0, 100 - int(v.get('wear', 0))), g['discount'] if g else 0))

    @app.post('/api/worlds/{wid}/travel')
    def start_travel(wid:int, data:Travel, request:Request, u=Depends(auth)):
        rate(request, 'travel-'+str(u['id']), 20, 3600000)
        with db.tx() as c:
            world(c, wid, True)
            ch = own(c, u['id'], wid)
            s = json.loads(ch['state_json'])
            speed = w_speed(c, wid)
            current = ch['current_district'] or 1
            if data.target_district not in ALWAYS_OPEN and data.target_district > era(c, wid)['districts']:fail(409, 'Dzielnica niedostępna w obecnej Erze świata.')
            if ch['travel_destination']:fail(409, 'Jesteś już w drodze do ' + name_of(ch['travel_destination']) + '.')
            if data.target_district == current:fail(422, 'Już jesteś w tej dzielnicy — wybierz inną.')
            E.sync(s, now(), speed)
            minutes = None
            if data.mode == 'bus':
                E.spend(s, cash=BUS_FARE)
            elif data.mode == 'car':
                ensure_vehicle_row(c, ch, s)
                if not c.execute('SELECT 1 FROM vehicles WHERE character_id=? AND condition>0', (ch['id'],)).fetchone():
                    fail(422, 'Potrzebujesz sprawnego pojazdu (kup w garażu albo serwisuj zużyty).')
                # 1.4 GDD v3.1: auto wysłane w trasę NPC nie może jednocześnie wieźć gracza
                s['npcCars'] = app.state.npc['cars'](c, ch['id'], now()) if hasattr(app.state, 'npc') else {}  # 2.4c GDD v3.1
                busy = E.vehicle_busy_until(s, (s.get('vehicle') or {}).get('id'), now())
                s.pop('npcCars', None)
                if busy:
                    fail(409, 'Auto zajęte w trasie NPC do ' + E.clock_hm(busy) + ' (jeszcze ' + str(-(-(busy - now()) // 60000)) + ' min). Wybierz inne auto albo jedź busem.')
                # 3.2 GDD v3.1: paliwo za przystanek (odległość jak przy czasie podróży); za mało → auto nie wyjeżdża
                veh = (s.get('vehicle') or {}).get('id')
                need = E.fuel_need(veh, abs(data.target_district - current))
                have = E.fuel_of(s, veh)
                if have + 1e-9 < need:
                    fail(409, f'Za mało paliwa ({round(have)}%, potrzeba {need}%). Zatankuj w Garażu albo jedź autobusem.')
                E.set_fuel(s, veh, have - need)
            else:
                minutes, unlucky = _draw_hitchhike()
                rescue = E.stat_pct(s, 2, 0.5, 12)  # 0.35: Refleks zmniejsza ryzyko nieudanego autostopu (baza 15%, min. 3%)
                if unlucky and rescue > 0 and _random.random() * 100 < rescue:unlucky = False
                if unlucky:s['energy'] = max(0.0, float(s['energy']) - 10)
                minutes = round(minutes * (1 - E.stat_pct(s, 2, 1.0, 25) / 100), 1)  # 0.35: Refleks skraca autostop (cap -25%)
            s['travelCar'] = (s.get('vehicle') or {}).get('id') if data.mode == 'car' else None  # 1.4: którym autem jedzie gracz (blokada tras NPC)
            ms = travel_ms(data.mode, abs(data.target_district - current), speed, minutes)
            s['ally'] = E.ally_levels(c, ch['id']); ms = max(1000, round(ms * E.ally_mult(s, 'freedom')))  # 0.57 Wolność
            until = now() + ms
            c.execute('UPDATE characters SET travel_destination=?,travel_until=?,travel_mode=?,travel_started=? WHERE id=?', (data.target_district, until, data.mode, now(), ch['id']))
            c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))
            audit(c, u['id'], 'travel.start', dict(mode=data.mode, frm=current, to=data.target_district, ms=ms))
            return dict(ok=True, travel=dict(to=data.target_district, toName=name_of(data.target_district), until=until, mode=data.mode, started=now()), cash=s['cash'], energy=s['energy'])

    @app.post('/api/worlds/{wid}/travel/arrive')
    def arrive(wid:int, u=Depends(auth)):
        with db.tx() as c:
            world(c, wid, True)
            ch = own(c, u['id'], wid)
            if not ch['travel_destination']:fail(409, 'Nie jesteś w drodze.')
            if ch['travel_until'] > now():
                left = round((ch['travel_until'] - now()) / 60000 / max(1, w_speed(c, wid)), 1)
                fail(409, 'Jeszcze w drodze do ' + name_of(ch['travel_destination']) + ' — zostało ok. ' + str(left) + ' min.')
            return settle(c, ch, now())
    @app.post('/api/worlds/{wid}/travel/speedup')
    def speedup(wid:int,request:Request,u=Depends(auth)):
        rate(request,'travel-speed-'+str(u['id']),20,3600000)
        with db.tx() as c:
            world(c, wid, True)
            ch = own(c, u['id'], wid)
            if not ch['travel_destination']:fail(409,'Nie jesteś w drodze.')
            if ch['travel_until'] <= now():fail(409,'Podróż właśnie się kończy — ogłoś przyjazd.')
            s = json.loads(ch['state_json'])
            if s.get('vipUntil',0) <= now():fail(403,'Przyspieszenie podróży to funkcja VIP (sklep projektowy).')
            remaining = ch['travel_until'] - now()
            until = now() + max(1000, remaining // 2)
            c.execute('UPDATE characters SET travel_until=? WHERE id=?',(until,ch['id']))
            audit(c, u['id'], 'travel.speedup', dict(remaining=remaining, until=until))
            return dict(ok=True, until=until, remaining=until-now(), message='Podróż przyspieszona o połowę pozostałego czasu (VIP).')
    return dict(lazy=lazy, info=info, settle=settle, travel_ms=travel_ms, ensure_vehicle_row=ensure_vehicle_row, DISTRICTS=DISTRICTS)
