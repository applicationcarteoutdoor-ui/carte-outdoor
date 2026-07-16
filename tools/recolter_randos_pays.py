# -*- coding: utf-8 -*-
"""
Randonnées ICONIQUES Suisse/Italie/Espagne : depuis la liste éditoriale
tools/randos-pays.json (vérifiée à la main / par recherche web), calcule le
TRACÉ réel sur le réseau de sentiers OSM (même méthode que la France :
routage Dijkstra départ→objectif, via ferrata et privé exclus, simplification
Douglas-Peucker, contrôle des extrémités < 300 m) puis les stats :
distance mesurée sur le tracé (aller-retour), D+ estimé (API open-meteo,
échantillonnage ~300 m), durée = valeur éditoriale (sources web).

HONNÊTETÉ : objectif introuvable/ambigu, départ irrésolu, chemin absent ou
extrémités trop loin → PAS de tracé (listé au bilan), rien d'inventé.

Résolution de l'OBJECTIF : d'abord parmi les points du pays
(data/<iso>/points.geojson : lacs, refuges, cascades — noms déjà vérifiés),
sinon Overpass par nom dans l'aire du pays (unique, sinon ambigu → rejet).
Résolution du DÉPART : Overpass par nom autour de l'objectif (rayon 12 km),
priorité col > lieu-dit > parking > tourisme (modèle France).

Sorties : tools/randos-pays-resolues.json (points + tracés, consommé par
construire_pays.py) — les fichiers data/ ne sont PAS écrits ici.
Cache par rando : tools/traces-pays-cache/<iso>-<n>.json (gitignoré).

Lancer :  python tools/recolter_randos_pays.py [ch|it|es] [--dry-run]
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
LISTE = DOSSIER / "randos-pays.json"
SORTIE = DOSSIER / "randos-pays-resolues.json"
CACHE_DIR = DOSSIER / "traces-pays-cache"

UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle ; contact bidband4@gmail.com)"}
# Miroirs publics : la récolte sanitaires monopolise overpass-api.de en
# parallèle ; kumi.systems pendait jusqu'au timeout (vécu v67). L'instance
# suisse ne couvre QUE la Suisse — parfaite pour le lot ch.
OVERPASS_PAR_PAYS = {
    "ch": "https://overpass.osm.ch/api/interpreter",
    "it": "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "es": "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
}
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"

ISO = {"ch": "CH", "it": "IT", "es": "ES"}
TOLERANCE_DP = 0.0001          # ~10 m
SEUIL_EXTREMITE_M = 300
MARGE_BBOX = 0.025
RAYON_DEPART = 12000           # m autour de l'objectif

FACTEUR_HIGHWAY = {
    "path": 1.0, "footway": 1.0, "steps": 1.0, "bridleway": 1.1,
    "track": 1.15, "pedestrian": 2.0, "cycleway": 2.5, "living_street": 2.5,
    "service": 3.0, "residential": 3.0, "unclassified": 3.0, "tertiary": 4.0,
    "secondary": 6.0,
}
FACTEUR_SAC = {"alpine_hiking": 8.0, "demanding_alpine_hiking": 20.0,
               "difficult_alpine_hiking": 30.0}

_PRIORITES = (("natural", "saddle"), ("mountain_pass", "yes"), ("place", None),
              ("amenity", "parking"), ("railway", "station"),
              ("aerialway", None), ("tourism", None))


def _overpass(requete):
    donnees = urllib.parse.urlencode({"data": requete}).encode()
    for attente in (0, 20, 60, 120):
        if attente:
            print(f"    (Overpass occupé, pause {attente} s…)", flush=True)
            time.sleep(attente)
        try:
            with urllib.request.urlopen(
                    urllib.request.Request(OVERPASS, data=donnees, headers=UA),
                    timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Overpass surchargé")


def _distance_m(lat1, lon1, lat2, lon2):
    a, b, c, d = map(radians, (lat1, lon1, lat2, lon2))
    h = sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def douglas_peucker(points, tolerance):
    if len(points) < 3:
        return points
    garder = [False] * len(points)
    garder[0] = garder[-1] = True
    pile = [(0, len(points) - 1)]
    while pile:
        debut, fin = pile.pop()
        x1, y1 = points[debut]
        x2, y2 = points[fin]
        dx, dy = x2 - x1, y2 - y1
        norme2 = dx * dx + dy * dy
        dist_max, indice = 0.0, -1
        for i in range(debut + 1, fin):
            x0, y0 = points[i]
            if norme2 == 0:
                d2 = (x0 - x1) ** 2 + (y0 - y1) ** 2
            else:
                t = max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / norme2))
                d2 = (x0 - x1 - t * dx) ** 2 + (y0 - y1 - t * dy) ** 2
            if d2 > dist_max:
                dist_max, indice = d2, i
        if dist_max > tolerance * tolerance:
            garder[indice] = True
            pile.append((debut, indice))
            pile.append((indice, fin))
    return [p for p, g in zip(points, garder) if g]


def _centre(e):
    if "lat" in e:
        return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")


def _prioriser(tags):
    for i, (cle, val) in enumerate(_PRIORITES):
        if cle in tags and (val is None or tags[cle] == val):
            return i
    return len(_PRIORITES)


# ---------------------------------------------------------------------------
# Résolutions
# ---------------------------------------------------------------------------

def points_du_pays(iso):
    f = RACINE / "data" / iso / "points.geojson"
    if not f.exists():
        return []
    d = json.loads(f.read_text(encoding="utf-8"))
    return [{"nom": p["properties"]["name"], "lat": p["geometry"]["coordinates"][1],
             "lon": p["geometry"]["coordinates"][0], "theme": p["properties"]["theme"]}
            for p in d["features"]]


def _lieu_majoritaire(sites, rayon_m=5000, seuil=0.7):
    """Un toponyme donne souvent PLUSIEURS objets OSM au même endroit (gare +
    hameau + restaurant « Alpiglen »…). Si ≥ 70 % des homonymes se groupent
    en un seul lieu, ce lieu est retenu ; sinon vraiment ambigu → None."""
    meilleur = None
    for s in sites:
        groupe = [x for x in sites
                  if _distance_m(s[0], s[1], x[0], x[1]) < rayon_m]
        if meilleur is None or len(groupe) > len(meilleur):
            meilleur = groupe
    if len(meilleur) >= seuil * len(sites):
        return meilleur[0]
    return None


# Tag OSM attendu selon le type d'objectif éditorial : sert à départager les
# homonymes (le « Monte Vettore » sommet bat la rue « Monte Vettore »).
_TAG_TYPE = {
    "sommet": lambda t: t.get("natural") == "peak",
    "lac": lambda t: t.get("natural") == "water" or t.get("water"),
    "refuge": lambda t: t.get("tourism") in ("alpine_hut", "wilderness_hut"),
}


def _regex_nom(nom):
    """Regex Overpass ancrée, insensible à la casse (« la Masieta »…).
    Antislashes doublés : la chaîne QL "…" consomme un niveau d'échappement."""
    return ("^" + re.escape(nom.strip()) + "$").replace("\\", "\\\\")


