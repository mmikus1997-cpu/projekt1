#!/usr/bin/env bash
# Eksport najnowszych kopii CITY EMPIRE poza maszynę gry. Uruchamiać z cron/timera.
# Przykład: 15 * * * * /opt/city-empire/deploy/backup-offsite.sh /mnt/backup-ce
set -euo pipefail
DEST="${1:?Podaj katalog docelowy, np. /mnt/backup-ce}"
SRC="${CITY_BACKUP_DIR:-/var/lib/city-empire/backups}"
mkdir -p "$DEST/auto" "$DEST/manual"
cp -p "$SRC"/auto-*.sqlite3 "$DEST/auto/" 2>/dev/null || true
cp -p "$SRC"/manual-*.sqlite3 "$DEST/manual/" 2>/dev/null || true
# Retencja po stronie kopii zapasowej: 30 dni poza maszyną gry.
find "$DEST" -name '*.sqlite3' -mtime +30 -delete
# Weryfikacja próbkowa: losowa kopia musi przejść quick_check.
f=$(ls -t "$DEST"/auto/*.sqlite3 | head -1)
python3 - "$f" <<'PY'
import sqlite3,sys
c=sqlite3.connect('file:'+sys.argv[1]+'?mode=ro',uri=True)
assert c.execute('PRAGMA quick_check').fetchone()[0]=='ok', sys.argv[1]
PY
echo "OK: kopie zsynchronizowane do $DEST"
