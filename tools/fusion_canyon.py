# -*- coding: utf-8 -*-
"""
Fusion de la catégorie « canyon » (canyonisme) dans data/points.geojson.

Socle  : RES / Data ES (Licence Ouverte Etalab 2.0) — position + nom + commune +
         longueur + dénivelé, pour ~1 274 canyons français (métropole + DOM).
Faits  : OpenStreetMap (ODbL) — cotation FFME, hauteur du plus grand rappel
         (→ corde estimée), site web et TRACÉ, greffés par PROXIMITÉ + NOM
         (conservateur) sur les canyons RES correspondants (~32 recouverts).

Ce que les données libres NE donnent PAS (honnêteté, cf. rapport de revue) :
temps d'approche et de retour (uniquement dans les topos rédigés, protégés).
Aucune prose ni photo recopiée. Ids stables `canyon-####` (première création).

Sorties : data/points.geojson (features theme=canyon) + data/canyons-traces.geojson
Lancer  : python tools/fusion_canyon.py            (aperçu)
          python tools/fusion_canyon.py --ecrire   (écrit)
"""

import json
import math
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
RES = RACINE / "tools" / "canyon-res.json"
OSM = RACINE / "tools" / "canyon-osm.json"
POINTS = RACINE / "data" / "points.geojson"
TRACES = RACINE / "data" / "canyons-traces.geojson"

R_MATCH_KM = 3.0        # rayon max pour rapprocher un canyon OSM d'un canyon RES
R_UNIQUE_KM = 1.2       # si un seul RES très proche, match même sans mot commun
MOTS_VIDES = {"de", "du", "des", "la", "le", "les", "l", "d", "canyon", "canyoning",
              "ruisseau", "riu", "ruissea", "gorge", "gorges", "defile", "ravine",
              "ravin", "arrec", "valat", "riviere", "vallon", "clue", "clues"}


def sans_accents(s):
    return "".join(c for c in unicodedata.normalize("NFD", s or "")
                   if unicodedata.category(c) != "Mn")


def tokens(nom):
    mots = re.split(r"[^a-z0-9]+", sans_accents(nom).lower())
    return {m for m in mots if m and m not in MOTS_VIDES and len(m) >= 3}


def hav(la1, lo1, la2, lo2):
    r = 6371.0
    p1, p2 = math.radians(la1), math.radians(la2)
    dp = math.radians(la2 - la1)
    dl = math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def num(v):
    try:
        return round(float(v))
    except (TypeError, ValueError):
        return None


def rapprocher(res, osm):
    """Associe chaque canyon OSM au canyon RES correspondant (conservateur).
    Renvoie {index_res: canyon_osm}. Un OSM non rapproché est ABANDONNÉ."""
    assoc = {}
    for o in osm:
        cand = []  # (dkm, i_res, mots_communs)
        for i, r in enumerate(res):
            dkm = hav(o["lat"], o["lon"], r["lat"], r["lon"])
            if dkm <= R_MATCH_KM:
                communs = tokens(o["nom"]) & tokens(r["nom"])
                cand.append((dkm, i, len(communs)))
        if not cand:
            continue
        # priorité : mots communs puis proximité
        avec_mot = [c for c in cand if c[2] >= 1]
        if avec_mot:
            avec_mot.sort(key=lambda c: (-c[2], c[0]))
            dkm, i, _ = avec_mot[0]
        else:
            cand.sort(key=lambda c: c[0])
            dkm, i, _ = cand[0]
            if dkm > R_UNIQUE_KM or len([c for c in cand if c[0] <= R_UNIQUE_KM]) != 1:
                continue  # ambigu et sans mot commun -> on n'invente pas
        # un RES ne prend que le meilleur OSM (le plus proche)
        if i in assoc and hav(res[i]["lat"], res[i]["lon"], assoc[i]["lat"], assoc[i]["lon"]) <= dkm:
            continue
        assoc[i] = o
    return assoc


