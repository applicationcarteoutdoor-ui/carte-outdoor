# -*- coding: utf-8 -*-
"""
Construit les données Nouvelle-Zélande de la carte :
  data/nz/points.geojson       (huttes, campings, lacs, cascades)
  data/nz/great-walks.geojson  (11 grands itinéraires assemblés)

Sources (faits seulement, licences ouvertes, attribution dans l'app) :
  - DOC (CC-BY 4.0)      : huttes + campings (*_DTO) + segments Great Walk,
                           liens pages officielles depuis les anciens datasets ;
  - NZ Gazetteer (CC-BY) : lacs et cascades aux noms OFFICIELS ;
  - OSM (ODbL)           : cascades nommées et campings en complément
                           (dédoublonnés nom+proximité, règle conservatrice).

Escalade : ABANDONNÉE pour la NZ (106 objets OSM, aucune source libre — les
topos ClimbNZ ne sont pas en licence ouverte). Dit honnêtement, pas de bricolage.

Ids STABLES `nz-<type>-####` posés par ordre alphabétique de nom à la PREMIÈRE
création — comme partout, jamais renumérotés ensuite (statuts/carnet).

Lancer :  python tools/construire_nz.py            (aperçu)
          python tools/construire_nz.py --ecrire   (écrit)
"""

import json
import math
import sys
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
DOC = RACINE / "tools" / "nz-doc.json"
OSM = RACINE / "tools" / "nz-osm.json"
GAZ = RACINE / "tools" / "nz-gazetteer.json"
WIKI = RACINE / "tools" / "nz-wikipedia.json"       # grottes + cathédrales (EN, photos Commons)
VILLAGES = RACINE / "tools" / "nz-villages.json"    # sélection éditoriale vérifiée (API Wikipédia)
CHAT_WIKI = RACINE / "tools" / "nz-chateaux-wiki.json"
DOSSIER_NZ = RACINE / "data" / "nz"
POINTS = DOSSIER_NZ / "points.geojson"
WALKS = DOSSIER_NZ / "great-walks.geojson"

# Châteaux et forts de NZ — liste éditoriale COMPLÈTE (le pays n'a qu'une
# poignée de vrais châteaux ; les 75 « homesteads » OSM ont été écartés).
# Positions OSM, recoupées Wikipédia (nz-chateaux-wiki.json) quand l'article
# a des coordonnées. `wiki` = titre en.wikipedia (lien + photo).
CHATEAUX_NZ = [
    ("Larnach Castle", -45.861855, 170.627323, "Château", "Larnach Castle",
     "Le « seul château de Nouvelle-Zélande » (1871), péninsule d'Otago — visitable"),
    ("Cargill's Castle", -45.917885, 170.480497, "Château", "Cargill's Castle",
     "Ruine néo-gothique de 1877 sur les falaises de Dunedin"),
    ("Riverstone Castle", -44.953609, 171.081785, "Château", "",
     "Château moderne (2017) près d'Oamaru — visites guidées"),
    ("Fort Jervois (Ripapa Island)", -43.619837, 172.754459, "Fort", "Ripapa Island",
     "Île fortifiée de 1886 (« Russian scare »), port de Lyttelton"),
    ("Fort Ballance", -41.294703, 174.834506, "Fort", "Fort Ballance",
     "Batterie côtière de 1885, presqu'île de Miramar (Wellington)"),
    ("Fort Dorset", -41.328988, 174.836095, "Fort", "",
     "Défense côtière de l'entrée du port de Wellington (1909)"),
    ("Wright's Hill Fortress", -41.295868, 174.738776, "Fort", "",
     "Fortification anti-invasion de 1942, canons de 9,2 pouces — visitable"),
]

