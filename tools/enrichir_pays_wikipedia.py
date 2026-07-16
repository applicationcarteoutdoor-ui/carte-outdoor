# -*- coding: utf-8 -*-
"""
Enrichit les points Suisse/Italie/Espagne avec Wikipédia : PHOTO (960 px),
LIEN vers l'article et DESCRIPTION courte (1re phrase de l'intro).

Cibles : refuges, lacs, cascades, grottes, châteaux, musées (les villages ont
déjà leur enrichissement ; les via ferrata reçoivent les sites spécialisés).

Appariement CONSERVATEUR (leçon des châteaux FR) : titre candidat = le NOM
EXACT du point ; l'article n'est retenu que si ses coordonnées sont à ≤ 10 km
(25 km pour les lacs — les grands lacs sont longs). Sans coordonnées : écarté.

Langues : it -> it.wikipedia, es -> es.wikipedia, ch -> fr puis de puis it
(les noms OSM suisses suivent la langue locale). Premier appariement gagnant.

Ce script ne fait que REMPLIR le cache tools/pays-wiki-<iso>.json (clé
« nom|lat4 ») ; l'application se fait au build par construire_pays.py
(re-build = ids stables + enrichissement rejoué).

Lancer :  python tools/enrichir_pays_wikipedia.py            (les trois)
          python tools/enrichir_pays_wikipedia.py it         (un pays)
"""

import json
import math
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle ; contact bidband4@gmail.com)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

LANGUES = {"ch": ["fr", "de", "it"], "it": ["it"], "es": ["es"]}
THEMES_CIBLES = ("refuge", "lac", "cascade", "grotte", "chateau", "culture")
RAYON_KM = {"lac": 25.0}
RAYON_DEFAUT = 10.0


def _get(url):
    for ctx in (CTX, CTX_NV):
        for attente in (0, 15, 60, 180):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA),
                                            timeout=90, context=ctx) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    print("    (429, patience…)", flush=True)
                    continue
                raise
            except Exception as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Wikipédia injoignable")


def hav(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def charger_points(iso):
    d = json.loads((RACINE / "data" / iso / "points.geojson").read_text(encoding="utf-8"))
    pts = []
    for f in d["features"]:
        p = f["properties"]
        if p["theme"] not in THEMES_CIBLES:
            continue
        lon, lat = f["geometry"]["coordinates"]
        pts.append({"nom": p["name"], "lat": lat, "lon": lon, "theme": p["theme"]})
    return pts


def cle_de(o):
    return f"{o['nom']}|{round(o['lat'], 4)}"


def passe_langue(iso, lang, lieux, cache):
    """Interroge <lang>.wikipedia pour les lieux encore sans article."""
    a_faire = [o for o in lieux
               if not cache.get(cle_de(o), {}).get("wiki")
               and lang not in cache.get(cle_de(o), {}).get("essais", [])]
    if not a_faire:
        return
    print(f"{iso}/{lang}: {len(a_faire)} lieux à interroger", flush=True)
    base = f"https://{lang}.wikipedia.org/w/api.php"
    fcache = DOSSIER / f"pays-wiki-{iso}.json"
    for i in range(0, len(a_faire), 50):
        lot = a_faire[i:i + 50]
        titres = "|".join(o["nom"].replace("|", " ")[:250] for o in lot)
        q = urllib.parse.urlencode({
            "action": "query", "titles": titres, "redirects": 1,
            "prop": "coordinates|pageimages", "colimit": "max",
            "piprop": "thumbnail", "pithumbsize": 900, "format": "json",
        })
        d = _get(f"{base}?{q}")
        query = d.get("query") or {}
        vers = {}
        for r in query.get("normalized", []) + query.get("redirects", []):
            vers[r["from"]] = r["to"]

        def titre_final(t):
            vu = set()
            while t in vers and t not in vu:
                vu.add(t)
                t = vers[t]
            return t

        par_titre = {p["title"]: p for p in query.get("pages", {}).values()
                     if "missing" not in p and "pageid" in p}
        for o in lot:
            k = cle_de(o)
            ent = cache.setdefault(k, {})
            ent.setdefault("essais", []).append(lang)
            p = par_titre.get(titre_final(o["nom"][:250]))
            if not p:
                continue
            c = (p.get("coordinates") or [{}])[0]
            rayon = RAYON_KM.get(o["theme"], RAYON_DEFAUT)
            if not c.get("lat") or hav(o["lat"], o["lon"], c["lat"], c["lon"]) > rayon:
                continue  # pas de coord ou trop loin : homonyme probable
            th = (p.get("thumbnail") or {}).get("source", "")
            ent.update({
                "lang": lang, "pageid": p["pageid"],
                "wiki": f"https://{lang}.wikipedia.org/wiki/" +
                        urllib.parse.quote(p["title"].replace(" ", "_")),
                "photo": th if th.startswith("https://upload.wikimedia.org") else "",
            })
        fcache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        ok = sum(1 for v in cache.values() if v.get("wiki"))
        print(f"  {iso}/{lang} {min(i + 50, len(a_faire))}/{len(a_faire)} — {ok} appariés",
              flush=True)
        time.sleep(1.2)


def descriptions(iso, cache):
    """1re phrase de l'intro pour les appariés, lots de 20 pageids PAR LANGUE."""
    fcache = DOSSIER / f"pays-wiki-{iso}.json"
    for lang in LANGUES[iso]:
        lot_lang = [(k, v) for k, v in cache.items()
                    if v.get("lang") == lang and v.get("pageid") and "description" not in v]
        if not lot_lang:
            continue
        print(f"{iso}/{lang}: descriptions à chercher : {len(lot_lang)}", flush=True)
        base = f"https://{lang}.wikipedia.org/w/api.php"
        for i in range(0, len(lot_lang), 20):
            lot = lot_lang[i:i + 20]
            q = urllib.parse.urlencode({
                "action": "query", "pageids": "|".join(str(v["pageid"]) for _, v in lot),
                "prop": "extracts", "exintro": 1, "explaintext": 1, "exsentences": 1,
                "format": "json",
            })
            d = _get(f"{base}?{q}")
            pages = (d.get("query") or {}).get("pages", {})
            for k, v in lot:
                v["description"] = (pages.get(str(v["pageid"])) or {}).get("extract", "").strip()[:300]
            fcache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            if (i // 20) % 20 == 0:
                print(f"  {iso}/{lang} descriptions {min(i + 20, len(lot_lang))}/{len(lot_lang)}",
                      flush=True)
            time.sleep(1.0)


def enrichir(iso):
    lieux = charger_points(iso)
    fcache = DOSSIER / f"pays-wiki-{iso}.json"
    cache = json.loads(fcache.read_text(encoding="utf-8")) if fcache.exists() else {}
    print(f"== {iso}: {len(lieux)} points cibles ({len(cache)} déjà en cache) ==", flush=True)
    for lang in LANGUES[iso]:
        passe_langue(iso, lang, lieux, cache)
    descriptions(iso, cache)
    ok = sum(1 for v in cache.values() if v.get("wiki"))
    photos = sum(1 for v in cache.values() if v.get("photo"))
    print(f"{iso} TERMINÉ : {ok} appariés, {photos} photos -> {fcache.name}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cibles = [a for a in sys.argv[1:] if a in LANGUES] or list(LANGUES)
    for iso in cibles:
        enrichir(iso)
