/**
 * Détection de la plateforme, partagée entre modules : liens d'itinéraire
 * (ouvrir l'appli Google Maps / Waze plutôt que leur site) et bouton
 * d'installation (invite native sur Android, mode d'emploi sur iOS).
 */

/* Les iPad récents se présentent comme des Mac : l'écran tactile les trahit. */
export const SUR_IOS =
  /iphone|ipad|ipod/i.test(navigator.userAgent) ||
  (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);

export const SUR_ANDROID = /android/i.test(navigator.userAgent);
