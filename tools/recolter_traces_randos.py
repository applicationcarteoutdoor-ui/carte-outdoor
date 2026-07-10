# -*- coding: utf-8 -*-
"""
Tracés des randonnées → data/randos.geojson (+ liens de recherche sur les
points « randonnee » de data/points.geojson).

PRINCIPE (extensible France entière) : il n'existe pas de relation OSM
route=hiking pour chaque voie normale (vérifié sur la Chartreuse : une seule
des 13, « Le sommet du Mont Granier »). Le tracé est donc calculé par
ROUTAGE sur le réseau de sentiers RÉEL d'OpenStreetMap :
  1. le DÉPART classique (details.depart du point) est résolu en coordonnées
     par une requête Overpass sur son nom (col, hameau, parking…) autour du
     sommet — table DEPARTS ci-dessous, une entrée par randonnée ;
  2. le réseau piéton (path/footway/track… + petites routes pénalisées) de la
     boîte départ-sommet est téléchargé (Overpass, `out geom`, cache) ;
  3. plus court chemin (Dijkstra) du départ au sommet, pondéré : sentiers
     favorisés, routes ×3, sac_scale alpin (T4+) fortement pénalisé,
     via ferrata et access=private/no EXCLUS ;
  4. simplification Douglas-Peucker ~10 m, contrôle des extrémités
     (< 300 m du départ ET du sommet, sinon tracé refusé).
HONNÊTETÉ : ni départ résolu, ni chemin trouvé, ni extrémités correctes
→ PAS de tracé pour cette randonnée (listée dans le bilan), rien d'inventé.
Chaque segment du tracé est un chemin cartographié dans OSM ; l'itinéraire
retenu est le plus court balisé, qui peut différer d'une variante éditoriale.

CAS PARTICULIER : quand une relation OSM route=hiking couvre EXACTEMENT la
randonnée (boucle du cirque de Saint-Même = « Sentier des Cascades »), sa
géométrie est reprise telle quelle (`relation` dans DEPARTS) — le routage
départ→sommet n'a pas de sens pour une boucle sans sommet. Contrôle : la
boucle doit passer à moins de 300 m du départ résolu.

Liens (volet 2) : chaque point rando reçoit properties.links = recherches
Google restreintes par site (komoot.fr, altituderando.com, alltrails.com),
même modèle que les sites d'escalade — pas d'URL profonde devinée.

Cache : tools/traces-randos-osm.json (gitignoré), une entrée par rando
(départ résolu + réseau), sauvegardé à chaque étape → reprise sur erreur.

Usage :  python tools/recolter_traces_randos.py            récolte + écriture
         python tools/recolter_traces_randos.py --dry-run  bilan sans écrire
"""

import json
import sys
import urllib.parse
from heapq import heappop, heappush
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import enrichissements as enr
from build_data import douglas_peucker

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
CIBLE_POINTS = RACINE / "data" / "points.geojson"
CIBLE_TRACES = RACINE / "data" / "randos.geojson"
CACHE = DOSSIER / "traces-randos-osm.json"

# Douglas-Peucker : ~10 m (0.0001° ≈ 11 m en latitude) ; coordonnées à 5
# décimales (~1 m) — même esprit que les GR de build_data.py, en plus fin.
TOLERANCE_DP = 0.0001
SEUIL_EXTREMITE_M = 300      # départ/sommet : le tracé doit coller au point
MARGE_BBOX = 0.025           # ° autour de la boîte départ-sommet (~2,5 km)

