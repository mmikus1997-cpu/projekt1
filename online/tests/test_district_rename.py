"""2.1b GDD v3.1: dzielnice 1 → Nadmorskie, 2 → Przemysłowe; migracja danych organizacji przy starcie."""
import sqlite3
from fastapi.testclient import TestClient
from server.app import create_app
from server import economy as E, travel as T

def test_names():
    d=dict(T.DISTRICTS)
    assert d[1]=='Nadmorskie' and d[2]=='Przemysłowe'
    assert 'Przemysłowe' in E.DISTRICTS and 'Zakłady Miejskie' not in E.DISTRICTS

def test_player_invest_key_migrates():
    assert E.INVEST_RENAME['Zakłady Miejskie']=='Przemysłowe'
    assert E.INVEST_RENAME['Strefa Przemysłowa']=='Przemysłowe'

def test_org_data_migrates_on_start(tmp_path):
    db=tmp_path/'m.sqlite3'
    create_app(db,lambda:1780000000000,tmp_path/'s.txt')
    with sqlite3.connect(db) as c:
        c.execute('PRAGMA foreign_keys=OFF')
        for i in (1,2):
            c.execute("INSERT INTO organizations(id,world_id,name,tag,description,leader_id,created_at) VALUES(?,2,?,?,'',1,0)",(i,f'Org{i}',f'O{i}'))
        # org 1 ma wpisy pod starą i nową nazwą (scalenie), org 2 tylko pod starą
        c.executemany('INSERT INTO org_investments(org_id,district,total) VALUES(?,?,?)',
            [(1,'Zakłady Miejskie',3000),(1,'Przemysłowe',2000),(2,'Strefa Przemysłowa',1000)])
        c.execute("INSERT INTO territory_state(world_id,district,org_id,since) VALUES(2,'Zakłady Miejskie',1,0)")
        c.execute("INSERT INTO territory_log(world_id,district,org_id,at) VALUES(2,'Zakłady Miejskie',1,0)")
    TestClient(create_app(db,lambda:1780000000000,tmp_path/'s.txt'))  # ponowny start = migracja
    TestClient(create_app(db,lambda:1780000000000,tmp_path/'s.txt'))  # idempotentność
    with sqlite3.connect(db) as c:
        inv=dict(((o,d),t) for o,d,t in c.execute('SELECT org_id,district,total FROM org_investments'))
        assert inv=={(1,'Przemysłowe'):5000,(2,'Przemysłowe'):1000}
        assert [r[0] for r in c.execute('SELECT district FROM territory_state')]==['Przemysłowe']
        assert not c.execute("SELECT 1 FROM territory_log WHERE district='Zakłady Miejskie'").fetchone()
