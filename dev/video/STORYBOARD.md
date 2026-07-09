# Vidéo de lancement — « Il ne savait pas quoi faire »

Durée : **13 s**. Format : **9:16** (1080 × 1920) pour le Play Store, Instagram, TikTok.

Le fil : *il s'ennuie → il touche une via ferrata, il y est → il touche un château, il y est → il touche une grotte, il y est → les trois photos atterrissent dans son carnet.*

**La règle de trois.** Une téléportation, c'est un gadget. Trois, c'est une promesse : *tout ce que tu touches, tu peux le vivre.* Et les trois lieux disent ce qu'aucun plan unique ne dirait — l'application ne parle pas d'escalade, elle parle de **7 400 façons de sortir de chez soi**.

---

## 1. Le découpage

| # | Temps | Plan | Texte à l'écran | Son |
|---|---|---|---|---|
| 1 | 0 → 1,2 s | Avachi sur son canapé, lumière grise de dimanche, il soupire | « Dimanche. Rien de prévu. » | Une horloge, puis rien |
| 2 | 1,2 → 2,2 s | `carte.png` : la carte se peuple d'épingles, zoom avant | — | *Whoosh*, la musique démarre |
| 3 | 2,2 → 4,2 s | **VIA FERRATA** — tap sur l'épingle (`fiche-viaferrata.png`) → plongée dans l'épingle → il est sur le câble, le vide dessous → **flash** | — | *Tap*, vent, **clic d'obturateur** |
| 4 | 4,2 → 6,2 s | **CHÂTEAU** — tap (`fiche-chateau.png`) → il est devant Chambord, contre-plongée → **flash** | — | *Tap*, corbeaux, **clic** |
| 5 | 6,2 → 8,2 s | **GROTTE** — tap (`fiche-grotte.png`) → il est sous terre, lampe frontale → **flash** | — | *Tap*, goutte d'eau, **clic** |
| 6 | 8,2 → 11,2 s | Le grimoire s'ouvre. Les trois photos se collent une à une, la plume écrit | « Une journée. Trois souvenirs. » | Plume qui gratte, page qui tourne |
| 7 | 11,2 → 13 s | Fond sombre, logo | **Carte Outdoor**<br>7 400 spots. Ton carnet d'aventures.<br>*applicationcarteoutdoor-ui.github.io/carte-outdoor* | La musique retombe |

**Le battement.** Chaque bloc de 2 s se découpe en `0,5 s de tap → 1 s sur place → 0,5 s de flash`. Les **trois flashs** sont la respiration de la vidéo : cale-les sur les temps forts de la musique et la vidéo se monte toute seule. Ne filme pas le personnage en train de sortir son téléphone : **le flash EST la photo**. C'est plus rapide et plus élégant.

**Le raccord de téléportation** (le seul truc à réussir) : zoome dans l'épingle de la fiche jusqu'à ce que sa couleur remplisse l'écran, coupe sur un **flash blanc de 3 images**, et démarre le plan suivant *déjà en mouvement* (caméra qui recule). Le cerveau recolle tout seul.

---

## 2. Ce qui est déjà prêt : les captures de l'app

Vraies images de l'application, dans `captures/` (780 × 1688, sauf la double page).

| Fichier | Plan | Ce qu'on y voit |
|---|---|---|
| `carte.png` | 2 | La carte, massif du Mont-Blanc, épingles et grappes |
| `fiche-viaferrata.png` | 3 | Fiche « Via ferrata de Chamonix » |
| `fiche-chateau.png` | 4 | Fiche « Chambord », avec sa photo |
| `fiche-grotte.png` | 5 | Fiche « Aven d'Orgnac » |
| `carnet-p1.png` `carnet-p2.png` `carnet-p3.png` | 6 | Les trois pages du grimoire (grotte, château, via ferrata) |
| `carnet-double.png` | 6 (variante) | **Le grimoire ouvert en double page : deux souvenirs d'un coup** |
| `carnet-photo.png` | bonus | Une photo du carnet en plein écran |
| `oracle.png` | bonus | La boule de cristal |

Régénérer : `python tools/dev_server.py 8125` dans un terminal, puis `python dev/video/capturer.py` (ou `python dev/video/capturer.py carnet-double` pour une seule scène).

### ⚠️ Une contrainte réelle, à connaître avant de monter

Sur un téléphone, **le carnet affiche une entrée par page** (mesuré : « page 1 / 3 »). Les trois photos ne tiennent donc **pas** sur une seule page verticale. Trois façons de faire le plan 6, par ordre de préférence :

1. **Le feuilletage** (le plus beau et le plus vrai) : `carnet-p1` → `carnet-p2` → `carnet-p3`, 0,6 s chacune, avec le bruit de page. Trois photos, trois pages, trois souvenirs.
2. **La double page** : `carnet-double.png` (format tablette) montre deux entrées côte à côte. Superbe en 16:9.
3. Composer un montage de trois polaroïds qui tombent sur une page — joli, mais ce n'est plus l'écran réel de l'app. À éviter : la sincérité est ton meilleur argument.

### Les photos du carnet

`photos/via-ferrata.jpg`, `photos/chateau.jpg`, `photos/grotte.jpg` sont des **illustrations de substitution** que j'ai dessinées. Une fois le tournage fait : remplace ces trois fichiers par les vraies photos, relance `capturer.py`, et les pages du grimoire contiendront **ses** photos. C'est ce détail qui rendra la fin vraie — le carnet de la vidéo sera littéralement le carnet de l'app.

---

## 3. Les prompts

