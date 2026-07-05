/**
 * Le Carnet : journal de sorties façon grimoire.
 *
 * S'alimente tout seul : chaque passage d'un point à « fait » crée une
 * sortie horodatée (voir changerStatut dans app.js), et les notes/photos du
 * carnet par point (details.js) apparaissent aussi. Une ENTRÉE = un lieu à
 * une date donnée ; les pages se REMPLISSENT : plusieurs entrées par page
 * tant qu'il y a la place (pagination mesurée dans une page invisible aux
 * dimensions réelles — les photos ont une hauteur CSS fixe pour que la
 * mesure soit juste avant leur chargement).
 *
 * Couverture cuir, pages jaunies aux imperfections pseudo-aléatoires
 * (déterministes par page), écriture manuscrite. Une page à la fois sur
 * petit écran, double page sur grand. Export PDF via l'impression du
 * navigateur (zone #carnet-print + feuille @media print).
 */

import * as storage from "./storage.js";
import { getTheme } from "./config/themes.js";
import { confirmer, toast } from "./import-export.js";
import { redimensionnerPhoto } from "./details.js";
import { esc } from "./util.js";

let overlay = null;
let cb = {}; // { getPoints, getStatuses, onVoirSurCarte }

let entrees = []; // groupes (lieu, jour) après filtres/tri
let pagesListe = []; // entrées réparties par page : [[entrée, …], …]
let indexPage = 0; // 0 = couverture, 1..n = pages
let animation = false;
let minuterieResize = null;

/** Filtres et tri courants (réinitialisés à chaque ouverture du carnet). */
const vue = { recherche: "", tri: "date", favoris: false, activite: null };

/** Thème du carnet : prédéfini (grimoire, voyage, nuit) ou personnalisé
 *  avec les photos de l'utilisateur (couverture et fond de page).
 *  `logo` est INDÉPENDANT du thème : médaillon sur la plaque de couverture. */
let themeCarnet = { theme: "grimoire", couverture: null, page: null, logo: null };

async function chargerThemeCarnet() {
  const enregistre = await storage.getCarnetTheme().catch(() => null);
  if (enregistre) themeCarnet = enregistre;
}

function appliquerThemeCarnet() {
  overlay.classList.remove("carnet-theme-voyage", "carnet-theme-nuit", "carnet-couv-perso", "carnet-page-perso");
  const t = themeCarnet.theme;
  if (t === "voyage" || t === "nuit") overlay.classList.add(`carnet-theme-${t}`);
  if (t === "perso") {
    // Chaque image est indépendante : sans photo, l'élément garde le
    // style Grimoire (les classes ne sont posées que si l'image existe)
    if (themeCarnet.couverture) {
      overlay.classList.add("carnet-couv-perso");
      overlay.style.setProperty("--image-couverture", `url(${themeCarnet.couverture})`);
    }
    if (themeCarnet.page) {
      overlay.classList.add("carnet-page-perso");
      overlay.style.setProperty("--image-page", `url(${themeCarnet.page})`);
    }
  }
}

const MOIS_JOURS = { weekday: "long", day: "numeric", month: "long", year: "numeric" };

export function initCarnet(callbacks) {
  cb = callbacks;
  overlay = document.getElementById("carnet-overlay");
  // Ne PAS passer ouvrirCarnet directement : l'événement de clic serait
  // pris pour le paramètre `activite` (carnet filtré sur un lieu fantôme)
  document.getElementById("btn-carnet").addEventListener("click", () => ouvrirCarnet());

  document.addEventListener("keydown", (e) => {
    if (overlay.hidden) return;
    if (e.key === "Escape") fermerCarnet();
    if (e.key === "ArrowRight") tourner(1);
    if (e.key === "ArrowLeft") tourner(-1);
  });

  // La répartition dépend de la taille des pages : on re-pagine au
  // redimensionnement (rotation du téléphone, fenêtre redimensionnée…)
  window.addEventListener("resize", () => {
    if (overlay.hidden) return;
    clearTimeout(minuterieResize);
    minuterieResize = setTimeout(async () => {
      paginer();
      if (indexPage > pagesListe.length) indexPage = Math.max(1, pagesListe.length);
      rendre();
    }, 250);
  });
}

export async function ouvrirCarnet(activite = null) {
  // Jamais d'échec silencieux : si quelque chose casse, on le dit.
  try {
    vue.recherche = "";
    vue.favoris = false;
    vue.activite = activite;
    await chargerThemeCarnet();
    await construireEntrees();
    indexPage = 0; // toujours la couverture d'abord
    batirSquelette();
    appliquerThemeCarnet();
    overlay.hidden = false; // la mesure des pages exige une mise en page réelle
    paginer();
    rendre();
  } catch (e) {
    console.error("Ouverture du carnet impossible :", e);
    toast("Impossible d'ouvrir le carnet — rechargez la page et réessayez.");
  }
}

