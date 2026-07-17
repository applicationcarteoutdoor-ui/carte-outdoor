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
import {
  allPacks,
  getPack,
  getDefaultPack,
  setPackOverrides,
  setOrdrePacks,
  isCustomPack,
  packExists,
  PACK_MES_CATEGORIES,
} from "./config/packs.js";
import { paysActuel } from "./config/pays.js";
import * as storage from "./storage.js";
import { renderTracksInto, tracksCount } from "./gpx.js";
import { esc } from "./util.js";

let panel = null;
let cb = {}; // {onToggleTheme, onToggleGr, onToggleTraces, onThemesChanged, onPacksChanged, onSidebarViewChange}
let etatCourant = null; // dernier état reçu de app.js (pour re-rendre)
let editionEnCours = null;
let tracesDepliees = false;
// Navigation de la sidebar (v72) : accueil des packs, pack ouvert, ou liste
// complète (l'ancien affichage). Restaurée depuis les prefs par app.js.
let vueSidebar = { mode: "packs", packOuvert: null };
let editionPack = null; // id du pack en édition, "nouveau" pour la création

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

/** Catégories visibles dans le pays courant : la liste `categories` du pays
 *  filtre les catégories de base (null = toutes) ; les catégories PERSONNELLES
 *  et celles qui contiennent des points de l'utilisateur restent visibles. */
function categoriesVisibles(etat) {
  const pays = paysActuel();
  const catPays = pays.categories;
  const exclues = pays.categoriesExclues || [];
  return allThemes().filter((def) => {
    if (isCustomTheme(def.id) || (etat.userPointCounts?.get(def.id) || 0) > 0) return true;
    if (exclues.includes(def.id)) return false;
    return !catPays || catPays.includes(def.id);
  });
}

/** Contenu du pack VIRTUEL « Mes catégories » : perso/importées + celles où
 *  l'utilisateur a des points + « autre » (ids, dans l'ordre d'allThemes). */
function categoriesMiennes(etat) {
  const ids = allThemes()
    .filter((def) => isCustomTheme(def.id) || (etat.userPointCounts?.get(def.id) || 0) > 0)
    .map((def) => def.id);
  if (etat.counts.get(FALLBACK_THEME.id) > 0) ids.push(FALLBACK_THEME.id);
  return ids;
}

/** Ouvre un pack (aussi utilisé par le tuto et les liens #pack=). */
export function ouvrirPack(packId) {
  if (!packExists(packId)) return;
  vueSidebar = { mode: "packs", packOuvert: packId };
  editionPack = null;
  if (etatCourant) renderSidebar(etatCourant);
  cb.onSidebarViewChange?.(vueSidebar);
}

/** Revient à l'accueil des packs (tuto, fin d'édition). */
export function retourAccueilPacks() {
  vueSidebar = { mode: "packs", packOuvert: null };
  editionPack = null;
  if (etatCourant) renderSidebar(etatCourant);
  cb.onSidebarViewChange?.(vueSidebar);
}

/** Restaure la navigation depuis les prefs (appelée par app.js au boot). */
export function setSidebarVue(vue) {
  if (vue && (vue.mode === "packs" || vue.mode === "liste")) {
    vueSidebar = {
      mode: vue.mode,
      packOuvert: vue.packOuvert && packExists(vue.packOuvert) ? vue.packOuvert : null,
    };
  }
}

/**
 * (Re)dessine la liste des catégories.
 * @param {object} etat {counts: Map, activeThemes: Set, statusFilters: Set,
 *                       statusCounts: {a-faire, fait, favori}, grVisible, tracesVisible}
 */
