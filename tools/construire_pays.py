# -*- coding: utf-8 -*-
"""
Construit data/<iso>/points.geojson pour la Suisse, l'Italie et l'Espagne à
partir de tools/pays-<iso>-osm.json (OSM, ODbL) et tools/pays-villages.json
(villages labellisés via Wikipédia/Wikidata).

Enrichissements appliqués AU BUILD (v67) — les caches sont rejoués à chaque
reconstruction, les ids restent stables :
  - tools/pays-wiki-<iso>.json   (enrichir_pays_wikipedia.py) : photo 960 px,
    lien d'article, description — clé « nom|lat4 » ;
  - tools/vf-liens-<iso>.json    (apparier_vf_sites.py) : lien vers LA fiche
    du site spécialisé du pays (ferrate365.it / deandar.com / myferrata.ch) ;
  - tools/randos-pays-resolues.json (recolter_randos_pays.py) : randonnées
    iconiques — points `<iso>-rand-####` + tracés data/<iso>/randos.geojson.

Ids STABLES `<iso>-<type>-####` posés par ordre alphabétique à la première
création (statuts/carnet pointent dessus — jamais renumérotés).

Lancer :  python tools/construire_pays.py            (aperçu)
          python tools/construire_pays.py --ecrire   (écrit)
"""

import json
import math
import re
import sys
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
PAYS = {
    "ch": {"nom": "Suisse", "recherche": "Switzerland"},
    "it": {"nom": "Italie", "recherche": "Italy"},
    "es": {"nom": "Espagne", "recherche": "Spain"},
    "pt": {"nom": "Portugal", "recherche": "Portugal"},
    "de": {"nom": "Allemagne", "recherche": "Germany"},
    "nl": {"nom": "Pays-Bas", "recherche": "Netherlands"},
    "lu": {"nom": "Luxembourg", "recherche": "Luxembourg"},
    "be": {"nom": "Belgique", "recherche": "Belgium"},
}
# catégorie OSM -> (theme, abréviation d'id)
THEMES = {
    "refuge": ("refuge", "ref"),
    "camping": ("camping", "camp"),
    "lac": ("lac", "lac"),
    "cascade": ("cascade", "casc"),
    "grotte": ("grotte", "grot"),
    "via-ferrata": ("via-ferrata", "vf"),
    "chateau": ("chateau", "chat"),
    "culture": ("culture", "mus"),
}


