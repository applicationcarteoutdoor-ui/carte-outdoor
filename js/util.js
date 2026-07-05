/**
 * Utilitaires partagés.
 *
 * Un SEUL point de vérité pour l'échappement HTML : `esc()` échappe aussi les
 * guillemets, donc son résultat est sûr dans le contenu d'un élément COMME
 * dans une valeur d'attribut (`value="${esc(x)}"`, `data-nom="${esc(x)}"`…).
 * L'ancienne astuce `div.textContent` n'échappait pas les guillemets : une
 * valeur contenant `"` pouvait s'échapper d'un attribut (injection). C'est
 * important car les noms de points et les libellés de catégories peuvent
 * provenir d'un fichier de sauvegarde importé (donc d'un tiers).
 */

/** Échappe &, <, >, " et ' — sûr pour le contenu et les attributs HTML. */
export function esc(texte) {
  return String(texte ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/** Alias historique (certains modules l'appelaient « echapper »). */
export const echapper = esc;
