# 🏔️ SpotMap (ex-Carte Outdoor)

**➡️ Application en ligne : https://applicationcarteoutdoor-ui.github.io/carte-outdoor/**
(sur téléphone : ouvrez l'URL puis « Ajouter à l'écran d'accueil » pour l'installer)

Application web de carte interactive de points d'intérêt outdoor :
via ferrata (liens directs viaferrata-fr.net), escalade, grottes et
cathédrales (fiches et photos Wikipédia), châteaux, cités de caractère,
refuges (refuges.info), sentiers GR et traces GPX — **7 300+ points**
filtrables par catégorie, statut et critères propres à chaque catégorie
(cotation, altitude, places…). S'y ajoutent **66 000+ toilettes publiques**
(OpenStreetMap), chargées à la demande, avec un bouton 🏃🚻 qui affiche
celles à moins de 1 km de votre position.

- **100 % statique** : aucun serveur, aucune base de données, aucune clé API.
- **Hors-ligne** : l'application, les données et les zones de carte déjà
  consultées restent disponibles sans réseau (PWA installable).
- **Données locales** : suivi, points importés, personnalisation des
  catégories, carnet, idées et traces restent dans le navigateur
  (localStorage + IndexedDB).

## Lancer en local

N'ouvrez pas `index.html` directement (les modules ES exigent HTTP) :

```bash
python tools/dev_server.py 8124
# puis http://localhost:8124
```

