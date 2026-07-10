# -*- coding: utf-8 -*-
"""
Génération des données de l'application (v3).

Produit :
  - data/points.geojson : via ferrata, refuges non gardés, escalade,
    châteaux, cités de caractère (géocodés au centroïde de commune),
    + 2 points d'exemple (grotte, toilettes)
  - data/gr.geojson : tracés des GR simplifiés (Douglas-Peucker)

Géocodage : les xlsx (escalade, châteaux, cités) n'ont pas de coordonnées.
On les rattache au CENTROÏDE de leur commune via les référentiels officiels
téléchargés une fois dans tools/ :
  - tools/communes.json      (geo.api.gouv.fr/communes?fields=nom,centre,codeDepartement)
  - tools/departements.json  (geo.api.gouv.fr/departements?fields=nom,code)
La précision est donc « au bourg », pas au site exact.

Usage :  python tools/build_data.py
"""

import csv
import io
import json
import re
import sys
import unicodedata
import urllib.parse
from pathlib import Path

import openpyxl

import enrichissements as enr
import recolter_cascades
import recolter_lacs

RACINE = Path(__file__).resolve().parent.parent
DONNEES = RACINE / "Donné"
CSV_VIA_FERRATA = DONNEES / "Via Ferrata" / "via-ferrata-france.csv"
KML_REFUGES = DONNEES / "Refuge" / "refuge non garder total.kml"
KML_GR = DONNEES / "GR" / "La carte  GR.kml"
XLSX_ESCALADE = DONNEES / "Escalade" / "Feuille de calcul sans titre.xlsx"
CSV_ESCALADE_ENRICHI = (DONNEES / "Escalade" / "Avec longeure de corde et distance d'aproche"
                        / "Spots_Enrichis_Verifies.csv")
XLSX_CHATEAUX = DONNEES / "chateau" / "Feuille de calcul sans titre.xlsx"
XLSX_CITES = DONNEES / "city de caractere" / "Feuille de calcul sans titre.xlsx"
HTML_FICHES_VF = RACINE / "tools" / "viaferrata-liste.html"
COMMUNES_JSON = RACINE / "tools" / "communes.json"
DEPARTEMENTS_JSON = RACINE / "tools" / "departements.json"
CIBLE_POINTS = RACINE / "data" / "points.geojson"
CIBLE_GR = RACINE / "data" / "gr.geojson"
CIBLE_TOILETTES = RACINE / "data" / "toilettes.geojson"

SITE_VF = "https://www.viaferrata-fr.net/"

LAT_MIN, LAT_MAX = 41.0, 51.5
LON_MIN, LON_MAX = -5.5, 10.0

RE_COTATION = re.compile(r"\b(ED|TD|AD|PD|F|D)[+-]?")


def normaliser(texte):
    """minuscules, sans accents ni ponctuation — pour comparer des noms."""
    texte = unicodedata.normalize("NFD", texte or "")
    texte = "".join(c for c in texte if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]", "", texte.lower())


def normaliser_commune(texte):
    """Normalisation renforcée pour les noms de communes : St/Ste → Saint,
    et Sainte assimilée à Saint (orthographes fluctuantes des sources)."""
    texte = re.sub(r"\bSte?s?\b\.?", "Saint", texte or "", flags=re.I)
    n = normaliser(texte)
    return n.replace("sainte", "saint")


def lire_xlsx(chemin):
    """Renvoie les lignes (tuples) de la première feuille, en-tête exclu."""
    wb = openpyxl.load_workbook(chemin, read_only=True)
    lignes = list(wb.worksheets[0].iter_rows(values_only=True))
    wb.close()
    return lignes[1:]


# ---------------------------------------------------------------------------
# Référentiel des communes (géocodage au centroïde)
# ---------------------------------------------------------------------------

class Communes:
    def __init__(self):
        data = json.loads(COMMUNES_JSON.read_text(encoding="utf-8"))
        depts = json.loads(DEPARTEMENTS_JSON.read_text(encoding="utf-8"))
        self.dept_par_nom = {normaliser(d["nom"]): d["code"] for d in depts}
        self.nom_par_code = {d["code"]: d["nom"] for d in depts}
        # index : nomNormalisé → [ {nom, dept, lonlat} ]
        self.par_nom = {}
        for c in data:
            if not c.get("centre"):
                continue
            entree = {
                "nom": c["nom"],
                "dept": c["codeDepartement"],
                "lonlat": c["centre"]["coordinates"],
            }
            self.par_nom.setdefault(normaliser_commune(c["nom"]), []).append(entree)

    def code_dept(self, nom_dept):
        return self.dept_par_nom.get(normaliser(nom_dept))

    def chercher(self, nom_commune, code_dept=None):
        """Centroïde de la commune, avec rattrapages successifs :
        1. correspondance exacte ;
        2. la commune actuelle COMMENCE par le nom cherché (fusions :
           « Écouché » → « Écouché-les-Vallées ») ;
        3. le nom cherché COMMENCE par la commune (suffixes touristiques :
           « Moncontour-de-Bretagne » → « Moncontour ») ;
        4. la commune CONTIENT le nom cherché (« Pelvoux » → « Vallouise-Pelvoux »).
        Sans département, privilégie la métropole en cas d'homonymes."""
        cle = normaliser_commune(nom_commune)
        if len(cle) < 3:
            return None, "introuvable"

        def filtrer(liste):
            return [c for c in liste if not code_dept or c["dept"] == code_dept]

        candidates = filtrer(self.par_nom.get(cle, []))
        if not candidates:
            for test in (
                lambda nom: nom.startswith(cle),
                lambda nom: len(cle) >= 5 and cle.startswith(nom),
                lambda nom: len(cle) >= 5 and cle in nom,
            ):
                candidates = filtrer(
                    [c for nom, liste in self.par_nom.items() if test(nom) for c in liste]
                )
                if candidates:
                    break
        if not candidates:
            return None, "introuvable"
        if len(candidates) > 1:
            # Homonymes : préférer la métropole (codes ≤ 95 / 2A / 2B)
            metro = [c for c in candidates if len(c["dept"]) == 2]
            candidates = metro or candidates
            return candidates[0], "ambigu" if len(candidates) > 1 else "ok"
        return candidates[0], "ok"


