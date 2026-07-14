/**
 * Catégories COMMUNAUTAIRES : partager ses catégories personnelles et importer
 * celles des autres. Serveur : Supabase (table `categories_partagees`, RLS,
 * schéma supabase/communaute-schema.sql). Chaque soumission passe par une
 * VALIDATION MANUELLE (statut en_attente → validee) avant d'être visible.
 *
 * - Explorer/importer : PUBLIC (lecture des catégories validées, sans compte).
 * - Partager : exige la connexion Google (anti-spam + auteur identifié).
 * - v1 SANS photos : elles sont retirées du colis (droits d'auteur + poids).
 * - Sécurité d'affichage : tout texte serveur passe par esc() ; l'import
 *   re-identifie thème et points (`comm-<id>…`, ids STABLES → réimport
 *   idempotent) et ne garde que des champs connus.
 */

import { SUPABASE_URL, SUPABASE_ANON } from "./config/supabase.js";
import { PAYS, paysActuel } from "./config/pays.js";
import { sessionCommunaute, demanderConnexion } from "./sync.js";
import { toast, confirmer } from "./import-export.js";
import { esc } from "./util.js";

let cb = {}; // { getMesCategories, getPointsDeTheme, importerCategorie, estImportee }
let dialog = null;

const MAX_POINTS = 500;
const MAX_OCTETS = 1_000_000; // 1 Mo (le serveur revérifie)

/* ------------------------------------------------------------------ */
/* Accès serveur (fetch pur, comme sync.js)                            */
/* ------------------------------------------------------------------ */

const REST = `${SUPABASE_URL}/rest/v1/categories_partagees`;

function entetes(token) {
  return {
    apikey: SUPABASE_ANON,
    Authorization: `Bearer ${token || SUPABASE_ANON}`,
    "Content-Type": "application/json",
  };
}

/** La table n'existe pas encore (SQL non exécuté) → message honnête. */
function serveurAbsent(res) {
  return res.status === 404 || res.status === 400;
}

/** fetch avec erreur réseau lisible (hors-ligne, préview…) */
async function requeter(url, options) {
  let res;
  try {
    res = await fetch(url, options);
  } catch {
    throw new Error("réseau");
  }
  return res;
}

async function listerValidees() {
  const res = await requeter(
    `${REST}?select=id,nom,description,pays,nb_points,telechargements,cree` +
      `&statut=eq.validee&order=telechargements.desc,cree.desc&limit=100`,
    { headers: entetes() }
  );
  if (!res.ok) {
    if (serveurAbsent(res)) throw new Error("indisponible");
    throw new Error(`serveur (${res.status})`);
  }
  return res.json();
}

async function telechargerColis(id) {
  const res = await requeter(`${REST}?id=eq.${encodeURIComponent(id)}&select=donnees`, {
    headers: entetes(),
  });
  if (!res.ok) throw new Error(`serveur (${res.status})`);
  const [ligne] = await res.json();
  if (!ligne?.donnees) throw new Error("colis introuvable");
  // compteur best-effort (ne bloque jamais l'import)
  fetch(`${SUPABASE_URL}/rest/v1/rpc/compter_telechargement`, {
    method: "POST",
    headers: entetes(),
    body: JSON.stringify({ p_id: id }),
  }).catch(() => {});
  return ligne.donnees;
}

async function soumettre(colis, session) {
  const res = await requeter(REST, {
    method: "POST",
    headers: { ...entetes(session.token), Prefer: "return=minimal" },
    body: JSON.stringify({
      auteur: session.userId,
      nom: colis.nom,
      description: colis.description,
      pays: colis.pays,
      donnees: colis,
      nb_points: colis.points.length,
    }),
  });
  if (!res.ok) {
    if (serveurAbsent(res)) throw new Error("indisponible");
    throw new Error(`envoi refusé (${res.status})`);
  }
}

/* ------------------------------------------------------------------ */
/* Colis : construction (partage) et contrôle (import)                 */
/* ------------------------------------------------------------------ */

/** Construit le colis partageable d'une catégorie perso : thème + points,
 *  SANS photos ni champs inconnus. Renvoie { colis } ou { erreur }. */
