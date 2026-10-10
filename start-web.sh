#!/bin/bash
set -e
cd "$(dirname "$0")/app"
exec python3 tools/serve_web.py --host 127.0.0.1 --port 8080
