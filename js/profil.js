/**
 * Profil utilisateur + badges (v77) — 100 % LOCAL.
 *
 * Tout se calcule depuis les données du téléphone (statuts « ✓ Fait »,
 * sorties du carnet, traces GPX) — rien ne part sur un serveur. Le pseudo et
 * l'avatar (emoji) vivent dans les prefs et suivent la sync si l'utilisateur
 * est connecté (comme le reste des prefs légères).
 *
 * app.js fournit les getters (statuts/sorties/traces + un résolveur de points
 * TOUS pays, comme le carnet). Rien d'autre à câbler.
 */

import { BADGES, valeurMetrique } from "./config/badges.js";
import { getTheme } from "./config/themes.js";
import { PAYS } from "./config/pays.js";
import * as storage from "./storage.js";
import { esc } from "./util.js";

let dialog = null;
let cb = {}; // { getStatuses, getSorties, getTracks, resoudrePoints, statsGpx }

// Les points ÉTRANGERS ont l'id `<iso>-<abréviation>-<numéro>` (ex.
// ch-ref-0001, nz-hut-0001). ⚠️ Un château FRANÇAIS est « ch-0002 » (ch =
// château, PAS la Suisse) : d'où le `-<lettres>-<chiffre>` obligatoire après
// l'iso, sinon la France serait comptée comme deux pays.
const ISO = Object.keys(PAYS).filter((i) => i !== "fr"); // ch, it, es, pt, de, nl, lu, be, nz
const RE_ISO = new RegExp(`^(${ISO.join("|")})-[a-z]{2,}-\\d`);

/** Pays d'un id de point : préfixe ISO étranger, ou France par défaut.
 *  Les points perso/communautaires (perso-, comm-…) ne comptent pas. */
function paysDeId(id) {
  if (/^(perso-|comm-|selection-)/.test(id)) return null;
  const m = RE_ISO.exec(id);
  return m ? m[1] : "fr";
}

/** Agrège toutes les statistiques locales pour le profil et les badges. */
async function calculerStats() {
  const statuses = await cb.getStatuses();
  const sorties = await cb.getSorties();
  const carte = await cb.resoudrePoints(); // Map<id, feature> tous pays

  const faits = Object.entries(statuses).filter(([, s]) => s === "fait").map(([id]) => id);
  const paysVus = new Set();
  const parTheme = {};
  const parPays = {};
  for (const id of faits) {
    const p = paysDeId(id);
    if (p) { paysVus.add(p); parPays[p] = (parPays[p] || 0) + 1; }
    const f = carte.get(id);
    if (f) {
      const t = getTheme(f.properties.theme).id;
      parTheme[t] = (parTheme[t] || 0) + 1;
    }
  }

  // traces GPX : distance + D+ cumulés (chaque trace porte déjà ses `stats`,
  // calculées à l'import par gpx.js)
  const tracks = await cb.getTracks().catch(() => []);
  let km = 0;
  let dplus = 0;
  for (const tr of tracks) {
    const s = tr.stats;
    if (s) { km += s.distanceKm || 0; dplus += s.dplus || 0; }
  }

  // sorties datées, pour la rétrospective de l'année
  const annees = {};
  for (const s of sorties) {
    if (s.date) {
      const a = s.date.slice(0, 4);
      annees[a] = (annees[a] || 0) + 1;
    }
  }

  return {
    sorties: sorties.length,
    lieux: faits.length,
    pays: paysVus.size,
    categories: Object.keys(parTheme).length,
    km: Math.round(km),
    dplus: Math.round(dplus),
    parTheme,
    parPays,
    annees,
  };
}

function carteStat(valeur, libelle, icone) {
  return `<div class="profil-stat"><span class="profil-stat-ico" aria-hidden="true">${icone}</span>
    <strong>${valeur.toLocaleString("fr-FR")}</strong><span>${esc(libelle)}</span></div>`;
}

