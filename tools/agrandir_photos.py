# -*- coding: utf-8 -*-
"""
Augmente la qualité des photos Wikimedia de data/points.geojson : les vignettes
historiques à 500 px passent à 960 px (taille NORMALISÉE Wikimedia — 900 px
répond « HTTP 400 Use thumbnail sizes listed ») quand l'ORIGINAL est assez
grand (Wikimedia refuse d'agrandir au-delà de la source).

Méthode : la largeur réelle des originaux est demandée à l'API Commons
`prop=imageinfo&iiprop=size` par LOTS DE 50 fichiers (≈ 40 requêtes au total) —
PAS de HEAD sur upload.wikimedia (rate-limité en rafale : des 429 avaient fait
passer 97 % des images pour « trop petites »). Cache, idempotent.

Lancer :  python tools/agrandir_photos.py
"""

import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
POINTS = RACINE / "data" / "points.geojson"
CACHE = RACINE / "tools" / "photos-largeurs-cache.json"
API = "https://commons.wikimedia.org/w/api.php"
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle ; contact bidband4@gmail.com)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE
CIBLE = 960


def _get(url):
    for ctx in (CTX, CTX_NV):
        for attente in (0, 20, 60):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90, context=ctx) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    continue
                raise
            except Exception as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("API Commons injoignable")


def nom_fichier(url_thumb):
    """…/thumb/8/8d/Nom_du_fichier.JPG/500px-… → Nom_du_fichier.JPG (décodé)."""
    m = re.search(r"/thumb/[0-9a-f]/[0-9a-f]{2}/([^/]+)/", url_thumb)
    return urllib.parse.unquote(m.group(1)) if m else None


def main():
    d = json.loads(POINTS.read_text(encoding="utf-8"))
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

    urls = set()
    for f in d["features"]:
        for p in f["properties"].get("photos") or []:
            if "upload.wikimedia.org" in p and "/500px-" in p:
                urls.add(p)
    fichiers = {}
    for u in urls:
        nf = nom_fichier(u)
        if nf:
            fichiers.setdefault(nf, []).append(u)
    a_demander = [nf for nf in fichiers if nf not in cache]
    print(f"{len(urls)} photos 500px, {len(fichiers)} fichiers ({len(a_demander)} à interroger)", flush=True)

    for i in range(0, len(a_demander), 50):
        lot = a_demander[i:i + 50]
        q = urllib.parse.urlencode({
            "action": "query", "titles": "|".join("File:" + nf.replace("_", " ") for nf in lot),
            "prop": "imageinfo", "iiprop": "size", "redirects": 1, "format": "json",
        })
        rep = _get(f"{API}?{q}")
        pages = (rep.get("query") or {}).get("pages", {})
        # normalisations : titre demandé -> titre final
        vers = {}
        for r in (rep.get("query") or {}).get("normalized", []) + (rep.get("query") or {}).get("redirects", []):
            vers[r["from"]] = r["to"]
        largeur_par_titre = {}
        for p in pages.values():
            ii = (p.get("imageinfo") or [{}])[0]
            largeur_par_titre[p.get("title", "")] = ii.get("width", 0)
        for nf in lot:
            t = "File:" + nf.replace("_", " ")
            seen = set()
            while t in vers and t not in seen:
                seen.add(t)
                t = vers[t]
            cache[nf] = largeur_par_titre.get(t, 0)
        CACHE.write_text(json.dumps(cache), encoding="utf-8")
        print(f"  {min(i + 50, len(a_demander))}/{len(a_demander)}…", flush=True)
        time.sleep(1.2)

    remplacees = 0
    for f in d["features"]:
        photos = f["properties"].get("photos") or []
        for i, p in enumerate(photos):
            nf = nom_fichier(p) if ("upload.wikimedia.org" in p and "/500px-" in p) else None
            if nf and cache.get(nf, 0) >= CIBLE:
                photos[i] = p.replace("/500px-", f"/{CIBLE}px-")
                remplacees += 1
    POINTS.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    petites = sum(1 for nf in fichiers if 0 < cache.get(nf, 0) < CIBLE)
    print(f"ÉCRIT : {remplacees} photos passées à {CIBLE}px ; {petites} originaux < {CIBLE}px restent à 500px")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