# ---------------------------------------------------------------------------
# Départs classiques : nom(s) OSM à résoudre autour du sommet (rayon en m).
# `parking` : prendre le amenity=parking le plus proche (cas des parkings
# sans nom propre). Une entrée par id de point — ids STABLES (jamais renommés).
# ---------------------------------------------------------------------------
DEPARTS = {
    "rando-0001": {"noms": ["Col de Porte"], "rayon": 4500},          # Chamechaude
    "rando-0002": {"noms": ["Oratoire du Charmant Som",               # Charmant Som
                            "Bergerie du Charmant Som",
                            "Auberge du Charmant Som",
                            "Habert de Charmant Som"], "rayon": 3000},
    # Cirque de Saint-Même : boucle des 4 cascades = relation OSM dédiée
    # (« Sentier des Cascades », position vérifiée dans le cirque) ; le point
    # Wikipédia est à ~100 m du parking → un routage donnerait 100 m de trait.
    "rando-0003": {"parking": True, "rayon": 3000, "relation": 15927441},
    "rando-0004": {"noms": ["Col du Coq"], "rayon": 4500},            # Dent de Crolles
    "rando-0005": {"noms": ["Perquelin"], "rayon": 6000},             # Dôme de Bellefont
    "rando-0006": {"noms": ["Col de la Charmette"], "rayon": 4000},   # Grande Sure
    "rando-0007": {"noms": ["La Correrie"], "rayon": 4000},           # Grand Som
    "rando-0008": {"noms": ["Perquelin"], "rayon": 5000},             # Lances de Malissard
    "rando-0009": {"noms": ["Col de Porte"], "rayon": 5000},          # La Pinéa
    "rando-0010": {"noms": ["La Plagne"], "rayon": 5000},             # Mont Granier
    "rando-0011": {"noms": ["Le Désert d'Entremont", "Le Désert"],    # Mont Outheran
                   "rayon": 6000},
    "rando-0012": {"noms": ["Col de Vence"], "rayon": 6000},          # Mont Saint-Eynard
                                                    # (col à 4,6 km du sommet)
    "rando-0013": {"noms": ["Saint-Pierre-d'Entremont"],              # Roche Veyrand
                   "rayon": 4500},
}

# Réseau praticable à pied : facteur multiplicatif du coût (1 = sentier).
# Les petites routes restent utilisables (sortie de village) mais pénalisées.
FACTEUR_HIGHWAY = {
    "path": 1.0, "footway": 1.0, "steps": 1.0, "bridleway": 1.1,
    "track": 1.15, "pedestrian": 2.0, "cycleway": 2.5, "living_street": 2.5,
    "service": 3.0, "residential": 3.0, "unclassified": 3.0, "tertiary": 4.0,
    "secondary": 6.0,
}
# sac_scale T4+ : pas un itinéraire de randonnée « voie normale » — très
# pénalisé (utilisé seulement s'il n'existe AUCUNE alternative).
FACTEUR_SAC = {"alpine_hiking": 8.0, "demanding_alpine_hiking": 20.0,
               "difficult_alpine_hiking": 30.0}

SITES_LIENS = [("🥾 Komoot", "komoot.fr"),
               ("⛰️ Altitude Rando", "altituderando.com"),
               ("🗺️ AllTrails", "alltrails.com")]


def _distance_m(lat1, lon1, lat2, lon2):
    a, b, c, d = map(radians, (lat1, lon1, lat2, lon2))
    h = sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def _charger_cache():
    if CACHE.exists():
        return json.loads(CACHE.read_text(encoding="utf-8"))
    return {}


def _sauver_cache(cache):
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1) Résolution du départ (nom OSM → coordonnées)
# ---------------------------------------------------------------------------

# Un nœud col/hameau est plus fiable qu'un arrêt de bus ou un bâtiment homonyme.
_PRIORITES = (("natural", "saddle"), ("mountain_pass", "yes"), ("place", None),
              ("amenity", "parking"), ("tourism", None))


def _prioriser(tags):
    for i, (cle, val) in enumerate(_PRIORITES):
        if cle in tags and (val is None or tags[cle] == val):
            return i
    return len(_PRIORITES)


def _centre(element):
    if "lat" in element:
        return element["lat"], element["lon"]
    c = element.get("center") or {}
    return c.get("lat"), c.get("lon")


