# -*- coding: utf-8 -*-
"""
Revue de la catégorie « escalade » : recalage GPS + enrichissement (site web,
photo) + détection des sites manquants, en croisant nos 2033 points (au
centroïde de commune) avec les sites OSM récoltés par recolter_escalade_osm.py.

Clé de rapprochement = le NOM du site (nos crags ont de vrais noms : « Paracol »,
« La Boissière »…) avec un plafond de distance au centroïde de commune (un site
OSM de même nom à l'autre bout de la France n'est pas le nôtre). CONSERVATEUR :
on ne recale que sur correspondance de nom certaine et unique.

  python tools/revue_escalade.py            # diagnostic (n'écrit rien)
  python tools/revue_escalade.py --ecrire   # applique recalage + enrichissement
"""

import hashlib
import json
import re
import sys
import unicodedata
from pathlib import Path

import revue_via_ferrata as rvf  # réutilise dist_m / _haversine

DOSSIER = Path(__file__).resolve().parent
BRUT = DOSSIER / "escalade-osm-brut.json"
CIBLE = DOSSIER.parent / "data" / "points.geojson"

RAYON_CLUSTER = 800     # m : segments/voies d'un même site
RAYON_NOM = 18000       # m : un site OSM de même nom au-delà n'est pas le nôtre
RE_SECTEUR = re.compile(r"secteur|partie|^\W*[a-z0-9]\W*$|^\d+$", re.I)  # sous-parties


def apparier(cible_norm, lon, lat, nommes):
    """Renvoie (site, type) ou (None, raison). Correspondance UNIQUE exigée.
    Rule 1 : nom exact. Rule 2 : notre nom ⊂ nom OSM (>=5 car., distinctif)."""
    if len(cible_norm) < 4:
        return None, "nom trop court"
    proches = [(rvf.dist_m(lon, lat, s["lon"], s["lat"]), s) for s in nommes]
    proches = [(dd, s) for dd, s in proches if dd <= RAYON_NOM]
    exact = [(dd, s) for dd, s in proches if s["nomNorm"] == cible_norm]
    if len(exact) == 1:
        return exact[0][1], "exact"
    if len(exact) > 1:
        return None, "homonymes"
    if len(cible_norm) >= 5:
        sub = [(dd, s) for dd, s in proches if cible_norm in s["nomNorm"]]
        if len(sub) == 1:
            return sub[0][1], "nom~"
        if len(sub) > 1:
            return None, "homonymes"
    return None, "aucun"


def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def commons_url(valeur):
    """URL directe upload.wikimedia.org depuis un tag wikimedia_commons=File:…
    (seul hôte autorisé par la CSP). Renvoie '' si ce n'est pas un fichier."""
    if not valeur or not valeur.lower().startswith("file:"):
        return ""
    nom = valeur.split(":", 1)[1].strip().replace(" ", "_")
    if not nom:
        return ""
    h = hashlib.md5(nom.encode("utf-8")).hexdigest()
    from urllib.parse import quote
    return f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{quote(nom)}"


def _coord(e):
    lat = e.get("lat") or (e.get("center") or {}).get("lat")
    lon = e.get("lon") or (e.get("center") or {}).get("lon")
    return lon, lat


