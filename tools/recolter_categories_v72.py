"""Quatre nouvelles catégories v72 (France, extension pays plus tard) :

  - sommet-croix      : OSM natural=peak + summit:cross=yes (croix sommitales)
  - col-mythique      : OSM mountain_pass=yes nommés, GARDÉS seulement si un
                        article Wikipédia fr au nom exact existe à ≤ 10 km
                        (la notoriété fait le « mythique ») — photo/description
  - village-abandonne : Wikidata (villages abandonnés/villes fantômes, P17=France,
                        P625) + article fr quand il existe
  - ciel-etoile       : liste ÉDITORIALE des lieux certifiés DarkSky (7 RICE
                        françaises + réserves/parcs célèbres de nos pays),
                        coordonnées/photo/extraits via l'API Wikipédia

Append dans data/points.geojson avec des ids STABLES (croix-####, col-####,
vaba-####, ciel-####) — relançable : les points déjà présents (par id) sont
mis à jour EN PLACE, jamais renumérotés (registre = ordre du premier run).

Usage : python tools/recolter_categories_v72.py [--ecrire]
"""

import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
OVERPASS = "https://maps.mail.ru/osm/tools/overpass/api/interpreter"
UA = {"User-Agent": "SpotMap/1.0 (nouvelles categories; contact bidband4@gmail.com)"}


def _http(url, data=None, essais=4):
    for i in range(essais):
        try:
            r = urllib.request.Request(url, data=data, headers=UA)
            return json.load(urllib.request.urlopen(r, timeout=180))
        except Exception as e:
            print(f"  (réseau occupé, pause {15 * (i + 1)} s… {str(e)[:60]})", flush=True)
            time.sleep(15 * (i + 1))
    return {}


def overpass(req):
    return _http(OVERPASS, urllib.parse.urlencode({"data": req}).encode())


def wiki_api(base, **params):
    q = urllib.parse.urlencode({"action": "query", "format": "json",
                                "formatversion": "2", **params})
    return _http(f"https://{base}/w/api.php?{q}")


def _centre(e):
    if e.get("lat") is not None:
        return e["lat"], e["lon"]
    c = e.get("center") or {}
    return c.get("lat"), c.get("lon")


def _hav_km(a, b, c, d):
    import math
    dx = (d - b) * math.cos(math.radians(a)) * 111.32
    dy = (c - a) * 111.32
    return (dx * dx + dy * dy) ** 0.5


# ---------------------------------------------------------------- sommets à croix
def sommets_croix():
    d = overpass('[out:json][timeout:180];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["natural"="peak"]["summit:cross"="yes"](area.p););out center tags;')
    pts = []
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        if lat is None:
            continue
        details = {"fiche": "À vérifier"}
        if (t.get("ele") or "").replace(".", "").isdigit():
            alt = int(float(t["ele"]))
            details["altitude"] = f"{alt} m"
            details["altitude_n"] = alt
        pts.append({
            "nom": (t.get("name") or "Croix sommitale").strip(),
            "lat": round(lat, 6), "lon": round(lon, 6),
            "details": details, "links": [], "photos": [], "description": "",
        })
    print(f"sommets à croix : {len(pts)}", flush=True)
    return pts


