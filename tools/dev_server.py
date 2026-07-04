# -*- coding: utf-8 -*-
"""
Serveur de développement : comme `python -m http.server`, mais envoie
Cache-Control: no-store pour que ni le navigateur ni un proxy ne servent
d'anciennes versions des fichiers pendant le développement.

(En production — GitHub Pages, Netlify… — c'est le service worker et sa
constante VERSION qui gèrent la mise à jour.)

Usage :  python tools/dev_server.py [port]
"""

import sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler


class SansCache(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass  # silencieux


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123
    print(f"Serveur de dev sur http://localhost:{port} (cache désactivé)", flush=True)
    # Threading : indispensable, le navigateur ouvre plusieurs connexions en parallèle
    ThreadingHTTPServer(("", port), SansCache).serve_forever()
