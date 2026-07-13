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
  montrerTraceRando,
  montrerTraceCanyon,
  cacherTraceRando,
  getTraceRando,
  getTraceCanyon,
  selectionnerGr,
  deselectionnerGr,
  getFonds,
  setFond,
} from "./map.js";
import { initFilters, renderFilters } from "./filters.js";
import {
  initDetails,
  openDetails,
  openDetailsGr,
  closeDetails,
  refreshDetailsIfOpen,
  getOpenPointId,
  getOpenGrId,
} from "./details.js";
import { initSidebar, renderSidebar, refreshTraces, closeSidebar } from "./sidebar.js";
import { initImportExport, toast, confirmer } from "./import-export.js";
import { initGpx, setAllTracesVisible } from "./gpx.js";
import { initAddPoint } from "./addpoint.js";
import { initTuto, startTuto } from "./tuto.js";
import { initIdeas } from "./ideas.js";
import { initOracle } from "./oracle.js";
import { initSync, finaliserPopupAuth } from "./sync.js";
import { initCarnet, exporterCarnetPDF, ouvrirCarnetPourPoint } from "./carnet.js";
import { initPartage } from "./partage.js";
import { SUR_ANDROID, SUR_IOS } from "./config/platform.js";
import { esc } from "./util.js";
import { passeFiltre } from "./filtrage.js";

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

/** Points d'eau (data/eau.geojson, ~49 500 points) : même modèle que les
 *  toilettes — fichier séparé non pré-caché, chargé à la première activation. */
let pointsEau = [];

/** Grottes/cavités (data/grottes.geojson, ~50 000 entrées Grottocenter +
 *  grottes Wikipédia) : même modèle de couche lourde à la demande. */
let pointsGrottes = [];

/** Indices du cycle « flèche ➤ » (clics successifs → point suivant). */
const cycleUserPoint = {};

/** Bandeau « données escalade partielles » : la croix le ferme, mais il
 *  réapparaît à chaque nouvelle activation de la catégorie Escalade. */

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
  for (const f of [...defauts, ...pointsToilettes, ...pointsEau, ...pointsGrottes, ...importes]) parId.set(f.properties.id, f);
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

/** Charge les points d'eau si nécessaire ; renvoie false en cas d'échec. */
async function chargerEau() {
  if (pointsEau.length) return true;
  toast("Chargement des points d'eau…");
  try {
    const reponse = await fetch("data/eau.geojson");
    pointsEau = (await reponse.json()).features || [];
    await chargerPoints();
    return true;
  } catch (e) {
    console.error("Impossible de charger data/eau.geojson :", e);
    toast("Points d'eau indisponibles pour le moment (hors connexion ?).");
    return false;
  }
}

