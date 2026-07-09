# -*- coding: utf-8 -*-
"""
Récolte des cascades de France métropolitaine (+ Corse) et fusion dans
data/points.geojson (catégorie « cascade », ids casc-0001…).

Source principale : OpenStreetMap via Overpass (waterway=waterfall), par
tuiles de 3°, restreint au territoire français (area ISO3166-1=FR — la bbox
métropole mord sur la Suisse, l'Italie, l'Espagne… sans ce filtre).
Enrichissement : Wikipédia (article, photo upload.wikimedia.org, résumé)
pour les cascades portant un tag wikipedia/wikidata, ou dont le nom évoque
clairement une cascade (lien accepté seulement si l'article est géolocalisé
à moins de 2 km du point OSM — évite les homonymes).

Règles de sélection :
  - access=private|no écartés ;
  - cascades sans nom : gardées seulement si elles apportent quelque chose
    (tag height, wikipedia ou wikidata), nommées « Cascade (Commune) » par
    géocodage inverse geo.api.gouv.fr — sinon écartées ;
  - doublons internes : même nom normalisé à < 500 m → fiche la plus
    complète (complétée par les champs des doublons) ;
  - doublons avec l'existant (toutes catégories) : même nom à < 500 m →
    fusion dans le point EXISTANT (id conservé, seuls les champs manquants
    sont ajoutés), aucun nouveau point.

Ids stables : une ré-exécution réattribue à chaque cascade déjà présente
dans points.geojson son id (correspondance nom + < 500 m) ; les nouvelles
continuent la séquence. Ne JAMAIS renuméroter.

Caches (tools/, gitignorés, repris d'une exécution à l'autre) :
  cascades-osm.json       éléments Overpass (sauvé si TOUTES les tuiles réussissent)
  cascades-communes.json  géocodage inverse des cascades sans nom
  cascades-wikidata.json  Qxxx → titre frwiki
  cascades-wiki.json      titre → {url, thumb, extract, lat, lon} | null

Usage :  python tools/recolter_cascades.py           récolte + fusion
         python tools/recolter_cascades.py --dry-run récolte + bilan, sans écrire
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

CACHE_OSM = DOSSIER / "cascades-osm.json"
CACHE_COMMUNES_INV = DOSSIER / "cascades-communes.json"
CACHE_WIKIDATA = DOSSIER / "cascades-wikidata.json"
CACHE_WIKI = DOSSIER / "cascades-wiki.json"

LAT_MIN, LAT_MAX = 41.0, 51.5
LON_MIN, LON_MAX = -5.5, 10.0

SEUIL_DOUBLON_M = 500       # même nom à < 500 m = même cascade
SEUIL_COORD_WIKI_M = 2000   # écart max article deviné ↔ point OSM
MAX_NOUVELLES = 5000        # garde-fou : au-delà, décision utilisateur requise

RE_HAUTEUR = re.compile(r"(\d+(?:[.,]\d+)?)")
RE_NOM_TECHNIQUE = re.compile(r"^(?:node|way|relation)[ /]?\d+$|^\d+$|^unnamed$", re.I)
# Noms « clairement cascade » : seuls ceux-là sont tentés sur Wikipédia sans
# tag wikipedia/wikidata (l'article doit en plus être à < 2 km du point).
RE_NOM_CASCADE = re.compile(r"cascade|chute|saut|voile")


def normaliser_nom(texte):
    """minuscules, sans accents/ponctuation, St↔Saint — pour comparer."""
    texte = re.sub(r"\bSte?s?\b\.?", "Saint", texte or "", flags=re.I)
    return enr.normaliser(texte).replace("sainte", "saint")


def _nettoyer_texte(texte, maxi=350):
    """Supprime les balises HTML, unifie les espaces, tronque au mot."""
    t = re.sub(r"<[^>]+>", " ", texte or "")
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) > maxi:
        t = t[:maxi].rsplit(" ", 1)[0].rstrip(",;:. ") + "…"
    return t


def _distance_m(a, b):
    """Distance en mètres entre deux candidats/points {lon, lat}."""
    return enr._haversine((a["lon"], a["lat"]), (b["lon"], b["lat"]))


# ---------------------------------------------------------------------------
# 1. Récolte Overpass
# ---------------------------------------------------------------------------

def telecharger_cascades():
    """Tous les waterway=waterfall de France métropolitaine + Corse
    (nœuds + centres des ways/relations), par tuiles de 3°. Le cache n'est
    sauvegardé QUE si toutes les tuiles ont réussi."""
    if CACHE_OSM.exists():
        return json.loads(CACHE_OSM.read_text(encoding="utf-8"))
    print("  téléchargement Overpass (waterway=waterfall)…")
    pas = 3.0
    tuiles = []
    lon = LON_MIN
    while lon < LON_MAX:
        lat = LAT_MIN
        while lat < LAT_MAX:
            # bbox Overpass : sud, ouest, nord, est
            tuiles.append(f"{lat},{lon},{min(lat + pas, LAT_MAX)},{min(lon + pas, LON_MAX)}")
            lat += pas
        lon += pas
    elements = {}
    # 3 passes : les tuiles en échec (Overpass surchargé) sont retentées
    # après une longue pause plutôt que de rejouer toute la récolte.
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
                       f'nwr["waterway"="waterfall"](area.fr)({bbox});'
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
        print(f"  ! {len(tuiles)} tuile(s) en échec : cache NON sauvegardé, relancer le script")
    else:
        CACHE_OSM.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    print(f"  Overpass : {len(liste)} éléments waterfall")
    return liste


# ---------------------------------------------------------------------------
# 2. Éléments OSM → candidats
# ---------------------------------------------------------------------------

def _hauteur_m(tags):
    """Tag height → hauteur en mètres (0,5 à 500 m), ou None."""
    m = RE_HAUTEUR.search((tags.get("height") or "").strip())
    if not m:
        return None
    try:
        v = float(m.group(1).replace(",", "."))
    except ValueError:
        return None
    return v if 0.5 <= v <= 500 else None


def _titre_wikipedia_fr(tags):
    """Tag wikipedia → titre frwiki, ou None (autre langue : inexploitable)."""
    if tags.get("wikipedia:fr"):
        return tags["wikipedia:fr"].strip()
    brut = (tags.get("wikipedia") or "").strip()
    if not brut:
        return None
    lang, sep, titre = brut.partition(":")
    if not sep:
        return brut
    return titre.strip() if lang.strip().lower() == "fr" else None


def extraire_candidats(elements, stats):
    candidats = []
    for e in sorted(elements, key=lambda x: (x["type"], x["id"])):
        tags = e.get("tags") or {}
        if tags.get("waterway") != "waterfall":
            continue
        stats["elements_osm"] += 1
        if tags.get("access") in ("private", "no"):
            stats["prives"] += 1
            continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or lon is None:
            stats["sans_coordonnees"] += 1
            continue
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            stats["hors_bornes"] += 1
            continue

        nom = re.sub(r"\s+", " ", (tags.get("name") or tags.get("name:fr") or "")).strip()
        if nom and (RE_NOM_TECHNIQUE.match(nom) or not normaliser_nom(nom)):
            stats["noms_rejetes"] += 1
            nom = ""  # nom inutilisable : traité comme une cascade sans nom

        hauteur = _hauteur_m(tags)
        wikipedia = _titre_wikipedia_fr(tags)
        wikidata = None
        m = re.match(r"(Q\d+)", (tags.get("wikidata") or "").strip())
        if m:
            wikidata = m.group(1)
        if not nom and not (hauteur or wikipedia or wikidata):
            stats["anonymes_ecartees"] += 1
            continue  # une chute anonyme sans rien n'apporte rien

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

        candidats.append({
            "osm": f"{e['type']}/{e['id']}",
            "type": e["type"],
            "lat": lat, "lon": lon,
            "nom": nom or None,          # None = à nommer par la commune
            "nom_devine": not nom,
            "hauteur": hauteur,
            "ele": ele,
            "wikipedia": wikipedia,
            "wikidata": wikidata,
            "website": website,
            "descr_osm": _nettoyer_texte(tags.get("description") or "", 300),
            "intermittent": tags.get("intermittent") == "yes",
            "commune": "",
        })
    return candidats


# ---------------------------------------------------------------------------
# 3. Cascades sans nom → « Cascade (Commune) » (géocodage inverse)
# ---------------------------------------------------------------------------

def nommer_sans_nom(candidats, stats):
    """Nomme les candidats sans nom d'après leur commune (geo.api.gouv.fr).
    Échec du géocodage (mer, enclave, réseau) → candidat écarté."""
    cache = json.loads(CACHE_COMMUNES_INV.read_text(encoding="utf-8")) if CACHE_COMMUNES_INV.exists() else {}
    sans_nom = [c for c in candidats if c["nom"] is None]
    a_faire = [c for c in sans_nom if f"{c['lat']:.4f},{c['lon']:.4f}" not in cache]
    if a_faire:
        print(f"  géocodage inverse de {len(a_faire)} cascades sans nom…")
    for i, c in enumerate(a_faire, 1):
        cle = f"{c['lat']:.4f},{c['lon']:.4f}"
        try:
            d = enr.http_json("https://geo.api.gouv.fr/communes?"
                              + urllib.parse.urlencode({"lat": f"{c['lat']:.6f}",
                                                        "lon": f"{c['lon']:.6f}",
                                                        "fields": "nom", "format": "json"}))
            cache[cle] = d[0]["nom"] if d else None
        except Exception as exc:
            print(f"    ! {cle} : {exc}")  # échec réseau : pas mis en cache, retenté
        if i % 25 == 0 or i == len(a_faire):
            CACHE_COMMUNES_INV.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    {i}/{len(a_faire)}")
        time.sleep(0.15)
    gardes = []
    for c in candidats:
        if c["nom"] is None:
            commune = cache.get(f"{c['lat']:.4f},{c['lon']:.4f}")
            if not commune:
                stats["sans_commune"] += 1
                continue
            c["nom"] = f"Cascade ({commune})"
            c["commune"] = commune
        gardes.append(c)
    return gardes


# ---------------------------------------------------------------------------
# 4. Dédoublonnage interne (même nom normalisé à < 500 m)
# ---------------------------------------------------------------------------

def _score(c):
    """Complétude d'une fiche (pour choisir laquelle garder entre doublons)."""
    return ((3 if c["wikipedia"] or c["wikidata"] else 0)
            + (2 if c["hauteur"] else 0)
            + (1 if c["descr_osm"] else 0)
            + (1 if c["website"] else 0)
            + (0.5 if c["ele"] else 0)
            + (0.25 if c["type"] == "node" else 0))


