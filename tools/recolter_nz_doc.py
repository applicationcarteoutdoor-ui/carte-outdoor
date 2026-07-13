# -*- coding: utf-8 -*-
"""
Récolte des données du DOC (Department of Conservation, Nouvelle-Zélande) —
huttes, campings et segments des Great Walks. Source OFFICIELLE via les
FeatureServers ArcGIS publics du DOC, licence **CC-BY 4.0** (« DOC, © Crown »,
attribution affichée dans l'app). Aucune clé requise.

Services (org 3JjYDyG3oajxU6HO) — utiliser les *_DTO, les anciens
DOC_Huts/DOC_Campsites sont DÉPRÉCIÉS (répondent encore mais ne sont plus
maintenus ; l'ancien Huts contient ~500 huttes non maintenues en plus) :
  - DOC_Huts_DTO/0       (~958 huttes)   champs métier en paires pivot
  - DOC_Campsites_DTO/0  (~326 campings)  CharName1..15/CharValue1..15
  - DOC_Tracks_EAM/0     SubObjectType='Great Walk' → 77 segments, regroupables
                         proprement par préfixe FlocID (MILFRDTK-, KEPLERTK-…)

PIÈGES payés :
  - outSR=4326 OBLIGATOIRE (données natives NZTM/EPSG:2193 → millions de mètres) ;
  - pagination resultOffset SANS orderByFields = instable (doublons/trous) ;
  - paires pivot : le mapping index→nom VARIE par entité → pivoter par CharName,
    jamais par indice ; bunks en TEXTE (« 54 each ») → parser.

Lancer :  python tools/recolter_nz_doc.py
Sortie   :  tools/nz-doc.json
"""

import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
SORTIE = DOSSIER / "nz-doc.json"
BASE = "https://services1.arcgis.com/3JjYDyG3oajxU6HO/arcgis/rest/services"
UA = {"User-Agent": "CarteOutdoor/1.0 (cartographie outdoor personnelle)"}
CTX = ssl.create_default_context()
CTX_NV = ssl.create_default_context(); CTX_NV.check_hostname = False; CTX_NV.verify_mode = ssl.CERT_NONE


def _get(url):
    for ctx in (CTX, CTX_NV):
        for attente in (0, 10, 30):
            if attente:
                time.sleep(attente)
            try:
                with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120, context=ctx) as r:
                    return json.load(r)
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ConnectionError, ssl.SSLError) as e:
                print(f"    (réseau : {e})", flush=True)
    raise RuntimeError("ArcGIS DOC injoignable")


def requeter(service, layer, where="1=1", champs="*"):
    """Toutes les entités (géométrie WGS84, pagination TRIÉE par OBJECTID)."""
    feats, offset = [], 0
    while True:
        url = (f"{BASE}/{service}/FeatureServer/{layer}/query?"
               f"where={urllib.parse.quote(where)}&outFields={urllib.parse.quote(champs)}"
               f"&returnGeometry=true&outSR=4326&orderByFields=OBJECTID"
               f"&resultOffset={offset}&resultRecordCount=1000&f=json")
        d = _get(url)
        lot = d.get("features", [])
        feats.extend(lot)
        print(f"  {service}: {len(feats)}…", flush=True)
        if not d.get("exceededTransferLimit") and len(lot) < 1000:
            break
        offset += len(lot)
        time.sleep(0.5)
    return feats


def pivot(attrs):
    """Reconstruit {nom_de_champ: valeur} depuis les paires CharName#/CharValue#."""
    d = {}
    for i in range(1, 16):
        nom = attrs.get(f"CharName{i}")
        if nom:
            d[nom.strip()] = (attrs.get(f"CharValue{i}") or "").strip()
    return d


def nombre(texte):
    """« 54 each », « 20 » → 54, 20 (None si pas de nombre)."""
    m = re.search(r"\d+", str(texte or ""))
    return int(m.group()) if m else None


