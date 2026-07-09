# Rapport d'enrichissement — Cascades (2026-07-09)

Nouvelle catégorie **`cascade`** (💦 « Cascade », bleu d'eau vive `#0096c7`) :
**1 133 cascades** de France métropolitaine + Corse intégrées à `data/points.geojson`.

## Vue d'ensemble

| | Avant | Après |
|---|---|---|
| Points dans `points.geojson` | 7 386 | **8 519** |
| Taille du fichier | 5 208 Ko | 5 553 Ko |
| Catégories | 8 | 9 (+ `cascade`) |

Aucun id existant modifié, aucun point supprimé. Les cascades portent les ids
`casc-0001` → `casc-1133` (tri stable par nom normalisé puis lon/lat → diff git lisible).

## Sources et requêtes

1. **OpenStreetMap via Overpass** (source principale) —
   `nwr["waterway"="waterfall"](area.fr)(bbox)` par tuiles de 3°, `out center`
   (nœuds + centres des ways/relations), **filtre pays `area["ISO3166-1"="FR"]`**
   (sans lui, la bbox métropole moissonne la Suisse, l'Italie, l'Espagne…).
   Récolte : **2 744 éléments** (2 677 nœuds, 67 ways). Overpass a rate-limité
   fort (429/504 par vagues) : le script fait 3 passes sur les tuiles en échec
   au lieu de rejouer toute la récolte ; cache `tools/cascades-osm.json`
   sauvegardé seulement une fois TOUTES les tuiles réussies.
2. **Wikipédia (fr)** — 844 titres vérifiés par lots de 20
   (`prop=coordinates|pageimages|extracts|info|pageprops`, `colimit=max` +
   suivi de `continue`, `exlimit` plafonné à 20 par l'API) : tags OSM
   `wikipedia`/`wikipedia:fr` (45), tags `wikidata` résolus vers frwiki via
   `wbgetentities` (59 entités), et noms « clairement cascade » tentés tels
   quels — **lien accepté seulement si l'article est géolocalisé à < 2 km du
   point OSM** (8 devinés rejetés car trop loin → zéro homonyme).
   Photos : uniquement `upload.wikimedia.org` (seul domaine autorisé par la CSP).
3. **geo.api.gouv.fr** (géocodage inverse) — pour nommer « Cascade (Commune) »
   les 123 cascades sans nom conservées.

Caches (gitignorés, reprise incrémentale) : `tools/cascades-osm.json`,
`cascades-wiki.json`, `cascades-wikidata.json`, `cascades-communes.json`.

## Compteurs

| Étape | Nombre |
|---|---|
| Éléments OSM `waterway=waterfall` récoltés | 2 744 |
| Écartés : `access=private/no` | 1 |
| Écartés : **anonymes sans intérêt** (ni nom, ni hauteur, ni wikipedia/wikidata) | 1 558 |
| Sans nom conservées (hauteur ou wiki) → nommées « Cascade (Commune) » | 123 récoltées, 100 intégrées après dédoublonnage |
| Doublons internes (même nom normalisé à < 500 m) fusionnés | 50 |
| Fusionnés dans des points existants (autres catégories) | 2 |
| Liens Wikipédia posés | 101 (devinés rejetés : 8) |
| Hors bornes / mojibake / HTML / noms vides / photos hors domaine | 0 |
| **AJOUTÉS** | **1 133** |

Les 2 fusions dans l'existant (id conservé, aucun doublon créé) :
- `rf-8540` (refuge) « Salt de l'Aigua » — cascade OSM homonyme à 26 m ;
- `esc-0303` (escalade) « Cascade de Salins » — cascade OSM homonyme à 268 m
  (site de cascade de glace sur la chute elle-même).

3 autres homonymies (« Cascade de Doran », « Cascade de La Fare »…) restent
volontairement des points distincts : les sites d'escalade sont géocodés au
centroïde de commune, à > 500 m de la chute réelle.

## Couverture des champs (sur 1 133)

| Champ | Nombre | % |
|---|---|---|
| `details.hauteur` (+ `hauteur_n` numérique, prêt pour un futur filtre à tranches) | 279 | 25 % |
| Photo (Wikipédia, upload.wikimedia.org) | 100 | 9 % |
| Lien (article Wikipédia ou site) | 108 | 10 % |
| Description riche (extrait Wikipédia ou description OSM) | 127 | 11 % |
| `details.altitude` (tag `ele`) | 17 | 1,5 % |
| Mention « cours d'eau intermittent » (tag `intermittent=yes`) | 37 | 3 % |

Les autres fiches portent la description générique « Cascade référencée par
les contributeurs OpenStreetMap » — mieux vaut un champ absent qu'une donnée
inventée (l'application n'affiche que ce qui existe).

## Décisions notables

- **1 558 chutes anonymes écartées** : sans nom, sans hauteur, sans article,
  elles n'apportent rien à l'utilisateur (et auraient doublé le volume).
  Les 123 anonymes conservées avaient au moins une hauteur ou un article ;
  elles sont nommées « Cascade (Commune) » par géocodage inverse exact.
- **Pas de filtre déclaratif pour l'instant** : `hauteur_n` n'est présent que
  sur 25 % des points ; un filtre à tranches exclurait silencieusement les
  75 % restants. Le champ numérique est en place pour l'activer plus tard.
- **Intégration au pipeline** : `tools/build_data.py` appelle désormais
  `recolter_cascades.convertir_cascades()` — une régénération complète ne
  perd pas les cascades, et **les ids `casc-…` sont préservés** d'une
  exécution à l'autre (correspondance nom + < 500 m, vérifiée : un second
  passage réutilise 1 133 ids et n'ajoute rien).

## Vérifications effectuées

- Bornes France + Corse : 0 point hors bornes ; ordre GeoJSON **[lon, lat]**
  contrôlé sur la carte (marqueur exactement sur l'étiquette du fond topo).
- Échantillon de 10 points systématiques (casc-0001, 0114, 0227, 0340, 0453,
  0566, 0679, 0792, 0905, 1018) : positions plausibles (Hérault, Bauges,
  Écrins, Aravis, Giffre, Val-d'Isère, Oisans, Maurienne, Mont-Dore, Gard).
- Contrôles nominatifs : Cascade du Ray-Pic (fiche complète : extrait
  Wikipédia, « Hauteur de chute 60 m », lien, photo chargée), La Grande
  Cascade de Gavarnie, Cascade/Glissades du Capucin (pin sur l'étiquette
  « Cascade du Capucin » du fond de carte).
- `dev/tests.html` : **24 réussis · 0 échoué**.
- Catégorie visible dans le panneau (« 💦 Cascade 1133 »), décochée par
  défaut ; données d'essai du navigateur de preview nettoyées.

## Limites connues

- **Couverture OSM inégale** : très dense dans les Alpes, les Pyrénées, le
  Jura et le Massif central ; clairsemée en plaine (réalité hydrographique,
  mais aussi biais de contribution OSM).
- **Cascades frontalières mappées côté voisin exclues** par le filtre pays :
  le Saut du Doubs, par exemple, a son nœud OSM côté suisse.
- Hauteur connue sur un quart des points seulement ; altitude quasi absente
  (tag `ele` rare sur les cascades).
- Plusieurs cascades anonymes d'une même commune partagent le même nom
  « Cascade (Commune) » quand elles sont à > 500 m l'une de l'autre.
- Les tags OSM `image` (18) et `wikimedia_commons` (16) n'ont pas été
  exploités : la CSP `img-src` n'autorise que `upload.wikimedia.org` et ces
  tags pointent souvent ailleurs (pages `File:`, sites tiers).

## Reste à faire (suggestions)

1. Activer un filtre à tranches sur `hauteur_n` si la couverture OSM monte.
2. Passer les tags `wikimedia_commons`/`image` par l'API Commons pour en
   tirer des vignettes `upload.wikimedia.org` supplémentaires (+ ~30 photos).
3. Catégorie « Lac » (`nwr["natural"="water"]["water"~"lake|reservoir"]["name"]`)
   avec la même mécanique (le script est réutilisable à ~80 %).
4. Au moment de livrer : `VERSION` de `sw.js` déjà à v44 non publiée — ces
   données partent dans la même v44 (aucun bump fait ici, conformément à la
   consigne). Commit + push à faire par l'utilisateur.

## Fichiers touchés

- `tools/recolter_cascades.py` (nouveau) — récolte + enrichissement + fusion,
  reprise sur caches, `--dry-run` disponible.
- `tools/build_data.py` — appel des cascades dans le pipeline complet.
- `js/config/themes.js` — entrée `cascade` (id stable, champs Hauteur de
  chute / Altitude, pas de filtre).
- `data/points.geojson` — 8 519 features.
