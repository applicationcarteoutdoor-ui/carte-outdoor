/**
 * Service worker : consultation hors connexion.
 *
 * Stratégie :
 *  - Le "shell" de l'application (HTML, CSS, JS, librairies, données par
 *    défaut, icônes) est pré-caché à l'installation → l'app démarre sans réseau.
 *  - Les fichiers same-origin chargés ensuite (ex. data/gr.geojson, volumineux
 *    donc non pré-caché) sont mis en cache à la volée → disponibles hors-ligne
 *    après un premier chargement.
 *  - Les tuiles de carte sont mises en cache au fil de la navigation
 *    (cache-first, plafonné) → les zones déjà consultées restent visibles.
 *
 * ⚠️ Incrémenter VERSION à chaque mise à jour des fichiers de l'application
 *    pour invalider l'ancien cache.
 */

const VERSION = "v49";
const CACHE_SHELL = `carte-outdoor-shell-${VERSION}`;
const CACHE_TUILES = "carte-outdoor-tuiles-v1";
const MAX_TUILES = 600;

/* Chemins relatifs : fonctionne à la racine d'un domaine comme dans un
   sous-dossier (GitHub Pages). */
const SHELL = [
  "./",
  "./index.html",
  "./manifest.webmanifest",
  "./css/styles.css",
  "./css/carnet.css",
  "./css/oracle.css",
  "./fonts/caveat.woff2",
  "./js/app.js",
  "./js/util.js",
  "./js/filtrage.js",
  "./js/carnet.js",
  "./js/oracle.js",
  "./js/sync.js",
  "./js/map.js",
  "./js/filters.js",
  "./js/details.js",
  "./js/sidebar.js",
  "./js/import-export.js",
  "./js/gpx.js",
  "./js/storage.js",
  "./js/tuto.js",
  "./js/ideas.js",
  "./js/addpoint.js",
  "./js/partage.js",
  "./js/config/themes.js",
  "./js/config/glossaire.js",
  "./js/config/supabase.js",
  "./js/config/platform.js",
  "./data/points.geojson",
  "./vendor/leaflet/leaflet.js",
  "./vendor/leaflet/leaflet.css",
  "./vendor/leaflet/images/layers.png",
  "./vendor/leaflet/images/layers-2x.png",
  "./vendor/markercluster/leaflet.markercluster.js",
  "./vendor/markercluster/MarkerCluster.css",
  "./vendor/markercluster/MarkerCluster.Default.css",
  "./vendor/togeojson/togeojson.umd.js",
  "./vendor/fflate/fflate.min.js",
  "./icons/icon.svg",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./img/carnet-couverture.jpg",
  "./img/carnet-page-1.jpg",
  "./img/carnet-page-2.jpg",
  "./img/carnet-page-3.jpg",
  "./img/carnet-page-4.jpg",
  "./img/qr-site.svg",
];

/** Hôtes des serveurs de tuiles (cache dédié). */
const HOTES_TUILES = [
  "tile.openstreetmap.org",
  "tile.opentopomap.org",
  "data.geopf.fr",
  "server.arcgisonline.com",
];

self.addEventListener("install", (event) => {
  event.waitUntil(precacherShell().then(() => self.skipWaiting()));
});

/**
 * Pré-cache le shell en forçant `cache: "reload"` : chaque fichier est
 * re-téléchargé depuis le RÉSEAU, jamais depuis le cache HTTP du navigateur.
 *
 * ⚠️ Indispensable : `cache.addAll()` passe par le cache HTTP. Un fichier
 * dont le CONTENU change sans que son NOM change (ex. img/carnet-*.jpg
 * remplacées d'une version à l'autre) était alors recopié PÉRIMÉ dans le
 * nouveau cache — la VERSION montait mais les pixels restaient anciens
 * (bug « couverture avec le bureau » constaté en v24→v26).
 */
async function precacherShell() {
  const cache = await caches.open(CACHE_SHELL);
  await Promise.all(
    SHELL.map(async (url) => {
      try {
        const reponse = await fetch(new Request(url, { cache: "reload" }));
        if (reponse.ok) await cache.put(url, reponse);
      } catch (e) {
        // Un fichier manquant ne doit pas faire échouer toute l'installation
        console.warn("Pré-cache impossible :", url, e);
      }
    })
  );
}

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((noms) =>
        Promise.all(
          noms
            .filter((n) => n.startsWith("carte-outdoor-shell-") && n !== CACHE_SHELL)
            .map((n) => caches.delete(n))
        )
      )
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== "GET") return;

  // Tuiles de carte : cache-first avec plafond
  if (HOTES_TUILES.some((h) => url.hostname.endsWith(h))) {
    event.respondWith(repondreTuile(event.request));
    return;
  }

  // Fichiers de l'application : cache-first + mise en cache à la volée
  if (url.origin === self.location.origin) {
    event.respondWith(repondreShell(event.request));
  }
});

async function repondreShell(requete) {
  const cache = await caches.open(CACHE_SHELL);
  const enCache = await cache.match(requete, { ignoreSearch: true });
  if (enCache) return enCache;
  try {
    const reponse = await fetch(requete);
    // Mise en cache à la volée des fichiers non pré-cachés (ex. gr.geojson)
    if (reponse.ok) cache.put(requete, reponse.clone());
    return reponse;
  } catch (e) {
    // Navigation hors-ligne vers une page inconnue → l'application
    if (requete.mode === "navigate") {
      const index = await cache.match("./index.html");
      if (index) return index;
    }
    throw e;
  }
}

async function repondreTuile(requete) {
  const cache = await caches.open(CACHE_TUILES);
  const enCache = await cache.match(requete);
  if (enCache) return enCache;
  try {
    const reponse = await fetch(requete);
    // Les tuiles chargées par <img> donnent des réponses "opaques" (status 0) :
    // on les met en cache quand même, sinon rien ne serait conservé hors-ligne.
    if (reponse.ok || reponse.type === "opaque") {
      cache.put(requete, reponse.clone());
      limiterCache(cache); // sans await : nettoyage en tâche de fond
    }
    return reponse;
  } catch {
    // Hors-ligne et tuile absente du cache : tuile vide
    return new Response("", { status: 204 });
  }
}

/** Supprime les entrées les plus anciennes au-delà du plafond. */
async function limiterCache(cache) {
  const cles = await cache.keys();
  if (cles.length > MAX_TUILES) {
    const aSupprimer = cles.slice(0, cles.length - MAX_TUILES);
    await Promise.all(aSupprimer.map((c) => cache.delete(c)));
  }
}
