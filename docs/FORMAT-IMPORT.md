# Formats d'import

Le bouton **Import** (icône ⬆ de la barre, entrée du menu ⋯ sur mobile, ou
bouton « Ajouter des traces » de l'onglet Traces) accepte **tous les formats
ci-dessous, plusieurs fichiers à la fois**. Chaque fichier est analysé :

- les **lignes** (itinéraires) deviennent des **traces** (1 fichier = 1 trace) ;
- les **points** passent par un dialogue de validation qui liste les erreurs
  ligne par ligne — vous importez les points valides ou annulez.

| Extension | Contenu accepté | Conversion |
|---|---|---|
| `.gpx` | traces de rando/vélo | toGeoJSON |
| `.kml` | points et/ou lignes (Google My Maps, etc.) | toGeoJSON |
| `.kmz` | KML zippé | fflate + toGeoJSON |
| `.geojson` / `.json` | FeatureCollection (points et/ou lignes) ou sauvegarde de l'app | direct |
| `.csv` | points (colonnes fixes, voir ci-dessous) | analyseur intégré |

Si les points d'un fichier n'indiquent pas de catégorie (KML, GeoJSON tiers,
CSV sans colonne `theme`), l'application demande de choisir **une catégorie
pour tout le fichier** au moment de l'import.

## 1. GeoJSON — format des points

`FeatureCollection` de `Point`. Champs de `properties` :

| Champ | Obligatoire | Description |
|---|---|---|
| `name` | ✅ | Nom du point |
| `theme` | (✅) | Identifiant de catégorie (voir liste) — sinon choix à l'import |
| `id` | — | Identifiant unique ; généré automatiquement si absent |
| `description` | — | Texte libre (retours à la ligne conservés) |
| `link` | — | URL du site de référence |
| `links` | — | Tableau `[{label, url}]` de liens supplémentaires |
| `photos` | — | Tableau d'URLs d'images |
| `details` | — | Objet `{clé: valeur}` de champs spécifiques à la catégorie |

Rappel GeoJSON : coordonnées dans l'ordre **`[longitude, latitude]`**.

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": { "type": "Point", "coordinates": [6.205759, 44.623407] },
      "properties": {
        "name": "Via ferrata d'Ancelle",
        "theme": "via-ferrata",
        "description": "Trois parcours au-dessus du torrent.",
        "link": "https://www.viaferrata-fr.net/",
        "details": { "cotation": "PD à D", "duree": "2 h" }
      }
    }
  ]
}
```

## 2. CSV

- Séparateur `,` ou `;` (détecté automatiquement), guillemets acceptés.
- Ligne d'en-tête obligatoire, colonnes **`name`, `lat`, `lon`** requises.
- Colonnes optionnelles : `theme`, `description`, `link`, `id`.
- Virgule décimale tolérée dans `lat`/`lon`.
- **Toute autre colonne** devient un champ « détail » affiché dans la fiche.

```csv
name;lat;lon;theme;description;cotation
Via ferrata de la Roche;45.123;6.456;via-ferrata;Belle ambiance;AD
Cascade du Pin;45.200;6.300;cascade;Accès 30 min;
```

## 3. Fichier de sauvegarde de l'application

Le fichier produit par **⬇ Exporter** (bas du panneau des catégories)
contient vos points importés/ajoutés, votre suivi (à faire / fait / favori),
votre **carnet** (notes + photos) et vos **catégories personnalisées**.
Le réimporter restaure tout — pratique pour changer d'appareil.

```json
{
  "formatVersion": 2,
  "points": { "type": "FeatureCollection", "features": [] },
  "statuses": { "vf-001": "fait", "ex-002": "a-faire", "rf-3414": "favori" },
  "journal": { "vf-001": [{ "id": "j-x", "date": "2026-07-04T10:00:00Z", "text": "…", "photo": "data:image/jpeg;…" }] },
  "customThemes": [{ "id": "perso-champignons", "label": "Coins à champignons", "icon": "🍄", "color": "#7048b6" }]
}
```

(Les sauvegardes `formatVersion: 1` de l'ancienne version restent importables.)

## Identifiants de catégorie valides

`via-ferrata`, `escalade`, `grotte`, `cascade`, `chateau`, `cathedrale`,
`cite-caractere`, `refuge`, `toilettes`, plus vos catégories personnalisées
(`perso-…`, créées via le bouton ➕ « Ajouter un point »).

Les points importés avec une catégorie inconnue sont rattachés à « Autre »
(dont l'ancienne `chateau-a-verifier`, fusionnée dans `chateau` en v45).

⚠️ Ces identifiants sont **stables** : renommer une catégorie dans
l'application (panneau liste → ✎) ne change que son nom affiché, jamais son
identifiant — vos points restent rattachés. Pour ajouter une catégorie,
modifiez `js/config/themes.js` (voir le README).
