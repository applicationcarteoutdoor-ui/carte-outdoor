# -*- coding: utf-8 -*-
"""
Récolte les FICHES des sites spécialisés de via ferrata, pour lier chaque
via ferrata CH/IT/ES à SA page détaillée (demande utilisateur v67) :

  - IT : ferrate365.it  — sitemap /vie-ferrate/ (~448 fiches), chaque page
         porte titre + coordonnées GPS (lien « Indicazioni Stradali »)
  - ES : deandar.com    — KML de la carte (322 fiches : nom, lien, K, GPS)
  - CH : myferrata.ch   — sitemap (~37 fiches), titre seulement (pas de GPS)

On n'extrait QUE nom / URL / coordonnées / cotation K (FAITS, pour
l'appariement et le lien) — jamais les topos/descriptions/photos (droits).

Sortie : tools/vf-sites-<iso>.json  [{nom, url, lat?, lon?, k?}]
Caches : tools/f365-cache/<slug>.html (gitignoré), reprise sur relance.

Lancer :  python tools/recolter_vf_sites.py [it|es|ch]
"""

import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

DOSSIER = Path(__file__).resolve().parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; SpotMap/1.0; contact bidband4@gmail.com)"}


def _get(url, binaire=False):
    req = urllib.request.Request(url, headers=UA)
    for attente in (0, 20, 60):
        if attente:
            time.sleep(attente)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                raw = r.read()
                return raw if binaire else raw.decode("utf-8", "replace")
        except Exception as e:
            print(f"    (réseau {url[:60]} : {e})", flush=True)
    return None


def italie():
    """ferrate365.it : sitemap -> chaque fiche -> titre + GPS."""
    sm = _get("https://www.ferrate365.it/job_listing-sitemap.xml")
    slugs = sorted(set(
        u.rstrip("/").rsplit("/", 1)[1]
        for u in re.findall(r"<loc>([^<]+)</loc>", sm or "")
        if "/vie-ferrate/" in u and "/en/" not in u))
    print(f"it: {len(slugs)} fiches ferrate365 à lire", flush=True)
    cache_dir = DOSSIER / "f365-cache"
    cache_dir.mkdir(exist_ok=True)
    fiches = []
    for n, slug in enumerate(slugs, 1):
        fc = cache_dir / f"{slug}.html"
        if fc.exists():
            x = fc.read_text(encoding="utf-8", errors="replace")
        else:
            x = _get(f"https://www.ferrate365.it/vie-ferrate/{slug}/")
            if x is None:
                continue
            fc.write_text(x, encoding="utf-8")
            time.sleep(1.2)
        titre = re.search(r"<title>(.*?)</title>", x, re.S)
        titre = html.unescape(titre.group(1).strip()) if titre else slug
        titre = re.sub(r"\s*[-|–]\s*Ferrate365.*$", "", titre, flags=re.I).strip()
        m = re.search(r"daddr=(-?\d+\.\d+)%2C\+?(-?\d+\.\d+)", x)
        fiche = {"nom": titre, "url": f"https://www.ferrate365.it/vie-ferrate/{slug}/"}
        if m:
            fiche["lat"], fiche["lon"] = float(m.group(1)), float(m.group(2))
        fiches.append(fiche)
        if n % 50 == 0:
            print(f"  it {n}/{len(slugs)}", flush=True)
    return fiches


def espagne():
    """deandar.com : KML de la carte (nom | lien | K | GPS), windows-1252."""
    page = _get("https://deandar.com/ferratas/todas/Espa%C3%B1a")
    loc = urllib.parse.unquote(urllib.parse.unquote(
        re.search(r'resource_loc=([^&"]+)', page).group(1)))
    raw = _get("https://deandar.com" + loc, binaire=True)
    try:                                   # l'encodage du serveur varie !
        t = raw.decode("utf-8")
    except UnicodeDecodeError:
        t = raw.decode("windows-1252", "replace")
    fiches = []
    for pm in re.findall(r"<Placemark>(.*?)</Placemark>", t, re.S):
        lien = re.search(r'href="(?:https?:)?(//deandar\.com/ferratas/[^"]+)"', pm)
        coords = re.search(r"<coordinates>\s*(-?[\d.]+),(-?[\d.]+)", pm)
        titre = re.search(r'class="titol_mapa"[^>]*>(.*?)</a>', pm, re.S)
        if not (lien and coords and titre):
            continue
        brut = html.unescape(re.sub(r"<[^>]+>", " ", titre.group(1)))
        k = re.search(r"\[K(\d)\]", brut)
        nom = re.sub(r"\[K\d\]", "", brut).strip()
        fiche = {"nom": nom, "url": "https:" + lien.group(1),
                 "lat": float(coords.group(2)), "lon": float(coords.group(1))}
        if k:
            fiche["k"] = f"K{k.group(1)}"
        fiches.append(fiche)
    print(f"es: {len(fiches)} fiches deandar", flush=True)
    return fiches


def suisse():
    """myferrata.ch : sitemap plat -> fiches (titre, pas de GPS)."""
    sm = _get("https://www.myferrata.ch/sitemap.xml")
    urls = re.findall(r"<loc>([^<]+)</loc>", sm or "")
    hors = ("news", "oeffnungszeiten", "klettersteige", "kontakt", "impressum",
            "datenschutz", "links", "shop", "ueber", "klettersteig-urlaub",
            "tipps", "vorbereitung-ausruestung", "produkttests")
    pages = [u for u in urls if u.count("/") == 4 and u.endswith("/")
             and not any(s in u for s in hors) and u != "https://www.myferrata.ch/"]
    print(f"ch: {len(pages)} fiches myferrata à lire", flush=True)
    fiches = []
    for u in pages:
        x = _get(u)
        if not x:
            continue
        titre = re.search(r"<title>(.*?)</title>", x, re.S)
        titre = html.unescape(titre.group(1).strip()) if titre else u
        titre = re.sub(r"\s*-\s*my ferrata.*$", "", titre, flags=re.I)
        titre = re.sub(r",\s*\d+\s*m\s*$", "", titre).strip()  # « , 1723m »
        fiches.append({"nom": titre, "url": u})
        time.sleep(5)  # Crawl-Delay: 5 demandé par leur robots.txt
    return fiches


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cibles = [a for a in sys.argv[1:] if a in ("it", "es", "ch")] or ["it", "es", "ch"]
    for iso, fn in (("it", italie), ("es", espagne), ("ch", suisse)):
        if iso not in cibles:
            continue
        fiches = fn()
        (DOSSIER / f"vf-sites-{iso}.json").write_text(
            json.dumps(fiches, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"{iso}: {len(fiches)} fiches -> tools/vf-sites-{iso}.json", flush=True)
