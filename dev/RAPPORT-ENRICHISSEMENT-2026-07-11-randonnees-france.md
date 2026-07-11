# Rapport d'enrichissement — Randonnées France entière (2026-07-10 → 11)

Extension de la catégorie `randonnee` (pilote Chartreuse, rando-0001…0013)
à tous les grands massifs de France. **Rapport écrit au fil de l'eau** :
chaque massif est intégré séquentiellement (points → tracés → statistiques).

## Méthode (identique au pilote, industrialisée)

1. **Listes éditoriales par massif** (`tools/randos_liste_*.py`) : sommets
   majeurs à voie normale de randonnée documentée + objectifs célèbres
   (cirques, cols historiques). Sélection qualitative : article Wikipédia
   OBLIGATOIRE (notoriété), sommets d'alpinisme/escalade écartés d'office
   (Mont Aiguille, Grande Casse, Pierra Menta, pic du Midi d'Ossau…), sommets
   à route carrossable écartés (Revard, Bonette…), objectifs homonymes d'un
   point existant écartés (lacs déjà en catégorie `lac` : Gaube, Ayous,
   Lauzanier… ; cirque de Navacelles = cascade déjà en base).
2. **Validation Wikipédia** (`tools/recolter_randonnees_france.py`) :
   coordonnées du sommet, photo (upload.wikimedia.org seulement), résumé,
   altitude croisée avec l'article (corrigée quand l'article contredit la
   valeur éditoriale), bbox par massif. Ids stables `rando-NNNN` (registre
   `tools/randos-registre.json` : un id n'est JAMAIS réutilisé), convention
   `details.fiche` = « Référencée » (photo + résumé) / « À vérifier ».
3. **Tracés par routage OSM** (`tools/recolter_traces_randos.py`, adapté) :
   départ classique résolu par nom dans OSM (cols > lieux-dits > parkings),
   réseau piéton Overpass de la boîte départ-sommet, Dijkstra pondéré
   (sentiers favorisés, routes pénalisées, T4+ très pénalisé, via ferrata et
   privé EXCLUS), Douglas-Peucker ~10 m, extrémités contrôlées (< 300 m).
   **Règle : pas de randonnée sans tracé** — routage impossible = point retiré
   (`tools/retirer_randos.py`), id gelé au registre. Cache shardé par rando
   (`tools/traces-cache/`), randos.geojson réécrit après CHAQUE tracé.
4. **Statistiques** (`tools/completer_stats_randos.py`) : distance mesurée du
   tracé (aller/boucle), dénivelé IGN si non éditorial, durée estimée
   (4 km/h + 300 m/h). Relancé après chaque massif — objectif : 0 « sans tracé ».
5. **Liens** : chaque point porte `properties.links` = 3 recherches ciblées
   (🥾 Komoot, ⛰️ Altitude Rando, 🗺️ AllTrails), même modèle que le pilote.
6. `js/config/themes.js` : chaque massif ajouté en option du filtre « Massif »
   (APPEND uniquement, valeurs = `details.massif` exactes).

## Compteurs par massif

| Massif | Candidates | Validées Wikipédia | Tracées & intégrées |
|---|---|---|---|
| Chartreuse (pilote, rappel) | 15 | 13 | 13 |
| **Groupe 1 — Alpes du Nord (intégré le 10/07)** | | | |
| Vercors | 6 | 5 | 5 |
| Belledonne | 6 | 5 | 5 |
| Bauges | 7 | 7 | 7 |
| Aravis-Bornes | 8 | 7 | 7 |
| Beaufortain | 6 | 5 | 5 |
| Vanoise | 5 | 4 | 4 |
| Mont-Blanc | 7 | 4 | 4 |
| **Groupe 2 — Alpes du Sud et Provence (intégré le 11/07)** | | | |
| Écrins | 5 | 4 | 4 |
| Dévoluy | 3 | 3 | 3 |
| Queyras | 5 | 4 | 4 |
| Ubaye | 3 | 2 | 2 |
| Mercantour | 5 | 5 | 5 |
| Verdon | 3 | 2 | 2 |
| Provence | 5 | 5 | 5 |
| **Groupe 3 — Pyrénées (intégré le 11/07)** | | | |
| Pays basque-Béarn | 6 | 5 | 5 |
| Bigorre | 5 | 4 | 4 |
| Luchonnais | 3 | 3 | 3 |
| Ariège | 6 | 6 | 6 |
| Pyrénées-Orientales | 5 | 5 | 5 |
| **Groupe 4 — Jura, Vosges, Massif central (intégré le 11/07)** | | | |
| Jura | 7 | 7 | 7 |
| Vosges | 8 | 8 | 8 |
| Sancy | 3 | 3 | 3 |
| Chaîne des Puys | 2 | 2 | 2 |
| Cantal | 5 | 5 | 5 |
| Cévennes | 3 | 2 | 2 |
| Mézenc | 2 | 2 | 2 |
| **Groupe 5 — Corse (intégré le 11/07)** | | | |
| Corse | 9 | 9 | 8 |
| **TOTAL catégorie** | **≈ 152** | **136** | **135** |

## Écartées (détail)

**Au fil des groupes 2-5** : Pic du Mas de la Grave, Tête du Pelvas, Tête de
Louis XVI, Cadières de Brandis, Pic de Cabaliros, Pic Cassini (pas d'article
Wikipédia dédié ou sans coordonnées) ; Capu Rossu (géolocalisation Wikipédia
inexploitable, routage refusé). Récupérées par titre exact : Mont Charvin
(« Mont Charvin (chaîne des Aravis) »), Pic d'Iparla (« Iparla »), Pic de
Madrès, Mont d'Or (« Mont d'Or (Doubs) »), Sainte-Victoire (point au pic des
Mouches) ; Bric Froid ajouté en remplacement du Pelvas.

