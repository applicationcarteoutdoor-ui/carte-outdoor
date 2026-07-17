/**
 * PACKS de catégories : le rangement de la sidebar (v72).
 *
 * Un pack = une liste ORDONNÉE d'ids de catégories (themes.js) — pure
 * présentation : cocher/décocher, l'exclusivité des couches lourdes et les
 * filtres restent l'affaire d'app.js, rien ne change pour les points.
 *
 * Trois couches, miroir exact de themes.js :
 *  - PACKS         : packs par défaut (ids STABLES à jamais) ;
 *  - customPacks   : packs créés par l'utilisateur (registerCustomPacks au
 *                    boot, localStorage carte-outdoor:customPacks, synchronisés) ;
 *  - packOverrides : personnalisation d'un pack par défaut — label, icône,
 *                    couleur ET `categories` (réordonner/retirer/ajouter sans
 *                    dupliquer le pack ; « Réinitialiser » restaure l'usine).
 *
 * Une catégorie peut vivre dans PLUSIEURS packs (cascade → Montagne ET
 * Nature). Un pack sans catégorie visible dans le pays courant est masqué.
 * Toujours passer par getPack()/allPacks() pour l'affichage.
 *
 * Ids RÉSERVÉS (éternels — ne jamais renommer, comme les ids de thèmes) :
 *  - packs à venir : sport, gastronomie, loisirs, professionnel ;
 *  - catégories à venir : panorama, plongee, phare, cascade-glace,
 *    arbre-remarquable (cf. feuille de route V2-V5).
 */

// Contenus VALIDÉS par l'utilisateur (v73-v74) — les ids de packs restent
// stables même quand le label change (nature → « Eau », road-trip →
// « Services »). RÈGLE des packs PAR DÉFAUT : une catégorie ne vit que dans
// UN SEUL pack (cocher deux packs qui se recouvrent est déroutant) — les
// packs PERSO, eux, mélangent ce qu'ils veulent.
export const PACKS = [
  {
    id: "montagne",
    label: "Montagne",
    icon: "🏔️",
    color: "#2d6a4f",
    categories: ["randonnee", "via-ferrata", "escalade", "grotte", "refuge"],
  },
  {
    id: "nature",
    label: "Eau",
    icon: "💧",
    color: "#0096c7",
    categories: ["cascade", "canyon", "lac", "eau", "plongee"],
  },
  {
    id: "paysages",
    label: "Paysages",
    icon: "🌄",
    color: "#b76935",
    categories: ["panorama", "sommet-croix", "col-mythique", "ciel-etoile",
                 "arbre-remarquable", "phare"],
  },
  {
    id: "culture",
    label: "Culture & patrimoine",
    icon: "🏛️",
    color: "#780000",
    categories: ["chateau", "cathedrale", "culture", "cite-caractere", "village-abandonne"],
  },
  {
    id: "road-trip",
    label: "Services",
    icon: "🚐",
    color: "#606c38",
    categories: ["camping", "toilettes"],
  },
];

/** Pack VIRTUEL « Mes catégories » : catégories perso/importées + celles où
 *  l'utilisateur a des points + « autre ». Contenu CALCULÉ au rendu par la
 *  sidebar (jamais stocké), masqué s'il est vide. */
export const PACK_MES_CATEGORIES = {
  id: "mes-categories",
  label: "Mes catégories",
  icon: "📌",
  color: "#3a86ff",
};

let customPacks = [];
let packOverrides = {};
let ordrePacks = []; // ordre d'affichage des TUILES choisi par l'utilisateur (pref)

/** Enregistre les packs créés par l'utilisateur (au boot, après lecture). */
export function registerCustomPacks(liste) {
  customPacks = (liste || []).map((p) => ({ categories: [], ...p }));
}

/** Mémorise l'ordre d'affichage des packs (l'utilisateur place ses tuiles). */
export function setOrdrePacks(liste) {
  ordrePacks = Array.isArray(liste) ? liste : [];
}

export function getOrdrePacks() {
  return [...ordrePacks];
}

/** Tous les packs affichables, dans l'ORDRE choisi par l'utilisateur
 *  (les packs absents de sa liste s'ajoutent à la suite, ordre d'usine). */
export function allPacks() {
  const tous = [...PACKS, ...customPacks];
  if (!ordrePacks.length) return tous;
  const rang = new Map(ordrePacks.map((id, i) => [id, i]));
  return tous.slice().sort((a, b) =>
    (rang.has(a.id) ? rang.get(a.id) : 999) - (rang.has(b.id) ? rang.get(b.id) : 999));
}

function baseDe(id) {
  return PACKS.find((p) => p.id === id) || customPacks.find((p) => p.id === id) || null;
}

/** Pack prêt à afficher : base + personnalisation éventuelle. */
export function getPack(id) {
  const base = baseDe(id);
  if (!base) return null;
  const o = packOverrides[base.id] || {};
  return {
    ...base,
    ...(o.label ? { label: o.label } : {}),
    ...(o.icon ? { icon: o.icon } : {}),
    ...(o.color ? { color: o.color } : {}),
    ...(Array.isArray(o.categories) && o.categories.length ? { categories: o.categories } : {}),
  };
}

/** Pack d'usine, sans personnalisation (bouton « Réinitialiser »). */
export function getDefaultPack(id) {
  return baseDe(id);
}

export function setPackOverrides(nouvelles) {
  packOverrides = nouvelles || {};
}

export function packExists(id) {
  return !!baseDe(id) || id === PACK_MES_CATEGORIES.id;
}

/** Vrai pour un pack créé par l'utilisateur (→ supprimable). */
export function isCustomPack(id) {
  return customPacks.some((p) => p.id === id);
}

/** Ids des packs contenant la catégorie (multi-appartenance permise). */
export function packsDeCategorie(themeId) {
  return allPacks().filter((p) => getPack(p.id).categories.includes(themeId)).map((p) => p.id);
}