def hav(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def entier(v):
    m = re.search(r"\d+", str(v or ""))
    return int(m.group()) if m else None


# Échelle autrichienne (Schall) parfois trouvée dans via_ferrata_scale à la
# place de l'échelle K — équivalence usuelle. « 0 » = valeur vide déguisée.
SCHALL_VERS_K = {"A": "K1", "B": "K2", "C": "K3", "D": "K4", "E": "K5", "F": "K6"}


def normaliser_cotation(c):
    """→ cotation K propre, ou None si inexploitable (« 0 »…)."""
    c = (c or "").strip()
    if not c or c == "0":
        return None
    morceaux = [SCHALL_VERS_K.get(x.strip().upper(), x.strip()) for x in c.split("/")]
    return "/".join(morceaux)


def nettoyer_nom(nom):
    """Retire le point final des noms « en forme de phrase » (« Yvoire en
    Haute-Savoie. ») en ÉPARGNANT les abréviations (« C.A.S. », « inf. »,
    « 1260 m. » : dernier mot court ou à points internes)."""
    n = nom.strip()
    if n.endswith(".") and not n.endswith(".."):
        dernier = n[:-1].split()[-1] if n[:-1].split() else ""
        if "." not in dernier and len(dernier) > 3:
            return n[:-1].rstrip()
    return n


RX_VIGNETTE = re.compile(r"^(https://upload\.wikimedia\.org/wikipedia/[^/]+)/thumb/(.+)/(\d+)px-[^/?#]+$")


def vignette_sure(url):
    """Wikimedia (2025+) n'accepte que des tailles de vignettes normalisées
    (500/960/1280 vérifiées). Les tags OSM `image` charrient des /NNNpx-
    arbitraires → HTTP 400 silencieux : on retombe sur l'ORIGINAL (toujours
    valide). tools/normaliser_vignettes.py fait mieux (API) après coup."""
    m = RX_VIGNETTE.match(url)
    if m and int(m.group(3)) not in (500, 960, 1280):
        return f"{m.group(1)}/{m.group(2)}"
    return url


def details_pour(cat, t):
    """FAITS des tags OSM -> details de fiche (mêmes clés que la France)."""
    d = {}
    alt = entier(t.get("ele"))
    if alt:
        d["altitude"] = f"{alt} m"
        d["altitude_n"] = alt
    if cat == "refuge":
        cap = entier(t.get("capacity"))
        if cap:
            d["capacite"] = f"{cap} places"
            d["places_n"] = cap
    if cat == "cascade" and entier(t.get("height")):
        d["hauteur"] = f"{entier(t.get('height'))} m"
    if cat == "via-ferrata" and t.get("via_ferrata_scale"):
        d["cotation"] = f"K{entier(t['via_ferrata_scale'])}" if entier(t.get("via_ferrata_scale")) \
            else t["via_ferrata_scale"][:12]
    if cat == "chateau":
        d["type"] = "Fort" if (t.get("castle_type") or "") in ("fortress", "defensive", "citadel") else "Château"
        if t.get("ruins") == "yes":
            d["etat"] = "Ruine"
    if cat == "culture" and t.get("opening_hours"):
        d["horaires"] = t["opening_hours"][:200]
    if cat == "grotte":
        d["type"] = "Grotte"
    d["fiche"] = "Référencé" if (t.get("website") or t.get("image")) else "À vérifier"
    return d


def dedoublonner_vf(objets):
    """Les via ferrata OSM sont des tronçons : fusion par nom identique < 1 km."""
    gardes = []
    for o in sorted(objets, key=lambda x: (x["nom"], x["lat"])):
        if any(g["nom"] == o["nom"] and hav(g["lat"], g["lon"], o["lat"], o["lon"]) < 1.0
               for g in gardes):
            continue
        gardes.append(o)
    return gardes


def _charger_json(chemin, defaut):
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.exists() else defaut


VF_LABELS = {"ch": "🧗 Fiche myferrata.ch", "it": "🧗 Fiche Ferrate365",
             "es": "🧗 Fiche deandar.com"}


def construire(iso):
    cfg = PAYS[iso]
    osm = json.loads((RACINE / "tools" / f"pays-{iso}-osm.json").read_text(encoding="utf-8"))
    villages = json.loads((RACINE / "tools" / "pays-villages.json").read_text(encoding="utf-8")).get(iso, [])
    wiki = _charger_json(RACINE / "tools" / f"pays-wiki-{iso}.json", {})
    # géo-recherche v75 (enrichir_geosearch_pays.py) : résultats DÉJÀ contrôlés
    # (anti-homonyme), rejoués au build — clé « nom|lat4 » comme le wiki
    geo = _charger_json(RACINE / "tools" / f"geosearch-{iso}.json", {})
    vf_liens = _charger_json(RACINE / "tools" / f"vf-liens-{iso}.json", {})
    randos = _charger_json(RACINE / "tools" / "randos-pays-resolues.json", {}).get(iso, [])
    feats = []
    traces = []
    stats = {}
    for cat, (theme, abr) in THEMES.items():
        objets = osm.get(cat, [])
        if cat == "via-ferrata":
            objets = dedoublonner_vf(objets)
        objets = sorted(objets, key=lambda o: (o["nom"], o["lat"]))
        for n, o in enumerate(objets, start=1):
            t = o.get("tags", {})
            cle = f"{o['nom']}|{round(o['lat'], 4)}"
            w = wiki.get(cle) or {}
            links = []
            # Via ferrata : LA fiche du site spécialisé du pays en premier
            vfl = vf_liens.get(cle) if cat == "via-ferrata" else None
            if vfl:
                links.append({"label": VF_LABELS[iso], "url": vfl["url"]})
            if (t.get("website") or "").startswith("http"):
                # les tags OSM charrient parfois des espaces parasites
                links.append({"label": "🌐 Site officiel", "url": t["website"].replace(" ", "")[:300]})
            g = geo.get(cle) or {}
            if w.get("wiki"):
                links.append({"label": "🔗 Wikipédia", "url": w["wiki"]})
            elif g.get("url"):
                links.append({"label": "🔗 Wikipédia", "url": g["url"]})
            links.append({"label": "🔎 Infos", "url": "https://www.google.com/search?q=" +
                          quote(f"{o['nom']} {cfg['recherche']}")})
            details = details_pour(cat, t)
            if "cotation" in details:
                c = normaliser_cotation(details["cotation"])
                if c: details["cotation"] = c
                else: details.pop("cotation")
            if vfl and vfl.get("k") and not details.get("cotation"):
                details["cotation"] = vfl["k"]        # cotation K de deandar (fait)
            if (vfl or w.get("wiki") or g.get("url")) and details.get("fiche") == "À vérifier":
                details["fiche"] = "Référencé"
            photos = [t["image"]] if t.get("image") else []
            if not photos and w.get("photo"):
                photos = [w["photo"]]
            if not photos and g.get("photo"):
                photos = [g["photo"]]
            photos = [vignette_sure(u) for u in photos]
            description = (t.get("description") or "")[:300] or w.get("description", "") \
                or g.get("desc", "")
            feats.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [o["lon"], o["lat"]]},
                "properties": {
                    "id": f"{iso}-{abr}-{n:04d}",
                    "name": nettoyer_nom(o["nom"]),
                    "theme": theme,
                    "description": description,
                    "links": links,
                    "photos": photos,
                    "details": details,
                },
            })
        stats[theme] = len(objets)

    # Randonnées iconiques (liste éditoriale tracée sur le réseau OSM par
    # recolter_randos_pays.py) : point + tracé LineString (rando = id du point).
    # Ids STABLES via un registre nom -> id (un ajout futur prolonge la
    # séquence, jamais de renumérotation même si l'ordre alphabétique change).
    reg_path = RACINE / "tools" / "randos-pays-ids.json"
    registre = _charger_json(reg_path, {})
    reg_pays = registre.setdefault(iso, {})
    maxi = max((int(v.rsplit("-", 1)[1]) for v in reg_pays.values()), default=0)
    for r in sorted(randos, key=lambda x: x["rando"]["nom"]):
        e = r["rando"]
        if r["distance_aller_km"] < 0.9:
            # tracé dégénéré (ex. boucle du lac de Braies routée A->B sur
            # 300 m) : le routage départ->objectif ne sait pas faire — honnête.
            # (Les vraies balades courtes depuis une remontée — Stellisee
            # 1,0 km — restent, elles.)
            continue
        if e["nom"] not in reg_pays:
            maxi += 1
            reg_pays[e["nom"]] = f"{iso}-rand-{maxi:04d}"
        rid = reg_pays[e["nom"]]
        boucle = r.get("boucle", False)
        details = {
            "massif": e.get("region", ""),
            "depart": r["depart"]["nom"],
            "distance": f"{r['distance_aller_km']} km ({'boucle' if boucle else 'aller'})",
            "distance_n": r["distance_aller_km"],
            "fiche": "Référencé",
        }
        if e.get("dureeIndicativeH"):
            h = e["dureeIndicativeH"]
            # cohérence durée éditoriale / tracé : vitesse implicite plausible
            # (boucle = distance totale ; sinon aller-retour), sinon durée tue
            vitesse = (1 if boucle else 2) * r["distance_aller_km"] / h
            if 1.2 <= vitesse <= 6.5:
                details["duree"] = f"≈ {h:g} h{'' if boucle else ' aller-retour'}"
                details["duree_n"] = h
        if r.get("denivele_m") is not None:
            details["denivele"] = f"+{r['denivele_m']} m (estimation)"
            details["denivele_n"] = r["denivele_m"]
        liens_rando = [
            {"label": "🥾 Komoot", "url": "https://www.google.com/search?q=" +
             quote(f"{e['nom']} {cfg['recherche']} site:komoot.com")},
            {"label": "🗺️ AllTrails", "url": "https://www.google.com/search?q=" +
             quote(f"{e['nom']} {cfg['recherche']} site:alltrails.com")},
            {"label": "⛰️ Outdooractive", "url": "https://www.google.com/search?q=" +
             quote(f"{e['nom']} {cfg['recherche']} site:outdooractive.com")},
        ]
        feats.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [r["objectif"]["lon"], r["objectif"]["lat"]]},
            "properties": {
                "id": rid,
                "name": e["nom"],
                "theme": "randonnee",
                "description": e.get("description", ""),
                "links": liens_rando,
                "photos": [],
                "details": details,
            },
        })
        # relations OSM = parfois plusieurs tronçons ; le routage = un seul
        for chaine in (r.get("traces") or [r["trace"]]):
            traces.append({
                "type": "Feature",
                "geometry": {"type": "LineString",
                             "coordinates": [[lo, la] for la, lo in chaine]},
                "properties": {"rando": rid, "name": e["nom"]},
            })
    stats["randonnee"] = len(randos)
    if randos:
        reg_path.write_text(json.dumps(registre, ensure_ascii=False, indent=1),
                            encoding="utf-8")

    # Villages labellisés (label officiel du pays, photo + extrait Wikipédia)
    for n, v in enumerate(sorted(villages, key=lambda x: x["nom"]), start=1):
        links = [{"label": "🔗 Wikipédia",
                  "url": f"https://{v['lang']}.wikipedia.org/wiki/" + quote(v["titre"].replace(" ", "_"))},
                 {"label": "🔎 Infos", "url": "https://www.google.com/search?q=" +
                  quote(f"{v['nom']} {cfg['recherche']}")}]
        f = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [v["lon"], v["lat"]]},
            "properties": {
                "id": f"{iso}-vill-{n:04d}",
                "name": v["nom"],
                "theme": "cite-caractere",
                "description": v.get("extrait", ""),
                "links": links,
                "photos": [v["photo"]] if v.get("photo") else [],
                "details": {"label": v["label"], "fiche": "Référencé"},
            },
        }
        feats.append(f)
    stats["cite-caractere"] = len(villages)
    return feats, traces, stats


