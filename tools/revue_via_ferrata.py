# -*- coding: utf-8 -*-
"""
Revue qualité de la catégorie « via-ferrata » de data/points.geojson.

Croise les 126 points existants avec deux références :
  - viaferrata-fr.net (cache tools/viaferrata-liste.html) : LA liste de
    référence des via ferrata françaises (nom réel, commune, cotation, année,
    fermetures temporaires) — pas de coordonnées ;
  - OpenStreetMap via Overpass (highway=via_ferrata + via_ferrata_scale) :
    coordonnées réelles du tracé, échelle K1–K6, tyroliennes (aerialway=zip_line),
    longueur, site officiel, wikidata.

Ne renumérote JAMAIS les ids existants (vf-NNN). Corrige un point existant en
place (id conservé) : nom réel, GPS recalé sur le tracé OSM quand notre point
est un centroïde de commune, cotation officielle, champs complétés. Les via
ferrata neuves prolongent la séquence (vf-127…).

Étape 1 (ce fichier, --diag) : parse les références, mesure les écarts GPS,
liste les fiches non couvertes. N'écrit rien.
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import enrichissements as enr

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
CIBLE_POINTS = RACINE / "data" / "points.geojson"
HTML_FICHES = DOSSIER / "viaferrata-liste.html"
CACHE_OSM = DOSSIER / "vf-osm-brut.json"
SITE_VF = "https://www.viaferrata-fr.net/"

# Bornes France + DOM (les VF de La Réunion/Guadeloupe/Martinique sont valides)
LAT_MIN_M, LAT_MAX_M = 41.0, 51.5
LON_MIN_M, LON_MAX_M = -5.5, 10.0

RE_COTATION = re.compile(r"\b(F|PD|AD|D|TD|ED)\b")
ORDRE_COT = ["F", "PD", "AD", "D", "TD", "ED"]


def norm(texte):
    """minuscules sans accents/ponctuation, St->Saint — pour comparer."""
    texte = re.sub(r"\bSte?s?\b\.?", "Saint", texte or "", flags=re.I)
    texte = unicodedata.normalize("NFD", texte)
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texte.lower())


def dist_m(lon1, lat1, lon2, lat2):
    return enr._haversine((lon1, lat1), (lon2, lat2))


# ---------------------------------------------------------------------------
# 1. Référence viaferrata-fr.net : toutes les fiches (nom, commune, cotation)
# ---------------------------------------------------------------------------

def parser_fiches():
    html = HTML_FICHES.read_text(encoding="latin-1")
    fiches = []
    dept_courant = ""
    # Découpe en blocs : en-têtes de département + lignes <tr>
    for bloc in re.split(r"(<tr[^>]*>.*?</tr>)", html, flags=re.S):
        entete = re.search(r'via-ferrata-departement-\d+\.html">([^<]+)</a>', bloc)
        if entete:
            dept_courant = entete.group(1).strip()
        lien = re.search(r'<a href="(via-ferrata-(\d+)-[^"]+\.html)">([^<]+)</a>', bloc)
        if not lien:
            continue
        cells = [re.sub(r"<[^>]+>", "", c).strip()
                 for c in re.findall(r"<td[^>]*>(.*?)</td>", bloc, re.S)]
        # cells[0]=nom, [1]=commune, [2]=cotation, [3]=année
        ville = cells[1] if len(cells) > 1 else ""
        diff = cells[2] if len(cells) > 2 else ""
        annee = cells[3] if len(cells) > 3 else ""
        fiches.append({
            "id": int(lien.group(2)),
            "url": SITE_VF + lien.group(1),
            "nom": lien.group(3).strip(),
            "ville": ville,
            "villeNorm": norm(ville),
            "dept": dept_courant,
            "deptNorm": norm(dept_courant),
            "difficulte": diff,
            "annee": annee,
            "fermeture": "Fermeture temporaire" in bloc,
        })
    return fiches


# ---------------------------------------------------------------------------
# 2. OSM : segments -> sites VF distincts (clustering spatial par proximité)
# ---------------------------------------------------------------------------

def _coord(e):
    lat = e.get("lat") or (e.get("center") or {}).get("lat")
    lon = e.get("lon") or (e.get("center") or {}).get("lon")
    return lon, lat


def _scale_num(v):
    m = re.match(r"(\d)", str(v or ""))
    return int(m.group(1)) if m else None


def clusterer_osm(rayon=700):
    els = json.loads(CACHE_OSM.read_text(encoding="utf-8"))
    segs = []
    for e in els:
        lon, lat = _coord(e)
        if lon is None:
            continue
        t = e.get("tags") or {}
        segs.append({
            "lon": lon, "lat": lat,
            "nom": (t.get("name") or t.get("name:fr") or "").strip(),
            "scale": _scale_num(t.get("via_ferrata_scale")),
            "zip": t.get("aerialway") == "zip_line",
            "website": (t.get("website") or t.get("contact:website") or "").strip(),
            "wikidata": (t.get("wikidata") or "").strip(),
            "length": t.get("length"),
            "descr": (t.get("description") or "").strip(),
        })
    # Clustering greedy par proximité (segments contigus d'une même VF)
    clusters = []
    for s in segs:
        best = None
        for c in clusters:
            d = dist_m(s["lon"], s["lat"], c["lon"], c["lat"])
            if d < rayon and (best is None or d < best[1]):
                best = (c, d)
        if best:
            c = best[0]
            c["membres"].append(s)
        else:
            clusters.append({"lon": s["lon"], "lat": s["lat"], "membres": [s]})
        # recalcule le centroïde du cluster choisi/créé
        c = best[0] if best else clusters[-1]
        n = len(c["membres"])
        c["lon"] = sum(m["lon"] for m in c["membres"]) / n
        c["lat"] = sum(m["lat"] for m in c["membres"]) / n
    # Synthèse par cluster
    sites = []
    for c in clusters:
        ms = c["membres"]
        noms = [m["nom"] for m in ms if m["nom"]]
        # nom principal = le plus fréquent
        nom = max(set(noms), key=noms.count) if noms else ""
        scales = [m["scale"] for m in ms if m["scale"] is not None]
        sites.append({
            "lon": round(c["lon"], 6), "lat": round(c["lat"], 6),
            "nom": nom,
            "noms": sorted(set(noms)),
            "scale_max": max(scales) if scales else None,
            "zip": any(m["zip"] for m in ms),
            "website": next((m["website"] for m in ms if m["website"]), ""),
            "wikidata": next((m["wikidata"] for m in ms if m["wikidata"]), ""),
            "n_seg": len(ms),
        })
    return sites


# ---------------------------------------------------------------------------
# 3. Diagnostic
# ---------------------------------------------------------------------------

def charger_points():
    d = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
    return d, [f for f in d["features"] if f["properties"].get("theme") == "via-ferrata"]


def diag():
    fiches = parser_fiches()
    print(f"viaferrata-fr.net : {len(fiches)} fiches de référence")
    sites = clusterer_osm()
    print(f"OSM : {len(sites)} sites VF distincts (clusters), "
          f"dont {sum(1 for s in sites if s['nom'])} nommés")
    _, points = charger_points()
    print(f"Notre base : {len(points)} via ferrata\n")

    # 3a. Écarts GPS : distance de chaque point au site OSM le plus proche
    tranches = {"<100m": 0, "100-500m": 0, "500m-2km": 0, "2-8km": 0, ">8km/aucun": 0}
    details_loin = []
    for f in points:
        lon, lat = f["geometry"]["coordinates"][:2]
        proche, dmin = None, 1e9
        for s in sites:
            d = dist_m(lon, lat, s["lon"], s["lat"])
            if d < dmin:
                dmin, proche = d, s
        if dmin < 100:
            tranches["<100m"] += 1
        elif dmin < 500:
            tranches["100-500m"] += 1
        elif dmin < 2000:
            tranches["500m-2km"] += 1
        elif dmin < 8000:
            tranches["2-8km"] += 1
        else:
            tranches[">8km/aucun"] += 1
        if dmin >= 500:
            details_loin.append((f["properties"]["id"], f["properties"]["name"],
                                 round(dmin), proche["nom"] if proche else "-"))
    print("Écart GPS de nos points au site OSM le plus proche :")
    for k, v in tranches.items():
        print(f"  {k:14s} {v}")
    print(f"\nPoints à > 500 m d'un site OSM (candidats recalage) : {len(details_loin)}")
    for pid, nom, d, osmnom in sorted(details_loin, key=lambda x: -x[2])[:40]:
        print(f"  {pid} {d:6d}m  {nom[:38]:38s} -> OSM: {osmnom[:30]}")

    # 3b. Couverture des fiches par commune+dept
    idx_pts = {}
    d_full, _ = charger_points()
    for f in points:
        # commune : extraite du nom "Via ferrata de X" et de la description
        m = re.search(r"Département : (\d+)", f["properties"].get("description", ""))
        idx_pts.setdefault(norm(f["properties"]["name"].replace("Via ferrata de ", "")), []).append(f)
    couvertes, manquantes = 0, []
    for fi in fiches:
        # une fiche est couverte si un de nos points est dans la même commune
        trouve = any(fi["villeNorm"] and (fi["villeNorm"] in k or k in fi["villeNorm"])
                     for k in idx_pts)
        if trouve:
            couvertes += 1
        else:
            manquantes.append(fi)
    print(f"\nFiches viaferrata-fr.net couvertes par commune : {couvertes}/{len(fiches)}")
    print(f"Fiches SANS point correspondant (à investiguer) : {len(manquantes)}")
    for fi in manquantes:
        flag = " [FERMÉE]" if fi["fermeture"] else ""
        print(f"  #{fi['id']:3d} {fi['nom'][:34]:34s} {fi['ville'][:22]:22s} "
              f"{fi['dept'][:20]:20s} {fi['difficulte'][:14]}{flag}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    diag()
