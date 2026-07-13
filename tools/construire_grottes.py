# -*- coding: utf-8 -*-
"""
Construit data/grottes.geojson (COUCHE LOURDE, non pré-cachée) à partir de :
  - Grottocenter (tools/grottes-gc.json, ~75 600 entrées, FAITS ODbL :
    coordonnées, nom, profondeur, développement, commune/région) ;
  - les 484 grottes Wikipédia déjà présentes dans data/points.geojson
    (conservées : id grot-XXXX stable, photo, lien) — enrichies en faits.

Retire la catégorie « grotte » de points.geojson (elle devient une couche à la
demande, comme eau/toilettes). Détecte type / progression / présence d'eau à
partir du NOM (fait linguistique), et pose les champs numériques pour les
filtres par bucket. Faits seulement ; descriptions/topos/photos Grottocenter
NON récupérés (protégés) — seul le lien retour.

Ids : les 484 gardent grot-XXXX ; les entrées Grottocenter prennent un id
STABLE dérivé de leur id d'entrée : grot-g{id} (idempotent à la ré-exécution).

Lancer :  python tools/construire_grottes.py [--ecrire]
"""

import json
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request
from collections import defaultdict
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent
POINTS = RACINE / "data" / "points.geojson"
CIBLE = RACINE / "data" / "grottes.geojson"
GC = json.loads((DOSSIER / "grottes-gc.json").read_text(encoding="utf-8"))
CACHE_RG = DOSSIER / "grottes-revgeo.json"   # "lat,lon" → {commune, region} | null (hors France)
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}

R_MERGE = 300   # m : entrée GC ↔ grotte Wikipédia = même cavité

# La bbox « métropole » mord sur l'Italie, l'Espagne, la Suisse, la Belgique…
# On ne garde que les entrées dont la région est française (Grottocenter porte
# le nom de région administrative), les sans-région étant tranchées par
# géocodage inverse. Régions FR (métropole + DOM) + libellé générique.
FR_REGIONS = {n for n in map(lambda s: s.lower(), [
    "Auvergne-Rhône-Alpes", "Bourgogne-Franche-Comté", "Bretagne",
    "Centre-Val de Loire", "Corse", "Grand Est", "Hauts-de-France",
    "Île-de-France", "Normandie", "Nouvelle-Aquitaine", "Occitanie",
    "Pays de la Loire", "Provence-Alpes-Côte d'Azur", "France métropolitaine",
    "Guadeloupe", "Martinique", "Guyane", "La Réunion", "Mayotte",
])}


def _rg_charger():
    return json.loads(CACHE_RG.read_text(encoding="utf-8")) if CACHE_RG.exists() else {}