### Détail groupe 1

- **Sans article Wikipédia dédié** (filtre de notoriété) : Grand Colon,
  Trou de la Mouche, Roc du Vent, Aiguillette des Posettes.
- **Article sans coordonnées** : Glandasse, Petit Mont Blanc (Vanoise).
- **Homonymie trompeuse** : La Jonction (l'article décrit le confluent
  Rhône-Arve à Genève, pas le site de Chamonix).
- **Corrections de routage** (départs OSM introuvables, réglés puis tracés) :
  Pic Saint-Michel (départ déplacé à Lans-en-Vercors), Roc Cornafion
  (Villard-de-Lans), Pointe de la Galoppaz (col de la Buffaz), Mont Charvin
  (nom OSM « Le Bouchet-Mont-Charvin »), Trélod (bbox élargie : réseaux
  disjoints dans la petite boîte), Le Brévent (429 Overpass, retenté).

## Sources

- **Wikipédia fr** (API `action=query`, `prop=coordinates|pageimages|extracts`,
  `colimit=max` + suivi de `continue`) : coordonnées, photos, résumés, liens.
- **OpenStreetMap via Overpass** (réseau de sentiers, résolution des départs,
  © contributeurs OSM, ODbL) : tracés calculés sur le réseau réel.
- **IGN** (`data.geopf.fr/altimetrie`) : dénivelés estimés le long des tracés.
- Altitudes croisées éditorial ↔ article (corrigées : Tournette 2350,
  Parmelan 1856, Garlaban 714, La Rhune 900, Valier 2839, Canigou 2785…).

## Limites honnêtes

- Le tracé est **le plus court chemin sur sentiers cartographiés OSM**
  (départ → sommet) : les variantes en boucle éditoriales et les itinéraires
  « conseillés » des topos ne sont pas couverts ; certains derniers mètres
  hors réseau OSM sont absents (contrôle < 300 m du sommet).
- Les durées sont des **estimations** (règle de marche) sauf mention
  éditoriale ; les dénivelés IGN sont calculés le long du tracé aller.
- Petits massifs (Dévoluy, Ubaye, Verdon, Mézenc…) : moins de 8 randonnées
  retenues — le vivier de sommets **randonnables à article Wikipédia** y est
  simplement plus petit ; rien n'a été gonflé artificiellement (règle
  « qualité avant quantité »).
- Groupements éditoriaux : « Provence » réunit Ventoux, Dentelles, Luberon,
  Sainte-Victoire et Garlaban ; « Verdon » couvre les Préalpes de Castellane ;
  la Grande Sassière est rattachée à « Vanoise » ; le mont Joly au
  « Beaufortain » ; « Chaîne des Puys » sépare Puy de Dôme/Pariou du Sancy.
