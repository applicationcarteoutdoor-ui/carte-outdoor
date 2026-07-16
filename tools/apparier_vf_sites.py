# -*- coding: utf-8 -*-
"""
Apparie chaque via ferrata CH/IT/ES (data/<iso>/points.geojson) à SA fiche
sur le site spécialisé du pays (tools/vf-sites-<iso>.json, récoltés par
recolter_vf_sites.py) — appariement CONSERVATEUR :

  IT / ES (fiches AVEC coordonnées) :
    - fiche à < 5 km AVEC recouvrement de jetons de nom -> apparié (les
      candidates nommées passent TOUJOURS avant la simple proximité) ;
    - sans accord de nom : fiche à < 300 m ET seule dans un rayon de 1 km
      (une falaise à plusieurs ferratas voisines resterait ambiguë) ;
    - sinon rien (jamais deviné).
  CH (myferrata.ch, ~37 fiches SANS coordonnées) :
    - appariement par jetons distinctifs du nom uniquement (≥ 5 caractères) ;
      une fiche qui matche PLUSIEURS via ferrata est écartée (ambiguë).

Sortie : tools/vf-liens-<iso>.json — clé « nom|lat4 » (stable au rebuild) →
{url, k?} ; consommé par construire_pays.py. Rapport imprimé pour relecture.

Lancer :  python tools/apparier_vf_sites.py
"""

import json
import math
import re
import sys
import unicodedata
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
RACINE = DOSSIER.parent

STOPS = {"via", "ferrata", "ferrate", "klettersteig", "sentiero", "attrezzato",
         "attrezzata", "via", "del", "della", "delle", "dello", "dei", "degli",
         "di", "da", "la", "le", "li", "lo", "il", "i", "al", "alla", "alle",
         "ai", "agli", "de", "du", "des", "d", "l", "els", "el", "las", "los",
         "es", "sa", "ses", "y", "e", "ed", "und", "am", "an", "im", "in",
         "auf", "der", "die", "das", "den", "zum", "zur", "monte", "mont",
         "mount", "cima", "pic", "pico", "punta", "sul", "sulla", "per", "a"}


def jetons(nom):
    n = unicodedata.normalize("NFKD", nom.lower())
    n = "".join(c for c in n if not unicodedata.combining(c))
    mots = re.findall(r"[a-z0-9]+", n)
    return {m for m in mots if m not in STOPS and len(m) >= 3}


def hav_km(la1, lo1, la2, lo2):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = math.radians(la2 - la1), math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def vf_du_pays(iso):
    d = json.loads((RACINE / "data" / iso / "points.geojson").read_text(encoding="utf-8"))
    return [{"nom": f["properties"]["name"],
             "lat": f["geometry"]["coordinates"][1],
             "lon": f["geometry"]["coordinates"][0]}
            for f in d["features"] if f["properties"]["theme"] == "via-ferrata"]


def apparier_geo(iso, points, fiches):
    """IT/ES : proximité d'abord, nom en confirmation au-delà de 800 m."""
    liens, pris = {}, {}
    for p in sorted(points, key=lambda x: x["nom"]):
        jp = jetons(p["nom"])
        nommees, proches = [], []
        for f in fiches:
            if "lat" not in f:
                continue
            d = hav_km(p["lat"], p["lon"], f["lat"], f["lon"])
            if d > 5.0:
                continue
            commun = jp & jetons(f["nom"])
            if commun:
                nommees.append((d, len(commun), f))
            elif d < 1.0:
                proches.append((d, 0, f))
        if nommees:
            nommees.sort(key=lambda c: (-c[1], c[0]))
            cands = nommees
        elif len(proches) == 1 and proches[0][0] < 0.3:
            # proximité « aveugle » : une SEULE fiche à moins de 300 m et
            # aucune autre à moins de 1 km — sans quoi c'est ambigu
            cands = proches
        else:
            continue
        d, commun, f = cands[0]
        cle = f"{p['nom']}|{round(p['lat'], 4)}"
        # une même fiche ne sert qu'une fois : garde le point le plus proche
        if f["url"] in pris and pris[f["url"]][0] <= d:
            continue
        if f["url"] in pris:
            del liens[pris[f["url"]][1]]
        pris[f["url"]] = (d, cle)
        liens[cle] = {"url": f["url"], "d_km": round(d, 2), "fiche": f["nom"]}
        if f.get("k"):
            liens[cle]["k"] = f["k"]
    return liens


def apparier_nom(iso, points, fiches):
    """CH : jetons distinctifs seulement (pas de coordonnées côté site)."""
    liens = {}
    for f in fiches:
        jf = {j for j in jetons(f["nom"]) if len(j) >= 5}
        if not jf:
            continue
        touches = [p for p in points if jf & jetons(p["nom"])]
        # ambigu si la fiche matche des VF distantes de plus de 2 km entre elles
        if not touches:
            continue
        eloignees = any(hav_km(touches[0]["lat"], touches[0]["lon"], t["lat"], t["lon"]) > 2
                        for t in touches[1:])
        if eloignees:
            print(f"  ch: fiche ambiguë écartée « {f['nom']} » ({len(touches)} VF)")
            continue
        for p in touches:
            cle = f"{p['nom']}|{round(p['lat'], 4)}"
            liens.setdefault(cle, {"url": f["url"], "fiche": f["nom"]})
    return liens


def main():
    for iso in ("it", "es", "ch"):
        src = DOSSIER / f"vf-sites-{iso}.json"
        if not src.exists():
            print(f"{iso}: vf-sites-{iso}.json absent — lancer recolter_vf_sites.py")
            continue
        fiches = json.loads(src.read_text(encoding="utf-8"))
        points = vf_du_pays(iso)
        liens = (apparier_nom if iso == "ch" else apparier_geo)(iso, points, fiches)
        (DOSSIER / f"vf-liens-{iso}.json").write_text(
            json.dumps(liens, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{iso}: {len(liens)}/{len(points)} via ferrata appariées "
              f"({len(fiches)} fiches) -> vf-liens-{iso}.json")
        for cle, v in sorted(liens.items()):
            d = f" ({v['d_km']} km)" if "d_km" in v else ""
            print(f"   {cle.split('|')[0]}  ->  {v['fiche']}{d}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
