# -*- coding: utf-8 -*-
"""
PILOTE « Randonnées remarquables » — massif de la Chartreuse uniquement.
Fusionne dans data/points.geojson (catégorie « randonnee », ids rando-0001…).

SÉLECTION QUALITATIVE (règle posée par l'utilisateur) : il n'existe AUCUNE
base libre de « belles randonnées » (FFRandonnée, Visorando = propriétaires).
Le pilote repose donc sur une LISTE ÉDITORIALE de sorties emblématiques du
massif (sommets à voie normale de randonnée + le cirque de Saint-Même),
validée par deux sources libres :
  - Wikipédia (article obligatoire = filtre de notoriété ; coordonnées du
    sommet, photo, résumé introductif, vérification croisée de l'altitude) ;
  - OSM/Overpass (relations route=hiking de la bbox Chartreuse) en
    CORROBORATION : itinéraires balisés portant le nom de l'objectif.
Un candidat SANS article Wikipédia est écarté (compteur « sans_article »).

CONVENTION DE PLACEMENT : le point est posé au SOMMET (ou à l'objectif —
cirque…) de la randonnée, jamais au parking. C'est ce que Wikipédia géolocalise
précisément, c'est ce que le voyageur cherche sur la carte, et un même sommet a
souvent plusieurs départs. Le départ classique est donné dans details.depart.

Champs details : sommet, altitude (+altitude_n, croisée avec le texte de
l'article), denivele (+denivele_n, ESTIMATION « ≈ » = altitude sommet −
altitude du départ classique, valeurs éditoriales connues), duree (estimation
éditoriale, seulement quand elle est bien établie), depart, acces (voie
normale, 1 phrase), massif (pour le filtre « Massif » de themes.js),
fiche (« Référencée » = photo + résumé / « À vérifier »).

Ids stables : ré-exécution → chaque randonnée déjà en base garde son id
(correspondance nom + < 500 m). Ne JAMAIS renuméroter.

Caches (tools/, gitignorés) :
  randos-wiki.json      titre → page Wikipédia (coordonnées, photo, résumé)
  randos-osm.json       relations route=hiking de la bbox Chartreuse
  randos-cadrage.json   comptages Overpass France (volet cadrage)

Usage :  python tools/recolter_randonnees.py            récolte + fusion
         python tools/recolter_randonnees.py --dry-run  bilan sans écrire
         python tools/recolter_randonnees.py --cadrage  comptages France
                                                        (aucune écriture)
"""

import json
import re
import sys
import urllib.parse
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

import enrichissements as enr

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
CIBLE_POINTS = RACINE / "data" / "points.geojson"

CACHE_WIKI = DOSSIER / "randos-wiki.json"
CACHE_OSM = DOSSIER / "randos-osm.json"
CACHE_CADRAGE = DOSSIER / "randos-cadrage.json"

SEUIL_DOUBLON_M = 500
# Bbox Chartreuse (contrôle qualité : tout point du pilote doit y tomber).
CH_LAT = (45.15, 45.55)
CH_LON = (5.55, 6.05)

