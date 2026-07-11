/**
 * Configuration des catégories de points d'intérêt.
 *
 * ★ C'est LE fichier à modifier pour ajouter une catégorie :
 *   - id        : identifiant STABLE et unique (kebab-case). Stocké dans les
 *                 données des points — il ne doit JAMAIS changer, même si le
 *                 nom affiché change.
 *   - label     : nom affiché (personnalisable dans l'application)
 *   - color     : couleur de fond (marqueur, pastille)
 *   - textColor : couleur du texte/icône sur ce fond
 *   - icon      : emoji du marqueur
 *   - fields    : champs affichés dans la fiche détaillée
 *   - filters   : filtres proposés quand la catégorie est cochée (voir ci-dessous)
 *
 * Schéma d'un filtre :
 *   { key, label, type, field, options: [{value, label?, icon?, min?, max?}] }
 *   - type "tokens" : le champ contient des cotations (F, PD, AD…) ; le point
 *                     passe si l'une des cotations sélectionnées y figure
 *   - type "prefix" : le champ commence par l'une des valeurs sélectionnées
 *   - type "value"  : le champ vaut exactement l'une des valeurs
 *   - type "bucket" : le champ (numérique, suffixe _n) tombe dans l'une des
 *                     tranches sélectionnées [min, max)
 *   Aucune sélection = « Tout » (pas de filtrage).
 */

