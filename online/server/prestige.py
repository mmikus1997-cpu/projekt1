"""4.5 GDD v3.1: Sala Chwały — prestiżowy RESET postaci na serwerze (świecie).

Trzy kroki (serwer pilnuje wszystkich):
  1) POST /server_reset bez confirm_text → podsumowanie + „uzbrojenie” resetu (start licznika 10 s);
  2) confirm_text musi brzmieć dokładnie „RESET POTWIERDZAM”;
  3) wykonanie najwcześniej 10 s po kroku 1 (UI: timer na przycisku), najpóźniej 10 min.
"""
import json
from typing import Optional
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field

RESET_CONFIRM = 'RESET POTWIERDZAM'
ARM_DELAY_MS = 10_000
ARM_TTL_MS = 10 * 60_000
BONUS_STEP = 10      # +10% dochodu za każdy reset na tym świecie
BONUS_MAX = 50       # sufit +50%

SCHEMA = """
CREATE TABLE IF NOT EXISTS server_resets(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,
  world_id INTEGER NOT NULL,
  reset_n INTEGER NOT NULL,
  bonus_pct INTEGER NOT NULL,
  diamonds_returned INTEGER NOT NULL DEFAULT 0,
  created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS server_resets_char ON server_resets(character_id);
"""
ACCOUNT_COLUMNS = (('premium_currency', ' INTEGER NOT NULL DEFAULT 0'), ('prestige_points', ' INTEGER NOT NULL DEFAULT 0'))

WIPES = ['gotówka (do kwoty startowej)', 'poziom postaci i XP (powrót do poziomu 1)', 'firmy (City Courier od poziomu 1, Studio Forma do kupienia)', 'poziomy budynków (w tym Sala Chwały i Buffet)', 'skarbce Kawiarni i Klubu Nocnego',
         'zatrudnieni NPC (także ci na zmianie — bez wypłaty)', 'auta w Garażu (z Mistrzem Rankingu)', 'konie i stajnia',
         'statystyki postaci', 'ewolucja klasy', 'AI Manager, personel firm, licznik dyspozytora']
KEEPS = ['wygląd i kosmetyki awatara', 'czas VIP', 'postęp Battle Passa', 'Punkty Prestiżu', 'cały ekwipunek', 'tytuły i ramki', 'ranking PvP']


class ResetIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    confirm_text: Optional[str] = Field(default=None, max_length=40)


def bonus_for(n):
    return min(BONUS_MAX, BONUS_STEP * n)