# ---------------------------------------------------------------------------
# Via ferrata (CSV + fiches viaferrata-fr.net) — inchangé depuis la v2
# ---------------------------------------------------------------------------

def charger_fiches_vf():
    if not HTML_FICHES_VF.exists():
        print("! tools/viaferrata-liste.html absent : pas de liens vers les fiches")
        return []
    html = HTML_FICHES_VF.read_text(encoding="latin-1")
    fiches = []
    sections = re.split(r'href="via-ferrata-departement-\d+\.html">([^<]+)</a>', html)
    for i in range(1, len(sections) - 1, 2):
        dept = sections[i].strip()
        for m in re.finditer(
            r'<a href="(via-ferrata-\d+-[^"]+\.html)">([^<]+)</a>.*?<td>([^<]*)</td>\s*'
            r'<td align="center">([^<]*)</td>\s*<td align="center">([^<]*)</td>',
            sections[i + 1],
            re.S,
        ):
            url, nom, ville, difficulte, annee = (x.strip() for x in m.groups())
            fiches.append({
                "url": SITE_VF + url,
                "nom": nom,
                "villeNorm": normaliser(ville),
                "deptNorm": normaliser(dept),
                "difficulte": difficulte,
            })
    return fiches


def chercher_fiches(fiches, nom_csv, dept_csv):
    nom_norm = normaliser(nom_csv)
    dept_norm = normaliser(re.sub(r"^\d+\s*-\s*", "", dept_csv))
    candidates = [f for f in fiches if f["deptNorm"] == dept_norm]
    exactes = [f for f in candidates if f["villeNorm"] == nom_norm]
    if exactes:
        return exactes
    return [f for f in candidates
            if f["villeNorm"] and (f["villeNorm"] in nom_norm or nom_norm in f["villeNorm"])]


def analyser_ligne_vf(champs):
    champs = [c.strip() for c in champs]
    texte = champs[-1]
    nombres = champs[:-1]
    if len(nombres) == 2:
        lon, lat = float(nombres[0]), float(nombres[1])
    elif len(nombres) == 4:  # décimales séparées par des virgules
        lon = float(f"{nombres[0]}.{nombres[1]}")
        lat = float(f"{nombres[2]}.{nombres[3]}")
    else:
        raise ValueError(f"nombre de champs inattendu : {len(champs)}")
    return lon, lat, texte


def analyser_texte_vf(texte):
    gauche, _, droite = texte.partition(":")
    morceaux = [m.strip() for m in gauche.split(" / ")]
    if len(morceaux) >= 2 and re.match(r"^\d{1,3}\s*-", morceaux[-1]):
        departement = morceaux[-1]
        nom = " / ".join(morceaux[:-1])
    else:
        departement = ""
        nom = gauche.strip()
    parcours = [p.strip() for p in re.split(r"(?:^|\s*)-\s+", droite) if p.strip()]
    return nom, departement, parcours