# ---------------------------------------------------------------------------
# Liste éditoriale du pilote — massif de la Chartreuse.
# Chaque entrée : nom affiché, titres Wikipédia candidats (le premier trouvé
# gagne), altitude attendue (croisée avec l'article), départ classique
# (+ altitude du parking/col quand elle est bien connue → D+ estimé), durée
# aller-retour quand elle est bien établie, voie normale en une phrase.
# Écartés d'office (documentés dans le rapport) : Le Néron (arête exposée,
# accidents fréquents — pas une randonnée), Roc d'Arguille / Croix de l'Alpe /
# La Scia (pas d'article Wikipédia dédié = pas de notoriété vérifiable).
# ---------------------------------------------------------------------------
RANDOS_PILOTE = [
    {
        "nom": "Chamechaude",
        "titres": ["Chamechaude"],
        "altitude": 2082,
        "depart": "Col de Porte (1326 m)", "depart_alt": 1326,
        "duree": "≈ 4 h aller-retour",
        "voie": "Voie normale par la cabane de Bachasson et la prairie de "
                "la Folatière — point culminant du massif.",
    },
    {
        "nom": "Dent de Crolles",
        "titres": ["Dent de Crolles"],
        "altitude": 2062,
        "depart": "Col du Coq (1434 m)", "depart_alt": 1434,
        "duree": "≈ 3 h 30 aller-retour",
        "voie": "Voie normale par le pas de l'Œille ; boucle classique en "
                "redescendant par le Trou du Glaz.",
    },
    {
        "nom": "Grand Som",
        "titres": ["Grand Som"],
        "altitude": 2026,
        "depart": "La Correrie, Saint-Pierre-de-Chartreuse (≈ 900 m)",
        "depart_alt": 900,
        "duree": "≈ 6 h aller-retour",
        "voie": "Montée au-dessus du monastère de la Grande Chartreuse par "
                "le habert de Bovinant.",
    },
    {
        "nom": "Charmant Som",
        "titres": ["Charmant Som"],
        "altitude": 1867,
        "depart": "Bergerie du Charmant Som, route depuis le col de Porte "
                  "(≈ 1650 m)", "depart_alt": 1650,
        "duree": "≈ 1 h 30 aller-retour",
        "voie": "Courte montée en alpages depuis l'oratoire — panorama et "
                "fromagerie d'alpage en été.",
    },
    {
        "nom": "Mont Granier",
        "titres": ["Mont Granier"],
        "altitude": 1933,
        "depart": "La Plagne, Entremont-le-Vieux (≈ 1100 m)",
        "depart_alt": 1100,
        "duree": "≈ 5 h aller-retour",
        "voie": "Voie normale par le pas des Barres, au-dessus des "
                "impressionnantes falaises de l'éboulement de 1248.",
    },
    {
        "nom": "Grande Sure",
        "titres": ["Grande Sure"],
        "altitude": 1920,
        "depart": "Col de la Charmette (1261 m)", "depart_alt": 1261,
        "duree": "≈ 4 h 30 aller-retour",
        "voie": "Boucle classique par le col de la Sure — belvédère "
                "occidental du massif.",
    },
    {
        "nom": "Petit Som",
        "titres": ["Petit Som"],
        "altitude": 1772,
        "depart": "La Ruchère, Saint-Christophe-sur-Guiers (≈ 1160 m)",
        "depart_alt": 1160,
        "voie": "Montée par le col de Léchaud ou le habert de Bovinant, "
                "au-dessus du monastère.",
    },
    {
        "nom": "Lances de Malissard",
        "titres": ["Lances de Malissard"],
        "altitude": 2045,
        "depart": "Perquelin, Saint-Pierre-de-Chartreuse (≈ 1050 m)",
        "depart_alt": 1050,
        "voie": "Longue montée par le col de Bellefont, sur les hauts "
                "plateaux de la réserve naturelle.",
    },
    {
        "nom": "Dôme de Bellefont",
        "titres": ["Dôme de Bellefont"],
        "altitude": 1975,
        "depart": "Perquelin ou plateau des Petites Roches",
        "voie": "Sommet des hauts plateaux, atteint par le col de Bellefont.",
    },
    {
        "nom": "La Pinéa",
        "titres": ["La Pinéa", "Pinéa"],
        "altitude": 1771,
        "depart": "Col de Porte (1326 m)", "depart_alt": 1326,
        "duree": "≈ 2 h 30 aller-retour",
        "voie": "Petit sommet conique face à Chamechaude, accessible en "
                "famille par la crête.",
    },
    {
        "nom": "Mont Saint-Eynard",
        "titres": ["Mont Saint-Eynard", "Saint-Eynard"],
        "altitude": 1379,
        "depart": "Col de Vence, Le Sappey-en-Chartreuse",
        "voie": "Balcon au-dessus de Grenoble, par le fort du Saint-Eynard.",
    },
    {
        "nom": "Roc de Pravouta",
        "titres": ["Roc de Pravouta", "Pravouta"],
        "altitude": 1760,
        "depart": "Col du Coq (1434 m)", "depart_alt": 1434,
        "duree": "≈ 2 h aller-retour",
        "voie": "Petite boucle panoramique face à la dent de Crolles, "
                "idéale en famille.",
    },
    {
        "nom": "Cirque de Saint-Même",
        "titres": ["Cirque de Saint-Même"],
        "altitude": None,  # objectif non sommital : altitude non affichée
        "depart": "Parking du cirque, Saint-Même-d'en-Haut (≈ 870 m)",
        "depart_alt": None,
        "duree": "≈ 2 h 30 (boucle)",
        "voie": "Boucle des quatre cascades du Guiers vif, au pied des "
                "falaises du cirque.",
    },
    {
        "nom": "Mont Outheran",
        "titres": ["Mont Outheran"],
        "altitude": 1676,
        "depart": "Le Désert d'Entremont",
        "voie": "Sommet nord du massif, en forêt puis en crête.",
    },
    {
        "nom": "Roche Veyrand",
        "titres": ["Roche Veyrand"],
        "altitude": 1429,
        "depart": "Saint-Pierre-d'Entremont",
        "voie": "Belvédère sur les Entremonts, par le sentier en forêt "
                "(une via ferrata gravit la face ouest).",
    },
]


