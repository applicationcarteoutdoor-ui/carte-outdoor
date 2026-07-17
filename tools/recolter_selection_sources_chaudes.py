"""Colis « Sélection SpotMap » : les SOURCES CHAUDES naturelles d'Europe.

Récolte OSM (`natural=hot_spring`, ODbL — faits seulement) sur les pays de
l'app + voisins alpins, dédoublonnage < 300 m, plafond 500 points (limite du
format de colis communautaire). Écrit data/communaute/selection.json : une
liste de colis au format partagé (formatVersion 1), importables hors serveur.
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
PAYS = ["FR", "CH", "IT", "ES", "PT", "DE", "AT", "GR", "IS"]  # volontairement large : la catégorie est un cadeau


def overpass(req, essais=4):
    for i in range(essais):
        try:
            r = urllib.request.Request(OVERPASS, data=urllib.parse.urlencode({"data": req}).encode(),
                                       headers={"User-Agent": "SpotMap/1.0 (contact bidband4@gmail.com)"})
            return json.load(urllib.request.urlopen(r, timeout=180))
        except Exception as e:
            print(f"  (Overpass occupé, pause {20 * (i + 1)} s… {e})", flush=True)
            time.sleep(20 * (i + 1))
    return {"elements": []}


def _centre(e):
    if e.get("lat") is not None:
        return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")


def main():
    bruts = []
    for iso in PAYS:
        d = overpass(f'[out:json][timeout:120];area["ISO3166-1"="{iso}"][admin_level=2]->.p;'
                     f'(nwr["natural"="hot_spring"](area.p););out center tags;')
        n = 0
        for e in d.get("elements", []):
            lat, lon = _centre(e)
            if lat is None:
                continue
            t = e.get("tags", {})
            bruts.append({"iso": iso.lower(), "lat": round(lat, 5), "lon": round(lon, 5),
                          "nom": (t.get("name") or "").strip(), "tags": t})
            n += 1
        print(f"{iso}: {n} sources chaudes", flush=True)
        time.sleep(8)

    # dédoublonnage < 300 m (les nommées gagnent sur les anonymes)
    bruts.sort(key=lambda b: (b["nom"] == "", b["nom"]))
    gardes = []
    for b in bruts:
        if any(abs(g["lat"] - b["lat"]) < 0.003 and abs(g["lon"] - b["lon"]) < 0.004 for g in gardes):
            continue
        gardes.append(b)

    feats = []
    for b in gardes[:500]:
        t = b["tags"]
        details = {}
        if t.get("temperature"):
            details["temperature"] = str(t["temperature"])[:20] + ("°C" if str(t["temperature"]).replace(".", "").isdigit() else "")
        if t.get("access") in ("private", "no"):
            details["acces"] = "Privé"
        if t.get("fee") == "yes":
            details["acces"] = (details.get("acces", "") + " · payant").strip(" ·")
        links = []
        if (t.get("website") or "").startswith("http"):
            links.append({"label": "🌐 Site", "url": t["website"].replace(" ", "")[:300]})
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [b["lon"], b["lat"]]},
            "properties": {
                "name": b["nom"] or f"Source chaude ({b['iso'].upper()})",
                "description": "",
                "details": details,
                "links": links,
            },
        })

    colis = {
        "id": "selection-sources-chaudes",
        "formatVersion": 1,
        "nom": "Sources chaudes naturelles",
        "description": "Bains chauds sauvages et sources thermales naturelles d'Europe "
                       "(France, Alpes, Espagne, Portugal, Islande…) — l'eau fumante après la rando. "
                       "Source : OpenStreetMap (ODbL).",
        "pays": "eu",
        "theme": {"label": "Source chaude", "color": "#c2452d", "textColor": "#ffffff", "icon": "♨️"},
        "points": feats,
    }
    dossier = RACINE / "data" / "communaute"
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "selection.json").write_text(json.dumps([colis], ensure_ascii=False), encoding="utf-8")
    print(f"ÉCRIT data/communaute/selection.json — {len(feats)} points "
          f"({sum(1 for f in feats if not f['properties']['name'].startswith('Source chaude ('))} nommés)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
