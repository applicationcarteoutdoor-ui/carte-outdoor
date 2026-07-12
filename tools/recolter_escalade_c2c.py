# -*- coding: utf-8 -*-
"""
Récolte des sites d'escalade de Camp to Camp (camptocamp.org) — LA base de
référence francophone (licence CC-BY-SA). API publique, waypoints de type
`climbing_outdoor`. Sert à la revue de la catégorie « escalade » : recalage GPS
précis, ajout des sites manquants, et lien direct C2C.

Endpoint liste : coordonnées (EPSG:3857 → WGS84), titre, altitude, régions,
document_id (→ lien https://www.camptocamp.org/waypoints/ID). Les cotations /
type de roche / description viennent du détail (recolter_escalade_c2c_detail.py).

Lancer :  python tools/recolter_escalade_c2c.py
Sortie   :  tools/escalade-c2c.json  (liste de sites {id,nom,lat,lon,ele,regions})
"""

import json
import math
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "escalade-c2c.json"
STATUT = DOSSIER / "escalade-c2c-status.json"
API = "https://api.camptocamp.org/waypoints"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
R = 20037508.342789244  # demi-circonférence Web Mercator


def merc_wgs(x, y):
    lon = x / R * 180
    lat = math.degrees(2 * math.atan(math.exp(y / R * math.pi)) - math.pi / 2)
    return round(lon, 6), round(lat, 6)


def _get(url):
    for attente in (0, 10, 30, 60):
        if attente:
            time.sleep(attente)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return json.load(r)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("C2C injoignable")


def recolter():
    sites, offset, total = [], 0, None
    while True:
        url = f"{API}?wtyp=climbing_outdoor&limit=100&offset={offset}"
        d = _get(url)
        total = d.get("total")
        docs = d.get("documents", [])
        if not docs:
            break
        for w in docs:
            try:
                geom = json.loads(w["geometry"]["geom"])
                lon, lat = merc_wgs(*geom["coordinates"])
            except Exception:
                continue
            titre = ""
            for l in w.get("locales", []):
                if l.get("title"):
                    titre = l["title"].strip()
                    break
            sites.append({
                "id": w["document_id"],
                "nom": titre,
                "lat": lat, "lon": lon,
                "ele": w.get("elevation"),
                "regions": [a.get("document_id") for a in w.get("areas", [])],
            })
        offset += 100
        STATUT.write_text(json.dumps({"phase": "recolte", "recus": len(sites),
                                      "total": total, "offset": offset,
                                      "horodatage": time.strftime("%H:%M:%S")}), encoding="utf-8")
        print(f"  {len(sites)}/{total} sites…", flush=True)
        time.sleep(0.5)
        if total and offset >= total:
            break

    # garder ceux en France métropolitaine + DOM (bornes larges)
    France = [s for s in sites if s["nom"] and -65 < s["lon"] < 12 and -25 < s["lat"] < 52]
    SORTIE.write_text(json.dumps(France, ensure_ascii=False), encoding="utf-8")
    STATUT.write_text(json.dumps({"phase": "termine", "sites": len(France),
                                  "total_c2c": total}), encoding="utf-8")
    print(f"\nÉCRIT : {len(France)} sites nommés -> {SORTIE.name} (total C2C : {total})", flush=True)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
