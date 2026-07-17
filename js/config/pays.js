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
    // Couches volumineuses à la demande (id de catégorie → fichier de points,
    // NON pré-caché). v67 : toilettes + eau existent pour TOUS les pays ;
    // grottes (Grottocenter) et musées restent des couches France.
    couchesLourdes: {
      toilettes: "data/toilettes.geojson",
      eau: "data/eau.geojson",
      grotte: "data/grottes.geojson",
      culture: "data/culture.geojson",
    },
    vue: { center: [46.5, 2.6], zoom: 6 },
    wikiLang: "fr",
  },
  ch: {
    id: "ch",
    drapeau: "🇨🇭",
    label: "Suisse",
    sousTitre: "Cabanes et refuges, lacs, cascades, via ferrata, musées et plus beaux villages",
    fichierPoints: "data/ch/points.geojson",
    gr: null, // pas encore de surcouche de grands itinéraires (Via Alpina à venir)
    fichierRandos: "data/ch/randos.geojson",
    categories: ["via-ferrata", "randonnee", "refuge", "camping", "grotte", "lac", "cascade",
                 "chateau", "cite-caractere", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/ch/toilettes.geojson", eau: "data/ch/eau.geojson" },
    vue: { center: [46.8, 8.2], zoom: 8 },
    wikiLang: "fr",
  },
  it: {
    id: "it",
    drapeau: "🇮🇹",
    label: "Italie",
    sousTitre: "Refuges des Dolomites, via ferrata, lacs, châteaux, musées et borghi più belli",
    fichierPoints: "data/it/points.geojson",
    gr: null,
    fichierRandos: "data/it/randos.geojson",
    categories: ["via-ferrata", "randonnee", "refuge", "camping", "grotte", "lac", "cascade",
                 "chateau", "cite-caractere", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/it/toilettes.geojson", eau: "data/it/eau.geojson" },
    vue: { center: [42.6, 12.5], zoom: 6 },
    wikiLang: "it",
  },
  es: {
    id: "es",
    drapeau: "🇪🇸",
    label: "Espagne",
    sousTitre: "Refuges des Pyrénées et Picos, via ferrata, lacs, châteaux et pueblos bonitos",
    fichierPoints: "data/es/points.geojson",
    gr: null,
    fichierRandos: "data/es/randos.geojson",
    categories: ["via-ferrata", "randonnee", "refuge", "camping", "grotte", "lac", "cascade",
                 "chateau", "cite-caractere", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/es/toilettes.geojson", eau: "data/es/eau.geojson" },
    vue: { center: [40.2, -3.6], zoom: 6 },
    wikiLang: "es",
  },
  pt: {
    id: "pt",
    drapeau: "🇵🇹",
    label: "Portugal",
    sousTitre: "Aldeias históricas, châteaux, lacs, cascades et grottes du Portugal",
    fichierPoints: "data/pt/points.geojson",
    gr: null,
    categories: ["chateau", "cite-caractere", "grotte", "lac", "cascade", "camping",
                 "refuge", "via-ferrata", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/pt/toilettes.geojson", eau: "data/pt/eau.geojson" },
    vue: { center: [39.5, -8.0], zoom: 7 },
    wikiLang: "pt",
  },
  de: {
    id: "de",
    drapeau: "🇩🇪",
    label: "Allemagne",
    sousTitre: "Châteaux de légende, refuges alpins, lacs, via ferrata et musées d'Allemagne",
    fichierPoints: "data/de/points.geojson",
    gr: null,
    categories: ["via-ferrata", "refuge", "camping", "grotte", "lac", "cascade",
                 "chateau", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/de/toilettes.geojson", eau: "data/de/eau.geojson" },
    vue: { center: [51.2, 10.3], zoom: 6 },
    wikiLang: "de",
  },
  nl: {
    id: "nl",
    drapeau: "🇳🇱",
    label: "Pays-Bas",
    sousTitre: "Campings, lacs, châteaux, grottes de marne et musées des Pays-Bas",
    fichierPoints: "data/nl/points.geojson",
    gr: null,
    // plat pays : pas de via ferrata ni de refuges (1-2 objets OSM anecdotiques)
    categories: ["camping", "grotte", "lac", "cascade", "chateau", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/nl/toilettes.geojson", eau: "data/nl/eau.geojson" },
    vue: { center: [52.2, 5.4], zoom: 7 },
    wikiLang: "nl",
  },
  lu: {
    id: "lu",
    drapeau: "🇱🇺",
    label: "Luxembourg",
    sousTitre: "Châteaux, cascades du Mullerthal, campings et musées du Luxembourg",
    fichierPoints: "data/lu/points.geojson",
    gr: null,
    categories: ["camping", "grotte", "lac", "cascade", "chateau", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/lu/toilettes.geojson", eau: "data/lu/eau.geojson" },
    vue: { center: [49.8, 6.1], zoom: 9 },
    wikiLang: "fr",
  },
  be: {
    id: "be",
    drapeau: "🇧🇪",
    label: "Belgique",
    sousTitre: "Plus Beaux Villages de Wallonie, châteaux, grottes et cascades des Ardennes",
    fichierPoints: "data/be/points.geojson",
    gr: null,
    categories: ["chateau", "cite-caractere", "grotte", "cascade", "lac", "camping",
                 "refuge", "via-ferrata", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/be/toilettes.geojson", eau: "data/be/eau.geojson" },
    vue: { center: [50.5, 4.7], zoom: 8 },
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
    // pas la couche lourde française (absente de couchesLourdes ci-dessous).
    gr: { fichier: "data/nz/great-walks.geojson", label: "Great Walks", compte: 11, fiche: "Great Walk" },
    fichierRandos: "data/nz/randos.geojson",
    categories: ["via-ferrata", "randonnee", "refuge", "camping", "grotte", "lac", "cascade",
                 "chateau", "cathedrale", "cite-caractere", "culture", "toilettes", "eau"],
    couchesLourdes: { toilettes: "data/nz/toilettes.geojson", eau: "data/nz/eau.geojson" },
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
