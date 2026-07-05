/**
 * Point d'entrée de l'application : charge les données, initialise les
 * modules (carte, panneau des catégories, filtres, fiche, import/export,
 * traces, ajout de point, tuto, boîte à idées) et les relie entre eux.
 * Tout l'état partagé vit ici.
 */

import {
  THEMES,
  getTheme,
  setThemeOverrides,
  registerCustomThemes,
} from "./config/themes.js";
import * as storage from "./storage.js";
import {
  initMap,
  setPoints,
  focusPoint,
  setGrVisible,
  toggleLocate,
  highlightPoint,
  clearHighlight,
  montrerRayon,
} from "./map.js";
import { initFilters, renderFilters } from "./filters.js";
import {
  initDetails,
  openDetails,
  closeDetails,
  refreshDetailsIfOpen,
  getOpenPointId,
} from "./details.js";
import { initSidebar, renderSidebar, refreshTraces, closeSidebar } from "./sidebar.js";
import { initImportExport, toast, confirmer } from "./import-export.js";
import { initGpx, setAllTracesVisible } from "./gpx.js";
import { initAddPoint } from "./addpoint.js";
import { initTuto, startTuto } from "./tuto.js";
import { initIdeas } from "./ideas.js";
import { initCarnet, exporterCarnetPDF } from "./carnet.js";
import { SUR_ANDROID, SUR_IOS } from "./config/platform.js";

/** État global de l'application. */
const state = {
  allPoints: [], // features des données par défaut + points importés/ajoutés
  userPointIds: new Set(), // ids des points ajoutés/importés (supprimables un à un)
  statuses: {}, // { idDuPoint: "fait" | "a-faire" | "favori" }
  activeThemes: new Set(), // catégories cochées
  statusFilters: new Set(), // statuts cochés (vide = pas de filtre de suivi)
  filterSelections: {}, // { themeId: { filterKey: Set(valeurs) } }
  filtersCollapsed: false,
  tracesVisible: true,
  grVisible: false,
};

/* ------------------------------------------------------------------ */
/* Chargement des données                                               */
/* ------------------------------------------------------------------ */

/** Toilettes (data/toilettes.geojson, volumineux) : fichier séparé non
 *  pré-caché, chargé à la première activation de la catégorie ou du bouton
 *  « toilettes autour de moi ». */
let pointsToilettes = [];

/** Indices du cycle « flèche ➤ » (clics successifs → point suivant). */
const cycleUserPoint = {};

/** Bandeau « données escalade partielles » : la croix le ferme, mais il
 *  réapparaît à chaque nouvelle activation de la catégorie Escalade. */
let bandeauEscaladeFerme = false;

/** Invite d'installation PWA (Android/Chrome) : capturée au niveau module —
 *  beforeinstallprompt peut arriver avant la fin du démarrage. */
let evenementInstallation = null;
window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault(); // pas de mini-bandeau du navigateur : notre bouton s'en charge
  evenementInstallation = e;
});

async function chargerPoints() {
  let defauts = [];
  try {
    const reponse = await fetch("data/points.geojson");
    defauts = (await reponse.json()).features || [];
  } catch (e) {
    console.error("Impossible de charger data/points.geojson :", e);
  }
  const importes = await storage.getUserPoints().catch(() => []);
  state.userPointIds = new Set(importes.map((f) => f.properties.id));
  const parId = new Map();
  for (const f of [...defauts, ...pointsToilettes, ...importes]) parId.set(f.properties.id, f);
  state.allPoints = [...parId.values()];
}

/** Charge les toilettes si nécessaire ; renvoie false en cas d'échec. */
async function chargerToilettes() {
  if (pointsToilettes.length) return true;
  toast("Chargement des toilettes…");
  try {
    const reponse = await fetch("data/toilettes.geojson");
    pointsToilettes = (await reponse.json()).features || [];
    await chargerPoints();
    return true;
  } catch (e) {
    console.error("Impossible de charger data/toilettes.geojson :", e);
    toast("Toilettes indisponibles pour le moment (hors connexion ?).");
    return false;
  }
}

