#!/usr/bin/env bash
# Throwaway QA runner: fresh SQLite file + fresh admin bootstrap per browser suite,
# so the shared 8-registrations/15-min rate limiter never distorts results.
set -uo pipefail
cd "$(dirname "$0")/.."
NAME="$1"; PORT="$2"; shift 2
DB="tests/$NAME.sqlite3"; SETUP="tests/$NAME-setup.txt"; BDIR="tests/$NAME-backups"
rm -f "$DB" "$DB-wal" "$DB-shm" "$SETUP"; rm -rf "$BDIR"
CITY_DB="$DB" CITY_SETUP_FILE="$SETUP" CITY_BACKUP_DIR="$BDIR" CITY_PORT="$PORT" \
  python -m uvicorn server.app:app --host 0.0.0.0 --port "$PORT" >"tests/$NAME-server.log" 2>&1 &
SRV=$!
for _ in $(seq 1 60); do
  if python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:$PORT/api/health',timeout=2).status==200 else 1)" 2>/dev/null; then break; fi
  if ! kill -0 $SRV 2>/dev/null; then echo "server died"; tail -20 "tests/$NAME-server.log"; rm -f "$DB" "$DB-wal" "$DB-shm" "$SETUP"; exit 1; fi
  sleep 1
done
status=0
TEST_BASE_URL="http://127.0.0.1:$PORT" TEST_STRIP_HEADERS=1 TEST_SETUP_FILE="$SETUP" TEST_DB="$DB" "$@" || status=1
kill $SRV 2>/dev/null; wait $SRV 2>/dev/null
rm -f "$DB" "$DB-wal" "$DB-shm" "$SETUP" "tests/$NAME-server.log"; rm -rf "$BDIR"
exit $status
