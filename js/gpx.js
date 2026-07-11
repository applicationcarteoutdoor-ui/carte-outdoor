/**
 * Traces (GPX, KML, KMZ, GeoJSON) : stockage, affichage, profil altimétrique.
 *
 * Le parsing des fichiers est fait par import-export.js (tout est converti
 * en GeoJSON) ; ce module reçoit des traces GeoJSON via importTraceGeojson(),
 * les persiste dans IndexedDB, les affiche sur la carte et rend la liste
 * dans l'onglet « Traces » du panneau latéral.
 *
 * Le profil altimétrique est un SVG généré à la main : distance cumulée
 * (haversine) en abscisse, altitude en ordonnée.
 */

import * as storage from "./storage.js";
import { getMap } from "./map.js";
// Cycle import-export ⇄ gpx sans danger : `confirmer` est une déclaration de
// fonction (hissée) et n'est appelée qu'au clic, longtemps après le chargement.
import { confirmer } from "./import-export.js";
import { esc } from "./util.js";

/* global L */

const COULEURS = ["#e63946", "#3a86ff", "#2a9d8f", "#f4a261", "#9d4edd", "#588157", "#bc4749", "#023e8a"];

let tracks = []; // [{id, name, color, visible, geojson, stats}]
const layersById = new Map();
let trackGroup = null; // groupe maître : permet de tout masquer d'un coup
let conteneur = null; // conteneur de rendu (onglet Traces du panneau latéral)
let onTracksChanged = null;

export async function initGpx(callbacks = {}) {
  onTracksChanged = callbacks.onTracksChanged;
  trackGroup = L.layerGroup().addTo(getMap());
  tracks = await storage.getTracks();
  for (const t of tracks) creerCouche(t);
}

export function tracksCount() {
  return tracks.length;
}

/** Affiche/masque TOUTES les traces (toggle global du panneau de filtres). */
export function setAllTracesVisible(visible) {
  if (!trackGroup) return;
  if (visible) trackGroup.addTo(getMap());
  else trackGroup.remove();
}

/* ------------------------------------------------------------------ */
/* Import d'une trace déjà convertie en GeoJSON                         */
/* ------------------------------------------------------------------ */

/**
 * Enregistre et affiche une nouvelle trace.
 * @param {string} nom nom de la trace (balise <name> ou nom du fichier)
 * @param {object} geojson FeatureCollection contenant les lignes
 * @returns {object|null} la trace créée, ou null si aucune ligne
 */
export async function importTraceGeojson(nom, geojson) {
  const coords = extraireCoordonnees(geojson);
  if (!coords.length) return null;
  const track = {
    id: `tr-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`,
    name: nom,
    color: COULEURS[tracks.length % COULEURS.length],
    visible: true,
    geojson,
    stats: calculerStats(coords),
  };
  tracks.push(track);
  await storage.addTrack(track);
  creerCouche(track);
  renderTracks();
  onTracksChanged?.();
  return track;
}

/** Zoome la carte sur une trace. */
export function zoomSurTrace(id) {
  const couche = layersById.get(id);
  if (couche) getMap().fitBounds(couche.getBounds(), { padding: [30, 30] });
}

function extraireCoordonnees(geojson) {
  const coords = [];
  for (const f of geojson.features || []) {
    if (f.geometry?.type === "LineString") coords.push(...f.geometry.coordinates);
    else if (f.geometry?.type === "MultiLineString")
      for (const ligne of f.geometry.coordinates) coords.push(...ligne);
  }
  return coords;
}

/* ------------------------------------------------------------------ */
/* Statistiques (distance, dénivelé)                                    */
/* ------------------------------------------------------------------ */

