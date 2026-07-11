# Rapport d'enrichissement — Points d'eau (fontaines & sources)

Date : 2026-07-11 · Récolte : agent enrichisseur (OSM/Overpass) · Câblage app : session principale
Périmètre validé par l'utilisateur : « eau potable + sources », ville ET montagne.

> Note : l'agent de récolte s'est interrompu (mise en veille sur un moniteur) avant
> d'écrire son rapport ; ce document a été rédigé par la session principale à partir
> des données livrées et vérifiées. Le fichier `data/eau.geojson` est complet et valide.

---

## Résultat

| | |
|---|---|
| **Points d'eau** | **49 531** (`eau-00001` … `eau-49531`) |
| Fichier | `data/eau.geojson` — 9,7 Mo, **séparé et chargé à la demande** (comme les toilettes, non pré-caché) |
| Géométrie | 100 % Points, toutes dans les bornes France + Corse |

### Par type

| Type | Nombre |
|---|---|
| Fontaine (`amenity=drinking_water`) | 26 119 |
| Source (`natural=spring`) | 18 700 |
| Robinet (`man_made=water_tap`) | 2 896 |
| Point d'eau (`amenity=water_point`) | 1 816 |

### Par potabilité

| Potabilité | Nombre | Règle |
|---|---|---|
| 💧 Eau potable | 30 811 | `amenity=drinking_water`/`water_tap`, ou `drinking_water=yes` |
| 🚱 Non potable | 1 157 | `drinking_water=no` |
| ⚠️ Potabilité non garantie | 17 563 | sources sans tag de potabilité — **jamais présumée potable** |

## Source et méthode

- **OpenStreetMap via Overpass** (`tools/recolter_eau.py`) : tuiles de 3° avec filtre d'aire France, retries longs (20/60/120 s — Overpass a fortement throttlé), cache par tuile reprenable. Tags : `amenity=drinking_water`, `man_made=water_tap`, `amenity=water_point`, `natural=spring`. `amenity=fountain` (décoratives) exclu sauf `drinking_water=yes`. `access=private/no` écartés.
- `tools/normaliser_eau.py` pose `details.type` et `details.potabilite` en libellés lisibles — ils servent **à la fois** à l'affichage de la fiche et de valeur aux filtres déclaratifs (même convention que le « Tarif » des toilettes ; les filtres de `js/filtrage.js` lisent dans `details`).

## Intégration dans l'app

- Catégorie `eau` (💧 « Fontaines & sources », `#1a9ec4`) dans `js/config/themes.js`, avec filtres **Potabilité** (Eau potable / Non potable / Potabilité non garantie) et **Type** (Fontaine / Source / Robinet / Point d'eau).
- Chargement à la demande dans `app.js` (`chargerEau`), modèle identique aux toilettes : fichier tiré à la première activation de la catégorie, rechargé au boot si elle était cochée.

## Vérifications

- 49 531 ids uniques, `[lon, lat]` respecté, 0 point hors bornes France+Corse, UTF-8 propre.
- Navigateur (CDP headless, SW purgé) : catégorie chargée (compteur 49 531), filtres Potabilité + Type rendus, fiche d'un point (type + potabilité affichés). `dev/tests.html` : 24/24.
- Filtres contrôlés sur les données réelles : « Eau potable » → 30 811, « Source » → 18 700 (exacts).

## Limites connues

- Couverture OSM inégale selon les régions (le bénévolat cartographie plus les villes et les GR).
- La potabilité des **sources** est presque toujours non renseignée dans OSM → 17 563 points en « non garantie ». C'est un choix de prudence assumé (une source non taguée n'est PAS présumée potable), pas un manque de données à corriger.
- Horaires, gestionnaire, saisonnalité : rarement présents dans OSM, affichés seulement quand ils existent.