/* ------------------------------------------------------------------ */
/* Filtrage                                                             */
/* ------------------------------------------------------------------ */

function compteursParTheme() {
  const compteurs = new Map();
  for (const f of state.allPoints) {
    const id = getTheme(f.properties.theme).id;
    compteurs.set(id, (compteurs.get(id) || 0) + 1);
  }
  // Toilettes pas encore chargées : « … » plutôt qu'un 0 trompeur
  if (!pointsToilettes.length) compteurs.set("toilettes", "…");
  return compteurs;
}

/** Nombre de points ajoutés/importés par l'utilisateur, par catégorie —
 *  pour la petite flèche « retrouver mes points » du panneau gauche. */
function compteursPointsUtilisateur() {
  const compteurs = new Map();
  for (const f of state.allPoints) {
    if (state.userPointIds.has(f.properties.id)) {
      const id = getTheme(f.properties.theme).id;
      compteurs.set(id, (compteurs.get(id) || 0) + 1);
    }
  }
  return compteurs;
}

function compteursParStatut() {
  const compteurs = { "a-faire": 0, fait: 0, favori: 0 };
  for (const s of Object.values(state.statuses)) {
    if (s in compteurs) compteurs[s]++;
  }
  return compteurs;
}

const RE_TOKENS = /\b(ED|TD|AD|PD|F|D)\b/g;

/** Applique un filtre déclaré dans themes.js à un point. */
function passeFiltre(filtre, details, selection) {
  if (!selection || selection.size === 0) return true; // « Tout »
  const brut = details?.[filtre.field];
  switch (filtre.type) {
    case "tokens": {
      const tokens = String(brut || "").match(RE_TOKENS) || [];
      return tokens.some((t) => selection.has(t));
    }
    case "prefix":
      return [...selection].some((v) => String(brut || "").startsWith(v));
    case "contains":
      return [...selection].some((v) => String(brut || "").includes(v));
    case "value":
      return selection.has(String(brut ?? ""));
    case "bucket": {
      const n = Number(brut);
      if (!Number.isFinite(n)) return false;
      return filtre.options.some(
        (o) =>
          selection.has(o.value) &&
          (o.min === undefined || n >= o.min) &&
          (o.max === undefined || n < o.max)
      );
    }
  }
  return true;
}

function pointsVisibles() {
  // Mode suivi : un statut coché (★ ✓ ♥) affiche TOUS les points suivis,
  // même si leur catégorie d'origine n'est pas cochée. Les deux modes sont
  // exclusifs (cocher l'un décoche l'autre, voir initSidebar).
  if (state.statusFilters.size) {
    return state.allPoints.filter((f) =>
      state.statusFilters.has(state.statuses[f.properties.id])
    );
  }
  const filtresParTheme = new Map(THEMES.map((t) => [t.id, t.filters]));
  return state.allPoints.filter((f) => {
    const themeId = getTheme(f.properties.theme).id;
    if (!state.activeThemes.has(themeId)) return false;
    const filtres = filtresParTheme.get(themeId) || [];
    const selections = state.filterSelections[themeId] || {};
    return filtres.every((filtre) =>
      passeFiltre(filtre, f.properties.details, selections[filtre.key])
    );
  });
}

/* ------------------------------------------------------------------ */
/* Rendu global + persistance                                           */
/* ------------------------------------------------------------------ */

function rafraichir() {
  renderSidebar({
    counts: compteursParTheme(),
    userPointCounts: compteursPointsUtilisateur(),
    activeThemes: state.activeThemes,
    statusFilters: state.statusFilters,
    statusCounts: compteursParStatut(),
    grVisible: state.grVisible,
    tracesVisible: state.tracesVisible,
  });
  renderFilters({
    activeThemes: state.activeThemes,
    filterSelections: state.filterSelections,
    collapsed: state.filtersCollapsed,
    statusActif: state.statusFilters.size > 0,
  });
  setPoints(pointsVisibles(), state.statuses);
  document.getElementById("banner-escalade").hidden = 
    !state.activeThemes.has("escalade") || bandeauEscaladeFerme;
  storage.savePrefs({
    activeThemes: [...state.activeThemes],
    statusFilters: [...state.statusFilters],
    filterSelections: Object.fromEntries(
      Object.entries(state.filterSelections).map(([theme, filtres]) => [
        theme,
        Object.fromEntries(Object.entries(filtres).map(([cle, sel]) => [cle, [...sel]])),
      ])
    ),
    filtersCollapsed: state.filtersCollapsed,
    tracesVisible: state.tracesVisible,
    grVisible: state.grVisible,
  });
}

