# -*- coding: utf-8 -*-
"""
Récolte des lacs de France métropolitaine (+ Corse) et fusion dans
data/points.geojson (catégorie « lac », ids lac-0001…).

SÉLECTION QUALITATIVE (règle posée par l'utilisateur) : un lac entre s'il a
un article Wikipédia francophone — c'est le filtre de notoriété touristique.
On ne moissonne PAS tout OSM : lacs de montagne, grands lacs, lacs réputés.

Source principale : arbres de catégories Wikipédia.
  - « Catégorie:Lac en France » (sous-catégories suivies si leur nom contient
    « lac », hors ébauches/listes/anciens lacs — sans quoi le parcours dérive :
    les catégories-sujets « Catégorie:Lac d'Annecy » contiennent plages,
    châteaux et compagnies de navigation, d'où le filtre de titre d'article) ;
  - « Catégorie:Étang en France » : les étangs CÉLÈBRES (Thau, Vaccarès,
    Berre…) sont des lacs au sens touristique, mais l'arbre contient des
    dizaines d'étangs de pêche anonymes → seuil de notoriété SEUIL_ETANG
    (longueur d'article en octets) appliqué aux seuls articles venus de cet
    arbre (ceux aussi présents dans l'arbre Lac ne subissent pas le seuil).

Enrichissements :
  - Wikidata (via pageprops.wikibase_item) : altitude P2044, superficie P2046,
    profondeur max P4511 — données typées, plus fiables que le texte ;
  - OSM/Overpass (natural=water + water~lake|reservoir + name, area FR —
    indispensable : la bbox métropole mord sur la Suisse et l'Italie) :
    altitude « ele » en repli, coordonnées de secours pour les rares articles
    non géolocalisés (acceptées seulement si le nom n'a QU'UNE correspondance
    OSM en France — les « Lac Blanc » sont légion). L'OSM n'élargit JAMAIS la
    sélection, il ne fait qu'enrichir des lacs déjà retenus.

Écartés (compteurs dans le bilan) : articles-listes, barrages en tant
qu'ouvrages, pages d'homonymie, lacs disparus/asséchés (détectés dans le
résumé introductif), articles sans coordonnées ni correspondance OSM sûre,
lacs hors métropole (DOM listés à part dans le rapport), doublons.

Ids stables : une ré-exécution réattribue à chaque lac déjà présent dans
points.geojson son id (correspondance nom + < 500 m) ; les nouveaux
continuent la séquence. Ne JAMAIS renuméroter.

Caches (tools/, gitignorés, repris d'une exécution à l'autre) :
  lacs-wiki-arbre.json  pageid → {titre, source lac|etang} (parcours des arbres)
  lacs-wiki-pages.json  pageid → {titre, lat, lon, url, thumb, extract, octets, qid} | null
  lacs-wikidata.json    Qxxx → {altitude, superficie_ha, profondeur}
  lacs-osm.json         éléments Overpass (sauvé si TOUTES les tuiles réussissent)

Usage :  python tools/recolter_lacs.py            récolte + fusion
         python tools/recolter_lacs.py --dry-run  récolte + bilan, sans écrire
"""

import json
import re
import sys
import time
import urllib.parse
from pathlib import Path

import enrichissements as enr

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
CIBLE_POINTS = RACINE / "data" / "points.geojson"

CACHE_ARBRE = DOSSIER / "lacs-wiki-arbre.json"
CACHE_PAGES = DOSSIER / "lacs-wiki-pages.json"
CACHE_WIKIDATA = DOSSIER / "lacs-wikidata.json"
CACHE_OSM = DOSSIER / "lacs-osm.json"
CACHE_COMMUNES = DOSSIER / "lacs-communes.json"
CACHE_ALTI = DOSSIER / "lacs-alti.json"
CACHE_EAU = DOSSIER / "lacs-eau.json"

LAT_MIN, LAT_MAX = 41.0, 51.5
LON_MIN, LON_MAX = -5.5, 10.0

SEUIL_DOUBLON_M = 500        # même nom à < 500 m = même lieu
SEUIL_OSM_M = 10_000         # écart max étiquette Wikipédia ↔ centre OSM (grands lacs)
SEUIL_ETANG = 8_000          # octets d'article : un étang n'entre que s'il est
                             # « célèbre » (calibré pour garder Vaccarès, 8 336 o,
                             # et écarter les étangs de pêche et un roman à 5 995 o)
MAX_NOUVEAUX = 2_500         # garde-fou : au-delà, décision utilisateur requise

# Un article de l'arbre doit RESSEMBLER à un plan d'eau (sinon c'est la dérive
# des catégories-sujets : plages, îles, châteaux, compagnies de navigation…).
# NB : appliqué au titre passé par enr.normaliser() (minuscules, sans espaces).
# Les noms régionaux comptent : laquet (Pyrénées), estany/estanh (catalan,
# aranais), ibón/embalse (versant espagnol — écartés ensuite par le filtre
# pays), Weiher (Alsace/Lorraine).
RE_TITRE_LACUSTRE = re.compile(
    r"lac|laquet|etang|estany|estanh|ibon|embalse|lagune|plandeau|gour|bassin"
    r"|retenue|reservoir|weiher|leman")
