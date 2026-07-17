/**
 * Synchronisation multi-appareils via Supabase.
 *
 * Objectif : retrouver son carnet, ses points, ses statuts et sa
 * personnalisation sur téléphone ET sur ordinateur.
 *
 * Fonctionnement (sans dépendance : appels `fetch` sur l'API Supabase) :
 *  - Connexion avec un compte Google (flux OAuth « implicite » : la page part
 *    vers Supabase → Google → revient avec un jeton dans l'URL).
 *  - À la connexion et au retour au premier plan : on TIRE les données du
 *    cloud, on les FUSIONNE avec le local (via les fonctions de fusion de
 *    storage.js — jamais de perte), puis on POUSSE le résultat.
 *  - Une table clé/valeur `donnees` (une ligne par catégorie de données),
 *    protégée par RLS : chaque compte ne voit que ses lignes.
 *
 * Ne sont PAS synchronisées : les clés API de l'Oracle (secrètes, propres à
 * l'appareil) et les préférences d'affichage (centre de carte, mode nuit…).
 */

import * as storage from "./storage.js";
import { SUPABASE_URL, SUPABASE_ANON } from "./config/supabase.js";
import { toast } from "./import-export.js";
import { esc } from "./util.js";

const KEY_SESSION = "carte-outdoor:sync-session";

let cb = {}; // { onSynced }
let session = null; // { access_token, refresh_token, expires_at, user, lastSync }
let syncEnCours = false;

/* ------------------------------------------------------------------ */
/* Session (jetons + utilisateur), en localStorage                      */
/* ------------------------------------------------------------------ */

function lireSession() {
  try {
    return JSON.parse(localStorage.getItem(KEY_SESSION)) || null;
  } catch {
    return null;
  }
}
function ecrireSession(s) {
  session = s;
  if (s) localStorage.setItem(KEY_SESSION, JSON.stringify(s));
  else localStorage.removeItem(KEY_SESSION);
}

/** Identifiant du compte, lu dans le jeton (claim `sub`) — sans appel réseau. */
function sujetDuJeton(jwt) {
  try {
    const charge = jwt.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(atob(charge)).sub || null;
  } catch {
    return null;
  }
}

/* ------------------------------------------------------------------ */
/* Authentification (Google via Supabase, flux implicite)               */
/* ------------------------------------------------------------------ */

/** Dernier repli : redirige la page ENTIÈRE vers Google (retour sur l'app avec
 *  le jeton dans l'URL). Utilisé si les popups sont bloqués. */
function connecter() {
  const retour = location.origin + location.pathname;
  location.href =
    `${SUPABASE_URL}/auth/v1/authorize?provider=google` +
    `&redirect_to=${encodeURIComponent(retour)}`;
}

/**
 * Connexion par FENÊTRE (popup) : Google s'ouvre dans une petite fenêtre, la
 * page principale reste en place. Ne dépend PAS de FedCM → fiable partout.
 * Le popup revient sur notre origine avec le jeton ; il l'enregistre (app.js →
 * finaliserPopupAuth) et se ferme, et cette fenêtre est prévenue par
 * l'événement `storage`. Si les popups sont bloqués → redirection pleine page.
 */
function connecterFenetre() {
  const retour = location.origin + location.pathname;
  const url =
    `${SUPABASE_URL}/auth/v1/authorize?provider=google` +
    `&redirect_to=${encodeURIComponent(retour)}`;
  // Le NOM « carte-oauth-popup » persiste à travers les redirections OAuth
  // (propriété de la fenêtre) : c'est ainsi que le popup se reconnaît, même si
  // COOP coupe window.opener.
  const popup = window.open(url, "carte-oauth-popup", "width=480,height=680,menubar=no,toolbar=no");
  if (!popup) connecter(); // popups bloqués → plein écran
}

