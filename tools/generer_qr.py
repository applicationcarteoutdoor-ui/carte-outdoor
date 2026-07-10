"""Génère img/qr-site.svg : le QR code de l'URL publique du site.

À relancer uniquement si l'URL change (déménagement du site).
Dépendance : pip install segno (pur Python).
"""

from pathlib import Path

import segno

URL_SITE = "https://applicationcarteoutdoor-ui.github.io/carte-outdoor/"
SORTIE = Path(__file__).resolve().parent.parent / "img" / "qr-site.svg"

qr = segno.make(URL_SITE, error="m")
# omitsize → viewBox seul (le SVG s'adapte à toute taille CSS) ;
# light=None → fond transparent (le cadre blanc est posé par le CSS).
qr.save(
    str(SORTIE),
    kind="svg",
    xmldecl=False,
    svgclass=None,
    lineclass=None,
    dark="#22313c",
    light=None,
    border=2,
    omitsize=True,
)
print(f"OK : {SORTIE} ({SORTIE.stat().st_size} octets) — {qr.designator}")
