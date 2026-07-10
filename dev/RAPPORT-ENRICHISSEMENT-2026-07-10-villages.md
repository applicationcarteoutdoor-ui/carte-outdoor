# Rapport d'enrichissement — Plus Beaux Villages de France (2026-07-10)

Intégration des Plus Beaux Villages de France dans la catégorie **existante**
`cite-caractere` (label « Village »), sans nouvelle catégorie ni modification
de `themes.js` (le filtre « Label » ⭐/🏘️ existant les distingue déjà).

## Source et méthode

- Wikipédia : catégorie « Localité adhérant à l'association Les Plus Beaux
  Villages de France » (+ sous-catégories par département), puis
  `prop=coordinates|pageimages|extracts` par lots de 20 (`colimit=max`,
  suivi de `continue`, `exintro`/`exsentences=2`).
- Script : `tools/recolter_villages.py` (idempotent — relance sans doublon,
  les `pbvf-*` existants sont mis à jour en place). Caches :
  `tools/villages-articles.json`, `tools/villages-details.json`
  (sauvegardé à chaque tranche).
- Photos : `upload.wikimedia.org` uniquement (vignettes 500 px) ;
  lien Wikipédia dans `link` ; extrait d'intro (2 phrases) en description.

## Compteurs

| | |
|---|---|
| points.geojson avant → après | 9 484 → 9 653 (+169) |
| Articles récoltés | 182 (dont 1 article « Liste… » sans coordonnées, écarté) |
| Nouveaux points `pbvf-0001…pbvf-0169` | 169 (`details.label` = « Plus Beaux Villages de France ») |
| Fusionnés dans une cité existante (nom normalisé < 3 km, id `cc-*` conservé) | 10 : Marcolès, Locronan, Rochefort-en-Terre, Sancerre, Saint-Céneri-le-Gérei, Aubeterre-sur-Dronne, Charroux, Talmont-sur-Gironde, Montsoreau, Vouvant — `details.label` = « Cité de caractère · Plus Beaux Villages de France », photo/lien/description complétés seulement s'ils manquaient |
| Doublon interne au lot | 1 (« Saint-Antoine-l'Abbaye » / « Saint Antoine l'Abbaye » : deux articles Wikipédia du même village, fusionnés) |
| Hors métropole (écarté) | 1 : Hell-Bourg (La Réunion, hors bornes de l'app) |
| `details.fiche` | 179 « Référencé » / 0 « À vérifier » |

## Couverture

- Photo : 169/169 nouveaux points (100 %) · Description : 169/169 · Lien : 169/169.
- Les 201 cités de caractère non PBVF restantes sont inchangées (pas de champ `fiche`, comme avant).

## Écart avec la liste officielle

La liste officielle compte ~180 villages. Récolte : 180 villages distincts
(179 en métropole + Hell-Bourg à La Réunion, exclu car hors bornes de la
carte). Écart nul ou marginal — la catégorie Wikipédia suit la liste de près
(un déclassement/classement très récent peut ne pas y être répercuté).

## Vérifications

- Assertions script : total 9 653, ids `pbvf-*` uniques et continus, bornes
  France métropolitaine respectées, `[lon, lat]` confirmé sur Gordes
  (5.201, 43.912), Riquewihr (7.298, 48.167), Rocamadour (1.619, 44.800),
  aucun `details.label` vide, photos 100 % `upload.wikimedia.org`,
  encodage UTF-8 propre, pas de HTML dans les textes.
- `dev/tests.html` (SW purgé avant) : **24 réussis, 0 échoué**.

## Limites

- Descriptions = intro Wikipédia (2 phrases) : parfois administratives
  (« … est une commune française située… ») plutôt que touristiques.
- Coordonnées = point Wikipédia de la commune (généralement le bourg) —
  précision suffisante à l'échelle de la carte.
- Pas de vérification visuelle complète dans l'app (budget) : un tour
  d'échantillon via le testeur reste possible.

## Reste à faire (par l'utilisateur)

- Bump `VERSION` dans `sw.js` (interdit à cet agent sur cette mission —
  travail parallèle en cours), puis commit + push.
