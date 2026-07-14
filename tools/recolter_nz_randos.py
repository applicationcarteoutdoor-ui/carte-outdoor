# -*- coding: utf-8 -*-
"""
Randonnées emblématiques de Nouvelle-Zélande — liste ÉDITORIALE vérifiée,
tracés réels depuis DOC_Tracks_EAM (CC-BY 4.0). Chaque entrée cible des
segments PRÉCIS (FlocID exacts, vérifiés à la main le 14/07/2026) : pas de
rapprochement flou, pas de mauvais tracé (règle conservatrice du projet).

Produit :
  - tools/nz-randos.json        (points + stats, consommé par construire_nz.py)
  - data/nz/randos.geojson      (tracés, properties.rando = id du point)

Stats honnêtes : distance mesurée sur le tracé ; durée estimée à 4 km/h
(aller-retour si le tracé ne boucle pas, séjour en jours au-delà de 25 km) ;
pas de D+ (pas d'altimétrie NZ branchée).

Lancer :  python tools/recolter_nz_randos.py
"""

import json
import math
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE_JSON = RACINE / "tools" / "nz-randos.json"
SORTIE_TRACES = RACINE / "data" / "nz" / "randos.geojson"
B = "https://services1.arcgis.com/3JjYDyG3oajxU6HO/arcgis/rest/services/DOC_Tracks_EAM/FeatureServer/0/query"
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

# (nom affiché, [FlocID exacts], région, note courte pour la fiche)
RANDOS = [
    ("Roys Peak Track", ["WANAKALH-TK22"], "Wanaka (Otago)",
     "LA vue carte postale sur le lac Wanaka — montée raide et régulière"),
    ("Ben Lomond Track", ["QUEENSTN-TK01"], "Queenstown (Otago)",
     "Le sommet au-dessus de Queenstown (1 748 m)"),
    ("Mueller Hut Route (par Sealy Tarns)", ["SEALYMUL-TK02", "SEALYMUL-TK01"], "Aoraki / Mount Cook",
     "Les 2 200 « marches » des Sealy Tarns puis l'éboulis vers le refuge Mueller — face à l'Aoraki"),
    ("Kea Point Track", ["HOOKRVAL-TK01"], "Aoraki / Mount Cook",
     "Balade facile vers le point de vue sur le glacier Mueller"),
    ("Key Summit Track", ["MILFRDRJ-TK03"], "Fiordland",
     "Détour alpin de la Routeburn : tarns et panorama sur les Darran"),
    ("Lake Marian Track", ["DARRANEM-TK07"], "Fiordland",
     "Lac alpin suspendu dans un cirque des monts Darran"),
    ("Rob Roy Track", ["WMATUKIT-TK01"], "Mount Aspiring",
     "Face au glacier Rob Roy et ses cascades, vallée du Matukituki"),
    ("Avalanche Peak Track", ["ARTHRPBC-TK04"], "Arthur's Pass",
     "Sommet exigeant au-dessus du village d'Arthur's Pass (1 833 m)"),
    ("Pouakai Track", ["EGMONTBC-TK20"], "Taranaki",
     "Vers les tarns des Pouakai et LE reflet du mont Taranaki"),
    ("Taranaki Falls Track", ["WHAKAPVW-TK10"], "Tongariro",
     "Boucle facile vers une chute de 20 m sous le Ruapehu"),
    ("Tama Lakes Track", ["WHAKAPVW-TK11", "WHAKAPVW-TK12"], "Tongariro",
     "Deux lacs de cratère entre Ruapehu et Ngauruhoe"),
    ("Rangitoto Summit Track", ["RANGITOS-TK06"], "Auckland",
     "Le volcan de la baie d'Auckland (accès en ferry)"),
    ("Cape Brett Track", ["CBRETTLH-TK01"], "Northland (Bay of Islands)",
     "Crêtes côtières jusqu'au phare de Cape Brett"),
    ("Tarawera Trail", ["TARAWERA-TK01"], "Rotorua",
     "Le long du lac Tarawera jusqu'à Hot Water Beach"),
    ("Putangirua Pinnacles Track", ["PUTANGIR-TK02"], "Wairarapa",
     "Les orgues de pierre du « Chemin des Morts » (Le Seigneur des Anneaux)"),
    ("Cathedral Cove Walk", ["CATHEDRC-TK02"], "Coromandel",
     "L'arche marine la plus célèbre du pays"),
    ("Wainui Falls Track", ["ABTASNPN-TK01"], "Golden Bay (Abel Tasman)",
     "Cascade de 20 m par une passerelle suspendue"),
    ("Robert Ridge Route (lac Angelus)", ["TRAVERSS-TK01"], "Nelson Lakes",
     "Ligne de crête alpine vers le refuge Angelus — par beau temps seulement"),
    ("Bealey Spur Track", ["ARTHRPAC-TK01"], "Arthur's Pass",
     "Éperon panoramique au-dessus de la vallée du Waimakariri"),
    ("Blue Pools Walk", ["MAKAHAST-TK10"], "Mount Aspiring (Haast)",
     "Vasques bleu glacier du Makarora"),
    ("Gertrude Valley / Saddle Track", ["DARRANEM-TK02"], "Fiordland",
     "Le col au-dessus du Milford Sound — itinéraire alpin non balisé en fin de course"),
    ("Red Tarns Track", ["REDTARNS-TK01"], "Aoraki / Mount Cook",
     "Tarns rouges au-dessus du village du Mount Cook"),
    ("Isthmus Peak Track", ["WANAKALH-TK26"], "Wanaka (Otago)",
     "L'alternative à Roys Peak, entre les lacs Wanaka et Hawea"),
    ("Diamond Lake & Lake Wanaka Lookout", ["WANAKALH-TK09", "WANAKALH-TK24"], "Wanaka (Otago)",
     "Petit lac et belvédères au-dessus du Wanaka"),
    ("Copland Track (Welcome Flat)", ["COPLNDKA-TK01"], "West Coast",
     "Jusqu'aux sources chaudes de Welcome Flat, au pied des Alpes du Sud"),
    ("Hollyford Track", ["HOLLYFTK-TK01", "HOLLYFTK-TK02", "HOLLYFTK-TK04", "HOLLYFTK-TK05"], "Fiordland",
     "Grande traversée SANS col, de la vallée Hollyford à la mer de Tasman (plusieurs jours)"),
]