def recolter():
    donnees = {}

    # 1. Huttes (DTO : statut, catégorie, couchettes, équipements via pivot)
    feats = requeter("DOC_Huts_DTO", 0)
    huts = []
    for f in feats:
        a = f.get("attributes", {})
        g = f.get("geometry") or {}
        lon, lat = g.get("x"), g.get("y")
        nom = (a.get("TechObjectName") or "").strip()
        if not (lat and lon and nom):
            continue
        p = pivot(a)
        huts.append({
            "nom": nom,
            "statut": p.get("USER_STATUS", ""),
            "categorie": p.get("WEB_CATEGORY_HUT", ""),
            "couchettes": nombre(p.get("WEB_HUT_BUNKS")),
            "equipements": p.get("WEB_FACILITIES_HUT", ""),
            "public": p.get("PUBLIC_USE", ""),
            "lat": round(lat, 6), "lon": round(lon, 6),
        })
    donnees["huts"] = huts

    # 2. Campings (DTO, même modèle pivot)
    feats = requeter("DOC_Campsites_DTO", 0)
    camps = []
    for f in feats:
        a = f.get("attributes", {})
        g = f.get("geometry") or {}
        lon, lat = g.get("x"), g.get("y")
        nom = (a.get("TechObjectName") or "").strip()
        if not (lat and lon and nom):
            continue
        p = pivot(a)
        camps.append({
            "nom": nom,
            "statut": p.get("USER_STATUS", ""),
            "categorie": p.get("WEB_CATEGORY_CAMPSITE", "") or (a.get("SubObjectType") or "").strip(),
            "places": nombre(p.get("WEB_CAMPSITE_SITES") or p.get("WEB_NO_OF_SITES")),
            "equipements": p.get("WEB_FACILITIES_CAMPSITE", ""),
            "public": p.get("PUBLIC_USE", ""),
            "pivot": p,  # gardé brut : les noms de champs campings varient
            "lat": round(lat, 6), "lon": round(lon, 6),
        })
    donnees["campsites"] = camps

    # 3. Great Walks : segments EAM par PRÉFIXE FlocID (chaque préfixe = un
    #    itinéraire). PIÈGE : filtrer SubObjectType='Great Walk' rend les tracés
    #    TROUÉS — les sections d'accès du même itinéraire sont typées « Walking
    #    Track » (ex. Kepler : Control Gates→Brod Bay). On prend donc TOUT le
    #    FlocID de l'itinéraire, moins les Short Walks annexes (nature walks).
    #    LHAUROBC (South Coast Track) : seul son tronçon typé Great Walk fait
    #    partie du Hump Ridge — « tous types » embarquerait le South Coast
    #    entier au-delà de Port Craig (Hump Ridge passait de 61 à 128 km).
    prefixes = ("ABTASCOT", "HEAPHYTK", "HUMPRIDG", "KEPLERTK",
                "MILFRDTK", "PAPROAGW", "RAKIURAT", "ROUTEBRN", "TONGARNC",
                "TONGARAC", "WAIKARTK")
    where = ("((" + " OR ".join(f"FlocID LIKE '{p}%'" for p in prefixes) + ")"
             " AND SubObjectType NOT IN ('Short Walk','Short Walk (disabled)'))"
             " OR (FlocID LIKE 'LHAUROBC%' AND SubObjectType='Great Walk')")
    feats = requeter("DOC_Tracks_EAM", 0, where=where,
                     champs="TechObjectName,FlocID")
    segs = []
    for f in feats:
        a = f.get("attributes", {})
        paths = (f.get("geometry") or {}).get("paths") or []
        if not paths:
            continue
        segs.append({
            "nom": (a.get("TechObjectName") or "").strip(),
            "floc": (a.get("FlocID") or "").strip(),
            "paths": [[[round(x, 6), round(y, 6)] for x, y in p] for p in paths],
        })
    donnees["greatwalk_segments"] = segs

    # 4. Métadonnées des ANCIENS datasets (dépréciés mais stables) : parc,
    #    région et LIEN VERS LA PAGE DOC OFFICIELLE — absents des *_DTO.
    #    Rapprochés par nom+proximité dans construire_nz.py.
    for svc, cle in (("DOC_Huts", "huts_meta"), ("DOC_Campsites", "camps_meta")):
        feats = requeter(svc, 0, champs="name,place,region,staticLink,x,y")
        meta = []
        for f in feats:
            a = f.get("attributes", {})
            g = f.get("geometry") or {}
            lon, lat = g.get("x") or a.get("x"), g.get("y") or a.get("y")
            if not (lat and lon and a.get("name")):
                continue
            meta.append({
                "nom": a["name"].strip(),
                "lieu": (a.get("place") or "").strip(),
                "region": (a.get("region") or "").strip(),
                "lien": (a.get("staticLink") or "").strip(),
                "lat": round(lat, 6), "lon": round(lon, 6),
            })
        # dédoublonnage (l'ancien dataset contient des doublons)
        vus, uniques = set(), []
        for m in meta:
            k = (m["nom"].lower(), round(m["lat"], 4), round(m["lon"], 4))
            if k not in vus:
                vus.add(k)
                uniques.append(m)
        donnees[cle] = uniques

    SORTIE.write_text(json.dumps(donnees, ensure_ascii=False), encoding="utf-8")
    print(f"\nÉCRIT : {len(huts)} huttes, {len(camps)} campings, "
          f"{len(segs)} segments Great Walk -> {SORTIE.name}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    recolter()