/* ------------------------------------------------------------------ */
/* Actions                                                              */
/* ------------------------------------------------------------------ */

function ouvrirFiche(feature) {
  highlightPoint(feature.properties.id); // épingle agrandie + halo
  openDetails(feature, state.statuses[feature.properties.id]);
}

async function changerStatut(pointId, statut) {
  const avant = state.statuses[pointId];
  state.statuses = await storage.setStatus(pointId, statut);
  // Le carnet s'alimente tout seul : passer à « fait » enregistre une sortie
  // datée ; décocher le jour même l'annule (faux clic), l'historique ancien
  // reste.
  if (statut === "fait" && avant !== "fait") await storage.addSortie(pointId);
  if (avant === "fait" && statut !== "fait") await storage.deleteSortieDuJour(pointId);
  setPoints(pointsVisibles(), state.statuses);
  refreshDetailsIfOpen(pointId, statut);
  renderSidebar({
    counts: compteursParTheme(),
    userPointCounts: compteursPointsUtilisateur(),
    activeThemes: state.activeThemes,
    statusFilters: state.statusFilters,
    statusCounts: compteursParStatut(),
    grVisible: state.grVisible,
    tracesVisible: state.tracesVisible,
  });
}

function allerAuPoint(feature) {
  const themeId = getTheme(feature.properties.theme).id;
  let change = false;
  // En mode suivi, si le point demandé n'y figure pas, on repasse en mode
  // catégories (sinon il resterait invisible malgré le recentrage).
  if (state.statusFilters.size && !state.statusFilters.has(state.statuses[feature.properties.id])) {
    state.statusFilters.clear();
    change = true;
  }
  if (!state.statusFilters.size && !state.activeThemes.has(themeId)) {
    state.activeThemes.add(themeId);
    change = true;
  }
  if (change) rafraichir();
  focusPoint(feature);
  ouvrirFiche(feature);
}

/** Supprime un point ajouté/importé par l'utilisateur (quelle que soit sa catégorie). */
async function supprimerPoint(feature) {
  const nom = feature.properties.name;
  const ok = await confirmer(`Supprimer le point « ${nom} » ? Cette action est définitive.`);
  if (!ok) return;
  await storage.deleteUserPoint(feature.properties.id);
  await storage.deleteJournal(feature.properties.id).catch(() => {});
  await storage.deleteSortiesDuPoint(feature.properties.id).catch(() => {});
  state.statuses = await storage.setStatus(feature.properties.id, null);
  closeDetails();
  await chargerPoints();
  rafraichir();
  toast(`Point « ${nom} » supprimé.`);
}

async function apresImportPoints(features) {
  await chargerPoints();
  state.statuses = await storage.getStatuses();
  if (features.length) state.statusFilters.clear(); // les nouveaux points doivent être visibles
  for (const f of features) state.activeThemes.add(getTheme(f.properties.theme).id);
  rafraichir();
}

/* ------------------------------------------------------------------ */
/* Recherche (dans le panneau des catégories)                           */
/* ------------------------------------------------------------------ */

