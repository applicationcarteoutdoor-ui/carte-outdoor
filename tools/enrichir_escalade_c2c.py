# -*- coding: utf-8 -*-
"""
Enrichit les points escalade appariés à Camp to Camp (lien
camptocamp.org/waypoints/ID) avec les infos du DÉTAIL C2C : cotation réelle
(min→max), nombre de voies, type de roche, hauteur, orientation. Ne remplit que
les champs VIDES (ne piétine pas une donnée FFME existante), sauf voies=0 qui est
remplacé. Cache reprenable dans tools/escalade-c2c-detail.json.

Lancer :  python tools/enrichir_escalade_c2c.py
"""

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CIBLE = DOSSIER.parent / "data" / "points.geojson"
CACHE = DOSSIER / "escalade-c2c-detail.json"
STATUT = DOSSIER / "escalade-c2c-detail-status.json"
API = "https://api.camptocamp.org/waypoints/"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}

ROCHE = {"calcaire": "Calcaire", "granite": "Granit", "gneiss": "Gneiss",
         "sandstone": "Grès", "gres": "Grès", "basalt": "Basalte", "basalte": "Basalte",
         "conglomerate": "Conglomérat", "conglomerat": "Conglomérat",
         "quartzite": "Quartzite", "schist": "Schiste", "schiste": "Schiste",
         "molasse": "Molasse", "gritstone": "Grès", "porphyry": "Porphyre",
         "rhyolite": "Rhyolite", "trachyte": "Trachyte", "limestone": "Calcaire"}
ORIENT = {"N": "N", "NE": "NE", "E": "E", "SE": "SE", "S": "S", "SW": "SO",
          "W": "O", "NW": "NO"}


def _get(url):
    for attente in (0, 10, 30):
        if attente:
            time.sleep(attente)
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
    return None


def extraire(w):
    lo, hi = w.get("climbing_rating_min"), w.get("climbing_rating_max")
    cot = f"{lo} à {hi}" if lo and hi and lo != hi else (lo or hi or "")
    rs = w.get("rock_types") or []
    roche = ", ".join(dict.fromkeys(ROCHE.get(r, r.capitalize()) for r in rs))
    ors = w.get("orientations") or []
    orient = ", ".join(ORIENT.get(o, o) for o in ors)
    h = w.get("height_max") or w.get("height_median")
    return {
        "cotation": cot,
        "voies": w.get("routes_quantity"),
        "roche": roche,
        "hauteur": f"{h} m" if h else "",
        "orientation": orient,
    }


def main():
    cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    esc = [f for f in d["features"] if f["properties"].get("theme") == "escalade"]
    cibles = [(f, m.group(1)) for f in esc
              if (m := re.search(r"camptocamp\.org/waypoints/(\d+)", f["properties"].get("link") or ""))]
    print(f"{len(cibles)} points escalade avec lien C2C à enrichir", flush=True)

    faits = 0
    for i, (f, cid) in enumerate(cibles):
        if cid not in cache:
            w = _get(f"{API}{cid}?l=fr")
            cache[cid] = extraire(w) if w else {}
            if i % 25 == 0:
                CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
                STATUT.write_text(json.dumps({"faits": i, "total": len(cibles),
                                  "horodatage": time.strftime("%H:%M:%S")}), encoding="utf-8")
                print(f"  {i}/{len(cibles)}…", flush=True)
            time.sleep(0.4)
    CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    # Application : ne remplit que le vide (voies=0 remplacé)
    maj = {"cotation": 0, "voies": 0, "roche": 0, "hauteur": 0, "orientation": 0}
    for f, cid in cibles:
        info = cache.get(cid) or {}
        det = f["properties"].setdefault("details", {})
        if info.get("cotation") and not det.get("cotation"):
            det["cotation"] = info["cotation"]; maj["cotation"] += 1
        if info.get("voies") and str(det.get("voies", "0")) in ("0", "", "None"):
            det["voies"] = str(info["voies"]); det["voies_n"] = info["voies"]; maj["voies"] += 1
        if info.get("roche") and not det.get("roche"):
            det["roche"] = info["roche"]; maj["roche"] += 1
        if info.get("hauteur") and not det.get("hauteur"):
            det["hauteur"] = info["hauteur"]; maj["hauteur"] += 1
        if info.get("orientation") and not det.get("orientation"):
            det["orientation"] = info["orientation"]; maj["orientation"] += 1

    CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    STATUT.write_text(json.dumps({"phase": "termine", "total": len(cibles), "maj": maj}), encoding="utf-8")
    print(f"\nEnrichi : cotation +{maj['cotation']}, voies +{maj['voies']}, "
          f"roche +{maj['roche']}, hauteur +{maj['hauteur']}, orientation +{maj['orientation']}", flush=True)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
