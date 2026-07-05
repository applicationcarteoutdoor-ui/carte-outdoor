/**
 * Le Carnet : journal de sorties façon grimoire.
 *
 * S'alimente tout seul : chaque passage d'un point à « fait » crée une
 * sortie horodatée (voir changerStatut dans app.js), et les notes/photos du
 * carnet par point (details.js) apparaissent aussi. Une PAGE = un lieu à une
 * date donnée (sortie « fait » et/ou notes du même jour).
 *
 * Le livre s'ouvre plein écran par-dessus la carte : couverture cuir,
 * pages jaunies aux imperfections pseudo-aléatoires (déterministes par page :
 * elles ne changent pas d'un feuilletage à l'autre), écriture manuscrite.
 * Une page à la fois sur petit écran, double page sur grand écran.
 */

import * as storage from "./storage.js";
import { getTheme } from "./config/themes.js";
import { confirmer, toast } from "./import-export.js";

let overlay = null;
let cb = {}; // { getPoints, getStatuses, onVoirSurCarte }

let pages = []; // pages du livre après filtres/tri (hors couverture)
let indexPage = 0; // 0 = couverture, 1..n = pages
let animation = false;

/** Filtres et tri courants (réinitialisés à chaque ouverture du carnet). */
const vue = { recherche: "", tri: "date", favoris: false, activite: null };

const MOIS_JOURS = { weekday: "long", day: "numeric", month: "long", year: "numeric" };

export function initCarnet(callbacks) {
  cb = callbacks;
  overlay = document.getElementById("carnet-overlay");
  document.getElementById("btn-carnet").addEventListener("click", ouvrirCarnet);

  document.addEventListener("keydown", (e) => {
    if (overlay.hidden) return;
    if (e.key === "Escape") fermerCarnet();
    if (e.key === "ArrowRight") tourner(1);
    if (e.key === "ArrowLeft") tourner(-1);
  });
}

export async function ouvrirCarnet() {
  // Jamais d'échec silencieux : si quelque chose casse, on le dit.
  try {
    vue.recherche = "";
    vue.favoris = false;
    vue.activite = null;
    await construirePages();
    indexPage = 0; // toujours la couverture d'abord
    batirSquelette();
    rendre();
    overlay.hidden = false;
  } catch (e) {
    console.error("Ouverture du carnet impossible :", e);
    toast("Impossible d'ouvrir le carnet — rechargez la page et réessayez.");
  }
}

function fermerCarnet() {
  overlay.hidden = true;
  overlay.textContent = "";
}

/* ------------------------------------------------------------------ */
/* Données : sorties + notes regroupées par (lieu, jour)                */
/* ------------------------------------------------------------------ */

async function construirePages() {
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
  for (const [pointId, entrees] of Object.entries(journaux)) {
    for (const e of entrees) obtenir(pointId, e.date).notes.push(e);
  }

  let liste = [...groupes.values()].filter((g) => parId.has(g.pointId));
  for (const g of liste) {
    g.feature = parId.get(g.pointId);
    g.nom = g.feature.properties.name;
    g.theme = getTheme(g.feature.properties.theme);
    g.favori = statuses[g.pointId] === "favori";
  }

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

  // Nombre total de sorties par lieu (pour « autres sorties sur ce lieu »)
  const parLieu = new Map();
  for (const g of [...groupes.values()]) {
    parLieu.set(g.pointId, (parLieu.get(g.pointId) || 0) + 1);
  }
  for (const g of liste) g.nbPagesLieu = parLieu.get(g.pointId) || 1;

  pages = liste;
}

function normaliser(texte) {
  return String(texte)
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase();
}

/* ------------------------------------------------------------------ */
/* Squelette de l'interface                                             */
/* ------------------------------------------------------------------ */

