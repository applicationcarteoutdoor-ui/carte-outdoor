# Rapport de revue — canyon / canyonisme (nouvelle catégorie)

Date : 2026-07-13 · Session principale. Ajout d'une **nouvelle catégorie
« Canyon »** (descentes de canyon) sur demande utilisateur : « rajouter les
spots de canyoning », avec si possible longueur de corde, site web, temps
d'aller/retour et le tracé.

## Recherche des sources (workflow multi-agents, licences d'abord)

Contrairement à l'escalade, **il n'existe aucun équivalent open-licence de Camp
to Camp pour le canyoning** (C2C n'a pas d'activité « canyoning » : filtre API
ignoré, vérifié). Bilan des sources :

| Source | Licence | Apport | Verdict |
|---|---|---|---|
| **RES / Data ES** (Ministère des Sports) | **Licence Ouverte Etalab 2.0** | type d'équipement « Canyon », ~1 298 sites, coords + longueur + dénivelé + commune | **socle** (compatible store) |
| **OpenStreetMap** (`route=canyoning`) | ODbL | ~32 canyons FR : cotation FFME, plus grand rappel, site web, **tracé** | complément (~2 %) |
| descente-canyon.com | **CC BY-NC-SA** + droit *sui generis* producteur | base la plus riche (corde, temps d'approche/retour) | **écarté** — clause « pas d'usage commercial » incompatible store, extraction massive risquée. On ne scrape pas ; on peut seulement y lier. |
| FFME / canyoning.com | « Reproduction interdite » | — | écarté |
| Wikidata (CC0) | CC0 | ~234 gorges = reliefs, pas des descentes | non substituable |

## Verdict franc sur les 5 champs demandés

- **Position + nom + commune + longueur + dénivelé** : ✅ **~1 274 canyons** (RES).
- **Cotation, plus grand rappel, corde estimée, site web, tracé** : 🟡 **OSM seulement (~27 canyons, ~2 %)**.
- **Temps d'approche et de retour** : 🔴 **IMPOSSIBLES en données libres.** Aucun
  tag OSM, aucun champ RES ; ces valeurs n'existent que dans les topos rédigés
  (descente-canyon, FFME), protégés. Exactement comme la spéléo (« le nombre de
  cordes est dans les topos protégés »). Annoncés comme non disponibles.
- **Corde** : jamais recopiée d'un topo — **estimée** depuis le plus grand rappel
  OSM (`max:abseil`), libellée « estimation », comme la corde de l'escalade.

## Construction

- `tools/recolter_canyon_res.py` — API Opendatasoft `equip_type_name="Canyon"`,
  Licence Ouverte : **1 274 canyons** (24 sans coords écartés), 98 % avec
  longueur, 96 % avec dénivelé. DOM inclus (Réunion 98, Martinique 55).
- `tools/recolter_canyon_osm.py` — Overpass `relation[route=canyoning]` (area
  France + bbox Réunion), `out geom` : **32 canyons**, tracé reconstruit depuis
  la géométrie des ways membres (le cours d'eau = la ligne de descente,
  MultiLineString). *(Piège payé : `out tags geom` est contradictoire → résultat
  vide ; la bonne forme est `out geom`, qui inclut déjà les tags.)*
- `tools/fusion_canyon.py` — socle RES ; rapprochement OSM→RES **conservateur**
  (proximité ≤ 3 km + mots de nom communs, sinon RES unique ≤ 1,2 km) :
  **27 canyons rapprochés/32** (5 OSM sans correspondance RES abandonnés, jamais
  d'attribution douteuse). Ids stables `canyon-0001…canyon-1274`. Écrit les
  features dans `data/points.geojson` + les **27 tracés** dans
  `data/canyons-traces.geojson` (chargé à la demande, hors SHELL du SW).

## Résultat

**Nouvelle catégorie `canyon`** (🪢, teal #0a9396), **1 274 canyons** →
points.geojson passe de 10 670 à **11 944 features**.

- **Fiche** : commune, longueur de la descente, dénivelé, + (si OSM) cotation
  `v#a#III`, plus grand rappel, corde recommandée (estimation), accès. Liens :
  🌐 topo OSM (si présent) + 🔎 recherche « topo, corde & horaires » (là où
  l'utilisateur trouve corde/temps, sans qu'on recopie les topos protégés).
- **Filtres** : Longueur (bucket), Dénivelé (bucket), Accès (libre/réglementé).
- **Tracé** : 27 canyons ont un tracé dessiné sur la carte (teal pointillé,
  suit le cours d'eau), épinglé comme une randonnée (pastille de rappel), avec
  export **📥 GPX**. Mécanisme de tracé rando **généralisé** (rando + canyon)
  dans map.js/app.js/details.js — pas de duplication.
- **Attribution** ajoutée aux Réglages : RES – Ministère des Sports (Licence
  Ouverte 2.0) + OpenStreetMap (ODbL).

## Limites honnêtes annoncées

- **Temps d'approche/retour : absents** (topos protégés) — 0 % en open data.
- **Cotation / rappel / corde / site web / tracé : ~2 %** (frange OSM de 27
  canyons) ; le socle RES livre position + longueur + dénivelé pour les 1 274.
- **Corde : estimation** dérivée du plus grand rappel, jamais un topo recopié.
- **descente-canyon.com** (la base riche) restera hors des données : lien seulement.

## Vérification (navigateur, SW + caches purgés)

- **0 erreur console** ; **tests purs 24/24**.
- Catégorie « 🪢 Canyon 1274 » dans la sidebar (après Escalade).
- Fiche « Ruisseau de Purcaraccia » (Quenza, Corse-du-Sud) : v4a2II, rappel
  45 m, corde ≈ 45 m (estimation), accès libre, bouton GPX, liens OSM + recherche.
- Filtres Longueur/Dénivelé/Accès : 9/9 assertions de bucket/valeur correctes.
- Tracé teal pointillé dessiné le long du cours d'eau, épinglé après fermeture
  de la fiche (pastille), correction du champ interne `acces_v` qui fuitait en fiche.

## Bilan des catégories revues (étape 1)

| Catégorie | Points | Apport principal |
|---|--:|---|
| via-ferrata | 126 → 133 | 44 recalés, +7 |
| escalade | 2 033 → 3 351 | socle RES + faits C2C |
| cascade | 1 133 → 1 174 | +41 outre-mer |
| chateau | 810 | 666 recalés (82 %) |
| lac | 965 | GPS vérifié, +12 photos |
| grotte | 484 → 49 717 | couche spéléo Grottocenter |
| **canyon** | **0 → 1 274** | **nouvelle catégorie : socle RES (Licence Ouverte) + faits/tracé OSM** |
