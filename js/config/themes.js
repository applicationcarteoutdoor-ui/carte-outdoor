/**
 * Configuration des catégories de points d'intérêt.
 *
 * ★ C'est LE fichier à modifier pour ajouter une catégorie :
 *   - id        : identifiant STABLE et unique (kebab-case). Stocké dans les
 *                 données des points — il ne doit JAMAIS changer, même si le
 *                 nom affiché change.
 *   - label     : nom affiché (personnalisable dans l'application)
 *   - color     : couleur de fond (marqueur, pastille)
 *   - textColor : couleur du texte/icône sur ce fond
 *   - icon      : emoji du marqueur
 *   - fields    : champs affichés dans la fiche détaillée
 *   - filters   : filtres proposés quand la catégorie est cochée (voir ci-dessous)
 *
 * Schéma d'un filtre :
 *   { key, label, type, field, options: [{value, label?, icon?, min?, max?}] }
 *   - type "tokens" : le champ contient des cotations (F, PD, AD…) ; le point
 *                     passe si l'une des cotations sélectionnées y figure
 *   - type "prefix" : le champ commence par l'une des valeurs sélectionnées
 *   - type "value"  : le champ vaut exactement l'une des valeurs
 *   - type "bucket" : le champ (numérique, suffixe _n) tombe dans l'une des
 *                     tranches sélectionnées [min, max)
 *   Aucune sélection = « Tout » (pas de filtrage).
 */