# Lacs authentiques dont le titre n'évoque aucun mot d'eau (vérifiés un à un).
TITRES_LACUSTRES_EXPRES = {
    "Lauvitel", "Lindre", "Fischboedle", "Schiessrothried",
    "Grand Laoucien", "L'Estagnas",
    "Rabassoles bas", "Rabassoles bleu", "Rabassoles noir",
}
# Sous-catégories à ne pas suivre malgré le mot-clé.
RE_SOUSCAT_EXCLUE = re.compile(r"ebauche|listede|ancienlac|lacfictif|lacdefiction")
# Titres à écarter d'office (listes, ouvrages d'art, articles-régions,
# homonymies résiduelles).
RE_TITRE_EXCLU = re.compile(
    r"^(Liste[s ]|Barrage |Projet de |Historique |Région |Catégorie:)", re.I)
# Lac disparu/asséché, détecté au début du résumé introductif (texte normalisé
# SANS espaces — les motifs sont donc collés).
RE_LAC_DISPARU = re.compile(
    r"ancien(lac|etang)|(lac|etang)\w{0,60}(asseche|disparu|vidangedefinitive)")
# Incontournables (critère « taille/réputation ») absents des arbres : l'article
# « Léman » n'est catégorisé que dans « Catégorie:Léman », jamais « Lac … ».
TITRES_SUPPLEMENTAIRES = ("Léman",)
# Exemptés du filtre pays : leur centre tombe hors de tout polygone communal
# (grande étendue d'eau non rattachée), mais ils sont incontestablement français.
TITRES_FRANCE_EXPRES = {"Étang de Berre"}
# Lacs français dont une superficie > 20 km² est crédible (géographie stable).
# Toute autre valeur > 2 000 ha est une erreur Wikidata (déjà vu : « Lac de
# Ribou 87 km² » pour 0,87, « Lac de Saint-Félix 21,5 km² »…).
GRANDS_LACS_CONNUS = {
    "Léman", "Étang de Berre", "Étang de Thau", "Étang de Vaccarès",
    "Étang de Bages-Sigean", "Étang de Leucate", "Étang de l'Or",
    "Étangs de la Dombes", "Lac d'Annecy", "Lac du Bourget",
    "Lac de Serre-Ponçon", "Lac de Sainte-Croix", "Lac de Grand-Lieu",
    "Lac du Der-Chantecoq", "Lac d'Orient", "Lacs Amance et du Temple",
    "Lac d'Hourtin et de Carcans", "Lac de Cazaux et de Sanguinet",
    "Lac de Biscarrosse et de Parentis", "Lac de Lacanau",
}
# Superficie annoncée dans le résumé de l'article (recoupement anti-erreur).
# Le nombre peut porter un séparateur de milliers (« 7 500 hectares »).
RE_SUPERFICIE_TXT = re.compile(
    r"(\d{1,3}(?:[   ]\d{3})*(?:[,.]\d+)?)\s*(km²|km2|hectares?|ha)\b")


def normaliser_nom(texte):
    """minuscules, sans accents/ponctuation, St↔Saint, parenthèses ôtées."""
    texte = re.sub(r"\([^)]*\)", " ", texte or "")           # « Lac Blanc (Vosges) »
    texte = re.sub(r"\bSte?s?\b\.?", "Saint", texte, flags=re.I)
    return enr.normaliser(texte).replace("sainte", "saint")


def _nettoyer_texte(texte, maxi=350):
    t = re.sub(r"<[^>]+>", " ", texte or "")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > maxi:
        t = t[:maxi].rsplit(" ", 1)[0].rstrip(",;:. ") + "…"
    return t


def _distance_m(a, b):
    return enr._haversine((a["lon"], a["lat"]), (b["lon"], b["lat"]))


# ---------------------------------------------------------------------------
# 1. Parcours des arbres de catégories Wikipédia
# ---------------------------------------------------------------------------

def parcourir_arbres():
    """pageid (str) → {titre, source} pour les arbres Lac et Étang.
    source = "lac" (critère : l'article suffit) ou "etang" (seuil de célébrité).
    Un article présent dans les deux arbres garde la source « lac »."""
    if CACHE_ARBRE.exists():
        return _completer_supplementaires(
            json.loads(CACHE_ARBRE.read_text(encoding="utf-8")))
    articles = {}
    for racine, mot, source in (("Catégorie:Lac en France", "lac", "lac"),
                                ("Catégorie:Étang en France", "etang", "etang")):
        print(f"  Wikipédia : parcours de « {racine} »…")
        vues, file = set(), [(racine, 0)]
        while file:
            cat, prof = file.pop(0)
            if cat in vues:
                continue
            vues.add(cat)
            for m in enr._membres_categorie(cat):
                if m["ns"] == 0:
                    pid = str(m["pageid"])
                    # l'arbre Lac (parcouru en premier) prime sur l'arbre Étang
                    if articles.get(pid, {}).get("source") != "lac":
                        articles[pid] = {"titre": m["title"], "source": source}
                elif m["ns"] == 14 and prof < 4:
                    nrm = enr.normaliser(m["title"])
                    if mot in nrm and not RE_SOUSCAT_EXCLUE.search(nrm):
                        file.append((m["title"], prof + 1))
            time.sleep(0.2)
        print(f"    {len(vues)} catégories parcourues, cumul {len(articles)} articles")
    CACHE_ARBRE.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
    return _completer_supplementaires(articles)


