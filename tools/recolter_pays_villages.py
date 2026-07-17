# -*- coding: utf-8 -*-
"""
Villages LABELLISÉS de Suisse/Italie/Espagne — les vrais labels officiels
(associations sœurs des « Plus Beaux Villages de France ») via les catégories
Wikipédia locales : coordonnées + photo (960 px) + 1re phrase.

  IT : « I borghi più belli d'Italia »  (~360)
  ES : « Los Pueblos Más Bonitos de España » (~120)
  CH : « Les plus beaux villages de Suisse » (~50)

Pièges Wikipédia habituels : categorymembers paginé (cmcontinue), coordonnées
par lots avec colimit=max + continue, photos pithumbsize=960 (taille normalisée).

Lancer :  python tools/recolter_pays_villages.py
Sortie   :  tools/pays-villages.json  { ch: [...], it: [...], es: [...] }
"""

import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "pays-villages.json"
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

# IT : it.wikipedia ne catégorise PAS les borghi labellisés → la liste vient de
# WIKIDATA (membres P463 de Q127107 « I borghi più belli d'Italia », CC0),
# l'aval (coordonnées/photo/extrait) reste l'API Wikipédia comme les autres.
PAYS = {
    "it": {"lang": "it", "label": "Borghi più belli d'Italia",
           "wikidata": "Q127107",
           "bornes": (35.0, 47.5, 6.0, 19.0)},
    "es": {"lang": "es", "label": "Pueblos Más Bonitos de España",
           "categories": ["Categoría:Localidades de la asociación Los Pueblos más bonitos de España"],
           "bornes": (27.0, 44.0, -18.5, 4.5)},  # Canaries incluses
    "ch": {"lang": "fr", "label": "Plus beaux villages de Suisse",
           "categories": ["Catégorie:Localité adhérant à l'association Les plus beaux villages de Suisse"],
           "bornes": (45.7, 47.9, 5.8, 10.6)},
    "be": {"lang": "fr", "label": "Plus Beaux Villages de Wallonie",
           "categories": ["Catégorie:Localité adhérant à l'association Les Plus Beaux Villages de Wallonie"],
           "bornes": (49.4, 50.9, 2.5, 6.5)},
    # Aucune structure Wikidata/catégorie exploitable : liste ÉDITORIALE du
    # réseau officiel Aldeias Históricas de Portugal (12 villages).
    "pt": {"lang": "pt", "label": "Aldeia Histórica de Portugal",
           "titres": ["Almeida (vila)", "Belmonte (Portugal)", "Castelo Mendo", "Castelo Novo",
                      "Castelo Rodrigo", "Idanha-a-Velha", "Linhares (Celorico da Beira)",
                      "Marialva (Mêda)", "Monsanto (Idanha-a-Nova)", "Piódão", "Sortelha", "Trancoso"],
           "bornes": (36.8, 42.2, -9.6, -6.1)},
    # DE / NL / LU : pas de label national établi — catégorie villages absente
    # pour ces pays (honnête), rien à récolter.
}


def titres_wikidata(qid, lang):
    """Titres des articles <lang>.wikipedia des membres P463 de `qid` (SPARQL)."""
    sparql = (
        "SELECT ?article WHERE { ?c wdt:P463 wd:" + qid + ". "
        "?article schema:about ?c; schema:isPartOf <https://" + lang + ".wikipedia.org/>. }"
    )
    u = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": sparql, "format": "json"})
    d = _get(u)
    titres = []
    for b in d.get("results", {}).get("bindings", []):
        url = b.get("article", {}).get("value", "")
        if "/wiki/" in url:
            titres.append(urllib.parse.unquote(url.split("/wiki/", 1)[1]).replace("_", " "))
    return titres


def _get(url):
    for ctx in (CTX, CTX_NV):
        for att in (0, 20, 60):
            if att:
                time.sleep(att)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90, context=ctx) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    continue
                raise
            except Exception as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Wikipédia injoignable")


def membres(base, categorie):
    """Tous les articles (ns 0) d'une catégorie."""
    titres, cont = [], ""
    while True:
        q = urllib.parse.urlencode({"action": "query", "list": "categorymembers",
                                    "cmtitle": categorie, "cmnamespace": 0,
                                    "cmlimit": "500", "format": "json"})
        d = _get(f"{base}?{q}{cont}")
        titres += [m["title"] for m in d.get("query", {}).get("categorymembers", [])]
        c = d.get("continue", {}).get("cmcontinue")
        if not c:
            return titres
        cont = "&cmcontinue=" + urllib.parse.quote(c)


