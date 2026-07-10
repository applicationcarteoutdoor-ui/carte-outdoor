# Rapport d'enrichissement — Catégorie « Lac » (2026-07-10)

Nouvelle catégorie `lac` (id stable, ids `lac-0001` → `lac-0965`), créée en
**sélection strictement qualitative** : des lacs que des voyageurs auront
réellement envie de découvrir, pas un aspirateur à plans d'eau.

**Résultat : 965 lacs intégrés** (8 519 → 9 484 points), dont 483 lacs de
montagne (> 1 500 m). Fiches « Référencé » : 769 (79 %).

## Critères de sélection appliqués

1. **Un lac entre s'il a un article Wikipédia francophone** (= notoriété
   touristique réelle). Source : arbre de catégories « Catégorie:Lac en
   France » (sous-catégories suivies seulement si leur nom contient « lac »,
   hors ébauches/listes/anciens lacs).
2. **Étangs célèbres** (Thau, Vaccarès, Berre…) : l'arbre « Catégorie:Étang
   en France » est parcouru en plus, avec un **seuil de notoriété de
   8 000 octets d'article** — calibré pour garder Vaccarès (8 336 o) et
   écarter les étangs de pêche anonymes ainsi qu'un roman de jeunesse
   (« Les Six Compagnons à l'Étang de Berre », 5 995 o). 23 étangs retenus
   par cette voie, 58 écartés.
3. **Incontournables hors arbres** : le Léman n'est catégorisé que dans
   « Catégorie:Léman » — injecté nominativement (`TITRES_SUPPLEMENTAIRES`).
4. **OSM/Overpass n'élargit JAMAIS la sélection** : il enrichit (altitude
   `ele`, recentrage des grands lacs, coordonnées de secours pour 3 articles
   non géolocalisés à correspondance de nom sans ambiguïté).

## Compteurs (1 311 articles récoltés → 965 retenus, 26 % écartés)

| Raison d'écartement | Nombre |
|---|---|
| Hors métropole (DOM/TOM, listés en fin de rapport) | 142 |
| Hors France — Andorre, Espagne, Suisse, Italie (filtre commune geo.api.gouv.fr) | 56 |
| Étangs sans notoriété suffisante (< 8 000 o) | 58 |
| Titres non lacustres (dérive des catégories-sujets : plages, canaux, mares, mémoriaux…) | 43 |
| Listes / barrages-ouvrages / articles-régions | 28 |
| Lacs disparus ou asséchés (détectés dans le résumé : Chedde, Malpasset, Glière…) | 11 |
| Sans coordonnées récupérables (articles-groupes : « Lacs de Clairvaux », « Étangs de la Dombes » sans géoloc…) | 8 |
| Doublons internes / fusions dans l'existant | 0 |

Le piège principal : **la bbox métropole contient l'Andorre et mord sur
l'Espagne, la Suisse et l'Italie**, et les catégories « Lac des Pyrénées »
couvrent les deux versants. D'où le filtre pays par géocodage inverse
(cache `tools/lacs-communes.json`) — 56 lacs étrangers écartés qui seraient
sinon passés (Estanys andorrans, embalses aragonais, lacs valaisans…).

## Qualité des données (leçons du run)

- **Wikidata porte des erreurs** : « Lac du Bourget 2 315 m » (231,5 réels),
  « Lac de Ribou 87 km² » (0,87), « Lac de Saint-Félix 21,5 km² »…
  Contre-mesures : altitudes validées/complétées par le **service
  altimétrique IGN au point du lac** (le MNT sur l'eau EST la surface :
  240 altitudes complétées, 16 corrigées → couverture 100 %) ; superficies
  > 20 km² acceptées seulement pour les grands lacs français connus (liste
  blanche) et recoupées avec le texte de l'article (7 valeurs douteuses
  écartées — champ absent plutôt que faux).
- **Étiquettes Wikipédia parfois à côté de l'eau** (Lac d'Annecy : en ville,
  à 6 km) et **centres OSM parfois sur une presqu'île** (Serre-Ponçon, lac
  en L). Pour les lacs ≥ 500 ha : test « le point est-il DANS un polygone
  natural=water ? » (Overpass `is_in`, cache `lacs-eau.json`) — 18 lacs
  recentrés, 3 conservent leur étiquette WP vérifiée dans l'eau.
- Noms régionaux pris en compte : laquet (Pyrénées), estany/estanh (catalan,
  aranais), Weiher (Vosges/Alsace) + exceptions nominatives vérifiées une à
  une (Lauvitel, Lindre, Fischboedle, Rabassoles…).

## Couverture des champs (sur 965)

| Champ | Couverture |
|---|---|
| Description (résumé Wikipédia) | 100 % |
| Lien (article Wikipédia) | 100 % |
| Altitude (`altitude` + `altitude_n`, Wikidata P2044 → IGN) | 100 % |
| Photo (upload.wikimedia.org uniquement) | 79 % (769) |
| Superficie (`superficie` + `superficie_n` en ha, Wikidata P2046) | 61 % (591) |
| Profondeur max (Wikidata P4511) | 27 % (260) |
| `details.fiche` « Référencé » (photo + information) | 79 % — 196 « À vérifier » |