def convertir_via_ferrata(fiches):
    features, erreurs = [], []
    brut = CSV_VIA_FERRATA.read_text(encoding="cp1252")
    for num, champs in enumerate(csv.reader(io.StringIO(brut)), start=1):
        if not champs or all(not c.strip() for c in champs):
            continue
        try:
            lon, lat, texte = analyser_ligne_vf(champs)
        except (ValueError, IndexError) as exc:
            erreurs.append(f"via ferrata ligne {num} : {exc}")
            continue
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            erreurs.append(f"via ferrata ligne {num} : hors France")
            continue
        nom, departement, parcours = analyser_texte_vf(texte)
        cotations = sorted(set(RE_COTATION.findall(" ".join(parcours))),
                           key=["F", "PD", "AD", "D", "TD", "ED"].index)
        correspondances = chercher_fiches(fiches, nom, departement)
        description = ""
        if departement:
            description += f"Département : {departement}\n"
        if parcours:
            description += "Parcours :\n" + "\n".join(f"* {p}" for p in parcours)
        liens = [{"label": f["nom"] + (f" ({f['difficulte']})" if f["difficulte"] else ""),
                  "url": f["url"]} for f in correspondances]
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"vf-{len(features) + 1:03d}",
                "name": f"Via ferrata de {nom}" if not nom.lower().startswith("via") else nom,
                "theme": "via-ferrata",
                "description": description.strip(),
                "link": liens[0]["url"] if len(liens) == 1 else (SITE_VF if not liens else ""),
                "links": liens if len(liens) > 1 else [],
                "photos": [],
                "details": {
                    "cotation": " à ".join(cotations) if cotations else "",
                    "parcours": str(len(parcours)) if parcours else "",
                },
            },
        })

    # Tyroliennes : lues dans le tableau d'équipements des fiches
    # viaferrata-fr.net (cache tools/vf-fiches-cache.json). Les points sans
    # fiche exploitable restent sans info (exclus du filtre « Tyrolienne »).
    urls_fiches = sorted({u for f in features
                          for u in [f["properties"]["link"]]
                          + [l["url"] for l in f["properties"]["links"]]
                          if "via-ferrata-" in u})
    infos_vf = enr.telecharger_fiches_vf(urls_fiches)
    for f in features:
        p = f["properties"]
        connus = [infos_vf[u] for u in [p["link"]] + [l["url"] for l in p["links"]]
                  if "via-ferrata-" in u
                  and infos_vf.get(u, {}).get("tyroliennes") is not None]
        if not connus:
            continue
        total = sum(i["tyroliennes"] for i in connus)
        if total:
            poulies = sorted({i["poulie"].lower() for i in connus if i["poulie"]})
            p["details"]["tyrolienne"] = f"Oui ({total})" + (
                f" — {', '.join(poulies)}" if poulies else "")
            p["details"]["tyrolienne_type"] = "oui"
        else:
            p["details"]["tyrolienne"] = "Non"
            p["details"]["tyrolienne_type"] = "non"
    return features, erreurs


# ---------------------------------------------------------------------------
# Refuges non gardés — API refuges.info (chauffage, eau, remarques…)
# Le KML fourni initialement dans Donné/Refuge est remplacé par l'API :
# mêmes points (id refuges.info identiques), données bien plus riches.
# ---------------------------------------------------------------------------

def oui_non(info):
    v = str((info or {}).get("valeur", "")).strip().lower()
    if v in ("oui", "true", "1"):
        return True
    if v in ("non", "false", "0"):
        return False
    return None  # inconnu


def convertir_refuges():
    bruts = enr.telecharger_refuges()
    features, ignores = [], 0
    for f in bruts:
        p = f["properties"]
        coord = p.get("coord", {})
        lon, lat = coord.get("long"), coord.get("lat")
        if lon is None or lat is None:
            continue
        etat = (p.get("etat") or {}).get("valeur", "") or ""
        if normaliser(etat).startswith("detruit"):
            ignores += 1
            continue

        ic = p.get("info_comp", {})
        poele = oui_non(ic.get("poele"))
        cheminee = oui_non(ic.get("cheminee"))
        if poele and cheminee:
            chauffage, chauffage_type = "Poêle et cheminée", "poele cheminee"
        elif poele:
            chauffage, chauffage_type = "Poêle à bois", "poele"
        elif cheminee:
            chauffage, chauffage_type = "Cheminée", "cheminee"
        elif poele is False and cheminee is False:
            chauffage, chauffage_type = "Aucun", "aucun"
        else:
            chauffage, chauffage_type = "", ""

        try:
            places = int(float((ic.get("places") or {}).get("nb") or 0))
        except (TypeError, ValueError):
            places = 0
        try:
            matelas = int(float((ic.get("places_matelas") or {}).get("nb") or 0))
        except (TypeError, ValueError):
            matelas = 0

        details = {"etat": etat}
        alt = coord.get("alt")
        if alt:
            details["altitude"] = f"{int(alt)} m"
            details["altitude_n"] = int(alt)
        if places:
            details["capacite"] = f"{places} place(s)" + (f" dont {matelas} matelas" if matelas else "")
            details["places_n"] = places
        if chauffage:
            details["chauffage"] = chauffage
        details["chauffage_type"] = chauffage_type
        eau = oui_non(ic.get("eau"))
        if eau is not None:
            details["eau"] = "À moins de 100 m" if eau else "Non"
        latrines = oui_non(ic.get("latrines"))
        if latrines is not None:
            details["latrines"] = "Oui" if latrines else "Non"
        couvertures = oui_non(ic.get("couvertures"))
        if couvertures is not None:
            details["couvertures"] = "Oui" if couvertures else "Non"

        morceaux = ["Cabane/refuge non gardé (source : refuges.info)."]
        remarque = ((p.get("remarque") or {}).get("valeur") or "").strip()
        if remarque:
            morceaux.append(remarque[:400] + ("…" if len(remarque) > 400 else ""))
        acces = ((p.get("acces") or {}).get("valeur") or "").strip()
        if acces:
            morceaux.append("Accès : " + acces[:300] + ("…" if len(acces) > 300 else ""))
        if etat:
            morceaux.append(f"! État : {etat}")

        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"rf-{p['id']}",
                "name": p.get("nom", "Cabane"),
                "theme": "refuge",
                "description": "\n".join(morceaux),
                "link": p.get("lien", ""),
                "photos": [],
                "details": details,
            },
        })
    print(f"Refuges : {len(features)} (détruits ignorés : {ignores})")
    return features


