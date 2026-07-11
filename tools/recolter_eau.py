# -*- coding: utf-8 -*-
"""
Récolte des POINTS D'EAU de France métropolitaine + Corse depuis
OpenStreetMap (API Overpass) -> data/eau.geojson.

Couche utilitaire chargée à la demande par l'application (modèle :
data/toilettes.geojson) : fichier séparé, non pré-caché.

Périmètre (feu vert utilisateur : « eau potable + sources ») :
  - amenity=drinking_water   (fontaines / points d'eau potable — le cœur)
  - man_made=water_tap       (robinets)
  - amenity=water_point      (points de remplissage d'eau)
  - natural=spring           (sources naturelles — montagne)
  - amenity=fountain UNIQUEMENT si drinking_water=yes (fontaines potables)
  access=private / access=no écartés.

Méthode :
  - Overpass, POST, France découpée en tuiles de 3° AVEC filtre d'aire France
    (area["ISO3166-1"="FR"]) : exclut Suisse/Italie/Espagne/… qui débordent
    des bornes métropole (vérifié : ~2x moins d'éléments sur la frontière
    du Mont-Blanc).
  - Rate-limit fort (429/504) : retries longs 20/60/120 s ; si une tuile 3°
    échoue quand même, elle est DÉCOUPÉE en quatre et retentée (jusqu'à
    ~0,75°). Cache par tuile dans tools/eau-tuiles.json (gitignoré) sauvegardé
    au fil de l'eau -> reprise sur relance.
  - Dédoublonnage : par id OSM (recouvrements de tuiles) puis coords arrondies
    (~11 m) pour les doublons nœud/way d'un même point.
  - Ids stables : registre tools/eau-registre.json (clé OSM -> eau-00001…),
    jamais renuméroté sur relance.
  - Contrôle qualité avant écriture : bornes France+Corse (lat 41–51.5,
    lon -5.5–10), UTF-8, pas de HTML brut.

Lancer :  python tools/recolter_eau.py
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
CACHE_TUILES = DOSSIER / "eau-tuiles.json"       # {clef_bbox: [elements] | {"split": true}}
REGISTRE = DOSSIER / "eau-registre.json"          # {clefOSM: "eau-00001"}
HEARTBEAT = DOSSIER / "eau-status.json"           # suivi d'avancement (poll)
CIBLE = RACINE / "data" / "eau.geojson"

UA = {"User-Agent": "CarteOutdoor/1.0 (application personnelle de cartographie outdoor)"}
OVERPASS = "https://overpass-api.de/api/interpreter"

LAT_MIN, LAT_MAX = 41.0, 51.5
LON_MIN, LON_MAX = -5.5, 10.0
PAS = 3.0            # tuile initiale
TUILE_MIN = 0.75     # on ne descend pas plus bas en cas d'échec répété

# Sélecteurs OSM (un seul bloc, filtré par l'aire France .fr)
def _selecteurs(bbox):
    tags = [
        '["amenity"="drinking_water"]',
        '["man_made"="water_tap"]',
        '["amenity"="water_point"]',
        '["natural"="spring"]',
        '["amenity"="fountain"]["drinking_water"="yes"]',
    ]
    lignes = []
    for t in tags:
        lignes.append(f'node{t}(area.fr)({bbox});')
        lignes.append(f'way{t}(area.fr)({bbox});')
    return "".join(lignes)


def _requete(bbox):
    return ('[out:json][timeout:280];'
            'area["ISO3166-1"="FR"]["admin_level"="2"]->.fr;'
            '(' + _selecteurs(bbox) + ');out center;')


def _overpass(requete):
    donnees = urllib.parse.urlencode({"data": requete}).encode()
    for attente in (0, 20, 60, 120):
        if attente:
            print(f"    (Overpass occupé, pause {attente} s…)", flush=True)
            time.sleep(attente)
        req = urllib.request.Request(OVERPASS, data=donnees, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    (réseau : {e}) ", flush=True)
    raise RuntimeError("Overpass surchargé (429/504/timeout persistant)")


def _clef(w, s, e, n):
    return f"{s:.4f},{w:.4f},{n:.4f},{e:.4f}"  # sud,ouest,nord,est (ordre Overpass)


def _charger(path, defaut):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return defaut


def _sauver(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _statut(resultats, echecs, phase, extra=None):
    tuiles = sum(1 for v in resultats.values() if isinstance(v, list))
    elems = sum(len(v) for v in resultats.values() if isinstance(v, list))
    d = {"phase": phase, "tuiles_ok": tuiles, "elements_bruts": elems,
         "echecs": echecs, "horodatage": time.strftime("%Y-%m-%d %H:%M:%S")}
    if extra:
        d.update(extra)
    _sauver(HEARTBEAT, d)


def recolter():
    """Parcourt les tuiles (avec subdivision adaptative), remplit le cache."""
    resultats = _charger(CACHE_TUILES, {})
    echecs = []

    def traiter(w, s, e, n):
        key = _clef(w, s, e, n)
        cached = resultats.get(key)
        if isinstance(cached, list):
            return                      # tuile déjà récoltée
        if isinstance(cached, dict) and cached.get("split"):
            # déjà subdivisée précédemment : traiter les 4 enfants
            _subdiviser(w, s, e, n)
            return
        bbox = f"{s},{w},{n},{e}"
        print(f"  tuile {key} …", flush=True)
        try:
            d = _overpass(_requete(bbox))
            els = d.get("elements", [])
            resultats[key] = els
            _sauver(CACHE_TUILES, resultats)
            _statut(resultats, len(echecs), "recolte", {"derniere_tuile": key,
                    "elements_tuile": len(els)})
            print(f"    -> {len(els)} éléments", flush=True)
            time.sleep(2)
        except Exception as exc:
            largeur = min(e - w, n - s)
            if largeur > TUILE_MIN + 1e-9:
                print(f"    ! échec, subdivision de {key} : {exc}", flush=True)
                resultats[key] = {"split": True}
                _sauver(CACHE_TUILES, resultats)
                _subdiviser(w, s, e, n)
            else:
                print(f"    !! échec définitif {key} : {exc}", flush=True)
                echecs.append(key)
                _statut(resultats, len(echecs), "recolte", {"echec_tuile": key})

    def _subdiviser(w, s, e, n):
        mw, ms = (w + e) / 2, (s + n) / 2
        for sw, ss, se, sn in ((w, s, mw, ms), (mw, s, e, ms),
                               (w, ms, mw, n), (mw, ms, e, n)):
            traiter(sw, ss, se, sn)

    lon = LON_MIN
    while lon < LON_MAX - 1e-9:
        lat = LAT_MIN
        while lat < LAT_MAX - 1e-9:
            traiter(lon, lat, min(lon + PAS, LON_MAX), min(lat + PAS, LAT_MAX))
            lat += PAS
        lon += PAS

    if echecs:
        print(f"\n  ! {len(echecs)} tuile(s) en échec définitif : {echecs}", flush=True)
    else:
        print("\n  Toutes les tuiles récoltées.", flush=True)
    return resultats, echecs


# ---------------------------------------------------------------------------
# Conversion en GeoJSON
# ---------------------------------------------------------------------------

RE_HTML = re.compile(r"<[^>]+>")

def _type_et_nom(tags):
    """(type interne, nom générique par défaut) selon le tag OSM d'origine."""
    if tags.get("amenity") == "drinking_water" or (
            tags.get("amenity") == "fountain" and tags.get("drinking_water") == "yes"):
        return "fontaine", "Point d'eau potable"
    if tags.get("man_made") == "water_tap":
        return "robinet", "Robinet"
    if tags.get("amenity") == "water_point":
        return "point_d_eau", "Point d'eau"
    if tags.get("natural") == "spring":
        return "source", "Source"
    return None, None


