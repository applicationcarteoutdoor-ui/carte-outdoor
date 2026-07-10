# -*- coding: utf-8 -*-
"""
Plus Beaux Villages de France → catégorie EXISTANTE `cite-caractere`.

Récolte l'arbre de catégories Wikipédia « Localité adhérant à l'association
Les Plus Beaux Villages de France » (+ sous-catégories par département), puis
coordonnées / vignette / extrait par lots (colimit=max + suivi de continue).

Intégration dans data/points.geojson SANS nouvelle catégorie :
  - fusion dans le point cite-caractere existant (même nom normalisé < 3 km) :
    id conservé, photo/description/lien complétés seulement s'ils manquent,
    details.label = "Cité de caractère · Plus Beaux Villages de France" ;
  - sinon nouveau point id pbvf-NNNN (tri stable par nom → ids déterministes),
    details.label = "Plus Beaux Villages de France".
  - details.fiche = "Référencé" (photo ET description/lien) sinon "À vérifier".

Idempotent : caches tools/villages-*.json (repris tranche par tranche) et
relance sans doublon (les pbvf-* déjà présents sont mis à jour en place).
"""

import json
import math
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from enrichissements import DOSSIER, _api_wiki, _membres_categorie, normaliser

CACHE_ARTICLES = DOSSIER / "villages-articles.json"
CACHE_DETAILS = DOSSIER / "villages-details.json"
POINTS = DOSSIER.parent / "data" / "points.geojson"

CATEGORIE = ("Catégorie:Localité adhérant à l'association "
             "Les Plus Beaux Villages de France")
LABEL_PBVF = "Plus Beaux Villages de France"
LABEL_FUSION = "Cité de caractère · Plus Beaux Villages de France"

# France métropolitaine + Corse (hors bornes = DOM ou erreur, écarté et signalé)
LAT_MIN, LAT_MAX, LON_MIN, LON_MAX = 41.0, 51.5, -5.5, 10.0


# ---------------------------------------------------------------------------
# Récolte Wikipédia
# ---------------------------------------------------------------------------

def recolter_articles():
    """[{pageid, title}] : membres ns=0 de la catégorie racine et de ses
    sous-catégories PBVF (« … par département » → une sous-cat par dép.)."""
    if CACHE_ARTICLES.exists():
        return json.loads(CACHE_ARTICLES.read_text(encoding="utf-8"))
    print(f"Parcours de « {CATEGORIE} »…")
    articles, vues, file = {}, set(), [(CATEGORIE, 0)]
    while file:
        cat, prof = file.pop(0)
        if cat in vues:
            continue
        vues.add(cat)
        for m in _membres_categorie(cat):
            if m["ns"] == 0:
                articles[m["pageid"]] = m["title"]
            elif m["ns"] == 14 and prof < 2 and \
                    "plusbeauxvillagesdefrance" in normaliser(m["title"]):
                file.append((m["title"], prof + 1))
        time.sleep(0.2)
    liste = [{"pageid": pid, "title": t} for pid, t in sorted(articles.items())]
    CACHE_ARTICLES.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    print(f"  {len(vues)} catégories, {len(liste)} articles")
    return liste


