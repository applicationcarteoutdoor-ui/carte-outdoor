/**
 * Panneau de filtres (à droite de la carte).
 *
 * Dès qu'une catégorie cochée possède des filtres (déclarés dans
 * js/config/themes.js), ils apparaissent ici : le nom du filtre au-dessus,
 * puis des pastilles cliquables. Par défaut aucune pastille n'est
 * sélectionnée = « Tout » (aucun filtrage). Les pastilles dont la valeur
 * figure au glossaire (cotations F, PD, AD…) ont une infobulle au survol.
 *
 * S'y ajoute le filtre global de suivi (tous / à faire / faits / favoris).
 */

import { THEMES, getTheme } from "./config/themes.js";
import { definir } from "./config/glossaire.js";
import { esc } from "./util.js";

let panel = null;
let boutonReouvrir = null;
let cb = {}; // {onFilterToggle, onFilterReset, onCollapse}

export function initFilters(callbacks) {
  cb = callbacks;
  panel = document.getElementById("filter-panel");
  boutonReouvrir = document.getElementById("btn-filters-reopen");

  panel.querySelector(".panel-close").addEventListener("click", () => cb.onCollapse(true));
  boutonReouvrir.addEventListener("click", () => cb.onCollapse(false));
}

/**
 * Met à jour le panneau.
 * @param {object} etat {activeThemes: Set, filterSelections, collapsed, statusActif}
 */
export function renderFilters(etat) {
  // Groupes de filtres des catégories cochées
  const zone = panel.querySelector(".filter-groups");
  zone.textContent = "";
  const themesAvecFiltres = THEMES.filter(
    (t) => etat.activeThemes.has(t.id) && t.filters.length
  );

  for (const def of themesAvecFiltres) {
    const theme = getTheme(def.id);
    const section = document.createElement("section");
    section.className = "filter-cat";
    section.innerHTML = `
      <h3><span class="group-icon" style="--pin-color:${theme.color};--pin-text:${theme.textColor}"
        aria-hidden="true">${theme.icon}</span> ${esc(theme.label)}</h3>`;

    for (const filtre of def.filters) {
      const selection = etat.filterSelections[def.id]?.[filtre.key] || new Set();
      const groupe = document.createElement("div");
      groupe.className = "filter-group";
      groupe.innerHTML = `<h4>${esc(filtre.label)}</h4><div class="filter-options" role="group" aria-label="${esc(filtre.label)}"></div>`;
      const options = groupe.querySelector(".filter-options");

      // Pastille « Tout » : efface la sélection du filtre
      const tout = document.createElement("button");
      tout.type = "button";
      tout.className = "chip chip-mini" + (selection.size === 0 ? " chip-active" : "");
      tout.textContent = "Tout";
      tout.addEventListener("click", () => cb.onFilterReset(def.id, filtre.key));
      options.appendChild(tout);

      for (const opt of filtre.options) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "chip chip-mini" + (selection.has(opt.value) ? " chip-active" : "");
        chip.style.setProperty("--chip-color", theme.color);
        chip.style.setProperty("--chip-text", theme.textColor);
        chip.innerHTML =
          (opt.icon ? `<span aria-hidden="true">${opt.icon}</span>` : "") +
          esc(opt.label || opt.value);
        const definition = definir(opt.value);
        if (definition) {
          chip.classList.add("glossary-term");
          chip.dataset.tip = definition;
        }
        chip.addEventListener("click", () => cb.onFilterToggle(def.id, filtre.key, opt.value));
        options.appendChild(chip);
      }
      section.appendChild(groupe);
    }
    zone.appendChild(section);
  }

  // Visibilité : panneau affiché s'il y a quelque chose à filtrer
  const utile = themesAvecFiltres.length > 0;
  panel.classList.toggle("open", utile && !etat.collapsed);
  boutonReouvrir.hidden = !(utile && etat.collapsed);

  const filtresActifs =
    etat.statusActif ||
    Object.values(etat.filterSelections).some((filtres) =>
      Object.values(filtres).some((sel) => sel.size > 0)
    );
  boutonReouvrir.classList.toggle("has-dot", filtresActifs);
}