# Via ferrata de NZ — liste éditoriale (3 parcours connus, vérifiés : opérateurs
# réels ; positions = site du parcours, Twin Falls via le Gazetteer pour Wildwire).
VIA_FERRATA_NZ = [
    ("Wildwire Wanaka — Lord of the Rungs", -44.64843, 168.927135,
     "https://wildwire.co.nz",
     "La via ferrata de cascade la plus haute du monde (Twin Falls, 450 m) — 3 niveaux, sortie guidée"),
    ("Via Ferrata Queenstown", -45.030914, 168.660824,
     "https://viaferrata.co.nz",
     "Parcours sur les falaises au-dessus du centre de Queenstown — accueil 39 Camp Street"),
    ("Via Ferrata Aotearoa (Golden Bay)", -41.033175, 172.862254,
     "https://viaferrata.org.nz",
     "Via ferrata associative de Golden Bay (Takaka) — accès encadré par le club"),
]

# Great Walks : préfixe FlocID → itinéraire. LHAUROBC = section côtière Port
# Craig du Hump Ridge Track (vérifié par les noms de segments). Écartés
# (conservateur, comme le recalage GPS) : MILFRDRJ (embranchement Key Summit),
# WHAKAPVW (Tama Lakes, aller-retour annexe), WHANGANJ (Whanganui Journey =
# descente de RIVIÈRE en canoë : son unique tronçon terrestre serait trompeur).
GREAT_WALKS = {
    "ABTASCOT": ("Abel Tasman Coast Track", "Abel_Tasman_Coast_Track"),
    "HEAPHYTK": ("Heaphy Track", "Heaphy_Track"),
    "HUMPRIDG": ("Hump Ridge Track", "Hump_Ridge_Track"),
    "LHAUROBC": ("Hump Ridge Track", "Hump_Ridge_Track"),
    "KEPLERTK": ("Kepler Track", "Kepler_Track"),
    "MILFRDTK": ("Milford Track", "Milford_Track"),
    "PAPROAGW": ("Paparoa Track", "Paparoa_Track"),
    "RAKIURAT": ("Rakiura Track", "Rakiura_Track"),
    "ROUTEBRN": ("Routeburn Track", "Routeburn_Track"),
    "TONGARNC": ("Tongariro Northern Circuit", "Tongariro_Northern_Circuit"),
    "TONGARAC": ("Tongariro Alpine Crossing", "Tongariro_Alpine_Crossing"),
    "WAIKARTK": ("Lake Waikaremoana Great Walk", "Lake_Waikaremoana_Great_Walk"),
}

CAT_HUT = {  # catégories DOC → libellés de fiche
    "Great Walk": "Great Walk",
    "Serviced": "Aménagée (gaz, matelas)",
    "Serviced alpine": "Alpine aménagée",
    "Standard": "Standard",
    "Basic/bivvies": "Basique / bivouac",
}
CAT_CAMP = {  # catégories DOC → valeurs du filtre Type (themes.js : EXACTES)
    "Serviced": "Aménagé",
    "Standard": "Standard",
    "Basic": "Basique",
    "Backcountry": "Arrière-pays",
    "Great Walk": "Great Walk",
}


def hav(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def lien_doc(nom, meta, seuil_km=1.0):
    """Page DOC officielle : rapprochement nom exact (insensible casse) + proximité."""
    cible = nom.lower()
    for m in meta:
        if m["nom"].lower() == cible:
            return m
    return None


def point(pid, nom, theme, lat, lon, details, links):
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [lon, lat]},
        "properties": {"id": pid, "name": nom, "theme": theme,
                       "description": "", "links": links, "photos": [], "details": details},
    }


def recherche(nom, contexte):
    q = quote(f"{nom} {contexte} New Zealand")
    return {"label": "🔎 Infos & topo", "url": f"https://www.google.com/search?q={q}"}


import re

RE_GOUFFRE = re.compile(r"\b(tomos?|shafts?|pot|pots|holes?|abyss|chasms?|sinkholes?)\b", re.I)
RE_SOURCE = re.compile(r"\b(springs?|resurgences?)\b", re.I)


def type_cavite(nom):
    """Type spéléo depuis le nom anglais — mêmes libellés que le filtre grotte."""
    if RE_GOUFFRE.search(nom):
        return "Gouffre / aven"
    if RE_SOURCE.search(nom):
        return "Source / résurgence"
    if re.search(r"\b(caves?|grotto|caverns?)\b", nom, re.I):
        return "Grotte"
    return "Cavité"


