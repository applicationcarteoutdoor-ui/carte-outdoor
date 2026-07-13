-- Modèle de données de l'Oracle payant (« pack de consultations »).
-- À exécuter une fois dans l'éditeur SQL Supabase. Voir docs/ORACLE-PAYANT.md.

-- 1. Solde de consultations par compte.
create table if not exists public.oracle_credits (
  user_id    uuid primary key references auth.users (id) on delete cascade,
  credits    integer not null default 0 check (credits >= 0),
  maj        timestamptz not null default now()
);

-- 2. Journal des achats (idempotence : un jeton d'achat Play ne crédite qu'une fois).
create table if not exists public.oracle_achats (
  achat_token text primary key,          -- purchaseToken Play Billing
  user_id     uuid not null references auth.users (id) on delete cascade,
  produit     text not null,             -- ex. "pack_30_consultations"
  credits     integer not null,
  cree        timestamptz not null default now()
);

-- 3. RLS : chacun lit SON solde ; personne n'écrit directement (seule la
--    fonction, via le rôle service, modifie les crédits — anti-triche).
alter table public.oracle_credits enable row level security;
alter table public.oracle_achats  enable row level security;

drop policy if exists lire_son_solde on public.oracle_credits;
create policy lire_son_solde on public.oracle_credits
  for select using (auth.uid() = user_id);

-- 4. Décompte atomique d'une consultation (appelé par l'Edge Function consume).
create or replace function public.consommer_credit(p_user uuid)
returns integer
language plpgsql
security definer
as $$
declare reste integer;
begin
  update public.oracle_credits
     set credits = credits - 1, maj = now()
   where user_id = p_user and credits > 0
   returning credits into reste;
  return coalesce(reste, 0);
end;
$$;

-- 5. Créditer un achat vérifié (appelé par la fonction "grant" après
--    validation du purchaseToken Play Billing — cf. docs, étape Play Store).
create or replace function public.crediter_achat(
  p_user uuid, p_token text, p_produit text, p_credits integer)
returns void
language plpgsql
security definer
as $$
begin
  insert into public.oracle_achats (achat_token, user_id, produit, credits)
  values (p_token, p_user, p_produit, p_credits)
  on conflict (achat_token) do nothing;   -- idempotent : rejoue sans double-créditer
  if found then
    insert into public.oracle_credits (user_id, credits)
    values (p_user, p_credits)
    on conflict (user_id) do update set credits = oracle_credits.credits + excluded.credits, maj = now();
  end if;
end;
$$;
