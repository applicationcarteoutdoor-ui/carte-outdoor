# -*- coding: utf-8 -*-
"""
Phase 2 du recalage « chateau » : recaler les châteaux ENCORE au centroïde de
commune (après recaler_chateaux.py) à partir d'OpenStreetMap (ODbL).

Source : Overpass `historic=castle|fort|fortress|manor|citadel` en France, par
tuiles de 3° (area ISO3166-1=FR). Recalage CONSERVATEUR : on ne bouge un point
que si un château OSM au NOM correspondant est UNIQUE à < 12 km du centroïde —
sinon on laisse (recaler sur le mauvais château est pire que le centroïde).
Si l'objet OSM porte un tag wikipedia:fr, on rétablit aussi le lien.

FAITS réutilisables (coordonnées, tag wikipedia) — jamais de prose.

Lancer :  python tools/recaler_chateaux_osm.py            (simulation)
          python tools/recaler_chateaux_osm.py --ecrire   (écrit points.geojson)
"""

import json
import re
import sys
import time
import unicodedata
import urllib.parse
from collections import defaultdict
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import enrichissements as enr

DOSSIER = Path(__file__).resolve().parent
CIBLE = DOSSIER.parent / "data" / "points.geojson"
CACHE_OSM = DOSSIER / "chateaux-osm.json"
STATUT = DOSSIER / "chateaux-osm-status.json"

LAT_MIN, LAT_MAX = 41.0, 51.5
LON_MIN, LON_MAX = -5.5, 10.0
RAYON_KM = 12.0
RE_CENTRE = re.compile(r"\(Position au centre de la commune\.?\)", re.I)
TYPES = ("castle", "fort", "fortress", "manor", "citadel")


def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def hav(lat1, lon1, lat2, lon2):
    R = 6371000
    dla, dlo = radians(lat2 - lat1), radians(lon2 - lon1)
    x = sin(dla / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlo / 2) ** 2
    return R * 2 * atan2(sqrt(x), sqrt(1 - x))


def coeur(nom):
    """Nom château → cœur comparable : sans « Château/Fort… de/du/la », sans
    « à Commune » / « dans le Dépt »."""
    n = re.split(r"\s(?:à|au|aux|dans|en)\s", nom or "")[0].strip().rstrip(",")
    n = re.sub(r"^(le|la|les|l['’])\s*", "", n, flags=re.I)
    n = re.sub(r"^(château|chateau|manoir|fort(?:eresse)?|citadelle|palais|abbaye|"
               r"tour|bastide|commanderie|donjon|chartreuse|maison forte)\s+"
               r"(de la |de l['’]|des |du |de |d['’])?", "", n, flags=re.I)
    return norm(n)


def telecharger_osm():
    if CACHE_OSM.exists():
        return json.loads(CACHE_OSM.read_text(encoding="utf-8"))
    print("  Overpass historic=castle|fort|… (tuiles 3°)…")
    filtre = "|".join(TYPES)
    tuiles, lon = [], LON_MIN
    while lon < LON_MAX:
        lat = LAT_MIN
        while lat < LAT_MAX:
            tuiles.append(f"{lat},{lon},{min(lat + 3, LAT_MAX)},{min(lon + 3, LON_MAX)}")
            lat += 3
        lon += 3
    elements = {}
    for passe in range(1, 4):
        if not tuiles:
            break
        if passe > 1:
            print(f"  passe {passe} : {len(tuiles)} tuile(s), pause 90 s…"); time.sleep(90)
        restantes = []
        for i, bbox in enumerate(tuiles):
            req = ('[out:json][timeout:180];'
                   'area["ISO3166-1"="FR"]["admin_level"="2"]->.fr;'
                   f'nwr["historic"~"^({filtre})$"]["name"](area.fr)({bbox});'
                   'out center;')
            try:
                d = enr._overpass(req)
                for e in d.get("elements", []):
                    elements[f"{e['type']}{e['id']}"] = e
            except Exception as exc:
                restantes.append(bbox); print(f"    ! {bbox} : {exc}")
            STATUT.write_text(json.dumps({"passe": passe, "tuile": i + 1,
                                          "total": len(tuiles), "trouves": len(elements)}),
                              encoding="utf-8")
            time.sleep(2)
        tuiles = restantes
    liste = []
    for e in elements.values():
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        tags = e.get("tags") or {}
        nom = tags.get("name") or tags.get("name:fr")
        if lat is None or nom is None:
            continue
        wp = tags.get("wikipedia:fr") or tags.get("wikipedia") or ""
        if wp and not wp.lower().startswith(("fr:",)) and ":" in wp:
            wp = ""  # autre langue
        liste.append({"lat": lat, "lon": lon, "nom": nom,
                      "coeur": coeur(nom), "wikipedia": wp})
    if not tuiles:
        CACHE_OSM.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    else:
        print(f"  ! {len(tuiles)} tuile(s) en échec : cache NON sauvé")
    print(f"  OSM : {len(liste)} châteaux nommés")
    return liste


