# Rapport de test — Carte Outdoor v41 — 2026-07-06

Testeur : agent « testeur-app » (parcours complet de bout en bout dans le navigateur de preview, service worker désinscrit et caches vidés avant test, viewport bureau 1280×800 puis mobile 375×812).

> **Suivi post-rapport (2026-07-07)** : les 3 bugs de la section 2 ont été **corrigés et re-vérifiés** dans la v41 avant publication — entrée fantôme du carnet (`deleteSortieDuJour` supprime aussi la seed sans date au retrait du statut « fait », les sorties datées anciennes sont conservées), élision « à l'ouest / à l'est », et « sur place » à la place de « 0.0 km ». Les points d'ergonomie (§3) et les idées (§4) restent à arbitrer par l'utilisateur.

## 1. Synthèse

L'application est en très bon état : les ~7 386 points se chargent sans erreur console, tous les parcours critiques (navigation, recherche, statuts, filtres, ajout/suppression de point, carnet, Oracle, import/export, tuto, toilettes, fonds de carte, mode nuit, mobile) fonctionnent. Les nouveautés v41 sont toutes conformes : boule ronde à l'ouverture puis capsule pour les réponses et le panneau des clés, bandeaux « clé API » en haut ET en bas des résultats gratuits, bascule 🧠 IA sans clé qui ouvre le panneau 🔑 (et retour ✨ Gratuit qui le referme), étape Oracle dans le tuto, fermeture au tap sur mobile. **1 bug de données (majeur-mineur, l'entrée fantôme du carnet) et 2 bugs cosmétiques** ont été reproduits ; aucune régression bloquante.

## 2. 🐛 Bugs

| Gravité | Où | Reproduction | Cause probable |
|---|---|---|---|
| **Majeur/mineur** | Carnet — entrée fantôme indélébile par le flux normal | 1) Marquer un point « ✓ Fait » (sortie datée créée). 2) Dans le carnet, supprimer cette sortie avec 🗑 (le point reste « fait »). 3) Rouvrir le carnet : une sortie « seed » (date null) est recréée, affichée « Date inconnue / Faite avant le carnet ». 4) Retirer le statut « ✓ Fait » de la fiche. → La sortie seed **reste** : le carnet affiche toujours « Via ferrata de Ancelle — ✓ Sortie faite — Date inconnue » alors que le point n'est plus marqué fait, sans note ni photo. | `deleteSortieDuJour` (`js/storage.js:118-128`) ne supprime que la sortie datée du jour ; la seed créée par `seedSortiesDepuisStatuts` (`js/storage.js:137-150`, appelée à chaque ouverture par `js/carnet.js:128`) a `date: null` et n'est jamais nettoyée par `js/app.js:257`. Piste : au retrait du statut fait, supprimer aussi `s-seed-<pointId>`. |
| Mineur (cosmétique) | Oracle — texte des distances | Consulter en mode ✨ Gratuit (ex. 74400) : « Via ferrata de Chamonix — à 4.7 km **au ouest** ». Idem « au est ». | `js/oracle.js:666` : `à ${km} km au ${direction(...)}` — il faut « à l'ouest » / « à l'est » pour ces deux directions (élision). |
| Mineur (cosmétique) | Oracle — distances nulles | Même consultation : « Brévent (petite falaise) — à **0.0 km** au nord » (×4 pour l'escalade, géocodée au centroïde de commune). | `kmLisible` (`js/oracle.js:634`) affiche `toFixed(1)` même sous 100 m. Piste : « sur place » ou « < 1 km », et omettre la direction quand d ≈ 0. |

### À vérifier (non confirmé comme bug)

- **Panneau latéral mobile** : pendant les transitions, `getBoundingClientRect()` renvoyait des positions incohérentes (panneau « ouvert » mesuré hors écran). Après stabilisation, les états ouvert/fermé sont corrects (classe `open`, `transform: none` ↔ `-260px`, `visibility`). Tout indique un lag de rendu du preview (documenté dans CLAUDE.md), pas un bug de l'app — à confirmer sur un vrai mobile.
- **Store IndexedDB `carnet`** : contient un enregistrement `theme` entièrement par défaut (`{theme:"grimoire", couverture:null, page:null, logo:null}`), peut-être créé à la première ouverture du carnet. Sans conséquence, laissé en place.

## 3. 🎨 Ergonomie (par impact décroissant)

1. **Le mode SUIVI efface la sélection de catégories sans la restaurer.** Cocher ★/✓/♥ vide `activeThemes` (voulu, `js/app.js:777`) mais décocher le statut laisse tout décoché : l'utilisateur qui avait 4 catégories cochées doit tout recocher à la main. Mémoriser la sélection et la restaurer au décochage serait indolore.
2. **Recherche du carnet sans résultat = faux message.** Si la recherche ne matche rien, le livre se referme sur la couverture avec « Votre carnet attend sa première sortie : marquez une activité "✓ Fait" ! » — trompeur quand le carnet contient des entrées. Un « Aucune sortie ne correspond à "xxx" » serait plus juste.
3. **L'entrée fantôme (bug 1) affiche la mention « ✓ Sortie faite »** alors que le point n'est plus marqué fait — incohérence visible même avant correction du bug de fond.
4. **Recherche limitée à 12 résultats sans le dire.** « ferrata » affiche 12 lignes sans indiquer qu'il en existe 126 — un « … et 114 autres » aiderait.
5. **Toilettes : ~15 s de chargement.** Le dialogue d'avertissement (« Beaucoup de points ! ») est bien pensé, mais après « Valider » il n'y a plus d'indicateur pendant le téléchargement/parsing des 14 Mo ; le compteur passe de « … » à 66 584 sans état intermédiaire.

## 4. 💡 Idées d'évolution

1. **« Autour de moi » généralisé** : l'Oracle sait déjà trier tous les points par distance/direction (`sectionCarte`, `js/oracle.js:637`) — proposer un filtre « à moins de X km » de ma position ou d'un point cliqué, pour toutes les catégories (comme le fait déjà le bouton 🚻).
2. **Préparer une étape de GR** : les tracés GR ont un D+ estimé et la carte connaît refuges et toilettes — un clic sur un GR pourrait lister les refuges à moins de 2 km du tracé (bivouac/ravitaillement), très outdoor.
3. **Météo de la fiche** : open-meteo.com est gratuit et sans clé — afficher la météo à 3 jours du point (altitude connue pour les refuges) dans la fiche ou la consultation Oracle.
4. **Statistiques du carnet** : nombre de sorties par an/catégorie, altitudes cumulées des refuges faits — une page « bilan » dans le grimoire, dans l'esprit manuscrit.
5. **Restaurer la sélection au décochage du suivi** (voir ergonomie 1) — quasi une correction, gros gain de confort.

## 5. ✅ Ce qui marche bien

- **v41 conforme sur toute la ligne** : boule ronde à l'ouverture (634×634, `border-radius: 50%`) → capsule 820×688 pour la réponse ; bandeaux 🔑 haut + bas ; IA sans clé → panneau des clés ; retour Gratuit → panneau refermé ; étape « L'Oracle 🔮 » (9/11) dans le tuto ; fermeture au tap mobile ; fournisseurs Anthropic + Google (OpenAI bien retiré).
- **Import/export exemplaires** : validation ligne par ligne (« point 3 : latitude hors limites (95) »), choix de catégorie si absente, export `formatVersion: 2` complet, `dernierExport` mis à jour.
- Suppressions toutes protégées par le **dialogue de confirmation intégré** (jamais de `confirm()` natif).
- **Tuto soigné** : 11 étapes qui visent toutes un élément réellement visible, état de démo (Via ferrata + filtres ouverts à l'étape 5) proprement restauré à la sortie.
- Filtres déclaratifs impeccables (cotation TD : 18 → 8 marqueurs, « Tout » restaure, infobulles glossaire « Peu Difficile »), panneau auto-ouvert/fermé selon les catégories.
- Mode nuit lisible partout (panneau, fiche, Oracle) ; le carnet garde son identité de grimoire.
- Mobile : FABs tous atteignables, fiche plein écran, carnet centré sans débordement, capsule Oracle 363×682 dans les 375 px.
- Toast de géolocalisation refusée clair ; parcours toilettes dégradé bien géré.
- Zéro erreur console du chargement à la fin des tests.

## 6. Nettoyage

Créé puis supprimé pendant le test :

- Point utilisateur « TEST-AGENT point temporaire » (via ferrata) — supprimé via 🗑 + confirmation ; IndexedDB `userPoints` = 0.
- 2 points importés « TEST-IMPORT alpha/beta » (GeoJSON de test) — supprimés ; compteur Grotte revenu à 484.
- Statuts ★/✓/♥ posés sur « Refuge du rocher des vierges » et « Via ferrata de Ancelle » — tous retirés (compteurs SUIVI à 0, clé `carte-outdoor:statuses` supprimée).
- Note de carnet « Note de test du testeur automatique » — supprimée ; sorties (y compris la seed du bug 1) supprimées ; `journal` = 0, `carte-outdoor:sorties` = `[]`.
- 2 consultations Oracle (Chamonix, bureau + mobile) — supprimées de l'historique ; clé bidon `sk-ant-FAUSSE-CLE-DE-TEST-000` effacée ; clés localStorage `oracle-modele`, `oracle-mode`, `oracle-cles`, `oracle-historique` retirées.
- Mode nuit → mode jour restauré ; fond Relief → Plan (OSM) restauré ; viewport → bureau.
- `carte-outdoor:prefs` restauré à l'identique de l'état trouvé (`activeThemes:["cite-caractere"]`, zoom 6, centre [45.22848, 0.4834], fond OSM).

**Vérification finale après rechargement** : localStorage strictement identique à l'état initial (2 clés : `prefs`, `sorties`), IndexedDB `userPoints`/`journal`/`tracks` = 0, seule « Cité de caractère » cochée, version v41, zéro erreur console. Aucun fichier de l'application modifié.
