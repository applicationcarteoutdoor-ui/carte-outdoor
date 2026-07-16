# -*- coding: utf-8 -*-
"""
Récolte GÉNÉRIQUE des TOILETTES et POINTS D'EAU d'un pays depuis OSM
(Overpass) -> data/<iso>/toilettes.geojson + data/<iso>/eau.geojson.

Même schéma que la France (themes.js inchangé) :
  - toilettes : details tarif/accessibilite/pmr_type/acces/equipement/horaires
  - eau       : details type/potabilite (libellés) + fee/wheelchair/seasonal/…
    (la potabilité d'une SOURCE n'est jamais présumée : « non garantie »)

Ids STABLES dérivés de l'id OSM : <iso>-wc-n1234 / <iso>-eau-w5678 —
une re-récolte ne renumérote jamais (contrairement à un compteur).

Méthode : Overpass POST, aire pays area["ISO3166-1"] + tuiles 3° avec
subdivision adaptative en cas d'échec (modèle recolter_eau.py). La NZ est
récoltée SANS bbox (les Chatham chevauchent l'antiméridien) : aire seule.
Cache par tuile tools/sanitaires-<iso>.json (gitignoré) -> reprise sur relance.

Lancer :  python tools/recolter_sanitaires_pays.py IT
          python tools/recolter_sanitaires_pays.py ES CH NZ
"""

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle ; contact bidband4@gmail.com)"}
OVERPASS = "https://overpass-api.de/api/interpreter"

# bboxes : [(lon_min, lat_min, lon_max, lat_max), …] — None = aire seule (NZ)
PAYS = {
    "ch": {"iso": "CH", "bboxes": [(5.8, 45.7, 10.6, 47.95)], "pas": 3.0},
    "it": {"iso": "IT", "bboxes": [(6.5, 35.2, 18.7, 47.2)], "pas": 3.0},
    "es": {"iso": "ES", "bboxes": [(-9.5, 35.9, 4.5, 43.95),      # péninsule + Baléares
                                   (-18.4, 27.4, -13.3, 29.5)],   # Canaries
           "pas": 3.0},
    "nz": {"iso": "NZ", "bboxes": None, "pas": None},
}

SEL_TOILETTES = ['["amenity"="toilets"]']
SEL_EAU = [
    '["amenity"="drinking_water"]',
    '["man_made"="water_tap"]',
    '["amenity"="water_point"]',
    '["natural"="spring"]',
    '["amenity"="fountain"]["drinking_water"="yes"]',
]
TUILE_MIN = 0.75

TYPE_EAU = {"fontaine": "Fontaine", "source": "Source",
            "robinet": "Robinet", "point_d_eau": "Point d'eau"}
POTABLE = {"oui": "Eau potable", "non": "Non potable",
           "inconnu": "Potabilité non garantie"}
RE_HTML = re.compile(r"<[^>]+>")
RE_JOUR_OSM = re.compile(r"\b(Mo|Tu|We|Th|Fr|Sa|Su|PH)\b")
TRAD_JOURS = {"Mo": "lun", "Tu": "mar", "We": "mer", "Th": "jeu",
              "Fr": "ven", "Sa": "sam", "Su": "dim", "PH": "fériés"}


def _overpass(requete):
    donnees = urllib.parse.urlencode({"data": requete}).encode()
    for attente in (0, 20, 60, 120):
        if attente:
            print(f"    (Overpass occupé, pause {attente} s…)", flush=True)
            time.sleep(attente)
        req = urllib.request.Request(OVERPASS, data=donnees, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=320) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Overpass surchargé (429/504/timeout persistant)")


def _requete(iso, selecteurs, bbox):
    """bbox = 'sud,ouest,nord,est' ou None (aire seule, cas NZ)."""
    zone = f"({bbox})" if bbox else ""
    lignes = "".join(f"node{t}(area.p){zone};way{t}(area.p){zone};" for t in selecteurs)
    return ('[out:json][timeout:280];'
            f'area["ISO3166-1"="{iso}"]["admin_level"="2"]->.p;'
            f'({lignes});out center;')


