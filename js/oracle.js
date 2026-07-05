/**
 * L'Oracle 🔮 — guide local par IA.
 *
 * À partir d'un code postal (ou de la position GPS), interroge une IA AVEC
 * recherche web pour révéler tout ce qu'il y a à faire autour : randonnées,
 * lacs & baignades, événements du moment (concerts, brocantes, marchés…),
 * visites, activités.
 *
 * Multi-fournisseurs : l'utilisateur peut renseigner une clé Anthropic
 * (Claude), OpenAI (GPT) et/ou Google (Gemini), et choisir le moteur utilisé.
 * Chaque fournisseur a son propre format de requête ET son propre mécanisme
 * de recherche web — d'où l'abstraction FOURNISSEURS ci-dessous.
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

const KEY_CLES = "carte-outdoor:oracle-cles"; // { anthropic, openai, google }
const KEY_MODELE = "carte-outdoor:oracle-modele"; // { provider, model }
const KEY_HISTO = "carte-outdoor:oracle-historique";
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
  openai: {
    nom: "OpenAI (GPT)",
    lien: "https://platform.openai.com/api-keys",
    placeholder: "sk-…",
    // OpenAI n'envoie pas d'en-têtes CORS : impossible de l'appeler directement
    // depuis un navigateur (vérifié). Reste proposé, mais avec un avertissement.
    avert: "⚠️ OpenAI n'autorise pas l'appel direct depuis un navigateur : cette clé ne fonctionnera probablement pas ici. Préfère Claude ou Gemini.",
    modeles: [
      { id: "gpt-4o", label: "GPT-4o — recommandé" },
      { id: "gpt-4o-mini", label: "GPT-4o mini — économique" },
      { id: "gpt-4.1", label: "GPT-4.1" },
      { id: "gpt-4.1-mini", label: "GPT-4.1 mini" },
    ],
    appeler: appelerOpenAI,
  },
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

/* --- OpenAI (Responses API + outil web_search_preview) ------------- */
async function appelerOpenAI({ cle, model, message, signal }) {
  const res = await fetchIA(
    "https://api.openai.com/v1/responses",
    {
      method: "POST",
      signal,
      headers: { "content-type": "application/json", Authorization: `Bearer ${cle}` },
      body: JSON.stringify({
        model,
        instructions: SYSTEME,
        input: message,
        tools: [{ type: "web_search_preview" }],
        max_output_tokens: 2800,
      }),
    },
    "OpenAI"
  );
  const data = await lireJSON(res, "OpenAI");
  let texte = "";
  const sources = [];
  const vus = new Set();
  for (const item of data.output || []) {
    if (item.type !== "message") continue;
    for (const c of item.content || []) {
      if (c.type === "output_text") {
        texte += c.text || "";
        for (const a of c.annotations || []) {
          if (a.type === "url_citation") ajouter(sources, vus, a.url, a.title);
        }
      }
    }
  }
  return { texte: texte.trim(), sources };
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

function esc(t) {
  const d = document.createElement("div");
  d.textContent = t ?? "";
  return d.innerHTML;
}
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
  return esc(t).replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
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

function etatVide() {
  elReponse.innerHTML =
    '<div class="oracle-vide"><div class="oracle-vide-boule">🔮</div>' +
    "<p>Entre un code postal (ou touche 📍) et laisse l'Oracle révéler tout ce qu'il y a à faire dans les environs.</p></div>";
}

const MESSAGES_LOADER = [
  "L'Oracle scrute les environs…",
  "Il suit les sentiers et longe les lacs…",
  "Il déniche les événements du moment…",
  "Il consulte les astres locaux…",
  "Il rassemble les pépites du coin…",
];

function loaderTexte(msg) {
  arreterLoader();
  elReponse.innerHTML =
    '<div class="oracle-loader"><div class="oracle-loader-boule"><span></span><span></span></div>' +
    `<p class="oracle-loader-msg">${esc(msg)}</p></div>`;
}

function demarrerLoader(lieu) {
  arreterLoader();
  let i = 0;
  const nom = lieu?.nom ? "Autour de " + esc(lieu.nom) : "";
  elReponse.innerHTML =
    '<div class="oracle-loader"><div class="oracle-loader-boule"><span></span><span></span></div>' +
    (nom ? `<p class="oracle-loader-lieu">${nom}</p>` : "") +
    `<p class="oracle-loader-msg">${esc(MESSAGES_LOADER[0])}</p></div>`;
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
  elReponse.innerHTML =
    '<div class="oracle-resultat"><div class="oracle-resultat-tete">' +
    `<h3>✨ Autour de ${esc(lieu.nom || "")}</h3>` +
    `<p class="oracle-resultat-meta">${esc(meta)}${meta ? " — " : ""}${esc(date)}${moteur}</p></div>` +
    `<div class="oracle-texte">${formaterReponse(entree.texte)}</div>` +
    rendreSources(entree.sources) +
    "</div>";
  elReponse.scrollTop = 0;
}

function afficherErreur(e) {
  arreterLoader();
  let msg = e?.message || "Erreur inconnue.";
  if (e?.name === "AbortError") {
    msg = "La consultation a été trop longue et a été interrompue. Réessaie.";
  }
  elReponse.innerHTML = `<div class="oracle-erreur"><p>🌫️ ${esc(msg)}</p></div>`;
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
  const choix = lireModeleChoisi();
  const f = FOURNISSEURS[choix.provider];
  const cle = lireCles()[choix.provider];
  if (!cle) {
    toast(`Renseigne d'abord ta clé ${f.nom}.`);
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

async function depuisPosition() {
  if (enCours) return;
  if (!cleCourante()) {
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
  const aCle = !!cleCourante();
  ouvrirPanneauCle(!aCle); // premier usage : on montre d'emblée le panneau
  if (aCle) etatVide();
  dialog.showModal();
}

export function initOracle() {
  dialog = document.getElementById("oracle-dialog");
  elReponse = dialog.querySelector(".oracle-reponse");
  elHisto = dialog.querySelector(".oracle-histo-liste");

  document.getElementById("btn-oracle").addEventListener("click", ouvrir);
  dialog.querySelector(".oracle-close").addEventListener("click", () => dialog.close());
  dialog.querySelector(".oracle-cle-toggle").addEventListener("click", () => ouvrirPanneauCle());

  dialog.querySelector(".oracle-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const cp = (dialog.querySelector(".oracle-cp").value || "").trim();
    if (!/^\d{5}$/.test(cp)) {
      toast("Entre un code postal à 5 chiffres.");
      return;
    }
    depuisCodePostal(cp);
  });

  dialog.querySelector(".oracle-position").addEventListener("click", depuisPosition);

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
