/**
 * Visite guidée (tuto).
 *
 * Lancée automatiquement à la toute première connexion (skippable), et
 * relançable à tout moment avec le bouton 🎓. Chaque étape met en lumière
 * un élément de l'interface (découpe dans un voile sombre) avec une carte
 * explicative. Les étapes sont déclarées dans le tableau ETAPES : en
 * ajouter une = ajouter une entrée.
 */

let overlay = null;
let indice = 0;
let onFin = null;
let ouvrirFiltresHook = null; // fourni par app.js : affiche un vrai panneau de filtres

const ETAPES = [
  {
    titre: "Bienvenue sur Carte Outdoor ! 🏔️",
    texte:
      "Une carte de points d'intérêt outdoor : via ferrata, escalade, refuges, châteaux, cités de caractère, GR… " +
      "Ce petit tour vous montre l'essentiel (vous pouvez le revoir à tout moment avec le bouton 🎓).",
  },
  {
    cible: "#search-input",
    avant: () => document.getElementById("sidebar").classList.add("open"),
    titre: "La recherche",
    texte: "Retrouvez n'importe quel point par son nom, directement au-dessus des catégories.",
  },
  {
    cible: "#sidebar .cat-list",
    placement: "cote", // la carte ne doit pas recouvrir la liste des catégories
    titre: "Les catégories",
    texte:
      "Cochez les catégories à afficher — plusieurs à la fois si vous voulez. " +
      "Vos statuts (★ à faire, ✓ fait, ♥ favoris), les sentiers GR et vos traces GPX se cochent " +
      "au même endroit, et ✎ personnalise le nom, les couleurs et l'icône de chaque catégorie.",
  },
  {
    cible: "#btn-settings",
    titre: "Les réglages ⚙️",
    texte:
      "La roue en bas du panneau regroupe : l'import de vos propres points (GeoJSON, CSV, KML, KMZ), " +
      "l'export de vos données (points, suivi, carnet, catégories), l'installation de l'application " +
      "sur l'écran d'accueil, la synchronisation multi-appareils avec votre compte Google " +
      "et la vérification des mises à jour. " +
      "Les traces GPX, elles, s'importent depuis la ligne « Mes traces GPX ».",
  },
  {
    cible: "#filter-panel",
    avant: () => {
      document.getElementById("sidebar").classList.remove("open");
      // Ouvre un panneau de filtres réel (coche une catégorie à filtres si besoin)
      ouvrirFiltresHook?.();
    },
    titre: "Les filtres",
    texte:
      "Dès qu'une catégorie cochée propose des filtres (cotation des via ferrata, chauffage et altitude " +
      "des refuges…), ils apparaissent ici en pastilles. « Tout » = aucun filtrage. " +
      "Survolez une cotation (PD, AD, D…) pour voir sa signification.",
  },
  {
    cible: "#map",
    titre: "La carte",
    texte:
      "Cliquez un point pour ouvrir sa fiche : itinéraire Google Maps/Waze, liens et photos, " +
      "statuts, carnet personnel. Cliquez un tracé de GR pour voir son nom, sa distance, son D+ " +
      "et ses liens — il se met en surbrillance orange.",
  },
  {
    cible: "#btn-add-point",
    titre: "Ajouter un point",
    texte:
      "Le gros bouton vert : cliquez-le, puis cliquez sur la carte à l'endroit voulu. " +
      "Choisissez une catégorie existante ou créez-en une à la volée (nom, icône, couleur).",
  },
  {
    cible: "#btn-carnet",
    avant: () => document.getElementById("sidebar").classList.remove("open"),
    titre: "Votre carnet de sorties 📖",
    texte:
      "Un vrai grimoire à feuilleter ! Chaque activité marquée « ✓ Fait », chaque note et chaque " +
      "photo s'y enregistre automatiquement, une sortie par page. Recherche, tri par date ou " +
      "catégorie, filtre favoris — et pour chaque lieu, l'historique de toutes vos venues.",
  },
  {
    cible: "#btn-oracle",
    avant: () => document.getElementById("sidebar").classList.remove("open"),
    titre: "L'Oracle 🔮",
    texte:
      "Entrez un code postal (ou touchez 📍) : l'Oracle révèle tout ce qu'il y a à faire " +
      "autour — randonnées, lacs, patrimoine, événements. Le mode ✨ Gratuit ne demande " +
      "aucune clé ; avec une clé API (bouton 🔑), le mode 🧠 IA déniche en plus les concerts, " +
      "spectacles et brocantes du moment, avec leurs dates.",
  },
  {
    cible: "#btn-wc",
    avant: () => document.getElementById("sidebar").classList.remove("open"),
    titre: "Les toilettes publiques",
    texte:
      "Plus de 66 000 toilettes publiques (source OpenStreetMap) ! Ce bouton vous géolocalise et " +
      "n'affiche que celles à moins de 1 km de vous. Vous pouvez aussi cocher la catégorie " +
      "Toilettes dans le panneau : un message vous proposera d'abord le mode le plus adapté " +
      "(tout afficher peut ralentir la carte).",
  },
  {
    cible: ".foot-outils",
    // Les outils vivent dans le pied du panneau : on l'ouvre (mobile)
    avant: () => document.getElementById("sidebar").classList.add("open"),
    placement: "cote",
    titre: "Les outils",
    texte:
      "À côté des réglages ⚙️ : 💡 pour noter vos idées, 🎓 pour revoir ce tuto, " +
      "◎ pour afficher votre position et 🗺️ pour changer le fond de carte (plan, relief, IGN, satellite). " +
      "L'application fonctionne aussi hors connexion : les zones déjà consultées restent visibles. " +
      "Astuce : ajoutez cette carte à votre écran d'accueil pour l'utiliser comme une vraie application. " +
      "Bonne exploration !",
  },
];

