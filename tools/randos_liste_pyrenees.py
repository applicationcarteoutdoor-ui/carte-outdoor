# -*- coding: utf-8 -*-
"""Liste éditoriale des randonnées emblématiques — PYRÉNÉES.

Mêmes conventions que randos_liste_alpes_nord.py.
Écartés d'office : Vignemale et Balaïtous (glaciers/alpinisme), pic du Midi
d'Ossau (cheminées d'escalade en voie normale), les objectifs « lac » déjà
en catégorie lac (Gaube, Oô, Ayous…), Artzamendi et Hautacam (routes au
sommet).
"""

MASSIFS = {
    "Pays basque-Béarn": {
        "bbox": (42.75, 43.45, -1.85, -0.35),
        "randos": [
            {"nom": "La Rhune", "titres": ["La Rhune"],
             "altitude": 900, "depart": "Col de Saint-Ignace (≈ 169 m)",
             "depart_alt": 169,
             "duree": "≈ 4 h aller-retour",
             "voie": "La montagne mythique du Labourd, entre pottoks et "
                     "palombières — vue sur toute la côte basque.",
             "osm": {"noms": ["Col de Saint-Ignace"], "rayon": 4500}},
            {"nom": "Pic d'Orhy", "titres": ["Pic d'Orhy", "Orhy"],
             "altitude": 2017, "depart": "Chalets d'Iraty, col Bagargiak (≈ 1327 m)",
             "depart_alt": 1327,
             "voie": "Premier 2000 des Pyrénées depuis l'Atlantique, par "
                     "la crête frontière de Soule depuis les cols d'Iraty "
                     "(le port de Larrau n'est pas nommé dans OSM).",
             "osm": {"noms": ["Col Bagargiak", "Chalets d'Iraty",
                              "Col d'Organbidexka", "Col d'Orgambidesca"],
                     "rayon": 6500}},
            {"nom": "Pic d'Iparla", "titres": ["Iparla"],
             "altitude": 1044, "depart": "Bidarray (≈ 150 m)", "depart_alt": 150,
             "voie": "La grande crête d'Iparla au-dessus de la vallée des "
                     "Aldudes — vols de vautours garantis.",
             "osm": {"noms": ["Bidarray"], "rayon": 5500}},
            {"nom": "Mondarrain", "titres": ["Mondarrain"],
             "altitude": 749, "depart": "Laxia, Itxassou (≈ 100 m)", "depart_alt": 100,
             "voie": "Sommet-forteresse dominant la vallée de la Nive — "
                     "redoutes, pottoks et rochers sommitaux.",
             "osm": {"noms": ["Laxia"], "rayon": 5000}},
            {"nom": "Pic d'Anie", "titres": ["Pic d'Anie"],
             "altitude": 2504, "depart": "La Pierre Saint-Martin (≈ 1650 m)",
             "depart_alt": 1650,
             "voie": "Voie normale par le pas du Braca et les arres de "
                     "lapiaz — la pyramide du Barétous.",
             "osm": {"noms": ["La Pierre Saint-Martin", "La Pierre-Saint-Martin"],
                     "rayon": 7000}},
        ],
    },
    "Bigorre": {
        "bbox": (42.60, 43.20, -0.40, 0.40),
        "randos": [
            {"nom": "Pic du Midi de Bigorre", "titres": ["Pic du Midi de Bigorre"],
             "altitude": 2876, "depart": "Col du Tourmalet (≈ 2115 m)",
             "depart_alt": 2115,
             "duree": "≈ 5 h aller-retour",
             "voie": "Voie normale depuis le Tourmalet par les Laquets — "
                     "l'observatoire mythique des Pyrénées.",
             "osm": {"noms": ["Col du Tourmalet"], "rayon": 5000}},
            {"nom": "Cirque de Gavarnie", "titres": ["Cirque de Gavarnie"],
             "altitude": None, "depart": "Gavarnie (≈ 1365 m)", "depart_alt": None,
             "duree": "≈ 3 h aller-retour",
             "voie": "Le grand site des Pyrénées, classé UNESCO : muraille "
                     "de 1 500 m et Grande Cascade, depuis le village.",
             "osm": {"noms": ["Gavarnie"], "rayon": 5500}},
            {"nom": "Brèche de Roland", "titres": ["Brèche de Roland"],
             "altitude": 2807, "depart": "Col des Tentes, Gavarnie (≈ 2208 m)",
             "depart_alt": 2208,
             "voie": "Par le port de Boucharo et le refuge des Sarradets — "
                     "l'entaille légendaire de la muraille de Gavarnie "
                     "(névés fréquents, randonnée exigeante).",
             "osm": {"noms": ["Col de Tentes", "Col des Tentes",
                              "Port de Boucharo", "Col de Boucharo"],
                     "rayon": 5500}},
            {"nom": "Pic de Néouvielle", "titres": ["Pic de Néouvielle"],
             "altitude": 3091, "depart": "Lac d'Aubert, réserve du Néouvielle (≈ 2150 m)",
             "depart_alt": 2150,
             "voie": "Voie normale par la brèche de Chausenque — 3000 "
                     "classique au-dessus des lacs de la réserve.",
             # parking le plus proche du sommet = parking du lac d'Aubert
             # (le nom « Lac d'Aubert » résout au CENTRE du lac, sans sentier
             # à moins de 300 m — vécu au premier routage).
             "osm": {"parking": True, "rayon": 5000}},
            # Pic de Cabaliros : pas d'article Wikipédia fr → écarté.
        ],
    },
    "Luchonnais": {
        "bbox": (42.55, 43.00, 0.40, 0.80),
        "randos": [
            {"nom": "Port de Vénasque", "titres": ["Port de Vénasque"],
             "altitude": 2444, "depart": "Hospice de France (≈ 1385 m)",
             "depart_alt": 1385,
             "voie": "Le passage historique vers l'Aragon depuis l'hospice "
                     "de France — face à face brutal avec l'Aneto.",
             "osm": {"noms": ["Hospice de France"], "rayon": 4500}},
            {"nom": "Pic de Sauvegarde", "titres": ["Pic de Sauvegarde"],
             "altitude": 2737, "depart": "Hospice de France (≈ 1385 m)",
             "depart_alt": 1385,
             "voie": "Par le port de Vénasque puis la crête frontière — le "
                     "belvédère classique sur les 3000 de la Maladeta.",
             "osm": {"noms": ["Hospice de France"], "rayon": 5500}},
            {"nom": "Pic de Céciré", "titres": ["Pic de Céciré", "Céciré"],
             "altitude": 2403, "depart": "Superbagnères (≈ 1800 m)", "depart_alt": 1800,
             "voie": "Depuis Superbagnères par le chemin de crête — vue "
                     "sur tout le Luchonnais et la Maladeta.",
             "osm": {"noms": ["Superbagnères"], "rayon": 4500}},
        ],
    },
    "Ariège": {
        "bbox": (42.50, 43.05, 0.90, 2.05),
        "randos": [
            {"nom": "Mont Valier", "titres": ["Mont Valier"],
             "altitude": 2839, "depart": "Pla de la Lau, vallée du Ribérot (≈ 940 m)",
             "depart_alt": 940,
             "voie": "Le « seigneur du Couserans » par la cascade de "
                     "Nérech et le refuge des Estagnous — très longue "
                     "voie normale mythique.",
             "osm": {"noms": ["Pla de la Lau", "La Pucelle"], "rayon": 9500}},
            {"nom": "Pique d'Estats", "titres": ["Pique d'Estats"],
             "altitude": 3143, "depart": "L'Artigue, Auzat (≈ 1180 m)",
             "depart_alt": 1180,
             "voie": "Toit de l'Ariège et de la Catalogne par le port de "
                     "Sullo — immense course de randonnée en haute montagne.",
             "osm": {"noms": ["L'Artigue"], "rayon": 10000}},
            {"nom": "Pic des Trois Seigneurs", "titres": ["Pic des Trois Seigneurs"],
             "altitude": 2199, "depart": "Port de Lers (≈ 1517 m)", "depart_alt": 1517,
             "voie": "Voie normale par l'étang d'Arbu — la pyramide "
                     "emblématique du Vicdessos.",
             "osm": {"noms": ["Port de Lers", "Port de Lhers"], "rayon": 5500}},
            {"nom": "Pic de Soularac", "titres": ["Pic de Soularac"],
             "altitude": 2368, "depart": "Montségur (≈ 900 m)", "depart_alt": 900,
             "voie": "Point culminant du massif de Tabe, au-dessus du "
                     "château cathare de Montségur.",
             "osm": {"noms": ["Montségur"], "rayon": 7000}},
            {"nom": "Pic de Saint-Barthélemy", "titres": ["Pic de Saint-Barthélemy"],
             "altitude": 2348, "depart": "Station des Monts d'Olmes (≈ 1400 m)",
             "depart_alt": 1400,
             "voie": "Par les étangs du massif de Tabe — le sommet sacré "
                     "du pays d'Olmes.",
             "osm": {"noms": ["Les Monts d'Olmes", "Monts d'Olmes"], "rayon": 5500}},
            {"nom": "Pic de Tarbésou", "titres": ["Pic de Tarbésou", "Tarbésou"],
             "altitude": 2364, "depart": "Port de Pailhères (≈ 2001 m)",
             "depart_alt": 2001,
             "voie": "Boucle par les étangs bleu et noir de Rabassoles — "
                     "crêtes douces du Donezan.",
             "osm": {"noms": ["Port de Pailhères", "Col de Pailhères"],
                     "rayon": 4500}},
        ],
    },
    "Pyrénées-Orientales": {
        "bbox": (42.30, 42.85, 1.80, 2.65),
        "randos": [
            {"nom": "Pic du Canigou", "titres": ["Pic du Canigou", "Canigou"],
             "altitude": 2785, "depart": "Refuge des Cortalets (≈ 2150 m)",
             "depart_alt": 2150,
             "duree": "≈ 4 h aller-retour",
             "voie": "La montagne sacrée des Catalans par la voie normale "
                     "des Cortalets — cheminée finale facile.",
             "osm": {"noms": ["Refuge des Cortalets"], "rayon": 5000}},
            {"nom": "Pic Carlit", "titres": ["Pic Carlit", "Carlit"],
             "altitude": 2921, "depart": "Lac des Bouillouses (≈ 2020 m)",
             "depart_alt": 2020,
             "voie": "Toit des Pyrénées-Orientales par le désert du Carlit "
                     "et ses douze lacs — final raide et rocheux.",
             # parking du barrage des Bouillouses (le nom « Lac des
             # Bouillouses » résout au centre du lac, loin des sentiers).
             "osm": {"parking": True, "rayon": 7500}},
            {"nom": "Cambre d'Aze", "titres": ["Cambre d'Aze"],
             "altitude": 2711, "depart": "Eyne (≈ 1600 m)", "depart_alt": 1600,
             "voie": "Par la vallée d'Eyne, « vallée des fleurs » classée "
                     "réserve naturelle — cirque glaciaire au sommet.",
             "osm": {"noms": ["Eyne"], "rayon": 7500}},
            {"nom": "Pic de Madrès", "titres": ["Pic de Madrès"],
             "altitude": 2469, "depart": "Col de Jau (≈ 1506 m)", "depart_alt": 1506,
             "voie": "Longue crête forestière puis pelouses sommitales — "
                     "le château d'eau du Conflent et du Capcir.",
             "osm": {"noms": ["Col de Jau"], "rayon": 8000}},
            {"nom": "Pic du Costabonne", "titres": ["Pic du Costabonne",
                                                    "Costabonne"],
             "altitude": 2465, "depart": "La Preste, Prats-de-Mollo (≈ 1130 m)",
             "depart_alt": 1130,
             "voie": "Voie normale du haut Vallespir par le col du Pal — "
                     "sources du Tech et crête frontière.",
             "osm": {"noms": ["La Preste"], "rayon": 7500}},
        ],
    },
}
