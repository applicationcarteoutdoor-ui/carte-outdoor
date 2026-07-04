# -*- coding: utf-8 -*-
"""
Enrichissements en ligne pour build_data.py (tout est mis en cache dans
tools/ : les exécutions suivantes ne re-téléchargent rien).

  - Refuges : API refuges.info (poêle, cheminée, eau, latrines, remarques…)
  - Châteaux / cités : lien + vignette Wikipédia (API MediaWiki)
  - GR : article Wikipédia du GR, page gr-go.fr correspondante,
         D+ estimé via le service altimétrique IGN (Géoplateforme)
"""

import json
import math
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CACHE_REFUGES = DOSSIER / "refuges-api.json"
CACHE_WIKI = DOSSIER / "wiki-cache.json"
CACHE_ALTI = DOSSIER / "alti-cache.json"
CACHE_TOILETTES = DOSSIER / "toilettes-osm.json"
INDEX_GRGO = DOSSIER / "grgo-index.html"

UA = {"User-Agent": "CarteOutdoor/1.0 (application personnelle de cartographie outdoor)"}
API_WIKI = "https://fr.wikipedia.org/w/api.php"


def http_json(url, corps=None):
    entetes = dict(UA)
    donnees = None
    if corps is not None:
        donnees = json.dumps(corps).encode()
        entetes["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=donnees, headers=entetes)
    # Retente avec temporisation croissante en cas de limitation (429/503)
    for attente in (0, 15, 45, 90, 180):
        if attente:
            print(f"    (limite atteinte, pause {attente} s…)")
            time.sleep(attente)
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 503):
                raise
    raise RuntimeError(f"limitation persistante sur {url[:80]}")


def normaliser(texte):
    texte = unicodedata.normalize("NFD", texte or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texte.lower())


# ---------------------------------------------------------------------------
# Refuges : API refuges.info
# ---------------------------------------------------------------------------

def telecharger_refuges():
    """Toutes les cabanes non gardées de France métropolitaine (API bbox par
    tuiles, dédupliquées par id). Résultat mis en cache."""
    if CACHE_REFUGES.exists():
        return json.loads(CACHE_REFUGES.read_text(encoding="utf-8"))
    print("  téléchargement refuges.info…")
    par_id = {}
    pas = 3.0
    lon = -5.5
    while lon < 10.0:
        lat = 41.0
        while lat < 51.5:
            bbox = f"{lon},{lat},{min(lon + pas, 10.0)},{min(lat + pas, 51.5)}"
            url = (f"https://www.refuges.info/api/bbox?bbox={bbox}"
                   "&type_points=cabane&format=geojson&detail=complet&nb_points=all")
            try:
                d = http_json(url)
                for f in d.get("features", []):
                    par_id[f["properties"]["id"]] = f
            except Exception as e:
                print(f"    ! bbox {bbox} : {e}")
            time.sleep(0.3)
            lat += pas
        lon += pas
    features = list(par_id.values())
    CACHE_REFUGES.write_text(json.dumps(features, ensure_ascii=False), encoding="utf-8")
    print(f"  refuges.info : {len(features)} cabanes")
    return features


# ---------------------------------------------------------------------------
# Wikipédia : liens + vignettes
# ---------------------------------------------------------------------------

def _charger_cache_wiki():
    if CACHE_WIKI.exists():
        return json.loads(CACHE_WIKI.read_text(encoding="utf-8"))
    return {}


