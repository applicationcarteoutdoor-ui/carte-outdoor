# Feuille de route — Carte Outdoor

Tenue par l'agent **chef-de-projet** (`.claude/agents/chef-de-projet.md`). Dernière mise à jour : 2026-07-13 (v61 : **multi-pays + Nouvelle-Zélande complète**, 3 930 points sur 9 catégories ; v59 : canyon ; v58 : cascade + château + lac + grotte/spéléo).

## État des lieux

- **En ligne (v52)** : ~9 800 points (135 randonnées/28 massifs avec tracés + GPX, cascades, lacs, villages…), 190 GR cliquables, 66 500 toilettes + 49 500 points d'eau à la demande, Oracle (gratuit + IA), sync Supabase, partage QR, carnet.
- **v53 en préparation** : revue de code complète (3 bugs corrigés : confirm() natif des traces, boule Oracle bloquée sans clé, révocation d'URL d'export) — test de bout en bout en cours.

## Étape 1 — 🔄 Vérifier et enrichir toutes les données (EN COURS)

- [x] **Audit de complétude** (2026-07-11) — taux de remplissage par catégorie :

  | Catégorie | Points | Photos | Liens | « À vérifier » |
  |---|--:|--:|--:|--:|
  | cascade | 1 133 | 8 % | 9 % | **91 %** 🔴 |
  | chateau | 810 | 64 % | 67 % | 35 % 🟠 |
  | lac | 965 | 79 % | 100 % | 20 % 🟡 |
  | via-ferrata | 126 | 0 % | 100 % | 0 % |
  | escalade | 2 033 | 0 % | 100 % | 0 % (24 sites DOM confirmés valides) |
  | refuge | 3 524 | 0 % | 100 % | 0 % (refuges.info) |
  | grotte / cathédrale / village / rando | — | 92-99 % | 100 % | 0 % 🟢 |

  Constat : gros du travail sur **cascade** et **chateau**. Les 0 % photos (via-ferrata/escalade/refuge) = limite honnête (photos libres rares). Les 24 « coord hors bornes » escalade = DOM valides, PAS des erreurs → le contrôle de bornes doit inclure les DOM.
