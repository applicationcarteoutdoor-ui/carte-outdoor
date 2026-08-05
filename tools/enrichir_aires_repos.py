# -*- coding: utf-8 -*-
"""
Équipements des aires de repos — par PROXIMITÉ, pas par étiquette (v84).

Constat de l'audit (18 401 aires françaises) : les tags de l'aire elle-même
sont quasi vides — toilettes 8,5 %, table 1 %, poubelle 0,2 %, ombre 1 seul
objet dans tout le pays. Un filtre bâti là-dessus mentirait, puisqu'une aire
non renseignée n'est pas une aire sans équipement.

La raison est structurelle : dans OSM, une aire de pique-nique est un ENCLOS,
et les tables, toilettes et poubelles sont des objets DISTINCTS posés
dedans. Il faut donc regarder le voisinage.

Gain mesuré sur les toilettes : 997 aires via le tag → 3 904 via la
proximité (100 m), en croisant simplement le fichier data/toilettes.geojson
que l'application possède déjà.

Règle de restitution : un équipement n'est affiché que s'il est CONSTATÉ.
L'absence de mention veut dire « non renseigné », jamais « absent » — et la
fiche le dit.

Lancer : python tools/enrichir_aires_repos.py [--ecrire]
"""

import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
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

RAYON = 100      # m : au-delà, l'équipement n'appartient plus à l'aire
PAS = 0.004      # grille ~300 m au pire (longitude, hautes latitudes)

# Objets à récolter pour qualifier les aires. Volumes élevés mais une seule
# requête chacun, et le croisement se fait ensuite hors ligne.
VOISINS = {
    "table": 'nwr["leisure"="picnic_table"](area.p);',
    "poubelle": 'nwr["amenity"="waste_basket"](area.p);',
    "banc": 'nwr["amenity"="bench"](area.p);',
    "jeux": 'nwr["leisure"="playground"](area.p);',
}


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX, CTX_NV):
            for att in (0, 30, 90, 200):
                if att:
                    time.sleep(att)
                try:
                    req = urllib.request.Request(ep, data=data, headers=UA)
                    with urllib.request.urlopen(req, timeout=600, context=ctx) as r:
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


def hav_m(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def grille(points):
    g = {}
    for la, lo in points:
        g.setdefault((math.floor(la / PAS), math.floor(lo / PAS)), []).append((la, lo))
    return g


def proche(g, la, lo, rayon=RAYON):
    cx, cy = math.floor(la / PAS), math.floor(lo / PAS)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for (qa, qo) in g.get((cx + dx, cy + dy), ()):
                if hav_m(la, lo, qa, qo) <= rayon:
                    return True
    return False


def recolter_voisins(iso="FR"):
    cache = DOSSIER / f"aires-voisins-{iso.lower()}.json"
    deja = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for cle, sel in VOISINS.items():
        if cle in deja:
            print(f"  {cle}: déjà en cache ({len(deja[cle])})", flush=True)
            continue
        req = ('[out:json][timeout:600];'
               f'area["ISO3166-1"="{iso}"][admin_level=2]->.p;'
               f'({sel});out center;')
        d = _post(req)
        if d is None:
            print(f"  {cle}: ÉCHEC réseau — équipement ignoré", flush=True)
            deja[cle] = []
        else:
            pts = []
            for e in d.get("elements", []):
                la, lo = _centre(e)
                if la is not None:
                    pts.append([round(la, 6), round(lo, 6)])
            deja[cle] = pts
            print(f"  {cle}: {len(pts)}", flush=True)
        cache.write_text(json.dumps(deja), encoding="utf-8")
        time.sleep(5)
    return deja


def enrichir():
    aires_par_veine = json.loads((DOSSIER / "aires-repos-fr.json").read_text(encoding="utf-8"))
    voisins = recolter_voisins("FR")

    # les toilettes sont DÉJÀ dans l'application : aucun appel réseau
    wc = json.loads((RACINE / "data" / "toilettes.geojson").read_text(encoding="utf-8"))
    g_wc = grille([(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0])
                   for f in wc["features"]])
    eau = json.loads((RACINE / "data" / "eau.geojson").read_text(encoding="utf-8"))
    g_eau = grille([(f["geometry"]["coordinates"][1], f["geometry"]["coordinates"][0])
                    for f in eau["features"]])
    grilles = {"toilettes": g_wc, "eau": g_eau}
    for cle, pts in voisins.items():
        grilles[cle] = grille([(a, b) for a, b in pts])

    enrichies = []
    for veine, liste in aires_par_veine.items():
        for p in liste:
            t = p["tags"]
            eq = set()
            # 1) ce que l'aire déclare elle-même (rare mais fiable)
            if (t.get("toilets") or "") in ("yes", "separate"):
                eq.add("toilettes")
            if (t.get("picnic_table") or "").lower() not in ("", "no"):
                eq.add("table")
            if (t.get("drinking_water") or "") == "yes":
                eq.add("eau")
            if t.get("waste_basket"):
                eq.add("poubelle")
            if (t.get("shelter") or "") == "yes" or (t.get("covered") or "") == "yes":
                eq.add("abri")
            if t.get("fireplace") or t.get("bbq"):
                eq.add("barbecue")
            # 2) ce que le VOISINAGE révèle (le gros de l'information)
            for nom, g in grilles.items():
                if proche(g, p["lat"], p["lon"]):
                    eq.add(nom)
            p["equipements"] = sorted(eq)
            p["veine"] = veine
            enrichies.append(p)

    n = len(enrichies)
    print(f"\n=== ÉQUIPEMENTS CONSTATÉS sur {n} aires ===")
    from collections import Counter
    c = Counter(e for p in enrichies for e in p["equipements"])
    for nom, k in c.most_common():
        print(f"  {nom:12} {k:6}  ({100*k/n:5.1f} %)")
    sans = sum(1 for p in enrichies if not p["equipements"])
    print(f"  {'(aucun)':12} {sans:6}  ({100*sans/n:5.1f} %)")

    (DOSSIER / "aires-repos-enrichies.json").write_text(
        json.dumps(enrichies, ensure_ascii=False), encoding="utf-8")
    print("ÉCRIT tools/aires-repos-enrichies.json")
    return enrichies


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    enrichir()
