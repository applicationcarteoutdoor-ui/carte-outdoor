# -*- coding: utf-8 -*-
"""
Contrôle qualité des spots de saut dans l'eau récoltés hors OSM (forums,
vidéos, blogs) — v82.

Ces spots viennent de sources humaines : le risque n'est pas la licence
(on ne garde que les FAITS + le lien), c'est la POSITION INVENTÉE. Un point
de saut placé au hasard est pire qu'absent : il envoie quelqu'un sauter là
où il n'y a pas d'eau. Chaque coordonnée est donc confrontée à OSM.

Trois contrôles, tous éliminatoires :
  1. EAU À PROXIMITÉ — une étendue d'eau (rivière, lac, mer, réservoir) doit
     exister à moins de RAYON_EAU mètres, sinon le point est rejeté.
  2. LIEN VALIDE — la source doit répondre (HTTP < 400).
  3. DOUBLON — deux spots à moins de 200 m sont fusionnés.

Les spots marqués `precision_coords = "incertaine"` sont écartés d'office.

⚠️ Les INTERDICTIONS et les ACCIDENTS ne sont PAS des motifs de rejet
(décision utilisateur v82) : le spot est conservé et l'information est
AFFICHÉE dans sa fiche. Masquer un site n'empêche personne d'y aller — un
utilisateur qui lit « baignade interdite par arrêté, 24 noyades depuis 1983 »
est bien mieux protégé qu'un utilisateur à qui l'on ne montre rien.
Ces contrôles-ci ne portent donc que sur la FIABILITÉ de la position, jamais
sur ce qu'il est permis ou raisonnable d'y faire.

Lancer : python tools/verifier_spots_saut.py <fichier-brut.json> [--ecrire]
Sortie  : tools/spots-saut-verifies.json
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
RAYON_EAU = 150      # m : au-delà, la position ne décrit plus le plan d'eau
FUSION_M = 200       # m : même spot décrit par deux sources
CACHE = DOSSIER / "spots-saut-cache-eau.json"


def _post(corps):
    data = ("data=" + urllib.parse.quote(corps)).encode("utf-8")
    for ep in ENDPOINTS:
        for att in (0, 20, 60):
            if att:
                time.sleep(att)
            try:
                req = urllib.request.Request(ep, data=data, headers=UA)
                with urllib.request.urlopen(req, timeout=180, context=CTX) as r:
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code in (429, 504):
                    continue
                break
            except Exception:
                continue
    return None


def hav_m(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def eau_a_proximite(lat, lon, cache):
    """Vrai s'il existe une étendue d'eau à moins de RAYON_EAU mètres."""
    cle = f"{round(lat, 5)}|{round(lon, 5)}"
    if cle in cache:
        return cache[cle]
    # ⚠️ `around` mesure la distance à la GÉOMÉTRIE (rive, berge), pas à la
    # surface : au centre d'un grand lac il ne trouve rien. Sans importance
    # ici — un spot de saut est toujours AU BORD — mais à savoir avant de
    # réutiliser cette fonction ailleurs.
    # Les bassins d'agrément, fontaines et bassins de traitement sont EXCLUS :
    # sinon une place de centre-ville avec un miroir d'eau validerait une
    # coordonnée inventée (constaté sur la place Bellecour à Lyon).
    exclus = '["water"!~"^(pond|basin|reflecting_pool|wastewater|fountain)$"]'
    req = (
        f'[out:json][timeout:120];('
        f'nwr(around:{RAYON_EAU},{lat},{lon})["natural"="water"]{exclus}["fountain"!~"."];'
        f'nwr(around:{RAYON_EAU},{lat},{lon})["waterway"~"^(river|stream|riverbank|canal|waterfall)$"];'
        f'nwr(around:{RAYON_EAU},{lat},{lon})["natural"="coastline"];'
        f'nwr(around:{RAYON_EAU},{lat},{lon})["landuse"="reservoir"];'
        f');out count;'
    )
    d = _post(req)
    if d is None:
        return None  # réseau : on ne tranche pas, on retentera
    total = 0
    for e in d.get("elements", []):
        if e.get("type") == "count":
            total = int(e.get("tags", {}).get("total", 0))
    cache[cle] = total > 0
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    time.sleep(1.0)
    return cache[cle]


# Codes qui signalent un BLOCAGE ANTI-ROBOT et non une page absente : la
# ressource existe, c'est notre requête automatisée qui est refusée. Les
# rejeter ferait perdre de très bonnes sources institutionnelles — mesuré sur
# stadt-zuerich.ch (Flussbad Oberer Letten) et ge.ch (Pont Sous-Terre), deux
# spots de saut officiels et documentés.
ANTI_ROBOT = {401, 403, 405, 406, 409, 418, 429, 500, 503}
MORTS = {404, 410}


def lien_valide(url):
    if not isinstance(url, str) or not url.startswith("http"):
        return False
    # ⚠️ Le repli sur un contexte SSL non vérifiant n'est pas une coquetterie :
    # ce poste ne valide pas les certificats de plusieurs sites publics suisses
    # (stadt-zuerich.ch, ge.ch), ce qui faisait rejeter d'excellentes sources
    # officielles. On ne fait que constater l'EXISTENCE d'une page, aucune
    # donnée n'est transmise — le même repli existe dans recolter_pays_osm.py.
    for ctx in (CTX, CTX_NV):
        for methode in ("HEAD", "GET"):
            try:
                req = urllib.request.Request(url, headers=UA, method=methode)
                with urllib.request.urlopen(req, timeout=25, context=ctx) as r:
                    return r.status < 400
            except urllib.error.HTTPError as e:
                if e.code in MORTS:
                    return False          # page réellement absente
                if e.code in ANTI_ROBOT:
                    if methode == "GET":  # le GET aussi est refusé → anti-robot
                        return True
                    continue              # sinon on retente en GET
                return False
            except Exception:
                continue
    return False


def verifier(spots):
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    gardes, rejets = [], []

    for s in spots:
        motif = None
        lat, lon = s.get("lat"), s.get("lon")
        if not (isinstance(lat, (int, float)) and isinstance(lon, (int, float))):
            motif = "coordonnées absentes"
        elif not (-90 <= lat <= 90 and -180 <= lon <= 180):
            motif = "coordonnées hors du monde"
        elif s.get("precision_coords") == "incertaine":
            motif = "position incertaine (déclarée par la recherche)"
        # NB : ni l'interdiction ni les accidents ne font rejeter — ils
        # deviennent des mentions affichées dans la fiche (cf. en-tête).
        if motif:
            rejets.append({**s, "motif": motif})
            continue

        eau = eau_a_proximite(lat, lon, cache)
        if eau is False:
            rejets.append({**s, "motif": f"aucune eau à moins de {RAYON_EAU} m (position douteuse)"})
            continue
        if eau is None:
            rejets.append({**s, "motif": "vérification eau impossible (réseau)"})
            continue
        if not lien_valide(s.get("source_url")):
            rejets.append({**s, "motif": "lien source injoignable"})
            continue
        gardes.append(s)
        print(f"  OK {s['nom'][:44]:46} {s.get('pays','?')} {s.get('source_type','?')}", flush=True)

    # dédoublonnage : deux sources décrivent souvent le même spot
    uniques = []
    for s in sorted(gardes, key=lambda x: (x.get("precision_coords") != "exacte", x["nom"])):
        if any(hav_m(s["lat"], s["lon"], u["lat"], u["lon"]) <= FUSION_M for u in uniques):
            continue
        uniques.append(s)

    return uniques, rejets


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    src = Path(sys.argv[1])
    brut = json.loads(src.read_text(encoding="utf-8"))
    spots = brut["spots"] if isinstance(brut, dict) else brut
    print(f"{len(spots)} spots à vérifier\n")
    ok, ko = verifier(spots)
    print(f"\nRETENUS {len(ok)} | REJETÉS {len(ko)}")
    par_motif = {}
    for r in ko:
        cle = r["motif"].split(" (")[0].split(" :")[0]
        par_motif[cle] = par_motif.get(cle, 0) + 1
    for m, n in sorted(par_motif.items(), key=lambda x: -x[1]):
        print(f"  {n:3}  {m}")
    if "--ecrire" in sys.argv:
        (DOSSIER / "spots-saut-verifies.json").write_text(
            json.dumps(ok, ensure_ascii=False, indent=1), encoding="utf-8")
        (DOSSIER / "spots-saut-rejets.json").write_text(
            json.dumps(ko, ensure_ascii=False, indent=1), encoding="utf-8")
        print("ÉCRIT tools/spots-saut-verifies.json (+ rejets)")
