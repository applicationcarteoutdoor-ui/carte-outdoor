# -*- coding: utf-8 -*-
"""Liste éditoriale des randonnées emblématiques — JURA, VOSGES, MASSIF CENTRAL.

Mêmes conventions que randos_liste_alpes_nord.py.
Écartés d'office : cascades du Hérisson et lac Blanc des Vosges (déjà en
catégories cascade/lac), Puy de Dôme par le train (le chemin des Muletiers
est retenu), sommets à route (Mont Revard…), cirque de Navacelles (cascade
homonyme en base).
"""

MASSIFS = {
    "Jura": {
        "bbox": (45.70, 47.15, 5.50, 6.65),
        "randos": [
            {"nom": "Crêt de la Neige", "titres": ["Crêt de la Neige"],
             "altitude": 1721, "depart": "Lélex (≈ 900 m)", "depart_alt": 900,
             "voie": "Point culminant du Jura par les combes de la haute "
                     "chaîne — chamois et vue sur le Mont-Blanc.",
             "osm": {"noms": ["Lélex"], "rayon": 6500}},
            {"nom": "Le Reculet", "titres": ["Le Reculet", "Reculet"],
             "altitude": 1717, "depart": "Lélex (≈ 900 m)", "depart_alt": 900,
             "voie": "Deuxième sommet du Jura, à la grande croix dominant "
                     "le pays de Gex et le Léman.",
             "osm": {"noms": ["Lélex"], "rayon": 8000}},
            {"nom": "Colomby de Gex", "titres": ["Colomby de Gex"],
             "altitude": 1688, "depart": "Col de la Faucille (≈ 1323 m)",
             "depart_alt": 1323,
             "voie": "Crête de la haute chaîne depuis la Faucille — "
                     "alpages, murets et panorama lémanique.",
             "osm": {"noms": ["Col de la Faucille"], "rayon": 6500}},
            {"nom": "Grand Colombier", "titres": ["Grand Colombier (Ain)",
                                                  "Grand Colombier"],
             "altitude": 1534, "depart": "Virieu-le-Petit (≈ 550 m)", "depart_alt": 550,
             "voie": "La sentinelle sud du Jura au-dessus du Rhône — "
                     "montée soutenue, vue sur les lacs et les Alpes.",
             "osm": {"noms": ["Virieu-le-Petit"], "rayon": 7000}},
            {"nom": "Mont d'Or", "titres": ["Mont d'Or (Doubs)"],
             "altitude": 1463, "depart": "Métabief (≈ 1000 m)", "depart_alt": 1000,
             "voie": "Falaises du haut Doubs face à la chaîne des Alpes "
                     "bernoises — sommet du fromage éponyme.",
             "osm": {"noms": ["Métabief"], "rayon": 6000}},
            {"nom": "Pic de l'Aigle", "titres": ["Pic de l'Aigle"],
             "altitude": 998, "depart": "La Chaux-du-Dombief (≈ 730 m)",
             "depart_alt": 730,
             "duree": "≈ 2 h aller-retour",
             "voie": "Le belvédère de la région des lacs — enchaînable "
                     "avec le belvédère des Quatre Lacs.",
             "osm": {"noms": ["La Chaux-du-Dombief"], "rayon": 4000,
                     "marge": 0.06}},
            {"nom": "Crêt de Chalam", "titres": ["Crêt de Chalam"],
             "altitude": 1540, "depart": "La Pesse (≈ 1160 m)", "depart_alt": 1160,
             "voie": "La pyramide du haut Jura au-dessus de la Valserine, "
                     "haut lieu du maquis de l'Ain.",
             "osm": {"noms": ["La Pesse"], "rayon": 6000}},
        ],
    },
    "Vosges": {
        "bbox": (47.70, 48.65, 6.60, 7.40),
        "randos": [
            {"nom": "Grand Ballon", "titres": ["Grand Ballon"],
             "altitude": 1424, "depart": "Col Amic (≈ 825 m)", "depart_alt": 825,
             "voie": "Toit des Vosges par le GR5 — radôme, monument des "
                     "Diables Bleus et vue sur les Alpes par temps clair.",
             "osm": {"noms": ["Col Amic"], "rayon": 5500}},
            {"nom": "Hohneck", "titres": ["Hohneck (Vosges)", "Hohneck"],
             "altitude": 1363, "depart": "Col de la Schlucht (≈ 1139 m)",
             "depart_alt": 1139,
             "duree": "≈ 3 h aller-retour",
             "voie": "Par le sentier des crêtes au-dessus des cirques "
                     "glaciaires de Frankenthal et du Wormspel.",
             "osm": {"noms": ["Col de la Schlucht"], "rayon": 4500}},
            {"nom": "Petit Ballon", "titres": ["Petit Ballon"],
             "altitude": 1272, "depart": "Wasserbourg (≈ 550 m)", "depart_alt": 550,
             "voie": "Montée par les fermes-auberges du Kahlenwasen — "
                     "chaumes à munster et panorama sur la plaine d'Alsace.",
             "osm": {"noms": ["Wasserbourg"], "rayon": 6000}},
            {"nom": "Ballon d'Alsace", "titres": ["Ballon d'Alsace"],
             "altitude": 1247, "depart": "Saint-Maurice-sur-Moselle (≈ 550 m)",
             "depart_alt": 550,
             "voie": "Montée historique par le GR5 — statue de Jeanne "
                     "d'Arc et vierge sommitale entre trois régions.",
             "osm": {"noms": ["Saint-Maurice-sur-Moselle"], "rayon": 8000}},
            {"nom": "Ballon de Servance", "titres": ["Ballon de Servance"],
             "altitude": 1216, "depart": "Plancher-les-Mines (≈ 430 m)",
             "depart_alt": 430,
             "voie": "Par la planche des Belles Filles et la crête — le "
                     "sommet militaire et sauvage des Vosges saônoises.",
             "osm": {"noms": ["Plancher-les-Mines"], "rayon": 8500}},
            {"nom": "Donon", "titres": ["Donon"],
             "altitude": 1009, "depart": "Col du Donon (≈ 727 m)", "depart_alt": 727,
             "duree": "≈ 2 h aller-retour",
             "voie": "La montagne sacrée des Vosges gréseuses — temple "
                     "gallo-romain reconstitué au sommet.",
             "osm": {"noms": ["Col du Donon"], "rayon": 3500}},
            {"nom": "Champ du Feu", "titres": ["Champ du Feu"],
             "altitude": 1098, "depart": "Col de la Charbonnière (≈ 960 m)",
             "depart_alt": 960,
             "voie": "Chaumes sommitales du Bas-Rhin, tour panoramique et "
                     "myrtilles — le plateau nordique alsacien.",
             "osm": {"noms": ["Col de la Charbonnière"], "rayon": 4000}},
            {"nom": "Gazon du Faing", "titres": ["Gazon du Faing"],
             "altitude": 1306, "depart": "Col du Calvaire (≈ 1144 m)",
             "depart_alt": 1144,
             "voie": "Réserve naturelle du Tanet-Gazon du Faing : tourbières "
                     "et vue plongeante sur les lacs Blanc, Noir et des Truites.",
             "osm": {"noms": ["Col du Calvaire"], "rayon": 4500}},
        ],
    },
    "Sancy": {
        "bbox": (45.40, 45.70, 2.65, 3.00),
        "randos": [
            {"nom": "Puy de Sancy", "titres": ["Puy de Sancy"],
             "altitude": 1885, "depart": "Le Mont-Dore (≈ 1050 m)", "depart_alt": 1050,
             "duree": "≈ 4 h 30 aller-retour",
             "voie": "Toit du Massif central par le val de Courre — crêtes "
                     "volcaniques effilées et sources de la Dordogne.",
             "osm": {"noms": ["Le Mont-Dore"], "rayon": 6000}},
            {"nom": "Banne d'Ordanche", "titres": ["Banne d'Ordanche"],
             "altitude": 1512, "depart": "La Bourboule (≈ 850 m)", "depart_alt": 850,
             "voie": "Ancien neck volcanique dominant la haute Dordogne — "
                     "table d'orientation sur la chaîne des Puys.",
             "osm": {"noms": ["La Bourboule"], "rayon": 7000}},
            {"nom": "Puy de l'Angle", "titres": ["Puy de l'Angle"],
             "altitude": 1740, "depart": "Col de la Croix Saint-Robert (≈ 1451 m)",
             "depart_alt": 1451,
             "voie": "Crête des Monts Dore entre la Croix Saint-Robert et "
                     "la Croix Morand — moutonnements herbeux à l'infini.",
             "osm": {"noms": ["Col de la Croix Saint-Robert"], "rayon": 4000}},
        ],
    },
    "Chaîne des Puys": {
        "bbox": (45.65, 46.00, 2.85, 3.10),
        "randos": [
            {"nom": "Puy de Dôme", "titres": ["Puy de Dôme"],
             "altitude": 1465, "depart": "Col de Ceyssat (≈ 1078 m)", "depart_alt": 1078,
             "duree": "≈ 2 h 30 aller-retour",
             "voie": "Le chemin des Muletiers, sur les pas des pèlerins "
                     "gallo-romains — temple de Mercure au sommet (UNESCO).",
             "osm": {"noms": ["Col de Ceyssat"], "rayon": 3000}},
            {"nom": "Puy Pariou", "titres": ["Puy Pariou", "Pariou"],
             "altitude": 1209, "depart": "Orcines (≈ 830 m)", "depart_alt": 830,
             "voie": "Le cratère parfait de la chaîne des Puys — montée "
                     "par la forêt puis tour de la lèvre du volcan.",
             "osm": {"noms": ["Orcines"], "rayon": 5500}},
        ],
    },
    "Cantal": {
        "bbox": (44.90, 45.25, 2.55, 2.95),
        "randos": [
            {"nom": "Puy Mary", "titres": ["Puy Mary"],
             "altitude": 1783, "depart": "Pas de Peyrol (≈ 1588 m)", "depart_alt": 1588,
             "duree": "≈ 1 h 30 aller-retour",
             "voie": "Grand site de France : l'escalier du plus grand "
                     "stratovolcan d'Europe — panorama sur toutes les vallées.",
             "osm": {"noms": ["Pas de Peyrol"], "rayon": 3000}},
            {"nom": "Plomb du Cantal", "titres": ["Plomb du Cantal"],
             "altitude": 1855, "depart": "Prat de Bouc (≈ 1392 m)", "depart_alt": 1392,
             "voie": "Toit du Cantal par les estives de Prat de Bouc — "
                     "burons, vaches salers et crêtes ondulantes.",
             "osm": {"noms": ["Prat de Bouc", "Col de Prat de Bouc"], "rayon": 5500}},
            {"nom": "Puy Griou", "titres": ["Puy Griou"],
             "altitude": 1690, "depart": "Col de Font de Cère, Le Lioran (≈ 1289 m)",
             "depart_alt": 1289,
             "voie": "Le cône phonolitique parfait du Cantal — final raide "
                     "dans les orgues volcaniques.",
             "osm": {"noms": ["Col de Font de Cère", "Le Lioran"], "rayon": 5000}},
            {"nom": "Puy Violent", "titres": ["Puy Violent"],
             "altitude": 1592, "depart": "Salers (≈ 950 m)", "depart_alt": 950,
             "voie": "Depuis l'un des plus beaux villages de France, par "
                     "les estives — vue sur le cirque de Récusset.",
             "osm": {"noms": ["Salers"], "rayon": 8000}},
            {"nom": "Puy de Peyre-Arse", "titres": ["Puy de Peyre-Arse"],
             "altitude": 1806, "depart": "Pas de Peyrol (≈ 1588 m)", "depart_alt": 1588,
             "voie": "Par la brèche de Rolland et la crête — le deuxième "
                     "sommet du volcan cantalien, face au Puy Mary.",
             "osm": {"noms": ["Pas de Peyrol"], "rayon": 4500}},
        ],
    },
    "Cévennes": {
        "bbox": (43.90, 44.60, 3.30, 4.05),
        "randos": [
            {"nom": "Mont Aigoual", "titres": ["Mont Aigoual"],
             "altitude": 1565, "depart": "Valleraugue (≈ 350 m)", "depart_alt": 350,
             "voie": "Le sentier des 4 000 marches, la montée mythique des "
                     "Cévennes — observatoire météo au sommet.",
             "osm": {"noms": ["Valleraugue"], "rayon": 9500}},
            {"nom": "Sommet de Finiels", "titres": ["Sommet de Finiels"],
             "altitude": 1699, "depart": "Col de Finiels (≈ 1541 m)", "depart_alt": 1541,
             "voie": "Toit du mont Lozère par le sentier du GR7, entre "
                     "chaos granitiques et pelouses à myrtilles.",
             "osm": {"noms": ["Col de Finiels"], "rayon": 4000}},
            # Pic Cassini : pas d'article Wikipédia dédié → écarté.
        ],
    },
    "Mézenc": {
        "bbox": (44.75, 45.05, 4.05, 4.40),
        "randos": [
            {"nom": "Mont Mézenc", "titres": ["Mont Mézenc"],
             "altitude": 1753, "depart": "Croix de Boutières (≈ 1508 m)",
             "depart_alt": 1508,
             "duree": "≈ 2 h aller-retour",
             "voie": "Toit du Velay-Vivarais entre Loire et Rhône — "
                     "panorama du Mont-Blanc au Ventoux par temps clair.",
             "osm": {"noms": ["Croix de Boutières",
                              "Col de la Croix de Boutières"], "rayon": 3500}},
            {"nom": "Mont Gerbier de Jonc", "titres": ["Mont Gerbier de Jonc"],
             "altitude": 1551, "depart": "Parking au pied du mont (≈ 1417 m)",
             "depart_alt": 1417,
             "duree": "≈ 1 h aller-retour",
             "voie": "Le pain de sucre phonolitique des sources de la "
                     "Loire — sentier raide aménagé jusqu'au sommet.",
             "osm": {"parking": True, "rayon": 2000}},
        ],
    },
}