- **Ordre de revue** : via-ferrata (pilote) → escalade → cascade → chateau → lac → reste. Une catégorie = un run reprenable (enrichisseur, avec sa mémoire).
- [x] ✅ **via-ferrata** (2026-07-11) — pilote. **44 GPS recalés** (centroïde de commune → site OSM réel, règle conservatrice), **+7 VF manquantes** ajoutées (126 → 133, double accord OSM + viaferrata-fr.net). 47 points laissés « à vérifier manuellement » (OSM absent ou massif dense), photos toujours 0 (limite honnête). Rapport : dev/RAPPORT-REVUE-via-ferrata-2026-07-11.md. Méthode validée & réutilisable (diagnostic → recalage sûr → ajout double-accord). Scripts gabarits dans tools/.
- [x] ✅ **escalade** (2 033 → **3 351**) (2026-07-12) — revue approfondie **Camp to Camp + RES (Licence Ouverte Etalab)** après retour utilisateur (fiches vides). Workflow licences/sources d'abord. **1 790 GPS recalés** (1 519 C2C + 271 RES officiels) + **enrichis** (cotation/voies/roche/hauteur/orientation, ex. Saint-Simon 0→17 voies 4c-8a calcaire), **corde estimée** depuis la hauteur (749), **+1 318 sites manquants** ajoutés (275 C2C + 1 043 RES nationaux). **Attribution** ajoutée (Réglages). Couverture 3 351 : cotation 65 %/roche 51 %/hauteur 64 %/corde 61 % (baisse = +1 043 blocs/petits sites sans cotation, plafond honnête des sources libres). ~243 restent au centroïde. Rapport : dev/RAPPORT-REVUE-escalade-2026-07-11.md.
- [x] ✅ **cascade** (1 133 → **1 174**) (2026-07-12) — GPS OSM **déjà précis** (contrôle Gavarnie/Sillans/Sautadet/Ars OK) → **aucun recalage**. Enrichissement Wikipédia (garde anti-homonyme < 2 km) : **20 fiches** complétées (plafond honnête — seuls 97 noms ont un article frwiki, 79 déjà liés). Vraie valeur : **+41 cascades notables** via l'arbre catégorie « Chute d'eau en France » — surtout **l'outre-mer** (Réunion : Trou de Fer, Grand Galet ; Guadeloupe : Chutes du Carbet ; Guyane : Chutes Voltaire…), absent car la récolte OSM était bornée à la métropole. Couverture photo/lien/référencée 8-9 % → 13-14 %. Rapport : dev/RAPPORT-REVUE-cascade-2026-07-12.md.
- [x] ✅ **chateau** (810) (2026-07-12) — **TOUS au centroïde de commune** au départ. Recalage en 2 phases : **Phase 1** (`recaler_chateaux.py`) depuis les articles Wikipédia liés (coordonnée réelle jamais récupérée jusqu'ici) → **505 recalés**, avec validation par **département** (géocodage inverse) pour les cas > 20 km : **44 centroïdes faux corrigés** (géocodés sur mauvaise commune homonyme, ex. Brissac Hérault→Maine-et-Loire) et **32 liens Wikipédia erronés déliés** (homonymes, ex. « Château de Belfort » en Suisse). **Phase 2** (`recaler_chateaux_osm.py`) via OSM `historic=castle` (15 360 objets) pour les sans-article : **161 recalés** (correspondance de nom unique < 12 km, partiels durcis) + **94 re-liés**. Total **666/810 recalés (82 %)**, 144 restent au centroïde (correspondance non certaine → laissés). Liens 67→74 %, fiche Référencé 64→72 %. Rapport : dev/RAPPORT-REVUE-chateau-2026-07-12.md.
- [x] ✅ **lac** (965) (2026-07-12) — la mieux lotie : **100 % liens/altitude/description**, GPS déjà recentré dans l'eau (vérifié : Annecy, Léman, Serre-Ponçon, Pavin… tous OK) → **aucun recalage**. Les 196 « À vérifier » = exactement les 196 sans photo. Enrichissement Wikidata (`enrichir_lacs.py`, P18/P2046/P4511 + Commons) : **+12 photos, +7 superficies** (photo/Référencé 79→80 %). Plafond honnête : sur 196 sans photo seuls 12 ont une image Wikidata ; superficie/profondeur des manquants quasi absentes de Wikidata. Rapport : dev/RAPPORT-REVUE-lac-2026-07-12.md.
- [x] ✅ **canyon / canyonisme** (0 → **1 274**) (2026-07-13) — **nouvelle catégorie** sur demande. Pas d'équivalent C2C (C2C n'a pas le canyoning) ; descente-canyon.com (la base riche) **écartée** (CC BY-NC-SA + droit producteur, clause non-commercial incompatible store). Socle **RES / Data ES** (type « Canyon », **Licence Ouverte Etalab 2.0**, 1 274 sites : position + longueur + dénivelé, DOM inclus) + faits **OpenStreetMap** (ODbL) sur ~27 canyons : cotation FFME, plus grand rappel (→ corde estimée), site web, **tracé** (reconstruit du cours d'eau, épinglé + GPX, mécanisme rando généralisé). Filtres Longueur/Dénivelé/Accès. **Limite dure honnête : temps d'approche/retour IMPOSSIBLES en open data** (topos protégés, comme le nb de cordes en spéléo). Scripts `recolter_canyon_res.py` + `recolter_canyon_osm.py` + `fusion_canyon.py`. Rapport : dev/RAPPORT-REVUE-canyon-2026-07-13.md.
- [x] ✅ **grotte / spéléo** (484 → **49 717**) (2026-07-12) — chantier majeur. Recherche multi-sources (workflow, licences d'abord) → socle **Grottocenter** (API publique, faits ODbL). Nouvelle **couche lourde** `data/grottes.geojson` (24,7 Mo, à la demande, COUCHES_LOURDES + dialogue #grottes-dialog). ~50 000 cavités FR (filtre France par région + géocodage inverse), type/progression/eau déduits du nom, **profondeur/développement Grottocenter**. **6 filtres** spéléo alimentés (type, progression, profondeur, développement, eau, fiche). Les 484 Wikipédia fusionnées (ids stables, enrichies). Limites honnêtes : nombre de cordes / hauteur de puits impossibles (topos protégés). Attribution ODbL + garde-fous éthiques. Rapport : dev/RAPPORT-REVUE-grotte-2026-07-12.md.
- **Étape 1 : reste à revoir** — les catégories déjà à 92-99 % (cathédrale, village, refuge, rando) : vérification légère, faible gain attendu. Le gros de l'étape 1 est fait (via-ferrata, escalade, cascade, château, lac, grotte).
- **Reste sur via-ferrata** : recaler à la main les 47 points ambigus (reverse-geocode + choix humain) ; ajouter Le Regardoir/Vouglans et Roc del Gorb (rapprochement de nom incertain).
- ⚠️ Plafond de dépense mensuel — découper, intégrer au fil de l'eau.

## v62 (2026-07-14) — SpotMap + page de garde carte du monde

- [x] **Renommage : Carte Outdoor → SpotMap** (choix utilisateur, informé de la collision avec l'appli « Spotmap » existante du Play Store — suggestion : fiche store « SpotMap : spots outdoor & rando » pour se différencier). Dépôt/URL/localStorage inchangés.
- [x] **Page de garde refaite : carte du monde cliquable** (data/monde.geojson, Natural Earth domaine public, Leaflet sans tuiles = hors-ligne ; pays disponibles en teal + épingles drapeaux pulsantes, boutons en doublon pour l'accessibilité). Sélection → centrage auto sur le pays + catégories du pays.
- [x] **Partage de catégories communautaires — LIVRÉ côté app (v63)** : `js/communaute.js` (dialogue Importer/Partager, page de garde + Réglages), colis ≤ 500 pts/1 Mo SANS photos, import re-identifié `comm-…` (réimport idempotent), publication après **validation manuelle**. Serveur : `supabase/communaute-schema.sql` (table + RLS + modérateurs + compteur) — **action utilisateur : exécuter le SQL + s'ajouter dans `moderateurs`** (guide docs/COMMUNAUTE.md). Tant que le SQL n'est pas passé, l'app affiche « bientôt » proprement.
- [x] **Page de garde v3 (v63)** : monde EN COULEURS (teinte stable par pays), nom au survol (Intl.DisplayNames fr), pays disponibles = points verts pulsants, **16 pays « bientôt »** en points ambrés (Pérou, Pays-Bas, Népal, Singapour, Laos, Suisse, Japon…), Antarctique retiré. **Nouveau logo** : spot + « ? » (icon.svg + PNG via tools/generer_icones.py).

## v64 (2026-07-14) — vraie carte d'accueil, filtres vierges, randos NZ, catégorie Culture

- [x] **Page de garde = vraie carte** (tuiles OSM, zoom/déplacement libres, océan clair) — pays dispo surlignés + points verts, « bientôt » ambrés, nom au survol conservés.
- [x] **Filtres VIERGES à chaque activation de catégorie** (aucune sélection d'une session passée ne reste).
- [x] **Randonnées NZ : 26 itinéraires emblématiques** (Roys Peak, Mueller Hut, Rob Roy, Avalanche Peak, Hollyford…) — liste éditoriale, FlocID DOC exacts, tracés réels (`data/nz/randos.geojson`), distance mesurée + durée estimée, GPX/épinglage comme la France (`pays.fichierRandos`).
- [x] **Catégorie Culture 🏛️** (musées, galeries, sites archéo, monuments — OSM ODbL : nom, GPS, site web, horaires, description, photos wikimedia rares) : **France 14 919 = couche lourde** `data/culture.geojson` (dialogue + « à moins de 1 km », hors pré-cache) ; **NZ 1 331 = catégorie normale** (dont 704 pā/sites archéo). Filtres Type + Fiche. Les châteaux restent leur propre catégorie.

## v66 (2026-07-16) — Musées, catégories exclusives, SUISSE + ITALIE + ESPAGNE

- [x] **Culture → Musée** (15 000 → 5 053 FR, 66 % avec site web ; archéo/monuments/galeries écartés — si patrimoine bâti un jour : base Mérimée officielle, pas OSM). Id `culture` stable, label « Musée ».
- [x] **Grosses catégories exclusives** : une couche lourde s'affiche seule ; les petites se combinent ; cocher une petite chasse la grosse.
- [x] **3 nouveaux pays (pipeline générique `recolter_pays_osm.py` + `construire_pays.py`)** : **Suisse 5 080** · **Italie 29 316** · **Espagne 21 949** points (9 catégories : refuges, campings, lacs, cascades, grottes, via ferrata cotées K, châteaux/forts, musées) + **villages labellisés officiels** (389 Borghi più belli d'Italia via Wikidata, 101 Pueblos Más Bonitos, 36 Plus beaux villages de Suisse — photos + descriptions). Page de garde : 5 pays cliquables. Pas encore de surcouche d'itinéraires ni de randos éditoriales pour ces 3 pays (gr: null — Via Alpina/GR espagnols à venir).

## v67 (2026-07-16) — Enrichissement CH/IT/ES + sanitaires PARTOUT (rapport : dev/RAPPORT-ENRICHISSEMENT-2026-07-16-v67.md)

- [x] **Wikipédia (CH/IT/ES)** : 5 259 points appariés (photos 960 px ~4 990, lien 🔗, description) — `enrichir_pays_wikipedia.py`, appliqué au build.
- [x] **Fiches via ferrata** : lien vers LA page de la VF sur le site du pays — IT ferrate365.it (187/284), ES deandar.com (85/143, +83 cotations K), CH myferrata.ch (26/89). rocjumper interdit aux agents IA (respecté). FR/NZ déjà couverts.
- [x] **Randonnées iconiques : 72 tracées** (CH 24, IT 23, ES 25) — listes éditoriales web vérifiées, routage OSM (modèle France), boucles par relation OSM, D+ open-meteo, GPX. Écartées honnêtes : lac de Braies, Gelmersee (boucles sans relation).
- [x] **Toilettes + fontaines pour TOUS les pays** : IT 10 211/79 138 · ES 7 404/60 144 · CH 6 588/18 023 · NZ 4 562/1 957 (`recolter_sanitaires_pays.py`) ; `pays.couchesLourdes` = table id→fichier, `chargerCouche()` générique, FAB 🚻 partout.
- [ ] Reste : catégorie `randonnee` sans photos pour CH/IT/ES (limite photos libres) ; toilettes FRANCE à re-récolter avec filtre d'aire (points allemands/suisses dans le fichier — tâche proposée).

## Étape 2 — 📋 Publier sur le Play Store

Guide existant : `docs/PLAYSTORE.md` (TWA/PWABuilder). Reste à faire :

- [ ] Testeur vert sur la version candidate + données auditées (étape 1 au moins amorcée).
- [ ] **Action utilisateur** : compte Play Console (25 $ une fois), récupérer l'empreinte SHA-256 → compléter `.well-known/assetlinks.json`.
- [ ] Page « politique de confidentialité » (obligatoire Play Store — l'app ne collecte rien côté serveur hors sync opt-in : à écrire et héberger sur le site).
- [ ] Formulaire « sécurité des données » Play Console, captures d'écran, fiche store (texte + visuels).
- [ ] Paquet TWA (PWABuilder), test interne, puis production.

## Étape 3 — 🔄 Modèle économique de l'Oracle (décidé)

**Décisions (2026-07-13)** : gratuit inchangé ; IA avec sa propre clé inchangée ; nouveau 3ᵉ mode **IA sans clé = pack de consultations** (achat unique décompté), payé via **Google Play Billing**. Détails et séquence : `docs/ORACLE-PAYANT.md`.

- ⛔ **Bloqué par l'étape 2** : Play Billing exige que l'app soit publiée sur le Play Store. L'Oracle payant s'active donc **avec** la publication.
- [x] **Fait maintenant** (indépendant du store) : relais serveur `supabase/functions/oracle-ia/index.ts` (Edge Function qui détient notre clé + décompte les crédits) + modèle de données `schema.sql` (table crédits/achats, RLS, RPC atomiques) + guide complet.
- [ ] **Après le Play Store** : fonction `grant` (vérification du `purchaseToken` via Google Play Developer API) + câblage client `js/oracle.js` (3ᵉ mode, solde, bouton d'achat Digital Goods API) — testable de bout en bout seulement une fois l'app sur le store.
- [ ] **Actions utilisateur** : compte Play Console + produits « pack », compte de service Google Play Developer API, déploiement des fonctions Supabase + secret `ANTHROPIC_API_KEY` (l'agent ne manipule ni comptes ni paiements ni clés).
- 💶 Économie : ~0,01-0,05 € d'API/consultation, Google prend 15-30 % → viser un pack 30 à 1,99 € (et/ou 10 à 0,99 €). Décompte seulement après appel réussi ; plafond/jour possible.

## Étape 4 — ✅ Multi-pays : Nouvelle-Zélande (LIVRÉE 2026-07-13, v61)

**Décision utilisateur : même app + page de garde de choix du pays** (France / Nouvelle-Zélande, extensible). Rapport : `dev/RAPPORT-NOUVELLE-ZELANDE-2026-07-13.md`.

- [x] Architecture multi-pays : `js/config/pays.js` (registre : fichier de points, surcouche GR/Great Walks, catégories dispo, vue, wikiLang), page de garde `#pays-overlay` + « 🌍 Changer de pays » (Réglages), vue mémorisée PAR pays, **carnet/statuts COMMUNS** (ids préfixés `nz-`, résolution croisée des noms à l'ouverture du carnet — vérifié).
- [x] **Carte NZ : 3 930 points** (958 huttes DOC avec couchettes/catégorie/lien officiel · 1 184 campings DOC+OSM · 1 190 lacs Gazetteer · 421 cascades · **127 grottes · 22 villages · 18 cathédrales · 7 châteaux/forts · 3 via ferrata** — 2e vague v61) + **11 grands itinéraires cliquables** (9 Great Walks + Hump Ridge + Tongariro Alpine Crossing, distance + GPX + Wikipédia). Sources : DOC CC-BY 4.0, NZ Gazetteer/LINZ CC-BY 4.0, OSM ODbL, Wikipédia EN (photos Commons) — attribution aux Réglages. Nouvelle catégorie **`camping`** ⛺ (masquée en France en attendant ses données). **Couches lourdes conditionnées au pays** (`coucheLourde(id)`) : `grotte` = dialogue+fichier séparé en France, catégorie normale en NZ.
- [x] Honnêteté : escalade NZ abandonnée (pas de source libre), Whanganui Journey écarté (rivière), pas de label officiel « joli village » en NZ (sélection éditoriale vérifiée Wikipédia), interface reste en français.
- [ ] Reste (plus tard) : couches lourdes par pays (toilettes NZ ~4 500 dans OSM), camping France, i18n EN si demandé.
- **Prochain pays — décision (2026-07-14, session autonome v65) : PAS de nouveau pays avant le Play Store.** Raisons : la qualité de l'existant prime avant la publication (étape 2), et un pays bien fait = une session dédiée. **Candidat n°1 retenu : la Suisse** — public francophone limitrophe, données exemplaires (OSM très riche, open data swisstopo, cabanes du CAS déjà en partie dans refuges.info, Via Alpina comme surcouche d'itinéraires). L'architecture multi-pays est prête : une entrée `PAYS` + `data/ch/`.

## Backlog (petites améliorations, à grouper dans une future vague)

- Carnet : retirer une sortie laisse la note et le statut « ✓ Fait » en place (deux corbeilles distinctes, compteur d'apparence incohérente — rapport de test 2026-07-11). Décider d'une sémantique claire avec l'utilisateur avant de toucher.
- Sidebar : compteur GR figé à 190 (constante commentée dans sidebar.js) — recalculer si data/gr.geojson évolue.

## Prochain coup recommandé

Finaliser la **v53** (rapport du testeur → correctifs éventuels → push), puis lancer l'**audit de données** (étape 1) — c'est le prérequis des étapes 2 et 4, et il est parallélisable avec la préparation Play Store côté utilisateur (compte + SHA-256).

## Décisions en attente de l'utilisateur

1. Oracle payant : option A (Supabase + Play Billing) ou B (Stripe hors store) ? Forfait ou paquet de consultations ?
2. NZ : app séparée ou sélecteur de pays ?
3. Play Console : créer le compte et récupérer l'empreinte SHA-256.