# ---------------------------------------------------------------------------
# Utilitaires (mêmes conventions que recolter_lacs.py)
# ---------------------------------------------------------------------------

def normaliser_nom(texte):
    t = enr.normaliser(texte or "")
    t = re.sub(r"\bst\b", "saint", t)
    return re.sub(r"[^a-z0-9]", "", t)


def _distance_m(a, b):
    lat1, lon1 = radians(a["lat"]), radians(a["lon"])
    lat2, lon2 = radians(b["lat"]), radians(b["lon"])
    h = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * asin(sqrt(h))


def _nettoyer_extrait(texte, maxi=340):
    """1-2 phrases propres du résumé introductif."""
    t = re.sub(r"\s+", " ", (texte or "")).strip()
    t = re.sub(r"\[\d+\]", "", t)
    if not t:
        return ""
    phrases = re.split(r"(?<=[.!?]) ", t)
    resultat = ""
    for p in phrases:
        if resultat and len(resultat) + len(p) > maxi:
            break
        resultat = (resultat + " " + p).strip()
        if len(resultat) >= 160:
            break
    return resultat


# ---------------------------------------------------------------------------
# Wikipédia : coordonnées + photo + résumé, par lot, avec suivi de continue
# (colimit=max obligatoire — voir CLAUDE.md, bug des 10 coordonnées).
# ---------------------------------------------------------------------------