def _completer_supplementaires(articles):
    """Injecte (idempotent) les incontournables listés hors arbres."""
    connus = {v["titre"] for v in articles.values()}
    manquants = [t for t in TITRES_SUPPLEMENTAIRES if t not in connus]
    if not manquants:
        return articles
    d = enr._api_wiki({"action": "query", "redirects": "1",
                       "titles": "|".join(manquants)})
    for pid, page in (d.get("query", {}).get("pages") or {}).items():
        if int(pid) > 0:
            articles[str(pid)] = {"titre": page["title"], "source": "lac"}
    CACHE_ARBRE.write_text(json.dumps(articles, ensure_ascii=False), encoding="utf-8")
    return articles


# ---------------------------------------------------------------------------
# 2. Détails des articles (coordonnées, photo, résumé, longueur, entité)
# ---------------------------------------------------------------------------

def details_articles(pageids):
    """pageid → {titre, lat, lon, url, thumb, extract, octets, qid} | None
    (None = page manquante ou homonymie). Lots de 20 (limite exlimit),
    colimit=max ET suivi de « continue » (sans quoi l'API ne renvoie que
    10 coordonnées/réponse), cache sauvegardé à chaque lot."""
    cache = json.loads(CACHE_PAGES.read_text(encoding="utf-8")) if CACHE_PAGES.exists() else {}
    a_faire = [p for p in sorted(pageids, key=int) if p not in cache]
    if a_faire:
        print(f"  Wikipédia : {len(a_faire)} articles à détailler…")
    for i in range(0, len(a_faire), 20):
        lot = a_faire[i:i + 20]
        params = {"action": "query", "format": "json",
                  "pageids": "|".join(lot),
                  "prop": "coordinates|pageimages|extracts|info|pageprops",
                  "colimit": "max",
                  "piprop": "thumbnail", "pithumbsize": "400", "pilimit": "max",
                  "exintro": "1", "explaintext": "1", "exsentences": "3", "exlimit": "max",
                  "ppprop": "disambiguation|wikibase_item", "inprop": "url"}
        pages, cont = {}, {}
        while True:
            d = enr.http_json(enr.API_WIKI + "?" + urllib.parse.urlencode({**params, **cont}))
            for pid, page in (d.get("query", {}).get("pages") or {}).items():
                fusion = pages.setdefault(pid, {})
                for cle, val in page.items():
                    fusion.setdefault(cle, val)
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items() if k != "continue"}
            time.sleep(0.3)
        for pid, page in pages.items():
            props = page.get("pageprops") or {}
            if "missing" in page or "disambiguation" in props:
                cache[pid] = None
                continue
            coord = (page.get("coordinates") or [{}])[0]
            cache[pid] = {
                "titre": page.get("title", ""),
                "lat": coord.get("lat"), "lon": coord.get("lon"),
                "url": page.get("fullurl", ""),
                "thumb": (page.get("thumbnail") or {}).get("source", ""),
                "extract": _nettoyer_texte(page.get("extract", "")),
                "octets": page.get("length", 0),
                "qid": props.get("wikibase_item", ""),
            }
        for pid in lot:
            cache.setdefault(pid, None)
        CACHE_PAGES.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 20, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.5)
    return cache


# ---------------------------------------------------------------------------
# 3. Wikidata : altitude (P2044), superficie (P2046), profondeur max (P4511)
# ---------------------------------------------------------------------------

_UNITES_SURFACE_HA = {  # entité Wikidata → facteur vers hectares
    "Q712226": 100.0,       # km²
    "Q35852": 1.0,          # hectare
    "Q25343": 0.0001,       # m²
}


def _quantite(claims, prop):
    """Première valeur numérique (amount, unité) d'une propriété, ou None."""
    for c in claims.get(prop, []):
        val = (((c.get("mainsnak") or {}).get("datavalue") or {}).get("value") or {})
        try:
            return float(val["amount"]), (val.get("unit") or "").rsplit("/", 1)[-1]
        except (KeyError, ValueError, TypeError):
            continue
    return None


def donnees_wikidata(qids):
    """Qxxx → {altitude, superficie_ha, profondeur} (None si inconnu),
    par lots de 50, avec cache."""
    cache = json.loads(CACHE_WIKIDATA.read_text(encoding="utf-8")) if CACHE_WIKIDATA.exists() else {}
    a_faire = sorted({q for q in qids if q and q not in cache})
    if a_faire:
        print(f"  Wikidata : {len(a_faire)} entités (altitude/superficie/profondeur)…")
    for i in range(0, len(a_faire), 50):
        lot = a_faire[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
               "&props=claims&ids=" + "|".join(lot))
        try:
            d = enr.http_json(url)
        except Exception as exc:
            print(f"    ! wikidata : {exc}")
            break
        for q, ent in (d.get("entities") or {}).items():
            claims = ent.get("claims") or {}
            res = {"altitude": None, "superficie_ha": None, "profondeur": None}
            alt = _quantite(claims, "P2044")
            if alt and alt[1] in ("Q11573", "1") and -10 <= alt[0] <= 4900:
                res["altitude"] = int(round(alt[0]))
            surf = _quantite(claims, "P2046")
            if surf and surf[1] in _UNITES_SURFACE_HA:
                ha = surf[0] * _UNITES_SURFACE_HA[surf[1]]
                if 0 < ha <= 100_000:
                    res["superficie_ha"] = round(ha, 1)
            prof = _quantite(claims, "P4511")
            if prof and prof[1] in ("Q11573", "1") and 0 < prof[0] <= 400:
                res["profondeur"] = round(prof[0], 1)
            cache[q] = res
        CACHE_WIKIDATA.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 50, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.4)
    return cache