def dedoublonner_interne(candidats, stats):
    par_nom = {}
    for c in candidats:
        par_nom.setdefault(normaliser_nom(c["nom"]), []).append(c)
    gardes = []
    for groupe in par_nom.values():
        groupe.sort(key=lambda c: (-_score(c), c["osm"]))
        retenus = []
        for c in groupe:
            proche = next((r for r in retenus if _distance_m(c, r) < SEUIL_DOUBLON_M), None)
            if proche:
                stats["doublons_internes"] += 1
                # la fiche retenue récupère ce que le doublon apportait en plus
                for cle in ("hauteur", "ele", "website", "descr_osm", "wikipedia", "wikidata"):
                    if not proche.get(cle) and c.get(cle):
                        proche[cle] = c[cle]
                proche["intermittent"] = proche["intermittent"] or c["intermittent"]
            else:
                retenus.append(c)
        gardes.extend(retenus)
    return gardes


# ---------------------------------------------------------------------------
# 5. Enrichissement Wikipédia (article, photo, résumé)
# ---------------------------------------------------------------------------

def _resoudre_wikidata(qids):
    """{Qxxx: titre frwiki | None}, par lots de 50, avec cache."""
    cache = json.loads(CACHE_WIKIDATA.read_text(encoding="utf-8")) if CACHE_WIKIDATA.exists() else {}
    a_faire = sorted({q for q in qids if q and q not in cache})
    if a_faire:
        print(f"  Wikidata : {len(a_faire)} entités à résoudre vers frwiki…")
    for i in range(0, len(a_faire), 50):
        lot = a_faire[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
               "&props=sitelinks&sitefilter=frwiki&ids=" + "|".join(lot))
        try:
            d = enr.http_json(url)
        except Exception as exc:
            print(f"    ! wikidata : {exc}")
            break
        for q, ent in (d.get("entities") or {}).items():
            titre = ((ent.get("sitelinks") or {}).get("frwiki") or {}).get("title")
            cache[q] = titre or None
        CACHE_WIKIDATA.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 50, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.4)
    return cache