export function renderSidebar(etat) {
  etatCourant = etat;
  const liste = panel.querySelector(".cat-list");
  liste.textContent = "";

  // --- Aiguillage des 3 vues (v72) ---------------------------------------
  if (vueSidebar.mode === "packs" && vueSidebar.packOuvert) {
    renderPackOuvert(liste, etat, vueSidebar.packOuvert);
    return; // Suivi/Tracés vivent sur l'accueil — le retour est à 1 tap
  }
  if (vueSidebar.mode === "packs") {
    renderAccueilPacks(liste, etat);
  } else {
    renderListeComplete(liste, etat);
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
/* Vues packs (v72)                                                     */
/* ------------------------------------------------------------------ */

/** Ligne cochable d'une catégorie par son id (partagée par les 3 vues). */
function ligneDeTheme(liste, etat, id) {
  const estAutre = id === FALLBACK_THEME.id;
  const theme = estAutre ? FALLBACK_THEME : getTheme(id);
  const nbMiens = etat.userPointCounts?.get(id) || 0;
  liste.appendChild(
    ligneCategorie({
      icone: theme.icon,
      couleur: theme.color,
      texte: theme.textColor || "#fff",
      label: theme.label,
      count: etat.counts.get(id) || 0,
      coche: etat.activeThemes.has(id),
      onCheck: (on) => cb.onToggleTheme(id, on),
      locate: nbMiens,
      onLocate: nbMiens ? () => cb.onLocateUserPoint?.(id) : null,
      ...(estAutre ? {} : {
        onEdit: () => {
          editionEnCours = editionEnCours === id ? null : id;
          renderSidebar(etatCourant);
        },
        editeur: editionEnCours === id ? id : null,
      }),
    })
  );
}

/** Vue « liste complète » : l'affichage historique, filet de migration. */
function renderListeComplete(liste, etat) {
  const retour = document.createElement("button");
  retour.type = "button";
  retour.className = "pack-retour";
  retour.innerHTML = "← Retour aux packs";
  retour.addEventListener("click", retourAccueilPacks);
  liste.appendChild(retour);
  for (const def of categoriesVisibles(etat)) ligneDeTheme(liste, etat, def.id);
  if (etat.counts.get(FALLBACK_THEME.id) > 0) ligneDeTheme(liste, etat, FALLBACK_THEME.id);
}

/** Catégories d'un pack RÉELLEMENT affichables dans le pays courant. */
function categoriesDuPack(packId, etat) {
  const ids = packId === PACK_MES_CATEGORIES.id
    ? categoriesMiennes(etat)
    : (getPack(packId)?.categories || []);
  const visibles = new Set(categoriesVisibles(etat).map((d) => d.id));
  if (etat.counts.get(FALLBACK_THEME.id) > 0) visibles.add(FALLBACK_THEME.id);
  return ids.filter((id) => visibles.has(id));
}

let modeOrganiser = false; // ↕ : réordonner les TUILES de packs

/** Vue « accueil » : la grille des tuiles de packs.
 *  CLIC sur la tuile = afficher/masquer TOUT le pack (les couches volumineuses
 *  restent à cocher individuellement — dialogue oblige) ; ▸ = entrer dedans. */
function renderAccueilPacks(liste, etat) {
  const grille = document.createElement("div");
  grille.className = "pack-grid";
  const idsAffiches = [...allPacks().map((p) => p.id), PACK_MES_CATEGORIES.id];
  for (const packId of idsAffiches) {
    const cats = categoriesDuPack(packId, etat);
    if (!cats.length) continue; // pack vide dans ce pays : masqué
    const pack = packId === PACK_MES_CATEGORIES.id ? PACK_MES_CATEGORIES : getPack(packId);
    let total = 0;
    let charge = true;
    for (const id of cats) {
      const c = etat.counts.get(id) || 0;
      if (c === "…") charge = false;
      else total += c;
    }
    const nbCochees = cats.filter((id) => etat.activeThemes.has(id)).length;
    const tuile = document.createElement("div");
    tuile.className = "pack-tuile" + (nbCochees ? " pack-actif" : "");
    tuile.style.setProperty("--pack-color", pack.color);
    tuile.innerHTML = `
      <button type="button" class="pack-corps" title="${nbCochees ? "Masquer" : "Afficher"} tout le pack">
        <span class="pack-ico" aria-hidden="true">${esc(pack.icon)}</span>
        <span class="pack-nom">${esc(pack.label)}</span>
        <span class="pack-compte">${charge ? total.toLocaleString("fr-FR") + " lieux"
          : total ? total.toLocaleString("fr-FR") + "+ lieux" : "… lieux"}</span>
      </button>
      ${nbCochees ? `<span class="pack-cochees" title="${nbCochees} catégorie(s) affichée(s)">${nbCochees} ✓</span>` : ""}
      ${modeOrganiser
        ? `<span class="pack-ordre">
             <button type="button" class="btn-icon pack-monter" title="Monter">▲</button>
             <button type="button" class="btn-icon pack-descendre" title="Descendre">▼</button>
           </span>`
        : `<button type="button" class="btn-icon pack-ouvrir" title="Voir les catégories du pack" aria-label="Voir les catégories de ${esc(pack.label)}">▸</button>`}`;
    // clic = tout afficher / tout masquer (bascule)
    tuile.querySelector(".pack-corps").addEventListener("click", () =>
      cb.onTogglePack?.(cats, nbCochees === 0));
    tuile.querySelector(".pack-ouvrir")?.addEventListener("click", () => ouvrirPack(packId));
    tuile.querySelector(".pack-monter")?.addEventListener("click", () => bougerPack(packId, -1));
    tuile.querySelector(".pack-descendre")?.addEventListener("click", () => bougerPack(packId, 1));
    grille.appendChild(tuile);
  }
  liste.appendChild(grille);

  // Actions sous la grille : liste complète, création, organisation
  const actions = document.createElement("div");
  actions.className = "pack-actions";
  actions.innerHTML = `
    <button type="button" class="pack-action pack-tout">☰ Toutes les catégories</button>
    <button type="button" class="pack-action pack-creer">＋ Créer un pack</button>
    <button type="button" class="pack-action pack-organiser${modeOrganiser ? " actif" : ""}">${modeOrganiser ? "✓ Terminé" : "↕ Organiser"}</button>`;
  actions.querySelector(".pack-tout").addEventListener("click", () => {
    vueSidebar = { mode: "liste", packOuvert: null };
    renderSidebar(etatCourant);
    cb.onSidebarViewChange?.(vueSidebar);
  });
  actions.querySelector(".pack-creer").addEventListener("click", () => {
    editionPack = "nouveau";
    renderSidebar(etatCourant);
  });
  actions.querySelector(".pack-organiser").addEventListener("click", () => {
    modeOrganiser = !modeOrganiser;
    renderSidebar(etatCourant);
  });
  liste.appendChild(actions);

  if (editionPack === "nouveau") {
    const zone = document.createElement("div");
    zone.className = "group-editor pack-editor";
    liste.appendChild(zone);
    renderEditeurPack(zone, null, etat);
  }
}

/** Déplace une tuile dans l'ordre des packs (mode ↕ Organiser). */
function bougerPack(packId, sens) {
  const ids = allPacks().map((p) => p.id);
  const i = ids.indexOf(packId);
  const j = i + sens;
  if (i < 0 || j < 0 || j >= ids.length) return;
  [ids[i], ids[j]] = [ids[j], ids[i]];
  setOrdrePacks(ids);
  renderSidebar(etatCourant);
  cb.onOrdrePacks?.(ids);
}

/** Vue « pack ouvert » : en-tête ← + les catégories du pack. */
function renderPackOuvert(liste, etat, packId) {
  const cats = categoriesDuPack(packId, etat);
  const pack = packId === PACK_MES_CATEGORIES.id ? PACK_MES_CATEGORIES : getPack(packId);
  if (!pack || (!cats.length && packId !== PACK_MES_CATEGORIES.id)) {
    retourAccueilPacks(); // pack supprimé/vidé entre-temps
    return;
  }
  const entete = document.createElement("div");
  entete.className = "pack-header";
  entete.innerHTML = `
    <button type="button" class="btn-icon pack-back" title="Retour aux packs" aria-label="Retour aux packs">←</button>
    <span class="pack-ico" aria-hidden="true">${esc(pack.icon)}</span>
    <span class="pack-titre">${esc(pack.label)}</span>
    ${packId !== PACK_MES_CATEGORIES.id
      ? `<button type="button" class="btn-icon pack-edit" title="Personnaliser ce pack">✎</button>` : ""}`;
  entete.querySelector(".pack-back").addEventListener("click", retourAccueilPacks);
  entete.querySelector(".pack-edit")?.addEventListener("click", () => {
    editionPack = editionPack === packId ? null : packId;
    renderSidebar(etatCourant);
  });
  liste.appendChild(entete);

  if (editionPack === packId) {
    const zone = document.createElement("div");
    zone.className = "group-editor pack-editor";
    liste.appendChild(zone);
    renderEditeurPack(zone, packId, etat);
    return; // l'éditeur remplace la liste (place aux cases + ▲▼)
  }
  for (const id of cats) ligneDeTheme(liste, etat, id);
}

/* ------------------------------------------------------------------ */
/* Éditeur de pack (nom, icône, couleur, catégories + ordre)            */
/* ------------------------------------------------------------------ */

function renderEditeurPack(zone, packId, etat) {
  const creation = packId === null;
  const pack = creation
    ? { label: "", icon: "🧭", color: "#2d6a4f", categories: [] }
    : getPack(packId);
  // Les catégories s'affichent dans l'ordre STANDARD de l'application —
  // l'utilisateur choisit LESQUELLES, pas leur ordre (retour v73 : l'ordre,
  // c'est pour les tuiles de packs, bouton ↕ Organiser de l'accueil).
  const visibles = categoriesVisibles(etat).map((d) => d.id);
  const cochees = new Set((pack.categories || []).filter((id) => visibles.includes(id)));

  const lignesHtml = () => visibles.map((id) => {
    const t = getTheme(id);
    return `
      <div class="pack-cat-ligne" data-id="${esc(id)}">
        <label><input type="checkbox" ${cochees.has(id) ? "checked" : ""}>
          <span class="group-icon" style="--pin-color:${t.color};--pin-text:${t.textColor}" aria-hidden="true">${t.icon}</span>
          ${esc(t.label)}</label>
      </div>`;
  }).join("");

  zone.innerHTML = `
    <label>Nom du pack <input type="text" class="edit-label" value="${esc(pack.label)}" maxlength="30" placeholder="Mon pack"></label>
    <label>Icône (emoji) <input type="text" class="edit-icon" value="${esc(pack.icon)}" maxlength="4"></label>
    <label>Couleur <input type="color" class="edit-color" value="${pack.color}"></label>
    <p class="editor-note">Cochez les catégories à inclure dans ce pack.</p>
    <div class="pack-cats">${lignesHtml()}</div>
    <div class="editor-actions">
      ${!creation && isCustomPack(packId)
        ? '<button type="button" class="btn btn-danger edit-delete">🗑 Supprimer</button>' : ""}
      ${!creation && !isCustomPack(packId)
        ? '<button type="button" class="btn btn-secondary edit-reset">Réinitialiser</button>' : ""}
      <button type="button" class="btn btn-secondary edit-annuler">Annuler</button>
      <button type="button" class="btn edit-save">Enregistrer</button>
    </div>`;

  zone.querySelectorAll(".pack-cat-ligne input").forEach((input) => {
    const id = input.closest(".pack-cat-ligne").dataset.id;
    input.addEventListener("change", (e) => {
      e.target.checked ? cochees.add(id) : cochees.delete(id);
    });
  });

  zone.querySelector(".edit-annuler").addEventListener("click", () => {
    editionPack = null;
    renderSidebar(etatCourant);
  });

  zone.querySelector(".edit-save").addEventListener("click", async () => {
    const label = zone.querySelector(".edit-label").value.trim() || "Mon pack";
    const icon = zone.querySelector(".edit-icon").value.trim() || "🧭";
    const color = zone.querySelector(".edit-color").value;
    const categories = visibles.filter((id) => cochees.has(id));
    if (!categories.length) return; // un pack vide n'a pas de sens
    if (creation || isCustomPack(packId)) {
      const packs = await storage.getCustomPacks();
      if (creation) {
        packs.push({ id: `pack-perso-${Date.now().toString(36)}`, label, icon, color, categories });
        // la tuile naît en fin de grille : ↕ Organiser la place où on veut
        cb.onToast?.(`Pack « ${label} » créé — placez sa tuile avec ↕ Organiser.`);
      } else {
        const p = packs.find((x) => x.id === packId);
        if (p) Object.assign(p, { label, icon, color, categories });
      }
      await storage.saveCustomPacks(packs);
    } else {
      // pack par défaut : la personnalisation (contenu inclus) vit en override
      const overrides = await storage.getPackOverrides();
      const defaut = getDefaultPack(packId);
      const o = {};
      if (label !== defaut.label) o.label = label;
      if (icon !== defaut.icon) o.icon = icon;
      if (color !== defaut.color) o.color = color;
      if (JSON.stringify(categories) !== JSON.stringify(defaut.categories)) o.categories = categories;
      if (Object.keys(o).length) overrides[packId] = o;
      else delete overrides[packId];
      await storage.savePackOverrides(overrides);
    }
    editionPack = null;
    cb.onPacksChanged?.();
  });

  zone.querySelector(".edit-reset")?.addEventListener("click", async () => {
    const overrides = await storage.getPackOverrides();
    delete overrides[packId];
    await storage.savePackOverrides(overrides);
    editionPack = null;
    cb.onPacksChanged?.();
  });

  zone.querySelector(".edit-delete")?.addEventListener("click", async () => {
    const packs = (await storage.getCustomPacks()).filter((p) => p.id !== packId);
    await storage.saveCustomPacks(packs);
    editionPack = null;
    vueSidebar = { mode: "packs", packOuvert: null };
    cb.onPacksChanged?.();
    cb.onSidebarViewChange?.(vueSidebar);
  });
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
