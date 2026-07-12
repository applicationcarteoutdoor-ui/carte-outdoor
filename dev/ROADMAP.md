# Feuille de route — Carte Outdoor

Tenue par l'agent **chef-de-projet** (`.claude/agents/chef-de-projet.md`). Dernière mise à jour : 2026-07-11.

## État des lieux

- **En ligne (v52)** : ~9 800 points (135 randonnées/28 massifs avec tracés + GPX, cascades, lacs, villages…), 190 GR cliquables, 66 500 toilettes + 49 500 points d'eau à la demande, Oracle (gratuit + IA), sync Supabase, partage QR, carnet.
- **v53 en préparation** : revue de code complète (3 bugs corrigés : confirm() natif des traces, boule Oracle bloquée sans clé, révocation d'URL d'export) — test de bout en bout en cours.

## Étape 1 — 🔄 Vérifier et enrichir toutes les données (EN COURS)

- [x] **Audit de complétude** (2026-07-11) — taux de remplissage par catégorie :

  | Catégorie | Points | Photos | Liens | « À vérifier » |
  |---|--:|--:|--:|--:|
  | cascade | 1 133 | 8 % | 9 % | **91 %** 🔴 |
  | chateau | 810 | 64 % | 67 % | 35 % 🟠 |
  | lac | 965 | 79 % | 100 % | 20 % 🟡 |
  | via-ferrata | 126 | 0 % | 100 % | 0 % |
  | escalade | 2 033 | 0 % | 100 % | 0 % (24 sites DOM confirmés valides) |
  | refuge | 3 524 | 0 % | 100 % | 0 % (refuges.info) |
  | grotte / cathédrale / village / rando | — | 92-99 % | 100 % | 0 % 🟢 |

  Constat : gros du travail sur **cascade** et **chateau**. Les 0 % photos (via-ferrata/escalade/refuge) = limite honnête (photos libres rares). Les 24 « coord hors bornes » escalade = DOM valides, PAS des erreurs → le contrôle de bornes doit inclure les DOM.
- **Ordre de revue** : via-ferrata (pilote) → escalade → cascade → chateau → lac → reste. Une catégorie = un run reprenable (enrichisseur, avec sa mémoire).
- [x] ✅ **via-ferrata** (2026-07-11) — pilote. **44 GPS recalés** (centroïde de commune → site OSM réel, règle conservatrice), **+7 VF manquantes** ajoutées (126 → 133, double accord OSM + viaferrata-fr.net). 47 points laissés « à vérifier manuellement » (OSM absent ou massif dense), photos toujours 0 (limite honnête). Rapport : dev/RAPPORT-REVUE-via-ferrata-2026-07-11.md. Méthode validée & réutilisable (diagnostic → recalage sûr → ajout double-accord). Scripts gabarits dans tools/.
- [x] ✅ **escalade** (2 033 → 2 308) (2026-07-11/12) — **revue approfondie via Camp to Camp** (après retour utilisateur : fiches vides). **1 519 points recalés + enrichis** (cotation/voies/roche/hauteur/orientation + lien C2C direct ; ex. Saint-Simon : 0 voie → 17 voies, 4c-8a, calcaire), **+275 sites manquants** ajoutés (France confirmée + contenu réel). ~514 restent au centroïde (pas de site C2C proche), photos toujours quasi nulles (CSP). Rapport : dev/RAPPORT-REVUE-escalade-2026-07-11.md.
- [ ] cascade (1 133, 91 % « à vérifier ») — le gros morceau (source : à récolter noms + coords Wikipédia/OSM).
- [ ] chateau, lac, … (à suivre)
- **Reste sur via-ferrata** : recaler à la main les 47 points ambigus (reverse-geocode + choix humain) ; ajouter Le Regardoir/Vouglans et Roc del Gorb (rapprochement de nom incertain).
- ⚠️ Plafond de dépense mensuel — découper, intégrer au fil de l'eau.

## Étape 2 — 📋 Publier sur le Play Store

Guide existant : `docs/PLAYSTORE.md` (TWA/PWABuilder). Reste à faire :

- [ ] Testeur vert sur la version candidate + données auditées (étape 1 au moins amorcée).
- [ ] **Action utilisateur** : compte Play Console (25 $ une fois), récupérer l'empreinte SHA-256 → compléter `.well-known/assetlinks.json`.
- [ ] Page « politique de confidentialité » (obligatoire Play Store — l'app ne collecte rien côté serveur hors sync opt-in : à écrire et héberger sur le site).
- [ ] Formulaire « sécurité des données » Play Console, captures d'écran, fiche store (texte + visuels).
- [ ] Paquet TWA (PWABuilder), test interne, puis production.

## Étape 3 — 📋 Modèle économique de l'Oracle

Décision d'architecture à trancher AVANT de coder (2 options) :

- **Le gratuit reste gratuit** (points de la carte + Wikipédia + liens d'agendas) — inchangé.
- **IA avec sa propre clé** — inchangé (déjà en place).
- **IA sans clé (payant ~0,99 €)** : nécessite un **relais serveur** qui détient NOTRE clé API et vérifie le droit d'accès — impossible en statique pur (une clé embarquée serait volée en 5 minutes).
  - Option A (recommandée) : **fonction serverless Supabase** (déjà notre back-end de sync) : vérifie l'achat, appelle l'API IA avec notre clé, plafonne par utilisateur/jour (anti-abus). Paiement : Play Billing dans la TWA (Digital Goods API) pour Android + repli web.
  - Option B : abonnement via Stripe (site web) — plus universel, mais Google impose Play Billing pour les achats numériques DANS l'app Android → risque de rejet. À n'utiliser que hors Play Store.
  - ⚠️ Risques à chiffrer : coût API par consultation (~0,01-0,05 €), donc 0,99 € ≈ 20-100 consultations → prévoir soit un forfait mensuel, soit un paquet de consultations. Anti-abus indispensable.

## Étape 4 — 📋 Autres pays : Nouvelle-Zélande d'abord

Architecture « pack pays » à concevoir (l'app est déjà country-agnostique, le PIPELINE ne l'est pas) :

- [ ] Abstraire ce qui est franco-centré : geo.api.gouv.fr (géocodage), IGN (altimétrie), bornes France, sources par catégorie.
- [ ] Sources NZ : OSM/Overpass (identique), LINZ + DOC (Department of Conservation : huts, tracks — données ouvertes excellentes), Wikipédia EN.
- [ ] Choix produit : une app par pays (carte-outdoor-nz) ou un sélecteur de pays dans la même app ? (à trancher avec l'utilisateur)
- [ ] i18n : interface EN pour la NZ.

## Backlog (petites améliorations, à grouper dans une future vague)

- Carnet : retirer une sortie laisse la note et le statut « ✓ Fait » en place (deux corbeilles distinctes, compteur d'apparence incohérente — rapport de test 2026-07-11). Décider d'une sémantique claire avec l'utilisateur avant de toucher.
- Sidebar : compteur GR figé à 190 (constante commentée dans sidebar.js) — recalculer si data/gr.geojson évolue.

## Prochain coup recommandé

Finaliser la **v53** (rapport du testeur → correctifs éventuels → push), puis lancer l'**audit de données** (étape 1) — c'est le prérequis des étapes 2 et 4, et il est parallélisable avec la préparation Play Store côté utilisateur (compte + SHA-256).

## Décisions en attente de l'utilisateur

1. Oracle payant : option A (Supabase + Play Billing) ou B (Stripe hors store) ? Forfait ou paquet de consultations ?
2. NZ : app séparée ou sélecteur de pays ?
3. Play Console : créer le compte et récupérer l'empreinte SHA-256.
