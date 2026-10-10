"""0.14 Sklep (wersja rozwojowa): pozorowana kasa, realne ceny w zł, brama opiekuna.

ZASADA TWARDA: w tym środowisku nigdy nie ma prawdziwych płatności. „Kup” symuluje
transakcję (status 'paid_dev'), wszystko trafia do dziennika audytu z ceną. W produkcji
zakupy cyfrowe idą wyłącznie przez Play Billing / Apple IAP (patrz MONETYZACJA.md).
Zgodnie z decyzją z 0.14: zakupy DOMYŚLNIE WYŁĄCZONE dla każdego konta — włączenie
wymaga oświadczenia (16+ albo zgoda opiekuna; dev-stub ścieżki z RODO art. 8).
"""
import datetime
import json

from fastapi import Depends, Request
from pydantic import BaseModel, Field

from . import age as AGE

DAY = 24 * 3600 * 1000
day_utc = lambda t: t // DAY * DAY  # noqa: E731

SKU = {
 'vip30':   dict(name='VIP · 30 dni', price='19,99 zł', cents=1999, kind='vip', days=30, desc='+25% gotówki z kontraktów, złota rama profilu. Działa na wszystkich Twoich postaciach.'),
 'vip7':    dict(name='VIP · 7 dni', price='7,99 zł', cents=799, kind='vip', days=7, desc='To samo co VIP 30 dni, krócej. Okresy VIP się sumują.'),
 'starter': dict(name='Pakiet startowy', price='9,99 zł', cents=999, kind='starter', desc='5 000 $, zestaw Specjalistyczne (3 przedmioty) i natychmiastowy odpoczynek. Raz na konto, na wybrany świat.'),
 'energy':  dict(name='Energiapak +100', price='4,99 zł', cents=499, kind='energy', limit=2, desc='+100 energii natychmiast (nadwyżka ponad 240 przepada). Limit 2/dobę UTC.'),
 'speedup': dict(name='Przyspieszenie zlecenia', price='2,99 zł', cents=299, kind='speedup', limit=3, desc='Skraca trwające zlecenie o połowę. Limit 3/dobę UTC. Nie zmienia wyników PvP.'),
 'skin_copper': dict(name='Skórka: Miedź', price='3,99 zł', cents=399, kind='skin', desc='Miedziana rama profilu. Czysto kosmetyczna, zero statystyk.'),
 'skin_gold':   dict(name='Skórka: Złoto', price='5,99 zł', cents=599, kind='skin', desc='Złota rama profilu. Czysto kosmetyczna, zero statystyk.'),
 'skin_neon':   dict(name='Skórka: Neon', price='9,99 zł', cents=999, kind='skin', desc='Neonowa rama profilu. Czysto kosmetyczna, zero statystyk.'),
}
STARTER_ITEMS = ('analyst-band', 'agile-shoes', 'captain-shirt')  # tier „Specjalistyczne”
BANNER = 'Wersja rozwojowa: kasa pozorowana, BEZ prawdziwych płatności. W produkcji zakupy cyfrowe wyłącznie przez sklep aplikacji (Play Billing / Apple IAP).'
GATE_TEXT = 'Zakupy są domyślnie wyłączone. Włączając je oświadczasz, że masz ukończone 16 lat albo że opiekun prawny wyraża zgodę na wydatki w tej wersji. Pełna ścieżka zgody opiekuna (RODO art. 8): MONETYZACJA.md.'

SCHEMA = '''
CREATE TABLE IF NOT EXISTS shop_state(account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,spending_enabled INTEGER NOT NULL DEFAULT 0,enabled_at INTEGER,vip_until INTEGER NOT NULL DEFAULT 0,starter INTEGER NOT NULL DEFAULT 0,skin TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS shop_purchases(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,sku TEXT NOT NULL,price TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'paid_dev',world_id INTEGER,created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS shop_purchases_acc ON shop_purchases(account_id,id DESC);
CREATE TABLE IF NOT EXISTS shop_usage(account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,sku TEXT NOT NULL,day INTEGER NOT NULL,count INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(account_id,sku,day));
CREATE TABLE IF NOT EXISTS guardian_consents(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,guardian_name TEXT NOT NULL,weekly_limit INTEGER NOT NULL,created_at INTEGER NOT NULL,revoked_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS guardian_active ON guardian_consents(account_id) WHERE revoked_at IS NULL;
'''


class Gate(BaseModel):
    enable: bool
    statement: bool = Field(default=False)
    minor: bool = Field(default=False)


class Guardian(BaseModel):
    guardian_name: str = Field(min_length=3, max_length=60)
    weekly_limit: int = Field(ge=500, le=20000)


