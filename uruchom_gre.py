"""Lokalne uruchomienie backendu i gotowego frontendu. Zależności: online/requirements.txt."""
import argparse
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description='Lokalna gra City Empire')
    parser.add_argument('--api-port', type=int, default=3000)
    parser.add_argument('--web-port', type=int, default=8080)
    parser.add_argument('--host', default='127.0.0.1', help='Adres WWW; 0.0.0.0 udostępnia grę w sieci')
    args = parser.parse_args()
    if args.api_port == args.web_port:
        parser.error('API i WWW wymagają różnych portów.')
    jobs = []
    result = 0
    env = dict(os.environ, CITY_PORT=str(args.api_port))
    try:
        jobs.append(subprocess.Popen([sys.executable, '-m', 'uvicorn', 'server.app:app', '--host', '127.0.0.1', '--port', str(args.api_port)], cwd=ROOT/'online', env=env))
        jobs.append(subprocess.Popen([sys.executable, 'tools/serve_web.py', '--host', args.host, '--port', str(args.web_port), '--backend', f'http://127.0.0.1:{args.api_port}'], cwd=ROOT/'app'))
        print(f'Gra: http://localhost:{args.web_port} | Zatrzymanie: Ctrl+C', flush=True)
        while all(p.poll() is None for p in jobs):
            time.sleep(1)
        result = 1
        print('Jeden z serwerów zakończył działanie. Sprawdź komunikaty powyżej.', file=sys.stderr)
    except KeyboardInterrupt:
        pass
    finally:
        for p in jobs:
            if p.poll() is None:
                p.terminate()
        for p in jobs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
    return result

if __name__ == '__main__':
    sys.exit(main())
