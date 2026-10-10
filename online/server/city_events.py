"""0.16 Eventy miejskie: wspólny cel całego świata ustawiany przez administratora.

Nagroda czysto reputacyjna: odznaka-tytuł „Pionier: ⟨nazwa⟩" dla mieszkańców świata
w chwili zaliczenia (wpisuje się do `character_titles`, widoczna jako chip w rankingu).
Zero premii do siły, zero wypłat, zero losowości. Jeden aktywny event na świat
(częściowy indeks). Wygasanie i zaliczenie liczą się leniwie przy odczycie stanu.
"""
import json

from fastapi import Depends
# 0.33: harmonogram Er — Era I: dzielnice 1–3 i firmy do poziomu 2; Era II: +4–5 i praca PC;
# Era III: +6–7 i pojazdy premium; Era IV: +8, epilog i przygotowanie sezonu.
ERAS=[
 dict(n=1,label='Czas Pionierów',districts=3,business=2,pc=False,premium=False),
 dict(n=2,label='Rozwój Przemysłu',districts=5,business=7,pc=True,premium=False),
 dict(n=3,label='Wielki Biznes',districts=6,business=7,pc=True,premium=True),
 dict(n=4,label='Metropolia & Epilog',districts=8,business=7,pc=True,premium=True),
]
ERA_DAY=86400000
def era_of(w,now_ts):
    day=int((now_ts-w['created_at'])//ERA_DAY)+1
    n=1+min(3,max(0,(day-1)//7))
    e=ERAS[n-1]
    sn=max(1,(now_ts-_seasons.SEASON_ANCHOR)//_seasons.SEASON_LEN+1)
    nxt=None if n>=4 else dict(n=n+1,label=ERAS[n]['label'],districts=ERAS[n]['districts'],inDays=-(-(w['created_at']+7*n*ERA_DAY-now_ts)//ERA_DAY))
    return dict(n=n,label=e['label'],day=min(day,28),total=28,districts=e['districts'],business=e['business'],pc=e['pc'],premium=e['premium'],final=bool(day>=28),
        next=nxt,epilog=bool(n==4),
        season=dict(n=sn,endsAt=_seasons.SEASON_ANCHOR+sn*_seasons.SEASON_LEN,daysLeft=-(-(_seasons.SEASON_ANCHOR+sn*_seasons.SEASON_LEN-now_ts)//ERA_DAY)))
from pydantic import BaseModel, Field

from . import chronicle
from . import features as _seasons  # 0.34: 28-dniowy rytm rankingowy (season_of/SEASON_*)

SCHEMA = '''
CREATE TABLE IF NOT EXISTS city_events(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,name TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',kind TEXT NOT NULL,district TEXT NOT NULL DEFAULT '',target INTEGER NOT NULL,baseline INTEGER NOT NULL,deadline INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',created_by INTEGER REFERENCES accounts(id) ON DELETE SET NULL,created_at INTEGER NOT NULL,done_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS city_event_active ON city_events(world_id) WHERE status='active';
CREATE INDEX IF NOT EXISTS city_events_world ON city_events(world_id,id DESC);
'''


class CityEventCreate(BaseModel):
    world_id: int = Field(ge=1, le=1000000)
    name: str = Field(min_length=3, max_length=60)
    description: str = Field(default='', max_length=300)
    kind: str = Field(pattern='^(xp|prestige)$')
    district: str = Field(default='', max_length=40)
    target: int = Field(ge=100, le=500000)
    hours: int = Field(ge=24, le=336)


class CityEventCancel(BaseModel):
    id: int = Field(ge=1, le=10000000)


def install(app, d, E):
    db, now, fail, admin, audit = d.db, d.now, d.fail, d.admin, d.audit
    rec = d.chronicle['record']
    c = db.connect()
    try:
        c.executescript(SCHEMA);c.commit()
    finally:
        c.close()

    def emit(c, wid, cids, kind, payload):
        for cid in set(cids):
            c.execute('INSERT INTO game_events(world_id,character_id,kind,payload,created_at) VALUES(?,?,?,?,?)', (wid, cid, kind, json.dumps(payload, ensure_ascii=False, separators=(',', ':')), now()))
            c.execute('DELETE FROM game_events WHERE character_id=? AND id NOT IN (SELECT id FROM game_events WHERE character_id=? ORDER BY id DESC LIMIT 100)', (cid, cid))

    def world_chars(c, wid):
        return [r['id'] for r in c.execute('SELECT id FROM characters WHERE world_id=?', (wid,)).fetchall()]

    def progress(c, row):
        if row['kind'] == 'xp':
            cur = c.execute('SELECT coalesce(sum(json_extract(state_json,"$.xp")),0) FROM characters WHERE world_id=?', (row['world_id'],)).fetchone()[0]
        else:
            cur = c.execute('SELECT coalesce(sum(i.total),0) FROM org_investments i JOIN organizations o ON o.id=i.org_id WHERE o.world_id=? AND i.district=?', (row['world_id'], row['district'])).fetchone()[0]
        return max(0, cur - row['baseline'])

    def current(c, wid):
        # lazy settlement: deadline first, then target; returns public payload or None
        row = c.execute("SELECT * FROM city_events WHERE world_id=? AND status='active'", (wid,)).fetchone()
        if not row:return None
        if row['deadline'] <= now():
            c.execute("UPDATE city_events SET status='missed' WHERE id=?", (row['id'],))
            emit(c, wid, world_chars(c, wid), 'city.event_missed', {'name': row['name']})
            chronicle.city_missed(rec, c, wid, row['name'])
            return None
        if progress(c, row) >= row['target']:
            c.execute("UPDATE city_events SET status='done',done_at=? WHERE id=?", (now(), row['id']))
            chars = world_chars(c, wid)
            for cid in chars:
                c.execute('INSERT OR IGNORE INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,0,?,?,?)', (cid, 'event_' + str(row['id']), 'Pionier: ' + row['name'], now()))
            emit(c, wid, chars, 'city.event_done', {'name': row['name']})
            chronicle.city_done(rec, c, wid, row['name'])
            return None
        return dict(id=row['id'], name=row['name'], description=row['description'], kind=row['kind'], district=row['district'], target=row['target'], progress=progress(c, row), endsAt=row['deadline'])

    def overview(c):
        rows = []
        for r in c.execute('SELECT * FROM city_events ORDER BY id DESC LIMIT 20').fetchall():
            rows.append(dict(id=r['id'], world_id=r['world_id'], name=r['name'], kind=r['kind'], district=r['district'], target=r['target'], progress=progress(c, r) if r['status'] == 'active' else None, deadline=r['deadline'], status=r['status']))
        return rows

    @app.post('/api/admin/events')
    def create_event(data: CityEventCreate, u=Depends(admin)):
        name = data.name.strip()
        if data.kind == 'prestige':
            if data.district not in E.DISTRICTS:fail(422, 'Wybierz dzielnicę dla celu prestiżowego.')
            if data.target > 50000:fail(422, 'Cel prestiżowy: do 50 000 $.')
        with db.tx() as c:
            w = c.execute('SELECT id FROM worlds WHERE id=?', (data.world_id,)).fetchone()
            if not w:fail(404, 'Nie ma takiego świata.')
            if c.execute("SELECT 1 FROM city_events WHERE world_id=? AND status='active'", (data.world_id,)).fetchone():fail(409, 'Ten świat ma już aktywny event miejski.')
            if data.kind == 'xp':
                baseline = c.execute('SELECT coalesce(sum(json_extract(state_json,"$.xp")),0) FROM characters WHERE world_id=?', (data.world_id,)).fetchone()[0]
                district = ''
            else:
                baseline = c.execute('SELECT coalesce(sum(i.total),0) FROM org_investments i JOIN organizations o ON o.id=i.org_id WHERE o.world_id=? AND i.district=?', (data.world_id, data.district)).fetchone()[0]
                district = data.district
            eid = c.execute("INSERT INTO city_events(world_id,name,description,kind,district,target,baseline,deadline,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", (data.world_id, name, data.description.strip(), data.kind, district, data.target, baseline, now() + data.hours * 3600000, u['id'], now())).lastrowid
            audit(c, u['id'], 'city.event_create', dict(event=eid, world=data.world_id, kind=data.kind, target=data.target, hours=data.hours))
            emit(c, data.world_id, world_chars(c, data.world_id), 'city.event_created', {'name': name, 'kind': data.kind, 'district': district, 'target': data.target})
            chronicle.city_new(rec, c, data.world_id, name, data.description, data.kind, district, data.target)
            return dict(id=eid)

    @app.post('/api/admin/events/{eid}/cancel')
    def cancel_event(eid:int, u=Depends(admin)):
        with db.tx() as c:
            row = c.execute('SELECT * FROM city_events WHERE id=?', (eid,)).fetchone()
            if not row:fail(404, 'Nie ma takiego eventu.')
            if row['status'] != 'active':fail(409, 'Ten event już się zakończył.')
            c.execute("UPDATE city_events SET status='cancelled' WHERE id=?", (eid,))
            audit(c, u['id'], 'city.event_cancel', dict(event=eid))
            emit(c, row['world_id'], world_chars(c, row['world_id']), 'city.event_cancelled', {'name': row['name']})
            chronicle.city_cancel(rec, c, row['world_id'], row['name'])
            return {'ok': True}
    # --- 0.33 System Er Świata: 28-dniowy cykl żywotności liczony od created_at świata. ---
    def era(c,wid):
        w=c.execute('SELECT * FROM worlds WHERE id=?',(wid,)).fetchone()
        if not w:fail(404,'Nie ma takiego świata.')
        info=era_of(w,now())
        if (w['world_era'] or 1)!=info['n']:
            c.execute('UPDATE worlds SET world_era=? WHERE id=?',(info['n'],wid))
            rec(c,wid,'era','Era '+str(info['n'])+': '+info['label'],'Miasto rośnie — otwarte dzielnice 1–'+str(info['districts'])+' (dzień '+str(info['day'])+'/28).')
        return info
    def era_n(c,wid):
        w=c.execute('SELECT created_at,world_era FROM worlds WHERE id=?',(wid,)).fetchone()
        if not w:fail(404,'Nie ma takiego świata.')
        return era_of(w,now())['n']
    return dict(current=current, overview=overview, emit=emit, era=era, era_n=era_n)
