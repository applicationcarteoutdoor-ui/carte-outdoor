# -*- coding: utf-8 -*-
"""
Intègre les AIRES DE REPOS et les BONNES TABLES dans la France (v84).

Aires  : OSM, vraies aires aménagées uniquement, équipements CONSTATÉS par
         voisinage (cf. enrichir_aires_repos.py) — les tags de l'aire
         elle-même sont quasi vides (table 1 %, poubelle 0,2 %).
Tables : DATAtourisme (Licence Ouverte), restaurants portant un label ou une
         distinction publiée par les offices de tourisme. Michelin,
         Gault&Millau et Petit Futé ne sont JAMAIS récoltés directement :
         seules les mentions déjà publiées en Licence Ouverte sont reprises.

CRITÈRE DE QUALITÉ (demande utilisateur « je veux de la qualité ») : une aire
n'est retenue que si elle a un NOM ou au moins un ÉQUIPEMENT constaté. Les
aires sans nom ni équipement n'apprennent rien et sont écartées.

Ids stables `aire-####` / `resto-####`, mise à jour EN PLACE à la relance
(les statuts et le carnet des utilisateurs pointent dessus).

Lancer : python tools/integrer_aires_restaurants.py [--ecrire]
"""

import json
import math
import sys
from pathlib import Path
from urllib.parse import quote

RACINE = Path(__file__).resolve().parent.parent
DOSSIER = Path(__file__).resolve().parent

EQUIP_LBL = {"toilettes": "Toilettes", "table": "Table", "eau": "Eau potable",
             "poubelle": "Poubelle", "jeux": "Jeux enfants", "banc": "Banc",
             "abri": "Abri", "barbecue": "Barbecue"}
ORDRE_EQ = ["toilettes", "table", "eau", "poubelle", "jeux", "banc", "abri", "barbecue"]
FAMILLE_LBL = {"officiel": "Titre d'État", "label": "Label", "guide": "Guide"}
NOM_REPLI = {"Bord de route": "Aire de repos",
             "En ville": "Aire de pique-nique",
             "Nature": "Aire de pique-nique"}
DESC_CADRE = {"Bord de route": "Aire de repos en bord de route",
              "En ville": "Aire de pique-nique en zone habitée",
              "Nature": "Aire de pique-nique en pleine nature"}


def hav_m(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371000.0 * math.asin(math.sqrt(a))


def grille_communes():
    """Centres des 34 969 communes, pour situer une aire en zone habitée."""
    com = json.loads((DOSSIER / "communes.json").read_text(encoding="utf-8"))
    g, pas = {}, 0.02
    for c in com:
        cc = (c.get("centre") or {}).get("coordinates")
        if not cc:
            continue
        lo, la = cc[0], cc[1]
        g.setdefault((math.floor(la / pas), math.floor(lo / pas)), []).append((la, lo))
    return g, pas


def cadre_de(p, g_com, pas):
    """« Bord de route » vient du tag OSM (fiable). « En ville » est déduit de
    la proximité d'un centre de commune : approximatif mais honnête — une aire
    à moins de 500 m d'un centre-bourg est bien en zone habitée."""
    if p.get("veine") in ("rest_area", "services"):
        return "Bord de route"
    la, lo = p["lat"], p["lon"]
    cx, cy = math.floor(la / pas), math.floor(lo / pas)
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for (qa, qo) in g_com.get((cx + dx, cy + dy), ()):
                if hav_m(la, lo, qa, qo) <= 500:
                    return "En ville"
    return "Nature"


def _osm(ref):
    if not ref or len(ref) < 2:
        return ""
    return {"n": "node", "w": "way", "r": "relation"}.get(ref[0], "node") + "/" + ref[1:]


def point_aire(pid, p, cadre):
    t = p.get("tags", {})
    eq = [EQUIP_LBL[e] for e in ORDRE_EQ if e in p.get("equipements", [])]
    d = {"cadre": cadre}
    if eq:
        d["equipements"] = ", ".join(eq)
    acces = (t.get("access") or "").lower()
    if acces in ("private", "no"):
        d["acces"] = "Privé"
    elif acces == "customers":
        d["acces"] = "Réservé aux clients"
    # Dire ce qu'on NE sait pas : sans cette note, une fiche sans équipement
    # laisserait croire qu'il n'y a rien sur place, alors qu'on l'ignore.
    d["note"] = ("Équipements relevés à proximité immédiate ; la liste peut être incomplète."
                 if eq else "Équipements non renseignés pour cette aire.")

    nom = (t.get("name") or "").strip() or NOM_REPLI[cadre]
    liens = [{"label": "🗺️ Source OpenStreetMap (ODbL)",
              "url": "https://www.openstreetmap.org/" + _osm(p.get("osm"))},
             {"label": "🔎 Infos",
              "url": "https://www.google.com/search?q=" + quote(f"{nom} France")}]

    desc = DESC_CADRE[cadre] + (" — " + ", ".join(e.lower() for e in eq) + "." if eq else ".")
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [p["lon"], p["lat"]]},
        "properties": {"id": pid, "name": nom, "theme": "aire-repos",
                       "description": desc, "links": liens, "photos": [], "details": d},
    }


