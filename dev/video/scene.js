/**
 * Script de SCÈNE — s'exécute à l'intérieur de l'application (iframe).
 *
 * Chargé par dev/video/capture.html. Comme il vient de la même origine, la CSP
 * de l'app (`script-src 'self'`) l'autorise, et ses `import()` retombent sur
 * les MÊMES instances de modules que l'application vivante : on peut donc
 * ouvrir une fiche ou le carnet exactement comme le ferait l'utilisateur.
 *
 * Outil de développement : jamais pré-caché, jamais servi aux visiteurs.
 */

const params = new URL(import.meta.url).searchParams;
const scene = params.get("scene") || "carte";
const pointId = params.get("point");

const attendre = (ms) => new Promise((r) => setTimeout(r, ms));

/** Attend que la carte ait des tuiles ET des épingles (sinon on photographie du vide). */
async function attendreCarte() {
  for (let i = 0; i < 80; i++) {
    const tuiles = document.querySelectorAll(".leaflet-tile-loaded").length;
    const epingles = document.querySelectorAll(".leaflet-marker-icon").length;
    if (tuiles > 4 && epingles > 0) return true;
    await attendre(250);
  }
  return false;
}

/** Le tuto et le rappel de sauvegarde peuvent malgré tout s'afficher. */
function fermerTuto() {
  document.querySelector(".tuto-skip")?.click();
  const overlay = document.getElementById("tuto-overlay");
  if (overlay) overlay.hidden = true;
  document.getElementById("backup-dialog")?.close?.();
}

/** Le panneau de filtres s'ouvre tout seul (catégories filtrables cochées) :
 *  pour une capture, on veut la carte nue. */
function fermerFiltres() {
  document.querySelector("#filter-panel .panel-close")?.click();
}

/** Fige les animations : une capture nette, pas un flou de scintillement. */
function figerAnimations() {
  const st = document.createElement("style");
  st.textContent = "*{animation:none!important;transition:none!important}";
  document.head.appendChild(st);
}

async function pretPour(selecteur, essais = 40) {
  for (let i = 0; i < essais; i++) {
    if (document.querySelector(selecteur)) return true;
    await attendre(200);
  }
  return false;
}

/** Ouvre la fiche du point, carte centrée dessus — le geste du plan « il clique ». */
async function ouvrirFiche(id) {
  const pts = await fetch("./data/points.geojson").then((r) => r.json());
  const feature = pts.features.find((f) => f.properties.id === id);
  const { focusPoint } = await import("../../js/map.js");
  focusPoint(feature); // la carte se centre sur le spot, épingle en avant
  await attendre(1500);
  const details = await import("../../js/details.js");
  details.openDetails(feature, null);
  await pretPour(".details-panel, #details-panel");
  await attendre(1400); // laisse la photo Wikipédia arriver
}

/** Feuillette le grimoire : le carnet écoute les flèches sur `document`. */
async function tournerPages(nb) {
  for (let i = 0; i < nb; i++) {
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowRight", bubbles: true }));
    await attendre(800); // l'animation de pli dure ~300 ms
  }
}

(async () => {
  await attendreCarte();
  fermerTuto();
  fermerFiltres();
  await attendre(400);

  // Un plan large sur la France n'inspire rien : on cadre le massif du héros,
  // comme le ferait un utilisateur qui zoome sur sa région.
  if (scene === "carte") {
    const { getMap } = await import("../../js/map.js");
    getMap()?.setView([45.75, 6.6], 9, { animate: false }); // Alpes / Mont-Blanc
    await attendre(2200); // les tuiles du nouveau cadrage
  }

  if (scene.startsWith("fiche-")) await ouvrirFiche(pointId);

  if (scene === "oracle") {
    document.getElementById("btn-oracle").click();
    await attendre(700);
  }

  if (scene.startsWith("carnet")) {
    const carnet = await import("../../js/carnet.js");
    await carnet.ouvrirCarnet();
    await attendre(900);
    document.querySelector(".carnet-couverture")?.click(); // on ouvre le livre
    await attendre(1200);

    // carnet-p1 / p2 / p3 : la page voulue du grimoire
    const page = Number((scene.match(/^carnet-p(\d+)$/) || [])[1] || 1);
    if (page > 1) await tournerPages(page - 1);

    if (scene === "carnet-photo") {
      document.querySelector(".page-photo")?.click(); // visionneuse plein écran
      await attendre(700);
    }
  }

  figerAnimations();
  await attendre(300);
  // Repère pour l'outil de capture : posé DANS l'iframe et sur la page hôte
  // (même origine) — l'outil photographie dès qu'il le voit.
  document.title = "PRET — " + scene;
  document.documentElement.dataset.scenePrete = scene;
  try {
    window.parent.document.documentElement.dataset.scenePrete = scene;
  } catch {}
})();
