#!/usr/bin/env python3
"""Zasiew kont sparingowych do PvP (0.44) — świat, w którym gra konto 'test'.

Idempotentny: istniejące loginy/postacie/klasy/taktyki są pomijane (409 = OK).
XP dozujemy bezpośrednio w bazie (serwer czyta stan przy każdym żądaniu).
Użycie: python tools/seed_sparring.py [--base http://127.0.0.1:3000]
"""
import argparse, json, pathlib, sqlite3
import httpx

ROOT = pathlib.Path(__file__).resolve().parents[1]
DB = ROOT / 'data' / 'city_empire.sqlite3'
PASSWORD = 'sparring-arena-2026'
# (login, nick, klasa, taktyka, xp-docelowe)
ACCOUNTS = [
    ('riva',           'Riva',            'szybki',   'presja',    800),
    ('marek_metal',    'Marek Metal',     'obronca',  'kontrola', 1500),
    ('ninja_osiedle',  'Ninja z Osiedla', 'szybki',   'kontra',   2600),
    ('zelazna_logika', 'Żelazna Logika',  'obronca',  'kontrola', 3300),
    ('doktor_cios',    'Doktor Cios',     'bokser',   'presja',   4200),
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', default='http://127.0.0.1:3000')
    a = ap.parse_args()
    con = sqlite3.connect(DB)
    row = con.execute("SELECT world_id FROM characters WHERE nickname='test'").fetchone()
    wid = row[0] if row else con.execute('SELECT id FROM worlds ORDER BY id LIMIT 1').fetchone()[0]
    print('Świat docelowy:', wid)
    c = httpx.Client(base_url=a.base, timeout=30)
    for login, nick, cls, style, xp in ACCOUNTS:
        r = c.post('/api/auth/register', json={'username': login, 'password': PASSWORD, 'consent': True})
        if r.status_code == 409:
            r = c.post('/api/auth/login', json={'username': login, 'password': PASSWORD})
        if r.status_code != 200:
            print(f'{login}: auth HTTP {r.status_code} {r.text[:90]}')
            continue
        d = r.json()
        token = d.get('previewSessionToken')
        c.headers.update({'X-CSRF-Token': d['csrf'], **({'Authorization': 'Bearer ' + token} if token else {})})
        ch = c.post(f'/api/worlds/{wid}/character', json={'nickname': nick, 'accept_test_reset': True})
        print(f'{login}: postać "{nick}" -> {ch.status_code}' + ('' if ch.status_code == 200 else ' (jest?)'))
        cl = c.post(f'/api/worlds/{wid}/class', json={'class_type': cls})
        print(f'{login}: klasa {cls} -> {cl.status_code}' + ('' if cl.status_code in (200, 409) else ' ' + cl.text[:90]))
        tc = c.post(f'/api/worlds/{wid}/tactic', json={'style': style})
        print(f'{login}: taktyka {style} -> {tc.status_code}')
    for login, nick, cls, style, xp in ACCOUNTS:
        row = con.execute('SELECT state_json FROM characters WHERE nickname=? AND world_id=?', (nick, wid)).fetchone()
        if not row:
            print(f'!! brak postaci {nick} — XP niedosypany')
            continue
        st = json.loads(row[0]); st['xp'] = xp
        con.execute('UPDATE characters SET state_json=? WHERE nickname=? AND world_id=?', (json.dumps(st), nick, wid))
    con.commit()
    n = con.execute('SELECT count(*) FROM characters WHERE world_id=?', (wid,)).fetchone()[0]
    lvl = con.execute("SELECT json_extract(state_json,'$.xp') FROM characters WHERE nickname='test'").fetchone()
    print('Postaci w świecie:', n, '| XP konta test:', lvl and lvl[0])
    con.close()
    print('Hasło wszystkich kont sparingowych:', PASSWORD)

if __name__ == '__main__':
    main()
