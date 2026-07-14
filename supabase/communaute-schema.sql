-- Catégories communautaires de SpotMap : partage entre utilisateurs avec
-- VALIDATION MANUELLE avant publication (statut en_attente → validee/refusee).
-- À exécuter une fois dans l'éditeur SQL Supabase. Voir docs/COMMUNAUTE.md.

-- 1. Les catégories soumises. `donnees` = le colis JSON complet
--    { formatVersion, nom, description, theme:{label,color,textColor,icon},
--      points:[Features GeoJSON] } — plafonds durs contre l'abus.
create table if not exists public.categories_partagees (
  id              uuid primary key default gen_random_uuid(),
  auteur          uuid not null references auth.users (id) on delete cascade,
  nom             text not null check (char_length(nom) between 3 and 60),
  description     text not null default '' check (char_length(description) <= 500),
  pays            text not null default 'fr' check (char_length(pays) <= 8),
  statut          text not null default 'en_attente'
                  check (statut in ('en_attente', 'validee', 'refusee')),
  donnees         jsonb not null check (pg_column_size(donnees) < 1048576), -- < 1 Mo
  nb_points       integer not null check (nb_points between 1 and 500),
  telechargements integer not null default 0,
  cree            timestamptz not null default now()
);

-- 2. Les modérateurs (toi). Table SANS policy : invisible et non modifiable via
--    l'API publique — on s'y ajoute UNE FOIS via l'éditeur SQL :
--      insert into public.moderateurs (user_id)
--      values ('<ton-user-id, visible dans Authentication → Users>');
create table if not exists public.moderateurs (
  user_id uuid primary key references auth.users (id) on delete cascade
);
alter table public.moderateurs enable row level security;

-- 3. RLS des catégories : lecture publique des validées (+ ses propres
--    soumissions), soumission par un compte connecté TOUJOURS en attente,
--    retrait par l'auteur, modération réservée à la table moderateurs.
alter table public.categories_partagees enable row level security;

drop policy if exists lire_validees on public.categories_partagees;
create policy lire_validees on public.categories_partagees
  for select using (statut = 'validee' or auth.uid() = auteur);

drop policy if exists soumettre on public.categories_partagees;
create policy soumettre on public.categories_partagees
  for insert with check (auth.uid() = auteur and statut = 'en_attente');

drop policy if exists retirer_sa_soumission on public.categories_partagees;
create policy retirer_sa_soumission on public.categories_partagees
  for delete using (auth.uid() = auteur);

drop policy if exists moderer on public.categories_partagees;
create policy moderer on public.categories_partagees
  for update using (exists (select 1 from public.moderateurs m where m.user_id = auth.uid()))
  with check (exists (select 1 from public.moderateurs m where m.user_id = auth.uid()));

-- 4. Compteur de téléchargements : atomique, appelable par tous, uniquement
--    sur une catégorie validée (security definer = passe outre la RLS pour
--    CETTE opération précise, rien d'autre).
create or replace function public.compter_telechargement(p_id uuid)
returns void
language sql
security definer
as $$
  update public.categories_partagees
     set telechargements = telechargements + 1
   where id = p_id and statut = 'validee';
$$;

-- 5. Index utiles (liste publique triée, file de modération).
create index if not exists idx_catpart_statut on public.categories_partagees (statut, telechargements desc);
