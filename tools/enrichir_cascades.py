# -*- coding: utf-8 -*-
"""
Enrichissement de la catégorie « cascade » à partir de sources RÉUTILISABLES,
en place dans data/points.geojson (ids stables, jamais renumérotés).

Constat de l'audit : les 1 133 cascades ont des coordonnées OSM précises (pas
de centroïde de commune — rien à recaler), mais 91 % sont « À vérifier »,
89 % n'ont qu'une description générique OSM, 8 % une photo, 9 % un lien.

Sources (FAITS + courts extraits + photos libres seulement) :
  - Wikipédia FR par le NOM de chaque cascade nommée : article, photo
    (upload.wikimedia.org uniquement — CSP), extrait de 2 phrases, lien.
    Garde-fou anti-homonyme : l'article doit être géolocalisé à < 2 km.
  - Arbre de catégories Wikipédia « Chute d'eau en France » (par département /
    région / parc national / DOM) : découvre les cascades NOTABLES absentes de
    notre set (article obligatoire → fiche riche), et enrichit les existantes
    par proximité (< 500 m = même chute).

Ne remplit QUE le vide ; remplace les descriptions génériques OSM par l'extrait
Wikipédia quand il existe. Recalcule le champ « fiche » (Référencée / À vérifier).

Lancer :  python tools/enrichir_cascades.py            (simulation)
          python tools/enrichir_cascades.py --ecrire   (écrit points.geojson)
"""

import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import enrichissements as enr
import recolter_cascades as rc

DOSSIER = Path(__file__).resolve().parent
CIBLE = DOSSIER.parent / "data" / "points.geojson"
CACHE_CAT = "cascades-wiki-cat.json"          # arbre catégorie (via enr.)
STATUT = DOSSIER / "enrichir-cascades-status.json"

R_MEME = 500        # m : article catégorie ↔ point existant = même cascade
R_NOM = 2000        # m : garde-fou anti-homonyme pour un match par le nom
R_DEDUP = 500       # m : entre nouvelles cascades ajoutées

# Bornes de validité pour un AJOUT (métropole + DOM à cascades notables).
ZONES_FR = [
    (41.0, 51.5, -5.5, 10.0),      # métropole + Corse
    (-21.5, -20.8, 55.2, 55.9),    # Réunion
    (15.8, 16.6, -61.9, -61.0),    # Guadeloupe
    (14.3, 14.9, -61.3, -60.7),    # Martinique
    (2.0, 6.0, -54.7, -51.5),      # Guyane
    (-13.1, -12.6, 45.0, 45.4),    # Mayotte
]

RE_GENERIQUE = re.compile(r"^Cascade \(", re.I)   # nom « Cascade (Commune) »
RE_TITRE_REJET = re.compile(r"^(Liste|Catégorie|Parc|Modèle)\b", re.I)
MARQUEURS_GENERIQUE = ("référencée par les contributeurs OpenStreetMap",
                       "sans nom précis dans OpenStreetMap")


def en_france(lat, lon):
    return any(la0 <= lat <= la1 and lo0 <= lon <= lo1
               for la0, la1, lo0, lo1 in ZONES_FR)


def desc_generique(desc):
    return any(m in (desc or "") for m in MARQUEURS_GENERIQUE)


def nom_depuis_titre(titre):
    """Titre d'article → nom de point lisible (sans parenthèse d'homonymie
    purement géographique laissée telle quelle : « Cascade du Ray-Pic »)."""
    return re.sub(r"\s+", " ", titre.replace("_", " ")).strip()


