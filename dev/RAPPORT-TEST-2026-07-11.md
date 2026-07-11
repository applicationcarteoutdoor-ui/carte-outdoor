# Rapport de test — Carte Outdoor v53 (non poussée)

**Date** : 11 juillet 2026 · **Testeur** : agent testeur-app · **Environnement** : Chrome headless piloté par CDP
(profil jetable), serveur de dev `http://localhost:8128`, SW + caches + localStorage purgés avant tout test.
Desktop 1280×900 puis mobile 390×844 (émulation CDP + `map.invalidateSize()`).

---

## 1. Synthèse

L'application est en très bon état : **aucun bug bloquant, aucun bug majeur, 3 bugs mineurs** (tous cosmétiques),
et **zéro erreur console applicative** sur l'ensemble de la session (les seules erreurs relevées venaient de mes
propres sondes de test, bloquées par la CSP — comportement attendu). Les quatre nouveautés prioritaires
(GR cliquables, filtres randonnées, Fontaines & sources, Partage) fonctionnent de bout en bout, et les deux
correctifs frais de la v53 (confirmation intégrée à la suppression de trace GPX, Oracle IA sans clé) sont
validés. Le parcours complet — recherche, statuts, ajout de point, carnet, Oracle, import/export, tuto,
mode nuit, mobile — passe sans accroc.

## 2. 🐛 Bugs

| Gravité | Où | Reproduction | Cause probable |
|---|---|---|---|
| Mineur | Fiche d'une randonnée | Ouvrir n'importe quelle fiche `randonnee` (ex. Chamechaude) → une ligne « **fiche** Référencée » s'affiche avec un libellé brut en minuscule, incohérent avec « Altitude », « Massif »… | `js/details.js:173-183` affiche les champs de `details` non déclarés dans `theme.fields` avec leur clé brute. `fiche` est déclaré comme **filtre** (`themes.js`) mais pas comme champ → il tombe dans le rattrapage. Touche potentiellement toute catégorie à convention `details.fiche` dont le champ n'est pas déclaré (randonnée confirmé ; cascade/lac/château à vérifier). |
| Mineur | Fiche d'un point d'eau | Ouvrir la fiche d'une fontaine avec info PMR (ex. « Source Sainte-Odile ») → ligne « **wheelchair** Non accessible PMR » : clé anglaise brute comme libellé. | Même mécanisme : `wheelchair` absent des `fields` du thème `eau` dans `js/config/themes.js`. Déclarer le champ avec un label (« Accès PMR ») suffirait. |
| Mineur | Filtres randonnée / lac (buckets) | Sélectionner « > 1000 m » de D+ → 44 randonnées affichées, alors que 42 ont strictement plus de 1000 m : les 2 randos à exactement 1000 m tombent dans « > 1000 m » et pas dans « 500 à 1000 m ». | Sémantique des buckets `min`/`max` (`js/filtrage.js`) : `min` inclusif, `max` exclusif. Les libellés « 500 à 1000 m » / « > 1000 m » suggèrent l'inverse pour la borne 1000. Pur affichage, aucun point perdu. |

### À vérifier (non confirmé / hors app)

- **CLAUDE.md périmé sur la forme de l'Oracle** : la doc affirme « border-radius: 50 % en permanence — la forme
  étirée est une ellipse, jamais un rectangle », mais `css/oracle.css` (en-tête + `.forme-etiree`, ligne 126-129)
  définit délibérément une **capsule** à `border-radius: 26px`. Le CSS étant cohérent et soigné, c'est la doc qui
  est en retard, pas un bug d'affichage — mais un futur agent pourrait « corriger » le CSS à tort.
- **`js/sidebar.js:141`** : le compte des Sentiers GR est codé en dur (`count: 190`) — exact aujourd'hui,
  à surveiller si `data/gr.geojson` évolue (le commentaire du code le signale déjà).

## 3. 🎨 Ergonomie

Classé par impact décroissant :

1. **Import sans catégorie choisie : refus silencieux.** Dans le dialogue d'import, cliquer « Importer » sans
   avoir choisi de catégorie ne fait rien du tout — pas de message, pas de secousse, le dialogue reste ouvert.
   L'utilisateur peut croire que le bouton est cassé. Un toast (« Choisissez d'abord une catégorie ») ou une mise
   en évidence du sélecteur suffirait. (`js/import-export.js`, gestion de `.import-confirm`.)
2. **Deux corbeilles pour une même entrée de carnet.** Marquer un point « ✓ Fait » puis lui ajouter une note crée
   une sortie ET une note. Dans le carnet, la corbeille de l'entrée (« Retirer cette sortie… ») supprime la sortie
   mais laisse la note affichée sur la page — il faut une seconde suppression (dans la fiche ou le carnet) pour la
   note. Cohérent côté données, mais surprenant : l'utilisateur qui « retire la sortie » s'attend plutôt à voir
   la page se vider. Au minimum, préciser le message de confirmation (« la note associée sera conservée »).
3. **Supprimer une sortie du carnet ne retire pas le statut « ✓ Fait »** du point. Défendable (le statut et le
   journal sont deux choses), mais après suppression le compteur « ✓ Fait 1 » de la sidebar peut sembler
   incohérent avec un carnet vide.
