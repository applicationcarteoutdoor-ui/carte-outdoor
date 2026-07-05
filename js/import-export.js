/**
 * Import / export unifié.
 *
 * Un seul bouton d'import accepte tous les formats (voir docs/FORMAT-IMPORT.md) :
 *  - .gpx            → trace(s)
 *  - .kml / .kmz     → converti via toGeoJSON (KMZ décompressé par fflate) ;
 *                      les lignes deviennent des traces, les points passent
 *                      par le dialogue de validation
 *  - .geojson/.json  → FeatureCollection (points et/ou lignes) ou fichier de
 *                      sauvegarde de l'application {formatVersion, points,
 *                      statuses, journal}
 *  - .csv            → points (colonnes name, lat, lon [, theme, ...])
 *
 * Chaque point est validé individuellement : les erreurs sont listées avec
 * leur position, et l'utilisateur importe les entrées valides ou annule.
 * Les fichiers sont traités séquentiellement (un dialogue à la fois).
 */

import { allThemes, themeExists, registerCustomThemes } from "./config/themes.js";
import * as storage from "./storage.js";
import { importTraceGeojson } from "./gpx.js";

/* global toGeoJSON, fflate */

let dialog = null;
let cb = {}; // {getExistingIds, getExportData, onImportedPoints, onImportedTraces}

// Résultat de l'analyse affichée dans le dialogue, et résolveur de la
// promesse permettant de traiter les fichiers l'un après l'autre.
let analyseEnCours = null;
let resoudreDialogue = null;

export function initImportExport(callbacks) {
  cb = callbacks;
  dialog = document.getElementById("import-dialog");

  // L'ouverture du sélecteur de fichiers est déclenchée ailleurs (panneau
  // des catégories, volet traces, menu ⋯) : ce module ne gère que l'analyse.
  const input = document.getElementById("file-import");
  input.addEventListener("change", async () => {
    const fichiers = [...input.files];
    input.value = "";
    let nbTraces = 0;
    for (const fichier of fichiers) {
      nbTraces += await traiterFichier(fichier);
    }
    if (nbTraces) {
      toast(`${nbTraces} trace(s) importée(s) — visibles dans le panneau latéral, onglet Traces.`);
      cb.onImportedTraces?.();
    }
  });

  document.getElementById("btn-export").addEventListener("click", exporter);
  dialog.querySelector(".import-cancel").addEventListener("click", () => fermerDialogue(false));
  dialog.querySelector(".import-confirm").addEventListener("click", confirmerImport);
  dialog.addEventListener("cancel", () => fermerDialogue(false)); // touche Échap
  dialog.querySelector("#import-theme-select").addEventListener("change", majBoutonConfirmer);
}

/* ------------------------------------------------------------------ */
/* Routage par format                                                   */
/* ------------------------------------------------------------------ */

/** Traite un fichier ; retourne le nombre de traces créées. */
async function traiterFichier(fichier) {
  const nom = fichier.name;
  const nomSansExt = nom.replace(/\.[^.]+$/, "");
  const ext = (nom.match(/\.([^.]+)$/)?.[1] || "").toLowerCase();
  try {
    if (ext === "gpx") {
      const geojson = toGeoJSON.gpx(parserXML(await fichier.text()));
      return await importerLignes(geojson, nomDeTrace(geojson, nomSansExt));
    }
    if (ext === "kml" || ext === "kmz") {
      let texte;
      if (ext === "kmz") {
        // KMZ = zip contenant un doc.kml
        const zip = fflate.unzipSync(new Uint8Array(await fichier.arrayBuffer()));
        const entree = Object.keys(zip).find((n) => n.toLowerCase().endsWith(".kml"));
        if (!entree) throw new Error("aucun fichier .kml dans le KMZ");
        texte = new TextDecoder().decode(zip[entree]);
      } else {
        texte = await fichier.text();
      }
      const geojson = toGeoJSON.kml(parserXML(texte));
      const nbTraces = await importerLignes(geojson, nomDeTrace(geojson, nomSansExt));
      await importerPointsSiPresents(geojson, nom);
      return nbTraces;
    }
    if (ext === "csv") {
      await afficherRapportEtAttendre(nom, analyserCSV(await fichier.text()));
      return 0;
    }
    // .json / .geojson
    const data = JSON.parse(await fichier.text());
    if (data.formatVersion && data.points) {
      // Fichier de sauvegarde de l'application : les catégories personnalisées
      // sont restaurées AVANT la validation (les points peuvent s'y référer)
      if (Array.isArray(data.customThemes) && data.customThemes.length) {
        const existants = await storage.getCustomThemes();
        const ids = new Set(existants.map((t) => t.id));
        for (const t of data.customThemes) {
          if (t && t.id && !ids.has(t.id)) existants.push(t);
        }
        await storage.saveCustomThemes(existants);
        registerCustomThemes(existants);
      }
      const resultat = validerFeatureCollection(data.points);
      resultat.statuses = typeof data.statuses === "object" && data.statuses ? data.statuses : null;
      resultat.journal = typeof data.journal === "object" && data.journal ? data.journal : null;
      resultat.sorties = Array.isArray(data.sorties) ? data.sorties : null;
      await afficherRapportEtAttendre(nom, resultat);
      return 0;
    }
    if (data.type === "FeatureCollection") {
      const nbTraces = await importerLignes(data, nomDeTrace(data, nomSansExt));
      await importerPointsSiPresents(data, nom);
      return nbTraces;
    }
    throw new Error("JSON non reconnu (ni FeatureCollection GeoJSON, ni sauvegarde)");
  } catch (e) {
    await afficherRapportEtAttendre(nom, {
      valides: [],
      erreurs: [`Fichier illisible : ${e.message}`],
    });
    return 0;
  }
}

