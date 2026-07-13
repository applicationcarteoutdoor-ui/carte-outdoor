# -*- coding: utf-8 -*-
"""
Récolte Wikipédia EN pour la Nouvelle-Zélande : arbres de catégories
« Caves of New Zealand » et « Cathedrals in New Zealand » → articles
géolocalisés + photo (pageimages, hébergée sur upload.wikimedia.org — le seul
hôte d'images autorisé par la CSP). FAITS + lien + photo Commons seulement.

Même méthode (et mêmes pièges payés) que la France :
  - sous-catégories suivies SEULEMENT si leur nom contient le mot-clé, sinon
    le parcours dérive hors sujet ;
  - `colimit=max` + suivi de `continue` OBLIGATOIRES sur prop=coordinates
    (sinon 10 coordonnées par réponse, 80 % silencieusement perdues).

Lancer :  python tools/recolter_nz_wikipedia.py
Sortie   :  tools/nz-wikipedia.json
"""

import json
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "nz-wikipedia.json"
API = "https://en.wikipedia.org/w/api.php"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE

ARBRES = {
    "grottes": ("Category:Caves of New Zealand", "cave"),
    "cathedrales": ("Category:Cathedrals in New Zealand", "cathedral"),
}


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    for ctx in (CTX, CTX_NV):
        for attente in (0, 15, 60):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60, context=ctx) as r:
                    return json.load(r)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Wikipédia injoignable")


def membres_categorie(cat, motcle, vues=None, profondeur=0):
    """Pages de l'arbre de catégorie (sous-catégories suivies si nom à mot-clé)."""
    vues = vues if vues is not None else set()
    if cat in vues or profondeur > 3:
        return []
    vues.add(cat)
    pages, cont = [], {}
    while True:
        d = _get({"action": "query", "list": "categorymembers", "cmtitle": cat,
                  "cmlimit": "max", "format": "json", **cont})
        for m in d.get("query", {}).get("categorymembers", []):
            if m["ns"] == 0:
                pages.append(m["title"])
            elif m["ns"] == 14 and motcle in m["title"].lower():
                pages.extend(membres_categorie(m["title"], motcle, vues, profondeur + 1))
        cont = d.get("continue") or {}
        if not cont:
            break
    return pages


def coordonnees_photos(titres):
    """{titre: {lat, lon, photo}} par lots de 50 — colimit=max + continue."""
    infos = {}
    for i in range(0, len(titres), 50):
        lot = titres[i:i + 50]
        cont = {}
        while True:
            d = _get({"action": "query", "titles": "|".join(lot), "prop": "coordinates|pageimages",
                      "colimit": "max", "piprop": "thumbnail", "pithumbsize": "640",
                      "redirects": 1, "format": "json", **cont})
            for p in d.get("query", {}).get("pages", {}).values():
                t = p.get("title")
                if not t:
                    continue
                e = infos.setdefault(t, {})
                if p.get("coordinates"):
                    e["lat"] = round(p["coordinates"][0]["lat"], 6)
                    e["lon"] = round(p["coordinates"][0]["lon"], 6)
                thumb = (p.get("thumbnail") or {}).get("source", "")
                if thumb.startswith("https://upload.wikimedia.org"):
                    e["photo"] = thumb
            cont = d.get("continue") or {}
            if not cont:
                break
        print(f"  coordonnées {min(i + 50, len(titres))}/{len(titres)}", flush=True)
        time.sleep(0.5)
    return infos


def recolter():
    donnees = {}
    for cle, (cat, motcle) in ARBRES.items():
        titres = sorted(set(membres_categorie(cat, motcle)))
        print(f"{cle}: {len(titres)} articles dans l'arbre", flush=True)
        infos = coordonnees_photos(titres)
        objs = []
        for t in titres:
            e = infos.get(t, {})
            if "lat" not in e:
                continue  # article sans coordonnées : inutilisable pour la carte
            objs.append({
                "titre": t,
                "lat": e["lat"], "lon": e["lon"],
                "photo": e.get("photo", ""),
                "url": "https://en.wikipedia.org/wiki/" + urllib.parse.quote(t.replace(" ", "_")),
            })
        donnees[cle] = objs
        print(f"{cle}: {len(objs)} géolocalisés ({sum(1 for o in objs if o['photo'])} photos)", flush=True)
    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    print(f"ÉCRIT -> {SORTIE.name}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