export const THEMES = [
  {
    id: "via-ferrata",
    label: "Via ferrata",
    color: "#e63946",
    icon: "🧗",
    fields: [
      { key: "cotation", label: "Cotation" },
      { key: "parcours", label: "Nombre de parcours" },
      { key: "longueur", label: "Longueur" },
      { key: "denivele", label: "Dénivelé" },
      { key: "duree", label: "Durée" },
      { key: "materiel", label: "Matériel requis" },
      { key: "tyrolienne", label: "Tyrolienne" },
    ],
    filters: [
      {
        key: "cotation",
        label: "Cotation",
        type: "tokens",
        field: "cotation",
        options: [
          { value: "F" }, { value: "PD" }, { value: "AD" },
          { value: "D" }, { value: "TD" }, { value: "ED" },
        ],
      },
      {
        key: "tyrolienne",
        label: "Tyrolienne",
        type: "value",
        field: "tyrolienne_type",
        options: [
          { value: "oui", label: "Avec tyrolienne", icon: "🚡" },
          { value: "non", label: "Sans" },
        ],
      },
    ],
  },
  {
    id: "escalade",
    label: "Escalade",
    color: "#d62828",
    icon: "🪨",
    fields: [
      { key: "cotation", label: "Cotations" },
      { key: "type", label: "Type de site" },
      { key: "voies", label: "Nombre de voies" },
      { key: "corde", label: "Longueur de corde" },
      { key: "approche", label: "Marche d'approche" },
      { key: "orientation", label: "Orientation" },
    ],
    filters: [
      {
        key: "type",
        label: "Type de site",
        type: "prefix",
        field: "type",
        options: [
          { value: "Site sportif", icon: "🧗" },
          { value: "Terrain d'aventure", icon: "🏔️" },
          { value: "Site de bloc", icon: "🪨" },
        ],
      },
      {
        key: "voies",
        label: "Nombre de voies",
        type: "bucket",
        field: "voies_n",
        options: [
          { value: "v1", label: "< 20", max: 20 },
          { value: "v2", label: "20 à 50", min: 20, max: 50 },
          { value: "v3", label: "> 50", min: 50 },
        ],
      },
      {
        key: "corde",
        label: "Longueur de corde",
        type: "bucket",
        field: "corde_n",
        options: [
          { value: "c1", label: "≤ 50 m", icon: "🪢", max: 51 },
          { value: "c2", label: "51 à 70 m", min: 51, max: 71 },
          { value: "c3", label: "> 70 m", min: 71 },
        ],
      },
      {
        key: "approche",
        label: "Marche d'approche",
        type: "bucket",
        field: "approche_n",
        options: [
          { value: "a1", label: "≤ 10 min", icon: "🚶", max: 11 },
          { value: "a2", label: "11 à 30 min", min: 11, max: 31 },
          { value: "a3", label: "> 30 min", min: 31 },
        ],
      },
    ],
  },
  {
    // Randonnées remarquables — sélection éditoriale (sommets à voie normale
    // documentée, objectifs emblématiques), validée par Wikipédia et OSM.
    // PILOTE : massif de la Chartreuse uniquement (extension France à venir —
    // le filtre « Massif » est prévu pour accueillir les massifs suivants).
    // Convention : le point est placé au SOMMET/objectif de la randonnée,
    // jamais au parking ; details.depart donne le départ classique.
    id: "randonnee",
    label: "Randonnée",
    color: "#2d6a4f",
    icon: "🥾",
    fields: [
      { key: "altitude", label: "Altitude" },
      { key: "denivele", label: "Dénivelé (estimation)" },
      { key: "distance", label: "Distance" },
      { key: "duree", label: "Durée" },
      { key: "depart", label: "Départ classique" },
      { key: "acces", label: "Voie normale" },
      { key: "itineraire", label: "Itinéraire balisé (OSM)" },
      { key: "massif", label: "Massif" },
    ],
    // Filtres par effort : durée, dénivelé positif et distance, en tranches
    // (buckets lisant les champs numériques duree_n / denivele_n / distance_n
    // posés par tools/completer_stats_randos.py).
    filters: [
      {
        key: "duree",
        label: "Durée",
        type: "bucket",
        field: "duree_n",
        options: [
          { value: "d1", label: "< 2 h", icon: "⏱️", max: 2 },
          { value: "d2", label: "2 à 4 h", min: 2, max: 4 },
          { value: "d3", label: "4 à 6 h", min: 4, max: 6 },
          { value: "d4", label: "> 6 h", min: 6 },
        ],
      },
      {
        key: "denivele",
        label: "Dénivelé (D+)",
        type: "bucket",
        field: "denivele_n",
        options: [
          { value: "e1", label: "< 500 m", icon: "📈", max: 500 },
          { value: "e2", label: "500 à 1000 m", min: 500, max: 1000 },
          { value: "e3", label: "> 1000 m", min: 1000 },
        ],
      },
      {
        key: "distance",
        label: "Distance",
        type: "bucket",
        field: "distance_n",
        options: [
          { value: "s1", label: "< 5 km", icon: "📏", max: 5 },
          { value: "s2", label: "5 à 10 km", min: 5, max: 10 },
          { value: "s3", label: "> 10 km", min: 10 },
        ],
      },
    ],
  },
  {
    id: "grotte",
    label: "Grotte",
    color: "#7f5539",
    icon: "🕳️",
    fields: [
      { key: "type", label: "Type" },
      { key: "duree", label: "Durée de visite" },
      { key: "equipement", label: "Équipement" },
      { key: "horaires", label: "Horaires" },
      { key: "tarif", label: "Tarif" },
    ],
    filters: [],
  },
  {
    id: "cascade",
    label: "Cascade",
    color: "#0096c7",
    icon: "💦",
    fields: [
      { key: "hauteur", label: "Hauteur de chute" },
      { key: "altitude", label: "Altitude" },
    ],
    // « Fiche » : Référencée (photo + informations) / À vérifier (incomplète).
    // Le champ details.fiche est posé par le pipeline de données.
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencée", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    // Sélection qualitative : uniquement les lacs ayant un article Wikipédia
    // (lacs de montagne, grands lacs, étangs célèbres) — pas les plans d'eau
    // anonymes. Données : Wikipédia + Wikidata, altitudes complétées par OSM.
    id: "lac",
    label: "Lac",
    color: "#1a659e",
    icon: "🏞️",
    fields: [
      { key: "altitude", label: "Altitude" },
      { key: "superficie", label: "Superficie" },
      { key: "profondeur", label: "Profondeur max" },
    ],
    // « Fiche » : Référencé (photo + informations) / À vérifier (incomplète).
    // Le champ details.fiche est posé par le pipeline de données.
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "alt1", label: "Plaine (< 600 m)", max: 600 },
          { value: "alt2", label: "600 à 1 500 m", min: 600, max: 1500 },
          { value: "alt3", label: "Montagne (> 1 500 m)", icon: "🏔️", min: 1500 },
        ],
      },
    ],
  },
  {
    // Une seule catégorie Château (l'ancienne « chateau-a-verifier » a été
    // fusionnée ici en v45 : c'est le filtre « Fiche » qui distingue les
    // châteaux documentés de ceux restant à confirmer).
    id: "chateau",
    label: "Château",
    color: "#9d4edd",
    icon: "🏰",
    fields: [
      { key: "periode", label: "Période" },
      { key: "horaires", label: "Horaires" },
      { key: "tarif", label: "Tarif" },
      { key: "accessibilite", label: "Accessibilité" },
    ],
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    id: "cathedrale",
    label: "Cathédrale",
    color: "#3d5a80",
    icon: "⛪",
    fields: [
      { key: "style", label: "Style" },
      { key: "periode", label: "Période" },
    ],
    filters: [],
  },
  {
    // Une seule catégorie « Village » : les Cités de caractère du fichier
    // source (211) ET les Plus Beaux Villages de France (récolte enrichisseur)
    // y cohabitent, distingués par le filtre « Label » (details.label, type
    // contains : un village peut cumuler les deux labels).
    id: "cite-caractere", // id historique STABLE — ne jamais renommer
    label: "Village",
    color: "#f77f00",
    icon: "🏘️",
    fields: [
      { key: "label", label: "Label" },
    ],
    filters: [
      {
        key: "label",
        label: "Label",
        type: "contains",
        field: "label",
        options: [
          { value: "Plus Beaux Villages", label: "Plus beau village de France", icon: "⭐" },
          { value: "Cité de caractère", label: "Cité de caractère", icon: "🏘️" },
        ],
      },
    ],
  },
  {
    id: "refuge",
    label: "Refuge",
    color: "#996633",
    icon: "🛖",
    fields: [
      { key: "capacite", label: "Capacité" },
      { key: "altitude", label: "Altitude" },
      { key: "chauffage", label: "Chauffage" },
      { key: "eau", label: "Eau à moins de 100 m" },
      { key: "latrines", label: "Latrines" },
      { key: "couvertures", label: "Couvertures" },
      { key: "etat", label: "État" },
      { key: "contact", label: "Contact" },
    ],
    filters: [
      {
        key: "chauffage",
        label: "Chauffage",
        type: "contains",
        field: "chauffage_type",
        options: [
          { value: "poele", label: "Poêle à bois", icon: "🔥" },
          { value: "cheminee", label: "Cheminée", icon: "🪵" },
          { value: "aucun", label: "Aucun", icon: "❄️" },
        ],
      },
      {
        key: "places",
        label: "Nombre de places",
        type: "bucket",
        field: "places_n",
        options: [
          { value: "p1", label: "1 à 4", icon: "🛏️", max: 5 },
          { value: "p2", label: "5 à 9", icon: "🛏️", min: 5, max: 10 },
          { value: "p3", label: "10 et +", icon: "🛏️", min: 10 },
        ],
      },
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "a1", label: "< 1000 m", max: 1000 },
          { value: "a2", label: "1000 à 1500 m", min: 1000, max: 1500 },
          { value: "a3", label: "1500 à 2000 m", min: 1500, max: 2000 },
          { value: "a4", label: "> 2000 m", min: 2000 },
        ],
      },
      {
        key: "etat",
        label: "État",
        type: "value",
        field: "etat",
        options: [
          { value: "", label: "Ouverte", icon: "🔓" },
          { value: "Clé à récupérer avant", label: "Clé à récupérer", icon: "🔑" },
          { value: "Fermée", label: "Fermée", icon: "🚫" },
        ],
      },
    ],
  },
  {
    id: "toilettes",
    label: "Toilettes",
    color: "#8d99ae",
    icon: "🚻",
    fields: [
      { key: "tarif", label: "Tarif" },
      { key: "accessibilite", label: "Accès PMR" },
      { key: "acces", label: "Accès" },
      { key: "equipement", label: "Équipement" },
      { key: "horaires", label: "Horaires" },
    ],
    filters: [
      {
        key: "tarif",
        label: "Tarif",
        type: "value",
        field: "tarif",
        options: [
          { value: "Gratuit", icon: "🆓" },
          { value: "Payant", icon: "💰" },
        ],
      },
      {
        key: "pmr",
        label: "Accès PMR",
        type: "value",
        field: "pmr_type",
        options: [
          { value: "oui", label: "PMR", icon: "♿" },
          { value: "non", label: "Non PMR" },
        ],
      },
    ],
  },
];