4. **Compteurs sans séparateur de milliers** dans la sidebar (« Toilettes 66584 », « Fontaines & sources 49531 ») :
   un `toLocaleString("fr-FR")` rendrait ces gros nombres lisibles.
5. **Suppression d'une consultation Oracle en un clic** (✕ « Oublier »), sans confirmation — assumé et peu risqué
   (une consultation se recrée), mais incohérent avec le reste de l'app qui confirme toutes les suppressions.
6. **Grosses couches : pas d'indicateur de complétude.** Les 49 531 points d'eau mettent ~15-20 s à finir de
   s'ajouter (la zone visible arrive vite, par design). Pendant ce temps, un filtre cliqué compte sur un ensemble
   partiel. Un petit indicateur discret « chargement… » sur la ligne de catégorie éviterait la confusion.

## 4. 💡 Idées d'évolution

- **Filtre « eau potable sur mon itinéraire »** : croiser la trace GPX importée (ou le tracé d'une rando) avec les
  points d'eau/toilettes à moins de X m du tracé — les données sont déjà toutes là.
- **Distance/durée cumulées dans la fiche GR** : les GR ont distance et D+ ; proposer « ~n jours de marche »
  (à 20-25 km/j) donnerait une échelle immédiate.
- **Regroupement par massif** : le champ `massif` des randonnées ferait un joli filtre global (et un tri du carnet).
- **Export GPX d'une sélection** : on exporte le GPX d'une rando ou d'un GR — permettre d'exporter tous les
  favoris ♥ en un seul fichier de waypoints serait naturel pour les GPS de terrain.
- **Buckets de superficie pour les lacs** (le champ `superficie` existe déjà) au même titre que l'altitude.

## 5. ✅ Ce qui marche bien

- **GR cliquables** : clic au doigt fiable (tolérance canvas), fiche complète (badge, 521,8 km, D+ estimé,
  📥 GPX, liens), tracé conservé fiche fermée, pastille de réouverture, dé-épinglage propre quand une rando
  prend la place, disparition totale au décochage. Impeccable.
- **Filtres randonnées** : les 3 groupes de buckets filtrent réellement (135 → 7 → 87 → 44 → 3 selon les combinaisons),
  cumulables entre groupes (ET) et dans un groupe (OU), vérifiés contre les données brutes ; les 135 randos ont
  tous leurs champs `_n`.
- **Fontaines & sources** : dialogue d'avertissement complet (Retour décoche proprement), 49 531 points chargés,
  filtres Potabilité + Type opérants, échec de géolocalisation géré avec des messages clairs.
- **Correctifs v53 validés** : la suppression de trace GPX passe par le dialogue intégré (aucun `confirm()` natif
  détecté de toute la session, sur aucun flux) ; l'Oracle en mode IA sans clé revient à l'écran d'accueil, toaste
  un message clair et ouvre le panneau des clés ; retour en ✨ Gratuit → le panneau se referme.
- **Sécurité** : nom de point piégé (`<script>`) échappé partout (recherche, fiche), aucun script injecté ;
  export sans aucune fuite de clé API ; les clés se posent et s'effacent proprement.
- **Le reste du parcours** : recherche par nom/ville/code postal, statuts avec badge sur l'épingle et compteurs,
  ajout/suppression de point, carnet (tri, thèmes, notes, photos), tuto (11 étapes, toutes les cibles visibles,
  textes à jour), profil altimétrique des traces, fonds de carte, mode nuit contrasté partout, mobile 390 px
  (FABs atteignables, fiche en volet plein écran, Oracle rond 374×374 puis capsule sans débord, carnet centré).

## 6. Nettoyage

Tout le test s'est déroulé dans un **profil Chrome jetable** (supprimé en fin de session) : rien n'a touché le
navigateur ni les données de l'utilisateur. À l'intérieur de la session, chaque donnée de test a de plus été
supprimée par l'interface pour exercer les flux de suppression :

- Trace GPX « Trace de test QA » — importée puis supprimée (confirmation intégrée) ✔
- Point « Point de test QA » (ajout manuel) — supprimé via sa fiche ✔
- Points « Point import QA 1 / 2 » (import GeoJSON) — supprimés via leur fiche ✔ (`getUserPoints()` = 0)
- Statuts ★/✓/♥ posés sur « Via ferrata de Chamonix » — tous retirés (compteurs à 0, `statuses` = `{}`) ✔
- Sortie + note de carnet sur ce même point — supprimées (journal vide, `sorties` = `[]`) ✔
- Consultations Oracle (Chamonix 74400, 38380) — effacées de l'historique (`[]`) ✔
- Clé API bidon — effacée (« Tout effacer », `oracle-cles` = `{}`) ✔
- Idée de test — supprimée (`idees` = `[]`) ✔
- Thème du carnet remis sur Grimoire, mode nuit désactivé, fond de carte remis sur Plan (OSM) ✔
- Catégories remises à l'état du premier lancement (Village + Mes traces GPX cochées, le reste décoché) ✔

Aucun fichier de l'application n'a été modifié ; seul ce rapport est créé.