def recolter(pays, cfg):
    """Remplit le cache tuile par tuile (clé '<couche>|<bbox>')."""
    fcache = DOSSIER / f"sanitaires-{pays}.json"
    cache = json.loads(fcache.read_text(encoding="utf-8")) if fcache.exists() else {}
    echecs = []

    def sauver():
        fcache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    def traiter(couche, selecteurs, w, s, e, n):
        key = f"{couche}|{s:.4f},{w:.4f},{n:.4f},{e:.4f}"
        val = cache.get(key)
        if isinstance(val, list):
            return
        if isinstance(val, dict) and val.get("split"):
            subdiviser(couche, selecteurs, w, s, e, n)
            return
        bbox = f"{s},{w},{n},{e}"
        print(f"  {pays} {couche} tuile {bbox} …", flush=True)
        try:
            d = _overpass(_requete(cfg["iso"], selecteurs, bbox))
            cache[key] = d.get("elements", [])
            sauver()
            print(f"    -> {len(cache[key])} éléments", flush=True)
            time.sleep(2)
        except Exception as exc:
            if min(e - w, n - s) > TUILE_MIN + 1e-9:
                print(f"    ! échec, subdivision : {exc}", flush=True)
                cache[key] = {"split": True}
                sauver()
                subdiviser(couche, selecteurs, w, s, e, n)
            else:
                print(f"    !! échec définitif {key} : {exc}", flush=True)
                echecs.append(key)

    def subdiviser(couche, selecteurs, w, s, e, n):
        mw, ms = (w + e) / 2, (s + n) / 2
        for q in ((w, s, mw, ms), (mw, s, e, ms), (w, ms, mw, n), (mw, ms, e, n)):
            traiter(couche, selecteurs, *q)

    for couche, selecteurs in (("wc", SEL_TOILETTES), ("eau", SEL_EAU)):
        if cfg["bboxes"] is None:
            # NZ : une seule requête par couche, aire seule (antiméridien)
            key = f"{couche}|pays"
            if not isinstance(cache.get(key), list):
                print(f"  {pays} {couche} (aire entière) …", flush=True)
                d = _overpass(_requete(cfg["iso"], selecteurs, None))
                cache[key] = d.get("elements", [])
                sauver()
                print(f"    -> {len(cache[key])} éléments", flush=True)
                time.sleep(2)
            continue
        for (lon0, lat0, lon1, lat1) in cfg["bboxes"]:
            lon = lon0
            while lon < lon1 - 1e-9:
                lat = lat0
                while lat < lat1 - 1e-9:
                    traiter(couche, selecteurs,
                            lon, lat, min(lon + cfg["pas"], lon1), min(lat + cfg["pas"], lat1))
                    lat += cfg["pas"]
                lon += cfg["pas"]
    return cache, echecs


# ---------------------------------------------------------------------------
# Conversions (schémas identiques à la France)
# ---------------------------------------------------------------------------

def horaires_fr(valeur):
    v = valeur.strip()
    if v == "24/7":
        return "24 h/24, 7 j/7"
    if v == "off":
        return "Fermées actuellement"
    v = RE_JOUR_OSM.sub(lambda m: TRAD_JOURS[m.group(1)], v)
    v = (v.replace("sunrise", "lever du soleil").replace("sunset", "coucher du soleil")
         .replace(" off", " fermé").replace(";", " · "))
    return v[:100]


def _coords(e):
    lat = e.get("lat") or (e.get("center") or {}).get("lat")
    lon = e.get("lon") or (e.get("center") or {}).get("lon")
    return lat, lon


