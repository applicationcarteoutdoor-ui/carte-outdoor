# -*- coding: utf-8 -*-
"""
Récolte des entrées de cavités de France depuis Grottocenter (Wikicaves),
API publique sans clé — FAITS sous ODbL (attribution + partage à l'identique).

Endpoint carte : GET /api/v1/geoloc/entrances?sw_lat&sw_lng&ne_lat&ne_lng
renvoie en un appel toutes les entrées d'une bbox avec : id, name, city,
region, caveId, caveName, depth (profondeur du réseau, m), length
(développement, m), longitude, latitude, quality, dataQuality.

On ne récolte que des FAITS réutilisables (coordonnées, nom, profondeur,
développement, commune) + l'id Grottocenter (lien retour). Les descriptions,
commentaires, topos et photos de Grottocenter sont protégés (CC-BY-SA / CC) et
ne sont PAS récupérés. Les entrées volontairement masquées par leurs
contributeurs (patrimoine, chauves-souris) n'ont pas de coordonnées publiques
et sont donc naturellement absentes de la réponse — on respecte ce masquage.

Cache : tools/grottes-gc.json (repris tel quel s'il existe).

Lancer :  python tools/recolter_grottes_grottocenter.py
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CACHE = DOSSIER / "grottes-gc.json"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
API = "https://api.grottocenter.org/api/v1/geoloc/entrances"

# Métropole + Corse, et boîtes outre-mer (comme escalade/cascade)
BBOX = [
    (41.0, -5.5, 51.5, 9.6),        # métropole + Corse
    (-21.5, 55.2, -20.8, 55.9),     # Réunion
    (15.8, -61.9, 16.6, -61.0),     # Guadeloupe
    (14.3, -61.3, 14.9, -60.7),     # Martinique
]


def fetch(sw_lat, sw_lng, ne_lat, ne_lng):
    url = (f"{API}?sw_lat={sw_lat}&sw_lng={sw_lng}&ne_lat={ne_lat}&ne_lng={ne_lng}")
    for attente in (0, 20, 60):
        if attente:
            print(f"    pause {attente} s…"); time.sleep(attente)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=180) as r:
                return json.load(r)
        except Exception as exc:
            print(f"    ! {exc}")
    return []


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if CACHE.exists():
        d = json.loads(CACHE.read_text(encoding="utf-8"))
        print(f"cache existant : {len(d)} entrées")
        return
    par_id = {}
    for sw_lat, sw_lng, ne_lat, ne_lng in BBOX:
        print(f"bbox {sw_lat},{sw_lng} → {ne_lat},{ne_lng}…")
        d = fetch(sw_lat, sw_lng, ne_lat, ne_lng)
        for e in d:
            if e.get("latitude") and e.get("longitude"):
                par_id[e["id"]] = e
        print(f"  cumul : {len(par_id)}")
        time.sleep(1)
    liste = list(par_id.values())
    CACHE.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    print(f"ÉCRIT {len(liste)} entrées → {CACHE.name}")


if __name__ == "__main__":
    main()
