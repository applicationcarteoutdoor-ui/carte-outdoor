# -*- coding: utf-8 -*-
"""
Recalage GPS de la catégorie « chateau » (en place, ids stables).

Constat : les 810 châteaux sont TOUS au centroïde de commune (« Position au
centre de la commune »). 543 ont déjà un lien Wikipédia confirmé → l'article
porte la VRAIE position du château. On la récupère (prop=coordinates) et on
recale — avec un garde-fou : ne recaler que si l'article est à < 20 km du
centroïde (sinon le lien est douteux : deux châteaux homonymes pointant le même
article, cf. ch-0008 à 100 km). Repli Wikidata P625 pour les articles sans
coordonnées. Photo Wikimedia récupérée au passage si manquante.

FAITS réutilisables (coordonnées, image Commons) — jamais de prose recopiée.

Lancer :  python tools/recaler_chateaux.py            (simulation)
          python tools/recaler_chateaux.py --ecrire   (écrit points.geojson)
"""

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CIBLE = DOSSIER.parent / "data" / "points.geojson"
CACHE = DOSSIER / "chateaux-wiki-coords.json"     # titre → {lat, lon, qid, thumb} | null
CACHE_WD = DOSSIER / "chateaux-wikidata-coords.json"  # qid → {lat, lon} | null
CACHE_RG = DOSSIER / "chateaux-revgeo.json"       # "lat,lon" → {dep, commune} | null
API_WIKI = "https://fr.wikipedia.org/w/api.php"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}

GARDE_KM = 20.0        # écart centroïde ↔ article : en deçà, on recale en confiance
RE_CENTRE = re.compile(r"\s*\(Position au centre de la commune\.?\)", re.I)
RE_DESC_DEP = re.compile(r"Commune\s*:\s*([^()]+?)\s*\(([\dAB]+)\)")
# « … en Maine-et-Loire », « … dans le Gard », « … dans les Yvelines »,
# « … dans l'Eure » (pas d'espace après l' : d'où \s*).
RE_NOM_DEP = re.compile(r"\b(?:en\s+|dans\s+(?:l['’]\s*|les?\s+|la\s+))([A-Za-zÀ-ÿ'’ -]+)$")


def _norm(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t.lower())


DEP_NOM_VERS_CODE = {_norm(d["nom"]): d["code"]
                     for d in json.loads((DOSSIER / "departements.json").read_text(encoding="utf-8"))}


def dep_du_nom(name):
    """Département cité dans le nom (« … en Maine-et-Loire ») → code, ou None."""
    m = RE_NOM_DEP.search(name or "")
    return DEP_NOM_VERS_CODE.get(_norm(m.group(1))) if m else None


def dep_desc(desc):
    """(commune, code département) depuis « Commune : X (NN) »."""
    m = RE_DESC_DEP.search(desc or "")
    return (m.group(1).strip(), m.group(2)) if m else (None, None)


def revgeo(lat, lon):
    """Géocodage inverse geo.api.gouv.fr → {dep, commune} | None (hors France)."""
    cache = json.loads(CACHE_RG.read_text(encoding="utf-8")) if CACHE_RG.exists() else {}
    cle = f"{lat:.4f},{lon:.4f}"
    if cle not in cache:
        try:
            url = ("https://geo.api.gouv.fr/communes?" + urllib.parse.urlencode(
                {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}",
                 "fields": "nom,codeDepartement", "format": "json"}))
            d = http_json(url)
            cache[cle] = ({"dep": d[0]["codeDepartement"], "commune": d[0]["nom"]}
                          if d else None)
        except Exception as exc:
            print(f"    ! revgeo {cle} : {exc}")
            return "ERREUR"  # pas mis en cache : retenté au prochain run
        CACHE_RG.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        time.sleep(0.12)
    return cache[cle]


def hav(lat1, lon1, lat2, lon2):
    R = 6371000
    dla, dlo = radians(lat2 - lat1), radians(lon2 - lon1)
    x = sin(dla / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlo / 2) ** 2
    return R * 2 * atan2(sqrt(x), sqrt(1 - x))


