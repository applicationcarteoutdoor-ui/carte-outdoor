/**
 * Fiche détaillée d'un point : panneau latéral (desktop) / bottom-sheet (mobile).
 *
 * Affiche les champs communs, les champs spécifiques au thème, les liens vers
 * les fiches externes (ex. viaferrata-fr.net, refuges.info), les boutons
 * d'itinéraire Google Maps / Waze, les trois statuts de suivi et le carnet
 * personnel (notes + photos datées, redimensionnées avant stockage).
 */

import { getTheme } from "./config/themes.js";
import { glossaireHTML } from "./config/glossaire.js";
import { SUR_ANDROID, SUR_IOS } from "./config/platform.js";
import * as storage from "./storage.js";
import { confirmer } from "./import-export.js";

const PHOTO_MAX = 1024; // côté max (px) des photos stockées
const PHOTO_QUALITE = 0.8;

// Signalements : même adresse dédiée que la boîte à idées (app statique → mailto)
const EMAIL_SIGNALEMENT = "Applicationcarteoutdoor@gmail.com";
const KEY_SIGNALEMENTS = "carte-outdoor:signalements";

let panel = null;
let onStatusChangeCallback = null;
let onCloseCallback = null;
let isUserPointCallback = null;
let onDeletePointCallback = null;
let featureCourante = null;

function esc(texte) {
  const div = document.createElement("div");
  div.textContent = texte ?? "";
  return div.innerHTML;
}

export function initDetails({ onStatusChange, onClose, isUserPoint, onDeletePoint }) {
  onStatusChangeCallback = onStatusChange;
  onCloseCallback = onClose;
  isUserPointCallback = isUserPoint;
  onDeletePointCallback = onDeletePoint;
  panel = document.getElementById("details-panel");
  panel.querySelector(".panel-close").addEventListener("click", closeDetails);
  initSignalement();
}

/* ------------------------------------------------------------------ */
/* Signalement d'un point (ouvert/fermé, correction…) → e-mail          */
/* ------------------------------------------------------------------ */

function initSignalement() {
  const dlg = document.getElementById("report-dialog");
  dlg.querySelector(".report-cancel").addEventListener("click", () => dlg.close());
  dlg.querySelector(".report-form").addEventListener("submit", (e) => {
    e.preventDefault();
    if (!featureCourante) return dlg.close();
    const p = featureCourante.properties;
    const [lon, lat] = featureCourante.geometry.coordinates;
    const type = dlg.querySelector(".report-type").value;
    const texte = dlg.querySelector(".report-text").value.trim();
    // Trace locale (permet de retrouver ses signalements passés)
    try {
      const liste = JSON.parse(localStorage.getItem(KEY_SIGNALEMENTS)) || [];
      liste.push({ date: new Date().toISOString(), id: p.id, name: p.name, type, texte });
      localStorage.setItem(KEY_SIGNALEMENTS, JSON.stringify(liste));
    } catch {
      /* stockage indisponible : l'e-mail part quand même */
    }
    const corps =
      `Point : ${p.name}\n` +
      `Id : ${p.id} (catégorie ${p.theme})\n` +
      `Coordonnées : ${lat.toFixed(5)}, ${lon.toFixed(5)}\n` +
      `Signalement : ${type}\n` +
      (texte ? `Commentaire : ${texte}\n` : "");
    dlg.close();
    location.href =
      `mailto:${EMAIL_SIGNALEMENT}?subject=${encodeURIComponent(`[Carte Outdoor] Signalement : ${p.name}`)}` +
      `&body=${encodeURIComponent(corps)}`;
  });
}

export function closeDetails() {
  panel.classList.remove("open");
  featureCourante = null;
  onCloseCallback?.();
}

