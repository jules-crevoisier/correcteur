# -*- coding: utf-8 -*-
"""Regles de grammaire contextuelles.

Le lexique corrige les mots pris un a un. Il ne voit donc pas les fautes les
plus frequentes du francais, celles ou les deux graphies existent :

    je sais pas si sa va      « sa » est un mot, « ça » aussi
    ils on mangé              « on » est un mot, « ont » aussi
    j'ai manger               « manger » est un mot, « mangé » aussi

Ce module regarde les mots voisins pour trancher. Chaque regle est une petite
fonction qui repond « voila ce qu'il faut ecrire ici » ou ne repond rien.

Deux principes, les memes que partout ailleurs dans le projet :

1. On ne corrige jamais le registre. Aucune regle n'ajoute le « ne » d'une
   negation, ne remplace « ça » par « cela » ni « y a » par « il y a ».
2. Devant le moindre doute, on se tait. Une regle ne se declenche que sur un
   contexte ou l'autre lecture est impossible : « ils on » est toujours une
   faute, « elle et contente » aussi. Les cas ambigus — « il a la flemme »
   contre « je vais a la gare » — sont laisses tels quels.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable

from .lexique import ACCENTUEES, accentue as accentue_mot, sans_accents
from .morphologie import (
    CONJUGUES, NOMS_PLURIELS, PARTICIPES, PARTICIPES_MASCULINS, PLURIELS,
    Morphologie,
)
from . import confusions
from .politique import PARLE, SOUTENU

# ---------------------------------------------------------------------------
# Decoupage en mots
# ---------------------------------------------------------------------------

# Un mot : des lettres ou des chiffres, avec ses apostrophes internes
# (« j'ai », « aujourd'hui ») et son eventuelle apostrophe finale (« qu' »).
_MOT = re.compile(r"[^\W_]+(?:['’][^\W_]+)*['’]?", re.UNICODE)

# Elisions placees devant un mot. Les isoler permet de traiter « j'ai » comme
# l'auxiliaire « ai », et « qu'il » comme le pronom « il ».
CLITIQUES = (
    "aujourd'", "jusqu'", "lorsqu'", "puisqu'", "quoiqu'", "presqu'", "entr'",
    "qu'", "c'", "ç'", "d'", "j'", "l'", "m'", "n'", "s'", "t'",
)


@dataclass(frozen=True)
class Jeton:
    texte: str
    debut: int
    fin: int


def decouper(texte: str) -> list[Jeton]:
    return [Jeton(m.group(), m.start(), m.end()) for m in _MOT.finditer(texte)]


def separer_clitique(mot: str) -> tuple[str, str]:
    """« c'est » -> (« c' », « est »). « bonjour » -> (« », « bonjour »)."""
    minuscule = mot.lower().replace("’", "'")
    for clitique in CLITIQUES:
        if minuscule.startswith(clitique) and len(minuscule) > len(clitique):
            # « aujourd'hui » n'est pas une elision : son noyau n'est pas un mot.
            if clitique == "aujourd'":
                return "", mot
            return mot[: len(clitique)], mot[len(clitique):]
    return "", mot


# ---------------------------------------------------------------------------
# Vocabulaire des regles
# ---------------------------------------------------------------------------

PRONOMS_SUJETS = {"je", "tu", "il", "elle", "on", "nous", "vous", "ils", "elles"}

# Pronoms qui s'intercalent entre le sujet et le verbe. Le « ne » se place
# devant eux, pas devant le verbe : « il n'y a pas », jamais « il y n'a pas ».
PRONOMS_INTERCALES = {"me", "te", "se", "le", "la", "les", "lui", "leur",
                      "y", "en", "nous", "vous"}

# Sujets a la 3e personne du singulier : devant eux, « et » est un « est ».
# Compares sans leurs accents : a la premiere passe, « ça » peut encore
# s'ecrire « ca », et le sujet ne doit pas passer inapercu pour autant.
SUJETS_SINGULIER = {
    "il", "elle", "on", "ça", "ce", "qui", "celui", "celle", "chacun",
    "quelqu'un", "personne", "tout", "ceci", "cela",
}

SUJETS_SINGULIER_NUS = {sans_accents(mot) for mot in SUJETS_SINGULIER}

PRONOMS_PLURIEL = {"ils", "elles"}

# Auxiliaires : ce qui les suit est un participe, jamais un infinitif.
# « été » en est volontairement absent : « j'ai été manger » est correct.
AUXILIAIRES = {
    "ai", "as", "a", "avons", "avez", "ont",
    "avais", "avait", "avions", "aviez", "avaient",
    "aurai", "auras", "aura", "aurons", "aurez", "auront",
    "aurais", "aurait", "aurions", "auriez", "auraient",
    "suis", "es", "est", "sommes", "êtes", "sont",
    "étais", "était", "étions", "étiez", "étaient",
    "serai", "seras", "sera", "serons", "serez", "seront",
    "serais", "serait", "serions", "seriez", "seraient",
}

# Semi-auxiliaires et prepositions : ce qui les suit est un infinitif,
# jamais un participe.
SEMI_AUXILIAIRES = {
    "vais", "vas", "va", "allons", "allez", "vont",
    "peux", "peut", "pouvons", "pouvez", "peuvent", "pourrais", "pourrait",
    "dois", "doit", "devons", "devez", "doivent", "devrais", "devrait",
    "veux", "veut", "voulons", "voulez", "veulent", "voudrais", "voudrait",
    "faut", "faudrait", "sais", "savons", "savez", "savent",
    "aime", "aimes", "aimons", "aimez", "aiment", "adore", "adores",
    "déteste", "détestes", "préfère", "préfères", "espère", "espères",
    "essaie", "essaies", "essaye", "compte", "comptes", "ose", "oses",
    "viens", "vient", "venons", "venez", "viennent",
    "sans", "pour",
}

# Participes irreguliers frequents, que leur terminaison ne trahit pas.
# Adverbes qui se glissent entre l'auxiliaire et le participe :
# « elle a beaucoup travaillé ».
ADVERBES_INTERCALES = {
    "beaucoup", "bien", "trop", "peu", "déjà", "jamais", "toujours", "encore",
    "vraiment", "presque", "enfin", "souvent", "rarement", "tellement",
    "même", "aussi", "pas", "plus", "rien", "tout",
}

PARTICIPES_IRREGULIERS = {
    "dit", "fait", "mis", "pris", "vu", "su", "pu", "voulu", "dû", "eu",
    "été", "venu", "tenu", "reçu", "connu", "cru", "bu", "lu", "écrit",
    "ouvert", "offert", "mort", "né", "allé", "compris", "appris", "permis",
    "promis", "assis", "surpris", "rendu", "perdu", "vendu", "attendu",
    "entendu", "répondu", "descendu", "battu", "vécu", "couru", "sorti",
    "parti", "senti", "dormi", "servi", "suivi", "fini", "choisi", "réussi",
}

# Noms en « -é » que leur terminaison fait passer pour des participes.
NOMS_EN_E = {
    "côté", "été", "café", "thé", "marché", "pré", "degré", "carré",
    "résumé", "employé", "invité", "député", "comité", "canapé", "blé",
    "clé", "congé", "cliché", "supermarché", "musée", "lycée", "défilé",
    "abbé", "curé", "gré", "pavé", "fossé", "traité", "procédé", "aîné",
}

DETERMINANTS_PLURIELS = {
    "des", "ces", "mes", "tes", "ses", "nos", "vos", "leurs",
    "plusieurs", "quelques", "certains", "certaines", "différents", "divers",
}

# Ce qui ferme un membre de phrase. Le motif porte sur le *separateur* entre
# deux mots : une ponctuation, un retour a la ligne, une parenthese fermante.
#
# Il s'y trouvait un « $ », pour le dernier mot du texte. Or un separateur
# d'un seul espace satisfait « ^\s*$ » : tout mot suivi d'une espace passait
# donc pour une fin de phrase, et « c'est la vie » devenait « c'est là vie ».
# Le dernier mot est deja traite a part, juste en dessous.
FIN_DE_SEGMENT = re.compile(r"^\s*[.!?,;:…\n)\]»\"]")
DEBUT_DE_SEGMENT = re.compile(r"[.!?,;:…\n]")

# Mots qui ouvrent un membre de phrase sans en etre le sujet.
CHARNIERES = {"mais", "et", "ou", "donc", "car", "puis", "alors", "bref",
              "franchement", "honnêtement", "perso", "après", "enfin"}


# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Suggestion:
    """Un remplacement propose par une regle."""

    index: int        # premier jeton concerne
    portee: int       # nombre de jetons remplaces
    texte: str        # ce qu'il faut ecrire a la place
    regle: str
    message: str


Fonction = Callable[["Contexte", int], "str | tuple[str, int] | None"]


@dataclass(frozen=True)
class Regle:
    nom: str
    message: str
    fonction: Fonction
    # « tous » : la regle corrige une faute, quel que soit le ton.
    # « soutenu » : elle releve le registre, ce qui ne se fait que sur demande.
    registre: str = "tous"


REGLES: list[Regle] = []


def regle(nom: str, message: str, registre: str = "tous"):
    """Enregistre une regle. L'ordre de declaration est l'ordre d'application."""
    def decorateur(fonction: Fonction) -> Fonction:
        REGLES.append(Regle(nom, message, fonction, registre))
        return fonction
    return decorateur


class Contexte:
    """Le texte decoupe, plus les quelques services dont les regles ont besoin."""

    def __init__(self, texte: str, jetons: list[Jeton], lexique,
                 morphologie=None):
        self.texte = texte
        self.jetons = jetons
        self.lexique = lexique
        # Sans elle, les regles d'accord se taisent : une table vide ne
        # connait aucun mot, et `connait` est la premiere question qu'elles
        # posent.
        self.morphologie = (morphologie if morphologie is not None
                            else Morphologie(analyses=[], flexions=[]))

    # -- lecture des mots ---------------------------------------------------

    def mot(self, i: int) -> str:
        """Le jeton entier, en minuscules : « C'est » -> « c'est »."""
        if 0 <= i < len(self.jetons):
            return self.jetons[i].texte.lower().replace("’", "'")
        return ""

    def noyau(self, i: int) -> str:
        """Le jeton prive de son elision : « c'est » -> « est »."""
        return separer_clitique(self.mot(i))[1]

    def elision(self, i: int) -> str:
        """L'elision du jeton : « c'est » -> « c' »."""
        return separer_clitique(self.mot(i))[0]

    def brut(self, i: int) -> str:
        return self.jetons[i].texte if 0 <= i < len(self.jetons) else ""

    # -- lecture de ce qui separe les mots ----------------------------------

    def separateur(self, i: int) -> str:
        """Le texte entre le jeton i et le suivant."""
        if i + 1 >= len(self.jetons):
            return self.texte[self.jetons[i].fin:] if 0 <= i < len(self.jetons) else ""
        return self.texte[self.jetons[i].fin:self.jetons[i + 1].debut]

    def debut_de_segment(self, i: int) -> bool:
        """Le jeton i ouvre-t-il une phrase ou un membre de phrase ?"""
        if i <= 0:
            return True
        return bool(DEBUT_DE_SEGMENT.search(self.separateur(i - 1)))

    def fin_de_segment(self, i: int) -> bool:
        """Le jeton i termine-t-il une phrase ou un membre de phrase ?"""
        if i >= len(self.jetons) - 1:
            return True
        return bool(FIN_DE_SEGMENT.match(self.separateur(i)))

    # -- services lexicaux --------------------------------------------------

    def connait(self, mot: str) -> bool:
        return self.lexique.connait(mot)

    def est_participe(self, mot: str) -> bool:
        """« mangé », « fini », « pris » — mais pas « clé » ni « nuit »."""
        if mot in PARTICIPES_IRREGULIERS:
            return True
        if mot in NOMS_EN_E:
            return False
        for terminaison, infinitif in (("ées", "er"), ("ée", "er"), ("és", "er"),
                                       ("é", "er"), ("is", "ir"), ("i", "ir"),
                                       ("us", "re"), ("u", "re")):
            if mot.endswith(terminaison):
                radical = mot[: -len(terminaison)]
                if radical and self.connait(radical + infinitif):
                    return True
        return False


# Terminaisons du present et du participe des verbes du 1er groupe, de la
# plus longue a la plus courte : « mangeons » avant « mange ».
TERMINAISONS_PREMIER_GROUPE = ("ent", "ons", "ez", "ées", "és", "ée", "es",
                               "é", "e")


