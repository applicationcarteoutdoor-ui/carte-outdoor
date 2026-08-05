# -*- coding: utf-8 -*-
"""
Restaurants LABELLISÉS (v84) — source DATAtourisme, Licence Ouverte.

⚠️ Michelin, Gault&Millau et Petit Futé sont des bases PROPRIÉTAIRES : leurs
sélections ne peuvent pas être reprises (même cas qu'Urbexology). Et il
n'existe rien de libre sur les étoilés — mesuré : le tag OSM `michelin_star`
a ZÉRO usage dans le monde, et Wikidata ne compte que 623 restaurants
français géolocalisés au total.

La seule voie propre est donc le LABEL OFFICIEL, vérifiable et public :
Maître Restaurateur (titre d'État), Logis, Bistrot de Pays… DATAtourisme
(base nationale alimentée par les offices de tourisme, Licence Ouverte) les
porte dans sa colonne `Classements_du_POI`.

Le fichier source fait ~267 Mo : il est lu EN FLUX, filtré à la volée, jamais
stocké entier.

Étape 1 (audit)  : python tools/recolter_restaurants_labels.py --audit
Étape 2 (récolte): python tools/recolter_restaurants_labels.py --ecrire
"""

import csv
import io
import json
import re
import ssl
import sys
import urllib.request
from collections import Counter
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "SpotMap/1.0 (cartographie outdoor personnelle; bidband4@gmail.com)"}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

SOURCE = ("https://static.data.gouv.fr/resources/datatourisme-la-base-nationale-"
          "des-donnees-publiques-dinformation-touristique-en-open-data/"
          "20260805-025037/datatourisme-place.csv")

# Distinctions retenues, telles que les offices de tourisme les publient dans
# DATAtourisme (Licence Ouverte). Trois familles, affichées distinctement :
#   - « officiel »  : titre décerné par l'État, le plus fort ;
#   - « label »     : label associatif ou professionnel national ;
#   - « guide »     : mention d'un guide gastronomique. Reprise ici depuis une
#     base PUBLIQUE en Licence Ouverte — sans note ni commentaire, et sur une
#     fraction seulement des établissements cités : ce n'est pas une reprise
#     du guide lui-même, qu'on ne récolte évidemment jamais.
#
# ⚠️ NE JAMAIS faire correspondre « 3/4/5 étoiles » : dans DATAtourisme c'est
# le classement HÔTELIER officiel, pas une étoile Michelin. Les confondre
# afficherait une distinction culinaire imaginaire.
LABELS = {
    "Maître Restaurateur": (r"ma[iî]tre[s]?\s+restaurateur", "officiel"),
    "Restaurateur de France": (r"restaurateur[s]?\s+de\s+france", "label"),
    "Tables et Auberges de France": (r"tables?\s+et\s+auberges?", "label"),
    "Collège culinaire de France": (r"coll[eè]ge\s+culinaire", "label"),
    "Logis": (r"\blogis\b", "label"),
    "Bistrot de Pays": (r"bistrot\s+de\s+pays", "label"),
    "Restaurant Gourmand": (r"restaurant\s+gourmand", "label"),
    "Guide Michelin": (r"(guide|s[eé]lection)\s+michelin|michelin", "guide"),
    "Gault&Millau": (r"gault\s*&?\s*millau", "guide"),
    "Bottin Gourmand": (r"bottin\s+gourmand", "guide"),
    "Le Fooding": (r"le\s+fooding", "guide"),
}
RE_RESTAURANT = re.compile(r"#(Restaurant|FoodEstablishment|BarOrPub)\b", re.I)


def flux():
    """Lit le CSV distant en flux (267 Mo : jamais chargé en mémoire)."""
    req = urllib.request.Request(SOURCE, headers=UA)
    rep = urllib.request.urlopen(req, timeout=900, context=CTX)
    return csv.DictReader(io.TextIOWrapper(rep, encoding="utf-8", errors="replace"))


def auditer():
    """Quels labels existent RÉELLEMENT sur les restaurants, et combien ?"""
    labels = Counter()
    n_resto = n_total = 0
    for ligne in flux():
        n_total += 1
        if not RE_RESTAURANT.search(ligne.get("Categories_de_POI") or ""):
            continue
        n_resto += 1
        for cl in (ligne.get("Classements_du_POI") or "").split("#"):
            cl = cl.strip()
            if cl:
                labels[cl] += 1
        if n_total % 200000 == 0:
            print(f"  … {n_total} lignes, {n_resto} restaurants", flush=True)
    print(f"\n{n_total} POI lus, {n_resto} restaurants")
    print("\n=== LABELS les plus fréquents sur les restaurants ===")
    for lab, n in labels.most_common(40):
        print(f"  {n:6}  {lab[:70]}")
    return labels


def _coord(v):
    try:
        f = float(str(v).replace(",", "."))
        return f if -90 <= f <= 90 or -180 <= f <= 180 else None
    except Exception:
        return None


def recolter():
    gardes, vus = [], set()
    n_resto = 0
    for ligne in flux():
        if not RE_RESTAURANT.search(ligne.get("Categories_de_POI") or ""):
            continue
        n_resto += 1
        classements = (ligne.get("Classements_du_POI") or "")
        trouves = [nom for nom, (motif, _f) in LABELS.items()
                   if re.search(motif, classements, re.I)]
        if not trouves:
            continue
        # famille la plus forte : titre d'État > label > guide
        familles = {LABELS[n][1] for n in trouves}
        famille = ("officiel" if "officiel" in familles
                   else "label" if "label" in familles else "guide")
        lat = _coord(ligne.get("Latitude"))
        lon = _coord(ligne.get("Longitude"))
        if lat is None or lon is None or not (41 <= lat <= 52 and -6 <= lon <= 10):
            continue  # hors métropole ou coordonnées absentes
        nom = (ligne.get("Nom_du_POI") or "").strip()
        if not nom:
            continue
        cle = f"{nom.lower()}|{round(lat,4)}|{round(lon,4)}"
        if cle in vus:
            continue
        vus.add(cle)
        cp_com = (ligne.get("Code_postal_et_commune") or "").split("#")
        gardes.append({
            "nom": nom,
            "lat": round(lat, 6),
            "lon": round(lon, 6),
            "labels": trouves,
            "famille": famille,
            "adresse": (ligne.get("Adresse_postale") or "").strip()[:120],
            "commune": (cp_com[1] if len(cp_com) > 1 else "").strip()[:60],
            "cp": (cp_com[0] if cp_com else "").strip()[:5],
            "uri": (ligne.get("URI_ID_du_POI") or "").strip(),
            "maj": (ligne.get("Date_de_mise_a_jour") or "").strip()[:10],
            "contacts": (ligne.get("Contacts_du_POI") or "").strip()[:200],
        })
    print(f"\n{n_resto} restaurants lus → {len(gardes)} labellisés retenus")
    print("  par label :", dict(Counter(l for g in gardes for l in g["labels"])))
    (DOSSIER / "restaurants-labels-fr.json").write_text(
        json.dumps(gardes, ensure_ascii=False), encoding="utf-8")
    print("ÉCRIT tools/restaurants-labels-fr.json")
    return gardes


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if "--audit" in sys.argv:
        auditer()
    elif "--ecrire" in sys.argv:
        recolter()
    else:
        print(__doc__)