function normaliser(texte) {
  return texte
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

function initRecherche() {
  const input = document.getElementById("search-input");
  const resultats = document.getElementById("search-results");

  input.addEventListener("input", () => {
    const requete = normaliser(input.value.trim());
    resultats.textContent = "";
    if (requete.length < 2) return;
    const trouves = state.allPoints
      .filter((f) => normaliser(f.properties.name).includes(requete))
      .slice(0, 12);
    for (const f of trouves) {
      const theme = getTheme(f.properties.theme);
      const item = document.createElement("button");
      item.type = "button";
      item.className = "search-result";
      item.innerHTML =
        `<span class="group-icon" style="--pin-color:${theme.color};--pin-text:${theme.textColor}" aria-hidden="true">${theme.icon}</span>` +
        `<span class="search-result-text"><strong></strong><small>${theme.label}</small></span>`;
      item.querySelector("strong").textContent = f.properties.name;
      item.addEventListener("click", () => {
        input.value = "";
        resultats.textContent = "";
        if (window.innerWidth < 900) closeSidebar();
        allerAuPoint(f);
      });
      resultats.appendChild(item);
    }
    if (!trouves.length) {
      resultats.innerHTML = '<p class="list-empty">Aucun point trouvé.</p>';
    }
  });

  input.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      input.value = "";
      resultats.textContent = "";
    }
    if (e.key === "Enter") {
      e.preventDefault();
      resultats.querySelector(".search-result")?.click();
    }
  });
}

/* ------------------------------------------------------------------ */
/* Toilettes autour de moi (bouton 🏃🚻)                                 */
/* ------------------------------------------------------------------ */

