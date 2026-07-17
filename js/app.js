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
  isCustomTheme,
} from "./config/themes.js";
import { PAYS, paysChoisi, paysActuel, definirPays } from "./config/pays.js";
import { initCommunaute, ouvrirCommunaute } from "./communaute.js";
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
  getMap,
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
import { initFrequentation, statsFrequentation } from "./frequentation.js";
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

/** Couches lourdes (fichiers séparés NON pré-cachés, chargés à la première
 *  activation) : points par catégorie. Le FICHIER dépend du pays courant —
 *  `paysActuel().couchesLourdes` (js/config/pays.js) mappe id → fichier
 *  (v67 : toilettes/eau existent pour TOUS les pays ; grottes/musées = France,
 *  ces catégories restent ordinaires ailleurs). */
const pointsCouches = { toilettes: [], eau: [], grotte: [], culture: [] };

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
  const fichier = paysActuel().fichierPoints;
  try {
    const reponse = await fetch(fichier);
    defauts = (await reponse.json()).features || [];
  } catch (e) {
    console.error(`Impossible de charger ${fichier} :`, e);
  }
  const importes = await storage.getUserPoints().catch(() => []);
  state.userPointIds = new Set(importes.map((f) => f.properties.id));
  const parId = new Map();
  for (const f of [...defauts, ...Object.values(pointsCouches).flat(), ...importes]) parId.set(f.properties.id, f);
  state.allPoints = [...parId.values()];
}

/** Charge la couche lourde `id` depuis le fichier du PAYS courant si
 *  nécessaire ; renvoie false en cas d'échec (hors connexion, pays sans
 *  cette couche…). */
