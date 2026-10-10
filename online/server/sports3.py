"""QA 5 (feedback z testów na żywo): Agility psów 2.0 i nowa Jazda Konna.

Agility psów:
  - wynik zależy od statystyk AKTYWNEGO psa (szybkość, wytrzymałość, posłuszeństwo) + trochę Refleksu gracza,
  - limit 10 konkursów w oknie 4 h (okna liczone od północy UTC: 0–4, 4–8, …),
  - „Smaczek dla psa” (100 $) kupowany przy zapisie: wynik +10%,
  - rasy w psiarni (kundel startowy za darmo + 3 rasy do kupienia), szkolenie za $ podnosi statystykę psa na stałe.
Jazda Konna (zastępuje stary placeholder): szybki konkurs jak agility — statystyki aktywnego konia (speed, stamina)
  + Refleks/Charyzma gracza → wynik, ocena i nagroda $ + XP. Bez zakładów (guard: hipodrom bez obstawiania).
Losowość deterministyczna (hash postaci i czasu), zero realnych pieniędzy.
"""
import hashlib
import json
from typing import Literal, Optional

from fastapi import Depends, Request
from pydantic import BaseModel

WINDOW_MS = 4 * 3600000
LIMIT = 10
TREAT_COST, TREAT_MULT = 100, 1.10
AGILITY_ENTRY, AGILITY_ENERGY = 50, 10
RIDING_ENTRY, RIDING_ENERGY = 80, 15
DOG_STAT_CAP = 20
DOG_STATS = ('speed', 'stamina', 'obedience')

DOG_BREEDS = {
    'kundel': dict(name='Kundel z podwórka', price=0, level=1, speed=3, stamina=3, obedience=3, icon='🐕', desc='Wierny towarzysz na start — darmowy.'),
    'jack-russell': dict(name='Jack Russell', price=1200, level=3, speed=6, stamina=3, obedience=3, icon='🐶', desc='Szybki jak strzała, ale szybko się męczy.'),
    'border-collie': dict(name='Border Collie', price=2500, level=5, speed=5, stamina=4, obedience=7, icon='🐕‍🦺', desc='Najmądrzejszy na torze — perfekcyjnie słucha komend.'),
    'owczarek': dict(name='Owczarek Niemiecki', price=4000, level=8, speed=5, stamina=7, obedience=5, icon='🦮', desc='Wytrzymały all-rounder na długie tory.'),
}
STARTER_HORSE = dict(id='kucyk', name='Kucyk klubowy (wypożyczony)', speed=2, stamina=2)


class AgilityIn(BaseModel):
    treat: bool = False


class DogBuy(BaseModel):
    breed: Literal['jack-russell', 'border-collie', 'owczarek']


class DogPick(BaseModel):
    key: str


class DogTrain(BaseModel):
    stat: Literal['speed', 'stamina', 'obedience']


class RidingIn(BaseModel):
    treat: bool = False


def _hash(*parts):
    return int.from_bytes(hashlib.sha256(':'.join(map(str, parts)).encode()).digest()[:8], 'big')


def train_cost(value):
    """Szkolenie psa: 150 $ + 100 $ za każdy obecny punkt statystyki."""
    return 150 + 100 * int(value)


def grade(score):
    return 'S' if score >= 110 else 'A' if score >= 90 else 'B' if score >= 75 else 'C' if score >= 60 else 'D' if score >= 45 else 'E'


