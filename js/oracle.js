/**
 * L'Oracle 🔮 — guide local par IA.
 *
 * À partir d'un code postal (ou de la position GPS), interroge une IA AVEC
 * recherche web pour révéler tout ce qu'il y a à faire autour : randonnées,
 * lacs & baignades, événements du moment (concerts, brocantes, marchés…),
 * visites, activités.
 *
 * Multi-fournisseurs : l'utilisateur peut renseigner une clé Anthropic
 * (Claude) et/ou Google (Gemini), et choisir le moteur utilisé. Chaque
 * fournisseur a son propre format de requête ET son propre mécanisme de
 * recherche web — d'où l'abstraction FOURNISSEURS ci-dessous (OpenAI retiré :
 * pas de CORS sur son API, voir la note dans FOURNISSEURS).
 *
 * Confidentialité :
 *  - Les clés et l'historique restent dans le navigateur (localStorage, CET
 *    appareil), sous des clés dédiées, et ne sont JAMAIS incluses dans
 *    l'export de sauvegarde (import-export.js n'exporte que des champs nommés).
 *  - Une clé n'est envoyée qu'à l'API de SON fournisseur, en HTTPS (chiffré).
 *  - La réponse du modèle est échappée avant affichage (aucune injection HTML),
 *    et les liens de sources sont validés en http(s).
 */

import { toast, confirmer } from "./import-export.js";
import { esc } from "./util.js";
import { getTheme } from "./config/themes.js";
import { paysActuel } from "./config/pays.js";

const KEY_CLES = "carte-outdoor:oracle-cles"; // { anthropic, openai, google }
const KEY_MODELE = "carte-outdoor:oracle-modele"; // { provider, model }
const KEY_HISTO = "carte-outdoor:oracle-historique";
const KEY_MODE = "carte-outdoor:oracle-mode"; // "libre" (gratuit) | "ia"
const KEY_CLE_LEGACY = "carte-outdoor:oracle-cle"; // ancienne clé unique (v32)
const MAX_HISTO = 15;

const GEO_URL = "https://geo.api.gouv.fr/communes";

/**
 * Le « super prompt » commun à tous les moteurs : rôle, obligation de
 * chercher sur le web (événements réels et datés), rubriques, et format de
 * sortie strict (titres « ## », puces « - ») que le rendu met en forme sans
 * risque d'injection.
 */
const SYSTEME = `Tu es « l'Oracle », un guide local passionné qui connaît toute la France comme sa poche. Ta mission : à partir d'un lieu, révéler à la personne TOUT ce qu'il y a d'intéressant à faire autour d'elle, comme le ferait un ami du coin qui connaît les meilleurs spots ET les événements du moment.

Tu disposes d'un outil de recherche web : utilise-le vraiment, plusieurs fois, surtout pour les ÉVÉNEMENTS À VENIR (concerts, festivals, marchés, brocantes, vide-greniers, fêtes de village, expositions…) qui changent en permanence. N'invente JAMAIS un événement, une date, un lieu ou un prix : si tu n'es pas certain, cherche ; si tu ne trouves rien de fiable, ne le mets pas.

Concentre-toi sur ce qui est accessible dans un rayon raisonnable (jusqu'à ~45 min de route). Privilégie la variété et les pépites locales plutôt que les évidences ultra-touristiques.

Organise ta réponse en sections, dans cet ordre, en n'incluant une section QUE si tu as du concret à y mettre :

## 🥾 Randonnées & balades
## 🏞️ Lacs, baignades & rivières
## 🎪 Ce qui se passe en ce moment
## 🏛️ Visites & patrimoine
## 🎯 Activités & loisirs

Dans « Ce qui se passe en ce moment » : concerts, festivals, marchés, brocantes, vide-greniers, fêtes locales, expositions — chacun AVEC SA DATE.
Dans « Activités & loisirs » : accrobranche, canoë/kayak, VTT, escalade, via ferrata, thermes, fermes à visiter, ateliers, cours de danse, etc.

Dans chaque section, propose 3 à 6 idées sous forme de puces :
- **Nom du lieu ou de l'événement** — une phrase disant pourquoi ça vaut le coup, puis une info pratique (distance/direction depuis la ville, saison idéale, la DATE si c'est un événement, s'il faut réserver).

Règles de style :
- Écris en français, ton chaleureux et enthousiaste mais concis. AUCUNE phrase d'introduction ni de conclusion.
- Pour un événement, donne toujours la date et rappelle brièvement de vérifier avant de se déplacer.
- Emploie UNIQUEMENT ce format : des titres de section commençant par « ## » et des puces commençant par « - », les noms en **gras**. Pas de tableaux, pas de liens collés dans le texte (les sources s'affichent automatiquement en dessous).`;

/* ------------------------------------------------------------------ */
/* Fournisseurs d'IA : chacun sa requête et sa recherche web            */
/* ------------------------------------------------------------------ */

