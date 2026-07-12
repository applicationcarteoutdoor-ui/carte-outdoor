# -*- coding: utf-8 -*-
"""
Recalage GPS + relevé des manquantes pour la catégorie via-ferrata.

S'appuie sur le diagnostic de revue_via_ferrata.py (parsing viaferrata-fr.net +
clustering OSM). RÈGLE CONSERVATRICE — ne recale un point QUE si le rapprochement
est SÛR :
  - point déjà à < 500 m d'un site OSM  -> considéré bien placé, on ne touche pas ;
  - sinon, on recale UNIQUEMENT s'il existe EXACTEMENT UN site OSM dans un rayon
    de 12 km ET que ce site n'est revendiqué que par ce seul point (les via ferrata
    sont espacées d'~50 km en moyenne : un site unique à portée = quasi certain) ;
  - tout le reste (aucun site OSM à portée, ou plusieurs candidats/points en
    concurrence) -> LAISSÉ EN PLACE et listé « à vérifier manuellement ».

Ids jamais renumérotés. `--ecrire` applique ; sans, simulation (n'écrit rien).
"""

import json
import re
import sys
from collections import Counter
from pathlib import Path

import revue_via_ferrata as rvf


def commune_norm(nom):
    """Nom de commune normalisé, extrait de « Via ferrata de <Commune> »."""
    c = re.sub(r"^via ?ferrata\s+(de\s+|d'|du\s+|des\s+|la\s+|le\s+|l')?", "", nom, flags=re.I)
    return rvf.norm(c)

CIBLE = Path(__file__).resolve().parent.parent / "data" / "points.geojson"
RAYON_OK = 500       # déjà bien placé : on ne touche pas
RAYON_MATCH = 12000  # recalage si UN SEUL site OSM dans ce rayon


def appliquer_recalage(f, s, ecrire):
    if ecrire:
        f["geometry"]["coordinates"][0] = round(s["lon"], 6)
        f["geometry"]["coordinates"][1] = round(s["lat"], 6)


def main(ecrire=False):
    sites = rvf.clusterer_osm()
    d, points = rvf.charger_points()

    infos = []
    for f in points:
        lon, lat = f["geometry"]["coordinates"][:2]
        proches = sorted(((rvf.dist_m(lon, lat, s["lon"], s["lat"]), s) for s in sites),
                         key=lambda x: x[0])
        dmin, smin = proches[0]
        cand = [(dd, s) for dd, s in proches if dd <= RAYON_MATCH]
        infos.append({"f": f, "dmin": dmin, "smin": smin, "cand": cand})

    # Un site OSM revendiqué comme UNIQUE candidat par plusieurs points = ambigu
    revend = Counter()
    for i in infos:
        if i["dmin"] > RAYON_OK and len(i["cand"]) == 1:
            revend[i["cand"][0][1]["nom"], round(i["cand"][0][1]["lon"], 4)] += 1

    recales, deja_ok, a_verifier = [], [], []
    for i in infos:
        f = i["f"]
        pid = f["properties"]["id"]
        nom = f["properties"]["name"]
        if i["dmin"] <= RAYON_OK:
            deja_ok.append((pid, nom, round(i["dmin"])))
            continue
        # Règle 1 : un seul site OSM à portée, non revendiqué par un autre point.
        if len(i["cand"]) == 1:
            dd, s = i["cand"][0]
            cle = (s["nom"], round(s["lon"], 4))
            if revend[cle] == 1:
                appliquer_recalage(f, s, ecrire)
                recales.append((pid, nom, round(dd), s["nom"] or "(sans nom OSM)"))
                continue
        # Règle 2 : plusieurs candidats, mais UN SEUL dont le nom OSM contient
        # notre commune (« Via Ferrata de Tende » pour « Via ferrata de Tende »)
        # → désambiguïsation quasi certaine par le nom.
        cnorm = commune_norm(nom)
        if len(cnorm) >= 4:
            par_nom = [(dd, s) for dd, s in i["cand"] if cnorm in rvf.norm(s["nom"])]
            if len(par_nom) == 1:
                dd, s = par_nom[0]
                appliquer_recalage(f, s, ecrire)
                recales.append((pid, nom, round(dd), (s["nom"] or "") + " [nom]"))
                continue
        raison = "aucun site OSM à <12 km" if not i["cand"] else f"{len(i['cand'])} candidats/concurrence"
        a_verifier.append((pid, nom, round(i["dmin"]), i["smin"]["nom"] or "-", raison))

    # Sites OSM nommés sans aucun de nos points à proximité = VF potentiellement manquantes
    manquantes = []
    for s in sites:
        if not s["nom"]:
            continue
        dmin_pt = min(rvf.dist_m(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1],
                                 s["lon"], s["lat"]) for f in points)
        if dmin_pt > RAYON_MATCH:
            manquantes.append((s["nom"], round(s["lat"], 5), round(s["lon"], 5), s.get("scale_max")))

    print(f"Recalés : {len(recales)} | déjà bien placés : {len(deja_ok)} | "
          f"à vérifier manuellement : {len(a_verifier)}")
    print(f"VF potentiellement manquantes (site OSM nommé sans point à <12 km) : {len(manquantes)}\n")
    print("--- RECALÉS (déplacement) ---")
    for pid, nom, dd, osm in sorted(recales, key=lambda x: -x[2]):
        print(f"  {pid} {dd:6d}m  {nom[:40]:40s} -> {osm[:34]}")
    print("\n--- À VÉRIFIER MANUELLEMENT ---")
    for pid, nom, dd, osm, r in sorted(a_verifier, key=lambda x: -x[2]):
        print(f"  {pid} {dd:6d}m  {nom[:38]:38s} [{r}] proche: {osm[:24]}")
    print("\n--- MANQUANTES (candidates) ---")
    for nom, la, lo, sc in sorted(manquantes):
        print(f"  {la:>8},{lo:>8}  K{sc if sc else '?'}  {nom[:48]}")

    if ecrire:
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"\nÉCRIT : {len(recales)} coordonnées recalées dans {CIBLE.name} (ids conservés).")
    else:
        print("\n(SIMULATION — rien écrit. Relancer avec --ecrire pour appliquer.)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(ecrire="--ecrire" in sys.argv)
