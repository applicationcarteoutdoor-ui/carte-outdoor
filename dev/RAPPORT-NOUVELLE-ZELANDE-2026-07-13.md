# Rapport — Multi-pays & carte de la Nouvelle-Zélande

Date : 2026-07-13 · Session principale. Étape 4 de la feuille de route :
**page de garde avec choix du pays** (France / Nouvelle-Zélande, extensible) et
**première carte étrangère : la Nouvelle-Zélande** — livrée en deux vagues le
même jour : socle (3 753 points + 11 Great Walks) puis **+177 points sur 5
nouvelles catégories** (grottes, cathédrales, châteaux/forts, villages, via
ferrata) → **3 930 points** au total (v61).

## Architecture multi-pays

- **`js/config/pays.js`** (nouveau, SHELL) — registre des pays : fichier de
  points, surcouche de grands itinéraires (fichier/libellé/compte/sous-titre de
  fiche), catégories disponibles (`categories`, `categoriesExclues`), couches
  lourdes oui/non, vue de départ, langue Wikipédia. Pays mémorisé dans
  `carte-outdoor:pays` (lecture synchrone au boot).
- **Page de garde** `#pays-overlay` (index.html + styles) : au premier
  lancement, le choix du pays précède tout ; ensuite « 🌍 Changer de pays »
  dans ⚙️ Réglages (changement → rechargement complet propre).
- **Par pays** : fichier de points (`data/points.geojson` FR /
  `data/nz/points.geojson` NZ, non pré-caché), catégories de la sidebar
  filtrées (les catégories perso et celles avec des points utilisateur restent
  toujours visibles), **vue mémorisée par pays** (`vue_fr`/`vue_nz` — sinon on
  rouvrirait sur le mauvais hémisphère), surcouche GR ↔ Great Walks, FAB 🚻 et
  couches lourdes (toilettes/eau/grottes) France seulement, Wikipédia de
  l'Oracle en anglais en NZ (CSP : `en.wikipedia.org` ajouté à connect-src).
- **Catégories actives inconnues du pays → décochées au boot** (leurs filtres
  polluaient le panneau) ; si plus rien n'est coché, la 1re catégorie du pays
  est activée (pas de carte vide au premier passage).

## Le carnet (et les statuts) sont COMMUNS — réponse à la question

Carnet, statuts (À faire/Fait/Favoris) et sync sont indexés par **id de point**,
et les ids NZ sont préfixés (`nz-hut-0001`…) : aucune collision. À l'ouverture
du carnet, les points des **autres pays** sont chargés (une fois par session,
hook `avantOuverture` de carnet.js) pour résoudre les noms de tous les
souvenirs. **Vérifié** : une sortie sur une hutte NZ apparaît dans le grimoire
en mode France. Limite : les souvenirs sur des points de couches lourdes d'un
autre pays (toilettes/eau/grottes FR vues depuis la NZ) ne sont pas résolus
(fichiers trop lourds pour un chargement croisé).

## Sources NZ (workflow multi-agents, licences d'abord)

| Source | Licence | Apport |
|---|---|---|
| **DOC** (Department of Conservation, ArcGIS `*_DTO`) | **CC-BY 4.0** « DOC, © Crown » | 958 huttes (couchettes/catégorie/statut), 326 campings (type/emplacements/accès/chiens), segments Great Walks ; liens pages officielles via les anciens datasets |
| **NZ Gazetteer / LINZ** (gaz.csv, sans clé) | **CC-BY 4.0** | 1 190 lacs + 301 cascades aux noms OFFICIELS |
| **OSM** (Overpass, area NZ) | ODbL | +120 cascades nommées, +858 campings (dédoublonnés ≤ 500 m) |
| Escalade | — | **ABANDONNÉE** : 106 objets OSM, topos ClimbNZ non libres — dit honnêtement |

## Résultat — data/nz/ (1,75 Mo, non pré-caché)

**3 930 points** : 958 refuges (huttes) · 1 184 campings (326 DOC + 858 OSM) ·
1 190 lacs · 421 cascades · **127 grottes · 22 villages · 18 cathédrales ·
7 châteaux/forts · 3 via ferrata**. **Nouvelle catégorie `camping`** (⛺,
filtres Type/Emplacements) — France : masquée en attendant ses données.

## Deuxième vague — via ferrata, grottes, châteaux, cathédrales, villages

- **Grottes (127)** — Gazetteer (53 noms officiels) + OSM `cave_entrance`
  nommées (dédoublonnées ≤ 300 m), **type spéléo déduit du nom anglais**
  (tomo/shaft/hole → Gouffre/aven, spring → Source/résurgence) alimentant le
  filtre existant ; 13 enrichies Wikipédia EN (lien + **photo Commons** —
  Waitomo, Cathedral Caves…). Les 118 entrées OSM anonymes sont écartées
  (qualité). **Débranchement critique** : en France `grotte` est une couche
  lourde (dialogue + fichier séparé) — le mécanisme est maintenant conditionné
  au pays (`coucheLourde(id)`) : en NZ, catégorie normale, compteur réel,
  aucun dialogue. Vérifié dans les deux sens.