def main(ecrire):
    for iso, cfg in PAYS.items():
        src = RACINE / "tools" / f"pays-{iso}-osm.json"
        if not src.exists():
            print(f"{iso}: récolte absente — lancer recolter_pays_osm.py {iso.upper()}")
            continue
        feats, traces, stats = construire(iso)
        photos = sum(1 for f in feats if f["properties"]["photos"])
        wikis = sum(1 for f in feats
                    if any("Wikipédia" in l["label"] for l in f["properties"]["links"]))
        fiches_vf = sum(1 for f in feats
                        if any("🧗" in l["label"] for l in f["properties"]["links"]))
        print(f"{iso} ({cfg['nom']}) : {len(feats)} points — " +
              ", ".join(f"{k} {v}" for k, v in stats.items() if v))
        print(f"   photos {photos} | wikipédia {wikis} | fiches VF {fiches_vf} | sites web "
              f"{sum(1 for f in feats if any('Site officiel' in l['label'] for l in f['properties']['links']))}")
        if not ecrire:
            continue
        dossier = RACINE / "data" / iso
        dossier.mkdir(parents=True, exist_ok=True)
        (dossier / "points.geojson").write_text(
            json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
            encoding="utf-8")
        taille = (dossier / "points.geojson").stat().st_size // 1024
        print(f"   ÉCRIT data/{iso}/points.geojson ({taille} Ko)")
        if traces:
            (dossier / "randos.geojson").write_text(
                json.dumps({"type": "FeatureCollection", "features": traces},
                           ensure_ascii=False),
                encoding="utf-8")
            ko = (dossier / "randos.geojson").stat().st_size // 1024
            print(f"   ÉCRIT data/{iso}/randos.geojson ({len(traces)} tracés, {ko} Ko)")
    if not ecrire:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main("--ecrire" in sys.argv)