# ---------------------------------------------------------------- cols mythiques
def cols_mythiques():
    d = overpass('[out:json][timeout:180];area["ISO3166-1"="FR"][admin_level=2]->.p;'
                 '(nwr["mountain_pass"="yes"]["name"](area.p););out center tags;')
    bruts = []
    vus = set()
    for e in d.get("elements", []):
        lat, lon = _centre(e)
        t = e.get("tags", {})
        nom = (t.get("name") or "").strip()
        if lat is None or not nom or nom.lower() in vus:
            continue
        vus.add(nom.lower())
        bruts.append({"nom": nom, "lat": round(lat, 6), "lon": round(lon, 6), "tags": t})
    print(f"cols nommés OSM : {len(bruts)} — croisement Wikipédia…", flush=True)

    # la notoriété (article fr au nom EXACT, coords ≤ 10 km) fait le « mythique »
    gardes = []
    for i in range(0, len(bruts), 50):
        lot = bruts[i:i + 50]
        d = wiki_api("fr.wikipedia.org", titles="|".join(c["nom"] for c in lot),
                     redirects="1", prop="coordinates|pageimages|extracts",
                     colimit="max", piprop="thumbnail", pithumbsize="960",
                     exintro="1", explaintext="1", exsentences="1", exlimit="max")
        pages = {p["title"]: p for p in (d.get("query") or {}).get("pages", []) if not p.get("missing")}
        redir = {r["from"]: r["to"] for r in (d.get("query") or {}).get("redirects", [])}
        for c in lot:
            p = pages.get(redir.get(c["nom"], c["nom"]))
            if not p:
                continue
            coord = (p.get("coordinates") or [{}])[0]
            if not coord.get("lat") or _hav_km(c["lat"], c["lon"], coord["lat"], coord["lon"]) > 10:
                continue
            th = (p.get("thumbnail") or {}).get("source", "")
            details = {"fiche": "Référencé"}
            if (c["tags"].get("ele") or "").replace(".", "").isdigit():
                alt = int(float(c["tags"]["ele"]))
                details["altitude"] = f"{alt} m"
                details["altitude_n"] = alt
            gardes.append({
                "nom": c["nom"], "lat": c["lat"], "lon": c["lon"],
                "details": details,
                "links": [{"label": "🔗 Wikipédia",
                           "url": "https://fr.wikipedia.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))}],
                "photos": [th] if th.startswith("https://upload.wikimedia.org") else [],
                "description": (p.get("extract") or "").strip()[:300],
            })
        print(f"  cols {min(i + 50, len(bruts))}/{len(bruts)} -> {len(gardes)} mythiques", flush=True)
        time.sleep(1.2)
    return gardes


# ---------------------------------------------------------------- villages abandonnés
def villages_abandonnes():
    # Q74047 ville fantôme, Q17362920 village abandonné — France, avec P625
    sparql = """SELECT DISTINCT ?item ?itemLabel ?coord ?article WHERE {
      { ?item wdt:P31/wdt:P279* wd:Q74047. } UNION { ?item wdt:P31/wdt:P279* wd:Q17362920. }
      ?item wdt:P17 wd:Q142; wdt:P625 ?coord.
      OPTIONAL { ?article schema:about ?item; schema:isPartOf <https://fr.wikipedia.org/>. }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "fr". }
    }"""
    d = _http("https://query.wikidata.org/sparql?" +
              urllib.parse.urlencode({"query": sparql, "format": "json"}))
    pts, vus = [], set()
    for b in d.get("results", {}).get("bindings", []):
        nom = b.get("itemLabel", {}).get("value", "")
        coord = b.get("coord", {}).get("value", "")  # Point(lon lat)
        if not nom or nom.startswith("Q") or not coord.startswith("Point("):
            continue
        lon, lat = map(float, coord[6:-1].split())
        if not (41 <= lat <= 51.5 or -63 <= lon <= 56):  # métropole + DOM très large
            continue
        cle = f"{nom.lower()}|{round(lat, 3)}"
        if cle in vus:
            continue
        vus.add(cle)
        article = b.get("article", {}).get("value", "")
        pts.append({
            "nom": nom, "lat": round(lat, 6), "lon": round(lon, 6),
            "details": {"fiche": "Référencé" if article else "À vérifier"},
            "links": [{"label": "🔗 Wikipédia", "url": article}] if article else [],
            "photos": [], "description": "",
        })
    # photos/descriptions pour ceux qui ont un article
    avec = [p for p in pts if p["links"]]
    for i in range(0, len(avec), 50):
        lot = avec[i:i + 50]
        titres = [urllib.parse.unquote(p["links"][0]["url"].split("/wiki/")[-1]).replace("_", " ") for p in lot]
        d = wiki_api("fr.wikipedia.org", titles="|".join(titres), redirects="1",
                     prop="pageimages|extracts", piprop="thumbnail", pithumbsize="960",
                     exintro="1", explaintext="1", exsentences="1", exlimit="max")
        pages = {p["title"]: p for p in (d.get("query") or {}).get("pages", [])}
        for p, titre in zip(lot, titres):
            page = pages.get(titre) or {}
            th = (page.get("thumbnail") or {}).get("source", "")
            if th.startswith("https://upload.wikimedia.org"):
                p["photos"] = [th]
            p["description"] = (page.get("extract") or "").strip()[:300]
        time.sleep(1.0)
    print(f"villages abandonnés : {len(pts)} (dont {len(avec)} avec article)", flush=True)
    return pts


# ---------------------------------------------------------------- ciels étoilés
# Lieux CERTIFIÉS DarkSky de nos 10 pays (liste éditoriale vérifiée juillet
# 2026 — les 7 RICE françaises + réserves/parcs célèbres ailleurs). Le titre
# Wikipédia fournit coordonnées/photo/description (jamais de coordonnée de tête).
CIELS = [
    ("fr", "Pic du Midi de Bigorre", "Réserve internationale de ciel étoilé (2013, la 1re de France)"),
    ("fr", "Parc national des Cévennes", "Réserve internationale de ciel étoilé (2018, la plus vaste d'Europe)"),
    ("fr", "Parc national du Mercantour", "Réserve internationale de ciel étoilé Alpes Azur Mercantour (2019)"),
    ("fr", "Parc naturel régional de Millevaches en Limousin", "Réserve internationale de ciel étoilé (2021)"),
    ("fr", "Parc naturel régional du Vercors", "Réserve internationale de ciel étoilé (2022)"),
    ("fr", "Parc naturel régional des Landes de Gascogne", "Réserve internationale de ciel étoilé (2024)"),
    ("fr", "Parc naturel régional du Morvan", "Réserve internationale de ciel étoilé (2025)"),
    ("de", "Nationalpark Eifel", "Parc international de ciel étoilé (2019)"),
    ("de", "Biosphärenreservat Rhön", "Réserve internationale de ciel étoilé (2014)"),
    ("de", "Naturpark Westhavelland", "Réserve internationale de ciel étoilé (2014), la plus proche de Berlin"),
    ("ch", "Naturpark Gantrisch", "Parc de ciel étoilé certifié DarkSky (2019)"),
    ("nl", "Nationaal Park Lauwersmeer", "Parc international de ciel étoilé (2016)"),
    ("pt", "Alqueva", "Grande Rota do Alqueva — première destination touristique Starlight au monde (2011)"),
    ("nz", "Aoraki / Mount Cook National Park", "Cœur de la réserve Aoraki Mackenzie (2012), l'un des plus beaux ciels du monde"),
    ("nz", "Rakiura National Park", "Sanctuaire international de ciel étoilé de Stewart Island (2019)"),
    ("nz", "Great Barrier Island", "Sanctuaire international de ciel étoilé (2017)"),
]
WIKI_PAR_PAYS = {"fr": "fr", "de": "de", "ch": "de", "nl": "nl", "pt": "pt", "nz": "en"}


def ciels_etoiles():
    pts = []
    for pays, titre, note in CIELS:
        base = f"{WIKI_PAR_PAYS[pays]}.wikipedia.org"
        d = wiki_api(base, titles=titre, redirects="1",
                     prop="coordinates|pageimages|extracts", colimit="max",
                     piprop="thumbnail", pithumbsize="960",
                     exintro="1", explaintext="1", exsentences="1")
        pages = (d.get("query") or {}).get("pages", [])
        p = pages[0] if pages and not pages[0].get("missing") else None
        coord = (p.get("coordinates") or [{}])[0] if p else {}
        if not coord.get("lat"):
            print(f"  ciel-etoile SANS coordonnées : {titre} ({pays}) — écarté", flush=True)
            continue
        th = (p.get("thumbnail") or {}).get("source", "")
        pts.append({
            "pays": pays,
            "nom": titre.replace("Parc naturel régional", "PNR") if len(titre) > 60 else titre,
            "lat": round(coord["lat"], 6), "lon": round(coord["lon"], 6),
            "details": {"label": note, "fiche": "Référencé"},
            "links": [{"label": "🔗 Wikipédia",
                       "url": f"https://{base}/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))}],
            "photos": [th] if th.startswith("https://upload.wikimedia.org") else [],
            "description": (p.get("extract") or "").strip()[:300],
        })
        time.sleep(0.8)
    print(f"ciels étoilés : {len(pts)} lieux certifiés", flush=True)
    return pts


# ---------------------------------------------------------------- intégration
def integrer(ecrire):
    # V1 : FRANCE seulement — data/points.geojson. Les lieux DarkSky des autres
    # pays (liste CIELS ci-dessus) attendent l'intégration construire_pays
    # (un append manuel dans data/<iso>/ serait écrasé au rebuild).
    ciels_fr = []
    for p in ciels_etoiles():
        if p.pop("pays") == "fr":
            ciels_fr.append(p)
    recoltes = {
        "sommet-croix": ("croix", sommets_croix()),
        "col-mythique": ("col", cols_mythiques()),
        "village-abandonne": ("vaba", villages_abandonnes()),
        "ciel-etoile": ("ciel", ciels_fr),
    }
    chemin = RACINE / "data" / "points.geojson"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    existants = {f["properties"]["id"]: f for f in d["features"]}
    # registre implicite : ordre stable = tri (nom, lat) au PREMIER run ;
    # les runs suivants retrouvent les ids par (theme, nom, ~lat)
    cles_connues = {}
    for f in d["features"]:
        p = f["properties"]
        cles_connues[f'{p["theme"]}|{p["name"].lower()}|{round(f["geometry"]["coordinates"][1], 3)}'] = p["id"]
    bilan = {}
    for theme, (abr, pts) in recoltes.items():
        suivant = 1 + max([int(i.split("-")[-1]) for i in existants if i.startswith(abr + "-")] or [0])
        n_nouveaux = n_maj = 0
        for p in sorted(pts, key=lambda x: (x["nom"], x["lat"])):
            cle = f'{theme}|{p["nom"].lower()}|{round(p["lat"], 3)}'
            pid = cles_connues.get(cle)
            props = {
                "id": pid or f"{abr}-{suivant:04d}",
                "name": p["nom"], "theme": theme,
                "description": p["description"], "links": p["links"],
                "photos": p["photos"], "details": p["details"],
            }
            feat = {"type": "Feature",
                    "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
                    "properties": props}
            if pid and pid in existants:
                existants[pid].update(feat)
                n_maj += 1
            else:
                d["features"].append(feat)
                suivant += 1
                n_nouveaux += 1
        bilan[theme] = (n_nouveaux, n_maj)
        print(f"{theme}: +{n_nouveaux} nouveaux, {n_maj} mis à jour", flush=True)
    if ecrire:
        chemin.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT data/points.geojson ({chemin.stat().st_size // 1024} Ko)")
    else:
        print("(aperçu — relancer avec --ecrire)")
    return bilan


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    integrer("--ecrire" in sys.argv)
