from __future__ import annotations
import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
import time
import httpx
from contextlib import contextmanager
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from . import age as AGE
from . import services as services_mod  # 2.2 GDD v3.1: lokacje usługowe
from . import npc as npc_mod  # 2.3 GDD v3.1: NPC z 3 emocjami
from . import seasons as seasons_mod  # 5.4 GDD v3.1: miesięczne sezony Elo
from . import longplay as longplay_mod
from . import prestige as prestige_mod  # 4.5 GDD v3.1: Sala Chwały i RESET  # 3.4 GDD v3.1: kamienie milowe długiej gry
from . import assistant as assistant_mod  # 2.6 GDD v3.1: Asystent Podróży (doradca)
from . import gear as gear_mod
from . import battlepass as bp_mod
from . import economy as E, combat, features, shop, city_events, chronicle, travel, sports, pvp as pvp_mod, dungeon as dungeon_mod, sports2 as sports2_mod, sports3 as sports3_mod, avatar as AV
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
PH=PasswordHasher(time_cost=2,memory_cost=32768,parallelism=2)
DUMMY_HASH=PH.hash('unusable-'+secrets.token_urlsafe(24))
COOKIE='ce_session'

def packed(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'))
def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def fail(status,text):raise HTTPException(status,text)

class Strict(BaseModel):model_config=ConfigDict(extra='forbid',strict=True)
class Credentials(Strict):
 username:str=Field(min_length=3,max_length=24)
 password:str=Field(min_length=1,max_length=128)
 preview_session:bool=False
 consent:bool=False
 birth_date:str|None=Field(default=None,max_length=10)      # 1.8: YYYY-MM-DD (opcjonalne do Fazy B)
 guardian_email:str|None=Field(default=None,max_length=254) # 1.8: wymagany, gdy wiek < 16
class BirthDateIn(Strict):
 birth_date:str=Field(min_length=10,max_length=10)
 guardian_email:str|None=Field(default=None,max_length=254)
class GuardianVerify(Strict):
 token:str=Field(min_length=20,max_length=128)
class PreviewRequest(Strict):
 session:str=Field(min_length=1,max_length=200,repr=False)
 csrf:str=Field(default='',max_length=200,repr=False)
 method:Literal['GET','POST','PATCH']
 path:str=Field(min_length=1,max_length=120)
 payload:dict|None=None
 idempotency_key:str|None=Field(default=None,max_length=100)
class CreateCharacter(Strict):
 nickname:str=Field(min_length=3,max_length=24)
 accept_test_reset:bool=False
 class_type:str|None=Field(default=None,max_length=12)
 avatar:dict|None=None
class AvatarIn(Strict):
 avatar:dict
class WardrobeBuy(Strict):
 item:str=Field(min_length=2,max_length=12)

class ClassPick(BaseModel):
 class_type:str=Field(max_length=12)
class LocationIn(Strict):
 location:str=Field(min_length=2,max_length=24)
class Action(Strict):
 action:Literal['upgrade_buffet','collect_nightclub','auto_mechanic','refuel','contract','claim_contract','train','claim_training','buy','equip','collect','upgrade','buy_business','tutorial_dismiss','buy_residence','rest_start','rest_claim','buy_vehicle','equip_vehicle','service_vehicle','upgrade_vehicle','hire_staff','tender_accept','invest','home_train','remote_work','gather','sell_materials','upgrade_building','route_dispatch','route_claim']
 contract:str|None=None
 task_id:int|None=None
 stat:int|None=None
 item:str|None=None
 business:str|None=None
 material:str|None=None
 building:str|None=None
 route:str|None=None
 residence:str|None=None
 rest:str|None=None
 vehicle:str|None=None
 staff:str|None=None
 district:str|None=None
 amount:int|None=None

class Invite(Strict):
 target_id:int
 tactic:Literal['presja','kontrola','kontra']|None=None  # 0.41: ignorowane — taktyka zapisana na postaci
class Accept(Strict):tactic:Literal['presja','kontrola','kontra']|None=None
class Password(Strict):password:str=Field(min_length=1,max_length=128)
class Bootstrap(Strict):code:str=Field(min_length=10,max_length=150)
class Notice(Strict):
 text:str=Field(min_length=3,max_length=500)
 world_id:int|None=None
class CancelDelete(Strict):password:str
class WorldCreate(Strict):
 name:str=Field(min_length=3,max_length=40)
 kind:Literal['standard','event','test','experimental']='standard'
 opens_at:int|None=None
 registration_open:bool=True
 speed:int=Field(default=1,ge=1,le=60)
class WorldUpdate(Strict):
 registration_open:bool|None=None
 maintenance:bool|None=None
 announcement:str|None=Field(default=None,max_length=500)
class Moderate(Strict):
 banned:bool|None=None
 moderator:bool|None=None

SCHEMA='''
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY AUTOINCREMENT,username TEXT NOT NULL COLLATE NOCASE UNIQUE,password_hash TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'player',banned INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,deletion_at INTEGER,consent TEXT NOT NULL DEFAULT '',ip_hash TEXT NOT NULL DEFAULT '');
CREATE TABLE IF NOT EXISTS notices(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER REFERENCES worlds(id) ON DELETE CASCADE,text TEXT NOT NULL,author_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS daily_actions(character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,day INTEGER NOT NULL,kind TEXT NOT NULL,updated_at INTEGER NOT NULL,PRIMARY KEY(character_id,day));
CREATE TABLE IF NOT EXISTS daily_distinctions(id INTEGER PRIMARY KEY AUTOINCREMENT,character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,day INTEGER NOT NULL,kind TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS world_daily(world_id INTEGER NOT NULL REFERENCES worlds(id) ON DELETE CASCADE,day INTEGER NOT NULL,deeds INTEGER NOT NULL DEFAULT 0,cash INTEGER NOT NULL DEFAULT 0,xp INTEGER NOT NULL DEFAULT 0,shop_cents INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(world_id,day));
CREATE TABLE IF NOT EXISTS char_daily(character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,day INTEGER NOT NULL,deeds INTEGER NOT NULL DEFAULT 0,cash INTEGER NOT NULL DEFAULT 0,xp INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(character_id,day));
CREATE UNIQUE INDEX IF NOT EXISTS daily_distinction_day ON daily_distinctions(character_id,day);
CREATE TABLE IF NOT EXISTS appeals(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,text TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',resolution TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,resolved_at INTEGER,resolved_by INTEGER REFERENCES accounts(id) ON DELETE SET NULL);
CREATE TABLE IF NOT EXISTS investments(character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,district TEXT NOT NULL,total INTEGER NOT NULL,PRIMARY KEY(character_id,district));
CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY,account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,csrf TEXT NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS worlds(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT NOT NULL UNIQUE,kind TEXT NOT NULL,opens_at INTEGER NOT NULL,registration_open INTEGER NOT NULL,speed INTEGER NOT NULL DEFAULT 1,maintenance INTEGER NOT NULL DEFAULT 0,announcement TEXT NOT NULL DEFAULT '',created_at INTEGER NOT NULL,world_era INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS characters(id INTEGER PRIMARY KEY AUTOINCREMENT,account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,world_id INTEGER NOT NULL REFERENCES worlds(id),nickname TEXT NOT NULL COLLATE NOCASE,state_json TEXT NOT NULL,rating REAL NOT NULL DEFAULT 1000,wins INTEGER NOT NULL DEFAULT 0,losses INTEGER NOT NULL DEFAULT 0,draws INTEGER NOT NULL DEFAULT 0,created_at INTEGER NOT NULL,UNIQUE(account_id,world_id),UNIQUE(world_id,nickname));
CREATE TABLE IF NOT EXISTS operations(account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,world_id INTEGER NOT NULL,key TEXT NOT NULL,request_hash TEXT NOT NULL,response_json TEXT NOT NULL,created_at INTEGER NOT NULL,PRIMARY KEY(account_id,world_id,key));
CREATE TABLE IF NOT EXISTS challenges(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id),attacker_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,defender_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,attacker_snapshot TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at INTEGER NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY AUTOINCREMENT,world_id INTEGER NOT NULL REFERENCES worlds(id),challenge_id INTEGER UNIQUE REFERENCES challenges(id) ON DELETE CASCADE,attacker_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,defender_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,report_json TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,actor_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,event TEXT NOT NULL,details TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS ranked_usage(character_id INTEGER NOT NULL REFERENCES characters(id) ON DELETE CASCADE,day INTEGER NOT NULL,used INTEGER NOT NULL,PRIMARY KEY(character_id,day));
CREATE TABLE IF NOT EXISTS rate_limits(key TEXT PRIMARY KEY,count INTEGER NOT NULL,until_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS rate_limits_until ON rate_limits(until_at);
CREATE INDEX IF NOT EXISTS chars_world ON characters(world_id,rating DESC);
CREATE INDEX IF NOT EXISTS matches_world ON matches(world_id,created_at);
CREATE INDEX IF NOT EXISTS challenges_target ON challenges(defender_id,status);
'''

class Database:
 def __init__(self,path):self.path=str(path);Path(path).parent.mkdir(parents=True,exist_ok=True)
 def connect(self):
  c=sqlite3.connect(self.path,timeout=15);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=15000');return c
 @contextmanager
 def tx(self):
  c=self.connect()
  try:c.execute('BEGIN IMMEDIATE');yield c;c.commit()
  except BaseException:c.rollback();raise
  finally:c.close()
 @contextmanager
 def read(self):
  c=self.connect()
  try:yield c
  finally:c.close()

def create_app(db_path=None,clock=None,bootstrap_path=None,mode=None):
 mode=mode or os.getenv('CITY_MODE','development')
 if mode not in ('development','production'):raise RuntimeError('CITY_MODE must be development or production')
 min_password_length=4 if mode=='development' else 12
 preview_sessions=mode=='development'
 app=FastAPI(title='CITY EMPIRE development API',docs_url=None,redoc_url=None,openapi_url=None)
 db=Database(db_path or os.getenv('CITY_DB',str(ROOT/'data'/'city_empire.sqlite3')))
 now=clock or (lambda:int(time.time()*1000))
 setup_file=Path(bootstrap_path or os.getenv('CITY_SETUP_FILE',str(ROOT/'data'/'administrator-setup.txt')))
 app.state.db=db;app.state.now=now
 with db.connect() as c:
  c.execute('PRAGMA journal_mode=WAL');c.executescript(SCHEMA);c.commit()
 cols={r[1] for r in c.execute('PRAGMA table_info(accounts)')}
 for column in ('deletion_at','consent','ip_hash'):
  if column not in cols:c.execute('ALTER TABLE accounts ADD COLUMN '+column+(" INTEGER" if column=='deletion_at' else " TEXT NOT NULL DEFAULT ''"))
 # 1.8 GDD v3.1: bramka wiekowa — addytywna migracja (stare konta: NULL / 'none')
 for column,ddl in (('birth_date',' TEXT'),('guardian_email',' TEXT'),('guardian_status'," TEXT NOT NULL DEFAULT 'none'"),('guardian_token_hash',' TEXT'),('guardian_token_exp',' INTEGER')):
  if column not in cols:c.execute('ALTER TABLE accounts ADD COLUMN '+column+ddl)
 ccols={r[1] for r in c.execute('PRAGMA table_info(characters)')}
 # 0.30 Klasy i Baza: additive migracja — stare bazy dostają kolumny z bezpiecznymi defaults.
 for column,ddl in (('class_type',' TEXT'),('class_evolution',' INTEGER NOT NULL DEFAULT 1'),('current_location'," TEXT NOT NULL DEFAULT 'ulica'"),('dungeon_progress',' INTEGER NOT NULL DEFAULT 0')):
  if column not in ccols:c.execute('ALTER TABLE characters ADD COLUMN '+column+ddl)
 wcols={r[1] for r in c.execute('PRAGMA table_info(worlds)')}
 if 'world_era' not in wcols:c.execute('ALTER TABLE worlds ADD COLUMN world_era INTEGER NOT NULL DEFAULT 1')  # 0.33 Er-y świata
 # 1.6 GDD v3.1: wersja silnika w zapisanych walkach (stare wiersze = NULL → fallback)
 mcols={r[1] for r in c.execute('PRAGMA table_info(matches)')}
 if 'combat_version' not in mcols:c.execute('ALTER TABLE matches ADD COLUMN combat_version TEXT')
 c.commit()
 os.chmod(db.path,0o600)
 with db.tx() as c:
  # Backfill only absent daily ledgers for databases created by earlier development builds.
  c.execute('INSERT OR IGNORE INTO ranked_usage SELECT character_id,day,count(*) FROM (SELECT attacker_id character_id,(created_at / 86400000)*86400000 day FROM matches UNION ALL SELECT defender_id character_id,(created_at / 86400000)*86400000 day FROM matches) GROUP BY character_id,day')
  if not c.execute('SELECT 1 FROM worlds').fetchone():
   c.execute('INSERT INTO worlds(name,kind,opens_at,registration_open,speed,created_at) VALUES(?,?,?,?,?,?)',('CITY 1','standard',now(),1,1,now()))
   c.execute('INSERT INTO worlds(name,kind,opens_at,registration_open,speed,announcement,created_at) VALUES(?,?,?,?,?,?,?)',('CITY LAB','test',now(),1,60,'Serwer testowy ×60. Start: 3 000 $ i 240 energii. Postęp może zostać zresetowany po wcześniejszym komunikacie.',now()))
  if not c.execute("SELECT 1 FROM accounts WHERE role='admin'").fetchone():
   if not c.execute("SELECT 1 FROM meta WHERE key='bootstrap_hash'").fetchone() or not setup_file.exists():
    code=secrets.token_urlsafe(24);c.execute("INSERT OR REPLACE INTO meta VALUES('bootstrap_hash',?)",(digest(code),))
    setup_file.parent.mkdir(parents=True,exist_ok=True);setup_file.write_text('CITY EMPIRE — jednorazowy kod instalacyjny\n\n'+code+'\n\nZarejestruj konto, otwórz „Konto”, wpisz kod w sekcji aktywacji administratora.\nKod działa tylko raz. Nie publikuj tego pliku. Nie jest serwowany przez HTTP.\n');os.chmod(setup_file,0o600)
  else:
   c.execute("DELETE FROM meta WHERE key='bootstrap_hash'")
   if setup_file.exists():setup_file.unlink()

 @app.middleware('http')
 async def security(request,call_next):
  if request.url.path.startswith('/api/') and request.method in ('POST','PATCH','DELETE','PUT'):
   origin=request.headers.get('origin')
   hosts={request.headers.get('host','').lower(),request.headers.get('x-forwarded-host','').split(',')[0].strip().lower()}
   if origin and (origin=='null' or urlparse(origin).netloc.lower() not in hosts):return JSONResponse({'detail':'Niedozwolone źródło żądania.'},403)
   if request.headers.get('content-type','').split(';')[0]!='application/json':return JSONResponse({'detail':'Wymagany format JSON.'},415)
   if not request.headers.get('content-length','0').isdigit() or int(request.headers.get('content-length','0') or '0')>16384:return JSONResponse({'detail':'Żądanie jest zbyt duże.'},413)
  response=await call_next(request)
  response.headers['X-Content-Type-Options']='nosniff';response.headers['Referrer-Policy']='same-origin'
  if request.url.path.startswith('/api/'):response.headers['Cache-Control']='no-store'
  # Embedding is intentional for Arena's live preview. Production deployment must choose its own frame policy.
  response.headers['Content-Security-Policy']="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'"
  return response

 # 8.5 GDD v3.1: język komunikatu = język konta (ustawiany w auth) lub Accept-Language
 from . import err_i18n as ERRI
 def err_lang(request):
  from .gear import pick_lang
  return pick_lang(request.headers.get('accept-language'),getattr(request.state,'acc_lang',None))
 @app.exception_handler(E.RuleError)
 async def rule_error(request,error):return JSONResponse({'detail':ERRI.translate(str(error),err_lang(request))},409)
 @app.exception_handler(HTTPException)
 async def http_error(request,error):
  return JSONResponse({'detail':ERRI.translate(error.detail,err_lang(request))},error.status_code,headers=getattr(error,'headers',None))

 # 1.8 A3: ścieżki dostępne dla konta zablokowanego bramką wiekową (stan bramki, prawa RODO, wylogowanie)
 AGE_GATE_OPEN={'/api/me','/api/auth/logout','/api/account/birth-date','/api/guardian/resend','/api/account/export','/api/account/delete','/api/account/delete/cancel'}
 def auth(request:Request):
  authorization=request.headers.get('authorization','')
  scheme,_,token=authorization.partition(' ')
  # X-City-Session: własny nagłówek podglądu (proxy podglądu potrafi podmienić Authorization)
  custom=request.headers.get('x-city-session','')
  if custom:
   if not preview_sessions or len(custom)>200:fail(401,'Zaloguj się ponownie.')
   token=custom
  elif authorization:
   if not preview_sessions or scheme.lower()!='bearer' or not token or len(token)>200:fail(401,'Zaloguj się ponownie.')
  else:token=request.cookies.get(COOKIE,'')
  with db.read() as c:
   row=c.execute('SELECT a.*,s.csrf,s.token_hash,s.last_seen FROM sessions s JOIN accounts a ON a.id=s.account_id WHERE token_hash=? AND expires_at>?',(digest(token),now())).fetchone()
  if not row:fail(401,'Zaloguj się ponownie.')
  request.state.acc_lang=row['language'] if 'language' in row.keys() else None
  if row['banned']:fail(403,'Konto zostało zawieszone.')
  if request.url.path not in AGE_GATE_OPEN:
   if row['guardian_status']=='pending':fail(403,'Czekamy na zgodę rodzica lub opiekuna — sprawdźcie e-mail. Do tego czasu konto jest wstrzymane.')
   if AGE.require_birth_date() and not row['birth_date']:fail(403,'Uzupełnij datę urodzenia, aby kontynuować.')
  if request.method not in ('GET','HEAD') and not hmac.compare_digest(request.headers.get('x-csrf-token',''),row['csrf']):fail(403,'Nieprawidłowy token ochrony żądania.')
  if row['last_seen']<now()-60000:
   with db.tx() as c:c.execute('UPDATE sessions SET last_seen=? WHERE token_hash=?',(now(),row['token_hash']))
  return dict(row)
 def admin(user=Depends(auth)):
  if user['role']!='admin':fail(403,'Wymagane uprawnienia administratora.')
  return user
 def staff(user=Depends(auth)):
  if user['role'] not in ('admin','moderator'):fail(403,'Wymagane uprawnienia moderatora.')
  return user
 def rate(request,scope,limit,window,username=''):
  # Only immediate peer address; no trust in client-supplied forwarded IP headers.
  key=digest(scope+'|'+(request.client.host if request.client else 'unknown')+'|'+username.lower())
  with db.tx() as c:
   old=c.execute('SELECT * FROM rate_limits WHERE key=?',(key,)).fetchone()
   if old and old['until_at']>now():
    if old['count']>=limit:fail(429,'Zbyt wiele prób. Spróbuj później.')
    c.execute('UPDATE rate_limits SET count=count+1 WHERE key=?',(key,))
   else:c.execute('INSERT OR REPLACE INTO rate_limits VALUES(?,?,?)',(key,1,now()+window))
 def user_public(u):return dict(id=u['id'],username=u['username'],role=u['role'],created_at=u['created_at'],deletion_at=u['deletion_at'])
 def issue(c,uid,request,preview_requested=False):
  token=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24)
  c.execute('DELETE FROM sessions WHERE expires_at<=?',(now(),))
  c.execute('INSERT INTO sessions(token_hash,account_id,csrf,expires_at,sid,created_at,last_seen) VALUES(?,?,?,?,?,?,?)',(digest(token),uid,csrf,now()+7*24*E.HOUR,secrets.token_hex(12),now(),now()))
  u=c.execute('SELECT * FROM accounts WHERE id=?',(uid,)).fetchone()
  body=dict(user=user_public(u),csrf=csrf)
  # Explicit development-only transport for embedded previews that block cookies.
  # Never return this token from /me, exports, URLs or production-mode login.
  if preview_sessions and (preview_requested or request.headers.get('x-city-preview-session')=='1'):body['previewSessionToken']=token
  response=JSONResponse(body)
  secure=request.url.scheme=='https' or request.headers.get('x-forwarded-proto','').split(',')[0]=='https'
  response.set_cookie(COOKIE,token,httponly=True,secure=secure,samesite='none' if secure else 'lax',max_age=7*86400,path='/')
  if secure:response.headers['set-cookie']=response.headers['set-cookie']+'; Partitioned'
  return response
 def clear_cookie(response,request):
  secure=request.url.scheme=='https' or request.headers.get('x-forwarded-proto','').split(',')[0]=='https'
  response.delete_cookie(COOKIE,path='/',httponly=True,secure=secure,samesite='none' if secure else 'lax')
  if secure:response.headers['set-cookie']+='; Partitioned'
  return response
 def world(c,wid,play=False):
  w=c.execute('SELECT * FROM worlds WHERE id=?',(wid,)).fetchone()
  if not w:fail(404,'Nie ma takiego świata.')
  if play and (w['opens_at']>now() or w['maintenance']):fail(409,'Świat nie jest teraz dostępny do gry.')
  return dict(w)
 own_hooks={}  # 3.4 GDD v3.1: haki wołane przy każdym żądaniu świata (licznik dni aktywności)
 def own(c,uid,wid):
  ch=c.execute('SELECT * FROM characters WHERE account_id=? AND world_id=?',(uid,wid)).fetchone()
  if not ch:fail(404,'Najpierw utwórz postać na tym świecie.')
  if 'touch' in own_hooks and own_hooks['touch'](c,dict(ch)):  # nagroda zmieniła stan → świeży wiersz
   ch=c.execute('SELECT * FROM characters WHERE id=?',(ch['id'],)).fetchone()
  return dict(ch)
 def state_of(c,ch,w):
  s=json.loads(ch['state_json']);E.sync(s,now(),w['speed']);c.execute('UPDATE characters SET state_json=? WHERE id=?',(packed(s),ch['id']));return s
 def state_response(c,u,wid,message=None):
  w=world(c,wid,True);ch=own(c,u['id'],wid);s=state_of(c,ch,w);travel_api['lazy'](c,ch['id'],now())
  away=None
  if now()-s.get('lastAction',now())>round(30*E.MINUTE/w['speed']):
   away=dict(minutes=max(0,round((now()-s['lastAction'])/60000)),
    contracts=[t['id'] for t in s['contracts'] if t['end']<=now()],
    training=sum(1 for t in s['training'] if t['end']<=now()),
    vault=int(s['business']['vault'])+sum(int((s['ventures'][k] or {}).get('vault',0)) for k in s['ventures'])+sum(int(x) for x in (s.get('vaults') or {}).values()),  # 4.2: skarbce budynków
    rest=bool(s.get('rest') and s['rest']['end']<=now()),
    energy=int(s['energy']))
   s['lastAction']=now();c.execute('UPDATE characters SET state_json=? WHERE id=?',(packed(s),ch['id']))
  day=E.day_of(now())
  totals=dict(c.execute('SELECT i.district,sum(i.total) FROM investments i JOIN characters ch ON ch.id=i.character_id WHERE ch.world_id=? GROUP BY i.district',(wid,)).fetchall())
  districts=[dict(name=d,mine=s['invested'].get(d,0),world=int(totals.get(d,0) or 0),bonus=E.invest_bonus(s,d)) for d in E.DISTRICTS]
  notices=[dict(r) for r in c.execute('SELECT n.id,n.text,n.world_id,n.created_at FROM notices n WHERE n.created_at>? AND (n.world_id IS NULL OR n.world_id=?) ORDER BY n.id DESC LIMIT 10',(now()-7*24*E.HOUR,wid))]
  eventsUnread=c.execute('SELECT count(*) FROM game_events WHERE character_id=? AND read_at IS NULL',(ch['id'],)).fetchone()[0]
  eventsRecent=[dict(id=r['id'],kind=r['kind'],payload=json.loads(r['payload'] or '{}'),created_at=r['created_at'],read=r['read_at'] is not None) for r in c.execute('SELECT id,kind,payload,created_at,read_at FROM game_events WHERE character_id=? ORDER BY id DESC LIMIT 8',(ch['id'],))]  # 0.59 Chmurka
  holders={r['district']:dict(tag=r['tag'],name=r['name'],since=r['since']) for r in c.execute('SELECT t.district,t.since,o.tag,o.name FROM territory_state t JOIN organizations o ON o.id=t.org_id WHERE t.world_id=?',(wid,)).fetchall()}  # 0.45: kto rządzi dzielnicą
  # 2.1c GDD v3.1: surowce wycofane — materials/matBuy/matBase puste, zgodność ze starym UI
  return dict(territory=holders,eventsRecent=eventsRecent,timedEvent=E.timed_event(now()),state=s,character={**{k:ch[k] for k in ('id','nickname','rating','wins','losses','draws')},'classType':ch['class_type'],'classEvolution':ch['class_evolution'],'currentLocation':ch['current_location'],'dungeonProgress':ch['dungeon_progress'],'evolutionCode':s.get('evolutionCode'),'evolution2Code':s.get('evolution2Code'),'tactic':combat.class_tactic(E.effective(s),ch['class_type']),'pvpLevel':combat.pvp_level(ch['wins'],ch['losses'],ch['draws']),'evolution':combat.evolution_status(ch['class_type'],ch['wins'],ch['losses'],ch['draws'],s.get('evolutionCode'),s.get('evolution2Code'))},titles=[dict(code=r['code'],label=r['label']) for r in c.execute('SELECT code,label FROM character_titles WHERE character_id=? ORDER BY id DESC LIMIT 12',(ch['id'],))],distinction=E.distinction_state(c,ch['id'],now()),travelInfo=travel_api['info'](c,ch['id']),dungeon=dungeon_api['payload'](c,ch,s),racing=sports_api['payload'](c,u,wid),activity=[dict(r) for r in c.execute('SELECT day,deeds,cash,xp FROM char_daily WHERE character_id=? ORDER BY day DESC LIMIT 14',(ch['id'],))],world=w,serverTime=now(),away=away,notices=notices,eventsUnread=eventsUnread,dmUnread=c.execute('SELECT count(*) FROM dm_messages WHERE world_id=? AND recipient_id=? AND read_at IS NULL',(wid,ch['id'])).fetchone()[0],cityEvent=city_api['current'](c,wid),era=city_api['era'](c,wid),chronicle=chron_api['feed'](c,wid),shop=shop_api['summary'](c,u['id']),catalog=dict(items=E.ITEMS+E.DUNGEON_ITEMS,gameLooks=AV.GAME_LOOKS,ventures=list(E.VENTURES.values()),contracts=[{**x,'duration':round(x['duration']/w['speed']),'mult':E.price_mult(wid,x['id'],day),'hop':E.hop_bonus(x)} for x in E.CONTRACTS],trainingDuration=0,gymCosts=[E.gym_cost(s,i) for i in range(5)],upgradeDuration=round(10*E.MINUTE/w['speed']),residences=E.RESIDENCES,rests=[{**r,'duration':round(r['duration']/w['speed'])} for r in E.RESTS],regenPerHour=E.regen(s)*w['speed'],vehicles=E.GARAGE,staffOffers=[dict(slot=k,**v) for k,v in E.STAFF.items()],prices={x['id']:E.price_mult(wid,x['id'],day) for x in E.CONTRACTS},tender=E.daily_tender(wid,ch['id'],day),materials={},matBuy={},matBase={},buildings=E.BUILDINGS,buildingMax=E.BUILDING_MAX,buildingCosts=E.BUILDING_UPGRADE_COST,buildingMaxes=E.BUILDING_MAXES,buildingCostsBy=E.BUILDING_COSTS,buildingVaults=E.BUILDING_VAULTS,hallCost=E.HALL_UNLOCK_COST,npcRoutes=[{**x,'duration':round(x['minutes']*E.MINUTE/w['speed'])} for x in E.NPC_ROUTES],routeVehMult=E.VEH_MULT,allyBuildings=E.ALLY_BUILDINGS,allyMax=E.ALLY_MAX,allyCost=E.ALLY_COST,districts=districts,investStep=E.INVEST_STEP,investCap=E.INVEST_CAP),message=message)
 def audit(c,uid,event,details):c.execute('INSERT INTO audit(actor_id,event,details,created_at) VALUES(?,?,?,?)',(uid,event,packed(details),now()))
 def check_tactic(t):
  if t not in combat.BEATS:fail(422,'Nieznana taktyka.')
 RANKED_DAILY=15  # 5.3 GDD v3.1: wspólny limit walk rankingowych (wyzwania 1.0 + PvP 2.0) na dobę UTC
 PAIR_MAX=4       # 5.3 (spec rev. 2): z tym samym przeciwnikiem najwyżej 4 walki w oknie 24 h (5. zablokowana)
 def daily_limit(c,cid):
  season_api['ensure'](c)  # 5.4: przed walką rankingową zamknij zakończony sezon Elo (leniwie)
  day=now()//(24*E.HOUR)*(24*E.HOUR)
  row=c.execute('SELECT used FROM ranked_usage WHERE character_id=? AND day=?',(cid,day)).fetchone()
  if row and row['used']>=RANKED_DAILY:fail(409,f'Wykorzystano {RANKED_DAILY} walk rankingowych na dobę UTC.')
 def pair_limit(c,a,b):
  since=now()-24*E.HOUR;q='SELECT count(*) FROM {} WHERE ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?)) AND created_at>?'
  n=sum(c.execute(q.format(t),(a,b,b,a,since)).fetchone()[0] for t in ('matches','pvp_battles'))
  if n>=PAIR_MAX:fail(409,f'Z tym przeciwnikiem walczysz najwyżej {PAIR_MAX} razy na 24 godziny — wybierz kogoś innego.')

 @app.get('/')
 def index():return FileResponse(ROOT/'web'/'index.html',headers={'Cache-Control':'no-cache'})
 @app.get('/art/{name}')
 def art(name:str):
  import re as _re
  if not _re.fullmatch(r'[a-z0-9][a-z0-9._-]*',name) or not name.endswith(('.jpg','.png','.webp')):fail(404,'Brak pliku.')
  f=ROOT/'web'/'art'/name
  if not f.is_file():fail(404,'Brak pliku.')
  return FileResponse(f,headers={'Cache-Control':'public, max-age=86400'})
 @app.get('/api/health')
 def health():return dict(status='ok',version='0.59.0',database='sqlite',serverTime=now())
 @app.get('/api/auth/config')
 def auth_config():return dict(mode=mode,minPasswordLength=min_password_length,previewSessions=preview_sessions,previewTransport='json-v1' if preview_sessions else None)
 @app.post('/api/preview/request')
 async def preview_request(data:PreviewRequest,request:Request):
  # A development-only, closed RPC envelope for preview proxies that remove
  # Cookie / Authorization / custom request headers. Never an external HTTP proxy.
  if not preview_sessions:fail(404,'Nie znaleziono zasobu.')
  routes={
   'GET':r'/(?:me|shop|shop/prices|i18n/(?:pl|en|de|fr)|worlds|account/(?:export|security|profile|rankings)|avatar/catalog|admin/(?:overview|reports|backups|worlds/[1-9][0-9]*/summary)|staff/appeals|worlds/[1-9][0-9]*/(?:state|services|npcs|assistant|milestones|players|elo-season|rankings|dungeon/history|dungeon/runs/[1-9][0-9]*|gear|gear/shop|dashboard|battlepass|federations|monuments|pvp|pvp/targets|community|sports2|sports3|racing/open|organizations/[1-9][0-9]*|chat/(?:world|organization)|dm|dm/[1-9][0-9]*)|matches/[1-9][0-9]*|ranking/global/season/[1-9][0-9]*|ranking/global/[1-9][0-9]*)',
   'POST':r'/(?:auth/logout|account/language|worlds/[1-9][0-9]*/battlepass/(?:premium|claim)|worlds/[1-9][0-9]*/federations(?:/invite|/leave|/[1-9][0-9]*/accept)?|worlds/[1-9][0-9]*/gear/(?:equip|unequip|bag/unlock|craft|shop/buy|coupon/use)|worlds/[1-9][0-9]*/npcs/(?:recruit|batch|manager|feed|[1-9][0-9]*/(?:dispatch|recall|feed|role|taxi))|worlds/[1-9][0-9]*/services/[a-z]+/unlock|worlds/[1-9][0-9]*/server_reset|setup/claim|guardian/(?:verify|resend)|account/(?:birth-date|delete|delete/cancel|password|sessions/revoke|blocks/remove|appeals)|admin/(?:worlds|backups|notices|notices/[1-9][0-9]*/delete|events|events/[1-9][0-9]*/cancel|reports/[1-9][0-9]*/resolve)|staff/appeals/[1-9][0-9]*/resolve|organization-invites/[1-9][0-9]*/(?:accept|decline)|org-applications/[1-9][0-9]*/(?:accept|decline)|shop/(?:gate|checkout|equip|guardian|guardian/revoke)|worlds/[1-9][0-9]*/(?:character(?:/evolve)?|actions|challenges|class|distinction/claim|travel(?:/(?:arrive|speedup))?|location|avatar|wardrobe|dungeon/floor|racing(?:/(?:horse|npc|open|join/[1-9][0-9]*|cancel/[1-9][0-9]*|breed|stable))?|sports/(?:tournament|agility|archery|swim|riding|dog/(?:buy|pick|train))|pvp(?:/(?:defense|evolve|attack/[1-9][0-9]*))?|organizations(?:/(?:invite|building|leave|transfer|remove-member|apply|fund|invest|announcement|role|contract(?:/cancel)?))?|chat/(?:world|organization)|dm/[1-9][0-9]*|events/read|reports|blocks)|challenges/[1-9][0-9]*/(?:accept|decline))',
   'PATCH':r'/admin/(?:worlds|accounts)/[1-9][0-9]*',
  }
  if not re.fullmatch(routes[data.method],data.path):fail(404,'Nieobsługiwana operacja podglądu.')
  if data.method=='GET' and data.payload is not None:fail(422,'Odczyt nie przyjmuje danych operacji.')
  # Feed the existing endpoints, not a second implementation of game rules.
  # Their authentication, CSRF, roles, validation and database transactions still apply.
  headers={'Authorization':'Bearer '+data.session,'X-CSRF-Token':data.csrf}
  if data.idempotency_key is not None:headers['Idempotency-Key']=data.idempotency_key
  secure=request.url.scheme=='https' or request.headers.get('x-forwarded-proto','').split(',')[0]=='https'
  transport=httpx.ASGITransport(app=app,client=(request.client.host if request.client else 'unknown',request.client.port if request.client else 0))
  async with httpx.AsyncClient(transport=transport,base_url=('https' if secure else 'http')+'://city-internal') as client:
   result=await client.request(data.method,'/api'+data.path,headers=headers,**({'json':data.payload or {}} if data.method!='GET' else {}))
  response=JSONResponse(result.json(),status_code=result.status_code)
  if 'set-cookie' in result.headers:response.headers['set-cookie']=result.headers['set-cookie']
  return response
 @app.get('/api/setup/status')
 def setup_status():
  with db.read() as c:return dict(needsAdmin=not bool(c.execute("SELECT 1 FROM accounts WHERE role='admin'").fetchone()))
 @app.post('/api/auth/register')
 def register(data:Credentials,request:Request):
  rate(request,'register',8,15*E.MINUTE)
  username=data.username.strip().lower()
  if not re.fullmatch(r'[a-z0-9_-]{3,24}',username):fail(422,'Login: 3–24 litery a–z, cyfry, _ lub -.')
  if len(data.password)<min_password_length:fail(422,'Hasło musi mieć co najmniej 4 znaki (tryb testowy).' if preview_sessions else 'Hasło musi mieć co najmniej 12 znaków.')
  if not data.consent:fail(422,'Potwierdź, że masz 16 lat albo posiadasz zgodę rodzica lub opiekuna.')
  birth=None;minor=False;today=AGE.today_from_ms(now())
  if data.birth_date:
   try:birth=AGE.parse_birth(data.birth_date,today)
   except ValueError as e:fail(422,str(e))
   years=AGE.age_on(birth,today)
   if years<AGE.MIN_AGE:fail(422,'Gra jest dostępna od '+str(AGE.MIN_AGE)+' lat.')
   minor=years<AGE.CONSENT_AGE
   if minor and not (data.guardian_email and AGE.EMAIL_RE.match(data.guardian_email.strip())):fail(422,'Masz mniej niż 16 lat — podaj e-mail rodzica lub opiekuna, wyślemy prośbę o zgodę.')
  elif AGE.require_birth_date():fail(422,'Podaj datę urodzenia.')
  # Storage-minimised abuse guard: only a one-way hash of the address, never the address itself.
  ip=digest('ip|'+(request.client.host if request.client else 'unknown'))
  hashed=PH.hash(data.password)
  with db.tx() as c:
   if c.execute('SELECT 1 FROM accounts WHERE username=?',(username,)).fetchone():fail(409,'Nie można użyć tego loginu.')
   # limit kont na IP; CITY_MAX_ACCOUNTS_PER_IP=0 wyłącza (serwer testowy za proxy podglądu = jedno IP)
   _lim=int(os.environ.get('CITY_MAX_ACCOUNTS_PER_IP','8'))
   if _lim>0 and c.execute('SELECT count(*) FROM accounts WHERE ip_hash=?',(ip,)).fetchone()[0]>=_lim:fail(409,f'Limit {_lim} kont dla tego urządzenia lub sieci został osiągnięty.')
   token=th=None
   if minor:token,th=AGE.new_token()
   uid=c.execute('INSERT INTO accounts(username,password_hash,created_at,consent,ip_hash,birth_date,guardian_email,guardian_status,guardian_token_hash,guardian_token_exp) VALUES(?,?,?,?,?,?,?,?,?,?)',
    (username,hashed,now(),('guardian' if minor else '16+') if data.consent else '',ip,birth.isoformat() if birth else None,
     data.guardian_email.strip().lower() if minor else None,'pending' if minor else 'none',th,now()+AGE.TOKEN_DAYS*86400000 if minor else None)).lastrowid
   if minor:audit(c,uid,'guardian.requested',dict(token_exp_days=AGE.TOKEN_DAYS))  # bez e-maila i tokenu w audycie
   result=issue(c,uid,request,data.preview_session)
  if minor:app.state.mailer.send_guardian(data.guardian_email.strip().lower(),username,token)  # po commicie transakcji
  return result
 @app.post('/api/auth/login')
 def login(data:Credentials,request:Request):
  rate(request,'login-ip',40,15*E.MINUTE);rate(request,'login-user',10,15*E.MINUTE,data.username)
  with db.read() as c:u=c.execute('SELECT * FROM accounts WHERE username=?',(data.username.strip().lower(),)).fetchone()
  try:valid=PH.verify(u['password_hash'] if u else DUMMY_HASH,data.password)
  except VerificationError:valid=False
  if not u or not valid:fail(401,'Nieprawidłowy login lub hasło.')
  if u['banned']:fail(403,'Konto zostało zawieszone.')
  with db.tx() as c:return issue(c,u['id'],request,data.preview_session)
 def age_gate(u):
  # 1.8: stan bramki dla klienta (bez daty urodzenia i e-maila — minimalizacja danych)
  st=u['guardian_status'] or 'none'
  return dict(needsBirthDate=not u['birth_date'],required=AGE.require_birth_date(),guardianStatus=st,guardianExpiresAt=u['guardian_token_exp'] if st=='pending' else None)
 @app.get('/api/me')
 def me(u=Depends(auth)):return dict(user=user_public(u),csrf=u['csrf'],serverTime=now(),ageGate=age_gate(u))
 @app.post('/api/account/birth-date')
 def set_birth_date(data:BirthDateIn,request:Request,u=Depends(auth)):
  # 1.8 A2: jednorazowe uzupełnienie daty urodzenia dla kont sprzed bramki wiekowej
  rate(request,'birth-date',5,3600000,u['username'])
  if u['birth_date']:fail(409,'Data urodzenia została już podana — zmiana tylko przez pomoc techniczną.')
  today=AGE.today_from_ms(now())
  try:birth=AGE.parse_birth(data.birth_date,today)
  except ValueError as e:fail(422,str(e))
  years=AGE.age_on(birth,today)
  if years<AGE.MIN_AGE:
   # RODO: danych dziecka < 12 nie przetwarzamy dalej — natychmiastowe usunięcie konta (purge_due)
   with db.tx() as c:
    c.execute('UPDATE accounts SET deletion_at=? WHERE id=?',(now(),u['id']))
    audit(c,u['id'],'guardian.rejected_underage',dict(min_age=AGE.MIN_AGE))
   app.state.purge()
   fail(422,'Gra jest dostępna od '+str(AGE.MIN_AGE)+' lat. Konto zostało usunięte.')
  minor=years<AGE.CONSENT_AGE
  email=(data.guardian_email or '').strip().lower()
  if minor and not AGE.EMAIL_RE.match(email):fail(422,'Masz mniej niż 16 lat — podaj e-mail rodzica lub opiekuna, wyślemy prośbę o zgodę.')
  token=th=None
  if minor:token,th=AGE.new_token()
  with db.tx() as c:
   c.execute('UPDATE accounts SET birth_date=?,guardian_email=?,guardian_status=?,guardian_token_hash=?,guardian_token_exp=? WHERE id=? AND birth_date IS NULL',
    (birth.isoformat(),email if minor else None,'pending' if minor else 'none',th,now()+AGE.TOKEN_DAYS*86400000 if minor else None,u['id']))
   audit(c,u['id'],'account.birth_date',dict(minor=minor))
  if minor:app.state.mailer.send_guardian(email,u['username'],token)
  return dict(ok=True,guardianStatus='pending' if minor else 'none')
 @app.post('/api/guardian/resend')
 def guardian_resend(request:Request,u=Depends(auth)):
  # 1.8 A3: ponowna wysyłka (opiekun zgubił e-mail) — nowy token unieważnia stary, termin 7 dni NIE jest przedłużany
  if u['guardian_status']!='pending':fail(409,'Konto nie czeka na zgodę opiekuna.')
  rate(request,'guardian-resend',3,24*3600000,u['username'])
  token,th=AGE.new_token()
  with db.tx() as c:
   c.execute("UPDATE accounts SET guardian_token_hash=? WHERE id=? AND guardian_status='pending'",(th,u['id']))
   audit(c,u['id'],'guardian.resent',{})
  app.state.mailer.send_guardian(u['guardian_email'],u['username'],token)
  return dict(ok=True,guardianExpiresAt=u['guardian_token_exp'])
 @app.post('/api/guardian/verify')
 def guardian_verify(data:GuardianVerify,request:Request):
  # 1.8 A2: publiczny — opiekun nie ma konta w grze; odpowiedź nie zdradza, czy konto istnieje
  rate(request,'guardian-verify',10,15*E.MINUTE)
  with db.tx() as c:
   row=c.execute("SELECT id FROM accounts WHERE guardian_token_hash=? AND guardian_status='pending' AND guardian_token_exp>?",(AGE.token_hash(data.token),now())).fetchone()
   if not row:fail(404,'Link jest nieważny lub wygasł.')
   c.execute("UPDATE accounts SET guardian_status='verified',guardian_token_hash=NULL,guardian_token_exp=NULL WHERE id=?",(row['id'],))
   audit(c,row['id'],'guardian.verified',{})
  return dict(ok=True,message='Dziękujemy — zgoda zapisana. Konto dziecka jest aktywne.')
 @app.post('/api/auth/logout')
 def logout(request:Request,u=Depends(auth)):
  with db.tx() as c:c.execute('DELETE FROM sessions WHERE token_hash=?',(u['token_hash'],))
  return clear_cookie(JSONResponse({'ok':True}),request)
 @app.post('/api/setup/claim')
 def claim_admin(data:Bootstrap,request:Request,u=Depends(auth)):
  rate(request,'bootstrap',5,30*E.MINUTE)
  with db.tx() as c:
   entry=c.execute("SELECT value FROM meta WHERE key='bootstrap_hash'").fetchone()
   if not entry or c.execute("SELECT 1 FROM accounts WHERE role='admin'").fetchone() or not hmac.compare_digest(digest(data.code.strip()),entry['value']):fail(403,'Kod instalacyjny jest nieprawidłowy albo został już użyty.')
   c.execute("UPDATE accounts SET role='admin' WHERE id=?",(u['id'],));c.execute("DELETE FROM meta WHERE key='bootstrap_hash'");audit(c,u['id'],'bootstrap.claim',{})
  if setup_file.exists():setup_file.unlink()
  return {'ok':True}

 @app.get('/api/worlds')
 def worlds(u=Depends(auth)):
  with db.read() as c:
   worlds_=[dict(r) for r in c.execute('SELECT * FROM worlds ORDER BY opens_at,id')]
   chars={r['world_id']:dict(id=r['id'],nickname=r['nickname'],avatar=AV.brief(json.loads(r['state_json']))) for r in c.execute('SELECT id,world_id,nickname,state_json FROM characters WHERE account_id=?',(u['id'],))}
   for w in worlds_:w['character']=chars.get(w['id']);w['planned']=w['opens_at']>now();w['era']=city_events.era_of(w,now())  # 0.34 kalendarz Er na karcie świata
  return {'worlds':worlds_,'serverTime':now()}
 @app.post('/api/worlds/{wid}/character')
 def create_character(wid:int,data:CreateCharacter,u=Depends(auth)):
  nickname=data.nickname.strip()
  if not re.fullmatch(r'[\w -]{3,24}',nickname,flags=re.UNICODE):fail(422,'Nazwa postaci: litery, cyfry, spacje, _ lub -, od 3 do 24 znaków.')
  with db.tx() as c:
   w=world(c,wid,True)
   if not w['registration_open']:fail(409,'Rejestracja postaci na tym świecie jest zamknięta.')
   if w['kind'] in ('test','experimental') and not data.accept_test_reset:fail(422,'Potwierdź zasady serwera testowego.')
   if c.execute('SELECT 1 FROM characters WHERE account_id=? AND world_id=?',(u['id'],wid)).fetchone():fail(409,'Masz już postać na tym świecie.')
   if c.execute('SELECT 1 FROM characters WHERE world_id=? AND nickname=?',(wid,nickname)).fetchone():fail(409,'Ta nazwa jest zajęta na tym świecie.')
   ct=(data.class_type or '').strip().lower() or None
   if ct is not None and ct not in E.CLASSES:fail(422,'Klasa: wybierz bokser, obronca albo szybki.')
   s=E.new(now(),w['kind'] in ('test','experimental'),E.CLASSES[ct]['stats'] if ct else None)  # null=legacy 10/10/10/10/10; UI 0.41 wymusza wybór (radio required)
   vip=shop_api['vip_until'](c,u['id'])
   if vip>now():s['vipUntil']=vip
   if data.avatar:  # 0.46: wygląd awatara wybrany w kreatorze (rzeczy zwykłe gratis, VIP tylko z aktywnym VIP)
    clean,err=AV.validate(data.avatar,vip>now(),set(),True)
    if err:fail(422,err)
    s['avatar']={'body':clean['body'],'worn':clean['worn'],'owned':clean['new_owned']}
   c.execute('INSERT INTO characters(account_id,world_id,nickname,state_json,created_at,class_type,class_evolution,current_location,dungeon_progress) VALUES(?,?,?,?,?,?,1,?,0)',(u['id'],wid,nickname,packed(s),now(),ct,'ulica'))
   return state_response(c,u,wid,'Utworzono postać. Witaj w mieście!')
 @app.post('/api/worlds/{wid}/class')
 def pick_class(wid:int,data:ClassPick,request:Request,u=Depends(auth)):
  rate(request,'class-'+str(u['id']),10,3600000)
  ct=(data.class_type or '').strip().lower()
  if ct not in E.CLASSES:fail(422,'Klasa: wybierz bokser, obronca albo szybki.')
  with db.tx() as c:
   w=world(c,wid,True);ch=own(c,u['id'],wid)
   if ch['class_type']:fail(409,'Klasa jest już wybrana — decyzja jest jednorazowa i nieodwracalna.')
   s=json.loads(ch['state_json'])  # 0.43: klasa przeniesiona z kreacji do pierwszego wejścia w PvP
   s['stats']=[max(1,cur-10+cls) for cur,cls in zip(s['stats'],E.CLASSES[ct]['stats'])]
   c.execute('UPDATE characters SET class_type=?,state_json=? WHERE id=?',(ct,packed(s),ch['id']))
   audit(c,u['id'],'class.pick',dict(cls=ct))
   return dict(ok=True,classType=ct,stats=s['stats'],message='Karta zawodnika wydana: '+E.CLASSES[ct]['label']+'. Wybór jednorazowy.')
 @app.post('/api/worlds/{wid}/location')
 def move_location(wid:int,data:LocationIn,request:Request,u=Depends(auth)):
  rate(request,'location-'+str(u['id']),60,3600000)
  loc=data.location.strip().lower()
  if loc not in E.LOCATIONS:fail(422,'Nieznana lokacja. Dozwolone: '+', '.join(sorted(E.LOCATIONS))+'.')
  with db.tx() as c:
   world(c,wid,True);ch=own(c,u['id'],wid)
   if ch['current_location']==loc:return dict(ok=True,currentLocation=loc,message='Już jesteś w lokacji: '+E.LOCATIONS[loc]+'.')
   c.execute('UPDATE characters SET current_location=? WHERE id=?',(loc,ch['id']))
   audit(c,u['id'],'location.move',dict(frm=ch['current_location'],to=loc))
   return dict(ok=True,currentLocation=loc,message='Przeszedłeś do lokacji: '+E.LOCATIONS[loc]+'.')
 @app.get('/api/worlds/{wid}/state')
 def get_state(wid:int,u=Depends(auth)):
  with db.tx() as c:return state_response(c,u,wid)
 @app.post('/api/worlds/{wid}/actions')
 def actions(wid:int,data:Action,request:Request,u=Depends(auth)):
  key=request.headers.get('idempotency-key','')
  if not re.fullmatch(r'[A-Za-z0-9_-]{16,100}',key):fail(422,'Brak poprawnego identyfikatora operacji.')
  payload=data.model_dump(exclude_none=True);fingerprint=digest(packed(payload))
  with db.tx() as c:
   old=c.execute('SELECT * FROM operations WHERE account_id=? AND world_id=? AND key=?',(u['id'],wid,key)).fetchone()
   if old:
    if old['request_hash']!=fingerprint:fail(409,'Identyfikator został użyty dla innej operacji.')
    return json.loads(old['response_json'])
   w=world(c,wid,True);ch=own(c,u['id'],wid);s=json.loads(ch['state_json']);cash0=s['cash'];xp0=s['xp']
   veteran=bool(ch['created_at']<=now()-7*E.DAY_MS or w['created_at']<=now()-7*E.DAY_MS)  # 0.26 brama 7 dni: postać ALBO świat
   was_remote=data.action=='claim_contract' and any(t['id']==data.task_id and t.get('contract')=='remote' for t in s['contracts'])
   sv=c.execute('SELECT vip_until FROM shop_state WHERE account_id=?',(u['id'],)).fetchone()
   vip=bool(sv and sv['vip_until']>now())
   s['ally']=E.ally_levels(c,ch['id'])
   s['npcCars']=npc_api['cars'](c,ch['id'],now())  # 2.4c GDD v3.1: auta na zmianie NPC (tylko w pamięci)
   message=E.action(s,data.action,payload,now(),w['speed'],wid=wid,cid=ch['id'],district=ch['current_district'] or 1,traveling=bool(ch['travel_destination']),veteran=veteran,era=city_api['era_n'](c,wid),vip=vip)
   deed={'claim_contract':'remote' if was_remote else 'contract','claim_training':'training','train':'training','collect':'collect','rest_claim':'rest'}.get(data.action)
   gear_api['after_action'](s,data.action,xp0,cash0,now())
   if data.action=='upgrade_building' and E.BP_HOOK[0]:E.BP_HOOK[0](c,ch['id'],'build')  # 8.4: XP przepustki za rozbudowę  # 7.5: kupony XP / Kontrakt
   if deed:E.mark_daily(c,ch['id'],deed,now())
   if data.action in ('claim_contract','claim_training','train','collect','rest_claim'):E.bump(c,wid,ch['id'],now(),deeds=1,cash=(s['cash']-cash0 if data.action not in ('claim_training','train') else 0),xp=(s['xp']-xp0 if data.action=='claim_contract' else 0))
   if data.action=='buy_vehicle' and s.get('vehicle'):
    g=next((g for g in E.GARAGE if g['id']==s['vehicle']['id']),None)
    c.execute('INSERT INTO vehicles(character_id,type,condition,speed_bonus) SELECT ?,?,?,? WHERE NOT EXISTS(SELECT 1 FROM vehicles WHERE character_id=? AND type=?)',(ch['id'],s['vehicle']['id'],100-int(s['vehicle'].get('wear',0)),g['discount'] if g else 0,ch['id'],s['vehicle']['id']))
   if data.action=='service_vehicle' and (payload.get('vehicle') or s.get('vehicle')):c.execute('UPDATE vehicles SET condition=100 WHERE character_id=? AND type=?',(ch['id'],payload.get('vehicle') or s['vehicle']['id']))  # 3.3: wskazane auto
   if data.action=='auto_mechanic':c.execute('UPDATE vehicles SET condition=100 WHERE character_id=?',(ch['id'],))  # 3.3
   if data.action=='invest':c.execute('INSERT INTO investments(character_id,district,total) VALUES(?,?,?) ON CONFLICT(character_id,district) DO UPDATE SET total=excluded.total',(ch['id'],payload['district'],s['invested'][payload['district']]))
   s.pop('npcCars',None)
   c.execute('UPDATE characters SET state_json=? WHERE id=?',(packed(s),ch['id']));result=state_response(c,u,wid,message)
   c.execute('INSERT INTO operations VALUES(?,?,?,?,?,?)',(u['id'],wid,key,fingerprint,packed(result),now()))
   return result
 # 5.1 GDD v3.1: endpoint POST /api/worlds/{wid}/tactic usunięty — Klasa = Taktyka (combat.CLASS_TACTIC)
 @app.get('/api/worlds/{wid}/players')
 def players(wid:int,u=Depends(auth)):
  with db.tx() as c:season_api['ensure'](c)  # 5.4: ranking Elo zawsze z bieżącego sezonu
  with db.read() as c:
   world(c,wid,True);own(c,u['id'],wid)
   ts=now()
   rows=c.execute('SELECT c.id,c.nickname,c.account_id,c.rating,c.wins,c.losses,c.draws,c.state_json,c.current_district,c.travel_destination,MAX(s.last_seen) seen FROM characters c JOIN accounts a ON a.id=c.account_id AND a.banned=0 LEFT JOIN sessions s ON s.account_id=c.account_id AND s.expires_at>? WHERE c.world_id=? GROUP BY c.id ORDER BY c.rating DESC,c.id LIMIT 200',(ts,wid)).fetchall()
   # 0.37/0.40: presence na wielkiej mapie — dzielnicę i firmy publikujemy TYLKO graczy online (lub siebie); offline = None
   players=[]
   for r in rows:
    online=bool(r['seen']) and ts-r['seen']<=300000
    vis=online or r['account_id']==u['id']
    st=json.loads(r['state_json']);biz=None;origin=None
    if vis:
     biz={'courier':int((st.get('business') or {}).get('level',1))}
     v=(st.get('ventures') or {}).get('studio')
     if v:biz['studio']=int(v.get('level',1))
     for k in ('cafe','nightclub'):  # 4.1: kawiarnia i klub nocny to budynki
      lv=int((st.get('buildings') or {}).get(k,0) or 0)
      if lv:biz[k]=lv
     if r['travel_destination']:origin=r['current_district'] or 1
    players.append(dict(id=r['id'],nickname=r['nickname'],rating=round(r['rating']),wins=r['wins'],losses=r['losses'],draws=r['draws'],level=E.level(st['xp']),own=r['account_id']==u['id'],online=online,avatar=AV.brief(st),
     district=((r['travel_destination'] or r['current_district'] or 1) if vis else None),
     traveling=bool(r['travel_destination']) if vis else False,biz=biz,origin=origin))
   return {'players':players}
 @app.get('/api/worlds/{wid}/pvp')
 def pvp(wid:int,u=Depends(auth)):
  with db.tx() as c:
   world(c,wid,True);ch=own(c,u['id'],wid)
   c.execute("UPDATE challenges SET status='expired' WHERE status='pending' AND expires_at<=?",(now(),))
   rows=c.execute('SELECT q.id,q.status,q.created_at,q.expires_at,q.attacker_id,q.defender_id,a.nickname attacker_name,d.nickname defender_name FROM challenges q JOIN characters a ON a.id=q.attacker_id JOIN characters d ON d.id=q.defender_id WHERE q.world_id=? AND (q.attacker_id=? OR q.defender_id=?) ORDER BY q.id DESC LIMIT 50',(wid,ch['id'],ch['id'])).fetchall()
   matches=c.execute('SELECT m.id,m.created_at,m.attacker_id,m.defender_id,a.nickname attacker_name,d.nickname defender_name FROM matches m JOIN characters a ON a.id=m.attacker_id JOIN characters d ON d.id=m.defender_id WHERE m.world_id=? AND (m.attacker_id=? OR m.defender_id=?) ORDER BY m.id DESC LIMIT 30',(wid,ch['id'],ch['id'])).fetchall()
   day=now()//(24*E.HOUR)*(24*E.HOUR);usage=c.execute('SELECT used FROM ranked_usage WHERE character_id=? AND day=?',(ch['id'],day)).fetchone();used=usage['used'] if usage else 0
   org=c.execute('SELECT o.id,o.name,o.tag,m.role FROM organizations o JOIN org_members m ON m.org_id=o.id WHERE m.character_id=?',(ch['id'],)).fetchone()  # 0.48: zaproszenia do gildii prosto z listy PvP
   myOrg=dict(id=org['id'],name=org['name'],tag=org['tag'],canInvite=org['role'] in ('leader','officer')) if org else None
   return dict(challenges=[dict(r) for r in rows],matches=[dict(r) for r in matches],character_id=ch['id'],daily_used=used,myOrg=myOrg)
 @app.post('/api/worlds/{wid}/challenges')
 def invite(wid:int,data:Invite,request:Request,u=Depends(auth)):
  rate(request,'challenge-'+str(u['id']),15,10*E.MINUTE)
  with db.tx() as c:
   w=world(c,wid,True);a=own(c,u['id'],wid)
   d=c.execute('SELECT c.* FROM characters c JOIN accounts a ON a.id=c.account_id WHERE c.id=? AND c.world_id=? AND a.banned=0',(data.target_id,wid)).fetchone()
   if not d or d['account_id']==u['id']:fail(404,'Nieprawidłowy przeciwnik z tego świata.')
   if extra.blocked(c,u['id'],d['account_id']):fail(409,'Kontakt został zablokowany.')
   sa=state_of(c,a,w)
   if E.level(sa['xp'])<2:fail(409,'Wyzwania PvP odblokowują się na 2. poziomie.')
   daily_limit(c,a['id']);daily_limit(c,d['id']);pair_limit(c,a['id'],d['id'])
   if c.execute("SELECT count(*) FROM challenges WHERE attacker_id=? AND status='pending' AND expires_at>?",(a['id'],now())).fetchone()[0]>=3:fail(409,'Masz już trzy oczekujące wyzwania.')
   if c.execute("SELECT 1 FROM challenges WHERE status='pending' AND expires_at>? AND ((attacker_id=? AND defender_id=?) OR (attacker_id=? AND defender_id=?))",(now(),a['id'],d['id'],d['id'],a['id'])).fetchone():fail(409,'Wyzwanie tej pary już oczekuje.')
   snapshot=dict(stats=E.effective(sa),cls=a['class_type'],tactic=combat.class_tactic(E.effective(sa),a['class_type']))  # 5.1: Klasa = Taktyka
   cid=c.execute('INSERT INTO challenges(world_id,attacker_id,defender_id,attacker_snapshot,created_at,expires_at) VALUES(?,?,?,?,?,?)',(wid,a['id'],d['id'],packed(snapshot),now(),now()+24*E.HOUR)).lastrowid
   return dict(id=cid,message='Wysłano wyzwanie — walczysz taktyką swojej klasy.')
 @app.post('/api/challenges/{cid}/accept')
 def accept(cid:int,data:Accept,u=Depends(auth)):
  with db.tx() as c:
   q=c.execute('SELECT * FROM challenges WHERE id=?',(cid,)).fetchone()
   if not q:fail(404,'Nie znaleziono wyzwania.')
   d=own(c,u['id'],q['world_id'])
   if d['id']!=q['defender_id']:fail(403,'Tylko zaproszony gracz może przyjąć wyzwanie.')
   existing=c.execute('SELECT report_json,id FROM matches WHERE challenge_id=?',(cid,)).fetchone()
   if existing:return dict(report=json.loads(existing['report_json']),match_id=existing['id'])
   if q['status']!='pending' or q['expires_at']<=now():fail(409,'Wyzwanie nie jest już aktywne.')
   w=world(c,q['world_id'],True);a=c.execute('SELECT c.* FROM characters c JOIN accounts a ON a.id=c.account_id WHERE c.id=? AND a.banned=0',(q['attacker_id'],)).fetchone()
   if not a:fail(409,'Przeciwnik jest niedostępny.')
   if extra.blocked(c,u['id'],d['account_id']):fail(409,'Kontakt został zablokowany.')
   daily_limit(c,a['id']);daily_limit(c,d['id']);pair_limit(c,a['id'],d['id'])
   snapshot=json.loads(q['attacker_snapshot']);ds=state_of(c,d,w)
   report=combat.fight(snapshot['stats'],E.effective(ds),levels=(E.level(json.loads(a['state_json']).get('xp',0)),E.level(ds.get('xp',0))),classes=(snapshot.get('cls') or a['class_type'],d['class_type']),evos=((json.loads(a['state_json']).get('evolutionCode'),json.loads(a['state_json']).get('evolution2Code')),(ds.get('evolutionCode'),ds.get('evolution2Code'))),gears=(json.loads(a['state_json']).get('equipped'),ds.get('equipped')))  # Combat 3.0: ewolucje i ekwipunek  # 5.1: Klasa = Taktyka; 5.2: HP z poziomem
   report['names']=[a['nickname'],d['nickname']];report['characterIds']=[a['id'],d['id']];report['ranked']=True
   report['avatars']=[AV.brief(json.loads(a['state_json'])),AV.brief(ds)]  # 0.47: awatary i sprzet zawodnikow w raporcie
   report['gear']=[AV.gear(json.loads(a['state_json'])),AV.gear(ds)]
   expected=1/(1+10**((d['rating']-a['rating'])/400));score=0.5 if report['winner'] is None else 1 if report['winner']==0 else 0;change=24*(score-expected)
   report['ratingChanges']=[change,-change]
   for row,index,delta in [(a,0,change),(d,1,-change)]:
    day=now()//(24*E.HOUR)*(24*E.HOUR)
    c.execute('INSERT INTO ranked_usage(character_id,day,used) VALUES(?,?,1) ON CONFLICT(character_id,day) DO UPDATE SET used=used+1',(row['id'],day))
    c.execute('UPDATE characters SET rating=rating+?,wins=wins+?,losses=losses+?,draws=draws+? WHERE id=?',(delta,int(report['winner']==index),int(report['winner'] is not None and report['winner']!=index),int(report['winner'] is None),row['id']))
   rw=[pvp_api['reward'](c,row['id'],'draw' if report['winner'] is None else 'win' if report['winner']==i else 'loss') for i,row in ((0,a),(1,d))]
   report['rewards']=rw  # 5.3 GDD v3.1: nagrody dla obu stron
   mid=c.execute('INSERT INTO matches(world_id,challenge_id,attacker_id,defender_id,report_json,created_at,combat_version) VALUES(?,?,?,?,?,?,?)',(q['world_id'],cid,a['id'],d['id'],packed(report),now(),combat.ENGINE_V1)).lastrowid
   c.execute("UPDATE challenges SET status='accepted' WHERE id=?",(cid,));return dict(report=report,match_id=mid)
 @app.post('/api/challenges/{cid}/decline')
 def decline(cid:int,u=Depends(auth)):
  with db.tx() as c:
   q=c.execute('SELECT q.*,d.account_id defender_account,a.account_id attacker_account FROM challenges q JOIN characters d ON d.id=q.defender_id JOIN characters a ON a.id=q.attacker_id WHERE q.id=?',(cid,)).fetchone()
   if not q or u['id'] not in (q['defender_account'],q['attacker_account']):fail(404,'Nie znaleziono wyzwania.')
   if q['status']!='pending':fail(409,'Wyzwanie zostało już rozliczone.')
   c.execute("UPDATE challenges SET status='declined' WHERE id=?",(cid,));return {'ok':True}
 @app.get('/api/matches/{mid}')
 def match(mid:int,u=Depends(auth)):
  with db.read() as c:
   r=c.execute('SELECT m.*,a.account_id a_uid,d.account_id d_uid FROM matches m JOIN characters a ON a.id=m.attacker_id JOIN characters d ON d.id=m.defender_id WHERE m.id=?',(mid,)).fetchone()
   if not r or u['id'] not in (r['a_uid'],r['d_uid']):fail(404,'Raport nie jest dostępny.')
   return {'report':json.loads(r['report_json']),'match_id':mid,'combat_version':r['combat_version'] or combat.ENGINE_V1_LEGACY}  # 1.6: fallback dla starych walk (formuły sprzed 5.x)
 @app.get('/api/admin/worlds/{wid}/summary')
 def world_summary(wid:int,u=Depends(admin)):
  # wyłącznie odczyt: obraz świata dla administratora (ludzie, cele, orgs, kronika, dev-sklep)
  with db.read() as c:
   w=world(c,wid)
   chars=c.execute('SELECT count(*) n,coalesce(sum(json_extract(state_json,"$.xp")),0) xp FROM characters WHERE world_id=?',(wid,)).fetchone()
   top=[dict(nickname=r['nickname'],level=E.level(r['xp'] or 0),xp=r['xp'] or 0) for r in c.execute('SELECT nickname,json_extract(state_json,"$.xp") xp FROM characters WHERE world_id=? ORDER BY json_extract(state_json,"$.xp") DESC,id LIMIT 5',(wid,))]
   newest=c.execute('SELECT nickname,created_at FROM characters WHERE world_id=? ORDER BY id DESC LIMIT 1',(wid,)).fetchone()
   orgs=c.execute('SELECT count(*) FROM organizations WHERE world_id=?',(wid,)).fetchone()[0]
   top_orgs=[dict(r) for r in c.execute('SELECT o.name,o.tag,coalesce((SELECT sum(i.total) FROM org_investments i WHERE i.org_id=o.id),0) prestige,(SELECT count(*) FROM org_members m WHERE m.org_id=o.id) members FROM organizations o WHERE o.world_id=? ORDER BY prestige DESC,o.id LIMIT 5',(wid,)).fetchall()]
   contracts=dict(active=c.execute("SELECT count(*) FROM org_contracts oc JOIN organizations o ON o.id=oc.org_id WHERE o.world_id=? AND oc.status='active'",(wid,)).fetchone()[0],done=c.execute("SELECT count(*) FROM org_contracts oc JOIN organizations o ON o.id=oc.org_id WHERE o.world_id=? AND oc.status='done'",(wid,)).fetchone()[0],missed=c.execute("SELECT count(*) FROM org_contracts oc JOIN organizations o ON o.id=oc.org_id WHERE o.world_id=? AND oc.status='missed'",(wid,)).fetchone()[0])
   ev=[e for e in city_api['overview'](c) if e['world_id']==wid]
   event=dict(ev[0]) if ev else None
   daily=[dict(r) for r in c.execute('SELECT day,deeds,cash,xp,shop_cents FROM world_daily WHERE world_id=? ORDER BY day DESC LIMIT 14',(wid,))]
   chronicle_count=c.execute('SELECT count(*) FROM chronicle WHERE world_id=?',(wid,)).fetchone()[0]
   notices_count=c.execute('SELECT count(*) FROM notices WHERE created_at>? AND (world_id IS NULL OR world_id=?)',(now()-7*24*E.HOUR,wid)).fetchone()[0]
   shop=dict(purchases=c.execute('SELECT count(*) FROM shop_purchases WHERE world_id=?',(wid,)).fetchone()[0],cents=c.execute('SELECT coalesce(sum(cents),0) FROM shop_purchases WHERE world_id=?',(wid,)).fetchone()[0])
   vip_residents=c.execute('SELECT count(DISTINCT s.account_id) FROM shop_state s JOIN characters c2 ON c2.account_id=s.account_id WHERE c2.world_id=? AND s.vip_until>?',(wid,now())).fetchone()[0]
   return dict(world=dict(id=w['id'],name=w['name'],kind=w['kind'],speed=w['speed'],registration_open=bool(w['registration_open']),maintenance=bool(w['maintenance']),opens_at=w['opens_at']),population=chars['n'],cityXp=chars['xp'],top=top,newest=dict(nickname=newest['nickname'],created_at=newest['created_at']) if newest else None,orgs=orgs,topOrgs=top_orgs,contracts=contracts,event=event,chronicleCount=chronicle_count,noticesCount=notices_count,shop=shop,vipResidents=vip_residents,daily=daily)
 @app.get('/api/admin/overview')
 def overview(u=Depends(admin)):
  with db.read() as c:return dict(worlds=[dict(r) for r in c.execute('SELECT w.*,(SELECT count(*) FROM characters c WHERE c.world_id=w.id) population FROM worlds w ORDER BY w.id')],accounts=[{k:r[k] for k in ('id','username','role','banned','created_at')} for r in c.execute('SELECT * FROM accounts ORDER BY id DESC LIMIT 100')],audit=[dict(r) for r in c.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')],notices=[dict(r) for r in c.execute('SELECT id,world_id,text,created_at FROM notices ORDER BY id DESC LIMIT 20')],events=city_api['overview'](c))
 @app.post('/api/admin/worlds')
 def admin_create(data:WorldCreate,u=Depends(admin)):
  if data.kind=='standard' and data.speed!=1:fail(422,'Standardowe światy używają tempa ×1.')
  if not data.name.strip():fail(422,'Wpisz nazwę świata.')
  if data.opens_at is not None and not 0<=data.opens_at<=now()+10*365*24*E.HOUR:fail(422,'Nieprawidłowy termin otwarcia.')
  with db.tx() as c:
   if c.execute('SELECT count(*) FROM worlds').fetchone()[0]>=300:fail(409,'Limit 300 logicznych światów.')
   if c.execute('SELECT 1 FROM worlds WHERE name=?',(data.name.strip(),)).fetchone():fail(409,'Nazwa świata jest zajęta.')
   wid=c.execute('INSERT INTO worlds(name,kind,opens_at,registration_open,speed,created_at) VALUES(?,?,?,?,?,?)',(data.name.strip(),data.kind,data.opens_at or now(),int(data.registration_open),data.speed,now())).lastrowid
   audit(c,u['id'],'world.create',dict(id=wid,**data.model_dump()));return {'id':wid}
 @app.patch('/api/admin/worlds/{wid}')
 def admin_update(wid:int,data:WorldUpdate,u=Depends(admin)):
  with db.tx() as c:
   world(c,wid);changes=data.model_dump(exclude_none=True)
   for key,value in changes.items():c.execute('UPDATE worlds SET '+key+'=? WHERE id=?',(int(value) if isinstance(value,bool) else value,wid))
   audit(c,u['id'],'world.update',dict(id=wid,**changes));return {'ok':True}
 @app.patch('/api/admin/accounts/{uid}')
 def moderate(uid:int,data:Moderate,u=Depends(admin)):
  with db.tx() as c:
   target=c.execute('SELECT * FROM accounts WHERE id=?',(uid,)).fetchone()
   if not target:fail(404,'Nie ma takiego konta.')
   if target['role']=='admin':fail(409,'Ten panel nie zmienia kont administratorów.')
   changes={}
   if data.banned is not None:
    c.execute('UPDATE accounts SET banned=? WHERE id=?',(int(data.banned),uid))
    if data.banned:c.execute('DELETE FROM sessions WHERE account_id=?',(uid,))
    changes['banned']=data.banned
   if data.moderator is not None:
    c.execute('UPDATE accounts SET role=? WHERE id=?',('moderator' if data.moderator else 'player',uid))
    changes['moderator']=data.moderator
   audit(c,u['id'],'account.moderate',dict(id=uid,**changes));return {'ok':True}
 @app.get('/api/account/export')
 def export(u=Depends(auth)):
  with db.read() as c:
   chars=[]
   for row in c.execute('SELECT id,world_id,nickname,state_json,rating,wins,losses,draws,created_at FROM characters WHERE account_id=?',(u['id'],)):
    d=dict(row);d['state']=json.loads(d.pop('state_json'));chars.append(d)
   matches=[]
   for row in c.execute('SELECT m.id,m.world_id,m.created_at,m.report_json FROM matches m JOIN characters a ON a.id=m.attacker_id JOIN characters d ON d.id=m.defender_id WHERE a.account_id=? OR d.account_id=?',(u['id'],u['id'])):
    item=dict(row);item['report']=json.loads(item.pop('report_json'));matches.append(item)
   usage=[dict(r) for r in c.execute('SELECT r.character_id,r.day,r.used FROM ranked_usage r JOIN characters c ON c.id=r.character_id WHERE c.account_id=?',(u['id'],))]
   return dict(account=user_public(u),characters=chars,matches=matches,ranked_usage=usage,community=extra.export_account(c,u['id']),exported_at=now())
 @app.get('/api/account/profile')
 def account_profile(u=Depends(auth)):
  # 0.45.2: profil konta z osiągnięciami — czytelny z ekranu wyboru światów, przed wejściem do gry.
  with db.read() as c:
   out=[]
   for row in c.execute('SELECT c.id,c.world_id,c.nickname,c.rating,c.wins,c.losses,c.draws,c.class_type,c.class_evolution,c.current_location,c.dungeon_progress,c.state_json,w.name wname,w.kind wkind FROM characters c JOIN worlds w ON w.id=c.world_id WHERE c.account_id=? ORDER BY c.world_id',(u['id'],)):
    st=json.loads(row['state_json']);lvl=E.level(st['xp'])
    titles=[r['label'] for r in c.execute('SELECT label FROM character_titles WHERE character_id=? ORDER BY id DESC LIMIT 24',(row['id'],))]
    total=c.execute('SELECT count(*) FROM character_titles WHERE character_id=?',(row['id'],)).fetchone()[0]
    comp=st.get('completed') or {};avb=AV.brief(st)
    out.append(dict(worldId=row['world_id'],world=row['wname'],kind=row['wkind'],nickname=row['nickname'],level=lvl,xp=st['xp'],xpBase=lvl*(lvl-1)*50,xpNext=lvl*(lvl+1)*50,cash=st.get('cash',0),clas=row['class_type'],evolution=row['class_evolution'],location=row['current_location'],dungeon=row['dungeon_progress'] or 0,rating=row['rating'],wins=row['wins'],losses=row['losses'],draws=row['draws'],deeds=(comp.get('contracts',0)+comp.get('training',0)+comp.get('collected',0)),titles=titles,titlesTotal=total,avatar=avb))
   # Flutter Profil: Punkty Prestiżu konta, ramki (kosmetyka) i liczba resetów w Sali Chwały per postać
   pp=c.execute('SELECT prestige_points FROM accounts WHERE id=?',(u['id'],)).fetchone()
   has_resets=bool(c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='server_resets'").fetchone())
   for o in out:
    row=c.execute('SELECT id,state_json,created_at FROM characters WHERE account_id=? AND world_id=?',(u['id'],o['worldId'])).fetchone()
    st=json.loads(row['state_json']) if row else {}
    o['frames']=list(st.get('frames') or []);o['frame']=st.get('frame')
    o['resets']=c.execute('SELECT count(*) FROM server_resets WHERE character_id=?',(row['id'],)).fetchone()[0] if (row and has_resets) else 0
    o['createdAt']=row['created_at'] if row and 'created_at' in row.keys() else None
   return dict(username=u['username'],characters=out,prestigePoints=int((pp['prestige_points'] if pp and 'prestige_points' in pp.keys() else 0) or 0),generatedAt=now())
 @app.get('/api/avatar/catalog')
 def avatar_catalog(u=Depends(auth)):
  # 0.46: katalog garderoby (kosmetyka) + czy konto ma aktywne VIP, żeby UI od razu blokowało rzeczy VIP.
  with db.read() as c:
   return dict(cats=[dict(k=k,label=lb,icon=ic) for k,lb,ic in AV.CATS],items=AV.ITEMS,bodies=AV.BODIES,vipActive=shop_api['vip_until'](c,u['id'])>now())
 @app.post('/api/worlds/{wid}/avatar')
 def wear_avatar(wid:int,data:AvatarIn,request:Request,u=Depends(auth)):
  rate(request,'avatar-'+str(u['id']),30,60000)
  with db.tx() as c:
   world(c,wid,True);ch=own(c,u['id'],wid);s=json.loads(ch['state_json'])
   av=s.get('avatar') if isinstance(s.get('avatar'),dict) else AV.default()
   owned=set(av.get('owned') or [])
   clean,err=AV.validate(data.avatar,shop_api['vip_until'](c,u['id'])>now(),owned,False)
   if err:fail(422,err)
   s['avatar']={'body':clean['body'],'worn':clean['worn'],'owned':sorted(owned)}
   c.execute('UPDATE characters SET state_json=? WHERE id=?',(packed(s),ch['id']))
   audit(c,u['id'],'avatar.wear',dict(worn=clean['worn']))
   return dict(ok=True,avatar=s['avatar'],message='Wygląd zapisany.')
 @app.post('/api/worlds/{wid}/wardrobe')
 def wardrobe_buy(wid:int,data:WardrobeBuy,request:Request,u=Depends(auth)):
  rate(request,'wardrobe-'+str(u['id']),20,60000)
  with db.tx() as c:
   world(c,wid,True);ch=own(c,u['id'],wid);s=json.loads(ch['state_json'])
   it=AV.ID2ITEM.get(data.item)
   if not it:fail(404,'Nie ma takiej rzeczy w garderobie.')
   av=s.get('avatar') if isinstance(s.get('avatar'),dict) else AV.default()
   owned=set(av.get('owned') or [])
   if it['id'] in owned:fail(409,'Masz już tę rzecz.')
   if it['vip'] and shop_api['vip_until'](c,u['id'])<=now():fail(409,'Ta rzecz jest dla członków VIP — aktywuj VIP w sklepie.')
   if s['cash']<it['p']:fail(409,'Za mało gotówki — potrzeba '+str(it['p'])+' $.')
   s['cash']=round(s['cash']-it['p'],2)
   owned.add(it['id'])
   s['avatar']={'body':av.get('body') or AV.default()['body'],'worn':{**(av.get('worn') or {}),it['k']:it['id']},'owned':sorted(owned)}
   c.execute('UPDATE characters SET state_json=? WHERE id=?',(packed(s),ch['id']))
   audit(c,u['id'],'wardrobe.buy',dict(item=it['id'],price=it['p']))
   return dict(ok=True,cash=s['cash'],avatar=s['avatar'],message='Kupione i założone: '+it['n']+'.')
 @app.get('/api/account/rankings')
 def account_rankings(u=Depends(auth)):
  # 0.46: ranking PRZED grą — TOP 10 każdego świata, gdzie mam postać, + globalny sezon (XP kariery).
  with db.read() as c:
   cur=features.season_of(now())
   rows=c.execute('SELECT ch.world_id,w.name,ch.nickname,ch.state_json FROM characters ch JOIN worlds w ON w.id=ch.world_id WHERE ch.account_id=? ORDER BY ch.world_id',(u['id'],)).fetchall()
   mine=[]
   for r in rows:
    xp=json.loads(r['state_json']).get('xp',0)
    top=[dict(place=i+1,nickname=t['nickname'],xp=t['xp'],level=E.level(t['xp'])) for i,t in enumerate(c.execute('SELECT ch2.nickname,json_extract(ch2.state_json,"$.xp") xp FROM characters ch2 JOIN accounts a ON a.id=ch2.account_id WHERE ch2.world_id=? AND a.banned=0 ORDER BY xp DESC LIMIT 10',(r['world_id'],)).fetchall())]
    higher=c.execute('SELECT count(*) FROM characters ch2 JOIN accounts a ON a.id=ch2.account_id WHERE ch2.world_id=? AND a.banned=0 AND json_extract(ch2.state_json,"$.xp")>?',(r['world_id'],xp)).fetchone()[0]
    mine.append(dict(worldId=r['world_id'],world=r['name'],nickname=r['nickname'],xp=xp,place=higher+1,top=top))
   gtop=[dict(place=i+1,nickname=t['nickname'],world=t['wname'],xp=t['xp'],level=E.level(t['xp'])) for i,t in enumerate(c.execute('SELECT ch2.nickname,json_extract(ch2.state_json,"$.xp") xp,w.name wname FROM characters ch2 JOIN accounts a ON a.id=ch2.account_id JOIN worlds w ON w.id=ch2.world_id WHERE a.banned=0 ORDER BY xp DESC LIMIT 10').fetchall())]
   gbest=None
   for r in rows:
    xp=json.loads(r['state_json']).get('xp',0)
    higher=c.execute('SELECT count(*) FROM characters ch2 JOIN accounts a ON a.id=ch2.account_id WHERE a.banned=0 AND json_extract(ch2.state_json,"$.xp")>?',(xp,)).fetchone()[0]
    place=higher+1
    if gbest is None or place<gbest.place:gbest=dict(place=place,nickname=r['nickname'],world=r['name'],xp=xp,level=E.level(xp))
   return dict(season=cur,worlds=mine,globalTop=gtop,myGlobal=gbest)
 @app.post('/api/account/delete')
 def delete_account(data:Password,request:Request,u=Depends(auth)):
  try:valid=PH.verify(u['password_hash'],data.password)
  except VerificationError:valid=False
  if not valid:fail(403,'Nieprawidłowe hasło.')
  with db.tx() as c:
   if u['role']=='admin' and c.execute("SELECT count(*) FROM accounts WHERE role='admin'").fetchone()[0]<=1:fail(409,'Najpierw przekaż rolę administratora innemu kontu przez narzędzie operatorskie.')
   current=c.execute('SELECT password_hash FROM accounts WHERE id=?',(u['id'],)).fetchone()
   if not current or current['password_hash']!=u['password_hash']:fail(409,'Hasło zmieniło się w innej sesji. Zaloguj się ponownie.')
   if u['deletion_at']:fail(409,'Usunięcie tego konta jest już zaplanowane.')
   extra.before_delete(c,u['id'])
   # Grace period: the account stops existing for the owner now, data leaves after 7 days.
   c.execute('UPDATE accounts SET deletion_at=? WHERE id=? AND password_hash=?',(now()+7*24*E.HOUR,u['id'],u['password_hash']))
   c.execute('DELETE FROM sessions WHERE account_id=?',(u['id'],))
   audit(c,u['id'],'account.delete_scheduled',dict(deletion_at=now()+7*24*E.HOUR))
  return clear_cookie(JSONResponse({'ok':True,'scheduled':True,'deletion_at':now()+7*24*E.HOUR}),request)
 @app.post('/api/account/delete/cancel')
 def cancel_delete(data:Password,u=Depends(auth)):
  try:valid=PH.verify(u['password_hash'],data.password)
  except VerificationError:valid=False
  if not valid:fail(403,'Nieprawidłowe hasło.')
  with db.tx() as c:
   current=c.execute('SELECT password_hash,deletion_at FROM accounts WHERE id=?',(u['id'],)).fetchone()
   if not current or current['password_hash']!=u['password_hash']:fail(409,'Hasło zmieniło się w innej sesji. Zaloguj się ponownie.')
   if not current['deletion_at']:fail(409,'Usunięcie nie zostało zaplanowane.')
   c.execute('UPDATE accounts SET deletion_at=NULL WHERE id=? AND password_hash=?',(u['id'],u['password_hash']))
   audit(c,u['id'],'account.delete_cancelled',{})
  return {'ok':True}

 @app.post('/api/admin/notices')
 def post_notice(data:Notice,u=Depends(admin)):
  text=data.text.strip()
  with db.tx() as c:
   if data.world_id is not None:world(c,data.world_id)
   nid=c.execute('INSERT INTO notices(world_id,text,author_id,created_at) VALUES(?,?,?,?)',(data.world_id,text,u['id'],now())).lastrowid
   c.execute('DELETE FROM notices WHERE id NOT IN (SELECT id FROM notices ORDER BY id DESC LIMIT 20)')
   audit(c,u['id'],'notice.posted',dict(id=nid,world_id=data.world_id))
  return {'ok':True,'id':nid}
 @app.post('/api/admin/notices/{nid}/delete')
 def delete_notice(nid:int,u=Depends(admin)):
  with db.tx() as c:
   row=c.execute('SELECT id FROM notices WHERE id=?',(nid,)).fetchone()
   if not row:fail(404,'Nie ma takiego ogłoszenia.')
   c.execute('DELETE FROM notices WHERE id=?',(nid,))
   audit(c,u['id'],'notice.delete',dict(id=nid))
   return {'ok':True}
 chron_api=chronicle.install(app,SimpleNamespace(db=db,now=now),E)
 extra=features.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,admin=admin,staff=staff,rate=rate,PH=PH,audit=audit,min_password_length=min_password_length,chronicle=chron_api))
 shop_api=shop.install(app,SimpleNamespace(db=db,now=now,fail=fail,auth=auth,rate=rate,audit=audit),E)
 city_api=city_events.install(app,SimpleNamespace(db=db,now=now,fail=fail,admin=admin,audit=audit,chronicle=chron_api),E)
 travel_api=travel.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,era=city_api['era']),E)
 sports_api=sports.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,chron=chron_api),E)
 season_api=seasons_mod.install(app,db,SimpleNamespace(now=now,auth=auth,own=own),E)  # 5.4 GDD v3.1: miesięczne sezony Elo
 app.state.seasons=season_api
 pvp_api=pvp_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,extra=extra,limit=daily_limit,pair=pair_limit),E,combat,city_api)
 bp_api=bp_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,audit=audit),E)  # 8.4 GDD v3.1
 gear_api=gear_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,audit=audit),E)  # 7.x GDD v3.1
 dungeon_api=dungeon_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E,combat)
 sports2_api=sports2_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E,combat)
 sports3_api=sports3_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit),E)  # QA 5
 services_api=services_mod.install(app,SimpleNamespace(db=db,world=world,own=own,auth=auth,now=now,fail=fail,rate=rate,audit=audit),E)  # 2.2 GDD v3.1
 npc_api=npc_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,rate=rate,audit=audit,emit=extra.emit),E,services_mod)  # 2.3 GDD v3.1
 own_hooks.update(longplay_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,own=own,auth=auth,audit=audit,emit=extra.emit),E))  # 3.4 GDD v3.1
 prestige_api=prestige_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,audit=audit,emit=extra.emit,chronicle=chron_api),E)  # 4.5 GDD v3.1
 app.state.npc=npc_api  # 2.3: dostęp do sweep w testach
 assistant_mod.install(app,SimpleNamespace(db=db,now=now,fail=fail,world=world,own=own,auth=auth,era=city_api['era'],npc=npc_api,always_open=travel.ALWAYS_OPEN,bus_fare=travel.BUS_FARE),E,services_mod,npc_mod,travel_api)  # 2.6 GDD v3.1
 def purge_due():
  try:
   with db.tx() as c:
    rows=c.execute('SELECT id FROM accounts WHERE deletion_at IS NOT NULL AND deletion_at<=?',(now(),)).fetchall()
    for r in rows:
     try:extra.before_delete(c,r['id'])
     except Exception:continue
     c.execute('DELETE FROM accounts WHERE id=?',(r['id'],))
     c.execute('INSERT INTO audit(actor_id,event,details,created_at) VALUES(NULL,?,?,?)',('account.purged',packed(dict(id=r['id'])),now()))
  except Exception:pass
 purge_due()
 app.state.purge=purge_due
 app.state.mailer=AGE.Mailer()  # 1.8: dev-stub; testy/produkcja mogą podmienić
 def purge_rate_limits():
  # 1.5 GDD v3.1: usuń limity wygasłe ponad dobę temu (tabela nie rośnie bez końca)
  try:
   with db.tx() as c:return c.execute('DELETE FROM rate_limits WHERE until_at<?',(now()-24*3600000,)).rowcount
  except Exception:return 0
 purge_rate_limits()
 app.state.purge_rates=purge_rate_limits
 def purge_guardian_expired():
  # 1.8 A3: brak zgody opiekuna w 7 dni → konto oznaczone do usunięcia; purge_due usuwa je razem z danymi
  try:
   with db.tx() as c:
    rows=c.execute("SELECT id FROM accounts WHERE guardian_status='pending' AND guardian_token_exp<=? AND deletion_at IS NULL",(now(),)).fetchall()
    for r in rows:
     c.execute('UPDATE accounts SET deletion_at=? WHERE id=?',(now(),r['id']))
     c.execute('INSERT INTO audit(actor_id,event,details,created_at) VALUES(?,?,?,?)',(r['id'],'guardian.expired','{}',now()))
   return len(rows)
  except Exception:return 0
 app.state.purge_guardian=purge_guardian_expired
 purge_guardian_expired();purge_due()
 def sweep():
  while True:
   time.sleep(600);purge_guardian_expired();purge_due();purge_rate_limits();npc_api['sweep']()
   try:
    with db.tx() as c:season_api['ensure'](c)  # 5.4: domknięcie sezonu Elo także bez ruchu graczy
   except Exception:pass
 threading.Thread(target=sweep,daemon=True).start()
 # 8.6 GDD v3.1: jeden zbiorczy endpoint pod Fluttera — stan, NPC, asystent, eventy, skarbce, BP, staż w 1 żądaniu.
 # Składany z istniejących endpointów (ta sama logika i uprawnienia, zero duplikacji reguł).
 _ep={(r.path,m):r.endpoint for r in app.router.routes if hasattr(r,'methods') for m in r.methods}
 @app.get('/api/worlds/{wid}/dashboard')
 def dashboard(wid:int,u=Depends(auth)):
  st=_ep[('/api/worlds/{wid}/state','GET')](wid=wid,u=u)
  npcs=_ep[('/api/worlds/{wid}/npcs','GET')](wid=wid,u=u)
  asst=_ep[('/api/worlds/{wid}/assistant','GET')](wid=wid,hours=8,u=u)
  bp=_ep[('/api/worlds/{wid}/battlepass','GET')](wid=wid,u=u)
  ms=_ep[('/api/worlds/{wid}/milestones','GET')](wid=wid,u=u)
  s=st['state'];lst=npcs.get('npcs',[]) if isinstance(npcs,dict) else []
  by={}
  for n in lst:by[n.get('status') or 'idle']=by.get(n.get('status') or 'idle',0)+1
  # Flutter: skarbce = tylko Kawiarnia i Klub Nocny; stare firmy (City Courier, Studio Forma) nie trafiają do /dashboard
  vaults=dict(buildings={k:int((s.get('vaults') or {}).get(k,0)) for k in ('cafe','nightclub')})
  vaults['total']=sum(vaults['buildings'].values())
  st={**st,'state':{k:v for k,v in s.items() if k not in ('business','ventures')}}
  return dict(generatedAt=now(),state=st,
   npc=dict(count=len(lst),byStatus=by,capacity=npcs.get('slots') if isinstance(npcs,dict) else None,list=lst,
    byRole=npcs.get('byRole'),drivers=npcs.get('drivers'),loyal=sum(1 for n in lst if n.get('loyal')),rides=len(npcs.get('rides') or [])),  # v3.2
   assistant=asst,events=dict(timed=st.get('timedEvent'),recent=st.get('eventsRecent')),vaults=vaults,
   battlepass={k:bp[k] for k in ('season','theme','endsAt','xp','level','levels','premium')},
   milestones=dict(activeDays=ms['activeDays'],next=next((m for m in ms['milestones'] if not m['claimed']),None)),
   diamonds=int(s.get('diamonds') or 0),alliance=dash_alliance(st['character']['id']))
 def dash_alliance(cid):
  # Sojusz postaci dla pulpitu: tag, nazwa, rola, liczba członków, fundusz, federacja; None gdy brak
  with db.read() as c:
   r=c.execute('SELECT o.id,o.name,o.tag,o.fund,m.role,(SELECT count(*) FROM org_members x WHERE x.org_id=o.id) members FROM organizations o JOIN org_members m ON m.org_id=o.id WHERE m.character_id=?',(cid,)).fetchone()
   if not r:return None
   out=dict(r)
   try:
    f=c.execute('SELECT f.id,f.name,(SELECT count(*) FROM federation_members y WHERE y.fed_id=f.id) orgs FROM federation_members fm JOIN federations f ON f.id=fm.fed_id WHERE fm.org_id=?',(r['id'],)).fetchone()
    out['federation']=dict(f) if f else None
   except Exception:out['federation']=None  # tabela federacji jeszcze nie utworzona
   return out
 return app

app=create_app()

