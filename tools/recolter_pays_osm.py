# -*- coding: utf-8 -*-
"""
Récolte OSM GÉNÉRIQUE d'un pays européen (Suisse, Italie, Espagne…) : refuges,
campings, lacs, cascades, grottes, via ferrata, châteaux, musées — les FAITS
(ODbL, attribution déjà affichée dans l'app), nom obligatoire partout.

Un sélecteur = une requête `area ISO3166-1` (jamais de bbox), `out center`,
retries longs (Overpass rate-limite). Les images ne sont gardées que si
hébergées sur upload.wikimedia.org (CSP).

Lancer :  python tools/recolter_pays_osm.py CH IT ES   (ou un seul)
Sortie   :  tools/pays-<iso>-osm.json
"""

import json
import ssl
import sys
import time
import urllib.error
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

# catégorie -> sélecteur Overpass (name obligatoire)
SELECTEURS = {
    "refuge": '(nwr["tourism"="alpine_hut"]["name"](area.p);nwr["tourism"="wilderness_hut"]["name"](area.p););',
    "camping": '(nwr["tourism"="camp_site"]["name"](area.p););',
    "lac": '(nwr["natural"="water"]["water"~"^(lake|reservoir)$"]["name"](area.p););',
    "cascade": '(nwr["waterway"="waterfall"]["name"](area.p););',
    "grotte": '(nwr["natural"="cave_entrance"]["name"](area.p););',
    "via-ferrata": '(nwr["sport"="via_ferrata"]["name"](area.p);nwr["highway"="via_ferrata"]["name"](area.p););',
    "chateau": '(nwr["historic"="castle"]["name"](area.p););',
    "culture": '(nwr["tourism"="museum"]["name"](area.p););',
}
TAGS_UTILES = ("ele", "capacity", "height", "website", "contact:website", "opening_hours",
               "via_ferrata_scale", "castle_type", "description", "image", "fee", "ruins")


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX, CTX_NV):
            for att in (0, 30, 90, 180):
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
    sortie = DOSSIER / f"pays-{iso.lower()}-osm.json"
    deja = json.loads(sortie.read_text(encoding="utf-8")) if sortie.exists() else {}
    area = f'area["ISO3166-1"="{iso}"][admin_level=2]->.p;'
    donnees = dict(deja)
    for cat, sel in SELECTEURS.items():
        if cat in donnees:
            print(f"  {iso} {cat}: déjà en cache ({len(donnees[cat])})", flush=True)
            continue
        corps = f"[out:json][timeout:400];{area}{sel}out tags center;"
        d = _post(corps)
        objets, vus = [], set()
        for el in d.get("elements", []):
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            t = el.get("tags", {})
            nom = (t.get("name") or "").strip()
            if lat is None or not nom:
                continue
            cle = f"{el['type'][0]}{el['id']}"
            if cle in vus:
                continue
            vus.add(cle)
            garde = {k: str(t[k]).strip() for k in TAGS_UTILES if t.get(k)}
            if not (garde.get("image") or "").startswith("https://upload.wikimedia.org"):
                garde.pop("image", None)
            garde["website"] = garde.get("website") or garde.pop("contact:website", "")
            objets.append({"nom": nom, "lat": round(lat, 6), "lon": round(lon, 6), "tags": garde})
        donnees[cat] = objets
        sortie.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
        print(f"  {iso} {cat}: {len(objets)}", flush=True)
        time.sleep(10)
    print(f"{iso} TERMINÉ -> {sortie.name} : " +
          ", ".join(f"{k} {len(v)}" for k, v in donnees.items()), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for iso in [a.upper() for a in sys.argv[1:]] or ["CH", "IT", "ES"]:
        recolter(iso)
