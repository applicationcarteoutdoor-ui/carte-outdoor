"""Normalise les vignettes Wikimedia aux tailles ACCEPTÉES (500/960/1280).

Depuis 2025, Wikimedia ne sert plus que des tailles de vignettes normalisées :
/280px-, /640px-, /800px-… répondent HTTP 400. Ce script trouve toutes les
photos /NNNpx- hors liste blanche, interroge l'API Commons (largeur de
l'original, par lots de 50 — JAMAIS de rafale de HEAD : 429 silencieux) et
réécrit chaque URL vers la plus grande taille sûre ≤ l'original ; si
l'original est plus petit que 500 px, l'URL de l'ORIGINAL (sans /thumb) est
utilisée — toujours valide.

Usage : python tools/normaliser_vignettes.py [--ecrire]
"""

import json
import re
import sys
import urllib.parse
import urllib.request

FICHIERS = [
    "data/points.geojson", "data/culture.geojson",
    "data/ch/points.geojson", "data/it/points.geojson", "data/es/points.geojson",
    "data/nz/points.geojson",
]
TAILLES_SURES = (1280, 960, 500)
RX_THUMB = re.compile(r"^(https://upload\.wikimedia\.org/wikipedia/[^/]+)/thumb/(.+)/(\d+)px-([^/?#]+)$")

API = "https://commons.wikimedia.org/w/api.php"


def largeur_originaux(titres):
    """{titre_fichier: largeur} via l'API Commons, par lots de 50."""
    largeurs = {}
    for i in range(0, len(titres), 50):
        lot = titres[i:i + 50]
        params = urllib.parse.urlencode({
            "action": "query", "format": "json", "formatversion": "2",
            "titles": "|".join(f"File:{t}" for t in lot),
            "prop": "imageinfo", "iiprop": "size",
        })
        req = urllib.request.Request(f"{API}?{params}", headers={
            "User-Agent": "SpotMap/1.0 (normalisation vignettes; contact bidband4@gmail.com)"})
        d = json.load(urllib.request.urlopen(req, timeout=60))
        for page in d.get("query", {}).get("pages", []):
            info = (page.get("imageinfo") or [{}])[0]
            if info.get("width"):
                largeurs[page["title"].removeprefix("File:")] = info["width"]
    return largeurs


def corriger(url, largeurs):
    m = RX_THUMB.match(url)
    if not m:
        return url
    base, chemin, taille, fichier = m.group(1), m.group(2), int(m.group(3)), m.group(4)
    if taille in TAILLES_SURES:
        return url
    nom = urllib.parse.unquote(fichier).replace("_", " ")
    largeur = largeurs.get(nom)
    if largeur:
        for t in TAILLES_SURES:
            if t <= largeur:
                return f"{base}/thumb/{chemin}/{t}px-{fichier}"
    # original plus petit que 500 px (ou largeur inconnue) : l'original direct
    return f"{base}/{chemin}"


def main():
    ecrire = "--ecrire" in sys.argv
    # 1. recenser les vignettes hors liste blanche
    a_verifier = set()
    for f in FICHIERS:
        d = json.load(open(f, encoding="utf-8"))
        for feat in d["features"]:
            for url in feat["properties"].get("photos") or []:
                m = RX_THUMB.match(url)
                if m and int(m.group(3)) not in TAILLES_SURES:
                    a_verifier.add(urllib.parse.unquote(m.group(4)).replace("_", " "))
    print(f"{len(a_verifier)} fichiers image à vérifier via l'API Commons")
    largeurs = largeur_originaux(sorted(a_verifier)) if a_verifier else {}

    # 2. réécrire
    for f in FICHIERS:
        d = json.load(open(f, encoding="utf-8"))
        n = 0
        for feat in d["features"]:
            photos = feat["properties"].get("photos") or []
            nouvelles = [corriger(u, largeurs) for u in photos]
            if nouvelles != photos:
                feat["properties"]["photos"] = nouvelles
                n += 1
        if n and ecrire:
            json.dump(d, open(f, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
        print(f"{f} : {n} point(s) corrigé(s){' (écrit)' if n and ecrire else ''}")


if __name__ == "__main__":
    main()
