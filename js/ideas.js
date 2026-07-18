/**
 * Boîte à idées 💡
 *
 * Les suggestions sont conservées localement (localStorage) pour pouvoir
 * les relire, et un bouton prépare un e-mail (mailto) contenant toutes les
 * idées — l'application étant 100 % statique, il n'y a pas de serveur pour
 * les recevoir automatiquement.
 */

import { esc } from "./util.js";
import { toast } from "./import-export.js";

const KEY = "carte-outdoor:idees";
const EMAIL = "Applicationcarteoutdoor@gmail.com";

let dialog = null;

function lireIdees() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) || [];
  } catch {
    return [];
  }
}

function ecrireIdees(idees) {
  localStorage.setItem(KEY, JSON.stringify(idees));
}

export function initIdeas() {
  dialog = document.getElementById("ideas-dialog");
  document.getElementById("btn-ideas").addEventListener("click", () => {
    render();
    dialog.showModal();
  });
  dialog.querySelector(".ideas-close").addEventListener("click", () => dialog.close());

  dialog.querySelector(".ideas-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const champ = dialog.querySelector(".ideas-form textarea");
    const texte = champ.value.trim();
    if (!texte) return;
    const idees = lireIdees();
    idees.push({ date: new Date().toISOString(), text: texte });
    ecrireIdees(idees);
    champ.value = "";
    render();
  });

  dialog.querySelector(".ideas-mail").addEventListener("click", async () => {
    // Le texte EN COURS DE FRAPPE part aussi : l'utilisateur écrit puis touche
    // directement ✉️ sans passer par « Ajouter » — il était perdu (vécu).
    const champ = dialog.querySelector(".ideas-form textarea");
    const enCours = champ.value.trim();
    if (enCours) {
      const idees = lireIdees();
      idees.push({ date: new Date().toISOString(), text: enCours });
      ecrireIdees(idees);
      champ.value = "";
      render();
    }
    const idees = lireIdees();
    if (!idees.length) {
      toast("Aucune idée à envoyer — écrivez-en une d'abord 🙂");
      return;
    }
    const corps = idees.map((i) => `- [${i.date.slice(0, 10)}] ${i.text}`).join("\r\n");
    // Filet : certaines messageries (Android surtout) ouvrent le brouillon en
    // ignorant le corps du mailto — le texte est donc AUSSI copié, prêt à coller.
    try {
      await navigator.clipboard.writeText(corps);
    } catch { /* presse-papiers refusé : le mailto reste tenté tel quel */ }
    location.href =
      `mailto:${EMAIL}?subject=${encodeURIComponent("Idées SpotMap")}` +
      `&body=${encodeURIComponent(corps)}`;
    // Une fois envoyées, les idées sont VIDÉES automatiquement (demande v76) :
    // plus besoin de les supprimer à la main. Copie de secours faite au cas où.
    ecrireIdees([]);
    render();
    toast("Idées envoyées et effacées ✉️ (une copie reste dans le presse-papiers).");
  });
}

function render() {
  const zone = dialog.querySelector(".ideas-list");
  const idees = lireIdees();
  zone.textContent = "";
  if (!idees.length) {
    zone.innerHTML = '<p class="list-empty">Aucune idée pour le moment — lancez-vous !</p>';
    return;
  }
  idees
    .slice()
    .reverse()
    .forEach((idee) => {
      const date = new Date(idee.date).toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric",
      });
      const item = document.createElement("div");
      item.className = "idea-item";
      item.innerHTML =
        `<div class="idea-text"><time>${esc(date)}</time><p>${esc(idee.text)}</p></div>` +
        '<button type="button" class="btn-icon idea-delete" title="Supprimer">🗑</button>';
      item.querySelector(".idea-delete").addEventListener("click", () => {
        ecrireIdees(lireIdees().filter((i) => !(i.date === idee.date && i.text === idee.text)));
        render();
      });
      zone.appendChild(item);
    });
}