def recolter_details(articles):
    """{pageid(str): {titre, lat, lon, url, thumb, extrait}} — lots de 20
    (limite exlimit des extraits), cache sauvegardé à chaque tranche."""
    cache = json.loads(CACHE_DETAILS.read_text(encoding="utf-8")) \
        if CACHE_DETAILS.exists() else {}
    a_faire = [a["pageid"] for a in articles if str(a["pageid"]) not in cache]
    if a_faire:
        print(f"Détails Wikipédia : {len(a_faire)} pages…")
    for i in range(0, len(a_faire), 20):
        lot = a_faire[i:i + 20]
        params = {"action": "query",
                  "pageids": "|".join(str(x) for x in lot),
                  "prop": "coordinates|pageimages|extracts|info",
                  "inprop": "url",
                  "colimit": "max",
                  "piprop": "thumbnail", "pithumbsize": "500", "pilimit": "max",
                  "exintro": 1, "explaintext": 1, "exsentences": 2,
                  "exlimit": "max"}
        pages, cont = {}, {}
        while True:  # suivi de continue : coordonnées/extraits arrivent par vagues
            d = _api_wiki({**params, **cont})
            for pid, page in d["query"].get("pages", {}).items():
                fusion = pages.setdefault(pid, {})
                for cle, valeur in page.items():
                    fusion.setdefault(cle, valeur)
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items() if k != "continue"}
            time.sleep(0.3)
        for pid, page in pages.items():
            coord = (page.get("coordinates") or [{}])[0]
            cache[pid] = {
                "titre": page.get("title", ""),
                "lat": coord.get("lat"),
                "lon": coord.get("lon"),
                "url": page.get("fullurl", ""),
                "thumb": (page.get("thumbnail") or {}).get("source", ""),
                "extrait": (page.get("extract") or "").strip(),
            }
        CACHE_DETAILS.write_text(json.dumps(cache, ensure_ascii=False),
                                 encoding="utf-8")
        print(f"  {min(i + 20, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.4)
    return cache


# ---------------------------------------------------------------------------
# Intégration dans points.geojson
# ---------------------------------------------------------------------------

def _distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _nom_village(titre):
    """« Sainte-Agnès (Alpes-Maritimes) » → « Sainte-Agnès »."""
    return titre.split(" (")[0].strip()


def _fiche(props):
    """"Référencé" si photo ET (description ou lien), sinon "À vérifier"."""
    complet = props.get("photos") and (props.get("description") or props.get("link"))
    return "Référencé" if complet else "À vérifier"


def integrer(details):
    donnees = json.loads(POINTS.read_text(encoding="utf-8"))
    feats = donnees["features"]
    avant = len(feats)

    # Index des cite-caractere existants (cc-* ET pbvf-* pour l'idempotence)
    index = {}  # nom normalisé → [feature]
    for f in feats:
        if f["properties"]["theme"] == "cite-caractere":
            index.setdefault(normaliser(f["properties"]["name"]), []).append(f)

    villages = sorted(details.values(), key=lambda v: normaliser(v["titre"]))
    cpt = {"fusionnes": 0, "ajoutes": 0, "maj_pbvf": 0,
           "sans_coord": [], "hors_bornes": [], "doublons_lot": []}
    nouveaux = []

    for v in villages:
        nom = _nom_village(v["titre"])
        if v["lat"] is None or v["lon"] is None:
            cpt["sans_coord"].append(nom)
            continue
        if not (LAT_MIN <= v["lat"] <= LAT_MAX and LON_MIN <= v["lon"] <= LON_MAX):
            cpt["hors_bornes"].append(f"{nom} ({v['lat']:.2f}, {v['lon']:.2f})")
            continue

        cible = None
        for f in index.get(normaliser(nom), []):
            flon, flat = f["geometry"]["coordinates"]
            if _distance_km(v["lat"], v["lon"], flat, flon) < 3.0:
                cible = f
                break

        if cible is not None:                       # fusion / mise à jour
            p = cible["properties"]
            det = p.setdefault("details", {})
            if p["id"] is None:                     # doublon interne au lot
                cpt["doublons_lot"].append(nom)
                continue
            deja_pbvf = p["id"].startswith("pbvf-")
            if not p.get("photos") and v["thumb"]:
                p["photos"] = [v["thumb"]]
            if not p.get("link") and v["url"]:
                p["link"] = v["url"]
            if not p.get("description") and v["extrait"]:
                p["description"] = v["extrait"]
            det["label"] = LABEL_PBVF if deja_pbvf else LABEL_FUSION
            det["fiche"] = _fiche(p)
            cpt["maj_pbvf" if deja_pbvf else "fusionnes"] += 1
        else:                                       # nouveau point
            props = {
                "id": None,  # numéroté après tri (déterministe)
                "name": nom,
                "theme": "cite-caractere",
                "description": v["extrait"] or
                    f"Village classé parmi les Plus Beaux Villages de France.",
                "link": v["url"],
                "details": {"label": LABEL_PBVF},
            }
            if v["thumb"]:
                props["photos"] = [v["thumb"]]
            props["details"]["fiche"] = _fiche(props)
            feat = {"type": "Feature",
                    "geometry": {"type": "Point",
                                 "coordinates": [round(v["lon"], 5), round(v["lat"], 5)]},
                    "properties": props}
            nouveaux.append(feat)
            index.setdefault(normaliser(nom), []).append(feat)

    # Ids déterministes : tri stable par nom, numérotation après le max existant
    deja = [int(f["properties"]["id"][5:]) for f in feats
            if f["properties"]["id"].startswith("pbvf-")]
    prochain = max(deja, default=0) + 1
    nouveaux.sort(key=lambda f: normaliser(f["properties"]["name"]))
    for f in nouveaux:
        f["properties"]["id"] = f"pbvf-{prochain:04d}"
        prochain += 1
        cpt["ajoutes"] += 1
    feats.extend(nouveaux)

    POINTS.write_text(json.dumps(donnees, ensure_ascii=False,
                                 separators=(",", ":")), encoding="utf-8")
    print(f"\npoints.geojson : {avant} -> {len(feats)} features")
    print(f"  fusionnés avec une cité existante : {cpt['fusionnes']}")
    print(f"  nouveaux (pbvf-*)                : {cpt['ajoutes']}")
    print(f"  pbvf-* mis à jour (relance)      : {cpt['maj_pbvf']}")
    if cpt["sans_coord"]:
        print(f"  sans coordonnées (écartés)       : {cpt['sans_coord']}")
    if cpt["hors_bornes"]:
        print(f"  hors métropole (écartés)         : {cpt['hors_bornes']}")
    if cpt["doublons_lot"]:
        print(f"  doublons dans le lot (écartés)   : {cpt['doublons_lot']}")
    return cpt


if __name__ == "__main__":
    articles = recolter_articles()
    details = recolter_details(articles)
    geo = sum(1 for v in details.values() if v["lat"] is not None)
    photo = sum(1 for v in details.values() if v["thumb"])
    extrait = sum(1 for v in details.values() if v["extrait"])
    print(f"Récolte : {len(details)} articles, {geo} géolocalisés, "
          f"{photo} avec photo, {extrait} avec extrait")
    integrer(details)