/** Ouvre (ou met à jour) la fiche du point donné. */
export function openDetails(feature, statut) {
  featureCourante = feature;
  const p = feature.properties;
  const theme = getTheme(p.theme);
  const [lon, lat] = feature.geometry.coordinates;
  const coords = `${lat.toFixed(5)}, ${lon.toFixed(5)}`;

  // --- Champs spécifiques au thème ---
  const details = p.details || {};
  // Les valeurs passent par le glossaire : les cotations (PD, AD, D…)
  // reçoivent une infobulle expliquant leur signification.
  const lignes = theme.fields
    .filter((champ) => details[champ.key] !== undefined && details[champ.key] !== "")
    .map(
      (champ) =>
        `<div class="detail-row"><dt>${esc(champ.label)}</dt><dd>${glossaireHTML(String(details[champ.key]))}</dd></div>`
    );
  // Champs non déclarés dans le thème : affichés aussi, SAUF les champs
  // techniques destinés aux filtres (suffixes _n et _type)
  const clesConnues = new Set(theme.fields.map((c) => c.key));
  for (const [cle, valeur] of Object.entries(details)) {
    if (
      !clesConnues.has(cle) &&
      valeur !== "" &&
      valeur !== undefined &&
      !cle.endsWith("_n") &&
      !cle.endsWith("_type")
    ) {
      lignes.push(`<div class="detail-row"><dt>${esc(cle)}</dt><dd>${glossaireHTML(String(valeur))}</dd></div>`);
    }
  }

  // --- Liens externes : lien principal + liste de fiches (via ferrata multi-parcours) ---
  let liens = "";
  if (p.link) {
    liens += `<a href="${esc(p.link)}" target="_blank" rel="noopener">🔗 ${esc(nomDeSite(p.link))}</a>`;
  }
  for (const l of p.links || []) {
    liens += `<a href="${esc(l.url)}" target="_blank" rel="noopener">🔗 ${esc(l.label)}</a>`;
  }

  const photos = (p.photos || [])
    .map((url) => `<a href="${esc(url)}" target="_blank" rel="noopener"><img src="${esc(url)}" alt="Photo de ${esc(p.name)}" loading="lazy"></a>`)
    .join("");

  panel.querySelector(".panel-body").innerHTML = `
    <div class="details-theme" style="--pin-color:${theme.color};--pin-text:${theme.textColor}">
      <span aria-hidden="true">${theme.icon}</span> ${esc(theme.label)}
    </div>
    <h2 class="details-name">${esc(p.name)}</h2>

    <div class="details-status" role="group" aria-label="Suivi du point">
      <button type="button" class="btn-status" data-statut="a-faire"
        aria-pressed="${statut === "a-faire"}">★ À faire</button>
      <button type="button" class="btn-status" data-statut="fait"
        aria-pressed="${statut === "fait"}">✓ Fait</button>
      <button type="button" class="btn-status" data-statut="favori"
        aria-pressed="${statut === "favori"}">♥ Favori</button>
    </div>

    <div class="details-route">
      ${lienItineraireMaps(lat, lon)}
      ${lienItineraireWaze(lat, lon)}
    </div>

    ${p.description ? `<p class="details-description">${glossaireHTML(p.description).replaceAll("\n", "<br>")}</p>` : ""}

    ${lignes.length ? `<dl class="details-fields">${lignes.join("")}</dl>` : ""}

    ${liens ? `<div class="details-links">${liens}</div>` : ""}

    ${photos ? `<div class="details-photos">${photos}</div>` : ""}

    <p class="details-coords">
      <span>📍 ${coords}</span>
      <button type="button" class="btn-copy" title="Copier les coordonnées">Copier</button>
    </p>

    <section class="carnet" aria-label="Mon carnet">
      <h3>📔 Mon carnet</h3>
      <div class="carnet-entries"></div>
      <form class="carnet-form">
        <textarea rows="2" placeholder="Une note, un souvenir… (date ajoutée automatiquement)"></textarea>
        <div class="carnet-form-actions">
          <label class="btn btn-secondary carnet-photo-label">
            📷 Photo<input type="file" accept="image/*" hidden>
          </label>
          <span class="carnet-photo-nom"></span>
          <button type="submit" class="btn">Ajouter</button>
        </div>
      </form>
    </section>

    <button type="button" class="btn btn-secondary btn-report">📢 Signaler / corriger ce point</button>
    ${isUserPointCallback?.(p.id)
      ? '<button type="button" class="btn btn-danger btn-delete-point">🗑 Supprimer ce point</button>'
      : ""}
  `;

  // Statuts : re-cliquer sur le statut actif le retire
  panel.querySelectorAll(".btn-status").forEach((btn) => {
    btn.addEventListener("click", () => {
      const demande = btn.dataset.statut;
      onStatusChangeCallback?.(feature.properties.id, demande === statut ? null : demande);
    });
  });

  // iOS : si l'appli (Maps/Waze) n'est pas installée, son schéma ne fait
  // rien — repli vers le site web si la page est toujours visible après 1,6 s
  // (si l'appli s'est ouverte, la page est passée en arrière-plan).
  panel.querySelectorAll(".btn-route[data-fallback]").forEach((a) => {
    a.addEventListener("click", () => {
      const secours = a.dataset.fallback;
      setTimeout(() => {
        if (!document.hidden) location.href = secours;
      }, 1600);
    });
  });

  // Copie des coordonnées
  panel.querySelector(".btn-copy").addEventListener("click", async (e) => {
    try {
      await navigator.clipboard.writeText(coords);
      e.target.textContent = "Copié ✓";
      setTimeout(() => (e.target.textContent = "Copier"), 1500);
    } catch {
      e.target.textContent = coords;
    }
  });

  // Suppression du point : uniquement pour les points ajoutés/importés par
  // l'utilisateur (les données par défaut ne sont pas supprimables une à une).
  panel.querySelector(".btn-delete-point")?.addEventListener("click", () => {
    onDeletePointCallback?.(feature);
  });

  // Signalement (tous les points) : ouvre le dialogue pré-rempli
  panel.querySelector(".btn-report").addEventListener("click", () => {
    const dlg = document.getElementById("report-dialog");
    dlg.querySelector(".report-point").textContent = `${theme.icon} ${p.name}`;
    dlg.querySelector(".report-text").value = "";
    dlg.showModal();
  });

  initCarnet(feature.properties.id);

  panel.classList.add("open");
  panel.querySelector(".panel-body").scrollTop = 0;
}

