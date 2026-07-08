# Vidéo de lancement — « Le dimanche où il ne savait pas quoi faire »

Durée : **13 s** (tient dans les 10-15 s demandées). Format : **9:16** (1080 × 1920) pour Play Store, Instagram, TikTok. Une version 16:9 se recadre ensuite.

Le fil : *un type s'ennuie → il ouvre l'app → il touche un point → il y est → il se prend en photo → la photo se colle dans son carnet.* Tout tient sur une seule idée : **l'app transforme un dimanche vide en souvenir**.

---

## 1. Ce qui est déjà prêt

Les captures de l'application, en vraies images (780 × 1688, format téléphone) :

| Fichier | Ce qu'on y voit | Sert au plan |
|---|---|---|
| `captures/carte.png` | La carte, massif du Mont-Blanc, épingles et grappes de spots | 2 |
| `captures/fiche.png` | La fiche « Via ferrata de Ancelle » (cotation, Google Maps, carnet) | 3 |
| `captures/carnet.png` | La page du grimoire : photo en polaroïd + note manuscrite | 7 |
| `captures/carnet-photo.png` | La photo ouverte en plein écran, avec Télécharger | bonus |
| `captures/oracle.png` | La boule de cristal (mode Gratuit) | variante du plan 2 |

Régénérables à volonté : `python tools/dev_server.py 8125` dans un terminal, puis `python dev/video/capturer.py`.

⚠️ **`selfie-placeholder.jpg` est une silhouette dessinée**, pas une vraie photo. Une fois le tournage fait : remplacer ce fichier par la vraie photo du héros, relancer `capturer.py`, et la page du carnet contiendra **sa** photo. C'est ce détail qui rendra la fin crédible.

---

## 2. Le découpage, plan par plan

| # | Temps | Plan | Texte à l'écran | Son |
|---|---|---|---|---|
| 1 | 0,0 → 1,6 s | Il est avachi dans son canapé, téléphone à la main, il soupire. Lumière grise de dimanche. | « Dimanche. Rien de prévu. » | Silence, une horloge |
| 2 | 1,6 → 3,2 s | Plan serré sur l'écran : `carte.png`, la carte se peuple d'épingles, léger zoom avant | — | *Whoosh* + musique qui démarre |
| 3 | 3,2 → 4,4 s | Son pouce touche une épingle → `fiche.png` remonte depuis le bas | « Via ferrata de Ancelle » | *Tap* net |
| 4 | 4,4 → 5,4 s | **La téléportation** : on plonge DANS l'épingle, flash blanc, la carte devient la vraie montagne | — | Montée + coup sourd |
| 5 | 5,4 → 7,6 s | Il est sur la via ferrata : câble, vide sous lui, vallée immense. Il sourit. | — | Vent, mousquetons |
| 6 | 7,6 → 9,2 s | Bras levé, il se prend en photo. **Flash + arrêt sur image** | — | *Clic* d'obturateur |
| 7 | 9,2 → 11,4 s | L'arrêt sur image devient un polaroïd qui tombe dans le grimoire : `carnet.png`, la note s'écrit à la plume | « Je ne savais pas quoi faire de mon week-end. Maintenant si. » | Plume qui gratte |
| 8 | 11,4 → 13,0 s | Fond sombre, logo, accroche | **Carte Outdoor**<br>7 400 spots. Ton carnet d'aventures.<br>*applicationcarteoutdoor-ui.github.io/carte-outdoor* | Musique qui retombe |

**La règle d'or du plan 4** : le mouvement doit être *continu*. On zoome sur l'épingle brune de la fiche, le flash blanc couvre la coupe, et le plan suivant démarre déjà en mouvement (caméra qui recule sur la falaise). C'est ce raccord qui donne la téléportation.

---

## 3. Les prompts (à coller dans l'outil de génération)

Trois plans seulement sont à générer ou à filmer : **1** (le canapé), **5** (la via ferrata), **6** (le selfie). Les autres sont les captures de l'app.

Les IA vidéo comprennent mieux l'anglais : le prompt anglais est la version à coller, le français est là pour que tu saches ce qu'il dit.

### Plan 1 — L'ennui (1,6 s)

> **EN** — *Vertical 9:16. A young man in his late twenties slumped on a grey sofa in a dim living room, overcast Sunday light through the window, phone loose in his hand, he exhales and stares at the ceiling, bored. Static shot, 35mm lens, shallow depth of field, muted desaturated colors, cinematic, photorealistic. Subtle slow push-in. No text, no logo.*
>
> **FR** — Un homme d'une trentaine d'années affalé sur un canapé gris, lumière grise de dimanche, téléphone mou dans la main, il souffle et fixe le plafond. Plan fixe, léger travelling avant, couleurs désaturées, photoréaliste.

