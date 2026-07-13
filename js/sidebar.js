/**
 * Panneau latéral gauche : la liste COCHABLE des catégories.
 *
 * - Chaque catégorie a une case à cocher : on peut en afficher plusieurs à
 *   la fois sur la carte. Le bouton ✎ ouvre l'éditeur (nom, couleurs, icône —
 *   l'identifiant technique reste stable, voir js/config/themes.js).
 * - Les sentiers GR et les traces GPX importées apparaissent au même niveau
 *   que les autres catégories : une case pour les afficher/masquer, et pour
 *   les traces un volet dépliable (liste, profil altimétrique, import GPX).
 * - En bas : « Importer une catégorie » (GeoJSON, CSV, KML, KMZ).
 *
 * Persistant sur grand écran, en tiroir (slide-in) sur mobile.
 */

import {
  allThemes,
  getTheme,
  getDefaultTheme,
  setThemeOverrides,
  isCustomTheme,
  FALLBACK_THEME,
} from "./config/themes.js";
import { paysActuel } from "./config/pays.js";
import * as storage from "./storage.js";
import { renderTracksInto, tracksCount } from "./gpx.js";
import { esc } from "./util.js";

let panel = null;
let cb = {}; // {onToggleTheme, onToggleGr, onToggleTraces, onThemesChanged}
let etatCourant = null; // dernier état reçu de app.js (pour re-rendre)
let editionEnCours = null;
let tracesDepliees = false;

export function initSidebar(callbacks) {
  cb = callbacks;
  panel = document.getElementById("sidebar");

  document.getElementById("btn-sidebar").addEventListener("click", () => {
    panel.classList.toggle("open");
  });
  panel.querySelector(".panel-close").addEventListener("click", closeSidebar);
  document.getElementById("btn-import-category").addEventListener("click", () => {
    document.getElementById("file-import").click();
  });
}

export function closeSidebar() {
  panel.classList.remove("open");
}

const STATUTS = [
  { id: "a-faire", label: "À faire", icone: "★", couleur: "#e07b00" },
  { id: "fait", label: "Fait", icone: "✓", couleur: "#2d8a39" },
  { id: "favori", label: "Favoris", icone: "♥", couleur: "#d6336c" },
];

/**
 * (Re)dessine la liste des catégories.
 * @param {object} etat {counts: Map, activeThemes: Set, statusFilters: Set,
 *                       statusCounts: {a-faire, fait, favori}, grVisible, tracesVisible}
 */