/** Ouvre le carnet directement sur les sorties d'un lieu (depuis la fiche). */
export async function ouvrirCarnetPourPoint(pointId) {
  await ouvrirCarnet(pointId);
}

function fermerCarnet() {
  overlay.hidden = true;
  overlay.textContent = "";
}

/* ------------------------------------------------------------------ */
/* Données : sorties + notes regroupées par (lieu, jour)                */
/* ------------------------------------------------------------------ */

async function construireEntrees() {
  const sorties = await storage.seedSortiesDepuisStatuts();
  const journaux = await storage.getAllJournals().catch(() => ({}));
  const statuses = cb.getStatuses();
  const parId = new Map(cb.getPoints().map((f) => [f.properties.id, f]));

  const groupes = new Map();
  const obtenir = (pointId, date) => {
    const jour = date ? String(date).slice(0, 10) : "inconnue";
    const cle = `${pointId}|${jour}`;
    if (!groupes.has(cle)) {
      groupes.set(cle, { cle, pointId, jour, date: date || null, sorties: [], notes: [] });
    }
    const g = groupes.get(cle);
    if (date && (!g.date || date > g.date)) g.date = date;
    return g;
  };

  for (const s of sorties) obtenir(s.pointId, s.date).sorties.push(s);
  for (const [pointId, notes] of Object.entries(journaux)) {
    for (const e of notes) obtenir(pointId, e.date).notes.push(e);
  }

  let liste = [...groupes.values()].filter((g) => parId.has(g.pointId));
  for (const g of liste) {
    g.feature = parId.get(g.pointId);
    g.nom = g.feature.properties.name;
    g.theme = getTheme(g.feature.properties.theme);
    g.favori = statuses[g.pointId] === "favori";
  }

  // Nombre d'entrées par lieu (pour « toutes mes sorties ici »), calculé
  // AVANT les filtres pour rester exact quel que soit l'affichage
  const parLieu = new Map();
  for (const g of liste) parLieu.set(g.pointId, (parLieu.get(g.pointId) || 0) + 1);
  for (const g of liste) g.nbEntreesLieu = parLieu.get(g.pointId) || 1;

  if (vue.activite) liste = liste.filter((g) => g.pointId === vue.activite);
  if (vue.favoris) liste = liste.filter((g) => g.favori);
  if (vue.recherche) {
    const q = normaliser(vue.recherche);
    liste = liste.filter(
      (g) =>
        normaliser(g.nom).includes(q) ||
        normaliser(g.theme.label).includes(q) ||
        g.notes.some((n) => normaliser(n.text || "").includes(q))
    );
  }

  // Dates inconnues en fin de livre (les plus anciennes pages) ;
  // tri « catégorie » : par catégorie puis du plus récent au plus ancien.
  const parDate = (a, b) => {
    if (!a.date && !b.date) return a.nom.localeCompare(b.nom);
    if (!a.date) return 1;
    if (!b.date) return -1;
    return b.date.localeCompare(a.date);
  };
  liste.sort(
    vue.tri === "categorie"
      ? (a, b) => a.theme.label.localeCompare(b.theme.label) || parDate(a, b)
      : parDate
  );

  entrees = liste;
}

