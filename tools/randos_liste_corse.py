# -*- coding: utf-8 -*-
"""Liste éditoriale des randonnées emblématiques — CORSE.

Mêmes conventions que randos_liste_alpes_nord.py.
Écartés d'office : les lacs de Nino, Melo et Capitello (déjà en catégorie
lac), les aiguilles de Bavella (escalade). Les voies normales corses sont
souvent longues et cairnées : la mention « exigeante » est portée quand le
terrain le justifie.
"""

MASSIFS = {
    "Corse": {
        "bbox": (41.45, 43.05, 8.40, 9.55),
        "randos": [
            {"nom": "Monte Cinto", "titres": ["Monte Cinto"],
             "altitude": 2706, "depart": "Haut-Asco (≈ 1422 m)", "depart_alt": 1422,
             "voie": "Toit de la Corse par la voie normale du versant "
                     "Asco — longue course cairnée très exigeante.",
             "osm": {"noms": ["Haut-Asco", "Haut Asco", "Ascu Stagnu"],
                     "rayon": 5500}},
            {"nom": "Paglia Orba", "titres": ["Paglia Orba"],
             "altitude": 2525, "depart": "Castel di Vergio (≈ 1404 m)",
             "depart_alt": 1404,
             "voie": "Le « Cervin corse » par le refuge de Ciottulu di i "
                     "Mori — final rocheux exigeant (passages faciles d'escalade).",
             "osm": {"noms": ["Castel di Vergio", "Castel de Vergio",
                              "Col de Vergio"], "rayon": 8500}},
            {"nom": "Monte Rotondo", "titres": ["Monte Rotondo"],
             "altitude": 2622, "depart": "Bergeries de Timozzo, Restonica (≈ 1500 m)",
             "depart_alt": 1500,
             "voie": "Par le vallon du Timozzo et le lac de l'Oriente — "
                     "deuxième sommet de l'île, cirques et névés tardifs.",
             "osm": {"noms": ["Bergeries de Timozzo", "Timozzo"], "rayon": 6000}},
            {"nom": "Monte d'Oro", "titres": ["Monte d'Oro"],
             "altitude": 2390, "depart": "Vizzavona (≈ 920 m)", "depart_alt": 920,
             "voie": "La pyramide de Vizzavona par la voie des Pozzi — "
                     "grande classique exigeante au cœur de l'île.",
             "osm": {"noms": ["Vizzavona"], "rayon": 6500}},
            {"nom": "Monte Renoso", "titres": ["Monte Renoso", "Monte Renosu"],
             "altitude": 2352, "depart": "Bergeries de Capannelle (≈ 1586 m)",
             "depart_alt": 1586,
             "voie": "Par le lac de Bastani — le grand sommet débonnaire "
                     "du sud, pozzines et vue sur les deux mers.",
             "osm": {"noms": ["Capannelle", "Bergeries de Capannelle",
                              "Capanelle"], "rayon": 6000}},
            {"nom": "Monte Incudine", "titres": ["Monte Incudine", "Incudine"],
             "altitude": 2134, "depart": "Col de Bavella (≈ 1218 m)", "depart_alt": 1218,
             "voie": "L'« enclume » de l'Alta Rocca par le GR20 sud depuis "
                     "Bavella — longue traversée en crête.",
             "osm": {"noms": ["Col de Bavella", "Bocca di Bavella"],
                     "rayon": 10000}},
            {"nom": "Monte San Petrone", "titres": ["Monte San Petrone"],
             "altitude": 1767, "depart": "Col de Prato (≈ 985 m)", "depart_alt": 985,
             "voie": "Toit de la Castagniccia par les forêts de châtaigniers "
                     "et de hêtres — vue sur toute la côte orientale.",
             "osm": {"noms": ["Col de Prato", "Bocca di u Pratu"], "rayon": 5500}},
            {"nom": "Monte Stello", "titres": ["Monte Stello"],
             "altitude": 1306, "depart": "Pozzo, Brando (≈ 380 m)", "depart_alt": 380,
             "voie": "Le sommet du Cap Corse depuis la marine de Pozzo — "
                     "maquis, crêtes et mer des deux côtés.",
             "osm": {"noms": ["Pozzo"], "rayon": 5500}},
            # Capu Rossu : coordonnées Wikipédia à mi-presqu'île, dans le
            # maquis à 315 m du premier sentier → routage refusé, ÉCARTÉ
            # (rando-0128 retiré, id gelé au registre). Rien d'inventé.
        ],
    },
}