def _sites_par_nom(iso, nom):
    """Homonymes du toponyme dans tout le pays -> [(lat, lon, tags)]."""
    d = _overpass(f'[out:json][timeout:120];'
                  f'area["ISO3166-1"="{ISO[iso]}"]["admin_level"="2"]->.p;'
                  f'(nwr["name"~"{_regex_nom(nom)}",i](area.p););out center tags;')
    sites = []
    for e in d.get("elements", []):
        if e.get("type") == "relation" and (e.get("tags", {}).get("type") != "multipolygon"):
            continue
        lat, lon = _centre(e)
        if lat is not None:
            sites.append((lat, lon, e.get("tags", {})))
    return sites


def resoudre_objectif(iso, noms, pts_pays, obj_type=None, noms_dep=()):
    """Coordonnées de l'objectif : points du pays d'abord, sinon Overpass pays
    entier. Homonymes départagés dans l'ordre : tag du type attendu -> lieu
    majoritaire -> PAIRE avec le départ (seul l'homonyme qui a le bon départ
    à moins de 12 km est gardé), sinon rejet honnête."""
    for nom in noms:
        exacts = [(p["lat"], p["lon"]) for p in pts_pays
                  if p["nom"].strip().lower() == nom.strip().lower()]
        lieu = _lieu_majoritaire(exacts) if exacts else None
        if lieu:
            return {"lat": lieu[0], "lon": lieu[1], "source": "points"}
    deps = None
    for nom in noms:
        sites = _sites_par_nom(iso, nom)
        if not sites:
            continue
        du_type = _TAG_TYPE.get(obj_type)
        types = [s for s in sites if du_type and du_type(s[2])]
        lieu = _lieu_majoritaire([(s[0], s[1]) for s in (types or sites)])
        if lieu:
            return {"lat": lieu[0], "lon": lieu[1], "source": "osm"}
        # dernier recours : l'homonyme dont le DÉPART annoncé est voisin
        if deps is None:
            deps = []
            for nd in noms_dep:
                if nd:
                    deps.extend(_sites_par_nom(iso, nd))
        apparies = [s for s in sites
                    if any(_distance_m(s[0], s[1], d[0], d[1]) < RAYON_DEPART
                           for d in deps)]
        lieu = _lieu_majoritaire([(s[0], s[1]) for s in apparies]) if apparies else None
        if lieu:
            return {"lat": lieu[0], "lon": lieu[1], "source": "osm+depart"}
        print(f"    objectif ambigu ({len(sites)} homonymes) : {nom}", flush=True)
    return None


