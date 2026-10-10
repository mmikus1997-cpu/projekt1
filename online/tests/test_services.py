"""2.2 GDD v3.1: katalog 12 lokacji usługowych + GET /api/worlds/{wid}/services."""
import pytest
from fastapi.testclient import TestClient
from server.app import create_app
from server import services as S, travel as T

def test_catalog_shape():
    assert len(S.SERVICES)==12 and len(S.BY_ID)==12
    assert {x['d'] for x in S.SERVICES}==set(dict(T.DISTRICTS)), 'każda z 8 dzielnic ma usługę'
    for x in S.SERVICES:
        assert x['rate']>0 and x['hunger'] in (2,3)
        assert x['hunger']==(3 if x['energy']<0 else 2), x['id']
    assert S.BY_ID['biblioteka']['mood']==1 and S.BY_ID['park']['mood']==2
    assert set(S.REGEN)=={'biblioteka','park'}
    assert S.BY_ID['park']['d']==6 and S.BY_ID['warsztat']['d']==7 and S.BY_ID['hotel']['d']==8
    assert S.TRANSPORT_MIN_MS==30000 and S.COOLDOWN_AFTER==10 and S.COOLDOWN_MS==120000

def test_view_rules():
    v={x['id']:x for x in S.view({'cash':3000},5)}
    assert v['minimarket']['unlocked'] and v['sprzatanie']['unlocked']
    assert not v['kurier']['unlocked'] and v['kurier']['canUnlock']        # lvl 5, 2000 $ ≤ 3000
    assert not v['warsztat']['levelOk'] and not v['warsztat']['canUnlock']  # lvl 7
    v={x['id']:x for x in S.view({'cash':0,'servicesUnlocked':['kurier']},5)}
    assert v['kurier']['unlocked'] and not v['kurier']['canUnlock']

def test_endpoint(tmp_path):
    app=create_app(tmp_path/'s.sqlite3',lambda:1780000000000,tmp_path/'setup.txt');c=TestClient(app)
    r=c.post('/api/auth/register',json={'username':'uslugi','password':'test-password-long-123','consent':True})
    c.headers['X-CSRF-Token']=r.json()['csrf']
    assert c.get('/api/worlds/2/services').status_code==404   # bez postaci
    assert c.post('/api/worlds/2/character',json={'nickname':'Usluga','accept_test_reset':True}).status_code==200
    r=c.get('/api/worlds/2/services');assert r.status_code==200,r.text
    j=r.json();assert len(j['services'])==12 and j['transportMinMs']==30000
    v={x['id']:x for x in j['services']}
    assert v['minimarket']['unlocked'] and not v['hotel']['levelOk']

def test_preview_allowlist_has_services():
    import inspect, server.app as A
    assert '(?:state|services|' in inspect.getsource(A)


# --- 2.4a GDD v3.1: odblokowanie usług + czas dojazdu ---
import json as _json, sqlite3 as _sq, uuid as _uuid
from server import economy as _E


def _xp_for(level):
    xp = 0
    while _E.level(xp) < level:
        xp += 10
    return xp


def _setup(tmp_path, name, **state):
    app = create_app(tmp_path / 'u.sqlite3', lambda: 1780000000000, tmp_path / 'setup.txt'); c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': name, 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/2/character', json={'nickname': name.title(), 'accept_test_reset': True}).status_code == 200
    with _sq.connect(tmp_path / 'u.sqlite3') as d:
        cid, raw = d.execute('SELECT id,state_json FROM characters').fetchone(); s = _json.loads(raw); s.update(state)
        d.execute('UPDATE characters SET state_json=? WHERE id=?', (_json.dumps(s), cid))
    return c


def _unlock(c, sid, key=None):
    return c.post(f'/api/worlds/2/services/{sid}/unlock', json={}, headers={'Idempotency-Key': key or _uuid.uuid4().hex})


