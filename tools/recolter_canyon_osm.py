# -*- coding: utf-8 -*-
"""
Récolte OpenStreetMap (ODbL) des descentes de canyon — relations
`type=route` + `route=canyoning`. Complément du socle RES : apporte les seuls
FAITS libres qui manquent au RES, là où ils existent (couverture ~2 % en France) :
  - cotation FFME (tag `rating`, format « v# a# <chiffre romain> »),
  - hauteur du plus grand rappel (tag `max:abseil`, en m) → sert à ESTIMER la
    corde recommandée (comme l'escalade), jamais recopiée d'un topo,
  - site web (`website` / `website:fr`),
  - **tracé** : reconstruit depuis la géométrie des ways membres de la relation
    (le cours d'eau = la ligne de descente), en MultiLineString.

Bbox large volontaire (déborde sur les pays voisins) : sans importance, la fusion
ne garde que les canyons OSM qui rapprochent d'un canyon RES français.
ATTENTION : aucune prose ni photo OSM (il n'y en a pas) — seulement des faits.

Lancer :  python tools/recolter_canyon_osm.py
Sortie   :  tools/canyon-osm.json
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
SORTIE = DOSSIER / "canyon-osm.json"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
# `out geom;` renvoie les TAGS de la relation + la géométrie des ways membres.
# (ATTENTION : `out tags geom;` est contradictoire — tags exclut la géométrie —
#  et fait renvoyer un résultat vide.)
# Métropole via l'area officielle (Corse incluse) + Réunion via bbox (célèbres
# canyons de l'île). Les DOM Antilles sont couverts par le socle RES ; OSM y est
# vide, on ne les interroge donc pas.
REQUETES = [
    ('area["ISO3166-1"="FR"][admin_level=2]->.fr;'
     'relation["route"="canyoning"](area.fr);'),
    ('relation["route"="canyoning"](-21.4,55.2,-20.8,55.9);'),  # La Réunion
]
CTX_DEF = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE


def _post(corps):
    """POST Overpass avec bascule d'endpoint et de contexte SSL (CA local périmé)."""
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX_DEF, CTX_NV):
            for attente in (0, 15, 45):
                if attente:
                    time.sleep(attente)
                try:
                    req = urllib.request.Request(ep, data=data, headers=UA)
                    with urllib.request.urlopen(req, timeout=180, context=ctx) as r:
                        return json.load(r)
                except urllib.error.HTTPError as e:
                    print(f"    ({ep.split('/')[2]} HTTP {e.code})", flush=True)
                    if e.code in (429, 504):
                        continue
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
                    print(f"    ({ep.split('/')[2]} : {e})", flush=True)
    raise RuntimeError("Overpass injoignable")


def _centroide(segments):
    pts = [p for seg in segments for p in seg]
    if not pts:
        return None, None
    return (round(sum(p[1] for p in pts) / len(pts), 6),
            round(sum(p[0] for p in pts) / len(pts), 6))  # lat, lon


def recolter():
    vus = {}  # id relation -> canyon (dédoublonnage inter-requête)
    for i, sel in enumerate(REQUETES):
        corps = f"[out:json][timeout:180];{sel}out geom;"
        d = _post(corps)
        if d.get("remark"):
            print(f"    (remark Overpass : {d['remark']})", flush=True)
        for el in d.get("elements", []):
            if el.get("type") != "relation":
                continue
            rid = el["id"]
            if rid in vus:
                continue
            t = el.get("tags", {})
            # tracé : géométrie de chaque way membre -> liste de segments [[lon,lat],...]
            segments = []
            for m in el.get("members", []):
                g = m.get("geometry")
                if g and len(g) >= 2:
                    segments.append([[round(p["lon"], 6), round(p["lat"], 6)] for p in g])
            lat, lon = _centroide(segments)
            if lat is None:
                continue
            vus[rid] = {
                "osm_id": rid,
                "nom": (t.get("name") or t.get("name:fr") or "").strip(),
                "lat": lat, "lon": lon,
                "rating": (t.get("rating") or t.get("canyon:rating") or "").strip(),
                "abseil": t.get("max:abseil") or t.get("abseil") or "",
                "website": (t.get("website") or t.get("website:fr") or "").strip(),
                "segments": segments,
            }
        print(f"  requête {i + 1}/{len(REQUETES)} : {len(vus)} relations canyoning cumulées", flush=True)
        time.sleep(5)
    canyons = list(vus.values())
    SORTIE.write_text(json.dumps(canyons, ensure_ascii=False), encoding="utf-8")
    avec_trace = sum(1 for c in canyons if c["segments"])
    avec_cot = sum(1 for c in canyons if c["rating"])
    avec_rap = sum(1 for c in canyons if c["abseil"])
    print(f"\nÉCRIT : {len(canyons)} canyons OSM -> {SORTIE.name} "
          f"(tracé {avec_trace}, cotation {avec_cot}, rappel {avec_rap})", flush=True)
    return canyons


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