# ---------------------------------------------------------------------------
# Escalade (xlsx : NOM | VILLE (Dépt - NN) | TYPE | NIVEAU)
# + enrichissement corde/approche depuis le CSV « Spots_Enrichis_Verifies »
# ---------------------------------------------------------------------------

RE_VILLE = re.compile(r"^(.*?)\s*\(([^()]*?)-\s*(\d+[AB]?|\d+)\s*\)\s*$")
RE_NIVEAU = re.compile(r"Nombre de voies\s*:\s*(\d+)?\s*(?:de\s*(\S*)\s*à\s*(\S*))?", re.I)

RE_APPROCHE_TXT = re.compile(r"^(?:(\d+)\s*h\s*(\d*)|(\d+)\s*min)\b", re.I)
RE_CORDE_TXT = re.compile(r"^(2\s*x\s*)?(\d{2,3})\s*m$", re.I)
RE_COT_RANGE = re.compile(r"^(\d[abc]?\+?)\s*>\s*(\d[abc]?\+?)$", re.I)
RE_GRADE = re.compile(r"^\d[abc]\+?$", re.I)


def _minutes_approche(texte):
    """« 15 min » / « 1h15 » → minutes, ou None."""
    m = RE_APPROCHE_TXT.match(texte.strip())
    if not m:
        return None
    if m.group(3):
        return int(m.group(3))
    return int(m.group(1)) * 60 + int(m.group(2) or 0)


def _libelle_corde(valeurs, double):
    mini, maxi = min(valeurs), max(valeurs)
    prefixe = "2×" if double else ""
    return f"{prefixe}{maxi} m" if mini == maxi else f"{prefixe}{mini} à {maxi} m"


def enrichissement_escalade():
    """Lit le CSV « Spots_Enrichis_Verifies » (corde, approche, cotations).

    Le fichier est un export partiellement cassé : deux gabarits de lignes
    coexistent (colonnes Nom/Ville enrichies remplies avec unités explicites,
    ou vides avec valeurs nues décalées). On extrait par MOTIF (NN min, NNm,
    2x50m, plages x > y) — jamais par position seule.
    Retourne {nomNorm|villeNorm: {corde, corde_n, approche, approche_n,
    cotation, voies_alt}}."""
    if not CSV_ESCALADE_ENRICHI.exists():
        return {}
    infos = {}
    texte = CSV_ESCALADE_ENRICHI.read_text(encoding="utf-8-sig")
    for l in csv.reader(io.StringIO(texte), delimiter="\t"):
        if not l or not l[0].strip() or l[0].strip() == "nom":
            continue
        l = [c.strip() for c in l] + [""] * (18 - len(l))
        d = {}
        if l[7]:
            # Gabarit A : Nb | Cotations | Approche | Corde Min/Moy/Max (unités)
            mc = RE_COT_RANGE.match(l[11])
            if mc:
                d["cotation"] = f"{mc.group(1)} à {mc.group(2)}"
            minutes = _minutes_approche(l[12])
            if minutes and 0 < minutes <= 240:
                d["approche"], d["approche_n"] = l[12], minutes
            valeurs, double = [], False
            for c in (l[13], l[14], l[15]):
                m = RE_CORDE_TXT.match(c)
                if m:
                    valeurs.append(int(m.group(2)))
                    double = double or bool(m.group(1))
            valeurs = [v for v in valeurs if 15 <= v <= 200]
            if valeurs:
                d["corde"], d["corde_n"] = _libelle_corde(valeurs, double), max(valeurs)
            if l[10].isdigit() and int(l[10]) > 0:
                d["voies_alt"] = int(l[10])
        else:
            # Gabarit B : Nb | cot. min | cot. max | approche (min) | cordes (m)
            if RE_GRADE.match(l[11]) and RE_GRADE.match(l[12]):
                d["cotation"] = f"{l[11]} à {l[12]}"
            if l[13].isdigit() and 0 < int(l[13]) <= 240:
                d["approche"], d["approche_n"] = f"{int(l[13])} min", int(l[13])
            valeurs = [int(c) for c in (l[14], l[15], l[16])
                       if c.isdigit() and 15 <= int(c) <= 200]
            if valeurs:
                d["corde"], d["corde_n"] = _libelle_corde(valeurs, False), max(valeurs)
            if l[10].isdigit() and int(l[10]) > 0:
                d["voies_alt"] = int(l[10])
        if d:
            infos[f"{normaliser(l[0])}|{normaliser(l[1])}"] = d
    return infos


