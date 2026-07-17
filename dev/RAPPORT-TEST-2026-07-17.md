# Rapport de test — 17 juillet 2026 (vague v68, avant bump VERSION)

Campagne de bout en bout en Chrome headless (CDP, profil jetable), serveur de dev `http://localhost:8128`, purge SW + caches + localStorage + IndexedDB avant démarrage. Priorité aux nouveautés v68 (page de garde, bouton maison, réglages en grille, fréquentation, communauté 3 volets, tuto refondu) + protocole standard complet + multi-pays v67 (IT/CH/ES).

## 1. Synthèse

L'application est dans un très bon état : **aucun bug d'interface reproduit** sur l'ensemble des parcours (v68 + protocole standard + multi-pays), et **zéro erreur console applicative** sur toute la campagne. Les sept nouveautés v68 sont conformes à leur cahier des charges, souvent au pixel près (tuto 11 étapes ciblant des éléments réellement visibles, bouton maison avec ses trois comportements, grille 3×3…). Les seuls problèmes trouvés sont : **1 majeur d'infrastructure** (le domaine Supabase du projet ne résout plus en DNS — sync, communauté et fréquentation inopérants même en production) et **2 mineurs de données** (15 noms de points « en forme de phrase », une rando italienne dont la description contredit les stats mesurées). Bilan : 0 bloquant, 1 majeur (infra), 2 mineurs (données), plus quelques frictions d'ergonomie listées.

## 2. 🐛 Bugs

| Gravité | Où | Reproduction | Cause probable |
|---|---|---|---|
| **Majeur** (infra, pas le code) | Sync, Communauté, Fréquentation | `nslookup xwrqqhvqyccgtkslexbu.supabase.co` → **NXDOMAIN** (« Non-existent domain », vérifié via dns.google). Dans l'app : Communauté → Explorer affiche « Bibliothèque injoignable — êtes-vous en ligne ? », Fréquentation affiche le message doux, et chaque boot logge une erreur réseau `ERR_NAME_NOT_RESOLVED` (ping de présence). | Le **projet Supabase n'existe plus** (supprimé ? en pause longue ? ref changée ?) — un projet simplement « sans SQL exécuté » répondrait quand même en DNS. `js/config/supabase.js:12`. Tous les replis de l'app fonctionnent (aucune erreur applicative), mais la synchronisation multi-appareils est donc cassée **aussi en production**. À vérifier dans la console Supabase avant le déploiement v68. |
| **Mineur** (données) | Fiches, carnet, dialogues de confirmation | Rechercher « Yvoire » → le point château s'appelle « Yvoire en Haute-Savoie. » (avec point final). Le carnet affiche « Retirer cette sortie à “Yvoire en Haute-Savoie.” ». | **15 points ont un nom en forme de phrase** (audit `data/points.geojson`) : 8 châteaux (`ch-0092` « Château de Bignicourt-sur-Saulx dans la Marne. », `ch-0162`, `ch-0460`, `ch-0632` « la Nerthe à Châteauneuf-du-Pape dans le Vaucluse. », `ch-0657`, `ch-0854`, `ch-0879`, `ch-0931`), 5 refuges (`rf-3996`, `rf-6500`, `rf-5272`, `rf-5016`, `rf-7893`), 2 escalades (`esc-2159`, `esc-3141`). Résidus de descriptions recopiées dans `name` au build. |
| **Mineur** (données) | Fiche randonnée IT | Italie → Randonnée → « Tour des Tre Cime di Lavaredo » : la description annonce « **Boucle de 10 km** … (~400 m D+) » mais les champs mesurés affichent « Distance **3,9 km** (aller) » et « Dénivelé +200 m ». GPX généré : 42 points, 3,9 km. | Boucle balisée reprise en **routage A→B** (Auronzo→Locatelli) au lieu de sa relation OSM — piège documenté dans CLAUDE.md (`relationOsm` dans `tools/randos-pays.json`). Le tracé dépasse le seuil de 0,9 km donc n'a pas été écarté au build, mais il contredit la fiche. Vérifier les autres boucles CH/IT/ES dont la durée éditoriale a été écartée. |

### À vérifier (non confirmé, pas mis en bug)

- Le compteur de la couverture du carnet a affiché « **2 sortie(s)** » alors qu'il existait 1 sortie + 1 note devenue orpheline (après suppression de la sortie mais pas de la note). Le compte semble mélanger sorties et pages. Scénario tordu (créé par mon nettoyage partiel), à confirmer sur un cas réel avant correction.

## 3. 🎨 Ergonomie (classée par impact)

