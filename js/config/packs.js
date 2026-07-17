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

export const PACKS = [
  {
    id: "montagne",
    label: "Montagne",
    icon: "🏔️",
    color: "#2d6a4f",
    categories: ["randonnee", "via-ferrata", "escalade", "canyon", "grotte",
                 "refuge", "sommet-croix", "col-mythique"],
  },
  {
    id: "nature",
    label: "Nature & eau",
    icon: "🌿",
    color: "#0096c7",
    categories: ["cascade", "lac", "eau", "ciel-etoile"],
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
    label: "Road trip & services",
    icon: "🚐",
    color: "#606c38",
    categories: ["camping", "toilettes", "eau", "refuge", "cite-caractere"],
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

/** Enregistre les packs créés par l'utilisateur (au boot, après lecture). */
export function registerCustomPacks(liste) {
  customPacks = (liste || []).map((p) => ({ categories: [], ...p }));
}

/** Tous les packs affichables, par défaut d'abord (ordre de déclaration). */
export function allPacks() {
  return [...PACKS, ...customPacks];
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
