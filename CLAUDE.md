# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Carte Outdoor : PWA statique de cartographie de points d'intérêt outdoor (via ferrata, refuges, escalade, châteaux, cités de caractère, GR). **Vanilla JS + modules ES, aucun build, aucune dépendance npm** — les librairies (Leaflet, markercluster, togeojson, fflate) sont vendorées dans `vendor/`. Interface, commentaires et documentation en **français**. ~7 400 points par défaut + 190 tracés GR + ~66 500 toilettes (fichier séparé `data/toilettes.geojson`, chargé à la demande, non pré-caché).

**En ligne** : https://applicationcarteoutdoor-ui.github.io/carte-outdoor/ (GitHub Pages, dépôt public `applicationcarteoutdoor-ui/carte-outdoor`, branche `main`). `Donné/` (sources perso, 117 Mo) et les caches de `tools/` sont exclus par `.gitignore`. **C'est l'utilisateur qui pousse (`git push`), jamais l'agent** : proposer le workflow, ne pas l'exécuter. Workflow de mise à jour : finaliser → bump `VERSION` dans `sw.js` → `git add -A && git commit && git push` → Pages redéploie (~1 min) → les visiteurs reçoivent la nouvelle version au chargement suivant.

## Commandes

```bash
# Serveur de développement (obligatoire : les modules ES exigent HTTP)
python tools/dev_server.py 8125

# Régénérer les données depuis Donné/ (one-shot, reprend sur caches)
python tools/build_data.py
```