const FOURNISSEURS = {
  anthropic: {
    nom: "Anthropic (Claude)",
    lien: "https://console.anthropic.com/settings/keys",
    placeholder: "sk-ant-…",
    modeles: [
      { id: "claude-sonnet-5", label: "Claude Sonnet 5 — recommandé" },
      { id: "claude-haiku-4-5-20251001", label: "Claude Haiku 4.5 — économique" },
      { id: "claude-opus-4-8", label: "Claude Opus 4.8 — le plus puissant" },
    ],
    appeler: appelerAnthropic,
  },
  google: {
    nom: "Google (Gemini)",
    lien: "https://aistudio.google.com/app/apikey",
    placeholder: "AIza…",
    modeles: [
      { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro — recommandé" },
      { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash — économique" },
      { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
    ],
    appeler: appelerGoogle,
  },
  // OpenAI a été retiré volontairement : son API n'envoie pas d'en-têtes CORS,
  // donc impossible de l'appeler directement depuis un navigateur (vérifié) —
  // il aurait fallu un serveur relais, ce qui exposerait la clé. Claude et
  // Gemini, eux, autorisent l'appel direct.
};

const FOURNISSEUR_DEFAUT = "anthropic";

/* --- Anthropic (Messages API + outil web_search) ------------------- */
async function appelerAnthropic({ cle, model, message, signal }) {
  const res = await fetchIA(
    "https://api.anthropic.com/v1/messages",
    {
      method: "POST",
      signal,
      headers: {
        "content-type": "application/json",
        "x-api-key": cle,
        "anthropic-version": "2023-06-01",
        // Autorise l'appel direct depuis un navigateur (CORS).
        "anthropic-dangerous-direct-browser-access": "true",
      },
      body: JSON.stringify({
        model,
        max_tokens: 3000,
        system: SYSTEME,
        messages: [{ role: "user", content: message }],
        tools: [{ type: "web_search_20250305", name: "web_search", max_uses: 6 }],
      }),
    },
    "Anthropic"
  );
  const data = await lireJSON(res, "Anthropic");
  let texte = "";
  const citees = [];
  const vusC = new Set();
  const trouvees = [];
  const vusT = new Set();
  for (const bloc of data.content || []) {
    if (bloc.type === "text") {
      texte += bloc.text;
      for (const c of bloc.citations || []) ajouter(citees, vusC, c.url, c.title);
    } else if (bloc.type === "web_search_tool_result" && Array.isArray(bloc.content)) {
      for (const r of bloc.content) ajouter(trouvees, vusT, r.url, r.title);
    }
  }
  return { texte: texte.trim(), sources: citees.length ? citees : trouvees.slice(0, 8) };
}

/* --- Google (generateContent + grounding google_search) ------------ */
async function appelerGoogle({ cle, model, message, signal }) {
  const url =
    `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}` +
    `:generateContent?key=${encodeURIComponent(cle)}`;
  const res = await fetchIA(
    url,
    {
      method: "POST",
      signal,
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        systemInstruction: { parts: [{ text: SYSTEME }] },
        contents: [{ role: "user", parts: [{ text: message }] }],
        tools: [{ google_search: {} }],
      }),
    },
    "Google"
  );
  const data = await lireJSON(res, "Google");
  const cand = data.candidates?.[0];
  const texte = (cand?.content?.parts || []).map((p) => p.text || "").join("");
  const sources = [];
  const vus = new Set();
  for (const ch of cand?.groundingMetadata?.groundingChunks || []) {
    if (ch.web) ajouter(sources, vus, ch.web.uri, ch.web.title);
  }
  return { texte: texte.trim(), sources };
}

/** fetch avec message d'erreur réseau/CORS clair (préfixé du fournisseur). */
async function fetchIA(url, options, nom) {
  try {
    return await fetch(url, options);
  } catch (e) {
    if (e?.name === "AbortError") throw e;
    throw new Error(
      `Connexion à ${nom} impossible. Vérifie ta connexion internet et que ce fournisseur autorise l'accès direct depuis le navigateur.`
    );
  }
}

/** Lit le JSON et lève une erreur explicite si le statut n'est pas OK. */
async function lireJSON(res, nom) {
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.error?.message || `${nom} a renvoyé une erreur ${res.status}.`);
  }
  return data;
}

function ajouter(liste, vus, url, title) {
  if (url && !vus.has(url)) {
    vus.add(url);
    liste.push({ url, title: title || url });
  }
}

/* ------------------------------------------------------------------ */
/* État + persistance                                                   */
/* ------------------------------------------------------------------ */

let dialog = null;
let elReponse = null;
let elHisto = null;
let timerLoader = null;
let enCours = false;
let cb = {}; // { getPoints } — les points de la carte, pour le mode sans clé

function lire(key, defaut) {
  try {
    const v = localStorage.getItem(key);
    return v == null ? defaut : JSON.parse(v);
  } catch {
    return defaut;
  }
}
function ecrire(key, val) {
  try {
    localStorage.setItem(key, JSON.stringify(val));
  } catch (e) {
    console.warn("localStorage indisponible :", e);
  }
}

function lireCles() {
  const cles = lire(KEY_CLES, null);
  if (cles && typeof cles === "object") return cles;
  // Migration de l'ancienne clé unique (v32 : Anthropic seule)
  const ancienne = lire(KEY_CLE_LEGACY, "");
  return ancienne ? { anthropic: ancienne } : {};
}
function ecrireCles(cles) {
  ecrire(KEY_CLES, cles);
  try {
    localStorage.removeItem(KEY_CLE_LEGACY);
  } catch {}
}