def pages_wikipedia(titres):
    cache = {}
    if CACHE_WIKI.exists():
        cache = json.loads(CACHE_WIKI.read_text(encoding="utf-8"))
    manquants = [t for t in titres if t not in cache]
    for i in range(0, len(manquants), 20):   # exlimit=max ≤ 20 avec exintro
        lot = manquants[i:i + 20]
        params = {
            "action": "query", "format": "json", "redirects": 1,
            "prop": "coordinates|pageimages|extracts|info",
            "colimit": "max", "coprimary": "primary",
            "piprop": "thumbnail", "pithumbsize": 500,
            "exintro": 1, "explaintext": 1, "exlimit": "max",
            "inprop": "url",
            "titles": "|".join(lot),
        }
        pages, suivants = {}, {}      # suivants : titre demandé → titre final
        continuer = {}
        while True:
            d = enr.http_json("https://fr.wikipedia.org/w/api.php?" +
                              urllib.parse.urlencode({**params, **continuer}))
            q = d.get("query", {})
            # Chaîne AVANT (from → to) : deux titres demandés peuvent aboutir
            # à la MÊME page (« Petit Som » redirige vers « Grand Som ») —
            # une chaîne inversée perdrait l'un des deux.
            for n in q.get("normalized", []) + q.get("redirects", []):
                suivants[n["from"]] = n["to"]
            for pid, page in q.get("pages", {}).items():
                fiche = pages.setdefault(pid, {"titre": page.get("title", "")})
                if "missing" in page:
                    fiche["absent"] = True
                if page.get("coordinates"):
                    c = page["coordinates"][0]
                    fiche["lat"], fiche["lon"] = c["lat"], c["lon"]
                if page.get("thumbnail"):
                    fiche["thumb"] = page["thumbnail"].get("source", "")
                if page.get("extract"):
                    fiche["extract"] = page["extract"]
                if page.get("fullurl"):
                    fiche["url"] = page["fullurl"]
            if "continue" not in d:
                break
            continuer = d["continue"]
        par_titre = {f["titre"]: f for f in pages.values()}
        for t in lot:
            final, vus = t, set()
            while final in suivants and final not in vus:
                vus.add(final)
                final = suivants[final]
            fiche = par_titre.get(final)
            cache[t] = None if (fiche is None or fiche.get("absent")) else fiche
        CACHE_WIKI.write_text(json.dumps(cache, ensure_ascii=False),
                              encoding="utf-8")
    return cache


def verifier_altitude(entree, page):
    """Croise l'altitude éditoriale avec le texte de l'article (anti-typo)."""
    if not entree["altitude"] or not page.get("extract"):
        return True
    alt = entree["altitude"]
    variantes = {str(alt), f"{alt // 1000} {alt % 1000:03d}",
                 f"{alt // 1000} {alt % 1000:03d}",
                 f"{alt // 1000} {alt % 1000:03d}"}
    return any(v in page["extract"] for v in variantes)


# ---------------------------------------------------------------------------
# OSM : relations route=hiking de la bbox Chartreuse (corroboration).
# ---------------------------------------------------------------------------

def relations_osm_chartreuse():
    if CACHE_OSM.exists():
        return json.loads(CACHE_OSM.read_text(encoding="utf-8"))
    requete = (f'[out:json][timeout:180];'
               f'relation["route"="hiking"]["name"]'
               f'({CH_LAT[0]},{CH_LON[0]},{CH_LAT[1]},{CH_LON[1]});out tags;')
    d = enr._overpass(requete)
    elements = d.get("elements", [])
    CACHE_OSM.write_text(json.dumps(elements, ensure_ascii=False),
                         encoding="utf-8")
    return elements


def corroborer_osm(candidats, relations):
    """Marque les randonnées dont le nom apparaît dans une relation balisée."""
    noms_rel = [(r["tags"].get("name", ""),
                 normaliser_nom(r["tags"].get("name", ""))) for r in relations]
    for c in candidats:
        cle = normaliser_nom(c["nom"])
        c["osm_relations"] = [brut for brut, n in noms_rel if cle and cle in n]


# ---------------------------------------------------------------------------
# Construction des features
# ---------------------------------------------------------------------------

