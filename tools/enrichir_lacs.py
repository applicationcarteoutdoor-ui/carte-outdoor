# -*- coding: utf-8 -*-
"""
Enrichissement de la catégorie « lac » à partir de Wikidata (CC0) et Wikimedia
Commons, en place dans data/points.geojson (ids stables).

Constat de l'audit : les 965 lacs ont un article Wikipédia (100 % liens), une
altitude IGN (100 %), et sont recentrés dans l'eau — le GPS est bon, aucun
recalage. Manquent : superficie (39 %), profondeur (74 %), photo (21 %).
Ces 21 % sans photo sont exactement les 20 % « À vérifier » (la fiche exige
une photo). Les faits (superficie/profondeur) et l'image sont dans Wikidata,
non entièrement capturés au premier passage.

On ne remplit QUE le vide, en FAITS réutilisables :
  - P2046 superficie (converti en hectares, affiché ha / km²) ;
  - P4511 profondeur maximale (mètres) ;
  - P18 image → vignette 400 px sur upload.wikimedia.org (via l'API Commons ;
    upload.wikimedia est le seul hôte autorisé par la CSP).

Lancer :  python tools/enrichir_lacs.py            (simulation)
          python tools/enrichir_lacs.py --ecrire   (écrit points.geojson)
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
CIBLE = DOSSIER.parent / "data" / "points.geojson"
CACHE_WP = DOSSIER / "lacs-wiki-pages.json"
CACHE_WD = DOSSIER / "lacs-wd-enrichir.json"     # qid → {p18, superficie_ha, profondeur}
CACHE_IMG = DOSSIER / "lacs-commons-img.json"    # filename → url 400px | null
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}

# Unités Wikidata de superficie → facteur vers hectares
UNITE_HA = {"Q712226": 100.0, "Q35852": 1.0, "Q25343": 1e-4, "Q2489629": 0.01}


def http_json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40) as r:
        return json.load(r)


def fmt(v):
    """Nombre en français : virgule décimale, entier si rond."""
    if float(v).is_integer():
        return str(int(v))
    return f"{v:.1f}".replace(".", ",")


def superficie_txt(ha):
    if ha >= 100:
        return f"{fmt(ha / 100)} km²"
    return f"{fmt(ha)} ha"


def charger(path):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def fetch_wikidata(qids):
    """{qid: {p18, superficie_ha, profondeur}} — P18 / P2046 / P4511, lots de 50."""
    cache = charger(CACHE_WD)
    a_faire = [q for q in dict.fromkeys(qids) if q and q not in cache]
    if a_faire:
        print(f"  Wikidata : {len(a_faire)} entités (P18/P2046/P4511)…")
    for i in range(0, len(a_faire), 50):
        lot = a_faire[i:i + 50]
        url = ("https://www.wikidata.org/w/api.php?action=wbgetentities&format=json"
               "&props=claims&ids=" + "|".join(lot))
        try:
            d = http_json(url)
        except Exception as exc:
            print(f"    ! wikidata : {exc} — pause 15 s"); time.sleep(15); continue
        for q, ent in (d.get("entities") or {}).items():
            cl = ent.get("claims") or {}

            def snak(pid):
                c = cl.get(pid) or []
                return c[0].get("mainsnak", {}).get("datavalue", {}).get("value") if c else None

            img = snak("P18")
            sup = snak("P2046")
            prof = snak("P4511")
            ha = None
            if isinstance(sup, dict):
                try:
                    unite = sup.get("unit", "").rstrip("/").split("/")[-1]
                    ha = abs(float(sup["amount"])) * UNITE_HA.get(unite, 0)
                    ha = ha or None
                except (ValueError, TypeError):
                    ha = None
            m = None
            if isinstance(prof, dict):
                try:
                    m = abs(float(prof["amount"]))
                except (ValueError, TypeError):
                    m = None
            cache[q] = {"p18": img if isinstance(img, str) else None,
                        "superficie_ha": ha, "profondeur": m}
        CACHE_WD.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 50, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.4)
    return cache


def fetch_commons(noms):
    """{filename: url 400px sur upload.wikimedia | None} via l'API Commons."""
    cache = charger(CACHE_IMG)
    a_faire = [n for n in dict.fromkeys(noms) if n and n not in cache]
    if a_faire:
        print(f"  Commons : {len(a_faire)} images à résoudre…")
    for i in range(0, len(a_faire), 40):
        lot = a_faire[i:i + 40]
        titres = "|".join("File:" + n for n in lot)
        url = ("https://commons.wikimedia.org/w/api.php?action=query&format=json"
               "&prop=imageinfo&iiprop=url&iiurlwidth=400&titles=" + urllib.parse.quote(titres))
        try:
            d = http_json(url)
        except Exception as exc:
            print(f"    ! commons : {exc} — pause 15 s"); time.sleep(15); continue
        trouve = {}
        for page in (d.get("query", {}).get("pages") or {}).values():
            ii = (page.get("imageinfo") or [{}])[0]
            # l'API normalise les titres avec des ESPACES → on repasse en
            # underscores pour matcher les clés du lot (bug corrigé).
            nom = re.sub(r"^File:", "", page.get("title", "")).replace(" ", "_")
            u = ii.get("thumburl") or ii.get("url") or ""
            trouve[nom] = u if u.startswith("https://upload.wikimedia.org") else None
        for n in lot:
            cache[n] = trouve.get(n)
        CACHE_IMG.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        print(f"    {min(i + 40, len(a_faire))}/{len(a_faire)}")
        time.sleep(0.3)
    return cache