def _pages_cascades(titres):
    """{ "t:"+titre : {url, thumb, extract, lat, lon} | None }.

    Lots de 20 titres (limite exlimit de prop=extracts), colimit=max ET suivi
    de « continue » (sans quoi l'API ne renvoie que 10 coordonnées/réponse),
    cache sauvegardé à chaque lot (les 429 arrivent par vagues)."""
    cache = json.loads(CACHE_WIKI.read_text(encoding="utf-8")) if CACHE_WIKI.exists() else {}
    a_faire = [t for t in dict.fromkeys(titres) if "t:" + t not in cache]
    if a_faire:
        print(f"  Wikipédia : {len(a_faire)} titres à interroger…")
    for i in range(0, len(a_faire), 20):
        lot = a_faire[i:i + 20]
        params = {"action": "query", "format": "json", "redirects": "1",
                  "prop": "coordinates|pageimages|extracts|info|pageprops",
                  "colimit": "max",
                  "piprop": "thumbnail", "pithumbsize": "400", "pilimit": "max",
                  "exintro": "1", "explaintext": "1", "exsentences": "2", "exlimit": "max",
                  "ppprop": "disambiguation", "inprop": "url",
                  "titles": "|".join(lot)}
        pages, corresp, cont = {}, {}, {}
        while True:
            d = enr.http_json(enr.API_WIKI + "?" + urllib.parse.urlencode({**params, **cont}))
            q = d.get("query", {})
            for n in q.get("normalized", []) + q.get("redirects", []):
                corresp.setdefault(n["to"], n["from"])
            for pid, page in (q.get("pages") or {}).items():
                fusion = pages.setdefault(pid, {})
                for cle, val in page.items():
                    fusion.setdefault(cle, val)
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items() if k != "continue"}
            time.sleep(0.3)

        def titre_origine(t):
            vus = set()
            while t in corresp and t not in vus:
                vus.add(t)
                t = corresp[t]
            return t

        for page in pages.values():
            origine = titre_origine(page.get("title", ""))
            if "missing" in page or "disambiguation" in (page.get("pageprops") or {}):
                cache["t:" + origine] = None
            else:
                coord = (page.get("coordinates") or [{}])[0]
                cache["t:" + origine] = {
                    "url": page.get("fullurl", ""),
                    "thumb": (page.get("thumbnail") or {}).get("source", ""),
                    "extract": _nettoyer_texte(page.get("extract", "")),
                    "lat": coord.get("lat"), "lon": coord.get("lon"),
                }
        for t in lot:  # titres restés sans réponse (invalides…)
            cache.setdefault("t:" + t, None)
        CACHE_WIKI.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 20, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.5)
    return cache


