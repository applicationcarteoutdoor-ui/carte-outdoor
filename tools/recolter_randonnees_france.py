# -*- coding: utf-8 -*-
"""Extension France des « Randonnées remarquables » — tous massifs.

Généralise le pilote Chartreuse (recolter_randonnees.py, dont il réutilise
les briques : validation Wikipédia par lots, nettoyage des extraits,
dédoublonnage nom + distance) à partir des listes éditoriales par massif
(randos_liste_*.py). Chaque massif est intégré SÉQUENTIELLEMENT dans
data/points.geojson : une interruption ne perd que le massif en cours.

Garanties d'ids :
  - ids stables `rando-NNNN` à partir de rando-0014 (le pilote possède
    0001-0013) ; une randonnée déjà en base (même nom à < 500 m) garde son id;
  - un id attribué n'est JAMAIS réutilisé, même si la randonnée est ensuite
    écartée (routage impossible) : registre tools/randos-registre.json.

Sorties annexes (caches gitignorés) :
  tools/randos-registre.json         id → nom (tous les ids jamais attribués)
  tools/randos-departs-france.json   id → spécification du départ OSM
                                     (consommée par recolter_traces_randos.py)

Usage :
  python tools/recolter_randonnees_france.py --massif Vercors [Belledonne …]
  python tools/recolter_randonnees_france.py --tous
  option --dry-run : bilan sans écrire.
"""

import argparse
import json
import sys
from pathlib import Path

from recolter_randonnees import (_distance_m, _index_par_nom,
                                 _nettoyer_extrait, normaliser_nom,
                                 pages_wikipedia, verifier_altitude)

from randos_liste_alpes_nord import MASSIFS as _M1
from randos_liste_alpes_sud import MASSIFS as _M2
from randos_liste_pyrenees import MASSIFS as _M3
from randos_liste_est_centre import MASSIFS as _M4
from randos_liste_corse import MASSIFS as _M5

MASSIFS = {}
for _m in (_M1, _M2, _M3, _M4, _M5):
    MASSIFS.update(_m)

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
CIBLE_POINTS = RACINE / "data" / "points.geojson"
REGISTRE = DOSSIER / "randos-registre.json"
DEPARTS_FR = DOSSIER / "randos-departs-france.json"

SEUIL_DOUBLON_M = 500

# Tous les noms d'entrées (tous massifs) : détection des redirections vers
# l'article d'une AUTRE randonnée (pas d'article dédié → écartée).
_NOMS_ENTREES = {normaliser_nom(e["nom"])
                 for conf in MASSIFS.values() for e in conf["randos"]}


def _charger(chemin, defaut):
    if chemin.exists():
        return json.loads(chemin.read_text(encoding="utf-8"))
    return defaut


def _sauver(chemin, donnees):
    chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=1),
                      encoding="utf-8")


def construire_candidats(massif, conf, stats):
    """Valide les entrées éditoriales du massif contre Wikipédia."""
    entrees = conf["randos"]
    pages = pages_wikipedia([t for e in entrees for t in e["titres"]])
    lat_min, lat_max, lon_min, lon_max = conf["bbox"]
    candidats = []
    for entree in entrees:
        cle_entree = normaliser_nom(entree["nom"])
        page = None
        for t in entree["titres"]:
            fiche = pages.get(t)
            if not fiche:
                continue
            cle_page = normaliser_nom(fiche["titre"])
            if cle_page != cle_entree and cle_page in _NOMS_ENTREES:
                continue        # redirection vers une autre entrée : pas dédié
            page = fiche
            break
        if not page:
            stats["sans_article"] += 1
            stats.setdefault("_sans_article", []).append(entree["nom"])
            continue
        if "lat" not in page:
            stats["sans_coordonnees"] += 1
            stats.setdefault("_sans_coords", []).append(entree["nom"])
            continue
        if not (lat_min <= page["lat"] <= lat_max
                and lon_min <= page["lon"] <= lon_max):
            stats["hors_bbox"] += 1
            stats.setdefault("_hors_bbox", []).append(
                f"{entree['nom']} ({page['lat']:.3f},{page['lon']:.3f})")
            continue
        if not verifier_altitude(entree, page):
            stats["altitude_non_confirmee"] += 1
            stats.setdefault("_alt_douteuse", []).append(entree["nom"])
        candidats.append({**entree, "massif": massif,
                          "lat": page["lat"], "lon": page["lon"],
                          "extract": _nettoyer_extrait(page.get("extract")),
                          "thumb": page.get("thumb", ""),
                          "wiki_url": page.get("url", "")})
    return candidats


def construire_feature(c, id_):
    details = {"massif": c["massif"]}
    if c.get("altitude"):
        details["altitude"] = f"{c['altitude']:,} m".replace(",", " ")
        details["altitude_n"] = c["altitude"]
    if c.get("altitude") and c.get("depart_alt"):
        dplus = c["altitude"] - c["depart_alt"]
        if dplus > 0:
            details["denivele"] = f"≈ {dplus} m"
            details["denivele_n"] = dplus
    if c.get("duree"):
        details["duree"] = c["duree"]
    if c.get("depart"):
        details["depart"] = c["depart"]
    if c.get("voie"):
        details["acces"] = c["voie"]
    desc = " ".join(x for x in (c["extract"], c.get("voie", "")) if x).strip()
    photo = c["thumb"] if (c["thumb"] or "").startswith(
        "https://upload.wikimedia.org") else ""
    details["fiche"] = ("Référencée" if photo and c["extract"]
                        else "À vérifier")
    return {"type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]},
            "properties": {"id": id_, "name": c["nom"], "theme": "randonnee",
                           "description": desc, "link": c["wiki_url"],
                           "photos": [photo] if photo else [],
                           "details": details}}


