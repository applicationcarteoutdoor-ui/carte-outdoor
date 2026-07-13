# Rapport de revue — grotte / spéléologie

Date : 2026-07-12 · Session principale. Catégorie **grotte** : de 484 grottes Wikipédia à une **couche spéléo de ~49 700 cavités**.

## Constat de départ

484 grottes issues **uniquement de Wikipédia** (« Catégorie:Grotte en France »), beaucoup d'**abris préhistoriques/archéologiques** (Abri Audi, Castanet…), **aucune donnée technique** (details vide), aucun filtre. Le vrai monde de la spéléologie sportive était absent.

Demande utilisateur : ajouter des grottes de spéléo depuis des sources ouvertes (forums), avec des données techniques — le sport, le nombre de cordes, à combien on descend, présence d'eau (néoprène) — et de nouveaux filtres.

## Recherche des sources (workflow multi-agents, licences d'abord)

| Source | Licence | Apport | Verdict |
|---|---|---|---|
| **Grottocenter** (Wikicaves) | **ODbL** (faits) | API publique sans clé, coords + **profondeur + développement** + isDiving, ~50 000 cavités FR | **socle** |
| OpenStreetMap `cave_entrance` | ODbL | ~10 770 positions, pas de données techniques | complément |
| BRGM BDCavités | Licence Ouverte | 174 500 cavités mais surtout carrières/effondrements, orienté risque | écarté |
| Wikidata | CC0 | ~769 grottes, photos/type des classiques ; profondeur/longueur quasi vides | complément |

**Honnêteté livrée d'emblée** : le **nombre de cordes** et la **hauteur des puits** sont dans les topos d'équipement (droit d'auteur) — **impossibles en open data**, exactement comme on n'a pas recopié les topos d'escalade. La présence d'eau se réduit à un signal (type hydrologique / siphon), pas au détail néoprène.

**Éthique** : la communauté spéléo (FFS) et Grottocenter protègent volontairement certaines localisations (karst, chauves-souris, sécurité). L'utilisateur a **choisi le périmètre exhaustif** en connaissance de cause. Garde-fous conservés (respect des signaux des données, pas une censure) : l'endpoint géo de Grottocenter **exclut déjà les entrées masquées** (sans coordonnées publiques) ; **avertissement de sécurité** dans le dialogue d'activation et dans chaque fiche ; attribution ODbL + partage à l'identique dans les Réglages.

## Récolte et construction

- `tools/recolter_grottes_grottocenter.py` — endpoint carte `GET /geoloc/entrances` (bbox), **75 597 entrées** France + DOM en quelques appels (coords, nom, profondeur, développement, commune, région).
- **Filtre France** (`construire_grottes.py`) : la bbox mord sur l'Italie/Espagne/Suisse/Belgique → filtrage par **région administrative** (whitelist FR) + géocodage inverse des sans-région → **49 546 cavités françaises** (26 051 étrangères écartées).
- **Détection type / progression / eau par le NOM** (fait linguistique) : *Gouffre/aven* (aven, gouffre, scialet, igue, puits, tanne, diaclase → **verticale à cordes**), *Grotte* (grotte, baume, cova, porche → **horizontale**), *Source/résurgence* (source, perte, résurgence, event, ruisseau → **eau active**), *Cavité* (reste). Profondeur ≥ 30 m sans mot horizontal → verticale.
- **Fusion des 484 grottes Wikipédia** (id `grot-XXXX` **stables**, photos/liens conservés) enrichies par les faits Grottocenter proches (< 300 m) — ex. **Abîme de Bramabiau** : 0 donnée → gouffre, **87 m / 10 km, verticale**, lien Grottocenter. Nouvelles entrées : id **stable `grot-g{id}`** (idempotent). Faits seulement ; **descriptions/topos/photos Grottocenter NON récupérés** (protégés) — seul le lien retour.

## Résultat — data/grottes.geojson (couche lourde, 24,7 Mo, ~6 Mo gzippé)

**484 → 49 717 grottes.** Répartition : Grotte 17 111 · Gouffre/aven 14 368 · Source/résurgence 6 498 · Cavité 11 740.
Couverture : **profondeur 35 %** (17 400), **développement 28 %** (14 000), **eau active 14 %** (7 257), Référencé 40 %.

**Architecture** : nouvelle **couche lourde à la demande** (modèle `COUCHES_LOURDES` comme eau/toilettes) — fichier séparé non pré-caché, chargé à la première activation via un **dialogue d'avertissement** (Retour / « à moins de 1 km » / Valider), compteur « … » tant que non chargée. La catégorie n'est plus dans `points.geojson` (retirée) ni cochée par défaut.

**6 nouveaux filtres** (themes.js) — tous **réellement alimentés** :
- **Type** (Grotte / Gouffre-aven / Source-résurgence / Cavité)
- **Progression** (Horizontale / Verticale à cordes / Non précisé)
- **Profondeur** (bucket : <30 / 30-100 / 100-300 / >300 m — **661 gouffres > 300 m**)
- **Développement** (bucket : <500 m / 0,5-2 km / 2-10 km / >10 km)
- **Présence d'eau** (Actif / Non renseigné)
- **Fiche** (Référencé / À vérifier)

## Limites honnêtes annoncées

- **Nombre de cordes / hauteur des puits : absents** (topos protégés) — au mieux le lien Grottocenter.
- **Eau** : type hydrologique déduit du nom (source/résurgence/perte), pas le détail actif-fossile ni le besoin de néoprène.
- **Profondeur/développement : ~1/3 des cavités** (les autres n'ont pas la donnée dans Grottocenter).
- **Type « Cavité »** (24 %) : noms sans mot-clé exploitable (dolines, codes de cadastre, noms propres).
- Non-exhaustif : Grottocenter publie ~50 000 entrées FR ; le cadastre FFS (fermé) en recense davantage — l'écart est volontaire (secret des cavités).

## Vérification

App rechargée (SW + caches purgés) : **0 erreur console**, 24 tests purs OK. Activation grotte → dialogue → chargement des **49 717 grottes**, marqueurs clusterisés (Vercors), filtres discriminant correctement (Gouffres 14 368, >300 m 661, actifs 7 257), fiche Abîme de Bramabiau complète (87 m / 10 km / verticale / lien Grottocenter). `sw.js` v58, grottes.geojson hors du SHELL.

## Bilan des catégories revues (étape 1)

| Catégorie | Points | Apport principal |
|---|--:|---|
| via-ferrata | 126 → 133 | 44 recalés, +7 |
| escalade | 2 033 → 3 351 | socle RES + faits C2C |
| cascade | 1 133 → 1 174 | +41 outre-mer |
| chateau | 810 | 666 recalés (82 %), 32 liens erronés corrigés |
| lac | 965 | GPS vérifié, +12 photos |
| **grotte** | **484 → 49 717** | **couche spéléo Grottocenter (ODbL) : profondeur/développement/type/eau, 6 filtres** |