def details(base, titres):
    """Coordonnées + photo + extrait, par lots de 20 (exlimit)."""
    res = {}
    for i in range(0, len(titres), 20):
        lot = titres[i:i + 20]
        q = urllib.parse.urlencode({
            "action": "query", "titles": "|".join(lot), "redirects": 1,
            "prop": "coordinates|pageimages|extracts", "colimit": "max",
            "piprop": "thumbnail", "pithumbsize": 960,
            "exintro": 1, "explaintext": 1, "exsentences": 1, "exlimit": "max",
            "format": "json",
        })
        d = _get(f"{base}?{q}")
        for p in (d.get("query") or {}).get("pages", {}).values():
            c = (p.get("coordinates") or [{}])[0]
            th = (p.get("thumbnail") or {}).get("source", "")
            res[p.get("title", "")] = {
                "lat": c.get("lat"), "lon": c.get("lon"),
                "photo": th if th.startswith("https://upload.wikimedia.org") else "",
                "extrait": (p.get("extract") or "").strip()[:300],
            }
        # un titre demandé redirigé garde son entrée sous le nom DEMANDÉ
        for r in (d.get("query") or {}).get("redirects", []):
            if r.get("to") in res:
                res[r["from"]] = res[r["to"]]
        time.sleep(1.0)
    # Repli WIKIDATA P625 : fréquent sur pt.wikipedia, les articles de
    # freguesias n'exposent pas prop=coordinates alors que l'entité en a.
    sans = [t for t, v in res.items() if not v.get("lat")]
    if sans:
        for t, (lat, lon) in _coords_wikidata(base, sans).items():
            if t in res:
                res[t]["lat"], res[t]["lon"] = lat, lon
    return res


def _coords_wikidata(base, titres):
    """{titre: (lat, lon)} via pageprops.wikibase_item puis P625."""
    coords = {}
    for i in range(0, len(titres), 20):
        lot = titres[i:i + 20]
        q = urllib.parse.urlencode({"action": "query", "titles": "|".join(lot),
                                    "redirects": 1, "prop": "pageprops", "format": "json"})
        d = _get(f"{base}?{q}")
        qids = {}
        for p in (d.get("query") or {}).get("pages", {}).values():
            qid = (p.get("pageprops") or {}).get("wikibase_item")
            if qid:
                qids[qid] = p.get("title", "")
        if not qids:
            continue
        q2 = urllib.parse.urlencode({"action": "wbgetentities", "ids": "|".join(qids),
                                     "props": "claims", "format": "json"})
        d2 = _get(f"https://www.wikidata.org/w/api.php?{q2}")
        for qid, ent in (d2.get("entities") or {}).items():
            cl = (ent.get("claims", {}).get("P625") or [{}])[0]
            val = cl.get("mainsnak", {}).get("datavalue", {}).get("value", {})
            if val.get("latitude") is not None and qid in qids:
                coords[qids[qid]] = (val["latitude"], val["longitude"])
        time.sleep(0.6)
    return coords


def recolter(cibles=None):
    """`cibles` (["be", "pt"]…) : ne récolte QUE ces pays et FUSIONNE dans le
    fichier existant — re-récolter un pays déjà construit ferait dériver
    l'ordre du cache, donc RENUMÉROTERAIT ses ids de villages (interdit)."""
    tout = json.loads(SORTIE.read_text(encoding="utf-8")) if SORTIE.exists() else {}
    for iso, cfg in PAYS.items():
        if cibles and iso not in cibles:
            continue
        base = f"https://{cfg['lang']}.wikipedia.org/w/api.php"
        titres = list(cfg.get("titres", []))  # liste éditoriale explicite
        if not titres and cfg.get("wikidata"):
            titres = titres_wikidata(cfg["wikidata"], cfg["lang"])
            print(f"{iso}: Wikidata {cfg['wikidata']} -> {len(titres)} articles", flush=True)
        for cat in cfg.get("categories", []):
            titres = membres(base, cat)
            if titres:
                print(f"{iso}: catégorie « {cat} » -> {len(titres)} articles", flush=True)
                break
            print(f"{iso}: « {cat} » vide, essai suivant…", flush=True)
        if not titres:
            print(f"{iso}: AUCUNE catégorie trouvée — villages ignorés (honnête)", flush=True)
            tout[iso] = []
            continue
        d = details(base, titres)
        la1, la2, lo1, lo2 = cfg["bornes"]
        villages = []
        for t in titres:
            v = d.get(t) or {}
            if not v.get("lat") or not (la1 <= v["lat"] <= la2 and lo1 <= v["lon"] <= lo2):
                continue
            villages.append({"nom": t.split(" (")[0], "titre": t, "lat": round(v["lat"], 6),
                             "lon": round(v["lon"], 6), "photo": v.get("photo", ""),
                             "extrait": v.get("extrait", ""), "label": cfg["label"],
                             "lang": cfg["lang"]})
        tout[iso] = villages
        print(f"{iso}: {len(villages)} villages géolocalisés", flush=True)
    SORTIE.write_text(json.dumps(tout, ensure_ascii=False), encoding="utf-8")
    print("ÉCRIT " + SORTIE.name + " : " + ", ".join(f"{k} {len(v)}" for k, v in tout.items()))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter([a.lower() for a in sys.argv[1:]] or None)
