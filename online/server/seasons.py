"""5.4 GDD v3.1: miesięczne sezony rankingowe Elo (per świat).

Sezon = miesiąc kalendarzowy UTC. Numeracja (rok-2026)*12+miesiąc — październik 2026 = 10,
czyli ciągłość ze starymi 28-dniowymi sezonami XP (ostatni archiwizowany = 9, patrz features.XP_SEASON_LAST).
Zamknięcie sezonu (leniwe: przed każdą walką rankingową, w rankingu graczy i w wątku sweep):
  - ranking świata po rating DESC, id; nagradzani tylko gracze z ≥1 walką rankingową w sezonie,
  - Top 10: ramka diamentowa + 600💎 + Tytuł Sezonu; Top 100: ramka złota + 200💎; Top 1000: ramka srebrna + 50💎,
  - 💎 trafiają na postać (s['diamonds']), ramki do s['frames'] (zachowywane przy resecie),
  - reset Elo wszystkich postaci świata do 1000.
Ranking XP pozostaje całoroczny, bez sezonów (decyzja usera).
"""
import datetime
import json

from fastapi import Depends

MONTHLY_START = 10          # pierwszy sezon miesięczny (październik 2026)
RATING_START = 1000
TIERS = ((10, 'diamond', 600, 'Diamentowa'), (100, 'gold', 200, 'Złota'), (1000, 'silver', 50, 'Srebrna'))

SCHEMA = '''
CREATE TABLE IF NOT EXISTS elo_seasons(world_id INTEGER NOT NULL REFERENCES worlds(id),season INTEGER NOT NULL,closed_at INTEGER NOT NULL,players INTEGER NOT NULL,PRIMARY KEY(world_id,season));
CREATE TABLE IF NOT EXISTS elo_season_results(world_id INTEGER NOT NULL,season INTEGER NOT NULL,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,place INTEGER NOT NULL,rating REAL NOT NULL,tier TEXT NOT NULL,diamonds INTEGER NOT NULL,PRIMARY KEY(world_id,season,character_id));
'''


def month_season(t):
    d = datetime.datetime.fromtimestamp(t / 1000, datetime.timezone.utc)
    return (d.year - 2026) * 12 + d.month


def bounds(sn):
    """[początek, koniec) sezonu w ms UTC — koniec = 00:00 UTC pierwszego dnia następnego miesiąca."""
    y, m = 2026 + (sn - 1) // 12, (sn - 1) % 12 + 1
    ny, nm = (y + 1, 1) if m == 12 else (y, m + 1)
    ms = lambda a, b: int(datetime.datetime(a, b, 1, tzinfo=datetime.timezone.utc).timestamp() * 1000)
    return ms(y, m), ms(ny, nm)


def tier_of(place):
    for limit, code, dia, label in TIERS:
        if place <= limit:
            return code, dia, label
    return None


