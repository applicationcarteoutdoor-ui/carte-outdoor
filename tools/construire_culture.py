# -*- coding: utf-8 -*-
"""
Intègre la catégorie CULTURE (musées, galeries, sites archéologiques,
monuments — source OSM, ODbL) :
  - France : data/culture.geojson — COUCHE LOURDE à la demande (~15 000 lieux,
    hors pré-cache, ids stables cult-####), comme toilettes/eau/grottes ;
  - NZ     : data/nz/points.geojson — catégorie normale (ids nz-cult-####).

Ids posés par ordre alphabétique de (nom, lat) à la PREMIÈRE création — comme
partout, jamais renumérotés (statuts/carnet). Réexécuter remplace EN PLACE les
features culture (idempotent).

Lancer :  python tools/construire_culture.py            (aperçu)
          python tools/construire_culture.py --ecrire   (écrit)
"""

import json
import sys
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
# Décision utilisateur (v66) : la catégorie se limite aux MUSÉES — les sites
# archéologiques (6 273, souvent des dolmens anonymes), monuments (1 513,
# plaques et obélisques) et galeries (2 080, surtout des boutiques d'art)
# noyaient la catégorie sans apporter de qualité.
TYPES = {
    "musee": "Musée",
}
CIBLES = {
    # France : fichier SÉPARÉ (couche lourde, remplacé entièrement)
    "fr": {"source": RACINE / "tools" / "culture-fr-osm.json",
           "points": RACINE / "data" / "culture.geojson", "prefixe": "cult",
           "seul": True},
    # NZ : fusionné dans les points du pays (catégorie normale)
    "nz": {"source": RACINE / "tools" / "culture-nz-osm.json",
           "points": RACINE / "data" / "nz" / "points.geojson", "prefixe": "nz-cult",
           "seul": False},
}


def construire(pays):
    cfg = CIBLES[pays]
    lieux = json.loads(cfg["source"].read_text(encoding="utf-8"))
    lieux = [o for o in lieux if o["type"] in TYPES]  # musées uniquement (v66)
    lieux.sort(key=lambda o: (o["nom"], o["lat"]))
    # Enrichissement Wikipédia (photo/description/lien) — facultatif :
    # tools/culture-wiki-<pays>.json, clé « nom|lat4 » (enrichir_culture_wikipedia.py)
    fwiki = RACINE / "tools" / f"culture-wiki-{pays}.json"
    wiki = json.loads(fwiki.read_text(encoding="utf-8")) if fwiki.exists() else {}
    feats = []
    for n, o in enumerate(lieux, start=1):
        w = wiki.get(f"{o['nom']}|{round(o['lat'], 4)}") or {}
        d = {"type": TYPES.get(o["type"], "Patrimoine")}
        if o.get("horaires"):
            d["horaires"] = o["horaires"][:200]
        if o.get("commune"):
            d["commune"] = o["commune"]
        d["fiche"] = "Référencé" if (o.get("site") or w.get("wiki")) else "À vérifier"
        links = []
        if (o.get("site") or "").startswith("http"):
            links.append({"label": "🌐 Site officiel", "url": o["site"][:300]})
        if w.get("wiki"):
            links.append({"label": "🔗 Wikipédia", "url": w["wiki"]})
        links.append({"label": "🔎 Infos visiteur", "url": "https://www.google.com/search?q=" +
                      quote(f"{o['nom']} {o.get('commune', '')}".strip())})
        photos = [o["image"]] if o.get("image") else ([w["photo"]] if w.get("photo") else [])
        f = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [o["lon"], o["lat"]]},
            "properties": {
                "id": f"{cfg['prefixe']}-{n:04d}",
                "name": o["nom"],
                "theme": "culture",
                "description": o.get("description") or w.get("description", ""),
                "links": links,
                "photos": photos,
                "details": d,
            },
        }
        feats.append(f)
    return feats


def main(ecrire):
    for pays, cfg in CIBLES.items():
        if not cfg["source"].exists():
            print(f"{pays}: source absente ({cfg['source'].name}) — lancer recolter_culture_osm.py")
            continue
        feats = construire(pays)
        types = {}
        for f in feats:
            t = f["properties"]["details"]["type"]
            types[t] = types.get(t, 0) + 1
        sites = sum(1 for f in feats if f["properties"]["details"]["fiche"] == "Référencé")
        horaires = sum(1 for f in feats if "horaires" in f["properties"]["details"])
        photos = sum(1 for f in feats if f["properties"]["photos"])
        print(f"{pays}: {len(feats)} lieux — {types}")
        print(f"   site web {sites} ({100 * sites // max(1, len(feats))}%) | "
              f"horaires {horaires} | photos {photos}")
        if not ecrire:
            continue
        if cfg["seul"]:
            cfg["points"].write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                ensure_ascii=False), encoding="utf-8")
            print(f"   ÉCRIT {cfg['points'].name} : {len(feats)} features "
                  f"({cfg['points'].stat().st_size // 1024} Ko, couche à la demande)")
        else:
            data = json.loads(cfg["points"].read_text(encoding="utf-8"))
            avant = len(data["features"])
            data["features"] = [f for f in data["features"] if f["properties"].get("theme") != "culture"]
            data["features"].extend(feats)
            cfg["points"].write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            print(f"   ÉCRIT {cfg['points'].name} : {avant} -> {len(data['features'])} features")
    if not ecrire:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main("--ecrire" in sys.argv)
