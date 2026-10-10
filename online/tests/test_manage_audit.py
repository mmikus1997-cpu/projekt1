"""GDD v3.1 1.7: komendy operatora manage.py zostawiają pełny ślad w tabeli audit (na kopii bazy)."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from server.app import create_app

ROOT = Path(__file__).resolve().parents[1]


def run(db, *a):
    return subprocess.run([sys.executable, str(ROOT / 'manage.py'), '--db', str(db), *a], capture_output=True, text=True, cwd=ROOT)


def seed(tmp_path):
    db = tmp_path / 'ops.sqlite3'
    app = create_app(db, lambda: 1780000000000, tmp_path / 'setup.txt')
    c = TestClient(app)
    r = c.post('/api/auth/register', json={'username': 'operowany', 'password': 'test-password-long-123', 'consent': True})
    c.headers['X-CSRF-Token'] = r.json()['csrf']
    assert c.post('/api/worlds/2/character', json={'nickname': 'Opek', 'accept_test_reset': True}).status_code == 200
    return db


def last(db, event):
    with sqlite3.connect(db) as d:
        row = d.execute('SELECT details FROM audit WHERE event=? ORDER BY id DESC LIMIT 1', (event,)).fetchone()
    assert row, event
    return json.loads(row[0])


def test_grant_cash_audit_has_operator_and_before_after(tmp_path):
    db = seed(tmp_path)
    r = run(db, 'grant-cash', 'operowany', '1000'); assert r.returncode == 0, r.stderr
    d = last(db, 'operator.grant-cash')
    assert d['operator']['os_user'] and d['operator']['host'] and d['operator']['command'] == 'grant-cash'
    ch = d['characters'][0]
    assert ch['cash_after'] - ch['cash_before'] == 1000


def test_grant_admin_audit_has_operator(tmp_path):
    db = seed(tmp_path)
    assert run(db, 'grant-admin', 'operowany').returncode == 0
    assert last(db, 'operator.grant-admin')['operator']['command'] == 'grant-admin'


def test_backup_is_audited(tmp_path):
    db = seed(tmp_path); out = tmp_path / 'kopia.sqlite3'
    r = run(db, 'backup', '--output', str(out)); assert r.returncode == 0, r.stderr
    assert last(db, 'operator.backup')['output'] == str(out)


def test_verify_backup_does_not_modify_file(tmp_path):
    db = seed(tmp_path); out = tmp_path / 'kopia.sqlite3'
    assert run(db, 'backup', '--output', str(out)).returncode == 0
    h = hashlib.sha256(out.read_bytes()).hexdigest()
    assert run(out, 'verify-backup').returncode == 0
    assert hashlib.sha256(out.read_bytes()).hexdigest() == h