def _get(url):
    for ctx in (CTX, CTX_NV):
        for att in (0, 10, 30):
            if att:
                time.sleep(att)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120, context=ctx) as r:
                    return json.load(r)
            except Exception as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("ArcGIS injoignable")


def hav(a, b):
    la1, lo1, la2, lo2 = a[1], a[0], b[1], b[0]
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    x = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(x))


def segments_de(flocs):
    where = urllib.parse.quote("FlocID IN (" + ",".join(f"'{f}'" for f in flocs) + ")")
    d = _get(f"{B}?where={where}&outFields=FlocID&returnGeometry=true&outSR=4326&f=json")
    segs = []
    for f in d.get("features", []):
        for p in (f.get("geometry") or {}).get("paths") or []:
            segs.append([[round(x, 6), round(y, 6)] for x, y in p])
    return segs


def recolter():
    points, traces = [], []
    rate = []
    for n, (nom, flocs, region, note) in enumerate(sorted(RANDOS, key=lambda r: r[0]), start=1):
        pid = f"nz-rando-{n:04d}"
        segs = segments_de(flocs)
        if not segs:
            rate.append(nom)
            continue
        km = sum(hav(a, b) for s in segs for a, b in zip(s, s[1:]))
        # boucle si départ et arrivée du tracé assemblé se touchent (< 500 m)
        debut, fin = segs[0][0], segs[-1][-1]
        boucle = hav(debut, fin) < 0.5
        if km > 25:
            duree, duree_n = f"≈ {max(2, round(km / 20))} jours", round(km / 4 * 2)
            dist_txt = f"{km:.0f} km"
        elif boucle:
            duree_n = km / 4
            duree, dist_txt = f"≈ {duree_n:.0f} h (boucle)".replace("≈ 0 h", "≈ 1 h"), f"{km:.1f} km (boucle)"
        else:
            duree_n = km * 2 / 4
            duree, dist_txt = f"≈ {max(1, round(duree_n))} h aller-retour", f"{km:.1f} km (aller)"
        points.append({
            "id": pid, "nom": nom, "region": region, "note": note,
            "lat": debut[1], "lon": debut[0],  # départ du premier segment (côté accès)
            "distance": dist_txt, "distance_n": round(km, 1),
            "duree": duree, "duree_n": round(duree_n, 1),
        })
        traces.append({
            "type": "Feature",
            "geometry": {"type": "MultiLineString", "coordinates": segs},
            "properties": {"rando": pid, "name": nom},
        })
        print(f"  {nom}: {km:.1f} km, {len(segs)} segment(s)", flush=True)
        time.sleep(0.3)

    SORTIE_JSON.write_text(json.dumps(points, ensure_ascii=False), encoding="utf-8")
    SORTIE_TRACES.write_text(json.dumps({"type": "FeatureCollection", "features": traces},
                                        ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT : {len(points)} randos -> {SORTIE_JSON.name} + {SORTIE_TRACES}"
          f" ({SORTIE_TRACES.stat().st_size // 1024} Ko)")
    if rate:
        print("SANS TRACÉ (écartées) :", rate)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