function badgeHTML(badge, stats) {
  const val = valeurMetrique(badge.metrique, stats);
  const obtenu = val >= badge.palier;
  const pourcent = Math.min(100, Math.round((val / badge.palier) * 100));
  return `
    <div class="profil-badge${obtenu ? " obtenu" : ""}" title="${esc(badge.description)}">
      <span class="profil-badge-ico" aria-hidden="true">${badge.icone}</span>
      <span class="profil-badge-titre">${esc(badge.titre)}</span>
      <span class="profil-badge-jauge"><span style="width:${pourcent}%"></span></span>
      <span class="profil-badge-compte">${obtenu ? "✓ " + badge.description : `${val} / ${badge.palier}`}</span>
    </div>`;
}

async function rendre() {
  const prefs = await storage.getPrefs();
  const pseudo = prefs.profilPseudo || "Aventurier·ère";
  const avatar = prefs.profilAvatar || "🧗";
  const stats = await calculerStats();
  const obtenus = BADGES.filter((b) => valeurMetrique(b.metrique, stats) >= b.palier).length;

  // rétrospective : l'année en cours (ou la plus récente enregistrée)
  const anneeCourante = Object.keys(stats.annees).sort().pop();
  const retro = anneeCourante
    ? `<p class="profil-retro">📅 <strong>${stats.annees[anneeCourante]}</strong> sortie(s) en ${anneeCourante}
        — continuez comme ça !</p>` : "";

  const corps = dialog.querySelector(".profil-corps");
  corps.innerHTML = `
    <div class="profil-entete">
      <button type="button" class="profil-avatar" title="Changer d'avatar">${avatar}</button>
      <div class="profil-ident">
        <input type="text" class="profil-pseudo" value="${esc(pseudo)}" maxlength="24" aria-label="Votre pseudo">
        <span class="profil-sous">${obtenus} / ${BADGES.length} badges débloqués</span>
      </div>
    </div>
    <div class="profil-stats">
      ${carteStat(stats.lieux, "lieux visités", "📍")}
      ${carteStat(stats.sorties, "sorties", "📖")}
      ${carteStat(stats.pays, "pays", "🌍")}
      ${carteStat(stats.categories, "catégories", "🎨")}
      ${carteStat(stats.km, "km (GPX)", "👟")}
      ${carteStat(stats.dplus, "m de D+", "🏔️")}
    </div>
    ${retro}
    <h3 class="profil-titre-badges">🏅 Mes badges</h3>
    <div class="profil-badges">${BADGES.map((b) => badgeHTML(b, stats)).join("")}</div>
    <p class="menu-note">Tout est calculé sur votre téléphone, à partir de vos lieux « ✓ Fait »,
      de votre carnet et de vos traces GPX. Rien n'est envoyé sur un serveur.</p>`;

  // pseudo : enregistré à la volée
  corps.querySelector(".profil-pseudo").addEventListener("change", (e) => {
    storage.savePrefs({ profilPseudo: e.target.value.trim().slice(0, 24) || "Aventurier·ère" });
  });
  // avatar : petit choix d'emojis
  corps.querySelector(".profil-avatar").addEventListener("click", async () => {
    const choix = ["🧗", "🥾", "🏔️", "🚵", "🏕️", "🧭", "🦉", "🐾", "🌲", "⛰️", "🏄", "🤿", "🦌", "🌟"];
    const actuel = (await storage.getPrefs()).profilAvatar || "🧗";
    const suivant = choix[(choix.indexOf(actuel) + 1) % choix.length];
    await storage.savePrefs({ profilAvatar: suivant });
    rendre();
  });
}

export function initProfil(callbacks) {
  cb = callbacks;
  dialog = document.getElementById("profil-dialog");
  dialog.querySelector(".profil-close").addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (e) => { if (e.target === dialog) dialog.close(); });
  document.getElementById("btn-profil").addEventListener("click", () => {
    // Ouvrir TOUT DE SUITE (le calcul charge les points de tous les pays :
    // on montre un état de chargement plutôt qu'un délai à vide).
    dialog.querySelector(".profil-corps").innerHTML =
      `<p class="menu-note" style="text-align:center;padding:24px">Calcul de vos statistiques…</p>`;
    dialog.showModal();
    rendre();
  });
}