def resoudre_depart(noms, lat_obj, lon_obj):
    clauses = "".join(
        f'nwr["name"~"{_regex_nom(n)}",i](around:{RAYON_DEPART},{lat_obj},{lon_obj});'
        for n in noms if n)
    if not clauses:
        return None
    d = _overpass(f"[out:json][timeout:90];({clauses});out center tags;")
    candidats = []
    for e in d.get("elements", []):
        if e.get("type") == "relation":
            continue
        lat, lon = _centre(e)
        tags = e.get("tags", {})
        if lat is None or tags.get("natural") == "peak":
            continue
        candidats.append((_prioriser(tags), _distance_m(lat, lon, lat_obj, lon_obj),
                          {"lat": lat, "lon": lon, "nom": tags.get("name", "départ")}))
    if not candidats:
        return None
    candidats.sort(key=lambda c: (c[0], c[1]))
    return candidats[0][2]


# ---------------------------------------------------------------------------
# Réseau + routage (modèle France, recolter_traces_randos.py)
# ---------------------------------------------------------------------------

def telecharger_reseau(lat1, lon1, lat2, lon2, marge=MARGE_BBOX):
    bbox = (f"{min(lat1, lat2) - marge},{min(lon1, lon2) - marge},"
            f"{max(lat1, lat2) + marge},{max(lon1, lon2) + marge}")
    d = _overpass(f'[out:json][timeout:180];way["highway"]({bbox});out geom;')
    utiles = []
    for w in d.get("elements", []):
        tags = w.get("tags", {})
        if tags.get("highway") in FACTEUR_HIGHWAY and w.get("geometry"):
            # `out geom` émet parfois null pour un nœud hors bbox : on filtre
            # les PAIRES (nœud, sommet) pour garder l'alignement des listes.
            paires = [(n, [p["lat"], p["lon"]])
                      for n, p in zip(w.get("nodes", []), w["geometry"]) if p]
            if len(paires) < 2:
                continue
            utiles.append({
                "nodes": [n for n, _ in paires],
                "geometry": [g for _, g in paires],
                "tags": {k: v for k, v in tags.items()
                         if k in ("highway", "sac_scale", "access", "foot",
                                  "via_ferrata_scale")},
            })
    return utiles


def _exclu(tags):
    if tags.get("via_ferrata_scale"):
        return True
    if tags.get("foot") in ("no", "private"):
        return True
    if tags.get("access") in ("no", "private") and \
            tags.get("foot") not in ("yes", "designated", "permissive"):
        return True
    return False


