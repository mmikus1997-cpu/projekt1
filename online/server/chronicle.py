"""0.17 Kronika miasta: publiczna, tylko-do-czytania historia wspólnych momentów świata.

Zapisujemy wyłącznie wydarzenia „międzyludzkie": założenie organizacji, wspólne
wyzwanie miasta (0.16) w trakcie/zaliczone/przepadnięte/anulowane oraz kontrakt
organizacji (0.15) zaliczony lub przepadnięty. Czysto kosmetyczne: brak statystyk,
gotówki i losowości. Limit 300 wpisów na świat; do stanu gry trafia 15 najnowszych.
Wpisy zapisujemy w tej samej transakcji co fakt, więc kronika nigdy nie kłamie.
"""
SCHEMA = '''
CREATE TABLE IF NOT EXISTS chronicle(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,kind TEXT NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',district TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS chronicle_world ON chronicle(world_id,id DESC);
'''
CAP = 300


def fmt(n):
    return f'{n:,}'.replace(',', ' ')


def install(app, d, E):
    db, now = d.db, d.now
    c = db.connect()
    try:
        c.executescript(SCHEMA);c.commit()
    finally:
        c.close()

    def record(c, wid, kind, title, description='', district=''):
        c.execute('INSERT INTO chronicle(world_id,kind,title,description,district,created_at) VALUES(?,?,?,?,?,?)', (wid, kind, title, description, district, now()))
        c.execute('DELETE FROM chronicle WHERE world_id=? AND id NOT IN (SELECT id FROM chronicle WHERE world_id=? ORDER BY id DESC LIMIT ?)', (wid, wid, CAP))

    def feed(c, wid, limit=15):
        return [dict(r) for r in c.execute('SELECT id,kind,title,description,district,created_at FROM chronicle WHERE world_id=? ORDER BY id DESC LIMIT ?', (wid, limit)).fetchall()]

    return dict(record=record, feed=feed)


# Gotowe teksty wpisów — używane przez city_events (0.16) i features (0.15, organizacje).
def city_new(rec, c, wid, name, description, kind, district, target):
    goal = fmt(target) + (' XP miasta.' if kind == 'xp' else ' $ prestiżu w ' + district + '.')
    rec(c, wid, 'city_new', 'Miasto ogłasza wyzwanie: ' + name, (description.strip() + ' ' if description.strip() else '') + 'Wspólny cel: ' + goal, district if kind == 'prestige' else '')


def city_done(rec, c, wid, name):
    rec(c, wid, 'city_done', 'Wyzwanie „' + name + '” zaliczone', 'Odznaka Pioniera: ' + name + ' — dla mieszkańców świata (kosmetyka).')


def city_missed(rec, c, wid, name):
    rec(c, wid, 'city_missed', 'Wyzwanie „' + name + '” przepadło', 'Termin minął bez zaliczenia wspólnego celu.')


def city_cancel(rec, c, wid, name):
    rec(c, wid, 'city_cancel', 'Wyzwanie „' + name + '” anulowane', 'Administrator świata zakończył cel przed terminem.')


def org_founded(rec, c, wid, name, tag, description):
    rec(c, wid, 'org_founded', 'Powstaje organizacja ' + name + ' [' + tag + ']', description.strip())


def org_done(rec, c, wid, name, tag, kind, district, target):
    goal = ('Zbiórka ' + fmt(target) + ' $ do funduszu zakończona.' if kind == 'fund' else 'Prestiż w ' + district + ': +' + fmt(target) + ' $.')
    rec(c, wid, 'org_done', name + ' [' + tag + '] zalicza wspólny cel', goal, district or '')


def org_missed(rec, c, wid, name, tag, kind, district):
    goal = ('Zbiórka do funduszu wygasła bez realizacji.' if kind == 'fund' else 'Cel prestiżu w ' + district + ' wygasł bez realizacji.')
    rec(c, wid, 'org_missed', name + ' [' + tag + '] nie zdążyła z celem', goal, district or '')