(`dev_server.py` = serveur statique multi-thread qui désactive tout cache —
indispensable pour voir vos modifications immédiatement pendant le
développement. En production c'est le service worker qui gère le cache.)

## Prévisualiser PC + mobile côte à côte

Pendant que le serveur local tourne : http://localhost:8124/dev/apercu.html
(rendu bureau 1280 px et rendu téléphone au choix, bouton de rechargement
qui vide le cache du service worker).

## Mettre à jour le site en ligne

Le site est servi par GitHub Pages depuis la branche `main` du dépôt
[applicationcarteoutdoor-ui/carte-outdoor](https://github.com/applicationcarteoutdoor-ui/carte-outdoor) :

```bash
# 1. Une fois les modifications FINALISÉES : incrémenter VERSION dans sw.js
# 2. Puis :
git add -A
git commit -m "Description de la mise à jour"
git push
# Pages redéploie en ~1 minute ; les visiteurs reçoivent la nouvelle
# version automatiquement (rechargement au changement de service worker).
```

> **Ne poussez jamais sans avoir incrémenté `VERSION` dans `sw.js`** quand des
> fichiers de l'application ont changé, sinon les visiteurs gardent l'ancienne
> version en cache. (`Donné/` et les caches de `tools/` ne sont pas versionnés.)

## Interface

- **Panneau gauche** (fixe sur grand écran, tiroir via le bouton ☰ flottant
  sur mobile) : la **recherche** au-dessus, puis les catégories **cochables**
  — plusieurs à la fois — avec compteurs, les statuts (**★ À faire, ✓ Fait,
  ♥ Favoris**, cochables comme des catégories), les **Sentiers GR** et
  **Mes traces GPX** (volet dépliable : liste, profil, import). ✎
  personnalise nom/couleurs/icône (l'identifiant technique reste stable).
  En bas : **＋ Importer une catégorie** et **⬇ Exporter**.
- **Panneau droit (filtres)** : apparaît dès qu'une catégorie cochée a des
  filtres. Nom du filtre au-dessus, pastilles cliquables, « Tout » par
  défaut. Filtres actuels : cotation (via ferrata), type de site et nombre
  de voies (escalade), **chauffage (poêle/cheminée/aucun)** / places /
  altitude / état (refuge).
- **Boutons flottants** : **➕ ajouter un point** (gros bouton vert : cliquez
  la carte, choisissez ou créez une catégorie à la volée), 💡 boîte à idées,
  🎓 revoir le tuto, ◎ ma position.
- **GR** : cliquer un tracé le met en **surbrillance orange** et affiche nom,
  distance, **D+ estimé** (altimétrie IGN) et liens (gr-go.fr, Wikipédia,
  gr-infos.com).
- **Tuto** : visite guidée automatique à la première connexion, skippable.
- **Infobulles** : survolez une cotation (PD, AD, D…) — définitions dans
  `js/config/glossaire.js`.
- **Fiche d'un point** : itinéraire Google Maps/Waze, **liens et photos
  Wikipédia** (châteaux, cités), liens topos (escalade), statuts ★/✓/♥,
  carnet (notes + photos datées, redimensionnées à 1024 px).
- **Première connexion** : seules les cités de caractère sont affichées.

## Structure du code

```
index.html                 Coquille de l'interface
css/styles.css             Styles (mobile d'abord, clair épuré)
js/app.js                  Point d'entrée : état global + câblage des modules
js/config/themes.js        ★ Catégories (id STABLE, label, couleurs, icône, champs, FILTRES)
js/config/glossaire.js     ★ Définitions des acronymes (infobulles)
js/map.js                  Carte Leaflet : marqueurs en cache + clustering chunké, GR, géoloc
js/sidebar.js              Panneau gauche : catégories cochables + éditeur + traces
js/filters.js              Panneau droit : filtres par catégorie + suivi
js/details.js              Fiche détaillée + itinéraires + carnet
js/import-export.js        Import unifié multi-formats + export de sauvegarde
js/gpx.js                  Traces : stats, affichage, profil altimétrique
js/tuto.js                 Visite guidée (étapes déclaratives)
js/ideas.js                Boîte à idées
js/storage.js              Persistance (localStorage + IndexedDB), API async
sw.js                      Service worker — VERSION à incrémenter
data/points.geojson        4 460 points par défaut
data/gr.geojson            190 GR simplifiés (chargés à la demande)
tools/build_data.py        Génération des données depuis Donné/ (géocodage inclus)
tools/dev_server.py        Serveur de développement sans cache
docs/FORMAT-IMPORT.md      Formats d'import documentés
vendor/                    Leaflet, markercluster, togeojson, fflate (vendorés)
```

## Ajouter une catégorie ou un filtre

Dans `js/config/themes.js` : une entrée du tableau `THEMES` déclare id
(stable, ne JAMAIS le changer), label, couleurs, icône, champs de fiche et
**filtres** — 4 types : `tokens` (cotations), `prefix`, `value`, `bucket`
(tranches numériques sur les champs `*_n`). Panneau gauche, filtres,
fiche, import et éditeur les prennent en compte automatiquement.

Pour une nouvelle infobulle d'acronyme : une ligne dans
`js/config/glossaire.js`.

## Données

`tools/build_data.py` (relançable, tout est mis en cache dans `tools/`)
génère les données et les **enrichit en ligne** :

| Catégorie | Source | Enrichissement |
|---|---|---|
| Via ferrata (126) | CSV + scrape viaferrata-fr.net | liens directs vers les fiches |
| Refuge (~3 500) | **API refuges.info** (plus complet que le KML initial) | chauffage, eau, latrines, couvertures, remarques, accès |
| Escalade (2 033) | xlsx, centroïde de commune | liens camptocamp + topos |
| Château (810) | xlsx, centroïde de commune | **lien + photo Wikipédia** (recherche validée) |
| Cité de caractère (211) | xlsx, centroïde de commune | **lien + photo Wikipédia** |
| Sentiers GR (190) | KML 52 Mo → simplifié 2 Mo | distance calculée, **D+ estimé (altimétrie IGN)**, liens gr-go.fr / Wikipédia / gr-infos |

Géocodage par les référentiels officiels (geo.api.gouv.fr) : précision
« au bourg » pour escalade/châteaux/cités. Les échecs (~420 lieux-dits ou
communes fusionnées) sont listés à l'exécution. Caches : `communes.json`,
`departements.json`, `refuges-api.json`, `wiki-cache.json`, `alti-cache.json`.

## Fonds de carte

OpenStreetMap, OpenTopoMap, Plan IGN (Géoplateforme), satellite Esri —
gratuits, sans clé. Ajout : `creerFondsDeCarte()` dans `js/map.js` +
`HOTES_TUILES` dans `sw.js`.