/** Catégorie de repli pour les points dont la catégorie est inconnue
 *  (ex. anciens imports référençant une catégorie supprimée). */
export const FALLBACK_THEME = {
  id: "autre",
  label: "Autre",
  color: "#6c757d",
  icon: "📍",
  fields: [],
  filters: [],
};

const TEXT_COLOR_DEFAUT = "#ffffff";

const parId = new Map(THEMES.map((t) => [t.id, t]));

/** Catégories créées par l'utilisateur (fonction « ajouter un point »).
 *  Persistées par storage.js et enregistrées ici au démarrage. */
let customThemes = [];

export function registerCustomThemes(liste) {
  customThemes = (liste || []).map((t) => ({ fields: [], filters: [], ...t }));
}

/** Toutes les catégories connues (par défaut + personnalisées). */
export function allThemes() {
  return [...THEMES, ...customThemes];
}

function baseDe(id) {
  return parId.get(id) || customThemes.find((t) => t.id === id) || FALLBACK_THEME;
}

/** Surcharges utilisateur : { themeId: {label?, color?, textColor?, icon?} } */
let overrides = {};

export function setThemeOverrides(nouvelles) {
  overrides = nouvelles || {};
}

/** Définition d'une catégorie, personnalisations utilisateur incluses. */
export function getTheme(id) {
  const base = baseDe(id);
  const o = overrides[base.id];
  if (!o) return { textColor: TEXT_COLOR_DEFAUT, ...base };
  return {
    ...base,
    textColor: TEXT_COLOR_DEFAUT,
    ...Object.fromEntries(Object.entries(o).filter(([, v]) => v)),
  };
}

/** Valeurs par défaut (sans personnalisation) — pour « Réinitialiser ». */
export function getDefaultTheme(id) {
  return { textColor: TEXT_COLOR_DEFAUT, ...baseDe(id) };
}

export function themeExists(id) {
  return parId.has(id) || customThemes.some((t) => t.id === id);
}

/** Vrai pour les catégories créées/importées par l'utilisateur (supprimables),
 *  faux pour les catégories de base de l'application. */
export function isCustomTheme(id) {
  return customThemes.some((t) => t.id === id);
}
