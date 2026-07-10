# Rapport d'enrichissement — Randonnées remarquables (PILOTE Chartreuse) + cadrage France

Date : 2026-07-10 · Agent : enrichisseur de données
Volet 1 : pilote intégré (massif de la Chartreuse). Volet 2 : cadrage France (aucune récolte).

---

## 1. Pilote Chartreuse — intégré

### Constat de départ (honnête)

Il n'existe **aucune base libre de « belles randonnées »** : FFRandonnée, Visorando,
AllTrails sont propriétaires. Les GR (tracés) sont déjà dans l'app. Le pilote repose
donc sur une **liste éditoriale** de sorties emblématiques du massif, validée par
deux sources libres :
- **Wikipédia** (obligatoire = filtre de notoriété) : coordonnées du sommet, photo
  (`upload.wikimedia.org`), résumé introductif, **vérification croisée de l'altitude**
  éditoriale dans le texte de l'article ;
- **OSM/Overpass** (corroboration) : relations `route=hiking` nommées de la bbox
  Chartreuse (45.15–45.55 / 5.55–6.05) — un itinéraire balisé portant le nom de
  l'objectif est signalé dans `details.itineraire`.

### Convention de placement (décision documentée)

**Le point est posé au SOMMET (ou à l'objectif — cirque) de la randonnée, jamais au
parking.** Raisons : c'est ce que Wikipédia géolocalise précisément, c'est ce que le
voyageur cherche sur la carte, et un même sommet a plusieurs départs. Le départ
classique est donné dans `details.depart` (avec son altitude quand elle est connue).

### Critères de sélection (posés AVANT la récolte)

1. Objectif emblématique du massif (sommet à voie normale de randonnée, ou site
   majeur type cirque de Saint-Même) ;
2. Article Wikipédia fr **dédié** (une redirection vers un autre article = écarté) ;
3. Praticable en randonnée : **Le Néron écarté volontairement** (arête exposée,
   accidents fréquents — ce n'est pas une randonnée) ;
4. Coordonnées dans la bbox Chartreuse (garde-fou anti-erreur de géocodage).

### Compteurs

| | |
|---|---|
| Points avant | 9 653 (0 randonnée) |
| Candidates (liste éditoriale) | 15 |
| **Ajoutées** | **13** (`rando-0001` … `rando-0013`) |
| Rejetées (qualité/notoriété) | 2 — *Petit Som* (redirige vers l'article Grand Som), *Roc de Pravouta* (aucun article) + *Le Néron* écarté en amont (sécurité) |
| Doublons avec l'existant | 0 (collisions vérifiées : Dent de Crolles/escalade, Mont Outheran/escalade… toutes à > 500 m — sites géocodés au centroïde de commune) |
| Points après | **9 666** |

Les 4 grands sommets demandés sont présents : **Chamechaude (2 082 m), Dent de
Crolles (2 062 m), Grand Som (2 026 m), Charmant Som (1 867 m)**.

### Couverture des champs

photo 92 % · description 100 % · D+ estimé 61 % · durée 61 % · départ 100 % ·
fiche « Référencée » 92 % (12/13 — seule `rando-0005` Dôme de Bellefont est
« À vérifier » : pas de photo sur son article). Corroboration OSM : 1 relation
(« Le sommet du Mont Granier ») — les boucles classiques de Chartreuse ne sont
presque jamais des relations OSM nommées, c'est un enseignement du pilote.

**Nature des D+ et durées** : le dénivelé est une **estimation** (altitude sommet −
altitude du départ classique, affichée « ≈ ») ; les durées sont des valeurs
éditoriales classiques, données seulement quand elles sont bien établies. Les champs
absents restent absents (pas de données inventées). Une altitude éditoriale non
retrouvée dans l'article est signalée au lieu de bloquer (cas du Grand Som : son
intro ne cite pas son altitude).

### Bug rencontré (documenté pour la suite)

L'API Wikipédia fusionne les redirections : « Petit Som » redirige vers « Grand Som »,
et une chaîne de correspondance *inversée* (to→from) attribuait la page au Petit Som
en laissant le Grand Som orphelin. Corrigé dans `pages_wikipedia()` : suivi **avant**
(from→to) par titre demandé, et rejet des redirections aboutissant à l'article d'une
autre entrée du pilote.

### Vérifications effectuées

- Assertions Python : 13 ids `rando-NNNN` uniques (et unicité globale des 9 666 ids),
  bornes bbox Chartreuse respectées, `[lon, lat]` vérifié sur Chamechaude
  ([5.78806, 45.2875] = le sommet, pas l'inverse), photos 100 % `upload.wikimedia.org`,
  UTF-8 propre, `massif`/`fiche` posés partout ;
- Ré-exécution du script : les 13 ids sont **réattribués à l'identique** (mécanisme
  d'ids stables opérationnel) ;
- Navigateur (preview 8128, SW purgé) : `dev/tests.html` **24/24 verts** avec la
  nouvelle entrée themes.js ; catégorie « Randonnée » visible dans le panneau,
  thème résolu (vert #2d6a4f, 🥾, 2 filtres), Chamechaude au bon endroit avec photo
  et fiche Référencée.

### Fichiers livrés

- `tools/recolter_randonnees.py` — récolte + fusion, caches `tools/randos-*.json`
  (gitignorés), `--dry-run`, `--cadrage`, extensible massif par massif ;
- `data/points.geojson` — +13 features `randonnee` ;
- `js/config/themes.js` — entrée `randonnee` (vert sentier #2d6a4f, 🥾), champs
  altitude/D+/durée/départ/voie normale/itinéraire OSM/massif, filtres déclaratifs
  « Fiche » (✅ Référencée / 🔍 À vérifier) et « Massif » (type value, extensible).

**Reste à faire (hors périmètre du pilote)** : bump `VERSION` dans `sw.js` au moment
de la publication (non fait ici : un autre chantier est en cours dans l'arbre de
travail — sw.js, oracle.js, map.js modifiés par ailleurs).

---

## 2. Cadrage France entière (aucune récolte — comptages seuls)

### Volumes mesurés

| Source | Requête | Compte |
|---|---|---|
| Overpass | relations `route=hiking` nommées, aire France (DOM inclus) | **15 407** |
| Overpass | … dont taguées `wikidata` | **356** |
| Wikidata (SPARQL) | montagnes de France (P31=Q8502) avec article Wikipédia fr + altitude | **1 543** |
| Wikidata | … dont ≥ 1 500 m | **828** |
| Wikidata | … dont ≥ 2 000 m | **620** |

Notes de mesure : le comptage Overpass des nœuds `natural=peak` à l'échelle France
**expire systématiquement** (> 200 s, vécu deux fois) → sommets comptés via Wikidata
(une seule requête SPARQL, 3 sous-selects — le WDQS était en limitation 1 req/min).
P31=Q8502 strict : les sommets typés autrement (Q207326…) manquent, les vrais
volumes sont donc un peu supérieurs.

### Options pour l'échelle France (à valider par l'utilisateur)

**Option A — Extension éditoriale massif par massif (recommandée)**
Le modèle du pilote appliqué aux grands massifs : Vercors, Belledonne, Bauges,
Aravis, Vanoise, Écrins, Queyras, Ubaye, Mercantour, Mont-Blanc/Aiguilles Rouges,
Pyrénées (4-5 secteurs), Vosges, Jura, Massif central (Sancy, Cantal, Mézenc),
Corse — soit ~20 listes de 12 à 25 sorties. **Volume : ~250 à 400 randonnées.**
Qualité maximale (départ classique, D+, durée, tri sécurité), coût : rédaction des
listes éditoriales (le réservoir Wikipédia existe : 828 sommets ≥ 1 500 m documentés).
Le filtre « Massif » et la structure du script sont déjà prêts pour ça.

**Option B — Relations OSM `route=hiking` taguées wikidata (356)**
Itinéraires balisés réels et documentés, mais : recouvrement fort avec les GR déjà
dans l'app, couverture très inégale (1 seule relation nommée corroborait le pilote
Chartreuse), et une relation est une LIGNE (choix d'un point représentatif délicat).
**Volume exploitable estimé après tri : ~150-250.** Complément possible de l'option A,
pas une base autonome.

**Option C — Import automatique des sommets ≥ 2 000 m avec article (620)**
Rapide mais dangereux pour la ligne éditoriale : beaucoup sont des courses
d'alpinisme (Grandes Jorasses, Meije…), pas des randonnées, et Wikipédia ne fournit
ni départ ni voie normale de façon structurée. Exigerait un tri manuel a posteriori
équivalent au coût de l'option A, pour une qualité moindre. **Déconseillée.**

### Limites connues du pilote

- Corroboration OSM quasi muette en Chartreuse (1/13) — l'angle « relations OSM »
  est plus faible qu'espéré pour les boucles de sommets ;
- D+ et durées : estimations éditoriales, pas de source structurée libre ;
- 1 fiche « À vérifier » (Dôme de Bellefont, sans photo) ;
- Sélection éditoriale = subjectivité assumée, mais critères écrits et rejets comptés.