function distanceM(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180;
  const x =
    Math.sin(((lat2 - lat1) * rad) / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2;
  return 2 * 6371000 * Math.asin(Math.sqrt(x));
}

/** Dialogue d'avertissement à l'activation de la catégorie Toilettes.
 *  @returns {Promise<"valider"|"retour"|"proximite">} */
function demanderModeToilettes() {
  const dlg = document.getElementById("wc-dialog");
  dlg.showModal();
  return new Promise((resolve) => {
    const repondre = (choix) => {
      if (dlg.open) dlg.close();
      resolve(choix);
    };
    dlg.querySelector(".wc-valider").onclick = () => repondre("valider");
    dlg.querySelector(".wc-retour").onclick = () => repondre("retour");
    dlg.querySelector(".wc-proximite").onclick = () => repondre("proximite");
    dlg.oncancel = () => resolve("retour"); // touche Échap
  });
}

/** Géolocalise puis affiche les toilettes seules, autour de la position
 *  (cercle de 1 km). Utilisé par le bouton 🏃🚻 et par l'avertissement. */
async function toilettesAutourDeMoi() {
  const bouton = document.getElementById("btn-wc");
  bouton.disabled = true;
  try {
    toast("Recherche de votre position…");
    const [lat, lon] = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
        reject,
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
    if (!(await chargerToilettes())) return;
    // Vue « toilettes seules », centrée sur la position, rayon de 1 km.
    // Le zoom se fait AVANT le rendu : les marqueurs se remplissent en
    // priorité autour de la position (tri par distance dans setPoints).
    montrerRayon(lat, lon, 1000);
    state.activeThemes = new Set(["toilettes"]);
    state.statusFilters.clear();
    rafraichir();
    const distances = pointsToilettes.map((f) =>
      distanceM(lat, lon, f.geometry.coordinates[1], f.geometry.coordinates[0])
    );
    const proches = distances.filter((d) => d <= 1000).length;
    if (proches) {
      toast(`${proches} toilettes à moins de 1 km.`);
    } else {
      const mini = Math.min(...distances);
      toast(Number.isFinite(mini)
        ? `Aucunes toilettes à moins de 1 km — la plus proche est à ${(mini / 1000).toFixed(1)} km.`
        : "Aucunes toilettes connues.");
    }
  } catch (e) {
    toast(e && e.code === 1
      ? "Géolocalisation refusée : autorisez-la dans votre navigateur."
      : "Position introuvable pour le moment.");
  } finally {
    bouton.disabled = false;
  }
}

function initToilettesProches() {
  document.getElementById("btn-wc").addEventListener("click", toilettesAutourDeMoi);
}

/* ------------------------------------------------------------------ */
/* Installation sur l'écran d'accueil + numéro de version               */
/* ------------------------------------------------------------------ */

function initInstallation() {
  const bouton = document.getElementById("btn-install");
  // Déjà lancée depuis l'écran d'accueil : rien à installer
  if (matchMedia("(display-mode: standalone)").matches || navigator.standalone === true) return;
  bouton.hidden = false;

  window.addEventListener("appinstalled", () => {
    bouton.hidden = true;
    toast("Application installée : retrouvez-la sur votre écran d'accueil !");
  });

  const dlg = document.getElementById("install-dialog");
  dlg.querySelector(".install-ok").addEventListener("click", () => dlg.close());

  bouton.addEventListener("click", async () => {
    // L'invite du navigateur peut arriver quelques secondes après le
    // chargement : on lui laisse jusqu'à 2 s avant le mode d'emploi.
    for (let i = 0; i < 20 && !evenementInstallation; i++) {
      await new Promise((r) => setTimeout(r, 100));
    }
    // Android / Chrome : la vraie invite d'installation du navigateur.
    // L'événement ne sert qu'UNE fois (re-prompter la même instance lève une
    // erreur) : on le consomme ; le navigateur en émettra un nouveau au besoin.
    if (evenementInstallation) {
      const invite = evenementInstallation;
      evenementInstallation = null;
      invite.prompt();
      await invite.userChoice;
      return;
    }
    // Pas d'invite : sur Android c'est presque toujours que l'application
    // est DÉJÀ installée (Chrome ne la repropose pas) — on le vérifie quand
    // le navigateur sait répondre (nécessite related_applications du manifest).
    let dejaInstallee = false;
    try {
      dejaInstallee = ((await navigator.getInstalledRelatedApps?.()) || []).length > 0;
    } catch { /* détection indisponible : message générique */ }
    dlg.querySelector(".install-steps").innerHTML = SUR_IOS
      ? `<p>Sur iPhone / iPad, l'installation passe par <strong>Safari</strong> :</p>
         <ol>
           <li>Ouvrez cette page dans <strong>Safari</strong> (si ce n'est pas déjà le cas).</li>
           <li>Touchez le bouton <strong>Partager</strong> — le carré avec une flèche vers le haut, en bas de l'écran.</li>
           <li>Choisissez <strong>« Sur l'écran d'accueil »</strong> (ou « Ajouter à l'écran d'accueil »).</li>
           <li>Touchez <strong>Ajouter</strong> : l'icône apparaît comme une vraie application.</li>
         </ol>`
      : dejaInstallee
      ? `<p><strong>✅ L'application est déjà installée sur cet appareil</strong> :
         retrouvez son icône sur votre écran d'accueil.</p>
         <p>Le navigateur ne propose pas de la réinstaller.</p>`
      : SUR_ANDROID
      ? `<p>Le navigateur ne propose pas l'installation automatique pour le moment.
         C'est presque toujours que l'application est <strong>déjà installée</strong> :
         vérifiez votre écran d'accueil.</p>
         <p>Sinon : menu <strong>⋮</strong> du navigateur →
         <strong>« Ajouter à l'écran d'accueil »</strong> → <strong>Installer</strong>.</p>`
      : `<p>Ouvrez le <strong>menu de votre navigateur</strong> (⋮ ou ≡) puis choisissez
         <strong>« Installer l'application »</strong> ou <strong>« Ajouter à l'écran d'accueil »</strong>.</p>`;
    dlg.showModal();
  });
}

/* ------------------------------------------------------------------ */
/* Menu ⚙️ Réglages + vérification de mise à jour                      */
/* ------------------------------------------------------------------ */

function initReglages() {
  const dlg = document.getElementById("settings-dialog");
  document.getElementById("btn-settings").addEventListener("click", () => dlg.showModal());
  dlg.querySelector(".settings-close").addEventListener("click", () => dlg.close());
  // Chaque action referme le menu (l'import ouvre un sélecteur de fichier,
  // l'installation son propre dialogue, la vérification un toast…)
  for (const bouton of dlg.querySelectorAll(".settings-list .btn")) {
    bouton.addEventListener("click", () => dlg.close());
  }
  document.getElementById("btn-update").addEventListener("click", verifierMiseAJour);
  document.getElementById("btn-export-pdf").addEventListener("click", exporterCarnetPDF);
}

/** Force une vérification de mise à jour : le navigateur va rechercher
 *  sw.js sur le réseau (sans cache) ; si la VERSION a changé, le nouveau
 *  service worker s'installe et la page se recharge toute seule
 *  (controllerchange, en place depuis la v9). */
async function verifierMiseAJour() {
  toast("Vérification de la mise à jour…");
  try {
    const reg = await navigator.serviceWorker.getRegistration();
    if (!reg) {
      toast("Vérification impossible dans ce contexte.");
      return;
    }
    await reg.update();
    if (reg.installing || reg.waiting) {
      toast("Nouvelle version trouvée ! Installation… la page va se recharger toute seule.");
    } else {
      toast(`Vous avez déjà la dernière version (${versionLocale}).`);
    }
  } catch {
    toast("Vérification impossible : êtes-vous connecté à Internet ?");
  }
}

/** Version qui tourne actuellement (affichée en pied de panneau et utilisée
 *  par « Vérifier la mise à jour »). */
let versionLocale = "?";

/** Affiche le numéro de version, lu dans sw.js : une seule source à
 *  incrémenter, et chacun peut vérifier quelle version tourne chez lui. */
async function afficherVersion() {
  try {
    const texte = await (await fetch("sw.js")).text();
    const version = texte.match(/VERSION = "(v[^"]+)"/)?.[1];
    if (version) {
      versionLocale = version;
      document.getElementById("app-version").textContent = `version ${version}`;
    }
  } catch {
    /* hors-ligne avant toute mise en cache : pas de numéro, tant pis */
  }
}

