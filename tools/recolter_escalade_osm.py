# -*- coding: utf-8 -*-
"""
Récolte OSM des SITES d'escalade (crags) de France — support de la revue de la
catégorie « escalade » : recalage GPS (nos 2033 points sont au centroïde de
commune) et détection des sites manquants.

Modèle : recolter_eau.py (tuiles 3° adaptatives, aire France, retries 20/60/120,
cache par tuile reprenable). On récolte les objets `sport=climbing` NOMMÉS en
EXCLUANT les voies individuelles (climbing=route/route_bottom) pour ne garder que
les sites/falaises. Le clustering (côté revue) fait le reste.

Lancer :  python tools/recolter_escalade_osm.py
Sortie   :  tools/escalade-osm-brut.json (liste d'éléments OSM, center inclus)
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CACHE_TUILES = DOSSIER / "escalade-osm-tuiles.json"
HEARTBEAT = DOSSIER / "escalade-osm-status.json"
BRUT = DOSSIER / "escalade-osm-brut.json"

UA = {"User-Agent": "CarteOutdoor/1.0 (application personnelle de cartographie outdoor)"}
OVERPASS = "https://overpass-api.de/api/interpreter"
LAT_MIN, LAT_MAX = 41.0, 51.5
LON_MIN, LON_MAX = -5.5, 10.0
PAS = 3.0
TUILE_MIN = 0.75


def _selecteurs(bbox):
    # Sites d'escalade nommés, SAUF les voies individuelles.
    base = '["sport"="climbing"]["name"]["climbing"!="route_bottom"]["climbing"!="route"]'
    return "".join(f'{k}{base}(area.fr)({bbox});' for k in ("node", "way", "relation"))


def _requete(bbox):
    return ('[out:json][timeout:280];'
            'area["ISO3166-1"="FR"]["admin_level"="2"]->.fr;'
            '(' + _selecteurs(bbox) + ');out center tags;')


def _overpass(requete):
    donnees = urllib.parse.urlencode({"data": requete}).encode()
    for attente in (0, 20, 60, 120):
        if attente:
            print(f"    (Overpass occupé, pause {attente} s…)", flush=True)
            time.sleep(attente)
        req = urllib.request.Request(OVERPASS, data=donnees, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=300) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code not in (429, 504):
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("Overpass surchargé (429/504/timeout persistant)")


def _clef(w, s, e, n):
    return f"{s:.4f},{w:.4f},{n:.4f},{e:.4f}"


def _charger(path, defaut):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else defaut


def _sauver(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")


def _statut(resultats, echecs, phase, extra=None):
    tuiles = sum(1 for v in resultats.values() if isinstance(v, list))
    elems = sum(len(v) for v in resultats.values() if isinstance(v, list))
    d = {"phase": phase, "tuiles_ok": tuiles, "elements_bruts": elems,
         "echecs": echecs, "horodatage": time.strftime("%Y-%m-%d %H:%M:%S")}
    if extra:
        d.update(extra)
    _sauver(HEARTBEAT, d)


def recolter():
    resultats = _charger(CACHE_TUILES, {})
    echecs = []

    def traiter(w, s, e, n):
        key = _clef(w, s, e, n)
        cached = resultats.get(key)
        if isinstance(cached, list):
            return
        if isinstance(cached, dict) and cached.get("split"):
            _subdiviser(w, s, e, n)
            return
        bbox = f"{s},{w},{n},{e}"
        print(f"  tuile {key} …", flush=True)
        try:
            d = _overpass(_requete(bbox))
            els = d.get("elements", [])
            resultats[key] = els
            _sauver(CACHE_TUILES, resultats)
            _statut(resultats, len(echecs), "recolte",
                    {"derniere_tuile": key, "elements_tuile": len(els)})
            print(f"    -> {len(els)} éléments", flush=True)
            time.sleep(2)
        except Exception as exc:
            largeur = min(e - w, n - s)
            if largeur > TUILE_MIN + 1e-9:
                print(f"    ! échec, subdivision de {key} : {exc}", flush=True)
                resultats[key] = {"split": True}
                _sauver(CACHE_TUILES, resultats)
                _subdiviser(w, s, e, n)
            else:
                print(f"    !! échec définitif {key} : {exc}", flush=True)
                echecs.append(key)
                _statut(resultats, len(echecs), "recolte", {"echec_tuile": key})

    def _subdiviser(w, s, e, n):
        mw, ms = (w + e) / 2, (s + n) / 2
        for sw, ss, se, sn in ((w, s, mw, ms), (mw, s, e, ms),
                               (w, ms, mw, n), (mw, ms, e, n)):
            traiter(sw, ss, se, sn)

    lon = LON_MIN
    while lon < LON_MAX - 1e-9:
        lat = LAT_MIN
        while lat < LAT_MAX - 1e-9:
            traiter(lon, lat, min(lon + PAS, LON_MAX), min(lat + PAS, LAT_MAX))
            lat += PAS
        lon += PAS

    if echecs:
        print(f"\n  ! {len(echecs)} tuile(s) en échec : {echecs}", flush=True)
    else:
        print("\n  Toutes les tuiles récoltées.", flush=True)

    # Dédoublonnage inter-tuiles par (type, id) et fusion → brut
    vus, brut = set(), []
    for els in resultats.values():
        if not isinstance(els, list):
            continue
        for e in els:
            cle = (e.get("type"), e.get("id"))
            if cle in vus:
                continue
            vus.add(cle)
            brut.append(e)
    _sauver(BRUT, brut)
    _statut(resultats, len(echecs), "termine", {"brut": len(brut)})
    print(f"\nÉCRIT : {len(brut)} éléments OSM uniques -> {BRUT.name}", flush=True)
    return brut


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
