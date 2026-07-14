/**
 * Partage de l'application : QR code affiché en grand, partage natif
 * (navigator.share : messagerie, e-mail, WhatsApp…) et copie du lien.
 * Le QR (img/qr-site.svg) est généré une fois pour toutes par
 * tools/generer_qr.py — il encode l'URL publique du site.
 */

import { toast } from "./import-export.js";

const URL_SITE = "https://applicationcarteoutdoor-ui.github.io/carte-outdoor/";

export function initPartage() {
  const dlg = document.getElementById("partage-dialog");

  document.getElementById("btn-partage").addEventListener("click", () => dlg.showModal());
  dlg.querySelector(".partage-close").addEventListener("click", () => dlg.close());

  // Partage natif : proposé seulement si l'appareil le gère (téléphones,
  // navigateurs récents) — sinon le bouton est masqué, le QR et la copie suffisent.
  const btnNatif = document.getElementById("btn-partage-natif");
  if (navigator.share) {
    btnNatif.addEventListener("click", async () => {
      try {
        await navigator.share({
          title: "SpotMap",
          text: "Découvre SpotMap : via ferrata, refuges, cascades, lacs, randonnées…",
          url: URL_SITE,
        });
      } catch {
        /* partage annulé par l'utilisateur : rien à signaler */
      }
    });
  } else {
    btnNatif.hidden = true;
  }

  document.getElementById("btn-copier-lien").addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(URL_SITE);
      toast("Lien copié !");
    } catch {
      toast(URL_SITE); // repli : afficher l'URL pour une copie manuelle
    }
  });
}