def convertir_toilettes(pays, elements):
    features = []
    for e in sorted(elements.values(), key=lambda x: (x["type"], x["id"])):
        tags = e.get("tags") or {}
        if tags.get("amenity") != "toilets" or tags.get("access") in ("private", "no"):
            continue
        lat, lon = _coords(e)
        if lat is None:
            continue
        details = {}
        fee = tags.get("fee")
        if fee == "yes":
            details["tarif"] = "Payant"
        elif fee == "no":
            details["tarif"] = "Gratuit"
        pmr = tags.get("wheelchair")
        if pmr == "yes":
            details["accessibilite"], details["pmr_type"] = "PMR", "oui"
        elif pmr == "limited":
            details["accessibilite"], details["pmr_type"] = "PMR (accès limité)", "oui"
        elif pmr == "no":
            details["accessibilite"], details["pmr_type"] = "Non accessible PMR", "non"
        if tags.get("access") == "customers":
            details["acces"] = "Réservées à la clientèle"
        if tags.get("changing_table") == "yes":
            details["equipement"] = "Table à langer"
        if tags.get("opening_hours"):
            details["horaires"] = horaires_fr(tags["opening_hours"])
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"{pays}-wc-{e['type'][0]}{e['id']}",
                "name": tags.get("name") or "Toilettes publiques",
                "theme": "toilettes",
                "details": details,
            },
        })
    return features


def _type_eau(tags):
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
    return "oui" if typ in ("fontaine", "robinet", "point_d_eau") else "inconnu"


def convertir_eau(pays, elements):
    features, vus = [], set()
    for e in sorted(elements.values(), key=lambda x: (x["type"], x["id"])):
        tags = e.get("tags") or {}
        if tags.get("access") in ("private", "no"):
            continue
        typ, nom_defaut = _type_eau(tags)
        if typ is None:
            continue
        lat, lon = _coords(e)
        if lat is None:
            continue
        gk = (typ, round(lat, 4), round(lon, 4))   # doublon nœud/way ~11 m
        if gk in vus:
            continue
        vus.add(gk)
        nom = RE_HTML.sub("", (tags.get("name") or "").strip()).strip()
        if not nom or re.fullmatch(r"(way|node|relation)?[/ ]?\d+", nom, re.I):
            nom = nom_defaut
        details = {"type": TYPE_EAU[typ], "potabilite": POTABLE[_potable(typ, tags)]}
        fee = tags.get("fee")
        if fee == "yes":
            details["fee"] = "Payant"
        elif fee == "no":
            details["fee"] = "Gratuit"
        pmr = tags.get("wheelchair")
        if pmr == "yes":
            details["wheelchair"] = "Accessible PMR"
        elif pmr == "limited":
            details["wheelchair"] = "PMR (accès limité)"
        elif pmr == "no":
            details["wheelchair"] = "Non accessible PMR"
        m = re.match(r"^-?\d+(\.\d+)?", (tags.get("ele") or "").strip().replace(",", "."))
        if m:
            try:
                alt = int(round(float(m.group(0))))
                if -50 <= alt <= 5000:
                    details["ele"] = alt
            except ValueError:
                pass
        desc = RE_HTML.sub("", (tags.get("description") or "").strip()).strip()
        if desc:
            details["description"] = desc[:200]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"{pays}-eau-{e['type'][0]}{e['id']}",
                "name": nom,
                "theme": "eau",
                "details": details,
            },
        })
    return features


def construire(pays):
    cfg = PAYS[pays]
    cache, echecs = recolter(pays, cfg)
    par_couche = {"wc": {}, "eau": {}}
    for key, val in cache.items():
        if not isinstance(val, list):
            continue
        couche = key.split("|", 1)[0]
        for e in val:
            par_couche[couche][f"{e['type']}{e['id']}"] = e
    dossier = RACINE / "data" / pays
    dossier.mkdir(parents=True, exist_ok=True)
    for couche, nom_fichier, conv in (("wc", "toilettes.geojson", convertir_toilettes),
                                      ("eau", "eau.geojson", convertir_eau)):
        feats = conv(pays, par_couche[couche])
        cible = dossier / nom_fichier
        cible.write_text(
            json.dumps({"type": "FeatureCollection", "features": feats},
                       ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8")
        print(f"{pays}: data/{pays}/{nom_fichier} — {len(feats)} points, "
              f"{cible.stat().st_size // 1024} Ko", flush=True)
    if echecs:
        print(f"{pays}: !! récolte INCOMPLÈTE, tuiles en échec : {echecs}", flush=True)
    return not echecs


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cibles = [a.lower() for a in sys.argv[1:] if a.lower() in PAYS] or list(PAYS)
    for pays in cibles:
        print(f"== {pays.upper()} : toilettes + points d'eau ==", flush=True)
        construire(pays)
    print("Terminé.", flush=True)