/** Si la fiche du point donné est ouverte, la re-rend avec le nouveau statut. */
export function refreshDetailsIfOpen(pointId, statut) {
  if (featureCourante && featureCourante.properties.id === pointId) {
    openDetails(featureCourante, statut);
  }
}

/** Id du point dont la fiche est ouverte, ou null. */
export function getOpenPointId() {
  return featureCourante ? featureCourante.properties.id : null;
}

/* ------------------------------------------------------------------ */
/* Itinéraire : sur téléphone, ouvrir l'APPLI Maps/Waze plutôt que le site */
/* ------------------------------------------------------------------ */

/**
 * Bouton <a> d'itinéraire selon la plateforme :
 *  - Android : URL intent — ouvre l'appli visée, avec repli vers le site
 *    web intégré à l'URL si elle n'est pas installée ;
 *  - iOS : schéma d'appli (comgooglemaps://, waze://) — pas de repli natif,
 *    d'où le data-fallback exploité par une minuterie (voir openDetails) ;
 *  - ailleurs (ordinateur) : le site web dans un nouvel onglet.
 */
function boutonItineraire(label, { web, android, ios }) {
  if (SUR_ANDROID) return `<a class="btn btn-route" href="${esc(android)}">${label}</a>`;
  if (SUR_IOS) return `<a class="btn btn-route" href="${esc(ios)}" data-fallback="${esc(web)}">${label}</a>`;
  return `<a class="btn btn-route" target="_blank" rel="noopener" href="${esc(web)}">${label}</a>`;
}

function lienItineraireMaps(lat, lon) {
  const web = `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
  return boutonItineraire("🗺️ Google Maps", {
    web,
    android:
      `intent://www.google.com/maps/dir/?api=1&destination=${lat},${lon}` +
      `#Intent;scheme=https;package=com.google.android.apps.maps;S.browser_fallback_url=${encodeURIComponent(web)};end`,
    ios: `comgooglemaps://?daddr=${lat},${lon}`,
  });
}

