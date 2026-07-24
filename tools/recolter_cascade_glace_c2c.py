# -*- coding: utf-8 -*-
"""
Récolte des CASCADES DE GLACE (escalade sur glace) depuis Camp to Camp.

⚠️ OpenStreetMap est INUTILISABLE pour cette catégorie : l'union des tags
`climbing:ice=yes` + `sport=ice_climbing` ne donne que 47 objets pour nos
10 pays (FR 6, CH 3, IT 36, ES 1, 0 ailleurs), dont un seul coté. Camp to
Camp en recense 2 408 dans le monde, ~2 060 chez nous, 100 % géolocalisés et
nommés, 87 % avec cotation glace. C'est donc la source principale.

LICENCE — Camp to Camp est en CC-BY-SA. Règle projet déjà appliquée à
l'escalade : on reprend les FAITS (nom, coordonnées, cotation WI, cotation
mixte, hauteur, altitude, orientation, durée, nombre de voies) et JAMAIS les
descriptions rédigées (`locales[].summary`) ni les photos. Un lien vers la
fiche source remplace la prose ; attribution dans « Sources des données ».
Les photos C2C vivent d'ailleurs sur media.camptocamp.org, absent de la
directive img-src de la CSP : elles seraient bloquées silencieusement.

REGROUPEMENT : plusieurs voies partagent souvent la même cascade (épingles
empilées). On regroupe à 300 m en SITES ; la voie la mieux renseignée donne
le nom et le lien, les cotations sont agrégées (max) et le nombre de voies
est conservé.

Lancer :  python tools/recolter_cascade_glace_c2c.py
Sortie :  tools/cascade-glace-c2c.json  (par pays, rejoué à l'intégration)
"""

import json
import math
import sys
import time
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle; contact bidband4@gmail.com)"}
API = "https://api.camptocamp.org/routes?act=ice_climbing&limit=100&offset={}"

# Titre ANGLAIS de la zone Camp to Camp -> iso du pays de l'app
PAYS_C2C = {
    "France": "fr", "Switzerland": "ch", "Italy": "it", "Spain": "es",
    "Portugal": "pt", "Germany": "de", "Netherlands": "nl",
    "Luxembourg": "lu", "Belgium": "be", "New Zealand": "nz",
}
REGROUPEMENT_M = 300
QUALITE = {"great": 4, "fine": 3, "medium": 2, "draft": 1}
# cotations glace WI, de la plus facile à la plus dure (pour agréger un max)
ORDRE_GLACE = ["1", "2", "2+", "3", "3+", "4", "4+", "5", "5+", "6", "6+", "7", "7+"]


def _http(url, essais=4):
    for i in range(essais):
        try:
            r = urllib.request.Request(url, headers=UA)
            return json.load(urllib.request.urlopen(r, timeout=180))
        except Exception as e:
            print(f"  (réseau occupé, pause {10 * (i + 1)} s… {str(e)[:70]})", flush=True)
            time.sleep(10 * (i + 1))
    return {}


def merc_vers_latlon(x, y):
    """Camp to Camp stocke en EPSG:3857 (Web Mercator) — jamais en lat/lon."""
    lon = x / 20037508.34 * 180.0
    lat = y / 20037508.34 * 180.0
    lat = 180.0 / math.pi * (2.0 * math.atan(math.exp(lat * math.pi / 180.0)) - math.pi / 2.0)
    return lat, lon