# ---------------------------------------------------------------------------
# 4. OSM/Overpass : enrichissement (altitude ele, coordonnées de secours)
# ---------------------------------------------------------------------------

def telecharger_lacs_osm():
    """Plans d'eau NOMMÉS lake|reservoir de France (nœuds + centres), par
    tuiles de 3°. Cache sauvegardé QUE si toutes les tuiles réussissent."""
    if CACHE_OSM.exists():
        return json.loads(CACHE_OSM.read_text(encoding="utf-8"))
    print("  téléchargement Overpass (natural=water, lake|reservoir, nommés)…")
    pas = 3.0
    tuiles = []
    lon = LON_MIN
    while lon < LON_MAX:
        lat = LAT_MIN
        while lat < LAT_MAX:
            tuiles.append(f"{lat},{lon},{min(lat + pas, LAT_MAX)},{min(lon + pas, LON_MAX)}")
            lat += pas
        lon += pas
    elements = {}
    for passe in range(1, 4):
        if not tuiles:
            break
        if passe > 1:
            print(f"  passe {passe} : {len(tuiles)} tuile(s) à retenter, pause 90 s…")
            time.sleep(90)
        restantes = []
        for bbox in tuiles:
            requete = ('[out:json][timeout:180];'
                       'area["ISO3166-1"="FR"]["admin_level"="2"]->.fr;'
                       f'nwr["natural"="water"]["water"~"^(lake|reservoir)$"]["name"]'
                       f'(area.fr)({bbox});'
                       'out center;')
            try:
                d = enr._overpass(requete)
                for e in d.get("elements", []):
                    elements[f"{e['type']}{e['id']}"] = e
            except Exception as exc:
                restantes.append(bbox)
                print(f"    ! bbox {bbox} : {exc}")
            time.sleep(2)
        tuiles = restantes
    liste = list(elements.values())
    if tuiles:
        print(f"  ! {len(tuiles)} tuile(s) en échec : cache NON sauvegardé, relancer")
    else:
        CACHE_OSM.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    print(f"  Overpass : {len(liste)} plans d'eau nommés")
    return liste


def indexer_osm(elements):
    """nomNormalisé → [{lat, lon, ele, website}] (accès private/no écartés)."""
    index = {}
    for e in elements:
        tags = e.get("tags") or {}
        if tags.get("access") in ("private", "no"):
            continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        nom = normaliser_nom(tags.get("name") or tags.get("name:fr") or "")
        if lat is None or lon is None or not nom:
            continue
        ele = None
        try:
            v = float((tags.get("ele") or "").replace(",", "."))
            if -10 <= v <= 4900:
                ele = int(round(v))
        except ValueError:
            pass
        website = (tags.get("website") or tags.get("contact:website") or "").strip()
        if not re.match(r"^https?://", website) or len(website) > 300:
            website = ""
        index.setdefault(nom, []).append(
            {"lat": lat, "lon": lon, "ele": ele, "website": website})
    return index


def _dans_leau(lat, lon, cache):
    """Le point tombe-t-il dans un polygone natural=water OSM ? (is_in
    Overpass, cache lacs-eau.json). None = indéterminé (Overpass en échec)."""
    cle = f"{lat:.5f},{lon:.5f}"
    if cle in cache:
        return cache[cle]
    try:
        d = enr._overpass(f'[out:json][timeout:30];is_in({lat:.6f},{lon:.6f})->.a;'
                          'area.a["natural"="water"];out ids;')
        cache[cle] = bool(d.get("elements"))
        CACHE_EAU.write_text(json.dumps(cache), encoding="utf-8")
        time.sleep(1)
        return cache[cle]
    except Exception as exc:
        print(f"    ! is_in({cle}) : {exc}")
        return None


def enrichir_osm(candidats, index_osm, stats):
    """Altitude « ele » en repli, site web, coordonnées de secours (article
    sans coordonnées : acceptées si les correspondances OSM du nom sont sans
    ambiguïté — une seule, ou toutes dans la même grappe de 2 km : un lac
    découpé en plusieurs polygones)."""
    cache_eau = json.loads(CACHE_EAU.read_text(encoding="utf-8")) if CACHE_EAU.exists() else {}
    for c in candidats:
        cle = normaliser_nom(c["nom"])
        entrees = index_osm.get(cle, [])
        if c["lat"] is None:
            grappe = (entrees and all(
                _distance_m(a, b) < 2000
                for i, a in enumerate(entrees) for b in entrees[i + 1:]))
            if grappe:
                c["lat"] = sum(e["lat"] for e in entrees) / len(entrees)
                c["lon"] = sum(e["lon"] for e in entrees) / len(entrees)
                c["coord_osm"] = True
                stats["coords_recuperees_osm"] += 1
            continue
        proche = min(entrees, key=lambda e: _distance_m(c, e), default=None)
        if proche and _distance_m(c, proche) < SEUIL_OSM_M:
            if not c.get("altitude") and proche["ele"]:
                c["altitude"] = proche["ele"]
                stats["altitudes_osm"] += 1
            if not c.get("website") and proche["website"]:
                c["website"] = proche["website"]
            # Grand lac : l'étiquette Wikipédia est parfois posée sur une rive
            # ou la ville voisine (Annecy : à 6 km de l'eau), et le centre OSM
            # (centre de la boîte englobante) peut tomber sur une presqu'île
            # pour un lac en L (Serre-Ponçon). On prend le premier point qui
            # est réellement DANS l'eau : centre OSM, sinon étiquette WP.
            # Un homonyme de 500 ha à < 10 km n'existe pas, c'est sûr.
            if (c["superficie_ha"] or 0) >= 500:
                if _dans_leau(proche["lat"], proche["lon"], cache_eau) is not False:
                    c["lat"], c["lon"] = proche["lat"], proche["lon"]
                    stats["recentres_osm"] += 1
                elif _dans_leau(c["lat"], c["lon"], cache_eau) is False:
                    # ni l'un ni l'autre dans l'eau : le centre OSM reste
                    # le plus proche du plan d'eau
                    c["lat"], c["lon"] = proche["lat"], proche["lon"]
                    stats["recentres_osm"] += 1


