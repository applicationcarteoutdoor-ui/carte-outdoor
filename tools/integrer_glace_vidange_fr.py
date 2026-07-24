# -*- coding: utf-8 -*-
"""
Intègre les cascades de glace et les aires de vidange dans la FRANCE
(data/points.geojson) — v81.

Les autres pays passent par construire_pays.py (qui rejoue les mêmes caches
via le module partagé points_glace_vidange) et la NZ par construire_nz.py :
un append manuel dans data/<iso>/ serait écrasé au prochain rebuild.

Ids STABLES `glace-####` / `vid-####`, posés par ordre (nom, lat) au premier
run ; une relance retrouve les ids par la clé « theme|nom|lat3 » et met à
jour EN PLACE (les statuts et le carnet des utilisateurs pointent dessus).

Lancer : python tools/integrer_glace_vidange_fr.py [--ecrire]
"""

import json
import sys
from pathlib import Path

from points_glace_vidange import point_cascade_glace, point_vidange

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = Path(__file__).resolve().parent


def integrer(ecrire):
    glace = json.loads((DOSSIER / "cascade-glace-c2c.json").read_text(encoding="utf-8")).get("fr", [])
    chemin_vid = DOSSIER / "vidange-fr.json"
    vidanges = json.loads(chemin_vid.read_text(encoding="utf-8")) if chemin_vid.exists() else []
    if not vidanges:
        print("⚠️  tools/vidange-fr.json absent — lancer recolter_vidange.py fr")

    chemin = RACINE / "data" / "points.geojson"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    existants = {f["properties"]["id"]: f for f in d["features"]}
    # ⚠️ Clé avec latitude ET longitude : les aires de vidange sont pour la
    # plupart ANONYMES (toutes nommées « Aire de vidange »). Une clé sur la
    # seule latitude au millième (~111 m) ferait entrer en collision deux
    # aires décalées en longitude — elles se voleraient leur id d'un run à
    # l'autre, et les statuts des utilisateurs suivraient.
    cles_connues = {}
    for f in d["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1]
        cles_connues[f'{p["theme"]}|{p["name"].lower()}|'
                     f'{round(lat, 4)}|{round(lon, 4)}'] = p["id"]

    lots = [
        ("cascade-glace", "glace", sorted(glace, key=lambda x: (x["nom"], x["lat"])),
         lambda pid, o: point_cascade_glace(pid, o, "France")),
        ("vidange", "vid", sorted(vidanges, key=lambda x: (x.get("nom") or "", x["lat"])),
         lambda pid, o: point_vidange(pid, o, "France")),
    ]
    for theme, abr, objets, fabrique in lots:
        suivant = 1 + max([int(i.split("-")[-1]) for i in existants
                           if i.startswith(abr + "-")] or [0])
        n_nouveaux = n_maj = 0
        for o in objets:
            nom = (o.get("nom") or ("Aire de vidange" if theme == "vidange" else "")).lower()
            cle = f'{theme}|{nom}|{round(o["lat"], 4)}|{round(o["lon"], 4)}'
            pid = cles_connues.get(cle)
            feat = fabrique(pid or f"{abr}-{suivant:04d}", o)
            if pid and pid in existants:
                existants[pid].update(feat)
                n_maj += 1
            else:
                d["features"].append(feat)
                suivant += 1
                n_nouveaux += 1
        print(f"{theme}: +{n_nouveaux} nouveaux, {n_maj} mis à jour", flush=True)

    if ecrire:
        chemin.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")),
                          encoding="utf-8")
        print(f"ÉCRIT data/points.geojson ({chemin.stat().st_size // 1024} Ko, "
              f"{len(d['features'])} points)")
    else:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    integrer("--ecrire" in sys.argv)
