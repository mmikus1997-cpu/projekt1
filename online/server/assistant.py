"""2.6 GDD v3.1: Asystent Podróży — doradca, który liczy za gracza (tylko odczyt, niczego nie zapisuje poza
leniwym rozliczeniem NPC, jak każdy odczyt /npcs).

GET /api/worlds/{wid}/assistant?hours=8
  plans  — dla każdego wolnego NPC 3 najlepsze usługi wg npc.estimate() (prawdziwe advance() na kopii),
           z przydziałem wolnych aut od najszybszego (jak akcja zbiorcza cars='auto');
  alerts — przemęczenie, głód, kończące się zmiany, zmiana popytu, wolne auta, przerwa dyspozytora, eventy;
  travel — porady podróży gracza: autobus / auto / autostop do każdej dostępnej dzielnicy.
"""
import json
from fastapi import Depends, Query

ALERT_HUNGER = 40               # sytość < 40 → podpowiedź posiłku
ALERT_SHIFT_END_MS = 3_600_000  # zmiana kończy się w ciągu godziny
ALERT_DEMAND_MS = 30 * 60_000   # popyt zmieni się w ciągu 30 min
TOP_PLANS = 3
LOW_FUEL = 20                   # 3.2: alert, gdy paliwo < 20%
CAUSE = {'energy': 'wyczerpany', 'mood': 'zły nastrój', 'hunger': 'głodny'}


