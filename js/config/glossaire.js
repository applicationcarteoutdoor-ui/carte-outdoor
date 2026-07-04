/**
 * Glossaire centralisé des acronymes et cotations.
 *
 * ★ Pour ajouter une infobulle sur un nouvel acronyme, ajoutez simplement
 * une entrée ici : tout texte affiché via glossaireHTML() et toutes les
 * pastilles de filtre dont la valeur figure dans ce glossaire reçoivent
 * automatiquement une infobulle au survol.
 */

export const GLOSSAIRE = {
  // Cotations via ferrata (échelle Hüsler adaptée)
  F: "Facile",
  PD: "Peu Difficile",
  AD: "Assez Difficile",
  D: "Difficile",
  TD: "Très Difficile",
  ED: "Extrêmement Difficile",

  // Sigles courants
  GR: "Grande Randonnée",
  "D+": "Dénivelé positif cumulé",
  "D-": "Dénivelé négatif cumulé",
  PMR: "Personnes à Mobilité Réduite.",
  "A/R": "Aller / Retour.",
};

/** Définition d'un terme, ou chaîne vide. */
export function definir(terme) {
  return GLOSSAIRE[terme] || "";
}

function echapper(texte) {
  const div = document.createElement("div");
  div.textContent = texte ?? "";
  return div.innerHTML;
}

// Termes triés du plus long au plus court pour que « D+ » gagne sur « D »
const TERMES = Object.keys(GLOSSAIRE).sort((a, b) => b.length - a.length);
const RE_TERMES = new RegExp(
  `(^|[^\\w+-])(${TERMES.map((t) => t.replace(/[+\-]/g, "\\$&")).join("|")})(?![\\w+-])`,
  "g"
);

/**
 * Échappe un texte et enveloppe chaque acronyme connu dans un
 * <span class="glossary-term" data-tip="…"> qui affiche l'infobulle au survol.
 */
export function glossaireHTML(texte) {
  return echapper(texte).replace(
    RE_TERMES,
    (tout, avant, terme) =>
      `${avant}<span class="glossary-term" tabindex="0" data-tip="${echapper(GLOSSAIRE[terme])}">${terme}</span>`
  );
}