def convertir_escalade(communes):
    features, echecs = [], []
    enrichis = enrichissement_escalade()
    nb_enrichis = 0
    for i, ligne in enumerate(lire_xlsx(XLSX_ESCALADE)):
        if not ligne or not ligne[0]:
            continue
        nom = str(ligne[0]).strip()
        ville_brute = str(ligne[1] or "").strip()
        type_site = str(ligne[2] or "").strip()
        niveau = str(ligne[3] or "").strip()

        m = RE_VILLE.match(ville_brute)
        if not m:
            echecs.append(f"{nom} (ville illisible : {ville_brute})")
            continue
        ville, _, code_dept = (x.strip() for x in m.groups())
        code_dept = code_dept.zfill(2) if code_dept.isdigit() else code_dept
        commune, statut = communes.chercher(ville, code_dept)
        if not commune and ("-" in ville or "/" in ville):
            # « Plougasnou - Pointe de Primel » → réessaie avec le 1er segment
            commune, statut = communes.chercher(re.split(r"\s*[-/]\s*", ville)[0], code_dept)
        if not commune:
            echecs.append(f"{nom} ({ville}, {code_dept})")
            continue

        details = {}
        if type_site:
            details["type"] = type_site
        mn = RE_NIVEAU.search(niveau)
        if mn:
            if mn.group(1):
                details["voies"] = mn.group(1)
                details["voies_n"] = int(mn.group(1))
            if mn.group(2) and mn.group(3) and mn.group(2) != "à":
                details["cotation"] = f"{mn.group(2)} à {mn.group(3)}"
        # Enrichissement corde / approche (CSV fourni, couverture partielle)
        extra = enrichis.get(f"{normaliser(nom)}|{normaliser(ville)}")
        if extra:
            nb_enrichis += 1
            if "cotation" not in details and extra.get("cotation"):
                details["cotation"] = extra["cotation"]
            if "voies" not in details and extra.get("voies_alt"):
                details["voies"] = str(extra["voies_alt"])
                details["voies_n"] = extra["voies_alt"]
            for cle in ("corde", "corde_n", "approche", "approche_n"):
                if extra.get(cle) is not None:
                    details[cle] = extra[cle]
        lon, lat = commune["lonlat"]
        # Liens vers les sites communautaires qui documentent les voies
        recherche = urllib.parse.quote(nom)
        recherche_g = urllib.parse.quote(f"{nom} escalade {commune['nom']}")
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"esc-{i + 1:04d}",
                "name": nom,
                "theme": "escalade",
                "description": f"Commune : {commune['nom']} ({commune['dept']})\n\n"
                               "(Position au centre de la commune — repérez le site exact avant d'y aller.)",
                "link": "",
                "links": [
                    {"label": "Chercher sur camptocamp.org", "url": f"https://www.camptocamp.org/waypoints?q={recherche}"},
                    {"label": "Chercher les topos (Google)", "url": f"https://www.google.com/search?q={recherche_g}"},
                ],
                "photos": [],
                "details": details,
            },
        })
    print(f"Escalade : {len(features)} (échecs géocodage : {len(echecs)}, "
          f"enrichis corde/approche : {nb_enrichis})")
    return features, echecs


# ---------------------------------------------------------------------------
# Châteaux (xlsx : « Château de X à Commune dans le Dépt » et variantes)
# ---------------------------------------------------------------------------

def analyser_chateau(texte):
    """Retourne (commune, nomDept) ou (None, None)."""
    t = texte.strip().rstrip(".")
    # Département : après le dernier « dans » ou « en »
    m = re.search(r"\s(?:dans|en)\s+(?:l['e]s?\s*|la\s+|le\s+)?([^,]+)$", t)
    if not m:
        # Pas de département (« Bazouges à Bazouges-sur-le-Loir »)
        m2 = re.search(r"\s(?:à|au|aux)\s+([^,]+)$", t)
        if m2:
            commune = m2.group(1).strip()
            if re.search(r"\sau\s+[^,]+$", t):
                commune = "Le " + commune
            elif re.search(r"\saux\s+[^,]+$", t):
                commune = "Les " + commune
            return commune, None
        return None, None
    dept = m.group(1).strip()
    gauche = t[: m.start()].strip().rstrip(",")
    # Commune : après le dernier « à / au / aux »
    m2 = re.search(r"\s(?:à|au|aux)\s+([^,]+)$", gauche)
    if m2:
        commune = m2.group(1).strip()
        if re.search(r"\sau\s+[^,]+$", gauche):
            commune = "Le " + commune
        elif re.search(r"\saux\s+[^,]+$", gauche):
            commune = "Les " + commune
    else:
        # « Loubressac en Dordogne » : le nom EST la commune
        commune = re.sub(r"^(château|chateau|manoir|fort|citadelle|palais|abbaye|tour)\s+(de la|de l'|des|du|de|d')\s*",
                         "", gauche, flags=re.I).strip()
    return commune, dept


