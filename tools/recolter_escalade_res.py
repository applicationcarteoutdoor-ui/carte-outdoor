# -*- coding: utf-8 -*-
"""
Récolte du RES (Recensement des Équipements Sportifs, data-es) — sites
d'escalade en falaise + de blocs. Source OFFICIELLE, **Licence Ouverte Etalab
2.0** (réutilisation libre avec attribution). API Opendatasoft.

Fournit : coordonnées PRÉCISES par secteur, hauteur, commune/CP/dép,
gestionnaire, accès libre, saisonnalité. PAS de cotation/roche/voies (→ complété
par Camp to Camp). Attribution à afficher dans l'app.

Lancer :  python tools/recolter_escalade_res.py
Sortie   :  tools/escalade-res.json
"""

import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import quote

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "escalade-res.json"
API = "https://equipements.sports.gouv.fr/api/explore/v2.1/catalog/datasets/data-es/records"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
TYPES = ["Site d'escalade en falaise", "Site de blocs d'escalade"]
CHAMPS = ("equip_numero,new_name,equip_nom,equip_type_name,equip_coordonnees,"
          "equip_haut,inst_cp,dep_code,dep_nom,reg_nom,equip_gest_type,"
          "equip_prop_type,equip_acc_libre,equip_saison")


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
    sites = []
    for t in TYPES:
        where = quote(f'equip_type_name="{t}"')
        offset = 0
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
                sites.append({
                    "id": r.get("equip_numero"),
                    "commune": r.get("new_name") or "",
                    "secteur": r.get("equip_nom") or "",
                    "type": "bloc" if "blocs" in (r.get("equip_type_name") or "") else "falaise",
                    "lat": round(c["lat"], 6), "lon": round(c["lon"], 6),
                    "haut": r.get("equip_haut"),
                    "cp": r.get("inst_cp") or "",
                    "dep": r.get("dep_code") or "",
                    "gest": r.get("equip_gest_type") or "",
                    "acces_libre": r.get("equip_acc_libre"),
                    "saison": r.get("equip_saison"),
                })
            offset += 100
            print(f"  {t[:22]}… {offset}", flush=True)
            time.sleep(0.3)
            if offset >= d.get("total_count", 0):
                break
    SORTIE.write_text(json.dumps(sites, ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT : {len(sites)} sites RES -> {SORTIE.name}", flush=True)
    return sites


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
