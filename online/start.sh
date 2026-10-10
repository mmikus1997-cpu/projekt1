#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Workspace restoration may preserve files but not installed dependencies.
# Never delete/recreate the database to repair a missing runtime.
if ! python -c 'import fastapi, uvicorn, argon2, httpx' >/dev/null 2>&1; then
  echo 'Installing missing CITY EMPIRE runtime dependencies...'
  python -m pip install -r requirements.txt
fi
python build.py
exec python -m uvicorn server.app:app --host 0.0.0.0 --port "${CITY_PORT:-3000}"