def hav_m(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def pays_de(doc):
    """Pays via les zones C2C (titre anglais) — autoritaire, pas de test
    géométrique approximatif aux frontières."""
    for a in doc.get("areas") or []:
        for loc in a.get("locales") or []:
            if loc.get("lang") == "en" and loc.get("title") in PAYS_C2C:
                return PAYS_C2C[loc["title"]]
    return None


def telecharger():
    """Toutes les voies de glace, paginées."""
    cache = DOSSIER / "cascade-glace-c2c-brut.json"
    if cache.exists():
        docs = json.loads(cache.read_text(encoding="utf-8"))
        print(f"brut déjà en cache : {len(docs)} voies", flush=True)
        return docs
    docs, offset = [], 0
    while True:
        d = _http(API.format(offset))
        lot = d.get("documents") or []
        if not lot:
            break
        docs.extend(lot)
        total = d.get("total") or 0
        print(f"  {len(docs)}/{total} voies", flush=True)
        offset += 100
        if offset >= total:
            break
        time.sleep(0.5)
    cache.write_text(json.dumps(docs, ensure_ascii=False), encoding="utf-8")
    return docs


def voie_utile(doc):
    """Extrait les FAITS d'une voie (jamais le summary : CC-BY-SA)."""
    g = doc.get("geometry") or {}
    try:
        geom = json.loads(g.get("geom") or "{}")
        x, y = geom["coordinates"][0], geom["coordinates"][1]
    except Exception:
        return None
    lat, lon = merc_vers_latlon(x, y)
    titre = ""
    for loc in doc.get("locales") or []:
        if loc.get("title"):
            titre = loc["title"].strip()
            break
    if not titre:
        return None
    return {
        "id": doc["document_id"],
        "nom": titre,
        "lat": round(lat, 6),
        "lon": round(lon, 6),
        "pays": pays_de(doc),
        "glace": doc.get("ice_rating"),
        "mixte": doc.get("mixed_rating"),
        "global": doc.get("global_rating"),
        "engagement": doc.get("engagement_rating"),
        "orientations": doc.get("orientations") or [],
        "hauteur": doc.get("height_diff_difficulties"),
        "altitude": doc.get("elevation_max"),
        "durees": doc.get("durations") or [],
        "qualite": QUALITE.get(doc.get("quality"), 0),
    }


def cote_max(valeurs):
    connues = [v for v in valeurs if v in ORDRE_GLACE]
    return max(connues, key=ORDRE_GLACE.index) if connues else None


def regrouper(voies):
    """Regroupe les voies proches en SITES (une cascade porte souvent
    plusieurs voies) — la mieux renseignée donne nom et lien."""
    sites = []
    for v in sorted(voies, key=lambda v: (-v["qualite"], v["nom"])):
        proche = None
        for s in sites:
            if hav_m(v["lat"], v["lon"], s["lat"], s["lon"]) <= REGROUPEMENT_M:
                proche = s
                break
        if proche:
            proche["voies"].append(v)
        else:
            sites.append({"lat": v["lat"], "lon": v["lon"], "voies": [v]})

    sortie = []
    for s in sites:
        vs = s["voies"]
        chef = vs[0]  # déjà le mieux renseigné (tri ci-dessus)
        orientations = sorted({o for v in vs for o in v["orientations"]})
        hauteurs = [v["hauteur"] for v in vs if isinstance(v["hauteur"], (int, float))]
        altitudes = [v["altitude"] for v in vs if isinstance(v["altitude"], (int, float))]
        sortie.append({
            "id_c2c": chef["id"],
            "nom": chef["nom"],
            "lat": chef["lat"],
            "lon": chef["lon"],
            "pays": chef["pays"],
            "nb_voies": len(vs),
            "glace": cote_max([v["glace"] for v in vs]),
            "mixte": cote_max([str(v["mixte"] or "").replace("M", "") for v in vs]),
            "global": chef["global"],
            "engagement": chef["engagement"],
            "orientations": orientations,
            "hauteur": max(hauteurs) if hauteurs else None,
            "altitude": max(altitudes) if altitudes else None,
            "durees": chef["durees"],
        })
    return sortie


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    docs = telecharger()
    voies = [v for v in (voie_utile(d) for d in docs) if v]
    retenues = [v for v in voies if v["pays"]]
    print(f"{len(docs)} voies brutes → {len(voies)} exploitables → "
          f"{len(retenues)} dans les 10 pays de l'app")

    par_pays = {}
    for v in retenues:
        par_pays.setdefault(v["pays"], []).append(v)

    resultat = {}
    for iso, vs in sorted(par_pays.items()):
        sites = regrouper(vs)
        resultat[iso] = sites
        cotees = sum(1 for s in sites if s["glace"])
        print(f"  {iso}: {len(vs)} voies → {len(sites)} sites ({cotees} cotés)")

    (DOSSIER / "cascade-glace-c2c.json").write_text(
        json.dumps(resultat, ensure_ascii=False), encoding="utf-8")
    print(f"ÉCRIT tools/cascade-glace-c2c.json — {sum(len(v) for v in resultat.values())} sites")