export const THEMES = [
  {
    id: "via-ferrata",
    label: "Via ferrata",
    color: "#e63946",
    icon: "🧗",
    fields: [
      { key: "cotation", label: "Cotation" },
      { key: "parcours", label: "Nombre de parcours" },
      { key: "longueur", label: "Longueur" },
      { key: "denivele", label: "Dénivelé" },
      { key: "duree", label: "Durée" },
      { key: "materiel", label: "Matériel requis" },
      { key: "tyrolienne", label: "Tyrolienne" },
    ],
    filters: [
      {
        key: "cotation",
        label: "Cotation",
        type: "tokens",
        field: "cotation",
        options: [
          { value: "F" }, { value: "PD" }, { value: "AD" },
          { value: "D" }, { value: "TD" }, { value: "ED" },
        ],
      },
      {
        key: "tyrolienne",
        label: "Tyrolienne",
        type: "value",
        field: "tyrolienne_type",
        options: [
          { value: "oui", label: "Avec tyrolienne", icon: "🚡" },
          { value: "non", label: "Sans" },
        ],
      },
    ],
  },
  {
    id: "escalade",
    label: "Escalade",
    color: "#d62828",
    icon: "🪨",
    fields: [
      { key: "cotation", label: "Cotations" },
      { key: "type", label: "Type de site" },
      { key: "voies", label: "Nombre de voies" },
      { key: "roche", label: "Roche" },
      { key: "hauteur", label: "Hauteur" },
      { key: "corde", label: "Longueur de corde" },
      { key: "approche", label: "Marche d'approche" },
      { key: "orientation", label: "Orientation" },
    ],
    filters: [
      {
        key: "type",
        label: "Type de site",
        type: "prefix",
        field: "type",
        options: [
          { value: "Site sportif", icon: "🧗" },
          { value: "Terrain d'aventure", icon: "🏔️" },
          { value: "Site de bloc", icon: "🪨" },
        ],
      },
      {
        key: "voies",
        label: "Nombre de voies",
        type: "bucket",
        field: "voies_n",
        options: [
          { value: "v1", label: "< 20", max: 20 },
          { value: "v2", label: "20 à 50", min: 20, max: 50 },
          { value: "v3", label: "> 50", min: 50 },
        ],
      },
      {
        key: "corde",
        label: "Longueur de corde",
        type: "bucket",
        field: "corde_n",
        options: [
          { value: "c1", label: "≤ 50 m", icon: "🪢", max: 51 },
          { value: "c2", label: "51 à 70 m", min: 51, max: 71 },
          { value: "c3", label: "> 70 m", min: 71 },
        ],
      },
      {
        key: "approche",
        label: "Marche d'approche",
        type: "bucket",
        field: "approche_n",
        options: [
          { value: "a1", label: "≤ 10 min", icon: "🚶", max: 11 },
          { value: "a2", label: "11 à 30 min", min: 11, max: 31 },
          { value: "a3", label: "> 30 min", min: 31 },
        ],
      },
    ],
  },
  {
    // Canyonisme — descentes de canyon. Socle RES / Data ES (Licence Ouverte
    // Etalab 2.0 : position, longueur, dénivelé), enrichi par OpenStreetMap
    // (ODbL) là où il existe (~27 sites) : cotation FFME, plus grand rappel
    // (→ corde estimée), site web, tracé (data/canyons-traces.geojson).
    // Les temps d'approche/retour sont IMPOSSIBLES en données libres (ils
    // n'existent que dans les topos rédigés, protégés) : volontairement absents.
    // Construction : tools/recolter_canyon_res.py + recolter_canyon_osm.py +
    // fusion_canyon.py. Rapport : dev/RAPPORT-REVUE-canyon-*.md.
    id: "canyon",
    label: "Canyon",
    color: "#0a9396",
    icon: "🪢",
    fields: [
      { key: "commune", label: "Commune" },
      { key: "longueur", label: "Longueur de la descente" },
      { key: "denivele", label: "Dénivelé" },
      { key: "cotation", label: "Cotation (verticalité/aquatique/engagement)" },
      { key: "rappel", label: "Plus grand rappel" },
      { key: "corde", label: "Corde recommandée" },
      { key: "acces", label: "Accès" },
    ],
    filters: [
      {
        key: "longueur",
        label: "Longueur",
        type: "bucket",
        field: "longueur_n",
        options: [
          { value: "l1", label: "< 500 m", max: 500 },
          { value: "l2", label: "500 m à 1,5 km", min: 500, max: 1500 },
          { value: "l3", label: "> 1,5 km", min: 1500 },
        ],
      },
      {
        key: "denivele",
        label: "Dénivelé",
        type: "bucket",
        field: "denivele_n",
        options: [
          { value: "d1", label: "< 100 m", max: 100 },
          { value: "d2", label: "100 à 300 m", min: 100, max: 300 },
          { value: "d3", label: "> 300 m", min: 300 },
        ],
      },
      {
        key: "acces",
        label: "Accès",
        type: "value",
        field: "acces_type",
        options: [
          { value: "libre", label: "Accès libre", icon: "✅" },
          { value: "reglemente", label: "Réglementé", icon: "⚠️" },
        ],
      },
    ],
  },
  {
    // Randonnées remarquables — sélection éditoriale (sommets à voie normale
    // documentée, objectifs emblématiques), validée par Wikipédia et OSM.
    // PILOTE : massif de la Chartreuse uniquement (extension France à venir —
    // le filtre « Massif » est prévu pour accueillir les massifs suivants).
    // Convention : le point est placé au SOMMET/objectif de la randonnée,
    // jamais au parking ; details.depart donne le départ classique.
    id: "randonnee",
    label: "Randonnée",
    color: "#2d6a4f",
    icon: "🥾",
    fields: [
      { key: "altitude", label: "Altitude" },
      { key: "denivele", label: "Dénivelé (estimation)" },
      { key: "distance", label: "Distance" },
      { key: "duree", label: "Durée" },
      { key: "depart", label: "Départ classique" },
      { key: "acces", label: "Voie normale" },
      { key: "itineraire", label: "Itinéraire balisé (OSM)" },
      { key: "massif", label: "Massif" },
    ],
    // Filtres par effort : durée, dénivelé positif et distance, en tranches
    // (buckets lisant les champs numériques duree_n / denivele_n / distance_n
    // posés par tools/completer_stats_randos.py).
    filters: [
      {
        key: "duree",
        label: "Durée",
        type: "bucket",
        field: "duree_n",
        options: [
          { value: "d1", label: "< 2 h", icon: "⏱️", max: 2 },
          { value: "d2", label: "2 à 4 h", min: 2, max: 4 },
          { value: "d3", label: "4 à 6 h", min: 4, max: 6 },
          { value: "d4", label: "> 6 h", min: 6 },
        ],
      },
      {
        key: "denivele",
        label: "Dénivelé (D+)",
        type: "bucket",
        field: "denivele_n",
        options: [
          { value: "e1", label: "< 500 m", icon: "📈", max: 500 },
          { value: "e2", label: "500 à 1000 m", min: 500, max: 1000 },
          { value: "e3", label: "> 1000 m", min: 1000 },
        ],
      },
      {
        key: "distance",
        label: "Distance",
        type: "bucket",
        field: "distance_n",
        options: [
          { value: "s1", label: "< 5 km", icon: "📏", max: 5 },
          { value: "s2", label: "5 à 10 km", min: 5, max: 10 },
          { value: "s3", label: "> 10 km", min: 10 },
        ],
      },
    ],
  },
  {
    // Couche lourde (data/grottes.geojson, ~50 000 cavités Grottocenter +
    // grottes Wikipédia) chargée à la demande — voir COUCHES_LOURDES (app.js).
    // Données spéléo = FAITS ODbL (Grottocenter) : profondeur, développement,
    // type/eau déduits du nom. Pas de nombre de cordes / hauteur de puits
    // (topos protégés). Voir dev/RAPPORT-REVUE-grotte.
    id: "grotte",
    label: "Grotte",
    color: "#7f5539",
    icon: "🕳️",
    fields: [
      { key: "type", label: "Type" },
      { key: "profondeur", label: "Profondeur" },
      { key: "developpement", label: "Développement" },
      { key: "progression", label: "Progression" },
      { key: "eau", label: "Présence d'eau" },
      { key: "commune", label: "Commune" },
      { key: "duree", label: "Durée de visite" },
      { key: "equipement", label: "Équipement" },
      { key: "horaires", label: "Horaires" },
      { key: "tarif", label: "Tarif" },
    ],
    filters: [
      {
        key: "type",
        label: "Type",
        type: "value",
        field: "type",
        options: [
          { value: "Grotte", icon: "🕳️" },
          { value: "Gouffre / aven", icon: "🕳️" },
          { value: "Source / résurgence", icon: "💧" },
          { value: "Cavité", icon: "⛰️" },
        ],
      },
      {
        key: "progression",
        label: "Progression",
        type: "value",
        field: "progression",
        options: [
          { value: "Horizontale", icon: "🚶" },
          { value: "Verticale (à cordes)", icon: "🧗" },
          { value: "Non précisé", icon: "❔" },
        ],
      },
      {
        key: "profondeur",
        label: "Profondeur",
        type: "bucket",
        field: "profondeur_n",
        options: [
          { value: "prof1", label: "< 30 m", max: 30 },
          { value: "prof2", label: "30 à 100 m", min: 30, max: 100 },
          { value: "prof3", label: "100 à 300 m", min: 100, max: 300 },
          { value: "prof4", label: "> 300 m", icon: "⬇️", min: 300 },
        ],
      },
      {
        key: "developpement",
        label: "Développement",
        type: "bucket",
        field: "developpement_n",
        options: [
          { value: "dev1", label: "< 500 m", max: 500 },
          { value: "dev2", label: "0,5 à 2 km", min: 500, max: 2000 },
          { value: "dev3", label: "2 à 10 km", min: 2000, max: 10000 },
          { value: "dev4", label: "> 10 km", icon: "🕸️", min: 10000 },
        ],
      },
      {
        key: "eau",
        label: "Présence d'eau",
        type: "value",
        field: "eau",
        options: [
          { value: "Actif (eau)", icon: "💧" },
          { value: "Non renseigné", icon: "❔" },
        ],
      },
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    id: "cascade",
    label: "Cascade",
    color: "#0096c7",
    icon: "💦",
    fields: [
      { key: "hauteur", label: "Hauteur de chute" },
      { key: "altitude", label: "Altitude" },
    ],
    // « Fiche » : Référencée (photo + informations) / À vérifier (incomplète).
    // Le champ details.fiche est posé par le pipeline de données.
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencée", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    // Sélection qualitative : uniquement les lacs ayant un article Wikipédia
    // (lacs de montagne, grands lacs, étangs célèbres) — pas les plans d'eau
    // anonymes. Données : Wikipédia + Wikidata, altitudes complétées par OSM.
    id: "lac",
    label: "Lac",
    color: "#1a659e",
    icon: "🏞️",
    fields: [
      { key: "altitude", label: "Altitude" },
      { key: "superficie", label: "Superficie" },
      { key: "profondeur", label: "Profondeur max" },
    ],
    // « Fiche » : Référencé (photo + informations) / À vérifier (incomplète).
    // Le champ details.fiche est posé par le pipeline de données.
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "alt1", label: "Plaine (< 600 m)", max: 600 },
          { value: "alt2", label: "600 à 1 500 m", min: 600, max: 1500 },
          { value: "alt3", label: "Montagne (> 1 500 m)", icon: "🏔️", min: 1500 },
        ],
      },
    ],
  },
  {
    // Une seule catégorie Château (l'ancienne « chateau-a-verifier » a été
    // fusionnée ici en v45 : c'est le filtre « Fiche » qui distingue les
    // châteaux documentés de ceux restant à confirmer).
    id: "chateau",
    label: "Château",
    color: "#9d4edd",
    icon: "🏰",
    fields: [
      { key: "type", label: "Type" }, // Château / Fort (NZ notamment)
      { key: "periode", label: "Période" },
      { key: "horaires", label: "Horaires" },
      { key: "tarif", label: "Tarif" },
      { key: "accessibilite", label: "Accessibilité" },
    ],
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    id: "cathedrale",
    label: "Cathédrale",
    color: "#3d5a80",
    icon: "⛪",
    fields: [
      { key: "style", label: "Style" },
      { key: "periode", label: "Période" },
    ],
    filters: [],
  },
  {
    // Culture = les MUSÉES (décision v66 : les sites archéo/monuments/galeries
    // OSM noyaient la catégorie — 15 000 points de qualité inégale → ~5 000
    // musées propres). Source OSM (ODbL : nom, GPS, site web, horaires) +
    // enrichissement Wikipédia (photos/descriptions). L'id `culture` est
    // STABLE (ne jamais renommer) — seul le label a changé.
    id: "culture",
    label: "Musée",
    color: "#780000",
    icon: "🏛️",
    fields: [
      { key: "horaires", label: "Horaires" },
      { key: "commune", label: "Commune" },
    ],
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", label: "Site web connu", icon: "✅" },
          { value: "À vérifier", label: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    // Une seule catégorie « Village » : les Cités de caractère du fichier
    // source (211) ET les Plus Beaux Villages de France (récolte enrichisseur)
    // y cohabitent, distingués par le filtre « Label » (details.label, type
    // contains : un village peut cumuler les deux labels).
    id: "cite-caractere", // id historique STABLE — ne jamais renommer
    label: "Village",
    color: "#f77f00",
    icon: "🏘️",
    fields: [
      { key: "label", label: "Label" },
      { key: "region", label: "Région" },
    ],
    filters: [
      {
        key: "label",
        label: "Label",
        type: "contains",
        field: "label",
        options: [
          { value: "Plus Beaux Villages", label: "Plus beau village de France", icon: "⭐" },
          { value: "Cité de caractère", label: "Cité de caractère", icon: "🏘️" },
        ],
      },
    ],
  },
  {
    id: "refuge",
    label: "Refuge",
    color: "#996633",
    icon: "🛖",
    fields: [
      { key: "capacite", label: "Capacité" },
      { key: "altitude", label: "Altitude" },
      { key: "chauffage", label: "Chauffage" },
      { key: "eau", label: "Eau à moins de 100 m" },
      { key: "latrines", label: "Latrines" },
      { key: "couvertures", label: "Couvertures" },
      { key: "etat", label: "État" },
      { key: "contact", label: "Contact" },
      // Champs des huttes néo-zélandaises (DOC) — absents des refuges français
      { key: "categorie", label: "Catégorie" },
      { key: "equipements", label: "Équipements" },
      { key: "lieu", label: "Parc / réserve" },
      { key: "region", label: "Région" },
    ],
    filters: [
      {
        key: "chauffage",
        label: "Chauffage",
        type: "contains",
        field: "chauffage_type",
        options: [
          { value: "poele", label: "Poêle à bois", icon: "🔥" },
          { value: "cheminee", label: "Cheminée", icon: "🪵" },
          { value: "aucun", label: "Aucun", icon: "❄️" },
        ],
      },
      {
        key: "places",
        label: "Nombre de places",
        type: "bucket",
        field: "places_n",
        options: [
          { value: "p1", label: "1 à 4", icon: "🛏️", max: 5 },
          { value: "p2", label: "5 à 9", icon: "🛏️", min: 5, max: 10 },
          { value: "p3", label: "10 et +", icon: "🛏️", min: 10 },
        ],
      },
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "a1", label: "< 1000 m", max: 1000 },
          { value: "a2", label: "1000 à 1500 m", min: 1000, max: 1500 },
          { value: "a3", label: "1500 à 2000 m", min: 1500, max: 2000 },
          { value: "a4", label: "> 2000 m", min: 2000 },
        ],
      },
      {
        key: "etat",
        label: "État",
        type: "value",
        field: "etat",
        options: [
          { value: "", label: "Ouverte", icon: "🔓" },
          { value: "Clé à récupérer avant", label: "Clé à récupérer", icon: "🔑" },
          { value: "Fermée", label: "Fermée", icon: "🚫" },
        ],
      },
    ],
  },
  {
    // Campings — d'abord peuplée par la Nouvelle-Zélande (campsites du DOC,
    // CC-BY 4.0) ; la France pourra suivre. Les libellés du filtre « Type »
    // doivent correspondre EXACTEMENT aux details.type posés par le pipeline
    // (tools/construire_nz.py) : catégories DOC traduites.
    id: "camping",
    label: "Camping",
    color: "#606c38",
    icon: "⛺",
    fields: [
      { key: "type", label: "Type" },
      { key: "places", label: "Emplacements" },
      { key: "acces", label: "Accès" },
      { key: "chiens", label: "Chiens" },
      { key: "paysage", label: "Paysage" },
      { key: "tarif", label: "Tarif" },
      { key: "etat", label: "État" },
      { key: "lieu", label: "Parc / réserve" },
      { key: "region", label: "Région" },
    ],
    filters: [
      {
        key: "type",
        label: "Type",
        type: "value",
        field: "type",
        options: [
          { value: "Aménagé", label: "Aménagé", icon: "🚿" },
          { value: "Standard", label: "Standard", icon: "⛺" },
          { value: "Basique", label: "Basique", icon: "🌿" },
          { value: "Arrière-pays", label: "Arrière-pays", icon: "🏔️" },
          { value: "Great Walk", label: "Great Walk", icon: "🥾" },
        ],
      },
      {
        key: "places",
        label: "Emplacements",
        type: "bucket",
        field: "places_n",
        options: [
          { value: "p1", label: "< 10", max: 10 },
          { value: "p2", label: "10 à 30", min: 10, max: 30 },
          { value: "p3", label: "30 et +", min: 30 },
        ],
      },
    ],
  },
  {
    id: "toilettes",
    label: "Toilettes",
    color: "#8d99ae",
    icon: "🚻",
    fields: [
      { key: "tarif", label: "Tarif" },
      { key: "accessibilite", label: "Accès PMR" },
      { key: "acces", label: "Accès" },
      { key: "equipement", label: "Équipement" },
      { key: "horaires", label: "Horaires" },
    ],
    filters: [
      {
        key: "tarif",
        label: "Tarif",
        type: "value",
        field: "tarif",
        options: [
          { value: "Gratuit", icon: "🆓" },
          { value: "Payant", icon: "💰" },
        ],
      },
      {
        key: "pmr",
        label: "Accès PMR",
        type: "value",
        field: "pmr_type",
        options: [
          { value: "oui", label: "PMR", icon: "♿" },
          { value: "non", label: "Non PMR" },
        ],
      },
    ],
  },
  {
    // Points d'eau (fontaines, robinets, sources) — couche utilitaire chargée
    // à la demande depuis data/eau.geojson (comme les toilettes, ~49 500 points).
    // La potabilité des SOURCES n'est jamais présumée : « non garantie ».
    id: "eau",
    label: "Fontaines & sources",
    color: "#1a9ec4",
    icon: "💧",
    fields: [
      { key: "type", label: "Type" },
      { key: "potabilite", label: "Potabilité" },
      { key: "fee", label: "Tarif" },
      { key: "charge", label: "Prix" },
      { key: "seasonal", label: "Disponibilité" },
      { key: "ele", label: "Altitude" },
      { key: "wheelchair", label: "Accès PMR" },
      { key: "operator", label: "Gestionnaire" },
      { key: "description", label: "Description" },
    ],
    filters: [
      {
        key: "potabilite",
        label: "Potabilité",
        type: "value",
        field: "potabilite",
        options: [
          { value: "Eau potable", icon: "💧" },
          { value: "Non potable", icon: "🚱" },
          { value: "Potabilité non garantie", icon: "⚠️" },
        ],
      },
      {
        key: "type",
        label: "Type",
        type: "value",
        field: "type",
        options: [
          { value: "Fontaine", icon: "⛲" },
          { value: "Source", icon: "🏔️" },
          { value: "Robinet", icon: "🚰" },
          { value: "Point d'eau", icon: "💧" },
        ],
      },
    ],
  },
  /* --- Nouvelles catégories v72 (packs Montagne / Nature / Culture) ------ */
  {
    id: "sommet-croix",
    label: "Sommet à croix",
    color: "#5c677d",
    icon: "✝️",
    fields: [{ key: "altitude", label: "Altitude" }],
    filters: [
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "alt1", label: "< 1 000 m", max: 1000 },
          { value: "alt2", label: "1 000 à 2 000 m", min: 1000, max: 2000 },
          { value: "alt3", label: "> 2 000 m", icon: "🏔️", min: 2000 },
        ],
      },
    ],
  },
  {
    id: "col-mythique",
    label: "Col mythique",
    color: "#8a5a44",
    icon: "🚵",
    fields: [{ key: "altitude", label: "Altitude" }],
    filters: [
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "alt1", label: "< 1 000 m", max: 1000 },
          { value: "alt2", label: "1 000 à 1 800 m", min: 1000, max: 1800 },
          { value: "alt3", label: "Géants (> 1 800 m)", icon: "🏔️", min: 1800 },
        ],
      },
    ],
  },
  {
    id: "village-abandonne",
    label: "Village abandonné",
    color: "#6d597a",
    icon: "🏚️",
    fields: [],
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    id: "ciel-etoile",
    label: "Ciel étoilé",
    color: "#1d3557",
    icon: "🌌",
    fields: [{ key: "label", label: "Certification" }],
    filters: [],
  },
  /* --- Catégories v74 (pack Paysages + plongée dans Eau) ----------------- */
  {
    id: "panorama",
    label: "Panorama",
    color: "#b76935",
    icon: "🌄",
    fields: [
      { key: "altitude", label: "Altitude" },
      { key: "equipement", label: "Équipement" },
    ],
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
      {
        key: "altitude",
        label: "Altitude",
        type: "bucket",
        field: "altitude_n",
        options: [
          { value: "alt1", label: "< 800 m", max: 800 },
          { value: "alt2", label: "800 à 1 800 m", min: 800, max: 1800 },
          { value: "alt3", label: "> 1 800 m", icon: "🏔️", min: 1800 },
        ],
      },
    ],
  },
  {
    id: "plongee",
    label: "Plongée & snorkeling",
    color: "#023e8a",
    icon: "🤿",
    fields: [],
    filters: [],
  },
  {
    id: "phare",
    label: "Phare",
    color: "#c1121f",
    icon: "🗼",
    fields: [{ key: "hauteur", label: "Hauteur" }],
    filters: [
      {
        key: "fiche",
        label: "Fiche",
        type: "value",
        field: "fiche",
        options: [
          { value: "Référencé", icon: "✅" },
          { value: "À vérifier", icon: "🔍" },
        ],
      },
    ],
  },
  {
    id: "arbre-remarquable",
    label: "Arbre remarquable",
    color: "#386641",
    icon: "🌳",
    fields: [
      { key: "espece", label: "Espèce" },
      { key: "circonference", label: "Circonférence" },
    ],
    filters: [],
  },
];

