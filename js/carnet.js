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

let overlay = null;
let cb = {}; // { getPoints, getStatuses, onVoirSurCarte }

let entrees = []; // groupes (lieu, jour) après filtres/tri
let pagesListe = []; // entrées réparties par page : [[entrée, …], …]
let indexPage = 0; // 0 = couverture, 1..n = pages
let animation = false;
let minuterieResize = null;

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

export async function ouvrirCarnet() {
  // Jamais d'échec silencieux : si quelque chose casse, on le dit.
  try {
    vue.recherche = "";
    vue.favoris = false;
    vue.activite = null;
    await construireEntrees();
    indexPage = 0; // toujours la couverture d'abord
    batirSquelette();
    overlay.hidden = false; // la mesure des pages exige une mise en page réelle
    paginer();
    rendre();
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
  if (vue.activite && entrees.length) {
    bandeau.querySelector(".bandeau-texte").textContent =
      `${entrees[0].theme.icon} ${entrees[0].nom} — ${entrees.length} sortie(s)`;
  }

  if (indexPage === 0) {
    livre.innerHTML = htmlCouverture();
    livre.querySelector(".carnet-couverture").addEventListener("click", () => tourner(1));
    pied.textContent = pagesListe.length
      ? `${entrees.length} sortie(s) sur ${pagesListe.length} page(s) — touchez la couverture pour ouvrir`
      : "Votre carnet attend sa première sortie : marquez une activité « ✓ Fait » !";
  } else {
    const morceaux = [htmlPage(indexPage)];
    if (doublePage()) {
      morceaux.push(
        indexPage + 1 <= pagesListe.length ? htmlPage(indexPage + 1) : '<div class="page-carnet page-vide"></div>'
      );
    }
    // Le livre ouvert : couverture de cuir dépassant sous le bloc de pages,
    // ruban marque-page — l'épaisseur vient des tranches en box-shadow.
    livre.innerHTML = `
      <div class="livre-ouvert${doublePage() ? " double" : ""}">
        <div class="carnet-pages${doublePage() ? " double" : ""}">${morceaux.join("")}</div>
        <i class="livre-signet" aria-hidden="true"></i>
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
  return `
    <div class="carnet-couverture" role="button" tabindex="0" aria-label="Ouvrir le carnet">
      <i class="couv-fermoir" aria-hidden="true"></i>
      <i class="couv-coin coin-hg" aria-hidden="true"></i>
      <i class="couv-coin coin-hd" aria-hidden="true"></i>
      <i class="couv-coin coin-bg" aria-hidden="true"></i>
      <i class="couv-coin coin-bd" aria-hidden="true"></i>
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
    .map((n) => `<img class="page-photo" src="${n.photo}" alt="Photo de ${esc(g.nom)}" loading="lazy" style="transform:rotate(${((alea() - 0.5) * 4).toFixed(1)}deg)">`)
    .join("");
  const notes = g.notes
    .filter((n) => n.text)
    .map((n) => `<p class="page-note">${esc(n.text)}</p>`)
    .join("");

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

  // Chaque entrée a SA teinte d'encre (sépia à brun sombre) : un carnet
  // écrit au fil des ans n'a jamais deux encres parfaitement identiques.
  const encre = `hsl(${(20 + alea() * 16).toFixed(0)}, ${(42 + alea() * 16).toFixed(0)}%, ${(16 + alea() * 9).toFixed(0)}%)`;

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
      ${actions}
    </section>`;
}

function htmlPage(numero) {
  const groupe = pagesListe[numero - 1];
  const alea = graine(groupe.map((g) => g.cle).join("¤") + numero);

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

  return `
    <article class="page-carnet" style="--pente:${((alea() - 0.5) * 1.2).toFixed(2)}deg">
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