Pas de tests automatisés ni de linter. La vérification se fait dans le navigateur (les modules de la page sont importables depuis la console : `await import('./js/map.js')` renvoie les instances vivantes de l'application).

## Règles critiques

- **Incrémenter `VERSION` dans `sw.js` après toute modification de fichiers de l'app** — mais seulement quand l'ensemble est finalisé : une version bumpée en cours de chantier fige un état intermédiaire dans le cache des visiteurs (déjà causé des « bugs » fantômes). Depuis la v9, `app.js` recharge automatiquement la page au `controllerchange` : la nouvelle version s'applique au premier chargement. Depuis la v31, `app.js` appelle aussi `reg.update()` au retour au premier plan (`visibilitychange`) et toutes les heures → une PWA installée restée ouverte se met à jour seule.
- **Pré-cache du shell avec `fetch(new Request(url, { cache: "reload" }))`, jamais `cache.addAll()`** : `addAll` passe par le cache HTTP du navigateur, donc un fichier dont le CONTENU change sans que le NOM change (ex. `img/carnet-*.jpg` remplacées) était recopié PÉRIMÉ dans le nouveau cache — la VERSION montait mais les pixels restaient anciens (bug « couverture avec le bureau » v24→v26, plusieurs versions à diagnostiquer).
- **Jamais de `confirm()`/`alert()` natifs** : silencieusement ignorés dans certains contextes (PWA installée, dialogues bloqués) — utiliser `confirmer()` de `js/import-export.js` (dialogue intégré).
- En dev, le service worker sert son pré-cache : pour tester une modification, désinscrire le SW + vider les caches dans le navigateur (ou mode navigation privée). `dev_server.py` envoie `no-store` mais ne neutralise pas le SW.
- Les **ids de catégorie** (`themes.js`) sont stables et stockés dans les données des points : ne jamais les renommer. Seul le `label` est modifiable.
- `dev_server.py` doit rester sur `ThreadingHTTPServer` (un serveur mono-thread bloque le chargement : le navigateur ouvre des connexions parallèles).

## Architecture

`js/app.js` est le seul propriétaire de l'état partagé (`state` : points, statuts, catégories cochées, sélections de filtres) et câble tous les modules par callbacks à l'init. Les modules ne s'importent presque pas entre eux ; le flux est : interaction → callback vers app.js → mutation de `state` → `rafraichir()` (re-rend panneau gauche + filtres + marqueurs + persiste les prefs).

- **`js/config/themes.js`** — LE point de configuration : catégories (id stable, label, couleurs, icône), champs de fiche, et **filtres déclaratifs** (types `tokens`/`prefix`/`contains`/`value`/`bucket`, évalués par `passeFiltre()` dans app.js ; les buckets lisent les champs numériques suffixés `_n` des `details`). Trois couches de catégories : `THEMES` (base), `customThemes` (créées par l'utilisateur, enregistrées via `registerCustomThemes()` au boot, supprimables), `overrides` (personnalisation label/couleurs/icône, appliquée par `getTheme()`). Toujours passer par `getTheme()`/`allThemes()` pour l'affichage.
- **`js/storage.js`** — toute la persistance, API volontairement async pour pouvoir brancher un back-end plus tard sans toucher au reste. localStorage (prefs, statuts, overrides, customThemes, idées) ; IndexedDB v3 (`DB_VERSION = 3`, stores : `userPoints`, `tracks`, `journal` = carnet par point avec photos, `carnet` = thème + images du grimoire dont le logo). Protection anti-effacement : `app.js` demande `navigator.storage.persist()` et rappelle une sauvegarde (export) au bout de 14 j sans export ; `dernierExport`/`dernierRappelSauvegarde` sont des prefs.
- **`js/map.js`** — performance : les marqueurs sont créés une fois et mis en cache (`cache: Map<id>`), les instances de divIcon sont partagées (une par combinaison thème/statut/sélection), l'icône n'est régénérée que si statut/thème/sélection change ; la **sélection fait partie de l'icône** (classe `pin-selected`) pour survivre aux reconstructions du clustering. Au-delà de 4 000 points, `setPoints` ajoute par tranches **triées par distance au centre** (la zone regardée s'affiche en ~1 s, le reste en fond) — **ne pas revenir au `chunkedLoading` de markercluster : il n'affiche RIEN avant la fin du lot complet** (~25 s pour 66 000 points). Attention : `map.getCenter()` pendant un `setView` animé renvoie l'ANCIEN centre (d'où `animate: false` dans `montrerRayon`). La carte est en `preferCanvas` : les polylignes (GR, traces) ne sont **pas** des `<path>` SVG — les tester via `map.eachLayer`, pas par sélecteur CSS. Surcouches chargées à la demande : `data/gr.geojson` (2 Mo) et `data/toilettes.geojson` (14 Mo).
- **`js/import-export.js`** — import unifié (un seul `<input>` `#file-import`) : tout est converti en GeoJSON (togeojson pour GPX/KML, fflate pour KMZ), puis routé — LineStrings → traces (`gpx.js`), Points → dialogue de validation (erreurs listées par ligne, choix de catégorie si absente). L'export `formatVersion: 2` embarque points + statuts + carnet + customThemes. Formats documentés dans `docs/FORMAT-IMPORT.md`.
- **`js/carnet.js`** — « le Carnet », grimoire de sorties : couverture + pages en images de fond (`img/carnet-couverture.jpg`, `img/carnet-page-1..4.jpg`, pré-cachées), historique manuscrit par lieu. Personnalisable via un dialogue de thème (grimoire / voyage / nuit) et un **logo utilisateur** rond incrusté sur la plaque de couverture (`.couv-logo`, positionné en % pour masquer le symbole « ? » de l'image). Réglages persistés dans le store IndexedDB `carnet`.
- **`js/config/glossaire.js`** — définitions des acronymes (cotations…) ; `glossaireHTML()` échappe et enveloppe automatiquement les termes connus d'une infobulle. Une entrée à ajouter suffit pour un nouvel acronyme.

## Pipeline de données (`tools/`)

`build_data.py` + `enrichissements.py` génèrent `data/points.geojson` et `data/gr.geojson` depuis `Donné/` et des sources en ligne. **Tout est mis en cache dans `tools/`** (`communes.json`, `refuges-api.json`, `wiki-cache.json`, `alti-cache.json`, `viaferrata-liste.html`, `grgo-index.html`) : relancer le script ne re-télécharge que le manquant.

- Refuges : API refuges.info (`api/bbox…detail=complet`) — le KML de `Donné/Refuge` est obsolète.
- Escalade/châteaux/cités : géocodés au **centroïde de commune** (référentiel geo.api.gouv.fr, rapprochement exact → préfixe → contient, St↔Saint normalisé).
- Wikipédia : **ne pas utiliser l'endpoint de recherche** (rate-limité en rafale et renvoie l'article de la commune) — construire des titres candidats (« Château de X »…) et les vérifier par lots de 50 via `action=query&titles=`, en sauvegardant le cache à chaque tranche (les 429 arrivent par vagues, le retry attend 15-180 s). Les châteaux sans page trouvée basculent dans la catégorie `chateau-a-verifier`.
- Grottes et cathédrales : récolte des arbres de catégories Wikipédia (`recolter_categorie_wikipedia`, sous-catégories suivies seulement si leur nom contient le mot-clé, sinon le parcours dérive hors sujet) puis `prop=coordinates|pageimages` — **`colimit=max` et suivi de `continue` obligatoires**, sinon l'API ne renvoie que 10 coordonnées par réponse (bug déjà rencontré : 80 % des points silencieusement sans coordonnées).
- D+ des GR : service altimétrique IGN (`data.geopf.fr/altimetrie`, POST par lots de 180 points, échantillonnage ~300 m) — c'est une estimation, affichée comme telle.
- Toilettes : API Overpass (`amenity=toilets`, tuiles 3°, nœuds + centres de bâtiments, `access=private/no` écartés) → `data/toilettes.geojson` séparé. Overpass rate-limite fort (429/504) : retries longs, cache sauvegardé seulement si toutes les tuiles réussissent. Le GeoJSON « toilets » fourni dans `Donné/` ne contient QUE des restaurants (mauvais export) — ne pas l'utiliser.
- Les échecs (lieux-dits, communes fusionnées, ~420 sites) sont listés en fin d'exécution ; c'est une limite des données sources, pas un bug.

## Pièges connus de l'environnement de preview

Le proxy du panneau de preview cache agressivement : si des fichiers périmés sont servis malgré `no-store`, **changer le port** dans `.claude/launch.json` (URLs neuves = cache froid). Après un `preview_resize`, la carte Leaflet garde sa taille (pas d'événement resize) → `map.invalidateSize()`, et les captures d'écran deviennent peu fiables → redémarrer le serveur de preview pour un onglet frais.