/** Charge les grottes si nécessaire ; renvoie false en cas d'échec. */
async function chargerGrottes() {
  if (pointsGrottes.length) return true;
  toast("Chargement des grottes…");
  try {
    const reponse = await fetch("data/grottes.geojson");
    pointsGrottes = (await reponse.json()).features || [];
    await chargerPoints();
    return true;
  } catch (e) {
    console.error("Impossible de charger data/grottes.geojson :", e);
    toast("Grottes indisponibles pour le moment (hors connexion ?).");
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
  // Couches lourdes pas encore chargées : « … » plutôt qu'un 0 trompeur
  if (!pointsToilettes.length) compteurs.set("toilettes", "…");
  if (!pointsEau.length) compteurs.set("eau", "…");
  if (!pointsGrottes.length) compteurs.set("grotte", "…");
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

/* Écriture des préférences DÉBOUNCÉE : rafraichir() est appelé à chaque
 * interaction (cocher une catégorie, un filtre…). On regroupe les écritures
 * localStorage sur 400 ms, et on force l'enregistrement quand l'onglet passe
 * en arrière-plan ou se ferme, pour ne jamais rien perdre. */
let prefsTimer = null;
let prefsEnAttente = null;
function planifierPrefs(prefs) {
  prefsEnAttente = prefs;
  clearTimeout(prefsTimer);
  prefsTimer = setTimeout(enregistrerPrefs, 400);
}
function enregistrerPrefs() {
  clearTimeout(prefsTimer);
  prefsTimer = null;
  if (prefsEnAttente) {
    storage.savePrefs(prefsEnAttente);
    prefsEnAttente = null;
  }
}
document.addEventListener("visibilitychange", () => {
  if (document.hidden) enregistrerPrefs();
});
window.addEventListener("pagehide", enregistrerPrefs);

/** Rendu du panneau gauche (catégories + suivi). Regroupé ici car appelé
 *  à l'identique par rafraichir() et par changerStatut(). */
function rendreSidebar() {
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

function rafraichir() {
  rendreSidebar();
  renderFilters({
    activeThemes: state.activeThemes,
    filterSelections: state.filterSelections,
    collapsed: state.filtersCollapsed,
    statusActif: state.statusFilters.size > 0,
  });
  setPoints(pointsVisibles(), state.statuses);
  // Catégorie Randonnée/Canyon décochée → tracé épinglé, pastille et fiche disparaissent
  const catEpinglee =
    itineraireEpingle?.type === "rando" ? "randonnee"
    : itineraireEpingle?.type === "canyon" ? "canyon"
    : null;
  if (catEpinglee && !state.activeThemes.has(catEpinglee)) {
    const idEpinglee = itineraireEpingle.id;
    itineraireEpingle = null;
    cacherTraceRando();
    if (getOpenPointId() === idEpinglee) closeDetails();
    else majPastilleItineraire();
  }
  planifierPrefs({
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

// Itinéraire « épinglé » : une randonnée (point) OU un sentier GR (ligne).
// Son tracé reste sur la carte même fiche fermée ; la pastille #rando-chip la
// rouvre. UN SEUL épinglé à la fois — sélectionner l'autre remplace le précédent.
let itineraireEpingle = null; // { type: "rando"|"gr", id, name, icon, feature }

function ouvrirFiche(feature) {
  highlightPoint(feature.properties.id); // épingle agrandie + halo
  openDetails(feature, state.statuses[feature.properties.id]);
  // Randonnée et Canyon : leur CHEMIN se dessine sur la carte et y reste épinglé
  // (tracés dans data/randos.geojson / data/canyons-traces.geojson). Ouvrir un
  // point d'une AUTRE catégorie ne retire pas l'itinéraire épinglé (choix
  // utilisateur) ; seul un autre itinéraire le fait. Tous les canyons n'ont pas
  // de tracé (~27 recouverts par OSM) : sans tracé, rien n'est épinglé.
  const themeId = getTheme(feature.properties.theme).id;
  if (themeId === "randonnee" || themeId === "canyon") {
    deselectionnerGr(); // un GR était peut-être épinglé : il cède la place
    itineraireEpingle = {
      type: themeId === "canyon" ? "canyon" : "rando",
      id: feature.properties.id,
      name: feature.properties.name,
      icon: getTheme(feature.properties.theme).icon,
      feature,
    };
    majPastilleItineraire();
    const montrer = themeId === "canyon" ? montrerTraceCanyon : montrerTraceRando;
    montrer(feature.properties.id).then((ok) => {
      if (!ok && itineraireEpingle?.id === feature.properties.id) {
        itineraireEpingle = null; // pas de tracé connu : rien à épingler
        majPastilleItineraire();
      }
    });
  }
}

/** Ouvre la fiche d'un sentier GR (comme une randonnée : tracé épinglé + pastille). */
function ouvrirFicheGr(grFeature) {
  const grId = grFeature.properties.grId;
  cacherTraceRando(); // une rando était peut-être épinglée : elle cède la place
  clearHighlight();
  selectionnerGr(grId); // surligne le GR en orange, y compris fiche fermée
  itineraireEpingle = {
    type: "gr",
    id: grId,
    name: grFeature.properties.name || "GR",
    icon: "🥾",
    feature: grFeature,
  };
  openDetailsGr(grFeature);
  majPastilleItineraire();
}

/**
 * Pastille de l'itinéraire épinglé (rando ou GR) : visible seulement quand un
 * tracé est affiché ET que sa fiche est fermée. Cliquer la rouvre.
 */
function majPastilleItineraire() {
  const pastille = document.getElementById("rando-chip");
  const ficheOuverte =
    itineraireEpingle &&
    (itineraireEpingle.type === "gr"
      ? getOpenGrId() === itineraireEpingle.id
      : getOpenPointId() === itineraireEpingle.id);
  if (!itineraireEpingle || ficheOuverte) {
    pastille.hidden = true;
    return;
  }
  pastille.querySelector(".rando-chip-icone").textContent = itineraireEpingle.icon;
  pastille.querySelector(".rando-chip-nom").textContent = itineraireEpingle.name;
  pastille.hidden = false;
}

/** Nom de fichier sûr à partir d'un nom de lieu (accents et espaces retirés). */
function nomFichier(nom) {
  return (
    normaliser(nom)
      .replace(/[^a-z0-9]+/g, "-")
      .replace(/^-+|-+$/g, "") || "trace"
  );
}

/**
 * Écrit un GPX (une ou plusieurs `trkseg`) et déclenche son téléchargement.
 * `segments` = tableau de segments, chaque segment = tableau de [lon, lat].
 * `depart` optionnel = [lat, lon] posé comme waypoint (départ de la rando).
 */
function telechargerGpx(nom, segments, depart) {
  const trksegs = segments
    .map(
      (seg) =>
        `    <trkseg>\n${seg
          .map(([lon, lat]) => `      <trkpt lat="${lat}" lon="${lon}"/>`)
          .join("\n")}\n    </trkseg>`
    )
    .join("\n");
  const gpx = `<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" creator="Carte Outdoor" xmlns="http://www.topografix.com/GPX/1/1">
  <metadata><name>${esc(nom)}</name></metadata>
${depart ? `  <wpt lat="${depart[0]}" lon="${depart[1]}"><name>${esc(nom)}</name></wpt>\n` : ""}  <trk>
    <name>${esc(nom)}</name>
${trksegs}
  </trk>
</gpx>
`;
  const url = URL.createObjectURL(new Blob([gpx], { type: "application/gpx+xml" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = `${nomFichier(nom)}.gpx`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
  toast("GPX téléchargé — importable dans Komoot, AllTrails, une montre GPS…");
}

/** GPX d'une randonnée (passerelle vers Komoot, AllTrails, montres GPS). */
async function telechargerGpxRando(feature) {
  const morceaux = await getTraceRando(feature.properties.id);
  if (!morceaux.length) {
    toast("Tracé indisponible pour cette randonnée.");
    return;
  }
  const [lonPt, latPt] = feature.geometry.coordinates;
  telechargerGpx(feature.properties.name, morceaux.map((m) => m.geometry.coordinates), [latPt, lonPt]);
}

/** GPX d'un canyon (tracé MultiLineString dans data/canyons-traces.geojson). */
async function telechargerGpxCanyon(feature) {
  const morceaux = await getTraceCanyon(feature.properties.id);
  if (!morceaux.length) {
    toast("Tracé indisponible pour ce canyon.");
    return;
  }
  // MultiLineString : geometry.coordinates est déjà un tableau de segments.
  const segments = morceaux.flatMap((m) =>
    m.geometry.type === "MultiLineString" ? m.geometry.coordinates : [m.geometry.coordinates]
  );
  const [lonPt, latPt] = feature.geometry.coordinates;
  telechargerGpx(feature.properties.name, segments, [latPt, lonPt]);
}

/** Bouton 📥 GPX d'une fiche point : aiguille vers la rando ou le canyon selon le thème. */
function telechargerGpxItineraire(feature) {
  if (getTheme(feature.properties.theme).id === "canyon") telechargerGpxCanyon(feature);
  else telechargerGpxRando(feature);
}

/** GPX d'un sentier GR (sa géométrie LineString est directement dans la feature). */
function telechargerGpxGr(grFeature) {
  const coords = grFeature.geometry?.coordinates || [];
  if (!coords.length) {
    toast("Tracé indisponible pour ce GR.");
    return;
  }
  telechargerGpx(grFeature.properties?.name || "GR", [coords], null);
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
  rendreSidebar();
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
  if (itineraireEpingle?.type === "rando" && itineraireEpingle.id === feature.properties.id) {
    itineraireEpingle = null; // le point supprimé était la rando épinglée
    cacherTraceRando();
  }
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
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase();
}

function initRecherche() {
  const input = document.getElementById("search-input");
  const resultats = document.getElementById("search-results");
  let minuterieVilles = null;
  let requeteVilles = 0; // anti-course : seule la DERNIÈRE réponse s'affiche

  input.addEventListener("input", () => {
    const brut = input.value.trim();
    resultats.textContent = "";
    clearTimeout(minuterieVilles);

    // Un code postal (5 chiffres) : on propose d'aller sur la carte à cet
    // endroit plutôt que de chercher un point nommé « 05100 ».
    if (/^\d{5}$/.test(brut)) {
      const item = document.createElement("button");
      item.type = "button";
      item.className = "search-result";
      item.innerHTML =
        '<span class="group-icon" style="--pin-color:#2e7d52;--pin-text:#fff" aria-hidden="true">📍</span>' +
        '<span class="search-result-text"><strong></strong><small>Aller sur la carte</small></span>';
      item.querySelector("strong").textContent = `Code postal ${brut}`;
      item.addEventListener("click", () => allerAuCodePostal(brut));
      resultats.appendChild(item);
      return;
    }

    const requete = normaliser(brut);
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
        `<span class="group-icon" style="--pin-color:${esc(theme.color)};--pin-text:${esc(theme.textColor)}" aria-hidden="true">${esc(theme.icon)}</span>` +
        `<span class="search-result-text"><strong></strong><small>${esc(theme.label)}</small></span>`;
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

    // En complément des points : les VILLES qui portent ce nom (≥ 3 lettres),
    // pour se déplacer sur la carte. Débouncé (une frappe = pas un appel),
    // et gardé contre les réponses réseau arrivées dans le désordre.
    if (brut.length >= 3) {
      const jeton = ++requeteVilles;
      minuterieVilles = setTimeout(() => proposerVilles(brut, jeton, resultats), 250);
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

  /** Suggestions de VILLES (geo.api.gouv.fr), ajoutées sous les points. */
  async function proposerVilles(nom, jeton, conteneur) {
    let communes = [];
    try {
      const res = await fetch(
        `https://geo.api.gouv.fr/communes?nom=${encodeURIComponent(nom)}` +
          "&fields=nom,centre,departement&boost=population&limit=3"
      );
      communes = res.ok ? await res.json() : [];
    } catch {
      return; // hors connexion : la recherche de points reste utilisable
    }
    // Une frappe plus récente a relancé une recherche : réponse périmée
    if (jeton !== requeteVilles) return;
    for (const c of communes) {
      const coords = c.centre?.coordinates;
      if (!coords) continue;
      const item = document.createElement("button");
      item.type = "button";
      item.className = "search-result search-ville";
      item.innerHTML =
        '<span class="group-icon" style="--pin-color:#2e7d52;--pin-text:#fff" aria-hidden="true">📍</span>' +
        '<span class="search-result-text"><strong></strong><small>Ville — aller sur la carte</small></span>';
      item.querySelector("strong").textContent =
        c.nom + (c.departement ? ` (${c.departement.code})` : "");
      item.addEventListener("click", () => {
        input.value = "";
        conteneur.textContent = "";
        if (window.innerWidth < 900) closeSidebar();
        montrerRayon(coords[1], coords[0], 3000, 12);
        toast(c.nom + (c.departement ? ` — ${c.departement.nom}` : ""));
      });
      conteneur.appendChild(item);
    }
  }
}

/** Recentre la carte sur un code postal (commune résolue via geo.api.gouv.fr). */
async function allerAuCodePostal(cp) {
  const input = document.getElementById("search-input");
  const resultats = document.getElementById("search-results");
  try {
    const res = await fetch(
      `https://geo.api.gouv.fr/communes?codePostal=${encodeURIComponent(cp)}&fields=nom,centre&format=json`
    );
    const arr = res.ok ? await res.json() : null;
    const coords = Array.isArray(arr) && arr[0]?.centre?.coordinates;
    if (!coords) {
      toast(`Aucune commune trouvée pour le code postal ${cp}.`);
      return;
    }
    input.value = "";
    resultats.textContent = "";
    if (window.innerWidth < 900) closeSidebar();
    // Vue d'ensemble de la commune (zoom 12) + cercle indicatif de 3 km.
    montrerRayon(coords[1], coords[0], 3000, 12);
    toast(`Code postal ${cp} — ${arr[0].nom}`);
  } catch {
    toast("Impossible de localiser ce code postal (connexion ?).");
  }
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

/** Couches volumineuses chargées à la demande : même UX (avertissement à
 *  l'activation + mode « autour de moi » à 1 km). `points` est un getter car
 *  le tableau est réassigné au chargement. */
const COUCHES_LOURDES = {
  toilettes: {
    dialog: "wc-dialog", charger: chargerToilettes, points: () => pointsToilettes,
    pluriel: "toilettes", vide: "Aucunes toilettes à moins de 1 km",
    proche: "la plus proche", aucun: "Aucunes toilettes connues.",
  },
  eau: {
    dialog: "eau-dialog", charger: chargerEau, points: () => pointsEau,
    pluriel: "points d'eau", vide: "Aucun point d'eau à moins de 1 km",
    proche: "le plus proche", aucun: "Aucun point d'eau connu.",
  },
  grotte: {
    dialog: "grottes-dialog", charger: chargerGrottes, points: () => pointsGrottes,
    pluriel: "grottes", vide: "Aucune grotte à moins de 1 km",
    proche: "la plus proche", aucun: "Aucune grotte connue.",
  },
};

/** Dialogue d'avertissement à l'activation d'une couche lourde (toilettes, eau).
 *  @returns {Promise<"valider"|"retour"|"proximite">} */
function demanderModeCouche(dialogId) {
  const dlg = document.getElementById(dialogId);
  dlg.showModal();
  return new Promise((resolve) => {
    const repondre = (choix) => {
      if (dlg.open) dlg.close();
      resolve(choix);
    };
    dlg.querySelector(".mode-valider").onclick = () => repondre("valider");
    dlg.querySelector(".mode-retour").onclick = () => repondre("retour");
    dlg.querySelector(".mode-proximite").onclick = () => repondre("proximite");
    dlg.oncancel = () => resolve("retour"); // touche Échap
  });
}

/** Géolocalise puis affiche SEULE la couche `id` (toilettes/eau) autour de la
 *  position (cercle de 1 km). Utilisé par l'avertissement et par le bouton 🏃🚻. */
async function coucheAutourDeMoi(id) {
  const conf = COUCHES_LOURDES[id];
  try {
    toast("Recherche de votre position…");
    const [lat, lon] = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
        reject,
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
    if (!(await conf.charger())) return;
    // Le zoom se fait AVANT le rendu : les marqueurs se remplissent en priorité
    // autour de la position (tri par distance dans setPoints).
    montrerRayon(lat, lon, 1000);
    state.activeThemes = new Set([id]);
    state.statusFilters.clear();
    rafraichir();
    const distances = conf.points().map((f) =>
      distanceM(lat, lon, f.geometry.coordinates[1], f.geometry.coordinates[0])
    );
    const proches = distances.filter((d) => d <= 1000).length;
    if (proches) {
      toast(`${proches} ${conf.pluriel} à moins de 1 km.`);
    } else {
      const mini = Math.min(...distances);
      toast(Number.isFinite(mini)
        ? `${conf.vide} — ${conf.proche} est à ${(mini / 1000).toFixed(1)} km.`
        : conf.aucun);
    }
  } catch (e) {
    toast(e && e.code === 1
      ? "Géolocalisation refusée : autorisez-la dans votre navigateur."
      : "Position introuvable pour le moment.");
  }
}

/** Bouton flottant 🏃🚻 : toilettes autour de moi (désactive le bouton pendant l'opération). */
async function toilettesAutourDeMoi() {
  const bouton = document.getElementById("btn-wc");
  bouton.disabled = true;
  try {
    await coucheAutourDeMoi("toilettes");
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
  document.getElementById("btn-settings").addEventListener("click", () => {
    majStatutStockage();
    dlg.showModal();
  });
  dlg.querySelector(".settings-close").addEventListener("click", () => dlg.close());
  // Chaque action referme le menu (l'import ouvre un sélecteur de fichier,
  // l'installation son propre dialogue, la vérification un toast…)
  for (const bouton of dlg.querySelectorAll(".settings-list .btn")) {
    bouton.addEventListener("click", () => dlg.close());
  }
  document.getElementById("btn-update").addEventListener("click", verifierMiseAJour);
  document.getElementById("btn-export-pdf").addEventListener("click", exporterCarnetPDF);
}

/** Mode nuit de l'application : couleurs sombres + tuiles de carte
 *  assombries (voir styles.css). Préférence mémorisée. */
function initModeNuit(prefs) {
  const bouton = document.getElementById("btn-mode-nuit");
  let actif = prefs.modeNuit === true;
  const appliquer = () => {
    document.body.classList.toggle("mode-nuit", actif);
    bouton.textContent = actif ? "☀️ Mode jour" : "🌙 Mode nuit";
  };
  appliquer();
  bouton.addEventListener("click", () => {
    actif = !actif;
    appliquer();
    storage.savePrefs({ modeNuit: actif });
  });
}

/** Renseigne la ligne d'état du stockage dans ⚙️ Réglages : protection
 *  anti-effacement + date de dernière sauvegarde. */
async function majStatutStockage() {
  const el = document.getElementById("storage-status");
  let persistant = false;
  try {
    persistant = (await navigator.storage?.persisted?.()) === true;
  } catch {
    /* API absente */
  }
  const prefs = await storage.getPrefs();
  const dateSauv = prefs.dernierExport
    ? new Date(prefs.dernierExport).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })
    : "jamais";
  el.innerHTML =
    `${persistant ? "🔒 Données protégées contre l'effacement automatique." : "⚠️ Le navigateur pourrait effacer les données sous contrainte d'espace — pensez à sauvegarder."}` +
    `<br>Dernière sauvegarde : <strong>${dateSauv}</strong>.`;
}

/* ------------------------------------------------------------------ */
/* Protection des données : anti-éviction + rappel de sauvegarde        */
/* ------------------------------------------------------------------ */

/**
 * Les données de l'utilisateur (sorties, carnet, points, statuts) vivent
 * dans le navigateur de l'appareil. Deux protections :
 *  1. `navigator.storage.persist()` demande au navigateur de NE PAS les
 *     effacer automatiquement pour libérer de la place (éviction) ;
 *  2. un rappel invite à exporter une sauvegarde de temps en temps — seul
 *     rempart en cas de changement d'appareil ou de nettoyage manuel.
 * Depuis le correctif du service worker (v27), aucune manipulation de type
 * « vider les données du site » n'est plus nécessaire pour les mises à jour.
 */
async function initProtectionDonnees(prefs, premiereVisite) {
  // 1) Stockage persistant (souvent accordé d'office pour une PWA installée)
  try {
    if (navigator.storage?.persist && !(await navigator.storage.persisted())) {
      await navigator.storage.persist();
    }
  } catch {
    /* API indisponible : on continue sans */
  }

  // 2) Rappel de sauvegarde
  const dlg = document.getElementById("backup-dialog");
  dlg.querySelector(".backup-plus-tard").addEventListener("click", () => {
    dlg.close();
    storage.savePrefs({ dernierRappelSauvegarde: Date.now() });
  });
  dlg.querySelector(".backup-maintenant").addEventListener("click", () => {
    dlg.close();
    document.getElementById("btn-export").click(); // exporter() note la date
  });

  // Pas de rappel à la toute première visite (aucune donnée, et il y a le tuto)
  if (premiereVisite) return;
  const sorties = await storage.getSorties().catch(() => []);
  const aDesDonnees =
    state.userPointIds.size > 0 ||
    sorties.length > 0 ||
    Object.keys(state.statuses).length > 0;
  if (!aDesDonnees) return;

  const DELAI = 14 * 24 * 60 * 60 * 1000; // 14 jours
  const dernier = Math.max(prefs.dernierExport || 0, prefs.dernierRappelSauvegarde || 0);
  if (Date.now() - dernier < DELAI) return;

  document.getElementById("backup-message").textContent = prefs.dernierExport
    ? "Votre dernière sauvegarde commence à dater."
    : "Vous avez des données enregistrées, mais aucune sauvegarde n'a encore été faite.";
  // Léger différé : ne pas surgir en plein chargement de la carte
  setTimeout(() => {
    if (!dlg.open) dlg.showModal();
  }, 1800);
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

/** Choix du fond de carte : bouton 🗺️ du pied de panneau → dialogue à
 *  cases (remplace le sélecteur Leaflet qui encombrait la carte). */
function initFondsCarte() {
  const dlg = document.getElementById("layers-dialog");
  const liste = dlg.querySelector(".layers-list");
  document.getElementById("btn-layers").addEventListener("click", () => {
    const { noms, actif } = getFonds();
    liste.textContent = "";
    for (const nom of noms) {
      const label = document.createElement("label");
      label.className = "layers-choix";
      label.innerHTML =
        `<input type="radio" name="fond-carte" ${nom === actif ? "checked" : ""}>` +
        `<span>${esc(nom)}</span>`;
      label.querySelector("input").addEventListener("change", () => {
        setFond(nom);
        dlg.close();
      });
      liste.appendChild(label);
    }
    dlg.showModal();
  });
  dlg.querySelector(".layers-close").addEventListener("click", () => dlg.close());
}

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

  const carte = initMap(prefs, {
    onPointClick: ouvrirFiche,
    onGrClick: ouvrirFicheGr,
    onViewChange: (vue) => storage.savePrefs(vue),
  });
  // Toucher la carte replie le tiroir des catégories (sur mobile, il recouvre
  // la carte). Sur PC (≥ 900 px) le panneau est fixe : closeSidebar sans effet.
  // Les clics sur les épingles ne remontent pas jusqu'à la carte : ouvrir une
  // fiche depuis la liste ne referme donc rien d'involontaire.
  carte.on("click", () => closeSidebar());

  initSidebar({
    onToggleTheme: async (id, coche) => {
      // Couches lourdes (toilettes ~66k, eau ~49k) → avertissement avec trois
      // choix : Retour, « À moins de 1 km » (zoom sur la position), Valider.
      if (COUCHES_LOURDES[id] && coche) {
        const choix = await demanderModeCouche(COUCHES_LOURDES[id].dialog);
        if (choix === "retour") {
          rafraichir(); // re-décoche la case (l'état n'a pas changé)
          return;
        }
        if (choix === "proximite") {
          rafraichir();
          await coucheAutourDeMoi(id);
          return;
        }
        // « Valider » : affichage complet, comme une catégorie normale
      }
      coche ? state.activeThemes.add(id) : state.activeThemes.delete(id);
      if (coche) {
        state.statusFilters.clear(); // exclusif avec le mode suivi
        if (COUCHES_LOURDES[id] && !(await COUCHES_LOURDES[id].charger())) {
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
      // GR masqués → un GR épinglé (tracé/pastille/fiche) doit disparaître
      if (!on && itineraireEpingle?.type === "gr") {
        const idEpingle = itineraireEpingle.id;
        itineraireEpingle = null;
        deselectionnerGr();
        if (getOpenGrId() === idEpingle) closeDetails();
        else majPastilleItineraire();
      }
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
    onClose: () => {
      clearHighlight();
      majPastilleItineraire(); // le tracé épinglé RESTE : la pastille prend le relais
    },
    isUserPoint: (id) => state.userPointIds.has(id),
    onDeletePoint: supprimerPoint,
    onVoirCarnet: ouvrirCarnetPourPoint,
    onTelechargerGpx: telechargerGpxItineraire,
    onTelechargerGpxGr: telechargerGpxGr,
  });

  // Pastille de l'itinéraire épinglé (rando ou GR) : rouvre sa fiche telle quelle
  document.getElementById("rando-chip").addEventListener("click", () => {
    if (!itineraireEpingle) return;
    if (itineraireEpingle.type === "gr") ouvrirFicheGr(itineraireEpingle.feature);
    else ouvrirFiche(itineraireEpingle.feature);
  });

  initPartage();

  initImportExport({
    getExistingIds: () => state.allPoints.map((f) => f.properties.id),
    getExportData: async () => ({
      points: await storage.getUserPoints().catch(() => []),
      statuses: state.statuses,
      journal: await storage.getAllJournals().catch(() => ({})),
      customThemes: await storage.getCustomThemes().catch(() => []),
      sorties: await storage.getSorties().catch(() => []),
      carnetTheme: await storage.getCarnetTheme().catch(() => null),
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
  initFondsCarte();
  initToilettesProches();
  initIdeas();
  // L'Oracle : le mode « sans clé » puise dans les points déjà chargés, et un
  // point annoncé peut être ouvert directement sur la carte.
  initOracle({
    getPoints: () => state.allPoints,
    onVoirPoint: (id) => {
      const f = state.allPoints.find((p) => p.properties.id === id);
      if (f) allerAuPoint(f);
    },
  });
  // Synchronisation multi-appareils : après une fusion « légère » (thème/
  // statuts), on ré-applique l'état sans recharger. Une fusion qui apporte de
  // nouveaux points/sorties déclenche, elle, un rechargement (voir sync.js).
  initSync({
    onSynced: async () => {
      registerCustomThemes(await storage.getCustomThemes());
      setThemeOverrides(await storage.getThemeOverrides());
      state.statuses = await storage.getStatuses();
      await chargerPoints();
      rafraichir();
    },
  });
  initInstallation();
  initReglages();
  initModeNuit(prefs);
  initProtectionDonnees(prefs, premiereVisite);
  afficherVersion();
  initCarnet({
    getPoints: () => state.allPoints,
    getStatuses: () => state.statuses,
    onVoirSurCarte: (feature) => allerAuPoint(feature),
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
  if (state.activeThemes.has("eau")) {
    chargerEau().then((ok) => ok && rafraichir());
  }
  if (state.activeThemes.has("grotte")) {
    chargerGrottes().then((ok) => ok && rafraichir());
  }

  // Tuto lancé automatiquement à la toute première connexion (skippable)
  if (premiereVisite) setTimeout(startTuto, 600);

  // Hors-ligne + MISE À JOUR AUTOMATIQUE (aucune action de l'utilisateur)
  if ("serviceWorker" in navigator) {
    // Quand le nouveau service worker prend la main (nouvelle VERSION de
    // sw.js), la page se recharge d'elle-même → les visiteurs voient la
    // dernière version, y compris le nouveau design du carnet, sans rien
    // faire. Le pré-cache force le réseau (cache:"reload", v27) : les
    // fichiers au nom inchangé mais au contenu modifié (img/carnet-*.jpg)
    // sont donc bien rafraîchis.
    let avaitControleur = !!navigator.serviceWorker.controller;
    let rechargeEnCours = false;
    navigator.serviceWorker.addEventListener("controllerchange", () => {
      if (avaitControleur && !rechargeEnCours) {
        rechargeEnCours = true; // garde-fou anti double-rechargement
        location.reload();
      }
      avaitControleur = true;
    });

    navigator.serviceWorker
      .register("sw.js")
      .then((reg) => {
        // Par défaut le navigateur ne cherche une nouvelle version qu'au
        // (re)chargement de la page. On vérifie AUSSI à chaque retour de
        // l'application au premier plan et une fois par heure : une appli
        // installée qui reste ouverte se met alors à jour toute seule.
        const verifier = () => reg.update().catch(() => {});
        document.addEventListener("visibilitychange", () => {
          if (!document.hidden) verifier();
        });
        setInterval(verifier, 60 * 60 * 1000);
      })
      .catch((e) => console.warn("Service worker non enregistré :", e));
  }
}

function getThemeFilters(id) {
  return THEMES.find((t) => t.id === id)?.filters || [];
}

// Cette page est-elle le POPUP de connexion (ouvert par la synchronisation) ?
// Le nom de fenêtre « carte-oauth-popup » persiste à travers les redirections
// OAuth. Si oui, on enregistre la session puis on ferme — SANS démarrer toute
// l'application (la fenêtre principale est prévenue via l'événement `storage`).
if (window.name === "carte-oauth-popup" && /[#&](access_token|error)=/.test(location.hash)) {
  finaliserPopupAuth(location.hash);
} else {
  demarrer();
}
