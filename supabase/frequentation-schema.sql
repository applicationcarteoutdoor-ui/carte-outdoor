-- Fréquentation ANONYME de SpotMap : « combien de personnes utilisent la carte
-- en ce moment / aujourd'hui / cette semaine ». À exécuter une fois dans
-- l'éditeur SQL Supabase (comme communaute-schema.sql). Voir docs/FREQUENTATION.md.
--
-- Vie privée : on ne stocke QU'UN identifiant aléatoire par navigateur (UUID
-- tiré au hasard, jamais lié au compte, jamais exporté) et des horodatages.
-- Aucune IP, aucun nom, aucune position. La table est INVISIBLE via l'API
-- (RLS sans policy) : seuls les deux appels ci-dessous passent, et le second
-- ne renvoie que des TOTAUX.

create table if not exists public.frequentation (
  visiteur uuid not null,
  jour     date not null default (now() at time zone 'utc')::date,
  vu_le    timestamptz not null default now(),
  primary key (visiteur, jour)
);

alter table public.frequentation enable row level security; -- aucune policy : accès API bloqué

create index if not exists idx_frequentation_vu_le on public.frequentation (vu_le);

-- Le « ping » de présence : l'app l'appelle au chargement puis toutes les
-- 4 minutes tant qu'elle est ouverte. Upsert (1 ligne par visiteur et par
-- jour) + ménage des traces de plus de 90 jours.
create or replace function public.signaler_presence(p_visiteur uuid)
returns void
language sql
security definer
as $$
  delete from public.frequentation where vu_le < now() - interval '90 days';
  insert into public.frequentation (visiteur)
  values (p_visiteur)
  on conflict (visiteur, jour) do update set vu_le = now();
$$;

-- Les statistiques AGRÉGÉES (les seules données lisibles de l'extérieur) :
--   maintenant  = visiteurs actifs dans les 5 dernières minutes
--   aujourdhui  = visiteurs distincts du jour (UTC)
--   semaine     = visiteurs distincts sur 7 jours glissants
create or replace function public.stats_frequentation()
returns json
language sql
security definer
as $$
  select json_build_object(
    'maintenant', (select count(distinct visiteur) from public.frequentation
                    where vu_le > now() - interval '5 minutes'),
    'aujourdhui', (select count(*) from public.frequentation
                    where jour = (now() at time zone 'utc')::date),
    'semaine',    (select count(distinct visiteur) from public.frequentation
                    where vu_le > now() - interval '7 days')
  );
$$;