1. **Carnet : « Retirer cette sortie » ne retire pas vraiment la page.** Le 🗑 supprime la sortie mais laisse le statut ✓ Fait → la page **réapparaît** en « Date inconnue — Faite avant le carnet — préciser la date ». L'utilisateur croit avoir supprimé, la page revient sous une autre forme. Proposer dans la confirmation : « Retirer aussi le ✓ Fait de ce lieu ? » (ou expliquer ce qui va rester).
2. **Auto-cochage silencieux des catégories.** Ouvrir une fiche depuis la recherche coche la catégorie du point (bien !) mais elle **reste cochée** après fermeture : en trois recherches, je me suis retrouvé avec Cascade + Château + Village actifs sans l'avoir voulu. Décocher au retour si la coche était automatique, ou toast « Catégorie X activée ».
3. **Message Fréquentation côté visiteur = jargon développeur.** « exécutez supabase/frequentation-schema.sql (guide : docs/FREQUENTATION.md) » sera lu par n'importe quel utilisateur final tant que le serveur n'est pas équipé. Un simple « Le compteur arrive bientôt 🙂 » suffirait côté public (le détail technique peut rester en commentaire ou en console).
4. **Recherche stricte sur la chaîne.** « Tour du Lac Blanc » → 0 résultat ; « lac blanc » → 8. Une recherche par mots-clés indépendants (tous les mots présents, peu importe l'ordre) rendrait la barre nettement plus tolérante.
5. **`.pays-desc` généré mais jamais montré** (`css/styles.css:1501` `display:none`, volontaire). Les descriptions par pays sont soignées (« Refuges des Dolomites, via ferrata… ») mais invisibles partout : les exposer en `title`/infobulle des cartes pays coûterait une ligne, ou ne plus les générer.

## 4. 💡 Idées d'évolution

- **Badge boucle / aller-retour sur les fiches rando** : la détection existe déjà au build (`completer_stats_randos.py`), l'afficher lèverait l'ambiguïté relevée sur les Tre Cime.
- **Statistiques personnelles depuis le carnet** : nb de sorties par an, dénivelé cumulé, catégories les plus pratiquées — toutes les données sont déjà en IndexedDB.
- **Oracle contextuel depuis une fiche** : un bouton « 🔮 Autour de ce lieu » dans la fiche (l'Oracle sait déjà travailler depuis des coordonnées).
- **Raccourci « eau potable seulement »** : le filtre potabilité existe ; une pastille dédiée en tête de la couche Fontaines éviterait d'ouvrir le panneau de filtres en rando.
- **Indicateur de complétude hors-ligne** : « cette zone est disponible hors connexion » (le SW met déjà les tuiles/fichiers en cache à la volée).

## 5. ✅ Ce qui marche bien

- **Page de garde v68** : carte du monde cliquable + cartes pays façon icônes d'app (pastille drapeau 52 px, rayon 16 px), défilement horizontal réel en mobile (564 px > 347 px), **un seul** bouton communauté qui répond bien « Choisissez d'abord votre pays 🙂 » au premier boot.
- **Bouton maison** : ouvre le monde, même pays = referme **sans reload**, autre pays = **reload** (vérifié FR→IT→CH→ES), clic sur le fond = referme.
- **⚙️ Réglages en grille** : 9 tuiles, 3 colonnes, chaque tuile ferme le dialogue et ouvre la bonne action ; Mode nuit bascule état + icône + libellé (🌙↔☀️) et le rendu nuit est lisible partout (sidebar, fiche, réglages).
- **Tuto refondu** : 11 étapes / 11 points de progression, émoji par étape, « Passer » discret, Précédent fonctionnel, « C'est parti ! 🚀 », l'étape 🌍 cible le bouton maison, **toutes** les cibles mesurées visibles à l'écran et les textes collent à l'interface v68.
- **Communauté 3 volets** avec replis propres et connexion Google proposée sur Partager / Mes partages.
- **Multi-pays v67** : boots IT/CH/ES nickel (Randonnée 23/24/25), couches lourdes « … » → dialogue → chargement (79 138 fontaines IT sans une erreur), liens « 🧗 Fiche Ferrate365 / myferrata.ch / deandar.com » + cotations K, rando IT avec tracé épinglé, pastille de rappel, GPX valide (42 trkpt), décocher efface tout.
- **Import/export** : export formatVersion 2 **sans aucune clé API** ; import GeoJSON avec erreurs listées par ligne (« point 3 : latitude hors limites (95.2) »), choix de catégorie obligatoire, bouton « Importer 2 point(s) ».
- **Statuts exclusifs** ★/✓/♥ avec badge sur le marqueur et compteurs en direct ; filtres par cotation (133 → 71 → 133) ; exclusivité grosses/petites couches dans les deux sens ; FAB 🚻 dégradé proprement sans géoloc ; 4 fonds de carte fonctionnels.

## 6. Nettoyage

Créé puis supprimé pendant la campagne (tout vérifié par compteurs/état après suppression) :
- Point utilisateur « TEST-QA point temporaire » (Cascade 1174→1175→1174) — supprimé via sa fiche.
- 2 points importés « TEST-QA import 1/2 » (1174→1176→1174) — supprimés via leurs fiches.
- Statuts ★/✓/♥ posés sur « Le Lac Blanc-Rocher Hans » puis retirés (compteurs 0/0/0).
- Sortie carnet + note « Note de test QA » sur le château d'Yvoire — sortie retirée (🗑), note supprimée (✎ → vide → Enregistrer), statut ✓ Fait retiré ; carnet revenu à « attend sa première sortie ».
- Consultation Oracle « Chamonix-Mont-Blanc » (mode ✨ Gratuit uniquement, aucune clé API saisie) — supprimée de l'historique (`carte-outdoor:oracle-historique` = `[]`).
- Fond de carte remis sur Plan (OSM), mode nuit rebasculé jour, émulation revenue en desktop.
- **Purge finale** : service worker désinscrit, 2 caches supprimés, IndexedDB `carte-outdoor` supprimée, `localStorage.clear()` puis `carte-outdoor:pays = "fr"` reposé comme demandé. Profil Chrome jetable détruit. Aucun fichier de l'application modifié.

Note de méthode : un faux « bug » (checkbox Toilettes inerte) était causé par mon propre patch de `HTMLInputElement.prototype.click` (outillage d'import) non restauré — corrigé et consigné dans la mémoire du testeur pour ne plus le payer.