function esc(texte) {
  const div = document.createElement("div");
  div.textContent = texte ?? "";
  return div.innerHTML;
}

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
        <button type="button" class="panel-close carnet-fermer" title="Fermer le carnet"
                aria-label="Fermer le carnet">✕</button>
      </div>
      <div class="carnet-bandeau-activite" hidden>
        <span class="bandeau-texte"></span>
        <button type="button" class="btn btn-secondary carnet-refait">＋ J'y suis retourné</button>
        <button type="button" class="btn btn-secondary carnet-retour">↩ Tout le carnet</button>
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

  const recherche = overlay.querySelector(".carnet-recherche");
  recherche.addEventListener("input", async () => {
    vue.recherche = recherche.value.trim();
    await construirePages();
    indexPage = pages.length ? 1 : 0;
    rendre();
  });
  overlay.querySelector(".carnet-tri").addEventListener("change", async (e) => {
    vue.tri = e.target.value;
    await construirePages();
    indexPage = pages.length ? 1 : 0;
    rendre();
  });
  overlay.querySelector(".carnet-favoris").addEventListener("click", async (e) => {
    vue.favoris = !vue.favoris;
    e.currentTarget.setAttribute("aria-pressed", String(vue.favoris));
    e.currentTarget.classList.toggle("actif", vue.favoris);
    await construirePages();
    indexPage = pages.length ? 1 : 0;
    rendre();
  });
  overlay.querySelector(".carnet-retour").addEventListener("click", async () => {
    vue.activite = null;
    await construirePages();
    indexPage = pages.length ? 1 : 0;
    rendre();
  });
  overlay.querySelector(".carnet-refait").addEventListener("click", async () => {
    if (!vue.activite) return;
    await storage.addSortie(vue.activite);
    toast("Sortie d'aujourd'hui ajoutée au carnet !");
    await construirePages();
    indexPage = 1;
    rendre();
  });

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

function doublePage() {
  return window.innerWidth >= 900;
}

function rendre() {
  const livre = overlay.querySelector(".carnet-livre");
  const pied = overlay.querySelector(".carnet-pied");
  const bandeau = overlay.querySelector(".carnet-bandeau-activite");

  bandeau.hidden = !vue.activite;
  if (vue.activite && pages.length) {
    bandeau.querySelector(".bandeau-texte").textContent =
      `${pages[0].theme.icon} ${pages[0].nom} — ${pages.length} sortie(s)`;
  }

  if (indexPage === 0) {
    livre.innerHTML = htmlCouverture();
    livre.querySelector(".carnet-couverture").addEventListener("click", () => tourner(1));
    pied.textContent = pages.length
      ? `${pages.length} page(s) — touchez la couverture pour ouvrir`
      : "Votre carnet attend sa première sortie : marquez une activité « ✓ Fait » !";
  } else {
    const morceaux = [htmlPage(indexPage)];
    if (doublePage() && indexPage + 1 <= pages.length) morceaux.push(htmlPage(indexPage + 1));
    else if (doublePage()) morceaux.push('<div class="page-carnet page-vide"></div>');
    livre.innerHTML = `<div class="carnet-pages${doublePage() ? " double" : ""}">${morceaux.join("")}</div>`;
    brancherPage(livre);
    pied.textContent = doublePage() && indexPage + 1 <= pages.length
      ? `pages ${indexPage}-${indexPage + 1} / ${pages.length}`
      : `page ${indexPage} / ${pages.length}`;
  }

  overlay.querySelector(".carnet-prec").disabled = indexPage === 0;
  // Depuis la couverture, une seule page suffit pour ouvrir (même en double
  // page) ; ensuite, on bloque quand la dernière page est déjà affichée.
  overlay.querySelector(".carnet-suiv").disabled =
    indexPage === 0 ? pages.length === 0 : indexPage + (doublePage() ? 2 : 1) > pages.length;
}

/** Tourne la ou les pages avec l'animation de feuilletage (pli au dos). */
function tourner(sens) {
  if (animation) return;
  const pas = indexPage === 0 ? 1 : doublePage() ? 2 : 1;
  const cible = Math.max(0, indexPage + sens * pas);
  if (cible === indexPage || (sens > 0 && cible > pages.length)) return;
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
    }, 240);
  }, 240);
}

/* ------------------------------------------------------------------ */
/* Couverture : cuir vieilli, carte gravée en relief                    */
/* ------------------------------------------------------------------ */

function htmlCouverture() {
  return `
    <div class="carnet-couverture" role="button" tabindex="0" aria-label="Ouvrir le carnet">
      <div class="couv-cadre">
        <svg class="couv-carte" viewBox="0 0 200 200" aria-hidden="true">
          <path class="grave" d="M30 150 Q60 120 80 130 T130 100 T175 60" fill="none"/>
          <path class="grave" d="M40 60 L55 35 L70 60 Z M60 60 L75 30 L90 60 Z"/>
          <circle class="grave" cx="150" cy="140" r="17" fill="none"/>
          <path class="grave" d="M150 118 L150 162 M128 140 L172 140 M150 123 L155 135 L150 133 L145 135 Z"/>
          <path class="grave" d="M85 132 l3 -7 3 7 M110 115 l3 -7 3 7" fill="none"/>
        </svg>
        <h2 class="couv-titre">Carnet<br>de sorties</h2>
        <p class="couv-sous-titre">Carte Outdoor</p>
      </div>
      <p class="couv-indice">Toucher pour ouvrir</p>
    </div>`;
}

