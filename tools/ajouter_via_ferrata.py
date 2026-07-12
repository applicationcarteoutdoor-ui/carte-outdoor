# -*- coding: utf-8 -*-
"""
Ajout des via ferrata MANQUANTES : sites OSM nommés (> 12 km de tout point
existant) CROISÉS avec une fiche viaferrata-fr.net non couverte. Le double
accord (OSM = nouveau lieu réel + fiche autorité = commune/cotation/lien) rend
l'ajout sûr. On EXCLUT les via-corda et les « secteurs/variantes » d'un site.

Ids neufs vf-127…, format identique à l'existant. `--ecrire` applique.
"""

import json
import re
import sys
from pathlib import Path

import revue_via_ferrata as rvf

CIBLE = Path(__file__).resolve().parent.parent / "data" / "points.geojson"
RAYON_MATCH = 12000

# Motifs à écarter : ni via ferrata au sens strict, ni fiche de référence.
EXCLURE = re.compile(r"via[- ]?corda|cordata|sentier|pont de singe|aventur", re.I)


def fiches_non_couvertes(points):
    fiches = rvf.parser_fiches()
    idx = {}
    for f in points:
        idx.setdefault(rvf.norm(f["properties"]["name"].replace("Via ferrata de ", "")), 1)
    manq = []
    for fi in fiches:
        couverte = any(fi["villeNorm"] and (fi["villeNorm"] in k or k in fi["villeNorm"]) for k in idx)
        if not couverte and not fi["fermeture"]:
            manq.append(fi)
    return manq


def main(ecrire=False):
    sites = rvf.clusterer_osm()
    d, points = rvf.charger_points()

    # sites OSM « nouveaux » (loin de tout point) et de vraies VF
    nouveaux = []
    for s in sites:
        if not s["nom"] or EXCLURE.search(s["nom"]):
            continue
        dmin = min(rvf.dist_m(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1],
                              s["lon"], s["lat"]) for f in points)
        if dmin > RAYON_MATCH:
            nouveaux.append(s)

    fiches = fiches_non_couvertes(points)

    # Rapprochement site OSM <-> fiche par le nom (commune ou intitulé)
    ajouts = []
    pris = set()
    for s in nouveaux:
        snorm = rvf.norm(s["nom"])
        fi = None
        for cand in fiches:
            if cand["id"] in pris:
                continue
            cle = rvf.norm(cand["nom"])
            ville = cand["villeNorm"]
            if (len(cle) >= 4 and cle in snorm) or (len(ville) >= 4 and ville in snorm):
                fi = cand
                break
        if not fi:
            continue
        pris.add(fi["id"])
        ajouts.append((s, fi))

    # Numérotation neuve
    nums = [int(m.group(1)) for f in points
            if (m := re.match(r"vf-(\d+)", f["properties"]["id"]))]
    prochain = max(nums) + 1

    features_neuves = []
    for k, (s, fi) in enumerate(sorted(ajouts, key=lambda x: x[1]["ville"])):
        pid = f"vf-{prochain + k:03d}"
        ville = fi["ville"] or fi["nom"]
        det = {"cotation": fi["difficulte"], "parcours": "1"}
        if s["zip"]:
            det["tyrolienne"] = "Oui"
            det["tyrolienne_type"] = "oui"
        else:
            det["tyrolienne_type"] = "non"
        features_neuves.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(s["lon"], 6), round(s["lat"], 6)]},
            "properties": {
                "id": pid,
                "name": f"Via ferrata de {ville}",
                "theme": "via-ferrata",
                "description": f"Département : {fi['dept']}\nParcours :\n* {fi['nom']} ({fi['difficulte']})",
                "link": fi["url"],
                "links": [],
                "photos": [],
                "details": det,
            },
        })
        print(f"  {pid}  {ville[:26]:26s} {fi['difficulte'][:10]:10s} "
              f"{round(s['lat'],4)},{round(s['lon'],4)}  <- OSM {s['nom'][:28]}")

    print(f"\n{len(features_neuves)} via ferrata manquantes à ajouter "
          f"(sites OSM nouveaux : {len(nouveaux)}, fiches non couvertes : {len(fiches)}).")

    if ecrire and features_neuves:
        d["features"].extend(features_neuves)
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT : +{len(features_neuves)} via ferrata dans {CIBLE.name}.")
    elif not ecrire:
        print("(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(ecrire="--ecrire" in sys.argv)