def titre_de_lien(url):
    m = re.search(r"/wiki/([^#?]+)", url or "")
    if not m:
        return None
    return urllib.parse.unquote(m.group(1)).replace("_", " ").strip()


def http_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)


def fetch_coords_wiki(titres):
    """{titre demandé : {lat, lon, qid, thumb} | None}. Lots de 50, colimit=max
    + suivi de continue (sinon 10 coord/réponse), cache incrémental."""
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    a_faire = [t for t in dict.fromkeys(titres) if "t:" + t not in cache]
    if a_faire:
        print(f"  Wikipédia : coordonnées de {len(a_faire)} articles château…")
    for i in range(0, len(a_faire), 50):
        lot = a_faire[i:i + 50]
        base = {"action": "query", "format": "json", "redirects": "1",
                "prop": "coordinates|pageprops|pageimages",
                "colimit": "max", "ppprop": "wikibase_item|disambiguation",
                "piprop": "thumbnail", "pithumbsize": "400", "pilimit": "max",
                "titles": "|".join(lot)}
        pages, corresp, cont = {}, {}, {}
        for _ in range(12):
            try:
                d = http_json(API_WIKI + "?" + urllib.parse.urlencode({**base, **cont}))
            except Exception as exc:
                print(f"    ! {exc} — pause 20 s"); time.sleep(20); continue
            q = d.get("query", {})
            for n in q.get("normalized", []) + q.get("redirects", []):
                corresp.setdefault(n["to"], n["from"])
            for pid, page in (q.get("pages") or {}).items():
                fusion = pages.setdefault(pid, {})
                for k, v in page.items():
                    fusion.setdefault(k, v)
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items() if k != "continue"}
            time.sleep(0.3)

        def origine(t):
            vus = set()
            while t in corresp and t not in vus:
                vus.add(t); t = corresp[t]
            return t

        for page in pages.values():
            o = origine(page.get("title", ""))
            pp = page.get("pageprops") or {}
            if "missing" in page or "disambiguation" in pp:
                cache["t:" + o] = None
                continue
            co = (page.get("coordinates") or [{}])[0]
            cache["t:" + o] = {
                "lat": co.get("lat"), "lon": co.get("lon"),
                "qid": pp.get("wikibase_item"),
                "thumb": (page.get("thumbnail") or {}).get("source", ""),
            }
        for t in lot:
            cache.setdefault("t:" + t, None)
        CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 50, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.4)
    return cache


def fetch_coords_wikidata(qids):
    """{qid : {lat, lon} | None} via P625, lots de 50, cache incrémental."""
    cache = json.loads(CACHE_WD.read_text(encoding="utf-8")) if CACHE_WD.exists() else {}
    a_faire = [q for q in dict.fromkeys(qids) if q and q not in cache]
    if a_faire:
        print(f"  Wikidata : P625 de {len(a_faire)} entités…")
    for i in range(0, len(a_faire), 50):
        lot = a_faire[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
               "&props=claims&ids=" + "|".join(lot))
        try:
            d = http_json(url)
        except Exception as exc:
            print(f"    ! wikidata : {exc}"); break
        for q, ent in (d.get("entities") or {}).items():
            claims = (ent.get("claims") or {}).get("P625") or []
            val = (claims[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                   if claims else None)
            cache[q] = {"lat": val["latitude"], "lon": val["longitude"]} if val else None
        CACHE_WD.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 50, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.4)
    return cache