def construire_graphe(ways):
    arcs, coords = {}, {}
    for w in ways:
        tags = w["tags"]
        if _exclu(tags):
            continue
        facteur = FACTEUR_HIGHWAY[tags["highway"]] * \
            FACTEUR_SAC.get(tags.get("sac_scale"), 1.0)
        noeuds, geom = w["nodes"], w["geometry"]
        if len(noeuds) != len(geom):
            continue
        for n, (lat, lon) in zip(noeuds, geom):
            coords[n] = (lat, lon)
        for a, b in zip(noeuds, noeuds[1:]):
            d = _distance_m(*coords[a], *coords[b]) * facteur
            arcs.setdefault(a, []).append((b, d))
            arcs.setdefault(b, []).append((a, d))
    return arcs, coords


def noeuds_proches(coords, arcs, lat, lon, maxi, cap=40):
    cands = []
    for n, (la, lo) in coords.items():
        if n not in arcs:
            continue
        d = _distance_m(la, lo, lat, lon)
        if d < maxi:
            cands.append((d, n))
    cands.sort()
    return cands[:cap]


def dijkstra_vers(arcs, depart, cibles):
    dists, precedes, file_ = {depart: 0.0}, {}, [(0.0, depart)]
    atteint = None
    while file_:
        d, n = heappop(file_)
        if n in cibles:
            atteint = n
            break
        if d > dists.get(n, float("inf")):
            continue
        for voisin, cout in arcs.get(n, []):
            nd = d + cout
            if nd < dists.get(voisin, float("inf")):
                dists[voisin], precedes[voisin] = nd, n
                heappush(file_, (nd, voisin))
    if atteint is None:
        return None
    chemin, n = [atteint], atteint
    while n != depart:
        n = precedes[n]
        chemin.append(n)
    return chemin[::-1]


def _assembler(segments):
    """Fusionne les ways d'une relation par extrémités communes → chaînes."""
    segs = [list(map(tuple, s)) for s in segments if len(s) >= 2]
    fusion = True
    while fusion:
        fusion = False
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                a, b = segs[i], segs[j]
                if a[-1] == b[0]:
                    segs[i] = a + b[1:]
                elif a[-1] == b[-1]:
                    segs[i] = a + b[-2::-1]
                elif a[0] == b[-1]:
                    segs[i] = b + a[1:]
                elif a[0] == b[0]:
                    segs[i] = b[::-1] + a[1:]
                else:
                    continue
                segs.pop(j)
                fusion = True
                break
            if fusion:
                break
    return segs


def tracer_relation(e):
    """Boucle balisée OSM (`relationOsm` dans la liste éditoriale) : géométrie
    reprise telle quelle (chaînes fusionnées + DP) — le routage départ→objectif
    n'a pas de sens pour une boucle. → (entree_partielle | None, motif)."""
    d = _overpass(f'[out:json][timeout:120];relation({e["relationOsm"]});out geom;')
    rel_tags, segments = {}, []
    for el in d.get("elements", []):
        rel_tags = el.get("tags", {})
        for m in el.get("members", []):
            if m.get("type") == "way" and m.get("geometry"):
                segments.append([[p["lat"], p["lon"]] for p in m["geometry"] if p])
    chaines = [c for c in _assembler(segments) if len(c) >= 2]
    if not chaines:
        return None, "relation OSM sans géométrie"
    longueur = sum(_distance_m(*a, *b) for c in chaines for a, b in zip(c, c[1:])) / 1000
    principale = max(chaines, key=len)
    boucle = rel_tags.get("roundtrip") == "yes" or \
        _distance_m(*principale[0], *principale[-1]) < 500
    # centre de la boucle → résolution du départ (facultative, fiche seulement)
    clat = sum(p[0] for p in principale) / len(principale)
    clon = sum(p[1] for p in principale) / len(principale)
    depart = resoudre_depart([e.get("departNom"), e.get("departAlt")], clat, clon)
    if depart:
        pt = min((p for c in chaines for p in c),
                 key=lambda p: _distance_m(p[0], p[1], depart["lat"], depart["lon"]))
    else:
        depart = {"nom": e.get("departNom", "départ"), "lat": None, "lon": None}
        pt = principale[0]
    dplus = denivele_positif(principale)
    return {
        "rando": e,
        "depart": depart,
        "objectif": {"lat": pt[0], "lon": pt[1], "source": f"relation {e['relationOsm']}"},
        "traces": [[[round(la, 5), round(lo, 5)]
                    for la, lo in douglas_peucker(c, TOLERANCE_DP)] for c in chaines],
        "distance_aller_km": round(longueur, 1),
        "denivele_m": dplus,
        "boucle": boucle,
    }, ""


