"""0.7 community and account tools. All mutations remain server-authoritative."""
import json
import os
import re
import secrets
import unicodedata
from pathlib import Path
from types import SimpleNamespace
from fastapi import Depends, Request
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal
from argon2.exceptions import VerificationError
from .backups import Backups
from . import combat
from . import economy as E
from . import chronicle

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Empty(Strict):pass
class Appeal(Strict):text:str=Field(min_length=10,max_length=300)
class EvolveIn(Strict):evolution_code:str=Field(min_length=3,max_length=24)
class Apply(Strict):
 org_id:int
 text:str=Field(min_length=10,max_length=200)
class Fund(Strict):amount:int=Field(ge=50,le=5000)
class InvestOrg(Strict):
 district:str=Field(min_length=2,max_length=40)
 amount:int=Field(ge=100,le=5000)
class AllyBuild(Strict):building:str=Field(max_length=20)
class OrgAnnounce(Strict):text:str=Field(min_length=3,max_length=200)
class OrgContract(Strict):
 kind:str=Field(pattern='^(prestige|fund)$')
 district:str=Field(default='',max_length=40)
 target:int=Field(ge=100,le=50000)
 hours:int=Field(ge=24,le=168)
class Role(Strict):
 target_id:int
 role:Literal['member','officer']
class AppealResolve(Strict):
 uphold:bool
 note:str=Field(default='',max_length=200)
class Organization(Strict):
 name:str=Field(min_length=3,max_length=32)
 tag:str=Field(min_length=2,max_length=5)
 description:str=Field(default='',max_length=180)
