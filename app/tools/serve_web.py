"""Serwer podglądu Flutter Web dla City Empire.

Serwuje build/web i przekazuje /api/* do backendu (domyślnie http://127.0.0.1:3000).
Dzięki temu aplikacja i API mają ten sam origin — działa za proxy podglądu i bez CORS.
Nagłówek Host jest przekazywany bez zmian (backend porównuje go z Origin przy POST).

Użycie: python3 tools/serve_web.py [--port 8080] [--backend http://127.0.0.1:3000]
"""
import argparse
import http.client
import os
from pathlib import Path
from zipfile import ZipFile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# build/web (świeży build) albo web_release/ (kopia przetrwająca reset sandboxa; canvaskit z CDN)
ROOT = os.path.join(_APP, 'build', 'web')
if not os.path.exists(os.path.join(ROOT, 'main.dart.js')):
    ROOT = os.path.join(_APP, 'web_release')
# Gotowy build jest także w pełnym ZIP-ie. Po czyszczeniu artefaktów odtwarzamy
# wyłącznie jego podkatalog do build/web (nie nadpisujemy źródeł ani bazy).
if not os.path.exists(os.path.join(ROOT, 'main.dart.js')):
    archive = Path(_APP).resolve().parent / 'city-empire-online-0.60.0-gdd32.zip'
    if archive.is_file():
        target = Path(_APP).resolve() / 'build' / 'web'
        with ZipFile(archive) as z:
            for name in z.namelist():
                if not name.startswith('app/web_release/') or name.endswith('/'):
                    continue
                relative = Path(name.removeprefix('app/web_release/'))
                if relative.is_absolute() or '..' in relative.parts:
                    raise ValueError('Nieprawidłowa ścieżka w paczce WWW')
                dest = target / relative
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(z.read(name))
        ROOT = str(target)

HOP = {'connection', 'keep-alive', 'transfer-encoding', 'te', 'trailer', 'upgrade', 'proxy-authorization', 'proxy-authenticate'}


def _ver():
    """Wersja buildu = czas modyfikacji main.dart.js (zmienia się przy każdym buildzie)."""
    import time
    return time.strftime('%m%d-%H%M', time.localtime(os.path.getmtime(os.path.join(ROOT, 'main.dart.js'))))


def _index_html():
    """index.html + wersja w adresie bootstrapu, sprzątanie starych service workerów i znacznik wersji."""
    v = _ver()
    html = open(os.path.join(ROOT, 'index.html'), 'rb').read().decode('utf-8')
    html = html.replace('flutter_bootstrap.js', 'flutter_bootstrap.js?v=' + v)
    extra = (
        "<script>if('serviceWorker' in navigator){navigator.serviceWorker.getRegistrations()"
        ".then(function(rs){rs.forEach(function(r){r.unregister()})});}"
        "if(window.caches){caches.keys().then(function(ks){ks.forEach(function(k){caches.delete(k)})});}</script>"
        # UI v2: na telefonie (< 600 px) znacznik nad dolnym paskiem nawigacji — nie nachodzi na podpisy ikon
        "<style>#ce-ver{position:fixed;right:8px;bottom:6px;z-index:99999;pointer-events:none;"
        "font:11px sans-serif;color:rgba(74,168,255,.75)}"
        "@media(max-width:599px){#ce-ver{bottom:84px;right:6px;font-size:9px;opacity:.6}}</style>"
        "<div id='ce-ver'>wersja " + v + "</div>"
    )
    return html.replace('</body>', extra + '</body>').encode('utf-8')


class Handler(SimpleHTTPRequestHandler):
    backend = urlsplit('http://127.0.0.1:3000')

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def log_message(self, fmt, *args):  # cichszy log: tylko API
        if self.path.startswith('/api/'):
            super().log_message(fmt, *args)

    def _proxy(self):
        length = int(self.headers.get('content-length') or 0)
        body = self.rfile.read(length) if length else None
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP}
        conn = http.client.HTTPConnection(self.backend.hostname, self.backend.port or 80, timeout=30)
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            r = conn.getresponse()
            data = r.read()
        except OSError as e:
            self.send_error(502, f'Backend niedostępny: {e}')
            return
        finally:
            conn.close()
        self.send_response(r.status)
        for k, v in r.getheaders():
            if k.lower() not in HOP and k.lower() != 'content-length':
                self.send_header(k, v)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _spa(self):
        # Ścieżki go_router (/login, /dashboard…) → index.html
        path = self.translate_path(self.path.split('?')[0])
        if not os.path.exists(path):
            self.path = '/index.html'
        if self.path in ('/', '/index.html'):
            self.send_response(200)
            data = _index_html()
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        super().do_GET()

    def do_GET(self):
        if self.path.split('?')[0] == '/flutter_bootstrap.js':
            # bootstrap z wersją w adresie main.dart.js → cache przeglądarki / CDN nie poda starej kopii
            data = open(os.path.join(ROOT, 'flutter_bootstrap.js'), 'rb').read().replace(b'main.dart.js', b'main.dart.js?v=' + _ver().encode())
            self.send_response(200)
            self.send_header('Content-Type', 'application/javascript')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        self._proxy() if self.path.startswith('/api/') else self._spa()

    def do_POST(self):
        self._proxy() if self.path.startswith('/api/') else self.send_error(405)

    do_PATCH = do_PUT = do_DELETE = do_POST

    def end_headers(self):
        if not self.path.startswith('/api/'):
            self.send_header('Cache-Control', 'no-store, max-age=0')
        super().end_headers()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', default='0.0.0.0')
    ap.add_argument('--port', type=int, default=8080)
    ap.add_argument('--backend', default='http://127.0.0.1:3000')
    a = ap.parse_args()
    Handler.backend = urlsplit(a.backend)
    print(f'City Empire Web → http://{a.host}:{a.port}  (API → {a.backend})', flush=True)
    ThreadingHTTPServer((a.host, a.port), Handler).serve_forever()
