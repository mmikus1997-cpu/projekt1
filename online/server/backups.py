"""Local verified SQLite snapshots, never served over HTTP. Not off-site hosting."""
import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import threading
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

class Backups:
 def __init__(self,db_path,directory):
  self.db_path=Path(db_path);self.directory=Path(directory);self.lock=threading.Lock();self.error=None
 def create(self,kind='manual'):
  assert kind in ('manual','auto')
  with self.lock:
   self.directory.mkdir(parents=True,exist_ok=True)
   stamp=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S-%f')
   path=self.directory/(kind+'-'+stamp+'.sqlite3');partial=path.with_suffix('.partial')
   try:
    os.close(os.open(partial,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600))
    source=sqlite3.connect(self.db_path.resolve().as_uri()+'?mode=ro',uri=True,timeout=20);destination=sqlite3.connect(partial)
    try:
     source.backup(destination)
     if destination.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity failed')
     if destination.execute('PRAGMA foreign_key_check').fetchall():raise RuntimeError('Backup foreign key check failed')
    finally:source.close();destination.close()
    os.chmod(partial,0o600);partial.replace(path)
    record={'name':path.name,'kind':kind,'created_at':int(datetime.now(timezone.utc).timestamp()*1000),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'verified':True}
    manifest=path.with_suffix('.json')
    with os.fdopen(os.open(manifest,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as stream:json.dump(record,stream)
    for old in sorted(self.directory.glob(kind+'-*.sqlite3'),reverse=True)[6:]:
     old.unlink();old.with_suffix('.json').unlink(missing_ok=True)
    self.error=None;return record
   except Exception:
    partial.unlink(missing_ok=True);self.error='Kopia nie powstała. Sprawdź miejsce i uprawnienia katalogu kopii.';raise
 def status(self):
  items=[]
  if self.directory.exists():
   for p in self.directory.glob('*.json'):
    if not p.name.startswith(('auto-','manual-')):continue
    try:
     item=json.loads(p.read_text())
     if (self.directory/item['name']).is_file():items.append(item)
    except (ValueError,KeyError,OSError):continue
  return dict(copies=sorted(items,key=lambda x:x['created_at'],reverse=True),error=self.error,interval_minutes=10,retention_per_kind=6,local_only=True)
 def attach(self,app):
  async def loop():
   while True:
    await asyncio.sleep(600)
    try:await asyncio.to_thread(self.create,'auto')
    except Exception:logging.getLogger('uvicorn.error').error('CITY EMPIRE: automatic backup failed; check backup directory.')
  @asynccontextmanager
  async def lifespan(app):
   try:await asyncio.to_thread(self.create,'auto')
   except Exception:logging.getLogger('uvicorn.error').error('CITY EMPIRE: startup backup failed; check backup directory.')
   worker=asyncio.create_task(loop())
   try:yield
   finally:
    worker.cancel()
    try:await worker
    except asyncio.CancelledError:pass
  app.router.lifespan_context=lifespan
