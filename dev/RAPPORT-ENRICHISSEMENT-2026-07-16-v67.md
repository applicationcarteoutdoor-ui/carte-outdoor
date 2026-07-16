# Rapport d'enrichissement — v67 (16 juillet 2026)

Demande utilisateur : liens Wikipédia + photos, liens des sites de via ferrata
(« le lien du site de la via ferrata, pas juste ferrate365.it »), randonnées
iconiques, toilettes et fontaines **pour tous les pays**.

## 1. Liens Wikipédia + photos (Suisse, Italie, Espagne)

`tools/enrichir_pays_wikipedia.py` — appariement conservateur : titre = nom
EXACT du point, article retenu seulement si ses coordonnées sont à ≤ 10 km
(25 km pour les lacs). CH interrogé en fr → de → it (noms OSM en langue locale).

| Pays | Interrogés | Appariés | Photos | Après build (liens 🔗) |
|---|---|---|---|---|
| 🇨🇭 ch | 4 436 | 1 130 | 1 080 | 1 178 |
| 🇮🇹 it | 26 371 | 2 622 | 2 479 | 3 036 |
| 🇪🇸 es | 20 078 | 1 507 | 1 432 | 1 633 |

Chaque appariement ajoute : photo 960 px (`upload.wikimedia.org`, conforme CSP),
lien « 🔗 Wikipédia », description (1re phrase) si le point n'en avait pas, et
passe la fiche en « Référencé ». Appliqué AU BUILD par `construire_pays.py`
(cache `tools/pays-wiki-<iso>.json`, clé « nom|lat4 » → ids stables).

## 2. Fiches via ferrata des sites spécialisés

`tools/recolter_vf_sites.py` + `tools/apparier_vf_sites.py` :

| Pays | Site de référence | Fiches récoltées | VF appariées / total |
|---|---|---|---|
| 🇮🇹 it | ferrate365.it (GPS extraits du lien « Indicazioni Stradali ») | 448 | **187 / 284** |
| 🇪🇸 es | deandar.com (KML de la carte : nom + lien + K + GPS) | 322 | **85 / 143** (+83 cotations K récupérées) |
| 🇨🇭 ch | myferrata.ch (titres seuls, pas de GPS) | 38 | **26 / 89** |

Appariement conservateur : accord de nom d'abord (< 5 km) ; proximité aveugle
< 300 m seulement si la fiche est SEULE à < 1 km (falaises multi-ferratas =
ambiguës, jamais devinées). France : viaferrata-fr.net déjà en place ; NZ :
sites officiels déjà en place. **rocjumper.com écarté : son robots.txt interdit
les agents IA** (on respecte). deandar : extraction minimale nom/lien/K/GPS
(licence CC BY-NC-ND sur le contenu — on ne copie rien d'autre, on LIE).

## 3. Randonnées iconiques (72 tracées / 74 retenues)

Listes éditoriales par recherche web multi-agents (3 chercheurs + 3
vérificateurs adverses), puis `tools/recolter_randos_pays.py` (routage Dijkstra
sur le réseau OSM, modèle France) :

- 🇨🇭 **24** (Oeschinensee, Eiger Trail, Faulhorn, 5-Seenweg/Stellisee, Creux du
  Van, cabanes Trient/Moiry, Piz Languard, crête du Stoos, Jöriseen…)
- 🇮🇹 **23** (Tre Cime, lac de Sorapis, Seceda, Piz Boè, tours du Vajolet,
  Corno Grande, Sentier des Dieux, Cinque Terre, Cala Goloritzé, Zingaro…)
- 🇪🇸 **25** (Ruta del Cares, Urriellu, Ordesa/Cola de Caballo, Aneto-Renclusa,
  Mulhacén, Pedraforca, Sant Jeroni, Mont-rebei, Caminito del Rey, Teide…)

Chaque point : tracé réel (data/<iso>/randos.geojson, GPX téléchargeable),
distance mesurée, D+ estimé (open-meteo), durée éditoriale (affichée seulement
si cohérente avec la distance), massif, départ, liens Komoot/AllTrails/
Outdooractive (recherches par site — pas d'URL profonde devinée).

Résolutions ajoutées en cours de route : homonymes départagés par tag du type
attendu (sommet/lac/refuge), lieu majoritaire ≥ 70 %, paire départ↔objectif,
et **boucles reprises par leur relation OSM** (Urederra, Ruta amarilla du
Torcal, Congost de Mont-rebei, Jöriseen, Val Trupchun).

**Écartées honnêtement (2)** : tour du lac de Braies et Gelmersee — boucles
sans relation OSM, le routage A→B produit un tracé dégénéré (< 0,9 km).

## 4. Toilettes + fontaines pour tous les pays

`tools/recolter_sanitaires_pays.py` (Overpass, aire ISO + tuiles subdivisées,
schémas identiques à la France, ids stables dérivés des ids OSM) :

| Pays | Toilettes | Points d'eau | Poids |
|---|---|---|---|
| 🇮🇹 it | 10 211 | 79 138 | 2,1 + 17,7 Mo |
| 🇪🇸 es | 7 404 | 60 144 | 1,5 + 13,5 Mo |
| 🇨🇭 ch | 6 588 | 18 023 | 1,4 + 3,9 Mo |
| 🇳🇿 nz | 4 562 | 1 957 | 0,9 + 0,4 Mo |

Côté app : `pays.couchesLourdes` devient une table `id → fichier` ;
`chargerCouche(id)` générique ; FAB 🚻 visible partout où la couche existe ;
compteurs « … » par pays ; dialogues d'avertissement inchangés. Récolte NZ
sans bbox (antiméridien des Chatham), 0 tuile en échec.

## Vérifications

- Boot par pays : compteurs corrects, toilettes IT 10 211 / eau ES 60 144 /
  toilettes NZ 4 562 chargées via les dialogues, `grotte` NZ reste normale (127).
- Exclusivité v66 conservée (cocher Randonnée décoche Toilettes).
- Fiche « Tour des Tre Cime di Lavaredo » : tracé épinglé (polyligne présente),
  GPX, description, D+ ; VF « Klettersteig Fürenwand » → fiche myferrata.ch ;
  VF « Via Ferrata Santa Elena » → fiche deandar + cotation K1.
- France : régression zéro (eau 49 531, musées 5 053, données inchangées).
- dev/tests.html : **24 réussis · 0 échoué** ; console : aucune erreur.

## Pièges consignés (CLAUDE.md à jour)

kumi.systems pend jusqu'au timeout ; osm.ch = Suisse seule (rapide) ;
maps.mail.ru = planète ; `out geom` émet des sommets null ; l'encodage de
deandar varie utf-8/cp1252 ; rocjumper interdit les agents IA ; les points
lac sont DANS l'eau (tolérance d'arrivée 900 m) ; les boucles se tracent par
relation OSM, jamais par routage A→B.