def install(app, db, d, E):
    with db.tx() as c:
        c.executescript(SCHEMA)

    def emit(c, wid, cid, kind, payload):
        c.execute('INSERT INTO game_events(world_id,character_id,kind,payload,created_at) VALUES(?,?,?,?,?)', (wid, cid, kind, json.dumps(payload, ensure_ascii=False, separators=(',', ':')), d.now()))

    def close(c, wid, sn):
        start, end = bounds(sn)
        rows = c.execute('''SELECT ch.id,ch.rating,ch.state_json FROM characters ch JOIN accounts a ON a.id=ch.account_id
            WHERE ch.world_id=? AND a.banned=0 AND EXISTS(SELECT 1 FROM ranked_usage r WHERE r.character_id=ch.id AND r.day>=? AND r.day<? AND r.used>0)
            ORDER BY ch.rating DESC,ch.id LIMIT 1000''', (wid, start, end)).fetchall()
        for place, r in enumerate(rows, 1):
            code, dia, label = tier_of(place)
            s = json.loads(r['state_json'])
            frame = f'season-{sn}-{code}'
            s.setdefault('frames', [])
            if frame not in s['frames']:
                s['frames'].append(frame)
            s['diamonds'] = s.get('diamonds', 0) + dia
            E.log(s, f'🏆 Koniec sezonu {sn}: miejsce {place} — ramka {label}, +{dia} 💎.', d.now())
            c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, ensure_ascii=False, separators=(',', ':')), r['id']))
            if code == 'diamond':
                c.execute('INSERT INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,?,?,?,?)', (r['id'], sn, 'season_top10', f'Tytuł Sezonu {sn} — Top 10', d.now()))
            c.execute('INSERT INTO elo_season_results(world_id,season,character_id,place,rating,tier,diamonds) VALUES(?,?,?,?,?,?,?)', (wid, sn, r['id'], place, r['rating'], code, dia))
            emit(c, wid, r['id'], 'season.reward', {'season': sn, 'place': place, 'tier': code, 'diamonds': dia, 'frame': frame, 'title': code == 'diamond'})
        c.execute('UPDATE characters SET rating=? WHERE world_id=?', (RATING_START, wid))   # reset Elo
        c.execute('INSERT INTO elo_seasons(world_id,season,closed_at,players) VALUES(?,?,?,?)', (wid, sn, d.now(), len(rows)))

    def ensure(c):
        """Zamyka wszystkie zakończone, niezamknięte sezony (≥ MONTHLY_START) we wszystkich światach."""
        cur = month_season(d.now())
        if cur <= MONTHLY_START:
            return 0
        n = 0
        for w in c.execute('SELECT id FROM worlds ORDER BY id').fetchall():
            done = {r['season'] for r in c.execute('SELECT season FROM elo_seasons WHERE world_id=?', (w['id'],))}
            for sn in range(MONTHLY_START, cur):
                if sn not in done:
                    close(c, w['id'], sn); n += 1
        return n

    @app.get('/api/worlds/{wid}/elo-season')
    def elo_season(wid: int, u=Depends(d.auth)):
        with db.tx() as c:
            ensure(c)
            ch = d.own(c, u['id'], wid)
            sn = month_season(d.now()); start, end = bounds(sn)
            last = c.execute('SELECT season,place,tier,diamonds,rating FROM elo_season_results WHERE character_id=? ORDER BY season DESC LIMIT 12', (ch['id'],)).fetchall()
            return dict(season=sn, monthly=sn >= MONTHLY_START, startsAt=start, endsAt=end, rating=ch['rating'],
                        tiers=[dict(top=t[0], tier=t[1], diamonds=t[2], frame=t[3], title=t[1] == 'diamond') for t in TIERS],
                        history=[dict(r) for r in last])

    # Flutter „Ranking Świata”: 4 zestawienia jednego świata (Top 20 + moja pozycja).
    # Elo = bieżący sezon miesięczny; Lochy = rekord pięter (normal/hard/nightmare); Prestiż = liczba resetów
    # w Sali Chwały; Bogacze = gotówka postaci. Konta zbanowane pominięte.
    RANK_LIMIT = 20

    @app.get('/api/worlds/{wid}/rankings')
    def world_rankings(wid: int, u=Depends(d.auth)):
        with db.tx() as c:
            ensure(c)
            me = d.own(c, u['id'], wid)
            sn = month_season(d.now()); start, end = bounds(sn)
            has_resets = bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='server_resets'").fetchone())
            resets = ('(SELECT count(*) FROM server_resets r WHERE r.character_id=ch.id)' if has_resets else '0')
            rows = c.execute('SELECT ch.id,ch.nickname,ch.rating,ch.wins,ch.losses,ch.draws,ch.class_type,'
                             'coalesce(ch.dungeon_normal,0) dn,coalesce(ch.dungeon_hard,0) dh,coalesce(ch.dungeon_nightmare,0) dnm,'
                             f'{resets} resets,json_extract(ch.state_json,"$.cash") cash,json_extract(ch.state_json,"$.xp") xp,'
                             '(SELECT o.tag FROM org_members m JOIN organizations o ON o.id=m.org_id WHERE m.character_id=ch.id) tag '
                             'FROM characters ch JOIN accounts a ON a.id=ch.account_id WHERE ch.world_id=? AND a.banned=0', (wid,)).fetchall()
            base = [dict(id=r['id'], nickname=r['nickname'], tag=r['tag'], level=E.level(r['xp'] or 0), cls=r['class_type']) for r in rows]

            def board(key, extra):
                order = sorted(range(len(rows)), key=lambda i: (-key(rows[i]), rows[i]['id']))
                out = [dict(base[i], place=n + 1, value=key(rows[i]), **extra(rows[i])) for n, i in enumerate(order)]
                mine = next((x for x in out if x['id'] == me['id']), None)
                return dict(rows=out[:RANK_LIMIT], me=mine, total=len(out))

            pvp = board(lambda r: round(r['rating'] or 0), lambda r: dict(wins=r['wins'], losses=r['losses'], draws=r['draws']))
            # sortowanie Lochów: najpierw tryb Nightmare, potem Hard, potem Normal (rekord pięter w trybie)
            order = sorted(rows, key=lambda r: (-r['dnm'], -r['dh'], -r['dn'], r['id']))
            drows = [dict(base[[x['id'] for x in rows].index(r['id'])], place=n + 1, value=r['dnm'] or r['dh'] or r['dn'],
                          mode='nightmare' if r['dnm'] else 'hard' if r['dh'] else 'normal', normal=r['dn'], hard=r['dh'], nightmare=r['dnm'])
                     for n, r in enumerate(order)]
            dungeon = dict(rows=drows[:RANK_LIMIT], me=next((x for x in drows if x['id'] == me['id']), None), total=len(drows))
            prestige = board(lambda r: int(r['resets'] or 0), lambda r: {})
            wealth = board(lambda r: int(r['cash'] or 0), lambda r: {})
            return dict(season=sn, seasonStartsAt=start, seasonEndsAt=end, serverTime=d.now(),
                        pvp=pvp, dungeon=dungeon, prestige=prestige, wealth=wealth)

    return dict(ensure=ensure, month_season=month_season, bounds=bounds)
