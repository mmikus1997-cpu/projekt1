"""Offline operator commands. Requires filesystem access; not exposed through HTTP."""
import argparse
import datetime
import getpass
import json
import os
from pathlib import Path
import socket
import sqlite3
import sys
import time

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description='CITY EMPIRE — narzędzia operatora wersji rozwojowej')
parser.add_argument('--db',default=os.getenv('CITY_DB',str(ROOT/'data'/'city_empire.sqlite3')))
commands=parser.add_subparsers(dest='command',required=True)
for name in ('grant-admin','revoke-admin'):
 p=commands.add_parser(name);p.add_argument('username')
p=commands.add_parser('grant-cash');p.add_argument('username');p.add_argument('amount',type=int)
p=commands.add_parser('backup');p.add_argument('--output',default=None)
commands.add_parser('expire-sessions')
commands.add_parser('verify-backup')
p=commands.add_parser('rehearse-restore');p.add_argument('--output',required=True)
args=parser.parse_args()
path=Path(args.db)
if not path.is_file():parser.error('Baza nie istnieje. Najpierw uruchom aplikację.')
def operator():
 # 1.7 GDD v3.1: kto i skąd wykonał komendę operatora (CLI nie ma konta w grze → actor_id NULL)
 try:who=getpass.getuser()
 except Exception:who='nieznany'
 return {'os_user':who,'host':socket.gethostname(),'command':args.command,'argv':sys.argv[1:]}
def audit(event,details):
 connection.execute('INSERT INTO audit(actor_id,event,details,created_at) VALUES(NULL,?,?,?)',(event,json.dumps({**details,'operator':operator()},ensure_ascii=False),int(time.time()*1000)))
connection=sqlite3.connect(path);connection.row_factory=sqlite3.Row;connection.execute('PRAGMA foreign_keys=ON');connection.execute('PRAGMA busy_timeout=15000')
try:
 if args.command in ('verify-backup','rehearse-restore'):
  checks=connection.execute('PRAGMA integrity_check').fetchall()
  if len(checks)!=1 or checks[0][0]!='ok':parser.error('Kontrola spójności nie powiodła się.')
  if connection.execute('PRAGMA foreign_key_check').fetchall():parser.error('Kopia zawiera naruszenia powiązań danych.')
  print('Spójność SQLite i powiązania danych: OK')
  if args.command=='rehearse-restore':
   output=Path(args.output)
   if output.exists() or output.resolve()==path.resolve():parser.error('Próba odtworzenia wymaga NOWEGO pliku; nigdy nie nadpisuj aktywnej bazy.')
   output.parent.mkdir(parents=True,exist_ok=True)
   os.close(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600))
   destination=sqlite3.connect(output)
   try:
    connection.backup(destination)
    if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':parser.error('Odtworzony plik nie przeszedł kontroli.')
    counts={table:destination.execute('SELECT count(*) FROM '+table).fetchone()[0] for table in ['accounts','characters','worlds']}
    print('Próbne odtworzenie:',output,'| liczby rekordów:',counts)
   finally:destination.close()
 elif args.command=='backup':
  output=Path(args.output or ROOT/'backups'/('city-empire-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3'))
  if output.resolve()==path.resolve() or output.exists():parser.error('Kopia musi wskazywać nowy plik, inny niż baza źródłowa.')
  output.parent.mkdir(parents=True,exist_ok=True)
  os.close(os.open(output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600))
  destination=sqlite3.connect(output)
  try:
   connection.backup(destination)
   if destination.execute('PRAGMA integrity_check').fetchone()[0]!='ok':parser.error('Kopia nie przeszła kontroli spójności.')
  finally:destination.close()
  os.chmod(output,0o600);audit('operator.backup',{'output':str(output)});connection.commit()  # 1.7: ślad po udanej kopii
  print('Utworzono spójną kopię SQLite:',output)
 elif args.command=='grant-cash':
  connection.execute('BEGIN IMMEDIATE')
  user=connection.execute('SELECT * FROM accounts WHERE username=?',(args.username.strip().lower(),)).fetchone()
  if not user:parser.error('Nie znaleziono konta.')
  if args.amount<1 or args.amount>1000000:parser.error('Kwota 1..1 000 000.')
  rows=connection.execute('SELECT id,state_json FROM characters WHERE account_id=?',(user['id'],)).fetchall()
  if not rows:parser.error('Konto nie ma postaci.')
  details={'account_id':user['id'],'amount':args.amount,'characters':[]}
  for r in rows:
   st=json.loads(r['state_json'] or '{}');before=st.get('cash') or 0;st['cash']=before+args.amount
   connection.execute('UPDATE characters SET state_json=? WHERE id=?',(json.dumps(st,ensure_ascii=False,separators=(',',':')),r['id']))
   details['characters'].append({'id':r['id'],'cash_before':before,'cash_after':st['cash']})
  audit('operator.grant-cash',details)
  connection.commit();print('Wykonano: grant-cash —',args.amount,'$ dla postaci:',[x['id'] for x in details['characters']])
 else:
  connection.execute('BEGIN IMMEDIATE')
  if args.command=='expire-sessions':
   connection.execute('DELETE FROM sessions');details={}
  else:
   user=connection.execute('SELECT * FROM accounts WHERE username=?',(args.username.strip().lower(),)).fetchone()
   if not user:parser.error('Nie znaleziono konta.')
   if args.command=='grant-admin':
    if user['banned']:parser.error('Najpierw odblokuj konto.')
    role='admin'
   else:
    if user['role']=='admin' and connection.execute("SELECT count(*) FROM accounts WHERE role='admin'").fetchone()[0]<=1:parser.error('Nie można odebrać roli ostatniemu administratorowi.')
    role='player'
   connection.execute('UPDATE accounts SET role=? WHERE id=?',(role,user['id']))
   connection.execute('DELETE FROM sessions WHERE account_id=?',(user['id'],));details={'account_id':user['id'],'role':role}
  audit('operator.'+args.command,details)
  connection.commit();print('Wykonano:',args.command,'— zmiana zapisana w dzienniku. Zmienione konto musi zalogować się ponownie.')
finally:connection.close()