def convertir_chateaux(communes):
    features, echecs = [], []
    entrees_wiki = []  # (feature, texte original) pour l'enrichissement Wikipédia
    vus = set()
    for i, ligne in enumerate(lire_xlsx(XLSX_CHATEAUX)):
        if not ligne or not ligne[0]:
            continue
        texte = str(ligne[0]).strip()
        if not texte or texte.lower() in vus:
            continue
        vus.add(texte.lower())
        commune_nom, dept_nom = analyser_chateau(texte)
        if not commune_nom:
            echecs.append(texte)
            continue
        code = communes.code_dept(dept_nom) if dept_nom else None
        commune, statut = communes.chercher(commune_nom, code)
        if not commune and code:
            commune, statut = communes.chercher(commune_nom)  # repli sans dept
        if not commune:
            echecs.append(texte)
            continue
        nom = texte if texte.lower().startswith(("château", "chateau", "fort", "manoir", "citadelle")) \
            else f"Château {texte}" if " à " not in texte and " dans " in texte else texte
        lon, lat = commune["lonlat"]
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"ch-{i + 1:04d}",
                "name": nom,
                "theme": "chateau",
                "description": f"Commune : {commune['nom']} ({commune['dept']})\n\n"
                               "(Position au centre de la commune.)",
                "link": "",
                "photos": [],
                "details": {},
            },
        }
        features.append(feature)
        entrees_wiki.append((feature, texte))
    print(f"Châteaux : {len(features)} (échecs : {len(echecs)})")
    enr.enrichir_chateaux(entrees_wiki)
    # Une seule catégorie Château (v45) : le champ details.fiche distingue les
    # châteaux documentés (photo + page Wikipédia) de ceux restant à confirmer.
    # Il alimente le filtre déclaratif « Fiche » de js/config/themes.js.
    non_confirmes = 0
    for feature in features:
        p = feature["properties"]
        complet = bool(p.get("photos")) and bool(p.get("link"))
        p["details"]["fiche"] = "Référencé" if complet else "À vérifier"
        if not p["link"]:
            p["description"] += (
                "\n\n! Existence non confirmée : aucune page Wikipédia trouvée "
                "pour ce château (nom approximatif ou site disparu possible)."
            )
            non_confirmes += 1
    print(f"  châteaux sans page Wikipédia -> fiche « À vérifier » : {non_confirmes}")
    return features, echecs


# ---------------------------------------------------------------------------
# Cités de caractère (xlsx : noms de communes)
# ---------------------------------------------------------------------------

def convertir_cites(communes):
    features, echecs, ambigus = [], [], 0
    entrees_wiki = []  # (feature, nomXlsx, nomCommune, nomDept)
    vus = set()
    for i, ligne in enumerate(lire_xlsx(XLSX_CITES)):
        if not ligne or not ligne[0]:
            continue
        nom = str(ligne[0]).strip()
        if not nom or normaliser(nom) in vus:
            continue
        vus.add(normaliser(nom))
        commune, statut = communes.chercher(nom)
        if not commune:
            echecs.append(nom)
            continue
        if statut == "ambigu":
            ambigus += 1
        lon, lat = commune["lonlat"]
        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"cc-{i + 1:03d}",
                "name": nom,
                "theme": "cite-caractere",
                "description": f"Village / cité de caractère.\nCommune : {commune['nom']} ({commune['dept']})",
                "link": "",
                "photos": [],
                "details": {},
            },
        }
        features.append(feature)
        entrees_wiki.append((feature, nom, commune["nom"],
                             communes.nom_par_code.get(commune["dept"], "")))
    print(f"Cités de caractère : {len(features)} (échecs : {len(echecs)}, homonymes ambigus : {ambigus})")
    enr.enrichir_cites(entrees_wiki)
    return features, echecs


# ---------------------------------------------------------------------------
# Grottes et cathédrales : catégories Wikipédia géolocalisées
# (le xlsx cathédrales ne contient que des noms sans ville — inutilisable ;
# les catégories Wikipédia donnent coordonnées exactes + lien + photo)
# ---------------------------------------------------------------------------

def convertir_wikipedia(nom_cache, racine, mot_souscat, theme, prefixe_id, description):
    infos = enr.recolter_categorie_wikipedia(nom_cache, racine, mot_souscat)
    features, vus = [], set()
    sans_coord = 0
    for page in sorted(infos, key=lambda p: p["titre"]):
        titre = page["titre"]
        # Écarte les doublons et les articles-listes (« Liste des grottes… »)
        if not titre or titre in vus or titre.lower().startswith("liste"):
            continue
        vus.add(titre)
        lat, lon = page["lat"], page["lon"]
        if lat is None or lon is None:
            sans_coord += 1
            continue
        if not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            continue  # hors métropole (Corse incluse dans la bbox)
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"{prefixe_id}-{len(features) + 1:04d}",
                "name": titre,
                "theme": theme,
                "description": description,
                "link": page["url"],
                "photos": [page["thumb"]] if page["thumb"] else [],
                "details": {},
            },
        })
    print(f"{theme} : {len(features)} (articles sans coordonnées ignorés : {sans_coord})")
    return features


