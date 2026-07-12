# -*- coding: utf-8 -*-
"""
Revue escalade via Camp to Camp : recalage GPS sur coordonnées C2C (précises),
ajout du lien direct C2C, et détection des sites manquants. S'appuie sur
tools/escalade-c2c.json (recolter_escalade_c2c.py).

Rapprochement par NOM (exact, ou notre nom ⊂ nom C2C) dans un rayon du centroïde
de commune. UNIQUE exigé, sinon on n'y touche pas. Les cotations/roche viennent
ensuite du détail C2C (revue_escalade_c2c_detail.py).

  python tools/revue_escalade_c2c.py            # diagnostic
  python tools/revue_escalade_c2c.py --ecrire   # applique recalage + lien
"""

import json
import re
import sys
import unicodedata
from pathlib import Path

import revue_via_ferrata as rvf

DOSSIER = Path(__file__).resolve().parent
C2C = DOSSIER / "escalade-c2c.json"
CIBLE = DOSSIER.parent / "data" / "points.geojson"
RAYON_NOM = 22000       # m : plafond au centroïde de commune
RAYON_MANQUANT = 3000   # m : un site C2C à > 3 km de tout point = candidat manquant
C2C_URL = "https://www.camptocamp.org/waypoints/"


def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def apparier(cible_norm, lon, lat, sites):
    if len(cible_norm) < 4:
        return None, "court"
    proches = [(rvf.dist_m(lon, lat, s["lon"], s["lat"]), s) for s in sites]
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


def main(ecrire=False):
    sites = json.loads(C2C.read_text(encoding="utf-8"))
    for s in sites:
        s["nomNorm"] = norm(s["nom"])
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    esc = [f for f in d["features"] if f["properties"].get("theme") == "escalade"]
    print(f"C2C : {len(sites)} sites | notre base : {len(esc)} points\n")

    RAYON_PROX = 6000  # m : à défaut de nom, le site C2C le plus proche (≤6 km)
    parId = {s["id"]: s for s in sites}
    apparies = set()
    choix = {}  # id de notre point -> (site, methode)

    # Phase 1 : correspondance de NOM (certaine)
    reste = []
    for f in esc:
        lon, lat = f["geometry"]["coordinates"][:2]
        s, typ = apparier(norm(f["properties"]["name"]), lon, lat, sites)
        if s:
            choix[f["properties"]["id"]] = (s, "nom")
            apparies.add(s["id"])
        else:
            reste.append(f)

    # Phase 2 : PROXIMITÉ — site C2C non revendiqué le plus proche, ≤ 6 km
    for f in reste:
        lon, lat = f["geometry"]["coordinates"][:2]
        best = None
        for s in sites:
            if s["id"] in apparies:
                continue
            dd = rvf.dist_m(lon, lat, s["lon"], s["lat"])
            if dd <= RAYON_PROX and (best is None or dd < best[0]):
                best = (dd, s)
        if best:
            choix[f["properties"]["id"]] = (best[1], "proximite")
            apparies.add(best[1]["id"])

    par_nom = sum(1 for _, m in choix.values() if m == "nom")
    par_prox = sum(1 for _, m in choix.values() if m == "proximite")
    recales = liens = 0
    for f in esc:
        c = choix.get(f["properties"]["id"])
        if not c:
            continue
        s = c[0]
        p = f["properties"]
        if ecrire:
            f["geometry"]["coordinates"][0] = s["lon"]
            f["geometry"]["coordinates"][1] = s["lat"]
            p["link"] = C2C_URL + str(s["id"])
            if s.get("ele") and not (p.get("details") or {}).get("altitude"):
                p.setdefault("details", {})["altitude"] = f"{s['ele']} m"
            # La position n'est plus au centre de commune : retirer la mention
            # (elle induirait en erreur) mais garder la ligne « Commune : … ».
            if p.get("description"):
                p["description"] = re.sub(
                    r"\s*\(Position au centre de la commune[^)]*\)", "", p["description"]).strip()
        recales += 1
        liens += 1
    print(f"Appariés par NOM : {par_nom} | par PROXIMITÉ (≤6 km) : {par_prox} | total {recales}")

    # Sites C2C manquants : > 3 km de TOUT point existant (nouveaux lieux)
    manquants = []
    for s in sites:
        if s["id"] in apparies:
            continue
        dmin = min(rvf.dist_m(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1],
                              s["lon"], s["lat"]) for f in esc)
        if dmin > RAYON_MANQUANT:
            manquants.append(s)

    print(f"Appariés (recalés + lien C2C) : {recales}")
    print(f"Sites C2C candidats MANQUANTS (> 3 km de tout point) : {len(manquants)}")
    for s in manquants[:25]:
        print(f"  {s['lat']:.4f},{s['lon']:.4f}  ele={s['ele']}  {s['nom'][:46]}")

    if ecrire:
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"\nÉCRIT : {recales} points recalés + liens C2C directs (ids conservés).")
    else:
        print("\n(SIMULATION — rien écrit.)")
    return manquants


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(ecrire="--ecrire" in sys.argv)
