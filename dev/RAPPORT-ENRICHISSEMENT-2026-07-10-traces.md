# Rapport d'enrichissement — Tracés et liens des randonnées (pilote Chartreuse)

**Date** : 2026-07-10 · **Script** : `tools/recolter_traces_randos.py` · **Sorties** : `data/randos.geojson` (remplacé — le tracé d'essai `source: "test"` a disparu), `data/points.geojson` (champ `properties.links` des 13 points rando uniquement).

## Méthode (volet 1 — tracés)

Il n'existe pas de relation OSM `route=hiking` par voie normale (1 seule des 13 en avait une : « Le sommet du Mont Granier »). Les tracés sont donc **calculés par routage sur le réseau de sentiers réel d'OpenStreetMap** :

1. **Départ classique** (`details.depart` du point) résolu en coordonnées par requête Overpass sur son nom (col, hameau, parking) autour du sommet — priorité aux nœuds `natural=saddle` / `mountain_pass` / `place` pour écarter arrêts de bus et homonymes ;
2. **Réseau piéton** de la boîte départ–sommet (marge 0,025°) téléchargé via `way["highway"](bbox); out geom;`, filtré côté client (path/footway/track/steps… + petites routes) ;
3. **Plus court chemin** (Dijkstra) départ → sommet, pondéré : sentiers ×1, routes ×3–6, `sac_scale` alpin (T4+) ×8–30, **via ferrata et `access=private|no` exclus** (Roche Veyrand a une VF en face ouest — jamais empruntée) ;
4. **Simplification Douglas-Peucker** (helper réutilisé de `build_data.py`) tolérance 0,0001° ≈ 10 m, coordonnées arrondies à 5 décimales ;
5. **Contrôle des extrémités** : tracé refusé si à plus de 300 m du départ résolu ou du sommet.

**Cas particulier** : Cirque de Saint-Même = boucle sans sommet ; le point Wikipédia est à ~100 m du parking (le routage donnait 100 m de trait). Sa géométrie vient de la **relation OSM dédiée 15927441 « Sentier des Cascades »** (boucle des 4 cascades, position vérifiée dans le cirque, passe à 7 m du parking résolu).

**Honnêteté** : chaque segment est un chemin cartographié dans OSM ; l'itinéraire retenu est le plus court balisé, qui peut différer d'une variante éditoriale (ex. Dent de Crolles : montée ET descente par le pas de l'Œille, pas la boucle par le Trou du Glaz décrite dans la fiche).

## Résultats : 13 tracés / 13 randonnées

| Id | Randonnée | Longueur | Départ résolu (OSM) | Bouts (départ / sommet) | Points (avant → après DP) |
|---|---|---|---|---|---|
| rando-0001 | Chamechaude | 3,1 km | Col de Porte | 0 m / 5 m | 367 → 42 |
| rando-0002 | Charmant Som | 1,1 km | Auberge du Charmant Som | 10 m / 7 m | 102 → 13 |
| rando-0003 | Cirque de Saint-Même | 2,8 km (boucle) | parking du cirque | passe à 7 m | 192 → 43 |
| rando-0004 | Dent de Crolles | 3,8 km | Col du Coq | 0 m / 12 m | 496 → 58 |
| rando-0005 | Dôme de Bellefont | 6,0 km | Perquelin | 9 m / 13 m | 441 → 91 |
| rando-0006 | Grande Sure | 4,7 km | Col de la Charmette | 0 m / 4 m | 309 → 67 |
| rando-0007 | Grand Som | 5,3 km | La Correrie | 7 m / 9 m | 405 → 80 |
| rando-0008 | Lances de Malissard | 6,1 km | Perquelin | 9 m / 17 m | 366 → 72 |
| rando-0009 | La Pinéa | 3,6 km | Col de Porte | 0 m / 8 m | 352 → 45 |
| rando-0010 | Mont Granier | 4,4 km | La Plagne | 11 m / 14 m | 293 → 60 |
| rando-0011 | Mont Outheran | 3,4 km | Le Désert d'Entremont | 21 m / 4 m | 235 → 41 |
| rando-0012 | Mont Saint-Eynard | 7,1 km | Col de Vence | 0 m / 20 m | 485 → 62 |
| rando-0013 | Roche Veyrand | 2,8 km | Saint-Pierre-d'Entremont | 5 m / 9 m | 294 → 47 |

Longueurs = aller simple (boucle complète pour Saint-Même). **`data/randos.geojson` : 15 Ko** (objectif < 500 Ko), 13 features LineString, `properties = {rando, name, source: "OSM"}`.

Deux échecs de première passe, corrigés : rando-0004 (Overpass 429 persistant → repris sur cache), rando-0012 (« Col de Vence » à 4,6 km du sommet, hors du rayon de 4 km initial → rayon porté à 6 km).

## Volet 2 — liens

Chaque point rando a reçu `properties.links` : 3 recherches Google restreintes par site (modèle éprouvé des sites d'escalade — pas d'URL profonde devinée) : `🥾 Komoot` (`site:komoot.fr`), `⛰️ Altitude Rando` (`site:altituderando.com`), `🗺️ AllTrails` (`site:alltrails.com`), requête `<nom> Chartreuse` URL-encodée (le massif vient de `details.massif` → extensible).

## Vérifications effectuées

- Assertions Python : chaque trace référence un id rando existant ; toutes les coordonnées `[lon, lat]` dans la bbox Chartreuse (45,15–45,55 / 5,55–6,05 — aucune inversion lon/lat) ; témoins Chamechaude et Dent de Crolles : début à 0 m du col, fin à 5 m / 12 m du sommet (< 300 m exigés) ; taille < 500 Ko ; 3 liens conformes sur chacun des 13 points.
- Navigateur (port 8128, SW purgé) : ouverture de la fiche Chamechaude → `montrerTraceRando('rando-0001')` renvoie `true`, tracé dessiné depuis le nouveau fichier ; la fiche affiche bien les 3 liens de recherche à côté du lien Wikipédia. État nettoyé ensuite.

## Limites connues

- **Plus court chemin ≠ variante éditoriale** : l'aller et le retour sont identiques (pas de boucles Trou du Glaz, col de la Sure…) ; c'est la voie normale « montée » dans la quasi-totalité des cas.
- Le tracé s'arrête au dernier nœud du réseau OSM proche du sommet (4 à 20 m) — les tout derniers mètres hors sentier ne sont pas dessinés.
- Qualité tributaire d'OSM : un sentier retagué ou coupé (`access=private`) changerait le résultat à la prochaine récolte ; le cache `tools/traces-randos-osm.json` (gitignoré) fige la récolte du jour.
- Overpass rate-limite fort (429 par vagues) : la récolte complète a demandé des pauses de 20–120 s ; le cache par randonnée permet la reprise.
- `data/randos.geojson` n'est **pas pré-caché** par le service worker (chargé à la demande) : aucun bump de `VERSION` requis pour ce fichier seul — non touché, conformément à la consigne.

## Reste à faire (hors périmètre de cette passe)

- Étendre `DEPARTS` quand de nouvelles randonnées seront ajoutées (le script signale « pas d'entrée DEPARTS »).
- Éventuellement dessiner les boucles complètes (descente différente) quand une relation OSM dédiée existe.