def resoudre_depart(spec, lat_sommet, lon_sommet):
    """→ {"lat", "lon", "nom"} ou None. Requête Overpass autour du sommet."""
    rayon = spec["rayon"]
    if spec.get("parking"):
        clauses = f'nwr["amenity"="parking"](around:{rayon},{lat_sommet},{lon_sommet});'
    else:
        clauses = "".join(
            f'nwr["name"="{n}"](around:{rayon},{lat_sommet},{lon_sommet});'
            for n in spec["noms"])
    d = enr._overpass(f"[out:json][timeout:90];({clauses});out center tags;")
    candidats = []
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        tags = e.get("tags", {})
        if lat is None or tags.get("natural") == "peak":   # pas le sommet !
            continue
        candidats.append((_prioriser(tags),
                          _distance_m(lat, lon, lat_sommet, lon_sommet),
                          {"lat": lat, "lon": lon,
                           "nom": tags.get("name", "parking")}))
    if not candidats:
        return None
    candidats.sort(key=lambda c: (c[0], c[1]))
    return candidats[0][2]


# ---------------------------------------------------------------------------
# 2) Réseau piéton de la boîte départ-sommet
# ---------------------------------------------------------------------------

def telecharger_reseau(lat1, lon1, lat2, lon2):
    bbox = (f"{min(lat1, lat2) - MARGE_BBOX},{min(lon1, lon2) - MARGE_BBOX},"
            f"{max(lat1, lat2) + MARGE_BBOX},{max(lon1, lon2) + MARGE_BBOX}")
    d = enr._overpass(f'[out:json][timeout:180];way["highway"]({bbox});out geom;')
    # On ne garde que le praticable (allège le cache) ; tags utiles seulement.
    utiles = []
    for w in d.get("elements", []):
        tags = w.get("tags", {})
        if tags.get("highway") in FACTEUR_HIGHWAY and w.get("geometry"):
            utiles.append({
                "nodes": w.get("nodes", []),
                "geometry": [[p["lat"], p["lon"]] for p in w["geometry"]],
                "tags": {k: v for k, v in tags.items()
                         if k in ("highway", "sac_scale", "access", "foot",
                                  "via_ferrata_scale")},
            })
    return utiles


def _exclu(tags):
    if tags.get("via_ferrata_scale"):                     # jamais une VF !
        return True
    if tags.get("foot") in ("no", "private"):
        return True
    if tags.get("access") in ("no", "private") and \
            tags.get("foot") not in ("yes", "designated", "permissive"):
        return True
    return False


def construire_graphe(ways):
    """→ (arcs : nœud → [(voisin, coût)], coords : nœud → (lat, lon))."""
    arcs, coords = {}, {}
    for w in ways:
        tags = w["tags"]
        if _exclu(tags):
            continue
        facteur = FACTEUR_HIGHWAY[tags["highway"]] * \
            FACTEUR_SAC.get(tags.get("sac_scale"), 1.0)
        noeuds, geom = w["nodes"], w["geometry"]
        if len(noeuds) != len(geom):                      # géométrie tronquée
            continue
        for n, (lat, lon) in zip(noeuds, geom):
            coords[n] = (lat, lon)
        for a, b in zip(noeuds, noeuds[1:]):
            d = _distance_m(*coords[a], *coords[b]) * facteur
            arcs.setdefault(a, []).append((b, d))
            arcs.setdefault(b, []).append((a, d))
    return arcs, coords


def noeud_le_plus_proche(coords, arcs, lat, lon, maxi):
    meilleur, dist = None, maxi
    for n, (la, lo) in coords.items():
        if n not in arcs:
            continue
        d = _distance_m(la, lo, lat, lon)
        if d < dist:
            meilleur, dist = n, d
    return meilleur, dist