## Intégration

- `tools/recolter_lacs.py` : récolte + fusion, **idempotent** (relance :
  965 ids réutilisés, 0 ajout), caches repris (`lacs-wiki-arbre.json`,
  `lacs-wiki-pages.json`, `lacs-wikidata.json`, `lacs-osm.json`,
  `lacs-communes.json`, `lacs-alti.json`, `lacs-eau.json` — gitignorés).
- `tools/build_data.py` : appel `recolter_lacs.convertir_lacs()` après les
  cascades (ids préservés d'une exécution à l'autre).
- `js/config/themes.js` : entrée `lac` (label « Lac », 🏞️, `#1a659e`),
  champs Altitude/Superficie/Profondeur max, filtres **Fiche** (✅ Référencé /
  🔍 À vérifier) et **Altitude** (Plaine < 600 m / 600-1 500 m / 🏔️ > 1 500 m).
- Dédoublonnage contre les 8 519 points existants (nom normalisé + < 500 m,
  toutes catégories) : **0 fusion nécessaire** — les homonymes trouvés
  (« Lac Bleu » cascade vs lacs) sont des lieux distincts à > 500 m.

## Vérifications effectuées

- Contrôles automatiques : bornes France (0 hors bornes), ordre
  [lon, lat] confirmé sur Annecy/Bourget/Léman/Serre-Ponçon, ids uniques et
  bien formés, aucun nom technique, aucun mojibake, aucun HTML brut,
  photos 100 % upload.wikimedia.org.
- Navigateur (preview, SW purgé) : catégorie cochée → 965 points, clusters
  France entière ; **pins d'Annecy et Serre-Ponçon visuellement dans l'eau** ;
  fiche « Lac du Lauzet » complète (description, altitude, lien, boutons) ;
  photo Wikimedia affichée ; filtre Altitude : 1 176 → 694 marqueurs
  (les 482 lacs < 1 500 m visibles masqués, autres catégories intactes).
- Échantillon aléatoire de 10 lacs : liens Wikipédia 10/10 en HTTP 200 ;
  photos 4/9 en 200 et 5/9 en 429 (rate-limit Wikimedia sur ma rafale de
  HEAD — URLs valides, affichage navigateur vérifié par ailleurs).
- `dev/tests.html` : **24/24 réussis**.

## Limites connues

- **196 fiches « À vérifier »** (sans photo Wikipédia pour l'essentiel) —
  le filtre Fiche permet de les retrouver d'un coup d'œil.
- Profondeur connue pour 27 % seulement (Wikidata lacunaire).
- **Lacs de crête frontalière** géolocalisés côté étranger par Wikipédia
  (Lac de la Bernatoire, Lac de Chésery/Lac Vert du Chablais, Lac
  Saint-Maurice d'Ariège) : écartés par le filtre pays — ambiguïté
  inhérente à la frontière, ~3-4 cas.
- 6 lacs réels sans coordonnées ni correspondance OSM (Lac Lano, Lac de
  Bellebone, Lac de l'Ortolo, Étang Vallier, Étang des Belles Seignes,
  Étangs de Corot) : non intégrés.
- **142 lacs hors métropole non intégrés** (bassins de la Réunion, étangs
  de Guadeloupe/Martinique, Guyane, Mayotte, Saint-Pierre-et-Miquelon,
  Kerguelen…) : intégrables plus tard si l'app couvre les DOM.
- Étangs : seuil de 8 000 octets = choix calibré (alternatives chiffrées :
  12 000 o → perd Vaccarès ; 5 000 o → +13 étangs dont un roman et des
  étangs de pêche). Ajustable dans `SEUIL_ETANG`.
- Le port du serveur de preview est passé de 8125 à **8128** dans
  `.claude/launch.json` (remède documenté au cache agressif du proxy de
  preview, qui servait un points.geojson périmé).

## Hors métropole (non intégrés, pour mémoire)

Bassin Bleu, Bassin Bœuf, Bassin Cadet, Bassin Cormoran, Bassin Malheur,
Bassin Pigeons, Bassin Vital, Bassin des Aigrettes, Bassin des Hirondelles,
Bassin du Diable, Bassin la Mer, Bassin la Paix… (+130 — liste complète
reproductible via `python tools/recolter_lacs.py --dry-run`).

## Reste à faire

- Bump `VERSION` dans `sw.js` (réservé à l'orchestrateur), commit + push
  par l'utilisateur.
- Idées de suite : photos manquantes via Wikimedia Commons (P18 Wikidata),
  tag OSM baignade/activités (peu présent sur les polygones d'eau, à
  chercher sur les `leisure=*` riverains), catégorie DOM séparée.
