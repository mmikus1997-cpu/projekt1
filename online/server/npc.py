"""2.3 GDD v3.1: NPC gracza — rekrutacja w Rezydencji, 3 emocje (energia / nastrój / sytość), ucieczka.

Emocje liczone leniwie: advance(n, now) nalicza zmianę od n['updated_at'] po stawkach zależnych od statusu.
Wołane przy każdym odczycie/akcji oraz z app.sweep() co 10 min (ucieczka także dla graczy offline).

2.4: zmiana pracy (auto-pilot 2/4/8/12 h) jako maszyna stanów liczona w advance():
  to_work → working →(energia ≤ 15)→ to_home → sleeping →(energia ≥ 90)→ to_work … → koniec zmiany → wypłata.

2.3c: zamiast ucieczki — PRZEMĘCZENIE: gdy którakolwiek emocja < 30, zarobek ×0,5 do czasu, aż wszystkie
wrócą do ≥ 40 (histereza). NPC nigdy nie znika z bazy. Kolumna unhappy_since = „przemęczony od”.

Kolumna `hunger` oznacza SYTOŚĆ: 100 = najedzony, spada ku zeru (decyzja usera). Dzięki temu wszystkie
trzy emocje działają w tym samym kierunku i warunek ucieczki „wszystkie < 30” jest spójny.
"""
import json
import random
import re
from fastapi import Depends, Request
from typing import List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field, field_validator

SCHEMA = '''
CREATE TABLE IF NOT EXISTS npcs(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  name TEXT NOT NULL,
  avatar TEXT NOT NULL,
  energy REAL NOT NULL DEFAULT 100 CHECK(energy BETWEEN 0 AND 100),
  mood REAL NOT NULL DEFAULT 100 CHECK(mood BETWEEN 0 AND 100),
  hunger REAL NOT NULL DEFAULT 100 CHECK(hunger BETWEEN 0 AND 100),
  status TEXT NOT NULL DEFAULT 'idle',
  assigned_service_id TEXT,
  assigned_car_id TEXT,
  autopilot_mode TEXT,
  autopilot_expires_at INTEGER,
  unhappy_since INTEGER,
  warned_at INTEGER,
  hired_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS npcs_character ON npcs(character_id);
CREATE INDEX IF NOT EXISTS npcs_unhappy ON npcs(unhappy_since) WHERE unhappy_since IS NOT NULL;
'''

# 2.4 GDD v3.1: kolumny zmiany pracy (dodawane ALTER TABLE — kompatybilność wstecz)
SHIFT_COLUMNS = [
    ('phase', 'TEXT'),                                  # to_work | working | to_home | sleeping | NULL
    ('phase_until', 'INTEGER'),                         # koniec bieżącego odcinka dojazdu (ms)
    ('travel_ms', 'INTEGER'),                           # czas jednego odcinka w tej zmianie
    ('shift_started_at', 'INTEGER'),
    ('shift_cash', 'REAL NOT NULL DEFAULT 0'),          # zarobek brutto (z bonusem i eventem)
    ('shift_fares', 'INTEGER NOT NULL DEFAULT 0'),      # bilety autobusowe do potrącenia
    ('shift_bonus', 'REAL NOT NULL DEFAULT 0'),         # bonus auto-pilota (0 / .05 / .10 / .15)
    ('shift_event', 'REAL NOT NULL DEFAULT 1'),         # mnożnik „Szczytu Usług” zamrożony przy starcie
    ('shift_demand', 'REAL NOT NULL DEFAULT 1'),        # 2.2b: popyt usługi zamrożony przy wysłaniu (50–150%)
    ('shift_recalled', 'INTEGER NOT NULL DEFAULT 0'),   # odwołany wcześniej → bez bonusu
    ('shift_bus', 'INTEGER NOT NULL DEFAULT 0'),        # 1 = jedzie autobusem (bilet za odcinek)
    ('shift_fare_mult', 'REAL NOT NULL DEFAULT 1'),     # 2.4e: mnożnik biletu zamrożony przy wysłaniu (0 = Darmowa Komunikacja)
    ('shift_manager', 'INTEGER NOT NULL DEFAULT 0'),    # 2.7: zmiana wysłana przez AI Managera (prowizja 10%)
    ('shift_fuel', 'REAL'),                             # 3.2: paliwo auta przekazane na zmianę (reszta wraca do garażu)
    ('shift_fuel_need', 'REAL'),                        # 3.2: % baku na jeden odcinek dojazdu
    ('bus_travel_ms', 'INTEGER'),                       # 3.2: czas odcinka autobusem (przesiadka przy pustym baku)
]

# 2.3b GDD v3.1: osobowość NPC — 1 z 6 cech losowana przy rekrutacji (kolumna `trait`).
TRAITS = {
    'pracoholik': dict(label='Pracoholik', icon='💼', earn=0.10, energy_drain=1.2,
                       desc='+10% zarobku, energia w pracy spada 1,2× szybciej'),
    'spioch':     dict(label='Śpioch', icon='😴', earn=-0.10, sleep_regen=1.3,
                       desc='−10% zarobku, regeneracja energii ze snu +30%'),
    'ambitny':    dict(label='Ambitny', icon='🚀', earn=0.15, mood_drain=1.5,
                       desc='+15% zarobku, nastrój spada 1,5× szybciej'),
    'optymista':  dict(label='Optymista', icon='🌞', mood_drain=0.5,
                       desc='nastrój spada o połowę wolniej'),
    'analityk':   dict(label='Analityk', icon='📊', earn_in={'callcenter': 0.15, 'marketing': 0.15},
                       desc='+15% zarobku w pracy biurowej (Call center, Agencja marketingowa)'),
    # v3.2 Zad. 4: cecha działa wyłącznie dla roli DRIVER (pasażer nie prowadzi). wear = mnożnik zużycia auta (negatyw).
    'kierowca_rajdowy': dict(label='Kierowca rajdowy', icon='🏎️', travel=0.8, wear=2.0, roles=('driver',),
                             desc='tylko kierowca: czas jazdy −20% (min. 30 s), zużycie auta ×2'),
}
TRAIT_IDS = list(TRAITS)
TRAIT_ALIAS = {'kierowca': 'kierowca_rajdowy'}   # v3.2: zgodność wstecz (dawna cecha „Kierowca”)
EXTRA_COLUMNS = [('trait', 'TEXT')]

# v3.2 Zad. 1: role NPC
ROLES = ('service', 'driver')
ROLE_LABEL = {'service': 'Usługi', 'driver': 'Kierowca'}
ROLE_CHANGE_MS = 24 * 3_600_000                  # zmiana roli maks. raz na 24 h
# v3.2: kolumny ról, kursów, Taxi i lojalności (ALTER TABLE — migracja addytywna)
V32_COLUMNS = [
    ('role', "TEXT NOT NULL DEFAULT 'service'"),
    ('role_changed_at', 'INTEGER'),
    ('duty', 'TEXT'),                             # kierowca: ferry | taxi | NULL (wolny)
    ('busy_until', 'INTEGER'),                    # kierowca: koniec kursu / zmiany Taxi
    ('ride_car', 'TEXT'),                         # kierowca: auto bieżącego kursu / Taxi
    ('taxi_started_at', 'INTEGER'),
    ('taxi_until', 'INTEGER'),
    ('taxi_hours', 'INTEGER'),
    ('taxi_cash', 'REAL NOT NULL DEFAULT 0'),
    ('taxi_mult', 'REAL NOT NULL DEFAULT 1'),     # mnożnik stawki zamrożony przy starcie (VEH_MULT auta)
    ('taxi_recalled', 'INTEGER NOT NULL DEFAULT 0'),
    ('loyalty', 'INTEGER NOT NULL DEFAULT 0'),
    ('loyal_since', 'INTEGER'),
    ('loy_day', 'INTEGER'),                       # indeks doby UTC (t // DAY)
    ('loy_min', 'REAL'),                          # najniższa emocja w bieżącej dobie
    ('leg_mode', 'TEXT'),                         # SERVICE: bieżący odcinek car | bus
    ('leg_ride', 'INTEGER'),                      # SERVICE: id kursu (npc_rides)
    ('shift_legacy', 'INTEGER NOT NULL DEFAULT 0'),   # 1 = zmiana sprzed v3.2 (auto przypięte do NPC)
    ('leg_want', 'TEXT'),                         # SERVICE: żądanie odcinka to_work|to_home czekające na dyspozytora
    ('pref_car', 'TEXT'),                         # SERVICE: auto preferowane przez gracza (nie rezerwuje auta)
    ('taxi_fuel_end', 'INTEGER'),                 # Taxi: chwila, w której skończy się paliwo w aucie
]

# v3.2 Zad. 2: Shift Taxi — wolny kierowca jeździ 2/4/8 h. Dochód wyraźnie niższy niż usługi (50–220 $/h),
# ale zawsze pokrywa paliwo i serwis (kalibracja w PROJEKT-GDD32-NPC.md §4). Bez losowości.
TAXI_RATE = 40.0                 # $/h przed mnożnikiem auta
# v3.2 Zad. 5: lojalność — +1 za pełną dobę UTC bez spadku żadnej emocji < 50; przy 100 status „Lojalny”
LOYALTY_MAX = 100
LOYALTY_MIN_EMOTION = 50
LOYAL_MULT = 1.05                # +5% zarobku (usługi i Taxi) na stałe
TAXI_HOURS = (2, 4, 8)
TAXI_HOPS_PER_H = 1              # paliwo: 1 odcinek-hop na godzinę × car.fuel (% baku)
TAXI_WEAR_PER_H = 1.0            # % zużycia na godzinę (rajdowy ×2)
TAXI_RATES = (-6.0, -3.0, -3.0)  # kierowca na Taxi: energia, nastrój, sytość na godzinę (poziom Kuriera)
TAXI_MULT = {'dostawczak': 0.85, 'furgonetka': 1.0, 'sedan': 1.15, 'van': 1.25, 'suv': 1.45, 'mistrz': 1.45}   # = VEH_MULT

# v3.2 Zad. 3: logistyka — kursy kierowców (blokada aut i kierowców, historia)
RIDES_SCHEMA = '''
CREATE TABLE IF NOT EXISTS npc_rides(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  driver_id INTEGER NOT NULL REFERENCES npcs(id) ON DELETE CASCADE,
  car_id TEXT NOT NULL,
  kind TEXT NOT NULL,
  district INTEGER,
  depart_at INTEGER NOT NULL,
  meet_at INTEGER NOT NULL,
  arrive_at INTEGER NOT NULL,
  back_at INTEGER NOT NULL,
  passengers TEXT NOT NULL DEFAULT '[]',
  fuel REAL NOT NULL DEFAULT 0,
  wear REAL NOT NULL DEFAULT 0,
  cash INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS npc_rides_busy ON npc_rides(character_id, back_at);
'''
SEATS = {'dostawczak': 1, 'sedan': 2, 'van': 3, 'furgonetka': 3, 'suv': 4, 'mistrz': 4}   # pasażerowie (bez kierowcy)
WEAR_PER_HOP = 1                 # D6: % zużycia auta na odcinek-hop kursu (rajdowy ×2)
FERRY_RATES = (-4.0, -1.0, -2.0)  # kierowca w kursie: energia, nastrój, sytość na godzinę
RIDE_KEEP_MS = 7 * 24 * 3_600_000


def role_of(n):
    return n.get('role') or 'service'


def trait_of(n):
    """Cecha NPC z uwzględnieniem roli (v3.2: kierowca_rajdowy tylko dla DRIVER) i lojalności (bez negatywów)."""
    tid = TRAIT_ALIAS.get(n.get('trait') or '', n.get('trait') or '')
    t = TRAITS.get(tid, {})
    if t.get('roles') and role_of(n) not in t['roles']:
        return {}
    if n.get('loyal_since') and t:
        t = {k: v for k, v in t.items() if not (k in ('energy_drain', 'mood_drain', 'wear') and v > 1)
             and not (k == 'earn' and v < 0)}
    return t


