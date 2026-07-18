"""RÈGLE QUALITÉ (v75, demande utilisateur) : viser pour CHAQUE point
1 lien + 1 photo + 1 description — les manques restent acceptés, mais on
ne livre plus de catégorie « nue ».

Ce script (France, data/points.geojson) :
 1. ajoute les OBSERVATOIRES astronomiques (OSM man_made=observatory nommés)
    à `ciel-etoile` — les VRAIS spots où regarder les étoiles, en plus des
    7 réserves certifiées ;
 2. LIEN : tout point sans lien reçoit « 🔎 Infos » (recherche web) ;
 3. DESCRIPTION : composée depuis les FAITS quand elle manque (altitude,
    espèce, circonférence, hauteur…) — jamais de blabla inventé ;
 4. PHOTO/WIKI : géo-recherche Wikipédia fr autour des points SANS photo
    (croix, phares, plongée, panoramas, villages abandonnés, observatoires) —
    l'article n'est retenu que s'il partage un mot (≥ 4 lettres) avec le nom
    du point OU s'il est à < 150 m (anti-homonyme).

Ids stables (mise à jour EN PLACE, clé theme|nom|lat3 comme v72/v74).
Usage : python tools/enrichir_qualite_v75.py [--ecrire]
"""

import json
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recolter_categories_v72 import RACINE, overpass, _centre, _http  # noqa: E402

UA_API = "https://fr.wikipedia.org/w/api.php"
GEOSEARCH_RAYONS = {"sommet-croix": 400, "phare": 500, "plongee": 300,
                    "panorama": 250, "village-abandonne": 800, "ciel-etoile": 600,
                    "arbre-remarquable": 200}


def _mots(texte):
    t = unicodedata.normalize("NFD", texte.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {m for m in re.split(r"[^a-z0-9]+", t) if len(m) >= 4}


def geosearch(lat, lon, rayon):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "geosearch", "ggscoord": f"{lat}|{lon}",
        "ggsradius": rayon, "ggslimit": 1,
        "prop": "coordinates|pageimages|extracts", "colimit": "max",
        "piprop": "thumbnail", "pithumbsize": 960,
        "exintro": 1, "explaintext": 1, "exsentences": 1,
    })
    d = _http(f"{UA_API}?{q}")
    pages = (d.get("query") or {}).get("pages", [])
    return pages[0] if pages else None


def observatoires():
    d = overpass('[out:json][timeout:120];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["man_made"="observatory"]["name"](area.p););out center tags;')
    pts, vus = [], set()
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        nom = (t.get("name") or "").strip()
        if lat is None or not nom or nom.lower() in vus:
            continue
        vus.add(nom.lower())
        links = []
        if (t.get("website") or "").startswith("http"):
            links.append({"label": "🌐 Site", "url": t["website"].replace(" ", "")[:300]})
        pts.append({"nom": nom, "lat": round(lat, 6), "lon": round(lon, 6),
                    "details": {"label": "Observatoire astronomique", "fiche": "À vérifier"},
                    "links": links, "photos": [], "description": ""})
    print(f"observatoires : {len(pts)}", flush=True)
    return pts


def description_factuelle(theme, p):
    """Compose une description depuis les FAITS présents (jamais inventée)."""
    d = p.get("details", {})
    if theme == "arbre-remarquable":
        morceaux = []
        if d.get("espece"):
            morceaux.append(f"{d['espece']} remarquable")
        if d.get("circonference"):
            morceaux.append(f"circonférence {d['circonference']}")
        return (" — ".join(morceaux) + ".") if morceaux else ""
    if theme == "panorama":
        base = f"Point de vue à {d['altitude']} d'altitude" if d.get("altitude") else ""
        if d.get("equipement"):
            base = (base + " — " if base else "") + "table d'orientation"
        return (base + ".") if base else ""
    if theme == "sommet-croix":
        return f"Sommet portant une croix sommitale ({d['altitude']})." if d.get("altitude") else \
               "Sommet portant une croix sommitale."
    if theme == "phare":
        return f"Phare de {d['hauteur']} de haut." if d.get("hauteur") else ""
    if theme == "ciel-etoile" and d.get("label") == "Observatoire astronomique":
        return "Observatoire astronomique — un vrai spot pour observer le ciel."
    return ""


