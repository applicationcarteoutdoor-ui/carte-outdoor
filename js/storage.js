/**
 * Couche de persistance locale.
 *
 * Toute l'application passe par ce module pour lire/écrire des données :
 * l'API est volontairement asynchrone partout, pour pouvoir remplacer un
 * jour localStorage/IndexedDB par un back-end (Supabase, Firebase…) sans
 * toucher au reste du code.
 *
 * Répartition :
 *  - localStorage : préférences d'interface, statuts, personnalisation des
 *                   catégories (petits volumes)
 *  - IndexedDB    : points importés, traces, carnet avec photos (gros volumes)
 */

const PREFIX = "carte-outdoor:";
const KEY_PREFS = PREFIX + "prefs";
const KEY_STATUSES = PREFIX + "statuses";
const KEY_THEME_OVERRIDES = PREFIX + "themeOverrides";

const DB_NAME = "carte-outdoor";
const DB_VERSION = 3;
const STORE_POINTS = "userPoints"; // features GeoJSON importées (clé : properties.id)
const STORE_TRACKS = "tracks"; // traces GPX/KML… (clé : id)
const STORE_JOURNAL = "journal"; // carnet par point (clé : pointId)
const STORE_CARNET = "carnet"; // réglages du carnet : thème + images (clé : cle)

/* ------------------------------------------------------------------ */
/* localStorage                                                         */
/* ------------------------------------------------------------------ */

function lireJSON(key, defaut) {
  try {
    const brut = localStorage.getItem(key);
    return brut ? JSON.parse(brut) : defaut;
  } catch {
    return defaut;
  }
}

function ecrireJSON(key, valeur) {
  try {
    localStorage.setItem(key, JSON.stringify(valeur));
  } catch (e) {
    console.warn("localStorage indisponible :", e);
  }
}

/** Préférences d'interface : filtres actifs, fond de carte, position… */
export async function getPrefs() {
  return lireJSON(KEY_PREFS, {});
}

/** Fusionne `patch` dans les préférences existantes. */
export async function savePrefs(patch) {
  ecrireJSON(KEY_PREFS, { ...lireJSON(KEY_PREFS, {}), ...patch });
}

/** Statuts de suivi : { idDuPoint: "fait" | "a-faire" | "favori" } */
export async function getStatuses() {
  return lireJSON(KEY_STATUSES, {});
}

/** Change le statut d'un point ; `null` supprime le suivi. */
export async function setStatus(pointId, statut) {
  const statuses = lireJSON(KEY_STATUSES, {});
  if (statut === null || statut === undefined) delete statuses[pointId];
  else statuses[pointId] = statut;
  ecrireJSON(KEY_STATUSES, statuses);
  return statuses;
}

/** Fusionne plusieurs statuts d'un coup (import de sauvegarde). */
export async function mergeStatuses(nouveaux) {
  const statuses = { ...lireJSON(KEY_STATUSES, {}), ...nouveaux };
  ecrireJSON(KEY_STATUSES, statuses);
  return statuses;
}

/* ------------------------------------------------------------------ */
/* Sorties : journal horodaté des « fait » — alimente le Carnet         */
/* ------------------------------------------------------------------ */

const KEY_SORTIES = PREFIX + "sorties";

/** Toutes les sorties : [{id, pointId, date|null}] — date null = inconnue
 *  (points marqués « fait » avant l'existence du carnet). */
export async function getSorties() {
  return lireJSON(KEY_SORTIES, []);
}