class Checkout(BaseModel):
    sku: str = Field(min_length=2, max_length=24)
    wid: int = Field(default=0, ge=0, le=1000000)


class Equip(BaseModel):
    skin: str = Field(default='', max_length=24)


def install(app, d, E):
    db, now, fail, auth, audit = d.db, d.now, d.fail, d.auth, d.audit
    c = db.connect()
    try:
        c.executescript(SCHEMA)
        if 'cents' not in {r[1] for r in c.execute('PRAGMA table_info(shop_purchases)')}:
            c.execute('ALTER TABLE shop_purchases ADD COLUMN cents INTEGER NOT NULL DEFAULT 0')
        c.commit()
    finally:
        c.close()

    week_utc = lambda t: (t // DAY - (t // DAY + 3) % 7) * DAY  # poniedziałek 00:00 UTC  # noqa: E731

    def is_minor(u, gate_minor=False):
        # 1.8 A4: znana data urodzenia → wiek liczony przez serwer (deklaracja klienta ignorowana);
        # brak daty (konto sprzed bramki, flaga wyłączona) → dotychczasowa deklaracja z formularza
        if u.get('birth_date'):
            return AGE.age_on(datetime.date.fromisoformat(u['birth_date']), AGE.today_from_ms(now())) < AGE.CONSENT_AGE
        return bool(gate_minor)

    def active_consent(c, uid):
        return c.execute('SELECT * FROM guardian_consents WHERE account_id=? AND revoked_at IS NULL', (uid,)).fetchone()

    def week_spent(c, uid):
        return c.execute('SELECT coalesce(sum(cents),0) FROM shop_purchases WHERE account_id=? AND created_at>=?', (uid, week_utc(now()))).fetchone()[0]

    def guardian_info(c, uid):
        row = active_consent(c, uid)
        if not row:return None
        return dict(since=row['created_at'], guardianName=row['guardian_name'], weeklyLimit=row['weekly_limit'], weeklySpent=week_spent(c, uid))

    def st(c, uid):
        row = c.execute('SELECT * FROM shop_state WHERE account_id=?', (uid,)).fetchone()
        if not row:
            c.execute('INSERT INTO shop_state(account_id) VALUES(?)', (uid,))
            row = c.execute('SELECT * FROM shop_state WHERE account_id=?', (uid,)).fetchone()
        return row

    def usage(c, uid, sku):
        row = c.execute('SELECT count FROM shop_usage WHERE account_id=? AND sku=? AND day=?', (uid, sku, day_utc(now()))).fetchone()
        return row['count'] if row else 0

    def bump(c, uid, sku):
        c.execute('INSERT INTO shop_usage(account_id,sku,day,count) VALUES(?,?,?,1) ON CONFLICT(account_id,sku,day) DO UPDATE SET count=count+1', (uid, sku, day_utc(now())))

    def save(c, ch, s):
        c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))

    # VIP lives on the account, but the contract bonus is computed from the character
    # state; purchase stamps every character, a new character gets it at creation.
    def vip_until(c, uid):
        return st(c, uid)['vip_until']

    def stamp(c, uid, until):
        for r in c.execute('SELECT id,state_json FROM characters WHERE account_id=?', (uid,)).fetchall():
            s = json.loads(r['state_json']);s['vipUntil'] = until
            c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), r['id']))

    def summary(c, uid):
        row = st(c, uid)
        owned = [r['sku'] for r in c.execute("SELECT DISTINCT sku FROM shop_purchases WHERE account_id=? AND sku LIKE 'skin_%' ORDER BY sku", (uid,))]
        return dict(spendingEnabled=bool(row['spending_enabled']), vipActive=bool(row['vip_until'] > now()), vipUntil=row['vip_until'] if row['vip_until'] else None, starter=bool(row['starter']), skin=row['skin'], ownedSkins=owned, guardian=guardian_info(c, uid), banner=BANNER)

    @app.get('/api/shop')
    def shop_index(u=Depends(auth)):
        with db.read() as c:
            row = st(c, u['id'])
            owned = {r['sku'] for r in c.execute("SELECT DISTINCT sku FROM shop_purchases WHERE account_id=? AND sku LIKE 'skin_%'", (u['id'],))}
            products = []
            for sku, v in SKU.items():
                p = dict(sku=sku, **{k: v[k] for k in ('name', 'price', 'desc', 'kind')})
                if 'limit' in v:p.update(limit=v['limit'], usedToday=usage(c, u['id'], sku))
                if v['kind'] == 'vip':p['activeUntil'] = row['vip_until'] if row['vip_until'] else None
                if v['kind'] == 'starter':p['owned'] = bool(row['starter'])
                if v['kind'] == 'skin':p.update(owned=sku in owned, equipped=row['skin'] == sku)
                products.append(p)
            history = [dict(id=r['id'], sku=r['sku'], price=r['price'], status=r['status'], created_at=r['created_at']) for r in c.execute('SELECT id,sku,price,status,created_at FROM shop_purchases WHERE account_id=? ORDER BY id DESC LIMIT 10', (u['id'],))]
            return dict(products=products, state=summary(c, u['id']), history=history, gate=GATE_TEXT, minor=is_minor(u), minorSource='birth_date' if u.get('birth_date') else 'declared')

    @app.post('/api/shop/gate')
    def shop_gate(data: Gate, u=Depends(auth)):
        with db.tx() as c:
            row = st(c, u['id'])
            if data.enable:
                if not data.statement:fail(422, GATE_TEXT)
                minor = is_minor(u, data.minor)
                if minor and not active_consent(c, u['id']):fail(422, 'Dla osoby poniżej 16 lat najpierw zapisz zgodę opiekuna (formularz zgody w sklepie).')
                if not row['spending_enabled']:
                    c.execute('UPDATE shop_state SET spending_enabled=1, enabled_at=? WHERE account_id=?', (now(), u['id']))
                    audit(c, u['id'], 'shop.gate_enabled', dict(statement=True, minor=minor, source='birth_date' if u.get('birth_date') else 'declared'))
            else:
                c.execute('UPDATE shop_state SET spending_enabled=0 WHERE account_id=?', (u['id'],))
                audit(c, u['id'], 'shop.gate_disabled', {})
            return dict(ok=True, spendingEnabled=bool(data.enable))

    @app.post('/api/shop/guardian')
    def shop_guardian(data: Guardian, u=Depends(auth)):
        with db.tx() as c:
            if active_consent(c, u['id']):fail(409, 'Zgoda opiekuna już istnieje — najpierw ją cofnij.')
            st(c, u['id'])
            cid = c.execute('INSERT INTO guardian_consents(account_id,guardian_name,weekly_limit,created_at) VALUES(?,?,?,?)', (u['id'], data.guardian_name.strip(), data.weekly_limit, now())).lastrowid
            audit(c, u['id'], 'shop.guardian_consent', dict(id=cid, weekly_limit=data.weekly_limit))
            return dict(ok=True, guardian=guardian_info(c, u['id']))

    @app.post('/api/shop/guardian/revoke')
    def shop_guardian_revoke(u=Depends(auth)):
        with db.tx() as c:
            row = active_consent(c, u['id'])
            if not row:fail(404, 'Nie ma aktywnej zgody opiekuna.')
            c.execute('UPDATE guardian_consents SET revoked_at=? WHERE id=?', (now(), row['id']))
            c.execute('UPDATE shop_state SET spending_enabled=0 WHERE account_id=?', (u['id'],))
            audit(c, u['id'], 'shop.guardian_revoke', dict(id=row['id']))
            return dict(ok=True)

    @app.post('/api/shop/equip')
    def shop_equip(data: Equip, u=Depends(auth)):
        with db.tx() as c:
            if data.skin:
                if data.skin not in SKU or not data.skin.startswith('skin_'):fail(422, 'Nieznana skórka.')
                if not c.execute('SELECT 1 FROM shop_purchases WHERE account_id=? AND sku=?', (u['id'], data.skin)).fetchone():fail(409, 'Najpierw kup tę skórkę (wersja dev: pozorowana kasa).')
            c.execute('UPDATE shop_state SET skin=? WHERE account_id=?', (data.skin, u['id']))
            return dict(ok=True, skin=data.skin)

    @app.post('/api/shop/checkout')
    def shop_checkout(data: Checkout, request: Request, u=Depends(auth)):
        d.rate(request, 'shop-checkout-' + str(u['id']), 10, 3600000)
        sku = data.sku if data.sku in SKU else fail(422, 'Nieznany produkt.')
        v = SKU[sku]
        with db.tx() as c:
            row = st(c, u['id'])
            if not row['spending_enabled']:fail(403, 'Zakupy są wyłączone (domyślnie). Włącz je w sklepie po oświadczeniu wiekowym albo zgodzie opiekuna.')
            # 1.8 A4: zakupy włączone przed podaniem daty (deklaracja „dorosły”), a data pokazuje < 16 → wymagana zgoda opiekuna
            if u.get('birth_date') and is_minor(u) and not active_consent(c, u['id']):
                fail(403, 'Masz mniej niż 16 lat — zakupy wymagają zgody opiekuna z limitem tygodniowym (formularz w sklepie).')
            world_sku = v['kind'] in ('starter', 'energy', 'speedup')
            ch = None;s = None
            if world_sku:
                if not data.wid:fail(422, 'Wskaż świat — ten produkt działa na postać w danym świecie.')
                w = c.execute('SELECT * FROM worlds WHERE id=?', (data.wid,)).fetchone()
                if not w:fail(404, 'Nie ma takiego świata.')
                ch = c.execute('SELECT * FROM characters WHERE account_id=? AND world_id=?', (u['id'], data.wid)).fetchone()
                if not ch:fail(409, 'Wejdź najpierw do świata — ten produkt działa na postać.')
                s = json.loads(ch['state_json'])
            if v['kind'] == 'starter' and row['starter']:fail(409, 'Pakiet startowy można kupić raz na konto.')
            if v['kind'] == 'skin' and c.execute('SELECT 1 FROM shop_purchases WHERE account_id=? AND sku=?', (u['id'], sku)).fetchone():fail(409, 'Tę skórkę już posiadasz.')
            if 'limit' in v and usage(c, u['id'], sku) >= v['limit']:fail(409, 'Dzienny limit tego produktu został wykorzystany (dobę UTC liczy serwer).')
            consent = active_consent(c, u['id'])
            if consent and week_spent(c, u['id']) + v['cents'] > consent['weekly_limit']:fail(409, 'Tygodniowy limit wydatków ustalony przez opiekuna został wykorzystany (limit ' + str(consent['weekly_limit'] // 100) + ' zł na tydzień).')
            # --- Pozorowana transakcja (dev): żadnej prawdziwej płatności; pełny audyt z ceną.
            c.execute('INSERT INTO shop_purchases(account_id,sku,price,cents,world_id,created_at) VALUES(?,?,?,?,?,?)', (u['id'], sku, v['price'], v['cents'], data.wid if world_sku else None, now()))
            if world_sku and ch is not None:E.bump(c,data.wid,ch['id'],now(),cents=v['cents'])
            audit(c, u['id'], 'shop.paid_dev', dict(sku=sku, price=v['price'], world=data.wid if world_sku else None))
            if 'limit' in v:bump(c, u['id'], sku)
            if v['kind'] == 'vip':
                until = max(row['vip_until'], now()) + v['days'] * DAY
                c.execute('UPDATE shop_state SET vip_until=? WHERE account_id=?', (until, u['id']))
                stamp(c, u['id'], until)
                return dict(ok=True, sku=sku, vipUntil=until, message='VIP aktywny do ' + str(until) + ' (dev).')
            if v['kind'] == 'starter':
                added = [i for i in STARTER_ITEMS if i not in s['inventory']]
                s['inventory'] += added;s['cash'] += 5000;s['restInstant'] = s.get('restInstant', 0) + 1
                c.execute('UPDATE shop_state SET starter=1 WHERE account_id=?', (u['id'],))
                save(c, ch, s)
                return dict(ok=True, sku=sku, message='Pakiet startowy: +5 000 $, zestaw Specjalistyczne (' + str(len(added)) + ' szt.), 1× natychmiastowy odpoczynek.')
            if v['kind'] == 'energy':
                s['energy'] = min(240, int(s['energy']) + 100)
                save(c, ch, s)
                return dict(ok=True, sku=sku, message='+100 energii (limit 240; nadwyżka przepadła).')
            if v['kind'] == 'speedup':
                queue = [t for t in s['contracts'] if t['end'] > now()]
                if not queue:fail(409, 'Żadne zlecenie teraz nie trwa — przyspieszenie wymaga aktywnego zlecenia.')
                t = min(queue, key=lambda x: x['end'])
                new_end = t['end'] - max(1, (t['end'] - t['start']) // 2)
                if new_end <= now():fail(409, 'To zlecenie już prawie się kończy — poczekaj na odbiór nagrody.')
                t['end'] = new_end
                save(c, ch, s)
                return dict(ok=True, sku=sku, message='Zlecenie skrócone o połowę (dev).')
            if v['kind'] == 'skin':
                c.execute('UPDATE shop_state SET skin=? WHERE account_id=?', (sku, u['id']))
                return dict(ok=True, sku=sku, message='Skórka kupiona i założona (kosmetyka, zero statystyk).')
    return dict(st=st, vip_until=vip_until, stamp=stamp, summary=summary, usage=usage, guardian_info=guardian_info, SCHEMA=SCHEMA)
