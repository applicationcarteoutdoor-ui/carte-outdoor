# Rapport de revue — château

Date : 2026-07-12 · Session principale. Catégorie **chateau** (810 points).

## Constat de départ (audit)

**810 châteaux, TOUS au centroïde de commune** (« Position au centre de la commune » dans 810/810 descriptions) — géocodés à l'origine au centre du bourg, comme l'escalade avant sa revue. 89 partagent exactement la même coordonnée (plusieurs châteaux dans une même commune). Enrichissement Wikipédia partiel : 64 % photo, 67 % lien, **35 % « À vérifier »**.

Deux familles de défauts détectées :
1. **Position au centroïde** (100 %) — jamais la vraie position du château.
2. **Erreurs** : liens Wikipédia vers des **homonymes** (le rapprochement d'origine « Château de X » visait le premier article existant, souvent le mauvais) ; **centroïdes géocodés sur la mauvaise commune homonyme** (ex. « Brissac-Quincé en Maine-et-Loire » placé à *Brissac* dans l'Hérault) ; départements erronés dans certains noms (« Château Aiguèze **dans le Rhône** » alors que Aiguèze est dans le Gard).

## Sources — faits réutilisables

- **Wikipédia FR** — l'article d'un château porte sa **vraie position** (`prop=coordinates`, jamais récupérée jusqu'ici) + le QID Wikidata. Coordonnée = fait réutilisable.
- **Wikidata** (CC0) — `P625` en repli quand l'article n'a pas de coordonnée.
- **OpenStreetMap** (ODbL) — `historic=castle|fort|fortress|manor|citadel` pour les châteaux sans article Wikipédia (Phase 2).
- **geo.api.gouv.fr** — géocodage inverse (validation du département).

## Phase 1 — Recalage depuis les articles Wikipédia liés (`recaler_chateaux.py`)

Pour chacun des **543 châteaux liés** : récupération de la coordonnée de l'article (529/533 en ont une) + QID.

**Deux niveaux de décision :**
- **Article à < 20 km du centroïde** → le centroïde corrobore → **recalage direct** (461 châteaux). Écarts typiques 0,3–3 km : la vraie position dans la commune.
- **Article à > 20 km** (80 cas) → le centroïde est peut-être FAUX. On tranche par le **département** (géocodage inverse de l'article, comparé au département cité dans le NOM et au code de la description) :
  - **département concordant → recalage** + correction de la ligne « Commune » (elle pointait un homonyme). **44 châteaux** ainsi sauvés — ex. Brissac (Hérault → **Maine-et-Loire**, la vraie position), Bonnefontaine (→ Ille-et-Vilaine), Bridoire (→ Dordogne), Château-Queyras, Fort de Joux.
  - **article à l'étranger ou dans un autre département = lien erroné (homonyme) → déliaison** : lien + photo retirés, fiche remise à « À vérifier ». **32 châteaux** — ex. « Château de Belfort » (article en Suisse), « Château Grammont » → article « Château de Villersexel », « Château Laval » → « Château de Val ». **Correction d'erreurs**, pas une perte.
  - incertain (département du nom illisible) → **laissé tel quel** (4).

**Bilan Phase 1** : **505 recalés** (461 proches + 44 validés par département), **32 liens erronés corrigés**, ~2 sans coordonnée. Garde-fou conforme à la règle « recaler sur le mauvais site est pire que le centroïde ».

## Phase 2 — OSM `historic=castle` pour les châteaux sans article (`recaler_chateaux_osm.py`)

Récolte Overpass `historic=castle|fort|fortress|manor|citadel` en France (ODbL, tuiles 3°) → **15 360 châteaux nommés**. Recalage CONSERVATEUR des 305 châteaux encore au centroïde : uniquement si un château OSM au **nom correspondant** est **unique à < 12 km** du centroïde (sinon on laisse — pas de devinette). Rétablissement du lien Wikipédia si l'objet OSM porte un tag `wikipedia:fr`.

**Précision du rapprochement** : correspondance de cœur de nom **exacte** (jusqu'à 12 km) ; correspondance **partielle** (un cœur contient l'autre) durcie à cœurs ≥ 5 lettres ET < 5 km (les faux positifs génériques type « la Motte » sont plus loin — ex. écarté « Lamotte-Beuvron » → *Château de la Motte* à 9,9 km).

**Bilan Phase 2** : **161 recalés** (118 exacts + 43 partiels), dont **94 re-liés à Wikipédia** via le tag OSM. 4 ambigus (≥ 2 châteaux OSM au même nom → laissés), 140 sans correspondance OSM. Contrôle : 41 correspondances partielles inspectées une à une, médiane 1 km, aucun déplacement > 4,1 km ; un seul discutable (« Château des Évêques de Verdun » → *Citadelle de Verdun*, 1,9 km, même ville → impact négligeable).

## Résultat global

**666 châteaux recalés sur 810 (82 %)** — Phase 1 (505, Wikipédia) + Phase 2 (161, OSM). **144 restent au centroïde** (18 %). Liens 67 % → **74 %** (32 erronés retirés, 94 rétablis), fiche Référencé 64 % → **72 %**. Photos 64 % → 61 % (baisse **voulue** : les photos des 32 liens homonymes erronés ont été retirées — une photo fausse est pire qu'aucune). Vérifié dans l'app : 0 erreur console, Brissac en Maine-et-Loire, Cirey-sur-Blaise (château de Voltaire) recalé et lié, Belfort délié.

## Limite honnête / reste à faire

- Les châteaux **sans article Wikipédia ET sans château OSM nommé correspondant** restent au centroïde : correspondance non certaine → laissés (conformément à la règle de recalage prudent). Leur commune est correcte, c'est l'essentiel pour la carte.
- Départements erronés dans quelques **noms** (« … dans le Rhône » pour un château du Gard) : cosmétique, le code correct est dans la description ; nettoyage possible en suivi.
- Photos toujours limitées par la CSP (upload.wikimedia.org uniquement) et par l'absence d'image dans certains articles.

## Bilan des catégories revues (étape 1)

| Catégorie | Points | GPS recalés | Fiches corrigées | Ajouts |
|---|--:|--:|--:|--:|
| via-ferrata | 126 → 133 | 44 | — | +7 |
| escalade | 2 033 → 3 351 | 1 790 | ~1 519 | +1 318 |
| cascade | 1 133 → 1 174 | 0 (GPS OSM déjà bons) | 20 | +41 (outre-mer) |
| **chateau** | **810** | **666** (82 % : 505 Wikipédia + 161 OSM) | **32 liens erronés déliés + 44 centroïdes homonymes corrigés + 94 re-liés** | — |