def _sauver_cache_wiki(cache):
    CACHE_WIKI.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def _pages_wikipedia(titres):
    """Interroge l'API par lots de 50 : {titreDemandé: {url, thumb} | None}.
    Suit les redirections, ignore les pages d'homonymie."""
    resultats = {}
    for i in range(0, len(titres), 50):
        lot = titres[i:i + 50]
        url = (API_WIKI + "?action=query&format=json&redirects=1"
               "&prop=pageimages|pageprops|info&inprop=url&piprop=thumbnail&pithumbsize=400"
               "&titles=" + urllib.parse.quote("|".join(lot)))
        d = http_json(url)
        # suit la chaîne normalisation → redirection pour retrouver le titre demandé
        corresp = {}
        for n in d["query"].get("normalized", []) + d["query"].get("redirects", []):
            corresp[n["to"]] = n["from"]
        def titre_origine(titre):
            vus = set()
            while titre in corresp and titre not in vus:
                vus.add(titre)
                titre = corresp[titre]
            return titre
        for page in d["query"].get("pages", {}).values():
            origine = titre_origine(page.get("title", ""))
            if "missing" in page or "disambiguation" in page.get("pageprops", {}):
                resultats[origine] = None
            else:
                resultats[origine] = {
                    "url": page.get("fullurl") or
                           "https://fr.wikipedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
                    "thumb": page.get("thumbnail", {}).get("source", ""),
                }
        time.sleep(0.5)
    return resultats


def enrichir_cites(entrees):
    """entrees : [(feature, nomXlsx, nomCommune, nomDept)]. Ajoute link+photo."""
    cache = _charger_cache_wiki()
    a_chercher = []
    for _, nom, commune, dept in entrees:
        for titre in dict.fromkeys([nom, commune, f"{nom} ({dept})"]):
            cle = "t:" + titre
            if cle not in cache:
                a_chercher.append(titre)
    if a_chercher:
        print(f"  Wikipédia cités : {len(a_chercher)} titres à vérifier")
        trouves = _pages_wikipedia(list(dict.fromkeys(a_chercher)))
        for titre, res in trouves.items():
            cache["t:" + titre] = res
        _sauver_cache_wiki(cache)
    ok = 0
    for feature, nom, commune, dept in entrees:
        page = (cache.get("t:" + nom) or cache.get("t:" + f"{nom} ({dept})")
                or cache.get("t:" + commune))
        if page:
            feature["properties"]["link"] = page["url"]
            if page["thumb"]:
                feature["properties"]["photos"] = [page["thumb"]]
            ok += 1
    print(f"  cités avec page Wikipédia : {ok}/{len(entrees)}")


MOTS_CHATEAU = ("chateau", "manoir", "fort", "citadelle", "palais", "abbaye",
                "tour", "bastide", "commanderie", "donjon", "chartreuse")


def _candidats_chateau(texte):
    """Titres Wikipédia candidats construits depuis le texte source.
    Ex. « Adhémar à Montélimar dans la Drôme » →
        « Château des Adhémar », « Château d'Adhémar », « Château Adhémar »…
    (L'endpoint de recherche plein-texte est trop rate-limité et retombe sur
    l'article de la commune : on vérifie plutôt des titres exacts par lots.)"""
    # Nom « utile » : ce qui précède « à Commune » / « dans le Dépt »
    nom = re.split(r"\s(?:à|au|aux|dans|en)\s", texte)[0].strip().rstrip(",")
    nom = re.sub(r"^(le|la|les|l')\s*", "", nom, flags=re.I).strip()
    sans_prefixe = re.sub(
        r"^(château|chateau|manoir|fort|citadelle|palais|abbaye|tour|bastide|commanderie|donjon|chartreuse)\s+(de la|de l'|des|du|de|d')?\s*",
        "", nom, flags=re.I).strip()
    if not sans_prefixe:
        return []
    variantes = []
    if normaliser(nom).startswith(MOTS_CHATEAU):
        variantes.append(nom[0].upper() + nom[1:])  # le texte contient déjà « Château de … »
    premiere = sans_prefixe[0].upper() + sans_prefixe[1:]
    articles = ["de ", "du ", "des ", "de la ", "d'", "de l'", ""]
    variantes += [f"Château {a}{premiere}" for a in articles]
    # dédoublonne en conservant l'ordre
    return list(dict.fromkeys(variantes))