def _potable(typ, tags):
    dw = tags.get("drinking_water")
    if dw == "yes":
        return "oui"
    if dw == "no":
        return "non"
    if typ in ("fontaine", "robinet", "point_d_eau"):
        return "oui"          # vocation potable, sans contre-indication
    return "inconnu"          # source non taguée : la potabilité ne se présume pas


def _details(tags):
    d = {}
    op = (tags.get("operator") or "").strip()
    if op and not RE_HTML.search(op):
        d["operator"] = op[:80]
    fee = tags.get("fee")
    if fee == "yes":
        d["fee"] = "Payant"
    elif fee == "no":
        d["fee"] = "Gratuit"
    charge = (tags.get("charge") or "").strip()
    if charge:
        d["charge"] = charge[:60]
    saison = (tags.get("seasonal") or "").strip()
    if saison and saison != "no":
        d["seasonal"] = "Saisonnier" if saison == "yes" else saison[:40]
    pmr = tags.get("wheelchair")
    if pmr == "yes":
        d["wheelchair"] = "Accessible PMR"
    elif pmr == "limited":
        d["wheelchair"] = "PMR (accès limité)"
    elif pmr == "no":
        d["wheelchair"] = "Non accessible PMR"
    ele = (tags.get("ele") or "").strip().replace(",", ".")
    m = re.match(r"^-?\d+(\.\d+)?", ele)
    if m:
        try:
            alt = int(round(float(m.group(0))))
            if -50 <= alt <= 5000:
                d["ele"] = alt
        except ValueError:
            pass
    desc = (tags.get("description") or "").strip()
    if desc:
        desc = RE_HTML.sub("", desc).strip()
        if desc:
            d["description"] = desc[:200]
    return d