# ---------------------------------------------------------------------------
# 4 bis. Filtre pays : le point doit tomber dans une commune française
# (la bbox métropole INCLUT l'Andorre et mord sur l'Espagne, la Suisse et
# l'Italie — les catégories « Lac des Pyrénées » couvrent les deux versants)
# ---------------------------------------------------------------------------

def _commune_a(lat, lon):
    """Nom de la commune française contenant le point, ou None."""
    d = enr.http_json("https://geo.api.gouv.fr/communes?"
                      + urllib.parse.urlencode({"lat": f"{lat:.6f}",
                                                "lon": f"{lon:.6f}",
                                                "fields": "nom", "format": "json"}))
    return d[0]["nom"] if d else None


def filtrer_france(candidats, stats):
    """Garde les candidats situés dans une commune française. Le centre d'un
    très grand plan d'eau peut tomber hors de tout polygone communal (Berre,
    Léman) : ces cas connus sont exemptés NOMINATIVEMENT — un sauvetage
    géométrique (anneau de sondage) a déjà repêché par erreur un lac suisse
    à la superficie Wikidata fausse, on ne recommence pas."""
    exemptes = TITRES_FRANCE_EXPRES | set(TITRES_SUPPLEMENTAIRES)
    cache = json.loads(CACHE_COMMUNES.read_text(encoding="utf-8")) if CACHE_COMMUNES.exists() else {}
    a_faire = [c for c in candidats if c["lat"] is not None
               and c["nom"] not in exemptes
               and f"{c['lat']:.4f},{c['lon']:.4f}" not in cache]
    if a_faire:
        print(f"  filtre pays : géocodage inverse de {len(a_faire)} points…")
    for i, c in enumerate(a_faire, 1):
        cle = f"{c['lat']:.4f},{c['lon']:.4f}"
        try:
            cache[cle] = _commune_a(c["lat"], c["lon"])
        except Exception as exc:
            print(f"    ! {cle} : {exc}")   # pas mis en cache : retenté au run suivant
        if i % 50 == 0 or i == len(a_faire):
            CACHE_COMMUNES.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    {i}/{len(a_faire)}")
        time.sleep(0.12)
    gardes, hors_france = [], []
    for c in candidats:
        if c["lat"] is None:
            gardes.append(c)                 # tranché plus loin (sans_coordonnees)
            continue
        cle = f"{c['lat']:.4f},{c['lon']:.4f}"
        if c["nom"] in exemptes or cle not in cache:
            if cle not in cache and c["nom"] not in exemptes:
                print(f"    ! géocodage indisponible pour « {c['nom']} » : gardé, à revérifier")
            gardes.append(c)
            continue
        if cache[cle]:
            gardes.append(c)
        else:
            hors_france.append(c["nom"])
            stats["hors_france"] += 1
    return gardes, sorted(hors_france)


# ---------------------------------------------------------------------------
# 5. Sélection : articles → candidats
# ---------------------------------------------------------------------------

def construire_candidats(arbre, pages, stats):
    candidats, hors_metropole = [], []
    for pid, info in arbre.items():
        stats["articles_arbre"] += 1
        page = pages.get(pid)
        if page is None:
            stats["homonymies_manquants"] += 1
            continue
        titre = page["titre"] or info["titre"]
        if RE_TITRE_EXCLU.match(titre):
            stats["listes_barrages"] += 1
            continue
        if (not RE_TITRE_LACUSTRE.search(enr.normaliser(titre))
                and titre not in TITRES_LACUSTRES_EXPRES):
            stats["titres_non_lacustres"] += 1      # dérive des catégories-sujets
            continue
        if RE_LAC_DISPARU.search(enr.normaliser(page["extract"][:220])):
            stats["disparus"] += 1
            continue
        if info["source"] == "etang" and page["octets"] < SEUIL_ETANG:
            stats["etangs_anonymes"] += 1           # pas assez célèbre
            continue
        c = {"pageid": pid, "nom": titre,
             "lat": page["lat"], "lon": page["lon"],
             "wiki_url": page["url"], "thumb": page["thumb"],
             "extract": page["extract"], "qid": page["qid"],
             "octets": page["octets"], "source": info["source"],
             "altitude": None, "superficie_ha": None, "profondeur": None,
             "website": "", "coord_osm": False}
        if c["lat"] is not None and not (LAT_MIN <= c["lat"] <= LAT_MAX
                                         and LON_MIN <= c["lon"] <= LON_MAX):
            hors_metropole.append(titre)
            continue
        candidats.append(c)
    stats["hors_metropole"] = len(hors_metropole)
    return candidats, sorted(hors_metropole)


