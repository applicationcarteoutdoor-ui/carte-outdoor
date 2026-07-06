# Synchronisation multi-appareils (Supabase + Google)

L'application peut synchroniser le **carnet, les points ajoutés, le suivi et la
personnalisation** entre plusieurs appareils, via un compte Google. Les **clés
API de l'Oracle** et les **préférences d'affichage** (centre de carte, mode
nuit) ne sont **pas** synchronisées : elles restent sur chaque appareil.

Le code : [`js/sync.js`](../js/sync.js) + config dans
[`js/config/supabase.js`](../js/config/supabase.js). Aucune dépendance : appels
`fetch` directs sur l'API Supabase.

## Comment se connecte-t-on ?

Au clic sur « Se connecter avec Google », une **petite fenêtre** (popup) s'ouvre
sur Google ; **l'application reste ouverte derrière**. Après le choix du compte,
la fenêtre se ferme et l'app se connecte — le jeton transite par le localStorage
partagé (événement `storage`), ce qui reste fiable même si le lien avec la
fenêtre est coupé (COOP). Si le navigateur **bloque les popups**, on bascule sur
une redirection pleine page (retour ensuite avec le jeton dans l'URL).

Avantage : **aucune librairie externe**, aucun réglage « JavaScript origins »,
pas de FedCM. Seuls les *redirect URIs* (Google) et les *Redirect URLs*
(Supabase) — déjà en place — sont nécessaires.

## Mise en place (une fois)

### 1. Projet Supabase
- Créer un projet, copier **Project URL** + **clé anon** → les mettre dans
  `js/config/supabase.js`.
- SQL Editor → créer la table :
  ```sql
  create table if not exists public.donnees (
    user_id uuid not null references auth.users on delete cascade,
    cle text not null,
    valeur jsonb,
    updated_at timestamptz not null default now(),
    primary key (user_id, cle)
  );
  alter table public.donnees enable row level security;
  create policy "chacun ses donnees" on public.donnees
    for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
  ```

### 2. Google Cloud — client OAuth
Dans *APIs & Services → Credentials → le client OAuth*, **Authorized redirect
URIs** :
```
https://<ref>.supabase.co/auth/v1/callback
```
(Les « Authorized JavaScript origins » ne sont **pas** nécessaires avec la
connexion par fenêtre.)

### 3. Supabase — provider Google
*Authentication → Providers → Google* : activer, coller Client ID + Secret.
*Authentication → URL Configuration → Redirect URLs* : ajouter l'URL du site
(`https://applicationcarteoutdoor-ui.github.io/carte-outdoor/`) et
`http://localhost:8125`.

## Sécurité
- URL, clé anon et Client ID sont **publics par conception**. La protection
  vient du **RLS** : chaque compte ne peut lire/écrire que ses propres lignes
  (une écriture sans compte est refusée par la base).
- Le domaine Supabase et `accounts.google.com` sont autorisés dans la **CSP**
  (`index.html`). Si on change de projet Supabase, mettre à jour la CSP.
