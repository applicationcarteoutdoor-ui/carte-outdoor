# -*- coding: utf-8 -*-
"""
Récolte des AIRES DE VIDANGE pour fourgons/camping-cars (eaux grises, eaux
noires, WC chimique) — OSM, ODbL, FAITS seulement.

⚠️ Le tag principal ne suffit PAS : la moitié du gisement est cartographiée
sur le polygone d'un camping/aire de services. Trois veines obligatoires
(mesuré : la 2e apporte ~+1 000 points en France, la 3e ~+650) :
  1. amenity=sanitary_dump_station          → « Aire dédiée »
  2. tourism=caravan_site  + sanitary_dump_station=yes|customers|public
  3. tourism=camp_site     + sanitary_dump_station=yes|customers|public
                                            → « Aire de camping »
Fusion par proximité à 150 m, la veine 1 (aire dédiée, position précise)
l'emportant sur le polygone de camping.

PIÈGES mesurés (ne pas « corriger » sans relire) :
  - `sanitary_dump_station:black_water` est documenté sur le wiki mais son
    usage mondial réel est ZÉRO → aucun filtre « eaux noires » possible.
  - `fee` sur un polygone de camping veut dire que LE CAMPING est payant, pas
    la vidange → le tarif n'est retenu que sur les aires DÉDIÉES (veine 1).
  - `access` n'est rempli qu'à 9,5 % sur les polygones de camping (contre
    51 % sur les aires dédiées) → même prudence.

Lancer :  python tools/recolter_vidange.py            (les 10 pays)
          python tools/recolter_vidange.py fr de      (une sélection)
Sortie :  tools/vidange-<iso>.json  (rejoué par les scripts d'intégration)
"""

import json
import math
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle)"}
# overpass-api.de en tête ; maps.mail.ru en secours. JAMAIS kumi.systems
# (il pend jusqu'au timeout — vécu, cf. CLAUDE.md).
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context()
CTX_NV.check_hostname = False
CTX_NV.verify_mode = ssl.CERT_NONE

PAYS = ["fr", "ch", "it", "es", "pt", "de", "nl", "lu", "be", "nz"]
# valeurs de sanitary_dump_station qui signalent une vidange DISPONIBLE
VALEURS_OK = {"yes", "customers", "public", "permissive"}
FUSION_M = 150  # rayon de dédoublonnage entre veines


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for ctx in (CTX, CTX_NV):
            for att in (0, 30, 90, 180):
                if att:
                    time.sleep(att)
                try:
                    req = urllib.request.Request(ep, data=data, headers=UA)
                    with urllib.request.urlopen(req, timeout=400, context=ctx) as r:
                        return json.load(r)
                except urllib.error.HTTPError as e:
                    print(f"    ({ep.split('/')[2]} HTTP {e.code})", flush=True)
                    if e.code in (429, 504):
                        continue
                    break
                except Exception as e:
                    print(f"    ({ep.split('/')[2]} : {str(e)[:70]})", flush=True)
    raise RuntimeError("Overpass injoignable")


def _centre(e):
    if e.get("lat") is not None:
        return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")


