# -*- coding: utf-8 -*-
"""Le genre des noms, que le dictionnaire ne dit pas.

`morphologie.py` lit tout ce que le dictionnaire Hunspell sait : la personne,
le nombre, et le genre — mais seulement celui des paradigmes a deux genres,
« chat » / « chatte ». Pour « voiture », « cheval » ou « porte », il n'en dit
rien : ces mots n'ont qu'une forme par nombre, et rien ne trahit leur genre.

Cela ne manquait a personne tant que les accords se faisaient au masculin par
defaut. Mais « des voitures blanc » devenait « des voitures blancs » : non pas
une faute laissee, une faute **ecrite**. C'est la categorie que ce projet
refuse.

Trois reponses, dans l'ordre ou on les essaie.

**1. Ce que la phrase dit elle-meme.** Un determinant, un adjectif deja
accorde : « une belle maison blanc » porte deux fois le feminin avant d'en
avoir besoin une troisieme. Cette source-la est exacte et ne coute rien.

**2. La terminaison.** Le francais n'est pas avare : « -tion », « -ité »,
« -esse » sont feminins sans exception, « -ment », « -isme », « -oir »
masculins de meme. Les suffixes retenus ici le sont pour cette raison, et
leurs rares exceptions sont nommees une a une.

**3. Une liste.** Ce qui reste, ce sont les noms courts et courants, ceux
qu'aucune regle ne couvre et que tout le monde ecrit : « eau », « nuit »,
« main », « jour ». Ils sont ici, ecrits a la main.

**4. Rien.** Et alors on se tait. Un nom dont on ignore le genre ne fait pas
accorder d'adjectif dont le masculin et le feminin different — « des trucs
blanc » reste tel quel plutot que de devenir faux. C'est aussi la reponse
pour les mots qui changent de sens avec leur genre — « le livre » et « la
livre », « le poste » et « la poste » —, qui n'ont rien a faire dans une
table a une colonne.
"""

from __future__ import annotations

MASCULIN = "m"
FEMININ = "f"

# ---------------------------------------------------------------------------
# Les terminaisons
#
# Chacune est suivie de ses exceptions, ce qui est la seule facon de la rendre
# sure. Une terminaison dont on ne sait pas nommer les exceptions n'a rien a
# faire ici : « -eur » est feminin dans « couleur » et masculin dans
# « moteur », et n'y figure donc pas.
# ---------------------------------------------------------------------------

TERMINAISONS = (
    # -- feminines
    ("tion", FEMININ, ()),          # nation, question, attention
    ("sion", FEMININ, ()),          # passion, décision, occasion
    ("xion", FEMININ, ()),          # connexion, réflexion
    ("nion", FEMININ, ()),          # réunion, opinion, communion
    ("ité", FEMININ, ()),           # qualité, activité, unité
    ("iété", FEMININ, ()),          # société, propriété, variété
    ("esse", FEMININ, ()),          # vitesse, richesse, jeunesse
    ("ette", FEMININ, ("squelette", "quintette", "tabouret")),
    ("ance", FEMININ, ()),          # chance, distance, ambiance
    ("ence", FEMININ, ("silence",)),
    ("aison", FEMININ, ()),         # maison, raison, saison
    ("sson", FEMININ, ("poisson", "buisson", "caisson", "paillasson",
                       "hérisson", "polisson", "nourrisson")),
    ("ure", FEMININ, ("murmure", "augure", "parjure", "mercure", "azur")),
    ("ude", FEMININ, ("prélude", "interlude")),
    ("ade", FEMININ, ("grade", "stade", "jade", "nomade")),
    ("euse", FEMININ, ()),          # vendeuse, chanteuse
    ("ière", FEMININ, ("derrière", "cimetière")),
    ("erie", FEMININ, ()),          # boulangerie, mairie
    ("ie", FEMININ, ("génie", "incendie", "parapluie", "sosie", "zombie",
                     "messie", "colibri")),

    # -- masculines
    ("ment", MASCULIN, ("jument",)),
    ("isme", MASCULIN, ()),         # tourisme, réalisme
    ("oir", MASCULIN, ()),          # miroir, couloir, devoir
    ("eau", MASCULIN, ("eau", "peau")),
    ("al", MASCULIN, ()),           # cheval, journal, hôpital
    ("teur", MASCULIN, ()),         # ordinateur, moteur, acteur
    ("phone", MASCULIN, ()),        # téléphone, micro
    ("scope", MASCULIN, ()),        # microscope
    ("ier", MASCULIN, ()),          # papier, cahier, quartier
    ("age", MASCULIN, ("page", "image", "plage", "cage", "rage", "nage",
                       "cage", "ombrage")),
)