function lireModeleChoisi() {
  const m = lire(KEY_MODELE, null);
  if (m && FOURNISSEURS[m.provider]) {
    const f = FOURNISSEURS[m.provider];
    const model = f.modeles.some((x) => x.id === m.model) ? m.model : f.modeles[0].id;
    return { provider: m.provider, model };
  }
  return { provider: FOURNISSEUR_DEFAUT, model: FOURNISSEURS[FOURNISSEUR_DEFAUT].modeles[0].id };
}
const cleCourante = () => lireCles()[lireModeleChoisi().provider] || "";

const lireHisto = () => lire(KEY_HISTO, []);
const ecrireHisto = (h) => ecrire(KEY_HISTO, h.slice(0, MAX_HISTO));

/** Moteur choisi : « libre » (gratuit, sans clé — la carte + Wikipédia) ou
 *  « ia » (clé requise). Par défaut : ia si une clé existe, sinon libre. */
function lireMode() {
  const m = lire(KEY_MODE, null);
  if (m === "libre" || m === "ia") return m;
  return cleCourante() ? "ia" : "libre";
}

function majModeUI() {
  const mode = lireMode();
  dialog.querySelectorAll(".oracle-mode-btn").forEach((b) => {
    b.classList.toggle("actif", b.dataset.mode === mode);
  });
}

/* ------------------------------------------------------------------ */
/* Résolution du lieu (code postal ou position) via geo.api.gouv.fr     */
/* ------------------------------------------------------------------ */

function versLieu(commune, cp) {
  const coords = commune.centre?.coordinates || [];
  return {
    nom: commune.nom,
    cp: cp || commune.codesPostaux?.[0] || "",
    departement: commune.departement?.nom || "",
    region: commune.region?.nom || "",
    lat: coords[1],
    lon: coords[0],
  };
}

/** Résout un NOM de commune (« Chamonix », « Riquewihr »…) — la commune la
 *  plus peuplée gagne en cas d'homonymes (boost=population). */
async function resoudreNomCommune(nom) {
  const url =
    `${GEO_URL}?nom=${encodeURIComponent(nom)}` +
    `&fields=nom,centre,departement,region,codesPostaux&boost=population&limit=1&format=json`;
  let arr;
  try {
    const res = await fetch(url);
    arr = res.ok ? await res.json() : null;
  } catch {
    throw new Error("Impossible de chercher cette commune (connexion ?).");
  }
  if (!Array.isArray(arr) || !arr.length) {
    throw new Error(`Aucune commune trouvée pour « ${nom} ».`);
  }
  return versLieu(arr[0]);
}

async function resoudreCodePostal(cp) {
  const url = `${GEO_URL}?codePostal=${encodeURIComponent(cp)}&fields=nom,centre,departement,region,codesPostaux&format=json`;
  let arr;
  try {
    const res = await fetch(url);
    arr = res.ok ? await res.json() : null;
  } catch {
    throw new Error("Impossible de vérifier le code postal (connexion ?).");
  }
  if (!Array.isArray(arr) || !arr.length) {
    throw new Error(`Aucune commune trouvée pour le code postal ${cp}.`);
  }
  return versLieu(arr[0], cp);
}

async function resoudrePosition() {
  const pos = await new Promise((resolve, reject) => {
    if (!navigator.geolocation) return reject(new Error("Géolocalisation indisponible sur cet appareil."));
    navigator.geolocation.getCurrentPosition(
      resolve,
      () => reject(new Error("Position refusée ou indisponible.")),
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 60000 }
    );
  });
  const { latitude, longitude } = pos.coords;
  const url = `${GEO_URL}?lat=${latitude}&lon=${longitude}&fields=nom,centre,departement,region,codesPostaux&format=json`;
  let arr;
  try {
    const res = await fetch(url);
    arr = res.ok ? await res.json() : null;
  } catch {
    throw new Error("Impossible de localiser la commune (connexion ?).");
  }
  if (!Array.isArray(arr) || !arr.length) {
    throw new Error("Aucune commune trouvée à ta position.");
  }
  return versLieu(arr[0]);
}

