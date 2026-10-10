#!/bin/bash
set -e
cd "$(dirname "$0")/online"
exec python3 -m uvicorn server.app:app --host 127.0.0.1 --port 3000