def enrichir_chateaux(entrees):
    """entrees : [(feature, texteOriginal)]. Construit des titres candidats
    « Château de X » et vérifie leur existence par lots (peu de requêtes,
    correspondance exacte : pas de faux positifs de communes)."""
    cache = _charger_cache_wiki()
    tous_candidats = {}  # texte → [titres candidats]
    a_verifier = []
    for _, texte in entrees:
        candidats = _candidats_chateau(texte)
        tous_candidats[texte] = candidats
        for t in candidats:
            if "t:" + t not in cache:
                a_verifier.append(t)
    a_verifier = list(dict.fromkeys(a_verifier))
    if a_verifier:
        print(f"  Wikipédia châteaux : vérification de {len(a_verifier)} titres candidats par lots…")
        # Par tranches de 200, avec sauvegarde du cache à chaque tranche :
        # une interruption (rate-limit persistant…) ne perd pas la progression
        for i in range(0, len(a_verifier), 200):
            tranche = a_verifier[i:i + 200]
            trouves = _pages_wikipedia(tranche)
            for titre, res in trouves.items():
                cache["t:" + titre] = res
            _sauver_cache_wiki(cache)
            print(f"    {min(i + 200, len(a_verifier))}/{len(a_verifier)}")
            time.sleep(1.5)

    candidats = {}  # titre retenu → [features]
    for feature, texte in entrees:
        for titre in tous_candidats[texte]:
            page = cache.get("t:" + titre)
            if page:
                candidats.setdefault(titre, []).append(feature)
                break

    a_verifier = [t for t in candidats if "t:" + t not in cache]
    if a_verifier:
        trouves = _pages_wikipedia(a_verifier)
        for titre, res in trouves.items():
            cache["t:" + titre] = res
        _sauver_cache_wiki(cache)

    ok = 0
    for titre, features in candidats.items():
        page = cache.get("t:" + titre)
        if not page:
            continue
        for feature in features:
            feature["properties"]["link"] = page["url"]
            if page["thumb"]:
                feature["properties"]["photos"] = [page["thumb"]]
            ok += 1
    print(f"  châteaux avec page Wikipédia : {ok}/{len(entrees)}")


def _api_wiki(params):
    url = API_WIKI + "?" + urllib.parse.urlencode({**params, "format": "json"})
    return http_json(url)


def _membres_categorie(titre):
    membres, cont = [], {}
    while True:
        d = _api_wiki({"action": "query", "list": "categorymembers", "cmtitle": titre,
                       "cmlimit": "500", "cmtype": "page|subcat", **cont})
        membres += d["query"].get("categorymembers", [])
        if "continue" not in d:
            return membres
        cont = {"cmcontinue": d["continue"]["cmcontinue"]}
        time.sleep(0.2)


def recolter_categorie_wikipedia(nom_cache, racine, mot_souscat, profondeur_max=4):
    """Articles géolocalisés d'un arbre de catégories Wikipédia (grottes,
    cathédrales…) : [{titre, lat, lon, url, thumb}].

    Les sous-catégories ne sont suivies que si leur nom contient mot_souscat
    (normalisé) — sans quoi le parcours dériverait hors sujet (« Spéléologie
    en France », « Art pariétal »…). Résultat mis en cache dans tools/."""
    cache_path = DOSSIER / nom_cache
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    print(f"  Wikipédia : parcours de « {racine} »…")
    articles = {}  # pageid → titre (dédoublonne les articles multi-catégories)
    vues = set()
    file = [(racine, 0)]
    while file:
        cat, prof = file.pop(0)
        if cat in vues:
            continue
        vues.add(cat)
        for m in _membres_categorie(cat):
            if m["ns"] == 0:
                articles[m["pageid"]] = m["title"]
            elif m["ns"] == 14 and prof < profondeur_max and mot_souscat in normaliser(m["title"]):
                file.append((m["title"], prof + 1))
        time.sleep(0.2)
    print(f"    {len(vues)} catégories parcourues, {len(articles)} articles ; coordonnées…")
    infos = []
    ids = sorted(articles)
    for i in range(0, len(ids), 50):
        # colimit/pilimit max + suivi de "continue" : sans cela l'API ne
        # renvoie les coordonnées que de 10 pages par réponse.
        params = {"action": "query",
                  "pageids": "|".join(str(x) for x in ids[i:i + 50]),
                  "prop": "coordinates|pageimages|info", "inprop": "url",
                  "colimit": "max", "piprop": "thumbnail",
                  "pithumbsize": "400", "pilimit": "50"}
        pages = {}  # pageid → données fusionnées entre les réponses "continue"
        cont = {}
        while True:
            d = _api_wiki({**params, **cont})
            for pid, page in d["query"].get("pages", {}).items():
                fusion = pages.setdefault(pid, {})
                for cle, valeur in page.items():
                    fusion.setdefault(cle, valeur)
            if "continue" not in d:
                break
            cont = {k: v for k, v in d["continue"].items() if k != "continue"}
            time.sleep(0.3)
        for page in pages.values():
            coord = (page.get("coordinates") or [{}])[0]
            infos.append({
                "titre": page.get("title", ""),
                "lat": coord.get("lat"),
                "lon": coord.get("lon"),
                "url": page.get("fullurl", ""),
                "thumb": (page.get("thumbnail") or {}).get("source", ""),
            })
        time.sleep(0.4)
    cache_path.write_text(json.dumps(infos, ensure_ascii=False), encoding="utf-8")
    geo = sum(1 for p in infos if p["lat"] is not None)
    print(f"    {geo}/{len(infos)} articles géolocalisés")
    return infos


