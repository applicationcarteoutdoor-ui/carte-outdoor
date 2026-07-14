// Registre des PAYS de la carte. Chaque pays définit son fichier de points,
// sa surcouche de grands itinéraires (GR en France, Great Walks en NZ), les
// catégories disponibles et sa vue de départ. Le pays choisi est mémorisé dans
// une clé localStorage dédiée, lue de façon SYNCHRONE au chargement du module
// (le boot et map.js en ont besoin avant toute promesse).
//
// AJOUTER UN PAYS = une entrée ici + les fichiers data/<pays>/… + (option)
// masquer les catégories absentes via `categories`. Les ids de points doivent
// être préfixés par pays (ex. nz-hut-0001) : les statuts et le carnet — COMMUNS
// à tous les pays — pointent sur ces ids, aucune collision possible.

const CLE = "carte-outdoor:pays";

export const PAYS = {
  fr: {
    id: "fr",
    drapeau: "🇫🇷",
    label: "France",
    sousTitre: "~12 400 lieux : escalade, canyons, cascades, châteaux, refuges… + toilettes, eau et spéléo",
    fichierPoints: "data/points.geojson",
    // Surcouche de grands itinéraires cliquables (fiche + GPX) ;
    // `fiche` = sous-titre affiché dans la fiche d'un itinéraire cliqué
    gr: { fichier: "data/gr.geojson", label: "Sentiers GR", compte: 190, fiche: "Sentier de grande randonnée" },
    // Tracés des randonnées (bouton GPX + dessin au clic)
    fichierRandos: "data/randos.geojson",
    // null = toutes les catégories de themes.js
    categories: null,
    // Catégories de base sans données pour ce pays (masquées en attendant)
    categoriesExclues: ["camping"],
    // Couches volumineuses à la demande (toilettes/eau/grottes) : France seulement
    couchesLourdes: true,
    vue: { center: [46.5, 2.6], zoom: 6 },
    wikiLang: "fr",
  },
  nz: {
    id: "nz",
    drapeau: "🇳🇿",
    label: "Nouvelle-Zélande",
    sousTitre: "Huttes et campings du DOC, Great Walks, lacs, cascades, grottes, villages…",
    fichierPoints: "data/nz/points.geojson",
    // Escalade : pas de source libre en NZ (106 objets OSM, topos ClimbNZ
    // non ouverts) — catégorie volontairement absente, cf. rapport de revue.
    // `grotte` ici = catégorie NORMALE (~130 points dans points.geojson),
    // pas la couche lourde française (couchesLourdes: false la débranche).
    gr: { fichier: "data/nz/great-walks.geojson", label: "Great Walks", compte: 11, fiche: "Great Walk" },
    fichierRandos: "data/nz/randos.geojson",
    categories: ["via-ferrata", "randonnee", "refuge", "camping", "grotte", "lac", "cascade",
                 "chateau", "cathedrale", "cite-caractere", "culture"],
    couchesLourdes: false,
    vue: { center: [-41.3, 172.6], zoom: 6 },
    wikiLang: "en",
  },
};

/** Id du pays mémorisé, ou null si l'utilisateur n'a pas encore choisi. */
export function paysChoisi() {
  const id = localStorage.getItem(CLE);
  return PAYS[id] ? id : null;
}

/** Configuration du pays actuel (France par défaut tant que rien n'est choisi :
 *  les modules peuvent s'initialiser, la page de garde tranche au boot). */
export function paysActuel() {
  return PAYS[paysChoisi() || "fr"];
}

/** Mémorise le pays (le boot ou le changement de pays rechargent la page). */
export function definirPays(id) {
  if (PAYS[id]) localStorage.setItem(CLE, id);
}