/* ------------------------------------------------------------------ */
/* Géolocalisation                                                      */
/* ------------------------------------------------------------------ */

function initGeolocalisation() {
  const bouton = document.getElementById("btn-locate");
  bouton.addEventListener("click", async () => {
    bouton.disabled = true;
    try {
      const etat = await toggleLocate();
      bouton.classList.toggle("active", etat === "on");
    } catch (e) {
      toast(
        e.code === 1
          ? "Géolocalisation refusée : autorisez-la dans votre navigateur."
          : "Position introuvable pour le moment."
      );
    } finally {
      bouton.disabled = false;
    }
  });
}

/* ------------------------------------------------------------------ */
/* Démarrage                                                            */
/* ------------------------------------------------------------------ */

function restaurerPrefs(prefs) {
  if (Array.isArray(prefs.activeThemes)) {
    state.activeThemes = new Set(prefs.activeThemes.filter((t) => getTheme(t).id === t));
  } else {
    // ★ Toute première connexion : seules les cités de caractère sont affichées
    state.activeThemes = new Set(["cite-caractere"]);
  }
  state.statusFilters = new Set(
    (Array.isArray(prefs.statusFilters) ? prefs.statusFilters : []).filter((s) =>
      ["a-faire", "fait", "favori"].includes(s)
    )
  );
  for (const [theme, filtres] of Object.entries(prefs.filterSelections || {})) {
    state.filterSelections[theme] = {};
    for (const [cle, valeurs] of Object.entries(filtres)) {
      state.filterSelections[theme][cle] = new Set(Array.isArray(valeurs) ? valeurs : []);
    }
  }
  state.filtersCollapsed = prefs.filtersCollapsed === true;
  state.tracesVisible = prefs.tracesVisible !== false;
  state.grVisible = prefs.grVisible === true;
}