def convertir_grottes():
    return convertir_wikipedia(
        "wiki-grottes.json", "Catégorie:Grotte en France", "grotte",
        "grotte", "grot",
        "Grotte référencée sur Wikipédia (voir la fiche pour l'accès et "
        "les conditions de visite).")


def convertir_cathedrales():
    return convertir_wikipedia(
        "wiki-cathedrales.json", "Catégorie:Cathédrale en France", "cathedrale",
        "cathedrale", "cath",
        "Cathédrale référencée sur Wikipédia.")


# ---------------------------------------------------------------------------
# GR (KML volumineux → GeoJSON simplifié) — inchangé depuis la v2
# ---------------------------------------------------------------------------

def douglas_peucker(points, tolerance):
    if len(points) < 3:
        return points
    garder = [False] * len(points)
    garder[0] = garder[-1] = True
    pile = [(0, len(points) - 1)]
    while pile:
        debut, fin = pile.pop()
        x1, y1 = points[debut]
        x2, y2 = points[fin]
        dx, dy = x2 - x1, y2 - y1
        norme2 = dx * dx + dy * dy
        dist_max, indice = 0.0, -1
        for i in range(debut + 1, fin):
            x0, y0 = points[i]
            if norme2 == 0:
                d2 = (x0 - x1) ** 2 + (y0 - y1) ** 2
            else:
                t = max(0.0, min(1.0, ((x0 - x1) * dx + (y0 - y1) * dy) / norme2))
                d2 = (x0 - x1 - t * dx) ** 2 + (y0 - y1 - t * dy) ** 2
            if d2 > dist_max:
                dist_max, indice = d2, i
        if dist_max > tolerance * tolerance:
            garder[indice] = True
            pile.append((debut, indice))
            pile.append((indice, fin))
    return [p for p, g in zip(points, garder) if g]


def convertir_gr(tolerance=0.0008):
    data = KML_GR.read_text(encoding="utf-8")
    features = []
    for pm in re.finditer(r"<Placemark>(.*?)</Placemark>", data, re.S):
        bloc = pm.group(1)
        nom = re.search(r"<name>(.*?)</name>", bloc, re.S)
        coords = re.search(r"<coordinates>(.*?)</coordinates>", bloc, re.S)
        if not nom or not coords:
            continue
        nom = re.sub(r"<!\[CDATA\[|\]\]>", "", nom.group(1)).replace("®", "").strip()
        nom = re.sub(r"\s*\(\d{4}.?gr-infos\.com\)\s*$", "", nom)
        # Lien gr-infos : href, ou URL en clair dans la description
        lien = re.search(r'href="(https?://www\.gr-infos\.com[^"]*)"', bloc) \
            or re.search(r"(https?://www\.gr-infos\.com/\S+?)(?=[\s\"'<])", bloc)
        points = []
        for triplet in coords.group(1).split():
            morceaux = triplet.split(",")
            if len(morceaux) >= 2:
                points.append((round(float(morceaux[0]), 5), round(float(morceaux[1]), 5)))
        if len(points) < 2:
            continue
        simplifie = douglas_peucker(points, tolerance)
        numero = re.match(r"GR\s?(\d+)\b", nom)
        features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": [[p[0], p[1]] for p in simplifie]},
            "properties": {
                "name": nom,
                "num": int(numero.group(1)) if numero else None,
                "link": lien.group(1) if lien else "",
            },
        })

    # Enrichissements : distance calculée, D+ estimé (IGN), liens gr-go + Wikipédia
    grgo = enr.liens_grgo()
    wiki = enr.liens_wikipedia_gr([f["properties"]["num"] for f in features if f["properties"]["num"]])
    print("  altimétrie IGN (D+ estimé, mis en cache)…")
    for f in features:
        p = f["properties"]
        coords = f["geometry"]["coordinates"]
        p["distance_km"] = round(enr.distance_km(coords), 1)
        p["dplus"] = enr.denivele_gr(p["name"], coords)
        if p["num"] in grgo:
            p["grgo"] = grgo[p["num"]]
        if p["num"] in wiki:
            p["wiki"] = wiki[p["num"]]
        del p["num"]
    avec_grgo = sum(1 for f in features if f["properties"].get("grgo"))
    avec_wiki = sum(1 for f in features if f["properties"].get("wiki"))
    print(f"GR : {len(features)} tracés (gr-go : {avec_grgo}, Wikipédia : {avec_wiki})")
    return features


# ---------------------------------------------------------------------------
# Toilettes publiques (OpenStreetMap/Overpass) → data/toilettes.geojson
# Fichier SÉPARÉ, volumineux : chargé à la demande par l'application,
# non pré-caché par le service worker (comme gr.geojson).
# ---------------------------------------------------------------------------

RE_JOUR_OSM = re.compile(r"\b(Mo|Tu|We|Th|Fr|Sa|Su|PH)\b")
TRAD_JOURS = {"Mo": "lun", "Tu": "mar", "We": "mer", "Th": "jeu",
              "Fr": "ven", "Sa": "sam", "Su": "dim", "PH": "fériés"}