def appliquer_wikidata(candidats, wd):
    for c in candidats:
        d = wd.get(c["qid"]) or {}
        c["altitude"] = d.get("altitude")
        c["superficie_ha"] = d.get("superficie_ha")
        c["profondeur"] = d.get("profondeur")


def valider_superficies(candidats, stats):
    """Écarte les superficies Wikidata invraisemblables : > 20 km² hors de la
    liste des grands lacs français connus, ou en désaccord (facteur > 3) avec
    la superficie annoncée dans le résumé de l'article. Mieux vaut un champ
    absent qu'une donnée fausse."""
    for c in candidats:
        s = c["superficie_ha"]
        if not s:
            continue
        if s > 2000 and c["nom"] not in GRANDS_LACS_CONNUS:
            c["superficie_ha"] = None
            stats["superficies_douteuses"] += 1
            continue
        m = RE_SUPERFICIE_TXT.search(c["extract"] or "")
        if m and "versant" not in (c["extract"] or "")[max(0, m.start() - 40):m.start()]:
            try:
                v = float(re.sub(r"[   ]", "", m.group(1)).replace(",", "."))
            except ValueError:
                continue
            ha = v * (100 if m.group(2).startswith("km") else 1)
            if ha > 0 and (s / ha > 3 or ha / s > 3):
                c["superficie_ha"] = None
                stats["superficies_douteuses"] += 1


def coords_wikidata(candidats, stats):
    """Dernier repli pour les articles sans coordonnées : la propriété P625
    de leur entité Wikidata (concerne une poignée de lacs — pas de cache)."""
    restants = [c for c in candidats if c["lat"] is None and c["qid"]]
    for i in range(0, len(restants), 50):
        lot = restants[i:i + 50]
        ids = "|".join(dict.fromkeys(c["qid"] for c in lot))
        try:
            d = enr.http_json("https://www.wikidata.org/w/api.php?action=wbgetentities"
                              "&format=json&props=claims&ids=" + ids)
        except Exception as exc:
            print(f"    ! wikidata P625 : {exc}")
            return
        for c in lot:
            ent = (d.get("entities") or {}).get(c["qid"]) or {}
            for cl in (ent.get("claims") or {}).get("P625", []):
                val = (((cl.get("mainsnak") or {}).get("datavalue") or {})
                       .get("value") or {})
                if "latitude" in val:
                    c["lat"], c["lon"] = val["latitude"], val["longitude"]
                    stats["coords_recuperees_wikidata"] += 1
                    break
        time.sleep(0.4)


# ---------------------------------------------------------------------------
# 6. Dédoublonnage interne (même nom normalisé à < 500 m)
# ---------------------------------------------------------------------------

def valider_altitudes(candidats, stats):
    """Altitude IGN au point du lac (le MNT sur un plan d'eau EST la surface
    de l'eau) : remplit les altitudes manquantes et corrige les valeurs
    Wikidata aberrantes (déjà vu : « Lac du Bourget 2 315 m » pour 231,5).
    Cache lacs-alti.json ; échec réseau = on garde ce qu'on a."""
    cache = json.loads(CACHE_ALTI.read_text(encoding="utf-8")) if CACHE_ALTI.exists() else {}
    avec_coords = [c for c in candidats if c["lat"] is not None]
    a_faire = [c for c in avec_coords if f"{c['lat']:.4f},{c['lon']:.4f}" not in cache]
    if a_faire:
        print(f"  altimétrie IGN : {len(a_faire)} points…")
        try:
            alts = enr._elevations_ign([(c["lon"], c["lat"]) for c in a_faire])
            for c, alt in zip(a_faire, alts):
                cache[f"{c['lat']:.4f},{c['lon']:.4f}"] = alt
            CACHE_ALTI.write_text(json.dumps(cache), encoding="utf-8")
        except Exception as exc:
            print(f"    ! altimétrie : {exc}")
    for c in avec_coords:
        alt = cache.get(f"{c['lat']:.4f},{c['lon']:.4f}")
        if alt is None or not (-10 <= alt <= 4900):
            continue                        # hors couverture IGN (Léman…)
        if c["altitude"] is None:
            c["altitude"] = int(round(alt))
            stats["altitudes_ign"] += 1
        elif abs(c["altitude"] - alt) > 150:
            c["altitude"] = int(round(alt))
            stats["altitudes_corrigees"] += 1


def _score(c):
    return ((2 if c["thumb"] else 0) + (1 if c["extract"] else 0)
            + (1 if c["superficie_ha"] else 0) + (0.5 if c["altitude"] else 0)
            + min(c["octets"], 60_000) / 1e6)


