# -*- coding: utf-8 -*-
"""
Fusion finale de la catégorie escalade à partir de sources RÉUTILISABLES :

  - RES / data-es (Licence Ouverte Etalab) = SOCLE : coordonnées précises,
    hauteur, commune, accès. Recale nos points encore au centre de commune ET
    fournit les sites manquants (officiels, nationaux).
  - Camp to Camp (FAITS seulement : cotation, roche, nb de voies, orientation ;
    JAMAIS prose ni photo — cf. licence) : enrichit par PROXIMITÉ.
  - Corde recommandée : ESTIMÉE depuis la hauteur (≈ 2 × hauteur + marge),
    libellée comme estimation. Pas de champ source structuré.

Ids existants conservés ; nouveaux sites en esc-NNNN. Écrit data/points.geojson.

Lancer :  python tools/fusion_escalade.py [--ecrire]
"""

import json
import re
import time
import unicodedata
import urllib.error
import urllib.request
from collections import defaultdict
from math import ceil
from pathlib import Path

import revue_via_ferrata as rvf
from enrichir_escalade_c2c import extraire

DOSSIER = Path(__file__).resolve().parent
CIBLE = DOSSIER.parent / "data" / "points.geojson"
RES = json.loads((DOSSIER / "escalade-res.json").read_text(encoding="utf-8"))
C2C = json.loads((DOSSIER / "escalade-c2c.json").read_text(encoding="utf-8"))
DETAIL_PATH = DOSSIER / "escalade-c2c-detail.json"
DETAIL = json.loads(DETAIL_PATH.read_text(encoding="utf-8")) if DETAIL_PATH.exists() else {}
STATUT = DOSSIER / "fusion-escalade-status.json"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}

R_EXIST = 500      # m : un site source à < 500 m d'un point existant = déjà couvert
R_FACTS = 450      # m : rapprochement pour enrichir en faits C2C
R_DEDUP = 500      # m : entre nouveaux sites


def norm(t):
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", t.lower())


def commune_desc(desc):
    m = re.search(r"Commune\s*:\s*([^(]+)", desc or "")
    return norm(m.group(1)) if m else ""


RE_GENERIQUE = re.compile(
    r"^\s*(site naturel|secteur\s+(face\s+)?(nord|sud|est|ouest|[nseo])\b|falaise|[ée]cole)\s*",
    re.I)


def nom_site(secteur, commune):
    """Nom lisible : le secteur s'il est distinctif, sinon la commune."""
    sec = (secteur or "").strip().strip('"').strip()
    if not sec or len(sec) < 3 or RE_GENERIQUE.match(sec):
        return commune
    return sec


def rope_est(h):
    try:
        h = float(re.search(r"\d+", str(h)).group())
    except Exception:
        return ""
    if h < 18:
        return ""  # sur une petite falaise, la corde n'est pas le facteur limitant
    r = min(max(ceil((2 * h + 8) / 10) * 10, 60), 120)
    return f"≈ {r} m (estimation d'après la hauteur)"


# --- Index spatial grossier des sites C2C (pour proximité rapide) ---
_grid = defaultdict(list)
for s in C2C:
    _grid[(round(s["lat"], 1), round(s["lon"], 1))].append(s)


def c2c_proche(lat, lon, r=R_FACTS):
    best = None
    for dlat in (-0.1, 0, 0.1):
        for dlon in (-0.1, 0, 0.1):
            for s in _grid.get((round(lat + dlat, 1), round(lon + dlon, 1)), []):
                d = rvf.dist_m(lon, lat, s["lon"], s["lat"])
                if d <= r and (best is None or d < best[0]):
                    best = (d, s)
    return best[1] if best else None


def _detail(cid):
    cid = str(cid)
    if cid not in DETAIL:
        for attente in (0, 8):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(
                        f"https://api.camptocamp.org/waypoints/{cid}?l=fr", headers=UA), timeout=40) as r:
                    DETAIL[cid] = extraire(json.load(r))
                    break
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    DETAIL[cid] = {}
                    break
            except Exception:
                DETAIL[cid] = {}
        DETAIL.setdefault(cid, {})
        time.sleep(0.3)
    return DETAIL[cid]


def enrichir_faits(det, lat, lon):
    """Ajoute cotation/roche/voies/orientation depuis le site C2C le plus proche
    (faits réutilisables) + son lien direct. Ne remplit que le vide."""
    s = c2c_proche(lat, lon)
    if not s:
        return None
    info = _detail(s["id"])
    lien = f"https://www.camptocamp.org/waypoints/{s['id']}"
    if info.get("cotation") and not det.get("cotation"):
        det["cotation"] = info["cotation"]
    if info.get("voies") and str(det.get("voies", "0")) in ("0", "", "None"):
        det["voies"] = str(info["voies"]); det["voies_n"] = info["voies"]
    if info.get("roche") and not det.get("roche"):
        det["roche"] = info["roche"]
    if info.get("hauteur") and not det.get("hauteur"):
        det["hauteur"] = info["hauteur"]
    if info.get("orientation") and not det.get("orientation"):
        det["orientation"] = info["orientation"]
    return lien


