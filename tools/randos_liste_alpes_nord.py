# -*- coding: utf-8 -*-
"""Liste éditoriale des randonnées emblématiques — ALPES DU NORD.

Sélection qualitative (règle « qualité avant quantité ») : sommets majeurs à
voie normale de RANDONNÉE documentée, objectifs célèbres. Article Wikipédia
obligatoire (filtre de notoriété, appliqué par recolter_randonnees_france.py).
Écartés d'office : sommets d'alpinisme/escalade (Mont Aiguille, Grande Casse,
Pierra Menta…), objectifs homonymes d'un point existant (lacs déjà en
catégorie « lac » : Lac Blanc, lacs Robert…), sommets à route carrossable
jusqu'au sommet (Revard, Semnoz, Signal de Bisanne…).

Champs : nom, titres (candidats Wikipédia, le premier trouvé gagne),
altitude (croisée avec l'article), depart (+depart_alt → D+ estimé),
duree (seulement si bien établie), voie (1 phrase), osm (spécification du
départ pour le routage de recolter_traces_randos.py : noms OSM candidats ou
parking le plus proche + rayon de recherche autour du sommet, en m).
"""

MASSIFS = {
    "Vercors": {
        "bbox": (44.70, 45.35, 5.20, 5.90),
        "randos": [
            {"nom": "Grand Veymont", "titres": ["Grand Veymont"],
             "altitude": 2341, "depart": "Gresse-en-Vercors (≈ 1210 m)",
             "depart_alt": 1210,
             "voie": "Voie normale par le pas de la Ville puis la crête — "
                     "point culminant du Vercors, face au mont Aiguille.",
             "osm": {"noms": ["Gresse-en-Vercors"], "rayon": 7000}},
            {"nom": "Le Moucherotte", "titres": ["Le Moucherotte", "Moucherotte"],
             "altitude": 1901,
             "depart": "Saint-Nizier-du-Moucherotte (≈ 1160 m)", "depart_alt": 1160,
             "duree": "≈ 4 h aller-retour",
             "voie": "Montée par le sentier des Trois Pucelles ou le GR91 — "
                     "balcon spectaculaire au-dessus de Grenoble.",
             "osm": {"noms": ["Saint-Nizier-du-Moucherotte"], "rayon": 4500}},
            {"nom": "Pic Saint-Michel", "titres": ["Pic Saint-Michel"],
             "altitude": 1966, "depart": "Parking des Allières, Lans-en-Vercors (≈ 1420 m)",
             "depart_alt": 1420,
             "voie": "Voie normale par le col de l'Arc — vue sur toute la "
                     "chaîne de Belledonne.",
             "osm": {"noms": ["Les Allières"], "rayon": 5500}},
            {"nom": "Grande Moucherolle", "titres": ["Grande Moucherolle"],
             "altitude": 2284, "depart": "Corrençon-en-Vercors (≈ 1110 m)",
             "depart_alt": 1110,
             "voie": "Longue montée par la Combe de Fer et le col des Deux "
                     "Sœurs — deuxième sommet du massif.",
             "osm": {"noms": ["Corrençon-en-Vercors"], "rayon": 7500}},
            {"nom": "Roc Cornafion", "titres": ["Roc Cornafion", "Cornafion"],
             "altitude": 2049, "depart": "Col de l'Arzelier (≈ 1150 m)",
             "depart_alt": 1150,
             "voie": "Montée en forêt puis en crête depuis le col de "
                     "l'Arzelier — belvédère sur le Trièves.",
             "osm": {"noms": ["Col de l'Arzelier"], "rayon": 5500}},
            # Glandasse : article sans coordonnées → écartée (dry-run 10/07).
        ],
    },
    "Belledonne": {
        "bbox": (45.00, 45.55, 5.80, 6.30),
        "randos": [
            {"nom": "Croix de Belledonne", "titres": ["Croix de Belledonne"],
             "altitude": 2926, "depart": "Freydières, Revel (≈ 1160 m)",
             "depart_alt": 1160,
             "voie": "Grande course de randonnée par le refuge de la Pra et "
                     "le lac du Doménon — panorama immense.",
             "osm": {"noms": ["Freydières"], "rayon": 8500}},
            {"nom": "Croix de Chamrousse", "titres": ["Croix de Chamrousse"],
             "altitude": 2253, "depart": "Chamrousse 1650 (Le Recoin)",
             "depart_alt": 1650,
             "voie": "Montée par les pistes ou le sentier des crêtes — vue "
                     "sur Grenoble et les lacs Robert.",
             "osm": {"noms": ["Le Recoin", "Chamrousse 1650", "Chamrousse"],
                     "rayon": 4500}},
            # Grand Colon : pas d'article Wikipédia dédié → écarté.
            {"nom": "Grande Lance de Domène", "titres": ["Grande Lance de Domène"],
             "altitude": 2790, "depart": "Freydières, Revel (≈ 1160 m)",
             "depart_alt": 1160,
             "voie": "Par le refuge de la Pra puis la voie normale sud — "
                     "randonnée exigeante et minérale.",
             "osm": {"noms": ["Freydières"], "rayon": 8000}},
            {"nom": "Pic de la Belle Étoile", "titres": ["Pic de la Belle Étoile"],
             "altitude": 2718, "depart": "Le Pleynet, Les Sept-Laux (≈ 1450 m)",
             "depart_alt": 1450,
             "voie": "Montée par les lacs des Sept-Laux puis la crête — "
                     "l'un des plus beaux belvédères du massif.",
             "osm": {"noms": ["Le Pleynet"], "rayon": 6500}},
            {"nom": "Rocher Blanc", "titres": ["Rocher Blanc (Belledonne)",
                                               "Rocher Blanc"],
             "altitude": 2928, "depart": "Fond de France (≈ 1090 m)",
             "depart_alt": 1090,
             "voie": "Longue voie normale par les lacs des Sept-Laux — "
                     "sommet débonnaire le plus haut du nord de Belledonne.",
             "osm": {"noms": ["Fond de France"], "rayon": 8500}},
        ],
    },
    "Bauges": {
        "bbox": (45.55, 45.95, 5.90, 6.40),
        "randos": [
            {"nom": "Trélod", "titres": ["Trélod", "Le Trélod"],
             "altitude": 2181, "depart": "Col de Chérel (≈ 1495 m)",
             "depart_alt": 1495,
             "voie": "Voie normale par l'arête sud-ouest depuis le col de "
                     "Chérel, au cœur de la réserve des Bauges.",
             "osm": {"noms": ["Col de Chérel"], "rayon": 5500}},
            {"nom": "Pointe d'Arcalod", "titres": ["Pointe d'Arcalod", "Arcalod"],
             "altitude": 2217, "depart": "Col de Chérel (≈ 1495 m)",
             "depart_alt": 1495,
             "voie": "Point culminant des Bauges — voie normale raide, "
                     "dernier ressaut rocheux exigeant (passages câblés).",
             "osm": {"noms": ["Col de Chérel"], "rayon": 5000}},
            {"nom": "Pointe de la Sambuy", "titres": ["Pointe de la Sambuy",
                                                      "La Sambuy"],
             "altitude": 2198, "depart": "Station de la Sambuy, Seythenex (≈ 1150 m)",
             "depart_alt": 1150,
             "voie": "Voie normale par le vallon de la Sambuy — vue "
                     "plongeante sur le lac d'Annecy.",
             "osm": {"noms": ["La Sambuy", "Seythenex"], "rayon": 7000}},
            {"nom": "Dent d'Arclusaz", "titres": ["Dent d'Arclusaz"],
             "altitude": 2041, "depart": "Col du Frêne, École (≈ 950 m)",
             "depart_alt": 950,
             "voie": "Montée par les alpages depuis le col du Frêne — la "
                     "dent emblématique de la combe de Savoie.",
             "osm": {"noms": ["Col du Frêne"], "rayon": 6000}},
            {"nom": "Pointe de la Galoppaz", "titres": ["Pointe de la Galoppaz"],
             "altitude": 1680, "depart": "Col de Plainpalais (≈ 1170 m)",
             "depart_alt": 1170,
             "voie": "Boucle facile en forêt puis en alpage — belvédère "
                     "familial sur les Bauges et Belledonne.",
             "osm": {"noms": ["Col de Plainpalais"], "rayon": 5500}},
            {"nom": "Mont Margériaz", "titres": ["Mont Margériaz", "Margériaz"],
             "altitude": 1845, "depart": "Aillon-le-Jeune (≈ 1000 m)",
             "depart_alt": 1000,
             "voie": "Montée par les pistes ou la Féclaz — long plateau "
                     "calcaire criblé de lapiaz et de tannes.",
             "osm": {"noms": ["Aillon-le-Jeune"], "rayon": 6500}},
            {"nom": "Croix du Nivolet", "titres": ["Croix du Nivolet"],
             "altitude": 1547, "depart": "La Féclaz (≈ 1330 m)", "depart_alt": 1330,
             "duree": "≈ 3 h aller-retour",
             "voie": "Classique depuis La Féclaz par le plateau — la grande "
                     "croix qui domine Chambéry.",
             "osm": {"noms": ["La Féclaz"], "rayon": 5500}},
        ],
    },
    "Aravis-Bornes": {
        "bbox": (45.75, 46.20, 6.00, 6.65),
        "randos": [
            {"nom": "La Tournette", "titres": ["La Tournette"],
             "altitude": 2350, "depart": "Col de la Forclaz de Montmin (≈ 1150 m)",
             "depart_alt": 1150,
             "duree": "≈ 6 h aller-retour",
             "voie": "Voie normale par le chalet de l'Aulp et le refuge — "
                     "LE sommet du lac d'Annecy, main courante au fauteuil.",
             "osm": {"noms": ["Col de la Forclaz", "Chalet de l'Aulp"],
                     "rayon": 5000}},
            {"nom": "Pointe Percée", "titres": ["Pointe Percée"],
             "altitude": 2750, "depart": "Col des Annes (≈ 1720 m)",
             "depart_alt": 1720,
             "voie": "Point culminant des Aravis par le refuge de Gramusset — "
                     "final rocheux exigeant (cheminées, II).",
             "osm": {"noms": ["Col des Annes"], "rayon": 5500}},
            {"nom": "Mont Charvin",
             "titres": ["Mont Charvin (chaîne des Aravis)"],
             "altitude": 2409, "depart": "Le Bouchet-Mont-Charvin (≈ 950 m)",
             "depart_alt": 950,
             "voie": "Voie normale par le lac du Charvin — pyramide "
                     "solitaire entre Aravis et val d'Arly.",
             "osm": {"noms": ["Le Bouchet"], "rayon": 7500}},
            # Trou de la Mouche : pas d'article Wikipédia dédié → écarté.
            {"nom": "Pic de Jallouvre", "titres": ["Pic de Jallouvre"],
             "altitude": 2408, "depart": "Col de la Colombière (≈ 1613 m)",
             "depart_alt": 1613,
             "voie": "Voie normale par le lac de Peyre — sentinelle calcaire "
                     "de la chaîne du Bargy.",
             "osm": {"noms": ["Col de la Colombière"], "rayon": 5000}},
            {"nom": "Parmelan", "titres": ["Parmelan"],
             "altitude": 1856, "depart": "Parking de l'Anglettaz, Villaz (≈ 1220 m)",
             "depart_alt": 1220,
             "duree": "≈ 3 h 30 aller-retour",
             "voie": "Grande classique d'Annecy par le Grand ou le Petit "
                     "Montoir, refuge et lapiaz au sommet.",
             "osm": {"noms": ["Anglettaz", "L'Anglettaz", "Villaz"], "rayon": 7000}},
            {"nom": "Le Môle", "titres": ["Le Môle"],
             "altitude": 1863, "depart": "Bovère, Saint-Jean-de-Tholome (≈ 1080 m)",
             "depart_alt": 1080,
             "voie": "Cône herbeux isolé entre Arve et Giffre — panorama "
                     "réputé sur le Mont-Blanc et le Léman.",
             "osm": {"noms": ["Bovère", "Saint-Jean-de-Tholome"], "rayon": 6000}},
            {"nom": "Pointe d'Andey", "titres": ["Pointe d'Andey"],
             "altitude": 1877, "depart": "Plateau de Solaison, Brizon (≈ 1500 m)",
             "depart_alt": 1500,
             "voie": "Courte montée depuis le plateau de Solaison — balcon "
                     "sur la vallée de l'Arve et le Bargy.",
             "osm": {"noms": ["Solaison"], "rayon": 4000}},
        ],
    },
    "Beaufortain": {
        "bbox": (45.55, 45.95, 6.30, 6.90),
        "randos": [
            {"nom": "Grand Mont", "titres": ["Grand Mont (massif du Beaufortain)",
                                             "Grand Mont", "Le Grand Mont"],
             "altitude": 2686, "depart": "Arêches (≈ 1080 m)", "depart_alt": 1080,
             "voie": "La grande classique d'Arêches — voie normale par le "
                     "lac des Fées, vue sur le Mont-Blanc.",
             "osm": {"noms": ["Arêches"], "rayon": 7000}},
            {"nom": "Mont Mirantin", "titres": ["Mont Mirantin", "Mirantin"],
             "altitude": 2460, "depart": "Arêches (≈ 1080 m)", "depart_alt": 1080,
             "voie": "Voie normale par les chalets du Lac et l'arête — "
                     "sommet pyramidal au-dessus d'Albertville.",
             "osm": {"noms": ["Arêches"], "rayon": 6500}},
            # Roc du Vent : pas d'article Wikipédia dédié → écarté.
            {"nom": "Col de la Croix du Bonhomme",
             "titres": ["Col de la Croix du Bonhomme"],
             "altitude": 2479, "depart": "Les Chapieux (≈ 1550 m)", "depart_alt": 1550,
             "voie": "Étape mythique du Tour du Mont-Blanc et du GR5, entre "
                     "Beaufortain et Tarentaise.",
             "osm": {"noms": ["Les Chapieux"], "rayon": 6500}},
            {"nom": "Aiguille Croche", "titres": ["Aiguille Croche"],
             "altitude": 2487, "depart": "Col du Joly (≈ 1989 m)", "depart_alt": 1989,
             "voie": "Courte montée en crête depuis le col du Joly — l'un "
                     "des panoramas les plus réputés des Alpes du Nord.",
             "osm": {"noms": ["Col du Joly"], "rayon": 4000}},
            {"nom": "Mont Joly", "titres": ["Mont Joly"],
             "altitude": 2525, "depart": "Le Bettex, Saint-Gervais (≈ 1400 m)",
             "depart_alt": 1400,
             "voie": "Par le mont Géroux et la crête — belvédère célèbre "
                     "face au massif du Mont-Blanc.",
             "osm": {"noms": ["Le Bettex"], "rayon": 7000}},
        ],
    },
    "Vanoise": {
        "bbox": (45.20, 45.80, 6.50, 7.15),
        "randos": [
            {"nom": "Col de la Vanoise", "titres": ["Col de la Vanoise"],
             "altitude": 2517, "depart": "Pralognan-la-Vanoise (≈ 1420 m)",
             "depart_alt": 1420,
             "duree": "≈ 5 h aller-retour",
             "voie": "Montée classique par le lac des Vaches — le grand "
                     "passage historique de la Vanoise, face à la Grande Casse.",
             "osm": {"noms": ["Pralognan-la-Vanoise"], "rayon": 7000}},
            # Petit Mont Blanc : pas d'article fr avec coordonnées → écarté.
            {"nom": "Mont Jovet", "titres": ["Mont Jovet"],
             "altitude": 2558, "depart": "La Plagne (≈ 1970 m)", "depart_alt": 1970,
             "voie": "Montée en alpage par le refuge du Mont Jovet — table "
                     "d'orientation et panorama à 360°.",
             "osm": {"noms": ["Plagne Centre", "La Plagne"], "rayon": 7000}},
            {"nom": "Col d'Aussois", "titres": ["Col d'Aussois"],
             "altitude": 2914, "depart": "Barrage de Plan d'Amont, Aussois (≈ 2080 m)",
             "depart_alt": 2080,
             "voie": "Montée par le refuge du Fond d'Aussois — le plus haut "
                     "col piéton de Vanoise, sous la pointe de l'Observatoire.",
             "osm": {"noms": ["Plan d'Amont", "Barrage de Plan d'Amont"],
                     "rayon": 6000}},
            {"nom": "Pointe de la Grande Sassière",
             "titres": ["Pointe de la Grande Sassière", "Grande Sassière"],
             "altitude": 3747, "depart": "Barrage du Saut, Val-d'Isère (≈ 2280 m)",
             "depart_alt": 2280,
             "voie": "Voie normale en sentier cairné — l'un des plus hauts "
                     "sommets des Alpes accessibles en randonnée exigeante.",
             "osm": {"noms": ["Le Saut", "Barrage du Saut"], "rayon": 6500}},
        ],
    },
    "Mont-Blanc": {
        "bbox": (45.75, 46.15, 6.60, 7.10),
        "randos": [
            {"nom": "Le Brévent", "titres": ["Brévent", "Le Brévent"],
             "altitude": 2525, "depart": "Les Houches (≈ 1000 m)", "depart_alt": 1000,
             "voie": "Montée par Bellachat et son refuge — LE balcon face "
                     "au Mont-Blanc, au cœur des Aiguilles Rouges.",
             "osm": {"noms": ["Les Houches"], "rayon": 7000}},
            {"nom": "Mont Buet", "titres": ["Mont Buet"],
             "altitude": 3096, "depart": "Le Buet, Vallorcine (≈ 1330 m)",
             "depart_alt": 1330,
             "duree": "≈ 9 h aller-retour",
             "voie": "Le « Mont-Blanc des dames » par la Pierre à Bérard — "
                     "très longue voie normale, panorama exceptionnel.",
             "osm": {"noms": ["Le Buet"], "rayon": 9000}},
            # La Jonction : l'article homonyme est à Genève (confluent Rhône-
            # Arve) → écartée, pas d'article dédié au site de Chamonix.
            {"nom": "Le Prarion", "titres": ["Le Prarion", "Prarion"],
             "altitude": 1969, "depart": "Col de Voza (≈ 1653 m)", "depart_alt": 1653,
             "voie": "Crête douce au-dessus du col de Voza — vue sur toute "
                     "la vallée de Chamonix et les dômes de Miage.",
             "osm": {"noms": ["Col de Voza"], "rayon": 4000}},
            # Aiguillette des Posettes : pas d'article Wikipédia → écartée.
            {"nom": "Pointe Noire de Pormenaz",
             "titres": ["Pointe Noire de Pormenaz", "Pormenaz"],
             "altitude": 2323, "depart": "Plaine-Joux, Passy (≈ 1360 m)",
             "depart_alt": 1360,
             "voie": "Par le chalet du Souay et le lac de Pormenaz — "
                     "réserve naturelle sauvage face aux Fiz.",
             "osm": {"noms": ["Plaine-Joux", "Plaine Joux"], "rayon": 5500}},
        ],
    },
}
