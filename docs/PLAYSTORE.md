# Publier Carte Outdoor sur le Google Play Store

La PWA est empaquetée en **TWA** (*Trusted Web Activity*) : une vraie appli
Android qui affiche le site en plein écran, sans barre d'adresse. C'est la
méthode officielle pour publier une PWA sur le Play Store. Le site reste la
seule source : chaque `git push` met à jour l'app du Store **sans repasser par
Google**.

## Déjà prêt dans le dépôt

- ✅ `manifest.webmanifest` complet (nom, icônes 192/512 `maskable`,
  `display: standalone`) — validé par PWABuilder.
- ✅ Service worker + HTTPS (GitHub Pages).
- ✅ [`.well-known/assetlinks.json`](../.well-known/assetlinks.json) — le lien
  officiel entre le domaine et l'app Android (il masque la barre d'adresse).
  L'empreinte `sha256_cert_fingerprints` est un **placeholder à remplacer**
  (étape 5).
- ✅ `.nojekyll` — sans lui, GitHub Pages ne servirait pas le dossier
  `.well-known` (Jekyll ignore les dossiers commençant par un point).

## Étapes (~1 h, 25 $ une seule fois)

### 1. Compte développeur Google Play
[play.google.com/console/signup](https://play.google.com/console/signup) —
25 $ une fois, à vie. (Compte « personnel » suffisant.)

### 2. Générer le paquet Android avec PWABuilder
1. Aller sur [pwabuilder.com](https://www.pwabuilder.com), coller
   `https://applicationcarteoutdoor-ui.github.io/carte-outdoor/` → *Start*.
2. *Package for stores* → **Android** → options :
   - **Package ID** : `io.github.applicationcarteoutdoor_ui.carteoutdoor`
     (exactement celui de `assetlinks.json`, sinon le remplacer dans le fichier).
   - App name : `SpotMap` (fiche Store suggérée : « SpotMap : spots outdoor &
     rando » pour se distinguer de l'appli « Spotmap » existante) ; le reste
     par défaut. ⚠️ Un paquet généré AVANT le renommage v62 (ancien nom/icônes)
     est périmé : toujours regénérer sur le site à jour.
3. Télécharger le zip : il contient le **`.aab`** (à téléverser sur Play) et
   un **fichier de signature (`signing.keystore` + mots de passe)**.
   **⚠️ CONSERVER précieusement le keystore et ses mots de passe** (hors du
   dépôt git !) : ils seront exigés pour toute mise à jour du paquet.

### 3. Créer l'application dans la Play Console
*Créer une application* → nom `Carte Outdoor`, langue français, type
Application, gratuite. Remplir les fiches obligatoires (description,
confidentialité, captures d'écran — des captures du site suffisent).

### 4. Téléverser le `.aab`
*Production → Créer une release* → glisser le `.aab` → suivre les écrans.
Accepter la **signature d'application par Google Play** (recommandé).

### 5. Relier le domaine (masquer la barre d'adresse)
1. Play Console → *Configuration → Signature d'application* → copier
   l'**empreinte SHA-256** du certificat.
2. La coller dans
   [`.well-known/assetlinks.json`](../.well-known/assetlinks.json) à la place
   du placeholder (garder les `:` de l'empreinte).
3. `git add -A && git commit && git push` — vérifier ensuite que
   `https://applicationcarteoutdoor-ui.github.io/.well-known/assetlinks.json`
   répond bien (⚠️ le fichier est servi à la **racine du domaine github.io**,
   c'est normal et c'est là que Google le cherche).

### 6. Publier
Envoyer en **test interne** d'abord (lien d'installation immédiat pour soi),
puis en production. La première revue Google prend de quelques heures à
quelques jours.

## ⚠️ À faire aussi : l'écran de consentement Google (connexion)

Pour que **n'importe qui** puisse utiliser « Se connecter avec Google » (et pas
seulement les comptes de test) : Google Cloud Console → *APIs & Services →
OAuth consent screen* → **Publish app** (passer de « Testing » à
« In production »). Sans cela, la connexion échoue pour les autres après 100
utilisateurs de test / 7 jours de jetons.

## Notes

- Le nom de domaine `github.io` appartient à GitHub : le Package ID
  `io.github.…` reflète le sous-domaine — c'est accepté par le Play Store.
- Mises à jour de CONTENU : un simple `git push` (les utilisateurs du Store
  reçoivent la nouvelle version au lancement suivant, comme sur le web).
  Seul un changement d'icône/nom d'app/écran de démarrage nécessite de
  régénérer un `.aab` (PWABuilder, mêmes keystore et Package ID, versionCode +1).