def hav_m(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


# Une VEINE = une requête séparée. Les trois réunies en un seul appel font
# tomber Overpass en 504 sur les gros pays (vécu sur la France) : on interroge
# veine par veine, c'est plus léger et ça repart tout seul en cas d'échec.
VEINES = (
    ('nwr["amenity"="sanitary_dump_station"](area.p);', "Aire dédiée"),
    ('nwr["tourism"="caravan_site"]["sanitary_dump_station"](area.p);', "Aire de camping"),
    ('nwr["tourism"="camp_site"]["sanitary_dump_station"](area.p);', "Aire de camping"),
)


def recolter(iso):
    """Les 3 veines, une requête chacune (area ISO, jamais de bbox : la NZ
    chevauche l'antiméridien avec les Chatham)."""
    dedies, campings = [], []
    for sel, type_aire in VEINES:
        req = ('[out:json][timeout:300];'
               f'area["ISO3166-1"="{iso.upper()}"][admin_level=2]->.p;'
               f'({sel});out center tags;')
        d = _post(req)
        n = 0
        for e in d.get("elements", []):
            lat, lon = _centre(e)
            if lat is None:
                continue
            t = e.get("tags", {})
            if type_aire == "Aire dédiée":
                cible = dedies
            else:
                # veines 2/3 : ne garder que si la vidange est réellement dispo
                if (t.get("sanitary_dump_station") or "").lower() not in VALEURS_OK:
                    continue
                cible = campings
            cible.append({
                "osm": f'{e.get("type", "node")[0]}{e.get("id")}',
                "nom": (t.get("name") or "").strip(),
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "type_aire": type_aire,
                "tags": {k: v for k, v in t.items() if k in TAGS_GARDES},
            })
            n += 1
        print(f"    veine {type_aire} : {n}", flush=True)
        time.sleep(2)

    # une même aire peut sortir des veines 2 ET 3 (camp_site + caravan_site)
    vus, uniques = set(), []
    for c in campings:
        if c["osm"] not in vus:
            vus.add(c["osm"])
            uniques.append(c)
    campings = uniques

    # Fusion 150 m : on ne retire QUE les doublons entre veines — la même aire
    # cartographiée à la fois en nœud dédié et en polygone de camping. Toutes
    # les aires DÉDIÉES sont conservées (chacune est un objet OSM réel : les
    # dédoublonner entre elles supprimerait des aires voisines légitimes).
    #
    # Grille spatiale plutôt que comparaison deux à deux (la France fait
    # 2 694 dédiées × 3 114 campings = 8,4 M de distances en O(n²)).
    # ⚠️ Le pas doit rester > 150 m EN LONGITUDE au plus haut de nos latitudes :
    # 0,004° font 445 m en latitude mais seulement 0,004 × 111320 × cos(54°)
    # ≈ 262 m aux Pays-Bas — d'où 0,004 et non 0,002 (qui tombait à ~131 m et
    # laissait passer des doublons).
    pas = 0.004
    grille = {}

    def _cellule(p):
        return (math.floor(p["lat"] / pas), math.floor(p["lon"] / pas))

    def _ajouter(p):
        grille.setdefault(_cellule(p), []).append(p)

    def _proche(p):
        cx, cy = _cellule(p)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in grille.get((cx + dx, cy + dy), ()):
                    if hav_m(p["lat"], p["lon"], q["lat"], q["lon"]) <= FUSION_M:
                        return True
        return False

    gardes = list(dedies)
    for p in dedies:
        _ajouter(p)
    for c in campings:
        if _proche(c):
            continue
        gardes.append(c)
        _ajouter(c)
    print(f"  {iso}: {len(dedies)} dédiées + {len(campings)} campings "
          f"→ {len(gardes)} après fusion {FUSION_M} m", flush=True)
    return gardes


TAGS_GARDES = ("name", "fee", "access", "water_point", "drinking_water", "opening_hours",
               "website", "contact:website", "operator", "charge", "description",
               "sanitary_dump_station", "sanitary_dump_station:chemical_toilet",
               "sanitary_dump_station:grey_water", "motor_vehicle", "capacity")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cibles = [a.lower() for a in sys.argv[1:] if not a.startswith("--")] or PAYS
    total = 0
    for iso in cibles:
        sortie = DOSSIER / f"vidange-{iso}.json"
        if sortie.exists() and "--refaire" not in sys.argv:
            deja = json.loads(sortie.read_text(encoding="utf-8"))
            print(f"  {iso}: déjà en cache ({len(deja)})", flush=True)
            total += len(deja)
            continue
        pts = recolter(iso)
        sortie.write_text(json.dumps(pts, ensure_ascii=False), encoding="utf-8")
        total += len(pts)
        time.sleep(5)  # politesse entre pays
    print(f"TOTAL {total} aires de vidange")