def enrichir_wikipedia(candidats, stats):
    """Pose wiki_url / photo / extrait sur les candidats.
    Tag wikipedia/wikidata = lien de confiance ; nom deviné = accepté
    seulement si l'article est géolocalisé à < 2 km du point OSM."""
    wd = _resoudre_wikidata([c["wikidata"] for c in candidats
                             if not c["wikipedia"] and c["wikidata"]])
    demandes = []  # (candidat, titre, lien_sur)
    for c in candidats:
        titre, sur_tag = None, False
        if c["wikipedia"]:
            titre, sur_tag = c["wikipedia"], True
        elif c["wikidata"] and wd.get(c["wikidata"]):
            titre, sur_tag = wd[c["wikidata"]], True
        elif not c["nom_devine"] and RE_NOM_CASCADE.search(normaliser_nom(c["nom"])):
            titre = c["nom"]
        if titre:
            titre = titre.replace("_", " ").strip()
            if titre and "|" not in titre and "#" not in titre:
                demandes.append((c, titre, sur_tag))
    cache = _pages_cascades([t for _, t, _ in demandes])
    for c, titre, sur_tag in demandes:
        page = cache.get("t:" + titre)
        if not page or not page.get("url"):
            continue
        if not sur_tag:
            if page["lat"] is None or _distance_m(c, page) > SEUIL_COORD_WIKI_M:
                stats["wiki_trop_loin"] += 1
                continue
        c["wiki_url"] = page["url"]
        if (page.get("thumb") or "").startswith("https://upload.wikimedia.org"):
            c["photo"] = page["thumb"]
        if page.get("extract"):
            c["extrait"] = page["extract"]
        stats["wiki_lies"] += 1