function haversine([lon1, lat1], [lon2, lat2]) {
  const R = 6371000;
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

function calculerStats(coords) {
  let distance = 0;
  let dplus = 0;
  let dminus = 0;
  let eleMin = Infinity;
  let eleMax = -Infinity;
  const profil = [];

  // Hystérésis de 5 m sur l'altitude pour ne pas cumuler le bruit du GPS
  const SEUIL = 5;
  let eleReference = null;

  for (let i = 0; i < coords.length; i++) {
    if (i > 0) distance += haversine(coords[i - 1], coords[i]);
    const ele = coords[i][2];
    if (typeof ele === "number") {
      eleMin = Math.min(eleMin, ele);
      eleMax = Math.max(eleMax, ele);
      profil.push([distance, ele]);
      if (eleReference === null) {
        eleReference = ele;
      } else if (Math.abs(ele - eleReference) >= SEUIL) {
        if (ele > eleReference) dplus += ele - eleReference;
        else dminus += eleReference - ele;
        eleReference = ele;
      }
    }
  }

  return {
    distanceKm: distance / 1000,
    dplus: Math.round(dplus),
    dminus: Math.round(dminus),
    eleMin: profil.length ? Math.round(eleMin) : null,
    eleMax: profil.length ? Math.round(eleMax) : null,
    profil,
  };
}

/* ------------------------------------------------------------------ */
/* Couches Leaflet                                                      */
/* ------------------------------------------------------------------ */

function creerCouche(track) {
  const couche = L.geoJSON(track.geojson, {
    style: { color: track.color, weight: 4, opacity: 0.85 },
    pointToLayer: (f, latlng) =>
      L.circleMarker(latlng, { radius: 5, color: track.color, fillOpacity: 0.8 }),
  });
  layersById.set(track.id, couche);
  if (track.visible) couche.addTo(trackGroup);
}

/* ------------------------------------------------------------------ */
/* Rendu de la liste des traces (onglet du panneau latéral)             */
/* ------------------------------------------------------------------ */

/** Fixe le conteneur de rendu (appelé par le panneau latéral) puis rend. */
export function renderTracksInto(element) {
  conteneur = element;
  renderTracks();
}

function renderTracks() {
  if (!conteneur) return;
  const corps = conteneur.querySelector(".tracks-items");
  corps.textContent = "";
  if (!tracks.length) {
    corps.innerHTML =
      '<p class="list-empty">Aucune trace pour le moment.<br>Importez vos fichiers GPX, KML, KMZ ou GeoJSON avec le bouton d\'import.</p>';
    return;
  }

  for (const track of tracks) {
    const s = track.stats;
    const stats =
      `${s.distanceKm.toFixed(1)} km` +
      (s.eleMin !== null ? ` · D+ ${s.dplus} m · D- ${s.dminus} m` : "");
    const item = document.createElement("div");
    item.className = "track-item";
    item.innerHTML = `
      <button type="button" class="track-main" title="Zoomer sur la trace">
        <span class="track-color" style="background:${track.color}" aria-hidden="true"></span>
        <span class="track-text"><strong>${esc(track.name)}</strong><small>${stats}</small></span>
      </button>
      <div class="track-actions">
        <button type="button" class="btn-icon track-toggle" aria-pressed="${track.visible}"
          title="${track.visible ? "Masquer" : "Afficher"}">${track.visible ? "👁" : "🚫"}</button>
        <button type="button" class="btn-icon track-profile" title="Profil altimétrique"
          ${s.profil.length ? "" : "disabled"}>📈</button>
        <button type="button" class="btn-icon track-delete" title="Supprimer">🗑</button>
      </div>`;

    item.querySelector(".track-main").addEventListener("click", () => {
      zoomSurTrace(track.id);
      document.getElementById("sidebar").classList.remove("open");
    });
    item.querySelector(".track-toggle").addEventListener("click", async () => {
      track.visible = !track.visible;
      const couche = layersById.get(track.id);
      if (track.visible) couche.addTo(trackGroup);
      else trackGroup.removeLayer(couche);
      await storage.updateTrack(track.id, { visible: track.visible });
      renderTracks();
    });
    item.querySelector(".track-profile").addEventListener("click", () => afficherProfil(track));
    item.querySelector(".track-delete").addEventListener("click", async () => {
      // JAMAIS confirm() natif : silencieusement ignoré en PWA installée
      if (!(await confirmer(`Supprimer la trace « ${track.name} » ?`))) return;
      const couche = layersById.get(track.id);
      if (couche) trackGroup.removeLayer(couche);
      layersById.delete(track.id);
      tracks = tracks.filter((t) => t.id !== track.id);
      await storage.deleteTrack(track.id);
      renderTracks();
      onTracksChanged?.();
    });
    corps.appendChild(item);
  }
}

/* ------------------------------------------------------------------ */
/* Profil altimétrique (SVG maison)                                     */
/* ------------------------------------------------------------------ */

function afficherProfil(track) {
  const zone = conteneur.querySelector(".track-profile-area");
  const { profil, distanceKm, dplus, dminus, eleMin, eleMax } = track.stats;

  const W = 640;
  const H = 240;
  const M = { haut: 14, droite: 12, bas: 26, gauche: 44 };
  const largeur = W - M.gauche - M.droite;
  const hauteur = H - M.haut - M.bas;
  const distMax = profil[profil.length - 1][0];
  const margeEle = Math.max(10, (eleMax - eleMin) * 0.08);
  const yMin = eleMin - margeEle;
  const yMax = eleMax + margeEle;

  const x = (d) => M.gauche + (d / distMax) * largeur;
  const y = (e) => M.haut + hauteur - ((e - yMin) / (yMax - yMin)) * hauteur;

  const pas = Math.max(1, Math.floor(profil.length / 600));
  const points = [];
  for (let i = 0; i < profil.length; i += pas) {
    points.push(`${x(profil[i][0]).toFixed(1)},${y(profil[i][1]).toFixed(1)}`);
  }
  const dernier = profil[profil.length - 1];
  points.push(`${x(dernier[0]).toFixed(1)},${y(dernier[1]).toFixed(1)}`);

  const surface = `${M.gauche},${M.haut + hauteur} ${points.join(" ")} ${x(distMax).toFixed(1)},${M.haut + hauteur}`;

  const grads = [eleMin, Math.round((eleMin + eleMax) / 2), eleMax]
    .map(
      (e) =>
        `<line x1="${M.gauche}" y1="${y(e)}" x2="${W - M.droite}" y2="${y(e)}" class="profil-grille"/>` +
        `<text x="${M.gauche - 6}" y="${y(e) + 4}" class="profil-texte" text-anchor="end">${e} m</text>`
    )
    .join("");
  const gradsX = [0, distMax / 2, distMax]
    .map(
      (d) =>
        `<text x="${x(d)}" y="${H - 8}" class="profil-texte" text-anchor="middle">${(d / 1000).toFixed(1)} km</text>`
    )
    .join("");

  zone.innerHTML = `
    <div class="profil-entete">
      <strong>${esc(track.name)}</strong>
      <button type="button" class="btn-icon profil-close" title="Fermer le profil">✕</button>
    </div>
    <p class="profil-stats">${distanceKm.toFixed(1)} km · D+ ${dplus} m · D- ${dminus} m · ${eleMin}–${eleMax} m</p>
    <svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Profil altimétrique de ${esc(track.name)}" preserveAspectRatio="xMidYMid meet">
      ${grads}
      <polygon points="${surface}" fill="${track.color}" opacity="0.18"/>
      <polyline points="${points.join(" ")}" fill="none" stroke="${track.color}" stroke-width="2"/>
      ${gradsX}
    </svg>`;
  zone.style.display = "";
  zone.querySelector(".profil-close").addEventListener("click", () => {
    zone.style.display = "none";
    zone.innerHTML = "";
  });
}
