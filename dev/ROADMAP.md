# Feuille de route — Carte Outdoor

Tenue par l'agent **chef-de-projet** (`.claude/agents/chef-de-projet.md`). Dernière mise à jour : 2026-07-11.

## État des lieux

- **En ligne (v52)** : ~9 800 points (135 randonnées/28 massifs avec tracés + GPX, cascades, lacs, villages…), 190 GR cliquables, 66 500 toilettes + 49 500 points d'eau à la demande, Oracle (gratuit + IA), sync Supabase, partage QR, carnet.
- **v53 en préparation** : revue de code complète (3 bugs corrigés : confirm() natif des traces, boule Oracle bloquée sans clé, révocation d'URL d'export) — test de bout en bout en cours.

## Étape 1 — 📋 Vérifier et enrichir toutes les données

Audit de complétude par catégorie puis enrichissement ciblé (agent enrichisseur, par fournées) :

- [ ] Audit : pour chaque catégorie, taux de remplissage des champs de fiche (photo, description, lien, horaires…), fiches « À vérifier » restantes, coordonnées suspectes. Livrable : rapport chiffré + liste priorisée.
- [ ] Croisement avec les sources fiables (OSM, Wikipédia, data.gouv.fr — Google Maps n'a pas d'API de moissonnage licite : croiser via liens sortants seulement).
- [ ] Enrichissement par fournées (une catégorie = un run reprenable), convention `details.fiche` partout.
- ⚠️ Contrainte : plafond de dépense mensuel — découper, intégrer au fil de l'eau.

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
