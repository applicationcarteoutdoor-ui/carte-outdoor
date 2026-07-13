# -*- coding: utf-8 -*-
"""
Récolte du RES (Recensement des Équipements Sportifs, data-es) — sites de
**canyonisme** (type d'équipement « Canyon »). Source OFFICIELLE, **Licence
Ouverte Etalab 2.0** (réutilisation libre, y compris commerciale, avec
attribution). API Opendatasoft — même mécanique que recolter_escalade_res.py.

Fournit les FAITS : coordonnées, nom, commune/CP/dép/région, longueur de la
descente (equip_long) et dénivelé (equip_haut), accès libre. PAS de cotation /
corde / temps d'approche/retour / tracé (→ complétés par OSM là où ils existent,
et pour l'essentiel absents des données libres — cf. rapport de revue).

Lancer :  python tools/recolter_canyon_res.py
Sortie   :  tools/canyon-res.json
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "canyon-res.json"
API = "https://equipements.sports.gouv.fr/api/explore/v2.1/catalog/datasets/data-es/records"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
CHAMPS = ("equip_numero,equip_nom,inst_nom,new_name,equip_type_name,"
          "equip_coordonnees,equip_long,equip_haut,inst_cp,dep_code,dep_nom,"
          "reg_nom,equip_acc_libre,equip_saison,equip_url")


def _get(url):
    for attente in (0, 8, 25):
        if attente:
            time.sleep(attente)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.load(r)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("RES injoignable")


def recolter():
    sites, offset = [], 0
    where = quote('equip_type_name="Canyon"')
    while True:
        url = f"{API}?where={where}&select={quote(CHAMPS)}&limit=100&offset={offset}"
        d = _get(url)
        res = d.get("results", [])
        if not res:
            break
        for r in res:
            c = r.get("equip_coordonnees") or {}
            if not (c.get("lat") and c.get("lon")):
                continue
            nom = (r.get("equip_nom") or r.get("inst_nom") or "").strip()
            sites.append({
                "id": r.get("equip_numero"),
                "nom": nom,
                "commune": r.get("new_name") or "",
                "lat": round(c["lat"], 6), "lon": round(c["lon"], 6),
                "long": r.get("equip_long"),      # longueur de la descente (m)
                "haut": r.get("equip_haut"),      # dénivelé (m)
                "cp": r.get("inst_cp") or "",
                "dep": r.get("dep_code") or "",
                "dep_nom": r.get("dep_nom") or "",
                "reg": r.get("reg_nom") or "",
                "acces_libre": r.get("equip_acc_libre"),
                "saison": r.get("equip_saison"),
                "url": r.get("equip_url") or "",
            })
        offset += 100
        print(f"  Canyon… {offset}/{d.get('total_count', 0)}", flush=True)
        time.sleep(0.3)
        if offset >= d.get("total_count", 0):
            break
    SORTIE.write_text(json.dumps(sites, ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT : {len(sites)} canyons RES -> {SORTIE.name}", flush=True)
    return sites


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
