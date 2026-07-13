# Rapport de revue — cascade

Date : 2026-07-12 · Session principale. Catégorie **cascade** (le « gros morceau » de l'étape 1 : 91 % « À vérifier » au départ).

## Constat de départ (audit de complétude)

Sur **1 133 cascades** (source : OpenStreetMap `waterway=waterfall`, récolte `recolter_cascades.py`) :

| Champ | Rempli | |
|---|--:|--:|
| Description **rédigée** (Wikipédia) | 127 | 11 % |
| Description **générique OSM** | 1 006 | 89 % 🔴 |
| Photo | 100 | 8 % |
| Lien | 108 | 9 % |
| Hauteur | 279 | 24 % |
| Fiche « À vérifier » | 1 033 | **91 %** 🔴 |

**Différence clé avec l'escalade / les châteaux** : les cascades ont des **coordonnées OSM précises** (nœud réel de la chute), **pas de centroïde de commune**. Contrôle GPS sur les cascades célèbres — Gavarnie (423 m), Sillans (43,56/6,18), Sautadet (44,19/4,52), Ars (42,76/1,36), Tufs de Baume (46,69/5,64) : **positions correctes**. → **Aucun recalage GPS nécessaire.** L'effort porte entièrement sur l'**enrichissement** et l'**ajout de cascades notables manquantes**.

## Sources — licences vérifiées d'abord

- **Pas de jeu de données ouvert dédié** aux cascades sur data.gouv (contrairement au RES pour l'escalade) : recherche confirmée. Waterfalls ne sont ni équipements sportifs ni cavités inventoriés.
- **OpenStreetMap** (ODbL) — socle existant, faits réutilisables (attribution déjà en place dans ⚙️ Réglages).
- **Wikipédia FR** — on ne prend que des **FAITS + éléments libres** : le lien de l'article, un **extrait de 2 phrases** (résumé court, cité avec lien), la **photo** (`upload.wikimedia.org` uniquement — seul domaine autorisé par la CSP), les **coordonnées**. Jamais de recopie de prose longue.
- **Wikidata** (CC0) — non exploité dans cette passe (pas de champ hauteur/goutte fiable pour les chutes) ; piste de suivi mineure.

## Méthode (`tools/enrichir_cascades.py`, en place, ids stables)

1. **Arbre de catégories Wikipédia « Chute d'eau en France »** (par département / région / parc national / **DOM**), via `enrichissements.recolter_categorie_wikipedia` → **160 articles**, **147 géolocalisés**.
2. **Résolution Wikipédia** des noms des 1 033 cascades nommées + des 160 titres de catégorie (`_pages_cascades` : extrait + photo + coordonnées, avec suivi `continue` et `colimit=max`).
3. **Enrichissement des cascades existantes** (ne remplit QUE le vide ; remplace la description **générique OSM** par l'extrait Wikipédia) :
   - a) l'article portant **exactement le nom** de la cascade, avec **garde-fou anti-homonyme < 2 km** ;
   - b) sinon, un article de la catégorie « Chute d'eau » à **< 500 m** (même chute).
4. **Ajout des cascades notables manquantes** : articles de catégorie à > 500 m de tout point existant, en France (métropole + DOM), dédoublonnés.
5. **Recalcul du champ `fiche`** (Référencée = photo ET (lien ∪ extrait ∪ hauteur)).

## Résultat

### Enrichissement des existantes — 20 fiches
Peu de gain, et c'est un **résultat honnête, pas un bug** : le run d'origine tentait déjà Wikipédia pour tout nom contenant « cascade / chute / saut / voile » (soit la quasi-totalité des noms). Sur les 1 033 cascades nommées, **seules 97 ont un article frwiki au même nom, dont 79 étaient déjà liées**. La garde-fou < 2 km a **correctement rejeté** les faux amis (« Gouaux » = commune à 20 km ; « La Cascade » = *Immeuble La Cascade* à Villeurbanne, 400-800 km ; « Cascade Blanche » métropole → article de la Réunion à 8 900 km).

### Ajouts — +41 cascades notables (1 133 → 1 174)
La vraie valeur : la récolte OSM était **bornée à la métropole** → **tout l'outre-mer manquait**. La catégorie Wikipédia a rapporté les **cascades iconiques** absentes, chacune avec **photo CC + extrait + coordonnées précises** :

- **La Réunion** : Trou de Fer, cascade de Grand Galet (Langevin), Voile de la Mariée (Grand Bassin & Salazie), Cascade Blanche, Trou Noir, Les Trois Roches, Bras Magasin, Bras d'Annette, Chien, Biberon, Jacqueline, Pisse-en-l'air…
- **Guadeloupe** : Chutes du Carbet, Cascade aux Écrevisses, Saut de la Lézarde, Saut d'Acomat, Saut de Matouba, Chute du Galion, Chutes Moreau, Saut des Trois Cornes…
- **Guyane** : Chutes Voltaire, Saut Niagara, Chutes de Fourgassier, Chutes Patawa, Chute Pas Trop Tôt…
- **Martinique / Mayotte** : Chute du Bras-du-Fort, Cascade de Soulou…
- **Métropole** : Cascade d'Alzen (Ariège), du Régourdel (Lozère), de Polischellu (Corse).

39/41 avec photo, 41/41 avec extrait. Ids neufs `casc-1134`…`casc-1174`.

### Couverture finale (1 174 cascades)
Photo **8 % → 13 %**, lien **9 % → 14 %**, fiche Référencée **8 % → 13 %**, description rédigée **11 % → 16 %**.

## Limites honnêtes / plafond des sources

- **~80 % des cascades OSM françaises sont des chutes mineures sans article Wikipédia** : ni photo ni description rédigée ne peuvent être ajoutées sans les inventer. C'est le **plafond honnête des sources réutilisables** (même nature que la cotation escalade à 65 % ou les photos via-ferrata à 0 %). La position et le nom restent corrects, c'est l'essentiel pour la carte.
- **Hauteur** figée à ~24 % (tag OSM `height` seul ; Wikidata n'a pas de champ de goutte fiable).
- Suivi possible et modeste : image Wikidata (P18) pour les cascades à entité mais sans article frwiki ; récolte OSM des chutes DOM (mineures) si une couverture exhaustive outre-mer est souhaitée.

## Vérification

App rechargée (SW + caches purgés) : **0 erreur console**, 11 154 features servies, 1 174 cascades. Fiche **Trou de Fer** (casc-1172, Réunion) ouverte dans l'app → badge Cascade, extrait, photo aérienne CC, lien fr.wikipedia.org, statuts/Maps/Waze : **complète**.

## Bilan des catégories revues (étape 1)

| Catégorie | Points | GPS recalés | Fiches enrichies | Ajouts |
|---|--:|--:|--:|--:|
| via-ferrata | 126 → 133 | 44 | — | +7 |
| escalade | 2 033 → 3 351 | 1 790 | ~1 519 | +1 318 |
| **cascade** | **1 133 → 1 174** | **0** (GPS OSM déjà bons) | **20 + 41 neuves** | **+41** (dont l'outre-mer, absent) |
