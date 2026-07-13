# Oracle payant — plan et mise en œuvre

Décisions actées avec l'utilisateur (2026-07-13) : **pack de consultations** (achat unique, décompté) payé via **Google Play Billing**. Play Billing impose que l'app soit **publiée sur le Play Store** → l'Oracle payant **s'active avec l'étape 2 (Play Store)**, pas avant.

Le mode **gratuit** (points de la carte + Wikipédia + agendas) et le mode **« ma propre clé »** restent inchangés. On ajoute un **3ᵉ mode** : IA sans clé, débloquée par un pack de consultations.

## Pourquoi un serveur (rappel)

Une PWA statique ne peut pas cacher une clé API. Il faut un relais qui détient **notre** clé. On réutilise **Supabase** (déjà là pour la sync + le login Google). Deux fonctions :

- **consume** (`supabase/functions/oracle-ia/index.ts`) — vérifie le login + le solde, appelle l'IA avec notre clé, **décompte** 1 consultation. **Indépendant du store, prêt à déployer.**
- **grant** (à écrire au moment du Play Store) — reçoit un `purchaseToken` Play Billing, le **vérifie** auprès de la Google Play Developer API, puis crédite le pack (`crediter_achat`, idempotent).

## Modèle de données

`supabase/functions/oracle-ia/schema.sql` : table `oracle_credits` (solde par compte), `oracle_achats` (journal anti-double-crédit), RPC `consommer_credit` (décompte atomique) et `crediter_achat` (idempotent). RLS : chacun lit son solde, **seule la fonction** (rôle service) modifie les crédits.

## Flux d'activation, côté utilisateur

1. Oracle sans clé → bandeau **« Débloquer l'IA — pack de consultations »**.
2. Achat via **Play Billing** (Digital Goods API dans la TWA) → `purchaseToken`.
3. La fonction **grant** vérifie l'achat et crédite le compte (lié au login Google).
4. Les questions Oracle IA appellent **consume** → réponse + solde décrémenté, sans aucune clé côté utilisateur.
5. Solde épuisé → on repropose l'achat.

## Économie (à garder en tête pour fixer le pack)

- Une consultation IA (Claude Haiku + `web_search`) coûte **~0,01–0,05 €** de notre poche.
- Google prend **15–30 %** sur les achats in-app.
- Suggestion de départ : **pack 30 consultations à 1,99 €** (marge correcte) et/ou **pack 10 à 0,99 €**. Ajustable dans la Play Console sans toucher au code.
- Anti-abus : plafond de consultations/jour par compte (à ajouter dans `consume` si besoin), et le décompte n'a lieu **qu'après un appel réussi**.

## Séquence de mise en œuvre

**Bloqué tant que l'app n'est pas sur le Play Store (étape 2).**

1. **[fait]** Code du relais `consume` + schéma SQL (ce dossier).
2. **[étape 2]** Publier l'app sur le Play Store (TWA/PWABuilder — voir `docs/PLAYSTORE.md`).
3. **[utilisateur]** Créer les produits « pack » dans la **Play Console** (`pack_10`, `pack_30`), configurer un **compte de service** Google Play Developer API.
4. **[utilisateur]** Déployer les fonctions Supabase et poser les secrets :
   ```bash
   supabase functions deploy oracle-ia --no-verify-jwt
   supabase secrets set ANTHROPIC_API_KEY=sk-ant-...
   # exécuter schema.sql dans l'éditeur SQL Supabase
   ```
5. **[agent]** Écrire la fonction **grant** (vérification Play Billing) + le câblage client de `js/oracle.js` (3ᵉ mode, affichage du solde, bouton d'achat via Digital Goods API) — **testable de bout en bout seulement une fois l'app sur le store**.
6. Test interne (piste fermée Play Console) puis production.

## Ce que l'agent NE peut PAS faire (actions utilisateur)

Créer les comptes (Play Console 25 $, Google Cloud service account), saisir/déposer la clé Anthropic comme secret, configurer le paiement et les produits. L'agent fournit le code, le schéma et ce guide ; **l'utilisateur déploie et gère les comptes/paiements/secrets**.

## Repli web (optionnel, plus tard)

Si un jour on veut l'Oracle payant **hors** Play Store (site/PWA), ajouter **Stripe** (Checkout + webhook → `crediter_achat`). Non retenu pour l'instant (choix : Play Billing d'abord). Le relais `consume` est déjà agnostique du moyen de paiement.
