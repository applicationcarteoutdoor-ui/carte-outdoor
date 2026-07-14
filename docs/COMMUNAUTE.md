# Catégories communautaires — déploiement et modération

Les utilisateurs peuvent **partager leurs catégories personnelles** (spots de
pêche, circuits VTT, coins photo…) et **importer celles des autres**. Chaque
soumission passe par une **validation manuelle** avant d'être visible.

Client : `js/communaute.js` (dialogue « 🌍 Catégories de la communauté », page
de garde + ⚙️ Réglages). Serveur : Supabase, table `categories_partagees`.

## Mise en service (une fois, ~5 minutes)

1. Ouvrir l'éditeur SQL du projet Supabase (celui de la sync) et exécuter
   **`supabase/communaute-schema.sql`** — crée la table, la sécurité (RLS),
   le compteur de téléchargements et la table des modérateurs.
2. S'ajouter comme **modérateur** : récupérer son user id dans
   *Authentication → Users* (le compte Google), puis dans l'éditeur SQL :
   ```sql
   insert into public.moderateurs (user_id) values ('<ton-user-id>');
   ```
3. C'est tout. Tant que le SQL n'est pas exécuté, l'app affiche « la
   bibliothèque n'est pas encore ouverte » (aucune erreur).

## Comment ça marche

- **Partager** (connexion Google requise) : l'app construit un « colis »
  (nom, description, thème, points **sans photos**, ≤ 500 points, ≤ 1 Mo,
  plafonds revérifiés par la base) et l'insère en statut `en_attente`.
  La RLS force : auteur = compte connecté, statut = en_attente. Personne ne
  peut publier directement.
- **Importer** (public, sans compte) : seules les catégories `validee` sont
  visibles. L'import re-identifie tout (`comm-<id>`, ids stables → réimporter
  met à jour au lieu de dupliquer), rejette coordonnées invalides, liens non
  http(s), champs inconnus — et l'affichage passe par `esc()` comme toujours.

## Modérer (toi, via le tableau de bord Supabase)

*Table Editor → categories_partagees* : les soumissions arrivent en
`en_attente`. Pour chacune :

1. **Regarder `donnees`** (le JSON) : noms de points corrects ? coordonnées
   plausibles (dans le pays annoncé) ? liens propres ?
2. **Droits** : la liste ne doit pas être la recopie massive d'une base
   protégée (un topo commercial, un site sous licence NC…). Des points
   personnels, oui ; un scraping, non.
3. **Contenu** : pas de données personnelles (adresses privées…), pas de
   contenu déplacé dans les noms/descriptions.
4. Passer `statut` à **`validee`** (publiée pour tous) ou **`refusee`**.

L'auteur peut retirer sa propre soumission depuis la base (policy DELETE) ;
un panneau admin dans l'app pourra suivre si le volume le justifie.

## Limites v1 (choix assumés)

- **Pas de photos** dans les colis (droit d'auteur + poids) — v2 possible via
  Supabase Storage avec plafond de taille.
- Pas de notation/commentaires ; tri par nombre d'imports.
- La modération est manuelle — c'est voulu (qualité et droits d'abord).
