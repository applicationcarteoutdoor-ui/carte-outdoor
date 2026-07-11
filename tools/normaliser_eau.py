"""Prépare data/eau.geojson pour l'affichage et les filtres de l'app.

Le récolteur pose `type` et `potable` au niveau des propriétés ; les filtres
déclaratifs de l'app (js/filtrage.js) lisent DANS `details`. Ce script recopie
donc, en libellés lisibles, `details.type` et `details.potabilite` (qui servent
À LA FOIS à l'affichage de la fiche et de valeur de filtre, comme le « Tarif »
des toilettes). Idempotent : relançable sans dommage.
"""

import json
from pathlib import Path

FICHIER = Path(__file__).resolve().parent.parent / "data" / "eau.geojson"

TYPE = {
    "fontaine": "Fontaine",
    "source": "Source",
    "robinet": "Robinet",
    "point_d_eau": "Point d'eau",
}
POTABLE = {
    "oui": "Eau potable",
    "non": "Non potable",
    "inconnu": "Potabilité non garantie",
}

# Traductions des valeurs saisonnières brutes d'OSM (celles déjà en français restent)
SAISONS = {
    "yes": "Saisonnier", "summer": "En été", "winter": "En hiver",
    "spring;summer;autumn": "Du printemps à l'automne",
    "spring, summer, fall": "Du printemps à l'automne",
    "may-october": "De mai à octobre", "no": None,  # no = pas saisonnier : retirer
}

d = json.loads(FICHIER.read_text(encoding="utf-8"))
for f in d["features"]:
    p = f["properties"]
    det = p.setdefault("details", {})
    det["type"] = TYPE.get(p.get("type"), "Point d'eau")
    det["potabilite"] = POTABLE.get(p.get("potable"), "Potabilité non garantie")
    # Altitude : nombre nu → « 1050 m » (idempotent : ne rajoute pas de m à un m)
    ele = str(det.get("ele", "")).strip()
    if ele and not ele.endswith("m"):
        det["ele"] = f"{ele} m" if ele.replace(".", "", 1).isdigit() else ele
    # Saisonnalité : traduire les valeurs brutes anglaises connues
    saison = det.get("seasonal")
    if saison in SAISONS:
        if SAISONS[saison] is None:
            det.pop("seasonal", None)
        else:
            det["seasonal"] = SAISONS[saison]

FICHIER.write_text(
    json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)
print(f"OK : {len(d['features'])} points normalisés (details.type + details.potabilite)")