function normaliser(texte) {
  return String(texte)
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/* ------------------------------------------------------------------ */
/* Pagination : on remplit chaque page tant qu'il y a la place          */
/* ------------------------------------------------------------------ */

function doublePage() {
  return window.innerWidth >= 900;
}

function paginer() {
  const livre = overlay.querySelector(".carnet-livre");
  if (!livre) {
    pagesListe = entrees.map((g) => [g]);
    return;
  }
  // Page de mesure invisible, aux dimensions exactes d'une vraie page
  // (même structure livre-ouvert → même géométrie, par construction)
  const mesure = document.createElement("div");
  mesure.className = "livre-ouvert carnet-mesure" + (doublePage() ? " double" : "");
  mesure.innerHTML = doublePage()
    ? '<div class="carnet-pages double"><article class="page-carnet"></article><article class="page-carnet"></article></div>'
    : '<div class="carnet-pages"><article class="page-carnet"></article></div>';
  livre.appendChild(mesure);
  const page = mesure.querySelector(".page-carnet");
  const hauteurMax = page.clientHeight;

  pagesListe = [];
  let courante = [];
  const bac = document.createElement("div");
  for (const g of entrees) {
    bac.innerHTML = htmlEntree(g);
    const bloc = bac.firstElementChild;
    page.appendChild(bloc);
    if (page.scrollHeight > hauteurMax + 2 && courante.length) {
      // Déborde : l'entrée ouvre la page suivante (seule sur sa page si
      // elle est trop grande à elle seule — la page défile alors).
      bloc.remove();
      pagesListe.push(courante);
      courante = [];
      page.textContent = "";
      bac.innerHTML = htmlEntree(g);
      page.appendChild(bac.firstElementChild);
    }
    courante.push(g);
  }
  if (courante.length) pagesListe.push(courante);
  mesure.remove();
}

/* ------------------------------------------------------------------ */
/* Squelette de l'interface                                             */
/* ------------------------------------------------------------------ */

function batirSquelette() {
  overlay.innerHTML = `
    <div class="carnet-boite">
      <div class="carnet-barre">
        <input type="search" class="carnet-recherche" placeholder="Rechercher une sortie…"
               aria-label="Rechercher dans le carnet">
        <select class="carnet-tri" aria-label="Trier le carnet">
          <option value="date">Par date</option>
          <option value="categorie">Par catégorie</option>
        </select>
        <button type="button" class="carnet-favoris" aria-pressed="false"
                title="N'afficher que les favoris">♥</button>
        <button type="button" class="carnet-theme" title="Personnaliser le carnet"
                aria-label="Personnaliser le carnet">🎨</button>
        <button type="button" class="carnet-fermer" title="Fermer le carnet"
                aria-label="Fermer le carnet">✕</button>
      </div>
      <div class="carnet-bandeau-activite" hidden>
        <span class="bandeau-texte"></span>
        <button type="button" class="carnet-bouton carnet-refait">＋ J'y suis retourné</button>
        <button type="button" class="carnet-bouton carnet-retour">↩ Tout le carnet</button>
      </div>
      <div class="carnet-scene">
        <button type="button" class="carnet-fleche carnet-prec" aria-label="Page précédente">‹</button>
        <div class="carnet-livre"></div>
        <button type="button" class="carnet-fleche carnet-suiv" aria-label="Page suivante">›</button>
      </div>
      <p class="carnet-pied"></p>
    </div>`;

  overlay.querySelector(".carnet-fermer").addEventListener("click", fermerCarnet);
  overlay.querySelector(".carnet-prec").addEventListener("click", () => tourner(-1));
  overlay.querySelector(".carnet-suiv").addEventListener("click", () => tourner(1));
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) fermerCarnet(); // clic sur le voile sombre
  });

  const relancer = async () => {
    await construireEntrees();
    paginer();
    indexPage = pagesListe.length ? 1 : 0;
    rendre();
  };

  const recherche = overlay.querySelector(".carnet-recherche");
  recherche.addEventListener("input", () => {
    vue.recherche = recherche.value.trim();
    relancer();
  });
  overlay.querySelector(".carnet-tri").addEventListener("change", (e) => {
    vue.tri = e.target.value;
    relancer();
  });
  overlay.querySelector(".carnet-favoris").addEventListener("click", (e) => {
    vue.favoris = !vue.favoris;
    e.currentTarget.setAttribute("aria-pressed", String(vue.favoris));
    e.currentTarget.classList.toggle("actif", vue.favoris);
    relancer();
  });
  overlay.querySelector(".carnet-retour").addEventListener("click", () => {
    vue.activite = null;
    relancer();
  });
  overlay.querySelector(".carnet-refait").addEventListener("click", async () => {
    if (!vue.activite) return;
    await storage.addSortie(vue.activite);
    toast("Sortie d'aujourd'hui ajoutée au carnet !");
    relancer();
  });
  overlay.querySelector(".carnet-theme").addEventListener("click", ouvrirDialogueTheme);

  // Feuilletage au doigt
  const livre = overlay.querySelector(".carnet-livre");
  let departX = null;
  livre.addEventListener("touchstart", (e) => (departX = e.touches[0].clientX), { passive: true });
  livre.addEventListener(
    "touchend",
    (e) => {
      if (departX === null) return;
      const delta = e.changedTouches[0].clientX - departX;
      departX = null;
      if (Math.abs(delta) > 45) tourner(delta < 0 ? 1 : -1);
    },
    { passive: true }
  );
}

/* ------------------------------------------------------------------ */
/* Rendu : couverture ou page(s) courante(s)                            */
/* ------------------------------------------------------------------ */