# Formes des verbes irreguliers les plus courants. Le dictionnaire en
# rattache certaines a un verbe du 1er groupe homographe — « sommes » a
# « sommer », « fait » a « faiter » — et la conjugaison automatique les
# abimerait : « nous sommes » deviendrait « nous sommons ».
FORMES_INTOUCHABLES = {
    "suis", "es", "est", "somme", "sommes", "êtes", "sont", "été",
    "étais", "était", "étions", "étiez", "étaient",
    "ai", "as", "a", "avons", "avez", "ont", "eu",
    "avais", "avait", "avions", "aviez", "avaient",
    "vais", "vas", "va", "allons", "allez", "vont",
    "fais", "fait", "faisons", "faites", "font", "faisais", "faisait",
    "dis", "dit", "disons", "dites", "disent",
    "peux", "peut", "pouvons", "pouvez", "peuvent",
    "veux", "veut", "voulons", "voulez", "veulent",
    "dois", "doit", "devons", "devez", "doivent",
    "sais", "sait", "savons", "savez", "savent",
    "vois", "voit", "voyons", "voyez", "voient",
    "viens", "vient", "venons", "venez", "viennent",
    "prends", "prend", "prenons", "prenez", "prennent",
    "mets", "met", "mettons", "mettez", "mettent",
    "sors", "sort", "sortons", "sortez", "sortent",
    "pars", "part", "partons", "partez", "partent",
    "lis", "lit", "lisons", "lisez", "lisent",
    "écris", "écrit", "écrivons", "écrivez", "écrivent",
}


def infinitif_premier_groupe(ctx: "Contexte", mot: str) -> str | None:
    """L'infinitif dont `mot` serait une forme, s'il est du 1er groupe.

    « mange », « mangeons », « mangé » -> « manger ». Le dictionnaire tranche :
    on ne renvoie un infinitif que s'il existe vraiment, ce qui ecarte
    « rouge » (« rouger » n'existe pas) sans avoir a le savoir d'avance.
    """
    minuscule = mot.lower()
    if minuscule in FORMES_INTOUCHABLES:
        return None
    for terminaison in TERMINAISONS_PREMIER_GROUPE:
        if not minuscule.endswith(terminaison):
            continue
        radical = minuscule[: len(minuscule) - len(terminaison)]
        if len(radical) < 2:
            continue
        candidats = [radical + "er"]
        if radical.endswith(("e", "è")):
            # « mangeons » -> « manger », « achète » -> « acheter »
            candidats.append(radical[:-1] + "er")
        for candidat in candidats:
            if ctx.connait(candidat):
                return candidat
    return None


def conjuguer(ctx: "Contexte", infinitif: str, terminaison: str) -> str | None:
    """« manger » + « ons » -> « mangeons ». None si la forme n'existe pas.

    Les irregularites orthographiques du 1er groupe — le « e » de
    « mangeons », l'accent de « achète » — se resolvent en proposant les
    variantes au dictionnaire plutot qu'en les codant.
    """
    radical = infinitif[:-2]
    for candidat in (radical + terminaison,
                     radical + "e" + terminaison,
                     radical + "è" + terminaison):
        if ctx.connait(candidat) and _vaut_la_peine(ctx, candidat):
            return candidat
    return None


def _vaut_la_peine(ctx: "Contexte", candidat: str) -> bool:
    """La forme conjuguee est-elle employee par quelqu'un ?

    « les claviers telephone » : l'orthographe rend « téléphone » (797e mot
    du francais), puis l'accord le conjugue en « téléphonent » — une forme
    qui existe au dictionnaire mais que personne n'ecrit, et le nom devient
    un verbe. Une forme absente des cinquante mille mots les plus employes
    ne remplace pas un mot qui, lui, en fait partie.
    """
    from .lexique import RANG_INCONNU

    return ctx.lexique.rang(candidat) != RANG_INCONNU


def sujet_avant(ctx: "Contexte", i: int) -> str:
    """Le sujet du verbe en position i, pronom complement saute au besoin.

    « ils se parlent », « je me souviens » : entre le sujet et son verbe, un
    pronom s'intercale souvent. Le chercher un mot plus loin evite d'avoir a
    l'ecrire dans chaque regle.
    """
    precedent = ctx.noyau(i - 1)
    if precedent in PRONOMS_INTERCALES and ctx.noyau(i - 2) in PRONOMS_SUJETS:
        return ctx.noyau(i - 2)
    return precedent


def appliquer_casse(modele: str, mot: str) -> str:
    """Garde la majuscule du mot d'origine : « On » -> « Ont »."""
    if modele[:1].isupper():
        return mot[:1].upper() + mot[1:]
    return mot


# ---------------------------------------------------------------------------
# Les regles, dans leur ordre d'application
# ---------------------------------------------------------------------------

VERBES_APRES_CA = {
    "va", "vas", "vaut", "fait", "fera", "ferait", "marche", "marchera",
    "dépend", "dépendra", "suffit", "arrive", "arrivera", "existe", "veut",
    "peut", "pourrait", "doit", "sert", "change", "reste", "craint", "passe",
    "coûte", "coûtera", "ira", "irait", "sera", "serait", "était", "est",
    "donne", "rend", "commence", "finit", "prend", "tombe", "sent", "sonne",
    "ressemble", "aide", "gêne", "dérange", "regarde", "compte", "m'", "t'",
    "s'", "me", "te", "lui", "leur", "y", "en", "ne", "n'", "aurait", "a",
}


# Pronoms qui ne sont jamais le verbe attendu par les regles d'accord.
PRONOMS_COMPLEMENTS = {
    "me", "te", "se", "le", "la", "les", "lui", "leur", "y", "en", "ne",
    "que", "de", "ce", "une", "autre", "même", "pire",
}

# Formes de la 3e personne employees a tort avec « je » ou « tu ».
ACCORDS_SUJET = {
    "je": {"peut": "peux", "veut": "veux", "doit": "dois", "fait": "fais",
           "va": "vais", "a": "ai", "est": "suis", "sait": "sais",
           "dit": "dis", "prend": "prends", "met": "mets", "vient": "viens",
           "part": "pars", "sort": "sors", "vaut": "vaux", "voit": "vois"},
    "tu": {"peut": "peux", "veut": "veux", "doit": "dois", "fait": "fais",
           "va": "vas", "a": "as", "est": "es", "sait": "sais",
           "dit": "dis", "prend": "prends", "met": "mets", "vient": "viens",
           "part": "pars", "sort": "sors", "vaut": "vaux", "voit": "vois"},
}


@regle("ACCORD_SUJET_VERBE",
       "le verbe s'accorde avec « je » ou « tu »")
def _accord_sujet_verbe(ctx: Contexte, i: int):
    formes = ACCORDS_SUJET.get(sujet_avant(ctx, i))
    if formes is None:
        return None
    correcte = formes.get(ctx.mot(i))
    if correcte is None or ctx.elision(i):
        return None
    return appliquer_casse(ctx.brut(i), correcte)


@regle("ACCORD_JE_TU_S",
       "avec « je » ou « tu », le verbe se termine par « -s »")
