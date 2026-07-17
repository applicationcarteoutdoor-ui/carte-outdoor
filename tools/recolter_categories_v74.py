"""Catégories v74 (France) + enrichissement des sommets à croix.

  - panorama          : OSM tourism=viewpoint NOMMÉS (~4 400) — altitude,
                        table d'orientation, direction quand présents
  - plongee           : OSM sport=scuba_diving (~360)
  - phare             : OSM man_made=lighthouse nommés (~355) + Wikipédia
  - arbre-remarquable : OSM natural=tree + denotation=natural_monument (~3 000)
  - sommet-croix      : RE-parcouru pour ajouter article Wikipédia/photo aux
                        143 existants (mise à jour EN PLACE, ids conservés)

Même mécanique d'intégration que recolter_categories_v72 : append dans
data/points.geojson, ids stables (pano-, plon-, phare-, arbre-), relance =
mise à jour EN PLACE par clé theme|nom|lat3.

Usage : python tools/recolter_categories_v74.py [--ecrire]
"""

import json
import sys
import time
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recolter_categories_v72 import (  # noqa: E402 — mécanique partagée
    RACINE, overpass, wiki_api, _centre, _hav_km, sommets_croix,
)


def _alt(details, tags):
    if (tags.get("ele") or "").replace(".", "").isdigit():
        alt = int(float(tags["ele"]))
        details["altitude"] = f"{alt} m"
        details["altitude_n"] = alt


def panoramas():
    d = overpass('[out:json][timeout:180];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["tourism"="viewpoint"]["name"](area.p););out center tags;')
    pts, vus = [], set()
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        nom = (t.get("name") or "").strip()
        if lat is None or not nom:
            continue
        cle = f"{nom.lower()}|{round(lat, 3)}"
        if cle in vus:
            continue
        vus.add(cle)
        details = {"fiche": "À vérifier"}
        _alt(details, t)
        if t.get("information") == "tab" or t.get("board_type") == "orientation_table" \
           or "orientation" in (t.get("information") or ""):
            details["equipement"] = "Table d'orientation"
        pts.append({"nom": nom, "lat": round(lat, 6), "lon": round(lon, 6),
                    "details": details, "links": [], "photos": [], "description": ""})
    print(f"panoramas : {len(pts)}", flush=True)
    return pts


def plongees():
    d = overpass('[out:json][timeout:180];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["sport"="scuba_diving"](area.p););out center tags;')
    pts = []
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        if lat is None:
            continue
        links = []
        if (t.get("website") or "").startswith("http"):
            links.append({"label": "🌐 Site", "url": t["website"].replace(" ", "")[:300]})
        pts.append({"nom": (t.get("name") or "Spot de plongée").strip(),
                    "lat": round(lat, 6), "lon": round(lon, 6),
                    "details": {"fiche": "À vérifier"}, "links": links,
                    "photos": [], "description": ""})
    print(f"plongée : {len(pts)}", flush=True)
    return pts


def _croiser_wikipedia(pts, marge_km=10):
    """Ajoute article/photo/description Wikipédia fr (nom EXACT ≤ marge_km)."""
    enrichis = 0
    for i in range(0, len(pts), 50):
        lot = pts[i:i + 50]
        d = wiki_api("fr.wikipedia.org", titles="|".join(p["nom"] for p in lot),
                     redirects="1", prop="coordinates|pageimages|extracts",
                     colimit="max", piprop="thumbnail", pithumbsize="960",
                     exintro="1", explaintext="1", exsentences="1", exlimit="max")
        pages = {p["title"]: p for p in (d.get("query") or {}).get("pages", []) if not p.get("missing")}
        redir = {r["from"]: r["to"] for r in (d.get("query") or {}).get("redirects", [])}
        for p in lot:
            page = pages.get(redir.get(p["nom"], p["nom"]))
            if not page:
                continue
            coord = (page.get("coordinates") or [{}])[0]
            if not coord.get("lat") or _hav_km(p["lat"], p["lon"], coord["lat"], coord["lon"]) > marge_km:
                continue
            th = (page.get("thumbnail") or {}).get("source", "")
            p["links"] = [{"label": "🔗 Wikipédia",
                           "url": "https://fr.wikipedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_"))}] \
                + [l for l in p["links"] if l["label"] != "🔗 Wikipédia"]
            if th.startswith("https://upload.wikimedia.org") and not p["photos"]:
                p["photos"] = [th]
            if not p["description"]:
                p["description"] = (page.get("extract") or "").strip()[:300]
            p["details"]["fiche"] = "Référencé"
            enrichis += 1
        time.sleep(1.2)
    print(f"  … {enrichis}/{len(pts)} enrichis Wikipédia", flush=True)
    return pts