/** Catégorie de repli pour les points dont la catégorie est inconnue
 *  (ex. anciens imports référençant une catégorie supprimée). */
export const FALLBACK_THEME = {
  id: "autre",
  label: "Autre",
  color: "#6c757d",
  icon: "📍",
  fields: [],
  filters: [],
};

const TEXT_COLOR_DEFAUT = "#ffffff";

const parId = new Map(THEMES.map((t) => [t.id, t]));

/** Catégories créées par l'utilisateur (fonction « ajouter un point »).
 *  Persistées par storage.js et enregistrées ici au démarrage. */
let customThemes = [];

export function registerCustomThemes(liste) {
  customThemes = (liste || []).map((t) => ({ fields: [], filters: [], ...t }));
}

/** Toutes les catégories connues (par défaut + personnalisées). */
export function allThemes() {
  return [...THEMES, ...customThemes];
}

function baseDe(id) {
  return parId.get(id) || customThemes.find((t) => t.id === id) || FALLBACK_THEME;
}

/** Surcharges utilisateur : { themeId: {label?, color?, textColor?, icon?} } */
let overrides = {};

export function setThemeOverrides(nouvelles) {
  overrides = nouvelles || {};
}

/** Définition d'une catégorie, personnalisations utilisateur incluses. */
export function getTheme(id) {
  const base = baseDe(id);
  const o = overrides[base.id];
  if (!o) return { textColor: TEXT_COLOR_DEFAUT, ...base };
  return {
    ...base,
    textColor: TEXT_COLOR_DEFAUT,
    ...Object.fromEntries(Object.entries(o).filter(([, v]) => v)),
  };
}

/** Valeurs par défaut (sans personnalisation) — pour « Réinitialiser ». */
export function getDefaultTheme(id) {
  return { textColor: TEXT_COLOR_DEFAUT, ...baseDe(id) };
}

export function themeExists(id) {
  return parId.has(id) || customThemes.some((t) => t.id === id);
}

/** Vrai pour les catégories créées/importées par l'utilisateur (supprimables),
 *  faux pour les catégories de base de l'application. */
export function isCustomTheme(id) {
  return customThemes.some((t) => t.id === id);
}