def main(ecrire=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    osm = telecharger_osm()
    grille = defaultdict(list)
    for s in osm:
        grille[(round(s["lat"], 1), round(s["lon"], 1))].append(s)

    def proches(lat, lon):
        out = []
        for dla in (-0.1, 0, 0.1):
            for dlo in (-0.1, 0, 0.1):
                out += grille.get((round(lat + dla, 1), round(lon + dlo, 1)), [])
        return out

    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    ch = [f for f in d["features"] if f["properties"].get("theme") == "chateau"]
    au_centre = [f for f in ch if RE_CENTRE.search(f["properties"].get("description", ""))]
    print(f"chateaux au centroïde à traiter : {len(au_centre)}")

    st = {"recale": 0, "relie": 0, "ambigu": 0, "sans_match": 0}
    for f in au_centre:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2]
        cible = coeur(p["name"])
        if not cible or len(cible) < 3:
            st["sans_match"] += 1
            continue
        cand = []
        for s in proches(lat, lon):
            dkm = hav(lat, lon, s["lat"], s["lon"]) / 1000
            if dkm > RAYON_KM:
                continue
            c = s["coeur"]
            if not c:
                continue
            exact = (c == cible)
            # correspondance partielle (un cœur contient l'autre) : plus risquée
            # (noms génériques « la Motte »…) → cœurs ≥ 5 lettres ET < 5 km.
            partiel = (not exact and len(c) >= 5 and len(cible) >= 5
                       and (c in cible or cible in c) and dkm <= 5.0)
            if exact or partiel:
                cand.append(s)
        # correspondance CERTAINE = un seul château OSM au nom correspondant
        uniques = {(round(s["lat"], 5), round(s["lon"], 5)) for s in cand}
        if len(uniques) != 1:
            st["ambigu" if cand else "sans_match"] += 1
            continue
        s = cand[0]
        f["geometry"]["coordinates"] = [round(s["lon"], 6), round(s["lat"], 6)]
        p["description"] = RE_CENTRE.sub("", p.get("description", "")).strip()
        st["recale"] += 1
        if not p.get("link") and s.get("wikipedia"):
            titre = s["wikipedia"].split(":", 1)[-1].strip().replace(" ", "_")
            p["link"] = "https://fr.wikipedia.org/wiki/" + urllib.parse.quote(titre)
            p.setdefault("details", {})["fiche"] = "Référencé"
            st["relie"] += 1

    print(f"\nRecalés via OSM : {st['recale']} (dont reliés à Wikipédia : {st['relie']})")
    print(f"Non recalés : ambigus (≥2 châteaux OSM) {st['ambigu']}, "
          f"sans correspondance {st['sans_match']}")
    reste = len(au_centre) - st["recale"]
    print(f"Restent au centroïde : {reste}")

    if ecrire:
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT. {CIBLE.stat().st_size // 1024} Ko")
    else:
        print("(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    main(ecrire="--ecrire" in sys.argv)