def details_canyon(r, o):
    """Construit le dict details d'un canyon (faits seulement)."""
    d = {}
    dep = r.get("dep_nom") or r.get("dep") or ""
    d["commune"] = f"{r['commune']} ({dep})" if dep else r["commune"]
    lo = num(r.get("long"))
    if lo:
        d["longueur"] = f"{lo} m"
        d["longueur_n"] = lo
    ha = num(r.get("haut"))
    if ha:
        d["denivele"] = f"{ha} m"
        d["denivele_n"] = ha
    if o:
        if o.get("rating"):
            d["cotation"] = re.sub(r"\s+", "", o["rating"])   # « v3 a3 III » -> « v3a3III »
        rap = num(o.get("abseil"))
        if rap and rap > 0:
            d["rappel"] = f"{rap} m"
            d["corde"] = f"≈ {rap} m (estimation)"
            d["corde_n"] = rap
    libre = str(r.get("acces_libre")).lower() == "true"
    d["acces"] = "Accès libre" if libre else "Accès réglementé"
    d["acces_type"] = "libre" if libre else "reglemente"  # _type : masqué en fiche, sert au filtre
    return d


def liens(r, o):
    L = []
    if o and o.get("website"):
        L.append({"label": "🌐 Topo (OpenStreetMap)", "url": o["website"]})
    # recherche : c'est LÀ que l'utilisateur trouvera corde/horaires (topos protégés)
    q = quote(f"{r['nom']} canyon {r['commune']}")
    L.append({"label": "🔎 Topo, corde & horaires", "url": f"https://www.google.com/search?q={q}"})
    return L


def construire():
    res = json.loads(RES.read_text(encoding="utf-8"))
    osm = json.loads(OSM.read_text(encoding="utf-8"))
    res.sort(key=lambda r: r.get("id") or "")   # ordre stable (equip_numero)
    assoc = rapprocher(res, osm)

    feats, traces = [], []
    for n, r in enumerate(res, start=1):
        cid = f"canyon-{n:04d}"
        o = assoc.get(n - 1)
        det = details_canyon(r, o)
        a_trace = bool(o and o.get("segments"))
        props = {
            "id": cid,
            "name": r["nom"],
            "theme": "canyon",
            "description": "",
            "links": liens(r, o),
            "photos": [],
            "details": det,
        }
        if a_trace:
            props["trace"] = True   # active le bouton 📥 GPX (tracé disponible)
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
            "properties": props,
        })
        if a_trace:
            traces.append({
                "type": "Feature",
                "geometry": {"type": "MultiLineString", "coordinates": o["segments"]},
                "properties": {"id": cid, "name": r["nom"], "osm_id": o["osm_id"]},
            })
    return feats, traces, assoc


def main(ecrire):
    feats, traces, assoc = construire()
    enrichis = sum(1 for f in feats if "cotation" in f["properties"]["details"]
                   or "rappel" in f["properties"]["details"])
    print(f"Canyons construits : {len(feats)}")
    print(f"  enrichis OSM (cotation/rappel) : {enrichis}")
    print(f"  avec tracé                     : {len(traces)}")
    print(f"  rapprochements OSM→RES         : {len(assoc)}/{len(json.loads(OSM.read_text(encoding='utf-8')))}")
    ex = feats[0]["properties"]
    print(f"\nExemple : {ex['id']} {ex['name']!r}\n  details={json.dumps(ex['details'],ensure_ascii=False)}")
    # un exemple enrichi
    for f in feats:
        if "cotation" in f["properties"]["details"]:
            p = f["properties"]
            print(f"  enrichi : {p['id']} {p['name']!r} -> {json.dumps(p['details'],ensure_ascii=False)}")
            break
    if not ecrire:
        print("\n(aperçu — relancer avec --ecrire pour écrire)")
        return
    data = json.loads(POINTS.read_text(encoding="utf-8"))
    avant = len(data["features"])
    data["features"] = [f for f in data["features"] if f["properties"].get("theme") != "canyon"]
    data["features"].extend(feats)
    POINTS.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    TRACES.write_text(json.dumps({"type": "FeatureCollection", "features": traces},
                                 ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT points.geojson : {avant} -> {len(data['features'])} features (+{len(feats)} canyons)")
    print(f"ÉCRIT {TRACES.name} : {len(traces)} tracés")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main("--ecrire" in sys.argv)