def install(app, d, E):
    db, now, fail, world, own, auth, rate, audit = d.db, d.now, d.fail, d.world, d.own, d.auth, d.rate, d.audit

    def load(c, cid):
        return json.loads(c.execute('SELECT state_json FROM characters WHERE id=?', (cid,)).fetchone()[0])

    def save(c, cid, s):
        s['lastAction'] = now()
        c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), cid))

    def kennel(s):
        """Psiarnia: s['dogs'] (wspólna z Lochem/BP). Zapewnia darmowego kundla i pole posłuszeństwa (migracja addytywna)."""
        dogs = s.setdefault('dogs', {})
        if not dogs:
            b = DOG_BREEDS['kundel']
            dogs['kennel-kundel'] = dict(key='kennel-kundel', breed='kundel', name=b['name'], speed=b['speed'], stamina=b['stamina'], obedience=b['obedience'], gen=1)
        for dg in dogs.values():
            dg.setdefault('obedience', DOG_BREEDS.get(dg.get('breed'), {}).get('obedience', 4 if dg.get('premium') else 3))
        if s.get('dog') not in dogs:
            s['dog'] = max(dogs.values(), key=lambda x: x['speed'] + x['stamina'] + x['obedience'])['key']
        return dogs

    def window(s, key):
        w = now() // WINDOW_MS
        a = s.setdefault('sports2', {}).setdefault(key, {})
        if a.get('w') != w:
            a.update(w=w, runs=0)
        return a

    def window_view(s, key):
        a = window(s, key)
        return dict(runs=a['runs'], limit=LIMIT, left=LIMIT - a['runs'], resetAt=(now() // WINDOW_MS + 1) * WINDOW_MS, best=a.get('best', 0))

    def common_checks(s, entry, energy, treat, key):
        if s.get('travel_destination'):
            fail(409, 'Jesteś w drodze — konkurs poczeka na przyjazd.')
        a = window(s, key)
        if a['runs'] >= LIMIT:
            fail(409, f'Limit {LIMIT} konkursów na 4 godziny — następne okno wkrótce.')
        cost = entry + (TREAT_COST if treat else 0)
        if s['cash'] < cost:
            fail(409, f'Potrzebujesz {cost} $ (wpisowe{" + smaczek" if treat else ""}).')
        if s['energy'] < energy:
            fail(409, f'Konkurs kosztuje {energy} energii.')
        s['cash'] -= cost; s['energy'] -= energy; a['runs'] += 1
        return a

    def payload(s):
        dogs = kennel(s)
        horse = s.get('horse') or STARTER_HORSE
        return dict(
            dogs=[dict(v, active=v['key'] == s['dog'], trainCost={k: train_cost(v[k]) for k in DOG_STATS}) for v in dogs.values()],
            activeDog=s['dog'], breeds=[dict(id=k, **v) for k, v in DOG_BREEDS.items() if v['price'] > 0],
            agility=window_view(s, 'agil2'), riding=window_view(s, 'ride'),
            horse=dict(horse, starter=not s.get('horse')), stable=list((s.get('horses') or {}).values()),
            rules=dict(limit=LIMIT, windowHours=4, treatCost=TREAT_COST, treatPct=10, agilityEntry=AGILITY_ENTRY, agilityEnergy=AGILITY_ENERGY,
                       ridingEntry=RIDING_ENTRY, ridingEnergy=RIDING_ENERGY, dogStatCap=DOG_STAT_CAP))

    @app.get('/api/worlds/{wid}/sports3')
    def sports3_state(wid: int, u=Depends(auth)):
        with db.read() as c:
            world(c, wid)
            ch = c.execute('SELECT id,state_json FROM characters WHERE account_id=? AND world_id=?', (u['id'], wid)).fetchone()
            if not ch:
                fail(404, 'Najpierw stwórz postać w tym świecie.')
            s = json.loads(ch['state_json'])
            return payload(s)

    @app.post('/api/worlds/{wid}/sports/agility')
    def agility(wid: int, request: Request, data: Optional[AgilityIn] = None, u=Depends(auth)):
        rate(request, 'sports-agility-' + str(u['id']), 40, 3600000)
        treat = bool(data and data.treat)
        with db.tx() as c:
            w = world(c, wid, True); ch = own(c, u['id'], wid); s = load(c, ch['id']); E.sync(s, now(), w['speed'])
            dog = kennel(s)[s['dog']]
            a = common_checks(s, AGILITY_ENTRY, AGILITY_ENERGY, treat, 'agil2')
            jitter = _hash('agil', ch['id'], now()) % 16
            ref = E.effective(s)[2]
            raw = 20 + dog['speed'] * 3 + dog['stamina'] * 2 + dog['obedience'] * 3 + max(0, ref - 10) * 0.5 + jitter
            score = int(round(raw * (TREAT_MULT if treat else 1)))
            g = grade(score); cash = score * 2; xp = 10 + score // 3
            s['cash'] += cash; s['xp'] = s.get('xp', 0) + xp
            best0 = a.get('best', 0); a['best'] = max(best0, score)
            ag = s['sports2'].setdefault('agil', {'best': 0, 'runs': 0}); ag['runs'] += 1; ag['best'] = max(ag['best'], score)  # zgodność ze starym licznikiem
            save(c, ch['id'], s)
            audit(c, u['id'], 'sports.agility', dict(score=score, dog=dog['key'], treat=treat))
            return dict(ok=True, score=score, grade=g, dog=dog['name'], treat=treat, rewards=dict(cash=cash, xp=xp), newRecord=score > best0,
                        agility=window_view(s, 'agil2'),
                        message=f'🐕 {dog["name"]}: {score} pkt (ocena {g}){" · 🦴 smaczek +10%" if treat else ""} · +{cash} $ · +{xp} XP')

    @app.post('/api/worlds/{wid}/sports/dog/buy')
    def dog_buy(wid: int, data: DogBuy, request: Request, u=Depends(auth)):
        rate(request, 'sports-dogbuy-' + str(u['id']), 10, 3600000)
        b = DOG_BREEDS[data.breed]
        with db.tx() as c:
            world(c, wid, True); ch = own(c, u['id'], wid); s = load(c, ch['id'])
            dogs = kennel(s); key = 'kennel-' + data.breed
            if key in dogs:
                fail(409, 'Ten pies już mieszka w Twojej psiarni.')
            if E.level(s.get('xp') or 0) < b['level']:
                fail(409, f'{b["name"]} wymaga poziomu {b["level"]}.')
            E.spend(s, cash=b['price'])
            dogs[key] = dict(key=key, breed=data.breed, name=b['name'], speed=b['speed'], stamina=b['stamina'], obedience=b['obedience'], gen=1)
            s['dog'] = key
            save(c, ch['id'], s); audit(c, u['id'], 'sports.dog_buy', dict(breed=data.breed))
            return dict(ok=True, message=f'{b["icon"]} {b["name"]} dołącza do psiarni i startuje w konkursach!', **payload(s))

    @app.post('/api/worlds/{wid}/sports/dog/pick')
    def dog_pick(wid: int, data: DogPick, request: Request, u=Depends(auth)):
        with db.tx() as c:
            world(c, wid, True); ch = own(c, u['id'], wid); s = load(c, ch['id'])
            dogs = kennel(s)
            if data.key not in dogs:
                fail(404, 'Nie ma takiego psa w Twojej psiarni.')
            s['dog'] = data.key
            save(c, ch['id'], s)
            return dict(ok=True, message=f'Aktywny pies: {dogs[data.key]["name"]}.', **payload(s))

    @app.post('/api/worlds/{wid}/sports/dog/train')
    def dog_train(wid: int, data: DogTrain, request: Request, u=Depends(auth)):
        rate(request, 'sports-dogtrain-' + str(u['id']), 60, 3600000)
        with db.tx() as c:
            world(c, wid, True); ch = own(c, u['id'], wid); s = load(c, ch['id'])
            dog = kennel(s)[s['dog']]
            if dog[data.stat] >= DOG_STAT_CAP:
                fail(409, f'Ta statystyka psa osiągnęła maksimum ({DOG_STAT_CAP}).')
            cost = train_cost(dog[data.stat])
            E.spend(s, cash=cost)
            dog[data.stat] += 1
            label = {'speed': 'Szybkość', 'stamina': 'Wytrzymałość', 'obedience': 'Posłuszeństwo'}[data.stat]
            save(c, ch['id'], s); audit(c, u['id'], 'sports.dog_train', dict(dog=dog['key'], stat=data.stat))
            return dict(ok=True, message=f'🎓 {dog["name"]}: {label} {dog[data.stat]} (−{cost} $).', **payload(s))

    @app.post('/api/worlds/{wid}/sports/riding')
    def riding(wid: int, request: Request, data: Optional[RidingIn] = None, u=Depends(auth)):
        """Jazda Konna: konkurs zręcznościowy na torze z przeszkodami (bez zakładów)."""
        rate(request, 'sports-riding-' + str(u['id']), 40, 3600000)
        with db.tx() as c:
            w = world(c, wid, True); ch = own(c, u['id'], wid); s = load(c, ch['id']); E.sync(s, now(), w['speed'])
            horse = s.get('horse') or STARTER_HORSE
            a = common_checks(s, RIDING_ENTRY, RIDING_ENERGY, False, 'ride')
            eff = E.effective(s)
            jitter = _hash('ride', ch['id'], now()) % 16
            score = int(round(20 + horse['speed'] * 5 + horse['stamina'] * 4 + max(0, eff[2] - 10) * 0.4 + max(0, eff[3] - 10) * 0.3 + jitter))
            g = grade(score); cash = score * 3; xp = 15 + score // 3
            s['cash'] += cash; s['xp'] = s.get('xp', 0) + xp
            best0 = a.get('best', 0); a['best'] = max(best0, score)
            save(c, ch['id'], s)
            audit(c, u['id'], 'sports.riding', dict(score=score, horse=horse.get('id')))
            return dict(ok=True, score=score, grade=g, horse=horse['name'], rewards=dict(cash=cash, xp=xp), newRecord=score > best0,
                        riding=window_view(s, 'ride'),
                        message=f'🏇 {horse["name"]}: {score} pkt (ocena {g}) · +{cash} $ · +{xp} XP')

    return dict(payload=payload)
