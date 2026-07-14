# -*- coding: utf-8 -*-
"""
Enrichit la catégorie CULTURE avec Wikipédia : PHOTO (Commons, 900 px),
lien vers l'article et DESCRIPTION courte (1re phrase de l'intro).

Cibles : musées + galeries (FR, fr.wikipedia) et musées (NZ, en.wikipedia).
Les monuments/sites archéo sont EXCLUS : noms génériques (« Monument aux
morts »…), l'appariement par nom serait un nid d'homonymes.

Appariement CONSERVATEUR (leçon des châteaux) : titre candidat = le NOM EXACT
du lieu ; l'article n'est retenu que si ses coordonnées sont à ≤ 10 km du
point (un article sans coordonnées est écarté — jamais deviner).

Pièges Wikipédia gérés : lots de 50 titres via action=query&titles=,
redirects=1, cache sauvegardé à CHAQUE lot (les 429 arrivent par vagues,
retry 15-180 s), extraits par lots de 20 (exlimit).

Lancer :  python tools/enrichir_culture_wikipedia.py
Sortie   :  tools/culture-wiki-fr.json / tools/culture-wiki-nz.json
            (clé « nom|lat4 » → { photo, wiki, description })
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
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle ; contact bidband4@gmail.com)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

CIBLES = {
    "fr": {"source": "culture-fr-osm.json", "cache": "culture-wiki-fr.json",
           "lang": "fr", "types": ("musee", "galerie")},
    "nz": {"source": "culture-nz-osm.json", "cache": "culture-wiki-nz.json",
           "lang": "en", "types": ("musee", "galerie")},
}
RAYON_KM = 10.0


def _get(url):
    for ctx in (CTX, CTX_NV):
        for attente in (0, 15, 60, 180):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90, context=ctx) as r:
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


def cle_de(o):
    return f"{o['nom']}|{round(o['lat'], 4)}"


def enrichir(pays, cfg):
    src = json.loads((DOSSIER / cfg["source"]).read_text(encoding="utf-8"))
    fcache = DOSSIER / cfg["cache"]
    cache = json.loads(fcache.read_text(encoding="utf-8")) if fcache.exists() else {}
    lieux = [o for o in src if o["type"] in cfg["types"] and cle_de(o) not in cache]
    print(f"{pays}: {len(lieux)} lieux à interroger ({len(cache)} déjà en cache)", flush=True)
    base = f"https://{cfg['lang']}.wikipedia.org/w/api.php"

    # 1. Photo + coordonnées par LOTS DE 50 TITRES (titre = nom exact)
    for i in range(0, len(lieux), 50):
        lot = lieux[i:i + 50]
        titres = "|".join(o["nom"].replace("|", " ") for o in lot)
        q = urllib.parse.urlencode({
            "action": "query", "titles": titres, "redirects": 1,
            "prop": "coordinates|pageimages", "colimit": "max",
            "piprop": "thumbnail", "pithumbsize": 900, "format": "json",
        })
        d = _get(f"{base}?{q}")
        pages = (d.get("query") or {}).get("pages", {})
        # suivre les redirections/normalisations : titre demandé -> titre final
        vers = {}
        for r in (d.get("query") or {}).get("normalized", []) + (d.get("query") or {}).get("redirects", []):
            vers[r["from"]] = r["to"]
        def titre_final(t):
            vu = set()
            while t in vers and t not in vu:
                vu.add(t)
                t = vers[t]
            return t
        par_titre = {}
        for p in pages.values():
            if "missing" in p or "pageid" not in p:
                continue
            par_titre[p["title"]] = p
        for o in lot:
            k = cle_de(o)
            p = par_titre.get(titre_final(o["nom"]))
            if not p:
                cache[k] = {}  # article absent : mémorisé pour ne pas redemander
                continue
            c = (p.get("coordinates") or [{}])[0]
            if not c.get("lat") or hav(o["lat"], o["lon"], c["lat"], c["lon"]) > RAYON_KM:
                cache[k] = {}  # pas de coord, ou trop loin : homonyme probable
                continue
            th = (p.get("thumbnail") or {}).get("source", "")
            cache[k] = {
                "pageid": p["pageid"],
                "wiki": f"https://{cfg['lang']}.wikipedia.org/wiki/" +
                        urllib.parse.quote(p["title"].replace(" ", "_")),
                "photo": th if th.startswith("https://upload.wikimedia.org") else "",
            }
        fcache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        ok = sum(1 for v in cache.values() if v.get("wiki"))
        print(f"  {pays} {min(i + 50, len(lieux))}/{len(lieux)} — {ok} appariés", flush=True)
        time.sleep(1.2)

    # 2. Description courte (1re phrase) pour les appariés, lots de 20 pageids
    a_decrire = [(k, v) for k, v in cache.items() if v.get("pageid") and "description" not in v]
    print(f"{pays}: descriptions à chercher : {len(a_decrire)}", flush=True)
    for i in range(0, len(a_decrire), 20):
        lot = a_decrire[i:i + 20]
        q = urllib.parse.urlencode({
            "action": "query", "pageids": "|".join(str(v["pageid"]) for _, v in lot),
            "prop": "extracts", "exintro": 1, "explaintext": 1, "exsentences": 1,
            "format": "json",
        })
        d = _get(f"{base}?{q}")
        pages = (d.get("query") or {}).get("pages", {})
        for k, v in lot:
            ext = (pages.get(str(v["pageid"])) or {}).get("extract", "").strip()
            v["description"] = ext[:300]
        fcache.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        if (i // 20) % 10 == 0:
            print(f"  {pays} descriptions {min(i + 20, len(a_decrire))}/{len(a_decrire)}", flush=True)
        time.sleep(1.0)

    ok = sum(1 for v in cache.values() if v.get("wiki"))
    photos = sum(1 for v in cache.values() if v.get("photo"))
    print(f"{pays} TERMINÉ : {ok} appariés, {photos} photos -> {fcache.name}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cibles = [a for a in sys.argv[1:] if a in CIBLES] or list(CIBLES)
    for pays in cibles:
        enrichir(pays, CIBLES[pays])