- **Cathédrales (18)** — arbre Wikipédia EN « Cathedrals in New Zealand »,
  coordonnées + photos Commons (Cardboard Cathedral incluse).
- **Châteaux et forts (7)** — liste éditoriale COMPLÈTE (la NZ n'a qu'une
  poignée de châteaux) : Larnach Castle (« le seul château de NZ », 1871),
  Cargill's Castle (ruine 1877), Riverstone Castle (2017) + 4 forts côtiers
  historiques (Ripapa Island/Fort Jervois 1886, Fort Ballance, Fort Dorset,
  Wright's Hill 1942). Les **75 « homesteads » OSM écartés** (fermes
  historiques, pas des châteaux) ; 4/7 vérifiés Wikipédia avec photos.
- **Villages de caractère (22)** — pas de label officiel en NZ (l'équivalent
  des « Plus beaux villages » n'existe pas ; les Beautiful Awards KNZB
  récompensent la propreté, pas le patrimoine) → **sélection éditoriale
  vérifiée** article par article via l'API Wikipédia : Arrowtown, Akaroa
  (colonie française 1840), Russell, Oamaru (précinct victorien), Napier
  (Art déco), St Bathans, Whangamōmona (la « République »)… chacun avec un
  fait marquant en description et le lien Wikipédia.
- **Via ferrata (3)** — l'exhaustif honnête du pays : Wildwire Wanaka (« la
  via ferrata de cascade la plus haute du monde », position Twin Falls via le
  Gazetteer), Via Ferrata Queenstown, Via Ferrata Aotearoa (Golden Bay).
  Écarté : la « High Canopy » du zoo d'Auckland (habitat d'ANIMAUX tagué
  via_ferrata dans OSM !).
- Recherche éditoriale : workflow multi-agents — l'agent villages a livré une
  liste sourcée ; les agents châteaux/via-ferrata sont morts sur le plafond de
  dépense mensuel → **listes reprises en direct par la session principale**
  (sondes API Wikipédia + OSM), méthode habituelle.

**11 grands itinéraires** (`data/nz/great-walks.geojson`, MultiLineString,
cliquables comme les GR, fiche « Great Walk » + distance mesurée + Wikipédia +
DOC + 📥 GPX) : les 9 Great Walks terrestres (Milford 54,6 km, Kepler 62,1,
Routeburn 32,7, Abel Tasman 69,1, Heaphy 73,7, Waikaremoana 48, Tongariro
Northern Circuit 34,4, Rakiura 29,2, Paparoa 61,2) + Hump Ridge 45,9 +
**Tongariro Alpine Crossing 19,7** (classé « Great Walk » par le DOC). Écartés
(conservateur) : Whanganui Journey (descente de RIVIÈRE en canoë — un tracé
terrestre serait trompeur) et 2 embranchements ambigus.

## Pièges payés (à retenir)

- ArcGIS : pagination `resultOffset` **sans `orderByFields` = instable**
  (500 doublons) ; `outSR=4326` obligatoire (natif NZTM) ; datasets
  « Deprecated » répondent encore → utiliser `*_DTO` ; champs métier en paires
  pivot `CharName#/CharValue#` dont le mapping **varie par entité**.
- Great Walks : filtrer `SubObjectType='Great Walk'` troue les tracés (les
  sections d'accès sont « Walking Track ») → prendre tout le **préfixe FlocID**
  de l'itinéraire, sauf Short Walks ; exception LHAUROBC (type Great Walk seul,
  sinon Hump Ridge embarque tout le South Coast Track : 128 km au lieu de 61).
- Gazetteer : BOM UTF-8 ; filtrer lat -34/-48,5 (Antarctique + reliefs
  sous-marins sinon).
- Overpass NZ : `area ISO3166-1=NZ`, jamais de bbox (îles Chatham sur
  l'antiméridien).

## Limites honnêtes

- Interface en français (données NZ en anglais) — i18n non faite, à décider.
- Pas d'escalade NZ (pas de source libre), pas de toilettes/eau/grottes NZ
  (modèle couches lourdes non multi-pays pour l'instant ; OSM NZ a ~4 500
  toilettes → enrichissement futur possible).
- Grandes distances mesurées sur le réseau dessiné (tronçons + accès) —
  cohérentes avec l'officiel (vérifiées une à une), pas de D+ (pas
  d'altimétrie NZ branchée).
- Great Walks du DOC = tracés officiels, mais le Tongariro Northern Circuit
  partage des tronçons avec l'Alpine Crossing (comptés dans ce dernier).

## Vérification (navigateur, SW/caches/localStorage purgés)

0 erreur console · tests purs **24/24** · page de garde au premier boot ·
choix NZ → carte centrée NZ, catégories Cascade 421/Lac 1190/Refuge 958/
Camping 1184, « Great Walks 11 », FAB 🚻 masqué · fiche Luxmore Hut (54
couchettes, Great Walk, Fiordland, lien DOC officiel) · clic Milford Track →
fiche + GPX · retour France intact (18 lignes, GR 190, vue France) · carnet
commun vérifié (sortie NZ visible en mode France) · premier passage NZ →
Refuge auto-coché, panneau de filtres propre. `sw.js` v60 (pays.js au SHELL,
données NZ hors SHELL).