def liens_wikipedia_gr(numeros):
    """{num: url} pour les GR dont l'article « Sentier de grande randonnée N » existe."""
    cache = _charger_cache_wiki()
    titres = [f"Sentier de grande randonnée {n}" for n in sorted(set(numeros))]
    a_chercher = [t for t in titres if "t:" + t not in cache]
    if a_chercher:
        trouves = _pages_wikipedia(a_chercher)
        for titre, res in trouves.items():
            cache["t:" + titre] = res
        _sauver_cache_wiki(cache)
    liens = {}
    for n in set(numeros):
        page = cache.get(f"t:Sentier de grande randonnée {n}")
        if page:
            liens[n] = page["url"]
    return liens


# ---------------------------------------------------------------------------
# Toilettes publiques : OpenStreetMap via l'API Overpass
# (le GeoJSON fourni dans Donné/ ne contenait que des restaurants)
# ---------------------------------------------------------------------------

def _overpass(requete):
    donnees = urllib.parse.urlencode({"data": requete}).encode()
    for attente in (0, 20, 60, 120):
        if attente:
            print(f"    (Overpass occupé, pause {attente} s…)")
            time.sleep(attente)
        req = urllib.request.Request("https://overpass-api.de/api/interpreter",
                                     data=donnees, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=240) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 504):
                raise
    raise RuntimeError("Overpass surchargé (429/504 persistant)")


def telecharger_toilettes():
    """Toutes les toilettes publiques (amenity=toilets) de France
    métropolitaine : nœuds + centres des bâtiments, par tuiles de 3°.
    Le cache n'est sauvegardé QUE si toutes les tuiles ont réussi."""
    if CACHE_TOILETTES.exists():
        return json.loads(CACHE_TOILETTES.read_text(encoding="utf-8"))
    print("  téléchargement Overpass (amenity=toilets)…")
    elements, echecs = {}, 0
    pas = 3.0
    lon = -5.5
    while lon < 10.0:
        lat = 41.0
        while lat < 51.5:
            # bbox Overpass : sud, ouest, nord, est
            bbox = f"{lat},{lon},{min(lat + pas, 51.5)},{min(lon + pas, 10.0)}"
            requete = ('[out:json][timeout:180];'
                       f'(node["amenity"="toilets"]({bbox});'
                       f'way["amenity"="toilets"]({bbox}););out center;')
            try:
                d = _overpass(requete)
                for e in d.get("elements", []):
                    elements[f"{e['type']}{e['id']}"] = e
            except Exception as exc:
                echecs += 1
                print(f"    ! bbox {bbox} : {exc}")
            time.sleep(2)
            lat += pas
        lon += pas
    liste = list(elements.values())
    if echecs:
        print(f"  ! {echecs} tuile(s) en échec : cache NON sauvegardé, relancer le script")
    else:
        CACHE_TOILETTES.write_text(json.dumps(liste, ensure_ascii=False), encoding="utf-8")
    print(f"  Overpass : {len(liste)} toilettes")
    return liste