def tracer(depart, objectif, obj_type=None):
    """→ liste [lat, lon] simplifiée, ou None (honnête)."""
    ways = telecharger_reseau(depart["lat"], depart["lon"], objectif["lat"], objectif["lon"])
    arcs, coords = construire_graphe(ways)
    if not arcs:
        return None
    # Les points « lac » sont recentrés DANS l'eau et les « sites » (gorges,
    # sources, cirques) au cœur de l'objet : le sentier passe à distance —
    # tolérance d'arrivée élargie (le tracé s'arrête au plus près).
    seuil_arrivee = {"lac": 900, "site": 600}.get(obj_type, SEUIL_EXTREMITE_M)
    dep_cands = noeuds_proches(coords, arcs, depart["lat"], depart["lon"], SEUIL_EXTREMITE_M)
    arr_cands = noeuds_proches(coords, arcs, objectif["lat"], objectif["lon"], seuil_arrivee)
    if not dep_cands or not arr_cands:
        return None
    cibles = {n for _, n in arr_cands}
    for _, dep in dep_cands:
        chemin = dijkstra_vers(arcs, dep, cibles)
        if chemin:
            pts = [coords[n] for n in chemin]
            return douglas_peucker(pts, TOLERANCE_DP)
    return None


# ---------------------------------------------------------------------------
# Stats : distance mesurée, D+ estimé (open-meteo), durée éditoriale
# ---------------------------------------------------------------------------

def longueur_km(pts):
    return sum(_distance_m(*a, *b) for a, b in zip(pts, pts[1:])) / 1000.0


def echantillonner(pts, pas_m=300.0):
    """Points tous les ~300 m le long du tracé (pour le profil altimétrique)."""
    ech, acc = [pts[0]], 0.0
    for a, b in zip(pts, pts[1:]):
        acc += _distance_m(*a, *b)
        if acc >= pas_m:
            ech.append(b)
            acc = 0.0
    if ech[-1] != pts[-1]:
        ech.append(pts[-1])
    return ech


def denivele_positif(pts):
    """D+ (m) via l'API d'altitude open-meteo (100 points max par requête).
    → int ou None si l'API échoue (le champ est alors simplement absent)."""
    ech = echantillonner(pts)
    alts = []
    try:
        for i in range(0, len(ech), 100):
            lot = ech[i:i + 100]
            q = urllib.parse.urlencode({
                "latitude": ",".join(f"{p[0]:.5f}" for p in lot),
                "longitude": ",".join(f"{p[1]:.5f}" for p in lot),
            })
            with urllib.request.urlopen(
                    urllib.request.Request(
                        f"https://api.open-meteo.com/v1/elevation?{q}", headers=UA),
                    timeout=60) as r:
                alts.extend(json.load(r).get("elevation", []))
            time.sleep(1)
    except Exception as e:
        print(f"    (altimétrie indisponible : {e})", flush=True)
        return None
    if len(alts) != len(ech):
        return None
    # lissage simple : on n'additionne que les montées > 2 m entre échantillons
    dplus = sum(max(0.0, b - a) for a, b in zip(alts, alts[1:]) if b - a > 2)
    return int(round(dplus / 10.0) * 10)


# ---------------------------------------------------------------------------
# Pilote
# ---------------------------------------------------------------------------

