# Rapport de revue — lac

Date : 2026-07-12 · Session principale. Catégorie **lac** (965 points) — la mieux lotie de l'étape 1.

## Constat de départ (audit)

**965 lacs**, tous issus de la récolte qualitative de l'enrichisseur (article Wikipédia obligatoire = filtre de notoriété). État déjà excellent :

| Champ | Rempli | |
|---|--:|--:|
| lien (Wikipédia) | 965 | **100 %** |
| description | 965 | 100 % |
| altitude (IGN) | 965 | 100 % |
| photo | 769 | 79 % |
| superficie | 591 | 61 % |
| profondeur | 260 | 26 % |
| fiche « À vérifier » | 196 | 20 % |

**GPS déjà bon** : les lacs ont été recentrés dans l'eau à la récolte. Contrôle sur les lacs célèbres — Annecy, Léman, Bourget, Serre-Ponçon, Sainte-Croix, Pavin : **tous correctement positionnés dans l'eau**. → **Aucun recalage.**

Fait notable : les **196 « À vérifier » sont exactement les 196 sans photo** (la fiche exige une photo pour « Référencé »). La revue lac est donc purement un enrichissement de photos + faits (superficie/profondeur), pas une correction de positions ni de liens.

## Sources — faits réutilisables

- **Wikidata** (CC0) : `P2046` superficie, `P4511` profondeur, `P18` image.
- **Wikimedia Commons** (API) : résolution de l'image P18 en vignette sur **upload.wikimedia.org** (seul hôte autorisé par la CSP).

## Méthode (`tools/enrichir_lacs.py`)

Pour chaque lac auquel il manque photo / superficie / profondeur : QID retrouvé par l'URL de l'article (961/965 résolus), puis Wikidata `P18/P2046/P4511`, et Commons pour l'URL d'image. Ne remplit que le vide, en faits.

**Bug corrigé en cours de route** : l'API Commons normalise les titres de fichiers avec des **espaces**, alors que la requête utilisait des **underscores** → toutes les images résolvaient à `null` (0/12). Après correction (normalisation en underscores à la lecture), les 12 images se résolvent.

## Résultat

- **+12 photos** (image Wikidata P18 → Commons), toutes de vraies vues de lacs (panoramas), sur upload.wikimedia.org → 12 lacs passent de « À vérifier » à « Référencé ».
- **+7 superficies** (Wikidata P2046, converties en hectares, affichées ha / km²).
- **+0 profondeur** : Wikidata n'a `P4511` que pour les lacs qui l'ont déjà.

Couverture : photo 79 → **80 %**, superficie 61 %, profondeur 26 %, fiche Référencé 79 → **80 %**.

## Limite honnête / plafond des sources

La catégorie lac était **déjà quasi complète** (l'enrichisseur avait bien travaillé). Le faible gain n'est pas un défaut de méthode mais le **plafond des sources libres** :
- sur les **196 lacs sans photo, seuls 12 ont une image Wikidata** (P18) — les 184 autres n'ont ni image de tête Wikipédia ni P18 : aucune photo libre à ajouter (même nature de limite que les cascades mineures) ;
- sur les **374 sans superficie, seuls 7** ont une `P2046` dans Wikidata ;
- sur les **705 sans profondeur, 0** n'a de `P4511` exploitable.

Position, nom, altitude, lien et description restent corrects et complets à 100 % : l'essentiel pour la carte.

## Bilan des catégories revues (étape 1)

| Catégorie | Points | GPS recalés | Fiches enrichies/corrigées | Ajouts |
|---|--:|--:|--:|--:|
| via-ferrata | 126 → 133 | 44 | — | +7 |
| escalade | 2 033 → 3 351 | 1 790 | ~1 519 | +1 318 |
| cascade | 1 133 → 1 174 | 0 (GPS OSM bons) | 20 | +41 (outre-mer) |
| chateau | 810 | 666 (82 %) | 32 liens erronés + 44 centroïdes corrigés + 94 re-liés | — |
| **lac** | **965** | **0** (GPS déjà bons, vérifiés) | **+12 photos, +7 superficies** | — |