# ---------------------------------------------------------------------------
# La liste
#
# Les noms courants que ni la phrase ni la terminaison ne couvrent. Ils sont
# courts, tres employes, et sans regle : c'est exactement le genre de mots
# qu'il faut ecrire a la main.
# ---------------------------------------------------------------------------

_FEMININS = """
eau peau main fin faim nuit voix fois part paix mer terre lune mort dent
soif toux croix noix voie joie loi foi clé clef cle chair chance
voiture porte table chaise fleur route ville place page chose personne
école classe famille mère soeur sœur fille femme dame amie copine
idée année semaine heure minute seconde journée soirée matinée
guerre armée police banque gare église rue avenue piste
jambe tête bouche langue gorge joue lèvre épaule hanche
maison chambre cuisine salle fenêtre cave cour
bière boisson soupe salade viande pomme poire fraise cerise banane
lettre carte photo image affiche note liste fiche facture
faute erreur peur colère honte tristesse
couleur chaleur douleur valeur odeur saveur
phrase question réponse parole
musique chanson danse fête vacance sortie
histoire vie envie partie entrée montée descente
gauche droite haut moitié portion
vitesse force puissance énergie
équipe bande foule
date durée
autoroute
étoile planète île plage
crainte
affaires courses vacances toilettes
""".split()

_MASCULINS = """
jour soir matin midi minuit an mois moment temps instant
homme garçon fils frère père copain ami mari monsieur
travail boulot bureau métier emploi salaire argent prix
cahier stylo papier dossier fichier document texte mot
pays monde ciel soleil vent feu bois fer or
chemin pont mur toit sol plafond coin bord
pied bras doigt dos ventre coeur cœur nez oeil œil cheveu genou
chien chat cheval oiseau poisson
pain fromage gâteau plat repas café thé vin jus
train bus métro avion bateau vélo camion moteur
film jeu sport match but point score
nom prénom numéro code titre sujet
problème souci risque danger effort
groupe ensemble reste milieu centre
siècle
gens yeux cheveux ciseaux travaux environs alentours
""".split()

GENRES: dict[str, str] = {}
for _mot in _FEMININS:
    GENRES[_mot] = FEMININ
for _mot in _MASCULINS:
    GENRES[_mot] = MASCULIN
del _mot

# Les exceptions des terminaisons sont du genre inverse : on les range ici
# pour que la recherche par terminaison n'ait rien a refaire.
_EXCEPTIONS: dict[str, str] = {}
for _fin, _genre, _exceptions in TERMINAISONS:
    _inverse = MASCULIN if _genre == FEMININ else FEMININ
    for _exception in _exceptions:
        _EXCEPTIONS[_exception] = _inverse
del _fin, _genre, _exceptions, _inverse, _exception


def genre(nom: str) -> str | None:
    """« voiture » -> « f », « cheval » -> « m », « truc » -> None.

    La liste passe avant les terminaisons : « page » y figure comme feminin,
    et n'a pas a se defendre contre « -age ».
    """
    minuscule = (nom or "").lower()
    if not minuscule:
        return None
    if minuscule in GENRES:
        return GENRES[minuscule]
    if minuscule in _EXCEPTIONS:
        return _EXCEPTIONS[minuscule]
    for fin, valeur, _exceptions in TERMINAISONS:
        if minuscule.endswith(fin) and len(minuscule) > len(fin):
            return valeur
    return None