Négatif : `text, watermark, distorted hands, extra fingers, cartoon`

### Plan 5 — La via ferrata (2,2 s)

> **EN** — *Vertical 9:16. A hiker in a helmet and harness clipped to a steel cable on a vertical limestone via ferrata, deep alpine valley far below, late afternoon golden light, French Alps. Camera pulls back and slightly up, revealing the drop. Handheld energy, natural motion blur, photorealistic, cinematic color grade, 24mm wide lens.*
>
> **FR** — Un randonneur casqué et encordé sur une via ferrata verticale, vallée alpine loin en contrebas, lumière dorée de fin d'après-midi. La caméra recule et monte pour révéler le vide. Grand-angle, photoréaliste.

Négatif : `text, watermark, floating body, wrong anatomy, fake plastic rock`

### Plan 6 — Le selfie (1,6 s)

> **EN** — *Vertical 9:16. Same hiker standing on a rocky summit, raises his arm holding a phone to take a selfie, wind in his jacket, huge mountain panorama behind him, golden hour. The frame freezes for an instant as the shutter fires, a soft white flash. Photorealistic, cinematic, 35mm.*
>
> **FR** — Le même randonneur, debout sur une arête, lève le bras avec son téléphone pour un selfie, vent dans la veste, panorama immense derrière lui. L'image se fige au déclenchement, léger flash blanc.

Négatif : `text, watermark, deformed phone, extra arms`

### Plan 4 — La transition (facultatif, 1 s)

Souvent plus propre à faire au montage (zoom + flash) qu'à générer. Si tu veux l'essayer en IA :

> **EN** — *Vertical 9:16. Extreme close-up push into a brown map pin on a phone screen, the screen dissolves into a real alpine cliff face, seamless morph transition, white flash at the midpoint, cinematic, photorealistic.*

### Cohérence du personnage

Génère le **plan 5 d'abord**, garde son image, puis pour le plan 6 utilise la fonction **image-to-video** (Runway Gen-3, Kling) en partant de la dernière image du plan 5 : le personnage, sa veste et la lumière restent identiques. Sinon, tu auras deux hommes différents — l'erreur classique.

### Quel outil ?

- **Veo 3** (via Gemini) : le seul qui génère aussi le **son** (vent, obturateur). Le plus simple pour toi.
- **Runway Gen-3** : le meilleur en *image-to-video*, donc pour la continuité du personnage.
- **Kling** : très bon sur les morphs (le plan 4).

---

## 4. Les plans de l'app : capture ou enregistrement d'écran ?

Les PNG suffisent si tu les animes au montage (zoom lent, glissement de la fiche). Mais **un enregistrement d'écran est plus vivant** pour le plan 3 (le doigt qui touche l'épingle) :

- **Téléphone** : ouvre le site, lance l'enregistrement d'écran d'Android/iOS, touche l'épingle, ouvre le carnet. Tu filmes le vrai geste.
- **Ordinateur** : Chrome → F12 → mode téléphone (Ctrl+Maj+M) → enregistre la fenêtre avec OBS.

Dis-moi si tu veux d'autres états capturés (l'Oracle qui donne une réponse, le carnet qui se feuillette, le mode nuit) : `capturer.py` sait déjà les mettre en scène, il suffit d'ajouter une scène.

---

## 5. Montage

- **CapCut** (gratuit, mobile ou PC) suffit largement. DaVinci Resolve si tu veux étalonner.
- **Musique** : quelque chose qui démarre discret et s'ouvre au plan 4. Libre de droits : YouTube Audio Library, Pixabay Music, Uppbeat. Cherche « uplifting cinematic adventure ».
- **Zone de sécurité** : sur 9:16, garde les textes entre 15 % et 85 % de la hauteur — les interfaces des réseaux mangent les bords.
- **Fin** : la dernière image (logo + URL) doit rester **au moins 1,5 s** et lisible sans le son.
- **Sous-titres** : incruste les textes à l'écran. 85 % des gens regardent sans le son.

---

## 6. Ce qui rend cette vidéo honnête

Tout ce qui est montré de l'application est **réel** : la carte, les 7 400 points, la fiche, le grimoire. Rien n'est une maquette. Le seul élément fabriqué est le héros — et c'est normal, c'est une fiction.

Ne surpromets pas : pas de « l'IA planifie ton week-end » si le mode Gratuit ne fait pas ça. La promesse tenue par l'app est plus belle et plus simple : **« Tu ne sais pas quoi faire ? Voilà 7 400 idées, et un carnet pour t'en souvenir. »**