function rendre() {
  const livre = overlay.querySelector(".carnet-livre");
  const pied = overlay.querySelector(".carnet-pied");
  const bandeau = overlay.querySelector(".carnet-bandeau-activite");

  bandeau.hidden = !vue.activite;
  if (vue.activite) {
    // Le nom vient du point lui-même : le bandeau reste juste même quand
    // le lieu n'a encore aucune sortie (arrivée depuis la fiche)
    const feature = cb.getPoints().find((f) => f.properties.id === vue.activite);
    const nom = feature ? feature.properties.name : "";
    const icone = feature ? getTheme(feature.properties.theme).icon : "📖";
    bandeau.querySelector(".bandeau-texte").textContent =
      `${icone} ${nom} — ${entrees.length} sortie(s)`;
  }

  if (indexPage === 0) {
    livre.innerHTML = htmlCouverture();
    livre.querySelector(".carnet-couverture").addEventListener("click", () => tourner(1));
    pied.textContent = pagesListe.length
      ? `${entrees.length} sortie(s) sur ${pagesListe.length} page(s) — touchez la couverture pour ouvrir`
      : vue.activite
      ? "Aucune sortie ici pour l'instant — marquez ce lieu « ✓ Fait » ou ajoutez-y une note !"
      : "Votre carnet attend sa première sortie : marquez une activité « ✓ Fait » !";
  } else {
    const morceaux = [htmlPage(indexPage)];
    if (doublePage()) {
      morceaux.push(
        indexPage + 1 <= pagesListe.length ? htmlPage(indexPage + 1) : '<div class="page-carnet page-vide"></div>'
      );
    }
    // Le livre ouvert : couverture de cuir dépassant sous le bloc de pages,
    // l'épaisseur vient des tranches en box-shadow.
    livre.innerHTML = `
      <div class="livre-ouvert${doublePage() ? " double" : ""}">
        <div class="carnet-pages${doublePage() ? " double" : ""}">${morceaux.join("")}</div>
      </div>`;
    brancherPages(livre);
    pied.textContent =
      doublePage() && indexPage + 1 <= pagesListe.length
        ? `pages ${indexPage}-${indexPage + 1} / ${pagesListe.length}`
        : `page ${indexPage} / ${pagesListe.length}`;
  }

  overlay.querySelector(".carnet-prec").disabled = indexPage === 0;
  // Depuis la couverture, une seule page suffit pour ouvrir (même en double
  // page) ; ensuite, on bloque quand la dernière page est déjà affichée.
  overlay.querySelector(".carnet-suiv").disabled =
    indexPage === 0 ? pagesListe.length === 0 : indexPage + (doublePage() ? 2 : 1) > pagesListe.length;
}

/** Tourne la ou les pages avec l'animation de feuilletage (pli au dos). */
function tourner(sens) {
  if (animation) return;
  const pas = indexPage === 0 ? 1 : doublePage() ? 2 : 1;
  const cible = Math.max(0, indexPage + sens * pas);
  if (cible === indexPage || (sens > 0 && cible > pagesListe.length)) return;
  const livre = overlay.querySelector(".carnet-livre");
  animation = true;
  livre.classList.add(sens > 0 ? "plie-avant" : "plie-arriere");
  setTimeout(() => {
    indexPage = cible;
    rendre();
    livre.classList.remove("plie-avant", "plie-arriere");
    livre.classList.add(sens > 0 ? "deplie-avant" : "deplie-arriere");
    setTimeout(() => {
      livre.classList.remove("deplie-avant", "deplie-arriere");
      animation = false;
    }, 300);
  }, 300);
}

/* ------------------------------------------------------------------ */
/* Couverture : cuir vieilli, carte gravée en relief                    */
/* ------------------------------------------------------------------ */

