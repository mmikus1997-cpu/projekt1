"""Pełna paczka gry: śledzone źródła, gotowy frontend i lokalny CanvasKit, bez zapisów kont."""
from pathlib import Path
import hashlib
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'city-empire-online-0.60.0-gdd32.zip'
TEMP = DEST.with_suffix('.tmp')
WEB = ROOT / 'app/build/web'
if not (WEB / 'main.dart.js').is_file():
    WEB = ROOT / 'app/web_release'
ENGINE = WEB / 'canvaskit'
REQUIRED_ENGINE = ['canvaskit.js', 'canvaskit.wasm', 'chromium/canvaskit.js', 'chromium/canvaskit.wasm']


def main():
    for name in REQUIRED_ENGINE:
        if not (ENGINE / name).is_file():
            raise SystemExit('Najpierw skompiluj Flutter Web; brak silnika: ' + name)
    with zipfile.ZipFile(TEMP, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for repo in ['online', 'app']:
            base = ROOT / repo
            try:
                names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=base, stderr=subprocess.DEVNULL).decode().split('\0')
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Paczka źródłowa nie zawiera historii Git; można ją ponownie spakować.
                excluded = {'.git', '.venv', 'node_modules', '.dart_tool', 'build', 'web_release', 'data', 'shots', 'screens', '__pycache__', '.pytest_cache', 'backups'}
                names = [str(f.relative_to(base)) for f in base.rglob('*') if f.is_file() and not excluded.intersection(f.relative_to(base).parts)]
            for name in names:
                f = base / name
                if not name or not f.is_file():
                    continue
                if name.startswith(('data/', '.git/', 'shots/', 'screens/')) or '.backup' in name or f.name.startswith('.env'):
                    continue
                z.write(f, f.relative_to(ROOT))
        for f in WEB.rglob('*'):
            if not f.is_file() or 'canvaskit' in f.parts:
                continue
            name = 'app/web_release/' + f.relative_to(WEB).as_posix()
            if f.name == 'flutter_bootstrap.js':
                text = f.read_text()
                marker = '_flutter.loader.load({'
                if marker not in text:
                    raise RuntimeError('Nieznany format bootstrapu Fluttera')
                z.writestr(name, text.replace(marker, marker + '\n  config: {canvasKitBaseUrl: "canvaskit/", fontFallbackBaseUrl: "font_fallback/"},', 1))
            else:
                z.write(f, name)
        for name in REQUIRED_ENGINE:
            z.write(ENGINE / name, 'app/web_release/canvaskit/' + name)
        for f in ROOT.glob('*.md'):
            z.write(f, f.name)
        for name in ['uruchom_gre.py', 'tools/package_game.py']:
            z.write(ROOT / name, name)
        z.writestr('start-api.sh', '#!/bin/bash\nset -e\ncd "$(dirname "$0")/online"\nexec python3 -m uvicorn server.app:app --host 127.0.0.1 --port 3000\n')
        z.writestr('start-web.sh', '#!/bin/bash\nset -e\ncd "$(dirname "$0")/app"\nexec python3 tools/serve_web.py --host 127.0.0.1 --port 8080\n')
    with zipfile.ZipFile(TEMP) as z:
        assert z.testzip() is None
        names = z.namelist()
        assert len(names) == len(set(names))
        assert not any(n.startswith('online/data/') for n in names)
        for name in ['app/web_release/main.dart.js', 'online/server/app.py', 'app/lib/main.dart', 'uruchom_gre.py']:
            assert name in names
    TEMP.replace(DEST)
    digest = hashlib.sha256(DEST.read_bytes()).hexdigest()
    (ROOT / 'SHA256.txt').write_text(digest + '  ' + DEST.name + '\n')
    print(f'PASS ZIP: {len(names)} plików, {DEST.stat().st_size / 1024**2:.1f} MiB; SHA256 {digest}')


if __name__ == '__main__':
    main()
