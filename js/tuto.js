/**
 * Visite guidée (tuto).
 *
 * Lancée automatiquement à la toute première connexion (skippable), et
 * relançable à tout moment avec le bouton 🎓. Chaque étape met en lumière
 * un élément de l'interface (découpe dans un voile sombre) avec une carte
 * explicative. Les étapes sont déclarées dans le tableau ETAPES : en
 * ajouter une = ajouter une entrée.
 */

import { ouvrirPack, retourAccueilPacks } from "./sidebar.js";

let overlay = null;
let indice = 0;
let onFin = null;
let ouvrirFiltresHook = null; // fourni par app.js : affiche un vrai panneau de filtres

const ETAPES = [
  {
    emoji: "🏔️",
    titre: "Bienvenue sur SpotMap !",
    texte:
      "Votre carte de l'outdoor : randonnées, via ferrata, escalade, refuges, cascades, lacs, " +
      "châteaux, villages… dans 10 pays, de la France à la Nouvelle-Zélande. " +
      "Deux minutes de visite — revoyez-la quand vous voulez avec le bouton 🎓.",
  },
  {
    cible: "#search-input",
    avant: () => document.getElementById("sidebar").classList.add("open"),
    emoji: "🔎",
    titre: "La recherche",
    texte: "Tapez un nom (lac, sommet, village, code postal…) : la carte y file directement.",
  },
  {
    cible: "#sidebar .pack-grid, #sidebar .cat-list",
    placement: "cote", // la carte ne doit pas recouvrir la liste
    avant: () => {
      document.getElementById("sidebar").classList.add("open");
      retourAccueilPacks(); // montre la grille des packs
    },
    emoji: "🧭",
    titre: "Les packs",
    texte:
      "Vos catégories sont rangées en packs. Touchez une tuile pour tout afficher, " +
      "▸ pour choisir dedans, ＋ pour créer le vôtre.",
  },
  {
    cible: "#sidebar .cat-list",
    placement: "cote",
    avant: () => {
      document.getElementById("sidebar").classList.add("open");
      ouvrirPack("montagne"); // un pack ouvert = des catégories cochables
    },
    emoji: "🗂️",
    titre: "Les catégories",
    texte:
      "Dans un pack, cochez ce que vous voulez voir — plusieurs à la fois. Seules les très " +
      "grosses couches (toilettes, fontaines…) s'affichent seules, pour rester fluide. " +
      "✎ personnalise nom, couleurs et icône.",
  },
  {
    cible: "#filter-panel",
    avant: () => {
      document.getElementById("sidebar").classList.remove("open");
      // Ouvre un panneau de filtres réel (coche une catégorie à filtres si besoin)
      ouvrirFiltresHook?.();
    },
    emoji: "🎚️",
    titre: "Les filtres",
    texte:
      "Chaque catégorie a ses filtres en pastilles : cotation des via ferrata, effort des randos, " +
      "altitude des refuges… Ils repartent à zéro à chaque activation — « Tout » = aucun filtrage. " +
      "Survolez une cotation (PD, AD, K3…) pour sa signification.",
  },
  {
    cible: "#map",
    emoji: "🗺️",
    titre: "La carte et les fiches",
    texte:
      "Touchez un point : photo, description, itinéraire Google Maps/Waze, liens spécialisés. " +
      "Touchez une randonnée ou un GR : son tracé s'épingle en couleur et le bouton 📥 GPX " +
      "l'emporte dans votre GPS.",
  },
  {
    cible: "#btn-add-point",
    emoji: "📍",
    titre: "Vos propres points",
    texte:
      "Le gros bouton vert : un clic, puis un clic sur la carte. Catégorie existante ou " +
      "créée à la volée (nom, icône, couleur) — et l'import de fichiers GPX/KML/CSV fait le reste.",
  },
  {
    cible: "#btn-carnet",
    avant: () => document.getElementById("sidebar").classList.remove("open"),
    emoji: "📖",
    titre: "Le carnet de sorties",
    texte:
      "Un grimoire à feuilleter : chaque lieu marqué « ✓ Fait » y écrit sa page, avec vos notes " +
      "et vos photos. Il vous suit dans TOUS les pays, et se synchronise entre vos appareils.",
  },
  {
    cible: "#btn-oracle",
    avant: () => document.getElementById("sidebar").classList.remove("open"),
    emoji: "🔮",
    titre: "L'Oracle",
    texte:
      "Un code postal, un village ou votre position 📍 : l'Oracle révèle quoi faire autour. " +
      "Gratuit sans clé ; avec une clé API (🔑), il déniche aussi concerts, fêtes et brocantes datées.",
  },
  {
    cible: "#btn-wc",
    avant: () => document.getElementById("sidebar").classList.remove("open"),
    emoji: "🚻",
    titre: "Toilettes & fontaines",
    texte:
      "Dans chaque pays : les toilettes publiques et les points d'eau (fontaines, sources) " +
      "d'OpenStreetMap. Ce bouton n'affiche que celles à moins de 1 km de vous — pratique en ville " +
      "comme en rando.",
  },
  {
    cible: "#btn-home",
    avant: () => document.getElementById("sidebar").classList.add("open"),
    placement: "cote",
    emoji: "🌍",
    titre: "Changer de pays",
    texte:
      "Touchez SpotMap (ou le globe) : la carte du monde revient, choisissez un autre terrain " +
      "de jeu. Carnet, statuts et catégories personnelles vous suivent partout.",
  },
  {
    cible: ".foot-outils",
    avant: () => document.getElementById("sidebar").classList.add("open"),
    placement: "cote",
    emoji: "⚙️",
    titre: "Réglages & outils",
    texte:
      "La grille ⚙️ rassemble tout : export/sauvegarde, installation sur l'écran d'accueil, mode " +
      "nuit, communauté 🧩 (importer ou partager des catégories), fréquentation 📊 et mises à jour. " +
      "À côté : 💡 idées, 🎓 ce tuto, 🗺️ fond de carte. Ça marche aussi hors connexion. " +
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

  const dots = ETAPES.map((_, i) =>
    `<span class="tuto-dot${i === indice ? " actif" : i < indice ? " fait" : ""}"></span>`
  ).join("");
  overlay.innerHTML = `
    <div class="tuto-spot" style="${spot}"></div>
    <div class="tuto-card" role="dialog" aria-labelledby="tuto-titre">
      <div class="tuto-entete">
        <span class="tuto-emoji" aria-hidden="true">${etape.emoji || "✨"}</span>
        <h2 id="tuto-titre">${etape.titre}</h2>
      </div>
      <p>${etape.texte}</p>
      <div class="tuto-dots" aria-label="Étape ${indice + 1} sur ${ETAPES.length}">${dots}</div>
      <div class="tuto-actions">
        <button type="button" class="tuto-skip">Passer</button>
        <span class="tuto-nav">
          ${indice > 0 ? '<button type="button" class="btn btn-secondary tuto-prev" aria-label="Précédent">←</button>' : ""}
          <button type="button" class="btn tuto-next">${indice === ETAPES.length - 1 ? "C'est parti ! 🚀" : "Suivant"}</button>
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