def trait_pool(role):
    """v3.2: cechy losowane przy rekrutacji wg roli (analityk tylko usługi, rajdowy tylko kierowca)."""
    return [k for k in TRAIT_IDS if k != 'analityk' or role == 'service'
            if not TRAITS[k].get('roles') or role in TRAITS[k]['roles']]


def trait_earn(n):
    """Dodatek procentowy cechy do zarobku w bieżącej usłudze (sumowany z bonusem auto-pilota)."""
    t = trait_of(n)
    return t.get('earn', 0.0) + t.get('earn_in', {}).get(n.get('assigned_service_id'), 0.0)


HOUR = 3_600_000
DAY = 24 * HOUR
MAX_NPC = 20                     # v3.2 Zad. 1 (było 15)
SLOTS_PER_RESIDENCE = 4          # v3.2 D1: pojemność = poziom Rezydencji × 4 (4, 8, 12, 16, 20)
IDLE_RATES = (10.0, 0.0, -1.0)   # energia, nastrój, sytość na godzinę w Rezydencji
EXHAUST_BELOW = 30               # 2.3c: którakolwiek emocja < 30 → przemęczenie
RECOVER_AT = 40                  # 2.3c: wyjście, gdy WSZYSTKIE ≥ 40 (histereza — bez spamu powiadomień)
BURNOUT_MULT = 0.5               # 2.3c: zarobek przemęczonego NPC ×0,5
HOME_DISTRICT = 1                # Rezydencja stoi w Nadmorskiem
SWEEP_BATCH = 500
SWEEP_CHARS = 100                # v3.2: sweep — postaci w jednej partii

AUTOPILOT = {2: 0.0, 4: 0.05, 8: 0.10, 12: 0.15}   # godziny zmiany → bonus do zarobku
TRAVEL_RATES = (0.0, 0.0, -1.0)  # w drodze: emocje stoją, sytość −1/h
TIRED = 30                       # 2.3c: energia ≤ 30 → wraca spać (samo zmęczenie nie wywołuje przemęczenia)
RESTED = 90                      # energia ≥ 90 → wraca do pracy (jeśli zmiana trwa)
MIN_WORK_MS = 30 * 60_000        # powrót do pracy tylko gdy zostanie ≥ 2 dojazdy + 30 min
DISPATCH_MIN_ENERGY = 40         # 2.3c: wysyłka od energii 40 (powyżej progu powrotu 30)
BUS_FARE = 20                    # bilet za odcinek (jak travel.BUS_FARE)
# 4.4 GDD v3.1: Buffet w Rezydencji zastępuje prowizoryczny posiłek 30 $ / +50 (2.4d)
MEALS = {
    1: dict(name='Zwykłe jedzenie', cost=10, hunger=15, mood=0, energy=0),
    2: dict(name='Dobre jedzenie', cost=25, hunger=25, mood=5, energy=0),
    3: dict(name='Premium catering', cost=60, hunger=40, mood=15, energy=5),
}
EPS = 1e-9

# 2.7 GDD v3.1: AI Manager — automatyczne ponawianie zmian. Model F2P: prowizja 10% od wypłat zmian, które wysłał.
# Docelowo wariant premium (💎, bez prowizji) za flagą feature_flag_premium_currency — na razie wyłącznie prowizja.
MANAGER_COMMISSION = 0.10
MANAGER_MIN_LEVEL = 10
MANAGER_MAX_CHAIN = 50          # bezpiecznik: maks. zmian ponowionych w jednym rozliczeniu NPC
MANAGER_FEED_BELOW = 40         # manager karmi przed wysłaniem, gdy sytość < 40

NAMES = ['Ania', 'Bartek', 'Celina', 'Damian', 'Ewa', 'Filip', 'Gosia', 'Hubert', 'Iga', 'Janek', 'Kasia', 'Leon',
         'Magda', 'Nikodem', 'Ola', 'Piotrek', 'Róża', 'Szymon', 'Tosia', 'Wiktor', 'Zuzia', 'Adam', 'Basia', 'Czarek',
         'Dorota', 'Emil', 'Franek', 'Hania', 'Igor', 'Julka', 'Kuba', 'Lena', 'Marek', 'Natalia', 'Oskar', 'Paula',
         'Radek', 'Sara', 'Tomek', 'Wera']
AVATARS = ['npc-01', 'npc-02', 'npc-03', 'npc-04', 'npc-05', 'npc-06', 'npc-07', 'npc-08']


def recruit_cost(count):
    """Cena następnego NPC wg obecnej liczby: #1–3 500, #4–6 1500, #7–10 5000, #11–15 15000, #16–20 30000 (v3.2 D1)."""
    n = count + 1
    if n <= 3:
        return 500
    if n <= 6:
        return 1500
    if n <= 10:
        return 5000
    if n <= 15:
        return 15000
    return 30000


def slots(s):
    """Liczba miejsc na NPC = poziom Rezydencji × 4, maks. 20 (v3.2 D1)."""
    lvl = max(1, int((s.get('buildings') or {}).get('residence', 1) or 1))
    return min(MAX_NPC, lvl * SLOTS_PER_RESIDENCE)


def clamp(v):
    return max(0.0, min(100.0, v))


def rates(n, S):
    """Zmiana emocji na godzinę: praca wg katalogu usługi (sytość = −głód), bezczynność wg IDLE_RATES."""
    if n.get('duty') == 'ferry':   # v3.2: kierowca w kursie
        return FERRY_RATES
    if n.get('duty') == 'taxi':    # v3.2: Taxi — cechy zmieniają tylko zużycie (pracoholik, ambitny, optymista)
        tr = trait_of(n)
        e, m, h = TAXI_RATES
        return e * tr.get('energy_drain', 1.0), m * tr.get('mood_drain', 1.0), h
    phase = n.get('phase')
    if (phase == 'working' or (phase is None and n.get('status') == 'working')) and n.get('assigned_service_id') in S.BY_ID:
        x = S.BY_ID[n['assigned_service_id']]
        tr = trait_of(n)
        e, m = float(x['energy']), float(x['mood'])
        if e < 0:   # cecha zmienia tylko ZUŻYCIE (regeneracja Biblioteki/Parku bez zmian)
            e *= tr.get('energy_drain', 1.0)
        if m < 0:
            m *= tr.get('mood_drain', 1.0)
        return e, m, -float(x['hunger'])
    if phase in ('to_work', 'to_home'):
        return TRAVEL_RATES
    return IDLE_RATES[0] * trait_of(n).get('sleep_regen', 1.0), IDLE_RATES[1], IDLE_RATES[2]


KEYS = ('energy', 'mood', 'hunger')


def exhausted(n):
    return n.get('unhappy_since') is not None


def _next_flip(n, r, t):
    """Najbliższa chwila (ms) zmiany stanu przemęczenia przy stawkach r, albo inf.

    Nieprzemęczony: pierwsza emocja spadająca poniżej 30. Przemęczony: chwila, gdy wszystkie są ≥ 40."""
    inf = float('inf')
    if not exhausted(n):
        # +1 ms: stan zmienia się tuż ZA progiem — powrót do domu przy energii = 30 (TIRED) wygrywa z przemęczeniem
        times = [t + max(0.0, n[k] - EXHAUST_BELOW) / -rk * HOUR + 1 for k, rk in zip(KEYS, r)
                 if rk < 0 and n[k] >= EXHAUST_BELOW - EPS]
        return min(times, default=inf)
    times = []
    for k, rk in zip(KEYS, r):
        if n[k] < RECOVER_AT - EPS:
            if rk <= 0:
                return inf
            times.append(t + (RECOVER_AT - n[k]) / rk * HOUR + 1)
    return max(times, default=t)


def eat(n, meal, t, evs):
    """4.4: efekt posiłku. Gdy przyczyną przemęczenia był WYŁĄCZNIE głód (energia i nastrój ≥ 30),
    a po posiłku sytość ≥ 30 — przemęczenie znika od razu (bez czekania na próg 40)."""
    m = MEALS[meal]
    n = dict(n, hunger=clamp(n['hunger'] + m['hunger']), mood=clamp(n['mood'] + m['mood']),
             energy=clamp(n['energy'] + m['energy']))
    if exhausted(n) and all(n[k] >= EXHAUST_BELOW - EPS for k in KEYS):
        n['unhappy_since'] = None
        n['warned_at'] = None
        evs.append(dict(kind='recovered'))
    else:
        update_burnout(n, t, evs)
    return n


def update_burnout(n, t, evs):
    """Przełącza stan przemęczenia w chwili t (wejście < 30, wyjście ≥ 40) i dopisuje zdarzenie."""
    if not exhausted(n) and any(n[k] < EXHAUST_BELOW - EPS for k in KEYS):
        n['unhappy_since'] = int(t)
        low = min(KEYS, key=lambda k: n[k])
        evs.append(dict(kind='burnout', cause=low))
    elif exhausted(n) and all(n[k] >= RECOVER_AT - EPS for k in KEYS):
        n['unhappy_since'] = None
        n['warned_at'] = None
        evs.append(dict(kind='recovered'))


def _segment_end(n, t, now, S):
    """Koniec bieżącego odcinka o stałych stawkach: granica fazy, próg energii, koniec zmiany lub now."""
    p, se = n.get('phase'), n.get('autopilot_expires_at')
    if p is None:
        e = now
        if n.get('duty') and n.get('busy_until'):   # v3.2: koniec kursu kierowcy dzieli odcinek
            e = min(e, n['busy_until'])
        if n.get('duty') == 'taxi':                 # Taxi: pusty bak albo energia 30 kończą zmianę wcześniej
            if n.get('taxi_fuel_end'):
                e = min(e, n['taxi_fuel_end'])
            re = rates(n, S)[0]
            if re < 0:
                e = min(e, t + max(0.0, n['energy'] - TIRED) / -re * HOUR)
    elif p in ('to_work', 'to_home'):
        e = min(now, n['phase_until'])
    elif p == 'working':
        e = min(now, se)
        re = rates(n, S)[0]
        if re < 0:
            e = min(e, t + max(0.0, n['energy'] - TIRED) / -re * HOUR)
    else:  # sleeping
        e = min(now, se)
        if n['energy'] < RESTED - EPS:
            e = min(e, t + (RESTED - n['energy']) / rates(n, S)[0] * HOUR)
    e = min(e, _next_flip(n, rates(n, S), t))   # 2.3c: wejście/wyjście z przemęczenia dzieli odcinek
    if n.get('loy_day') is not None:            # v3.2: północ UTC dzieli odcinek (lojalność liczona per doba)
        e = min(e, (n['loy_day'] + 1) * DAY)
    return max(t, e)


def loyal_mult(n):
    return LOYAL_MULT if n.get('loyal_since') else 1.0


