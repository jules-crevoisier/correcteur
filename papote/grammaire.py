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

from .lexique import sans_accents
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

FIN_DE_SEGMENT = re.compile(r"^\s*($|[.!?,;:…\n)\]»\"])")
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

    def __init__(self, texte: str, jetons: list[Jeton], lexique):
        self.texte = texte
        self.jetons = jetons
        self.lexique = lexique

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
        if ctx.connait(candidat):
            return candidat
    return None


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


@regle("OU_ACCENT", "« où » designe le lieu ; « ou » relie deux choix")
def _ou_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "ou":
        return None
    if ctx.mot(i + 1) in ("est", "sont", "es", "était", "étaient", "sera",
                          "seront", "ça"):
        return appliquer_casse(ctx.brut(i), "où")
    # « là ou j'habite » : apres « là », c'est toujours le lieu.
    if ctx.mot(i - 1) == "là":
        return appliquer_casse(ctx.brut(i), "où")
    # « je sais pas ou aller » : devant un infinitif, « ou » n'a pas de sens.
    suivant = ctx.mot(i + 1)
    if suivant.endswith(("er", "ir")) and ctx.connait(suivant) \
            and suivant not in MOTS_INVARIABLES:
        return appliquer_casse(ctx.brut(i), "où")
    return None


AVANT_LA_ACCENT = {
    "suis", "es", "est", "sommes", "êtes", "sont", "étais", "était",
    "serai", "sera", "reste", "restes", "restons", "restez", "viens",
    "vient", "venez", "arrive", "arrives", "jusque", "par", "celui",
    "celle", "ceux", "celles", "mets", "assieds",
}


@regle("LA_ACCENT", "« là » designe le lieu ; « la » est un article")
def _la_accent(ctx: Contexte, i: int):
    if ctx.mot(i) != "la":
        return None
    if ctx.mot(i + 1) == "bas" and ctx.separateur(i) == " ":
        return (appliquer_casse(ctx.brut(i), "là-bas"), 2)
    if ctx.noyau(i - 1) in AVANT_LA_ACCENT and ctx.fin_de_segment(i):
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

    accorde = mot + terminaison
    if mot.endswith(("s", "x", "e")) or not ctx.connait(accorde):
        return None
    return appliquer_casse(ctx.brut(i), accorde)


def _accord_sujet_nominal_etre(ctx: Contexte, i: int) -> str | None:
    """« les enfants sont content » : le sujet est un nom, et il est pluriel.

    Le genre reste inconnu — le dictionnaire ne le dit pas — donc on ne
    propose que le pluriel masculin, celui qui vaut aussi pour un groupe
    mixte.
    """
    if ctx.noyau(i - 1) not in ("sont", "sommes", "étaient", "étions",
                                "seront", "serons"):
        return None
    if not _est_pluriel(ctx, ctx.mot(i - 2)):
        return None
    return "s"


NOMBRES_PLURIELS = {"deux", "trois", "quatre", "cinq", "six", "sept", "huit",
                    "neuf", "dix", "onze", "douze", "quinze", "vingt", "cent"}

# Mots qui ne s'accordent jamais. Plusieurs ont pourtant un pluriel au
# dictionnaire — « les avants » d'une equipe, « les contres » au bridge — et
# les regles d'accord les prendraient pour des adjectifs.
MOTS_INVARIABLES = {
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


def _est_adjectif(ctx: "Contexte", mot: str) -> bool:
    """Le mot peut-il s'accorder comme un adjectif ?

    Un adjectif a un feminin — « content » / « contente » — ou se termine
    deja par un « e » qui lui en tient lieu — « rouge ». Cette question
    posee au dictionnaire suffit a ecarter « avant », « contre » et les
    autres invariables qui ont un pluriel pour d'autres raisons.
    """
    if mot in MOTS_INVARIABLES or not ctx.connait(mot):
        return False
    return mot.endswith("e") or ctx.connait(mot + "e")


def _est_pluriel(ctx: "Contexte", mot: str) -> bool:
    """Le mot est-il un nom au pluriel ?

    « quelques » et « plusieurs » portent bien la marque du pluriel, mais ce
    sont des determinants : les prendre pour le nom du groupe ferait chercher
    le verbe un mot trop loin.
    """
    if not mot or not mot.endswith(("s", "x")):
        return False
    if (mot in DETERMINANTS_PLURIELS or mot in NOMBRES_PLURIELS
            or mot in MOTS_INVARIABLES or mot in PRONOMS_SUJETS):
        return False
    return ctx.connait(mot)


def _determinant_pluriel(ctx: "Contexte", i: int) -> bool:
    """Le jeton i annonce-t-il un groupe au pluriel ?

    « les » est aussi un pronom complement : « je les mange » n'annonce
    aucun nom. On le refuse donc derriere un pronom sujet.
    """
    mot = ctx.mot(i)
    if mot in DETERMINANTS_PLURIELS or mot in NOMBRES_PLURIELS:
        return True
    return mot == "les" and ctx.mot(i - 1) not in PRONOMS_SUJETS


def _pluriels(mot: str) -> list[str]:
    """Les pluriels envisageables d'un nom singulier."""
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

    if determinant not in DETERMINANTS_PLURIELS:
        # « les » est aussi un pronom : « je les mange » n'a pas de nom.
        if determinant != "les" or ctx.mot(i - 2) in PRONOMS_SUJETS:
            return None

    if ctx.elision(i) or mot.endswith(("s", "x", "z")) or not ctx.connait(mot):
        return None

    for pluriel in _pluriels(mot):
        if ctx.connait(pluriel):
            return appliquer_casse(ctx.brut(i), pluriel)
    return None


@regle("ACCORD_SUJET_NOMINAL",
       "le verbe s'accorde avec son sujet au pluriel")
def _accord_sujet_nominal(ctx: Contexte, i: int):
    """« les gens pense » -> « les gens pensent »."""
    if ctx.elision(i):
        return None
    if not _est_pluriel(ctx, ctx.mot(i - 1)) or not _determinant_pluriel(ctx, i - 2):
        return None

    mot = ctx.mot(i)
    if mot.endswith("ent") or mot in PRONOMS_COMPLEMENTS:
        return None
    # « ces quelques minutes » : un nom deja au pluriel n'est pas le verbe
    # qu'on cherche, meme si « minuter » existe.
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
    # Un verbe s'accorde autrement : ACCORD_SUJET_NOMINAL s'en charge.
    if infinitif_premier_groupe(ctx, mot) is not None:
        return None

    apres_le_nom = (_est_pluriel(ctx, ctx.mot(i - 1))
                    and _determinant_pluriel(ctx, i - 2))
    avant_le_nom = (_determinant_pluriel(ctx, i - 1)
                    and _est_pluriel(ctx, ctx.mot(i + 1)))
    if not (apres_le_nom or avant_le_nom):
        return None

    for pluriel in _pluriels(mot):
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
             registre: str = PARLE) -> list[Suggestion]:
    """Passe toutes les regles sur le texte et renvoie leurs propositions."""
    ctx = Contexte(texte, jetons, lexique)
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