def convertir(resultats):
    # 1) fusion de toutes les tuiles, dédoublonnage par id OSM
    par_osm = {}
    for v in resultats.values():
        if not isinstance(v, list):
            continue
        for el in v:
            par_osm[f"{el['type']}{el['id']}"] = el

    # 2) construction des candidats + contrôle qualité
    candidats = []          # (clefOSM, type_letter, osm_id, feature_partiel)
    hors_bornes = 0
    prives = 0
    for clef_osm, el in par_osm.items():
        tags = el.get("tags") or {}
        if tags.get("access") in ("private", "no"):
            prives += 1
            continue
        typ, nom_defaut = _type_et_nom(tags)
        if typ is None:
            continue
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None or lon is None:
            continue
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            hors_bornes += 1
            continue
        nom = (tags.get("name") or "").strip()
        nom = RE_HTML.sub("", nom).strip()
        if not nom or re.fullmatch(r"(way|node|relation)?[/ ]?\d+", nom, re.I):
            nom = nom_defaut
        details = _details(tags)
        pot = _potable(typ, tags)
        feat = {
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": None,  # affecté après (registre)
                "name": nom,
                "theme": "eau",
                "type": typ,
                "potable": pot,
                "details": details,
            },
        }
        candidats.append((clef_osm, el["type"][0], el["id"], feat, lat, lon))

    # 3) dédoublonnage géographique (nœud/way d'un même point, ~11 m, même type)
    vus = {}
    dedup = []
    doublons_geo = 0
    for c in candidats:
        clef_osm, tl, oid, feat, lat, lon = c
        gk = (feat["properties"]["type"], round(lat, 4), round(lon, 4))
        if gk in vus:
            doublons_geo += 1
            # garde la fiche la plus riche (plus de details), sinon id le plus bas
            autre = vus[gk]
            score = len(feat["properties"]["details"])
            score_autre = len(autre[3]["properties"]["details"])
            if score > score_autre:
                dedup[autre[6]] = None  # invalide l'ancien
                vus[gk] = c + (len(dedup),)
                dedup.append(c)
            continue
        vus[gk] = c + (len(dedup),)
        dedup.append(c)
    dedup = [c for c in dedup if c is not None]

    # 4) affectation des ids stables via le registre
    registre = _charger(REGISTRE, {})
    used = set(registre.values())
    if registre:
        maxi = max(int(v.split("-")[1]) for v in registre.values())
    else:
        maxi = 0
    # nouveaux : ordre déterministe (type, id OSM) pour un diff git lisible
    nouveaux = sorted((c for c in dedup if c[0] not in registre),
                      key=lambda c: (c[1], c[2]))
    for c in nouveaux:
        maxi += 1
        registre[c[0]] = f"eau-{maxi:05d}"
    _sauver(REGISTRE, registre)

    features = []
    for c in dedup:
        feat = c[3]
        feat["properties"]["id"] = registre[c[0]]
        # retire la clef details vide pour rester léger, mais garde l'objet
        features.append((registre[c[0]], feat))
    # tri final par id -> diff git déterministe
    features.sort(key=lambda x: x[0])
    features = [f for _, f in features]

    stats = {
        "total": len(features),
        "hors_bornes": hors_bornes,
        "prives_ecartes": prives,
        "doublons_geo": doublons_geo,
        "osm_uniques": len(par_osm),
    }
    return features, stats


def ecrire(features, stats):
    CIBLE.write_text(
        json.dumps({"type": "FeatureCollection", "features": features},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    ko = CIBLE.stat().st_size // 1024
    par_type, par_pot = {}, {}
    for f in features:
        p = f["properties"]
        par_type[p["type"]] = par_type.get(p["type"], 0) + 1
        par_pot[p["potable"]] = par_pot.get(p["potable"], 0) + 1
    print(f"\n=== data/eau.geojson : {len(features)} points, {ko} Ko ===")
    print(f"  par type    : {par_type}")
    print(f"  potabilité  : {par_pot}")
    print(f"  hors bornes : {stats['hors_bornes']} | privés écartés : "
          f"{stats['prives_ecartes']} | doublons géo : {stats['doublons_geo']}")
    _statut({}, 0, "termine", {"final": stats, "par_type": par_type,
             "par_potable": par_pot, "poids_ko": ko})


def main():
    print("== Récolte des points d'eau (OSM/Overpass) ==", flush=True)
    _statut(_charger(CACHE_TUILES, {}), 0, "demarrage")
    resultats, echecs = recolter()
    print("\n== Conversion en GeoJSON ==", flush=True)
    features, stats = convertir(resultats)
    ecrire(features, stats)
    if echecs:
        print(f"\n!! Récolte INCOMPLÈTE : tuiles à reprendre : {echecs}")
    print("Terminé.", flush=True)


if __name__ == "__main__":
    main()