def _loyalty(n, t, evs):
    """v3.2: minimum emocji w bieżącej dobie (emocje liniowe w odcinku → wystarczą końce odcinków) i rozliczenie
    doby po północy. Doba liczy się tylko, gdy NPC był zatrudniony przez całą dobę. Lojalność nie spada (D3)."""
    low = min(n[k] for k in KEYS)
    if n.get('loy_day') is None:                # NPC sprzed v3.2: pierwsza (niepełna) doba się nie liczy
        n['loy_day'], n['loy_min'] = int(t // DAY), -1.0
        return
    # najpierw koniec odcinka (odcinki są cięte o północy, więc t ≤ granica bieżącej doby), potem rozliczenie doby
    n['loy_min'] = min(low, n['loy_min'] if n.get('loy_min') is not None else low)
    while t >= (n['loy_day'] + 1) * DAY:
        start = n['loy_day'] * DAY
        lm = n.get('loy_min')
        if lm is not None and lm >= LOYALTY_MIN_EMOTION - EPS and (n.get('hired_at') or 0) <= start \
                and (n.get('loyalty') or 0) < LOYALTY_MAX:
            n['loyalty'] = (n.get('loyalty') or 0) + 1
            if n['loyalty'] >= LOYALTY_MAX and not n.get('loyal_since'):
                n['loyal_since'] = int((n['loy_day'] + 1) * DAY)
                evs.append(dict(kind='loyal', at=n['loyal_since']))
        n['loy_day'] += 1
        n['loy_min'] = low                      # nowa doba zaczyna się od bieżących emocji


def payout(n, stripped=False):
    """Wypłata za zmianę: brutto (bez bonusu, gdy odwołano/uciekł) minus bilety."""
    gross = n.get('shift_cash') or 0
    if stripped:
        tb = trait_earn(n)
        gross *= (1 + tb) / (1 + (n.get('shift_bonus') or 0) + tb)   # zdejmij bonus auto-pilota, cecha zostaje
    return int(round(gross - (n.get('shift_fares') or 0)))


def _start_leg(n, phase, t, evs=None):
    if n.get('assigned_car_id') and not n.get('shift_bus'):
        # 3.2 GDD v3.1: paliwo za odcinek; pusty bak → przesiadka do autobusu do końca zmiany (×2,0 i bilety)
        need = n.get('shift_fuel_need') or 0
        if (n.get('shift_fuel') or 0) + EPS >= need:
            n['shift_fuel'] = round((n.get('shift_fuel') or 0) - need, 6)
        else:
            n['shift_bus'] = 1
            n['travel_ms'] = n.get('bus_travel_ms') or n.get('travel_ms')
            if evs is not None:
                evs.append(dict(kind='fuel_out'))
    n['phase'] = phase
    n['status'] = 'traveling'
    n['phase_until'] = int(t + (n.get('travel_ms') or 0))
    if n.get('shift_bus'):
        mult = n.get('shift_fare_mult')
        n['shift_fares'] = (n.get('shift_fares') or 0) + round(BUS_FARE * (1.0 if mult is None else mult))


def _finish(n, t, evs):
    evs.append(dict(kind='done', cash=payout(n, bool(n.get('shift_recalled'))), service=n.get('assigned_service_id'),
                    recalled=bool(n.get('shift_recalled')), at=int(t), car=n.get('assigned_car_id'),
                    manager=bool(n.get('shift_manager')), fuel=n.get('shift_fuel') if n.get('assigned_car_id') else None,
                    pref=n.get('pref_car')))
    clear_shift(n)


def clear_shift(n):
    if n.get('trait') == 'kierowca':   # v3.2 D2: dawny „Kierowca” po dokończeniu starej zmiany zostaje DRIVER-em
        n.update(trait='kierowca_rajdowy', role='driver')
    n.update(phase=None, phase_until=None, travel_ms=None, shift_started_at=None, shift_cash=0, shift_fares=0,
             shift_bonus=0, shift_event=1, shift_demand=1, shift_recalled=0, shift_bus=0, shift_fare_mult=1, shift_manager=0, shift_fuel=None, shift_fuel_need=None, bus_travel_ms=None, status='idle', assigned_service_id=None,
             assigned_car_id=None, autopilot_mode=None, autopilot_expires_at=None,
             leg_mode=None, leg_ride=None, leg_want=None, pref_car=None, shift_legacy=0)


def _leg(n, phase, t, evs, engine):
    """v3.2: start odcinka. W rozliczeniu (engine) nowa zmiana zgłasza żądanie — transport wybiera dyspozytor
    (kierowca + auto albo autobus). Prognozy (estimate) i zmiany sprzed v3.2 — stary model (auto przypięte do NPC)."""
    if engine and not n.get('shift_legacy'):
        n['leg_want'] = phase
    else:
        _start_leg(n, phase, t, evs)


def begin_leg(n, phase, t, mode, tm, ride=None):
    """v3.2: odcinek przydzielony przez dyspozytora: mode car (kurs `ride`) albo bus (bilet z mnożnikiem eventu)."""
    n.update(phase=phase, status='traveling', phase_until=int(t + tm), travel_ms=int(tm), leg_mode=mode,
             leg_ride=ride, leg_want=None, shift_bus=1 if mode == 'bus' else 0)
    if mode == 'bus':
        mult = n.get('shift_fare_mult')
        n['shift_fares'] = (n.get('shift_fares') or 0) + round(BUS_FARE * (1.0 if mult is None else mult))


def _transition(n, t, evs, engine=False):
    """Przejście między fazami w chwili t. Zwraca True, jeśli faza się zmieniła."""
    if n.get('duty') == 'ferry' and t >= (n.get('busy_until') or 0):   # v3.2: kierowca wrócił z kursu
        n.update(duty=None, ride_car=None)
        return True
    if n.get('duty') == 'taxi':
        fuel_end = n.get('taxi_fuel_end') or float('inf')
        until = n.get('taxi_until') or 0
        if t >= until or t >= fuel_end or n['energy'] <= TIRED + EPS:
            reason = 'recalled' if n.get('taxi_recalled') and t >= until else ('done' if t >= until else (
                'fuel' if t >= fuel_end else 'tired'))
            evs.append(dict(kind='taxi_done', cash=int(round(n.get('taxi_cash') or 0)), car=n.get('ride_car'),
                            started=n.get('taxi_started_at'), at=int(t), hours=n.get('taxi_hours'), reason=reason))
            n.update(duty=None, busy_until=int(t), ride_car=None, taxi_started_at=None, taxi_until=None, taxi_hours=None,
                     taxi_cash=0, taxi_mult=1, taxi_recalled=0, taxi_fuel_end=None)
            return True
    p, se = n.get('phase'), n.get('autopilot_expires_at')
    if p == 'to_work' and t >= n['phase_until']:
        if t >= se:
            _leg(n, 'to_home', t, evs, engine)
        else:
            n['phase'], n['status'] = 'working', 'working'
        return True
    if p == 'working' and (t >= se or n['energy'] <= TIRED + EPS):
        _leg(n, 'to_home', t, evs, engine)
        return True
    if p == 'to_home' and t >= n['phase_until']:
        if t < se:
            n['phase'], n['status'] = 'sleeping', 'sleeping'
        else:
            _finish(n, t, evs)
        return True
    if p == 'sleeping':
        if t >= se:
            _finish(n, t, evs)
            return True
        if n['energy'] >= RESTED - EPS and se - t >= 2 * (n.get('travel_ms') or 0) + MIN_WORK_MS:
            _leg(n, 'to_work', t, evs, engine)
            return True
    return False


def advance(n, now, S, stop_at_done=False, engine=False):
    """Nalicza emocje i zmianę pracy od n['updated_at'] do now, odcinek po odcinku o stałych stawkach.

    Zwraca (n, zdarzenia): lista słowników kind = burnout | recovered | done (z kwotą do wypłaty)."""
    n = n if isinstance(n, dict) else dict(n)
    n = dict(n)
    evs = []
    t = n['updated_at']
    if n.get('leg_want'):     # v3.2: czeka na dyspozytora w chwili updated_at
        return n, evs
    _loyalty(n, t, evs)
    for _ in range(10_000):   # bezpiecznik; realnie kilka–kilkadziesiąt odcinków
        update_burnout(n, t, evs)
        end = _segment_end(n, t, now, S)
        r = rates(n, S)
        if end > t:
            h = (end - t) / HOUR
            for k, rk in zip(KEYS, r):
                n[k] = clamp(n[k] + rk * h)
            if n.get('duty') == 'taxi':      # v3.2: zarobek Taxi (burnout ×0,5 jak w usługach)
                n['taxi_cash'] = (n.get('taxi_cash') or 0) + TAXI_RATE * (n.get('taxi_mult') or 1) * h \
                    * (1 + trait_of(n).get('earn', 0.0)) * (BURNOUT_MULT if exhausted(n) else 1.0) * loyal_mult(n)
            if n.get('phase') == 'working' and n.get('assigned_service_id') in S.BY_ID:
                n['shift_cash'] = (n.get('shift_cash') or 0) + S.BY_ID[n['assigned_service_id']]['base_rate'] * h \
                    * (n.get('shift_demand') or 1) * (1 + (n.get('shift_bonus') or 0) + trait_earn(n)) * (n.get('shift_event') or 1) \
                    * (BURNOUT_MULT if exhausted(n) else 1.0) * loyal_mult(n)
        t = end
        _loyalty(n, t, evs)
        update_burnout(n, t, evs)
        if not _transition(n, t, evs, engine) and t >= now:
            break
        if n.get('leg_want'):  # v3.2: zatrzymanie przed odcinkiem — przydział kierowcy i auta w tej chwili
            n['updated_at'] = int(t)
            return n, evs
        if stop_at_done and evs and evs[-1]['kind'] == 'done':   # 2.7: AI Manager ponawia zmianę w tej chwili
            n['updated_at'] = int(t)
            return n, evs
    n['updated_at'] = int(max(n['updated_at'], now))
    return n, evs


def public(n, now):
    """Widok NPC dla API (zaokrąglone emocje, czas do ucieczki gdy nieszczęśliwy)."""
    tr = trait_of(n)
    out = {k: n[k] for k in ('id', 'name', 'avatar', 'status', 'assigned_service_id', 'assigned_car_id',
                             'autopilot_mode', 'autopilot_expires_at', 'hired_at')}
    out.update(energy=round(n['energy']), mood=round(n['mood']), hunger=round(n['hunger']),
               exhausted=exhausted(n), exhaustedSince=n.get('unhappy_since'),
               earnMult=BURNOUT_MULT if exhausted(n) else 1.0,
               phase=n.get('phase'), phaseUntil=n.get('phase_until'), shiftEndsAt=n.get('autopilot_expires_at'),
               shiftStartedAt=n.get('shift_started_at'),  # M4: start zmiany → pasek postępu w panelu usługi
               role=role_of(n), roleLabel=ROLE_LABEL[role_of(n)],
               trait=TRAIT_ALIAS.get(n.get('trait'), n.get('trait')), traitActive=bool(tr) or not n.get('trait'),
               traitLabel=(tr or TRAITS.get(TRAIT_ALIAS.get(n.get('trait'), n.get('trait') or ''), {})).get('label'), traitIcon=(tr or TRAITS.get(TRAIT_ALIAS.get(n.get('trait'), n.get('trait') or ''), {})).get('icon'),
               traitDesc=(tr or TRAITS.get(TRAIT_ALIAS.get(n.get('trait'), n.get('trait') or ''), {})).get('desc'),
               travelMs=n.get('travel_ms'), shiftCash=payout(n) if n.get('phase') else 0, bus=bool(n.get('shift_bus')),
               fuel=round(n['shift_fuel'], 1) if n.get('phase') and n.get('shift_fuel') is not None else None,
               duty=n.get('duty'), busyUntil=n.get('busy_until') if n.get('duty') else None, rideCar=n.get('ride_car'),
               transport=(n.get('leg_mode') or ('bus' if n.get('shift_bus') else 'car')) if n.get('phase') else None,
               loyalty=int(n.get('loyalty') or 0), loyal=bool(n.get('loyal_since')), loyalSince=n.get('loyal_since'),
               taxiUntil=n.get('taxi_until') if n.get('duty') == 'taxi' else None,
               taxiCash=int(round(n.get('taxi_cash') or 0)) if n.get('duty') == 'taxi' else 0,
               rideId=n.get('leg_ride'), prefCar=n.get('pref_car'), legacy=bool(n.get('shift_legacy')) if n.get('phase') else False)
    return out


class Refuse(Exception):
    """2.5: odmowa akcji dla jednego NPC (kod HTTP + komunikat) — pojedynczy endpoint zamienia na błąd, zbiorczy na wynik."""
    def __init__(self, code, msg):
        super().__init__(msg)
        self.code, self.msg = code, msg


def plan_shift(n, x, hours, car, t, wid, E, S, fuel=100.0, worn=False, engine=False):
    """Kopia NPC tuż po wysłaniu na zmianę (bez walidacji) — wspólna dla dispatch i estimate().

    3.2: paliwo auta przechodzi na zmianę; za mało na pierwszy odcinek → auto zostaje w garażu, NPC jedzie autobusem."""
    n = dict(n)
    clear_shift(n)
    need = E.fuel_need(car, E.HOPS.get(x['d'], 0)) if car else 0
    if car and fuel + EPS < need and not engine:
        car = None
    n.update(assigned_service_id=x['id'], assigned_car_id=car, autopilot_mode=f'{hours}h',
             autopilot_expires_at=t + hours * HOUR, shift_started_at=t,
             travel_ms=S.travel_ms(x, car, E, trait_of(n).get('travel', 1.0), worn),   # 3.3: zużyte auto wolniej
             shift_bonus=AUTOPILOT[hours], shift_event=E.ev_mult(t, 'service_cash'),
             shift_demand=S.demand(wid, x['id'], t), shift_bus=0 if car else 1,
             shift_fare_mult=E.ev_mult(t, 'bus_free'),
             shift_fuel=float(fuel) if car else None, shift_fuel_need=need if car else None,
             bus_travel_ms=S.travel_ms(x, None, E, trait_of(n).get('travel', 1.0)))
    if engine:   # v3.2: auto tylko preferowane; pierwszy odcinek przydziela dyspozytor w chwili t
        n.update(assigned_car_id=None, pref_car=car, shift_bus=0, shift_fuel=None, shift_fuel_need=None,
                 leg_want='to_work', shift_legacy=0)
    else:
        _start_leg(n, 'to_work', t)
    n['updated_at'] = t
    return n


def estimate(n, x, hours, car, t, wid, E, S, fuel=100.0, worn=False):
    """2.5/2.6: prognoza zmiany — prawdziwe advance() na kopii aż do powrotu. Ta sama matematyka co rozliczenie.

    Zwraca: cash (wypłata netto), endsAt (powrót), burnout (czy NPC wejdzie w przemęczenie), energy/mood/hunger na końcu."""
    m = plan_shift(n, x, hours, car, t, wid, E, S, fuel, worn)
    car = m['assigned_car_id']
    end = m['autopilot_expires_at'] + max(m['travel_ms'] or 0, m.get('bus_travel_ms') or 0) + 1
    out, evs = advance(m, end, S)
    done = next((e for e in evs if e['kind'] == 'done'), None)
    return dict(service=x['id'], name=x['name'], hours=hours, car=car, cash=done['cash'] if done else payout(out),
                demand=m['shift_demand'], travelMs=m['travel_ms'], endsAt=int(end),
                burnout=exhausted(n) or any(e['kind'] == 'burnout' for e in evs),
                energy=round(out['energy']), mood=round(out['mood']), hunger=round(out['hunger']))


def available(s, E, S):
    """Usługi, do których gracz może wysłać NPC (odblokowane i z wymaganym poziomem)."""
    lvl, have = E.level(s['xp']), set(S.unlocked_ids(s))
    return [x for x in S.SERVICES if x['id'] in have and lvl >= x['level']]


def ranked(n, s, hours, car, t, wid, E, S):
    """Wszystkie dostępne usługi posortowane wg prognozowanej wypłaty (malejąco)."""
    fuel = E.fuel_of(s, car) if car else 100.0
    worn = bool(car) and E.worn(s, car)
    return sorted((estimate(n, x, hours, car, t, wid, E, S, fuel, worn) for x in available(s, E, S)), key=lambda e: -e['cash'])


def best_plan(n, s, hours, car, t, wid, E, S, safe=False):
    """2.5: najlepsza usługa dla NPC; safe=True → tylko plany bez przemęczenia (None, gdy żadnego)."""
    for e in ranked(n, s, hours, car, t, wid, E, S):
        if not safe or not e['burnout']:
            return e
    return None


def fastest_cars(s, S):
    """Auta gracza od najszybszego (najmniejszy współczynnik czasu dojazdu)."""
    return sorted((s.get('garage') or []), key=lambda v: S.TRAVEL_FACTOR.get(v, 1.0))


def ready_cars(s, S, E):
    """3.2: auta od najszybszego z paliwem na najdłuższy odcinek (automatyczny przydział: batch, manager, asystent)."""
    return [v for v in fastest_cars(s, S) if E.fuel_ready(s, v)]


def bump_streak(disp, t, S):
    """2.4c: licznik tras „z rzędu” (odstęp < COOLDOWN_MS); 10. włącza przerwę. 2.5: akcja zbiorcza = 1."""
    streak = 0 if t - int(disp.get('lastAt') or 0) >= S.COOLDOWN_MS else int(disp.get('streak') or 0)
    streak += 1
    disp.update(lastAt=t, streak=0 if streak >= S.COOLDOWN_AFTER else streak,
                cooldownUntil=t + S.COOLDOWN_MS if streak >= S.COOLDOWN_AFTER else int(disp.get('cooldownUntil') or 0))


def cooldown_left(s, t, S):
    left = int((s.get('dispatch') or {}).get('cooldownUntil') or 0) - t
    if left > 0:
        raise Refuse(409, f'Przerwa dyspozytora — {left // 60000}:{left % 60000 // 1000:02d}. Po {S.COOLDOWN_AFTER} trasach z rzędu kierowcy odpoczywają {S.COOLDOWN_MS // 60000} min.')


class RecruitIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['service', 'driver'] = 'service'   # v3.2 Zad. 1


class TaxiIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    hours: Literal[2, 4, 8]
    car_id: Optional[str] = Field(default=None, max_length=24)


def taxi_net(v, E):
    """Netto $/h Taxi danym autem (zarobek − paliwo − serwis za zużycie) — kolejność automatycznego wyboru auta."""
    g = E.car(v)
    return TAXI_RATE * TAXI_MULT.get(v, 1.0) - TAXI_HOPS_PER_H * g.get('fuel', 0) * g.get('fuelPrice', 1.0) \
        - TAXI_WEAR_PER_H * g.get('service', 0) / 100


class RoleIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    role: Literal['service', 'driver']


class DispatchIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    service_id: str = Field(min_length=2, max_length=24)
    hours: Literal[2, 4, 8, 12]
    car_id: Optional[str] = Field(default=None, max_length=24)


def manager_view(s, t):
    """2.7: stan AI Managera dla API."""
    m = (s or {}).get('aiManager') or {}
    return dict(active=bool(m.get('until')) and m['until'] > t, until=m.get('until'), since=m.get('since'),
                policy=m.get('policy'), hours=m.get('hours'), feed=m.get('feed', True), exclude=m.get('exclude') or [],
                shifts=int(m.get('shifts') or 0), earned=int(m.get('earned') or 0), fees=int(m.get('fees') or 0),
                feeds=int(m.get('feeds') or 0), commission=MANAGER_COMMISSION, minLevel=MANAGER_MIN_LEVEL)


class ManagerIn(BaseModel):
    """2.7: włączenie (enabled=True) lub wyłączenie AI Managera."""
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    policy: Literal['max', 'safe'] = 'max'
    hours: Literal[2, 4, 8, 12] = 8
    feed: bool = True
    duration_h: int = Field(default=24, ge=1, le=168)
    exclude: List[int] = Field(default_factory=list, max_length=MAX_NPC)


class FeedIn(BaseModel):
    """4.4: feed_npc — jeden NPC, posiłek 1–3 (domyślnie najlepszy dostępny w Buffecie)."""
    model_config = ConfigDict(extra='forbid')
    npc_id: int = Field(ge=1)
    meal: Optional[int] = Field(default=None, ge=1, le=3)


class BatchIn(BaseModel):
    """2.5: akcja zbiorcza. npcs: lista id (≤ 15) albo 'idle' (wolni) / 'all'."""
    model_config = ConfigDict(extra='forbid')
    action: Literal['dispatch', 'recall', 'feed', 'all_to_buffet']   # 4.4: all_to_buffet (feed = alias)
    meal: Optional[int] = Field(default=None, ge=1, le=3)
    npcs: Union[Literal['idle', 'all'], List[int]] = 'idle'
    service_id: Optional[str] = Field(default=None, min_length=2, max_length=24)   # 'best' = najlepsza dla każdego
    hours: Optional[Literal[2, 4, 8, 12]] = None
    cars: Literal['auto', 'none'] = 'none'

    @field_validator('npcs')
    @classmethod
    def _limit(cls, v):
        if isinstance(v, list) and not 1 <= len(v) <= MAX_NPC:
            raise ValueError(f'od 1 do {MAX_NPC} NPC')
        return v


def install(app, d, E, S):
    db, now, fail, world, own, auth, rate, audit, emit = d.db, d.now, d.fail, d.world, d.own, d.auth, d.rate, d.audit, d.emit

    c = db.connect()
    try:
        c.executescript(SCHEMA)
        c.executescript(RIDES_SCHEMA)   # v3.2: kursy kierowców
        have = {r['name'] for r in c.execute('PRAGMA table_info(npcs)')}
        for name, ddl in SHIFT_COLUMNS + EXTRA_COLUMNS + V32_COLUMNS:   # 2.4/2.3b/v3.2: addytywna migracja kolumn
            if name not in have:
                c.execute('ALTER TABLE npcs ADD COLUMN ' + name + ' ' + ddl)
        if 'role' not in have:   # v3.2: pierwsze uruchomienie — D2 + dokończenie trwających zmian po staremu
            c.execute("UPDATE npcs SET role='driver' WHERE trait='kierowca' AND phase IS NULL")
            c.execute('UPDATE npcs SET shift_legacy=1 WHERE phase IS NOT NULL')
        c.execute("UPDATE npcs SET trait='kierowca_rajdowy' WHERE trait='kierowca' AND phase IS NULL")
        # D2: kierowca w trakcie starej zmiany zostaje DRIVER-em dopiero po jej końcu (handle 'done')
        for old, new in (('rower', 'dostawczak'), ('bus', 'van'), ('supercar', 'suv')):   # 3.1: auta z katalogu 0.59
            c.execute('UPDATE npcs SET assigned_car_id=? WHERE assigned_car_id=?', (new, old))
            c.execute('UPDATE vehicles SET type=? WHERE type=?', (new, old))
        for r in c.execute('SELECT id FROM npcs WHERE trait IS NULL').fetchall():   # 2.3b: NPC sprzed cech
            c.execute('UPDATE npcs SET trait=? WHERE id=?', (TRAIT_IDS[r['id'] % len(TRAIT_IDS)], r['id']))
        c.commit()
    finally:
        c.close()

    MUTABLE = ('energy', 'mood', 'hunger', 'status', 'assigned_service_id', 'assigned_car_id', 'autopilot_mode',
               'autopilot_expires_at', 'unhappy_since', 'warned_at', 'updated_at', 'trait') \
        + tuple(k for k, _ in SHIFT_COLUMNS) + tuple(k for k, _ in V32_COLUMNS)

    def save(c, n):
        c.execute('UPDATE npcs SET ' + ','.join(k + '=?' for k in MUTABLE) + ' WHERE id=?',
                  tuple(n.get(k) for k in MUTABLE) + (n['id'],))

    def credit(c, cid, amount, text, t, fee=None, fuel=None):
        """Wypłata na konto postaci (gotówka nie spada poniżej 0) + wpis w dzienniku gracza. fee: prowizja managera (2.7)."""
        row = c.execute('SELECT state_json FROM characters WHERE id=?', (cid,)).fetchone()
        if not row:
            return
        st = json.loads(row['state_json'])
        if amount > 0:
            amount = round(amount * E.prestige_mult(st))   # 4.5: bonus resetu od wypłat NPC
        st['cash'] = max(0, (st.get('cash') or 0) + amount)
        if fuel and fuel[0] in (st.get('garage') or []):   # 3.2: reszta paliwa wraca do auta
            E.set_fuel(st, fuel[0], fuel[1])
        if fee is not None and isinstance(st.get('aiManager'), dict):
            mg = st['aiManager']
            mg['earned'] = int(mg.get('earned') or 0) + amount
            mg['fees'] = int(mg.get('fees') or 0) + fee
        E.log(st, text, t)
        c.execute('UPDATE characters SET state_json=? WHERE id=?',
                  (json.dumps(st, ensure_ascii=False, separators=(',', ':')), cid))

    def load(c, cid):
        row = c.execute('SELECT state_json FROM characters WHERE id=?', (cid,)).fetchone()
        return json.loads(row['state_json']) if row else None

    def store(c, cid, st):
        c.execute('UPDATE characters SET state_json=? WHERE id=?',
                  (json.dumps(st, ensure_ascii=False, separators=(',', ':')), cid))

    def handle(c, n, wid, evs, t):
        """Zdarzenia z advance(): powiadomienia + wypłaty (2.7: minus prowizja managera)."""
        cid = n['character_id']
        for ev in evs:
            if ev['kind'] == 'burnout':
                why = {'energy': 'jest wyczerpany', 'mood': 'ma zły nastrój', 'hunger': 'jest głodny'}[ev['cause']]
                emit(c, wid, [cid], 'npc.burnout', dict(npc=n['id'], name=n['name'], cause=ev['cause'],
                     text=f"{n['name']} {why} — przemęczenie: zarabia o połowę mniej. Daj mu odpocząć albo coś zjeść."))
            elif ev['kind'] == 'recovered':
                emit(c, wid, [cid], 'npc.recovered', dict(npc=n['id'], name=n['name'],
                     text=f"{n['name']} doszedł do siebie — znowu pracuje na 100%."))
            elif ev['kind'] == 'fuel_out':
                emit(c, wid, [cid], 'npc.fuel_out', dict(npc=n['id'], name=n['name'], car=n.get('assigned_car_id'),
                     text=f"{n['name']}: w aucie skończyło się paliwo — do końca zmiany jeździ autobusem."))
            elif ev['kind'] == 'loyal':
                text = f"Twój NPC {n['name']} staje się wobec Ciebie lojalny! (+5% zarobku, bez negatywnych efektów cechy)"
                credit(c, cid, 0, text, ev['at'])
                emit(c, wid, [cid], 'npc.loyal', dict(npc=n['id'], name=n['name'], text=text))
            elif ev['kind'] == 'taxi_done':
                taxi_settle(c, n, wid, ev)
            elif ev['kind'] == 'done':
                x = S.BY_ID.get(ev['service']) or {}
                fee = round(max(0, ev['cash']) * MANAGER_COMMISSION) if ev.get('manager') else 0
                net = ev['cash'] - fee
                if net > 0 and E.TERRITORY_HOOK[0] and x.get('d', 1) >= 2 and E.TERRITORY_HOOK[0](c, cid, E.DISTRICTS[x['d'] - 2]):
                    net = round(net * (1 + E.CONTROL_NPC_BONUS))   # 8.3 GDD v3.1: +5% $ z pracy NPC w dzielnicy sojuszu (>55%)
                text = f"{n['name']} wraca z {x.get('name', 'pracy')}: {net:+d} $" + (' (odwołany — bez bonusu)' if ev['recalled'] else '') \
                    + (f' (AI Manager: prowizja {fee} $)' if ev.get('manager') else '')
                if E.BP_HOOK[0]:
                    E.BP_HOOK[0](c, cid, 'npc')   # 8.4 GDD v3.1: XP przepustki za zmianę NPC
                credit(c, cid, net, text, t, fee if ev.get('manager') else None,
                       (ev['car'], ev['fuel']) if ev.get('car') and ev.get('fuel') is not None else None)
                emit(c, wid, [cid], 'npc.shift_done', dict(npc=n['id'], name=n['name'], cash=net, fee=fee,
                     service=ev['service'], recalled=ev['recalled'], manager=bool(ev.get('manager')), text=text))

    def taxi_settle(c, n, wid, ev):
        """v3.2: koniec Taxi — wypłata (prestiż, bez bonusu terytorium), paliwo i zużycie wg przejechanego czasu."""
        cid, car = n['character_id'], ev['car']
        h = max(0.0, (ev['at'] - (ev['started'] or ev['at'])) / HOUR)
        g = E.car(car)
        fuel = round(h * TAXI_HOPS_PER_H * g.get('fuel', 0), 4)
        wear = h * TAXI_WEAR_PER_H * trait_of(n).get('wear', 1.0)
        st = load(c, cid)
        if st and car in (st.get('garage') or []):
            E.set_fuel(st, car, E.fuel_of(st, car) - fuel)
            E.set_wear(st, car, E.wear_of(st, car) + wear)
            store(c, cid, st)
        c.execute("UPDATE npc_rides SET back_at=?, arrive_at=?, cash=?, fuel=?, wear=? WHERE driver_id=? AND kind='taxi' "
                  'AND back_at>=? AND depart_at=?', (ev['at'], ev['at'], ev['cash'], fuel, wear, n['id'], ev['at'], ev['started']))
        why = {'done': '', 'recalled': ' (odwołany wcześniej)', 'fuel': ' — skończyło się paliwo, zatankuj auto',
               'tired': ' — kierowca jest zmęczony (energia 30)'}[ev['reason']]
        text = f"{n['name']} kończy Taxi ({E.car(car).get('name', car)}, {h:.1f} h): {ev['cash']:+d} $" + why
        if E.BP_HOOK[0]:
            E.BP_HOOK[0](c, cid, 'npc')
        credit(c, cid, ev['cash'], text, ev['at'])
        emit(c, wid, [cid], 'npc.taxi_done', dict(npc=n['id'], name=n['name'], cash=ev['cash'], car=car,
             hours=round(h, 2), reason=ev['reason'], text=text))

    def manager_of(c, n):
        """Aktywna konfiguracja AI Managera dla tego NPC albo None."""
        st = load(c, n['character_id'])
        m = (st or {}).get('aiManager') or {}
        if not m.get('until') or n['id'] in (m.get('exclude') or []) or role_of(n) != 'service':
            return None
        return m

    def pick_car(c, st, n, prefer, at):
        """Auto dla zmiany managera: poprzednie auto NPC, potem wolne od najszybszego, inaczej autobus (None)."""
        busy = {r['assigned_car_id'] for r in c.execute(
            'SELECT assigned_car_id FROM npcs WHERE character_id=? AND id<>? AND phase IS NOT NULL AND assigned_car_id IS NOT NULL',
            (n['character_id'], n['id']))}
        ch = c.execute('SELECT travel_destination, travel_started FROM characters WHERE id=?', (n['character_id'],)).fetchone()
        driving = st.get('travelCar') if ch and ch['travel_destination'] else None
        busy |= {r['car_id'] for r in c.execute('SELECT car_id FROM npc_rides WHERE character_id=? AND back_at>?',
                                                 (n['character_id'], at))}   # v3.2: auta w kursach
        for v in ([prefer] if prefer else []) + ready_cars(st, S, E):
            if v and not E.fuel_ready(st, v):
                continue
            if v and v in (st.get('garage') or []) and v not in busy and v != driving and E.vehicle_busy_until(st, v, at) <= at:
                return v
        return None

    def manager_dispatch(c, n, wid, m, at, prefer, drivers=()):
        """2.7: AI Manager wysyła NPC w chwili `at` (posiłek → wybór planu wg polityki → start). None = nie wysłał."""
        cid = n['character_id']
        if n['energy'] < DISPATCH_MIN_ENERGY - EPS:
            return None
        st = load(c, cid)
        mg = st.setdefault('aiManager', {})            # liczniki na świeżym stanie (credit mógł je zmienić)
        lvl = max(1, E.buffet_level(st))              # 4.4: manager zamawia najlepszy dostępny posiłek
        if n['hunger'] < MANAGER_FEED_BELOW and m.get('feed', True) and st['cash'] >= MEALS[lvl]['cost']:
            st['cash'] -= MEALS[lvl]['cost']
            n = eat(n, lvl, at, [])
            mg['feeds'] = int(mg.get('feeds') or 0) + 1
        free = any((not d.get('duty') or (d.get('busy_until') or 0) <= at) and d['energy'] >= TIRED - EPS
                   for d in drivers)   # v3.2: auto tylko z kierowcą (kurs kończący się do `at` = wolny)
        car = pick_car(c, st, n, prefer, at) if free else None
        if not car and st['cash'] < BUS_FARE and E.ev_mult(at, 'bus_free') > 0:
            return None
        hours = int(m.get('hours') or 8)
        plan = best_plan(n, st, hours, car, at, wid, E, S, safe=m.get('policy') == 'safe')
        if plan is None and m.get('policy') == 'safe':        # same przemęczenia → regeneracja nastroju (Biblioteka/Park)
            regen = [e for e in ranked(n, st, hours, car, at, wid, E, S) if e['service'] in S.REGEN]
            plan = regen[0] if regen else None
        if plan is None:
            return None
        n = plan_shift(n, S.BY_ID[plan['service']], hours, car, at, wid, E, S, E.fuel_of(st, car) if car else 100.0,
                       bool(car) and E.worn(st, car), engine=True)
        n['shift_manager'] = 1
        mg['shifts'] = int(mg.get('shifts') or 0) + 1
        store(c, cid, st)
        return n

    def run_npc(c, n, wid, t, drivers):
        """Jeden NPC usługowy od updated_at do t — albo do pierwszego żądania odcinka (leg_want), które rozstrzyga
        dyspozytor w settle_character. 2.7: z AI Managerem zatrzymuje się na końcu zmiany i wysyła NPC dalej
        (także offline); odpoczywającego (energia < 40) — w chwili, gdy ją odzyska."""
        n = dict(n)
        m = manager_of(c, n)
        prefer = n.get('pref_car') or n.get('assigned_car_id')
        for _ in range(MANAGER_MAX_CHAIN):
            if n.get('leg_want'):
                return n
            if not m:
                break
            if not n.get('phase'):
                at = max(n['updated_at'], int(m.get('since') or 0))
                if at > t:
                    break
                if at > n['updated_at']:
                    n, evs = advance(n, at, S, engine=True)
                    handle(c, n, wid, evs, t)
                regen = IDLE_RATES[0] * trait_of(n).get('sleep_regen', 1.0)
                ready = at if n['energy'] >= DISPATCH_MIN_ENERGY - EPS else int(at + (DISPATCH_MIN_ENERGY - n['energy']) / regen * HOUR) + 1
                if ready > t or ready >= m['until']:
                    break
                if ready > n['updated_at']:
                    n, evs = advance(n, ready, S, engine=True)
                    handle(c, n, wid, evs, t)
                sent = manager_dispatch(c, n, wid, m, ready, prefer, drivers)
                if sent is None:
                    break
                n = sent
                continue                      # nowy odcinek to_work czeka na dyspozytora
            n, evs = advance(n, t, S, stop_at_done=True, engine=True)
            handle(c, n, wid, evs, t)
            if n.get('leg_want'):
                return n
            done = [e for e in evs if e['kind'] == 'done']
            if not done or n['updated_at'] >= t:
                break
            prefer = done[-1].get('car') or done[-1].get('pref')
            m = manager_of(c, n)
        if not n.get('leg_want'):
            n, evs = advance(n, t, S, engine=True)
            handle(c, n, wid, evs, t)
        return n

    def settle(c, row, wid, t):
        """Zgodność wstecz: rozliczenie zawsze dla całej postaci (niezmiennik v3.2)."""
        team = settle_character(c, row['character_id'], wid, t)
        return next((m for m in team if m['id'] == row['id']), None)

    # --- v3.2 Zad. 3: dyspozytor kursów ---
    def player_car(c, cid, st):
        ch = c.execute('SELECT travel_destination FROM characters WHERE id=?', (cid,)).fetchone()
        return st.get('travelCar') if ch and ch['travel_destination'] else None

    def car_free(c, cid, st, v, depart):
        if c.execute('SELECT 1 FROM npc_rides WHERE character_id=? AND car_id=? AND back_at>? LIMIT 1',
                     (cid, v, depart)).fetchone():
            return False
        if c.execute('SELECT 1 FROM npcs WHERE character_id=? AND phase IS NOT NULL AND shift_legacy=1 AND assigned_car_id=? '
                     'AND shift_bus=0 LIMIT 1', (cid, v)).fetchone():
            return False                                     # auto przypięte do zmiany sprzed v3.2
        return E.vehicle_busy_until(dict(st, npcCars={}), v, depart) <= depart   # stare trasy aut

    def find_pair(c, cid, st, drivers, at, x, phase, prefer):
        """Wolny kierowca (energia ≥ 30, najdłużej wolny) + wolne auto z paliwem na kurs (preferowane → najszybsze).
        DROP: kierowca wolny od `at`; PICKUP: od `at − T` (dojazd po pasażerów na pusto). None → autobus."""
        hops = E.HOPS.get(x['d'], 0)
        driving = player_car(c, cid, st)
        cars = [v for v in dict.fromkeys(([prefer] if prefer else []) + fastest_cars(st, S))
                if v in (st.get('garage') or []) and v != driving and E.fuel_of(st, v) + EPS >= 2 * E.fuel_need(v, hops)]
        for d in sorted(drivers, key=lambda d: (d.get('busy_until') or 0, d['id'])):
            if d.get('duty') or d.get('phase') or d['energy'] < TIRED - EPS:
                continue
            tr = trait_of(d).get('travel', 1.0)
            for v in cars:
                tm = S.travel_ms(x, v, E, tr, E.worn(st, v))
                depart = at if phase == 'to_work' else at - tm
                if (d.get('busy_until') or 0) > depart or not car_free(c, cid, st, v, depart):
                    continue
                return d, v, tm, depart
        return None

    def allocate(c, cid, wid, group, T, drivers):
        """Przydział transportu dla żądań odcinków z tej samej chwili T. Pasażerowie jadący w tym samym kierunku
        do tej samej dzielnicy dzielą auto (do SEATS); brak pary kierowca + auto → autobus (bilet, ×2,0)."""
        st = load(c, cid)
        buckets = {}
        for n in sorted(group, key=lambda n: n['id']):
            x = S.BY_ID[n['assigned_service_id']]
            buckets.setdefault((n['leg_want'], x['d']), []).append(n)
        for (phase, dist), pax in sorted(buckets.items()):
            x = S.BY_ID[pax[0]['assigned_service_id']]
            while pax:
                pair = find_pair(c, cid, st, drivers, T, x, phase, pax[0].get('pref_car'))
                if not pair:
                    for n in pax:
                        begin_leg(n, phase, T, 'bus', n.get('bus_travel_ms') or n.get('travel_ms') or 0)
                    if drivers or any(n.get('pref_car') for n in pax):
                        names = ', '.join(n['name'] for n in pax)
                        emit(c, wid, [cid], 'npc.bus_fallback', dict(npcs=[n['id'] for n in pax], phase=phase,
                             text=f"{names}: brak wolnego kierowcy z autem — jazda autobusem ({BUS_FARE} $, 2× dłużej)."))
                    break
                d, v, tm, depart = pair
                take, pax = pax[:SEATS.get(v, 1)], pax[SEATS.get(v, 1):]
                hops = max(1, int(E.HOPS.get(x['d'], 0) or 0))
                fuel = 2 * E.fuel_need(v, E.HOPS.get(x['d'], 0))          # tam i z powrotem (jeden odcinek na pusto)
                wear = WEAR_PER_HOP * hops * 2 * trait_of(d).get('wear', 1.0)
                E.set_fuel(st, v, E.fuel_of(st, v) - fuel)
                E.set_wear(st, v, E.wear_of(st, v) + wear)
                arrive = T + tm
                back = T + 2 * tm if phase == 'to_work' else T + tm
                rid = c.execute('INSERT INTO npc_rides(character_id,driver_id,car_id,kind,district,depart_at,meet_at,'
                                'arrive_at,back_at,passengers,fuel,wear) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
                                (cid, d['id'], v, 'drop' if phase == 'to_work' else 'pickup', x['d'], int(depart), int(T),
                                 int(arrive), int(back), json.dumps([n['id'] for n in take]), fuel, wear)).lastrowid
                d.update(duty='ferry', busy_until=int(back), ride_car=v)
                for n in take:
                    begin_leg(n, phase, T, 'car', tm, rid)
        store(c, cid, st)

    def settle_character(c, cid, wid, t):
        """v3.2: JEDYNE wejście rozliczenia — zawsze wszyscy NPC postaci naraz (niezmiennik: nigdy pojedynczy NPC),
        bo kierowcy i auta są wspólne dla całej ekipy. Zwraca listę NPC po rozliczeniu (kolejność wg id)."""
        rows = c.execute('SELECT * FROM npcs WHERE character_id=? ORDER BY id', (cid,)).fetchall()
        by = {r['id']: dict(r) for r in rows}
        drv = [i for i, n in by.items() if role_of(n) == 'driver' and not n.get('phase')]

        def drivers_to(T):
            for i in drv:
                if by[i]['updated_at'] <= T:          # także == T: przejścia w tej chwili (recall Taxi)
                    nd, evs = advance(by[i], T, S)
                    handle(c, nd, wid, evs, t)
                    by[i].clear()
                    by[i].update(nd)                  # ta sama referencja — allocate() widzi aktualny stan

        # 1) każdy NPC usługowy do t albo do pierwszego żądania odcinka (niezależni od siebie)
        for i in by:
            if i not in drv:
                by[i] = run_npc(c, by[i], wid, t, [by[j] for j in drv])
        # 2) żądania w porządku czasowym: kierowcy do chwili T → przydział (łączenie) → dalszy bieg pasażerów
        for _ in range(20_000):
            wants = [n for n in by.values() if n.get('leg_want')]
            if not wants:
                break
            T = min(n['updated_at'] for n in wants)
            drivers_to(T)
            group = [n for n in wants if n['updated_at'] == T]
            allocate(c, cid, wid, group, T, [by[j] for j in drv])
            for n in group:
                by[n['id']] = run_npc(c, n, wid, t, [by[j] for j in drv])
        drivers_to(t)
        for n in by.values():
            save(c, n)
        return [by[i] for i in sorted(by)]

    def roster(c, ch, wid):
        return settle_character(c, ch['id'], wid, now())

    def payload(c, ch, wid, s):
        t = now()
        team = roster(c, ch, wid)
        cap = slots(s)
        names = {n['id']: n['name'] for n in team}
        rides = [dict(id=r['id'], kind=r['kind'], driver=r['driver_id'], driverName=names.get(r['driver_id']), car=r['car_id'],
                      district=r['district'], departAt=r['depart_at'], meetAt=r['meet_at'], arriveAt=r['arrive_at'],
                      backAt=r['back_at'], passengers=json.loads(r['passengers'] or '[]'))
                 for r in c.execute('SELECT * FROM npc_rides WHERE character_id=? AND back_at>? ORDER BY depart_at',
                                    (ch['id'], t))]
        drivers = [n for n in team if role_of(n) == 'driver']
        return dict(npcs=[public(n, t) for n in team], count=len(team), slots=cap, maxSlots=MAX_NPC,
                    rides=rides, seats=SEATS, byRole={r: sum(role_of(n) == r for n in team) for r in ROLES},
                    drivers=dict(total=len(drivers), free=sum(not n.get('duty') and n['energy'] >= TIRED - EPS for n in drivers)),
                    nextCost=recruit_cost(len(team)) if len(team) < cap else None,
                    canRecruitHere=(ch['current_district'] or 1) == HOME_DISTRICT and not ch['travel_destination'],
                    dispatchCooldownUntil=int((s.get('dispatch') or {}).get('cooldownUntil') or 0),
                    manager=manager_view(load(c, ch['id']), t))   # 2.7: świeży stan (po prowizjach z roster)

    @app.get('/api/worlds/{wid}/npcs')
    def npcs_list(wid: int, u=Depends(auth)):
        with db.tx() as c:
            world(c, wid)
            ch = own(c, u['id'], wid)
            return payload(c, ch, wid, json.loads(ch['state_json']))

    @app.post('/api/worlds/{wid}/npcs/recruit')
    def npcs_recruit(wid: int, data: RecruitIn, request: Request, u=Depends(auth)):
        key = request.headers.get('idempotency-key', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
            fail(422, 'Brak poprawnego identyfikatora operacji.')
        rate(request, 'npc-recruit-' + str(u['id']), 40, HOUR)  # 2.4c/v3.2: 40/h (20 miejsc — zespół da się zapełnić od razu)
        okey = 'npc-recruit:' + key
        with db.tx() as c:
            old = c.execute('SELECT response_json FROM operations WHERE account_id=? AND world_id=? AND key=?',
                            (u['id'], wid, okey)).fetchone()
            if old:
                return json.loads(old['response_json'])
            w = world(c, wid, True)
            ch = own(c, u['id'], wid)
            if ch['travel_destination']:
                fail(409, 'Jesteś w drodze — rekrutacja w Rezydencji po przyjeździe.')
            if (ch['current_district'] or 1) != HOME_DISTRICT:
                fail(409, 'Rekrutacja odbywa się w Rezydencji (dzielnica Nadmorskie).')
            team = roster(c, ch, wid)   # najpierw wypłaty z zakończonych zmian, potem świeży stan
            ch = own(c, u['id'], wid)
            s = json.loads(ch['state_json'])
            E.sync(s, now(), w['speed'])
            cap = slots(s)
            if len(team) >= cap:
                fail(409, f'Brak miejsc w Rezydencji ({cap}). Rozbuduj Rezydencję, aby zatrudnić więcej NPC.')
            cost = recruit_cost(len(team))
            if s['cash'] < cost:
                fail(409, f'Rekrutacja kosztuje {cost} $.')
            s['cash'] -= cost
            t = now()
            taken = {n['name'] for n in team}
            name = random.choice([x for x in NAMES if x not in taken] or NAMES)
            avatar = random.choice(AVATARS)
            trait = random.choice(trait_pool(data.role))   # 2.3b: osobowość (v3.2: pula wg roli)
            nid = c.execute('INSERT INTO npcs(character_id,name,avatar,trait,role,hired_at,updated_at,loy_day,loy_min) '
                            'VALUES(?,?,?,?,?,?,?,?,?)',
                            (ch['id'], name, avatar, trait, data.role, t, t, t // DAY, 100.0)).lastrowid
            c.execute('UPDATE characters SET state_json=? WHERE id=?',
                      (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))
            audit(c, u['id'], 'npc.recruit', dict(npc=nid, character=ch['id'], cost=cost, name=name))
            ch = dict(ch, state_json=json.dumps(s))
            result = dict(message=f'{name} dołącza do zespołu jako {ROLE_LABEL[data.role].lower()} (−{cost} $).', cash=s['cash'], **payload(c, ch, wid, s))
            c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',
                      (u['id'], wid, okey, 'npc-recruit', json.dumps(result, ensure_ascii=False), t))
            return result

    def cars_in_use(c, cid, t):
        """2.4c: {auto: przewidywany koniec zmiany z powrotem} — dla starych tras i podróży gracza."""
        rows = c.execute('SELECT assigned_car_id car, autopilot_expires_at e, travel_ms tm FROM npcs '
                         'WHERE character_id=? AND phase IS NOT NULL AND assigned_car_id IS NOT NULL', (cid,)).fetchall()
        out = {r['car']: int(r['e'] + (r['tm'] or 0)) for r in rows if r['e'] and r['e'] + (r['tm'] or 0) > t}
        for r in c.execute('SELECT car_id, MAX(back_at) b FROM npc_rides WHERE character_id=? AND back_at>? GROUP BY car_id',
                           (cid, t)):                       # v3.2: auta w kursach kierowców / na Taxi
            out[r['car_id']] = max(out.get(r['car_id'], 0), int(r['b']))
        return out

    def once(c, u, wid, request, scope, fn):
        """Idempotentne wykonanie akcji NPC (tabela operations, klucz z prefiksem)."""
        key = request.headers.get('idempotency-key', '')
        if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}', key):
            fail(422, 'Brak poprawnego identyfikatora operacji.')
        okey = scope + ':' + key
        old = c.execute('SELECT response_json FROM operations WHERE account_id=? AND world_id=? AND key=?',
                        (u['id'], wid, okey)).fetchone()
        if old:
            return json.loads(old['response_json'])
        result = fn()
        c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',
                  (u['id'], wid, okey, scope, json.dumps(result, ensure_ascii=False), now()))
        return result

    def mine(c, ch, wid, nid):
        team = roster(c, ch, wid)
        n = next((x for x in team if x['id'] == nid), None)
        if not n:
            fail(404, 'Nie masz takiego NPC.')
        return team, n

    # --- 2.5: rdzenie akcji (wspólne dla pojedynczych endpointów i akcji zbiorczej) ---
    def start_shift(c, s, team, n, service_id, hours, car, t, wid):
        """Walidacja + wysłanie jednego NPC. Zwraca nowy stan NPC; Refuse przy odmowie. Nie rusza licznika tras."""
        x = S.BY_ID.get(service_id)
        if not x:
            raise Refuse(404, 'Nieznana usługa.')
        if role_of(n) == 'driver':
            raise Refuse(409, f"{n['name']} jest kierowcą — nie pracuje w usługach. Wyślij go na Taxi albo zmień rolę.")
        if n.get('phase'):
            raise Refuse(409, f"{n['name']} jest już na zmianie.")
        if n['energy'] < DISPATCH_MIN_ENERGY:
            raise Refuse(409, f"{n['name']} jest zbyt zmęczony (energia < {DISPATCH_MIN_ENERGY}). Daj mu odpocząć w Rezydencji.")
        if E.level(s['xp']) < x['level'] or service_id not in S.unlocked_ids(s):
            raise Refuse(409, f"{x['name']} nie jest odblokowana.")
        drivers = [m for m in team if role_of(m) == 'driver']
        if car:   # v3.2: auto = preferencja dla dyspozytora; prowadzi wyłącznie DRIVER
            if car not in (s.get('garage') or []):
                raise Refuse(409, 'Tego auta nie ma w twoim garażu.')
            if not drivers:
                raise Refuse(409, 'Autami z garażu jeżdżą tylko kierowcy — zatrudnij NPC w roli Kierowca albo wyślij autobusem.')
        free = any(not m.get('duty') and m['energy'] >= TIRED - EPS for m in drivers)
        if not free and s['cash'] < BUS_FARE and E.ev_mult(t, 'bus_free') > 0:
            raise Refuse(409, f'Brak wolnego kierowcy i gotówki na bilet autobusowy ({BUS_FARE} $).')
        guess = car or next((v for v in ready_cars(s, S, E)), None) if free else None   # prognoza czasu dojazdu
        n = plan_shift(n, x, hours, guess, t, wid, E, S, E.fuel_of(s, guess) if guess else 100.0,
                       bool(guess) and E.worn(s, guess), engine=True)
        n['pref_car'] = car
        save(c, n)
        return n

    def recall_one(c, n, wid, t):
        if n.get('duty') == 'taxi':   # v3.2: Taxi — koniec teraz, wypłata za przepracowany czas
            n = dict(n, taxi_recalled=1, taxi_until=min(n['taxi_until'], t), busy_until=min(n['busy_until'] or t, t))
            save(c, n)
            team = settle_character(c, n['character_id'], wid, t)
            return next(m for m in team if m['id'] == n['id'])
        if n.get('duty') == 'ferry':
            raise Refuse(409, f"{n['name']} wiezie właśnie ekipę — wróci za chwilę.")
        if not n.get('phase'):
            raise Refuse(409, f"{n['name']} nie jest na zmianie.")
        n = dict(n, shift_recalled=1, autopilot_expires_at=min(n['autopilot_expires_at'], t))
        save(c, n)
        team = settle_character(c, n['character_id'], wid, t)   # przejście fazy od razu (sen → wypłata, praca → powrót)
        return next(m for m in team if m['id'] == n['id'])

    def feed_one(c, wid, s, n, t, meal=None):
        """4.4: posiłek z Buffetu (mutuje s['cash']). meal 1–3, domyślnie najlepszy dostępny."""
        lvl = max(1, E.buffet_level(s))        # korekta usera: „Zwykłe jedzenie” zawsze dostępne, Buffet odblokowuje wyższe tiery
        meal = int(meal or lvl)
        if meal > lvl:
            raise Refuse(409, f"{MEALS[meal]['name']} wymaga Buffetu na poziomie {meal}.")
        if n['hunger'] >= 100 - EPS:
            raise Refuse(409, f"{n['name']} jest najedzony.")
        cost = MEALS[meal]['cost']
        if s['cash'] < cost:
            raise Refuse(409, f"{MEALS[meal]['name']} kosztuje {cost} $.")
        s['cash'] -= cost
        evs = []
        n = eat(n, meal, t, evs)
        save(c, n)
        if evs:
            emit(c, wid, [n['character_id']], 'npc.recovered', dict(npc=n['id'], name=n['name'],
                 text=f"{n['name']} doszedł do siebie — znowu pracuje na 100%."))
        return n

    def put_state(c, ch, s):
        c.execute('UPDATE characters SET state_json=? WHERE id=?',
                  (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))

    def guard(fn):
        try:
            return fn()
        except Refuse as e:
            fail(e.code, e.msg)

    @app.post('/api/worlds/{wid}/npcs/{nid}/dispatch')
    def npcs_dispatch(wid: int, nid: int, data: DispatchIn, request: Request, u=Depends(auth)):
        """2.4b: wysyła NPC na zmianę (auto-pilot 2/4/8/12 h) do odblokowanej usługi, autem z garażu lub autobusem."""
        rate(request, 'npc-dispatch-' + str(u['id']), 120, HOUR)
        with db.tx() as c:
            def run():
                w = world(c, wid, True)
                ch = own(c, u['id'], wid)
                team, n = mine(c, ch, wid, nid)
                ch = own(c, u['id'], wid)
                s = json.loads(ch['state_json'])
                t = now()
                E.sync(s, t, w['speed'])
                cooldown_left(s, t, S)            # 2.4c: przerwa dyspozytora po 10 trasach z rzędu
                n = start_shift(c, s, team, n, data.service_id, data.hours, data.car_id, t, wid)
                bump_streak(s.setdefault('dispatch', {}), t, S)
                put_state(c, ch, s)
                audit(c, u['id'], 'npc.dispatch', dict(npc=nid, service=data.service_id, hours=data.hours, car=data.car_id))
                out = payload(c, ch, wid, s)          # rozliczenie → dyspozytor przydziela kierowcę i auto albo autobus
                me = next(m for m in out['npcs'] if m['id'] == nid)
                ride = next((r for r in out['rides'] if r['id'] == me.get('rideId')), None)
                how = f"auto: {E.car(ride['car']).get('name', ride['car'])}, kierowca {ride['driverName']}" if ride else (
                    'autobus — brak wolnego kierowcy z autem' if data.car_id else 'autobus')
                return dict(message=f"{n['name']} jedzie do: {S.BY_ID[data.service_id]['name']} ({data.hours} h, {how}).",
                            transport='car' if ride else 'bus', rideId=ride['id'] if ride else None, **out)
            return once(c, u, wid, request, 'npc-dispatch', lambda: guard(run))

    @app.post('/api/worlds/{wid}/npcs/{nid}/recall')
    def npcs_recall(wid: int, nid: int, request: Request, u=Depends(auth)):
        """2.4b: wcześniejsze zakończenie zmiany — NPC wraca, wypłata bez bonusu auto-pilota."""
        rate(request, 'npc-recall-' + str(u['id']), 120, HOUR)
        with db.tx() as c:
            def run():
                world(c, wid, True)
                ch = own(c, u['id'], wid)
                _, n = mine(c, ch, wid, nid)
                n = recall_one(c, n, wid, now())
                ch = own(c, u['id'], wid)
                return dict(message=f"{n['name']} kończy zmianę wcześniej.", **payload(c, ch, wid, json.loads(ch['state_json'])))
            return once(c, u, wid, request, 'npc-recall', lambda: guard(run))

    @app.post('/api/worlds/{wid}/npcs/feed')
    def npcs_feed_npc(wid: int, data: FeedIn, request: Request, u=Depends(auth)):
        """4.4 GDD v3.1: feed_npc — posiłek z Buffetu dla jednego NPC (masowo: batch all_to_buffet)."""
        return npcs_feed(wid, data.npc_id, request, u, data.meal)

    @app.post('/api/worlds/{wid}/npcs/{nid}/feed')
    def npcs_feed(wid: int, nid: int, request: Request, u=Depends(auth), meal: Optional[int] = None):
        """Zgodność wstecz (2.4d): ta sama logika Buffetu co POST /npcs/feed; posiłek domyślnie najlepszy."""
        if meal is not None and meal not in MEALS:
            fail(422, 'Posiłek: 1, 2 albo 3.')
        rate(request, 'npc-feed-' + str(u['id']), 120, HOUR)
        with db.tx() as c:
            def run():
                w = world(c, wid, True)
                ch = own(c, u['id'], wid)
                _, n = mine(c, ch, wid, nid)              # najpierw rozliczenie emocji do teraz
                ch = own(c, u['id'], wid)
                s = json.loads(ch['state_json'])
                E.sync(s, now(), w['speed'])
                lvl = int(meal or E.buffet_level(s) or 1)
                n = feed_one(c, wid, s, n, now(), meal)
                put_state(c, ch, s)
                ml = MEALS[lvl]
                return dict(message=f"{n['name']}: {ml['name']} (−{ml['cost']} $, sytość +{ml['hunger']}"
                                    + (f", nastrój +{ml['mood']}" if ml['mood'] else '') + (f", energia +{ml['energy']}" if ml['energy'] else '') + ').',
                            **payload(c, ch, wid, s))
            return once(c, u, wid, request, 'npc-feed', lambda: guard(run))

    @app.post('/api/worlds/{wid}/npcs/batch')
    def npcs_batch(wid: int, data: BatchIn, request: Request, u=Depends(auth)):
        """2.5 GDD v3.1: akcja zbiorcza (dispatch / recall / feed) na wielu NPC w jednej transakcji.

        Wynik osobno dla każdego NPC (częściowy sukces). Cała akcja = 1 trasa w liczniku przerwy dyspozytora.
        service_id='best' → najlepsza usługa wg estimate() dla każdego NPC osobno; cars='auto' → wolne auta od najszybszego."""
        rate(request, 'npc-batch-' + str(u['id']), 60, HOUR)
        if data.action == 'dispatch' and (not data.service_id or not data.hours):
            fail(422, 'Akcja zbiorcza dispatch wymaga service_id i hours.')
        with db.tx() as c:
            def run():
                w = world(c, wid, True)
                ch = own(c, u['id'], wid)
                team = roster(c, ch, wid)
                ch = own(c, u['id'], wid)
                s = json.loads(ch['state_json'])
                t = now()
                E.sync(s, t, w['speed'])
                if data.npcs == 'idle':
                    chosen = [n for n in team if not n.get('phase') and not n.get('duty')
                              and (data.action != 'dispatch' or role_of(n) == 'service')]
                elif data.npcs == 'all':
                    chosen = list(team)
                else:
                    ids = list(dict.fromkeys(data.npcs))
                    by = {n['id']: n for n in team}
                    if any(i not in by for i in ids):
                        fail(404, 'Nie masz takiego NPC.')
                    chosen = [by[i] for i in ids]
                if not chosen:
                    fail(409, 'Brak NPC do tej akcji.')
                if data.action == 'dispatch':
                    guard(lambda: cooldown_left(s, t, S))
                results, ok = [], 0
                cars = []   # v3.2: transport przydziela dyspozytor po zapisie (łączenie pasażerów w kursy)
                guess = next(iter(ready_cars(s, S, E)), None) if any(role_of(m) == 'driver' for m in team) else None
                for n in chosen:
                    try:
                        if data.action == 'dispatch':
                            if n.get('phase'):
                                raise Refuse(409, f"{n['name']} jest już na zmianie.")
                            car = None
                            sid = data.service_id
                            if sid == 'best':
                                plan = best_plan(n, s, data.hours, guess, t, wid, E, S)
                                if not plan:
                                    raise Refuse(409, 'Brak odblokowanych usług.')
                                sid = plan['service']
                            m = start_shift(c, s, team, n, sid, data.hours, car, t, wid)
                            team = [m if x['id'] == m['id'] else x for x in team]
                            results.append(dict(npc=n['id'], name=n['name'], ok=True, service=sid, car=None,
                                                message=f"{n['name']} → {S.BY_ID[sid]['name']}."))
                        elif data.action == 'recall':
                            recall_one(c, n, wid, t)
                            results.append(dict(npc=n['id'], name=n['name'], ok=True, message=f"{n['name']} kończy zmianę wcześniej."))
                        else:
                            m = feed_one(c, wid, s, n, t, data.meal)
                            results.append(dict(npc=n['id'], name=n['name'], ok=True, message=f"{n['name']} zjadł posiłek.",
                                                exhausted=exhausted(m)))
                        ok += 1
                    except Refuse as e:
                        results.append(dict(npc=n['id'], name=n['name'], ok=False, message=e.msg))
                if data.action == 'recall':          # wypłaty z recall trafiły do bazy — świeży stan
                    s = json.loads(own(c, u['id'], wid)['state_json'])
                if data.action == 'dispatch' and ok:
                    bump_streak(s.setdefault('dispatch', {}), t, S)   # 2.5: cała akcja = 1 trasa
                put_state(c, ch, s)
                audit(c, u['id'], 'npc.batch', dict(action=data.action, ok=ok, total=len(chosen), service=data.service_id))
                verb = {'dispatch': 'Wysłano', 'recall': 'Odwołano', 'feed': 'Nakarmiono', 'all_to_buffet': 'Nakarmiono'}[data.action]
                out = payload(c, ch, wid, s)          # v3.2: tu dyspozytor łączy wysłanych w kursy
                if data.action == 'dispatch':
                    pub = {m['id']: m for m in out['npcs']}
                    cars_of = {r['id']: r['car'] for r in out['rides']}
                    for r in results:
                        if r['ok']:
                            car = cars_of.get(pub[r['npc']].get('rideId'))
                            r['car'] = car
                            r['message'] = r['message'][:-1] + f" ({'auto' if car else 'autobus'})."
                return dict(message=f'{verb} {ok}/{len(chosen)} NPC.', results=results, okCount=ok,
                            rideCount=len({pub[r['npc']].get('rideId') for r in results if r['ok'] and r['car']}) if data.action == 'dispatch' else 0,
                            **out)
            return once(c, u, wid, request, 'npc-batch', run)

    @app.post('/api/worlds/{wid}/npcs/manager')
    def npcs_manager(wid: int, data: ManagerIn, request: Request, u=Depends(auth)):
        """2.7 GDD v3.1: AI Manager — ponawia zmiany NPC (polityka max/safe) za 10% prowizji od wypłat."""
        rate(request, 'npc-manager-' + str(u['id']), 60, HOUR)
        with db.tx() as c:
            def run():
                w = world(c, wid, True)
                ch = own(c, u['id'], wid)
                team = roster(c, ch, wid)              # najpierw rozliczenie do teraz (stara konfiguracja)
                ch = own(c, u['id'], wid)
                s = json.loads(ch['state_json'])
                t = now()
                E.sync(s, t, w['speed'])
                old = s.get('aiManager') or {}
                stats = {k: old[k] for k in ('shifts', 'earned', 'fees', 'feeds') if k in old}
                if data.enabled:
                    if E.level(s['xp']) < MANAGER_MIN_LEVEL:
                        fail(409, f'AI Manager jest dostępny od {MANAGER_MIN_LEVEL}. poziomu.')
                    ids = {n['id'] for n in team}
                    if any(i not in ids for i in data.exclude):
                        fail(404, 'Nie masz takiego NPC.')
                    s['aiManager'] = dict(stats, until=t + data.duration_h * HOUR, since=t, policy=data.policy,
                                          hours=data.hours, feed=data.feed, exclude=sorted(set(data.exclude)))
                    msg = (f"AI Manager pracuje {data.duration_h} h ({'maksymalny zarobek' if data.policy == 'max' else 'bez przemęczenia'}, "
                           f"zmiany {data.hours} h). Prowizja {round(MANAGER_COMMISSION * 100)}% od wypłat.")
                else:
                    if not old.get('until') or old['until'] <= t:
                        fail(409, 'AI Manager nie jest aktywny.')
                    s['aiManager'] = dict(stats, until=None)
                    msg = 'AI Manager wyłączony — trwające zmiany dokończą się normalnie (z prowizją).'
                put_state(c, ch, s)
                audit(c, u['id'], 'npc.manager', dict(enabled=data.enabled, policy=data.policy, hours=data.hours,
                                                      duration=data.duration_h, exclude=data.exclude))
                return dict(message=msg, **payload(c, ch, wid, s))   # payload → roster → manager wysyła wolnych od razu
            return once(c, u, wid, request, 'npc-manager', run)

    @app.post('/api/worlds/{wid}/npcs/{nid}/taxi')
    def npcs_taxi(wid: int, nid: int, data: TaxiIn, request: Request, u=Depends(auth)):
        """v3.2 Zad. 2: Shift Taxi — wolny kierowca z autem na 2/4/8 h (D4: blokuje kierowcę i auto do końca)."""
        rate(request, 'npc-taxi-' + str(u['id']), 120, HOUR)
        with db.tx() as c:
            def run():
                w = world(c, wid, True)
                ch = own(c, u['id'], wid)
                _, n = mine(c, ch, wid, nid)
                ch = own(c, u['id'], wid)
                s = json.loads(ch['state_json'])
                t = now()
                E.sync(s, t, w['speed'])
                if role_of(n) != 'driver':
                    raise Refuse(409, f"{n['name']} nie jest kierowcą — Taxi jeżdżą tylko NPC w roli Kierowca.")
                if n.get('duty'):
                    raise Refuse(409, f"{n['name']} jest zajęty ({'kurs z ekipą' if n['duty'] == 'ferry' else 'Taxi'}).")
                if n['energy'] < DISPATCH_MIN_ENERGY:
                    raise Refuse(409, f"{n['name']} jest zbyt zmęczony (energia < {DISPATCH_MIN_ENERGY}).")
                garage = s.get('garage') or []
                if data.car_id and data.car_id not in garage:
                    raise Refuse(409, 'Tego auta nie ma w twoim garażu.')
                driving = player_car(c, ch['id'], s)
                order = [data.car_id] if data.car_id else sorted(garage, key=lambda v: (-taxi_net(v, E), v))
                car = None
                for v in order:
                    if v == driving or not car_free(c, ch['id'], s, v, t):
                        if data.car_id:
                            raise Refuse(409, 'To auto jest teraz w użyciu (kurs, Taxi albo twoja podróż).')
                        continue
                    if E.fuel_of(s, v) + EPS < TAXI_HOPS_PER_H * E.car(v).get('fuel', 0):
                        if data.car_id:
                            raise Refuse(409, 'Za mało paliwa na godzinę Taxi — zatankuj auto w Garażu.')
                        continue
                    car = v
                    break
                if not car:
                    raise Refuse(409, 'Brak wolnego auta z paliwem na Taxi.' if garage else 'Taxi wymaga auta w garażu.')
                per_h = TAXI_HOPS_PER_H * E.car(car).get('fuel', 0)
                fuel_end = t + int(E.fuel_of(s, car) / per_h * HOUR) if per_h else None
                until = t + data.hours * HOUR
                n = dict(n, duty='taxi', busy_until=until, ride_car=car, taxi_started_at=t, taxi_until=until,
                         taxi_hours=data.hours, taxi_cash=0, taxi_mult=TAXI_MULT.get(car, 1.0), taxi_recalled=0,
                         taxi_fuel_end=fuel_end if fuel_end and fuel_end < until else None)
                save(c, n)
                c.execute('INSERT INTO npc_rides(character_id,driver_id,car_id,kind,district,depart_at,meet_at,arrive_at,back_at,'
                          "passengers) VALUES(?,?,?,'taxi',NULL,?,?,?,?,'[]')", (ch['id'], nid, car, t, t, until, until))
                audit(c, u['id'], 'npc.taxi', dict(npc=nid, car=car, hours=data.hours))
                est = round(TAXI_RATE * TAXI_MULT.get(car, 1.0) * data.hours * (BURNOUT_MULT if exhausted(n) else 1.0))
                return dict(message=f"{n['name']} jedzie na Taxi: {E.car(car).get('name', car)}, {data.hours} h (≈ {est} $ brutto).",
                            car=car, **payload(c, ch, wid, s))
            return once(c, u, wid, request, 'npc-taxi', lambda: guard(run))

    @app.post('/api/worlds/{wid}/npcs/{nid}/role')
    def npcs_role(wid: int, nid: int, data: RoleIn, request: Request, u=Depends(auth)):
        """v3.2 Zad. 1: zmiana roli SERVICE ↔ DRIVER — tylko wolny NPC, maks. raz na 24 h."""
        rate(request, 'npc-role-' + str(u['id']), 30, HOUR)
        with db.tx() as c:
            def run():
                world(c, wid, True)
                ch = own(c, u['id'], wid)
                _, n = mine(c, ch, wid, nid)
                t = now()
                if role_of(n) == data.role:
                    raise Refuse(409, f"{n['name']} ma już rolę: {ROLE_LABEL[data.role].lower()}.")
                if n.get('phase') or n.get('duty'):
                    raise Refuse(409, f"{n['name']} jest zajęty — rolę zmienisz, gdy wróci do Rezydencji.")
                left = int(n.get('role_changed_at') or 0) + ROLE_CHANGE_MS - t
                if n.get('role_changed_at') and left > 0:
                    raise Refuse(409, f"Rolę można zmieniać raz na 24 h — spróbuj za {left // HOUR} h {left % HOUR // 60000} min.")
                n = dict(n, role=data.role, role_changed_at=t)
                save(c, n)
                audit(c, u['id'], 'npc.role', dict(npc=nid, role=data.role))
                ch = own(c, u['id'], wid)
                return dict(message=f"{n['name']} ma teraz rolę: {ROLE_LABEL[data.role].lower()}.",
                            **payload(c, ch, wid, json.loads(ch['state_json'])))
            return once(c, u, wid, request, 'npc-role', lambda: guard(run))

    def sweep_npcs():
        """Co 10 min z app.sweep(): emocje i ucieczka dla wszystkich, także graczy offline."""
        # v3.2: iteracja po POSTACIACH (partie), każda postać w osobnej transakcji — błąd jednej nie cofa innych
        t = now()
        last = 0
        while True:
            with db.tx() as c:
                chars = c.execute('SELECT DISTINCT n.character_id cid, ch.world_id wid FROM npcs n JOIN characters ch '
                                  'ON ch.id=n.character_id WHERE n.character_id>? ORDER BY n.character_id LIMIT ?',
                                  (last, SWEEP_CHARS)).fetchall()
            for r in chars:
                try:
                    with db.tx() as c:
                        settle_character(c, r['cid'], r['wid'], t)
                except Exception:   # bezpiecznik: jedna uszkodzona postać nie zatrzymuje sweepa
                    import logging
                    logging.getLogger('city.npc').exception('sweep NPC: postać %s', r['cid'])
            if len(chars) < SWEEP_CHARS:
                break
            last = chars[-1]['cid']
        with db.tx() as c:
            c.execute('DELETE FROM npc_rides WHERE back_at<?', (t - RIDE_KEEP_MS,))

    return dict(sweep=sweep_npcs, advance=advance, slots=slots, recruit_cost=recruit_cost, cars=cars_in_use, roster=roster)
