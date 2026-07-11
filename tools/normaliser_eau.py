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

d = json.loads(FICHIER.read_text(encoding="utf-8"))
for f in d["features"]:
    p = f["properties"]
    det = p.setdefault("details", {})
    det["type"] = TYPE.get(p.get("type"), "Point d'eau")
    det["potabilite"] = POTABLE.get(p.get("potable"), "Potabilité non garantie")

FICHIER.write_text(
    json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
)
print(f"OK : {len(d['features'])} points normalisés (details.type + details.potabilite)")