function construireColis(theme, points, description) {
  const feats = points.slice(0, MAX_POINTS).map((f) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: f.geometry.coordinates.slice(0, 2) },
    properties: {
      name: String(f.properties.name || "").slice(0, 120),
      description: String(f.properties.description || "").slice(0, 500),
      details: f.properties.details && typeof f.properties.details === "object"
        ? f.properties.details : {},
      links: (f.properties.links || [])
        .filter((l) => /^https?:\/\//.test(l?.url || ""))
        .slice(0, 3)
        .map((l) => ({ label: String(l.label || "Lien").slice(0, 60), url: String(l.url).slice(0, 300) })),
    },
  }));
  if (!feats.length) return { erreur: "Cette catégorie ne contient aucun point à partager." };
  const colis = {
    formatVersion: 1,
    nom: String(theme.label || "").slice(0, 60),
    description: String(description || "").slice(0, 500),
    pays: paysActuel().id,
    theme: {
      label: String(theme.label || "").slice(0, 40),
      color: String(theme.color || "#6c757d").slice(0, 20),
      textColor: String(theme.textColor || "#ffffff").slice(0, 20),
      icon: String(theme.icon || "📍").slice(0, 8),
    },
    points: feats,
  };
  if (points.length > MAX_POINTS) {
    return { erreur: `Trop de points (${points.length}) — le plafond est de ${MAX_POINTS}.` };
  }
  if (JSON.stringify(colis).length > MAX_OCTETS) {
    return { erreur: "Catégorie trop volumineuse (plus de 1 Mo hors photos)." };
  }
  return { colis };
}

/** Vérifie et NORMALISE un colis téléchargé (données tierces : zéro confiance).
 *  Renvoie { theme, points } prêts pour l'import, ou lève une erreur. */