Quatre plans à générer ou filmer : le canapé, et les trois arrivées. Les modèles répondent mieux en anglais ; le français est là pour que tu saches ce que tu colles.

### Plan 1 — L'ennui (1,2 s)

> **EN** — *Vertical 9:16. A man in his late twenties slumped on a grey sofa in a dim living room, overcast Sunday light through the window, phone loose in his hand, he exhales and stares at the ceiling, bored. Static shot with a very slow push-in, 35mm lens, shallow depth of field, muted desaturated colors, photorealistic, cinematic.*
>
> **FR** — Un homme d'une trentaine d'années affalé sur un canapé gris, lumière grise de dimanche, téléphone mou dans la main. Il souffle, fixe le plafond. Plan fixe, très lent travelling avant, couleurs désaturées.

### Plan 3 — L'arrivée sur la via ferrata (1 s)

> **EN** — *Vertical 9:16. A man in a helmet and harness suddenly standing on a vertical limestone cliff, clipped to a steel cable, a deep alpine valley thousands of feet below, French Alps, late afternoon golden light. The camera pulls back and tilts up to reveal the drop. Handheld energy, natural motion blur, 24mm wide lens, photorealistic, cinematic color grade.*
>
> **FR** — Un homme casqué et encordé, debout sur une falaise verticale, câble d'acier, vallée alpine très loin en dessous, lumière dorée. La caméra recule et bascule vers le haut pour révéler le vide.

### Plan 4 — L'arrivée au château (1 s)

> **EN** — *Vertical 9:16. The same man standing in front of the château de Chambord at golden hour, low angle looking up at the towers and chimneys, reflecting pool in the foreground, warm light, few tourists. Slow camera rise. Photorealistic, cinematic, 28mm.*
>
> **FR** — Le même homme devant le château de Chambord à l'heure dorée, contre-plongée sur les tours, bassin au premier plan. La caméra s'élève lentement.

### Plan 5 — L'arrivée dans la grotte (1 s)

> **EN** — *Vertical 9:16. The same man deep inside a vast limestone cave, wearing a headlamp, its beam sweeping across enormous stalactites, wet rock glistening, total darkness beyond the light. Camera slowly orbits him. Photorealistic, cinematic, high contrast, 24mm.*
>
> **FR** — Le même homme au fond d'une immense grotte calcaire, lampe frontale, faisceau balayant d'énormes stalactites, roche humide qui brille, noir total au-delà. La caméra tourne lentement autour de lui.

**Prompt négatif, pour les quatre** : `text, watermark, logo, distorted hands, extra fingers, deformed face, cartoon, plastic look`

### La continuité du personnage — le point qui rate le plus souvent

Trois lieux = trois chances d'obtenir trois hommes différents. La méthode :

1. Génère **le plan 3** (via ferrata) jusqu'à obtenir un personnage qui te plaît.
2. Extrais une image de ce plan où on voit bien son visage et sa veste.
3. Pour les plans 4 et 5, utilise le mode **image-to-video** (Runway Gen-3, Kling) en partant de cette image, et décris seulement le *nouveau décor*.

Sans ça, ta vidéo racontera l'histoire de trois personnes, et personne ne comprendra.

### Quel outil ?

- **Veo 3** (dans Gemini) : le seul qui génère aussi **le son** — vent, gouttes, obturateur. Le plus simple si tu ne veux pas bricoler la bande-son.
- **Runway Gen-3** : le meilleur en *image-to-video*, donc pour la continuité du personnage.
- **Kling** : le plus fort sur les morphs, si tu veux tenter les transitions épingle → décor en génération plutôt qu'au montage.

---

## 4. Les plans de l'app : capture ou enregistrement d'écran ?

Les PNG suffisent si tu les animes (zoom lent, fiche qui glisse). Mais pour les trois **taps**, un enregistrement d'écran est plus vivant — on voit le vrai doigt, le vrai geste :

- **Téléphone** : ouvre le site, lance l'enregistrement d'écran, touche les trois épingles, ouvre le carnet.
- **Ordinateur** : Chrome → F12 → mode téléphone (Ctrl+Maj+M) → OBS pour enregistrer la fenêtre.

Besoin d'autres états (l'Oracle qui répond, le mode nuit, une page précise) ? `capturer.py` sait les mettre en scène : il suffit d'ajouter une scène dans `scene.js`.

---

## 5. Montage

- **CapCut** suffit (gratuit, PC ou mobile). DaVinci Resolve si tu veux étalonner.
- **Musique** : discrète au plan 1, elle s'ouvre au premier flash. Libre de droits : Pixabay Music, Uppbeat, YouTube Audio Library. Cherche *« uplifting cinematic adventure »*.
- **Les flashs** : 2 à 3 images de blanc pur, pas plus. Au-delà, ça pique.
- **Zone de sécurité 9:16** : garde les textes entre 15 % et 85 % de la hauteur, les interfaces des réseaux mangent les bords.
- **La dernière image** (logo + URL) reste **au moins 1,5 s**, lisible sans le son.
- **Sous-titres incrustés** : la majorité des gens regardent sans le son.

---

## 6. Rester honnête

Tout ce qui est montré de l'application est **réel** : la carte, les fiches, le grimoire, les photos de Chambord et de l'Aven d'Orgnac. Rien n'est une maquette. Le seul élément fabriqué est le héros — et c'est le propre d'une fiction.

Ne promets pas ce que l'app ne fait pas. Sa promesse tenue est déjà la bonne : **« Tu ne sais pas quoi faire ? Voilà 7 400 idées — et un carnet pour t'en souvenir. »**