def main(ecrire=False):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    d = json.loads(CIBLE.read_text(encoding="utf-8"))
    lac = [f for f in d["features"] if f["properties"].get("theme") == "lac"]
    print(f"lacs : {len(lac)}")

    wp = charger(CACHE_WP)
    url2qid = {(v.get("url") or "").rstrip("/"): v.get("qid")
               for v in wp.values() if isinstance(v, dict) and v.get("qid")}

    # QID de chaque lac auquel il manque quelque chose
    besoins = []
    for f in lac:
        p = f["properties"]
        det = p.get("details") or {}
        if p.get("photos") and "superficie" in det and "profondeur" in det:
            continue
        q = url2qid.get((p.get("link") or "").rstrip("/"))
        if q:
            besoins.append(q)
    wd = fetch_wikidata(besoins)

    # Résolution des images Commons nécessaires (lacs sans photo dont le QID a une P18)
    imgs = []
    for f in lac:
        if f["properties"].get("photos"):
            continue
        q = url2qid.get((f["properties"].get("link") or "").rstrip("/"))
        info = wd.get(q) if q else None
        if info and info.get("p18"):
            imgs.append(info["p18"].replace(" ", "_"))
    commons = fetch_commons(imgs)

    st = {"photo": 0, "superficie": 0, "profondeur": 0, "refait": 0}
    for f in lac:
        p = f["properties"]
        det = p.setdefault("details", {})
        q = url2qid.get((p.get("link") or "").rstrip("/"))
        info = wd.get(q) if q else None
        if not info:
            continue
        if not p.get("photos") and info.get("p18"):
            u = commons.get(info["p18"].replace(" ", "_"))
            if u:
                p["photos"] = [u]; st["photo"] += 1
        if "superficie" not in det and info.get("superficie_ha"):
            ha = info["superficie_ha"]
            det["superficie"] = superficie_txt(ha)
            det["superficie_n"] = round(ha, 1)
            st["superficie"] += 1
        if "profondeur" not in det and info.get("profondeur"):
            det["profondeur"] = f"{fmt(info['profondeur'])} m"
            st["profondeur"] += 1
        # fiche : Référencé = photo (comme les autres catégories)
        avant = det.get("fiche")
        det["fiche"] = "Référencé" if p.get("photos") else "À vérifier"
        if avant != det["fiche"]:
            st["refait"] += 1

    print(f"\nAjouts : photo {st['photo']} | superficie {st['superficie']} | profondeur {st['profondeur']}")
    # couverture
    tot = len(lac)
    q = lambda t: sum(1 for f in lac if t(f["properties"])) * 100 // tot
    print(f"Couverture : photo {q(lambda p: p.get('photos'))} %, "
          f"superficie {q(lambda p: 'superficie' in (p.get('details') or {}))} %, "
          f"profondeur {q(lambda p: 'profondeur' in (p.get('details') or {}))} %, "
          f"Référencé {q(lambda p: (p.get('details') or {}).get('fiche') == 'Référencé')} %")

    if ecrire:
        CIBLE.write_text(json.dumps(d, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"ÉCRIT. {CIBLE.stat().st_size // 1024} Ko")
    else:
        print("(SIMULATION — rien écrit.)")


if __name__ == "__main__":
    main(ecrire="--ecrire" in sys.argv)