async function deconnecter() {
  // Révoque le jeton côté serveur (best-effort), puis oublie localement.
  try {
    await fetch(`${SUPABASE_URL}/auth/v1/logout`, {
      method: "POST",
      headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${session?.access_token}` },
    });
  } catch {}
  ecrireSession(null);
  rendreUI();
  toast("Déconnecté de ce compte sur cet appareil.");
}

/**
 * Au chargement, capte le jeton renvoyé par Supabase dans le fragment d'URL
 * (#access_token=…). Renvoie true si on revient tout juste de connexion.
 */
/** Extrait la session d'un fragment d'URL (#access_token=…) et l'enregistre.
 *  Renvoie true si une session valide a été posée. */
function appliquerHash(hash) {
  const p = new URLSearchParams((hash || "").replace(/^#/, ""));
  if (p.get("error")) {
    toast("Connexion annulée : " + (p.get("error_description") || p.get("error")));
    return false;
  }
  const access_token = p.get("access_token");
  if (!access_token) return false;
  ecrireSession({
    access_token,
    refresh_token: p.get("refresh_token"),
    expires_at: Date.now() + Number(p.get("expires_in") || 3600) * 1000,
    user: { id: sujetDuJeton(access_token) },
    lastSync: 0,
  });
  return true;
}

/** Cas « retour de redirection pleine page » : la page revient avec le jeton
 *  dans l'URL. On nettoie l'URL (ne pas laisser traîner un jeton). */
function capterRetour() {
  const hash = location.hash || "";
  if (!hash.includes("access_token=") && !hash.includes("error=")) return false;
  history.replaceState(null, "", location.pathname + location.search);
  return appliquerHash(hash);
}

/**
 * Appelé DEPUIS LE POPUP d'authentification (voir app.js) : enregistre la
 * session dans le localStorage — PARTAGÉ entre fenêtres de même origine, donc
 * la fenêtre principale est prévenue par l'événement `storage` — puis ferme le
 * popup. Robuste même si le lien window.opener est coupé (COOP).
 */
export function finaliserPopupAuth(hash) {
  appliquerHash(hash);
  document.body && (document.body.textContent = "Connexion réussie, vous pouvez fermer cette fenêtre.");
  try {
    window.close();
  } catch {}
}

/** Rafraîchit le jeton d'accès s'il est expiré (ou proche de l'être).
 *  SÉRIALISÉ : Supabase fait tourner les refresh_token (usage unique), donc
 *  deux rafraîchissements simultanés s'invalideraient — un seul à la fois. */
let rafraichissement = null;
async function assurerJeton() {
  if (!session) throw new Error("Non connecté.");
  if (Date.now() < session.expires_at - 60000) return; // encore valable
  if (rafraichissement) return rafraichissement;
  rafraichissement = (async () => {
    const res = await fetch(`${SUPABASE_URL}/auth/v1/token?grant_type=refresh_token`, {
      method: "POST",
      headers: { apikey: SUPABASE_ANON, "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    });
    if (!res.ok) {
      ecrireSession(null); // session expirée/révoquée → on redemande une connexion
      throw new Error("Session expirée, reconnecte-toi.");
    }
    const d = await res.json();
    ecrireSession({
      ...session,
      access_token: d.access_token,
      refresh_token: d.refresh_token || session.refresh_token,
      expires_at: Date.now() + (d.expires_in || 3600) * 1000,
    });
  })().finally(() => {
    rafraichissement = null;
  });
  return rafraichissement;
}

/**
 * Session pour les autres modules (catégories communautaires) : jeton frais +
 * identifiant du compte, ou null si non connecté. Exporté — la connexion Google
 * et le rafraîchissement sérialisé restent gérés ICI, une seule fois.
 */
export async function sessionCommunaute() {
  if (!session) return null;
  try {
    await assurerJeton();
  } catch {
    return null; // session expirée : l'appelant proposera la connexion
  }
  return { token: session.access_token, userId: session.user?.id || null };
}

/** Ouvre la connexion Google (popup, repli pleine page) — pour la communauté. */
export function demanderConnexion() {
  connecterFenetre();
}

/** Récupère l'e-mail/nom du compte (pour l'affichage) — non bloquant. */
async function chargerProfil() {
  try {
    await assurerJeton();
    const res = await fetch(`${SUPABASE_URL}/auth/v1/user`, {
      headers: { apikey: SUPABASE_ANON, Authorization: `Bearer ${session.access_token}` },
    });
    if (!res.ok) return;
    const u = await res.json();
    session.user = {
      id: u.id,
      email: u.email,
      nom: u.user_metadata?.full_name || u.user_metadata?.name || "",
    };
    ecrireSession(session);
    rendreUI();
  } catch {}
}

/* ------------------------------------------------------------------ */
/* Données : quelles clés on synchronise, tirer / fusionner / pousser   */
/* ------------------------------------------------------------------ */

/** Rassemble les données locales à synchroniser (PAS les clés API ni les
 *  préférences d'affichage). Une entrée = une ligne dans la table. */
async function collecterLocal() {
  const carnetTheme = await storage.getCarnetTheme().catch(() => null);
  return {
    statuses: await storage.getStatuses(),
    sorties: await storage.getSorties(),
    journals: await storage.getAllJournals(),
    userPoints: await storage.getUserPoints(),
    tracks: await storage.getTracks(),
    customThemes: await storage.getCustomThemes(),
    themeOverrides: await storage.getThemeOverrides(),
    customPacks: await storage.getCustomPacks(),
    packOverrides: await storage.getPackOverrides(),
    carnetTheme: carnetTheme || undefined,
  };
}

/** Fusionne les données distantes dans le local (jamais de perte pour les
 *  collections ; le distant l'emporte pour les réglages uniques). */
async function appliquerDistant(d) {
  if (d.statuses) await storage.mergeStatuses(d.statuses);
  if (d.sorties) await storage.mergeSorties(d.sorties);
  if (d.journals) await storage.mergeJournals(d.journals);
  if (Array.isArray(d.userPoints) && d.userPoints.length) await storage.addUserPoints(d.userPoints);
  if (Array.isArray(d.tracks)) for (const t of d.tracks) await storage.addTrack(t);
  if (Array.isArray(d.customThemes)) {
    const local = await storage.getCustomThemes();
    const ids = new Set(local.map((t) => t.id));
    await storage.saveCustomThemes([...local, ...d.customThemes.filter((t) => !ids.has(t.id))]);
  }
  if (d.themeOverrides) {
    await storage.saveThemeOverrides({ ...(await storage.getThemeOverrides()), ...d.themeOverrides });
  }
  if (Array.isArray(d.customPacks)) {
    const local = await storage.getCustomPacks();
    const ids = new Set(local.map((p) => p.id));
    await storage.saveCustomPacks([...local, ...d.customPacks.filter((p) => !ids.has(p.id))]);
  }
  if (d.packOverrides) {
    await storage.savePackOverrides({ ...(await storage.getPackOverrides()), ...d.packOverrides });
  }
  if (d.carnetTheme) await storage.saveCarnetTheme(d.carnetTheme);
}

/** Empreinte des volumes locaux : sert à détecter si un tirage a apporté des
 *  nouveautés (→ on recharge alors la page pour tout refléter proprement). */
async function empreinte() {
  const [s, so, j, p, t, c] = await Promise.all([
    storage.getStatuses(),
    storage.getSorties(),
    storage.getAllJournals(),
    storage.getUserPoints(),
    storage.getTracks(),
    storage.getCustomThemes(),
  ]);
  const nbNotes = Object.values(j).reduce((n, e) => n + e.length, 0);
  return JSON.stringify([Object.keys(s).length, so.length, nbNotes, p.length, t.length, c.length]);
}

/** Requête REST authentifiée sur la base (PostgREST). */
async function api(chemin, options = {}) {
  await assurerJeton();
  const res = await fetch(`${SUPABASE_URL}/rest/v1${chemin}`, {
    ...options,
    headers: {
      apikey: SUPABASE_ANON,
      Authorization: `Bearer ${session.access_token}`,
      ...(options.headers || {}),
    },
  });
  if (!res.ok) {
    const t = await res.text().catch(() => "");
    throw new Error(`Supabase ${res.status} : ${t.slice(0, 120)}`);
  }
  return res;
}

async function tirer() {
  const res = await api("/donnees?select=cle,valeur");
  const lignes = await res.json();
  const obj = {};
  for (const l of lignes) obj[l.cle] = l.valeur;
  return obj;
}

async function pousser(local) {
  const rows = Object.entries(local)
    .filter(([, v]) => v !== undefined && v !== null)
    .map(([cle, valeur]) => ({
      user_id: session.user.id,
      cle,
      valeur,
      updated_at: new Date().toISOString(),
    }));
  if (!rows.length) return;
  await api("/donnees", {
    method: "POST",
    headers: { "Content-Type": "application/json", Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify(rows),
  });
}

/* ------------------------------------------------------------------ */
/* Orchestration                                                        */
/* ------------------------------------------------------------------ */

async function synchroniser(manuel = false) {
  if (!session || syncEnCours) return;
  syncEnCours = true;
  majStatut("Synchronisation…", true);
  try {
    const distant = await tirer();
    const avant = await empreinte();
    await appliquerDistant(distant);
    const apres = await empreinte();
    await pousser(await collecterLocal());
    session.lastSync = Date.now();
    ecrireSession(session);
    // Le distant a apporté des nouveautés → on recharge pour tout refléter
    // (points, carnet, traces, thèmes) sans risque d'affichage partiel.
    if (avant !== apres) {
      majStatut("Nouvelles données reçues — actualisation…");
      toast("Carnet et points synchronisés !");
      setTimeout(() => location.reload(), 900);
    } else {
      await cb.onSynced?.(); // rafraîchit thèmes/statuts en place
      majStatut("À jour");
      if (manuel) toast("Déjà à jour sur cet appareil.");
    }
  } catch (e) {
    console.warn("Synchronisation impossible :", e);
    majStatut("Échec — " + (e.message || "réessaie plus tard"));
    if (manuel) toast("Synchronisation impossible : " + (e.message || "réessaie"));
  } finally {
    syncEnCours = false;
    rendreUI();
  }
}

/* ------------------------------------------------------------------ */
/* Interface (dans le dialogue ⚙️ Réglages)                             */
/* ------------------------------------------------------------------ */

let zone = null;

function majStatut(texte, charge = false) {
  const el = zone?.querySelector(".sync-statut");
  if (el) {
    el.textContent = texte;
    el.classList.toggle("sync-charge", charge);
  }
}

function rendreUI() {
  if (!zone) return;
  if (!session) {
    zone.innerHTML = `
      <p class="menu-note">Connecte-toi pour retrouver ton carnet, tes points et ton suivi
        sur tous tes appareils. Tes clés API et ton affichage restent, eux, sur cet appareil.</p>
      <button type="button" class="btn btn-secondary sync-connexion">
        <span aria-hidden="true">🔵</span> Se connecter avec Google</button>
      <p class="menu-note">Une petite fenêtre Google s'ouvre ; l'application reste ouverte derrière.</p>`;
    zone.querySelector(".sync-connexion").addEventListener("click", connecterFenetre);
    return;
  }
  const qui = esc(session.user?.email || session.user?.nom || "compte connecté");
  const quand = session.lastSync
    ? new Date(session.lastSync).toLocaleString("fr-FR", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })
    : "jamais";
  zone.innerHTML = `
    <p class="menu-note">Connecté : <strong>${qui}</strong></p>
    <p class="sync-statut menu-note"></p>
    <div class="sync-actions">
      <button type="button" class="btn btn-secondary sync-maintenant">🔄 Synchroniser maintenant</button>
      <button type="button" class="btn btn-secondary sync-deconnexion">Se déconnecter</button>
    </div>
    <p class="menu-note">Dernière synchro : ${esc(quand)}.</p>`;
  zone.querySelector(".sync-maintenant").addEventListener("click", () => synchroniser(true));
  zone.querySelector(".sync-deconnexion").addEventListener("click", deconnecter);
}

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */

export function initSync(callbacks) {
  cb = callbacks || {};
  zone = document.getElementById("sync-zone");
  session = lireSession();

  const retourDeConnexion = capterRetour();
  rendreUI();

  // Connexion/déconnexion venue d'une AUTRE fenêtre : le popup d'authentification
  // écrit la session dans le localStorage PARTAGÉ → l'événement `storage` nous
  // prévient ici (robuste même si COOP a coupé window.opener).
  window.addEventListener("storage", (e) => {
    if (e.key !== KEY_SESSION) return;
    const s = lireSession();
    if (s && !session) {
      session = s;
      rendreUI();
      chargerProfil();
      synchroniser(true);
    } else if (!s && session) {
      session = null;
      rendreUI();
    }
  });

  // Sync au retour au premier plan, quand on est connecté.
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden && session && !syncEnCours) synchroniser(false);
  });

  if (session) {
    chargerProfil(); // e-mail/nom pour l'affichage
    synchroniser(retourDeConnexion);
  }
}