function htmlCouverture() {
  // Fidèle à la référence : cuir ouvragé de volutes, plaque de laiton
  // rivetée gravée d'une rose des vents, craquelures de vieille carte,
  // écusson — le titre est discret, sous la plaque.
  const logo = themeCarnet.logo
    ? `<img class="couv-logo" src="${themeCarnet.logo}" alt="" aria-hidden="true">`
    : "";
  return `
    <div class="carnet-couverture${themeCarnet.logo ? " couv-avec-logo" : ""}" role="button"
         tabindex="0" aria-label="Ouvrir le carnet">
      ${logo}
      <i class="couv-fermoir" aria-hidden="true"></i>
      <i class="couv-coin coin-hg" aria-hidden="true"></i>
      <i class="couv-coin coin-hd" aria-hidden="true"></i>
      <i class="couv-coin coin-bg" aria-hidden="true"></i>
      <i class="couv-coin coin-bd" aria-hidden="true"></i>
      <div class="couv-plaque" aria-hidden="true">
        <svg class="plaque-grave" viewBox="0 0 240 240">
          <g class="fissures">
            <path d="M18 58 L64 82 L92 74 M148 26 L158 72 L204 94 M26 172 L78 150 L108 166 M186 204 L172 158 L216 138 M60 222 L84 198 L122 206"/>
          </g>
          <g class="rose">
            <circle cx="120" cy="120" r="64"/>
            <circle cx="120" cy="120" r="54" class="fin"/>
            <circle cx="120" cy="120" r="13" class="fin"/>
            <path class="plein" d="M120 32 L129 111 L120 120 L111 111 Z M120 208 L129 129 L120 120 L111 129 Z M32 120 L111 129 L120 120 L111 111 Z M208 120 L129 111 L120 120 L129 129 Z"/>
            <path class="plein demi" d="M78 78 L112 112 L120 120 L106 106 Z M162 78 L128 112 L120 120 L134 106 Z M78 162 L112 128 L120 120 L106 134 Z M162 162 L128 128 L120 120 L134 134 Z"/>
          </g>
          <g class="pointilles">
            <path d="M120 14 V30 M120 210 V226 M14 120 H30 M210 120 H226 M46 46 L60 60 M194 46 L180 60 M46 194 L60 180 M194 194 L180 180"/>
          </g>
          <g class="lettres">
            <text x="120" y="27">N</text><text x="120" y="235">S</text>
            <text x="18" y="126">W</text><text x="222" y="126">E</text>
          </g>
          <path class="ecusson" d="M198 32 l16 7 v15 c0 9 -7 14 -16 19 c-9 -5 -16 -10 -16 -19 v-15 Z m-16 14 h32 m-16 -12 v24"/>
        </svg>
        <i class="rivet r-hg"></i><i class="rivet r-hd"></i><i class="rivet r-bg"></i><i class="rivet r-bd"></i>
      </div>
      <h2 class="couv-titre">Carnet de sorties</h2>
      <p class="couv-indice">Toucher pour ouvrir</p>
    </div>`;
}

/* ------------------------------------------------------------------ */
/* Entrées et pages                                                     */
/* ------------------------------------------------------------------ */

/** Générateur pseudo-aléatoire déterministe : les imperfections d'une page
 *  (taches, usure, inclinaison) sont stables d'un affichage à l'autre. */