function parserXML(texte) {
  const xml = new DOMParser().parseFromString(texte, "application/xml");
  if (xml.querySelector("parsererror")) throw new Error("XML invalide");
  return xml;
}

/** Nom de la trace : balise <name> de la première ligne, sinon nom du fichier. */
function nomDeTrace(geojson, repli) {
  const ligne = (geojson.features || []).find(
    (f) => f.geometry?.type === "LineString" || f.geometry?.type === "MultiLineString"
  );
  return (ligne?.properties?.name || repli).trim();
}

/** Importe les lignes d'une FeatureCollection comme UNE trace (1 fichier = 1 trace). */
async function importerLignes(geojson, nom) {
  const lignes = (geojson.features || []).filter(
    (f) => f.geometry?.type === "LineString" || f.geometry?.type === "MultiLineString"
  );
  if (!lignes.length) return 0;
  const trace = await importTraceGeojson(nom, { type: "FeatureCollection", features: lignes });
  return trace ? 1 : 0;
}

/** Si la collection contient des points, les passe au dialogue de validation. */
async function importerPointsSiPresents(geojson, nomFichier) {
  const points = (geojson.features || []).filter((f) => f.geometry?.type === "Point");
  if (!points.length) return;
  const resultat = validerFeatureCollection({ type: "FeatureCollection", features: points });
  await afficherRapportEtAttendre(nomFichier, resultat);
}

/* ------------------------------------------------------------------ */
/* Validation des points                                                */
/* ------------------------------------------------------------------ */

function validerCoordonnees(lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return "coordonnées non numériques";
  if (lat < -90 || lat > 90) return `latitude hors limites (${lat})`;
  if (lon < -180 || lon > 180) return `longitude hors limites (${lon})`;
  return null;
}

/**
 * Valide une FeatureCollection de points.
 * Si AUCUN point n'a de thème connu (KML, GeoJSON tiers…), le dialogue
 * demandera un thème unique pour tout le fichier (themeRequis) au lieu de
 * rejeter chaque point.
 */
function validerFeatureCollection(fc) {
  const valides = [];
  const erreurs = [];
  const features = Array.isArray(fc.features) ? fc.features : [];
  if (!features.length) erreurs.push("Aucun point dans le fichier.");

  const aucunTheme = features.every((f) => !themeExists(f?.properties?.theme));

  features.forEach((f, i) => {
    const ou = `point ${i + 1}`;
    if (!f || !f.geometry || f.geometry.type !== "Point") {
      erreurs.push(`${ou} : géométrie invalide (Point attendu)`);
      return;
    }
    const [lon, lat] = f.geometry.coordinates || [];
    const errCoord = validerCoordonnees(lat, lon);
    if (errCoord) {
      erreurs.push(`${ou} : ${errCoord}`);
      return;
    }
    const p = f.properties || {};
    if (!p.name || !String(p.name).trim()) {
      erreurs.push(`${ou} : propriété « name » manquante`);
      return;
    }
    if (!aucunTheme && !themeExists(p.theme)) {
      erreurs.push(
        `${ou} (${p.name}) : thème « ${p.theme || "absent"} » inconnu — thèmes valides : ${allThemes().map((t) => t.id).join(", ")}`
      );
      return;
    }
    valides.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        id: p.id ? String(p.id) : "",
        name: String(p.name).trim(),
        theme: themeExists(p.theme) ? p.theme : "",
        description: p.description ? String(p.description) : "",
        link: p.link ? String(p.link) : "",
        links: Array.isArray(p.links) ? p.links : [],
        photos: Array.isArray(p.photos) ? p.photos.map(String) : [],
        details: typeof p.details === "object" && p.details ? p.details : {},
      },
    });
  });
  return { valides, erreurs, statuses: null, journal: null, themeRequis: aucunTheme };
}