async function chargerCouche(id) {
  if (pointsCouches[id].length) return true;
  const fichier = (paysActuel().couchesLourdes || {})[id];
  if (!fichier) return false;
  toast(`Chargement des ${COUCHES_LOURDES[id].pluriel}…`);
  try {
    const reponse = await fetch(fichier);
    pointsCouches[id] = (await reponse.json()).features || [];
    await chargerPoints();
    return true;
  } catch (e) {
    console.error(`Impossible de charger ${fichier} :`, e);
    toast(`${COUCHES_LOURDES[id].indisponible} pour le moment (hors connexion ?).`);
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
  // Couches lourdes du pays pas encore chargées : « … » plutôt qu'un 0
  // trompeur. (Une catégorie hors de cette table — ex. `grotte` en NZ — vit
  // dans points.geojson : vrai compte.)
  for (const id of Object.keys(paysActuel().couchesLourdes || {})) {
    if (!pointsCouches[id].length) compteurs.set(id, "…");
  }
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
<gpx version="1.1" creator="SpotMap" xmlns="http://www.topografix.com/GPX/1/1">
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

/** GPX d'un grand itinéraire (GR LineString, Great Walk MultiLineString) :
 *  sa géométrie est directement dans la feature. */
function telechargerGpxGr(grFeature) {
  const geom = grFeature.geometry || {};
  const segments =
    geom.type === "MultiLineString" ? geom.coordinates : [geom.coordinates || []];
  if (!segments.length || !segments[0].length) {
    toast("Tracé indisponible pour cet itinéraire.");
    return;
  }
  telechargerGpx(grFeature.properties?.name || "GR", segments, null);
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
    // Recherche par MOTS-CLÉS : tous les mots présents, peu importe l'ordre
    // (« Tour du Lac Blanc » trouve « Lac Blanc » et réciproquement).
    // Les mots-outils d'une lettre ou deux (du, le, de…) ne filtrent pas.
    const mots = requete.split(/\s+/).filter((m) => m.length > 2);
    const cherche = mots.length ? mots : [requete];
    const trouves = state.allPoints
      .filter((f) => {
        const nom = normaliser(f.properties.name);
        return cherche.every((m) => nom.includes(m));
      })
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

  /** Suggestions de VILLES, ajoutées sous les points. France : geo.api.gouv.fr
   *  (riche, boost population). Autres pays : Nominatim (OSM) restreint au
   *  pays courant, en français (« Turin » comme « Torino » trouvent la ville). */
  async function proposerVilles(nom, jeton, conteneur) {
    let communes = [];
    const paysId = paysActuel().id;
    try {
      if (paysId === "fr") {
        const res = await fetch(
          `https://geo.api.gouv.fr/communes?nom=${encodeURIComponent(nom)}` +
            "&fields=nom,centre,departement&boost=population&limit=3"
        );
        communes = res.ok ? await res.json() : [];
      } else {
        const res = await fetch(
          `https://nominatim.openstreetmap.org/search?format=jsonv2&limit=3` +
            `&countrycodes=${paysId}&featureType=settlement&accept-language=fr` +
            `&q=${encodeURIComponent(nom)}`
        );
        const lieux = res.ok ? await res.json() : [];
        // même forme que geo.api.gouv.fr → le rendu ci-dessous est commun.
        // Nominatim renvoie souvent la ville en double (nœud + limite
        // administrative) : on dédoublonne par nom.
        const vus = new Set();
        communes = lieux
          .map((l) => ({
            nom: (l.display_name || l.name || "").split(",")[0],
            centre: { coordinates: [Number(l.lon), Number(l.lat)] },
            region: (l.display_name || "").split(",").slice(1, 2).join("").trim(),
          }))
          .filter((c) => c.nom && !vus.has(c.nom) && vus.add(c.nom));
      }
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
        c.nom + (c.departement ? ` (${c.departement.code})` : c.region ? ` (${c.region})` : "");
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
 *  l'activation + mode « autour de moi » à 1 km) ; textes seulement, les
 *  points vivent dans pointsCouches et le fichier dans la config du pays. */
const COUCHES_LOURDES = {
  // ⚠️ Ces ids ne déclenchent le dialogue + fichier séparé que si le pays
  // courant les liste dans `couchesLourdes` (js/config/pays.js, id → fichier).
  // Ailleurs, la même catégorie (ex. `grotte` en NZ ou en Italie, points DANS
  // points.geojson) se comporte comme une catégorie normale — passer par
  // coucheLourde(id), jamais par l'objet direct.
  toilettes: {
    dialog: "wc-dialog", pluriel: "toilettes", indisponible: "Toilettes indisponibles",
    vide: "Aucunes toilettes à moins de 1 km",
    proche: "la plus proche", aucun: "Aucunes toilettes connues.",
  },
  eau: {
    dialog: "eau-dialog", pluriel: "points d'eau", indisponible: "Points d'eau indisponibles",
    vide: "Aucun point d'eau à moins de 1 km",
    proche: "le plus proche", aucun: "Aucun point d'eau connu.",
  },
  grotte: {
    dialog: "grottes-dialog", pluriel: "grottes", indisponible: "Grottes indisponibles",
    vide: "Aucune grotte à moins de 1 km",
    proche: "la plus proche", aucun: "Aucune grotte connue.",
  },
  culture: {
    dialog: "culture-dialog", pluriel: "musées", indisponible: "Musées indisponibles",
    vide: "Aucun musée à moins de 1 km",
    proche: "le plus proche", aucun: "Aucun musée connu.",
  },
};

/** Config de couche lourde pour `id` — ou undefined si le pays courant n'a
 *  pas cette couche (la catégorie redevient alors ordinaire, ses points sont
 *  déjà chargés). */
function coucheLourde(id) {
  return (paysActuel().couchesLourdes || {})[id] ? COUCHES_LOURDES[id] : undefined;
}

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
  const conf = coucheLourde(id);
  if (!conf) return; // pays sans couches lourdes : bouton masqué, garde-fou
  try {
    toast("Recherche de votre position…");
    const [lat, lon] = await new Promise((resolve, reject) => {
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve([pos.coords.latitude, pos.coords.longitude]),
        reject,
        { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
      );
    });
    if (!(await chargerCouche(id))) return;
    // Le zoom se fait AVANT le rendu : les marqueurs se remplissent en priorité
    // autour de la position (tri par distance dans setPoints).
    montrerRayon(lat, lon, 1000);
    state.activeThemes = new Set([id]);
    state.statusFilters.clear();
    rafraichir();
    const distances = pointsCouches[id].map((f) =>
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
  for (const bouton of dlg.querySelectorAll(".settings-list button")) {
    bouton.addEventListener("click", () => dlg.close());
  }
  document.getElementById("btn-update").addEventListener("click", verifierMiseAJour);
  document.getElementById("btn-export-pdf").addEventListener("click", exporterCarnetPDF);

  // 📊 Fréquentation : totaux anonymes (voir js/frequentation.js)
  const freqDlg = document.getElementById("frequentation-dialog");
  freqDlg.querySelector(".freq-close").addEventListener("click", () => freqDlg.close());
  document.getElementById("btn-frequentation").addEventListener("click", async () => {
    const zone = freqDlg.querySelector(".freq-stats");
    zone.innerHTML = `<p class="menu-note">Chargement…</p>`;
    freqDlg.showModal();
    const s = await statsFrequentation();
    zone.innerHTML = s
      ? `<div class="freq-tuiles">
           <div class="freq-tuile"><strong>${Number(s.maintenant) || 0}</strong><span>en ce moment</span></div>
           <div class="freq-tuile"><strong>${Number(s.aujourdhui) || 0}</strong><span>aujourd'hui</span></div>
           <div class="freq-tuile"><strong>${Number(s.semaine) || 0}</strong><span>sur 7 jours</span></div>
         </div>`
      : `<p class="menu-note">Le compteur arrive bientôt 🙂</p>`;
    // Détail pour le propriétaire (sans jargon à l'écran) : activer = exécuter
    // supabase/frequentation-schema.sql — guide docs/FREQUENTATION.md.
    if (!s) console.info("Fréquentation : exécuter supabase/frequentation-schema.sql (docs/FREQUENTATION.md).");
  });
}

/** Mode nuit de l'application : couleurs sombres + tuiles de carte
 *  assombries (voir styles.css). Préférence mémorisée. */
function initModeNuit(prefs) {
  const bouton = document.getElementById("btn-mode-nuit");
  let actif = prefs.modeNuit === true;
  const appliquer = () => {
    document.body.classList.toggle("mode-nuit", actif);
    // Tuile des Réglages : icône + libellé séparés
    bouton.querySelector(".tuile-ico").textContent = actif ? "☀️" : "🌙";
    bouton.querySelector(".tuile-lbl").textContent = actif ? "Mode jour" : "Mode nuit";
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
  // Catégories de base INDISPONIBLES dans le pays courant : décochées — leurs
  // points ne sont pas chargés et leurs filtres pollueraient le panneau (les
  // catégories personnelles, hors THEMES, ne sont jamais touchées). Si plus
  // rien n'est coché (ex. premier passage en NZ), la 1re catégorie du pays
  // prend le relais pour ne pas ouvrir une carte vide.
  const pays = paysActuel();
  const exclues = pays.categoriesExclues || [];
  for (const id of [...state.activeThemes]) {
    const deBase = THEMES.some((t) => t.id === id);
    const dispo = (!pays.categories || pays.categories.includes(id)) && !exclues.includes(id);
    if (deBase && !dispo) state.activeThemes.delete(id);
  }
  if (!state.activeThemes.size && pays.categories?.length) {
    state.activeThemes.add(pays.categories[0]);
  }
  // Règle v66 (grosses catégories exclusives) appliquée aussi aux prefs
  // héritées : une grosse ne cohabite avec rien. S'il y a des petites, elles
  // gagnent (les grosses sautent) ; s'il n'y a que des grosses, on garde la 1re.
  const grosses = [...state.activeThemes].filter((id) => coucheLourde(id));
  if (grosses.length && state.activeThemes.size > 1) {
    if (grosses.length < state.activeThemes.size) {
      for (const id of grosses) state.activeThemes.delete(id); // petites présentes
    } else {
      state.activeThemes = new Set([grosses[0]]); // que des grosses
    }
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

/* ------------------------------------------------------------------ */
/* Multi-pays : page de garde + résolution croisée pour le carnet       */
/* ------------------------------------------------------------------ */

// Fond de la page de garde : le monde en polygones (data/monde.geojson,
// Natural Earth simplifié, domaine public) — rendu Leaflet SANS tuiles,
// donc hors-ligne. Chargé une fois par session.
let mondePromesse = null;
function chargerMonde() {
  if (!mondePromesse) {
    mondePromesse = fetch("data/monde.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .catch(() => null); // fichier absent/hors ligne : les boutons suffisent
  }
  return mondePromesse;
}

// Pays « bientôt » de la page de garde : petits points ambrés, purement
// TEASER (survol = nom, clic = clin d'œil). Liste éditoriale, dans l'ordre
// de nos envies — en ajouter un = une ligne.
const PAYS_BIENTOT = [
  ["Pérou", -9.2, -75.0], ["Népal", 28.2, 84.0],
  ["Singapour", 1.35, 103.82], ["Laos", 19.0, 103.0], ["Canada", 56.0, -106.0],
  ["Japon", 36.2, 138.3], ["Norvège", 61.0, 9.0], ["Islande", 64.9, -18.6],
  ["Maroc", 31.8, -6.5], ["Costa Rica", 9.7, -84.2], ["Australie", -25.3, 133.8],
  ["Royaume-Uni", 54.0, -2.0], ["Autriche", 47.5, 14.1],
];

/** Couleur d'un pays de la page de garde : teinte stable dérivée du nom —
 *  le monde est COLORÉ mais chaque pays garde toujours sa couleur. */
function couleurPaysMonde(nom) {
  let h = 0;
  for (const c of nom) h = (h * 31 + c.charCodeAt(0)) % 360;
  return { fill: `hsl(${h} 38% 34%)`, line: `hsl(${h} 30% 46%)` };
}

/** Nom français d'un pays depuis son code ISO2 (repli : nom Natural Earth). */
const nomsFr = ("DisplayNames" in Intl) ? new Intl.DisplayNames(["fr"], { type: "region" }) : null;
function nomPaysFr(iso, nomNe) {
  try {
    const n = iso && nomsFr ? nomsFr.of(iso) : null;
    return n && n !== iso ? n : nomNe;
  } catch {
    return nomNe;
  }
}

/**
 * Page de garde : CARTE DU MONDE cliquable — les pays disponibles sont
 * surlignés (polygones + épingle drapeau), les boutons sous la carte doublent
 * le clic (accessibilité, petits écrans). Résout avec l'id du pays choisi.
 * `annulable` (bouton Réglages) : cliquer le fond referme (resolve null).
 */
function choisirPays(annulable = false) {
  return new Promise((resolve) => {
    const overlay = document.getElementById("pays-overlay");
    const liste = overlay.querySelector(".pays-liste");
    liste.textContent = "";
    let mini = null; // la carte Leaflet de la page de garde

    const terminer = (id) => {
      mini?.remove();
      mini = null;
      overlay.hidden = true;
      resolve(id);
    };

    for (const p of Object.values(PAYS)) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "pays-choix";
      btn.innerHTML =
        `<span class="pays-drapeau" aria-hidden="true">${esc(p.drapeau)}</span>` +
        `<span class="pays-infos"><span class="pays-nom">${esc(p.label)}</span></span>`;
      btn.title = p.sousTitre; // le détail vit en infobulle (cartes compactes)
      btn.addEventListener("click", () => terminer(p.id));
      liste.appendChild(btn);
    }
    if (annulable) {
      overlay.addEventListener("click", function fermer(e) {
        if (e.target === overlay) {
          overlay.removeEventListener("click", fermer);
          terminer(null);
        }
      });
    }
    overlay.hidden = false;

    // Bouton communauté de la page de garde (onclick assigné : choisirPays
    // peut être rappelée, pas d'écouteurs empilés). Le dialogue s'ouvre
    // PAR-DESSUS la carte du monde, même avant tout choix de pays — seul
    // l'import attend qu'un pays soit choisi (garde-fou dans communaute.js).
    document.getElementById("pays-btn-communaute").onclick = () => ouvrirCommunaute("explorer");

    // La carte du monde (après l'affichage : Leaflet doit mesurer le conteneur)
    const parIso = {};
    for (const p of Object.values(PAYS)) parIso[p.id.toUpperCase()] = p;
    chargerMonde().then((monde) => {
      if (!monde || overlay.hidden) return; // déjà choisi, ou fichier indisponible
      // Une VRAIE carte : tuiles OSM, zoom et déplacement LIBRES. Les pays
      // disponibles restent surlignés par-dessus ; hors connexion, les tuiles
      // manquent mais surlignages, points et boutons suffisent.
      mini = L.map("pays-monde", {
        zoomControl: true, attributionControl: true,
        minZoom: 1, maxZoom: 12, zoomSnap: 0.5,
        worldCopyJump: true,
      });
      L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
        attribution: "© OpenStreetMap",
      }).addTo(mini);
      const dispo = monde.features.filter((f) => parIso[f.properties.iso]);
      const autres = monde.features.filter((f) => !parIso[f.properties.iso]);
      // Les autres pays : invisibles sur la carte (les tuiles font le décor),
      // mais le SURVOL donne toujours le nom du pays.
      L.geoJSON({ type: "FeatureCollection", features: autres }, {
        style: { stroke: false, fillColor: "#000", fillOpacity: 0.001 },
        onEachFeature: (f, couche) => {
          couche.bindTooltip(esc(nomPaysFr(f.properties.iso, f.properties.nom)), {
            sticky: true, direction: "top", className: "pays-tooltip",
          });
        },
      }).addTo(mini);
      // Pays DISPONIBLES : halo vert SEMI-TRANSPARENT (la vraie carte reste
      // lisible dessous), nom au survol, clic = choisir
      L.geoJSON({ type: "FeatureCollection", features: dispo }, {
        style: { color: "#0a9396", weight: 2.5, fillColor: "#18a883", fillOpacity: 0.3 },
        onEachFeature: (f, couche) => {
          const p = parIso[f.properties.iso];
          couche.bindTooltip(`${esc(p.drapeau)} ${esc(p.label)} — disponible !`, {
            sticky: true, direction: "top", className: "pays-tooltip pays-tooltip-dispo",
          });
          couche.on("click", () => terminer(p.id));
          couche.on("mouseover", () => couche.setStyle({ fillOpacity: 0.5 }));
          couche.on("mouseout", () => couche.setStyle({ fillOpacity: 0.3 }));
        },
      }).addTo(mini);
      // POINTS des pays disponibles : gros, pulsants, nom au survol
      for (const p of Object.values(PAYS)) {
        const icone = L.divIcon({ className: "", iconSize: null, html: `<span class="pays-point"></span>` });
        L.marker(p.vue.center, { icon: icone, keyboard: false })
          .addTo(mini)
          .bindTooltip(`${esc(p.drapeau)} ${esc(p.label)} — disponible !`, {
            direction: "top", offset: [0, -10], className: "pays-tooltip pays-tooltip-dispo",
          })
          .on("click", () => terminer(p.id));
      }
      // Points « BIENTÔT » : petits, ambrés — survol = nom, clic = clin d'œil
      for (const [nom, lat, lon] of PAYS_BIENTOT) {
        const icone = L.divIcon({ className: "", iconSize: null, html: `<span class="pays-point-bientot"></span>` });
        L.marker([lat, lon], { icon: icone, keyboard: false })
          .addTo(mini)
          .bindTooltip(`${esc(nom)} — bientôt`, {
            direction: "top", offset: [0, -8], className: "pays-tooltip",
          })
          .on("click", () => toast(`${nom} arrive un jour 🌱 — dix pays vous attendent déjà !`));
      }
      // Monde sans l'Antarctique (vide et encombrant au zoom monde)
      setTimeout(() => {
        if (!mini) return;
        mini.invalidateSize();
        mini.fitBounds([[-55, -180], [74, 180]]);
      }, 60);
    });
  });
}

// Le carnet et les statuts sont COMMUNS à tous les pays (clés = ids de points,
// préfixés par pays). Pour que le grimoire affiche aussi les souvenirs des
// autres pays, leurs points sont chargés À L'OUVERTURE du carnet (une fois par
// session ; celui du pays courant est déjà pré-caché par le SW). Limite : les
// couches lourdes (toilettes/eau/grottes) des autres pays ne sont pas relues.
let pointsAutresPays = null;
async function chargerPointsAutresPays() {
  if (pointsAutresPays) return pointsAutresPays;
  const charges = [];
  for (const p of Object.values(PAYS)) {
    if (p.id === paysActuel().id) continue;
    try {
      const r = await fetch(p.fichierPoints);
      charges.push(...((await r.json()).features || []));
    } catch {
      /* hors ligne ou fichier absent : les entrées de ce pays resteront masquées */
    }
  }
  pointsAutresPays = charges;
  return pointsAutresPays;
}

async function demarrer() {
  // PAGE DE GARDE : au tout premier lancement (aucun pays mémorisé), le choix
  // du pays précède tout — les données chargées en dépendent.
  if (!paysChoisi()) {
    definirPays(await choisirPays());
  }
  const pays = paysActuel();

  // Catégories personnalisées et personnalisations AVANT tout rendu
  registerCustomThemes(await storage.getCustomThemes());
  setThemeOverrides(await storage.getThemeOverrides());

  const prefs = await storage.getPrefs();
  const premiereVisite = prefs.activeThemes === undefined && prefs.tutoVu !== true;
  state.statuses = await storage.getStatuses();
  await chargerPoints();
  restaurerPrefs(prefs);

  // Vue mémorisée PAR PAYS (`vue_fr`, `vue_nz`…) — sinon changer de pays
  // rouvrirait la carte sur l'autre hémisphère. Repli : l'ancienne pref
  // globale (center/zoom, historique France), puis la vue par défaut du pays.
  const vuePays = prefs[`vue_${pays.id}`] ||
    (pays.id === "fr" && prefs.center ? { center: prefs.center, zoom: prefs.zoom } : pays.vue);
  const carte = initMap({ ...prefs, center: vuePays.center, zoom: vuePays.zoom }, {
    onPointClick: ouvrirFiche,
    onGrClick: ouvrirFicheGr,
    onViewChange: (vue) => storage.savePrefs({ [`vue_${pays.id}`]: vue }),
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
      if (coucheLourde(id) && coche) {
        const choix = await demanderModeCouche(coucheLourde(id).dialog);
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
      if (coche) {
        // GROSSES catégories (couches lourdes : toilettes/eau/grottes/musées)
        // EXCLUSIVES (demande utilisateur v66) : une grosse s'affiche SEULE
        // (activer une grosse décoche tout), et cocher une petite décoche la
        // grosse. Seules les petites catégories se combinent entre elles.
        if (coucheLourde(id)) {
          state.activeThemes.clear();
        } else {
          for (const autre of [...state.activeThemes]) {
            if (coucheLourde(autre)) state.activeThemes.delete(autre);
          }
        }
      }
      coche ? state.activeThemes.add(id) : state.activeThemes.delete(id);
      if (coche) {
        state.statusFilters.clear(); // exclusif avec le mode suivi
        // Chaque OUVERTURE de catégorie repart avec des filtres VIERGES :
        // l'utilisateur choisit lui-même — aucune sélection d'une session
        // passée ne reste accrochée (demande utilisateur v64).
        delete state.filterSelections[id];
        if (coucheLourde(id) && !(await chargerCouche(id))) {
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
  // « 🗺️ Changer de pays » (Réglages) et logo/titre SpotMap (bouton 🌍 du
  // panneau) : rouvrent la page de garde — la carte du monde ; un choix
  // différent recharge la page (ré-init complète : données, vue, catégories).
  const ouvrirMonde = async () => {
    const choix = await choisirPays(true);
    if (choix && choix !== pays.id) {
      definirPays(choix);
      location.reload();
    }
  };
  document.getElementById("btn-pays").addEventListener("click", () => {
    document.getElementById("settings-dialog").close();
    ouvrirMonde();
  });
  document.getElementById("btn-home").addEventListener("click", ouvrirMonde);

  // ✅ « Mes lieux faits » : la carte ne montre plus que les lieux ✓ Fait
  // (mécanisme des filtres de suivi) et se cadre dessus. Re-cocher un statut
  // ou une catégorie dans le panneau rend la vue normale.
  document.getElementById("btn-vue-faits").addEventListener("click", () => {
    const faits = state.allPoints.filter((f) => state.statuses[f.properties.id] === "fait");
    if (!faits.length) {
      toast("Aucun lieu marqué ✓ Fait pour l'instant — ouvrez une fiche et touchez ✓ !");
      return;
    }
    state.statusFilters = new Set(["fait"]);
    rafraichir();
    const lats = faits.map((f) => f.geometry.coordinates[1]);
    const lons = faits.map((f) => f.geometry.coordinates[0]);
    getMap().fitBounds(
      [[Math.min(...lats), Math.min(...lons)], [Math.max(...lats), Math.max(...lons)]],
      { padding: [46, 46], maxZoom: 13 }
    );
    toast(`Vos ${faits.length} lieu(x) faits ✓`);
  });

  // Catégories COMMUNAUTAIRES : partager les siennes / importer celles des
  // autres (js/communaute.js). L'import écrit les points comme des points
  // utilisateur (mêmes règles que l'import de fichier) et coche la catégorie.
  initCommunaute({
    getMesCategories: async () => {
      const miens = await storage.getUserPoints().catch(() => []);
      return (await storage.getCustomThemes()).map((t) => ({
        ...t,
        nbPoints: miens.filter((f) => f.properties.theme === t.id).length,
      }));
    },
    getPointsDeTheme: async (id) =>
      (await storage.getUserPoints().catch(() => [])).filter((f) => f.properties.theme === id),
    importerCategorie: async (theme, points) => {
      const customs = await storage.getCustomThemes();
      if (!customs.some((t) => t.id === theme.id)) customs.push(theme);
      await storage.saveCustomThemes(customs);
      registerCustomThemes(customs);
      await storage.addUserPoints(points); // ids stables comm-… : réimport = mise à jour
      await apresImportPoints(points);
    },
    estImportee: (themeId) => isCustomTheme(themeId),
  });
  document.getElementById("btn-communaute").addEventListener("click", () => {
    document.getElementById("settings-dialog").close();
    ouvrirCommunaute("explorer");
  });
  initModeNuit(prefs);
  initProtectionDonnees(prefs, premiereVisite);
  initFrequentation(); // ping de présence anonyme (silencieux)
  afficherVersion();
  initCarnet({
    // Carnet COMMUN : points du pays courant + ceux des autres pays (chargés
    // par avantOuverture) — les souvenirs suivent l'utilisateur partout.
    getPoints: () => [...state.allPoints, ...(pointsAutresPays || [])],
    getStatuses: () => state.statuses,
    onVoirSurCarte: (feature) => allerAuPoint(feature),
    avantOuverture: chargerPointsAutresPays,
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
  for (const id of Object.keys(pays.couchesLourdes || {})) {
    if (state.activeThemes.has(id)) {
      chargerCouche(id).then((ok) => ok && rafraichir());
    }
  }
  // Bouton 🏃🚻 (toilettes autour de moi) : seulement là où la couche existe.
  document.getElementById("btn-wc").hidden = !(pays.couchesLourdes || {}).toilettes;

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