def install(app, d, E):
    db, now, fail, world, own, auth, audit, emit, chron = d.db, d.now, d.fail, d.world, d.own, d.auth, d.audit, d.emit, d.chronicle
    c = db.connect()
    try:
        c.executescript(SCHEMA)
        have = {r['name'] for r in c.execute('PRAGMA table_info(accounts)')}
        for name, ddl in ACCOUNT_COLUMNS:          # migracja addytywna — kompatybilna wstecz
            if name not in have:
                c.execute('ALTER TABLE accounts ADD COLUMN ' + name + ddl)
        c.commit()
    finally:
        c.close()

    def summary(c, u, ch, s):
        n = c.execute('SELECT count(*) FROM server_resets WHERE character_id=?', (ch['id'],)).fetchone()[0] + 1
        acc = c.execute('SELECT premium_currency,prestige_points FROM accounts WHERE id=?', (u['id'],)).fetchone()
        return dict(resetNumber=n, bonusAfter=bonus_for(n), bonusNow=int((s.get('prestige') or {}).get('bonus', 0)),
                    bonusMax=BONUS_MAX, prestigePoints=acc['prestige_points'], prestigeAfter=acc['prestige_points'] + 1,
                    diamondsToAccount=int(s.get('diamonds') or 0), frame=f'Reset #{n}', wipes=WIPES, keeps=KEEPS,
                    npcs=c.execute('SELECT count(*) FROM npcs WHERE character_id=?', (ch['id'],)).fetchone()[0],
                    confirmText=RESET_CONFIRM, delaySeconds=ARM_DELAY_MS // 1000)

    def wipe(s, t, n, bonus):
        fresh = E.new(t)
        s['cash'] = fresh['cash']
        s['xp'] = 0                                   # korekta usera: powrót do poziomu 1
        s['business'] = fresh['business']             # korekta usera: firmy od zera (kurier lvl 1, Studio do kupienia)
        s['ventures'] = {k: None for k in E.VENTURES}
        s['frames'] = sorted(set((s.get('frames') or []) + [f'reset-{n}']))   # ramki kolekcjonowane
        s['buildings'] = dict(E.BUILDING_START)
        s['vaults'] = {k: 0 for k in E.BUILDING_VAULTS}
        s['buffet'] = 0
        s['garage'], s['vehicle'], s['cars'], s['garageUp'] = [], None, {}, {}
        s['horse'], s['horses'] = None, {}
        s['stats'] = [10] * 5
        s['evolutionCode'] = None
        s['aiManager'], s['staff'], s['dispatch'] = {}, {}, {}
        s.pop('diamonds', None)
        s['prestige'] = dict(resets=n, bonus=bonus)
        s['frame'] = f'reset-{n}'
        s.pop('resetArmedAt', None)
        E.log(s, f'🏆 Reset #{n}: miasto od nowa — stały bonus dochodu +{bonus}% na tym świecie.', t)

    @app.post('/api/worlds/{wid}/server_reset')
    def server_reset(wid: int, data: ResetIn, request: Request, u=Depends(auth)):
        with db.tx() as c:
            w = world(c, wid, True)
            ch = own(c, u['id'], wid)
            s = json.loads(ch['state_json'])
            t = now()
            E.sync(s, t, w['speed'])
            if (s.get('buildings') or {}).get('hall', 0) < 1:
                fail(409, 'Reset jest dostępny w Sali Chwały — najpierw ją odblokuj (wszystkie budynki na max + 10 000 $).')
            if ch['travel_destination']:
                fail(409, 'Jesteś w drodze — reset po przyjeździe.')
            info = summary(c, u, ch, s)
            if data.confirm_text is None:               # krok 1: podsumowanie + uzbrojenie
                s['resetArmedAt'] = t
                c.execute('UPDATE characters SET state_json=? WHERE id=?', (json.dumps(s, separators=(',', ':')), ch['id']))
                return dict(step=1, armedAt=t, executeAfter=t + ARM_DELAY_MS, **info)
            if data.confirm_text != RESET_CONFIRM:     # krok 2
                fail(422, f'Wpisz dokładnie: {RESET_CONFIRM}')
            armed = s.get('resetArmedAt')
            if not armed or t - armed > ARM_TTL_MS:
                fail(409, 'Potwierdzenie wygasło — zacznij od podsumowania resetu.')
            if t - armed < ARM_DELAY_MS:               # krok 3: timer 10 s
                fail(409, f'Odczekaj jeszcze {(ARM_DELAY_MS - (t - armed) + 999) // 1000} s.')
            n, bonus, dia = info['resetNumber'], info['bonusAfter'], info['diamondsToAccount']
            wipe(s, t, n, bonus)
            c.execute('DELETE FROM npcs WHERE character_id=?', (ch['id'],))
            c.execute('DELETE FROM vehicles WHERE character_id=?', (ch['id'],))
            c.execute('UPDATE characters SET state_json=?,class_evolution=1 WHERE id=?',
                      (json.dumps(s, ensure_ascii=False, separators=(',', ':')), ch['id']))
            c.execute('UPDATE accounts SET prestige_points=prestige_points+1,premium_currency=premium_currency+? WHERE id=?', (dia, u['id']))
            c.execute('INSERT INTO server_resets(account_id,character_id,world_id,reset_n,bonus_pct,diamonds_returned,created_at) VALUES(?,?,?,?,?,?,?)',
                      (u['id'], ch['id'], wid, n, bonus, dia, t))
            c.execute('INSERT INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,0,?,?,?)',
                      (ch['id'], f'reset_{n}', f'Reset #{n}', t))
            chron['record'](c, wid, 'server_reset', f"{ch['nickname']} — Reset #{n} w Sali Chwały",
                            f'Miasto od nowa ze stałym bonusem +{bonus}% dochodu.')
            emit(c, wid, [ch['id']], 'prestige.reset', dict(n=n, bonus=bonus, diamonds=dia))
            audit(c, u['id'], 'server.reset', dict(character_id=ch['id'], world_id=wid, n=n, bonus=bonus, diamonds=dia))
            acc = c.execute('SELECT premium_currency,prestige_points FROM accounts WHERE id=?', (u['id'],)).fetchone()
            return dict(step=3, done=True, resetNumber=n, bonus=bonus, prestigePoints=acc['prestige_points'],
                        premiumCurrency=acc['premium_currency'], frame=f'Reset #{n}',
                        message=f'🏆 Reset #{n} zakończony: +1 Punkt Prestiżu, stały bonus dochodu +{bonus}%.')

    return dict(bonus_for=bonus_for)