function construireMessage(lieu) {
  const date = new Date().toLocaleDateString("fr-FR", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  const loc = [lieu.nom, lieu.departement, lieu.region].filter(Boolean).join(", ");
  return (
    `Je me trouve à ${loc} (code postal ${lieu.cp}). Nous sommes le ${date}. ` +
    `Que puis-je faire d'intéressant autour de moi — aujourd'hui, ce week-end et dans les prochaines semaines ? ` +
    `Cherche en priorité les événements du moment (concerts, festivals, marchés, brocantes, vide-greniers, fêtes locales, expositions), ` +
    `ainsi que les randonnées, lacs et baignades, visites de patrimoine et activités de plein air dans les environs.`
  );
}

/* ------------------------------------------------------------------ */
/* Rendu sûr de la réponse                                              */
/* ------------------------------------------------------------------ */

function enLigne(t) {
  return (
    esc(t)
      // Lien interne vers un point de NOTRE carte : {{p:ID}}texte{{/p}}.
      // Posé par le mode Gratuit (sectionCarte). L'ID est validé
      // alphanumérique/tiret, le texte est déjà échappé par esc() → sûr même
      // si un modèle IA tentait d'imiter ce marqueur (un ID inconnu ne fera
      // rien au clic, voir le gestionnaire dans initOracle).
      .replace(
        /\{\{p:([\w-]+)\}\}([\s\S]+?)\{\{\/p\}\}/g,
        (m, id, texte) => `<button type="button" class="oracle-point" data-id="${id}">${texte}</button>`
      )
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
  );
}

function formaterReponse(texte) {
  const lignes = String(texte).split("\n");
  let html = "";
  let dansListe = false;
  const fermerListe = () => {
    if (dansListe) {
      html += "</ul>";
      dansListe = false;
    }
  };
  for (const brute of lignes) {
    const l = brute.trim();
    if (!l) {
      fermerListe();
      continue;
    }
    if (l.startsWith("## ")) {
      fermerListe();
      html += `<h4 class="oracle-section">${enLigne(l.slice(3))}</h4>`;
    } else if (l.startsWith("### ")) {
      fermerListe();
      html += `<h5 class="oracle-soussection">${enLigne(l.slice(4))}</h5>`;
    } else if (l.startsWith("- ") || l.startsWith("* ")) {
      if (!dansListe) {
        html += '<ul class="oracle-puces">';
        dansListe = true;
      }
      html += `<li>${enLigne(l.slice(2))}</li>`;
    } else {
      fermerListe();
      html += `<p>${enLigne(l)}</p>`;
    }
  }
  fermerListe();
  return html;
}

function rendreSources(sources) {
  const items = (sources || [])
    .filter((s) => /^https?:\/\//i.test(s.url))
    .slice(0, 12)
    .map(
      (s) =>
        `<li><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(
          s.title || s.url
        )}</a></li>`
    )
    .join("");
  if (!items) return "";
  return `<div class="oracle-sources"><h4>🔗 Sources</h4><ul>${items}</ul></div>`;
}

/* ------------------------------------------------------------------ */
/* Affichage : état vide, chargement, résultat, erreur                  */
/* ------------------------------------------------------------------ */

/**
 * Forme de la boule : sphère parfaite quand le contenu est court (accueil,
 * chargement, erreur) ; elle se déploie en CAPSULE rectangulaire de verre
 * quand il faut de la place (réponse, panneau des clés) — retour utilisateur
 * v41 : la capsule est plus lisible que l'ellipse pour la lecture.
 */
let contenuActuel = "vide"; // "vide" | "chargement" | "erreur" | "reponse"

function majForme() {
  const panneauOuvert = !panneauCle().hidden;
  dialog.classList.toggle("forme-etiree", panneauOuvert || contenuActuel === "reponse");
}

function etatVide() {
  contenuActuel = "vide";
  elReponse.innerHTML =
    '<div class="oracle-vide"><div class="oracle-vide-signe" aria-hidden="true">✦</div>' +
    "<p>Entre un code postal ou une commune (ou touche 📍) : l'Oracle révèle ce qu'il y a à " +
    "faire autour. ✨ Le mode Gratuit ne demande aucune clé.</p></div>";
  majForme();
}

const MESSAGES_LOADER = [
  "L'Oracle scrute les environs…",
  "Il suit les sentiers et longe les lacs…",
  "Il déniche les événements du moment…",
  "Il consulte les astres locaux…",
  "Il rassemble les pépites du coin…",
];

/* La brume tourbillonne DANS la boule pendant que l'Oracle cherche */
const HTML_BRUME =
  '<span class="oracle-brume b1" aria-hidden="true"></span>' +
  '<span class="oracle-brume b2" aria-hidden="true"></span>';

function loaderTexte(msg) {
  arreterLoader();
  contenuActuel = "chargement";
  elReponse.innerHTML =
    `<div class="oracle-loader">${HTML_BRUME}<p class="oracle-loader-msg">${esc(msg)}</p></div>`;
  majForme();
}

function demarrerLoader(lieu) {
  arreterLoader();
  contenuActuel = "chargement";
  let i = 0;
  const nom = lieu?.nom ? "Autour de " + esc(lieu.nom) : "";
  elReponse.innerHTML =
    `<div class="oracle-loader">${HTML_BRUME}` +
    (nom ? `<p class="oracle-loader-lieu">${nom}</p>` : "") +
    `<p class="oracle-loader-msg">${esc(MESSAGES_LOADER[0])}</p></div>`;
  majForme();
  timerLoader = setInterval(() => {
    i++;
    const m = elReponse.querySelector(".oracle-loader-msg");
    if (m) m.textContent = MESSAGES_LOADER[i % MESSAGES_LOADER.length];
  }, 2600);
}

function arreterLoader() {
  if (timerLoader) {
    clearInterval(timerLoader);
    timerLoader = null;
  }
}

function afficherReponse(entree) {
  contenuActuel = "reponse"; // la boule s'étire en capsule pour la lecture
  const lieu = entree.lieu || {};
  const date = new Date(entree.date).toLocaleDateString("fr-FR", {
    day: "numeric",
    month: "long",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
  const meta = [lieu.departement, lieu.region].filter(Boolean).join(" · ");
  const moteur = entree.moteur ? ` · ${esc(entree.moteur)}` : "";
  // Résultat du mode Gratuit : on encadre la réponse (haut ET bas) d'un rappel
  // que les fonctionnalités avancées (spectacles, événements datés…) passent
  // par une clé API. Le test sur `moteur` couvre aussi l'ancien historique.
  const gratuit = /gratuit|sans clé/i.test(entree.moteur || "");
  const noteIA =
    '<p class="oracle-note-ia">🔑 Pour les fonctionnalités avancées — spectacles, concerts, ' +
    "brocantes et événements datés à proximité — renseigne une clé API et passe en mode 🧠 IA.</p>";
  elReponse.innerHTML =
    '<div class="oracle-resultat"><div class="oracle-resultat-tete">' +
    `<h3>✨ Autour de ${esc(lieu.nom || "")}</h3>` +
    `<p class="oracle-resultat-meta">${esc(meta)}${meta ? " — " : ""}${esc(date)}${moteur}</p></div>` +
    (gratuit ? noteIA : "") +
    `<div class="oracle-texte">${formaterReponse(entree.texte)}</div>` +
    rendreSources(entree.sources) +
    (gratuit ? noteIA : "") +
    "</div>";
  elReponse.scrollTop = 0;
  majForme();
}

function afficherErreur(e) {
  arreterLoader();
  contenuActuel = "erreur"; // court : la boule reste une boule
  let msg = e?.message || "Erreur inconnue.";
  if (e?.name === "AbortError") {
    msg = "La consultation a été trop longue et a été interrompue. Réessaie.";
  }
  elReponse.innerHTML = `<div class="oracle-erreur"><p>🌫️ ${esc(msg)}</p></div>`;
  majForme();
}

/* ------------------------------------------------------------------ */
/* Historique                                                           */
/* ------------------------------------------------------------------ */

function renderHisto() {
  const histo = lireHisto();
  if (!histo.length) {
    elHisto.innerHTML = '<p class="oracle-histo-vide">Tes consultations passées apparaîtront ici.</p>';
    return;
  }
  elHisto.innerHTML = "";
  for (const e of histo) {
    const item = document.createElement("div");
    item.className = "oracle-histo-item";
    const d = new Date(e.date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" });
    item.innerHTML =
      '<button type="button" class="oracle-histo-open">' +
      `<span class="oracle-histo-lieu">${esc(e.lieu?.nom || "?")}</span>` +
      `<span class="oracle-histo-date">${esc(d)}</span></button>` +
      '<button type="button" class="oracle-histo-suppr" title="Oublier" aria-label="Oublier cette consultation">✕</button>';
    item.querySelector(".oracle-histo-open").addEventListener("click", () => {
      afficherReponse(e);
      elHisto.querySelectorAll(".oracle-histo-item").forEach((x) => x.classList.remove("actif"));
      item.classList.add("actif");
    });
    item.querySelector(".oracle-histo-suppr").addEventListener("click", () => {
      ecrireHisto(lireHisto().filter((x) => x.id !== e.id));
      renderHisto();
    });
    elHisto.appendChild(item);
  }
}

/* ------------------------------------------------------------------ */
/* Panneau des clés & du moteur                                         */
/* ------------------------------------------------------------------ */

function panneauCle() {
  return dialog.querySelector(".oracle-cle-panneau");
}

/** Remplit le sélecteur de fournisseur, la liste de modèles et les champs
 *  de clé (un par fournisseur) selon ce qui est enregistré. */
function garnirPanneauCle() {
  const choisi = lireModeleChoisi();
  const cles = lireCles();

  const selF = dialog.querySelector(".oracle-fournisseur");
  selF.innerHTML = Object.entries(FOURNISSEURS)
    .map(([id, f]) => `<option value="${id}">${esc(f.nom)}</option>`)
    .join("");
  selF.value = choisi.provider;
  selF.onchange = () => majListeModeles();
  majListeModeles(choisi.model);

  const cont = dialog.querySelector(".oracle-cles");
  cont.innerHTML = "";
  for (const [id, f] of Object.entries(FOURNISSEURS)) {
    const champ = document.createElement("label");
    champ.className = "oracle-champ oracle-cle-champ";
    champ.innerHTML =
      `<span>${esc(f.nom)} — <a href="${f.lien}" target="_blank" rel="noopener noreferrer">obtenir une clé</a></span>` +
      `<input type="password" data-fournisseur="${id}" placeholder="${esc(f.placeholder)}" autocomplete="off" spellcheck="false">` +
      (f.avert ? `<small class="oracle-avert">${esc(f.avert)}</small>` : "");
    champ.querySelector("input").value = cles[id] || "";
    cont.appendChild(champ);
  }
}

function majListeModeles(modelePref) {
  const provider = dialog.querySelector(".oracle-fournisseur").value;
  const selM = dialog.querySelector(".oracle-modele");
  selM.innerHTML = FOURNISSEURS[provider].modeles
    .map((m) => `<option value="${m.id}">${esc(m.label)}</option>`)
    .join("");
  if (modelePref && FOURNISSEURS[provider].modeles.some((m) => m.id === modelePref)) {
    selM.value = modelePref;
  }
}

/** force === true : afficher ; false : masquer ; undefined : basculer. */
function ouvrirPanneauCle(force) {
  const p = panneauCle();
  const afficher = force === undefined ? p.hidden : force;
  p.hidden = !afficher;
  if (afficher) {
    garnirPanneauCle();
    p.querySelector(".oracle-fournisseur").focus();
  }
  majForme(); // le panneau a besoin de place : boule → capsule (et retour)
}

/* ------------------------------------------------------------------ */
/* Mode GRATUIT (sans clé) : les points de la carte + Wikipédia          */
/* + liens d'agendas pour les événements. Aucune IA, zéro coût.          */
/* ------------------------------------------------------------------ */

function distanceKm(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180;
  const dLat = (lat2 - lat1) * rad;
  const dLon = (lon2 - lon1) * rad;
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(dLon / 2) ** 2;
  return 2 * 6371 * Math.asin(Math.sqrt(a));
}

function direction(lat1, lon1, lat2, lon2) {
  const rad = Math.PI / 180;
  const y = Math.sin((lon2 - lon1) * rad) * Math.cos(lat2 * rad);
  const x =
    Math.cos(lat1 * rad) * Math.sin(lat2 * rad) -
    Math.sin(lat1 * rad) * Math.cos(lat2 * rad) * Math.cos((lon2 - lon1) * rad);
  const cap = (Math.atan2(y, x) * 180) / Math.PI;
  const dirs = ["nord", "nord-est", "est", "sud-est", "sud", "sud-ouest", "ouest", "nord-ouest"];
  return dirs[Math.round(((cap + 360) % 360) / 45) % 8];
}

const kmLisible = (d) => (d < 10 ? d.toFixed(1) : String(Math.round(d)));

/** « au nord », mais « à l'est » / « à l'ouest » (élision). */
const versDirection = (d) => (d.startsWith("est") || d.startsWith("ouest") ? `à l'${d}` : `au ${d}`);

/** Les meilleurs points de NOTRE carte autour du lieu, groupés par catégorie. */
function sectionCarte(lieu) {
  const points = cb.getPoints?.() || [];
  if (!points.length || !Number.isFinite(lieu.lat)) return "";
  const groupes = [
    ["via-ferrata"],
    ["escalade"],
    ["refuge"],
    ["grotte"],
    ["chateau"],
    ["cathedrale"],
    ["cite-caractere"],
  ];
  const blocs = [];
  for (const ids of groupes) {
    const proches = [];
    for (const f of points) {
      const t = getTheme(f.properties.theme);
      if (!ids.includes(t.id)) continue;
      const [lon, lat] = f.geometry?.coordinates || [];
      if (!Number.isFinite(lat)) continue;
      const d = distanceKm(lieu.lat, lieu.lon, lat, lon);
      if (d <= 40) proches.push({ f, t, d, lat, lon });
    }
    if (!proches.length) continue;
    proches.sort((a, b) => a.d - b.d);
    const lignes = proches.slice(0, 4).map((p) => {
      // Les points géocodés au centroïde de commune tombent pile sur le lieu
      // demandé : « à 0.0 km au nord » n'a pas de sens → « sur place ».
      const ou =
        p.d < 0.15
          ? "sur place"
          : `à ${kmLisible(p.d)} km ${versDirection(direction(lieu.lat, lieu.lon, p.lat, p.lon))}`;
      // Le nom devient un LIEN vers le point sur la carte (marqueur {{p:ID}}
      // interprété par enLigne). Repli en simple gras si l'id est atypique.
      const id = p.f.properties.id;
      const nom = /^[\w-]+$/.test(id)
        ? `{{p:${id}}}**${p.f.properties.name}**{{/p}}`
        : `**${p.f.properties.name}**`;
      return `- ${nom} — ${ou}`;
    });
    blocs.push(`### ${proches[0].t.icon} ${proches[0].t.label}\n${lignes.join("\n")}`);
  }
  if (!blocs.length) return "";
  return "## 🗺️ Sur ta carte, tout près\n" + blocs.join("\n");
}

/** Curiosités du coin via l'API Wikipédia (gratuite, sans clé).
 *  Langue selon le pays de la carte (fr en France, en en Nouvelle-Zélande :
 *  fr.wikipedia est quasi vide là-bas). */
async function chercherWikipedia(lieu) {
  const lang = paysActuel().wikiLang || "fr";
  const base = `https://${lang}.wikipedia.org/w/api.php`;
  const res = await fetch(
    `${base}?action=query&list=geosearch&gscoord=${lieu.lat}%7C${lieu.lon}` +
      `&gsradius=10000&gslimit=12&format=json&origin=*`
  );
  if (!res.ok) return { texte: "", sources: [] };
  const trouves = (await res.json())?.query?.geosearch || [];
  // L'article de la commune elle-même n'apprend rien : on l'écarte
  const retenus = trouves.filter((p) => p.title !== lieu.nom).slice(0, 6);
  if (!retenus.length) return { texte: "", sources: [] };

  // Une phrase de résumé par page (facultatif : tant pis si ça échoue)
  let extraits = {};
  try {
    const ex = await fetch(
      `${base}?action=query&pageids=${retenus.map((p) => p.pageid).join("%7C")}` +
        `&prop=extracts&exintro=1&explaintext=1&exsentences=1&format=json&origin=*`
    );
    if (ex.ok) extraits = (await ex.json())?.query?.pages || {};
  } catch {}

  const lignes = retenus.map((p) => {
    const resume = (extraits[p.pageid]?.extract || "").trim();
    return `- **${p.title}** — ${resume ? resume + " " : ""}À ${kmLisible(p.dist / 1000)} km.`;
  });
  const sources = retenus.map((p) => ({
    url: `https://${lang}.wikipedia.org/wiki/` + encodeURIComponent(p.title.replace(/ /g, "_")),
    title: "Wikipédia — " + p.title,
  }));
  return { texte: "## 🏛️ À découvrir dans le coin\n" + lignes.join("\n"), sources };
}

async function lancerLibre(lieu) {
  if (enCours) return;
  enCours = true;
  majBoutons(true);
  demarrerLoader(lieu);
  try {
    const morceaux = [];
    const sources = [];

    const carte = sectionCarte(lieu);
    if (carte) morceaux.push(carte);

    try {
      const wiki = await chercherWikipedia(lieu);
      if (wiki.texte) {
        morceaux.push(wiki.texte);
        sources.push(...wiki.sources);
      }
    } catch {}

    // Les événements bougent tous les jours : sans IA, on tend les bons liens
    const q = (t) => "https://www.google.com/search?q=" + encodeURIComponent(t);
    morceaux.push(
      "## 🎪 Ce qui se passe en ce moment\n" +
        "- Les événements changent chaque jour : ouvre les agendas dans les **sources ci-dessous**, ou passe en mode 🧠 IA pour une sélection datée et vérifiée."
    );
    sources.push(
      { url: q(`que faire à ${lieu.nom} ce week-end`), title: `🔎 Que faire à ${lieu.nom} ce week-end` },
      { url: q(`concert festival agenda ${lieu.nom} ${lieu.departement}`), title: `🎵 Concerts & festivals autour de ${lieu.nom}` },
      { url: q(`brocante vide-grenier marché ${lieu.nom} ${lieu.cp}`), title: "🛍️ Brocantes, vide-greniers & marchés" }
    );

    if (!carte) {
      morceaux.unshift(
        "Rien de répertorié sur ta carte à moins de 40 km — mais voici ce que Wikipédia et les agendas racontent."
      );
    }

    const entree = {
      id: `o-${Date.now().toString(36)}`,
      date: new Date().toISOString(),
      lieu,
      texte: morceaux.join("\n\n"),
      sources,
      moteur: "Oracle gratuit",
    };
    const histo = lireHisto();
    histo.unshift(entree);
    ecrireHisto(histo);
    renderHisto();
    afficherReponse(entree);
  } catch (e) {
    afficherErreur(e);
  } finally {
    arreterLoader();
    enCours = false;
    majBoutons(false);
  }
}

/* ------------------------------------------------------------------ */
/* Lancement d'une consultation                                         */
/* ------------------------------------------------------------------ */

function majBoutons(charge) {
  dialog.querySelector(".oracle-consulter").disabled = charge;
  dialog.querySelector(".oracle-consulter").classList.toggle("charge", charge);
  dialog.querySelector(".oracle-position").disabled = charge;
}

async function lancer(lieu) {
  if (enCours) return;
  // Mode gratuit : aucune clé requise, aucune dépense
  if (lireMode() === "libre") return lancerLibre(lieu);
  const choix = lireModeleChoisi();
  const f = FOURNISSEURS[choix.provider];
  const cle = lireCles()[choix.provider];
  if (!cle) {
    toast(`Renseigne d'abord ta clé ${f.nom} (ou passe en mode ✨ Gratuit).`);
    etatVide(); // la boule affichait « Localisation… » : ne pas l'y laisser
    ouvrirPanneauCle(true);
    return;
  }
  enCours = true;
  majBoutons(true);
  demarrerLoader(lieu);
  const ctrl = new AbortController();
  const minuteur = setTimeout(() => ctrl.abort(), 90000);
  try {
    const { texte, sources } = await f.appeler({
      cle,
      model: choix.model,
      message: construireMessage(lieu),
      signal: ctrl.signal,
    });
    if (!texte) throw new Error("L'Oracle n'a rien révélé cette fois — réessaie dans un instant.");
    const entree = {
      id: `o-${Date.now().toString(36)}`,
      date: new Date().toISOString(),
      lieu,
      texte,
      sources,
      moteur: f.nom,
    };
    const histo = lireHisto();
    histo.unshift(entree);
    ecrireHisto(histo);
    renderHisto();
    afficherReponse(entree);
  } catch (e) {
    afficherErreur(e);
  } finally {
    clearTimeout(minuteur);
    arreterLoader();
    enCours = false;
    majBoutons(false);
  }
}

async function depuisCodePostal(cp) {
  if (enCours) return;
  loaderTexte("Localisation…");
  try {
    const lieu = await resoudreCodePostal(cp);
    await lancer(lieu);
  } catch (e) {
    afficherErreur(e);
  }
}

async function depuisNomCommune(nom) {
  if (enCours) return;
  loaderTexte("Localisation…");
  try {
    const lieu = await resoudreNomCommune(nom);
    await lancer(lieu);
  } catch (e) {
    afficherErreur(e);
  }
}

async function depuisPosition() {
  if (enCours) return;
  if (lireMode() === "ia" && !cleCourante()) {
    ouvrirPanneauCle(true);
    return;
  }
  loaderTexte("Recherche de ta position…");
  try {
    const lieu = await resoudrePosition();
    dialog.querySelector(".oracle-cp").value = lieu.cp || "";
    await lancer(lieu);
  } catch (e) {
    afficherErreur(e);
  }
}

/* ------------------------------------------------------------------ */
/* Ouverture / init                                                     */
/* ------------------------------------------------------------------ */

function ouvrir() {
  renderHisto();
  majModeUI();
  // À l'ouverture : TOUJOURS la boule (le panneau des clés ne s'impose plus —
  // le mode ✨ Gratuit marche sans rien, et 🔑 reste à portée de main).
  ouvrirPanneauCle(false);
  etatVide();
  dialog.showModal();
}

export function initOracle(callbacks = {}) {
  cb = callbacks;
  dialog = document.getElementById("oracle-dialog");
  elReponse = dialog.querySelector(".oracle-reponse");
  elHisto = dialog.querySelector(".oracle-histo-liste");

  document.getElementById("btn-oracle").addEventListener("click", ouvrir);
  dialog.querySelector(".oracle-close").addEventListener("click", () => dialog.close());

  // Clic sur un point annoncé (mode Gratuit) → on ferme l'Oracle et on montre
  // le point sur la carte. L'id vient d'un marqueur validé (voir enLigne).
  elReponse.addEventListener("click", (e) => {
    const btn = e.target.closest(".oracle-point");
    if (!btn) return;
    dialog.close();
    cb.onVoirPoint?.(btn.dataset.id);
  });
  dialog.querySelector(".oracle-cle-toggle").addEventListener("click", () => ouvrirPanneauCle());

  // Fermeture en touchant le fond, hors de la fenêtre (indispensable sur
  // mobile où le ✕ pouvait être difficile à atteindre — « impossible à fermer »).
  dialog.addEventListener("click", (e) => {
    if (e.target !== dialog) return; // clic sur le contenu : on ignore
    const r = dialog.getBoundingClientRect();
    const dehors =
      e.clientX < r.left || e.clientX > r.right || e.clientY < r.top || e.clientY > r.bottom;
    if (dehors) dialog.close();
  });

  // Code postal (5 chiffres) OU nom de commune — les deux mènent au même lieu
  dialog.querySelector(".oracle-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const brut = (dialog.querySelector(".oracle-cp").value || "").trim();
    if (!brut) {
      toast("Entre un code postal ou un nom de commune.");
      return;
    }
    if (/^\d{5}$/.test(brut)) depuisCodePostal(brut);
    else if (/^\d+$/.test(brut)) toast("Un code postal fait 5 chiffres.");
    else depuisNomCommune(brut);
  });

  dialog.querySelector(".oracle-position").addEventListener("click", depuisPosition);

  // Bascule ✨ Gratuit / 🧠 IA (persistée) — choisir IA sans clé ouvre 🔑,
  // et revenir au Gratuit REFERME le panneau des clés (sinon il restait
  // affiché sur mobile — bug signalé en v40).
  dialog.querySelectorAll(".oracle-mode-btn").forEach((b) =>
    b.addEventListener("click", () => {
      ecrire(KEY_MODE, b.dataset.mode);
      majModeUI();
      if (b.dataset.mode === "ia" && !cleCourante()) ouvrirPanneauCle(true);
      else if (b.dataset.mode === "libre") ouvrirPanneauCle(false);
    })
  );

  dialog.querySelector(".oracle-cle-enregistrer").addEventListener("click", () => {
    const cles = {};
    dialog.querySelectorAll(".oracle-cles input").forEach((inp) => {
      const v = inp.value.trim();
      if (v) cles[inp.dataset.fournisseur] = v;
    });
    ecrireCles(cles);
    const provider = dialog.querySelector(".oracle-fournisseur").value;
    const model = dialog.querySelector(".oracle-modele").value;
    ecrire(KEY_MODELE, { provider, model });
    ouvrirPanneauCle(false);
    if (cleCourante()) etatVide();
    toast("Réglages enregistrés sur cet appareil.");
  });

  dialog.querySelector(".oracle-cle-effacer").addEventListener("click", async () => {
    if (!(await confirmer("Effacer toutes les clés API de cet appareil ?"))) return;
    ecrireCles({});
    garnirPanneauCle();
    toast("Clés effacées.");
  });
}