# ---------------------------------------------------------------------------
# 6. Candidats → features, fusion avec l'existant, attribution des ids
# ---------------------------------------------------------------------------

def _construire_feature(c, id_):
    details = {}
    if c["hauteur"]:
        h = c["hauteur"]
        if float(h).is_integer():
            details["hauteur"], details["hauteur_n"] = f"{int(h)} m", int(h)
        else:
            details["hauteur"] = f"{h:.1f} m".replace(".", ",")
            details["hauteur_n"] = round(h, 1)
    if c["ele"]:
        details["altitude"] = f"{c['ele']} m"
    desc = c.get("extrait") or c.get("descr_osm") or ""
    if not desc:
        desc = (f"Cascade sans nom précis dans OpenStreetMap, sur la commune de {c['commune']}."
                if c["nom_devine"] else
                "Cascade référencée par les contributeurs OpenStreetMap.")
    if c["intermittent"]:
        desc += " Cours d'eau intermittent : la cascade peut être à sec une partie de l'année."
    props = {
        "id": id_,
        "name": c["nom"],
        "theme": "cascade",
        "description": desc,
        "link": c.get("wiki_url") or c.get("website") or "",
        "photos": [c["photo"]] if c.get("photo") else [],
        "details": details,
    }
    if c.get("wiki_url") and c.get("website"):
        props["links"] = [{"label": "Site officiel", "url": c["website"]}]
    return {"type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(c["lon"], 6), round(c["lat"], 6)]},
            "properties": props}


def _index_par_nom(features):
    """nomNormalisé → [{feature, lon, lat}] (features avec géométrie Point)."""
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
    """Complète le point existant avec les champs manquants du candidat."""
    p = entree["feature"]["properties"]
    if not p.get("link") and (c.get("wiki_url") or c.get("website")):
        p["link"] = c.get("wiki_url") or c.get("website")
    if not p.get("photos") and c.get("photo"):
        p["photos"] = [c["photo"]]
    if not p.get("description") and (c.get("extrait") or c.get("descr_osm")):
        p["description"] = c.get("extrait") or c.get("descr_osm")
    stats["fusionnes"] += 1


