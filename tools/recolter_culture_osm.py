# -*- coding: utf-8 -*-
"""
Récolte OpenStreetMap (ODbL) de la catégorie CULTURE — France et
Nouvelle-Zélande : musées, galeries d'art, sites archéologiques, monuments.
FAITS seulement : nom, position, site web, horaires d'ouverture, description
courte quand elle existe ; l'image n'est gardée QUE si elle est hébergée sur
upload.wikimedia.org (seul hôte d'images autorisé par la CSP de l'app).

Lancer :  python tools/recolter_culture_osm.py [fr|nz]   (défaut : les deux)
Sortie   :  tools/culture-fr-osm.json / tools/culture-nz-osm.json
"""

import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

SELECTEURS = {
    "musee": '["tourism"="museum"]',
    "galerie": '["tourism"="gallery"]',
    "archeo": '["historic"="archaeological_site"]',
    "monument": '["historic"="monument"]',
}


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX, CTX_NV):
            for att in (0, 30, 90):
                if att:
                    time.sleep(att)
                try:
                    req = urllib.request.Request(ep, data=data, headers=UA)
                    with urllib.request.urlopen(req, timeout=400, context=ctx) as r:
                        return json.load(r)
                except urllib.error.HTTPError as e:
                    print(f"    ({ep.split('/')[2]} HTTP {e.code})", flush=True)
                    if e.code in (429, 504):
                        continue
                    break
                except Exception as e:
                    print(f"    ({ep.split('/')[2]} : {e})", flush=True)
    raise RuntimeError("Overpass injoignable")


def recolter(iso):
    sortie = DOSSIER / f"culture-{iso.lower()}-osm.json"
    area = f'area["ISO3166-1"="{iso}"][admin_level=2]->.p;'
    objets = {}
    for type_, sel in SELECTEURS.items():
        corps = f'[out:json][timeout:400];{area}(nwr{sel}["name"](area.p););out tags center;'
        d = _post(corps)
        n = 0
        for el in d.get("elements", []):
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            t = el.get("tags", {})
            nom = (t.get("name") or "").strip()
            if lat is None or not nom:
                continue
            cle = f"{el['type'][0]}{el['id']}"
            if cle in objets:
                continue
            image = (t.get("image") or "").strip()
            if not image.startswith("https://upload.wikimedia.org"):
                image = ""  # CSP : seul hôte d'images autorisé
            objets[cle] = {
                "type": type_,
                "nom": nom,
                "lat": round(lat, 6), "lon": round(lon, 6),
                "site": (t.get("website") or t.get("contact:website") or "").strip(),
                "horaires": (t.get("opening_hours") or "").strip(),
                "description": (t.get("description") or t.get("description:fr") or "").strip()[:300],
                "image": image,
                "commune": (t.get("addr:city") or "").strip(),
            }
            n += 1
        print(f"  {iso} {type_}: {n}", flush=True)
        time.sleep(8)
    liste = list(objets.values())
    sortie.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    print(f"ÉCRIT {sortie.name} : {len(liste)} lieux", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cibles = [a for a in sys.argv[1:] if a in ("fr", "nz")] or ["fr", "nz"]
    for c in cibles:
        recolter(c.upper())