function graine(texte) {
  let h = 2166136261;
  for (let i = 0; i < texte.length; i++) {
    h ^= texte.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return () => {
    h = Math.imul(h ^ (h >>> 15), 2246822519);
    h = Math.imul(h ^ (h >>> 13), 3266489917);
    return ((h ^= h >>> 16) >>> 0) / 4294967296;
  };
}

function encreAleatoire(alea) {
  // Papier sombre = craie : soit le thème Nuit (manuel), soit le Grimoire
  // quand l'application est en mode nuit (le grimoire suit le mode jour/nuit).
  const sombre =
    themeCarnet.theme === "nuit" ||
    (themeCarnet.theme === "grimoire" && document.body.classList.contains("mode-nuit"));
  if (sombre) {
    // craie et ivoire sur papier sombre
    return `hsl(${(38 + alea() * 14).toFixed(0)}, ${(26 + alea() * 18).toFixed(0)}%, ${(76 + alea() * 10).toFixed(0)}%)`;
  }
  // encre BLEUE (plume) — couleur de base de l'écriture
  return `hsl(${(210 + alea() * 22).toFixed(0)}, ${(38 + alea() * 20).toFixed(0)}%, ${(22 + alea() * 9).toFixed(0)}%)`;
}

/** Une entrée : un lieu à une date, avec ses notes/photos et ses actions.
 *  `pourImpression` retire les boutons (export PDF). */
function htmlEntree(g, pourImpression = false) {
  const alea = graine(g.cle);
  const dateLisible = g.date
    ? new Date(g.date).toLocaleDateString("fr-FR", MOIS_JOURS)
    : "Date inconnue";
  const sortieFaite = g.sorties.length > 0;
  const sortieId = sortieFaite ? g.sorties[0].id : null;

  const photos = g.notes
    .filter((n) => n.photo)
    .map((n) => {
      const img = `<img class="page-photo" src="${n.photo}" alt="Photo de ${esc(g.nom)}" loading="lazy" style="transform:rotate(${((alea() - 0.5) * 4).toFixed(1)}deg)">`;
      return pourImpression
        ? img
        : `<span class="page-photo-bloc">${img}<button type="button" class="photo-suppr" data-note="${esc(n.id)}" data-point="${esc(g.pointId)}" title="Retirer la photo" aria-label="Retirer la photo">✕</button></span>`;
    })
    .join("");
  const notes = g.notes
    .filter((n) => n.text)
    .map((n) =>
      pourImpression
        ? `<p class="page-note">${esc(n.text)}</p>`
        : `<div class="page-note-bloc" data-note="${esc(n.id)}" data-point="${esc(g.pointId)}"><p class="page-note">${esc(n.text)}</p><button type="button" class="note-editer" title="Modifier la note" aria-label="Modifier la note">✎</button></div>`
    )
    .join("");

  // Ajout d'une note ou d'une photo directement dans le carnet (sur ce lieu,
  // à cette date). Absent de l'export PDF.
  const dateAjout = g.date ? esc(g.date) : "";
  const ajout = pourImpression
    ? ""
    : `<div class="entree-ajout">
        <button type="button" class="page-action ajout-note" data-point="${esc(g.pointId)}" data-date="${dateAjout}">＋ Note</button>
        <label class="page-action ajout-photo">＋ Photo<input type="file" accept="image/*" hidden data-point="${esc(g.pointId)}" data-date="${dateAjout}"></label>
      </div>`;

  const actions = pourImpression
    ? ""
    : `<div class="entree-actions">
        <button type="button" class="page-action page-voir" data-cle="${esc(g.cle)}">🗺 Voir sur la carte</button>
        ${g.nbEntreesLieu > 1 && !vue.activite
          ? `<button type="button" class="page-action page-occurrences" data-point="${esc(g.pointId)}">📖 Toutes mes sorties ici (${g.nbEntreesLieu})</button>`
          : ""}
        ${sortieId
          ? `<button type="button" class="page-action page-suppr" data-sortie="${esc(sortieId)}" data-nom="${esc(g.nom)}" title="Retirer cette sortie du carnet">🗑</button>`
          : ""}
      </div>`;

  // Chaque entrée a SA teinte d'encre : un carnet écrit au fil des ans n'a
  // jamais deux encres identiques. La gamme dépend du thème (sépia pour le
  // grimoire, bleu nuit pour le carnet de voyage, craie pour la nuit).
  const encre = encreAleatoire(alea);

  return `
    <section class="entree" style="--encre:${encre}">
      <header class="page-entete">
        <time>${esc(dateLisible)}</time>
        <span class="page-cat">${g.theme.icon} ${esc(g.theme.label)}</span>
      </header>
      <h3 class="page-titre">${esc(g.nom)} ${g.favori ? '<span class="page-coeur" title="En favori">♥</span>' : ""}</h3>
      ${sortieFaite ? '<p class="page-mention">✓ Sortie faite</p>' : ""}
      ${g.date === null && sortieId && !pourImpression
        ? `<p class="page-fixer-date">Faite avant le carnet —
             <label>préciser la date : <input type="date" class="page-date-input" data-sortie="${esc(sortieId)}"
               max="${new Date().toISOString().slice(0, 10)}"></label></p>`
        : ""}
      ${photos ? `<div class="page-photos">${photos}</div>` : ""}
      ${notes}
      ${ajout}
      ${actions}
    </section>`;
}

function htmlPage(numero) {
  const groupe = pagesListe[numero - 1];
  const alea = graine(groupe.map((g) => g.cle).join("¤") + numero);
  // Quatre papiers différents (même esprit) : le tirage est stable par page
  const variante = 1 + Math.floor(alea() * 4);

  // Imperfections : parfois présentes, parfois non — jamais identiques
  let imperfections = "";
  const nbTaches = Math.floor(alea() * 4); // 0 à 3 taches
  for (let i = 0; i < nbTaches; i++) {
    const taille = 14 + alea() * 60;
    imperfections += `<i class="page-tache" style="left:${(alea() * 86).toFixed(1)}%;top:${(alea() * 88).toFixed(1)}%;width:${taille.toFixed(0)}px;height:${(taille * (0.6 + alea() * 0.8)).toFixed(0)}px;opacity:${(0.05 + alea() * 0.1).toFixed(2)};transform:rotate(${(alea() * 360).toFixed(0)}deg)"></i>`;
  }
  if (alea() < 0.3) {
    imperfections += `<i class="page-trou" style="left:${(6 + alea() * 84).toFixed(1)}%;top:${(6 + alea() * 84).toFixed(1)}%;transform:scale(${(0.6 + alea() * 0.9).toFixed(2)})"></i>`;
  }
  if (alea() < 0.45) imperfections += `<i class="page-usure coin-${alea() < 0.5 ? "bd" : "hg"}"></i>`;
  // Pétales de rose séchés et poudre d'or, comme sur la référence :
  // parfois là, parfois non, jamais aux mêmes endroits
  if (alea() < 0.5) {
    const nb = 1 + Math.floor(alea() * 2);
    for (let i = 0; i < nb; i++) {
      imperfections += `<i class="page-petale" style="left:${(6 + alea() * 84).toFixed(1)}%;top:${(6 + alea() * 84).toFixed(1)}%;transform:rotate(${(alea() * 360).toFixed(0)}deg) scale(${(0.7 + alea() * 0.6).toFixed(2)})"></i>`;
    }
  }
  if (alea() < 0.4) {
    imperfections += `<i class="page-poudre" style="left:${(alea() * 78).toFixed(1)}%;top:${(alea() * 84).toFixed(1)}%;width:${(26 + alea() * 46).toFixed(0)}px;height:${(20 + alea() * 30).toFixed(0)}px;transform:rotate(${(alea() * 180).toFixed(0)}deg)"></i>`;
  }

  return `
    <article class="page-carnet page-v${variante}" style="--pente:${((alea() - 0.5) * 1.2).toFixed(2)}deg">
      ${imperfections}
      ${groupe.map((g) => htmlEntree(g)).join("")}
      <span class="page-numero">— ${numero} —</span>
    </article>`;
}

function brancherPages(livre) {
  livre.querySelectorAll(".page-voir").forEach((b) =>
    b.addEventListener("click", () => {
      const g = entrees.find((p) => p.cle === b.dataset.cle);
      if (!g) return;
      fermerCarnet();
      cb.onVoirSurCarte?.(g.feature);
    })
  );
  livre.querySelectorAll(".page-occurrences").forEach((b) =>
    b.addEventListener("click", async () => {
      vue.activite = b.dataset.point;
      await construireEntrees();
      paginer();
      indexPage = pagesListe.length ? 1 : 0;
      rendre();
    })
  );
  livre.querySelectorAll(".page-suppr").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!(await confirmer(`Retirer cette sortie à « ${b.dataset.nom} » du carnet ?`))) return;
      await storage.deleteSortie(b.dataset.sortie);
      await construireEntrees();
      paginer();
      if (indexPage > pagesListe.length) indexPage = Math.max(pagesListe.length, 0);
      rendre();
    })
  );
  livre.querySelectorAll(".page-date-input").forEach((input) =>
    input.addEventListener("change", async () => {
      if (!input.value) return;
      await storage.updateSortie(input.dataset.sortie, {
        date: new Date(input.value + "T12:00:00").toISOString(),
      });
      toast("Date enregistrée !");
      await construireEntrees();
      paginer();
      indexPage = 1;
      rendre();
    })
  );

  // --- Édition dans le carnet : modifier une note, en ajouter, gérer les photos
  livre.querySelectorAll(".note-editer").forEach((b) =>
    b.addEventListener("click", () => {
      const bloc = b.closest(".page-note-bloc");
      ouvrirEditeurNote(
        bloc,
        bloc.dataset.point,
        bloc.dataset.note,
        bloc.querySelector(".page-note").textContent,
        null
      );
    })
  );
  livre.querySelectorAll(".ajout-note").forEach((b) =>
    b.addEventListener("click", () => {
      const section = b.closest(".entree");
      const bloc = document.createElement("div");
      bloc.className = "page-note-bloc";
      section.insertBefore(bloc, b.closest(".entree-ajout"));
      ouvrirEditeurNote(bloc, b.dataset.point, null, "", b.dataset.date || null);
    })
  );
  livre.querySelectorAll(".ajout-photo input").forEach((inp) =>
    inp.addEventListener("change", async () => {
      const fichier = inp.files[0];
      if (!fichier) return;
      try {
        const photo = await redimensionnerPhoto(fichier);
        await storage.addJournalEntry(inp.dataset.point, {
          id: `j-${Date.now().toString(36)}`,
          date: inp.dataset.date || null,
          text: "",
          photo,
        });
        toast("Photo ajoutée au carnet !");
        await rafraichirEdition();
      } catch {
        toast("Photo illisible — essayez-en une autre.");
      }
    })
  );
  livre.querySelectorAll(".photo-suppr").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!(await confirmer("Retirer cette photo du carnet ?"))) return;
      const pointId = b.dataset.point;
      const note = b.dataset.note;
      // Si la note contient aussi du texte, on ne retire QUE la photo
      const entree = (await storage.getJournal(pointId)).find((e) => e.id === note);
      if (entree && entree.text) await storage.updateJournalEntry(pointId, note, { photo: null });
      else await storage.deleteJournalEntry(pointId, note);
      await rafraichirEdition();
    })
  );
}