def construire():
    doc = json.loads(DOC.read_text(encoding="utf-8"))
    osm = json.loads(OSM.read_text(encoding="utf-8"))
    gaz = json.loads(GAZ.read_text(encoding="utf-8"))
    wiki = json.loads(WIKI.read_text(encoding="utf-8"))
    villages = json.loads(VILLAGES.read_text(encoding="utf-8"))
    chat_wiki = json.loads(CHAT_WIKI.read_text(encoding="utf-8"))
    feats = []

    # ---- Huttes (DOC DTO, enrichies parc/région/lien de l'ancien dataset) ----
    metas = doc.get("huts_meta", [])
    par_nom_meta = {}
    for m in metas:
        par_nom_meta.setdefault(m["nom"].lower(), []).append(m)
    huts = sorted(doc["huts"], key=lambda h: (h["nom"], h["lat"]))
    for n, h in enumerate(huts, start=1):
        d = {}
        cat = CAT_HUT.get(h["categorie"], h["categorie"])
        if cat:
            d["categorie"] = cat
        if h["couchettes"]:
            d["capacite"] = f"{h['couchettes']} couchettes"
            d["places_n"] = h["couchettes"]
        if h["equipements"]:
            d["equipements"] = h["equipements"]
        if h["statut"] == "CLSD":
            d["etat"] = "Fermée"
        # enrichissement méta (nom exact + < 1 km — conservateur)
        links = []
        candidats = par_nom_meta.get(h["nom"].lower(), [])
        proches = [m for m in candidats if hav(h["lat"], h["lon"], m["lat"], m["lon"]) <= 1.0]
        if proches:
            m = proches[0]
            if m["lieu"]:
                d["lieu"] = m["lieu"]
            if m["region"]:
                d["region"] = m["region"]
            if m["lien"]:
                links.append({"label": "🔗 Page officielle DOC", "url": m["lien"]})
        links.append(recherche(h["nom"], "hut"))
        feats.append(point(f"nz-hut-{n:04d}", h["nom"], "refuge", h["lat"], h["lon"], d, links))
    nb_huts = len(huts)

    # ---- Campings (DOC DTO socle + OSM complément dédoublonné) ----
    metas_c = doc.get("camps_meta", [])
    par_nom_meta_c = {}
    for m in metas_c:
        par_nom_meta_c.setdefault(m["nom"].lower(), []).append(m)
    camps = sorted(doc["campsites"], key=lambda c: (c["nom"], c["lat"]))
    positions_doc = []
    num_camp = 0
    for c in camps:
        num_camp += 1
        p = c.get("pivot", {})
        d = {"type": CAT_CAMP.get(c["categorie"], c["categorie"] or "")}
        n_places = 0
        for cle in ("WEB_NUM_SITES_NON_POWER", "WEB_NUM_SITES_POWER"):
            try:
                n_places += int(p.get(cle) or 0)
            except ValueError:
                pass
        if n_places:
            d["places"] = f"{n_places} emplacements"
            d["places_n"] = n_places
        if p.get("WEB_ACCESS_CAMP"):
            d["acces"] = p["WEB_ACCESS_CAMP"]
        if p.get("WEB_DOGS_ALLOWED"):
            d["chiens"] = p["WEB_DOGS_ALLOWED"]
        if p.get("WEB_LANDSCAPE"):
            d["paysage"] = p["WEB_LANDSCAPE"]
        if c["statut"] == "CLSD":
            d["etat"] = "Fermé"
        links = []
        candidats = par_nom_meta_c.get(c["nom"].lower(), [])
        proches = [m for m in candidats if hav(c["lat"], c["lon"], m["lat"], m["lon"]) <= 1.0]
        if proches:
            m = proches[0]
            if m["lieu"]:
                d["lieu"] = m["lieu"]
            if m["region"]:
                d["region"] = m["region"]
            if m["lien"]:
                links.append({"label": "🔗 Page officielle DOC", "url": m["lien"]})
        links.append(recherche(c["nom"], "campsite"))
        feats.append(point(f"nz-camp-{num_camp:04d}", c["nom"], "camping", c["lat"], c["lon"], d, links))
        positions_doc.append((c["lat"], c["lon"], c["nom"].lower()))

    # complément OSM : campings NOMMÉS à > 500 m de tout camping DOC
    osm_camps = sorted([o for o in osm.get("campings", []) if o["nom"]],
                       key=lambda o: (o["nom"], o["lat"]))
    ajoutes_osm = 0
    for o in osm_camps:
        if any(hav(o["lat"], o["lon"], la, lo) <= 0.5 for la, lo, _ in positions_doc):
            continue  # déjà couvert par le DOC
        num_camp += 1
        ajoutes_osm += 1
        d = {}
        t = o.get("tags", {})
        if t.get("fee") in ("no", "non"):
            d["tarif"] = "Gratuit"
        links = []
        if t.get("website", "").startswith("http"):
            links.append({"label": "🌐 Site du camping", "url": t["website"]})
        links.append(recherche(o["nom"], "campsite"))
        feats.append(point(f"nz-camp-{num_camp:04d}", o["nom"], "camping", o["lat"], o["lon"], d, links))

    # ---- Lacs (Gazetteer officiel) ----
    lacs = sorted(gaz["lacs"], key=lambda l: (l["nom"], l["lat"]))
    for n, l in enumerate(lacs, start=1):
        d = {"fiche": "Référencé" if l["statut"].startswith("Official") else "À vérifier"}
        feats.append(point(f"nz-lac-{n:04d}", l["nom"], "lac", l["lat"], l["lon"], d,
                           [recherche(l["nom"], "lake")]))

    # ---- Cascades (Gazetteer officiel + OSM nommées, dédoublonnées) ----
    cascades = [dict(c, source="gaz") for c in gaz["cascades"]]
    pos_gaz = [(c["lat"], c["lon"]) for c in cascades]
    osm_casc = [o for o in osm.get("cascades", []) if o["nom"]]
    for o in osm_casc:
        if any(hav(o["lat"], o["lon"], la, lo) <= 0.5 for la, lo in pos_gaz):
            continue
        cascades.append({"nom": o["nom"], "lat": o["lat"], "lon": o["lon"],
                         "statut": "", "source": "osm", "tags": o.get("tags", {})})
    cascades.sort(key=lambda c: (c["nom"], c["lat"]))
    for n, c in enumerate(cascades, start=1):
        d = {"fiche": "Référencé" if c.get("statut", "").startswith("Official") else "À vérifier"}
        h = (c.get("tags") or {}).get("height")
        if h:
            d["hauteur"] = f"{h} m"
        feats.append(point(f"nz-casc-{n:04d}", c["nom"], "cascade", c["lat"], c["lon"], d,
                           [recherche(c["nom"], "waterfall")]))
    nb_casc_osm = sum(1 for c in cascades if c.get("source") == "osm")

    # ---- Grottes (Gazetteer officiel + OSM nommées, enrichies Wikipédia) ----
    grottes = [dict(g, source="gaz") for g in gaz.get("grottes", [])]
    pos_g = [(g["lat"], g["lon"]) for g in grottes]
    osm_grottes_nommees = [o for o in osm.get("grottes", []) if o["nom"]]
    for o in osm_grottes_nommees:
        if any(hav(o["lat"], o["lon"], la, lo) <= 0.3 for la, lo in pos_g):
            continue
        grottes.append({"nom": o["nom"], "lat": o["lat"], "lon": o["lon"],
                        "statut": "", "source": "osm", "tags": o.get("tags", {})})
    # enrichissement Wikipédia (articles géolocalisés : lien + photo) par proximité
    wiki_grottes = list(wiki.get("grottes", []))
    grottes.sort(key=lambda g: (g["nom"], g["lat"]))
    nb_wiki_grot = 0
    for n, g in enumerate(grottes, start=1):
        d = {"type": type_cavite(g["nom"])}
        t = g.get("tags") or {}
        if t.get("depth"):
            d["profondeur"] = f"{t['depth']} m"
        if t.get("length"):
            d["developpement"] = f"{t['length']} m"
        links = [recherche(g["nom"], "cave")]
        photos = []
        # article wiki à moins de 1 km dont le titre partage un mot significatif
        mots = {m for m in re.split(r"[^a-zà-ÿ]+", g["nom"].lower()) if len(m) >= 4 and m != "cave"}
        for w in wiki_grottes:
            if hav(g["lat"], g["lon"], w["lat"], w["lon"]) <= 1.0 and \
               (mots & {m for m in re.split(r"[^a-zà-ÿ]+", w["titre"].lower()) if len(m) >= 4}):
                links.insert(0, {"label": "🔗 Wikipédia", "url": w["url"]})
                if w.get("photo"):
                    photos.append(w["photo"])
                nb_wiki_grot += 1
                break
        d["fiche"] = "Référencé" if (photos or g.get("statut", "").startswith("Official")) else "À vérifier"
        f = point(f"nz-grot-{n:04d}", g["nom"], "grotte", g["lat"], g["lon"], d, links)
        f["properties"]["photos"] = photos
        feats.append(f)
    nb_grottes = len(grottes)

    # ---- Cathédrales (Wikipédia EN : coordonnées + photos Commons) ----
    caths = sorted(wiki.get("cathedrales", []), key=lambda c: (c["titre"], c["lat"]))
    for n, c in enumerate(caths, start=1):
        d = {"fiche": "Référencé"}
        links = [{"label": "🔗 Wikipédia", "url": c["url"]}]
        f = point(f"nz-cath-{n:04d}", c["titre"], "cathedrale", c["lat"], c["lon"], d, links)
        if c.get("photo"):
            f["properties"]["photos"] = [c["photo"]]
        feats.append(f)

    # ---- Châteaux et forts (liste éditoriale complète, cf. CHATEAUX_NZ) ----
    for n, (nom, lat, lon, typ, wtitre, fait) in enumerate(
            sorted(CHATEAUX_NZ, key=lambda c: c[0]), start=1):
        d = {"type": typ, "fiche": "Référencé" if wtitre else "À vérifier"}
        links = []
        w = chat_wiki.get(wtitre) if wtitre else None
        if wtitre:
            links.append({"label": "🔗 Wikipédia",
                          "url": "https://en.wikipedia.org/wiki/" + quote(wtitre.replace(" ", "_"))})
        links.append(recherche(nom, "castle"))
        f = point(f"nz-chat-{n:04d}", nom, "chateau", lat, lon, d, links)
        f["properties"]["description"] = fait
        if w and w.get("photo"):
            f["properties"]["photos"] = [w["photo"]]
        feats.append(f)

    # ---- Villages de caractère (sélection éditoriale vérifiée Wikipédia) ----
    vills = sorted(villages["items"], key=lambda v: v["nom"])
    for n, v in enumerate(vills, start=1):
        d = {"label": "Village de caractère", "region": v.get("lieu", ""), "fiche": "Référencé"}
        links = []
        if v.get("wikipedia_en"):
            links.append({"label": "🔗 Wikipédia",
                          "url": "https://en.wikipedia.org/wiki/" + quote(v["wikipedia_en"].replace(" ", "_"))})
        links.append(recherche(v["nom"], "village"))
        f = point(f"nz-vill-{n:04d}", v["nom"], "cite-caractere", v["lat"], v["lon"], d, links)
        f["properties"]["description"] = v.get("fait_marquant", "")
        if (v.get("photo") or "").startswith("https://upload.wikimedia.org"):
            f["properties"]["photos"] = [v["photo"]]
        feats.append(f)

    # ---- Via ferrata (liste éditoriale, 3 parcours) ----
    for n, (nom, lat, lon, site, fait) in enumerate(VIA_FERRATA_NZ, start=1):
        d = {"fiche": "Référencé"}
        links = [{"label": "🌐 Site officiel", "url": site}, recherche(nom, "via ferrata")]
        f = point(f"nz-vf-{n:04d}", nom, "via-ferrata", lat, lon, d, links)
        f["properties"]["description"] = fait
        feats.append(f)

    # ---- Randonnées emblématiques (liste éditoriale, tracés DOC réels) ----
    #      Produites par recolter_nz_randos.py (tools/nz-randos.json +
    #      data/nz/randos.geojson). Point = départ du tracé (côté accès).
    randos = json.loads((RACINE / "tools" / "nz-randos.json").read_text(encoding="utf-8"))
    for r in randos:
        d = {
            "massif": r["region"],
            "distance": r["distance"], "distance_n": r["distance_n"],
            "duree": r["duree"], "duree_n": r["duree_n"],
            "fiche": "Référencé",
        }
        f = point(r["id"], r["nom"], "randonnee", r["lat"], r["lon"], d, [
            {"label": "🥾 Fiche DOC", "url": "https://www.google.com/search?q=" +
             quote(f"{r['nom']} site:doc.govt.nz")},
            {"label": "🗺️ AllTrails", "url": "https://www.google.com/search?q=" +
             quote(f"{r['nom']} New Zealand site:alltrails.com")},
        ])
        f["properties"]["description"] = r["note"]
        feats.append(f)

    # ---- Great Walks (segments EAM regroupés par itinéraire) ----
    walks = {}
    ecartes = []
    for s in doc["greatwalk_segments"]:
        pref = s["floc"].split("-")[0]
        if pref not in GREAT_WALKS:
            ecartes.append(s["floc"])
            continue
        nom, wiki = GREAT_WALKS[pref]
        w = walks.setdefault(nom, {"wiki": wiki, "segments": []})
        w["segments"].extend(s["paths"])
    wfeats = []
    for nom in sorted(walks):
        w = walks[nom]
        km = sum(hav(a[1], a[0], b[1], b[0])
                 for seg in w["segments"] for a, b in zip(seg, seg[1:]))
        wfeats.append({
            "type": "Feature",
            "geometry": {"type": "MultiLineString", "coordinates": w["segments"]},
            "properties": {
                "name": nom,
                "distance_km": round(km, 1),
                "wiki": f"https://en.wikipedia.org/wiki/{w['wiki']}",
                "link": "https://www.doc.govt.nz/parks-and-recreation/things-to-do/walking-and-tramping/great-walks/",
            },
        })
    return feats, wfeats, {"huts": nb_huts, "camps_doc": len(camps), "camps_osm": ajoutes_osm,
                           "lacs": len(lacs), "cascades": len(cascades), "casc_osm": nb_casc_osm,
                           "grottes": nb_grottes, "grottes_wiki": nb_wiki_grot,
                           "cathedrales": len(caths), "chateaux": len(CHATEAUX_NZ),
                           "villages": len(vills), "vf": len(VIA_FERRATA_NZ),
                           "walks": len(wfeats), "segments_ecartes": ecartes}


