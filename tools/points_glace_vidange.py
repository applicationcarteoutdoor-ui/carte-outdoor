# -*- coding: utf-8 -*-
"""
Fabrique des points « cascade de glace » et « aire de vidange » (v81).

Module PARTAGÉ par les trois pipelines (France, pays européens via
construire_pays.py, Nouvelle-Zélande) : la fiche est définie ICI et une
seule fois, sinon les trois se désynchronisent au premier ajustement.

Règle qualité v75 respectée pour les deux catégories :
  - 1 LIEN  : fiche Camp to Camp (glace) / OSM ou site officiel (vidange),
              plus un « 🔎 Infos » de repli systématique ;
  - 1 DESCRIPTION : FACTUELLE, composée des faits (cotation, hauteur,
              orientation, altitude / type d'aire, tarif) — jamais de prose
              recopiée d'une source protégée ;
  - 1 PHOTO : impossible ici et c'est assumé — les photos Camp to Camp sont
              sous CC-BY-SA ET hébergées sur media.camptocamp.org, absent de
              la directive img-src de la CSP (elles seraient bloquées sans
              erreur visible). Les aires de vidange n'ont pas de photo libre.
"""

from urllib.parse import quote

# Camp to Camp cote la glace sur l'échelle WI ; on en dérive un numérique
# pour le filtre en tranches (themes.js → cotation_n).
COTE_GLACE_N = {"1": 1, "2": 2, "2+": 2.5, "3": 3, "3+": 3.5, "4": 4, "4+": 4.5,
                "5": 5, "5+": 5.5, "6": 6, "6+": 6.5, "7": 7, "7+": 7.5}
# orientations Camp to Camp (anglaises) → abréviations françaises
ORIENT_FR = {"N": "N", "NE": "NE", "E": "E", "SE": "SE",
             "S": "S", "SW": "SO", "W": "O", "NW": "NO"}

AVERTISSEMENT_GLACE = ("Conditions très variables : la formation de la glace change "
                       "chaque jour. La présence d'une cascade ici ne signifie pas "
                       "qu'elle est en condition. Vérifiez les conditions récentes et "
                       "le bulletin d'avalanche avant de partir.")


def _infos(nom, pays_recherche):
    return {"label": "🔎 Infos",
            "url": "https://www.google.com/search?q=" + quote(f"{nom} {pays_recherche}")}


def point_cascade_glace(pid, s, pays_recherche):
    """`s` = un site issu de tools/cascade-glace-c2c.json."""
    d = {}
    if s.get("glace"):
        d["cotation"] = "WI " + str(s["glace"])
        n = COTE_GLACE_N.get(str(s["glace"]))
        if n:
            d["cotation_n"] = n
    if s.get("mixte"):
        d["mixte"] = "M" + str(s["mixte"])
    if isinstance(s.get("hauteur"), (int, float)):
        d["hauteur"] = f'{int(s["hauteur"])} m'
        d["hauteur_n"] = int(s["hauteur"])
    if isinstance(s.get("altitude"), (int, float)):
        d["altitude"] = f'{int(s["altitude"])} m'
        d["altitude_n"] = int(s["altitude"])
    orient = [ORIENT_FR.get(o, o) for o in (s.get("orientations") or [])]
    if orient:
        d["orientation"] = ", ".join(orient)
    if (s.get("nb_voies") or 1) > 1:
        d["voies"] = f'{s["nb_voies"]} voies'
    if s.get("engagement"):
        d["engagement"] = str(s["engagement"])
    d["type"] = "Mixte (glace et rocher)" if s.get("mixte") else "Glace pure"
    d["avertissement"] = AVERTISSEMENT_GLACE

    liens = [{"label": "🧊 Fiche Camp to Camp",
              "url": f'https://www.camptocamp.org/routes/{s["id_c2c"]}'},
             _infos(s["nom"], pays_recherche)]

    # description FACTUELLE (les résumés Camp to Camp sont CC-BY-SA : jamais
    # copiés). La cotation se colle au groupe nominal, le reste suit après une
    # virgule — sinon « Cascade de glace 25 m de haut » (sans cotation) boite.
    tete = "Cascade de glace"
    if d.get("cotation"):
        tete += f' cotée {d["cotation"]}'
    suite = []
    if d.get("hauteur"):
        suite.append(f'{d["hauteur"]} de haut')
    if d.get("orientation"):
        suite.append(f'exposée {d["orientation"]}')
    if d.get("altitude"):
        suite.append(f'à {d["altitude"]}')
    desc = tete + (", " + ", ".join(suite) if suite else "") + "."
    if (s.get("nb_voies") or 1) > 1:
        desc += f' {s["nb_voies"]} voies répertoriées.'

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
        "properties": {
            "id": pid,
            "name": s["nom"],
            "theme": "cascade-glace",
            "description": desc,
            "links": liens,
            "photos": [],
            "details": d,
        },
    }


