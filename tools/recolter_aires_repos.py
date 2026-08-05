# -*- coding: utf-8 -*-
"""
Aires de repos aménagées (v84) — récolte OSM + audit des équipements.

Demande utilisateur : QUE des aires réellement aménagées, avec un descriptif
de ce qu'on y trouve, et de la qualité — toilettes, table, poubelle, ombre.
Trois cadres à distinguer : en ville / aire routière / montagne et nature.

⚠️ On ne prend PAS `leisure=picnic_table` seul : une table isolée au bord
d'un parking n'est pas une aire, et il y en a des dizaines de milliers en
France — la carte serait noyée pour rien.

Ce script fait d'abord un AUDIT (taux de remplissage de chaque tag) : c'est
lui qui décide quels filtres sont honnêtes à proposer. Un filtre « ombre »
n'a de sens que si le tag correspondant est réellement renseigné.

Lancer : python tools/recolter_aires_repos.py FR [--ecrire]
Sortie  : tools/aires-repos-fr.json (brut + audit)
"""

import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle; bidband4@gmail.com)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context()
CTX_NV.check_hostname = False
CTX_NV.verify_mode = ssl.CERT_NONE

# Une veine par requête : réunies, elles font tomber Overpass en 504.
VEINES = {
    "picnic": 'nwr["tourism"="picnic_site"](area.p);',
    "rest_area": 'nwr["highway"="rest_area"](area.p);',
    "services": 'nwr["highway"="services"](area.p);',
}

# Tags qui décrivent l'ÉQUIPEMENT (ce que l'utilisateur veut voir en fiche)
TAGS_EQUIPEMENT = ("picnic_table", "table", "toilets", "toilet", "drinking_water",
                   "water_point", "waste_basket", "waste_disposal", "bench",
                   "shelter", "covered", "shade", "bbq", "barbecue_grill", "fireplace",
                   "playground", "leisure", "amenity", "fee", "access", "wheelchair",
                   "dog", "opening_hours", "operator", "name", "ele", "description",
                   "natural", "surface", "lit", "parking", "motor_vehicle")


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX, CTX_NV):
            for att in (0, 30, 90, 200):
                if att:
                    time.sleep(att)
                try:
                    req = urllib.request.Request(ep, data=data, headers=UA)
                    with urllib.request.urlopen(req, timeout=500, context=ctx) as r:
                        return json.load(r)
                except urllib.error.HTTPError as e:
                    print(f"    ({ep.split('/')[2]} HTTP {e.code})", flush=True)
                    if e.code in (429, 504):
                        continue
                    break
                except Exception as e:
                    print(f"    ({ep.split('/')[2]} : {str(e)[:60]})", flush=True)
    return None


def _centre(e):
    if e.get("lat") is not None:
        return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")


def recolter(iso="FR"):
    cache = DOSSIER / f"aires-repos-{iso.lower()}.json"
    deja = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for cle, sel in VEINES.items():
        if cle in deja:
            print(f"  {cle}: déjà en cache ({len(deja[cle])})", flush=True)
            continue
        req = ('[out:json][timeout:400];'
               f'area["ISO3166-1"="{iso}"][admin_level=2]->.p;'
               f'({sel});out center tags;')
        d = _post(req)
        if d is None:
            print(f"  {cle}: ÉCHEC réseau", flush=True)
            continue
        pts = []
        for e in d.get("elements", []):
            lat, lon = _centre(e)
            if lat is None:
                continue
            t = e.get("tags", {})
            pts.append({
                "osm": f'{e.get("type","node")[0]}{e.get("id")}',
                "lat": round(lat, 6), "lon": round(lon, 6),
                "tags": {k: v for k, v in t.items() if k in TAGS_EQUIPEMENT},
            })
        deja[cle] = pts
        cache.write_text(json.dumps(deja, ensure_ascii=False), encoding="utf-8")
        print(f"  {cle}: {len(pts)}", flush=True)
        time.sleep(5)
    return deja


def auditer(par_veine):
    """Combien d'aires renseignent réellement chaque équipement ?
    Un filtre ne se propose que si son tag est assez rempli."""
    tous = [p for v in par_veine.values() for p in v]
    n = len(tous)
    print(f"\n=== AUDIT sur {n} aires ===")
    interet = ["name", "toilets", "picnic_table", "drinking_water", "waste_basket",
               "shelter", "covered", "shade", "bench", "fireplace", "bbq",
               "wheelchair", "fee", "access", "ele", "opening_hours", "description"]
    for k in interet:
        c = sum(1 for p in tous if p["tags"].get(k))
        if n:
            print(f"  {k:16} {c:6}  ({100*c/n:5.1f} %)")
    # valeurs les plus fréquentes des tags décisifs
    for k in ("toilets", "picnic_table", "shelter", "access"):
        vals = Counter(p["tags"].get(k) for p in tous if p["tags"].get(k))
        if vals:
            print(f"  → {k} : {dict(vals.most_common(5))}")
    return n


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    iso = next((a.upper() for a in sys.argv[1:] if not a.startswith("--")), "FR")
    par_veine = recolter(iso)
    for cle, v in par_veine.items():
        print(f"  {cle}: {len(v)}")
    auditer(par_veine)