def dijkstra(arcs, depart, arrivee):
    dists, precedes, file_ = {depart: 0.0}, {}, [(0.0, depart)]
    while file_:
        d, n = heappop(file_)
        if n == arrivee:
            break
        if d > dists.get(n, float("inf")):
            continue
        for voisin, cout in arcs.get(n, []):
            nd = d + cout
            if nd < dists.get(voisin, float("inf")):
                dists[voisin], precedes[voisin] = nd, n
                heappush(file_, (nd, voisin))
    if arrivee not in dists:
        return None
    chemin, n = [arrivee], arrivee
    while n != depart:
        n = precedes[n]
        chemin.append(n)
    return chemin[::-1]


# ---------------------------------------------------------------------------
# 2 bis) Relation OSM reprise telle quelle (boucles balisées dédiées)
# ---------------------------------------------------------------------------

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


def tracer_relation(entree, id_relation, depart, pid, nom):
    """→ (features, longueur_km, points_avant, points_après). La géométrie
    de la relation est reprise telle quelle (chaînes fusionnées + DP)."""
    if "relation_geom" not in entree:
        d = enr._overpass(f"[out:json][timeout:90];relation({id_relation});out geom;")
        segments = []
        for e in d.get("elements", []):
            for m in e.get("members", []):
                if m.get("type") == "way" and m.get("geometry"):
                    segments.append([[p["lat"], p["lon"]] for p in m["geometry"]])
        entree["relation_geom"] = segments
    chaines = _assembler(entree["relation_geom"])
    if not chaines:
        return None, "relation OSM sans géométrie", 0, 0, 0
    # La boucle doit passer près du départ résolu (sinon mauvaise relation).
    plus_pres = min(_distance_m(lat, lon, depart["lat"], depart["lon"])
                    for c in chaines for lat, lon in c)
    if plus_pres > SEUIL_EXTREMITE_M:
        return None, f"relation à {plus_pres:.0f} m du départ", 0, 0, 0
    longueur = sum(_distance_m(*a, *b)
                   for c in chaines for a, b in zip(c, c[1:]))
    avant = sum(len(c) for c in chaines)
    features = []
    for c in chaines:
        simplifie = douglas_peucker([(lon, lat) for lat, lon in c], TOLERANCE_DP)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString",
                         "coordinates": [[round(x, 5), round(y, 5)]
                                         for x, y in simplifie]},
            "properties": {"rando": pid, "name": nom, "source": "OSM"},
        })
    apres = sum(len(f["geometry"]["coordinates"]) for f in features)
    print(f"  {pid} {nom} : boucle balisée (relation {id_relation}), "
          f"{longueur / 1000:.1f} km, à {plus_pres:.0f} m du départ "
          f"« {depart['nom']} », {avant} → {apres} points "
          f"({len(features)} morceau(x))")
    return features, "", longueur / 1000, avant, apres


# ---------------------------------------------------------------------------
# 3) Tracé d'une randonnée
# ---------------------------------------------------------------------------

