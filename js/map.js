/**
 * Gestion de la carte Leaflet : fonds, marqueurs/clusters, surcouche GR,
 * géolocalisation.
 *
 * Performance (≈ 4 500 points) :
 *  - les marqueurs sont créés UNE SEULE FOIS puis réutilisés à chaque
 *    changement de filtre (seule l'icône est régénérée si le statut ou la
 *    personnalisation de la catégorie a changé) ;
 *  - le clustering charge les marqueurs par petits paquets (chunkedLoading)
 *    pour ne jamais bloquer l'interface ;
 *  - markercluster ne rend que les marqueurs visibles à l'écran
 *    (removeOutsideVisibleBounds, comportement par défaut).
 */

import { getTheme } from "./config/themes.js";

/* global L */

let map = null;
let clusterGroup = null;
let onPointClickCallback = null;

// Cache des marqueurs : id → { marker, statut, cleTheme }
const cache = new Map();

/** Fonds de carte disponibles (tous gratuits, sans clé API). */
function creerFondsDeCarte() {
  return {
    "Plan (OSM)": L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }),
    "Relief (OpenTopoMap)": L.tileLayer("https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png", {
      maxZoom: 17,
      attribution:
        '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a>, SRTM | © <a href="https://opentopomap.org">OpenTopoMap</a> (CC-BY-SA)',
    }),
    "Plan IGN": L.tileLayer(
      "https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0" +
        "&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&TILEMATRIXSET=PM" +
        "&FORMAT=image/png&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}",
      { maxZoom: 19, attribution: '&copy; <a href="https://www.ign.fr">IGN</a> - Géoplateforme' }
    ),
    Satellite: L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      { maxZoom: 19, attribution: "&copy; Esri, Maxar, Earthstar Geographics" }
    ),
  };
}

export function initMap(prefs, { onPointClick, onViewChange }) {
  onPointClickCallback = onPointClick;

  map = L.map("map", {
    center: prefs.center || [46.5, 2.6], // France entière par défaut
    zoom: prefs.zoom || 6,
    zoomControl: false,
    preferCanvas: true,
  });
  L.control.zoom({ position: "bottomright" }).addTo(map);
  L.control.scale({ imperial: false, position: "bottomleft" }).addTo(map);

  const fonds = creerFondsDeCarte();
  const nomFond = fonds[prefs.baseLayer] ? prefs.baseLayer : "Plan (OSM)";
  fonds[nomFond].addTo(map);
  L.control.layers(fonds, null, { position: "bottomright" }).addTo(map);

  clusterGroup = L.markerClusterGroup({
    showCoverageOnHover: false,
    maxClusterRadius: 50,
    spiderfyOnMaxZoom: true,
    // Pas de chunkedLoading : il n'affiche RIEN avant la fin du lot complet
    // (~25 s pour les 66 000 toilettes). setPoints fait son propre découpage
    // en tranches, avec affichage progressif trié par distance.
  });
  map.addLayer(clusterGroup);

  let fondCourant = nomFond;
  map.on("baselayerchange", (e) => {
    fondCourant = e.name;
    signalerVue();
  });
  map.on("moveend", signalerVue);
  function signalerVue() {
    const c = map.getCenter();
    onViewChange?.({
      center: [Number(c.lat.toFixed(5)), Number(c.lng.toFixed(5))],
      zoom: map.getZoom(),
      baseLayer: fondCourant,
    });
  }

  return map;
}

/* ------------------------------------------------------------------ */
/* Marqueurs des points (avec cache)                                    */
/* ------------------------------------------------------------------ */

const BADGES = {
  fait: '<span class="pin-badge pin-badge-fait" aria-hidden="true">✓</span>',
  "a-faire": '<span class="pin-badge pin-badge-afaire" aria-hidden="true">★</span>',
  favori: '<span class="pin-badge pin-badge-favori" aria-hidden="true">♥</span>',
};

// Id du point sélectionné : son épingle est agrandie et mise en évidence.
// La sélection fait partie de l'icône elle-même pour survivre aux
// reconstructions du clustering.
let pointSelectionne = null;

// Les instances de divIcon sont des descripteurs immuables : une seule par
// combinaison (thème, statut, sélection) suffit pour tous les marqueurs —
// indispensable avec ~66 000 toilettes.
const iconeCache = new Map();

function creerIcone(theme, statut, selectionne) {
  const cle = `${theme.color}|${theme.textColor}|${theme.icon}|${statut || ""}|${selectionne ? 1 : 0}`;
  let icone = iconeCache.get(cle);
  if (!icone) {
    icone = L.divIcon({
      className: "pin-wrapper" + (selectionne ? " pin-selected" : ""),
      html:
        `<div class="pin" style="--pin-color:${theme.color};--pin-text:${theme.textColor}">` +
        `<span class="pin-head">${theme.icon}</span>` +
        `<span class="pin-tip"></span>${BADGES[statut] || ""}</div>`,
      iconSize: [36, 46],
      iconAnchor: [18, 44],
    });
    iconeCache.set(cle, icone);
  }
  return icone;
}

