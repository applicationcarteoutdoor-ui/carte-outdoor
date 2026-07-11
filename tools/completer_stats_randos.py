"""Complète les fiches Randonnée à partir de leurs tracés (data/randos.geojson) :

- distance : longueur mesurée du tracé, avec détection aller / boucle ;
- dénivelé : s'il manque, estimé par le service altimétrique IGN le long du tracé ;
- durée : si elle manque, estimée (4 km/h à plat + 300 m/h de montée,
  descente comptée à demi-vitesse, arrondi au quart d'heure).

Idempotent et relançable : l'enrichisseur DOIT le relancer après chaque
recolter_traces_randos.py (nouveaux massifs). Les durées éditoriales déjà
présentes ne sont jamais écrasées ; la distance est recalculée à chaque fois.
"""

import json
from pathlib import Path

from enrichissements import denivele_gr, distance_km

DOSSIER = Path(__file__).resolve().parent
POINTS = DOSSIER.parent / "data" / "points.geojson"
RANDOS = DOSSIER.parent / "data" / "randos.geojson"

# En deçà de cette distance entre départ et arrivée du tracé, la randonnée
# est considérée comme une boucle (sinon : un aller, durée comptée aller-retour).
SEUIL_BOUCLE_KM = 0.15


def fmt_km(km):
    return f"{km:.1f}".replace(".", ",")


def fmt_duree(heures):
    quarts = max(1, round(heures * 4))  # jamais « 0 h »
    h, mn = divmod(quarts * 15, 60)
    if h == 0:
        return f"{mn} min"
    return f"{h} h {mn:02d}" if mn else f"{h} h"


def duree_estimee(dist_km, denivele_m, boucle):
    """Règle de marche classique : 4 km/h à plat + 300 m/h en montée ;
    au retour la pente aide (600 m/h) mais la fatigue ralentit (5 km/h)."""
    if boucle:
        return dist_km / 4 + denivele_m / 300
    aller = dist_km / 4 + denivele_m / 300
    retour = dist_km / 5 + denivele_m / 600
    return aller + retour


def main():
    randos = json.loads(RANDOS.read_text(encoding="utf-8"))
    donnees = json.loads(POINTS.read_text(encoding="utf-8"))

    # Tracés groupés par id de point (une rando peut compter plusieurs morceaux)
    traces = {}
    for f in randos.get("features", []):
        rid = f.get("properties", {}).get("rando")
        if rid:
            traces.setdefault(rid, []).append(f["geometry"]["coordinates"])

    stats = {"distance": 0, "denivele_ign": 0, "duree": 0, "sans_trace": []}
    for f in donnees["features"]:
        p = f["properties"]
        if p.get("theme") != "randonnee":
            continue
        morceaux = traces.get(p["id"])
        if not morceaux:
            stats["sans_trace"].append(p["id"])
            continue
        details = p.setdefault("details", {})
        coords = [c for morceau in morceaux for c in morceau]

        dist = sum(distance_km(m) for m in morceaux)
        boucle = _haversine_km(coords[0], coords[-1]) < SEUIL_BOUCLE_KM
        details["distance"] = f"≈ {fmt_km(dist)} km ({'boucle' if boucle else 'aller'})"
        details["distance_n"] = round(dist, 1)
        stats["distance"] += 1

        if "denivele_n" not in details:
            dplus = denivele_gr(f"rando:{p['id']}", coords)
            if dplus is not None:
                details["denivele"] = f"≈ {dplus} m"
                details["denivele_n"] = dplus
                stats["denivele_ign"] += 1

        # Durée estimée : duree_n (heures) posé pour TOUTES les randos — il
        # alimente le filtre par tranches, même quand un libellé éditorial existe.
        h = duree_estimee(dist, details.get("denivele_n", 0), boucle)
        details["duree_n"] = round(h, 1)
        if not details.get("duree"):
            suffixe = "(boucle)" if boucle else "aller-retour"
            details["duree"] = f"≈ {fmt_duree(h)} {suffixe}"
            stats["duree"] += 1

    POINTS.write_text(
        json.dumps(donnees, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"Distances écrites : {stats['distance']}")
    print(f"Dénivelés estimés par l'IGN : {stats['denivele_ign']}")
    print(f"Durées estimées : {stats['duree']}")
    if stats["sans_trace"]:
        print(f"! Sans tracé (à traiter) : {', '.join(stats['sans_trace'])}")


def _haversine_km(a, b):
    from enrichissements import _haversine

    return _haversine(a, b) / 1000


if __name__ == "__main__":
    main()
