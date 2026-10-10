"""3.4 GDD v3.1: kamienie milowe długiej gry. Licznik dni aktywności (UTC) i auto „Mistrz Rankingu” za 7 dni.

Dzień aktywny = co najmniej jedno żądanie do świata (own()) w danym dniu UTC.
Dni nie muszą być kolejne. Nagroda jest jednorazowa (claimed_milestones).
"""
import json
import time
from fastapi import Depends

SCHEMA = """
CREATE TABLE IF NOT EXISTS longplay_milestones(
  character_id INTEGER PRIMARY KEY REFERENCES characters(id) ON DELETE CASCADE,
  active_days INTEGER NOT NULL DEFAULT 0,
  last_active_utc TEXT,
  claimed_milestones TEXT NOT NULL DEFAULT '[]'
);
"""
MILESTONES = {'mistrz_7d': 7}   # kod → wymagane dni aktywności
# 8.1 GDD v3.1: pełna tabela stażu 7–1000 dni (mistrz_7d zostaje — auto Mistrz Rankingu, zgodność wsteczna)
STAZ = {
    'staz_7': dict(days=7, title='🎖️ Debiutant', dia=50, income=10, buildings=dict(cafe=1)),
    'staz_14': dict(days=14, title='📚 Praktykant', dia=70, buildings=dict(residence=2, nightclub=1)),
    'staz_30': dict(days=30, title='🏅 Weteran', dia=100, pets=True),
    'staz_90': dict(days=90, title='👑 Legenda', dia=300, cosmetics=['outfit-legenda']),
    'staz_180': dict(days=180, title='💎 Magnat', dia=500, frame='magnat', nick_color='#d4af37'),
    'staz_365': dict(days=365, title='🌟 Ikona', dia=1000, cosmetics=['pomnik-ikona'], monument=True),
    'staz_1000': dict(days=1000, title='🏛️ Założyciel', income=5, perks=['discord', 'ankiety']),
}
MILESTONES.update({k: v['days'] for k, v in STAZ.items()})
DAY_MS = 86400000


def utc_day(t):
    return time.strftime('%Y-%m-%d', time.gmtime(t / 1000))


