/**
 * Prévisions météo à 3 jours par spot (Open-Meteo — gratuit, sans clé, CORS).
 *
 * Fonctionne EN LIGNE : à l'ouverture d'une fiche, on interroge
 * api.open-meteo.com pour les coordonnées du point et on affiche 3 cartes
 * (icône, min/max, pluie, vent) — de quoi organiser et planifier sa sortie.
 * Le résultat est mis en cache 1 h par coordonnée arrondie : les re-rendus de
 * la fiche (changement de statut) ne relancent pas d'appel. Hors ligne ou en
 * cas d'erreur : message discret, jamais de blocage de la fiche.
 *
 * ⚠️ api.open-meteo.com doit figurer dans la CSP connect-src (index.html),
 * sinon l'appel est bloqué silencieusement.
 */

import { esc } from "./util.js";

const TTL = 60 * 60 * 1000; // fraîcheur du cache : 1 h
const cache = new Map(); // "lat3,lon3" -> { at, data }

// Codes météo WMO renvoyés par Open-Meteo → emoji + libellé court (fr).
const WMO = {
  0: ["☀️", "Ciel clair"],
  1: ["🌤️", "Peu nuageux"],
  2: ["⛅", "Partiellement nuageux"],
  3: ["☁️", "Couvert"],
  45: ["🌫️", "Brouillard"],
  48: ["🌫️", "Brouillard givrant"],
  51: ["🌦️", "Bruine légère"],
  53: ["🌦️", "Bruine"],
  55: ["🌦️", "Bruine dense"],
  56: ["🌧️", "Bruine verglaçante"],
  57: ["🌧️", "Bruine verglaçante"],
  61: ["🌧️", "Pluie faible"],
  63: ["🌧️", "Pluie"],
  65: ["🌧️", "Forte pluie"],
  66: ["🌧️", "Pluie verglaçante"],
  67: ["🌧️", "Pluie verglaçante"],
  71: ["🌨️", "Neige faible"],
  73: ["🌨️", "Neige"],
  75: ["🌨️", "Fortes chutes de neige"],
  77: ["🌨️", "Grains de neige"],
  80: ["🌦️", "Averses"],
  81: ["🌦️", "Averses"],
  82: ["⛈️", "Fortes averses"],
  85: ["🌨️", "Averses de neige"],
  86: ["🌨️", "Averses de neige"],
  95: ["⛈️", "Orage"],
  96: ["⛈️", "Orage grêleux"],
  99: ["⛈️", "Orage grêleux"],
};

function codeWmo(c) {
  return WMO[c] || ["❓", "—"];
}

/** Libellé du jour : « Auj. », « Demain », puis le jour de la semaine. */
function libelleJour(iso, i) {
  if (i === 0) return "Auj.";
  if (i === 1) return "Demain";
  // midi pour éviter tout effet de bord de fuseau/heure d'été
  const s = new Date(iso + "T12:00:00").toLocaleDateString("fr-FR", { weekday: "short" });
  return s.charAt(0).toUpperCase() + s.slice(1); // « lun. » → « Lun. »
}

async function prevoir(lat, lon) {
  const cle = `${lat.toFixed(3)},${lon.toFixed(3)}`;
  const enCache = cache.get(cle);
  if (enCache && Date.now() - enCache.at < TTL) return enCache.data;

  const url =
    "https://api.open-meteo.com/v1/forecast" +
    `?latitude=${lat.toFixed(4)}&longitude=${lon.toFixed(4)}` +
    "&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max" +
    "&forecast_days=3&timezone=auto";

  // minuteur : une requête trop lente ne laisse pas « Chargement… » à l'infini
  const ctrl = new AbortController();
  const minuteur = setTimeout(() => ctrl.abort(), 8000);
  try {
    const r = await fetch(url, { signal: ctrl.signal });
    if (!r.ok) throw new Error("http " + r.status);
    const data = await r.json();
    cache.set(cle, { at: Date.now(), data });
    return data;
  } finally {
    clearTimeout(minuteur);
  }
}

function carteJour(d, i) {
  const [emoji, label] = codeWmo(d.code);
  const pluie = d.pluie < 10 ? d.pluie.toFixed(1) : Math.round(d.pluie);
  return `<div class="meteo-jour">
    <span class="meteo-jour-nom">${esc(libelleJour(d.iso, i))}</span>
    <span class="meteo-ico" role="img" aria-label="${esc(label)}" title="${esc(label)}">${emoji}</span>
    <span class="meteo-temp"><strong>${Math.round(d.tmax)}°</strong><span class="meteo-tmin">${Math.round(d.tmin)}°</span></span>
    <span class="meteo-ligne">💧 ${pluie} mm</span>
    <span class="meteo-ligne">💨 ${Math.round(d.vent)} km/h</span>
  </div>`;
}

/**
 * Remplit `conteneur` avec les prévisions à 3 jours pour (lat, lon).
 * Fire-and-forget : à ne pas attendre, l'ouverture de la fiche n'est jamais
 * bloquée par le réseau.
 */
export async function chargerMeteo(lat, lon, conteneur) {
  if (!conteneur) return;
  if (!navigator.onLine) {
    conteneur.innerHTML = `<p class="meteo-note">🌦️ Prévisions météo indisponibles hors ligne.</p>`;
    return;
  }
  conteneur.innerHTML = `<p class="meteo-note">🌦️ Chargement des prévisions…</p>`;
  try {
    const dj = (await prevoir(lat, lon)).daily;
    const jours = dj.time.slice(0, 3).map((iso, i) => ({
      iso,
      code: dj.weather_code[i],
      tmax: dj.temperature_2m_max[i],
      tmin: dj.temperature_2m_min[i],
      pluie: dj.precipitation_sum[i] ?? 0,
      vent: dj.wind_speed_10m_max[i] ?? 0,
    }));
    conteneur.innerHTML = `
      <h3 class="meteo-titre">🌦️ Météo — 3 jours</h3>
      <div class="meteo-jours">${jours.map(carteJour).join("")}</div>
      <p class="meteo-source">Prévisions <a href="https://open-meteo.com/" target="_blank" rel="noopener">Open-Meteo</a></p>`;
  } catch {
    conteneur.innerHTML = `<p class="meteo-note">🌦️ Prévisions météo indisponibles pour le moment.</p>`;
  }
}