def revgeo(lat, lon, cache):
    """geo.api.gouv.fr : {commune, region} si en France, None sinon."""
    cle = f"{lat:.4f},{lon:.4f}"
    if cle not in cache:
        try:
            url = ("https://geo.api.gouv.fr/communes?" + urllib.parse.urlencode(
                {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}", "fields": "nom,codeRegion", "format": "json"}))
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30) as r:
                d = json.load(r)
            cache[cle] = {"commune": d[0]["nom"]} if d else None
        except Exception:
            return "ERREUR"
        time.sleep(0.1)
    return cache[cle]


def filtrer_france(gc):
    """Ne garde que les entrées françaises (région FR, ou sans région mais
    géocodées en France). Renseigne la commune des sans-région au passage."""
    cache = _rg_charger()
    sans_region = [e for e in gc if not (e.get("region") or "").strip()]
    a_faire = [e for e in sans_region if f"{e['latitude']:.4f},{e['longitude']:.4f}" not in cache]
    if a_faire:
        print(f"  géocodage inverse de {len(a_faire)} entrées sans région…")
    for i, e in enumerate(a_faire, 1):
        revgeo(e["latitude"], e["longitude"], cache)
        if i % 200 == 0:
            CACHE_RG.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    {i}/{len(a_faire)}")
    CACHE_RG.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
    garde = []
    for e in gc:
        reg = (e.get("region") or "").strip()
        if reg:
            if reg.lower() in FR_REGIONS:
                garde.append(e)
            continue
        rg = cache.get(f"{e['latitude']:.4f},{e['longitude']:.4f}")
        if isinstance(rg, dict):  # en France
            e.setdefault("city", None)
            if not e.get("city"):
                e["city"] = rg.get("commune")
            garde.append(e)
    print(f"  France : {len(garde)} / {len(gc)} entrées (étrangères et hors-France écartées)")
    return garde

AVERTISSEMENT = "⚠️ Cavité possiblement sauvage : prudence, encadrement conseillé."

# --- Détection par le nom (fait linguistique) ---
# Pas de \b final : « grottes », « avens », « sources » (pluriels) doivent
# matcher aussi.
RE_VERTICAL = re.compile(r"\b(avens?|gouffres?|scialets?|igues?|puits|ab[iî]mes?|"
                         r"embuts?|tindouls?|garagais?|cloups?|ragages?|tannes?|"
                         r"diaclases?)", re.I)
RE_GROTTE = re.compile(r"\b(grottes?|baumes?|baumo|balmes?|baoumo|covas?|tunes?|"
                       r"caves?|trous?|failles?|abris?|cluzeaus?|creux|barencs?|"
                       r"porches?)", re.I)
RE_EAU = re.compile(r"\b(sources?|r[ée]surgences?|exsurgences?|[ée]mergences?|"
                    r"pertes?|[ée]vents?|gouls?|fontaines?|boulidous?|foux|"
                    r"gours?|ruisseaux?)", re.I)


def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", " ", t.lower()).strip()


def hav(lat1, lon1, lat2, lon2):
    R = 6371000
    dla, dlo = radians(lat2 - lat1), radians(lon2 - lon1)
    x = sin(dla / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlo / 2) ** 2
    return R * 2 * atan2(sqrt(x), sqrt(1 - x))


def type_progression(nom, depth):
    """(type, progression, eau) déduits du nom + de la profondeur."""
    vertical = bool(RE_VERTICAL.search(nom))
    grotte = bool(RE_GROTTE.search(nom))
    eau = bool(RE_EAU.search(nom))
    if vertical:
        typ, prog = "Gouffre / aven", "Verticale (à cordes)"
    elif grotte:
        typ, prog = "Grotte", "Horizontale"
    elif eau:
        typ, prog = "Source / résurgence", "Non précisé"
    else:
        typ, prog = "Cavité", "Non précisé"
    # profondeur notable sans mot horizontal → probablement vertical
    if prog == "Non précisé" and isinstance(depth, (int, float)) and depth >= 30:
        prog = "Verticale (à cordes)"
    return typ, prog, ("Actif (eau)" if eau else "Non renseigné")


def fmt_m(v):
    return f"{int(round(v))} m"


def fmt_dev(v):
    if v >= 1000:
        km = v / 1000
        return (f"{km:.1f}".replace(".", ",") if km < 10 else f"{int(round(km))}") + " km"
    return f"{int(round(v))} m"


def details_faits(depth, length, typ, prog, eau, commune):
    det = {"type": typ, "progression": prog, "eau": eau}
    if isinstance(depth, (int, float)) and depth > 0:
        det["profondeur"] = fmt_m(depth); det["profondeur_n"] = int(round(depth))
    if isinstance(length, (int, float)) and length > 0:
        det["developpement"] = fmt_dev(length); det["developpement_n"] = int(round(length))
    if commune:
        det["commune"] = commune
    # Référencé = photo (posée ailleurs) OU au moins une donnée technique
    det["fiche"] = "Référencé" if ("profondeur" in det or "developpement" in det) else "À vérifier"
    return det


def main(ecrire=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    coll = json.loads(POINTS.read_text(encoding="utf-8"))
    autres = [f for f in coll["features"] if f["properties"].get("theme") != "grotte"]
    wiki = [f for f in coll["features"] if f["properties"].get("theme") == "grotte"]
    # Idempotence : si points.geojson n'a plus de grottes (déjà déplacées dans
    # grottes.geojson lors d'un run précédent), on récupère les grottes
    # d'origine Wikipédia (id grot-XXXX, pas grot-g…) pour ne pas les perdre.
    if not wiki and CIBLE.exists():
        anc = json.loads(CIBLE.read_text(encoding="utf-8")).get("features", [])
        wiki = [f for f in anc if not f["properties"]["id"].startswith("grot-g")]
        print(f"  (récupéré {len(wiki)} grottes Wikipédia depuis grottes.geojson)")
    print(f"points.geojson : {len(autres)} autres, {len(wiki)} grottes Wikipédia")
    print(f"Grottocenter : {len(GC)} entrées (avant filtre France)")
    gc = filtrer_france(GC)
    # index spatial sur les seules entrées françaises
    GC.clear(); GC.extend(gc)

    # index spatial GC
    grille = defaultdict(list)
    for e in GC:
        grille[(round(e["latitude"], 1), round(e["longitude"], 1))].append(e)

    def gc_proche(lat, lon, nom_norm):
        best = None
        for dla in (-0.1, 0, 0.1):
            for dlo in (-0.1, 0, 0.1):
                for e in grille.get((round(lat + dla, 1), round(lon + dlo, 1)), []):
                    dd = hav(lat, lon, e["latitude"], e["longitude"])
                    if dd > R_MERGE:
                        continue
                    # même cavité si les noms se recoupent OU très proche (<120 m)
                    en = norm(e.get("name"))
                    ok = dd < 120 or (nom_norm and en and (nom_norm in en or en in nom_norm))
                    if ok and (best is None or dd < best[0]):
                        best = (dd, e)
        return best[1] if best else None

    gc_utilises = set()
    features = []

    # 1. Grottes Wikipédia : conservées (id, photo, lien), enrichies en faits
    for f in wiki:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2]
        e = gc_proche(lat, lon, norm(p.get("name")))
        typ, prog, eau = type_progression(norm(p.get("name")), e.get("depth") if e else None)
        commune = None
        depth = length = None
        if e:
            gc_utilises.add(e["id"])
            depth, length = e.get("depth"), e.get("length")
            commune = e.get("city")
        det = details_faits(depth, length, typ, prog, eau, commune)
        if p.get("photos"):
            det["fiche"] = "Référencé"
        # conserve la description Wikipédia existante, ajoute le lien GC secondaire
        p["details"] = det
        if e:
            liens = [l for l in (p.get("links") or []) if l.get("label") != "Grottocenter"]
            liens.append({"label": "Grottocenter", "url": f"https://grottocenter.org/ui/entry/{e['id']}"})
            p["links"] = liens
            p["source"] = "Wikipédia + Grottocenter"
        features.append(f)

    # 2. Entrées Grottocenter non appariées → nouveaux points grot-g{id}
    for e in GC:
        if e["id"] in gc_utilises:
            continue
        lat, lon = e["latitude"], e["longitude"]
        nom = re.sub(r"\s+", " ", (e.get("name") or "").strip()) or "Cavité"
        typ, prog, eau = type_progression(norm(nom), e.get("depth"))
        det = details_faits(e.get("depth"), e.get("length"), typ, prog, eau, e.get("city"))
        lieu = e.get("city") or e.get("region") or ""
        desc = typ + (f" — {lieu}." if lieu else ".") + f" {AVERTISSEMENT}"
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"grot-g{e['id']}",
                "name": nom, "theme": "grotte",
                "description": desc,
                "link": f"https://grottocenter.org/ui/entry/{e['id']}",
                "photos": [], "details": det,
            },
        })

    # bilan
    tot = len(features)
    q = lambda t: sum(1 for f in features if t(f["properties"])) * 100 // tot
    print(f"\ngrottes totales : {tot} (dont {len(wiki)} Wikipédia enrichies, "
          f"{tot - len(wiki)} nouvelles Grottocenter)")
    tc = defaultdict(int)
    for f in features:
        tc[f["properties"]["details"]["type"]] += 1
    print("types :", dict(tc))
    print(f"couverture : profondeur {q(lambda p: 'profondeur' in p['details'])} %, "
          f"développement {q(lambda p: 'developpement' in p['details'])} %, "
          f"eau/actif {q(lambda p: p['details'].get('eau') == 'Actif (eau)')} %, "
          f"photo {q(lambda p: p.get('photos'))} %, "
          f"Référencé {q(lambda p: p['details'].get('fiche') == 'Référencé')} %")

    if ecrire:
        features.sort(key=lambda f: f["properties"]["id"])
        CIBLE.write_text(json.dumps({"type": "FeatureCollection", "features": features},
                                    ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        coll["features"] = autres
        POINTS.write_text(json.dumps(coll, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"\nÉCRIT grottes.geojson ({CIBLE.stat().st_size // 1024} Ko) ; "
              f"points.geojson sans grottes ({len(autres)} features)")
    else:
        print("\n(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    main(ecrire="--ecrire" in sys.argv)
