# -*- coding: utf-8 -*-
"""
Construit data/<iso>/points.geojson pour la Suisse, l'Italie et l'Espagne à
partir de tools/pays-<iso>-osm.json (OSM, ODbL) et tools/pays-villages.json
(villages labellisés via Wikipédia/Wikidata).

Ids STABLES `<iso>-<type>-####` posés par ordre alphabétique à la première
création (statuts/carnet pointent dessus — jamais renumérotés).

Lancer :  python tools/construire_pays.py            (aperçu)
          python tools/construire_pays.py --ecrire   (écrit)
"""

import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
PAYS = {
    "ch": {"nom": "Suisse", "recherche": "Switzerland"},
    "it": {"nom": "Italie", "recherche": "Italy"},
    "es": {"nom": "Espagne", "recherche": "Spain"},
}
# catégorie OSM -> (theme, abréviation d'id)
THEMES = {
    "refuge": ("refuge", "ref"),
    "camping": ("camping", "camp"),
    "lac": ("lac", "lac"),
    "cascade": ("cascade", "casc"),
    "grotte": ("grotte", "grot"),
    "via-ferrata": ("via-ferrata", "vf"),
    "chateau": ("chateau", "chat"),
    "culture": ("culture", "mus"),
}


def hav(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def entier(v):
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else None


def details_pour(cat, t):
    """FAITS des tags OSM -> details de fiche (mêmes clés que la France)."""
    d = {}
    alt = entier(t.get("ele"))
    if alt:
        d["altitude"] = f"{alt} m"
        d["altitude_n"] = alt
    if cat == "refuge":
        cap = entier(t.get("capacity"))
        if cap:
            d["capacite"] = f"{cap} places"
            d["places_n"] = cap
    if cat == "cascade" and entier(t.get("height")):
        d["hauteur"] = f"{entier(t.get('height'))} m"
    if cat == "via-ferrata" and t.get("via_ferrata_scale"):
        d["cotation"] = f"K{entier(t['via_ferrata_scale'])}" if entier(t.get("via_ferrata_scale")) \
            else t["via_ferrata_scale"][:12]
    if cat == "chateau":
        d["type"] = "Fort" if (t.get("castle_type") or "") in ("fortress", "defensive", "citadel") else "Château"
        if t.get("ruins") == "yes":
            d["etat"] = "Ruine"
    if cat == "culture" and t.get("opening_hours"):
        d["horaires"] = t["opening_hours"][:200]
    if cat == "grotte":
        d["type"] = "Grotte"
    d["fiche"] = "Référencé" if (t.get("website") or t.get("image")) else "À vérifier"
    return d


def dedoublonner_vf(objets):
    """Les via ferrata OSM sont des tronçons : fusion par nom identique < 1 km."""
    gardes = []
    for o in sorted(objets, key=lambda x: (x["nom"], x["lat"])):
        if any(g["nom"] == o["nom"] and hav(g["lat"], g["lon"], o["lat"], o["lon"]) < 1.0
               for g in gardes):
            continue
        gardes.append(o)
    return gardes


def construire(iso):
    cfg = PAYS[iso]
    osm = json.loads((RACINE / "tools" / f"pays-{iso}-osm.json").read_text(encoding="utf-8"))
    villages = json.loads((RACINE / "tools" / "pays-villages.json").read_text(encoding="utf-8")).get(iso, [])
    feats = []
    stats = {}
    for cat, (theme, abr) in THEMES.items():
        objets = osm.get(cat, [])
        if cat == "via-ferrata":
            objets = dedoublonner_vf(objets)
        objets = sorted(objets, key=lambda o: (o["nom"], o["lat"]))
        for n, o in enumerate(objets, start=1):
            t = o.get("tags", {})
            links = []
            if (t.get("website") or "").startswith("http"):
                links.append({"label": "🌐 Site officiel", "url": t["website"][:300]})
            links.append({"label": "🔎 Infos", "url": "https://www.google.com/search?q=" +
                          quote(f"{o['nom']} {cfg['recherche']}")})
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [o["lon"], o["lat"]]},
                "properties": {
                    "id": f"{iso}-{abr}-{n:04d}",
                    "name": o["nom"],
                    "theme": theme,
                    "description": (t.get("description") or "")[:300],
                    "links": links,
                    "photos": [t["image"]] if t.get("image") else [],
                    "details": details_pour(cat, t),
                },
            })
        stats[theme] = len(objets)

    # Villages labellisés (label officiel du pays, photo + extrait Wikipédia)
    for n, v in enumerate(sorted(villages, key=lambda x: x["nom"]), start=1):
        links = [{"label": "🔗 Wikipédia",
                  "url": f"https://{v['lang']}.wikipedia.org/wiki/" + quote(v["titre"].replace(" ", "_"))},
                 {"label": "🔎 Infos", "url": "https://www.google.com/search?q=" +
                  quote(f"{v['nom']} {cfg['recherche']}")}]
        f = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [v["lon"], v["lat"]]},
            "properties": {
                "id": f"{iso}-vill-{n:04d}",
                "name": v["nom"],
                "theme": "cite-caractere",
                "description": v.get("extrait", ""),
                "links": links,
                "photos": [v["photo"]] if v.get("photo") else [],
                "details": {"label": v["label"], "fiche": "Référencé"},
            },
        }
        feats.append(f)
    stats["cite-caractere"] = len(villages)
    return feats, stats


def main(ecrire):
    for iso, cfg in PAYS.items():
        src = RACINE / "tools" / f"pays-{iso}-osm.json"
        if not src.exists():
            print(f"{iso}: récolte absente — lancer recolter_pays_osm.py {iso.upper()}")
            continue
        feats, stats = construire(iso)
        photos = sum(1 for f in feats if f["properties"]["photos"])
        print(f"{iso} ({cfg['nom']}) : {len(feats)} points — " +
              ", ".join(f"{k} {v}" for k, v in stats.items() if v))
        print(f"   photos {photos} | sites web {sum(1 for f in feats if any('Site officiel' in l['label'] for l in f['properties']['links']))}")
        if not ecrire:
            continue
        dossier = RACINE / "data" / iso
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "points.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
            encoding="utf-8")
        taille = (dossier / "points.geojson").stat().st_size // 1024
        print(f"   ÉCRIT data/{iso}/points.geojson ({taille} Ko)")
    if not ecrire:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main("--ecrire" in sys.argv)