def main(ecrire=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    casc = [f for f in d["features"] if f["properties"].get("theme") == "cascade"]
    autres = [f for f in d["features"] if f["properties"].get("theme") != "cascade"]
    print(f"points.geojson : {len(casc)} cascades, {len(autres)} autres points")

    # --- 1. Arbre catégorie Wikipédia « Chute d'eau en France » ---
    cat = enr.recolter_categorie_wikipedia(CACHE_CAT, "Catégorie:Chute d'eau en France", "chute")
    cat = [a for a in cat if a.get("lat") is not None
           and not RE_TITRE_REJET.match(a.get("titre", ""))]
    print(f"catégorie Wikipédia : {len(cat)} articles géolocalisés")

    # --- 2. Résolution Wikipédia (extraits) : noms des cascades + titres catégorie ---
    titres_noms = [f["properties"]["name"] for f in casc
                   if not RE_GENERIQUE.match(f["properties"]["name"])]
    titres_cat = [a["titre"] for a in cat]
    pages = rc._pages_cascades(list(dict.fromkeys(titres_noms + titres_cat)))

    def page_valide(titre):
        p = pages.get("t:" + titre)
        return p if (p and p.get("url")) else None

    # index catégorie par cellule 0.1° (proximité rapide)
    grille_cat = defaultdict(list)
    for a in cat:
        grille_cat[(round(a["lat"], 1), round(a["lon"], 1))].append(a)

    def cat_proche(lat, lon, r=R_MEME):
        best = None
        for dla in (-0.1, 0, 0.1):
            for dlo in (-0.1, 0, 0.1):
                for a in grille_cat.get((round(lat + dla, 1), round(lon + dlo, 1)), []):
                    dd = enr._haversine((lon, lat), (a["lon"], a["lat"]))
                    if dd <= r and (best is None or dd < best[0]):
                        best = (dd, a)
        return best[1] if best else None

    st = defaultdict(int)
    titres_utilises = set()   # articles catégorie déjà rattachés à un point

    # --- 3. Enrichir les cascades existantes (ne remplir que le vide) ---
    for f in casc:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2]
        det = p.setdefault("details", {})
        page, titre_src = None, None

        # a) l'article portant EXACTEMENT le nom de la cascade, à < 2 km
        if not RE_GENERIQUE.match(p["name"]):
            pg = page_valide(p["name"])
            if pg and pg.get("lat") is not None and \
                    enr._haversine((lon, lat), (pg["lon"], pg["lat"])) <= R_NOM:
                page, titre_src = pg, p["name"]

        # b) sinon, un article de la catégorie « Chute d'eau » à < 500 m
        if page is None:
            a = cat_proche(lat, lon)
            if a:
                page = page_valide(a["titre"]) or a
                titre_src = a["titre"]

        if not page:
            continue
        if titre_src:
            titres_utilises.add(titre_src)

        change = False
        if not p.get("link") and page.get("url"):
            p["link"] = page["url"]; change = True
        thumb = page.get("thumb") or ""
        if not p.get("photos") and thumb.startswith("https://upload.wikimedia.org"):
            p["photos"] = [thumb]; change = True
        extrait = (page.get("extract") or "").strip()
        if extrait and (not (p.get("description") or "").strip() or desc_generique(p.get("description"))):
            p["description"] = extrait; change = True
        if change:
            st["enrichies"] += 1

        # fiche : Référencée = photo ET (lien OU extrait OU hauteur)
        complet = bool(p.get("photos")) and bool(
            p.get("link") or (not desc_generique(p.get("description"))
                              and (p.get("description") or "").strip()) or "hauteur" in det)
        det["fiche"] = "Référencée" if complet else "À vérifier"

    # --- 4. Ajouter les cascades notables manquantes (articles catégorie) ---
    tous = [(g["geometry"]["coordinates"][0], g["geometry"]["coordinates"][1])
            for g in (casc + autres) if (g.get("geometry") or {}).get("type") == "Point"]
    grille_ex = defaultdict(list)
    for lo, la in tous:
        grille_ex[(round(la, 1), round(lo, 1))].append((lo, la))

    def loin(lat, lon, r):
        for dla in (-0.1, 0, 0.1):
            for dlo in (-0.1, 0, 0.1):
                for lo, la in grille_ex.get((round(lat + dla, 1), round(lon + dlo, 1)), []):
                    if enr._haversine((lon, lat), (lo, la)) <= r:
                        return False
        return True

    nums = [int(m.group(1)) for f in casc
            if (m := re.match(r"casc-(\d+)", f["properties"]["id"]))]
    prochain = (max(nums) + 1) if nums else 1
    ajouts, ajoutes_coords = [], []
    for a in sorted(cat, key=lambda x: x["titre"]):
        if a["titre"] in titres_utilises:
            continue
        lat, lon = a["lat"], a["lon"]
        if not en_france(lat, lon) or not loin(lat, lon, R_MEME):
            continue
        if any(enr._haversine((lon, lat), (lo, la)) <= R_DEDUP for lo, la in ajoutes_coords):
            continue
        page = page_valide(a["titre"]) or a
        nom = nom_depuis_titre(a["titre"])
        thumb = page.get("thumb") or a.get("thumb") or ""
        extrait = (page.get("extract") or "").strip()
        det = {}
        photos = [thumb] if thumb.startswith("https://upload.wikimedia.org") else []
        complet = bool(photos) and bool(page.get("url") or extrait)
        det["fiche"] = "Référencée" if complet else "À vérifier"
        ajouts.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"casc-{prochain + len(ajouts):04d}",
                "name": nom, "theme": "cascade",
                "description": extrait or "Chute d'eau documentée sur Wikipédia.",
                "link": page.get("url") or a.get("url") or "",
                "photos": photos, "details": det,
            },
        })
        ajoutes_coords.append((lon, lat))

    print(f"\nEnrichies : {st['enrichies']} | cascades notables ajoutées : {len(ajouts)}")
    print(f"Cascade : {len(casc)} -> {len(casc) + len(ajouts)}")

    # couverture après coup
    apres = casc + ajouts
    tot = len(apres) or 1
    q = lambda test: sum(1 for f in apres if test(f["properties"])) * 100 // tot
    print(f"  couverture : photo {q(lambda p: p.get('photos'))} %, "
          f"lien {q(lambda p: p.get('link'))} %, "
          f"référencée {q(lambda p: (p.get('details') or {}).get('fiche') == 'Référencée')} %, "
          f"description rédigée {q(lambda p: (p.get('description') and not desc_generique(p['description'])))} %")

    STATUT.write_text(json.dumps({"enrichies": st["enrichies"], "ajouts": len(ajouts),
                                  "total": len(apres)}, ensure_ascii=False), encoding="utf-8")

    if ecrire:
        # Cascades existantes mutées en place (mêmes objets que d["features"]) ;
        # seules les nouvelles sont ajoutées → ordre préservé, diff minimal.
        d["features"].extend(ajouts)
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT. points.geojson : {len(d['features'])} features, {CIBLE.stat().st_size // 1024} Ko")
    else:
        print("(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    main(ecrire="--ecrire" in sys.argv)