# ---------------------------------------------------------------------------
# gr-go.fr : association GR → page
# ---------------------------------------------------------------------------

def liens_grgo():
    """{numéroGR: url gr-go.fr} d'après l'index sauvegardé dans tools/."""
    if not INDEX_GRGO.exists():
        try:
            req = urllib.request.Request("https://gr-go.fr/grande-randonnee/", headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                INDEX_GRGO.write_bytes(r.read())
        except Exception as e:
            print(f"  ! gr-go.fr inaccessible : {e}")
            return {}
    html = INDEX_GRGO.read_text(encoding="utf-8", errors="replace")
    liens = {}
    for slug in re.findall(r'href="(/grande-randonnee/gr-?(\d+)[^"]*)"', html):
        chemin, num = slug
        liens.setdefault(int(num), "https://gr-go.fr" + chemin)
    print(f"  gr-go.fr : {len(liens)} GR référencés")
    return liens


# ---------------------------------------------------------------------------
# Altimétrie IGN : D+ estimé des GR
# ---------------------------------------------------------------------------

def _haversine(a, b):
    R = 6371000
    rad = math.pi / 180
    dlat = (b[1] - a[1]) * rad
    dlon = (b[0] - a[0]) * rad
    x = math.sin(dlat / 2) ** 2 + math.cos(a[1] * rad) * math.cos(b[1] * rad) * math.sin(dlon / 2) ** 2
    return 2 * R * math.asin(math.sqrt(x))


def distance_km(coords):
    return sum(_haversine(coords[i - 1], coords[i]) for i in range(1, len(coords))) / 1000


def _reechantillonner(coords, espacement=300, maximum=800):
    """Sous-ensemble de points espacés d'~300 m (800 points max)."""
    total = distance_km(coords) * 1000
    if total / espacement > maximum:
        espacement = total / maximum
    pris = [coords[0]]
    acc = 0.0
    for i in range(1, len(coords)):
        acc += _haversine(coords[i - 1], coords[i])
        if acc >= espacement:
            pris.append(coords[i])
            acc = 0.0
    if pris[-1] != coords[-1]:
        pris.append(coords[-1])
    return pris


def _elevations_ign(points):
    """Altitudes IGN pour [(lon, lat)…], par lots de 180."""
    alts = []
    for i in range(0, len(points), 180):
        lot = points[i:i + 180]
        corps = {
            "lon": "|".join(f"{p[0]:.5f}" for p in lot),
            "lat": "|".join(f"{p[1]:.5f}" for p in lot),
            "resource": "ign_rge_alti_wld",
            "zonly": "true",
        }
        d = http_json("https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json", corps)
        alts.extend(d["elevations"])
        time.sleep(0.15)
    return alts


def denivele_gr(nom, coords):
    """D+ estimé (hystérésis 20 m sur un échantillonnage ~300 m), avec cache."""
    cache = json.loads(CACHE_ALTI.read_text(encoding="utf-8")) if CACHE_ALTI.exists() else {}
    cle = f"{nom}|{len(coords)}"
    if cle in cache:
        return cache[cle]
    points = _reechantillonner(coords)
    try:
        alts = _elevations_ign(points)
    except Exception as e:
        print(f"  ! altimétrie {nom} : {e}")
        return None
    dplus = 0.0
    reference = None
    for a in alts:
        if a is None or a < -100:
            continue
        if reference is None:
            reference = a
        elif abs(a - reference) >= 20:
            if a > reference:
                dplus += a - reference
            reference = a
    resultat = int(round(dplus / 50) * 50)  # arrondi à 50 m : c'est une estimation
    cache[cle] = resultat
    CACHE_ALTI.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    return resultat