def phares():
    d = overpass('[out:json][timeout:180];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["man_made"="lighthouse"]["name"](area.p););out center tags;')
    pts, vus = [], set()
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        nom = (t.get("name") or "").strip()
        if lat is None or not nom:
            continue
        cle = f"{nom.lower()}|{round(lat, 3)}"
        if cle in vus:
            continue
        vus.add(cle)
        details = {"fiche": "À vérifier"}
        if (t.get("height") or "").replace(".", "").isdigit():
            details["hauteur"] = f"{int(float(t['height']))} m"
        pts.append({"nom": nom, "lat": round(lat, 6), "lon": round(lon, 6),
                    "details": details, "links": [], "photos": [], "description": ""})
    print(f"phares : {len(pts)}", flush=True)
    return _croiser_wikipedia(pts, 5)


def arbres():
    d = overpass('[out:json][timeout:180];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["natural"="tree"]["denotation"="natural_monument"](area.p););out center tags;')
    pts = []
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        if lat is None:
            continue
        nom = (t.get("name") or "").strip()
        espece = (t.get("species:fr") or t.get("genus:fr") or t.get("species") or "").strip()
        details = {"fiche": "À vérifier"}
        if espece:
            details["espece"] = espece[:60]
        if (t.get("circumference") or "").replace(".", "").replace(",", "").isdigit():
            details["circonference"] = f"{t['circumference'].replace(',', '.')} m"
        pts.append({"nom": nom or (espece and f"{espece} remarquable") or "Arbre remarquable",
                    "lat": round(lat, 6), "lon": round(lon, 6),
                    "details": details, "links": [], "photos": [], "description": ""})
    print(f"arbres remarquables : {len(pts)}", flush=True)
    return pts


def integrer(ecrire):
    croix = _croiser_wikipedia(sommets_croix(), 5)  # maj EN PLACE des 143
    recoltes = {
        "panorama": ("pano", panoramas()),
        "plongee": ("plon", plongees()),
        "phare": ("phare", phares()),
        "arbre-remarquable": ("arbre", arbres()),
        "sommet-croix": ("croix", croix),
    }
    chemin = RACINE / "data" / "points.geojson"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    existants = {f["properties"]["id"]: f for f in d["features"]}
    cles_connues = {}
    for f in d["features"]:
        p = f["properties"]
        cles_connues[f'{p["theme"]}|{p["name"].lower()}|{round(f["geometry"]["coordinates"][1], 3)}'] = p["id"]
    for theme, (abr, pts) in recoltes.items():
        suivant = 1 + max([int(i.split("-")[-1]) for i in existants if i.startswith(abr + "-")] or [0])
        n_nouveaux = n_maj = 0
        for p in sorted(pts, key=lambda x: (x["nom"], x["lat"])):
            cle = f'{theme}|{p["nom"].lower()}|{round(p["lat"], 3)}'
            pid = cles_connues.get(cle)
            feat = {"type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                    "properties": {"id": pid or f"{abr}-{suivant:04d}", "name": p["nom"],
                                   "theme": theme, "description": p["description"],
                                   "links": p["links"], "photos": p["photos"],
                                   "details": p["details"]}}
            if pid and pid in existants:
                existants[pid].update(feat)
                n_maj += 1
            else:
                d["features"].append(feat)
                suivant += 1
                n_nouveaux += 1
        print(f"{theme}: +{n_nouveaux} nouveaux, {n_maj} mis à jour", flush=True)
    if ecrire:
        chemin.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT data/points.geojson ({chemin.stat().st_size // 1024} Ko)")
    else:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    integrer("--ecrire" in sys.argv)
