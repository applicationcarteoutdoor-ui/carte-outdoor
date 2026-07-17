# Fréquentation — savoir combien de personnes utilisent SpotMap

## Ce que ça donne

Dans **⚙️ Réglages → 📊 Fréquentation**, l'app affiche :

- **En ce moment** : visiteurs actifs dans les 5 dernières minutes ;
- **Aujourd'hui** : visiteurs distincts du jour ;
- **7 jours** : visiteurs distincts de la semaine glissante.

## Mise en service (une fois, ~2 minutes)

1. Ouvrir [le tableau de bord Supabase](https://supabase.com/dashboard) → ton
   projet (le même que la synchronisation) → **SQL Editor**.
2. Copier-coller le contenu de `supabase/frequentation-schema.sql` → **Run**.
3. C'est tout : l'app pinge déjà, les compteurs se remplissent dès la
   prochaine visite. Tant que le SQL n'est pas exécuté, l'app ne casse rien
   (échecs silencieux, message doux dans Réglages).

## Comment ça marche (et la vie privée)

- Chaque navigateur tire **un UUID au hasard** (localStorage
  `carte-outdoor:visiteur`) — jamais lié au compte Google, jamais exporté,
  jamais synchronisé.
- L'app appelle `signaler_presence` au chargement puis toutes les 4 minutes
  quand l'onglet est visible → une ligne `(visiteur, jour)` upsertée.
- **Aucune IP, aucun nom, aucune position** ne sont stockés ; la table est
  invisible via l'API (RLS sans policy), seuls les **totaux** sortent
  (`stats_frequentation`). Les traces de plus de 90 jours s'effacent seules.
- Pas de cookie tiers, pas de consentement requis (pas de donnée personnelle).

## Voir plus de détail (optionnel)

Dans l'éditeur SQL Supabase :

```sql
-- courbe des visiteurs par jour (30 derniers jours)
select jour, count(*) as visiteurs
from frequentation
where jour > current_date - 30
group by jour order by jour;
```

## Alternatives si un jour tu veux plus (pages vues, pays, appareils)

- **GoatCounter** (gratuit, open source, sans cookie) : créer un compte sur
  goatcounter.com puis ajouter leur `<script>` à `index.html` **et** son
  domaine à la CSP (`script-src`/`connect-src`) — à faire par toi.
- **Cloudflare Web Analytics** (gratuit, sans cookie) : nécessite de passer le
  DNS chez Cloudflare — plus lourd.

Le compteur Supabase ci-dessus reste la solution la plus simple : zéro compte
en plus, zéro cookie, et il répond à la question « combien de monde ? ».
