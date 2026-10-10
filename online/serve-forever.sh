#!/usr/bin/env bash
# Keeps the dev/preview server alive across crashes: rebuilds once, then respawns uvicorn.
# Data is never deleted here — start.sh already refuses to recreate the database.
set -uo pipefail
cd "$(dirname "$0")"
if ! python -c 'import fastapi, uvicorn, argon2, httpx' >/dev/null 2>&1; then
  echo 'Installing missing CITY EMPIRE runtime dependencies...'
  python -m pip install -r requirements.txt
fi
python build.py
while :; do
  python -m uvicorn server.app:app --host 0.0.0.0 --port "${CITY_PORT:-3000}"
  code=$?
  echo "server exited (code $code); restarting in 2s"
  sleep 2
done