class Target(Strict):target_id:int
class Message(Strict):
 text:str=Field(min_length=1,max_length=300)
 client_id:str=Field(min_length=16,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
class Report(Strict):
 message_id:int
 reason:str=Field(min_length=3,max_length=300)
class Resolve(Strict):
 action:Literal['dismiss','hide','hide_mute']
 note:str=Field(default='',max_length=300)
class PasswordChange(Strict):
 current_password:str=Field(min_length=1,max_length=128,repr=False)
 new_password:str=Field(min_length=1,max_length=128,repr=False)
class Revoke(Strict):
 password:str=Field(min_length=1,max_length=128,repr=False)
 session_id:str|None=Field(default=None,max_length=100)
class Unblock(Strict):account_id:int
class EventsRead(Strict):
 ids:list[int]=Field(default_factory=list,max_length=100)
 all:bool=False
SCHEMA='''
CREATE TABLE IF NOT EXISTS organizations(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id),name TEXT NOT NULL,tag TEXT NOT NULL COLLATE NOCASE,description TEXT NOT NULL,leader_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE RESTRICT,created_at INTEGER NOT NULL,UNIQUE(world_id,tag));
CREATE TABLE IF NOT EXISTS org_members(character_id INTEGER PRIMARY KEY REFERENCES characters(id) ON DELETE CASCADE,org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,joined_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS org_invites(id INTEGER PRIMARY KEY AUTOINCREMENT,org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,target_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,status TEXT NOT NULL DEFAULT 'pending',created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS org_applications(id INTEGER PRIMARY KEY AUTOINCREMENT,org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,text TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS org_investments(org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,district TEXT NOT NULL,total INTEGER NOT NULL,PRIMARY KEY(org_id,district));
CREATE TABLE IF NOT EXISTS territory_state(world_id INTEGER NOT NULL REFERENCES worlds(id),district TEXT NOT NULL,org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,since INTEGER NOT NULL,PRIMARY KEY(world_id,district));
CREATE TABLE IF NOT EXISTS territory_log(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id),district TEXT NOT NULL,org_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,prev_org_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS territory_log_world ON territory_log(world_id,id DESC);
CREATE TABLE IF NOT EXISTS game_events(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,kind TEXT NOT NULL,payload TEXT NOT NULL DEFAULT '{}',created_at INTEGER NOT NULL,read_at INTEGER);
CREATE INDEX IF NOT EXISTS game_events_char ON game_events(character_id,id DESC);
CREATE TABLE IF NOT EXISTS season_archive(season INTEGER NOT NULL,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,payload TEXT NOT NULL,created_at INTEGER NOT NULL,PRIMARY KEY(season,world_id));
CREATE TABLE IF NOT EXISTS org_contracts(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,kind TEXT NOT NULL,district TEXT,target INTEGER NOT NULL,base INTEGER NOT NULL,deadline INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'active',created_by INTEGER NOT NULL REFERENCES characters(id),created_at INTEGER NOT NULL,done_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS org_contract_active ON org_contracts(org_id) WHERE status='active';
CREATE TABLE IF NOT EXISTS character_titles(id INTEGER PRIMARY KEY AUTOINCREMENT,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,season INTEGER NOT NULL,code TEXT NOT NULL,label TEXT NOT NULL,granted_at INTEGER NOT NULL,UNIQUE(character_id,code,season));
CREATE TABLE IF NOT EXISTS social_blocks(account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,target_account INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,display_name TEXT NOT NULL,created_at INTEGER NOT NULL,PRIMARY KEY(account_id,target_account));
CREATE TABLE IF NOT EXISTS chat_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id),org_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,author_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,body TEXT NOT NULL,client_id TEXT NOT NULL,created_at INTEGER NOT NULL,hidden INTEGER NOT NULL DEFAULT 0,UNIQUE(author_id,client_id));
CREATE TABLE IF NOT EXISTS chat_reports(id INTEGER PRIMARY KEY AUTOINCREMENT,message_id INTEGER REFERENCES chat_messages(id) ON DELETE SET NULL,reporter_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'open',note TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,resolved_at INTEGER,UNIQUE(message_id,reporter_id));
CREATE TABLE IF NOT EXISTS chat_mutes(account_id INTEGER PRIMARY KEY REFERENCES accounts(id) ON DELETE CASCADE,until_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS chat_channel ON chat_messages(world_id,org_id,id DESC);
CREATE INDEX IF NOT EXISTS org_invites_target ON org_invites(target_id,status);
CREATE TABLE IF NOT EXISTS dm_messages(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,sender_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,recipient_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,body TEXT NOT NULL,created_at INTEGER NOT NULL,read_at INTEGER);
CREATE INDEX IF NOT EXISTS dm_box ON dm_messages(world_id,sender_id,recipient_id,id DESC);
CREATE INDEX IF NOT EXISTS dm_inbox ON dm_messages(world_id,recipient_id,id DESC);
'''

# 0.12/0.34: 28-dniowe sezony rankingowe — wspólne dla rankingów i Er świata (city_events.era_of).
SEASON_ANCHOR=1767571200000;SEASON_LEN=28*86400000
def season_of(t):return max(1,(t-SEASON_ANCHOR)//SEASON_LEN+1)
# 5.4 GDD v3.1: ranking XP jest całoroczny — archiwa/tytuły XP tylko dla starych sezonów 28-dniowych 1..9;
# od października 2026 (sezon 10) sezony są miesięczne i dotyczą Elo (server/seasons.py).
XP_SEASON_LAST=9

class DmSend(Strict):
 text:str=Field(min_length=1,max_length=500)


FED_SCHEMA='''
CREATE TABLE IF NOT EXISTS federations(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id),name TEXT NOT NULL,leader_org_id INTEGER NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS federation_members(org_id INTEGER PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,fed_id INTEGER NOT NULL REFERENCES federations(id) ON DELETE CASCADE,joined_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS federation_invites(fed_id INTEGER NOT NULL REFERENCES federations(id) ON DELETE CASCADE,org_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,created_at INTEGER NOT NULL,PRIMARY KEY(fed_id,org_id));
'''
FED_MAX=3  # 8.3: maks. 3 sojusze w federacji (decyzja usera: prosta federacja)
class FedCreate(Strict):name:str=Field(min_length=3,max_length=40)
class FedInvite(Strict):tag:str=Field(min_length=2,max_length=8)

def install(app,d):
 db,now,fail=d.db,d.now,d.fail
 chron=d.chronicle['record']
 c=db.connect()
 try:
  c.executescript(SCHEMA)
  c.executescript(FED_SCHEMA)  # 8.3 GDD v3.1: federacje (migracja addytywna)
  if 'fed_id' not in {r['name'] for r in c.execute('PRAGMA table_info(territory_state)')}:c.execute('ALTER TABLE territory_state ADD COLUMN fed_id INTEGER')
  columns={r['name'] for r in c.execute('PRAGMA table_info(sessions)')}
  for name,definition in [('sid','TEXT'),('created_at','INTEGER NOT NULL DEFAULT 0'),('last_seen','INTEGER NOT NULL DEFAULT 0')]:
   if name not in columns:c.execute('ALTER TABLE sessions ADD COLUMN '+name+' '+definition)
  # 0.39: read_at dorasta do istniejących tabel dm_messages additively.
  dm_cols={r['name'] for r in c.execute('PRAGMA table_info(dm_messages)')} if c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='dm_messages'").fetchone() else set()
  if dm_cols and 'read_at' not in dm_cols:c.execute('ALTER TABLE dm_messages ADD COLUMN read_at INTEGER')
  # 0.10: org ranks, fund and announcements join existing databases additively.
  member_cols={r['name'] for r in c.execute('PRAGMA table_info(org_members)')}
  if 'role' not in member_cols:c.execute("ALTER TABLE org_members ADD COLUMN role TEXT NOT NULL DEFAULT 'member'")
  org_cols={r['name'] for r in c.execute('PRAGMA table_info(organizations)')}
  if 'buildings' not in org_cols:c.execute("ALTER TABLE organizations ADD COLUMN buildings TEXT NOT NULL DEFAULT '{}'")
  for name in ('fund','announcement'):
   if name not in org_cols:c.execute('ALTER TABLE organizations ADD COLUMN '+name+(' INTEGER NOT NULL DEFAULT 0' if name=='fund' else " TEXT NOT NULL DEFAULT ''"))
  # 2.1b GDD v3.1: migracja nazw dzielnic w danych organizacji (idempotentna).
  for old,new in E.INVEST_RENAME.items():
   # inwestycje: scal kwoty pod nową nazwą (PK org_id+district), potem usuń stare wiersze
   for r in c.execute('SELECT org_id,total FROM org_investments WHERE district=?',(old,)).fetchall():
    if not c.execute('UPDATE org_investments SET total=total+? WHERE org_id=? AND district=?',(r['total'],r['org_id'],new)).rowcount:
     c.execute('INSERT INTO org_investments(org_id,district,total) VALUES(?,?,?)',(r['org_id'],new,r['total']))
   c.execute('DELETE FROM org_investments WHERE district=?',(old,))
   # terytorium: przy kolizji PK zostaje wpis pod nową nazwą
   c.execute('UPDATE OR IGNORE territory_state SET district=? WHERE district=?',(new,old))
   c.execute('DELETE FROM territory_state WHERE district=?',(old,))
   c.execute('UPDATE territory_log SET district=? WHERE district=?',(new,old))
   c.execute('UPDATE org_contracts SET district=? WHERE district=?',(new,old))
  c.execute("UPDATE org_members SET role='leader' WHERE character_id IN (SELECT leader_id FROM organizations)")
  for r in c.execute('SELECT token_hash FROM sessions WHERE sid IS NULL').fetchall():c.execute('UPDATE sessions SET sid=? WHERE token_hash=?',(secrets.token_hex(12),r['token_hash']))
  c.execute('CREATE UNIQUE INDEX IF NOT EXISTS session_public_id ON sessions(sid)');c.commit()
 finally:c.close()
 backups=Backups(db.path,os.getenv('CITY_BACKUP_DIR',str(Path(db.path).parent/'backups')));backups.attach(app)
 def text(value,minimum=1):
  value=''.join(ch for ch in value if unicodedata.category(ch) not in ('Cc','Cf') or ch=='\n').strip()
  if len(value)<minimum:fail(422,'Wpisz treść wiadomości.')
  if re.search(r'https?://|www\.|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}|\b(?:[\w-]+\.)+[a-zA-Z]{2,}\b',value,re.I):fail(422,'Linki i adresy e-mail są wyłączone w czacie testowym.')
  return value
 def own(c,u,wid):d.world(c,wid,True);return d.own(c,u['id'],wid)
 def org_for(c,cid):
  row=c.execute('SELECT o.* FROM organizations o JOIN org_members m ON m.org_id=o.id WHERE m.character_id=?',(cid,)).fetchone()
  return dict(row) if row else None
 # 0.11 territory influence: prestige sums decide the holder of a district; takeover is logged. Purely reputational.
 def claim(c,wid,district,uid):
  # 8.3 GDD v3.1: kontrola tylko przy >55% udziałów; federacja sumuje udziały sojuszy składowych.
  rows=[dict(r) for r in c.execute('SELECT o.id,o.tag,o.name,sum(i.total) total,fm.fed_id FROM org_investments i JOIN organizations o ON o.id=i.org_id LEFT JOIN federation_members fm ON fm.org_id=o.id WHERE i.district=? AND o.world_id=? GROUP BY o.id ORDER BY total DESC,o.id',(district,wid))]
  cur=c.execute('SELECT org_id,fed_id FROM territory_state WHERE world_id=? AND district=?',(wid,district)).fetchone()
  allsum=sum(r['total'] for r in rows);blocs={}
  for r in rows:blocs.setdefault(('f',r['fed_id']) if r['fed_id'] else ('o',r['id']),[]).append(r)
  best=max(blocs.values(),key=lambda b:(sum(x['total'] for x in b),-b[0]['id'])) if blocs else None
  if not best or sum(x['total'] for x in best)<=E.CONTROL_SHARE*allsum:
   if cur:
    c.execute('DELETE FROM territory_state WHERE world_id=? AND district=?',(wid,district))
    c.execute('INSERT INTO territory_log(world_id,district,org_id,prev_org_id,at) VALUES(?,?,?,?,?)',(wid,district,None,cur['org_id'],now()))
   return None
  top=dict(best[0],share=round(sum(x['total'] for x in best)/allsum,4),blocTotal=sum(x['total'] for x in best))
  if cur and cur['org_id']==top['id'] and (cur['fed_id'] or None)==(top['fed_id'] or None):return dict(top,changed=False,prev=None)
  c.execute('INSERT INTO territory_state(world_id,district,org_id,since,fed_id) VALUES(?,?,?,?,?) ON CONFLICT(world_id,district) DO UPDATE SET org_id=excluded.org_id,since=excluded.since,fed_id=excluded.fed_id',(wid,district,top['id'],now(),top['fed_id']))
  c.execute('INSERT INTO territory_log(world_id,district,org_id,prev_org_id,at) VALUES(?,?,?,?,?)',(wid,district,top['id'],cur['org_id'] if cur else None,now()))
  d.audit(c,uid,'territory.claim',dict(district=district,org=top['id'],prev=cur['org_id'] if cur else None))
  return dict(top,changed=True,prev=cur['org_id'] if cur else None)
 def controls(c,cid,district):
  """8.3: czy sojusz postaci (albo jego federacja) kontroluje dzielnicę (>55%)."""
  m=c.execute('SELECT m.org_id,fm.fed_id FROM org_members m LEFT JOIN federation_members fm ON fm.org_id=m.org_id WHERE m.character_id=?',(cid,)).fetchone()
  if not m:return False
  w=c.execute('SELECT world_id FROM characters WHERE id=?',(cid,)).fetchone()
  t=c.execute('SELECT org_id,fed_id FROM territory_state WHERE world_id=? AND district=?',(w['world_id'],district)).fetchone() if w else None
  return bool(t and (t['org_id']==m['org_id'] or (m['fed_id'] and t['fed_id']==m['fed_id'])))
 E.TERRITORY_HOOK[0]=controls
 def reclaim_all(c,wid,uid):
  for name in E.DISTRICTS:claim(c,wid,name,uid)
 def fed_of(c,org_id):
  r=c.execute('SELECT f.* FROM federations f JOIN federation_members m ON m.fed_id=f.id WHERE m.org_id=?',(org_id,)).fetchone()
  return dict(r) if r else None
 def leader_org(c,ch):
  org=org_for(c,ch['id'])
  if not org or org['leader_id']!=ch['id']:fail(403,'Federacjami zarządza lider sojuszu.')
  return org
 def fed_view(c,org):
  f=fed_of(c,org['id']) if org else None
  members=[dict(r) for r in c.execute('SELECT o.id,o.tag,o.name FROM federation_members m JOIN organizations o ON o.id=m.org_id WHERE m.fed_id=? ORDER BY m.joined_at',(f['id'],))] if f else []
  invites=[dict(r) for r in c.execute('SELECT f.id,f.name FROM federation_invites i JOIN federations f ON f.id=i.fed_id WHERE i.org_id=?',(org['id'],))] if org else []
  return dict(federation=dict(f,members=members) if f else None,invites=invites,maxMembers=FED_MAX,controlShare=E.CONTROL_SHARE)
 @app.get('/api/worlds/{wid}/federations')
 def fed_get(wid:int,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);return fed_view(c,org_for(c,ch['id']))
 @app.post('/api/worlds/{wid}/federations')
 def fed_create(wid:int,data:FedCreate,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=leader_org(c,ch)
   if fed_of(c,org['id']):fail(409,'Twój sojusz jest już w federacji.')
   fid=c.execute('INSERT INTO federations(world_id,name,leader_org_id,created_at) VALUES(?,?,?,?)',(wid,data.name.strip(),org['id'],now())).lastrowid
   c.execute('INSERT INTO federation_members(org_id,fed_id,joined_at) VALUES(?,?,?)',(org['id'],fid,now()))
   d.audit(c,u['id'],'federation.create',dict(fed=fid,org=org['id']));reclaim_all(c,wid,u['id'])
   return fed_view(c,org)
 @app.post('/api/worlds/{wid}/federations/invite')
 def fed_invite(wid:int,data:FedInvite,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=leader_org(c,ch);f=fed_of(c,org['id'])
   if not f or f['leader_org_id']!=org['id']:fail(403,'Zaprasza lider federacji.')
   t=c.execute('SELECT * FROM organizations WHERE world_id=? AND tag=?',(wid,data.tag)).fetchone()
   if not t:fail(404,'Nie ma sojuszu o takim tagu.')
   if fed_of(c,t['id']):fail(409,'Ten sojusz jest już w federacji.')
   c.execute('INSERT OR IGNORE INTO federation_invites(fed_id,org_id,created_at) VALUES(?,?,?)',(f['id'],t['id'],now()))
   return fed_view(c,org)
 @app.post('/api/worlds/{wid}/federations/{fid}/accept')
 def fed_accept(wid:int,fid:int,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=leader_org(c,ch)
   if not c.execute('SELECT 1 FROM federation_invites WHERE fed_id=? AND org_id=?',(fid,org['id'])).fetchone():fail(404,'Brak zaproszenia do tej federacji.')
   if fed_of(c,org['id']):fail(409,'Twój sojusz jest już w federacji.')
   if c.execute('SELECT count(*) FROM federation_members WHERE fed_id=?',(fid,)).fetchone()[0]>=FED_MAX:fail(409,'Federacja ma już '+str(FED_MAX)+' sojusze.')
   c.execute('DELETE FROM federation_invites WHERE org_id=?',(org['id'],))
   c.execute('INSERT INTO federation_members(org_id,fed_id,joined_at) VALUES(?,?,?)',(org['id'],fid,now()))
   d.audit(c,u['id'],'federation.join',dict(fed=fid,org=org['id']));reclaim_all(c,wid,u['id'])
   return fed_view(c,org)
 @app.post('/api/worlds/{wid}/federations/leave')
 def fed_leave(wid:int,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=leader_org(c,ch);f=fed_of(c,org['id'])
   if not f:fail(409,'Twój sojusz nie jest w federacji.')
   if f['leader_org_id']==org['id']:c.execute('DELETE FROM federations WHERE id=?',(f['id'],));c.execute('DELETE FROM federation_members WHERE fed_id=?',(f['id'],))  # lider wychodzi → rozwiązanie
   else:c.execute('DELETE FROM federation_members WHERE org_id=?',(org['id'],))
   d.audit(c,u['id'],'federation.leave',dict(fed=f['id'],org=org['id']));reclaim_all(c,wid,u['id'])
   return fed_view(c,org)
 def influence_rows(c,wid,org):
  rows=c.execute('SELECT i.district,o.id org_id,o.name,o.tag,sum(i.total) total FROM org_investments i JOIN organizations o ON o.id=i.org_id WHERE o.world_id=? GROUP BY i.district,o.id ORDER BY i.district,total DESC,o.id',(wid,)).fetchall()
  per={}
  for r in rows:per.setdefault(r['district'],[]).append(dict(r))
  holders={r['district']:r['since'] for r in c.execute('SELECT t.district,t.since FROM territory_state t WHERE t.world_id=?',(wid,))}
  districts=[]
  for name in E.DISTRICTS:
   arr=per.get(name,[]);mine=next((e for e in arr if org and e['org_id']==org['id']),None)
   districts.append(dict(district=name,total=sum(e['total'] for e in arr),leader=arr[0] if arr else None,second=arr[1] if len(arr)>1 else None,myTotal=mine['total'] if mine else 0,myRank=(arr.index(mine)+1) if mine else None,holderSince=holders.get(name)))
  log=[dict(r) for r in c.execute("SELECT l.district,l.at,coalesce(o.tag,'?') tag,coalesce(o.name,'(rozwiązana)') name,coalesce(p.tag,'') prev_tag FROM territory_log l LEFT JOIN organizations o ON o.id=l.org_id LEFT JOIN organizations p ON p.id=l.prev_org_id WHERE l.world_id=? ORDER BY l.id DESC LIMIT 8",(wid,))]
  return districts,log
 # 0.12 in-game notifications: per-character event feed (max 100 kept), and 28-day ranking seasons.
 def emit(c,wid,cids,kind,payload):
  for cid in set(cids):
   c.execute('INSERT INTO game_events(world_id,character_id,kind,payload,created_at) VALUES(?,?,?,?,?)',(wid,cid,kind,json.dumps(payload,ensure_ascii=False,separators=(',',':')),now()))
   c.execute('DELETE FROM game_events WHERE character_id=? AND id NOT IN (SELECT id FROM game_events WHERE character_id=? ORDER BY id DESC LIMIT 100)',(cid,cid))
 def org_contract_current(c,row):
  # live progress: current prestige in the district or current fund, minus the baseline
  if row['kind']=='fund':
   cur=c.execute('SELECT fund FROM organizations WHERE id=?',(row['org_id'],)).fetchone()['fund']
  else:
   cur=c.execute('SELECT coalesce(sum(total),0) FROM org_investments WHERE org_id=? AND district=?',(row['org_id'],row['district'])).fetchone()[0]
  return max(0,cur-row['base'])
 def check_org_contract(c,wid,org,uid):
  row=c.execute("SELECT * FROM org_contracts WHERE org_id=? AND status='active'",(org['id'],)).fetchone()
  if not row:return None
  if org_contract_current(c,row)>=row['target']:
   c.execute("UPDATE org_contracts SET status='done',done_at=? WHERE id=?",(now(),row['id']))
   emit(c,wid,[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(org['id'],))],'org.contract_done',{'org':org['name'],'tag':org['tag'],'target':row['target'],'kind':row['kind'],'district':row['district'] or ''})
   chronicle.org_done(chron,c,wid,org['name'],org['tag'],row['kind'],row['district'] or '',row['target'])
   d.audit(c,uid,'org.contract_done',dict(org=org['id'],contract=row['id']))
   return dict(done=True)
  return None
 def expire_org_contracts(c,wid):
  for row in c.execute("SELECT oc.*,o.name oname,o.tag otag FROM org_contracts oc JOIN organizations o ON o.id=oc.org_id WHERE oc.world_id=? AND oc.status='active' AND oc.deadline<=?",(wid,now())).fetchall():
   c.execute("UPDATE org_contracts SET status='missed' WHERE id=?",(row['id'],))
   emit(c,wid,[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(row['org_id'],))],'org.contract_missed',{'org':row['oname'],'tag':row['otag']})
   chronicle.org_missed(chron,c,wid,row['oname'],row['otag'],row['kind'],row['district'] or '')
 def org_officer_ids(c,org):
  return [r['character_id'] for r in c.execute("SELECT character_id FROM org_members WHERE org_id=? AND (character_id=? OR role='officer')",(org['id'],org['leader_id']))]
 def ensure_seasons(c,cur):
  for w in c.execute('SELECT id,name FROM worlds ORDER BY id').fetchall():
   done={r['season'] for r in c.execute('SELECT season FROM season_archive WHERE world_id=?',(w['id'],))}
   for sn in range(1,min(cur,XP_SEASON_LAST+1)):  # 5.4: XP bez nowych sezonów
    if sn in done:continue
    top=c.execute('SELECT ch.id,ch.nickname,json_extract(ch.state_json,"$.xp") xp FROM characters ch JOIN accounts a ON a.id=ch.account_id WHERE ch.world_id=? AND a.banned=0 ORDER BY xp DESC,ch.id LIMIT 10',(w['id'],)).fetchall()
    c.execute('INSERT INTO season_archive(season,world_id,payload,created_at) VALUES(?,?,?,?)',(sn,w['id'],json.dumps([dict(cid=r['id'],nickname=r['nickname'],xp=r['xp'] or 0,level=E.level(r['xp'] or 0)) for r in top],ensure_ascii=False,separators=(',',':')),now()))
    chars=[r['id'] for r in c.execute('SELECT id FROM characters WHERE world_id=?',(w['id'],)).fetchall()]
    place={r['id']:i+1 for i,r in enumerate(top)}
    for cid in chars:emit(c,w['id'],[cid],'season.end',{'season':sn,'world':w['name'],'place':place.get(cid)})
  # 0.13 reputation titles: granted once per finished season, purely cosmetic (no stats, no cash).
  titled={r['season'] for r in c.execute('SELECT DISTINCT season FROM character_titles')}
  for sn in range(1,min(cur,XP_SEASON_LAST+1)):  # 5.4: brak nowych tytułów XP
   if sn in titled or not c.execute('SELECT 1 FROM season_archive WHERE season=?',(sn,)).fetchone():continue
   entries=[]
   for r in c.execute('SELECT payload,world_id FROM season_archive WHERE season=?',(sn,)).fetchall():
    for e in json.loads(r['payload']):entries.append(dict(e,wid=r['world_id']))
   if not entries:continue
   entries.sort(key=lambda e:(-e['xp'],e.get('cid',0)))
   grants=[(entries[0],'champion','Mistrz Sezonu '+str(sn))]
   if len(entries)>1:grants.append((entries[1],'elite','Elita Sezonu '+str(sn)))
   if len(entries)>2:grants.append((entries[2],'elite','Elita Sezonu '+str(sn)))
   world_name={r['id']:r['name'] for r in c.execute('SELECT id,name FROM worlds').fetchall()}
   for wid in {e['wid'] for e in entries}:
    best=next(e for e in entries if e['wid']==wid)
    grants.append((best,'world_leader','Lider Świata '+world_name.get(wid,'?')))
   for e,code,label in grants:
    char=c.execute('SELECT id FROM characters WHERE world_id=? AND nickname=?',(e['wid'],e['nickname'])).fetchone()
    if not char:continue
    c.execute('INSERT INTO character_titles(character_id,season,code,label,granted_at) VALUES(?,?,?,?,?)',(char['id'],sn,code,label,now()))
    emit(c,e['wid'],[char['id']],'season.title',{'season':sn,'label':label})
 def blocked(c,a,b):return bool(c.execute('SELECT 1 FROM social_blocks WHERE (account_id=? AND target_account=?) OR (account_id=? AND target_account=?)',(a,b,b,a)).fetchone())
 def target(c,wid,cid):
  row=c.execute('SELECT c.* FROM characters c JOIN accounts a ON a.id=c.account_id WHERE c.id=? AND c.world_id=? AND a.banned=0',(cid,wid)).fetchone()
  if not row:fail(404,'Postać nie jest dostępna na tym świecie.')
  return dict(row)
 def leader(c,ch):
  org=org_for(c,ch['id'])
  if not org or org['leader_id']!=ch['id']:fail(403,'Tylko lider może wykonać tę operację.')
  return org
 def rank(c,ch,org):
  if org['leader_id']==ch['id']:return 'leader'
  row=c.execute('SELECT role FROM org_members WHERE character_id=?',(ch['id'],)).fetchone()
  return row['role'] if row else 'member'
 def officer(c,ch):
  org=org_for(c,ch['id'])
  if not org or rank(c,ch,org) not in ('leader','officer'):fail(403,'Wymagana rola lidera albo oficera.')
  return org
 def channel(c,ch,kind):
  if kind=='world':return None
  if kind!='organization':fail(404,'Nieznany kanał.')
  org=org_for(c,ch['id'])
  if not org:fail(403,'Dołącz do organizacji, aby korzystać z jej czatu.')
  return org['id']
 def check_password(u,value):
  try:valid=d.PH.verify(u['password_hash'],value)
  except VerificationError:valid=False
  if not valid:fail(403,'Nieprawidłowe obecne hasło.')

 @app.get('/api/worlds/{wid}/community')
 def community(wid:int,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=org_for(c,ch['id'])
   if org:
    try:org['buildings']=json.loads(org.get('buildings') or '{}')
    except Exception:org['buildings']={}
   if org:org['prestige']=c.execute('SELECT coalesce(sum(total),0) FROM org_investments WHERE org_id=?',(org['id'],)).fetchone()[0]
   c.execute("UPDATE org_invites SET status='expired' WHERE status='pending' AND expires_at<=?",(now(),))
   organizations=[dict(r) for r in c.execute('SELECT o.id,o.name,o.tag,o.description,o.fund,l.nickname leader_name,(SELECT count(*) FROM org_members m WHERE m.org_id=o.id) members,coalesce((SELECT sum(i.total) FROM org_investments i WHERE i.org_id=o.id),0) prestige FROM organizations o JOIN characters l ON l.id=o.leader_id WHERE o.world_id=? ORDER BY o.id LIMIT 200',(wid,))]
   members=[];applications=[]
   if org:members=[dict(id=r['id'],nickname=r['nickname'],leader=r['id']==org['leader_id'],role='leader' if r['id']==org['leader_id'] else r['role']) for r in c.execute('SELECT c.id,c.nickname,m.role FROM characters c JOIN org_members m ON m.character_id=c.id WHERE m.org_id=? ORDER BY c.id',(org['id'],))]
   invitations=[]
   for r in c.execute("SELECT i.id,i.expires_at,o.name,o.tag,l.account_id FROM org_invites i JOIN organizations o ON o.id=i.org_id JOIN characters l ON l.id=o.leader_id WHERE i.target_id=? AND i.status='pending'",(ch['id'],)):
    if not blocked(c,u['id'],r['account_id']):invitations.append({k:r[k] for k in ('id','expires_at','name','tag')})
   if org and rank(c,ch,org) in ('leader','officer'):
    applications=[dict(r) for r in c.execute("SELECT a.id,a.text,a.created_at,c.nickname FROM org_applications a JOIN characters c ON c.id=a.character_id WHERE a.org_id=? AND a.status='pending' AND a.expires_at>? ORDER BY a.id LIMIT 30",(org['id'],now()))]
   mine=c.execute("SELECT org_id FROM org_applications WHERE character_id=? AND status='pending' AND expires_at>? ORDER BY id DESC LIMIT 1",(ch['id'],now())).fetchone()
   ranking=[dict(r) for r in c.execute('SELECT o.id,o.name,o.tag,coalesce(sum(i.total),0) prestige,(SELECT count(*) FROM org_members m WHERE m.org_id=o.id) members FROM organizations o LEFT JOIN org_investments i ON i.org_id=o.id WHERE o.world_id=? GROUP BY o.id ORDER BY prestige DESC,o.id LIMIT 10',(wid,))]
   held_map={}
   for r in c.execute('SELECT t.district,t.org_id FROM territory_state t JOIN organizations o ON o.id=t.org_id WHERE o.world_id=?',(wid,)).fetchall():held_map.setdefault(r['org_id'],[]).append(r['district'])
   for o in organizations:o['held']=held_map.get(o['id'],[])
   districts,log=influence_rows(c,wid,org)
   expire_org_contracts(c,wid)
   events=[dict(id=r['id'],kind=r['kind'],payload=json.loads(r['payload']),created_at=r['created_at'],read=r['read_at'] is not None) for r in c.execute('SELECT * FROM game_events WHERE character_id=? ORDER BY id DESC LIMIT 30',(ch['id'],))]
   eventsUnread=c.execute('SELECT count(*) FROM game_events WHERE character_id=? AND read_at IS NULL',(ch['id'],)).fetchone()[0]
   orgContract=None
   if org:
    row=c.execute("SELECT * FROM org_contracts WHERE org_id=? AND status='active'",(org['id'],)).fetchone()
    if row:orgContract=dict(id=row['id'],kind=row['kind'],district=row['district'],target=row['target'],deadline=row['deadline'],progress=org_contract_current(c,row))
   orgContractsDone=c.execute("SELECT count(*) FROM org_contracts WHERE org_id=? AND status='done'",(org['id'],)).fetchone()[0] if org else 0
   return dict(notices=[dict(r) for r in c.execute('SELECT id,text,world_id,created_at FROM notices WHERE created_at>? AND (world_id IS NULL OR world_id=?) ORDER BY id DESC LIMIT 10',(now()-7*24*E.HOUR,wid))],organizations=organizations,organization=org,members=members,invitations=invitations,applications=applications,appliedTo=mine['org_id'] if mine else None,ranking=ranking,influence=districts,territoryLog=log,myHeld=held_map.get(org['id'],[]) if org else [],events=events,eventsUnread=eventsUnread,orgContract=orgContract,orgContractsDone=orgContractsDone,character_id=ch['id'],myRole=rank(c,ch,org) if org else None,is_leader=bool(org and org['leader_id']==ch['id']),isOfficer=bool(org and rank(c,ch,org) in ('leader','officer')))

 @app.get('/api/worlds/{wid}/organizations/{oid}')
 def org_profile(wid:int,oid:int,u=Depends(d.auth)):
  # publiczna wizytówka: podstawy, skład, prestiż, wpływy i historia z kroniki
  with db.tx() as c:
   ch=own(c,u,wid)
   org=c.execute('SELECT o.*,l.nickname leader_name FROM organizations o JOIN characters l ON l.id=o.leader_id WHERE o.id=? AND o.world_id=?',(oid,wid)).fetchone()
   if not org:fail(404,'Nie ma takiej organizacji w tym świecie.')
   members=[dict(nickname=r['nickname'],role='leader' if r['id']==org['leader_id'] else r['role']) for r in c.execute('SELECT c.nickname,c.id,m.role FROM characters c JOIN org_members m ON m.character_id=c.id WHERE m.org_id=? ORDER BY c.id',(org['id'],))]
   prestige=c.execute('SELECT coalesce(sum(total),0) FROM org_investments WHERE org_id=?',(org['id'],)).fetchone()[0]
   held=[r['district'] for r in c.execute('SELECT t.district FROM territory_state t JOIN organizations o ON o.id=t.org_id WHERE o.id=? ORDER BY t.district',(org['id'],))]
   done=c.execute("SELECT count(*) FROM org_contracts WHERE org_id=? AND status='done'",(org['id'],)).fetchone()[0]
   history=[dict(r) for r in c.execute("SELECT kind,title,description,created_at FROM chronicle WHERE world_id=? AND kind LIKE 'org_%' AND title LIKE ? ORDER BY id DESC LIMIT 6",(wid,'%['+org['tag']+']%'))]
   return dict(name=org['name'],tag=org['tag'],description=org['description'],created_at=org['created_at'],leader=org['leader_name'],members=members,prestige=prestige,held=held,contractsDone=done,history=history)
 @app.post('/api/worlds/{wid}/distinction/claim')
 def claim_distinction(wid:int,request:Request,u=Depends(d.auth)):
  d.rate(request,'distinction-'+str(u['id']),10,3600000)
  with db.tx() as c:
   ch=own(c,u,wid);ts=now();day=E.day_start(ts)
   row=c.execute('SELECT kind FROM daily_actions WHERE character_id=? AND day=?',(ch['id'],day)).fetchone()
   if not row:fail(409,'Dzisiejsza dystynkcja jeszcze się nie zapracowała — wykonaj dziś kontrakt, trening, odbiór dochodu, wpłatę do funduszu albo inwestycję dzielnicową.')
   cur=c.execute('INSERT OR IGNORE INTO daily_distinctions(character_id,world_id,day,kind,created_at) VALUES(?,?,?,?,?)',(ch['id'],wid,day,row['kind'],ts))
   if cur.rowcount==0:fail(409,'Dzisiejsza dystynkcja została już odebrana — wróć jutro po kolejną.')
   return dict(ok=True,kind=row['kind'],label=E.MARKS[row['kind']])
 @app.post('/api/worlds/{wid}/character/evolve')
 def evolve(wid:int,data:EvolveIn,request:Request,u=Depends(d.auth)):
  # 0.32 Ewolucja I stopnia: jednorazowy wybór jednej z 2 pasywek własnej klasy, od 10 poziomu.
  d.rate(request,'evolve-'+str(u['id']),10,3600000)
  code=data.evolution_code.strip().lower()
  evo=combat.EVOLUTIONS.get(code)
  if not evo:fail(422,'Nieznana ewolucja — wybierz jedną z kart swojej klasy.')
  with db.tx() as c:
   ch=own(c,u,wid)
   if not ch['class_type']:fail(422,'Ewolucja wymaga klasy postaci — nowe postacie wybierają ją przy tworzeniu.')
   if (ch['class_evolution'] or 1)!=1:fail(409,'Ewolucja I stopnia została już wybrana — wybór jest jednorazowy.')
   if evo['cls']!=ch['class_type']:fail(422,'Ta ewolucja należy do innej klasy (wymaga: '+evo['cls']+', Twoja: '+str(ch['class_type'])+').')
   s=json.loads(ch['state_json'])
   lvl=E.level(s['xp'])
   if lvl<10:fail(409,'Ewolucja dostępna od 10 poziomu postaci — masz poziom '+str(lvl)+'.')
   s['evolutionCode']=code
   c.execute('UPDATE characters SET state_json=?,class_evolution=2 WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),ch['id']))
   d.audit(c,u['id'],'character.evolve',dict(code=code,level=lvl))
   return dict(ok=True,evolution=dict(code=code,label=evo['label'],icon=evo['icon'],passive=evo['passive'],desc=evo['desc']),level=lvl)
 @app.post('/api/worlds/{wid}/organizations')
 def create_org(wid:int,data:Organization,u=Depends(d.auth)):
  name=data.name.strip();tag=data.tag.strip().upper()
  if not re.fullmatch(r'[\w -]{3,32}',name) or not re.fullmatch(r'[A-Z0-9]{2,5}',tag):fail(422,'Nazwa: 3–32 litery/cyfry/spacje; skrót: 2–5 liter A–Z lub cyfr.')
  description=text(data.description) if data.description.strip() else ''
  with db.tx() as c:
   ch=own(c,u,wid)
   if org_for(c,ch['id']):fail(409,'Już należysz do organizacji.')
   if c.execute('SELECT count(*) FROM organizations WHERE world_id=?',(wid,)).fetchone()[0]>=200:fail(409,'Osiągnięto limit organizacji w wersji testowej.')
   if any(r['name'].casefold()==name.casefold() for r in c.execute('SELECT name FROM organizations WHERE world_id=?',(wid,))):fail(409,'Ta nazwa jest już zajęta na tym świecie.')
   if c.execute('SELECT 1 FROM organizations WHERE world_id=? AND tag=?',(wid,tag)).fetchone():fail(409,'Ten skrót jest już zajęty na tym świecie.')
   oid=c.execute('INSERT INTO organizations(world_id,name,tag,description,leader_id,created_at) VALUES(?,?,?,?,?,?)',(wid,name,tag,description,ch['id'],now())).lastrowid
   c.execute("INSERT INTO org_members(character_id,org_id,joined_at,role) VALUES(?,?,?,'leader')",(ch['id'],oid,now()))
   chronicle.org_founded(chron,c,wid,name,tag,description);return dict(id=oid)

 @app.post('/api/worlds/{wid}/organizations/invite')
 def invite(wid:int,data:Target,request:Request,u=Depends(d.auth)):
  d.rate(request,'org-invite-'+str(u['id']),20,3600000)
  with db.tx() as c:
   ch=own(c,u,wid);org=officer(c,ch);t=target(c,wid,data.target_id)
   if org_for(c,t['id']):fail(409,'Ta postać już należy do organizacji.')
   if blocked(c,u['id'],t['account_id']):fail(409,'Zaproszenie nie jest dostępne z powodu blokady kontaktu.')
   if c.execute('SELECT count(*) FROM org_members WHERE org_id=?',(org['id'],)).fetchone()[0]>=20:fail(409,'Organizacja ma już 20 członków.')
   if c.execute('SELECT 1 FROM org_invites WHERE org_id=? AND target_id=? AND created_at>?',(org['id'],t['id'],now()-86400000)).fetchone():fail(409,'Zaproszenie tej postaci można wysłać raz na 24 godziny.')
   iid=c.execute('INSERT INTO org_invites(org_id,target_id,created_at,expires_at) VALUES(?,?,?,?)',(org['id'],t['id'],now(),now()+86400000)).lastrowid
   emit(c,wid,[t['id']],'org.invite',{'org':org['name'],'tag':org['tag']})
   return dict(id=iid)

 @app.post('/api/organization-invites/{iid}/{decision}')
 def decide(iid:int,decision:str,data:Empty,u=Depends(d.auth)):
  if decision not in ('accept','decline'):fail(404,'Nieznana decyzja.')
  with db.tx() as c:
   row=c.execute('SELECT i.*,o.world_id,o.name oname,o.tag otag,o.leader_id,l.account_id leader_account FROM org_invites i JOIN organizations o ON o.id=i.org_id JOIN characters l ON l.id=o.leader_id WHERE i.id=?',(iid,)).fetchone()
   if not row:fail(404,'Zaproszenie nie istnieje.')
   ch=own(c,u,row['world_id'])
   if row['target_id']!=ch['id']:fail(403,'To zaproszenie jest dla innej postaci.')
   org=org_for(c,ch['id'])
   if row['status']=='accepted' and decision=='accept' and org and org['id']==row['org_id']:return {'ok':True}
   if row['status']!='pending' or row['expires_at']<=now():fail(409,'Zaproszenie nie jest już aktywne.')
   if decision=='accept':
    if org:fail(409,'Już należysz do organizacji.')
    if blocked(c,u['id'],row['leader_account']):fail(409,'Kontakt został zablokowany.')
    if c.execute('SELECT count(*) FROM org_members WHERE org_id=?',(row['org_id'],)).fetchone()[0]>=20:fail(409,'Organizacja jest pełna.')
    c.execute("INSERT INTO org_members(character_id,org_id,joined_at,role) VALUES(?,?,?,'member')",(ch['id'],row['org_id'],now()))
    c.execute("UPDATE org_invites SET status='declined' WHERE target_id=? AND status='pending'",(ch['id'],))
    emit(c,row['world_id'],[x for x in org_officer_ids(c,{'id':row['org_id'],'leader_id':row['leader_id']}) if x!=ch['id']],'org.joined',{'org':row['oname'],'tag':row['otag'],'nick':ch['nickname']})
   c.execute('UPDATE org_invites SET status=? WHERE id=?',('accepted' if decision=='accept' else 'declined',iid));return {'ok':True}

 @app.post('/api/worlds/{wid}/organizations/apply')
 def apply_org(wid:int,data:Apply,request:Request,u=Depends(d.auth)):
  d.rate(request,'org-apply-'+str(u['id']),5,3600000)
  body=text(data.text,10)
  with db.tx() as c:
   ch=own(c,u,wid)
   if org_for(c,ch['id']):fail(409,'Już należysz do organizacji.')
   org=c.execute('SELECT o.* FROM organizations o WHERE o.id=? AND o.world_id=?',(data.org_id,wid)).fetchone()
   if not org:fail(404,'Nie ma takiej organizacji w tym świecie.')
   if c.execute('SELECT count(*) FROM org_members WHERE org_id=?',(org['id'],)).fetchone()[0]>=20:fail(409,'Organizacja jest pełna.')
   if blocked(c,u['id'],c.execute('SELECT a.id FROM accounts a JOIN characters ch ON ch.account_id=a.id WHERE ch.id=?',(org['leader_id'],)).fetchone()['id']):fail(409,'Podanie nie jest dostępne z powodu blokady kontaktu.')
   if c.execute("SELECT 1 FROM org_applications WHERE character_id=? AND org_id=? AND status='pending' AND expires_at>?",(ch['id'],org['id'],now())).fetchone():fail(409,'Twoje podanie do tej organizacji już czeka na decyzję.')
   aid=c.execute('INSERT INTO org_applications(org_id,character_id,text,created_at,expires_at) VALUES(?,?,?,?,?)',(org['id'],ch['id'],body,now(),now()+7*86400000)).lastrowid
   emit(c,wid,[x for x in org_officer_ids(c,org) if x!=ch['id']],'org.application',{'org':org['name'],'tag':org['tag'],'nick':ch['nickname'],'aid':aid})
  return dict(id=aid)
 @app.post('/api/org-applications/{aid}/{decision}')
 def decide_application(aid:int,decision:str,data:Empty,u=Depends(d.auth)):
  if decision not in ('accept','decline'):fail(404,'Nieznana decyzja.')
  with db.tx() as c:
   row=c.execute('SELECT a.*,o.world_id FROM org_applications a JOIN organizations o ON o.id=a.org_id WHERE a.id=?',(aid,)).fetchone()
   if not row:fail(404,'Podanie nie istnieje.')
   ch=own(c,u,row['world_id']);org=org_for(c,ch['id'])
   if not org or org['id']!=row['org_id'] or rank(c,ch,org) not in ('leader','officer'):fail(403,'Decyzje podejmują lider i oficerowie tej organizacji.')
   if row['status']!='pending':fail(409,'Podanie zostało już rozpatrzone.')
   applicant=org_for(c,row['character_id'])
   if decision=='accept':
    if applicant:fail(409,'Kandydat dołączył już do innej organizacji.')
    if c.execute('SELECT count(*) FROM org_members WHERE org_id=?',(org['id'],)).fetchone()[0]>=20:fail(409,'Organizacja jest pełna.')
    leader_acct=c.execute('SELECT a.id FROM accounts a JOIN characters ch ON ch.account_id=a.id WHERE ch.id=?',(org['leader_id'],)).fetchone()['id']
    app_acct=c.execute('SELECT account_id FROM characters WHERE id=?',(row['character_id'],)).fetchone()['account_id']
    if blocked(c,leader_acct,app_acct):fail(409,'Kontakt został zablokowany.')
    c.execute("INSERT INTO org_members(character_id,org_id,joined_at,role) VALUES(?,?,?,'member')",(row['character_id'],org['id'],now()))
    c.execute("UPDATE org_applications SET status='declined' WHERE character_id=? AND status='pending' AND id<>?",(row['character_id'],aid))
    emit(c,row['world_id'],[x for x in org_officer_ids(c,org) if x!=row['character_id']],'org.joined',{'org':org['name'],'tag':org['tag'],'nick':c.execute('SELECT nickname FROM characters WHERE id=?',(row['character_id'],)).fetchone()['nickname']})
   c.execute('UPDATE org_applications SET status=? WHERE id=?',('accepted' if decision=='accept' else 'declined',aid))
   emit(c,row['world_id'],[row['character_id']],'org.accepted' if decision=='accept' else 'org.declined',{'org':org['name'],'tag':org['tag']})
   d.audit(c,u['id'],'org.application_'+('accepted' if decision=='accept' else 'declined'),dict(org=org['id'],application=aid))
   return {'ok':True}
 @app.post('/api/worlds/{wid}/organizations/building')
 def org_building(wid:int,data:AllyBuild,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=officer(c,ch)
   b=next((x for x in E.ALLY_BUILDINGS if x['id']==data.building),None)
   if not b:fail(422,'Nieznany budynek sojuszu.')
   try:lv=json.loads(org.get('buildings') or '{}')
   except Exception:lv={}
   cur=int(lv.get(b['id'],0))
   if cur>=E.ALLY_MAX:fail(409,b['name']+' ma już maksymalny poziom.')
   cost=E.ALLY_COST[cur]
   if org['fund']<cost:fail(409,'Za mało w funduszu sojuszu — potrzeba '+str(cost)+' $.')
   lv[b['id']]=cur+1
   c.execute('UPDATE organizations SET fund=fund-?,buildings=? WHERE id=?',(cost,json.dumps(lv),org['id']))
   d.audit(c,u['id'],'org.building',dict(org=org['id'],building=b['id'],level=cur+1))
   emit(c,wid,[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(org['id'],)) if r['character_id']!=ch['id']],'org.building',{'org':org['name'],'tag':org['tag'],'building':b['name'],'level':cur+1})
  return dict(buildings=lv,fund=org['fund']-cost)
 @app.post('/api/worlds/{wid}/organizations/fund')
 def fund_org(wid:int,data:Fund,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=org_for(c,ch['id'])
   if not org:fail(403,'Nie należysz do organizacji.')
   if data.amount<50 or data.amount>5000:fail(422,'Jednorazowo można wpłacić 50–5 000 $.')
   w=d.world(c,wid,True);s=json.loads(ch['state_json']);E.sync(s,now(),w['speed']);E.spend(s,cash=data.amount)
   c.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(s,ensure_ascii=False,separators=(',',':')),ch['id']))
   c.execute('UPDATE organizations SET fund=fund+? WHERE id=?',(data.amount,org['id']))
   d.audit(c,u['id'],'org.fund',dict(org=org['id'],amount=data.amount))
   E.mark_daily(c,ch['id'],'fund',now())
   E.bump(c,wid,ch['id'],now(),deeds=1)
   check_org_contract(c,wid,org,u['id'])
  return dict(fund=org['fund']+data.amount,cash=s['cash'])
 @app.post('/api/worlds/{wid}/organizations/invest')
 def invest_org(wid:int,data:InvestOrg,request:Request,u=Depends(d.auth)):
  d.rate(request,'org-invest-'+str(u['id']),20,3600000)
  with db.tx() as c:
   ch=own(c,u,wid);org=officer(c,ch)
   if data.district not in E.DISTRICTS:fail(422,'Nieznana dzielnica.')
   fresh=c.execute('SELECT fund FROM organizations WHERE id=?',(org['id'],)).fetchone()['fund']
   if fresh<data.amount:fail(409,'Fundusz organizacji jest za mały.')
   old=c.execute('SELECT total FROM org_investments WHERE org_id=? AND district=?',(org['id'],data.district)).fetchone()
   if E.INVEST_CAP and old and old['total']+data.amount>E.INVEST_CAP:fail(409,'Limit inwestycji organizacji w dzielnicy to '+str(E.INVEST_CAP)+' $.')
   c.execute('UPDATE organizations SET fund=fund-? WHERE id=?',(data.amount,org['id']))
   c.execute('INSERT INTO org_investments(org_id,district,total) VALUES(?,?,?) ON CONFLICT(org_id,district) DO UPDATE SET total=excluded.total',(org['id'],data.district,(old['total'] if old else 0)+data.amount))
   d.audit(c,u['id'],'org.invest',dict(org=org['id'],district=data.district,amount=data.amount))
   check_org_contract(c,wid,org,u['id'])
   E.mark_daily(c,ch['id'],'invest',now())
   E.bump(c,wid,ch['id'],now(),deeds=1)
   top=claim(c,wid,data.district,u['id'])
   if top and top['changed']:
    mine=[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(org['id'],)) if r['character_id']!=ch['id']]
    emit(c,wid,mine,'territory.gained',{'district':data.district,'tag':org['tag']})
    if top['prev']:
     lost=[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(top['prev'],))]
     emit(c,wid,lost,'territory.lost',{'district':data.district,'by':org['tag']})
   held=[r['district'] for r in c.execute('SELECT district FROM territory_state WHERE world_id=? AND org_id=?',(wid,org['id'])).fetchall()]
   return dict(fund=fresh-data.amount,invested=(old['total'] if old else 0)+data.amount,claimed=top['tag'] if top and top['id']==org['id'] else None,held=held)
 @app.post('/api/worlds/{wid}/events/read')
 def events_read(wid:int,data:EventsRead,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid)
   if data.all:c.execute('UPDATE game_events SET read_at=? WHERE character_id=? AND read_at IS NULL',(now(),ch['id']))
   else:
    for i in data.ids[:100]:c.execute('UPDATE game_events SET read_at=? WHERE character_id=? AND id=? AND read_at IS NULL',(now(),ch['id'],i))
   return {'ok':True}
 @app.get('/api/ranking/global/season/{sn}')
 def ranking_global_season(sn:int,u=Depends(d.auth)):
  with db.tx() as c:
   cur=season_of(now())
   if sn>cur:fail(422,'Ten sezon jeszcze się nie zakończył.')
   ensure_seasons(c,cur)
   merged=[]
   for r in c.execute('SELECT payload FROM season_archive WHERE season=?',(sn,)).fetchall():
    for e in json.loads(r['payload']):merged.append(dict(e))
   merged.sort(key=lambda e:(-e['xp'],e['nickname']))
   labels={}
   for r in c.execute('SELECT t.character_id,t.label FROM character_titles t JOIN season_archive sa ON sa.season=t.season WHERE t.season=?',(sn,)).fetchall():labels.setdefault(r['character_id'],[]).append(r['label'])
   return dict(season=sn,rows=[dict(place=i+1,nickname=e['nickname'],level=e['level'],xp=e['xp'],titles=labels.get(e.get('cid'),[])) for i,e in enumerate(merged[:10])],worlds=c.execute('SELECT count(*) FROM season_archive WHERE season=?',(sn,)).fetchone()[0])
 @app.get('/api/ranking/global/{wid}')
 def ranking_global(wid:int,u=Depends(d.auth)):
  # Season ranking spans all worlds; wid only anchors the "your position" line.
  with db.tx() as c:
   cur=season_of(now());ensure_seasons(c,cur)
   me=None
   w=c.execute('SELECT name FROM worlds WHERE id=?',(wid,)).fetchone()
   if w:
    ch=d.own(c,u['id'],wid)
    xp=json.loads(ch['state_json']).get('xp',0)
    higher=c.execute('SELECT count(*) FROM characters c2 JOIN accounts a ON a.id=c2.account_id WHERE a.banned=0 AND json_extract(c2.state_json,"$.xp")>?',(xp,)).fetchone()[0]
    me=dict(place=higher+1,xp=xp,level=E.level(xp),world=w['name'])
   rows=[dict(place=i+1,nickname=r['nickname'],world=r['wname'],level=E.level(r['xp'] or 0),xp=r['xp'] or 0,tag=r['tag'],titles=r['titles'].split(';') if r['titles'] else []) for i,r in enumerate(c.execute('SELECT ch.nickname,json_extract(ch.state_json,"$.xp") xp,w.name wname,o.tag tag,(SELECT group_concat(label,char(59)) FROM character_titles t WHERE t.character_id=ch.id) titles FROM characters ch JOIN accounts a ON a.id=ch.account_id JOIN worlds w ON w.id=ch.world_id LEFT JOIN org_members m ON m.character_id=ch.id LEFT JOIN organizations o ON o.id=m.org_id WHERE a.banned=0 ORDER BY xp DESC,ch.id LIMIT 50').fetchall())]
   archive=[r['season'] for r in c.execute('SELECT DISTINCT season FROM season_archive ORDER BY season DESC')]
   if me is not None:
    tl=c.execute('SELECT group_concat(label,char(59)) FROM character_titles WHERE character_id=?',(ch['id'],)).fetchone()[0]
    me['titles']=tl.split(';') if tl else []
   return dict(season=cur,seasonEndsAt=SEASON_ANCHOR+cur*SEASON_LEN,archive=archive,rows=rows,me=me)
 @app.post('/api/worlds/{wid}/organizations/contract')
 def create_org_contract(wid:int,data:OrgContract,request:Request,u=Depends(d.auth)):
  d.rate(request,'org-contract-'+str(u['id']),5,3600000)
  if data.kind=='prestige':
   if data.district not in E.DISTRICTS:fail(422,'Wybierz dzielnicę celu.')
   if data.target<100 or data.target>20000:fail(422,'Cel prestiżu: 100–20 000 $.')
  elif data.target<200 or data.target>50000:fail(422,'Cel zbiórki: 200–50 000 $.')
  with db.tx() as c:
   ch=own(c,u,wid);org=officer(c,ch)
   if c.execute("SELECT 1 FROM org_contracts WHERE org_id=? AND status='active'",(org['id'],)).fetchone():fail(409,'Ten organizacja ma już aktywny kontrakt — najpierw go ukończ lub anuluj.')
   base=(c.execute('SELECT fund FROM organizations WHERE id=?',(org['id'],)).fetchone()['fund'] if data.kind=='fund' else c.execute('SELECT coalesce(sum(total),0) FROM org_investments WHERE org_id=? AND district=?',(org['id'],data.district)).fetchone()[0])
   cid=c.execute("INSERT INTO org_contracts(world_id,org_id,kind,district,target,base,deadline,created_by,created_at) VALUES(?,?,?,?,?,?,?,?,?)",(wid,org['id'],data.kind,data.district if data.kind=='prestige' else '',data.target,base,now()+data.hours*3600000,ch['id'],now())).lastrowid
   d.audit(c,u['id'],'org.contract_create',dict(org=org['id'],kind=data.kind,district=data.district,target=data.target,hours=data.hours))
   emit(c,wid,[x for x in org_officer_ids(c,org)+[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(org['id'],))] if x!=ch['id']],'org.contract_created',{'org':org['name'],'tag':org['tag'],'kind':data.kind,'district':data.district or '','target':data.target})
  return dict(id=cid)
 @app.post('/api/worlds/{wid}/organizations/contract/cancel')
 def cancel_org_contract(wid:int,data:Empty,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=officer(c,ch)
   row=c.execute("SELECT * FROM org_contracts WHERE org_id=? AND status='active'",(org['id'],)).fetchone()
   if not row:fail(404,'Brak aktywnego kontraktu organizacyjnego.')
   c.execute("UPDATE org_contracts SET status='cancelled' WHERE id=?",(row['id'],))
   d.audit(c,u['id'],'org.contract_cancel',dict(org=org['id'],contract=row['id']))
   emit(c,wid,[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(org['id'],)) if r['character_id']!=ch['id']],'org.contract_cancelled',{'org':org['name'],'tag':org['tag']})
  return {'ok':True}
 @app.post('/api/worlds/{wid}/organizations/announcement')
 def announce_org(wid:int,data:OrgAnnounce,u=Depends(d.auth)):
  body=data.text.strip()
  if len(body)<3:fail(422,'Wpisz treść ogłoszenia.')
  if re.search(r'https?://|[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}',body,re.I):fail(422,'Linki i adresy e-mail są wyłączone.')
  with db.tx() as c:
   ch=own(c,u,wid);org=officer(c,ch)
   c.execute('UPDATE organizations SET announcement=? WHERE id=?',(body[:200],org['id']))
   emit(c,wid,[r['character_id'] for r in c.execute('SELECT character_id FROM org_members WHERE org_id=?',(org['id'],)) if r['character_id']!=ch['id']],'org.announcement',{'org':org['name'],'tag':org['tag'],'text':body[:80]})
  return {'ok':True}
 @app.post('/api/worlds/{wid}/organizations/role')
 def set_role(wid:int,data:Role,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=leader(c,ch);t=target(c,wid,data.target_id)
   if t['id']==ch['id'] or not c.execute('SELECT 1 FROM org_members WHERE org_id=? AND character_id=?',(org['id'],t['id'])).fetchone():fail(409,'Wybierz innego członka swojej organizacji.')
   c.execute('UPDATE org_members SET role=? WHERE character_id=?',('officer' if data.role=='officer' else 'member',t['id']))
   emit(c,wid,[t['id']],'org.role',{'org':org['name'],'tag':org['tag'],'role':data.role})
   d.audit(c,u['id'],'org.role',dict(org=org['id'],target=t['id'],role=data.role))
   return {'ok':True}

 @app.post('/api/worlds/{wid}/organizations/leave')
 def leave(wid:int,data:Empty,u=Depends(d.auth)):
  with db.tx() as c:
   ch=own(c,u,wid);org=org_for(c,ch['id'])
   if not org:fail(409,'Nie należysz do organizacji.')
   if org['leader_id']==ch['id']:
    if c.execute('SELECT count(*) FROM org_members WHERE org_id=?',(org['id'],)).fetchone()[0]>1:fail(409,'Najpierw przekaż rolę lidera innemu członkowi.')
    c.execute('DELETE FROM organizations WHERE id=?',(org['id'],))
   else:c.execute('DELETE FROM org_members WHERE character_id=?',(ch['id'],))
   return {'ok':True}

 @app.post('/api/worlds/{wid}/organizations/{operation}')
 def member_action(wid:int,operation:str,data:Target,u=Depends(d.auth)):
  if operation not in ('transfer','remove-member'):fail(404,'Nieznana operacja.')
  with db.tx() as c:
   ch=own(c,u,wid);org=leader(c,ch) if operation=='transfer' else officer(c,ch);t=target(c,wid,data.target_id)
   if t['id']==ch['id'] or not c.execute('SELECT 1 FROM org_members WHERE org_id=? AND character_id=?',(org['id'],t['id'])).fetchone():fail(409,'Wybierz innego członka swojej organizacji.')
   if operation=='transfer':
    c.execute('UPDATE organizations SET leader_id=? WHERE id=?',(t['id'],org['id']))
    c.execute("UPDATE org_members SET role='leader' WHERE character_id=?",(t['id'],))
    c.execute("UPDATE org_members SET role='officer' WHERE character_id=?",(ch['id'],))
   else:
    t_rank=rank(c,t,org)
    if t_rank!='member' and rank(c,ch,org)!='leader':fail(403,'Tylko lider może usunąć oficera.')
    c.execute('DELETE FROM org_members WHERE character_id=?',(t['id'],))
   return {'ok':True}

 @app.get('/api/worlds/{wid}/chat/{kind}')
 def read_chat(wid:int,kind:str,u=Depends(d.auth)):
  with db.read() as c:
   ch=own(c,u,wid);oid=channel(c,ch,kind)
   rows=c.execute('SELECT m.id,m.author_id,m.body,m.created_at,m.hidden,c.nickname,c.account_id,COALESCE((SELECT org.tag FROM org_members om JOIN organizations org ON org.id=om.org_id WHERE om.character_id=c.id LIMIT 1),(SELECT org2.tag FROM organizations org2 WHERE org2.leader_id=c.id LIMIT 1)) org_tag FROM chat_messages m JOIN characters c ON c.id=m.author_id WHERE m.world_id=? AND m.org_id IS ? AND NOT EXISTS (SELECT 1 FROM social_blocks b WHERE (b.account_id=? AND b.target_account=c.account_id) OR (b.account_id=c.account_id AND b.target_account=?)) ORDER BY m.id DESC LIMIT 60',(wid,oid,u['id'],u['id'])).fetchall()
   muted=c.execute('SELECT until_at FROM chat_mutes WHERE account_id=? AND until_at>?',(u['id'],now())).fetchone()
   return dict(messages=[dict(id=r['id'],author_id=r['author_id'],nickname=r['nickname'],text='Wiadomość ukryta przez moderatora.' if r['hidden'] else r['body'],hidden=bool(r['hidden']),created_at=r['created_at'],own=r['account_id']==u['id'],org_tag=r['org_tag'] or None) for r in reversed(rows)],muted_until=muted['until_at'] if muted else None,serverTime=now())

 @app.post('/api/worlds/{wid}/chat/{kind}')
 def send_chat(wid:int,kind:str,data:Message,u=Depends(d.auth)):
  body=text(data.text)
  with db.tx() as c:
   ch=own(c,u,wid);oid=channel(c,ch,kind)
   old=c.execute('SELECT * FROM chat_messages WHERE author_id=? AND client_id=?',(ch['id'],data.client_id)).fetchone()
   if old:
    if old['body']!=body or old['org_id']!=oid:fail(409,'Identyfikator wiadomości został użyty dla innej treści.')
    return dict(id=old['id'])
   if c.execute('SELECT 1 FROM chat_mutes WHERE account_id=? AND until_at>?',(u['id'],now())).fetchone():fail(403,'Możliwość pisania została czasowo zawieszona.')
   recent=c.execute('SELECT max(m.created_at),count(*) FROM chat_messages m JOIN characters c ON c.id=m.author_id WHERE c.account_id=? AND m.created_at>?',(u['id'],now()-3600000)).fetchone()
   if recent[1]>=40 or (recent[0] is not None and recent[0]>now()-3000):fail(429,'Odczekaj 3 sekundy. Limit czatu: 40 wiadomości na godzinę na konto.')
   mid=c.execute('INSERT INTO chat_messages(world_id,org_id,author_id,body,client_id,created_at) VALUES(?,?,?,?,?,?)',(wid,oid,ch['id'],body,data.client_id,now())).lastrowid
   return dict(id=mid)

 @app.post('/api/worlds/{wid}/reports')
 def report(wid:int,data:Report,request:Request,u=Depends(d.auth)):
  d.rate(request,'reports-'+str(u['id']),12,3600000)
  with db.tx() as c:
   ch=own(c,u,wid);row=c.execute('SELECT * FROM chat_messages WHERE id=? AND world_id=?',(data.message_id,wid)).fetchone()
   org=org_for(c,ch['id'])
   if not row or (row['org_id'] is not None and (not org or row['org_id']!=org['id'])):fail(404,'Wiadomość nie jest dostępna.')
   if row['author_id']==ch['id']:fail(409,'Nie zgłaszasz własnej wiadomości.')
   c.execute('INSERT OR IGNORE INTO chat_reports(message_id,reporter_id,reason,created_at) VALUES(?,?,?,?)',(row['id'],u['id'],text(data.reason,3),now()));return {'ok':True}

 @app.post('/api/worlds/{wid}/blocks')
 def block(wid:int,data:Target,u=Depends(d.auth)):
  with db.tx() as c:
   own(c,u,wid);t=target(c,wid,data.target_id)
   if t['account_id']==u['id']:fail(409,'Nie możesz zablokować siebie.')
   c.execute('INSERT OR IGNORE INTO social_blocks VALUES(?,?,?,?)',(u['id'],t['account_id'],t['nickname'],now()))
   c.execute("UPDATE challenges SET status='declined' WHERE status='pending' AND ((attacker_id IN (SELECT id FROM characters WHERE account_id=?) AND defender_id IN (SELECT id FROM characters WHERE account_id=?)) OR (attacker_id IN (SELECT id FROM characters WHERE account_id=?) AND defender_id IN (SELECT id FROM characters WHERE account_id=?)))",(u['id'],t['account_id'],t['account_id'],u['id']))
   return {'ok':True}

 # 0.38: DM z mapy — wątek dwojga mieszkańców; blokady, mute i limity jak na czacie.
 @app.get('/api/worlds/{wid}/dm')
 def dm_threads(wid:int,u=Depends(d.auth)):
  with db.read() as c:
   ch=own(c,u,wid)
   peers=c.execute('SELECT peer,MAX(id) mid FROM (SELECT CASE WHEN sender_id=? THEN recipient_id ELSE sender_id END peer,id FROM dm_messages WHERE world_id=? AND (sender_id=? OR recipient_id=?)) GROUP BY peer ORDER BY mid DESC LIMIT 20',(ch['id'],wid,ch['id'],ch['id'])).fetchall()
   threads=[]
   for r in peers:
    m=c.execute('SELECT body,created_at,sender_id FROM dm_messages WHERE id=?',(r['mid'],)).fetchone()
    p=c.execute('SELECT id,nickname,state_json FROM characters WHERE id=? AND world_id=?',(r['peer'],wid)).fetchone()
    if m and p:threads.append(dict(pid=p['id'],nickname=p['nickname'],level=E.level(json.loads(p['state_json'])['xp']),last=m['body'],at=m['created_at'],mine=m['sender_id']==ch['id'],
      unread=c.execute('SELECT count(*) FROM dm_messages WHERE world_id=? AND sender_id=? AND recipient_id=? AND read_at IS NULL',(wid,p['id'],ch['id'])).fetchone()[0]))
   return dict(threads=threads)

 def dm_pair(c,u,wid,pid):
  ch=own(c,u,wid);p=target(c,wid,pid)
  if p['id']==ch['id']:fail(409,'Nie piszesz do siebie.')
  if blocked(c,u['id'],p['account_id']):fail(409,'Kontakt został zablokowany.')
  return ch,p

 @app.get('/api/worlds/{wid}/dm/{pid}')
 def dm_thread(wid:int,pid:int,u=Depends(d.auth)):
  with db.tx() as c:  # 0.39: otwarcie wątku oznacza wiadomości partnera jako przeczytane
   ch,p=dm_pair(c,u,wid,pid)
   seen=c.execute('SELECT MAX(last_seen) ls FROM sessions WHERE account_id=? AND expires_at>?',(p['account_id'],now())).fetchone()
   rows=c.execute('SELECT id,sender_id,body,created_at FROM dm_messages WHERE world_id=? AND ((sender_id=? AND recipient_id=?) OR (sender_id=? AND recipient_id=?)) ORDER BY id DESC LIMIT 50',(wid,ch['id'],p['id'],p['id'],ch['id'])).fetchall()
   c.execute('UPDATE dm_messages SET read_at=? WHERE world_id=? AND recipient_id=? AND sender_id=? AND read_at IS NULL',(now(),wid,ch['id'],p['id']))
   return dict(partner=dict(id=p['id'],nickname=p['nickname'],level=E.level(json.loads(p['state_json'])['xp']),online=bool(seen['ls']) and now()-seen['ls']<=300000),
    messages=[dict(id=r['id'],mine=r['sender_id']==ch['id'],body=r['body'],created_at=r['created_at']) for r in reversed(rows)])

 @app.post('/api/worlds/{wid}/dm/{pid}')
 def dm_send(wid:int,pid:int,data:DmSend,request:Request,u=Depends(d.auth)):
  d.rate(request,'dm-'+str(u['id']),60,3600000)
  body=text(data.text)
  with db.tx() as c:
   ch,p=dm_pair(c,u,wid,pid)
   if c.execute('SELECT 1 FROM chat_mutes WHERE account_id=? AND until_at>?',(u['id'],now())).fetchone():fail(403,'Możliwość pisania została czasowo zawieszona.')
   last=c.execute('SELECT MAX(created_at) t FROM dm_messages WHERE sender_id=?',(ch['id'],)).fetchone()
   if last['t'] and last['t']>now()-3000:fail(429,'Odczekaj 3 sekundy przed kolejną wiadomością.')
   if c.execute('SELECT count(*) FROM dm_messages WHERE sender_id=? AND created_at>?',(ch['id'],now()-3600000)).fetchone()[0]>=30:fail(429,'Limit DM: 30 wiadomości na godzinę.')
   mid=c.execute('INSERT INTO dm_messages(world_id,sender_id,recipient_id,body,created_at) VALUES(?,?,?,?,?)',(wid,ch['id'],p['id'],body,now())).lastrowid
   return dict(ok=True,id=mid)

 @app.post('/api/account/blocks/remove')
 def unblock(data:Unblock,u=Depends(d.auth)):
  with db.tx() as c:c.execute('DELETE FROM social_blocks WHERE account_id=? AND target_account=?',(u['id'],data.account_id));return {'ok':True}

 @app.get('/api/account/security')
 def security(u=Depends(d.auth)):
  with db.read() as c:
   sessions=[dict(id=r['sid'],created_at=r['created_at'],last_seen=r['last_seen'],expires_at=r['expires_at'],current=r['token_hash']==u['token_hash']) for r in c.execute('SELECT * FROM sessions WHERE account_id=? AND expires_at>? ORDER BY created_at DESC',(u['id'],now()))]
   blocks=[dict(r) for r in c.execute('SELECT target_account account_id,display_name,created_at FROM social_blocks WHERE account_id=?',(u['id'],))]
   appeals=[dict(r) for r in c.execute('SELECT id,text,status,resolution,created_at,resolved_at FROM appeals WHERE account_id=? ORDER BY id DESC LIMIT 5',(u['id'],))]
   return dict(sessions=sessions,blocks=blocks,appeals=appeals,minPasswordLength=d.min_password_length)

 @app.post('/api/account/password')
 def password(data:PasswordChange,request:Request,u=Depends(d.auth)):
  d.rate(request,'password-'+str(u['id']),8,900000);check_password(u,data.current_password)
  if len(data.new_password)<d.min_password_length:fail(422,'Nowe hasło musi mieć co najmniej '+str(d.min_password_length)+' znaków.')
  hashed=d.PH.hash(data.new_password)
  with db.tx() as c:
   r=c.execute('UPDATE accounts SET password_hash=? WHERE id=? AND password_hash=?',(hashed,u['id'],u['password_hash']))
   if r.rowcount!=1:fail(409,'Hasło zostało zmienione w innej sesji. Zaloguj się ponownie.')
   c.execute('DELETE FROM sessions WHERE account_id=?',(u['id'],));d.audit(c,u['id'],'account.password_changed',{})
  return {'ok':True,'requiresLogin':True}

 @app.post('/api/account/sessions/revoke')
 def revoke(data:Revoke,request:Request,u=Depends(d.auth)):
  d.rate(request,'revoke-'+str(u['id']),12,900000);check_password(u,data.password)
  with db.tx() as c:
   current=c.execute('SELECT password_hash FROM accounts WHERE id=?',(u['id'],)).fetchone()
   if not current or current['password_hash']!=u['password_hash']:fail(409,'Hasło zmieniło się w innej sesji. Zaloguj się ponownie.')
   if data.session_id is None:c.execute('DELETE FROM sessions WHERE account_id=? AND token_hash<>?',(u['id'],u['token_hash']))
   else:
    row=c.execute('SELECT token_hash FROM sessions WHERE sid=? AND account_id=?',(data.session_id,u['id'])).fetchone()
    if not row:fail(404,'Sesja nie należy do tego konta albo już wygasła.')
    if row['token_hash']==u['token_hash']:fail(409,'Do zakończenia bieżącej sesji użyj przycisku Wyloguj.')
    c.execute('DELETE FROM sessions WHERE sid=? AND account_id=?',(data.session_id,u['id']))
   return {'ok':True}

 @app.get('/api/admin/reports')
 def reports(u=Depends(d.staff)):
  with db.read() as c:
   rows=c.execute("SELECT r.*,m.body,m.hidden,m.world_id,c.nickname,w.name world_name FROM chat_reports r LEFT JOIN chat_messages m ON m.id=r.message_id LEFT JOIN characters c ON c.id=m.author_id LEFT JOIN worlds w ON w.id=m.world_id ORDER BY (r.status='open') DESC,r.id DESC LIMIT 100").fetchall()
   appeals=[dict(r) for r in c.execute("SELECT a.*,ac.username FROM appeals a JOIN accounts ac ON ac.id=a.account_id ORDER BY (a.status='pending') DESC,a.id DESC LIMIT 50")]
   return {'reports':[dict(r) for r in rows],'appeals':appeals}

 @app.post('/api/admin/reports/{rid}/resolve')
 def resolve(rid:int,data:Resolve,u=Depends(d.staff)):
  with db.tx() as c:
   r=c.execute('SELECT * FROM chat_reports WHERE id=?',(rid,)).fetchone()
   if not r:fail(404,'Zgłoszenie nie istnieje.')
   if r['status']!='open':fail(409,'Zgłoszenie zostało już rozpatrzone.')
   if data.action!='dismiss':
    c.execute('UPDATE chat_messages SET hidden=1 WHERE id=?',(r['message_id'],))
    if data.action=='hide_mute':
     a=c.execute('SELECT a.id,a.role FROM accounts a JOIN characters c ON c.account_id=a.id JOIN chat_messages m ON m.author_id=c.id WHERE m.id=?',(r['message_id'],)).fetchone()
     if a:c.execute('INSERT INTO chat_mutes VALUES(?,?) ON CONFLICT(account_id) DO UPDATE SET until_at=max(until_at,excluded.until_at)',(a['id'],now()+86400000))
   c.execute("UPDATE chat_reports SET status=?,note=?,resolved_at=? WHERE id=?",(data.action,data.note,now(),rid));d.audit(c,u['id'],'chat.report_resolved',dict(report_id=rid,action=data.action));return {'ok':True}

 @app.post('/api/account/appeals')
 def create_appeal(data:Appeal,request:Request,u=Depends(d.auth)):
  # Pre-check outside the transaction: rate() opens its own write transaction and must never nest.
  with db.read() as c:
   if not c.execute('SELECT 1 FROM chat_mutes WHERE account_id=?',(u['id'],)).fetchone():fail(409,'Odwołanie dotyczy kar czatu — to konto nie otrzymało kary.')
   pending=c.execute("SELECT 1 FROM appeals WHERE account_id=? AND status='pending'",(u['id'],)).fetchone()
   if pending:fail(409,'Twoje poprzednie odwołanie czeka na rozpatrzenie.')
  d.rate(request,'appeal-'+str(u['id']),1,24*3600000)
  with db.tx() as c:
   pending=c.execute("SELECT 1 FROM appeals WHERE account_id=? AND status='pending'",(u['id'],)).fetchone()
   if pending:fail(409,'Twoje poprzednie odwołanie czeka na rozpatrzenie.')
   aid=c.execute('INSERT INTO appeals(account_id,text,created_at) VALUES(?,?,?)',(u['id'],data.text.strip(),now())).lastrowid
   d.audit(c,u['id'],'appeal.created',dict(id=aid))
  return dict(id=aid)
 @app.post('/api/staff/appeals/{aid}/resolve')
 def resolve_appeal(aid:int,data:AppealResolve,u=Depends(d.staff)):
  with db.tx() as c:
   row=c.execute('SELECT * FROM appeals WHERE id=?',(aid,)).fetchone()
   if not row:fail(404,'Odwołanie nie istnieje.')
   if row['status']!='pending':fail(409,'Odwołanie zostało już rozpatrzone.')
   status='upheld' if data.uphold else 'dismissed'
   c.execute('UPDATE appeals SET status=?,resolution=?,resolved_at=?,resolved_by=? WHERE id=?',(status,data.note.strip(),now(),u['id'],aid))
   if data.uphold:c.execute('DELETE FROM chat_mutes WHERE account_id=?',(row['account_id'],))
   d.audit(c,u['id'],'appeal.resolved',dict(id=aid,status=status))
  return {'ok':True}
 @app.get('/api/admin/backups')
 def backup_status(u=Depends(d.admin)):return backups.status()
 @app.post('/api/admin/backups')
 def backup_create(data:Empty,request:Request,u=Depends(d.admin)):
  d.rate(request,'backup-'+str(u['id']),3,3600000)
  try:record=backups.create()
  except Exception:fail(503,'Kopia nie powstała. Sprawdź katalog i wolne miejsce.')
  with db.tx() as c:d.audit(c,u['id'],'backup.created',dict(name=record['name']))
  return record

 def before_delete(c,uid):
  orgs=c.execute('SELECT o.id FROM organizations o JOIN characters ch ON ch.id=o.leader_id WHERE ch.account_id=?',(uid,)).fetchall()
  for org in orgs:
   if c.execute('SELECT count(*) FROM org_members WHERE org_id=?',(org['id'],)).fetchone()[0]>1:fail(409,'Przed usunięciem konta przekaż rolę lidera organizacji innemu członkowi.')
   c.execute('DELETE FROM organizations WHERE id=?',(org['id'],))
 def export_account(c,uid):
  return dict(invitations=[dict(r) for r in c.execute('SELECT i.id,i.org_id,i.target_id,i.status,i.created_at,i.expires_at FROM org_invites i JOIN characters ch ON ch.id=i.target_id WHERE ch.account_id=?',(uid,))],mutes=[dict(r) for r in c.execute('SELECT until_at FROM chat_mutes WHERE account_id=?',(uid,))],sessions=[dict(r) for r in c.execute('SELECT created_at,last_seen,expires_at FROM sessions WHERE account_id=?',(uid,))],organizations_led=[dict(r) for r in c.execute('SELECT o.id,o.world_id,o.name,o.tag,o.description,o.created_at FROM organizations o JOIN characters ch ON ch.id=o.leader_id WHERE ch.account_id=?',(uid,))],messages=[dict(r) for r in c.execute('SELECT m.id,m.world_id,m.org_id,m.body,m.created_at,m.hidden FROM chat_messages m JOIN characters ch ON ch.id=m.author_id WHERE ch.account_id=?',(uid,))],blocks=[dict(r) for r in c.execute('SELECT target_account,display_name,created_at FROM social_blocks WHERE account_id=?',(uid,))],reports=[dict(r) for r in c.execute('SELECT id,message_id,reason,status,created_at FROM chat_reports WHERE reporter_id=?',(uid,))],memberships=[dict(r) for r in c.execute('SELECT m.character_id,m.org_id,m.joined_at FROM org_members m JOIN characters ch ON ch.id=m.character_id WHERE ch.account_id=?',(uid,))],appeals=[dict(r) for r in c.execute('SELECT id,text,status,resolution,created_at,resolved_at FROM appeals WHERE account_id=? ORDER BY id DESC',(uid,))])
 return SimpleNamespace(before_delete=before_delete,export_account=export_account,blocked=blocked,backups=backups,emit=emit)  # 2.3: emit dla npc.py