def main(ecrire):
    chemin = RACINE / "data" / "points.geojson"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    feats = d["features"]

    # 1. observatoires -> ciel-etoile (append id stable, maj en place si relance)
    cles = {f'{f["properties"]["theme"]}|{f["properties"]["name"].lower()}|'
            f'{round(f["geometry"]["coordinates"][1], 3)}': f["properties"]["id"] for f in feats}
    existants = {f["properties"]["id"] for f in feats}
    suivant = 1 + max([int(i.split("-")[-1]) for i in existants if i.startswith("ciel-")] or [0])
    ajoutes = 0
    for p in sorted(observatoires(), key=lambda x: (x["nom"], x["lat"])):
        cle = f'ciel-etoile|{p["nom"].lower()}|{round(p["lat"], 3)}'
        if cle in cles:
            continue
        feats.append({"type": "Feature",
                      "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                      "properties": {"id": f"ciel-{suivant:04d}", "name": p["nom"],
                                     "theme": "ciel-etoile", "description": p["description"],
                                     "links": p["links"], "photos": p["photos"],
                                     "details": p["details"]}})
        suivant += 1
        ajoutes += 1
    print(f"ciel-etoile : +{ajoutes} observatoires", flush=True)

    # 2-4. passe qualité sur les catégories ciblées
    CIBLES = set(GEOSEARCH_RAYONS)
    n_liens = n_desc = n_photos = n_appels = 0
    for f in feats:
        p = f["properties"]
        theme = p["theme"]
        if theme not in CIBLES:
            continue
        lat = f["geometry"]["coordinates"][1]
        lon = f["geometry"]["coordinates"][0]
        # photo/wiki par géo-recherche (seulement si photo absente)
        if not p.get("photos"):
            page = geosearch(lat, lon, GEOSEARCH_RAYONS[theme])
            n_appels += 1
            if n_appels % 400 == 0:
                print(f"  … {n_appels} géo-recherches", flush=True)
            time.sleep(0.25)
            if page:
                coord = (page.get("coordinates") or [{}])[0]
                import math
                dist = 99999
                if coord.get("lat") is not None:
                    dx = (coord["lon"] - lon) * math.cos(math.radians(lat)) * 111320
                    dy = (coord["lat"] - lat) * 111320
                    dist = (dx * dx + dy * dy) ** 0.5
                sur = dist < 150 or (_mots(page["title"]) & _mots(p["name"]))
                if sur:
                    th = (page.get("thumbnail") or {}).get("source", "")
                    if th.startswith("https://upload.wikimedia.org"):
                        p["photos"] = [th]
                        n_photos += 1
                    url = "https://fr.wikipedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_"))
                    if not any(l["label"] == "🔗 Wikipédia" for l in p["links"]):
                        p["links"].insert(0, {"label": "🔗 Wikipédia", "url": url})
                    if not p.get("description"):
                        p["description"] = (page.get("extract") or "").strip()[:300]
                    p["details"]["fiche"] = "Référencé"
        # description factuelle en repli
        if not p.get("description"):
            texte = description_factuelle(theme, p)
            if texte:
                p["description"] = texte
                n_desc += 1
        # lien 🔎 systématique en dernier recours
        if not p.get("links"):
            p["links"] = [{"label": "🔎 Infos", "url": "https://www.google.com/search?q=" +
                           urllib.parse.quote(f'{p["name"]} France')}]
            n_liens += 1
    print(f"qualité : +{n_photos} photos/wiki, +{n_desc} descriptions factuelles, "
          f"+{n_liens} liens 🔎 ({n_appels} géo-recherches)", flush=True)

    if ecrire:
        chemin.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT data/points.geojson ({chemin.stat().st_size // 1024} Ko)")
    else:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main("--ecrire" in sys.argv)