def traiter_pays(iso, entrees, dry_run):
    pts_pays = points_du_pays(iso)
    CACHE_DIR.mkdir(exist_ok=True)
    resolues, echecs = [], []
    for n, e in enumerate(entrees, start=1):
        cle = f"{iso}-{n:02d}"
        shard = CACHE_DIR / f"{cle}.json"
        if shard.exists():
            entree = json.loads(shard.read_text(encoding="utf-8"))
            if entree.get("trace"):
                resolues.append(entree)
                continue
            if entree.get("echec") and not entree.get("retenter"):
                echecs.append((e["nom"], entree["echec"]))
                continue
        print(f"  [{cle}] {e['nom']}", flush=True)
        if dry_run:
            continue
        if e.get("relationOsm"):
            entree, motif = tracer_relation(e)
            if entree:
                entree["iso"] = iso
                shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
                resolues.append(entree)
                print(f"    ✓ {'boucle' if entree['boucle'] else 'tracé'} balisée "
                      f"(relation {e['relationOsm']}) {entree['distance_aller_km']} km, "
                      f"D+ {entree['denivele_m'] if entree['denivele_m'] is not None else '—'} m",
                      flush=True)
            else:
                entree = {"rando": e, "echec": motif, "retenter": True}
                shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
                echecs.append((e["nom"], motif))
            time.sleep(2)
            continue
        noms_obj = [e.get("nomLocal") or "", e["objectifNom"]]
        noms_obj = [x for x in dict.fromkeys(noms_obj) if x]
        objectif = resoudre_objectif(iso, [e["objectifNom"]] + noms_obj, pts_pays,
                                     e.get("objectifType"),
                                     (e.get("departNom"), e.get("departAlt")))
        if not objectif:
            entree = {"rando": e, "echec": "objectif introuvable/ambigu"}
            shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
            echecs.append((e["nom"], entree["echec"]))
            continue
        depart = resoudre_depart([e.get("departNom"), e.get("departAlt")],
                                 objectif["lat"], objectif["lon"])
        if not depart:
            entree = {"rando": e, "echec": f"départ introuvable ({e.get('departNom')})"}
            shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
            echecs.append((e["nom"], entree["echec"]))
            continue
        # Départ = objectif (station supérieure au bord du lac…) : pas de routage
        if _distance_m(depart["lat"], depart["lon"], objectif["lat"], objectif["lon"]) < 400:
            entree = {"rando": e, "echec": "départ confondu avec l'objectif"}
            shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
            echecs.append((e["nom"], entree["echec"]))
            continue
        try:
            pts = tracer(depart, objectif, e.get("objectifType"))
        except Exception as exc:
            print(f"    ! réseau/routage : {exc}", flush=True)
            pts = None
        if not pts:
            entree = {"rando": e, "echec": "pas de chemin balisé trouvé", "retenter": True}
            shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
            echecs.append((e["nom"], entree["echec"]))
            continue
        dist_aller = longueur_km(pts)
        dplus = denivele_positif(pts)
        entree = {
            "rando": e, "iso": iso,
            "depart": depart, "objectif": objectif,
            "trace": [[round(la, 5), round(lo, 5)] for la, lo in pts],
            "distance_aller_km": round(dist_aller, 1),
            "denivele_m": dplus,
        }
        shard.write_text(json.dumps(entree, ensure_ascii=False), encoding="utf-8")
        resolues.append(entree)
        print(f"    ✓ tracé {dist_aller:.1f} km (aller), départ « {depart['nom']} », "
              f"D+ {dplus if dplus is not None else '—'} m", flush=True)
        time.sleep(2)
    return resolues, echecs


def main():
    dry_run = "--dry-run" in sys.argv
    cibles = [a for a in sys.argv[1:] if a in ISO] or list(ISO)
    liste = json.loads(LISTE.read_text(encoding="utf-8"))
    final = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else {}
    for iso in cibles:
        global OVERPASS
        OVERPASS = OVERPASS_PAR_PAYS.get(iso, OVERPASS)
        entrees = liste.get(iso, [])
        print(f"== {iso}: {len(entrees)} randonnées éditoriales ({OVERPASS.split('/')[2]}) ==",
              flush=True)
        resolues, echecs = traiter_pays(iso, entrees, dry_run)
        final[iso] = resolues
        print(f"{iso}: {len(resolues)} tracées, {len(echecs)} échecs", flush=True)
        for nom, raison in echecs:
            print(f"   ✗ {nom} — {raison}", flush=True)
    if not dry_run:
        SORTIE.write_text(json.dumps(final, ensure_ascii=False), encoding="utf-8")
        print(f"-> {SORTIE.name}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