export function renderSidebar(etat) {
  etatCourant = etat;
  const liste = panel.querySelector(".cat-list");
  liste.textContent = "";

  // Catégories du PAYS courant : la liste `categories` du pays filtre les
  // catégories de base (null = toutes) ; les catégories PERSONNELLES et celles
  // qui contiennent des points de l'utilisateur restent toujours visibles.
  const pays = paysActuel();
  const catPays = pays.categories;
  const exclues = pays.categoriesExclues || [];
  const visibles = allThemes().filter((def) => {
    // Toujours visibles : catégories perso, et celles où l'utilisateur a des points
    if (isCustomTheme(def.id) || (etat.userPointCounts?.get(def.id) || 0) > 0) return true;
    if (exclues.includes(def.id)) return false;
    return !catPays || catPays.includes(def.id);
  });
  for (const def of visibles) {
    const theme = getTheme(def.id);
    const count = etat.counts.get(def.id) || 0;
    const nbMiens = etat.userPointCounts?.get(def.id) || 0;
    liste.appendChild(
      ligneCategorie({
        icone: theme.icon,
        couleur: theme.color,
        texte: theme.textColor,
        label: theme.label,
        count,
        coche: etat.activeThemes.has(def.id),
        onCheck: (on) => cb.onToggleTheme(def.id, on),
        // Flèche ➤ visible seulement si la catégorie contient des points
        // ajoutés par l'utilisateur (comme le zoom des traces GPX)
        locate: nbMiens,
        onLocate: nbMiens ? () => cb.onLocateUserPoint?.(def.id) : null,
        onEdit: () => {
          editionEnCours = editionEnCours === def.id ? null : def.id;
          renderSidebar(etatCourant);
        },
        editeur: editionEnCours === def.id ? def.id : null,
      })
    );
  }

  // --- « Autre » : points dont la catégorie n'existe plus (imports, suppressions) ---
  if (etat.counts.get(FALLBACK_THEME.id) > 0) {
    const nbMiens = etat.userPointCounts?.get(FALLBACK_THEME.id) || 0;
    liste.appendChild(
      ligneCategorie({
        icone: FALLBACK_THEME.icon,
        couleur: FALLBACK_THEME.color,
        texte: "#fff",
        label: FALLBACK_THEME.label,
        count: etat.counts.get(FALLBACK_THEME.id),
        coche: etat.activeThemes.has(FALLBACK_THEME.id),
        onCheck: (on) => cb.onToggleTheme(FALLBACK_THEME.id, on),
        locate: nbMiens,
        onLocate: nbMiens ? () => cb.onLocateUserPoint?.(FALLBACK_THEME.id) : null,
      })
    );
  }

  // --- Suivi : Fait / Favoris / À faire, cochables comme des catégories ---
  const sep = document.createElement("div");
  sep.className = "cat-separator";
  sep.textContent = "Suivi";
  liste.appendChild(sep);
  for (const statut of STATUTS) {
    liste.appendChild(
      ligneCategorie({
        icone: statut.icone,
        couleur: statut.couleur,
        texte: "#fff",
        label: statut.label,
        count: etat.statusCounts[statut.id] || 0,
        coche: etat.statusFilters.has(statut.id),
        onCheck: (on) => cb.onToggleStatus(statut.id, on),
      })
    );
  }

  const sep2 = document.createElement("div");
  sep2.className = "cat-separator";
  sep2.textContent = "Tracés";
  liste.appendChild(sep2);

  // --- Grands itinéraires (surcouche de tracés, cochable comme une catégorie)
  //     Par pays : « Sentiers GR » en France, « Great Walks » en NZ — libellé
  //     et compte viennent de js/config/pays.js (à tenir en phase avec le fichier).
  const gr = paysActuel().gr;
  if (gr) {
    liste.appendChild(
      ligneCategorie({
        icone: "🥾",
        couleur: "#b02a2a",
        texte: "#fff",
        label: gr.label,
        count: gr.compte,
        coche: etat.grVisible,
        onCheck: (on) => cb.onToggleGr(on),
      })
    );
  }

  // --- Traces GPX importées ---
  const ligneTraces = ligneCategorie({
    icone: "〽️",
    couleur: "#3a86ff",
    texte: "#fff",
    label: "Mes traces GPX",
    count: tracksCount(),
    coche: etat.tracesVisible,
    onCheck: (on) => cb.onToggleTraces(on),
    chevron: tracesDepliees,
    onChevron: () => {
      tracesDepliees = !tracesDepliees;
      renderSidebar(etatCourant);
    },
  });
  liste.appendChild(ligneTraces);

  if (tracesDepliees) {
    const volet = document.createElement("div");
    volet.className = "traces-volet";
    volet.innerHTML = `
      <button type="button" class="btn btn-secondary tracks-add">＋ Importer des traces GPX</button>
      <div class="track-profile-area" style="display:none"></div>
      <div class="tracks-items"></div>`;
    volet.querySelector(".tracks-add").addEventListener("click", () => {
      document.getElementById("file-import").click();
    });
    liste.appendChild(volet);
    renderTracksInto(volet);
  }
}

/** Rafraîchit uniquement le volet des traces (après import/suppression). */
export function refreshTraces() {
  if (etatCourant) renderSidebar(etatCourant);
}

/* ------------------------------------------------------------------ */
/* Ligne de catégorie                                                   */
/* ------------------------------------------------------------------ */

function ligneCategorie({ icone, couleur, texte, label, count, coche, onCheck, onEdit, editeur, chevron, onChevron, locate, onLocate }) {
  const bloc = document.createElement("div");
  bloc.className = "cat-bloc";
  const row = document.createElement("div");
  row.className = "cat-row";
  row.innerHTML = `
    <label class="cat-check">
      <input type="checkbox" ${coche ? "checked" : ""}>
      <span class="group-icon" style="--pin-color:${couleur};--pin-text:${texte}" aria-hidden="true">${icone}</span>
      <span class="cat-label">${esc(label)}</span>
      <span class="group-count">${count}</span>
    </label>
    ${onLocate ? `<button type="button" class="btn-icon cat-locate" title="Retrouver mes points ajoutés (${locate})">➤</button>` : ""}
    ${onChevron ? `<button type="button" class="btn-icon cat-chevron" title="Voir les traces" aria-expanded="${!!chevron}">${chevron ? "▾" : "▸"}</button>` : ""}
    ${onEdit ? `<button type="button" class="btn-icon cat-edit" title="Personnaliser « ${esc(label)} »">✎</button>` : ""}
  `;
  row.querySelector("input").addEventListener("change", (e) => onCheck(e.target.checked));
  row.querySelector(".cat-edit")?.addEventListener("click", onEdit);
  row.querySelector(".cat-chevron")?.addEventListener("click", onChevron);
  row.querySelector(".cat-locate")?.addEventListener("click", onLocate);
  bloc.appendChild(row);

  if (editeur) {
    const zone = document.createElement("div");
    zone.className = "group-editor";
    bloc.appendChild(zone);
    renderEditeur(zone, editeur);
  }
  return bloc;
}

