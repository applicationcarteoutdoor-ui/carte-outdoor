# -*- coding: utf-8 -*-
"""
Génère icons/icon-192.png et icons/icon-512.png (logo SpotMap : épingle + « ? »)
— même dessin que icons/icon.svg, rendu avec Pillow (pas de moteur SVG requis).
Le contenu reste dans la zone sûre centrale (icônes « maskable » du manifest).

Lancer :  python tools/generer_icones.py
"""

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

RACINE = Path(__file__).resolve().parent.parent
ICONS = RACINE / "icons"
VERT = (45, 106, 79)    # #2d6a4f
TEAL = (10, 147, 150)   # #0a9396


def police(taille):
    for nom in ("arialbd.ttf", "seguisb.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(f"C:/Windows/Fonts/{nom}", taille)
        except OSError:
            continue
    return ImageFont.load_default()


def dessiner(cote):
    # supersampling ×4 pour des bords nets
    S = cote * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # fond arrondi en dégradé diagonal vert → teal
    fond = Image.new("RGBA", (S, S))
    fd = ImageDraw.Draw(fond)
    for y in range(S):
        t = y / S
        r = int(VERT[0] + (TEAL[0] - VERT[0]) * t)
        g = int(VERT[1] + (TEAL[1] - VERT[1]) * t)
        b = int(VERT[2] + (TEAL[2] - VERT[2]) * t)
        fd.line([(0, y), (S, y)], fill=(r, g, b, 255))
    masque = Image.new("L", (S, S), 0)
    ImageDraw.Draw(masque).rounded_rectangle([0, 0, S - 1, S - 1], radius=int(S * 0.1875), fill=255)
    img.paste(fond, (0, 0), masque)

    # ombre du spot
    d = ImageDraw.Draw(img)
    d.ellipse([S * 0.355, S * 0.80, S * 0.645, S * 0.865], fill=(8, 59, 49, 115))

    # l'épingle : tête ronde + pointe triangulaire arrondie par le cercle
    cx, cy, r = S * 0.5, S * 0.39, S * 0.242
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 255))
    # pointe : triangle des tangentes du cercle vers le bas
    d.polygon([(cx - r * 0.62, cy + r * 0.72), (cx + r * 0.62, cy + r * 0.72), (cx, S * 0.825)],
              fill=(255, 255, 255, 255))

    # le « ? » au centre de la tête
    f = police(int(S * 0.34))
    bbox = d.textbbox((0, 0), "?", font=f)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), "?", font=f, fill=TEAL + (255,))

    return img.resize((cote, cote), Image.LANCZOS)


def main():
    for cote in (192, 512):
        dessiner(cote).save(ICONS / f"icon-{cote}.png")
        print(f"icons/icon-{cote}.png écrit")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
