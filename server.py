#!/usr/bin/env python3
"""
server.py — serve the Coursera "My Learning" clone as https://www.coursera.org/…

Binds 127.0.0.1 on :80 and :443 (hosts points coursera.org here), reuses the
trusted self-signed cert from ../fake_coursera so the padlock stays valid.
The my-learning SPA route is served index.html for any ?myLearningTab value.

Run as root (ports < 1024):  sudo python3 server.py
"""

import os
import ssl
import threading
from urllib.parse import urlparse, parse_qs
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
# project-local cert (created by setup.py / gen_cert.py) — fully portable
CERT = os.path.join(HERE, 'cert.pem')
KEY = os.path.join(HERE, 'key.pem')
# legacy fallback for the original dev machine
if not os.path.exists(CERT):
    CERT = os.path.join(HERE, '..', 'fake_coursera', 'cert.pem')
    KEY = os.path.join(HERE, '..', 'fake_coursera', 'key.pem')


class Handler(SimpleHTTPRequestHandler):
    server_version = 'AkamaiGHost'
    sys_version = ''
    # cert previews were captured with an ambiguous type and saved as .bin (JPEG);
    # real certificates are served as .jpg previews and .pdf downloads
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      '.bin': 'image/jpeg', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
                      '.pdf': 'application/pdf', '.json': 'application/json'}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=os.path.join(HERE, 'site'), **k)

    def translate_path(self, path):
        parsed = urlparse(path)
        clean = parsed.path
        site = os.path.join(HERE, 'site')
        # shared asset pool
        if clean.startswith('/_res/'):
            return os.path.join(site, '_res', os.path.basename(clean))
        # the My Learning page: pick the captured tab from ?myLearningTab=
        if '/my-learning' in clean or clean in ('/', ''):
            q = parse_qs(parsed.query)
            tab = (q.get('myLearningTab', ['IN_PROGRESS'])[0]).upper()
            valid = {'IN_PROGRESS', 'COMPLETED', 'SAVED', 'CERTIFICATES'}
            if tab not in valid:
                tab = 'IN_PROGRESS'
            return os.path.join(site, 'tabs', f'{tab}.html')
        # fall back to any real file under ./site
        p = super().translate_path(path)
        return p

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        super().end_headers()

    def log_message(self, fmt, *args):
        print(f'[{self.address_string()}] {self.command} {self.path}')


def serve(port, tls):
    srv = ThreadingHTTPServer(('127.0.0.1', port), Handler)
    if tls:
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(certfile=CERT, keyfile=KEY)
        srv.socket = ctx.wrap_socket(srv.socket, server_side=True)
    print(f'{"HTTPS" if tls else "HTTP "} clone on 127.0.0.1:{port}')
    srv.serve_forever()


if __name__ == '__main__':
    if not os.path.exists(CERT):
        raise SystemExit(f'Cert not found at {CERT}. Run:  python gen_cert.py   (or python setup.py) first.')
    threads = [threading.Thread(target=serve, args=(p, tls), daemon=True)
               for p, tls in ((80, False), (443, True))]
    for t in threads:
        t.start()
    print('Serving Coursera clone. Open https://www.coursera.org/organizations/viot/my-learning')
    print('Ctrl-C to stop.')
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        print('\nstopped.')
