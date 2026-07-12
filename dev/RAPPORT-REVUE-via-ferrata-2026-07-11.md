# Rapport de revue — via-ferrata (catégorie PILOTE)

Date : 2026-07-11 · Revue lancée par la session principale (l'agent enrichisseur a produit le diagnostic puis a calé sur des pannes d'environnement — stall watchdog, puis erreur SSL — la session principale a repris la phase d'écriture).

## Sources croisées

- **viaferrata-fr.net** (cache `tools/viaferrata-liste.html`) : liste de référence des VF françaises → **186 fiches** (nom, commune, département, cotation, année, fermetures). Pas de coordonnées.
- **OpenStreetMap / Overpass** (`highway=via_ferrata`, cache `tools/vf-osm-brut.json`, 1 667 segments) → clusterisés en **191 sites distincts** (169 nommés), avec coordonnées réelles, échelle K, tyroliennes, liens.
- Notre base : **126 via ferrata** au départ (ids `vf-001`…`vf-126`).

## Problème principal trouvé : GPS au centroïde de commune

Nos VF avaient été géocodées au **centre de la commune**, pas sur la falaise. Mesuré contre OSM : **91 de nos 126 points étaient à > 500 m** du site réel (jusqu'à 5–57 km).

### Recalage GPS — **44 points corrigés** (règle conservatrice)

Un point n'est recalé QUE si le rapprochement est sûr :
- **35 points** déjà à < 500 m d'un site OSM → laissés tels quels (bien placés) ;
- **44 recalés** sur le site OSM réel, selon deux règles à haute confiance :
  1. un **seul** site OSM VF dans un rayon de 12 km, non revendiqué par un autre de nos points (les VF sont espacées d'~50 km : un site unique à portée = quasi certain) ;
  2. sinon, désambiguïsation par le **nom** (ex. « Via Ferrata de Tende » pour notre « Via ferrata de Tende »).
  Exemples vérifiés : Millau → Boffi (+5,3 km), Céüse → Céüse, Mazamet → Mazamet, Beaufort → Roc du Vent, Roubion → Balma Negra.
- **47 points laissés « à vérifier manuellement »** (aucun recalage automatique) : soit OSM n'a pas le site à portée (Moltifao 57 km, Saint-Pé-d'Ardet 23 km, Enchastrayes 16 km), soit **plusieurs VF voisines** rendent le choix ambigu (massifs denses : Chamonix, Serre Chevalier, Courchevel, La Clusaz, Vanoise…). **Un recalage sur la mauvaise falaise étant pire que pas de recalage, on s'abstient et on liste.**

## Spots manquants : **+7 via ferrata ajoutées** (vf-127…vf-133)

Sites OSM nommés situés à > 12 km de tout point existant ET **croisés avec une fiche viaferrata-fr.net non couverte** (double accord : coordonnées OSM + commune/cotation de la référence). Via-corda, « secteurs/variantes » et VF fermées écartés.

| id | Commune | Cotation | VF |
|---|---|---|---|
| vf-127 | Bessans (73) | D | Andagne |
| vf-128 | Col du Rousset (26) | D/TD | Chironne |
| vf-129 | Mont-Dore (63) | PD à D | Le Capucin |
| vf-130 | Prads-Haute-Bléone (04) | AD+/D | Falaise de Meichira |
| vf-131 | Saint-Julien-en-Genevois (74) | D | Jacques Révaclier |
| vf-132 | Saint-Martial-Entraygues (19) | F à D | Dordogne |
| vf-133 | Servant (63) | PD/AD | Gorges de la Sioule |

Total via-ferrata : **126 → 133**.

## Limites honnêtes / reste à faire

- **47 points encore au centroïde de commune** : recalage manuel nécessaire (OSM absent ou ambigu). Liste complète dans la sortie de `tools/recaler_via_ferrata.py`. Piste : reverse-geocoding + choix humain massif par massif.
- Quelques VF réelles NON ajoutées faute de rapprochement de nom certain (Le Regardoir/Vouglans, Roc del Gorb/Bor-et-Bar) — à ajouter à la main.
- VF **fermées** signalées par viaferrata-fr.net non ajoutées (Crolles « vire des lavandières » et « grand dièdre ») — volontaire.
- **Photos** : toujours 0 % (les photos libres de via ferrata sur upload.wikimedia.org sont rares) — limite assumée, pas un échec.
- Les cotations/tyroliennes existantes n'ont PAS été écrasées (elles venaient déjà de viaferrata-fr.net) ; seules les coordonnées ont bougé et 7 fiches ont été créées.

## Méthode réutilisable (pour escalade, cascades, châteaux…)

1. **Diagnostic d'abord, écriture ensuite** : parser une source de référence faisant autorité (spécifique à la catégorie) + OSM pour les coordonnées, mesurer les écarts, lister les manquants — SANS rien écrire.
2. **Recalage conservateur** : ne corriger un GPS que sur correspondance certaine (site unique à portée, ou nom concordant) ; tout le reste → « à vérifier manuellement », jamais deviner.
3. **Ajout sur double accord** seulement (deux sources indépendantes concordent).
4. **Ids stables** : jamais renuméroter ; les neufs prolongent la séquence.
5. Un **script qui fait tout d'un coup** puis s'exécute (ne pas micro-déboguer en boucle interactive — cause du stall de l'agent).

## Scripts livrés

`tools/revue_via_ferrata.py` (diagnostic), `tools/recaler_via_ferrata.py` (recalage GPS), `tools/ajouter_via_ferrata.py` (ajout des manquantes). Caches : `tools/viaferrata-liste.html`, `tools/vf-osm-brut.json` (gitignorés).