def dedoublonner_interne(candidats, stats):
    par_nom = {}
    for c in candidats:
        par_nom.setdefault(normaliser_nom(c["nom"]), []).append(c)
    gardes = []
    for groupe in par_nom.values():
        groupe.sort(key=lambda c: (-_score(c), c["pageid"]))
        retenus = []
        for c in groupe:
            proche = next((r for r in retenus if _distance_m(c, r) < SEUIL_DOUBLON_M), None)
            if proche:
                stats["doublons_internes"] += 1
                for cle in ("altitude", "superficie_ha", "profondeur", "thumb",
                            "extract", "website"):
                    if not proche.get(cle) and c.get(cle):
                        proche[cle] = c[cle]
            else:
                retenus.append(c)
        gardes.extend(retenus)
    return gardes


# ---------------------------------------------------------------------------
# 7. Candidats → features, fusion avec l'existant, attribution des ids
# ---------------------------------------------------------------------------

def _fmt_superficie(ha):
    if ha >= 100:
        km2 = ha / 100
        txt = f"{km2:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " km²"
    else:
        txt = f"{ha:.1f}".rstrip("0").rstrip(".").replace(".", ",") + " ha"
    return txt


def _construire_feature(c, id_):
    details = {}
    if c["altitude"] is not None:
        details["altitude"] = f"{c['altitude']} m"
        details["altitude_n"] = c["altitude"]
    if c["superficie_ha"]:
        details["superficie"] = _fmt_superficie(c["superficie_ha"])
        details["superficie_n"] = c["superficie_ha"]
    if c["profondeur"]:
        p = c["profondeur"]
        details["profondeur"] = (f"{int(p)} m" if float(p).is_integer()
                                 else f"{p:.1f} m".replace(".", ","))
    desc = c["extract"] or "Lac répertorié dans l'encyclopédie Wikipédia."
    # Filtre « Fiche » (themes.js) : Référencé = photo ET une vraie information
    # (résumé ou donnée clé) ; sinon À vérifier.
    complet = bool(c["thumb"]) and bool(c["extract"] or c["superficie_ha"]
                                        or c["altitude"] is not None)
    details["fiche"] = "Référencé" if complet else "À vérifier"
    photo = c["thumb"] if (c["thumb"] or "").startswith("https://upload.wikimedia.org") else ""
    props = {
        "id": id_,
        "name": c["nom"],
        "theme": "lac",
        "description": desc,
        "link": c["wiki_url"] or c["website"] or "",
        "photos": [photo] if photo else [],
        "details": details,
    }
    if c["wiki_url"] and c["website"]:
        props["links"] = [{"label": "Site officiel", "url": c["website"]}]
    return {"type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]},
            "properties": props}


def _index_par_nom(features):
    index = {}
    for f in features:
        g = f.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        lon, lat = g["coordinates"][:2]
        cle = normaliser_nom(f["properties"].get("name", ""))
        if cle:
            index.setdefault(cle, []).append({"feature": f, "lon": lon, "lat": lat})
    return index


def _fusionner_dans_existant(entree, c, stats):
    p = entree["feature"]["properties"]
    if not p.get("link") and c["wiki_url"]:
        p["link"] = c["wiki_url"]
    if not p.get("photos") and (c["thumb"] or "").startswith("https://upload.wikimedia.org"):
        p["photos"] = [c["thumb"]]
    if not p.get("description") and c["extract"]:
        p["description"] = c["extract"]
    stats["fusionnes"] += 1


def convertir_lacs(autres_features, precedents=None):
    """Construit les features « lac » et fusionne les doublons dans les points
    existants (autres_features est MUTÉ : champs manquants complétés).

    precedents : features lac déjà en base (préservation des ids) ;
    None → lues depuis data/points.geojson si le fichier existe.
    Renvoie (features_lac, stats, {hors_metropole, hors_france})."""
    if precedents is None:
        precedents = []
        if CIBLE_POINTS.exists():
            anciens = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
            precedents = [f for f in anciens.get("features", [])
                          if f.get("properties", {}).get("theme") == "lac"]

    stats = {k: 0 for k in ("articles_arbre", "homonymies_manquants",
                            "listes_barrages", "titres_non_lacustres",
                            "disparus", "etangs_anonymes", "hors_metropole",
                            "hors_france", "sans_coordonnees",
                            "coords_recuperees_osm", "coords_recuperees_wikidata",
                            "altitudes_osm", "recentres_osm", "superficies_douteuses",
                            "altitudes_ign", "altitudes_corrigees",
                            "doublons_internes", "fusionnes",
                            "ajoutes", "ids_reutilises", "conserves_sans_source")}

    arbre = parcourir_arbres()
    pages = details_articles(list(arbre))
    candidats, hors_metropole = construire_candidats(arbre, pages, stats)
    appliquer_wikidata(candidats, donnees_wikidata([c["qid"] for c in candidats]))
    valider_superficies(candidats, stats)
    enrichir_osm(candidats, indexer_osm(telecharger_lacs_osm()), stats)
    coords_wikidata(candidats, stats)
    candidats, hors_france = filtrer_france(candidats, stats)

    avant = len(candidats)
    candidats = [c for c in candidats if c["lat"] is not None
                 and LAT_MIN <= c["lat"] <= LAT_MAX and LON_MIN <= c["lon"] <= LON_MAX]
    stats["sans_coordonnees"] = avant - len(candidats)
    valider_altitudes(candidats, stats)
    candidats = dedoublonner_interne(candidats, stats)

    index_autres = _index_par_nom(autres_features)
    index_prec = _index_par_nom(precedents)
    ids_pris = {f["properties"]["id"] for f in precedents}

    def prochain_id():
        n = 1
        while f"lac-{n:04d}" in ids_pris:
            n += 1
        ids_pris.add(f"lac-{n:04d}")
        return f"lac-{n:04d}"

    features = []
    ids_reutilises = set()
    candidats.sort(key=lambda c: (normaliser_nom(c["nom"]), c["lon"], c["lat"]))
    for c in candidats:
        cle = normaliser_nom(c["nom"])
        # 1. déjà en base en tant que lac → même id, fiche réactualisée
        prec = next((e for e in index_prec.get(cle, [])
                     if _distance_m(c, e) < SEUIL_DOUBLON_M
                     and e["feature"]["properties"]["id"] not in ids_reutilises), None)
        if prec:
            id_ = prec["feature"]["properties"]["id"]
            ids_reutilises.add(id_)
            features.append(_construire_feature(c, id_))
            stats["ids_reutilises"] += 1
            continue
        # 2. déjà en base dans une AUTRE catégorie → fusion, pas de doublon
        autre = next((e for e in index_autres.get(cle, [])
                      if _distance_m(c, e) < SEUIL_DOUBLON_M), None)
        if autre:
            _fusionner_dans_existant(autre, c, stats)
            continue
        # 3. nouveau point
        features.append(_construire_feature(c, prochain_id()))
        stats["ajoutes"] += 1

    # Lacs précédents disparus de la récolte : conservés tels quels (les
    # statuts/carnet des utilisateurs pointent sur leurs ids).
    for f in precedents:
        if f["properties"]["id"] not in ids_reutilises:
            features.append(f)
            stats["conserves_sans_source"] += 1

    if stats["ajoutes"] > MAX_NOUVEAUX:
        raise RuntimeError(
            f"{stats['ajoutes']} nouveaux lacs (> {MAX_NOUVEAUX}) : "
            "volume à valider par l'utilisateur avant intégration")
    features.sort(key=lambda f: f["properties"]["id"])  # tri stable → diff lisible
    return features, stats, {"hors_metropole": hors_metropole,
                             "hors_france": hors_france}


