/**
 * Badges (v77) : des objectifs débloqués depuis les données LOCALES (carnet,
 * statuts « ✓ Fait », traces GPX). Aucune donnée ne part sur un serveur —
 * tout se calcule sur le téléphone (voir js/profil.js).
 *
 * Un badge = { id (stable), icone, titre, description, metrique, palier }.
 * `metrique` pointe une clé de l'objet `stats` calculé par profil.js, ou
 * `theme:<id>` pour compter les lieux « faits » d'une catégorie précise.
 * Ajouter un badge = une entrée ici (rien d'autre à toucher).
 */

export const BADGES = [
  { id: "premiers-pas", icone: "👣", titre: "Premiers pas",
    description: "Première sortie enregistrée", metrique: "sorties", palier: 1 },
  { id: "explorateur", icone: "🧭", titre: "Explorateur",
    description: "10 lieux visités", metrique: "lieux", palier: 10 },
  { id: "grand-explorateur", icone: "🗺️", titre: "Grand explorateur",
    description: "50 lieux visités", metrique: "lieux", palier: 50 },
  { id: "centurion", icone: "💯", titre: "Centurion",
    description: "100 lieux visités", metrique: "lieux", palier: 100 },
  { id: "aventurier", icone: "🌟", titre: "Aventurier",
    description: "250 lieux visités", metrique: "lieux", palier: 250 },
  { id: "deux-pays", icone: "🌍", titre: "Frontalier",
    description: "Des sorties dans 2 pays", metrique: "pays", palier: 2 },
  { id: "globe-trotteur", icone: "✈️", titre: "Globe-trotteur",
    description: "Des sorties dans 5 pays", metrique: "pays", palier: 5 },
  { id: "curieux", icone: "🎨", titre: "Touche-à-tout",
    description: "5 catégories différentes explorées", metrique: "categories", palier: 5 },
  { id: "encyclopediste", icone: "📚", titre: "Encyclopédiste",
    description: "10 catégories différentes explorées", metrique: "categories", palier: 10 },
  { id: "randonneur", icone: "🥾", titre: "Randonneur",
    description: "10 randonnées faites", metrique: "theme:randonnee", palier: 10 },
  { id: "grimpeur", icone: "🧗", titre: "Grimpeur",
    description: "10 sites d'escalade ou via ferrata",
    metrique: "theme:escalade+via-ferrata", palier: 10 },
  { id: "sommet", icone: "⛰️", titre: "Sommets",
    description: "5 sommets à croix ou cols", metrique: "theme:sommet-croix+col-mythique", palier: 5 },
  { id: "chatelain", icone: "🏰", titre: "Châtelain",
    description: "10 châteaux visités", metrique: "theme:chateau", palier: 10 },
  { id: "marcheur", icone: "👟", titre: "Marcheur",
    description: "100 km enregistrés (traces GPX)", metrique: "km", palier: 100 },
  { id: "ultra", icone: "🏃", titre: "Ultra",
    description: "1 000 km enregistrés", metrique: "km", palier: 1000 },
  { id: "alpiniste", icone: "🏔️", titre: "Alpiniste",
    description: "10 000 m de dénivelé positif cumulé", metrique: "dplus", palier: 10000 },
];

/** Valeur atteinte pour la métrique d'un badge, depuis l'objet stats. */
export function valeurMetrique(metrique, stats) {
  if (metrique.startsWith("theme:")) {
    return metrique.slice(6).split("+")
      .reduce((somme, t) => somme + (stats.parTheme?.[t] || 0), 0);
  }
  return stats[metrique] || 0;
}