def convertir_cascades(autres_features, precedentes=None):
    """Construit les features « cascade » et fusionne les doublons dans les
    points existants (autres_features est MUTÉ : champs manquants complétés).

    precedentes : features cascade déjà en base (préservation des ids) ;
    None → lues depuis data/points.geojson si le fichier existe.
    Renvoie (features_cascade, stats)."""
    if precedentes is None:
        precedentes = []
        if CIBLE_POINTS.exists():
            anciennes = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
            precedentes = [f for f in anciennes.get("features", [])
                           if f.get("properties", {}).get("theme") == "cascade"]

    stats = {k: 0 for k in ("elements_osm", "prives", "sans_coordonnees",
                            "hors_bornes", "noms_rejetes", "anonymes_ecartees",
                            "sans_commune", "doublons_internes", "wiki_lies",
                            "wiki_trop_loin", "fusionnes", "ajoutes",
                            "ids_reutilises", "conservees_sans_source")}

    candidats = extraire_candidats(telecharger_cascades(), stats)
    candidats = nommer_sans_nom(candidats, stats)
    candidats = dedoublonner_interne(candidats, stats)
    enrichir_wikipedia(candidats, stats)

    index_autres = _index_par_nom(autres_features)
    index_prec = _index_par_nom(precedentes)
    ids_pris = {f["properties"]["id"] for f in precedentes}

    def prochain_id():
        n = 1
        while f"casc-{n:04d}" in ids_pris:
            n += 1
        ids_pris.add(f"casc-{n:04d}")
        return f"casc-{n:04d}"

    features = []
    ids_reutilises = set()
    candidats.sort(key=lambda c: (normaliser_nom(c["nom"]), c["lon"], c["lat"]))
    for c in candidats:
        cle = normaliser_nom(c["nom"])
        # 1. déjà en base en tant que cascade → même id, fiche réactualisée
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

    # Cascades précédentes disparues de la récolte : conservées telles quelles
    # (les statuts/carnet des utilisateurs pointent sur leurs ids).
    for f in precedentes:
        if f["properties"]["id"] not in ids_reutilises:
            features.append(f)
            stats["conservees_sans_source"] += 1

    if stats["ajoutes"] > MAX_NOUVELLES:
        raise RuntimeError(
            f"{stats['ajoutes']} nouvelles cascades (> {MAX_NOUVELLES}) : "
            "volume à valider par l'utilisateur avant intégration")
    features.sort(key=lambda f: f["properties"]["id"])  # tri stable → diff git lisible
    return features, stats


# ---------------------------------------------------------------------------
# Exécution autonome : fusion dans data/points.geojson
# ---------------------------------------------------------------------------

def _bilan(features, stats):
    total = len(features) or 1
    avec = lambda test: sum(1 for f in features if test(f["properties"]))
    print(f"""
Bilan cascades
  éléments OSM waterfall : {stats['elements_osm']}
  écartés : privés {stats['prives']}, anonymes sans intérêt {stats['anonymes_ecartees']},
            noms illisibles {stats['noms_rejetes']}, hors bornes {stats['hors_bornes']},
            sans coordonnées {stats['sans_coordonnees']}, commune introuvable {stats['sans_commune']}
  doublons internes fusionnés : {stats['doublons_internes']}
  fusionnés dans des points existants : {stats['fusionnes']}
  liens Wikipédia posés : {stats['wiki_lies']} (devinés rejetés car trop loin : {stats['wiki_trop_loin']})
  ids réutilisés : {stats['ids_reutilises']}, conservées sans source : {stats['conservees_sans_source']}
  AJOUTÉS : {stats['ajoutes']}  (total catégorie : {len(features)})
  couverture : hauteur {avec(lambda p: 'hauteur' in p.get('details', {})) * 100 // total} %,
               photo {avec(lambda p: p.get('photos')) * 100 // total} %,
               lien {avec(lambda p: p.get('link')) * 100 // total} %,
               altitude {avec(lambda p: 'altitude' in p.get('details', {})) * 100 // total} %""")


def main(dry_run=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    collection = json.loads(CIBLE_POINTS.read_text(encoding="utf-8"))
    autres = [f for f in collection["features"]
              if f["properties"].get("theme") != "cascade"]
    precedentes = [f for f in collection["features"]
                   if f["properties"].get("theme") == "cascade"]
    print(f"points.geojson : {len(autres)} points existants, "
          f"{len(precedentes)} cascades déjà en base")
    cascades, stats = convertir_cascades(autres, precedentes)
    _bilan(cascades, stats)
    if dry_run:
        print("(--dry-run : rien n'a été écrit)")
        return 0
    collection["features"] = autres + cascades
    CIBLE_POINTS.write_text(
        json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"points.geojson : {len(collection['features'])} features, "
          f"{CIBLE_POINTS.stat().st_size // 1024} Ko")
    return 0


if __name__ == "__main__":
    sys.exit(main(dry_run="--dry-run" in sys.argv))
