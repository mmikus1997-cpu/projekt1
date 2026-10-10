"""0.58.0 Eventy czasowe: okna 6 h, rotacja globalna, premie w kontraktach/trasach/surowcach."""
import json
import sqlite3
import uuid

import pytest
from fastapi.testclient import TestClient

from server.app import create_app
from server import economy as E

W = E.EVENT_WINDOW


def test_rotation_and_windows():
    ids = [E.timed_event(k * W + 5)['id'] for k in range(8)]
    assert ids[:4] == ids[4:] and len(set(ids[:4])) == 4  # cykl 4 eventów
    e = E.timed_event(10 * W + 123)
    assert e['start'] == 10 * W and e['end'] == 11 * W
    assert e['next']['id'] == E.timed_event(11 * W)['id']


def test_ev_mult_only_for_active_effect():
    t = next(k * W for k in range(4) if E.timed_event(k * W)['effect'] == 'bus_free')
    assert E.ev_mult(t, 'bus_free') == 0.0                      # 2.4e: mnożnik ceny biletu
    assert E.ev_mult(t, 'contract_cash') == 1.0 and E.ev_mult(t + W, 'bus_free') == 1.0


@pytest.fixture
def env(tmp_path):
    clock = [1780000000000]
    app = create_app(tmp_path / 'game.sqlite3', lambda: clock[0], tmp_path / 'setup.txt')
    return app, clock


def test_packet_shows_bus_free(env):
    app, clock = env
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': 'tev' + uuid.uuid4().hex[:5], 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/2/character', json={'nickname': 'Eventowy', 'accept_test_reset': True}).status_code == 200
    base = (clock[0] // W) * W
    clock[0] = next(base + k * W + 1000 for k in range(4) if E.timed_event(base + k * W)['effect'] == 'bus_free')
    pk = c.get('/api/worlds/2/state').json()
    assert pk['timedEvent']['id'] == 'bus_free' and pk['timedEvent']['end'] > clock[0]