function appliquerIcone(entree) {
  const theme = getTheme(entree.marker._feature.properties.theme);
  const selectionne = entree.marker._feature.properties.id === pointSelectionne;
  entree.marker.setIcon(creerIcone(theme, entree.statut, selectionne));
  entree.marker.setZIndexOffset(selectionne ? 1000 : 0);
  entree.selectionne = selectionne;
}

function obtenirMarqueur(feature, statut) {
  const id = feature.properties.id;
  const theme = getTheme(feature.properties.theme);
  const cleTheme = `${theme.color}|${theme.textColor}|${theme.icon}`;
  const selectionne = id === pointSelectionne;
  let entree = cache.get(id);
  if (!entree) {
    const [lon, lat] = feature.geometry.coordinates;
    const marker = L.marker([lat, lon], {
      icon: creerIcone(theme, statut, selectionne),
      title: feature.properties.name,
      alt: feature.properties.name,
      zIndexOffset: selectionne ? 1000 : 0,
    });
    marker.on("click", () => onPointClickCallback?.(marker._feature));
    entree = { marker, statut, cleTheme, selectionne };
    cache.set(id, entree);
  } else if (
    entree.statut !== statut ||
    entree.cleTheme !== cleTheme ||
    entree.selectionne !== selectionne
  ) {
    entree.statut = statut;
    entree.cleTheme = cleTheme;
    entree.marker._feature = feature;
    appliquerIcone(entree);
  }
  entree.marker._feature = feature; // référence à jour (ré-imports)
  return entree.marker;
}

/** Met en évidence le point sélectionné (épingle agrandie + halo). */
export function highlightPoint(id) {
  const ancien = pointSelectionne;
  pointSelectionne = id;
  for (const pid of new Set([ancien, id])) {
    const entree = pid && cache.get(pid);
    if (entree) appliquerIcone(entree);
  }
}

export function clearHighlight() {
  highlightPoint(null);
}

/** Annule les tranches en attente quand un nouveau setPoints remplace tout. */
let generationSetPoints = 0;

/** (Re)affiche l'ensemble des points visibles. Grâce au cache, seuls les
 *  marqueurs nouveaux ou modifiés sont reconstruits.
 *  Au-delà de quelques milliers de points, l'ajout se fait par tranches
 *  triées par distance au centre : la zone regardée s'affiche en ~1 s,
 *  le reste de la France se remplit en arrière-plan sans geler la page. */
export function setPoints(features, statuses) {
  generationSetPoints++;
  clusterGroup.clearLayers();

  if (features.length <= 4000) {
    clusterGroup.addLayers(
      features.map((f) => obtenirMarqueur(f, statuses[f.properties.id]))
    );
    return;
  }

  const c = map.getCenter();
  const cosLat = Math.cos((c.lat * Math.PI) / 180);
  const d2 = (f) => {
    const [lon, lat] = f.geometry.coordinates;
    const dLon = (lon - c.lng) * cosLat;
    return (lat - c.lat) * (lat - c.lat) + dLon * dLon;
  };
  const triees = [...features].sort((a, b) => d2(a) - d2(b));

  const generation = generationSetPoints;
  const TRANCHE = 1500;
  let i = 0;
  const ajouterTranche = () => {
    if (generation !== generationSetPoints) return; // remplacé entre-temps
    clusterGroup.addLayers(
      triees.slice(i, i + TRANCHE).map((f) => obtenirMarqueur(f, statuses[f.properties.id]))
    );
    i += TRANCHE;
    if (i < triees.length) setTimeout(ajouterTranche, 60);
  };
  ajouterTranche();
}

/** Centre la carte sur un point (déplie son cluster si besoin). */
export function focusPoint(feature) {
  const [lon, lat] = feature.geometry.coordinates;
  const entree = cache.get(feature.properties.id);
  if (entree && clusterGroup.hasLayer(entree.marker)) {
    clusterGroup.zoomToShowLayer(entree.marker, () => {});
  } else {
    map.flyTo([lat, lon], Math.max(map.getZoom(), 13), { duration: 0.6 });
  }
}

/** Cercle de recherche (ex. toilettes à moins de 1 km) : un seul à la fois. */
let cercleRayon = null;

export function montrerRayon(lat, lon, rayon) {
  if (cercleRayon) cercleRayon.remove();
  cercleRayon = L.circle([lat, lon], {
    radius: rayon,
    color: "#2e7d52",
    weight: 2,
    dashArray: "6 6",
    fillOpacity: 0.06,
  }).addTo(map);
  // Sans animation : le centre doit être à jour IMMÉDIATEMENT, car le tri
  // par distance de setPoints (gros lots) lit map.getCenter() juste après.
  map.setView([lat, lon], 15, { animate: false });
}