def main(ecrire=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    ch = [f for f in d["features"] if f["properties"].get("theme") == "chateau"]
    lies = [f for f in ch if f["properties"].get("link")]
    print(f"chateaux : {len(ch)} | avec lien : {len(lies)}")

    titres = {}   # feature id → titre
    for f in lies:
        t = titre_de_lien(f["properties"]["link"])
        if t:
            titres[f["properties"]["id"]] = t
    cache = fetch_coords_wiki(list(titres.values()))

    # Repli Wikidata pour les articles SANS coordonnée mais avec QID
    qids = []
    for f in lies:
        t = titres.get(f["properties"]["id"])
        pg = cache.get("t:" + t) if t else None
        if pg and pg.get("lat") is None and pg.get("qid"):
            qids.append(pg["qid"])
    wd = fetch_coords_wikidata(qids)

    def poser(f, nlat, nlon):
        f["geometry"]["coordinates"] = [round(nlon, 6), round(nlat, 6)]

    st = {"recale_proche": 0, "recale_dep": 0, "recale_wd": 0, "delie": 0,
          "indetermine": 0, "photo": 0, "sans_coord": 0}
    for f in lies:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2]
        t = titres.get(p["id"])
        pg = cache.get("t:" + t) if t else None
        if not pg:
            st["sans_coord"] += 1
            continue
        nlat, nlon, src = pg.get("lat"), pg.get("lon"), "wiki"
        if nlat is None and pg.get("qid") and wd.get(pg["qid"]):
            nlat, nlon, src = wd[pg["qid"]]["lat"], wd[pg["qid"]]["lon"], "wd"
        if nlat is None:
            st["sans_coord"] += 1
            continue

        def enrichir_photo():
            if not p.get("photos") and (pg.get("thumb") or "").startswith("https://upload.wikimedia.org"):
                p["photos"] = [pg["thumb"]]; st["photo"] += 1

        dkm = hav(lat, lon, nlat, nlon) / 1000
        if dkm <= GARDE_KM:
            # le centroïde corrobore : article dans/près de la commune → recaler
            poser(f, nlat, nlon)
            p["description"] = RE_CENTRE.sub("", p.get("description", "")).strip()
            enrichir_photo()
            st["recale_wd" if src == "wd" else "recale_proche"] += 1
            continue

        # Hors garde-fou : le centroïde est peut-être FAUX (géocodé sur une
        # commune homonyme d'un autre département). On tranche par le
        # département : géocodage inverse de l'article, comparé au département
        # cité dans le nom ET au code de la description.
        rg = revgeo(nlat, nlon)
        if rg == "ERREUR":
            st["indetermine"] += 1
            continue
        rg_dep = rg["dep"] if rg else None
        name_dep = dep_du_nom(p["name"])
        _, desc_dep = dep_desc(p.get("description"))
        if rg_dep and (rg_dep == name_dep or rg_dep == desc_dep):
            # article dans le bon département : centroïde faux → recaler et
            # corriger la ligne « Commune » (elle pointait un homonyme).
            poser(f, nlat, nlon)
            nd = RE_CENTRE.sub("", p.get("description", ""))
            nd = RE_DESC_DEP.sub(f"Commune : {rg['commune']} ({rg['dep']})", nd).strip()
            p["description"] = nd
            enrichir_photo()
            st["recale_dep"] += 1
        elif rg is None or (name_dep and rg_dep and rg_dep != name_dep):
            # article à l'ÉTRANGER, ou dans un département différent de celui
            # cité dans le NOM (signal éditorial fiable) = lien erroné
            # (homonyme). On délie : lien + photo retirés, fiche à revérifier.
            p["link"] = ""
            p["photos"] = []
            p.setdefault("details", {})["fiche"] = "À vérifier"
            st["delie"] += 1
        else:
            # incertain (département du nom illisible, pas de correspondance
            # nette sans certitude d'erreur) : on ne touche à rien.
            st["indetermine"] += 1

    recale = st["recale_proche"] + st["recale_dep"] + st["recale_wd"]
    print(f"\nRecalés : {recale} "
          f"(proche {st['recale_proche']} + dépt-validé {st['recale_dep']} + Wikidata {st['recale_wd']}) "
          f"| photos ajoutées : {st['photo']}")
    print(f"Liens erronés déliés (homonymes) : {st['delie']} | "
          f"indéterminés (revgeo échoué) : {st['indetermine']} | sans coordonnée : {st['sans_coord']}")
    reste = len(ch) - recale
    print(f"Restent au centroïde : {reste} "
          f"({len(ch) - len(lies)} jamais liés + {st['delie']} déliés + {st['indetermine'] + st['sans_coord']} sans coord)")

    if ecrire:
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT. {CIBLE.stat().st_size // 1024} Ko")
    else:
        print("(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    main(ecrire="--ecrire" in sys.argv)