function controlerColis(colis, idPartage) {
  if (!colis || !Array.isArray(colis.points) || !colis.theme) throw new Error("colis illisible");
  const themeId = `comm-${idPartage.slice(0, 8)}`;
  const theme = {
    id: themeId,
    label: String(colis.theme.label || colis.nom || "Communauté").slice(0, 40),
    color: /^#[0-9a-fA-F]{3,8}$/.test(colis.theme.color) ? colis.theme.color : "#6c757d",
    textColor: /^#[0-9a-fA-F]{3,8}$/.test(colis.theme.textColor) ? colis.theme.textColor : "#ffffff",
    icon: String(colis.theme.icon || "📍").slice(0, 8),
  };
  const points = [];
  colis.points.slice(0, MAX_POINTS).forEach((f, i) => {
    const c = f?.geometry?.coordinates;
    const lon = Number(c?.[0]), lat = Number(c?.[1]);
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return;
    const nom = String(f.properties?.name || "").trim().slice(0, 120);
    if (!nom) return;
    points.push({
      type: "Feature",
      geometry: { type: "Point", coordinates: [lon, lat] },
      properties: {
        id: `${themeId}-${String(i + 1).padStart(4, "0")}`, // stable → réimport idempotent
        name: nom,
        theme: themeId,
        description: String(f.properties?.description || "").slice(0, 500),
        links: (f.properties?.links || [])
          .filter((l) => /^https?:\/\//.test(l?.url || ""))
          .slice(0, 3)
          .map((l) => ({ label: String(l.label || "Lien").slice(0, 60), url: String(l.url).slice(0, 300) })),
        photos: [],
        details: Object.fromEntries(
          Object.entries(f.properties?.details || {})
            .slice(0, 20)
            .map(([k, v]) => [String(k).slice(0, 40), typeof v === "number" ? v : String(v).slice(0, 200)])
        ),
      },
    });
  });
  if (!points.length) throw new Error("aucun point valide dans ce colis");
  return { theme, points };
}

/* ------------------------------------------------------------------ */
/* Interface (dialogue à deux volets)                                  */
/* ------------------------------------------------------------------ */

function drapeauPays(id) {
  return PAYS[id]?.drapeau || "🌍";
}

async function rendreExplorer() {
  const zone = dialog.querySelector("#comm-explorer");
  zone.innerHTML = `<p class="menu-note">Chargement…</p>`;
  let liste;
  try {
    liste = await listerValidees();
  } catch (e) {
    zone.innerHTML =
      e.message === "indisponible"
        ? `<p class="menu-note">La bibliothèque communautaire n'est pas encore ouverte — elle arrive bientôt !</p>`
        : e.message === "réseau"
          ? `<p class="menu-note">Bibliothèque injoignable — êtes-vous en ligne ?</p>`
          : `<p class="menu-note">Bibliothèque injoignable (${esc(e.message)}). Réessayez plus tard.</p>`;
    return;
  }
  if (!liste.length) {
    zone.innerHTML = `<p class="menu-note">Aucune catégorie publiée pour l'instant — partagez la vôtre !</p>`;
    return;
  }
  zone.innerHTML = liste
    .map((c) => {
      const deja = cb.estImportee?.(`comm-${c.id.slice(0, 8)}`);
      return `
      <div class="comm-carte">
        <div class="comm-infos">
          <strong>${drapeauPays(c.pays)} ${esc(c.nom)}</strong>
          <span class="comm-meta">${c.nb_points} point(s) · ${c.telechargements} import(s)</span>
          ${c.description ? `<span class="comm-desc">${esc(c.description)}</span>` : ""}
        </div>
        <button type="button" class="btn btn-secondary comm-importer" data-id="${esc(c.id)}"
          ${deja ? "disabled" : ""}>${deja ? "✓ Importée" : "📥 Importer"}</button>
      </div>`;
    })
    .join("");
  zone.querySelectorAll(".comm-importer").forEach((btn) =>
    btn.addEventListener("click", async () => {
      btn.disabled = true;
      btn.textContent = "…";
      try {
        const colis = await telechargerColis(btn.dataset.id);
        const { theme, points } = controlerColis(colis, btn.dataset.id);
        await cb.importerCategorie(theme, points);
        btn.textContent = "✓ Importée";
        toast(`Catégorie « ${theme.label} » ajoutée à votre carte (${points.length} points).`);
      } catch (e) {
        btn.disabled = false;
        btn.textContent = "📥 Importer";
        toast(`Import impossible : ${e.message}`);
      }
    })
  );
}

async function rendrePartager() {
  const zone = dialog.querySelector("#comm-partager");
  const session = await sessionCommunaute();
  if (!session) {
    zone.innerHTML = `
      <p class="menu-note">Partager demande un compte (le même que la synchronisation) :
        votre catégorie sera relue avant publication.</p>
      <button type="button" class="btn btn-primary" id="comm-connexion">Se connecter avec Google</button>`;
    zone.querySelector("#comm-connexion").addEventListener("click", () => demanderConnexion());
    return;
  }
  const cats = await cb.getMesCategories();
  if (!cats.length) {
    zone.innerHTML = `<p class="menu-note">Créez d'abord une catégorie personnelle (bouton ➕ de la carte,
      ou import d'un fichier) — vous pourrez ensuite la partager ici.</p>`;
    return;
  }
  zone.innerHTML = `
    <p class="menu-note">Choisissez une de VOS catégories. Après relecture (contenu, données,
      droits), elle sera publiée pour tous. Les photos ne sont pas partagées.</p>
    ${cats
      .map(
        (c) => `
      <div class="comm-carte">
        <div class="comm-infos"><strong>${esc(c.icon)} ${esc(c.label)}</strong>
          <span class="comm-meta">${c.nbPoints} point(s)</span></div>
        <button type="button" class="btn btn-secondary comm-envoyer" data-id="${esc(c.id)}"
          ${c.nbPoints ? "" : "disabled"}>🌍 Partager</button>
      </div>`
      )
      .join("")}
    <textarea id="comm-description" maxlength="500" rows="2"
      placeholder="Une phrase pour décrire la catégorie partagée (facultatif)…"></textarea>`;
  zone.querySelectorAll(".comm-envoyer").forEach((btn) =>
    btn.addEventListener("click", async () => {
      const cat = cats.find((c) => c.id === btn.dataset.id);
      const description = zone.querySelector("#comm-description").value.trim();
      if (!(await confirmer(
        `Partager « ${cat.label} » (${cat.nbPoints} points) ? Elle sera relue avant publication.`
      ))) return;
      btn.disabled = true;
      btn.textContent = "…";
      try {
        const points = await cb.getPointsDeTheme(cat.id);
        const { colis, erreur } = construireColis(cat, points, description);
        if (erreur) throw new Error(erreur);
        await soumettre(colis, session);
        btn.textContent = "✓ Envoyée";
        toast("Merci ! Votre catégorie est en file de relecture — publiée après validation.");
      } catch (e) {
        btn.disabled = false;
        btn.textContent = "🌍 Partager";
        toast(
          e.message === "indisponible"
            ? "Le partage n'est pas encore ouvert côté serveur — bientôt !"
            : `Envoi impossible : ${e.message}`
        );
      }
    })
  );
}

function basculerVolet(volet) {
  dialog.querySelectorAll(".comm-onglet").forEach((o) =>
    o.classList.toggle("actif", o.dataset.volet === volet)
  );
  dialog.querySelector("#comm-explorer").hidden = volet !== "explorer";
  dialog.querySelector("#comm-partager").hidden = volet !== "partager";
  if (volet === "explorer") rendreExplorer();
  else rendrePartager();
}

/** Ouvre le dialogue communauté sur le volet demandé. */
export function ouvrirCommunaute(volet = "explorer") {
  basculerVolet(volet);
  dialog.showModal();
}

export function initCommunaute(callbacks) {
  cb = callbacks;
  dialog = document.getElementById("communaute-dialog");
  dialog.querySelector(".communaute-close").addEventListener("click", () => dialog.close());
  dialog.querySelectorAll(".comm-onglet").forEach((o) =>
    o.addEventListener("click", () => basculerVolet(o.dataset.volet))
  );
  // fermer d'un tap sur le fond (comme les autres dialogues)
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) dialog.close();
  });
}