export function getMap() {
  return map;
}

/* ------------------------------------------------------------------ */
/* Surcouche GR (chargée à la demande depuis data/gr.geojson)           */
/* ------------------------------------------------------------------ */

let grLayer = null;
let grChargement = null;
let grSelectionne = null; // tracé mis en évidence

const GR_STYLE = { color: "#b02a2a", weight: 2.5, opacity: 0.75, dashArray: "6 4" };
const GR_STYLE_ACTIF = { color: "#ff9500", weight: 5, opacity: 1, dashArray: null };

function echapper(texte) {
  const div = document.createElement("div");
  div.textContent = texte ?? "";
  return div.innerHTML;
}

/** Contenu de la bulle d'un GR : nom, distance, D+ estimé, liens. */
function popupGr(p) {
  const stats = [];
  if (p.distance_km) stats.push(`${p.distance_km.toLocaleString("fr-FR")} km`);
  if (p.dplus) stats.push(`D+ estimé ${p.dplus.toLocaleString("fr-FR")} m`);
  const liens = [];
  if (p.grgo) liens.push(`<a href="${p.grgo}" target="_blank" rel="noopener">gr-go.fr (planificateur)</a>`);
  if (p.wiki) liens.push(`<a href="${p.wiki}" target="_blank" rel="noopener">Wikipédia</a>`);
  if (p.link) liens.push(`<a href="${p.link}" target="_blank" rel="noopener">gr-infos.com</a>`);
  return (
    `<strong>${echapper(p.name || "GR")}</strong>` +
    (stats.length ? `<br>${stats.join(" · ")}` : "") +
    (liens.length ? `<br>${liens.join(" · ")}` : "")
  );
}

export async function setGrVisible(visible) {
  if (!visible) {
    grLayer?.remove();
    return;
  }
  if (!grLayer) {
    if (!grChargement) {
      grChargement = fetch("data/gr.geojson")
        .then((r) => r.json())
        .then((geojson) => {
          grLayer = L.geoJSON(geojson, {
            style: GR_STYLE,
            onEachFeature: (f, layer) => {
              layer.bindPopup(popupGr(f.properties || {}));
              // Au clic : le GR sélectionné change de couleur pour être repérable
              layer.on("popupopen", () => {
                grSelectionne?.setStyle(GR_STYLE);
                layer.setStyle(GR_STYLE_ACTIF);
                grSelectionne = layer;
              });
            },
          });
        });
    }
    await grChargement;
  }
  grLayer.addTo(map);
}

/* ------------------------------------------------------------------ */
/* Choix d'un emplacement sur la carte (fonction « ajouter un point »)  */
/* ------------------------------------------------------------------ */

/**
 * Passe la carte en mode « visée » : résout avec le L.LatLng cliqué,
 * ou null si l'utilisateur annule avec Échap.
 */
export function pickLocation() {
  return new Promise((resolve) => {
    const conteneur = map.getContainer();
    conteneur.classList.add("picking");
    const finir = (latlng) => {
      conteneur.classList.remove("picking");
      map.off("click", surClic);
      document.removeEventListener("keydown", surTouche);
      resolve(latlng);
    };
    const surClic = (e) => finir(e.latlng);
    const surTouche = (e) => {
      if (e.key === "Escape") finir(null);
    };
    map.on("click", surClic);
    document.addEventListener("keydown", surTouche);
  });
}

/* ------------------------------------------------------------------ */
/* Géolocalisation « autour de moi »                                    */
/* ------------------------------------------------------------------ */

let positionLayer = null;

export async function toggleLocate() {
  if (positionLayer) {
    positionLayer.remove();
    positionLayer = null;
    return "off";
  }
  const pos = await new Promise((resolve, reject) => {
    navigator.geolocation.getCurrentPosition(resolve, reject, {
      enableHighAccuracy: true,
      timeout: 12000,
      maximumAge: 30000,
    });
  });
  const { latitude, longitude, accuracy } = pos.coords;
  positionLayer = L.layerGroup([
    L.circle([latitude, longitude], {
      radius: accuracy,
      color: "#2e7d52",
      weight: 1,
      fillOpacity: 0.12,
    }),
    L.circleMarker([latitude, longitude], {
      radius: 8,
      color: "#ffffff",
      weight: 3,
      fillColor: "#2e7d52",
      fillOpacity: 1,
    }),
  ]).addTo(map);
  map.flyTo([latitude, longitude], Math.max(map.getZoom(), 13), { duration: 0.8 });
  return "on";
}