def test_unlock_rules(tmp_path):
    c = _setup(tmp_path, 'odblokuj', cash=2500, xp=_xp_for(5))
    r = _unlock(c, 'warsztat'); assert r.status_code == 409 and '7. poziomu' in r.json()['detail']
    r = _unlock(c, 'minimarket'); assert r.status_code == 409 and 'już' in r.json()['detail']   # darmowa
    k = _uuid.uuid4().hex
    r = _unlock(c, 'kurier', k); assert r.status_code == 200 and r.json()['cash'] == 500
    assert _unlock(c, 'kurier', k).json() == r.json(), 'idempotencja'
    v = {x['id']: x for x in c.get('/api/worlds/2/services').json()['services']}
    assert v['kurier']['unlocked']
    r = _unlock(c, 'callcenter'); assert r.status_code == 409 and '2000' in r.json()['detail']
    assert _unlock(c, 'nieznana').status_code == 404


def test_travel_ms():
    assert S.travel_ms(S.BY_ID['biblioteka'], None, _E) == 30000            # 0 przystanków → minimum
    k = S.BY_ID['klinika']                                                   # Centrum: 1 przystanek
    assert [S.travel_ms(k, car, _E) for car in (None, 'dostawczak', 'sedan', 'suv')] == [120000, 72000, 48000, 42000]
    assert S.travel_ms(S.BY_ID['marketing'], None, _E) == 240000             # Biznesowe: 2 przystanki × 60 s × 2,0


# --- 2.2b GDD v3.1: dynamiczny popyt ---
def test_demand_range_window_and_world():
    T = 1780000000000; W = S.DEMAND_WINDOW_MS
    vals = [S.demand(2, x['id'], T + k * W) for x in S.SERVICES for k in range(40)]
    assert all(0.5 <= v <= 1.5 for v in vals) and min(vals) < 0.7 and max(vals) > 1.3, 'pełny zakres 50–150%'
    start = (T // W) * W
    assert S.demand(2, 'hotel', start) == S.demand(2, 'hotel', start + W - 1), 'stały w oknie 6 h'
    assert any(S.demand(2, 'hotel', start + k * W) != S.demand(2, 'hotel', start) for k in range(1, 5)), 'zmienia się co 6 h'
    assert any(S.demand(2, x['id'], T) != S.demand(3, x['id'], T) for x in S.SERVICES), 'inny między światami'
    b = S.demand_board(2, T)
    assert b['changesAt'] == start + W and len(b['top']) == 3
    assert b['top'][0]['demand'] == max(b['now'].values())


def test_services_api_returns_demand(tmp_path):
    c = _setup(tmp_path, 'popyt')
    j = c.get('/api/worlds/2/services').json()
    assert len(j['demandTop']) == 3 and j['demandWindowMs'] == S.DEMAND_WINDOW_MS
    for x in j['services']:
        assert 0.5 <= x['demand'] <= 1.5 and x['rateNow'] == round(x['baseRate'] * x['demand'], 2)
        assert x['demandChangesAt'] == j['demandChangesAt'] and 0.5 <= x['demandNext'] <= 1.5
    assert {x['id']: x['demand'] for x in j['services']} == S.demand_board(2, 1780000000000)['now'], 'jeden popyt dla świata'


def test_demand_frozen_in_shift():
    from server import npc as N
    T = 1780000000000
    n = dict(id=1, character_id=1, name='A', energy=100.0, mood=100.0, hunger=100.0, unhappy_since=None, warned_at=None, updated_at=T)
    N.clear_shift(n)
    n.update(assigned_service_id='minimarket', autopilot_expires_at=T + 2 * 3600000, travel_ms=30000, shift_bus=0,
             shift_demand=1.5, shift_event=1.0, shift_bonus=0.0)
    N._start_leg(n, 'to_work', T)
    _, evs = N.advance(n, T + 2 * 3600000 + 30000, S)
    assert evs[-1]['cash'] == round((2 - 30 / 3600) * 50 * 1.5)
