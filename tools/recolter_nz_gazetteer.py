# -*- coding: utf-8 -*-
"""
Récolte du NZ Gazetteer (noms de lieux OFFICIELS de Nouvelle-Zélande, LINZ /
NZ Geographic Board). UN SEUL GET sur le CSV complet — aucune clé, aucun
compte. Licence **CC-BY 4.0** (attribution « Land Information New Zealand »).

On en tire les LACS (~1 200) et les CASCADES (~300) officiels : nom + position.
PIÈGES : BOM UTF-8 en tête ; filtrer la latitude (-34 à -48,5) sinon on embarque
les dépendances antarctiques et les reliefs SOUS-MARINS des zones océaniques.

Lancer :  python tools/recolter_nz_gazetteer.py
Sortie   :  tools/nz-gazetteer.json
"""

import csv
import io
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "nz-gazetteer.json"
URL = "https://gazetteer.linz.govt.nz/gaz.csv"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

TYPES = {"Lake": "lacs", "Waterfall": "cascades", "Cave": "grottes"}
LAT_MIN, LAT_MAX = -48.5, -34.0  # NZ métropolitaine (Stewart Island incluse)


def telecharger():
    for ctx in (CTX, CTX_NV):
        for attente in (0, 15):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(URL, headers=UA), timeout=300, context=ctx) as r:
                    return r.read().decode("utf-8-sig")  # -sig : avale le BOM
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Gazetteer injoignable")


def recolter():
    texte = telecharger()
    lignes = csv.DictReader(io.StringIO(texte))
    donnees = {v: [] for v in TYPES.values()}
    total = 0
    for l in lignes:
        total += 1
        cle = TYPES.get((l.get("feat_type") or "").strip())
        if not cle:
            continue
        try:
            lat, lon = float(l["crd_latitude"]), float(l["crd_longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        if not (LAT_MIN <= lat <= LAT_MAX):
            continue  # Antarctique / océanique
        nom = (l.get("name") or "").strip()
        if not nom:
            continue
        donnees[cle].append({
            "nom": nom,
            "lat": round(lat, 6), "lon": round(lon, 6),
            "statut": (l.get("status") or "").strip(),  # Official / Unofficial…
        })
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    print(f"ÉCRIT ({total} lignes lues) : " +
          ", ".join(f"{k} {len(v)}" for k, v in donnees.items()) + f" -> {SORTIE.name}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