def construire_candidats(stats):
    pages = pages_wikipedia([t for e in RANDOS_PILOTE for t in e["titres"]])
    noms_pilote = {normaliser_nom(e["nom"]): e["nom"] for e in RANDOS_PILOTE}
    candidats = []
    for entree in RANDOS_PILOTE:
        cle_entree = normaliser_nom(entree["nom"])
        page = None
        for t in entree["titres"]:
            fiche = pages.get(t)
            if not fiche:
                continue
            # Redirection vers l'article d'une AUTRE entrée du pilote
            # (« Petit Som » → « Grand Som ») = pas d'article dédié → écarté,
            # sinon deux points identiques dont un mal nommé.
            cle_page = normaliser_nom(fiche["titre"])
            if cle_page != cle_entree and cle_page in noms_pilote:
                continue
            page = fiche
            break
        if not page:
            stats["sans_article"] += 1
            stats.setdefault("_sans_article", []).append(entree["nom"])
            continue
        if "lat" not in page:
            stats["sans_coordonnees"] += 1
            stats.setdefault("_sans_coords", []).append(entree["nom"])
            continue
        if not (CH_LAT[0] <= page["lat"] <= CH_LAT[1]
                and CH_LON[0] <= page["lon"] <= CH_LON[1]):
            stats["hors_bbox"] += 1
            stats.setdefault("_hors_bbox", []).append(entree["nom"])
            continue
        if not verifier_altitude(entree, page):
            stats["altitude_non_confirmee"] += 1
            stats.setdefault("_alt_douteuse", []).append(entree["nom"])
        candidats.append({**entree, "lat": page["lat"], "lon": page["lon"],
                          "extract": _nettoyer_extrait(page.get("extract")),
                          "thumb": page.get("thumb", ""),
                          "wiki_url": page.get("url", "")})
    return candidats


def _construire_feature(c, id_):
    details = {"massif": "Chartreuse"}
    if c["altitude"]:
        details["altitude"] = f"{c['altitude']:,} m".replace(",", " ")
        details["altitude_n"] = c["altitude"]
    if c["altitude"] and c.get("depart_alt"):
        dplus = c["altitude"] - c["depart_alt"]
        if dplus > 0:
            details["denivele"] = f"≈ {dplus} m"
            details["denivele_n"] = dplus
    if c.get("duree"):
        details["duree"] = c["duree"]
    if c.get("depart"):
        details["depart"] = c["depart"]
    if c.get("voie"):
        details["acces"] = c["voie"]
    if c.get("osm_relations"):
        details["itineraire"] = c["osm_relations"][0]
    desc = " ".join(x for x in (c["extract"], c.get("voie", "")) if x).strip()
    photo = c["thumb"] if (c["thumb"] or "").startswith(
        "https://upload.wikimedia.org") else ""
    # « Référencée » = photo ET une vraie information (résumé Wikipédia).
    details["fiche"] = ("Référencée" if photo and c["extract"]
                        else "À vérifier")
    return {"type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]},
            "properties": {"id": id_, "name": c["nom"], "theme": "randonnee",
                           "description": desc, "link": c["wiki_url"],
                           "photos": [photo] if photo else [],
                           "details": details}}


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


