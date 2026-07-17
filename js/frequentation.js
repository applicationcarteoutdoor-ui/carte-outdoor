/**
 * Fréquentation ANONYME : « combien de personnes utilisent la carte ? ».
 *
 * L'app envoie un « ping » de présence (RPC Supabase `signaler_presence`) au
 * chargement puis toutes les 4 minutes tant que l'onglet est visible. Côté
 * serveur : une ligne (visiteur, jour) — voir supabase/frequentation-schema.sql.
 *
 * Vie privée :
 *  - l'identifiant visiteur est un UUID TIRÉ AU HASARD, stocké en localStorage,
 *    jamais lié au compte Google, jamais exporté ni synchronisé ;
 *  - aucune position, aucune IP, aucun nom ne partent d'ici ;
 *  - la table est invisible via l'API (RLS sans policy) : seuls des TOTAUX
 *    ressortent (stats_frequentation).
 *
 * Tant que le SQL n'a pas été exécuté côté Supabase, tout échoue en silence
 * (ping) et les stats affichent un message doux.
 */

import { SUPABASE_URL, SUPABASE_ANON } from "./config/supabase.js";

const CLE_VISITEUR = "carte-outdoor:visiteur";
const PERIODE_PING_MS = 4 * 60 * 1000;

function idVisiteur() {
  let id = localStorage.getItem(CLE_VISITEUR);
  if (!id) {
    id = crypto.randomUUID ? crypto.randomUUID()
      // repli très vieux navigateurs : pseudo-UUID v4
      : "xxxxxxxx-xxxx-4xxx-8xxx-xxxxxxxxxxxx".replace(/x/g,
          () => Math.floor(Math.random() * 16).toString(16));
    localStorage.setItem(CLE_VISITEUR, id);
  }
  return id;
}

async function rpc(nom, corps) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/rpc/${nom}`, {
    method: "POST",
    headers: {
      apikey: SUPABASE_ANON,
      Authorization: `Bearer ${SUPABASE_ANON}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(corps || {}),
  });
  if (!res.ok) throw new Error(String(res.status));
  const texte = await res.text();
  return texte ? JSON.parse(texte) : null;
}

/** Démarre les pings de présence (silencieux, jamais bloquant). */
export function initFrequentation() {
  const ping = () => rpc("signaler_presence", { p_visiteur: idVisiteur() }).catch(() => {});
  ping();
  setInterval(() => { if (!document.hidden) ping(); }, PERIODE_PING_MS);
  document.addEventListener("visibilitychange", () => { if (!document.hidden) ping(); });
}

/** Totaux { maintenant, aujourdhui, semaine }, ou null si indisponible. */
export async function statsFrequentation() {
  try {
    return await rpc("stats_frequentation");
  } catch {
    return null;
  }
}