/* ------------------------------------------------------------------ */
/* Pages : une sortie (lieu + jour) par page                            */
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

function htmlPage(numero) {
  const g = pages[numero - 1];
  const alea = graine(g.cle);

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

  const dateLisible = g.date
    ? new Date(g.date).toLocaleDateString("fr-FR", MOIS_JOURS)
    : "Date inconnue";
  const sortieFaite = g.sorties.length > 0;
  const sortieId = sortieFaite ? g.sorties[0].id : null;

  const photos = g.notes
    .filter((n) => n.photo)
    .map((n) => `<img class="page-photo" src="${n.photo}" alt="Photo de ${esc(g.nom)}" loading="lazy" style="transform:rotate(${((alea() - 0.5) * 4).toFixed(1)}deg)">`)
    .join("");
  const notes = g.notes
    .filter((n) => n.text)
    .map((n) => `<p class="page-note">${esc(n.text)}</p>`)
    .join("");

  return `
    <article class="page-carnet" data-cle="${esc(g.cle)}"
             style="--pente:${((alea() - 0.5) * 1.2).toFixed(2)}deg">
      ${imperfections}
      <header class="page-entete">
        <time>${esc(dateLisible)}</time>
        <span class="page-cat" style="--pin-color:${g.theme.color}">${g.theme.icon} ${esc(g.theme.label)}</span>
      </header>
      <h3 class="page-titre">${esc(g.nom)} ${g.favori ? '<span class="page-coeur" title="En favori">♥</span>' : ""}</h3>
      ${sortieFaite ? '<p class="page-mention">✓ Sortie faite</p>' : ""}
      ${g.date === null && sortieId
        ? `<p class="page-fixer-date">Faite avant le carnet —
             <label>préciser la date : <input type="date" class="page-date-input" data-sortie="${esc(sortieId)}"
               max="${new Date().toISOString().slice(0, 10)}"></label></p>`
        : ""}
      ${photos ? `<div class="page-photos">${photos}</div>` : ""}
      ${notes || '<p class="page-note page-note-vide">Aucune note ce jour-là…</p>'}
      <footer class="page-pied">
        <button type="button" class="page-action page-voir" data-cle="${esc(g.cle)}">🗺 Voir sur la carte</button>
        ${g.nbPagesLieu > 1 && !vue.activite
          ? `<button type="button" class="page-action page-occurrences" data-point="${esc(g.pointId)}">📖 Toutes mes sorties ici (${g.nbPagesLieu})</button>`
          : ""}
        ${sortieId
          ? `<button type="button" class="page-action page-suppr" data-sortie="${esc(sortieId)}" data-nom="${esc(g.nom)}" title="Retirer cette sortie du carnet">🗑</button>`
          : ""}
        <span class="page-numero">— ${numero} —</span>
      </footer>
    </article>`;
}

function brancherPage(livre) {
  livre.querySelectorAll(".page-voir").forEach((b) =>
    b.addEventListener("click", () => {
      const g = pages.find((p) => p.cle === b.dataset.cle);
      if (!g) return;
      fermerCarnet();
      cb.onVoirSurCarte?.(g.feature);
    })
  );
  livre.querySelectorAll(".page-occurrences").forEach((b) =>
    b.addEventListener("click", async () => {
      vue.activite = b.dataset.point;
      await construirePages();
      indexPage = pages.length ? 1 : 0;
      rendre();
    })
  );
  livre.querySelectorAll(".page-suppr").forEach((b) =>
    b.addEventListener("click", async () => {
      if (!(await confirmer(`Retirer cette sortie à « ${b.dataset.nom} » du carnet ?`))) return;
      await storage.deleteSortie(b.dataset.sortie);
      await construirePages();
      if (indexPage > pages.length) indexPage = Math.max(pages.length, 0);
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
      await construirePages();
      indexPage = 1;
      rendre();
    })
  );
}