/** Réaffiche le carnet après une modification (reste sur une page valide). */
async function rafraichirEdition() {
  const avant = indexPage;
  await construireEntrees();
  paginer();
  indexPage = pagesListe.length ? Math.min(Math.max(1, avant), pagesListe.length) : 0;
  rendre();
}

/** Éditeur inline d'une note : `noteId` null = création (à la date `dateAjout`). */
function ouvrirEditeurNote(bloc, pointId, noteId, texteInitial, dateAjout) {
  bloc.classList.add("note-edition");
  bloc.innerHTML = `
    <textarea class="note-edit-champ" rows="3" placeholder="Votre note…">${esc(texteInitial)}</textarea>
    <div class="note-edit-actions">
      <button type="button" class="page-action note-annuler">Annuler</button>
      <button type="button" class="page-action note-ok">✓ Enregistrer</button>
    </div>`;
  const champ = bloc.querySelector(".note-edit-champ");
  champ.focus();
  champ.setSelectionRange(champ.value.length, champ.value.length);
  bloc.querySelector(".note-annuler").addEventListener("click", () => rendre());
  bloc.querySelector(".note-ok").addEventListener("click", async () => {
    const texte = champ.value.trim();
    if (noteId) {
      if (texte) await storage.updateJournalEntry(pointId, noteId, { text: texte });
      else await storage.deleteJournalEntry(pointId, noteId);
    } else if (texte) {
      await storage.addJournalEntry(pointId, {
        id: `j-${Date.now().toString(36)}`,
        date: dateAjout || null,
        text: texte,
        photo: null,
      });
    } else {
      rendre(); // rien saisi : on annule proprement
      return;
    }
    await rafraichirEdition();
  });
}

