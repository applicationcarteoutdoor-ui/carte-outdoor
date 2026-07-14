# -*- coding: utf-8 -*-
"""
Prépare data/monde.geojson pour la page de garde (carte du monde cliquable).

Source : Natural Earth 110m « admin 0 – countries » (DOMAINE PUBLIC), via le
miroir geojson.xyz. On ne garde que le nom + le code ISO2 et on arrondit les
coordonnées à 2 décimales (~1 km — largement assez au zoom monde) pour un
fichier léger, pré-cachable par le service worker (la page de garde marche
alors hors ligne).

Piège Natural Earth connu : la France (et la Norvège) ont ISO_A2 = "-99" dans
certaines éditions (à cause des territoires) → correction par NOM.

Lancer :  python tools/preparer_monde.py
Sortie   :  data/monde.geojson
"""

import json
import ssl
import sys
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE = RACINE / "data" / "monde.geojson"
URL = "https://d2ad6b4ur7yvpq.cloudfront.net/naturalearth-3.3.0/ne_110m_admin_0_countries.geojson"
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

ISO_PAR_NOM = {"France": "FR", "Norway": "NO"}  # ISO_A2 = -99 dans Natural Earth


def arrondir(coords):
    if isinstance(coords[0], (int, float)):
        return [round(coords[0], 2), round(coords[1], 2)]
    return [arrondir(c) for c in coords]


def main():
    for ctx in (CTX, CTX_NV):
        try:
            with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=120, context=ctx) as r:
                monde = json.load(r)
            break
        except Exception as e:
            print(f"  ({e})", flush=True)
    else:
        raise RuntimeError("Natural Earth injoignable")

    feats = []
    for f in monde["features"]:
        p = f.get("properties", {})
        nom = p.get("name") or p.get("NAME") or ""
        if nom == "Antarctica":
            continue  # vide et encombrant au bas de la page de garde
        iso = (p.get("iso_a2") or p.get("ISO_A2") or "").upper()
        if iso in ("-99", ""):
            iso = ISO_PAR_NOM.get(nom, "")
        feats.append({
            "type": "Feature",
            "geometry": {"type": f["geometry"]["type"],
                         "coordinates": arrondir(f["geometry"]["coordinates"])},
            "properties": {"nom": nom, "iso": iso},
        })
    SORTIE.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                 ensure_ascii=False), encoding="utf-8")
    fr = sum(1 for f in feats if f["properties"]["iso"] == "FR")
    nz = sum(1 for f in feats if f["properties"]["iso"] == "NZ")
    print(f"ÉCRIT {SORTIE.name} : {len(feats)} pays, {SORTIE.stat().st_size // 1024} Ko "
          f"(FR trouvé : {fr}, NZ trouvé : {nz})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