/* ------------------------------------------------------------------ */
/* Éditeur de catégorie (nom, couleurs, icône)                          */
/* ------------------------------------------------------------------ */

function renderEditeur(zone, themeId) {
  const theme = getTheme(themeId);
  zone.innerHTML = `
    <label>Nom affiché <input type="text" class="edit-label" value="${esc(theme.label)}" maxlength="40"></label>
    <label>Icône (emoji) <input type="text" class="edit-icon" value="${esc(theme.icon)}" maxlength="4"></label>
    <div class="editor-colors">
      <label>Fond <input type="color" class="edit-color" value="${theme.color}"></label>
      <label>Texte <input type="color" class="edit-text-color" value="${theme.textColor}"></label>
    </div>
    <p class="editor-preview">Aperçu :
      <span class="group-icon edit-preview-icon" aria-hidden="true"></span>
      <span class="chip chip-active edit-preview-chip"></span>
    </p>
    <p class="editor-note">L'identifiant technique « ${esc(themeId)} » ne change pas :
      les points restent rattachés même si vous renommez la catégorie.</p>
    <div class="editor-actions">
      ${isCustomTheme(themeId)
        ? '<button type="button" class="btn btn-danger edit-delete">🗑 Supprimer</button>'
        : ""}
      <button type="button" class="btn btn-secondary edit-reset">Réinitialiser</button>
      <button type="button" class="btn edit-save">Enregistrer</button>
    </div>
  `;

  const maj = () => {
    const couleur = zone.querySelector(".edit-color").value;
    const texte = zone.querySelector(".edit-text-color").value;
    const icone = zone.querySelector(".edit-icon").value || theme.icon;
    const label = zone.querySelector(".edit-label").value || theme.label;
    const apercuIcone = zone.querySelector(".edit-preview-icon");
    apercuIcone.style.setProperty("--pin-color", couleur);
    apercuIcone.style.setProperty("--pin-text", texte);
    apercuIcone.textContent = icone;
    const apercuChip = zone.querySelector(".edit-preview-chip");
    apercuChip.style.setProperty("--chip-color", couleur);
    apercuChip.style.setProperty("--chip-text", texte);
    apercuChip.textContent = `${icone} ${label}`;
  };
  zone.querySelectorAll("input").forEach((i) => i.addEventListener("input", maj));
  maj();

  zone.querySelector(".edit-save").addEventListener("click", async () => {
    const overrides = await storage.getThemeOverrides();
    const defaut = getDefaultTheme(themeId);
    const nouvelles = {
      label: zone.querySelector(".edit-label").value.trim(),
      icon: zone.querySelector(".edit-icon").value.trim(),
      color: zone.querySelector(".edit-color").value,
      textColor: zone.querySelector(".edit-text-color").value,
    };
    const utile = Object.fromEntries(
      Object.entries(nouvelles).filter(([cle, valeur]) => valeur && valeur !== defaut[cle])
    );
    if (Object.keys(utile).length) overrides[themeId] = utile;
    else delete overrides[themeId];
    await appliquer(overrides);
  });

  zone.querySelector(".edit-reset").addEventListener("click", async () => {
    const overrides = await storage.getThemeOverrides();
    delete overrides[themeId];
    await appliquer(overrides);
  });

  // Suppression : uniquement pour les catégories créées/importées par
  // l'utilisateur — jamais pour les catégories de base de l'application.
  zone.querySelector(".edit-delete")?.addEventListener("click", () => {
    editionEnCours = null;
    cb.onDeleteTheme?.(themeId);
  });

  async function appliquer(overrides) {
    await storage.saveThemeOverrides(overrides);
    setThemeOverrides(overrides);
    editionEnCours = null;
    cb.onThemesChanged?.();
  }
}