# ---------------------------------------------------------------------------
# Exécution autonome : fusion dans data/points.geojson
# ---------------------------------------------------------------------------

def _bilan(features, stats, ecartes):
    total = len(features) or 1
    avec = lambda test: sum(1 for f in features if test(f["properties"]))
    print(f"""
Bilan lacs
  articles des arbres Wikipédia : {stats['articles_arbre']}
  écartés : homonymies/pages manquantes {stats['homonymies_manquants']},
            listes/barrages {stats['listes_barrages']}, titres non lacustres {stats['titres_non_lacustres']},
            lacs disparus/asséchés {stats['disparus']}, étangs sans notoriété {stats['etangs_anonymes']},
            hors métropole {stats['hors_metropole']}, hors France (Andorre/Espagne/Suisse) {stats['hors_france']},
            sans coordonnées {stats['sans_coordonnees']}
  coordonnées récupérées : OSM {stats['coords_recuperees_osm']}, Wikidata {stats['coords_recuperees_wikidata']} ; altitudes OSM : {stats['altitudes_osm']}
  grands lacs recentrés sur le plan d'eau OSM : {stats['recentres_osm']} ; superficies douteuses écartées : {stats['superficies_douteuses']}
  altitudes IGN : complétées {stats['altitudes_ign']}, corrigées (Wikidata aberrant) {stats['altitudes_corrigees']}
  doublons internes fusionnés : {stats['doublons_internes']}
  fusionnés dans des points existants : {stats['fusionnes']}
  ids réutilisés : {stats['ids_reutilises']}, conservés sans source : {stats['conserves_sans_source']}
  AJOUTÉS : {stats['ajoutes']}  (total catégorie : {len(features)})
  couverture : photo {avec(lambda p: p.get('photos')) * 100 // total} %,
               description {avec(lambda p: p.get('description')) * 100 // total} %,
               altitude {avec(lambda p: 'altitude' in p.get('details', {})) * 100 // total} %,
               superficie {avec(lambda p: 'superficie' in p.get('details', {})) * 100 // total} %,
               fiche Référencé {avec(lambda p: p.get('details', {}).get('fiche') == 'Référencé') * 100 // total} %""")
    for cle, libelle in (("hors_metropole", "hors métropole"),
                         ("hors_france", "hors France")):
        liste = ecartes.get(cle) or []
        if liste:
            print(f"  {libelle} (non intégrés) : {', '.join(liste[:12])}"
                  + (f"… (+{len(liste) - 12})" if len(liste) > 12 else ""))


def main(dry_run=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    collection = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
    autres = [f for f in collection["features"]
              if f["properties"].get("theme") != "lac"]
    precedents = [f for f in collection["features"]
                  if f["properties"].get("theme") == "lac"]
    print(f"points.geojson : {len(autres)} points existants, "
          f"{len(precedents)} lacs déjà en base")
    lacs, stats, ecartes = convertir_lacs(autres, precedents)
    _bilan(lacs, stats, ecartes)
    if dry_run:
        print("(--dry-run : rien n'a été écrit)")
        return 0
    collection["features"] = autres + lacs
    CIBLE_POINTS.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"points.geojson : {len(collection['features'])} features, "
          f"{CIBLE_POINTS.stat().st_size // 1024} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
