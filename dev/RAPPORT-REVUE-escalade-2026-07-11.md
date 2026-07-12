# Rapport de revue — escalade

Date : 2026-07-11/12 · Session principale.

## Constat de départ (l'utilisateur avait raison)

Un premier passage OSM (recalage GPS seul) a corrigé 251 positions mais **n'avait pas rempli les fiches vides**. Capture à l'appui, l'utilisateur a montré un point (« Saint Simon de Bordes ») avec **0 voie, aucune cotation, aucune info**. Audit honnête : sur 2 033 sites (source XLSX FFME, tous au centroïde de commune), **64 % sans longueur de corde, 63 % sans approche, 97 % sans vrai lien, 99 % sans photo, 9 % totalement vides**.

## La bonne source : Camp to Camp (camptocamp.org)

API publique, **5 306 sites d'escalade** (`climbing_outdoor`), licence CC-BY-SA → **4 427 nommés en France**, avec coordonnées précises, cotations, type de roche, hauteur, orientation. Bien meilleure qu'OSM pour l'escalade. Constat clé : **82 % de nos points ont un site C2C à < 5 km, 93 % à < 10 km** — la couverture existait, c'est le rapprochement par nom qui échouait (C2C ajoute des suffixes : « Saint-Simon-de-Bordes - Les Roches »).

## Résultat

### Appariement et recalage — 1 519 points (74 %)
- **544 par nom** (exact ou notre nom ⊂ nom C2C) + **975 par proximité** (site C2C réel le plus proche du centroïde, ≤ 6 km, un-pour-un).
- Chacun : **coordonnées réelles** C2C, **lien Camp to Camp direct** (fini la recherche Google), altitude, et **mention « Position au centre de la commune » retirée** (devenue fausse).

### Enrichissement des fiches (détail C2C) — 1 519 points
- Champs vides remplis (jamais d'écrasement des données FFME correctes) : **+108 cotations, +129 nombres de voies** (les « 0 voie » corrigés), **+1 297 types de roche, +986 hauteurs, +1 130 orientations**.
- Résultat global : cotation **92 %**, voies renseignées **91 %**, roche **63 %**, hauteur **48 %**.
- Nouveaux champs de fiche : « Roche », « Hauteur » (`js/config/themes.js`).
- **Exemple Saint-Simon-de-Bordes** : 0 voie/rien → **17 voies, 4c à 8a, calcaire, 11 m**, position sur la falaise, lien C2C direct.

### Spots manquants — +275 sites (2 033 → 2 308)
Sites C2C à > 3 km de tout point existant, **confirmés en France** (reverse-geocoding geo.api.gouv.fr → donne aussi la commune), avec **contenu réel** (≥ 3 voies ou cotation), dédoublonnés. Ex. : Aubazine (100 voies), Audun-le-Tiche (150 voies), Petite Raille/Abondance (31 voies). Ids neufs `esc-2356`…, chacun avec commune, cotation, voies, roche et lien C2C.

## Limites honnêtes / reste à faire

- **~514 points** sans site C2C à < 6 km (sites ruraux/mineurs) restent au centroïde de commune, avec commune + lien de recherche C2C. Recalage impossible automatiquement.
- **Photos** : toujours quasi absentes (C2C héberge ses images hors Wikimedia → bloquées par la CSP). Limite structurelle.
- La longueur de corde (FFME) n'est pas dans C2C : les 64 % sans corde le restent (mais gagnent cotation/roche/hauteur).
- L'appariement par proximité (975) peut, dans une commune à plusieurs sites, viser un site voisin plutôt que l'exact FFME — mais c'est un site RÉEL documenté à < 6 km, avec lien C2C pour tout voir : très supérieur au marqueur vide au centre du bourg.

## Scripts livrés

`recolter_escalade_c2c.py` (récolte API C2C), `revue_escalade_c2c.py` (appariement nom+proximité, recalage, lien), `enrichir_escalade_c2c.py` (détail : cotation/voies/roche/hauteur/orientation), `ajouter_escalade_c2c.py` (manquants France + contenu). Le passage OSM initial (`recolter_escalade_osm.py`, `revue_escalade.py`) reste comme repli. Caches C2C gitignorés.

## Bilan des catégories revues

| Catégorie | Points | GPS recalés | Fiches enrichies | Ajouts |
|---|--:|--:|--:|--:|
| via-ferrata | 126 → 133 | 44 | — | +7 |
| **escalade** | **2 033 → 2 308** | **1 519** (C2C) | **1 519** (cotation/voies/roche/hauteur) | **+275** |
