# -*- coding: utf-8 -*-
"""
Ajoute les sites d'escalade MANQUANTS depuis Camp to Camp : sites C2C à > 3 km
de tout point existant, CONFIRMÉS en France (reverse-geocoding geo.api.gouv.fr →
donne aussi la commune), avec du CONTENU réel (voies >= 3 ou cotation), et
dédoublonnés entre eux. Ids neufs esc-NNNN prolongeant la séquence.

Caches reprenables : escalade-c2c-revgeo.json (commune par site),
escalade-c2c-detail.json (détail, partagé avec l'enrichisseur).

Lancer :  python tools/ajouter_escalade_c2c.py [--ecrire]
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import revue_via_ferrata as rvf
from enrichir_escalade_c2c import extraire, ROCHE  # réutilise l'extraction détail

DOSSIER = Path(__file__).resolve().parent
C2C = DOSSIER / "escalade-c2c.json"
CIBLE = DOSSIER.parent / "data" / "points.geojson"
REVGEO = DOSSIER / "escalade-c2c-revgeo.json"
DETAIL = DOSSIER / "escalade-c2c-detail.json"
STATUT = DOSSIER / "escalade-c2c-manquants-status.json"
API_DETAIL = "https://api.camptocamp.org/waypoints/"
GEO = "https://geo.api.gouv.fr/communes"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
LOIN = 3000       # m : > 3 km de tout point existant
DEDUP = 700       # m : entre nouveaux sites


def _json(url):
    for attente in (0, 8, 25):
        if attente:
            time.sleep(attente)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
    return None


def commune_de(lat, lon, cache):
    cle = f"{round(lat,4)},{round(lon,4)}"
    if cle in cache:
        return cache[cle]
    url = f"{GEO}?lat={lat}&lon={lon}&fields=nom,codeDepartement&format=json"
    arr = _json(url)
    val = None
    if isinstance(arr, list) and arr:
        val = {"nom": arr[0].get("nom", ""), "dep": arr[0].get("codeDepartement", "")}
    cache[cle] = val
    return val


def main(ecrire=False):
    sites = json.loads(C2C.read_text(encoding="utf-8"))
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    esc = [f for f in d["features"] if f["properties"].get("theme") == "escalade"]
    coords_esc = [(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1]) for f in esc]

    # candidats : sites C2C à > 3 km de TOUT point existant
    candidats = []
    for s in sites:
        dmin = min(rvf.dist_m(s["lon"], s["lat"], lo, la) for lo, la in coords_esc)
        if dmin > LOIN:
            candidats.append(s)
    print(f"{len(candidats)} sites C2C à >3 km de tout point — filtrage France + contenu…", flush=True)

    revgeo = json.loads(REVGEO.read_text(encoding="utf-8")) if REVGEO.exists() else {}
    detail = json.loads(DETAIL.read_text(encoding="utf-8")) if DETAIL.exists() else {}

    retenus = []
    for i, s in enumerate(candidats):
        com = commune_de(s["lat"], s["lon"], revgeo)
        if i % 40 == 0:
            REVGEO.write_text(json.dumps(revgeo, ensure_ascii=False), encoding="utf-8")
            STATUT.write_text(json.dumps({"phase": "revgeo", "i": i, "total": len(candidats),
                              "retenus": len(retenus), "horodatage": time.strftime("%H:%M:%S")}), encoding="utf-8")
            print(f"  {i}/{len(candidats)} (retenus {len(retenus)})…", flush=True)
        if not com:
            continue  # hors France (étranger / mer)
        cid = str(s["id"])
        if cid not in detail:
            w = _json(f"{API_DETAIL}{cid}?l=fr")
            detail[cid] = extraire(w) if w else {}
            time.sleep(0.4)
        info = detail[cid]
        voies = info.get("voies") or 0
        if not (voies and voies >= 3) and not info.get("cotation"):
            continue  # pas assez de contenu (site anecdotique / vide)
        s["_com"] = com
        s["_info"] = info
        retenus.append(s)
    REVGEO.write_text(json.dumps(revgeo, ensure_ascii=False), encoding="utf-8")
    DETAIL.write_text(json.dumps(detail, ensure_ascii=False), encoding="utf-8")

    # dédoublonnage entre nouveaux (sous-secteurs proches) : on garde le plus fourni
    retenus.sort(key=lambda s: -(s["_info"].get("voies") or 0))
    gardes = []
    for s in retenus:
        if all(rvf.dist_m(s["lon"], s["lat"], g["lon"], g["lat"]) > DEDUP for g in gardes):
            gardes.append(s)

    nums = [int(m.group(1)) for f in esc if (m := re.match(r"esc-(\d+)", f["properties"]["id"]))]
    prochain = max(nums) + 1
    neuves = []
    for k, s in enumerate(sorted(gardes, key=lambda x: x["_com"]["nom"])):
        info = s["_info"]
        det = {"type": "Site sportif"}
        if info.get("cotation"):
            det["cotation"] = info["cotation"]
        if info.get("voies"):
            det["voies"] = str(info["voies"]); det["voies_n"] = info["voies"]
        for k2 in ("roche", "hauteur", "orientation"):
            if info.get(k2):
                det[k2] = info[k2]
        if s.get("ele"):
            det["altitude"] = f"{s['ele']} m"
        neuves.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {
                "id": f"esc-{prochain + k:04d}",
                "name": s["nom"],
                "theme": "escalade",
                "description": f"Commune : {s['_com']['nom']} ({s['_com']['dep']})",
                "link": f"https://www.camptocamp.org/waypoints/{s['id']}",
                "links": [], "photos": [], "details": det,
            },
        })

    print(f"\nRetenus (France + contenu) : {len(retenus)} | après dédoublonnage : {len(gardes)} "
          f"→ {len(neuves)} sites à ajouter", flush=True)
    for f in neuves[:20]:
        p = f["properties"]
        print(f"  {p['id']} {p['name'][:34]:34s} {p['details'].get('cotation','?'):10s} "
              f"{p['details'].get('voies','?')} voies  {p['description'][10:]}")

    if ecrire and neuves:
        d["features"].extend(neuves)
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        STATUT.write_text(json.dumps({"phase": "termine", "ajoutes": len(neuves)}), encoding="utf-8")
        print(f"\nÉCRIT : +{len(neuves)} sites d'escalade (esc-{prochain:04d}…).", flush=True)
    else:
        STATUT.write_text(json.dumps({"phase": "simulation", "candidats": len(neuves)}), encoding="utf-8")
        print("\n(SIMULATION — rien écrit.)", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(ecrire="--ecrire" in sys.argv)