def main(ecrire=False):
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    esc = [f for f in d["features"] if f["properties"].get("theme") == "escalade"]

    # RES par commune (pour recaler nos points au centroïde)
    res_com = defaultdict(list)
    for s in RES:
        res_com[norm(s["commune"])].append(s)

    # === A. Recaler les points encore au centre de commune, via RES ===
    recal = 0
    for f in esc:
        p = f["properties"]
        if "camptocamp.org/waypoints/" in (p.get("link") or ""):
            continue  # déjà recalé précisément (C2C)
        cands = res_com.get(commune_desc(p.get("description")))
        if not cands:
            continue
        lon, lat = f["geometry"]["coordinates"][:2]
        dd, s = min(((rvf.dist_m(lon, lat, x["lon"], x["lat"]), x) for x in cands), key=lambda t: t[0])
        f["geometry"]["coordinates"] = [s["lon"], s["lat"]]
        det = p.setdefault("details", {})
        if s.get("haut") and not det.get("hauteur"):
            det["hauteur"] = f"{int(s['haut'])} m"
        p["description"] = re.sub(r"\s*\(Position au centre de la commune[^)]*\)", "", p.get("description", "")).strip()
        lien = enrichir_faits(det, s["lat"], s["lon"])
        if lien and not p.get("link"):
            p["link"] = lien
        recal += 1
        if recal % 50 == 0:
            DETAIL_PATH.write_text(json.dumps(DETAIL, ensure_ascii=False), encoding="utf-8")
            STATUT.write_text(json.dumps({"phase": "recalage", "recal": recal}), encoding="utf-8")
            print(f"  recalés {recal}…", flush=True)

    # === Corde estimée (pour tous ceux qui ont une hauteur, sans corde) ===
    corde = 0
    for f in esc:
        det = f["properties"].get("details") or {}
        if det.get("hauteur") and not det.get("corde"):
            c = rope_est(det["hauteur"])
            if c:
                det["corde"] = c; det["corde_n"] = int(re.search(r"\d+", c).group()); corde += 1

    # === B. Ajouter les sites RES manquants (loin de tout point existant) ===
    existants = [(f["geometry"]["coordinates"][0], f["geometry"]["coordinates"][1]) for f in esc]
    grille_ex = defaultdict(list)
    for lo, la in existants:
        grille_ex[(round(la, 1), round(lo, 1))].append((lo, la))

    def loin(lat, lon, r):
        for dlat in (-0.1, 0, 0.1):
            for dlon in (-0.1, 0, 0.1):
                for lo, la in grille_ex.get((round(lat + dlat, 1), round(lon + dlon, 1)), []):
                    if rvf.dist_m(lon, lat, lo, la) <= r:
                        return False
        return True

    nums = [int(m.group(1)) for f in esc if (m := re.match(r"esc-(\d+)", f["properties"]["id"]))]
    prochain = max(nums) + 1
    ajouts = []
    ajoutes_coords = []
    for i, s in enumerate(RES):
        if not loin(s["lat"], s["lon"], R_EXIST):
            continue
        if any(rvf.dist_m(s["lon"], s["lat"], lo, la) <= R_DEDUP for lo, la in ajoutes_coords):
            continue
        det = {"type": "Site de blocs" if s["type"] == "bloc" else "Site sportif"}
        if s.get("haut"):
            det["hauteur"] = f"{int(s['haut'])} m"
        lien = enrichir_faits(det, s["lat"], s["lon"])
        c = rope_est(det.get("hauteur", ""))
        if c:
            det["corde"] = c; det["corde_n"] = int(re.search(r"\d+", c).group())
        nom = nom_site(s["secteur"], s["commune"])
        desc = f"Commune : {s['commune']} ({s['dep']})"
        if s.get("gest"):
            desc += f"\nGestion : {s['gest']}"
        ajouts.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [s["lon"], s["lat"]]},
            "properties": {
                "id": f"esc-{prochain + len(ajouts):04d}",
                "name": nom, "theme": "escalade",
                "description": desc,
                "link": lien or "", "links": [], "photos": [], "details": det,
            },
        })
        ajoutes_coords.append((s["lon"], s["lat"]))
        if len(ajouts) % 50 == 0:
            DETAIL_PATH.write_text(json.dumps(DETAIL, ensure_ascii=False), encoding="utf-8")
            STATUT.write_text(json.dumps({"phase": "ajout", "ajouts": len(ajouts), "i": i, "total_res": len(RES)}), encoding="utf-8")
            print(f"  ajoutés {len(ajouts)} (RES {i}/{len(RES)})…", flush=True)

    DETAIL_PATH.write_text(json.dumps(DETAIL, ensure_ascii=False), encoding="utf-8")
    print(f"\nRecalés via RES : {recal} | corde estimée : {corde} | sites RES ajoutés : {len(ajouts)}", flush=True)
    print(f"Escalade : {len(esc)} -> {len(esc) + len(ajouts)}", flush=True)

    if ecrire:
        d["features"].extend(ajouts)
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        STATUT.write_text(json.dumps({"phase": "termine", "recal": recal, "corde": corde, "ajouts": len(ajouts)}), encoding="utf-8")
        print("ÉCRIT.", flush=True)
    else:
        STATUT.write_text(json.dumps({"phase": "simulation", "recal": recal, "corde": corde, "ajouts": len(ajouts)}), encoding="utf-8")
        print("(SIMULATION — rien écrit.)", flush=True)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main(ecrire="--ecrire" in sys.argv)