def _accord_je_tu_s(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if sujet_avant(ctx, i) not in ("je", "tu") or ctx.elision(i):
        return None
    if mot in PRONOMS_COMPLEMENTS:
        return None
    if mot.endswith("d"):
        accorde = mot + "s"
    elif mot.endswith("t"):
        accorde = mot[:-1] + "s"
    elif not ctx.connait(mot) and mot not in MOTS_INVARIABLES:
        # « tu vien » : le mot n'existe pas, mais « viens » oui.
        accorde = mot + "s"
    else:
        return None
    if ctx.connait(accorde):
        return appliquer_casse(ctx.brut(i), accorde)
    return None


@regle("ACCORD_TU_S", "avec « tu », le verbe se termine par « -s »")
def _accord_tu_s(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if sujet_avant(ctx, i) != "tu" or ctx.elision(i):
        return None
    if not mot.endswith("e") or mot in PRONOMS_COMPLEMENTS:
        return None
    if ctx.connait(mot + "s"):
        return appliquer_casse(ctx.brut(i), mot + "s")
    return None


# Les auxiliaires ne se conjuguent pas comme les autres : « nous somme »
# doit devenir « nous sommes », surement pas « nous sommons ».
AUXILIAIRES_NOUS_VOUS = {
    "nous": {"somme": "sommes", "suis": "sommes", "est": "sommes",
             "sont": "sommes", "etes": "sommes", "été": "sommes",
             "ai": "avons", "as": "avons", "a": "avons", "ont": "avons",
             "vais": "allons", "va": "allons", "vas": "allons",
             "étais": "étions", "était": "étions", "étaient": "étions"},
    "vous": {"ete": "êtes", "été": "êtes", "etes": "êtes", "est": "êtes",
             "suis": "êtes", "sont": "êtes", "sommes": "êtes",
             "ai": "avez", "as": "avez", "a": "avez", "ont": "avez",
             "vais": "allez", "va": "allez", "vas": "allez",
             "étais": "étiez", "était": "étiez", "étaient": "étiez"},
}


@regle("ACCORD_AUXILIAIRE_NOUS_VOUS",
       "l'auxiliaire s'accorde avec « nous » ou « vous »")
def _accord_auxiliaire_nous_vous(ctx: Contexte, i: int):
    """« nous somme » -> « nous sommes », « vous ete » -> « vous êtes »."""
    formes = AUXILIAIRES_NOUS_VOUS.get(ctx.noyau(i - 1))
    if formes is None or ctx.elision(i):
        return None
    # « il nous a dit » : « nous » y est complement.
    if ctx.mot(i - 2) in PRONOMS_SUJETS:
        return None
    correcte = formes.get(ctx.mot(i))
    if correcte is None:
        return None
    return appliquer_casse(ctx.brut(i), correcte)


# Ce qu'un pronom sujet impose au verbe qui le suit. « ce » n'y figure pas :
# « ce sont des choses qui arrivent » est du francais, et le pronom y
# commande un pluriel.
PERSONNE_DU_SUJET = {
    "je": "1s", "tu": "2s",
    "il": "3s", "elle": "3s", "on": "3s", "ça": "3s",
    "nous": "1p", "vous": "2p",
    "ils": "3p", "elles": "3p",
}

# Devant un pronom, elles en font un sujet multiple : « lui et elle sont
# partis » se conjugue au pluriel, meme si le pronom, lui, est singulier.
COORDINATIONS = {"et", "ou", "ni"}


def accorder_le_verbe(ctx: "Contexte", i: int, personne: str) -> str | None:
    """La forme du verbe en position i qui porte cette personne.

    C'est la question que posaient, chacune a sa maniere et avec ses propres
    listes, une demi-douzaine de regles : celle-ci la pose une fois, au
    dictionnaire.

    Trois conditions, toutes necessaires :

    - le mot doit etre une forme **conjuguee** connue. Un nom, un participe,
      un infinitif ne s'accordent pas avec un sujet ;
    - il ne doit pas **deja** porter la personne demandee. « je pense » est
      juste, et « pense » est aussi une 3e personne : ne regarder que le
      sujet ferait corriger des phrases correctes ;
    - la forme de remplacement doit etre employee par quelqu'un. Le
      dictionnaire conjugue tout, y compris ce que personne n'ecrit.
    """
    mot = ctx.mot(i)
    if ctx.elision(i) or mot in PRONOMS_COMPLEMENTS or mot in MOTS_INVARIABLES:
        return None

    traits = ctx.morphologie.traits(mot)
    if not traits or not traits & CONJUGUES or personne in traits:
        return None

    accorde = ctx.morphologie.accorder(mot, personne)
    if accorde is None or accorde == mot or not _vaut_la_peine(ctx, accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("ACCORD_PRONOM_VERBE",
       "le verbe s'accorde avec son pronom sujet")
def _accord_pronom_verbe(ctx: Contexte, i: int):
    """« je peut » -> « je peux », « ils vient » -> « ils viennent ».

    Une seule regle pour les neuf pronoms et pour tous les verbes, la ou il
    fallait auparavant une table par personne et un modele de conjugaison
    par groupe — soit, en pratique, les verbes en « -er » et rien d'autre.
    """
    sujet = sujet_avant(ctx, i)
    personne = PERSONNE_DU_SUJET.get(sujet)
    if personne is None:
        return None
    # « il nous parle » : « nous » y est complement, le verbe a raison.
    if personne in ("1p", "2p") and ctx.mot(i - 2) in PRONOMS_SUJETS:
        return None
    # « lui et elle sont partis », « toi et moi on verra » : le sujet ne se
    # limite pas au pronom qu'on voit. La conjonction est juste avant lui,
    # ou un mot plus loin quand un pronom s'est glisse entre les deux.
    if (ctx.mot(i - 2) in COORDINATIONS or ctx.mot(i - 3) in COORDINATIONS):
        return None
    return accorder_le_verbe(ctx, i, personne)


@regle("ACCORD_NOUS_VOUS",
       "le verbe s'accorde avec « nous » ou « vous »")
def _accord_nous_vous(ctx: Contexte, i: int):
    """« nous mange » -> « nous mangeons », « vous parle » -> « vous parlez »."""
    terminaisons = {"nous": "ons", "vous": "ez"}
    terminaison = terminaisons.get(sujet_avant(ctx, i))
    if terminaison is None or ctx.elision(i):
        return None

    # « il nous parle » : « nous » y est complement, le verbe a raison.
    if ctx.mot(i - 2) in PRONOMS_SUJETS:
        return None

    mot = ctx.mot(i)
    if mot in PRONOMS_COMPLEMENTS or mot.endswith(terminaison):
        return None

    infinitif = infinitif_premier_groupe(ctx, mot)
    if infinitif is None:
        return None
    accorde = conjuguer(ctx, infinitif, terminaison)
    if accorde is None or accorde == mot:
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("ACCORD_IL_SINGULIER",
       "avec « il » ou « elle », le verbe reste au singulier")
def _accord_il_singulier(ctx: Contexte, i: int):
    """« il mangent » -> « il mange »."""
    if sujet_avant(ctx, i) not in ("il", "elle", "on") or ctx.elision(i):
        return None
    mot = ctx.mot(i)
    if not mot.endswith("ent"):
        return None

    infinitif = infinitif_premier_groupe(ctx, mot)
    if infinitif is None:
        return None
    accorde = conjuguer(ctx, infinitif, "e")
    if accorde is None or accorde == mot:
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("ACCORD_IMPARFAIT",
       "a l'imparfait, « je » et « tu » prennent « -ais », « il » prend « -ait »")
def _accord_imparfait(ctx: Contexte, i: int):
    """« il mangeais » -> « il mangeait », « je mangeait » -> « je mangeais »."""
    sujet = sujet_avant(ctx, i)
    mot = ctx.mot(i)
    if ctx.elision(i) or mot in FORMES_INTOUCHABLES:
        return None

    if sujet in ("il", "elle", "on") and mot.endswith("ais"):
        accorde = mot[:-3] + "ait"
    elif sujet in ("je", "tu") and mot.endswith("ait"):
        accorde = mot[:-3] + "ais"
    else:
        return None

    if not ctx.connait(accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("ACCORD_ILS_ENT", "avec « ils », le verbe se termine par « -nt »")
def _accord_ils_ent(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if sujet_avant(ctx, i) not in PRONOMS_PLURIEL or ctx.elision(i):
        return None
    if not mot.endswith("e") or mot in PRONOMS_COMPLEMENTS:
        return None
    if ctx.connait(mot + "nt"):
        return appliquer_casse(ctx.brut(i), mot + "nt")
    return None


@regle("SA_CA", "« sa » est un possessif ; devant un verbe, c'est « ça »")
def _sa_ca(ctx: Contexte, i: int):
    if ctx.mot(i) != "sa":
        return None
    if ctx.mot(i + 1) in VERBES_APRES_CA or ctx.elision(i + 1) in VERBES_APRES_CA:
        return appliquer_casse(ctx.brut(i), "ça")
    return None


APOSTROPHES_AVANT_PARTICIPE = {
    "ma": "m'a", "ta": "t'a", "mas": "m'as", "tas": "t'as", "la": "l'a",
}

# L'auxiliaire s'accorde avec le sujet, et le sujet n'est pas toujours la.
#
#     ta passé une bonne journée   ->  t'as   (c'est « tu » qui manque)
#     il ta dit quoi               ->  t'a    (le sujet est « il »)
#     tu ma dit que                ->  m'as   (le sujet est « tu »)
#     ça ma pris deux heures       ->  m'a    (le sujet est « ça »)

PRONOMS_AVANT_L_A = {"me", "te", "se", "nous", "vous", "lui", "leur"}

DETERMINANTS = {"un", "une", "le", "la", "les", "ce", "cet", "des", "du",
                "mon", "ton", "son", "quel", "ce"}


@regle("APOSTROPHE_AVANT_PARTICIPE",
       "« ma » est un possessif ; devant un participe, c'est « m'a »")
def _apostrophe_avant_participe(ctx: Contexte, i: int):
    remplacement = APOSTROPHES_AVANT_PARTICIPE.get(ctx.mot(i))
    if remplacement is None or ctx.elision(i):
        return None
    # « un tas fini » : precede d'un determinant, c'est un vrai nom.
    if ctx.mot(i - 1) in DETERMINANTS:
        return None
    # « la » est bien trop souvent un article : on ne le touche qu'apres un
    # pronom complement, ou « il me la dit » ne peut etre que « me l'a dit ».
    if ctx.mot(i) == "la" and ctx.mot(i - 1) not in PRONOMS_AVANT_L_A:
        return None
    if not ctx.est_participe(ctx.noyau(i + 1)):
        return None

    precedent = sans_accents(ctx.noyau(i - 1))
    if ctx.mot(i) == "ta" and precedent not in SUJETS_SINGULIER_NUS:
        remplacement = "t'as"
    elif ctx.mot(i) == "ma" and precedent == "tu":
        remplacement = "m'as"

    return appliquer_casse(ctx.brut(i), remplacement)


@regle("IL_A", "apres un pronom sujet, « a » est le verbe avoir : pas d'accent")
def _il_a(ctx: Contexte, i: int):
    if ctx.mot(i) != "à":
        return None
    if ctx.noyau(i - 1) in SUJETS_SINGULIER or ctx.elision(i) in ("c'", "ç'"):
        return appliquer_casse(ctx.brut(i), "a")
    return None


# Mots apres lesquels « a » ne peut etre que la preposition « à ».
AVANT_A_ACCENT = {
    "vais", "vas", "va", "allons", "allez", "vont", "aller", "allé", "allée",
    "allés", "allées", "irai", "iras", "ira", "irons", "irez", "iront",
    "grâce", "quant", "face", "contrairement", "conformément", "jusqu'",
    "prêt", "prête", "prêts", "prêtes", "habitué", "habituée", "obligé",
    "obligée", "pense", "penses", "pensé", "penser", "réfléchir", "réfléchi",
    "commence", "commences", "commencé", "commencer", "continue", "continuer",
    "hésite", "hésites", "hésité", "hésiter", "aide", "aider", "aidé",
    "sert", "servir", "servi", "arrive", "arriver", "arrivé", "parle",
    "parler", "parlé", "parles", "demande", "demander", "demandé", "donne",
    "donner", "donné", "joue", "jouer", "joué", "réussi", "réussit",
    "apprendre", "apprends", "appris", "rapport", "retour", "suite",
    "aille", "ailles", "aillent", "viens", "vient", "venez", "venir", "venu",
    "reste", "rester", "resté", "retourne", "retourner", "retourné", "monte",
    "monter", "emmène", "emmener", "amène", "amener", "envoie", "envoyer",
    "envoyé", "habite", "habiter", "travaille", "travailler", "cherche",
    "chercher", "cherché", "tiens", "tient", "sers", "décide", "décidé",
    "décider", "oblige", "obligé", "invite", "invité", "inviter", "force",
}

# Mots apres lesquels « a » ne peut etre que la preposition « à ».
APRES_A_ACCENT = {
    "côté", "cause", "travers", "propos", "peine", "nouveau", "priori",
    "part", "moitié", "force", "fond", "volonté", "moi", "toi",
    "condition", "défaut", "domicile", "l'heure", "l'aise", "l'avance",
    "l'époque", "l'écart",
}

# « à plus ! », « à demain ! » : ceux-la ne valent qu'en fin de phrase.
# « il n'y a plus rien » est un tout autre « a ».
APRES_A_ACCENT_FINAL = {"plus", "demain", "bientôt", "toute", "tantôt"}

# Devant ces mots, « a » est le verbe avoir : « il a », « on n'a », « y a ».
AVANT_A_VERBE = PRONOMS_SUJETS | {"ça", "ce", "qui", "y", "en", "n'", "qu'"}


@regle("A_ACCENT", "ici « a » est la preposition « à »")
def _a_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "a":
        return None
    if ctx.noyau(i - 1) in AVANT_A_ACCENT or ctx.mot(i - 1) in AVANT_A_ACCENT:
        return appliquer_casse(ctx.brut(i), "à")

    # Un sujet juste avant, et « a » redevient le verbe avoir.
    if ctx.noyau(i - 1) in AVANT_A_VERBE or ctx.elision(i - 1) == "n'":
        return None

    if ctx.mot(i + 1) in APRES_A_ACCENT:
        return appliquer_casse(ctx.brut(i), "à")
    if ctx.mot(i + 1) in APRES_A_ACCENT_FINAL and ctx.fin_de_segment(i + 1):
        return appliquer_casse(ctx.brut(i), "à")
    return None


@regle("ET_EST", "apres un pronom sujet, c'est le verbe « est »")
def _et_est(ctx: Contexte, i: int):
    if ctx.noyau(i) != "et":
        return None
    # « lui et elle », « toi et moi » : une vraie coordination.
    if ctx.mot(i + 1) in PRONOMS_SUJETS | {"moi", "toi", "lui", "eux"}:
        return None
    if ctx.elision(i) in ("c'", "ç'") or ctx.noyau(i - 1) in SUJETS_SINGULIER:
        return appliquer_casse(ctx.brut(i), ctx.elision(i) + "est")
    return None


@regle("ILS_ONT", "« ils on » : le verbe avoir s'ecrit « ont »")
def _ils_ont(ctx: Contexte, i: int):
    if ctx.mot(i) == "on" and ctx.mot(i - 1) in PRONOMS_PLURIEL:
        return appliquer_casse(ctx.brut(i), "ont")
    return None


@regle("ILS_SONT", "« ils son » : le verbe etre s'ecrit « sont »")
def _ils_sont(ctx: Contexte, i: int):
    if ctx.mot(i) != "son":
        return None
    sujet_pluriel = (ctx.mot(i - 1) in PRONOMS_PLURIEL
                     or (_est_pluriel(ctx, ctx.mot(i - 1))
                         and _determinant_pluriel(ctx, i - 2)))
    if sujet_pluriel:
        return appliquer_casse(ctx.brut(i), "sont")
    return None


# Terminaisons qu'un verbe conjugue ou un infinitif peut avoir. Un mot qui
# n'en a aucune (« truc », « film », « mec ») n'est pas un verbe, donc « se »
# ne peut pas le preceder.
TERMINAISONS_VERBALES = ("e", "s", "t", "d", "x", "r", "a", "i", "u", "é",
                         "ée", "ù", "û")

# Noms frequents dont la terminaison ressemble pourtant a celle d'un verbe.
NOMS_APRES_CE = {
    "soir", "matin", "midi", "jour", "moment", "week", "weekend", "coup",
    "gars", "truc", "machin", "bail", "délire", "monde", "genre", "temps",
    "niveau", "prix", "bruit", "message", "serveur", "salon", "projet",
    "sujet", "texte", "lien", "site", "compte", "groupe", "jeu", "type",
}


def _peut_etre_verbe(mot: str) -> bool:
    if mot in NOMS_APRES_CE:
        return False
    return mot.endswith(TERMINAISONS_VERBALES)


@regle("SE_CE", "« se » annonce un verbe ; ici c'est le demonstratif « ce »")
def _se_ce(ctx: Contexte, i: int):
    if ctx.mot(i) != "se":
        return None
    suivant = ctx.mot(i + 1)
    if suivant in ("qui", "que", "dont") or ctx.elision(i + 1) == "qu'":
        return appliquer_casse(ctx.brut(i), "ce")
    # « se truc » : ce qui suit n'est pas un verbe, « se » n'a rien a y faire.
    if suivant and ctx.connait(suivant) and not _peut_etre_verbe(suivant):
        return appliquer_casse(ctx.brut(i), "ce")
    return None


@regle("CE_SE", "devant un verbe pronominal, c'est « se »")
def _ce_se(ctx: Contexte, i: int):
    if ctx.mot(i) != "ce" or ctx.mot(i - 1) not in PRONOMS_SUJETS:
        return None
    # « il ce que » n'existe pas non plus, mais SE_CE s'en occupe.
    if ctx.mot(i + 1) in ("qui", "que", "dont", "soir", "matin") \
            or ctx.elision(i + 1) == "qu'":
        return None
    return appliquer_casse(ctx.brut(i), "se")


APRES_C_EST = {
    "un", "une", "le", "la", "les", "pas", "trop", "vrai", "vraiment", "bon",
    "bien", "ça", "cool", "chaud", "clair", "sûr", "mon", "ton", "son",
    "mes", "quoi", "comme", "beaucoup", "juste", "déjà", "possible",
    "impossible", "normal", "bizarre", "dur", "facile", "difficile", "nul",
    "génial", "cher", "grave", "moi", "toi", "lui", "eux", "nous", "vous",
    "peut", "toujours", "jamais", "rien", "tout", "mieux", "pire",
}


@regle("S_EST_C_EST", "« s'est » exige un verbe pronominal ; ici c'est « c'est »")
def _s_est_c_est(ctx: Contexte, i: int):
    if ctx.elision(i) != "s'" or ctx.noyau(i) != "est":
        return None
    # « on ne s'est pas vus », « il s'est pas rendu compte » : precede d'un
    # sujet, « s'est » est le pronominal attendu. La faute ne se produit
    # qu'en tete de phrase, la ou « c'est » etait le mot juste.
    if not ctx.debut_de_segment(i) and ctx.mot(i - 1) not in CHARNIERES:
        return None
    if ctx.mot(i + 1) in APRES_C_EST:
        return appliquer_casse(ctx.brut(i), "c'est")
    return None


# Verbes apres lesquels un « ou » final designe forcement un lieu : « tu vas
# ou ? », « il est ou ? ». La liste est fermee, et c'est ce qui la rend sure —
# « tu viens ou ? » veut dire « ou pas ? », et « venir » n'y figure pas.
VERBES_DE_LIEU = {
    "est", "sont", "es", "suis", "sommes", "êtes", "était", "étaient",
    "sera", "seront", "vas", "va", "vais", "allons", "allez", "vont",
    "habite", "habites", "habitez", "habitent", "bosse", "bosses",
    "travaille", "travailles", "travaillez", "mets", "met", "mettez",
    "range", "ranges", "rangez", "trouve", "trouves", "trouvez", "trouvent",
    "retrouve", "retrouves", "retrouvons", "retrouve-t-on", "pars", "part",
    "partez", "partent", "passe", "passes", "passez", "passent",
}

# Verbes qui introduisent une interrogation indirecte : apres eux, « ou »
# annonce un lieu et non un choix. « je sais pas ou il est ».
VERBES_D_INTERROGATION = {
    "sais", "sait", "savons", "savez", "savent", "su",
    "dis", "dit", "dites", "disent", "demande", "demandes", "demandez",
    "demandent", "demander", "voir", "vois", "voit", "voyez", "regarde",
    "regardes", "regardez", "cherche", "cherches", "cherchez", "cherchent",
    "oublie", "oublies", "oublié", "montre", "montres", "montrez",
}


@regle("C_EST_S_EST",
       "apres un pronom sujet, « c'est » est le pronominal « s'est »")
def _c_est_s_est(ctx: Contexte, i: int):
    """« il c'est trompe » -> « il s'est trompé ».

    La regle inverse existe deja. Celle-ci prend l'autre sens, et sa
    condition est nette : derriere un pronom sujet et devant un participe,
    « c'est » n'a aucune lecture — c'est le verbe pronominal.
    """
    if ctx.elision(i) != "c'" or ctx.noyau(i) != "est":
        return None
    if ctx.mot(i - 1) not in PRONOMS_SUJETS:
        return None
    # « il c'est bien passé » : un adverbe se glisse souvent entre
    # l'auxiliaire et son participe.
    suivant = ctx.mot(i + 1)
    if suivant in ADVERBES_INTERCALES:
        suivant = ctx.mot(i + 2)
    if not suivant or not (ctx.morphologie.est(suivant, *PARTICIPES)
                           or ctx.est_participe(suivant)):
        return None
    return appliquer_casse(ctx.brut(i), "s'est")


@regle("CES_C_EST", "« ces » est un determinant ; ici c'est « c'est »")
def _ces_c_est(ctx: Contexte, i: int):
    """« ces pas grave » -> « c'est pas grave ».

    « ces » et « ses » determinent un nom au pluriel. Devant « pas » suivi
    d'un adjectif, il n'y a pas de nom du tout : c'est « c'est », et la
    negation sans « ne » du francais parle.

    « ses pas resonnaient dans le couloir » existe, lui — d'ou la condition
    sur ce qui suit : un verbe conjugue derriere « pas » et la regle se
    tait.
    """
    if ctx.mot(i) not in ("ces", "ses") or ctx.elision(i):
        return None
    if ctx.mot(i + 1) != "pas":
        return None
    apres = ctx.mot(i + 2)
    # Derriere « c'est pas », ce qui suit est au singulier : « c'est pas
    # grave », « c'est pas vrai ». Le moindre pluriel derriere — « ses pas
    # résonnaient », « ses pas perdus » — et « pas » est bien le nom. Le mot
    # doit aussi etre connu : « resonnaient » sans accent ne prouve rien.
    if not ctx.morphologie.connait(apres) or ctx.morphologie.est(apres, *PLURIELS):
        return None
    return appliquer_casse(ctx.brut(i), "c'est")


@regle("OU_ACCENT", "« où » designe le lieu ; « ou » relie deux choix")
def _ou_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "ou":
        return None
    if ctx.mot(i + 1) in ("est", "sont", "es", "était", "étaient", "sera",
                          "seront", "ça"):
        return appliquer_casse(ctx.brut(i), "où")
    # « là ou j'habite » : apres « là », c'est toujours le lieu. L'accent du
    # « la » est encore a mettre : LA_ACCENT s'en charge, de son cote.
    if ctx.mot(i - 1) in ("là", "la"):
        return appliquer_casse(ctx.brut(i), "où")
    # « je sais pas ou aller » : devant un infinitif, « ou » n'a pas de sens.
    suivant = ctx.mot(i + 1)
    if suivant.endswith(("er", "ir")) and ctx.connait(suivant) \
            and suivant not in MOTS_INVARIABLES:
        return appliquer_casse(ctx.brut(i), "où")
    # « tu vas ou ? » : une conjonction ne ferme pas une phrase — il lui
    # faut quelque chose des deux cotes. Reste a ecarter « tu viens ou ? »,
    # qui veut dire « ou pas ? » : seuls les verbes de lieu comptent.
    if ctx.fin_de_segment(i) and ctx.noyau(i - 1) in VERBES_DE_LIEU:
        return appliquer_casse(ctx.brut(i), "où")
    # « je sais pas ou il est » : apres un verbe d'interrogation indirecte,
    # suivi d'un pronom ou d'un nom, c'est le lieu.
    if ctx.mot(i + 1) in ("est-ce", "est") or (
            ctx.mot(i + 1) in PRONOMS_SUJETS
            and _verbe_d_interrogation_avant(ctx, i)):
        return appliquer_casse(ctx.brut(i), "où")
    # « il est ou le fichier » : la question posee a l'envers. Un verbe de
    # lieu devant, un groupe nominal derriere — une conjonction n'aurait
    # rien a relier.
    if ctx.noyau(i - 1) in VERBES_DE_LIEU and ctx.mot(i + 1) in DETERMINANTS:
        return appliquer_casse(ctx.brut(i), "où")
    return None


def _verbe_d_interrogation_avant(ctx: "Contexte", i: int) -> bool:
    """« je sais pas ou », « dis moi ou » : le verbe est a deux ou trois mots."""
    return any(ctx.noyau(i - recul) in VERBES_D_INTERROGATION
               for recul in (1, 2, 3))


AVANT_LA_ACCENT = {
    "être", "suis", "es", "est", "sommes", "êtes", "sont", "étais", "était",
    "serai", "sera", "reste", "restes", "restons", "restez", "viens",
    "vient", "venez", "arrive", "arrives", "jusque", "par", "celui",
    "celle", "ceux", "celles", "mets", "assieds",
}


def _peut_suivre_un_article(ctx: "Contexte", i: int) -> bool:
    """Le mot en position i peut-il venir juste apres « la » ?

    C'est la question qui separe l'article de l'adverbe : dans « c'est la
    vie », « vie » est un nom, donc « la » est un article ; dans « il est la
    depuis hier », rien ne suit que « la » puisse determiner, et c'est
    « là ».

    Le dictionnaire ne dit pas la nature des mots — « aussi » et « vie » y
    sont tous deux de simples entrees. Mais il dit leur **pluriel**, et
    seuls les noms et les adjectifs en ont un : « vies » existe, « aussis »
    non. C'est ce detour qui repond a la question.
    """
    mot = ctx.mot(i)
    if not mot or mot in MOTS_INVARIABLES:
        return False
    if mot in DETERMINANTS or _adjectif_antepose(mot):
        return True
    return ctx.morphologie.au_pluriel(mot) is not None


def _infinitif_apres(ctx: "Contexte", i: int, sauts: int = 2) -> bool:
    """Un infinitif suit, un pronom complement eventuellement intercale.

    « il a du partir », « il a du le faire » : entre l'auxiliaire et
    l'infinitif se glissent « le », « la », « les », « en », « y ».
    """
    for saut in range(1, sauts + 1):
        mot = ctx.mot(i + saut)
        if not mot:
            return False
        if ctx.morphologie.est(mot, "inf"):
            return True
        if mot not in PRONOMS_INTERCALES and mot not in ADVERBES_DE_NEGATION:
            return False
    return False


# « je peu pas venir » : la negation se glisse entre le verbe et son
# infinitif, et le « ne » manque — c'est du francais parle, pas une faute.
ADVERBES_DE_NEGATION = {"pas", "plus", "jamais", "rien", "que", "qu'"}


@regle("DU_ACCENT", "« dû » est le participe de « devoir »")
def _du_accent(ctx: Contexte, i: int):
    """« il a du partir » -> « il a dû partir ».

    « du » est un article, « dû » le participe de « devoir ». Les deux sont
    trop courants pour se departager sur la frequence : c'est l'infinitif
    qui suit qui tranche, car un article n'en precede jamais.
    """
    if ctx.mot(i) != "du" or ctx.elision(i):
        return None
    if ctx.noyau(i - 1) not in AUXILIAIRES_AVOIR:
        return None
    if not _infinitif_apres(ctx, i):
        return None
    return appliquer_casse(ctx.brut(i), "dû")


# Formes de « avoir » : elles seules annoncent le participe « dû ».
AUXILIAIRES_AVOIR = {
    "ai", "as", "a", "avons", "avez", "ont",
    "avais", "avait", "avions", "aviez", "avaient",
    "aurai", "auras", "aura", "aurons", "aurez", "auront",
    "aurais", "aurait", "aurions", "auriez", "auraient",
}


@regle("SUR_ACCENT", "« sûr » veut dire certain ; « sur » est la preposition")
def _sur_accent(ctx: Contexte, i: int):
    """« je suis sur de moi » -> « sûr », « bien sur » -> « bien sûr ».

    La preposition « sur » introduit un lieu ; l'adjectif « sûr » se
    construit avec « de » ou « que ». C'est cette construction qui tranche,
    et elle ne laisse pas de place au doute : « sur de » n'existe pas.
    """
    mot = ctx.mot(i)
    if mot not in ("sur", "sure", "surs", "sures") or ctx.elision(i):
        return None
    accentue = {"sur": "sûr", "sure": "sûre",
                "surs": "sûrs", "sures": "sûres"}[mot]

    # « bien sur, on y va » : la locution, qui ne mene nulle part.
    if mot == "sur" and ctx.mot(i - 1) == "bien" and (
            ctx.fin_de_segment(i) or ctx.mot(i + 1) in ("que", "qu'")):
        return appliquer_casse(ctx.brut(i), accentue)

    # « je suis sur de moi », « t'es sur que c'est bon ».
    if ctx.noyau(i - 1) not in AUXILIAIRES_ETRE:
        return None
    if ctx.mot(i + 1) not in ("de", "d'", "que", "qu'") \
            and ctx.elision(i + 1) not in ("d'", "qu'"):
        return None
    return appliquer_casse(ctx.brut(i), accentue)


AUXILIAIRES_ETRE = {
    "suis", "es", "est", "sommes", "êtes", "sont",
    "étais", "était", "étions", "étiez", "étaient",
    "serai", "seras", "sera", "serons", "serez", "seront",
    "serais", "serait", "seriez", "seraient", "sois", "soit", "soyez",
}


@regle("PEU_PEUT", "« peut » est le verbe pouvoir ; « peu » est l'adverbe")
def _peu_peut(ctx: Contexte, i: int):
    """« il peu venir » -> « il peut venir ».

    PEUT_PEU traite le sens inverse. Ici c'est l'infinitif qui suit qui
    fait du « peu » un verbe : un adverbe n'en gouverne jamais.
    """
    if ctx.mot(i) != "peu" or ctx.elision(i):
        return None
    sujet = sujet_avant(ctx, i)
    formes = {"je": "peux", "tu": "peux", "il": "peut", "elle": "peut",
              "on": "peut", "ça": "peut"}
    accorde = formes.get(sujet)
    if accorde is None or not _infinitif_apres(ctx, i):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("PEUT_ETRE", "« peut-être » s'ecrit avec un trait d'union")
def _peut_etre(ctx: Contexte, i: int):
    """« peu etre que oui » -> « peut-être que oui ».

    « peu être » n'existe pas : l'adverbe « peu » ne gouverne pas
    d'infinitif. Sauf derriere un sujet, ou « il peut être là » est correct
    et c'est PEU_PEUT qui s'en occupe.
    """
    if ctx.mot(i) != "peu" or ctx.separateur(i) != " ":
        return None
    if ctx.mot(i + 1) not in ("etre", "être"):
        return None
    if sujet_avant(ctx, i) in PRONOMS_SUJETS:
        return None
    return (appliquer_casse(ctx.brut(i), "peut-être"), 2)


@regle("VOIRE_VOIR", "« voire » veut dire « et même » ; ici c'est « voir »")
def _voire_voir(ctx: Contexte, i: int):
    """« je vais voire » -> « je vais voir ».

    « voire » est un adverbe : il ne se conjugue pas, ne suit pas un
    semi-auxiliaire et ne se laisse pas introduire par « de » ou « a ».
    """
    if ctx.mot(i) != "voire" or ctx.elision(i):
        return None
    precedent = ctx.noyau(i - 1)
    if precedent not in SEMI_AUXILIAIRES and precedent not in ("de", "d'", "à"):
        return None
    return appliquer_casse(ctx.brut(i), "voir")


@regle("LA_ACCENT", "« là » designe le lieu ; « la » est un article")
def _la_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "la":
        return None
    if ctx.mot(i + 1) == "bas" and ctx.separateur(i) == " ":
        return (appliquer_casse(ctx.brut(i), "là-bas"), 2)
    # « la ou j'habite » : l'article ne precede jamais une conjonction, et
    # les deux mots se corrigent ensemble.
    if ctx.mot(i + 1) in ("ou", "où") and ctx.separateur(i) == " ":
        return (appliquer_casse(ctx.brut(i), "là où"), 2)
    if ctx.noyau(i - 1) in AVANT_LA_ACCENT and not _peut_suivre_un_article(ctx, i + 1):
        return appliquer_casse(ctx.brut(i), "là")
    return None


@regle("TOUT_TOUS", "devant un determinant pluriel, « tout » s'ecrit « tous »")
def _tout_tous(ctx: Contexte, i: int):
    if ctx.mot(i) != "tout":
        return None
    if ctx.mot(i + 1) in ("les", "ces", "mes", "tes", "ses", "nos", "vos",
                          "leurs", "ceux"):
        return appliquer_casse(ctx.brut(i), "tous")
    return None


@regle("MES_MAIS", "ici « mes » est la conjonction « mais »")
def _mes_mais(ctx: Contexte, i: int):
    if ctx.mot(i) != "mes":
        return None
    if ctx.mot(i + 1) in PRONOMS_SUJETS | {"ça", "bon", "bref", "quand"} \
            or ctx.mot(i + 1) in ("c'est", "j'ai", "j'y"):
        return appliquer_casse(ctx.brut(i), "mais")
    return None


@regle("PEUT_PEU", "« un peu » : l'adverbe ne prend pas de « t »")
def _peut_peu(ctx: Contexte, i: int):
    if ctx.mot(i) != "peut":
        return None
    if ctx.mot(i - 1) in ("un", "très", "trop", "si", "plus", "aussi",
                          "assez", "quelque"):
        return appliquer_casse(ctx.brut(i), "peu")
    return None


MOTS_INTERROGATIFS = {"qui", "où", "quand", "comment", "pourquoi", "combien",
                      "quel", "quelle", "quels", "quelles", "que"}


@regle("EST_CE", "« est-ce » s'ecrit avec un trait d'union")
def _est_ce(ctx: Contexte, i: int):
    if ctx.mot(i) != "est" or ctx.mot(i + 1) != "ce" or ctx.separateur(i) != " ":
        return None
    interroge = (
        i == 0
        or ctx.mot(i - 1) in MOTS_INTERROGATIFS
        or ctx.elision(i - 1) == "qu'"
        or ctx.mot(i + 2) == "que"
        or ctx.elision(i + 2) == "qu'"
    )
    if not interroge:
        return None
    return (appliquer_casse(ctx.brut(i), "est-ce"), 2)


def _auxiliaire_avant(ctx: Contexte, i: int) -> bool:
    """Un auxiliaire precede-t-il, adverbe intercale ou non ?

    « elle a beaucoup travaillé » : l'adverbe ne coupe pas le lien entre
    l'auxiliaire et son participe.
    """
    if ctx.noyau(i - 1) in AUXILIAIRES:
        return True
    return (ctx.mot(i - 1) in ADVERBES_INTERCALES
            and ctx.noyau(i - 2) in AUXILIAIRES)


@regle("PARTICIPE_APRES_AUXILIAIRE",
       "apres l'auxiliaire, le verbe prend « -é » et non « -er »")
def _participe_apres_auxiliaire(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if not mot.endswith("er") or ctx.elision(i):
        return None
    if not _auxiliaire_avant(ctx, i):
        return None
    participe = mot[:-2] + "é"
    if ctx.connait(participe):
        return appliquer_casse(ctx.brut(i), participe)
    return None


@regle("PARTICIPE_APRES_AUXILIAIRE_CONJUGUE",
       "apres l'auxiliaire, le verbe se met au participe")
def _participe_apres_auxiliaire_conjugue(ctx: Contexte, i: int):
    """« ils ont prit le train » -> « ils ont pris le train ».

    La regle d'au-dessus ne connait que les infinitifs en « -er ». Celle-ci
    s'appuie sur le dictionnaire : apres un auxiliaire, une forme conjuguee
    est forcement un participe mal ecrit, quel que soit le verbe.

    Le participe se cherche dans tout le paradigme, pas dans le temps du mot
    ecrit : « prit » est un passe simple, « pris » n'en fait pas partie.
    """
    mot = ctx.mot(i)
    if ctx.elision(i) or not _auxiliaire_avant(ctx, i):
        return None
    traits = ctx.morphologie.traits(mot)
    # Une forme conjuguee, et rien d'autre : ni nom, ni participe deja
    # correct, ni infinitif.
    if not traits or not traits <= CONJUGUES:
        return None
    participe = ctx.morphologie.forme(mot, PARTICIPES_MASCULINS)
    if participe is None or participe == mot:
        return None
    return appliquer_casse(ctx.brut(i), participe)


@regle("PARTICIPE_SANS_ACCENT",
       "apres l'auxiliaire, le participe prend son accent")
def _participe_sans_accent(ctx: Contexte, i: int):
    """« j'ai mange » -> « j'ai mangé ».

    L'accent oublie ne se voit pas du dictionnaire : « mange » est un mot.
    Seul l'auxiliaire qui precede trahit le participe.

    Reste un piege : « j'ai envie » n'est pas « j'ai envié ». On s'appuie sur
    la frequence — un participe bien plus rare que le mot ecrit est sans
    doute un nom qui lui ressemble.
    """
    if ctx.noyau(i - 1) not in AUXILIAIRES or ctx.elision(i):
        return None

    mot = ctx.mot(i)
    if not mot.endswith("e") or mot in MOTS_INVARIABLES:
        return None

    # « contente » est le feminin de « content », pas une forme de
    # « contenter » : quand le mot prive de son « e » existe deja, c'est un
    # adjectif ou un nom, et l'auxiliaire ne prouve rien.
    if ctx.connait(mot[:-1]):
        return None

    # « le fichier est vide » : « vide » est un adjectif, et l'auxiliaire ne
    # le rend pas participe. La regle du « e » manquant ne le voyait pas,
    # « vid » n'etant pas un mot ; le dictionnaire, lui, le sait.
    if ctx.morphologie.nom(mot):
        return None

    infinitif = infinitif_premier_groupe(ctx, mot)
    if infinitif is None or infinitif[:-2] + "e" != mot:
        return None

    participe = infinitif[:-2] + "é"
    if not ctx.connait(participe):
        return None
    if ctx.lexique.rang(participe) > ctx.lexique.rang(mot) * 10:
        return None
    return appliquer_casse(ctx.brut(i), participe)


@regle("INFINITIF_APRES_SEMI_AUXILIAIRE",
       "apres ce verbe, le suivant reste a l'infinitif : « -er »")
def _infinitif_apres_semi_auxiliaire(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if not mot.endswith("é") or mot in NOMS_EN_E or ctx.elision(i):
        return None
    if ctx.noyau(i - 1) not in SEMI_AUXILIAIRES:
        return None
    infinitif = mot[:-1] + "er"
    if ctx.connait(infinitif):
        return appliquer_casse(ctx.brut(i), infinitif)
    return None


# Verbes pronominaux dont le participe ne s'accorde pas : leur complement
# est indirect. « elles se sont écrit » — on ecrit *a* quelqu'un.
PARTICIPES_SANS_ACCORD = {
    "écrit", "parlé", "téléphoné", "plu", "souri", "menti", "nui",
    "succédé", "ressemblé", "demandé", "dit", "répondu", "promis",
    "permis", "rendu", "donné", "offert", "envoyé", "juré", "raconté",
}

# Sujet -> terminaison a ajouter au participe employe avec « etre ».
ACCORDS_ETRE = {
    ("elle", "est"): "e",
    ("elles", "sont"): "es",
    ("ils", "sont"): "s",
    ("nous", "sommes"): "s",
}

# Les memes accords, dits au dictionnaire plutot qu'ecrits a la main. Il
# connait les formes que l'ajout d'une lettre ne donne pas : « ils sont
# national » veut « nationaux », pas « nationals ».
TRAITS_ETRE = {
    "e": ("pfs", "fs"),
    "es": ("pfp", "fp"),
    "s": ("pmp", "mp"),
}


@regle("ACCORD_PARTICIPE_ETRE",
       "avec l'auxiliaire « etre », le participe s'accorde avec le sujet")
def _accord_participe_etre(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    if ctx.elision(i):
        return None
    # Un participe (« venu ») ou un adjectif (« content ») : les deux
    # s'accordent avec le sujet.
    if not ctx.est_participe(mot) and not _est_adjectif(ctx, mot):
        return None

    # « elles se sont écrit » : le complement est indirect, rien ne s'accorde.
    if ctx.mot(i - 2) in ("se", "s'") and mot in PARTICIPES_SANS_ACCORD:
        return None

    # « nous sommes arrivé » : le sujet est juste la. « ils se sont trompé » :
    # il est un mot plus loin, derriere le pronom reflechi.
    auxiliaire = ctx.noyau(i - 1)
    terminaison = ACCORDS_ETRE.get((ctx.mot(i - 2), auxiliaire))
    if terminaison is None and ctx.mot(i - 2) in PRONOMS_INTERCALES:
        terminaison = ACCORDS_ETRE.get((ctx.mot(i - 3), auxiliaire))
    if terminaison is None:
        terminaison = _accord_sujet_nominal_etre(ctx, i)
    if terminaison is None:
        return None

    if mot.endswith(("s", "x", "e")):
        return None

    accorde = ctx.morphologie.forme(mot, TRAITS_ETRE[terminaison])
    if accorde is None:
        accorde = mot + terminaison
    if accorde == mot or not ctx.connait(accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


ETRE_PLURIEL = {"sont", "sommes", "étaient", "étions", "seront", "serons"}
ETRE_SINGULIER = {"est", "était", "sera", "serait", "soit"}


def _accord_sujet_nominal_etre(ctx: Contexte, i: int) -> str | None:
    """« les enfants sont content », « la porte est ouvert ».

    Le sujet est un nom : c'est l'auxiliaire qui donne le nombre, et le nom
    qui donne le genre — quand on le connait. Sans le genre, on s'en tient
    au masculin pluriel, qui vaut aussi pour un groupe mixte ; au singulier,
    ou le masculin ne se rattrape pas, on se tait.
    """
    auxiliaire = ctx.noyau(i - 1)
    if auxiliaire in ETRE_PLURIEL:
        if not _est_pluriel(ctx, ctx.mot(i - 2)):
            return None
        return "es" if genre_du_nom(ctx, i - 2) == "f" else "s"

    if auxiliaire in ETRE_SINGULIER:
        nom = ctx.mot(i - 2)
        if nom in PRONOMS_SUJETS or not ctx.morphologie.singulier(nom):
            return None
        if ctx.mot(i - 3) not in DETERMINANTS_SINGULIERS \
                and ctx.elision(i - 2) != "l'":
            return None
        return "e" if genre_du_nom(ctx, i - 2) == "f" else None
    return None


NOMBRES_PLURIELS = {"deux", "trois", "quatre", "cinq", "six", "sept", "huit",
                    "neuf", "dix", "onze", "douze", "quinze", "vingt", "cent"}

# Mots qui ne s'accordent jamais. Plusieurs ont pourtant un pluriel au
# dictionnaire — « les avants » d'une equipe, « les contres » au bridge — et
# les regles d'accord les prendraient pour des adjectifs.
MOTS_INVARIABLES = {
    # « pas » est aussi un nom — « des pas dans le couloir » — mais c'est
    # mille fois la negation. Le compter comme un pluriel ferait accorder
    # ce qui le suit : « c'est pas vrai » deviendrait « pas vrais ».
    "pas",
    "avant", "après", "contre", "entre", "sous", "sur", "dans", "vers",
    "chez", "depuis", "pendant", "malgré", "selon", "sauf", "comme", "sans",
    "avec", "pour", "par", "de", "du", "des", "à", "au", "aux", "en", "que",
    "qui", "quoi", "dont", "où", "quand", "donc", "alors", "puis", "ensuite",
    "très", "trop", "bien", "mal", "encore", "jamais", "toujours", "aussi",
    "plus", "moins", "ainsi", "lorsque", "puisque", "parce", "car", "mais",
    "ou", "et", "ni", "si", "non", "oui", "peu", "assez", "presque", "déjà",
    "hier", "demain", "aujourd'hui", "ici", "là", "partout", "ailleurs",
    "dehors", "dedans", "dessus", "dessous", "jusque", "jusqu", "afin",
    "autour", "auprès", "grâce", "face", "quant", "soit", "tant", "tellement",
}


# Determinants qui portent le genre. « les », « des », « ces » ne le
# portent pas, et c'est justement dans ces groupes-la qu'on en a besoin.
DETERMINANTS_GENRES = {
    "le": "m", "un": "m", "ce": "m", "cet": "m", "mon": "m", "ton": "m",
    "son": "m", "du": "m", "au": "m", "quel": "m",
    "la": "f", "une": "f", "cette": "f", "ma": "f", "ta": "f", "sa": "f",
    "quelle": "f",
}


def genre_du_nom(ctx: "Contexte", i: int) -> str | None:
    """Le genre du nom en position i, par tout ce qui peut le dire.

    Quatre sources, de la plus sure a la moins precise :

    1. le dictionnaire, quand le nom a deux genres — « chatte » est un
       feminin, il le dit lui-meme ;
    2. le determinant, quand il en porte un — « la porte », « une maison » ;
    3. un adjectif deja accorde dans le groupe — « une belle maison » le dit
       deux fois avant qu'on ait besoin d'une troisieme ;
    4. la table de `genres.py`, terminaisons et liste.

    Rien du tout est une reponse : elle fait taire les regles qui en
    dependent, ce qui vaut mieux que d'ecrire un masculin au hasard.
    """
    mot = ctx.mot(i)
    if not mot:
        return None

    traits = ctx.morphologie.traits(mot)
    if traits & {"ms", "mp"} and not traits & {"fs", "fp"}:
        return "m"
    if traits & {"fs", "fp"} and not traits & {"ms", "mp"}:
        return "f"

    for recul in (1, 2):
        precedent = ctx.mot(i - recul)
        if precedent in DETERMINANTS_GENRES:
            return DETERMINANTS_GENRES[precedent]
        # « une belle maison » : l'adjectif antepose porte deja l'accord.
        voisins = ctx.morphologie.traits(precedent)
        if _adjectif_antepose(precedent) and voisins & {"fs", "fp"} \
                and not voisins & {"ms", "mp"}:
            return "f"

    from .genres import genre

    lemmes = ctx.morphologie.lemmes(mot)
    return genre(lemmes[0] if lemmes else mot)


def _est_participe_seulement(ctx: "Contexte", mot: str) -> bool:
    """« fermé » est un participe et rien d'autre ; « mange » est un verbe."""
    traits = ctx.morphologie.traits(mot)
    return bool(traits) and traits <= PARTICIPES


def _est_adjectif(ctx: "Contexte", mot: str) -> bool:
    """Le mot peut-il s'accorder comme un adjectif ?

    Un adjectif a un feminin — « content » / « contente » — ou se termine
    deja par un « e » qui lui en tient lieu — « rouge ». Cette question
    ecarte « avant », « contre » et les autres invariables qui ont un
    pluriel pour d'autres raisons, et surtout les noms : « restaurant » n'a
    pas de feminin, donc « des tickets restaurant » ne s'accorde pas.

    Ajouter un « e » a la fin ne suffisait pas a la poser. « blanc » fait
    « blanche », « long » fait « longue », « fermé » fait « fermée » : le
    dictionnaire connait ces feminins-la, la regle de terminaison non, et
    « des chevaux blanc » restait tel quel.
    """
    if mot in MOTS_INVARIABLES or not ctx.connait(mot):
        return False
    if mot.endswith("e"):
        return True
    traits = ctx.morphologie.traits(mot)
    if traits & {"ms", "pms"}:
        # `accorder` cherche le feminin dans le paradigme ou le mot figure
        # au masculin. « content » est aussi la 3e personne du pluriel de
        # « conter » : chercher partout rendrait « contée » aussi bien que
        # « contente », et le doute ferait tout taire.
        return ctx.morphologie.accorder(mot, {"fs", "pfs"}) is not None
    if traits:
        # Le dictionnaire connait ce mot et ne lui voit pas de feminin.
        return False
    return ctx.connait(mot + "e")


def _est_pluriel(ctx: "Contexte", mot: str) -> bool:
    """Le mot peut-il etre un nom au pluriel ?

    « quelques » et « plusieurs » portent bien la marque du pluriel, mais ce
    sont des determinants : les prendre pour le nom du groupe ferait chercher
    le verbe un mot trop loin.

    Le dictionnaire repond mieux que la terminaison : il sait que « chevaux »
    est un pluriel, que « le prix » et « les prix » s'ecrivent pareil, et que
    « finis » est un verbe et non le pluriel de quoi que ce soit.
    """
    if not mot:
        return False
    if (mot in DETERMINANTS_PLURIELS or mot in NOMBRES_PLURIELS
            or mot in MOTS_INVARIABLES or mot in PRONOMS_SUJETS):
        return False
    traits = ctx.morphologie.traits(mot)
    if traits:
        return bool(traits & NOMS_PLURIELS)
    return mot.endswith(("s", "x")) and ctx.connait(mot)


# Quantites suivies de « de » : elles commandent le pluriel aussi surement
# qu'un determinant. « beaucoup de gens pensent », « plein de trucs
# trainent ».
QUANTITES = {"beaucoup", "plein", "peu", "tant", "autant", "plupart",
             "combien", "assez", "trop", "moins", "plus"}


def _sujet_pluriel_avant(ctx: "Contexte", i: int) -> bool:
    """Le verbe en position i a-t-il un sujet nominal au pluriel ?

    Trois facons de l'ecrire, et le correcteur n'en voyait qu'une :

        les gens pensent              un determinant, un nom
        beaucoup de gens pensent      une quantite, « de », un nom
        les gens qui pensent          le meme groupe, derriere « qui »

    Chacune demande que le nom soit un pluriel et que ce qui l'annonce en
    soit un aussi : sans ces deux appuis, « les » pourrait etre un pronom
    (« je les mange ») et le nom pourrait etre le verbe.
    """
    # « les gens qui pensent » : le pronom relatif reprend le groupe d'avant.
    recul = 1
    if ctx.mot(i - 1) == "qui":
        recul = 2

    nom = ctx.mot(i - recul)
    if not _est_pluriel(ctx, nom) or _adjectif_antepose(nom):
        return False
    if _determinant_pluriel(ctx, i - recul - 1):
        return True
    # « beaucoup de gens » : la quantite est deux mots plus loin.
    return (ctx.noyau(i - recul - 1) in ("de", "d'")
            and ctx.mot(i - recul - 2) in QUANTITES)


def _determinant_pluriel(ctx: "Contexte", i: int) -> bool:
    """Le jeton i annonce-t-il un groupe au pluriel ?

    « les » est aussi un pronom complement : « je les mange » n'annonce
    aucun nom. On le refuse donc derriere un pronom sujet.
    """
    mot = ctx.mot(i)
    if mot in DETERMINANTS_PLURIELS or mot in NOMBRES_PLURIELS:
        return True
    return mot == "les" and ctx.mot(i - 1) not in PRONOMS_SUJETS


def _pluriels(ctx: "Contexte", mot: str) -> list[str]:
    """Les pluriels envisageables d'un nom singulier.

    Le dictionnaire connait le sien — « bijou » fait « bijoux », « pneu »
    fait « pneus », et aucune regle de terminaison ne distingue les deux.
    Quand il ignore le mot, on retombe sur ces regles, qui ont le merite de
    ne rien demander.
    """
    lu = ctx.morphologie.au_pluriel(mot)
    if lu is not None:
        return [lu]
    if mot.endswith("al"):
        return [mot[:-2] + "aux", mot + "s"]
    if mot.endswith(("eau", "eu")):
        return [mot + "x", mot + "s"]
    return [mot + "s"]


@regle("ACCORD_DETERMINANT_NOM",
       "le nom s'accorde avec son determinant pluriel")
def _accord_determinant_nom(ctx: Contexte, i: int):
    mot = ctx.mot(i)
    determinant = ctx.mot(i - 1)

    if determinant in DETERMINANTS_PLURIELS | NOMBRES_PLURIELS:
        pass
    elif determinant == "les" and ctx.mot(i - 2) not in PRONOMS_SUJETS:
        pass
    elif _adjectif_antepose(determinant) and _est_pluriel(ctx, determinant) \
            and _determinant_pluriel(ctx, i - 2):
        # « des jolies fleur », « les dernières affiche » : entre le
        # determinant et le nom se glisse un adjectif, et il n'y en a qu'une
        # petite classe fermee qui se place la.
        pass
    else:
        # « les » est aussi un pronom : « je les mange » n'a pas de nom.
        return None

    if ctx.elision(i) or mot.endswith(("s", "x", "z")) or not ctx.connait(mot):
        return None

    for pluriel in _pluriels(ctx, mot):
        if ctx.connait(pluriel):
            return appliquer_casse(ctx.brut(i), pluriel)
    return None


# Les seuls adjectifs qui se placent *avant* le nom en francais. La liste
# est courte et fermee, ce qui la rend sure : dans « les dernières affiches »,
# « dernières » ne peut pas etre le sujet, et « affiches » est donc un nom.
# Sans elle, « les dernières affiche » devenait « les dernières affichent ».
ADJECTIFS_ANTEPOSES = {
    "dernier", "premier", "second", "prochain", "grand", "petit", "gros",
    "bon", "mauvais", "beau", "joli", "nouveau", "vieux", "jeune", "long",
    "autre", "même", "seul", "vrai", "faux", "certain", "propre", "ancien",
    "haut", "large", "court", "meilleur", "moindre", "double", "demi",
}


def _adjectif_antepose(mot: str) -> bool:
    """Ce mot est-il un adjectif qui se place avant son nom ?"""
    for terminaison in ("ières", "ière", "iers", "ier", "elles", "elle",
                        "eaux", "eau", "les", "es", "s", "x", "e", ""):
        if terminaison and not mot.endswith(terminaison):
            continue
        racine = mot[: len(mot) - len(terminaison)] if terminaison else mot
        for retour in ("", "ier", "eau", "el", "l", "e"):
            if racine + retour in ADJECTIFS_ANTEPOSES:
                return True
    return mot in ADJECTIFS_ANTEPOSES


@regle("ACCORD_SUJET_NOMINAL",
       "le verbe s'accorde avec son sujet au pluriel")
def _accord_sujet_nominal(ctx: Contexte, i: int):
    """« les gens pense » -> « les gens pensent »."""
    if ctx.elision(i) or not _sujet_pluriel_avant(ctx, i):
        return None

    mot = ctx.mot(i)
    if mot in PRONOMS_COMPLEMENTS:
        return None

    # Le dictionnaire sait conjuguer tous les verbes, pas seulement ceux du
    # 1er groupe : « les gens finit » devient « les gens finissent ».
    #
    # On ne le suit toutefois que sur les mots qui ne peuvent **pas** etre
    # des noms. Un seul mot au pluriel devant lui ne suffit pas a faire d'un
    # nom un verbe — « les dernières affiche » l'a montre une fois — et les
    # noms, eux, restent traites par la voie d'en dessous, plus etroite et
    # eprouvee.
    if not ctx.morphologie.nom(mot):
        accorde = accorder_le_verbe(ctx, i, "3p")
        if accorde is not None:
            return accorde
        if ctx.morphologie.connait(mot):
            # Il sait ce qu'est ce mot, et sa reponse est « non ».
            return None

    if mot.endswith("ent"):
        return None
    if mot.endswith(("s", "x")) and ctx.connait(mot[:-1]):
        return None
    infinitif = infinitif_premier_groupe(ctx, mot)
    if infinitif is None:
        return None
    # Un participe (« les enfants joué ») n'est pas un verbe conjugue.
    if mot.endswith(("é", "és", "ée", "ées")):
        return None
    accorde = conjuguer(ctx, infinitif, "ent")
    if accorde is None or accorde == mot:
        return None
    return appliquer_casse(ctx.brut(i), accorde)


@regle("ACCORD_ADJECTIF_PLURIEL",
       "l'adjectif s'accorde avec le nom au pluriel")
def _accord_adjectif_pluriel(ctx: Contexte, i: int):
    """« des voitures rouge » -> « rouges », « trois petit chats » -> « petits »."""
    mot = ctx.mot(i)
    if ctx.elision(i) or not mot or mot.endswith(("s", "x")):
        return None
    if mot in PRONOMS_COMPLEMENTS or not _est_adjectif(ctx, mot):
        return None
    # Un verbe s'accorde autrement : ACCORD_SUJET_NOMINAL s'en charge. Un
    # participe, lui, s'accorde bien comme un adjectif — « les yeux fermé »
    # veut « fermés » — et la terminaison seule les confondait.
    if (infinitif_premier_groupe(ctx, mot) is not None
            and not _est_participe_seulement(ctx, mot)):
        return None
    # « les chiens court vite » : « court » est un adjectif autant qu'un
    # verbe, et les deux lectures demandent des corrections opposees —
    # « courts » ou « courent ». Devant ce partage, on n'invente pas.
    if ctx.morphologie.verbe(mot):
        return None

    indice_du_nom = None
    if _est_pluriel(ctx, ctx.mot(i - 1)) and _determinant_pluriel(ctx, i - 2):
        indice_du_nom = i - 1
    elif _determinant_pluriel(ctx, i - 1) and _est_pluriel(ctx, ctx.mot(i + 1)):
        indice_du_nom = i + 1
    if indice_du_nom is None:
        return None

    # L'adjectif suit le genre du nom. Quand ce genre reste inconnu, deux
    # cas : ou bien l'adjectif s'ecrit pareil aux deux genres — « rouges »,
    # « faciles » — et le nombre suffit ; ou bien il differe, et l'ecrire au
    # masculin serait un coup de des. « des voitures blanc » devenait « des
    # voitures blancs » : une faute laissee vaut mieux qu'une faute ecrite.
    voulu = genre_du_nom(ctx, indice_du_nom)
    masculin = ctx.morphologie.accorder(mot, {"mp", "pmp"})
    feminin = ctx.morphologie.accorder(mot, {"fp", "pfp"})

    if voulu == "f" and feminin is not None:
        return appliquer_casse(ctx.brut(i), feminin)
    if voulu == "m" and masculin is not None:
        return appliquer_casse(ctx.brut(i), masculin)
    if voulu is None and masculin is not None and feminin is not None \
            and masculin != feminin:
        return None

    for pluriel in _pluriels(ctx, mot):
        if ctx.connait(pluriel):
            return appliquer_casse(ctx.brut(i), pluriel)
    return None


# Conditionnel -> imparfait, pour les verbes dont la forme ne se devine pas.
IMPARFAITS = {
    "aurais": "avais", "aurait": "avait", "aurions": "avions",
    "auriez": "aviez", "auraient": "avaient",
    "serais": "étais", "serait": "était", "serions": "étions",
    "seriez": "étiez", "seraient": "étaient",
    "pourrais": "pouvais", "pourrait": "pouvait", "pourrions": "pouvions",
    "pourriez": "pouviez", "pourraient": "pouvaient",
    "voudrais": "voulais", "voudrait": "voulait", "voudraient": "voulaient",
    "devrais": "devais", "devrait": "devait", "devraient": "devaient",
    "saurais": "savais", "saurait": "savait", "sauraient": "savaient",
    "irais": "allais", "irait": "allait", "iraient": "allaient",
    "ferais": "faisais", "ferait": "faisait", "feraient": "faisaient",
    "viendrais": "venais", "viendrait": "venait", "viendraient": "venaient",
    "verrais": "voyais", "verrait": "voyait", "verraient": "voyaient",
}

TERMINAISONS_CONDITIONNEL = ("rais", "rait", "raient", "rions", "riez")


@regle("SI_CONDITIONNEL",
       "apres « si », le verbe se met a l'imparfait, jamais au conditionnel")
def _si_conditionnel(ctx: Contexte, i: int):
    """« si j'aurais su » -> « si j'avais su », « si tu pourrais » -> « pouvais »."""
    # Le sujet peut s'intercaler : « si tu pourrais ».
    apres_si = ctx.mot(i - 1) == "si" or (
        ctx.mot(i - 1) in PRONOMS_SUJETS and ctx.mot(i - 2) == "si"
    )
    if not apres_si:
        return None

    elision, noyau = separer_clitique(ctx.mot(i))
    if not noyau:
        return None

    imparfait = IMPARFAITS.get(noyau)
    if imparfait is None:
        # Verbes reguliers : le conditionnel est l'infinitif suivi de « -ais ».
        for terminaison in TERMINAISONS_CONDITIONNEL:
            if not noyau.endswith(terminaison):
                continue
            infinitif = noyau[: len(noyau) - len(terminaison)] + "r"
            if not ctx.connait(infinitif) or not infinitif.endswith("er"):
                continue
            imparfait = conjuguer(ctx, infinitif,
                                  terminaison.replace("r", "", 1))
            break

    if imparfait is None or imparfait == noyau:
        return None
    return appliquer_casse(ctx.brut(i), elision + imparfait)


@regle("LEUR_LEURS", "devant un nom au pluriel, « leur » prend un « s »")
def _leur_leurs(ctx: Contexte, i: int):
    """« dans leur maisons » -> « dans leurs maisons »."""
    if ctx.mot(i) != "leur" or ctx.elision(i):
        return None
    # « je leur dis » : la, « leur » est un pronom, et reste invariable.
    if ctx.mot(i - 1) in PRONOMS_SUJETS:
        return None

    suivant = ctx.mot(i + 1)
    if not _est_pluriel(ctx, suivant):
        return None
    # Le mot doit avoir un singulier : c'est ce qui distingue un nom au
    # pluriel d'un verbe comme « dis ».
    if not ctx.connait(suivant[:-1]) or infinitif_premier_groupe(ctx, suivant):
        return None
    return appliquer_casse(ctx.brut(i), "leurs")


# ---------------------------------------------------------------------------
# Analyse
# ---------------------------------------------------------------------------

def analyser(texte: str, jetons: list[Jeton], lexique,
             regles_ignorees: set[str] = frozenset(),
             registre: str = PARLE, morphologie=None) -> list[Suggestion]:
    """Passe toutes les regles sur le texte et renvoie leurs propositions."""
    ctx = Contexte(texte, jetons, lexique, morphologie)
    applicables = [
        r for r in REGLES
        if r.registre == "tous" or (r.registre == SOUTENU and registre == SOUTENU)
    ]
    suggestions: list[Suggestion] = []
    couvert: set[int] = set()

    for i in range(len(jetons)):
        if i in couvert:
            continue
        for r in applicables:
            if r.nom in regles_ignorees:
                continue
            resultat = r.fonction(ctx, i)
            if resultat is None:
                continue
            remplacement, portee = (
                resultat if isinstance(resultat, tuple) else (resultat, 1)
            )
            if remplacement == texte[jetons[i].debut:jetons[i + portee - 1].fin]:
                continue
            suggestions.append(
                Suggestion(i, portee, remplacement, r.nom, r.message)
            )
            couvert.update(range(i, i + portee))
            break

    return suggestions


# ---------------------------------------------------------------------------
# Le registre soutenu
#
# Ces regles-la ne corrigent aucune faute : elles remontent le ton. Elles
# dorment donc tant qu'on ne les reclame pas, application par application ou
# d'un reglage. C'est exactement ce que Papote refuse de faire par defaut.
# ---------------------------------------------------------------------------

# « que » n'y figure pas : « faut que j'y aille » n'est pas une negation.
NEGATIONS = {"pas", "plus", "jamais", "rien", "personne", "guère", "aucun",
             "aucune", "nul", "nulle"}

# Combien de mots peuvent separer le verbe de sa negation.
PORTEE_NEGATION = 3

# Sujets derriere lesquels on peut glisser un « ne » sans se tromper. Ni « y »
# ni « en » n'y figurent : ce sont des pronoms intercales, et le « ne » se
# place devant eux — « il n'y a pas », jamais « il y n'a pas ».
SUJETS_NEGATION = PRONOMS_SUJETS | {"ça", "ce", "qui", "celui", "celle",
                                    "chacun", "personne", "tout"}

# Elisions qui portent le sujet : « j'ai » -> « je n'ai ».
SUJETS_ELIDES = {"j'": "je", "c'": "ce", "ç'": "ce", "t'": "tu", "n'": None}

VOYELLES = "aeiouyàâäéèêëîïôöùûüh"


def _negation(verbe: str) -> str:
    """« ne » ou « n' », selon ce que le verbe commence."""
    return "n'" if verbe[:1].lower() in VOYELLES else "ne "


@regle("NEGATION_COMPLETE",
       "a l'ecrit soutenu, la negation garde son « ne »", registre=SOUTENU)
def _negation_complete(ctx: Contexte, i: int):
    """« j'ai pas » -> « je n'ai pas », « y a pas » -> « n'y a pas ».

    La regle se declenche sur le premier mot qui suit le sujet, et non sur le
    verbe : le « ne » se glisse devant les pronoms qui les separent.
    """
    debut = ctx.brut(i)
    if not debut:
        return None

    elision, noyau = separer_clitique(debut.lower())
    if not noyau:
        return None

    # Le sujet est-il juste avant, ou porte par l'elision du mot lui-meme ?
    sujet_elide = SUJETS_ELIDES.get(elision) if elision else None
    if sujet_elide is None and ctx.noyau(i - 1) not in SUJETS_NEGATION:
        return None
    if elision and sujet_elide is None:
        return None

    # Une negation suit-elle, a portee de vue ?
    if not any(ctx.mot(i + n) in NEGATIONS for n in range(1, PORTEE_NEGATION + 1)):
        return None

    # Deja niee ?
    if elision == "n'" or ctx.mot(i - 1) in ("ne", "n'"):
        return None
    if any(ctx.mot(i + n) in ("ne", "n'") or ctx.elision(i + n) == "n'"
           for n in range(0, PORTEE_NEGATION)):
        return None

    if sujet_elide is not None:
        return appliquer_casse(debut, f"{sujet_elide} {_negation(noyau)}{noyau}")
    return f"{_negation(noyau)}{debut}"


@regle("SUJET_IMPERSONNEL",
       "a l'ecrit soutenu, le sujet impersonnel s'ecrit", registre=SOUTENU)
def _sujet_impersonnel(ctx: Contexte, i: int):
    """« faut y aller » -> « il faut y aller », « y a » -> « il y a »."""
    if not ctx.debut_de_segment(i):
        return None
    mot = ctx.mot(i)
    if mot == "faut":
        return appliquer_casse(ctx.brut(i), "il faut")
    if mot == "y" and ctx.mot(i + 1) in ("a", "avait", "aura", "aurait"):
        return appliquer_casse(ctx.brut(i), "il y")
    return None


@regle("CA_CELA", "a l'ecrit soutenu, « ça » devient « cela »", registre=SOUTENU)
def _ca_cela(ctx: Contexte, i: int):
    if ctx.mot(i) != "ça" or ctx.elision(i):
        return None
    # « ça va ? » reste « ça va ? » : personne n'ecrit « cela va ? ».
    if ctx.mot(i + 1) in ("va", "vas", "allait"):
        return None
    return appliquer_casse(ctx.brut(i), "cela")


# ---------------------------------------------------------------------------
# Les mots justes qui en cachent un autre
#
# Le correcteur ne regarde que les mots absents du dictionnaire. « commet »
# y figure — c'est le verbe commettre — donc « commet ça va » passait
# intact. La table de `confusions.py` liste ces paires, chacune avec la
# condition qui rend la substitution sure.
# ---------------------------------------------------------------------------

@regle("MOT_REEL_TROMPEUR",
       "ce mot existe, mais ce n'est pas celui-la qu'on attend ici")
def _mot_reel_trompeur(ctx: Contexte, i: int):
    confusion = confusions.trouver(ctx, i, ctx.lexique)
    if confusion is None:
        return None
    return appliquer_casse(ctx.brut(i), confusion.voulu)


# ---------------------------------------------------------------------------
# Doublons
# ---------------------------------------------------------------------------

# Ces mots se repetent legitimement : « il a a peine mangé » est faux, mais
# « nous nous levons », « vous vous trompez » et « c'est très très bon » ne
# le sont pas.
DOUBLONS_LEGITIMES = {
    "nous", "vous", "se", "très", "bien", "plus", "moins", "tout", "si",
    "non", "oui", "eh", "ah", "oh", "ha", "ho", "hi", "na", "chut",
    # Les nombres et les lettres se repetent en enumerant.
    "un", "une", "deux", "a", "à", "y", "en",
}


@regle("DOUBLON", "ce mot est écrit deux fois de suite")
def _doublon(ctx: Contexte, i: int):
    """« je vais vais partir » — la faute de frappe la plus banale qui soit.

    On n'y touche que dans une meme phrase et sans ponctuation entre les
    deux : « bon, bon » est une insistance, pas une faute, et « il a dit :
    dit-il » n'est pas un doublon.
    """
    mot = ctx.mot(i)
    if not mot or mot != ctx.mot(i + 1):
        return None
    if mot in DOUBLONS_LEGITIMES or len(mot) < 2:
        return None
    # Une ponctuation ou un retour a la ligne entre les deux : c'est voulu.
    if ctx.separateur(i) != " ":
        return None
    # Une majuscule au second signale un debut de phrase, donc une coupure.
    if ctx.brut(i + 1)[:1].isupper() and not ctx.brut(i)[:1].isupper():
        return None
    return (ctx.brut(i), 2)


# ---------------------------------------------------------------------------
# Traits d'union
# ---------------------------------------------------------------------------

# Mots composes que l'on ecrit couramment en deux morceaux. Chaque entree est
# une suite de mots, et ce qu'elle doit devenir. Les suites longues passent
# avant les courtes : « c'est à dire » avant « à dire ».
COMPOSES = {
    ("rendez", "vous"): "rendez-vous",
    ("peut", "etre"): "peut-être",
    ("peut", "être"): "peut-être",
    ("au", "dessus"): "au-dessus",
    ("au", "dessous"): "au-dessous",
    ("au", "delà"): "au-delà",
    ("là", "bas"): "là-bas",
    ("la", "bas"): "là-bas",
    ("là", "haut"): "là-haut",
    ("ci", "dessus"): "ci-dessus",
    ("ci", "dessous"): "ci-dessous",
    ("ci", "joint"): "ci-joint",
    ("week", "end"): "week-end",
    ("après", "midi"): "après-midi",
    ("apres", "midi"): "après-midi",
    ("avant", "hier"): "avant-hier",
    ("aujourd'hui",): "aujourd'hui",
    ("quelque", "part"): "quelque part",   # sans trait d'union, justement
}

# Celles-la comptent trois mots.
COMPOSES_LONGS = {
    ("c'est", "à", "dire"): "c'est-à-dire",
    ("c'est", "a", "dire"): "c'est-à-dire",
    ("qu'est", "ce", "que"): "qu'est-ce que",
    ("qu'est", "ce", "qui"): "qu'est-ce qui",
    ("est", "ce", "que"): "est-ce que",
    ("est", "ce", "qui"): "est-ce qui",
    ("vis", "à", "vis"): "vis-à-vis",
    ("par", "ci", "par"): None,            # reserve, voir plus bas
}


@regle("TRAIT_UNION_COMPOSE", "ce mot composé prend un trait d'union")
def _trait_union_compose(ctx: Contexte, i: int):
    """« rendez vous », « peut etre », « c'est à dire »."""
    if ctx.separateur(i) != " ":
        return None

    trois = (ctx.mot(i), ctx.mot(i + 1), ctx.mot(i + 2))
    if trois in COMPOSES_LONGS and COMPOSES_LONGS[trois] is not None:
        if ctx.separateur(i + 1) != " ":
            return None
        return (appliquer_casse(ctx.brut(i), COMPOSES_LONGS[trois]), 3)

    deux = (ctx.mot(i), ctx.mot(i + 1))
    if deux in COMPOSES:
        remplacement = COMPOSES[deux]
        if remplacement == " ".join(deux):
            return None
        # « peut être » peut etre le verbe : « il peut être là ». Un sujet
        # devant, et on ne touche a rien.
        if deux[0] == "peut" and ctx.mot(i - 1) in PRONOMS_SUJETS:
            return None
        # « rendez-vous » : « rendez vous compte » est un imperatif.
        if deux == ("rendez", "vous") and ctx.mot(i + 2) in (
                "compte", "service", "la", "le", "les", "à", "a"):
            return None
        return (appliquer_casse(ctx.brut(i), remplacement), 2)
    return None


# Un imperatif suivi d'un pronom prend un trait d'union : « dis-moi »,
# « envoie-moi », « donne-lui », « vas-y ». Les formes sont listees plutot
# que devinees : « dis moi » est un imperatif, « je dis moi aussi » non.
IMPERATIFS_AVEC_PRONOM = {
    "dis", "dites", "donne", "donnez", "envoie", "envoyez", "montre",
    "montrez", "passe", "passez", "prends", "prenez", "laisse", "laissez",
    "rappelle", "rappelez", "explique", "expliquez", "excuse", "excusez",
    "aide", "aidez", "attends", "attendez", "regarde", "regardez",
    "écoute", "écoutez", "raconte", "racontez", "appelle", "appelez",
    "va", "vas", "allez", "viens", "venez", "tiens", "tenez", "suis",
    "arrête", "arrêtez", "occupe", "occupez", "amuse", "amusez",
}

PRONOMS_APRES_IMPERATIF = {"moi", "toi", "lui", "nous", "vous", "leur",
                           "le", "la", "les", "y", "en"}


@regle("TRAIT_UNION_IMPERATIF",
       "l'impératif et son pronom prennent un trait d'union")
def _trait_union_imperatif(ctx: Contexte, i: int):
    """« dis moi » -> « dis-moi », « vas y » -> « vas-y »."""
    if ctx.separateur(i) != " ":
        return None
    verbe, pronom = ctx.mot(i), ctx.mot(i + 1)
    if verbe not in IMPERATIFS_AVEC_PRONOM:
        return None
    if pronom not in PRONOMS_APRES_IMPERATIF:
        return None
    # Un sujet devant, et ce n'est plus un imperatif : « je dis moi aussi »,
    # « tu envoies le lien ».
    if ctx.mot(i - 1) in PRONOMS_SUJETS or ctx.elision(i - 1) in SUJETS_ELIDES:
        return None
    # « allez les bleus », « va la chercher » : le pronom y est complement
    # d'un verbe qui suit, pas de l'imperatif.
    if pronom in ("le", "la", "les") and ctx.mot(i + 2):
        return None
    # « vas y » demande un « s » ; « va y » n'existe pas.
    if verbe == "va" and pronom == "y":
        return (appliquer_casse(ctx.brut(i), "vas-y"), 2)
    return (appliquer_casse(ctx.brut(i), f"{ctx.brut(i)}-{pronom}"), 2)


# ---------------------------------------------------------------------------
# L'accent oublie sur un mot qui existe quand meme
#
# « pole » est au dictionnaire — c'est la « pole position » — mais « pôle »
# est trois fois plus employe. Le correcteur ne regardant que les mots
# absents du dictionnaire, il passait son chemin. Ils sont soixante-seize
# dans ce cas : moitie/moitié, comite/comité, foret/forêt, voila/voilà.
#
# La difficulte est que beaucoup sont aussi des verbes conjugues : « il
# prive », « tu cites », « on publie ». Un sujet devant, et l'on ne touche a
# rien.
# ---------------------------------------------------------------------------

# Ecart de frequence exige entre la graphie sans accent et celle avec.
ECART_ACCENT_OUBLIE = 3

# En dessous, le mot est trop court pour que la statistique dise quelque
# chose.
LONGUEUR_MINIMALE_ACCENT_OUBLIE = 4

# Ce qui annonce un verbe : apres eux, une forme sans accent est a sa place.
AVANT_UN_VERBE = (PRONOMS_SUJETS
                  | {"qui", "ne", "n'", "ça", "ce", "on", "y", "en",
                     "j'", "s'", "m'", "t'", "c'", "qu'", "me", "te", "se",
                     "lui", "leur", "nous", "vous"})

# « le », « la », « les » sont ambigus : article devant un nom (« la moitié »),
# pronom devant un verbe (« il la prive »). C'est ce qui les precede qui
# tranche.
ARTICLES_AMBIGUS = {"le", "la", "les", "l'"}


def _annonce_un_verbe(ctx: "Contexte", i: int) -> bool:
    """Ce qui precede le mot i en fait-il un verbe conjugue ?"""
    precedent = ctx.elision(i - 1) or ctx.mot(i - 1)
    if precedent in AVANT_UN_VERBE:
        return True
    if precedent in ARTICLES_AMBIGUS:
        # « il la prive » est un verbe ; « la moitié » est un nom. Un sujet
        # avant l'article, et c'est un pronom complement.
        avant = ctx.elision(i - 2) or ctx.mot(i - 2)
        return avant in AVANT_UN_VERBE or avant in PRONOMS_SUJETS
    return False


@regle("ACCENT_OUBLIE", "ce mot existe, mais il lui manque son accent")
def _accent_oublie(ctx: Contexte, i: int):
    """« au pole nord » -> « au pôle nord », « la moitie » -> « la moitié »."""
    mot = ctx.mot(i)
    if (len(mot) < LONGUEUR_MINIMALE_ACCENT_OUBLIE or ctx.elision(i)
            or not mot.isalpha() or mot != mot.lower()):
        return None
    if any(c in ACCENTUEES for c in mot):
        return None

    # Un sujet ou un pronom devant : c'est un verbe, et il est bien ecrit.
    if _annonce_un_verbe(ctx, i):
        return None

    # Un auxiliaire devant : c'est un participe, et deux participes se
    # ressemblent trop pour qu'on choisisse. « elles sont reparties » veut
    # dire qu'elles sont parties de nouveau, pas qu'on les a réparties.
    if _auxiliaire_avant(ctx, i):
        return None

    # Il faut une seule graphie accentuee : « cote » en a trois — « côte »,
    # « côté », « coté » — et rien ne dit laquelle.
    accentuees = [f for f in ctx.lexique.formes(mot)
                  if f.islower() and f != mot and accentue_mot(f)]
    if len(accentuees) != 1:
        return None

    avec = accentuees[0]
    rang_sans = ctx.lexique.rang(mot)
    rang_avec = ctx.lexique.rang(avec)
    if rang_avec * ECART_ACCENT_OUBLIE > rang_sans:
        return None
    return appliquer_casse(ctx.brut(i), avec)


# ---------------------------------------------------------------------------
# Un determinant singulier veut un nom singulier
# ---------------------------------------------------------------------------

DETERMINANTS_SINGULIERS = {
    "le", "la", "un", "une", "ce", "cet", "cette", "au", "du",
    "mon", "ma", "ton", "ta", "son", "sa", "notre", "votre", "leur",
    "chaque", "aucun", "aucune", "quel", "quelle",
}

# Ces noms se terminent par « s » ou « x » au singulier : leur retirer la
# derniere lettre en ferait autre chose, ou rien du tout.
INVARIABLES_EN_S = {
    "temps", "fois", "prix", "corps", "pays", "bras", "cours", "mois",
    "poids", "univers", "succes", "succès", "proces", "procès", "repas",
    "puis", "depuis", "plus", "moins", "jamais", "toujours", "alors",
    "tous", "vous", "nous", "sens", "fils", "gaz", "choix", "voix",
    "croix", "noix", "prix", "taux", "faux", "roux", "doux", "vieux",
    "mieux", "ceux", "eux", "yeux", "cheveux", "jeux", "lieux", "dieux",
    "genoux", "bijoux", "travaux", "journaux", "vitraux",
}


@regle("ACCORD_DETERMINANT_SINGULIER",
       "après un déterminant singulier, le nom reste au singulier")
def _accord_determinant_singulier(ctx: Contexte, i: int):
    """« au niveaux » -> « au niveau », « une choses » -> « une chose »."""
    mot = ctx.mot(i)
    if ctx.elision(i) or not mot.endswith(("s", "x")) or len(mot) < 4:
        return None
    if mot in INVARIABLES_EN_S or mot in MOTS_INVARIABLES:
        return None
    if ctx.mot(i - 1) not in DETERMINANTS_SINGULIERS:
        return None

    # Le mot doit vraiment etre un pluriel. « la souris », « le prix », « le
    # temps » finissent par « s » et n'en sont pas, et la liste ecrite a la
    # main n'en voyait jamais la fin : le dictionnaire, lui, les connait
    # tous.
    if ctx.morphologie.connait(mot) and not ctx.morphologie.nom_pluriel(mot):
        return None

    # Un pronom sujet juste avant le determinant : ce n'en est pas un.
    # « elles son parties » n'est pas « elles son partie » — c'est « sont »
    # qu'il fallait lire, et une autre regle s'en charge.
    if ctx.mot(i - 2) in PRONOMS_SUJETS:
        return None

    singulier = ctx.morphologie.au_singulier(mot) or mot[:-1]
    if not ctx.connait(singulier):
        return None
    # Le singulier doit etre la forme courante : « le temps » n'est pas
    # « le temp », et « un bus » n'est pas « un bu ».
    rang_pluriel = ctx.lexique.rang(mot)
    rang_singulier = ctx.lexique.rang(singulier)
    if rang_singulier >= rang_pluriel:
        return None
    return appliquer_casse(ctx.brut(i), singulier)
