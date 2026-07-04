/**
 * Ajout d'un point à la main.
 *
 * Le gros bouton « repère + » passe la carte en mode visée : un clic sur la
 * carte ouvre le formulaire (nom, catégorie, description). La catégorie peut
 * être choisie parmi les existantes ou créée à la volée — les catégories
 * personnalisées sont persistées (storage.js) et incluses dans l'export.
 */

import { allThemes, themeExists, registerCustomThemes, getTheme } from "./config/themes.js";
import * as storage from "./storage.js";
import { pickLocation } from "./map.js";
import { toast } from "./import-export.js";

let dialog = null;
let onPointAddedCallback = null;
let positionCourante = null;

export function initAddPoint({ onPointAdded }) {
  onPointAddedCallback = onPointAdded;
  dialog = document.getElementById("point-dialog");

  document.getElementById("btn-add-point").addEventListener("click", async () => {
    toast("Cliquez sur la carte à l'endroit du point (Échap pour annuler).");
    const position = await pickLocation();
    if (!position) return;
    positionCourante = position;
    ouvrirFormulaire();
  });

  dialog.querySelector(".point-cancel").addEventListener("click", () => dialog.close());
  dialog.querySelector(".point-theme").addEventListener("change", (e) => {
    dialog.querySelector(".point-newcat").hidden = e.target.value !== "__new__";
  });
  dialog.querySelector(".point-form").addEventListener("submit", valider);
}

function ouvrirFormulaire() {
  const select = dialog.querySelector(".point-theme");
  select.textContent = "";
  for (const t of allThemes()) {
    const theme = getTheme(t.id);
    select.appendChild(new Option(`${theme.icon} ${theme.label}`, t.id));
  }
  select.appendChild(new Option("➕ Nouvelle catégorie…", "__new__"));
  dialog.querySelector(".point-newcat").hidden = true;
  dialog.querySelector(".point-name").value = "";
  dialog.querySelector(".point-desc").value = "";
  dialog.querySelector(".point-coords").textContent =
    `📍 ${positionCourante.lat.toFixed(5)}, ${positionCourante.lng.toFixed(5)}`;
  dialog.showModal();
}

function idDepuisLabel(label) {
  const slug = label
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 24) || "categorie";
  let id = `perso-${slug}`;
  let n = 2;
  while (themeExists(id)) id = `perso-${slug}-${n++}`;
  return id;
}

async function valider(e) {
  e.preventDefault();
  const nom = dialog.querySelector(".point-name").value.trim();
  if (!nom || !positionCourante) return;

  let themeId = dialog.querySelector(".point-theme").value;
  if (themeId === "__new__") {
    const label = dialog.querySelector(".newcat-label").value.trim();
    if (!label) {
      dialog.querySelector(".newcat-label").focus();
      return;
    }
    const nouvelle = {
      id: idDepuisLabel(label),
      label,
      icon: dialog.querySelector(".newcat-icon").value.trim() || "📍",
      color: dialog.querySelector(".newcat-color").value,
      textColor: "#ffffff",
    };
    const customs = await storage.getCustomThemes();
    customs.push(nouvelle);
    await storage.saveCustomThemes(customs);
    registerCustomThemes(customs);
    themeId = nouvelle.id;
  }

  const feature = {
    type: "Feature",
    geometry: {
      type: "Point",
      coordinates: [
        Number(positionCourante.lng.toFixed(6)),
        Number(positionCourante.lat.toFixed(6)),
      ],
    },
    properties: {
      id: `pt-${Date.now().toString(36)}`,
      name: nom,
      theme: themeId,
      description: dialog.querySelector(".point-desc").value.trim(),
      link: "",
      links: [],
      photos: [],
      details: {},
    },
  };
  await storage.addUserPoints([feature]);
  dialog.close();
  toast(`Point « ${nom} » ajouté.`);
  onPointAddedCallback?.(feature);
}