def convertir_randonnees(autres_features, precedents):
    stats = {k: 0 for k in ("sans_article", "sans_coordonnees", "hors_bbox",
                            "altitude_non_confirmee", "doublons_existants",
                            "ids_reutilises", "ajoutes", "conserves_sans_source",
                            "osm_corroborees")}
    candidats = construire_candidats(stats)
    try:
        corroborer_osm(candidats, relations_osm_chartreuse())
    except Exception as e:                       # corroboration facultative
        print(f"  (Overpass indisponible, corroboration sautée : {e})")
        for c in candidats:
            c["osm_relations"] = []
    stats["osm_corroborees"] = sum(1 for c in candidats if c["osm_relations"])

    index_autres = _index_par_nom(autres_features)
    index_prec = _index_par_nom(precedents)
    ids_pris = {f["properties"]["id"] for f in precedents}

    def prochain_id():
        n = 1
        while f"rando-{n:04d}" in ids_pris:
            n += 1
        ids_pris.add(f"rando-{n:04d}")
        return f"rando-{n:04d}"

    features, ids_reutilises = [], set()
    candidats.sort(key=lambda c: (normaliser_nom(c["nom"]), c["lon"]))
    for c in candidats:
        cle = normaliser_nom(c["nom"])
        prec = next((e for e in index_prec.get(cle, [])
                     if _distance_m(c, e) < SEUIL_DOUBLON_M
                     and e["feature"]["properties"]["id"] not in ids_reutilises),
                    None)
        if prec:
            id_ = prec["feature"]["properties"]["id"]
            ids_reutilises.add(id_)
            features.append(_construire_feature(c, id_))
            stats["ids_reutilises"] += 1
            continue
        # Même nom < 500 m dans une autre catégorie : signalé, non créé
        # (un objectif de rando homonyme ET co-localisé = même lieu).
        autre = next((e for e in index_autres.get(cle, [])
                      if _distance_m(c, e) < SEUIL_DOUBLON_M), None)
        if autre:
            stats["doublons_existants"] += 1
            stats.setdefault("_doublons", []).append(
                f"{c['nom']} ↔ {autre['feature']['properties']['id']}")
            continue
        features.append(_construire_feature(c, prochain_id()))
        stats["ajoutes"] += 1

    for f in precedents:                 # ids jamais supprimés (statuts/carnet)
        if f["properties"]["id"] not in ids_reutilises:
            features.append(f)
            stats["conserves_sans_source"] += 1
    features.sort(key=lambda f: f["properties"]["id"])
    return features, stats


# ---------------------------------------------------------------------------
# Volet cadrage : comptages Overpass France (AUCUNE récolte, AUCUNE écriture).
# ---------------------------------------------------------------------------