export function initTuto({ onTermine, ouvrirFiltres } = {}) {
  onFin = onTermine;
  ouvrirFiltresHook = ouvrirFiltres;
  overlay = document.getElementById("tuto-overlay");
  document.getElementById("btn-tuto").addEventListener("click", startTuto);
}

export function startTuto() {
  indice = 0;
  overlay.hidden = false;
  montrerEtape();
}

function terminer() {
  overlay.hidden = true;
  overlay.innerHTML = "";
  onFin?.();
}

async function montrerEtape() {
  const etape = ETAPES[indice];
  if (etape.avant) {
    etape.avant();
    // Laisse les transitions CSS se terminer (ouverture/fermeture du panneau)
    // avant de mesurer la cible, sinon le rectangle est mesuré en plein vol.
    overlay.innerHTML = "";
    await new Promise((r) => setTimeout(r, 320));
  }

  // Cible : premier sélecteur visible de la liste
  let rect = null;
  if (etape.cible) {
    for (const sel of etape.cible.split(",")) {
      const el = document.querySelector(sel.trim());
      if (!el || el.hidden) continue;
      const r = el.getBoundingClientRect();
      // visible = dans l'écran avec une taille non nulle
      if (r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < window.innerHeight) {
        rect = r;
        break;
      }
    }
  }

  const marge = 8;
  const spot = rect
    ? `top:${rect.top - marge}px;left:${rect.left - marge}px;width:${rect.width + 2 * marge}px;height:${rect.height + 2 * marge}px;`
    : "top:50%;left:50%;width:0;height:0;";

  overlay.innerHTML = `
    <div class="tuto-spot" style="${spot}"></div>
    <div class="tuto-card" role="dialog" aria-labelledby="tuto-titre">
      <h2 id="tuto-titre">${etape.titre}</h2>
      <p>${etape.texte}</p>
      <div class="tuto-progress">${indice + 1} / ${ETAPES.length}</div>
      <div class="tuto-actions">
        <button type="button" class="btn btn-secondary tuto-skip">Passer</button>
        <span class="tuto-nav">
          ${indice > 0 ? '<button type="button" class="btn btn-secondary tuto-prev">Précédent</button>' : ""}
          <button type="button" class="btn tuto-next">${indice === ETAPES.length - 1 ? "Terminer" : "Suivant"}</button>
        </span>
      </div>
    </div>`;

  // Positionne la carte : sous la cible si la place le permet, sinon
  // au-dessus, et TOUJOURS ramenée à l'intérieur de l'écran.
  // placement "cote" : à droite de la cible (pour ne pas la recouvrir) ;
  // s'il n'y a pas la place (mobile), en bas de l'écran — le haut de la
  // cible reste visible.
  const carte = overlay.querySelector(".tuto-card");
  if (rect) {
    const h = carte.offsetHeight || 240;
    const w = carte.offsetWidth || 340;
    if (etape.placement === "cote" && rect.right + 14 + w <= window.innerWidth - 12) {
      carte.style.left = `${rect.right + 14}px`;
      const haut = Math.max(12, Math.min(rect.top + 30, window.innerHeight - h - 12));
      carte.style.top = `${haut}px`;
    } else if (etape.placement === "cote") {
      carte.style.top = `${Math.max(12, window.innerHeight - h - 12)}px`;
      carte.style.left = `${Math.max(12, Math.min(rect.left, window.innerWidth - w - 12))}px`;
    } else {
      let haut = rect.bottom + 14;
      if (haut + h > window.innerHeight - 12) haut = rect.top - h - 14;
      haut = Math.max(12, Math.min(haut, window.innerHeight - h - 12));
      carte.style.top = `${haut}px`;
      const gauche = Math.max(12, Math.min(rect.left, window.innerWidth - w - 12));
      carte.style.left = `${gauche}px`;
    }
  } else {
    carte.classList.add("tuto-card-centre");
  }

  overlay.querySelector(".tuto-skip").addEventListener("click", terminer);
  overlay.querySelector(".tuto-prev")?.addEventListener("click", () => {
    indice--;
    montrerEtape();
  });
  overlay.querySelector(".tuto-next").addEventListener("click", () => {
    if (indice === ETAPES.length - 1) return terminer();
    indice++;
    montrerEtape();
  });
}