def tracer(rando, cache):
    """→ (features | None, motif, longueur_km, nb_points_avant, nb_apres)."""
    pid = rando["properties"]["id"]
    nom = rando["properties"]["name"]
    lon_s, lat_s = rando["geometry"]["coordinates"][:2]
    spec = DEPARTS.get(pid)
    if not spec:
        return None, "pas d'entrée DEPARTS (nouvelle randonnée ?)", 0, 0, 0

    entree = cache.setdefault(pid, {})
    if "depart" not in entree:
        entree["depart"] = resoudre_depart(spec, lat_s, lon_s)
        _sauver_cache(cache)
    depart = entree["depart"]
    if not depart:
        return None, "départ introuvable dans OSM", 0, 0, 0

    if spec.get("relation"):                  # boucle balisée dédiée
        resultat = tracer_relation(entree, spec["relation"], depart, pid, nom)
        _sauver_cache(cache)
        return resultat

    if "reseau" not in entree:
        entree["reseau"] = telecharger_reseau(depart["lat"], depart["lon"],
                                              lat_s, lon_s)
        _sauver_cache(cache)
    arcs, coords = construire_graphe(entree["reseau"])
    if not arcs:
        return None, "aucun chemin praticable dans la zone", 0, 0, 0

    n_dep, d_dep = noeud_le_plus_proche(coords, arcs, depart["lat"],
                                        depart["lon"], SEUIL_EXTREMITE_M)
    n_som, d_som = noeud_le_plus_proche(coords, arcs, lat_s, lon_s,
                                        SEUIL_EXTREMITE_M)
    if n_dep is None:
        return None, f"aucun sentier à moins de {SEUIL_EXTREMITE_M} m du départ", 0, 0, 0
    if n_som is None:
        return None, f"aucun sentier à moins de {SEUIL_EXTREMITE_M} m du sommet", 0, 0, 0

    chemin = dijkstra(arcs, n_dep, n_som)
    if not chemin:
        return None, "départ et sommet non reliés par le réseau OSM", 0, 0, 0

    points = [coords[n] for n in chemin]                  # (lat, lon)
    longueur = sum(_distance_m(*a, *b) for a, b in zip(points, points[1:]))
    lonlat = [(lon, lat) for lat, lon in points]
    simplifie = douglas_peucker(lonlat, TOLERANCE_DP)
    feature = {
        "type": "Feature",
        "geometry": {"type": "LineString",
                     "coordinates": [[round(x, 5), round(y, 5)]
                                     for x, y in simplifie]},
        "properties": {"rando": pid, "name": nom, "source": "OSM"},
    }
    print(f"  {pid} {nom} : {longueur / 1000:.1f} km, départ « {depart['nom']} » "
          f"(bouts à {d_dep:.0f} m / {d_som:.0f} m), "
          f"{len(points)} → {len(simplifie)} points")
    return [feature], "", longueur / 1000, len(points), len(simplifie)


# ---------------------------------------------------------------------------
# 4) Liens de recherche (volet 2) — modèle des sites d'escalade
# ---------------------------------------------------------------------------

def liens_recherche(nom, massif):
    contexte = f"{nom} {massif}".strip()
    return [{"label": label,
             "url": "https://www.google.com/search?q="
                    + urllib.parse.quote(f"{contexte} site:{site}", safe="")}
            for label, site in SITES_LIENS]


# ---------------------------------------------------------------------------
# Exécution
# ---------------------------------------------------------------------------

def main(dry_run=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    collection = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
    randos = [f for f in collection["features"]
              if f["properties"].get("theme") == "randonnee"]
    randos.sort(key=lambda f: f["properties"]["id"])
    print(f"{len(randos)} randonnées dans points.geojson")

    cache = _charger_cache()
    features, absents, traces = [], [], 0
    for r in randos:
        try:
            morceaux, motif, *_ = tracer(r, cache)
        except Exception as e:                            # Overpass épuisé…
            morceaux, motif = None, f"erreur : {e}"
        if morceaux:
            features.extend(morceaux)
            traces += 1
        else:
            absents.append((r["properties"]["id"], r["properties"]["name"], motif))
            print(f"  {r['properties']['id']} {r['properties']['name']} : "
                  f"SANS TRACÉ — {motif}")

    # Liens de recherche sur chaque point rando (remplace un éventuel ancien).
    for r in randos:
        r["properties"]["links"] = liens_recherche(
            r["properties"]["name"],
            r["properties"].get("details", {}).get("massif", ""))

    print(f"\nBilan : {traces} tracés / {len(randos)} randonnées"
          + (f", absents : {[a[0] for a in absents]}" if absents else ""))
    if dry_run:
        print("(--dry-run : rien n'a été écrit)")
        return 0

    CIBLE_TRACES.write_text(
        json.dumps({"type": "FeatureCollection", "features": features},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"data/randos.geojson : {CIBLE_TRACES.stat().st_size / 1024:.0f} Ko")
    CIBLE_POINTS.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print("points.geojson : liens de recherche posés sur les points rando")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