def integrer_massif(massif, conf, collection, registre, departs, dry_run):
    """Intègre un massif dans la collection (mutée en place). → stats."""
    stats = {k: 0 for k in ("sans_article", "sans_coordonnees", "hors_bbox",
                            "altitude_non_confirmee", "doublons_existants",
                            "ids_reutilises", "ajoutes")}
    stats["candidates"] = len(conf["randos"])
    candidats = construire_candidats(massif, conf, stats)

    autres = [f for f in collection["features"]
              if f["properties"].get("theme") != "randonnee"]
    precedents = [f for f in collection["features"]
                  if f["properties"].get("theme") == "randonnee"]
    index_autres = _index_par_nom(autres)
    index_prec = _index_par_nom(precedents)

    # Ids déjà pris : base vivante ∪ registre (ids écartés compris).
    ids_pris = ({f["properties"]["id"] for f in precedents}
                | set(registre))
    prochain = max((int(i.split("-")[1]) for i in ids_pris), default=0) + 1

    par_id = {f["properties"]["id"]: f for f in precedents}
    candidats.sort(key=lambda c: (normaliser_nom(c["nom"]), c["lon"]))
    ids_reutilises = set()
    for c in candidats:
        cle = normaliser_nom(c["nom"])
        prec = next((e for e in index_prec.get(cle, [])
                     if _distance_m(c, e) < SEUIL_DOUBLON_M
                     and e["feature"]["properties"]["id"] not in ids_reutilises),
                    None)
        if prec:                      # déjà en base : même id, fiche rafraîchie
            id_ = prec["feature"]["properties"]["id"]
            ids_reutilises.add(id_)
            par_id[id_] = construire_feature(c, id_)
            stats["ids_reutilises"] += 1
        else:
            autre = next((e for e in index_autres.get(cle, [])
                          if _distance_m(c, e) < SEUIL_DOUBLON_M), None)
            if autre:                 # homonyme co-localisé d'un point existant
                stats["doublons_existants"] += 1
                stats.setdefault("_doublons", []).append(
                    f"{c['nom']} ↔ {autre['feature']['properties']['id']}")
                continue
            id_ = f"rando-{prochain:04d}"
            prochain += 1
            par_id[id_] = construire_feature(c, id_)
            stats["ajoutes"] += 1
        registre[id_] = c["nom"]
        departs[id_] = c["osm"]

    randos = [par_id[i] for i in sorted(par_id)]
    collection["features"] = autres + randos
    if not dry_run:
        CIBLE_POINTS.write_text(
            json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        _sauver(REGISTRE, registre)
        _sauver(DEPARTS_FR, departs)
    return stats


def _afficher_bilan(massif, stats):
    print(f"\n=== {massif} : {stats['candidates']} candidates, "
          f"{stats['ajoutes']} ajoutées, {stats['ids_reutilises']} rafraîchies ===")
    for cle, libelle in (
            ("_sans_article", "sans article Wikipédia (écartées)"),
            ("_sans_coords", "sans coordonnées (écartées)"),
            ("_hors_bbox", "hors bbox massif (écartées)"),
            ("_alt_douteuse", "altitude éditoriale non confirmée (à vérifier)"),
            ("_doublons", "homonymes d'un point existant (écartées)")):
        if stats.get(cle):
            print(f"  {libelle} : {stats[cle]}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--massif", nargs="+", default=None)
    ap.add_argument("--tous", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cibles = list(MASSIFS) if args.tous else (args.massif or [])
    if not cibles:
        print("Massifs disponibles :", ", ".join(MASSIFS))
        return 1
    inconnus = [m for m in cibles if m not in MASSIFS]
    if inconnus:
        print("Massifs inconnus :", inconnus)
        return 1

    collection = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
    registre = _charger(REGISTRE, {})
    departs = _charger(DEPARTS_FR, {})
    total = {"ajoutes": 0, "ecartees": 0}
    for massif in cibles:                 # intégration massif par massif
        stats = integrer_massif(massif, MASSIFS[massif], collection,
                                registre, departs, args.dry_run)
        _afficher_bilan(massif, stats)
        total["ajoutes"] += stats["ajoutes"]
        total["ecartees"] += (stats["sans_article"] + stats["sans_coordonnees"]
                              + stats["hors_bbox"] + stats["doublons_existants"])
    nb_randos = sum(1 for f in collection["features"]
                    if f["properties"].get("theme") == "randonnee")
    print(f"\nTOTAL : +{total['ajoutes']} randonnées "
          f"({total['ecartees']} écartées) — catégorie : {nb_randos} points"
          + (" [dry-run : rien écrit]" if args.dry_run else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