def point_vidange(pid, v, pays_recherche):
    """`v` = une aire issue de tools/vidange-<iso>.json."""
    t = v.get("tags", {})
    dedie = v["type_aire"] == "Aire dédiée"
    d = {"type": v["type_aire"]}

    # ⚠️ Sur un polygone de camping, fee=yes veut dire que LE CAMPING est
    # payant — pas la vidange. Le tarif n'est donc lu que sur les aires dédiées.
    if dedie:
        fee = (t.get("fee") or "").lower()
        if fee in ("no", "free"):
            d["tarif"] = "Gratuit"
        elif fee == "yes":
            d["tarif"] = "Payant"
        acces = (t.get("access") or "").lower()
        if acces in ("yes", "public", "permissive"):
            d["acces"] = "Public"
        elif acces in ("customers", "permit", "private"):
            d["acces"] = "Réservé aux clients"
    else:
        # là, sanitary_dump_station=customers qualifie bien LA VIDANGE
        if (t.get("sanitary_dump_station") or "").lower() == "customers":
            d["acces"] = "Réservé aux clients"
        elif (t.get("sanitary_dump_station") or "").lower() in ("public", "yes"):
            d["acces"] = "Public"

    if (t.get("water_point") or "").lower() == "yes" or \
       (t.get("drinking_water") or "").lower() == "yes":
        d["eau"] = "Oui"
    if t.get("opening_hours"):
        d["horaires"] = t["opening_hours"][:60]
    if t.get("operator"):
        d["gestionnaire"] = t["operator"][:60]

    nom = v.get("nom") or "Aire de vidange"
    liens = []
    site = t.get("website") or t.get("contact:website") or ""
    if site.startswith("http"):
        liens.append({"label": "🌐 Site officiel", "url": site})
    liens.append({"label": "🗺️ Voir sur OpenStreetMap",
                  "url": f'https://www.openstreetmap.org/{_osm_url(v.get("osm"))}'})
    liens.append(_infos(nom, pays_recherche))

    bouts = []
    if d.get("tarif"):
        bouts.append(d["tarif"].lower())
    if d.get("acces"):
        bouts.append(d["acces"].lower())
    if d.get("eau"):
        bouts.append("eau sur place")
    desc = ("Aire de vidange pour fourgons et camping-cars"
            + (" (" + ", ".join(bouts) + ")" if bouts else "")
            + (" — sur une aire de camping." if not dedie else "."))

    return {
        "type": "Feature",
        "geometry": {"type": "Point", "coordinates": [v["lon"], v["lat"]]},
        "properties": {
            "id": pid,
            "name": nom,
            "theme": "vidange",
            "description": desc,
            "links": liens,
            "photos": [],
            "details": d,
        },
    }


def _osm_url(ref):
    """« n123 » → « node/123 » (lien vers l'objet source, attribution ODbL)."""
    if not ref or len(ref) < 2:
        return ""
    return {"n": "node", "w": "way", "r": "relation"}.get(ref[0], "node") + "/" + ref[1:]
