# -*- coding: utf-8 -*-
"""
Récolte OpenStreetMap (ODbL) pour la Nouvelle-Zélande : cascades, lacs NOMMÉS
et sites d'escalade. Complète le socle DOC (huttes/campings/Great Walks).

- Cascades : waterway=waterfall (nœuds), name conservé s'il existe.
- Lacs : natural=water + water=lake|reservoir AVEC nom (les étangs anonymes
  sont écartés — même sélection qualitative que la France). Récupérés par
  `out center` (le centre du polygone suffit pour une épingle).
- Escalade : sport=climbing (nœuds + ways/relations par centre),
  climbing:* facts s'ils existent.

Lancer :  python tools/recolter_nz_osm.py
Sortie   :  tools/nz-osm.json
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
SORTIE = DOSSIER / "nz-osm.json"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE
AREA = 'area["ISO3166-1"="NZ"][admin_level=2]->.nz;'


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX, CTX_NV):
            for attente in (0, 20, 60):
                if attente:
                    time.sleep(attente)
                try:
                    req = urllib.request.Request(ep, data=data, headers=UA)
                    with urllib.request.urlopen(req, timeout=300, context=ctx) as r:
                        return json.load(r)
                except urllib.error.HTTPError as e:
                    print(f"    ({ep.split('/')[2]} HTTP {e.code})", flush=True)
                    if e.code in (429, 504):
                        continue
                    break
                except (urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
                    print(f"    ({ep.split('/')[2]} : {e})", flush=True)
    raise RuntimeError("Overpass injoignable")


def extraire(el):
    """Coordonnées d'un élément Overpass (nœud direct ou centre)."""
    if el.get("type") == "node":
        return el.get("lat"), el.get("lon")
    c = el.get("center") or {}
    return c.get("lat"), c.get("lon")


def recolter():
    donnees = {}

    requetes = {
        # nom facultatif pour les cascades (beaucoup sont anonymes mais localisées)
        "cascades": 'nwr["waterway"="waterfall"](area.nz);',
        # lacs : NOMMÉS uniquement (sélection qualitative)
        "lacs": 'nwr["natural"="water"]["water"~"^(lake|reservoir)$"]["name"](area.nz);',
        "escalade": 'nwr["sport"="climbing"](area.nz);',
    }
    for cle, sel in requetes.items():
        corps = f"[out:json][timeout:300];{AREA}({sel});out tags center;"
        d = _post(corps)
        objs = []
        for el in d.get("elements", []):
            lat, lon = extraire(el)
            t = el.get("tags", {})
            if lat is None:
                continue
            objs.append({
                "osm": f"{el['type'][0]}{el['id']}",
                "nom": (t.get("name") or t.get("name:en") or "").strip(),
                "lat": round(lat, 6), "lon": round(lon, 6),
                "tags": {k: v for k, v in t.items()
                         if k in ("ele", "height", "climbing:rock", "climbing:routes",
                                  "climbing:length", "website", "description") or k.startswith("climbing:grade")},
            })
        donnees[cle] = objs
        print(f"  {cle}: {len(objs)}", flush=True)
        time.sleep(5)

    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT -> {SORTIE.name} : " +
          ", ".join(f"{k} {len(v)}" for k, v in donnees.items()), flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