def point_resto(pid, r):
    labels = r.get("labels") or []
    d = {"distinction": ", ".join(labels),
         "famille": FAMILLE_LBL.get(r.get("famille"), "Label")}
    if r.get("adresse"):
        d["adresse"] = r["adresse"]
    commune = (r.get("cp", "") + " " + (r.get("commune") or "")).strip()
    if commune:
        d["commune"] = commune
    if r.get("maj"):
        d["maj"] = r["maj"]

    liens = []
    for c in (r.get("contacts") or "").split("#"):
        c = c.strip()
        if c.startswith("http"):
            liens.append({"label": "🌐 Site", "url": c})
            break
    liens.append({"label": "🔎 Infos", "url": "https://www.google.com/search?q="
                  + quote(f'{r["nom"]} {r.get("commune", "")} restaurant')})

    if len(labels) == 1:
        desc = f"Table distinguée : {labels[0]}."
    else:
        desc = "Table distinguée : " + ", ".join(labels) + "."
    desc += " Source : DATAtourisme (Licence Ouverte)."
    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [r["lon"], r["lat"]]},
        "properties": {"id": pid, "name": r["nom"], "theme": "restaurant",
                       "description": desc, "links": liens, "photos": [], "details": d},
    }


def integrer(ecrire):
    aires = json.loads((DOSSIER / "aires-repos-enrichies.json").read_text(encoding="utf-8"))
    restos = json.loads((DOSSIER / "restaurants-labels-fr.json").read_text(encoding="utf-8"))
    g_com, pas = grille_communes()

    # qualité : un nom OU au moins un équipement constaté
    retenues = [p for p in aires
                if (p.get("tags", {}).get("name") or "").strip() or p.get("equipements")]
    print(f"aires : {len(aires)} → {len(retenues)} retenues "
          f"({len(aires)-len(retenues)} sans nom ni équipement, écartées)")

    chemin = RACINE / "data" / "points.geojson"
    d = json.loads(chemin.read_text(encoding="utf-8"))
    existants = {f["properties"]["id"]: f for f in d["features"]}
    cles = {}
    for f in d["features"]:
        p = f["properties"]
        lon, lat = f["geometry"]["coordinates"]
        cles[f'{p["theme"]}|{p["name"].lower()}|{round(lat,4)}|{round(lon,4)}'] = p["id"]

    from collections import Counter
    stats_cadre = Counter()
    lots = []

    faits = []
    for p in sorted(retenues, key=lambda x: (x["lat"], x["lon"])):
        c = cadre_de(p, g_com, pas)
        stats_cadre[c] += 1
        faits.append((p, c))
    lots.append(("aire-repos", "aire", faits,
                 lambda pid, o: point_aire(pid, o[0], o[1]),
                 lambda o: (o[0].get("tags", {}).get("name") or NOM_REPLI[o[1]], o[0]["lat"], o[0]["lon"])))
    lots.append(("restaurant", "resto", sorted(restos, key=lambda x: (x["nom"], x["lat"])),
                 lambda pid, o: point_resto(pid, o),
                 lambda o: (o["nom"], o["lat"], o["lon"])))

    for theme, abr, objets, fabrique, cle_de in lots:
        suivant = 1 + max([int(i.split("-")[-1]) for i in existants
                           if i.startswith(abr + "-") and i.split("-")[-1].isdigit()] or [0])
        neufs = maj = 0
        for o in objets:
            nom, lat, lon = cle_de(o)
            cle = f'{theme}|{str(nom).lower()}|{round(lat,4)}|{round(lon,4)}'
            pid = cles.get(cle)
            feat = fabrique(pid or f"{abr}-{suivant:04d}", o)
            if pid and pid in existants:
                existants[pid].update(feat)
                maj += 1
            else:
                d["features"].append(feat)
                suivant += 1
                neufs += 1
        print(f"{theme}: +{neufs} nouveaux, {maj} mis à jour")

    print("  cadres :", dict(stats_cadre))
    if ecrire:
        chemin.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")),
                          encoding="utf-8")
        print(f"ÉCRIT data/points.geojson ({chemin.stat().st_size//1024} Ko, "
              f"{len(d['features'])} points)")
    else:
        print("(aperçu — relancer avec --ecrire)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    integrer("--ecrire" in sys.argv)