async function demarrer() {
  // Catégories personnalisées et personnalisations AVANT tout rendu
  registerCustomThemes(await storage.getCustomThemes());
  setThemeOverrides(await storage.getThemeOverrides());

  const prefs = await storage.getPrefs();
  const premiereVisite = prefs.activeThemes === undefined && prefs.tutoVu !== true;
  state.statuses = await storage.getStatuses();
  await chargerPoints();
  restaurerPrefs(prefs);

  initMap(prefs, {
    onPointClick: ouvrirFiche,
    onViewChange: (vue) => storage.savePrefs(vue),
  });

  initSidebar({
    onToggleTheme: async (id, coche) => {
      // Toilettes : ~66 000 points → avertissement avec trois choix
      if (id === "toilettes" && coche) {
        const choix = await demanderModeToilettes();
        if (choix === "retour") {
          rafraichir(); // re-décoche la case (l'état n'a pas changé)
          return;
        }
        if (choix === "proximite") {
          rafraichir();
          await toilettesAutourDeMoi();
          return;
        }
        // « Valider » : affichage complet, comme une catégorie normale
      }
      coche ? state.activeThemes.add(id) : state.activeThemes.delete(id);
      if (coche) {
        state.statusFilters.clear(); // exclusif avec le mode suivi
        if (id === "escalade") bandeauEscaladeFerme = false; // le bandeau revient
        if (id === "toilettes" && !(await chargerToilettes())) {
          state.activeThemes.delete(id);
        }
        if (getThemeFilters(id).length) state.filtersCollapsed = false;
      }
      rafraichir();
    },
    onToggleStatus: (statut, coche) => {
      coche ? state.statusFilters.add(statut) : state.statusFilters.delete(statut);
      // Mode suivi : n'afficher QUE les points suivis → décoche les catégories
      if (coche) state.activeThemes.clear();
      rafraichir();
    },
    onToggleGr: (on) => {
      state.grVisible = on;
      setGrVisible(on);
      rafraichir();
    },
    onToggleTraces: (on) => {
      state.tracesVisible = on;
      setAllTracesVisible(on);
      rafraichir();
    },
    onThemesChanged: () => {
      rafraichir();
      const idOuvert = getOpenPointId();
      if (idOuvert) refreshDetailsIfOpen(idOuvert, state.statuses[idOuvert]);
    },
    // Flèche ➤ : zoome sur les points ajoutés dans cette catégorie
    // (clics successifs = point suivant)
    onLocateUserPoint: (themeId) => {
      const miens = state.allPoints.filter(
        (f) => state.userPointIds.has(f.properties.id) && getTheme(f.properties.theme).id === themeId
      );
      if (!miens.length) return;
      cycleUserPoint[themeId] = ((cycleUserPoint[themeId] ?? -1) + 1) % miens.length;
      if (window.innerWidth < 900) closeSidebar();
      allerAuPoint(miens[cycleUserPoint[themeId]]);
    },
    onDeleteTheme: async (id) => {
      const theme = getTheme(id);
      const pointsLies = (await storage.getUserPoints().catch(() => [])).filter(
        (f) => f.properties.theme === id
      );
      const message =
        `Supprimer la catégorie « ${theme.label} »` +
        (pointsLies.length ? ` et ses ${pointsLies.length} point(s)` : "") +
        " ? Cette action est définitive.";
      if (!(await confirmer(message))) return;
      for (const f of pointsLies) await storage.deleteUserPoint(f.properties.id);
      const customs = (await storage.getCustomThemes()).filter((t) => t.id !== id);
      await storage.saveCustomThemes(customs);
      registerCustomThemes(customs);
      const overrides = await storage.getThemeOverrides();
      delete overrides[id];
      await storage.saveThemeOverrides(overrides);
      setThemeOverrides(overrides);
      state.activeThemes.delete(id);
      await chargerPoints();
      rafraichir();
      toast(`Catégorie « ${theme.label} » supprimée.`);
    },
  });

  initFilters({
    onFilterToggle: (themeId, cle, valeur) => {
      const filtres = (state.filterSelections[themeId] ??= {});
      const sel = (filtres[cle] ??= new Set());
      sel.has(valeur) ? sel.delete(valeur) : sel.add(valeur);
      rafraichir();
    },
    onFilterReset: (themeId, cle) => {
      state.filterSelections[themeId]?.[cle]?.clear();
      rafraichir();
    },
    onCollapse: (replie) => {
      state.filtersCollapsed = replie;
      rafraichir();
    },
  });

  initDetails({
    onStatusChange: changerStatut,
    onClose: clearHighlight,
    isUserPoint: (id) => state.userPointIds.has(id),
    onDeletePoint: supprimerPoint,
  });

  initImportExport({
    getExistingIds: () => state.allPoints.map((f) => f.properties.id),
    getExportData: async () => ({
      points: await storage.getUserPoints().catch(() => []),
      statuses: state.statuses,
      journal: await storage.getAllJournals().catch(() => ({})),
      customThemes: await storage.getCustomThemes().catch(() => []),
      sorties: await storage.getSorties().catch(() => []),
    }),
    onImportedPoints: apresImportPoints,
    onImportedTraces: () => {
      if (!state.tracesVisible) {
        state.tracesVisible = true;
        setAllTracesVisible(true);
      }
      refreshTraces();
      rafraichir();
    },
  });

  await initGpx({ onTracksChanged: refreshTraces });
  setAllTracesVisible(state.tracesVisible);
  if (state.grVisible) setGrVisible(true);

  initAddPoint({
    onPointAdded: async (feature) => {
      await apresImportPoints([feature]);
      allerAuPoint(feature);
    },
  });

  initRecherche();
  initGeolocalisation();
  initToilettesProches();
  initIdeas();
  initInstallation();
  initReglages();
  afficherVersion();
  initCarnet({
    getPoints: () => state.allPoints,
    getStatuses: () => state.statuses,
    onVoirSurCarte: (feature) => allerAuPoint(feature),
  });

  // Fermeture du bandeau escalade : clic N'IMPORTE OÙ sur le bandeau
  // (pas seulement la croix) ou touche Échap. Volontairement non persisté :
  // il revient à la prochaine activation de la catégorie.
  const fermerBandeau = () => {
    bandeauEscaladeFerme = true;
    document.getElementById("banner-escalade").hidden = true;
  };
  document.getElementById("banner-escalade").addEventListener("click", fermerBandeau);
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && !document.getElementById("banner-escalade").hidden) {
      fermerBandeau();
    }
  });

  // Étape « filtres » du tuto : elle montre TOUJOURS les filtres des via
  // ferrata (jamais ceux des toilettes ni d'une autre catégorie cochée) —
  // les catégories de l'utilisateur sont restaurées à la fin de la visite.
  let themesAvantTuto = null;
  initTuto({
    onTermine: () => {
      storage.savePrefs({ tutoVu: true });
      if (themesAvantTuto) {
        state.activeThemes = themesAvantTuto;
        themesAvantTuto = null;
        rafraichir();
      }
    },
    ouvrirFiltres: () => {
      if (!themesAvantTuto) themesAvantTuto = new Set(state.activeThemes);
      state.activeThemes = new Set(["via-ferrata"]);
      state.filtersCollapsed = false;
      rafraichir();
    },
  });

  rafraichir();

  // Toilettes déjà cochées lors d'une session précédente : leur fichier
  // (chargé à la demande) doit l'être aussi au démarrage — en arrière-plan,
  // pour ne pas retarder le premier affichage.
  if (state.activeThemes.has("toilettes")) {
    chargerToilettes().then((ok) => ok && rafraichir());
  }

  // Tuto lancé automatiquement à la toute première connexion (skippable)
  if (premiereVisite) setTimeout(startTuto, 600);

  // Hors-ligne : service worker (chemin relatif pour GitHub Pages)
  if ("serviceWorker" in navigator) {
    // Après une mise à jour (nouvelle VERSION dans sw.js), la page recharge
    // dès que le nouveau SW prend la main : les visiteurs voient la dernière
    // version au premier chargement, sans second F5 manuel.
    let avaitControleur = !!navigator.serviceWorker.controller;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (avaitControleur) location.reload();
      avaitControleur = true;
    });
    navigator.serviceWorker.register("sw.js").catch((e) => {
      console.warn("Service worker non enregistré :", e);
    });
  }
}

function getThemeFilters(id) {
  return THEMES.find((t) => t.id === id)?.filters || [];
}

demarrer();