- Quelques sommets emblématiques restent volontairement absents : voie
  normale non « randonnée » (Meije, Pelvoux, Mont Aiguille, pic du Midi
  d'Ossau, Pierra Menta) ou pas d'article Wikipédia dédié (Pic Cassini,
  Cadières de Brandis, Tête du Pelvas, Pic de Cabaliros…).

## État d'avancement (mis à jour au fil de l'eau)

- [x] Groupe 1 — Alpes du Nord : 37 randonnées ajoutées (50 au total avec la
      Chartreuse), 50/50 tracées, stats complètes, 8 massifs au filtre.
- [x] Groupe 2 — Alpes du Sud : +25 randonnées (75 au total), 75/75 tracées,
      stats complètes, 15 massifs au filtre. Écartées : Pic du Mas de la
      Grave, Tête du Pelvas, Tête de Louis XVI, Cadières de Brandis (pas
      d'article/coordonnées) ; Bric Froid ajouté en remplacement du Pelvas.
      Départs corrigés après routage : Obiou (Les Baumes), Pain de
      Sucre/Caramantran (Refuge Agnel), Gélas (Refuge de la Madone de
      Fenestre).
- [x] Groupe 3 — Pyrénées : +23 randonnées (98 au total), 98/98 tracées,
      stats complètes, 20 massifs au filtre. Écartées : Pic de Cabaliros,
      Trou de la Mouche… (pas d'article) ; deux améliorations générales du
      routage nées de ce groupe : essais multi-nœuds aux extrémités (îlot
      isolé de l'observatoire du pic du Midi) et exclusion des relations OSM
      dans la résolution des départs (relation « Port de Larrau » centrée à
      3,8 km du col). Départs corrigés : Orhy (cols d'Iraty), Brèche de
      Roland (« Col de Tentes »), Néouvielle et Carlit (parking du lac —
      le nom du lac résout au centre de l'eau).
- [x] Groupe 4 — Jura, Vosges, Massif central : +29 randonnées (127 au
      total), 127/127 tracées, stats complètes, 27 massifs au filtre.
      Écarté : Pic Cassini (pas d'article dédié). Amélioration du routage :
      jusqu'à 5 composantes distinctes essayées côté départ (l'îlot de
      10 nœuds de la placette de la Chaux-du-Dombief bloquait le pic de
      l'Aigle).
- [x] Groupe 5 — Corse : +8 randonnées (135 au total), 135/135 tracées.
      Écarté APRÈS routage : Capu Rossu (rando-0128) — les coordonnées
      Wikipédia tombent dans le maquis à mi-presqu'île, à 315 m du premier
      sentier ; point retiré par `tools/retirer_randos.py`, id gelé au
      registre (jamais réattribué).

## Résultat final (vérifié le 11/07)

- **+122 randonnées** ajoutées (catégorie : 13 → **135 points**,
  base : 9 666 → 9 788 features), **135/135 tracées** —
  `completer_stats_randos.py` ne signale **aucun « Sans tracé »**.
- **28 massifs** au filtre « Massif », tous alignés sur `details.massif`.
- Couverture : photos 99 %, descriptions 100 %, dénivelé 100 %,
  distance 100 %, durée 100 %, fiche « Référencée » 134/135 (la vallée des
  Merveilles reste « À vérifier » : pas de photo libre exploitable).
- Chaque point : sommet/objectif (jamais le parking), `details`
  (altitude(_n), dénivelé(_n), distance(_n), durée, départ, voie normale,
  massif, fiche), lien Wikipédia, 3 liens `properties.links`
  (🥾 Komoot, ⛰️ Altitude Rando, 🗺️ AllTrails).
- Vérification navigateur (headless CDP) : `dev/tests.html` **24/24 verts**,
  application chargée sans erreur, marqueurs affichés, exemple de fiche
  contrôlé (Pic de Tarbésou : liens, distance mesurée, durée estimée).
- Bornes France + Corse respectées, GeoJSON `[longitude, latitude]` contrôlé
  sur points connus (pic du Midi de Bigorre, Monte Cinto, Mont d'Or).
- data/randos.geojson : 205 Ko (tracés simplifiés Douglas-Peucker ~10 m).
- `sw.js` **non touché** (bump VERSION à faire par la session principale) ;
  aucun `git push` (workflow : l'utilisateur pousse).