def mins(ms):
    return max(1, -(-int(ms) // 60_000))


def install(app, d, E, S, N, travel):
    db, now, world, own, auth, era = d.db, d.now, d.world, d.own, d.auth, d.era
    npc = d.npc

    def free_cars(s, team, t, traveling):
        """Wolne auta gracza od najszybszego: nie z NPC, nie na starej trasie, nie wiozą gracza."""
        out = []
        if not any(N.role_of(m) == 'driver' and not m.get('duty') for m in team):
            return out                    # v3.2: autami z garażu jeżdżą tylko wolni kierowcy
        for v in N.ready_cars(s, S, E):   # 3.2: tylko auta z paliwem na najdłuższy odcinek
            if any(m['assigned_car_id'] == v and m.get('phase') for m in team):
                continue
            if E.vehicle_busy_until(s, v, t) > t or (traveling and s.get('travelCar') == v):
                continue
            out.append(v)
        return out

    def npc_section(c, ch, wid, s, t, hours, traveling):
        team = npc['roster'](c, ch, wid)
        s['npcCars'] = npc['cars'](c, ch['id'], t)
        cars = free_cars(s, team, t, traveling)
        s.pop('npcCars', None)
        cars_left = list(cars)
        plans, resting, alerts = [], [], []
        for n in team:
            if n.get('phase'):
                left = (n['autopilot_expires_at'] or t) - t
                if 0 <= left <= ALERT_SHIFT_END_MS:
                    alerts.append(dict(kind='shift_ending', level='info', npc=n['id'], at=n['autopilot_expires_at'],
                                       text=f"{n['name']} kończy zmianę za {mins(left)} min."))
            elif n['energy'] < N.DISPATCH_MIN_ENERGY:
                regen = N.IDLE_RATES[0] * N.trait_of(n).get('sleep_regen', 1.0)
                at = int(t + (N.DISPATCH_MIN_ENERGY - n['energy']) / regen * N.HOUR)
                resting.append(dict(npc=n['id'], name=n['name'], readyAt=at))
            elif N.role_of(n) == 'service' and not n.get('duty'):   # v3.2: kierowcy nie pracują w usługach
                car = cars_left[0] if cars_left else None
                opts = N.ranked(n, s, hours, car, t, wid, E, S)[:TOP_PLANS]
                if opts and car:
                    cars_left.pop(0)
                plans.append(dict(npc=n['id'], name=n['name'], trait=n.get('trait'), car=car, options=opts,
                                  text=(f"{n['name']}: {opts[0]['name']} {hours} h {'autem' if car else 'autobusem'} ≈ {opts[0]['cash']} $ "
                                        f"(popyt {round(opts[0]['demand'] * 100)}%)" + (' ⚠ przemęczenie' if opts[0]['burnout'] else '')) if opts else
                                       f"{n['name']}: brak odblokowanych usług."))
            if n.get('unhappy_since') is not None:
                low = min(N.KEYS, key=lambda k: n[k])
                alerts.append(dict(kind='exhausted', level='warn', npc=n['id'], cause=low,
                                   text=f"{n['name']} jest przemęczony ({CAUSE[low]}) — zarabia o połowę mniej."))
            if n['hunger'] < ALERT_HUNGER:
                alerts.append(dict(kind='hungry', level='warn', npc=n['id'],
                                   text=f"{n['name']} jest głodny (sytość {round(n['hunger'])}) — "
                                        + f"{N.MEALS[max(1, E.buffet_level(s))]['name']}: {N.MEALS[max(1, E.buffet_level(s))]['cost']} $."))  # 4.4
        # wolne auta, których nie wzięły plany, a ktoś jeździ autobusem → następną zmianę lepiej autem
        if cars_left and any(m.get('phase') and m.get('shift_bus') for m in team):
            alerts.append(dict(kind='cars_idle', level='info', cars=cars_left,
                               text=f"Wolne auta w garażu: {', '.join(cars_left)}, a część NPC jeździ autobusem — przy następnej zmianie wyślij ich autem (krótszy dojazd, bez biletów)."))
        if (s.get('garage') or []) and not any(N.role_of(m) == 'driver' for m in team) \
                and any(m.get('phase') and m.get('shift_bus') for m in team):
            alerts.append(dict(kind='need_driver', level='info',   # v3.2: auta stoją, bo nie ma kierowcy
                               text='Masz auta w garażu, ale ekipa jeździ autobusem — zatrudnij NPC w roli Kierowca, aby wozić ich do pracy.'))
        cd = int((s.get('dispatch') or {}).get('cooldownUntil') or 0)
        if cd > t:
            alerts.append(dict(kind='cooldown', level='info', at=cd, text=f'Przerwa dyspozytora jeszcze {mins(cd - t)} min.'))
        on_shift = {m['assigned_car_id'] for m in team if m.get('phase') and m.get('assigned_car_id')}
        for v in s.get('garage') or []:
            if v not in on_shift and E.fuel_of(s, v) < LOW_FUEL:   # 3.2: auto na zmianie ma paliwo „w zmianie”
                full = round(100 - E.fuel_of(s, v), 2)
                alerts.append(dict(kind='low_fuel', level='warn', car=v, fuel=round(E.fuel_of(s, v)),
                                   cost=E.refuel_cost(s, v, full, t),
                                   text=f"{E.car(v).get('name', v)}: paliwo {round(E.fuel_of(s, v))}% — do pełna {E.refuel_cost(s, v, full, t)} $."))
        cap, cost = N.slots(s), N.recruit_cost(len(team))
        if len(team) < cap and s['cash'] >= cost:
            alerts.append(dict(kind='can_recruit', level='info',
                               text=f'Wolne miejsce w Rezydencji ({len(team)}/{cap}) — nowy NPC kosztuje {cost} $.'))
        return team, plans, resting, alerts

    def travel_section(c, ch, wid, w, s, t):
        """Porady podróży gracza (te same wzory co travel.start_travel, łącznie z bonusem Wolności)."""
        if ch['travel_destination']:
            return dict(traveling=True, to=ch['travel_destination'], until=ch['travel_until'], options=[])
        cur = ch['current_district'] or 1
        speed = w['speed']
        open_to = era(c, wid)['districts']
        s['ally'] = E.ally_levels(c, ch['id'])
        f = E.ally_mult(s, 'freedom')
        veh = (s.get('vehicle') or {}).get('id')
        cond = None
        if veh:
            r = c.execute('SELECT condition FROM vehicles WHERE character_id=? AND type=?', (ch['id'], veh)).fetchone()
            cond = r['condition'] if r else max(0, 100 - int((s.get('vehicle') or {}).get('wear', 0)))
        s['npcCars'] = npc['cars'](c, ch['id'], t)
        busy = E.vehicle_busy_until(s, veh, t) if veh else 0
        s.pop('npcCars', None)
        fuel = E.fuel_of(s, veh) if veh else None
        car_ok = bool(veh) and (cond or 0) > 0 and not busy
        opts = []
        for did, name in travel['DISTRICTS']:
            if did == cur:
                continue
            dist = abs(did - cur)
            ok = did in d.always_open or did <= open_to
            bus = max(1000, round(travel['travel_ms']('bus', dist, speed) * f))
            car = max(1000, round(travel['travel_ms']('car', dist, speed) * f)) if veh else None
            hh = (max(1000, round(travel['travel_ms']('hitchhike', dist, speed, 3.0) * f)),
                  max(1000, round(travel['travel_ms']('hitchhike', dist, speed, 10.0) * f)))
            need = E.fuel_need(veh, dist) if veh else None
            fuel_ok = bool(veh) and fuel + 1e-9 >= need
            if car_ok and fuel_ok:
                rec, why = 'car', f'auto jest wolne — najszybciej (paliwo −{need}%)'
            elif car_ok and s['cash'] >= d.bus_fare:
                rec, why = 'bus', f'za mało paliwa ({round(fuel)}%, potrzeba {need}%) — zatankuj albo jedź autobusem'
            elif s['cash'] >= d.bus_fare:
                rec, why = 'bus', ('auto zajęte przez NPC' if busy else 'brak sprawnego auta') + ' — autobus'
            else:
                rec, why = 'hitchhike', 'brak gotówki na bilet — autostop (ryzyko −10 energii)'
            opts.append(dict(district=did, name=name, open=ok, recommended=rec if ok else None, why=why if ok else 'Dzielnica niedostępna w obecnej Erze.',
                             bus=dict(ms=bus, fare=d.bus_fare), car=dict(ms=car, available=car_ok and fuel_ok, busyUntil=busy or None, vehicle=veh,
                                                                  fuel=round(fuel, 1) if veh else None, fuelNeed=need),
                             hitchhike=dict(minMs=hh[0], maxMs=hh[1])))
        return dict(traveling=False, from_=cur, options=opts)

    @app.get('/api/worlds/{wid}/assistant')
    def assistant(wid: int, hours: int = Query(8), u=Depends(auth)):
        if hours not in N.AUTOPILOT:
            d.fail(422, 'Długość zmiany: 2, 4, 8 albo 12 h.')
        with db.tx() as c:
            w = world(c, wid)
            ch = own(c, u['id'], wid)
            t = now()
            team, plans, resting, alerts = npc_section(c, ch, wid, json.loads(own(c, u['id'], wid)['state_json']), t, hours,
                                                       bool(ch['travel_destination']))
            ch = own(c, u['id'], wid)            # świeży stan po wypłatach z zakończonych zmian
            s = json.loads(ch['state_json'])
            E.sync(s, t, w['speed'])
            board = S.demand_board(wid, t)
            if board['changesAt'] - t <= ALERT_DEMAND_MS:
                up = max(S.SERVICES, key=lambda x: board['next'][x['id']])
                alerts.append(dict(kind='demand_change', level='info', at=board['changesAt'],
                                   text=f"Popyt zmieni się za {mins(board['changesAt'] - t)} min — potem najlepiej: {up['name']} ({round(board['next'][up['id']] * 100)}%)."))
            ev = E.timed_event(t)
            if ev['effect'] == 'bus_free':
                alerts.append(dict(kind='bus_free', level='info', at=ev['end'],
                                   text=f"🚌 Darmowa Komunikacja jeszcze {mins(ev['end'] - t)} min — wysłani teraz NPC nie płacą za bilety."))
            elif ev['effect'] == 'service_cash':
                alerts.append(dict(kind='service_rush', level='info', at=ev['end'],
                                   text=f"🏪 Szczyt Usług jeszcze {mins(ev['end'] - t)} min — wysłani teraz NPC zarabiają +25%."))
            expected = sum(p['options'][0]['cash'] for p in plans if p['options'])
            return dict(hours=hours, plans=plans, resting=resting, alerts=alerts, expectedTotal=expected,
                        batch=dict(action='dispatch', npcs='idle', service_id='best', hours=hours, cars='auto') if plans else None,
                        demand=dict(changesAt=board['changesAt'], top=board['top']),
                        travel=travel_section(c, ch, wid, w, s, t), serverTime=t)

    return dict()
