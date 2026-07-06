/**
 * Mini harnais de tests — invariants du code (pures, sans DOM ni base).
 *
 * Ouvrir /dev/tests.html via le serveur de dev. Aucune donnée utilisateur
 * n'est touchée : on ne teste que des fonctions pures (échappement, filtrage,
 * résolution des thèmes). Le but est d'attraper les régressions silencieuses.
 */

import { esc } from "../js/util.js";
import { passeFiltre } from "../js/filtrage.js";
import {
  getTheme,
  registerCustomThemes,
  setThemeOverrides,
  FALLBACK_THEME,
} from "../js/config/themes.js";

const liste = document.getElementById("liste");
let pass = 0;
let fail = 0;

function check(nom, cond) {
  const li = document.createElement("li");
  li.className = cond ? "pass" : "fail";
  li.textContent = nom;
  liste.appendChild(li);
  cond ? pass++ : fail++;
}
const S = (...v) => new Set(v);

/* --- util.esc : échappement sûr pour le contenu ET les attributs --------- */
check("esc échappe <>", esc("<b>") === "&lt;b&gt;");
check("esc échappe &", esc("a&b") === "a&amp;b");
check('esc échappe le guillemet double "', esc('x"y') === "x&quot;y");
check("esc échappe l'apostrophe '", esc("x'y") === "x&#39;y");
check("esc gère null/undefined", esc(null) === "" && esc(undefined) === "");
check("esc neutralise une injection d'attribut", !esc('"><img onerror=x>').includes('"'));

/* --- filtrage.passeFiltre : cœur du filtrage des points ------------------ */
check("sélection vide = « Tout »", passeFiltre({ type: "value", field: "x" }, { x: "a" }, S()) === true);
check("value : correspond", passeFiltre({ type: "value", field: "tarif" }, { tarif: "Gratuit" }, S("Gratuit")));
check("value : ne correspond pas", !passeFiltre({ type: "value", field: "tarif" }, { tarif: "Payant" }, S("Gratuit")));
check("value : champ absent = « »", passeFiltre({ type: "value", field: "etat" }, {}, S("")));
check("tokens : cotation contient AD", passeFiltre({ type: "tokens", field: "c" }, { c: "PD/AD" }, S("AD")));
check("tokens : cotation ne contient pas ED", !passeFiltre({ type: "tokens", field: "c" }, { c: "PD/AD" }, S("ED")));
check("prefix : commence par", passeFiltre({ type: "prefix", field: "t" }, { t: "Site sportif équipé" }, S("Site sportif")));
check("prefix : ne commence pas par", !passeFiltre({ type: "prefix", field: "t" }, { t: "Terrain d'aventure" }, S("Site sportif")));
check("contains : inclut le motif", passeFiltre({ type: "contains", field: "c" }, { c: "poele à bois" }, S("poele")));
const bucket = { type: "bucket", field: "n", options: [{ value: "v2", min: 20, max: 50 }] };
check("bucket : 30 dans [20,50)", passeFiltre(bucket, { n: 30 }, S("v2")));
check("bucket : 20 inclus (min inclusif)", passeFiltre(bucket, { n: 20 }, S("v2")));
check("bucket : 50 exclu (max exclusif)", !passeFiltre(bucket, { n: 50 }, S("v2")));
check("bucket : valeur non numérique exclue", !passeFiltre(bucket, { n: "?" }, S("v2")));

/* --- themes : fallback, catégories perso, surcharges --------------------- */
check("thème inconnu → repli « autre »", getTheme("inexistant").id === FALLBACK_THEME.id);
check("thème de base conserve son id", getTheme("refuge").id === "refuge");
registerCustomThemes([{ id: "perso-test", label: "Perso", color: "#123456", icon: "⭐" }]);
check("catégorie perso résolue", getTheme("perso-test").label === "Perso");
setThemeOverrides({ refuge: { label: "Cabane" } });
check("surcharge change le label", getTheme("refuge").label === "Cabane");
check("surcharge conserve l'id stable", getTheme("refuge").id === "refuge");
// Nettoyage de l'état de module (cette page est isolée, mais restons propres)
setThemeOverrides({});
registerCustomThemes([]);

/* --- Résumé -------------------------------------------------------------- */
const resume = document.getElementById("resume");
resume.textContent = `${pass} réussis · ${fail} échoué${fail > 1 ? "s" : ""}`;
resume.className = fail ? "ko" : "ok";
document.title = (fail ? "✗ " : "✓ ") + document.title;
