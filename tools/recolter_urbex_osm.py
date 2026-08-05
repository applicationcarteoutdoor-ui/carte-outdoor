# -*- coding: utf-8 -*-
"""
Pack « Lieux abandonnés » (urbex) — récolte OpenStreetMap, France.

⚠️ POURQUOI PAS URBEXOLOGY : leurs conditions interdisent explicitement la
copie de toute partie du site sans accord écrit, ET le partage des lieux avec
quiconque en dehors de leur Discord. C'est aussi un service avec une offre
payante : sa base EST son produit. On ne le récolte donc pas — même règle que
descente-canyon.com et rocjumper.com.

OSM (ODbL) donne la même matière et se partage librement, à une condition :
l'ATTRIBUTION doit voyager avec les données. Elle est donc écrite dans la
catégorie et dans chaque fiche.

Ce script produit un fichier d'IMPORT autonome (formatVersion 2) : il crée la
catégorie personnalisée ET les points. Il n'est jamais intégré à l'app.

Sélection : on privilégie les lieux NOMMÉS (un « bunker » anonyme parmi 9 000
n'aide personne, « Fort de Douaumont » si). Les types rares et sans ambiguïté
(mines, gares désaffectées) sont gardés même sans nom.

Lancer : python tools/recolter_urbex_osm.py [FR] [--ecrire]
Sortie  : dev/pack-urbex-france.geojson  (à importer via ⬆ Importer)
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

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle; bidband4@gmail.com)"}
ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
]
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context()
CTX_NV.check_hostname = False
CTX_NV.verify_mode = ssl.CERT_NONE

THEME_ID = "perso-urbex"          # préfixe « perso- » = catégorie utilisateur
FUSION_M = 60                     # un même site tagué plusieurs fois

# Une veine = un type de lieu. TOUT est pris, nommé ou non (demande
# utilisateur) : les objets anonymes gardent un libellé de repli lisible
# (« Bunker / ouvrage militaire »…) plutôt qu'un nom vide.
VEINES = [
    ("bunker",    'nwr["military"="bunker"](area.p);',         False, "Bunker / ouvrage militaire"),
    ("fort",      'nwr["historic"="fort"](area.p);',           False, "Fort"),
    ("ruine",     'nwr["historic"="ruins"](area.p);',          False, "Ruines"),
    ("batiment",  'nwr["building"="ruins"](area.p);'
                  'nwr["ruins"="yes"](area.p);',               False, "Bâtiment en ruine"),
    ("mine",      'nwr["man_made"="mineshaft"](area.p);'
                  'nwr["historic"="mine"](area.p);'
                  'nwr["historic"="mine_shaft"](area.p);',     False, "Mine / puits"),
    ("gare",      'nwr["disused:railway"="station"](area.p);'
                  'nwr["railway"="disused_station"](area.p);'
                  'nwr["abandoned:railway"="station"](area.p);', False, "Gare désaffectée"),
    ("friche",    'nwr["landuse"="brownfield"](area.p);',      False, "Friche industrielle"),
    ("abandonne", 'nwr["abandoned"="yes"](area.p);',           False, "Lieu abandonné"),
    ("usine",     'nwr["disused:man_made"="works"](area.p);'
                  'nwr["abandoned:man_made"="works"](area.p);'
                  'nwr["disused:industrial"](area.p);',        False, "Usine désaffectée"),
    ("militaire", 'nwr["disused:military"](area.p);'
                  'nwr["abandoned:military"](area.p);'
                  'nwr["military"="trench"](area.p);',         False, "Site militaire désaffecté"),
    ("carriere",  'nwr["disused:landuse"="quarry"](area.p);'
                  'nwr["abandoned:landuse"="quarry"](area.p);', False, "Carrière abandonnée"),
    ("village",   'nwr["abandoned:place"](area.p);'
                  'nwr["place"]["abandoned"="yes"](area.p);',  False, "Lieu-dit abandonné"),
]

# ⚠️ Ce texte est recopié sur CHAQUE point : à 50 000 points, 100 caractères
# de plus = 5 Mo de fichier. D'où la version courte — la version longue de la
# mise en garde tient dans le nom de la catégorie et dans le mode d'emploi
# livré à côté du pack.
AVERTISSEMENT = ("Terrain souvent privé (entrée interdite) et bâti dangereux. "
                 "Position OSM non vérifiée.")


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
                    print(f"    ({ep.split('/')[2]} : {str(e)[:60]})", flush=True)
    return None


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


TAGS_UTILES = ("name", "historic", "military", "bunker_type", "ruins", "building",
               "start_date", "description", "wikipedia", "website", "operator",
               "abandoned", "disused", "resource", "man_made", "access")


def recolter(iso="FR"):
    """Une requête par veine (les réunir fait tomber Overpass en 504)."""
    cache = DOSSIER / f"urbex-{iso.lower()}-osm.json"
    deja = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else {}
    for cle, sel, nom_requis, libelle in VEINES:
        if cle in deja:
            print(f"  {cle}: déjà en cache ({len(deja[cle])})", flush=True)
            continue
        req = ('[out:json][timeout:300];'
               f'area["ISO3166-1"="{iso}"][admin_level=2]->.p;'
               f'({sel});out center tags;')
        d = _post(req)
        if d is None:
            print(f"  {cle}: ÉCHEC réseau — relancer plus tard", flush=True)
            continue
        pts = []
        for e in d.get("elements", []):
            lat, lon = _centre(e)
            if lat is None:
                continue
            t = e.get("tags", {})
            nom = (t.get("name") or "").strip()
            if nom_requis and not nom:
                continue
            pts.append({
                "osm": f'{e.get("type", "node")[0]}{e.get("id")}',
                "nom": nom or libelle,
                "lat": round(lat, 6),
                "lon": round(lon, 6),
                "genre": libelle,
                "tags": {k: v for k, v in t.items() if k in TAGS_UTILES},
            })
        deja[cle] = pts
        cache.write_text(json.dumps(deja, ensure_ascii=False), encoding="utf-8")
        print(f"  {cle}: {len(pts)}", flush=True)
        time.sleep(4)
    return deja


def construire(par_veine):
    """Fusionne, dédoublonne et met au format d'import de l'application."""
    tous = []
    for cle, _sel, _nr, _lib in VEINES:
        tous.extend(par_veine.get(cle, []))

    # dédoublonnage spatial (grille : un même site porte souvent 2 tags)
    pas = 0.002
    grille, gardes = {}, []
    for p in tous:
        cx, cy = math.floor(p["lat"] / pas), math.floor(p["lon"] / pas)
        double = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for q in grille.get((cx + dx, cy + dy), ()):
                    if hav_m(p["lat"], p["lon"], q["lat"], q["lon"]) <= FUSION_M:
                        double = True
                        break
                if double:
                    break
            if double:
                break
        if double:
            continue
        gardes.append(p)
        grille.setdefault((cx, cy), []).append(p)

    feats = []
    for n, p in enumerate(sorted(gardes, key=lambda x: (x["nom"], x["lat"])), start=1):
        t = p["tags"]
        d = {"type": p["genre"], "avertissement": AVERTISSEMENT}
        if t.get("start_date"):
            d["epoque"] = t["start_date"][:40]
        if t.get("bunker_type"):
            d["ouvrage"] = t["bunker_type"][:40]
        if t.get("operator"):
            d["exploitant"] = t["operator"][:60]
        if (t.get("access") or "") in ("private", "no"):
            d["acces"] = "Privé — entrée interdite"

        # Le lien OSM porte l'ATTRIBUTION exigée par l'ODbL (il pointe sur
        # l'objet source, son auteur et son historique) : il est sur chaque
        # point, jamais optionnel.
        liens = [{"label": "🗺️ Source OpenStreetMap (ODbL)",
                  "url": "https://www.openstreetmap.org/" + _osm_url(p["osm"])}]
        if t.get("wikipedia"):
            lang, _, titre = t["wikipedia"].partition(":")
            if titre:
                liens.append({"label": "🔗 Wikipédia",
                              "url": f"https://{lang}.wikipedia.org/wiki/"
                                     + urllib.parse.quote(titre.replace(" ", "_"))})
        site = t.get("website") or ""
        if site.startswith("http"):
            liens.append({"label": "🌐 Site", "url": site})
        # « Infos » seulement pour les lieux NOMMÉS : une recherche web sur
        # « Bâtiment en ruine » ne mène nulle part et pèse 100 octets × 35 000.
        if t.get("name"):
            liens.append({"label": "🔎 Infos",
                          "url": "https://www.google.com/search?q="
                                 + urllib.parse.quote(f'{p["nom"]} France')})

        desc = p["genre"] + "."
        if d.get("epoque"):
            desc = f'{p["genre"]} ({d["epoque"]}).'
        if d.get("acces"):
            desc += " Terrain privé : entrée interdite."

        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
            "properties": {
                "id": f"urbex-{n:05d}",
                "name": p["nom"],
                "theme": THEME_ID,
                "description": desc,
                "links": liens,
                "photos": [],
                "details": d,
            },
        })
    return feats


def _osm_url(ref):
    if not ref or len(ref) < 2:
        return ""
    return {"n": "node", "w": "way", "r": "relation"}.get(ref[0], "node") + "/" + ref[1:]


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    iso = next((a.upper() for a in sys.argv[1:] if not a.startswith("--")), "FR")
    par_veine = recolter(iso)
    feats = construire(par_veine)
    print(f"\n{sum(len(v) for v in par_veine.values())} objets bruts → {len(feats)} points après fusion {FUSION_M} m")
    from collections import Counter
    for g, n in Counter(f["properties"]["details"]["type"] for f in feats).most_common():
        print(f"  {g:32} {n}")

    if "--ecrire" in sys.argv:
        def ecrire(features, nom_fichier, label):
            paquet = {
                "formatVersion": 2,
                "points": {"type": "FeatureCollection", "features": features},
                "statuses": {},
                "journal": {},
                "customThemes": [{
                    "id": THEME_ID,
                    "label": label,
                    "icon": "🏚️",
                    "color": "#6c584c",
                }],
            }
            chemin = RACINE / "dev" / nom_fichier
            chemin.parent.mkdir(exist_ok=True)
            chemin.write_text(json.dumps(paquet, ensure_ascii=False, separators=(",", ":")),
                              encoding="utf-8")
            mo = chemin.stat().st_size / 1048576
            print(f"  ÉCRIT {chemin.name} — {len(features)} points, {mo:.1f} Mo")

        # Version COMPLÈTE et version allégée aux lieux NOMMÉS : 50 000 points
        # tiennent sur la carte, mais un fichier de dizaines de Mo se transmet
        # mal et pèse au premier import. Le choix reste à l'utilisateur.
        nommes = [f for f in feats
                  if f["properties"]["name"] not in {v[3] for v in VEINES}]
        print()
        ecrire(feats, f"pack-urbex-{iso.lower()}-complet.geojson", "Lieux abandonnés")
        ecrire(nommes, f"pack-urbex-{iso.lower()}-nommes.geojson", "Lieux abandonnés")
        print("→ à importer par ⬆ Importer : le fichier crée la catégorie ET les points.")
    else:
        print("\n(aperçu — relancer avec --ecrire)")