def install(app, d, E):
    db, now, fail, own, auth, audit, emit = d.db, d.now, d.fail, d.own, d.auth, d.audit, d.emit
    c = db.connect()
    try:
        c.executescript(SCHEMA)
        c.commit()
    finally:
        c.close()

    def row(c, cid):
        r = c.execute('SELECT * FROM longplay_milestones WHERE character_id=?', (cid,)).fetchone()
        return dict(r) if r else dict(character_id=cid, active_days=0, last_active_utc=None, claimed_milestones='[]')

    def grant_mistrz(c, ch, t):
        """Dodaje Mistrza do garażu (nie zajmuje miejsca), pełny bak, 0% zużycia. Gdy brak aktywnego auta — ustawia go."""
        s = json.loads(ch['state_json'])
        g = s.setdefault('garage', [])
        if 'mistrz' not in g:
            g.append('mistrz')
        E.set_fuel(s, 'mistrz', 100)
        E.set_wear(s, 'mistrz', 0)
        if not s.get('vehicle'):
            s['vehicle'] = dict(id='mistrz', wear=0)
        E.log(s, '🏆 7 dni w grze! Odblokowano auto „Mistrz Rankingu”.', t)
        c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, separators=(',', ':')), ch['id']))

    def grant_staz(c, ch, code, t):
        """8.1: nagroda stażowa — tytuł, 💎 na postać, budynki (min. poziom), zwierzęta, kosmetyka, stały bonus dochodu."""
        m = STAZ[code]
        s = json.loads(c.execute('SELECT state_json FROM characters WHERE id=?', (ch['id'],)).fetchone()[0])
        s['diamonds'] = int(s.get('diamonds') or 0) + m.get('dia', 0)
        if m.get('income'):
            s['seniority'] = int(s.get('seniority') or 0) + m['income']   # E.prestige_mult: każdy $ z pracy
        bl = s.setdefault('buildings', dict(E.BUILDING_START))
        for k, lv in (m.get('buildings') or {}).items():
            bl[k] = max(int(bl.get(k, 0)), lv)
        if m.get('pets'):
            s.setdefault('dogs', {})['kennel-staz-30'] = dict(key='kennel-staz-30', breed='weteran', name='Pies Weterana', speed=8, stamina=8, gen=1, premium=True)
            s.setdefault('horses', {})['stable-staz-30'] = dict(key='stable-staz-30', breed='weteran', name='Koń Weterana', speed=8, stamina=8, gen=1, premium=True)
        for cm in m.get('cosmetics') or []:
            s.setdefault('cosmetics', [])
            if cm not in s['cosmetics']:
                s['cosmetics'].append(cm)
        if m.get('frame'):
            s['frames'] = sorted(set((s.get('frames') or []) + [m['frame']]))
        if m.get('nick_color'):
            s['nickColor'] = m['nick_color']
        if m.get('perks'):
            s['perks'] = sorted(set((s.get('perks') or []) + m['perks']))
        if m.get('monument'):
            s['monument'] = dict(district=ch['current_district'] or 1, since=t)
        E.log(s, f"{m['title']}: {m['days']} dni w grze! Nagroda stażowa odebrana.", t)
        c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, separators=(',', ':')), ch['id']))
        c.execute('INSERT OR IGNORE INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,0,?,?,?)', (ch['id'], code, m['title'], t))

    def touch(c, ch):
        """Wołane z own() przy każdym żądaniu świata. Zwraca True, gdy stan postaci się zmienił."""
        t = now()
        day = utc_day(t)
        r = row(c, ch['id'])
        if r['last_active_utc'] == day:
            return False   # szybka ścieżka: dzień już policzony
        days = r['active_days'] + 1
        claimed = json.loads(r['claimed_milestones'] or '[]')
        changed = False
        if days >= MILESTONES['mistrz_7d'] and 'mistrz_7d' not in claimed:
            grant_mistrz(c, ch, t)
            claimed.append('mistrz_7d')
            changed = True
            emit(c, ch['world_id'], [ch['id']], 'milestone.unlocked', dict(code='mistrz_7d', days=days, vehicle='mistrz'))
            audit(c, ch['account_id'], 'milestone.unlocked', dict(character_id=ch['id'], code='mistrz_7d', days=days))
        for code, m in STAZ.items():
            if days >= m['days'] and code not in claimed:
                grant_staz(c, ch, code, t)
                claimed.append(code)
                changed = True
                emit(c, ch['world_id'], [ch['id']], 'milestone.unlocked', dict(code=code, days=days))
                audit(c, ch['account_id'], 'milestone.unlocked', dict(character_id=ch['id'], code=code, days=days))
        c.execute('INSERT INTO longplay_milestones(character_id,active_days,last_active_utc,claimed_milestones) VALUES(?,?,?,?) '
                  'ON CONFLICT(character_id) DO UPDATE SET active_days=excluded.active_days,last_active_utc=excluded.last_active_utc,'
                  'claimed_milestones=excluded.claimed_milestones', (ch['id'], days, day, json.dumps(claimed)))
        return changed

    @app.get('/api/worlds/{wid}/milestones')
    def milestones(wid: int, u=Depends(auth)):
        """Postęp dla klienta (Flutter): dni aktywności, następny próg, odebrane nagrody."""
        with db.tx() as c:
            ch = own(c, u['id'], wid)
            r = row(c, ch['id'])
            claimed = json.loads(r['claimed_milestones'] or '[]')
            return dict(activeDays=r['active_days'], lastActiveUtc=r['last_active_utc'], claimed=claimed,
                        milestones=[dict(code=k, days=v, claimed=k in claimed, **({'title': STAZ[k]['title'], 'diamonds': STAZ[k].get('dia', 0),
                                                                                    'incomeBonus': STAZ[k].get('income', 0)} if k in STAZ else {}))
                                    for k, v in MILESTONES.items()])

    @app.get('/api/worlds/{wid}/monuments')
    def monuments(wid: int, u=Depends(auth)):
        """8.1: pomniki na mapie (365 dni) — lista dla klienta."""
        with db.tx() as c:
            own(c, u['id'], wid)
            out = []
            for r in c.execute('SELECT id,nickname,state_json FROM characters WHERE world_id=?', (wid,)):
                m = json.loads(r['state_json']).get('monument')
                if m:
                    out.append(dict(characterId=r['id'], nickname=r['nickname'], district=m['district'], since=m['since']))
            return dict(monuments=out)

    return dict(touch=touch)