def main(ecrire):
    feats, wfeats, stats = construire()
    print(f"Points NZ : {len(feats)}")
    print(f"  huttes {stats['huts']} | campings DOC {stats['camps_doc']} + OSM {stats['camps_osm']}"
          f" | lacs {stats['lacs']} | cascades {stats['cascades']} (dont OSM {stats['casc_osm']})")
    print(f"  grottes {stats['grottes']} (wiki {stats['grottes_wiki']}) | cathédrales {stats['cathedrales']}"
          f" | châteaux/forts {stats['chateaux']} | villages {stats['villages']} | via ferrata {stats['vf']}")
    print(f"Great Walks : {stats['walks']} itinéraires "
          f"(segments écartés : {stats['segments_ecartes']})")
    for w in wfeats:
        print(f"  - {w['properties']['name']}: {w['properties']['distance_km']} km")
    exemples = [f for f in feats if f["properties"]["theme"] == "refuge"][:1] + \
               [f for f in feats if f["properties"]["theme"] == "camping"][:1]
    for ex in exemples:
        p = ex["properties"]
        print(f"\nex {p['id']} {p['name']!r}: {json.dumps(p['details'], ensure_ascii=False)[:220]}")
    if not ecrire:
        print("\n(aperçu — relancer avec --ecrire)")
        return
    DOSSIER_NZ.mkdir(parents=True, exist_ok=True)
    POINTS.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                 ensure_ascii=False), encoding="utf-8")
    WALKS.write_text(json.dumps({"type": "FeatureCollection", "features": wfeats},
                                ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT {POINTS} ({len(feats)} features, "
          f"{POINTS.stat().st_size // 1024} Ko) + {WALKS.name} ({len(wfeats)})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main("--ecrire" in sys.argv)