/* ------------------------------------------------------------------ */
/* Personnalisation : thèmes prédéfinis + photos de l'utilisateur       */
/* ------------------------------------------------------------------ */

function ouvrirDialogueTheme() {
  const dlg = document.getElementById("carnet-theme-dialog");
  // Brouillon de travail : rien n'est enregistré avant « Appliquer »
  const brouillon = { ...themeCarnet };

  const zonePerso = dlg.querySelector(".ct-perso");
  const etatCouv = dlg.querySelector(".ct-couv-etat");
  const etatPage = dlg.querySelector(".ct-page-etat");
  const etatLogo = dlg.querySelector(".ct-logo-etat");
  const majEtat = () => {
    zonePerso.hidden = brouillon.theme !== "perso";
    etatCouv.textContent = brouillon.couverture ? "✓ photo choisie" : "aucune photo";
    etatPage.textContent = brouillon.page ? "✓ photo choisie" : "aucune photo";
    etatLogo.textContent = brouillon.logo ? "✓ logo choisi" : "emblème d'origine";
    dlg.querySelector(".ct-logo-retirer").hidden = !brouillon.logo;
  };

  for (const radio of dlg.querySelectorAll('input[name="ct-theme"]')) {
    radio.checked = radio.value === brouillon.theme;
    radio.onchange = () => {
      brouillon.theme = radio.value;
      majEtat();
    };
  }

  const brancherPhoto = (input, champ) => {
    input.value = "";
    input.onchange = async () => {
      const fichier = input.files[0];
      if (!fichier) return;
      try {
        brouillon[champ] = await redimensionnerPhoto(fichier);
      } catch {
        toast("Photo illisible — essayez-en une autre.");
      }
      majEtat();
    };
  };
  brancherPhoto(dlg.querySelector(".ct-photo-couv"), "couverture");
  brancherPhoto(dlg.querySelector(".ct-photo-page"), "page");
  brancherPhoto(dlg.querySelector(".ct-photo-logo"), "logo");
  dlg.querySelector(".ct-logo-retirer").onclick = () => {
    brouillon.logo = null;
    majEtat();
  };

  dlg.querySelector(".ct-annuler").onclick = () => dlg.close();
  dlg.querySelector(".ct-appliquer").onclick = async () => {
    themeCarnet = brouillon;
    await storage.saveCarnetTheme(themeCarnet).catch(() => {});
    dlg.close();
    appliquerThemeCarnet();
    rendre(); // les encres et la couverture dépendent du thème
    toast("Thème du carnet appliqué !");
  };

  majEtat();
  dlg.showModal();
}

/* ------------------------------------------------------------------ */
/* Export PDF : zone d'impression + dialogue d'impression du navigateur */
/* (« Enregistrer au format PDF » — aucune dépendance)                  */
/* ------------------------------------------------------------------ */

export async function exporterCarnetPDF() {
  const memo = { ...vue };
  vue.recherche = "";
  vue.favoris = false;
  vue.activite = null;
  vue.tri = "date";
  await construireEntrees();
  Object.assign(vue, memo);
  if (!entrees.length) {
    toast("Carnet vide : rien à exporter pour le moment.");
    return;
  }

  let zone = document.getElementById("carnet-print");
  if (!zone) {
    zone = document.createElement("div");
    zone.id = "carnet-print";
    document.body.appendChild(zone);
  }
  const date = new Date().toLocaleDateString("fr-FR", MOIS_JOURS);
  zone.innerHTML =
    `<div class="print-garde"><h1>Carnet de sorties</h1>
      <p>Carte Outdoor — ${entrees.length} sortie(s), exporté le ${esc(date)}</p></div>` +
    entrees.map((g) => htmlEntree(g, true)).join("");

  // La zone est vidée après impression (libère les photos en mémoire)
  window.addEventListener("afterprint", () => (zone.textContent = ""), { once: true });
  window.print();
}
