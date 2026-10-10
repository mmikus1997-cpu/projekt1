"""QA helper: wstawia odznakę (character_titles) dla nicku — używa TEST_DB."""
import json
import os
import sqlite3
import sys

db = sqlite3.connect(os.environ['TEST_DB'])
cid = db.execute('SELECT id FROM characters WHERE nickname=?', (sys.argv[1],)).fetchone()[0]
db.execute('INSERT INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,0,?,?,?)', (cid, 'qa_seed', sys.argv[2], 1780000000000))
db.commit(); db.close()
print('seeded', sys.argv[2])
