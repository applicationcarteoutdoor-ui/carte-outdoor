# -*- coding: utf-8 -*-
"""Liste éditoriale des randonnées emblématiques — ALPES DU SUD ET PROVENCE.

Mêmes conventions que randos_liste_alpes_nord.py. Le groupe « Provence »
réunit Ventoux, Baronnies, Luberon, Sainte-Victoire et Garlaban (massifs
provençaux de basse altitude, trop petits pour un filtre chacun).
Écartés d'office : la Meije, le Pelvoux, l'Aiguille de Chambeyron (alpinisme),
le Pic de Rochebrune (cheminées d'escalade), la cime de la Bonette (route au
sommet), les objectifs « lac » déjà en catégorie lac (Lauvitel, Allos,
Lauzanier…) et le cirque de Navacelles (cascade homonyme déjà en base).
"""

MASSIFS = {
    "Écrins": {
        "bbox": (44.50, 45.20, 5.90, 6.60),
        "randos": [
            {"nom": "Tête de la Maye", "titres": ["Tête de la Maye"],
             "altitude": 2518, "depart": "La Bérarde (≈ 1710 m)", "depart_alt": 1710,
             "voie": "Belvédère mythique de la Bérarde, face à la Meije et "
                     "aux Écrins — sentier raide, passages câblés au sommet.",
             "osm": {"noms": ["La Bérarde"], "rayon": 3500}},
            {"nom": "Vieux Chaillol", "titres": ["Vieux Chaillol"],
             "altitude": 3163, "depart": "Chaillol 1600 (≈ 1600 m)", "depart_alt": 1600,
             "voie": "Grande voie normale de randonnée du Champsaur, par "
                     "les chalets de Rouanne — panorama sur tout le massif.",
             "osm": {"noms": ["Chaillol 1600", "Chaillol"], "rayon": 8500}},
            # Pic du Mas de la Grave : pas d'article Wikipédia fr → écarté.
            {"nom": "Plateau d'Emparis", "titres": ["Plateau d'Emparis"],
             "altitude": None, "depart": "Le Chazelet (≈ 1800 m)", "depart_alt": None,
             "voie": "Boucle des lacs Lérié et Noir sur le plateau d'alpage — "
                     "le miroir des glaciers de la Meije.",
             "osm": {"noms": ["Le Chazelet"], "rayon": 7000}},
            {"nom": "Mont Guillaume", "titres": ["Mont Guillaume"],
             "altitude": 2542, "depart": "Embrun (≈ 870 m)", "depart_alt": 870,
             "voie": "Voie normale par la forêt domaniale et la chapelle "
                     "Saint-Guillaume — vigie au-dessus de Serre-Ponçon.",
             "osm": {"noms": ["Embrun"], "rayon": 9000}},
        ],
    },
    "Dévoluy": {
        "bbox": (44.55, 44.95, 5.75, 6.10),
        "randos": [
            {"nom": "Obiou", "titres": ["Obiou"],
             "altitude": 2789, "depart": "Les Payas, Pellafol (≈ 1670 m)",
             "depart_alt": 1670,
             "voie": "Point culminant du Dévoluy — voie normale cairnée "
                     "exigeante par le col des Faïsses, terrain à chamois.",
             "osm": {"noms": ["Les Payas"], "rayon": 5500}},
            {"nom": "Grand Ferrand", "titres": ["Grand Ferrand"],
             "altitude": 2758, "depart": "La Jarjatte, Lus-la-Croix-Haute (≈ 1180 m)",
             "depart_alt": 1180,
             "voie": "Voie normale par le vallon de la Jarjatte et le col "
                     "du Charnier — deuxième sommet du massif.",
             "osm": {"noms": ["La Jarjatte"], "rayon": 7000}},
            {"nom": "Pic de Bure", "titres": ["Pic de Bure"],
             "altitude": 2709, "depart": "Superdévoluy (≈ 1500 m)", "depart_alt": 1500,
             "voie": "Montée par la combe Ratin vers le vaste plateau de "
                     "Bure et son observatoire radioastronomique.",
             "osm": {"noms": ["Superdévoluy", "SuperDévoluy"], "rayon": 7000}},
        ],
    },
    "Queyras": {
        "bbox": (44.50, 44.90, 6.65, 7.15),
        "randos": [
            {"nom": "Pain de Sucre", "titres": ["Pain de Sucre (Alpes cottiennes)",
                                                "Pain de Sucre (Queyras)"],
             "altitude": 3208, "depart": "Col Agnel (≈ 2744 m)", "depart_alt": 2744,
             "duree": "≈ 3 h aller-retour",
             "voie": "Courte voie normale raide et cairnée depuis le col "
                     "Agnel — vue plongeante sur le Viso.",
             "osm": {"noms": ["Col Agnel"], "rayon": 3500}},
            {"nom": "Pic de Caramantran", "titres": ["Pic de Caramantran"],
             "altitude": 3025, "depart": "Col Agnel (≈ 2744 m)", "depart_alt": 2744,
             "voie": "Un 3000 débonnaire par le col de Chamoussière — "
                     "sommet panoramique idéal en premier 3000.",
             "osm": {"noms": ["Col Agnel"], "rayon": 4000}},
            {"nom": "Pic de Château Renard", "titres": ["Pic de Château Renard"],
             "altitude": 2989, "depart": "Saint-Véran (≈ 2040 m)", "depart_alt": 2040,
             "voie": "Montée depuis la plus haute commune d'Europe, par la "
                     "chapelle de Clausis et l'observatoire.",
             "osm": {"noms": ["Saint-Véran"], "rayon": 6000}},
            # Tête du Pelvas : pas d'article fr avec coordonnées → écartée.
            {"nom": "Bric Froid", "titres": ["Bric Froid"],
             "altitude": 3302, "depart": "Ristolas (≈ 1600 m)", "depart_alt": 1600,
             "voie": "Longue voie normale par le vallon de Ségure — crête "
                     "frontière face au mont Viso.",
             "osm": {"noms": ["Ristolas"], "rayon": 9500}},
        ],
    },
    "Ubaye": {
        "bbox": (44.25, 44.70, 6.50, 7.10),
        "randos": [
            {"nom": "Brec de Chambeyron", "titres": ["Brec de Chambeyron"],
             "altitude": 3389, "depart": "Fouillouse, Saint-Paul-sur-Ubaye (≈ 1900 m)",
             "depart_alt": 1900,
             "voie": "Par le refuge et les lacs de Chambeyron — sommet "
                     "fameux, final rocheux cairné très exigeant (passages II).",
             "osm": {"noms": ["Fouillouse"], "rayon": 7500}},
            {"nom": "Grande Séolane", "titres": ["Grande Séolane"],
             "altitude": 2909, "depart": "Les Agneliers (≈ 1800 m)", "depart_alt": 1800,
             "voie": "Voie normale par le vallon des Agneliers — la muraille "
                     "calcaire qui domine Pra-Loup.",
             "osm": {"noms": ["Les Agneliers"], "rayon": 6000}},
            # Tête de Louis XVI : pas d'article Wikipédia → écartée.
        ],
    },
    "Mercantour": {
        "bbox": (43.90, 44.40, 6.55, 7.60),
        "randos": [
            {"nom": "Mont Bégo", "titres": ["Mont Bégo"],
             "altitude": 2872, "depart": "Lac des Mesches, Tende (≈ 1390 m)",
             "depart_alt": 1390,
             "voie": "Par la vallée des Merveilles — la montagne sacrée aux "
                     "40 000 gravures protohistoriques.",
             "osm": {"noms": ["Lac des Mesches", "Les Mesches"], "rayon": 7500}},
            {"nom": "Vallée des Merveilles", "titres": ["Vallée des Merveilles"],
             "altitude": None, "depart": "Lac des Mesches, Tende (≈ 1390 m)",
             "depart_alt": None,
             "voie": "Montée au cœur du site archéologique classé, par le "
                     "refuge des Merveilles — gravures rupestres et lacs.",
             "osm": {"noms": ["Lac des Mesches", "Les Mesches"], "rayon": 7000}},
            {"nom": "Cime du Gélas", "titres": ["Cime du Gélas"],
             "altitude": 3143, "depart": "Madone de Fenestre (≈ 1900 m)",
             "depart_alt": 1900,
             "voie": "Point culminant des Alpes-Maritimes — voie normale "
                     "exigeante depuis le sanctuaire de la Madone.",
             "osm": {"noms": ["Madone de Fenestre"], "rayon": 5000}},
            {"nom": "Mont Mounier", "titres": ["Mont Mounier"],
             "altitude": 2817, "depart": "Beuil (≈ 1450 m)", "depart_alt": 1450,
             "voie": "Longue croupe panoramique dominant les gorges du "
                     "Cians — de la mer aux Écrins par temps clair.",
             "osm": {"noms": ["Beuil"], "rayon": 9500}},
            {"nom": "Mont Pelat", "titres": ["Mont Pelat"],
             "altitude": 3051, "depart": "Col de la Cayolle (≈ 2326 m)",
             "depart_alt": 2326,
             "voie": "Voie normale depuis le col de la Cayolle — le grand "
                     "3000 débonnaire du haut Verdon.",
             "osm": {"noms": ["Col de la Cayolle"], "rayon": 6500}},
        ],
    },
    "Verdon": {
        "bbox": (43.60, 44.05, 6.10, 6.65),
        "randos": [
            {"nom": "Mourre de Chanier", "titres": ["Mourre de Chanier"],
             "altitude": 1930, "depart": "Blieux (≈ 940 m)", "depart_alt": 940,
             "voie": "Point culminant des Préalpes de Castellane, entre "
                     "lavandes et crêtes — vue du Ventoux à la mer.",
             "osm": {"noms": ["Blieux"], "rayon": 7500}},
            # Cadières de Brandis : pas d'article Wikipédia → écartées.
            {"nom": "Grand Margès", "titres": ["Grand Margès"],
             "altitude": 1576, "depart": "Aiguines (≈ 820 m)", "depart_alt": 820,
             "voie": "Montée au belvédère du grand canyon du Verdon et du "
                     "lac de Sainte-Croix.",
             "osm": {"noms": ["Aiguines"], "rayon": 8000}},
        ],
    },
    "Provence": {
        "bbox": (43.15, 44.35, 4.85, 6.00),
        "randos": [
            {"nom": "Mont Ventoux", "titres": ["Mont Ventoux"],
             "altitude": 1910, "depart": "Chalet Reynard, Bédoin (≈ 1440 m)",
             "depart_alt": 1440,
             "voie": "Le Géant de Provence par le sentier des crêtes — "
                     "pierrier lunaire et panorama immense au sommet.",
             "osm": {"noms": ["Chalet Reynard", "Le Chalet Reynard"], "rayon": 7000}},
            {"nom": "Montagne Sainte-Victoire",
             "titres": ["Montagne Sainte-Victoire"],
             "altitude": 1011, "depart": "Puyloubier (≈ 350 m)", "depart_alt": 350,
             "voie": "Montée au pic des Mouches, point culminant de la "
                     "montagne de Cézanne, par le versant de Puyloubier.",
             "osm": {"noms": ["Puyloubier"], "rayon": 6000}},
            {"nom": "Mourre Nègre", "titres": ["Mourre Nègre"],
             "altitude": 1125, "depart": "Auribeau (≈ 500 m)", "depart_alt": 500,
             "voie": "Point culminant du Luberon par les crêtes du grand "
                     "Luberon — cèdres, garrigue et vue sur les Alpes.",
             "osm": {"noms": ["Auribeau"], "rayon": 6000}},
            {"nom": "Garlaban", "titres": ["Garlaban"],
             "altitude": 714, "depart": "La Treille, Marseille (≈ 210 m)",
             "depart_alt": 210,
             "voie": "Les collines de Pagnol depuis le village de la "
                     "Treille — garrigue, barres calcaires et grottes.",
             "osm": {"noms": ["La Treille"], "rayon": 6500}},
            {"nom": "Dentelles de Montmirail", "titres": ["Dentelles de Montmirail"],
             "altitude": 722, "depart": "Gigondas (≈ 310 m)", "depart_alt": 310,
             "voie": "Boucle au pied des lames calcaires dressées au-dessus "
                     "des vignobles — site emblématique du Vaucluse.",
             "osm": {"noms": ["Gigondas"], "rayon": 4500}},
        ],
    },
}
