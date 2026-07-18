"""Géo-recherche Wikipédia GÉNÉRALISÉE (règle qualité v75) : pour chaque
point SANS photo d'un pays, cherche l'article le plus proche (rayon par
catégorie, langue du pays) et ne le retient que s'il partage un mot (≥ 4
lettres) avec le nom du point OU s'il est à < 150 m — anti-homonyme.
Ajoute photo (960 px), lien Wikipédia et description manquante.

⚠️ N'écrit PAS data/<iso>/points.geojson directement (écrasé au rebuild) :
alimente le cache tools/geosearch-<iso>.json que construire_pays.py rejoue
au build (clé « nom|lat4 », comme pays-wiki-<iso>.json). Pour la FRANCE
(hors construire_pays), écrit directement data/points.geojson.

Usage : python tools/enrichir_geosearch_pays.py ch nz lu [--ecrire]
"""

import json
import math
import re
import sys
import time
import unicodedata
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from recolter_categories_v72 import RACINE, _http  # noqa: E402

LANGUES = {"fr": "fr", "ch": "fr", "it": "it", "es": "es", "pt": "pt",
           "de": "de", "nl": "nl", "lu": "fr", "be": "fr", "nz": "en"}
FICHIER = {"fr": "data/points.geojson"}
RAYON_DEFAUT = 300
RAYONS = {"chateau": 500, "cathedrale": 500, "cite-caractere": 900, "culture": 250,
          "lac": 900, "cascade": 400, "grotte": 300, "refuge": 400, "camping": 200,
          "via-ferrata": 400, "randonnee": 500, "village-abandonne": 800}
# catégories exclues : trop denses/anonymes pour la géo-recherche
EXCLUES = {"toilettes", "eau", "escalade", "canyon", "autre"}


def _mots(texte):
    t = unicodedata.normalize("NFD", (texte or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return {m for m in re.split(r"[^a-z0-9]+", t) if len(m) >= 4}


def geosearch(lang, lat, lon, rayon):
    q = urllib.parse.urlencode({
        "action": "query", "format": "json", "formatversion": "2",
        "generator": "geosearch", "ggscoord": f"{lat}|{lon}",
        "ggsradius": rayon, "ggslimit": 1,
        "prop": "coordinates|pageimages|extracts", "colimit": "max",
        "piprop": "thumbnail", "pithumbsize": 960,
        "exintro": 1, "explaintext": 1, "exsentences": 1,
    })
    d = _http(f"https://{lang}.wikipedia.org/w/api.php?{q}")
    pages = (d.get("query") or {}).get("pages", [])
    return pages[0] if pages else None


def traiter(iso, ecrire):
    lang = LANGUES[iso]
    chemin = RACINE / FICHIER.get(iso, f"data/{iso}/points.geojson")
    d = json.loads(chemin.read_text(encoding="utf-8"))
    cache_chemin = RACINE / "tools" / f"geosearch-{iso}.json"
    cache = json.loads(cache_chemin.read_text(encoding="utf-8")) if cache_chemin.exists() else {}
    cibles = [f for f in d["features"]
              if not f["properties"].get("photos") and f["properties"]["theme"] not in EXCLUES]
    print(f"{iso}: {len(cibles)} points sans photo à géo-chercher ({lang}.wikipedia)", flush=True)
    n_ok = n_appels = 0
    for f in cibles:
        p = f["properties"]
        lat = f["geometry"]["coordinates"][1]
        lon = f["geometry"]["coordinates"][0]
        cle = f'{p["name"]}|{round(lat, 4)}'
        if cle in cache:
            resultat = cache[cle]  # déjà cherché : accepté ({photo,url,desc}) ou null
        else:
            page = geosearch(lang, lat, lon, RAYONS.get(p["theme"], RAYON_DEFAUT))
            n_appels += 1
            resultat = None
            if page:
                # garde anti-homonyme AVANT mise en cache : le cache ne contient
                # que des résultats SÛRS, prêts à rejouer (construire_pays)
                coord = (page.get("coordinates") or [{}])[0]
                dist = 99999
                if coord and coord.get("lat") is not None:
                    dx = (coord["lon"] - lon) * math.cos(math.radians(lat)) * 111320
                    dy = (coord["lat"] - lat) * 111320
                    dist = (dx * dx + dy * dy) ** 0.5
                if dist < 150 or (_mots(page["title"]) & _mots(p["name"])):
                    th = (page.get("thumbnail") or {}).get("source", "")
                    resultat = {
                        "url": f"https://{lang}.wikipedia.org/wiki/" +
                               urllib.parse.quote(page["title"].replace(" ", "_")),
                        "photo": th if th.startswith("https://upload.wikimedia.org") else "",
                        "desc": (page.get("extract") or "").strip()[:300],
                    }
            cache[cle] = resultat
            if n_appels % 300 == 0:
                cache_chemin.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                print(f"  … {n_appels} appels, {n_ok} retenus", flush=True)
            time.sleep(0.3)
        if not resultat:
            continue
        if resultat.get("photo"):
            p["photos"] = [resultat["photo"]]
        if not any("Wikipédia" in l["label"] for l in p.get("links", [])):
            p.setdefault("links", []).insert(0, {"label": "🔗 Wikipédia", "url": resultat["url"]})
        if not (p.get("description") or "").strip() and resultat.get("desc"):
            p["description"] = resultat["desc"]
        if p.get("details", {}).get("fiche") == "À vérifier":
            p["details"]["fiche"] = "Référencé"
        n_ok += 1
    cache_chemin.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    print(f"{iso}: {n_ok} points enrichis ({n_appels} nouveaux appels)", flush=True)
    if ecrire:
        if iso == "fr":
            chemin.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"  ÉCRIT {chemin.name}")
        else:
            # les fichiers pays sont reconstruits par construire_pays : lui seul
            # écrit — il rejouera tools/geosearch-<iso>.json au prochain build
            print(f"  (cache geosearch-{iso}.json prêt — appliquer via construire_pays.py --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    args = [a.lower() for a in sys.argv[1:] if not a.startswith("--")]
    for iso in (args or ["ch"]):
        traiter(iso, "--ecrire" in sys.argv)
