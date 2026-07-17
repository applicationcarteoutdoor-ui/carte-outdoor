# Rapport de contrôle qualité des données — 17 juillet 2026

Contrôle complet en **lecture seule** de tous les fichiers de données (aucun fichier de `data/` ni `js/` modifié). Scripts d'audit dans le scratchpad de session (`qc_donnees.py`, `qc_approfondi.py`), exécutés deux fois avec résultats strictement identiques (données figées au 16/07 23:28, dernier build v67).

## Verdict global

**BON — publiable.** Aucune anomalie bloquante sur 431 536 points et 463 tracés. Les invariants structurels tiennent tous : ids uniques inter-fichiers, thèmes connus, tracés sans orphelins, géométries valides, potabilité 100 % dans le référentiel. Reste un lot bien identifié de **67 vignettes Wikimedia cassées** (tailles non normalisées → HTTP 400 vérifié), 2 liens cassés, 6 cotations via ferrata hors échelle K et 1 cathédrale hors Nouvelle-Zélande.

## Invariants re-vérifiés (validés au 1er passage, reconfirmés)

| Contrôle | Résultat |
|---|---|
| Unicité GLOBALE des ids (17 fichiers de points fusionnés dans l'app) | ✅ 431 536 ids, 0 doublon |
| Format des ids (`[\w-]+`, préfixes pays/catégorie) | ✅ 0 écart |
| Thèmes tous connus de `js/config/themes.js` | ✅ 0 inconnu |
| Tracés randos → id existant du points.geojson du même pays | ✅ 0 orphelin (FR 135, CH 24, IT 23, ES 27, NZ 26) |
| Tracés canyons → id existant + cohérence flag `properties.trace` ↔ fichier | ✅ 27/27, bijection parfaite |
| Segments ≥ 2 points, sommets dans les bornes du pays | ✅ 0 écart (gr.geojson 190, great-walks 11 inclus) |
| Potabilité ∈ {Eau potable, Non potable, Potabilité non garantie} | ✅ 100 % sur les 5 pays (208 793 points d'eau) |
| Champs `_n` numériques ; distance_n > 0 ; denivele_n ≥ 0 (randos) | ✅ (voir cosmétique pour 4 altitudes légitimement négatives) |
| Descriptions : HTML brut, littéraux `undefined`/`null`/`None`, caractères de contrôle | ✅ 0 cas |
| Labels de links vides ou suspects | ✅ 0 cas |
| Échantillon 10 fiches/pays (name non vide + thème connu) | ✅ 50/50 OK |

## Comptes par pays et thème

| Thème | FR | CH | IT | ES | NZ |
|---|---:|---:|---:|---:|---:|
| toilettes | 66 584 | 6 588 | 10 211 | 7 404 | 4 562 |
| eau | 49 531 | 18 023 | 79 138 | 60 144 | 1 957 |
| grotte | 49 717 | 357 | 9 363 | 7 931 | 127 |
| culture (musées) | 5 053 | 1 220 | 6 301 | 3 972 | 307 |
| refuge | 3 524 | 815 | 3 138 | 1 068 | 958 |
| escalade | 3 351 | — | — | — | — |
| canyon | 1 274 | — | — | — | — |
| cascade | 1 174 | 361 | 1 277 | 1 209 | 421 |
| lac | 965 | 773 | 2 138 | 3 068 | 1 190 |
| chateau | 810 | 910 | 4 154 | 2 830 | 7 |
| cite-caractere | 380 | 36 | 389 | 101 | 22 |
| cathedrale | 198 | — | — | — | 18 |
| randonnee | 135 | 24 | 23 | 25 | 26 |
| via-ferrata | 133 | 89 | 284 | 143 | 3 |
| camping | — | 519 | 2 272 | 1 627 | 1 184 |
| **Total** | **182 829** | **29 715** | **118 688** | **89 522** | **10 782** |

Poids : FR points 7,9 Mo, toilettes 14,1 Mo, eau 12,3 Mo, grottes 24,7 Mo, culture 2,8 Mo · CH 2,5 + 1,4 + 4,0 Mo · IT 13,1 + 2,1 + 17,7 Mo · ES 9,2 + 1,5 + 13,5 Mo · NZ 1,9 + 1,0 + 0,4 Mo · tracés : gr 2,0 Mo, randos FR 205 Ko, great-walks 1,2 Mo, canyons-traces 44 Ko, randos CH/IT/ES/NZ 32/33/42/246 Ko.

## Anomalies

### Bloquant — AUCUNE

### À corriger

**A1. 67 vignettes Wikimedia à taille non normalisée → images CASSÉES (HTTP 400 vérifié en direct).**
Wikimedia n'accepte plus que les tailles normalisées (250/500/960/1280… — cf. piège documenté dans CLAUDE.md) ; les URLs en 280–800 px renvoient `400 Use thumbnail sizes listed`. Test HEAD : 800px → 400, 450px → 400, 250px → 200 (OK).
- `data/ch/points.geojson` : **61 photos** — 47×800px + 400/450/539/682/749px, surtout les châteaux : ch-chat-0009, -0011, -0014, -0039, -0051, -0115, -0127, -0131, -0183, -0193, -0229, -0357, -0386, -0390, -0416, -0427, -0447, -0453, -0459, -0460, -0461, -0483, -0491, -0589, -0609, -0615, -0617, -0625, -0633, -0639, -0695, -0738, -0739, -0784, -0788, -0802, -0809, -0826, -0829, -0830, -0838, -0857, -0877, -0892 ; ch-mus-0016, -0042, -0080, -0121, -0349, -0428, -0447, -0481, -0490, -0688 ; ch-ref-0398, -0699 ; ch-lac-0563, -0575, -0767.
- `data/culture.geojson` : **5 photos** — cult-0561 (640px), cult-3287 (518px), cult-3632 (800px), cult-3710 (320px), cult-4552 (800px).
- `data/it/points.geojson` : **1 photo** — it-chat-1563 (280px).
- (ch-chat-0504 en 250px : taille normalisée, fonctionne — rien à faire.)
Remède : rejouer la méthode de `tools/agrandir_photos.py` (réécriture vers 500/960 avec HEAD de vérification) sur ces 67 ids.

**A2. 2 liens cassés + 1 négligé.**
- `es-mus-3451` (Museo del Arroz, Valence) : `https:// museodelarrozdevalencia.com` — espace après le schéma, lien mort.
- `nz-cult-0198` (Pātaka Art + Museum) : deux URLs concaténées `…pataka.org.nz/; https://poriruacity…` dans un seul champ.
- `cult-2195` (Musée de Béruges) : schéma `httpS://` — fonctionne au navigateur (schéma insensible à la casse) mais à normaliser.
- (`cult-2242` — apostrophe dans l'URL : valide en pratique, faux positif du contrôle.)

**A3. 6 cotations via ferrata hors échelle K (IT/ES).** Le filtre cotation K ne les matche pas → ces points disparaissent dès qu'un filtre K est posé :
- `it-vf-0135` et `it-vf-0265` : cotation `"0"` (déchet OSM, à vider → filtre « Tout »).
- `it-vf-0103` (`B/C`), `it-vf-0118` (`A/B`), `it-vf-0186` (`C`) : échelle autrichienne Schall — à convertir en K (A/B≈K1-2, B/C≈K2-3, C≈K3).
- `es-vf-0002` (`D/E`) : idem (≈K4-5).

**A4. `nz-cath-0016` — St. Joseph's Cathedral, Avarua : hors Nouvelle-Zélande.** lat -21,21 / lon -159,78 = Rarotonga, **Îles Cook** (État associé, pas la NZ). À retirer ou assumer explicitement.

**A5. 2 « musées » douteux aux Kerguelen (TAAF).** `cult-0115` « Atelier » et `cult-4731` « Porcherie » à Port-aux-Français (lat -49,55 / lon 69,82). Territoire français, donc coordonnées non fautives, mais des objets nommés « Atelier »/« Porcherie » tagués `tourism=museum` sont très probablement du bruit OSM — à écarter au prochain build culture.

### Cosmétique

- **1 769 descriptions > 400 caractères** dans `data/points.geojson` (1 762 refuges — texte de l'API refuges.info, max 786 car. sur `rf-5013` ; 7 randonnées). Aucun HTML, aucun littéral parasite : simple verbosité, l'affichage est correct.
- **`nz-rando-0010` (Hollyford Track) : `duree_n = 24`** (« ≈ 2 jours »). Hors borne conventionnelle (< 24 h) mais tombe dans le bucket « > 6 h » (sans max) → le filtre fonctionne. À garder en tête si un bucket max apparaît un jour.
- **4 lacs FR à altitude négative** : lac-0044 Étang de Citis (-10 m), lac-0085 Étang de Lavalduc (-10 m), lac-0105 Étang d'Engrenier (-9 m), lac-0157 Étang du Pourra (-4 m) — étangs de la région de Fos/Istres réellement sous le niveau de la mer. **Légitime, aucune action.**
- **`cult-2721` Musée Saint-Pierre-Chanel** (lat -14,30 / lon -178,09) : Futuna, territoire français — faux positif des bornes de contrôle, aucune action.
- **`es-rand-0007` (Congost de Mont-rebei) : tracé en 3 LineString** (82 + 3 + 5 sommets — reprise de la relation OSM). L'app dessine tous les morceaux (`getTraceRando` renvoie un tableau) donc rien de cassé, mais les 2 fragments de 3 et 5 sommets sont des résidus à nettoyer à l'occasion (ils partent aussi dans le GPX).

### Exclusions assumées (non signalées, conformément aux consignes)

DOM français hors métropole (légitimes, bornes DOM incluses au contrôle) ; points étrangers de `data/toilettes.geojson` France (chantier séparé en cours) ; photos absentes (limite honnête des sources libres).

## Méthode

Deux scripts Python en lecture seule dans le scratchpad de session : `qc_donnees.py` (17 fichiers de points + 8 fichiers de tracés : unicité globale des ids, bornes par pays avec boîtes métropole+DOM/CH/IT/ES+Canaries/NZ+Chatham, CSP photos `upload.wikimedia.org`, tailles `/NNNpx-`, URLs/labels de links, champs `_n`, potabilité, cotations, descriptions, références de tracés, échantillons aléatoires seed 20260717) et `qc_approfondi.py` (élucidation de chaque anomalie : test HEAD réel des vignettes sur Wikimedia, distribution des cotations et de la potabilité par pays, identification nominative des points signalés). Double exécution → résultats identiques.