def clusterer():
    els = json.loads(BRUT.read_text(encoding="utf-8"))
    pts = []
    for e in els:
        lon, lat = _coord(e)
        if lon is None:
            continue
        t = e.get("tags") or {}
        pts.append({
            "lon": lon, "lat": lat,
            "nom": (t.get("name") or "").strip(),
            "gmin": t.get("climbing:grade:french:min") or t.get("climbing:grade:french:minimum"),
            "gmax": t.get("climbing:grade:french:max") or t.get("climbing:grade:french:maximum"),
            "length": t.get("climbing:length"),
            "routes": t.get("climbing:routes") or t.get("climbing:sport"),
            "website": (t.get("website") or t.get("contact:website") or t.get("url") or "").strip(),
            "wikidata": (t.get("wikidata") or "").strip(),
            "commons": commons_url(t.get("wikimedia_commons") or t.get("image") or ""),
            "rock": (t.get("rock") or t.get("climbing:rock") or "").strip(),
        })
    clusters = []
    for p in pts:
        best = None
        for c in clusters:
            d = rvf.dist_m(p["lon"], p["lat"], c["lon"], c["lat"])
            if d < RAYON_CLUSTER and (best is None or d < best[1]):
                best = (c, d)
        if best:
            c = best[0]
            c["membres"].append(p)
        else:
            c = {"lon": p["lon"], "lat": p["lat"], "membres": [p]}
            clusters.append(c)
        n = len(c["membres"])
        c["lon"] = sum(m["lon"] for m in c["membres"]) / n
        c["lat"] = sum(m["lat"] for m in c["membres"]) / n
    sites = []
    for c in clusters:
        ms = c["membres"]
        noms = [m["nom"] for m in ms if m["nom"]]
        nom = max(set(noms), key=noms.count) if noms else ""
        prem = lambda k: next((m[k] for m in ms if m.get(k)), "")
        sites.append({
            "lon": round(c["lon"], 6), "lat": round(c["lat"], 6),
            "nom": nom, "nomNorm": norm(nom),
            "website": prem("website"), "wikidata": prem("wikidata"),
            "commons": prem("commons"), "rock": prem("rock"),
            "gmin": prem("gmin"), "gmax": prem("gmax"),
            "n_seg": len(ms),
        })
    return sites


def charger():
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    esc = [f for f in d["features"] if f["properties"].get("theme") == "escalade"]
    return d, esc


def main(ecrire=False):
    sites = clusterer()
    nommes = [s for s in sites if s["nomNorm"]]
    d, esc = charger()
    print(f"OSM : {len(sites)} sites d'escalade (clusters), {len(nommes)} nommés")
    print(f"Notre base : {len(esc)} points\n")

    recales = enrich_web = enrich_photo = 0
    gap_avant = []
    a_verifier = 0
    apparies_osm = set()

    for f in esc:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"][:2]
        s, typ = apparier(norm(p["name"]), lon, lat, nommes)
        if not s:
            if typ == "homonymes":
                a_verifier += 1
            continue
        apparies_osm.add((round(s["lon"], 5), round(s["lat"], 5)))
        gap_avant.append(rvf.dist_m(lon, lat, s["lon"], s["lat"]))
        det = p.setdefault("details", {})
        web_neuf = s["website"] and not p.get("link")
        photo_neuve = s["commons"] and not p.get("photos")
        if ecrire:
            f["geometry"]["coordinates"][0] = s["lon"]
            f["geometry"]["coordinates"][1] = s["lat"]
            if web_neuf:
                p["link"] = s["website"]
            if photo_neuve:
                p["photos"] = [s["commons"]]
        recales += 1
        enrich_web += bool(web_neuf)
        enrich_photo += bool(photo_neuve)

    # Sites OSM candidats MANQUANTS : nommés, jamais appariés, AVEC substance,
    # et PAS un secteur/sous-partie d'un site déjà couvert (à ne pas dupliquer).
    manquants = [s for s in nommes
                 if (round(s["lon"], 5), round(s["lat"], 5)) not in apparies_osm
                 and (s["gmin"] or s["n_seg"] >= 6)
                 and not RE_SECTEUR.search(s["nom"])
                 and min(rvf.dist_m(f["geometry"]["coordinates"][0],
                                    f["geometry"]["coordinates"][1], s["lon"], s["lat"])
                         for f in esc) > 3000]

    import statistics
    print(f"Recalés (nom unique, <25 km) : {recales}")
    if gap_avant:
        print(f"  déplacement médian : {round(statistics.median(gap_avant))} m, "
              f"max {round(max(gap_avant))} m")
    print(f"  dont site web ajouté : {enrich_web} | photo (Commons) ajoutée : {enrich_photo}")
    print(f"Non recalés (pas de correspondance OSM fiable) : {len(esc) - recales}")
    print(f"  dont écartés pour homonymes multiples : {a_verifier}")
    print(f"Sites OSM nommés candidats MANQUANTS : {len(manquants)}")
    for s in sorted(manquants, key=lambda x: -x["n_seg"])[:30]:
        print(f"  {s['lat']:.4f},{s['lon']:.4f}  seg={s['n_seg']:3d}  {s['nom'][:44]}")

    if ecrire:
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"\nÉCRIT : {recales} points recalés/enrichis (ids conservés).")
    else:
        print("\n(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(ecrire="--ecrire" in sys.argv)
