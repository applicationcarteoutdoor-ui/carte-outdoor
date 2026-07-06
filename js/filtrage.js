/**
 * Logique de FILTRAGE des points — fonction pure, testable en isolation.
 *
 * `passeFiltre` évalue un filtre déclaré dans js/config/themes.js contre les
 * `details` d'un point. Sortie de app.js pour l'alléger ET pour pouvoir la
 * tester sans DOM ni état global (voir dev/tests.html).
 *
 * Types de filtre (détaillés dans l'en-tête de js/config/themes.js) :
 *   tokens · prefix · contains · value · bucket
 */

const RE_TOKENS = /\b(ED|TD|AD|PD|F|D)\b/g;

/**
 * Vrai si le point (via ses `details`) satisfait `filtre` pour la `selection`
 * de valeurs cochées (un Set). Une sélection vide/absente = « Tout » → true.
 */
export function passeFiltre(filtre, details, selection) {
  if (!selection || selection.size === 0) return true;
  const brut = details?.[filtre.field];
  switch (filtre.type) {
    case "tokens": {
      const tokens = String(brut || "").match(RE_TOKENS) || [];
      return tokens.some((t) => selection.has(t));
    }
    case "prefix":
      return [...selection].some((v) => String(brut || "").startsWith(v));
    case "contains":
      return [...selection].some((v) => String(brut || "").includes(v));
    case "value":
      return selection.has(String(brut ?? ""));
    case "bucket": {
      const n = Number(brut);
      if (!Number.isFinite(n)) return false;
      return filtre.options.some(
        (o) =>
          selection.has(o.value) &&
          (o.min === undefined || n >= o.min) &&
          (o.max === undefined || n < o.max)
      );
    }
  }
  return true;
}