/** Analyse un CSV (séparateur , ou ; détecté sur l'en-tête). */
function analyserCSV(texte) {
  const lignes = decouperCSV(texte);
  const erreurs = [];
  const valides = [];
  if (lignes.length < 2) {
    return { valides, erreurs: ["CSV vide ou sans ligne de données."], themeRequis: false };
  }

  const entete = lignes[0].map((c) => c.trim().toLowerCase());
  const idx = (nom) => entete.indexOf(nom);
  for (const requis of ["name", "lat", "lon"]) {
    if (idx(requis) === -1) {
      return {
        valides,
        erreurs: [`Colonne obligatoire « ${requis} » absente de l'en-tête (colonnes trouvées : ${entete.join(", ")}).`],
        themeRequis: false,
      };
    }
  }
  const aColonneTheme = idx("theme") !== -1;
  const colonnesConnues = new Set(["name", "lat", "lon", "theme", "description", "link", "id"]);

  lignes.slice(1).forEach((champs, i) => {
    const ou = `ligne ${i + 2}`;
    if (champs.every((c) => !c.trim())) return;
    const nom = (champs[idx("name")] || "").trim();
    if (!nom) {
      erreurs.push(`${ou} : nom manquant`);
      return;
    }
    const lat = parseFloat((champs[idx("lat")] || "").replace(",", "."));
    const lon = parseFloat((champs[idx("lon")] || "").replace(",", "."));
    const errCoord = validerCoordonnees(lat, lon);
    if (errCoord) {
      erreurs.push(`${ou} (${nom}) : ${errCoord}`);
      return;
    }
    let theme = "";
    if (aColonneTheme) {
      theme = (champs[idx("theme")] || "").trim();
      if (!themeExists(theme)) {
        erreurs.push(`${ou} (${nom}) : thème « ${theme || "vide"} » inconnu`);
        return;
      }
    }
    const details = {};
    entete.forEach((col, j) => {
      if (!colonnesConnues.has(col) && champs[j] && champs[j].trim()) {
        details[col] = champs[j].trim();
      }
    });
    valides.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        id: idx("id") !== -1 ? (champs[idx("id")] || "").trim() : "",
        name: nom,
        theme,
        description: idx("description") !== -1 ? (champs[idx("description")] || "").trim() : "",
        link: idx("link") !== -1 ? (champs[idx("link")] || "").trim() : "",
        links: [],
        photos: [],
        details,
      },
    });
  });

  return { valides, erreurs, statuses: null, journal: null, themeRequis: !aColonneTheme };
}

/** Découpe un texte CSV en lignes de champs (guillemets gérés, séparateur , ou ;). */
function decouperCSV(texte) {
  const premiereLigne = texte.slice(0, texte.indexOf("\n"));
  const sep = (premiereLigne.match(/;/g) || []).length > (premiereLigne.match(/,/g) || []).length ? ";" : ",";
  const lignes = [];
  let champs = [];
  let champ = "";
  let entreGuillemets = false;
  for (let i = 0; i < texte.length; i++) {
    const c = texte[i];
    if (entreGuillemets) {
      if (c === '"' && texte[i + 1] === '"') {
        champ += '"';
        i++;
      } else if (c === '"') {
        entreGuillemets = false;
      } else {
        champ += c;
      }
    } else if (c === '"') {
      entreGuillemets = true;
    } else if (c === sep) {
      champs.push(champ);
      champ = "";
    } else if (c === "\n" || c === "\r") {
      if (c === "\r" && texte[i + 1] === "\n") i++;
      champs.push(champ);
      if (champs.some((x) => x !== "")) lignes.push(champs);
      champs = [];
      champ = "";
    } else {
      champ += c;
    }
  }
  champs.push(champ);
  if (champs.some((x) => x !== "")) lignes.push(champs);
  return lignes;
}

/* ------------------------------------------------------------------ */
/* Dialogue de rapport et confirmation                                  */
/* ------------------------------------------------------------------ */