def horaires_fr(valeur):
    """Syntaxe opening_hours OSM → libellé lisible (Mo-Fr → lun-ven…)."""
    v = valeur.strip()
    if v == "24/7":
        return "24 h/24, 7 j/7"
    if v == "off":
        return "Fermées actuellement"
    v = RE_JOUR_OSM.sub(lambda m: TRAD_JOURS[m.group(1)], v)
    v = (v.replace("sunrise", "lever du soleil").replace("sunset", "coucher du soleil")
         .replace(" off", " fermé").replace(";", " · "))
    return v[:100]


def convertir_toilettes():
    elements = enr.telecharger_toilettes()
    features, prives = [], 0
    for e in sorted(elements, key=lambda x: (x["type"], x["id"])):
        tags = e.get("tags") or {}
        if tags.get("amenity") != "toilets":
            continue
        if tags.get("access") in ("private", "no"):
            prives += 1
            continue
        lat = e.get("lat") or (e.get("center") or {}).get("lat")
        lon = e.get("lon") or (e.get("center") or {}).get("lon")
        if lat is None or lon is None or not (LAT_MIN <= lat <= LAT_MAX and LON_MIN <= lon <= LON_MAX):
            continue
        details = {}
        fee = tags.get("fee")
        if fee == "yes":
            details["tarif"] = "Payant"
        elif fee == "no":
            details["tarif"] = "Gratuit"
        pmr = tags.get("wheelchair")
        if pmr == "yes":
            details["accessibilite"], details["pmr_type"] = "PMR", "oui"
        elif pmr == "limited":
            details["accessibilite"], details["pmr_type"] = "PMR (accès limité)", "oui"
        elif pmr == "no":
            details["accessibilite"], details["pmr_type"] = "Non accessible PMR", "non"
        if tags.get("access") == "customers":
            details["acces"] = "Réservées à la clientèle"
        if tags.get("changing_table") == "yes":
            details["equipement"] = "Table à langer"
        if tags.get("opening_hours"):
            details["horaires"] = horaires_fr(tags["opening_hours"])
        # Propriétés minimales (description/link/photos omis) : le fichier
        # reste aussi léger que possible pour ~30-60 000 points
        features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
            "properties": {
                "id": f"wc-{e['type'][0]}{e['id']}",
                "name": tags.get("name") or "Toilettes publiques",
                "theme": "toilettes",
                "details": details,
            },
        })
    CIBLE_TOILETTES.write_text(
        json.dumps({"type": "FeatureCollection", "features": features},
                   ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8")
    print(f"Toilettes : {len(features)} (privées écartées : {prives}) -> "
          f"toilettes.geojson {CIBLE_TOILETTES.stat().st_size // 1024} Ko")
    return features


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    communes = Communes()
    fiches = charger_fiches_vf()

    via_ferrata, erreurs_vf = convertir_via_ferrata(fiches)
    print(f"Via ferrata : {len(via_ferrata)}")
    refuges = convertir_refuges()
    escalade, echecs_esc = convertir_escalade(communes)
    chateaux, echecs_ch = convertir_chateaux(communes)
    cites, echecs_cc = convertir_cites(communes)
    grottes = convertir_grottes()
    cathedrales = convertir_cathedrales()
    convertir_toilettes()  # fichier séparé data/toilettes.geojson

    # Cascades (OSM/Overpass + Wikipédia) : ids casc-… préservés d'une
    # exécution à l'autre (lus dans l'ancien points.geojson AVANT réécriture) ;
    # les doublons complètent les points des autres catégories (fusion).
    autres = via_ferrata + refuges + escalade + chateaux + cites + grottes + cathedrales
    cascades, _ = recolter_cascades.convertir_cascades(autres)
    print(f"Cascades : {len(cascades)}")

    # Lacs (Wikipédia + Wikidata + OSM) : même logique, ids lac-… préservés ;
    # les doublons complètent les points des autres catégories (fusion).
    lacs, _, _ = recolter_lacs.convertir_lacs(autres + cascades)
    print(f"Lacs : {len(lacs)}")

    collection = {"type": "FeatureCollection",
                  "features": autres + cascades + lacs}
    CIBLE_POINTS.write_text(json.dumps(collection, ensure_ascii=False, separators=(",", ":")),
                            encoding="utf-8")
    print(f"\npoints.geojson : {len(collection['features'])} features, "
          f"{CIBLE_POINTS.stat().st_size // 1024} Ko")

    gr = convertir_gr()
    CIBLE_GR.write_text(json.dumps({"type": "FeatureCollection", "features": gr},
                                   ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
    print(f"gr.geojson : {CIBLE_GR.stat().st_size // 1024} Ko")

    for titre, liste in [("via ferrata", erreurs_vf), ("escalade", echecs_esc),
                         ("châteaux", echecs_ch), ("cités", echecs_cc)]:
        if liste:
            print(f"\nNon convertis ({titre}) : {len(liste)}")
            for e in liste[:10]:
                print(f"  - {e}")
            if len(liste) > 10:
                print(f"  … et {len(liste) - 10} autres")
    return 0


if __name__ == "__main__":
    sys.exit(main())
