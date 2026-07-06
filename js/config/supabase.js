/**
 * Configuration Supabase (synchronisation multi-appareils).
 *
 * L'URL et la clé « anon » sont PUBLIQUES par conception : la sécurité repose
 * entièrement sur le Row Level Security (RLS) côté base — chaque compte ne peut
 * lire/écrire QUE ses propres lignes (vérifié : une écriture sans compte est
 * refusée). Il est donc normal et sans danger qu'elles figurent dans le code.
 *
 * Pour changer de projet Supabase, il suffit de modifier ces deux constantes
 * (et d'ajouter le domaine à la CSP dans index.html).
 */
export const SUPABASE_URL = "https://xwrqqhvqyccgtkslexbu.supabase.co";
export const SUPABASE_ANON =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Inh3cnFxaHZxeWNjZ3Rrc2xleGJ1Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODMzNTY1MjQsImV4cCI6MjA5ODkzMjUyNH0.GSDts7VxvpbQkUt46tlcF5LyWKmBlxSHpPlAnJjSMQg";