/** Affiche le rapport et attend la décision de l'utilisateur (promesse). */
function afficherRapportEtAttendre(nomFichier, resultat) {
  analyseEnCours = resultat;

  dialog.querySelector(".import-filename").textContent = nomFichier;
  dialog.querySelector(".import-summary").textContent =
    `${resultat.valides.length} point(s) valide(s), ${resultat.erreurs.length} erreur(s)` +
    (resultat.statuses ? ` — inclut le suivi (${Object.keys(resultat.statuses).length} statut(s))` : "") +
    (resultat.journal ? ` et le carnet (${Object.keys(resultat.journal).length} point(s))` : "");

  const ul = dialog.querySelector(".import-errors");
  ul.textContent = "";
  for (const e of resultat.erreurs) {
    const li = document.createElement("li");
    li.textContent = e;
    ul.appendChild(li);
  }
  ul.style.display = resultat.erreurs.length ? "" : "none";

  const zoneTheme = dialog.querySelector(".import-theme");
  const select = dialog.querySelector("#import-theme-select");
  if (resultat.themeRequis && resultat.valides.length) {
    select.textContent = "";
    select.appendChild(new Option("— Choisir la catégorie des points —", ""));
    for (const t of allThemes()) select.appendChild(new Option(`${t.icon} ${t.label}`, t.id));
    zoneTheme.style.display = "";
  } else {
    zoneTheme.style.display = "none";
  }

  majBoutonConfirmer();
  dialog.showModal();
  return new Promise((resolve) => {
    resoudreDialogue = resolve;
  });
}

function fermerDialogue(importe) {
  if (dialog.open) dialog.close();
  resoudreDialogue?.(importe);
  resoudreDialogue = null;
}

function majBoutonConfirmer() {
  const btn = dialog.querySelector(".import-confirm");
  const themeManquant =
    analyseEnCours?.themeRequis && !dialog.querySelector("#import-theme-select").value;
  const nb = analyseEnCours?.valides.length || 0;
  btn.disabled = nb === 0 || themeManquant;
  btn.textContent = nb ? `Importer ${nb} point(s)` : "Rien à importer";
}

async function confirmerImport() {
  const { valides, statuses, journal, sorties, themeRequis } = analyseEnCours;
  const themeChoisi = dialog.querySelector("#import-theme-select").value;

  const idsExistants = new Set(cb.getExistingIds());
  const horodatage = Date.now().toString(36);
  valides.forEach((f, i) => {
    if (themeRequis) f.properties.theme = themeChoisi;
    if (!f.properties.id) f.properties.id = `imp-${horodatage}-${i + 1}`;
    let id = f.properties.id;
    let n = 2;
    while (idsExistants.has(id)) id = `${f.properties.id}-${n++}`;
    f.properties.id = id;
    idsExistants.add(id);
  });

  await storage.addUserPoints(valides);
  if (statuses) await storage.mergeStatuses(statuses);
  if (journal) await storage.mergeJournals(journal);
  if (sorties) await storage.mergeSorties(sorties);
  fermerDialogue(true);
  cb.onImportedPoints?.(valides);
}

/* ------------------------------------------------------------------ */
/* Export                                                               */
/* ------------------------------------------------------------------ */

async function exporter() {
  const { points, statuses, journal, customThemes, sorties } = await cb.getExportData();
  const sauvegarde = {
    formatVersion: 2,
    exportedAt: new Date().toISOString(),
    application: "carte-outdoor",
    points: { type: "FeatureCollection", features: points },
    statuses,
    journal,
    customThemes,
    sorties,
  };
  const blob = new Blob([JSON.stringify(sauvegarde, null, 1)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `carte-outdoor-sauvegarde-${new Date().toISOString().slice(0, 10)}.json`;
  a.click();
  URL.revokeObjectURL(url);
  toast("Sauvegarde exportée (points importés, suivi et carnet).");
}

/* ------------------------------------------------------------------ */
/* Dialogue de confirmation                                             */
/* ------------------------------------------------------------------ */

/**
 * Demande confirmation via un dialogue intégré et renvoie une promesse de
 * booléen. Remplace le confirm() natif, silencieusement ignoré dans certains
 * contextes (PWA installée, dialogues bloqués par le navigateur, iframe).
 */
export function confirmer(message) {
  const dlg = document.getElementById("confirm-dialog");
  dlg.querySelector(".confirm-message").textContent = message;
  dlg.showModal();
  return new Promise((resolve) => {
    const repondre = (ok) => {
      if (dlg.open) dlg.close();
      resolve(ok);
    };
    // onclick (et non addEventListener) : les handlers sont remplacés à
    // chaque appel, pas empilés.
    dlg.querySelector(".confirm-ok").onclick = () => repondre(true);
    dlg.querySelector(".confirm-cancel").onclick = () => repondre(false);
    dlg.oncancel = () => resolve(false); // touche Échap
  });
}

/* ------------------------------------------------------------------ */
/* Petit toast de confirmation                                          */
/* ------------------------------------------------------------------ */

let toastTimer = null;

export function toast(message) {
  const el = document.getElementById("toast");
  el.textContent = message;
  el.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (el.hidden = true), 4000);
}