/** Enregistre une sortie (date ISO, défaut : maintenant). */
export async function addSortie(pointId, date = new Date().toISOString()) {
  const sorties = lireJSON(KEY_SORTIES, []);
  const sortie = {
    id: `s-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    pointId,
    date,
  };
  sorties.push(sortie);
  ecrireJSON(KEY_SORTIES, sorties);
  return sortie;
}

/** Met à jour une sortie (ex. préciser une date inconnue). */
export async function updateSortie(id, patch) {
  ecrireJSON(
    KEY_SORTIES,
    lireJSON(KEY_SORTIES, []).map((s) => (s.id === id ? { ...s, ...patch } : s))
  );
}

export async function deleteSortie(id) {
  ecrireJSON(KEY_SORTIES, lireJSON(KEY_SORTIES, []).filter((s) => s.id !== id));
}

/** Décocher « fait » retire la sortie du jour (faux clic) ET l'éventuelle
 *  sortie « seed » sans date : elle n'existe que parce que le point était
 *  marqué fait (seedSortiesDepuisStatuts) — la garder après le retrait du
 *  statut laissait une entrée fantôme indélébile dans le carnet.
 *  Les sorties datées plus anciennes, elles, restent dans le carnet. */
export async function deleteSortieDuJour(pointId) {
  const jour = new Date().toISOString().slice(0, 10);
  const sorties = lireJSON(KEY_SORTIES, []).filter((s) => {
    if (s.pointId !== pointId) return true;
    if (!s.date) return false; // seed « date inconnue » : liée au statut fait
    return s.date.slice(0, 10) !== jour;
  });
  ecrireJSON(KEY_SORTIES, sorties);
}

/** Toutes les sorties d'un point disparaissent avec lui. */
export async function deleteSortiesDuPoint(pointId) {
  ecrireJSON(KEY_SORTIES, lireJSON(KEY_SORTIES, []).filter((s) => s.pointId !== pointId));
}

/** Les points déjà « fait » avant le carnet reçoivent une sortie « date
 *  inconnue » (une seule fois : l'id de seed est stable). */
export async function seedSortiesDepuisStatuts() {
  const statuses = lireJSON(KEY_STATUSES, {});
  const sorties = lireJSON(KEY_SORTIES, []);
  const connus = new Set(sorties.map((s) => s.pointId));
  let modifie = false;
  for (const [pointId, statut] of Object.entries(statuses)) {
    if (statut === "fait" && !connus.has(pointId)) {
      sorties.push({ id: `s-seed-${pointId}`, pointId, date: null });
      modifie = true;
    }
  }
  if (modifie) ecrireJSON(KEY_SORTIES, sorties);
  return sorties;
}

/** Fusionne des sorties importées (sauvegarde), sans doublons d'id. */
export async function mergeSorties(importees) {
  const sorties = lireJSON(KEY_SORTIES, []);
  const ids = new Set(sorties.map((s) => s.id));
  for (const s of importees || []) if (!ids.has(s.id)) sorties.push(s);
  ecrireJSON(KEY_SORTIES, sorties);
}

/** Personnalisation des catégories : { themeId: {label, color, textColor, icon} } */
export async function getThemeOverrides() {
  return lireJSON(KEY_THEME_OVERRIDES, {});
}

export async function saveThemeOverrides(overrides) {
  ecrireJSON(KEY_THEME_OVERRIDES, overrides);
}

const KEY_CUSTOM_THEMES = PREFIX + "customThemes";

/** Catégories créées par l'utilisateur : [{id, label, color, textColor, icon}] */
export async function getCustomThemes() {
  return lireJSON(KEY_CUSTOM_THEMES, []);
}

export async function saveCustomThemes(liste) {
  ecrireJSON(KEY_CUSTOM_THEMES, liste);
}

/* Packs de catégories (v72) — mêmes patterns que les catégories perso. */
const KEY_CUSTOM_PACKS = PREFIX + "customPacks";
const KEY_PACK_OVERRIDES = PREFIX + "packOverrides";

/** Packs créés par l'utilisateur : [{id, label, icon, color, categories[]}] */
export async function getCustomPacks() {
  return lireJSON(KEY_CUSTOM_PACKS, []);
}

export async function saveCustomPacks(liste) {
  ecrireJSON(KEY_CUSTOM_PACKS, liste);
}

/** Personnalisation des packs PAR DÉFAUT : { packId: {label?, icon?, color?, categories?} } */
export async function getPackOverrides() {
  return lireJSON(KEY_PACK_OVERRIDES, {});
}

export async function savePackOverrides(overrides) {
  ecrireJSON(KEY_PACK_OVERRIDES, overrides);
}

/* ------------------------------------------------------------------ */
/* IndexedDB : mini-wrapper maison (aucune dépendance)                  */
/* ------------------------------------------------------------------ */

let dbPromise = null;

function ouvrirDB() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const db = req.result;
        if (!db.objectStoreNames.contains(STORE_POINTS)) {
          db.createObjectStore(STORE_POINTS, { keyPath: "properties.id" });
        }
        if (!db.objectStoreNames.contains(STORE_TRACKS)) {
          db.createObjectStore(STORE_TRACKS, { keyPath: "id" });
        }
        if (!db.objectStoreNames.contains(STORE_JOURNAL)) {
          db.createObjectStore(STORE_JOURNAL, { keyPath: "pointId" });
        }
        if (!db.objectStoreNames.contains(STORE_CARNET)) {
          db.createObjectStore(STORE_CARNET, { keyPath: "cle" });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return dbPromise;
}

async function transaction(storeName, mode, action) {
  const db = await ouvrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, mode);
    const store = tx.objectStore(storeName);
    const resultat = action(store);
    tx.oncomplete = () => {
      if (resultat && "result" in resultat) resolve(resultat.result);
      else resolve(undefined);
    };
    tx.onerror = () => reject(tx.error);
  });
}

/* ------------------------------------------------------------------ */
/* Points importés par l'utilisateur                                    */
/* ------------------------------------------------------------------ */

export async function getUserPoints() {
  return transaction(STORE_POINTS, "readonly", (store) => store.getAll());
}

export async function addUserPoints(features) {
  return transaction(STORE_POINTS, "readwrite", (store) => {
    for (const f of features) store.put(f);
  });
}

export async function deleteUserPoint(id) {
  return transaction(STORE_POINTS, "readwrite", (store) => store.delete(id));
}

export async function clearUserPoints() {
  return transaction(STORE_POINTS, "readwrite", (store) => store.clear());
}

/* ------------------------------------------------------------------ */
/* Traces (GPX, KML…)                                                   */
/* ------------------------------------------------------------------ */

/** Renvoie toutes les traces : {id, name, color, visible, geojson, stats}. */
export async function getTracks() {
  return transaction(STORE_TRACKS, "readonly", (store) => store.getAll());
}

export async function addTrack(track) {
  return transaction(STORE_TRACKS, "readwrite", (store) => store.put(track));
}

/** Met à jour partiellement une trace (ex. visibilité). */
export async function updateTrack(id, patch) {
  const db = await ouvrirDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(STORE_TRACKS, "readwrite");
    const store = tx.objectStore(STORE_TRACKS);
    const req = store.get(id);
    req.onsuccess = () => {
      if (req.result) store.put({ ...req.result, ...patch });
    };
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteTrack(id) {
  return transaction(STORE_TRACKS, "readwrite", (store) => store.delete(id));
}

/* ------------------------------------------------------------------ */
/* Carnet : notes + photos datées par point                             */
/* ------------------------------------------------------------------ */

/** Entrées du carnet d'un point : [{id, date, text, photo}] (photo = dataURL). */
export async function getJournal(pointId) {
  const enr = await transaction(STORE_JOURNAL, "readonly", (store) => store.get(pointId));
  return enr ? enr.entries : [];
}

/** Tout le carnet, pour l'export : { pointId: [entrées] } */
export async function getAllJournals() {
  const tous = await transaction(STORE_JOURNAL, "readonly", (store) => store.getAll());
  return Object.fromEntries(tous.map((e) => [e.pointId, e.entries]));
}

export async function addJournalEntry(pointId, entry) {
  const entries = await getJournal(pointId);
  entries.push(entry);
  await transaction(STORE_JOURNAL, "readwrite", (store) => store.put({ pointId, entries }));
  return entries;
}

export async function deleteJournalEntry(pointId, entryId) {
  const entries = (await getJournal(pointId)).filter((e) => e.id !== entryId);
  await transaction(STORE_JOURNAL, "readwrite", (store) =>
    entries.length ? store.put({ pointId, entries }) : store.delete(pointId)
  );
  return entries;
}

/** Modifie une entrée du carnet d'un point (ex. corriger le texte d'une note
 *  ou retirer sa photo) — fusionne `patch` dans l'entrée d'id `entryId`. */
export async function updateJournalEntry(pointId, entryId, patch) {
  const entries = (await getJournal(pointId)).map((e) =>
    e.id === entryId ? { ...e, ...patch } : e
  );
  await transaction(STORE_JOURNAL, "readwrite", (store) => store.put({ pointId, entries }));
  return entries;
}

/** Supprime tout le carnet d'un point (quand le point lui-même est supprimé). */
export async function deleteJournal(pointId) {
  return transaction(STORE_JOURNAL, "readwrite", (store) => store.delete(pointId));
}

/* ------------------------------------------------------------------ */
/* Thème du carnet : prédéfini ou personnalisé (photos en dataURL)      */
/* ------------------------------------------------------------------ */

/** Réglage du carnet : { theme: "grimoire"|"voyage"|"nuit"|"perso",
 *  couverture: dataURL|null, page: dataURL|null } — ou undefined. */
export async function getCarnetTheme() {
  return transaction(STORE_CARNET, "readonly", (store) => store.get("theme"));
}

export async function saveCarnetTheme(reglage) {
  return transaction(STORE_CARNET, "readwrite", (store) =>
    store.put({ cle: "theme", ...reglage })
  );
}

/** Fusionne un carnet importé (sauvegarde) avec l'existant, sans doublons d'id. */
export async function mergeJournals(journaux) {
  for (const [pointId, entries] of Object.entries(journaux || {})) {
    const existantes = await getJournal(pointId);
    const ids = new Set(existantes.map((e) => e.id));
    const fusion = [...existantes, ...entries.filter((e) => !ids.has(e.id))];
    await transaction(STORE_JOURNAL, "readwrite", (store) =>
      store.put({ pointId, entries: fusion })
    );
  }
}