def cadrage_france():
    """Deux requêtes de comptage seul (out count), cachées séparément —
    la version combinée expirait : le balayage des nœuds France est lourd.
    Filtres par PRÉSENCE de « wikidata » (les regex sur clé sont trop chères
    à cette échelle — timeout vécu). Timeout serveur < timeout client (240 s)."""
    cache = (json.loads(CACHE_CADRAGE.read_text(encoding="utf-8"))
             if CACHE_CADRAGE.exists() else {})
    if isinstance(cache, dict) and "elements" in cache:   # ancien format
        # Le volet relations était complet (2 comptes) malgré le timeout
        # survenu ensuite sur les nœuds : on le garde, sans le remark.
        cache = {"relations": {"elements": cache["elements"]}} \
            if len(cache.get("elements", [])) == 2 else {}
    comptes = []
    # 1) Relations route=hiking : Overpass (comptage seul, rapide).
    d = cache.get("relations")
    if not d or d.get("remark"):
        d = enr._overpass('[out:json][timeout:200];'
                          'area["ISO3166-1"="FR"][admin_level=2]->.fr;'
                          'relation["route"="hiking"]["name"](area.fr)->.rh;'
                          '.rh out count;'
                          'relation.rh["wikidata"]->.rhw;.rhw out count;')
        cache["relations"] = d
        CACHE_CADRAGE.write_text(json.dumps(cache, ensure_ascii=False),
                                 encoding="utf-8")
    comptes += [int(e["tags"]["total"]) for e in d.get("elements", [])
                if e.get("type") == "count"]
    # 2) Sommets : Wikidata SPARQL — le comptage Overpass des nœuds peak à
    # l'échelle France expire (> 200 s, vécu deux fois), et le vrai critère
    # de notoriété est l'ARTICLE Wikipédia fr, que Wikidata donne directement.
    # UNE SEULE requête (3 sous-selects) : le WDQS peut être limité à
    # 1 req/min (vécu : « aggressively rate-limiting » pendant une panne),
    # et il exige l'en-tête Accept (502 sans lui).
    if "sommets" not in cache:
        def sous(nom, filtre):
            return (f"{{ SELECT (COUNT(DISTINCT ?m{nom}) AS ?{nom}) WHERE {{ "
                    f"?m{nom} wdt:P31 wd:Q8502; wdt:P17 wd:Q142; "
                    f"wdt:P2044 ?e{nom}. ?a{nom} schema:about ?m{nom}; "
                    f"schema:isPartOf <https://fr.wikipedia.org/>. {filtre} }} }}")
        q = ("SELECT ?tous ?s1500 ?s2000 WHERE { "
             + sous("tous", "")
             + sous("s1500", "FILTER(?es1500 >= 1500)")
             + sous("s2000", "FILTER(?es2000 >= 2000)") + " }")
        import urllib.request
        req = urllib.request.Request(
            "https://query.wikidata.org/sparql?format=json&query="
            + urllib.parse.quote(q),
            headers={**enr.UA, "Accept": "application/sparql-results+json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            b = json.loads(r.read().decode())["results"]["bindings"][0]
        cache["sommets"] = [int(b[k]["value"])
                            for k in ("tous", "s1500", "s2000")]
        CACHE_CADRAGE.write_text(json.dumps(cache, ensure_ascii=False),
                                 encoding="utf-8")
    comptes += cache["sommets"]
    libelles = [
        "relations route=hiking nommées (Overpass, France entière DOM inclus)",
        "  … dont taguées wikidata",
        "montagnes de France avec article Wikipédia fr + altitude (Wikidata)",
        "  … dont altitude ≥ 1500 m",
        "  … dont altitude ≥ 2000 m"]
    for lib, n in zip(libelles, comptes):
        print(f"  {lib} : {n}")
    return comptes


# ---------------------------------------------------------------------------
# Exécution autonome
# ---------------------------------------------------------------------------

def _bilan(features, stats):
    total = len(features) or 1
    avec = lambda test: sum(1 for f in features if test(f["properties"]))
    print(f"""
Bilan randonnées (pilote Chartreuse)
  liste éditoriale : {len(RANDOS_PILOTE)} candidates
  écartées : sans article Wikipédia {stats['sans_article']} {stats.get('_sans_article', '')}
             sans coordonnées {stats['sans_coordonnees']} {stats.get('_sans_coords', '')}
             hors bbox Chartreuse {stats['hors_bbox']} {stats.get('_hors_bbox', '')}
  altitude éditoriale non confirmée par l'article : {stats['altitude_non_confirmee']} {stats.get('_alt_douteuse', '')}
  corroborées par une relation OSM route=hiking : {stats['osm_corroborees']}
  doublons avec l'existant (non créés) : {stats['doublons_existants']} {stats.get('_doublons', '')}
  ids réutilisés : {stats['ids_reutilises']}, conservés sans source : {stats['conserves_sans_source']}
  AJOUTÉES : {stats['ajoutes']}  (total catégorie : {len(features)})
  couverture : photo {avec(lambda p: p.get('photos')) * 100 // total} %,
               description {avec(lambda p: p.get('description')) * 100 // total} %,
               D+ {avec(lambda p: 'denivele' in p.get('details', {})) * 100 // total} %,
               durée {avec(lambda p: 'duree' in p.get('details', {})) * 100 // total} %,
               fiche Référencée {avec(lambda p: p.get('details', {}).get('fiche') == 'Référencée') * 100 // total} %""")


def main(dry_run=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--cadrage" in sys.argv:
        cadrage_france()
        return 0
    collection = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
    autres = [f for f in collection["features"]
              if f["properties"].get("theme") != "randonnee"]
    precedents = [f for f in collection["features"]
                  if f["properties"].get("theme") == "randonnee"]
    print(f"points.geojson : {len(autres)} points existants, "
          f"{len(precedents)} randonnées déjà en base")
    randos, stats = convertir_randonnees(autres, precedents)
    _bilan(randos, stats)
    if dry_run:
        print("(--dry-run : rien n'a été écrit)")
        return 0
    collection["features"] = autres + randos
    CIBLE_POINTS.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"points.geojson : {len(collection['features'])} features, "
          f"{CIBLE_POINTS.stat().st_size // 1024} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