function lienItineraireWaze(lat, lon) {
  const web = `https://waze.com/ul?ll=${lat},${lon}&navigate=yes`;
  return boutonItineraire("🚗 Waze", {
    web,
    android:
      `intent://waze.com/ul?ll=${lat},${lon}&navigate=yes` +
      `#Intent;scheme=https;package=com.waze;S.browser_fallback_url=${encodeURIComponent(web)};end`,
    ios: `waze://?ll=${lat},${lon}&navigate=yes`,
  });
}

/** Nom lisible du site d'un lien (ex. « viaferrata-fr.net »). */
function nomDeSite(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return "Site de référence";
  }
}

/* ------------------------------------------------------------------ */
/* Carnet : notes + photos datées                                       */
/* ------------------------------------------------------------------ */

async function initCarnet(pointId) {
  const zone = panel.querySelector(".carnet-entries");
  const form = panel.querySelector(".carnet-form");
  const inputPhoto = form.querySelector('input[type="file"]');
  const nomPhoto = form.querySelector(".carnet-photo-nom");
  let photoDataUrl = null;

  await afficherEntrees();

  inputPhoto.addEventListener("change", async () => {
    const fichier = inputPhoto.files[0];
    if (!fichier) return;
    try {
      photoDataUrl = await redimensionnerPhoto(fichier);
      nomPhoto.textContent = fichier.name;
    } catch {
      nomPhoto.textContent = "Photo illisible";
      photoDataUrl = null;
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const texte = form.querySelector("textarea").value.trim();
    if (!texte && !photoDataUrl) return;
    await storage.addJournalEntry(pointId, {
      id: `j-${Date.now().toString(36)}`,
      date: new Date().toISOString(),
      text: texte,
      photo: photoDataUrl,
    });
    form.querySelector("textarea").value = "";
    nomPhoto.textContent = "";
    photoDataUrl = null;
    inputPhoto.value = "";
    await afficherEntrees();
  });

  async function afficherEntrees() {
    const entrees = await storage.getJournal(pointId);
    zone.textContent = "";
    for (const entree of [...entrees].reverse()) {
      const date = new Date(entree.date).toLocaleDateString("fr-FR", {
        day: "numeric", month: "long", year: "numeric",
      });
      const div = document.createElement("article");
      div.className = "carnet-entry";
      div.innerHTML =
        `<header><time>${esc(date)}</time>` +
        `<button type="button" class="btn-icon carnet-delete" title="Supprimer cette entrée">🗑</button></header>` +
        (entree.photo ? `<img src="${entree.photo}" alt="Photo du ${esc(date)}" loading="lazy">` : "") +
        (entree.text ? `<p>${esc(entree.text)}</p>` : "");
      div.querySelector(".carnet-delete").addEventListener("click", async () => {
        if (!(await confirmer("Supprimer cette entrée du carnet ?"))) return;
        await storage.deleteJournalEntry(pointId, entree.id);
        await afficherEntrees();
      });
      zone.appendChild(div);
    }
  }
}

/**
 * Redimensionne une photo côté client (max 1024 px, JPEG qualité 0.8)
 * pour ne pas faire gonfler IndexedDB. Retourne une dataURL.
 */
async function redimensionnerPhoto(fichier) {
  const image = await new Promise((resolve, reject) => {
    const url = URL.createObjectURL(fichier);
    const img = new Image();
    img.onload = () => {
      URL.revokeObjectURL(url);
      resolve(img);
    };
    img.onerror = reject;
    img.src = url;
  });
  const ratio = Math.min(1, PHOTO_MAX / Math.max(image.width, image.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(image.width * ratio);
  canvas.height = Math.round(image.height * ratio);
  canvas.getContext("2d").drawImage(image, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL("image/jpeg", PHOTO_QUALITE);
}
